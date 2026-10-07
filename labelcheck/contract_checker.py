#!/usr/bin/env python3
"""Independent checker for the Study 9 decision contracts.

Written solely from docs/study9/CONTRACT_SPEC.md. Standard library only.

Usage:
    python3 labelcheck/contract_checker.py <workflow> <packet_dir>

Interpretation choices (where the spec is silent):
  * A prioritised fact (two sources) takes the values of the highest-priority
    source that has any value. If that source's own values disagree (e.g. two
    rows), the fact is conflicting -- priority cannot resolve it.
  * Values that cannot be parsed (non-ISO date, non-number amount) are treated
    as missing.
  * Unknown amounts range over all reals >= 0; unknown dates over all dates.
    Decisions over unknowns are exact: every order-type of the unknowns
    relative to the known constants is enumerated (see _candidates).
  * Juneteenth is a federal holiday from 2021 onward.
"""

import csv
import datetime as _dt
import itertools
import json
import os
import sys
from fractions import Fraction

# --------------------------------------------------------------------------
# Spec tables

WORKFLOWS = {
    "workforce": {
        "key": "employee_id",
        "tables": ["hr_roster", "i9_records", "payroll", "lca", "actual_wage_system"],
    },
    "purchasing": {
        "key": "po_id",
        "tables": ["requisitions", "purchase_orders", "signed_approvals", "erp_ledger"],
    },
    "engineering": {
        "key": "part_id",
        "tables": ["qa_tracker", "test_reports", "spec_sheets", "shipping_log"],
    },
}

# fact: (kind, [sources in priority order])
RULES = {
    "workforce": {
        "wf.section2": {
            "F": ("date", [("i9_records", "first_day_of_employment"), ("hr_roster", "hire_date")]),
            "S": ("date", [("i9_records", "section2_completed_on")]),
        },
        "wf.required_wage": {
            "P": ("amount", [("payroll", "annualised_gross")]),
            "W": ("amount", [("lca", "prevailing_wage")]),
            "A": ("amount", [("actual_wage_system", "actual_wage")]),
        },
    },
    "purchasing": {
        "pa.within_approval": {
            "O": ("amount", [("purchase_orders", "po_amount")]),
            "G": ("amount", [("signed_approvals", "approved_amount")]),
        },
        "pa.approved_before_order": {
            "D": ("date", [("signed_approvals", "signed_on")]),
            "T": ("date", [("purchase_orders", "po_date"), ("erp_ledger", "order_date")]),
        },
    },
    "engineering": {
        "ea.load_meets_spec": {
            "M": ("amount", [("test_reports", "measured_load_kn")]),
            "N": ("amount", [("spec_sheets", "min_load_kn")]),
        },
        "ea.tested_before_ship": {
            "X": ("date", [("test_reports", "tested_on")]),
            "Y": ("date", [("shipping_log", "shipped_on")]),
        },
    },
}

# --------------------------------------------------------------------------
# US federal holidays (observed)


def _nth_weekday(year, month, weekday, n):
    d = _dt.date(year, month, 1)
    d += _dt.timedelta(days=(weekday - d.weekday()) % 7)
    return d + _dt.timedelta(weeks=n - 1)


def _last_weekday(year, month, weekday):
    nxt = _dt.date(year + (month == 12), month % 12 + 1, 1)
    d = nxt - _dt.timedelta(days=1)
    return d - _dt.timedelta(days=(d.weekday() - weekday) % 7)


def _observed(d):
    if d.weekday() == 5:
        return d - _dt.timedelta(days=1)
    if d.weekday() == 6:
        return d + _dt.timedelta(days=1)
    return d


def _holidays_for_year(year):
    MON, THU = 0, 3
    fixed = [(1, 1), (7, 4), (11, 11), (12, 25)]
    if year >= 2021:
        fixed.append((6, 19))
    out = {_observed(_dt.date(year, m, d)) for m, d in fixed}
    out |= {
        _nth_weekday(year, 1, MON, 3),
        _nth_weekday(year, 2, MON, 3),
        _last_weekday(year, 5, MON),
        _nth_weekday(year, 9, MON, 1),
        _nth_weekday(year, 10, MON, 2),
        _nth_weekday(year, 11, THU, 4),
    }
    return out


_HOL_CACHE = {}


def is_holiday(d):
    # An observed date can spill into an adjacent year (Jan 1 on Sat -> Dec 31).
    for y in (d.year - 1, d.year, d.year + 1):
        if y < _dt.MINYEAR or y > _dt.MAXYEAR:
            continue
        if y not in _HOL_CACHE:
            try:
                _HOL_CACHE[y] = _holidays_for_year(y)
            except (ValueError, OverflowError):
                _HOL_CACHE[y] = set()
        if d in _HOL_CACHE[y]:
            return True
    return False


def is_business_day(d):
    return d.weekday() < 5 and not is_holiday(d)


def add_business_days(d, n):
    count = 0
    while count < n:
        d += _dt.timedelta(days=1)
        if is_business_day(d):
            count += 1
    return d


# --------------------------------------------------------------------------
# Loading


def _load_tables(workflow, packet_dir):
    spec = WORKFLOWS[workflow]
    key = spec["key"]
    tables = {}
    entities = set()
    for t in spec["tables"]:
        rows = []
        path = os.path.join(packet_dir, t + ".csv")
        if os.path.exists(path):
            with open(path, newline="", encoding="utf-8-sig") as fh:
                for row in csv.DictReader(fh):
                    eid = (row.get(key) or "").strip()
                    if not eid:
                        continue
                    entities.add(eid)
                    rows.append(row)
        tables[t] = rows
    return key, tables, entities


def _parse(kind, raw):
    s = (raw or "").strip()
    if not s:
        return None
    try:
        if kind == "date":
            return _dt.date.fromisoformat(s).toordinal()
        v = Fraction(s)
        return v
    except (ValueError, ZeroDivisionError):
        return None


CONFLICT = object()


def _gather(kind, sources, tables, key, eid):
    """Return a value, None (unknown) or CONFLICT."""
    for table, col in sources:
        vals = set()
        for row in tables.get(table, []):
            if (row.get(key) or "").strip() != eid:
                continue
            v = _parse(kind, row.get(col))
            if v is not None:
                vals.add(v)
        if len(vals) > 1:
            return CONFLICT
        if len(vals) == 1:
            return vals.pop()
        # no value in this source -> fall back to next (lower priority)
    return None


# --------------------------------------------------------------------------
# Predicates (date values are ordinals; amounts are Fractions)


def _section2(v):
    f = _dt.date.fromordinal(v["F"])
    return v["S"] <= add_business_days(f, 3).toordinal()


PREDICATES = {
    "wf.section2": _section2,
    "wf.required_wage": lambda v: v["P"] >= max(v["W"], v["A"]),
    "pa.within_approval": lambda v: v["O"] <= v["G"],
    "pa.approved_before_order": lambda v: v["D"] <= v["T"],
    "ea.load_meets_spec": lambda v: v["M"] >= v["N"],
    "ea.tested_before_ship": lambda v: v["X"] <= v["Y"],
}


def _candidates(kind, known, n_unknown):
    """Finite set of values that realise every order-type of n_unknown free
    variables relative to the known constants (and to each other).

    Amounts: domain [0, inf). Dates: all dates (integers); far points +-1000
    days are added so date predicates with a business-day offset are also
    covered on both sides."""
    k = max(n_unknown, 1)
    if kind == "amount":
        base = sorted(set(known) | {Fraction(0)})
        cands = set(base)
        for a, b in zip(base, base[1:]):
            for i in range(1, k + 1):
                cands.add(a + (b - a) * i / (k + 1))
        top = base[-1]
        for i in range(1, k + 1):
            cands.add(top + i)
        return sorted(cands)
    base = sorted(set(known)) or [_dt.date(2024, 6, 3).toordinal()]
    cands = set()
    for c in base:
        for off in range(-k - 12, k + 13):  # neighbours, incl. +3 business days span
            cands.add(c + off)
    lo, hi = base[0], base[-1]
    for i in range(1, k + 1):
        cands.add(lo - 1000 * i)
        cands.add(hi + 1000 * i)
    lo_ok, hi_ok = _dt.date.min.toordinal() + 10, _dt.date.max.toordinal() - 10
    return sorted(c for c in cands if lo_ok <= c <= hi_ok)


def _decide(rule_id, facts, values):
    if any(v is CONFLICT for v in values.values()):
        return "needs_evidence"
    pred = PREDICATES[rule_id]
    unknown = [f for f, v in values.items() if v is None]
    if not unknown:
        return "pass" if pred(values) else "fail"
    kinds = {f: facts[f][0] for f in facts}
    known_by_kind = {}
    for f, v in values.items():
        if v is not None:
            known_by_kind.setdefault(kinds[f], []).append(v)
    n_by_kind = {}
    for f in unknown:
        n_by_kind[kinds[f]] = n_by_kind.get(kinds[f], 0) + 1
    domains = [
        _candidates(kinds[f], known_by_kind.get(kinds[f], []), n_by_kind[kinds[f]])
        for f in unknown
    ]
    seen_true = seen_false = False
    for combo in itertools.product(*domains):
        trial = dict(values)
        trial.update(zip(unknown, combo))
        if pred(trial):
            seen_true = True
        else:
            seen_false = True
        if seen_true and seen_false:
            return "needs_evidence"
    return "pass" if seen_true else "fail"


# --------------------------------------------------------------------------


def check(workflow, packet_dir):
    if workflow not in WORKFLOWS:
        raise ValueError("unknown workflow: %r" % workflow)
    key, tables, entities = _load_tables(workflow, packet_dir)
    out = {}
    for rule_id, facts in RULES[workflow].items():
        for eid in entities:
            values = {
                f: _gather(kind, sources, tables, key, eid)
                for f, (kind, sources) in facts.items()
            }
            out["%s::%s" % (rule_id, eid)] = _decide(rule_id, facts, values)
    return dict(sorted(out.items()))


def main(argv):
    if len(argv) != 3:
        sys.stderr.write("usage: contract_checker.py <workflow> <packet_dir>\n")
        return 2
    print(json.dumps(check(argv[1], argv[2]), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
