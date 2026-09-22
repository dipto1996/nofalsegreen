"""Run the whole study across as many quota-days as it takes, unattended.

The free tier allows 50 requests a day. The declared 140-pair subset costs 12
calls per model per ablation condition, so four model-conditions fit in a day
and the full six-model, two-condition study takes three days.

This script walks the work queue in a fixed order, stops cleanly when the daily
quota is gone, and picks up exactly where it left off next time. Run it once a
day, or from cron; it is safe to run repeatedly on the same day because
completed work is skipped.

    python3 scripts/daily_sweep.py             # do as much as today's quota allows
    python3 scripts/daily_sweep.py --plan      # show the queue, make no calls
"""

from __future__ import annotations

import argparse
import datetime
import json
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from baselines.prompts import ABSTAIN_OFFERED, ABSTAIN_WITHHELD  # noqa: E402
from nofalsegreen.subset import DEFAULT_SIZE  # noqa: E402

RESULTS = ROOT / "docs" / "llm_results.json"

# Fixed order: strongest model first, so a study cut short by circumstance still
# has its most informative row. Both conditions of a model run adjacently so the
# ablation is complete for a model before the next model starts.
MODELS = [
    "nvidia/nemotron-3-ultra-550b-a55b:free",
    "nvidia/nemotron-3-super-120b-a12b:free",
    "nex-agi/nex-n2.5-pro:free",
    "nvidia/nemotron-3.5-lightning:free",
    "nex-agi/nex-n2.5-mini:free",
    "poolside/laguna-xs-2.1:free",
]
VARIANTS = [ABSTAIN_OFFERED, ABSTAIN_WITHHELD]
BATCH = 12


def quota_reset_at() -> datetime.datetime | None:
    """When the daily free-model allowance next resets, from OpenRouter's own
    headers. Returns None when quota is currently available.

    The window is midnight UTC, not local midnight, which is why "run it
    tomorrow" is the wrong instruction: the reset can land mid-afternoon local.
    """
    sys.path.insert(0, str(ROOT))
    from nofalsegreen.credentials import load_key

    body = json.dumps({
        "model": "nex-agi/nex-n2.5-mini:free",
        "max_tokens": 5,
        "messages": [{"role": "user", "content": "OK"}],
    }).encode()
    req = urllib.request.Request(
        "https://openrouter.ai/api/v1/chat/completions",
        data=body,
        headers={"Content-Type": "application/json",
                 "Authorization": f"Bearer {load_key('openrouter')}"},
    )
    try:
        with urllib.request.urlopen(req, timeout=45) as r:
            payload = json.loads(r.read())
        if isinstance(payload.get("error"), dict):
            meta = payload["error"].get("metadata") or {}
            ts = (meta.get("headers") or {}).get("X-RateLimit-Reset")
            if ts:
                return datetime.datetime.fromtimestamp(int(ts) / 1000)
        return None
    except urllib.error.HTTPError as e:
        try:
            meta = json.loads(e.read().decode()).get("error", {}).get("metadata", {}) or {}
            ts = (meta.get("headers") or {}).get("X-RateLimit-Reset")
            if ts:
                return datetime.datetime.fromtimestamp(int(ts) / 1000)
        except Exception:  # noqa: BLE001
            pass
        return datetime.datetime.now() + datetime.timedelta(hours=1)
    except Exception:  # noqa: BLE001
        return None


def completed() -> set[str]:
    """Keys of runs that already have a scored firm."""
    if not RESULTS.exists():
        return set()
    doc = json.loads(RESULTS.read_text())
    return {k for k, v in doc.get("runs", {}).items() if v.get("per_firm")}


def queue() -> list[tuple[str, str]]:
    done = completed()
    return [
        (m, v)
        for m in MODELS
        for v in VARIANTS
        if f"{m}::{v}" not in done
    ]


def run_one(model: str, variant: str, subset: int) -> str:
    """Returns 'done', 'quota', or 'error'."""
    cmd = [
        sys.executable, "-u", str(ROOT / "scripts" / "run_free.py"),
        "--provider", "openrouter", "--model", model,
        "--firms", "0", "--variant", variant,
        "--batch", str(BATCH), "--subset", str(subset), "--rpd", "50",
    ]
    proc = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
    out = proc.stdout + proc.stderr
    for line in out.splitlines():
        if line.strip().startswith(("northwind", "  northwind")):
            print(f"    {line.strip()}")
    if "daily quota exhausted" in out:
        return "quota"
    if proc.returncode != 0:
        print(f"    error: {out.strip().splitlines()[-1][:160] if out.strip() else 'no output'}")
        return "error"
    return "done"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--plan", action="store_true", help="print the queue, make no calls")
    ap.add_argument("--subset", type=int, default=DEFAULT_SIZE)
    ap.add_argument("--wait", action="store_true",
                    help="if quota is spent, sleep until it resets and continue, "
                         "repeating until the study is done")
    args = ap.parse_args()

    q = queue()
    done = completed()
    total = len(MODELS) * len(VARIANTS)

    print(f"study: {len(MODELS)} models x {len(VARIANTS)} conditions = {total} runs")
    print(f"subset: {args.subset} pairs -> ~{-(-args.subset // BATCH)} calls each")
    print(f"done: {len(done)}/{total}   remaining: {len(q)}")
    print(f"at 50 calls/day: ~{-(-len(q) * (-(-args.subset // BATCH)) // 50)} more day(s)\n")

    if args.plan:
        for m, v in q:
            print(f"  pending  {m.split('/')[-1]:<34} {v}")
        return 0

    while True:
        q = queue()
        if not q:
            break

        if args.wait:
            reset = quota_reset_at()
            if reset is not None:
                wait_s = max(0.0, (reset - datetime.datetime.now()).total_seconds()) + 60
                print(f"  quota spent; resets {reset:%Y-%m-%d %H:%M} local "
                      f"({wait_s / 3600:.1f}h). Sleeping.", flush=True)
                time.sleep(wait_s)
                continue

        stop = False
        for model, variant in q:
            print(f"  {model.split('/')[-1]} / {variant}", flush=True)
            outcome = run_one(model, variant, args.subset)
            if outcome == "quota":
                if args.wait:
                    print("    quota exhausted mid-run; will resume after reset")
                else:
                    print("\n  daily quota exhausted. Re-run this script "
                          "after the reset to continue.")
                stop = True
                break
            if outcome == "error":
                print("    skipping to next run")
        if stop and not args.wait:
            break
        if not args.wait:
            break

    remaining = len(queue())
    print(f"\nremaining after this session: {remaining}/{total}")
    if remaining == 0:
        print("study complete. Next: scripts/fill_results.py, scripts/make_figure.py")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
