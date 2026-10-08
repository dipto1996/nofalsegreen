#!/usr/bin/env python3
"""Independent reference checker for the Study 15 decision contracts.

Written from docs/study15/CONTRACT_SPEC.md and the native packet formats only.
Standard library only, Python 3.9+.

    python3 labelcheck/study15_checker.py <fda|usa|lca> <packet_dir>   # JSON verdicts
    python3 labelcheck/study15_checker.py --selftest                     # hand-worked cases

Exactness
---------
* Amounts become fractions.Fraction built from the decimal text. JSON is parsed with
  parse_float=Decimal and parse_int=Decimal, so no binary float is ever created;
  Fraction(Decimal) is exact. CSV cells are decimal text, Fraction(text) is exact.
* Dates become integer day ordinals (datetime.date.toordinal), so "+ k days" is integer
  addition of calendar days.

Step 4 (missing facts) -- exact over ALL real values, not a sample
-----------------------------------------------------------------
Every rule is one comparison between one fact and a linear transform of the other, so it
can be written as a single linear form

    f(x1, x2) = a1*x1 + a2*x2 + d   and the predicate is   f >= 0

with exact rational a1, a2, d (table RULES below). Each fact has a domain:
    date   : all integers (any calendar day; unbounded both ways)
    amount : [0, +inf)    ("any amount >= 0"; closed at 0)
Substitute the known facts; f is then linear in the missing facts and each missing fact
ranges independently over its domain, so over the product domain

    inf f = const + sum_i inf(a_i * x_i),   sup f = const + sum_i sup(a_i * x_i)

with, per missing fact (a_i != 0 for every fact in every rule):
    date             : inf = -inf, sup = +inf
    amount, a_i > 0  : inf = 0 (attained at x_i = 0), sup = +inf
    amount, a_i < 0  : inf = -inf, sup = 0 (attained at x_i = 0)
Every finite inf/sup is ATTAINED (at x_i = 0, the closed end of the amount domain), so
    "predicate holds for every completion"  <=>  inf f >= 0   (min f >= 0)
    "predicate fails for every completion"  <=>  sup f <  0   (max f <  0)
and otherwise some completion passes and some fails -> needs_evidence. When inf is -inf a
failing completion exists; when sup is +inf a passing completion exists; so the three
outcomes are exhaustive and mutually exclusive. This is a proof over the whole domain, not
a search. (Integer-valued dates do not matter: an unbounded date variable has unbounded
integer values in both directions, and d is an integer for every date rule.)

Consequences, for the record: any date rule with a missing date -> needs_evidence;
usa.obligated_95 with O missing passes iff V <= 0, with V missing fails iff O < 0;
lca.wage_105 with W missing passes iff P <= 0, with P missing fails iff W < 0.
"""

import csv
import datetime as _dt
import json
import os
import sys
import tempfile
from decimal import Decimal, InvalidOperation
from fractions import Fraction

PASS, FAIL, NEEDS = "pass", "fail", "needs_evidence"
DATE, AMOUNT = "date", "amount"

# workflow -> (file name, entity-key field)
DOCUMENTS = {
    "fda": ("fda_enforcement_reports.json", "recall_number"),
    "usa": ("usaspending_awards.json", "generated_unique_award_id"),
    "lca": ("lca_disclosure.csv", "CASE_NUMBER"),
}

# Facts: name -> (field path, kind). usa fields are paths into nested objects.
FACTS = {
    "fda": {
        "I": (("recall_initiation_date",), DATE),
        "C": (("center_classification_date",), DATE),
        "T": (("termination_date",), DATE),
    },
    "usa": {
        "S": (("period_of_performance", "start_date"), DATE),
        "E": (("period_of_performance", "end_date"), DATE),
        "O": (("total_obligation",), AMOUNT),
        "V": (("base_and_all_options",), AMOUNT),
    },
    "lca": {
        "B": (("BEGIN_DATE",), DATE),
        "E": (("END_DATE",), DATE),
        "W": (("WAGE_RATE_OF_PAY_FROM",), AMOUNT),
        "P": (("PREVAILING_WAGE",), AMOUNT),
    },
}

# rule_id -> (coefficients {fact: a}, constant d); predicate is sum(a*x) + d >= 0.
RULES = {
    "fda": {
        # C <= I + 30   <=>   I - C + 30 >= 0
        "fda.classified_30d": ({"I": Fraction(1), "C": Fraction(-1)}, Fraction(30)),
        # T <= I + 180  <=>   I - T + 180 >= 0
        "fda.terminated_180d": ({"I": Fraction(1), "T": Fraction(-1)}, Fraction(180)),
    },
    "usa": {
        # E <= S + 1095 <=>   S - E + 1095 >= 0
        "usa.period_3y": ({"S": Fraction(1), "E": Fraction(-1)}, Fraction(1095)),
        # O >= 0.95 V   <=>   O - (19/20) V >= 0
        "usa.obligated_95": ({"O": Fraction(1), "V": Fraction(-19, 20)}, Fraction(0)),
    },
    "lca": {
        # W >= 1.05 P   <=>   W - (21/20) P >= 0
        "lca.wage_105": ({"W": Fraction(1), "P": Fraction(-21, 20)}, Fraction(0)),
        # E >= B + 1095 <=>   E - B - 1095 >= 0
        "lca.three_years": ({"E": Fraction(1), "B": Fraction(-1)}, Fraction(-1095)),
    },
}

_EXCEL_EPOCH = _dt.date(1899, 12, 30)
_MISSING = object()


# ----------------------------------------------------------------------------- parsing

def _to_fraction(raw):
    """Exact rational from a Decimal, an int, or decimal text. Never accepts a float."""
    if isinstance(raw, bool) or isinstance(raw, float):
        raise TypeError("binary float / bool amount not allowed: %r" % (raw,))
    if isinstance(raw, Decimal):
        if not raw.is_finite():
            raise ValueError("non-finite amount %r" % (raw,))
        return Fraction(raw)
    if isinstance(raw, int):
        return Fraction(raw)
    if isinstance(raw, str):
        s = raw.strip()
        try:
            d = Decimal(s)
        except InvalidOperation:
            raise ValueError("not a decimal number: %r" % (raw,))
        if not d.is_finite():
            raise ValueError("non-finite amount %r" % (raw,))
        return Fraction(d)
    raise TypeError("unsupported amount value %r" % (raw,))


def _ymd(s):
    if len(s) != 10 or s[4] != "-" or s[7] != "-":
        raise ValueError("not YYYY-MM-DD: %r" % (s,))
    return _dt.date(int(s[0:4]), int(s[5:7]), int(s[8:10])).toordinal()


def parse_date(workflow, raw):
    if workflow == "fda":
        if not isinstance(raw, str) or len(raw) != 8 or not raw.isdigit():
            raise ValueError("fda date must be YYYYMMDD: %r" % (raw,))
        return _dt.date(int(raw[0:4]), int(raw[4:6]), int(raw[6:8])).toordinal()
    if workflow == "usa":
        if not isinstance(raw, str):
            raise ValueError("usa date must be a string: %r" % (raw,))
        return _ymd(raw[:10])  # ignore anything after the first ten characters
    if workflow == "lca":
        n = _to_fraction(raw)  # "46126" or "46126.0"
        if n.denominator != 1:
            raise ValueError("lca Excel serial is not a whole day: %r" % (raw,))
        return (_EXCEL_EPOCH + _dt.timedelta(days=int(n))).toordinal()
    raise ValueError(workflow)


def _is_missing(workflow, raw):
    if raw is _MISSING:
        return True
    if workflow == "fda":
        return raw == ""
    if workflow == "usa":
        return raw is None
    if workflow == "lca":
        return raw == ""
    raise ValueError(workflow)


def _lookup(workflow, record, path):
    cur = record
    for i, part in enumerate(path):
        if workflow == "usa" and i < len(path) - 1 and cur is None:
            return _MISSING  # absent (null) parent object
        if not isinstance(cur, dict) or part not in cur:
            return _MISSING  # absent key / absent parent object
        cur = cur[part]
    if workflow == "usa" and isinstance(cur, dict):
        raise ValueError("expected a scalar at %r" % (path,))
    return cur


def fact_value(workflow, record, fact):
    """Parsed value of a fact in one record, or None if the record has no value."""
    path, kind = FACTS[workflow][fact]
    raw = _lookup(workflow, record, path)
    if _is_missing(workflow, raw):
        return None
    return parse_date(workflow, raw) if kind == DATE else _to_fraction(raw)


def load_records(workflow, packet_dir):
    fname, _ = DOCUMENTS[workflow]
    path = os.path.join(packet_dir, fname)
    if workflow == "lca":
        with open(path, newline="", encoding="utf-8-sig") as fh:
            return list(csv.DictReader(fh))
    with open(path, encoding="utf-8") as fh:
        doc = json.load(fh, parse_float=Decimal, parse_int=Decimal)
    if workflow == "fda":
        if not isinstance(doc, dict) or not isinstance(doc.get("results"), list):
            raise ValueError("fda document must be an object with a results list")
        return doc["results"]
    if not isinstance(doc, list):
        raise ValueError("usa document must be a JSON list")
    return doc


# ---------------------------------------------------------------------------- verdicts

def decide(coeffs, const, kinds, values):
    """Steps 3 and 4 for one rule. values: fact -> exact value or None (no value)."""
    lo = const      # running inf of f; None means -inf
    hi = const      # running sup of f; None means +inf
    for fact, a in coeffs.items():
        v = values[fact]
        if v is not None:
            term = a * v
            lo = None if lo is None else lo + term
            hi = None if hi is None else hi + term
            continue
        if kinds[fact] == DATE:          # any date: a*x spans (-inf, +inf)
            lo, hi = None, None
        elif a > 0:                      # amount x>=0: a*x spans [0, +inf)
            hi = None
        elif a < 0:                      # amount x>=0: a*x spans (-inf, 0]
            lo = None
    if lo is not None and lo >= 0:       # min f >= 0 (finite inf is attained)
        return PASS
    if hi is not None and hi < 0:        # max f < 0  (finite sup is attained)
        return FAIL
    return NEEDS


def check(workflow, packet_dir):
    if workflow not in DOCUMENTS:
        raise ValueError("unknown workflow %r" % (workflow,))
    _, key_field = DOCUMENTS[workflow]
    records = load_records(workflow, packet_dir)

    # Step 1: per entity, per fact, the set of distinct non-missing parsed values.
    entities = {}
    for rec in records:
        key = rec.get(key_field) if isinstance(rec, dict) else None
        if key is None or key == "" or isinstance(key, Decimal):
            raise ValueError("record without a usable %s: %r" % (key_field, key))
        facts = entities.setdefault(key, {f: set() for f in FACTS[workflow]})
        for f in FACTS[workflow]:
            v = fact_value(workflow, rec, f)
            if v is not None:
                facts[f].add(v)

    kinds = {f: k for f, (_, k) in FACTS[workflow].items()}
    out = {}
    for key, facts in entities.items():
        for rule_id, (coeffs, const) in RULES[workflow].items():
            if any(len(facts[f]) > 1 for f in coeffs):     # Step 2: conflicting
                verdict = NEEDS
            else:                                           # Steps 3 / 4
                values = {f: (next(iter(facts[f])) if facts[f] else None) for f in coeffs}
                verdict = decide(coeffs, const, kinds, values)
            out["%s::%s" % (rule_id, key)] = verdict
    return dict(sorted(out.items()))


# --------------------------------------------------------------------------- self-test

def _write_packet(tmp, workflow, records):
    d = tempfile.mkdtemp(dir=tmp)
    fname, _ = DOCUMENTS[workflow]
    path = os.path.join(d, fname)
    if workflow == "fda":
        with open(path, "w", encoding="utf-8") as fh:
            json.dump({"meta": {}, "results": records}, fh)
    elif workflow == "usa":
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(records)  # raw JSON text, so number literals are exactly as written
    else:
        cols = ["CASE_NUMBER", "JOB_TITLE", "BEGIN_DATE", "END_DATE",
                "WAGE_RATE_OF_PAY_FROM", "WAGE_RATE_OF_PAY_TO", "PREVAILING_WAGE"]
        with open(path, "w", newline="", encoding="utf-8") as fh:
            w = csv.DictWriter(fh, fieldnames=cols)
            w.writeheader()
            for r in records:
                w.writerow({c: r.get(c, "") for c in cols})
    return d


def _fda(n, i, c, t):
    return {"recall_number": n, "recall_initiation_date": i,
            "center_classification_date": c, "termination_date": t,
            "status": "Terminated", "report_date": "20000101"}


def _xl(d):
    return str((d - _EXCEL_EPOCH).days)


def selftest():
    results = []

    def expect(got, key, want, label):
        ok = got.get(key) == want
        results.append((ok, label, key, want, got.get(key)))

    with tempfile.TemporaryDirectory() as tmp:
        # ---------------- fda: I = 2019-05-24; +30 = 2019-06-23; +31 = 2019-06-24;
        #                  +180 = 2019-11-20; +181 = 2019-11-21
        recs = [
            _fda("F-1", "20190524", "20190623", "20191120"),   # C=I+30, T=I+180 -> pass
            _fda("F-2", "20190524", "20190624", "20191121"),   # C=I+31, T=I+181 -> fail
            _fda("F-3", "", "20190623", "20191120"),           # I missing -> needs
            _fda("F-4", "20190524", "", "20191120"),           # C missing -> needs; T pass
            {"recall_number": "F-5", "recall_initiation_date": "20190524"},  # absent keys
            _fda("F-6", "20190524", "20190601", "20190701"),   # dup, disagreeing C
            _fda("F-6", "20190524", "20190602", "20190701"),
            _fda("F-7", "20190524", "20190601", ""),           # dup, complementary
            _fda("F-7", "20190524", "", "20190701"),           # (no conflict)
            _fda("F-8", "20240131", "20240301", "20240301"),   # leap year: I+30 = 03-01
        ]
        g = check("fda", _write_packet(tmp, "fda", recs))
        expect(g, "fda.classified_30d::F-1", PASS, "fda C = I + 30 passes")
        expect(g, "fda.classified_30d::F-2", FAIL, "fda C = I + 31 fails")
        expect(g, "fda.terminated_180d::F-1", PASS, "fda T = I + 180 passes")
        expect(g, "fda.terminated_180d::F-2", FAIL, "fda T = I + 181 fails")
        expect(g, "fda.classified_30d::F-3", NEEDS, "fda I missing")
        expect(g, "fda.terminated_180d::F-3", NEEDS, "fda I missing (T rule)")
        expect(g, "fda.classified_30d::F-4", NEEDS, "fda C empty string")
        expect(g, "fda.terminated_180d::F-4", PASS, "fda T rule unaffected by missing C")
        expect(g, "fda.classified_30d::F-5", NEEDS, "fda C absent key")
        expect(g, "fda.terminated_180d::F-5", NEEDS, "fda T absent key")
        expect(g, "fda.classified_30d::F-6", NEEDS, "fda duplicate disagreeing C")
        expect(g, "fda.terminated_180d::F-6", PASS, "fda duplicate agreeing T, I")
        expect(g, "fda.classified_30d::F-7", PASS, "fda duplicate missing+present merges")
        expect(g, "fda.terminated_180d::F-7", PASS, "fda duplicate missing+present merges (T)")
        expect(g, "fda.classified_30d::F-8", PASS, "fda leap-year calendar days")
        results.append((len(g) == 16, "fda one key per entity x rule", "count", 16, len(g)))

        # ---------------- usa: S = 2016-01-01; +1095 = 2018-12-31; +1096 = 2019-01-01
        usa_text = """[
 {"generated_unique_award_id": "U-1", "total_obligation": 95.00, "base_and_all_options": 100,
  "period_of_performance": {"start_date": "2016-01-01", "end_date": "2018-12-31",
                            "potential_end_date": "2030-01-01 00:00:00"}},
 {"generated_unique_award_id": "U-2", "total_obligation": 94.99, "base_and_all_options": 100.00,
  "period_of_performance": {"start_date": "2016-01-01 00:00:00", "end_date": "2019-01-01T12:00:00"}},
 {"generated_unique_award_id": "U-3", "total_obligation": null, "base_and_all_options": 0.0,
  "period_of_performance": {"start_date": null, "end_date": "2018-12-31"}},
 {"generated_unique_award_id": "U-4", "base_and_all_options": 5},
 {"generated_unique_award_id": "U-5", "total_obligation": 7, "base_and_all_options": null,
  "period_of_performance": null},
 {"generated_unique_award_id": "U-6", "total_obligation": -1, "base_and_all_options": null,
  "period_of_performance": {"start_date": "2016-01-01"}},
 {"generated_unique_award_id": "U-7", "total_obligation": 10, "base_and_all_options": 10,
  "period_of_performance": {"start_date": "2016-01-01", "end_date": "2016-06-01"}},
 {"generated_unique_award_id": "U-7", "total_obligation": 11, "base_and_all_options": 10.0,
  "period_of_performance": {"start_date": "2016-01-01", "end_date": "2016-06-01 00:00:00"}},
 {"generated_unique_award_id": "U-8", "total_obligation": 0.95, "base_and_all_options": 1.0000000000000000001}
]"""
        g = check("usa", _write_packet(tmp, "usa", usa_text))
        expect(g, "usa.period_3y::U-1", PASS, "usa E = S + 1095 passes")
        expect(g, "usa.period_3y::U-2", FAIL, "usa E = S + 1096 fails (time suffixes ignored)")
        expect(g, "usa.obligated_95::U-1", PASS, "usa O = 0.95 V passes")
        expect(g, "usa.obligated_95::U-2", FAIL, "usa O just below 0.95 V fails")
        expect(g, "usa.obligated_95::U-3", PASS, "usa V = 0 with O missing passes")
        expect(g, "usa.period_3y::U-3", NEEDS, "usa S null")
        expect(g, "usa.period_3y::U-4", NEEDS, "usa absent parent object")
        expect(g, "usa.obligated_95::U-4", NEEDS, "usa O absent key, V > 0")
        expect(g, "usa.period_3y::U-5", NEEDS, "usa null parent object")
        expect(g, "usa.obligated_95::U-5", NEEDS, "usa V missing, O >= 0")
        expect(g, "usa.obligated_95::U-6", FAIL, "usa V missing, O < 0 fails for all V >= 0")
        expect(g, "usa.period_3y::U-6", NEEDS, "usa end_date absent key")
        expect(g, "usa.obligated_95::U-7", NEEDS, "usa duplicate disagreeing O")
        expect(g, "usa.period_3y::U-7", PASS, "usa duplicate agreeing dates (suffix ignored)")
        expect(g, "usa.obligated_95::U-8", FAIL, "usa exact decimal: no float rounding")

        # ---------------- lca: B = 2026-04-14; +1095 = 2029-04-13; +1094 = 2029-04-12
        B = _dt.date(2026, 4, 14)
        E_ok = B + _dt.timedelta(days=1095)
        E_bad = B + _dt.timedelta(days=1094)
        recs = [
            {"CASE_NUMBER": "L-1", "BEGIN_DATE": _xl(B), "END_DATE": _xl(E_ok),
             "WAGE_RATE_OF_PAY_FROM": "105", "PREVAILING_WAGE": "100"},
            {"CASE_NUMBER": "L-2", "BEGIN_DATE": _xl(B) + ".0", "END_DATE": _xl(E_bad) + ".0",
             "WAGE_RATE_OF_PAY_FROM": "104.99", "PREVAILING_WAGE": "100.00",
             "WAGE_RATE_OF_PAY_TO": "999999"},
            {"CASE_NUMBER": "L-3", "BEGIN_DATE": _xl(B) + ".0", "END_DATE": _xl(E_ok),
             "WAGE_RATE_OF_PAY_FROM": "", "PREVAILING_WAGE": "0"},
            {"CASE_NUMBER": "L-4", "BEGIN_DATE": "", "END_DATE": _xl(E_ok),
             "WAGE_RATE_OF_PAY_FROM": "", "PREVAILING_WAGE": "50000"},
            {"CASE_NUMBER": "L-5", "BEGIN_DATE": _xl(B), "END_DATE": "",
             "WAGE_RATE_OF_PAY_FROM": "70000", "PREVAILING_WAGE": ""},
            {"CASE_NUMBER": "L-6", "BEGIN_DATE": _xl(B), "END_DATE": _xl(E_ok),
             "WAGE_RATE_OF_PAY_FROM": "80000", "PREVAILING_WAGE": "70000"},
            {"CASE_NUMBER": "L-6", "BEGIN_DATE": _xl(B), "END_DATE": _xl(E_bad),
             "WAGE_RATE_OF_PAY_FROM": "80000.0", "PREVAILING_WAGE": "70000.00"},
            {"CASE_NUMBER": "L-7", "BEGIN_DATE": "", "END_DATE": "",
             "WAGE_RATE_OF_PAY_FROM": "", "PREVAILING_WAGE": ""},
            {"CASE_NUMBER": "L-8", "BEGIN_DATE": _xl(B), "END_DATE": _xl(E_ok),
             "WAGE_RATE_OF_PAY_FROM": "77112.759999999995",
             "PREVAILING_WAGE": "73440.723809523805"},
        ]
        g = check("lca", _write_packet(tmp, "lca", recs))
        expect(g, "lca.three_years::L-1", PASS, "lca E = B + 1095 passes")
        expect(g, "lca.three_years::L-2", FAIL, "lca E = B + 1094 fails (serials with .0)")
        expect(g, "lca.wage_105::L-1", PASS, "lca W = 1.05 P passes")
        expect(g, "lca.wage_105::L-2", FAIL, "lca W just below 1.05 P fails")
        expect(g, "lca.three_years::L-3", PASS, "lca .0 serial equals integer serial")
        expect(g, "lca.wage_105::L-3", PASS, "lca P = 0 with W missing passes")
        expect(g, "lca.wage_105::L-4", NEEDS, "lca W missing, P > 0")
        expect(g, "lca.three_years::L-4", NEEDS, "lca B missing")
        expect(g, "lca.wage_105::L-5", NEEDS, "lca P missing, W >= 0")
        expect(g, "lca.three_years::L-5", NEEDS, "lca E missing")
        expect(g, "lca.three_years::L-6", NEEDS, "lca duplicate disagreeing E")
        expect(g, "lca.wage_105::L-6", PASS, "lca duplicate numerically equal W, P agree")
        expect(g, "lca.wage_105::L-7", NEEDS, "lca both amounts missing")
        expect(g, "lca.three_years::L-7", NEEDS, "lca both dates missing")
        # W - 1.05 P = 77112.759999999995 - 77112.75999999999525 = -1/4e12 < 0: fails by a
        # margin far below float resolution at this magnitude (ulp ~ 1.5e-11).
        expect(g, "lca.wage_105::L-8", FAIL, "lca exact decimal text (sub-ulp shortfall)")

    # Direct checks of the excel conversion and the step-4 table.
    results.append((parse_date("lca", "1") == _dt.date(1899, 12, 31).toordinal(),
                    "excel serial 1 = 1899-12-31 per date(1899,12,30)+n", "", True, None))
    results.append((parse_date("lca", "46126.0") == parse_date("lca", "46126"),
                    "excel serial trailing .0", "", True, None))
    results.append((_dt.date.fromordinal(parse_date("lca", "46126")) == _dt.date(2026, 4, 14),
                    "excel serial 46126 = 2026-04-14", "", True, None))
    for bad in ("46126.5",):
        try:
            parse_date("lca", bad)
            results.append((False, "fractional serial rejected", bad, "error", "accepted"))
        except ValueError:
            results.append((True, "fractional serial rejected", bad, "error", "error"))
    try:
        _to_fraction(0.95)
        results.append((False, "binary float rejected", "", "error", "accepted"))
    except TypeError:
        results.append((True, "binary float rejected", "", "error", "error"))

    failed = [r for r in results if not r[0]]
    for ok, label, key, want, got in results:
        print("%s  %s  %s" % ("ok  " if ok else "FAIL", label, "" if ok else
                               "(%s: want %r got %r)" % (key, want, got)))
    print("selftest: %d/%d passed" % (len(results) - len(failed), len(results)))
    return 0 if not failed else 1


def main(argv):
    if len(argv) == 2 and argv[1] == "--selftest":
        return selftest()
    if len(argv) != 3:
        sys.stderr.write("usage: study15_checker.py <fda|usa|lca> <packet_dir> | --selftest\n")
        return 2
    print(json.dumps(check(argv[1], argv[2]), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
