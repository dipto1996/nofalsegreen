# Study 14: a powered transfer test. Declaration

Declared 2026-10-08 and committed before any Study 14 call. Code:

- `nofalsegreen/study14.py`; layouts `nofalsegreen/study14_layouts_{a,b,c}.py`;
- `baselines/study14_parser.py` (the parser, frozen before the layouts entered the repository);
- `baselines/prompts.py` (`contract13b_*` unchanged from Study 13's replication; `codegen14`);
- `scripts/run_study14.py`, `scripts/run_study14_codegen.py`, `scripts/exec_study14_codegen.py`;
- `scripts/score_study14.py`; `scripts/power_study14.py`; `scripts/verify_study13_labels.py`.

## Why

Study 13 found large effects in the predicted direction, but its held-out inputs were six
contents rendered three times each. Clustered by content, its three tests have exact Holm
p = 0.094, and its layouts came from one designer. This study tests the same claims with
independent contents, new layouts from several designers, a stronger parser, a second
learned baseline and model-specific safety criteria.

## What is frozen

The six rules, labeller, solver and the corrected rule statement of Study 13's replication,
and both of its prompts, unchanged. Exact rational arithmetic for amounts (corrected after
review, before this declaration).

## Contents and layouts

- **Contents.** 30 new packets: ten seeds (1401–1410) per workflow, sixteen entities and the
  twelve patterns of Study 13. All 960 labels agree with the independent checker, and all 390
  completions of the 195 missing-value certificates verify (`docs/study13/label_check.json`,
  `by_study`).
- **Layouts.** Six, from three designers who worked separately from one another and from us,
  each given the same constraints (every record kept, blanks never rendered as values, every
  value exactly recoverable) and a different direction: A1–A2 public and standard formats (a
  pipe-delimited disclosure-style export with many unrelated columns, an X12-style
  interchange); B1–B2 human documents (HTML form sheets, an e-mail export with relative dates
  and decoy header dates); C1–C2 system exports (an SQL dump with epoch days, cents and
  decanewtons; a pivoted table with ISO week dates). Each designer's self-test reads every
  value back exactly.
- **Assignment.** Each content is rendered in two layouts from different designers
  (`study14.layouts_of`); each layout carries ten contents.

## Systems

- **Evidence-first prompt** and **extraction + solver**: Study 13's replication prompts.
- **Rule-based parser** (`baselines/study14_parser.py`): Study 13's parser, improved by its
  original author with all six Study 13 layouts as development data, frozen before the new
  layouts entered the repository. Study 13's parser is also reported.
- **Hybrid**: the parser's verdict where the parser reports a value for every fact of a pair;
  extraction + solver elsewhere (including wherever the parser reports `ABSENT` or `CONFLICT`).
- **Code generation** (`codegen14`): the model sees the packet and writes a parser program;
  the program runs sandboxed (no network, no writes, 60 s) and its facts go to the same solver.
  It is also run on another content in the same layout ("reuse").
- **Always abstain.**

Models: Gemini 3.1 Pro, Gemini 3.8 Flash, Gemma 4 26B, DeepSeek V3.2, GLM-5.2, one run. All
model systems are launched together for each model.

## Declared tests

Unit: the content (30). A content's value is the mean over its two renderings and, for model
systems, over five models with equal weight; a missing reply counts as no answer. Two-sided
sign-flip test over contents (200,000 random sign patterns), content bootstrap interval
(2,000 draws), Holm over H1–H4.

| | Contrast | Prediction |
|---|---|---|
| H1 | Extraction + solver − evidence-first: unsupported `pass` | negative |
| H2 | Extraction + solver − parser: correct decisions on decidable pairs | positive |
| H3 | Hybrid − parser: correct decisions on decidable pairs | positive |
| H4 | Extraction + solver − code generation: correct decisions | none (two-sided) |

**Power** (`docs/study14/power.json`): with Study 13's replication effects halved and its
variability, 30 contents give power 0.94 for H2, the weakest, at α = 0.05/4.

**Model-specific safety (declared criterion).** For each model and each of extraction, hybrid
and code generation: the content-bootstrap upper 95% bound of (system − parser) unsupported
`pass` is below 0.01. The margin, one extra unsupported `pass` per hundred decisions, is a
deployer's choice rather than a derived quantity; every model's interval is reported so a
reader can apply another.

**Layout families (declared secondary).** The H2 and H3 contrasts averaged within each of the
six layouts, with the number of layouts in the predicted direction and an exact sign-flip test
over layouts. Six layouts cannot reach significance after correction; this is reported as a
check on whether the effect holds across families, not as a test of a population of layouts.

## Reported, not tested

All measures by system, layout, model and pattern (conflicts in particular); a slot audit of
every reported fact; code generation's program, execution and reuse rates; tokens per pair for
every model system.
