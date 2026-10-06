"""Score the two AI pilot runs of the expert-review protocol. NOT expert validation.

Two AI systems were given the expert workbook and instructions as a pilot:
Claude (Anthropic) on kit v2 and Codex (OpenAI) on kit v3. Each is scored against
its own kit's construction labels. No API call. Writes docs/ai_pilot_review/results.json.
"""

from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
from score_expert_review import group, read  # noqa: E402

D = ROOT / "docs" / "ai_pilot_review"
RUNS = {"Claude (kit v2)": ("claude_v2.xlsx", "key_v2.json"), "Codex (kit v3)": ("codex_v3.xlsx", "key_v3.json")}


def main() -> int:
    out = {"note": "AI pilot runs of the expert protocol; not human expert review.", "runs": {}}
    for name, (wbf, kf) in RUNS.items():
        key = json.loads((D / kf).read_text())
        r = read(D / wbf)
        ids = sorted(key["items"], key=int)
        by = {}
        for i in ids:
            k, v = key["items"][i], r["items"].get(i, {}).get("verdict")
            g = by.setdefault(group(k), Counter())
            g["n"] += 1
            g["agree"] += v == k["label"]
            if v:
                g[v] += 1
        out["runs"][name] = {
            "items": len(ids),
            "answered": sum(1 for i in ids if r["items"].get(i, {}).get("verdict")),
            "agreement_overall": round(sum(r["items"].get(i, {}).get("verdict") == key["items"][i]["label"]
                                           for i in ids) / len(ids), 4),
            "by_group": {g: dict(c) for g, c in sorted(by.items())},
            "disagreements": [{"item": i, "label": key["items"][i]["label"], "answer": r["items"].get(i, {}).get("verdict"),
                               "group": group(key["items"][i]), "pair": key["items"][i]["pair_id"].split("::")[0],
                               "note": r["items"].get(i, {}).get("note")}
                              for i in ids if r["items"].get(i, {}).get("verdict") != key["items"][i]["label"]],
            "part_b": {s: r["statements"].get(str(j)) for j, s in enumerate(key["statements"], 1)},
            "about": r["about"],
        }
    (D / "results.json").write_text(json.dumps(out, indent=1, default=str))
    for n, v in out["runs"].items():
        print(n, v["answered"], "/", v["items"], "agreement", v["agreement_overall"])
        for g, c in v["by_group"].items():
            print("   ", g, c)
        for d in v["disagreements"]:
            print("    DISAGREE", d["item"], d["pair"], "label", d["label"], "->", d["answer"], "|", (d["note"] or "")[:150])
        for s, a in v["part_b"].items():
            print("    B:", a, "|", s[:80])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
