"""A declared evaluation subset of the anchor firm.

WHY THIS EXISTS. Evaluating all 221 anchor pairs costs 28 API calls per model
per ablation condition. On a free tier capped at 50 calls a day, a single model
consumes more than half a day's quota and a six-model, two-condition study takes
a week of wall-clock. The subset makes the study runnable without spend.

WHAT IT IS NOT. It is not "the first N pairs" and it is not chosen after seeing
results. It is a deterministic stratified sample fixed by a seed declared here,
built to preserve the properties the benchmark's claims depend on:

  1. EVERY planted violation is included. Violation recall over the subset is
     therefore recall over the firm's full violation set, not a sample of it.
  2. The class ratio is preserved. The full firm carries about 10 evidence
     requests per violation, and the subset holds that ratio rather than letting
     it drift: a subset with proportionally fewer abstention pairs would make the
     task easier than the firm it claims to represent, and would flatter any
     false-green rate measured on it.
  3. Every regulatory regime present in the firm keeps at least one pair, so the
     per-regime table in the paper is not silently missing rows.
  4. Selection is seeded and reproducible: same seed, same subset, forever.

WHAT IS LOST. A smaller denominator on the false-green rate, so its confidence
interval is wider. The paper reports subset size alongside every subset result
and does not present a subset rate as if it were the full-firm rate. Any model
that can be afforded on the full firm is run on the full firm and reported
separately.
"""

from __future__ import annotations

import json
import random
from collections import defaultdict
from pathlib import Path

from .schema import Firm, Pair, Verdict

# The declared subset of the anchor firm, frozen to a file. Selection depends on
# each rule's regime, and rulebook v2 assigned real regimes to 30 pairs that v1
# had bucketed as "unknown"; re-selecting under v2 would silently pick different
# pairs. Freezing keeps every prompt version evaluated on the identical 140
# pairs, so a difference between versions is attributable to the prompt alone.
FROZEN_ANCHOR_SUBSET = (
    Path(__file__).resolve().parent.parent
    / "data" / "firms" / "northwind-robotics" / "subset140.json"
)

# Fixed before any model was scored. Changing it changes the benchmark.
SUBSET_SEED = 20260921
# 140 keeps all 20 violations plus 120 evidence requests: a 6:1 abstention
# majority, every regime represented, and 12 calls at batch 12 -- so four
# model-condition runs fit inside a 50-call day.
DEFAULT_SIZE = 140

# Evidence requests per planted violation in the full anchor firm (201/20). The
# subset holds this ratio, so `size` sets the violation count and the abstention
# count follows.
TARGET_NE_PER_FAIL = 201 / 20


def stratified_subset(
    firm: Firm,
    rule_regimes: dict[str, str],
    *,
    size: int = DEFAULT_SIZE,
    seed: int = SUBSET_SEED,
) -> list[Pair]:
    """Return a reproducible subset of `firm`'s pairs.

    All planted violations are kept. The remaining budget is spent on
    needs_evidence pairs, allocated across regimes proportionally to their share
    of the firm, with at least one pair per regime that has any.
    """
    rng = random.Random(seed)
    labels = firm.label_index()

    fails: list[Pair] = []
    ne_by_regime: dict[str, list[Pair]] = defaultdict(list)
    for p in firm.pairs:
        lab = labels.get(p.pair_id)
        if lab is None:
            continue
        if lab.verdict is Verdict.FAIL:
            fails.append(p)
        else:
            regime = rule_regimes.get(p.rule_id, "unknown")
            ne_by_regime[regime].append(p)

    # Hold the full firm's class ratio. Taking `size - len(fails)` abstention
    # pairs instead would shrink the abstention share and make the subset an
    # easier task than the firm.
    ratio_budget = round(len(fails) * TARGET_NE_PER_FAIL)
    budget = max(0, min(size - len(fails), ratio_budget))
    total_ne = sum(len(v) for v in ne_by_regime.values())
    if total_ne == 0 or budget == 0:
        return sorted(fails, key=lambda p: p.pair_id)

    # Floor of one per regime, then proportional allocation of what remains.
    regimes = sorted(ne_by_regime)
    alloc = {r: 1 for r in regimes if ne_by_regime[r]}
    remaining = budget - sum(alloc.values())
    if remaining > 0:
        for r in regimes:
            share = len(ne_by_regime[r]) / total_ne
            alloc[r] += int(remaining * share)

    # Hand any rounding remainder to the largest regimes, deterministically.
    shortfall = budget - sum(alloc.values())
    for r in sorted(regimes, key=lambda x: -len(ne_by_regime[x]))[: max(0, shortfall)]:
        alloc[r] += 1

    chosen: list[Pair] = list(fails)
    for r in regimes:
        pool = sorted(ne_by_regime[r], key=lambda p: p.pair_id)
        n = min(alloc.get(r, 0), len(pool))
        chosen.extend(rng.sample(pool, n) if n < len(pool) else pool)

    return sorted(chosen, key=lambda p: p.pair_id)


def subset_firm(
    firm: Firm, rule_regimes: dict[str, str], *, size: int = DEFAULT_SIZE
) -> Firm:
    """A copy of `firm` restricted to the declared subset, labels included."""
    frozen = None
    if (firm.firm_id == "northwind-robotics" and size == DEFAULT_SIZE
            and FROZEN_ANCHOR_SUBSET.exists()):
        frozen = set(json.loads(FROZEN_ANCHOR_SUBSET.read_text())["pair_ids"])
    if frozen is not None:
        pairs = sorted((p for p in firm.pairs if p.pair_id in frozen), key=lambda p: p.pair_id)
        if len(pairs) != len(frozen):
            raise ValueError(
                f"frozen subset names {len(frozen)} pairs but only {len(pairs)} exist in "
                f"the firm; the expectation set has drifted from the frozen subset"
            )
    else:
        pairs = stratified_subset(firm, rule_regimes, size=size)
    keep = {p.pair_id for p in pairs}
    entity_ids = {p.entity_id for p in pairs}
    return Firm(
        firm_id=f"{firm.firm_id}-subset{len(pairs)}",
        name=firm.name,
        as_of=firm.as_of,
        sources=firm.sources,
        entities=[e for e in firm.entities if e.entity_id in entity_ids],
        pairs=pairs,
        labels=[l for l in firm.labels if l.pair_id in keep],
        provenance={
            **firm.provenance,
            "subset_of": firm.firm_id,
            "subset_seed": SUBSET_SEED,
            "subset_size": len(pairs),
            "parent_pairs": len(firm.pairs),
        },
    )
