"""Score Study 12 (docs/STUDY12_DECLARATION.md). No API call; writes docs/study12/results.json."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

from baselines.llm import parse_response  # noqa: E402
from nofalsegreen import study3c, study9  # noqa: E402
from nofalsegreen.rulebook import Rulebook  # noqa: E402
from score_study9 import MODELS, exact  # noqa: E402


def idx_of(dirs):
    idx = {}
    for d in dirs:
        for vc in sorted(d.glob("*.json")):
            for key, v in json.loads(vc.read_text()).items():
                parts = key.split("|")
                if len(parts) == 6:
                    idx.setdefault((parts[3], parts[2]), []).append((parts[1].split("/")[-1].split("#")[0],
                                                                      v.get("text", "") if isinstance(v, dict) else v))
    return idx


def main() -> int:
    docs = ROOT / "docs"
    idx = idx_of([docs / "study10" / "cache", docs / "study12" / "cache", docs / "study3c" / "cache", docs / "study6" / "cache"])
    # M1
    pred, labels = {}, {}
    for wf in study9.WORKFLOWS:
        for s in study9.A_SEEDS:
            f = study9.firm("A", wf, s, True)
            ids = sorted(p.pair_id for p in f.pairs)
            for l in f.labels:
                labels[(wf, s, l.pair_id)] = l.verdict.value
            for var in ("contract_sem_meaning_offered", "contract_sem_offered"):
                for m, text in idx.get((f.firm_id, var), []):
                    d = pred.setdefault((m, wf, s, var), {})
                    for p in parse_response(text, ids, var)[0]:
                        d[p.pair_id] = (p.verdict.value, " ".join(p.evidence_fields))

    def m1(models=MODELS):
        res = {}
        for wf in study9.WORKFLOWS:
            for s in study9.A_SEEDS:
                vals = []
                for m in models:
                    a, b = pred.get((m, wf, s, "contract_sem_meaning_offered"), {}), pred.get((m, wf, s, "contract_sem_offered"), {})
                    ks = [pid for (w, sd, pid), lab in labels.items() if w == wf and sd == s and lab == "needs_evidence" and pid in a and pid in b]
                    if ks:
                        vals.append(sum((a[k][0] == "pass") - (b[k][0] == "pass") for k in ks) / len(ks))
                if vals:
                    res[f"{wf}-{s}"] = sum(vals) / len(vals)
        return res
    # M2
    rb = Rulebook.load(ROOT / "rulebook" / "rulebook.json")
    pred2, lab2 = {}, {}
    for f in study3c.load_firms(rb, "proxy"):
        ids = sorted(p.pair_id for p in f.pairs)
        s = f.provenance["seed"]
        for l in f.labels:
            lab2[(s, l.pair_id)] = l.verdict.value
        for var in ("abstain_offered", "abstain_offered_nomatch"):
            for m, text in idx.get((f.firm_id, var), []):
                d = pred2.setdefault((m, s, var), {})
                for p in parse_response(text, ids, var)[0]:
                    d[p.pair_id] = (p.verdict.value, " ".join(p.evidence_fields))

    def m2(models=MODELS):
        res = {}
        for s in study3c.SEEDS:
            vals = []
            for m in models:
                a, b = pred2.get((m, s, "abstain_offered"), {}), pred2.get((m, s, "abstain_offered_nomatch"), {})
                ks = [pid for (sd, pid), lab in lab2.items() if sd == s and lab == "needs_evidence" and pid in a and pid in b]
                if ks:
                    vals.append(sum((a[k][0] == "pass") - (b[k][0] == "pass") for k in ks) / len(ks))
            if vals:
                res[str(s)] = sum(vals) / len(vals)
        return res
    prim = {"M1 with - without the reading rule, contract packets": exact(m1(), 12101),
            "M2 original - without the reading rule, Study 3c proxy firms": exact(m2(), 12102)}
    ps = {k: v["p_exact_two_sided"] for k, v in prim.items()}
    run = 0.0
    for i, k in enumerate(sorted(ps, key=ps.get)):
        run = max(run, min(1.0, (len(ps) - i) * ps[k]))
        prim[k]["p_holm"] = run
        prim[k]["outcome"] = "confirmed" if run < 0.05 else "not confirmed"
    avg = lambda r: round(sum(r.values()) / len(r), 4) if r else None  # noqa: E731
    out = {"declared": "docs/STUDY12_DECLARATION.md", "primary": prim,
           "per_model": {"M1": {m: avg(m1([m])) for m in MODELS}, "M2": {m: avg(m2([m])) for m in MODELS}}}
    rates = {}
    for m in MODELS:
        for var in ("abstain_offered", "abstain_offered_nomatch"):
            u = [v[0] == "pass" for (mm, s, vv), d in pred2.items() if mm == m and vv == var for pid, v in d.items() if lab2[(s, pid)] == "needs_evidence"]
            rates[f"{m}::{var}"] = round(sum(u) / len(u), 4) if u else None
        for var in ("contract_sem_meaning_offered", "contract_sem_offered"):
            u = [v[0] == "pass" for (mm, wf, s, vv), d in pred.items() if mm == m and vv == var for pid, v in d.items() if labels[(wf, s, pid)] == "needs_evidence"]
            rates[f"{m}::{var}"] = round(sum(u) / len(u), 4) if u else None
    out["unsupported_pass_rate"] = rates
    (ROOT / "docs" / "study12").mkdir(exist_ok=True)
    (ROOT / "docs" / "study12" / "results.json").write_text(json.dumps(out, indent=1))
    for k, v in prim.items():
        print(k, v)
    print(json.dumps(out["per_model"], indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
