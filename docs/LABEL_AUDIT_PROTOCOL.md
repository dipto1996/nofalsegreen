# Label audit protocol (declared 2026-10-01, before the audit ran)

## Why

The anchor firm's `needs_evidence` labels were written by a compliance engine.
For some rules the engine reports "evidence class not captured" because its own
column mapping does not read a column, even when the export carries that
information under another name. Example: `i9.section2.employer_signature` is
labelled `needs_evidence`, but `i9_records_export.csv` has
`section2_signed_date` and `section2_examiner_name` populated for every
employee. The benchmark prompt tells models to match columns by meaning, so a
model that does so is scored as a false green on a label the exports contradict.

This was noticed while reading results, which is why the audit is constrained
as below: it covers every withheld pair, not the ones models got wrong, and the
auditor never sees a model output.

## Scope

All 120 `needs_evidence` pairs in the frozen 140-pair subset
(`data/firms/northwind-robotics/subset140.json`). The 20 `fail` labels are not
audited: each is a planted violation whose evidence is in the exports by
construction.

## Blindness

The auditor is a separate agent. It receives a packet containing only, per pair:
the pair id and entity, the obligation text exactly as models saw it (check,
threshold, citation, information needed), the evaluation date, and the export
files that pair's batch was shown. It is not given model replies, scores,
the engine's label notes, or this repository's results files, and is
instructed not to open them.

## Criterion

A label is **overturned** (`evidence_present`) only if, for the pair's entity,
**every required item** under "information needed" is present in the exports
shown for that pair. *Present* means a column whose meaning matches the item,
holding a non-empty value for that entity (or, for an employer-level item, in
any row). An item that is explicitly conditional ("if", "if captured",
"informational", "only if ...") is required only when its condition applies on
the face of the exports.

If any required item is absent, the label **stands** (`evidence_withheld`).
Ambiguity resolves toward the label standing. For each pair the auditor lists
every required item and the `file.column` that supplies it, or `null`.

## The audited view

Overturned pairs are **removed** from scoring in the audited view. They are not
relabelled to `pass` or `fail`: the benchmark's labels are fixed by construction,
and an auditor's verdict would not be. All other pairs are scored as in the
engine view.

**Denominator caution.** Removing pairs shrinks the false-green denominator and
can only remove false greens that sat on overturned pairs. Because the audit
covers every withheld pair and is blind to outputs, which pairs are removed does
not depend on which pairs models got wrong. Every table reporting the audited
view states how many pairs it scores. The engine view remains the headline.

## Limitations, stated in the paper

The auditor is an AI agent, not immigration counsel, and the audit was
commissioned after results were partly known. Its per-pair reasoning is
published (`docs/label_audit.json`) so any reader can check each call.

## Second auditor and violation audit (declared 2026-10-03, before either ran)

**Why.** The first audit had one auditor, so its calls cannot be checked for agreement,
and the 20 `fail` labels were never audited.

**Second auditor.** Gemini 3.1 Pro (Vertex AI, temperature 0), a model from a different
developer than the first auditor. It audits each of the 120 withheld pairs alone, using the
same packet and the Criterion section above verbatim. It sees no model reply, no label note
and no result of the first audit. Agreement with the first audit is reported as raw
agreement and Cohen's kappa.

**Violation audit.** For each of the 20 `fail` pairs, the same model receives the same
packet fields and is asked for a three-way judgment: `violation_shown` (the exports show the
obligation is not met), `compliance_shown`, or `cannot_tell`, item by item. It is not told
the label. A violation label is *supported* only on `violation_shown`.

**Use.** Neither audit changes the headline (engine) view. Pairs overturned by **both**
auditors define a further sensitivity view, and the paper reports how many withheld pairs
each auditor would overturn. A `fail` label not supported is reported pair by pair.
`scripts/second_audit.py` does both and writes `docs/label_audit_second.json`.
Gemini 3.1 Pro is also a model under test. It never sees its own benchmark replies, but the
overlap is stated.
