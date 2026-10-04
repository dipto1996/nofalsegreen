# Study 3c: more I-9 firms, and one proxy column at a time. Declaration

Declared 2026-10-04 and committed before any Study 3c call, with `scripts/score_study3c.py`.

## Why

A reviewer found that most of Study 3's proxy-column effect is on the I-9 rules, whose
unassessable pairs came from only three firms, and asked which proxy column does the
work, since no reply cited the I-9 status column.

## Design

- **Firms.** The first ten seeds from 2001 upward that withhold the I-9 export and leave a
  rule family decidable: 2003, 2007, 2009, 2023, 2026, 2037, 2040, 2041, 2048, 2069
  (`nofalsegreen/study3c.py`). Each has 33 unassessable I-9 pairs (330 in all).
- **Renderings.** Plain; all five proxy columns (as in Study 3); and each of the three I-9
  proxy columns alone (`i9Status`, `onboardingCompletedDate`, `workAuthValidThrough`).
  Labels and all other exports are identical across renderings.
- **Cells.** Every rendering under the dashboard schema; plain and all-proxy also under the
  offered schema. Original wording (v1.1.0).
- **Models.** Gemini 3.1 Pro, Gemini 3.8 Flash, Gemma 4 26B; one run.

## Analysis

The outcome is the false-green indicator on an unassessable pair. Each contrast is paired
on pairs answered in both cells, averaged within model and then over the three models. The
**firm** is the unit of resampling: ten clusters. Inference is an exact sign-flip
permutation test over the ten firm-level differences (1,024 patterns; two-sided), with a
firm bootstrap interval (2,000 draws, seed 20261004). Holm across the five tests below.

| | Contrast | Schema |
|---|---|---|
| C1 | all proxy columns − plain | dashboard |
| C2 | all proxy columns − plain | offered |
| C3 | `i9Status` alone − plain | dashboard |
| C4 | `onboardingCompletedDate` alone − plain | dashboard |
| C5 | `workAuthValidThrough` alone − plain | dashboard |

C1 and C2 test replication on new firms. C3–C5 ask which column carries the effect; for
C5 the outcome is restricted to the reverification rule, the only rule the current
authorisation's end date bears on, and for C3 and C4 to the Section 1 and Section 2 rules.
