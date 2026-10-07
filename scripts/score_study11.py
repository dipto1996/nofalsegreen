"""Score Study 11 (docs/STUDY11_DECLARATION.md). No API call; writes docs/study11/results.json."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

from baselines.llm import parse_response  # noqa: E402
from nofalsegreen import study9  # noqa: E402
from score_study9 import MODELS, exact  # noqa: E402

VAR = "contract_offered"


def main() -> int:
    idx = {}
    for vc in sorted((ROOT / "docs" / "study11" / "cache").glob("*.json")):
        for key, v in json.loads(vc.read_text()).items():
            parts = key.split("|")
            if len(parts) == 6:
                idx.setdefault((parts[3], parts[2]), []).append((parts[1].split("/")[-1].split("#")[0],
                                                                  v.get("text", "") if isinstance(v, dict) else v))
    pred, labels = {}, {}
    for wf in study9.WORKFLOWS:
        for form in study9.GAP_FORMS:
            for s in study9.C_SEEDS:
                f = study9.gap_firm(wf, s, form)
                ids = sorted(p.pair_id for p in f.pairs)
                for l in f.labels:
                    labels[(wf, s, form, l.pair_id)] = l.verdict.value
                for m, text in idx.get((f.firm_id, VAR), []):
                    d = pred.setdefault((m, wf, s, form), {})
                    for p in parse_response(text, ids, VAR)[0]:
                        d[p.pair_id] = p.verdict.value

    def per_packet(b, a, wfs=study9.WORKFLOWS, models=MODELS, verdict="pass"):
        res = {}
        for wf in wfs:
            for s in study9.C_SEEDS:
                vals = []
                for m in models:
                    db, da = pred.get((m, wf, s, b), {}), pred.get((m, wf, s, a), {})
                    ks = [pid for (w, sd, fm, pid), lab in labels.items() if w == wf and sd == s and fm == b
                          and lab == "needs_evidence" and labels.get((wf, s, a, pid)) == "needs_evidence"
                          and pid in db and pid in da]
                    if ks:
                        vals.append(sum((db[k] == verdict) - (da[k] == verdict) for k in ks) / len(ks))
                if vals:
                    res[f"{wf}-{s}"] = sum(vals) / len(vals)
        return res

    prim = {"G1 table - row": exact(per_packet("table", "row"), 11101),
            "G2 row - blank": exact(per_packet("row", "blank"), 11102),
            "G3 table - blank": exact(per_packet("table", "blank"), 11103)}
    ps = {k: v["p_exact_two_sided"] for k, v in prim.items()}
    run = 0.0
    for i, k in enumerate(sorted(ps, key=ps.get)):
        run = max(run, min(1.0, (len(ps) - i) * ps[k]))
        prim[k]["p_holm"] = run
        prim[k]["outcome"] = "confirmed" if run < 0.05 else "not confirmed"
    avg = lambda r: round(sum(r.values()) / len(r), 4) if r else None  # noqa: E731
    out = {"declared": "docs/STUDY11_DECLARATION.md", "primary": prim}
    out["per_model"] = {k: {m: avg(per_packet(b, a, models=[m])) for m in MODELS}
                        for k, (b, a) in {"table-row": ("table", "row"), "row-blank": ("row", "blank"),
                                          "table-blank": ("table", "blank")}.items()}
    out["per_workflow"] = {k: {wf: avg(per_packet(b, a, wfs=(wf,))) for wf in study9.WORKFLOWS}
                           for k, (b, a) in {"table-blank": ("table", "blank")}.items()}
    rates = {}
    for form in study9.GAP_FORMS:
        for m in MODELS:
            hit = [(d.get(pid)) for (mm, wf, s, fm), d in pred.items() if mm == m and fm == form
                   for pid in d if labels[(wf, s, fm, pid)] == "needs_evidence"
                   and labels.get((wf, s, "blank", pid)) == "needs_evidence"]
            rates[f"{m}::{form}"] = {v: round(sum(x == v for x in hit) / len(hit), 4) for v in ("pass", "fail", "needs_evidence")} if hit else None
    out["rates_on_shared_needs_evidence_pairs"] = rates
    (ROOT / "docs" / "study11").mkdir(exist_ok=True)
    (ROOT / "docs" / "study11" / "results.json").write_text(json.dumps(out, indent=1))
    for k, v in prim.items():
        print(k, v)
    print(json.dumps(out["per_model"], indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
