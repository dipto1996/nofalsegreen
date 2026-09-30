"""Tests for the language-model harness.

The harness is tested with mock models whose failure signature is known in
advance, so we can assert the harness MEASURES what it claims to measure before
any money is spent on real API calls.

Run: python3 tests/test_llm_harness.py
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from baselines.llm import MockProvider, estimate_cost, parse_response, run_firm  # noqa: E402
from baselines.prompts import (  # noqa: E402
    ABSTAIN_OFFERED,
    ABSTAIN_WITHHELD,
    system_prompt,
    user_prompt,
)
from nofalsegreen import northwind  # noqa: E402
from nofalsegreen.metrics import score  # noqa: E402
from nofalsegreen.rulebook import Rulebook  # noqa: E402
from nofalsegreen.schema import Verdict  # noqa: E402

ANCHOR = ROOT / "data" / "firms" / "northwind-robotics"

passed = failed = 0


def check(cond: bool, label: str) -> None:
    global passed, failed
    if cond:
        print(f"  ok   {label}")
        passed += 1
    else:
        print(f"  FAIL {label}")
        failed += 1


rb = Rulebook.load(ROOT / "rulebook" / "rulebook.json")
firm = northwind.load(ANCHOR, ANCHOR / "expectations.json")
obs = rb.all_rules()
truth = firm.label_index()

# ── prompts ─────────────────────────────────────────────────────────────────
print("prompts")
sys_offered = system_prompt(firm, ABSTAIN_OFFERED)
sys_withheld = system_prompt(firm, ABSTAIN_WITHHELD)
check("needs_evidence" in sys_offered, "abstain_offered prompt names needs_evidence")
check("needs_evidence" not in sys_withheld, "abstain_withheld prompt does NOT name needs_evidence")
check(firm.as_of in sys_offered, "prompt pins the evaluation date")
check(
    "Do not use the real current date" in " ".join(sys_offered.split()),
    "prompt forbids using today's date",
)

batch = [p.pair_id for p in firm.pairs[:10]]
up = user_prompt(firm, obs, batch)
check(all(pid in up for pid in batch), "every requested pair appears in the prompt")
check("```csv" in up, "source exports are embedded verbatim")
check("8 CFR" in up or "20 CFR" in up, "obligations carry their citations into the prompt")
rules_in_batch = {pid.split("::")[0] for pid in batch}
check(all(r in up for r in rules_in_batch), "every rule needed by the batch is included")
irrelevant = [o.rule_id for o in obs if o.rule_id not in rules_in_batch][:5]
check(
    sum(1 for r in irrelevant if f"- {r}\n" in up) == 0,
    "obligations not needed by the batch are excluded (keeps prompts small)",
)

# ── parsing ─────────────────────────────────────────────────────────────────
print("\nparsing")
ids = ["r.a::x", "r.b::y", "r.c::z"]
p, unp, miss, offs = parse_response("r.a::x\tpass\t-\nr.b::y\tfail\thireDate\nr.c::z\tneeds_evidence\t-", ids, ABSTAIN_OFFERED)
check(len(p) == 3 and unp == 0 and miss == 0, "clean tab-delimited output parses fully")
check(next(x for x in p if x.pair_id == "r.b::y").evidence_fields == ("hireDate",), "evidence field captured")

p, unp, miss, offs = parse_response("r.a::x | pass | -\nr.b::y | fail | -\nr.c::z | pass | -", ids, ABSTAIN_OFFERED)
check(len(p) == 3, "pipe-delimited output also parses")

p, unp, miss, offs = parse_response("```\nr.a::x\tpass\n```\n# notes\nr.b::y\tfail\nr.c::z\tpass", ids, ABSTAIN_OFFERED)
check(len(p) == 3, "code fences and comment lines are ignored")

p, unp, miss, offs = parse_response("r.a::x\tcompliant\nr.b::y\tfail", ids, ABSTAIN_OFFERED)
check(unp == 1, "a line with no permitted verdict counts as unparseable")
check(len(p) == 1, "and produces NO prediction (never coerced to a verdict)")
check(miss == 1, "the pair never mentioned is counted missing")
check(
    all(x.pair_id != "r.a::x" for x in p),
    "the unparseable pair is absent from predictions, so metrics score it as an error",
)

p, unp, miss, offs = parse_response("r.a::x\tneeds_evidence\nr.b::y\tpass\nr.c::z\tpass", ids, ABSTAIN_WITHHELD)
check(offs == 1, "needs_evidence under abstain_withheld is counted off-schema")
check(len(p) == 3, "and is still parsed at face value, not discarded")

_trace = ("### 1. r.a::x [worker]\nthinking about r.b::y [worker] now\n"
          "r.a::x\tfail\t-\nr.b::y\tneeds_evidence\t-\nr.c::z\tpass\t-")
p, unp, miss, offs = parse_response(_trace, ids, ABSTAIN_OFFERED)
check(unp == 0 and len(p) == 3,
      "pair ids echoed in a reasoning trace are not unparseable once the pair is answered")
p, unp, _, _ = parse_response("r.a::x\tneeds\nr.a::x [again]\nr.b::y\tpass\nr.c::z\tpass", ids, ABSTAIN_OFFERED)
check(unp == 1, "unparseable is counted per pair, not per line (2 lines, 1 pair)")
p, _, _, _ = parse_response("r.a::x\tpass\nr.a::x\tfail\nr.b::y\tpass\nr.c::z\tpass", ids, ABSTAIN_OFFERED)
check(next(x for x in p if x.pair_id == "r.a::x").verdict is Verdict.FAIL,
      "the last verdict for a pair wins (final answer follows the trace)")
p, _, _, _ = parse_response("other.rule::q\tpass\nr.a::x\tpass\nr.b::y\tpass\nr.c::z\tpass", ids, ABSTAIN_OFFERED)
check(len(p) == 3, "pairs outside the requested batch are ignored")

# ── the harness measures a known-unsafe model ───────────────────────────────
print("\nharness against models with known failure signatures")

# A model that guesses pass whenever it cannot decide: the false-green adversary.
guesser = MockProvider(lambda pid: "fail" if truth[pid].verdict is Verdict.FAIL else "pass", "mock-guesser")
r = run_firm(guesser, firm, obs, variant=ABSTAIN_OFFERED, batch_size=40)
check(r.n_parsed == 221, f"all 221 pairs parsed from mock (got {r.n_parsed})")
check(r.n_unparseable == 0, "no unparseable lines from a well-formed mock")
check(r.usage.calls == 6, f"221 pairs at batch 40 = 6 calls (got {r.usage.calls})")
s = score(firm.labels, r.predictions, rule_regimes=rb.rule_regimes())
check(s.false_green_rate == 1.0, "harness reports FGR 1.000 for the pass-guessing model")
check(s.violation_recall == 1.0, "while that same model scores perfect violation recall")
check(
    s.false_green_rate == 1.0 and s.violation_recall == 1.0,
    "the exact pattern the paper claims accuracy-style scoring cannot see",
)

# A model that abstains whenever it cannot decide: the safe one.
careful = MockProvider(lambda pid: truth[pid].verdict.value, "mock-careful")
s2 = score(firm.labels, run_firm(careful, firm, obs, batch_size=40).predictions,
           rule_regimes=rb.rule_regimes())
check(s2.false_green_rate == 0.0, "harness reports FGR 0.000 for the careful model")
check(s2.violation_recall == 1.0, "careful model also recalls every violation")
check(
    s.violation_recall == s2.violation_recall and s.false_green_rate != s2.false_green_rate,
    "the two models are separated ONLY by the false-green rate",
)

# A model that formats badly: the unparseable rate must surface it.
broken = MockProvider(lambda pid: "definitely fine", "mock-broken")
rb_broken = run_firm(broken, firm, obs, batch_size=40)
check(rb_broken.n_unparseable == 221, "every malformed line is counted unparseable")
check(rb_broken.n_parsed == 0, "a malformed model produces no predictions")
s3 = score(firm.labels, rb_broken.predictions)
check(s3.n_missing == 221, "metrics count all 221 as missing, not skipped")
check(s3.false_green_rate == 0.0, "a broken model gets no false-green credit")
check(
    s3.violation_recall == 0.0,
    "and no recall credit either, so formatting failure cannot be mistaken for safety",
)
check(abs(rb_broken.unparseable_rate - 1.0) < 1e-9, "unparseable rate is reported separately")

# ── cost probe ──────────────────────────────────────────────────────────────
print("\ncost probe")
est = estimate_cost(firm, obs, batch_size=40)
check(est["n_pairs"] == 221, "probe counts 221 pairs")
check(est["n_batches"] == 6, "probe counts 6 batches")
check(est["est_input_tokens"] > 0, "probe estimates input tokens without any API call")
check(est["prompt_version"] == "1.1.0", "probe records the prompt version")

# ── prompt v1.1 guarantees (each one is a v1.0 pilot defect) ─────────────────
print("\nprompt v1.1 guarantees")
_all_ids = [p.pair_id for p in firm.pairs]
_up_all = "".join(user_prompt(firm, obs, _all_ids[i:i + 12]) for i in range(0, len(_all_ids), 12))
check(all(f"- {rid}\n" in _up_all for rid in {p.rule_id for p in firm.pairs}),
      "every anchor rule reaches the prompt WITH a definition block")
_raised = False
try:
    user_prompt(firm, rb.obligations, [p.pair_id for p in firm.pairs if p.rule_id == "lca.expiration"])
except ValueError:
    _raised = True
check(_raised, "a pair whose rule has no definition is a hard error, not a silent omission")
check("information needed:" in _up_all and "requires:" not in _up_all,
      "obligations show verbatim 'information needed' prose, not the v1 token list")
for _v in (ABSTAIN_OFFERED, ABSTAIN_WITHHELD):
    _sp = " ".join(system_prompt(firm, _v).split())
    check("Match them by meaning" in _sp and "Reference knowledge is not evidence" in _sp,
          f"both reading rules are present in {_v} (identical across the ablation)")
_ne = " ".join(system_prompt(firm, ABSTAIN_OFFERED).split())
check("firm-specific information" in _ne and "is ABSENT from the exports" not in _ne,
      "needs_evidence is defined by the firm's records, not by field names")
_ravi = user_prompt(firm, obs, ["i9.section2.timeliness::Ravi Anand"])
check("3 business days" in _ravi and "section2_signed_date" in _ravi,
      "the clearest planted violation's rule text and evidence column both reach the prompt")


# ── quota resume: the multi-day path ───────────────────────────────────────
print("\nquota resume + circuit breaker")
import json as _json, tempfile  # noqa: E402
from nofalsegreen.subset import subset_firm  # noqa: E402
from baselines.llm import Usage as _U  # noqa: E402

_sub = subset_firm(firm, rb.rule_regimes())
_truth = _sub.label_index()


class _DiesAfter:
    """Answers correctly for n calls then raises, like a quota stop."""

    name = "dying-mock"

    def __init__(self, n: int):
        self.n, self.calls = n, 0

    def complete(self, system, user, max_tokens):
        self.calls += 1
        if self.calls > self.n:
            raise RuntimeError("simulated provider failure")
        ids = re.findall(r"^([A-Za-z0-9_.\-]+::[^\t\n]+)\t", user, re.M)
        return "\n".join(f"{i}\t{_truth[i].verdict.value}\t-" for i in ids), _U(100, 50, 1, 0.0)


with tempfile.TemporaryDirectory() as _td:
    _cache = Path(_td) / "c.json"
    _n_batches = -(-len(_sub.pairs) // 12)

    _d1 = _DiesAfter(4)
    _r1 = run_firm(_d1, _sub, obs, variant=ABSTAIN_OFFERED, batch_size=12, cache_path=_cache)
    check(len(_json.loads(_cache.read_text())) == 4,
          "day 1 caches exactly its successful batches")
    check(_d1.calls == 7,
          f"circuit breaker stops after 3 consecutive failures (got {_d1.calls} calls)")
    check(_r1.n_failed_batches == 3, "failed batches are counted, not hidden")

    _d2 = _DiesAfter(999)
    _r2 = run_firm(_d2, _sub, obs, variant=ABSTAIN_OFFERED, batch_size=12, cache_path=_cache)
    check(_d2.calls == _n_batches - 4,
          f"day 2 re-requests only the missing batches ({_d2.calls} of {_n_batches})")
    check(_r2.n_parsed == len(_sub.pairs), "day 2 completes the firm")
    _s2 = score(_sub.labels, _r2.predictions)

    # A cache written under a different prompt version must be ignored.
    _stale = {k.replace("1.1.0|", "1.0.0|", 1): v for k, v in _json.loads(_cache.read_text()).items()}
    _cache.write_text(_json.dumps(_stale))
    _d3 = _DiesAfter(999)
    run_firm(_d3, _sub, obs, variant=ABSTAIN_OFFERED, batch_size=12, cache_path=_cache)
    check(_d3.calls == _n_batches,
          f"replies cached under another prompt version are NOT reused ({_d3.calls} fresh calls)")
    check(_s2.violation_recall == 1.0, "a resumed run scores the same as an unbroken one")
    check(_s2.false_green_rate == 0.0, "resumed run has zero false green")


print("\nempty and capped replies are re-requested, bounded")


class _Flaky:
    """Returns `bad` (empty or capped) replies on the listed call numbers."""

    name = "flaky-mock"

    def __init__(self, bad_calls: set[int], kind: str):
        self.bad, self.kind, self.calls = bad_calls, kind, 0

    def complete(self, system, user, max_tokens):
        self.calls += 1
        if self.calls in self.bad:
            if self.kind == "empty":
                return "", _U(100, 50, 1, 0.0)
            if self.kind == "length":
                # Cut off by an upstream limit well below our max_tokens.
                return "We are given a task to evaluate", _U(100, 8559, 1, 0.0, "length")
            return "cut off mid-trace", _U(100, max_tokens, 1, 0.0)
        ids = re.findall(r"^([A-Za-z0-9_.\-]+::[^\t\n]+)\t", user, re.M)
        return "\n".join(f"{i}\t{_truth[i].verdict.value}\t-" for i in ids), _U(100, 50, 1, 0.0)


_nb = -(-len(_sub.pairs) // 12)
with tempfile.TemporaryDirectory() as _td:
    _f = _Flaky({1, 3}, "empty")
    _rf = run_firm(_f, _sub, obs, variant=ABSTAIN_OFFERED, batch_size=12,
                   cache_path=Path(_td) / "c.json")
    check(_f.calls == _nb + 2, f"each empty reply is re-requested once ({_f.calls} calls)")
    check(_rf.n_parsed == len(_sub.pairs), "recovered batches are fully parsed")
    check(_rf.n_incomplete_calls == 2 and _rf.n_unrecovered_batches == 0,
          "incomplete calls counted, none unrecovered")
    check(len(_json.loads((Path(_td) / "c.json").read_text())) == _nb,
          "only the complete reply is cached")

with tempfile.TemporaryDirectory() as _td:
    _f = _Flaky({1, 2, 3}, "cap")
    _rf = run_firm(_f, _sub, obs, variant=ABSTAIN_OFFERED, batch_size=12,
                   cache_path=Path(_td) / "c.json")
    check(_f.calls == _nb + 2, f"a batch gets at most 3 attempts ({_f.calls} calls)")
    check(_rf.n_unrecovered_batches == 1 and _rf.n_truncated_calls == 3,
          "a batch capped three times is counted unrecovered, each cap counted")
    check(_rf.n_parsed == len(_sub.pairs) - 12, "its pairs are left missing, never guessed")

with tempfile.TemporaryDirectory() as _td:
    _f = _Flaky({2}, "length")
    _rf = run_firm(_f, _sub, obs, variant=ABSTAIN_OFFERED, batch_size=12,
                   cache_path=Path(_td) / "c.json")
    check(_f.calls == _nb + 1 and _rf.n_incomplete_calls == 1,
          "a reply the provider cut off below our cap (finish=length) is re-requested")
    check(all(v.get("finish_reason") != "length"
              for v in _json.loads((Path(_td) / "c.json").read_text()).values()),
          "a cut-off reply is never cached")

print(f"\n{'PASS' if failed == 0 else 'FAIL'} — {passed} ok, {failed} failed")
sys.exit(1 if failed else 0)
