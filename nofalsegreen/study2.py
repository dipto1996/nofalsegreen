"""Study 2: language models on generated firms (generator v2).

DECLARED 2026-10-03, before any call on a v2 firm.

HISTORY. A first declaration of Study 2 (commit 1741f04) used generator v1.
A blind consistency check then showed v1's labels were not decidable from its
own records (8 of 60 agreed), so v1 was replaced (nofalsegreen/generator.py,
docstring). Two Study 2 calls made on v1 firms are archived unused in
docs/study2_v1_invalid/. A blind check of v2 agreed with its labels on 60 of 60
pairs (15 per stratum) on seeds 101-110, which are not used here.

WHY. Study 1 (the anchor firm) has no conforming pairs, so false alarms and
near-miss controls were unmeasurable, and it is one firm. Study 2 runs the same
protocol (prompt v1.1.0, batch 12, scoped sources, both output schemas) on six
generated firms, every pair of each firm, with labels fixed by construction.

FIRMS. Generator v2 with default GeneratorConfig. The firms are the first six
seeds, counting up from 1, whose firm withholds at least one export AND leaves
at least one rule family decidable, so every firm contributes both withheld
pairs and decidable pairs (a firm withholding everything, or nothing, cannot
measure the false-green rate against detection). The rule was applied
mechanically to label counts only, before any call: seeds 1, 2, 9, 13, 14, 15.
All pairs of each firm are evaluated; nothing is sampled.

MODELS. The five Study 1 models whose hosts completed runs normally: Nemotron 3
Ultra 550B, Nemotron 3 Super 120B, Laguna XS 2.1, Qwen 3.8 27B, dots.3 Note
Preview. Nemotron 3.5 Lightning is excluded in advance because its free host
cut off most replies in Study 1 (coverage 92 and 68 of 140).

REPORTING. Per-firm metrics, then mean and standard deviation across the six
firms; false-alarm rate on all controls and on near-miss controls separately;
coverage and answered-only false-green rate as in Study 1.
"""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path

from .generator import FirmGenerator, GeneratorConfig
from .rulebook import Rulebook
from .schema import Firm

DECLARED_ON = "2026-10-03"
SEEDS = (1, 2, 9, 13, 14, 15)
MODELS = (
    "nvidia/nemotron-3-ultra-550b-a55b:free",
    "nvidia/nemotron-3-super-120b-a12b:free",
    "poolside/laguna-xs-2.1:free",
    "qwen/qwen3.8-27b:free",
    "dots-studio/dots-3-note-preview:free",
)

ROOT = Path(__file__).resolve().parent.parent
DIR = ROOT / "data" / "study2"


def _stratum(label) -> str | None:
    v = label.verdict.value
    if v == "fail":
        return "fail"
    if v == "needs_evidence":
        return "withheld"
    if v == "pass":
        return "near_miss" if "near-miss" in (label.note or "") else "control"
    return None


def load_firms(rb: Rulebook) -> list[Firm]:
    """The six Study 2 firms, with export paths resolved so a prompt can never
    be built without its data."""
    out = []
    gen = FirmGenerator(rb, GeneratorConfig())
    for s in SEEDS:
        d = DIR / f"v2_s{s}"
        firm = gen.generate(s, d)
        sources = {k: (v if Path(v).is_absolute() else d / v) for k, v in firm.sources.items()}
        out.append(replace(firm, sources=sources, firm_id=f"{firm.firm_id}-v2-study2"))
    return out


if __name__ == "__main__":
    from collections import Counter
    rb = Rulebook.load(ROOT / "rulebook" / "rulebook.json")
    tot: Counter = Counter()
    for f in load_firms(rb):
        c = Counter(_stratum(l) for l in f.labels)
        tot += c
        print(f.firm_id, len(f.pairs), dict(c), "withheld exports:", f.provenance["withheld_exports"])
    print("total", sum(tot.values()), dict(tot))
