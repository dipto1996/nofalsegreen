# Study 13: held-out contracts on heterogeneous records. Declaration

Declared 2026-10-07 and committed before any Study 13 call. Code:

- `nofalsegreen/study13.py`: contracts, labeller, generator, development layouts, solver;
- `nofalsegreen/study13_heldout.py`: held-out layouts L4–L6;
- `baselines/study13_parser.py`: the rule-based parsing baseline;
- the prompt variants `contract13_*` in `baselines/prompts.py`;
- `scripts/score_study13.py`; `scripts/verify_study13_labels.py`.

## Why

Study 9's remedy (the model extracts facts with their source; a program decides) was tested
on the rules and layout it was designed with, and a program reading the named columns was
exact there. This study asks whether the remedy transfers to rules and record layouts it was
not designed on, and whether learned extraction adds anything over a strong rule-based
parser when the layout is not known in advance.

## Task and labels

Six decision rules that appear in no earlier study, two per workflow
(`docs/study13/CONTRACT_SPEC.md`): a two-sided 90-day window, a posting deadline with a
10-business-day duration, a four-fact conjunction, a three-date ordering, a 365-day
validity window and a 1.2× threshold. Five of the six have a prioritised fact.

**Packets.** Sixteen entities, with twelve patterns: complete records; an adverse
authoritative record beside reassuring status fields; a blank fact beside a reassuring
proxy; a missing row; a blank fact; a redundant fallback source; a violation established
despite a gap; a fallback that disagrees (resolved by priority); disagreeing duplicate rows
in the fallback (resolved); disagreeing duplicate rows in the deciding source (conflict);
disagreeing duplicates in a single-source fact (conflict); every authoritative record of a
rule missing. Row order is shuffled. Where a workflow cannot express a pattern (a violation
despite a gap in engineering) the entity keeps complete records.

**Labels** come from compatible completions, as in Study 9. Before any call
(`docs/study13/label_check.json`):

- all 480 labels of the test and development packets agree with a checker written
  independently from the specification alone (`labelcheck/study13_checker.py`);
- all 198 completions of the 99 missing-value certificates are verified by that checker;
- on 3,000 random packets outside the generator's patterns (18,000 labels) the two agree
  everywhere, and shuffling rows changes no label.

**Layouts.** The same records in six layouts. L1–L3 are development layouts written with
the generator: canonical CSV; CSV with other headers and value formats; one line per field.
L4–L6 are held-out layouts, designed by a separate author from a brief and kept outside the
repository until the parsing baseline was frozen. Each test packet (two seeds per workflow)
is rendered in all six layouts, so layouts are paired on content.

## Systems

- **Evidence-first prompt** (`contract13_evidence_first`): Study 9's strongest prompt,
  restated for documents.
- **Extraction + solver** (`contract13_extract`): the model reports each fact with the
  document it came from; the solver accepts a value only from a document the contract names
  and applies the rule.
- **Rule-based parser + solver** (`baselines/study13_parser.py`): written by a separate
  author from the specification and the L1–L3 development packets (seeds 1391–1393), asked
  to be as robust to unseen layouts as possible, without a language model. Frozen before the
  held-out layouts entered the repository.
- **Program reading the named columns**: the canonical column names only; abstains when a
  document is not a CSV with those columns.
- Always abstain.

Models: Gemini 3.1 Pro, Gemini 3.8 Flash, Gemma 4 26B, DeepSeek V3.2, GLM-5.2 (one run,
`#r0`). Both prompts are launched together for each model, so their calls interleave in
time. Twelve pairs per call.

## Declared tests (held-out layouts L4–L6)

Unit: the packet (3 workflows × 3 layouts × 2 seeds = 18). Per packet, the mean over the
five models with equal weight. Unanswered pairs count as not correct and as needing
follow-up. Exact two-sided sign-flip test over packets, packet bootstrap interval (2,000
draws), Holm over H1–H3.

| | Contrast | Prediction |
|---|---|---|
| H1 | Extraction + solver − evidence-first: unsupported `pass` (all pairs) | negative |
| H2 | Extraction + solver − rule-based parser: correct decisions on decidable pairs | positive |
| H3 | Extraction + solver − evidence-first: correct decisions on decidable pairs | positive |

**Non-inferiority (N1, declared, outside Holm).** Extraction + solver − rule-based parser in
unsupported `pass`: the upper bound of the 95% packet-bootstrap interval is below +0.02.

## Reported, not tested

The same contrasts on the development layouts; every system's unsupported `pass`,
unsupported `fail`, correct decisions, coverage, unnecessary abstention and follow-up share,
by layout, by model (with per-model packet-bootstrap intervals) and by pattern; tokens per
pair for each prompt (`docs/study13/runs`); a slot-level audit of every extracted fact
(value, absence, conflict and document) against the records; and, exploratory, a hybrid
that uses the parser where it reports every fact and the model elsewhere.

## Failures

Every outcome is reported. Delivery failures follow the rule of Appendix C.4: retries, then
coverage is reported and missing pairs count as unanswered.

## Addendum: replication with a corrected rule statement

Declared 2026-10-07, after the first run had been scored and before any replication call.

**What went wrong.** The first run's rule statement printed some fact names with their unit
("measured load (kN)"), while the extraction prompt asks for "exactly the fact names in the
rule". Gemini 3.1 Pro, Gemini 3.8 Flash and GLM-5.2 copied the unit or wrote names in
snake_case, the declared scorer matches names exactly, and those facts were therefore
treated as absent, so the solver abstained. Under the declared scoring H1 and N1 were
confirmed and H2 and H3 were not. A post-hoc rescoring that matches names after removing a
trailing unit, case and underscores is reported beside it, marked as post hoc.

**Replication.** The same 36 packets and the same system prompts, with the rule statement
changed only so that each fact name is quoted on its own and its unit stated in a separate
sentence (`study13.statement_r2`; variants `contract13b_evidence_first` and
`contract13b_extract`; run tag `#r2`). Both prompts are launched together for each model.
H1–H3 and N1 are tested exactly as declared above, with the declared exact-name scoring, Holm
within the replication (`python3 scripts/score_study13.py --r2`, writing
`docs/study13/results_r2.json`). The first run's results are reported in full beside it.
