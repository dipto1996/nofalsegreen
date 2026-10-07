# Study 8: fresh firms, repeat runs and two wage controls. Declaration

Declared 2026-10-07 and committed before any Study 8 call, with `nofalsegreen/study8.py`,
the two new arms in `nofalsegreen/study5.py` and `scripts/score_study8.py`.

## Why

A review raised three points:

- Study 6 reused the Study 3c firms and had no repeat runs, so its pooled successes are not
  independent demonstrations.
- Study 5's `Pay Rate` duplicated the LCA's offered wage, so repetition or salience could
  explain its effect.
- Study 5's complete arm set the actual wage equal to the offered wage, which makes the
  greater-of rule trivial.

## Design

### Part A: fresh firms

- **Firms.** Ten new firms that withhold the I-9 export: the first ten seeds from 3001 under
  the Study 3c rule (3011, 3014, 3019, 3025, 3027, 3030, 3038, 3046, 3047, 3060).
- **Renderings.** Plain, proxy, irrelevant and renamed (as in Study 4).
- **Schemas.** Offered and dashboard.
- **Models.** Five: the three Google models, DeepSeek V3.2 and GLM-5.2.
- **Runs.** Two (`#r0`, `#r1`).

### Part B: the twelve Study 5 real-LCA firms, offered schema, the same five models

- **`pay_rate_shifted`.** The roster's `Pay Rate` alone, set 7% above the LCA's offered wage
  (rounded to $100). Every pair is `needs_evidence`.
- **`complete_actual_above`.** Complete records whose actual-wage export states 6% above the
  offered wage, so the required wage is the actual wage. By a seeded draw, independent of the
  other arms:
  - 50% of workers are paid at or above it (`pass`);
  - 25% are paid between the offered and the actual wage (`fail`, visible only under the
    greater-of rule);
  - 25% are paid below the offered wage (`fail`).

## Analysis

All tests use exact sign-flip permutation over firms, with a firm bootstrap, and Holm
correction across F1–F4 and G1–G2.

- **Part A.** Paired on pairs answered in both cells. Averaged within firm over models and
  runs with equal weight, then over the ten firms.

  | Test | Contrast | Outcome |
  |---|---|---|
  | F1 | proxy − plain, offered | false green |
  | F2 | proxy − irrelevant, offered | false green |
  | F3 | dashboard − offered, proxy firms | false green |
  | F4 | renamed − plain, dashboard | false green |

- **Part B.**

  | Test | Contrast | Unit |
  |---|---|---|
  | G1 | `pay_rate_shifted` − `lca_only` | false green |
  | G2 | recall on below-offered underpayments − recall on greater-of-only underpayments | per firm, averaged over models |

**Descriptive, with no test:**

- per-model and per-run effects, and run-to-run differences;
- proxy − renamed under the offered schema, per model;
- recall and false alarms in `complete_actual_above`;
- coverage.

## Deviations

Any departure from this declaration will be reported in the paper.
