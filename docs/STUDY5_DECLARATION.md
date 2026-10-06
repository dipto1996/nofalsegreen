# Study 5: the wage rule on real LCA records. Declaration

Declared 2026-10-06 and committed before any Study 5 call, with `nofalsegreen/study5.py`
and `scripts/score_study5.py`.

## Why

Reviewers objected that every earlier study uses generated records. Study 5 uses 120
real certified H-1B LCAs from DOL's public disclosure file (`data/real_lca/PROVENANCE.md`).

The label is fixed by what a disclosure is, not by legal interpretation. A disclosure
states the wage offered and the prevailing wage, never the wages paid. So whether the
worker was paid the required wage (20 C.F.R. 655.731) cannot be decided from it.

The roster follows BambooHR's documented export column names. Its `Pay Rate` field (a
salary of record) is the realistic version of the proxy studied earlier.

## Design

- **Firms.** The 120 rows in file order form 12 firms of 10 LCAs, one worker each. Worker
  names are synthetic, and no employer name is used. The evaluation date is 2027-03-31.
- **Arms.**

  | Arm | What the model is given | Correct verdict |
  |---|---|---|
  | `lca_only` | Roster without pay fields, plus the real LCA rows | `needs_evidence` |
  | `salary` | As `lca_only`, with the roster's `Pay Rate` (salary of record, set to the LCA's offered wage) | `needs_evidence` |
  | `complete` | As `salary`, plus a constructed payroll register (Jan–Mar 2027) and an actual-wage export | Decidable: by a seeded draw, half the workers are paid at or above the required wage (`pass`) and half below it (`fail`) |

- **Schemas.** Offered and dashboard, wording v1.1.0.
- **Models.** Gemini 3.1 Pro, Gemini 3.8 Flash and Gemma 4 26B, at batch 12, one run each.

## Analysis

- **Unit.** The outcome is the false-green indicator on a pair.
- **Contrasts.**
  - Paired on pairs answered in both cells.
  - Averaged within firm and model, then over the three models.
  - Exact sign-flip test over the 12 firms (4,096 patterns, two-sided).
  - Firm bootstrap: 2,000 draws, seed 20261006.
  - Holm correction across R1–R3.

| | Contrast | Schema |
|---|---|---|
| R1 | `salary` − `lca_only` | offered |
| R2 | `salary` − `lca_only` | dashboard |
| R3 | dashboard − offered, on `lca_only` | — |

**Descriptive, with no test:**

- **False-green rate per cell.** Over all pairs, and over answered pairs.
- **Fields cited on false greens.**
- **`complete` arm.** Recall on underpaid workers. False-alarm rate on correctly paid
  workers (any verdict but `pass`, over all pairs). This shows whether the models can
  decide when the records are present.
- **Comparison with Study 3.** The Study 3 wage-rule rates, for reference.

## Deviations

Any departure from this declaration will be reported in the paper.
