"""Power analysis for Study 15 (docs/STUDY15_DECLARATION.md), from Study 14's content-level
results: each declared contrast's content-level differences are modelled as normal with Study
14's mean halved and the SD implied by its 30-content bootstrap interval. H2 (extraction vs the
strengthened code-generation arm) is shown with Study 14's H4 halved and quartered.
Alpha 0.05/3 (Holm's strictest step). No API call; writes docs/study15/power.json."""

from __future__ import annotations

import json
import random
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SIMS, SEED = 400, 20261008


def p_signflip(xs, rng, draws=2000):
    n = len(xs)
    obs = abs(sum(xs)) / n
    hits = sum(abs(sum(x if rng.random() < 0.5 else -x for x in xs)) / n >= obs - 1e-12 for _ in range(draws))
    return (hits + 1) / (draws + 1)


if __name__ == "__main__":
    d = json.loads((ROOT / "docs" / "study14" / "results.json").read_text())
    r = list(d["primary"].values())
    ef = d["secondary"]["extraction - evidence-first: correct decisions"]
    # H1: Study 14 H1; H3: Study 14's extraction - prompt correct decisions; H2: Study 14 H4,
    # in two scenarios, as the strengthened arm may close half or three quarters of the gap.
    spec = {"H1": (r[0], 0.5), "H2 (gap halved)": (r[3], 0.5), "H2 (gap quartered)": (r[3], 0.25), "H3": (ef, 0.5)}
    out = {"assumption": "content-level normal; Study 14 means halved (H2 also quartered); SD from 30-content intervals"}
    rng = random.Random(SEED)
    for n in (30, 50):
        pw = {}
        for h, (v, shrink) in spec.items():
            lo, hi = v["ci95_content_bootstrap"]
            sd = (hi - lo) / (2 * 1.96) * 30 ** 0.5
            mu = v["delta"] * shrink
            pw[h] = round(sum(p_signflip([rng.gauss(mu, sd) for _ in range(n)], rng) < 0.05 / 3
                              for _ in range(SIMS)) / SIMS, 3)
        out[str(n)] = pw
        print(n, pw)
    (ROOT / "docs" / "study15").mkdir(parents=True, exist_ok=True)
    (ROOT / "docs" / "study15" / "power.json").write_text(json.dumps(out, indent=1))
