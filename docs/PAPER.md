# No False Green: A Benchmark for Evidence-Aware Compliance Verdicts over Structured Employer Records

**Status of this draft: structural review.** Sections 1 through 7 and 10 through 11 are
written. Section 8.1 reports trivial-baseline results that have been run and verified.
Sections 8.2 and 9 are specified but empty: the tables, figure, and analyses are named and
their shape is fixed, with cells marked `[…]`, so the reporting structure is committed
before any number exists.

Every quantitative claim in the written sections is recomputed from the artifacts by
`scripts/verify_paper.py`, which currently confirms 103 of 103. Nothing marked `[TO RUN]`
may be filled by estimation.

Section 8.2 also states what will be reported if the empirical result is null, so the
paper's structure does not depend on the outcome being interesting.

---

## Abstract

Automated systems increasingly issue machine-generated compliance verdicts in regulated
domains, presenting an organisation's obligations as a dashboard of satisfied and
violated states. The evaluation of such systems measures accuracy on isolated
determinations, which leaves the deployment-critical error unmeasured: reporting an
obligation as *satisfied* when the evidence required to assess it was never present. We
call this a **false green**, and we argue it is categorically worse than a false alarm,
because a false alarm is corrected by review whereas a false green suppresses the review
that would correct it.

We introduce **No False Green**, a benchmark for evidence-aware compliance verdicts over
structured employer records in United States employment-based immigration. An instance is
a synthetic employer: a bundle of source exports paired with a rulebook of 190 citable
obligations across ten regulatory regimes. A system must return one of four verdicts for
each (obligation, entity) pair: `pass`, `fail`, `needs_evidence`, or `unmonitored`.
Ground truth is fixed by construction. A generator selects each pair's disposition first,
then renders source records consistent with that choice, so labels are not annotations of
data but the specification the data was rendered from.

The benchmark inverts the incentive structure of standard evaluation in one specific way:
correct abstention is the **majority class**, at 201 of 221 pairs in the hand-authored
anchor firm and 45.3% of 57,701 pairs across the released set. We report the false-green
rate alongside violation recall, false-alarm rate on planted controls, abstention
precision and recall, and a consistency check between a system's headline counts and its
own per-pair verdicts. Trivial baselines establish that these metrics are not
individually sufficient: a system answering `pass` everywhere attains a 0.000 false-alarm
rate and is indistinguishable from a safe system under accuracy-style scoring, while
scoring 1.000 on the false-green rate; conversely a system abstaining everywhere attains
0.632 abstention F1 while detecting no violations. An evidence-aware oracle attains 1.000
on every axis, establishing that the task is solvable and that low scores reflect the
system under test. Language-model baselines are specified in Section 7 and **have not yet
been run**. Because every instance is synthetic, the benchmark is released without the
confidentiality constraints that keep comparable compliance data unpublishable.

---

## 1. Introduction

A compliance dashboard makes a claim about the world with every cell it renders. When a
cell is green, it asserts that a specific legal obligation, attached to a specific worker
or filing, has been assessed and found satisfied. The assertion has a precondition that
the rendering does not express: that the evidence needed to perform the assessment was
present.

When the precondition fails, a system has three options. It can say so. It can decline to
render the cell. Or it can render the cell green. The third option is the one this paper
is about, and it is attractive to build for reasons that have nothing to do with
correctness: a dashboard of mostly-green cells looks like a working product, a mostly-grey
one looks broken, and the customer cannot distinguish "assessed and fine" from
"unassessed" without reading the underlying records themselves, which is the labour the
product exists to remove.

We call the third option a **false green** and make three claims about it.

**It is not symmetric with a false alarm.** A false alarm consumes reviewer time and is
extinguished by the review it triggers. A false green consumes nothing and triggers
nothing. It is self-concealing: the only signal that would surface it is the review that
it suppresses. In immigration compliance specifically, the obligations at issue carry
per-worker civil penalties and the enforcement mechanism is an audit that arrives without
warning, so a false green converts a curable gap into an uncurable finding.

**It is invisible to accuracy.** Violations are a minority class in real compliance data.
A system that answers `pass` on every pair whose evidence is absent therefore scores well
on any metric that averages over pairs, and scores *perfectly* on the compliant cases
that dominate the distribution. Section 8 shows this concretely: our `always_pass`
baseline attains a false-alarm rate of 0.000 across 31 firms.

**It is not measured.** Benchmarks in legal NLP evaluate reasoning and classification over
regulatory text and case law. Benchmarks for abstention evaluate free-text question
answering, where "insufficient evidence" is a property of a query. Neither addresses a
system reading an organisation's structured records and deciding, per obligation, whether
the records support a verdict at all.

We make three contributions.

1. **A task.** Verdicts over (obligation, entity) pairs with four states, where
   `needs_evidence` is a first-class output with its own correctness condition rather than
   a refusal to participate (Section 4).
2. **A benchmark.** A hand-authored anchor firm with 221 pinned expectations, a seeded
   generator producing unbounded additional firms with ground truth by construction, and a
   rulebook of 190 obligations each carrying its regulatory citation (Section 5).
3. **A metric suite** centred on the false-green rate, with baselines demonstrating that
   no single metric in the suite is sufficient alone (Sections 6 and 8).

The benchmark is fully synthetic, which is the reason it can exist. Compliance data
describing real employers is subject to attorney-client privilege and employee privacy
obligations that make publication impossible, which is why the gap this benchmark fills
has remained open.

---

## 2. Related work

Four literatures touch this problem. None occupies the position this benchmark takes, and
the reason in each case is a difference in what the system is given and what it must
return.

**Legal and regulatory NLP benchmarks.** Work in this area evaluates reasoning and
classification over *regulatory text*: statutes, case law, policy manuals. A system is
given a legal question or a document and asked to answer, classify, or retrieve. Our
input is an organisation's structured operational records, and our output is a verdict
per obligation about that organisation. A model that scores well on legal reasoning has
demonstrated nothing about whether it will report an unassessable duty as satisfied,
because the task never asks it to decide whether its evidence base is sufficient.

**Immigration-specific datasets.** Recent work covers question answering over
immigration policy sources, and reasoning over administrative appellate decisions
including adjudicator error. Both are beneficiary-side and text-side: the questions
concern what the law says or how a decision was reasoned. Employer-side obligations,
which is where the per-worker civil penalties and the audit exposure actually sit, are
absent. We are not aware of a public dataset of employer immigration-compliance records
with labelled obligation outcomes, and the reason is straightforward: real ones cannot
be published.

**Compliance benchmarks for AI systems.** A growing body of work assesses whether an AI
system complies with rules governing AI, including regulation-conformance assessment and
runtime governance-evidence sufficiency for agent audit trails. The direction of
assessment is inverted relative to ours. There, the system under test is the regulated
subject. Here, the system under test is the *assessor*, and the regulated subject is a
third party whose records it reads. The nearest neighbour in spirit is work asking
whether an evidence bundle suffices to reconstruct a decision; the difference is that we
ask whether a system correctly declines to issue a regulatory verdict about someone else.

**Abstention and selective prediction.** This is the closest literature and deserves the
most precision, because a reviewer will reasonably ask what is new.

Selective prediction gives a model the option to abstain and evaluates it on a
risk-coverage curve: coverage is a good to be maximised subject to a risk budget, and
abstention is a *cost* incurred to avoid error. Recent abstention benchmarks evaluate
whether models recognise unanswerable or underspecified questions, typically in free
text, where insufficiency is a property of the query and ground truth is established by
annotation.

Three things differ here.

First, abstention is not a cost. For 45.3% of pairs in our released set it is the
*correct output*, and it is actionable: `needs_evidence` names a document the firm must
produce. A system that trades abstention for coverage is not moving along a tradeoff
curve, it is producing wrong answers that happen to look like answers.

Second, insufficiency is a property of the evidence base rather than the query, so it is
determinable **by construction**. The generator withholds a required field and the label
follows mechanically. Free-text abstention benchmarks must annotate insufficiency, and
annotation of legal sufficiency is exactly the judgement call that makes such datasets
small and contestable.

Third, the error is directional in a way the risk-coverage framing does not capture.
Answering `fail` on an undecidable pair is wrong but triggers review. Answering `pass` is
wrong and *suppresses* review. Aggregating both into a single risk term hides the only
distinction that matters operationally, which is why we report the false-green rate as a
separate quantity rather than as one minus abstention recall.

**Aggregate consistency.** We are not aware of prior work measuring whether a system's
reported headline counts agree with its own per-item outputs. We include it as a metric
because we have observed the failure in deployed compliance dashboards, where a card and
its drilldown disagree; we flag it as the least-established axis in the suite.

**Positioning, stated plainly.** The contribution is not a new abstention algorithm and
not a theoretical result. It is a task formulation in which correct abstention is the
majority class and is fixed by construction, an instrument for measuring the directional
error that matters in deployment, and a releasable artifact in a domain where
releasability is the binding constraint. Section 10 states what this does not establish.

---

## 3. Background: the four states

The four-state vocabulary is not a design choice we made for the benchmark. It is forced
by the professional-responsibility constraints on any system that reports on legal
obligations without being counsel, and it was arrived at in a deployed product before it
was formalised here.

**`pass`.** A rule was evaluated against present evidence and the evidence satisfies it.
The claim must be time-bound, because a pass is only as current as the last data import.

**`fail`.** A rule was evaluated against present evidence and the evidence violates it.
The claim must be framed as a potential issue requiring review rather than as a legal
conclusion, because characterising conduct as unlawful is an act of legal judgement.

**`needs_evidence`.** The rule could not be evaluated because a required input is absent.
This is the state that most often collapses in practice, and the collapse has a direction:
a file that was never provided is reported as a file that is in order. The two are
opposite. A not-provided document is an **open gap** that counts against audit readiness.

**`unmonitored`.** The obligation is not assessable from this class of source data at all.
An employer export cannot evidence whether an adverse action was taken against a worker
while a contested tentative nonconfirmation was pending, because that fact lives in
conduct and not in a record the employer exports. Such an obligation must remain visible
as unmonitored. Silent omission is itself a false green.

The distinction between `needs_evidence` and `unmonitored` matters operationally: the
first is actionable by the firm (provide the document), the second is not (no document
exists to provide), and conflating them either sends firms on impossible errands or hides
real gaps.

---

## 4. The task

An instance is a firm $F = (S, E, R, a)$ where $S$ is a set of source exports, $E$ a set
of entities, $R$ a rulebook, and $a$ a pinned evaluation date.

An **entity** $e \in E$ has a type: `worker`, `lca`, `worksite`, `wage_cohort`, or
`employer`. Entity type matters because obligations attach at different granularities: an
I-9 timeliness duty attaches to a worker, a wage-floor duty to a filing, a prevailing-wage
comparison to a cohort defined by occupation, level, and location, and a site-visit
readiness duty to the employer as a whole.

An **obligation** $r \in R$ carries a regulatory citation, the entity type it attaches to,
and a set $\mathrm{req}(r)$ of source fields that must be present for the obligation to be
decidable. This last component is what makes `needs_evidence` computable rather than a
judgement call: if a field in $\mathrm{req}(r)$ is absent from $S$ for entity $e$, the pair
is not decidable, and any verdict other than `needs_evidence` is wrong regardless of
whether the underlying situation happens to be compliant.

A **pair** is $(r, e)$ where $e$'s type matches $r$'s attachment. The prediction target is
a verdict $v \in \{\texttt{pass}, \texttt{fail}, \texttt{needs\_evidence},
\texttt{unmonitored}\}$, optionally with evidence pointers and a citation.

All date-relative obligations evaluate against $a$ rather than against the current date, so
planted expiry windows remain valid indefinitely. The anchor firm pins $a$ = 2026-06-29.

**Scoring rule.** A pair with no prediction is counted as an error rather than skipped. A
system cannot raise its score by declining to answer the pairs it finds hard. This is
enforced in the harness and tested.

---

## 5. Benchmark construction

### 5.1 The rulebook

The rulebook contains 190 obligations across ten regimes: I-9 and E-Verify (26), Labor
Condition Application (23), Public Access File (15), wage and prevailing wage (21), H-1B
status (16), I-129 supplement (11), L-1 (21), F-1 OPT and STEM OPT (15), site-visit
readiness (14), and cross-cutting deadlines and penalties (28).

Each obligation carries the check it performs, its regulatory citation, and its required
evidence. The citations had previously been through a verification pass in which incorrect
citations and thresholds were corrected inline against primary sources; we extracted the
rulebook programmatically from that manifest rather than retyping it, so the benchmark's
citations are traceable to a source document rather than to our own recollection.

One honest discrepancy: the source manifest's header states 196 rules, while 190 appear as
complete rule blocks carrying both a citation and a required-evidence list. We use 190
throughout and do not reconcile the difference.

### 5.2 The anchor firm

The anchor firm is a synthetic employer of twelve workers, nine on H-1B status and three
United States citizens, operating from two worksites, with eleven source exports totalling
93 data rows: HR roster, case-management export, certified LCAs, I-9 records, E-Verify
cases, payroll register, RFE and NOID cases, cap cases, green-card cases, PERM recruitment
tracker, and benefits census.

Each worker exercises one planted regulatory mechanism. The design is one clean plant per
persona so that a missed finding localises to a mechanism rather than to an interaction.
Representative plants:

| Mechanism | Planted signal |
|---|---|
| I-9 Section 2 timeliness | Section 2 completed 8 business days after start, against a 3-day limit |
| Reverification deadline | List A document expiring 14 days after the pinned date |
| E-Verify TNC window | Notice delivered, no employee decision recorded, well past the response window |
| LCA expiration | Certified period ending 4 days after the pinned date |
| Required wage, greater-of | Salary equals the certified rate but falls below the prevailing wage |
| Material change, occupation | Filing carries an individual-contributor occupation code against a management title |
| Material change, worksite | Roster location differs from the filing's stated area of intended employment |
| Petition expiry | Validity ending 21 days after the pinned date |

The firm also carries **clean controls**: one H-1B worker whose records conform on every
dimension, and three United States citizens outside H-1B scope. A finding on a control is
a false alarm the harness scores.

Its expectation set contains 221 pairs: 20 planted violations and 201 evidence requests.
The 201 arise because most obligations in this domain require evidence an employer export
does not contain. A certified LCA does not evidence that the required notice was posted; a
roster does not evidence which document a worker presented. The honest output for such a
pair is an evidence request, and the fact that these outnumber confirmed violations
tenfold is the empirical claim underlying the benchmark's design.

### 5.3 The generator

The anchor firm is too small to support a confidence interval on any system's error rate.
The generator addresses this.

Its central property is that **labels precede data**. For each applicable (obligation,
entity) pair the generator draws a disposition:

- `planted_violation`, and a specific regulatory breach is rendered into the records;
- `planted_control`, and a conforming case is rendered, with a configurable share placed
  exactly on the legal boundary (I-9 Section 2 on business day three of three, an LCA
  expiring on day eight of a seven-day window, a salary equal to the floor) to test whether
  a system flags on proximity rather than on the rule;
- `withheld_evidence`, and a required input is omitted;
- `not_applicable`, for obligations with no expression in export data.

Only after the full disposition map is drawn are the CSVs written. There is consequently no
annotation step and no annotator disagreement to report, and each label is auditable back
to the decision that produced it. The cost of this design is that the generator can only
express mechanisms we have implemented renderers for; unrendered obligations reach the
label set as withheld-evidence or not-applicable, which is honest but limits the diversity
of planted violations relative to the hand-authored firm.

Generation is deterministic in the seed. Two runs of the same seed produce byte-identical
label sets and firm metadata, which the test suite asserts.

### 5.4 Released scale

| | Value |
|---|---|
| Firms | 31 (1 anchor + 30 generated at seeds 1-30) |
| Pairs | 57,701 |
| Withheld-evidence pairs | 26,115 (45.3%) |
| Planted violations | 6,890 |
| Obligations | 190 |

Additional firms are available at any seed.

---

## 6. Metrics

Let $T$ be ground truth and $P$ predictions over pairs.

**Violation recall.** Of pairs labelled `fail`, the share predicted `fail`. A missed
violation is the failure the domain treats as unforgivable, so this is reported first.

**Violation precision** and **false-alarm rate.** Precision over `fail` predictions, and
separately the share of `planted_control` pairs on which a system raised any alarm. The
second is reported separately because controls are the pairs where a false alarm is
unambiguously an error.

**False-green rate.** The headline metric:

$$\mathrm{FGR} = \frac{|\{p : T(p) = \texttt{needs\_evidence} \wedge P(p) = \texttt{pass}\}|}{|\{p : T(p) = \texttt{needs\_evidence}\}|}$$

The share of undecidable pairs a system reports as satisfied. Note what it is not: it is
not one minus abstention recall. A system that answers `fail` on an undecidable pair is
wrong, but it is wrong in a direction that triggers review. Only `pass` suppresses review,
so only `pass` counts here.

**Abstention precision and recall,** treating `needs_evidence` as a class. Precision
matters because a system can drive the false-green rate to zero by abstaining everywhere,
which the baselines demonstrate.

**Evidence-pointer accuracy.** Among pairs a system got right and for which ground truth
records the relevant fields, the share where the system's cited evidence intersects them.
A correct verdict reached by citing the wrong record is not a reliable verdict.

**Consistency drift.** Mean absolute relative disagreement between the counts a system
displays for a surface and the per-pair verdicts the same system emitted. A card reading
twelve above a drilldown returning three is internally inconsistent regardless of which
number is correct. This axis exists because we have observed the failure in deployed
dashboards and are not aware of it being measured elsewhere.

**Reporting requirement.** The false-green rate must be reported alongside violation
recall. Neither is meaningful alone, and Section 8 shows why.

---

## 7. Baselines

**Trivial baselines (run).** `always_pass` answers `pass` everywhere and is maximally
unsafe. `always_abstain` answers `needs_evidence` everywhere: safe but useless.
`always_fail` flags everything. `oracle` reads the label basis and decides exactly when
evidence is present; it is not a competitive system but an upper bound establishing that
the task is solvable.

**Language-model baselines `[TO RUN]`.** These experiments **have not yet been run**. The
harness is implemented, tested against mock models with known failure signatures, and
dry-run end to end; only the API calls remain. The protocol is frozen in code (`baselines/prompts.py`, `PROMPT_VERSION` 1.0.0)
so that the reported result cannot be a post-hoc selection of prompt:

- *Prompt.* Per firm, the source exports verbatim as CSV, the obligations needed by the
  batch with their citations and required-evidence lists, and the pairs to decide.
  Verdicts are returned one per line as `pair_id`, verdict, evidence field. The
  evaluation date is pinned in the prompt with an explicit instruction not to use the
  real current date, since every deadline rule depends on it.
- *Output schema ablation.* Each model is run twice. In `abstain_offered` the schema
  includes `needs_evidence` and states the `pass`-versus-`needs_evidence` distinction
  explicitly. In `abstain_withheld` only `pass` and `fail` are permitted. The second
  condition is not a strawman: it is what a system built to fill a dashboard looks like,
  where every cell must resolve and there is no representation for "we could not tell".
  The difference isolates how much of the false-green rate is an interface artifact
  rather than a reasoning failure. We separately count **off-schema** replies, where a
  model abstains despite the schema forbidding it, which we read as a finding rather
  than an error.
- *Models.* Eight to twelve current instruction-tuned models across providers and sizes.
- *Aggregation.* Scored per firm, then averaged across firms with standard deviation.
  Pairs within a firm share source records and are not independent.

**Parsing policy, which is a scoring decision.** A reply line naming a pair but no
permitted verdict yields **no prediction**, and the metric module counts the pair as an
error. It is never coerced. Coercing to `needs_evidence` would convert a model's
formatting failures into abstentions and flatter its false-green rate; coercing to `pass`
would do the reverse. Either would make the headline number a function of our parser. We
report the unparseable rate separately so a reader can see how much of a score is
formatting. The test suite asserts that a model emitting no valid verdicts earns zero on
both the false-green rate and violation recall, so a formatting failure can never be
mistaken for safety.

**Measured cost.** The full sweep is 1,446 API calls per model per variant, about 2.55M
input and 1.73M output tokens over 31 firms at batch size 40. At list prices that is
roughly \$9 to \$170 per model per variant depending on tier, and \$180 to \$3,400 for
ten models across both variants. Prompt caching on the sources-and-rulebook prefix should
reduce input cost materially, since every batch within a firm re-sends the same prefix.
The anchor firm alone costs under \$1.50 on the most expensive tier, which is the
recommended first run.

### 7.1 Running on free API tiers

We report results obtained entirely on providers' free tiers, which constrains the
experiment in two ways that must be stated because both affect the measurement.

**Source scoping.** Free tiers cap tokens per minute, and the cap is checked against the
largest single call, not the average. Sending all eleven exports on every call puts the
anchor firm's largest call at 11,306 tokens at batch size 20, and 15,067 at batch size 40,
which exceeds several free per-minute quotas outright. We therefore send only the exports
whose regime an obligation can be evaluated against, with the HR roster always included
because every other source joins to it. This reduces the largest call to 9,750 tokens at
batch size 20. Note that shrinking the batch does not help: the obligation text is
re-sent with every call, so a smaller batch raises the per-call floor rather than
lowering it.

Scoping is a change to the prompt, so we treat it as part of the protocol rather than an
implementation detail. Two safeguards keep it from manufacturing abstentions. First, the
prompt names the exports that were withheld and instructs the model not to infer that an
absent field exists in an export it cannot see; a model that abstained merely because it
suspected hidden data would otherwise inflate the apparent abstention rate. Second, an
obligation whose regime is unclassified falls back to all sources, so the mapping can only
narrow prompts for regimes it knows about and can never hide data from an obligation it
has not classified. The test suite asserts that a correct model scores identically with
scoping on and off, and that the pass-guessing baseline is still caught at a false-green
rate of 1.000 under scoping.

**Model coverage, and the limitation it creates.** Free tiers offer a narrower and
generally smaller set of models than the specification in Section 7 assumes. Any result we
obtain this way therefore speaks to the models we could reach, not to the frontier. We
state the models and their published quotas alongside every number and do not generalise
beyond them. This is a genuine weakness of the study rather than a presentational choice,
and it is repeated in Section 10.

**Throughput.** At a representative free quota of 10 requests per minute and 250 per day,
the anchor firm across both ablation conditions is 24 calls, or about a tenth of one day.
Adding five generated firms is roughly four days of quota. The runner paces itself under
the per-minute limit, backs off on a transient rate-limit response, stops cleanly when the
daily ceiling is reached, and resumes from a checkpoint, so a multi-day run is a matter of
re-issuing the same command. Every model response is retained so that any reported number
can be traced back to output.

**A baseline we deliberately exclude.** The anchor firm's expectation set originated as
the acceptance gate for a commercial compliance engine. That engine would score near
ceiling on this firm for a reason that has nothing to do with capability: the expectations
and the engine were developed against each other. Reporting it as a baseline would be
misleading, and we do not.

---

## 8. Results

### 8.1 Trivial baselines

**Table 1 — trivial baselines.** Across 31 firms and 57,701 pairs, aggregated per firm
then averaged. Reproduced by `python3 scripts/sweep.py --firms 30`.

| System | False green | Violation recall | Precision | False alarm | Abstention F1 |
|---|---|---|---|---|---|
| `always_pass` | **1.000** | 0.000 | 0.000 | **0.000** | 0.000 |
| `always_abstain` | 0.000 | 0.000 | 0.000 | 0.968 | **0.632** |
| `always_fail` | 0.000 | **1.000** | 0.119 | 0.968 | 0.000 |
| `oracle` | 0.000 | 1.000 | 1.000 | 0.000 | 1.000 |

Three readings.

**The false-green rate is not redundant.** `always_pass` attains a false-alarm rate of
0.000, the best possible score on compliant cases. Under any metric that rewards not
crying wolf, it is indistinguishable from a careful system. It is in fact the worst
possible system for deployment, reporting all 26,115 undecidable pairs as satisfied. Only
the false-green rate separates them. On the anchor firm alone the separation is starker:
`always_pass` reports all 201 unassessed obligations as satisfied while raising zero false
alarms.

**The false-green rate is also not sufficient.** `always_abstain` attains 0.000 on it
while detecting no violations, and reaches 0.632 abstention F1. On the anchor firm, whose
expectation set declares no control pairs, it reaches 0.953 abstention F1 while being
useless. Abstention scores are therefore gameable in isolation, which is why the suite
must be reported jointly.

**The task is solvable.** The oracle reaches 1.000 on every axis. A system scoring poorly
is exhibiting a property of itself, not of an ill-posed benchmark.

### 8.2 Language-model results

`[TO RUN]` — no language-model experiments have been conducted. Section 7 fixes the
protocol in advance so that the reported result is not a post-hoc selection. The tables
below are the ones that will be filled, specified now so the structure cannot be chosen
after seeing the numbers.

**Table 2 — main result, `abstain_offered`.** One row per model. Every cell is a mean
across firms with standard deviation; the unparseable column guards the rest.

<!-- BEGIN GENERATED: table2-main -->
| Model | False green | Recall | Precision | False alarm | Abst. P | Abst. R | Abst. F1 | Unparse. |
|---|---|---|---|---|---|---|---|---|
| `[TO RUN]` | `[…]` | `[…]` | `[…]` | `[…]` | `[…]` | `[…]` | `[…]` | `[…]` |
| `always_pass` (ref) | 1.000 | 0.000 | 0.000 | 0.000 | 0.000 | — | 0.000 | 0.000 |
| `oracle` (ref) | 0.000 | 1.000 | 1.000 | 0.000 | 0.000 | — | 1.000 | 0.000 |
<!-- END GENERATED: table2-main -->

The trivial baselines are repeated in-table as reference rows, so a reader sees
immediately where each model sits between the unsafe floor and the attainable ceiling.

**Table 3 — the schema ablation.** The paper's most informative experiment. Same models,
both conditions, difference reported per model.

<!-- BEGIN GENERATED: table3-ablation -->
| Model | FGR, abstention offered | FGR, abstention withheld | Δ | Off-schema abstentions |
|---|---|---|---|---|
| `[TO RUN]` | `[…]` | `[…]` | `[…]` | `[n of N]` |
<!-- END GENERATED: table3-ablation -->

The off-schema column counts pairs where a model returned `needs_evidence` although the
schema permitted only `pass` and `fail`. A model doing this frequently is refusing a
schema that cannot express what it observed, which we would report as a finding about the
interface rather than an instruction-following failure.

**Table 4 — false-green rate by regime.** One row per regulatory regime, one column per
model. This is where the document-versus-field asymmetry in Section 9 is tested.

<!-- BEGIN GENERATED: table4-regime -->
| Regime | `[TO RUN]` |
|---|---|
| *ten rows, one per regime, one column per model* | `[…]` |
<!-- END GENERATED: table4-regime -->

**Table 5 — near-miss controls.** For conforming cases placed exactly on the legal
boundary, the rate at which each model raises an alarm, against its rate on
comfortably-conforming controls. A gap indicates proximity heuristics rather than rule
application.

**Figure 1 — the separation plot.** Violation recall on one axis, false-green rate on the
other, one point per model, with the four trivial baselines marking the corners. The
argument of the paper is that real systems cluster where recall looks acceptable and the
false-green rate does not, and this figure either shows that or refutes it.

**What we will report if the result is null.** If the models tested abstain correctly and
the false-green rate is uniformly low, we will say so and the paper's claim narrows to the
task, the construction method, and the instrument, with the empirical section reporting a
negative result. The benchmark is publishable either way, and committing to this in
advance is what makes the eventual number credible.

---

## 9. Analysis

`[TO RUN — depends on 8.2]` The analyses this section will perform, specified now. Each
names the artifact that answers it, so none can be quietly dropped if inconvenient.

**Which failure dominates, per model.** Error decomposed into missed violations, false
greens, false alarms, and unparseable output, as a stacked proportion. A model whose error
is mostly unparseable output is making a formatting claim, not a reasoning one, and must
be discussed separately.

**Where abstention is hardest.** From Table 4. The hypothesis, stated before the run:
obligations whose required evidence is a *field* (an I-94 expiry, a first-pay date) will
show a lower false-green rate than those whose required evidence is a *document* (a
posting notice, a public access file). Absence of a field is visible as an empty column;
absence of a document is visible only as the absence of a record that was never expected
to exist, which is a harder inference. If the asymmetry holds it is the most actionable
finding for system builders, because it says where to put human review. If it does not
hold, we report that the failure is uniform across evidence classes, which is also useful
and which we will not suppress.

**Near-miss controls.** From Table 5. Distinguishes rule application from proximity
heuristics.

**The schema ablation.** From Table 3. A large reduction in false greens when abstention
is offered locates the problem in interface design, which is an actionable finding for
anyone shipping a compliance dashboard. A small reduction locates it in the models, which
is a harder problem and a more important result. We commit to reporting whichever occurs.

**Evidence-pointer quality.** Among pairs answered correctly, how often the cited evidence
field is one ground truth records as relevant. A correct verdict reached by pointing at the
wrong record is not a reliable verdict, and at scale it is indistinguishable from a guess.

**Consistency drift.** Reported if a system under test exposes headline counts. Flagged in
Section 6 as the least-established axis in the suite, and it will be reported as
exploratory rather than as a headline.

**Qualitative failure cases.** Three to five verbatim excerpts from retained raw output
showing a model asserting a verdict the records cannot support. These are the most
persuasive evidence in the paper for a reader who does not care about aggregate rates, and
they are available because every response is retained.

---

## 10. Limitations

**One jurisdiction, one domain.** United States employment-based immigration. We claim the
false-green failure generalises to other regulated domains and claim nothing about whether
performance does.

**The anchor firm is small and not independent.** Twelve workers. Its expectations were
hand-authored by the same author who built the engine it was first used to test. The
generated firms address scale, not independence; a genuinely independent labelling of the
anchor firm by practising immigration counsel is the obvious next step and has not been
done.

**The generator's violations are less diverse than the anchor firm's.** It renders only
mechanisms we implemented renderers for. Unrendered obligations land as withheld-evidence
or not-applicable, so the generated planted-violation set is narrower than the manifest
would allow.

**Synthetic data does not exercise extraction.** Real deployments read records from
scanned documents through OCR, where a field can be invented from an adjacent label rather
than merely absent. This benchmark starts from clean structured exports and therefore
isolates the verdict layer, which is a deliberate scope choice and also a gap.

**Verdict granularity is coarse.** Real adjudication distinguishes technical from
substantive defects and admits cure periods. Four states do not capture that.

**The rulebook count is unreconciled.** 190 extracted against a claimed 196.

**Model coverage is limited to free API tiers, and that limit is severe.** The study was
run without a compute budget, so the models evaluated are those reachable on providers'
free tiers rather than a representative sample of the frontier. This is not a mild caveat.
On a screening run of the 15 free chat models that met the task's context requirement,
**only 6 returned a usable answer to a two-pair request**: 5 were rate-limited, 2 refused
with a permissions error, 1 returned an upstream provider failure, and 1 returned an empty
completion. Which models are evaluable on a given day is therefore decided by provider
capacity rather than by our selection, and the model set in any free-tier result is
partly an artifact of when it was run. We report the screening outcome alongside results
so the composition of the model set is visible. Whether the largest current proprietary
models exhibit the same false-green behaviour is untested, and it is the single most
valuable extension of this work.

**Prompts send only regime-relevant exports.** Required by free per-minute token quotas
(Section 7.1). Safeguarded by disclosing withheld exports in the prompt, forbidding
inference about unseen data, falling back to all sources for unclassified regimes, and
asserting in tests that a correct model scores identically either way. It remains a
deviation from sending a firm's complete record.

**No human baseline.** We do not know what false-green rate a competent paralegal or
attorney would attain on this task, which would be the most informative reference point of
all.

---

## 11. Ethics and release

**No real personal data.** Every record is synthetic. Names are combinatorial draws from
generic pools chosen to make joins legible, not to depict anyone.

**Not legal advice, and not a compliance product.** The rulebook is a research artifact. A
high score does not establish that a system may be relied upon by an employer. We state
this because the plausible misuse of this benchmark is precisely a vendor citing a score as
evidence of fitness.

**Not a training set.** Fitting a model to these labels measures nothing, since the labels
are the generator's specification.

**Dual use.** A benchmark measuring how often systems report unassessed obligations as
satisfied could in principle guide a vendor toward suppressing the measurement rather than
the failure. We judge the risk low and the transparency benefit high: the failure mode is
already occurring and is currently unmeasured.

**Release.** Code under Apache-2.0, data and rulebook under CC-BY-4.0, with a datasheet.
The harness requires only the Python standard library and runs offline.

---

## Appendix A: Reproduction

```bash
python3 -m nofalsegreen.cli describe                                  # rulebook + anchor stats
python3 -m nofalsegreen.cli score --firm northwind --baseline always_pass
python3 -m nofalsegreen.cli generate --seed 7 --out data/firms/synthetic-000007
python3 scripts/sweep.py --firms 30                                   # reproduces Table 1
python3 tests/test_benchmark.py                                       # 36 assertions
```

## Appendix B: Prompt and protocol

The prompts are frozen in `baselines/prompts.py` at `PROMPT_VERSION` 1.0.0 and reproduced
verbatim below in both ablation conditions, since a benchmark whose prompt is not
published is not reproducible.

`[INSERT: system prompt, abstain_offered]`

`[INSERT: system prompt, abstain_withheld]`

`[INSERT: one complete user prompt for a single batch, elided in the middle]`

Changing any of these text blocks changes the benchmark. Any edit bumps
`PROMPT_VERSION`, and results carry the version they were produced under.
