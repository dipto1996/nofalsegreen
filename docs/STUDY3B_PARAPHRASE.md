# Study 3b: paraphrase robustness. Declaration

Declared 2026-10-04 and committed before any Study 3b call, with its analysis script
(`scripts/score_paraphrase.py`).

## Why

Study 3 tested each schema condition in one wording. A reviewer can fairly ask whether
the effects belong to that wording. Study 3b re-runs the two end points of the schema
ladder with every instruction sentence reworded and the meaning kept.

## Design

- **Firms.** The twelve Study 3 firms, plain and proxy-column renderings, unchanged.
- **Conditions.** `abstain_offered_para` and `abstain_withheld_para`
  (`baselines/prompts.py`). Each rewords the system prompt and the verdict menu of its
  original condition sentence by sentence. The verdict tokens are unchanged, so replies
  parse identically.
- **Models.** Gemini 3.1 Pro, Gemini 3.8 Flash and Gemma 4 26B, on Vertex AI, one run
  each. The four open-weights models from other developers are not re-run: their billing
  against the author's cloud credits had not posted when this was declared, and the
  study uses no other funds.
- **Protocol.** Identical to Study 3.

## Hypotheses

Pooled over the three models with equal weight, using the paired estimator,
clusters (18) and bootstrap draws of Study 3 (seed 20261003). Two-sided, Holm across the
three:

| | Contrast (false-green rate) | Firms |
|---|---|---|
| R1 | proxy − plain, paraphrased dashboard | paired |
| R2 | proxy − plain, paraphrased offered | paired |
| R3 | paraphrased dashboard − paraphrased offered | proxy |

A hypothesis is replicated if its adjusted p is below 0.05 and its sign is positive.

**Secondary (descriptive).** For each of R1–R3, the same contrast in the original wording
on the same three models, and the difference between wordings.
