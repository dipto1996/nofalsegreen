"""Run Study 4 (docs/STUDY4_DECLARATION.md): one process per (model, run, arm, schema)."""

from __future__ import annotations

import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from baselines.prompts import CITE_FIRST, FACTORIAL  # noqa: E402
from nofalsegreen import study4  # noqa: E402

OUT = ROOT / "docs" / "study4"
OFF, DASH = "abstain_offered", "abstain_withheld"
CELLS = ([("r0", a, c) for a in study4.CONTROL_ARMS for c in (OFF, DASH)]
         + [("r0", a, v) for a in ("plain", "proxy") for v in (*FACTORIAL, CITE_FIRST)]
         + [(r, a, c) for r in ("r1", "r2") for a in ("plain", "proxy") for c in (OFF, DASH)])


def run(w):
    model, rk, arm, cond = w
    t = f"{model}__{rk}__{arm}__{cond}"
    cmd = [sys.executable, "-u", str(ROOT / "scripts" / "run_free.py"), "--provider", "vertex",
           "--model", f"vertex/{model}#{rk}", "--firms", "0", "--variant", cond, "--batch", "12",
           "--rpm", "10", "--rpd", "100000", "--study4", arm,
           "--cache", str(OUT / "cache" / f"{t}.json"), "--out", str(OUT / "runs" / f"{t}.json"),
           "--checkpoint", str(OUT / "runs" / f".ckpt_{t}.json")]
    with (OUT / "logs" / f"{t}.log").open("a") as fh:
        subprocess.run(cmd, cwd=ROOT, stdout=fh, stderr=subprocess.STDOUT)
    return t


if __name__ == "__main__":
    for d in ("cache", "runs", "logs"):
        (OUT / d).mkdir(parents=True, exist_ok=True)
    work = [(m, *c) for m in study4.MODELS for c in CELLS]
    print(len(work), "processes", flush=True)
    with ThreadPoolExecutor(max_workers=len(work)) as ex:
        for t in ex.map(run, work):
            print("finished", t, flush=True)
