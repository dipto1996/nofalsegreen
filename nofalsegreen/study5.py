"""Study 5: the wage rule on real LCA records.

DECLARED 2026-10-06, before any Study 5 call (docs/STUDY5_DECLARATION.md).

WHY. Every earlier study uses generated records. Here the LCA records are real:
120 certified H-1B LCAs with annual wages, drawn by a fixed rule from the
Department of Labor's public FY2026 Q3 LCA disclosure file
(data/real_lca/PROVENANCE.md). A public disclosure states the wage the employer
offered and the prevailing wage, never the wages actually paid, so whether the
worker was paid the required wage (20 C.F.R. 655.731) cannot be decided from it.
That label is not a matter of legal interpretation.

FIRMS. The 120 rows, in file order, form 12 firms of 10 LCAs. Each LCA gets one
worker on a roster whose column names follow BambooHR's documented export
("Employee #", "Hire Date", "Pay Rate", ...). Worker names are synthetic; no
employer name from the disclosure file is used.

ARMS.
  lca_only   roster without pay fields + the real LCA rows. Every pair needs_evidence.
  salary     as lca_only, plus the roster's "Pay Rate" (salary of record, set to the
             LCA's offered wage). Every pair needs_evidence.
  complete   as salary, plus a payroll register and an actual-wage export, so every
             pair is decidable: half paid at or above the required wage (pass),
             half below it (fail), by a seeded draw.
"""

from __future__ import annotations

import csv
import math
import random
from datetime import date, timedelta
from pathlib import Path

from .schema import Entity, Firm, Label, Pair, Severity, Verdict

DECLARED_ON = "2026-10-06"
ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "data" / "real_lca" / "sample_120.csv"
DIR = ROOT / "data" / "study5"
RULE = "lca.wage.required_wage_greater_of"
AS_OF = date(2027, 3, 31)
ARMS = ("lca_only", "salary", "complete")
# Study 7 (docs/STUDY7_DECLARATION.md): the salary arm's three pay fields taken apart.
#   pay_rate_only     roster with "Pay Rate" alone
#   pay_context_only  roster with "Pay Type" and "Pay Schedule" alone
STUDY7_ARMS = ("pay_rate_only", "pay_context_only")
N_FIRMS, PER_FIRM = 12, 10
SEED = 20261006
FIRST = ["Aarav", "Mei", "Lucas", "Sofia", "Omar", "Priya", "Daniel", "Yuki", "Elena", "Kwame",
         "Ines", "Tariq", "Hana", "Mateo", "Leila", "Ravi", "Chloe", "Jun", "Nadia", "Felix"]
LAST = ["Shah", "Chen", "Silva", "Novak", "Haddad", "Iyer", "Brooks", "Tanaka", "Petrov", "Mensah",
        "Duarte", "Rahimi", "Kim", "Lopez", "Farah", "Menon", "Martin", "Park", "Aziz", "Weber"]


def _xl_date(v: str) -> date:
    return date(1899, 12, 30) + timedelta(days=int(float(v)))


def _rows() -> list[dict]:
    with SRC.open(newline="") as fh:
        return list(csv.DictReader(fh))


def build(arm: str) -> list[Firm]:
    rows = _rows()
    assert len(rows) == N_FIRMS * PER_FIRM
    firms = []
    for fi in range(N_FIRMS):
        rng = random.Random(f"{SEED}-{fi}")  # same draws in every arm: names and pass/fail
        part = rows[fi * PER_FIRM:(fi + 1) * PER_FIRM]
        d = DIR / arm / f"f{fi + 1:02d}"
        d.mkdir(parents=True, exist_ok=True)
        workers = []
        for j, r in enumerate(part):
            offered = float(r["WAGE_RATE_OF_PAY_FROM"])
            required = max(offered, float(r["PREVAILING_WAGE"]))  # actual wage set to the offered wage
            ok = rng.random() < 0.5
            k = rng.randint(1, 10)
            annual = required + 1200 * k if ok else required - 1200 * k
            workers.append({
                "id": f"{fi + 1:02d}{j + 1:02d}", "first": rng.choice(FIRST), "last": rng.choice(LAST),
                "row": r, "hire": _xl_date(r["BEGIN_DATE"]), "offered": offered, "required": required,
                "semimonthly": (math.ceil if ok else math.floor)(annual / 24 * 100) / 100, "ok": ok,
            })
        sources = {}
        p = d / "hris_roster_export.csv"
        with p.open("w", newline="") as fh:
            w = csv.writer(fh)
            cols = {"salary": (0, 1, 2), "complete": (0, 1, 2), "pay_rate_only": (0,), "pay_context_only": (1, 2)}.get(arm, ())
            w.writerow(["Employee #", "First Name", "Last Name", "Job Title", "Hire Date", "Employment Status",
                        "Work Authorization Type", *(["Pay Rate", "Pay Type", "Pay Schedule"][c] for c in cols)])
            for x in workers:
                pay = [f"{x['offered']:.2f} USD", "Salary", "Twice a month"]
                w.writerow([x["id"], x["first"], x["last"], x["row"]["JOB_TITLE"], x["hire"].isoformat(), "Full-Time",
                            "H-1B", *(pay[c] for c in cols)])
        sources["hris_roster_export"] = p
        p = d / "lca_export.csv"
        cols = ["CASE_NUMBER", "JOB_TITLE", "SOC_CODE", "SOC_TITLE", "FULL_TIME_POSITION", "BEGIN_DATE", "END_DATE",
                "WAGE_RATE_OF_PAY_FROM", "WAGE_RATE_OF_PAY_TO", "WAGE_UNIT_OF_PAY", "PREVAILING_WAGE", "PW_UNIT_OF_PAY",
                "PW_WAGE_LEVEL", "WORKSITE_CITY", "WORKSITE_STATE"]
        with p.open("w", newline="") as fh:
            w = csv.writer(fh)
            w.writerow(["EMPLOYEE_NUMBER", *cols])
            for x in workers:
                r = dict(x["row"], WAGE_UNIT_OF_PAY="Year", PW_UNIT_OF_PAY="Year",
                         BEGIN_DATE=_xl_date(x["row"]["BEGIN_DATE"]).isoformat(),
                         END_DATE=_xl_date(x["row"]["END_DATE"]).isoformat())
                w.writerow([x["id"], *(r[c] for c in cols)])
        sources["lca_export"] = p
        if arm == "complete":
            p = d / "payroll_register.csv"
            with p.open("w", newline="") as fh:
                w = csv.writer(fh)
                w.writerow(["employeeNumber", "payPeriodStart", "payPeriodEnd", "payDate", "payFrequency",
                            "fullOrPartTime", "grossPay"])
                for x in workers:
                    for m in (1, 2, 3):
                        for a, b in ((1, 15), (16, (31 if m in (1, 3) else 28))):
                            w.writerow([x["id"], date(2027, m, a).isoformat(), date(2027, m, b).isoformat(),
                                        date(2027, m, b).isoformat(), "Semimonthly", "FT", f"{x['semimonthly']:.2f}"])
            sources["payroll_register"] = p
            p = d / "actual_wage_system.csv"
            with p.open("w", newline="") as fh:
                w = csv.writer(fh)
                w.writerow(["CASE_NUMBER", "JOB_TITLE", "ACTUAL_WAGE_FOR_SIMILARLY_EMPLOYED_ANNUAL", "BASIS"])
                for x in workers:
                    w.writerow([x["row"]["CASE_NUMBER"], x["row"]["JOB_TITLE"], f"{x['offered']:.2f}",
                                "Employer actual wage system: rate paid to workers with similar experience and "
                                "qualifications in this role"])
            sources["actual_wage_system"] = p
        entities, pairs, labels = [], [], []
        for x in workers:
            case = x["row"]["CASE_NUMBER"]
            entities.append(Entity(case, "lca", f"LCA {case}"))
            pair = Pair.make(RULE, case)
            pairs.append(pair)
            v = (Verdict.PASS if x["ok"] else Verdict.FAIL) if arm == "complete" else Verdict.NEEDS_EVIDENCE
            labels.append(Label(pair_id=pair.pair_id, verdict=v,
                                basis="real_lca_constructed_pay" if arm == "complete" else "no_record_of_wages_paid",
                                severity=Severity.HIGH if v is Verdict.FAIL else None,
                                evidence_fields=("payroll_register", "actual_wage_system")))
        firms.append(Firm(firm_id=f"real-lca-{fi + 1:02d}-study5-{arm}", name=f"Employer {fi + 1:02d}",
                          as_of=AS_OF.isoformat(), sources=sources, entities=entities, pairs=pairs, labels=labels,
                          provenance={"seed": fi + 1, "study": "study5", "arm": arm, "real_lca_rows": True,
                                      "withheld_exports": [] if arm == "complete" else ["payroll", "actual_wage"]}))
    return firms


def load_firms(rb, arm: str) -> list[Firm]:
    return build(arm)
