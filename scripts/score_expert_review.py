"""Score returned expert-review workbooks (v3) against the construction labels.

Put each human reviewer's completed workbook in docs/expert_review_v3/returned/
(one file per reviewer). Workbooks completed by AI systems must not be placed there.
No API call. Writes docs/expert_review_v3/results.json.

Reported, per reviewer and pooled:
  - agreement with the construction label, overall and by item group
    (proxy-column unassessable, plain unassessable, decidable violation, decidable control)
  - for unassessable items: share answered pass (an expert false green), fail, needs_evidence
  - Cohen's kappa between each pair of reviewers, and Fleiss' kappa across all
  - Part B: the distribution of answers to each statement
"""

from __future__ import annotations

import itertools
import json
import sys
from collections import Counter
from pathlib import Path

from openpyxl import load_workbook

ROOT = Path(__file__).resolve().parent.parent
KIT = ROOT / "docs" / "expert_review_v3"
KEY = json.loads((ROOT / "docs" / "expert_review_v3_key.json").read_text())
CATS = ("pass", "fail", "needs_evidence", "not_applicable")
SCALE = ("Strongly disagree", "Disagree", "Neutral", "Agree", "Strongly agree")


def group(k: dict) -> str:
    if k["label"] == "needs_evidence":
        return f"unassessable, {k['arm']} firm"
    return "decidable violation" if k["label"] == "fail" else "decidable control"


def read(path: Path) -> dict:
    wb = load_workbook(path, data_only=True)
    a = wb["Part A - Items"]
    items = {}
    for r in range(3, a.max_row + 1):
        i, v = a.cell(r, 1).value, a.cell(r, 7).value
        if i is None or str(i) == "Ex.":
            continue
        items[str(i)] = {"verdict": (str(v).strip() if v else None), "confidence": a.cell(r, 8).value,
                         "relied": a.cell(r, 9).value, "note": a.cell(r, 10).value}
    b = wb["Part B - Statements"]
    stm = {str(b.cell(r, 1).value): b.cell(r, 3).value for r in range(2, b.max_row + 1) if b.cell(r, 1).value}
    y = wb["About you"]
    about = {str(y.cell(r, 1).value): y.cell(r, 2).value for r in range(2, y.max_row + 1) if y.cell(r, 1).value}
    return {"items": items, "statements": stm, "about": about}


def cohen(a: list, b: list) -> float | None:
    pairs = [(x, y) for x, y in zip(a, b) if x and y]
    if not pairs:
        return None
    po = sum(x == y for x, y in pairs) / len(pairs)
    ca, cb = Counter(x for x, _ in pairs), Counter(y for _, y in pairs)
    pe = sum(ca[c] * cb[c] for c in CATS) / len(pairs) ** 2
    return round((po - pe) / (1 - pe), 4) if pe < 1 else None


def fleiss(rows: list[list]) -> float | None:
    rows = [[x for x in r if x] for r in rows]
    rows = [r for r in rows if len(r) >= 2]
    if not rows:
        return None
    n = min(len(r) for r in rows)
    rows = [r[:n] for r in rows]
    N = len(rows)
    p = {c: sum(r.count(c) for r in rows) / (N * n) for c in CATS}
    P = [(sum(r.count(c) ** 2 for c in CATS) - n) / (n * (n - 1)) for r in rows]
    pbar, pe = sum(P) / N, sum(v * v for v in p.values())
    return round((pbar - pe) / (1 - pe), 4) if pe < 1 else None


def main() -> int:
    files = sorted((KIT / "returned").glob("*.xlsx"))
    if not files:
        print("no returned workbooks in", KIT / "returned")
        return 1
    rev = {f.stem: read(f) for f in files}
    ids = sorted(KEY["items"], key=int)
    out = {"n_reviewers": len(rev), "reviewers": {}, "pooled": {}}
    for name, r in rev.items():
        by = {}
        for i in ids:
            k, v = KEY["items"][i], r["items"].get(i, {}).get("verdict")
            g = by.setdefault(group(k), Counter())
            g["n"] += 1
            g["answered"] += v is not None
            g["agree"] += v == k["label"]
            if v:
                g[v] += 1
        out["reviewers"][name] = {
            "agreement_overall": round(sum(r["items"].get(i, {}).get("verdict") == KEY["items"][i]["label"] for i in ids) / len(ids), 4),
            "by_group": {g: dict(c) for g, c in by.items()}, "about": r["about"]}
    for g in sorted({group(KEY["items"][i]) for i in ids}):
        gi = [i for i in ids if group(KEY["items"][i]) == g]
        votes = Counter(rv["items"].get(i, {}).get("verdict") for rv in rev.values() for i in gi)
        out["pooled"][g] = {"items": len(gi), "votes": {k: v for k, v in votes.items() if k},
                            "agreement": round(sum(rv["items"].get(i, {}).get("verdict") == KEY["items"][i]["label"]
                                                   for rv in rev.values() for i in gi) / (len(gi) * len(rev)), 4)}
    names = list(rev)
    out["cohen_kappa"] = {f"{a} vs {b}": cohen([rev[a]["items"].get(i, {}).get("verdict") for i in ids],
                                               [rev[b]["items"].get(i, {}).get("verdict") for i in ids])
                          for a, b in itertools.combinations(names, 2)}
    out["fleiss_kappa"] = fleiss([[rev[n]["items"].get(i, {}).get("verdict") for n in names] for i in ids])
    maj = {}
    for i in ids:
        c = Counter(v for v in (rev[n]["items"].get(i, {}).get("verdict") for n in names) if v)
        if c:
            top, cnt = c.most_common(1)[0]
            if cnt > len(names) / 2:
                maj[i] = top
    out["majority_agreement_with_label"] = {"items_with_majority": len(maj),
                                            "agree": sum(maj[i] == KEY["items"][i]["label"] for i in maj)}
    out["part_b"] = {s: dict(Counter(rv["statements"].get(str(j)) for rv in rev.values()))
                     for j, s in enumerate(KEY["statements"], 1)}
    (KIT / "results.json").write_text(json.dumps(out, indent=1, default=str))
    print(json.dumps({k: out[k] for k in ("n_reviewers", "pooled", "cohen_kappa", "fleiss_kappa",
                                          "majority_agreement_with_label")}, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
