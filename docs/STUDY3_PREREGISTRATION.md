# Study 3: declaration

Declared 2026-10-03 and committed before any Study 3 call. The commit that adds this file
is the time stamp; the analysis script (`scripts/score_study3.py`) is committed with it.
Only one-word availability probes ("Reply with the word ok."), carrying no benchmark data,
were sent to the new models before this commit.

## Why

Two of the paper's findings were formed after seeing results, and the paper says so:

1. **Decomposition.** The dashboard schema's effect on the false-green rate splits into
   an *abstention effect* (removing every non-committal verdict) and a *definition effect*
   (redefining `pass` from "the required evidence is present and shows compliance" to "the
   obligation is satisfied"). The conditions that separate them (`abstain_removed_only`,
   `abstain_closed`) were added after the first results.
2. **Mechanism.** False greens arise by *adjacent-field substitution*: a populated column
   whose meaning sits beside the missing evidence is read as that evidence. This was read
   off the anchor firm's replies. Study 2 could not test it, because generator v2 never
   renders such a column.

Study 3 tests both on fresh firms, with a generator that plants adjacent columns, and on
models from four developers besides Google.

## Design

**Firms.** The first twelve seeds from 1001 upward that meet the Study 2 eligibility rule
(the firm withholds at least one export and leaves at least one rule family decidable):
1001, 1002, 1003, 1008, 1010, 1014, 1017, 1018, 1020, 1021, 1024, 1027
(`nofalsegreen/study3.py`, `seeds()` reproduces the list). Each firm has 42 pairs; the
twelve hold 504 pairs, of which 180 are withheld (81 wage-rule pairs in nine firms, 99
I-9 pairs in three firms), 87 are violations and 237 are conforming controls.

**Arms.** Each seed is rendered twice.
- `plain`: generator v2, as in Study 2.
- `decoy`: generator v3 (`GeneratorConfig(decoys=True)`). The HRIS roster gains five
  columns that sit beside the evidence a rule needs without being it: `i9Status`
  ("Complete"), `onboardingCompletedDate`, `workAuthValidThrough` (the current
  authorization's end), `annualBaseSalary` (salary of record, set at the LCA offered
  wage) and `payBandMidpoint`. The columns appear in every decoy firm, whether or not the
  export they imitate is withheld. They come from a separate random stream, so the two
  arms have identical workers, labels and other exports. No label changes: none of the
  five columns is an item the rulebook lists as evidence for the rule it imitates.

**Conditions.** The four schema conditions of the Vertex block, prompt v1.1.0 verbatim
(Appendix B): `abstain_offered`, `abstain_removed_only`, `abstain_closed`,
`abstain_withheld`.

**Models (seven).**
- Google, as in the Vertex block: Gemini 3.1 Pro (`gemini-3.1-pro-preview`), Gemini 3.8
  Flash (`gemini-3.8-flash`), Gemma 4 26B (`gemma-4-26b-a4b-it-maas`).
- Other developers, open weights served by Google on Vertex AI: OpenAI gpt-oss-120b,
  DeepSeek V3.2, Qwen3 235B A22B Instruct 2507, Moonshot Kimi K2 Thinking.

**Protocol.** As in Studies 1 and 2 and the Vertex block: batch 12, scoped sources,
temperature 0, output cap 32,000 tokens (reasoning tokens included), the same
delivery-failure rule. Two changes are fixed in advance.
- Qwen3 235B's served output limit is 16,384 tokens, so its requests are capped there.
- A scoping defect is corrected. Checking the decoy prompts for this declaration showed
  that the scoped prompt for the wage rule never carried the generated firms'
  `actual_wage_system` export, which the rule needs. In Study 2 every wage pair was
  therefore sent without it. The withheld wage pairs stay correctly labelled, because the
  evidence was missing either way. The 27 decidable wage pairs (three firms) were not
  decidable from what was sent; the paper excludes them from Study 2's detection and
  false-alarm metrics and says so. The fix (`baselines/prompts.py`, `REGIME_SOURCES`)
  adds the export to the wage regimes. It changes no anchor-firm prompt, because the
  anchor firm has no such export. Study 3 runs with the fix.

**Repeats.** One run per (model, arm, condition). In the Vertex block the spread across
three repeats was at most 0.06 in 21 of 24 cells; the budget goes to firms and models
instead.

**Extension E1 (descriptive).** The four new models are also run on the Study 1 anchor
subset (140 pairs) under the four conditions, once each, so that Tables 3, 7 and 8 can
report them beside the earlier models. E1 is not part of the confirmatory family.

## Outcome and unit

The outcome is the false-green indicator on a withheld pair: 1 if the verdict is `pass`,
else 0. A contrast between two cells uses only withheld pairs answered in both. A pair is
answered if a verdict was parsed for it, including a verdict outside the condition's
menu, as in the Vertex block. Coverage is reported for every cell.

Uncertainty comes from an obligation-cluster bootstrap. A cluster is one (firm, rule),
giving 18 clusters of withheld pairs. There are 2,000 draws with seed 20261003, and the
same draws are used for every model. The p-value is two-sided: twice the smaller tail
share of bootstrap differences at or beyond zero, floored at 1/2,000.

## Hypotheses

The primary estimate pools the seven models: the mean over models of each model's mean
paired difference. All four primary tests predict a positive difference.

| | Name | Contrast (false-green rate) | Arm |
|---|---|---|---|
| P1 | Abstention effect | `abstain_closed` − `abstain_offered` | decoy |
| P2 | Definition effect | `abstain_withheld` − `abstain_closed` | decoy |
| P3 | Adjacent columns, dashboard schema | decoy − plain, paired by pair | `abstain_withheld` |
| P4 | Adjacent columns, recommended schema | decoy − plain, paired by pair | `abstain_offered` |

**Decision rule.** Holm correction across P1–P4. A hypothesis is *confirmed* if its
Holm-adjusted p is below 0.05 and the difference is positive. It is *contradicted* if the
p is below 0.05 and the difference is negative. Otherwise it is *not confirmed*. The paper
reports the outcome of every test, whatever it is, and revises its claims to match.

**Secondary analyses (Holm within each family).**
- S1: P1–P4 per model, 28 tests.
- S2: `abstain_removed_only` − `abstain_offered` on the decoy arm, pooled and per model.
- S3: the interaction, (P2 contrast on decoy) − (P2 contrast on plain), pooled.
- S4: P1–P4 pooled separately over the Google models and over the other four.
- S5: the false-alarm rate on conforming controls, and on near-miss controls, per arm,
  and decoy − plain. Decoy columns may also cause false alarms, for example where the
  salary of record differs from wages paid.

All other breakdowns are exploratory and labelled as such.

## What would change the paper

- If P1 and P2 are confirmed, the two design rules are stated as confirmed on fresh data
  across five developers.
- If P3 and P4 are confirmed, adjacent-field substitution is stated as a tested mechanism
  rather than an interpretation.
- If P4 fails while P3 holds, the recommended schema is stated to protect against
  adjacent columns, and the design rules gain a stronger justification.
- If any of P1–P3 is not confirmed, the corresponding claim in Sections 1, 9 and 10 is
  scoped to the anchor firm and labelled exploratory.
