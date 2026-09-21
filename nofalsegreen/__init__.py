"""No False Green: a benchmark for evidence-aware compliance verdicts."""

from .metrics import Report, score
from .rulebook import Rulebook
from .schema import Entity, Firm, Label, Obligation, Pair, Prediction, Severity, Verdict

__version__ = "0.1.0"
__all__ = [
    "Entity", "Firm", "Label", "Obligation", "Pair", "Prediction", "Report",
    "Rulebook", "Severity", "Verdict", "score",
]
