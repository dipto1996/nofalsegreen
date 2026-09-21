"""Loader for the hand-authored firm (`northwind-robotics`).

This firm is the benchmark's anchor instance. Unlike generated firms, its
violations were planted by hand against a written test plan and its ground
truth was maintained through repeated correctness fixes to the reference
engine. Its labels come from that pinned expectation set.

The generated firms give the benchmark statistical power; this firm gives it
a case whose every finding a human authored and can defend.
"""

from __future__ import annotations

import json
from pathlib import Path

from .schema import Entity, Firm, Label, Pair, Severity, Verdict

_OUTCOME = {"fail": Verdict.FAIL, "needs_evidence": Verdict.NEEDS_EVIDENCE}
_SEVERITY = {"urgent": Severity.URGENT, "high": Severity.HIGH, "medium": Severity.MEDIUM}

_SOURCES = {
    "hris_roster_export": "bamboohr_active_employees.csv",
    "cms_case_export": "cms_h1b_cases_export.csv",
    "lca_export": "lca_certified_h1b_2024-2025.csv",
    "i9_record_export": "i9_records_export.csv",
    "everify_case_export": "everify_cases_2025.csv",
    "payroll_register": "gusto_payroll_register_2025-q2.csv",
    "rfe_noid_export": "rfe_noid_cases_export.csv",
    "h1b_cap_export": "h1b_cap_cases_export.csv",
    "greencard_case_export": "greencard_cases_export.csv",
    "perm_recruitment_export": "perm_recruitment_tracker.csv",
    "benefits_census_export": "benefits_census_2025.csv",
}


def _entity_type(match: str, match_on: str) -> str:
    if match_on == "owner":
        return "worker"
    if match.startswith("I-200-"):
        return "lca"
    if ":" in match and match.split(":")[0] in {"deadline-gap", "fdns-gap", "structural-gap", "wave-b-gap"}:
        return "employer"
    if match.count(":") >= 2:
        return "wage_cohort"
    return "employer"


def load(firm_dir: Path | str, expectations: Path | str) -> Firm:
    """Build the anchor firm from its CSVs plus the pinned expectation set."""
    firm_dir = Path(firm_dir)
    doc = json.loads(Path(expectations).read_text())
    items = doc["items"]

    entities: dict[str, Entity] = {}
    pairs: list[Pair] = []
    labels: list[Label] = []

    for it in items:
        match, match_on = it["match"], it["matchOn"]
        etype = _entity_type(match, match_on)
        entities.setdefault(match, Entity(entity_id=match, entity_type=etype, label=match))
        pair = Pair.make(it["ruleId"], match)
        pairs.append(pair)
        labels.append(
            Label(
                pair_id=pair.pair_id,
                verdict=_OUTCOME[it["outcome"]],
                basis="planted_violation" if it["outcome"] == "fail" else "withheld_evidence",
                severity=_SEVERITY[it["severity"]],
                note=it["label"],
            )
        )

    # Clean controls carry no finding. They are declared so a system that fires
    # on them is scored as a false alarm rather than silently unpenalised.
    for name in doc.get("clean_controls", []):
        entities.setdefault(name, Entity(name, "worker", name))

    sources = {
        kind: firm_dir / fname
        for kind, fname in _SOURCES.items()
        if (firm_dir / fname).exists()
    }

    return Firm(
        firm_id="northwind-robotics",
        name=doc["employer"],
        as_of=doc["asOf"],
        sources=sources,
        entities=list(entities.values()),
        pairs=pairs,
        labels=labels,
        provenance={
            "authoring": "hand-authored against a written test plan",
            "tenant": doc["tenant"],
            "n_expected": len(items),
            "synthetic": True,
            "contains_real_personal_data": False,
        },
    )
