"""Estimate the token cost of the full language-model sweep before spending
anything. Builds every prompt that would be sent and counts it. No API calls.

    python3 scripts/cost_probe.py --firms 30 --batch 40
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from baselines.llm import estimate_cost  # noqa: E402
from nofalsegreen import northwind  # noqa: E402
from nofalsegreen.generator import FirmGenerator, GeneratorConfig  # noqa: E402
from nofalsegreen.rulebook import Rulebook  # noqa: E402

ANCHOR = ROOT / "data" / "firms" / "northwind-robotics"

# Published list prices per million tokens, for arithmetic only. Verify before
# relying on any figure here; these move.
PRICES = {
    "frontier-large": (15.00, 75.00),
    "frontier-mid": (3.00, 15.00),
    "frontier-small": (0.80, 4.00),
}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--firms", type=int, default=30)
    ap.add_argument("--batch", type=int, default=40)
    ap.add_argument("--workers", type=int, default=12)
    ap.add_argument("--models", type=int, default=10, help="models in the planned sweep")
    args = ap.parse_args()

    rb = Rulebook.load(ROOT / "rulebook" / "rulebook.json")
    gen = FirmGenerator(rb, GeneratorConfig(n_workers=args.workers))
    scratch = ROOT / ".cost-tmp"

    firms = [northwind.load(ANCHOR, ANCHOR / "expectations.json")]
    for seed in range(1, args.firms + 1):
        firms.append(gen.generate(seed, scratch / f"s{seed}"))

    tot_in = tot_out = tot_batches = tot_pairs = 0
    print(f"{'firm':<22}{'pairs':>7}{'batches':>9}{'in-tok':>12}{'out-tok':>10}")
    print("-" * 60)
    for f in firms:
        e = estimate_cost(f, rb.obligations, batch_size=args.batch)
        tot_in += e["est_input_tokens"]
        tot_out += e["est_output_tokens"]
        tot_batches += e["n_batches"]
        tot_pairs += e["n_pairs"]
        if f.firm_id == "northwind-robotics" or f.firm_id.endswith(("000001", "000002")):
            print(f"{f.firm_id:<22}{e['n_pairs']:>7}{e['n_batches']:>9}"
                  f"{e['est_input_tokens']:>12,}{e['est_output_tokens']:>10,}")
    print(f"{'... ' + str(len(firms)) + ' firms total':<22}{tot_pairs:>7}{tot_batches:>9}"
          f"{tot_in:>12,}{tot_out:>10,}")

    print(f"\nPER MODEL, PER VARIANT ({len(firms)} firms, batch={args.batch}):")
    print(f"  api calls        {tot_batches:,}")
    print(f"  input tokens     {tot_in:,}")
    print(f"  output tokens    {tot_out:,}")
    print("\n  cost at list prices (uncached, verify prices before relying on these):")
    for tier, (pin, pout) in PRICES.items():
        c = tot_in / 1e6 * pin + tot_out / 1e6 * pout
        print(f"    {tier:<16} ${c:,.2f}")

    variants = 2  # abstain_offered + abstain_withheld
    print(f"\nFULL SWEEP ({args.models} models x {variants} variants):")
    for tier, (pin, pout) in PRICES.items():
        c = (tot_in / 1e6 * pin + tot_out / 1e6 * pout) * args.models * variants
        print(f"    all-{tier:<12} ${c:,.2f}")

    anchor = estimate_cost(firms[0], rb.obligations, batch_size=args.batch)
    print("\nANCHOR FIRM ONLY (recommended first run, 1 model, 1 variant):")
    print(f"  {anchor['n_batches']} calls, {anchor['est_input_tokens']:,} in / "
          f"{anchor['est_output_tokens']:,} out")
    for tier, (pin, pout) in PRICES.items():
        c = anchor["est_input_tokens"] / 1e6 * pin + anchor["est_output_tokens"] / 1e6 * pout
        print(f"    {tier:<16} ${c:,.4f}")

    print("\nNote: prompt caching on the sources+rulebook prefix should cut input")
    print("cost substantially, since every batch of a firm re-sends the same prefix.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
