"""Second blind label audit and violation audit (docs/LABEL_AUDIT_PROTOCOL.md,
section declared 2026-10-03). One call per pair to Gemini 3.1 Pro on Vertex AI.

    python3 scripts/second_audit.py
"""

from __future__ import annotations

import json
import re
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from baselines.freetier import Quota, VertexProvider  # noqa: E402
from baselines.prompts import sources_for_regimes  # noqa: E402
from nofalsegreen import northwind  # noqa: E402
from nofalsegreen.rulebook import Rulebook  # noqa: E402
from nofalsegreen.subset import subset_firm  # noqa: E402

BATCH = 12
OUT = ROOT / "docs" / "label_audit_second.json"
PROTOCOL = (ROOT / "docs" / "LABEL_AUDIT_PROTOCOL.md").read_text()
CRITERION = PROTOCOL.split("## Criterion", 1)[1].split("## The audited view", 1)[0].strip()

SYSTEM = ("You are auditing the labels of a compliance benchmark. You are careful and literal. "
          "You answer with a single JSON object and nothing else.")

WITHHELD = """Audit this pair under the criterion below.

CRITERION
{criterion}

EVALUATION DATE: {as_of}
PAIR: {pair_id}
ENTITY: {entity}
OBLIGATION
  check:     {check}
  threshold: {threshold}
  citation:  {citation}
  information needed: {needed}

EXPORTS SHOWN FOR THIS PAIR
{exports}

Answer with JSON:
{{"decision": "evidence_present" | "evidence_withheld",
  "items": [{{"item": "...", "found_in": "file.column" or null, "value_for_entity": "..." or null}}],
  "conditional_items_skipped": ["..."],
  "reason": "one or two sentences"}}"""

VIOLATION = """Decide, from the exports alone, whether this entity meets the obligation.

Work item by item through "information needed": for each item give the file.column that
supplies it and its value for the entity, or null. Then apply the check and threshold as of
the evaluation date.

- "violation_shown": every item the decision needs is present and shows the obligation is
  not met.
- "compliance_shown": every item the decision needs is present and shows it is met.
- "cannot_tell": an item the decision needs is absent.

EVALUATION DATE: {as_of}
PAIR: {pair_id}
ENTITY: {entity}
OBLIGATION
  check:     {check}
  threshold: {threshold}
  citation:  {citation}
  information needed: {needed}

EXPORTS SHOWN FOR THIS PAIR
{exports}

Answer with JSON:
{{"decision": "violation_shown" | "compliance_shown" | "cannot_tell",
  "items": [{{"item": "...", "found_in": "file.column" or null, "value_for_entity": "..." or null}}],
  "reason": "one or two sentences"}}"""


def main() -> int:
    anchor = ROOT / "data" / "firms" / "northwind-robotics"
    rb = Rulebook.load(ROOT / "rulebook" / "rulebook.json")
    firm = subset_firm(northwind.load(anchor, anchor / "expectations.json"), rb.rule_regimes())
    by = {o.rule_id: o for o in rb.all_rules()}
    ent = {e.entity_id: f"{e.entity_type}: {e.label}" for e in firm.entities}
    lab = {l.pair_id: l for l in firm.labels}
    ids = [p.pair_id for p in firm.pairs]

    jobs = []
    for i in range(0, len(ids), BATCH):
        batch = ids[i:i + BATCH]
        srcs = sources_for_regimes(firm, {by[p.split("::")[0]].regime for p in batch})
        files = []
        for s in srcs:
            p = Path(firm.sources[s])
            p = p if p.is_absolute() else anchor / p
            files.append(f"### {p.name}\n```csv\n{p.read_text()}\n```")
        for pid in batch:
            v = lab[pid].verdict.value
            if v not in ("needs_evidence", "fail"):
                continue
            rid, eid = pid.split("::", 1)
            o = by[rid]
            fields = dict(criterion=CRITERION, as_of=firm.as_of, pair_id=pid,
                          entity=ent.get(eid, "entity: " + eid), check=o.summary,
                          threshold=o.threshold, citation=o.citation,
                          needed=o.data_needed or ", ".join(o.evidence_required),
                          exports="\n\n".join(files))
            jobs.append((pid, "withheld" if v == "needs_evidence" else "violation",
                         (WITHHELD if v == "needs_evidence" else VIOLATION).format(**fields)))

    done = json.loads(OUT.read_text())["pairs"] if OUT.exists() else {}
    prov = VertexProvider("vertex/gemini-3.1-pro-preview#audit",
                          Quota(rpm=20, rpd=100_000, tpm=None, label="vertex"))

    def run(job):
        pid, kind, prompt = job
        if pid in done:
            return pid, done[pid]
        for _ in range(3):
            text, _u = prov.complete(SYSTEM, prompt, 32_000)
            m = re.search(r"\{.*\}", text, re.S)
            try:
                return pid, {"audit": kind, **json.loads(m.group(0))}
            except (AttributeError, json.JSONDecodeError):
                continue
        return pid, {"audit": kind, "decision": "unparseable", "raw": text[:2000]}

    with ThreadPoolExecutor(max_workers=6) as ex:
        for pid, r in ex.map(run, jobs):
            done[pid] = r
            OUT.write_text(json.dumps({"auditor": "gemini-3.1-pro-preview (Vertex AI, temperature 0)",
                                       "protocol": "docs/LABEL_AUDIT_PROTOCOL.md (2026-10-03 section)",
                                       "pairs": done}, indent=1))
    first = json.loads((ROOT / "docs" / "label_audit.json").read_text())["pairs"]
    w = [p for p, r in done.items() if r["audit"] == "withheld"]
    a = [(first[p]["decision"], done[p]["decision"]) for p in w if p in first]
    agree = sum(x == y for x, y in a)
    po = agree / len(a)
    p1 = sum(x == "evidence_present" for x, _ in a) / len(a)
    p2 = sum(y == "evidence_present" for _, y in a) / len(a)
    pe = p1 * p2 + (1 - p1) * (1 - p2)
    kappa = (po - pe) / (1 - pe) if pe < 1 else 1.0
    viol = {p: r["decision"] for p, r in done.items() if r["audit"] == "violation"}
    summary = {"withheld_pairs": len(a), "agreement": agree, "cohen_kappa": round(kappa, 3),
               "overturned_first": sum(x == "evidence_present" for x, _ in a),
               "overturned_second": sum(y == "evidence_present" for _, y in a),
               "overturned_both": sorted(p for p in w if p in first
                                         and first[p]["decision"] == done[p]["decision"] == "evidence_present"),
               "overturned_second_only": sorted(p for p in w if p in first and done[p]["decision"] == "evidence_present"
                                                and first[p]["decision"] != "evidence_present"),
               "violation_decisions": {d: sum(v == d for v in viol.values()) for d in set(viol.values())},
               "violations_not_supported": sorted(p for p, d in viol.items() if d != "violation_shown")}
    doc = json.loads(OUT.read_text())
    doc["summary"] = summary
    OUT.write_text(json.dumps(doc, indent=1))
    print(json.dumps(summary, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
