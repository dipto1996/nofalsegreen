"""Run Study 10 (docs/STUDY10_DECLARATION.md). Sharded for throughput only."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from nofalsegreen import study4, study6, study9  # noqa: E402

OUT = ROOT / "docs" / "study10"
SHARDS = {"glm-5.2-maas": 6, "gemini-3.8-flash": 3, "gemini-3.1-pro-preview": 2}

if __name__ == "__main__":
    for d in ("cache", "runs", "logs"):
        (OUT / d).mkdir(parents=True, exist_ok=True)
    models = [("vertex", m) for m in study4.MODELS] + [("vertexopen", m) for m in study6.MODELS]
    n = 0
    for prov, model in models:
        short = model.split("/")[-1]
        k_ = SHARDS.get(short, 1)
        for wf in study9.WORKFLOWS:
            for var in ("contract_sem_offered", "contract_sem_forced"):
                for k in range(k_):
                    t = f"{short}__A-{wf}-familiar__{var}" + (f"__shard{k}of{k_}" if k_ > 1 else "")
                    cmd = [sys.executable, "-u", str(ROOT / "scripts" / "run_free.py"), "--provider", prov,
                           "--model", f"{prov}/{model}#r0", "--firms", "0", "--variant", var, "--batch", "12",
                           "--rpm", "10", "--rpd", "100000", "--study9", f"A:{wf}:familiar",
                           "--cache", str(OUT / "cache" / f"{t}.json"), "--out", str(OUT / "runs" / f"{t}.json"),
                           "--checkpoint", str(OUT / "runs" / f".ckpt_{t}.json")]
                    if k_ > 1:
                        cmd += ["--shard", f"{k}/{k_}"]
                    subprocess.Popen(cmd, cwd=ROOT, stdout=(OUT / "logs" / f"{t}.log").open("a"),
                                     stderr=subprocess.STDOUT, start_new_session=True)
                    n += 1
    print("started", n)
