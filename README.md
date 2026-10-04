# No False Green

A benchmark for **evidence-aware compliance verdicts** over structured employer records.

Automated compliance tools present an organisation's obligations as a dashboard of
green and red states. The dangerous error is not a wrong red. It is a **false green**:
an obligation reported as satisfied when the evidence needed to assess it was never
present. This benchmark measures that error directly.

```bash
python3 -m nofalsegreen.cli describe
python3 -m nofalsegreen.cli score --firm northwind --baseline always_pass
python3 -m nofalsegreen.cli generate --seed 7 --out data/firms/synthetic-000007
python3 tests/test_benchmark.py          # 52 assertions
python3 tests/test_llm_harness.py        # 54 assertions
python3 scripts/sweep.py --firms 30      # trivial baselines
python3 scripts/cost_probe.py --firms 30 # token cost, no API calls
```

No dependencies beyond the Python 3.10+ standard library. Provider SDKs are imported
only when a real model is actually called.

## Evaluating a language model

```bash
# dry run: exercises the whole path offline, no keys needed
python3 scripts/run_llm.py --model mock-guesser --firms 2 --variant both

# real run: anchor firm first (under $1.50 on the priciest tier)
export ANTHROPIC_API_KEY=...
python3 scripts/run_llm.py --provider anthropic --model <model-id> --firms 0

# full sweep, both ablation conditions, resumable
python3 scripts/run_llm.py --provider anthropic --model <model-id> \
    --firms 30 --variant both --out docs/llm_results.json
```

Results are keyed by `(model, variant)` and appended, so the sweep can be run
incrementally. `--keep-raw` writes every model response to `docs/raw/` so any reported
number traces back to output.

**The ablation.** Each model runs twice. `abstain_offered` includes `needs_evidence` in
the schema; `abstain_withheld` permits only `pass` and `fail`. The second is what a
system built to fill a dashboard looks like, where every cell must resolve. The
difference isolates how much of the false-green rate is an interface artifact rather than
a reasoning failure.

**Parsing policy.** A reply naming a pair but no permitted verdict yields *no
prediction*, and the metrics count it as an error. It is never coerced to a verdict,
because coercing to `needs_evidence` would turn formatting failures into abstentions and
flatter the false-green rate. The unparseable rate is reported separately. An unanswered
pair cannot be a false green, so every results table also reports coverage and the
false-green rate among answered pairs.

**Cost.** The free-tier studies cost nothing; at batch 12 the Study 1 subset is 12 calls
per model and condition and Study 2 is 24. Run `scripts/cost_probe.py` for list-price
arithmetic.

## Running on a free tier (no spend)

```bash
export GEMINI_API_KEY=...        # or GROQ_API_KEY
python3 scripts/run_free.py --provider gemini --model gemini-2.5-flash \
    --firms 0 --variant both     # anchor firm, both conditions: 24 calls

python3 scripts/run_free.py --provider gemini --model gemini-2.5-flash \
    --firms 5 --variant both     # ~4 days of free quota; re-run daily
```

The runner paces itself under the per-minute limit, backs off on a transient 429, stops
cleanly when the daily ceiling is reached, and resumes from a checkpoint. Re-issue the
same command each day to continue. It exits 0 on quota exhaustion, so it can be driven
from cron. Standard library only, no provider SDK.

**Source scoping.** Free tiers cap tokens per minute against the *largest single call*, and
sending all eleven exports on every call exceeds several free quotas. Scoping sends only the
exports an obligation's regime can be evaluated against, plus the roster. Every run in the
paper uses batches of 12 pairs.

Three safeguards stop this from manufacturing abstentions:

1. the prompt names the withheld exports and forbids inferring that an absent field lives
   in one the model cannot see;
2. an unclassified regime falls back to *all* sources, so the mapping can only narrow
   prompts for regimes it knows;
3. tests assert a correct model scores identically with scoping on and off, and that the
   pass-guessing baseline is still caught at false-green 1.000.

Shrinking the batch does not help. The obligation text is re-sent every call, so a
smaller batch *raises* the per-call floor.

## The task

Given a firm's source exports and a rulebook of cited obligations, return one verdict
per `(obligation, entity)` pair:

| Verdict | Meaning |
|---|---|
| `pass` | evaluated against present evidence, satisfied |
| `fail` | evaluated against present evidence, violated |
| `needs_evidence` | the evidence required to decide is **absent** |
| `unmonitored` | not assessable from this class of source data |

`needs_evidence` is the abstention, and it is a large share of the task by design: 201 of
the 221 pairs in the anchor firm, and 48.8% of the 1,481 pairs in the released set. A system that
maximises coverage by guessing scores worse than one that routes to human review.

## Why pass/fail scoring hides the failure

A system that answers `pass` everywhere:

```
violation recall        0.000
false alarm rate        0.000     <- perfect on compliant cases
FALSE GREEN RATE        1.000     <- reports all 201 unassessed duties as satisfied
```

It never raises a false alarm. Only the false-green rate separates it from a safe
system. This is the benchmark's argument in one table.

The converse also holds. A system that abstains everywhere scores 0.717 abstention F1
across the generated firms while detecting zero violations, so the metrics must be read
as a set. Neither the false-green rate nor abstention F1 is meaningful alone.

## Results (trivial baselines, 31 firms, 1,481 pairs, generator v2)

| system | false green | recall | precision | false alarm | abstention F1 |
|---|---|---|---|---|---|
| `always_pass` | 1.000 | 0.000 | — | 0.000 | 0.000 |
| `always_abstain` | 0.000 | 0.000 | — | 1.000 | 0.717 |
| `always_fail` | 0.000 | 1.000 | 0.170 | 1.000 | 0.000 |
| `oracle` | 0.000 | 1.000 | 1.000 | 0.000 | 1.000 |

Each rate is averaged over the firms in which it is defined. An earlier generator (v1)
produced labels its own records did not support; its figures (58,961 pairs) are withdrawn
and archived in `docs/study2_v1_invalid/`.

The oracle reaches 1.000 on every axis, so the task is solvable in principle and a low
score is a property of the system under test rather than of an ill-posed benchmark.

**Language-model results** are in `docs/PAPER.md` Section 8. On the anchor firm's 140-pair
declared subset, the six free models offered an abstention report 0.042 to 0.142 of
unassessable obligations as satisfied; a dashboard schema raises that to 0.175 to 0.525.
**Study 3**, preregistered in `docs/STUDY3_PREREGISTRATION.md` before any call, tests the
schema decomposition and adjacent-field substitution on twelve fresh firms rendered with and
without five misleading roster columns, across seven models from five developers. All four
declared hypotheses were confirmed (`docs/study3/results.json`; rerun with
`python3 scripts/score_study3.py`).

## Where the labels come from

**Generated firms (generator v2): by construction.** The generator decides each pair's
outcome first, then writes records that decide it:

- `planted_violation` the records show a breach
- `planted_control` the records show conformity, some placed exactly on the legal boundary
- `withheld_evidence` the export carrying the required information is not provided at all

It emits a pair only for the four rule families whose every listed input it renders, and
only where the rule applies. An independent checker written from the regulations, without
access to the generator or the labels (`labelcheck/`), reproduces all 1,680 labels of every
generated firm used in the paper (`python3 scripts/labelcheck_compare.py`). With
`GeneratorConfig(decoys=True)` (v3) the roster gains five adjacent-but-insufficient columns
and nothing else changes.

**Anchor firm: from a rule engine, audited.** The anchor firm's 221 expectations were
written as the acceptance gate for the author's company's compliance engine. Its withheld
labels were audited blind by two AI auditors (2 and 5 of 120 overturned, none in common),
and the second audited its violation labels, supporting five of the ten in the strict view;
see the paper, Section 6.1. No label was validated by an independent human
expert; `docs/expert_labelling/` is a blind kit for anyone who wants to.

## Contents

| Path | What |
|---|---|
| `nofalsegreen/schema.py` | verdicts, pairs, labels, firms |
| `nofalsegreen/metrics.py` | the metric suite, including the false-green rate |
| `nofalsegreen/generator.py` | seeded firm generator (v2; v3 adds decoy columns) |
| `nofalsegreen/study3.py`, `docs/STUDY3_PREREGISTRATION.md` | Study 3 firms, models and declaration |
| `labelcheck/` | independent reference checker and its interpretive choices |
| `nofalsegreen/rulebook.py` | rulebook loader |
| `nofalsegreen/northwind.py` | anchor-firm loader |
| `rulebook/rulebook.json` | 194 manifest obligations + 17 engine aliases/roll-ups, every one cited |
| `data/firms/northwind-robotics/` | anchor firm: 11 exports, 221 pinned expectations |
| `baselines/trivial.py` | floor and ceiling baselines |
| `tests/` | benchmark, harness and free-tier test suites |
| `docs/DATASHEET.md` | datasheet |

## Data statement

Every record is synthetic. No real person's data is present, and nothing is sampled
from a real employer. Names are drawn combinatorially from generic pools to make CSV
joins legible; they are not intended to depict anyone. The anchor firm's 11 exports
were hand-authored against a written test plan.

## Limitations

- **One jurisdiction, one domain.** United States employment-based immigration only.
- **The anchor firm is small** (12 workers) and its expectations were authored by the
  same people who built the reference engine it was first used to test. The generated
  firms exist to address the scale problem, not the independence problem.
- **Prompt v1.1 follows a disclosed pilot.** Prompt v1.0 was run on the same 140 pairs and
  found to be invalid: 30 pairs reached the model with no obligation text. The pilot's
  replies and scores are kept in `docs/pilot_v1.0/`. See paper Section 7.1.
- **Verdict granularity is coarse.** Real adjudication distinguishes a technical from
  a substantive defect; this benchmark does not.

## Licence

Code: Apache-2.0. Data and rulebook: CC-BY-4.0.
