"""Study 15, code-generation arm (docs/STUDY15_DECLARATION.md). Per model and packet: up to three
calls of 32,000 output tokens (extraction's budget for the same packet). The program is run
sandboxed on the packet with its manifest; if it fails, prints no valid JSON, misses or adds
pairs, or reports malformed facts, the diagnostics (never a label or a correct value) go back
to the model for a repair, at most twice. The final program is also run on the next packet of
the same source with that packet's manifest ("reuse"). Everything, including each execution,
is cached in docs/study15/codegen_cache."""

from __future__ import annotations

import json
import re
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))
from baselines.freetier import FREE_PROVIDERS, Quota  # noqa: E402
from baselines.prompts import PROMPT_VERSION, codegen15_prompt, codegen15_repair  # noqa: E402
from exec_study14_codegen import program as extract_program  # noqa: E402
from nofalsegreen import study15  # noqa: E402

OUT = ROOT / "docs" / "study15" / "codegen_cache"
MAX_TOKENS, MAX_CALLS = 32000, 3
PROFILE = "(version 1)(allow default)(deny network*)(deny file-write*)"


def manifest(f) -> dict:
    rules = sorted({p.pair_id.split("::")[0] for p in f.pairs})
    return {"pairs": [p.pair_id for p in f.pairs],
            "facts": {r: [x.name for x in study15.CONTRACTS[r].facts] for r in rules}}


def execute(code: str, packet: Path, man: dict) -> dict:
    import subprocess
    with tempfile.TemporaryDirectory() as d:
        (Path(d) / "prog.py").write_text(code)
        (Path(d) / "manifest.json").write_text(json.dumps(man))
        try:
            r = subprocess.run(["sandbox-exec", "-p", PROFILE, sys.executable, "-I", "-B", str(Path(d) / "prog.py"),
                                str(packet), str(Path(d) / "manifest.json")], capture_output=True, text=True, timeout=60)
            return {"returncode": r.returncode, "stdout": r.stdout[-400000:], "stderr": r.stderr[-2000:]}
        except subprocess.TimeoutExpired:
            return {"returncode": None, "stdout": "", "stderr": "timeout"}


def diagnose(run: dict, man: dict, doc: str) -> list:
    """Problems visible without any label: execution, JSON, pairs, fact shapes."""
    out = []
    if run["returncode"] != 0:
        out.append(f"The program exited with code {run['returncode']}. Standard error (end):\n{run['stderr'][-1500:]}")
        return out
    s = run["stdout"]
    try:
        obj = json.loads(s[s.index("{"):s.rindex("}") + 1])
    except ValueError:
        return ["Standard output did not contain a JSON object."]
    want = set(man["pairs"])
    miss, extra = sorted(want - set(obj)), sorted(set(obj) - want)
    if miss:
        out.append(f"{len(miss)} manifest pairs are missing from the output, e.g. {miss[:5]}.")
    if extra:
        out.append(f"{len(extra)} pairs not in the manifest were printed, e.g. {extra[:5]}.")
    bad = []
    for pid in sorted(want & set(obj)):
        facts = obj[pid]
        names = man["facts"].get(pid.split("::")[0], [])
        if not isinstance(facts, dict) or set(facts) != set(names):
            bad.append(f"{pid}: expected exactly the facts {names}")
            continue
        for k, v in facts.items():
            if v in ("ABSENT", "CONFLICT"):
                continue
            if not (isinstance(v, list) and len(v) == 2):
                bad.append(f"{pid} / {k}: not [value, document], ABSENT or CONFLICT")
                continue
            kind = next(f.kind for f in study15.CONTRACTS[pid.split("::")[0]].facts if f.name == k)
            ok = bool(re.fullmatch(r"\d{4}-\d{2}-\d{2}", str(v[0]))) if kind == "date" else \
                bool(re.fullmatch(r"-?\d+(\.\d+)?", str(v[0])))
            if not ok:
                bad.append(f"{pid} / {k}: value {v[0]!r} is not a {'YYYY-MM-DD date' if kind == 'date' else 'decimal string'}")
            if str(v[1]) != doc:
                bad.append(f"{pid} / {k}: document {v[1]!r} is not {doc!r}")
    if bad:
        out.append(f"{len(bad)} malformed facts, e.g.:\n" + "\n".join(bad[:8]))
    return out


if __name__ == "__main__":
    prov, model, wf = sys.argv[1], sys.argv[2], sys.argv[3]
    shard, nshards = map(int, (sys.argv[4] if len(sys.argv) > 4 else "0/1").split("/"))  # throughput only
    OUT.mkdir(parents=True, exist_ok=True)
    short = model.split("/")[-1].split("#")[0]
    path = OUT / f"{short}__{wf}__s{shard}of{nshards}.json"
    cache = json.loads(path.read_text()) if path.exists() else {}
    provider = FREE_PROVIDERS[prov](model, Quota(4, 100000, None, f"{model} codegen15"))
    obls = study15.obligations()
    for k in range(study15.PACKETS[wf]):
        if k % nshards != shard:
            continue
        f = study15.firm(wf, k)
        key = f"{PROMPT_VERSION}|{model}|codegen15|{f.firm_id}"
        if key in cache:
            continue
        man = manifest(f)
        system, user0 = codegen15_prompt(f, obls, man)
        user, calls, code, last = user0, [], None, None
        for call in range(1, MAX_CALLS + 1):
            text, u = None, None
            for attempt in range(1, 4):  # delivery retries (errors, rate limits) are not repair calls
                try:
                    text, u = provider.complete(system, user, MAX_TOKENS)
                    break
                except Exception as e:  # noqa: BLE001
                    print(f"  {f.firm_id} call {call} delivery {attempt}: {type(e).__name__} {str(e)[:100]}", flush=True)
                    time.sleep(30 * attempt)
            if text is None:
                break
            new = extract_program(text)
            rec = {"output_tokens": u.output_tokens, "input_tokens": u.input_tokens, "finish_reason": u.finish_reason,
                   "has_program": new is not None}
            if new is None:
                calls.append(rec)
                diag = ["The reply contained no ```python block."]
            else:
                code = new
                last = execute(code, study15.packet_dir(wf, k), man)
                diag = diagnose(last, man, study15.DOC[wf])
                rec["diagnostics"] = diag
                calls.append(rec)
            print(f"  {f.firm_id} call {call}: {u.output_tokens} out, finish={u.finish_reason}, "
                  f"{'clean' if not diag else str(len(diag)) + ' problem(s)'}", flush=True)
            if not diag:
                break
            if call < MAX_CALLS and code is not None:
                user = codegen15_repair(user0, code, "\n\n".join(diag))
        entry = {"calls": calls, "program": code, "own": last}
        if code is not None:
            nxt = (k + 1) % study15.PACKETS[wf]
            g = study15.firm(wf, nxt)
            entry["reuse_packet"] = nxt
            entry["reuse"] = execute(code, study15.packet_dir(wf, nxt), manifest(g))
        cache[key] = entry
        path.write_text(json.dumps(cache, indent=1))
    print("done", len(cache))
