"""Score Study 14 (docs/STUDY14_DECLARATION.md). No API call; writes docs/study14/results.json.

Unit of inference: the packet content (30). A content's value is the mean over its two
renderings; for model-based systems, the mean over five models with equal weight."""

from __future__ import annotations

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
from baselines import study13_parser, study14_parser  # noqa: E402
from nofalsegreen import study4, study6, study14  # noqa: E402
from nofalsegreen import study13 as S  # noqa: E402

MODELS = [m.split("/")[-1] for m in (*study4.MODELS, *study6.MODELS)]
EF, EX, CG = "contract13b_evidence_first", "contract13b_extract", "codegen14"
ABSTAIN = {"needs_evidence", "unmonitored"}
OUT = ROOT / "docs" / "study14"
FACT_RE = re.compile(r"^\s*(?P<name>[^=|]+?)\s*=\s*(?P<val>[^|]*?)(?:\s+from\s+(?P<src>[^|]+?))?\s*$")
MARGIN = 0.01
MC, SEED = 200000, 20261008


def fid(wf, lay, s):
    return f"study14-{wf}-{lay}-s{s}"


def slots(text: str, ids: set) -> dict:
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
            if v.upper() in ("ABSENT", "CONFLICT"):
                rep[m.group("name").strip()] = v.upper()
            elif m.group("src"):
                rep[m.group("name").strip()] = (v, m.group("src").strip())
        out[pid] = rep
    return out


def codegen_facts(stdout: str, ids: set) -> dict:
    """The program's JSON, as solver input; anything unreadable counts as no output."""
    try:
        obj = json.loads(stdout[stdout.index("{"):stdout.rindex("}") + 1])
    except (ValueError, json.JSONDecodeError):
        return {}
    out = {}
    for pid, facts in (obj.items() if isinstance(obj, dict) else []):
        if pid not in ids or not isinstance(facts, dict):
            continue
        out[pid] = {k: (tuple(str(x) for x in v[:2]) if isinstance(v, list) and len(v) >= 2 else
                        v if v in ("ABSENT", "CONFLICT") else "ABSENT") for k, v in facts.items()}
    return out


def signflip(xs: list, seed: int) -> float:
    n = len(xs)
    obs = abs(sum(xs)) / n
    rng = random.Random(seed)
    hits = sum(abs(sum(x if rng.random() < 0.5 else -x for x in xs)) / n >= obs - 1e-12 for _ in range(MC))
    return (hits + 1) / (MC + 1)


def boot(per: dict, seed: int) -> list:
    keys = sorted(per)
    rng = random.Random(seed)
    bs = sorted(sum(per[rng.choice(keys)] for _ in keys) / len(keys) for _ in range(2000))
    return [round(bs[49], 4), round(bs[1949], 4)]


def main() -> int:
    cache: dict = {}
    for vc in sorted((OUT / "cache").glob("*.json")):
        cache.update(json.loads(vc.read_text()))
    idx: dict = {}
    for key, v in sorted(cache.items()):
        parts = key.split("|")
        if len(parts) == 6 and parts[0] == PROMPT_VERSION:
            idx.setdefault((parts[3], parts[2]), []).append(
                (parts[1].split("/")[-1].split("#")[0], v.get("text", "") if isinstance(v, dict) else v))
    exe = json.loads((OUT / "codegen_exec.json").read_text()) if (OUT / "codegen_exec.json").exists() else {}
    cgc: dict = {}
    for p in sorted((OUT / "codegen_cache").glob("*.json")):
        cgc.update(json.loads(p.read_text()))

    packets = {(wf, s): S.make_packet(wf, s) for wf, s in study14.contents()}
    labels = {(wf, s): {k: v.label for k, v in p.labels.items()} for (wf, s), p in packets.items()}
    pats = {(wf, s): {k: (p.patterns[k.split("::")[1]][0] if p.patterns[k.split("::")[1]][1] in (None, k.split("::")[0])
                          else "complete") for k in p.labels} for (wf, s), p in packets.items()}
    pred: dict = {}     # (system, model) -> (wf, lay, s) -> {pair: verdict}
    reports: dict = {}  # (who, model, wf, lay, s) -> facts
    reuse: dict = {}    # model -> (wf, lay, written-for seed, run-on seed) -> {pair: verdict}
    for wf, lay, s in study14.renderings():
        ids = set(labels[(wf, s)])
        f_ = fid(wf, lay, s)
        for var in (EF, EX):
            for m, text in idx.get((f_, var), []):
                d = pred.setdefault((var, m), {}).setdefault((wf, lay, s), {})
                if var == EX:
                    rp = reports.setdefault(("extraction", m, wf, lay, s), {})
                    for pid, rep in slots(text, ids).items():
                        rp.setdefault(pid, rep)
                        d.setdefault(pid, S.verdict_from_facts(S.CONTRACTS[pid.split("::")[0]], rep))
                else:
                    for pr in parse_response(text, sorted(ids), var)[0]:
                        d.setdefault(pr.pair_id, pr.verdict.value)
        for key, rec in exe.items():
            if key.split("|")[3] != f_:
                continue
            m = key.split("|")[1].split("/")[-1].split("#")[0]
            facts = codegen_facts(rec.get("own", {}).get("stdout", ""), ids)
            reports[("codegen", m, wf, lay, s)] = facts
            pred.setdefault((CG, m), {})[(wf, lay, s)] = {
                k: S.verdict_from_facts(S.CONTRACTS[k.split("::")[0]], v) for k, v in facts.items()}
            t = rec.get("reuse_seed")
            if t is not None:
                ids_t = set(labels[(wf, t)])
                ft = codegen_facts(rec.get("reuse", {}).get("stdout", ""), ids_t)
                reuse.setdefault(m, {})[(wf, lay, s, t)] = {
                    k: S.verdict_from_facts(S.CONTRACTS[k.split("::")[0]], v) for k, v in ft.items()}
        pdir = study14.packet_dir(wf, lay, s)
        for name, mod in (("parser", study14_parser), ("parser, Study 13", study13_parser)):
            facts = mod.extract(wf, str(pdir))
            reports[(name, "-", wf, lay, s)] = facts
            pred.setdefault((name, "-"), {})[(wf, lay, s)] = {
                k: S.verdict_from_facts(S.CONTRACTS[k.split("::")[0]], v) for k, v in facts.items() if k in ids}
        pred.setdefault(("always abstain", "-"), {})[(wf, lay, s)] = {k: "needs_evidence" for k in ids}
    # the declared hybrid: the parser where it reports every fact of the pair, extraction elsewhere
    for m in MODELS:
        for key, d in pred.get((EX, m), {}).items():
            par = reports.get(("parser", "-") + key, {})
            h = {}
            for pid in labels[(key[0], key[2])]:
                rep = par.get(pid, {})
                full = all(isinstance(rep.get(f.name), tuple) for f in S.CONTRACTS[pid.split("::")[0]].facts)
                v = pred[("parser", "-")][key].get(pid) if full else d.get(pid)
                if v is not None:
                    h[pid] = v
            pred.setdefault(("hybrid", m), {})[key] = h

    def measures(d: dict, labs: dict) -> dict:
        n, dec = len(labs), {k: v for k, v in labs.items() if v != "needs_evidence"}
        return {"unsupported_pos": sum(d.get(k) == "pass" and v != "pass" for k, v in labs.items()) / n,
                "unsupported_neg": sum(d.get(k) == "fail" and v != "fail" for k, v in labs.items()) / n,
                "correct_determinate": sum(d.get(k) == v for k, v in dec.items()) / len(dec),
                "coverage": sum(k in d for k in labs) / n,
                "unnecessary_abstention": sum(d.get(k) in ABSTAIN for k in dec) / len(dec),
                "followup_share": sum(d.get(k) in ABSTAIN or d.get(k) == "fail" or k not in d for k in labs) / n}

    SYSTEMS = (EF, EX, CG, "hybrid", "parser", "parser, Study 13", "always abstain")
    MODEL_SYSTEMS = (EF, EX, CG, "hybrid")

    def per_rendering(system, metric, models=MODELS, layouts=study14.LAYOUTS):
        res = {}
        for wf, lay, s in study14.renderings():
            if lay not in layouts:
                continue
            ms = models if system in MODEL_SYSTEMS else ["-"]
            xs = [measures(pred[(system, m)][(wf, lay, s)], labels[(wf, s)])[metric] for m in ms
                  if (wf, lay, s) in pred.get((system, m), {})]
            # a model with no reply for a rendering counts as answering nothing
            xs += [measures({}, labels[(wf, s)])[metric] for m in ms if (wf, lay, s) not in pred.get((system, m), {})]
            res[(wf, lay, s)] = sum(xs) / len(xs)
        return res

    def per_content(system, metric, models=MODELS):
        r = per_rendering(system, metric, models)
        by: dict = {}
        for (wf, lay, s), v in r.items():
            by.setdefault(f"{wf}-{s}", []).append(v)
        return {k: sum(v) / len(v) for k, v in by.items()}

    def contrast(a, b, metric, seed, models=MODELS, test=True):
        pa, pb = per_content(a, metric, models), per_content(b, metric, models)
        diff = {k: pa[k] - pb[k] for k in sorted(set(pa) & set(pb))}
        xs = [diff[k] for k in sorted(diff)]
        out = {"n_contents": len(xs), "delta": round(sum(xs) / len(xs), 4), "ci95_content_bootstrap": boot(diff, seed),
               "contents_positive": sum(x > 1e-12 for x in xs), "contents_negative": sum(x < -1e-12 for x in xs)}
        if test:
            out["p_two_sided"] = signflip(xs, seed)
        return out

    tests = {"H1 extraction + solver - evidence-first: unsupported pass": (contrast(EX, EF, "unsupported_pos", 1), -1),
             "H2 extraction + solver - parser: correct decisions": (contrast(EX, "parser", "correct_determinate", 2), 1),
             "H3 hybrid - parser: correct decisions": (contrast("hybrid", "parser", "correct_determinate", 3), 1),
             "H4 extraction + solver - code generation: correct decisions": (contrast(EX, CG, "correct_determinate", 4), 0)}
    run = 0.0
    for i, k in enumerate(sorted(tests, key=lambda k: tests[k][0]["p_two_sided"])):
        run = max(run, min(1.0, (len(tests) - i) * tests[k][0]["p_two_sided"]))
        v, want = tests[k]
        v["p_holm"] = run
        v["outcome"] = ("confirmed" if run < 0.05 and want * v["delta"] > 0 else "not confirmed") if want else \
            ("difference" if run < 0.05 else "no detectable difference")
    out: dict = {"declared": "docs/STUDY14_DECLARATION.md", "primary": {k: v for k, (v, _) in tests.items()}}
    # declared per-model safety: upper 95% bound of (system - parser) unsupported pass below MARGIN
    out["safety_per_model"] = {}
    for sy in (EX, "hybrid", CG):
        for m in MODELS:
            c = contrast(sy, "parser", "unsupported_pos", 30 + MODELS.index(m), [m], test=False)
            c["meets_margin"] = c["ci95_content_bootstrap"][1] < MARGIN
            out["safety_per_model"][f"{sy}::{m}"] = c
    # declared secondary: layout families as units (H2 contrast and hybrid's)
    lay_tab = {}
    for name, a in (("extraction - parser", EX), ("hybrid - parser", "hybrid")):
        ra, rb = per_rendering(a, "correct_determinate"), per_rendering("parser", "correct_determinate")
        means = {}
        for lay in study14.LAYOUTS:
            ks = [k for k in ra if k[1] == lay and k in rb]
            means[lay] = round(sum(ra[k] - rb[k] for k in ks) / len(ks), 4)
        xs = list(means.values())
        lay_tab[name] = {"by_layout": means, "layouts_positive": sum(x > 0 for x in xs),
                         "p_exact_two_sided_over_layouts": signflip(xs, 50) if xs else None}
    out["layout_families"] = lay_tab
    METRICS = ("unsupported_pos", "unsupported_neg", "correct_determinate", "coverage", "unnecessary_abstention",
               "followup_share")

    def summary(models=MODELS, layouts=study14.LAYOUTS):
        res = {}
        for sy in SYSTEMS:
            row = {}
            for mt in METRICS:
                r = per_rendering(sy, mt, models, layouts)
                row[mt] = round(sum(r.values()) / len(r), 4) if r else None
            res[sy] = row
        return res
    out["summary"] = summary()
    out["by_layout"] = {lay: summary(layouts=(lay,)) for lay in study14.LAYOUTS}
    out["per_model"] = {m: {sy: v for sy, v in summary([m]).items() if sy in MODEL_SYSTEMS} for m in MODELS}
    # by pattern: share of pairs decided correctly, all renderings
    bp = {}
    for sy in (EF, EX, CG, "hybrid", "parser"):
        cnt, tot = Counter(), Counter()
        for (s_, m), dd in pred.items():
            if s_ != sy:
                continue
            for (wf, lay, s), d in dd.items():
                for k, lab in labels[(wf, s)].items():
                    tot[pats[(wf, s)][k]] += 1
                    cnt[pats[(wf, s)][k]] += d.get(k) == lab
        bp[sy] = {p_: round(cnt[p_] / tot[p_], 4) for p_ in sorted(tot)}
    out["correct_by_pattern"] = bp
    # code generation: programs, execution and reuse on another packet in the same layout
    cg = {"replies": 0, "with_program": 0, "ran_cleanly": 0, "timeouts": 0}
    for key, rec in exe.items():
        cg["replies"] += 1
        cg["with_program"] += rec.get("has_program", False)
        cg["ran_cleanly"] += rec.get("own", {}).get("returncode") == 0
        cg["timeouts"] += rec.get("own", {}).get("stderr") == "timeout"
    rr = []
    for m, dd in reuse.items():
        for (wf, lay, s, t), d in dd.items():
            rr.append(measures(d, labels[(wf, t)])["correct_determinate"])
    cg["reuse_correct_determinate"] = round(sum(rr) / len(rr), 4) if rr else None
    out["codegen"] = cg
    # slot audit of reported facts
    audit: dict = {}
    for (who, m, wf, lay, s), rp in sorted(reports.items()):
        if who == "parser, Study 13":
            continue
        p = packets[(wf, s)]
        t = audit.setdefault(who, Counter())
        for pid in sorted(labels[(wf, s)]):
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
                        got = S.amount(v) if f.kind == "amount" else S._d(str(v).strip())
                    except (ValueError, ZeroDivisionError):
                        got = None
                    doc = str(doc).strip().strip("`").split(".")[0].lower()
                    decider = next((x.table for x in f.sources if any(
                        rr_.get(x.key) == e and rr_.get(x.column) not in (None, "") for rr_ in p.tables[x.table])), None)
                    o = "value, correct" if st == "known" and got == val and doc == decider else "value, wrong"
                t[f"{st}: {o}"] += 1
    out["slot_audit"] = {w: {"slots": sum(t.values()),
                             "correct": t["known: value, correct"] + t["unknown: ABSENT"] + t["conflict: CONFLICT"],
                             "outcomes": dict(sorted(t.items()))} for w, t in sorted(audit.items())}
    # cost: tokens per pair
    tok: dict = {}
    for f in sorted((OUT / "runs").glob("*.json")):
        doc = json.loads(f.read_text())
        for r in doc.get("runs", {}).values():
            k = f"{r['model'].split('/')[-1].split('#')[0]}::{r['variant']}"
            a = tok.setdefault(k, [0, 0, 0])
            u = r.get("usage", {})
            a[0] += u.get("input_tokens", 0)
            a[1] += u.get("output_tokens", 0)
            a[2] += sum(x.get("n_pairs", 0) for x in r.get("per_firm", []))
    for key, v in cgc.items():
        k = f"{key.split('|')[1].split('/')[-1].split('#')[0]}::{CG}"
        a = tok.setdefault(k, [0, 0, 0])
        a[0] += v.get("input_tokens", 0)
        a[1] += v.get("output_tokens", 0)
        a[2] += 32
    out["tokens_per_pair"] = {k: {"input": round(a[0] / a[2], 1), "output": round(a[1] / a[2], 1)}
                              for k, a in sorted(tok.items()) if a[2]}
    out["label_counts"] = dict(Counter(v for d in labels.values() for v in d.values()))
    (OUT / "results.json").write_text(json.dumps(out, indent=1))
    for k, v in out["primary"].items():
        print(k, v)
    for sy, row in out["summary"].items():
        print(f"{sy:28s}", row)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
