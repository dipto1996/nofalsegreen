"""Core types for the No False Green benchmark.

A *task instance* is one firm: a bundle of source exports plus a rulebook.
A *pair* is one (obligation, entity) the system must return a verdict for.
A *verdict* is one of four states; `NEEDS_EVIDENCE` is the abstention.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from enum import Enum
from pathlib import Path


class Verdict(str, Enum):
    """The four states a system may return for an (obligation, entity) pair.

    PASS           the rule was evaluated against present evidence and is satisfied
    FAIL           the rule was evaluated against present evidence and is violated
    NEEDS_EVIDENCE the evidence required to decide is absent (the abstention)
    UNMONITORED    the obligation is not assessable from this class of source data
    """

    PASS = "pass"
    FAIL = "fail"
    NEEDS_EVIDENCE = "needs_evidence"
    UNMONITORED = "unmonitored"


class Severity(str, Enum):
    URGENT = "urgent"
    HIGH = "high"
    MEDIUM = "medium"


@dataclass(frozen=True)
class Entity:
    """A thing an obligation attaches to: a worker, an LCA, a worksite, a cohort."""

    entity_id: str
    entity_type: str  # worker | lca | worksite | wage_cohort | employer
    label: str


@dataclass(frozen=True)
class Obligation:
    """One citable duty from the rulebook."""

    rule_id: str
    regime: str
    citation: str
    summary: str  # the manifest's one-line "check"
    applies_to: str  # entity_type this rule attaches to
    evidence_required: tuple[str, ...]  # short items, for label annotation only
    requirement: str = ""
    threshold: str = ""
    data_needed: str = ""  # verbatim manifest prose; this is what the prompt shows
    needs_counsel: bool = False
    alias_of: str | None = None  # manifest id, when this is an engine alias
    source: str = "manifest"  # manifest | engine_alias | engine_rollup


@dataclass(frozen=True)
class Pair:
    """One unit of prediction."""

    pair_id: str
    rule_id: str
    entity_id: str

    @staticmethod
    def make(rule_id: str, entity_id: str) -> "Pair":
        return Pair(pair_id=f"{rule_id}::{entity_id}", rule_id=rule_id, entity_id=entity_id)


@dataclass(frozen=True)
class Label:
    """Ground truth for one pair, fixed by construction.

    `basis` records WHY this is the label, which is what makes the set auditable:
      planted_violation  the generator injected a specific regulatory breach
      planted_control    the generator injected a conforming case
      withheld_evidence  the generator omitted a required input
      not_applicable     the rule does not attach to this entity
    """

    pair_id: str
    verdict: Verdict
    basis: str
    severity: Severity | None = None
    evidence_fields: tuple[str, ...] = ()
    note: str = ""


@dataclass
class Prediction:
    """What a system under evaluation returns for one pair."""

    pair_id: str
    verdict: Verdict
    evidence_fields: tuple[str, ...] = ()
    citation: str | None = None
    rationale: str = ""


@dataclass
class Firm:
    """One task instance."""

    firm_id: str
    name: str
    as_of: str  # ISO date; all date-relative rules evaluate against this pin
    sources: dict[str, Path]  # source_kind -> csv path
    entities: list[Entity] = field(default_factory=list)
    pairs: list[Pair] = field(default_factory=list)
    labels: list[Label] = field(default_factory=list)
    provenance: dict = field(default_factory=dict)

    def label_index(self) -> dict[str, Label]:
        return {l.pair_id: l for l in self.labels}

    def to_json(self) -> str:
        d = asdict(self)
        d["sources"] = {k: str(v) for k, v in self.sources.items()}
        return json.dumps(d, indent=2, default=str)
