# Study 12: the "match by meaning" reading rule. Declaration

Declared 2026-10-07 and committed before any Study 12 call, with the variants
`contract_sem_meaning_offered` and `abstain_offered_nomatch` (`baselines/prompts.py`) and
`scripts/score_study12.py`.

## Why

Unsupported `pass` answers were common in Studies 3–8 (0.2–0.4 under the offered schema on
proxy-column firms) and rare in Studies 9–11 (under 0.06). Two candidate explanations did not
survive their declared tests:

- binding the evidence to named columns (Study 10);
- the visibility of the gap (Study 11).

One instruction remains that the Studies 3–8 prompt has and the Studies 9–11 prompts lack:
"Export column names will not match the wording of the obligations. Match them by meaning…"
It licenses reading a column as the required fact by meaning.

## Design

**M1. Adding the rule.**

- **Packets.** The Study 9 Part A packets, with familiar names.
- **Contrast.** The described-evidence offered prompt with the reading rule added
  (`contract_sem_meaning_offered`), against the same prompt without it (`contract_sem_offered`,
  Study 10's replies).
- **Unit.** The packet (18). Outcome: unsupported `pass` on `needs_evidence` pairs, paired on
  pairs answered in both conditions.

**M2. Removing the rule.**

- **Firms.** The Study 3c proxy-column firms.
- **Contrast.** The original offered prompt (Study 3c and Study 6 replies) against the same
  prompt with the reading rule deleted (`abstain_offered_nomatch`). The effect is reported as
  original − without.
- **Unit.** The firm (10). Outcome: false green on unassessable pairs, paired.

**Shared settings.**

- **Models.** The same five, one run each.
- **Inference.** Exact two-sided sign-flip test, with Holm correction across M1 and M2.
- **Prediction.** Both effects are positive.

**Descriptive, with no test:** per-model effects, and the fields cited on false greens.

## Deviations

Any departure from this declaration will be reported in the paper.
