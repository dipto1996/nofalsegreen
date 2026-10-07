"""Score Study 10 (docs/STUDY10_DECLARATION.md). No API call; writes docs/study10/results.json."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

from baselines.llm import parse_response  # noqa: E402
from nofalsegreen import study9  # noqa: E402
from score_study9 import MODELS, exact, load_cache  # noqa: E402

PAIRS = {"offered": ("contract_sem_offered", "contract_offered"), "forced": ("contract_sem_forced", "contract_forced")}


def main() -> int:
    idx = load_cache()
    idx10 = {}
    for vc in sorted((ROOT / "docs" / "study10" / "cache").glob("*.json")):
        for key, v in json.loads(vc.read_text()).items():
            parts = key.split("|")
            if len(parts) == 6:
                idx10.setdefault((parts[3], parts[2]), []).append((parts[1].split("/")[-1].split("#")[0],
                                                                    v.get("text", "") if isinstance(v, dict) else v))
    idx = {**idx, **idx10}
    pred, labels = {}, {}
    for wf in study9.WORKFLOWS:
        for s in study9.A_SEEDS:
            f = study9.firm("A", wf, s, True)
            ids = sorted(p.pair_id for p in f.pairs)
            for l in f.labels:
                labels[(wf, s, l.pair_id)] = l.verdict.value
            for var in ("contract_sem_offered", "contract_sem_forced", "contract_offered", "contract_forced"):
                for m, text in idx.get((f.firm_id, var), []):
                    d = pred.setdefault((m, wf, s, var), {})
                    for p in parse_response(text, ids, var)[0]:
                        d[p.pair_id] = (p.verdict.value, " ".join(p.evidence_fields))

    def per_packet(menu, wfs, models=MODELS, outcome="pass", on="needs_evidence"):
        sem, bound = PAIRS[menu]
        res = {}
        for wf in wfs:
            for s in study9.A_SEEDS:
                vals = []
                for m in models:
                    a, b = pred.get((m, wf, s, sem), {}), pred.get((m, wf, s, bound), {})
                    ks = [pid for (w, sd, pid), lab in labels.items() if w == wf and sd == s
                          and (lab == on if on != "decidable" else lab in ("pass", "fail")) and pid in a and pid in b]
                    if ks:
                        if outcome == "abstain":
                            vals.append(sum((a[k][0] in ("needs_evidence", "unmonitored")) - (b[k][0] in ("needs_evidence", "unmonitored")) for k in ks) / len(ks))
                        else:
                            vals.append(sum((a[k][0] == "pass") - (b[k][0] == "pass") for k in ks) / len(ks))
                if vals:
                    res[f"{wf}-{s}"] = sum(vals) / len(vals)
        return res

    W = study9.WORKFLOWS
    prim = {"B1 described - bound, unsupported pass, offered": exact(per_packet("offered", W), 10101),
            "B2 described - bound, unsupported pass, forced": exact(per_packet("forced", W), 10102),
            "B3 described - bound, offered, purchasing and engineering": exact(per_packet("offered", ("purchasing", "engineering")), 10103)}
    ps = {k: v["p_exact_two_sided"] for k, v in prim.items()}
    run = 0.0
    for i, k in enumerate(sorted(ps, key=ps.get)):
        run = max(run, min(1.0, (len(ps) - i) * ps[k]))
        prim[k]["p_holm"] = run
        prim[k]["outcome"] = "confirmed" if run < 0.05 else "not confirmed"
    out = {"declared": "docs/STUDY10_DECLARATION.md", "primary": prim}
    avg = lambda r: round(sum(r.values()) / len(r), 4) if r else None  # noqa: E731
    out["per_model"] = {menu: {m: avg(per_packet(menu, W, models=[m])) for m in MODELS} for menu in PAIRS}
    out["abstention_on_decidable_described_minus_bound"] = {menu: avg(per_packet(menu, W, outcome="abstain", on="decidable")) for menu in PAIRS}
    rates = {}
    for m in MODELS:
        for var in ("contract_sem_offered", "contract_offered", "contract_sem_forced", "contract_forced"):
            u = [v[0] == "pass" for (mm, wf, s, vv), d in pred.items() if mm == m and vv == var
                 for pid, v in d.items() if labels[(wf, s, pid)] == "needs_evidence"]
            rates[f"{m}::{var}"] = round(sum(u) / len(u), 4) if u else None
    out["unsupported_pass_rate"] = rates
    cites = {}
    for (m, wf, s, var), d in pred.items():
        if var != "contract_sem_offered":
            continue
        for pid, (v, ev) in d.items():
            if v == "pass" and labels[(wf, s, pid)] == "needs_evidence":
                cites[ev.split(".")[-1] if ev else "-"] = cites.get(ev.split(".")[-1] if ev else "-", 0) + 1
    out["described_offered_false_green_cites"] = dict(sorted(cites.items(), key=lambda x: -x[1]))
    (ROOT / "docs" / "study10").mkdir(exist_ok=True)
    (ROOT / "docs" / "study10" / "results.json").write_text(json.dumps(out, indent=1))
    for k, v in prim.items():
        print(k, v)
    print(json.dumps({k: out[k] for k in ("per_model", "abstention_on_decidable_described_minus_bound")}, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
