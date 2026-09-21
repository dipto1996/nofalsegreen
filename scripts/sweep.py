"""Run every baseline across the anchor firm plus N generated firms.

Emits the results table used in the paper, plus a JSON record for the repo.

    python3 scripts/sweep.py --firms 30
"""

from __future__ import annotations

import argparse
import json
import statistics
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from baselines.trivial import REGISTRY  # noqa: E402
from nofalsegreen import northwind  # noqa: E402
from nofalsegreen.generator import FirmGenerator, GeneratorConfig  # noqa: E402
from nofalsegreen.metrics import score  # noqa: E402
from nofalsegreen.rulebook import Rulebook  # noqa: E402

ANCHOR = ROOT / "data" / "firms" / "northwind-robotics"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--firms", type=int, default=30, help="number of generated firms")
    ap.add_argument("--workers", type=int, default=12)
    ap.add_argument("--out", default=str(ROOT / "docs" / "results.json"))
    args = ap.parse_args()

    rb = Rulebook.load(ROOT / "rulebook" / "rulebook.json")
    regimes = rb.rule_regimes()
    gen = FirmGenerator(rb, GeneratorConfig(n_workers=args.workers))
    scratch = ROOT / ".sweep-tmp"

    anchor = northwind.load(ANCHOR, ANCHOR / "expectations.json")
    firms = [("northwind-robotics", anchor)]
    for seed in range(1, args.firms + 1):
        firms.append((f"synthetic-{seed:06d}", gen.generate(seed, scratch / f"s{seed}")))

    rows: dict[str, dict] = {}
    for name, fn in REGISTRY.items():
        fg, vr, vp, fa, af = [], [], [], [], []
        for _, firm in firms:
            r = score(firm.labels, fn(firm), rule_regimes=regimes)
            fg.append(r.false_green_rate)
            vr.append(r.violation_recall)
            vp.append(r.violation_precision)
            fa.append(r.false_alarm_rate)
            af.append(r.abstention_f1)

        def agg(xs: list[float]) -> dict:
            return {
                "mean": round(statistics.mean(xs), 4),
                "stdev": round(statistics.stdev(xs), 4) if len(xs) > 1 else 0.0,
                "min": round(min(xs), 4),
                "max": round(max(xs), 4),
            }

        rows[name] = {
            "false_green_rate": agg(fg),
            "violation_recall": agg(vr),
            "violation_precision": agg(vp),
            "false_alarm_rate": agg(fa),
            "abstention_f1": agg(af),
        }

    total_pairs = sum(len(f.pairs) for _, f in firms)
    total_withheld = sum(
        sum(1 for l in f.labels if l.verdict.value == "needs_evidence") for _, f in firms
    )
    total_fails = sum(sum(1 for l in f.labels if l.verdict.value == "fail") for _, f in firms)

    print(f"firms {len(firms)}  pairs {total_pairs}  "
          f"withheld {total_withheld} ({total_withheld/total_pairs:.1%})  fails {total_fails}")
    print()
    hdr = f"{'system':<16}{'FGR':>8}{'recall':>9}{'prec':>8}{'falarm':>9}{'absF1':>8}"
    print(hdr)
    print("-" * len(hdr))
    for name, r in rows.items():
        print(f"{name:<16}"
              f"{r['false_green_rate']['mean']:>8.3f}"
              f"{r['violation_recall']['mean']:>9.3f}"
              f"{r['violation_precision']['mean']:>8.3f}"
              f"{r['false_alarm_rate']['mean']:>9.3f}"
              f"{r['abstention_f1']['mean']:>8.3f}")

    doc = {
        "n_firms": len(firms),
        "n_pairs": total_pairs,
        "n_withheld": total_withheld,
        "n_planted_violations": total_fails,
        "rulebook_version": rb.version,
        "rulebook_obligations": len(rb.obligations),
        "systems": rows,
        "note": (
            "Trivial baselines only. No language-model results are reported here; "
            "those experiments have not been run."
        ),
    }
    Path(args.out).write_text(json.dumps(doc, indent=2))
    print(f"\nwrote {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
