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


def jobs_for(model: str, rep: int, variants=VARIANTS, group: str = "") -> list[list[str]]:
    """One process per (model, repeat), each with its OWN cache, results and
    checkpoint files: the harness rewrites those files whole on every save, so
    two writers on one file lose each other's work."""
    tag = f"{model}__r{rep}{'__' + group if group else ''}"
    out = []
    for study, extra in STUDIES.items():
        for variant in variants:
            out.append([
                sys.executable, "-u", str(ROOT / "scripts" / "run_free.py"),
                "--provider", "vertex", "--model", f"vertex/{model}#r{rep}",
                "--firms", "0", "--variant", variant, "--batch", "12",
                "--rpm", "10", "--rpd", "100000",
                "--cache", str(OUT / "cache" / f"{tag}.json"),
                "--out", str(OUT / "runs" / f"{tag}__{study}.json"),
                "--checkpoint", str(OUT / "runs" / f".ckpt_{tag}__{study}.json"),
                *extra,
            ])
    return out


def run_job(model: str, rep: int, variants=VARIANTS, group: str = "") -> str:
    log = OUT / "logs" / f"{model}__r{rep}{'__' + group if group else ''}.log"
    with log.open("a") as fh:
        for cmd in jobs_for(model, rep, variants, group):
            fh.write(f"\n=== {' '.join(cmd[4:12])} {' '.join(cmd[-2:])}\n")
            fh.flush()
            subprocess.run(cmd, cwd=ROOT, stdout=fh, stderr=subprocess.STDOUT)
    return f"{model} r{rep}"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--plan", action="store_true")
    ap.add_argument("--models", nargs="*", default=list(MODELS))
    ap.add_argument("--variants", nargs="*", default=list(VARIANTS))
    ap.add_argument("--group", default="",
                    help="separates this invocation's cache/results files from another running one")
    args = ap.parse_args()
    for d in ("cache", "runs", "logs"):
        (OUT / d).mkdir(parents=True, exist_ok=True)
    work = [(m, r) for m in args.models for r in REPEATS]
    if args.plan:
        for m, r in work:
            print(m, f"r{r}", len(jobs_for(m, r, args.variants, args.group)), "runs")
        return 0
    with ThreadPoolExecutor(max_workers=len(work)) as ex:
        for done in ex.map(lambda mr: run_job(*mr, args.variants, args.group), work):
            print("finished", done, flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
