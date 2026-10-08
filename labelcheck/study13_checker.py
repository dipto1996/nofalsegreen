#!/usr/bin/env python3
"""Independent reference checker for the Study 13 decision contracts.

Written from docs/study13/CONTRACT_SPEC.md only (no other code in this repo was read).
Standard library only, Python 3.9+.

    python3 labelcheck/study13_checker.py <workflow> <packet_dir>
    python3 labelcheck/study13_checker.py --selftest

check(workflow, packet_dir) -> {"<rule_id>::<entity_id>": "pass"|"fail"|"needs_evidence"}
"""
import csv
import datetime as _dt
import itertools
import json
import os
import sys
from fractions import Fraction
from functools import lru_cache

# ---------------------------------------------------------------------------
# Documents
# ---------------------------------------------------------------------------

WORKFLOW_DOCS = {
    "workforce": ["hr_roster", "work_authorizations", "ead_cards", "reverifications",
                  "lca_notices", "lca_filings", "dol_receipts"],
    "purchasing": ["requisitions", "purchase_orders", "invoices", "receipts",
                   "warehouse_scans", "payments"],
    "engineering": ["parts", "calibration_log", "test_reports", "lab_certificates",
                    "spec_sheets"],
}


def _read_doc(packet_dir, doc):
    """Return a list of (entity_key, {column: stripped_value}) for <doc>.csv.

    A missing file means the document has no rows. The entity key is the first column.
    Rows whose key is blank are dropped (they belong to no entity).
    """
    path = os.path.join(packet_dir, doc + ".csv")
    if not os.path.isfile(path):
        return []
    rows = []
    with open(path, newline="", encoding="utf-8-sig") as fh:
        reader = csv.reader(fh)
        header = None
        for raw in reader:
            if header is None:
                header = [h.strip() for h in raw]
                continue
            if not raw or all(not c.strip() for c in raw):
                continue
            rec = {}
            for i, name in enumerate(header):
                rec[name] = raw[i].strip() if i < len(raw) and raw[i] is not None else ""
            key = rec.get(header[0], "") if header else ""
            if key == "":
                continue
            rows.append((key, rec))
    return rows


# ---------------------------------------------------------------------------
# Values
# ---------------------------------------------------------------------------

def parse_date(s):
    """ISO YYYY-MM-DD -> proleptic Gregorian ordinal (int)."""
    return _dt.date.fromisoformat(s.strip()).toordinal()


def parse_amount(s):
    return Fraction(s.strip())


def ord_to_iso(o):
    return _dt.date.fromordinal(o).isoformat()


# ---------------------------------------------------------------------------
# US federal holidays (observed) and business days
# ---------------------------------------------------------------------------

def _nth_weekday(year, month, weekday, n):
    """n-th (1-based) given weekday (Mon=0) of month."""
    d = _dt.date(year, month, 1)
    shift = (weekday - d.weekday()) % 7
    return d + _dt.timedelta(days=shift + 7 * (n - 1))


def _last_weekday(year, month, weekday):
    nxt = _dt.date(year + (month == 12), month % 12 + 1, 1)
    d = nxt - _dt.timedelta(days=1)
    return d - _dt.timedelta(days=(d.weekday() - weekday) % 7)


def _observed(d):
    # Saturday -> preceding Friday; Sunday -> following Monday.
    if d.weekday() == 5:
        return d - _dt.timedelta(days=1)
    if d.weekday() == 6:
        return d + _dt.timedelta(days=1)
    return d


@lru_cache(maxsize=None)
def _holidays_nominal_year(year):
    """Observed dates of the eleven holidays whose *nominal* date is in `year`.

    The observed date can fall in a neighbouring year (New Year's Day on Saturday
    Jan 1 is observed Friday Dec 31 of the previous year), so callers look up
    the nominal years y-1, y, y+1.
    """
    days = [
        _dt.date(year, 1, 1),                  # New Year's Day
        _nth_weekday(year, 1, 0, 3),           # Birthday of Martin Luther King, Jr.
        _nth_weekday(year, 2, 0, 3),           # Washington's Birthday
        _last_weekday(year, 5, 0),             # Memorial Day
        _dt.date(year, 6, 19),                 # Juneteenth
        _dt.date(year, 7, 4),                  # Independence Day
        _nth_weekday(year, 9, 0, 1),           # Labor Day
        _nth_weekday(year, 10, 0, 2),          # Columbus Day
        _dt.date(year, 11, 11),                # Veterans Day
        _nth_weekday(year, 11, 3, 4),          # Thanksgiving Day
        _dt.date(year, 12, 25),                # Christmas Day
    ]
    return frozenset(_observed(d).toordinal() for d in days)


def is_holiday(o):
    y = _dt.date.fromordinal(o).year
    return any(o in _holidays_nominal_year(yy) for yy in (y - 1, y, y + 1))


def is_business_day(o):
    return _dt.date.fromordinal(o).weekday() < 5 and not is_holiday(o)


@lru_cache(maxsize=None)
def add_business_days(p, n=10):
    """P + n business days: P is day 0; each later business day counts one."""
    d, count = p, 0
    while count < n:
        d += 1
        if is_business_day(d):
            count += 1
    return d


@lru_cache(maxsize=None)
def inv_business_days(q, n=10):
    """max{P : P + n business days <= Q}.

    add_business_days is non-decreasing in P and strictly greater than P, so the set
    {P : bd(P) <= Q} is a down-set; its maximum is found by stepping down from Q.
    Then  Q >= bd(P)  <=>  P <= inv_business_days(Q).
    """
    p = q
    while add_business_days(p, n) > q:
        p -= 1
    return p


# ---------------------------------------------------------------------------
# Rules
# ---------------------------------------------------------------------------
# Each fact: (name, kind, [(document, column), ...] in priority order).
# `transforms` lists every map that turns one value into a value it is compared with
# inside the predicate, *and its inverse* (used for step 4 critical points).

D90 = 90
D365 = 365
K12 = Fraction(6, 5)


def _p_reverify(v):
    return v["E"] - D90 <= v["R"] <= v["E"]


def _p_notice(v):
    return v["P"] <= v["F"] and v["Q"] >= add_business_days(v["P"], 10)


def _p_three_way(v):
    return v["I"] <= v["O"] and v["Rq"] >= v["Iq"]


def _p_paid(v):
    return v["V"] <= v["Y"] <= v["D"]


def _p_calibration(v):
    return v["C"] <= v["T"] <= v["C"] + D365


def _p_load(v):
    return v["M"] >= K12 * v["N"]


RULES = {
    "workforce": [
        {
            "id": "wf.reverify_window", "kind": "date", "pred": _p_reverify,
            "facts": [
                ("E", [("work_authorizations", "expires_on"), ("ead_cards", "card_expiry")]),
                ("R", [("reverifications", "completed_on")]),
            ],
            "transforms": [lambda x: x - D90, lambda x: x + D90],
        },
        {
            "id": "wf.notice_posting", "kind": "date", "pred": _p_notice,
            "facts": [
                ("P", [("lca_notices", "posted_on")]),
                ("Q", [("lca_notices", "removed_on")]),
                ("F", [("lca_filings", "filed_on"), ("dol_receipts", "receipt_date")]),
            ],
            "transforms": [add_business_days, inv_business_days],
        },
    ],
    "purchasing": [
        {
            "id": "pa.three_way_match", "kind": "amount", "pred": _p_three_way,
            "facts": [
                ("I", [("invoices", "invoice_amount")]),
                ("O", [("purchase_orders", "po_amount")]),
                ("Rq", [("receipts", "received_qty")]),
                ("Iq", [("invoices", "invoiced_qty")]),
            ],
            "transforms": [],
        },
        {
            "id": "pa.paid_in_window", "kind": "date", "pred": _p_paid,
            "facts": [
                ("V", [("receipts", "received_on"), ("warehouse_scans", "scan_date")]),
                ("Y", [("payments", "paid_on")]),
                ("D", [("invoices", "due_on")]),
            ],
            "transforms": [],
        },
    ],
    "engineering": [
        {
            "id": "ea.calibration_current", "kind": "date", "pred": _p_calibration,
            "facts": [
                ("C", [("calibration_log", "calibrated_on")]),
                ("T", [("test_reports", "tested_on"), ("lab_certificates", "test_date")]),
            ],
            "transforms": [lambda x: x + D365, lambda x: x - D365],
        },
        {
            "id": "ea.load_with_margin", "kind": "amount", "pred": _p_load,
            "facts": [
                ("M", [("lab_certificates", "certified_load_kn"),
                       ("test_reports", "measured_load_kn")]),
                ("N", [("spec_sheets", "min_load_kn")]),
            ],
            "transforms": [lambda x: x * K12, lambda x: x / K12],
        },
    ],
}

CONFLICT = object()
UNKNOWN = object()


def gather_fact(sources, docs, entity, kind):
    """Step 1. First source with >=1 non-blank value decides; disagreement => conflict."""
    parse = parse_date if kind == "date" else parse_amount
    for doc, col in sources:
        vals = set()
        for key, rec in docs.get(doc, []):
            if key != entity:
                continue
            cell = rec.get(col, "")
            if cell != "":
                vals.add(parse(cell))
        if vals:
            return vals.pop() if len(vals) == 1 else CONFLICT
    return UNKNOWN


# ---------------------------------------------------------------------------
# Step 4: exact decision over all values of the unknown facts
# ---------------------------------------------------------------------------
#
# The verdict is pass iff no assignment of the unknowns falsifies the predicate,
# fail iff no assignment satisfies it. We enumerate a finite candidate set S for the
# unknowns (Cartesian product S^k) and record which truth values occur. This is exact
# provided: (a) whenever a satisfying assignment exists, one exists in S^k, and (b)
# whenever a falsifying assignment exists, one exists in S^k. Construction of S:
#
#   S0 = the known values of the rule's facts (or a fixed anchor if none is known);
#   S_{i+1} = S_i  U  t(S_i) for every transform t of the rule (each comparison map
#            that appears in the predicate and its inverse: -90/+90, +365/-365,
#            x1.2/÷1.2, +10 business days / its inverse max{P : bd(P) <= Q});
#   repeated k = #unknowns times (depth 1 is all the witnesses below need; more only
#   adds points). Then
#   dates:   S = S_k U (S_k - 1) U (S_k + 1)     (integer day ordinals)
#   amounts: S = S_k U {0} U midpoints of consecutive points U {max + 1}, kept >= 0.
#
# Every atom of every rule has the shape  a(x) <= b(y)  with a, b non-decreasing and
# unbounded maps (identity, +c, x1.2, +10 business days -- the latter a non-decreasing
# step function of P with bd(P) > P), or compares a variable with a constant.
#
# (b) Falsifying: the predicate is a conjunction, so it is falsifiable iff one atom is
#   falsifiable; the other unknowns can take any value of S (non-empty). For a single
#   atom, its truth as a function of one unknown x (others fixed) is monotone in x
#   with a single threshold located at t(known) for a transform t (e.g. R > E is false
#   first at R = E + 1; Q < bd(P) at Q = bd(P) - 1; P > inv(Q) at P = inv(Q) + 1;
#   O < I at O = 0 when I > 0; 1.2N > M at N = max + 1; M < 1.2N at M = 0 when N > 0;
#   I > O at I = max + 1). Those points, their ±1 neighbours, 0 and max+1 are all in S.
#   If both of the atom's variables are unknown, take x = any point a of S and the
#   other at t(a) ± 1 or 0 / max + 1, again in S. If no such point exists in the
#   non-negative amount domain (e.g. I = 0 known: I <= O for every O >= 0) the atom is
#   genuinely unfalsifiable.
#
# (a) Satisfying: per rule, a witness exists in S whenever any witness exists:
#   reverify / calibration (x <= y <= x + c): if one is known put the unknown equal to
#     it (R = E; T = C); if both unknown, both = a.
#   paid (V <= Y <= D): if V, D known and V <= D, Y = V; otherwise set every unknown
#     equal to the (smallest suitable) known value, or all = a. With Y known: V = D = Y.
#   notice (P <= F and Q >= bd(P)): small P only helps both atoms, so with P unknown
#     take P = min(F, inv(Q)) over the known ones (both in S_1); with P known take
#     F = P and Q = bd(P) (in S_1); unknown F/Q given an unknown P are set from P.
#   three_way (I <= O, Rq >= Iq, independent pairs): put an unknown equal to its
#     partner (known or not), or both = 0.
#   load (M >= 1.2N): M unknown -> M = 1.2N; N unknown -> N = 0; both -> 0, 0.
# Hence enumerating S^k is exact. The amount domain restriction (>= 0) is enforced by
# dropping negative candidates; midpoints between critical points are included so any
# open interval between two critical values is represented.

ANCHOR_DATE = _dt.date(2024, 1, 2).toordinal()


def _candidates(rule, known_vals, n_unknown):
    kind = rule["kind"]
    if known_vals:
        pts = set(known_vals)
    else:
        pts = {ANCHOR_DATE} if kind == "date" else {Fraction(0)}
    for _ in range(max(1, n_unknown)):
        new = set(pts)
        for t in rule["transforms"]:
            for x in pts:
                new.add(t(x))
        pts = new
    if kind == "date":
        out = set()
        for x in pts:
            out.update((x - 1, x, x + 1))
        return sorted(out)
    pts.add(Fraction(0))
    srt = sorted(p for p in pts if p >= 0)
    out = set(srt)
    for a, b in zip(srt, srt[1:]):
        out.add((a + b) / 2)
    out.add(srt[-1] + 1)
    return sorted(out)


def decide(rule, values):
    """values: {fact: value | CONFLICT | UNKNOWN} -> verdict (steps 2-4)."""
    if any(v is CONFLICT for v in values.values()):
        return "needs_evidence"
    unknown = [f for f, v in values.items() if v is UNKNOWN]
    pred = rule["pred"]
    if not unknown:
        return "pass" if pred(values) else "fail"
    known_vals = [v for v in values.values() if v is not UNKNOWN]
    cands = _candidates(rule, known_vals, len(unknown))
    seen = set()
    assign = dict(values)
    for combo in itertools.product(cands, repeat=len(unknown)):
        for f, x in zip(unknown, combo):
            assign[f] = x
        seen.add(bool(pred(assign)))
        if len(seen) == 2:
            return "needs_evidence"
    return "pass" if seen == {True} else "fail"


def check(workflow, packet_dir):
    if workflow not in WORKFLOW_DOCS:
        raise ValueError("unknown workflow: %r" % (workflow,))
    docs = {d: _read_doc(packet_dir, d) for d in WORKFLOW_DOCS[workflow]}
    entities = set()
    for rows in docs.values():
        for key, _ in rows:
            entities.add(key)
    out = {}
    for rule in RULES[workflow]:
        for ent in entities:
            vals = {name: gather_fact(srcs, docs, ent, rule["kind"])
                    for name, srcs in rule["facts"]}
            out["%s::%s" % (rule["id"], ent)] = decide(rule, vals)
    return {k: out[k] for k in sorted(out)}


# ---------------------------------------------------------------------------
# Self-test
# ---------------------------------------------------------------------------

def _write(dirpath, doc, header, rows):
    with open(os.path.join(dirpath, doc + ".csv"), "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(header)
        for r in rows:
            w.writerow(r)


def _selftest():
    import tempfile
    failures = []
    count = [0]

    def eq(label, got, want):
        count[0] += 1
        if got != want:
            failures.append("%s: got %r want %r" % (label, got, want))

    d = lambda s: parse_date(s)  # noqa: E731

    # --- holidays / business days -------------------------------------------------
    eq("2022-01-01 Sat -> observed Fri 2021-12-31", is_holiday(d("2021-12-31")), True)
    eq("2021-12-31 not a business day", is_business_day(d("2021-12-31")), False)
    eq("2022-01-03 Monday is a business day", is_business_day(d("2022-01-03")), True)
    eq("2021-07-04 Sun -> observed Mon 07-05", is_holiday(d("2021-07-05")), True)
    eq("2026-07-04 Sat -> observed Fri 07-03", is_holiday(d("2026-07-03")), True)
    eq("Thanksgiving 2025 = 11-27", is_holiday(d("2025-11-27")), True)
    eq("MLK 2025 = 01-20", is_holiday(d("2025-01-20")), True)
    eq("Memorial 2025 = 05-26", is_holiday(d("2025-05-26")), True)
    eq("Columbus 2025 = 10-13", is_holiday(d("2025-10-13")), True)
    eq("Juneteenth 2027 Sat -> 06-18", is_holiday(d("2027-06-18")), True)
    # 2025-06-30 (Mon) day 0; Jul 4 (Fri) holiday skipped -> day 10 is Tue 2025-07-15.
    eq("bd(2025-06-30)", ord_to_iso(add_business_days(d("2025-06-30"))), "2025-07-15")
    # 2021-12-27 Mon day 0; 12-31 observed New Year skipped:
    # 28,29,30 (3), Jan 3,4,5,6,7 (8), 10,11 (10)
    eq("bd(2021-12-27)", ord_to_iso(add_business_days(d("2021-12-27"))), "2022-01-11")
    for q in range(d("2025-06-01"), d("2025-08-01")):
        p = inv_business_days(q)
        if not (add_business_days(p) <= q < add_business_days(p + 1)):
            failures.append("inv_business_days wrong at %s" % ord_to_iso(q))
    count[0] += 1

    with tempfile.TemporaryDirectory() as tmp:
        def packet(name, files):
            p = os.path.join(tmp, name)
            os.mkdir(p)
            for doc, (header, rows) in files.items():
                _write(p, doc, header, rows)
            return p

        WA = ["employee_id", "document_type", "expires_on"]
        EAD = ["employee_id", "card_expiry"]
        REV = ["employee_id", "completed_on"]
        NOT = ["employee_id", "posted_on", "removed_on"]
        FIL = ["employee_id", "filed_on"]
        DOL = ["employee_id", "receipt_date"]
        ROS = ["employee_id", "reverification_status", "visa_end_date", "notice_status",
               "planned_filing_date"]

        # -- wf.reverify_window ---------------------------------------------------
        p = packet("wf1", {
            "hr_roster": (ROS, [["e_only_roster", "done", "2025-01-01", "", ""]]),
            "work_authorizations": (WA, [
                # conflict in top source, both orders; ead value must not rescue it
                ["c1", "EAD", "2025-06-30"], ["c1", "EAD", "2025-07-30"],
                ["c2", "EAD", "2025-07-30"], ["c2", "EAD", "2025-06-30"],
                # top source only blank -> ead used
                ["blank", "EAD", ""],
                # top has one value; conflict only in ead -> not conflicting
                ["lowc", "EAD", "2025-06-30"],
                ["b90", "EAD", "2025-06-30"], ["b91", "EAD", "2025-06-30"],
                ["bE", "EAD", "2025-06-30"], ["bE1", "EAD", "2025-06-30"],
                ["Eonly", "EAD", "2025-06-30"],
                ["agree", "EAD", "2025-06-30"], ["agree", "I-797", "2025-06-30"],
            ]),
            "ead_cards": (EAD, [
                ["c1", "2025-06-30"], ["c2", "2025-06-30"],
                ["blank", "2025-06-30"],
                ["lowc", "2024-01-01"], ["lowc", "2026-01-01"],
            ]),
            "reverifications": (REV, [
                ["c1", "2025-06-01"], ["c2", "2025-06-01"],
                ["blank", "2025-06-01"], ["lowc", "2025-06-01"],
                ["b90", "2025-04-01"],   # 2025-06-30 - 90 = 2025-04-01
                ["b91", "2025-03-31"],
                ["bE", "2025-06-30"], ["bE1", "2025-07-01"],
                ["Ronly", "2025-06-01"],
                ["agree", "2025-06-01"],
            ]),
        })
        r = check("workforce", p)
        W = "wf.reverify_window::"
        eq("conflict top source (order A)", r[W + "c1"], "needs_evidence")
        eq("conflict top source (order B)", r[W + "c2"], "needs_evidence")
        eq("blank top -> lower source", r[W + "blank"], "pass")
        eq("conflict only in lower source", r[W + "lowc"], "pass")
        eq("R = E - 90", r[W + "b90"], "pass")
        eq("R = E - 91", r[W + "b91"], "fail")
        eq("R = E", r[W + "bE"], "pass")
        eq("R = E + 1", r[W + "bE1"], "fail")
        eq("R unknown", r[W + "Eonly"], "needs_evidence")
        eq("E unknown", r[W + "Ronly"], "needs_evidence")
        eq("both unknown (roster-only entity)", r[W + "e_only_roster"], "needs_evidence")
        eq("agreeing duplicate rows", r[W + "agree"], "pass")
        eq("roster entity evaluated for notice rule",
           r["wf.notice_posting::e_only_roster"], "needs_evidence")

        # -- wf.notice_posting ----------------------------------------------------
        p = packet("wf2", {
            "lca_notices": (NOT, [
                ["n_ok", "2025-06-30", "2025-07-15"],    # exactly P + 10 bd (across Jul 4)
                ["n_short", "2025-06-30", "2025-07-14"],
                ["n_late", "2025-07-02", "2025-08-01"],  # P > F
                ["n_noq", "2025-07-02", ""],             # P > F known, Q unknown -> fail
                ["n_noq2", "2025-06-30", ""],            # P <= F, Q unknown
                ["n_nop", "", "2025-07-15"],             # P unknown
                ["n_conf", "2025-06-30", "2025-07-15"], ["n_conf", "2025-06-29", ""],
                ["n_fb", "2025-06-30", "2025-07-15"],
            ]),
            "lca_filings": (FIL, [
                ["n_ok", "2025-06-30"], ["n_short", "2025-06-30"], ["n_late", "2025-07-01"],
                ["n_noq", "2025-07-01"], ["n_noq2", "2025-07-01"], ["n_nop", "2025-07-01"],
                ["n_conf", "2025-07-01"], ["n_fb", ""],
            ]),
            "dol_receipts": (DOL, [["n_fb", "2025-06-29"], ["n_ok", "2020-01-01"]]),
        })
        r = check("workforce", p)
        N = "wf.notice_posting::"
        eq("Q = P + 10 bd across holiday, P = F", r[N + "n_ok"], "pass")
        eq("Q = P + 9 bd", r[N + "n_short"], "fail")
        eq("P > F", r[N + "n_late"], "fail")
        eq("P > F known, Q unknown", r[N + "n_noq"], "fail")
        eq("P <= F, Q unknown", r[N + "n_noq2"], "needs_evidence")
        eq("P unknown", r[N + "n_nop"], "needs_evidence")
        eq("P conflicting", r[N + "n_conf"], "needs_evidence")
        eq("F from dol_receipts when filings blank", r[N + "n_fb"], "fail")

        # -- purchasing -----------------------------------------------------------
        p = packet("pa", {
            "purchase_orders": (["po_id", "po_amount"], [
                ["m_ok", "100.00"], ["m_over", "100"], ["m_eq", "100"], ["m_qty", "100"],
                ["m_zero", ""], ["m_noI", "100"],
                ["m_conf", "100"], ["m_conf", "100.0"],  # numerically equal -> agree
                ["m_conf2", "100"], ["m_conf2", "101"],
            ]),
            "invoices": (["po_id", "invoice_amount", "invoiced_qty", "due_on"], [
                ["m_ok", "99.99", "5", "2025-03-31"],
                ["m_over", "100.01", "", ""],        # I > O, quantities unknown -> fail
                ["m_eq", "100", "5", ""],
                ["m_qty", "50", "6", ""],
                ["m_zero", "0", "3", ""],            # I = 0, O unknown (>= 0) -> I <= O
                ["m_noI", "", "3", ""],
                ["m_conf", "50", "1", ""], ["m_conf2", "50", "1", ""],
                ["y_ok", "", "", "2025-03-31"], ["y_lo", "", "", "2025-03-31"],
                ["y_hi", "", "", "2025-03-31"], ["y_noY", "", "", "2025-03-31"],
                ["y_bad", "", "", "2025-03-01"],
            ]),
            "receipts": (["po_id", "received_qty", "received_on"], [
                ["m_ok", "5", "2025-03-01"], ["m_eq", "5", ""], ["m_qty", "5", ""],
                ["m_zero", "3", ""], ["m_noI", "3", ""], ["m_conf", "1", ""],
                ["m_conf2", "1", ""],
                ["y_ok", "", "2025-03-01"], ["y_lo", "", ""], ["y_hi", "", "2025-03-01"],
                ["y_noY", "", "2025-03-01"], ["y_bad", "", "2025-03-02"],
            ]),
            "warehouse_scans": (["po_id", "scan_date"], [
                ["y_lo", "2025-03-01"], ["y_lo", "2025-03-05"],  # receipts blank -> scans decide: conflict
                ["y_ok", "2099-01-01"],  # ignored: receipts has a value
            ]),
            "payments": (["po_id", "paid_on"], [
                ["m_ok", "2025-03-15"],
                ["y_ok", "2025-03-01"], ["y_lo", "2025-03-01"], ["y_hi", "2025-04-01"],
            ]),
        })
        r = check("purchasing", p)
        M = "pa.three_way_match::"
        Y = "pa.paid_in_window::"
        eq("three-way ok", r[M + "m_ok"], "pass")
        eq("I > O, quantities unknown", r[M + "m_over"], "fail")
        eq("I = O, Rq = Iq", r[M + "m_eq"], "pass")
        eq("Rq < Iq", r[M + "m_qty"], "fail")
        eq("I = 0, O unknown", r[M + "m_zero"], "pass")
        eq("I unknown", r[M + "m_noI"], "needs_evidence")
        eq("100 vs 100.0 agree", r[M + "m_conf"], "pass")
        eq("O conflicting", r[M + "m_conf2"], "needs_evidence")
        eq("Y = V (lower bound), Y < D", r[Y + "y_ok"], "pass")
        eq("V from scans conflicting", r[Y + "y_lo"], "needs_evidence")
        eq("Y > D", r[Y + "y_hi"], "fail")
        eq("Y unknown, V <= D", r[Y + "y_noY"], "needs_evidence")
        eq("Y unknown, V > D", r[Y + "y_bad"], "fail")
        eq("m_ok paid window", r[Y + "m_ok"], "pass")
        eq("m_over: V,Y,D unknown", r[Y + "m_over"], "needs_evidence")

        # -- engineering ----------------------------------------------------------
        p = packet("ea", {
            "calibration_log": (["part_id", "calibrated_on"], [
                ["t365", "2024-03-01"], ["t366", "2024-03-01"], ["t0", "2024-03-01"],
                ["tneg", "2024-03-01"], ["tC", "2024-03-01"],
            ]),
            "test_reports": (["part_id", "tested_on", "measured_load_kn"], [
                ["t365", "2025-03-01", ""],   # 2024 leap year: 2024-03-01 + 365 = 2025-03-01
                ["t366", "2025-03-02", ""],
                ["t0", "2024-03-01", ""], ["tneg", "2024-02-29", ""],
                ["l_eq", "", "120"], ["l_lo", "", "119.99"],
                ["l_pref", "", "100"],
                ["l_noN", "", "50"],
            ]),
            "lab_certificates": (["part_id", "test_date", "certified_load_kn"], [
                ["l_pref", "", "120"],        # lab value takes priority over test_reports
                ["l_zeroN", "", ""],
                ["t365", "", ""],
            ]),
            "spec_sheets": (["part_id", "min_load_kn"], [
                ["l_eq", "100"], ["l_lo", "100"], ["l_pref", "100"], ["l_zeroN", "0"],
                ["l_posN", "1"],
            ]),
        })
        r = check("engineering", p)
        C = "ea.calibration_current::"
        L = "ea.load_with_margin::"
        eq("T = C + 365", r[C + "t365"], "pass")
        eq("T = C + 366", r[C + "t366"], "fail")
        eq("T = C", r[C + "t0"], "pass")
        eq("T = C - 1", r[C + "tneg"], "fail")
        eq("C only, T unknown", r[C + "tC"], "needs_evidence")
        eq("M = 1.2 x N", r[L + "l_eq"], "pass")
        eq("M < 1.2 x N", r[L + "l_lo"], "fail")
        eq("lab M priority over test_reports", r[L + "l_pref"], "pass")
        eq("N unknown", r[L + "l_noN"], "needs_evidence")
        eq("M unknown, N = 0", r[L + "l_zeroN"], "pass")
        eq("M unknown, N > 0", r[L + "l_posN"], "needs_evidence")
        eq("missing csv tolerated / keys sorted", list(r) == sorted(r), True)

    # --- step 4 vs brute force over a bounded window (sanity, not the proof) -------
    import random
    rng = random.Random(13)
    base = d("2025-06-20")
    for rule in RULES["workforce"] + RULES["purchasing"][1:] + RULES["engineering"][:1]:
        facts = [f for f, _ in rule["facts"]]
        span = 420 if rule["id"] == "ea.calibration_current" else 120
        for _ in range(40):
            vals = {f: (base + rng.randint(-30, 30) if rng.random() < 0.6 else UNKNOWN)
                    for f in facts}
            unk = [f for f in facts if vals[f] is UNKNOWN]
            if not unk or len(unk) > 2:
                continue
            seen = set()
            a = dict(vals)
            for combo in itertools.product(range(base - span, base + span), repeat=len(unk)):
                for f, x in zip(unk, combo):
                    a[f] = x
                seen.add(bool(rule["pred"](a)))
                if len(seen) == 2:
                    break
            want = "needs_evidence" if len(seen) == 2 else ("pass" if True in seen else "fail")
            eq("brute %s %r" % (rule["id"], vals), decide(rule, vals), want)

    print("selftest: %d checks, %d failures" % (count[0], len(failures)))
    for f in failures:
        print("  FAIL " + f)
    return 0 if not failures else 1


def main(argv):
    if len(argv) == 2 and argv[1] == "--selftest":
        return _selftest()
    if len(argv) != 3:
        sys.stderr.write("usage: study13_checker.py <workflow> <packet_dir> | --selftest\n")
        return 2
    print(json.dumps(check(argv[1], argv[2]), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
