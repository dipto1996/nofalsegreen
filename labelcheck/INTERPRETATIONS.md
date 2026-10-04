# Reference checker: interpretive choices

`labelcheck/reference_checker.py` was written independently. It is based only on the firm CSV exports, the four obligation entries in `rulebook/rulebook.json`, and the primary sources cited below. Evaluation date: **2026-06-29** for every firm.

Verdict semantics:
- `pass`: the required evidence is present and shows compliance.
- `fail`: the required evidence is present and shows non-compliance.
- `needs_evidence`: an item the obligation needs is not in the exports.

Sources consulted:
- 8 CFR 274a.1 and 274a.2(b)(1)(i), (ii), (iii) and (vii), read at law.cornell.edu.
- USCIS M-274 §3.0 (Section 1) and §4.0 (Section 2), read at uscis.gov.
- 20 CFR 655.731(a) and (c), read at law.cornell.edu.
- 5 U.S.C. 6103 (federal holidays).

---

## 1. `i9.section1.timeliness` (per roster worker)

**Rule applied.** The verdict is `pass` when all of these hold:
- `section1Signed = Y`;
- `offerAcceptedDate <= section1SignDate`;
- `section1SignDate <= firstDayOfEmployment`.

| Choice | Decision | Support |
|---|---|---|
| What "hire" means | The I-9 export's `firstDayOfEmployment` | 8 CFR 274a.1(c): "hire" means "the actual commencement of employment of an employee for wages or other remuneration". |
| May Section 1 be signed on the first day? | **Yes.** Signing on the first day is timely, and the first day is inclusive. | 274a.2(b)(1)(i)(A): Section 1 is completed "at the time of hire". M-274 §3.0: "no later than the employee's first day of employment". |
| Signing before offer acceptance | `fail` | M-274 §3.0: "You may not ask an individual who has not accepted a job offer to complete Section 1." Signing on the same day as acceptance is allowed. |
| Signing after the first day | `fail`, with no grace period | Same sources. The 3-business-day window in 274a.2(b)(1)(ii) applies only to Section 2. |
| `section1Signed = N` | `fail` once the first day has passed | The attestation must be signed. |
| No I-9 export, or a required field is blank | `needs_evidence` | The required evidence is absent. |

The roster's `hireDate` is **not** used. It is an HRIS field, not the I-9 record. It matched `firstDayOfEmployment` in every firm that had both files.

## 2. `i9.section2.timeliness` (per roster worker)

**Rule applied.** The first day of employment is day 0. Section 2 is due by the 3rd business day after it. The verdict is `fail` if `section2EmployerSignDate` is later than that deadline, or earlier than `offerAcceptedDate`.

| Choice | Decision | Support |
|---|---|---|
| How to count | Day 0 is the first day. The deadline is the 3rd business day **after** it, inclusive. | 274a.2(b)(1)(ii): "within three business days of the hire". M-274 §4.0 example: "if an employee begins employment on Monday, you must ... complete Section 2 on or before Thursday of that week." |
| What a business day is | Monday to Friday, **excluding federal holidays** under 5 U.S.C. 6103(a), with weekend holidays moved to their observed weekday (Saturday to Friday, Sunday to Monday). Juneteenth counts from 2021 onward. Inauguration Day is not counted, because it applies only in the DC area. | Neither the CFR nor M-274 §4.0 defines "business day". The Monday-to-Thursday example implies weekends do not count. Excluding federal holidays follows the conventional federal meaning and the rulebook threshold. |
| Short engagement (under 3 business days) | Section 2 is due on day 1. This applies only when the roster has a `terminationDate` and the employment lasted fewer than 3 business days. | 274a.2(b)(1)(iii). In practice no roster had a termination, so it never triggered. |
| Section 2 signed before offer acceptance | `fail` | M-274 §3.0: Section 2 may be done "at any time between the date the employee accepts the job offer ... to within three business days of the hire". |
| Section 2 signed before the first day, but after acceptance | `pass` | Same M-274 §3.0 text. |

**Ambiguity: the business-day definition.** Read literally, a business day is a day the employer is open. A 7-day-a-week employer would count weekends, and a firm open on federal holidays would count those too. No export gives the employer's operating calendar, so I used Monday to Friday minus federal holidays.

How much this choice matters across the 40 firms:
- **6 verdicts change** between "weekdays only" and "weekdays minus federal holidays". Those Section 2 dates fall on the day after a deadline that a holiday pushes back: the 2021-12-31 observed New Year's Day, Labor Day 2022, and Thanksgiving 2022 and 2023. My checker marks these **pass**.
- Counting calendar days instead would change **55 verdicts**.
- **70** Section 2 dates fall exactly on the deadline day.

## 3. `i9.reverification.deadline` (per worker whose temporary authorization has expired)

**Who is in scope.** A worker gets a row only if all of these hold:
1. The roster `visaType` is not a status that is never reverified. Excluded: U.S. citizen or national, and LPR. Under M-274 Part 6 and 274a.2(b)(1)(vii), reverification applies only to *temporary* employment authorization. In this data every `US Citizen` worker also has a blank `workAuthorizationExpiry`.
2. The I-9 record has a `workAuthorizationExpiry`, and it is **strictly before** 2026-06-29. If the expiry is on the evaluation date, the authorization has not yet expired, so the worker is out of scope. No such case occurred: every recorded expiry is earlier.
3. The worker was still employed at expiry. Every roster worker is `Active` with no `terminationDate`, so all qualifying workers are in scope.

**When the I-9 export is missing.** A temporary-status worker in a firm without an I-9 export, here every H-1B worker, gets **`needs_evidence`**. The expiry date the obligation depends on is not exported, so I cannot show the worker is out of scope. Dropping the row would silently assume compliance. This produces 117 rows.

**Rule applied to in-scope workers:**
- `supplementBReverificationDate <= workAuthorizationExpiry` gives `pass`.
- A later date gives `fail`.
- A blank date gives `fail`: the authorization expired, the worker is still employed, and the I-9 shows no Supplement B.
- A blank `supplementBDocumentType` gives `needs_evidence`.
- A List B (identity-only) document gives `fail`.

Every document in this data is "Form I-797A Approval Notice with Form I-94". That is acceptable evidence, because the employee chooses which List A or List C document to present.

| Choice | Decision | Support |
|---|---|---|
| Is reverification **on** the expiry date timely? | **Yes.** This decides 52 rows. | 274a.2(b)(1)(vii): reverify "not later than the date work authorization expires". |
| Early reverification | Not penalised | No regulation sets a minimum lead time. |

## 4. `lca.wage.required_wage_greater_of` (per LCA `CASE_NUMBER`)

**Required wage.** This is `max(prevailing wage, actual wage)`, under 655.731(a): "the greater of the actual wage rate ... or the prevailing wage".
- The **prevailing wage** comes from `PREVAILING_WAGE` and `PW_UNIT_OF_PAY` on the LCA, annualized. Hourly rates are multiplied by 2,080 (655.731(a)(2)), weekly by 52, bi-weekly by 26 and monthly by 12.
- The **actual wage** is `ACTUAL_WAGE_FOR_SIMILARLY_EMPLOYED_ANNUAL` from `actual_wage_system.csv`, matched on SOC_CODE and JOB_TITLE. This file is the employer's actual-wage system, as 655.731(a)(1) and (b)(1) describe.

**Wages paid.** These come from `payroll_register.csv`, the gross pay in each period. A period is counted only if both of these hold:
- it overlaps the LCA's BEGIN_DATE to END_DATE window;
- its `payDate` is on or before 2026-06-29. The 16–30 June period is not yet due, so it is excluded.

**Per-period comparison.** For a full-time LCA, the amount due each period is the required annual wage divided by the periods per year (24 for semimonthly). Under 655.731(c)(4), salaried wages are "due in prorated installments ... no less often than monthly".
- For a part-time LCA, the amount due is (annual ÷ 2,080) × `regularHours`.
- A period only partly inside the LCA window is prorated by calendar days. This never happened in the data.

`fail` if **any** counted period pays less than the amount due, after rounding the amount due to cents. I compare **each pay period**, not a year-to-date average, because wages are due on each pay date (655.731(c)(4) and (c)(5)).

**Evidence logic:**
- No payroll register, or no paid period inside the window: `needs_evidence`. The wages actually paid cannot be seen.
- Payroll shows pay **below the prevailing wage** in any period: `fail`, even when the actual-wage file is missing. The required wage is at least the prevailing wage, so the actual-wage leg cannot rescue it.
- Payroll is at or above the prevailing wage but `actual_wage_system.csv` is missing, or has no matching row: `needs_evidence`.
- Otherwise: compare against `max(PW, AW)`.

**Fields not used as wages paid:**
- `WAGE_RATE_OF_PAY_FROM` on the LCA is the attested *offered* rate. It is never below PW in the data.
- Roster `annualBaseSalary` is not evidence of wages paid.

The rulebook mentions "FT/PT, hours, pay frequency". These are read from the payroll register (`fullOrPartTime`, `regularHours`, `payFrequency`) and from the LCA's `FULL_TIME_POSITION`. All rows are FT and Semimonthly with 86.67 hours, which is 2,080 ÷ 24.

**Ambiguity: cohort wage rates.** The rulebook lists "cohort wage rates" as evidence. I treat the employer's actual-wage-system row as that evidence, rather than requiring individual coworker pay data. In 6 LCAs the pay is at or above PW but below AW, so they fail only on the actual-wage leg.

## Roster columns (HRIS export)

| Column | Treatment |
|---|---|
| `employeeNumber` | Entity id. Joins to the I-9, payroll and LCA `EMPLOYEE_NUMBER`. |
| `visaType` | Used only to decide reverification scope: citizen/national/LPR versus temporary status. |
| `employmentStatus`, `terminationDate` | Used for reverification scope (employed at expiry) and the short-engagement rule. |
| `hireDate` | Not used. The I-9 `firstDayOfEmployment` is the evidence. |
| `firstName`, `lastName`, `jobTitle`, `city`, `state` | Not used. |
| `i9Status` (decoy firms) | **Ignored.** A summary flag like "Complete" is not evidence of signing dates. |
| `onboardingCompletedDate` (decoy) | **Ignored.** It is not a Section 1 or Section 2 signature date. |
| `workAuthValidThrough` (decoy) | **Ignored.** The expiry evidence is the I-9 `workAuthorizationExpiry`. In decoy firms without an I-9 export, H-1B reverification stays `needs_evidence` even though this column is filled in. |
| `annualBaseSalary` (decoy) | **Ignored.** It is a salary of record, not wages actually paid. |
| `payBandMidpoint` (decoy) | **Ignored.** It is not the actual wage paid to similarly employed workers. |

As a result, the verdicts for plain and decoy versions of the same seed are identical. I checked this for all 12 seeds.
