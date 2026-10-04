"""Run Study 3 as declared (docs/STUDY3_PREREGISTRATION.md, nofalsegreen/study3.py).

One process per (model, arm), and one per new model for extension E1, each
with its own cache, results and checkpoint files under docs/study3/. Within a
process the four conditions run in a fixed order. Safe to re-run: finished
runs are skipped.

    python3 scripts/run_study3.py            # everything
    python3 scripts/run_study3.py --plan     # print the work, make no calls
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from nofalsegreen import study3  # noqa: E402

OUT = ROOT / "docs" / "study3"


def models() -> list[tuple[str, str]]:
    return ([("vertex", m) for m in study3.GOOGLE_MODELS]
            + [("vertexopen", m) for m in study3.OPEN_MODELS])


def tag(model: str, part: str, cond: str = "") -> str:
    # The first condition keeps the (model, part) files it was started with.
    suffix = f"__{cond}" if cond and cond != study3.CONDITIONS[0] else ""
    return f"{model.split('/')[-1]}__{part}{suffix}"


def jobs(provider: str, model: str, part: str, conds=study3.CONDITIONS, split=False) -> list[list[str]]:
    where = ["--subset", "140"] if part == "e1" else ["--study3", part]
    out = []
    for cond in conds:
        t = tag(model, part, cond if split else "")
        out.append([sys.executable, "-u", str(ROOT / "scripts" / "run_free.py"),
             "--provider", provider, "--model", f"{provider}/{model}#r0",
             "--firms", "0", "--variant", cond, "--batch", "12",
             "--rpm", "10", "--rpd", "100000",
             "--cache", str(OUT / "cache" / f"{t}.json"),
             "--out", str(OUT / "runs" / f"{t}.json"),
             "--checkpoint", str(OUT / "runs" / f".ckpt_{t}.json"),
             *where])
    return out


def run(work: tuple) -> str:
    provider, model, part, conds = work
    split = len(conds) == 1
    with (OUT / "logs" / f"{tag(model, part, conds[0] if split else '')}.log").open("a") as fh:
        for cmd in jobs(provider, model, part, conds, split):
            fh.write(f"\n=== {' '.join(cmd[4:12])}\n")
            fh.flush()
            subprocess.run(cmd, cwd=ROOT, stdout=fh, stderr=subprocess.STDOUT)
    return f"{model} {part}"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--plan", action="store_true")
    ap.add_argument("--parts", nargs="*", default=["decoy", "plain", "e1"])
    ap.add_argument("--split", nargs="*", default=[],
                    help="models (last path part) to run one process per condition, "
                         "for slow models; each condition then has its own files")
    args = ap.parse_args()
    for d in ("cache", "runs", "logs"):
        (OUT / d).mkdir(parents=True, exist_ok=True)
    work = []
    for part in args.parts:
        for p, m in models():
            if part == "e1" and p == "vertex":
                continue
            if m.split("/")[-1] in args.split:
                work += [(p, m, part, (c,)) for c in study3.CONDITIONS]
            else:
                work.append((p, m, part, study3.CONDITIONS))
    if args.plan:
        for w in work:
            print(*w[:3], w[3] if len(w[3]) == 1 else "all", len(jobs(*w[:3], w[3], len(w[3]) == 1)), "runs")
        return 0
    with ThreadPoolExecutor(max_workers=len(work)) as ex:
        for done in ex.map(run, work):
            print("finished", done, flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
