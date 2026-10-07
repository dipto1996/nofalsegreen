"""Score Study 4 (docs/STUDY4_DECLARATION.md). No API call; writes docs/study4/results.json."""

from __future__ import annotations

import itertools
import json
import random
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

from baselines.llm import parse_response  # noqa: E402
from baselines.prompts import CITE_FIRST, FACTORIAL, PROMPT_VERSION  # noqa: E402
from nofalsegreen import study4  # noqa: E402
from nofalsegreen.generator import NEEDS  # noqa: E402
from nofalsegreen.rulebook import Rulebook  # noqa: E402

OFF, DASH = "abstain_offered", "abstain_withheld"
RUNS = ("r0", "r1", "r2")
# --study6: the same declared analysis on the Study 6 models (docs/STUDY6_DECLARATION.md)
STUDY6 = "--study6" in sys.argv
if STUDY6:
    from nofalsegreen import study6  # noqa: E402
MODELS = [f"vertexopen/{m}#r0" for m in study6.MODELS] if STUDY6 else study4.MODELS
CACHES = ([ROOT / "docs" / "study6" / "cache"] if STUDY6
          else [ROOT / "docs" / "study3c" / "cache", ROOT / "docs" / "study4" / "cache"])


def short(m: str) -> str:
    return m.split("/")[-1].split("#")[0]


def load():
    rb = Rulebook.load(ROOT / "rulebook" / "rulebook.json")
    cache: dict = {}
    for d in CACHES:
        for vc in sorted(d.glob("*.json")):
            cache.update(json.loads(vc.read_text()))
    firms = {a: study4.load_firms(rb, a) for a in study4.ARMS}
    # index cache by (model, variant, firm_id)
    idx: dict = {}
    for key, v in cache.items():
        parts = key.split("|")
        if len(parts) == 6 and parts[0] == PROMPT_VERSION:
            idx.setdefault((parts[1], parts[2], parts[3]), []).append(v)
    preds = {}  # (model, run, arm, variant) -> {seed|pair: Prediction}
    for arm, fs in firms.items():
        for f in fs:
            ids = [p.pair_id for p in f.pairs]
            s = f.provenance["seed"]
            for (prov, var, fid), vals in idx.items():
                if fid != f.firm_id:
                    continue
                model, run = prov.split("#")
                d = preds.setdefault((model.split("/")[-1], run, arm, var), {})
                for v in vals:
                    for p in parse_response(v.get("text", "") if isinstance(v, dict) else v, ids, var)[0]:
                        d[f"{s}|{p.pair_id}"] = p
    labels = {f"{f.provenance['seed']}|{l.pair_id}": l for f in firms["plain"] for l in f.labels}
    return firms, preds, labels


def main() -> int:
    firms, preds, labels = load()
    unass = sorted(k for k, l in labels.items() if l.verdict.value == "needs_evidence")
    fseeds = [str(s) for s in study4.SEEDS]
    models = [short(m) for m in MODELS]
    signs = list(itertools.product((1, -1), repeat=len(fseeds)))
    rng = random.Random(20261005)
    draws = [[rng.choice(fseeds) for _ in fseeds] for _ in range(2000)]

    def ind(p, outcome):
        return float(p.verdict.value == outcome)

    def firm_diffs(cells_b, cells_a, outcome="pass", run="r0"):
        """Per-firm mean over models of the mean paired difference b - a.

        cells_* is a list of (arm, variant); several cells are averaged (factorial
        main effects average the four cells on each side)."""
        out = {}
        for fs in fseeds:
            per_model = []
            for m in models:
                vals = []
                for (ab, vb), (aa, va) in zip(cells_b, cells_a):
                    db, da = preds.get((m, run, ab, vb), {}), preds.get((m, run, aa, va), {})
                    ks = [k for k in unass if k.startswith(fs + "|") and k in db and k in da]
                    if ks:
                        vals.append(sum(ind(db[k], outcome) - ind(da[k], outcome) for k in ks) / len(ks))
                if vals:
                    per_model.append(sum(vals) / len(vals))
            if per_model:
                out[fs] = sum(per_model) / len(per_model)
        return out

    def test(per_firm):
        if not per_firm:
            return {"n_firms": 0}
        xs = list(per_firm.values())
        obs = sum(xs) / len(xs)
        perm = [abs(sum(s * x for s, x in zip(sg, xs)) / len(xs)) for sg in signs[: 2 ** len(xs)]]
        p = sum(v >= abs(obs) - 1e-12 for v in perm) / len(perm)
        boots = sorted(sum(per_firm[f] for f in d if f in per_firm) / max(1, sum(f in per_firm for f in d))
                       for d in draws)
        return {"n_firms": len(xs), "delta": round(obs, 4),
                "ci95_firm_bootstrap": [round(boots[50], 4), round(boots[1949], 4)],
                "p_exact_two_sided": p, "firms_positive": sum(x > 0 for x in xs),
                "firms_negative": sum(x < 0 for x in xs)}

    def fx(o, d, w):
        return f"fx_o{o}d{d}w{w}"

    def main_effect(arm, factor):
        b, a = [], []
        for x, y in itertools.product((0, 1), repeat=2):
            kw0 = dict(zip([f for f in "odw" if f != factor], (x, y)))
            b.append((arm, fx(**{**kw0, factor: 0})))
            a.append((arm, fx(**{**kw0, factor: 1})))
        return b, a

    primary = {
        "H1 proxy - renamed (false green, offered)": firm_diffs([("proxy", OFF)], [("renamed", OFF)]),
        "H2 proxy - irrelevant (false green, offered)": firm_diffs([("proxy", OFF)], [("irrelevant", OFF)]),
        "H3 adverse - plain (false red, offered)": firm_diffs([("adverse", OFF)], [("plain", OFF)], "fail"),
        "H4 O main effect: no abstaining verdicts (proxy firms)": firm_diffs(*main_effect("proxy", "o")),
        "H5 D main effect: bare definitions (proxy firms)": firm_diffs(*main_effect("proxy", "d")),
        "H6 W main effect: no warning (proxy firms)": firm_diffs(*main_effect("proxy", "w")),
        "H7 offered - cite_first (proxy firms)": firm_diffs([("proxy", OFF)], [("proxy", CITE_FIRST)]),
    }
    out: dict = {"declared": "docs/STUDY4_DECLARATION.md", "primary": {k: test(v) for k, v in primary.items()}}
    ps = {k: v["p_exact_two_sided"] for k, v in out["primary"].items() if "p_exact_two_sided" in v}
    run_ = 0.0
    for i, k in enumerate(sorted(ps, key=ps.get)):
        run_ = max(run_, min(1.0, (len(ps) - i) * ps[k]))
        out["primary"][k]["p_holm"] = run_
        out["primary"][k]["outcome"] = "confirmed" if run_ < 0.05 else "not confirmed"

    sec: dict = {}
    for cond in (OFF, DASH):
        for name, b, a, oc in (("proxy - renamed", "proxy", "renamed", "pass"),
                               ("proxy - irrelevant", "proxy", "irrelevant", "pass"),
                               ("renamed - plain", "renamed", "plain", "pass"),
                               ("irrelevant - plain", "irrelevant", "plain", "pass"),
                               ("proxy - plain", "proxy", "plain", "pass"),
                               ("adverse - plain (false red)", "adverse", "plain", "fail"),
                               ("adverse - plain (false green)", "adverse", "plain", "pass")):
            sec[f"{name} | {cond}"] = test(firm_diffs([(b, cond)], [(a, cond)], oc))
    for f in "odw":
        sec[f"{f.upper()} main effect | plain firms"] = test(firm_diffs(*main_effect("plain", f)))
    sec["offered - cite_first | plain firms"] = test(firm_diffs([("plain", OFF)], [("plain", CITE_FIRST)]))
    out["secondary"] = sec

    # rates and verdict allocation per cell (pooled over the three models)
    rates = {}
    for (m, run, arm, var), d in preds.items():
        cnt = Counter(d[k].verdict.value for k in unass if k in d)
        cnt["unanswered"] = len(unass) - sum(cnt.values())
        key = f"{arm}::{var}::{run}"
        r = rates.setdefault(key, {"by_model": {}})
        r["by_model"][m] = {"fgr": round(cnt["pass"] / max(1, len(unass) - cnt["unanswered"]), 4),
                            "allocation": dict(cnt)}
    for key, r in rates.items():
        r["fgr_mean_over_models"] = round(sum(x["fgr"] for x in r["by_model"].values()) / len(r["by_model"]), 4)
    out["cells"] = rates

    # factorial cell means (proxy and plain), mean over models
    out["factorial_means"] = {arm: {v: rates.get(f"{arm}::{v}::r0", {}).get("fgr_mean_over_models")
                                    for v in FACTORIAL} for arm in ("proxy", "plain")}

    # cite_first: detection and false alarms on decidable pairs, vs offered
    def decided(arm, var, m):
        d = preds.get((m, "r0", arm, var), {})
        vio = [k for k, l in labels.items() if l.verdict.value == "fail" and k in d]
        ok = [k for k, l in labels.items() if l.verdict.value == "pass" and k in d]
        return {"recall": round(sum(d[k].verdict.value == "fail" for k in vio) / max(1, len(vio)), 4),
                "false_alarm": round(sum(d[k].verdict.value == "fail" for k in ok) / max(1, len(ok)), 4)}
    out["cite_first_costs"] = {f"{arm}::{var}": {m: decided(arm, var, m) for m in models}
                               for arm in ("plain", "proxy") for var in (OFF, CITE_FIRST)}
    cites = {}
    for m in models:
        d = preds.get((m, "r0", "proxy", CITE_FIRST), {})
        passes = [k for k in unass if k in d and d[k].verdict.value == "pass"]
        cites[m] = {"passes": len(passes),
                    "cite_i9_export": sum("i9_record_export" in " ".join(d[k].evidence_fields).lower()
                                          for k in passes)}
    out["cite_first_pass_cites_required_export"] = cites

    # deterministic evidence gate on existing replies
    gate = {}
    for (m, run, arm, var), d in preds.items():
        if run != "r0" or arm not in ("plain", "proxy") or var not in (OFF, DASH):
            continue
        fs = {str(f.provenance["seed"]): set(f.provenance["withheld_exports"]) for f in firms[arm]}
        gated = {}
        for k, p in d.items():
            s, pid = k.split("|", 1)
            rule = pid.split("::")[0]
            gated[k] = "needs_evidence" if any(e in fs[s] for e in NEEDS.get(rule, ())) else p.verdict.value
        fg = sum(gated[k] == "pass" for k in unass if k in gated)
        vio = [k for k, l in labels.items() if l.verdict.value == "fail" and k in gated]
        gate[f"{m}::{arm}::{var}"] = {"fgr_after_gate": round(fg / max(1, sum(k in gated for k in unass)), 4),
                                      "recall_after_gate": round(sum(gated[k] == "fail" for k in vio) / max(1, len(vio)), 4)}
    out["deterministic_gate"] = gate

    # run-to-run variability
    var_ = {}
    for arm in ("plain", "proxy"):
        for cond in (OFF, DASH):
            for m in models:
                xs = [rates.get(f"{arm}::{cond}::{r}", {}).get("by_model", {}).get(m, {}).get("fgr") for r in RUNS]
                var_[f"{arm}::{cond}::{m}"] = xs
    for cond in (OFF, DASH):
        var_[f"proxy - plain per run | {cond}"] = [
            test(firm_diffs([("proxy", cond)], [("plain", cond)], run=r)).get("delta") for r in RUNS]
    out["repeat_runs"] = var_

    # ---- Added 2026-10-06 after review. The declaration listed the two-way
    # interactions and cell means as descriptive output, but the first version
    # of this script did not report the interactions; nothing below is a test.
    def cond_effect(arm, factor, fixed):
        """Effect of switching `factor` 1 -> 0 with `fixed` held, averaging the remaining factor."""
        b, a = [], []
        free = [f for f in "odw" if f != factor and f not in fixed]
        for x in (0, 1):
            kw = {**fixed, free[0]: x}
            b.append((arm, fx(**{**kw, factor: 0})))
            a.append((arm, fx(**{**kw, factor: 1})))
        pf = firm_diffs(b, a)
        return round(sum(pf.values()) / len(pf), 4) if pf else None

    inter = {}
    for f in "dw":
        for o in (1, 0):
            inter[f"{f.upper()} effect | O={o} (proxy firms)"] = cond_effect("proxy", f, {"o": o})
    for d in (1, 0):
        for w in (1, 0):
            inter[f"D effect | O=0, W={w} (proxy firms)"] = firm_diffs([("proxy", fx(o=0, d=0, w=w))], [("proxy", fx(o=0, d=1, w=w))])
    out["factorial_interactions_posthoc"] = {k: (round(sum(v.values()) / len(v), 4) if isinstance(v, dict) else v)
                                             for k, v in inter.items()}

    # all-pairs rates (the paper's FGR definition: unanswered pairs count as not false green)
    for key, rcell in rates.items():
        for m, x in rcell["by_model"].items():
            x["fgr_all_pairs"] = round(x["allocation"].get("pass", 0) / len(unass), 4)
        rcell["fgr_all_pairs_mean_over_models"] = round(
            sum(x["fgr_all_pairs"] for x in rcell["by_model"].values()) / len(rcell["by_model"]), 4)

    # cite_first: coverage on decidable pairs and the paper's false-alarm definition
    def decided_all(arm, var, m):
        d = preds.get((m, "r0", arm, var), {})
        vio = [k for k, l in labels.items() if l.verdict.value == "fail"]
        ok = [k for k, l in labels.items() if l.verdict.value == "pass"]
        return {"recall_all_pairs": round(sum(k in d and d[k].verdict.value == "fail" for k in vio) / len(vio), 4),
                "false_alarm_any_nonpass_all_pairs": round(sum(k in d and d[k].verdict.value != "pass" for k in ok) / len(ok), 4),
                "unanswered_violations": sum(k not in d for k in vio), "unanswered_controls": sum(k not in d for k in ok),
                "n_violations": len(vio), "n_controls": len(ok)}
    out["cite_first_costs_all_pairs"] = {f"{arm}::{var}": {m: decided_all(arm, var, m) for m in models}
                                         for arm in ("plain", "proxy") for var in (OFF, CITE_FIRST)}

    # share of the proxy - renamed difference (in false-green counts, offered) carried by each model
    share = {}
    for m in models:
        a, b = preds.get((m, "r0", "proxy", OFF), {}), preds.get((m, "r0", "renamed", OFF), {})
        share[m] = sum(1 for k in unass if k in a and k in b and a[k].verdict.value == "pass") - \
            sum(1 for k in unass if k in a and k in b and b[k].verdict.value == "pass")
    tot = sum(share.values())
    # per-model effect of each declared contrast (all paired pairs; post hoc, descriptive)
    def pm(m, b, a, outcome="pass"):
        vals = []
        for (ab, vb), (aa, va) in zip(b, a):
            db, da = preds.get((m, "r0", ab, vb), {}), preds.get((m, "r0", aa, va), {})
            ks = [k for k in unass if k in db and k in da]
            if ks:
                vals.append(sum(ind(db[k], outcome) - ind(da[k], outcome) for k in ks) / len(ks))
        return round(sum(vals) / len(vals), 4) if vals else None
    specs = {"H1": ([("proxy", OFF)], [("renamed", OFF)], "pass"), "H2": ([("proxy", OFF)], [("irrelevant", OFF)], "pass"),
             "H3": ([("adverse", OFF)], [("plain", OFF)], "fail"), "H4": (*main_effect("proxy", "o"), "pass"),
             "H5": (*main_effect("proxy", "d"), "pass"), "H6": (*main_effect("proxy", "w"), "pass"),
             "H7": ([("proxy", OFF)], [("proxy", CITE_FIRST)], "pass")}
    out["per_model_primary_posthoc"] = {h: {m: pm(m, b, a, oc) for m in models} for h, (b, a, oc) in specs.items()}
    out["proxy_minus_renamed_count_share_posthoc"] = {m: {"count_diff": v, "share": round(v / tot, 4) if tot else None}
                                                      for m, v in share.items()}

    (ROOT / "docs" / "study4").mkdir(exist_ok=True)
    (ROOT / "docs" / ("study6/study4_results.json" if STUDY6 else "study4/results.json")).write_text(json.dumps(out, indent=1))
    for k, v in out["primary"].items():
        print(k, v)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
