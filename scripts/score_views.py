"""Score every completed v1.1 run under both declared label views.

Predictions are rebuilt from the batch cache (keys carry PROMPT_VERSION), so this
re-scores without any API call and without touching a running sweep.

    python3 scripts/score_views.py            # -> docs/views_results.json
"""

from __future__ import annotations

import json
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from baselines.llm import parse_response  # noqa: E402
from baselines.prompts import PROMPT_VERSION  # noqa: E402
from nofalsegreen import northwind  # noqa: E402
from nofalsegreen.labelviews import DECLARED_ON, VIEWS, alert_report, apply_view  # noqa: E402
from nofalsegreen.metrics import score  # noqa: E402
from nofalsegreen.rulebook import Rulebook  # noqa: E402
from nofalsegreen.subset import subset_firm  # noqa: E402

ANCHOR = ROOT / "data" / "firms" / "northwind-robotics"
CACHE = ROOT / "docs" / ".batch_cache.json"
OUT = ROOT / "docs" / "views_results.json"


def predictions_by_run(firm, cache: dict) -> dict[tuple[str, str], list]:
    """Group cached replies for this firm and prompt version into predictions."""
    ids = [p.pair_id for p in firm.pairs]
    grouped: dict[tuple[str, str], dict] = defaultdict(dict)
    for key, text in cache.items():
        parts = key.split("|")
        if len(parts) != 6 or parts[0] != PROMPT_VERSION or parts[3] != firm.firm_id:
            continue
        _, model, variant, _, _, _ = parts
        if isinstance(text, dict):
            text = text.get("text", "")
        preds, _, _, _ = parse_response(text, ids, variant)
        for pr in preds:
            grouped[(model, variant)][pr.pair_id] = pr
    return {k: list(v.values()) for k, v in grouped.items()}


def main() -> int:
    rb = Rulebook.load(ROOT / "rulebook" / "rulebook.json")
    regimes = rb.rule_regimes()
    firm = subset_firm(northwind.load(ANCHOR, ANCHOR / "expectations.json"), regimes)
    cache = json.loads(CACHE.read_text()) if CACHE.exists() else {}
    runs = predictions_by_run(firm, cache)

    out = {"prompt_version": PROMPT_VERSION, "views_declared_on": DECLARED_ON,
           "firm_id": firm.firm_id, "n_pairs": len(firm.pairs), "runs": {}}
    for (model, variant), preds in sorted(runs.items()):
        entry = {"model": model, "variant": variant,
                 "n_predictions": len(preds), "complete": len(preds) == len(firm.pairs)}
        for view in VIEWS:
            try:
                scored, alerts = apply_view(firm.labels, view)
            except FileNotFoundError:
                continue  # audited view before the audit exists
            keep = {l.pair_id for l in scored}
            s = score(scored, [p for p in preds if p.pair_id in keep], rule_regimes=regimes)
            entry[view] = {
                "n_scored": len(scored),
                "n_violations": sum(1 for l in scored if l.verdict.value == "fail"),
                "false_green_rate": round(s.false_green_rate, 4),
                "n_false_green": s.n_false_green,
                "n_withheld": s.n_withheld,
                "violation_recall": round(s.violation_recall, 4),
                "violation_precision": round(s.violation_precision, 4),
                "abstention_f1": round(s.abstention_f1, 4),
                "n_missing": s.n_missing,
                # Unanswered pairs sit in the FGR denominator and can never be a
                # false green, so a run that answers less looks safer. This is
                # the rate among withheld pairs the model actually answered.
                "n_withheld_answered": sum(
                    1 for l in scored if l.verdict.value == "needs_evidence"
                    and l.pair_id in {p.pair_id for p in preds}),
            }
            ans = entry[view]["n_withheld_answered"]
            entry[view]["false_green_rate_answered"] = (
                round(s.n_false_green / ans, 4) if ans else None)
            if alerts:
                entry[view]["deadline_alerts"] = alert_report(preds, alerts)
        out["runs"][f"{model}::{variant}"] = entry

    OUT.write_text(json.dumps(out, indent=2))
    print(f"wrote {OUT}: {len(out['runs'])} run(s) scored under {len(VIEWS)} views")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
