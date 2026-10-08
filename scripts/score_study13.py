"""Score Study 13 (docs/STUDY13_DECLARATION.md). No API call; writes docs/study13/results.json."""

from __future__ import annotations

import csv
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
from baselines import study13_parser  # noqa: E402
from nofalsegreen import study4, study6  # noqa: E402
from nofalsegreen import study13 as S  # noqa: E402

MODELS = [m.split("/")[-1] for m in (*study4.MODELS, *study6.MODELS)]
R2 = "--r2" in sys.argv  # the replication of the declaration addendum
EF, EX = (("contract13b_evidence_first", "contract13b_extract") if R2
          else ("contract13_evidence_first", "contract13_extract"))
ABSTAIN = {"needs_evidence", "unmonitored"}
OUT = ROOT / "docs" / "study13"
FACT_RE = re.compile(r"^\s*(?P<name>[^=|]+?)\s*=\s*(?P<val>[^|]*?)(?:\s+from\s+(?P<src>[^|]+?))?\s*$")
PACKETS = [(wf, lay, s) for wf in S.WORKFLOWS for lay in S.LAYOUTS for s in S.SEEDS]


def fid(wf, lay, s):
    return f"study13-{wf}-{lay}-s{s}"


def load_cache() -> dict:
    cache: dict = {}
    for vc in sorted((OUT / "cache").glob("*.json")):
        cache.update(json.loads(vc.read_text()))
    idx: dict = {}
    for key, v in sorted(cache.items()):
        parts = key.split("|")
        if len(parts) == 6 and parts[0] == PROMPT_VERSION:
            idx.setdefault((parts[3], parts[2]), []).append(
                (parts[1].split("/")[-1].split("#")[0], v.get("text", "") if isinstance(v, dict) else v,
                 v.get("output_tokens", 0) if isinstance(v, dict) else 0))
    return idx


NORMALISE = False  # set for the disclosed post-hoc rescoring (fact names as the prompt displayed them)


def _name(n: str, pid: str) -> str:
    """Declared scoring matches fact names exactly. The prompt displayed some names with their unit
    ("measured load (kN)"), and some replies copied that form or used snake_case; the post-hoc
    rescoring maps a name to the rule's fact when they agree after removing a trailing
    parenthesised unit, case and underscores."""
    if not NORMALISE:
        return n
    key = re.sub(r"\s*\([^)]*\)\s*$", "", n).replace("_", " ").strip().lower()
    return next((f.name for f in S.CONTRACTS[pid.split("::")[0]].facts if f.name.lower() == key), n)


def slots(text: str, ids: set) -> dict:
    """pair -> {fact: (value, document) | 'ABSENT' | 'CONFLICT'} as the reply states them."""
    out: dict = {}
    for raw in text.splitlines():
        line = raw.strip()
        pid = next((t.strip() for t in re.split(r"\t+|\s{2,}", line) if t.strip() in ids), None) if "::" in line else None
        if pid is None or pid in out:
            continue
        rep = {}
        for chunk in re.sub(r"^\s*facts\s*", "", line.split(pid, 1)[1].strip(), flags=re.I).split("|"):
            m = FACT_RE.match(chunk.strip())
            if not m:
                continue
            v = m.group("val").strip().strip("`")
            name = _name(m.group("name").strip(), pid)
            if v.upper() in ("ABSENT", "CONFLICT"):
                rep[name] = v.upper()
            elif m.group("src"):
                rep[name] = (v, m.group("src").strip())
        out[pid] = rep
    return out


def named_columns(wf, d: Path) -> dict:
    """A program reading the canonical named columns: only CSV documents with those columns."""
    tables = {}
    for t, cols in S.SCHEMAS[wf].items():
        p = d / f"{t}.csv"
        if p.exists():
            with p.open(newline="") as fh:
                r = csv.DictReader(fh)
                if set(cols) <= set(r.fieldnames or []):
                    tables[t] = list(r)
    ents = {e for e in S.make_packet(wf, int(d.name[1:])).entities}
    return {f"{c.rule_id}::{e}": S.label(c, tables, e).label for c in S.RULES[wf] for e in ents}


def exact(xs: list) -> float:
    n = len(xs)
    obs = abs(sum(xs) / n)
    vals = [abs(sum(s * x for s, x in zip(sg, xs)) / n) for sg in itertools.product((1, -1), repeat=n)]
    return sum(v >= obs - 1e-12 for v in vals) / len(vals)


def boot(per: dict, seed: int) -> list:
    keys = sorted(per)
    rng = random.Random(seed)
    bs = sorted(sum(per[rng.choice(keys)] for _ in keys) / len(keys) for _ in range(2000))
    return [round(bs[49], 4), round(bs[1949], 4)]


def main(nested: bool = False):
    global NORMALISE
    idx = load_cache()
    labels, pats = {}, {}
    for wf in S.WORKFLOWS:
        for s in S.SEEDS:
            p = S.make_packet(wf, s)
            for k, v in p.labels.items():
                labels[(wf, s, k)] = v.label
                e = k.split("::")[1]
                pats[(wf, s, k)] = p.patterns[e][0] if p.patterns[e][1] in (None, k.split("::")[0]) else "complete"
    # ---------- predictions: system -> (wf, layout, seed) -> {pair: verdict}
    pred: dict = {}
    tokens: dict = {}
    reports: dict = {}
    for wf, lay, s in PACKETS:
        ids = {k for (w, sd, k) in labels if w == wf and sd == s}
        for var in (EF, EX):
            for m, text, otok in idx.get((fid(wf, lay, s), var), []):
                tokens.setdefault((m, var), [0, 0])
                tokens[(m, var)][0] += otok
                d = pred.setdefault((m, var), {}).setdefault((wf, lay, s), {})
                if var == EX:
                    rp = reports.setdefault((m, wf, lay, s), {})
                    for pid, rep in slots(text, ids).items():
                        rp.setdefault(pid, rep)
                        d.setdefault(pid, S.verdict_from_facts(S.CONTRACTS[pid.split("::")[0]], rep))
                else:
                    for pr in parse_response(text, sorted(ids), var)[0]:
                        d.setdefault(pr.pair_id, pr.verdict.value)
        pdir = S.DIR / lay / wf / f"s{s}"
        if pdir.exists():
            facts = study13_parser.extract(wf, str(pdir))
            reports[("parser", wf, lay, s)] = facts
            pred.setdefault(("parser", "program"), {})[(wf, lay, s)] = {
                k: S.verdict_from_facts(S.CONTRACTS[k.split("::")[0]], v) for k, v in facts.items() if k in ids}
            pred.setdefault(("named columns", "program"), {})[(wf, lay, s)] = {
                k: v for k, v in named_columns(wf, pdir).items() if k in ids}
            pred.setdefault(("always abstain", "program"), {})[(wf, lay, s)] = {k: "needs_evidence" for k in ids}
    # exploratory hybrid: the parser where it reports every fact, the model's extraction elsewhere
    for m in MODELS:
        for key, d in pred.get((m, EX), {}).items():
            par = reports.get(("parser",) + key, {})
            h = {}
            for pid in d:
                rep = par.get(pid, {})
                full = all(isinstance(rep.get(f.name), tuple) for f in S.CONTRACTS[pid.split("::")[0]].facts)
                h[pid] = pred[("parser", "program")][key].get(pid) if full else d[pid]
            pred.setdefault((m, "hybrid"), {})[key] = h

    def measures(d: dict, wf, s) -> dict:
        labs = {k: v for (w, sd, k), v in labels.items() if w == wf and sd == s}
        n, dec = len(labs), {k: v for k, v in labs.items() if v != "needs_evidence"}
        return {"unsupported_pos": sum(d.get(k) == "pass" and v != "pass" for k, v in labs.items()) / n,
                "unsupported_neg": sum(d.get(k) == "fail" and v != "fail" for k, v in labs.items()) / n,
                "correct_determinate": sum(d.get(k) == v for k, v in dec.items()) / len(dec),
                "coverage": sum(k in d for k in labs) / n,
                "unnecessary_abstention": sum(d.get(k) in ABSTAIN for k in dec) / len(dec),
                "followup_share": sum(d.get(k) in ABSTAIN or d.get(k) == "fail" or k not in d for k in labs) / n}

    def per_packet(system: str, metric: str, layouts, models=MODELS) -> dict:
        res = {}
        for wf, lay, s in PACKETS:
            if lay not in layouts:
                continue
            if system in ("parser", "named columns", "always abstain"):
                d = pred.get((system, "program"), {}).get((wf, lay, s))
                if d is not None:
                    res[f"{wf}-{lay}-{s}"] = measures(d, wf, s)[metric]
                continue
            xs = [measures(pred[(m, system)][(wf, lay, s)], wf, s)[metric] for m in models
                  if (wf, lay, s) in pred.get((m, system), {})]
            if xs:
                res[f"{wf}-{lay}-{s}"] = sum(xs) / len(xs)
        return res

    def contrast(a, b, metric, layouts, seed, models=MODELS):
        pa, pb = per_packet(a, metric, layouts, models), per_packet(b, metric, layouts, models)
        ks = sorted(set(pa) & set(pb))
        if not ks:
            return {"n_packets": 0}
        diff = {k: pa[k] - pb[k] for k in ks}
        xs = [diff[k] for k in ks]
        return {"n_packets": len(ks), "delta": round(sum(xs) / len(xs), 4), "ci95_packet_bootstrap": boot(diff, seed),
                "p_exact_two_sided": exact(xs) if len(xs) <= 18 else None,
                "packets_positive": sum(x > 1e-12 for x in xs), "packets_negative": sum(x < -1e-12 for x in xs)}

    H = S.HELDOUT_LAYOUTS
    out: dict = {"declared": "docs/STUDY13_DECLARATION.md", "primary": {
        "H1 extraction + solver - evidence-first: unsupported pass": contrast(EX, EF, "unsupported_pos", H, 1),
        "H2 extraction + solver - rule-based parser: correct decisions": contrast(EX, "parser", "correct_determinate", H, 2),
        "H3 extraction + solver - evidence-first: correct decisions": contrast(EX, EF, "correct_determinate", H, 3)}}
    ps = {k: v["p_exact_two_sided"] for k, v in out["primary"].items() if v.get("p_exact_two_sided") is not None}
    run = 0.0
    for i, k in enumerate(sorted(ps, key=ps.get)):
        run = max(run, min(1.0, (len(ps) - i) * ps[k]))
        out["primary"][k]["p_holm"] = run
        want = -1 if k.startswith("H1") else 1
        out["primary"][k]["outcome"] = "confirmed" if run < 0.05 and want * out["primary"][k]["delta"] > 0 else "not confirmed"
    n1 = contrast(EX, "parser", "unsupported_pos", H, 4)
    n1["outcome"] = "confirmed" if n1.get("n_packets") and n1["ci95_packet_bootstrap"][1] < 0.02 else "not confirmed"
    out["N1 non-inferiority: extraction + solver - parser, unsupported pass, upper bound < +0.02"] = n1
    out["development_layouts"] = {
        "extraction - evidence-first: unsupported pass": contrast(EX, EF, "unsupported_pos", S.DEV_LAYOUTS, 5),
        "extraction - parser: correct decisions": contrast(EX, "parser", "correct_determinate", S.DEV_LAYOUTS, 6),
        "extraction - evidence-first: correct decisions": contrast(EX, EF, "correct_determinate", S.DEV_LAYOUTS, 7)}
    METRICS = ("unsupported_pos", "unsupported_neg", "correct_determinate", "coverage", "unnecessary_abstention",
               "followup_share")
    systems = (EF, EX, "hybrid", "parser", "named columns", "always abstain")

    def table(layouts, models=MODELS):
        return {sy: {mt: (lambda r: round(sum(r.values()) / len(r), 4) if r else None)(per_packet(sy, mt, layouts, models))
                     for mt in METRICS} for sy in systems}
    out["summary_heldout"] = table(H)
    out["summary_development"] = table(S.DEV_LAYOUTS)
    out["by_layout"] = {lay: table((lay,)) for lay in S.LAYOUTS}
    out["per_model_heldout"] = {m: {**{sy: {mt: (lambda r: round(sum(r.values()) / len(r), 4) if r else None)(
        per_packet(sy, mt, H, [m])) for mt in METRICS} for sy in (EF, EX, "hybrid")},
        "H1": contrast(EX, EF, "unsupported_pos", H, 11, [m]),
        "H2": contrast(EX, "parser", "correct_determinate", H, 12, [m]),
        "H3": contrast(EX, EF, "correct_determinate", H, 13, [m])} for m in MODELS}
    # by pattern, held-out layouts, mean over models: share of pairs answered correctly
    bp: dict = {}
    for sy in (EF, EX, "parser"):
        cnt = Counter()
        tot = Counter()
        keys = [("parser", "program")] if sy == "parser" else [(m, sy) for m in MODELS]
        for key in keys:
            for (wf, lay, s), d in pred.get(key, {}).items():
                if lay not in H:
                    continue
                for (w, sd, k), lab in labels.items():
                    if w == wf and sd == s:
                        tot[pats[(w, sd, k)]] += 1
                        cnt[pats[(w, sd, k)]] += d.get(k) == lab
        bp[sy] = {p_: round(cnt[p_] / tot[p_], 4) for p_ in sorted(tot)}
    out["correct_by_pattern_heldout"] = bp
    # slot audit of extracted facts, held-out and development layouts separately
    audit: dict = {}
    for (who, wf, lay, s), rp in sorted(reports.items()):
        p = S.make_packet(wf, s)
        group = ("parser" if who == "parser" else "models") + ("::heldout" if lay in H else "::development")
        t = audit.setdefault(group, Counter())
        for pid in sorted(k for (w, sd, k) in labels if w == wf and sd == s):
            rep = rp.get(pid, {})
            rule, e = pid.split("::")
            for f in S.CONTRACTS[rule].facts:
                st, val = S.resolve(f, p.tables, e)
                r = rep.get(f.name)
                if r is None:
                    o = "omitted"
                elif r in ("ABSENT", "CONFLICT"):
                    o = r
                else:
                    v, doc = r
                    try:
                        got = float(str(v).replace(",", "").replace("$", "")) if f.kind == "amount" else S._d(str(v).strip())
                    except ValueError:
                        got = None
                    doc = str(doc).strip().strip("`").split(".")[0].lower()
                    srcs = [x.table for x in f.sources]
                    decider = next((x.table for x in f.sources if any(
                        rr.get(x.key) == e and rr.get(x.column) not in (None, "") for rr in p.tables[x.table])), None)
                    o = ("value, correct, deciding document" if st == "known" and got == val and doc == decider
                         else "value, correct, other named document" if st == "known" and got == val and doc in srcs
                         else "value, correct, unnamed document" if st == "known" and got == val
                         else "value, wrong")
                t[f"{st}: {o}"] += 1
    out["slot_audit"] = {g: {"slots": sum(t.values()),
                             "correct": t["known: value, correct, deciding document"] + t["unknown: ABSENT"] + t["conflict: CONFLICT"],
                             "outcomes": dict(sorted(t.items()))} for g, t in sorted(audit.items())}
    # cost: output tokens per pair, from the cached replies
    npairs = Counter()
    for (m, v), dd in pred.items():
        if v in (EF, EX):
            npairs[(m, v)] += sum(len(d) for d in dd.values())
    runs = {}
    for f in sorted((OUT / "runs").glob("*.json")):
        doc = json.loads(f.read_text())
        for r in doc.get("runs", {}).values():
            if r["variant"] not in (EF, EX):
                continue
            k = (r["model"].split("/")[-1].split("#")[0], r["variant"])
            u = r.get("usage", {})
            a = runs.setdefault(k, [0, 0, 0])
            a[0] += u.get("input_tokens", 0)
            a[1] += u.get("output_tokens", 0)
            a[2] += sum(x.get("n_pairs", 0) for x in r.get("per_firm", []))
    out["tokens_per_pair"] = {f"{m}::{v}": {"input": round(a[0] / a[2], 1) if a[2] else None,
                                            "output": round(a[1] / a[2], 1) if a[2] else None}
                              for (m, v), a in sorted(runs.items())}
    out["coverage_by_model"] = {f"{m}::{v}": round(sum(len(d) for d in dd.values()) / (len(PACKETS) * 32), 4)
                                for (m, v), dd in sorted(pred.items()) if v in (EF, EX)}
    out["label_counts"] = dict(Counter(labels.values()))
    if NORMALISE:
        return out
    NORMALISE = True
    out["posthoc_name_normalised"] = {k: main_out for k, main_out in main(nested=True).items()
                                      if k in ("primary", "N1 non-inferiority: extraction + solver - parser, unsupported pass, upper bound < +0.02",
                                               "development_layouts", "summary_heldout", "summary_development",
                                               "by_layout", "per_model_heldout", "correct_by_pattern_heldout", "slot_audit")}
    NORMALISE = False
    OUT.mkdir(exist_ok=True)
    (OUT / ("results_r2.json" if R2 else "results.json")).write_text(json.dumps(out, indent=1))
    for k, v in out["primary"].items():
        print(k, v)
    for k, v in out["posthoc_name_normalised"]["primary"].items():
        print("post hoc", k, v)
    print("N1", n1)
    for sy, row in out["summary_heldout"].items():
        print(f"{sy:28s}", row)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
