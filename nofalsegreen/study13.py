"""Study 13: held-out contracts on heterogeneous records.

Six decision rules that appear in no earlier study (docs/study13/CONTRACT_SPEC.md), with new
predicate shapes: a two-sided date window, a deadline with a business-day duration, a
four-fact conjunction, a three-date ordering, a 365-day validity window and a scaled
threshold. Each rule has at least one prioritised fact, except the three-way match.

The records are rendered in six layouts. L1-L3 are development layouts, written with the
generator and shown to the author of the parsing baseline. L4-L6 are held-out layouts,
designed by a separate author from a brief (nofalsegreen/study13_heldout.py) and never
shown to the parser's author. Every layout carries the same canonical records, written
alongside as CSV for the checkers.

Labels: the contract semantics of Study 9 (priority ranks sources; disagreeing rows in the
deciding source are a conflict; unknown facts range over all values). The labeller
enumerates candidate values that include every critical point of the predicate on both
sides; an independently written checker (labelcheck/study13_checker.py) decides the same
labels exactly, and scripts/verify_study13_labels.py compares them and checks every
certificate.
"""

from __future__ import annotations

import csv
import itertools
import random
from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path

from .contracts import Certified, Contract, Fact, Source
from .generator import add_business_days
from .schema import Entity, Firm, Label, Obligation, Pair, Verdict

DECLARED_ON = "2026-10-07"
ROOT = Path(__file__).resolve().parent.parent
DIR = ROOT / "data" / "study13"
WORKFLOWS = ("workforce", "purchasing", "engineering")
KEY = {"workforce": "employee_id", "purchasing": "po_id", "engineering": "part_id"}
PREFIX = {"workforce": "E", "purchasing": "PO", "engineering": "P"}
DEV_LAYOUTS, HELDOUT_LAYOUTS = ("L1", "L2", "L3"), ("L4", "L5", "L6")
LAYOUTS = DEV_LAYOUTS + HELDOUT_LAYOUTS
SEEDS = (1301, 1302)          # rendered in every layout: layouts are paired on content
PARSER_DEV_SEEDS = (1391, 1392, 1393)  # development packets for the parser's author (L1-L3 only)
N_ENTITIES = 16
AS_OF = "2026-10-07"


def _d(s):
    return date.fromisoformat(s) if isinstance(s, str) else s


# ---------------------------------------------------------------- documents
# (column, kind, unit, plain-language label). kind: id | date | amount | text.
DOCS = {
    "workforce": {
        "hr_roster": [("employee_id", "id", None, "employee number"),
                      ("reverification_status", "text", None, "reverification status"),
                      ("visa_end_date", "date", None, "visa end date"),
                      ("notice_status", "text", None, "LCA notice status"),
                      ("planned_filing_date", "date", None, "planned LCA filing date")],
        "work_authorizations": [("employee_id", "id", None, "employee number"),
                                ("document_type", "text", None, "document type"),
                                ("expires_on", "date", None, "authorization expiry date")],
        "ead_cards": [("employee_id", "id", None, "employee number"),
                      ("card_expiry", "date", None, "card expiry date")],
        "reverifications": [("employee_id", "id", None, "employee number"),
                            ("completed_on", "date", None, "reverification completion date")],
        "lca_notices": [("employee_id", "id", None, "employee number"),
                        ("posted_on", "date", None, "date the notice was posted"),
                        ("removed_on", "date", None, "date the notice was removed")],
        "lca_filings": [("employee_id", "id", None, "employee number"),
                        ("filed_on", "date", None, "LCA filing date")],
        "dol_receipts": [("employee_id", "id", None, "employee number"),
                         ("receipt_date", "date", None, "DOL receipt date")],
    },
    "purchasing": {
        "requisitions": [("po_id", "id", None, "purchase order number"),
                         ("status", "text", None, "requisition status"),
                         ("requested_amount", "amount", "USD", "requested amount"),
                         ("expected_delivery", "date", None, "expected delivery date")],
        "purchase_orders": [("po_id", "id", None, "purchase order number"),
                            ("po_amount", "amount", "USD", "order amount")],
        "invoices": [("po_id", "id", None, "purchase order number"),
                     ("invoice_amount", "amount", "USD", "invoice amount"),
                     ("invoiced_qty", "amount", "units", "quantity invoiced"),
                     ("due_on", "date", None, "payment due date")],
        "receipts": [("po_id", "id", None, "purchase order number"),
                     ("received_qty", "amount", "units", "quantity received"),
                     ("received_on", "date", None, "date goods were received")],
        "warehouse_scans": [("po_id", "id", None, "purchase order number"),
                            ("scan_date", "date", None, "warehouse scan date")],
        "payments": [("po_id", "id", None, "purchase order number"),
                     ("paid_on", "date", None, "payment date")],
    },
    "engineering": {
        "parts": [("part_id", "id", None, "part number"),
                  ("qa_status", "text", None, "QA status"),
                  ("target_load_kn", "amount", "kN", "target load"),
                  ("planned_test_date", "date", None, "planned test date")],
        "calibration_log": [("part_id", "id", None, "part number"),
                            ("calibrated_on", "date", None, "calibration date of the test rig")],
        "test_reports": [("part_id", "id", None, "part number"),
                         ("tested_on", "date", None, "test date"),
                         ("measured_load_kn", "amount", "kN", "measured failure load")],
        "lab_certificates": [("part_id", "id", None, "part number"),
                             ("test_date", "date", None, "date of test"),
                             ("certified_load_kn", "amount", "kN", "certified failure load")],
        "spec_sheets": [("part_id", "id", None, "part number"),
                        ("min_load_kn", "amount", "kN", "specified minimum failure load")],
    },
}
SCHEMAS = {wf: {t: [c[0] for c in cols] for t, cols in docs.items()} for wf, docs in DOCS.items()}
META = {(t, c[0]): c for docs in DOCS.values() for t, cols in docs.items() for c in cols}


# ---------------------------------------------------------------- contracts
def _src(t, c, wf):
    return Source(t, c, KEY[wf])


def _f(name, kind, wf, *tc):
    return Fact(name, kind, tuple(_src(t, c, wf) for t, c in tc), priority=len(tc) > 1)


CONTRACTS: dict[str, Contract] = {}
# Per rule, the maps that carry a known value to the comparison points the predicate can
# reach (the candidate generator also applies their inverses).
SHIFTS: dict[str, list] = {}


def _add(c: Contract, shifts) -> None:
    CONTRACTS[c.rule_id] = c
    SHIFTS[c.rule_id] = shifts


_add(Contract("wf.reverify_window", "workforce",
              "the reverification was completed no earlier than 90 calendar days before, and no later than, "
              "the expiry of the employee's work authorization.",
              (_f("authorization expiry", "date", "workforce", ("work_authorizations", "expires_on"), ("ead_cards", "card_expiry")),
               _f("reverification date", "date", "workforce", ("reverifications", "completed_on"))),
              lambda v: _d(v["authorization expiry"]) - timedelta(days=90) <= _d(v["reverification date"]) <= _d(v["authorization expiry"])),
     [("days", 90)])
_add(Contract("wf.notice_posting", "workforce",
              "the LCA notice was posted on or before the LCA filing date, and removed no earlier than 10 business "
              "days after it was posted (weekends and US federal holidays excluded).",
              (_f("notice posted", "date", "workforce", ("lca_notices", "posted_on")),
               _f("notice removed", "date", "workforce", ("lca_notices", "removed_on")),
               _f("LCA filed", "date", "workforce", ("lca_filings", "filed_on"), ("dol_receipts", "receipt_date"))),
              lambda v: _d(v["notice posted"]) <= _d(v["LCA filed"])
              and _d(v["notice removed"]) >= add_business_days(_d(v["notice posted"]), 10)),
     [("bdays", 10)])
_add(Contract("pa.three_way_match", "purchasing",
              "the invoice amount does not exceed the purchase order amount, and the quantity received is at least "
              "the quantity invoiced.",
              (_f("invoice amount", "amount", "purchasing", ("invoices", "invoice_amount")),
               _f("order amount", "amount", "purchasing", ("purchase_orders", "po_amount")),
               _f("quantity received", "amount", "purchasing", ("receipts", "received_qty")),
               _f("quantity invoiced", "amount", "purchasing", ("invoices", "invoiced_qty"))),
              lambda v: v["invoice amount"] <= v["order amount"] and v["quantity received"] >= v["quantity invoiced"]),
     [])
_add(Contract("pa.paid_in_window", "purchasing",
              "payment was made on or after the date the goods were received, and on or before the payment due date.",
              (_f("goods received", "date", "purchasing", ("receipts", "received_on"), ("warehouse_scans", "scan_date")),
               _f("payment date", "date", "purchasing", ("payments", "paid_on")),
               _f("payment due", "date", "purchasing", ("invoices", "due_on"))),
              lambda v: _d(v["goods received"]) <= _d(v["payment date"]) <= _d(v["payment due"])),
     [])
_add(Contract("ea.calibration_current", "engineering",
              "the part was tested on or after the test rig's calibration date and no more than 365 calendar days "
              "after it.",
              (_f("calibration date", "date", "engineering", ("calibration_log", "calibrated_on")),
               _f("test date", "date", "engineering", ("test_reports", "tested_on"), ("lab_certificates", "test_date"))),
              lambda v: _d(v["calibration date"]) <= _d(v["test date"]) <= _d(v["calibration date"]) + timedelta(days=365)),
     [("days", 365)])
_add(Contract("ea.load_with_margin", "engineering",
              "the measured failure load is at least 1.2 times the specified minimum failure load (kN).",
              (_f("measured load", "amount", "engineering", ("lab_certificates", "certified_load_kn"), ("test_reports", "measured_load_kn")),
               _f("specified minimum", "amount", "engineering", ("spec_sheets", "min_load_kn"))),
              lambda v: 5 * v["measured load"] >= 6 * v["specified minimum"]),  # M >= 1.2 N, exactly
     [("scale", 1.2)])
RULES = {w: [c for c in CONTRACTS.values() if c.workflow == w] for w in WORKFLOWS}


# ---------------------------------------------------------------- the labeller
def _value(kind, raw):
    return float(raw) if kind == "amount" else _d(raw)


def resolve(fact: Fact, tables: dict, entity: str):
    """('known', v) | ('unknown', None) | ('conflict', values): the spec's step 1."""
    for s in fact.sources:
        vals = {_value(fact.kind, r[s.column]) for r in tables.get(s.table, [])
                if r.get(s.key) == entity and r.get(s.column) not in (None, "")}
        if len(vals) == 1:
            return "known", vals.pop()
        if vals:
            return "conflict", sorted(vals)
    return "unknown", None


def _bd_back(d: date, n: int) -> date:
    """The latest date x with add_business_days(x, n) <= d."""
    x = d
    while add_business_days(x, n) > d:
        x -= timedelta(days=1)
    return x


def candidates(rule_id: str, kind: str, known: list, n_unknown: int) -> list:
    """Values for one unknown fact: every critical point of the predicate on both sides.

    Amounts: each known value, its images under the rule's scale and inverse scale, each
    +-0.5 (values are integers, so no comparison point lies strictly between), plus a
    ladder of distinct values so several unknowns can take every relative order. Dates:
    each known date and its images under the rule's day and business-day shifts and their
    inverses, each +-1 day, plus a ladder. A business-day shift is a non-decreasing step
    function, so its inverse image is bracketed by _bd_back and the day after."""
    pts = set()
    for k in known:
        imgs = {k}
        for typ, n in SHIFTS[rule_id]:
            if kind == "amount" and typ == "scale":
                imgs |= {k * n, k / n}
            if kind == "date" and typ == "days":
                imgs |= {k + timedelta(days=n), k - timedelta(days=n)}
            if kind == "date" and typ == "bdays":
                b = _bd_back(k, n)
                imgs |= {add_business_days(k, n), b, b + timedelta(days=1)}
        for x in imgs:
            pts |= ({x - 0.5, x, x + 0.5} if kind == "amount" else {x - timedelta(days=1), x, x + timedelta(days=1)})
    m = max(n_unknown, 1) + 1
    if kind == "amount":
        top = max([0.0, *known])
        pts |= {0.0, *(top * 3 + 1000.0 * (i + 1) * 3 for i in range(m))}
        return sorted(p for p in pts if p >= 0)
    ref = min(known) if known else date(2026, 1, 5)
    hi = max(known) if known else ref
    pts |= {ref - timedelta(days=1000 * (i + 1)) for i in range(m)} | {hi + timedelta(days=1000 * (i + 1)) for i in range(m)}
    return sorted(pts)


def label(contract: Contract, tables: dict, entity: str) -> Certified:
    known, unknown = {}, []
    for f in contract.facts:
        st, v = resolve(f, tables, entity)
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
        ks = [v for g, v in known.items() if next(x for x in contract.facts if x.name == g).kind == f.kind]
        n = sum(x.kind == f.kind for x in unknown)
        domains.append([(f.name, x) for x in candidates(contract.rule_id, f.kind, ks, n)])
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


def verdict_from_facts(contract: Contract, reported: dict) -> str:
    """The solver. `reported`: fact name -> (value, document) | 'ABSENT' | 'CONFLICT'.

    A value counts only if it was read from a document the contract names for that fact; a
    value from any other document is treated as ABSENT."""
    tables: dict = {}
    for f in contract.facts:
        r = reported.get(f.name, "ABSENT")
        if r == "CONFLICT":
            return "needs_evidence"
        if r == "ABSENT":
            continue
        value, doc = r
        doc = doc.strip().strip("`").split(".")[0].lower()
        s = next((x for x in f.sources if x.table == doc), None)
        if s is None:
            continue
        try:
            v = float(str(value).replace(",", "").replace("$", "")) if f.kind == "amount" else _d(str(value).strip())
        except ValueError:
            continue
        tables.setdefault(s.table, []).append({s.key: "X", s.column: v.isoformat() if f.kind == "date" else v})
    return label(contract, tables, "X").label


# ---------------------------------------------------------------- packets
PATTERNS = ("complete", "adverse_with_proxy", "proxy_only", "missing_row", "blank_fact", "redundant",
            "violation_despite_gap", "conflict_resolved", "conflict_lower_dup", "conflict_top_dup",
            "conflict_unresolved", "all_gap")


def _entity(rng: random.Random, wf: str, eid: str, ok: dict) -> dict:
    """Complete canonical records for one entity; ok[rule] says whether the rule is satisfied.
    About one in five values sits exactly on a boundary of its rule."""
    base = date(2026, 1, 5) + timedelta(days=rng.randint(0, 200))
    edge = rng.random() < 0.2
    if wf == "workforce":
        e = base + timedelta(days=rng.randint(60, 400))
        if ok["wf.reverify_window"]:
            r = e - timedelta(days=rng.choice([0, 90]) if edge else rng.randint(1, 89))
        else:
            r = e - timedelta(days=91 + rng.randint(0, 60)) if rng.random() < 0.5 else e + timedelta(days=rng.randint(1, 30))
        p = base
        q_min = add_business_days(p, 10)
        if ok["wf.notice_posting"]:
            q, f = q_min + timedelta(days=0 if edge else rng.randint(1, 20)), p + timedelta(days=0 if edge else rng.randint(1, 25))
        elif rng.random() < 0.5:  # removed too early
            q, f = q_min - timedelta(days=rng.randint(1, 5)), p + timedelta(days=rng.randint(0, 25))
        else:                     # filed before posting
            q, f = q_min + timedelta(days=rng.randint(0, 20)), p - timedelta(days=rng.randint(1, 20))
        return {"hr_roster": {"employee_id": eid, "reverification_status": "Complete",
                              "visa_end_date": (e + timedelta(days=rng.randint(30, 400))).isoformat(),
                              "notice_status": "Posted", "planned_filing_date": (p + timedelta(days=rng.randint(1, 30))).isoformat()},
                "work_authorizations": {"employee_id": eid, "document_type": "EAD", "expires_on": e.isoformat()},
                "ead_cards": {"employee_id": eid, "card_expiry": e.isoformat()},
                "reverifications": {"employee_id": eid, "completed_on": r.isoformat()},
                "lca_notices": {"employee_id": eid, "posted_on": p.isoformat(), "removed_on": q.isoformat()},
                "lca_filings": {"employee_id": eid, "filed_on": f.isoformat()},
                "dol_receipts": {"employee_id": eid, "receipt_date": f.isoformat()}}
    if wf == "purchasing":
        o = 500 * rng.randint(4, 400)
        qi = rng.randint(10, 500)
        bad = None if ok["pa.three_way_match"] else rng.choice(["amount", "qty", "both"])
        i = o + 500 * rng.randint(1, 10) if bad in ("amount", "both") else (o if edge else max(0, o - 500 * rng.randint(1, 10)))
        rq = qi - rng.randint(1, 9) if bad in ("qty", "both") else (qi if edge else qi + rng.randint(1, 20))
        v = base
        if ok["pa.paid_in_window"]:
            y = v + timedelta(days=0 if edge else rng.randint(1, 20))
            dd = y + timedelta(days=0 if edge else rng.randint(1, 20))
        elif rng.random() < 0.5:  # paid before receipt
            y = v - timedelta(days=rng.randint(1, 15))
            dd = v + timedelta(days=rng.randint(5, 30))
        else:                     # paid late
            dd = v + timedelta(days=rng.randint(0, 20))
            y = dd + timedelta(days=rng.randint(1, 20))
        return {"requisitions": {"po_id": eid, "status": "Approved", "requested_amount": o,
                                 "expected_delivery": (v - timedelta(days=rng.randint(0, 10))).isoformat()},
                "purchase_orders": {"po_id": eid, "po_amount": o},
                "invoices": {"po_id": eid, "invoice_amount": i, "invoiced_qty": qi, "due_on": dd.isoformat()},
                "receipts": {"po_id": eid, "received_qty": rq, "received_on": v.isoformat()},
                "warehouse_scans": {"po_id": eid, "scan_date": v.isoformat()},
                "payments": {"po_id": eid, "paid_on": y.isoformat()}}
    c = base
    if ok["ea.calibration_current"]:
        t = c + timedelta(days=rng.choice([0, 365]) if edge else rng.randint(1, 364))
    else:
        t = c - timedelta(days=rng.randint(1, 30)) if rng.random() < 0.5 else c + timedelta(days=366 + rng.randint(0, 60))
    n = 5 * rng.randint(10, 100)
    need = round(1.2 * n)  # n is a multiple of 5, so 1.2n is an integer
    m = (need if edge else need + rng.randint(1, 20)) if ok["ea.load_with_margin"] else need - rng.randint(1, 20)
    return {"parts": {"part_id": eid, "qa_status": "Pass", "target_load_kn": need + 10,
                      "planned_test_date": (t - timedelta(days=rng.randint(1, 10))).isoformat()},
            "calibration_log": {"part_id": eid, "calibrated_on": c.isoformat()},
            "test_reports": {"part_id": eid, "tested_on": t.isoformat(), "measured_load_kn": m},
            "lab_certificates": {"part_id": eid, "test_date": t.isoformat(), "certified_load_kn": m},
            "spec_sheets": {"part_id": eid, "min_load_kn": n}}


def _rows(tables, s: Source, eid):
    return [r for r in tables[s.table] if r.get(s.key) == eid]


def _shift(kind, v, rng):
    return (_d(v) + timedelta(days=rng.randint(3, 15))).isoformat() if kind == "date" else v + max(1, round(v * 0.05))


def _blank(tables, f: Fact, eid, row_level: bool) -> None:
    for s in f.sources:
        if row_level:
            tables[s.table] = [r for r in tables[s.table] if r.get(s.key) != eid]
        else:
            for r in _rows(tables, s, eid):
                r[s.column] = ""


# rules that can establish a violation with one fact missing, and how
_GAP_VIOLATION = {"wf.notice_posting", "pa.three_way_match", "pa.paid_in_window"}


def _make_violation_despite_gap(rng, tables, wf, eid) -> str | None:
    opts = [c for c in RULES[wf] if c.rule_id in _GAP_VIOLATION]
    if not opts:
        return None
    c = rng.choice(opts)
    if c.rule_id == "wf.notice_posting":  # removed too early, filing date missing
        for r in _rows(tables, Source("lca_notices", "removed_on", KEY[wf]), eid):
            r["removed_on"] = (add_business_days(_d(r["posted_on"]), 10) - timedelta(days=rng.randint(1, 5))).isoformat()
        _blank(tables, c.facts[2], eid, row_level=False)
    elif c.rule_id == "pa.three_way_match":  # invoice above order, receipts row missing
        o = _rows(tables, Source("purchase_orders", "po_amount", KEY[wf]), eid)[0]["po_amount"]
        for r in _rows(tables, Source("invoices", "invoice_amount", KEY[wf]), eid):
            r["invoice_amount"] = o + 500 * rng.randint(1, 10)
        _blank(tables, c.facts[2], eid, row_level=True)
    else:  # paid before receipt, due date blank
        for r in _rows(tables, Source("payments", "paid_on", KEY[wf]), eid):
            v = _rows(tables, Source("receipts", "received_on", KEY[wf]), eid)[0]["received_on"]
            r["paid_on"] = (_d(v) - timedelta(days=rng.randint(1, 15))).isoformat()
        _blank(tables, c.facts[2], eid, row_level=False)
    return c.rule_id


def apply_pattern(rng, tables, wf, eid, pattern) -> str | None:
    """Mutate `tables` for one entity; returns the targeted rule (None: records left complete)."""
    rules = RULES[wf]
    if pattern in ("complete", "adverse_with_proxy"):
        return None
    if pattern == "violation_despite_gap":
        return _make_violation_despite_gap(rng, tables, wf, eid)
    if pattern in ("redundant", "conflict_resolved", "conflict_lower_dup", "conflict_top_dup"):
        multi = [(c, f) for c in rules for f in c.facts if f.priority]
        if not multi:
            return None
        c, f = rng.choice(multi)
        top, low = f.sources[0], f.sources[-1]
        if pattern == "redundant":  # the first source is blank; the fallback establishes the fact
            for r in _rows(tables, top, eid):
                r[top.column] = ""
        elif pattern == "conflict_resolved":  # the fallback disagrees; the first source prevails
            for r in _rows(tables, low, eid):
                r[low.column] = _shift(f.kind, r[low.column], rng)
        elif pattern == "conflict_lower_dup":  # the fallback holds two disagreeing rows; still resolved
            row = _rows(tables, low, eid)[0]
            tables[low.table].append({**row, low.column: _shift(f.kind, row[low.column], rng)})
        else:  # the first source holds two disagreeing rows; the fallback agrees with one: conflict
            row = _rows(tables, top, eid)[0]
            tables[top.table].append({**row, top.column: _shift(f.kind, row[top.column], rng)})
        return c.rule_id
    c = rng.choice(rules)
    if pattern == "all_gap":
        for f in c.facts:
            _blank(tables, f, eid, row_level=True)
        return c.rule_id
    single = [x for x in c.facts if not x.priority]
    f = rng.choice(single or list(c.facts))
    if pattern in ("proxy_only", "blank_fact"):
        _blank(tables, f, eid, row_level=False)
    elif pattern == "missing_row":
        _blank(tables, f, eid, row_level=True)
    elif pattern == "conflict_unresolved":  # a second, disagreeing row in a single-source fact
        s = f.sources[0]
        row = _rows(tables, s, eid)[0]
        tables[s.table].append({**row, s.column: _shift(f.kind, row[s.column], rng)})
    return c.rule_id


@dataclass
class Packet:
    packet_id: str
    workflow: str
    tables: dict
    entities: list
    labels: dict
    patterns: dict


def make_packet(wf: str, seed: int, n: int = N_ENTITIES) -> Packet:
    rng = random.Random(f"study13-{wf}-{seed}")
    tables = {t: [] for t in SCHEMAS[wf]}
    ents, pats, adverse = [], {}, {}
    plan = [PATTERNS[i % len(PATTERNS)] for i in range(n)]
    rng.shuffle(plan)
    for i in range(n):
        eid = f"{PREFIX[wf]}-{seed % 1000:03d}{i + 1:02d}"
        ok = {c.rule_id: rng.random() < 0.5 for c in RULES[wf]}
        if plan[i] == "adverse_with_proxy":
            adverse[eid] = rng.choice(RULES[wf]).rule_id
            ok[adverse[eid]] = False
        for t, row in _entity(rng, wf, eid, ok).items():
            tables[t].append(row)
        ents.append(eid)
    for i, eid in enumerate(ents):
        pats[eid] = (plan[i], apply_pattern(rng, tables, wf, eid, plan[i]) or adverse.get(eid))
    for t in tables:  # row order carries no information
        rng.shuffle(tables[t])
    labels = {f"{c.rule_id}::{e}": label(c, tables, e) for c in RULES[wf] for e in ents}
    return Packet(f"{wf}-{seed}", wf, tables, ents, labels, pats)


# ---------------------------------------------------------------- rendering
def write_canonical(p: Packet, out: Path) -> None:
    out.mkdir(parents=True, exist_ok=True)
    for t, cols in SCHEMAS[p.workflow].items():
        with (out / f"{t}.csv").open("w", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=cols)
            w.writeheader()
            w.writerows(p.tables[t])


def _fmt_l2(kind, unit, raw):
    if raw in (None, ""):
        return ""
    if kind == "date":
        return _d(raw).strftime("%d %b %Y")
    if kind == "amount" and unit == "USD":
        return f"${float(raw):,.2f}"
    return str(raw)


def _fmt_l3(kind, unit, raw):
    if raw in (None, ""):
        return ""
    if kind == "date":
        d = _d(raw)
        return f"{d.strftime('%B')} {d.day}, {d.year}"
    if kind == "amount":
        return f"{float(raw):g} {unit}"
    return str(raw)


# Development layout L2 headers (the held-out layouts' author was asked to avoid these).
L2_HEADERS = {
    "employee_id": "Employee No", "po_id": "PO Number", "part_id": "Part No",
    "reverification_status": "Reverif. Status", "visa_end_date": "Visa End", "notice_status": "Notice Status",
    "planned_filing_date": "Planned Filing", "document_type": "Doc Type", "expires_on": "Expiration Date",
    "card_expiry": "Card Expires", "completed_on": "Completed", "posted_on": "Posted Date",
    "removed_on": "Removed Date", "filed_on": "Filing Date", "receipt_date": "Receipt Date",
    "status": "Req Status", "requested_amount": "Requested ($)", "expected_delivery": "Expected Delivery",
    "po_amount": "PO Total ($)", "invoice_amount": "Invoice Total ($)", "invoiced_qty": "Qty Invoiced",
    "due_on": "Due Date", "received_qty": "Qty Received", "received_on": "Received Date", "scan_date": "Scanned",
    "paid_on": "Payment Date", "qa_status": "QA", "target_load_kn": "Target Load (kN)",
    "planned_test_date": "Planned Test", "calibrated_on": "Calibration Date", "tested_on": "Test Date",
    "measured_load_kn": "Measured (kN)", "test_date": "Date of Test", "certified_load_kn": "Certified Load (kN)",
    "min_load_kn": "Min Load (kN)",
}


def _csv_text(header, rows) -> str:
    import io
    buf = io.StringIO()
    w = csv.writer(buf, lineterminator="\n")
    w.writerow(header)
    w.writerows(rows)
    return buf.getvalue()


def render_dev(layout: str, doc: str, columns: list, rows: list, key: str, rng) -> tuple[str, str]:
    """Development layouts. L1: canonical CSV. L2: CSV with other headers and value formats.
    L3: one line per field (record, entity, field, value)."""
    names = [c[0] for c in columns]
    if layout == "L1":
        return "csv", _csv_text(names, [[r.get(c, "") for c in names] for r in rows])
    if layout == "L2":
        return "csv", _csv_text([L2_HEADERS[c] for c in names],
                                [[_fmt_l2(k, u, r.get(c, "")) for c, k, u, _ in columns] for r in rows])
    out = []
    for i, r in enumerate(rows, 1):
        for c, k, u, lab in columns[1:]:
            v = _fmt_l3(k, u, r.get(c, ""))
            if v:
                out.append([f"{doc}-{i}", r[key], lab, v])
    return "csv", _csv_text(["record", "entity", "field", "value"], out)


def render(layout: str, doc: str, columns: list, rows: list, key: str, rng) -> tuple[str, str]:
    if layout in DEV_LAYOUTS:
        return render_dev(layout, doc, columns, rows, key, rng)
    from .study13_heldout import LAYOUTS as HELD
    return HELD[layout](doc, columns, rows, key, rng)


def write_packet(p: Packet, layout: str, out: Path) -> dict:
    out.mkdir(parents=True, exist_ok=True)
    paths = {}
    for t, cols in DOCS[p.workflow].items():
        rng = random.Random(f"study13-render-{layout}-{p.packet_id}-{t}")
        ext, text = render(layout, t, cols, p.tables[t], KEY[p.workflow], rng)
        path = out / f"{t}.{ext}"
        path.write_text(text)
        paths[t] = path
    return paths


# ---------------------------------------------------------------- prompts and firms
def statement(c: Contract) -> str:
    lines = [f"Decision rule: {c.predicate_text}"]
    for f in c.facts:
        srcs = [f"the {META[(s.table, s.column)][3]} in `{s.table}`" for s in f.sources]
        txt = srcs[0] + "".join(f"; if `{f.sources[0].table}` has no value for the entity, {x}" for x in srcs[1:])
        unit = META[(f.sources[0].table, f.sources[0].column)][2]
        lines.append(f"  - {f.name}{f' ({unit})' if unit else ''} is established only by {txt}. "
                     "No other document establishes it.")
    return "\n".join(lines)


def obligations() -> list[Obligation]:
    return [Obligation(rule_id=c.rule_id, regime="contract", citation="stated decision rule",
                       summary=c.predicate_text, applies_to="entity", evidence_required=(),
                       data_needed=statement(c)) for c in CONTRACTS.values()]


def firm(wf: str, layout: str, seed: int) -> Firm:
    p = make_packet(wf, seed)
    write_canonical(p, DIR / "canonical" / wf / f"s{seed}")
    sources = write_packet(p, layout, DIR / layout / wf / f"s{seed}")
    pairs = [Pair.make(c.rule_id, e) for c in RULES[wf] for e in p.entities]
    labels = [Label(pair_id=pr.pair_id, verdict=Verdict(p.labels[pr.pair_id].label),
                    basis=p.labels[pr.pair_id].kind) for pr in pairs]
    return Firm(firm_id=f"study13-{wf}-{layout}-s{seed}", name=f"Case file {wf}-{seed}", as_of=AS_OF,
                sources=sources, entities=[Entity(e, "entity", e) for e in p.entities], pairs=pairs, labels=labels,
                provenance={"seed": seed, "workflow": wf, "layout": layout, "header": "Case file"})


def load_firms(spec: str) -> list[Firm]:
    """spec = '<workflow>:<layout>'."""
    wf, layout = spec.split(":")
    return [firm(wf, layout, s) for s in SEEDS]
