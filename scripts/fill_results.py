"""Fill the paper's result tables from docs/llm_results.json.

The paper's Tables 2-5 are generated, never hand-typed. A number that appears
in the paper is therefore a number the harness produced, and re-running this
after new results keeps prose and artifact in lockstep.

Rows are emitted only for runs that actually exist. A model that has not been
run does not appear, rather than appearing with an invented value.

    python3 scripts/fill_results.py            # rewrites tables in docs/PAPER.md
    python3 scripts/fill_results.py --dry-run  # print, change nothing
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

PAPER = ROOT / "docs" / "PAPER.md"
LLM = ROOT / "docs" / "llm_results.json"
TRIV = ROOT / "docs" / "results.json"
VIEWS = ROOT / "docs" / "views_results.json"

# Markers delimit generated regions so regeneration never eats hand-written prose.
BEGIN = "<!-- BEGIN GENERATED: {name} -->"
END = "<!-- END GENERATED: {name} -->"


def disp(name: str) -> str:
    """Display name for a model id (tables use the names the figures use)."""
    return NAMES.get(name, name)


def short(model: str) -> str:
    return model.split("/")[-1].replace(":free", "")


def cell(agg: dict, key: str) -> str:
    a = agg.get(key)
    if not a:
        return "—"
    if a.get("n_firms", 1) > 1 and a.get("stdev"):
        return f"{a['mean']:.3f} ± {a['stdev']:.3f}"
    return f"{a['mean']:.3f}"


def load_runs() -> dict:
    if not LLM.exists():
        return {}
    return json.loads(LLM.read_text()).get("runs", {})


def table_trivial() -> str:
    """Table 1: trivial baselines over the anchor and 30 generated firms."""
    t = json.loads(TRIV.read_text())["systems"]
    rows = ["| System | False green | Violation recall | Precision | False alarm | Abstention F1 |",
            "|---|---|---|---|---|---|"]
    for name in ("always_pass", "always_abstain", "always_fail", "oracle"):
        cells = []
        for k in ("false_green_rate", "violation_recall", "violation_precision",
                  "false_alarm_rate", "abstention_f1"):
            m = t[name][k]["mean"]
            cells.append("—" if m is None else f"{m:.3f}")
        rows.append(f"| `{name}` | " + " | ".join(cells) + " |")
    rows.append("")
    rows.append("A dash marks a rate undefined for that system: `always_pass` and `always_abstain` "
                "never predict a violation, so their precision has no denominator.")
    return "\n".join(rows)


def table_main(runs: dict) -> str:
    """Table 2: main result under abstain_offered."""
    rows = [
        "| Model | False green | FG, answered only | Recall | Precision | False alarm | Abst. P | Abst. R | Abst. F1 | Unparse. | Answered |",
        "|---|---|---|---|---|---|---|---|---|---|---|",
    ]
    offered = {k: v for k, v in runs.items()
               if v["variant"].endswith("offered") and v.get("aggregate")}
    if not offered:
        rows.append("| `[TO RUN]` | `[…]` | `[…]` | `[…]` | `[…]` | `[…]` | `[…]` | `[…]` | `[…]` | `[…]` | `[…]` |")
    views = json.loads(VIEWS.read_text()).get("runs", {}) if VIEWS.exists() else {}
    for key in sorted(offered, key=lambda k: short(offered[k]["model"])):  # alphabetical: models are not ranked
        r = offered[key]
        a = r["aggregate"]
        unp = r.get("n_unparseable", 0) / max(r.get("n_pairs", 1), 1)
        answered = sum(f["n_parsed"] for f in r["per_firm"])
        n_pairs = sum(f["n_pairs"] for f in r["per_firm"])
        ev = (views.get(key) or {}).get("engine", {})
        fga = ev.get("false_green_rate_answered")
        fga_s = "—" if fga is None else f"{fga:.3f}"
        ci = lambda c: f" [{c[0]:.2f}, {c[1]:.2f}]" if c else ""  # noqa: E731
        rows.append(
            f"| {disp(short(r['model']))} | **{cell(a,'false_green_rate')}**{ci(ev.get('fgr_ci95'))} | {fga_s} "
            f"| {cell(a,'violation_recall')}{ci(ev.get('recall_ci95'))} "
            f"| {cell(a,'violation_precision')} | {cell(a,'false_alarm_rate')} "
            f"| {cell(a,'abstention_precision')} | {cell(a,'abstention_recall')} "
            f"| {cell(a,'abstention_f1')} | {unp:.3f} | {answered}/{n_pairs} |"
        )
    # Reference rows scored on the SAME 140-pair anchor subset as the models above.
    from baselines.trivial import REGISTRY
    from nofalsegreen import northwind
    from nofalsegreen.metrics import score
    from nofalsegreen.rulebook import Rulebook
    from nofalsegreen.subset import subset_firm
    anchor_dir = ROOT / "data" / "firms" / "northwind-robotics"
    rb = Rulebook.load(ROOT / "rulebook" / "rulebook.json")
    sub = subset_firm(northwind.load(anchor_dir, anchor_dir / "expectations.json"), rb.rule_regimes())
    for name in ("always_pass", "oracle"):
        r = score(sub.labels, REGISTRY[name](sub))
        prec = f"{r.violation_precision:.3f}" if name == "oracle" else "—"
        rows.append(
            f"| `{name}` (ref) | {r.false_green_rate:.3f} | {r.false_green_rate:.3f} "
            f"| {r.violation_recall:.3f} | {prec} | {r.false_alarm_rate:.3f} "
            f"| {r.abstention_precision:.3f} | {r.abstention_recall:.3f} | {r.abstention_f1:.3f} "
            f"| 0.000 | {len(sub.pairs)}/{len(sub.pairs)} |"
        )
    return "\n".join(rows)


def table_ablation(runs: dict) -> str:
    """Table 3: schema ablation, paired on withheld pairs answered in BOTH conditions."""
    abl = json.loads(VIEWS.read_text()).get("ablation", {}) if VIEWS.exists() else {}
    rows = [
        "| Model | Unassessable pairs answered in both | FGR offered | FGR dashboard | Change [95% CI] "
        "| Holm-adjusted p | Off-schema replies (dashboard) |",
        "|---|---|---|---|---|---|---|",
    ]
    by_model: dict[str, dict] = {}
    for r in runs.values():
        if r.get("aggregate"):
            by_model.setdefault(r["model"], {})["o" if r["variant"].endswith("offered") else "w"] = r
    views = json.loads(VIEWS.read_text())["runs"] if VIEWS.exists() else {}
    for m, a in sorted(abl.items()):
        if m not in by_model or "w" not in by_model[m]:
            continue
        w = by_model[m]["w"]
        offs = sum(f.get("n_off_schema", 0) for f in w["per_firm"])
        ans = sum(f["n_parsed"] for f in w["per_firm"])
        n, d, c = a["n_pairs_answered_both"], a["delta_fgr"], a["ci95"]
        # rates on the same restricted pair set
        fo = views[f"{m}::abstain_offered"]["engine"]
        rows.append(f"| {disp(short(m))} | {n} of 120 | {views[f'{m}::abstain_offered']['engine']['false_green_rate']:.3f} "
                    f"| {views[f'{m}::abstain_withheld']['engine']['false_green_rate']:.3f} "
                    f"| {d:+.3f} [{c[0]:+.2f}, {c[1]:+.2f}] | {a['p_holm']:.3f} | {offs} of {ans} answered |")
    rows.append("")
    rows.append("FGR columns are over all 120 unassessable pairs. The change, its interval "
                "(obligation-cluster bootstrap, 2,000 draws) and the two-sided p-value (Holm across the six "
                "models) are computed on the unassessable pairs both runs answered; the bootstrap p-value "
                "has a floor of 1/2,000.")
    return "\n".join(rows)


def table_regime(runs: dict) -> str:
    """Table 4: false-green rate by regulatory regime."""
    offered = [r for r in runs.values()
               if r["variant"].endswith("offered") and r.get("per_firm")]
    if not offered:
        return ("| Regime | `[TO RUN]` |\n|---|---|\n"
                "| *ten rows, one per regime, one column per model* | `[…]` |")

    regimes: set[str] = set()
    for r in offered:
        for f in r["per_firm"]:
            regimes |= set(f.get("per_regime", {}))
    regimes.discard("unknown")

    header = "| Regime | " + " | ".join(disp(short(r['model'])) for r in offered) + " |"
    rows = [header, "|---" * (len(offered) + 1) + "|"]
    for regime in sorted(regimes):
        cells = []
        for r in offered:
            vals, pairs = [], 0
            for f in r["per_firm"]:
                pr = f.get("per_regime", {}).get(regime)
                if pr and pr.get("n_pairs"):
                    vals.append(pr["false_green_rate"])
                    pairs += pr["n_pairs"]
            cells.append(f"{sum(vals)/len(vals):.3f} ({pairs})" if vals else "—")
        rows.append(f"| `{regime}` | " + " | ".join(cells) + " |")
    rows.append("")
    rows.append("Cells are the false-green rate over the regime's unassessable pairs; in parentheses, "
                "the regime's scored pairs of any label.")
    return "\n".join(rows)


def table_views() -> str:
    """Table 2b: engine vs strict label views, plus the deadline alerts."""
    head = ("| Model | Condition | FGR, engine | FGR, strict | Recall, engine (of 20) "
            "| Recall, strict (of 10) | Alerts: fail / pass / other |\n|---|---|---|---|---|---|---|")
    if not VIEWS.exists():
        return head + "\n| `[TO RUN]` | `[…]` | `[…]` | `[…]` | `[…]` | `[…]` | `[…]` |"
    runs = json.loads(VIEWS.read_text()).get("runs", {})
    # A run is listed once the sweep has recorded it as finished, even if some
    # pairs went unanswered: dropping it would hide exactly the runs whose
    # delivery failed. Unfinished (deferred) runs are not listed.
    finished = {k for k, v in load_runs().items() if v.get("per_firm")}
    rows = [head]
    for key in sorted(runs):
        r = runs[key]
        if key not in finished:
            continue
        e, st = r["engine"], r["strict"]
        v = st.get("deadline_alerts", {}).get("verdicts", {})
        other = sum(n for k, n in v.items() if k not in ("fail", "pass"))
        cond = "offered" if r["variant"].endswith("offered") else "dashboard"
        rows.append(
            f"| {disp(short(r['model']))} | {cond} | {e['false_green_rate']:.3f} | {st['false_green_rate']:.3f} "
            f"| {e['violation_recall']:.2f} | {st['violation_recall']:.2f} "
            f"| {v.get('fail', 0)} / {v.get('pass', 0)} / {other} |"
        )
    if len(rows) == 1:
        rows.append("| `[TO RUN]` | `[…]` | `[…]` | `[…]` | `[…]` | `[…]` | `[…]` |")
    return "\n".join(rows)


def table_audited() -> str:
    """Table 2c: engine view vs the blind-audit view (docs/LABEL_AUDIT_PROTOCOL.md)."""
    head = ("| Model | Condition | Unassessable pairs scored | FGR, engine | FGR, audited "
            "| FG, audited, answered only |\n|---|---|---|---|---|---|")
    if not VIEWS.exists():
        return head + "\n| `[TO RUN]` | `[…]` | `[…]` | `[…]` | `[…]` | `[…]` |"
    runs = json.loads(VIEWS.read_text()).get("runs", {})
    finished = {k for k, v in load_runs().items() if v.get("per_firm")}
    rows = [head]
    for key in sorted(runs):
        r = runs[key]
        if key not in finished or "audited" not in r:
            continue
        e, au = r["engine"], r["audited"]
        fga = au.get("false_green_rate_answered")
        cond = "offered" if r["variant"].endswith("offered") else "dashboard"
        rows.append(
            f"| {disp(short(r['model']))} | {cond} | {au['n_withheld']} of {e['n_withheld']} "
            f"| {e['false_green_rate']:.3f} | {au['false_green_rate']:.3f} "
            f"| {'—' if fga is None else f'{fga:.3f}'} |")
    if len(rows) == 1:
        rows.append("| `[TO RUN]` | `[…]` | `[…]` | `[…]` | `[…]` | `[…]` |")
    return "\n".join(rows)


STUDIES = ROOT / "docs" / "studies_results.json"


def _f(x, nd=3):
    return "—" if x is None else f"{x:.{nd}f}"


def table_study2() -> str:
    """Table 6: Study 2, free-tier models, six generated firms (mean ± sd over firms)."""
    head = ("| Model | Condition | False green | Recall | False alarm, all controls "
            "| False alarm, near-miss | Abst. F1 | Answered |\n|---|---|---|---|---|---|---|---|")
    if not STUDIES.exists():
        return head
    rows = [head]
    for key, r in sorted(json.loads(STUDIES.read_text())["study2"].items()):
        model, variant = key.split("::")
        m = r["mean_over_firms"]
        ms = lambda k: (f"{m[k]['mean']:.3f} ± {m[k]['sd']:.3f}" if m[k]["sd"] is not None  # noqa: E731
                        else _f(m[k]["mean"]))
        cond = "offered" if variant.endswith("offered") else "dashboard"
        rows.append(f"| {disp(short(model))} | {cond} | {ms('false_green_rate')} | {ms('violation_recall')} "
                    f"| {ms('false_alarm_rate')} | {ms('false_alarm_near_miss')} | {ms('abstention_f1')} "
                    f"| {r['pooled']['answered']}/{r['pooled']['n']} |")
    return "\n".join(rows)


COND = {"abstain_offered": "offered", "abstain_removed_only": "removed-only",
        "abstain_closed": "closed", "abstain_withheld": "dashboard"}


def table_vertex() -> str:
    """Table 7: Vertex block, four schema conditions, mean of three repeats [min, max],
    with where the withheld pairs went (mean count over repeats)."""
    head = ("| Model | Study | Schema | False green | FG, answered only | Recall | False alarm, near-miss "
            "| Unassessable pairs answered pass / fail / needs_ev. / unmon. | Min answered |"
            "\n|---|---|---|---|---|---|---|---|---|")
    if not STUDIES.exists():
        return head
    rows = [head]
    data = json.loads(STUDIES.read_text())["vertex"]
    order = list(COND)
    keys = sorted(data, key=lambda k: (k.split("::")[0], k.split("::")[1], order.index(k.split("::")[2])))
    for key in keys:
        r = data[key]
        model, study, variant = key.split("::")
        a = r["summary"]
        cell = lambda k: ("—" if not a[k] else  # noqa: E731
                          f"{a[k]['mean']:.3f} [{a[k]['min']:.3f}, {a[k]['max']:.3f}]")
        n = 140 if study == "study1" else 252
        reps = r["repeats"]
        dist = " / ".join(
            f"{sum(x['counts'].get('withheld_as_' + v, 0) for x in reps) / len(reps):.0f}"
            for v in ("pass", "fail", "needs_evidence", "unmonitored"))
        rows.append(f"| {disp(model.replace('vertex/', ''))} | {study[-1]} | {COND[variant]} "
                    f"| {cell('false_green_rate')} | {_f((a.get('false_green_rate_answered') or {}).get('mean'))} "
                    f"| {cell('violation_recall')} "
                    f"| {cell('false_alarm_near_miss')} | {dist} | {a['answered_min']}/{n} |")
    rows.append("")
    rows.append("Schemas: *offered* (four verdicts, evidence-anchored definitions); *removed-only* "
                "(offered minus `needs_evidence`); *closed* (`pass`/`fail` only, evidence-anchored "
                "definitions kept); *dashboard* (`pass`/`fail` only, `pass` redefined as \"the "
                "obligation is satisfied\", warning dropped). "
                "The anchor subset has 120 unassessable pairs and no controls; Study 2 rates are pooled "
                "over its six firms (126 unassessable pairs). Min answered: the fewest pairs answered in any "
                "of the three runs. The verdict columns show every off-schema answer: none occurred on an "
                "unassessable pair in any cell.")
    return "\n".join(rows)


def table_contrasts() -> str:
    """Table 8: paired contrasts between schema conditions, Vertex block."""
    head = ("| Model | Study | Change of schema | Unassessable pairs | Change in FGR [95% CI] | Holm p |"
            "\n|---|---|---|---|---|---|")
    if not STUDIES.exists():
        return head
    cs = json.loads(STUDIES.read_text()).get("contrasts", {})
    lab = {"abstain_offered->abstain_removed_only": "offered → removed-only",
           "abstain_offered->abstain_closed": "offered → closed",
           "abstain_closed->abstain_withheld": "closed → dashboard",
           "abstain_offered->abstain_withheld": "offered → dashboard"}
    rows = [head]
    for k in sorted(cs, key=lambda k: (k.split("::")[0], k.split("::")[1], list(lab).index(k.split("::")[2]))):
        m, st, c = k.split("::")
        v = cs[k]
        mark = " **" if v["p_holm"] < 0.05 else ""
        rows.append(f"| {disp(m.replace('vertex/', ''))} | {st[-1]} | {lab[c]} | {v['n_pairs']} "
                    f"| {v['delta']:+.3f} [{v['ci95'][0]:+.2f}, {v['ci95'][1]:+.2f}] "
                    f"| {v['p_holm']:.3f}{mark} |")
    rows.append("")
    rows.append("Each unassessable pair's outcome is its share of `pass` over the three runs. Pairs answered "
                "in every run of both conditions; obligations resampled (2,000 draws, firm by obligation "
                "in Study 2); two-sided p-values Holm-corrected across all 24 contrasts; ** marks p < 0.05.")
    return "\n".join(rows)

STUDY3 = ROOT / "docs" / "study3" / "results.json"
S3_ORDER = ["gemini-3.1-pro-preview", "gemini-3.8-flash", "gemma-4-26b-a4b-it-maas",
            "gpt-oss-120b-maas", "deepseek-v3.2-maas", "qwen3-235b-a22b-instruct-2507-maas",
            "kimi-k2-thinking-maas"]


DEV = {"nemotron": "NVIDIA", "laguna": "Poolside", "qwen3.8": "Alibaba", "dots": "dots-studio",
       "gemini": "Google", "gemma": "Google", "gpt-oss": "OpenAI", "deepseek": "DeepSeek",
       "qwen3-235b": "Alibaba", "kimi": "Moonshot"}


def _dev(m: str) -> str:
    return next(v for k, v in sorted(DEV.items(), key=lambda kv: -len(kv[0])) if k in m)


NAMES = {"dots-3-note-preview": "dots.3 Note Preview", "nemotron-3-super-120b-a12b": "Nemotron 3 Super 120B",
         "nemotron-3-ultra-550b-a55b": "Nemotron 3 Ultra 550B", "nemotron-3.5-lightning": "Nemotron 3.5 Lightning",
         "laguna-xs-2.1": "Laguna XS 2.1", "qwen3.8-27b": "Qwen 3.8 27B", "gemini-3.1-pro-preview": "Gemini 3.1 Pro",
         "gemini-3.8-flash": "Gemini 3.8 Flash", "gemma-4-26b-a4b-it-maas": "Gemma 4 26B",
         "gpt-oss-120b-maas": "gpt-oss-120b", "deepseek-v3.2-maas": "DeepSeek V3.2",
         "qwen3-235b-a22b-instruct-2507-maas": "Qwen3 235B", "kimi-k2-thinking-maas": "Kimi K2 Thinking"}


def table_anchor_all() -> str:
    """Anchor subset, all thirteen models: offered vs dashboard, with coverage and test status."""
    head = ("| Model | Developer | Runs | Answered (offered) | FGR offered | FGR offered, answered only "
            "| Recall offered (of 20) | FGR dashboard | Change significant? |"
            "\n|---|---|---|---|---|---|---|---|---|")
    rows = [head]
    vw = json.loads(VIEWS.read_text())
    fin = {k for k, v in json.loads((ROOT / "docs" / "llm_results.json").read_text())["runs"].items()
           if v.get("per_firm")}
    ab = vw.get("ablation", {})
    for k in sorted(k for k in vw["runs"] if k in fin and k.endswith("abstain_offered")):
        o, w = vw["runs"][k], vw["runs"].get(k.replace("offered", "withheld"))
        m = o["model"]
        a = ab.get(m, {})
        sig = (f"yes (p = {a['p_holm']:.3f})" if a.get("holm_reject_0.05") else
               f"no (p = {a['p_holm']:.3f})") if a else "—"
        rows.append(f"| {NAMES.get(short(m), short(m))} | {_dev(m)} | 1 | {o['n_predictions']}/140 "
                    f"| {o['engine']['false_green_rate']:.3f} | {o['engine']['false_green_rate_answered']:.3f} "
                    f"| {o['engine']['violation_recall']:.3f} | {w['engine']['false_green_rate']:.3f} | {sig} |")
    st = json.loads(STUDIES.read_text())
    for mm in ("gemini-3.1-pro-preview", "gemini-3.8-flash", "gemma-4-26b-a4b-it-maas"):
        o = st["vertex"][f"vertex/{mm}::study1::abstain_offered"]["summary"]
        w = st["vertex"][f"vertex/{mm}::study1::abstain_withheld"]["summary"]
        c = st["contrasts"][f"vertex/{mm}::study1::abstain_offered->abstain_withheld"]
        rows.append(f"| {NAMES[mm]} | Google | 3 (mean) | {o['answered_min']}/140 (min) "
                    f"| {o['false_green_rate']['mean']:.3f} | {o['false_green_rate_answered']['mean']:.3f} "
                    f"| {o['violation_recall']['mean']:.3f} | {w['false_green_rate']['mean']:.3f} "
                    f"| {'yes' if c['p_holm'] < 0.05 else 'no'} (p = {c['p_holm']:.3f}) |")
    if STUDY3.exists():
        e = json.loads(STUDY3.read_text())["E1_anchor"]
        for mm in S3_ORDER[3:]:
            o, w = e[f"{mm}::abstain_offered"], e[f"{mm}::abstain_withheld"]
            rows.append(f"| {NAMES[mm]} | {_dev(mm)} | 1 | {o['answered']}/140 | {o['false_green_rate']:.3f} "
                        f"| {o['false_green_rate_answered']:.3f} | {o['violation_recall']:.3f} "
                        f"| {w['false_green_rate']:.3f} | not tested |")
    rows.append("")
    rows.append("FGR over the 120 unassessable pairs of the 140-pair anchor subset; unanswered pairs cannot be "
                "false greens, so the answered-only column guards against coverage effects. Change: offered to "
                "dashboard, paired on pairs answered in both; Holm across the six single-run models, and across "
                "24 contrasts for the three repeated-run models. The last four models were added with Study 3 and "
                "run once, descriptively. Recall is against the source engine's violation labels (Section 4.4).")
    return "\n".join(rows)


def table_cited() -> str:
    """Exploratory: the column cited as evidence on each false green, proxy-column firms."""
    ex = ROOT / "docs" / "study3" / "exploratory.json"
    head = ("| Rule family | Schema | False greens | Citing a planted proxy column | Per model | Citing the LCA offered wage |"
            "\n|---|---|---|---|---|---|")
    if not ex.exists():
        return head
    c = json.loads(ex.read_text())["cited_evidence_on_false_greens"]
    rows = [head]
    for fam, flab in (("i9", "I-9 (three rules)"), ("wage", "LCA required wage")):
        for cond in ("abstain_offered", "abstain_withheld"):
            x = c[f"{fam}::decoy::{cond}"]
            n = x["total"]
            lca = sum(v for k, v in x["by_field"].items() if k.startswith("WAGE_RATE"))
            prox = n - lca - x["by_field"].get("other", 0)
            shares = []
            for m, bf in x["by_model"].items():
                t = sum(bf.values())
                if t >= 5:
                    shares.append(sum(v for k, v in bf.items() if k != "other" and not k.startswith("WAGE_RATE")) / t)
            rng = f"{min(shares):.0%}–{max(shares):.0%}" if shares else "—"
            rows.append(f"| {flab} | {COND[cond]} | {n} | {prox} ({prox / n:.0%}) | {rng} | {lca} ({lca / n:.0%}) |")
    rows.append("")
    rows.append("Study 3 proxy-column firms, pooled over the seven models; per model: range of the share citing a "
                "planted column among models with at least five false greens. The column is the evidence field the "
                "reply line names, a self-report. The I-9 status column was never cited. Exploratory.")
    return "\n".join(rows)


def table_arm_contrasts() -> str:
    """Schema contrasts on plain and proxy firms; proxy-arm values are the declared P1/P2."""
    head = ("| Change of schema | Plain firms (exploratory) | Proxy firms (declared test) |"
            "\n|---|---|---|")
    ex = ROOT / "docs" / "study3" / "exploratory.json"
    if not ex.exists() or not STUDY3.exists():
        return head
    e = json.loads(ex.read_text())["schema_contrasts_by_arm"]
    pr = json.loads(STUDY3.read_text())["primary"]
    names = list(pr)
    rows = [head]
    for lab, key, pk in (("Abstention: offered → closed", "abstention (offered -> closed)", names[0]),
                         ("Definition and warning: closed → dashboard",
                          "definition and warning (closed -> dashboard)", names[1])):
        a = e[f"{key} | plain"]
        b = pr[pk]
        rows.append(f"| {lab} | {a['delta']:+.3f} [{a['ci95'][0]:+.2f}, {a['ci95'][1]:+.2f}], "
                    + ("p < 0.001" if a['p_two_sided_unadjusted'] <= 0.0005 else f"p = {a['p_two_sided_unadjusted']:.3f}") + " unadjusted "
                    f"| {b['delta']:+.3f} [{b['ci95'][0]:+.2f}, {b['ci95'][1]:+.2f}], Holm p = {b['p_holm']:.3f} |")
    rows.append("")
    rows.append("Pooled over the seven models with equal weight; same pairs, clusters and bootstrap draws as the "
                "declared analysis. The plain-firm column was computed after the results and is not part of any "
                "declared family.")
    return "\n".join(rows)


def table_robust() -> str:
    """Study 3 declared tests with every robustness check (body table)."""
    rb = ROOT / "docs" / "study3" / "robustness.json"
    head = ("| Test | Effect [95% CI] | Exact p (Holm) | Firm-weighted effect, exact p | Drop one model | Drop one firm |"
            "\n|---|---|---|---|---|---|")
    if not (rb.exists() and STUDY3.exists()):
        return head
    pr = json.loads(STUDY3.read_text())["primary"]
    r = json.loads(rb.read_text())
    lab = {"P1": "P1 Abstention (proxy firms)", "P2": "P2 Definition and warning (proxy firms)",
           "P3": "P3 Proxy columns, dashboard", "P4": "P4 Proxy columns, offered"}
    fmtp = lambda x: "<0.001" if x < 0.001 else f"{x:.3f}"  # noqa: E731
    rows = [head]
    for k, v in pr.items():
        sp = r["sign_flip_permutation"][k]
        fl = r["firm_clustered"][k]
        lm = r["leave_one_model_out"][k]
        lf = r["leave_one_firm_out"][k]
        rows.append(f"| {lab[k[:2]]} | {v['delta']:+.3f} [{v['ci95'][0]:+.2f}, {v['ci95'][1]:+.2f}] "
                    f"| {fmtp(sp['p_holm'])} | {fl['firm_mean_effect']:+.3f} (p {'< 0.001' if fl['p_exact_two_sided'] < 0.001 else '= ' + format(fl['p_exact_two_sided'], '.3f')}) "
                    f"| {lm['min']:+.3f} to {lm['max']:+.3f} | {lf['min']:+.3f} to {lf['max']:+.3f} |")
    rows.append("")
    rows.append("Effect: change in false-green rate, pooled over seven models with equal weight, paired on "
                "unassessable pairs answered in both cells; interval from the declared bootstrap over 18 firm-by-rule "
                "clusters. Exact p: sign-flip permutation over those 18 clusters (all 262,144 patterns), Holm across the "
                "four tests. Firm-weighted: each of the 12 firms weighted equally, exact sign-flip over firms (4,096 "
                "patterns). Drop one: range of the pooled effect with any one model, or any one firm, left out. All "
                "columns after the first were computed after the results.")
    return "\n".join(rows)


def table_study3() -> str:
    """Table 9: Study 3, false-green rate by model, arm and schema; coverage; detection."""
    head = ("| Model | Arm | FGR offered | removed-only | closed | dashboard | Recall, offered "
            "| False alarm, offered | Min answered |\n|---|---|---|---|---|---|---|---|---|")
    if not STUDY3.exists():
        return head
    c = json.loads(STUDY3.read_text())["cells"]
    rows = [head]
    for m in S3_ORDER:
        for arm in ("plain", "decoy"):
            g = lambda cond, k: c.get(f"{m}::{arm}::{cond}", {}).get(k)  # noqa: E731
            ans = [g(cond, "answered") for cond in COND if g(cond, "answered") is not None]
            rows.append(f"| {disp(m)} | {'proxy' if arm == 'decoy' else arm} | " + " | ".join(_f(g(cond, "false_green_rate")) for cond in COND)
                        + f" | {_f(g('abstain_offered', 'violation_recall'))} "
                          f"| {_f(g('abstain_offered', 'false_alarm_rate'))} | {min(ans) if ans else '—'}/504 |")
    rows.append("")
    rows.append("Twelve fresh firms (504 pairs, 180 unassessable) per arm, one run per cell. *plain*: generator "
                "v2; *proxy*: the same firms with the five proxy columns (generator v3). False alarm "
                "is any non-`pass` verdict on one of the 237 conforming controls.")
    return "\n".join(rows)


def table_study3_tests() -> str:
    """Table 10: Study 3 preregistered tests (pooled, by developer group, per model)."""
    head = ("| Estimate | P1 abstention | P2 definition and warning | P3 proxy columns, dashboard | P4 proxy columns, offered |"
            "\n|---|---|---|---|---|")
    if not STUDY3.exists():
        return head
    d = json.loads(STUDY3.read_text())
    names = [k for k in d["primary"]]

    def fmt(v):
        if not v or "delta" not in v:
            return "—"
        mark = " **" if v.get("p_holm", 1) < 0.05 else ""
        return f"{v['delta']:+.3f} [{v['ci95'][0]:+.2f}, {v['ci95'][1]:+.2f}] p={v['p_holm']:.3f}{mark}"
    rows = [head, "| **Pooled, 7 models (primary)** | " + " | ".join(fmt(d["primary"][n]) for n in names) + " |"]
    for grp, lab in (("google", "Google, 3 models"), ("other_developers", "Other developers, 4 models")):
        rows.append(f"| {lab} | " + " | ".join(fmt(d["S4_by_developer_group"].get(f"{n} | {grp}")) for n in names) + " |")
    for m in S3_ORDER:
        rows.append(f"| {disp(m)} | " + " | ".join(fmt(d["S1_per_model"].get(f"{n} | {m}")) for n in names) + " |")
    rows.append("")
    rows.append("Difference in false-green rate on unassessable pairs answered in both cells, [95% CI] from an "
                "obligation-cluster bootstrap (18 firm-by-rule clusters, 2,000 draws), Holm-adjusted p. "
                "Holm families as declared: the four pooled tests; the 28 per-model tests; the eight "
                "group tests. ** marks adjusted p < 0.05. Pooled estimates weight each model equally.")
    return "\n".join(rows)


def table_e1() -> str:
    """Table 11: extension E1, the four new models on the anchor subset (descriptive)."""
    head = ("| Model | FGR offered | removed-only | closed | dashboard | FG answered only, offered "
            "| Recall, offered (of 20) | Answered, offered |\n|---|---|---|---|---|---|---|---|")
    if not STUDY3.exists():
        return head
    e = json.loads(STUDY3.read_text())["E1_anchor"]
    rows = [head]
    for m in S3_ORDER[3:]:
        g = lambda cond, k: e.get(f"{m}::{cond}", {}).get(k)  # noqa: E731
        rows.append(f"| {disp(m)} | " + " | ".join(_f(g(cond, "false_green_rate")) for cond in COND)
                    + f" | {_f(g('abstain_offered', 'false_green_rate_answered'))} "
                      f"| {_f(g('abstain_offered', 'violation_recall'))} | {g('abstain_offered', 'answered')}/140 |")
    return "\n".join(rows)


def table_study4() -> str:
    """Study 4 declared tests (body table)."""
    f = ROOT / "docs" / "study4" / "results.json"
    head = ("| Test | Contrast | Effect [95% CI] | Firms + / − | Exact p (Holm) |"
            "\n|---|---|---|---|---|")
    if not f.exists():
        return head
    pr = json.loads(f.read_text())["primary"]
    lab = {"H1": ("H1 Names", "proxy columns − same values, neutral names"),
           "H2": ("H2 Meaning", "proxy columns − irrelevant columns"),
           "H3": ("H3 Direction", "adverse proxies − none; outcome `fail`"),
           "H4": ("H4 Abstaining verdicts", "removed − listed (factorial)"),
           "H5": ("H5 Definitions", "bare − evidence-anchored (factorial)"),
           "H6": ("H6 Warning", "absent − present (factorial)"),
           "H7": ("H7 Name the record first", "offered − offered with record named first")}
    fmtp = lambda x: "<0.001" if x < 0.001 else f"{x:.3f}"  # noqa: E731
    rows = [head]
    for k, v in pr.items():
        a, b = lab[k[:2]]
        rows.append(f"| {a} | {b} | {v['delta']:+.3f} [{v['ci95_firm_bootstrap'][0]:+.2f}, "
                    f"{v['ci95_firm_bootstrap'][1]:+.2f}] | {v['firms_positive']} / {v['firms_negative']} "
                    f"| {fmtp(v['p_holm'])} |")
    rows.append("")
    rows.append("Ten Study 3c firms (330 unassessable I-9 pairs), three Google models. Outcome: false green "
                "(`pass` on an unassessable pair) except H3 (`fail`). H1-H3 and H7 use the offered schema; H4-H6 average "
                "the four factorial menus on each side of the switch. All tests except H3 are on proxy-column firms. Paired, averaged within firm and model then over models; interval from a firm bootstrap; exact "
                "sign-flip over the ten firms (1,024 patterns), Holm across the seven tests. Declared before any call.")
    return "\n".join(rows)


def splice(text: str, name: str, body: str) -> tuple[str, bool]:
    b, e = BEGIN.format(name=name), END.format(name=name)
    block = f"{b}\n{body}\n{e}"
    if b in text and e in text:
        return re.sub(re.escape(b) + r".*?" + re.escape(e), lambda _: block, text, flags=re.S), True
    return text, False


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    runs = load_runs()
    complete = [k for k, v in runs.items() if v.get("aggregate")]
    print(f"runs in llm_results.json: {len(runs)} ({len(complete)} with aggregates)")
    for k in sorted(runs):
        r = runs[k]
        a = r.get("aggregate")
        state = (f"FGR {a['false_green_rate']['mean']:.3f} recall "
                 f"{a['violation_recall']['mean']:.3f}") if a else "no aggregate"
        print(f"  {k:<58}{state}")

    tables = {
        "table1-trivial": table_trivial(),
        "table7-vertex": table_vertex(),
        "table8-contrasts": table_contrasts(),
        "table9-study3": table_study3(),
        "table10-study3-tests": table_study3_tests(),
        "table11-e1": table_e1(),
        "table-anchor-all": table_anchor_all(),
        "table-cited": table_cited(),
        "table-arm-contrasts": table_arm_contrasts(),
        "table-robust": table_robust(),
        "table-study4": table_study4(),
        "table2-main": table_main(runs),
        "table2b-strict": table_views(),
        "table2c-audited": table_audited(),
        "table3-ablation": table_ablation(runs),
        "table4-regime": table_regime(runs),
    }

    if args.dry_run:
        for name, body in tables.items():
            print(f"\n--- {name} ---\n{body}")
        return 0

    text = PAPER.read_text()
    applied = []
    for name, body in tables.items():
        text, ok = splice(text, name, body)
        applied.append((name, ok))
    PAPER.write_text(text)

    for name, ok in applied:
        print(f"  {'spliced' if ok else 'NO MARKERS (skipped)'}: {name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
