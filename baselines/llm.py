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

from .prompts import ABSTAIN_OFFERED, ABSTAIN_WITHHELD, PROMPT_VERSION, system_prompt, user_prompt

_VERDICTS = {v.value: v for v in Verdict}


@dataclass
class Usage:
    input_tokens: int = 0
    output_tokens: int = 0
    calls: int = 0
    seconds: float = 0.0

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
    unparseable = off_schema = 0

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
            # A line naming the pair but no permitted verdict is a failure to
            # answer, not an abstention. Leave it unpredicted.
            unparseable += 1
            continue

        if variant == ABSTAIN_WITHHELD and verdict in (Verdict.NEEDS_EVIDENCE, Verdict.UNMONITORED):
            off_schema += 1

        idx = parts.index(pair_id)
        ev = [p for p in parts[idx + 1:] if p.lower() not in _VERDICTS and p != "-"]
        seen[pair_id] = Prediction(
            pair_id=pair_id, verdict=verdict, evidence_fields=tuple(ev[:3])
        )

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
    max_tokens: int = 8000,
    keep_raw: bool = False,
    scope_sources: bool = False,
) -> RunResult:
    """Run one firm through a provider, batching pairs.

    Batching exists because a firm can carry thousands of pairs. Sources and the
    rulebook are re-sent per batch so that every batch is independently valid;
    providers with prefix caching absorb the repetition.
    """
    system = system_prompt(firm, variant)
    pair_ids = [p.pair_id for p in firm.pairs]

    preds: list[Prediction] = []
    usage = Usage()
    unparseable = missing = off_schema = 0
    raw: list[str] = []

    for i in range(0, len(pair_ids), batch_size):
        batch = pair_ids[i : i + batch_size]
        user = user_prompt(firm, obligations, batch, scope_sources=scope_sources)
        text, u = provider.complete(system, user, max_tokens)
        usage.add(u)
        if keep_raw:
            raw.append(text)
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
