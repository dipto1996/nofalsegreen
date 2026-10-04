"""Figures for the paper, drawn from the results files only (no API call).

    python3 scripts/make_figures.py      # -> paper/figures/*.pdf

Palette: the validated reference palette (light mode, print). Ordered schema
conditions use one sequential hue; plain/decoy use categorical slots 1-2; the
seven Study 3 models are small multiples, never seven hues.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
OUT = ROOT / "paper" / "figures"

INK, INK2, MUTED, GRID = "#0b0b0b", "#52514e", "#8a8984", "#e4e3df"
BLUE, ORANGE, AQUA, YELLOW = "#2a78d6", "#eb6834", "#1baf7a", "#eda100"
SEQ = ["#9ec5f4", "#5f9de8", "#2a78d6", "#14498a"]  # offered -> dashboard, light -> dark
COND = ["abstain_offered", "abstain_removed_only", "abstain_closed", "abstain_withheld"]
COND_LAB = ["offered", "removed-only", "closed", "dashboard"]
S3_MODELS = [
    ("gemini-3.1-pro-preview", "Gemini 3.1 Pro"), ("gemini-3.8-flash", "Gemini 3.8 Flash"),
    ("gemma-4-26b-a4b-it-maas", "Gemma 4 26B"), ("gpt-oss-120b-maas", "gpt-oss-120b"),
    ("deepseek-v3.2-maas", "DeepSeek V3.2"), ("qwen3-235b-a22b-instruct-2507-maas", "Qwen3 235B"),
    ("kimi-k2-thinking-maas", "Kimi K2 Thinking"),
]

plt.rcParams.update({
    "font.family": "serif", "font.serif": ["STIXGeneral", "Times New Roman", "DejaVu Serif"],
    "mathtext.fontset": "stix", "font.size": 8.5, "axes.titlesize": 8.5, "axes.labelsize": 8.5,
    "xtick.labelsize": 7.5, "ytick.labelsize": 7.5, "legend.fontsize": 7.5,
    "axes.edgecolor": MUTED, "axes.linewidth": 0.6, "axes.labelcolor": INK2,
    "xtick.color": INK2, "ytick.color": INK2, "xtick.major.width": 0.6, "ytick.major.width": 0.6,
    "axes.spines.top": False, "axes.spines.right": False, "axes.grid": True,
    "grid.color": GRID, "grid.linewidth": 0.5, "axes.axisbelow": True,
    "pdf.fonttype": 42, "legend.frameon": False, "savefig.bbox": "tight", "savefig.pad_inches": 0.02,
})


def load(p: str) -> dict:
    return json.loads((ROOT / p).read_text())


def save(fig, name: str) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUT / f"{name}.pdf")
    fig.savefig(OUT / f"{name}.png", dpi=200)
    plt.close(fig)
    print("wrote", name)


# ---------- body figures ----------

def fig_separation() -> None:
    """Study 1: violation recall vs false-green rate, offered (filled) vs dashboard (open)."""
    vw = load("docs/views_results.json")["runs"]
    fin = {k for k, v in load("docs/llm_results.json")["runs"].items() if v.get("per_firm")}
    pts: dict[str, dict] = {}
    for k, v in vw.items():
        if k not in fin:
            continue
        name = v["model"].split("/")[-1].replace(":free", "")
        pts.setdefault(name, {})["o" if v["variant"].endswith("offered") else "w"] = (
            v["engine"]["violation_recall"], v["engine"]["false_green_rate"])
    vx = load("docs/studies_results.json")["vertex"]
    for k, v in vx.items():
        m, st, c = k.split("::")
        if st == "study1" and c in ("abstain_offered", "abstain_withheld"):
            s = v["summary"]
            pts.setdefault(m.replace("vertex/", ""), {})["o" if c.endswith("offered") else "w"] = (
                s["violation_recall"]["mean"], s["false_green_rate"]["mean"])
    e1 = load("docs/study3/results.json")["E1_anchor"]
    for k, v in e1.items():
        m, c = k.split("::")
        if c in ("abstain_offered", "abstain_withheld"):
            pts.setdefault(m, {})["o" if c.endswith("offered") else "w"] = (v["violation_recall"], v["false_green_rate"])
    triv = load("docs/results.json")["systems"]

    fig, ax = plt.subplots(figsize=(3.4, 2.9))
    for name, d in pts.items():
        if "o" in d and "w" in d:
            ax.annotate("", xy=d["w"], xytext=d["o"],
                        arrowprops=dict(arrowstyle="-|>", color=MUTED, lw=0.6, shrinkA=3, shrinkB=3,
                                        mutation_scale=6))
        if "o" in d:
            ax.scatter(*d["o"], s=22, color=BLUE, edgecolor="white", linewidth=0.8, zorder=3)
        if "w" in d:
            ax.scatter(*d["w"], s=22, facecolor="white", edgecolor=BLUE, linewidth=1.0, zorder=3)
    placed: dict[tuple, list[str]] = {}
    for name, r in triv.items():
        xy = (round(r["violation_recall"]["mean"], 3), round(r["false_green_rate"]["mean"], 3))
        placed.setdefault(xy, []).append(name.replace("_", " "))
    for xy, names in placed.items():
        ax.scatter(*xy, s=26, marker="s", color=MUTED, zorder=3)
        right = xy[0] > 0.5
        ax.annotate(" = ".join(sorted(names)), xy, xytext=(-5 if right else 5, -10 if xy[1] > 0.5 else 7),
                    textcoords="offset points", fontsize=6.8, color=INK2, ha="right" if right else "left")
    ax.set_xlim(-0.03, 1.05)
    ax.set_ylim(-0.03, 1.05)
    ax.set_xlabel("Violation recall (higher is better)")
    ax.set_ylabel("False-green rate (lower is better)")
    ax.scatter([], [], s=22, color=BLUE, label="abstention offered")
    ax.scatter([], [], s=22, facecolor="white", edgecolor=BLUE, label="dashboard schema")
    ax.scatter([], [], s=26, marker="s", color=MUTED, label="trivial baseline")
    ax.legend(loc="upper center", ncol=1, bbox_to_anchor=(0.5, 0.98), handletextpad=0.3)
    save(fig, "fig_separation")


def fig_study3_multiples() -> None:
    """Study 3: FGR across the four schemas, plain vs decoy firms, one panel per model."""
    c = load("docs/study3/results.json")["cells"]
    fig, axes = plt.subplots(2, 4, figsize=(6.9, 3.3), sharex=True, sharey=True)
    xs = range(4)
    for ax, (m, lab) in zip(axes.flat, S3_MODELS):
        for arm, col, mk in (("plain", BLUE, "o"), ("decoy", ORANGE, "o")):
            ys = [c[f"{m}::{arm}::{k}"]["false_green_rate"] for k in COND]
            ax.plot(xs, ys, color=col, lw=1.6, marker=mk, ms=4,
                    markerfacecolor=col if arm == "decoy" else "white", markeredgecolor=col, mew=1.0)
        ax.set_title(lab, color=INK, pad=3)
        ax.set_ylim(-0.03, 1.0)
        ax.set_yticks([0, 0.25, 0.5, 0.75, 1.0])
    # pooled panel
    ax = axes.flat[7]
    for arm, col in (("plain", BLUE), ("decoy", ORANGE)):
        ys = [sum(c[f"{m}::{arm}::{k}"]["false_green_rate"] for m, _ in S3_MODELS) / len(S3_MODELS) for k in COND]
        ax.plot(xs, ys, color=col, lw=2.2, marker="o", ms=4.5,
                markerfacecolor=col if arm == "decoy" else "white", markeredgecolor=col, mew=1.0,
                label=("proxy-column firms" if arm == "decoy" else "plain firms"))
        ax.annotate(f"{ys[-1]:.2f}", (3, ys[-1]), xytext=(4, 0), textcoords="offset points",
                    fontsize=6.8, color=INK2, va="center")
    ax.set_title("Mean of the seven", color=INK, pad=3, fontweight="bold")
    fig.legend(*ax.get_legend_handles_labels(), loc="upper center", ncol=2,
               bbox_to_anchor=(0.5, 1.04), handlelength=1.8)
    for ax in axes[1]:
        ax.set_xticks(list(xs))
        ax.set_xticklabels(COND_LAB, rotation=35, ha="right")
    for ax in axes[:, 0]:
        ax.set_ylabel("False-green rate")
    fig.subplots_adjust(hspace=0.35, wspace=0.12)
    save(fig, "fig_study3_multiples")


def fig_forest() -> None:
    """Study 3 declared tests: effect and 95% CI, pooled, by developer group, per model."""
    d = load("docs/study3/results.json")
    names = list(d["primary"])
    titles = ["P1  abstention effect\n(offered → closed)", "P2  definition and warning\n(closed → dashboard)",
              "P3  proxy columns\n(dashboard schema)", "P4  proxy columns\n(offered schema)"]
    rows = [("Pooled, 7 models", lambda n: d["primary"][n], True),
            ("Google (3)", lambda n: d["S4_by_developer_group"][f"{n} | google"], False),
            ("Other developers (4)", lambda n: d["S4_by_developer_group"][f"{n} | other_developers"], False)]
    rows += [(lab, (lambda m: lambda n: d["S1_per_model"][f"{n} | {m}"])(m), False) for m, lab in S3_MODELS]
    fig, axes = plt.subplots(1, 4, figsize=(6.9, 3.0), sharey=True)
    ys = list(range(len(rows)))[::-1]
    for ax, n, t in zip(axes, names, titles):
        ax.axvline(0, color=INK2, lw=0.7)
        for y, (lab, get, pooled) in zip(ys, rows):
            v = get(n)
            if "delta" not in v:
                continue
            sig = v.get("p_holm", 1) < 0.05
            col = BLUE if sig else MUTED
            ax.plot(v["ci95"], [y, y], color=col, lw=2.2 if pooled else 1.2, solid_capstyle="round")
            ax.scatter(v["delta"], y, s=40 if pooled else 18, marker="D" if pooled else "o",
                       color=col if sig else "white", edgecolor=col, linewidth=1.0, zorder=3)
        ax.axhline(len(rows) - 3.5, color=GRID, lw=0.8)
        ax.set_title(t, color=INK, pad=4, fontsize=7.8)
        ax.set_xlim(-0.25, 0.8)
        ax.set_xticks([0, 0.25, 0.5, 0.75])
        ax.grid(axis="y", visible=False)
    axes[0].set_yticks(ys)
    axes[0].set_yticklabels([r[0] for r in rows])
    axes[0].get_yticklabels()[0].set_fontweight("bold")
    fig.text(0.56, -0.02, "Change in false-green rate, with 95% CI (filled: Holm-adjusted p < 0.05)",
             ha="center", color=INK2, fontsize=7.8)
    fig.subplots_adjust(wspace=0.08)
    save(fig, "fig_forest")


def fig_rule_family() -> None:
    """Exploratory: FGR by rule family, plain vs decoy, across schemas (mean of models)."""
    f = load("docs/study3/results.json")["exploratory_by_rule_family"]
    fig, axes = plt.subplots(1, 2, figsize=(5.0, 2.2), sharey=True)
    for ax, fam, title in ((axes[0], "i9", "I-9 rules (S1, S2, reverification)"),
                           (axes[1], "wage", "LCA required-wage rule")):
        for arm, col in (("plain", BLUE), ("decoy", ORANGE)):
            ys = [f[f"{fam}::{arm}::{k}"] for k in COND]
            ax.plot(range(4), ys, color=col, lw=1.8, marker="o", ms=4,
                    markerfacecolor=col if arm == "decoy" else "white", markeredgecolor=col,
                    label=("proxy-column firms" if arm == "decoy" else "plain firms"))
            for i in (0, 3):
                up = arm == "decoy" or fam == "i9"
                ax.annotate(f"{ys[i]:.2f}", (i, ys[i]), xytext=(0, 6 if up else -11),
                            textcoords="offset points", ha="center", fontsize=6.8, color=INK2)
        ax.set_title(title, color=INK, pad=3)
        ax.set_xticks(range(4))
        ax.set_xticklabels(COND_LAB, rotation=30, ha="right")
        ax.set_ylim(-0.08, 1.02)
    axes[0].set_ylabel("False-green rate (mean of 7 models)")
    axes[0].legend(loc="upper left")
    save(fig, "fig_rule_family")


# ---------- appendix figures ----------

def fig_verdict_routes() -> None:
    """Vertex block, Study 1: where the 120 withheld pairs go under each schema (mean of 3 runs)."""
    vx = load("docs/studies_results.json")["vertex"]
    models = [("gemini-3.1-pro-preview", "Gemini 3.1 Pro"), ("gemini-3.8-flash", "Gemini 3.8 Flash"),
              ("gemma-4-26b-a4b-it-maas", "Gemma 4 26B")]
    cats = [("needs_evidence", "needs_evidence", BLUE), ("pass", "pass (false green)", ORANGE),
            ("unmonitored", "unmonitored", AQUA), ("fail", "fail (unsupported violation)", YELLOW)]
    fig, axes = plt.subplots(1, 3, figsize=(6.9, 1.9), sharey=True)
    for ax, (m, lab) in zip(axes, models):
        for yi, k in enumerate(COND):
            reps = vx[f"vertex/{m}::study1::{k}"]["repeats"]
            left = 0.0
            for key, _, col in cats:
                w = sum(r["counts"].get(f"withheld_as_{key}", 0) for r in reps) / len(reps)
                ax.barh(3 - yi, w, left=left, color=col, height=0.62, edgecolor="white", linewidth=1.0)
                left += w
        ax.set_title(lab, color=INK, pad=3)
        ax.set_xlim(0, 120)
        ax.set_xticks([0, 30, 60, 90, 120])
        ax.grid(axis="y", visible=False)
    axes[0].set_yticks(range(4))
    axes[0].set_yticklabels(COND_LAB[::-1])
    axes[1].set_xlabel("Withheld pairs (of 120), by verdict given")
    handles = [plt.Rectangle((0, 0), 1, 1, color=c) for _, _, c in cats]
    fig.legend(handles, [l for _, l, _ in cats], loc="lower center", ncol=4, bbox_to_anchor=(0.5, -0.27))
    save(fig, "fig_verdict_routes")


def fig_regime_heatmap() -> None:
    """Study 1, abstention offered: FGR by regime and model (from the generated Table 4)."""
    paper = (ROOT / "docs" / "PAPER.md").read_text()
    block = paper[paper.index("BEGIN GENERATED: table4-regime"):paper.index("END GENERATED: table4-regime")]
    lines = [l for l in block.splitlines() if l.startswith("|")]
    head = [h.strip(" `") for h in lines[0].strip("|").split("|")]
    rows = [[c.strip(" `") for c in l.strip("|").split("|")] for l in lines[2:]]
    regimes = [r[0] for r in rows]
    models = head[1:]
    vals = [[float(re.match(r"[\d.]+", c).group()) if re.match(r"[\d.]+", c) else float("nan")
             for c in r[1:]] for r in rows]
    from matplotlib.colors import LinearSegmentedColormap
    cmap = LinearSegmentedColormap.from_list("seq", ["#f4f8fd", "#9ec5f4", "#2a78d6", "#0d3266"])
    fig, ax = plt.subplots(figsize=(6.4, 0.32 * len(regimes) + 0.9))
    im = ax.imshow(vals, cmap=cmap, vmin=0, vmax=0.5, aspect="auto")
    for i, r in enumerate(vals):
        for j, v in enumerate(r):
            if v == v:
                ax.text(j, i, f"{v:.2f}", ha="center", va="center", fontsize=6.8,
                        color="white" if v > 0.3 else INK)
    ax.set_xticks(range(len(models)))
    ax.set_xticklabels([m.replace("-preview", "").replace("-maas", "") for m in models], rotation=30, ha="right")
    ax.set_yticks(range(len(regimes)))
    ax.set_yticklabels(regimes)
    ax.grid(False)
    for s in ax.spines.values():
        s.set_visible(False)
    cb = fig.colorbar(im, ax=ax, fraction=0.025, pad=0.01)
    cb.outline.set_visible(False)
    cb.set_label("False-green rate", color=INK2)
    save(fig, "fig_regime_heatmap")


def fig_label_audit() -> None:
    """Second audit of the anchor firm's 20 violation labels, by declared group."""
    sys.path.insert(0, str(ROOT))
    from nofalsegreen.labelviews import MEMO_ABSENCE, PROSPECTIVE
    a = load("docs/label_audit_second.json")["pairs"]
    viol = {k: v["decision"] for k, v in a.items() if v["audit"] == "violation"}
    groups = [("Memo absences (5)", [k for k in viol if k in MEMO_ABSENCE]),
              ("Future deadlines (5)", [k for k in viol if k in PROSPECTIVE]),
              ("Strict-view breaches (10)", [k for k in viol if k not in MEMO_ABSENCE | PROSPECTIVE])]
    cats = [("violation_shown", "violation shown", BLUE), ("cannot_tell", "cannot tell from exports", ORANGE),
            ("compliance_shown", "compliance shown", AQUA)]
    fig, ax = plt.subplots(figsize=(4.6, 1.5))
    for yi, (lab, ks) in enumerate(groups):
        left = 0
        for key, _, col in cats:
            n = sum(viol[k] == key for k in ks)
            if n:
                ax.barh(2 - yi, n, left=left, color=col, height=0.6, edgecolor="white", linewidth=1.0)
                ax.text(left + n / 2, 2 - yi, str(n), ha="center", va="center", fontsize=7,
                        color="white" if col == BLUE else INK)
            left += n
    ax.set_yticks(range(3))
    ax.set_yticklabels([g[0] for g in groups][::-1])
    ax.set_xlim(0, 10)
    ax.set_xlabel("Violation labels")
    ax.grid(axis="y", visible=False)
    handles = [plt.Rectangle((0, 0), 1, 1, color=c) for _, _, c in cats]
    fig.legend(handles, [l for _, l, _ in cats], loc="lower center", ncol=3, bbox_to_anchor=(0.55, -0.36))
    save(fig, "fig_label_audit")


def fig_detection_vs_safety() -> None:
    """Study 3: detection on plain firms vs false greens on decoy firms (abstention offered)."""
    c = load("docs/study3/results.json")["cells"]
    fig, ax = plt.subplots(figsize=(3.4, 2.5))
    for m, lab in S3_MODELS:
        x = c[f"{m}::plain::abstain_offered"]["violation_recall"]
        y = c[f"{m}::decoy::abstain_offered"]["false_green_rate"]
        ax.scatter(x, y, s=24, color=BLUE, edgecolor="white", linewidth=0.8, zorder=3)
        slot = {"Gemini 3.8 Flash": 0.43, "gpt-oss-120b": 0.33, "Gemini 3.1 Pro": 0.23, "Kimi K2 Thinking": 0.10}
        if lab in slot:
            ax.annotate(lab, (x, y), xytext=(0.86, slot[lab]), textcoords="data", ha="right", va="center",
                        fontsize=6.8, color=INK2,
                        arrowprops=dict(arrowstyle="-", color=MUTED, lw=0.5, shrinkA=1, shrinkB=3))
        else:
            off = {"DeepSeek V3.2": (-5, 6)}.get(lab, (5, 3))
            ax.annotate(lab, (x, y), xytext=off, textcoords="offset points",
                        ha="right" if off[0] < 0 else "left", fontsize=6.8, color=INK2)
    ax.set_xlim(0, 1.05)
    ax.set_ylim(0, 1.0)
    ax.set_xlabel("Violation recall, plain firms")
    ax.set_ylabel("False-green rate, proxy-column firms")
    save(fig, "fig_detection_vs_safety")


if __name__ == "__main__":
    for f in (fig_separation, fig_study3_multiples, fig_forest, fig_rule_family,
              fig_verdict_routes, fig_regime_heatmap, fig_label_audit, fig_detection_vs_safety):
        f()
