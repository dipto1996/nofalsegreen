"""Vertex block: Google models through Vertex AI. Declared 2026-10-03, before any call.

WHY. Every Study 1 and Study 2 model is a free-tier open-weights model; none is
a current frontier model, and each run was made once. This block adds a frontier
model, a fast tier and an open-weights model from one provider, paid from the
author's startup cloud credits, and repeats every run three times.

MODELS (Vertex AI publisher ids, global endpoint):
  gemini-3.1-pro-preview    frontier tier
  gemini-3.8-flash          fast tier
  gemma-4-26b-a4b-it-maas   open weights, Google-hosted

PROTOCOL. Identical to Studies 1 and 2: prompt v1.1.0, batch 12, scoped
sources, both output schemas, temperature 0, output cap 32,000 tokens (thinking
tokens included), the same delivery-failure rule. Evaluated on the Study 1
anchor subset (140 pairs) and on all six Study 2 firms (252 pairs).

REPEATS. Each (model, study, condition) is run three times (r0, r1, r2) with
identical requests. At temperature 0 a repeat measures run-to-run variation of
the served model, not sampling. Point estimates are the mean of the three;
the spread is reported beside them.

REPORTING. In a block separate from the free-tier models: different access
route, different cost, and models chosen after the free-tier studies began,
which the paper states.
"""

from __future__ import annotations

DECLARED_ON = "2026-10-03"
PROJECT = "settle-v2-dev"
LOCATION = "global"
MODELS = ("gemini-3.1-pro-preview", "gemini-3.8-flash", "gemma-4-26b-a4b-it-maas")
REPEATS = (0, 1, 2)
