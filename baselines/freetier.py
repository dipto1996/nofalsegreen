"""Free-tier providers: rate limiting, backoff, and resume.

Free API tiers enforce several quotas at once (requests per minute, requests
per day, tokens per minute) and the first ceiling reached returns HTTP 429. A
sweep large enough to be worth reporting therefore spans multiple days, so the
runner must:

  1. pace itself under the per-minute request limit rather than discovering it,
  2. back off and retry on a 429 that is transient (per-minute),
  3. stop cleanly on a 429 that is not (per-day), leaving completed work intact,
  4. resume from a checkpoint so the next day continues where it left off.

Quotas move. They are passed in rather than hard-coded, and whatever is used is
recorded alongside results.
"""

from __future__ import annotations

import json
import os
import sys
import time
import urllib.error
import urllib.request
from collections import deque
from dataclasses import dataclass, field
from pathlib import Path

from .llm import Usage


class DailyQuotaExhausted(RuntimeError):
    """Raised when the per-day ceiling is hit. Not an error: stop and resume tomorrow."""


@dataclass
class Quota:
    rpm: int
    rpd: int
    tpm: int | None = None
    label: str = ""

    def as_dict(self) -> dict:
        return {"rpm": self.rpm, "rpd": self.rpd, "tpm": self.tpm, "label": self.label}


@dataclass
class RateLimiter:
    """Sliding-window pacer for requests per minute, plus a hard daily counter."""

    quota: Quota
    used_today: int = 0
    _recent: deque[float] = field(default_factory=deque)

    def acquire(self) -> None:
        if self.used_today >= self.quota.rpd:
            raise DailyQuotaExhausted(
                f"{self.quota.label or 'provider'}: {self.used_today}/{self.quota.rpd} "
                "requests used today"
            )
        now = time.time()
        while self._recent and now - self._recent[0] > 60.0:
            self._recent.popleft()
        if len(self._recent) >= self.quota.rpm:
            sleep_for = 60.0 - (now - self._recent[0]) + 0.5
            if sleep_for > 0:
                time.sleep(sleep_for)
            now = time.time()
            while self._recent and now - self._recent[0] > 60.0:
                self._recent.popleft()
        self._recent.append(time.time())
        self.used_today += 1


class GeminiFreeProvider:
    """Google Gemini via the REST endpoint, using only the standard library.

    No SDK dependency, so the benchmark stays installable with nothing but
    Python. Reads GEMINI_API_KEY or GOOGLE_API_KEY.
    """

    ENDPOINT = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"

    def __init__(self, model: str, quota: Quota, *, max_retries: int = 5):
        key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
        if not key:
            raise SystemExit("set GEMINI_API_KEY (or GOOGLE_API_KEY) to run this provider")
        self.name = model
        self._key = key
        self.limiter = RateLimiter(quota)
        self.max_retries = max_retries

    def complete(self, system: str, user: str, max_tokens: int) -> tuple[str, Usage]:
        body = json.dumps({
            "systemInstruction": {"parts": [{"text": system}]},
            "contents": [{"role": "user", "parts": [{"text": user}]}],
            "generationConfig": {"temperature": 0, "maxOutputTokens": max_tokens},
        }).encode()

        delay = 5.0
        last_err: Exception | None = None
        for attempt in range(self.max_retries):
            self.limiter.acquire()
            t0 = time.time()
            req = urllib.request.Request(
                self.ENDPOINT.format(model=self.name),
                data=body,
                headers={"Content-Type": "application/json", "x-goog-api-key": self._key},
            )
            try:
                with urllib.request.urlopen(req, timeout=240) as resp:
                    payload = json.loads(resp.read())
                break
            except urllib.error.HTTPError as e:
                detail = e.read().decode("utf-8", "replace")[:400]
                last_err = RuntimeError(f"HTTP {e.code}: {detail}")
                if e.code == 429:
                    # Per-day exhaustion is terminal for this session; the
                    # message distinguishes it from a per-minute burst.
                    if "per day" in detail.lower() or "quota_limit_value" in detail.lower():
                        raise DailyQuotaExhausted(detail) from e
                    time.sleep(delay)
                    delay = min(delay * 2, 120.0)
                    continue
                if 500 <= e.code < 600:
                    time.sleep(delay)
                    delay = min(delay * 2, 120.0)
                    continue
                raise last_err from e
            except (urllib.error.URLError, TimeoutError) as e:
                last_err = e
                time.sleep(delay)
                delay = min(delay * 2, 120.0)
                continue
        else:
            raise RuntimeError(f"{self.name}: giving up after {self.max_retries} attempts: {last_err}")

        cands = payload.get("candidates") or []
        text = ""
        if cands:
            for part in cands[0].get("content", {}).get("parts", []):
                text += part.get("text", "")
        um = payload.get("usageMetadata", {})
        return text, Usage(
            input_tokens=um.get("promptTokenCount", 0),
            output_tokens=um.get("candidatesTokenCount", 0),
            calls=1,
            seconds=time.time() - t0,
        )


class GroqFreeProvider:
    """Groq via its OpenAI-compatible REST endpoint. Standard library only."""

    ENDPOINT = "https://api.groq.com/openai/v1/chat/completions"

    def __init__(self, model: str, quota: Quota, *, max_retries: int = 5):
        key = os.environ.get("GROQ_API_KEY")
        if not key:
            raise SystemExit("set GROQ_API_KEY to run this provider")
        self.name = model
        self._key = key
        self.limiter = RateLimiter(quota)
        self.max_retries = max_retries

    def complete(self, system: str, user: str, max_tokens: int) -> tuple[str, Usage]:
        body = json.dumps({
            "model": self.name,
            "temperature": 0,
            "max_tokens": max_tokens,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        }).encode()

        delay = 5.0
        last_err: Exception | None = None
        for _ in range(self.max_retries):
            self.limiter.acquire()
            t0 = time.time()
            req = urllib.request.Request(
                self.ENDPOINT,
                data=body,
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {self._key}",
                },
            )
            try:
                with urllib.request.urlopen(req, timeout=240) as resp:
                    payload = json.loads(resp.read())
                break
            except urllib.error.HTTPError as e:
                detail = e.read().decode("utf-8", "replace")[:400]
                last_err = RuntimeError(f"HTTP {e.code}: {detail}")
                if e.code == 429:
                    if "per day" in detail.lower() or "requests per day" in detail.lower():
                        raise DailyQuotaExhausted(detail) from e
                    time.sleep(delay)
                    delay = min(delay * 2, 120.0)
                    continue
                if 500 <= e.code < 600:
                    time.sleep(delay)
                    delay = min(delay * 2, 120.0)
                    continue
                raise last_err from e
            except (urllib.error.URLError, TimeoutError) as e:
                last_err = e
                time.sleep(delay)
                delay = min(delay * 2, 120.0)
                continue
        else:
            raise RuntimeError(f"{self.name}: giving up after {self.max_retries} attempts: {last_err}")

        ch = (payload.get("choices") or [{}])[0]
        text = (ch.get("message") or {}).get("content") or ""
        u = payload.get("usage", {})
        return text, Usage(
            input_tokens=u.get("prompt_tokens", 0),
            output_tokens=u.get("completion_tokens", 0),
            calls=1,
            seconds=time.time() - t0,
        )


def _log_retry(model: str, err: Exception, t0: float) -> None:
    """Every failed attempt costs a request from the daily allowance, so each is
    logged; a silent retry loop can spend a day's quota with nothing to show."""
    print(f"      retry {model}: {type(err).__name__}: {str(err)[:160]} "
          f"after {time.time() - t0:.0f}s", file=sys.stderr, flush=True)


class OpenRouterFreeProvider:
    """OpenRouter free-tier models via its OpenAI-compatible endpoint.

    One key reaches many models, which is what makes a multi-model ablation
    feasible with no budget. Standard library only.

    Free-tier reality, measured 2026-09-21: of 15 free chat models meeting the
    context requirement, 6 returned a usable answer. The rest rate-limited,
    refused, or returned empty. `complete` therefore distinguishes a transient
    per-minute 429 (retry) from a daily ceiling (stop and resume tomorrow), and
    treats an upstream provider failure as a provider fault rather than a model
    answer.
    """

    ENDPOINT = "https://openrouter.ai/api/v1/chat/completions"

    def __init__(self, model: str, quota: Quota, *, max_retries: int = 4,
                 upstream_wait_s: float = 1800.0):
        from nofalsegreen.credentials import load_checked_key

        self.name = model
        self.upstream_wait_s = upstream_wait_s
        self._key = load_checked_key("openrouter")
        self.limiter = RateLimiter(quota)
        self.max_retries = max_retries

    def complete(self, system: str, user: str, max_tokens: int) -> tuple[str, Usage]:
        body = json.dumps({
            "model": self.name,
            "temperature": 0,
            "max_tokens": max_tokens,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        }).encode()

        delay = 8.0
        last_err: Exception | None = None
        # An upstream 429 ("temporarily rate-limited upstream") is the shared
        # free pool being saturated. Measured 2026-09-30: these are not charged
        # against the daily allowance, so they get a patient wait of their own
        # instead of consuming one of max_retries.
        upstream_deadline = time.time() + self.upstream_wait_s
        upstream_delay = 30.0
        attempts = 0
        while attempts < self.max_retries:
            attempts += 1
            self.limiter.acquire()
            t0 = time.time()
            req = urllib.request.Request(
                self.ENDPOINT,
                data=body,
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {self._key}",
                    "X-Title": "No False Green benchmark",
                },
            )
            try:
                with urllib.request.urlopen(req, timeout=300) as resp:
                    payload = json.loads(resp.read())
            except urllib.error.HTTPError as e:
                detail = e.read().decode("utf-8", "replace")[:400]
                last_err = RuntimeError(f"HTTP {e.code}: {detail}")
                _log_retry(self.name, last_err, t0)
                if e.code == 429:
                    if any(t in detail.lower() for t in ("per day", "per-day", "daily")):
                        raise DailyQuotaExhausted(detail) from e
                    if "upstream" in detail.lower() and time.time() < upstream_deadline:
                        attempts -= 1
                        self.limiter.used_today -= 1
                        time.sleep(upstream_delay)
                        upstream_delay = min(upstream_delay * 2, 300.0)
                        continue
                    time.sleep(delay)
                    delay = min(delay * 2, 120.0)
                    continue
                if e.code == 404 or 500 <= e.code < 600:
                    time.sleep(delay)
                    delay = min(delay * 2, 120.0)
                    continue
                raise last_err from e
            except (urllib.error.URLError, TimeoutError) as e:
                last_err = e
                _log_retry(self.name, e, t0)
                time.sleep(delay)
                delay = min(delay * 2, 120.0)
                continue

            # OpenRouter reports upstream failures as HTTP 200 + an error body.
            # Treating that as an empty model reply would blame the model for a
            # provider outage.
            if isinstance(payload.get("error"), dict):
                err = payload["error"]
                code = err.get("code")
                msg = str(err.get("message"))[:200]
                if code == 429:
                    raise DailyQuotaExhausted(msg)
                last_err = RuntimeError(f"upstream {code}: {msg}")
                _log_retry(self.name, last_err, t0)
                # 404 here is the upstream shedding load, not a missing model:
                # observed on an id that answered minutes before and after.
                # Treat it as transient, like a 5xx.
                if code in (404, 500, 502, 503, 504):
                    time.sleep(delay)
                    delay = min(delay * 2, 120.0)
                    continue
                raise last_err

            ch = (payload.get("choices") or [{}])[0]
            text = (ch.get("message") or {}).get("content") or ""
            u = payload.get("usage", {}) or {}
            return text, Usage(
                input_tokens=u.get("prompt_tokens", 0),
                output_tokens=u.get("completion_tokens", 0),
                calls=1,
                seconds=time.time() - t0,
                finish_reason=ch.get("finish_reason") or "",
            )

        raise RuntimeError(f"{self.name}: gave up after {self.max_retries} attempts: {last_err}")


class VertexProvider:
    """Google models through Vertex AI (generateContent), paid from cloud credits.

    `model` is "vertex/<publisher model id>#r<k>": the #r<k> suffix marks a
    repeat, so each repeat has its own cache keys and results entry while the
    request sent is identical. Auth is the gcloud user's access token,
    refreshed before it expires; no key file is involved.
    """

    def __init__(self, model: str, quota: Quota, *, max_retries: int = 6):
        from nofalsegreen.vertex_block import LOCATION, PROJECT

        self.name = model
        base = model.split("/", 1)[-1]
        self.model_id = base.split("#", 1)[0]
        self.project, self.location = PROJECT, LOCATION
        self.limiter = RateLimiter(quota)
        self.max_retries = max_retries
        self._token, self._token_at = "", 0.0

    def _auth(self) -> str:
        import subprocess
        if not self._token or time.time() - self._token_at > 45 * 60:
            self._token = subprocess.run(["gcloud", "auth", "print-access-token"],
                                         capture_output=True, text=True, check=True).stdout.strip()
            self._token_at = time.time()
        return self._token

    def complete(self, system: str, user: str, max_tokens: int) -> tuple[str, Usage]:
        host = ("aiplatform.googleapis.com" if self.location == "global"
                else f"{self.location}-aiplatform.googleapis.com")
        url = (f"https://{host}/v1/projects/{self.project}/locations/{self.location}"
               f"/publishers/google/models/{self.model_id}:generateContent")
        body = json.dumps({
            "systemInstruction": {"parts": [{"text": system}]},
            "contents": [{"role": "user", "parts": [{"text": user}]}],
            "generationConfig": {"temperature": 0, "maxOutputTokens": max_tokens},
        }).encode()
        delay, last_err = 10.0, None
        for _ in range(self.max_retries):
            self.limiter.acquire()
            t0 = time.time()
            req = urllib.request.Request(url, data=body, headers={
                "Content-Type": "application/json", "Authorization": f"Bearer {self._auth()}",
                "x-goog-user-project": self.project})
            try:
                with urllib.request.urlopen(req, timeout=900) as resp:
                    payload = json.loads(resp.read())
            except urllib.error.HTTPError as e:
                detail = e.read().decode("utf-8", "replace")[:300]
                last_err = RuntimeError(f"HTTP {e.code}: {detail}")
                _log_retry(self.name, last_err, t0)
                if e.code == 401:
                    self._token = ""
                if e.code in (401, 429) or e.code >= 500:
                    time.sleep(delay)
                    delay = min(delay * 2, 240.0)
                    continue
                raise last_err from e
            except (urllib.error.URLError, TimeoutError) as e:
                last_err = e
                _log_retry(self.name, e, t0)
                time.sleep(delay)
                delay = min(delay * 2, 240.0)
                continue
            cand = (payload.get("candidates") or [{}])[0]
            text = "".join(p.get("text", "") for p in (cand.get("content") or {}).get("parts", [])
                           if not p.get("thought"))
            fr = (cand.get("finishReason") or "").upper()
            finish = {"STOP": "stop", "MAX_TOKENS": "length"}.get(fr, fr.lower() or "")
            u = payload.get("usageMetadata", {}) or {}
            return text, Usage(
                input_tokens=u.get("promptTokenCount", 0),
                output_tokens=u.get("candidatesTokenCount", 0) + u.get("thoughtsTokenCount", 0),
                calls=1, seconds=time.time() - t0, finish_reason=finish,
            )
        raise RuntimeError(f"{self.name}: gave up after {self.max_retries} attempts: {last_err}")


class VertexOpenProvider(VertexProvider):
    """Open-weights models from other developers, served by Google on Vertex AI
    (Model Garden "model as a service") through its OpenAI-compatible endpoint.
    Billed as Vertex AI usage, so paid from the same cloud credits.

    `model` is "vertexopen/<publisher>/<model>#r<k>". The served location is
    per model (nofalsegreen/study3.py, OPEN_MODELS). A reasoning trace, when
    the model returns one, is counted toward output but never parsed.
    """

    def __init__(self, model: str, quota: Quota, *, max_retries: int = 6):
        from nofalsegreen.study3 import OPEN_MODELS, OUTPUT_LIMITS
        from nofalsegreen.study6 import MODELS as STUDY6_MODELS

        super().__init__(model, quota, max_retries=max_retries)
        self.location = {**STUDY6_MODELS, **OPEN_MODELS}[self.model_id]
        self.output_limit = OUTPUT_LIMITS.get(self.model_id)

    def complete(self, system: str, user: str, max_tokens: int) -> tuple[str, Usage]:
        host = ("aiplatform.googleapis.com" if self.location == "global"
                else f"{self.location}-aiplatform.googleapis.com")
        url = (f"https://{host}/v1/projects/{self.project}/locations/{self.location}"
               f"/endpoints/openapi/chat/completions")
        body = json.dumps({
            "model": self.model_id,
            "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
            "temperature": 0, "max_tokens": min(max_tokens, self.output_limit or max_tokens),
        }).encode()
        delay, last_err = 10.0, None
        for _ in range(self.max_retries):
            self.limiter.acquire()
            t0 = time.time()
            req = urllib.request.Request(url, data=body, headers={
                "Content-Type": "application/json", "Authorization": f"Bearer {self._auth()}",
                "x-goog-user-project": self.project})
            try:
                with urllib.request.urlopen(req, timeout=900) as resp:
                    raw = resp.read()
                payload = json.loads(raw) if raw.strip() else {}
            except urllib.error.HTTPError as e:
                detail = e.read().decode("utf-8", "replace")[:300]
                last_err = RuntimeError(f"HTTP {e.code}: {detail}")
                _log_retry(self.name, last_err, t0)
                if e.code == 401:
                    self._token = ""
                if e.code in (401, 429) or e.code >= 500:
                    time.sleep(delay)
                    delay = min(delay * 2, 240.0)
                    continue
                raise last_err from e
            except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as e:
                last_err = e
                _log_retry(self.name, e, t0)
                time.sleep(delay)
                delay = min(delay * 2, 240.0)
                continue
            if isinstance(payload, list):
                payload = payload[0] if payload else {}
            if "choices" not in payload:
                # An empty or error body is a delivery failure, retried like a 5xx.
                last_err = RuntimeError(f"no choices: {str(payload)[:200]}")
                _log_retry(self.name, last_err, t0)
                time.sleep(delay)
                delay = min(delay * 2, 240.0)
                continue
            ch = payload["choices"][0]
            text = (ch.get("message") or {}).get("content") or ""
            u = payload.get("usage") or {}
            return text, Usage(
                input_tokens=u.get("prompt_tokens", 0), output_tokens=u.get("completion_tokens", 0),
                calls=1, seconds=time.time() - t0, finish_reason=ch.get("finish_reason") or "",
            )
        raise RuntimeError(f"{self.name}: gave up after {self.max_retries} attempts: {last_err}")


# Quotas as published in vendor docs, September 2026. Verify before a run; the
# value actually used is recorded in the results file.
FREE_QUOTAS = {
    "gemini-2.5-flash": Quota(rpm=10, rpd=250, tpm=250_000, label="gemini-2.5-flash free"),
    "gemini-2.5-flash-lite": Quota(rpm=15, rpd=1_000, tpm=250_000, label="gemini-2.5-flash-lite free"),
    "llama-3.3-70b-versatile": Quota(rpm=30, rpd=1_000, tpm=12_000, label="groq llama-3.3-70b free"),
    "openai/gpt-oss-120b": Quota(rpm=30, rpd=1_000, tpm=8_000, label="groq gpt-oss-120b free"),
}

# OpenRouter free tier: 20 requests/minute; 50/day under $10 lifetime credit,
# 1000/day at or above it. Verified against the /api/v1/key endpoint.
OPENROUTER_QUOTA = Quota(rpm=20, rpd=50, tpm=None, label="openrouter free (<$10 credit)")

FREE_PROVIDERS = {
    "gemini": GeminiFreeProvider,
    "groq": GroqFreeProvider,
    "openrouter": OpenRouterFreeProvider,
    "vertex": VertexProvider,
    "vertexopen": VertexOpenProvider,
}


@dataclass
class Checkpoint:
    """Tracks which (model, variant, firm) runs are already done."""

    path: Path

    def load(self) -> dict:
        if self.path.exists():
            return json.loads(self.path.read_text())
        return {"completed": [], "usage": {}}

    def done(self, model: str, variant: str, firm_id: str) -> bool:
        return f"{model}::{variant}::{firm_id}" in set(self.load()["completed"])

    def mark(self, model: str, variant: str, firm_id: str, usage: Usage) -> None:
        doc = self.load()
        key = f"{model}::{variant}::{firm_id}"
        if key not in doc["completed"]:
            doc["completed"].append(key)
        u = doc["usage"].setdefault(model, {"calls": 0, "input_tokens": 0, "output_tokens": 0})
        u["calls"] += usage.calls
        u["input_tokens"] += usage.input_tokens
        u["output_tokens"] += usage.output_tokens
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(doc, indent=2))
