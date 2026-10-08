"""Study 15: real public records in their native formats.

DECLARED before any Study 15 call (docs/STUDY15_DECLARATION.md).

Records are real and rendered in the publisher's own format, outside the packet generator:
  fda       openFDA food enforcement reports (the API's JSON; dates YYYYMMDD; "" = missing)
  usa       USAspending contract award records (the award API's JSON; null = missing)
  lca       DOL LCA disclosure rows (the disclosure file's columns; dates as the file's Excel
            serial day numbers; blank = missing)
Each workflow has two decision rules over real fields, with thresholds set near the fields'
medians, before any model call, so that both outcomes occur. A packet is twelve records of one
source: 20 packets each from openFDA and USAspending, 10 from the LCA rows (50 contents). In each packet four records, chosen by a fixed rule, have one deciding field withheld
(blanked in that format's own convention); values are never altered or invented. The prompts,
solver and labeller are Study 13's, unchanged; the rule statements follow statement_r2.
"""

from __future__ import annotations

import csv
import hashlib
import io
import json
import random
from datetime import date, timedelta
from pathlib import Path

from . import study13 as S
from .contracts import Contract, Fact, Source
from .schema import Entity, Firm, Label, Obligation, Pair, Verdict

DECLARED_ON = "2026-10-08"
ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "study15" / "raw"
DIR = ROOT / "data" / "study15"
WORKFLOWS = ("fda", "usa", "lca")
DOC = {"fda": "fda_enforcement_reports", "usa": "usaspending_awards", "lca": "lca_disclosure"}
EXT = {"fda": "json", "usa": "json", "lca": "csv"}
KEY = {"fda": "recall_number", "usa": "generated_unique_award_id", "lca": "CASE_NUMBER"}
PER_PACKET, WITHHELD = 12, 4
PACKETS = {"fda": 20, "usa": 20, "lca": 10}  # 240, 240 and 120 records
AS_OF = "2026-10-08"

# canonical column (the native field path) -> (kind, unit, plain label)
FIELDS = {
    "fda": {"recall_initiation_date": ("date", None, "date the recall was initiated"),
            "center_classification_date": ("date", None, "date FDA classified the recall"),
            "termination_date": ("date", None, "date the recall was terminated")},
    "usa": {"period_of_performance.start_date": ("date", None, "period of performance start date"),
            "period_of_performance.end_date": ("date", None, "current period of performance end date"),
            "total_obligation": ("amount", "USD", "total amount obligated"),
            "base_and_all_options": ("amount", "USD", "value of the base award and all options")},
    "lca": {"BEGIN_DATE": ("date", None, "employment begin date"),
            "END_DATE": ("date", None, "employment end date"),
            "WAGE_RATE_OF_PAY_FROM": ("amount", "USD per year", "offered wage (lower bound)"),
            "PREVAILING_WAGE": ("amount", "USD per year", "prevailing wage")},
}


def _f(name, kind, wf, col):
    return Fact(name, kind, (Source(DOC[wf], col, KEY[wf]),))


CONTRACTS: dict[str, Contract] = {}


def _add(c: Contract, shifts) -> None:
    CONTRACTS[c.rule_id] = c
    S.EXTRA_SHIFTS[c.rule_id] = shifts


_d = S._d
_add(Contract("fda.classified_30d", "fda",
              "FDA classified the recall no more than 30 calendar days after it was initiated.",
              (_f("initiation date", "date", "fda", "recall_initiation_date"),
               _f("classification date", "date", "fda", "center_classification_date")),
              lambda v: _d(v["classification date"]) <= _d(v["initiation date"]) + timedelta(days=30)),
     [("days", 30)])
_add(Contract("fda.terminated_180d", "fda",
              "the recall was terminated no more than 180 calendar days after it was initiated.",
              (_f("initiation date", "date", "fda", "recall_initiation_date"),
               _f("termination date", "date", "fda", "termination_date")),
              lambda v: _d(v["termination date"]) <= _d(v["initiation date"]) + timedelta(days=180)),
     [("days", 180)])
_add(Contract("usa.period_3y", "usa",
              "the current period of performance ends no more than 1,095 calendar days after it starts.",
              (_f("performance start", "date", "usa", "period_of_performance.start_date"),
               _f("performance end", "date", "usa", "period_of_performance.end_date")),
              lambda v: _d(v["performance end"]) <= _d(v["performance start"]) + timedelta(days=1095)),
     [("days", 1095)])
_add(Contract("usa.obligated_95", "usa",
              "the total amount obligated is at least 0.95 times the value of the base award and all options.",
              (_f("amount obligated", "amount", "usa", "total_obligation"),
               _f("potential value", "amount", "usa", "base_and_all_options")),
              lambda v: 20 * v["amount obligated"] >= 19 * v["potential value"]),  # exactly 0.95
     [("scale", "0.95")])
_add(Contract("lca.wage_105", "lca",
              "the offered wage is at least 1.05 times the prevailing wage.",
              (_f("offered wage", "amount", "lca", "WAGE_RATE_OF_PAY_FROM"),
               _f("prevailing wage", "amount", "lca", "PREVAILING_WAGE")),
              lambda v: 20 * v["offered wage"] >= 21 * v["prevailing wage"]),  # exactly 1.05
     [("scale", "1.05")])
_add(Contract("lca.three_years", "lca",
              "the employment period ends at least 1,095 calendar days after it begins.",
              (_f("begin date", "date", "lca", "BEGIN_DATE"), _f("end date", "date", "lca", "END_DATE")),
              lambda v: _d(v["end date"]) >= _d(v["begin date"]) + timedelta(days=1095)),
     [("days", 1095)])
RULES = {w: [c for c in CONTRACTS.values() if c.workflow == w] for w in WORKFLOWS}


# ---------------------------------------------------------------- native records
def _h(s: str) -> str:
    return hashlib.sha256(s.encode()).hexdigest()


def records(wf: str) -> list:
    """The 120 records in a fixed order (SHA-256 of the identifier)."""
    if wf == "lca":
        with (ROOT / "data" / "real_lca" / "sample_120.csv").open(newline="") as fh:
            rows = list(csv.DictReader(fh))
        return sorted(rows, key=lambda r: _h(r["CASE_NUMBER"]))
    data = json.loads((RAW / ("fda_enforcement.json" if wf == "fda" else "usaspending_awards.json")).read_text())
    return sorted(data, key=lambda r: _h(r[KEY[wf]]))


def _get(rec: dict, path: str):
    cur = rec
    for part in path.split("."):
        cur = cur.get(part) if isinstance(cur, dict) else None
    return cur


def _set(rec: dict, path: str, value) -> None:
    parts = path.split(".")
    cur = rec
    for part in parts[:-1]:
        cur = cur[part]
    cur[parts[-1]] = value


def canonical_value(wf: str, col: str, raw):
    """Native value -> canonical string (ISO date or exact decimal), '' when missing."""
    if raw in (None, ""):
        return ""
    kind = FIELDS[wf][col][0]
    if kind == "date":
        s = str(raw)
        if wf == "fda":
            return f"{s[:4]}-{s[4:6]}-{s[6:8]}"
        if wf == "lca":
            return (date(1899, 12, 30) + timedelta(days=int(float(s)))).isoformat()
        return s[:10]
    return str(raw)


def packet_records(wf: str, k: int) -> tuple[list, list]:
    """(native records with withholding applied, [(entity, rule, column) withheld])."""
    import copy
    recs = copy.deepcopy(records(wf)[k * PER_PACKET:(k + 1) * PER_PACKET])
    rng = random.Random(f"study15-{wf}-{k}")
    withheld = []
    for rec in rng.sample(recs, WITHHELD):
        c = rng.choice(RULES[wf])
        col = rng.choice(c.facts).sources[0].column
        e = rec[KEY[wf]]
        if wf == "lca":
            rec[col] = ""
        elif wf == "fda":
            _set(rec, col, "")
        else:
            _set(rec, col, None)
        withheld.append((e, c.rule_id, col))
    return recs, withheld


def canonical_tables(wf: str, recs: list) -> dict:
    t = DOC[wf]
    return {t: [{KEY[wf]: r[KEY[wf]], **{col: canonical_value(wf, col, _get(r, col) if wf != "lca" else r.get(col))
                                         for col in FIELDS[wf]}} for r in recs]}


def render(wf: str, recs: list) -> str:
    if wf == "fda":
        return json.dumps({"results": recs}, indent=1)
    if wf == "usa":
        return json.dumps(recs, indent=1)
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=list(recs[0].keys()), lineterminator="\n")
    w.writeheader()
    w.writerows(recs)
    return buf.getvalue()


def make_packet(wf: str, k: int):
    recs, withheld = packet_records(wf, k)
    tables = canonical_tables(wf, recs)
    ents = [r[KEY[wf]] for r in recs]
    labels = {f"{c.rule_id}::{e}": S.label(c, tables, e) for c in RULES[wf] for e in ents}
    return recs, tables, ents, labels, withheld


def packet_dir(wf: str, k: int) -> Path:
    return DIR / wf / f"p{k:02d}"


def write_packet(wf: str, k: int) -> dict:
    recs, tables, ents, labels, withheld = make_packet(wf, k)
    d = packet_dir(wf, k)
    d.mkdir(parents=True, exist_ok=True)
    p = d / f"{DOC[wf]}.{EXT[wf]}"
    p.write_text(render(wf, recs))
    cd = DIR / "canonical" / wf / f"p{k:02d}"
    cd.mkdir(parents=True, exist_ok=True)
    for t, rows in tables.items():
        with (cd / f"{t}.csv").open("w", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=[KEY[wf], *FIELDS[wf]])
            w.writeheader()
            w.writerows(rows)
    return {DOC[wf]: p}


# ---------------------------------------------------------------- prompts and firms
def statement(c: Contract) -> str:
    """Study 13's corrected statement form (statement_r2), for these documents."""
    lines = [f"Decision rule: {c.predicate_text}"]
    for f in c.facts:
        s = f.sources[0]
        kind, unit, lab = FIELDS[c.workflow][s.column]
        lines.append(f"  - Fact name `{f.name}`: established only by the {lab} (`{s.column}`) in "
                     f"`{s.table}`. No other document or field establishes it." + (f" Report it in {unit}." if unit else ""))
    return "\n".join(lines)


def obligations() -> list[Obligation]:
    return [Obligation(rule_id=c.rule_id, regime="contract", citation="stated decision rule",
                       summary=c.predicate_text, applies_to="entity", evidence_required=(),
                       data_needed=statement(c)) for c in CONTRACTS.values()]


def firm(wf: str, k: int) -> Firm:
    recs, tables, ents, labels, withheld = make_packet(wf, k)
    sources = write_packet(wf, k)
    pairs = [Pair.make(c.rule_id, e) for c in RULES[wf] for e in ents]
    lab = [Label(pair_id=pr.pair_id, verdict=Verdict(labels[pr.pair_id].label), basis=labels[pr.pair_id].kind)
           for pr in pairs]
    return Firm(firm_id=f"study15-{wf}-p{k:02d}", name=f"Case file {wf}-{k:02d}", as_of=AS_OF, sources=sources,
                entities=[Entity(e, "record", e) for e in ents], pairs=pairs, labels=lab,
                provenance={"workflow": wf, "packet": k, "header": "Case file"})


def contents() -> list[tuple[str, int]]:
    return [(wf, k) for wf in WORKFLOWS for k in range(PACKETS[wf])]


def load_firms(spec: str) -> list[Firm]:
    """spec = '<workflow>'."""
    return [firm(spec, k) for k in range(PACKETS[spec])]
