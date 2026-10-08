"""Differential test: the generator's labeller against the independent checker on random packets.

The 2,304 retained labels cover only the patterns the generator emits. This samples the wider input
space the contract specification admits: 0-3 rows per entity per table, duplicate and disagreeing
rows, blank cells, every source combination for priority facts, simultaneous missing facts, and
values drawn from a small pool so that ties and boundaries are common. Every packet is also
re-labelled with its rows shuffled, which must not change any label. No API call. Writes
docs/study9/differential.json.
"""

from __future__ import annotations

import csv
import json
import random
import sys
import tempfile
from collections import Counter
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "labelcheck"))

from nofalsegreen import contracts as C  # noqa: E402
import contract_checker as K  # noqa: E402

SEED, N_PACKETS, ENTITIES = 20261007, 3000, 4
D0 = date(2026, 1, 2)  # a Friday before Martin Luther King Day: business-day edges are common


def _value(rng, col):
    if any(w in col for w in ("date", "_on", "first_day")):
        return (D0 + timedelta(days=rng.randint(0, 12))).isoformat()
    return str(rng.choice([90, 99, 100, 101, 110, 120]) * 1000) if "wage" in col or "gross" in col \
        else str(rng.choice([8, 9, 10, 11, 12]) * (10 if "kn" in col else 1000))


def packet(rng, wf):
    tables = {}
    for t, cols in C.SCHEMAS[wf].items():
        rows = []
        for e in range(ENTITIES):
            for _ in range(rng.choice([0, 1, 1, 1, 2, 2, 3])):
                rows.append({c: (f"{C.PREFIX[wf]}{e}" if c == C.KEY[wf]
                                 else "" if rng.random() < 0.2 else _value(rng, c)) for c in cols})
        tables[t] = rows
    return tables


def write(tables, wf, d):
    for t, rows in tables.items():
        with (d / f"{t}.csv").open("w", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=C.SCHEMAS[wf][t])
            w.writeheader()
            w.writerows(rows)


def labels(tables, wf):
    ents = sorted({r[C.KEY[wf]] for rows in tables.values() for r in rows})
    return {f"{c.rule_id}::{e}": C.label(c, tables, e).label for c in C.RULES[wf] for e in ents}


def main() -> int:
    rng = random.Random(SEED)
    out = {"seed": SEED, "packets": 0, "labels": 0, "disagreements": [], "permutation_changes": 0,
           "label_counts": Counter(), "cases": Counter()}
    with tempfile.TemporaryDirectory() as tmp:
        for i in range(N_PACKETS):
            wf = sorted(C.SCHEMAS)[i % 3]
            t = packet(rng, wf)
            d = Path(tmp) / str(i)
            d.mkdir()
            write(t, wf, d)
            mine, theirs = labels(t, wf), K.check(wf, str(d))
            shuffled = {k: rng.sample(v, len(v)) for k, v in t.items()}
            out["permutation_changes"] += sum(labels(shuffled, wf)[k] != v for k, v in mine.items())
            out["packets"] += 1
            out["labels"] += len(mine)
            for k, v in mine.items():
                out["label_counts"][v] += 1
                if theirs.get(k) != v:
                    out["disagreements"].append({"packet": i, "workflow": wf, "pair": k, "generator": v,
                                                 "checker": theirs.get(k)})
            for c in C.RULES[wf]:
                for e in {r[C.KEY[wf]] for rows in t.values() for r in rows}:
                    sts = [C._resolve(f, t, e)[0] for f in c.facts]
                    out["cases"]["duplicate rows in a source" if any(
                        sum(bool(r[C.KEY[wf]] == e and r.get(s.column)) for r in t.get(s.table, [])) > 1
                        for f in c.facts for s in f.sources) else "single rows"] += 1
                    out["cases"][f"{sts.count('unknown')} unknown, {sts.count('conflict')} conflicting"] += 1
    out["n_disagreements"] = len(out["disagreements"])
    out["disagreements"] = out["disagreements"][:20]
    out["label_counts"], out["cases"] = dict(sorted(out["label_counts"].items())), dict(sorted(out["cases"].items()))
    (ROOT / "docs" / "study9" / "differential.json").write_text(json.dumps(out, indent=1))
    print({k: v for k, v in out.items() if k != "disagreements"})
    return 0 if not out["n_disagreements"] and not out["permutation_changes"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
