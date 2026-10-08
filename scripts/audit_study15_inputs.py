"""Audit the inputs of Study 15's corrected run (declaration addendum). For every cached request
of the corrected run, regenerate the exact prompt, check that it contains the packet's whole
document and every record identifier, and that its SHA-256 matches the hash recorded with the
reply. Also checks the code-generation prompts. No API call; writes docs/study15/input_audit.json."""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))
from baselines.prompts import PROMPT_VERSION, codegen15_prompt, codegen15_repair, system_prompt, user_prompt  # noqa: E402
from nofalsegreen import study15  # noqa: E402

OUT = ROOT / "docs" / "study15"


def main() -> int:
    obls = study15.obligations()
    firms = {f"study15-{wf}-p{k:02d}": study15.firm(wf, k) for wf, k in study15.contents()}
    res = {"requests": 0, "hash_match": 0, "full_document": 0, "all_records": 0, "by_variant": {}}
    for p in sorted((OUT / "cache").glob("*contract15_*.json")):
        for key, v in sorted(json.loads(p.read_text()).items()):
            _, model, variant, fid, first, n = key.split("|")
            f = firms[fid]
            ids = [x.pair_id for x in f.pairs]
            i = ids.index(first)
            batch = ids[i:i + int(n)]
            system, user = system_prompt(f, variant), user_prompt(f, obls, batch, scope_sources=True)
            doc = Path(next(iter(f.sources.values()))).read_text()
            ok_hash = hashlib.sha256((system + "\x00" + user).encode()).hexdigest() == v.get("prompt_sha256")
            ok_doc = doc in user
            ok_ids = all(e.entity_id in user for e in f.entities)
            res["requests"] += 1
            res["hash_match"] += ok_hash
            res["full_document"] += ok_doc
            res["all_records"] += ok_ids
            b = res["by_variant"].setdefault(variant, [0, 0])
            b[0] += 1
            b[1] += ok_hash and ok_doc and ok_ids
    # Code generation: every call of every packet, repairs included. The first call's prompt is
    # rebuilt from the packet; a repair prompt from the previous call's retained program and
    # diagnostics, exactly as scripts/run_study15_codegen.py builds it.
    cg = {"packets": 0, "calls": 0, "hash_match": 0, "full_document": 0, "repair_calls": 0}
    for p in sorted((OUT / "codegen_cache_r2").glob("*.json")):
        for key, rec in sorted(json.loads(p.read_text()).items()):
            f = firms[key.split("|")[3]]
            doc = Path(next(iter(f.sources.values()))).read_text()
            man = {"pairs": [x.pair_id for x in f.pairs], "facts": {
                r: [x.name for x in study15.CONTRACTS[r].facts] for r in sorted({x.pair_id.split("::")[0] for x in f.pairs})}}
            system, user0 = codegen15_prompt(f, obls, man)
            user, code = user0, None
            cg["packets"] += 1
            for c in rec.get("calls", []):
                cg["calls"] += 1
                cg["hash_match"] += hashlib.sha256((system + "\x00" + user).encode()).hexdigest() == c.get("prompt_sha256")
                cg["full_document"] += doc in user
                cg["repair_calls"] += user is not user0
                if c.get("program"):
                    code = c["program"]
                if c.get("diagnostics") and code is not None:
                    user = codegen15_repair(user0, code, "\n\n".join(c["diagnostics"]))
    # Completions actually made (the cache keeps only accepted replies): from the run records.
    # A batch whose reply reached the 32,000-token cap is re-requested (up to three attempts).
    acc = {}
    for p in sorted((OUT / "runs").glob("*contract15_*.json")):
        if p.name.startswith("."):  # checkpoint files
            continue
        for r in json.loads(p.read_text())["runs"].values():
            k = f"{r['model'].split('/')[-1].split('#')[0]}::{r['variant']}"
            a = acc.setdefault(k, {"planned_batches": 0, "completions": 0, "capped_completions": 0})
            a["planned_batches"] += sum((x["n_pairs"] + r["batch_size"] - 1) // r["batch_size"] for x in r["per_firm"])
            a["completions"] += r["usage"]["calls"]
            a["capped_completions"] += sum(x.get("n_truncated_calls", 0) for x in r["per_firm"])
    for p in sorted((OUT / "codegen_cache_r2").glob("*.json")):
        for key, rec in json.loads(p.read_text()).items():
            k = f"{key.split('|')[1].split('/')[-1].split('#')[0]}::codegen15b"
            a = acc.setdefault(k, {"planned_batches": 0, "completions": 0, "capped_completions": 0})
            a["planned_batches"] += 1
            a["completions"] += len(rec.get("calls", []))
            a["capped_completions"] += sum(c.get("finish_reason") == "length" for c in rec.get("calls", []))
    res["completions"] = dict(sorted(acc.items()))
    res["codegen"] = cg
    res["prompt_version"] = PROMPT_VERSION
    (OUT / "input_audit.json").write_text(json.dumps(res, indent=1))
    print(json.dumps(res))
    ok = (res["requests"] == res["hash_match"] == res["full_document"] == res["all_records"]
          and cg["calls"] == cg["full_document"] == cg["hash_match"])
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
