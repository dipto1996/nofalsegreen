"""Score Study 7 (docs/STUDY7_DECLARATION.md). No API call; writes docs/study7/results.json.

The Study 5 real-LCA firms with the salary arm's pay fields taken apart, offered schema,
five models (the three Google models and the two Study 6 models). Baseline cells
(lca_only, salary) are the retained Study 5 and Study 6 replies.
"""

from __future__ import annotations

import itertools
import json
import random
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from baselines.llm import parse_response  # noqa: E402
from baselines.prompts import PROMPT_VERSION  # noqa: E402
from nofalsegreen import study4, study5, study6  # noqa: E402

OFF = "abstain_offered"
MODELS = [m.split("/")[-1] for m in (*study4.MODELS, *study6.MODELS)]
ARMS = ("lca_only", "salary", *study5.STUDY7_ARMS)
CACHES = [ROOT / "docs" / d / "cache" for d in ("study5", "study6", "study7")]


def main() -> int:
    cache: dict = {}
    for d in CACHES:
        for vc in sorted(d.glob("*.json")):
            cache.update(json.loads(vc.read_text()))
    preds: dict = {}
    for arm in ARMS:
        for f in study5.build(arm):
            ids = [p.pair_id for p in f.pairs]
            for key, v in cache.items():
                parts = key.split("|")
                if len(parts) != 6 or parts[0] != PROMPT_VERSION or parts[3] != f.firm_id or parts[2] != OFF:
                    continue
                m = parts[1].split("/")[-1].split("#")[0]
                for p in parse_response(v.get("text", "") if isinstance(v, dict) else v, ids, OFF)[0]:
                    preds.setdefault((m, arm), {})[f"{f.provenance['seed']}|{p.pair_id}"] = p.verdict.value
    keys = sorted({k for d in preds.values() for k in d})
    fids = [str(i) for i in range(1, study5.N_FIRMS + 1)]
    signs = list(itertools.product((1, -1), repeat=len(fids)))
    rng = random.Random(20261007)
    draws = [[rng.choice(fids) for _ in fids] for _ in range(2000)]

    def per_model(b, a, m):
        db, da = preds.get((m, b), {}), preds.get((m, a), {})
        ks = [k for k in keys if k in db and k in da]
        return round(sum((db[k] == "pass") - (da[k] == "pass") for k in ks) / len(ks), 4) if ks else None

    def firm_diff(b, a):
        out = {}
        for fs in fids:
            per = []
            for m in MODELS:
                db, da = preds.get((m, b), {}), preds.get((m, a), {})
                ks = [k for k in keys if k.startswith(fs + "|") and k in db and k in da]
                if ks:
                    per.append(sum((db[k] == "pass") - (da[k] == "pass") for k in ks) / len(ks))
            if per:
                out[fs] = sum(per) / len(per)
        return out

    def test(pf):
        xs = list(pf.values())
        obs = sum(xs) / len(xs)
        perm = [abs(sum(s * x for s, x in zip(sg, xs)) / len(xs)) for sg in signs[: 2 ** len(xs)]]
        p = sum(v >= abs(obs) - 1e-12 for v in perm) / len(perm)
        boots = sorted(sum(pf[f] for f in d if f in pf) / max(1, sum(f in pf for f in d)) for d in draws)
        return {"n_firms": len(xs), "delta": round(obs, 4), "ci95_firm_bootstrap": [round(boots[50], 4), round(boots[1949], 4)],
                "p_exact_two_sided": p, "firms_positive": sum(x > 0 for x in xs), "firms_negative": sum(x < 0 for x in xs)}

    out = {"declared": "docs/STUDY7_DECLARATION.md", "primary": {
        "W1 Pay Rate alone - LCA only": test(firm_diff("pay_rate_only", "lca_only")),
        "W2 Pay Type and Schedule alone - LCA only": test(firm_diff("pay_context_only", "lca_only")),
    }}
    ps = {k: v["p_exact_two_sided"] for k, v in out["primary"].items()}
    run = 0.0
    for i, k in enumerate(sorted(ps, key=ps.get)):
        run = max(run, min(1.0, (len(ps) - i) * ps[k]))
        out["primary"][k]["p_holm"] = run
        out["primary"][k]["outcome"] = "confirmed" if run < 0.05 else "not confirmed"
    out["per_model"] = {f"{b} - {a}": {m: per_model(b, a, m) for m in MODELS}
                        for b, a in (("pay_rate_only", "lca_only"), ("pay_context_only", "lca_only"),
                                     ("salary", "lca_only"), ("salary", "pay_rate_only"))}
    # post hoc diagnostic: the same estimator restricted to Study 5's three Google models
    google = [m.split("/")[-1] for m in study4.MODELS]

    def firm_diff_models(b, a, models):
        res = {}
        for fs in fids:
            per = []
            for m in models:
                db, da = preds.get((m, b), {}), preds.get((m, a), {})
                ks = [k for k in keys if k.startswith(fs + "|") and k in db and k in da]
                if ks:
                    per.append(sum((db[k] == "pass") - (da[k] == "pass") for k in ks) / len(ks))
            if per:
                res[fs] = sum(per) / len(per)
        return round(sum(res.values()) / len(res), 4) if res else None
    out["google_only_posthoc"] = {"pay_rate_only - lca_only": firm_diff_models("pay_rate_only", "lca_only", google),
                                  "salary - lca_only": firm_diff_models("salary", "lca_only", google)}
    out["answered"] = {f"{m}::{a}": len(preds.get((m, a), {})) for m in MODELS for a in ARMS}
    out["fgr_all_pairs"] = {f"{m}::{a}": round(sum(v == "pass" for v in preds.get((m, a), {}).values()) / 120, 4)
                            for m in MODELS for a in ARMS}
    (ROOT / "docs" / "study7").mkdir(exist_ok=True)
    (ROOT / "docs" / "study7" / "results.json").write_text(json.dumps(out, indent=1))
    for k, v in out["primary"].items():
        print(k, v)
    print(json.dumps(out["per_model"], indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
