"""Fetch Study 15's public records (docs/STUDY15_DECLARATION.md). Run once; the raw responses
are kept in data/study15/raw with their SHA-256 in data/study15/PROVENANCE.json.

Sources, each read through its official public interface and kept in its native form:
  openFDA food enforcement reports  https://api.fda.gov/food/enforcement.json
  USAspending contract awards       https://api.usaspending.gov/api/v2/ (search, then award detail)
  DOL LCA disclosure rows           data/real_lca/sample_120.csv (Study 5; data/real_lca/PROVENANCE.md)

Selection is fixed in advance: from a stated query, keep the 240 records whose SHA-256 of the
record identifier is smallest. A first fetch kept 120 by the same rule (USAspending from a
search pool half this size); both were enlarged for power before any Study 15 call, and the
first fetch is kept in data/study15/raw_first120."""

from __future__ import annotations

import hashlib
import json
import sys
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "study15" / "raw"
N = 240


def h(s: str) -> str:
    return hashlib.sha256(s.encode()).hexdigest()


def get(url: str, body: dict | None = None) -> dict:
    for attempt in range(5):
        try:
            req = urllib.request.Request(url, data=json.dumps(body).encode() if body else None,
                                         headers={"Content-Type": "application/json", "User-Agent": "nofalsegreen-research"})
            with urllib.request.urlopen(req, timeout=60) as r:
                return json.loads(r.read())
        except Exception as e:  # noqa: BLE001
            print("retry", attempt, type(e).__name__, str(e)[:100], flush=True)
            time.sleep(5 * (attempt + 1))
    raise SystemExit(f"failed: {url}")


def fda() -> list:
    q = "recall_initiation_date:%5B20190101+TO+20221231%5D"
    recs, skip = [], 0
    while True:
        d = get(f"https://api.fda.gov/food/enforcement.json?search={q}&sort=report_date:asc&limit=1000&skip={skip}")
        recs += d["results"]
        skip += 1000
        if skip >= d["meta"]["results"]["total"] or skip >= 25000:
            break
    print("fda pool", len(recs))
    return sorted(recs, key=lambda r: h(r["recall_number"]))[:N]


def usaspending() -> list:
    pool = []
    for page in range(1, 21):
        d = get("https://api.usaspending.gov/api/v2/search/spending_by_award/",
                {"filters": {"award_type_codes": ["A", "B", "C", "D"],
                             "time_period": [{"start_date": "2020-10-01", "end_date": "2021-09-30"}]},
                 "fields": ["Award ID", "generated_internal_id"], "limit": 100, "page": page,
                 "sort": "Award ID", "order": "asc"})
        pool += [r["generated_internal_id"] for r in d["results"]]
    print("usaspending pool", len(pool))
    keep = sorted(set(pool), key=h)[:N]
    out = []
    for gid in keep:
        out.append(get(f"https://api.usaspending.gov/api/v2/awards/{gid}/"))
        time.sleep(0.3)
    return out


if __name__ == "__main__":
    RAW.mkdir(parents=True, exist_ok=True)
    prov = {}
    for name, fn in (("fda_enforcement", fda), ("usaspending_awards", usaspending)):
        p = RAW / f"{name}.json"
        if not p.exists():
            p.write_text(json.dumps(fn(), indent=1, sort_keys=True))
        prov[name] = {"sha256": hashlib.sha256(p.read_bytes()).hexdigest(), "records": len(json.loads(p.read_text())),
                      "retrieved": time.strftime("%Y-%m-%d")}
    lca = ROOT / "data" / "real_lca" / "sample_120.csv"
    prov["lca_disclosure"] = {"sha256": hashlib.sha256(lca.read_bytes()).hexdigest(), "source": str(lca.relative_to(ROOT))}
    (ROOT / "data" / "study15" / "PROVENANCE.json").write_text(json.dumps(prov, indent=1))
    print(json.dumps(prov, indent=1))
