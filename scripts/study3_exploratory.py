"""Exploratory analyses of Study 3, added after the results (round-3 review).

None of these is in the declaration (docs/STUDY3_PREREGISTRATION.md), and the
paper labels each as exploratory. All are computed from the retained replies;
no API call is made. Writes docs/study3/exploratory.json.

1. Cited evidence. For every false green (a `pass` on an unassessable pair),
   which column the reply line cites: one of the five planted proxy columns,
   the LCA's own offered-wage column (a proxy present in every firm), or other.
2. The abstention and definition contrasts on PLAIN firms, with the declared
   estimator (paired, cluster bootstrap, same draws), for comparison with the
   declared proxy-arm tests.
3. Cluster sign counts: in how many of the 18 (firm, rule) clusters the
   proxy-minus-plain difference, averaged over models, is positive.
4. Where unassessable pairs go under each schema (verdict counts).
"""

from __future__ import annotations

import json
import random
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

from baselines.llm import parse_response  # noqa: E402
from baselines.prompts import PROMPT_VERSION  # noqa: E402
from score_study3 import DRAWS, MODELS, SEED, short  # noqa: E402
from nofalsegreen import study3  # noqa: E402
from nofalsegreen.rulebook import Rulebook  # noqa: E402

PROXY = ("i9Status", "onboardingCompletedDate", "workAuthValidThrough", "annualBaseSalary", "payBandMidpoint")


def predictions(cache, firm, model, cond):
    ids = [p.pair_id for p in firm.pairs]
    out = {}
    for key, v in cache.items():
        parts = key.split("|")
        if (len(parts) != 6 or parts[0] != PROMPT_VERSION or parts[1] != model
                or parts[2] != cond or parts[3] != firm.firm_id):
            continue
        for p in parse_response(v.get("text", "") if isinstance(v, dict) else v, ids, cond)[0]:
            out[p.pair_id] = p
    return out


def main() -> int:
    rb = Rulebook.load(ROOT / "rulebook" / "rulebook.json")
    firms = {a: study3.load_firms(rb, a) for a in study3.ARMS}
    cache: dict = {}
    for vc in sorted((ROOT / "docs" / "study3" / "cache").glob("*.json")):
        cache.update(json.loads(vc.read_text()))

    preds = {(m, a, c): {} for m in MODELS for a in study3.ARMS for c in study3.CONDITIONS}
    for m in MODELS:
        for a in study3.ARMS:
            for c in study3.CONDITIONS:
                for f in firms[a]:
                    s = f.provenance["seed"]
                    for pid, p in predictions(cache, f, m, c).items():
                        preds[(m, a, c)][f"{s}|{pid}"] = p
    unassessable = {f"{f.provenance['seed']}|{l.pair_id}" for f in firms["decoy"] for l in f.labels
                    if l.verdict.value == "needs_evidence"}
    fam = lambda k: "wage" if k.split("|", 1)[1].startswith("lca.wage") else "i9"  # noqa: E731
    out: dict = {"note": "EXPLORATORY: not in the Study 3 declaration; added after the results."}

    # 1. cited evidence on false greens
    cited: dict = {}
    for a in study3.ARMS:
        for c in study3.CONDITIONS:
            for family in ("i9", "wage"):
                cnt = Counter()
                per_model = defaultdict(Counter)
                for m in MODELS:
                    for k, p in preds[(m, a, c)].items():
                        if k in unassessable and fam(k) == family and p.verdict.value == "pass":
                            ev = " ".join(p.evidence_fields).lower()
                            hit = [col for col in PROXY if col.lower() in ev]
                            tag = (hit[0] if len(hit) == 1 else "several proxy columns" if hit
                                   else "WAGE_RATE_OF_PAY_FROM (LCA offered wage)" if "wage_rate_of_pay" in ev
                                   else "other")
                            cnt[tag] += 1
                            per_model[short(m)][tag] += 1
                cited[f"{family}::{a}::{c}"] = {"total": sum(cnt.values()), "by_field": dict(cnt),
                                                "by_model": {k: dict(v) for k, v in per_model.items()}}
    out["cited_evidence_on_false_greens"] = cited
    pr = [cited[f"{f}::decoy::{c}"] for f in ("i9", "wage") for c in study3.CONDITIONS]
    tot = sum(x["total"] for x in pr)
    proxy = sum(v for x in pr for k, v in x["by_field"].items()
                if k != "other" and not k.startswith("WAGE_RATE"))
    out["proxy_arm_false_greens_citing_a_proxy_column"] = {"n": tot, "citing_proxy": proxy,
                                                           "share": round(proxy / tot, 4) if tot else None}

    # shared clusters and draws, as in the declared analysis
    clusters: dict[str, list[str]] = defaultdict(list)
    for k in sorted(unassessable):
        clusters[k.split("|")[0] + "|" + k.split("|", 1)[1].split("::")[0]].append(k)
    cids = sorted(clusters)
    rng = random.Random(SEED)
    draws = [[rng.choice(cids) for _ in cids] for _ in range(DRAWS)]

    def diffs(m, a1, c1, a2, c2):
        va, vb = preds[(m, a1, c1)], preds[(m, a2, c2)]
        # sorted, so float sums do not depend on set iteration order (hash seed)
        return {k: float(vb[k].verdict.value == "pass") - float(va[k].verdict.value == "pass")
                for k in sorted(unassessable) if k in va and k in vb}

    def estimate(spec):
        ds = [d for d in (diffs(m, *spec) for m in MODELS) if d]

        def stat(pick):
            means = []
            for d in ds:
                xs = [d[k] for cl in pick for k in clusters[cl] if k in d]
                if xs:
                    means.append(sum(xs) / len(xs))
            return sum(means) / len(means) if means else None
        boots = sorted(x for x in (stat(p) for p in draws) if x is not None)
        n = len(boots)
        p = 2 * min(sum(x <= 0 for x in boots), sum(x >= 0 for x in boots)) / n
        return {"delta": round(stat(cids), 4), "ci95": [round(boots[int(0.025 * n)], 4),
                                                       round(boots[int(0.975 * n) - 1], 4)],
                "p_two_sided_unadjusted": round(max(p, 1 / DRAWS), 4)}

    # 2. plain-arm contrasts (and the proxy-arm ones recomputed, for the same table)
    out["schema_contrasts_by_arm"] = {
        f"{name} | {arm}": estimate((arm, a, arm, b))
        for name, a, b in (("abstention (offered -> closed)", "abstain_offered", "abstain_closed"),
                           ("definition and warning (closed -> dashboard)", "abstain_closed", "abstain_withheld"))
        for arm in ("plain", "decoy")}

    # 3. cluster sign counts for the proxy-column effect, in exact arithmetic (a cluster
    # whose mean difference is exactly zero must count as zero, not as a rounding residue)
    from fractions import Fraction
    signs = {}
    for cond in ("abstain_withheld", "abstain_offered"):
        per_cluster = []
        for cl in cids:
            ms = []
            for m in MODELS:
                d = diffs(m, "plain", cond, "decoy", cond)
                xs = [Fraction(int(d[k])) for k in clusters[cl] if k in d]
                if xs:
                    ms.append(sum(xs) / len(xs))
            per_cluster.append(sum(ms) / len(ms))
        signs[cond] = {"clusters": len(cids), "positive": sum(x > 0 for x in per_cluster),
                       "zero": sum(x == 0 for x in per_cluster), "negative": sum(x < 0 for x in per_cluster)}
    out["proxy_effect_cluster_signs"] = signs
    out["cluster_composition"] = dict(Counter(cl.split("|")[1] for cl in cids))
    out["firms_per_family"] = {f: len({cl.split("|")[0] for cl in cids if (cl.split("|")[1].startswith("lca.wage")) == (f == "wage")})
                               for f in ("i9", "wage")}

    # 4. where unassessable pairs go
    flow = {}
    for m in MODELS:
        for a in study3.ARMS:
            for c in study3.CONDITIONS:
                cnt = Counter(p.verdict.value for k, p in preds[(m, a, c)].items() if k in unassessable)
                cnt["unanswered"] = len(unassessable) - sum(cnt.values())
                flow[f"{short(m)}::{a}::{c}"] = dict(cnt)
    out["verdict_flow"] = flow

    (ROOT / "docs" / "study3" / "exploratory.json").write_text(json.dumps(out, indent=1))
    print(json.dumps({k: out[k] for k in ("proxy_arm_false_greens_citing_a_proxy_column",
                                          "schema_contrasts_by_arm", "proxy_effect_cluster_signs",
                                          "cluster_composition", "firms_per_family")}, indent=1))
    for k in ("i9::decoy::abstain_offered", "i9::decoy::abstain_withheld", "wage::decoy::abstain_offered",
              "wage::plain::abstain_offered"):
        print(k, cited[k]["total"], cited[k]["by_field"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
