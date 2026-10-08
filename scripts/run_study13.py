"""Run Study 13 (docs/STUDY13_DECLARATION.md). Both prompts are launched together for each
model, so their calls interleave in time; one process per (workflow, layout, prompt)."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from nofalsegreen import study4, study6, study13  # noqa: E402

OUT = ROOT / "docs" / "study13"
TAG = sys.argv[1] if len(sys.argv) > 1 else "r0"
# r2: the replication of the declaration addendum, with the corrected rule statement
VARIANTS = (("contract13b_evidence_first", "contract13b_extract") if TAG == "r2"
            else ("contract13_evidence_first", "contract13_extract"))

if __name__ == "__main__":
    for d in ("cache", "runs", "logs"):
        (OUT / d).mkdir(parents=True, exist_ok=True)
    models = [("vertex", m) for m in study4.MODELS] + [("vertexopen", m) for m in study6.MODELS]
    n = 0
    for prov, model in models:
        short = model.split("/")[-1]
        for wf in study13.WORKFLOWS:
            for lay in study13.LAYOUTS:
                for var in VARIANTS:
                    t = f"{short}__{wf}-{lay}__{var}" + ("" if TAG == "r0" else f"__{TAG}")
                    cmd = [sys.executable, "-u", str(ROOT / "scripts" / "run_free.py"), "--provider", prov,
                           "--model", f"{prov}/{model}#{TAG}", "--firms", "0", "--variant", var, "--batch", "12",
                           "--rpm", "6", "--rpd", "100000", "--study13", f"{wf}:{lay}",
                           "--cache", str(OUT / "cache" / f"{t}.json"), "--out", str(OUT / "runs" / f"{t}.json"),
                           "--checkpoint", str(OUT / "runs" / f".ckpt_{t}.json")]
                    subprocess.Popen(cmd, cwd=ROOT, stdout=(OUT / "logs" / f"{t}.log").open("a"),
                                     stderr=subprocess.STDOUT, start_new_session=True)
                    n += 1
    print("started", n)
