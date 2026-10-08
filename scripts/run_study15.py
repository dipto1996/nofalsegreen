"""Run Study 15 (docs/STUDY15_DECLARATION.md): both prompts and the code-generation arm are
launched together for each model and source, so their calls interleave in time."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from nofalsegreen import study4, study6, study15  # noqa: E402

OUT = ROOT / "docs" / "study15"
R2 = "--r2" in sys.argv  # the corrected run (declaration addendum)

if __name__ == "__main__":
    for d in ("cache", "runs", "logs"):
        (OUT / d).mkdir(parents=True, exist_ok=True)
    models = [("vertex", m) for m in study4.MODELS] + [("vertexopen", m) for m in study6.MODELS]
    n = 0
    for prov, model in models:
        short = model.split("/")[-1]
        for wf in study15.WORKFLOWS:
            for var in (("contract15_evidence_first", "contract15_extract") if R2
                        else ("contract13b_evidence_first", "contract13b_extract")):
                t = f"{short}__{wf}__{var}"
                cmd = [sys.executable, "-u", str(ROOT / "scripts" / "run_free.py"), "--provider", prov,
                       "--model", f"{prov}/{model}#r0", "--firms", "0", "--variant", var, "--batch", "12",
                       "--rpm", "6", "--rpd", "100000", "--study15", wf,
                       "--cache", str(OUT / "cache" / f"{t}.json"), "--out", str(OUT / "runs" / f"{t}.json"),
                       "--checkpoint", str(OUT / "runs" / f".ckpt_{t}.json")]
                subprocess.Popen(cmd, cwd=ROOT, stdout=(OUT / "logs" / f"{t}.log").open("a"),
                                 stderr=subprocess.STDOUT, start_new_session=True)
                n += 1
            for sh in range(4):
                cmd = [sys.executable, "-u", str(ROOT / "scripts" / "run_study15_codegen.py"), prov,
                       f"{prov}/{model}#r0", wf, f"{sh}/4"] + (["--r2"] if R2 else [])
                subprocess.Popen(cmd, cwd=ROOT, stdout=(OUT / "logs" / f"{short}__{wf}__codegen15{'b' if R2 else ''}_s{sh}.log").open("a"),
                                 stderr=subprocess.STDOUT, start_new_session=True)
                n += 1
    print("started", n)
