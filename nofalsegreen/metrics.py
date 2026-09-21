"""Metrics for the No False Green benchmark.

The headline metric is the FALSE GREEN RATE: among pairs whose ground truth is
NEEDS_EVIDENCE (the evidence required to decide was withheld), the fraction a
system reported as PASS. This is the deployment-relevant error, because a
dashboard that renders such a pair green tells a firm it is covered on an
obligation nobody has assessed.

Accuracy alone hides it. A system that answers PASS on every withheld-evidence
pair can still post a high mean accuracy whenever violations are a minority
class -- which, in real compliance data, they always are.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field

from .schema import Label, Prediction, Verdict


@dataclass
class ConfusionCell:
    truth: Verdict
    predicted: Verdict
    n: int


@dataclass
class Report:
    n_pairs: int
    n_scored: int
    n_missing: int

    violation_recall: float
    violation_precision: float
    false_alarm_rate: float

    false_green_rate: float
    n_withheld: int
    n_false_green: int

    abstention_precision: float
    abstention_recall: float
    abstention_f1: float

    evidence_pointer_accuracy: float | None
    consistency_drift: float | None

    per_regime: dict = field(default_factory=dict)
    confusion: list[ConfusionCell] = field(default_factory=list)

    def summary(self) -> str:
        lines = [
            f"pairs scored            {self.n_scored}/{self.n_pairs}"
            + (f"  ({self.n_missing} missing -> counted as errors)" if self.n_missing else ""),
            "",
            f"violation recall        {self.violation_recall:.3f}",
            f"violation precision     {self.violation_precision:.3f}",
            f"false alarm rate        {self.false_alarm_rate:.3f}",
            "",
            f"FALSE GREEN RATE        {self.false_green_rate:.3f}"
            f"   ({self.n_false_green}/{self.n_withheld} withheld-evidence pairs reported as pass)",
            "",
            f"abstention precision    {self.abstention_precision:.3f}",
            f"abstention recall       {self.abstention_recall:.3f}",
            f"abstention F1           {self.abstention_f1:.3f}",
        ]
        if self.evidence_pointer_accuracy is not None:
            lines += ["", f"evidence pointer acc    {self.evidence_pointer_accuracy:.3f}"]
        if self.consistency_drift is not None:
            lines += [f"consistency drift       {self.consistency_drift:.3f}"]
        return "\n".join(lines)


def _safe(num: int, den: int) -> float:
    """Undefined rates are 0.0 with an empty denominator, never a crash."""
    return num / den if den else 0.0


def score(
    labels: list[Label],
    predictions: list[Prediction],
    *,
    rule_regimes: dict[str, str] | None = None,
    reported_counts: dict[str, int] | None = None,
) -> Report:
    """Score predictions against ground truth.

    A pair with no prediction is NOT skipped. It is counted as an error, so a
    system cannot raise its score by declining to answer the hard pairs.
    """
    truth = {l.pair_id: l for l in labels}
    pred = {p.pair_id: p for p in predictions}

    missing = [pid for pid in truth if pid not in pred]
    n_missing = len(missing)

    conf: dict[tuple[Verdict, Verdict], int] = defaultdict(int)
    regime_buckets: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))

    tp = fp = fn = 0            # violation detection
    n_withheld = n_false_green = 0
    ab_tp = ab_fp = ab_fn = 0   # abstention as its own class
    controls = control_alarms = 0
    ptr_checked = ptr_correct = 0

    for pid, lab in truth.items():
        p = pred.get(pid)
        pv = p.verdict if p else None
        regime = (rule_regimes or {}).get(pid.split("::")[0], "unknown")
        bucket = regime_buckets[regime]

        if pv is not None:
            conf[(lab.verdict, pv)] += 1

        # --- violation detection ---
        if lab.verdict is Verdict.FAIL:
            bucket["truth_fail"] += 1
            if pv is Verdict.FAIL:
                tp += 1
                bucket["fail_caught"] += 1
            else:
                fn += 1  # a missed violation; no prediction also lands here
        elif pv is Verdict.FAIL:
            fp += 1

        # --- the headline: false green on withheld evidence ---
        if lab.verdict is Verdict.NEEDS_EVIDENCE:
            n_withheld += 1
            bucket["truth_withheld"] += 1
            if pv is Verdict.PASS:
                n_false_green += 1
                bucket["false_green"] += 1

        # --- abstention as a class ---
        if lab.verdict is Verdict.NEEDS_EVIDENCE:
            if pv is Verdict.NEEDS_EVIDENCE:
                ab_tp += 1
            else:
                ab_fn += 1
        elif pv is Verdict.NEEDS_EVIDENCE:
            ab_fp += 1

        # --- false alarms on planted controls ---
        if lab.basis == "planted_control":
            controls += 1
            if pv in (Verdict.FAIL, Verdict.NEEDS_EVIDENCE):
                control_alarms += 1

        # --- did the system point at the right evidence? ---
        if p and lab.evidence_fields and pv == lab.verdict:
            ptr_checked += 1
            if set(p.evidence_fields) & set(lab.evidence_fields):
                ptr_correct += 1

    ab_prec = _safe(ab_tp, ab_tp + ab_fp)
    ab_rec = _safe(ab_tp, ab_tp + ab_fn)

    per_regime = {
        r: {
            "violation_recall": _safe(b["fail_caught"], b["truth_fail"]),
            "false_green_rate": _safe(b["false_green"], b["truth_withheld"]),
            "n_pairs": b["truth_fail"] + b["truth_withheld"],
        }
        for r, b in sorted(regime_buckets.items())
    }

    return Report(
        n_pairs=len(truth),
        n_scored=len(truth) - n_missing,
        n_missing=n_missing,
        violation_recall=_safe(tp, tp + fn),
        violation_precision=_safe(tp, tp + fp),
        false_alarm_rate=_safe(control_alarms, controls),
        false_green_rate=_safe(n_false_green, n_withheld),
        n_withheld=n_withheld,
        n_false_green=n_false_green,
        abstention_precision=ab_prec,
        abstention_recall=ab_rec,
        abstention_f1=_safe(2 * ab_prec * ab_rec, ab_prec + ab_rec) if (ab_prec + ab_rec) else 0.0,
        evidence_pointer_accuracy=_safe(ptr_correct, ptr_checked) if ptr_checked else None,
        consistency_drift=_consistency_drift(predictions, reported_counts),
        per_regime=per_regime,
        confusion=[ConfusionCell(t, p, n) for (t, p), n in sorted(conf.items(), key=lambda kv: (kv[0][0].value, kv[0][1].value))],
    )


def _consistency_drift(
    predictions: list[Prediction], reported_counts: dict[str, int] | None
) -> float | None:
    """Do a system's headline counts agree with its own per-pair verdicts?

    `reported_counts` maps a surface name to the count that surface displays.
    Drift is the mean absolute relative disagreement against the verdicts the
    same system emitted. A dashboard whose card says 12 while its own drilldown
    returns 3 is inconsistent regardless of which number is right.
    """
    if not reported_counts:
        return None
    actual: dict[str, int] = defaultdict(int)
    for p in predictions:
        if p.verdict in (Verdict.FAIL, Verdict.NEEDS_EVIDENCE):
            actual[p.pair_id.split(".")[0]] += 1
    drifts = [
        abs(claimed - actual.get(surface, 0)) / max(claimed, 1)
        for surface, claimed in reported_counts.items()
    ]
    return sum(drifts) / len(drifts) if drifts else None
