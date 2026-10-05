# Study 4: controls for the proxy mechanism, a schema factorial, an evidence-gating prompt, and repeat runs. Declaration

Declared 2026-10-05 and committed before any Study 4 call, together with
`nofalsegreen/study4.py`, the prompt variants in `baselines/prompts.py`, and
`scripts/score_study4.py`.

## Why

An external review raised the following points:

1. **(a) The proxy effect may be a generic distractor effect.** Adding any five columns might raise false greens, so the effect is not shown to be evidence substitution. The review asked for:
   - columns matched in type and placement but irrelevant to any obligation;
   - the same values under neutral names;
   - proxies that suggest non-compliance.
2. **(b) The schema contrasts bundle changes.** Offered → closed removes the abstaining verdicts *and* their explanatory text. Closed → dashboard changes the definitions *and* drops a warning.
3. **(c) Recommendations are untested against realistic mitigations.**
4. **(d) Each confirmatory cell was run once.**

## Design

- **Firms.** The ten Study 3c firms (seeds 2003, 2007, 2009, 2023, 2026, 2037, 2040, 2041, 2048, 2069).
  - Every firm withholds the I-9 export.
  - Their 330 unassessable pairs are all I-9 pairs: Section 1, Section 2 and reverification.
  - Their wage pairs are all decidable.
- **Renderings.** Plain and all-proxy are the Study 3c firms themselves. Three new controls draw from the same separate random stream, so the labels and all other exports are identical to plain (verified for every seed):
  - **renamed:** the proxy values under the neutral names `rosterField1`–`rosterField5`.
  - **irrelevant:** five columns in the same positions and of the same types, unrelated to any obligation: `badgeStatus` = "Active", `parkingPermitIssuedDate` (near the start date), `laptopWarrantyThrough` (a future date), `annualTrainingBudgetUsd`, `commuterBenefitUsd`.
  - **adverse:** the proxy names with values that suggest non-compliance: `i9Status` = "Incomplete", an onboarding date 10–16 days after hire, a work-authorisation end date in the past, and salary and pay-band values below the required wage.
- **Schemas.**
  - **Original:** offered (`abstain_offered`) and dashboard (`abstain_withheld`), wording v1.1.0.
  - **Factorial `fx_o{O}d{D}w{W}`:** eight menus built from three switches. Every menu ends with the same closing sentence.
    - O: the two abstaining verdicts are listed with their offered definitions.
    - D: `pass` and `fail` are defined by the required evidence, against bare "satisfied"/"violated".
    - W: the one-sentence warning "A document that was not provided is not a document that is in order." is present.
  - **`cite_first`:** the offered menu plus a requirement to name the column that is itself the required record, as `<export>.<column>`, before `pass` or `fail`. If no export contains that record, the verdict is `needs_evidence`.
- **Cells (all on the three models below).**

  | Cells | Count |
  |---|---|
  | renamed, irrelevant, adverse × offered and dashboard | 6 |
  | plain, proxy × the eight factorial menus | 16 |
  | plain, proxy × `cite_first` | 2 |
  | plain, proxy × offered and dashboard, repeated as runs `#r1` and `#r2` | 8 |

  The `#r0` replies for plain and proxy under offered and dashboard are Study 3c's.
- **Models.** Gemini 3.1 Pro, Gemini 3.8 Flash and Gemma 4 26B, at batch 12, as in Study 3c. They run on Vertex, paid from cloud credits.

## Analysis

- **Unit of analysis.** The outcome is per unassessable pair: the false-green indicator (`pass`), or for H3 the false-red indicator (`fail`).
- **Averaging.** Each contrast is paired on pairs answered in both cells. It is averaged within firm and model, then over the three models, giving one difference per firm.
- **Inference.**
  - Exact two-sided sign-flip permutation over the ten firm differences (1,024 patterns).
  - Firm-bootstrap 95% interval: 2,000 draws, seed 20261005.
  - Holm correction across H1–H7.

| | Contrast | Outcome | Schema | Question |
|---|---|---|---|---|
| H1 | proxy − renamed | false green | offered | Do the column names carry the effect? |
| H2 | proxy − irrelevant | false green | offered | Is it more than adding any five columns? |
| H3 | adverse − plain | false red | offered | Do models substitute the proxy in both directions? |
| H4 | O main effect: mean over D, W of (O=0 − O=1) | false green | factorial, proxy firms | Removing the abstaining verdicts alone |
| H5 | D main effect: mean over O, W of (D=0 − D=1) | false green | factorial, proxy firms | Bare definitions alone |
| H6 | W main effect: mean over O, D of (W=0 − W=1) | false green | factorial, proxy firms | Dropping the warning alone |
| H7 | offered − `cite_first` | false green | proxy firms | Does naming the required record first reduce false greens? |

A test is *confirmed* if its Holm-adjusted p < 0.05; its sign is reported either way. No
direction is assumed.

## Secondary and descriptive (no test)

- **Controls under the dashboard schema.**
  - H1–H3 contrasts repeated under the dashboard schema.
  - renamed − plain and irrelevant − plain.
  - The fields cited on false greens.
- **Factorial details.**
  - The same main effects on plain firms.
  - The two-way interactions and the cell means for all eight menus.
- **`cite_first` costs.** Recall on violations and the false-alarm rate on conforming pairs, compared with offered. Also the share of `pass` replies that cite a column of the required export.
- **Deterministic evidence gate.** A rule is routed to `needs_evidence` when an export it needs is absent: I-9 rules need the I-9 export; the wage rule needs both the payroll register and the actual-wage export. The gate is applied to the existing replies, with no calls. It is reported with its limitation: it is exact here because insufficiency in the generator is whole-export.
- **Run-to-run variability.** For each repeated cell: the spread of the false-green rate over `#r0`–`#r2`, and the proxy − plain contrast per run.
- **Full verdict allocation** on unassessable pairs (pass, fail, needs_evidence, unmonitored, unanswered) for every cell.

## Deviations

- Any departure from this declaration will be reported in the paper.
- Delivery failures follow the Study 3 rule: retries, then sharding, then finalisation with the pairs answered.
