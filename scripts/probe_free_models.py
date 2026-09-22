"""Which OpenRouter free models can actually run this benchmark?

Screens the public catalogue against the task's hard requirements, with no API
key needed. A model that fails the context requirement cannot run the benchmark
at all; the rest have to be tested live (see --live) because a catalogue entry
says nothing about whether a model will hold a tabular output format.

    python3 scripts/probe_free_models.py                 # catalogue screen only
    python3 scripts/probe_free_models.py --live          # + one real call each
"""

from __future__ import annotations

import argparse
import json
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

CATALOGUE = "https://openrouter.ai/api/v1/models"

# The largest single call the benchmark issues, measured by estimate_cost at
# batch 20 with scoped sources. A model whose context is below this cannot be
# evaluated, full stop.
REQUIRED_CONTEXT = 9750
# Plus room for the reply: 20 pair lines at ~30 tokens.
REQUIRED_TOTAL = REQUIRED_CONTEXT + 20 * 30


def fetch(url: str, key: str | None = None, data: bytes | None = None) -> dict:
    headers = {"Content-Type": "application/json"}
    if key:
        headers["Authorization"] = f"Bearer {key}"
    req = urllib.request.Request(url, data=data, headers=headers)
    with urllib.request.urlopen(req, timeout=120) as r:
        return json.loads(r.read())


# Free models that are free but wrong for THIS task. Excluded by type with a
# stated reason, so the model set in the paper is a documented decision rather
# than whatever the catalogue happened to return.
EXCLUDE_BY_TYPE = {
    "google/lyria-3-clip-preview": "music generation, not a chat model",
    "google/lyria-3-pro-preview": "music generation, not a chat model",
    "nvidia/nemotron-3.5-content-safety:free": "safety classifier, not general chat",
    "inclusionai/ling-3.0-flash-sante:free": "medical-domain specialist",
    "inclusionai/ling-3.0-flash-fin:free": "finance-domain specialist",
    "inclusionai/ling-3.0-flash-vl:free": "vision-language specialist",
    "cohere/north-mini-code:free": "code-completion specialist",
    "openrouter/free": "router alias, not a fixed model - unreportable",
    "liquid/lfm-2.5-2.6b:free": "2.6B parameters, far below task scale",
}


def screen() -> list[dict]:
    models = fetch(CATALOGUE)["data"]
    free = []
    for m in models:
        p = m.get("pricing", {})
        try:
            is_free = float(p.get("prompt") or 0) == 0 and float(p.get("completion") or 0) == 0
        except (TypeError, ValueError):
            is_free = False
        if not is_free:
            continue
        ctx = m.get("context_length") or 0
        arch = m.get("architecture", {}) or {}
        params = m.get("supported_parameters") or []
        free.append({
            "id": m["id"],
            "name": m.get("name", ""),
            "context": ctx,
            "modality": arch.get("input_modalities") or arch.get("modality"),
            "tools": "tools" in params,
            "structured": "structured_outputs" in params or "response_format" in params,
            "fits_context": ctx >= REQUIRED_TOTAL,
            "excluded_reason": EXCLUDE_BY_TYPE.get(m["id"]),
        })
    return sorted(free, key=lambda x: (-x["context"], x["id"]))


LIVE_SYSTEM = (
    "Return one line per pair, exactly: <pair_id><TAB><verdict><TAB><field_or_dash>\n"
    "Permitted verdicts: pass, fail, needs_evidence, unmonitored.\n"
    "Return a line for every pair. No commentary, no headers."
)
LIVE_USER = """## Source data exports

### i9_record_export
```csv
employeeNumber,startDate,section2CompletedDate
SYN-1001,2025-02-03,2025-02-13
SYN-1002,2025-03-06,
```

## Obligations

- i9.section2.timeliness
    check: Section 2 completed within 3 business days of the start date.
    requires: startDate, section2CompletedDate

## Pairs to evaluate (2)

i9.section2.timeliness::SYN-1001\t[worker: SYN-1001]
i9.section2.timeliness::SYN-1002\t[worker: SYN-1002]"""


def live_test(model_id: str, key: str) -> dict:
    """One real call. Checks the model responds, holds the format, and gets an
    easy case right: 1001 is 8 business days late (fail), 1002 has no date at
    all (needs_evidence, NOT pass)."""
    body = json.dumps({
        "model": model_id,
        "temperature": 0,
        # Several free models emit a reasoning trace before the answer. A tight
        # cap truncates them mid-thought and would score a capable model as
        # unparseable, so give enough room for the trace plus the reply.
        "max_tokens": 4000,
        "messages": [
            {"role": "system", "content": LIVE_SYSTEM},
            {"role": "user", "content": LIVE_USER},
        ],
    }).encode()
    try:
        r = fetch("https://openrouter.ai/api/v1/chat/completions", key, body)
    except Exception as e:  # noqa: BLE001 - report, never crash the sweep
        return {"ok": False, "error": str(e)[:160]}

    # OpenRouter returns upstream failures as HTTP 200 with an `error` object.
    # Reporting these as an empty reply would misattribute a provider outage to
    # the model, so surface them explicitly.
    if isinstance(r.get("error"), dict):
        err = r["error"]
        return {
            "ok": False,
            "error": f"{err.get('code')}: {str(err.get('message'))[:120]}",
            "error_type": (err.get("metadata") or {}).get("error_type"),
        }

    txt = ((r.get("choices") or [{}])[0].get("message") or {}).get("content") or ""
    if not txt.strip():
        return {"ok": False, "error": "empty completion", "error_type": "empty"}
    low = txt.lower()

    def verdict_for(emp: str) -> str | None:
        for line in low.splitlines():
            if emp.lower() in line:
                for v in ("needs_evidence", "unmonitored", "fail", "pass"):
                    if v in line:
                        return v
        return None

    v1, v2 = verdict_for("SYN-1001"), verdict_for("SYN-1002")
    return {
        "ok": True,
        "parseable": v1 is not None and v2 is not None,
        "late_case_correct": v1 == "fail",
        "missing_case_correct": v2 == "needs_evidence",
        "false_green": v2 == "pass",
        "raw": txt[:200].replace("\n", " | "),
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--live", action="store_true", help="also make one real call per model")
    ap.add_argument("--out", default=str(ROOT / "docs" / "free_model_screen.json"))
    args = ap.parse_args()

    free = screen()
    usable = [m for m in free if m["fits_context"] and not m["excluded_reason"]]

    print(f"free models on OpenRouter: {len(free)}")
    print(f"benchmark needs >= {REQUIRED_TOTAL:,} tokens of context "
          f"(largest call {REQUIRED_CONTEXT:,} + reply)\n")
    print(f"{'model id':<46}{'context':>10}{'fits':>6}{'tools':>7}{'struct':>8}")
    print("-" * 77)
    for m in free:
        print(f"{m['id']:<46}{m['context']:>10,}{'yes' if m['fits_context'] else 'NO':>6}"
              f"{'y' if m['tools'] else '-':>7}{'y' if m['structured'] else '-':>8}")

    print(f"\ncandidates: {len(usable)}/{len(free)}")
    too_small = [m for m in free if not m["fits_context"]]
    if too_small:
        print(f"excluded for context: {', '.join(m['id'] for m in too_small)}")
    by_type = [m for m in free if m["excluded_reason"]]
    if by_type:
        print(f"\nexcluded by type ({len(by_type)}):")
        for m in by_type:
            print(f"  {m['id']:<50}{m['excluded_reason']}")

    doc = {
        "required_context_tokens": REQUIRED_TOTAL,
        "n_free": len(free),
        "n_candidates": len(usable),
        "candidates": [m["id"] for m in usable],
        "models": free,
    }

    if args.live:
        from nofalsegreen.credentials import load_checked_key, redact
        key = load_checked_key("openrouter", required=False)
        if not key:
            print("\n[live] no openrouter key found; see nofalsegreen/credentials.py")
        else:
            print(f"\nkey: {redact(key)}")
            print("\nlive format + easy-case test (2 pairs each):")
            print(f"{'model id':<46}{'resp':>6}{'parse':>7}{'late':>6}{'missing':>9}{'FG':>4}")
            print("-" * 78)
            for m in usable:
                res = live_test(m["id"], key)
                m["live"] = res
                if not res["ok"]:
                    print(f"{m['id']:<46}{'ERR':>6}   {res['error'][:40]}")
                    continue
                print(f"{m['id']:<46}{'y':>6}"
                      f"{'y' if res['parseable'] else 'n':>7}"
                      f"{'y' if res['late_case_correct'] else 'n':>6}"
                      f"{'y' if res['missing_case_correct'] else 'n':>9}"
                      f"{'!' if res['false_green'] else '-':>4}")
            good = [m for m in usable if m.get("live", {}).get("parseable")]
            print(f"\nresponded and parseable: {len(good)}/{len(usable)}")
            fg = [m for m in usable if m.get("live", {}).get("false_green")]
            if fg:
                print(f"reported the missing-date case as PASS (a false green): "
                      f"{', '.join(m['id'] for m in fg)}")

    Path(args.out).write_text(json.dumps(doc, indent=2))
    print(f"\nwrote {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
