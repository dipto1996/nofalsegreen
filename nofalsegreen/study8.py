"""Study 8: fresh firms and repeat runs for the core effects; two wage controls.

DECLARED 2026-10-07, before any Study 8 call (docs/STUDY8_DECLARATION.md).

A review noted that Study 6 reused the Study 3c firms without repeat runs, that the
Study 5 salary value duplicated the LCA's offered wage, and that the complete arm made
the greater-of rule trivial (actual wage = offered wage). Study 8:
  (a) draws ten fresh firms that withhold the I-9 export (seeds from 3001, the Study 3c
      rule applied mechanically) and renders them plain, with proxy columns, with
      irrelevant columns and with renamed proxy values; five models, two runs each;
  (b) adds two arms to the Study 5 real-LCA firms (nofalsegreen/study5.py):
      pay_rate_shifted       Pay Rate alone, set 7% above the LCA's offered wage
      complete_actual_above  complete records whose actual wage exceeds the offered wage,
                             so some underpayments are visible only under the greater-of rule
"""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path

from .generator import FirmGenerator, GeneratorConfig
from .rulebook import Rulebook
from .schema import Firm

DECLARED_ON = "2026-10-07"
SEEDS = (3011, 3014, 3019, 3025, 3027, 3030, 3038, 3046, 3047, 3060)  # first ten from 3001 (study3c rule)
ARMS = {
    "plain": GeneratorConfig(),
    "proxy": GeneratorConfig(decoys=True),
    "irrelevant": GeneratorConfig(decoys=True, decoy_style="irrelevant"),
    "renamed": GeneratorConfig(decoys=True, decoy_style="renamed"),
}
ROOT = Path(__file__).resolve().parent.parent
DIR = ROOT / "data" / "study8"


def load_firms(rb: Rulebook, arm: str) -> list[Firm]:
    gen = FirmGenerator(rb, ARMS[arm])
    out = []
    for s in SEEDS:
        d = DIR / arm / f"s{s}"
        firm = gen.generate(s, d)
        sources = {k: (v if Path(v).is_absolute() else d / v) for k, v in firm.sources.items()}
        out.append(replace(firm, sources=sources, firm_id=f"{firm.firm_id}-study8-{arm}"))
    return out
