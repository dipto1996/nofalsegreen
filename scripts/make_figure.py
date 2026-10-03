"""Figure 1: the separation plot.

Violation recall on the x axis, false-green rate on the y axis, one point per
system. The trivial baselines mark the corners, so a reader can place any model
between the unsafe floor and the attainable ceiling without reading a table.

The paper's claim is that a system can sit far right (good recall) and high
(bad false-green rate) at the same time, which is the configuration accuracy-
style scoring cannot distinguish from safety. This figure either shows models
there or it does not.

Pure SVG, no matplotlib, so the repo keeps its zero-dependency property.

    python3 scripts/make_figure.py            # -> docs/figure1_separation.svg
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

OUT = ROOT / "docs" / "figure1_separation.svg"

W, H = 640, 480
PAD_L, PAD_R, PAD_T, PAD_B = 74, 132, 44, 62
PW = W - PAD_L - PAD_R
PH = H - PAD_T - PAD_B

BASELINE_STYLE = {"fill": "#8a8a8a", "r": 5, "shape": "square"}
MODEL_STYLE = {"fill": "#1a4d7a", "r": 6, "shape": "circle"}


def x_of(recall: float) -> float:
    return PAD_L + recall * PW


def y_of(fgr: float) -> float:
    return PAD_T + (1.0 - fgr) * PH


def esc(t: str) -> str:
    return (t.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))


def collect() -> list[dict]:
    """Gather (label, recall, fgr, kind) from the results files that exist."""
    pts: list[dict] = []

    triv = ROOT / "docs" / "results.json"
    if triv.exists():
        d = json.loads(triv.read_text())
        for name, r in d["systems"].items():
            pts.append({
                "label": name,
                "recall": r["violation_recall"]["mean"],
                "fgr": r["false_green_rate"]["mean"],
                "kind": "baseline",
            })

    llm = ROOT / "docs" / "llm_results.json"
    if llm.exists():
        d = json.loads(llm.read_text())
        for key, run in d.get("runs", {}).items():
            agg = run.get("aggregate")
            if not agg:
                continue
            short = run["model"].split("/")[-1].replace(":free", "")
            variant = "offered" if run["variant"].endswith("offered") else "withheld"
            pts.append({
                "label": f"{short} ({variant})",
                "recall": agg["violation_recall"]["mean"],
                "fgr": agg["false_green_rate"]["mean"],
                "kind": "model",
            })
    return pts


def marker(p: dict, style: dict) -> str:
    x, y, r = x_of(p["recall"]), y_of(p["fgr"]), style["r"]
    if style["shape"] == "square":
        return (f'<rect x="{x - r:.1f}" y="{y - r:.1f}" width="{2 * r}" height="{2 * r}" '
                f'fill="{style["fill"]}" stroke="#fff" stroke-width="1.2"/>')
    return (f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{r}" fill="{style["fill"]}" '
            f'stroke="#fff" stroke-width="1.2"/>')


def build(pts: list[dict]) -> str:
    s: list[str] = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" '
        f'viewBox="0 0 {W} {H}" font-family="Helvetica, Arial, sans-serif">',
        f'<rect width="{W}" height="{H}" fill="#ffffff"/>',
    ]

    # The dangerous region: good recall, high false-green rate.
    s.append(f'<rect x="{x_of(0.5):.1f}" y="{PAD_T}" width="{PW / 2:.1f}" '
             f'height="{PH / 2:.1f}" fill="#fdeaea"/>')
    s.append(f'<text x="{x_of(0.97):.1f}" y="{PAD_T + 16}" font-size="9.5" '
             f'fill="#a33" text-anchor="end">looks accurate, unsafe</text>')
    s.append(f'<text x="{x_of(0.97):.1f}" y="{y_of(0.03):.1f}" font-size="9.5" '
             f'fill="#2c6e49" text-anchor="end">accurate and safe</text>')

    # grid + axes
    for i in range(6):
        f = i / 5
        gx, gy = x_of(f), y_of(f)
        s.append(f'<line x1="{gx:.1f}" y1="{PAD_T}" x2="{gx:.1f}" y2="{PAD_T + PH}" '
                 f'stroke="#e8e8e8" stroke-width="1"/>')
        s.append(f'<line x1="{PAD_L}" y1="{gy:.1f}" x2="{PAD_L + PW}" y2="{gy:.1f}" '
                 f'stroke="#e8e8e8" stroke-width="1"/>')
        s.append(f'<text x="{gx:.1f}" y="{PAD_T + PH + 16}" font-size="9.5" fill="#555" '
                 f'text-anchor="middle">{f:.1f}</text>')
        s.append(f'<text x="{PAD_L - 9}" y="{gy + 3.5:.1f}" font-size="9.5" fill="#555" '
                 f'text-anchor="end">{f:.1f}</text>')

    s.append(f'<rect x="{PAD_L}" y="{PAD_T}" width="{PW}" height="{PH}" fill="none" '
             f'stroke="#9aa5b1" stroke-width="1.2"/>')
    s.append(f'<text x="{PAD_L + PW / 2:.1f}" y="{H - 20}" font-size="11.5" fill="#222" '
             f'text-anchor="middle">violation recall  (higher is better)</text>')
    s.append(f'<text x="18" y="{PAD_T + PH / 2:.1f}" font-size="11.5" fill="#222" '
             f'text-anchor="middle" transform="rotate(-90 18 {PAD_T + PH / 2:.1f})">'
             f'false-green rate  (lower is better)</text>')
    s.append(f'<text x="{PAD_L}" y="{PAD_T - 18}" font-size="12.5" font-weight="bold" '
             f'fill="#111">Figure 1: recall does not imply safety</text>')

    # points, baselines first so models draw on top
    for p in sorted(pts, key=lambda q: q["kind"] != "baseline"):
        s.append(marker(p, BASELINE_STYLE if p["kind"] == "baseline" else MODEL_STYLE))

    # legend, right margin, so labels never overlap the plot
    ly = PAD_T + 6
    s.append(f'<text x="{PAD_L + PW + 14}" y="{ly}" font-size="10" font-weight="bold" '
             f'fill="#111">systems</text>')
    ly += 15
    for p in sorted(pts, key=lambda q: (q["kind"] != "baseline", q["label"])):
        st = BASELINE_STYLE if p["kind"] == "baseline" else MODEL_STYLE
        cx = PAD_L + PW + 20
        if st["shape"] == "square":
            s.append(f'<rect x="{cx - 4}" y="{ly - 4}" width="8" height="8" fill="{st["fill"]}"/>')
        else:
            s.append(f'<circle cx="{cx}" cy="{ly}" r="4.5" fill="{st["fill"]}"/>')
        s.append(f'<text x="{cx + 9}" y="{ly + 3.5}" font-size="8.6" fill="#333">'
                 f'{esc(p["label"])}</text>')
        ly += 14

    if not any(p["kind"] == "model" for p in pts):
        s.append(f'<text x="{PAD_L + PW / 2:.1f}" y="{PAD_T + PH / 2:.1f}" font-size="11" '
                 f'fill="#a06000" text-anchor="middle">language-model points pending '
                 f'(run scripts/run_free.py)</text>')

    s.append("</svg>")
    return "\n".join(s)


def main() -> int:
    pts = collect()
    OUT.write_text(build(pts))
    n_model = sum(1 for p in pts if p["kind"] == "model")
    print(f"wrote {OUT}")
    print(f"  {len(pts) - n_model} baseline points, {n_model} model points")
    for p in pts:
        print(f"    {p['label']:<34} recall {p['recall']:.3f}  fgr {p['fgr']:.3f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
