"""Study 14, code-generation baseline (docs/STUDY14_DECLARATION.md): one call per model and
packet rendering, asking for a parser program (baselines/prompts.codegen_prompt). Replies are
cached; scripts/score_study14.py executes them sandboxed. Retries a call whose reply is empty,
capped or has no program, up to three attempts."""

from __future__ import annotations

import json
import re
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from baselines.freetier import FREE_PROVIDERS, Quota  # noqa: E402
from baselines.prompts import PROMPT_VERSION, codegen_prompt  # noqa: E402
from nofalsegreen import study13, study14  # noqa: E402

OUT = ROOT / "docs" / "study14" / "codegen_cache"
MAX_TOKENS = 32000

if __name__ == "__main__":
    prov, model = sys.argv[1], sys.argv[2]
    only_wf = sys.argv[3] if len(sys.argv) > 3 else None
    OUT.mkdir(parents=True, exist_ok=True)
    short = model.split("/")[-1].split("#")[0]
    path = OUT / f"{short}{'__' + only_wf if only_wf else ''}.json"
    cache = json.loads(path.read_text()) if path.exists() else {}
    provider = FREE_PROVIDERS[prov](model, Quota(4, 100000, None, f"{model} codegen"))
    obls = study13.obligations(r2=True)
    for wf, lay, s in study14.renderings():
        if only_wf and wf != only_wf:
            continue
        f = study14.firm(wf, lay, s)
        key = f"{PROMPT_VERSION}|{model}|codegen14|{f.firm_id}"
        if key in cache:
            continue
        system, user = codegen_prompt(f, obls)
        for attempt in range(1, 4):
            t0 = time.time()
            try:
                text, u = provider.complete(system, user, MAX_TOKENS)
            except Exception as e:  # noqa: BLE001
                print(f"  {f.firm_id} attempt {attempt}: {type(e).__name__}: {str(e)[:120]}", flush=True)
                time.sleep(30 * attempt)
                continue
            ok = bool(re.search(r"```python\s*\n", text or "")) and u.finish_reason not in ("length", "error")
            print(f"  {f.firm_id} attempt {attempt}: {u.output_tokens} out, {time.time() - t0:.0f}s, "
                  f"finish={u.finish_reason}, {'ok' if ok else 'retry'}", flush=True)
            if ok or attempt == 3:
                cache[key] = {"text": text, "input_tokens": u.input_tokens, "output_tokens": u.output_tokens,
                              "finish_reason": u.finish_reason, "attempts": attempt}
                path.write_text(json.dumps(cache, indent=1))
                break
    print("done", len(cache))
