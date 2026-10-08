# Study 15: real public records in their native formats. Declaration

Declared 2026-10-08 and committed before any Study 15 call. Code: `nofalsegreen/study15.py`;
`scripts/fetch_study15.py`; `labelcheck/study15_checker.py`; `baselines/prompts.py`
(`contract13b_*` unchanged; `codegen15`); `scripts/run_study15.py`,
`scripts/run_study15_codegen.py`; `scripts/score_study15.py`; `scripts/power_study15.py`.

## Why

Studies 13 and 14 render generated records. This study freezes the systems and applies them to
real records from three public sources, in the formats their publishers use, outside the
packet generator, and compares extraction with a strengthened code-generation arm.

## Records

- **openFDA food enforcement reports** (the API's JSON), **USAspending contract awards** (the
  award API's JSON, nested), and **DOL LCA disclosure rows** (the disclosure file's columns,
  dates as the file's Excel serial day numbers): 240, 240 and 120 records, chosen by the
  smallest SHA-256 of the identifier from stated queries (`scripts/fetch_study15.py`; checksums
  in `data/study15/PROVENANCE.json`). A first fetch of 120 per API source by the same rule was
  enlarged for power before any call (kept in `data/study15/raw_first120`).
- **Packets.** Twelve records of one source: 20, 20 and 10 packets (50 contents). In each, four
  records have one deciding field withheld (chosen by a fixed seed), in the publisher's own
  convention for a missing value (`""`, `null`, an empty cell). Values are never altered.
  Fields are also missing at source (for example termination dates of ongoing recalls).
- **Rules** (`docs/study15/CONTRACT_SPEC.md`), two per source, with thresholds set near each
  field's median from the fetched data, before any call, so that both outcomes occur:
  classification within 30 days and termination within 180 days of initiation; a performance
  period of at most 1,095 days and an obligation of at least 0.95 of the potential value; an
  offered wage of at least 1.05 times the prevailing wage and an employment period of at least
  1,095 days. Reassuring fields that establish nothing remain (recall status, potential end
  date, exercised options, the wage range's upper bound).
- **Labels.** All 1,200 agree with a checker written by a separate agent from the
  specification, reading the native files directly (so it also checks our conversion of the
  formats), with exact decimal arithmetic.

## Systems (frozen)

- **Evidence-first prompt** and **extraction + solver**: Study 13's replication prompts and
  solver, unchanged; rule statements in the same corrected form.
- **Code generation, strengthened after review** (`codegen15`): the program receives the pairs
  to answer at run time (a manifest); the model has extraction's budget for the packet (up to
  three calls of 32,000 output tokens); a run that fails, prints no valid JSON, misses or adds
  pairs, or reports malformed facts is returned to the model with those diagnostics, never a
  label or value, for up to two repairs. The final program is also run on the next packet of
  the same source with its manifest.
- **Always abstain.** A program written for these three public schemas would be exact by
  construction (it is how the labels are computed); Study 13's rule-based parsers know only
  Study 13's rules and are not applicable.

Five models, one run; all systems launched together for each model.

## Declared tests

Unit: the packet (50). A packet's value is the mean over five models. Two-sided sign-flip test
(200,000 random sign patterns), packet bootstrap interval (2,000 draws), Holm over H1–H3.

| | Contrast | Prediction |
|---|---|---|
| H1 | Extraction + solver − evidence-first: unsupported `pass` | negative |
| H2 | Extraction + solver − code generation: correct decisions | positive |
| H3 | Extraction + solver − evidence-first: correct decisions | positive |

**Power** (`docs/study15/power.json`, from Study 14 with effects halved): about 1.0 for H1
and H3; for H2, 0.985 if the strengthened arm closes half of Study 14's gap and 0.49 if it
closes three quarters. A null H2 is therefore weak evidence of equivalence.

**Per-model safety (declared criterion).** For each model, extraction's and code generation's
unsupported `pass` rate, with a packet-bootstrap upper 95% bound below 0.01.

## Reported, not tested

All measures by source and by model; unsupported decisions on pairs whose evidence we withheld
versus pairs missing at source; code generation's calls, repairs, capped replies and reuse;
a slot audit; tokens per pair for every model system.
