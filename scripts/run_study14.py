"""Run Study 14 (docs/STUDY14_DECLARATION.md): both prompts and the code-generation baseline
are launched together for each model, so their calls interleave in time."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from nofalsegreen import study4, study6, study14  # noqa: E402

OUT = ROOT / "docs" / "study14"

if __name__ == "__main__":
    for d in ("cache", "runs", "logs"):
        (OUT / d).mkdir(parents=True, exist_ok=True)
    models = [("vertex", m) for m in study4.MODELS] + [("vertexopen", m) for m in study6.MODELS]
    n = 0
    for prov, model in models:
        short = model.split("/")[-1]
        for wf in study14.WORKFLOWS:
            for lay in study14.LAYOUTS:
                for var in ("contract13b_evidence_first", "contract13b_extract"):
                    t = f"{short}__{wf}-{lay}__{var}"
                    cmd = [sys.executable, "-u", str(ROOT / "scripts" / "run_free.py"), "--provider", prov,
                           "--model", f"{prov}/{model}#r0", "--firms", "0", "--variant", var, "--batch", "12",
                           "--rpm", "6", "--rpd", "100000", "--study14", f"{wf}:{lay}",
                           "--cache", str(OUT / "cache" / f"{t}.json"), "--out", str(OUT / "runs" / f"{t}.json"),
                           "--checkpoint", str(OUT / "runs" / f".ckpt_{t}.json")]
                    subprocess.Popen(cmd, cwd=ROOT, stdout=(OUT / "logs" / f"{t}.log").open("a"),
                                     stderr=subprocess.STDOUT, start_new_session=True)
                    n += 1
            cmd = [sys.executable, "-u", str(ROOT / "scripts" / "run_study14_codegen.py"), prov,
                   f"{prov}/{model}#r0", wf]
            subprocess.Popen(cmd, cwd=ROOT, stdout=(OUT / "logs" / f"{short}__{wf}__codegen14.log").open("a"),
                             stderr=subprocess.STDOUT, start_new_session=True)
            n += 1
    print("started", n)
