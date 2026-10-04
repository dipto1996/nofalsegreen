"""Run Study 3c: one process per (model, rendering, condition)."""

from __future__ import annotations

import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from nofalsegreen import study3c  # noqa: E402

OUT = ROOT / "docs" / "study3c"


def run(w):
    model, arm, cond = w
    t = f"{model}__{arm}__{cond}"
    cmd = [sys.executable, "-u", str(ROOT / "scripts" / "run_free.py"), "--provider", "vertex",
           "--model", f"vertex/{model}#r0", "--firms", "0", "--variant", cond, "--batch", "12",
           "--rpm", "10", "--rpd", "100000", "--study3c", arm,
           "--cache", str(OUT / "cache" / f"{t}.json"), "--out", str(OUT / "runs" / f"{t}.json"),
           "--checkpoint", str(OUT / "runs" / f".ckpt_{t}.json")]
    with (OUT / "logs" / f"{t}.log").open("a") as fh:
        subprocess.run(cmd, cwd=ROOT, stdout=fh, stderr=subprocess.STDOUT)
    return t


if __name__ == "__main__":
    for d in ("cache", "runs", "logs"):
        (OUT / d).mkdir(parents=True, exist_ok=True)
    work = [(m, a, c) for m in study3c.MODELS for a, c in study3c.CELLS]
    with ThreadPoolExecutor(max_workers=len(work)) as ex:
        for t in ex.map(run, work):
            print("finished", t, flush=True)
