# Review, round 3: "No False Green: A Benchmark for Evidence-Aware Compliance Verdicts over Structured Employer Records"

Reviewer role: area chair / senior PC (ACL/EMNLP main, NeurIPS D&B, JURIX/ICAIL).
Material checked: `docs/PAPER.md` (1,745 lines), `docs/STUDY3_PREREGISTRATION.md`,
`docs/study3/results.json`, `docs/label_audit_second.json`, `docs/labelcheck_results.json`,
`labelcheck/INTERPRETATIONS.md`, `scripts/score_studies.py`, `scripts/fill_results.py`, and
the cached Study 3 replies in `docs/study3/cache/`.

---

## 1. Summary

The paper defines a *false green*: a compliance system reports an obligation as satisfied
when the evidence needed to assess it is absent. It releases a benchmark of US
employment-immigration compliance verdicts over synthetic employer exports, made of one
hand-authored anchor firm (221 pairs) and a generator whose labels are fixed by
construction for four I-9/LCA rule families. It evaluates 13 LLMs across five
overlapping studies. The central result is a preregistered study (Study 3, 7 models, 12
fresh firms). In that study, removing the abstention verdict, redefining `pass`, and
adding roster columns that resemble the missing evidence each raise the false-green rate.
The column effect is the largest (+0.43 pooled under a pass/fail schema, +0.22 under the
recommended four-verdict schema).

---

## 2. Scores

| Dimension | Score (1-10) | One-line reason |
|---|---|---|
| Soundness | 6 | Study 3 is clean and preregistered. The headline effects, however, are on the decoy arm only, rest on 18 clusters (I-9 from 3 firms), and the "false green" label on proxy columns is a normative choice the paper never defends. |
| Novelty | 5 | The paper concedes that DEMM-Bench and Partial Evidence Bench already do directional, construction-labelled overclaiming. What is new is the domain, the schema decomposition and the adjacent-column manipulation. |
| Clarity | 4 | It reads like a lab notebook. There are five studies, three label views, two run regimes, and the term "withheld" has two meanings. The strongest result appears in §8.5, roughly 60% of the way through. |
| Significance | 6 | The design rules (keep an abstain verdict, define `pass` in terms of evidence, quarantine proxy columns) are useful to practitioners. Generalisation is limited by four rule families, synthetic data and no human/legal validation. |
| Reproducibility | 8 | Frozen prompts, all raw replies, seeds, generated tables and a verify script are released. Points are lost because preview and free-tier model endpoints will disappear. |

**Overall recommendation:**
- *ACL/EMNLP main:* **weak reject (borderline)** in the current form.
- *NeurIPS D&B or ICAIL/JURIX:* **weak accept** if restructured as outlined in §7 of this review.
- **Confidence:** 4/5. I checked numbers against the JSON. I am not an immigration practitioner.

The science is more careful than most submissions in this space. The disclosure discipline
is exemplary. The paper is let down by structure, by framing that runs ahead of the
preregistered design, and by one construct-validity question it has not confronted.

---

## 3. Major issues (ranked)

### M1. The "false green" label on adjacent columns is a normative evidentiary standard the paper asserts but never defends. "Mechanism, not interpretation" overclaims.

**Location.**
- Abstract: "adjacent columns: populated fields that sit beside the missing evidence without being it, such as an I-9 status of 'Complete'".
- §1, contribution 4: "adjacent-field substitution … is a mechanism of false greens rather than an interpretation".
- §5.3: "None is an item the rulebook lists as evidence for the rule it imitates".
- §8.5: "it is the case a practitioner might call a reasonable inference; we keep the label".

**Why it matters.** An AI-and-law reviewer will ask whether a model that sees
`i9Status = Complete`, `workAuthValidThrough = 2027-…` and `annualBaseSalary = <LCA wage>` and
answers `pass` is wrong, or is applying a different but defensible standard of proof. The
decoys are, by construction, the employer's own attestations. In a real HRIS they are
exactly what a compliance analyst would use to triage. The paper's answer is that the
rulebook's "information needed" field does not list them. That defines away the question
instead of answering it.

Study 3 then confirms that adding such columns raises `pass`. That is close to tautological:
the columns were designed so that a reader would take them as evidence. What Study 3
establishes is that models accept proxy or attestation evidence. Whether that is an
*error* depends on the standard. §8.5 already concedes the point for the wage rule, and the
same argument applies to `workAuthValidThrough` for reverification.

**There is a further gap between claim and evidence.** The abstract's showcase example,
`i9Status` = "Complete", is **never cited as evidence in any cached Study 3 reply**. A grep of
`docs/study3/cache/` finds 0 occurrences. Models cite `onboardingCompletedDate` (585 `pass`
lines), `workAuthValidThrough` (263) and `annualBaseSalary` (1,069). Those counts cover all
pairs, not only withheld ones, but the abstract's example is not the column doing the work.

**Fix (no new data).**
1. Add a short subsection, "What counts as evidence", to §4. State the standard: primary
   record versus attestation versus proxy. Ground it in the record-keeping duties, namely
   M-274 retention and the inspection-of-original-forms requirement under 8 C.F.R.
   274a.2(b)(2), and 20 C.F.R. 655.731(b) payroll-record requirements. Say plainly that
   the benchmark scores the primary-record standard, and why a monitoring product must.
2. Rename the concept from "adjacent-field substitution" to something like *proxy-evidence
   acceptance*, and drop "rather than an interpretation". What was tested is that proxies
   raise `pass`. It was not tested that models misread the proxy as the record.
3. **Mine the replies you already have.** Every reply line carries an evidence field. Add a
   table to §9 or the appendix: for decoy-arm false greens, the share whose cited field is
   one of the five decoy columns, broken down by column and model. This is the direct
   evidence of "substitution", it costs nothing, and it will show which decoys matter.
4. Replace the abstract's `i9Status` example with the column models actually cite.

### M2. The abstract and conclusion generalise effects that were tested only on the decoy arm. The claim that the definition of `pass` matters on both kinds of firm is unsupported.

**Location.**
- Abstract: "Removing every non-committal verdict raises the false-green rate by 0.259; redefining `pass` … raises it by a further 0.084".
- §8.5: "Adjacent columns raise false greens under every schema, and the definition of `pass` matters on both kinds of firm."

**Why it matters.** P1 and P2 were declared on the decoy arm only (preregistration table).
Approximate plain-arm effects from Table 9 cells (unpaired means over 7 models, computed
from `results.json`) are much smaller:

| Effect | Plain arm | Decoy arm |
|---|---|---|
| Abstention effect (P1) | ≈ +0.10 | ≈ +0.26 |
| Definition effect (P2) | ≈ +0.03 | ≈ +0.06 unpaired, +0.084 paired |

S3, the interaction test, returned p = 0.10. That result fails to reject "no interaction".
It does **not** establish a definition effect on plain firms; that is a classic
absence-of-evidence inference. A reviewer who computes the plain-arm numbers will read the
abstract as inflated.

**Fix (no new data).**
- In the abstract, say "on firms whose exports carry adjacent columns" for P1 and P2.
- In §8.5, report the plain-arm P1 and P2 contrasts as exploratory, using the existing
  cells and the same bootstrap code.
- Replace "matters on both kinds of firm" with: "we could not detect a difference in the
  definition effect between arms (S3, p = 0.10); on plain firms the effect is ≈0.03 and
  untested."

### M3. P2 is not a pure "definition effect", and P1 is not a pure "abstention effect".

**Location.**
- Abstract: "redefining `pass` from … to 'the obligation is satisfied' raises it by a further 0.084".
- Appendix B: compare the verdict menus.

**Why it matters.** Going from `abstain_closed` to `abstain_withheld` changes three things:
1. the definition of `pass`;
2. the definition of `fail`;
3. the deletion of the sentence "A document that was not provided is not a document that is in order."

§7 itself says the dashboard schema "drops the warning". Going from `abstain_offered` to
`abstain_closed` likewise deletes the paragraph "The distinction between `pass` and
`needs_evidence` is the one that matters most…". So P2 is a definition-plus-warning effect,
and P1 is an abstention-plus-instruction effect. The preregistration uses the same labels,
so this is not a protocol deviation. It is a naming overclaim that an ACL reviewer will
spot from Appendix B.

**Fix.**
- Rename P2 "definition-and-warning effect" everywhere.
- Add one line under Table 10 listing exactly which sentences differ between each pair of
  conditions.
- Add a diff-style figure of the four menus (see §6 of this review, Figure A2).

### M4. Inference rests on very few independent units, and the statistical reporting is inconsistent.

**Locations and problems.**
- **Few clusters, unevenly drawn.** Study 3's withheld pairs form 18 clusters (prereg):
  81 wage pairs from 9 firms and 99 I-9 pairs from **only 3 firms**. All four primary
  p-values sit at the bootstrap floor. A cluster bootstrap with 18 unbalanced clusters is
  fragile, and the bootstrap-tail "p-value" is a CI-inversion heuristic, not a test under
  the null.
- **I-9 claim rests on 3 firms.** The abstract's I-9 claim ("0.000 to 0.023 across schemas
  until an adjacent column is present") is an *exploratory* breakdown (§8.5 says so). It
  rests on 3 firms, yet it sits in the abstract.
- **Sidedness differs between tables.** Table 3's caption says "one-sided p-value";
  Table 8 and Study 3 are two-sided (`scripts/fill_results.py:148` vs `:331`).
- **"Eight of nine" mixes families and ignores four models.** The abstract's "significantly
  for eight of the nine models we tested for it after correction" combines two Holm
  families: 6 free models with one run each (Table 3), and 24 contrasts over Vertex models
  with three runs each (Table 8). Also, 13 models were run under the dashboard schema on
  the anchor subset. The four E1 models have no test (Table 11, "descriptive"), so "the
  nine models we tested for it" is wrong as phrased.
- **Inference is conditional on these seven models.** "Pooled over seven models … weight
  each model equally" is a fixed-effects estimate. It licenses no claim about "models" in
  general. Phrases like "for Google's models and for the others alike" invite that reading.

**Fix (no new data).**
- State the cluster composition (9 wage, 9 I-9 from 3 firms) in §8.5 and the Table 10 caption.
- Add a cluster-level sign count: in how many of the 18 clusters is the decoy-minus-plain
  difference positive? It is computable now and far more persuasive than p = 0.002 at a floor.
- Make all p-values two-sided, or say explicitly why Table 3 differs.
- Rewrite the abstract claim as "for all six free models (Holm across six) and two of three
  Google models (Holm across 24 contrasts); the four further models were run descriptively."
- Move the I-9 0.000→0.193 claim out of the abstract, or label it "exploratory, 3 firms".

### M5. The anchor firm's labels are weak, and the paper underreports how weak.

**Location.**
- §6.1: "On the withheld pairs the two auditors keep the label on 113 of 120."
- §6.1: "roughly half … is a breach evident from the exports".

**Why it matters.**
- **Agreement is overstated.** `docs/label_audit_second.json` reports **Cohen's κ = −0.024**
  between the two auditors on withheld pairs. Raw agreement of 113/120 looks high only
  because overturns are rare. On the question that matters, which labels are wrong, the
  two auditors agree on **zero** pairs. The paper does mention "no pair in common", but
  leads with 113/120.
- **Most violation labels are not supported.** The second auditor marks 13 of 20
  violation labels as unsupported (7 `violation_shown`, 12 `cannot_tell`, 1
  `compliance_shown`).
- **Further weaknesses.** The labels were authored by the author's company's engine.
  Gemini 3.1 Pro is both an auditor and a model under test.
- **Consequence.** Anchor violation recall (Tables 2, 2b, 11; abstract "detecting 0.050 to
  0.500 of its violations") is not interpretable as detection ability.

**Fix (no new data).**
- Report κ beside 113/120.
- Remove anchor recall from the abstract.
- Present the anchor firm as a *realism probe for false greens*. The FGR does not depend on
  violation labels, as §6.1 correctly notes. Recall belongs to the generated firms.
- Move Tables 2b and 2c to an appendix, with one summary sentence in the body: "label view
  changes FGR by ≤0.021 and never changes a condition effect."

### M6. The independence of the label checker is overstated, and its agreement count double-counts.

**Location.**
- §5.3: "After the fix the two derivations agree on all 1,680 labels".
- Abstract: "an independent checker written from the regulations".

**Why it matters.**
- **Double counting.** The 1,680 includes Study 3 *plain* (504) and *decoy* (504), whose
  labels are identical by design (§5.3: "identical in every label"). Distinct labels
  checked: 420 + 252 + 504 = **1,176**.
- **Correlated authors.** §12 says the generator code and the checker were both written by
  Claude agents. "Independent" here means "separate context, same model family". Errors
  are plausibly correlated: both read the same CFR text with the same priors. The checker
  also shares the generator's normative choices (whole-export withholding ⇒
  `needs_evidence`; LCA wage column is not evidence).
- **Missing denominator.** INTERPRETATIONS.md states that 70 Section 2 dates fall exactly
  on the deadline and 6 verdicts flip under the holiday convention. This is exactly the
  boundary mass where a shared misreading would matter. The paper does not report it.

**Fix.**
- Report "1,176 distinct labels (1,680 including the duplicated decoy arm)".
- Say "implemented separately by a second AI agent of the same model family".
- Report the boundary sensitivity in §11: 6 holiday flips and 55 calendar-day flips out of N.

### M7. Too many studies, regimes and post-hoc layers. The strongest result is buried.

**Location.**
- §7 to §8 present Study 1 (6 free models, 1 run), the "Vertex block" (3 models, 3 runs,
  4 schemas), Study 2 (6 firms, abandoned sweep, a scoping defect), Study 3 (preregistered)
  and E1 (descriptive), plus three label views and the pilot history.
- The preregistered result begins at line 985 of 1,745.

**Why it matters.**
- Reviewers will not reconstruct which claim rests on which study. The paper itself has to
  say "Everything in Sections 8.2 to 8.4 that decomposes the schema was formed or extended
  after results were seen."
- Study 2 contributes almost nothing in the current draft. It is superseded and its sweep
  was stopped. It has an excluded subset, and its one substantive reading was retracted
  in §8.3.

**Fix (pure restructuring; see §7 of this review).**
- Lead the results with Study 3.
- Present Study 1 together with the Vertex block as *one* exploratory anchor study that
  motivated the preregistration.
- Move Study 2, the pilot, model substitutions, delivery failures and the label-view
  tables to appendices.

### M8. The novelty claims in the introduction contradict the related-work section.

**Location.**
- §1: "**It is barely measured.** … None of it evaluates a system reading a third-party employer's structured records".
- §2: "We do not claim the directional, construction-labelled framing as new."

**Why it matters.** The introduction promises a new measurement problem. §2 concedes the
framing and limits novelty to the domain, the subject and the citation-grounding. That is
honest, but a reviewer reads §1 first and §2 as a retreat.

**Fix.** Rewrite claim 3 of §1 as the positioning sentence of §2:

> "Two recent benchmarks measure overclaiming under insufficient evidence for agents
> (Solozobov 2026; Tallam 2026); none does so for regulatory verdicts over a third party's
> structured records, where abstention is the correct answer for half the items."

Move the specific contrast up front.

### M9. The benchmark-versus-study identity is unclear. As a benchmark it is narrow.

**Location.**
- Title: "A Benchmark".
- §5.4: "1,481 pairs" across 31 firms.
- §5.3: "four rule families".
- §1, contribution 2: "arbitrarily many (if deliberately narrow) firms".

**Why it matters.** A D&B reviewer will measure the artifact. It has:
- one 12-worker anchor firm whose labels are contested (M5);
- a generator covering 4 of 194 rulebook obligations;
- withholding only at the granularity of a whole export, so "needs_evidence" is always
  "an entire file is missing", which is the easiest form of insufficiency to detect;
- a 194-obligation rulebook that is mostly unexercised by the generator.

The contribution that actually carries weight is the *controlled-manipulation methodology*:
the paired plain/decoy rendering and the schema ladder.

**Fix.** Reframe the title and contribution list around the methodology, for example "No
False Green: Measuring how output schemas and proxy columns produce unsupported compliance
verdicts". Present the dataset as the released instrument. State coverage plainly in §5
as one table: rules in the rulebook, rules exercised by the anchor firm, rules exercised by
the generator.

### M10. Asymmetric scoring choices are buried and can move headline numbers.

**Location.**
- §3: "a model's `unmonitored` answer on a withheld pair is scored as wrong but is not a false green".
- §6: needs_evidence on a control counts as a false alarm.

**Why it matters.** In the removed-only condition Gemini 3.1 Pro sends 109 of 120 withheld
pairs to `unmonitored` (Table 7). Under FGR alone that looks safe; under abstention F1 it
scores 0. The S2 result ("removing only `needs_evidence` raises FGR by 0.080") is therefore
partly a measure of each model's willingness to relabel abstentions as `unmonitored`. The
task defines four states but uses only three as targets.

**Fix.** Add a "verdict-flow" figure (§6 of this review, Figure 3) that shows where withheld
pairs go under each schema. State in §6 that `unmonitored` functions as a second abstention
in practice. Consider whether the four-state framing should be presented as three states
plus one reserved state.

### Issues that genuinely need new data (flagged separately)

- **N1. No human or legal labels and no human baseline.** Nothing short of practising
  counsel labelling the anchor firm and a sample of decoy-arm pairs settles M1, M5 or M6.
  The kit exists (`docs/expert_labelling/`). Even 2 attorneys × 100 pairs would change the
  paper's standing at ICAIL/JURIX.
- **N2. Per-column decoy ablation.** All five decoys appear together, so their effects
  cannot be separated except by rule family. The M1 evidence-field analysis is the
  zero-cost partial substitute.
- **N3. Prompt-paraphrase robustness.** There is one frozen prompt and no paraphrases. The
  §9 "Is this only prompt sensitivity?" argument is rhetorical without at least two
  paraphrases per schema.
- **N4. Closed frontier models.** No GPT-5-class or Claude-class model was evaluated. §11
  discloses this, but it limits significance for a venue audience.
- **N5. Within-export withholding.** Only whole-export withholding is tested. Missing
  cells, partial rows and stale records are the realistic and harder cases.

---

## 4. Writing and presentation issues

### 4.1 Structure and section order

- **Results appear in chronological order, not in order of evidential strength.** The
  sequence is §8.1 trivial baselines, then §8.2 Study 1 (6 single-run free models), §8.3
  Study 2, §8.4 the Vertex block, and §8.5 Study 3. Reverse the order of evidence:
  preregistered first, exploratory second.
- **§6.1 is misplaced.** The section on label views of the anchor firm is filed under
  "Metrics". It is label validation and belongs with §5.2 or in a "Label quality" section.
- **§3 comes too early.** "Background: the four states" arrives before the task is
  defined, and opens with the source engine and UPL rules. Fold it into §4 as a
  definitions table.
- **§7 mixes three things:** baselines, protocol, and a long list of operational rules
  (delivery failures, parsing, costs). Split it into "Models and protocol" (body, half a
  page) and "Run operations" (appendix).
- **Appendix C is out of order:** C.1, C.2, C.4, C.3, C.5.
- **Table numbering skips 5 and 6** (Tables 1, 2, 2b, 2c, 3, 4, 7, 8, 9, 10, 11).
  Figure 1 is the only figure.
- **The Terms glossary (§1 end) comes after first use** of LCA (line 77) and FDNS
  (line 81). Move it before §1's cost paragraph, or into a footnote at first use.

### 4.2 Redundancy (the same fact stated in several places)

| Fact | Where it appears |
|---|---|
| Anchor labels were the engine's acceptance gate, where `fail` = "requires action" | §5.2, §6.1, §7.2, §12 |
| Scoping defect (actual-wage export not sent) | §7.2, §8.3, §11, prereg |
| Unanswered pairs cannot be false greens; tables report coverage | §4 scoring rule, §7 parsing, §8.2 Lightning paragraph |
| No attorney/expert validated labels | Abstract, §5.3, §10, §11 (twice), §12 (twice) |
| Post-hoc status of the schema decomposition | §8.4 (twice), §8.5 opener, §9, §11 |
| Offered-schema FGR range 0.042–0.142/0.153 | Abstract, §8.2, §8.4, §8.5 E1, §9 |
| Three design rules | §9 and §10, nearly verbatim |
| Definition of adjacent columns | Abstract, §1, §5.3, §8.5, prereg |
| Engine excluded as a baseline | §7.2 and §12 |

Keep each fact once in the body, with back-references elsewhere.

### 4.3 Where the narrative buries the lede

- **The abstract** spends its second paragraph on Study 1 single-run free models and
  reaches the preregistered result only in paragraph 3.
- **§1** never states a quantitative finding. Put the Study 3 numbers in the introduction.
- **§8.5's best sentence** ("Detection does not predict safety: … detect at least 0.920 of
  violations … yet on decoy firms they call 0.161 to 0.361 of withheld pairs compliant")
  is the paper's most quotable, practitioner-relevant finding. It sits in the middle of a
  paragraph. Promote it to the abstract and a figure.
- **The "five columns raise FGR without any prompt change" point** appears only in §9 ("Is
  this only prompt sensitivity?"). It is the paper's best answer to the obvious objection
  and belongs in §1.

### 4.4 Jargon used before it is defined

- **"Vertex block":** used in §7 (line 591) and defined in §8.4. It is a cloud-provider
  name used as a study name. Rename it, e.g. "Repeated-run anchor study".
- **"Strict view":** used in §5.2 ("The strict view (Section 6) handles both") and defined
  in §6.1.
- **"Label basis":** used for the oracle in §7 and never defined.
- **"Scoping" / "scoped sources":** used in §5.3 and the prereg, defined in §7.2.
- **"Regime":** never defined. Is it a rulebook grouping? A regulatory programme?
- **"Near-miss controls":** first used in §5.3 and fine there, but §6 refers to them
  before the reader has the count.
- **"M-274", "ASVVP" (in the Appendix B prompt), "PW", "OES":** never expanded.
- **"Alerts" / "deadline alerts":** Table 2b has an "Alerts: fail / pass / other" column
  that is never explained in the caption.
- **"E1", "S2", "S3", "S5":** preregistration identifiers used in the body without a key.
- **"Generator v2 / v3":** v1 is "an earlier generator". Name the versions once in a table.
- **"Off-schema", "unparseable", "answered", "coverage":** four related terms. Define them
  together once.

### 4.5 Inconsistent terminology (each instance)

| Concept | Variants used | Recommendation |
|---|---|---|
| The 2-verdict schema | `abstain_withheld`, "withheld" (Tables 2b/2c "Condition: withheld"), "dashboard", "dashboard schema", "dashboard-style schema", "the dashboard condition", "pass/fail schema" | Use **"dashboard"** everywhere in prose; code names in Appendix B only |
| The 4-verdict schema | `abstain_offered`, "offered", "recommended schema", "evidence-anchored", "with abstention offered" | **"offered"** (or "recommended"), not both |
| **"Withheld"** | (a) the dashboard *condition*; (b) the `withheld_evidence` *label* or disposition; (c) "withheld pairs"; (d) exports "withheld" in the generator | **Critical collision.** Table 2b shows "Condition: withheld" in a table about withheld pairs. Rename the condition. |
| Undecidable pairs | `needs_evidence`, "withheld pairs", "withheld-evidence pairs", "unassessable", "undecidable", "evidence requests", "unassessed obligations", "open gap" | Pick one noun ("undecidable pairs") and one label (`needs_evidence`) |
| Anchor firm | "anchor firm", "Study 1", "the anchor subset", "declared stratified subset", "140-pair subset", "Northwind Robotics" (Appendix B only), "the hand-authored anchor" | "anchor firm" for the data, "Study 1" for the experiment; name Northwind once in §5.2 |
| Adjacent columns | "adjacent columns", "decoy" (arm name), "decoy columns" (prereg S5), "adjacent-but-insufficient roster columns" (Table 9 caption), "misleading columns" (§10), "populated column beside the missing evidence", "adjacent-field substitution" (the behaviour) | Use "adjacent columns" for the manipulation and "adjacent arm" in place of "decoy arm". "Decoy" implies intent to deceive, which concedes M1. |
| The engine | "source engine", "rule engine", "compliance engine", "the author's company's engine", "commercial compliance engine" | "the source engine" throughout |
| False green abbreviation | "FGR", "FG", "False green", "false-green rate" | "FGR" after first definition |
| Controls | "conforming controls", "control pairs", "planted_control", "conforming cases", "near-miss controls" | "controls" and "near-miss controls" |
| Violations | "planted violations", "violation labels", "violations", "breaches" | "violations" |
| Model groups | "free models", "free-tier open-weights model", "free API models", "open-weights models served on Vertex" | Free tier ≠ open weights (is dots.3 Note Preview open-weights?). Use "free-tier models" for provenance only. |
| Study 2 | "Study 2", "generated firms", "the Study 2 firms" | Fine, but Study 2 should move to the appendix |

### 4.6 Over-long sentences (examples to split)

- **§1, line 63–69:** "When the precondition fails, … which is the labour the product
  exists to remove." (about 70 words, with three clauses after a colon).
- **§5.3, line 446–453** (adjacent columns): "They appear in every such firm, whether or
  not … and come from a separate random stream, so the firm with them and the same seed
  without them are identical in every label and every other export."
- **§6.1, line 531–543:** the third-view paragraph is about 140 words, with four
  semicolon-joined clauses in one sentence ("The protocol … was committed before the audit
  ran; it covers all 120 withheld pairs; the auditor … ; and a label is overturned only if
  …").
- **§8.5, line 1052–1063:** a single paragraph that mixes P3 significance counts, the I-9
  breakdown, and the wage-rule caveat. Split it into three.
- **§9, line 1162–1170:** "The definition of `pass` is not incidental wording: every
  compliance dashboard must decide …, and that decision is the variable manipulated, with
  the prompt otherwise held word for word." This is also inaccurate; see M3.
- **Appendix C.2:** the entire paragraph, which is one 330-word block narrating fallback
  rules. Convert it to a numbered timeline.

### 4.7 Tables that should be figures

- **Table 9** (56 cells): a slope or dot plot. This is the paper's key figure (Figure 2 below).
- **Table 10:** a forest plot of P1–P4, pooled, by group and per model (Figure 3).
- **Tables 3 and 8:** one forest plot of within-model schema contrasts (appendix).
- **Table 4:** a heatmap of regime × model (appendix).
- **Table 7:** small multiples or a stacked verdict-flow bar chart (Figure 4).
- **Table 1** can stay a table. It is small and the dashes carry information.

### 4.8 Captions that are not self-contained

- **Table 2b:** "strict label view (Section 6.1), with the deadline alerts". Neither
  "strict" nor "alerts" is explained. Add a sentence for each.
- **Table 2c:** "audited label view". Say which two pairs are removed, and why.
- **Table 3:** "Same models, both conditions." Name the conditions. Say whether p is one-
  or two-sided and what the family is.
- **Table 4:** "In parentheses, the regime's scored pairs of any label". The cell metric is
  defined only in a footnote that duplicates the header text.
- **Table 7:** a solid caption, but the "Min answered" column is undefined: minimum over
  what?
- **Table 9:** "*plain*: generator v2; *decoy*: …". Give the five columns, and say that
  "FGR offered" means the four-verdict schema.
- **Table 11:** "(extension E1)". Say "four further models, run once, no significance test".
- **Figure 1:** no axis labels in the caption, no model identification, and the caption
  does not say that `always_fail` overlaps the oracle. Say what the reader should take
  away.

---

## 5. Overclaims and unsupported statements

Numbers were checked against `docs/study3/results.json`, `docs/label_audit_second.json`,
`docs/labelcheck_results.json` and the paper's own tables.

| # | Claim (location) | Check | Verdict |
|---|---|---|---|
| 1 | "all four declared hypotheses were confirmed (Holm-adjusted p = 0.002 each)" (Abstract) | `primary` P1–P4: Δ = 0.2594, 0.0841, 0.4268, 0.2170; p_holm = 0.002 each | **Correct**. Add that this is the floor of a 2,000-draw bootstrap on 18 clusters (M4). |
| 2 | "Removing every non-committal verdict raises the false-green rate by 0.259" (Abstract) | Decoy arm only; plain arm ≈ +0.10 (unpaired, from cells) | **Overgeneralised** (M2). |
| 3 | "redefining `pass` … raises it by a further 0.084" (Abstract) | Also drops the warning sentence; decoy arm only; plain ≈ +0.03 | **Mislabelled and overgeneralised** (M2, M3). |
| 4 | "significantly for eight of the nine models we tested for it after correction" (Abstract, §9, §10) | 6/6 free (Table 3, Holm/6) plus Flash and Gemma (Table 8, Holm/24); Gemini 3.1 Pro p = 1.000. E1's four models were run under the dashboard schema but not tested. | **Arithmetically correct, misleadingly phrased** (M4). |
| 5 | "On 140 pairs … 0.042 to 0.153 … detecting 0.050 to 0.500" (Abstract) | Free 0.042–0.142, Vertex up to 0.153; recall 0.05 (Lightning) to 0.500 (Flash) | **Correct**, but anchor recall is not interpretable (M5). |
| 6 | "0.131 to 0.589" dashboard range (Abstract) | Gemini Pro 0.131 to Gemma 0.589; covers the 9 models, E1 inside the range | **Correct.** |
| 7 | "On I-9 obligations, models almost never call a missing record compliant (0.000 to 0.023 across schemas)" (Abstract) | `exploratory_by_rule_family` i9 plain: 0.000, 0.000, 0.0029, 0.0231 | **Number correct**, but exploratory and from 3 firms; does not belong in the abstract unqualified. |
| 8 | "rises to 0.193 under the recommended schema and 0.686 under the dashboard" (§8.5) | 0.1934, 0.6856 | **Correct.** |
| 9 | "such as an I-9 status of 'Complete'" (Abstract, §5.3) | `i9Status` is cited as evidence in **0** cached replies | **Misleading exemplar** (M1). |
| 10 | "the two derivations agree on all 1,680 labels" (§5.3) | 1,680 includes 504 plain plus 504 decoy with identical labels; 1,176 distinct | **Inflated count** (M6). |
| 11 | "an independent checker written from the regulations" (Abstract, §10, §12) | Written by a separate Claude agent; the generator code was also written by Claude | **Overstated independence** (M6). |
| 12 | "On the withheld pairs the two auditors keep the label on 113 of 120" (§6.1) | κ = −0.024; zero overlap on overturns | **Selective statistic** (M5). |
| 13 | "adjacent-field substitution … is a mechanism of false greens rather than an interpretation" (§1, contribution 4) | Study 3 shows that the columns raise `pass`; it does not show that models read the column *as* the evidence. The evidence-field analysis is not reported. | **Overclaim** (M1). |
| 14 | "the definition of `pass` matters on both kinds of firm" (§8.5) | Inferred from a null interaction test (S3 p = 0.10) | **Unsupported** (M2). |
| 15 | "P3 is significant for every one of the seven models, and P4 for five" (§8.5) | S1: P3 all 7 < 0.05; P4 is not significant for Gemini Pro (0.432) or Kimi (1.000) | **Correct.** |
| 16 | "P1 is significant for five of the seven and P2 for one (gpt-oss-120b)" | P1 is not significant for Gemma (0.432) or gpt-oss (1.000); P2 only gpt-oss (0.014), Kimi 0.070 | **Correct.** |
| 17 | "adjacent columns change the false-alarm rate … by at most 0.038 (Table 9), and by at most 0.080 under any schema (S5)" | Recomputed max = 0.0802 (Qwen3, dashboard) | **Correct.** |
| 18 | "Each effect is also significant within the Google models and within the other four developers' models" | S4: all eight p_holm ≤ 0.021 | **Correct.** |
| 19 | "three runs' false-green rates differ by at most 0.142, and by 0.06 or less in 21" (§8.4) | Gemma S1 closed spread 0.142; Flash S1 closed 0.075 and dashboard 0.083 are the other two > 0.06 | **Correct.** |
| 20 | "The task is solvable. … A system scoring poorly is exhibiting a property of itself, not of an ill-posed benchmark." (§8.1) | The oracle reads the label basis. That proves internal consistency, not that the task is solvable from the exports by a reader without the basis. | **Overclaim.** Say "the labels are internally consistent and decidable from the label basis." |
| 21 | "a seeded generator producing arbitrarily many … firms" (§1) | True, but they differ only in seed over four rule families | Fine with "deliberately narrow", which is present. Avoid "arbitrarily many" in the title or abstract. |
| 22 | "We claim the false-green failure generalises to other regulated domains" (§11) | No evidence is offered | **Unsupported.** Change "claim" to "conjecture". |
| 23 | "Abstention is the *correct, actionable output* for 48.8% of released pairs" (§2) | 723/1,481 = 48.8% | **Correct**, but this is a design choice (§5.2 says so). Do not present it as a domain property in §2. |
| 24 | "Detection does not predict safety" (§8.5) | Four models with recall ≥ 0.92 have decoy FGR 0.161–0.361 | **Supported** for these models; avoid wording that implies a general law. |
| 25 | Preregistration date 2026-10-03, with all of Study 3 run and reported | Plausible (§C.5 says it ran in a day) | Fine. Cite the commit hash in the paper, not just "the commit history". |

---

## 6. Figures a strong version must have

### Main body (4 figures, about 1.25 pages)

**Figure 1: Task and the two failure directions (schematic).**
- *Content:* one obligation (I-9 Section 2 timeliness) and one worker, shown three ways:
  (a) I-9 export present ⇒ `pass`/`fail`; (b) I-9 export withheld ⇒ `needs_evidence`;
  (c) I-9 export withheld but the roster shows `onboardingCompletedDate` ⇒ the model says
  `pass` (a false green).
- *Arrows:* `fail` → "triggers review"; `pass` → "suppresses review".
- *Point:* the asymmetry and the adjacent-column trap, in one glance. It replaces about a
  page of §1 and §3 prose.

**Figure 2: The adjacent-column effect, by model and schema (Study 3, the key figure).**
- *Data:* Table 9's FGR (`results.json` → `cells`), 7 models × 4 schemas × 2 arms.
- *Chart:* small multiples, one panel per schema ordered offered → removed-only → closed →
  dashboard. In each panel, a dumbbell (slope) per model from plain to adjacent FGR, with
  the pooled mean as a thick bar.
- *Point:* every model moves right under every schema. The gap widens as the schema
  loosens, and no schema closes it.

**Figure 3: Preregistered contrasts (forest plot).**
- *Data:* `primary`, `S4_by_developer_group` and `S1_per_model` for P1–P4, plus S2 and S3.
- *Chart:* rows for pooled, Google, other developers and the 7 models. Columns P1–P4. Point
  estimate with 95% CI, a vertical zero line, and filled markers where Holm p < 0.05.
- *Point:* pooled effects are robust; per-model heterogeneity is large (P2 is significant
  for 1/7). This replaces Table 10.

**Figure 4: Where undecidable pairs go (verdict flow).**
- *Data:* per-condition counts of withheld pairs routed to pass, fail, needs_evidence,
  unmonitored and unanswered. Use Table 7's columns for the anchor firm, and the
  `cells.counts` `withheld_as_*` fields for Study 3.
- *Chart:* stacked 100% horizontal bars per model × schema, faceted by arm. Green = pass;
  the other colours are muted.
- *Point:* removing `needs_evidence` mostly diverts pairs to `unmonitored` or `fail`, not to
  `pass`. Models differ in their route (Gemini Pro → `fail`, Gemma → `pass`). This makes
  §8.4's three bullet points visual and addresses M10.

**Optional Figure 5: Detection does not predict safety.**
- *Data:* Study 3, offered schema, adjacent arm. x = violation recall, y = FGR, one point
  per model, with plain-arm points as hollow markers connected by lines.
- *Point:* the four high-recall models still have FGR 0.16–0.36. This replaces the current
  Figure 1, whose axes are degenerate (`always_fail` sits on the oracle's point, as the
  text admits).

### Appendix figures

- **A1. Anchor label quality.** A Sankey or alluvial plot of the 20 violation labels:
  engine view → strict view (kept / to needs_evidence / to deadline alert) → second
  auditor (violation_shown / cannot_tell / compliance_shown). Beside it, a 2×2 table of
  the two auditors' overturn decisions on 120 withheld pairs, showing κ = −0.024.
- **A2. Prompt diff.** The four verdict menus as a side-by-side diff with changed lines
  highlighted. It shows exactly what P1, P2 and S2 manipulate (M3).
- **A3. Evidence fields cited in adjacent-arm false greens.** Bar chart of the share of
  false-green lines by cited field (`onboardingCompletedDate`, `workAuthValidThrough`,
  `annualBaseSalary`, `payBandMidpoint`, `i9Status`, non-decoy fields), faceted by model.
  Data: `docs/study3/cache/`. This is the direct mechanism evidence (M1).
- **A4. Rule-family breakdown.** I-9 versus wage FGR, plain versus adjacent, across four
  schemas, from `exploratory_by_rule_family`. Annotate n = 3 firms (I-9) and 9 firms
  (wage). Use it to show that the wage "plain" arm already has an adjacent column (FGR
  0.44 offered).
- **A5. Regime heatmap.** Table 4 as a regime × model heatmap of FGR (offered, anchor),
  annotated with n.
- **A6. Schema contrasts on the anchor firm.** A forest plot combining Tables 3 and 8,
  colour-coded by run regime (1 run versus mean of 3) and annotated with the Holm family.
- **A7. Run-to-run spread.** Strip plot of the three runs for each of the 24 Vertex cells.
- **A8. Boundary sensitivity of generated labels.** The number of labels flipped under
  alternative interpretations (calendar days: 55; weekdays without holidays: 6), from
  `labelcheck/INTERPRETATIONS.md`.

---

## 7. The strongest version of this paper

**Thesis in one sentence.** Whether a compliance verdict system reports unassessable
obligations as satisfied depends less on the model than on two things a product team
controls: the output contract, and which proxy columns the system is shown. A
preregistered, paired manipulation on construction-labelled firms measures both.

### Recommended outline (~9 pages body)

| § | Title | Target length | Content |
|---|---|---|---|
| — | Abstract | 200 words | False green definition. Instrument (anchor firm plus paired generator). The preregistered result first: adjacent columns +0.43 dashboard / +0.22 recommended, abstention +0.26 and definition-and-warning +0.08 on adjacent-arm firms, 7 models / 5 developers. Detection ≠ safety. Exploratory anchor study second, in one sentence. Labels: AI-checked, no counsel. Drop the per-model ranges. |
| 1 | Introduction | 1.0 p | The dashboard-cell argument (cut by half). The asymmetry. Figure 1. Three findings with numbers. Contributions (4, not 5: task + instrument, metric suite, preregistered manipulation study, release). Positioning against DEMM-Bench and Partial Evidence Bench, in two sentences. |
| 2 | Related work | 0.75 p | Keep the "nearest neighbours" and "abstention" paragraphs. Compress legal NLP, immigration data and compliance checking into one paragraph. Move structured-data and output-format work to one paragraph each. |
| 3 | Task and evidence standard | 1.0 p | Merge the current §3 and §4. A four-state definitions table. The formal pair definition. **New: "What counts as evidence"** (M1). The scoring rules, including `unmonitored` and unanswered pairs (M10). |
| 4 | Instrument | 1.25 p | 4.1 Rulebook (one paragraph plus a coverage table: 194 / anchor / generator). 4.2 Generator: labels-before-data, near-miss controls, whole-export withholding, adjacent-column rendering. 4.3 Label validation: the checker (1,176 distinct labels, same-family caveat, boundary sensitivity). 4.4 Anchor firm: realism probe, its known label problems, κ. Released scale (one line). |
| 5 | Metrics and baselines | 0.75 p | FGR, recall, false alarm, abstention P/R. Table 1 (trivial baselines) with a three-sentence reading. The reporting requirement. |
| 6 | Models and protocol | 0.5 p | The prompt (frozen), the four schemas with the exact diff (pointer to Figure A2), decoding, scoping (two sentences), parsing and coverage (two sentences). Everything else goes to the appendix. |
| 7 | Preregistered study: schemas × adjacent columns | 2.0 p | Design (firms, arms, conditions, 18 clusters by composition). Figure 2. Figure 3. Plain-arm contrasts reported as exploratory (M2). The rule-family breakdown (labelled exploratory, n firms). Detection ≠ safety (Figure 5 or the Figure 2 inset). Evidence-field analysis (Figure A3 summary, M1). False alarms (S5) in one sentence. |
| 8 | Exploratory study on the anchor firm | 1.0 p | Study 1 plus the Vertex block, presented as *the study that generated the hypotheses*. One combined table: 13 models × offered / dashboard FGR with coverage. Figure 4 (verdict flow). Label views summarised in one sentence. Qualitative excerpts (keep; they are good). |
| 9 | Discussion | 0.5 p | Design rules (once). "Is this only prompt sensitivity?" (keep the no-prompt-change argument). What the evidence standard implies for deployed systems. |
| 10 | Limitations | 0.5 p | Compress to bullets: no counsel / no human baseline; narrow generator; AI-written checker; one prompt; no closed frontier models; synthetic, no OCR; 18 clusters. |
| — | Ethics, COI, AI use | 0.25 p | Keep as is, shortened. |

### Appendix

- A. Reproduction commands.
- B. Prompts verbatim, plus the Figure A2 diff.
- C. Protocol history: the pilot, the output cap, model substitutions as a timeline,
  delivery-failure departures, Study 3 operations. Renumber in order.
- D. Anchor label views: Tables 2b and 2c, both audits, Figure A1, and the full per-pair
  disagreement list.
- E. The Study 2 generated-firm results: Table 7's Study 2 rows, the scoping defect, and
  the retracted near-miss reading.
- F. All per-model tables: Tables 2, 3, 4 (as heatmap A5), 7, 8, 9, 10, 11.
- G. Generator interpretive choices and boundary sensitivity (A8).
- H. Datasheet.

### What to cut or move

- **§8.3 (Study 2):** move entirely to the appendix. It is superseded, its sweep was
  stopped, and it contains a retraction.
- **§7.1, §7.2 operational detail, Appendix C narrative:** in the body, one sentence each
  with a pointer.
- **Tables 2b, 2c, 3, 4, 7, 8, 11:** move to the appendix, replaced by Figures 2–4 and one
  combined anchor table.
- **The repeated disclosures listed in §4.2 of this review:** state each once.
- **§1's "Terms" glossary:** move to a footnote or the appendix, and define terms at first use.
- **Current Figure 1** (recall vs FGR on the anchor firm): replace it. Its axes cannot
  distinguish `always_fail` from the oracle.
- **The `unmonitored` exposition in §3:** reduce to two sentences plus the M10 scoring note,
  since no label uses it.
- **"Vertex block" as a name:** rename it.
- **The title:** consider emphasising the manipulation study over "Benchmark" (M9). If
  "Benchmark" stays, the coverage table in §4 is mandatory.

### Bottom line for the authors

The study is better than the paper. It needs no new experiments to clear a D&B bar. It
needs:
- the evidence-standard argument (M1);
- the evidence-field analysis from data already in `docs/study3/cache` (M1);
- honest scoping of P1 and P2 to the adjacent arm (M2) and renaming P2 (M3);
- κ and the distinct-label count (M5, M6);
- a reordering that puts the preregistered result first (M7).

For ICAIL/JURIX, N1 (even a small counsel-labelled sample) is the difference between a
methodological curiosity and a legal-informatics contribution.
