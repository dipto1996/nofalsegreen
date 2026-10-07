"""Score Study 5 (docs/STUDY5_DECLARATION.md). No API call; writes docs/study5/results.json."""

from __future__ import annotations

import itertools
import json
import random
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from baselines.llm import parse_response  # noqa: E402
from baselines.prompts import PROMPT_VERSION  # noqa: E402
from nofalsegreen import study4, study5  # noqa: E402

OFF, DASH = "abstain_offered", "abstain_withheld"
STUDY6 = "--study6" in sys.argv  # same declared analysis on the Study 6 models
if STUDY6:
    from nofalsegreen import study6  # noqa: E402
MODELS = [m.split("/")[-1] for m in (study6.MODELS if STUDY6 else study4.MODELS)]


def main() -> int:
    cache: dict = {}
    for vc in sorted((ROOT / "docs" / ("study6" if STUDY6 else "study5") / "cache").glob("*.json")):
        cache.update(json.loads(vc.read_text()))
    firms = {a: study5.build(a) for a in study5.ARMS}
    preds: dict = {}  # (model, arm, cond) -> {firm|pair: Prediction}
    for arm, fs in firms.items():
        for f in fs:
            ids = [p.pair_id for p in f.pairs]
            for key, v in cache.items():
                parts = key.split("|")
                if len(parts) != 6 or parts[0] != PROMPT_VERSION or parts[3] != f.firm_id:
                    continue
                m = parts[1].split("/")[-1].split("#")[0]
                for p in parse_response(v.get("text", "") if isinstance(v, dict) else v, ids, parts[2])[0]:
                    preds.setdefault((m, arm, parts[2]), {})[f"{f.provenance['seed']}|{p.pair_id}"] = p
    labels = {a: {f"{f.provenance['seed']}|{l.pair_id}": l.verdict.value for f in fs for l in f.labels}
              for a, fs in firms.items()}
    fids = [str(i) for i in range(1, study5.N_FIRMS + 1)]
    signs = list(itertools.product((1, -1), repeat=len(fids)))
    rng = random.Random(study5.SEED)
    draws = [[rng.choice(fids) for _ in fids] for _ in range(2000)]

    def firm_diff(b, a, outcome="pass"):
        out = {}
        for fs in fids:
            per = []
            for m in MODELS:
                db, da = preds.get((m, *b), {}), preds.get((m, *a), {})
                ks = [k for k in labels["lca_only"] if k.startswith(fs + "|") and k in db and k in da]
                if ks:
                    per.append(sum(float(db[k].verdict.value == outcome) - float(da[k].verdict.value == outcome)
                                   for k in ks) / len(ks))
            if per:
                out[fs] = sum(per) / len(per)
        return out

    def test(pf):
        if not pf:
            return {"n_firms": 0}
        xs = list(pf.values())
        obs = sum(xs) / len(xs)
        perm = [abs(sum(s * x for s, x in zip(sg, xs)) / len(xs)) for sg in signs[: 2 ** len(xs)]]
        p = sum(v >= abs(obs) - 1e-12 for v in perm) / len(perm)
        boots = sorted(sum(pf[f] for f in d if f in pf) / max(1, sum(f in pf for f in d)) for d in draws)
        return {"n_firms": len(xs), "delta": round(obs, 4), "ci95_firm_bootstrap": [round(boots[50], 4),
                round(boots[1949], 4)], "p_exact_two_sided": p, "firms_positive": sum(x > 0 for x in xs),
                "firms_negative": sum(x < 0 for x in xs)}

    out: dict = {"declared": "docs/STUDY5_DECLARATION.md", "primary": {
        "R1 salary of record, offered": test(firm_diff(("salary", OFF), ("lca_only", OFF))),
        "R2 salary of record, dashboard": test(firm_diff(("salary", DASH), ("lca_only", DASH))),
        "R3 dashboard - offered, LCA only": test(firm_diff(("lca_only", DASH), ("lca_only", OFF))),
    }}
    ps = {k: v["p_exact_two_sided"] for k, v in out["primary"].items() if "p_exact_two_sided" in v}
    run = 0.0
    for i, k in enumerate(sorted(ps, key=ps.get)):
        run = max(run, min(1.0, (len(ps) - i) * ps[k]))
        out["primary"][k]["p_holm"] = run
        out["primary"][k]["outcome"] = "confirmed" if run < 0.05 else "not confirmed"

    def pm(b, a, m, outcome="pass"):
        db, da = preds.get((m, *b), {}), preds.get((m, *a), {})
        ks = [k for k in labels["lca_only"] if k in db and k in da]
        return round(sum(float(db[k].verdict.value == outcome) - float(da[k].verdict.value == outcome)
                         for k in ks) / len(ks), 4) if ks else None
    out["per_model_primary_posthoc"] = {
        "R1": {m: pm(("salary", OFF), ("lca_only", OFF), m) for m in MODELS},
        "R2": {m: pm(("salary", DASH), ("lca_only", DASH), m) for m in MODELS},
        "R3": {m: pm(("lca_only", DASH), ("lca_only", OFF), m) for m in MODELS}}

    cells = {}
    for (m, arm, cond), d in sorted(preds.items()):
        lab = labels[arm]
        cnt = Counter(d[k].verdict.value for k in lab if k in d)
        n = len(lab)
        row = {"n": n, "answered": sum(cnt.values()), "allocation": dict(cnt)}
        if arm == "complete":
            vio = [k for k, v in lab.items() if v == "fail"]
            ok = [k for k, v in lab.items() if v == "pass"]
            row["recall_all_pairs"] = round(sum(k in d and d[k].verdict.value == "fail" for k in vio) / len(vio), 4)
            row["false_alarm_all_pairs"] = round(sum(k in d and d[k].verdict.value != "pass" for k in ok) / len(ok), 4)
        else:
            row["fgr_all_pairs"] = round(cnt["pass"] / n, 4)
            row["fgr_answered"] = round(cnt["pass"] / max(1, sum(cnt.values())), 4)
            ev = Counter()
            for k in lab:
                if k in d and d[k].verdict.value == "pass":
                    e = " ".join(d[k].evidence_fields).lower()
                    ev["pay rate (salary of record)" if "pay rate" in e or "pay_rate" in e else
                       "LCA offered wage" if "wage_rate_of_pay" in e else
                       "prevailing wage" if "prevailing" in e else "other"] += 1
            row["false_green_cites"] = dict(ev)
        cells[f"{m}::{arm}::{cond}"] = row
    out["cells"] = cells
    for arm in study5.ARMS:
        for cond in (OFF, DASH):
            rs = [cells.get(f"{m}::{arm}::{cond}") for m in MODELS]
            rs = [r for r in rs if r]
            if rs and arm != "complete":
                out.setdefault("means", {})[f"{arm}::{cond}"] = round(sum(r["fgr_all_pairs"] for r in rs) / len(rs), 4)
    (ROOT / "docs" / "study5").mkdir(exist_ok=True)
    (ROOT / "docs" / ("study6/study5_results.json" if STUDY6 else "study5/results.json")).write_text(json.dumps(out, indent=1))
    for k, v in out["primary"].items():
        print(k, v)
    print(out.get("means"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
