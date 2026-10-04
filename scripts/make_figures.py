"""Figures for the paper, drawn from the results files only (no API call).

    python3 scripts/make_figures.py      # -> paper/figures/*.pdf and *.png

House style: framed axes, serif type matching the paper, navy for the plain or
offered condition, brick for the proxy-column or dashboard condition, shading
where the shaded quantity is the point of the figure. The palette was checked
with the data-viz validator (lightness band, chroma, colour-blind separation);
gold sits below 3:1 contrast, so every gold segment carries a printed value.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.colors import LinearSegmentedColormap  # noqa: E402
import matplotlib.patheffects as pe  # noqa: E402

HALO = [pe.withStroke(linewidth=2.4, foreground="white")]

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
OUT = ROOT / "paper" / "figures"

INK, INK2, MUTED, GRID, FRAME = "#1b1b1b", "#4a4a48", "#9a9994", "#ebeae6", "#3a3a3a"
NAVY, BRICK, TEAL, GOLD = "#1d5c9e", "#c8553d", "#2a9d8f", "#e0a526"
SHADE_BAD, SHADE_GOOD = "#f6e3de", "#e3eef6"
COND = ["abstain_offered", "abstain_removed_only", "abstain_closed", "abstain_withheld"]
COND_LAB = ["offered", "removed\nonly", "closed", "dashboard"]
S3_MODELS = [
    ("gemini-3.1-pro-preview", "Gemini 3.1 Pro"), ("gemini-3.8-flash", "Gemini 3.8 Flash"),
    ("gemma-4-26b-a4b-it-maas", "Gemma 4 26B"), ("gpt-oss-120b-maas", "gpt-oss-120b"),
    ("deepseek-v3.2-maas", "DeepSeek V3.2"), ("qwen3-235b-a22b-instruct-2507-maas", "Qwen3 235B"),
    ("kimi-k2-thinking-maas", "Kimi K2 Thinking"),
]
NAMES = {
    "dots-3-note-preview": "dots.3 Note Preview", "laguna-xs-2.1": "Laguna XS 2.1",
    "nemotron-3-super-120b-a12b": "Nemotron 3 Super 120B", "nemotron-3-ultra-550b-a55b": "Nemotron 3 Ultra 550B",
    "nemotron-3.5-lightning": "Nemotron 3.5 Lightning", "qwen3.8-27b": "Qwen 3.8 27B",
    **{k: v for k, v in S3_MODELS},
}

plt.rcParams.update({
    "font.family": "serif", "font.serif": ["STIXGeneral", "Times New Roman", "DejaVu Serif"],
    "mathtext.fontset": "stix", "font.size": 9, "axes.titlesize": 9.5, "axes.labelsize": 9,
    "xtick.labelsize": 8, "ytick.labelsize": 8, "legend.fontsize": 8.5,
    "axes.edgecolor": FRAME, "axes.linewidth": 0.8, "axes.labelcolor": INK,
    "xtick.color": INK2, "ytick.color": INK2, "xtick.direction": "out", "ytick.direction": "out",
    "xtick.major.size": 3, "ytick.major.size": 3, "xtick.major.width": 0.7, "ytick.major.width": 0.7,
    "axes.grid": True, "grid.color": GRID, "grid.linewidth": 0.6, "axes.axisbelow": True,
    "axes.titleweight": "bold", "axes.titlecolor": INK,
    "pdf.fonttype": 42, "legend.frameon": False, "savefig.bbox": "tight", "savefig.pad_inches": 0.03,
    "lines.solid_capstyle": "round",
})


def load(p: str) -> dict:
    return json.loads((ROOT / p).read_text())


def save(fig, name: str) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUT / f"{name}.pdf")
    fig.savefig(OUT / f"{name}.png", dpi=220)
    plt.close(fig)
    print("wrote", name)


def pair_plot(ax, ys_plain, ys_proxy, lw=1.8, ms=5.2, shade=True):
    xs = range(len(ys_plain))
    if shade:
        ax.fill_between(xs, ys_plain, ys_proxy, color=BRICK, alpha=0.10, lw=0)
    ax.plot(xs, ys_plain, color=NAVY, lw=lw, marker="o", ms=ms, mfc="white", mec=NAVY, mew=1.3, zorder=3)
    ax.plot(xs, ys_proxy, color=BRICK, lw=lw, marker="o", ms=ms, mfc=BRICK, mec="white", mew=0.8, zorder=4)


# ---------- the separation plot (restored, all thirteen models) ----------

def anchor_points() -> list[tuple[str, tuple, tuple]]:
    vw = load("docs/views_results.json")["runs"]
    fin = {k for k, v in load("docs/llm_results.json")["runs"].items() if v.get("per_firm")}
    pts: dict[str, dict] = {}
    for k, v in vw.items():
        if k in fin:
            name = v["model"].split("/")[-1].replace(":free", "")
            pts.setdefault(name, {})["o" if v["variant"].endswith("offered") else "w"] = (
                v["engine"]["violation_recall"], v["engine"]["false_green_rate"])
    for k, v in load("docs/studies_results.json")["vertex"].items():
        m, st, c = k.split("::")
        if st == "study1" and c in ("abstain_offered", "abstain_withheld"):
            s = v["summary"]
            pts.setdefault(m.replace("vertex/", ""), {})["o" if c.endswith("offered") else "w"] = (
                s["violation_recall"]["mean"], s["false_green_rate"]["mean"])
    for k, v in load("docs/study3/results.json")["E1_anchor"].items():
        m, c = k.split("::")
        if c in ("abstain_offered", "abstain_withheld"):
            pts.setdefault(m, {})["o" if c.endswith("offered") else "w"] = (v["violation_recall"], v["false_green_rate"])
    order = sorted(pts, key=lambda m: NAMES.get(m, m).lower())
    return [(NAMES.get(m, m), pts[m]["o"], pts[m]["w"]) for m in order if "o" in pts[m] and "w" in pts[m]]


def fig_separation() -> None:
    """Anchor subset: each model's move from abstention offered (filled) to withheld (open)."""
    pts = anchor_points()
    triv = load("docs/results.json")["systems"]
    fig = plt.figure(figsize=(6.6, 3.9))
    ax = fig.add_axes([0.08, 0.12, 0.56, 0.82])
    ax.add_patch(plt.Rectangle((0.5, 0.3), 0.55, 0.75, color=SHADE_BAD, lw=0, zorder=0))
    ax.text(1.02, 1.0, "detects violations,\nbut unsafe", ha="right", va="top", fontsize=8,
            color=BRICK, style="italic")
    ax.add_patch(plt.Rectangle((0.5, -0.09), 0.55, 0.19, color=SHADE_GOOD, lw=0, zorder=0))
    ax.text(0.52, 0.085, "the target", ha="left", va="top", fontsize=8, color=NAVY, style="italic")
    taken: list[tuple] = []
    for i, (name, o, w) in enumerate(pts, 1):
        ax.plot([o[0], w[0]], [o[1], w[1]], color=NAVY, alpha=0.45, lw=0.9, zorder=2)
        ax.scatter(*o, s=34, color=NAVY, edgecolor="white", linewidth=0.8, zorder=4)
        ax.scatter(*w, s=34, facecolor="white", edgecolor=NAVY, linewidth=1.3, zorder=4)
        crowded = any(abs(w[0] - x) < 0.06 and abs(w[1] - y) < 0.035 for x, y in taken)
        ax.annotate(str(i), w, xytext=(5, -10) if crowded else (5, 3), textcoords="offset points",
                    fontsize=7.4, color=INK, fontweight="bold", zorder=6, path_effects=HALO)
        taken.append(w)
    placed: dict[tuple, list[str]] = {}
    for name, r in triv.items():
        xy = (round(r["violation_recall"]["mean"], 3), round(r["false_green_rate"]["mean"], 3))
        placed.setdefault(xy, []).append(name)
    for xy, names in placed.items():
        ax.scatter(*xy, s=40, marker="s", color=MUTED, zorder=5, clip_on=False)
        right = xy[0] > 0.5
        top = xy[1] > 0.5
        ax.annotate(" = ".join(sorted(names)), xy, xytext=(-8 if right else 8, -11 if top else -1),
                    textcoords="offset points", fontsize=7.2, color=INK2, family="monospace",
                    ha="right" if right else "left", va="top" if not top else "baseline")
    ax.set_xlim(-0.03, 1.05)
    ax.set_ylim(-0.09, 1.05)
    ax.set_xlabel("Violation recall (higher is better)")
    ax.set_ylabel("False-green rate (lower is better)")
    kx = fig.add_axes([0.66, 0.12, 0.33, 0.82])
    kx.axis("off")
    kx.set_xlim(0, 1)
    kx.set_ylim(0, 1)
    y = 0.98
    for i, (name, _, _) in enumerate(pts, 1):
        kx.text(0.02, y, f"{i:>2}", fontsize=7.6, color=INK, ha="right", va="top")
        kx.text(0.06, y, name, fontsize=7.6, color=INK2, va="top")
        y -= 0.052
    y -= 0.03
    kx.scatter(0.04, y - 0.012, s=34, color=NAVY, edgecolor="white", clip_on=False)
    kx.text(0.09, y, "abstention offered", fontsize=7.8, va="top")
    y -= 0.055
    kx.scatter(0.04, y - 0.012, s=34, facecolor="white", edgecolor=NAVY, linewidth=1.3, clip_on=False)
    kx.text(0.09, y, "abstention withheld (dashboard)", fontsize=7.8, va="top")
    y -= 0.055
    kx.scatter(0.04, y - 0.012, s=38, marker="s", color=MUTED, clip_on=False)
    kx.text(0.09, y, "trivial baseline", fontsize=7.8, va="top")
    save(fig, "fig_separation")


# ---------- Study 3 ----------

def fig_study3_multiples() -> None:
    c = load("docs/study3/results.json")["cells"]
    fig, axes = plt.subplots(2, 4, figsize=(6.9, 3.9), sharex=True, sharey=True)
    for ax, (m, lab) in zip(axes.flat, S3_MODELS):
        pair_plot(ax, [c[f"{m}::plain::{k}"]["false_green_rate"] for k in COND],
                  [c[f"{m}::decoy::{k}"]["false_green_rate"] for k in COND], lw=1.5, ms=4.4)
        ax.set_title(lab, fontsize=8.8, pad=4)
    ax = axes.flat[7]
    ax.set_facecolor("#f7f7f5")
    mp = [sum(c[f"{m}::plain::{k}"]["false_green_rate"] for m, _ in S3_MODELS) / 7 for k in COND]
    md = [sum(c[f"{m}::decoy::{k}"]["false_green_rate"] for m, _ in S3_MODELS) / 7 for k in COND]
    pair_plot(ax, mp, md, lw=2.2, ms=5.2)
    for ys, col, dy in ((mp, NAVY, -10), (md, BRICK, 6)):
        for i in (0, 3):
            ax.annotate(f"{ys[i]:.2f}", (i, ys[i]), xytext=(0, dy), textcoords="offset points",
                        ha="center", fontsize=7.2, color=col, fontweight="bold")
    ax.set_title("Mean of the seven", fontsize=8.8, pad=4)
    for ax in axes.flat:
        ax.set_ylim(-0.04, 1.02)
        ax.set_yticks([0, 0.25, 0.5, 0.75, 1.0])
        ax.set_yticklabels(["0", ".25", ".50", ".75", "1"])
        ax.set_xticks(range(4))
        ax.set_xticklabels(["off.", "rem.", "closed", "dash."], fontsize=7.4)
        ax.set_xlim(-0.35, 3.35)
    for ax in axes[:, 0]:
        ax.set_ylabel("False-green rate")
    fig.text(0.5, -0.025, "Schema: off. = offered, rem. = removed-only, closed, dash. = dashboard",
             ha="center", fontsize=7.8, color=INK2)
    h1 = plt.Line2D([], [], color=NAVY, marker="o", mfc="white", mec=NAVY, mew=1.3, lw=1.6, label="plain firms")
    h2 = plt.Line2D([], [], color=BRICK, marker="o", mfc=BRICK, mec="white", lw=1.6,
                    label="the same firms with proxy columns")
    h3 = plt.Rectangle((0, 0), 1, 1, color=BRICK, alpha=0.12, label="effect of proxy columns")
    fig.legend(handles=[h1, h2, h3], loc="upper center", ncol=3, bbox_to_anchor=(0.5, 1.035))
    fig.subplots_adjust(hspace=0.42, wspace=0.1)
    save(fig, "fig_study3_multiples")


def fig_forest() -> None:
    d = load("docs/study3/results.json")
    names = list(d["primary"])
    titles = ["P1  Abstention\noffered → closed", "P2  Definition and warning\nclosed → dashboard",
              "P3  Proxy columns\ndashboard schema", "P4  Proxy columns\noffered schema"]
    rows = [("Pooled, 7 models", lambda n: d["primary"][n], "pool"),
            ("Google (3)", lambda n: d["S4_by_developer_group"][f"{n} | google"], "grp"),
            ("Other developers (4)", lambda n: d["S4_by_developer_group"][f"{n} | other_developers"], "grp")]
    rows += [(lab, (lambda m: lambda n: d["S1_per_model"][f"{n} | {m}"])(m), "model") for m, lab in S3_MODELS]
    fig, axes = plt.subplots(1, 4, figsize=(6.9, 3.6), sharey=True)
    ys = list(range(len(rows)))[::-1]
    for ax, n, t in zip(axes, names, titles):
        for y in ys[::2]:
            ax.axhspan(y - 0.5, y + 0.5, color="#f6f6f3", zorder=0, lw=0)
        ax.axvline(0, color=FRAME, lw=0.8, zorder=1)
        for y, (lab, get, kind) in zip(ys, rows):
            v = get(n)
            if "delta" not in v:
                continue
            sig = v.get("p_holm", 1) < 0.05
            col = (BRICK if kind == "pool" else NAVY) if sig else MUTED
            ax.plot(v["ci95"], [y, y], color=col, lw=2.6 if kind == "pool" else 1.4, zorder=2)
            ax.scatter(v["delta"], y, s=58 if kind == "pool" else 24, marker="D" if kind == "pool" else "o",
                       color=col if sig else "white", edgecolor=col, linewidth=1.2, zorder=3)
        ax.axhline(len(rows) - 3.5, color=FRAME, lw=0.6)
        ax.set_title(t, fontsize=8.4, pad=5)
        ax.set_xlim(-0.2, 0.8)
        ax.set_xticks([0, 0.25, 0.5, 0.75])
        ax.set_xticklabels(["0", "+.25", "+.50", "+.75"])
        ax.grid(axis="y", visible=False)
        ax.set_ylim(-0.6, len(rows) - 0.4)
    axes[0].set_yticks(ys)
    axes[0].set_yticklabels([r[0] for r in rows])
    axes[0].get_yticklabels()[0].set_fontweight("bold")
    fig.text(0.58, -0.01, "Change in false-green rate with 95% interval.  Filled: significant after Holm correction;"
             " hollow grey: not significant.", ha="center", color=INK2, fontsize=8)
    fig.subplots_adjust(wspace=0.08)
    save(fig, "fig_forest")


def fig_rule_family() -> None:
    f = load("docs/study3/results.json")["exploratory_by_rule_family"]
    fig, axes = plt.subplots(1, 2, figsize=(6.0, 2.6), sharey=True)
    for ax, fam, title in ((axes[0], "i9", "I-9 rules (3 firms withhold the I-9 export)"),
                           (axes[1], "wage", "LCA required-wage rule (9 firms)")):
        yp = [f[f"{fam}::plain::{k}"] for k in COND]
        yd = [f[f"{fam}::decoy::{k}"] for k in COND]
        pair_plot(ax, yp, yd, lw=2.0, ms=5.4)
        for i in (0, 3):
            ax.annotate(f"{yd[i]:.2f}", (i, yd[i]), xytext=(0, 7), textcoords="offset points", ha="center",
                        fontsize=7.6, color=BRICK, fontweight="bold")
            ax.annotate(f"{yp[i]:.2f}", (i, yp[i]), xytext=(0, 7 if fam == "i9" else -12),
                        textcoords="offset points", ha="center", fontsize=7.6, color=NAVY, fontweight="bold")
        ax.set_title(title, fontsize=8.8, pad=5)
        ax.set_xticks(range(4))
        ax.set_xticklabels(COND_LAB, fontsize=7.6)
        ax.set_xlim(-0.35, 3.35)
        ax.set_ylim(-0.06, 1.02)
    axes[0].set_ylabel("False-green rate (mean of 7 models)")
    h1 = plt.Line2D([], [], color=NAVY, marker="o", mfc="white", mec=NAVY, mew=1.3, lw=1.8, label="plain firms")
    h2 = plt.Line2D([], [], color=BRICK, marker="o", mfc=BRICK, mec="white", lw=1.8, label="with proxy columns")
    fig.legend(handles=[h1, h2], loc="upper center", ncol=2, bbox_to_anchor=(0.5, 1.07))
    fig.subplots_adjust(wspace=0.08)
    save(fig, "fig_rule_family")


def fig_detection_vs_safety() -> None:
    c = load("docs/study3/results.json")["cells"]
    fig, ax = plt.subplots(figsize=(4.4, 3.1))
    ax.add_patch(plt.Rectangle((0.9, 0.1), 0.15, 0.95, color=SHADE_BAD, lw=0, zorder=0))
    ax.text(0.885, 0.97, "detects nearly every\nviolation, still unsafe", ha="right", va="top", fontsize=7.6,
            color=BRICK, style="italic")
    slot = {"Gemini 3.8 Flash": 0.47, "gpt-oss-120b": 0.37, "Gemini 3.1 Pro": 0.27, "Kimi K2 Thinking": 0.14}
    for m, lab in S3_MODELS:
        x0 = c[f"{m}::plain::abstain_offered"]["violation_recall"]
        y0 = c[f"{m}::plain::abstain_offered"]["false_green_rate"]
        y1 = c[f"{m}::decoy::abstain_offered"]["false_green_rate"]
        ax.plot([x0, x0], [y0, y1], color=BRICK, lw=1.0, alpha=0.6, zorder=2)
        ax.scatter(x0, y0, s=26, facecolor="white", edgecolor=NAVY, linewidth=1.2, zorder=3)
        ax.scatter(x0, y1, s=34, color=BRICK, edgecolor="white", linewidth=0.8, zorder=4)
        if lab in slot:
            ax.annotate(lab, (x0, y1), xytext=(0.84, slot[lab]), textcoords="data", ha="right", va="center",
                        fontsize=7.6, color=INK2, arrowprops=dict(arrowstyle="-", color=MUTED, lw=0.5,
                                                                  shrinkA=1, shrinkB=3))
        else:
            ax.annotate(lab, (x0, y1), xytext=(6, 2), textcoords="offset points", fontsize=7.6, color=INK2)
    ax.set_xlim(0, 1.05)
    ax.set_ylim(0, 1.0)
    ax.set_xlabel("Violation recall on plain firms (offered schema)")
    ax.set_ylabel("False-green rate (offered schema)")
    h1 = plt.Line2D([], [], ls="", marker="o", mfc="white", mec=NAVY, mew=1.2, label="plain firms")
    h2 = plt.Line2D([], [], ls="", marker="o", mfc=BRICK, mec="white", label="with proxy columns")
    ax.legend(handles=[h1, h2], loc="lower left")
    save(fig, "fig_detection_vs_safety")


# ---------- Section 7 and appendix ----------

def fig_verdict_routes() -> None:
    vx = load("docs/studies_results.json")["vertex"]
    models = [("gemini-3.1-pro-preview", "Gemini 3.1 Pro"), ("gemini-3.8-flash", "Gemini 3.8 Flash"),
              ("gemma-4-26b-a4b-it-maas", "Gemma 4 26B")]
    cats = [("needs_evidence", "needs_evidence (correct)", NAVY), ("pass", "pass (false green)", BRICK),
            ("unmonitored", "unmonitored", TEAL), ("fail", "fail (unsupported violation)", GOLD)]
    fig, axes = plt.subplots(1, 3, figsize=(6.9, 2.3), sharey=True)
    lab4 = ["offered", "removed-only", "closed", "dashboard"]
    for ax, (m, lab) in zip(axes, models):
        for yi, k in enumerate(COND):
            reps = vx[f"vertex/{m}::study1::{k}"]["repeats"]
            left = 0.0
            for key, _, col in cats:
                w = sum(r["counts"].get(f"withheld_as_{key}", 0) for r in reps) / len(reps)
                if w:
                    ax.barh(3 - yi, w, left=left, color=col, height=0.66, edgecolor="white", linewidth=1.2)
                    if w >= 12:
                        ax.text(left + w / 2, 3 - yi, f"{w:.0f}", ha="center", va="center", fontsize=7,
                                color="white" if col in (NAVY, BRICK, TEAL) else INK)
                left += w
        ax.set_title(lab, fontsize=8.8, pad=4)
        ax.set_xlim(0, 120)
        ax.set_xticks([0, 40, 80, 120])
        ax.grid(axis="y", visible=False)
    axes[0].set_yticks(range(4))
    axes[0].set_yticklabels(lab4[::-1])
    axes[1].set_xlabel("The 120 unassessable pairs, by the verdict given (mean of three runs)")
    handles = [plt.Rectangle((0, 0), 1, 1, color=c) for _, _, c in cats]
    fig.legend(handles, [l for _, l, _ in cats], loc="lower center", ncol=4, bbox_to_anchor=(0.5, -0.2))
    fig.subplots_adjust(wspace=0.14)
    save(fig, "fig_verdict_routes")


def fig_regime_heatmap() -> None:
    paper = (ROOT / "docs" / "PAPER.md").read_text()
    block = paper[paper.index("BEGIN GENERATED: table4-regime"):paper.index("END GENERATED: table4-regime")]
    lines = [l for l in block.splitlines() if l.startswith("|")]
    head = [h.strip(" `") for h in lines[0].strip("|").split("|")]
    rows = [[c.strip(" `") for c in l.strip("|").split("|")] for l in lines[2:]]
    regimes = [r[0] for r in rows]
    vals = [[float(re.match(r"[\d.]+", c).group()) if re.match(r"[\d.]+", c) else float("nan")
             for c in r[1:]] for r in rows]
    cmap = LinearSegmentedColormap.from_list("seq", ["#fbfbfa", "#c9dbee", "#5f8fc4", NAVY, "#0e2f52"])
    fig, ax = plt.subplots(figsize=(6.4, 0.34 * len(regimes) + 1.0))
    im = ax.imshow(vals, cmap=cmap, vmin=0, vmax=0.45, aspect="auto")
    for i, r in enumerate(vals):
        for j, v in enumerate(r):
            if v == v:
                ax.text(j, i, "·" if v == 0 else f"{v:.2f}", ha="center", va="center",
                        fontsize=8 if v else 10, color="white" if v > 0.25 else INK2)
    ax.set_xticks(range(len(head) - 1))
    ax.set_xticklabels([NAMES.get(m, m) for m in head[1:]], rotation=20, ha="right")
    ax.set_yticks(range(len(regimes)))
    ax.set_yticklabels(regimes)
    ax.grid(False)
    ax.tick_params(length=0)
    cb = fig.colorbar(im, ax=ax, fraction=0.025, pad=0.015)
    cb.outline.set_visible(False)
    cb.set_label("False-green rate", color=INK2)
    save(fig, "fig_regime_heatmap")


def fig_label_audit() -> None:
    from nofalsegreen.labelviews import MEMO_ABSENCE, PROSPECTIVE
    a = load("docs/label_audit_second.json")["pairs"]
    viol = {k: v["decision"] for k, v in a.items() if v["audit"] == "violation"}
    groups = [("Memo absences (5)", [k for k in viol if k in MEMO_ABSENCE]),
              ("Future deadlines (5)", [k for k in viol if k in PROSPECTIVE]),
              ("Strict-view breaches (10)", [k for k in viol if k not in MEMO_ABSENCE | PROSPECTIVE])]
    cats = [("violation_shown", "violation shown by the exports", NAVY),
            ("cannot_tell", "cannot tell from the exports", GOLD),
            ("compliance_shown", "compliance shown", TEAL)]
    fig, ax = plt.subplots(figsize=(5.2, 1.7))
    for yi, (lab, ks) in enumerate(groups):
        left = 0
        for key, _, col in cats:
            n = sum(viol[k] == key for k in ks)
            if n:
                ax.barh(2 - yi, n, left=left, color=col, height=0.62, edgecolor="white", linewidth=1.2)
                ax.text(left + n / 2, 2 - yi, str(n), ha="center", va="center", fontsize=8,
                        color="white" if col in (NAVY, TEAL) else INK, fontweight="bold")
            left += n
    ax.set_yticks(range(3))
    ax.set_yticklabels([g[0] for g in groups][::-1])
    ax.set_xlim(0, 10)
    ax.set_xlabel("Violation labels, judged blind by the second auditor")
    ax.grid(axis="y", visible=False)
    handles = [plt.Rectangle((0, 0), 1, 1, color=c) for _, _, c in cats]
    fig.legend(handles, [l for _, l, _ in cats], loc="lower center", ncol=3, bbox_to_anchor=(0.5, -0.42))
    save(fig, "fig_label_audit")


if __name__ == "__main__":
    for f in (fig_separation, fig_study3_multiples, fig_forest, fig_rule_family, fig_detection_vs_safety,
              fig_verdict_routes, fig_regime_heatmap, fig_label_audit):
        f()
