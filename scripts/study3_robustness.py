"""Robustness of the Study 3 primary tests (exploratory; added after the results).

1. Exact cluster sign-flip permutation test. Under the null of no effect, each
   (firm, rule) cluster's paired differences are symmetric about zero, so the
   sign of every cluster's contribution can be flipped. With 18 clusters all
   2^18 = 262,144 sign patterns are enumerated: an exact two-sided p-value with
   no bootstrap floor.
2. Leave one model out: the pooled estimate over the other six, seven times.
3. Leave one firm out: the pooled estimate over the other eleven firms, twelve times.

No API call. Writes docs/study3/robustness.json.
"""

from __future__ import annotations

import itertools
import json
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

from score_studies import preds_for  # noqa: E402
from score_study3 import MODELS, PRIMARY, short  # noqa: E402
from nofalsegreen import study3  # noqa: E402
from nofalsegreen.rulebook import Rulebook  # noqa: E402


def main() -> int:
    rb = Rulebook.load(ROOT / "rulebook" / "rulebook.json")
    firms = {a: study3.load_firms(rb, a) for a in study3.ARMS}
    cache: dict = {}
    for vc in sorted((ROOT / "docs" / "study3" / "cache").glob("*.json")):
        cache.update(json.loads(vc.read_text()))
    verd = {}
    for m in MODELS:
        for a in study3.ARMS:
            for c in study3.CONDITIONS:
                d = {}
                for f in firms[a]:
                    s = f.provenance["seed"]
                    for pid, v in preds_for(cache, f, m, c).items():
                        d[f"{s}|{pid}"] = v
                verd[(m, a, c)] = d
    unass = sorted({f"{f.provenance['seed']}|{l.pair_id}" for f in firms["decoy"] for l in f.labels
                    if l.verdict.value == "needs_evidence"})
    clusters = defaultdict(list)
    for k in unass:
        clusters[k.split("|")[0] + "|" + k.split("|", 1)[1].split("::")[0]].append(k)
    cids = sorted(clusters)

    def diffs(m, spec):
        _, a1, c1, a2, c2 = spec
        va, vb = verd[(m, a1, c1)], verd[(m, a2, c2)]
        return {k: float(vb[k] == "pass") - float(va[k] == "pass") for k in unass if k in va and k in vb}

    def pooled(spec, models, keep=lambda k: True):
        means = []
        for m in models:
            d = {k: v for k, v in diffs(m, spec).items() if keep(k)}
            if d:
                means.append(sum(d.values()) / len(d))
        return sum(means) / len(means)

    out = {"note": "EXPLORATORY: robustness checks added after the results."}
    signs = np.array(list(itertools.product((1.0, -1.0), repeat=len(cids))))
    perm = {}
    for spec in PRIMARY:
        # Cluster weights: the pooled statistic is linear in cluster sums.
        w = np.zeros(len(cids))
        for m in MODELS:
            d = diffs(m, spec)
            n = len(d)
            for j, c in enumerate(cids):
                w[j] += sum(d.get(k, 0.0) for k in clusters[c]) / n / len(MODELS)
        obs = float(w.sum())
        stats = np.concatenate([(signs[i:i + 16384] * w).sum(axis=1) for i in range(0, len(signs), 16384)])
        assert np.isfinite(stats).all() and abs(stats[0] - obs) < 1e-9
        p = float(np.mean(np.abs(stats) >= abs(obs) - 1e-12))
        perm[spec[0]] = {"observed": round(obs, 4), "p_exact_two_sided": p,
                         "n_patterns": int(len(signs))}
    ps = {k: v["p_exact_two_sided"] for k, v in perm.items()}
    run = 0.0
    for i, k in enumerate(sorted(ps, key=ps.get)):
        run = max(run, min(1.0, (len(ps) - i) * ps[k]))
        perm[k]["p_holm"] = run
    out["sign_flip_permutation"] = perm

    loo_m = {}
    for spec in PRIMARY:
        vals = {short(m): round(pooled(spec, [x for x in MODELS if x != m]), 4) for m in MODELS}
        loo_m[spec[0]] = {"min": min(vals.values()), "max": max(vals.values()), "by_dropped_model": vals}
    out["leave_one_model_out"] = loo_m

    seeds = sorted({k.split("|")[0] for k in unass})
    loo_f = {}
    for spec in PRIMARY:
        vals = {s: round(pooled(spec, MODELS, keep=lambda k, s=s: k.split("|")[0] != s), 4) for s in seeds}
        loo_f[spec[0]] = {"min": min(vals.values()), "max": max(vals.values()), "by_dropped_firm": vals}
    out["leave_one_firm_out"] = loo_f

    # 4. Firm as the unit: exact sign-flip over the 12 firms, firm bootstrap,
    # and the proxy-column effect split by rule family.
    import random
    seeds_ = sorted({k.split("|")[0] for k in unass})
    fam = lambda k: "wage" if k.split("|", 1)[1].startswith("lca.wage") else "i9"  # noqa: E731

    def firm_effects(spec, family=None):
        res = {}
        for fs in seeds_:
            vals = []
            for m in MODELS:
                d = diffs(m, spec)
                ks = [k for k in d if k.startswith(fs + "|") and (family is None or fam(k) == family)]
                if ks:
                    vals.append(sum(d[k] for k in ks) / len(ks))
            if vals:
                res[fs] = sum(vals) / len(vals)
        return res

    rng = random.Random(20261003)
    firm_level = {}
    for spec in PRIMARY:
        for family in (None, "i9", "wage"):
            if family and "adjacent" not in spec[0]:
                continue
            fe = firm_effects(spec, family)
            xs = list(fe.values())
            obs = sum(xs) / len(xs)
            pats = itertools.product((1, -1), repeat=len(xs))
            perm_f = [abs(sum(sg * x for sg, x in zip(pt, xs)) / len(xs)) for pt in pats]
            pval = sum(v >= abs(obs) - 1e-12 for v in perm_f) / len(perm_f)
            fs_ = list(fe)
            boots = sorted(sum(fe[f] for f in pick) / len(pick)
                           for pick in ([rng.choice(fs_) for _ in fs_] for _ in range(2000)))
            firm_level[f"{spec[0]}{' | ' + family if family else ''}"] = {
                "n_firms": len(xs), "firm_mean_effect": round(obs, 4),
                "ci95_firm_bootstrap": [round(boots[50], 4), round(boots[1949], 4)],
                "p_exact_two_sided": pval, "firms_positive": sum(x > 0 for x in xs)}
    out["firm_clustered"] = firm_level

    (ROOT / "docs" / "study3" / "robustness.json").write_text(json.dumps(out, indent=1))
    for k, v in firm_level.items():
        print("FIRM", k, v)
    for k in perm:
        print(k, perm[k], "| LOMO", loo_m[k]["min"], loo_m[k]["max"], "| LOFO", loo_f[k]["min"], loo_f[k]["max"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
