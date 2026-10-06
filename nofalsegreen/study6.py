"""Study 6: Studies 4 and 5 on two more developers' models.

DECLARED 2026-10-06, before any Study 6 call (docs/STUDY6_DECLARATION.md).

Studies 3b-5 ran on three Google models only. Study 6 runs the declared Study 4 and
Study 5 cells, unchanged, on DeepSeek V3.2 (DeepSeek) and GLM-5.2 (Zhipu AI), both
served by Google on Vertex AI as pay-per-token models. Firms, prompts and scoring are
those of Studies 4 and 5; only the model set differs.
"""

DECLARED_ON = "2026-10-06"
# publisher model id -> served location
MODELS = {"deepseek-ai/deepseek-v3.2-maas": "global", "zai-org/glm-5.2-maas": "global"}
