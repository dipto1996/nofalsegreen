"""Run free-tier models, resumably, across multiple days of quota.

    export GEMINI_API_KEY=...
    python3 scripts/run_free.py --provider gemini --model gemini-2.5-flash \
        --firms 0 --variant both            # anchor firm only: 24 calls

    python3 scripts/run_free.py --provider gemini --model gemini-2.5-flash \
        --firms 5 --variant both            # spans ~4 days of free quota

Re-run the same command each day. Completed (model, variant, firm) runs are
skipped via the checkpoint, so the sweep continues where the quota ran out.
Exits 0 on daily-quota exhaustion, since that is expected rather than a failure.
"""

from __future__ import annotations

import argparse
import json
import statistics
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from baselines.freetier import (  # noqa: E402
    FREE_PROVIDERS,
    FREE_QUOTAS,
    Checkpoint,
    DailyQuotaExhausted,
    Quota,
)
from baselines.llm import Usage, run_firm  # noqa: E402
from baselines.prompts import ABSTAIN_OFFERED, ABSTAIN_WITHHELD, PROMPT_VERSION  # noqa: E402
from nofalsegreen import northwind  # noqa: E402
from nofalsegreen.generator import FirmGenerator, GeneratorConfig  # noqa: E402
from nofalsegreen.metrics import score  # noqa: E402
from nofalsegreen.rulebook import Rulebook  # noqa: E402
from nofalsegreen.subset import DEFAULT_SIZE, subset_firm  # noqa: E402

ANCHOR = ROOT / "data" / "firms" / "northwind-robotics"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--provider", required=True, choices=sorted(FREE_PROVIDERS))
    ap.add_argument("--model", required=True)
    ap.add_argument("--firms", type=int, default=0, help="generated firms (0 = anchor only)")
    ap.add_argument("--variant", default="both",
                    choices=[ABSTAIN_OFFERED, ABSTAIN_WITHHELD, "both"])
    ap.add_argument("--batch", type=int, default=8,
                    help="pairs per call; reasoning models need a small batch "
                         "so their trace plus verdicts fit the output budget")
    ap.add_argument("--workers", type=int, default=12)
    ap.add_argument("--no-scope-sources", action="store_true",
                    help="send all exports every call (needs a large tpm quota)")
    ap.add_argument("--rpm", type=int, default=None, help="override published rpm")
    ap.add_argument("--rpd", type=int, default=None, help="override published rpd")
    ap.add_argument("--out", default=str(ROOT / "docs" / "llm_results.json"))
    ap.add_argument("--checkpoint", default=str(ROOT / "docs" / ".free_checkpoint.json"))
    ap.add_argument("--subset", type=int, default=0,
                    help=f"evaluate the declared stratified subset of N pairs "
                         f"(0 = full firm; {DEFAULT_SIZE} is the standard subset)")
    args = ap.parse_args()

    quota = FREE_QUOTAS.get(args.model) or Quota(rpm=10, rpd=250, label=f"{args.model} (assumed)")
    if args.rpm:
        quota = Quota(args.rpm, args.rpd or quota.rpd, quota.tpm, quota.label + " (overridden)")
    elif args.rpd:
        quota = Quota(quota.rpm, args.rpd, quota.tpm, quota.label + " (overridden)")

    rb = Rulebook.load(ROOT / "rulebook" / "rulebook.json")
    regimes = rb.rule_regimes()
    gen = FirmGenerator(rb, GeneratorConfig(n_workers=args.workers))

    anchor = northwind.load(ANCHOR, ANCHOR / "expectations.json")
    if args.subset:
        anchor = subset_firm(anchor, regimes, size=args.subset)
        print(f"using declared subset: {len(anchor.pairs)} of "
              f"{anchor.provenance['parent_pairs']} pairs "
              f"(seed {anchor.provenance['subset_seed']})")
    firms = [anchor]
    for seed in range(1, args.firms + 1):
        firms.append(gen.generate(seed, ROOT / ".llm-tmp" / f"s{seed}"))

    variants = [ABSTAIN_OFFERED, ABSTAIN_WITHHELD] if args.variant == "both" else [args.variant]
    scope = not args.no_scope_sources

    provider = FREE_PROVIDERS[args.provider](args.model, quota)
    ckpt = Checkpoint(Path(args.checkpoint))
    out_path = Path(args.out)
    doc = json.loads(out_path.read_text()) if out_path.exists() else {
        "prompt_version": PROMPT_VERSION, "runs": {}
    }

    print(f"{args.model} via {args.provider}  quota {quota.as_dict()}")
    print(f"batch {args.batch}  scoped_sources {scope}  firms {len(firms)}  variants {variants}\n")

    exhausted = False
    for variant in variants:
        key = f"{args.model}::{variant}"
        run = doc["runs"].setdefault(key, {
            "model": args.model, "provider": args.provider, "variant": variant,
            "prompt_version": PROMPT_VERSION, "batch_size": args.batch,
            "scope_sources": scope, "quota": quota.as_dict(),
            "free_tier": True, "per_firm": [], "usage":
                {"input_tokens": 0, "output_tokens": 0, "calls": 0, "wall_seconds": 0.0},
        })
        seen = {f["firm_id"] for f in run["per_firm"]}

        for firm in firms:
            if firm.firm_id in seen or ckpt.done(args.model, variant, firm.firm_id):
                print(f"  {firm.firm_id:<22} skip (done)")
                continue
            t0 = time.time()
            try:
                r = run_firm(provider, firm, rb.obligations, variant=variant,
                             batch_size=args.batch, scope_sources=scope, keep_raw=True,
                             progress=True,
                             cache_path=ROOT / "docs" / ".batch_cache.json")
            except DailyQuotaExhausted as e:
                print(f"\n  daily quota exhausted: {str(e)[:160]}")
                print("  progress saved; re-run the same command tomorrow to continue.")
                exhausted = True
                break

            s = score(firm.labels, r.predictions, rule_regimes=regimes)
            run["per_firm"].append({
                "firm_id": firm.firm_id,
                "n_pairs": r.n_pairs, "n_parsed": r.n_parsed,
                "n_unparseable": r.n_unparseable, "n_off_schema": r.n_off_schema,
                "n_truncated_calls": r.n_truncated_calls,
                "false_green_rate": s.false_green_rate,
                "n_false_green": s.n_false_green, "n_withheld": s.n_withheld,
                "violation_recall": s.violation_recall,
                "violation_precision": s.violation_precision,
                "false_alarm_rate": s.false_alarm_rate,
                "abstention_precision": s.abstention_precision,
                "abstention_recall": s.abstention_recall,
                "abstention_f1": s.abstention_f1,
                "n_missing": s.n_missing, "per_regime": s.per_regime,
            })
            u = run["usage"]
            u["input_tokens"] += r.usage.input_tokens
            u["output_tokens"] += r.usage.output_tokens
            u["calls"] += r.usage.calls
            u["wall_seconds"] = round(u["wall_seconds"] + (time.time() - t0), 1)

            raw_dir = ROOT / "docs" / "raw" / f"{args.model.replace('/', '_')}__{variant}"
            raw_dir.mkdir(parents=True, exist_ok=True)
            (raw_dir / f"{firm.firm_id}.txt").write_text("\n\n---\n\n".join(r.raw))

            ckpt.mark(args.model, variant, firm.firm_id, r.usage)
            out_path.parent.mkdir(parents=True, exist_ok=True)
            out_path.write_text(json.dumps(doc, indent=2))
            trunc = f"  TRUNCATED {r.n_truncated_calls}" if r.n_truncated_calls else ""
            print(f"  {firm.firm_id:<22} FGR {s.false_green_rate:.3f}  "
                  f"recall {s.violation_recall:.3f}  absF1 {s.abstention_f1:.3f}  "
                  f"unparsed {r.n_unparseable}  ({r.usage.calls} calls){trunc}")

        if run["per_firm"]:
            def agg(k: str) -> dict:
                xs = [f[k] for f in run["per_firm"]]
                return {
                    "mean": round(statistics.mean(xs), 4),
                    "stdev": round(statistics.stdev(xs), 4) if len(xs) > 1 else 0.0,
                    "min": round(min(xs), 4), "max": round(max(xs), 4), "n_firms": len(xs),
                }
            run["aggregate"] = {k: agg(k) for k in (
                "false_green_rate", "violation_recall", "violation_precision",
                "false_alarm_rate", "abstention_precision", "abstention_recall",
                "abstention_f1")}
            run["n_pairs"] = sum(f["n_pairs"] for f in run["per_firm"])
            run["n_unparseable"] = sum(f["n_unparseable"] for f in run["per_firm"])
            run["n_off_schema"] = sum(f["n_off_schema"] for f in run["per_firm"])
            run["n_truncated_calls"] = sum(f.get("n_truncated_calls", 0) for f in run["per_firm"])
            a = run["aggregate"]
            print(f"\n  {key}: FGR {a['false_green_rate']['mean']:.3f} "
                  f"(sd {a['false_green_rate']['stdev']:.3f})  "
                  f"recall {a['violation_recall']['mean']:.3f}  "
                  f"over {a['false_green_rate']['n_firms']} firm(s)\n")

        out_path.write_text(json.dumps(doc, indent=2))
        if exhausted:
            break

    out_path.write_text(json.dumps(doc, indent=2))
    print(f"wrote {out_path}")
    # Quota exhaustion is expected, not a failure: exit 0 so a cron/loop can retry.
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
