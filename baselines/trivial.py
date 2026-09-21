"""Trivial baselines. These exist to establish the floor and, more importantly,
to demonstrate that accuracy-style scoring cannot separate a safe system from
an unsafe one.

`always_pass` is the adversary the benchmark is built around: it is maximally
unsafe (it reports every unassessed obligation as satisfied) yet it scores
perfectly on the planted controls and is never wrong about a compliant case.
"""

from __future__ import annotations

from nofalsegreen.schema import Firm, Prediction, Verdict


def always_pass(firm: Firm) -> list[Prediction]:
    """Report everything as compliant. False green rate = 1.0 by construction."""
    return [Prediction(p.pair_id, Verdict.PASS, rationale="no contrary evidence found") for p in firm.pairs]


def always_abstain(firm: Firm) -> list[Prediction]:
    """Never decide anything. False green rate = 0.0, violation recall = 0.0.

    The safe-but-useless corner. Reporting this baseline is what keeps the
    false-green rate honest: a system cannot be praised for a low false-green
    rate without also showing it detects violations.
    """
    return [Prediction(p.pair_id, Verdict.NEEDS_EVIDENCE, rationale="abstain") for p in firm.pairs]


def always_fail(firm: Firm) -> list[Prediction]:
    """Flag everything. Perfect violation recall, maximal false alarms."""
    return [Prediction(p.pair_id, Verdict.FAIL, rationale="flag all") for p in firm.pairs]


def evidence_aware_oracle(firm: Firm) -> list[Prediction]:
    """Upper bound: decides exactly when the required evidence is present.

    This is not a competitive system; it reads the label basis. It exists to
    show the task is solvable in principle, so a low score is a property of
    the system under test and not of an ill-posed benchmark.
    """
    idx = firm.label_index()
    out = []
    for p in firm.pairs:
        lab = idx.get(p.pair_id)
        out.append(Prediction(p.pair_id, lab.verdict if lab else Verdict.NEEDS_EVIDENCE))
    return out


REGISTRY = {
    "always_pass": always_pass,
    "always_abstain": always_abstain,
    "always_fail": always_fail,
    "oracle": evidence_aware_oracle,
}
