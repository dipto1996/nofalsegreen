# Study 9: evidence sufficiency under explicit decision contracts. Declaration

Declared 2026-10-07 and committed before any Study 9 call. Code:

- `nofalsegreen/contracts.py`: contracts, labeller, generator, solver;
- `nofalsegreen/study9.py`;
- the prompt variants `contract_*` in `baselines/prompts.py`;
- `scripts/score_study9.py`;
- `scripts/verify_study9_labels.py`.

## Task and labels

Each of three workflows has two rules, stated as decision contracts:

| Workflow | Rules |
|---|---|
| Workforce | Section 2 deadline; greater-of wage |
| Purchasing | Within the signed approval; approved before order |
| Engineering | Load meets specification; tested before shipping |

Each contract names the only columns that establish each fact. The model sees the contract,
which lists those columns.

**Labels** come from compatible completions (`pass` / `fail` / `needs_evidence`, with
conflicts as `needs_evidence`). Before any call:

- all 1,008 labels agree with an independently written checker
  (`labelcheck/contract_checker.py`, written from `docs/study9/CONTRACT_SPEC.md` alone);
- all 454 `needs_evidence` certificates were verified by that checker
  (`docs/study9/label_verification.json`).

## Part A: authority × familiarity × menu

- **Packets.** Six per workflow, twelve entities each. Entities alternate between `complete`
  and `proxy_only` (one authoritative fact removed; reassuring non-authoritative columns
  remain). Proxies are present for every entity.
- **Renderings.** Familiar names, or neutral codes for every table and column. Values are
  identical. The contract names the columns in the same rendering.
- **Menus.** Offered (`contract_offered`) and forced (`contract_forced`).
- **Unit.** The packet (18). Contrasts are paired on pairs answered under both renderings,
  averaged over models with equal weight. Exact two-sided sign-flip test.

| | Prediction |
|---|---|
| P1 | Under the offered menu, familiar names raise unsupported `pass` on `needs_evidence` pairs, compared with neutral names. |
| P2 | Under the offered menu, neutral names raise abstention on decidable pairs, compared with familiar names. |
| P3 | The familiarity effect on unsupported `pass` is larger under the forced menu than under the offered menu. |
| P4 | P1 holds separately in purchasing and in engineering, the workflows that played no part in forming the hypotheses (Studies 3–8 used workforce records only). |

## Part B: harder packets and an intervention

- **Packets.** Six per workflow, sixteen entities, two of each pattern:
  - complete;
  - proxy only;
  - missing row;
  - blank fact;
  - redundant source;
  - violation despite a gap (workforce only; elsewhere it is complete);
  - conflict resolved by priority;
  - conflict with no resolution.
- **Names.** Familiar.
- **Conditions.**
  - `contract_offered`;
  - `contract_evidence_first`;
  - `contract_extract`: the model reports each fact with its source; a deterministic solver
    accepts a value only from a named column and applies the contract;
  - a row-level presence gate on top of each prompt: route to `needs_evidence` when any fact
    has no authoritative value;
  - always abstain.
- **Metrics,** per packet, averaged over models:
  - unsupported positives: `pass` where the label is not `pass`;
  - unsupported negatives;
  - correct determinate decisions;
  - coverage;
  - unnecessary abstention;
  - review burden.

| | Test |
|---|---|
| I1 | Unsupported positives: extraction + solver − evidence-first prompt |
| I2 | Correct determinate decisions: extraction + solver − evidence-first prompt |
| I3 | Correct determinate decisions: extraction + solver − presence gate on the evidence-first prompt |

## Inference

Holm correction across P1–P4 and I1–I3. Directions are reported whatever their sign.

## Models

Five models, at batch 12, one run each:

- Gemini 3.1 Pro
- Gemini 3.8 Flash
- Gemma 4 26B
- DeepSeek V3.2
- GLM-5.2

## Deviations

Any departure from this declaration will be reported in the paper.
