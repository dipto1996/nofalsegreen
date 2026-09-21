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
python3 tests/test_benchmark.py
python3 scripts/sweep.py --firms 30
```

No dependencies beyond the Python 3.10+ standard library.

## The task

Given a firm's source exports and a rulebook of cited obligations, return one verdict
per `(obligation, entity)` pair:

| Verdict | Meaning |
|---|---|
| `pass` | evaluated against present evidence, satisfied |
| `fail` | evaluated against present evidence, violated |
| `needs_evidence` | the evidence required to decide is **absent** |
| `unmonitored` | not assessable from this class of source data |

`needs_evidence` is the abstention, and it is the **majority class**: 201 of the 221
pairs in the anchor firm, and 45.3% of pairs across the generated set. A system that
maximises coverage by guessing scores worse than one that routes to human review.

## Why accuracy hides the failure

A system that answers `pass` everywhere:

```
violation recall        0.000
false alarm rate        0.000     <- perfect on compliant cases
FALSE GREEN RATE        1.000     <- reports all 201 unassessed duties as satisfied
```

It never raises a false alarm. Only the false-green rate separates it from a safe
system. This is the benchmark's argument in one table.

The converse also holds. A system that abstains everywhere scores 0.632 abstention F1
across the generated firms while detecting zero violations, so the metrics must be read
as a set. Neither the false-green rate nor abstention F1 is meaningful alone.

## Results (trivial baselines, 31 firms, 57,701 pairs)

| system | false green | recall | precision | false alarm | abstention F1 |
|---|---|---|---|---|---|
| `always_pass` | **1.000** | 0.000 | 0.000 | 0.000 | 0.000 |
| `always_abstain` | 0.000 | 0.000 | 0.000 | 0.968 | 0.632 |
| `always_fail` | 0.000 | 1.000 | 0.119 | 0.968 | 0.000 |
| `oracle` | 0.000 | 1.000 | 1.000 | 0.000 | 1.000 |

The oracle reaches 1.000 on every axis, so the task is solvable in principle and a low
score is a property of the system under test rather than of an ill-posed benchmark.

**No language-model results are reported.** Those experiments have not been run.

## Ground truth by construction

Labels are not annotations of generated data. The generator decides each pair's
disposition **first**, then renders source records consistent with that decision:

- `planted_violation` a specific regulatory breach is injected
- `planted_control` a conforming case is injected, some placed exactly on the legal
  boundary to test whether a system flags on proximity rather than on the rule
- `withheld_evidence` a required input is omitted
- `not_applicable` the obligation does not attach to the entity

There is no annotation step, so there is no annotator disagreement to measure. Every
label is auditable back to the decision that produced it.

## Contents

| Path | What |
|---|---|
| `nofalsegreen/schema.py` | verdicts, pairs, labels, firms |
| `nofalsegreen/metrics.py` | the metric suite, including the false-green rate |
| `nofalsegreen/generator.py` | seeded firm generator |
| `nofalsegreen/rulebook.py` | rulebook loader |
| `nofalsegreen/northwind.py` | anchor-firm loader |
| `rulebook/rulebook.json` | 190 obligations, 10 regimes, every one with a citation |
| `data/firms/northwind-robotics/` | anchor firm: 11 exports, 221 pinned expectations |
| `baselines/trivial.py` | floor and ceiling baselines |
| `tests/test_benchmark.py` | 36 assertions |
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
- **The rulebook is 190 obligations,** extracted from a manifest whose own header
  claims 196. The 190 are the ones that appear as complete rule blocks with a citation
  and a required-evidence list. The discrepancy is unresolved and 190 is the figure
  used throughout.
- **Verdict granularity is coarse.** Real adjudication distinguishes a technical from
  a substantive defect; this benchmark does not.

## Licence

Code: Apache-2.0. Data and rulebook: CC-BY-4.0.
