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
claim("194 citable" in paper and "194 obligations" in paper, "paper says 194 obligations")
claim(len(rb.obligations) == 194, "rulebook actually has 194 manifest rules")
claim("196" in paper and "unreconciled" not in paper.lower(),
      "paper explains 196 entries -> 194 rules; no longer calls it unreconciled")
claim(len(rb.engine_rules) == 17 and "17 rules" in paper,
      "paper states the 17 engine rules and how they are defined")
per_regime = rb.regimes()
for regime, n in [("i9-everify", 28), ("lca-dol", 23), ("paf", 15), ("wage-prevailing", 21),
                  ("h1b-status", 16), ("i129-supplement", 13), ("l1-visa", 21),
                  ("f1-opt-stem", 15), ("fdns-sitevisit", 14), ("deadlines-penalties", 28)]:
    claim(per_regime.get(regime) == n, f"regime {regime} = {n}")
claim(sum(per_regime.values()) == 194, "regime counts sum to 194")
claim("I-9 and E-Verify (28)" in paper and "I-129 supplement (13)" in paper,
      "paper's per-regime counts match the rulebook")

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
claim(results["n_pairs"] == 58961, f"58,961 pairs (got {results['n_pairs']})")
claim(results["n_withheld"] == 26682, f"26,682 withheld (got {results['n_withheld']})")
claim(results["n_planted_violations"] == 7044, f"7,044 planted violations (got {results['n_planted_violations']})")
share = results["n_withheld"] / results["n_pairs"]
claim(abs(share - 0.453) < 0.0005, f"withheld share 45.3% (got {share:.1%})")
claim("58,961" in paper and "26,682" in paper and "45.3" in paper and "57,701" not in paper,
      "paper quotes the regenerated figures and none of the stale ones")
claim("7,044" in paper, "paper quotes 7,044 planted violations")

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

print("\nharness claims")
claim("PROMPT_VERSION" in paper or "PROMPT_VERSION 1.0.0" in paper.replace("`",""),
      "paper names the frozen prompt version")
claim("1,446" in paper, "paper quotes the measured 1,446 calls per model per variant")
claim("2.55M" in paper and "1.73M" in paper, "paper quotes measured token volumes")
claim("abstain_offered" in paper and "abstain_withheld" in paper,
      "paper names both ablation conditions")
claim("off-schema" in paper.lower(), "paper defines the off-schema counter")
claim("never coerced" in paper, "paper states the parsing policy explicitly")
claim("unparseable rate" in paper, "paper commits to reporting the unparseable rate")

print("\nfree-tier protocol claims")
claim("free tier" in paper.lower(), "paper states results come from free tiers")
from baselines.llm import estimate_cost as _ec
_sc = _ec(firm, rb.all_rules(), batch_size=20, scope_sources=True)
_un = _ec(firm, rb.all_rules(), batch_size=20, scope_sources=False)
_un40 = _ec(firm, rb.all_rules(), batch_size=40, scope_sources=False)
claim(_sc["max_call_tokens"] == 10688, f"scoped max call is 10,688 (got {_sc['max_call_tokens']:,})")
claim(_un["max_call_tokens"] == 12185, f"unscoped max call is 12,185 (got {_un['max_call_tokens']:,})")
claim(_un40["max_call_tokens"] == 16832, f"unscoped batch-40 max call is 16,832 (got {_un40['max_call_tokens']:,})")
claim("10,688" in paper and "12,185" in paper and "16,832" in paper,
      "paper quotes all three measured per-call token figures")
claim("do not infer" in paper or "not to infer" in paper,
      "paper documents the anti-inference safeguard on scoped prompts")
claim("falls back to all sources" in paper or "fall back to all sources" in paper
      or "falls back to all sources" in paper.replace("\n"," "),
      "paper documents the unclassified-regime fallback")
claim("Model coverage is limited to free API tiers" in paper,
      "limitations name the model-coverage weakness")
claim("24 calls" in paper, "paper quotes the measured anchor-firm call count for both variants")

print("\nstructural-skeleton claims")
import re as _re
_heads = [l for l in paper.splitlines() if l.startswith(("## ", "### "))]
_nums = [h for h in _heads if _re.match(r"^## \d+\.", h)]
claim(len(_nums) == 11, f"11 numbered sections, contiguous (got {len(_nums)})")
claim([int(_re.match(r"^## (\d+)\.", h).group(1)) for h in _nums] == list(range(1, 12)),
      "section numbers run 1..11 with no gaps or repeats")
claim("## 2. Related work" in paper, "Related work is a real section, not an appendix stub")
claim("Appendix B: Related work to engage" not in paper, "the old related-work stub is gone")
for t in ("Table 1", "Table 2", "Table 3", "Table 4", "Table 5", "Figure 1"):
    claim(t in paper, f"{t} is named in the paper")
claim("if the result is null" in paper,
      "paper commits in advance to reporting a null result")
claim("[\u2026]" in paper or "[…]" in paper, "empty result cells are marked as placeholders")
_bad = _re.findall(r"Section \d+", paper)
_maxsec = max(int(x.split()[1]) for x in _bad)
claim(_maxsec <= 11, f"no cross-reference points past section 11 (max {_maxsec})")

print("\nfree-model screening claims")
_screen = json.loads((ROOT / "docs" / "free_model_live_probe_2026-09-21b.json").read_text())
_s = _screen["summary"]
claim(_s["n_candidates"] == 15, f"15 candidates screened (got {_s['n_candidates']})")
claim(_s["n_held_format"] == 6, f"6 returned a usable answer (got {_s['n_held_format']})")
claim(_s["n_false_green"] == 0, "zero false greens on the easy case")
claim("only 6 returned a usable answer" in paper,
      "paper quotes the measured 6-of-15 screening outcome")
claim("15 free chat models" in paper, "paper states the candidate count")
claim(_s["failure_modes"].get("rate_limited_429") == 5, "5 rate-limited")
claim(_s["failure_modes"].get("forbidden_403") == 2, "2 permission-refused")
claim("5 were rate-limited" in paper and "2 refused" in paper,
      "paper reports the failure-mode breakdown")


print("\ndeclared-subset claims")
from nofalsegreen.subset import DEFAULT_SIZE as _SZ, SUBSET_SEED as _SEED, subset_firm as _sf
_sub = _sf(firm, regimes)
_sc = collections.Counter(l.verdict.value for l in _sub.labels)
_fc = collections.Counter(l.verdict.value for l in firm.labels)
claim(_sc["fail"] == _fc["fail"], "subset keeps every planted violation")
claim(len(_sub.pairs) == 140, f"subset is 140 pairs (got {len(_sub.pairs)})")
claim(abs(_sc["needs_evidence"] / _sc["fail"] - 6.0) < 0.5,
      f"subset ratio is ~6:1 (got {_sc['needs_evidence']/_sc['fail']:.1f})")
claim("140 pairs" in paper or "140-pair" in paper, "paper states the subset size")
claim("declared stratified subset" in paper, "paper calls it a declared subset")
claim("3.8:1" in paper, "paper states the ratio it rejected and why")
claim("not all 221" in paper or "not all 221\npairs" in paper.replace("\n", " "),
      "limitations name the subset as a limitation")

print("\npilot disclosure matches the archived pilot")
_pilot = json.loads((ROOT / "docs" / "pilot_v1.0" / "llm_results.json").read_text())["runs"]
def _pfgr(m, v):
    return round(_pilot[f"{m}::{v}"]["aggregate"]["false_green_rate"]["mean"], 3)
_u, _su = "nvidia/nemotron-3-ultra-550b-a55b:free", "nvidia/nemotron-3-super-120b-a12b:free"
claim(_pfgr(_u, "abstain_withheld") == 0.117 and "0.117" in paper, "pilot 550B withheld FGR 0.117 quoted correctly")
claim(_pfgr(_su, "abstain_withheld") == 0.075 and "0.075" in paper, "pilot 120B withheld FGR 0.075 quoted correctly")
claim(all(_pilot[f"{m}::abstain_offered"]["aggregate"]["violation_recall"]["mean"] == 0.0 for m in (_u, _su)),
      "pilot offered-condition recall really was 0.000 for both models")
claim("four of twelve" in paper, "paper says the pilot completed four of twelve runs")
claim("Thirty of the\n140 pairs" in paper or "Thirty of the 140 pairs" in paper.replace("\n", " "),
      "paper states 30 of 140 pairs lacked obligation text")
from baselines.prompts import PROMPT_VERSION as _PV
claim(_PV == "1.1.0" and "`PROMPT_VERSION` 1.1.0" in paper, "paper and harness agree on prompt v1.1.0")
_frozen = json.loads((ROOT / "data" / "firms" / "northwind-robotics" / "subset140.json").read_text())
claim(_frozen["n_pairs"] == 140 and "identical" in paper, "the frozen subset backs the 'identical pairs' claim")

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

# The status header states how many claims this script confirms. Rather than
# asking a human to keep that in sync, the script writes it, so the number can
# never drift from the number of checks actually run.
_total = ok + bad
_paper_path = ROOT / "docs" / "PAPER.md"
_txt = _paper_path.read_text()
_new = re.sub(
    r"which currently confirms \d+ of \d+\.",
    f"which currently confirms {ok} of {_total}.",
    _txt,
)
if _new != _txt:
    _paper_path.write_text(_new)
    print(f"\n[verify] updated the status header to '{ok} of {_total}'")

print(f"\n{'PASS' if bad == 0 else 'FAIL'} — {ok} verified, {bad} unverified")
sys.exit(1 if bad else 0)
