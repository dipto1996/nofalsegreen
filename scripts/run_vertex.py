"""Run the declared Vertex block (nofalsegreen/vertex_block.py).

Each model runs in its own process, in parallel; within a model, studies,
conditions and repeats run in a fixed order. Results go to docs/vertex/, apart
from the free-tier results. Safe to re-run: finished runs are skipped.

    python3 scripts/run_vertex.py            # all models
    python3 scripts/run_vertex.py --plan     # print the work, make no calls
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from nofalsegreen.vertex_block import MODELS, REPEATS  # noqa: E402

OUT = ROOT / "docs" / "vertex"
STUDIES = {"study1": ["--subset", "140"], "study2": ["--study2"]}
VARIANTS = ("abstain_offered", "abstain_withheld")


def jobs_for(model: str) -> list[list[str]]:
    out = []
    for rep in REPEATS:
        for study, extra in STUDIES.items():
            for variant in VARIANTS:
                out.append([
                    sys.executable, "-u", str(ROOT / "scripts" / "run_free.py"),
                    "--provider", "vertex", "--model", f"vertex/{model}#r{rep}",
                    "--firms", "0", "--variant", variant, "--batch", "12",
                    "--rpm", "30", "--rpd", "100000",
                    "--out", str(OUT / f"{study}_llm_results.json"),
                    "--checkpoint", str(OUT / f".checkpoint_{study}.json"),
                    *extra,
                ])
    return out


def run_model(model: str) -> str:
    log = OUT / f"{model}.log"
    with log.open("a") as fh:
        for cmd in jobs_for(model):
            fh.write(f"\n=== {' '.join(cmd[4:12])} {' '.join(cmd[-2:])}\n")
            fh.flush()
            subprocess.run(cmd, cwd=ROOT, stdout=fh, stderr=subprocess.STDOUT)
    return model


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--plan", action="store_true")
    ap.add_argument("--models", nargs="*", default=list(MODELS))
    args = ap.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    if args.plan:
        for m in args.models:
            print(m, len(jobs_for(m)), "runs")
        return 0
    with ThreadPoolExecutor(max_workers=len(args.models)) as ex:
        for m in ex.map(run_model, args.models):
            print("finished", m, flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
