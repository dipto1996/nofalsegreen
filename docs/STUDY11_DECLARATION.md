# Study 11: how a missing record is visible. Declaration

Declared 2026-10-07 and committed before any Study 11 call, with `study9.gap_packet` /
`gap_firm` and `scripts/score_study11.py`.

## Why

Exploratory analyses after the Study 9 and 10 results showed two things:

- **Between studies.** Unsupported `pass` answers are rare when a deciding value is visibly
  absent from a table the model sees (Study 9). They are common when the whole deciding
  export is absent (Studies 3–8).
- **Within Study 9 Part B.** They rise from blank cells (about 1%) to missing rows (about
  6%).

Describing the evidence instead of binding it to columns did not matter (Study 10). Study 11
tests the account that **the visibility of the gap** drives unsupported positives.

## Design

- **Packets.** Six new packets per workflow (seeds 201–206), twelve entities each, all
  records complete before removal.
- **Target table.** One per workflow: `i9_records`, `signed_approvals`, `test_reports`. For
  the same half of the entities, its deciding values are removed in one of three forms:
  - `blank`: the cells are empty;
  - `row`: those entities' rows are absent;
  - `table`: the whole table is absent from the packet, so every entity loses those values.
- **Everything else is identical:** contracts bound to familiar column names, reassuring proxy
  columns present, the offered menu (`contract_offered`), and the same five models, one run
  each.
- **Labels.** From compatible completions, checked by the independent contract checker.

## Tests

The outcome is unsupported `pass` on pairs labelled `needs_evidence` under *both* forms
compared, which are the same entities and rules.

- **Unit.** The packet (18).
- **Pairing.** Averaged over models with equal weight.
- **Inference.** Exact two-sided sign-flip test, with Holm correction across G1–G3.

| | Contrast |
|---|---|
| G1 | table − row |
| G2 | row − blank |
| G3 | table − blank |

**Descriptive, with no test:**

- per-model and per-workflow effects;
- `fail` and abstention rates on the same pairs.

## Deviations

Any departure from this declaration will be reported in the paper.
