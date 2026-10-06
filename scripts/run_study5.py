"""Run Study 5 (docs/STUDY5_DECLARATION.md): one detached process per (model, arm, schema)."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from nofalsegreen import study4, study5  # noqa: E402

OUT = ROOT / "docs" / "study5"

if __name__ == "__main__":
    for d in ("cache", "runs", "logs"):
        (OUT / d).mkdir(parents=True, exist_ok=True)
    for model in study4.MODELS:
        for arm in study5.ARMS:
            for cond in ("abstain_offered", "abstain_withheld"):
                t = f"{model}__{arm}__{cond}"
                cmd = [sys.executable, "-u", str(ROOT / "scripts" / "run_free.py"), "--provider", "vertex",
                       "--model", f"vertex/{model}#r0", "--firms", "0", "--variant", cond, "--batch", "12",
                       "--rpm", "10", "--rpd", "100000", "--study5", arm,
                       "--cache", str(OUT / "cache" / f"{t}.json"), "--out", str(OUT / "runs" / f"{t}.json"),
                       "--checkpoint", str(OUT / "runs" / f".ckpt_{t}.json")]
                subprocess.Popen(cmd, cwd=ROOT, stdout=(OUT / "logs" / f"{t}.log").open("a"),
                                 stderr=subprocess.STDOUT, start_new_session=True)
                print("started", t)
