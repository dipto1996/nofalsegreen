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


BOOT_SEED = 20261003
BOOT_REPS = 2000


def cluster_ci(labels, preds, metric: str, reps: int = BOOT_REPS) -> list[float] | None:
    """95% percentile interval, resampling OBLIGATIONS (rule ids) with replacement.

    Pairs under one obligation share records and a single rule text, so they
    are not independent; resampling pairs would understate the interval."""
    import random
    rng = random.Random(BOOT_SEED)
    pred = {p.pair_id: p.verdict.value for p in preds}
    by_rule: dict[str, list] = defaultdict(list)
    for l in labels:
        by_rule[l.pair_id.split("::")[0]].append(l)
    rules = sorted(by_rule)
    vals = []
    for _ in range(reps):
        num = den = 0
        for r in (rng.choice(rules) for _ in rules):
            for l in by_rule[r]:
                t = l.verdict.value
                if metric == "fgr" and t == "needs_evidence":
                    den += 1
                    num += pred.get(l.pair_id) == "pass"
                elif metric == "recall" and t == "fail":
                    den += 1
                    num += pred.get(l.pair_id) == "fail"
        if den:
            vals.append(num / den)
    if not vals:
        return None
    vals.sort()
    return [round(vals[int(0.025 * len(vals))], 4), round(vals[int(0.975 * len(vals)) - 1], 4)]


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
            kept = [p for p in preds if p.pair_id in keep]
            entry[view]["fgr_ci95"] = cluster_ci(scored, kept, "fgr")
            entry[view]["recall_ci95"] = cluster_ci(scored, kept, "recall")
            ans = entry[view]["n_withheld_answered"]
            entry[view]["false_green_rate_answered"] = (
                round(s.n_false_green / ans, 4) if ans else None)
            if alerts:
                entry[view]["deadline_alerts"] = alert_report(preds, alerts)
        out["runs"][f"{model}::{variant}"] = entry

    # Paired test of the schema ablation: both conditions answer the SAME pairs,
    # so the interval is on the within-model difference, resampling obligations
    # jointly for both conditions.
    import random
    out["ablation"] = {}
    by_model: dict[str, dict] = defaultdict(dict)
    for (model, variant), preds in runs.items():
        by_model[model]["o" if variant.endswith("offered") else "w"] = {p.pair_id: p.verdict.value for p in preds}
    by_rule: dict[str, list] = defaultdict(list)
    for l in firm.labels:
        if l.verdict.value == "needs_evidence":
            by_rule[l.pair_id.split("::")[0]].append(l.pair_id)
    rules = sorted(by_rule)
    llm = ROOT / "docs" / "llm_results.json"
    finished = {k for k, v in json.loads(llm.read_text()).get("runs", {}).items()
                if v.get("per_firm")} if llm.exists() else set()
    for model, d in sorted(by_model.items()):
        if "o" not in d or "w" not in d or not {f"{model}::abstain_offered",
                                                 f"{model}::abstain_withheld"} <= finished:
            continue
        rng = random.Random(BOOT_SEED)
        diffs = []
        for _ in range(BOOT_REPS):
            ids = [pid for r in (rng.choice(rules) for _ in rules) for pid in by_rule[r]]
            fo = sum(d["o"].get(i) == "pass" for i in ids) / len(ids)
            fw = sum(d["w"].get(i) == "pass" for i in ids) / len(ids)
            diffs.append(fw - fo)
        diffs.sort()
        all_ids = [pid for r in rules for pid in by_rule[r]]
        point = (sum(d["w"].get(i) == "pass" for i in all_ids)
                 - sum(d["o"].get(i) == "pass" for i in all_ids)) / len(all_ids)
        out["ablation"][model] = {
            "delta_fgr": round(point, 4),
            "ci95": [round(diffs[int(0.025 * BOOT_REPS)], 4), round(diffs[int(0.975 * BOOT_REPS) - 1], 4)],
            "share_boot_le_0": round(sum(x <= 0 for x in diffs) / BOOT_REPS, 4),
        }

    OUT.write_text(json.dumps(out, indent=2))
    print(f"wrote {OUT}: {len(out['runs'])} run(s) scored under {len(VIEWS)} views")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
