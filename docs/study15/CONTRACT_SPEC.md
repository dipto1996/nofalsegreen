# Study 15 decision contracts (real public records, native formats)

Each packet directory holds ONE document, in its publisher's native format. Each record is one
entity, identified by the key field below. Evaluate both rules of the workflow for every record.

## Documents

| Workflow | File | Format | Entity key |
|---|---|---|---|
| fda | `fda_enforcement_reports.json` | openFDA food enforcement API: a JSON object whose `results` is a list of report objects | `recall_number` |
| usa | `usaspending_awards.json` | USAspending award API: a JSON list of award objects | `generated_unique_award_id` |
| lca | `lca_disclosure.csv` | DOL LCA disclosure columns, one row per record | `CASE_NUMBER` |

**Missing values.** fda: an empty string `""` (or an absent key) is no value. usa: `null` (or an
absent key, or an absent parent object) is no value. lca: an empty cell is no value.

**Value formats.**
- fda dates are strings `YYYYMMDD`.
- usa dates are strings beginning `YYYY-MM-DD` (ignore anything after the first ten characters);
  amounts are JSON numbers in USD.
- lca dates are Excel serial day numbers (day 1 = 1900-01-01; the conversion is
  date(1899, 12, 30) + n days; values may be written with a trailing `.0`); amounts are decimal
  numbers in USD per year.
- Treat amounts as exact decimals (no binary floating point).

## Rules

| Rule | Predicate | Facts (the only field that establishes each) |
|---|---|---|
| `fda.classified_30d` | C ≤ I + 30 days | I = `recall_initiation_date`; C = `center_classification_date` |
| `fda.terminated_180d` | T ≤ I + 180 days | I = `recall_initiation_date`; T = `termination_date` |
| `usa.period_3y` | E ≤ S + 1095 days | S = `period_of_performance.start_date`; E = `period_of_performance.end_date` |
| `usa.obligated_95` | O ≥ 0.95 × V | O = `total_obligation`; V = `base_and_all_options` |
| `lca.wage_105` | W ≥ 1.05 × P | W = `WAGE_RATE_OF_PAY_FROM`; P = `PREVAILING_WAGE` |
| `lca.three_years` | E ≥ B + 1095 days | B = `BEGIN_DATE`; E = `END_DATE` |

Days are calendar days. Every other field (statuses, potential end dates, report dates, wage
ranges, exercised options, and so on) establishes nothing.

## Verdicts, for each (rule, record)

1. Each fact takes the value of its field in the record. If the same entity key appears in more
   than one record with disagreeing non-missing values for a fact, that fact is conflicting.
2. If any fact is conflicting: `needs_evidence`.
3. If every fact has a value: `pass` if the predicate holds, else `fail`.
4. If some facts have no value: consider every possible value of the missing facts (any date;
   any amount ≥ 0): `pass` if the predicate holds for all of them, `fail` if it fails for all,
   otherwise `needs_evidence`.
