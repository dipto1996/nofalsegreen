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
    for key in sorted(offered, key=lambda k: offered[k]["aggregate"]["false_green_rate"]["mean"],
                      reverse=True):
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
    """Table 3: schema ablation, offered vs withheld."""
    by_model: dict[str, dict] = {}
    for r in runs.values():
        if not r.get("aggregate"):
            continue
        by_model.setdefault(r["model"], {})[
            "offered" if r["variant"].endswith("offered") else "withheld"] = r

    rows = [
        "| Model | FGR, abstention offered | FGR, abstention withheld | Change [95% CI] | Off-schema abstentions |",
        "|---|---|---|---|---|",
    ]
    abl = json.loads(VIEWS.read_text()).get("ablation", {}) if VIEWS.exists() else {}
    paired = {m: v for m, v in by_model.items() if "offered" in v and "withheld" in v}
    if not paired:
        rows.append("| `[TO RUN]` | `[…]` | `[…]` | `[…]` | `[n of N]` |")
        if by_model:
            have = ", ".join(f"{short(m)} ({'/'.join(sorted(v))})" for m, v in by_model.items())
            rows.append(f"| *partial: {have}* | | | | |")
    for m, v in sorted(paired.items()):
        fo = v["offered"]["aggregate"]["false_green_rate"]["mean"]
        fw = v["withheld"]["aggregate"]["false_green_rate"]["mean"]
        offs = v["withheld"].get("n_off_schema", 0)
        n = v["withheld"].get("n_pairs", 0)
        c = abl.get(m, {}).get("ci95")
        cs = f" [{c[0]:+.2f}, {c[1]:+.2f}]" if c else ""
        rows.append(f"| `{short(m)}` | {fo:.3f} | {fw:.3f} | {fw - fo:+.3f}{cs} | {offs} of {n} |")
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
    rows.append("Cells are the false-green rate with the number of scored pairs in parentheses. "
                "A dash means the regime contributed no scored pair for that model.")
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


def table_vertex() -> str:
    """Table 7: Vertex block, mean of three repeats [min, max]."""
    head = ("| Model | Study | Condition | False green | Recall | False alarm, near-miss "
            "| Abst. F1 | Min answered |\n|---|---|---|---|---|---|---|---|")
    if not STUDIES.exists():
        return head
    rows = [head]
    for key, r in sorted(json.loads(STUDIES.read_text())["vertex"].items()):
        model, study, variant = key.split("::")
        a = r["summary"]
        cell = lambda k: ("—" if not a[k] else  # noqa: E731
                          f"{a[k]['mean']:.3f} [{a[k]['min']:.3f}, {a[k]['max']:.3f}]")
        n = 140 if study == "study1" else 252
        cond = "offered" if variant.endswith("offered") else "withheld"
        rows.append(f"| `{model}` | {study[-1]} | {cond} | {cell('false_green_rate')} "
                    f"| {cell('violation_recall')} | {cell('false_alarm_near_miss')} "
                    f"| {cell('abstention_f1')} | {a['answered_min']}/{n} |")
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
        "table6-study2": table_study2(),
        "table7-vertex": table_vertex(),
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
