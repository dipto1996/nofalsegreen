"""Run Study 8 (docs/STUDY8_DECLARATION.md). GLM-5.2 cells are sharded three ways for throughput."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from nofalsegreen import study4, study5, study6, study8  # noqa: E402

OUT = ROOT / "docs" / "study8"

if __name__ == "__main__":
    for d in ("cache", "runs", "logs"):
        (OUT / d).mkdir(parents=True, exist_ok=True)
    models = [("vertex", m) for m in study4.MODELS] + [("vertexopen", m) for m in study6.MODELS]
    cells = ([("study8", a, c, r) for a in study8.ARMS for c in ("abstain_offered", "abstain_withheld") for r in ("r0", "r1")]
             + [("study5", a, "abstain_offered", "r0") for a in study5.STUDY8_ARMS])
    n = 0
    for prov, model in models:
        shards = 3 if "glm" in model else 1
        for st, arm, cond, rk in cells:
            for k in range(shards):
                t = f"{model.split('/')[-1]}__{st}__{arm}__{cond}__{rk}" + (f"__shard{k}of{shards}" if shards > 1 else "")
                cmd = [sys.executable, "-u", str(ROOT / "scripts" / "run_free.py"), "--provider", prov,
                       "--model", f"{prov}/{model}#{rk}", "--firms", "0", "--variant", cond, "--batch", "12",
                       "--rpm", "10", "--rpd", "100000", f"--{st}", arm,
                       "--cache", str(OUT / "cache" / f"{t}.json"), "--out", str(OUT / "runs" / f"{t}.json"),
                       "--checkpoint", str(OUT / "runs" / f".ckpt_{t}.json")]
                if shards > 1:
                    cmd += ["--shard", f"{k}/{shards}"]
                subprocess.Popen(cmd, cwd=ROOT, stdout=(OUT / "logs" / f"{t}.log").open("a"),
                                 stderr=subprocess.STDOUT, start_new_session=True)
                n += 1
    print("started", n)
