"""Resume unfinished Study 6 cells, sharded three ways (throughput only).

Each shard gets its own cache, results and checkpoint files, seeded from the cell's
existing cache so finished batches are not re-requested.
"""
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "docs" / "study6"
N = 3
for log in sorted(OUT.glob("logs/*.log")):
    t = log.stem
    if "__shard" in t or "wrote " in log.read_text():
        continue
    model_short, st, arm, cond = t.split("__")
    model = {"glm-5.2-maas": "zai-org/glm-5.2-maas", "deepseek-v3.2-maas": "deepseek-ai/deepseek-v3.2-maas"}[model_short]
    for k in range(N):
        tk = f"{t}__shard{k}of{N}"
        c = OUT / "cache" / f"{tk}.json"
        if not c.exists() and (OUT / "cache" / f"{t}.json").exists():
            shutil.copy(OUT / "cache" / f"{t}.json", c)
        cmd = [sys.executable, "-u", str(ROOT / "scripts" / "run_free.py"), "--provider", "vertexopen",
               "--model", f"vertexopen/{model}#r0", "--firms", "0", "--variant", cond, "--batch", "12",
               "--rpm", "10", "--rpd", "100000", f"--{st}", arm, "--shard", f"{k}/{N}",
               "--cache", str(c), "--out", str(OUT / "runs" / f"{tk}.json"),
               "--checkpoint", str(OUT / "runs" / f".ckpt_{tk}.json")]
        subprocess.Popen(cmd, cwd=ROOT, stdout=(OUT / "logs" / f"{tk}.log").open("a"),
                         stderr=subprocess.STDOUT, start_new_session=True)
        print("started", tk)
