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
claim(len(_nums) == 12, f"12 numbered sections, contiguous (got {len(_nums)})")
claim([int(_re.match(r"^## (\d+)\.", h).group(1)) for h in _nums] == list(range(1, 13)),
      "section numbers run 1..12 with no gaps or repeats")
claim("## 2. Related work" in paper, "Related work is a real section, not an appendix stub")
claim("Appendix B: Related work to engage" not in paper, "the old related-work stub is gone")
for t in ("Table 1", "Table 2", "Table 3", "Table 4", "Table 7", "Table 8", "Figure 1"):
    claim(t in paper, f"{t} is named in the paper")
claim("[\u2026]" not in paper and "[…]" not in paper, "no empty result cell remains")
_bad = _re.findall(r"Section \d+", paper)
_maxsec = max(int(x.split()[1]) for x in _bad)
claim(_maxsec <= 12, f"no cross-reference points past section 12 (max {_maxsec})")

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

print("\nhonesty checks")
claim("[TO RUN]" not in paper and "`[…]`" not in paper, "no unfilled placeholder remains")
claim("have not yet been run" not in paper and "has not been run" not in paper,
      "paper no longer claims the LM experiments are unrun")
_t2 = paper[paper.index("BEGIN GENERATED: table2-main"):paper.index("END GENERATED: table2-main")]
claim(all(f"`{k.split('/')[-1].split('::')[0].replace(':free', '')}`" in _t2
          for k in _fin if k.endswith("offered")), "Table 2 has a row for every finished offered run")
_V = json.loads((ROOT / "docs" / "studies_results.json").read_text())["vertex"]
_vm = lambda cond, metric: [_V[k]["summary"][metric]["mean"] for k in _V if f"study1::{cond}" in k]  # noqa: E731
_ab = paper[paper.index("## Abstract"):paper.index("## 1. Introduction")].replace("\n", " ")
_o = [v["engine"]["false_green_rate"] for v in _off.values()] + _vm("abstain_offered", "false_green_rate")
_r = [v["engine"]["violation_recall"] for v in _off.values()] + _vm("abstain_offered", "violation_recall")
_w = [v["engine"]["false_green_rate"] for v in _wit.values()] + _vm("abstain_withheld", "false_green_rate")
for _lab, _xs in (("offered FGR", _o), ("offered recall", _r), ("dashboard FGR", _w)):
    claim(f"{min(_xs):.3f} to {max(_xs):.3f}" in _ab, f"abstract {_lab} range {min(_xs):.3f}-{max(_xs):.3f} (9 models)")
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
