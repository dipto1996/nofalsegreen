"""Declared label views for scoring the anchor firm.

DECLARED 2026-09-24, BEFORE ANY PROMPT-v1.1 RESULT WAS READ. The git history of
this file is the evidence for that ordering. The views are fixed here; results
are computed under both and both are reported.

WHY TWO VIEWS. The anchor firm's labels were written as the acceptance gate for a
compliance engine, where `fail` means "requires action". This benchmark's `fail`
means "the records show a violation". Ten of the 20 planted violations sit
between those meanings:

  MEMO_ABSENCE (5 pairs). "Actual-wage memo missing." No export records that the
  memo is absent; the evidence simply is not there. Under this benchmark's own
  definition that is `needs_evidence`, not `fail`. Scoring a model's
  `needs_evidence` as a miss here would penalise exactly the behaviour the
  benchmark exists to reward.

  PROSPECTIVE (5 pairs). Deadlines that have not yet passed as of the pinned
  evaluation date: an LCA expiring in 4 days, a petition expiring in 21, an open
  extension window, and an RFE and a NOID not yet due. These are warnings. No
  duty has been breached, so neither `fail` nor `pass` is cleanly correct.

THE VIEWS.

  engine   The labels as authored. The HEADLINE view, because it is the label
           set that existed before this benchmark was built, so no choice made
           here can have tuned it.

  strict   MEMO_ABSENCE relabelled to `needs_evidence`. PROSPECTIVE removed from
           the scored set and reported separately as deadline alerts: for each,
           the verdict the model gave. The remaining 10 violations are breaches
           that had already happened on the evaluation date.

CAVEAT, stated up front because the view invites it. Strict-view violation
recall has a denominator of 10, so one pair moves it by 0.1. It is reported
beside the engine view and never alone.

Pairs are named by exact id, not selected by a rule, so the membership of each
group cannot drift if the expectation set is later edited.
"""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from dataclasses import replace

from .schema import Label, Prediction, Verdict

DECLARED_ON = "2026-09-24"

MEMO_ABSENCE: frozenset[str] = frozenset({
    "h1b.wage.actual.memo::17-2199:L3:Austin, TX:memo",
    "h1b.wage.actual.memo::wage:15-1252:L4:Austin, TX:memo",
    "h1b.wage.actual.memo::wage:17-2141:L3:Austin, TX:memo",
    "h1b.wage.actual.memo::wage:17-2061:L3:Austin, TX:memo",
    "h1b.wage.actual.memo::wage:15-1252:L2:Austin, TX:memo",
})

PROSPECTIVE: frozenset[str] = frozenset({
    "lca.expiration::I-200-22010-100004",
    "h1b.petition.expiry::Hiroshi Yamamoto",
    "extension.filing::Hiroshi Yamamoto",
    "h1b.rfe.response::Daniel Cho",
    "h1b.noid.response::Sofia Reyes",
})

VIEWS = ("engine", "strict", "audited")

# The audited view (docs/LABEL_AUDIT_PROTOCOL.md, declared 2026-10-01): withheld
# pairs a blind audit found to have every required item present in the exports
# are REMOVED from scoring, not relabelled. Absent the audit file the view is
# unavailable rather than silently equal to the engine view.
AUDIT_FILE = Path(__file__).resolve().parent.parent / "docs" / "label_audit.json"


def overturned() -> frozenset[str] | None:
    if not AUDIT_FILE.exists():
        return None
    doc = json.loads(AUDIT_FILE.read_text())
    return frozenset(pid for pid, a in doc["pairs"].items()
                     if a["decision"] == "evidence_present")


def apply_view(labels: list[Label], view: str) -> tuple[list[Label], list[Label]]:
    """Return (labels to score, deadline-alert labels reported separately)."""
    if view == "engine":
        return list(labels), []
    if view == "audited":
        gone = overturned()
        if gone is None:
            raise FileNotFoundError(f"audited view needs {AUDIT_FILE}")
        return [l for l in labels if l.pair_id not in gone], []
    if view != "strict":
        raise ValueError(f"unknown view {view!r}; have {VIEWS}")

    scored, alerts = [], []
    for lab in labels:
        if lab.pair_id in PROSPECTIVE:
            alerts.append(lab)
        elif lab.pair_id in MEMO_ABSENCE:
            scored.append(replace(
                lab,
                verdict=Verdict.NEEDS_EVIDENCE,
                basis="withheld_evidence",
                note=f"strict view: relabelled from fail (evidence absent, not shown absent). {lab.note}",
            ))
        else:
            scored.append(lab)
    return scored, alerts


def alert_report(predictions: list[Prediction], alerts: list[Label]) -> dict:
    """Which verdict the model gave on each prospective deadline."""
    pred = {p.pair_id: p.verdict.value for p in predictions}
    got = {a.pair_id: pred.get(a.pair_id, "no answer") for a in alerts}
    return {"n": len(alerts), "verdicts": dict(Counter(got.values())), "by_pair": got}
