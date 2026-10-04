"""Study 3: confirmatory replication with planted adjacent columns.

DECLARED 2026-10-03, before any Study 3 call. The full declaration, with the
hypotheses, the analysis and the decision rule, is docs/STUDY3_PREREGISTRATION.md;
this module fixes the firms and models it names.

WHY. Two findings of the paper were formed after seeing results: that the
dashboard schema's effect splits into an abstention effect and a definition
effect, and that false greens arise by adjacent-field substitution (a populated
column standing in for the missing evidence beside it). Study 2 could not test
the second, because generator v2 never renders an adjacent column. Study 3
tests both on fresh firms, with a generator that plants adjacent columns
(generator v3, `decoys=True`), and on models from four developers besides
Google.

FIRMS. The first twelve seeds counting up from 1001 that satisfy the Study 2
rule (the firm withholds at least one export AND leaves at least one rule
family decidable), applied mechanically to label counts before any call. Seeds
1-15 (Study 2) and 101-110 (the blind label check) are therefore excluded.
Each seed is rendered twice: arm `decoy` (v3, adjacent columns) and arm
`plain` (v2). The two renderings have identical workers, labels and exports
apart from the five roster columns, so the arms are paired.

MODELS. The three Vertex block models, and four open-weights models from other
developers served on Vertex AI, chosen before any Study 3 call from those that
answered a one-word availability probe (no benchmark data was sent).
"""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path

from .generator import NEEDS, FirmGenerator, GeneratorConfig
from .rulebook import Rulebook
from .schema import Firm

DECLARED_ON = "2026-10-03"
FIRST_SEED = 1001
N_FIRMS = 12
ARMS = ("decoy", "plain")
CONDITIONS = ("abstain_offered", "abstain_removed_only", "abstain_closed", "abstain_withheld")

GOOGLE_MODELS = ("gemini-3.1-pro-preview", "gemini-3.8-flash", "gemma-4-26b-a4b-it-maas")
# Vertex publisher id -> served location.
OPEN_MODELS = {
    "openai/gpt-oss-120b-maas": "us-central1",
    "deepseek-ai/deepseek-v3.2-maas": "global",
    "qwen/qwen3-235b-a22b-instruct-2507-maas": "global",
    "moonshotai/kimi-k2-thinking-maas": "global",
}
# Served output limits below the protocol's 32,000-token cap. The request is
# clamped to the limit; a reply that reaches it ends with finish_reason
# "length" and is treated as reaching the cap.
OUTPUT_LIMITS = {"qwen/qwen3-235b-a22b-instruct-2507-maas": 16_384}

ROOT = Path(__file__).resolve().parent.parent
DIR = ROOT / "data" / "study3"


def eligible(firm: Firm) -> bool:
    withheld = set(firm.provenance["withheld_exports"])
    decidable = [r for r, srcs in NEEDS.items() if not any(s in withheld for s in srcs)]
    return bool(withheld) and bool(decidable)


def seeds(rb: Rulebook) -> list[int]:
    import tempfile
    gen, out, s = FirmGenerator(rb, GeneratorConfig()), [], FIRST_SEED
    tmp = Path(tempfile.mkdtemp())
    while len(out) < N_FIRMS:
        f = gen.generate(s, tmp / str(s))
        if eligible(f):
            out.append(s)
        s += 1
    return out


SEEDS = (1001, 1002, 1003, 1008, 1010, 1014, 1017, 1018, 1020, 1021, 1024, 1027)  # = seeds(rb)


def load_firms(rb: Rulebook, arm: str) -> list[Firm]:
    if arm not in ARMS:
        raise ValueError(arm)
    gen = FirmGenerator(rb, GeneratorConfig(decoys=(arm == "decoy")))
    out = []
    for s in SEEDS:
        d = DIR / arm / f"s{s}"
        firm = gen.generate(s, d)
        sources = {k: (v if Path(v).is_absolute() else d / v) for k, v in firm.sources.items()}
        out.append(replace(firm, sources=sources, firm_id=f"{firm.firm_id}-study3-{arm}"))
    return out


if __name__ == "__main__":
    from collections import Counter
    rb = Rulebook.load(ROOT / "rulebook" / "rulebook.json")
    print("seed rule gives:", seeds(rb), "declared:", list(SEEDS))
    for arm in ARMS:
        tot: Counter = Counter()
        for f in load_firms(rb, arm):
            tot += Counter(l.verdict.value for l in f.labels)
        print(arm, dict(tot))
