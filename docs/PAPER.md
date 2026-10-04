# No False Green: A Benchmark for Evidence-Aware Compliance Verdicts over Structured Employer Records

Diptopal Roy, Settle AI Inc. (diptopal@joinsettle.info). See *Competing interests*, Section 12.

---

## Abstract

Automated systems increasingly present an organisation's regulatory obligations as a
dashboard of satisfied and violated states. Their evaluation measures accuracy on
individual determinations, which leaves one deployment-critical error unmeasured:
reporting an obligation as *satisfied* when the evidence needed to assess it was never
present. We call this a **false green**. It is worse than a false alarm in one specific
way: a false alarm prompts the review that corrects it, while a false green removes the
reason to review.

We introduce **No False Green**, a benchmark for evidence-aware compliance verdicts over
structured employer records in United States employment-based immigration. A system
receives an employer's data exports and a rulebook of citable obligations, and returns one
of four verdicts per (obligation, entity) pair: `pass`, `fail`, `needs_evidence`, or
`unmonitored`. The benchmark has two parts. A hand-authored anchor firm (221 pairs across
eight regulatory regimes) carries labels from a rule engine, audited blind for whether the
exports contain the evidence each label assumes. Generated firms carry labels fixed by
construction: the generator chooses each pair's outcome and then writes records that decide
it, including conforming cases placed exactly on the legal boundary. Trivial baselines show
that no single metric suffices. Answering `pass` everywhere raises no false alarm while
calling every unassessable obligation satisfied, and abstaining everywhere scores well on
abstention while detecting nothing.

We evaluate thirteen language models from eight developers. On 140 pairs of the anchor firm,
offered an abstention, models report 0.042 to 0.153 of unassessable obligations as satisfied
while detecting 0.050 to 0.500 of its violations. A dashboard-style schema permitting only
`pass` and `fail` raises that rate to 0.131 to 0.589, significantly for eight of the nine
models we tested for it after correction for multiple comparisons.

Two explanations of that effect were formed after seeing results, so we tested them in a
preregistered study on twelve fresh generated firms, each rendered with and without
**adjacent columns**: populated fields that sit beside the missing evidence without being it,
such as an I-9 status of "Complete". Pooled over seven models from five developers, all four
declared hypotheses were confirmed (Holm-adjusted p = 0.002 each). Removing every
non-committal verdict raises the false-green rate by 0.259; redefining `pass` from "the
required evidence is present and satisfies the obligation" to "the obligation is satisfied"
raises it by a further 0.084; and adjacent columns raise it by 0.427 under the dashboard
schema and by 0.217 even under the recommended one. On I-9 obligations, models almost never
call a missing record compliant (0.000 to 0.023 across schemas) until an adjacent column is
present. The labels of every generated firm agree with an independent checker written from
the regulations; the anchor firm's labels were audited by two blind AI auditors, and no
attorney has validated them.

Every instance is synthetic, so the benchmark is released without the confidentiality
constraints that keep comparable compliance data unpublishable.

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
it suppresses. In immigration compliance the cost is concrete. Form I-9 paperwork
violations are penalised per form (8 C.F.R. 274a.10(b)(2)) and LCA violations per violation
(20 C.F.R. 655.810(b)). A Form I-9 inspection gives the employer at least three business
days' notice (8 C.F.R. 274a.2(b)(2)(ii)), and technical or procedural failures can be
corrected within ten business days of notification (8 U.S.C. 1324a(b)(6)(B)), but
substantive violations cannot, and USCIS FDNS site visits are generally unannounced. A
gap found before an inspection can often be remedied; the same gap found during one
becomes a finding. A false green is what keeps it from being found before.

**It is invisible to pass/fail scoring.** An evaluation that labels every pair either
compliant or violated has no category for "the evidence was not there", so missing
evidence is scored as compliant, and a system that answers `pass` whenever evidence is
absent is never penalised. Violations are also a minority class, so on compliant cases
the same system scores perfectly. Section 8 shows the second point concretely: our
`always_pass` baseline raises no false alarm in any of the 24 firms that carry conforming
controls.

**It is barely measured.** Benchmarks in legal NLP evaluate reasoning and classification
over regulatory text and case law (Guha et al., 2023). Most abstention benchmarks evaluate
free-text question answering. Recent work has begun to score evidence sufficiency and the
overclaiming direction directly, in retrieval-augmented generation (Joren et al., 2024),
claim verification over databases (Theologitis et al., 2026), and agent governance and
authorisation-limited evidence (Solozobov, 2026; Tallam, 2026). None of it evaluates a
system reading a third-party employer's structured records and deciding, per legal
obligation, whether the records support a verdict at all, in a domain where correct
abstention is a large share of the task by design. Section 2 sets out how close each comes.

We make five contributions.

1. **A task.** Verdicts over (obligation, entity) pairs with four states, where
   `needs_evidence` is a first-class output with its own correctness condition rather than
   a refusal to participate (Section 4).
2. **A benchmark.** A hand-authored anchor firm with 221 audited expectations across eight
   regimes; a seeded generator producing arbitrarily many (if deliberately narrow) firms
   whose labels are fixed by construction, including conforming cases on the legal
   boundary; and a rulebook of 194 obligations, each with its regulatory citation
   (Section 5).
3. **A metric suite** centred on the false-green rate, with baselines demonstrating that
   no single metric in the suite is sufficient alone (Sections 6 and 8).
4. **An empirical study** of thirteen language models, including a preregistered
   confirmatory study on fresh firms. It separates the effect of a dashboard-style output
   schema into an abstention effect and a definition effect, and shows that adjacent-field
   substitution, a populated column read as the missing evidence beside it, is a
   mechanism of false greens rather than an interpretation (Sections 8 and 9).
5. **Label validation without an annotator pool.** Every generated label is reproduced by a
   checker written independently from the regulations, and the anchor firm's labels by two
   blind audits, whose disagreements are published pair by pair (Sections 5.3 and 6.1).

The benchmark is fully synthetic, which is the reason it can exist. Compliance data
describing real employers is subject to attorney-client privilege and employee privacy
obligations that make publication impossible, which is why the gap this benchmark fills
has remained open.

**Terms.** *Form I-9*: the employment-eligibility verification form every US employer
completes for each hire; *Section 1* is completed by the employee, *Section 2* by the
employer after examining documents, and *Supplement B* records reverification when
temporary work authorisation expires. *E-Verify*: the federal electronic eligibility check;
a *TNC* (tentative nonconfirmation, now called a mismatch) requires notice and a response
window. *H-1B*: the temporary specialty-occupation visa. *LCA*: the Labor Condition
Application an employer files with the Department of Labor before an H-1B petition,
attesting to wages and conditions; its *PAF* (public access file) must hold supporting
documents. *Prevailing wage* and *actual wage*: the two floors of the LCA required wage,
which is the greater of them. *SOC*: Standard Occupational Classification code. *I-94*: the
arrival-departure record. *EAD*: employment authorisation document. *RFE* and *NOID*:
USCIS requests for evidence and notices of intent to deny, each with a response deadline.
*FDNS*: the USCIS Fraud Detection and National Security directorate, which conducts site
visits. *AAO*: the USCIS Administrative Appeals Office.

---

## 2. Related work

Three recent benchmarks come closer to this one than its framing might suggest; we say
where. In each case the difference lies in what the system is given, what it must return,
and how the label is established.

**Legal NLP and legal hallucination.** LegalBench (Guha et al., 2023), LexGLUE (Chalkidis
et al., 2022), CaseHOLD (Zheng et al., 2021), CUAD (Hendrycks et al., 2021) and LawBench
(Fei et al., 2024) evaluate reasoning over *legal text*: a system is given a question or a
document and answers, classifies or retrieves. None asks whether the evidence base is
sufficient for a verdict, so a strong score says nothing about whether a model will report
an unassessable duty as satisfied. The legal hallucination literature is closer in
motivation: Dahl et al. (2024) find hallucination rates of 58% to 88% on verifiable
questions about federal cases, and Magesh et al. (2025), in a preregistered study, find
commercial legal research tools hallucinate more than their vendors claim. Both measure
unsupported output about the law; we measure unsupported output about a regulated party,
where the missing support is a record rather than a precedent.

**Immigration datasets.** ImmigrationQA has 17,058 question-answer pairs from USCIS and
8 CFR sources (Shportun, 2026). ImmigrationReason structures 12,375 Administrative Appeals
Office decisions with per-criterion evidence-sufficiency findings (Afsharrad and Mousavi,
2026); its sufficiency labels are the adjudicator's, about a petition record the dataset
does not contain. Both are text-side and petitioner-side. We know of no public dataset of
employer immigration-compliance records with labelled outcomes, because real ones cannot be
published.

**Compliance checking.** Automated checking predates language models, in construction
(Zhang and El-Gohary, 2016) and data protection (Amaral et al., 2022; Ravichander et al.,
2019). Among LLM benchmarks, COMPL-AI makes the AI system the regulated subject (Guldimann
et al., 2024), while HSE-Bench (Wang et al., 2025), Principle-Bench (Sarkar, 2026) and
ReguSim (Luo et al., 2026) make it the assessor, as here; ReguSim also takes records as
input. None gives insufficiency of the record its own correct label.

**The nearest neighbours.** Two recent benchmarks do. DEMM-Bench asks whether
agent-runtime records suffice to reconstruct a decision, labels by construction, and
reports an overclaim rate (Solozobov, 2026); its "container fallacy", treating the presence
of an evidence container as sufficiency, is close to our adjacent-field substitution.
Partial Evidence Bench places material evidence outside an agent's authorisation boundary
and scores *unsafe completeness*, finding that explicit fail-and-report behaviour removes it
without collapsing into trivial abstention (Tallam, 2026), which is our argument that the
false-green and abstention rates must be read together. We differ in three respects: the
subject is a third-party employer and the output a regulatory verdict per (obligation,
entity) pair; insufficiency is a property of what the employer's exports contain, not of
an agent's permissions; and the assessment is against cited regulations. We do not claim
the directional, construction-labelled framing as new.

**Abstention and selective prediction.** From the reject option (Chow, 1970) through
selective classification (El-Yaniv and Wiener, 2010; Geifman and El-Yaniv, 2017),
abstention is a *cost* traded against coverage. For language models it is evaluated mostly
on questions: SQuAD 2.0 (Rajpurkar et al., 2018), SelfAware (Yin et al., 2023) and
AbstentionBench, which finds that scaling helps little and reasoning fine-tuning degrades
abstention (Kirichenko et al., 2025); Wen et al. (2025) survey the area, and Kadavath et
al. (2022) show models can learn to predict whether they know an answer. Joren et al.
(2024) come nearest: they define whether a retrieved context is *sufficient* and find that
strong models often answer wrongly rather than abstain when it is not. Hallucination
benchmarks against world knowledge (Lin et al., 2022) or a knowledge source (Min et al.,
2023) have no abstention label. Three things differ here. Abstention is the *correct,
actionable output* for 48.8% of released pairs, not a cost: `needs_evidence` names a record
the firm must produce. Insufficiency belongs to the evidence base, so it is fixed **by
construction** rather than annotated, which is the judgement call that makes legal
sufficiency datasets small and contestable. And the error is directional: `fail` on an
undecidable pair triggers review, `pass` suppresses it, so we report the false-green rate
on its own rather than merging it into one risk term.

**Structured data.** Table fact verification (Chen et al., 2020) and text-to-SQL (Yu et
al., 2018) originally assumed every item decidable. FEVER's Supported / Refuted /
NotEnoughInfo (Thorne et al., 2018), extended to table cells by FEVEROUS (Aly et al., 2021),
is the nearest label structure to ours. EHRSQL (Lee et al., 2022), work on ambiguous and
unanswerable text-to-SQL questions (Wang et al., 2023) and TrustSQL (Lee et al., 2024) add
infeasible questions; ClaimDB verifies claims against multi-table databases with a
not-enough-info class and finds models struggle to abstain (Theologitis et al., 2026). Here
the item is a regulatory obligation attached to an entity, labels come from a generator,
and the two wrong answers on an undecidable item are scored asymmetrically.

**Output format.** Constraining output changes answers: structured formats degrade
reasoning (Tam et al., 2024), forced multiple choice changes substantive answers (Röttger
et al., 2024), and meaning-preserving format changes can swing accuracy by up to 76 points
(Sclar et al., 2024), which is why our prompt is frozen across conditions. Kalai et al.
(2025) attribute persistent hallucination partly to grading that gives no credit for
uncertainty. Our schema ablation is the same incentive located in a product interface, and
we know of no prior work that measures it on a directional error rate.

**Positioning.** The contribution is not an abstention algorithm, and not the first
construction-labelled overclaiming benchmark. It is a task in which correct abstention is a
large share of pairs and the assessed party is a third-party employer described by
structured exports; a directional measure for that setting with an ablation that separates
the schema's parts; a preregistered test of the mechanism on fresh data; and a releasable
artifact in a domain where releasability is the binding constraint. Generated ground truth
has precedent in bAbI (Weston et al., 2015) and lets fresh firms be drawn at any seed,
addressing contamination (Sainz et al., 2023). Constructed labels are not error-free, and
label errors can change rankings (Northcutt et al., 2021), which is why we audit them
(Section 6). The release follows datasheet practice (Gebru et al., 2021) and, in requiring
the false-green rate beside violation recall, the spirit of model cards (Mitchell et al.,
2019). We found no prior work measuring whether a system's headline counts agree with its
own per-item outputs; that metric is the least-established in the suite.

---

## 3. Background: the four states

The four-state vocabulary comes from the source engine (Section 5), where it was adopted
for a practical reason. A system that reports on legal obligations without being counsel
should not state a conclusion it has no basis for, and unauthorised-practice rules (for
example ABA Model Rule of Professional Conduct 5.5 and the state statutes it reflects)
make the line between reporting records and giving legal conclusions consequential. A
separate state for "not assessable from the evidence provided" keeps that line visible.

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
as unmonitored. Silent omission is itself a false green. In the data evaluated in this
paper no ground-truth label is `unmonitored`, so the state is defined and permitted but not
exercised as a target; a model's `unmonitored` answer on a withheld pair is scored as wrong
but is not a false green.

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
decidable. Two conventions qualify it. Reference knowledge (calendars, federal holidays,
regulatory thresholds) is supplied by the system rather than required from $S$, and fields
are matched to $\mathrm{req}(r)$ by meaning rather than by name. With those conventions,
`needs_evidence` is defined by the data rather than by an annotator's sense of sufficiency:
if an item of $\mathrm{req}(r)$ is absent from $S$ for entity $e$, the pair is not
decidable, and any verdict other than `needs_evidence` is wrong regardless of whether the
underlying situation happens to be compliant. Applying the meaning-match is itself a
judgement, which is why the anchor labels were audited (Section 6.1).

A **pair** is $(r, e)$ where $e$'s type matches $r$'s attachment. The prediction target is
a verdict $v \in \{\texttt{pass}, \texttt{fail}, \texttt{needs\_evidence},
\texttt{unmonitored}\}$, optionally with evidence pointers and a citation.

All date-relative obligations evaluate against $a$ rather than against the current date, so
planted expiry windows remain valid indefinitely. The anchor firm pins $a$ = 2026-06-29.

**Scoring rule.** A pair with no prediction is counted as an error rather than skipped, so
declining to answer lowers violation recall and every accuracy-type score. It does not raise
the false-green rate, because an unanswered pair cannot be a false green; every results
table therefore also reports coverage and the false-green rate among answered pairs
(Section 7).

---

## 5. Benchmark construction

### 5.1 The rulebook

The rulebook contains 194 obligations across ten regimes: I-9 and E-Verify (28), Labor
Condition Application (23), Public Access File (15), wage and prevailing wage (21), H-1B
status (16), I-129 supplement (13), L-1 (21), F-1 OPT and STEM OPT (15), site-visit
readiness (14), and cross-cutting deadlines and penalties (28). The source manifest lists
196 entries; two rules appear deliberately in two regimes, once as a field check and once
as a deadline clock, and are counted once here under I-9.

Each obligation carries the check it performs, its threshold, its regulatory citation, and
a description of the information needed to decide it. The citations had previously been
through a verification pass by the source engine's maintainers (the author's company), in
which incorrect citations and thresholds were corrected against primary sources; it was
not an independent legal review. The rulebook is built programmatically from the source
engine's machine-readable registry of that manifest rather than retyped, so every citation
is traceable to a source document rather than to our recollection.

The anchor firm's expectation set also refers to 17 rules by the engine's internal
identifiers rather than manifest identifiers. Fourteen map to the manifest rule stating the
same duty through the engine's own published alias table. Three are engine roll-ups whose
definitions are assembled from the manifest rules they aggregate and carry those rules'
citations. No obligation text in the benchmark is written from scratch.

### 5.2 The anchor firm

The anchor firm is a synthetic employer of twelve workers, nine on H-1B status and three
United States citizens, operating from two worksites, with eleven source exports totalling
93 data rows: HR roster, case-management export, certified LCAs, I-9 records, E-Verify
cases, payroll register, RFE and NOID cases, cap cases, green-card cases, PERM recruitment
tracker, and benefits census.

Most workers carry one planted regulatory mechanism, so that a missed finding usually
localises to a mechanism. Representative plants:

| Mechanism | Planted signal |
|---|---|
| I-9 Section 2 timeliness | Section 2 completed 8 business days after start, against a 3-day limit |
| Reverification deadline | Employment authorisation document expired 14 days before the pinned date, with no reverification recorded |
| E-Verify TNC window | Notice delivered, no employee decision recorded, well past the response window |
| LCA expiration | Certified period ending 4 days after the pinned date |
| Required wage, greater-of | Salary equals the certified rate but falls below the prevailing wage |
| Material change, occupation | Filing carries an individual-contributor occupation code against a management title |
| Material change, worksite | Roster location differs from the filing's stated area of intended employment |
| Petition expiry | Validity ending 21 days after the pinned date |

**What the anchor labels are, and their known problems.** The anchor firm's labels were
written as the acceptance gate for a compliance engine, not generated, so they are not
"fixed by construction" in the sense the generated firms are. Their `fail` means "requires
action" in that engine. A review of the 20 violation labels while preparing this paper
found the following, all disclosed rather than silently corrected, because the labels
predate every result:

- *Duplicates.* Four facts each carry two violation labels under different rules: Mei
  Tanaka's wage shortfall, Sofia Reyes's worksite, Daniel Cho's E-Verify case, and Hiroshi
  Yamamoto's petition expiry. The 20 labels describe 16 distinct facts.
- *Not violations on the records.* Five "actual-wage memo missing" labels have no evidence
  in any export, and five are deadlines that had not passed on the evaluation date. The
  strict view (Section 6) handles both.
- *Contestable plants.* Some plants ignore exceptions a practitioner would check. A roster
  location outside the LCA's area may be a permitted short-term placement (20 C.F.R.
  655.735). A management title against an individual-contributor occupation code is not by
  itself a material change, since the test is a change in duties (8 C.F.R.
  214.2(h)(2)(i)(E)). Helena Voss's reverification label has no reverification data in the
  export. One certified LCA states an offered wage below its prevailing wage, which the
  Department of Labor would not certify.

We keep the engine's labels as the headline view because they existed before this study.
The strict view, the duplicate count and the generated firms are the checks on them.

The firm's expectation set contains no `pass` labels. Some workers' records conform, but
the engine's expectations name only violations and evidence requests, so the anchor firm
cannot measure false alarms; the generated firms can (Section 5.3).

Its expectation set contains 221 pairs: 20 planted violations and 201 evidence requests.
The 201 arise because most obligations in this domain require evidence an employer export
does not contain. A certified LCA does not evidence that the required notice was posted; a
roster does not evidence which document a worker presented. The honest output for such a
pair is an evidence request. The ten-to-one ratio reflects which obligations the source
engine can assess from exports, not a measured property of real employers; we treat the
large abstention share as a design choice that mirrors that engine's coverage.

### 5.3 The generator

The anchor firm is one employer, too small to support an interval on any error rate and
lacking conforming controls. The generator addresses both over a deliberately narrow set of
rules. Its central property is that **labels precede data**: for each applicable
(obligation, entity) pair it first draws a disposition, then writes records that decide it.

- `planted_violation`: the records show the breach;
- `planted_control`: the records show conformity, with a configured share placed exactly on
  the legal boundary (near-miss controls) to test whether a system flags on proximity rather
  than on the rule;
- `withheld_evidence`: the export that would carry the required information is not provided.

It emits pairs only for four rule families whose every listed input it renders: I-9 Section 1
timeliness (signed on or before the first day of employment, not before offer acceptance),
Section 2 timeliness (within three business days, excluding weekends and federal holidays
with their observed dates), reverification by the expiry of temporary authorisation, and the
LCA required wage (wages paid at least the greater of the prevailing wage and the employer's
actual wage, from a semimonthly payroll register and an actual-wage table). Near-miss
controls sit on the boundary: Section 1 on the first day, Section 2 on business day three,
Supplement B on the expiry date, pay exactly equal to the required wage. Evidence is withheld
a whole export at a time, never by blanking one worker's cell, because a blank date for a
past deadline reads to a practitioner as "not done", which is a violation.

**An earlier generator failed this standard, and we replaced it.** A first version emitted a
label for every pair in the 194-obligation rulebook but rendered deciding data for only four
rule families, and applied rules to entities they cannot govern. A blind check caught this
before any result on generated firms was reported: an AI agent given only the records and
rule text for 60 stratified pairs agreed with its labels on 8. Every figure from that
version, including a released-set size of 58,961 pairs, is withdrawn
(`docs/study2_v1_invalid/`). The same check on the current generator agreed on all 60.

**An independent derivation of every generated label.** A sample check by a model is weak
evidence, so a separate agent wrote a deterministic checker for the four rules from the
regulations (8 C.F.R. 274a.1–274a.2, the M-274 handbook, 20 C.F.R. 655.731), with no access
to the generator's code or any label, recording each interpretive choice with its source
(`labelcheck/INTERPRETATIONS.md`). Run on every generated firm used or audited here, it
first disagreed on one pair of 1,680, exposing a generator bug: a New Year's Day falling on
a Saturday is observed on the preceding Friday, which the generator's calendar missed. The
bug touched one pair on an audit seed and no study firm. After the fix the two derivations
agree on all 1,680 labels (`docs/labelcheck_results.json`). Where the law is not explicit
(that signing Section 1 on the first day is timely, that "business day" excludes federal
holidays, that wages are compared per pay period) the choices are stated, so a reader who
would choose otherwise can rerun the checker.

**Adjacent columns (generator v3).** For Study 3 the generator can add five roster columns
that sit beside the evidence a rule needs without being it: an I-9 status of "Complete", an
onboarding completion date, the current authorisation's end date, a salary of record set at
the LCA offered wage, and an internal pay-band midpoint. They appear in every such firm,
whether or not the export they imitate is withheld, and come from a separate random stream,
so the firm with them and the same seed without them are identical in every label and every
other export. None is an item the rulebook lists as evidence for the rule it imitates, and
the reference checker ignores them.

The cost of this design is breadth: four rule families, tested thoroughly, against the
anchor firm's 221 pairs across eight regimes. Generation is deterministic in the seed.

### 5.4 Released scale

| | Value |
|---|---|
| Firms | 31 (1 anchor + 30 generated at seeds 1-30) |
| Pairs | 1,481 |
| Withheld-evidence pairs | 723 (48.8%) |
| Planted violations | 238 |
| Obligations in the rulebook | 194 (the generator renders four rule families) |

Additional firms are available at any seed.

---

## 6. Metrics

Let $T$ be ground truth and $P$ predictions over pairs.

**Violation recall.** Of pairs labelled `fail`, the share predicted `fail`. A missed
violation is the failure the domain treats as unforgivable, so this is reported first.

**Violation precision** and **false-alarm rate.** Precision over `fail` predictions, and
separately the share of conforming controls (label `pass`) on which a system returned
anything other than `pass`: `fail`, `needs_evidence` and `unmonitored` all count as an
alarm, since each sends a compliant item to review. Near-miss controls, placed exactly on
the legal boundary, are reported separately in Study 2.

**False-green rate.** The headline metric:

$$\mathrm{FGR} = \frac{|\{p : T(p) = \texttt{needs\_evidence} \wedge P(p) = \texttt{pass}\}|}{|\{p : T(p) = \texttt{needs\_evidence}\}|}$$

The share of undecidable pairs a system reports as satisfied. Note what it is not: it is
not one minus abstention recall. A system that answers `fail` on an undecidable pair is
wrong, but it is wrong in a direction that triggers review. Only `pass` suppresses review,
so only `pass` counts here.

**Abstention precision and recall,** treating `needs_evidence` as a class. Precision
matters because a system can drive the false-green rate to zero by abstaining everywhere,
which the baselines demonstrate.

Two further axes are defined in the harness for systems that expose them, and are **not
measured in this paper's studies**. *Evidence-pointer accuracy* is the share of correct
verdicts whose cited evidence intersects the fields ground truth records as relevant.
*Consistency drift* is the disagreement between the counts a dashboard displays and its own
per-pair verdicts. Neither applies to the language models evaluated here; we list them so
that system builders can report them.

**Reporting requirement.** The false-green rate must be reported alongside violation
recall. Neither is meaningful alone, and Section 8 shows why.

### 6.1 Label views of the anchor firm

**Two label views, fixed before per-pair results were read.** The anchor firm's labels were
written as the acceptance gate for a compliance engine, where `fail` means "requires
action"; here `fail` means "the records show a violation". Ten of the 20 planted violations
sit between those meanings, so we score under two views, fixed in
`nofalsegreen/labelviews.py` on 2026-09-24 with each affected pair named. The commit came
six minutes after a first, later-discarded attempt at the main run had printed preliminary
aggregate rates to its log; no per-pair result had been read, but we cannot exclude that
those aggregates influenced the decision.

- **Engine view, the headline.** The labels as authored, which existed before this
  benchmark did, so nothing decided here can have tuned them.
- **Strict view.** Five "actual-wage memo missing" violations become `needs_evidence`, since
  no export records the memo as absent. Five deadlines not yet passed on the evaluation date
  (an LCA and a petition near expiry, an open extension window, an RFE and a NOID not yet
  due) are removed from scoring and reported as deadline alerts. The remaining ten are
  breaches that had already occurred.

The strict view's ten violations include three duplicated facts (Section 5.2), so they
describe seven distinct facts. Its recall has a denominator of ten, so one pair moves it by
0.1, and it is always reported beside the engine view.

**A third view, from a blind audit of the withheld labels.** While reading early results we
found a withheld label the exports contradict: `i9.section2.employer_signature` is labelled
`needs_evidence` because the source engine never maps the column, yet
`section2_signed_date` and `section2_examiner_name` are populated for every employee.
Because this was noticed in model output, the correction was constrained so that output
could not steer it. The protocol (`docs/LABEL_AUDIT_PROTOCOL.md`) was committed before the
audit ran; it covers all 120 withheld pairs; the auditor, a separate agent, saw only each
pair's obligation text and exports; and a label is overturned only if every required item is
present for that entity. The audit overturned 2 of 120, the Section 1 and Section 2 I-9
signatures, both on signed-date columns (the Section 1 call is the weaker: a date is not
obviously a signature). In the **audited view** those pairs are removed from scoring, not
relabelled. Removing pairs can only remove false greens, so every table in this view states
its denominator, and the engine view remains the headline.

**A second auditor, and an audit of the violations.** Under a protocol addendum committed
before it ran, a second auditor from a different developer (Gemini 3.1 Pro, also a model
under test, which never saw its own replies) repeated the withheld audit and, blind to the
label, judged each violation pair as `violation_shown`, `compliance_shown` or `cannot_tell`
(`docs/label_audit_second.json`). On the withheld pairs the two auditors keep the label on
113 of 120. The first overturns 2 and the second 5, with no pair in common; the second's five
are three LCA wage pairs, the FDNS itinerary item and the I-9 physical-examination item. On
the violations, the second auditor supports neither the five memo absences nor the five
future deadlines on the labelled ground, reaching the strict view's correction independently.
Of the strict view's ten violations it supports five, covering four distinct facts: a late
Section 2, a missed reverification, pay below the required wage, and a lapsed E-Verify action
window. It judges four undecidable from the exports (a title change with no occupation code,
a worksite move and an LCA area breach with no effective date, an E-Verify referral with no
referral date) and one compliant (a U.S. passport holder with no reverification recorded).
The false-green rate does not depend on any violation label. Violation recall on the anchor
firm does, and should be read as recall against an engine's view of what is actionable, of
which roughly half is a breach evident from the exports.

## 7. Baselines

**Trivial baselines (run).** `always_pass` answers `pass` everywhere and is maximally
unsafe. `always_abstain` answers `needs_evidence` everywhere: safe but useless.
`always_fail` flags everything. `oracle` reads the label basis and decides exactly when
evidence is present; it is not a competitive system but an upper bound establishing that
the task is solvable.

**Language-model baselines.** The harness was tested against mock models with known failure
signatures before any real call. The protocol is frozen in code (`baselines/prompts.py`,
`PROMPT_VERSION` 1.1.0), so the reported result cannot be a post-hoc choice of prompt:

- *Prompt.* The source exports verbatim as CSV, the batch's obligations with check,
  threshold, citation and the information needed, and the pairs to decide. Columns are
  matched to obligations by meaning, and reference knowledge such as federal holidays is
  supplied by the model. The evaluation date is pinned, with an instruction not to use the
  real date. Verdicts come back one per line as `pair_id`, verdict, evidence field.
- *Output schemas.* `abstain_offered` permits four verdicts, defines `pass` as "the required
  evidence is present in the exports and satisfies the obligation", and stresses the
  `pass`-versus-`needs_evidence` distinction. `abstain_withheld` is a dashboard schema with
  only `pass` and `fail`; it changes four things at once (it removes `needs_evidence` and
  `unmonitored`, redefines `pass` as "the obligation is satisfied", and drops the warning).
  Two conditions separate those changes: `abstain_removed_only` (the offered prompt minus
  `needs_evidence` and its definition) and `abstain_closed` (only `pass` and `fail`, with the
  evidence-anchored definitions and warning kept). We count **off-schema** replies, verdicts
  a schema does not permit. Appendix B gives all four menus verbatim.
- *Decoding.* Temperature 0 and an output cap of 32,000 tokens, reasoning tokens included.
- *Models.* Study 1 ran six free API models from four developers (Section 7.2). The Vertex
  block adds three Google models: Gemini 3.1 Pro, Gemini 3.8 Flash and Gemma 4 26B. Study 3
  and its extension add four open-weights models from other developers, served on Vertex AI:
  OpenAI gpt-oss-120b, DeepSeek V3.2, Qwen3 235B A22B Instruct and Moonshot Kimi K2 Thinking
  (Qwen3 235B's served output limit is 16,384 tokens, below our cap). Results speak to these
  thirteen models only.

**Parsing and coverage are scoring decisions.** A reply line naming a pair without a
recognised verdict yields no prediction and is never coerced: coercing to `needs_evidence`
would turn formatting failures into abstentions and flatter the false-green rate, and
coercing to `pass` the reverse. We report the unparseable rate separately. An unanswered pair
counts as a miss for violation recall, but on the false-green rate it can never be a `pass`,
so a model that answers less looks safer and one that answers nothing scores 0.000. Every
results table therefore reports how many pairs were answered and the false-green rate among
withheld pairs actually answered.

**Delivery failures are not answers.** An empty reply, one ending in an upstream error, or
one cut off by the host below our cap is re-requested, up to three attempts. Three such
failures in a row means the host is failing: the run stops and resumes later, and is never
recorded as finished with a batch missing for this reason. A reply that ends normally with
no usable lines, or runs to our 32,000-token cap on all three attempts, is the model's own
outcome and counts as unanswered. Two departures from this rule occurred; both are in
Appendix C.4.

**Cost.** Study 1 used free API tiers only. The Vertex block, Study 2 and Study 3 were paid
from the author's startup cloud credits; token counts per run are in `docs/vertex/runs/` and
`docs/study3/runs/`.

### 7.1 Protocol revision after a pilot

A pilot under prompt v1.0 exposed three defects in our own harness, not in the models:
obligations sent without their definitions, a mangled "information needed" field, and a
definition of `needs_evidence` that a literal reader could apply to every pair. We fixed
them in prompt v1.1.0, archived the pilot, and report no pilot number as a result. The
main runs then exposed an output cap that cut off reasoning models mid-reply; incomplete
replies were purged and re-requested under a larger cap. Both revisions, with the numbers
that motivated them, are in Appendix C.

### 7.2 Source scoping, model set and subset

**Source scoping.** Free tiers cap tokens per minute, so each call carries only the exports
whose regime the batch's obligations can be evaluated against, with the HR roster always
included; every run uses batches of 12 pairs. Scoping changes the prompt, so it is part of the protocol.
The prompt names the exports not sent and tells the model not to infer that an absent field
exists in one of them, and an obligation of an unclassified regime falls back to all sources. Scoping is identical across conditions, so it cannot bias a contrast between them;
we did not run without it. One scoping defect was found and fixed before Study 3: the
generated firms' actual-wage export was never sent with the wage rule (Section 8.3).

**Model set.** Six free models were declared; two were withdrawn from the free tier
mid-study and replaced under rules committed before any replacement answered a batch
(Appendix C.2).

**The declared evaluation subset.** The free-tier budget (50 calls a day) does not cover the
full anchor firm, so Study 1 evaluates a **declared stratified subset** of 140 pairs, fixed
by a seed and frozen before any model was scored: **every planted violation** and 120 of the
201 withheld pairs, sampled in proportion to regime. We never present a subset rate as a
full-firm rate.

**A baseline we deliberately exclude.** The anchor firm's expectation set originated as
the acceptance gate for a commercial compliance engine developed by the author's company
(Section 12). That engine would score near
ceiling on this firm for a reason that has nothing to do with capability: the expectations
and the engine were developed against each other. Reporting it as a baseline would be
misleading, and we do not.

---

## 8. Results

### 8.1 Trivial baselines

**Table 1 — trivial baselines.** Across 31 firms (the anchor and 30 generated), aggregated
per firm then averaged over the firms in which each rate is defined: a generated firm may
withhold every export, or none, so not every rate exists in every firm. Reproduced by
`python3 scripts/sweep.py --firms 30`.

<!-- BEGIN GENERATED: table1-trivial -->
| System | False green | Violation recall | Precision | False alarm | Abstention F1 |
|---|---|---|---|---|---|
| `always_pass` | 1.000 | 0.000 | — | 0.000 | 0.000 |
| `always_abstain` | 0.000 | 0.000 | — | 1.000 | 0.717 |
| `always_fail` | 0.000 | 1.000 | 0.170 | 1.000 | 0.000 |
| `oracle` | 0.000 | 1.000 | 1.000 | 0.000 | 1.000 |

A dash marks a rate undefined for that system: `always_pass` and `always_abstain` never predict a violation, so their precision has no denominator.
<!-- END GENERATED: table1-trivial -->

Three readings.

**The false-green rate is not redundant.** `always_pass` attains a false-alarm rate of
0.000, the best possible score on compliant cases. Under any metric that rewards not
crying wolf, it is indistinguishable from a careful system. It is in fact the worst
possible system for deployment, reporting all 723 undecidable pairs as satisfied. Only
the false-green rate separates them. On the anchor firm alone the separation is starker:
`always_pass` reports all 201 unassessed obligations as satisfied while raising zero false
alarms.

**The false-green rate is also not sufficient.** `always_abstain` attains 0.000 on it
while detecting no violations, and reaches 0.717 abstention F1. On the anchor firm, whose
expectation set declares no control pairs, it reaches 0.953 abstention F1 while being
useless. Abstention scores are therefore gameable in isolation, which is why the suite
must be reported jointly.

**The task is solvable.** The oracle reaches 1.000 on every axis. A system scoring poorly
is exhibiting a property of itself, not of an ill-posed benchmark.

### 8.2 Language-model results

Six free models were evaluated on the declared 140-pair subset of the anchor firm under
prompt v1.1.0, each under both output schemas: Nemotron 3 Ultra 550B, Nemotron 3 Super
120B and Nemotron 3.5 Lightning (NVIDIA), Laguna XS 2.1 (Poolside), Qwen 3.8 27B (Alibaba),
and dots.3 Note Preview (dots-studio), the last two replacing withdrawn models (Section
7.2). Tables are generated from the retained replies (`scripts/fill_results.py`); the
coverage and answered-only columns were added after the first results, when the coverage
effect of Section 7 was found.

**Uncertainty.** Bracketed figures are 95% percentile intervals from a bootstrap that
resamples *obligations* (2,000 draws, fixed seed), since pairs under one obligation share a
rule text and records. At 140 pairs most differences *between* models are not resolved, so
we do not rank models and list them alphabetically. The comparison the study is built for is
*within* a model across schemas: the paired difference on withheld pairs both runs answered,
Holm-corrected across the six models. All six remain significant at 0.05 (Table 3).

**Table 2 — main result, `abstain_offered`.** One row per model on the 140-pair subset, with
the trivial baselines as reference rows. The false-alarm column is 0.000 by construction,
since the subset has no conforming pair.

<!-- BEGIN GENERATED: table2-main -->
| Model | False green | FG, answered only | Recall | Precision | False alarm | Abst. P | Abst. R | Abst. F1 | Unparse. | Answered |
|---|---|---|---|---|---|---|---|---|---|---|
| `dots-3-note-preview` | **0.100** [0.03, 0.21] | 0.100 | 0.450 [0.20, 0.79] | 0.900 | 0.000 | 0.906 | 0.883 | 0.894 | 0.000 | 140/140 |
| `laguna-xs-2.1` | **0.125** [0.05, 0.24] | 0.135 | 0.200 [0.04, 0.45] | 0.667 | 0.000 | 0.940 | 0.783 | 0.855 | 0.000 | 124/140 |
| `nemotron-3-super-120b-a12b` | **0.050** [0.01, 0.11] | 0.050 | 0.300 [0.10, 0.61] | 0.857 | 0.000 | 0.896 | 0.858 | 0.877 | 0.000 | 140/140 |
| `nemotron-3-ultra-550b-a55b` | **0.067** [0.02, 0.14] | 0.067 | 0.300 [0.10, 0.60] | 1.000 | 0.000 | 0.903 | 0.933 | 0.918 | 0.000 | 140/140 |
| `nemotron-3.5-lightning` | **0.042** [0.01, 0.09] | 0.059 | 0.050 [0.00, 0.18] | 0.500 | 0.000 | 0.951 | 0.642 | 0.766 | 0.000 | 92/140 |
| `qwen3.8-27b` | **0.142** [0.06, 0.25] | 0.142 | 0.350 [0.14, 0.67] | 0.875 | 0.000 | 0.894 | 0.842 | 0.867 | 0.000 | 140/140 |
| `always_pass` (ref) | 1.000 | 1.000 | 0.000 | — | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 140/140 |
| `oracle` (ref) | 0.000 | 0.000 | 1.000 | 1.000 | 0.000 | 1.000 | 1.000 | 1.000 | 0.000 | 140/140 |
<!-- END GENERATED: table2-main -->

**Offered an abstention, models abstain readily and detect little.** False-green rates
run from 0.042 to 0.142. The lowest belongs to Lightning, which answered only 92 of 140
pairs; among the withheld pairs it actually answered its rate is 0.059. Violation recall
runs from 0.050 to 0.450: models answer `needs_evidence` on violations whose evidence is in
the exports. Abstention F1 is between 0.766 and 0.918, so the abstentions mostly land on the
right pairs; there are too many of them.

**Table 2b — strict label view** (Section 6.1), with the deadline alerts.

<!-- BEGIN GENERATED: table2b-strict -->
| Model | Condition | FGR, engine | FGR, strict | Recall, engine (of 20) | Recall, strict (of 10) | Alerts: fail / pass / other |
|---|---|---|---|---|---|---|
| `dots-3-note-preview` | offered | 0.100 | 0.096 | 0.45 | 0.70 | 2 / 0 / 3 |
| `dots-3-note-preview` | withheld | 0.525 | 0.504 | 0.80 | 0.80 | 3 / 2 / 0 |
| `nemotron-3-super-120b-a12b` | offered | 0.050 | 0.048 | 0.30 | 0.40 | 2 / 0 / 3 |
| `nemotron-3-super-120b-a12b` | withheld | 0.175 | 0.168 | 0.95 | 0.90 | 5 / 0 / 0 |
| `nemotron-3-ultra-550b-a55b` | offered | 0.067 | 0.064 | 0.30 | 0.50 | 1 / 1 / 3 |
| `nemotron-3-ultra-550b-a55b` | withheld | 0.217 | 0.208 | 0.80 | 0.90 | 2 / 3 / 0 |
| `nemotron-3.5-lightning` | offered | 0.042 | 0.040 | 0.05 | 0.10 | 0 / 1 / 4 |
| `nemotron-3.5-lightning` | withheld | 0.208 | 0.200 | 0.50 | 0.40 | 3 / 0 / 2 |
| `laguna-xs-2.1` | offered | 0.125 | 0.120 | 0.20 | 0.30 | 1 / 0 / 4 |
| `laguna-xs-2.1` | withheld | 0.433 | 0.416 | 0.90 | 0.80 | 5 / 0 / 0 |
| `qwen3.8-27b` | offered | 0.142 | 0.136 | 0.35 | 0.50 | 2 / 0 / 3 |
| `qwen3.8-27b` | withheld | 0.417 | 0.400 | 0.85 | 0.90 | 3 / 2 / 0 |
<!-- END GENERATED: table2b-strict -->

The strict view moves false-green rates by at most 0.021 and raises recall for every model
under `abstain_offered`, because the five memo pairs most models answered `needs_evidence`
stop counting as misses. A `pass` on a deadline days away is the one alert outcome a
reviewer would never see: offered an abstention, models gave it on 2 of 30 alerts; without
it, on 7 of 30, three of them Nemotron Ultra's.

**Table 2c — audited label view.** The two withheld pairs the first audit overturned are
removed; the scored denominator is in every row.

<!-- BEGIN GENERATED: table2c-audited -->
| Model | Condition | Withheld pairs scored | FGR, engine | FGR, audited | FG, audited, answered only |
|---|---|---|---|---|---|
| `dots-3-note-preview` | offered | 118 of 120 | 0.100 | 0.085 | 0.085 |
| `dots-3-note-preview` | withheld | 118 of 120 | 0.525 | 0.517 | 0.517 |
| `nemotron-3-super-120b-a12b` | offered | 118 of 120 | 0.050 | 0.034 | 0.034 |
| `nemotron-3-super-120b-a12b` | withheld | 118 of 120 | 0.175 | 0.161 | 0.161 |
| `nemotron-3-ultra-550b-a55b` | offered | 118 of 120 | 0.067 | 0.051 | 0.051 |
| `nemotron-3-ultra-550b-a55b` | withheld | 118 of 120 | 0.217 | 0.203 | 0.203 |
| `nemotron-3.5-lightning` | offered | 118 of 120 | 0.042 | 0.025 | 0.036 |
| `nemotron-3.5-lightning` | withheld | 118 of 120 | 0.208 | 0.212 | 0.439 |
| `laguna-xs-2.1` | offered | 118 of 120 | 0.125 | 0.110 | 0.119 |
| `laguna-xs-2.1` | withheld | 118 of 120 | 0.433 | 0.424 | 0.472 |
| `qwen3.8-27b` | offered | 118 of 120 | 0.142 | 0.127 | 0.127 |
| `qwen3.8-27b` | withheld | 118 of 120 | 0.417 | 0.407 | 0.407 |
<!-- END GENERATED: table2c-audited -->

Removing the two I-9 signature pairs lowers the false-green rate by 0.008 to 0.016 in 11
of the 12 runs; in the twelfth, Lightning without the abstention, it rises by 0.004. It
changes neither the ordering of models nor the direction of any condition effect.

**Table 3 — the schema ablation.** Same models, both conditions.

<!-- BEGIN GENERATED: table3-ablation -->
| Model | Withheld pairs answered in both | FGR offered | FGR withheld | Change [95% CI] | Holm-adjusted p | Off-schema replies (withheld) |
|---|---|---|---|---|---|---|
| `dots-3-note-preview` | 120 of 120 | 0.100 | 0.525 | +0.425 [+0.26, +0.59] | 0.003 | 0 of 140 answered |
| `nemotron-3-super-120b-a12b` | 120 of 120 | 0.050 | 0.175 | +0.125 [+0.03, +0.24] | 0.006 | 0 of 140 answered |
| `nemotron-3-ultra-550b-a55b` | 120 of 120 | 0.067 | 0.217 | +0.150 [+0.07, +0.27] | 0.003 | 0 of 140 answered |
| `nemotron-3.5-lightning` | 41 of 120 | 0.042 | 0.208 | +0.463 [+0.12, +0.73] | 0.006 | 0 of 68 answered |
| `laguna-xs-2.1` | 99 of 120 | 0.125 | 0.433 | +0.333 [+0.16, +0.51] | 0.003 | 0 of 128 answered |
| `qwen3.8-27b` | 120 of 120 | 0.142 | 0.417 | +0.275 [+0.13, +0.43] | 0.003 | 0 of 140 answered |

FGR columns are over all 120 withheld pairs, as in Table 2. The change, its interval (obligation-cluster bootstrap, 2,000 draws) and the one-sided p-value are computed on the withheld pairs both runs answered; the bootstrap p-value has a floor of 1/2,000.
<!-- END GENERATED: table3-ablation -->

**Removing the abstention from a dashboard schema raises false greens in every model.** The
direction is close to built in: a schema with only `pass` and `fail` forces every
unassessable pair into one of them. What the design does not fix is the size: it rises by between 0.125
 (Nemotron Super) and 0.425 (dots.3), and the lean: five of the six models sent most
unassessable pairs to `fail`, while dots.3 sent more to `pass` (63) than to `fail` (57). No
model returned an off-schema verdict among the pairs it answered. This condition also
redefines `pass` and drops a warning paragraph, so its effect is that of moving to a
dashboard schema; Sections 8.4 and 8.5 take it apart.

**Table 4 — false-green rate by regime, `abstain_offered`.** In parentheses, the regime's
scored pairs of any label.

<!-- BEGIN GENERATED: table4-regime -->
| Regime | `nemotron-3-ultra-550b-a55b` | `nemotron-3-super-120b-a12b` | `nemotron-3.5-lightning` | `laguna-xs-2.1` | `qwen3.8-27b` | `dots-3-note-preview` |
|---|---|---|---|---|---|---|
| `deadlines-penalties` | 0.000 (6) | 0.000 (6) | 0.000 (6) | 0.000 (6) | 0.250 (6) | 0.000 (6) |
| `fdns-sitevisit` | 0.000 (7) | 0.000 (7) | 0.000 (7) | 0.000 (7) | 0.000 (7) | 0.000 (7) |
| `h1b-status` | 0.000 (17) | 0.000 (17) | 0.000 (17) | 0.000 (17) | 0.000 (17) | 0.000 (17) |
| `i129-supplement` | 0.000 (8) | 0.000 (8) | 0.000 (8) | 0.000 (8) | 0.125 (8) | 0.000 (8) |
| `i9-everify` | 0.217 (28) | 0.174 (28) | 0.174 (28) | 0.217 (28) | 0.304 (28) | 0.174 (28) |
| `lca-dol` | 0.100 (33) | 0.067 (33) | 0.000 (33) | 0.100 (33) | 0.100 (33) | 0.100 (33) |
| `paf` | 0.000 (17) | 0.000 (17) | 0.059 (17) | 0.000 (17) | 0.000 (17) | 0.000 (17) |
| `wage-prevailing` | 0.000 (24) | 0.000 (24) | 0.000 (24) | 0.389 (24) | 0.278 (24) | 0.278 (24) |

Cells are the false-green rate over the regime's withheld pairs; in parentheses, the regime's scored pairs of any label.
<!-- END GENERATED: table4-regime -->

Three regimes, I-9 and E-Verify, prevailing wage, and the LCA rules, hold almost every false
green; H-1B status and FDNS site visits have none. Section 9 traces this to populated columns
beside the missing evidence.

**Figure 1 — recall against false-green rate, Study 1.** Filled circles offered the
abstention, open circles did not; grey squares are the trivial baselines.

![Figure 1](figure1_separation.svg)

Without the abstention the models move up and right together, gaining recall at the cost of
false greens; none reaches the oracle's corner. `always_fail` sits on the oracle's point
because neither axis penalises calling an unassessable pair a violation, which is why the
decomposition of Section 9 counts that error. A recall-only evaluation would prefer the
dashboard schema; the false-green axis shows what that preference costs.

### 8.3 Study 2: generated firms

Study 2 runs the same protocol on all 252 pairs of six generated firms (Section 5.3), which
carry what the anchor firm lacks: conforming controls, a third of them near-miss cases on
the legal boundary. Firms were fixed in `nofalsegreen/study2.py` before any call. Results
come from the three Vertex models, three runs each, in the Study 2 rows of Table 7 (Section
8.4). The declared free-tier sweep was stopped after one model, superseded by Study 3
(Section 8.5), which runs four models from other developers on fresh firms.

**A scoping defect, and what it touches.** While preparing Study 3 we found that the scoped
prompt for the wage rule never carried a generated firm's `actual_wage_system` export, which
the rule needs. In Study 2 every wage pair was therefore sent without it. The 27 withheld
wage pairs are unaffected, since their evidence was missing either way. The 27 decidable wage
pairs (three firms, labelled `pass` or `fail`) were not decidable from what the models saw,
and are excluded from every Study 2 metric. False-green rates and the Table 8 contrasts do
not change. Detection and false-alarm figures do, and one reading in an earlier version of
this paper was wrong: we attributed Gemini 3.1 Pro's near-miss false alarms (0.162) to
caution about evidence that was present. They were requests for the missing actual-wage
export, which was correct. The defect is fixed for Study 3.

**Generated firms are easier.** With abstention offered, the three models report 0.021 to
0.071 of withheld pairs as compliant, below their Study 1 rates. Gemini 3.1 Pro and 3.8
Flash detect every violation and raise no false alarm on a conforming control, near-miss
controls included, in three of the four schemas. Gemma 4 detects 0.346 of violations. The
generated exports are clean, with no populated column next to a missing one, which is the
gap Study 3 fills. Excluding the reverification pairs, whose violation labels assume no
extension was filed (Section 11), changes no conclusion; no false green fell on them.

### 8.4 The Vertex block: a frontier model, and repeated runs

Every model in Section 8.2 is a free-tier open-weights model, run once. The Vertex block
adds Gemini 3.1 Pro (Google's frontier tier at the time of writing), Gemini 3.8 Flash, and
Gemma 4 26B (open weights, Google-hosted), on both studies, and runs every configuration
three times (`nofalsegreen/vertex_block.py`). These models were added after the free-tier
studies began, and are reported apart for that reason.

It also takes the schema ablation apart. The dashboard condition of Section 8.2 changes four
things at once, so the block adds two conditions, each declared before its first call. In
*removed-only*, the offered prompt loses only `needs_evidence` and its definition. In
*closed*, both non-committal verdicts are removed but `pass` and `fail` keep their
evidence-anchored definitions and the warning sentence. The *closed* condition was added
after the first *removed-only* results were seen, and is reported as such.

**Table 7 — Vertex block.** Mean of three runs, with the minimum and maximum in brackets.

<!-- BEGIN GENERATED: table7-vertex -->
| Model | Study | Schema | False green | FG, answered only | Recall | False alarm, near-miss | Withheld pairs answered pass / fail / needs_ev. / unmon. | Min answered |
|---|---|---|---|---|---|---|---|---|
| `gemini-3.1-pro-preview` | 1 | offered | 0.058 [0.058, 0.058] | 0.058 | 0.433 [0.400, 0.450] | — | 7 / 1 / 101 / 11 | 140/140 |
| `gemini-3.1-pro-preview` | 1 | removed-only | 0.050 [0.025, 0.067] | 0.050 | 0.550 [0.500, 0.600] | — | 6 / 5 / 0 / 109 | 140/140 |
| `gemini-3.1-pro-preview` | 1 | closed | 0.050 [0.033, 0.067] | 0.050 | 0.950 [0.950, 0.950] | — | 6 / 114 / 0 / 0 | 140/140 |
| `gemini-3.1-pro-preview` | 1 | dashboard | 0.131 [0.125, 0.142] | 0.131 | 0.917 [0.850, 0.950] | — | 16 / 104 / 0 / 0 | 140/140 |
| `gemini-3.1-pro-preview` | 2 | offered | 0.021 [0.016, 0.032] | 0.021 | 1.000 [1.000, 1.000] | 0.000 [0.000, 0.000] | 3 / 0 / 123 / 0 | 225/252 |
| `gemini-3.1-pro-preview` | 2 | removed-only | 0.056 [0.024, 0.071] | 0.056 | 1.000 [1.000, 1.000] | 0.025 [0.000, 0.037] | 7 / 26 / 0 / 93 | 225/252 |
| `gemini-3.1-pro-preview` | 2 | closed | 0.061 [0.056, 0.064] | 0.061 | 1.000 [1.000, 1.000] | 0.000 [0.000, 0.000] | 8 / 118 / 0 / 0 | 225/252 |
| `gemini-3.1-pro-preview` | 2 | dashboard | 0.061 [0.056, 0.064] | 0.061 | 1.000 [1.000, 1.000] | 0.000 [0.000, 0.000] | 8 / 118 / 0 / 0 | 225/252 |
| `gemini-3.8-flash` | 1 | offered | 0.094 [0.092, 0.100] | 0.094 | 0.500 [0.500, 0.500] | — | 11 / 0 / 96 / 12 | 140/140 |
| `gemini-3.8-flash` | 1 | removed-only | 0.156 [0.125, 0.183] | 0.160 | 0.783 [0.750, 0.850] | — | 19 / 18 / 0 / 79 | 128/140 |
| `gemini-3.8-flash` | 1 | closed | 0.242 [0.208, 0.283] | 0.245 | 0.767 [0.600, 0.850] | — | 29 / 89 / 0 / 0 | 127/140 |
| `gemini-3.8-flash` | 1 | dashboard | 0.419 [0.375, 0.458] | 0.433 | 0.833 [0.800, 0.850] | — | 50 / 66 / 0 / 0 | 127/140 |
| `gemini-3.8-flash` | 2 | offered | 0.026 [0.016, 0.032] | 0.027 | 1.000 [1.000, 1.000] | 0.000 [0.000, 0.000] | 3 / 4 / 117 / 0 | 219/252 |
| `gemini-3.8-flash` | 2 | removed-only | 0.037 [0.032, 0.048] | 0.037 | 1.000 [1.000, 1.000] | 0.000 [0.000, 0.000] | 5 / 62 / 0 / 59 | 225/252 |
| `gemini-3.8-flash` | 2 | closed | 0.156 [0.127, 0.182] | 0.156 | 1.000 [1.000, 1.000] | 0.000 [0.000, 0.000] | 20 / 106 / 0 / 0 | 225/252 |
| `gemini-3.8-flash` | 2 | dashboard | 0.167 [0.167, 0.167] | 0.167 | 1.000 [1.000, 1.000] | 0.000 [0.000, 0.000] | 21 / 105 / 0 / 0 | 225/252 |
| `gemma-4-26b-a4b-it-maas` | 1 | offered | 0.153 [0.150, 0.158] | 0.153 | 0.067 [0.050, 0.100] | — | 18 / 0 / 76 / 26 | 140/140 |
| `gemma-4-26b-a4b-it-maas` | 1 | removed-only | 0.183 [0.175, 0.200] | 0.220 | 0.067 [0.050, 0.100] | — | 22 / 0 / 0 / 79 | 116/140 |
| `gemma-4-26b-a4b-it-maas` | 1 | closed | 0.600 [0.525, 0.667] | 0.682 | 0.400 [0.400, 0.400] | — | 72 / 33 / 0 / 0 | 122/140 |
| `gemma-4-26b-a4b-it-maas` | 1 | dashboard | 0.589 [0.567, 0.617] | 0.635 | 0.400 [0.400, 0.400] | — | 71 / 41 / 0 / 0 | 128/140 |
| `gemma-4-26b-a4b-it-maas` | 2 | offered | 0.071 [0.071, 0.071] | 0.071 | 0.346 [0.296, 0.370] | 0.074 [0.074, 0.074] | 9 / 0 / 116 / 1 | 225/252 |
| `gemma-4-26b-a4b-it-maas` | 2 | removed-only | 0.071 [0.071, 0.071] | 0.071 | 0.370 [0.333, 0.407] | 0.111 [0.111, 0.111] | 9 / 0 / 0 / 117 | 225/252 |
| `gemma-4-26b-a4b-it-maas` | 2 | closed | 0.172 [0.167, 0.175] | 0.189 | 0.444 [0.370, 0.518] | 0.049 [0.037, 0.074] | 22 / 93 / 0 / 0 | 208/252 |
| `gemma-4-26b-a4b-it-maas` | 2 | dashboard | 0.175 [0.175, 0.175] | 0.175 | 0.370 [0.370, 0.370] | 0.037 [0.037, 0.037] | 22 / 104 / 0 / 0 | 225/252 |

Schemas: *offered* (four verdicts, evidence-anchored definitions); *removed-only* (offered minus `needs_evidence`); *closed* (`pass`/`fail` only, evidence-anchored definitions kept); *dashboard* (`pass`/`fail` only, `pass` redefined as "the obligation is satisfied", warning dropped; the `abstain_withheld` condition of Study 1). Study 1 has 120 withheld pairs and no conforming controls; Study 2 rates are pooled over its six firms (126 withheld pairs). The verdict columns show every off-schema answer: none occurred on a withheld pair in any cell.
<!-- END GENERATED: table7-vertex -->

**Table 8 — paired contrasts between schemas, Vertex block.**

<!-- BEGIN GENERATED: table8-contrasts -->
| Model | Study | Change of schema | Withheld pairs | Change in FGR [95% CI] | Holm p |
|---|---|---|---|---|---|
| `gemini-3.1-pro-preview` | 1 | offered → removed-only | 120 | -0.008 [-0.04, +0.01] | 1.000 |
| `gemini-3.1-pro-preview` | 1 | offered → closed | 120 | -0.008 [-0.09, +0.05] | 1.000 |
| `gemini-3.1-pro-preview` | 1 | closed → dashboard | 120 | +0.081 [+0.02, +0.17] | 0.036 ** |
| `gemini-3.1-pro-preview` | 1 | offered → dashboard | 120 | +0.072 [-0.04, +0.19] | 1.000 |
| `gemini-3.1-pro-preview` | 2 | offered → removed-only | 126 | +0.034 [+0.00, +0.11] | 1.000 |
| `gemini-3.1-pro-preview` | 2 | offered → closed | 126 | +0.040 [+0.00, +0.10] | 1.000 |
| `gemini-3.1-pro-preview` | 2 | closed → dashboard | 126 | +0.000 [+0.00, +0.00] | 1.000 |
| `gemini-3.1-pro-preview` | 2 | offered → dashboard | 126 | +0.040 [+0.00, +0.10] | 1.000 |
| `gemini-3.8-flash` | 1 | offered → removed-only | 108 | +0.077 [-0.01, +0.20] | 1.000 |
| `gemini-3.8-flash` | 1 | offered → closed | 115 | +0.136 [+0.04, +0.24] | 0.019 ** |
| `gemini-3.8-flash` | 1 | closed → dashboard | 103 | +0.168 [+0.10, +0.24] | 0.012 ** |
| `gemini-3.8-flash` | 1 | offered → dashboard | 108 | +0.324 [+0.17, +0.48] | 0.012 ** |
| `gemini-3.8-flash` | 2 | offered → removed-only | 120 | +0.003 [+0.00, +0.01] | 1.000 |
| `gemini-3.8-flash` | 2 | offered → closed | 120 | +0.133 [+0.00, +0.33] | 0.960 |
| `gemini-3.8-flash` | 2 | closed → dashboard | 126 | +0.011 [-0.01, +0.04] | 1.000 |
| `gemini-3.8-flash` | 2 | offered → dashboard | 120 | +0.142 [+0.00, +0.37] | 1.000 |
| `gemma-4-26b-a4b-it-maas` | 1 | offered → removed-only | 97 | +0.086 [+0.01, +0.20] | 0.012 ** |
| `gemma-4-26b-a4b-it-maas` | 1 | offered → closed | 102 | +0.542 [+0.38, +0.70] | 0.012 ** |
| `gemma-4-26b-a4b-it-maas` | 1 | closed → dashboard | 102 | -0.049 [-0.16, +0.04] | 1.000 |
| `gemma-4-26b-a4b-it-maas` | 1 | offered → dashboard | 108 | +0.509 [+0.34, +0.67] | 0.012 ** |
| `gemma-4-26b-a4b-it-maas` | 2 | offered → removed-only | 126 | +0.000 [+0.00, +0.00] | 1.000 |
| `gemma-4-26b-a4b-it-maas` | 2 | offered → closed | 109 | +0.110 [+0.01, +0.25] | 0.320 |
| `gemma-4-26b-a4b-it-maas` | 2 | closed → dashboard | 109 | +0.000 [+0.00, +0.00] | 1.000 |
| `gemma-4-26b-a4b-it-maas` | 2 | offered → dashboard | 126 | +0.103 [+0.02, +0.24] | 0.102 |

Each withheld pair's outcome is its share of `pass` over the three runs. Pairs answered in every run of both conditions; obligations resampled (2,000 draws, firm by obligation in Study 2); two-sided p-values Holm-corrected across all 24 contrasts; ** marks p < 0.05.
<!-- END GENERATED: table8-contrasts -->

**Repeats are close.** Across the 24 model, study and schema cells, the three runs'
false-green rates differ by at most 0.142, and by 0.06 or less in 21 of them. That bounds
run-to-run variation on one host at temperature 0; it says nothing about variation across
hosts, so it does not license the free-tier single runs of Section 8.2.

**The frontier model behaves like the better free models.** Offered an abstention, Gemini
3.1 Pro reports 0.058 of Study 1's withheld pairs as compliant, inside the free models' range
of 0.042 to 0.142, while detecting 0.433 of violations.

**Decomposing the dashboard schema, Study 1** (Table 8; these are observations about three
models from one provider, not a general law, and the *closed* condition was added after the
*removed-only* results were seen):

- *Removing only `needs_evidence`* significantly raises false greens for Gemma 4 alone
  (+0.086 on pairs it answered in every run). Gemini 3.1 Pro and Flash route unassessable
  pairs to the remaining non-committal verdict, `unmonitored`; Gemini 3.1 Pro sends 109 of
  120 there on average.
- *Removing every non-committal verdict* while keeping `pass` evidence-anchored (*closed*)
  raises false greens significantly for Gemma 4 (+0.542) and Flash (+0.136), and not for
  Gemini 3.1 Pro. Pro avoids false greens there by calling unassessable pairs violations:
  114 of 120, which is itself a wrong answer that sends every one to review.
- *Redefining `pass` and dropping the warning* (*closed* to *dashboard*) raises false greens
  significantly for Gemini 3.1 Pro (+0.081) and Flash (+0.168), and not for Gemma 4, whose
  rate under *closed* is already 0.600.

Each model fails through a different route, so neither safeguard is redundant: an
abstention verdict mattered for two of the three models, and an evidence-anchored definition
of `pass` for two of the three. On Study 2's generated firms no contrast survives correction.
Gemini 3.1 Pro's rise from 0.021 to 0.061 when abstention is removed is not significant
there. Our reading at this point, formed after the results, was that the schema matters most
on exports that carry a populated column next to the missing evidence, as the anchor firm's
do and the Study 2 firms' do not. Study 3 tested it.

### 8.5 Study 3: a preregistered test on fresh firms

Everything in Sections 8.2 to 8.4 that decomposes the schema was formed or extended after
results were seen. Study 3 tests it on data no model had seen, under a declaration committed
before any call (`docs/STUDY3_PREREGISTRATION.md`, with its analysis script): twelve fresh
generated firms (seeds from 1001, 504 pairs each time, 180 withheld), each rendered twice,
*plain* (as in Study 2) and *decoy* (the same firm plus the five adjacent columns of Section
5.3); the four schemas; and seven models from five developers. Three are the Google models
of the Vertex block. Four are open-weights models from other developers served on Vertex AI:
OpenAI's gpt-oss-120b, DeepSeek V3.2, Qwen3 235B and Moonshot's Kimi K2 Thinking. Each cell
was run once. Every cell answered at least 456 of 504 pairs.

The four declared hypotheses, each a positive difference in false-green rate pooled over the
seven models with equal weight, were **all confirmed** (Table 10):

- **P1, abstention effect** (*offered* to *closed*, decoy firms): +0.259 [0.20, 0.33].
- **P2, definition effect** (*closed* to *dashboard*, decoy firms): +0.084 [0.04, 0.12].
- **P3, adjacent columns under the dashboard schema** (plain to decoy): +0.427 [0.29, 0.56].
- **P4, adjacent columns under the recommended schema** (plain to decoy, *offered*): +0.217
  [0.15, 0.29].

Each Holm-adjusted p is 0.002, the smallest the 2,000-draw bootstrap can give after
correction. Each effect is also significant within the Google models and within the other
four developers' models taken separately.

**Table 9 — Study 3, false-green rate by model, arm and schema.**

<!-- BEGIN GENERATED: table9-study3 -->
| Model | Arm | FGR offered | removed-only | closed | dashboard | Recall, offered | False alarm, offered | Min answered |
|---|---|---|---|---|---|---|---|---|
| `gemini-3.1-pro-preview` | plain | 0.106 | 0.189 | 0.206 | 0.294 | 1.000 | 0.000 | 504/504 |
| `gemini-3.1-pro-preview` | decoy | 0.183 | 0.206 | 0.572 | 0.650 | 1.000 | 0.000 | 504/504 |
| `gemini-3.8-flash` | plain | 0.161 | 0.217 | 0.350 | 0.361 | 1.000 | 0.000 | 498/504 |
| `gemini-3.8-flash` | decoy | 0.361 | 0.433 | 0.639 | 0.778 | 1.000 | 0.000 | 471/504 |
| `gemma-4-26b-a4b-it-maas` | plain | 0.339 | 0.333 | 0.406 | 0.411 | 0.230 | 0.084 | 498/504 |
| `gemma-4-26b-a4b-it-maas` | decoy | 0.839 | 0.889 | 0.956 | 0.894 | 0.218 | 0.093 | 494/504 |
| `gpt-oss-120b-maas` | plain | 0.133 | 0.239 | 0.228 | 0.228 | 0.954 | 0.017 | 474/504 |
| `gpt-oss-120b-maas` | decoy | 0.289 | 0.228 | 0.272 | 0.400 | 0.920 | 0.030 | 468/504 |
| `deepseek-v3.2-maas` | plain | 0.111 | 0.211 | 0.189 | 0.267 | 0.529 | 0.131 | 504/504 |
| `deepseek-v3.2-maas` | decoy | 0.306 | 0.411 | 0.767 | 0.772 | 0.655 | 0.127 | 504/504 |
| `qwen3-235b-a22b-instruct-2507-maas` | plain | 0.317 | 0.350 | 0.367 | 0.394 | 0.345 | 0.194 | 489/504 |
| `qwen3-235b-a22b-instruct-2507-maas` | decoy | 0.628 | 0.739 | 0.894 | 0.917 | 0.368 | 0.232 | 494/504 |
| `kimi-k2-thinking-maas` | plain | 0.156 | 0.161 | 0.261 | 0.233 | 0.966 | 0.000 | 474/504 |
| `kimi-k2-thinking-maas` | decoy | 0.161 | 0.339 | 0.489 | 0.583 | 0.977 | 0.034 | 456/504 |

Twelve fresh firms (504 pairs, 180 withheld) per arm, one run per cell. *plain*: generator v2; *decoy*: the same firms with five adjacent-but-insufficient roster columns. False alarm is any non-`pass` verdict on one of the 237 conforming controls.
<!-- END GENERATED: table9-study3 -->

**Table 10 — Study 3, declared tests.**

<!-- BEGIN GENERATED: table10-study3-tests -->
| Estimate | P1 abstention | P2 definition | P3 adjacent cols, dashboard | P4 adjacent cols, offered |
|---|---|---|---|---|
| **Pooled, 7 models (primary)** | +0.259 [+0.20, +0.33] p=0.002 ** | +0.084 [+0.04, +0.12] p=0.002 ** | +0.427 [+0.29, +0.56] p=0.002 ** | +0.217 [+0.15, +0.29] p=0.002 ** |
| Google, 3 models | +0.258 [+0.16, +0.36] p=0.004 ** | +0.069 [+0.01, +0.13] p=0.021 ** | +0.440 [+0.27, +0.61] p=0.004 ** | +0.265 [+0.18, +0.35] p=0.004 ** |
| Other developers, 4 models | +0.260 [+0.18, +0.34] p=0.004 ** | +0.095 [+0.04, +0.14] p=0.004 ** | +0.417 [+0.29, +0.53] p=0.004 ** | +0.181 [+0.12, +0.26] p=0.004 ** |
| `gemini-3.1-pro-preview` | +0.389 [+0.24, +0.55] p=0.014 ** | +0.078 [+0.00, +0.17] p=0.432 | +0.356 [+0.22, +0.50] p=0.014 ** | +0.078 [+0.01, +0.17] p=0.432 |
| `gemini-3.8-flash` | +0.269 [+0.10, +0.46] p=0.014 ** | +0.136 [+0.00, +0.27] p=0.432 | +0.417 [+0.18, +0.64] p=0.015 ** | +0.218 [+0.07, +0.40] p=0.033 ** |
| `gemma-4-26b-a4b-it-maas` | +0.117 [+0.00, +0.25] p=0.432 | -0.006 [-0.02, +0.00] p=1.000 | +0.547 [+0.34, +0.72] p=0.014 ** | +0.500 [+0.29, +0.69] p=0.014 ** |
| `gpt-oss-120b-maas` | -0.020 [-0.12, +0.07] p=1.000 | +0.154 [+0.07, +0.23] p=0.014 ** | +0.174 [+0.08, +0.25] p=0.014 ** | +0.160 [+0.05, +0.30] p=0.015 ** |
| `deepseek-v3.2-maas` | +0.461 [+0.28, +0.62] p=0.014 ** | +0.006 [-0.06, +0.07] p=1.000 | +0.506 [+0.35, +0.66] p=0.014 ** | +0.194 [+0.06, +0.36] p=0.015 ** |
| `qwen3-235b-a22b-instruct-2507-maas` | +0.267 [+0.12, +0.40] p=0.014 ** | +0.035 [-0.04, +0.11] p=1.000 | +0.545 [+0.32, +0.74] p=0.014 ** | +0.311 [+0.19, +0.45] p=0.014 ** |
| `kimi-k2-thinking-maas` | +0.333 [+0.20, +0.49] p=0.014 ** | +0.187 [+0.06, +0.31] p=0.070 | +0.444 [+0.25, +0.63] p=0.015 ** | +0.058 [-0.03, +0.17] p=1.000 |

Difference in false-green rate on withheld pairs answered in both cells, [95% CI] from an obligation-cluster bootstrap (18 firm-by-rule clusters, 2,000 draws), Holm-adjusted p. Holm families as declared: the four pooled tests; the 28 per-model tests; the eight group tests. ** marks adjusted p < 0.05. Pooled estimates weight each model equally.
<!-- END GENERATED: table10-study3-tests -->

**Adjacent columns are the strongest effect, and the most general.** P3 is significant for
every one of the seven models, and P4 for five. The clearest case is the I-9 rules
(exploratory breakdown, `docs/study3/`). When a firm's I-9 export is withheld and nothing
stands beside it, the seven models almost never call a Section 1, Section 2 or
reverification pair compliant: a mean of 0.000 to 0.023 across the four schemas. When the
roster also carries an I-9 status of "Complete" and an onboarding date, the mean rises to
0.193 under the recommended schema and 0.686 under the dashboard. The wage rule is less
clean: even plain firms put the LCA's own offered-wage column beside a missing actual-wage
table, and models call 0.442 of those pairs compliant with abstention offered. Reading the
LCA rate as the required wage is adjacent-field substitution too, though it is the case a
practitioner might call a reasonable inference; we keep the label, which the reference
checker of Section 5.3 shares.

**The two schema effects replicate, but not model by model.** Pooled, removing every
non-committal verdict and redefining `pass` both raise false greens, for Google's models and
for the others alike. Per model, P1 is significant for five of the seven and P2 for one
(gpt-oss-120b, +0.154), so the definition effect is real but smaller and less uniform than
the abstention effect. Removing only `needs_evidence` (secondary analysis S2) raises false
greens by 0.080 pooled (p = 0.004), significantly for Kimi K2 alone. The interaction we
expected, a larger definition effect on decoy firms than on plain ones (S3), was not found:
+0.048 [−0.01, 0.10], p = 0.10. The earlier reading that adjacent columns are what make the
definition of `pass` matter is therefore not supported. Adjacent columns raise false greens
under every schema, and the definition of `pass` matters on both kinds of firm.

**No schema protects fully.** Under the recommended schema, decoy firms still draw false
greens from 0.161 (Kimi K2) to 0.839 (Gemma 4). Detection does not predict safety: Gemini 3.1
Pro, Gemini 3.8 Flash, gpt-oss-120b and Kimi K2 detect at least 0.920 of violations with
abstention offered, yet on decoy firms they call 0.161 to 0.361 of withheld pairs
compliant. With abstention offered, adjacent columns change the false-alarm rate on
conforming controls by at most 0.038 (Table 9), and by at most 0.080 under any schema (S5),
so their cost falls mostly on the false-green side.

**Extension E1.** The four new models were also run once on the Study 1 anchor subset
(Table 11, descriptive). Offered abstention, they report 0.042 to 0.142 of withheld pairs as
compliant and detect 0.200 to 0.400 of violations, inside the ranges of the first nine
models; under the dashboard schema their rate rises to 0.258 to 0.542.

**Table 11 — the four new models on the anchor subset (extension E1).**

<!-- BEGIN GENERATED: table11-e1 -->
| Model | FGR offered | removed-only | closed | dashboard | FG answered only, offered | Recall, offered (of 20) | Answered, offered |
|---|---|---|---|---|---|---|---|
| `gpt-oss-120b-maas` | 0.083 | 0.117 | 0.125 | 0.258 | 0.083 | 0.400 | 140/140 |
| `deepseek-v3.2-maas` | 0.067 | 0.108 | 0.250 | 0.542 | 0.067 | 0.200 | 140/140 |
| `qwen3-235b-a22b-instruct-2507-maas` | 0.142 | 0.167 | 0.258 | 0.308 | 0.155 | 0.250 | 128/140 |
| `kimi-k2-thinking-maas` | 0.042 | 0.175 | 0.167 | 0.267 | 0.042 | 0.350 | 140/140 |
<!-- END GENERATED: table11-e1 -->

---

## 9. Analysis

Each analysis below was specified before any result existed; the exceptions are marked.
Numbers come from `docs/analysis_results.json` (`scripts/analysis.py`) unless a table is
named.

**Which failure dominates.** Offered an abstention, each model misses between 11 and 19 of
the 20 violation labels (counting unanswered pairs as misses) and reports 5 to 17 of the 120
withheld pairs as compliant, so as a rate the missed violation is the larger failure for
every model. No reply line named a pair without a verdict; formatting failures were whole
replies with no usable lines, which appear as unanswered pairs (48 and 72 in Lightning's two
runs, 16 and 12 in Laguna's). Without the abstention each model misses 1 to 10 violations,
and most unassessable pairs become unsupported violations (32 to 99 of 120) or false greens
(21 to 63): the withheld condition buys recall by calling unassessable pairs violations.

**Where abstention is hardest.** The declared hypothesis was that obligations whose evidence
is a *document* (a posting notice, a public access file) show more false greens than those
whose evidence is a *field* (an I-94 expiry), because a missing document is visible only as a
record never expected to exist. Classes were assigned mechanically from each obligation's
"information needed" text, committed before any rate was computed by class: 49 document and
71 field pairs among the 120 withheld (`docs/evidence_class_assignment.txt`). *Result:* in
11 of the 12 runs the document rate is higher. Under `abstain_offered` the totals across
models are 25 false greens in 426 field-pair evaluations against 38 in 294 document-pair
evaluations, about 0.06 against 0.13; the runs share pairs, so we report counts and
direction, not a p-value. The one exception, Lightning without the abstention, holds even
among pairs it answered (0.575 on field pairs against 0.118 on document pairs).

The mechanism, however, is narrower than "documents are harder". The false greens cluster on
obligations whose required item sits *next to* a populated column: a signature flag beside a
signed date, a fee itemisation beside an unitemized deduction total. Several count as
document obligations only because their required item is a presence flag. Where nothing
adjacent is exported, as with the public access file's assembly obligations, the six-year
maximum stay or FDNS site-visit records, no model produced a false green with abstention
offered. We called this *adjacent-field substitution*. It was read off the anchor firm after
the results, and Study 3 then confirmed it under a prior declaration, for all seven models
under the dashboard schema and for five under the recommended one (Section 8.5). It is the
field-level form of what DEMM-Bench calls the container fallacy (Solozobov, 2026).

**Near-miss controls.** The anchor subset has no conforming pair, so its false-alarm rate is
0.000 by construction and carries no information. On the Study 2 firms (Table 7), with
abstention offered, Gemini 3.1 Pro and 3.8 Flash raise no near-miss false alarm and Gemma 4
raises 0.074: boundary cases are not where these models fail.

**The schema ablation.** The interface matters, but not as a single switch. A dashboard
schema significantly raises the false-green rate for eight of the nine models (Tables 3 and
8). Decomposed for the three Google models on the anchor firm (Section 8.4, partly post hoc),
each fails through a different route. Study 3 confirmed both parts on fresh firms and seven
models from five developers: removing every non-committal verdict raises false greens by
0.259 and redefining `pass` by a further 0.084, pooled, with the first effect significant for
five models and the second for one. This is, in a product interface, the incentive Kalai et
al. (2025) describe for benchmarks: formats that give no credit for uncertainty reward
guessing. Two design rules follow, cheap and not redundant: keep a verdict for "could not
tell", and define `pass` as "the required evidence is present and satisfies the obligation".
Neither absolves the models: with both rules in place, false-green rates of 0.04 to 0.15
remain on the anchor firm and 0.16 to 0.84 on firms with adjacent columns, and recall on the
anchor firm is too low for any model to serve as an unsupervised monitor. A third rule
follows from Study 3: since no schema protects against adjacent columns, an export column
that resembles required evidence should be excluded from what the model sees or flagged for
human review.

**Is this only prompt sensitivity?** That language models respond to wording is well known
(Sclar et al., 2024). Three things argue that this is more. The definition of `pass` is not
incidental wording: every compliance dashboard must decide whether green means "satisfied"
or "shown to be satisfied", and that decision is the variable manipulated, with the prompt
otherwise held word for word. The effects replicate on firms no model had seen and across
five developers, in the direction declared before the runs. And the largest effect in the
paper involves no change to the prompt at all: adding five columns to an export raises the
false-green rate by 0.217 to 0.427. The benchmark measures the interaction between an output
contract and the data, which is what a deployed system is.

**Two declared analyses that could not be run.** Evidence-pointer quality needs ground-truth
evidence fields, which the anchor firm's labels do not record; consistency drift needs a
system that reports headline counts, and no model under test does.

**Qualitative failure cases.** To keep excerpts from being the worst lines picked out of
thousands, the rule was fixed in code before any was read: for each model, under
`abstain_offered`, the first `pass` on a withheld pair whose reply cites an evidence field.
Applied as declared, it selected the same line for four of the six free models: a `pass` on
the Section 2 employer signature citing `section2_signed_date`, the label the audit later
overturned. Four models independently reading a populated signed-date column as a signature
suggests the label was at fault (Section 6.1), and the prompt's own example of matching
columns by meaning names that column. Applying the rule again while skipping overturned
pairs, a step added after the first result was seen, gives one excerpt per model on labels
the audit upheld:

- Qwen 3.8 27B and dots.3 Note Preview, independently:
  `h1b.wage.deductions.prohibited.business-expense … pass … pretax_deductions` (dots.3 cites
  `payroll_register`). The payroll export carries only an unitemized deduction total, so no
  prohibited fee can be identified either way; both cite the total as evidence that none was
  taken.
- Nemotron 3 Super 120B: `i9.remote.alternative_procedure … pass … alternative_procedure`.
  The flag is exported; E-Verify good standing, copy retention and the live-video
  attestation the procedure requires are not.
- Nemotron 3 Ultra 550B: `i9.documents.acceptable_list … pass … list_a_doc_title`. A
  document title is cited as evidence that the document was acceptable, though two expiry
  dates are blank and the reverification documents due on 2026-06-15 are not exported.
- Nemotron 3.5 Lightning and Laguna XS 2.1, independently:
  `i9.section2.physical_exam … pass … list_a_doc_title`. Physical examination is inferred
  from the presence of a document title.

Every one is a populated column standing in for the missing evidence beside it. The full
reply lines are in `docs/analysis_results.json`.

---

## 10. Conclusion

A compliance dashboard that reports an obligation as satisfied when its evidence was never
present makes the one error its user cannot see. This benchmark measures that error
directly. An audited anchor firm carries the messiness of real exports; generated firms,
whose every label an independent checker reproduces from the regulations, carry conforming
and boundary cases and can be rendered with or without misleading columns.

Three findings follow, the last two confirmed on fresh firms under a declaration made before
the runs, pooled over seven models from five developers. A dashboard-style schema raises
false greens, significantly for eight of the nine models tested on the anchor firm. Both of
its parts contribute: removing a verdict for "could not tell", and defining `pass` as
"satisfied" rather than "shown to be satisfied". And the largest effect comes from the data,
not the schema: a populated column beside missing evidence is read as that evidence,
significantly for all seven models under the dashboard schema and for five of the seven
under the recommended one. Three design rules follow: keep a
verdict for "could not tell", define `pass` in terms of evidence, and route any export
column that resembles required evidence to human review. The most important missing check
is labelling by practising counsel.

---

## 11. Limitations

**One jurisdiction, one domain.** United States employment-based immigration. We claim the
false-green failure generalises to other regulated domains and claim nothing about whether
performance does.

**No label was validated by a human expert.** The generated labels are reproduced in full
by a checker written independently from the regulations, but its author is an AI agent,
and the checker and the generator could share a misreading of the law; its interpretive
choices are published so that one can be found. The anchor firm's labels come from the
author's company's engine. Two AI auditors audited its withheld labels, and the second found
only half of the strict view's violations evident from the exports. Independent labelling by
practising immigration counsel remains the most important missing check; a blind labelling
kit is released for it.

**The generated firms are narrow.** The generator renders four rule families and withholds
evidence a whole export at a time. Its adjacent columns (Study 3) are five, chosen by us,
and always present in decoy firms; real exports will carry others, and how often a given
column misleads will vary. Two of its rules also simplify the
law. A late reverification is labelled a violation although an H-1B worker whose extension
was timely filed may keep working for up to 240 days (8 C.F.R. 274a.12(b)(20)); the exports
do not show extension filings. And the business-day convention (weekdays, excluding
federal holidays) is consistent with the Form I-9 handbook's example ("If an employee
begins employment on Monday, you must ... complete Section 2 on or before Thursday") but
the handbook does not define the term. The fixed public anchor also does not benefit from
the generator's resistance to contamination.

**Synthetic data does not exercise extraction.** Real deployments read records from
scanned documents through OCR, where a field can be invented from an adjacent label rather
than merely absent. This benchmark starts from clean structured exports and therefore
isolates the verdict layer, which is a deliberate scope choice and also a gap.

**Verdict granularity is coarse.** Real adjudication distinguishes technical from
substantive defects and admits cure periods. Four states do not capture that.


**Results are reported on a 140-pair declared subset of the anchor firm, not all 221
pairs.** Required by the free-tier call ceiling (Section 7.2). The subset keeps every
planted violation and covers every regime, but its smaller denominator widens every
interval.

**Statistics.** Study 1, Study 3 and extension E1 runs were made once each. Intervals
resample obligations, not model runs, so they do not include run-to-run variation; the
Vertex block measures that with three repeats. Study 3's pooled tests rest on 18 clusters
(firm by rule) and weight each model equally. Every family of tests is Holm-corrected; the
per-regime, evidence-class and rule-family breakdowns are descriptive. Only Study 3 was
declared before its results existed; the schema decomposition on the anchor firm was not.

**Model coverage is narrow.** Six models were reached on free tiers, where availability is
decided by provider capacity. Of 15 free chat models screened, only 6 returned a usable
answer to a two-pair request: 5 were rate-limited, 2 refused with a permissions error, 1
returned an upstream failure and 1 an empty completion. Two declared models were withdrawn
mid-study, and one host cut off most replies (coverage 92 and 68 of 140). Vertex AI added
seven more: three from Google, including one frontier model, and open-weights models from
OpenAI, DeepSeek, Alibaba and Moonshot. No closed model from OpenAI or Anthropic was
evaluated, because the study was run without funds beyond the author's cloud credits; whether
those models fail through the same routes is untested.

**Prompts send only regime-relevant exports.** Required by free per-minute token quotas
(Section 7.2). Safeguarded by disclosing withheld exports in the prompt, forbidding
inference about unseen data, falling back to all sources for unclassified regimes, and
asserting in tests that a correct model scores identically either way. It remains a
deviation from sending a firm's complete record, and it produced one defect: Study 2's wage
pairs were sent without the actual-wage export (Section 8.3).

**The label audits are AI audits, and came after results.** Both audits (Section 6.1) were
run by AI models, not by immigration counsel, and both were commissioned after early results
were read. Blindness to model output and coverage of every audited pair limit how far they
could be steered, and every decision is published with its reasoning, but neither is an
expert review. The two auditors overturned 2 and 5 withheld labels with no overlap, which
says the boundary between "present" and "absent" evidence is itself contestable on a few
pairs. One of the auditors, Gemini 3.1 Pro, is also a model under test.

**No human baseline.** We do not know what false-green rate a competent paralegal or
attorney would attain on this task, which would be the most informative reference point of
all.

---

## 12. Ethics and release

**No real personal data.** Every record is synthetic. Generated firms draw names from
generic combinatorial pools; the hand-authored anchor firm's names were written by hand to
be plausible and do not depict any real person. The anchor exports as evaluated contained
plausible personal e-mail addresses and street addresses. In the released data these are
replaced with reserved example domains (RFC 2606) and fictional addresses; no rule reads
either column, so no label or verdict depends on them.

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

**Competing interests.** The author is affiliated with Settle AI Inc., which develops
commercial compliance software for US employment-based immigration. The anchor firm's
expectations were written as the acceptance gate for that company's engine, and the
rulebook is derived from the same company's rule registry. Three safeguards follow from
this. The company's engine is excluded as a baseline (Section 7). The generated firms used
in Studies 2 and 3 take their labels from the generator, not from the engine, and an
independent checker reproduces every one. And the anchor firm's labels were audited blind
twice, including its violation labels (Section 6.1); the second audit's verdict on the
violations is reported in full, although it weakens the engine's labels. A blind labelling kit is released
(`docs/expert_labelling/`) so that anyone with no stake in the labels, including practising
counsel, can check them independently. No such external labelling was done for this paper. No model provider evaluated here was consulted,
and no result was shared with one before publication.

**Use of AI assistance.** An AI coding assistant (Anthropic's Claude) was used to write the
benchmark code, run the experiments and draft the text. A separate Claude agent performed
the first blind label audit and wrote the independent reference checker without access to
the generator or the labels; Gemini 3.1 Pro performed the second audit. All of these are
reported as AI checks, not expert review. Every quantitative claim is recomputed from released artifacts by
`scripts/verify_paper.py`; the author is responsible for all content.

**Release.** Code under Apache-2.0, data and rulebook under CC-BY-4.0, with a datasheet.
The harness requires only the Python standard library and runs offline.

---

## References

Afsharrad, A. and Mousavi, S. S. (2026). ImmigrationReason: A Structured Dataset of U.S. Immigration Appeals for Legal Reasoning Research. arXiv preprint arXiv:2608.20391. https://arxiv.org/abs/2608.20391

Aly, R., Guo, Z., Schlichtkrull, M., Thorne, J., Vlachos, A., Christodoulopoulos, C., Cocarascu, O. and Mittal, A. (2021). FEVEROUS: Fact Extraction and VERification Over Unstructured and Structured information. NeurIPS 2021 Datasets and Benchmarks Track. https://arxiv.org/abs/2106.05707

Amaral, O., Abualhaija, S., Torre, D., Sabetzadeh, M. and Briand, L. C. (2022). AI-enabled Automation for Completeness Checking of Privacy Policies. IEEE Transactions on Software Engineering 48(11). https://doi.org/10.1109/TSE.2021.3124332

Chalkidis, I., Jana, A., Hartung, D., Bommarito, M., Androutsopoulos, I., Katz, D. M. and Aletras, N. (2022). LexGLUE: A Benchmark Dataset for Legal Language Understanding in English. Proceedings of ACL 2022. https://aclanthology.org/2022.acl-long.297

Chen, W., Wang, H., Chen, J., Zhang, Y., Wang, H., Li, S., Zhou, X. and Wang, W. Y. (2020). TabFact: A Large-scale Dataset for Table-based Fact Verification. ICLR 2020. https://arxiv.org/abs/1909.02164

Chow, C. (1970). On optimum recognition error and reject tradeoff. IEEE Transactions on Information Theory 16(1):41-46. https://doi.org/10.1109/TIT.1970.1054406

Dahl, M., Magesh, V., Suzgun, M. and Ho, D. E. (2024). Large Legal Fictions: Profiling Legal Hallucinations in Large Language Models. Journal of Legal Analysis 16(1):64-93. https://arxiv.org/abs/2401.01301

El-Yaniv, R. and Wiener, Y. (2010). On the Foundations of Noise-free Selective Classification. Journal of Machine Learning Research 11:1605-1641. https://jmlr.org/papers/v11/el-yaniv10a.html

Fei, Z., Shen, X., Zhu, D., Zhou, F., Han, Z., Zhang, S., Chen, K., Shen, Z. and Ge, J. (2024). LawBench: Benchmarking Legal Knowledge of Large Language Models. Proceedings of EMNLP 2024. https://aclanthology.org/2024.emnlp-main.452

Gebru, T., Morgenstern, J., Vecchione, B., Vaughan, J. W., Wallach, H., Daumé, H. and Crawford, K. (2021). Datasheets for Datasets. Communications of the ACM 64(12). https://doi.org/10.1145/3458723

Geifman, Y. and El-Yaniv, R. (2017). Selective Classification for Deep Neural Networks. Advances in Neural Information Processing Systems 30. https://arxiv.org/abs/1705.08500

Guha, N., Nyarko, J., Ho, D. E., Ré, C., et al. (2023). LegalBench: A Collaboratively Built Benchmark for Measuring Legal Reasoning in Large Language Models. NeurIPS 2023 Datasets and Benchmarks Track. https://arxiv.org/abs/2308.11462

Guldimann, P., Spiridonov, A., Staab, R., Jovanović, N., Vero, M., Vechev, V., Gueorguieva, A.-M., Balunović, M., Konstantinov, N., Bielik, P., Tsankov, P. and Vechev, M. (2024). COMPL-AI Framework: A Technical Interpretation and LLM Benchmarking Suite for the EU Artificial Intelligence Act. arXiv preprint arXiv:2410.07959. https://arxiv.org/abs/2410.07959

Hendrycks, D., Burns, C., Chen, A. and Ball, S. (2021). CUAD: An Expert-Annotated NLP Dataset for Legal Contract Review. NeurIPS 2021 Datasets and Benchmarks Track. https://arxiv.org/abs/2103.06268

Joren, H., Zhang, J., Ferng, C.-S., Juan, D.-C., Taly, A. and Rashtchian, C. (2024). Sufficient Context: A New Lens on Retrieval Augmented Generation Systems. arXiv preprint arXiv:2411.06037. https://arxiv.org/abs/2411.06037

Kadavath, S., Conerly, T., Askell, A., Henighan, T., Drain, D., Perez, E., et al. (2022). Language Models (Mostly) Know What They Know. arXiv preprint arXiv:2207.05221. https://arxiv.org/abs/2207.05221

Kalai, A. T., Nachum, O., Vempala, S. S. and Zhang, E. (2025). Why Language Models Hallucinate. arXiv preprint arXiv:2509.04664. https://arxiv.org/abs/2509.04664

Kirichenko, P., Ibrahim, M., Chaudhuri, K. and Bell, S. J. (2025). AbstentionBench: Reasoning LLMs Fail on Unanswerable Questions. arXiv preprint arXiv:2506.09038. https://arxiv.org/abs/2506.09038

Lee, G., Chay, W., Cho, S. and Choi, E. (2024). TrustSQL: Benchmarking Text-to-SQL Reliability with Penalty-Based Scoring. arXiv preprint arXiv:2403.15879. https://arxiv.org/abs/2403.15879

Lee, G., Hwang, H., Bae, S., Kwon, Y., Shin, W., Yang, S., Seo, M., Kim, J.-Y. and Choi, E. (2022). EHRSQL: A Practical Text-to-SQL Benchmark for Electronic Health Records. NeurIPS 2022 Datasets and Benchmarks Track. https://arxiv.org/abs/2301.07695

Lin, S., Hilton, J. and Evans, O. (2022). TruthfulQA: Measuring How Models Mimic Human Falsehoods. Proceedings of ACL 2022. https://aclanthology.org/2022.acl-long.229

Luo, Y., Jiang, Y., Xie, Q., Lan, L., Cong, L. W., Rao, A. and Song, Y. (2026). ReguSim: Evaluating LLM Agent Rule Grounding in Financial Compliance. arXiv preprint arXiv:2608.19974. https://arxiv.org/abs/2608.19974

Magesh, V., Surani, F., Dahl, M., Suzgun, M., Manning, C. D. and Ho, D. E. (2025). Hallucination-Free? Assessing the Reliability of Leading AI Legal Research Tools. Journal of Empirical Legal Studies 22(2). https://doi.org/10.1111/jels.12413

Min, S., Krishna, K., Lyu, X., Lewis, M., Yih, W., Koh, P. W., Iyyer, M., Zettlemoyer, L. and Hajishirzi, H. (2023). FActScore: Fine-grained Atomic Evaluation of Factual Precision in Long Form Text Generation. Proceedings of EMNLP 2023. https://aclanthology.org/2023.emnlp-main.741

Mitchell, M., Wu, S., Zaldivar, A., Barnes, P., Vasserman, L., Hutchinson, B., Spitzer, E., Raji, I. D. and Gebru, T. (2019). Model Cards for Model Reporting. Proceedings of FAT* 2019. https://doi.org/10.1145/3287560.3287596

Northcutt, C. G., Athalye, A. and Mueller, J. (2021). Pervasive Label Errors in Test Sets Destabilize Machine Learning Benchmarks. NeurIPS 2021 Datasets and Benchmarks Track. https://arxiv.org/abs/2103.14749

Rajpurkar, P., Jia, R. and Liang, P. (2018). Know What You Don't Know: Unanswerable Questions for SQuAD. Proceedings of ACL 2018. https://aclanthology.org/P18-2124

Ravichander, A., Black, A. W., Wilson, S., Norton, T. and Sadeh, N. (2019). Question Answering for Privacy Policies: Combining Computational and Legal Perspectives. Proceedings of EMNLP-IJCNLP 2019. https://aclanthology.org/D19-1500

Röttger, P., Hofmann, V., Pyatkin, V., Hinck, M., Kirk, H. R., Schütze, H. and Hovy, D. (2024). Political Compass or Spinning Arrow? Towards More Meaningful Evaluations for Values and Opinions in Large Language Models. Proceedings of ACL 2024. https://aclanthology.org/2024.acl-long.816

Sainz, O., Campos, J. A., García-Ferrero, I., Etxaniz, J., Lopez de Lacalle, O. and Agirre, E. (2023). NLP Evaluation in trouble: On the Need to Measure LLM Data Contamination for each Benchmark. Findings of EMNLP 2023. https://aclanthology.org/2023.findings-emnlp.722

Sarkar, D. (2026). A Four-Axis Trustworthiness Benchmark for LLM-as-Judge in Principle-Based Regulation. KDD 2026 Workshop on Secure and Trustworthy Large Language Models. arXiv:2608.14329. https://arxiv.org/abs/2608.14329

Sclar, M., Choi, Y., Tsvetkov, Y. and Suhr, A. (2024). Quantifying Language Models' Sensitivity to Spurious Features in Prompt Design or: How I learned to start worrying about prompt formatting. ICLR 2024. https://arxiv.org/abs/2310.11324

Shportun, N. (2026). ImmigrationQA: A Source-Grounded Dataset and Small-Model Adaptation for U.S. Immigration Law. arXiv preprint arXiv:2605.30589. https://arxiv.org/abs/2605.30589

Solozobov, O. (2026). DEMM-Bench: A Cross-Regime Benchmark for Agent-Runtime Governance-Evidence Sufficiency. arXiv preprint arXiv:2606.20634. https://arxiv.org/abs/2606.20634

Tallam, K. (2026). Partial Evidence Bench: Benchmarking Authorization-Limited Evidence in Agentic Systems. arXiv preprint arXiv:2605.05379. https://arxiv.org/abs/2605.05379

Tam, Z. R., Wu, C.-K., Tsai, Y.-L., Lin, C.-Y., Lee, H. and Chen, Y.-N. (2024). Let Me Speak Freely? A Study On The Impact Of Format Restrictions On Large Language Model Performance. Proceedings of EMNLP 2024: Industry Track. https://aclanthology.org/2024.emnlp-industry.91

Theologitis, M., Dammu, P. P. S., Shah, C. and Suciu, D. (2026). ClaimDB: A Fact Verification Benchmark over Large Structured Data. ACL 2026. arXiv:2601.14698. https://arxiv.org/abs/2601.14698

Thorne, J., Vlachos, A., Christodoulopoulos, C. and Mittal, A. (2018). FEVER: a Large-scale Dataset for Fact Extraction and VERification. Proceedings of NAACL-HLT 2018. https://aclanthology.org/N18-1074

Wang, B., Gao, Y., Li, Z. and Lou, J.-G. (2023). Know What I don't Know: Handling Ambiguous and Unknown Questions for Text-to-SQL. Findings of ACL 2023. https://aclanthology.org/2023.findings-acl.352

Wang, J., Wang, M., Zhou, Y., Xing, Z., Liu, Q., Xu, X., Zhang, W. and Zhu, L. (2025). LLM-based HSE Compliance Assessment: Benchmark, Performance, and Advancements. arXiv preprint arXiv:2505.22959. https://arxiv.org/abs/2505.22959

Wen, B., Yao, J., Feng, S., Xu, C., Tsvetkov, Y., Howe, B. and Wang, L. L. (2025). Know Your Limits: A Survey of Abstention in Large Language Models. Transactions of the Association for Computational Linguistics. https://aclanthology.org/2025.tacl-1.26

Weston, J., Bordes, A., Chopra, S., Rush, A. M., van Merriënboer, B., Joulin, A. and Mikolov, T. (2015). Towards AI-Complete Question Answering: A Set of Prerequisite Toy Tasks. arXiv preprint arXiv:1502.05698. https://arxiv.org/abs/1502.05698

Yin, Z., Sun, Q., Guo, Q., Wu, J., Qiu, X. and Huang, X. (2023). Do Large Language Models Know What They Don't Know? Findings of ACL 2023. https://aclanthology.org/2023.findings-acl.551

Yu, T., Zhang, R., Yang, K., Yasunaga, M., Wang, D., Li, Z., Ma, J., Li, I., Yao, Q., Roman, S., Zhang, Z. and Radev, D. (2018). Spider: A Large-Scale Human-Labeled Dataset for Complex and Cross-Domain Semantic Parsing and Text-to-SQL Task. Proceedings of EMNLP 2018. https://aclanthology.org/D18-1425

Zhang, J. and El-Gohary, N. M. (2016). Semantic NLP-Based Information Extraction from Construction Regulatory Documents for Automated Compliance Checking. Journal of Computing in Civil Engineering 30(2). https://doi.org/10.1061/(ASCE)CP.1943-5487.0000346

Zheng, L., Guha, N., Anderson, B. R., Henderson, P. and Ho, D. E. (2021). When Does Pretraining Help? Assessing Self-Supervised Learning for Law and the CaseHOLD Dataset. ICAIL 2021. https://arxiv.org/abs/2104.08671

---

## Appendix A: Reproduction

```bash
python3 -m nofalsegreen.cli describe                                  # rulebook + anchor stats
python3 -m nofalsegreen.cli score --firm northwind --baseline always_pass
python3 -m nofalsegreen.cli generate --seed 7 --out data/firms/synthetic-000007
python3 scripts/sweep.py --firms 30                                   # reproduces Table 1
python3 tests/test_benchmark.py tests/test_llm_harness.py tests/test_freetier.py  # test suites
```

## Appendix B: Prompt and protocol

The prompts are frozen in `baselines/prompts.py` at `PROMPT_VERSION` 1.1.0 and reproduced
verbatim below. The system prompt is shown for the anchor firm (evaluation date 2026-06-29);
only the verdict menu differs between conditions.

**System prompt, `abstain_offered`:**

```text
You are auditing an employer's immigration-compliance records.

You will be given:
  1. the employer's source data exports, verbatim, as CSV
  2. a list of regulatory obligations, each with the check it performs, its
     citation, and a description of the information needed to decide it
  3. a list of (obligation, entity) pairs to return a verdict for

Evaluate each pair against the data actually present in the exports. Today's
date for the purpose of every deadline calculation is 2026-06-29. Do not use the
real current date.

Two reading rules:
  - Export column names will not match the wording of the obligations. Match
    them by meaning: for example, a column named start_date is the hire date,
    and section2_signed_date is the Section 2 completion date.
  - Reference knowledge is not evidence you need from the exports. Calendars
    and federal holidays, regulatory thresholds, and the evaluation date are
    yours to apply. Only facts about this employer and its workers must come
    from the exports.

Return one line per pair, in this exact format, and nothing else:

  <pair_id>	<verdict>	<evidence_field_or_dash>

Permitted verdicts:
  pass            the required evidence is present in the exports and satisfies the obligation
  fail            the required evidence is present in the exports and violates the obligation
  needs_evidence  the exports do not contain the firm-specific information needed to
                  decide this obligation for this entity, so it cannot be evaluated
                  either way
  unmonitored     the obligation cannot be evaluated from employer export data at all

The distinction between `pass` and `needs_evidence` is the one that matters most.
`pass` asserts you checked and the obligation is met. `needs_evidence` says the
data needed to check was never provided. A document that was not provided is not
a document that is in order.

Return a line for every pair. Do not add commentary, headers, or explanation.
```

**Verdict menu, `abstain_withheld`** (replaces the menu above; everything else identical):

```text
Permitted verdicts:
  pass            the obligation is satisfied
  fail            the obligation is violated

Every pair must receive one of these two verdicts.
```

**Verdict menu, `abstain_removed_only`** (the one-variable ablation of Section 8.4):

```text
Permitted verdicts:
  pass            the required evidence is present in the exports and satisfies the obligation
  fail            the required evidence is present in the exports and violates the obligation
  unmonitored     the obligation cannot be evaluated from employer export data at all

A document that was not provided is not a document that is in order.
```

**Verdict menu, `abstain_closed`** (the second ablation step of Section 8.4):

```text
Permitted verdicts:
  pass            the required evidence is present in the exports and satisfies the obligation
  fail            the required evidence is present in the exports and violates the obligation

A document that was not provided is not a document that is in order.

Every pair must receive one of these two verdicts.
```

**User prompt** for the first batch of the anchor subset, with CSV rows and most
obligations elided here for length (the model receives them in full). It is shown with the
released data; the evaluated prompts carried the earlier e-mail and street strings
(Section 12), which no rule reads.

````text
# Employer: Northwind Robotics, Inc.
# Evaluation date: 2026-06-29

## Source data exports

> Only the exports relevant to these obligations are shown. Not shown: benefits_census_export, greencard_case_export, h1b_cap_export, payroll_register, perm_recruitment_export, rfe_noid_export. Treat the exports below as the complete record for the obligations listed; do not infer that an absent field exists in an export you cannot see.

### cms_case_export  (cms_h1b_cases_export.csv)
```csv
matter_id,matter_type,matter_status,opened_date,client_first_name,client_last_name,client_dob,client_country_of_birth,client_a_number,beneficiary_passport_number,petitioner_company_name,petitioner_fein,receipt_number,priority_date,filing_date,decision_date,attorney_of_record,paralegal,lca_case_number,worksite_address1,worksite_city,worksite_state,worksite_zip,classification,valid_from,valid_to
NWR-2025-0101,H-1B Petition,Approved,2024-11-02,Ravi,Anand,1990-04-11,India,A-301000001,P1000001,"Northwind Robotics, Inc.",91-3055120,WAC2590010001,2024-12-01,2025-01-10,2025-03-20,"Priya Raman, Esq.",Tomás Reyes,I-200-25010-100001,"300 Birch St, Suite 1900",Austin,TX,78701,H-1B,2025-04-01,2028-03-31
NWR-2025-0102,H-1B Petition,Approved,2023-01-09,Lucia,Ferreira,1992-08-19,Brazil,A-301000002,P1000002,"Northwind Robotics, Inc.",91-3055120,WAC2390010002,2023-02-01,2023-02-15,2023-04-22,"Priya Raman, Esq.",Tomás Reyes,I-200-23010-100002,"300 Birch St, Suite 1900",Austin,TX,78701,H-1B,2023-06-01,2029-05-31
...(remaining rows elided here; sent in full)
```

### everify_case_export  (everify_cases_2025.csv)
```csv
case_number,employee_first_name,employee_last_name,client_company_name,case_creation_date,hire_date,case_status,ssa_tnc_date,dhs_tnc_date,fan_delivered_date,employee_decision,employee_decision_date,referral_date,final_result,case_closed_date,last_updated
2025020300010001,Ravi,Anand,"Northwind Robotics, Inc.",2025-02-05,2025-02-03,Employment Authorized,,,,,,,Employment Authorized,2025-02-10,2025-02-10
2023030600010002,Lucia,Ferreira,"Northwind Robotics, Inc.",2023-03-08,2023-03-06,Employment Authorized,,,,,,,Employment Authorized,2023-03-13,2023-03-13
...(remaining rows elided here; sent in full)
```

### hris_roster_export  (bamboohr_active_employees.csv)
```csv
id,employeeNumber,firstName,lastName,middleName,preferredName,displayName,dateOfBirth,ssn,gender,maritalStatus,nationality,workEmail,homeEmail,mobilePhone,address1,city,state,zipcode,country,hireDate,originalHireDate,employmentStatus,jobTitle,department,division,location,supervisor,reportsTo,payRate,payType,payFrequency,standardHoursPerWeek,visaType,passportNumber,status,terminationDate
b1000000-0000-4000-8000-000000000001,NWR-1001,Ravi,Anand,,Ravi,Ravi Anand,1990-04-11,***-**-1001,Male,Married,India,ravi.anand@northwind-robotics.example,ravianand@personal.example,+1-512-555-0101,"900 Maple St, Apt 12",Austin,TX,78701,United States,2025-02-03,2025-02-03,Full-Time,Robotics Software Engineer,Engineering,Technology,Austin - HQ,Grace Lindqvist,Grace Lindqvist,142000,Salary,Annually,40,H-1B,P1000001,Active,
b1000000-0000-4000-8000-000000000002,NWR-1002,Lucia,Ferreira,,Lucia,Lucia Ferreira,1992-08-19,***-**-1002,Female,Single,Brazil,lucia.ferreira@northwind-robotics.example,luciaf@personal.example,+1-512-555-0102,"1500 Cedar Ave, Unit 7",Austin,TX,78701,United States,2023-03-06,2023-03-06,Full-Time,Controls Engineer,Engineering,Technology,Austin - HQ,Grace Lindqvist,Grace Lindqvist,138000,Salary,Annually,40,H-1B,P1000002,Active,
...(remaining rows elided here; sent in full)
```

### i9_record_export  (i9_records_export.csv)
```csv
employee_id,employee_first_name,employee_last_name,start_date,section1_signed_date,section2_signed_date,section2_examiner_name,section2_examiner_title,list_a_doc_title,list_a_doc_number,list_a_doc_issuing_authority,list_a_doc_expiry,list_b_doc_title,list_b_doc_number,list_c_doc_title,list_c_doc_number,alternative_procedure,supplement_b_due,supplement_b_completed_date,everify_case_number
NWR-1001,Ravi,Anand,2025-02-03,2025-02-03,2025-02-13,Olivia Brandt,HR Generalist,Foreign Passport with Form I-94 (H-1B),P1000001,Government of India - Ministry of External Affairs,2028-03-31,,,,,N,,,2025020300010001
NWR-1002,Lucia,Ferreira,2023-03-06,2023-03-06,2023-03-08,Olivia Brandt,HR Generalist,Employment Authorization Document (Form I-766),EAD1000002,U.S. Citizenship and Immigration Services,2026-06-15,,,,,N,2026-06-15,,2023030600010002
...(remaining rows elided here; sent in full)
```

### lca_export  (lca_certified_h1b_2024-2025.csv)
```csv
CASE_NUMBER,CASE_STATUS,RECEIVED_DATE,DECISION_DATE,ORIGINAL_CERT_DATE,VISA_CLASS,JOB_TITLE,SOC_CODE,SOC_TITLE,FULL_TIME_POSITION,BEGIN_DATE,END_DATE,TOTAL_WORKER_POSITIONS,NEW_EMPLOYMENT,CONTINUED_EMPLOYMENT,CHANGE_PREVIOUS_EMPLOYMENT,NEW_CONCURRENT_EMPLOYMENT,CHANGE_EMPLOYER,AMENDED_PETITION,EMPLOYER_NAME,TRADE_NAME_DBA,EMPLOYER_ADDRESS1,EMPLOYER_ADDRESS2,EMPLOYER_CITY,EMPLOYER_STATE,EMPLOYER_POSTAL_CODE,EMPLOYER_COUNTRY,EMPLOYER_PHONE,NAICS_CODE,EMPLOYER_POC_LAST_NAME,EMPLOYER_POC_FIRST_NAME,EMPLOYER_POC_MIDDLE_NAME,EMPLOYER_POC_JOB_TITLE,EMPLOYER_POC_ADDRESS1,EMPLOYER_POC_CITY,EMPLOYER_POC_STATE,EMPLOYER_POC_POSTAL_CODE,EMPLOYER_POC_EMAIL,EMPLOYER_POC_PHONE,AGENT_ATTORNEY_LAST_NAME,AGENT_ATTORNEY_FIRST_NAME,AGENT_ATTORNEY_ADDRESS1,AGENT_ATTORNEY_CITY,AGENT_ATTORNEY_STATE,AGENT_ATTORNEY_POSTAL_CODE,AGENT_ATTORNEY_EMAIL,AGENT_ATTORNEY_PHONE,LAWFIRM_NAME_BUSINESS_NAME,SECONDARY_ENTITY,SECONDARY_ENTITY_BUSINESS_NAME,WORKSITE_WORKERS,WORKSITE_ADDRESS1,WORKSITE_CITY,WORKSITE_COUNTY,WORKSITE_STATE,WORKSITE_POSTAL_CODE,WAGE_RATE_OF_PAY_FROM,WAGE_RATE_OF_PAY_TO,WAGE_UNIT_OF_PAY,PREVAILING_WAGE,PW_UNIT_OF_PAY,PW_TRACKING_NUMBER,PW_WAGE_LEVEL,PW_OES_YEAR,H1B_DEPENDENT,WILLFUL_VIOLATOR,SUPPORT_H1B,STATUTORY_BASIS,PUBLIC_DISCLOSURE
I-200-25010-100001,CERTIFIED,2024-12-05,2024-12-20,2024-12-20,H-1B,Robotics Software Engineer,15-1252,Software Developers,Y,2025-04-01,2028-03-31,1,1,0,0,0,0,0,"Northwind Robotics, Inc.",Northwind Robotics,300 Birch St,Suite 1900,Austin,TX,78701,UNITED STATES OF AMERICA,512-555-0100,541512,Lindqvist,Grace,M,Director of Engineering,300 Birch St Suite 1900,Austin,TX,78701,glindqvist@northwind-robotics.example,512-555-0100,Raman,Priya,500 Willow Ave Suite 1900,Austin,TX,78701,praman@aperture-legal.example,512-555-0190,Aperture Legal Partners LLP,N,,1,300 Birch St,Austin,Travis,TX,78701,140000,150000,Year,138000,Year,P-200-24300-100001,Level II,2024,Y,N,N,,Disclose Business
I-200-23010-100002,CERTIFIED,2023-02-05,2023-02-20,2023-02-20,H-1B,Controls Engineer,17-2199,"Engineers, All Other",Y,2023-06-01,2029-05-31,1,1,0,0,0,0,0,"Northwind Robotics, Inc.",Northwind Robotics,300 Birch St,Suite 1900,Austin,TX,78701,UNITED STATES OF AMERICA,512-555-0100,541512,Lindqvist,Grace,M,Director of Engineering,300 Birch St Suite 1900,Austin,TX,78701,glindqvist@northwind-robotics.example,512-555-0100,Raman,Priya,500 Willow Ave Suite 1900,Austin,TX,78701,praman@aperture-legal.example,512-555-0190,Aperture Legal Partners LLP,N,,1,300 Birch St,Austin,Travis,TX,78701,132000,142000,Year,130000,Year,P-200-22300-100002,Level III,2022,Y,N,N,,Disclose Business
...(remaining rows elided here; sent in full)
```

## Obligations

- fdns.asvvp.actual_wage_ge_petition_wage
    check:     Beneficiary's ACTUAL paid wage ≥ the wage on the petition/LCA (which must itself be the greater of actual or prevailing wage).
    threshold: actualWage ≥ max(actualWageSystemRate, prevailingWage) = the LCA-attested required wage. Compare on the same basis; account for FT/PT and benching.
    citation:  20 CFR 655.731(a)(1)-(2); 8 CFR 214.2(h)(4)(i)(B)(1); penalties 20 CFR 655.810.
    information needed: Per beneficiary: actual pay rate + basis + FT/PT; LCA-attested wage + basis; prevailing-wage determination value/source/level; actual-wage-system rate; payroll evidence; benching/non-productive periods.
- fdns.asvvp.employer_employee_right_to_control
    check:     A bona fide employer-employee relationship with right-to-control exists between petitioner and beneficiary (critical for third-party/client-site placements).
    threshold: Qualitative right-to-control (supervision, assignment, hire/fire/discipline, tools, work-setting indicia). A valid contract/SOW chain from petitioner through intermediaries to the end-client, plus petitioner-retained supervisory control, is the readiness bar.
    citation:  8 CFR 214.2(h)(4)(ii) (United States employer); 8 CFR 214.2(h)(4)(i)(B)(1) (third-party worksite inspection authority); USCIS PM-602-0157 (Contracts and Itineraries).
    information needed: Per beneficiary/placement: placement type (direct vs third-party); end-client + worksite; contract/SOW chain (petitioner→vendor(s)→client) + validity dates; who supervises/assigns; petitioner's legal-presence proof, service-of-process agent, IRS tax ID; itinerary of services.

...(remaining obligations of this batch elided here)

## Pairs to evaluate (12)

everify.photo_matching::Anita Desai	[worker: Anita Desai]
everify.photo_matching::Hiroshi Yamamoto	[worker: Hiroshi Yamamoto]
everify.photo_matching::James Park	[worker: James Park]
everify.photo_matching::Mei Tanaka	[worker: Mei Tanaka]
everify.photo_matching::Yuki Sato	[worker: Yuki Sato]
everify.tnc.employer_action_window::Daniel Cho	[worker: Daniel Cho]
everify.tnc.overdue::Daniel Cho	[worker: Daniel Cho]
extension.filing::Hiroshi Yamamoto	[worker: Hiroshi Yamamoto]
fdns.asvvp.actual_wage_ge_petition_wage::fdns-gap:fdns.asvvp.actual_wage_ge_petition_wage	[employer: fdns-gap:fdns.asvvp.actual_wage_ge_petition_wage]
fdns.asvvp.employer_employee_right_to_control::fdns-gap:fdns.asvvp.employer_employee_right_to_control	[employer: fdns-gap:fdns.asvvp.employer_employee_right_to_control]
fdns.asvvp.entity_physical_existence::fdns-gap:fdns.asvvp.entity_physical_existence	[employer: fdns-gap:fdns.asvvp.entity_physical_existence]
fdns.asvvp.itinerary_when_multiple_sites::fdns-gap:fdns.asvvp.itinerary_when_multiple_sites	[employer: fdns-gap:fdns.asvvp.itinerary_when_multiple_sites]
````

Changing any of these text blocks changes the benchmark. Any edit bumps
`PROMPT_VERSION`, and results carry the version they were produced under.

---

## Appendix C: Protocol history and run log

This appendix holds the sequence of protocol decisions that the main text summarises.
Every decision listed was committed to the repository before the results it governs;
the commit identifiers are in the repository history.

### C.1 The v1.0 pilot and the revision it forced

The protocol above is version 1.1. Version 1.0 was run first, on the same 140 pairs, and
completed four of twelve model-condition runs before we stopped it. We report what it found
because it changed the protocol, and a reader should be able to judge whether the change
was principled.

The pilot showed violation recall of 0.000 for both models whenever the abstention option
was offered. On inspection this was mostly the harness, for three reasons. Thirty of the
140 pairs, including 10 of the 20 planted violations, used rule identifiers absent from the
version 1.0 rulebook and reached the prompt with no obligation text at all. The evidence
list shown for every obligation had been damaged by our extraction into run-together
tokens that matched no export column, and it named reference data no export contains, such
as a federal-holiday calendar. And version 1.0 defined `needs_evidence` as a required field
being absent, so a model that followed the prompt literally was obliged to abstain. In the
clearest case, a Section 2 completed eight business days late, both dates were in the I-9
export, and the model still answered `needs_evidence`.

Version 1.1 fixes these defects and changes nothing else. Every pair's rule is defined.
The evidence description is the manifest's own prose. `needs_evidence` is defined by the
firm's records rather than by field names. The same two reading rules are added to both
ablation conditions. The verdict menus are otherwise unchanged. The evaluated pairs are
identical, fixed in a file before either version ran, so any difference between the pilot
and the main run is attributable to the prompt. The pilot's raw replies and scores are
retained in the repository.

The first attempt at the version 1.1 run exposed one further defect, in the harness
rather than the prompt. We had capped each reply at 8,400 output tokens. Reasoning models
spend most of a reply thinking before they answer, and 46 of the first 84 batch replies
were cut off or came back empty before any verdict was written. The pairs in those
batches would have scored as misses, depressing recall for reasons that had nothing to
do with the models. We raised the cap to 32,000 tokens, which is below every evaluated
model's own limit, and re-requested only the affected batches. The 38 replies that had
finished within the lower cap were kept, because a cap that was never reached did not
affect them. Truncated or empty replies are no longer cached, and the parser now counts
a pair as unparseable only if it is never answered, not each time a model mentions it
while reasoning. The affected attempt is archived intact beside the pilot.

One pilot observation did not depend on the defects. When forced to choose between `pass`
and `fail`, both pilot models called most unassessable obligations violations rather than
compliant, with false-green rates of 0.117 and 0.075. We report version 1.1 as the result
and the pilot only as the account of how the protocol reached its final form.


### C.2 Model substitutions

The study was declared with
six free models. After four of the twelve model-condition runs had completed, OpenRouter
withdrew the free versions of both Nex models (N2.5 Pro and N2.5 Mini); the paid versions
remain, and paying for them was outside the free-tier studies' zero-cost constraint. Three batches of
Nex N2.5 Pro replies had been collected; they cover too few pairs to score and are
reported as an incomplete run, not as a result. Dropping both models would have left four,
three of them from one provider family (NVIDIA Nemotron). We therefore replaced them with
Qwen 3.8 27B and Gemma 4 31B, chosen for provider diversity among the models still free
whose output limit exceeds the 32,000-token cap, with Inkling named in advance as the
substitute should either fail the same two-pair screen the original models passed. Inkling
then turned out to refuse API calls outright (it is served only inside agent applications),
so before any replacement reply existed the fallback was changed to dots.3 Note Preview,
the one remaining free model from a provider family not already in the set. A transient
upstream rate limit is not treated as a screen failure. Both replacements then returned
upstream rate limits on every screen attempt for over an hour, so a cut-off was added,
again before any replacement had answered a benchmark batch: when the sweep reaches a
replacement it screens it once more, and a model that has still never passed yields its
slot to the fallback. The fallback fills at most one slot; a second unscreenable
replacement is dropped and reported as such. Every screen attempt is logged
(`docs/replacement_screen_2026-09-30.json`). The
replacements and the fallback rule were committed on 30 September 2026, before any reply
from either model existed; as with the label views, the commit history is the evidence of
that ordering. The replacements run under the identical prompt, subset, batch size, and
output cap.


### C.4 Departures from the delivery-failure rule

First, Nemotron 3.5
Lightning's
second run never finished normally: its host repeatedly cut replies off at a ten-minute
limit. Under a cut-off rule committed before the final quota window, once every other run
had finished, the run was given one pass that tried each remaining batch up to three times
and was then recorded with what it had answered: 68 of 140 pairs. Second, during that pass
one reply ended with an upstream error *after* delivering all twelve verdict lines. The
harness accepted it because the reply was not empty, contrary to the rule above. We keep
it, since its answer is complete, and the harness has since been corrected to re-request
such replies. It is the only reply in the study that ended without a normal stop.


### C.3 Throughput on free tiers

The OpenRouter free tier allowed 50 requests a day across all free models and 20 a
minute. At batch 12, the Study 1 subset costs 12 calls per model and condition, and each
Study 2 run (six generated firms) costs 24. The runner paces itself under the per-minute
limit, waits patiently on upstream rate limits (which were not charged against the daily
allowance), stops cleanly when the daily ceiling is reached, and resumes from a
checkpoint. Every model response is retained so that any reported number can be traced
back to output.

### C.5 Study 3 operations

Study 3 ran as one process per model and arm, then, for the four slowest models, one per
condition and finally, for gpt-oss-120b, four firm shards per condition, to finish within a
day. Each process kept its own cache file. A shard began from a copy of its condition's
cache, so batches already answered were reused, not requested again, and no request was sent
twice with different results kept. No run ended incomplete. Qwen3 235B's requests were
capped at its served limit of 16,384 tokens, as declared. Before the declaration, the four
open models were sent only a one-word availability probe. The free-tier Study 2 sweep was
stopped once Study 3 was declared; its one completed model's replies are retained in
`docs/study2/` and not reported.
