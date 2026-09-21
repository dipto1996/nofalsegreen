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


# Quotas as published in vendor docs, September 2026. Verify before a run; the
# value actually used is recorded in the results file.
FREE_QUOTAS = {
    "gemini-2.5-flash": Quota(rpm=10, rpd=250, tpm=250_000, label="gemini-2.5-flash free"),
    "gemini-2.5-flash-lite": Quota(rpm=15, rpd=1_000, tpm=250_000, label="gemini-2.5-flash-lite free"),
    "llama-3.3-70b-versatile": Quota(rpm=30, rpd=1_000, tpm=12_000, label="groq llama-3.3-70b free"),
    "openai/gpt-oss-120b": Quota(rpm=30, rpd=1_000, tpm=8_000, label="groq gpt-oss-120b free"),
}

FREE_PROVIDERS = {"gemini": GeminiFreeProvider, "groq": GroqFreeProvider}


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
