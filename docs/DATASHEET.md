# Datasheet: No False Green

Following Gebru et al., *Datasheets for Datasets*.

## Motivation

**Why was this created?** Automated compliance systems emit machine-generated verdicts
about an organisation's regulatory obligations. Existing evaluation measures accuracy on
isolated determinations, which cannot detect the deployment-critical error: reporting an
obligation as satisfied when the evidence needed to assess it was never present. No
public benchmark makes correct abstention the majority class or scores it directly.

**Who funded it?** Built by the author from artifacts developed for a commercial
compliance product. No external funding.

## Composition

**What do instances represent?** Two kinds.

1. **Firms.** A synthetic employer: a bundle of source exports (HR roster, payroll,
   Labor Condition Applications, Form I-9 records, E-Verify cases, and others).
2. **Pairs.** One `(obligation, entity)` unit of prediction. An entity is a worker, an
   LCA, a worksite, a wage cohort, or the employer as a whole.

**How many instances?**

| | Count |
|---|---|
| Anchor firm (hand-authored) | 1 firm, 221 pairs, 11 source exports, 151 entities |
| Anchor firm planted violations | 20 |
| Anchor firm evidence requests | 201 |
| Generated firms (seeds 1-30, default config) | 30 firms, 58,740 pairs |
| Generated withheld-evidence share | 45.3% |
| Rulebook obligations | 194 across 10 regimes (196 manifest entries), plus 17 engine aliases/roll-ups |

Generated firm count is unbounded; any seed produces a new instance.

**Is there a label?** Yes: one verdict per pair from `{pass, fail, needs_evidence,
unmonitored}`, plus a `basis` recording why that is the label, and a severity.

**Is anything missing?** By design. Withheld evidence is the mechanism that produces
the `needs_evidence` class. Which fields were withheld is recorded in the label.

**Are instances related?** Yes. Pairs within a firm share source records, so a system
that misreads one export is wrong on a correlated group of pairs. Results should be
aggregated per firm before averaging, which is what `scripts/sweep.py` does.

**Recommended splits?** None. This is a diagnostic evaluation set, not a training set.
Fitting a model to these labels would defeat the purpose.

**Errors or noise?** The generated labels are exact by construction. The anchor firm's
expectations are hand-authored and were revised repeatedly as defects were found in the
reference engine; the current pin is 221 items and its revision history is documented in
the source project rather than here.

**Self-contained?** Yes. No external downloads, no API keys, no network access.

**Confidential or offensive content?** None. Every record is synthetic.

**Does it relate to people?** It depicts fictional people. Names are drawn
combinatorially from generic given-name and family-name pools so that CSV joins are
legible. No real individual's data is present, and no name is intended to refer to
anyone. Identifiers such as passport and Social Security numbers are obviously
patterned placeholders.

## Collection

**How was the data acquired?** It was authored, not collected. The anchor firm was
written by hand against a test plan that specifies, per worker, which regulatory
mechanism that worker's records exercise. The generated firms are produced by a seeded
program.

**Who was involved?** The author.

**Over what timeframe?** The anchor firm and rulebook were developed during 2026. All
date-relative rules evaluate against a pinned `as_of` of 2026-06-29, so the planted
expiry windows do not rot.

**Ethical review?** Not applicable; no human subjects.

## Preprocessing

**Was anything cleaned or labelled?** The rulebook is built programmatically from the
source engine's machine-readable registry of a regulatory manifest (196 entries, 194
rule ids), preserving each obligation's check, threshold, citation and verbatim
description of the information needed. Seventeen engine rule ids used by the anchor
firm are resolved through the engine's own alias table or assembled from the manifest
rules they roll up; see `rulebook/source/engine_aliases.json`. The source manifest had previously been through a
citation-verification pass in which incorrect citations and thresholds were corrected
inline.

**Is the raw data available?** The source exports are the raw data and are included.

## Uses

**Intended use.** Diagnostic evaluation of compliance systems, and study of abstention
under absent evidence in structured-record settings.

**What should it not be used for?**

- **Not for training.** Fitting to these labels measures nothing.
- **Not as a compliance product or as legal advice.** The rulebook is a research
  artifact. A high score does not mean a system is fit to advise an employer.
- **Not as a claim about real firms.** Every instance is synthetic; violation rates
  here are generator parameters, not empirical estimates.
- **Not for cross-jurisdiction generalisation.** United States law only.

**Has it been used already?** The anchor firm's expectation set began as the acceptance
gate for one commercial compliance engine. That engine is therefore **not** an
independent baseline for it, and is not reported as one.

## Distribution

Public release under Apache-2.0 (code) and CC-BY-4.0 (data and rulebook). No third-party
IP restrictions: the regulatory text underlying the citations is US government work, and
the citations themselves are references rather than reproductions.

## Maintenance

Maintained by the author. The generator's config and seed fully determine each instance,
so corrections are shipped as a version bump on the rulebook or generator rather than as
a data patch. Breaking changes to the label schema will bump the major version.
