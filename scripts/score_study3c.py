"""Score Study 3c (docs/STUDY3C_DECLARATION.md). No API call; writes docs/study3c/results.json."""

from __future__ import annotations

import itertools
import json
import random
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

from score_studies import preds_for  # noqa: E402
from nofalsegreen import study3c  # noqa: E402
from nofalsegreen.rulebook import Rulebook  # noqa: E402

MODELS = [f"vertex/{m}#r0" for m in study3c.MODELS]
S12 = ("i9.section1.timeliness", "i9.section2.timeliness")
RV = ("i9.reverification.deadline",)
TESTS = {
    "C1 all proxy columns, dashboard": ("proxy", "abstain_withheld", S12 + RV),
    "C2 all proxy columns, offered": ("proxy", "abstain_offered", S12 + RV),
    "C3 i9Status alone, dashboard": ("only_i9Status", "abstain_withheld", S12),
    "C4 onboardingCompletedDate alone, dashboard": ("only_onboardingCompletedDate", "abstain_withheld", S12),
    "C5 workAuthValidThrough alone, dashboard": ("only_workAuthValidThrough", "abstain_withheld", RV),
}


def main() -> int:
    rb = Rulebook.load(ROOT / "rulebook" / "rulebook.json")
    cache: dict = {}
    for vc in sorted((ROOT / "docs" / "study3c" / "cache").glob("*.json")):
        cache.update(json.loads(vc.read_text()))
    verd = {}
    unass = set()
    for arm in study3c.ARMS:
        for f in study3c.load_firms(rb, arm):
            s = f.provenance["seed"]
            for l in f.labels:
                if l.verdict.value == "needs_evidence":
                    unass.add(f"{s}|{l.pair_id}")
            for m in MODELS:
                for c in ("abstain_withheld", "abstain_offered"):
                    for pid, v in preds_for(cache, f, m, c).items():
                        verd.setdefault((m, arm, c), {})[f"{s}|{pid}"] = v
    firms = [str(s) for s in study3c.SEEDS]
    out = {"declared": "docs/STUDY3C_DECLARATION.md", "rates": {}, "tests": {}}
    for (m, arm, c), d in sorted(verd.items()):
        for rules, lab in ((S12, "S1+S2"), (RV, "reverification")):
            ks = [k for k in unass if k in d and k.split("|", 1)[1].split("::")[0] in rules]
            if ks:
                out["rates"][f"{m.split('/')[1].split('#')[0]}::{arm}::{c}::{lab}"] = {
                    "fgr": round(sum(d[k] == "pass" for k in ks) / len(ks), 4), "n": len(ks)}
    rng = random.Random(20261004)
    draws = [[rng.choice(firms) for _ in firms] for _ in range(2000)]
    signs = list(itertools.product((1, -1), repeat=len(firms)))
    for name, (arm, cond, rules) in TESTS.items():
        per_firm = {}  # firm -> mean over models of that firm's mean paired difference
        for fs in firms:
            vals = []
            for m in MODELS:
                a, b = verd.get((m, "plain", cond), {}), verd.get((m, arm, cond), {})
                ks = [k for k in unass if k.startswith(fs + "|") and k.split("|", 1)[1].split("::")[0] in rules
                      and k in a and k in b]
                if ks:
                    vals.append(sum(float(b[k] == "pass") - float(a[k] == "pass") for k in ks) / len(ks))
            if vals:
                per_firm[fs] = sum(vals) / len(vals)
        if not per_firm:
            out["tests"][name] = {"n_firms": 0}
            continue
        xs = list(per_firm.values())
        obs = sum(xs) / len(xs)
        perm = [abs(sum(s * x for s, x in zip(sg, xs)) / len(xs)) for sg in signs[: 2 ** len(xs)]]
        p = sum(v >= abs(obs) - 1e-12 for v in perm) / len(perm)
        boots = sorted(sum(per_firm[f] for f in d if f in per_firm) / max(1, sum(f in per_firm for f in d))
                       for d in draws)
        out["tests"][name] = {"n_firms": len(xs), "delta": round(obs, 4),
                              "ci95_firm_bootstrap": [round(boots[50], 4), round(boots[1949], 4)],
                              "p_exact_two_sided": p, "firms_positive": sum(x > 0 for x in xs)}
    ps = {k: v["p_exact_two_sided"] for k, v in out["tests"].items() if "p_exact_two_sided" in v}
    run = 0.0
    for i, k in enumerate(sorted(ps, key=ps.get)):
        run = max(run, min(1.0, (len(ps) - i) * ps[k]))
        out["tests"][k]["p_holm"] = run
        out["tests"][k]["outcome"] = "confirmed" if run < 0.05 and out["tests"][k]["delta"] > 0 else "not confirmed"
    (ROOT / "docs" / "study3c").mkdir(exist_ok=True)
    (ROOT / "docs" / "study3c" / "results.json").write_text(json.dumps(out, indent=1))
    for k, v in out["tests"].items():
        print(k, v)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
