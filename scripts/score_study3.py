"""Score Study 3 as declared in docs/STUDY3_PREREGISTRATION.md.

Committed with the declaration, before any Study 3 call. Predictions are
rebuilt from the batch caches in docs/study3/cache/, so scoring makes no API
call. Writes docs/study3/results.json.

    python3 scripts/score_study3.py
"""

from __future__ import annotations

import json
import random
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

from score_studies import metrics, preds_for  # noqa: E402
from nofalsegreen import northwind, study3  # noqa: E402
from nofalsegreen.rulebook import Rulebook  # noqa: E402
from nofalsegreen.subset import subset_firm  # noqa: E402

DIR = ROOT / "docs" / "study3"
DRAWS, SEED = 2000, 20261003
MODELS = ([f"vertex/{m}#r0" for m in study3.GOOGLE_MODELS]
          + [f"vertexopen/{m}#r0" for m in study3.OPEN_MODELS])
GOOGLE = set(MODELS[:3])

# (name, arm A, condition A, arm B, condition B): difference is B - A.
PRIMARY = [
    ("P1 abstention effect", "decoy", "abstain_offered", "decoy", "abstain_closed"),
    ("P2 definition effect", "decoy", "abstain_closed", "decoy", "abstain_withheld"),
    ("P3 adjacent columns, dashboard schema", "plain", "abstain_withheld", "decoy", "abstain_withheld"),
    ("P4 adjacent columns, recommended schema", "plain", "abstain_offered", "decoy", "abstain_offered"),
]
S2 = ("S2 abstention label only", "decoy", "abstain_offered", "decoy", "abstain_removed_only")


def short(model: str) -> str:
    return model.split("/", 1)[1].split("#")[0].split("/")[-1]


def holm(ps: dict[str, float]) -> dict[str, float]:
    order, out, run = sorted(ps, key=ps.get), {}, 0.0
    for i, k in enumerate(order):
        run = max(run, min(1.0, (len(order) - i) * ps[k]))
        out[k] = round(run, 4)
    return out


def main() -> int:
    rb = Rulebook.load(ROOT / "rulebook" / "rulebook.json")
    firms = {arm: study3.load_firms(rb, arm) for arm in study3.ARMS}
    cache: dict = {}
    for vc in sorted((DIR / "cache").glob("*.json")):
        cache.update(json.loads(vc.read_text()))

    # verdicts[model][(arm, cond)][seed|pair_id] = verdict; labels keyed the same way
    verdicts: dict = defaultdict(dict)
    cells: dict = {}
    for model in MODELS:
        for arm in study3.ARMS:
            for cond in study3.CONDITIONS:
                pred, labels = {}, []
                from dataclasses import replace
                for f in firms[arm]:
                    seed = f.provenance["seed"]
                    p = preds_for(cache, f, model, cond)
                    for l in f.labels:
                        k = f"{seed}|{l.pair_id}"
                        labels.append(replace(l, pair_id=k))
                        if l.pair_id in p:
                            pred[k] = p[l.pair_id]
                verdicts[model][(arm, cond)] = pred
                cells[f"{short(model)}::{arm}::{cond}"] = metrics(labels, pred)

    withheld = {f"{f.provenance['seed']}|{l.pair_id}": f"{f.provenance['seed']}|{l.pair_id.split('::')[0]}"
                for f in firms["decoy"] for l in f.labels if l.verdict.value == "needs_evidence"}
    clusters: dict[str, list[str]] = defaultdict(list)
    for k, c in withheld.items():
        clusters[c].append(k)
    cids = sorted(clusters)
    rng = random.Random(SEED)
    draws = [[rng.choice(cids) for _ in cids] for _ in range(DRAWS)]

    def per_model_diffs(model, spec) -> dict[str, float]:
        _, a_arm, a_cond, b_arm, b_cond = spec
        va, vb = verdicts[model][(a_arm, a_cond)], verdicts[model][(b_arm, b_cond)]
        return {k: float(vb[k] == "pass") - float(va[k] == "pass")
                for k in withheld if k in va and k in vb}

    def estimate(models, spec) -> dict:
        diffs = {m: per_model_diffs(m, spec) for m in models}
        diffs = {m: d for m, d in diffs.items() if d}
        if not diffs:
            return {"n_models": 0}

        def stat(pick) -> float | None:
            means = []
            for d in diffs.values():
                xs = [d[k] for c in pick for k in clusters[c] if k in d]
                if xs:
                    means.append(sum(xs) / len(xs))
            return sum(means) / len(means) if means else None

        point = stat(cids)
        boots = sorted(x for x in (stat(p) for p in draws) if x is not None)
        n = len(boots)
        p = 2 * min(sum(x <= 0 for x in boots), sum(x >= 0 for x in boots)) / n
        return {"n_models": len(diffs), "n_pairs": {short(m): len(d) for m, d in diffs.items()},
                "delta": round(point, 4),
                "ci95": [round(boots[int(0.025 * n)], 4), round(boots[int(0.975 * n) - 1], 4)],
                "p_two_sided": round(min(1.0, max(p, 1 / DRAWS)), 4)}

    out: dict = {"declared": "docs/STUDY3_PREREGISTRATION.md", "cells": cells}

    prim = {spec[0]: estimate(MODELS, spec) for spec in PRIMARY}
    adj = holm({k: v["p_two_sided"] for k, v in prim.items() if "p_two_sided" in v})
    for k, v in prim.items():
        if k in adj:
            v["p_holm"] = adj[k]
            v["outcome"] = ("confirmed" if adj[k] < 0.05 and v["delta"] > 0 else
                            "contradicted" if adj[k] < 0.05 and v["delta"] < 0 else "not confirmed")
    out["primary"] = prim

    s1 = {f"{spec[0]} | {short(m)}": estimate([m], spec) for spec in PRIMARY for m in MODELS}
    adj = holm({k: v["p_two_sided"] for k, v in s1.items() if "p_two_sided" in v})
    for k in adj:
        s1[k]["p_holm"] = adj[k]
    out["S1_per_model"] = s1

    s2 = {"pooled": estimate(MODELS, S2), **{short(m): estimate([m], S2) for m in MODELS}}
    adj = holm({k: v["p_two_sided"] for k, v in s2.items() if "p_two_sided" in v})
    for k in adj:
        s2[k]["p_holm"] = adj[k]
    out["S2_removed_only"] = s2

    # S3: interaction, definition effect on decoy minus on plain.
    def p2_diff(model, arm):
        spec = ("", arm, "abstain_closed", arm, "abstain_withheld")
        return per_model_diffs(model, spec)
    inter = {}
    for m in MODELS:
        d_dec, d_pl = p2_diff(m, "decoy"), p2_diff(m, "plain")
        inter[m] = {k: d_dec[k] - d_pl[k] for k in d_dec if k in d_pl}
    inter = {m: d for m, d in inter.items() if d}

    def istat(pick):
        means = []
        for d in inter.values():
            xs = [d[k] for c in pick for k in clusters[c] if k in d]
            if xs:
                means.append(sum(xs) / len(xs))
        return sum(means) / len(means) if means else None
    if inter:
        boots = sorted(x for x in (istat(p) for p in draws) if x is not None)
        n = len(boots)
        out["S3_interaction"] = {
            "delta": round(istat(cids), 4),
            "ci95": [round(boots[int(0.025 * n)], 4), round(boots[int(0.975 * n) - 1], 4)],
            "p_two_sided": round(min(1.0, max(2 * min(sum(x <= 0 for x in boots),
                                                      sum(x >= 0 for x in boots)) / n, 1 / DRAWS)), 4)}

    s4 = {}
    for group, ms in (("google", [m for m in MODELS if m in GOOGLE]),
                      ("other_developers", [m for m in MODELS if m not in GOOGLE])):
        for spec in PRIMARY:
            s4[f"{spec[0]} | {group}"] = estimate(ms, spec)
    adj = holm({k: v["p_two_sided"] for k, v in s4.items() if "p_two_sided" in v})
    for k in adj:
        s4[k]["p_holm"] = adj[k]
    out["S4_by_developer_group"] = s4

    # S5: false alarms per arm (descriptive), from the cell metrics.
    out["S5_false_alarms"] = {
        k: {"all_controls": v["false_alarm_rate"], "near_miss": v["false_alarm_near_miss"]}
        for k, v in cells.items()}

    # EXPLORATORY, added after the results (not in the declaration): false-green rate
    # by rule family (I-9 rules vs the wage rule), mean over models, per arm and schema.
    fam = {}
    for arm in study3.ARMS:
        for cond in study3.CONDITIONS:
            for family in ("i9", "wage"):
                rates = []
                for m in MODELS:
                    v = verdicts[m][(arm, cond)]
                    ks = [k for k in withheld if k in v
                          and (k.split("|", 1)[1].startswith("lca.wage")) == (family == "wage")]
                    if ks:
                        rates.append(sum(v[k] == "pass" for k in ks) / len(ks))
                fam[f"{family}::{arm}::{cond}"] = round(sum(rates) / len(rates), 4) if rates else None
    out["exploratory_by_rule_family"] = fam

    # Extension E1: new models on the Study 1 anchor subset (descriptive).
    anchor_dir = ROOT / "data" / "firms" / "northwind-robotics"
    anchor = subset_firm(northwind.load(anchor_dir, anchor_dir / "expectations.json"),
                         rb.rule_regimes())
    e1 = {}
    for m in MODELS[3:]:
        for cond in study3.CONDITIONS:
            pr = preds_for(cache, anchor, m, cond)
            if pr:
                e1[f"{short(m)}::{cond}"] = metrics(anchor.labels, pr)
    out["E1_anchor"] = e1

    (DIR / "results.json").write_text(json.dumps(out, indent=2))
    print(f"wrote {DIR / 'results.json'}")
    for k, v in prim.items():
        print(f"  {k}: {v}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
