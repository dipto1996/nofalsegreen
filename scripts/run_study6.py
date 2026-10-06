"""Run Study 6 (docs/STUDY6_DECLARATION.md): the Study 4 and Study 5 cells on two more models."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from baselines.prompts import CITE_FIRST, FACTORIAL  # noqa: E402
from nofalsegreen import study5, study6  # noqa: E402

OUT = ROOT / "docs" / "study6"
OFF, DASH = "abstain_offered", "abstain_withheld"
CELLS = ([("study4", a, c) for a in ("plain", "proxy", "renamed", "irrelevant", "adverse") for c in (OFF, DASH)]
         + [("study4", a, v) for a in ("plain", "proxy") for v in (*FACTORIAL, CITE_FIRST)]
         + [("study5", a, c) for a in study5.ARMS for c in (OFF, DASH)])

if __name__ == "__main__":
    for d in ("cache", "runs", "logs"):
        (OUT / d).mkdir(parents=True, exist_ok=True)
    only = sys.argv[1:]  # optional subset of tags, for resuming
    for model in study6.MODELS:
        for st, arm, cond in CELLS:
            t = f"{model.split('/')[-1]}__{st}__{arm}__{cond}"
            if only and t not in only:
                continue
            cmd = [sys.executable, "-u", str(ROOT / "scripts" / "run_free.py"), "--provider", "vertexopen",
                   "--model", f"vertexopen/{model}#r0", "--firms", "0", "--variant", cond, "--batch", "12",
                   "--rpm", "10", "--rpd", "100000", f"--{st}", arm,
                   "--cache", str(OUT / "cache" / f"{t}.json"), "--out", str(OUT / "runs" / f"{t}.json"),
                   "--checkpoint", str(OUT / "runs" / f".ckpt_{t}.json")]
            subprocess.Popen(cmd, cwd=ROOT, stdout=(OUT / "logs" / f"{t}.log").open("a"),
                             stderr=subprocess.STDOUT, start_new_session=True)
            print("started", t)
