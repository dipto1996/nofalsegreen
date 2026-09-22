"""Credential loading.

Keys are read from a file outside the repository, never from a command line
argument and never hard-coded. Command lines land in shell history and in
process listings; this does not.

Default location:  ~/.config/nofalsegreen/<provider>.key   (chmod 600)
Override with the matching environment variable, which takes precedence.
"""

from __future__ import annotations

import os
import stat
from pathlib import Path

KEY_DIR = Path.home() / ".config" / "nofalsegreen"

ENV_VARS = {
    "openrouter": ("OPENROUTER_API_KEY",),
    "gemini": ("GEMINI_API_KEY", "GOOGLE_API_KEY"),
    "groq": ("GROQ_API_KEY",),
    "anthropic": ("ANTHROPIC_API_KEY",),
    "openai": ("OPENAI_API_KEY",),
}


def load_key(provider: str, *, required: bool = True) -> str | None:
    """Return the API key for `provider`, or None when absent and not required."""
    for var in ENV_VARS.get(provider, ()):
        val = os.environ.get(var)
        if val:
            return val.strip()

    path = KEY_DIR / f"{provider}.key"
    if path.exists():
        mode = stat.S_IMODE(path.stat().st_mode)
        if mode & (stat.S_IRGRP | stat.S_IROTH):
            print(f"[credentials] warning: {path} is group/world readable "
                  f"(mode {mode:o}); run: chmod 600 {path}")
        key = path.read_text().strip()
        if key:
            return key

    if required:
        names = " or ".join(ENV_VARS.get(provider, ("<env var>",)))
        raise SystemExit(
            f"no {provider} key found.\n"
            f"  set {names}, or write the key to {path} (chmod 600)"
        )
    return None


# Shapes that indicate a placeholder was stored instead of a real key. Catching
# this here turns a confusing 401 mid-sweep into a clear message up front.
_PLACEHOLDER_MARKERS = (
    "PASTE", "YOUR_", "YOUR-", "NEW-KEY", "NEWKEY", "HERE", "XXX", "<", ">",
    "example", "changeme",
)
_MIN_PLAUSIBLE_LEN = {"openrouter": 60, "gemini": 30, "groq": 40,
                      "anthropic": 80, "openai": 40}


def check_key(provider: str, key: str) -> list[str]:
    """Return a list of problems with `key`, empty when it looks usable.

    This is a shape check, not a validity check: only a live call proves a key
    works. It exists to catch the common case of storing placeholder text.
    """
    problems = []
    upper = key.upper()
    for marker in _PLACEHOLDER_MARKERS:
        if marker.upper() in upper:
            problems.append(f"contains placeholder text {marker!r}")
            break
    floor = _MIN_PLAUSIBLE_LEN.get(provider, 20)
    if len(key) < floor:
        problems.append(f"only {len(key)} chars; a real {provider} key is ~{floor}+")
    if any(c.isspace() for c in key):
        problems.append("contains whitespace")
    return problems


def load_checked_key(provider: str, *, required: bool = True) -> str | None:
    """load_key plus a shape check, so a placeholder fails loudly and early."""
    key = load_key(provider, required=required)
    if key is None:
        return None
    problems = check_key(provider, key)
    if problems:
        path = KEY_DIR / f"{provider}.key"
        raise SystemExit(
            f"the stored {provider} key does not look usable:\n"
            + "".join(f"  - {p}\n" for p in problems)
            + f"  fix: write the real key to {path} (chmod 600)"
        )
    return key


def redact(key: str | None) -> str:
    """Safe-to-print fingerprint: never the key itself."""
    if not key:
        return "<none>"
    return f"<{len(key)} chars, ends {key[-4:]}>"
