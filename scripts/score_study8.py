"""Score Study 8 (docs/STUDY8_DECLARATION.md). No API call; writes docs/study8/results.json."""

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
from nofalsegreen import study4, study5, study6, study8  # noqa: E402
from nofalsegreen.rulebook import Rulebook  # noqa: E402

OFF, DASH = "abstain_offered", "abstain_withheld"
MODELS = [m.split("/")[-1] for m in (*study4.MODELS, *study6.MODELS)]
RUNS = ("r0", "r1")


def load(cache_dirs, firms_by_arm):
    cache: dict = {}
    for d in cache_dirs:
        for vc in sorted(d.glob("*.json")):
            cache.update(json.loads(vc.read_text()))
    idx: dict = {}
    for key, v in cache.items():
        parts = key.split("|")
        if len(parts) == 6 and parts[0] == PROMPT_VERSION:
            idx.setdefault(parts[3], []).append((parts[1], parts[2], v))
    preds: dict = {}  # (model, run, arm, variant) -> {seed|pair: verdict}
    for arm, fs in firms_by_arm.items():
        for f in fs:
            ids = [p.pair_id for p in f.pairs]
            for prov, var, v in idx.get(f.firm_id, []):
                model, run = prov.split("#")
                for p in parse_response(v.get("text", "") if isinstance(v, dict) else v, ids, var)[0]:
                    preds.setdefault((model.split("/")[-1], run, arm, var), {})[f"{f.provenance['seed']}|{p.pair_id}"] = p.verdict.value
    return preds


def exact(per_firm: dict, seed: int) -> dict:
    fids = sorted(per_firm)
    xs = [per_firm[f] for f in fids]
    obs = sum(xs) / len(xs)
    perm = [abs(sum(s * x for s, x in zip(sg, xs)) / len(xs)) for sg in itertools.product((1, -1), repeat=len(xs))]
    p = sum(v >= abs(obs) - 1e-12 for v in perm) / len(perm)
    rng = random.Random(seed)
    boots = sorted(sum(per_firm[f] for f in d) / len(d) for d in ([rng.choice(fids) for _ in fids] for _ in range(2000)))
    return {"n_firms": len(xs), "delta": round(obs, 4), "ci95_firm_bootstrap": [round(boots[50], 4), round(boots[1949], 4)],
            "p_exact_two_sided": p, "firms_positive": sum(x > 0 for x in xs), "firms_negative": sum(x < 0 for x in xs)}


def main() -> int:
    rb = Rulebook.load(ROOT / "rulebook" / "rulebook.json")
    out: dict = {"declared": "docs/STUDY8_DECLARATION.md"}
    # ---- part A: fresh firms, two runs
    fa = {a: study8.load_firms(rb, a) for a in study8.ARMS}
    pa = load([ROOT / "docs" / "study8" / "cache"], fa)
    lab = {f"{f.provenance['seed']}|{l.pair_id}": l.verdict.value for f in fa["plain"] for l in f.labels}
    unass = [k for k, v in lab.items() if v == "needs_evidence"]
    seeds = [str(s) for s in study8.SEEDS]

    def fd(b, a, runs=RUNS, models=MODELS):
        res = {}
        for fs in seeds:
            per = []
            for m in models:
                for r in runs:
                    db, da = pa.get((m, r, *b), {}), pa.get((m, r, *a), {})
                    ks = [k for k in unass if k.startswith(fs + "|") and k in db and k in da]
                    if ks:
                        per.append(sum((db[k] == "pass") - (da[k] == "pass") for k in ks) / len(ks))
            if per:
                res[fs] = sum(per) / len(per)
        return res

    specs = {"F1 proxy - plain, offered": (("proxy", OFF), ("plain", OFF)),
             "F2 proxy - irrelevant, offered": (("proxy", OFF), ("irrelevant", OFF)),
             "F3 dashboard - offered, proxy firms": (("proxy", DASH), ("proxy", OFF)),
             "F4 renamed - plain, dashboard": (("renamed", DASH), ("plain", DASH))}
    prim = {k: exact(fd(*v), 20261007) for k, v in specs.items()}
    # per model and per run, descriptive
    out["fresh_per_model"] = {k: {m: round(sum(fd(*v, models=[m]).values()) / max(1, len(fd(*v, models=[m]))), 4)
                                  for m in MODELS} for k, v in specs.items()}
    out["fresh_per_run"] = {k: {r: round(sum(fd(*v, runs=[r]).values()) / max(1, len(fd(*v, runs=[r]))), 4)
                                for r in RUNS} for k, v in specs.items()}
    out["fresh_names_descriptive"] = {"proxy - renamed, offered, per model":
                                      {m: round(sum(fd(("proxy", OFF), ("renamed", OFF), models=[m]).values()) / 10, 4) for m in MODELS}}
    out["fresh_coverage_min"] = min(len([k for k in unass if k in d]) for d in pa.values()) if pa else None
    out["fresh_n_unassessable"] = len(unass)

    # ---- part B: real-LCA wage controls
    fb = {a: study5.build(a) for a in ("lca_only", "pay_rate_only", *study5.STUDY8_ARMS)}
    pb = load([ROOT / "docs" / d / "cache" for d in ("study5", "study6", "study7", "study8")], fb)
    labb = {f"{f.provenance['seed']}|{l.pair_id}": l for f in fb["complete_actual_above"] for l in f.labels}
    keys5 = sorted({k for (m, r, a, v), d in pb.items() if a == "lca_only" for k in d})
    fids = [str(i) for i in range(1, study5.N_FIRMS + 1)]

    def fd5(b, a):
        res = {}
        for fs in fids:
            per = []
            for m in MODELS:
                db, da = pb.get((m, "r0", b, OFF), {}), pb.get((m, "r0", a, OFF), {})
                ks = [k for k in keys5 if k.startswith(fs + "|") and k in db and k in da]
                if ks:
                    per.append(sum((db[k] == "pass") - (da[k] == "pass") for k in ks) / len(ks))
            if per:
                res[fs] = sum(per) / len(per)
        return res
    prim["G1 Pay Rate (7% above the LCA wage) - LCA only"] = exact(fd5("pay_rate_shifted", "lca_only"), 20261008)

    def recall_gap():
        res = {}
        for fs in fids:
            per = []
            for m in MODELS:
                d = pb.get((m, "r0", "complete_actual_above", OFF), {})
                below = [k for k, l in labb.items() if k.startswith(fs + "|") and l.note == "below_offered"]
                gof = [k for k, l in labb.items() if k.startswith(fs + "|") and l.note == "greater_of_only"]
                if below and gof and d:
                    rb_ = sum(d.get(k) == "fail" for k in below) / len(below)
                    rg_ = sum(d.get(k) == "fail" for k in gof) / len(gof)
                    per.append(rb_ - rg_)
            if per:
                res[fs] = sum(per) / len(per)
        return res
    prim["G2 recall: below the offered wage - greater-of only"] = exact(recall_gap(), 20261009)
    ps = {k: v["p_exact_two_sided"] for k, v in prim.items()}
    run = 0.0
    for i, k in enumerate(sorted(ps, key=ps.get)):
        run = max(run, min(1.0, (len(ps) - i) * ps[k]))
        prim[k]["p_holm"] = run
        prim[k]["outcome"] = "confirmed" if run < 0.05 else "not confirmed"
    out["primary"] = prim

    rec = {}
    for m in MODELS:
        d = pb.get((m, "r0", "complete_actual_above", OFF), {})
        for kind in ("below_offered", "greater_of_only"):
            ks = [k for k, l in labb.items() if l.note == kind]
            rec[f"{m}::{kind}"] = round(sum(d.get(k) == "fail" for k in ks) / len(ks), 4)
        ok = [k for k, l in labb.items() if l.verdict.value == "pass"]
        rec[f"{m}::false_alarm"] = round(sum(k in d and d[k] != "pass" for k in ok) / len(ok), 4)
        rec[f"{m}::answered"] = len(d)
    out["greater_of_recall"] = rec
    out["pay_rate_shifted_per_model"] = {m: round(sum(v == "pass" for v in pb.get((m, "r0", "pay_rate_shifted", OFF), {}).values()) / 120, 4)
                                         for m in MODELS}
    (ROOT / "docs" / "study8").mkdir(exist_ok=True)
    (ROOT / "docs" / "study8" / "results.json").write_text(json.dumps(out, indent=1))
    for k, v in prim.items():
        print(k, v)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
