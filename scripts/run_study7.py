"""Run Study 7 (docs/STUDY7_DECLARATION.md): two new real-LCA arms, offered schema, five models."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from nofalsegreen import study4, study5, study6  # noqa: E402

OUT = ROOT / "docs" / "study7"

if __name__ == "__main__":
    for d in ("cache", "runs", "logs"):
        (OUT / d).mkdir(parents=True, exist_ok=True)
    models = [("vertex", m) for m in study4.MODELS] + [("vertexopen", m) for m in study6.MODELS]
    for prov, model in models:
        for arm in study5.STUDY7_ARMS:
            for k in range(3):  # three shards per cell, for throughput only
                t = f"{model.split('/')[-1]}__{arm}__shard{k}of3"
                cmd = [sys.executable, "-u", str(ROOT / "scripts" / "run_free.py"), "--provider", prov,
                       "--model", f"{prov}/{model}#r0", "--firms", "0", "--variant", "abstain_offered",
                       "--batch", "12", "--rpm", "10", "--rpd", "100000", "--study5", arm, "--shard", f"{k}/3",
                       "--cache", str(OUT / "cache" / f"{t}.json"), "--out", str(OUT / "runs" / f"{t}.json"),
                       "--checkpoint", str(OUT / "runs" / f".ckpt_{t}.json")]
                subprocess.Popen(cmd, cwd=ROOT, stdout=(OUT / "logs" / f"{t}.log").open("a"),
                                 stderr=subprocess.STDOUT, start_new_session=True)
                print("started", t)
