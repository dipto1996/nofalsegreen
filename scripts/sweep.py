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
        # A rate enters a firm's average only where its denominator exists in
        # that firm: a generated firm may have no violations, or no withheld
        # pairs, and scoring an undefined rate as 0 would bias every mean.
        per: dict[str, list[float]] = {k: [] for k in
                                       ("false_green_rate", "violation_recall", "violation_precision",
                                        "false_alarm_rate", "abstention_f1")}
        for _, firm in firms:
            preds = fn(firm)
            r = score(firm.labels, preds, rule_regimes=regimes)
            v = [l.verdict.value for l in firm.labels]
            pv = {p.pair_id: p.verdict.value for p in preds}
            if "needs_evidence" in v:
                per["false_green_rate"].append(r.false_green_rate)
                per["abstention_f1"].append(r.abstention_f1)
            if "fail" in v:
                per["violation_recall"].append(r.violation_recall)
            if "fail" in pv.values():
                per["violation_precision"].append(r.violation_precision)
            if "pass" in v:
                per["false_alarm_rate"].append(r.false_alarm_rate)

        def agg(xs: list[float]) -> dict:
            if not xs:
                return {"mean": None, "stdev": None, "min": None, "max": None, "n_firms": 0}
            return {
                "mean": round(statistics.mean(xs), 4),
                "stdev": round(statistics.stdev(xs), 4) if len(xs) > 1 else 0.0,
                "min": round(min(xs), 4),
                "max": round(max(xs), 4),
                "n_firms": len(xs),
            }

        rows[name] = {k: agg(xs) for k, xs in per.items()}

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
              + "".join(f"{(r[k]['mean'] if r[k]['mean'] is not None else float('nan')):>{w}.3f}"
                        for k, w in (("false_green_rate", 8), ("violation_recall", 9),
                                     ("violation_precision", 8), ("false_alarm_rate", 9),
                                     ("abstention_f1", 8))))

    doc = {
        "n_firms": len(firms),
        "n_pairs": total_pairs,
        "n_withheld": total_withheld,
        "n_planted_violations": total_fails,
        "rulebook_version": rb.version,
        "rulebook_obligations": len(rb.obligations),
        "systems": rows,
        "generator": "v2",
        "note": (
            "Trivial baselines only; language-model results are in llm_results.json "
            "(Study 1) and study2/llm_results.json (Study 2). Each mean is over the "
            "firms in which the rate is defined (n_firms)."
        ),
    }
    Path(args.out).write_text(json.dumps(doc, indent=2))
    print(f"\nwrote {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
