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

# Rebuild first: re-run every scorer from the retained replies (no API call) and require
# that each results file comes out byte-identical to the one the paper's numbers were
# checked against. Skip with --no-rebuild for a quick text-only pass.
REBUILD = [("score_study3.py",), ("study3_exploratory.py",), ("study3_robustness.py",),
           ("score_paraphrase.py",), ("score_study3c.py",), ("score_study4.py",), ("score_study4.py", "--study6"),
           ("score_study5.py",), ("score_study5.py", "--study6"), ("score_study7.py",), ("score_study8.py",),
           ("score_ai_pilot.py",), ("sweep.py", "--firms", "30"), ("score_views.py",), ("score_studies.py",),
           ("analysis.py",), ("labelcheck_compare.py",), ("certify_existing.py",), ("verify_study9_labels.py",),
           ("score_study9.py",), ("score_study10.py",), ("score_study11.py",), ("score_study12.py",),
           ("differential_contracts.py",), ("verify_study13_labels.py",), ("score_study13.py",), ("score_study13.py", "--r2"),
           ("power_study14.py",), ("score_study14.py",), ("power_study15.py",), ("score_study15.py",), ("score_study15.py", "--r2"),
           ("audit_study15_inputs.py",)]
REBUILT = {}
if "--no-rebuild" not in sys.argv:
    import hashlib
    import subprocess
    outs = [ROOT / "docs" / f for f in ("study3/results.json", "study3/exploratory.json", "study3/robustness.json",
                                        "study3b/results.json", "study3c/results.json", "study4/results.json",
                                        "study6/study4_results.json", "study5/results.json", "study6/study5_results.json",
                                        "study7/results.json", "study8/results.json", "ai_pilot_review/results.json",
                                        "results.json", "views_results.json", "studies_results.json",
                                        "analysis_results.json", "labelcheck_results.json",
                                        "existing_certificates.json", "study9/label_verification.json",
                                        "study9/results.json", "study10/results.json", "study11/results.json",
                                        "study12/results.json", "study9/differential.json", "study13/label_check.json",
                                        "study13/results.json", "study13/results_r2.json", "study14/power.json",
                                        "study14/results.json", "study15/power.json", "study15/results.json",
                                        "study15/results_r2.json", "study15/input_audit.json")]
    import os
    before = {f: hashlib.sha256(f.read_bytes()).hexdigest() if f.exists() else None for f in outs}
    # A scorer that fails leaves the old file in place, which would hash as "identical";
    # so delete each output first and require every scorer to exit cleanly.
    for f in outs:
        if f.exists():
            f.rename(f.with_suffix(".json.prev"))
    SCORER_FAILURES = []
    env = {**os.environ, "PYTHONHASHSEED": "0"}
    for args in REBUILD:
        r = subprocess.run([sys.executable, str(ROOT / "scripts" / args[0]), *args[1:]], cwd=ROOT,
                           capture_output=True, text=True, env=env)
        if r.returncode != 0:
            SCORER_FAILURES.append((" ".join(args), r.stderr.strip().splitlines()[-1:] if r.stderr else []))
    after = {f: hashlib.sha256(f.read_bytes()).hexdigest() if f.exists() else None for f in outs}
    for f in outs:
        prev = f.with_suffix(".json.prev")
        if not f.exists() and prev.exists():
            prev.rename(f)  # restore so the text checks below still run; the rebuild check fails
        elif prev.exists():
            prev.unlink()
    REBUILT = {f: (before[f], after[f]) for f in outs}


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

print("rebuild from retained replies")
if "--no-rebuild" not in sys.argv:
    claim(not SCORER_FAILURES, f"every scorer exited cleanly (failures: {SCORER_FAILURES})")
for _f, (_b, _a) in REBUILT.items():
    claim(_a is not None and _b == _a, f"{_f.relative_to(ROOT)} rebuilt byte-identical from retained replies")

print("rulebook claims")
claim("194 obligations" in paper, "paper says 194 obligations")
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

print("\nsweep claims (generator v2, recomputed)")
claim(results.get("generator") == "v2", "released-set figures come from generator v2")
claim(results["n_firms"] == 31, "31 firms")
_np, _nw, _nf = results["n_pairs"], results["n_withheld"], results["n_planted_violations"]
claim(f"{_np:,}" in paper and f"{_nw:,}" in paper and f"{_nw / _np:.1%}" in paper and f"{_nf:,}" in paper,
      f"paper quotes {_np:,} pairs, {_nw:,} withheld ({_nw / _np:.1%}), {_nf:,} violations")
claim("58,961" not in paper.replace("released-set size of 58,961 pairs", ""),
      "the withdrawn v1 size appears only where it is withdrawn")
claim("8 of 60" not in paper or "agreed with its labels on 8" in paper, "v1 blind-check result disclosed")
claim("table1-trivial" in paper, "Table 1 is generated, not hand-typed")
_t1 = paper[paper.index("BEGIN GENERATED: table1-trivial"):paper.index("END GENERATED: table1-trivial")]
for _n, _s in results["systems"].items():
    claim(f"`{_n}`" in _t1, f"Table 1 row for {_n}")
claim(results["systems"]["oracle"]["false_green_rate"]["mean"] == 0.0
      and results["systems"]["oracle"]["violation_recall"]["mean"] == 1.0, "oracle perfect on the release")
claim(results["systems"]["always_pass"]["false_alarm_rate"]["mean"] == 0.0
      and results["systems"]["always_pass"]["false_green_rate"]["mean"] == 1.0,
      "always_pass: no false alarm, every withheld pair a false green")

print("\nanchor-firm specific claims in the text")
claim(scored["always_pass"].n_false_green == 201,
      "always_pass reports all 201 anchor evidence requests as satisfied")
claim(scored["always_pass"].false_alarm_rate == 0.0, "always_pass raises zero false alarms on anchor")
claim(abs(scored["always_abstain"].abstention_f1 - 0.953) < 0.001,
      f"always_abstain hits 0.953 abstention F1 on anchor (got {scored['always_abstain'].abstention_f1:.3f})")
claim("0.953" in paper, "paper quotes the 0.953 anchor figure")
claim(f"{results['systems']['always_abstain']['abstention_f1']['mean']:.3f}" in paper,
      "paper quotes the swept always_abstain abstention F1")
claim(scored["oracle"].false_green_rate == 0.0 and scored["oracle"].violation_recall == 1.0,
      "oracle is perfect on anchor")

print("\nharness claims")
claim("PROMPT_VERSION" in paper or "PROMPT_VERSION 1.0.0" in paper.replace("`",""),
      "paper names the frozen prompt version")
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
claim("10,688" not in paper and "16,832" not in paper,
      "stale batch-20/40 token figures removed (every run used batch 12)")
claim("batches of 12 pairs" in paper, "paper states the batch size actually used")
claim("do not infer" in paper or "not to infer" in paper,
      "paper documents the anti-inference safeguard on scoped prompts")
claim("falls back to all sources" in paper or "fall back to all sources" in paper
      or "falls back to all sources" in paper.replace("\n"," "),
      "paper documents the unclassified-regime fallback")
claim("Model coverage is narrow" in paper,
      "limitations name the model-coverage weakness")
claim("12 calls per model and condition" in paper and "costs 24" in paper,
      "paper quotes the per-run call counts at batch 12 (Study 1: 12, Study 2: 24)")

print("\nstructural-skeleton claims")
import re as _re
_heads = [l for l in paper.splitlines() if l.startswith(("## ", "### "))]
_nums = [h for h in _heads if _re.match(r"^## \d+\.", h)]
claim(len(_nums) == 9, f"9 numbered sections, contiguous (got {len(_nums)})")
claim([int(_re.match(r"^## (\d+)\.", h).group(1)) for h in _nums] == list(range(1, 10)),
      "section numbers run 1..9 with no gaps or repeats")
claim("## 2. Related work" in paper, "Related work is a real section, not an appendix stub")
claim("Appendix B: Related work to engage" not in paper, "the old related-work stub is gone")
for t in ["Table %d" % i for i in range(1, 17)] + ["Figure %d" % i for i in range(1, 10)]:
    claim(t in paper, f"{t} is named in the paper")
claim("[\u2026]" not in paper and "[…]" not in paper, "no empty result cell remains")
_bad = _re.findall(r"Section \d+", paper)
_maxsec = max(int(x.split()[1]) for x in _bad)
claim(_maxsec <= 10, f"no cross-reference points past section 10 (max {_maxsec})")

print("\nfree-model screening claims")
_screen = json.loads((ROOT / "docs" / "free_model_live_probe_2026-09-21b.json").read_text())
_s = _screen["summary"]
claim(_s["n_candidates"] == 15, f"15 candidates screened (got {_s['n_candidates']})")
claim(_s["n_held_format"] == 6, f"6 returned a usable answer (got {_s['n_held_format']})")
claim(_s["n_false_green"] == 0, "zero false greens on the easy case")
claim("only 6 returned a usable answer" in paper.replace("\n", " "),
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

print("\nlabel-view declaration")
from nofalsegreen.labelviews import DECLARED_ON as _DO, MEMO_ABSENCE as _MA, PROSPECTIVE as _PR
claim(_DO in paper and "fixed before per-pair results were read" in paper
      and "six minutes after" in paper,
      "paper states when the views were fixed, and what had been printed before")
claim(len(_MA) == 5 and len(_PR) == 5, "5 memo + 5 prospective pairs, as the paper says")
claim("Engine view, the headline" in paper, "engine view is named as the headline")
claim("denominator of ten" in paper, "paper flags the strict view's small denominator")
claim("table2b-strict" in paper, "Table 2b is generated, not hand-typed")

print("\ntruncation disclosure")
import json as _j
_bk = _j.loads((ROOT / "docs" / "v1.1_truncated_attempt" / "batch_cache.pre_purge_backup.json").read_text())
_v11 = [k for k in _bk if k.startswith("1.1.0|")]
_kept = _j.loads((ROOT / "docs" / ".batch_cache.json").read_text())
_txt = lambda v: v.get("text") if isinstance(v, dict) else v  # noqa: E731
# Kept = the same reply is still in the cache. Matching on key alone would count
# purged batches again once the sweep re-requests them under the same key.
_kept11 = [k for k in _v11 if k in _kept and _txt(_kept[k]) == _txt(_bk[k])]
claim(len(_v11) == 84 and "first 84 batch" in paper, "paper: 84 replies in the truncated attempt")
claim(len(_kept11) == 38 and "The 38 replies" in paper, "paper: 38 complete replies kept")
claim(len(_v11) - len(_kept11) == 46 and "46 of the first 84" in paper, "paper: 46 re-requested")
claim("8,400" in paper and "32,000" in paper, "paper states the old and new output caps")
from baselines.llm import run_firm as _rf
import inspect as _i
claim("32_000" in _i.getsource(_rf), "harness default output cap really is 32,000")

print("\nlanguage-model results prose (every number recomputed from the artifacts)")
_an = json.loads((ROOT / "docs" / "analysis_results.json").read_text())["runs"]
_vw = json.loads((ROOT / "docs" / "views_results.json").read_text())["runs"]
_fin = {k for k, v in json.loads((ROOT / "docs" / "llm_results.json").read_text())["runs"].items()
        if v.get("per_firm")}
_off = {k: v for k, v in _vw.items() if k in _fin and v["variant"].endswith("offered")}
_wit = {k: v for k, v in _vw.items() if k in _fin and v["variant"].endswith("withheld")}


def _rng(vals, fmt="{:.3f}"):
    return fmt.format(min(vals)), fmt.format(max(vals))


_lo, _hi = _rng([v["engine"]["false_green_rate"] for v in _off.values()])
claim(f"from {_lo} to {_hi}" in paper, f"offered FGR range {_lo}-{_hi}")
_lo, _hi = _rng([v["engine"]["violation_recall"] for v in _off.values()])
claim(f"from {_lo} to {_hi}" in paper, f"offered recall range {_lo}-{_hi}")
_lo, _hi = _rng([v["engine"]["abstention_f1"] for v in _off.values()])
claim(f"between {_lo} and {_hi}" in paper, f"offered abstention F1 range {_lo}-{_hi}")
_lt = _an.get("nvidia/nemotron-3.5-lightning:free::abstain_offered")
claim(_lt is not None and f"only {_lt['n_answered']} of 140" in paper
      and f"{_vw['nvidia/nemotron-3.5-lightning:free::abstain_offered']['engine']['false_green_rate_answered']:.3f}" in paper,
      "Lightning coverage and answered-only FGR")

_pairs = {}
for k, v in _vw.items():
    if k in _fin:
        _pairs.setdefault(v["model"], {})["o" if v["variant"].endswith("offered") else "w"] = v
_deltas = {m: d["w"]["engine"]["false_green_rate"] - d["o"]["engine"]["false_green_rate"]
           for m, d in _pairs.items() if "o" in d and "w" in d}
claim(all(x > 0 for x in _deltas.values()), "FGR rises without abstention for every paired model")
_lo, _hi = _rng(list(_deltas.values()))
claim(f"by between {_lo}" in paper and _hi in paper, f"ablation delta range {_lo}-{_hi}")
claim("fold" not in paper.replace("manifold", ""), "no fold-change language (ratios of small counts)")

_dw = [e["decomposition"] for k, e in _an.items() if k in _fin and k.endswith("withheld")]
_do = [e["decomposition"] for k, e in _an.items() if k in _fin and k.endswith("offered")]
# Missed violations count unanswered violation pairs as misses (1 - recall).
_miss = lambda runs: [round((1 - v["engine"]["violation_recall"]) * 20) for v in runs]  # noqa: E731
for _t in (f"between {min(_miss(_off.values()))} and {max(_miss(_off.values()))} of the 20",
           f"misses {min(_miss(_wit.values()))} to {max(_miss(_wit.values()))}"):
    claim(_t in paper.replace("\n", " "), f"missed-violation range stated: {_t}")
_dots = _an.get("dots-studio/dots-3-note-preview:free::abstain_withheld", {}).get("decomposition", {})
claim(f"more to `pass` ({_dots.get('false_green')}) than to `fail` ({_dots.get('unsupported_violation')})"
      in paper.replace("\n", " "), "dots.3 forced-choice split stated")
for _key, _set, _phrase in (("unsupported_violation", _dw, "({} to {} of 120)"),
                            ("false_green", _do, "reports {} to {}")):
    _vals = [d.get(_key, 0) for d in _set]
    _t = _phrase.format(min(_vals), max(_vals))
    claim(_t in paper, f"decomposition: {_t}")

_ec = [e["by_evidence_class"] for k, e in _an.items() if k in _fin]
_docwins = sum(b["document"]["fgr"] > b["field"]["fgr"] for b in _ec)
claim(f"{_docwins} of the {len(_ec)} runs" in paper.replace("\n", " "),
      f"document FGR > field FGR in {_docwins} of {len(_ec)} runs, as the paper states")
_eo = [e["by_evidence_class"] for k, e in _an.items() if k in _fin and k.endswith("offered")]
_ff = sum(b["field"]["n_false_green"] for b in _eo); _fn = sum(b["field"]["n_withheld"] for b in _eo)
_df = sum(b["document"]["n_false_green"] for b in _eo); _dn = sum(b["document"]["n_withheld"] for b in _eo)
claim(f"{_ff} false greens in {_fn} field-pair" in paper and f"{_df} in {_dn} document-pair" in paper,
      f"evidence-class totals {_ff}/{_fn} vs {_df}/{_dn}")

_ap = lambda runs: (sum(r["strict"]["deadline_alerts"]["verdicts"].get("pass", 0) for r in runs),  # noqa: E731
                    sum(r["strict"]["deadline_alerts"]["n"] for r in runs))
_p1, _n1 = _ap(_off.values()); _p2, _n2 = _ap(_wit.values())
claim(f"{_p1} of {_n1} alerts" in paper and f"{_p2} of {_n2}" in paper,
      f"deadline-alert passes {_p1}/{_n1} offered, {_p2}/{_n2} withheld")
_llm = json.loads((ROOT / "docs" / "llm_results.json").read_text())["runs"]
claim(all("n_off_schema" in f and f["n_off_schema"] == 0
          for k, v in _llm.items() if k in _fin for f in v["per_firm"]),
      "no off-schema abstention in any finished run")
_drops = [v["engine"]["false_green_rate"] - v["audited"]["false_green_rate"]
          for k, v in _vw.items() if k in _fin and "audited" in v]
_pos = [d for d in _drops if d > 0]
claim(f"by {min(_pos):.3f} to {max(_pos):.3f} in {len(_pos)}" in paper.replace("\n", " "),
      f"audited view lowers FGR by {min(_pos):.3f}-{max(_pos):.3f} in {len(_pos)} runs")
claim(all(d > 0 for d in _drops) or "rises by" in paper, "any audited-view rise is disclosed")

_sv = max(abs(v["engine"]["false_green_rate"] - v["strict"]["false_green_rate"])
          for k, v in _vw.items() if k in _fin)
claim(f"by at most {_sv:.3f}" in paper, f"strict view shifts FGR by at most {_sv:.3f}")

_abl = json.loads((ROOT / "docs" / "views_results.json").read_text()).get("ablation", {})
claim(len(_abl) == 6 and all(v["holm_reject_0.05"] for v in _abl.values())
      and "All six remain significant" in paper,
      f"all {len(_abl)} paired ablation tests significant after Holm, as stated")

_C = json.loads((ROOT / "docs" / "studies_results.json").read_text())["contrasts"]
_dash_sig = sum(1 for v in _abl.values() if v["holm_reject_0.05"]) + sum(
    1 for k, v in _C.items() if "study1::abstain_offered->abstain_withheld" in k and v["p_holm"] < 0.05)
claim(_dash_sig == 8 and "eight of the nine" in paper.replace("\n", " "),
      f"dashboard schema significant for {_dash_sig} of 9 models, as stated")
claim(not any(v["p_holm"] < 0.05 for k, v in _C.items() if "::study2::" in k)
      and "no contrast survives correction" in paper.replace("\n", " "),
      "no Study 2 contrast survives Holm, as stated")
_sig1 = {k.split("::")[0].replace("vertex/", "") + "|" + k.split("::")[2] for k, v in _C.items()
         if "::study1::" in k and v["p_holm"] < 0.05}
claim(_sig1 == {"gemma-4-26b-a4b-it-maas|abstain_offered->abstain_removed_only",
                "gemma-4-26b-a4b-it-maas|abstain_offered->abstain_closed",
                "gemini-3.8-flash|abstain_offered->abstain_closed",
                "gemini-3.1-pro-preview|abstain_closed->abstain_withheld",
                "gemini-3.8-flash|abstain_closed->abstain_withheld",
                "gemma-4-26b-a4b-it-maas|abstain_offered->abstain_withheld",
                "gemini-3.8-flash|abstain_offered->abstain_withheld"},
      f"the significant Study 1 contrasts are exactly those the text describes ({len(_sig1)})")


print("\nStudy 3, label checks and corrected Study 2 (recomputed)")
_P = re.sub(r"\s+", " ", paper)
_S3 = json.loads((ROOT / "docs" / "study3" / "results.json").read_text())
_pr = _S3["primary"]
_pk = list(_pr)
_RB = json.loads((ROOT / "docs" / "study3" / "robustness.json").read_text())
claim(all(v["outcome"] == "confirmed" and v["p_holm"] == 0.002 for v in _pr.values())
      and "All four were confirmed" in _P and "at its floor (0.002 after correction)" in _P,
      "all four primary hypotheses confirmed; bootstrap floor 0.002 stated")
_pmax = max(v["p_holm"] for v in _RB["sign_flip_permutation"].values())
claim(f"p ≤ {_pmax:.4f} for all four" in _P and f"permutation p ≤ {_pmax:.4f}, Holm" in _P,
      f"exact permutation p-values as stated (max Holm p {_pmax:.4f})")
for _k, _lab in zip(_pk, ("abstention", "definition", "dashboard", "recommended")):
    _v = _pr[_k]
    claim(f"{_v['delta']:+.3f} [{_v['ci95'][0]:+.2f}, {_v['ci95'][1]:+.2f}]" in _P,
          f"primary {_lab}: {_v['delta']:+.3f} with its interval in Table 3")
_AB = re.sub(r"\s+", " ", paper[paper.index("## Abstract"):paper.index("## 1. Introduction")])
claim(f"by {_pr[_pk[2]]['delta']:.3f} under a pass/fail dashboard" in _AB
      and f"by {_pr[_pk[3]]['delta']:.3f} when abstention was offered" in _AB
      and f"({_RB['firm_clustered'][_pk[2]]['firm_mean_effect']:.3f} and {_RB['firm_clustered'][_pk[3]]['firm_mean_effect']:.3f} with firms weighted equally" in _AB,
      "abstract effect sizes match the primary estimates, pooled and firm-weighted")
_s4 = _S3["S4_by_developer_group"]
claim(all(v["p_holm"] < 0.05 and v["delta"] > 0 for v in _s4.values()),
      "every primary effect significant within each developer group, as stated")
_s1 = _S3["S1_per_model"]
_nsig = {k: sum(1 for kk, v in _s1.items() if kk.startswith(k + " |") and v.get("p_holm", 1) < 0.05 and v["delta"] > 0) for k in _pk}
claim([_nsig[k] for k in _pk] == [5, 1, 7, 5], f"per-model significant counts P1-P4 {[_nsig[k] for k in _pk]} match the text")
_fam = _S3["exploratory_by_rule_family"]
_i9p = [_fam[f"i9::plain::{c}"] for c in ("abstain_offered", "abstain_removed_only", "abstain_closed", "abstain_withheld")]
claim(f"{min(_i9p):.3f} to {max(_i9p):.3f}" in _P and f"{_fam['i9::decoy::abstain_offered']:.3f} under the offered" in _P
      and f"{_fam['i9::decoy::abstain_withheld']:.3f} under the dashboard" in _P
      and f"{_fam['wage::plain::abstain_offered']:.3f} of pairs" in _P,
      "I-9 and wage rule-family figures match")
_c = _S3["cells"]
_ms = ["gemini-3.1-pro-preview", "gemini-3.8-flash", "gemma-4-26b-a4b-it-maas", "gpt-oss-120b-maas",
       "deepseek-v3.2-maas", "qwen3-235b-a22b-instruct-2507-maas", "kimi-k2-thinking-maas"]
claim(min(v["answered"] for v in _c.values()) == 456 and "at least 456 of 504" in _P, "Study 3 minimum coverage 456/504")
_dof = [_c[f"{m}::decoy::abstain_offered"]["false_green_rate"] for m in _ms]
claim(f"{min(_dof):.2f} to {max(_dof):.2f} on proxy-column firms" in _P, "proxy-arm offered FGR range")
_hi = [m for m in _ms if _c[f"{m}::plain::abstain_offered"]["violation_recall"] >= 0.92]
claim(len(_hi) == 4 and "{:.3f} to {:.3f} of unassessable pairs".format(
      min(_c[f"{m}::decoy::abstain_offered"]["false_green_rate"] for m in _hi),
      max(_c[f"{m}::decoy::abstain_offered"]["false_green_rate"] for m in _hi)) in _P,
      "high-recall models' decoy FGR range")
_fa_o = max(abs(_c[f"{m}::decoy::abstain_offered"]["false_alarm_rate"] - _c[f"{m}::plain::abstain_offered"]["false_alarm_rate"]) for m in _ms)
_fa_a = max(abs(_c[f"{m}::decoy::{k}"]["false_alarm_rate"] - _c[f"{m}::plain::{k}"]["false_alarm_rate"])
            for m in _ms for k in ("abstain_offered", "abstain_removed_only", "abstain_closed", "abstain_withheld"))
claim(f"at most {_fa_o:.3f} with abstention offered and {_fa_a:.3f} under any schema" in _P, "false-alarm shifts from proxy columns")
_s2 = _S3["S2_removed_only"]
claim(f"by {_s2['pooled']['delta']:.3f} pooled (p = {_s2['pooled']['p_holm']:.3f})" in _P
      and [k for k, v in _s2.items() if k != "pooled" and v.get("p_holm", 1) < 0.05] == ["kimi-k2-thinking-maas"],
      "S2 pooled and Kimi-only, as stated")
_s3 = _S3["S3_interaction"]
claim(_s3["p_two_sided"] >= 0.05 and f"{_s3['delta']:+.3f} [{_s3['ci95'][0]:.2f}, {_s3['ci95'][1]:.2f}], p = {_s3['p_two_sided']:.2f}".replace("-0.", "−0.") in _P,
      "interaction not significant, figures as stated")
_e1 = _S3["E1_anchor"]
_e = lambda cond, k: [v[k] for kk, v in _e1.items() if kk.endswith("::" + cond)]  # noqa: E731
_vx = json.loads((ROOT / "docs" / "studies_results.json").read_text())["vertex"]
_vm13 = lambda cond, metric: [_vx[k]["summary"][metric]["mean"] for k in _vx if f"study1::{cond}" in k]  # noqa: E731
_vw13 = json.loads((ROOT / "docs" / "views_results.json").read_text())["runs"]
_fin13 = {k for k, v in json.loads((ROOT / "docs" / "llm_results.json").read_text())["runs"].items() if v.get("per_firm")}
_free = lambda var, metric: [v["engine"][metric] for k, v in _vw13.items() if k in _fin13 and v["variant"] == var]  # noqa: E731
_o13 = _free("abstain_offered", "false_green_rate") + _vm13("abstain_offered", "false_green_rate") + _e("abstain_offered", "false_green_rate")
_w13 = _free("abstain_withheld", "false_green_rate") + _vm13("abstain_withheld", "false_green_rate") + _e("abstain_withheld", "false_green_rate")
_r13 = _free("abstain_offered", "violation_recall") + _vm13("abstain_offered", "violation_recall") + _e("abstain_offered", "violation_recall")
claim(len(_o13) == len(_w13) == len(_r13) == 13
      and f"thirteen models report {min(_o13):.3f} to {max(_o13):.3f}" in _P
      and f"{min(_w13):.3f} to {max(_w13):.3f} under the dashboard schema" in _P
      and min(_r13) >= 0,
      "Section 7 ranges over all thirteen models")
_lc = json.loads((ROOT / "docs" / "labelcheck_results.json").read_text())
_dup = _lc["by_group"]["study3_decoy"]["n"]
claim(_lc["n_pairs"] == _lc["n_agree"] == 1680 and f"all {_lc['n_pairs'] - _dup:,} distinct generated labels" in _P
      and "1,680 counting the proxy twins" in _P,
      "reference checker agrees on all distinct labels; the duplicated proxy twins are named")
_a2 = json.loads((ROOT / "docs" / "label_audit_second.json").read_text())["summary"]
claim(_a2["agreement"] == 113 and _a2["overturned_first"] == 2 and _a2["overturned_second"] == 5
      and not _a2["overturned_both"] and "keep the label on 113 of 120" in _P, "second audit agreement figures")
from nofalsegreen.labelviews import MEMO_ABSENCE, PROSPECTIVE  # noqa: E402
_va = {k: v["decision"] for k, v in json.loads((ROOT / "docs" / "label_audit_second.json").read_text())["pairs"].items()
       if v["audit"] == "violation" and k not in MEMO_ABSENCE | PROSPECTIVE}
claim(len(_va) == 10 and sum(v == "violation_shown" for v in _va.values()) == 5
      and sum(v == "cannot_tell" for v in _va.values()) == 4 and "it supports five" in _P,
      "second audit supports 5 of 10 strict-view violations, 4 undecidable, 1 compliant")
_st = json.loads((ROOT / "docs" / "studies_results.json").read_text())["vertex"]
_g = _st["vertex/gemma-4-26b-a4b-it-maas::study2::abstain_offered"]["summary"]
claim(f"detects {_g['violation_recall']['mean']:.3f} of violations" in _P
      and f"raises {_g['false_alarm_near_miss']['mean']:.3f}" in _P, "corrected Study 2 Gemma figures")
claim(all(_st[f"vertex/{m}::study2::{c}"]["summary"]["false_alarm_rate"]["max"] == 0
          and _st[f"vertex/{m}::study2::{c}"]["summary"]["violation_recall"]["min"] == 1.0
          for m in ("gemini-3.1-pro-preview", "gemini-3.8-flash")
          for c in ("abstain_offered", "abstain_closed", "abstain_withheld")),
      "corrected Study 2: Pro and Flash perfect recall, no false alarm in three schemas")


print("\nround-3 exploratory and label claims (recomputed)")
_EX = json.loads((ROOT / "docs" / "study3" / "exploratory.json").read_text())
_px = _EX["proxy_arm_false_greens_citing_a_proxy_column"]
claim(f"{_px['citing_proxy']:,} of the {_px['n']:,} false greens ({_px['share']:.0%})" in _P,
      "share of proxy-firm false greens citing a planted column")
_ci = _EX["cited_evidence_on_false_greens"]["i9::decoy::abstain_offered"]
_cp = sum(v for k, v in _ci["by_field"].items() if k != "other" and not k.startswith("WAGE_RATE"))
claim(f"{_cp} of {_ci['total']} ({_cp / _ci['total']:.0%})" in _P, "I-9 offered false greens citing a proxy")
claim(all("i9Status" not in x["by_field"] for x in _EX["cited_evidence_on_false_greens"].values())
      and "was never cited" in _P, "the I-9 status column is never cited, as stated")
_ac = _EX["schema_contrasts_by_arm"]
claim(f"(exploratory: +{_ac['abstention (offered -> closed) | plain']['delta']:.3f} and +{_ac['definition and warning (closed -> dashboard) | plain']['delta']:.3f})" in _P,
      "plain-firm schema contrasts as stated")
_sg = _EX["proxy_effect_cluster_signs"]
claim(_EX["firms_per_family"] == {"i9": 3, "wage": 9} and "I-9 pairs (99) come from only three firms" in _P
      and "the wage pairs (81) from nine" in _P, "cluster composition as stated")
_fc = _RB["firm_clustered"]
_pk4 = [k for k in _fc if "|" not in k]
claim(all(v["firm_mean_effect"] > 0 for k, v in _fc.items() if k in _pk4)
      and f"P3 falls to {_fc[[k for k in _pk4 if k.startswith('P3')][0]]['firm_mean_effect']:+.3f}" in _P
      and max(_fc[k]["p_exact_two_sided"] for k in _pk4) < 0.03 and "0.028)" in _P,
      "firm-weighted re-analysis as stated")
claim(all(v["min"] > 0 for v in _RB["leave_one_model_out"].values())
      and all(v["min"] > 0 for v in _RB["leave_one_firm_out"].values()), "leave-one-out effects all positive, as stated")
_c3 = _S3["cells"]
_rec = {m: _c3[f"{m}::plain::abstain_offered"]["violation_recall"] for m in _ms}
_recp = {m: _c3[f"{m}::decoy::abstain_offered"]["violation_recall"] for m in _ms}
_hi4 = [m for m in _ms if _recp[m] >= 0.9]
claim(len(_hi4) == 4 and f"detect at least {min(_recp[m] for m in _hi4):.3f} of violations" in _P,
      "high-recall group on the same proxy-column firms")
_A2 = json.loads((ROOT / "docs" / "label_audit_second.json").read_text())
_k = _A2["summary"]["cohen_kappa"]
claim(f"$\\kappa$ = {_k:.3f}".replace("-", "−") in paper.replace("\n", " "), f"kappa {_k} reported")
claim(_A2["summary"]["violation_decisions"].get("violation_shown") == 7 and "only 7 of its 20 violation labels shown by the exports" in _P,
      "second auditor supports 7 of 20 violations")
_rules = {p.pair_id.split("::")[0] for p in firm.pairs}
_sub2 = {p.pair_id.split("::")[0] for p in _sub.pairs}
claim(f"| Anchor firm | {len(_rules)} | {len({regimes.get(r) for r in _rules})} | 221 |" in paper
      and f"| Anchor subset (Section 7) | {len(_sub2)} | {len({regimes.get(r) for r in _sub2})} | 140 |" in paper,
      "rulebook coverage table")


print("\nStudies 3b and 3c (recomputed)")
_B = json.loads((ROOT / "docs" / "study3b" / "results.json").read_text())
_bt, _bo = _B["tests"], _B["original_wording"]
_bk = list(_bt)
claim(all(v["outcome"] == "replicated" and v["p_holm"] == 0.0015 for v in _bt.values())
      and "All three declared tests replicated (Holm-adjusted p = 0.0015 each" in _P, "Study 3b: all replicated")
claim(f"by {_bt[_bk[0]]['delta']:.3f} under the reworded dashboard" in _P
      and f"by {_bt[_bk[1]]['delta']:.3f} under the reworded offered" in _P
      and f"against {_bo[_bk[0]]['delta']:.3f} and {_bo[_bk[1]]['delta']:.3f}" in _P
      and f"raised it by {_bt[_bk[2]]['delta']:.3f}, against {_bo[_bk[2]]['delta']:.3f}" in _P, "Study 3b effect sizes")
_C = json.loads((ROOT / "docs" / "study3c" / "results.json").read_text())["tests"]
_ck = list(_C)
claim(all(v["outcome"] == "confirmed" for v in _C.values())
      and max(v["p_exact_two_sided"] for v in _C.values()) <= 0.004 and max(v["p_holm"] for v in _C.values()) <= 0.010
      and min(v["firms_positive"] for v in _C.values()) >= 9
      and "exact p ≤ 0.004, Holm-adjusted ≤ 0.010, positive in at least nine firms" in _P, "Study 3c: all confirmed")
claim(f"by {_C[_ck[0]]['delta']:.3f} under the dashboard schema and by {_C[_ck[1]]['delta']:.3f} under the offered" in _P
      and f"onboarding date raised it by {_C[_ck[3]]['delta']:.3f}" in _P
      and f"end date by {_C[_ck[4]]['delta']:.3f}" in _P and f"raised it by only {_C[_ck[2]]['delta']:.3f}" in _P,
      "Study 3c effect sizes")

print("\nhonesty checks")
claim("[TO RUN]" not in paper and "`[…]`" not in paper, "no unfilled placeholder remains")
claim("have not yet been run" not in paper and "has not been run" not in paper,
      "paper no longer claims the LM experiments are unrun")
_t2 = paper[paper.index("BEGIN GENERATED: table2-main"):paper.index("END GENERATED: table2-main")]
sys.path.insert(0, str(ROOT / "scripts"))
from fill_results import NAMES as _NAMES  # noqa: E402
claim(all(f"| {_NAMES.get(k.split('/')[-1].split('::')[0].replace(':free', ''), k)} |" in _t2
          for k in _fin if k.endswith("offered")), "per-model anchor table has a row for every finished offered run")
_V = json.loads((ROOT / "docs" / "studies_results.json").read_text())["vertex"]
_vm = lambda cond, metric: [_V[k]["summary"][metric]["mean"] for k in _V if f"study1::{cond}" in k]  # noqa: E731
claim("0.042" not in _AB and "0.589" not in _AB, "abstract leads with the declared study, not anchor ranges")
claim(len(_V) == 24 and all(v["n_repeats"] == 3 for v in _V.values()),
      "Vertex block: 24 cells, three repeats each")
_sp = [v["summary"]["false_green_rate"]["max"] - v["summary"]["false_green_rate"]["min"] for v in _V.values()]
claim(f"differ by at most {max(_sp):.3f}" in paper.replace("\n", " ")
      and f"in {sum(1 for x in _sp if x <= 0.06 + 1e-9)} of them" in paper.replace("\n", " "),
      "repeat-spread claims match")
claim(results["note"].startswith("Trivial baselines only"), "results.json is labelled as trivial baselines")
claim("Language-model results" in readme and "0.042 to 0.142" in readme, "README reports LM results")
for forbidden in ["250-rule", "237-rule", "612 cases", "768 checks"]:
    claim(forbidden not in paper, f"paper avoids unverified figure '{forbidden}'")
claim("not an independent baseline" in paper or "do not" in paper and "acceptance gate" in paper,
      "paper excludes the co-developed engine as a baseline")

# verdict allocation on unassessable pairs, Study 3 (mean over the seven models)
_FL = json.loads((ROOT / "docs" / "study3" / "exploratory.json").read_text())["verdict_flow"]


def _alloc(arm, cond, verdict):
    sh = [v.get(verdict, 0) / sum(v.values()) for k, v in _FL.items() if k.endswith(f"::{arm}::{cond}")]
    return f"{sum(sh) / len(sh):.3f}"


_flat = re.sub(r"\s+", " ", paper)
claim(f"{_alloc('decoy', 'abstain_offered', 'needs_evidence')} of unassessable pairs were answered `needs_evidence`, "
      f"{_alloc('decoy', 'abstain_offered', 'pass')} `pass` and {_alloc('decoy', 'abstain_offered', 'fail')} `fail`" in _flat
      and f"{_alloc('decoy', 'abstain_withheld', 'pass')} were `pass` and {_alloc('decoy', 'abstain_withheld', 'fail')} `fail`" in _flat,
      "verdict allocation on proxy-column firms matches exploratory.json")

# Study 4 (docs/STUDY4_DECLARATION.md)
_S4 = json.loads((ROOT / "docs" / "study4" / "results.json").read_text())
_P4, _X4, _C4 = _S4["primary"], _S4["secondary"], _S4["cells"]
_d = lambda k: _P4[k]["delta"]  # noqa: E731
_fg = lambda arm, v, m=None: (_C4[f"{arm}::{v}::r0"]["by_model"][m]["fgr"] if m  # noqa: E731
                              else _C4[f"{arm}::{v}::r0"]["fgr_mean_over_models"])
_k = {k[:2]: k for k in _P4}
claim(f"0.{round(_X4['renamed - plain | abstain_offered']['delta'] * 1000):03d} over plain firms" in _flat
      and f"by {_X4['irrelevant - plain | abstain_offered']['delta']:.3f}. The named" in _flat,
      "Study 4: renamed and irrelevant vs plain, offered")
claim(f"raised them {_d(_k['H1']):.3f} more than their renamed twins (H1) and {_d(_k['H2']):.3f} more" in _flat,
      "Study 4: H1, H2 effects")
claim(f"renamed values alone added {_X4['renamed - plain | abstain_withheld']['delta']:.3f}" in _flat,
      "Study 4: renamed vs plain, dashboard")
claim(f"+{_d(_k['H3']):.3f} (H3, Holm p = {_P4[_k['H3']]['p_holm']:.3f})" in _flat, "Study 4: H3")
_adv = _C4["adverse::abstain_offered::r0"]["by_model"]
claim(all(_adv[m]["allocation"].get("needs_evidence") == 330 for m in ("gemini-3.1-pro-preview", "gemini-3.8-flash"))
      and f"answered `pass` on {_adv['gemma-4-26b-a4b-it-maas']['allocation']['pass']} of them" in _flat
      and _adv["gemma-4-26b-a4b-it-maas"]["allocation"].get("fail", 0) > 0,
      "Study 4: adverse allocation (Gemini all needs_evidence; Gemma passes; fails only from Gemma)")
claim(f"by {_d(_k['H4']):.3f} (H4)" in _flat and f"warning by {_d(_k['H6']):.3f}" in _flat
      and f"them by {_d(_k['H5']):.3f} (H5, Holm p = {_P4[_k['H5']]['p_holm']:.3f}, not confirmed)".replace("-", "−") in _flat
      and _P4[_k["H5"]]["outcome"] == "not confirmed",
      "Study 4: factorial main effects H4-H6")
claim(f"+{_d(_k['H4']):.3f})" in _flat and f"(+{_d(_k['H6']):.3f})" in _flat and f"(−{_d(_k['H7']):.3f})" in _flat,
      "abstract: Study 4 effects")
claim(max(abs(_X4[f"{f} main effect | plain firms"]["delta"]) for f in "ODW") <= 0.019 + 1e-9
      and "more than 0.019" in _flat, "Study 4: plain-firm factorial effects")
claim(f"from {_fg('proxy', 'abstain_offered'):.3f} to {_fg('proxy', 'cite_first'):.3f} (H7, Holm p = {_P4[_k['H7']]['p_holm']:.3f})" in _flat
      and _fg("proxy", "cite_first", "gemini-3.1-pro-preview") == 0
      and f"from {_fg('proxy', 'abstain_offered', 'gemini-3.8-flash'):.3f} to {_fg('proxy', 'cite_first', 'gemini-3.8-flash'):.3f}" in _flat
      and f"from {_fg('proxy', 'abstain_offered', 'gemma-4-26b-a4b-it-maas'):.3f} to {_fg('proxy', 'cite_first', 'gemma-4-26b-a4b-it-maas'):.3f}" in _flat,
      "Study 4: cite-first rates")
_cc = _S4["cite_first_costs"]
_ca = _S4["cite_first_costs_all_pairs"]
claim(all(_ca[f"{a}::cite_first"][m]["recall_all_pairs"] >= _ca[f"{a}::abstain_offered"][m]["recall_all_pairs"]
          for a in ("plain", "proxy") for m in _ca["proxy::cite_first"])
      and "No model's recall over all violations fell" in _flat, "Study 4: cite-first lowers no model's recall (all pairs)")
_g = _ca["plain::cite_first"]["gemma-4-26b-a4b-it-maas"]
claim(f"left {_g['unanswered_violations']} of {_g['n_violations']} violations and {_g['unanswered_controls']} of {_g['n_controls']} controls unanswered" in _flat,
      "Study 4: Gemma cite-first coverage on plain firms")
_I = _S4["factorial_interactions_posthoc"]
claim(f"(+{_I['W effect | O=0 (proxy firms)']:.3f}, against +{_I['W effect | O=1 (proxy firms)']:.3f} with them)" in _flat
      and f"*lowered* false greens ({_I['D effect | O=0 (proxy firms)']:.3f})".replace("-", "−") in _flat,
      "Study 4: factorial interactions")
_sh = _S4["proxy_minus_renamed_count_share_posthoc"]["gemma-4-26b-a4b-it-maas"]["share"]
claim(f"accounts for {round(_sh * 100)}% of the named-versus-renamed" in _flat, "Study 4: Gemma share of H1")
_cf = _S4["cite_first_pass_cites_required_export"]["gemma-4-26b-a4b-it-maas"]
claim(_cf["cite_i9_export"] == 0 and f"none of Gemma 4's {_cf['passes']} remaining" in _flat, "Study 4: Gemma cite-first passes")
claim(all(v["fgr_after_gate"] == 0 for v in _S4["deterministic_gate"].values()), "Study 4: gate removes every false green")
_rr = _S4["repeat_runs"]
_sp4 = max(max(v) - min(v) for k, v in _rr.items() if "per run" not in k)
_po, _pd = _rr["proxy - plain per run | abstain_offered"], _rr["proxy - plain per run | abstain_withheld"]
claim(f"at most {_sp4:.3f}" in _flat and f"between {min(_po):.3f} and {max(_po):.3f}" in _flat
      and f"between {min(_pd):.3f} and {max(_pd):.3f}" in _flat, "Study 4: repeat-run spreads")
_cov = min(330 - v["allocation"].get("unanswered", 0) for c in _C4.values() for v in c["by_model"].values())
claim(f"lowest coverage\nwas {_cov} of 330".replace("\n", " ") in _flat, "Study 4: lowest coverage")
claim("table-study4" in paper, "Study 4 table is generated")

# Study 5 (docs/STUDY5_DECLARATION.md)
_S5 = json.loads((ROOT / "docs" / "study5" / "results.json").read_text())
_P5, _C5 = _S5["primary"], _S5["cells"]
_r = {k[:2]: v for k, v in _P5.items()}
claim(f"raised false greens by {_r['R1']['delta']:.3f} (R1, Holm p = {_r['R1']['p_holm']:.3f};" in _flat
      and f"rose a further {_r['R2']['delta']:.3f} with it (R2, not\nconfirmed)".replace("\n", " ") in _flat
      and _r["R2"]["outcome"] == "not confirmed"
      and f"raised them by {_r['R3']['delta']:.3f} (R3, Holm p = {_r['R3']['p_holm']:.4f})" in _flat,
      "Study 5: R1-R3")
claim(f"raised them by {_r['R1']['delta']:.3f} with abstention offered" in _AB, "abstract: Study 5 R1")
claim(f"false greens were {_S5['means']['lca_only::abstain_withheld']:.3f} without the pay field" in _flat, "Study 5: dashboard level")
_g5 = lambda m, a, c: _C5[f"{m}::{a}::{c}"]  # noqa: E731
claim(all(_g5(m, "lca_only", "abstain_offered")["allocation"] == {"needs_evidence": _g5(m, "lca_only", "abstain_offered")["answered"]}
          for m in ("gemini-3.1-pro-preview", "gemini-3.8-flash"))
      and f"Gemma 4 called {_g5('gemma-4-26b-a4b-it-maas', 'lca_only', 'abstain_offered')['fgr_all_pairs']:.3f} of them" in _flat,
      "Study 5: offered, no pay field")
_fl = _g5("gemini-3.8-flash", "salary", "abstain_offered")
claim(_fl["fgr_all_pairs"] == 0.5 and f"cited `Pay Rate` on {_fl['false_green_cites'].get('pay rate (salary of record)')} of its {_fl['allocation']['pass']}" in _flat
      and _g5("gemini-3.1-pro-preview", "salary", "abstain_offered")["fgr_all_pairs"] == 0, "Study 5: Flash and Pro with salary")
claim(all(_g5(m, "complete", "abstain_offered")["recall_all_pairs"] == 1 and _g5(m, "complete", "abstain_offered")["false_alarm_all_pairs"] == 0
          for m in ("gemini-3.1-pro-preview", "gemini-3.8-flash"))
      and f"Gemma 4 detected {_g5('gemma-4-26b-a4b-it-maas', 'complete', 'abstain_offered')['recall_all_pairs']:.3f} of them" in _flat,
      "Study 5: complete arm")
claim("(1,032,736 rows)" in _flat and "(3,443)" in _flat and "(1,238)" in _flat, "Study 5: selection counts in Appendix A")

# AI pilot of the expert protocol (Appendix I)
_AP = json.loads((ROOT / "docs" / "ai_pilot_review" / "results.json").read_text())["runs"]
claim(all(v["agreement_overall"] == 1 and v["items"] == 50 for v in _AP.values())
      and "Each agreed with all 50 labels" in _flat, "AI pilot: both agree with all 50 labels")
_pb = {n: list(v["part_b"].values()) for n, v in _AP.items()}
claim(all(x[:4] == ["Strongly disagree"] * 4 and x[5] == "Strongly agree" for x in _pb.values())
      and _pb["Claude (kit v2)"][4] == "Disagree" and _pb["Claude (kit v2)"][6] == "Disagree"
      and _pb["Codex (kit v3)"][4] == "Strongly disagree" and _pb["Codex (kit v3)"][6] == "Strongly disagree",
      "AI pilot: Part B answers as described")

# Study 6 (docs/STUDY6_DECLARATION.md)
_S64 = json.loads((ROOT / "docs" / "study6" / "study4_results.json").read_text())
_S65 = json.loads((ROOT / "docs" / "study6" / "study5_results.json").read_text())
_q = {k[:2]: v for k, v in {**_S64["primary"], **_S65["primary"]}.items()}
claim(f"(+{_q['H2']['delta']:.3f});" in _flat and f"(+{_q['H4']['delta']:.3f});" in _flat
      and f"(−{_q['H7']['delta']:.3f});" in _flat and f"raised them by {_q['R1']['delta']:.3f} with abstention offered" in _flat
      and f"raised them by {_q['R3']['delta']:.3f}." in _flat
      and all(_q[k]["outcome"] == "confirmed" for k in ("H2", "H3", "H4", "H6", "H7", "R1", "R3")), "Study 6: replicated tests")
_pm = _S64["per_model_primary_posthoc"]
claim(_q["H1"]["outcome"] == "not confirmed" and f"did not replicate ({_q['H1']['delta']:.3f})".replace("-", "−") in _flat
      and _q["H5"]["outcome"] == "confirmed" and _q["H5"]["delta"] > 0 and f"for both models (+{_q['H5']['delta']:.3f})" in _flat
      and all(v > 0 for v in _pm["H5"].values())
      and f"suggested a breach (+{_q['H3']['delta']:.3f})" in _flat, "Study 6: H1 not replicated, H5 opposite sign, H3")
claim(f"raised DeepSeek's false greens by {_pm['H1']['deepseek-v3.2-maas']:.3f}" in _flat
      and f"lowered GLM-5.2's by {-_pm['H1']['glm-5.2-maas']:.3f}" in _flat
      and f"came from DeepSeek (+{_pm['H6']['deepseek-v3.2-maas']:.3f}); for GLM-5.2 it was " + f"{_pm['H6']['glm-5.2-maas']:.3f}".replace("-", "−") in _flat,
      "Study 6: per-model H1 and H6")
_dc = _S64["cite_first_costs_all_pairs"]
_do, _df = _dc["proxy::abstain_offered"]["deepseek-v3.2-maas"], _dc["proxy::cite_first"]["deepseek-v3.2-maas"]
_dg = _S64["cells"]
claim(f"from {_dg['proxy::abstain_offered::r0']['by_model']['deepseek-v3.2-maas']['fgr']:.3f} to {_dg['proxy::cite_first::r0']['by_model']['deepseek-v3.2-maas']['fgr']:.3f}" in _flat
      and f"recall from {_do['recall_all_pairs']:.3f} to {_df['recall_all_pairs']:.3f}" in _flat
      and f"controls from {_do['false_alarm_any_nonpass_all_pairs']:.3f} to {_df['false_alarm_any_nonpass_all_pairs']:.3f}" in _flat,
      "Study 6: DeepSeek evidence-first cost")
_gl = _S64["cells"]
claim(f"called {_gl['renamed::abstain_offered::r0']['by_model']['glm-5.2-maas']['fgr']:.3f} of unassessable pairs compliant from the renamed values" in _flat
      and _gl["renamed::abstain_offered::r0"]["by_model"]["glm-5.2-maas"]["fgr"] > _gl["proxy::abstain_offered::r0"]["by_model"]["glm-5.2-maas"]["fgr"],
      "Study 6: GLM renamed > named")
_c6 = _S65["cells"]
claim(_c6["glm-5.2-maas::complete::abstain_offered"]["recall_all_pairs"] == 1
      and _c6["deepseek-v3.2-maas::complete::abstain_offered"]["recall_all_pairs"] == 0, "Study 6: complete-arm detection")
_cov6 = sorted(330 - v["allocation"].get("unanswered", 0) for c in _gl.values() for v in c["by_model"].values())
claim(_cov6[0] == 285 and _cov6[1] == 318 and min(v["answered"] for v in _c6.values()) == 110
      and "285 of 330" in _flat and "least 318 of 330" in _flat and "at least 110 of 120" in _flat, "Study 6: coverage")
claim("table-study6" in paper, "Study 6 table is generated")

# Study 7 (docs/STUDY7_DECLARATION.md)
_S7 = json.loads((ROOT / "docs" / "study7" / "results.json").read_text())
_w = {k[:2]: v for k, v in _S7["primary"].items()}
_p7 = _S7["per_model"]
claim(f"raised false greens by {_w['W1']['delta']:.3f} (W1, Holm p = {_w['W1']['p_holm']:.3f}, positive in all twelve" in _flat
      and _w["W1"]["firms_positive"] == 12 and _w["W2"]["outcome"] == "not confirmed"
      and f"added {_w['W2']['delta']:.3f} (W2, not confirmed)" in _flat, "Study 7: W1, W2")
_pr = _p7["pay_rate_only - lca_only"]; _sp = _p7["salary - pay_rate_only"]
claim(f"+{_pr['deepseek-v3.2-maas']:.3f} for DeepSeek V3.2, +{_pr['gemma-4-26b-a4b-it-maas']:.3f} for Gemma 4, +{_pr['gemini-3.8-flash']:.3f} for Gemini 3.8 Flash" in _flat
      and _pr["gemini-3.1-pro-preview"] == 0 and _pr["glm-5.2-maas"] == 0
      and f"Flash's false greens by {_sp['gemini-3.8-flash']:.3f} and GLM-5.2's by {_sp['glm-5.2-maas']:.3f}" in _flat
      and f"answered {_S7['answered']['glm-5.2-maas::pay_rate_only']} of 120 pairs in the `Pay Rate` arm" in _flat,
      "Study 7: per-model effects and coverage")

# Study 8 (docs/STUDY8_DECLARATION.md)
_S8 = json.loads((ROOT / "docs" / "study8" / "results.json").read_text())
_f8 = {k[:2]: v for k, v in _S8["primary"].items()}
claim(all(_f8[k]["outcome"] == "confirmed" and _f8[k]["firms_positive"] == 10 and f"{_f8[k]['p_holm']:.3f}" == "0.010"
          for k in ("F1", "F2", "F3", "F4"))
      and all(f"+{_f8[k]['delta']:.3f}" in _flat for k in ("F1", "F2", "F3", "F4")), "Study 8: F1-F4")
_pr8 = _S8["fresh_per_run"]
_pmr = _S8["fresh_per_model_per_run"]
_mx = max((abs(v["r0"] - v["r1"]), k, m) for k, mm in _pmr.items() for m, v in mm.items())
claim(max(abs(v["r0"] - v["r1"]) for v in _pr8.values()) <= 0.02 and "pooled estimates from the two runs agreed to within 0.02" in _flat
      and _mx[2] == "glm-5.2-maas" and _mx[1].startswith("F4") and f"GLM-5.2's F4 by {_mx[0]:.3f}" in _flat
      and f"single models by up to {_mx[0]:.3f}" in _flat, "Study 8: pooled vs per-model run agreement")
_pm8 = _S8["fresh_per_model"]["F1 proxy - plain, offered"]
claim(min(_pm8.values()) > 0 and f"+{min(_pm8.values()):.3f} (Gemini 3.1 Pro) to +{max(_pm8.values()):.3f} (Gemma 4)" in _flat
      and min(_pm8, key=_pm8.get) == "gemini-3.1-pro-preview" and max(_pm8, key=_pm8.get) == "gemma-4-26b-a4b-it-maas",
      "Study 8: per-model F1 range")
claim(_f8["G1"]["outcome"] == "confirmed" and f"raised false greens by {_f8['G1']['delta']:.3f}\n(Holm p = {_f8['G1']['p_holm']:.3f}, positive in eleven".replace("\n", " ") in _flat
      and _f8["G1"]["firms_positive"] == 11, "Study 8: G1")
_gr = _S8["greater_of_recall"]
_g2 = _f8["G2"]
claim(_g2["outcome"] == "not confirmed"
      and f"(G2, {_g2['delta']:.3f} [{_g2['ci95_firm_bootstrap'][0]:.3f}, +{_g2['ci95_firm_bootstrap'][1]:.3f}], ten firms, not confirmed)".replace("-", "−") in _flat
      and f"{_gr['deepseek-v3.2-maas::greater_of_only']:.3f} of them against {_gr['deepseek-v3.2-maas::below_offered']:.3f}" in _flat
      and _gr["gemini-3.1-pro-preview::greater_of_only"] == 1 and _gr["glm-5.2-maas::greater_of_only"] == 1
      and f"Flash {_gr['gemini-3.8-flash::greater_of_only']:.3f}" in _flat
      and f"flagged {_gr['deepseek-v3.2-maas::false_alarm']:.3f} of correctly paid" in _flat, "Study 8: G2 and recall")
claim(f"{_S8['fresh_coverage_min']} of {_S8['fresh_n_unassessable']} pairs" in _flat, "Study 8: coverage")

_go = _S7["google_only_posthoc"]
claim(f"`Pay Rate` alone gives +{_go['pay_rate_only - lca_only']:.3f} against +{_go['salary - lca_only']:.3f} for the three fields" in _flat
      and sum(v > 0 for v in _S7["per_model"]["pay_rate_only - lca_only"].values()) == 3
      and "column alone induced false greens in three of five models" in _AB, "Study 7: Google-only diagnostic and abstract claim")
_lab8 = json.loads((ROOT / "docs" / "study8" / "results.json").read_text())
from nofalsegreen import study5 as _s5  # noqa: E402
from collections import Counter as _C  # noqa: E402
_kinds = _C(l.note for f in _s5.build("complete_actual_above") for l in f.labels if l.verdict.value == "fail")
claim(_kinds["greater_of_only"] == 38 and _kinds["below_offered"] == 24
      and "these 38 underpayments and on the 24 below the offered wage" in _flat, "Study 8: G2 denominators")

claim(len(REBUILD) == 33 and "all 33 derived results files" in _flat, "Appendix A: rebuild coverage stated correctly")
_ec = json.loads((ROOT / "docs" / "existing_certificates.json").read_text())
_lv = json.loads((ROOT / "docs" / "study9" / "label_verification.json").read_text())
claim(_ec["needs_evidence_pairs"] == _ec["certified"] == 3330 and not _ec["failures"]
      and "All 3,330 such labels in Studies 3, 3c, 4 and 8 are certified" in _flat, "existing labels certified")
claim(_lv["certificates"] == _lv["certificates_verified"] == 454 and _lv["witness_labels"] == 227 and _lv["conflict_labels"] == 36
      and _lv["agree"] == _lv["labels"] and "as are all 227 that turn on missing values in Study 9 (454 completions checked)" in _flat
      and "Study 9's 36 conflict labels" in _flat, "Study 9 certificates (labels vs completions) and checker agreement")
_c5 = json.loads((ROOT / "docs" / "study5" / "results.json").read_text())["cells"]
claim(_c5["gemini-3.1-pro-preview::complete::abstain_offered"]["recall_all_pairs"] == 1
      and _c5["gemini-3.1-pro-preview::lca_only::abstain_offered"]["fgr_all_pairs"] == 0
      and _c5["gemini-3.1-pro-preview::salary::abstain_offered"]["fgr_all_pairs"] == 0
      and "Gemini 3.1 Pro both detected every underpayment and made no false green" in _flat
      and "largest cause" not in _flat, "intro: scoped recall claim; no cross-study superlative")

_wh = json.loads((ROOT / "docs" / "external" / "whd_h1b.json").read_text())["FY2025"]
claim(f"in {_wh['compliance_actions_with_violations']} compliance actions and recovered ${_wh['back_wages_usd']:,} in back wages for {_wh['employees_receiving_back_wages']} workers" in _flat,
      "intro: WHD FY2025 H-1B figures match the retained snapshot")

# Studies 9-12 (docs/STUDY9..12_DECLARATION.md)
_R = {n: json.loads((ROOT / "docs" / f"study{n}" / "results.json").read_text()) for n in (9, 10, 11, 12)}
_bm = _R[9]["partB_metrics"]
_ef, _ex, _gt = _bm["evidence-first prompt"], _bm["extraction + solver"], _bm["presence gate + evidence-first prompt"]
_p9 = {k[:2]: v for k, v in _R[9]["primary"].items() if not k.startswith("P4")}
claim(f"from {_ef['unsupported_pos']:.3f} to {_ex['unsupported_pos']:.3f}" in _AB
      and f"from {_ef['correct_determinate']:.3f} to {_ex['correct_determinate']:.3f}" in _AB, "abstract: Study 9 remedy")
claim(all(_p9[k]["outcome"] == "confirmed" for k in ("I1", "I2", "I3")) and all(_p9[k]["outcome"] == "not confirmed" for k in ("P1", "P2", "P3"))
      and all(v["outcome"] == "not confirmed" for k, v in _R[9]["primary"].items() if k.startswith("P4")), "Study 9: declared outcomes")
_dt = _bm["deterministic reading of named columns"]
claim(f"| Unsupported `pass` (I1) | {_ef['unsupported_pos']:.3f} | {_ex['unsupported_pos']:.3f} | {_dt['unsupported_pos']:.3f} |" in paper
      and f"| Correct decisions on decidable pairs (I2) | {_ef['correct_determinate']:.3f} | {_ex['correct_determinate']:.3f} | {_dt['correct_determinate']:.3f} |" in paper
      and f"| Unsupported `fail` | {_ef['unsupported_neg']:.3f} | {_ex['unsupported_neg']:.3f} | {_dt['unsupported_neg']:.3f} |" in paper
      and f"| Coverage | {_ef['coverage']:.3f} | {_ex['coverage']:.3f} | {_dt['coverage']:.3f} |" in paper
      and f"| Unnecessary abstention | {_ef['unnecessary_abstention']:.3f} | {_ex['unnecessary_abstention']:.3f} | {_dt['unnecessary_abstention']:.3f} |" in paper
      and f"| Share needing follow-up (`fail`, abstain or unanswered) | {_ef['followup_share']:.3f} | {_ex['followup_share']:.3f} | {_dt['followup_share']:.3f} |" in paper
      and f"({_ex['followup_share']:.3f} against {_ef['followup_share']:.3f}), close to the {_dt['followup_share']:.3f}" in _flat,
      "Study 9: remedy table with deterministic baseline and follow-up share")
_pm9 = _R[9]["partB_per_model"]
_e9, _x9 = _pm9["evidence-first prompt"], _pm9["extraction + solver"]
claim(f"(unsupported `pass` {_e9['gemma-4-26b-a4b-it-maas']['unsupported_pos']:.3f} to {_x9['gemma-4-26b-a4b-it-maas']['unsupported_pos']:.3f})" in _flat
      and f"({_e9['deepseek-v3.2-maas']['unsupported_pos']:.3f} to {_x9['deepseek-v3.2-maas']['unsupported_pos']:.3f})" in _flat
      and f"from {_e9['gemini-3.8-flash']['correct_determinate']:.3f} to {_x9['gemini-3.8-flash']['correct_determinate']:.3f}" in _flat
      and f"rose from {_e9['glm-5.2-maas']['unsupported_pos']:.3f} to {_x9['glm-5.2-maas']['unsupported_pos']:.3f}" in _flat,
      "Study 9: per-model trade-offs")
_sa = _R[9]["extraction_slots"]["pooled"]
_so = _sa["outcomes"]
_sm = _R[9]["extraction_slots"]["per_model"]
_sp = _R[9]["extraction_slots"]["pairs"]
claim(f"Of {_sa['slots']:,} slots, {_sa['correct']:,} were right" in _flat
      and f"{_sa['known_slots'] - _sa['known_correct'] - _so['known: value, correct, cited column does not hold it']} concern facts the record establishes ({_so['known: omitted or unparseable']} omitted, {_so['known: ABSENT']} reported absent and {_so['known: CONFLICT']}".replace(" and ", ", ") in _flat.replace(" and ", ", ")
      and f"{_so['known: value, correct, cited column does not hold it']} cite a column" in _flat
      and f"{_so['unknown: value, wrong']} invent a value" in _flat
      and f"{_sa['conflict_slots'] - _sa['conflict_correct']} miss a conflict" in _flat
      and f"Gemma 4 recognised {_sm['gemma-4-26b-a4b-it-maas']['conflict_correct']} of {_sm['gemma-4-26b-a4b-it-maas']['conflict_slots']} conflicts" in _flat
      and f"Of the {_sp['with_slot_error']} pairs with a slot error, {_sp['with_slot_error_and_wrong_verdict']} received" in _flat,
      "Study 9: slot-level extraction audit")
_dc = json.loads((ROOT / "docs" / "study9" / "differential.json").read_text())
_dcx = json.loads((ROOT / "docs" / "study9" / "decimal_correction.json").read_text())
claim(f"disagreed with the checkers on\n{_dcx['disagreements_before']['study9_random_packets']} Study 9 labels and {_dcx['disagreements_before']['study13_random_packets']} Study 13 labels".replace("\n", " ") in _flat
      and _dcx["published_labels_changed"] == 0, "decimal correction disclosed with its counts")
claim(f"({_dc['labels']:,} labels" in _flat and _dc["n_disagreements"] == 0 and _dc["permutation_changes"] == 0
      and f"on {_dc['packets']:,} random packets" in _flat, "Study 9: differential test against the independent checker")
_pre = json.loads((ROOT / "docs" / "study9" / "solver_correction.json").read_text())
claim(f"It produced {_pre['caused_by_defect']} of the remedy's then {_pre['before_unsupported_pass_count']} unsupported `pass` answers ({_pre['before_rate']:.3f})" in _flat
      and f"give {_ex['unsupported_pos']:.3f}" in _flat, "Study 9: solver correction disclosed")
claim(f"by {_p9['I3']['delta']:.3f} in correct decisions (I3)" in _flat and f"only to {_gt['unsupported_pos']:.3f}" in _flat
      and _p9["I1"]["packets_negative"] == 18 and _p9["I2"]["packets_positive"] == 17
      and "in every packet on unsupported `pass` and in 17 of 18 on correct decisions" in _flat,
      "Study 9: I3 and gate")
claim(1 - _ex["unsupported_pos"] / _ef["unsupported_pos"] > 0.8 and 1 - _ex["unsupported_neg"] / _ef["unsupported_neg"] > 0.8
      and "by more than 80%" in _flat and "without sending more items" not in _flat, "discussion: >80%, follow-up claim corrected")
_ra = _R[9]["partA_rates"]
_mods = ["gemini-3.1-pro-preview", "gemini-3.8-flash", "gemma-4-26b-a4b-it-maas", "deepseek-v3.2-maas", "glm-5.2-maas"]
_o = [_ra[f"{m}::familiar::contract_offered"]["unsupported_pos_on_unassessable"] for m in _mods]
_f = [_ra[f"{m}::familiar::contract_forced"]["unsupported_pos_on_unassessable"] for m in _mods]
claim(f"{max(_o):.3f}" == "0.009" and "at most 0.009 for every model" in _flat and f"{min(_f):.3f}–{max(_f):.3f} under the forced menu" in _flat
      and f"(−{-_p9['P1']['delta']:.3f}, not confirmed)" in _flat, "Study 9: Part A rates")
_b, _g, _m = ({k[:2]: v for k, v in _R[n]["primary"].items()} for n in (10, 11, 12))
claim(all(v["outcome"] == "not confirmed" for v in (*_b.values(), *_g.values(), _m["M1"]))
      and _m["M2"]["outcome"] == "confirmed" and _m["M2"]["packets_positive"] == 10
      and f"by only {_b['B1']['delta']:.3f}" in _flat and f"and {_b['B2']['delta']:.3f} under the forced menu" in _flat
      and f"[+{_b['B2']['ci95_packet_bootstrap'][0]:.3f}, +{_b['B2']['ci95_packet_bootstrap'][1]:.3f}]" in _flat
      and f"at most +{max(v['delta'] for v in _g.values()):.3f}" in _flat
      and f"by {_m['M2']['delta']:.3f} (M2, Holm p = {_m['M2']['p_holm']:.3f}, all ten firms)" in _flat, "Studies 10-12")
_ur = _R[12]["unsupported_pass_rate"]
claim(f"Gemma 4 from {_ur['gemma-4-26b-a4b-it-maas::abstain_offered']:.3f} to {_ur['gemma-4-26b-a4b-it-maas::abstain_offered_nomatch']:.3f}" in _flat
      and f"GLM-5.2 from {_ur['glm-5.2-maas::abstain_offered']:.3f} to {_ur['glm-5.2-maas::abstain_offered_nomatch']:.3f}" in _flat,
      "Study 12: per-model M2")
_cov = _R[9]["coverage_answered"]
def _cv(m):
    a = [v for k, v in _cov.items() if k.startswith(m + "::A::")]
    return sum(a) / (24 * len(a))
claim(f"{_cv('gemma-4-26b-a4b-it-maas'):.2f} and {_cv('glm-5.2-maas'):.2f}" in _flat, "Study 9: Part A coverage")
claim("table-study9" in paper and _lv["labels"] == 2304 and "All 2,304 labels of Studies 9 and 11" in _flat, "Study 9/11 label agreement")

_cm = _R[12]["M2_contemporaneous_baseline_addendum"]
claim(f"the estimate was +{_cm['delta']:.3f} [+{_cm['ci95_packet_bootstrap'][0]:.3f}, +{_cm['ci95_packet_bootstrap'][1]:.3f}] (exact p = {_cm['p_exact_two_sided']:.3f}, nine of ten firms)" in _flat
      and _cm["packets_positive"] == 9, "Study 12: contemporaneous baseline")

# Study 13: held-out rules and layouts (declared, with a declared replication)
_r13 = json.loads((ROOT / "docs" / "study13" / "results.json").read_text())
_q13 = json.loads((ROOT / "docs" / "study13" / "results_r2.json").read_text())
_lc13 = json.loads((ROOT / "docs" / "study13" / "label_check.json").read_text())
_P13, _P013, _PH13 = (list(x.values()) for x in (_q13["primary"], _r13["primary"], _r13["posthoc_name_normalised"]["primary"]))
_EF13, _EX13 = "contract13b_evidence_first", "contract13b_extract"
_h13, _bl13, _pm13 = _q13["summary_heldout"], _q13["by_layout"], _q13["per_model_heldout"]
_ci13 = lambda v: f"[{v['ci95_packet_bootstrap'][0]:+.3f}, {v['ci95_packet_bootstrap'][1]:+.3f}]"
_n113 = _q13["N1 non-inferiority: extraction + solver - parser, unsupported pass, upper bound < +0.02"]
_b13 = _lc13["by_study"]["13"]
claim(_lc13["labels"] == _lc13["agree"] and _lc13["certificates"] == _lc13["certificates_verified"]
      and _b13["labels"] == _b13["agree"] == 480 and _b13["completions"] == _b13["completions_verified"] == 198
      and _lc13["fuzz_disagreements"] == 0 and _lc13["fuzz_permutation_changes"] == 0 and _lc13["fuzz_labels"] == 18000
      and "All 480 labels agree" in _flat and "all 198 certificate completions verify" in _flat
      and "agree on all 18,000 labels" in _flat, "Study 13: labels, certificates and random packets")
claim(all(v["outcome"] == "confirmed" for v in _P13) and _n113["outcome"] == "confirmed"
      and _P013[0]["outcome"] == "confirmed" and _P013[1]["outcome"] == _P013[2]["outcome"] == "not confirmed",
      "Study 13: outcomes as stated (replication H1-H3, N1 confirmed; first run H2, H3 not)")
claim(f"fell by {-_P13[0]['delta']:.3f} {_ci13(_P13[0])}, in all 18 packets" in _flat and _P13[0]["packets_negative"] == 18
      and f"rose by {_P13[1]['delta']:.3f} {_ci13(_P13[1])}" in _flat
      and f"rose by {_P13[2]['delta']:.3f} {_ci13(_P13[2])}, in all 18 packets" in _flat and _P13[2]["packets_positive"] == 18
      and all(_pm13[m]["H2"]["ci95_packet_bootstrap"][0] > 0 for m in _pm13)
      and f"{_n113['delta']:+.3f} {_ci13(_n113)}" in _flat, "Study 13: declared tests in the text")
claim(f"({_P013[1]['delta']:+.3f} and {_P013[2]['delta']:+.3f})" in _flat
      and f"gave {_PH13[1]['delta']:+.3f} and {_PH13[2]['delta']:+.3f}" in _flat, "Study 13: first run, declared and post hoc")
claim(f"by {-_P13[0]['delta']:.3f} [" in _flat and f"rose by {_P13[1]['delta']:.3f} [" in _flat, "Study 13: effects in the text")
_ex13 = [_bl13[l][_EX13]["correct_determinate"] for l in ("L4", "L5", "L6")]
claim(all(_bl13[l]["parser"]["correct_determinate"] == 1.0 for l in ("L1", "L2", "L3"))
      and f"{_bl13['L4']['parser']['correct_determinate']:.3f}, {_bl13['L5']['parser']['correct_determinate']:.3f} and" in _flat
      and f"{_bl13['L6']['parser']['correct_determinate']:.3f} on L4, L5 and L6" in _flat
      and f"between {min(_ex13):.3f} and {max(_ex13):.3f}" in _flat
      and f"fell by up to {1 - _bl13['L6']['parser']['correct_determinate']:.3f}" in _flat, "Study 13: parser by layout")
_sa13 = _q13["slot_audit"]["models::heldout"]
_bp13 = _q13["correct_by_pattern_heldout"]
claim(f"{_h13['parser']['unsupported_pos']:.3f} against {_h13[_EX13]['unsupported_pos']:.3f}" in _flat
      and f"beats extraction by {-_q13['development_layouts']['extraction - parser: correct decisions']['delta']:.3f}" in _flat
      and f"decided {_bp13[_EX13]['conflict_top_dup']:.3f} of pairs" in _flat
      and f"and {_bp13[_EX13]['conflict_unresolved']:.3f} where" in _flat
      and f"against {_bp13['parser']['conflict_top_dup']:.3f} and {_bp13['parser']['conflict_unresolved']:.3f} for the parser" in _flat
      and f"{_sa13['correct']:,} of {_sa13['slots']:,} extracted facts" in _flat
      and f"gave\n{_h13['hybrid']['correct_determinate']:.3f}".replace("\n", " ") in _flat
      and f"of {_h13['hybrid']['unsupported_pos']:.3f}." in _flat, "Study 13: failures, audit and hybrid")
_cc13 = _q13["content_clustered_posthoc"]
_ps13 = _q13["per_model_safety_vs_parser"]
claim(all(_cc13[h]["n_contents"] == 6 and _cc13[h]["p_exact_two_sided"] == 0.03125 and abs(_cc13[h]["p_holm"] - 0.09375) < 1e-12
          for h in ("H1", "H2", "H3"))
      and _cc13["H1"]["contents_negative"] == _cc13["H2"]["contents_positive"] == _cc13["H3"]["contents_positive"] == 6
      and "after Holm\ncorrection p = 0.094 for each".replace("\n", " ") in _flat and "smallest attainable exact p is 0.031" in _flat
      and _cc13["N1"]["ci95_content_bootstrap"][1] < 0.02
      and _ps13["gemma-4-26b-a4b-it-maas"]["delta"] > 0 and _ps13["deepseek-v3.2-maas"]["delta"] > 0,
      "Study 13: content-clustered correction as stated")
_g13, _d13 = _pm13["gemma-4-26b-a4b-it-maas"], _pm13["deepseek-v3.2-maas"]
_tk13 = _q13["tokens_per_pair"]
claim(f"from {_g13[_EF13]['unsupported_pos']:.3f} to {_g13[_EX13]['unsupported_pos']:.3f}" in _flat
      and f"from {_d13[_EF13]['unsupported_pos']:.3f} to {_d13[_EX13]['unsupported_pos']:.3f}" in _flat
      and all(_pm13[m][s]["unsupported_pos"] == 0 and _pm13[m][_EX13]["correct_determinate"] == 1.0
              for m in ("gemini-3.1-pro-preview", "gemini-3.8-flash", "glm-5.2-maas") for s in (_EF13, _EX13))
      and f"{_tk13['gemini-3.8-flash::' + _EX13]['output']:.0f} against {_tk13['gemini-3.8-flash::' + _EF13]['output']:.0f} per pair" in _flat
      and all(_tk13[f"{m}::{_EX13}"]["output"] < _tk13[f"{m}::{_EF13}"]["output"]
              for m in ("gemini-3.1-pro-preview", "gemini-3.8-flash", "glm-5.2-maas"))
      and all(1.5 < _tk13[f"{m}::{_EX13}"]["output"] / _tk13[f"{m}::{_EF13}"]["output"] < 2.5
              for m in ("gemma-4-26b-a4b-it-maas", "deepseek-v3.2-maas")), "Study 13: by model and tokens")

# Study 14: the powered transfer test
_r14 = json.loads((ROOT / "docs" / "study14" / "results.json").read_text())
_pw14 = json.loads((ROOT / "docs" / "study14" / "power.json").read_text())
_P14 = list(_r14["primary"].values())
_s14, _sf14, _pm14, _bl14 = _r14["summary"], _r14["safety_per_model"], _r14["per_model"], _r14["by_layout"]
_EX14, _cg14, _lf14 = "contract13b_extract", _r14["codegen"], _r14["layout_families"]
_ci14 = lambda v: f"[{v['ci95_content_bootstrap'][0]:+.3f}, {v['ci95_content_bootstrap'][1]:+.3f}]"
_b14 = _lc13["by_study"]["14"]
claim(all(v["n_contents"] == 30 and v["p_holm"] < 0.001 for v in _P14)
      and [v["outcome"] for v in _P14] == ["confirmed", "confirmed", "confirmed", "difference"] and _P14[3]["delta"] > 0
      and "All four declared tests reached Holm p < 0.001 over contents" in _flat
      and _b14["labels"] == _b14["agree"] == 960 and "All 960 labels agree" in _flat
      and min(_pw14["30"][h] for h in ("H1", "H2", "H3")) == 0.94 and "power was at least 0.94 for H1–H3" in _flat, "Study 14: tests, labels and power")
claim(f"{-_P14[0]['delta']:.3f} {_ci14(_P14[0])}, in all 30 contents" in _flat and _P14[0]["contents_negative"] == 30
      and f"{_P14[1]['delta']:.3f} {_ci14(_P14[1])} more correct decisions" in _flat
      and f"by {_P14[2]['delta']:.3f} {_ci14(_P14[2])}, reaching {_s14['hybrid']['correct_determinate']:.3f}" in _flat
      and f"made {_P14[3]['delta']:.3f} {_ci14(_P14[3])} more correct" in _flat
      and f"reached {_s14['parser']['correct_determinate']:.3f} on the new ones" in _flat
      and f"({_s14['parser, Study 13']['correct_determinate']:.3f})" in _flat
      and _s14["parser, Study 13"]["correct_determinate"] > _s14["parser"]["correct_determinate"], "Study 14: effects in the text")
_cgc14 = {}
for _f in sorted((ROOT / "docs" / "study14" / "codegen_cache").glob("*.json")):
    _cgc14.update(json.loads(_f.read_text()))
_len14 = sum(v["finish_reason"] == "length" for k, v in _cgc14.items() if "glm-5.2" in k)
_rb14 = _cg14["reuse_breakdown"]
_fl14 = _pm14["gemini-3.8-flash"]
claim(f"({'ten' if _len14 == 10 else _len14} GLM-5.2 replies reached it)" in _flat
      and sum(v["finish_reason"] == "length" for v in _cgc14.values()) == _len14
      and f"so {_rb14['answered only the original packet' + chr(39) + 's pairs']} of the programs answered the original" in _flat
      and f"({_cg14['programs_with_literal_entity_ids']} had copied its identifiers) and only {_rb14['answered the new packet' + chr(39) + 's pairs']} answered" in _flat
      and f"made no unsupported `pass`\nand decided {_fl14['contract13b_evidence_first']['correct_determinate']:.3f}".replace("\n", " ") in _flat
      and _fl14["contract13b_evidence_first"]["unsupported_pos"] == _fl14[_EX14]["unsupported_pos"] == 0
      and f"against {_fl14[_EX14]['correct_determinate']:.3f} with extraction" in _flat, "Study 14: H4 scope, reuse breakdown, Flash")
claim(f"Of 300 replies, {_cg14['with_program']} contained a program" in _flat and f"{_cg14['ran_cleanly']} ran without error" in _flat
      and f"decided {_cg14['reuse_correct_determinate']:.3f} of decidable pairs" in _flat
      and f"five of six layouts (exact p = {_lf14['extraction - parser']['p_exact_two_sided_over_layouts']:.3f}" in _flat
      and _lf14["extraction - parser"]["layouts_positive"] == 5 and _lf14["extraction - parser"]["by_layout"]["B1"] < 0
      and f"from {min(_bl14[l][_EX14]['correct_determinate'] for l in _bl14):.3f} to" in _flat
      and min(_bl14, key=lambda l: _bl14[l][_EX14]["correct_determinate"]) == "C1", "Study 14: code generation and layouts")
_ok14 = [m for m in _pm14 if _sf14[f"{_EX14}::{m}"]["meets_margin"]]
claim(sorted(_ok14) == ["gemini-3.1-pro-preview", "gemini-3.8-flash", "glm-5.2-maas"]
      and all(_sf14[f"hybrid::{m}"]["meets_margin"] == (m in _ok14) for m in _pm14)
      and f"({_s14['parser']['unsupported_pos']:.3f})" in _flat
      and f"excess\n{_sf14[_EX14 + '::gemma-4-26b-a4b-it-maas']['delta']:+.3f} {_ci14(_sf14[_EX14 + '::gemma-4-26b-a4b-it-maas'])}".replace("\n", " ") in _flat
      and f"{_pm14['gemma-4-26b-a4b-it-maas'][_EX14]['correct_determinate']:.3f} and {_pm14['deepseek-v3.2-maas'][_EX14]['correct_determinate']:.3f}" in _flat,
      "Study 14: per-model safety criterion")
claim(f"by\n{-_P14[0]['delta']:.3f} against the strongest prompt".replace("\n", " ") in _AB
      and f"made {_P14[1]['delta']:.3f} more correct" in _AB and f"and {_P14[3]['delta']:.3f} more than" in _AB
      and "for two of five models it cost some safety" in _AB, "abstract: Study 14")
claim(f"decided {_s14['parser']['correct_determinate']:.3f} of decidable pairs correctly\nand extraction {_s14[_EX14]['correct_determinate']:.3f}".replace("\n", " ") in _flat,
      "discussion: Study 14")

# Study 15: real public records in native formats (corrected run primary; first run defective)
_r15 = json.loads((ROOT / "docs" / "study15" / "results_r2.json").read_text())
_r15a = json.loads((ROOT / "docs" / "study15" / "results.json").read_text())
_au15 = json.loads((ROOT / "docs" / "study15" / "input_audit.json").read_text())
_pw15 = json.loads((ROOT / "docs" / "study15" / "power.json").read_text())
_P15, _P15a = list(_r15["primary"].values()), list(_r15a["primary"].values())
_s15, _b15, _sf15, _cg15, _sa15, _mo15, _zb15 = (_r15[k] for k in ("summary", "by_source", "safety_per_model", "codegen",
                                                                   "slot_audit", "needs_evidence_by_origin", "zero_event_bounds"))
_EX15, _EF15, _CG15 = "contract15_extract", "contract15_evidence_first", "codegen15b"
_ci15 = lambda v: f"[{v['ci95_packet_bootstrap'][0]:+.3f}, {v['ci95_packet_bootstrap'][1]:+.3f}]"
_lab15 = sum(sum(v.values()) for v in _r15["label_counts"].values())
claim(_lab15 == 1200 and "All 1,200 labels agree" in _flat and all(v["n_packets"] == 50 for v in _P15)
      and [v["outcome"] for v in _P15] == ["confirmed", "not confirmed", "confirmed"] and _P15[1]["p_holm"] > 0.05
      and _P15a[1]["delta"] < 0 and _P15a[1]["p_holm"] < 0.05, "Study 15: outcomes (corrected H2 null; first run reversed)")
claim(_au15["requests"] == _au15["hash_match"] == _au15["full_document"] == _au15["all_records"]
      and _au15["codegen"]["calls"] == _au15["codegen"]["full_document"] == _au15["codegen"]["hash_match"]
      and f"all {_au15['requests']} retained prompt requests and all {_au15['codegen']['calls']} code-generation calls, the {_au15['codegen']['repair_calls']} repair prompts" in _flat
      and f"code generation ahead by {-_P15a[1]['delta']:.3f}" in _flat, "Study 15: input audit and the defect disclosed")
claim(f"by\n  {-_P15[0]['delta']:.3f} {_ci15(_P15[0])}, in all 50 packets".replace("\n  ", " ") in _flat
      and _P15[0]["packets_negative"] == 50 and _P15[2]["packets_positive"] == 50
      and f"made {_P15[2]['delta']:.3f} {_ci15(_P15[2])} more correct" in _flat
      and f"(difference {_P15[1]['delta']:+.3f} {_ci15(_P15[1])}, Holm p = {_P15[1]['p_holm']:.2f})" in _flat
      and f"{_s15[_EX15]['correct_determinate']:.3f} of decidable pairs correctly and the model-written parsers {_s15[_CG15]['correct_determinate']:.3f}" in _flat,
      "Study 15: tests in the text")
_g15, _d15 = "gemma-4-26b-a4b-it-maas", "deepseek-v3.2-maas"
_l15 = _sa15["extraction::lca"]["outcomes"]
claim(all(_r15["per_model"][m][_CG15]["unsupported_pos"] == 0 for m in _r15["per_model"])
      and f"bound is {_zb15[_CG15 + '::' + _g15]['upper95_per_pair_if_zero']:.4f} per pair" in _flat
      and f"{_zb15[_CG15 + '::' + _g15]['upper95_per_packet_if_zero']:.3f} per packet" in _flat
      and f"{_sf15[_EX15 + '::' + _g15]['rate']:.3f} for Gemma 4 and" in _flat and not _sf15[_EX15 + "::" + _g15]["meets_margin"]
      and not _sf15[_EX15 + "::" + _d15]["meets_margin"]
      and f"where {_l15['wrong value (date), record has one']} of {sum(x for k, x in _l15.items() if k.startswith('known')):,} values" in _flat
      and f"{_cg15['clean_first_call']} programs ran cleanly at the first call and {_cg15['clean_final']} after a second call" in _flat
      and f"decided\n{_cg15['reuse_correct_determinate']:.3f}".replace("\n", " ") in _flat
      and f"unsafe for Gemma 4 ({_sf15[_EF15 + '::' + _g15]['rate']:.3f})" in _flat
      and f"{_mo15[_EF15]['missing at source']['unsupported_pass']:.3f} where evidence was missing at source (ten items)" in _flat
      and _mo15[_EF15]["missing at source"]["pairs"] == 50, "Study 15: safety, LCA dates, repair and origin")
_cp15 = _au15["completions"]
_glx, _glc = _cp15["glm-5.2-maas::contract15_extract"], _cp15["glm-5.2-maas::codegen15b"]
_capped15 = sum(v["capped_completions"] for k, v in _cp15.items() if "contract15" in k)
claim(f"The {_capped15} prompt completions that reached the output cap" in _flat
      and f"made {_glx['completions']} completions for {_glx['planned_batches']} batches, retrying {_glx['capped_completions']} capped" in _flat
      and f"while {_glc['capped_completions']} of its {_glc['completions']} code-generation calls reached the cap" in _flat
      and all(v["capped_completions"] == 0 for k, v in _cp15.items() if not k.startswith("glm-5.2")),
      "Study 15: completion accounting and the GLM-5.2 asymmetry")
_h2m15, _h2x15, _pmc15 = _r15["h2_per_model"], _r15["h2_without_capped_models"], _r15["per_model"]
_neg = lambda v: f"[{-v['ci95_packet_bootstrap'][1]:+.3f}, {-v['ci95_packet_bootstrap'][0]:+.3f}]"
claim(f"generation was ahead by {-_h2m15[_g15]['delta']:.3f} {_neg(_h2m15[_g15])} for Gemma 4, extraction by" in _flat
      and f"{_h2m15['glm-5.2-maas']['delta']:.3f} for GLM-5.2, whose programs answered only {_pmc15['glm-5.2-maas'][_CG15]['coverage']:.3f}" in _flat
      and all(_h2m15[m]["delta"] == 0 for m in ("gemini-3.1-pro-preview", "gemini-3.8-flash"))
      and _h2x15["excluded"] == ["glm-5.2-maas"]
      and f"code generation was ahead by {-_h2x15['delta']:.3f}\n  {_neg(_h2x15)} (post hoc)".replace("\n  ", " ") in _flat,
      "Study 15: per-model H2 and the matched-resource sensitivity")
claim(f"(by {-_P15[0]['delta']:.3f}) and raised correct decisions (by {_P15[2]['delta']:.3f})" in _AB
      and "no unsupported positive in 6,000 evaluated pairs" in _AB and "6,000 decisions" not in _flat
      and f"({_capped15} capped Study 15 completions that were re-requested are counted but not kept" in _AB
      and sum(_zb15[f"{_CG15}::{m}"]["pairs"] for m in _r15["per_model"]) == 6000
      and f"({_s15[_CG15]['correct_determinate']:.3f} against {_s15[_EX15]['correct_determinate']:.3f})" in _AB
      and "equally accurate" not in _flat and "as accurate" not in _AB, "abstract: Study 15, no equivalence claim")
claim(_pw15["50"]["H2 (gap quartered)"] == 0.487 and "the power analysis gave 0.49 for a gap a quarter" in _flat
      and f"answered only {_pmc15['glm-5.2-maas'][_CG15]['coverage']:.3f} of pairs, against\n{_pmc15['glm-5.2-maas'][_EX15]['coverage']:.3f} for extraction".replace("\n", " ") in _flat,
      "Study 15: power and the coverage trade-off in the discussion")

# no stray percentages that we have not verified
pcts = set(re.findall(r"\b\d+\.\d\s?%", paper))
claim(pcts <= {f"{_nw / _np:.1%}"}, f"only verified percentages appear (found {sorted(pcts)})")

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
