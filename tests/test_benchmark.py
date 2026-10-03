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
check(len(rb.obligations) == 194,
      f"194 unique manifest rule ids from 196 entries (got {len(rb.obligations)})")
check(len(rb.by_id()) == 211, f"211 resolvable ids incl. 17 engine rules (got {len(rb.by_id())})")
_anchor_rules = {p.rule_id for p in northwind.load(ANCHOR, ANCHOR / "expectations.json").pairs}
check(_anchor_rules <= set(rb.by_id()),
      f"every anchor rule id has a definition (missing: {sorted(_anchor_rules - set(rb.by_id()))[:3]})")
check(all(o.data_needed for o in rb.all_rules()), "every rule carries verbatim 'information needed' prose")
check(not any("Dateemployer" in o.data_needed or "CompletionDateemployer" in o.data_needed
              for o in rb.all_rules()),
      "no v1-style mangled evidence tokens survive")
check(all(o.alias_of in {m.rule_id for m in rb.obligations}
          for o in rb.engine_rules if o.alias_of),
      "every engine alias points at a real manifest rule")
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



# generator v2: every record is internally consistent, across many seeds
import csv as _csv  # noqa: E402
from datetime import date as _date  # noqa: E402
from nofalsegreen.generator import add_business_days as _abd  # noqa: E402
_bad = []
for _seed in range(1, 41):
    _f = gen.generate(_seed, out / f"v2_{_seed}")
    _d = out / f"v2_{_seed}"
    _lab = {l.pair_id: l for l in _f.labels}
    if (_d / "i9_record_export.csv").exists() and "i9_record_export" in _f.sources:
        for r in _csv.DictReader(open(_d / "i9_record_export.csv")):
            s1, s2 = _date.fromisoformat(r["section1SignDate"]), _date.fromisoformat(r["section2EmployerSignDate"])
            st = _date.fromisoformat(r["firstDayOfEmployment"])
            if s1 > s2:
                _bad.append((_seed, r["employeeNumber"], "s1 after s2"))
            lab2 = _lab[f"i9.section2.timeliness::{r['employeeNumber']}"]
            on_time = s2 <= _abd(st, 3)
            if on_time != (lab2.verdict.value == "pass"):
                _bad.append((_seed, r["employeeNumber"], "s2 label vs data"))
            lab1 = _lab[f"i9.section1.timeliness::{r['employeeNumber']}"]
            if (s1 <= st) != (lab1.verdict.value == "pass"):
                _bad.append((_seed, r["employeeNumber"], "s1 label vs data"))
    if "payroll_register" in _f.sources:
        for r in _csv.DictReader(open(_d / "payroll_register.csv")):
            if _date.fromisoformat(r["payDate"]) > _date.fromisoformat(_f.as_of):
                _bad.append((_seed, r["employeeNumber"], "pay after as_of"))
check(not _bad, f"generator v2 records consistent with labels over 40 seeds ({_bad[:3]})")

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


# ── declared label views (declared before any v1.1 result was read) ─────────
print("\nlabel views")
from nofalsegreen.labelviews import MEMO_ABSENCE, PROSPECTIVE, alert_report, apply_view  # noqa: E402
from nofalsegreen.schema import Prediction  # noqa: E402

_fail_ids = {l.pair_id for l in firm.labels if l.verdict is Verdict.FAIL}
check(MEMO_ABSENCE <= _fail_ids and len(MEMO_ABSENCE) == 5, "the 5 memo pairs are real planted violations")
check(PROSPECTIVE <= _fail_ids and len(PROSPECTIVE) == 5, "the 5 prospective pairs are real planted violations")
check(not (MEMO_ABSENCE & PROSPECTIVE), "the two groups do not overlap")

_eng, _eng_alerts = apply_view(firm.labels, "engine")
check(_eng == list(firm.labels) and _eng_alerts == [], "engine view is the labels exactly as authored")

_st, _st_alerts = apply_view(firm.labels, "strict")
_stc = collections.Counter(l.verdict.value for l in _st)
check(len(_st) == 216 and len(_st_alerts) == 5, "strict view scores 216 pairs, sets 5 aside as alerts")
check(_stc["fail"] == 10, f"strict view keeps the 10 already-breached violations (got {_stc['fail']})")
check(_stc["needs_evidence"] == 206, "strict view: 201 evidence requests + 5 relabelled memos")
check(all(l.verdict is Verdict.NEEDS_EVIDENCE for l in _st if l.pair_id in MEMO_ABSENCE),
      "memo pairs become needs_evidence in the strict view")
check(firm.labels[0].verdict is not None and
      sum(1 for l in firm.labels if l.verdict is Verdict.FAIL) == 20,
      "applying a view never mutates the original labels")

_sub_st, _sub_alerts = apply_view(sub.labels, "strict")
check(sum(1 for l in _sub_st if l.verdict is Verdict.FAIL) == 10 and len(_sub_alerts) == 5,
      "on the 140-pair subset the strict view also keeps 10 violations and 5 alerts")

_mock = [Prediction(a.pair_id, Verdict.FAIL) for a in _sub_alerts[:3]] + \
        [Prediction(a.pair_id, Verdict.PASS) for a in _sub_alerts[3:4]]
_ar = alert_report(_mock, _sub_alerts)
check(_ar["verdicts"] == {"fail": 3, "pass": 1, "no answer": 1},
      "alert report counts each verdict and an unanswered alert as 'no answer'")

# A model that abstains on the memo pairs is penalised under engine, rewarded under strict.
_abst = [Prediction(l.pair_id, Verdict.NEEDS_EVIDENCE if l.pair_id in MEMO_ABSENCE else l.verdict)
         for l in sub.labels]
_se = score(sub.labels, _abst)
_ss = score(_sub_st, [x for x in _abst if x.pair_id in {l.pair_id for l in _sub_st}])
check(_se.violation_recall == 0.75 and _ss.violation_recall == 1.0,
      "abstaining on unevidenced memos costs recall under engine (0.75) and none under strict (1.0)")

print(f"\n{'PASS' if failed == 0 else 'FAIL'} — {passed} ok, {failed} failed")
sys.exit(1 if failed else 0)
