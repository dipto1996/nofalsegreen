# Redesign: evidence sufficiency under explicit decision contracts

Status: proposed, 2026-10-07. Supersedes the "legal compliance benchmark" framing.

## 1. Goal and claim boundary

**Research question.** When a decision rule states which observations establish each fact, do
language models distinguish conclusions the evidence establishes from conclusions that
reassuring metadata merely suggests? How do output menus and source representations change
that?

**Claim boundary.** Every label is correct relative to a stated decision contract, checkable by
machine. The paper makes no claim that a contract reproduces real legal or professional
practice. Immigration compliance is one instantiation and the motivating case. No attorney
labels, baseline or adjudication are part of the validation argument.

**Working title.** *No False Green: Evidence Sufficiency and Unsupported Decisions in Language
Models.*

## 2. Decision contracts and certified labels

A **contract** specifies:

- the predicate;
- the facts it depends on;
- for each fact, the sources that establish it (authoritative) and the sources that do not
  (summaries, plans, status flags);
- the rules for dates, missing values and conflicts, including source priority.

Each unknown fact has a finite candidate domain, which includes the boundary values. The
labeller enumerates every complete situation consistent with the visible input:

| Every compatible completion… | Label |
|---|---|
| …satisfies the predicate | `pass` |
| …violates it | `fail` |
| …is mixed | `needs_evidence` |
| …is impossible, because the evidence is inconsistent with no resolution rule | `conflict` (scored as needs_evidence) |

**Certificates.**

- *needs_evidence:* two completions with opposite outcomes and identical visible input.
- *Determinate labels:* the full enumeration over finite domains, which is sound because the
  domains are finite.

An independently written verifier re-checks every certificate. This replaces expert
validation in the argument, and it means a missing field forces abstention only when the
missing value could change the answer.

## 3. The benchmark: three workflows, built to defeat shortcuts

**Workflows.** Each has three or more rules with different structures: threshold, deadline,
two-source conjunction, and alternative valid sources.

- **Workforce compliance.** I-9 timeliness and reverification; the LCA wage under greater-of.
  The existing domain is re-expressed as contracts.
- **Purchase approval.** Spend within an approved budget requires a signed approval record.
  Proxies: an approval-status flag, a requested amount, a planned approver.
- **Engineering acceptance.** A part is accepted if the test report shows a measured load at or
  above the specification. Proxies: a "QA status: Pass" flag, a planned test date, a
  specification sheet.

**Missingness patterns.**

- whole source missing;
- missing rows;
- a single missing fact;
- a complete-looking record that still leaves the predicate undecidable;
- redundant evidence, where removing a source changes nothing;
- a violation established despite another gap;
- a conflict resolved by source priority;
- a conflict with no resolution;
- a reassuring summary beside an adverse authoritative record;
- valid evidence under unfamiliar field names.

**Splits.** Train and test splits do not apply, since no model is trained. Held-out splits are
used for the *predictions*, by:

- rule structure;
- layout family (field-naming conventions);
- missingness pattern;
- workflow.

## 4. The decisive experiment (declared before any call)

A 2×2×2 design within each workflow, holding values fixed:

- **Authority:** the source establishes the fact, or only summarises or plans it.
- **Familiarity:** the field and source names are familiar (e.g. `i9Status`, `qaStatus`), or
  neutral or unfamiliar.
- **Menu:** offered (four verdicts) or forced (pass/fail).

Declared predictions:

| | Prediction |
|---|---|
| P1 | Familiar non-authoritative sources produce more unsupported positives than unfamiliar non-authoritative sources. |
| P2 | Unfamiliar authoritative sources produce more unnecessary abstention than familiar authoritative ones. |
| P3 | The forced menu amplifies P1 more than P2. |
| P4 | The direction of P1–P3 holds on the held-out workflow and layout family. |

Each prediction is tested per workflow and on the held-out split. Failures are reported.

## 5. Intervention: contract-grounded adjudication

**Method.** The model extracts each contract fact with its source as a typed record, or
"absent". A deterministic solver then applies the contract.

**Baselines.**

- always-abstain;
- a record-presence gate (row-level, so it is no longer trivial);
- the strongest evidence-focused prompt (Study 4's evidence-first prompt, refined);
- deterministic rule evaluation on gold extraction, as an upper bound.

**Metrics.** Reported jointly:

- unsupported positives (false greens);
- unsupported negatives;
- correct determinate decisions;
- coverage;
- unnecessary abstention;
- review burden (items routed to a human).

An always-abstain system scores near zero on correct determinate decisions.

## 6. Models and scale

- **Models.** Five: Gemini 3.1 Pro, Gemini 3.8 Flash, Gemma 4 26B, DeepSeek V3.2 and GLM-5.2,
  all on Vertex and credit-covered.
- **Runs.** Two runs on the decisive experiment.
- **Clustering.** The firm or packet is the unit, with exact permutation tests where feasible.
- **Sizing.** Fixed in the declaration from a stated minimum effect (0.10 on the
  unsupported-positive rate).

## 7. Existing results

The current generator's firms are relabelled by the contract labeller. Every label change is
reported, and Studies 3–8 are re-scored under the new labels. No result is declared
"validated" retrospectively. Studies 3–8 remain in the paper as the workforce-compliance
instantiation, described as testing:

- proxy acceptance (non-authoritative familiar sources);
- menu effects;
- direction.

Study 5 is described as public documents embedded in constructed decision tasks.

## 8. Paper changes

| Location | Change |
|---|---|
| Abstract, §1 | Evidence sufficiency under explicit contracts; legal consequences as motivation |
| §3 | The formal task, contracts and certified labels; regulations as the motivation for one instantiation |
| §4 | Certificates, the independent verifier and adversarial controls replace the validation argument |
| §6 | Studies 3–8 as one instantiation; new sections for the three-workflow benchmark, the decisive experiment and the intervention |
| §8 | Technical implications, plus a practitioner section: five questions to ask of an AI system's evidence claims |
| §9 | Boundary: no claim about unrestricted legal practice |
| Appendix I | The expert workbook stays as disclosed pilot material, outside the validation argument |

## 9. Risks

- **Predictions may fail and the intervention may not beat the baselines.** Both are reported as
  found; a clean negative on a declared prediction is still a result.
- **Relabelling may change some existing labels.** Changes are reported, with their effect on
  every Study 3–8 estimate.
- **Novelty against DEMM-Bench, Partial Evidence Bench and ProofWriter.** This rests on P1–P4
  (authority × familiarity × menu, held out) and on the intervention. The related-work section
  states this.

## 10. Order of work

1. Contract format, labeller and certificate verifier (independent implementation). Relabel the
   existing firms and report the changes.
2. The three-workflow packet generator with all missingness patterns, layout families and splits.
3. Declaration of P1–P4 and the intervention comparison, committed before any call.
4. Runs on five models.
5. Scoring, re-scoring Studies 3–8, rewrite, the full verifier, and the Codex review.
