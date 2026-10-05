"""Study 4: controls for the proxy-column mechanism, a schema factorial, an
evidence-gating prompt, and repeat runs, on the Study 3c firms.

DECLARED 2026-10-05, before any Study 4 call (docs/STUDY4_DECLARATION.md).

The plain and proxy firms are the Study 3c firms themselves (same directories,
same firm ids), so Study 3c replies to the original schemas are reused. The
control arms are new renderings of the same ten seeds; each is paired with the
plain firm of its seed because the roster columns come from a separate random
stream and no label depends on them.
"""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path

from .generator import FirmGenerator, GeneratorConfig
from .rulebook import Rulebook
from .schema import Firm
from . import study3c

DECLARED_ON = "2026-10-05"
SEEDS = study3c.SEEDS
MODELS = study3c.MODELS
CONTROL_ARMS = {
    "renamed": GeneratorConfig(decoys=True, decoy_style="renamed"),
    "irrelevant": GeneratorConfig(decoys=True, decoy_style="irrelevant"),
    "adverse": GeneratorConfig(decoys=True, decoy_style="adverse"),
}
ARMS = ("plain", "proxy", *CONTROL_ARMS)

ROOT = Path(__file__).resolve().parent.parent
DIR = ROOT / "data" / "study4"


def load_firms(rb: Rulebook, arm: str) -> list[Firm]:
    if arm in study3c.ARMS:
        return study3c.load_firms(rb, arm)
    gen = FirmGenerator(rb, CONTROL_ARMS[arm])
    out = []
    for s in SEEDS:
        d = DIR / arm / f"s{s}"
        firm = gen.generate(s, d)
        sources = {k: (v if Path(v).is_absolute() else d / v) for k, v in firm.sources.items()}
        out.append(replace(firm, sources=sources, firm_id=f"{firm.firm_id}-study4-{arm}"))
    return out
