"""Rulebook loading.

The rulebook is a set of citable obligations built from the source engine's
machine-readable manifest registry (196 entries, 194 unique rule ids). Each
carries its regulatory citation, the check it performs, its threshold, and a
verbatim description of the information needed to decide it.

`obligations` holds the 194 manifest rules and is what the firm generator draws
from. The anchor firm's expectation set also uses 17 engine rule ids that are
not manifest ids; those are resolvable through `by_id()` and `rule_regimes()`
but are kept out of `obligations`, so a generated firm never counts one duty
twice under two names.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
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


def _obligation(o: dict) -> Obligation:
    return Obligation(
        rule_id=o["rule_id"],
        regime=o["regime"],
        citation=o["citation"],
        summary=o.get("check") or o.get("summary", ""),
        applies_to=_APPLIES_TO.get(o["regime"], "worker"),
        evidence_required=tuple(o.get("evidence_required", ())),
        requirement=o.get("requirement", ""),
        threshold=o.get("threshold", ""),
        data_needed=o.get("data_needed", ""),
        needs_counsel=bool(o.get("needs_counsel", False)),
        alias_of=o.get("alias_of"),
        source=o.get("source", "manifest"),
    )


@dataclass
class Rulebook:
    version: str
    source: str
    obligations: list[Obligation]
    engine_rules: list[Obligation] = field(default_factory=list)

    def by_id(self) -> dict[str, Obligation]:
        """Every resolvable rule id: manifest rules plus engine aliases/roll-ups."""
        return {o.rule_id: o for o in [*self.obligations, *self.engine_rules]}

    def all_rules(self) -> list[Obligation]:
        return [*self.obligations, *self.engine_rules]

    def regimes(self) -> dict[str, int]:
        """Manifest rule count per regime."""
        out: dict[str, int] = {}
        for o in self.obligations:
            out[o.regime] = out.get(o.regime, 0) + 1
        return dict(sorted(out.items()))

    def rule_regimes(self) -> dict[str, str]:
        return {o.rule_id: o.regime for o in self.all_rules()}

    @classmethod
    def load(cls, path: Path | str) -> "Rulebook":
        doc = json.loads(Path(path).read_text())
        manifest, engine = [], []
        for o in doc["obligations"]:
            ob = _obligation(o)
            (manifest if ob.source == "manifest" else engine).append(ob)
        return cls(version=doc["version"], source=doc["source"],
                   obligations=manifest, engine_rules=engine)
