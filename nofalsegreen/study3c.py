"""Study 3c: proxy columns on firms that withhold the I-9 export, and one column at a time.

DECLARED 2026-10-04, before any Study 3c call (docs/STUDY3C_DECLARATION.md).

WHY. In Study 3 the proxy-column effect is mostly an I-9 effect, and the I-9
pairs come from only three firms. A reviewer also asked which proxy column does
the work, since replies never cite the I-9 status column. Study 3c draws ten
fresh firms that all withhold the I-9 export and renders each five ways: plain,
all five proxy columns, and each of the three I-9 proxy columns alone.

FIRMS. The first ten seeds from 2001 upward whose firm withholds the I-9 export
and leaves at least one rule family decidable (the Study 2/3 eligibility rule
plus the I-9 condition), applied mechanically before any call.
"""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path

from .generator import FirmGenerator, GeneratorConfig
from .rulebook import Rulebook
from .schema import Firm
from .study3 import eligible

DECLARED_ON = "2026-10-04"
FIRST_SEED, N_FIRMS = 2001, 10
ARMS = {
    "plain": GeneratorConfig(),
    "proxy": GeneratorConfig(decoys=True),
    "only_i9Status": GeneratorConfig(decoys=True, decoy_columns=("i9Status",)),
    "only_onboardingCompletedDate": GeneratorConfig(decoys=True, decoy_columns=("onboardingCompletedDate",)),
    "only_workAuthValidThrough": GeneratorConfig(decoys=True, decoy_columns=("workAuthValidThrough",)),
}
# (arm, condition) cells run: every arm under the dashboard schema; plain and
# proxy also under the offered schema.
CELLS = [(a, "abstain_withheld") for a in ARMS] + [("plain", "abstain_offered"), ("proxy", "abstain_offered")]
MODELS = ("gemini-3.1-pro-preview", "gemini-3.8-flash", "gemma-4-26b-a4b-it-maas")

ROOT = Path(__file__).resolve().parent.parent
DIR = ROOT / "data" / "study3c"


def seeds(rb: Rulebook) -> list[int]:
    import tempfile
    gen, out, s = FirmGenerator(rb, GeneratorConfig()), [], FIRST_SEED
    tmp = Path(tempfile.mkdtemp())
    while len(out) < N_FIRMS:
        f = gen.generate(s, tmp / str(s))
        if eligible(f) and "i9" in f.provenance["withheld_exports"]:
            out.append(s)
        s += 1
    return out


SEEDS = (2003, 2007, 2009, 2023, 2026, 2037, 2040, 2041, 2048, 2069)  # = seeds(rb)


def load_firms(rb: Rulebook, arm: str) -> list[Firm]:
    gen = FirmGenerator(rb, ARMS[arm])
    out = []
    for s in SEEDS:
        d = DIR / arm / f"s{s}"
        firm = gen.generate(s, d)
        sources = {k: (v if Path(v).is_absolute() else d / v) for k, v in firm.sources.items()}
        out.append(replace(firm, sources=sources, firm_id=f"{firm.firm_id}-study3c-{arm}"))
    return out
