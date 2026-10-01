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
