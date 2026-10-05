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
LIGHT = "#d9d8d3"
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

from matplotlib import font_manager as _fm  # noqa: E402

for _f in (ROOT / "paper" / "fonts").glob("*.otf"):
    _fm.fontManager.addfont(str(_f))

plt.rcParams.update({
    "font.family": "Libertinus Serif", "mathtext.fontset": "stix",
    "font.size": 8.5, "axes.titlesize": 8.8, "axes.labelsize": 8.5,
    "xtick.labelsize": 7.8, "ytick.labelsize": 7.8, "legend.fontsize": 8,
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


def rate_axis(ax, ticks=(0, 0.25, 0.5, 0.75, 1.0)):
    ax.set_yticks(list(ticks))
    ax.set_yticklabels([f"{t:.2f}" if t not in (0, 1) else f"{t:.0f}" for t in ticks])


def pair_plot(ax, yp, yd, lw=1.6, ms=4.6):
    xs = list(range(len(yp)))
    ax.fill_between(xs, yp, yd, where=[d >= p for p, d in zip(yp, yd)], interpolate=True,
                    color=BRICK, alpha=0.11, lw=0)
    ax.plot(xs, yp, color=NAVY, lw=lw, marker="o", ms=ms, mfc="white", mec=NAVY, mew=1.2, zorder=3)
    ax.plot(xs, yd, color=BRICK, lw=lw, marker="o", ms=ms, mfc=BRICK, mec="white", mew=0.7, zorder=4)


def arm_legend(fig, y=1.04, extra=True):
    h = [plt.Line2D([], [], color=NAVY, marker="o", mfc="white", mec=NAVY, mew=1.2, lw=1.5, label="plain firms"),
         plt.Line2D([], [], color=BRICK, marker="o", mfc=BRICK, mec="white", lw=1.5,
                    label="same firms with proxy columns")]
    if extra:
        h.append(plt.Rectangle((0, 0), 1, 1, color=BRICK, alpha=0.13, label="increase due to proxy columns"))
    fig.legend(handles=h, loc="upper center", ncol=len(h), bbox_to_anchor=(0.5, y))


# ---------- Figure: Study 3 by model and schema ----------

def fig_study3_multiples() -> None:
    c = load("docs/study3/results.json")["cells"]
    fig, axes = plt.subplots(1, 8, figsize=(7.0, 1.95), sharey=True)
    series = [(lab, [c[f"{m}::plain::{k}"]["false_green_rate"] for k in COND],
               [c[f"{m}::decoy::{k}"]["false_green_rate"] for k in COND]) for m, lab in S3_MODELS]
    series.append(("Mean of seven", [sum(x[1][i] for x in series) / 7 for i in range(4)],
                   [sum(x[2][i] for x in series) / 7 for i in range(4)]))
    for ax, (lab, yp, yd) in zip(axes, series):
        pair_plot(ax, yp, yd, lw=1.9 if lab.startswith("Mean") else 1.4)
        SHORT = {"Gemini 3.1 Pro": "Gemini Pro", "Gemini 3.8 Flash": "Gemini Flash", "Gemma 4 26B": "Gemma 4",
                 "gpt-oss-120b": "gpt-oss", "DeepSeek V3.2": "DeepSeek", "Qwen3 235B": "Qwen3",
                 "Kimi K2 Thinking": "Kimi K2", "Mean of seven": "Mean of 7"}
        ax.set_title(SHORT[lab], fontsize=8, pad=3, fontweight="bold" if lab.startswith("Mean") else "normal")
        ax.set_xticks(range(4))
        ax.set_xticklabels(["O", "R", "C", "D"], fontsize=7.4)
        ax.set_xlim(-0.4, 3.4)
        ax.set_ylim(-0.04, 1.02)
        if lab.startswith("Mean"):
            ax.set_facecolor("#f5f5f2")
    rate_axis(axes[0])
    axes[0].set_ylabel("False-green rate")
    arm_legend(fig, y=1.16)
    fig.subplots_adjust(wspace=0.08)
    save(fig, "fig_study3_multiples")


def fig_forest() -> None:
    d = load("docs/study3/results.json")
    names = list(d["primary"])
    titles = ["P1  Abstention\noffered → closed", "P2  Definition & warning\nclosed → dashboard",
              "P3  Proxy columns\ndashboard schema", "P4  Proxy columns\noffered schema"]
    rows = [("Pooled, 7 models", lambda n: d["primary"][n], "pool"),
            ("Google (3)", lambda n: d["S4_by_developer_group"][f"{n} | google"], "grp"),
            ("Other developers (4)", lambda n: d["S4_by_developer_group"][f"{n} | other_developers"], "grp")]
    rows += [(lab, (lambda m: lambda n: d["S1_per_model"][f"{n} | {m}"])(m), "model") for m, lab in S3_MODELS]
    fig, axes = plt.subplots(1, 4, figsize=(7.0, 2.9), sharey=True)
    ys = list(range(len(rows)))[::-1]
    for ax, n, t in zip(axes, names, titles):
        for y in ys[::2]:
            ax.axhspan(y - 0.5, y + 0.5, color="#f5f5f2", zorder=0, lw=0)
        ax.axvline(0, color=FRAME, lw=0.8, zorder=1)
        for y, (lab, get, kind) in zip(ys, rows):
            v = get(n)
            if "delta" not in v:
                continue
            sig = v.get("p_holm", 1) < 0.05
            col = NAVY if sig else MUTED
            ax.plot(v["ci95"], [y, y], color=col, lw=2.4 if kind == "pool" else 1.3, zorder=2)
            ax.scatter(v["delta"], y, s=46 if kind == "pool" else 20, marker="D" if kind == "pool" else "o",
                       color=col if sig else "white", edgecolor=col, linewidth=1.1, zorder=3)
        ax.axhline(len(rows) - 3.5, color=FRAME, lw=0.6)
        ax.set_title(t, fontsize=8, pad=4)
        ax.set_xlim(-0.15, 0.78)
        ax.set_xticks([0, 0.25, 0.5, 0.75])
        ax.set_xticklabels(["0", "0.25", "0.50", "0.75"])
        ax.grid(axis="y", visible=False)
        ax.set_ylim(-0.6, len(rows) - 0.4)
    axes[0].set_yticks(ys)
    axes[0].set_yticklabels([r[0] for r in rows])
    axes[0].get_yticklabels()[0].set_fontweight("bold")
    fig.subplots_adjust(wspace=0.07)
    save(fig, "fig_forest")


def fig_i9() -> None:
    """(a, b) Study 3 by rule family; (c) Study 3c, I-9 false greens by which proxy column is present."""
    f = load("docs/study3/results.json")["exploratory_by_rule_family"]
    fig = plt.figure(figsize=(7.0, 2.35))
    axa = fig.add_axes([0.065, 0.17, 0.2, 0.68])
    axb = fig.add_axes([0.285, 0.17, 0.2, 0.68], sharey=axa)
    axc = fig.add_axes([0.70, 0.17, 0.29, 0.68])
    for ax, fam, title in ((axa, "i9", "(a) Study 3, I-9 rules"), (axb, "wage", "(b) Study 3, wage rule")):
        yp = [f[f"{fam}::plain::{k}"] for k in COND]
        yd = [f[f"{fam}::decoy::{k}"] for k in COND]
        pair_plot(ax, yp, yd, lw=1.6, ms=4.6)
        ax.set_title(title, fontsize=8.4, pad=4)
        ax.set_xticks(range(4))
        ax.set_xticklabels(["O", "R", "C", "D"])
        ax.set_xlim(-0.4, 3.4)
        ax.set_ylim(-0.04, 1.02)
    rate_axis(axa)
    plt.setp(axb.get_yticklabels(), visible=False)
    axa.set_ylabel("False-green rate")
    c3 = ROOT / "docs" / "study3c" / "results.json"
    if c3.exists():
        r = load("docs/study3c/results.json")["rates"]
        models = ["gemini-3.1-pro-preview", "gemini-3.8-flash", "gemma-4-26b-a4b-it-maas"]

        def rate(m, arm, fams):
            ks = [f"{m}::{arm}::abstain_withheld::{x}" for x in fams]
            n = sum(r[k]["n"] for k in ks if k in r)
            return sum(r[k]["fgr"] * r[k]["n"] for k in ks if k in r) / n if n else None
        rows = [("no proxy column", "plain", ("S1+S2", "reverification")),
                ("I-9 status only", "only_i9Status", ("S1+S2",)),
                ("onboarding date only", "only_onboardingCompletedDate", ("S1+S2",)),
                ("authorisation end only", "only_workAuthValidThrough", ("reverification",)),
                ("all five columns", "proxy", ("S1+S2", "reverification"))]
        for y, (lab, arm, fams) in enumerate(rows):
            xs = [v for v in (rate(m, arm, fams) for m in models) if v is not None]
            col = NAVY if arm == "plain" else BRICK
            axc.plot([min(xs), max(xs)], [y, y], color=col, lw=1, alpha=0.5, zorder=2)
            axc.scatter(xs, [y] * len(xs), s=14, color="white", edgecolor=col, linewidth=1, zorder=3)
            axc.scatter(sum(xs) / len(xs), y, s=42, marker="D", color=col, zorder=4)
        axc.set_yticks(range(len(rows)))
        axc.set_yticklabels([x[0] for x in rows], fontsize=7.8)
        axc.invert_yaxis()
        axc.set_xlim(-0.03, 1.03)
        axc.set_xticks([0, 0.25, 0.5, 0.75, 1])
        axc.set_xticklabels(["0", "0.25", "0.50", "0.75", "1"])
        axc.grid(axis="y", visible=False)
        axc.set_title("(c) Study 3c, dashboard schema", fontsize=8.4, pad=4)
        axc.set_xlabel("False-green rate on I-9 pairs")
    h = [plt.Line2D([], [], color=NAVY, marker="o", mfc="white", mec=NAVY, mew=1.2, lw=1.5, label="plain firms"),
         plt.Line2D([], [], color=BRICK, marker="o", mfc=BRICK, mec="white", lw=1.5, label="with proxy columns"),
         plt.Line2D([], [], ls="", marker="D", color=INK2, label="mean of three models"),
         plt.Line2D([], [], ls="", marker="o", mfc="white", mec=INK2, label="each model")]
    fig.legend(handles=h, loc="upper center", ncol=4, bbox_to_anchor=(0.5, 1.07))
    save(fig, "fig_i9")


# ---------- Figure: Study 4 controls, factorial and cite-first ----------

def fig_study4() -> None:
    r = load("docs/study4/results.json")["cells"]

    def rate(arm, var, verdict="pass"):
        bm = r[f"{arm}::{var}::r0"]["by_model"].values()
        per = [x["allocation"].get(verdict, 0) / max(1, sum(v for k, v in x["allocation"].items() if k != "unanswered"))
               for x in bm]
        return sum(per) / len(per), per

    fig = plt.figure(figsize=(7.0, 3.35))
    gs = fig.add_gridspec(2, 2, width_ratios=[1, 1], height_ratios=[5, 2.6], wspace=0.78, hspace=0.95,
                          left=0.205, right=0.985, bottom=0.12, top=0.93)

    def dumbbell(ax, rows, title, xlabel, legend):
        for i, (lab, a, b) in enumerate(rows):
            ax.plot([a[0], b[0]], [i, i], color=LIGHT, lw=2.4, zorder=1, solid_capstyle="round")
            for (m, per), col, kw in ((a, NAVY, dict(marker="o", mfc="white", mec=NAVY, mew=1.3)),
                                      (b, BRICK, dict(marker="o", mfc=BRICK, mec="white", mew=0.7))):
                ax.plot(per, [i] * len(per), ls="", marker="|", ms=5.5, color=col, alpha=0.5, zorder=2)
                ax.plot([m], [i], ls="", ms=6.2, zorder=3, **kw)
        ax.set_yticks(range(len(rows)))
        ax.set_yticklabels([x[0] for x in rows], fontsize=7.5)
        ax.set_ylim(len(rows) - 0.4, -0.6)
        ax.set_xlim(-0.03, 1.03)
        ax.set_xticks([0, 0.25, 0.5, 0.75, 1])
        ax.set_xticklabels(["0", "", "0.50", "", "1"])
        ax.grid(axis="y", visible=False)
        ax.set_title(title, fontsize=8.2, pad=13, loc="left")
        ax.set_xlabel(xlabel, fontsize=7.8, labelpad=2)
        h = [plt.Line2D([], [], ls="", marker="o", mfc="white", mec=NAVY, mew=1.3, label=legend[0]),
             plt.Line2D([], [], ls="", marker="o", mfc=BRICK, mec="white", label=legend[1])]
        ax.legend(handles=h, loc="lower left", bbox_to_anchor=(-0.02, 0.99), ncol=2, fontsize=7,
                  frameon=False, handletextpad=0.2, columnspacing=1.0, borderaxespad=0)

    off, dash = "abstain_offered", "abstain_withheld"
    dumbbell(fig.add_subplot(gs[0, 0]), [(lab, rate(a, off), rate(a, dash)) for lab, a in
                                         (("nothing added", "plain"), ("irrelevant columns", "irrelevant"),
                                          ("proxy values, neutral names", "renamed"), ("proxy columns", "proxy"),
                                          ("adverse proxy columns", "adverse"))],
             "(a) What is added to the roster", "False-green rate", ("offered schema", "dashboard schema"))
    dumbbell(fig.add_subplot(gs[1, 0]), [(lab, rate(a, off, "fail"), rate(a, dash, "fail")) for lab, a in
                                         (("nothing added", "plain"), ("adverse proxy columns", "adverse"))],
             "(b) Do adverse proxies push toward fail?", "Share of unassessable pairs answered fail",
             ("offered schema", "dashboard schema"))
    ax = fig.add_subplot(gs[:, 1])
    menus = [("fx_o1d1w1", "all three parts"), ("fx_o1d1w0", "− warning"), ("fx_o1d0w1", "− evidence definitions"),
             ("fx_o1d0w0", "− definitions, − warning"), ("fx_o0d1w1", "− abstaining verdicts"),
             ("fx_o0d1w0", "− abstaining, − warning"), ("fx_o0d0w1", "− abstaining, − definitions"),
             ("fx_o0d0w0", "none (dashboard-like)"), ("cite_first", "offered + name the record")]
    dumbbell(ax, [(lab, rate("plain", v), rate("proxy", v)) for v, lab in menus],
             "(c) Verdict-menu parts, one at a time", "False-green rate", ("plain firms", "proxy-column firms"))
    ax.axhline(7.5, color=INK2, lw=0.6, ls=(0, (2, 2)))
    save(fig, "fig_study4")


# ---------- the separation plot (anchor firm, thirteen models) ----------

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
    pts = anchor_points()
    triv = load("docs/results.json")["systems"]
    fig = plt.figure(figsize=(7.0, 3.0))
    ax = fig.add_axes([0.07, 0.14, 0.55, 0.82])
    ax.add_patch(plt.Rectangle((0.5, 0.3), 0.6, 0.8, color=SHADE_BAD, lw=0, zorder=0))
    ax.set_xlim(-0.03, 1.05)
    ax.set_ylim(-0.09, 1.05)
    fig.canvas.draw()
    to_px = ax.transData.transform
    pts_px = [to_px(w) for _, _, w in pts]
    placed_px: list = []
    for i, (name, o, w) in enumerate(pts, 1):
        ax.plot([o[0], w[0]], [o[1], w[1]], color=NAVY, alpha=0.4, lw=0.85, zorder=2)
        ax.scatter(*o, s=28, color=NAVY, edgecolor="white", linewidth=0.7, zorder=4)
        ax.scatter(*w, s=28, facecolor="white", edgecolor=BRICK, linewidth=1.2, zorder=4)
        px = to_px(w)
        best = None
        for off in ((6, 5), (6, -6), (-6, 5), (-6, -6), (0, 8), (0, -9)):
            cand = (px[0] + off[0] * fig.dpi / 72, px[1] + off[1] * fig.dpi / 72)
            clash = sum(((cand[0] - q[0]) ** 2 + (cand[1] - q[1]) ** 2) ** 0.5 < 8.5 * fig.dpi / 72
                        for q in placed_px) + sum(((cand[0] - q[0]) ** 2 + (cand[1] - q[1]) ** 2) ** 0.5
                                                  < 4.5 * fig.dpi / 72 for q in pts_px)
            if best is None or clash < best[0]:
                best = (clash, off, cand)
            if clash == 0:
                break
        placed_px.append(best[2])
        ax.annotate(str(i), w, xytext=best[1], textcoords="offset points", fontsize=7, color=INK,
                    fontweight="bold", zorder=6, path_effects=HALO, ha="center", va="center")
    # Trivial baselines. Recall and false-green rate cannot tell the oracle from
    # always_fail, so each label carries its false-alarm rate on conforming pairs.
    placed: dict[tuple, list[str]] = {}
    for name, r in triv.items():
        placed.setdefault((round(r["violation_recall"]["mean"], 3), round(r["false_green_rate"]["mean"], 3)), []).append(name)
    for xy, names in placed.items():
        ax.scatter(*xy, s=34, marker="s", color=MUTED, zorder=5, clip_on=False)
        right, top = xy[0] > 0.5, xy[1] > 0.5
        lab = "; ".join(f"{n.replace('_', ' ')} (false alarms {triv[n]['false_alarm_rate']['mean']:.0f})"
                        for n in sorted(names, key=lambda n: triv[n]["false_alarm_rate"]["mean"]))
        ax.annotate(lab, xy, xytext=(-7 if right else 7, -10 if top else -1),
                    textcoords="offset points", fontsize=7, color=INK2, style="italic",
                    ha="right" if right else "left", va="baseline" if top else "top")
    ax.set_xlim(-0.03, 1.05)
    ax.set_ylim(-0.09, 1.05)
    rate_axis(ax)
    ax.set_xticks([0, 0.25, 0.5, 0.75, 1])
    ax.set_xticklabels(["0", "0.25", "0.50", "0.75", "1"])
    ax.set_xlabel("Violation recall (source-engine labels)")
    ax.set_ylabel("False-green rate")
    kx = fig.add_axes([0.65, 0.14, 0.34, 0.82])
    kx.axis("off")
    kx.set_xlim(0, 1)
    kx.set_ylim(0, 1)
    half = (len(pts) + 1) // 2
    for i, (name, _, _) in enumerate(pts, 1):
        col, row = (0, i - 1) if i <= half else (1, i - 1 - half)
        x0, y0 = 0.02 + col * 0.52, 0.97 - row * 0.075
        kx.text(x0 + 0.05, y0, f"{i}", fontsize=7, color=INK, ha="right", va="top", fontweight="bold")
        kx.text(x0 + 0.08, y0, name, fontsize=7, color=INK2, va="top")
    yb = 0.97 - half * 0.075 - 0.06
    for dx, kw, lab in ((0.0, dict(s=28, color=NAVY, edgecolor="white"), "abstention offered"),
                        (0.0, dict(s=28, facecolor="white", edgecolor=BRICK, linewidth=1.2), "dashboard schema"),
                        (0.0, dict(s=30, marker="s", color=MUTED), "trivial baseline")):
        kx.scatter(0.05, yb - 0.012, clip_on=False, **kw)
        kx.text(0.1, yb, lab, fontsize=7.4, va="top")
        yb -= 0.075
    save(fig, "fig_separation")


# ---------- appendix ----------

def fig_verdict_flow() -> None:
    """Study 3, proxy-column firms: where the 180 unassessable pairs go, per model and schema."""
    fl = load("docs/study3/exploratory.json")["verdict_flow"]
    cats = [("needs_evidence", "needs_evidence (correct)", NAVY), ("unmonitored", "unmonitored", TEAL),
            ("fail", "fail", GOLD), ("pass", "pass (false green)", BRICK), ("unanswered", "no answer", LIGHT)]
    fig, axes = plt.subplots(1, 4, figsize=(7.0, 2.5), sharey=True)
    short = {m: lab for m, lab in S3_MODELS}
    for ax, k, t in zip(axes, COND, ["offered", "removed-only", "closed", "dashboard"]):
        for yi, (m, lab) in enumerate(S3_MODELS):
            key = f"{m}::decoy::{k}"
            d = fl[key]
            left = 0
            for c, _, col in cats:
                w = d.get(c, 0)
                if w:
                    ax.barh(yi, w, left=left, color=col, height=0.7, edgecolor="white", linewidth=0.8)
                    if c == "pass" and w >= 9:
                        ax.text(left + w / 2, yi, str(w), ha="center", va="center", fontsize=6.6, color="white")
                left += w
        ax.set_title(t, fontsize=8.4, pad=4)
        ax.set_xlim(0, 180)
        ax.set_xticks([0, 60, 120])
        ax.grid(axis="y", visible=False)
    axes[0].set_yticks(range(len(S3_MODELS)))
    axes[0].set_yticklabels([lab for _, lab in S3_MODELS])
    axes[0].invert_yaxis()
    axes[1].set_xlabel("The 180 unassessable pairs of the proxy-column firms, by verdict", x=1.05)
    h = [plt.Rectangle((0, 0), 1, 1, color=c) for _, _, c in cats]
    fig.legend(h, [l for _, l, _ in cats], loc="lower center", ncol=5, bbox_to_anchor=(0.5, -0.12))
    fig.subplots_adjust(wspace=0.08)
    save(fig, "fig_verdict_flow")


def fig_detection_vs_safety() -> None:
    c = load("docs/study3/results.json")["cells"]
    fig, ax = plt.subplots(figsize=(3.3, 2.5))
    for m, lab in S3_MODELS:
        x = c[f"{m}::decoy::abstain_offered"]["violation_recall"]
        y = c[f"{m}::decoy::abstain_offered"]["false_green_rate"]
        ax.scatter(x, y, s=26, color=BRICK, edgecolor="white", linewidth=0.7, zorder=4)
        slot = {"Gemini 3.8 Flash": 0.52, "gpt-oss-120b": 0.43, "Gemini 3.1 Pro": 0.10, "Kimi K2 Thinking": 0.03}
        if lab in slot:
            ax.annotate(lab, (x, y), xytext=(0.8, slot[lab]), textcoords="data", ha="right", va="center",
                        fontsize=7, color=INK2,
                        arrowprops=dict(arrowstyle="-", color=MUTED, lw=0.5, shrinkA=1, shrinkB=3))
        else:
            ax.annotate(lab, (x, y), xytext=(5, 2), textcoords="offset points", fontsize=7, color=INK2)
    ax.set_xlim(0, 1.05)
    ax.set_ylim(0, 1.0)
    rate_axis(ax)
    ax.set_xlabel("Violation recall")
    ax.set_ylabel("False-green rate")
    save(fig, "fig_detection_vs_safety")


def fig_regime_heatmap() -> None:
    paper = (ROOT / "docs" / "PAPER.md").read_text()
    block = paper[paper.index("BEGIN GENERATED: table4-regime"):paper.index("END GENERATED: table4-regime")]
    lines = [l for l in block.splitlines() if l.startswith("|")]
    head = [h.strip(" `") for h in lines[0].strip("|").split("|")]
    rows = [[c.strip(" `") for c in l.strip("|").split("|")] for l in lines[2:]]
    vals = [[float(re.match(r"[\d.]+", c).group()) if re.match(r"[\d.]+", c) else float("nan") for c in r[1:]] for r in rows]
    ns = [re.search(r"\((\d+)\)", r[1]).group(1) if re.search(r"\((\d+)\)", r[1]) else "" for r in rows]
    regimes = [f"{r[0]}  (n = {n})" for r, n in zip(rows, ns)]
    cmap = LinearSegmentedColormap.from_list("seq", ["#fbfbfa", "#c9dbee", "#5f8fc4", NAVY, "#0e2f52"])
    fig, ax = plt.subplots(figsize=(6.4, 0.3 * len(rows) + 1.0))
    im = ax.imshow(vals, cmap=cmap, vmin=0, vmax=0.45, aspect="auto")
    for i, r in enumerate(vals):
        for j, v in enumerate(r):
            if v == v:
                ax.text(j, i, "·" if v == 0 else f"{v:.2f}", ha="center", va="center",
                        fontsize=7.6 if v else 9, color="white" if v > 0.25 else INK2)
    ax.set_xticks(range(len(head) - 1))
    ax.set_xticklabels([NAMES.get(m, m) for m in head[1:]], rotation=20, ha="right")
    ax.set_yticks(range(len(rows)))
    ax.set_yticklabels(regimes)
    ax.grid(False)
    ax.tick_params(length=0)
    cb = fig.colorbar(im, ax=ax, fraction=0.025, pad=0.015)
    cb.outline.set_visible(False)
    cb.set_label("False-green rate", color=INK2)
    save(fig, "fig_regime_heatmap")


if __name__ == "__main__":
    for f in (fig_study3_multiples, fig_forest, fig_i9, fig_separation, fig_verdict_flow,
              fig_detection_vs_safety, fig_regime_heatmap, fig_study4):
        f()
