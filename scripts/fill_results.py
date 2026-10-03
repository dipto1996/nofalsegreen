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
            f"| `{short(r['model'])}` | **{cell(a,'false_green_rate')}**{ci(ev.get('fgr_ci95'))} | {fga_s} "
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
        "| Model | Withheld pairs answered in both | FGR offered | FGR withheld | Change [95% CI] "
        "| Holm-adjusted p | Off-schema replies (withheld) |",
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
        rows.append(f"| `{short(m)}` | {n} of 120 | {views[f'{m}::abstain_offered']['engine']['false_green_rate']:.3f} "
                    f"| {views[f'{m}::abstain_withheld']['engine']['false_green_rate']:.3f} "
                    f"| {d:+.3f} [{c[0]:+.2f}, {c[1]:+.2f}] | {a['p_holm']:.3f} | {offs} of {ans} answered |")
    rows.append("")
    rows.append("FGR columns are over all 120 withheld pairs, as in Table 2. The change, its interval "
                "(obligation-cluster bootstrap, 2,000 draws) and the one-sided p-value are computed on "
                "the withheld pairs both runs answered; the bootstrap p-value has a floor of 1/2,000.")
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

    header = "| Regime | " + " | ".join(f"`{short(r['model'])}`" for r in offered) + " |"
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
    rows.append("Cells are the false-green rate over the regime's withheld pairs; in parentheses, "
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
        cond = "offered" if r["variant"].endswith("offered") else "withheld"
        rows.append(
            f"| `{short(r['model'])}` | {cond} | {e['false_green_rate']:.3f} | {st['false_green_rate']:.3f} "
            f"| {e['violation_recall']:.2f} | {st['violation_recall']:.2f} "
            f"| {v.get('fail', 0)} / {v.get('pass', 0)} / {other} |"
        )
    if len(rows) == 1:
        rows.append("| `[TO RUN]` | `[…]` | `[…]` | `[…]` | `[…]` | `[…]` | `[…]` |")
    return "\n".join(rows)


def table_audited() -> str:
    """Table 2c: engine view vs the blind-audit view (docs/LABEL_AUDIT_PROTOCOL.md)."""
    head = ("| Model | Condition | Withheld pairs scored | FGR, engine | FGR, audited "
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
        cond = "offered" if r["variant"].endswith("offered") else "withheld"
        rows.append(
            f"| `{short(r['model'])}` | {cond} | {au['n_withheld']} of {e['n_withheld']} "
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
        cond = "offered" if variant.endswith("offered") else "withheld"
        rows.append(f"| `{short(model)}` | {cond} | {ms('false_green_rate')} | {ms('violation_recall')} "
                    f"| {ms('false_alarm_rate')} | {ms('false_alarm_near_miss')} | {ms('abstention_f1')} "
                    f"| {r['pooled']['answered']}/{r['pooled']['n']} |")
    return "\n".join(rows)


COND = {"abstain_offered": "offered", "abstain_removed_only": "removed-only",
        "abstain_closed": "closed", "abstain_withheld": "dashboard"}


def table_vertex() -> str:
    """Table 7: Vertex block, four schema conditions, mean of three repeats [min, max],
    with where the withheld pairs went (mean count over repeats)."""
    head = ("| Model | Study | Schema | False green | FG, answered only | Recall | False alarm, near-miss "
            "| Withheld pairs answered pass / fail / needs_ev. / unmon. | Min answered |"
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
        rows.append(f"| `{model.replace('vertex/', '')}` | {study[-1]} | {COND[variant]} "
                    f"| {cell('false_green_rate')} | {_f((a.get('false_green_rate_answered') or {}).get('mean'))} "
                    f"| {cell('violation_recall')} "
                    f"| {cell('false_alarm_near_miss')} | {dist} | {a['answered_min']}/{n} |")
    rows.append("")
    rows.append("Schemas: *offered* (four verdicts, evidence-anchored definitions); *removed-only* "
                "(offered minus `needs_evidence`); *closed* (`pass`/`fail` only, evidence-anchored "
                "definitions kept); *dashboard* (`pass`/`fail` only, `pass` redefined as \"the "
                "obligation is satisfied\", warning dropped; the `abstain_withheld` condition of Study 1). "
                "Study 1 has 120 withheld pairs and no conforming controls; Study 2 rates are pooled "
                "over its six firms (126 withheld pairs). The verdict columns show every off-schema "
                "answer: none occurred on a withheld pair in any cell.")
    return "\n".join(rows)


def table_contrasts() -> str:
    """Table 8: paired contrasts between schema conditions, Vertex block."""
    head = ("| Model | Study | Change of schema | Withheld pairs | Change in FGR [95% CI] | Holm p |"
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
        rows.append(f"| `{m.replace('vertex/', '')}` | {st[-1]} | {lab[c]} | {v['n_pairs']} "
                    f"| {v['delta']:+.3f} [{v['ci95'][0]:+.2f}, {v['ci95'][1]:+.2f}] "
                    f"| {v['p_holm']:.3f}{mark} |")
    rows.append("")
    rows.append("Each withheld pair's outcome is its share of `pass` over the three runs. Pairs answered "
                "in every run of both conditions; obligations resampled (2,000 draws, firm by obligation "
                "in Study 2); two-sided p-values Holm-corrected across all 24 contrasts; ** marks p < 0.05.")
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
