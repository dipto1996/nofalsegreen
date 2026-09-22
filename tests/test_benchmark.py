"""Test suite. Run: python3 tests/test_benchmark.py

House style matches the source project: plain asserts, one verdict line, a
non-zero exit on failure. No test framework dependency.
"""

from __future__ import annotations

import collections
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from baselines.trivial import REGISTRY
from nofalsegreen import northwind
from nofalsegreen.generator import FirmGenerator, GeneratorConfig
from nofalsegreen.metrics import score
from nofalsegreen.rulebook import Rulebook
from nofalsegreen.schema import Label, Prediction, Severity, Verdict

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


# ── rulebook ────────────────────────────────────────────────────────────────
print("rulebook")
rb = Rulebook.load(ROOT / "rulebook" / "rulebook.json")
check(len(rb.obligations) == 190, f"190 obligations loaded (got {len(rb.obligations)})")
check(all(o.citation for o in rb.obligations), "every obligation carries a citation")
check(all(o.evidence_required for o in rb.obligations), "every obligation declares required evidence")
check(len(rb.regimes()) == 10, f"10 regimes (got {len(rb.regimes())})")
check(len({o.rule_id for o in rb.obligations}) == len(rb.obligations), "rule ids are unique")

# ── anchor firm ─────────────────────────────────────────────────────────────
print("\nanchor firm")
firm = northwind.load(ANCHOR, ANCHOR / "expectations.json")
counts = collections.Counter(l.verdict.value for l in firm.labels)
check(len(firm.pairs) == 221, f"221 pairs (got {len(firm.pairs)})")
check(counts["fail"] == 20, f"20 planted violations (got {counts['fail']})")
check(counts["needs_evidence"] == 201, f"201 evidence requests (got {counts['needs_evidence']})")
check(
    counts["needs_evidence"] > counts["fail"],
    "abstention is the majority class (the benchmark's defining property)",
)
check(len(firm.sources) == 11, f"11 source exports (got {len(firm.sources)})")
check(all(p.exists() for p in firm.sources.values()), "every declared source file exists")
check(
    len({l.pair_id for l in firm.labels}) == len(firm.labels),
    "no duplicate pair in the ground truth",
)
check(
    all(l.severity is not Severity.URGENT for l in firm.labels if l.verdict is Verdict.NEEDS_EVIDENCE),
    "no evidence request is marked urgent (an unassessed duty is not a known breach)",
)

# ── metrics ─────────────────────────────────────────────────────────────────
print("\nmetrics")
labels = [
    Label("r::a", Verdict.FAIL, "planted_violation", Severity.HIGH),
    Label("r::b", Verdict.NEEDS_EVIDENCE, "withheld_evidence"),
    Label("r::c", Verdict.NEEDS_EVIDENCE, "withheld_evidence"),
    Label("r::d", Verdict.PASS, "planted_control"),
]
unsafe = score(labels, [
    Prediction("r::a", Verdict.FAIL), Prediction("r::b", Verdict.PASS),
    Prediction("r::c", Verdict.PASS), Prediction("r::d", Verdict.PASS),
])
check(unsafe.false_green_rate == 1.0, "false green rate is 1.0 when all withheld pairs pass")
check(unsafe.violation_recall == 1.0, "that same unsafe system still scores perfect recall")
check(unsafe.false_alarm_rate == 0.0, "and zero false alarms")

safe = score(labels, [
    Prediction("r::a", Verdict.FAIL), Prediction("r::b", Verdict.NEEDS_EVIDENCE),
    Prediction("r::c", Verdict.NEEDS_EVIDENCE), Prediction("r::d", Verdict.PASS),
])
check(safe.false_green_rate == 0.0, "false green rate is 0.0 for a correct system")
check(safe.abstention_f1 == 1.0, "abstention F1 is 1.0 for a correct system")

partial = score(labels, [Prediction("r::a", Verdict.FAIL)])
check(partial.n_missing == 3, "unanswered pairs are counted, not skipped")
check(
    partial.violation_recall == 1.0 and partial.abstention_recall == 0.0,
    "declining to answer cannot raise the abstention score",
)

# ── baselines ───────────────────────────────────────────────────────────────
print("\nbaselines on the anchor firm")
regimes = rb.rule_regimes()
results = {name: score(firm.labels, fn(firm), rule_regimes=regimes) for name, fn in REGISTRY.items()}
check(results["oracle"].false_green_rate == 0.0, "oracle: zero false green")
check(results["oracle"].violation_recall == 1.0, "oracle: full violation recall (task is solvable)")
check(results["always_pass"].false_green_rate == 1.0, "always_pass: false green rate 1.0")
check(results["always_pass"].false_alarm_rate == 0.0,
      "always_pass: zero false alarms despite being maximally unsafe")
check(results["always_abstain"].abstention_f1 > 0.9,
      "always_abstain: high abstention F1 while detecting nothing (metric is gameable alone)")
check(results["always_abstain"].violation_recall == 0.0,
      "always_abstain: zero violation recall, which is what exposes it")
check(results["always_fail"].violation_recall == 1.0, "always_fail: full recall")
check(results["always_fail"].violation_precision < 0.2, "always_fail: precision collapses")

# ── generator ───────────────────────────────────────────────────────────────
print("\ngenerator")
gen = FirmGenerator(rb, GeneratorConfig(n_workers=10))
out = ROOT / ".test-tmp"
a = gen.generate(42, out / "a")
b = gen.generate(42, out / "b")
c = gen.generate(43, out / "c")
check([l.verdict for l in a.labels] == [l.verdict for l in b.labels], "same seed gives same labels")
check(a.to_json() == b.to_json(), "same seed gives byte-identical firm.json")
check([l.verdict for l in a.labels] != [l.verdict for l in c.labels], "different seed gives different labels")
check(a.provenance["contains_real_personal_data"] is False, "provenance asserts no real personal data")
gcounts = collections.Counter(l.verdict.value for l in a.labels)
check(gcounts["needs_evidence"] > gcounts["fail"], "generated firm also has abstention-heavy labels")
check(
    score(a.labels, REGISTRY["oracle"](a)).false_green_rate == 0.0,
    "oracle scores zero false green on a generated firm",
)
check(
    score(a.labels, REGISTRY["always_pass"](a)).false_green_rate == 1.0,
    "always_pass scores 1.0 false green on a generated firm",
)

# every generated label must be justified by a recorded basis
bases = {l.basis for l in a.labels}
check(
    bases <= {"planted_violation", "planted_control", "withheld_evidence", "not_applicable"},
    f"every label carries a known basis (got {sorted(bases)})",
)



# ── declared evaluation subset ──────────────────────────────────────────────
print("\ndeclared subset")
from nofalsegreen.subset import DEFAULT_SIZE, SUBSET_SEED, subset_firm  # noqa: E402

rr = rb.rule_regimes()
sub = subset_firm(firm, rr)
sub_counts = collections.Counter(l.verdict.value for l in sub.labels)
full_counts = collections.Counter(l.verdict.value for l in firm.labels)

check(sub_counts["fail"] == full_counts["fail"],
      f"subset keeps EVERY planted violation ({sub_counts['fail']}/{full_counts['fail']})")
check(sub_counts["needs_evidence"] > sub_counts["fail"],
      "abstention is still the majority class in the subset")
ratio = sub_counts["needs_evidence"] / sub_counts["fail"]
check(ratio >= 5.0, f"class ratio stays skewed toward abstention (got {ratio:.1f}:1)")
check(len(sub.pairs) <= DEFAULT_SIZE, f"subset respects its size budget ({len(sub.pairs)})")

full_regimes = {rr.get(p.rule_id, "unknown") for p in firm.pairs}
sub_regimes = {rr.get(p.rule_id, "unknown") for p in sub.pairs}
check(full_regimes == sub_regimes, "every regime present in the firm survives into the subset")

again = subset_firm(firm, rr)
check([p.pair_id for p in sub.pairs] == [p.pair_id for p in again.pairs],
      "subset selection is deterministic")
check(sub.provenance["subset_seed"] == SUBSET_SEED, "subset records its seed")
check(sub.provenance["subset_of"] == firm.firm_id, "subset records its parent firm")
check(all(l.pair_id in {p.pair_id for p in sub.pairs} for l in sub.labels),
      "subset labels match subset pairs exactly")

# The subset must not make the task easier: an unsafe system still scores 1.0.
from baselines.trivial import always_pass as _ap  # noqa: E402
check(score(sub.labels, _ap(sub)).false_green_rate == 1.0,
      "always_pass still scores false-green 1.000 on the subset")
check(score(sub.labels, REGISTRY["oracle"](sub)).violation_recall == 1.0,
      "oracle still scores full recall on the subset")

print(f"\n{'PASS' if failed == 0 else 'FAIL'} — {passed} ok, {failed} failed")
sys.exit(1 if failed else 0)
