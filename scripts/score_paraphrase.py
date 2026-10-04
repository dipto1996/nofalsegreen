"""Score Study 3b (docs/STUDY3B_PARAPHRASE.md). No API call; writes docs/study3b/results.json."""

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
from nofalsegreen import study3  # noqa: E402
from nofalsegreen.rulebook import Rulebook  # noqa: E402

MODELS = [f"vertex/{m}#r0" for m in study3.GOOGLE_MODELS]
DRAWS, SEED = 2000, 20261003
SPECS = {
    "R1 proxy columns, dashboard": ("plain", "{w}", "decoy", "{w}"),
    "R2 proxy columns, offered": ("plain", "{o}", "decoy", "{o}"),
    "R3 schema, offered -> dashboard (proxy firms)": ("decoy", "{o}", "decoy", "{w}"),
}
WORDINGS = {"paraphrased": ("abstain_offered_para", "abstain_withheld_para"),
            "original": ("abstain_offered", "abstain_withheld")}


def main() -> int:
    rb = Rulebook.load(ROOT / "rulebook" / "rulebook.json")
    firms = {a: study3.load_firms(rb, a) for a in study3.ARMS}
    cache: dict = {}
    for d in ("study3", "study3b"):
        for vc in sorted((ROOT / "docs" / d / "cache").glob("*.json")):
            cache.update(json.loads(vc.read_text()))
    conds = [c for w in WORDINGS.values() for c in w]
    verd = {(m, a, c): {} for m in MODELS for a in study3.ARMS for c in conds}
    cells = {}
    for m in MODELS:
        for a in study3.ARMS:
            for c in conds:
                labels, pred = [], {}
                from dataclasses import replace
                for f in firms[a]:
                    s = f.provenance["seed"]
                    p = preds_for(cache, f, m, c)
                    for l in f.labels:
                        k = f"{s}|{l.pair_id}"
                        labels.append(replace(l, pair_id=k))
                        if l.pair_id in p:
                            pred[k] = p[l.pair_id]
                verd[(m, a, c)] = pred
                cells[f"{m.split('/')[1].split('#')[0]}::{a}::{c}"] = metrics(labels, pred)
    unass = sorted({f"{f.provenance['seed']}|{l.pair_id}" for f in firms["decoy"] for l in f.labels
                    if l.verdict.value == "needs_evidence"})
    clusters = defaultdict(list)
    for k in unass:
        clusters[k.split("|")[0] + "|" + k.split("|", 1)[1].split("::")[0]].append(k)
    cids = sorted(clusters)
    rng = random.Random(SEED)
    draws = [[rng.choice(cids) for _ in cids] for _ in range(DRAWS)]

    def est(a1, c1, a2, c2):
        ds = []
        for m in MODELS:
            va, vb = verd[(m, a1, c1)], verd[(m, a2, c2)]
            d = {k: float(vb[k] == "pass") - float(va[k] == "pass") for k in unass if k in va and k in vb}
            if d:
                ds.append(d)

        def stat(pick):
            means = []
            for d in ds:
                xs = [d[k] for cl in pick for k in clusters[cl] if k in d]
                if xs:
                    means.append(sum(xs) / len(xs))
            return sum(means) / len(means) if means else None
        if not ds:
            return {"n_models": 0}
        b = sorted(x for x in (stat(p) for p in draws) if x is not None)
        n = len(b)
        p = 2 * min(sum(x <= 0 for x in b), sum(x >= 0 for x in b)) / n
        return {"n_models": len(ds), "delta": round(stat(cids), 4),
                "ci95": [round(b[int(0.025 * n)], 4), round(b[int(0.975 * n) - 1], 4)],
                "p_two_sided": round(min(1.0, max(p, 1 / DRAWS)), 4)}

    out = {"declared": "docs/STUDY3B_PARAPHRASE.md", "cells": cells, "tests": {}, "original_wording": {}}
    for name, (a1, c1, a2, c2) in SPECS.items():
        o, w = WORDINGS["paraphrased"]
        out["tests"][name] = est(a1, c1.format(o=o, w=w), a2, c2.format(o=o, w=w))
        o, w = WORDINGS["original"]
        out["original_wording"][name] = est(a1, c1.format(o=o, w=w), a2, c2.format(o=o, w=w))
    ps = {k: v["p_two_sided"] for k, v in out["tests"].items() if "p_two_sided" in v}
    run = 0.0
    for i, k in enumerate(sorted(ps, key=ps.get)):
        run = max(run, min(1.0, (len(ps) - i) * ps[k]))
        out["tests"][k]["p_holm"] = round(run, 4)
        v = out["tests"][k]
        v["outcome"] = "replicated" if run < 0.05 and v["delta"] > 0 else "not replicated"
    (ROOT / "docs" / "study3b").mkdir(exist_ok=True)
    (ROOT / "docs" / "study3b" / "results.json").write_text(json.dumps(out, indent=2))
    for k in out["tests"]:
        print(k, out["tests"][k], "| original:", out["original_wording"][k])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
