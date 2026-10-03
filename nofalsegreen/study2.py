"""Study 2: language models on generated firms. Declared 2026-10-03, before any call.

WHY. Study 1 (the anchor firm) has no conforming pairs, so false alarms and
near-miss controls were unmeasurable, and it is one firm, so no between-firm
variance. Study 2 evaluates the same protocol (prompt v1.1.0, batch 12, scoped
sources, both output schemas) on five generated firms whose labels are fixed by
construction and which carry planted controls, a quarter of them near-miss.

THE SUBSET, fixed here and frozen to data/study2/subset.json:
  firms     generator seeds 1-5, GeneratorConfig(n_workers=12) defaults
  per firm  12 planted violations, 12 near-miss controls, 12 other controls,
            36 withheld-evidence pairs = 72 pairs = 6 calls per run
  sampling  seeded uniform within each stratum (SEED below), sorted by pair id

  The withheld share (36 of 72) is close to the released set's 45.3%, and the
  violation:control:withheld mix is fixed so a per-firm mean is comparable
  across firms. Strata are sampled without looking at any model output; no
  model has seen a generated firm under prompt v1.1.0.

MODELS. The five Study 1 models whose hosts completed runs normally: Nemotron 3
Ultra 550B, Nemotron 3 Super 120B, Laguna XS 2.1, Qwen 3.8 27B, dots.3 Note
Preview. Nemotron 3.5 Lightning is excluded IN ADVANCE because its free host
cut off most replies in Study 1 (coverage 92 and 68 of 140), which would make
its Study 2 rows measure the host. Any model added later (for example through
a free researcher programme) is reported in a separately labelled block.

REPORTING. Per-firm metrics, then mean and standard deviation across the five
firms; false-alarm rate on all controls and separately on near-miss controls;
evidence-pointer accuracy (generated labels record the evidence fields);
coverage and answered-only false-green rate as in Study 1.
"""

from __future__ import annotations

import json
import random
from dataclasses import replace
from pathlib import Path

from .generator import FirmGenerator, GeneratorConfig
from .rulebook import Rulebook
from .schema import Firm

DECLARED_ON = "2026-10-03"
SEEDS = (1, 2, 3, 4, 5)
SEED = 20261003
PER_STRATUM = {"fail": 12, "near_miss": 12, "control": 12, "withheld": 36}
MODELS = (
    "nvidia/nemotron-3-ultra-550b-a55b:free",
    "nvidia/nemotron-3-super-120b-a12b:free",
    "poolside/laguna-xs-2.1:free",
    "qwen/qwen3.8-27b:free",
    "dots-studio/dots-3-note-preview:free",
)

ROOT = Path(__file__).resolve().parent.parent
DIR = ROOT / "data" / "study2"
FROZEN = DIR / "subset.json"


def _stratum(label) -> str | None:
    v = label.verdict.value
    if v == "fail":
        return "fail"
    if v == "needs_evidence":
        return "withheld"
    if v == "pass":
        return "near_miss" if "near-miss" in (label.note or "") else "control"
    return None  # unmonitored: not part of Study 2


def generate(seed: int, rb: Rulebook) -> Firm:
    return FirmGenerator(rb, GeneratorConfig(n_workers=12)).generate(seed, DIR / f"firm_s{seed}")


def select(firm: Firm, seed: int) -> list[str]:
    rng = random.Random(SEED * 100 + seed)
    pools: dict[str, list[str]] = {k: [] for k in PER_STRATUM}
    for lab in firm.labels:
        s = _stratum(lab)
        if s:
            pools[s].append(lab.pair_id)
    chosen: list[str] = []
    for s, n in PER_STRATUM.items():
        pool = sorted(pools[s])
        if len(pool) < n:
            raise ValueError(f"seed {seed}: only {len(pool)} {s} pairs, need {n}")
        chosen.extend(rng.sample(pool, n))
    return sorted(chosen)


def freeze(rb: Rulebook) -> dict:
    doc = {"declared_on": DECLARED_ON, "seed": SEED, "per_stratum": PER_STRATUM, "firms": {}}
    for s in SEEDS:
        doc["firms"][str(s)] = select(generate(s, rb), s)
    DIR.mkdir(parents=True, exist_ok=True)
    FROZEN.write_text(json.dumps(doc, indent=2))
    return doc


def load_firms(rb: Rulebook) -> list[Firm]:
    """The five Study 2 firms restricted to their frozen subsets."""
    doc = json.loads(FROZEN.read_text())
    out = []
    for s in SEEDS:
        firm = generate(s, rb)
        keep = set(doc["firms"][str(s)])
        out.append(replace(
            firm,
            firm_id=f"{firm.firm_id}-study2",
            pairs=[p for p in firm.pairs if p.pair_id in keep],
            labels=[l for l in firm.labels if l.pair_id in keep],
        ))
    return out


if __name__ == "__main__":
    rb = Rulebook.load(ROOT / "rulebook" / "rulebook.json")
    d = freeze(rb)
    print({k: len(v) for k, v in d["firms"].items()})
