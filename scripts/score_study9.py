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


def _slots(text: str, ids: set) -> dict:
    """pair -> {fact name: ('value', raw, src) | 'ABSENT' | 'CONFLICT'} as the reply states them."""
    out: dict = {}
    for raw in text.splitlines():
        line = raw.strip()
        pid = next((t for t in re.split(r"\t+|\s{2,}", line) if t.strip() in ids), None) if "::" in line else None
        if pid is None or pid in out:
            continue
        rep = {}
        for chunk in re.sub(r"^\s*facts\s*", "", line.split(pid, 1)[1].strip(), flags=re.I).split("|"):
            m = FACT_RE.match(chunk.strip())
            if m:
                v = m.group("val").strip()
                rep[m.group("name").strip()] = v.upper() if v.upper() in ("ABSENT", "CONFLICT") else \
                    ("value", v, m.group("src")) if m.group("src") else None
        out[pid] = rep
    return out


def slot_audit(idx: dict, canon: dict, contracts: dict, labels: dict) -> dict:
    """Every required fact slot in every retained extraction reply (Part B), against the record.

    Record status per slot is the contract's resolution: a value, absent, or conflicting. A
    reported value is correct only if it equals the resolved value AND the cited column holds
    that value for that entity (provenance). Everything else is counted as its failure mode,
    including slots the reply omitted."""
    tally: dict = {}
    pairs = {"with_slot_error": 0, "with_slot_error_and_wrong_verdict": 0, "total": 0}
    for wf in study9.WORKFLOWS:
        for s_ in study9.B_SEEDS:
            p_ = canon[(wf, s_)]
            f_ = study9.firm("B", wf, s_, True)
            ids = {pr.pair_id for pr in f_.pairs}
            replies: dict = {}  # a model's replies for one packet each cover a shard of its pairs
            for m, text in idx.get((f_.firm_id, EX), []):
                replies.setdefault(m, []).append(text)
            for m, texts in sorted(replies.items()):
                rep_all, verdicts = {}, {}
                for text in texts:
                    for k, v in _slots(text, ids).items():
                        rep_all.setdefault(k, v)
                    for k, v in parse_extract(text, ids, contracts, {}).items():
                        verdicts.setdefault(k, v)
                for pid in sorted(ids):
                    rule, e = pid.split("::", 1)
                    c, rep, err = contracts[rule], rep_all.get(pid, {}), False
                    for fact in c.facts:
                        st, val = C._resolve(fact, p_.tables, e)
                        r = rep.get(fact.name)
                        if r is None:
                            out_ = "omitted or unparseable"
                        elif r == "ABSENT":
                            out_ = "ABSENT"
                        elif r == "CONFLICT":
                            out_ = "CONFLICT"
                        else:
                            _, v, src = r
                            try:
                                got = float(v.replace(",", "").replace("$", "")) if fact.kind == "amount" else C._d(v)
                            except ValueError:
                                got = None
                            t_, _, col = src.strip().strip("`").partition(".")
                            allowed = {(x.table, x.column) for x in fact.sources}
                            holds = (t_, col) in allowed and any(
                                rr.get(fact.sources[0].key if (t_, col) == (fact.sources[0].table, fact.sources[0].column)
                                       else next(x.key for x in fact.sources if (x.table, x.column) == (t_, col))) == e
                                and rr.get(col) not in (None, "")
                                and (float(rr[col]) if fact.kind == "amount" else C._d(rr[col])) == got
                                for rr in p_.tables.get(t_, []))
                            out_ = ("value, correct, cited column holds it" if st == "known" and got == val and holds
                                    else "value, correct, cited column does not hold it" if st == "known" and got == val
                                    else "value, wrong")
                        ok = (st, out_) in {("known", "value, correct, cited column holds it"),
                                            ("unknown", "ABSENT"), ("conflict", "CONFLICT")}
                        err |= not ok
                        tally.setdefault(m, Counter())[f"{st}: {out_}"] += 1
                    pairs["total"] += 1
                    if err:
                        pairs["with_slot_error"] += 1
                        if verdicts.get(pid) != labels[("B", wf, s_, pid)]:
                            pairs["with_slot_error_and_wrong_verdict"] += 1
    pooled = Counter()
    for t in tally.values():
        pooled.update(t)

    def summary(t):
        by = {st: sum(v for k, v in t.items() if k.startswith(st + ":")) for st in ("known", "unknown", "conflict")}
        good = {"known": t["known: value, correct, cited column holds it"], "unknown": t["unknown: ABSENT"],
                "conflict": t["conflict: CONFLICT"]}
        return {"slots": sum(by.values()), "correct": sum(good.values()),
                **{f"{st}_slots": by[st] for st in by}, **{f"{st}_correct": good[st] for st in by}}
    return {"pooled": {**summary(pooled), "outcomes": dict(sorted(pooled.items()))},
            "per_model": {m: summary(t) for m, t in sorted(tally.items())}, "pairs": pairs}


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
    def metrics(get, models=MODELS):
        """get(m, wf, s) -> {pair: verdict}; returns per-packet dicts of each metric (mean over models)."""
        res = {k: {} for k in ("unsupported_pos", "unsupported_neg", "correct_determinate", "coverage",
                                "unnecessary_abstention", "review_burden", "followup_share")}
        for wf in study9.WORKFLOWS:
            for s in study9.B_SEEDS:
                acc = {k: [] for k in res}
                for m in models:
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
                    # every item a person must look at: abstentions, fails and unanswered items
                    acc["followup_share"].append(sum(d.get(k) in ABSTAIN or d.get(k) == "fail" or k not in d for k in labs) / n)
                for k in res:
                    if acc[k]:
                        res[k][f"{wf}-{s}"] = sum(acc[k]) / len(acc[k])
        return res

    sys.path.insert(0, str(ROOT / "labelcheck"))
    from contract_checker import check as _independent  # noqa: E402
    import tempfile as _tf
    _detcache: dict = {}

    def _det(wf, s):
        """The independent checker applied directly to the packet: a program reading the named columns."""
        if (wf, s) not in _detcache:
            d = Path(_tf.mkdtemp())
            C.write_canonical(canon[(wf, s)], d)
            _detcache[(wf, s)] = _independent(wf, str(d))
        return _detcache[(wf, s)]

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
        "deterministic reading of named columns": lambda m, wf, s: _det(wf, s),
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
    out["partB_per_model"] = {name: {m: {k: (round(sum(v.values()) / len(v), 4) if v else None)
                                         for k, v in metrics(g, models=[m]).items()} for m in MODELS}
                               for name, g in getters.items() if name not in ("always abstain", "deterministic reading of named columns")}
    # extraction fidelity: extracted values attributed to a named column, compared with the record
    fid = {"values": 0, "match": 0, "reported_where_record_absent": 0}
    for wf in study9.WORKFLOWS:
        for s_ in study9.B_SEEDS:
            p_ = canon[(wf, s_)]
            f_ = study9.firm("B", wf, s_, True)
            for m, text in idx.get((f_.firm_id, EX), []):
                for raw in text.splitlines():
                    for pid in {pr.pair_id for pr in f_.pairs}:
                        if pid in raw:
                            rule, e = pid.split("::", 1)
                            c = contracts[rule]
                            for chunk in raw.split(pid, 1)[1].split("|"):
                                mm = FACT_RE.match(re.sub(r"^\s*facts\s*", "", chunk.strip(), flags=re.I))
                                if not mm or not mm.group("src") or mm.group("val").upper() in ("ABSENT", "CONFLICT"):
                                    continue
                                fact = next((x for x in c.facts if x.name == mm.group("name").strip()), None)
                                if fact is None:
                                    continue
                                st, val = C._resolve(fact, p_.tables, e)
                                fid["values"] += 1
                                try:
                                    got = float(mm.group("val").replace(",", "")) if fact.kind == "amount" else C._d(mm.group("val").strip())
                                except ValueError:
                                    continue
                                if st == "known" and got == val:
                                    fid["match"] += 1
                                if st == "unknown":
                                    fid["reported_where_record_absent"] += 1
                            break
    out["extraction_fidelity"] = fid
    out["extraction_slots"] = slot_audit(idx, canon, contracts, labels)
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
