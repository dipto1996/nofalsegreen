"""Tests for the free-tier runner: rate limiting, quota handling, resume, and
source scoping. All offline — no API key and no network.

Run: python3 tests/test_freetier.py
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from baselines.freetier import Checkpoint, DailyQuotaExhausted, Quota, RateLimiter  # noqa: E402
from baselines.llm import MockProvider, Usage, estimate_cost, run_firm  # noqa: E402
from baselines.prompts import (  # noqa: E402
    ABSTAIN_OFFERED,
    REGIME_SOURCES,
    sources_for_regimes,
    user_prompt,
)
from nofalsegreen import northwind  # noqa: E402
from nofalsegreen.metrics import score  # noqa: E402
from nofalsegreen.rulebook import Rulebook  # noqa: E402
from nofalsegreen.schema import Verdict  # noqa: E402

ANCHOR = ROOT / "data" / "firms" / "northwind-robotics"
SCRATCH = ROOT / ".test-tmp"

passed = failed = 0


def check(cond: bool, label: str) -> None:
    global passed, failed
    if cond:
        print(f"  ok   {label}")
        passed += 1
    else:
        print(f"  FAIL {label}")
        failed += 1


rb = Rulebook.load(ROOT / "rulebook" / "rulebook.json")
firm = northwind.load(ANCHOR, ANCHOR / "expectations.json")
truth = firm.label_index()

# ── rate limiter ────────────────────────────────────────────────────────────
print("rate limiter")
rl = RateLimiter(Quota(rpm=1000, rpd=3, label="test"))
rl.acquire(); rl.acquire(); rl.acquire()
check(rl.used_today == 3, "counts requests against the daily quota")
try:
    rl.acquire()
    check(False, "raises DailyQuotaExhausted at the daily ceiling")
except DailyQuotaExhausted:
    check(True, "raises DailyQuotaExhausted at the daily ceiling")

rl2 = RateLimiter(Quota(rpm=2, rpd=100, label="test"))
t0 = time.time()
rl2.acquire(); rl2.acquire()
check(time.time() - t0 < 1.0, "does not sleep while under the per-minute limit")
check(len(rl2._recent) == 2, "tracks the sliding window")

# Third call at rpm=2 must wait. Simulate by ageing the window instead of
# sleeping 60s, so the test stays fast.
rl2._recent[0] = time.time() - 61
rl2._recent[1] = time.time() - 61
t0 = time.time()
rl2.acquire()
check(time.time() - t0 < 1.0, "expired window entries are evicted rather than waited on")

# ── checkpoint / resume ─────────────────────────────────────────────────────
print("\ncheckpoint and resume")
cp_path = SCRATCH / "ckpt.json"
if cp_path.exists():
    cp_path.unlink()
cp = Checkpoint(cp_path)
check(cp.load()["completed"] == [], "fresh checkpoint is empty")
check(not cp.done("m", "v", "f1"), "nothing is done in a fresh checkpoint")
cp.mark("m", "v", "f1", Usage(input_tokens=100, output_tokens=20, calls=3))
check(cp.done("m", "v", "f1"), "a marked run is recorded done")
check(not cp.done("m", "v", "f2"), "a different firm is still pending")
check(not cp.done("m", "other", "f1"), "the same firm under another variant is pending")
cp.mark("m", "v", "f2", Usage(input_tokens=50, output_tokens=10, calls=2))
u = cp.load()["usage"]["m"]
check(u["calls"] == 5 and u["input_tokens"] == 150, "usage accumulates across runs")
cp2 = Checkpoint(cp_path)
check(cp2.done("m", "v", "f1"), "checkpoint survives being reloaded from disk")

# ── source scoping ──────────────────────────────────────────────────────────
print("\nsource scoping")
i9 = sources_for_regimes(firm, {"i9-everify"})
check("i9_record_export" in i9, "i9 regime gets the I-9 export")
check("hris_roster_export" in i9, "roster is always included (the canonical anchor)")
check("perm_recruitment_export" not in i9, "i9 regime does not get the PERM tracker")
check("payroll_register" not in i9, "i9 regime does not get payroll")

wage = sources_for_regimes(firm, {"wage-prevailing"})
check("payroll_register" in wage, "wage regime gets payroll")
check("lca_export" in wage, "wage regime gets LCAs")

allsrc = sources_for_regimes(firm, {"unknown-regime"})
check(len(allsrc) == len(firm.sources),
      "an unclassified regime falls back to ALL sources (never hides data)")
check(sources_for_regimes(firm, set()) == sorted(firm.sources),
      "empty regime set also falls back to all sources")
check(all("hris_roster_export" in v for v in REGIME_SOURCES.values()),
      "every regime mapping includes the roster")

i9_pairs = [p.pair_id for p in firm.pairs if p.pair_id.startswith("i9.")][:5]
if i9_pairs:
    scoped = user_prompt(firm, rb.all_rules(), i9_pairs, scope_sources=True)
    full = user_prompt(firm, rb.all_rules(), i9_pairs, scope_sources=False)
    check(len(scoped) < len(full), "scoped prompt is smaller than the full one")
    check("Not shown:" in scoped, "scoped prompt discloses which exports are withheld")
    check("do not infer that an absent field exists" in " ".join(scoped.split()),
          "scoped prompt forbids inferring data from an unseen export")
    check("perm_recruitment_export" in scoped.split("## Obligations")[0]
          or "Not shown" in scoped, "withheld exports are named, not silently dropped")

# ── scoping does not change the label set or the scoring path ───────────────
print("\nscoping does not distort measurement")
careful = MockProvider(lambda pid: truth[pid].verdict.value, "mock-careful")
r_scoped = run_firm(careful, firm, rb.all_rules(), batch_size=20, scope_sources=True)
r_full = run_firm(careful, firm, rb.all_rules(), batch_size=20, scope_sources=False)
check(r_scoped.n_parsed == r_full.n_parsed == 221,
      "both modes evaluate all 221 pairs")
s_scoped = score(firm.labels, r_scoped.predictions)
s_full = score(firm.labels, r_full.predictions)
check(s_scoped.false_green_rate == s_full.false_green_rate == 0.0,
      "a careful model scores identically under both modes")
check(s_scoped.violation_recall == s_full.violation_recall == 1.0,
      "recall is unaffected by source scoping")

guesser = MockProvider(
    lambda pid: "fail" if truth[pid].verdict is Verdict.FAIL else "pass", "mock-guesser"
)
s_g = score(firm.labels, run_firm(guesser, firm, rb.all_rules(), batch_size=20,
                                  scope_sources=True).predictions)
check(s_g.false_green_rate == 1.0,
      "the pass-guesser is still caught at FGR 1.000 with scoping on")

# ── feasibility figures the plan depends on ─────────────────────────────────
print("\nfeasibility")
e = estimate_cost(firm, rb.all_rules(), batch_size=20, scope_sources=True)
check(e["n_batches"] == 12, f"anchor firm is 12 calls at batch 20 (got {e['n_batches']})")
check(e["max_call_tokens"] < 250_000,
      f"largest call fits Gemini's 250k tpm (got {e['max_call_tokens']:,})")
check(e["scope_sources"] is True, "estimate records whether scoping was used")
check(e["max_call_tokens"] > 0, "estimate reports the largest single call")

e_un = estimate_cost(firm, rb.all_rules(), batch_size=20, scope_sources=False)
check(e["max_call_tokens"] < e_un["max_call_tokens"],
      "scoping reduces the largest single call")

print("\nupstream 429s wait patiently and are not charged as attempts")
import io as _io  # noqa: E402
import json as _json  # noqa: E402
import urllib.error as _ue  # noqa: E402
import urllib.request as _ur  # noqa: E402

import baselines.freetier as _ft  # noqa: E402


def _http429(msg):
    body = _json.dumps({"error": {"code": 429, "message": msg}}).encode()
    return _ue.HTTPError("u", 429, "Too Many Requests", {}, _io.BytesIO(body))


class _Resp(_io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


_script = []


def _fake_urlopen(req, timeout=None):
    nxt = _script.pop(0)
    if isinstance(nxt, Exception):
        raise nxt
    return _Resp(_json.dumps(nxt).encode())


_ok = {"choices": [{"message": {"content": "a::b\tpass\t-"}, "finish_reason": "stop"}],
       "usage": {"prompt_tokens": 10, "completion_tokens": 5}}
_orig = (_ur.urlopen, _ft.time.sleep, _ft.load_checked_key if hasattr(_ft, "load_checked_key") else None)
_ur.urlopen, _ft.time.sleep = _fake_urlopen, (lambda s: None)
import nofalsegreen.credentials as _cred  # noqa: E402
_ck = _cred.load_checked_key
_cred.load_checked_key = lambda *a, **k: "test-key"
try:
    _prov = _ft.OpenRouterFreeProvider("m:free", Quota(rpm=1000, rpd=50), max_retries=2)
    _script[:] = [_http429("m:free is temporarily rate-limited upstream") for _ in range(6)] + [_ok]
    _txt, _u = _prov.complete("s", "u", 100)
    check(_txt.startswith("a::b") and _prov.limiter.used_today == 1,
          "six upstream 429s then success: one request charged, max_retries=2 not consumed")
    check(_u.finish_reason == "stop", "finish_reason is carried through")

    _prov = _ft.OpenRouterFreeProvider("m:free", Quota(rpm=1000, rpd=50), max_retries=2)
    _script[:] = [_http429("Rate limit exceeded: free-models-per-day")]
    try:
        _prov.complete("s", "u", 100)
        check(False, "daily 429 raises DailyQuotaExhausted")
    except DailyQuotaExhausted:
        check(True, "daily 429 still raises DailyQuotaExhausted immediately")

    _prov = _ft.OpenRouterFreeProvider("m:free", Quota(rpm=1000, rpd=50), max_retries=2,
                                       upstream_wait_s=0)
    _script[:] = [_http429("temporarily rate-limited upstream") for _ in range(2)]
    try:
        _prov.complete("s", "u", 100)
        check(False, "upstream wait is bounded")
    except RuntimeError:
        check(True, "once the upstream wait budget is spent, 429s count as attempts again")
finally:
    _ur.urlopen, _ft.time.sleep = _orig[0], _orig[1]
    _cred.load_checked_key = _ck

print(f"\n{'PASS' if failed == 0 else 'FAIL'} — {passed} ok, {failed} failed")
sys.exit(1 if failed else 0)
