# Study 10: binding evidence to sources versus describing it. Declaration

Declared 2026-10-07 and committed before any Study 10 call, with the `contract_sem_*`
prompt variants, `study9.semantic_obligations()` and `scripts/score_study10.py`.

## Why

In Study 9 Part A the contract names the only columns that establish each fact. Early Part A
replies showed few unsupported `pass` answers, while Studies 3–8 showed many. Those studies
described the evidence the obligations need ("information needed") instead of binding it to
named columns.

That comparison spans different studies and was noticed after Part A results were seen, so
Study 10 tests it directly.

## Design

- **Firms and conditions.** The Study 9 Part A packets, with familiar names and identical
  records.
- **The only change.** Each rule describes its evidence instead of binding it:
  - the rule states "Information needed: <fact names>";
  - the system prompt drops the sentence saying that only named columns establish a fact;
  - the offered menu says "the records establish" instead of "the named columns establish".
- **Menus.** Offered (`contract_sem_offered`) and forced (`contract_sem_forced`).
- **Comparison.** Against the Study 9 Part A familiar cells (`contract_offered`,
  `contract_forced`).
- **Models.** The same five; one run each.
- **Labels.** Unchanged. Every proxy column differs in name and meaning from the missing
  fact it sits beside (onboarding date versus Section 2 date; requested amount versus signed
  approval amount; target load versus measured load; planned test date versus test date). So
  `needs_evidence` stays the correct reading under an ordinary-meaning description too.

## Tests

The outcome is unsupported `pass` on `needs_evidence` pairs.

- **Unit.** The packet (18).
- **Pairing.** Paired on pairs answered in both conditions, averaged over models with equal
  weight.
- **Inference.** Exact two-sided sign-flip test, with Holm correction across B1–B3.

| | Contrast | Packets |
|---|---|---|
| B1 | described − bound, offered menu | all 18 |
| B2 | described − bound, forced menu | all 18 |
| B3 | described − bound, offered menu | purchasing and engineering only (12) |

**Descriptive, with no test:**

- abstention on decidable pairs;
- per-model effects;
- the fields cited on unsupported `pass` answers.

## Deviations

Any departure from this declaration will be reported in the paper.
