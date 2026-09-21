"""Run language-model baselines and score them.

    # dry run, no keys needed, exercises the whole path
    python3 scripts/run_llm.py --model mock-guesser --firms 2

    # real run
    export ANTHROPIC_API_KEY=...
    python3 scripts/run_llm.py --provider anthropic --model <model-id> --firms 0
    python3 scripts/run_llm.py --provider anthropic --model <model-id> --firms 30 \
        --variant both --out docs/llm_results.json

Results are appended to the output file keyed by (model, variant), so the sweep
can be run incrementally and resumed. Raw responses are written per run when
--keep-raw is set, so any reported number can be traced back to model output.
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

from baselines.llm import PROVIDERS, MockProvider, Usage, run_firm  # noqa: E402
from baselines.prompts import ABSTAIN_OFFERED, ABSTAIN_WITHHELD, PROMPT_VERSION  # noqa: E402
from nofalsegreen import northwind  # noqa: E402
from nofalsegreen.generator import FirmGenerator, GeneratorConfig  # noqa: E402
from nofalsegreen.metrics import score  # noqa: E402
from nofalsegreen.rulebook import Rulebook  # noqa: E402
from nofalsegreen.schema import Verdict  # noqa: E402

ANCHOR = ROOT / "data" / "firms" / "northwind-robotics"


def build_provider(args, firm_truth):
    if args.provider == "mock":
        if args.model == "mock-guesser":
            return MockProvider(
                lambda pid: "fail" if firm_truth()[pid].verdict is Verdict.FAIL else "pass",
                "mock-guesser",
            )
        if args.model == "mock-careful":
            return MockProvider(lambda pid: firm_truth()[pid].verdict.value, "mock-careful")
        raise SystemExit(f"unknown mock model {args.model}")
    cls = PROVIDERS.get(args.provider)
    if not cls:
        raise SystemExit(f"unknown provider {args.provider}; have {sorted(PROVIDERS)} or 'mock'")
    return cls(args.model)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--provider", default="mock", help="mock | anthropic | openai")
    ap.add_argument("--model", default="mock-guesser")
    ap.add_argument("--firms", type=int, default=0, help="generated firms (0 = anchor only)")
    ap.add_argument("--variant", default=ABSTAIN_OFFERED,
                    choices=[ABSTAIN_OFFERED, ABSTAIN_WITHHELD, "both"])
    ap.add_argument("--batch", type=int, default=40)
    ap.add_argument("--workers", type=int, default=12)
    ap.add_argument("--out", default=str(ROOT / "docs" / "llm_results.json"))
    ap.add_argument("--keep-raw", action="store_true")
    args = ap.parse_args()

    rb = Rulebook.load(ROOT / "rulebook" / "rulebook.json")
    regimes = rb.rule_regimes()
    gen = FirmGenerator(rb, GeneratorConfig(n_workers=args.workers))

    firms = [northwind.load(ANCHOR, ANCHOR / "expectations.json")]
    for seed in range(1, args.firms + 1):
        firms.append(gen.generate(seed, ROOT / ".llm-tmp" / f"s{seed}"))

    variants = [ABSTAIN_OFFERED, ABSTAIN_WITHHELD] if args.variant == "both" else [args.variant]

    out_path = Path(args.out)
    doc = json.loads(out_path.read_text()) if out_path.exists() else {
        "prompt_version": PROMPT_VERSION, "runs": {}
    }

    for variant in variants:
        per_firm = []
        usage = Usage()
        unparse = offsch = 0
        t0 = time.time()

        for firm in firms:
            truth = firm.label_index()
            provider = build_provider(args, lambda: truth)
            r = run_firm(provider, firm, rb.obligations, variant=variant,
                         batch_size=args.batch, keep_raw=args.keep_raw)
            usage.add(r.usage)
            unparse += r.n_unparseable
            offsch += r.n_off_schema
            s = score(firm.labels, r.predictions, rule_regimes=regimes)
            per_firm.append({
                "firm_id": firm.firm_id,
                "n_pairs": r.n_pairs,
                "n_parsed": r.n_parsed,
                "n_unparseable": r.n_unparseable,
                "n_off_schema": r.n_off_schema,
                "false_green_rate": s.false_green_rate,
                "n_false_green": s.n_false_green,
                "n_withheld": s.n_withheld,
                "violation_recall": s.violation_recall,
                "violation_precision": s.violation_precision,
                "false_alarm_rate": s.false_alarm_rate,
                "abstention_precision": s.abstention_precision,
                "abstention_recall": s.abstention_recall,
                "abstention_f1": s.abstention_f1,
                "n_missing": s.n_missing,
                "per_regime": s.per_regime,
            })
            if args.keep_raw:
                raw_dir = ROOT / "docs" / "raw" / f"{args.model}__{variant}"
                raw_dir.mkdir(parents=True, exist_ok=True)
                (raw_dir / f"{firm.firm_id}.txt").write_text("\n\n---\n\n".join(r.raw))
            print(f"  {firm.firm_id:<22} FGR {s.false_green_rate:.3f}  "
                  f"recall {s.violation_recall:.3f}  unparsed {r.n_unparseable}")

        def agg(key: str) -> dict:
            xs = [f[key] for f in per_firm]
            return {
                "mean": round(statistics.mean(xs), 4),
                "stdev": round(statistics.stdev(xs), 4) if len(xs) > 1 else 0.0,
                "min": round(min(xs), 4),
                "max": round(max(xs), 4),
                "n_firms": len(xs),
            }

        key = f"{args.model}::{variant}"
        doc["runs"][key] = {
            "model": args.model,
            "provider": args.provider,
            "variant": variant,
            "prompt_version": PROMPT_VERSION,
            "batch_size": args.batch,
            "n_firms": len(firms),
            "n_pairs": sum(f["n_pairs"] for f in per_firm),
            "n_unparseable": unparse,
            "n_off_schema": offsch,
            "usage": {
                "input_tokens": usage.input_tokens,
                "output_tokens": usage.output_tokens,
                "calls": usage.calls,
                "wall_seconds": round(time.time() - t0, 1),
            },
            "aggregate": {
                k: agg(k) for k in (
                    "false_green_rate", "violation_recall", "violation_precision",
                    "false_alarm_rate", "abstention_precision", "abstention_recall",
                    "abstention_f1",
                )
            },
            "per_firm": per_firm,
        }

        a = doc["runs"][key]["aggregate"]
        print(f"\n{key}")
        print(f"  false green      {a['false_green_rate']['mean']:.3f} "
              f"(sd {a['false_green_rate']['stdev']:.3f})")
        print(f"  violation recall {a['violation_recall']['mean']:.3f} "
              f"(sd {a['violation_recall']['stdev']:.3f})")
        print(f"  false alarm      {a['false_alarm_rate']['mean']:.3f}")
        print(f"  abstention F1    {a['abstention_f1']['mean']:.3f}")
        print(f"  unparseable      {unparse} / {doc['runs'][key]['n_pairs']}")
        if variant == ABSTAIN_WITHHELD:
            print(f"  off-schema       {offsch} (abstained despite schema forbidding it)")

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(doc, indent=2))
    print(f"\nwrote {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
