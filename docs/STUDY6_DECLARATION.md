# Study 6: Studies 4 and 5 on two more developers' models. Declaration

Declared 2026-10-06 and committed before any Study 6 call, with `nofalsegreen/study6.py`
and `scripts/run_study6.py`.

## Why

Studies 3b–5 ran on three Google models only. Closed frontier models from other developers
are sold on Vertex AI through Google Cloud Marketplace, and promotional credits do not cover
Marketplace purchases, so they were not run. Study 6 runs two current open-weight models from
other developers that Google serves on Vertex as pay-per-token models:

- DeepSeek V3.2 (`deepseek-ai/deepseek-v3.2-maas`)
- GLM-5.2 from Zhipu AI (`zai-org/glm-5.2-maas`)

## Design

- **Cells.** Every declared Study 4 cell except the repeat runs:
  - plain, proxy, renamed, irrelevant and adverse, each under the offered and dashboard schemas;
  - plain and proxy under the eight factorial menus and the evidence-first prompt.

  Plus every Study 5 cell. Firms, prompts and batch size are unchanged; one run each.
- **Analysis.** The declared Study 4 and Study 5 scripts, unchanged, applied to these two
  models (`--study6`):
  - tests H1–H7 and R1–R3, with Holm correction within each study as declared;
  - each pair's effect averaged over the two models with equal weight.
- **What counts as replication.** A test replicates if it is confirmed with the same sign as
  in Studies 4 and 5. Each test's direction is also reported per model.

## Deviations

Any departure from this declaration will be reported in the paper.
