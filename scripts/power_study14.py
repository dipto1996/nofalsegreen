"""Power analysis for Study 14 (docs/STUDY14_DECLARATION.md), from Study 13's replication.

Unit: a packet content. Each Study 14 content is rendered in two unseen layouts, so a
content's contrast is the mean of two rendering-level contrasts. We resample Study 13's
held-out rendering-level contrasts (eighteen per test), shrink each effect to half its
observed size to allow for harder layouts, and estimate the power of the exact sign-flip test
over n contents with Holm over four tests. No API call; writes docs/study14/power.json."""

from __future__ import annotations

import json
import random
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

SIMS, SEED = 2000, 20261008


def p_signflip(xs, rng, draws=4000):
    n = len(xs)
    obs = abs(sum(xs)) / n
    hits = sum(abs(sum(x if rng.random() < 0.5 else -x for x in xs)) / n >= obs - 1e-12 for _ in range(draws))
    return (hits + 1) / (draws + 1)


def main() -> int:
    r = json.loads((ROOT / "docs" / "study13" / "results_r2.json").read_text())
    per = {}
    for m in ("H1", "H2", "H3"):
        k = [x for x in r["primary"] if x.startswith(m)][0]
        per[m] = r["primary"][k]
    # Rendering-level contrasts are modelled as normal, with the observed mean halved and the SD
    # implied by the 18-packet bootstrap interval. H4 (hybrid vs parser) is assumed no larger
    # than H2, so H2's power bounds the design. Alpha 0.05/4 (Holm's strictest step).
    out = {"assumption": "effects halved; SD from Study 13 replication packet bootstrap intervals"}
    rng = random.Random(SEED)
    for n in (8, 12, 16, 20, 24, 30):
        powers = {}
        for m, v in per.items():
            lo, hi = v["ci95_packet_bootstrap"]
            sd = (hi - lo) / (2 * 1.96) * (18 ** 0.5)
            mu = v["delta"] / 2
            ok = 0
            for _ in range(SIMS // 10):
                xs = [(rng.gauss(mu, sd) + rng.gauss(mu, sd)) / 2 for _ in range(n)]
                ok += p_signflip(xs, rng, 1000) < 0.05 / 4
            powers[m] = round(ok / (SIMS // 10), 3)
        out[str(n)] = powers
        print(n, powers)
    (ROOT / "docs" / "study14").mkdir(parents=True, exist_ok=True)
    (ROOT / "docs" / "study14" / "power.json").write_text(json.dumps(out, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
