"""Rulebook loading.

The rulebook is a set of citable obligations. Each carries the regulatory
citation it is derived from and the list of source fields that must be present
for the obligation to be *decidable*. That second field is what makes
NEEDS_EVIDENCE a computable label rather than a judgement call: if a required
field is absent from the firm's exports, the pair is not decidable, full stop.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from .schema import Obligation

# Which entity type each regime's obligations attach to. Obligations that
# attach to the employer as a whole are scope-level: one finding per firm.
_APPLIES_TO = {
    "i9-everify": "worker",
    "f1-opt-stem": "worker",
    "h1b-status": "worker",
    "deadlines-penalties": "worker",
    "l1-visa": "worker",
    "lca-dol": "lca",
    "wage-prevailing": "lca",
    "paf": "lca",
    "i129-supplement": "lca",
    "fdns-sitevisit": "employer",
}


@dataclass
class Rulebook:
    version: str
    source: str
    obligations: list[Obligation]

    def by_id(self) -> dict[str, Obligation]:
        return {o.rule_id: o for o in self.obligations}

    def regimes(self) -> dict[str, int]:
        out: dict[str, int] = {}
        for o in self.obligations:
            out[o.regime] = out.get(o.regime, 0) + 1
        return dict(sorted(out.items()))

    def rule_regimes(self) -> dict[str, str]:
        return {o.rule_id: o.regime for o in self.obligations}

    @classmethod
    def load(cls, path: Path | str) -> "Rulebook":
        doc = json.loads(Path(path).read_text())
        obs = [
            Obligation(
                rule_id=o["rule_id"],
                regime=o["regime"],
                citation=o["citation"],
                summary=o["summary"],
                applies_to=_APPLIES_TO.get(o["regime"], "worker"),
                evidence_required=tuple(o.get("evidence_required", ())),
            )
            for o in doc["obligations"]
        ]
        return cls(version=doc["version"], source=doc["source"], obligations=obs)
