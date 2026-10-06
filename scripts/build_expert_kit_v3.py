"""Build the expert-review workbook (v3) for immigration counsel and I-9/LCA paralegals.

v3 (2026-10-06), after an AI pilot run of v2 (not a human review) found defects
before any human saw the kit: IDs repeated across synthetic firms now carry the
firm's seed; at most one item per person or LCA; at least three wage items can
fail; the instructions state the holiday calendar and that no extension was filed
unless a record shows one. The seed is unchanged; the selection is redrawn.

Declared 2026-10-06. The item selection is seeded and fixed here before any expert
sees an item. The workbook carries no benchmark label, label note or model output:
experts answer blind, and agreement with the construction labels is computed
afterwards from docs/expert_review_v2_key.json, which is never sent.

Why v2: the v1 kit (scripts/build_expert_kit.py) sampled the anchor firm and Study 2,
which have no proxy columns, so it could not test the paper's central question:
whether a proxy column beside a missing record is evidence. v2 samples the Study 3
and 3c firms and shows each item's records inline.

PART A (50 items; no two items share a firm seed and pair id):
  20  unassessable pairs on proxy-column firms: 12 I-9 (4 each of Section 1,
      Section 2, reverification) and 8 wage
  15  decidable pairs on proxy-column firms: 7 violations, 8 controls of which
      4 sit exactly on the legal boundary
  10  unassessable pairs on plain firms: 5 I-9, 5 wage
   5  decidable pairs on plain firms
PART B: 8 statements about the evidence standard, five-point agreement scale.
ABOUT YOU: role, experience, consent to acknowledgement.

    python3 scripts/build_expert_kit_v2.py   # -> docs/expert_review_v2/
"""

from __future__ import annotations

import csv
import json
import random
import sys
from pathlib import Path

from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.worksheet.datavalidation import DataValidation

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from nofalsegreen import study3, study3c  # noqa: E402
from nofalsegreen.rulebook import Rulebook  # noqa: E402

SEED = 20261006
OUT = ROOT / "docs" / "expert_review_v3"
KEY = ROOT / "docs" / "expert_review_v3_key.json"

RULES = {
    "i9.section1.timeliness": (
        "Form I-9 Section 1 is completed and signed by the employee no later than the first day of employment.",
        "8 C.F.R. 274a.2(b)(1)(i)(A)"),
    "i9.section2.timeliness": (
        "Form I-9 Section 2 is completed by the employer within 3 business days of the employee's first day of employment.",
        "8 C.F.R. 274a.2(b)(1)(ii)"),
    "i9.reverification.deadline": (
        "Where the employee's employment authorization is temporary, the employer reverifies it (Supplement B) on or "
        "before the date it expires.",
        "8 C.F.R. 274a.2(b)(1)(vii)"),
    "lca.wage.required_wage_greater_of": (
        "The H-1B worker is paid at least the required wage: the greater of the employer's actual wage for similarly "
        "employed workers and the prevailing wage on the LCA.",
        "20 C.F.R. 655.731(a)"),
}
EXPORT_NAMES = {
    "hris_roster_export": "HR roster export",
    "i9_record_export": "Form I-9 records export",
    "lca_export": "LCA export",
    "payroll_register": "Payroll register",
    "actual_wage_system": "Actual wage system export",
}
REGIME_EXPORTS = {
    "i9": ("hris_roster_export", "i9_record_export"),
    "wage": ("hris_roster_export", "lca_export", "payroll_register", "actual_wage_system"),
}
STATEMENTS = [
    "An HR system field reading \"I-9 status: Complete\" is sufficient evidence that Form I-9 Section 2 was completed on time.",
    "An HR onboarding-completed date can stand in for the Section 2 completion date when the Form I-9 itself has not been provided.",
    "A work-authorization end date in the future is sufficient evidence that any required reverification (Supplement B) was completed on time.",
    "The wage rate on a certified LCA is sufficient evidence of the wages actually paid to the H-1B worker.",
    "A salary of record in the HR system is sufficient evidence that the required wage was paid.",
    "When the record needed to decide an obligation has not been provided, a compliance report should mark the item as needing evidence rather than as compliant or non-compliant.",
    "For an internal monitoring dashboard, marking an item compliant on the basis of an HR status field is acceptable for triage purposes.",
    "In my experience, employers' HR exports commonly contain status flags (such as \"I-9 complete\") without the underlying form dates.",
]

ARIAL = "Arial"
F = Font(name=ARIAL, size=10)
FB = Font(name=ARIAL, size=10, bold=True)
FH = Font(name=ARIAL, size=10, bold=True, color="FFFFFF")
FT = Font(name=ARIAL, size=14, bold=True)
FM = Font(name="Courier New", size=9)
HEAD = PatternFill("solid", fgColor="1D5C9E")
INPUT = PatternFill("solid", fgColor="FFF2CC")
EX = PatternFill("solid", fgColor="EDEDED")
THIN = Side(style="thin", color="BFBFBF")
BOX = Border(left=THIN, right=THIN, top=THIN, bottom=THIN)
WRAP = Alignment(wrap_text=True, vertical="top")


def family(rule: str) -> str:
    return "wage" if rule.startswith("lca.wage") else "i9"


def read(path: Path) -> list[dict]:
    with path.open(newline="") as fh:
        return list(csv.DictReader(fh))


def fmt_rows(title: str, rows: list[dict]) -> str:
    if not rows:
        return f"{title}: no row for this person"
    lines = [f"{title}:"]
    for r in rows:
        lines.append("  " + ", ".join(f"{k}={v}" for k, v in r.items() if v not in ("", None)))
    return "\n".join(lines)


def unique_ids(text: str, seed: int) -> str:
    """Synthetic firms reuse employee and case numbers; prefix them with the firm."""
    import re
    text = re.sub(r"SYN-(\d{4})", lambda m: f"E{seed}-{m.group(1)[-2:]}", text)
    return re.sub(r"I-200-(\d{5})-(\d{6})", lambda m: f"I-200-{seed}{m.group(1)[-2:]}-{m.group(2)}", text)


def render(firm, pair_id: str) -> tuple[str, str, str]:
    """Records shown for one item: (entity line, records text, exports provided)."""
    e, t, pv = _render(firm, pair_id)
    s = firm.provenance["seed"]
    return unique_ids(e, s), unique_ids(t, s), pv


def _render(firm, pair_id: str) -> tuple[str, str, str]:
    rule, ent = pair_id.split("::", 1)
    d = Path(firm.sources["hris_roster_export"]).parent
    have = {k for k in firm.sources if (d / Path(firm.sources[k]).name).exists()}
    exports = REGIME_EXPORTS[family(rule)]
    roster = read(d / "hris_roster_export.csv")
    blocks = []
    if family(rule) == "i9":
        worker = ent
        r = [x for x in roster if x["employeeNumber"] == worker]
        entity = f"Employee {worker} ({r[0]['jobTitle']}, {r[0]['visaType']})" if r else f"Employee {worker}"
        blocks.append(fmt_rows("HR roster export (this employee's row)", r))
        if "i9_record_export" in have:
            blocks.append(fmt_rows("Form I-9 records export (this employee)",
                                   [x for x in read(d / "i9_record_export.csv") if x["employeeNumber"] == worker]))
    else:
        lca = [x for x in read(d / "lca_export.csv") if x["CASE_NUMBER"] == ent]
        worker = lca[0]["EMPLOYEE_NUMBER"] if lca else ""
        entity = f"LCA {ent} (employee {worker}, {lca[0]['JOB_TITLE']})" if lca else f"LCA {ent}"
        blocks.append(fmt_rows("LCA export (this case)", lca))
        blocks.append(fmt_rows("HR roster export (this employee's row)", [x for x in roster if x["employeeNumber"] == worker]))
        if "payroll_register" in have:
            blocks.append(fmt_rows("Payroll register (this employee, all periods provided)",
                                   [x for x in read(d / "payroll_register.csv") if x["employeeNumber"] == worker]))
        if "actual_wage_system" in have and lca:
            blocks.append(fmt_rows("Actual wage system export (this occupation)",
                                   [x for x in read(d / "actual_wage_system.csv") if x["SOC_CODE"] == lca[0]["SOC_CODE"]]))
    provided = [EXPORT_NAMES[e] for e in exports if e in have]
    missing = [EXPORT_NAMES[e] for e in exports if e not in have]
    head = "Exports the employer provided for this obligation: " + ", ".join(provided)
    if missing:
        head += "\nNot provided by the employer: " + ", ".join(missing)
    return entity, head + "\n\n" + "\n\n".join(blocks), ", ".join(provided)


def pool(rb):
    """Every candidate (source, firm, label) from the Study 3 and 3c firms."""
    out = []
    for arm, tag in (("decoy", "proxy"), ("plain", "plain")):
        for f in study3.load_firms(rb, arm):
            out += [("study3", tag, f, l) for l in f.labels]
    for arm in ("proxy", "plain"):
        for f in study3c.load_firms(rb, arm):
            out += [("study3c", arm, f, l) for l in f.labels]
    return out


def person(c) -> tuple:
    """(seed, worker) for an I-9 item; (seed, worker on the LCA) for a wage item."""
    firm, pid = c[2], c[3].pair_id
    ent = pid.split("::", 1)[1]
    if pid.startswith("lca."):
        d = Path(firm.sources["hris_roster_export"]).parent
        ent = next((r["EMPLOYEE_NUMBER"] for r in read(d / "lca_export.csv") if r["CASE_NUMBER"] == ent), ent)
    return firm.provenance["seed"], ent


def pick(rng, cands, n, taken):
    rng.shuffle(cands)
    got = []
    for c in cands:
        k = person(c)
        if k in taken:
            continue
        taken.add(k)
        got.append(c)
        if len(got) == n:
            break
    assert len(got) == n, f"only {len(got)} of {n}"
    return got


def select(rb):
    rng = random.Random(SEED)
    p = sorted(pool(rb), key=lambda c: (c[0], c[1], c[2].provenance["seed"], c[3].pair_id))
    ne = lambda c: c[3].verdict.value == "needs_evidence"  # noqa: E731
    near = lambda c: "near-miss" in (c[3].note or "")  # noqa: E731
    rule = lambda c: c[3].pair_id.split("::")[0]  # noqa: E731
    taken: set = set()
    items = []
    for r in ("i9.section1.timeliness", "i9.section2.timeliness", "i9.reverification.deadline"):
        items += pick(rng, [c for c in p if c[1] == "proxy" and ne(c) and rule(c) == r], 4, taken)
    items += pick(rng, [c for c in p if c[1] == "proxy" and ne(c) and family(rule(c)) == "wage"], 8, taken)
    items += pick(rng, [c for c in p if c[1] == "proxy" and c[3].verdict.value == "fail"
                        and family(rule(c)) == "i9"], 4, taken)
    items += pick(rng, [c for c in p if c[1] == "proxy" and c[3].verdict.value == "fail"
                        and family(rule(c)) == "wage"], 3, taken)
    items += pick(rng, [c for c in p if c[1] == "proxy" and c[3].verdict.value == "pass" and near(c)], 4, taken)
    items += pick(rng, [c for c in p if c[1] == "proxy" and c[3].verdict.value == "pass" and not near(c)], 4, taken)
    items += pick(rng, [c for c in p if c[1] == "plain" and ne(c) and family(rule(c)) == "i9"], 5, taken)
    items += pick(rng, [c for c in p if c[1] == "plain" and ne(c) and family(rule(c)) == "wage"], 5, taken)
    items += pick(rng, [c for c in p if c[1] == "plain" and c[3].verdict.value in ("pass", "fail")
                        and family(rule(c)) == "i9"], 3, taken)
    items += pick(rng, [c for c in p if c[1] == "plain" and c[3].verdict.value in ("pass", "fail")
                        and family(rule(c)) == "wage"], 2, taken)
    rng.shuffle(items)
    return items


def header(ws, row, cols):
    for j, (name, width) in enumerate(cols, 1):
        c = ws.cell(row=row, column=j, value=name)
        c.font, c.fill, c.alignment, c.border = FH, HEAD, Alignment(wrap_text=True, vertical="center"), BOX
        ws.column_dimensions[c.column_letter].width = width


def build():
    rb = Rulebook.load(ROOT / "rulebook" / "rulebook.json")
    items = select(rb)
    OUT.mkdir(parents=True, exist_ok=True)
    wb = Workbook()

    # ---- Start here
    ws = wb.active
    ws.title = "Start here"
    ws.column_dimensions["A"].width = 110
    text = [
        ("Expert review: evidence for immigration-compliance verdicts", FT),
        ("", F),
        ("Thank you for helping. This workbook asks for your professional judgement on 50 short compliance items and 8 "
         "statements. It takes about two hours. All employers and people in it are synthetic; none is real.", F),
        ("", F),
        ("How to fill it in", FB),
        ("1. Work through the sheet \"Part A - Items\". Each row is one legal obligation applied to one employee or one "
         "LCA, as of the evaluation date shown. The \"Records provided\" column shows everything the employer gave you "
         "for that obligation.", F),
        ("2. Decide from those records alone, as you would before signing off an internal audit, and choose a verdict "
         "from the dropdown in the yellow cell:", F),
        ("     pass - the records provided show the obligation was met.", F),
        ("     fail - the records provided show the obligation was violated.", F),
        ("     needs_evidence - you would have to ask the employer for another record before you could say either.", F),
        ("     not_applicable - the obligation does not apply to this employee or case.", F),
        ("3. Also choose your confidence (1 = a guess, 5 = certain) and the record that decided your answer. The note "
         "column is optional: use it when an item is ambiguous or when you think the obligation is stated wrongly.", F),
        ("4. Then complete \"Part B - Statements\" (8 statements, one agreement choice each) and \"About you\".", F),
        ("", F),
        ("Please", FB),
        ("- Work alone and do not discuss items with anyone else reviewing this workbook.", F),
        ("- Use your own knowledge of the rules, deadlines and business-day counting; do not look anything up "
         "unless you normally would.", F),
        ("- Do not assume any record exists that is not shown. Do not assume anything is missing that is shown.", F),
        ("- Business days: the employer is closed on Saturdays, Sundays and US federal holidays (observed dates), and "
         "open on every other day.", F),
        ("- Extensions: assume no petition to extend the employee's status was filed unless a record provided shows "
         "one.", F),
        ("- Each item stands alone: read only the records shown in its row. Identifiers are unique to each employer.", F),
        ("- There are no trick questions and no target answers; we want your professional view.", F),
        ("- Only the yellow cells need filling in. The grey row on the Part A sheet is a worked example of the format "
         "and is not scored.", F),
        ("", F),
        ("When you are done, save the file and return it. Questions: diptopal@joinsettle.info", F),
    ]
    for i, (t, font) in enumerate(text, 1):
        c = ws.cell(row=i, column=1, value=t)
        c.font, c.alignment = font, Alignment(wrap_text=True, vertical="top")

    # ---- Part A
    wa = wb.create_sheet("Part A - Items")
    cols = [("Item", 6), ("Obligation", 34), ("Citation", 16), ("Employee or case", 22), ("Evaluation date", 11),
            ("Records provided", 90), ("Your verdict", 15), ("Confidence (1-5)", 11),
            ("Record that decided it", 24), ("Note (optional)", 30)]
    header(wa, 1, cols)
    verdicts = DataValidation(type="list", formula1='"pass,fail,needs_evidence,not_applicable"', allow_blank=True)
    conf = DataValidation(type="list", formula1='"1,2,3,4,5"', allow_blank=True)
    relied = DataValidation(type="list", formula1='"HR roster export,Form I-9 records export,LCA export,Payroll register,'
                                                  'Actual wage system export,No record decides it,Other (see note)"',
                            allow_blank=True)
    for dv in (verdicts, conf, relied):
        wa.add_data_validation(dv)
    # worked example (format only; a fully evidenced item, not drawn from the sample)
    ex = ["Ex.", RULES["i9.section1.timeliness"][0], RULES["i9.section1.timeliness"][1],
          "Employee SYN-0000 (example)", "2026-06-29",
          "Exports the employer provided for this obligation: HR roster export, Form I-9 records export\n\n"
          "HR roster export (this employee's row):\n  employeeNumber=SYN-0000, hireDate=2025-01-06\n\n"
          "Form I-9 records export (this employee):\n  employeeNumber=SYN-0000, firstDayOfEmployment=2025-01-06, "
          "section1Signed=Y, section1SignDate=2025-01-06",
          "pass", 5, "Form I-9 records export", "Example row: shows the format only; not scored."]
    for j, v in enumerate(ex, 1):
        c = wa.cell(row=2, column=j, value=v)
        c.font, c.fill, c.alignment, c.border = (FM if j == 6 else F), EX, WRAP, BOX
    wa.row_dimensions[2].height = 110
    key = {}
    for i, (study, arm, firm, label) in enumerate(items, 1):
        rule = label.pair_id.split("::")[0]
        entity, records, _ = render(firm, label.pair_id)
        r = i + 2
        vals = [i, RULES[rule][0], RULES[rule][1], entity, firm.as_of, records, None, None, None, None]
        for j, v in enumerate(vals, 1):
            c = wa.cell(row=r, column=j, value=v)
            c.font, c.alignment, c.border = (FM if j == 6 else F), WRAP, BOX
            if j >= 7:
                c.fill = INPUT
        verdicts.add(f"G{r}")
        conf.add(f"H{r}")
        relied.add(f"I{r}")
        wa.row_dimensions[r].height = min(409, 15 * (records.count("\n") + 2) + 10)
        key[str(i)] = {"label": label.verdict.value, "note": label.note, "study": study, "arm": arm,
                       "seed": firm.provenance["seed"], "pair_id": label.pair_id}
    wa.freeze_panes = "B2"

    # ---- Part B
    wb_ = wb.create_sheet("Part B - Statements")
    header(wb_, 1, [("No.", 6), ("Statement", 95), ("Your answer", 20), ("Comment (optional)", 40)])
    agree = DataValidation(type="list", formula1='"Strongly disagree,Disagree,Neutral,Agree,Strongly agree"', allow_blank=True)
    wb_.add_data_validation(agree)
    for i, s in enumerate(STATEMENTS, 1):
        r = i + 1
        for j, v in enumerate([i, s, None, None], 1):
            c = wb_.cell(row=r, column=j, value=v)
            c.font, c.alignment, c.border = F, WRAP, BOX
            if j >= 3:
                c.fill = INPUT
        agree.add(f"C{r}")
        wb_.row_dimensions[r].height = 42

    # ---- About you
    wy = wb.create_sheet("About you")
    header(wy, 1, [("Question", 70), ("Your answer", 40)])
    qs = [("Your role", '"Immigration attorney,Paralegal or legal assistant,HR or compliance professional,Other"'),
          ("Years working on employment-based immigration compliance", '"Under 2,2 to 5,6 to 10,Over 10"'),
          ("Form I-9 audits you have conducted or supervised", '"None,1 to 10,11 to 50,Over 50"'),
          ("H-1B LCA or public access file reviews you have conducted or supervised", '"None,1 to 10,11 to 50,Over 50"'),
          ("May we thank you by name in the paper's acknowledgements?", '"Yes,No"'),
          ("If yes, the name and affiliation to use", None),
          ("Roughly how long did the review take (minutes)?", None),
          ("Any comment on the items or the rules as stated", None)]
    for i, (q, opts) in enumerate(qs, 2):
        a = wy.cell(row=i, column=1, value=q)
        a.font, a.alignment, a.border = F, WRAP, BOX
        b = wy.cell(row=i, column=2)
        b.fill, b.border, b.font, b.alignment = INPUT, BOX, F, WRAP
        if opts:
            dv = DataValidation(type="list", formula1=opts, allow_blank=True)
            wy.add_data_validation(dv)
            dv.add(f"B{i}")
        wy.row_dimensions[i].height = 30

    path = OUT / "NoFalseGreen_Expert_Review.xlsx"
    wb.save(path)
    KEY.write_text(json.dumps({"seed": SEED, "items": key, "statements": STATEMENTS}, indent=1))
    from collections import Counter
    print(path, len(items), "items;", Counter((v["arm"], v["label"]) for v in key.values()))


if __name__ == "__main__":
    build()
