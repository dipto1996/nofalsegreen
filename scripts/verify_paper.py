"""Check every quantitative claim in docs/PAPER.md against the artifacts.

Any number in the paper that this script cannot confirm is a number that must
not be in the paper.
"""

from __future__ import annotations

import collections
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from baselines.trivial import REGISTRY  # noqa: E402
from nofalsegreen import northwind  # noqa: E402
from nofalsegreen.metrics import score  # noqa: E402
from nofalsegreen.rulebook import Rulebook  # noqa: E402

ANCHOR = ROOT / "data" / "firms" / "northwind-robotics"
paper = (ROOT / "docs" / "PAPER.md").read_text()
readme = (ROOT / "README.md").read_text()
results = json.loads((ROOT / "docs" / "results.json").read_text())

ok = bad = 0


def claim(cond: bool, label: str) -> None:
    global ok, bad
    if cond:
        print(f"  ok   {label}")
        ok += 1
    else:
        print(f"  FAIL {label}")
        bad += 1


rb = Rulebook.load(ROOT / "rulebook" / "rulebook.json")
firm = northwind.load(ANCHOR, ANCHOR / "expectations.json")
counts = collections.Counter(l.verdict.value for l in firm.labels)
regimes = rb.rule_regimes()
scored = {n: score(firm.labels, fn(firm), rule_regimes=regimes) for n, fn in REGISTRY.items()}

print("rulebook claims")
claim("190 citable obligations" in paper or "190 obligations" in paper, "paper says 190 obligations")
claim(len(rb.obligations) == 190, "rulebook actually has 190")
claim("196" in paper and "unreconciled" in paper.lower(), "paper discloses the 196/190 discrepancy")
per_regime = rb.regimes()
for regime, n in [("i9-everify", 26), ("lca-dol", 23), ("paf", 15), ("wage-prevailing", 21),
                  ("h1b-status", 16), ("i129-supplement", 11), ("l1-visa", 21),
                  ("f1-opt-stem", 15), ("fdns-sitevisit", 14), ("deadlines-penalties", 28)]:
    claim(per_regime.get(regime) == n, f"regime {regime} = {n}")
claim(sum(per_regime.values()) == 190, "regime counts sum to 190")

print("\nanchor firm claims")
claim("221" in paper, "paper says 221 pairs")
claim(len(firm.pairs) == 221, "anchor firm has 221 pairs")
claim(counts["fail"] == 20, "20 planted violations")
claim(counts["needs_evidence"] == 201, "201 evidence requests")
claim("twelve workers" in paper, "paper says twelve workers")
claim("93 data rows" in paper, "paper says 93 source data rows")
csvs = sorted(ANCHOR.glob("*.csv"))
rows = sum(max(0, len(p.read_text().strip().splitlines()) - 1) for p in csvs)
claim(len(csvs) == 11, f"11 source exports on disk (got {len(csvs)})")
claim(rows == 93, f"93 data rows across exports (got {rows})")

print("\nsweep claims")
claim(results["n_firms"] == 31, "31 firms")
claim(results["n_pairs"] == 57701, f"57,701 pairs (got {results['n_pairs']})")
claim(results["n_withheld"] == 26115, f"26,115 withheld (got {results['n_withheld']})")
claim(results["n_planted_violations"] == 6890, f"6,890 planted violations (got {results['n_planted_violations']})")
share = results["n_withheld"] / results["n_pairs"]
claim(abs(share - 0.453) < 0.0005, f"withheld share 45.3% (got {share:.1%})")
claim("57,701" in paper and "26,115" in paper and "45.3" in paper, "paper quotes these figures")
claim("6,890" in paper, "paper quotes 6,890 planted violations")

print("\ntable 7.1 vs results.json")
expect = {
    "always_pass":    (1.000, 0.000, 0.000, 0.000, 0.000),
    "always_abstain": (0.000, 0.000, 0.000, 0.968, 0.632),
    "always_fail":    (0.000, 1.000, 0.119, 0.968, 0.000),
    "oracle":         (0.000, 1.000, 1.000, 0.000, 1.000),
}
for name, (fgr, rec, prec, fa, af1) in expect.items():
    s = results["systems"][name]
    claim(abs(s["false_green_rate"]["mean"] - fgr) < 0.001, f"{name} FGR = {fgr:.3f}")
    claim(abs(s["violation_recall"]["mean"] - rec) < 0.001, f"{name} recall = {rec:.3f}")
    claim(abs(s["violation_precision"]["mean"] - prec) < 0.001, f"{name} precision = {prec:.3f}")
    claim(abs(s["false_alarm_rate"]["mean"] - fa) < 0.001, f"{name} false alarm = {fa:.3f}")
    claim(abs(s["abstention_f1"]["mean"] - af1) < 0.001, f"{name} abstention F1 = {af1:.3f}")

print("\nanchor-firm specific claims in the text")
claim(scored["always_pass"].n_false_green == 201,
      "always_pass reports all 201 anchor evidence requests as satisfied")
claim(scored["always_pass"].false_alarm_rate == 0.0, "always_pass raises zero false alarms on anchor")
claim(abs(scored["always_abstain"].abstention_f1 - 0.953) < 0.001,
      f"always_abstain hits 0.953 abstention F1 on anchor (got {scored['always_abstain'].abstention_f1:.3f})")
claim("0.953" in paper, "paper quotes the 0.953 anchor figure")
claim("0.632" in paper, "paper quotes the 0.632 swept figure")
claim(scored["oracle"].false_green_rate == 0.0 and scored["oracle"].violation_recall == 1.0,
      "oracle is perfect on anchor")

print("\nhonesty checks")
claim("[TO RUN]" in paper, "unrun experiments are marked, not estimated")
claim(paper.count("[TO RUN]") >= 3, "each unrun section is marked")
claim("have not yet been run" in paper or "has not been run" in paper or "not been conducted" in paper,
      "paper states plainly that LM experiments are unrun")
claim(results["note"].startswith("Trivial baselines only"), "results.json disclaims LM results")
claim("No language-model results are reported" in readme, "README disclaims LM results")
for forbidden in ["250-rule", "237-rule", "612 cases", "768 checks"]:
    claim(forbidden not in paper, f"paper avoids unverified figure '{forbidden}'")
claim("not an independent baseline" in paper or "do not" in paper and "acceptance gate" in paper,
      "paper excludes the co-developed engine as a baseline")

# no stray percentages that we have not verified
pcts = set(re.findall(r"\b\d+\.\d\s?%", paper))
claim(pcts <= {"45.3%"}, f"only verified percentages appear (found {sorted(pcts)})")

print(f"\n{'PASS' if bad == 0 else 'FAIL'} — {ok} verified, {bad} unverified")
sys.exit(1 if bad else 0)
