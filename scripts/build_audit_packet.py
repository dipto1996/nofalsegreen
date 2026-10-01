"""Build the blind label-audit packet (docs/LABEL_AUDIT_PROTOCOL.md).

Per withheld pair: the obligation text exactly as models saw it and the export
files that pair's batch was shown (frozen subset order, batch 12, scoped
sources). No labels beyond the pair list, no label notes, no model output.

    python3 scripts/build_audit_packet.py <out_dir>
"""

from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from baselines.prompts import sources_for_regimes  # noqa: E402
from nofalsegreen import northwind  # noqa: E402
from nofalsegreen.rulebook import Rulebook  # noqa: E402
from nofalsegreen.subset import subset_firm  # noqa: E402

BATCH = 12  # the sweep's batch size; determines which exports each pair was shown


def main(out: Path) -> int:
    anchor = ROOT / "data" / "firms" / "northwind-robotics"
    rb = Rulebook.load(ROOT / "rulebook" / "rulebook.json")
    firm = subset_firm(northwind.load(anchor, anchor / "expectations.json"), rb.rule_regimes())
    by = {o.rule_id: o for o in rb.all_rules()}
    ent = {e.entity_id: f"{e.entity_type}: {e.label}" for e in firm.entities}
    lab = {l.pair_id: l for l in firm.labels}
    ids = [p.pair_id for p in firm.pairs]

    (out / "exports").mkdir(parents=True, exist_ok=True)
    used: set[str] = set()
    pairs = []
    for i in range(0, len(ids), BATCH):
        batch = ids[i:i + BATCH]
        srcs = sources_for_regimes(firm, {by[p.split("::")[0]].regime for p in batch})
        for pid in batch:
            if lab[pid].verdict.value != "needs_evidence":
                continue
            rid, eid = pid.split("::", 1)
            o = by[rid]
            used |= {firm.sources[s] for s in srcs}
            pairs.append({
                "pair_id": pid,
                "entity": ent.get(eid, "entity: " + eid),
                "obligation": {
                    "rule_id": rid, "check": o.summary, "threshold": o.threshold,
                    "citation": o.citation,
                    "information_needed": o.data_needed or ", ".join(o.evidence_required),
                },
                "exports_shown": sorted(Path(firm.sources[s]).name for s in srcs),
            })
    for f in used:
        p = Path(f)
        p = p if p.is_absolute() else anchor / p
        shutil.copy(p, out / "exports" / p.name)
    (out / "pairs.json").write_text(json.dumps({
        "employer": firm.name, "evaluation_date": str(firm.as_of),
        "n_pairs": len(pairs), "pairs": pairs}, indent=2))
    print(f"{len(pairs)} pairs; exports: {sorted(x.name for x in (out / 'exports').iterdir())}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(Path(sys.argv[1])))
