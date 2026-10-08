"""Score Study 15 (docs/STUDY15_DECLARATION.md). No API call; writes docs/study15/results.json.

Unit of inference: the packet (50 contents, each rendered once in its publisher's format). A
packet's value for a model system is the mean over five models with equal weight."""

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
sys.path.insert(0, str(ROOT / "scripts"))

from baselines.llm import parse_response  # noqa: E402
from baselines.prompts import PROMPT_VERSION  # noqa: E402
from nofalsegreen import study4, study6, study15  # noqa: E402
from nofalsegreen import study13 as S  # noqa: E402
from score_study14 import codegen_facts, slots  # noqa: E402

MODELS = [m.split("/")[-1] for m in (*study4.MODELS, *study6.MODELS)]
EF, EX, CG = "contract13b_evidence_first", "contract13b_extract", "codegen15"
ABSTAIN = {"needs_evidence", "unmonitored"}
OUT = ROOT / "docs" / "study15"
MARGIN, MC = 0.01, 200000


def signflip(xs: list, seed: int) -> float:
    n = len(xs)
    obs = abs(sum(xs)) / n
    if n <= 20:
        vals = [abs(sum(s * x for s, x in zip(sg, xs))) / n for sg in itertools.product((1, -1), repeat=n)]
        return sum(v >= obs - 1e-12 for v in vals) / len(vals)
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
    cg: dict = {}
    for p in sorted((OUT / "codegen_cache").glob("*.json")):
        cg.update(json.loads(p.read_text()))

    packets = {(wf, k): study15.make_packet(wf, k) for wf, k in study15.contents()}
    labels = {c: {k: v.label for k, v in p[3].items()} for c, p in packets.items()}
    withheld = {c: {f"{r}::{e}" for e, r, _ in p[4]} for c, p in packets.items()}
    pred: dict = {}
    reports: dict = {}
    for (wf, k), (recs, tables, ents, labs, wh) in packets.items():
        ids = set(labels[(wf, k)])
        fid = f"study15-{wf}-p{k:02d}"
        for var in (EF, EX):
            for m, text in idx.get((fid, var), []):
                d = pred.setdefault((var, m), {}).setdefault((wf, k), {})
                if var == EX:
                    rp = reports.setdefault(("extraction", m, wf, k), {})
                    for pid, rep in slots(text, ids).items():
                        rp.setdefault(pid, rep)
                        d.setdefault(pid, S.verdict_from_facts(study15.CONTRACTS[pid.split("::")[0]], rep))
                else:
                    for pr in parse_response(text, sorted(ids), var)[0]:
                        d.setdefault(pr.pair_id, pr.verdict.value)
        for key, rec in cg.items():
            if key.split("|")[3] != fid:
                continue
            m = key.split("|")[1].split("/")[-1].split("#")[0]
            facts = codegen_facts((rec.get("own") or {}).get("stdout", ""), ids)
            reports[("codegen", m, wf, k)] = facts
            pred.setdefault((CG, m), {})[(wf, k)] = {
                pid: S.verdict_from_facts(study15.CONTRACTS[pid.split("::")[0]], v) for pid, v in facts.items()}
        pred.setdefault(("always abstain", "-"), {})[(wf, k)] = {pid: "needs_evidence" for pid in ids}

    def measures(d: dict, labs: dict) -> dict:
        n, dec = len(labs), {k: v for k, v in labs.items() if v != "needs_evidence"}
        return {"unsupported_pos": sum(d.get(k) == "pass" and v != "pass" for k, v in labs.items()) / n,
                "unsupported_neg": sum(d.get(k) == "fail" and v != "fail" for k, v in labs.items()) / n,
                "correct_determinate": sum(d.get(k) == v for k, v in dec.items()) / len(dec),
                "coverage": sum(k in d for k in labs) / n,
                "unnecessary_abstention": sum(d.get(k) in ABSTAIN for k in dec) / len(dec),
                "followup_share": sum(d.get(k) in ABSTAIN or d.get(k) == "fail" or k not in d for k in labs) / n}

    MODEL_SYSTEMS = (EF, EX, CG)

    def per_packet(system, metric, models=MODELS, wfs=study15.WORKFLOWS):
        res = {}
        for wf, k in study15.contents():
            if wf not in wfs:
                continue
            ms = models if system in MODEL_SYSTEMS else ["-"]
            xs = [measures(pred.get((system, m), {}).get((wf, k), {}), labels[(wf, k)])[metric] for m in ms]
            res[f"{wf}-{k:02d}"] = sum(xs) / len(xs)
        return res

    def contrast(a, b, metric, seed, models=MODELS, test=True):
        pa, pb = per_packet(a, metric, models), per_packet(b, metric, models)
        diff = {k: pa[k] - pb[k] for k in sorted(pa)}
        xs = [diff[k] for k in sorted(diff)]
        out = {"n_packets": len(xs), "delta": round(sum(xs) / len(xs), 4), "ci95_packet_bootstrap": boot(diff, seed),
               "packets_positive": sum(x > 1e-12 for x in xs), "packets_negative": sum(x < -1e-12 for x in xs)}
        if test:
            out["p_two_sided"] = signflip(xs, seed)
        return out

    tests = {"H1 extraction + solver - evidence-first: unsupported pass": (contrast(EX, EF, "unsupported_pos", 1), -1),
             "H2 extraction + solver - code generation: correct decisions": (contrast(EX, CG, "correct_determinate", 2), 1),
             "H3 extraction + solver - evidence-first: correct decisions": (contrast(EX, EF, "correct_determinate", 3), 1)}
    run = 0.0
    for i, k in enumerate(sorted(tests, key=lambda k: tests[k][0]["p_two_sided"])):
        run = max(run, min(1.0, (len(tests) - i) * tests[k][0]["p_two_sided"]))
        v, want = tests[k]
        v["p_holm"] = run
        v["outcome"] = "confirmed" if run < 0.05 and want * v["delta"] > 0 else "not confirmed"
    out: dict = {"declared": "docs/STUDY15_DECLARATION.md", "primary": {k: v for k, (v, _) in tests.items()}}
    # declared per-model safety: upper 95% packet-bootstrap bound of unsupported pass below 0.01
    out["safety_per_model"] = {}
    for sy in (EX, CG, EF):
        for m in MODELS:
            r = per_packet(sy, "unsupported_pos", [m])
            out["safety_per_model"][f"{sy}::{m}"] = {"rate": round(sum(r.values()) / len(r), 4),
                                                     "ci95_packet_bootstrap": boot(r, 40 + MODELS.index(m)),
                                                     "meets_margin": boot(r, 40 + MODELS.index(m))[1] < MARGIN}
    METRICS = ("unsupported_pos", "unsupported_neg", "correct_determinate", "coverage", "unnecessary_abstention",
               "followup_share")

    def summary(models=MODELS, wfs=study15.WORKFLOWS):
        res = {}
        for sy in (EF, EX, CG, "always abstain"):
            res[sy] = {mt: round(sum(per_packet(sy, mt, models, wfs).values()) / len(per_packet(sy, mt, models, wfs)), 4)
                       for mt in METRICS}
        return res
    out["summary"] = summary()
    out["by_source"] = {wf: summary(wfs=(wf,)) for wf in study15.WORKFLOWS}
    out["per_model"] = {m: {sy: v for sy, v in summary([m]).items() if sy in MODEL_SYSTEMS} for m in MODELS}
    out["per_model_by_source"] = {f"{m}::{wf}": {sy: v for sy, v in summary([m], (wf,)).items() if sy in MODEL_SYSTEMS}
                                  for m in MODELS for wf in study15.WORKFLOWS}
    # missing evidence: withheld by us versus missing in the publisher's own record
    miss = {}
    for sy in (EF, EX, CG):
        cnt = Counter()
        for m in MODELS:
            for c, d in pred.get((sy, m), {}).items():
                for pid, lab in labels[c].items():
                    if lab != "needs_evidence":
                        continue
                    kind = "withheld" if pid in withheld[c] else "missing at source"
                    cnt[(kind, "n")] += 1
                    cnt[(kind, "unsupported pass")] += d.get(pid) == "pass"
                    cnt[(kind, "unsupported fail")] += d.get(pid) == "fail"
        miss[sy] = {kind: {"pairs": cnt[(kind, "n")], "unsupported_pass": round(cnt[(kind, "unsupported pass")] / max(1, cnt[(kind, "n")]), 4),
                           "unsupported_fail": round(cnt[(kind, "unsupported fail")] / max(1, cnt[(kind, "n")]), 4)}
                    for kind in ("withheld", "missing at source")}
    out["needs_evidence_by_origin"] = miss
    # code generation: calls, repairs, execution and reuse with the next packet's manifest
    st = Counter()
    rr = []
    for key, rec in cg.items():
        calls = rec.get("calls", [])
        st["packets"] += 1
        st["calls"] += len(calls)
        st["clean_first_call"] += bool(calls) and calls[0].get("diagnostics") == []
        st["clean_final"] += bool(calls) and calls[-1].get("diagnostics") == []
        st["capped_calls"] += sum(c.get("finish_reason") == "length" for c in calls)
        st["no_program"] += rec.get("program") is None
        fid = key.split("|")[3]
        wf, k = fid.split("-")[1], int(fid.split("-")[2][1:])
        if rec.get("reuse_packet") is not None:
            nk = rec["reuse_packet"]
            ids = set(labels[(wf, nk)])
            facts = codegen_facts((rec.get("reuse") or {}).get("stdout", ""), ids)
            d = {pid: S.verdict_from_facts(study15.CONTRACTS[pid.split("::")[0]], v) for pid, v in facts.items()}
            rr.append(measures(d, labels[(wf, nk)])["correct_determinate"])
            st["reuse_answered_new_pairs"] += bool(set(facts) & ids)
    out["codegen"] = {**dict(st), "reuse_correct_determinate": round(sum(rr) / len(rr), 4) if rr else None}
    # slot audit against the canonical records
    audit: dict = {}
    for (who, m, wf, k), rp in sorted(reports.items()):
        tables = packets[(wf, k)][1]
        t = audit.setdefault(who, Counter())
        for pid in sorted(labels[(wf, k)]):
            rep = rp.get(pid, {})
            rule, e = pid.split("::", 1)
            for f in study15.CONTRACTS[rule].facts:
                st_, val = S.resolve(f, tables, e)
                r = rep.get(f.name)
                if r is None:
                    o = "omitted"
                elif r in ("ABSENT", "CONFLICT"):
                    o = r
                else:
                    try:
                        got = S.amount(r[0]) if f.kind == "amount" else S._d(str(r[0]).strip())
                    except (ValueError, ZeroDivisionError):
                        got = None
                    o = "value, correct" if st_ == "known" and got == val else "value, wrong"
                t[f"{st_}: {o}"] += 1
    out["slot_audit"] = {w: {"slots": sum(t.values()), "correct": t["known: value, correct"] + t["unknown: ABSENT"],
                             "outcomes": dict(sorted(t.items()))} for w, t in sorted(audit.items())}
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
    for key, rec in cg.items():
        k = f"{key.split('|')[1].split('/')[-1].split('#')[0]}::{CG}"
        a = tok.setdefault(k, [0, 0, 0])
        a[0] += sum(c.get("input_tokens", 0) for c in rec.get("calls", []))
        a[1] += sum(c.get("output_tokens", 0) for c in rec.get("calls", []))
        a[2] += 24
    out["tokens_per_pair"] = {k: {"input": round(a[0] / a[2], 1), "output": round(a[1] / a[2], 1)}
                              for k, a in sorted(tok.items()) if a[2]}
    out["label_counts"] = {wf: dict(Counter(v for (w, _), d in labels.items() if w == wf for v in d.values()))
                           for wf in study15.WORKFLOWS}
    (OUT / "results.json").write_text(json.dumps(out, indent=1, default=str))
    for k, v in out["primary"].items():
        print(k, v)
    for sy, row in out["summary"].items():
        print(f"{sy:28s}", row)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
