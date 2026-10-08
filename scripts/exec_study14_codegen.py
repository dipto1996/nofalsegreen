"""Execute the Study 14 code-generation replies (docs/STUDY14_DECLARATION.md), sandboxed.

Each program runs under macOS sandbox-exec with network access and all file writes denied,
in isolated mode (python3 -I -B), with a 60-second limit, on (a) the packet it was written
for and (b) the next content of the same workflow rendered in the same layout ("reuse").
Standard output is kept verbatim in docs/study14/codegen_exec.json, which the scorer reads,
so scoring never re-executes model code. No API call."""

from __future__ import annotations

import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from nofalsegreen import study14  # noqa: E402

PROFILE = "(version 1)(allow default)(deny network*)(deny file-write*)"
OUT = ROOT / "docs" / "study14" / "codegen_exec.json"


def program(text: str) -> str | None:
    m = re.findall(r"```python\s*\n(.*?)```", text or "", flags=re.S)
    return max(m, key=len) if m else None


def run(code: str, packet: Path) -> dict:
    with tempfile.TemporaryDirectory() as d:
        f = Path(d) / "prog.py"
        f.write_text(code)
        try:
            r = subprocess.run(["sandbox-exec", "-p", PROFILE, sys.executable, "-I", "-B", str(f), str(packet)],
                               capture_output=True, text=True, timeout=60)
            return {"returncode": r.returncode, "stdout": r.stdout[-400000:], "stderr": r.stderr[-2000:]}
        except subprocess.TimeoutExpired:
            return {"returncode": None, "stdout": "", "stderr": "timeout"}


def reuse_target(wf: str, lay: str, seed: int):
    """The next content of the same workflow in the same layout (wrapping round)."""
    others = sorted(s for w, l_, s in study14.renderings() if w == wf and l_ == lay and s != seed)
    later = [s for s in others if s > seed]
    return (later or others or [None])[0]


def _parsed(out: str):
    try:
        return json.loads(out[out.index("{"):out.rindex("}") + 1])
    except ValueError:
        return out


def replay() -> int:
    """Re-execute every retained program and compare with the stored record (added after review)."""
    done = json.loads(OUT.read_text())
    caches = {}
    for p in sorted((ROOT / "docs" / "study14" / "codegen_cache").glob("*.json")):
        caches.update(json.loads(p.read_text()))
    diff = 0
    for key, rec in sorted(done.items()):
        code = program(caches[key].get("text", ""))
        if not code:
            continue
        _, wf, lay, s = key.split("|")[3].split("-")
        for part, seed in (("own", int(s[1:])), ("reuse", rec.get("reuse_seed"))):
            if seed is None:
                continue
            r = run(code, study14.packet_dir(wf, lay, seed))
            # compare parsed output: a program that iterates a set prints in hash order, which
            # python3 -I leaves random, so the same facts can be printed in another order
            same = r["returncode"] == rec[part]["returncode"] and _parsed(r["stdout"]) == _parsed(rec[part]["stdout"])
            diff += not same
    print(f"replayed {len(done)} records; {diff} executions differ")
    return 1 if diff else 0


if __name__ == "__main__" and "--replay" in sys.argv:
    raise SystemExit(replay())

if __name__ == "__main__":
    caches = {}
    for p in sorted((ROOT / "docs" / "study14" / "codegen_cache").glob("*.json")):
        caches.update(json.loads(p.read_text()))
    done = json.loads(OUT.read_text()) if OUT.exists() else {}
    for key, v in sorted(caches.items()):
        if key in done:
            continue
        firm_id = key.split("|")[3]
        _, wf, lay, s = firm_id.split("-")
        seed = int(s[1:])
        code = program(v.get("text", ""))
        rec = {"has_program": code is not None}
        if code:
            rec["own"] = run(code, study14.packet_dir(wf, lay, seed))
            t = reuse_target(wf, lay, seed)
            rec["reuse_seed"] = t
            if t is not None:
                rec["reuse"] = run(code, study14.packet_dir(wf, lay, t))
        done[key] = rec
        OUT.write_text(json.dumps(done, indent=1, sort_keys=True))
        print(firm_id, key.split("|")[1].split("/")[-1], rec.get("own", {}).get("returncode"), flush=True)
    print("executed", len(done))
