# No False Green: How Output Schemas and Proxy Columns Lead Language Models to Report Unevidenced Compliance Obligations as Satisfied

Diptopal Roy, Settle AI Inc. (diptopal@joinsettle.info). See *Competing interests*, Section 10.

---

## Abstract

A compliance dashboard that shows an obligation as satisfied when the evidence needed to
assess it was never present makes the one error its user cannot see. We call it a **false
green** and study when language models make it, in employer-side United States immigration
compliance. A system reads an employer's structured exports and returns one of four verdicts
per (obligation, entity) pair: `pass`, `fail`, `needs_evidence` or `unmonitored`. A seeded
generator fixes every label by construction and can render each firm twice: plain, and with
**proxy columns**, populated fields that sit beside the required evidence without being it,
such as an HR onboarding date beside a missing Form I-9 record. In a preregistered study on
twelve fresh firms and seven models from five developers, all four declared hypotheses were
confirmed (Holm-adjusted p = 0.002 each). Proxy columns raise the false-green rate by 0.427
under a pass/fail dashboard schema and by 0.217 even under an evidence-anchored schema that
offers abstention. On proxy-column firms, removing the non-committal verdicts raises it by
0.259, and redefining `pass` as "the obligation is satisfied" (with one warning sentence
dropped) by a further 0.084. Half of the false greens on those firms cite a proxy column as
their evidence, and models that detect nearly every violation still call 16% to 36% of
unassessable pairs compliant. An exploratory study of thirteen models on a hand-authored
firm generated these hypotheses. Every generated label is reproduced by a separately written
checker; no attorney has validated any label. All data, prompts, replies and code are
released.

---

## 1. Introduction

A compliance dashboard makes a claim with every cell it renders. A green cell asserts that a
specific legal obligation, attached to a specific worker or filing, has been assessed and
found satisfied. The claim has a precondition that the rendering does not show: that the
evidence needed to assess it was present. When it was not, a system can say so, decline to
render the cell, or render it green. The third option is attractive for reasons unrelated to
correctness: a mostly green dashboard looks like a working product, and the customer cannot
tell "assessed and fine" from "unassessed" without reading the records the product exists to
read for them. We call it a **false green**.

**A false green is not the mirror image of a false alarm.** A false alarm costs reviewer
time and is extinguished by the review it triggers. A false green triggers nothing, and the
only signal that would surface it is the review it suppresses. In immigration compliance the
cost is concrete. Form I-9 paperwork violations are penalised per form (8 C.F.R.
274a.10(b)(2)) and violations of a Labor Condition Application (LCA), the wage attestation
behind every H-1B petition, per violation (20 C.F.R. 655.810(b)). An I-9 inspection gives at
least three business days' notice (8 C.F.R. 274a.2(b)(2)(ii)), and technical failures can be
corrected within ten business days of notification (8 U.S.C. 1324a(b)(6)(B)), but
substantive ones cannot. A gap found before an inspection can often be remedied; found
during one, it becomes a finding.

**Pass/fail evaluation cannot see it.** An evaluation that labels every item compliant or
violated has no category for "the evidence was not there", so a system that answers `pass`
whenever evidence is absent is never penalised, and on compliant items it scores perfectly.
Two recent benchmarks measure overclaiming under insufficient evidence for agents
(Solozobov, 2026; Tallam, 2026). None does so for regulatory verdicts over a third party's
structured records, where declining to decide is the correct answer for about half of the
items.

<!-- TEXFIGURE: fig_overview | One obligation, one worker, three situations (values illustrative). With the I-9 export present the evidence decides the verdict (a). With it missing the correct verdict is needs_evidence (b). With it missing but an onboarding date beside it, a model may answer pass: a false green (c). A wrong fail sends the item to review; a wrong pass removes it from review. -->

We built an instrument to measure this error and ran three studies. Figure 1 shows the
task. A system receives an employer's data exports and a rulebook of cited obligations, and
returns a verdict per (obligation, entity) pair. Our findings are three.

1. **Proxy columns are the largest cause we found.** Planting five columns that resemble
   required evidence, with the prompt unchanged, raises the false-green rate by 0.427 under a
   dashboard schema and by 0.217 under the recommended one, in a preregistered study. The
   effect is positive in 15 of the 18 firm-by-rule clusters, and half of the resulting false
   greens cite a proxy column as their evidence.
2. **The output schema matters, in two separable parts.** Removing the non-committal verdicts
   and redefining `pass` from "shown to be satisfied" to "satisfied" each raise false greens.
   Both effects are larger on firms with proxy columns.
3. **Detection does not imply safety.** Four models that detect at least 95% of violations
   still call 16% to 36% of unassessable pairs compliant on proxy-column firms.

**Contributions.** (i) A task with four verdict states, in which `needs_evidence` is a scored
output with its own correctness condition, and a stated evidentiary standard (Section 3).
(ii) An instrument: a rulebook of 194 cited obligations, a hand-authored anchor firm, and a
generator whose labels precede its data and which renders paired firms with and without
proxy columns, with every generated label reproduced by a separately written checker
(Section 4). (iii) A preregistered study separating schema effects from proxy-column effects
across seven models (Section 6), and an exploratory study of thirteen models that generated
its hypotheses (Section 7). (iv) A release of every prompt, reply, label and script, with
every number in this paper recomputed from them by a script.

---

## 2. Related work

**Legal NLP and legal hallucination.** LegalBench (Guha et al., 2023), LexGLUE (Chalkidis et
al., 2022), CaseHOLD (Zheng et al., 2021), CUAD (Hendrycks et al., 2021) and LawBench (Fei et
al., 2024) evaluate reasoning over legal *text*; none asks whether the evidence suffices for a
verdict. Dahl et al. (2024) and Magesh et al. (2025) measure unsupported statements about the
law; we measure unsupported statements about a regulated party, where the missing support is
a record. ImmigrationQA (Shportun, 2026) and ImmigrationReason (Afsharrad and Mousavi, 2026)
are petitioner-side and text-side. We know of no public dataset of employer
immigration-compliance records with labelled outcomes, because real ones cannot be published.

**Compliance checking.** Automated checking predates language models, in construction (Zhang
and El-Gohary, 2016) and data protection (Amaral et al., 2022; Ravichander et al., 2019).
COMPL-AI makes the model the regulated subject (Guldimann et al., 2024); HSE-Bench (Wang et
al., 2025), Principle-Bench (Sarkar, 2026) and ReguSim (Luo et al., 2026) make it the
assessor, as here, and ReguSim also takes records as input. None labels insufficiency of the
record as its own correct answer.

**The nearest neighbours.** DEMM-Bench asks whether agent-runtime records suffice to
reconstruct a decision, labels by construction and reports an overclaim rate (Solozobov,
2026). Its "container fallacy", treating the presence of an evidence container as
sufficiency, is the document-level counterpart of the proxy acceptance we measure at the
level of a column. Partial Evidence Bench places evidence outside an agent's authorisation
boundary and scores *unsafe completeness* (Tallam, 2026). We do not claim the directional,
construction-labelled framing as new. We differ in subject (a third-party employer), output
(a regulatory verdict per obligation and entity), the source of insufficiency (what the
exports contain), and in manipulating proxy columns directly.

**Abstention.** From the reject option (Chow, 1970) through selective classification
(El-Yaniv and Wiener, 2010; Geifman and El-Yaniv, 2017), abstention is a cost traded against
coverage. Language-model abstention is evaluated mostly on questions: SQuAD 2.0 (Rajpurkar et
al., 2018), SelfAware (Yin et al., 2023) and AbstentionBench (Kirichenko et al., 2025); Wen et
al. (2025) survey it, and Kadavath et al. (2022) show models can learn what they know. Joren
et al. (2024) come nearest, defining *sufficient context* for retrieval and finding that
strong models answer rather than abstain when it is missing. Hallucination benchmarks against
world knowledge (Lin et al., 2022) or a knowledge source (Min et al., 2023) have no
abstention label. Here abstention is the correct and actionable output for a large share of
items, insufficiency is fixed by construction rather than annotated, and the two wrong
answers on an unassessable item are scored asymmetrically.

**Structured data.** Table fact verification (Chen et al., 2020) and text-to-SQL (Yu et al.,
2018) assumed every item decidable. FEVER's NotEnoughInfo (Thorne et al., 2018), FEVEROUS
(Aly et al., 2021), EHRSQL (Lee et al., 2022), work on unanswerable text-to-SQL questions
(Wang et al., 2023), TrustSQL (Lee et al., 2024) and ClaimDB (Theologitis et al., 2026) add
an insufficiency class over tables and databases; ClaimDB finds that models struggle to
abstain when no evidence decides a claim.

**Output format.** Constraining output changes answers (Tam et al., 2024; Röttger et al.,
2024), and meaning-preserving format changes can swing accuracy by up to 76 points (Sclar et
al., 2024), which is why our prompt is frozen. Kalai et al. (2025) attribute persistent
hallucination partly to grading that gives no credit for uncertainty; our schema conditions
locate the same incentive in a product interface. Generated ground truth has precedent in
bAbI (Weston et al., 2015) and addresses contamination (Sainz et al., 2023); label errors can
change rankings (Northcutt et al., 2021), which is why we validate labels (Section 4). The
release follows datasheet practice (Gebru et al., 2021) and, in requiring the false-green
rate beside violation recall, the spirit of model cards (Mitchell et al., 2019).

---

## 3. Task, evidence standard and metrics

### 3.1 The task

An instance is a firm $F = (S, E, R, a)$: a set $S$ of source exports, a set $E$ of
entities, a rulebook $R$, and a pinned evaluation date $a$. An entity is a worker, an LCA, a
worksite, a wage cohort or the employer. An obligation $r \in R$ carries a regulatory
citation, the entity type it attaches to, and the set $\mathrm{req}(r)$ of items that must be
present for it to be decidable. A **pair** is $(r, e)$ with matching types, and the target is
one of four verdicts (Table 1). Reference knowledge (calendars, federal holidays, thresholds)
is supplied by the system, and export columns are matched to $\mathrm{req}(r)$ by meaning.
If an item of $\mathrm{req}(r)$ is absent for $e$, the pair is **unassessable**: its label is
`needs_evidence`, and any other verdict is wrong whether or not the underlying situation is
compliant. All dates are evaluated against $a$, so planted deadlines never expire.

**Table 1 — The four verdict states.** The vocabulary comes from the source engine (Section
4.4), which separates "not assessable" from "satisfied" because a system that is not counsel
should not state conclusions it has no basis for.

| Verdict | Meaning | Who acts |
|---|---|---|
| `pass` | The required evidence is present and shows the obligation is met | No one: the item leaves review |
| `fail` | The required evidence is present and shows a breach | Reviewer confirms a potential issue |
| `needs_evidence` | A required record is absent, so the obligation cannot be assessed | The firm produces the record |
| `unmonitored` | No employer export could evidence this obligation | Assessed outside the system |

No label in our data is `unmonitored`. A model's `unmonitored` on an unassessable pair is
scored as wrong but is not a false green; in practice it acts as a second abstention, and
Section 7 shows that some models use it that way.

### 3.2 What counts as evidence

The benchmark scores a **primary-record standard**: an obligation is evidenced only by the
record the law requires the employer to keep for it. For I-9 timeliness that is the form
itself, whose section dates the employer must retain and produce for inspection (8 C.F.R.
274a.2(b)(2)); an HR system's I-9 status or onboarding date is the employer's statement
about the form, not the form. For the LCA required wage it is the payroll record of wages
actually paid (20 C.F.R. 655.731(b)(1), (c)) and the employer's actual-wage documentation; a
salary of record is a rate the employer intends to pay.

We adopt this standard because a monitoring product's green cell is read as "an inspector
who asks for the record will find it in order", and only the record itself supports that
reading. A proxy-accepting standard is defensible for *triage*, where a reviewer will look
next. A reader who prefers it should read our proxy-column results as a **proxy-acceptance
rate**, not a rate of legal error. Section 6.3 reports which columns models actually cite,
so the two readings can be told apart.

### 3.3 Metrics

Let $T$ be ground truth and $P$ predictions over pairs. The headline metric is the
**false-green rate**,

$$\mathrm{FGR} = \frac{|\{p : T(p) = \texttt{needs\_evidence} \wedge P(p) = \texttt{pass}\}|}{|\{p : T(p) = \texttt{needs\_evidence}\}|},$$

the share of unassessable pairs reported as satisfied. It is not one minus abstention recall:
answering `fail` on an unassessable pair is wrong, but in a direction that triggers review.
We also report **violation recall** and precision; the **false-alarm rate**, the share of
conforming controls given any verdict other than `pass`, reported separately for
**near-miss controls** placed exactly on the legal boundary; and **abstention precision and
recall**, treating `needs_evidence` as a class. A pair with no parsed verdict counts as an
error for recall but can never be a false green, so a model that answers less looks safer;
every results table therefore reports coverage and the FGR among answered pairs. The
false-green rate must be reported beside violation recall; neither is meaningful alone.

**Table 2 — Trivial baselines.** Across 31 firms (the anchor and 30 generated), averaged over
the firms in which each rate is defined. Reproduced by `python3 scripts/sweep.py --firms 30`.

<!-- BEGIN GENERATED: table1-trivial -->
| System | False green | Violation recall | Precision | False alarm | Abstention F1 |
|---|---|---|---|---|---|
| `always_pass` | 1.000 | 0.000 | — | 0.000 | 0.000 |
| `always_abstain` | 0.000 | 0.000 | — | 1.000 | 0.717 |
| `always_fail` | 0.000 | 1.000 | 0.170 | 1.000 | 0.000 |
| `oracle` | 0.000 | 1.000 | 1.000 | 0.000 | 1.000 |

A dash marks a rate undefined for that system: `always_pass` and `always_abstain` never predict a violation, so their precision has no denominator.
<!-- END GENERATED: table1-trivial -->

`always_pass` raises no false alarm, the best possible score on compliant items, while
reporting all 723 unassessable pairs as satisfied; only the false-green rate separates it
from a careful system. `always_abstain` scores 0.000 on it and 0.717 abstention F1 (0.953 on
the anchor firm, which has no controls) while detecting nothing, so abstention scores are
gameable in isolation. The oracle, which reads the label basis, scores 1.000 on every axis:
the labels are internally consistent and decidable from the information each was built
from.

---

## 4. The instrument

### 4.1 The rulebook

The rulebook contains 194 obligations across ten regimes: I-9 and E-Verify (28), Labor
Condition Application (23), Public Access File (15), wage and prevailing wage (21), H-1B
status (16), I-129 supplement (13), L-1 (21), F-1 OPT and STEM OPT (15), site-visit readiness
(14), and cross-cutting deadlines and penalties (28). Each carries its check, threshold,
regulatory citation and the information needed to decide it. The source manifest lists 196
entries; two rules appear in two regimes and are counted once. The rulebook is built
programmatically from the source engine's registry, whose citations its maintainers (the
author's company) had verified against primary sources; that was not an independent legal
review. The anchor firm also refers to 17 rules by engine identifiers, mapped to manifest
rules through the engine's published alias table. Table 3 shows how much of the rulebook each
part of the instrument exercises.

**Table 3 — Coverage of the rulebook.**

| Component | Obligations exercised | Regimes | Pairs | Label source |
|---|---|---|---|---|
| Rulebook | 194 | 10 | — | Cited regulation per obligation |
| Anchor firm | 112 | 8 | 221 | Source engine, audited twice |
| Anchor subset (Section 7) | 76 | 8 | 140 | As above |
| Generator | 4 | 2 | 42 per firm | By construction, independently re-derived |

### 4.2 The generator and its proxy columns

The generator's central property is that **labels precede data**. For each applicable pair
it first draws a disposition and then writes records that decide it: `planted_violation`
(the records show a breach), `planted_control` (they show conformity, a configured share
placed exactly on the legal boundary as near-miss controls), or `withheld_evidence` (the
export carrying the required information is not provided). It renders four rule families
completely: I-9 Section 1 timeliness, Section 2 timeliness (three business days, excluding
weekends and federal holidays with their observed dates), reverification by the expiry of
temporary authorisation, and the LCA required wage (wages paid at least the greater of the
prevailing wage and the employer's actual wage). Evidence is withheld a whole export at a
time, because a blank date for a past deadline reads to a practitioner as "not done", which
is a violation. A firm has twelve workers, nine of them on H-1B status, and 42 pairs. A first
version of the generator failed a blind consistency check (8 of 60 sampled labels agreed with
its records) and was withdrawn (Appendix C).

<!-- TEXFIGURE: fig_proxy | Study 3 firm 1018 as generated, rendered plain and with proxy columns. Both withhold the I-9 export, so every I-9 pair is unassessable in both. The proxy rendering adds five roster columns (shaded) that resemble evidence without being it; every label and every other export is identical. -->

**Proxy columns (generator v3).** For Study 3 the generator can add five roster columns that
sit beside the evidence a rule needs (Figure 2): an I-9 status of "Complete", an onboarding
completion date, the current authorisation's end date, a salary of record set at the LCA
offered wage, and an internal pay-band midpoint. The columns appear in every such firm,
whether or not the export they imitate is withheld, so their presence reveals nothing. They
are drawn from a separate random stream, so a plain firm and its proxy twin have identical
labels and identical other exports. The wage rule already has a proxy in plain firms: the
LCA's own offered wage sits beside a missing actual-wage table.

### 4.3 Validating the generated labels

A separate AI agent wrote a deterministic checker for the four rules from the regulations
(8 C.F.R. 274a.1–274a.2, the M-274 handbook, 20 C.F.R. 655.731), without access to the
generator's code or to any label, recording every interpretive choice with its source
(`labelcheck/INTERPRETATIONS.md`). Run on every generated firm used or audited here, it first
disagreed on one label, exposing a generator bug: a New Year's Day that falls on a Saturday is
observed on the preceding Friday, which the generator's calendar missed. The bug touched one
pair on an audit seed and no study firm. After the fix the two derivations agree on all
1,176 distinct labels (1,680 counting the proxy twins, whose labels are identical by
construction; `docs/labelcheck_results.json`).

The agreement is less independent than two human annotators: both programs were written by
AI agents of one model family, and both apply the primary-record standard of Section 3.2. The
checker's boundary choices are therefore stated with their sensitivity. Across the checked
firms, 70 Section 2 dates fall exactly on the deadline day; counting weekdays without
excluding federal holidays would change 6 verdicts, and counting calendar days 55.

### 4.4 The anchor firm and its labels

The anchor firm (Northwind Robotics) is a hand-authored employer of twelve workers, nine on
H-1B status, with eleven source exports totalling 93 data rows: HR roster, case management,
certified LCAs, I-9 records, E-Verify cases, payroll, RFE and NOID cases, cap cases,
green-card cases, PERM recruitment and benefits census. Most workers carry one planted
mechanism (Table 4). It has 221 pairs, 20 labelled violations and 201 evidence requests, and
no `pass` labels, so it cannot measure false alarms. The share of evidence requests reflects
which obligations the source engine can assess from exports, a design choice rather than a
property of real employers.

**Table 4 — Representative plants in the anchor firm.**

| Mechanism | Planted signal |
|---|---|
| I-9 Section 2 timeliness | Section 2 completed 8 business days after start, against a 3-day limit |
| Reverification deadline | Employment authorisation document expired 14 days before the evaluation date, no reverification recorded |
| E-Verify notice window | Notice delivered, no employee decision recorded, well past the response window |
| LCA expiration | Certified period ending 4 days after the evaluation date |
| Required wage | Salary equals the certified rate but falls below the prevailing wage |
| Material change, worksite | Roster location differs from the filing's area of intended employment |

**The anchor labels are the paper's weakest component, and we use them accordingly.** They
were written as the acceptance gate for the source engine, a commercial compliance product of
the author's company, where `fail` means "requires action" rather than "the records show a
breach". Four facts carry two violation labels each, so the 20 labels describe 16 facts. Five
"actual-wage memo missing" labels have no evidence in any export, and five are deadlines not
yet passed on the evaluation date; a **strict view**, fixed before any per-pair result was
read, relabels the first five as evidence requests and removes the second five. Two blind AI
audits of the 120 evaluated evidence requests overturned 2 and 5 labels with no pair in
common (raw agreement 113 of 120, Cohen's $\kappa$ = −0.024: the auditors agree that the
labels mostly stand, and not on which few are wrong). Judging the violation labels, the second
auditor found 7 of 20 shown by the exports, and 5 of the strict view's 10. We therefore use the
anchor firm as a **realism probe for false greens**, which do not depend on any violation
label, and report its violation recall only as agreement with the engine. Appendix D gives
both audits, the label views and the per-pair decisions.

The released benchmark comprises 31 firms (the anchor and 30 generated at seeds 1-30), 1,481
pairs, 723 of them unassessable (48.8%), and 238 planted violations; further firms are
available at any seed.

---

## 5. Models and protocol

**Prompt.** The protocol is frozen in code (`baselines/prompts.py`, `PROMPT_VERSION` 1.1.0;
Appendix B gives it verbatim). Each request carries the source exports verbatim as CSV, the
batch's obligations with check, threshold, citation and the information needed, and twelve
pairs to decide; the evaluation date is pinned. Columns are matched by meaning, and reference
knowledge is the model's to supply. Each reply line gives a pair, a verdict and the evidence
field relied on.

**Schema conditions.** Four verdict menus form a ladder (Table 5); everything else in the
prompt is identical across them.

**Table 5 — The schema conditions.** Each row changes the row above it in the listed ways.

| Condition (code name) | Verdicts permitted | Definition of `pass` | Instruction text | Change from the row above |
|---|---|---|---|---|
| offered (`abstain_offered`) | pass, fail, needs_evidence, unmonitored | "the required evidence is present in the exports and satisfies the obligation" | Paragraph on why `pass` vs `needs_evidence` matters, ending "A document that was not provided is not a document that is in order." | — |
| removed-only (`abstain_removed_only`) | pass, fail, unmonitored | as above | Closing sentence only | `needs_evidence` and the paragraph's first three sentences removed |
| closed (`abstain_closed`) | pass, fail | as above | Closing sentence; "Every pair must receive one of these two verdicts." | `unmonitored` removed; every pair must be decided |
| dashboard (`abstain_withheld`) | pass, fail | "the obligation is satisfied" | "Every pair must receive one of these two verdicts." | `pass` and `fail` redefined; closing sentence removed |

The step from *offered* to *closed* is the **abstention effect**; besides removing both
non-committal verdicts it removes three sentences of instruction about them. The step from
*closed* to *dashboard* is the **definition-and-warning effect**: it changes the definitions
of both verdicts and removes one sentence, so it cannot separate the two.

**Models.** Thirteen models from eight developers. Six were reached on free API tiers for the
exploratory study: Nemotron 3 Ultra 550B, Nemotron 3 Super 120B and Nemotron 3.5 Lightning
(NVIDIA), Laguna XS 2.1 (Poolside), Qwen 3.8 27B (Alibaba) and dots.3 Note Preview
(dots-studio). Seven were served on Google's Vertex AI and paid from the author's cloud
credits: Gemini 3.1 Pro, Gemini 3.8 Flash and Gemma 4 26B (Google), and the open-weights
gpt-oss-120b (OpenAI), DeepSeek V3.2, Qwen3 235B A22B Instruct (Alibaba) and Kimi K2 Thinking
(Moonshot). Every request uses temperature 0 and an output cap of 32,000 tokens, reasoning
tokens included (16,384 for Qwen3 235B, its served limit).

**Scoring safeguards.** A reply line naming a pair without a recognised verdict yields no
prediction and is never coerced to any verdict; we report the unparseable rate. A verdict
outside the condition's menu is kept and counted as off-schema. Empty, cut-off or
error-ended replies are delivery failures and are re-requested; a run is never recorded as
finished while such a batch is missing. Each request carries only the exports relevant to its
batch's regimes (with the roster always included and a fall-back to all sources for
unclassified regimes), and the prompt names the exports not sent and tells the model not to
infer their contents. One defect in that scoping, found before Study 3, is disclosed in
Appendix E. The source engine is not evaluated as a baseline: its rules and the anchor labels
were developed against each other. Appendix C records the protocol history.

---

## 6. A preregistered study of schemas and proxy columns

### 6.1 Design

Study 3 was declared in a file committed before any Study 3 call (`docs/STUDY3_PREREGISTRATION.md`,
commit `e1baaeb`), with its analysis script. It uses the first twelve seeds from 1001 upward
that withhold at least one export and leave at least one rule family decidable: 504 pairs,
180 of them unassessable, 87 violations and 237 conforming controls. Each firm is rendered
plain and with proxy columns, and run under the four schemas with the seven Vertex models,
once per cell. Every cell answered at least 456 of 504 pairs.

The outcome is the false-green indicator on an unassessable pair. A contrast uses the pairs
answered in both cells, averaged within each model and then over models with equal weight.
Uncertainty comes from a bootstrap over the 18 (firm, rule) clusters of unassessable pairs,
with 2,000 draws shared across models. The 18 clusters are unbalanced: 9 wage-rule clusters
from 9 firms, and 9 I-9 clusters from only 3 firms, since a firm that withholds its I-9
export makes all three I-9 rules unassessable at once. The p-values are two-sided, with a
floor of 1/2,000. Four primary hypotheses, all predicting increases and Holm-corrected
together, were declared: **P1**, the abstention effect, and **P2**, the definition-and-warning
effect, both on proxy-column firms; **P3** and **P4**, the effect of proxy columns under the
dashboard and offered schemas.

### 6.2 Results

All four declared hypotheses were confirmed, each at the bootstrap's floor (Holm-adjusted
p = 0.002):

- **P1, abstention effect:** +0.259 [0.20, 0.33].
- **P2, definition-and-warning effect:** +0.084 [0.04, 0.12].
- **P3, proxy columns under the dashboard schema:** +0.427 [0.29, 0.56].
- **P4, proxy columns under the offered schema:** +0.217 [0.15, 0.29].

Each is also significant within the three Google models and within the four from other
developers taken separately. Because a floor p-value on 18 clusters is a weak summary, we
also count clusters. Averaged over models, the proxy-column effect is positive in 15 of the
18 clusters under the dashboard schema (2 negative, 1 zero) and in 16 under the offered
schema (2 negative).

<!-- FIGURE: fig_study3_multiples | wide | False-green rate on the 180 unassessable pairs of the Study 3 firms, by schema, for plain firms (hollow) and the same firms with proxy columns (filled). The last panel is the mean of the seven models. Proxy columns raise the rate for every model under the dashboard schema, and the gap widens as the schema loosens. -->

<!-- FIGURE: fig_forest | wide | The declared tests of Study 3: pooled, by developer group and per model, with 95% bootstrap intervals. Filled markers are significant after Holm correction within their family (the four pooled tests; the eight group tests; the 28 per-model tests). Pooled effects are robust; per-model effects vary, most of all P2. -->

The pooled effects are robust (Figure 3), but the models differ (Figure 4). The proxy-column
effect is the most uniform: P3 is significant for all seven models and P4 for five (not
Gemini 3.1 Pro or Kimi K2). The abstention effect is significant for five models (not Gemma 4
or gpt-oss-120b). The definition-and-warning effect is significant for one, gpt-oss-120b
(+0.154), so it is real on average and small or absent for most models individually. In
secondary analyses, removing only `needs_evidence` raised false greens by 0.080 pooled
(p = 0.004), significantly only for Kimi K2. The interaction we declared, a larger
definition-and-warning effect on proxy-column firms than on plain ones, was not found:
+0.048 [−0.01, 0.10], p = 0.10. Full tables are in Appendix F.

### 6.3 Exploratory analyses

The analyses in this subsection were not declared; we added them after the results, several
at a reviewer's request, and they test nothing.

**The schema effects are smaller on plain firms.** P1 and P2 were declared on proxy-column
firms only. With the same estimator on plain firms (Table 6), both effects are present but
less than half the size: +0.093 for abstention and +0.035 for definition and warning. So the
schema and the proxy columns compound: the schema matters most where proxy columns are
present, although the declared interaction test could not distinguish the two definition
effects.

**Table 6 — Schema contrasts on plain and proxy-column firms.**

<!-- BEGIN GENERATED: table-arm-contrasts -->
| Change of schema | Plain firms (exploratory) | Proxy firms (declared test) |
|---|---|---|
| Abstention: offered → closed | +0.093 [+0.04, +0.16], p < 0.001 unadjusted | +0.259 [+0.20, +0.33], Holm p = 0.002 |
| Definition and warning: closed → dashboard | +0.035 [+0.01, +0.06], p = 0.008 unadjusted | +0.084 [+0.04, +0.12], Holm p = 0.002 |

Pooled over the seven models with equal weight; same pairs, clusters and bootstrap draws as the declared analysis. The plain-firm column was computed after the results and is not part of any declared family.
<!-- END GENERATED: table-arm-contrasts -->

<!-- FIGURE: fig_rule_family | 0.82\textwidth | False-green rate by rule family, mean of the seven models (exploratory). I-9 rules: 3 firms withhold the I-9 export. Wage rule: 9 firms withhold payroll or the actual-wage table. Without proxy columns, models almost never call a missing I-9 record compliant; with them, they often do. The wage rule's plain firms already carry a proxy, the LCA's offered wage. -->

**Where proxy columns act.** For the I-9 rules (Figure 5), models with no proxy column almost
never call a pair compliant when the I-9 export is missing: 0.000 to 0.023 across the four
schemas. With proxy columns the rate rises to 0.193 under the offered schema and 0.686 under
the dashboard. This rests on three firms, the ones that withhold the I-9 export. The wage rule
is high even on plain firms, where models call 0.442 of those pairs compliant with abstention offered, because the LCA's offered wage already sits
beside the missing actual-wage table. This is the case a practitioner might most readily call
a reasonable inference.

**Models cite the proxy columns.** Every reply line names the evidence relied on, so the
mechanism can be read directly (Table 7). On proxy-column firms, 1,376 of the 2,807 false
greens (49%) cite one of the five planted columns. For the I-9 rules under the offered schema
it is 118 of 134 (88%), almost all the onboarding date or the current authorisation's end
date. On plain firms, wage-rule false greens most often cite the LCA's offered wage. The
I-9 status column, the most document-like of the five, was never cited, so what models take
as evidence is a date or an amount that looks like the required one, not a status flag. Under
the dashboard schema more false greens cite other fields, consistent with a schema that asks
only whether the obligation is satisfied.

**Table 7 — The column cited as evidence on each false green, Study 3.**

<!-- BEGIN GENERATED: table-cited -->
| Rule family | Firms | Schema | False greens | Cite a planted proxy column | Cite the LCA offered wage | Other |
|---|---|---|---|---|---|---|
| I-9 (3 rules) | plain | offered | 0 | 0 | 0 | 0 |
| I-9 (3 rules) | plain | dashboard | 16 | 0 (0%) | 0 (0%) | 16 (100%) |
| I-9 (3 rules) | proxy | offered | 134 | 118 (88%) | 0 (0%) | 16 (12%) |
| I-9 (3 rules) | proxy | dashboard | 462 | 276 (60%) | 0 (0%) | 186 (40%) |
| LCA required wage | plain | offered | 238 | 0 (0%) | 98 (41%) | 140 (59%) |
| LCA required wage | plain | dashboard | 378 | 0 (0%) | 122 (32%) | 256 (68%) |
| LCA required wage | proxy | offered | 364 | 123 (34%) | 119 (33%) | 122 (34%) |
| LCA required wage | proxy | dashboard | 437 | 124 (28%) | 45 (10%) | 268 (61%) |

Pooled over the seven models. A false green is a `pass` on an unassessable pair; the column is the evidence field the reply line names. Planted proxy columns: `onboardingCompletedDate`, `workAuthValidThrough`, `annualBaseSalary`, `payBandMidpoint`, `i9Status` (never cited). Exploratory: added after the results.
<!-- END GENERATED: table-cited -->

<!-- FIGURE: fig_detection_vs_safety | 0.48\textwidth | Violation recall on plain firms against the false-green rate on proxy-column firms, offered schema, one point per model. The four models that detect nearly every violation still report between 16% and 36% of unassessable pairs as compliant. -->

**Detection does not imply safety.** Gemini 3.1 Pro, Gemini 3.8 Flash, gpt-oss-120b and Kimi
K2 detect at least 0.954 of violations on plain firms with abstention offered, yet on
proxy-column firms they call 0.161 to 0.361 of unassessable pairs compliant (Figure 6). A
recall-based evaluation would rank these models highest without revealing this. Proxy columns
cost little on the other side: with abstention offered they change the false-alarm rate on
conforming controls by at most 0.038, and by at most 0.080 under any schema, so their cost
falls mostly on the false-green side.

---

## 7. The exploratory study that generated the hypotheses

Before Study 3, we ran all thirteen models on a declared stratified subset of the anchor firm:
140 of its 221 pairs, containing every planted violation and 120 evidence requests sampled in
proportion to regime, fixed by a seed before any model was scored. The six free-tier models
were run once under the offered and dashboard schemas. Gemini 3.1 Pro, Gemini 3.8 Flash and
Gemma 4 were run three times under all four schemas; across those 24 model, study and schema
cells (including Study 2, Appendix E) the three runs' false-green rates differ by at most
0.142, and by 0.06 or less in 21 of them. The four further models were run once each, with
Study 3. The two schema conditions between offered and dashboard were added after the first
results, which is why this study is exploratory.

**Table 8 — All thirteen models on the anchor subset.**

<!-- BEGIN GENERATED: table-anchor-all -->
| Model | Developer | Runs | Answered (offered) | FGR offered | FGR offered, answered only | Recall offered (of 20) | FGR dashboard | Change significant? |
|---|---|---|---|---|---|---|---|---|
| dots.3 Note Preview | dots-studio | 1 | 140/140 | 0.100 | 0.100 | 0.450 | 0.525 | yes (p = 0.003) |
| Nemotron 3 Super 120B | NVIDIA | 1 | 140/140 | 0.050 | 0.050 | 0.300 | 0.175 | yes (p = 0.012) |
| Nemotron 3 Ultra 550B | NVIDIA | 1 | 140/140 | 0.067 | 0.067 | 0.300 | 0.217 | yes (p = 0.003) |
| Nemotron 3.5 Lightning | NVIDIA | 1 | 92/140 | 0.042 | 0.059 | 0.050 | 0.208 | yes (p = 0.012) |
| Laguna XS 2.1 | Poolside | 1 | 124/140 | 0.125 | 0.135 | 0.200 | 0.433 | yes (p = 0.003) |
| Qwen 3.8 27B | Alibaba | 1 | 140/140 | 0.142 | 0.142 | 0.350 | 0.417 | yes (p = 0.003) |
| Gemini 3.1 Pro | Google | 3 (mean) | 140/140 (min) | 0.058 | 0.058 | 0.433 | 0.131 | no (p = 1.000) |
| Gemini 3.8 Flash | Google | 3 (mean) | 140/140 (min) | 0.094 | 0.094 | 0.500 | 0.419 | yes (p = 0.012) |
| Gemma 4 26B | Google | 3 (mean) | 140/140 (min) | 0.153 | 0.153 | 0.067 | 0.589 | yes (p = 0.012) |
| gpt-oss-120b | OpenAI | 1 | 140/140 | 0.083 | 0.083 | 0.400 | 0.258 | not tested |
| DeepSeek V3.2 | DeepSeek | 1 | 140/140 | 0.067 | 0.067 | 0.200 | 0.542 | not tested |
| Qwen3 235B | Alibaba | 1 | 128/140 | 0.142 | 0.155 | 0.250 | 0.308 | not tested |
| Kimi K2 Thinking | Moonshot | 1 | 140/140 | 0.042 | 0.042 | 0.350 | 0.267 | not tested |

FGR over the 120 unassessable pairs of the 140-pair anchor subset; unanswered pairs cannot be false greens, so the answered-only column guards against coverage effects. Change: offered to dashboard, paired on pairs answered in both; Holm across the six single-run models, and across 24 contrasts for the three repeated-run models. The last four models were added with Study 3 and run once, descriptively. Recall is against the source engine's violation labels (Section 4.4).
<!-- END GENERATED: table-anchor-all -->

**False greens persist when abstention is offered.** The thirteen models report 0.042 to
0.153 of the anchor firm's unassessable pairs as satisfied with abstention offered, and 0.131
to 0.589 under the dashboard schema (Table 8). The dashboard schema raised the rate
significantly for all six single-run models (Holm across six) and for two of the three
repeated-run models (Holm across 24 contrasts; not Gemini 3.1 Pro), so eight of the nine
models we tested for it; the four further models were run descriptively. Violation recall is
low (0.050 to 0.500 against the engine's labels): models answer `needs_evidence` on violations
whose evidence is present. The strict and audited label views change false-green rates by at
most 0.021 and change no condition effect (Appendix D).

<!-- FIGURE: fig_verdict_routes | wide | Where the anchor subset's 120 unassessable pairs go under each schema, for the three repeated-run models (mean of three runs). Removing needs_evidence alone sends most of them to unmonitored, not to pass; removing every non-committal verdict sends Gemini 3.1 Pro's to fail and Gemma 4's to pass. -->

**Models fail through different routes.** Decomposed for the three repeated-run models
(Figure 7), removing only `needs_evidence` significantly raised false greens for Gemma 4 alone
(+0.086); Gemini 3.1 Pro sent 109 of 120 unassessable pairs to `unmonitored` instead.
Removing every non-committal verdict raised false greens for Gemma 4 (+0.542) and Gemini 3.8
Flash (+0.136); Gemini 3.1 Pro instead called 114 of 120 pairs violations, which is also wrong
but sends every one to review. Redefining `pass` and dropping the warning raised false greens
for Gemini 3.1 Pro (+0.081) and Flash (+0.168), and not for Gemma 4, whose rate under *closed*
was already 0.600. On the six Study 2 generated firms, which have no proxy columns, no
contrast survives correction (Appendix E). These observations are what Study 3 was
designed to test.

**Where the false greens fell.** Under the offered schema, three regimes (I-9 and E-Verify,
prevailing wage, and the LCA rules) hold almost every false green on the anchor firm (Appendix
Figure 9). A declared comparison found more false greens on obligations whose evidence is a
document than on those whose evidence is a field, in 11 of the 12 single-run model and schema
combinations; but the false greens cluster on items whose required evidence sits next to a
populated column. Where nothing adjacent is exported, as for the public access file's assembly
obligations, the six-year maximum stay or site-visit records, no model produced a false green
with abstention offered. A rule fixed in code before any reply was read selected one false
green per model:

- Qwen 3.8 27B and dots.3 Note Preview, independently:
  `h1b.wage.deductions.prohibited.business-expense … pass … pretax_deductions`. The payroll
  export carries only an unitemized deduction total, so no prohibited fee can be identified
  either way; both cite the total as evidence that none was taken.
- Nemotron 3 Super 120B: `i9.remote.alternative_procedure … pass … alternative_procedure`. The
  flag is exported; the E-Verify standing, copy retention and live-video attestation the
  procedure requires are not.
- Nemotron 3 Ultra 550B: `i9.documents.acceptable_list … pass … list_a_doc_title`. A document
  title is cited as evidence that the document was acceptable.
- Nemotron 3.5 Lightning and Laguna XS 2.1, independently:
  `i9.section2.physical_exam … pass … list_a_doc_title`. Physical examination is inferred from
  the presence of a document title.

Each is a populated column standing in for the record beside it. Study 3 planted such columns
deliberately.

---

## 8. Discussion

**Design rules.** Three follow, each cheap. Keep a verdict for "could not tell", since
removing the non-committal verdicts raised false greens for five of seven models in Study 3.
Define `pass` as "the required evidence is present and satisfies the obligation", not "the
obligation is satisfied". And treat any export column that resembles required evidence as a
hazard: exclude it from what the model sees, or route the obligations it touches to human
review, since no schema we tested protected against it. Neither of the first two rules
absolves the models: with both in place, false-green rates of 0.04 to 0.15 remain on the
anchor firm and 0.16 to 0.84 on firms with proxy columns.

**Is this only prompt sensitivity?** That models respond to wording is well known (Sclar et
al., 2024). Three things suggest more is happening here. The schema changes are not
incidental: every compliance dashboard must decide what its verdicts mean, and Table 5 lists
exactly what each condition changes. The effects replicate on fresh firms and across five
developers, in the direction declared before the runs. And the largest effect involves no
change to the prompt at all: adding five columns to an export raises the false-green rate by
0.217 to 0.427, and the replies cite those columns. Two limits remain. We tested one wording
of each condition, and the definition-and-warning step changes two things at once.

**What the evidence standard implies.** Whether a proxy-column `pass` is an error depends on
the standard (Section 3.2). Under a triage standard it is a reasonable first guess. Under the
standard a monitoring product implicitly claims, that an inspector would find the record in
order, it is a claim made without the record. Our data say how often models make that move,
and which columns they rely on; they do not say which standard a given product should adopt.

---

## 9. Limitations

- **No human expert labels and no human baseline.** No attorney validated any label, and we
  do not know what false-green rate a paralegal or attorney would attain. The generated
  labels are re-derived by a separately written checker, but both programs were written by AI
  agents of one model family and share the primary-record standard. The anchor labels come
  from the author's company's engine; two AI audits and a strict view qualify them. A blind
  labelling kit is released (`docs/expert_labelling/`).
- **Narrow, synthetic generator.** Four rule families, whole-export withholding (the easiest
  insufficiency to notice), and five proxy columns chosen by us. Real exports carry other
  proxies, partially missing records and scanned documents read through OCR, none of which is
  tested. Two rules simplify the law: a late reverification is labelled a violation although a
  timely-filed extension can allow up to 240 more days of work (8 C.F.R. 274a.12(b)(20)), and
  the business-day convention follows the handbook's example rather than a definition.
- **Statistics.** Study 3 rests on 18 clusters, with the I-9 rules from 3 firms, and pooled
  estimates weight seven particular models equally; they license no claim about models in
  general. Study 3 and the single-run parts of the exploratory study were run once per cell.
  Only Study 3 was declared before its results existed.
- **One prompt.** Each condition was tested in one wording; the definition-and-warning step
  changes two things.
- **Model coverage is narrow.** No closed model from OpenAI or Anthropic was evaluated, because
  the study used no funds beyond cloud credits. Free-tier availability was decided by
  provider capacity: of 15 free chat models screened, only 6 returned a usable answer to a
  two-pair request (5 were rate-limited, 2 refused with a permissions error, 1 returned an
  upstream failure and 1 an empty completion). Several endpoints evaluated here are previews
  that will be retired.
- **The anchor results use a 140-pair declared subset, not all 221 pairs,** because of the
  free-tier call budget; the subset keeps every planted violation but widens every interval.
- **One jurisdiction and domain.** We conjecture, and do not show, that the failure generalises
  to other regulated domains.

---

## 10. Ethics, competing interests and AI use

**No real personal data.** Every record is synthetic. The anchor exports as evaluated contained
plausible personal e-mail and street addresses; the released data replace them with reserved
example domains and fictional addresses, which no rule reads.

**Not legal advice, not a training set.** The rulebook is a research artifact, and a high
score does not establish that a system may be relied upon by an employer; the plausible
misuse of this benchmark is a vendor citing a score as evidence of fitness. Fitting a model to
these labels measures nothing, since they are the generator's specification.

**Competing interests.** The author is affiliated with Settle AI Inc., which develops
commercial compliance software for US employment-based immigration. The anchor firm's labels
were written as that company's engine's acceptance gate, and the rulebook derives from its
rule registry. The engine is excluded as a baseline, the generated firms take their labels
from the generator, and the anchor labels were audited blind twice, with the results that
weaken them reported in full (Figure 8). No model provider was consulted, and no result was shared with
one before publication.

**Use of AI assistance.** An AI coding assistant (Anthropic's Claude) wrote the benchmark
code, ran the experiments and drafted the text. Separate Claude agents performed the first
label audit and wrote the reference checker without access to the generator or the labels;
Gemini 3.1 Pro performed the second audit. All are reported as AI checks, not expert review.
Every quantitative claim is recomputed from released artifacts by `scripts/verify_paper.py`;
the author is responsible for all content.

**Release.** Code under Apache-2.0, data and rulebook under CC-BY-4.0, with a datasheet.

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
python3 tests/test_benchmark.py; python3 tests/test_llm_harness.py; python3 tests/test_freetier.py
python3 scripts/sweep.py --firms 30            # Table 2 (trivial baselines)
python3 scripts/score_views.py                  # anchor study, label views, Table 12
python3 scripts/score_studies.py                # repeated-run study and Study 2
python3 scripts/score_study3.py                 # Study 3, the declared analysis
python3 scripts/study3_exploratory.py           # Section 6.3 (exploratory)
python3 scripts/labelcheck_compare.py           # generated labels vs the reference checker
python3 scripts/fill_results.py                 # regenerates every table in this paper
python3 scripts/make_figures.py                 # regenerates every chart
python3 scripts/verify_paper.py                 # recomputes every number in the text
```

No step makes an API call: every score is rebuilt from the retained replies in
`docs/**/cache/` and `docs/raw/`. Re-running the models uses `scripts/run_free.py`,
`scripts/run_vertex.py` and `scripts/run_study3.py`.

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

**Verdict menu, `abstain_removed_only`** (Table 5):

```text
Permitted verdicts:
  pass            the required evidence is present in the exports and satisfies the obligation
  fail            the required evidence is present in the exports and violates the obligation
  unmonitored     the obligation cannot be evaluated from employer export data at all

A document that was not provided is not a document that is in order.
```

**Verdict menu, `abstain_closed`** (Table 5):

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
(Section 10), which no rule reads.

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

A pilot under prompt v1.0 exposed three defects in our own harness, not in the models:
obligations sent without their definitions, a mangled "information needed" field, and a
definition of `needs_evidence` that a literal reader could apply to every pair. We fixed
them in prompt v1.1.0, archived the pilot, and report no pilot number as a result. The
main runs then exposed an output cap that cut off reasoning models mid-reply; incomplete
replies were purged and re-requested under a larger cap. Both revisions, with the numbers
that motivated them, follow.

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


### C.3 Throughput on free tiers

The OpenRouter free tier allowed 50 requests a day across all free models and 20 a
minute. At batch 12, the Study 1 subset costs 12 calls per model and condition, and each
Study 2 run (six generated firms) costs 24. The runner paces itself under the per-minute
limit, waits patiently on upstream rate limits (which were not charged against the daily
allowance), stops cleanly when the daily ceiling is reached, and resumes from a
checkpoint. Every model response is retained so that any reported number can be traced
back to output.

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

### C.6 Source scoping and the anchor subset

**Source scoping.** Free tiers cap tokens per minute, so each call carries only the exports
whose regime the batch's obligations can be evaluated against, with the HR roster always
included; every run uses batches of 12 pairs. Scoping changes the prompt, so it is part of the protocol.
The prompt names the exports not sent and tells the model not to infer that an absent field
exists in one of them, and an obligation of an unclassified regime falls back to all sources. Scoping is identical across conditions, so it cannot bias a contrast between them;
we did not run without it. One scoping defect was found and fixed before Study 3 (Appendix E).

**Model set.** Six free models were declared; two were withdrawn from the free tier
mid-study and replaced under rules committed before any replacement answered a batch
(C.2).

**The declared evaluation subset.** The free-tier budget (50 calls a day) does not cover the
full anchor firm, so Study 1 evaluates a **declared stratified subset** of 140 pairs, fixed
by a seed and frozen before any model was scored: **every planted violation** and 120 of the
201 withheld pairs, sampled in proportion to regime. We never present a subset rate as a
full-firm rate.

### C.7 Generator v1, withdrawn

 A first version emitted a
label for every pair in the 194-obligation rulebook but rendered deciding data for only four
rule families, and applied rules to entities they cannot govern. A blind check caught this
before any result on generated firms was reported: an AI agent given only the records and
rule text for 60 stratified pairs agreed with its labels on 8. Every figure from that
version, including a released-set size of 58,961 pairs, is withdrawn
(`docs/study2_v1_invalid/`). The same check on the current generator agreed on all 60.

## Appendix D: The anchor firm's labels and per-model results

### D.1 Known problems with the anchor labels

The anchor firm's labels were
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
  strict view (D.2) handles both.
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
cannot measure false alarms; the generated firms can (Section 4.2).

Its expectation set contains 221 pairs: 20 planted violations and 201 evidence requests.
The 201 arise because most obligations in this domain require evidence an employer export
does not contain. A certified LCA does not evidence that the required notice was posted; a
roster does not evidence which document a worker presented. The honest output for such a
pair is an evidence request. The ten-to-one ratio reflects which obligations the source
engine can assess from exports, not a measured property of real employers; we treat the
large abstention share as a design choice that mirrors that engine's coverage.


### D.2 Label views and the two audits

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

The strict view's ten violations include three duplicated facts (D.1), so they
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

<!-- FIGURE: fig_label_audit | 0.75\textwidth | The second audit of the anchor firm's 20 violation labels, grouped by the declared label views. The auditor supports none of the memo absences and none of the future deadlines on their labelled ground (two deadlines it judged violations for unrelated reasons), and five of the ten strict-view breaches. -->

### D.3 Per-model results of the single-run models

Six free models were evaluated on the declared 140-pair subset of the anchor firm under
prompt v1.1.0, each under both output schemas: Nemotron 3 Ultra 550B, Nemotron 3 Super
120B and Nemotron 3.5 Lightning (NVIDIA), Laguna XS 2.1 (Poolside), Qwen 3.8 27B (Alibaba),
and dots.3 Note Preview (dots-studio), the last two replacing withdrawn models (Appendix C.2). Tables are generated from the retained replies (`scripts/fill_results.py`); the
coverage and answered-only columns were added after the first results, when the coverage
effect of Section 3.3 was found.

**Uncertainty.** Bracketed figures are 95% percentile intervals from a bootstrap that
resamples *obligations* (2,000 draws, fixed seed), since pairs under one obligation share a
rule text and records. At 140 pairs most differences *between* models are not resolved, so
we do not rank models and list them alphabetically. The comparison the study is built for is
*within* a model across schemas: the paired difference on withheld pairs both runs answered,
Holm-corrected across the six models. All six remain significant at 0.05 (Table 12).

**Table 9 — Single-run models on the anchor subset, offered schema.** One row per model on the 140-pair subset, with
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

**Table 10 — Strict label view.** The same runs scored under the strict view (D.2). Alerts: the verdicts given on the five future deadlines the strict view removes.

<!-- BEGIN GENERATED: table2b-strict -->
| Model | Condition | FGR, engine | FGR, strict | Recall, engine (of 20) | Recall, strict (of 10) | Alerts: fail / pass / other |
|---|---|---|---|---|---|---|
| `dots-3-note-preview` | offered | 0.100 | 0.096 | 0.45 | 0.70 | 2 / 0 / 3 |
| `dots-3-note-preview` | dashboard | 0.525 | 0.504 | 0.80 | 0.80 | 3 / 2 / 0 |
| `nemotron-3-super-120b-a12b` | offered | 0.050 | 0.048 | 0.30 | 0.40 | 2 / 0 / 3 |
| `nemotron-3-super-120b-a12b` | dashboard | 0.175 | 0.168 | 0.95 | 0.90 | 5 / 0 / 0 |
| `nemotron-3-ultra-550b-a55b` | offered | 0.067 | 0.064 | 0.30 | 0.50 | 1 / 1 / 3 |
| `nemotron-3-ultra-550b-a55b` | dashboard | 0.217 | 0.208 | 0.80 | 0.90 | 2 / 3 / 0 |
| `nemotron-3.5-lightning` | offered | 0.042 | 0.040 | 0.05 | 0.10 | 0 / 1 / 4 |
| `nemotron-3.5-lightning` | dashboard | 0.208 | 0.200 | 0.50 | 0.40 | 3 / 0 / 2 |
| `laguna-xs-2.1` | offered | 0.125 | 0.120 | 0.20 | 0.30 | 1 / 0 / 4 |
| `laguna-xs-2.1` | dashboard | 0.433 | 0.416 | 0.90 | 0.80 | 5 / 0 / 0 |
| `qwen3.8-27b` | offered | 0.142 | 0.136 | 0.35 | 0.50 | 2 / 0 / 3 |
| `qwen3.8-27b` | dashboard | 0.417 | 0.400 | 0.85 | 0.90 | 3 / 2 / 0 |
<!-- END GENERATED: table2b-strict -->

The strict view moves false-green rates by at most 0.021 and raises recall for every model
under `abstain_offered`, because the five memo pairs most models answered `needs_evidence`
stop counting as misses. A `pass` on a deadline days away is the one alert outcome a
reviewer would never see: offered an abstention, models gave it on 2 of 30 alerts; without
it, on 7 of 30, three of them Nemotron Ultra's.

**Table 11 — Audited label view.** The two withheld pairs the first audit overturned are
removed; the scored denominator is in every row.

<!-- BEGIN GENERATED: table2c-audited -->
| Model | Condition | Unassessable pairs scored | FGR, engine | FGR, audited | FG, audited, answered only |
|---|---|---|---|---|---|
| `dots-3-note-preview` | offered | 118 of 120 | 0.100 | 0.085 | 0.085 |
| `dots-3-note-preview` | dashboard | 118 of 120 | 0.525 | 0.517 | 0.517 |
| `nemotron-3-super-120b-a12b` | offered | 118 of 120 | 0.050 | 0.034 | 0.034 |
| `nemotron-3-super-120b-a12b` | dashboard | 118 of 120 | 0.175 | 0.161 | 0.161 |
| `nemotron-3-ultra-550b-a55b` | offered | 118 of 120 | 0.067 | 0.051 | 0.051 |
| `nemotron-3-ultra-550b-a55b` | dashboard | 118 of 120 | 0.217 | 0.203 | 0.203 |
| `nemotron-3.5-lightning` | offered | 118 of 120 | 0.042 | 0.025 | 0.036 |
| `nemotron-3.5-lightning` | dashboard | 118 of 120 | 0.208 | 0.212 | 0.439 |
| `laguna-xs-2.1` | offered | 118 of 120 | 0.125 | 0.110 | 0.119 |
| `laguna-xs-2.1` | dashboard | 118 of 120 | 0.433 | 0.424 | 0.472 |
| `qwen3.8-27b` | offered | 118 of 120 | 0.142 | 0.127 | 0.127 |
| `qwen3.8-27b` | dashboard | 118 of 120 | 0.417 | 0.407 | 0.407 |
<!-- END GENERATED: table2c-audited -->

Removing the two I-9 signature pairs lowers the false-green rate by 0.008 to 0.016 in 11
of the 12 runs; in the twelfth, Lightning without the abstention, it rises by 0.004. It
changes neither the ordering of models nor the direction of any condition effect.

**Table 12 — Offered versus dashboard schema, single-run models.**

<!-- BEGIN GENERATED: table3-ablation -->
| Model | Unassessable pairs answered in both | FGR offered | FGR dashboard | Change [95% CI] | Holm-adjusted p | Off-schema replies (dashboard) |
|---|---|---|---|---|---|---|
| `dots-3-note-preview` | 120 of 120 | 0.100 | 0.525 | +0.425 [+0.26, +0.59] | 0.003 | 0 of 140 answered |
| `nemotron-3-super-120b-a12b` | 120 of 120 | 0.050 | 0.175 | +0.125 [+0.03, +0.24] | 0.012 | 0 of 140 answered |
| `nemotron-3-ultra-550b-a55b` | 120 of 120 | 0.067 | 0.217 | +0.150 [+0.07, +0.27] | 0.003 | 0 of 140 answered |
| `nemotron-3.5-lightning` | 41 of 120 | 0.042 | 0.208 | +0.463 [+0.12, +0.73] | 0.012 | 0 of 68 answered |
| `laguna-xs-2.1` | 99 of 120 | 0.125 | 0.433 | +0.333 [+0.16, +0.51] | 0.003 | 0 of 128 answered |
| `qwen3.8-27b` | 120 of 120 | 0.142 | 0.417 | +0.275 [+0.13, +0.43] | 0.003 | 0 of 140 answered |

FGR columns are over all 120 unassessable pairs. The change, its interval (obligation-cluster bootstrap, 2,000 draws) and the two-sided p-value (Holm across the six models) are computed on the unassessable pairs both runs answered; the bootstrap p-value has a floor of 1/2,000.
<!-- END GENERATED: table3-ablation -->

**Removing the abstention from a dashboard schema raises false greens in every model.** The
direction is close to built in: a schema with only `pass` and `fail` forces every
unassessable pair into one of them. What the design does not fix is the size: it rises by between 0.125
 (Nemotron Super) and 0.425 (dots.3), and the lean: five of the six models sent most
unassessable pairs to `fail`, while dots.3 sent more to `pass` (63) than to `fail` (57). No
model returned an off-schema verdict among the pairs it answered. This condition also
redefines `pass` and drops a warning paragraph, so its effect is that of moving to a
dashboard schema; Sections 6 and 7 take it apart.

**Table 13 — False-green rate by regime, offered schema.** In parentheses, the regime's
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

Cells are the false-green rate over the regime's unassessable pairs; in parentheses, the regime's scored pairs of any label.
<!-- END GENERATED: table4-regime -->

Three regimes, I-9 and E-Verify, prevailing wage, and the LCA rules, hold almost every false
green; H-1B status and FDNS site visits have none. Figure 9 shows the same data as a heatmap.

<!-- FIGURE: fig_regime_heatmap | wide | False-green rate by regime and model on the anchor subset, offered schema (the data of Table 13). False greens concentrate in the regimes whose exports carry a populated column next to the missing evidence. -->

### D.4 Further declared analyses

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

**Qualitative failure cases.** To keep excerpts from being the worst lines picked out of
thousands, the rule was fixed in code before any was read: for each model, under
`abstain_offered`, the first `pass` on a withheld pair whose reply cites an evidence field.
Applied as declared, it selected the same line for four of the six free models: a `pass` on
the Section 2 employer signature citing `section2_signed_date`, the label the audit later
overturned. Four models independently reading a populated signed-date column as a signature
suggests the label was at fault (D.2), and the prompt's own example of matching
columns by meaning names that column. Applying the rule again while skipping overturned
pairs, a step added after the first result was seen, gives the excerpts in Section 7.

## Appendix E: Study 2, six generated firms without proxy columns

Study 2 runs the same protocol on all 252 pairs of six generated firms (Section 4.2), which
carry what the anchor firm lacks: conforming controls, a third of them near-miss cases on
the legal boundary. Firms were fixed in `nofalsegreen/study2.py` before any call. Results
come from the three repeated-run models, three runs each, in the Study 2 rows of Table 14. The declared free-tier sweep was stopped after one model, superseded by Study 3
(Section 6), which runs four models from other developers on fresh firms.

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
0.071 of unassessable pairs as compliant, below their anchor-firm rates. Gemini 3.1 Pro and 3.8
Flash detect every violation and raise no false alarm on a conforming control, near-miss
controls included, in three of the four schemas. Gemma 4 detects 0.346 of violations and, with abstention offered, raises 0.074 near-miss false alarms. The
generated exports are clean, with no populated column next to a missing one, which is the
gap Study 3 fills. Excluding the reverification pairs, whose violation labels assume no
extension was filed (Section 9), changes no conclusion; no false green fell on them.

## Appendix F: Repeated-run and Study 3 tables

**Table 14 — The three repeated-run models, both studies, four schemas.** Mean of three runs, with the minimum and maximum in brackets.

<!-- BEGIN GENERATED: table7-vertex -->
| Model | Study | Schema | False green | FG, answered only | Recall | False alarm, near-miss | Unassessable pairs answered pass / fail / needs_ev. / unmon. | Min answered |
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

Schemas: *offered* (four verdicts, evidence-anchored definitions); *removed-only* (offered minus `needs_evidence`); *closed* (`pass`/`fail` only, evidence-anchored definitions kept); *dashboard* (`pass`/`fail` only, `pass` redefined as "the obligation is satisfied", warning dropped). The anchor subset has 120 unassessable pairs and no controls; Study 2 rates are pooled over its six firms (126 unassessable pairs). Min answered: the fewest pairs answered in any of the three runs. The verdict columns show every off-schema answer: none occurred on an unassessable pair in any cell.
<!-- END GENERATED: table7-vertex -->

**Table 15 — Paired schema contrasts, repeated-run models.**

<!-- BEGIN GENERATED: table8-contrasts -->
| Model | Study | Change of schema | Unassessable pairs | Change in FGR [95% CI] | Holm p |
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

Each unassessable pair's outcome is its share of `pass` over the three runs. Pairs answered in every run of both conditions; obligations resampled (2,000 draws, firm by obligation in Study 2); two-sided p-values Holm-corrected across all 24 contrasts; ** marks p < 0.05.
<!-- END GENERATED: table8-contrasts -->

**Repeats are close.** Across the 24 model, study and schema cells, the three runs'
false-green rates differ by at most 0.142, and by 0.06 or less in 21 of them. That bounds
run-to-run variation on one host at temperature 0; it says nothing about variation across
hosts, so it does not license the single runs of Section 7.

**Table 16 — Study 3, false-green rate by model, firm rendering and schema.**

<!-- BEGIN GENERATED: table9-study3 -->
| Model | Arm | FGR offered | removed-only | closed | dashboard | Recall, offered | False alarm, offered | Min answered |
|---|---|---|---|---|---|---|---|---|
| `gemini-3.1-pro-preview` | plain | 0.106 | 0.189 | 0.206 | 0.294 | 1.000 | 0.000 | 504/504 |
| `gemini-3.1-pro-preview` | proxy | 0.183 | 0.206 | 0.572 | 0.650 | 1.000 | 0.000 | 504/504 |
| `gemini-3.8-flash` | plain | 0.161 | 0.217 | 0.350 | 0.361 | 1.000 | 0.000 | 498/504 |
| `gemini-3.8-flash` | proxy | 0.361 | 0.433 | 0.639 | 0.778 | 1.000 | 0.000 | 471/504 |
| `gemma-4-26b-a4b-it-maas` | plain | 0.339 | 0.333 | 0.406 | 0.411 | 0.230 | 0.084 | 498/504 |
| `gemma-4-26b-a4b-it-maas` | proxy | 0.839 | 0.889 | 0.956 | 0.894 | 0.218 | 0.093 | 494/504 |
| `gpt-oss-120b-maas` | plain | 0.133 | 0.239 | 0.228 | 0.228 | 0.954 | 0.017 | 474/504 |
| `gpt-oss-120b-maas` | proxy | 0.289 | 0.228 | 0.272 | 0.400 | 0.920 | 0.030 | 468/504 |
| `deepseek-v3.2-maas` | plain | 0.111 | 0.211 | 0.189 | 0.267 | 0.529 | 0.131 | 504/504 |
| `deepseek-v3.2-maas` | proxy | 0.306 | 0.411 | 0.767 | 0.772 | 0.655 | 0.127 | 504/504 |
| `qwen3-235b-a22b-instruct-2507-maas` | plain | 0.317 | 0.350 | 0.367 | 0.394 | 0.345 | 0.194 | 489/504 |
| `qwen3-235b-a22b-instruct-2507-maas` | proxy | 0.628 | 0.739 | 0.894 | 0.917 | 0.368 | 0.232 | 494/504 |
| `kimi-k2-thinking-maas` | plain | 0.156 | 0.161 | 0.261 | 0.233 | 0.966 | 0.000 | 474/504 |
| `kimi-k2-thinking-maas` | proxy | 0.161 | 0.339 | 0.489 | 0.583 | 0.977 | 0.034 | 456/504 |

Twelve fresh firms (504 pairs, 180 unassessable) per arm, one run per cell. *plain*: generator v2; *proxy*: the same firms with the five proxy columns (generator v3). False alarm is any non-`pass` verdict on one of the 237 conforming controls.
<!-- END GENERATED: table9-study3 -->

**Table 17 — Study 3, the declared tests.**

<!-- BEGIN GENERATED: table10-study3-tests -->
| Estimate | P1 abstention | P2 definition and warning | P3 proxy columns, dashboard | P4 proxy columns, offered |
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

Difference in false-green rate on unassessable pairs answered in both cells, [95% CI] from an obligation-cluster bootstrap (18 firm-by-rule clusters, 2,000 draws), Holm-adjusted p. Holm families as declared: the four pooled tests; the 28 per-model tests; the eight group tests. ** marks adjusted p < 0.05. Pooled estimates weight each model equally.
<!-- END GENERATED: table10-study3-tests -->

## Appendix G: Interpretive choices of the reference checker

The checker of Section 4.3 records every choice the regulations leave open, with its source,
in `labelcheck/INTERPRETATIONS.md`. The choices that matter most are these. Section 1 signed on
the first day of employment is timely (8 C.F.R. 274a.2(b)(1)(i)(A); M-274 §3.0). Section 2 is
due by the third business day after the first day, with weekends and federal holidays (with
their observed dates) excluded; the M-274 does not define "business day". Reverification on
the expiry date itself is timely. The required wage is the greater of the prevailing wage
and the actual wage, compared per pay period rather than as a year-to-date average (20 C.F.R.
655.731(a), (c)(4)). None of the five proxy columns is treated as evidence. Section 4.3 gives
the number of verdicts each boundary choice would change.

