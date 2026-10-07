"""Score Study 9 (docs/STUDY9_DECLARATION.md). No API call; writes docs/study9/results.json."""

from __future__ import annotations

import itertools
import json
import random
import re
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from baselines.llm import parse_response  # noqa: E402
from baselines.prompts import PROMPT_VERSION  # noqa: E402
from nofalsegreen import contracts as C  # noqa: E402
from nofalsegreen import study4, study6, study9  # noqa: E402

MODELS = [m.split("/")[-1] for m in (*study4.MODELS, *study6.MODELS)]
OFF, FORCED, EF, EX = "contract_offered", "contract_forced", "contract_evidence_first", "contract_extract"
ABSTAIN = {"needs_evidence", "unmonitored"}


def load_cache() -> dict:
    cache: dict = {}
    for vc in sorted((ROOT / "docs" / "study9" / "cache").glob("*.json")):
        cache.update(json.loads(vc.read_text()))
    idx: dict = {}
    for key, v in cache.items():
        parts = key.split("|")
        if len(parts) == 6 and parts[0] == PROMPT_VERSION:
            idx.setdefault((parts[3], parts[2]), []).append((parts[1].split("/")[-1].split("#")[0],
                                                              v.get("text", "") if isinstance(v, dict) else v))
    return idx


FACT_RE = re.compile(r"^\s*(?P<name>[^=|]+?)\s*=\s*(?P<val>[^|]*?)(?:\s+from\s+(?P<src>[^\s|]+))?\s*$")


def parse_extract(text: str, ids: set, contracts: dict, names: dict) -> dict:
    out = {}
    for raw in text.splitlines():
        line = raw.strip()
        if "::" not in line:
            continue
        pid = next((t for t in re.split(r"\t+|\s{2,}", line) if t.strip() in ids), None)
        if pid is None:
            continue
        rest = line.split(pid, 1)[1]
        rest = re.sub(r"^\s*facts\s*", "", rest.strip(), flags=re.I)
        rep = {}
        for chunk in rest.split("|"):
            m = FACT_RE.match(chunk.strip())
            if not m:
                continue
            name, val, src = m.group("name").strip(), m.group("val").strip(), m.group("src")
            if val.upper() == "ABSENT":
                rep[name] = "ABSENT"
            elif val.upper() == "CONFLICT":
                rep[name] = "CONFLICT"
            elif src:
                rep[name] = (val, src)
        c = contracts[pid.split("::")[0]]
        out[pid] = C.verdict_from_facts(c, rep, names)
    return out


def exact(per: dict, seed: int) -> dict:
    keys = sorted(per)
    xs = [per[k] for k in keys]
    obs = sum(xs) / len(xs)
    n = len(xs)
    if n <= 20:
        pats = itertools.product((1, -1), repeat=n)
        vals = [abs(sum(s * x for s, x in zip(sg, xs)) / n) for sg in pats]
    else:
        rng = random.Random(seed)
        vals = [abs(sum(rng.choice((1, -1)) * x for x in xs) / n) for _ in range(200000)]
    p = sum(v >= abs(obs) - 1e-12 for v in vals) / len(vals)
    rng = random.Random(seed)
    boots = sorted(sum(per[k] for k in d) / n for d in ([rng.choice(keys) for _ in keys] for _ in range(2000)))
    return {"n_packets": n, "delta": round(obs, 4), "ci95_packet_bootstrap": [round(boots[50], 4), round(boots[1949], 4)],
            "p_exact_two_sided": p, "packets_positive": sum(x > 0 for x in xs), "packets_negative": sum(x < 0 for x in xs)}


def main() -> int:
    idx = load_cache()
    contracts = C.CONTRACTS
    # ---------------- collect predictions: (model, part, wf, seed, rendering, variant) -> {pair: verdict}
    pred, labels = {}, {}
    for part, seeds in (("A", study9.A_SEEDS), ("B", study9.B_SEEDS)):
        for wf in study9.WORKFLOWS:
            for fam in ((True, False) if part == "A" else (True,)):
                names = C.names_for(wf, fam)
                for s in seeds:
                    f = study9.firm(part, wf, s, fam)
                    ids = {p.pair_id for p in f.pairs}
                    for l in f.labels:
                        labels[(part, wf, s, l.pair_id)] = l.verdict.value
                    variants = (OFF, FORCED) if part == "A" else (OFF, EF, EX)
                    for var in variants:
                        for m, text in idx.get((f.firm_id, var), []):
                            d = pred.setdefault((m, part, wf, s, fam, var), {})
                            if var == EX:
                                d.update(parse_extract(text, ids, contracts, names))
                            else:
                                for p in parse_response(text, sorted(ids), var)[0]:
                                    d[p.pair_id] = p.verdict.value
    out: dict = {"declared": "docs/STUDY9_DECLARATION.md"}

    # ---------------- Part A
    def per_packet(metric, wfs=study9.WORKFLOWS, models=MODELS):
        res = {}
        for wf in wfs:
            for s in study9.A_SEEDS:
                vals = []
                for m in models:
                    v = metric(m, wf, s)
                    if v is not None:
                        vals.append(v)
                if vals:
                    res[f"{wf}-{s}"] = sum(vals) / len(vals)
        return res

    def rate(m, wf, s, fam, var, want, on):
        d = pred.get((m, "A", wf, s, fam, var), {})
        ks = [pid for (pt, w, sd, pid), lab in labels.items() if pt == "A" and w == wf and sd == s and on(lab) and pid in d]
        return (sum(want(d[k]) for k in ks) / len(ks)) if ks else None

    def diff(m, wf, s, var, want, on, a=True, b=False):
        x, y = rate(m, wf, s, a, var, want, on), rate(m, wf, s, b, var, want, on)
        return None if x is None or y is None else x - y

    def paired(m, wf, s, var, want, on, a, b):
        """paired on pairs answered under both renderings"""
        da, db = pred.get((m, "A", wf, s, a, var), {}), pred.get((m, "A", wf, s, b, var), {})
        ks = [pid for (pt, w, sd, pid), lab in labels.items() if pt == "A" and w == wf and sd == s and on(lab)
              and pid in da and pid in db]
        return (sum(want(da[k]) - want(db[k]) for k in ks) / len(ks)) if ks else None

    fg = lambda v: float(v == "pass")  # noqa: E731
    ab = lambda v: float(v in ABSTAIN)  # noqa: E731
    U = lambda lab: lab == "needs_evidence"  # noqa: E731
    D = lambda lab: lab in ("pass", "fail")  # noqa: E731
    p1 = per_packet(lambda m, wf, s: paired(m, wf, s, OFF, fg, U, True, False))
    p2 = per_packet(lambda m, wf, s: paired(m, wf, s, OFF, ab, D, False, True))

    def p3m(m, wf, s):
        a = paired(m, wf, s, FORCED, fg, U, True, False)
        b = paired(m, wf, s, OFF, fg, U, True, False)
        return None if a is None or b is None else a - b
    p3 = per_packet(p3m)
    prim = {"P1 familiar - neutral unsupported positives, offered": exact(p1, 9101),
            "P2 neutral - familiar abstention on decidable pairs, offered": exact(p2, 9102),
            "P3 forced minus offered familiarity effect on unsupported positives": exact(p3, 9103)}
    for wf in ("purchasing", "engineering"):
        prim[f"P4 P1 on held-out workflow: {wf}"] = exact(
            per_packet(lambda m, w, s: paired(m, w, s, OFF, fg, U, True, False), wfs=(wf,)), 9104)
    # ---------------- Part B
    def metrics(get):
        """get(m, wf, s) -> {pair: verdict}; returns per-packet dicts of each metric (mean over models)."""
        res = {k: {} for k in ("unsupported_pos", "unsupported_neg", "correct_determinate", "coverage",
                                "unnecessary_abstention", "review_burden")}
        for wf in study9.WORKFLOWS:
            for s in study9.B_SEEDS:
                acc = {k: [] for k in res}
                for m in MODELS:
                    d = get(m, wf, s)
                    if d is None:
                        continue
                    labs = {pid: lab for (pt, w, sd, pid), lab in labels.items() if pt == "B" and w == wf and sd == s}
                    n = len(labs)
                    nd = sum(1 for v in labs.values() if v != "needs_evidence")
                    acc["unsupported_pos"].append(sum(d.get(k) == "pass" and v != "pass" for k, v in labs.items()) / n)
                    acc["unsupported_neg"].append(sum(d.get(k) == "fail" and v != "fail" for k, v in labs.items()) / n)
                    acc["correct_determinate"].append(sum(d.get(k) == v for k, v in labs.items() if v != "needs_evidence") / max(1, nd))
                    acc["coverage"].append(sum(k in d for k in labs) / n)
                    acc["unnecessary_abstention"].append(sum(d.get(k) in ABSTAIN for k, v in labs.items() if v != "needs_evidence") / max(1, nd))
                    acc["review_burden"].append(sum(d.get(k) in ABSTAIN for k in labs) / n)
                for k in res:
                    if acc[k]:
                        res[k][f"{wf}-{s}"] = sum(acc[k]) / len(acc[k])
        return res

    canon = {}
    for wf in study9.WORKFLOWS:
        for s in study9.B_SEEDS:
            canon[(wf, s)] = study9.packet("B", wf, s)

    def gate(base):
        def g(m, wf, s):
            d = base(m, wf, s)
            if d is None:
                return None
            p = canon[(wf, s)]
            out_ = {}
            for k, v in d.items():
                rule, e = k.split("::", 1)
                missing = any(C._resolve(f, p.tables, e)[0] == "unknown" for f in contracts[rule].facts)
                out_[k] = "needs_evidence" if missing else v
            return out_
        return g

    getters = {
        "offered prompt": lambda m, wf, s: pred.get((m, "B", wf, s, True, OFF)),
        "evidence-first prompt": lambda m, wf, s: pred.get((m, "B", wf, s, True, EF)),
        "extraction + solver": lambda m, wf, s: pred.get((m, "B", wf, s, True, EX)),
        "presence gate + offered prompt": gate(lambda m, wf, s: pred.get((m, "B", wf, s, True, OFF))),
        "presence gate + evidence-first prompt": gate(lambda m, wf, s: pred.get((m, "B", wf, s, True, EF))),
        "always abstain": lambda m, wf, s: {pid: "needs_evidence" for (pt, w, sd, pid) in labels if pt == "B" and w == wf and sd == s},
    }
    met = {name: metrics(g) for name, g in getters.items()}
    out["partB_metrics"] = {name: {k: round(sum(v.values()) / len(v), 4) if v else None for k, v in mm.items()}
                            for name, mm in met.items()}

    def dpk(a, b, k):
        A, B = met[a][k], met[b][k]
        return {x: A[x] - B[x] for x in A if x in B}
    prim["I1 unsupported positives: extraction+solver - evidence-first"] = exact(dpk("extraction + solver", "evidence-first prompt", "unsupported_pos"), 9201)
    prim["I2 correct determinate: extraction+solver - evidence-first"] = exact(dpk("extraction + solver", "evidence-first prompt", "correct_determinate"), 9202)
    prim["I3 correct determinate: extraction+solver - presence gate + evidence-first"] = exact(
        dpk("extraction + solver", "presence gate + evidence-first prompt", "correct_determinate"), 9203)
    ps = {k: v["p_exact_two_sided"] for k, v in prim.items()}
    run = 0.0
    for i, k in enumerate(sorted(ps, key=ps.get)):
        run = max(run, min(1.0, (len(ps) - i) * ps[k]))
        prim[k]["p_holm"] = run
        prim[k]["outcome"] = "confirmed" if run < 0.05 else "not confirmed"
    out["primary"] = prim

    # ---------------- descriptive
    out["partA_rates"] = {}
    for m in MODELS:
        for fam in (True, False):
            for var in (OFF, FORCED):
                vals_u, vals_d = [], []
                for wf in study9.WORKFLOWS:
                    for s in study9.A_SEEDS:
                        u = rate(m, wf, s, fam, var, fg, U)
                        d_ = rate(m, wf, s, fam, var, ab, D)
                        if u is not None:
                            vals_u.append(u)
                        if d_ is not None:
                            vals_d.append(d_)
                out["partA_rates"][f"{m}::{'familiar' if fam else 'neutral'}::{var}"] = {
                    "unsupported_pos_on_unassessable": round(sum(vals_u) / len(vals_u), 4) if vals_u else None,
                    "abstention_on_decidable": round(sum(vals_d) / len(vals_d), 4) if vals_d else None}
    out["partA_per_model"] = {
        "P1": {m: (lambda r: round(sum(r.values()) / len(r), 4) if r else None)(per_packet(lambda mm, wf, s: paired(mm, wf, s, OFF, fg, U, True, False), models=[m])) for m in MODELS},
        "P2": {m: (lambda r: round(sum(r.values()) / len(r), 4) if r else None)(per_packet(lambda mm, wf, s: paired(mm, wf, s, OFF, ab, D, False, True), models=[m])) for m in MODELS}}
    out["partB_per_model"] = {name: {m: {k: round(sum(v.values()) / len(v), 4) if v else None
                                         for k, v in (lambda g: {kk: {x: y for x, y in vv.items()} for kk, vv in metrics(lambda mm, wf, s, g=g, m=m: g(m, wf, s) if mm == MODELS[0] else None).items()})(g).items()}
                                     for m in MODELS} for name, g in getters.items() if name != "always abstain"}
    pats = Counter()
    for wf in study9.WORKFLOWS:
        for s in study9.B_SEEDS:
            p = canon[(wf, s)]
            for e, (pat, rule) in p.patterns.items():
                pats[pat] += 1
    out["partB_pattern_counts"] = dict(pats)
    out["label_counts"] = {part: dict(Counter(v for (pt, *_), v in labels.items() if pt == part)) for part in ("A", "B")}
    out["coverage_answered"] = {f"{k[0]}::{k[1]}::{k[2]}::{k[4]}::{k[5]}": len(v) for k, v in pred.items()}
    (ROOT / "docs" / "study9").mkdir(exist_ok=True)
    (ROOT / "docs" / "study9" / "results.json").write_text(json.dumps(out, indent=1, default=str))
    for k, v in prim.items():
        print(k, v)
    print(json.dumps(out["partB_metrics"], indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
