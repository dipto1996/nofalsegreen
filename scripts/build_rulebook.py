"""Build rulebook/rulebook.json from the vendored manifest registry.

Rulebook v2 (2026-09-23) replaces v1, which was regex-parsed from the manifest's
markdown. That parse had two defects found by the pilot run:

  1. It missed 6 of the 196 manifest entries (the "196 vs 190" gap the v1 paper
     reported as unreconciled). The source engine ships a machine-readable
     registry of all 196; building from it closes the gap.
  2. It mangled each rule's required-evidence text into run-together tokens
     such as "section2CompletionDateemployersigndate", which a model cannot
     match to anything. v2 carries the verbatim prose.

v2 also resolves the 17 engine rule ids the anchor firm uses that are not
manifest ids, via rulebook/source/engine_aliases.json. In v1 those rules reached
the prompt with no definition at all.

    python3 scripts/build_rulebook.py
"""

from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "rulebook" / "source"
OUT = ROOT / "rulebook" / "rulebook.json"

VERSION = "2.0.0"


def clean_citation(c: str) -> str:
    """Drop the manifest's editorial verification notes; keep the citation."""
    c = re.sub(r"\s*\*\((?:[^)(]|\([^)]*\))*\)\*", "", c)
    return c.strip().rstrip(";").strip()


def tokens(data_needed: str) -> list[str]:
    """Short, human-readable items from the verbatim data-needed prose.

    Used only by the generator as a label annotation. The PROMPT uses the
    verbatim prose, never these tokens.
    """
    parts = re.split(r";|,(?![^(]*\))", data_needed)
    out = []
    for p in parts:
        p = re.sub(r"\s+", " ", p).strip(" .")
        if p:
            out.append(p[:80])
    return out[:10]


def main() -> int:
    registry = json.loads((SRC / "manifest_registry_196.json").read_text())
    aliases_doc = json.loads((SRC / "engine_aliases.json").read_text())

    by_id: dict[str, dict] = {}
    for e in registry:
        rid = e["ruleId"]
        if rid in by_id:
            # Two rules deliberately appear in two regimes (field view + timer
            # view). One entry per id; the second regime is recorded.
            by_id[rid].setdefault("also_in", []).append(e["category"])
            continue
        by_id[rid] = {
            "rule_id": rid,
            "regime": e["category"],
            "regime_name": e["regimeName"],
            "check": e.get("check") or "",
            "requirement": e.get("requirement") or "",
            "threshold": e.get("threshold") or "",
            "deadline": e.get("deadline") or "",
            "citation": clean_citation(e.get("citation") or ""),
            "data_needed": re.sub(r"\s+", " ", e.get("dataNeeded") or "").strip(),
            "needs_counsel": bool(e.get("needsCounsel")),
            "evidence_required": tokens(e.get("dataNeeded") or ""),
            "source": "manifest",
        }

    n_manifest_entries = len(registry)
    n_manifest_ids = len(by_id)

    for engine_id, target in aliases_doc["aliases"].items():
        t = by_id[target]  # KeyError here means the alias table is stale: fail loudly
        by_id[engine_id] = {**t, "rule_id": engine_id, "alias_of": target,
                            "source": "engine_alias"}

    for engine_id, r in aliases_doc["rollups"].items():
        parts = [by_id[x] for x in r["rolls_up"]]
        cites = []
        for p in parts:
            for c in re.split(r";\s*", p["citation"]):
                c = c.strip()
                if c and c not in cites:
                    cites.append(c)
        by_id[engine_id] = {
            "rule_id": engine_id,
            "regime": r["regime"],
            "regime_name": parts[0]["regime_name"],
            "check": r["check"],
            "requirement": " ".join(p["check"] for p in parts),
            "threshold": "",
            "deadline": "",
            "citation": "; ".join(cites[:4]),
            "data_needed": r["data_needed"],
            "needs_counsel": any(p["needs_counsel"] for p in parts),
            "evidence_required": tokens(r["data_needed"]),
            "rolls_up": r["rolls_up"],
            "source": "engine_rollup",
        }

    doc = {
        "version": VERSION,
        "source": "settle-v2 packages/rules/src/manifestRegistry.generated.ts "
                  "(196 entries) + rulebook/source/engine_aliases.json",
        "n_manifest_entries": n_manifest_entries,
        "n_manifest_ids": n_manifest_ids,
        "n_engine_aliases": len(aliases_doc["aliases"]),
        "n_engine_rollups": len(aliases_doc["rollups"]),
        "obligations": sorted(by_id.values(), key=lambda o: (o["regime"], o["rule_id"])),
    }
    OUT.write_text(json.dumps(doc, indent=1))
    print(f"wrote {OUT}")
    print(f"  manifest entries {n_manifest_entries}  ->  unique manifest ids {n_manifest_ids}")
    print(f"  + {doc['n_engine_aliases']} engine aliases + {doc['n_engine_rollups']} roll-ups"
          f"  =  {len(by_id)} resolvable rule ids")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
