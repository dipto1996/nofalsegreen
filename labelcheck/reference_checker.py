#!/usr/bin/env python3
"""Independent reference checker for four employer compliance obligations.

Pure stdlib. Works only from the firm's CSV exports and primary-law readings
documented in labelcheck/INTERPRETATIONS.md.

Usage: python3 labelcheck/reference_checker.py <firm_dir> [<firm_dir> ...]
Prints JSON {firm_dir: {"<rule_id>::<entity_id>": verdict}}.
"""
import csv
import datetime as dt
import json
import os
import sys

EVAL_DATE = dt.date(2026, 6, 29)

PASS, FAIL, NEEDS = "pass", "fail", "needs_evidence"

S1 = "i9.section1.timeliness"
S2 = "i9.section2.timeliness"
REV = "i9.reverification.deadline"
LCA = "lca.wage.required_wage_greater_of"

# Statuses that never require reverification (M-274 6.1 / 8 CFR 274a.2(b)(1)(vii)).
NO_REVERIFY_STATUSES = {"us citizen", "u.s. citizen", "citizen", "us national",
                        "noncitizen national", "lpr", "lawful permanent resident",
                        "green card", "permanent resident"}

# List B documents (identity only) can never be used for reverification.
LIST_B_HINTS = ("driver", "school id", "voter", "military card", "school record",
                "hospital record", "day-care", "nursery")


# ---------------------------------------------------------------- utilities
def read_csv(firm_dir, name):
    path = os.path.join(firm_dir, name)
    if not os.path.exists(path):
        return None
    with open(path, newline="", encoding="utf-8") as fh:
        return [{k.strip(): (v or "").strip() for k, v in row.items()}
                for row in csv.DictReader(fh)]


def parse_date(s):
    if not s:
        return None
    try:
        return dt.date.fromisoformat(s[:10])
    except ValueError:
        return None


def parse_num(s):
    if s is None or s == "":
        return None
    try:
        return float(s.replace(",", "").replace("$", ""))
    except ValueError:
        return None


# ------------------------------------------------- federal holiday calendar
def _nth_weekday(year, month, weekday, n):
    d = dt.date(year, month, 1)
    d += dt.timedelta(days=(weekday - d.weekday()) % 7)
    return d + dt.timedelta(weeks=n - 1)


def _last_weekday(year, month, weekday):
    d = dt.date(year + (month == 12), (month % 12) + 1, 1) - dt.timedelta(days=1)
    return d - dt.timedelta(days=(d.weekday() - weekday) % 7)


def _observed(d):
    # 5 U.S.C. 6103(b) / EO 11582: Saturday -> Friday, Sunday -> Monday.
    if d.weekday() == 5:
        return d - dt.timedelta(days=1)
    if d.weekday() == 6:
        return d + dt.timedelta(days=1)
    return d


def federal_holidays(year):
    """Legal public holidays under 5 U.S.C. 6103(a), observed dates."""
    h = {
        _observed(dt.date(year, 1, 1)),             # New Year's Day
        _nth_weekday(year, 1, 0, 3),                # MLK Day
        _nth_weekday(year, 2, 0, 3),                # Washington's Birthday
        _last_weekday(year, 5, 0),                  # Memorial Day
        _observed(dt.date(year, 7, 4)),             # Independence Day
        _nth_weekday(year, 9, 0, 1),                # Labor Day
        _nth_weekday(year, 10, 0, 2),               # Columbus Day
        _observed(dt.date(year, 11, 11)),           # Veterans Day
        _nth_weekday(year, 11, 3, 4),               # Thanksgiving
        _observed(dt.date(year, 12, 25)),           # Christmas
    }
    if year >= 2021:                                # Juneteenth (Pub. L. 117-17)
        h.add(_observed(dt.date(year, 6, 19)))
    # New Year's Day of the following year can be observed on Dec 31.
    h.add(_observed(dt.date(year + 1, 1, 1)))
    return h


_HOL_CACHE = {}


def is_business_day(d):
    if d.weekday() >= 5:
        return False
    if d.year not in _HOL_CACHE:
        _HOL_CACHE[d.year] = federal_holidays(d.year)
    return d not in _HOL_CACHE[d.year]


def add_business_days(start, n):
    """The n-th business day strictly after `start` (start = day 0)."""
    d, k = start, 0
    while k < n:
        d += dt.timedelta(days=1)
        if is_business_day(d):
            k += 1
    return d


def business_days_between(start, end_inclusive):
    """Count business days in [start, end_inclusive]."""
    n, d = 0, start
    while d <= end_inclusive:
        if is_business_day(d):
            n += 1
        d += dt.timedelta(days=1)
    return n


# ------------------------------------------------------------ obligations
def check_section1(i9):
    if i9 is None:
        return NEEDS
    first = parse_date(i9.get("firstDayOfEmployment"))
    sign = parse_date(i9.get("section1SignDate"))
    offer = parse_date(i9.get("offerAcceptedDate"))
    signed = i9.get("section1Signed", "").upper()
    if first is None or offer is None or signed == "":
        return NEEDS
    if signed in ("N", "NO", "FALSE", "0"):
        # Attestation unsigned; non-compliant once the first day has passed.
        return FAIL if first <= EVAL_DATE else NEEDS
    if sign is None:
        return NEEDS
    if sign > first:
        return FAIL
    if sign < offer:
        return FAIL
    return PASS


def check_section2(i9, roster):
    if i9 is None:
        return NEEDS
    first = parse_date(i9.get("firstDayOfEmployment"))
    s2 = parse_date(i9.get("section2EmployerSignDate"))
    offer = parse_date(i9.get("offerAcceptedDate"))
    if first is None:
        return NEEDS
    # Employment duration: short engagement (<3 business days) -> due day 1.
    term = parse_date(roster.get("terminationDate")) if roster else None
    status = (roster.get("employmentStatus", "") if roster else "").lower()
    if term is None and status not in ("active", "") and roster is not None:
        return NEEDS  # terminated/other with no termination date: duration unknown
    if term is not None and business_days_between(first, term) < 3:
        deadline = first
    else:
        deadline = add_business_days(first, 3)
    if s2 is None:
        return FAIL if deadline < EVAL_DATE else NEEDS
    if s2 > deadline:
        return FAIL
    if offer is not None and s2 < offer:
        return FAIL
    return PASS


def reverification_in_scope(roster, i9):
    """Decide whether this worker is in scope of the reverification rule.

    Returns (in_scope: bool|None, reason). None means 'cannot tell'.
    """
    visa = (roster.get("visaType", "") if roster else "").strip().lower()
    if visa in NO_REVERIFY_STATUSES:
        return False, "citizen/national/LPR - never reverified"
    status = (roster.get("employmentStatus", "") if roster else "").lower()
    term = parse_date(roster.get("terminationDate")) if roster else None
    if i9 is None:
        # Temporary-status worker, but the I-9 export (expiry) is absent.
        return (None, "temporary status, I-9 expiry not exported") if visa else (False, "unknown status")
    exp = parse_date(i9.get("workAuthorizationExpiry"))
    if exp is None:
        return False, "no expiring work authorization recorded on I-9"
    if exp >= EVAL_DATE:
        return False, "authorization not yet expired"
    if term is not None and term <= exp:
        return False, "employment ended before authorization expired"
    if status and status != "active" and term is None:
        return None, "employment status unclear"
    return True, "expired temporary authorization, still employed at expiry"


def check_reverification(i9):
    exp = parse_date(i9.get("workAuthorizationExpiry"))
    rev = parse_date(i9.get("supplementBReverificationDate"))
    doc = i9.get("supplementBDocumentType", "")
    if rev is None:
        return FAIL  # expired and no Supplement B on the I-9 record
    if rev > exp:
        return FAIL
    if not doc:
        return NEEDS
    if any(h in doc.lower() for h in LIST_B_HINTS):
        return FAIL
    return PASS


def annual_rate(amount, unit):
    unit = (unit or "").strip().lower()
    factor = {"year": 1, "yr": 1, "annual": 1, "hour": 2080, "hr": 2080,
              "week": 52, "wk": 52, "bi-weekly": 26, "biweekly": 26,
              "month": 12, "mth": 12}.get(unit)
    if amount is None or factor is None:
        return None
    return amount * factor


PERIODS_PER_YEAR = {"weekly": 52, "biweekly": 26, "bi-weekly": 26,
                    "semimonthly": 24, "semi-monthly": 24, "monthly": 12}


def check_lca(lca, actual_rows, payroll_rows):
    pw = annual_rate(parse_num(lca.get("PREVAILING_WAGE")), lca.get("PW_UNIT_OF_PAY"))
    if pw is None:
        return NEEDS
    aw = None
    if actual_rows is not None:
        for r in actual_rows:
            if (r.get("SOC_CODE") == lca.get("SOC_CODE")
                    and r.get("JOB_TITLE", "").lower() == lca.get("JOB_TITLE", "").lower()):
                aw = parse_num(r.get("ACTUAL_WAGE_FOR_SIMILARLY_EMPLOYED_ANNUAL"))
                break
    # Wages actually paid, per pay period within the LCA validity window that
    # has been paid by the evaluation date.
    if payroll_rows is None:
        return NEEDS
    begin = parse_date(lca.get("BEGIN_DATE")) or dt.date.min
    end = parse_date(lca.get("END_DATE")) or dt.date.max
    ft = lca.get("FULL_TIME_POSITION", "Y").upper() == "Y"
    emp = lca.get("EMPLOYEE_NUMBER")
    periods = []
    for p in payroll_rows:
        if p.get("employeeNumber") != emp:
            continue
        ps, pe = parse_date(p.get("payPeriodStart")), parse_date(p.get("payPeriodEnd"))
        pd_ = parse_date(p.get("payDate")) or pe
        if ps is None or pe is None:
            continue
        if pe < begin or ps > end or pd_ > EVAL_DATE:
            continue
        periods.append(p)
    if not periods:
        return NEEDS

    def short_against(required_annual):
        for p in periods:
            gross = parse_num(p.get("grossPay"))
            freq = PERIODS_PER_YEAR.get(p.get("payFrequency", "").strip().lower())
            if gross is None or freq is None:
                return None
            ps, pe = parse_date(p["payPeriodStart"]), parse_date(p["payPeriodEnd"])
            if ft:
                due = required_annual / freq
            else:
                hrs = parse_num(p.get("regularHours"))
                if hrs is None:
                    return None
                due = required_annual / 2080.0 * hrs
            # Prorate a period only partly inside the LCA window by calendar days.
            covered_s, covered_e = max(ps, begin), min(pe, end)
            frac = ((covered_e - covered_s).days + 1) / ((pe - ps).days + 1)
            due *= frac
            if gross + 0.005 < round(due, 2):
                return True
        return False

    below_pw = short_against(pw)
    if below_pw is None:
        return NEEDS
    if below_pw:
        return FAIL  # below the floor regardless of actual wage
    if aw is None:
        return NEEDS  # actual-wage leg unknown
    below_req = short_against(max(pw, aw))
    if below_req is None:
        return NEEDS
    return FAIL if below_req else PASS


# ------------------------------------------------------------------ driver
def check_firm(firm_dir):
    roster = read_csv(firm_dir, "hris_roster_export.csv") or []
    i9_rows = read_csv(firm_dir, "i9_record_export.csv")
    lcas = read_csv(firm_dir, "lca_export.csv") or []
    payroll = read_csv(firm_dir, "payroll_register.csv")
    actual = read_csv(firm_dir, "actual_wage_system.csv")

    i9_by_emp = {}
    if i9_rows is not None:
        for r in i9_rows:
            i9_by_emp.setdefault(r.get("employeeNumber"), r)

    out = {}
    for w in roster:
        emp = w.get("employeeNumber")
        if not emp:
            continue
        i9 = i9_by_emp.get(emp)
        out[f"{S1}::{emp}"] = check_section1(i9)
        out[f"{S2}::{emp}"] = check_section2(i9, w)
        in_scope, _ = reverification_in_scope(w, i9)
        if in_scope is None:
            out[f"{REV}::{emp}"] = NEEDS
        elif in_scope:
            out[f"{REV}::{emp}"] = check_reverification(i9)
    for l in lcas:
        case = l.get("CASE_NUMBER")
        if case:
            out[f"{LCA}::{case}"] = check_lca(l, actual, payroll)
    return out


def main(argv):
    if not argv:
        print(__doc__, file=sys.stderr)
        return 2
    result = {d: check_firm(d) for d in argv}
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
