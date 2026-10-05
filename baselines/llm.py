"""Language-model baselines.

Providers are pluggable. `MockProvider` exercises the entire path offline and is
what the test suite uses; the API providers are thin and interchangeable.

PARSING POLICY, which is a scoring decision and not a detail:

A reply line that names no permitted verdict is recorded as `unparseable` and
the pair is left WITHOUT a prediction, which the metric module counts as an
error. It is never silently coerced to a verdict. Coercing to `needs_evidence`
would flatter a model's false-green rate by converting its formatting failures
into abstentions; coercing to `pass` would do the opposite. Both would make the
headline number a function of our parser. We report the unparseable rate
separately so a reader can see how much of a model's score is formatting.

In the abstain_withheld condition a model may still emit `needs_evidence`
despite the schema forbidding it. That is a finding, not an error: it means the
model refused a schema that had no representation for absent evidence. Such
replies are parsed at face value and counted in `off_schema`.
"""

from __future__ import annotations

import json
import os
import re
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Protocol

from nofalsegreen.schema import Firm, Obligation, Prediction, Verdict

from .prompts import (ABSTAIN_CLOSED, ABSTAIN_OFFERED, ABSTAIN_REMOVED_ONLY, ABSTAIN_WITHHELD,
                      PROMPT_VERSION,
                      system_prompt, user_prompt)

_VERDICTS = {v.value: v for v in Verdict}


@dataclass
class Usage:
    input_tokens: int = 0
    output_tokens: int = 0
    calls: int = 0
    seconds: float = 0.0
    # The provider's own stop reason for a single call. "length" means the reply
    # was cut off, which can happen below our max_tokens when an upstream host
    # enforces a smaller limit of its own.
    finish_reason: str = ""

    def add(self, other: "Usage") -> None:
        self.input_tokens += other.input_tokens
        self.output_tokens += other.output_tokens
        self.calls += other.calls
        self.seconds += other.seconds


@dataclass
class RunResult:
    model: str
    variant: str
    firm_id: str
    predictions: list[Prediction]
    usage: Usage
    n_pairs: int
    n_parsed: int
    n_unparseable: int
    n_missing_lines: int
    n_off_schema: int
    n_truncated_calls: int = 0
    n_failed_batches: int = 0
    # Replies that came back empty or at the output cap, and batches still
    # without a complete reply after every re-request (the model ran to our cap
    # on every attempt; a final outcome, scored as unanswered).
    n_incomplete_calls: int = 0
    n_unrecovered_batches: int = 0
    # True when the run stopped on consecutive failed calls: the upstream is
    # down, and the run should resume later rather than be scored with holes.
    stopped_early: bool = False
    raw: list[str] = field(default_factory=list)

    @property
    def unparseable_rate(self) -> float:
        return self.n_unparseable / self.n_pairs if self.n_pairs else 0.0


class Provider(Protocol):
    name: str

    def complete(self, system: str, user: str, max_tokens: int) -> tuple[str, Usage]: ...


# ── providers ───────────────────────────────────────────────────────────────


class MockProvider:
    """Deterministic offline provider.

    `policy` decides the verdict from the pair id alone, so a test can construct
    a model with a known failure signature and assert the harness measures it.
    """

    def __init__(self, policy: Callable[[str], str], name: str = "mock"):
        self.policy = policy
        self.name = name

    def complete(self, system: str, user: str, max_tokens: int) -> tuple[str, Usage]:
        # Rule ids are not uniformly lower-case (e.g. specialty.occupation.criteria.A1_A4),
        # so the id pattern must be case-insensitive or pairs are silently dropped.
        pair_ids = re.findall(r"^([A-Za-z0-9_.\-]+::[^\t\n]+)\t", user, re.M)
        lines = [f"{pid}\t{self.policy(pid)}\t-" for pid in pair_ids]
        return "\n".join(lines), Usage(
            input_tokens=len(system + user) // 4,
            output_tokens=sum(len(l) for l in lines) // 4,
            calls=1,
            seconds=0.0,
        )


class AnthropicProvider:
    def __init__(self, model: str):
        import anthropic  # deferred: only needed when actually calling the API

        self.name = model
        self._client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

    def complete(self, system: str, user: str, max_tokens: int) -> tuple[str, Usage]:
        t0 = time.time()
        msg = self._client.messages.create(
            model=self.name,
            max_tokens=max_tokens,
            system=[{"type": "text", "text": system, "cache_control": {"type": "ephemeral"}}],
            messages=[{"role": "user", "content": user}],
        )
        text = "".join(b.text for b in msg.content if getattr(b, "type", "") == "text")
        return text, Usage(
            input_tokens=msg.usage.input_tokens,
            output_tokens=msg.usage.output_tokens,
            calls=1,
            seconds=time.time() - t0,
        )


class OpenAIProvider:
    def __init__(self, model: str):
        from openai import OpenAI

        self.name = model
        self._client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])

    def complete(self, system: str, user: str, max_tokens: int) -> tuple[str, Usage]:
        t0 = time.time()
        r = self._client.chat.completions.create(
            model=self.name,
            max_completion_tokens=max_tokens,
            messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
        )
        u = r.usage
        return r.choices[0].message.content or "", Usage(
            input_tokens=getattr(u, "prompt_tokens", 0),
            output_tokens=getattr(u, "completion_tokens", 0),
            calls=1,
            seconds=time.time() - t0,
        )


# ── parsing ─────────────────────────────────────────────────────────────────


def parse_response(text: str, expected_pair_ids: list[str], variant: str):
    """Parse model output into predictions.

    Returns (predictions, n_unparseable, n_missing_lines, n_off_schema).
    A pair whose line cannot be parsed gets NO prediction. See module docstring.
    """
    expected = set(expected_pair_ids)
    seen: dict[str, Prediction] = {}
    mentioned_without_verdict: set[str] = set()

    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or line.startswith("```"):
            continue

        parts = re.split(r"\t+|\s{2,}|\s*\|\s*", line)
        parts = [p.strip() for p in parts if p.strip()]
        if not parts:
            continue

        pair_id = next((p for p in parts if "::" in p), None)
        if pair_id is None or pair_id not in expected:
            continue

        verdict = None
        for p in parts:
            key = p.lower().strip(".,;:`*")
            if key in _VERDICTS:
                verdict = _VERDICTS[key]
                break
        if verdict is None:
            # A line naming the pair but no permitted verdict. Reasoning models
            # echo pair ids while thinking ("### 1. rule::entity [employer]")
            # before answering, so this is only a failure if the pair is never
            # answered anywhere in the reply; counted per PAIR after the loop.
            mentioned_without_verdict.add(pair_id)
            continue

        idx = parts.index(pair_id)
        ev = [p for p in parts[idx + 1:] if p.lower() not in _VERDICTS and p != "-"]
        seen[pair_id] = Prediction(
            pair_id=pair_id, verdict=verdict, evidence_fields=tuple(ev[:3])
        )

    # The LAST verdict line for a pair wins: the final answer follows the trace.
    unparseable = len(mentioned_without_verdict - set(seen))
    off_schema = 0
    variant = variant[:-len("_para")] if variant.endswith("_para") else variant
    if variant in (ABSTAIN_WITHHELD, ABSTAIN_CLOSED) or variant.startswith("fx_o0"):
        off_schema = sum(1 for pr in seen.values()
                         if pr.verdict in (Verdict.NEEDS_EVIDENCE, Verdict.UNMONITORED))
    elif variant == ABSTAIN_REMOVED_ONLY:
        off_schema = sum(1 for pr in seen.values() if pr.verdict is Verdict.NEEDS_EVIDENCE)
    missing = len(expected) - len(seen) - unparseable
    return list(seen.values()), unparseable, max(0, missing), off_schema


# ── runner ──────────────────────────────────────────────────────────────────


def run_firm(
    provider: Provider,
    firm: Firm,
    obligations: list[Obligation],
    *,
    variant: str = ABSTAIN_OFFERED,
    batch_size: int = 40,
    max_tokens: int | None = None,
    keep_raw: bool = False,
    scope_sources: bool = False,
    progress: bool = False,
    cache_path: Path | None = None,
    max_attempts: int = 3,
    stop_on_host_failure: bool = True,
) -> RunResult:
    """Run one firm through a provider, batching pairs.

    Batching exists because a firm can carry thousands of pairs. Sources and the
    rulebook are re-sent per batch so that every batch is independently valid;
    providers with prefix caching absorb the repetition.
    """
    system = system_prompt(firm, variant)
    pair_ids = [p.pair_id for p in firm.pairs]

    # Output budget. Reasoning models spend most of their completion on a trace
    # before emitting verdict lines: a 20-pair call measured ~4,400 output
    # tokens against ~600 tokens of actual answer. A flat cap truncates them
    # mid-trace, so they emit NO verdicts and score as unparseable -- a harness
    # artifact indistinguishable from model failure. Budget generously and
    # scale with batch size.
    if max_tokens is None:
        # 32,000 sits under every evaluated model's own completion ceiling (the
        # smallest is 32,768). The earlier max(4000, 700 * batch) = 8,400 at
        # batch 12 was measured to truncate 2-11 of 12 calls per run in the main
        # sweep: reasoning models spent the whole budget thinking and returned
        # EMPTY content, which scores as missed pairs -- a harness artifact
        # indistinguishable from model failure.
        max_tokens = 32_000

    preds: list[Prediction] = []
    usage = Usage()
    unparseable = missing = off_schema = truncated = failed_batches = 0
    incomplete = unrecovered = 0
    bad_streak, stopped_early = 0, False
    consecutive_failures = 0
    raw: list[str] = []

    # Batch-level cache. A firm of 221 pairs at batch 8 is 28 calls, which
    # exceeds a 50-per-day quota once both ablation conditions are counted, so
    # completed batches MUST survive a mid-firm stop or the firm never finishes.
    cache: dict[str, str] = {}
    if cache_path and cache_path.exists():
        try:
            cache = json.loads(cache_path.read_text())
        except json.JSONDecodeError:
            cache = {}

    def cache_key(ids: list[str]) -> str:
        # PROMPT_VERSION is part of the key: a reply to one prompt version must
        # never be reused as the reply to another. Without it, a protocol fix
        # would silently re-score the old prompt's answers.
        return f"{PROMPT_VERSION}|{provider.name}|{variant}|{firm.firm_id}|{ids[0]}|{len(ids)}"

    n_batches = (len(pair_ids) + batch_size - 1) // batch_size
    for i in range(0, len(pair_ids), batch_size):
        batch = pair_ids[i : i + batch_size]
        if progress:
            # A 28-call run is ~25 minutes; without this it is indistinguishable
            # from a hang.
            print(f"      batch {i // batch_size + 1}/{n_batches} "
                  f"({len(preds)} parsed so far)", flush=True)
        user = user_prompt(firm, obligations, batch, scope_sources=scope_sources)
        ck = cache_key(batch)
        cached = cache.get(ck)
        if isinstance(cached, dict):
            cached = cached.get("text")
        if cached is not None:
            p, unp, miss, offs = parse_response(cached, batch, variant)
            preds.extend(p)
            unparseable += unp
            missing += miss
            off_schema += offs
            if keep_raw:
                raw.append(cached)
            continue

        # An empty or capped reply is a delivery failure, not an answer: the
        # same rule that re-requested the truncated replies of the first v1.1
        # attempt. Re-request it up to max_attempts in total; if it is still
        # incomplete, its pairs are scored as missing and the batch is counted.
        try:
            for attempt in range(1, max_attempts + 1):
                text, u = provider.complete(system, user, max_tokens)
                usage.add(u)
                capped = (bool(u.output_tokens) and u.output_tokens >= max_tokens) \
                    or u.finish_reason == "length"
                # An upstream error ending a non-empty reply is a delivery
                # failure too (fixed after the study: one Lightning reply ended
                # this way after all 12 verdict lines and was kept; see paper).
                if u.finish_reason == "error":
                    capped = True
                if progress:
                    state = "CAP" if capped else ("EMPTY" if not text.strip() else "ok")
                    print(f"        attempt {attempt}: {u.output_tokens} output tokens, "
                          f"{u.seconds:.0f}s, finish={u.finish_reason or '?'}, {state}",
                          flush=True)
                if text.strip() and not capped:
                    bad_streak = 0
                    break
                incomplete += 1
                if capped:
                    truncated += 1
                # Two kinds of incomplete reply. A host fault (empty, an error
                # finish, or cut off below our cap) says nothing about the model.
                # A reply that runs to OUR cap is the model generating without
                # end; 32,000 is at the model's own ceiling, so that is the
                # model's behaviour and the batch is eventually left unanswered.
                own_cap = bool(u.output_tokens) and u.output_tokens >= max_tokens
                if own_cap:
                    continue
                # Three host faults in a row, across batches, means the host is
                # down. Each attempt costs a request from a 50-a-day allowance,
                # so stop and resume after the reset.
                bad_streak += 1
                # A finalizing pass tries every batch once more instead, then
                # records whatever was answered.
                if stop_on_host_failure and bad_streak >= max_attempts:
                    stopped_early = True
                    break
            else:
                unrecovered += 1
            if stopped_early:
                if progress:
                    print(f"      stopping: {bad_streak} consecutive incomplete "
                          f"replies; resume later", flush=True)
                break
        except Exception as exc:  # noqa: BLE001
            # One dead batch must not discard the other 20 calls of a firm. The
            # pairs in it get no prediction, which metrics score as errors, and
            # the failure is counted so it cannot be mistaken for model output.
            if type(exc).__name__ == "DailyQuotaExhausted":
                raise
            failed_batches += 1
            # Consecutive failures mean the provider is down or the quota is
            # spent in a form we did not recognise. Continuing would burn the
            # rest of the day's allowance on calls that cannot succeed, so stop
            # and let the cache carry what completed.
            consecutive_failures += 1
            if consecutive_failures >= 3:
                if progress:
                    print(f"      stopping: {consecutive_failures} consecutive "
                          f"batch failures", flush=True)
                break
            if keep_raw:
                raw.append(f"[BATCH FAILED] {type(exc).__name__}: {str(exc)[:200]}")
            continue
        if keep_raw:
            raw.append(text)
        consecutive_failures = 0
        hit_cap = (bool(u.output_tokens) and u.output_tokens >= max_tokens) \
            or u.finish_reason in ("length", "error")
        # Never cache a reply that was cut off or empty: a cached truncation
        # would be replayed forever instead of re-requested with more budget.
        if cache_path is not None and text.strip() and not hit_cap:
            cache[ck] = {"text": text, "output_tokens": u.output_tokens,
                         "max_tokens": max_tokens, "finish_reason": u.finish_reason}
            cache_path.parent.mkdir(parents=True, exist_ok=True)
            cache_path.write_text(json.dumps(cache, indent=1))

        p, unp, miss, offs = parse_response(text, batch, variant)
        preds.extend(p)
        unparseable += unp
        missing += miss
        off_schema += offs

    return RunResult(
        model=provider.name,
        variant=variant,
        firm_id=firm.firm_id,
        predictions=preds,
        usage=usage,
        n_pairs=len(pair_ids),
        n_parsed=len(preds),
        n_unparseable=unparseable,
        n_missing_lines=missing,
        n_off_schema=off_schema,
        n_truncated_calls=truncated,
        n_failed_batches=failed_batches,
        n_incomplete_calls=incomplete,
        n_unrecovered_batches=unrecovered,
        stopped_early=stopped_early,
        raw=raw,
    )


def estimate_cost(
    firm: Firm, obligations: list[Obligation], *, batch_size: int = 40,
    scope_sources: bool = False,
) -> dict:
    """Token-cost probe. Builds every prompt without calling any API."""
    system = system_prompt(firm, ABSTAIN_OFFERED)
    pair_ids = [p.pair_id for p in firm.pairs]
    in_chars = 0
    largest_call_chars = 0
    for i in range(0, len(pair_ids), batch_size):
        batch = pair_ids[i : i + batch_size]
        call_chars = len(system) + len(
            user_prompt(firm, obligations, batch, scope_sources=scope_sources)
        )
        in_chars += call_chars
        largest_call_chars = max(largest_call_chars, call_chars)
    n_batches = (len(pair_ids) + batch_size - 1) // batch_size
    # ~4 chars/token is the standard rough conversion; ~30 output tokens per pair line.
    return {
        "firm_id": firm.firm_id,
        "n_pairs": len(pair_ids),
        "n_batches": n_batches,
        "input_chars": in_chars,
        "est_input_tokens": in_chars // 4,
        "est_output_tokens": len(pair_ids) * 30,
        "prompt_version": PROMPT_VERSION,
        "scope_sources": scope_sources,
        # The per-minute token quota is checked against the LARGEST single call,
        # not the average, so this is the figure that decides feasibility.
        "max_call_tokens": largest_call_chars // 4 + batch_size * 30,
    }


PROVIDERS = {"anthropic": AnthropicProvider, "openai": OpenAIProvider}
