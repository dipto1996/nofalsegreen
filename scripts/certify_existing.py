"""Certificates for the needs_evidence labels of the generated firms of Studies 3, 3c, 4 and 8.

These firms withhold whole exports. For each firm with a withheld export, write two
completions of the missing export(s): one in which every affected obligation is met and one
in which every one is violated (on-time vs late I-9 dates; payroll at vs below the prevailing
wage; an actual wage below vs above the wages paid). The independently written reference
checker (labelcheck/reference_checker.py) must then return `pass` for every needs_evidence
pair in the first completion and `fail` in the second, which certifies that the visible
records cannot decide it. Writes docs/existing_certificates.json. No API call.
"""

from __future__ import annotations

import csv
import json
import shutil
import sys
import tempfile
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "labelcheck"))

import reference_checker as RC  # noqa: E402  (independent implementation)
from nofalsegreen import study3, study3c, study8  # noqa: E402
from nofalsegreen.generator import add_business_days  # noqa: E402
from nofalsegreen.rulebook import Rulebook  # noqa: E402

EVAL = RC.EVAL_DATE


def read(p: Path) -> list[dict]:
    with p.open(newline="") as fh:
        return list(csv.DictReader(fh))


def write(p: Path, header: list, rows: list) -> None:
    with p.open("w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(header)
        w.writerows(rows)


def complete(src: Path, withheld: list, ok: bool, dst: Path) -> None:
    shutil.copytree(src, dst)
    roster = read(dst / "hris_roster_export.csv")
    lcas = read(dst / "lca_export.csv")
    if "i9" in withheld:
        rows = []
        for w in roster:
            first = date.fromisoformat(w["hireDate"])
            temp = w["visaType"].strip().lower() not in RC.NO_REVERIFY_STATUSES
            exp = EVAL - timedelta(days=30) if temp else None
            s1 = first if ok else first + timedelta(days=2)
            s2 = add_business_days(first, 1) if ok else add_business_days(first, 8)
            rev = (exp - timedelta(days=5) if ok else exp + timedelta(days=5)) if exp else None
            rows.append([w["employeeNumber"], (first - timedelta(days=20)).isoformat(), first.isoformat(), "Y",
                         s1.isoformat(), s2.isoformat(), exp.isoformat() if exp else "",
                         rev.isoformat() if rev else "", "Form I-797A Approval Notice with Form I-94" if exp else ""])
        write(dst / "i9_record_export.csv", ["employeeNumber", "offerAcceptedDate", "firstDayOfEmployment",
                                             "section1Signed", "section1SignDate", "section2EmployerSignDate",
                                             "workAuthorizationExpiry", "supplementBReverificationDate",
                                             "supplementBDocumentType"], rows)
    if "payroll" in withheld:
        rows = []
        for l in lcas:
            pw = float(l["PREVAILING_WAGE"])
            req = max(pw, float(l["WAGE_RATE_OF_PAY_FROM"]))
            annual = req * 2 if ok else pw * 0.5
            for m in (4, 5, 6):
                for a, b in ((1, 15), (16, 30 if m != 5 else 31)):
                    s, e = date(2026, m, a), date(2026, m, b)
                    rows.append([l["EMPLOYEE_NUMBER"], s.isoformat(), e.isoformat(), e.isoformat(), "Semimonthly", "FT",
                                 "86.67", round(annual / 24, 2)])
        write(dst / "payroll_register.csv", ["employeeNumber", "payPeriodStart", "payPeriodEnd", "payDate",
                                             "payFrequency", "fullOrPartTime", "regularHours", "grossPay"], rows)
    if "actual_wage" in withheld:
        rows, seen = [], set()
        for l in lcas:
            k = (l["SOC_CODE"], l["JOB_TITLE"])
            if k in seen:
                continue
            seen.add(k)
            rows.append([l["SOC_CODE"], l["JOB_TITLE"], 1.0 if ok else 10_000_000.0, "completion"])
        write(dst / "actual_wage_system.csv", ["SOC_CODE", "JOB_TITLE", "ACTUAL_WAGE_FOR_SIMILARLY_EMPLOYED_ANNUAL", "BASIS"], rows)


def firm_dirs(rb):
    out = []
    for arm in study3.ARMS:
        out += [(f"study3-{arm}", f) for f in study3.load_firms(rb, arm)]
    for arm in study3c.ARMS:
        out += [(f"study3c-{arm}", f) for f in study3c.load_firms(rb, arm)]
    for arm in study8.ARMS:
        out += [(f"study8-{arm}", f) for f in study8.load_firms(rb, arm)]
    return out


def main() -> int:
    rb = Rulebook.load(ROOT / "rulebook" / "rulebook.json")
    tmp = Path(tempfile.mkdtemp())
    res = {"firms": 0, "needs_evidence_pairs": 0, "certified": 0, "failures": []}
    for tag, f in firm_dirs(rb):
        src = Path(f.sources["hris_roster_export"]).parent
        withheld = f.provenance["withheld_exports"]
        ne = [l.pair_id for l in f.labels if l.verdict.value == "needs_evidence"]
        if not ne:
            continue
        res["firms"] += 1
        got = {}
        for ok in (True, False):
            d = tmp / f"{tag}-{f.provenance['seed']}-{ok}"
            complete(src, withheld, ok, d)
            got[ok] = RC.check_firm(str(d))
        for pid in ne:
            res["needs_evidence_pairs"] += 1
            if got[True].get(pid) == "pass" and got[False].get(pid) == "fail":
                res["certified"] += 1
            else:
                res["failures"].append({"firm": tag, "seed": f.provenance["seed"], "pair": pid,
                                        "complete_ok": got[True].get(pid), "complete_bad": got[False].get(pid)})
    (ROOT / "docs" / "existing_certificates.json").write_text(json.dumps(res, indent=1))
    print({k: (v if not isinstance(v, list) else len(v)) for k, v in res.items()})
    for x in res["failures"][:8]:
        print(x)
    return 0 if not res["failures"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
