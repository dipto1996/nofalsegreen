"""Run the whole study across as many quota-days as it takes, unattended.

The free tier allows 50 requests a day. The declared 140-pair subset costs 12
calls per model per ablation condition, so four model-conditions fit in a day.
Six models are run; two declared models were withdrawn from the free tier
mid-study and replaced (see MODELS).

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
    # Replacements, declared 2026-09-30 before any of their replies existed.
    # OpenRouter withdrew both Nex models from the free tier mid-study; four
    # models, three of them Nemotron, would leave one provider family speaking
    # for the result. Chosen for provider diversity among the models still free
    # with an output limit >= the 32,000-token cap. If either fails the same
    # two-pair screen the originals passed, inkling takes its place.
    # Amended 2026-09-30, still before any replacement reply existed: inkling
    # answers API calls with 403 ("only available on agentic harnesses"), so the
    # fallback is dots-3-note-preview, the remaining free model from a provider
    # family not already in the set. A transient upstream 429 is not a screen
    # failure; the screen is retried until the model answers or is withdrawn.
    "qwen/qwen3.8-27b:free",
    "google/gemma-4-31b-it:free",
]
FALLBACK = "dots-studio/dots-3-note-preview:free"
VARIANTS = [ABSTAIN_OFFERED, ABSTAIN_WITHHELD]
BATCH = 12


def _openrouter_get(path: str) -> dict:
    sys.path.insert(0, str(ROOT))
    from nofalsegreen.credentials import load_key

    req = urllib.request.Request(
        f"https://openrouter.ai/api/v1/{path}",
        headers={"Authorization": f"Bearer {load_key('openrouter')}"},
    )
    with urllib.request.urlopen(req, timeout=45) as r:
        return json.loads(r.read())


def quota_reset_at() -> datetime.datetime | None:
    """When the daily free-model allowance next resets. Returns None when quota
    is currently available.

    Reads the key's own counter (GET /key costs no request) rather than probing
    with a chat call: a probe tied to one model misreads that model being
    withdrawn from the free tier as "quota spent", which is how the first sweep
    slept for two days on an unused allowance.

    The window is midnight UTC, not local midnight, which is why "run it
    tomorrow" is the wrong instruction: the reset can land mid-afternoon local.
    """
    try:
        free = _openrouter_get("key")["data"]["free_model_daily_requests"]
    except Exception:  # noqa: BLE001
        return None
    if free.get("remaining", 0) > 0:
        return None
    now = datetime.datetime.now(datetime.timezone.utc)
    midnight = (now + datetime.timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
    return midnight.astimezone().replace(tzinfo=None)


def withdrawn_models() -> set[str]:
    """Declared models OpenRouter no longer lists. Their runs cannot be made at
    zero cost; they are reported as withdrawn, never substituted silently."""
    try:
        live = {m["id"] for m in _openrouter_get("models")["data"]}
    except Exception:  # noqa: BLE001
        return set()
    return {m for m in MODELS if m not in live}


def completed() -> set[str]:
    """Keys of runs that already have a scored firm under the CURRENT prompt."""
    from baselines.prompts import PROMPT_VERSION

    if not RESULTS.exists():
        return set()
    doc = json.loads(RESULTS.read_text())
    if doc.get("prompt_version") != PROMPT_VERSION:
        return set()
    return {k for k, v in doc.get("runs", {}).items() if v.get("per_firm")}


def queue(skip: set[str] = frozenset()) -> list[tuple[str, str]]:
    done = completed()
    return [
        (m, v)
        for m in MODELS
        for v in VARIANTS
        if f"{m}::{v}" not in done and m not in skip
    ]


def run_one(model: str, variant: str, subset: int) -> str:
    """Returns 'done', 'quota', 'incomplete', or 'error'."""
    cmd = [
        sys.executable, "-u", str(ROOT / "scripts" / "run_free.py"),
        "--provider", "openrouter", "--model", model,
        "--firms", "0", "--variant", variant,
        "--batch", str(BATCH), "--subset", str(subset), "--rpd", "50",
    ]
    # Stream the child's output as it arrives: per-batch progress and every
    # retry must be visible while a run is in flight, not only after it ends.
    proc = subprocess.Popen(cmd, cwd=ROOT, stdout=subprocess.PIPE,
                            stderr=subprocess.STDOUT, text=True, bufsize=1)
    lines = []
    for line in proc.stdout:
        lines.append(line)
        print(f"    {line.rstrip()}", flush=True)
    proc.wait()
    out = "".join(lines)
    if "daily quota exhausted" in out:
        return "quota"
    if "INCOMPLETE" in out:
        return "incomplete"
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

    gone = withdrawn_models()
    q = queue(gone)
    done = completed()
    total = (len(MODELS) - len(gone)) * len(VARIANTS)
    for m in sorted(gone):
        print(f"withdrawn from the free tier, not run: {m}")

    print(f"study: {len(MODELS)} models x {len(VARIANTS)} conditions = {total} runs")
    print(f"subset: {args.subset} pairs -> ~{-(-args.subset // BATCH)} calls each")
    print(f"done: {len(done)}/{total}   remaining: {len(q)}")
    print(f"at 50 calls/day: ~{-(-len(q) * (-(-args.subset // BATCH)) // 50)} more day(s)\n")

    if args.plan:
        for m, v in q:
            print(f"  pending  {m.split('/')[-1]:<34} {v}")
        return 0

    # Runs whose upstream failed this quota day. They are retried after the next
    # reset, not immediately: a failing host would otherwise take the whole
    # day's allowance with it.
    deferred: set[tuple[str, str]] = set()
    while True:
        q = queue(gone)
        if not q:
            break
        if args.wait and all(r in deferred for r in q):
            now = datetime.datetime.now(datetime.timezone.utc)
            nxt = (now + datetime.timedelta(days=1)).replace(hour=0, minute=5, second=0, microsecond=0)
            wait_s = (nxt - now).total_seconds()
            print(f"  every remaining run is deferred; retrying after the reset "
                  f"({wait_s / 3600:.1f}h). Sleeping.", flush=True)
            time.sleep(wait_s)
            deferred.clear()
            continue
        q = [r for r in q if r not in deferred]

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
            if outcome == "incomplete":
                deferred.add((model, variant))
                print("    upstream failing; deferred to after the next reset")
            if outcome == "error":
                print("    skipping to next run")
        if stop and not args.wait:
            break
        if not args.wait:
            break

    remaining = len(queue(gone))
    print(f"\nremaining after this session: {remaining}/{total}")
    if remaining == 0:
        print("study complete. Next: scripts/fill_results.py, scripts/make_figure.py")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
