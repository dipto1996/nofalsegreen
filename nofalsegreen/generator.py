"""Seeded firm generator, v2.

Produces synthetic employers whose ground truth is fixed BY CONSTRUCTION: for
each (obligation, entity) pair the generator first chooses a disposition and
then renders source records that decide it.

WHY v2. A blind consistency check (2026-10-03) found that v1 emitted a label
for every (rule, entity) pair in the rulebook but rendered deciding data for
only four rule families, and applied rules to entities they cannot govern
(e.g. L-1 rules to H-1B workers). Its labels agreed with an independent
reading of its own records on 8 of 60 sampled pairs. v2 therefore emits a pair
only when BOTH hold:

  1. the rule applies to the entity (an I-9 rule to every worker; the
     reverification rule only to workers whose temporary authorization has
     expired; the LCA wage rule to every certified LCA), and
  2. every item the rulebook lists as "information needed" for that rule is
     rendered in an export, OR the export carrying it is withheld from the
     firm altogether.

Withholding is done at the level of a whole export, never by blanking one
worker's cell: a blank cell for a past deadline reads to a practitioner as
"not done", which is a violation, not missing evidence. A firm either provides
its I-9 export (and every I-9 pair is decidable) or does not (and every I-9
pair is `needs_evidence`).

Rule families rendered (rule ids as in the rulebook):
  i9.section1.timeliness       Section 1 signed on/before the first day of
                               employment and not before offer acceptance
  i9.section2.timeliness       Section 2 within 3 business days of the first
                               day (weekends and federal holidays excluded)
  i9.reverification.deadline   Supplement B on/before the authorization expiry
  lca.wage.required_wage_greater_of
                               wages actually paid >= max(prevailing wage,
                               employer's actual wage for similar workers)

Near-miss controls sit exactly on the boundary: Section 1 on the first day,
Section 2 on business day 3, Supplement B on the expiry date, pay exactly equal
to the required wage. Every firm is reproducible from (seed, config).

DECOYS (v3, `GeneratorConfig.decoys`, declared for Study 3 before any call).
v2 firms withhold whole exports, so abstention reduces to noticing a missing
file, and the adjacent-field substitution seen on the anchor firm cannot occur.
With `decoys=True` the HRIS roster carries five columns that sit beside the
evidence each rule needs without being it:

  i9Status                 "Complete": says a form exists, not when either
                           section was completed (S1, S2 timeliness)
  onboardingCompletedDate  an HR onboarding date near the start date, not a
                           Section 1 or Section 2 date (S1, S2 timeliness)
  workAuthValidThrough     the CURRENT authorization's end date (after the
                           evaluation date), which says nothing about when
                           Supplement B was completed (RV)
  annualBaseSalary         the salary of record, set at the LCA offered wage;
                           not wages actually paid (wage rule, 20 CFR
                           655.731(c))
  payBandMidpoint          an internal pay-band midpoint, not the employer's
                           actual wage for similarly employed workers

The columns appear in EVERY decoy firm, whether or not the export they imitate
is withheld, so their presence reveals nothing. They are drawn from a separate
random stream: a decoy firm and the plain firm of the same seed have identical
workers, labels and other exports, which makes the two arms paired. No label
changes, because none of the five columns is an item the rulebook lists as
evidence for the rule it imitates.
"""

from __future__ import annotations

import csv
import random
from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path

from .rulebook import Rulebook
from .schema import Entity, Firm, Label, Pair, Severity, Verdict

GIVEN = ["Amara", "Bao", "Camila", "Dmitri", "Elena", "Farid", "Grace", "Hana",
         "Ibrahim", "Jonas", "Keiko", "Lars", "Mira", "Nadia", "Omar", "Priya",
         "Qing", "Rosa", "Samir", "Tomas", "Uma", "Viktor", "Wen", "Yara", "Zane"]
FAMILY = ["Abara", "Bianchi", "Costa", "Duarte", "Eriksen", "Fontaine", "Gupta",
          "Haddad", "Ivanov", "Jansen", "Kovac", "Lindqvist", "Mwangi", "Nakamura",
          "Okafor", "Petrov", "Quintero", "Rahman", "Santos", "Tanaka", "Ueda",
          "Volkov", "Whitfield", "Xu", "Yilmaz", "Zhao"]
# (SOC, title, wage level, prevailing wage, employer actual wage); all annual
# amounts are multiples of 1,200 so semimonthly pay is a whole dollar amount.
ROLES = [("15-1252", "Software Developers", "II", 132_000, 138_000),
         ("15-1211", "Computer Systems Analysts", "II", 118_800, 116_400),
         ("17-2199", "Engineers, All Other", "III", 142_800, 150_000),
         ("11-9041", "Architectural and Engineering Managers", "III", 178_800, 186_000)]
CITIES = [("Austin", "TX", "Austin-Round Rock-Georgetown, TX"),
          ("Boston", "MA", "Boston-Cambridge-Newton, MA-NH")]

R_S1 = "i9.section1.timeliness"
R_S2 = "i9.section2.timeliness"
R_RV = "i9.reverification.deadline"
R_WG = "lca.wage.required_wage_greater_of"
RENDERED = (R_S1, R_S2, R_RV, R_WG)
# Which export each rule's information lives in; withholding any one of these
# makes every pair of that rule `needs_evidence`.
NEEDS = {R_S1: ("i9",), R_S2: ("i9",), R_RV: ("i9",), R_WG: ("payroll", "actual_wage")}


# ---------- business-day calendar ----------

def _nth_weekday(y: int, m: int, weekday: int, n: int) -> date:
    d = date(y, m, 1)
    d += timedelta(days=(weekday - d.weekday()) % 7)
    return d + timedelta(weeks=n - 1)


def _last_weekday(y: int, m: int, weekday: int) -> date:
    d = date(y, m + 1, 1) - timedelta(days=1) if m < 12 else date(y, 12, 31)
    return d - timedelta(days=(d.weekday() - weekday) % 7)


def _observed(d: date) -> date:
    if d.weekday() == 5:
        return d - timedelta(days=1)
    if d.weekday() == 6:
        return d + timedelta(days=1)
    return d


def federal_holidays(y: int) -> set[date]:
    """US federal holidays (5 U.S.C. 6103) with the observed-date rule."""
    fixed = [date(y, 1, 1), date(y, 6, 19), date(y, 7, 4), date(y, 11, 11), date(y, 12, 25)]
    out = {_observed(d) for d in fixed}
    out |= {
        _nth_weekday(y, 1, 0, 3),   # Martin Luther King Jr. Day
        _nth_weekday(y, 2, 0, 3),   # Washington's Birthday
        _last_weekday(y, 5, 0),     # Memorial Day
        _nth_weekday(y, 9, 0, 1),   # Labor Day
        _nth_weekday(y, 10, 0, 2),  # Columbus Day
        _nth_weekday(y, 11, 3, 4),  # Thanksgiving Day
    }
    return out


def is_business_day(d: date) -> bool:
    return d.weekday() < 5 and d not in federal_holidays(d.year)


def add_business_days(d: date, n: int) -> date:
    while n > 0:
        d += timedelta(days=1)
        if is_business_day(d):
            n -= 1
    return d


@dataclass
class GeneratorConfig:
    n_workers: int = 12
    h1b_share: float = 0.75
    violation_rate: float = 0.25    # of decidable pairs
    near_miss_share: float = 0.25   # of decidable pairs
    withhold_export: float = 0.4    # chance each of i9 / payroll / actual-wage export is withheld
    as_of: date = date(2026, 6, 29)
    decoys: bool = False            # v3: adjacent-but-insufficient roster columns (see docstring)


class FirmGenerator:
    def __init__(self, rulebook: Rulebook, config: GeneratorConfig | None = None):
        self.rb = rulebook
        self.cfg = config or GeneratorConfig()
        known = rulebook.by_id()
        missing = [r for r in RENDERED if r not in known]
        if missing:
            raise ValueError(f"rulebook lacks rendered rules {missing}")
        self.rules = {r: known[r] for r in RENDERED}

    def generate(self, seed: int, out_dir: Path) -> Firm:
        rng = random.Random(seed)
        cfg = self.cfg
        out_dir.mkdir(parents=True, exist_ok=True)
        withheld = {e for e in ("i9", "payroll", "actual_wage") if rng.random() < cfg.withhold_export}

        workers = self._make_workers(rng)
        lcas = self._make_lcas(rng, workers)

        entities = [Entity(w["id"], "worker", w["name"]) for w in workers]
        entities += [Entity(l["case"], "lca", f"LCA {l['case']}") for l in lcas]

        pairs: list[Pair] = []
        labels: list[Label] = []

        def decide(rule: str) -> tuple[Verdict, str, bool]:
            if any(src in withheld for src in NEEDS[rule]):
                return Verdict.NEEDS_EVIDENCE, "withheld_evidence", False
            roll = rng.random()
            if roll < cfg.violation_rate:
                return Verdict.FAIL, "planted_violation", False
            if roll < cfg.violation_rate + cfg.near_miss_share:
                return Verdict.PASS, "planted_control", True
            return Verdict.PASS, "planted_control", False

        def emit(rule: str, ent_id: str, v: Verdict, basis: str, near: bool) -> None:
            pair = Pair.make(rule, ent_id)
            pairs.append(pair)
            labels.append(Label(
                pair_id=pair.pair_id, verdict=v, basis=basis,
                severity=self._severity(v),
                evidence_fields=self.rules[rule].evidence_required,
                note="near-miss control" if near else "",
            ))

        for w in workers:
            # Section 1: offer accepted, then signed on/before day 1.
            v, b, near = decide(R_S1)
            start = w["start"]
            w["offer"] = start - timedelta(days=rng.randint(14, 45))
            if v is Verdict.FAIL:
                w["s1"] = start + timedelta(days=rng.randint(1, 10))
            elif near:
                w["s1"] = start
            else:
                w["s1"] = start - timedelta(days=rng.randint(1, 7))
            emit(R_S1, w["id"], v, b, near)

            # Section 2: within 3 business days after day 1.
            v, b, near = decide(R_S2)
            if v is Verdict.FAIL:
                w["s2"] = add_business_days(start, rng.randint(4, 12))
            elif near:
                w["s2"] = add_business_days(start, 3)
            else:
                w["s2"] = add_business_days(start, rng.randint(0, 2))
            emit(R_S2, w["id"], v, b, near)

            # The employee signs Section 1 before the employer completes Section
            # 2. A late Section 1 must still precede Section 2 in the record.
            if w["s1"] > w["s2"]:
                if w["s2"] == start:  # an early Section 2 on day 0 moves to day 1
                    w["s2"] = add_business_days(start, 1)
                w["s1"] = start + timedelta(days=rng.randint(1, (w["s2"] - start).days))

            # Reverification: only workers whose prior authorization expired.
            if w["visa"] == "H-1B":
                v, b, near = decide(R_RV)
                exp = w["auth_expiry"]
                if v is Verdict.FAIL:
                    w["suppb"] = exp + timedelta(days=rng.randint(1, 45))
                elif near:
                    w["suppb"] = exp
                else:
                    w["suppb"] = exp - timedelta(days=rng.randint(1, 60))
                emit(R_RV, w["id"], v, b, near)

        by_worker = {w["id"]: w for w in workers}
        for l in lcas:
            v, b, near = decide(R_WG)
            required = max(l["pw"], l["actual"])
            if v is Verdict.FAIL:
                pay = required - 1_200 * rng.randint(1, 10)
            elif near:
                pay = required
            else:
                pay = required + 1_200 * rng.randint(1, 15)
            by_worker[l["worker"]]["annual"] = pay
            emit(R_WG, l["case"], v, b, near)

        if cfg.decoys:
            self._add_decoys(random.Random(f"decoy-{seed}"), workers)
        sources = self._write_sources(out_dir, workers, lcas, withheld)
        return Firm(
            firm_id=f"synthetic-{seed:06d}",
            name=f"Synthetic Robotics {seed:04d}, Inc.",
            as_of=cfg.as_of.isoformat(),
            sources=sources,
            entities=entities,
            pairs=pairs,
            labels=labels,
            provenance={
                "seed": seed,
                "generator": "v3-decoys" if cfg.decoys else "v2",
                "withheld_exports": sorted(withheld),
                "config": {
                    "n_workers": cfg.n_workers, "violation_rate": cfg.violation_rate,
                    "near_miss_share": cfg.near_miss_share,
                    "withhold_export": cfg.withhold_export, "as_of": cfg.as_of.isoformat(),
                    **({"decoys": True} if cfg.decoys else {}),
                },
                "rulebook_version": self.rb.version,
                "synthetic": True,
                "contains_real_personal_data": False,
            },
        )

    # ---------- construction ----------

    def _make_workers(self, rng: random.Random) -> list[dict]:
        n = self.cfg.n_workers
        n_h1b = max(1, round(n * self.cfg.h1b_share))
        out = []
        for i in range(n):
            soc, title, level, pw, actual = rng.choice(ROLES)
            city, st, msa = rng.choice(CITIES)
            start = self.cfg.as_of - timedelta(days=rng.randint(150, 1800))
            while not is_business_day(start):
                start += timedelta(days=1)
            w = {
                "id": f"SYN-{1001 + i}",
                "first": rng.choice(GIVEN), "last": rng.choice(FAMILY),
                "visa": "H-1B" if i < n_h1b else "US Citizen",
                "soc": soc, "title": title, "level": level, "pw": pw, "actual": actual,
                "city": city, "state": st, "msa": msa, "start": start,
                "annual": max(pw, actual) + 1_200 * rng.randint(1, 15),
                "auth_expiry": None, "suppb": None,
            }
            if w["visa"] == "H-1B":
                # Prior H-1B validity ended after hire and before the evaluation date.
                lo = max(30, (self.cfg.as_of - start).days - 1400)
                w["auth_expiry"] = self.cfg.as_of - timedelta(days=rng.randint(lo, max(lo, (self.cfg.as_of - start).days - 60)))
            w["name"] = f"{w['first']} {w['last']}"
            out.append(w)
        return out

    def _add_decoys(self, rng: random.Random, workers: list[dict]) -> None:
        for w in workers:
            w["decoy"] = {
                "i9Status": "Complete",
                "onboardingCompletedDate": (w["start"] - timedelta(days=rng.randint(0, 6))).isoformat(),
                "workAuthValidThrough": ((self.cfg.as_of + timedelta(days=rng.randint(90, 1000))).isoformat()
                                         if w["auth_expiry"] else ""),
                "annualBaseSalary": max(w["pw"], w["actual"]) if w["visa"] == "H-1B" else w["annual"],
                "payBandMidpoint": w["actual"] - 1_200 * rng.randint(3, 8),
            }

    def _make_lcas(self, rng: random.Random, workers: list[dict]) -> list[dict]:
        out = []
        for i, w in enumerate(x for x in workers if x["visa"] == "H-1B"):
            begin = self.cfg.as_of - timedelta(days=rng.randint(90, 700))
            out.append({
                "case": f"I-200-{25000 + i}-{100001 + i}", "worker": w["id"], "beneficiary": w["name"],
                "soc": w["soc"], "title": w["title"], "level": w["level"],
                "pw": w["pw"], "actual": w["actual"], "offered": max(w["pw"], w["actual"]),
                "city": w["city"], "state": w["state"], "msa": w["msa"],
                "begin": begin, "end": begin + timedelta(days=3 * 365 - 1),
            })
        return out

    def _write_sources(self, out_dir: Path, workers: list[dict], lcas: list[dict],
                       withheld: set[str]) -> dict[str, Path]:
        files: dict[str, Path] = {}

        p = out_dir / "hris_roster_export.csv"
        with p.open("w", newline="") as f:
            wr = csv.writer(f)
            decoy_cols = list(workers[0]["decoy"]) if "decoy" in workers[0] else []
            wr.writerow(["employeeNumber", "firstName", "lastName", "visaType", "jobTitle",
                         "city", "state", "hireDate", "employmentStatus", "terminationDate",
                         *decoy_cols])
            for w in workers:
                wr.writerow([w["id"], w["first"], w["last"], w["visa"], w["title"], w["city"],
                             w["state"], w["start"].isoformat(), "Active", "",
                             *(w["decoy"][c] for c in decoy_cols)])
        files["hris_roster_export"] = Path(p.name)

        p = out_dir / "lca_export.csv"
        with p.open("w", newline="") as f:
            wr = csv.writer(f)
            wr.writerow(["CASE_NUMBER", "EMPLOYEE_NUMBER", "BENEFICIARY", "SOC_CODE", "JOB_TITLE",
                         "PW_WAGE_LEVEL", "PREVAILING_WAGE", "PW_UNIT_OF_PAY", "WAGE_RATE_OF_PAY_FROM",
                         "WAGE_UNIT_OF_PAY", "FULL_TIME_POSITION", "WORKSITE_CITY", "WORKSITE_STATE",
                         "AREA_OF_EMPLOYMENT", "BEGIN_DATE", "END_DATE"])
            for l in lcas:
                wr.writerow([l["case"], l["worker"], l["beneficiary"], l["soc"], l["title"], l["level"],
                             l["pw"], "Year", l["offered"], "Year", "Y", l["city"], l["state"], l["msa"],
                             l["begin"].isoformat(), l["end"].isoformat()])
        files["lca_export"] = Path(p.name)

        if "i9" not in withheld:
            p = out_dir / "i9_record_export.csv"
            with p.open("w", newline="") as f:
                wr = csv.writer(f)
                wr.writerow(["employeeNumber", "offerAcceptedDate", "firstDayOfEmployment",
                             "section1Signed", "section1SignDate", "section2EmployerSignDate",
                             "workAuthorizationExpiry", "supplementBReverificationDate",
                             "supplementBDocumentType"])
                for w in workers:
                    wr.writerow([w["id"], w["offer"].isoformat(), w["start"].isoformat(), "Y",
                                 w["s1"].isoformat(), w["s2"].isoformat(),
                                 w["auth_expiry"].isoformat() if w["auth_expiry"] else "",
                                 w["suppb"].isoformat() if w["suppb"] else "",
                                 "Form I-797A Approval Notice with Form I-94" if w["suppb"] else ""])
            files["i9_record_export"] = Path(p.name)

        if "payroll" not in withheld:
            p = out_dir / "payroll_register.csv"
            with p.open("w", newline="") as f:
                wr = csv.writer(f)
                wr.writerow(["employeeNumber", "payPeriodStart", "payPeriodEnd", "payDate",
                             "payFrequency", "fullOrPartTime", "regularHours", "grossPay"])
                periods = [(date(2026, m, 1), date(2026, m, 15)) for m in (4, 5, 6)]
                periods += [(date(2026, m, 16), (date(2026, m + 1, 1) - timedelta(days=1))) for m in (4, 5, 6)]
                # Only periods paid on or before the evaluation date exist.
                periods = [(a, b) for a, b in periods if b <= self.cfg.as_of]
                for w in workers:
                    for a, b in sorted(periods):
                        wr.writerow([w["id"], a.isoformat(), b.isoformat(), b.isoformat(),
                                     "Semimonthly", "FT", 86.67, w["annual"] // 24])
            files["payroll_register"] = Path(p.name)

        if "actual_wage" not in withheld:
            p = out_dir / "actual_wage_system.csv"
            with p.open("w", newline="") as f:
                wr = csv.writer(f)
                wr.writerow(["SOC_CODE", "JOB_TITLE", "ACTUAL_WAGE_FOR_SIMILARLY_EMPLOYED_ANNUAL",
                             "BASIS"])
                for soc, title, _lvl, _pw, actual in ROLES:
                    wr.writerow([soc, title, actual, "Employer actual wage system: rate paid to "
                                 "workers with similar experience and qualifications in this role"])
            files["actual_wage_system"] = Path(p.name)

        return files

    def _severity(self, verdict: Verdict) -> Severity | None:
        if verdict is Verdict.NEEDS_EVIDENCE:
            return Severity.MEDIUM
        if verdict is Verdict.FAIL:
            return Severity.HIGH
        return None
