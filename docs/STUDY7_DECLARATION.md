# Study 7: which pay field moves the wage verdict. Declaration

Declared 2026-10-07 and committed before any Study 7 call, with the two new arms in
`nofalsegreen/study5.py` and `scripts/score_study7.py`.

## Why

A review noted that Study 5's salary arm adds three roster fields at once:

- `Pay Rate`, the salary of record;
- `Pay Type`;
- `Pay Schedule`.

So R1 measures a pay-information bundle, not the salary column.

## Design

- **Firms.** The twelve Study 5 real-LCA firms, unchanged.
- **New arms.**
  - `pay_rate_only`: the roster with `Pay Rate` alone.
  - `pay_context_only`: the roster with `Pay Type` and `Pay Schedule` alone.
  - Every pair in both arms is `needs_evidence`.
- **Schema.** Offered, where R1 was confirmed.
- **Models.** Five:
  - Gemini 3.1 Pro, Gemini 3.8 Flash and Gemma 4 26B, as in Study 5;
  - DeepSeek V3.2 and GLM-5.2, as in Study 6.

  One run each, at batch 12.
- **Baseline.** The `lca_only` and `salary` cells are the retained Study 5 and Study 6
  replies.

## Analysis

The declared Study 5 estimator, over all five models:

- paired on pairs answered in both cells;
- averaged within firm and model, then over models with equal weight;
- exact sign-flip test over the 12 firms;
- Holm correction across W1 and W2.

| Test | Contrast |
|---|---|
| W1 | `pay_rate_only` − `lca_only` |
| W2 | `pay_context_only` − `lca_only` |

**Descriptive, with no test:**

- per-model contrasts;
- `salary` − `pay_rate_only`, which shows whether the pay context adds to the salary field;
- coverage.

## Deviations

Any departure from this declaration will be reported in the paper.
