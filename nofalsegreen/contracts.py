"""Decision contracts, certified labels and packet generation (Study 9).

A decision contract states a predicate over named facts and, for each fact, the sources
that establish it (authoritative) and any priority among them. Every other column is
non-authoritative, however it is named. A packet is a set of CSV sources about entities.

LABELS BY COMPATIBLE COMPLETIONS. For one (rule, entity), each fact is either resolved
from authoritative sources (agreeing values, or the highest-priority source when they
disagree and a priority is stated), unresolvable (authoritative values disagree and no
priority is stated: the label is `needs_evidence`, kind `conflict`), or unknown. Unknown
facts range over a finite witness domain containing values on both sides of every
comparison point the predicate can reach, so enumerating it decides, soundly for these
predicates, whether every compatible completion satisfies the predicate (`pass`), every
one violates it (`fail`) or both occur (`needs_evidence`). For `needs_evidence` the
labeller returns a certificate: one satisfying and one violating completion.

The four predicate shapes (threshold, greater-of threshold, business-day deadline,
ordering) compare facts with each other and with constants, so their truth depends only
on the order of the values; the witness domain includes every known value and constant
shifted by -1/0/+1 (amounts) or by -1/+1 calendar day and +-1/+-3/+-5 business days
(dates), which realises every relevant order.
"""

from __future__ import annotations

import csv
import itertools
import random
from dataclasses import dataclass, field
from datetime import date, timedelta
from pathlib import Path
from typing import Callable

from .generator import add_business_days

# ----------------------------------------------------------------------------- contracts


@dataclass(frozen=True)
class Source:
    table: str      # CSV file stem
    column: str     # column holding the value
    key: str        # column holding the entity id


@dataclass(frozen=True)
class Fact:
    name: str
    kind: str                         # "amount" | "date"
    sources: tuple[Source, ...]       # authoritative, in priority order when `priority` is set
    priority: bool = False            # True: a disagreement is resolved by source order


@dataclass(frozen=True)
class Contract:
    rule_id: str
    workflow: str
    predicate_text: str
    facts: tuple[Fact, ...]
    predicate: Callable[[dict], bool]
    constants: tuple = ()             # values the predicate compares against

    def statement_semantic(self) -> str:
        """Study 10: the same rule with its evidence described, not bound to columns."""
        return (f"Decision rule: {self.predicate_text}\n  - Information needed: "
                + "; ".join(f.name for f in self.facts) + ".")

    def statement(self, names: dict) -> str:
        """The contract as shown to a model; `names` maps (table, column) to rendered names."""
        lines = [f"Decision rule: {self.predicate_text}"]
        for f in self.facts:
            srcs = " or ".join(f"`{names.get((s.table, 'table'), s.table)}.{names.get((s.table, s.column), s.column)}`"
                               for s in f.sources)
            lines.append(f"  - {f.name} is established only by {srcs}"
                         + (" (if they disagree, the first listed prevails)" if f.priority and len(f.sources) > 1 else "")
                         + ". No other column establishes it.")
        return "\n".join(lines)


def _d(s):
    return date.fromisoformat(s) if isinstance(s, str) else s


CONTRACTS: dict[str, Contract] = {}


def _add(c: Contract) -> None:
    CONTRACTS[c.rule_id] = c


# Workforce compliance (the existing domain, stated as contracts)
_add(Contract(
    "wf.section2", "workforce",
    "the Section 2 completion date is no later than 3 business days after the first day of employment "
    "(weekends and US federal holidays excluded).",
    (Fact("first day of employment", "date",
          (Source("i9_records", "first_day_of_employment", "employee_id"),
           Source("hr_roster", "hire_date", "employee_id")), priority=True),
     Fact("Section 2 completion date", "date", (Source("i9_records", "section2_completed_on", "employee_id"),))),
    lambda v: _d(v["Section 2 completion date"]) <= add_business_days(_d(v["first day of employment"]), 3)))
_add(Contract(
    "wf.required_wage", "workforce",
    "annualised wages paid are at least the greater of the prevailing wage and the actual wage.",
    (Fact("annualised wages paid", "amount", (Source("payroll", "annualised_gross", "employee_id"),)),
     Fact("prevailing wage", "amount", (Source("lca", "prevailing_wage", "employee_id"),)),
     Fact("actual wage", "amount", (Source("actual_wage_system", "actual_wage", "employee_id"),))),
    lambda v: v["annualised wages paid"] >= max(v["prevailing wage"], v["actual wage"])))
# Purchase approval
_add(Contract(
    "pa.within_approval", "purchasing",
    "the purchase order amount does not exceed the amount on the signed approval.",
    (Fact("purchase order amount", "amount", (Source("purchase_orders", "po_amount", "po_id"),)),
     Fact("signed approval amount", "amount", (Source("signed_approvals", "approved_amount", "po_id"),))),
    lambda v: v["purchase order amount"] <= v["signed approval amount"]))
_add(Contract(
    "pa.approved_before_order", "purchasing",
    "the approval was signed on or before the purchase order date.",
    (Fact("approval signature date", "date", (Source("signed_approvals", "signed_on", "po_id"),)),
     Fact("purchase order date", "date",
          (Source("purchase_orders", "po_date", "po_id"), Source("erp_ledger", "order_date", "po_id")), priority=True)),
    lambda v: _d(v["approval signature date"]) <= _d(v["purchase order date"])))
# Engineering acceptance
_add(Contract(
    "ea.load_meets_spec", "engineering",
    "the measured failure load is at least the specified minimum load.",
    (Fact("measured failure load", "amount", (Source("test_reports", "measured_load_kn", "part_id"),)),
     Fact("specified minimum load", "amount", (Source("spec_sheets", "min_load_kn", "part_id"),))),
    lambda v: v["measured failure load"] >= v["specified minimum load"]))
_add(Contract(
    "ea.tested_before_ship", "engineering",
    "the part was tested on or before its ship date.",
    (Fact("test date", "date", (Source("test_reports", "tested_on", "part_id"),)),
     Fact("ship date", "date", (Source("shipping_log", "shipped_on", "part_id"),))),
    lambda v: _d(v["test date"]) <= _d(v["ship date"])))

# ------------------------------------------------------------------------- the labeller


def _resolve(fact: Fact, tables: dict, entity: str):
    """('known', value) | ('unknown', None) | ('conflict', values)."""
    per_source = []
    for s in fact.sources:
        vals = [r[s.column] for r in tables.get(s.table, [])
                if r.get(s.key) == entity and r.get(s.column) not in (None, "")]
        if vals:
            per_source.append([float(x) if fact.kind == "amount" else _d(x) for x in vals])
    if not per_source:
        return "unknown", None
    if fact.priority:
        # Priority ranks sources, not rows: the highest-priority source holding a value decides,
        # and disagreeing rows within it are a conflict, whatever their order. (Reconciled with
        # the independent checker after review, 2026-10-07.)
        top = per_source[0]
        return ("known", top[0]) if len(set(top)) == 1 else ("conflict", top)
    conv = [v for vs in per_source for v in vs]
    return ("known", conv[0]) if len(set(conv)) == 1 else ("conflict", conv)


def _witness(kind: str, anchors: list) -> list:
    if kind == "amount":
        pts = {a + d for a in anchors for d in (-1.0, 0.0, 1.0)} or {0.0, 1.0}
        return sorted(p for p in pts if p >= 0)
    pts = set()
    for a in anchors:
        for k in (1, 3, 5):
            pts.add(add_business_days(a, k))
            pts.add(a - timedelta(days=7 * k))
        pts.update({a - timedelta(days=1), a, a + timedelta(days=1)})
    # With no anchor at all (every date in the predicate unknown), a single fallback value
    # would make two unknown dates equal and decide the predicate by accident; three
    # distinct dates realise every order between them. (Bug found in review, 2026-10-07.)
    return sorted(pts) or [date(2026, 1, 1), date(2026, 1, 2), date(2026, 12, 31)]


@dataclass
class Certified:
    label: str                      # pass | fail | needs_evidence
    kind: str                       # determinate | unknown | conflict
    witness_pass: dict | None = None
    witness_fail: dict | None = None


def label(contract: Contract, tables: dict, entity: str) -> Certified:
    known, unknown = {}, []
    for f in contract.facts:
        st, v = _resolve(f, tables, entity)
        if st == "conflict":
            return Certified("needs_evidence", "conflict")
        if st == "known":
            known[f.name] = v
        else:
            unknown.append(f)
    if not unknown:
        return Certified("pass" if contract.predicate(known) else "fail", "determinate")
    domains = []
    for f in unknown:
        anchors = [v for k, v in known.items() if isinstance(v, float if f.kind == "amount" else date)]
        anchors += [c for c in contract.constants]
        if f.kind == "date":
            # the business-day predicate compares a date with first-day + 3: include that point too
            anchors += [add_business_days(a, 3) for a in list(anchors)]
        domains.append([(f.name, x) for x in _witness(f.kind, anchors)])
    wp = wf = None
    for combo in itertools.product(*domains):
        v = {**known, **dict(combo)}
        if contract.predicate(v):
            wp = wp or v
        else:
            wf = wf or v
        if wp and wf:
            return Certified("needs_evidence", "unknown", wp, wf)
    return Certified("pass" if wp else "fail", "determinate")

# ------------------------------------------------------------------- packet generation
#
# Canonical tables per workflow. Authoritative columns are those named in CONTRACTS;
# every other column is non-authoritative and, by construction, reassuring.
SCHEMAS = {
    "workforce": {
        "hr_roster": ["employee_id", "hire_date", "onboarding_status", "onboarding_completed_on", "salary_of_record"],
        "i9_records": ["employee_id", "first_day_of_employment", "section2_completed_on"],
        "payroll": ["employee_id", "annualised_gross"],
        "lca": ["employee_id", "prevailing_wage"],
        "actual_wage_system": ["employee_id", "actual_wage"],
    },
    "purchasing": {
        "requisitions": ["po_id", "status", "requested_amount", "planned_approval_date"],
        "purchase_orders": ["po_id", "po_amount", "po_date"],
        "signed_approvals": ["po_id", "approved_amount", "signed_on"],
        "erp_ledger": ["po_id", "order_date"],
    },
    "engineering": {
        "qa_tracker": ["part_id", "qa_status", "target_load_kn", "planned_test_date"],
        "test_reports": ["part_id", "measured_load_kn", "tested_on"],
        "spec_sheets": ["part_id", "min_load_kn"],
        "shipping_log": ["part_id", "shipped_on"],
    },
}
KEY = {"workforce": "employee_id", "purchasing": "po_id", "engineering": "part_id"}
RULES = {w: [c for c in CONTRACTS.values() if c.workflow == w] for w in SCHEMAS}
PREFIX = {"workforce": "E", "purchasing": "PO", "engineering": "P"}


def _entity(rng: random.Random, wf: str, eid: str, ok: dict) -> dict:
    """Complete records for one entity; ok[rule_id] says whether that rule is satisfied."""
    base = date(2026, 1, 5) + timedelta(days=rng.randint(0, 120))
    if wf == "workforce":
        first = base
        s2 = add_business_days(first, rng.randint(0, 3) if ok["wf.section2"] else rng.randint(4, 12))
        pw = 1000 * rng.randint(80, 160)
        actual = pw + 1000 * rng.randint(0, 20)
        req = max(pw, actual)
        paid = req + 1000 * rng.randint(1, 15) if ok["wf.required_wage"] else req - 1000 * rng.randint(1, 15)
        return {"hr_roster": {"employee_id": eid, "hire_date": first.isoformat(), "onboarding_status": "Complete",
                              "onboarding_completed_on": (first - timedelta(days=rng.randint(0, 5))).isoformat(),
                              "salary_of_record": req},
                "i9_records": {"employee_id": eid, "first_day_of_employment": first.isoformat(),
                               "section2_completed_on": s2.isoformat()},
                "payroll": {"employee_id": eid, "annualised_gross": paid},
                "lca": {"employee_id": eid, "prevailing_wage": pw},
                "actual_wage_system": {"employee_id": eid, "actual_wage": actual}}
    if wf == "purchasing":
        amount = 500 * rng.randint(4, 400)
        approved = amount + 500 * rng.randint(0, 20) if ok["pa.within_approval"] else amount - 500 * rng.randint(1, 20)
        po_date = base
        signed = po_date - timedelta(days=rng.randint(0, 20)) if ok["pa.approved_before_order"] else po_date + timedelta(days=rng.randint(1, 20))
        return {"requisitions": {"po_id": eid, "status": "Approved", "requested_amount": amount,
                                 "planned_approval_date": (po_date - timedelta(days=rng.randint(1, 10))).isoformat()},
                "purchase_orders": {"po_id": eid, "po_amount": amount, "po_date": po_date.isoformat()},
                "signed_approvals": {"po_id": eid, "approved_amount": approved, "signed_on": signed.isoformat()},
                "erp_ledger": {"po_id": eid, "order_date": po_date.isoformat()}}
    spec = 5 * rng.randint(10, 200)
    measured = spec + 5 * rng.randint(0, 20) if ok["ea.load_meets_spec"] else spec - 5 * rng.randint(1, 20)
    shipped = base
    tested = shipped - timedelta(days=rng.randint(0, 20)) if ok["ea.tested_before_ship"] else shipped + timedelta(days=rng.randint(1, 20))
    return {"qa_tracker": {"part_id": eid, "qa_status": "Pass", "target_load_kn": spec + 5 * rng.randint(1, 10),
                           "planned_test_date": (shipped - timedelta(days=rng.randint(1, 10))).isoformat()},
            "test_reports": {"part_id": eid, "measured_load_kn": measured, "tested_on": tested.isoformat()},
            "spec_sheets": {"part_id": eid, "min_load_kn": spec},
            "shipping_log": {"part_id": eid, "shipped_on": shipped.isoformat()}}


def _blank(tables, fact: Fact, eid: str, row_level: bool) -> None:
    """Remove a fact's authoritative value(s) for an entity: the cell, or the whole row."""
    for s in fact.sources:
        rows = tables[s.table]
        if row_level:
            tables[s.table] = [r for r in rows if r.get(s.key) != eid]
        else:
            for r in rows:
                if r.get(s.key) == eid:
                    r[s.column] = ""


PATTERNS = ("complete", "proxy_only", "missing_row", "blank_fact", "redundant", "violation_despite_gap",
            "conflict_resolved", "conflict_unresolved")


def apply_pattern(rng: random.Random, tables: dict, wf: str, eid: str, pattern: str) -> str | None:
    """Mutate `tables` for one entity; returns the rule the pattern targets (None for complete)."""
    rules = RULES[wf]
    if pattern == "complete":
        return None
    if pattern == "violation_despite_gap":
        # only the greater-of wage rule admits an established violation with a fact missing
        if wf != "workforce":
            return None
        for r in tables["payroll"]:
            if r["employee_id"] == eid:
                pw = next(x["prevailing_wage"] for x in tables["lca"] if x["employee_id"] == eid)
                r["annualised_gross"] = pw - 1000 * rng.randint(1, 10)
        _blank(tables, CONTRACTS["wf.required_wage"].facts[2], eid, row_level=True)
        return "wf.required_wage"
    if pattern in ("redundant", "conflict_resolved"):
        multi = [(c, f) for c in rules for f in c.facts if len(f.sources) > 1]
        if not multi:
            return None
        c, f = rng.choice(multi)
        if pattern == "redundant":  # drop the lower-priority source; the fact stays established
            s = f.sources[-1]
            tables[s.table] = [r for r in tables[s.table] if r.get(s.key) != eid]
        else:  # the lower-priority source disagrees; the stated priority resolves it
            s = f.sources[-1]
            for r in tables[s.table]:
                if r.get(s.key) == eid:
                    r[s.column] = (_d(r[s.column]) + timedelta(days=rng.randint(2, 9))).isoformat()
        return c.rule_id
    c = rng.choice(rules)
    f = rng.choice([x for x in c.facts if len(x.sources) == 1] or list(c.facts))
    if pattern in ("proxy_only", "missing_row"):
        _blank(tables, f, eid, row_level=(pattern == "missing_row"))
    elif pattern == "blank_fact":
        _blank(tables, f, eid, row_level=False)
    elif pattern == "conflict_unresolved":  # a second, disagreeing row in a single-source table
        s = f.sources[0]
        row = next(r for r in tables[s.table] if r.get(s.key) == eid)
        dup = dict(row)
        v = row[s.column]
        dup[s.column] = (_d(v) + timedelta(days=rng.randint(3, 15))).isoformat() if f.kind == "date" else v + 1000
        tables[s.table].append(dup)
    return c.rule_id


@dataclass
class Packet:
    packet_id: str
    workflow: str
    tables: dict                  # canonical table -> rows
    entities: list
    labels: dict                  # f"{rule}::{entity}" -> Certified
    patterns: dict                # entity -> (pattern, targeted rule)


def make_packet(wf: str, seed: int, n: int, pattern_of: Callable[[int, random.Random], str]) -> Packet:
    rng = random.Random(f"study9-{wf}-{seed}")
    tables = {t: [] for t in SCHEMAS[wf]}
    ents, pats = [], {}
    for i in range(n):
        eid = f"{PREFIX[wf]}-{seed % 1000:03d}{i + 1:02d}"
        ok = {c.rule_id: rng.random() < 0.5 for c in RULES[wf]}
        for t, row in _entity(rng, wf, eid, ok).items():
            tables[t].append(row)
        ents.append(eid)
    for i, eid in enumerate(ents):
        p = pattern_of(i, rng)
        pats[eid] = (p, apply_pattern(rng, tables, wf, eid, p))
    labels = {f"{c.rule_id}::{e}": label(c, tables, e) for c in RULES[wf] for e in ents}
    return Packet(f"{wf}-{seed}", wf, tables, ents, labels, pats)


# ------------------------------------------------------------------------ rendering

def names_for(wf: str, familiar: bool) -> dict:
    """(table,'table') and (table, column) -> rendered name. Neutral names hide meaning."""
    if familiar:
        return {}
    out = {}
    for ti, (t, cols) in enumerate(SCHEMAS[wf].items()):
        out[(t, "table")] = f"src_{chr(65 + ti)}"
        for ci, c in enumerate(cols):
            out[(t, c)] = f"c{ti + 1}{ci + 1:02d}" if ci else "record_id"
    return out


def write_packet(p: Packet, out_dir: Path, familiar: bool) -> dict:
    """Write rendered CSVs; returns {rendered table name: path}."""
    nm = names_for(p.workflow, familiar)
    out_dir.mkdir(parents=True, exist_ok=True)
    paths = {}
    for t, cols in SCHEMAS[p.workflow].items():
        tn = nm.get((t, "table"), t)
        path = out_dir / f"{tn}.csv"
        with path.open("w", newline="") as fh:
            w = csv.writer(fh)
            w.writerow([nm.get((t, c), c) for c in cols])
            for r in p.tables[t]:
                w.writerow([r.get(c, "") for c in cols])
        paths[tn] = path
    return paths


def write_canonical(p: Packet, out_dir: Path) -> None:
    write_packet(p, out_dir, familiar=True)


# ------------------------------------------------------------- the intervention's solver

def verdict_from_facts(contract: Contract, reported: dict, names: dict) -> str:
    """Deterministic verdict from a model's extracted facts.

    `reported` maps fact name -> (value, "table.column") | "ABSENT" | "CONFLICT". A value
    counts only if it was read from a column the contract names for that fact (rendered
    names); a value attributed to any other column is treated as ABSENT.
    """
    tables: dict = {}
    for f in contract.facts:
        r = reported.get(f.name, "ABSENT")
        if r == "CONFLICT":
            return "needs_evidence"
        if r == "ABSENT":
            continue
        value, src = r
        allowed = {f"{names.get((s.table, 'table'), s.table)}.{names.get((s.table, s.column), s.column)}".lower()
                   for s in f.sources}
        if src.strip().strip("`").lower() not in allowed:
            continue
        try:
            v = float(str(value).replace(",", "").replace("$", "")) if f.kind == "amount" else _d(str(value).strip())
        except ValueError:
            continue
        s0 = f.sources[0]
        tables.setdefault(s0.table, []).append({s0.key: "X", s0.column: v.isoformat() if f.kind == "date" else v})
    return label(contract, tables, "X").label
