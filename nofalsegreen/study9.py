"""Study 9: evidence sufficiency under explicit decision contracts.

DECLARED 2026-10-07, before any Study 9 call (docs/STUDY9_DECLARATION.md).

Three workflows (workforce, purchasing, engineering), labels certified by compatible
completions (nofalsegreen/contracts.py) and re-checked by an independently written checker
(labelcheck/contract_checker.py).

  Part A  authority x familiarity x menu. Six packets per workflow, twelve entities each;
          entities alternate between `complete` (every authoritative fact present) and
          `proxy_only` (one authoritative fact removed while the reassuring proxy columns
          stay). Each packet is rendered with familiar or neutral table and column names
          (values identical) and asked under the offered or forced menu.
  Part B  harder packets and an intervention. Six packets per workflow, sixteen entities,
          two of each of the eight missingness patterns; familiar names; asked with the
          offered prompt, the evidence-first prompt, or the extraction prompt whose facts a
          deterministic solver turns into verdicts.
"""

from __future__ import annotations

from pathlib import Path

from . import contracts as C
from .schema import Entity, Firm, Label, Obligation, Pair, Verdict

DECLARED_ON = "2026-10-07"
WORKFLOWS = ("workforce", "purchasing", "engineering")
ROOT = Path(__file__).resolve().parent.parent
DIR = ROOT / "data" / "study9"
A_SEEDS, B_SEEDS = range(1, 7), range(101, 107)
A_N, B_N = 12, 16


def packet(part: str, wf: str, seed: int) -> C.Packet:
    if part == "A":
        return C.make_packet(wf, seed, A_N, lambda i, r: "complete" if i % 2 == 0 else "proxy_only")
    return C.make_packet(wf, seed, B_N, lambda i, r: C.PATTERNS[i % len(C.PATTERNS)])


def obligations(wf: str, familiar: bool) -> list[Obligation]:
    nm = C.names_for(wf, familiar)
    return [Obligation(rule_id=c.rule_id, regime="contract", citation="stated decision rule",
                       summary=c.predicate_text, applies_to="entity", evidence_required=(),
                       data_needed=c.statement(nm)) for c in C.RULES[wf]]


def all_obligations() -> list[Obligation]:
    return [o for wf in WORKFLOWS for fam in (True, False) for o in obligations(wf, fam)]


def firm(part: str, wf: str, seed: int, familiar: bool) -> Firm:
    p = packet(part, wf, seed)
    d = DIR / part / wf / ("familiar" if familiar else "neutral") / f"s{seed}"
    sources = C.write_packet(p, d, familiar)
    C.write_canonical(p, DIR / part / wf / "canonical" / f"s{seed}")
    pairs = [Pair.make(c.rule_id, e) for c in C.RULES[wf] for e in p.entities]
    labels = [Label(pair_id=pr.pair_id, verdict=Verdict(p.labels[pr.pair_id].label),
                    basis=p.labels[pr.pair_id].kind) for pr in pairs]
    return Firm(firm_id=f"study9-{part}-{wf}-{'fam' if familiar else 'neu'}-s{seed}", name=f"Case file {wf}-{seed}",
                as_of="2026-10-07", sources=sources, entities=[Entity(e, "entity", e) for e in p.entities],
                pairs=pairs, labels=labels,
                provenance={"seed": seed, "workflow": wf, "part": part, "familiar": familiar, "header": "Case file"})


def load_firms(spec: str) -> list[Firm]:
    """spec = 'A:<workflow>:<familiar|neutral>' or 'B:<workflow>'."""
    parts = spec.split(":")
    part, wf = parts[0], parts[1]
    fam = part == "B" or parts[2] == "familiar"
    seeds = A_SEEDS if part == "A" else B_SEEDS
    return [firm(part, wf, s, fam) for s in seeds]
