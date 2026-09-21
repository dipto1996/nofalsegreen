"""Tests for the language-model harness.

The harness is tested with mock models whose failure signature is known in
advance, so we can assert the harness MEASURES what it claims to measure before
any money is spent on real API calls.

Run: python3 tests/test_llm_harness.py
"""

from __future__ import annotations

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
obs = rb.obligations
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
check(est["prompt_version"] == "1.0.0", "probe records the prompt version")

print(f"\n{'PASS' if failed == 0 else 'FAIL'} — {passed} ok, {failed} failed")
sys.exit(1 if failed else 0)
