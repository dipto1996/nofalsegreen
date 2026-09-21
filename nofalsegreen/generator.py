"""Seeded firm generator.

Produces synthetic employers whose ground truth is fixed BY CONSTRUCTION: the
generator decides, per (obligation, entity) pair, whether to
  - plant a violation      -> label FAIL
  - plant a conforming case -> label PASS
  - withhold a required input -> label NEEDS_EVIDENCE
and only then writes the source CSVs consistent with that decision. Labels are
therefore not annotations of generated data; the data is a rendering of the
labels. There is no annotator disagreement to measure because there is no
annotation step.

Every firm is reproducible from (seed, config). Nothing is sampled from a real
employer, and no real person's data is used.
"""

from __future__ import annotations

import csv
import random
from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path

from .rulebook import Rulebook
from .schema import Entity, Firm, Label, Pair, Severity, Verdict

# Name pools are deliberately generic and combinatorial. They exist to make
# joins legible in a CSV, not to depict anyone.
GIVEN = ["Amara", "Bao", "Camila", "Dmitri", "Elena", "Farid", "Grace", "Hana",
         "Ibrahim", "Jonas", "Keiko", "Lars", "Mira", "Nadia", "Omar", "Priya",
         "Qing", "Rosa", "Samir", "Tomas", "Uma", "Viktor", "Wen", "Yara", "Zane"]
FAMILY = ["Abara", "Bianchi", "Costa", "Duarte", "Eriksen", "Fontaine", "Gupta",
          "Haddad", "Ivanov", "Jansen", "Kovac", "Lindqvist", "Mwangi", "Nakamura",
          "Okafor", "Petrov", "Quintero", "Rahman", "Santos", "Tanaka", "Ueda",
          "Volkov", "Whitfield", "Xu", "Yilmaz", "Zhao"]
SOC = [("15-1252", "Software Developers", False), ("17-2199", "Engineers, All Other", False),
       ("15-1211", "Computer Systems Analysts", False), ("11-9041", "Architectural and Engineering Managers", True)]
CITIES = [("Austin", "TX", "78701", "Austin-Round Rock, TX"),
          ("Boston", "MA", "02109", "Boston-Cambridge-Newton, MA-NH"),
          ("Denver", "CO", "80202", "Denver-Aurora-Lakewood, CO"),
          ("Raleigh", "NC", "27601", "Raleigh-Cary, NC")]


@dataclass
class GeneratorConfig:
    """Knobs that control the difficulty and shape of a generated firm."""

    n_workers: int = 12
    h1b_share: float = 0.75
    violation_rate: float = 0.12       # share of applicable pairs that get a planted breach
    withhold_rate: float = 0.45        # share that get a required input withheld
    n_worksites: int = 2
    as_of: date = date(2026, 6, 29)
    # A near-miss is a conforming case placed just inside the legal boundary
    # (e.g. I-9 Section 2 on business day 3 of 3). It tests whether a system
    # flags on proximity rather than on the rule.
    near_miss_share: float = 0.25


class FirmGenerator:
    def __init__(self, rulebook: Rulebook, config: GeneratorConfig | None = None):
        self.rb = rulebook
        self.cfg = config or GeneratorConfig()

    # ---------- public ----------

    def generate(self, seed: int, out_dir: Path) -> Firm:
        rng = random.Random(seed)
        cfg = self.cfg
        out_dir.mkdir(parents=True, exist_ok=True)

        workers = self._make_workers(rng)
        worksites = self._make_worksites(rng)
        lcas = self._make_lcas(rng, workers, worksites)

        entities: list[Entity] = []
        entities += [Entity(w["employee_number"], "worker", w["display_name"]) for w in workers]
        entities += [Entity(l["case_number"], "lca", f"LCA {l['case_number']}") for l in lcas]
        entities += [Entity(s["id"], "worksite", s["label"]) for s in worksites]
        entities.append(Entity("EMPLOYER", "employer", "employer scope"))

        pairs: list[Pair] = []
        labels: list[Label] = []

        # The decision pass. For every applicable (rule, entity) pair, choose a
        # disposition FIRST; the writers below then render data that matches.
        for ob in self.rb.obligations:
            for ent in entities:
                if ent.entity_type != ob.applies_to:
                    continue
                pair = Pair.make(ob.rule_id, ent.entity_id)
                roll = rng.random()
                if not ob.evidence_required:
                    # Nothing to withhold: structurally unmonitored from exports.
                    verdict, basis = Verdict.UNMONITORED, "not_applicable"
                elif roll < cfg.violation_rate:
                    verdict, basis = Verdict.FAIL, "planted_violation"
                elif roll < cfg.violation_rate + cfg.withhold_rate:
                    verdict, basis = Verdict.NEEDS_EVIDENCE, "withheld_evidence"
                else:
                    verdict, basis = Verdict.PASS, "planted_control"
                pairs.append(pair)
                labels.append(
                    Label(
                        pair_id=pair.pair_id,
                        verdict=verdict,
                        basis=basis,
                        severity=self._severity(ob.rule_id, verdict, rng),
                        evidence_fields=ob.evidence_required,
                        note=(
                            "near-miss control" if basis == "planted_control"
                            and roll > 1 - cfg.near_miss_share else ""
                        ),
                    )
                )

        self._apply_dispositions(workers, lcas, labels, rng)
        sources = self._write_sources(out_dir, workers, lcas, worksites)

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
                "config": {
                    "n_workers": cfg.n_workers,
                    "violation_rate": cfg.violation_rate,
                    "withhold_rate": cfg.withhold_rate,
                    "near_miss_share": cfg.near_miss_share,
                    "as_of": cfg.as_of.isoformat(),
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
            soc, title, is_mgr = rng.choice(SOC)
            city, st, zipc, msa = rng.choice(CITIES[: self.cfg.n_worksites])
            hire = self.cfg.as_of - timedelta(days=rng.randint(120, 1800))
            out.append({
                "employee_number": f"SYN-{1001 + i}",
                "first_name": rng.choice(GIVEN),
                "last_name": rng.choice(FAMILY),
                "display_name": "",  # filled below
                "visa_type": "H-1B" if i < n_h1b else "US Citizen",
                "job_title": title,
                "soc_code": soc,
                "is_manager_title": is_mgr,
                "city": city, "state": st, "zip": zipc, "msa": msa,
                "hire_date": hire,
                "pay_rate": rng.choice([96000, 118000, 134000, 142000, 151000, 178000]),
                "i9_section2_date": None,
                "reverification_due": None,
                "salary_override": None,
            })
        for w in out:
            w["display_name"] = f"{w['first_name']} {w['last_name']}"
        return out

    def _make_worksites(self, rng: random.Random) -> list[dict]:
        return [
            {"id": f"WS-{i+1}", "label": f"{c[0]} - {'HQ' if i == 0 else 'Lab'}",
             "city": c[0], "state": c[1], "zip": c[2], "msa": c[3]}
            for i, c in enumerate(CITIES[: self.cfg.n_worksites])
        ]

    def _make_lcas(self, rng: random.Random, workers: list[dict], worksites: list[dict]) -> list[dict]:
        out = []
        for i, w in enumerate(x for x in workers if x["visa_type"] == "H-1B"):
            ws = rng.choice(worksites)
            pw = rng.choice([118000, 132000, 143000, 145000])
            out.append({
                "case_number": f"I-200-{25000 + i}-{100001 + i}",
                "employee_number": w["employee_number"],
                "beneficiary": w["display_name"],
                "soc_code": w["soc_code"],
                "wage_rate": w["pay_rate"],
                "prevailing_wage": pw,
                "worksite_city": ws["city"],
                "worksite_state": ws["state"],
                "msa": ws["msa"],
                "begin_date": self.cfg.as_of - timedelta(days=rng.randint(200, 900)),
                "end_date": self.cfg.as_of + timedelta(days=rng.randint(30, 700)),
            })
        return out

    def _apply_dispositions(
        self, workers: list[dict], lcas: list[dict], labels: list[Label], rng: random.Random
    ) -> None:
        """Render the chosen labels into the underlying records.

        Only the mechanisms with a concrete data expression are rendered here;
        the remainder are expressed by withholding the source column entirely
        (see `_write_sources`), which is what produces NEEDS_EVIDENCE.
        """
        by_worker = {w["employee_number"]: w for w in workers}
        by_lca = {l["case_number"]: l for l in lcas}

        for lab in labels:
            rule_id, ent_id = lab.pair_id.split("::")

            if rule_id == "i9.section2.timeliness" and ent_id in by_worker:
                w = by_worker[ent_id]
                if lab.verdict is Verdict.FAIL:
                    w["i9_section2_date"] = w["hire_date"] + timedelta(days=rng.randint(8, 20))
                elif lab.verdict is Verdict.PASS:
                    # near-miss controls land exactly on business day 3
                    offset = 3 if lab.note == "near-miss control" else rng.randint(0, 2)
                    w["i9_section2_date"] = w["hire_date"] + timedelta(days=offset)
                else:
                    w["i9_section2_date"] = None  # withheld

            elif rule_id == "lca.expiration" and ent_id in by_lca:
                l = by_lca[ent_id]
                if lab.verdict is Verdict.FAIL:
                    l["end_date"] = self.cfg.as_of + timedelta(days=rng.randint(1, 7))
                elif lab.verdict is Verdict.PASS:
                    l["end_date"] = self.cfg.as_of + timedelta(
                        days=8 if lab.note == "near-miss control" else rng.randint(90, 700)
                    )
                else:
                    l["end_date"] = None

            elif rule_id == "lca.wage.required_wage_greater_of" and ent_id in by_lca:
                l = by_lca[ent_id]
                w = by_worker.get(l["employee_number"])
                if not w:
                    continue
                floor = max(l["wage_rate"], l["prevailing_wage"])
                if lab.verdict is Verdict.FAIL:
                    # Pays the certified rate but under the prevailing wage: the
                    # exact false-pass the greater-of reading exists to catch.
                    w["salary_override"] = min(l["wage_rate"], l["prevailing_wage"]) - 1
                elif lab.verdict is Verdict.PASS:
                    w["salary_override"] = floor if lab.note == "near-miss control" else floor + rng.randint(1000, 20000)
                else:
                    w["salary_override"] = None

            elif rule_id == "h1b.material_change.soc" and ent_id in by_lca:
                l = by_lca[ent_id]
                w = by_worker.get(l["employee_number"])
                if not w:
                    continue
                if lab.verdict is Verdict.FAIL:
                    w["job_title"] = "Engineering Manager"
                    l["soc_code"] = "15-1252"  # IC code against a management title

            elif rule_id == "h1b.material_change.worksite" and ent_id in by_lca:
                l = by_lca[ent_id]
                w = by_worker.get(l["employee_number"])
                if not w:
                    continue
                if lab.verdict is Verdict.FAIL:
                    other = [c for c in CITIES[: self.cfg.n_worksites] if c[0] != l["worksite_city"]]
                    if other:
                        w["city"], w["state"], w["zip"], w["msa"] = rng.choice(other)

    def _write_sources(
        self, out_dir: Path, workers: list[dict], lcas: list[dict], worksites: list[dict]
    ) -> dict[str, Path]:
        roster = out_dir / "hris_roster_export.csv"
        with roster.open("w", newline="") as f:
            wr = csv.writer(f)
            wr.writerow(["employeeNumber", "firstName", "lastName", "displayName", "visaType",
                         "jobTitle", "city", "state", "zipcode", "hireDate", "payRate",
                         "payType", "payFrequency", "location"])
            for w in workers:
                site = next((s["label"] for s in worksites if s["city"] == w["city"]), worksites[0]["label"])
                wr.writerow([w["employee_number"], w["first_name"], w["last_name"], w["display_name"],
                             w["visa_type"], w["job_title"], w["city"], w["state"], w["zip"],
                             w["hire_date"].isoformat(),
                             w["salary_override"] if w["salary_override"] is not None else w["pay_rate"],
                             "Salary", "Annually", site])

        i9 = out_dir / "i9_record_export.csv"
        with i9.open("w", newline="") as f:
            wr = csv.writer(f)
            wr.writerow(["employeeNumber", "startDate", "section1SignDate", "section2CompletedDate"])
            for w in workers:
                s2 = w["i9_section2_date"]
                wr.writerow([w["employee_number"], w["hire_date"].isoformat(),
                             w["hire_date"].isoformat(), s2.isoformat() if s2 else ""])

        lca = out_dir / "lca_export.csv"
        with lca.open("w", newline="") as f:
            wr = csv.writer(f)
            wr.writerow(["CASE_NUMBER", "EMPLOYEE_NUMBER", "BENEFICIARY", "SOC_CODE", "WAGE_RATE",
                         "PREVAILING_WAGE", "WORKSITE_CITY", "WORKSITE_STATE", "MSA",
                         "BEGIN_DATE", "END_DATE"])
            for l in lcas:
                wr.writerow([l["case_number"], l["employee_number"], l["beneficiary"], l["soc_code"],
                             l["wage_rate"], l["prevailing_wage"], l["worksite_city"],
                             l["worksite_state"], l["msa"], l["begin_date"].isoformat(),
                             l["end_date"].isoformat() if l["end_date"] else ""])

        # Relative names keep firm.json portable and byte-identical across
        # output directories, so two seeds can be diffed meaningfully.
        return {
            "hris_roster_export": Path(roster.name),
            "i9_record_export": Path(i9.name),
            "lca_export": Path(lca.name),
        }

    def _severity(self, rule_id: str, verdict: Verdict, rng: random.Random) -> Severity | None:
        if verdict is Verdict.NEEDS_EVIDENCE:
            return Severity.MEDIUM  # an unassessed obligation is never "urgent"
        if verdict is Verdict.FAIL:
            return Severity.URGENT if "expir" in rule_id or "deadline" in rule_id else Severity.HIGH
        return None
