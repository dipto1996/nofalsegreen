"""Resume unfinished Study 4 cells, sharded three ways (throughput only).

Each shard gets its own cache, results and checkpoint files, seeded from the
cell's existing cache so finished batches are not re-requested.
"""
import json, shutil, subprocess, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "docs" / "study4"
N = 3
for f in sorted(OUT.glob("runs/*.json")):
    if f.name.startswith(".") or "__shard" in f.name:
        continue
    runs = list(json.loads(f.read_text())["runs"].values())
    if runs and len(runs[0].get("per_firm", {})) >= 10:
        continue
    t = f.stem
    model, rk, arm, cond = t.split("__")
    for k in range(N):
        tk = f"{t}__shard{k}of{N}"
        c = OUT / "cache" / f"{tk}.json"
        if not c.exists():
            shutil.copy(OUT / "cache" / f"{t}.json", c)
        cmd = [sys.executable, "-u", str(ROOT / "scripts" / "run_free.py"), "--provider", "vertex",
               "--model", f"vertex/{model}#{rk}", "--firms", "0", "--variant", cond, "--batch", "12",
               "--rpm", "10", "--rpd", "100000", "--study4", arm, "--shard", f"{k}/{N}",
               "--cache", str(c), "--out", str(OUT / "runs" / f"{tk}.json"),
               "--checkpoint", str(OUT / "runs" / f".ckpt_{tk}.json")]
        log = (OUT / "logs" / f"{tk}.log").open("a")
        subprocess.Popen(cmd, cwd=ROOT, stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
        print("started", tk)
