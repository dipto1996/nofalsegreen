"""Score Study 2 (free-tier models) and the Vertex block from retained replies.

Predictions are rebuilt from the batch cache, so scoring needs no API call.
Writes docs/studies_results.json.

Study 2 per run: per-firm metrics, then mean and standard deviation across the
six firms, plus pooled counts. False alarms are reported on all conforming
controls and separately on near-miss controls, the boundary cases.

Vertex block: each (model, study, condition) has three repeats; the reported
value is their mean, with min and max beside it.
"""

from __future__ import annotations

import json
import statistics
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from baselines.llm import parse_response  # noqa: E402
from baselines.prompts import PROMPT_VERSION  # noqa: E402
from nofalsegreen import northwind, study2  # noqa: E402
from nofalsegreen.rulebook import Rulebook  # noqa: E402
from nofalsegreen.subset import subset_firm  # noqa: E402

CACHE = ROOT / "docs" / ".batch_cache.json"
OUT = ROOT / "docs" / "studies_results.json"


def preds_for(cache: dict, firm, model: str, variant: str) -> dict[str, str]:
    ids = [p.pair_id for p in firm.pairs]
    out: dict[str, str] = {}
    for key, v in cache.items():
        parts = key.split("|")
        if (len(parts) != 6 or parts[0] != PROMPT_VERSION or parts[1] != model
                or parts[2] != variant or parts[3] != firm.firm_id):
            continue
        text = v.get("text", "") if isinstance(v, dict) else v
        for p in parse_response(text, ids, variant)[0]:
            out[p.pair_id] = p.verdict.value
    return out


def metrics(labels, pred: dict[str, str]) -> dict:
    c = defaultdict(int)
    for l in labels:
        t, g = l.verdict.value, pred.get(l.pair_id)
        near = "near-miss" in (l.note or "")
        c["answered"] += g is not None
        if t == "needs_evidence":
            c["withheld"] += 1
            c["fg"] += g == "pass"
            c["abst"] += g == "needs_evidence"
        elif t == "fail":
            c["fail"] += 1
            c["tp"] += g == "fail"
        elif t == "pass":
            k = "near" if near else "ctrl"
            c[k] += 1
            c[k + "_alarm"] += g is not None and g != "pass"
        c["pred_fail"] += g == "fail"
        if t == "needs_evidence" and g is not None:
            c[f"withheld_as_{g}"] += 1
        c["pred_abst"] += g == "needs_evidence"
    r = lambda a, b: (c[a] / c[b]) if c[b] else None  # noqa: E731
    prec_abst = c["abst"] / c["pred_abst"] if c["pred_abst"] else None
    rec_abst = r("abst", "withheld")
    f1 = (2 * prec_abst * rec_abst / (prec_abst + rec_abst)
          if prec_abst and rec_abst else (0.0 if c["withheld"] else None))
    alarms = c["ctrl_alarm"] + c["near_alarm"]
    controls = c["ctrl"] + c["near"]
    return {
        "n": len(labels), "answered": c["answered"],
        "false_green_rate": r("fg", "withheld"),
        "violation_recall": r("tp", "fail"),
        "violation_precision": (c["tp"] / c["pred_fail"]) if c["pred_fail"] else None,
        "false_alarm_rate": (alarms / controls) if controls else None,
        "false_alarm_near_miss": r("near_alarm", "near"),
        "false_alarm_other_controls": r("ctrl_alarm", "ctrl"),
        "abstention_f1": f1,
        "counts": dict(c),
    }


def pool(firms, cache, model, variant, exclude_rule: str | None = None) -> dict:
    """Pooled over firms. Pair ids repeat across generated firms (every firm
    has SYN-1001), so each pair is keyed by firm as well."""
    from dataclasses import replace as _r
    labels, pred = [], {}
    for f in firms:
        p = preds_for(cache, f, model, variant)
        for l in f.labels:
            if exclude_rule and l.pair_id.startswith(exclude_rule + "::"):
                continue
            k = f"{f.firm_id}|{l.pair_id}"
            labels.append(_r(l, pair_id=k))
            if l.pair_id in p:
                pred[k] = p[l.pair_id]
    return metrics(labels, pred)


def summarise(per_firm: list[dict]) -> dict:
    out = {}
    for k in ("false_green_rate", "violation_recall", "violation_precision", "false_alarm_rate",
              "false_alarm_near_miss", "false_alarm_other_controls", "abstention_f1"):
        xs = [m[k] for m in per_firm if m[k] is not None]
        out[k] = {"mean": round(statistics.mean(xs), 4) if xs else None,
                  "sd": round(statistics.stdev(xs), 4) if len(xs) > 1 else None,
                  "n_firms": len(xs)}
    return out


def main() -> int:
    rb = Rulebook.load(ROOT / "rulebook" / "rulebook.json")
    anchor_dir = ROOT / "data" / "firms" / "northwind-robotics"
    anchor = subset_firm(northwind.load(anchor_dir, anchor_dir / "expectations.json"), rb.rule_regimes())
    firms2 = study2.load_firms(rb)
    cache = json.loads(CACHE.read_text())
    # Vertex runs keep one cache per (model, repeat); merge them read-only.
    for vc in sorted((ROOT / "docs" / "vertex" / "cache").glob("*.json")):
        cache.update(json.loads(vc.read_text()))

    def finished(path: Path, n_firms: int) -> set[str]:
        if not path.exists():
            return set()
        return {k for k, v in json.loads(path.read_text()).get("runs", {}).items()
                if len(v.get("per_firm", [])) == n_firms}

    out = {"prompt_version": PROMPT_VERSION, "study2": {}, "vertex": {}}

    # Study 2, free-tier models
    for key in sorted(finished(ROOT / "docs" / "study2" / "llm_results.json", len(firms2))):
        model, variant = key.split("::")
        per = [metrics(f.labels, preds_for(cache, f, model, variant)) for f in firms2]
        pooled = pool(firms2, cache, model, variant)
        out["study2"][key] = {"per_firm": per, "mean_over_firms": summarise(per), "pooled": pooled,
                              "pooled_without_reverification": pool(
                                  firms2, cache, model, variant,
                                  exclude_rule="i9.reverification.deadline")}

    # Vertex block
    reps: dict[tuple, list] = defaultdict(list)
    vertex_runs = []
    for study in ("study1", "study2"):
        for path in sorted((ROOT / "docs" / "vertex" / "runs").glob(f"*__{study}.json")):
            vertex_runs += [(study, k) for k in finished(path, 1 if study == "study1" else len(firms2))]
    for study, key in vertex_runs:
        model, variant = key.split("::")
        base = model.split("#")[0]
        if study == "study1":
            m = metrics(anchor.labels, preds_for(cache, anchor, model, variant))
        else:
            m = pool(firms2, cache, model, variant)
            # Sensitivity: a late reverification may be lawful under the 240-day
            # rule, which the exports cannot show (paper, Section 10).
            m["without_reverification"] = pool(firms2, cache, model, variant,
                                               exclude_rule="i9.reverification.deadline")
        reps[(base, study, variant)].append({"rep": model.split("#")[-1], **m})
    for (base, study, variant), runs in sorted(reps.items()):
        agg = {}
        for k in ("false_green_rate", "violation_recall", "violation_precision", "false_alarm_rate",
                  "false_alarm_near_miss", "abstention_f1"):
            xs = [r[k] for r in runs if r[k] is not None]
            agg[k] = ({"mean": round(statistics.mean(xs), 4), "min": round(min(xs), 4),
                       "max": round(max(xs), 4)} if xs else None)
        agg["answered_min"] = min(r["answered"] for r in runs)
        out["vertex"][f"{base}::{study}::{variant}"] = {"n_repeats": len(runs), "repeats": runs, "summary": agg}

    OUT.write_text(json.dumps(out, indent=2))
    print(f"wrote {OUT}: {len(out['study2'])} Study 2 runs, {len(out['vertex'])} Vertex cells")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
