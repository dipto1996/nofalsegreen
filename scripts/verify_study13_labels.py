"""Study 13 and Study 14 labels against the independent checker (labelcheck/study13_checker.py).

1. Every label of every test and parser-development packet agrees with the checker.
2. Every needs_evidence certificate: both completions, written as records, are judged by the
   checker to pass and to fail respectively.
3. Random packets beyond the generator's patterns (0-3 rows per entity per document,
   disagreeing duplicates, blanks, boundary-heavy values) agree, and shuffling rows never
   changes a label. No API call. Writes docs/study13/label_check.json.
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
from nofalsegreen import study13 as S  # noqa: E402
import study13_checker as K  # noqa: E402

N_FUZZ, SEED = 3000, 20261013


def write(tables, wf, d: Path):
    d.mkdir(parents=True, exist_ok=True)
    for t, cols in S.SCHEMAS[wf].items():
        with (d / f"{t}.csv").open("w", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=cols)
            w.writeheader()
            w.writerows(tables.get(t, []))


def completion(c, values, key):
    """Records realising one completion: each fact's value in its first source."""
    tables = {}
    for f in c.facts:
        s = f.sources[0]
        v = values[f.name]
        tables.setdefault(s.table, {})[s.column] = v.isoformat() if isinstance(v, date) else str(v)
    return {t: [{key: "X", **cols}] for t, cols in tables.items()}


def labels(tables, wf):
    ents = sorted({r[S.KEY[wf]] for rows in tables.values() for r in rows if r.get(S.KEY[wf])})
    return {f"{c.rule_id}::{e}": S.label(c, tables, e) for c in S.RULES[wf] for e in ents}


def fuzz_value(rng, kind, col):
    if kind == "date":
        return (date(2026, 6, 26) + timedelta(days=rng.choice([0, 1, 2, 5, 9, 14, 15, 89, 90, 91, 364, 365, 366]))).isoformat()
    # integers and decimals, including pairs on the 1.2x boundary (0.10 / 0.12, 12.5 / 15) and
    # equal values written differently (0.1 / 0.10); added after review, 2026-10-08
    return rng.choice(["0", "5", "6", "10", "12", "50", "60", "100", "120",
                       "0.1", "0.10", "0.12", "0.119", "0.121", "12.5", "15", "15.0", "0.05", "0.06"])


def main() -> int:
    out = {"labels": 0, "agree": 0, "disagreements": [], "certificates": 0, "certificates_verified": 0,
           "kinds": Counter(), "fuzz_packets": 0, "fuzz_labels": 0, "fuzz_disagreements": 0,
           "fuzz_permutation_changes": 0, "fuzz_label_counts": Counter()}
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        for wf in S.WORKFLOWS:
            for seed in S.SEEDS + S.PARSER_DEV_SEEDS + tuple(range(1401, 1411)):  # Study 14 contents too
                p = S.make_packet(wf, seed)
                d = tmp / f"{wf}-{seed}"
                write(p.tables, wf, d)
                theirs = K.check(wf, str(d))
                st = out.setdefault("by_study", {}).setdefault("14" if seed >= 1401 else "13", Counter())
                for k, cert in sorted(p.labels.items()):
                    out["labels"] += 1
                    st["labels"] += 1
                    st["agree"] += theirs.get(k) == cert.label
                    st["missing_value_certificates"] += cert.kind == "unknown"
                    out["kinds"][cert.kind] += 1
                    if theirs.get(k) == cert.label:
                        out["agree"] += 1
                    else:
                        out["disagreements"].append({"packet": p.packet_id, "pair": k, "labeller": cert.label,
                                                     "checker": theirs.get(k)})
                    if cert.kind == "unknown":
                        c = S.CONTRACTS[k.split("::")[0]]
                        res = []
                        for want, vals in (("pass", cert.witness_pass), ("fail", cert.witness_fail)):
                            dd = tmp / f"cert-{out['certificates']}-{want}"
                            write(completion(c, vals, S.KEY[wf]), wf, dd)
                            res.append(K.check(wf, str(dd)).get(f"{c.rule_id}::X") == want)
                        out["certificates"] += 2
                        out["certificates_verified"] += sum(res)
                        st["completions"] += 2
                        st["completions_verified"] += sum(res)
        rng = random.Random(SEED)
        for i in range(N_FUZZ):
            wf = S.WORKFLOWS[i % 3]
            t = {}
            for doc, cols in S.DOCS[wf].items():
                t[doc] = [{c: (f"{S.PREFIX[wf]}{e}" if k == "id" else "" if rng.random() < 0.2
                               else fuzz_value(rng, k, c) if k in ("date", "amount") else "x")
                           for c, k, _, _ in cols}
                          for e in range(3) for _ in range(rng.choice([0, 1, 1, 1, 2, 2, 3]))]
            d = tmp / f"fz{i}"
            write(t, wf, d)
            mine = labels(t, wf)
            theirs = K.check(wf, str(d))
            sh = labels({k: rng.sample(v, len(v)) for k, v in t.items()}, wf)
            out["fuzz_packets"] += 1
            out["fuzz_labels"] += len(mine)
            for k, v in mine.items():
                out["fuzz_label_counts"][v.label] += 1
                out["fuzz_disagreements"] += theirs.get(k) != v.label
                out["fuzz_permutation_changes"] += sh[k].label != v.label
                if theirs.get(k) != v.label and len(out["disagreements"]) < 20:
                    out["disagreements"].append({"fuzz": i, "pair": k, "labeller": v.label, "checker": theirs.get(k)})
    out["kinds"], out["fuzz_label_counts"] = dict(out["kinds"]), dict(sorted(out["fuzz_label_counts"].items()))
    out["by_study"] = {k: dict(sorted(v.items())) for k, v in sorted(out["by_study"].items())}
    (ROOT / "docs" / "study13").mkdir(parents=True, exist_ok=True)
    (ROOT / "docs" / "study13" / "label_check.json").write_text(json.dumps(out, indent=1))
    print({k: v for k, v in out.items() if k != "disagreements"})
    print(out["disagreements"][:8])
    ok = out["agree"] == out["labels"] and out["certificates_verified"] == out["certificates"] \
        and not out["fuzz_disagreements"] and not out["fuzz_permutation_changes"]
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
