"""Build the expert-labelling kit for practising immigration counsel.

Declared 2026-10-03. Selection is seeded and fixed here, before any expert
sees a pair, and the kit carries no benchmark label, label note, or model
output: experts label blind, and agreement with the construction labels is
computed afterwards (scripts/expert_agreement.py).

SAMPLE (80 pairs):
  anchor firm   all 20 planted violations (never audited) + 20 withheld pairs,
                seeded uniform from the 118 the blind audit upheld
  Study 2       10 each of violation, near-miss control, other control and
                withheld, seeded uniform across the five firms' frozen subsets

    python3 scripts/build_expert_kit.py     # -> docs/expert_labelling/
"""

from __future__ import annotations

import csv
import json
import random
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from baselines.prompts import sources_for_regimes  # noqa: E402
from nofalsegreen import northwind, study2  # noqa: E402
from nofalsegreen.labelviews import overturned  # noqa: E402
from nofalsegreen.rulebook import Rulebook  # noqa: E402
from nofalsegreen.subset import subset_firm  # noqa: E402

SEED = 20261003
OUT = ROOT / "docs" / "expert_labelling"
INSTRUCTIONS = """# Expert labelling: instructions

Thank you for helping. You will label 80 compliance questions about synthetic
employers (no real person or company). Each takes 1-3 minutes; the whole set
should take about two to three hours. Please work alone and do not discuss
items with anyone else labelling the same set.

## What each row asks

Each row of `labelling_form.csv` is one obligation applied to one worker, LCA,
or employer, as of the evaluation date in the row. Open the CSV exports named
in the `exports` column (in `exports/`) and decide, from those records alone:

- **pass**: the records contain the information needed and show the obligation
  is met as of the evaluation date.
- **fail**: the records contain the information needed and show a violation as
  of the evaluation date.
- **needs_evidence**: the records do not contain firm-specific information
  needed to decide (a required item is missing or blank for this entity).
  Choose this whenever you would have to ask the client for something.
- **unmonitored**: the obligation cannot apply to this entity.

Use your professional knowledge of the rules, deadlines and thresholds. Do not
assume any fact about the employer that the records do not show.

## What to fill in

- `verdict`: one of the four words above.
- `confidence`: high, medium, or low.
- `comment` (optional but valuable): what decided it, or what is ambiguous.

The "information needed" column is the benchmark's own description of what an
assessment requires. If you disagree with it as a matter of law, decide as you
think correct and say so in the comment; that disagreement is itself useful.

## Returning

Save the CSV and send it back. You will be acknowledged by name in the paper
unless you prefer not to be.
"""


def row(pid_shown, entity, as_of, ob, files):
    return {
        "item": pid_shown, "entity": entity, "evaluation_date": as_of,
        "rule_id": ob.rule_id, "check": ob.summary or "", "threshold": ob.threshold or "",
        "citation": ob.citation or "",
        "information_needed": ob.data_needed or ", ".join(ob.evidence_required),
        "exports": " ; ".join(files), "verdict": "", "confidence": "", "comment": "",
    }


def main() -> int:
    rng = random.Random(SEED)
    rb = Rulebook.load(ROOT / "rulebook" / "rulebook.json")
    by = {o.rule_id: o for o in rb.all_rules()}
    (OUT / "exports").mkdir(parents=True, exist_ok=True)
    rows, key = [], {}

    def add(firm, pid, prefix):
        rid, eid = pid.split("::", 1)
        ob = by[rid]
        ent = {e.entity_id: f"{e.entity_type}: {e.label}" for e in firm.entities}
        files = []
        for s in sources_for_regimes(firm, {ob.regime}):
            src = Path(firm.sources[s])
            if not src.is_absolute():
                src = ROOT / "data" / "firms" / "northwind-robotics" / src
            dst = OUT / "exports" / f"{prefix}_{src.name}"
            if not dst.exists():
                shutil.copy(src, dst)
            files.append(dst.name)
        item = f"Q{len(rows) + 1:03d}"
        rows.append(row(item, ent.get(eid, eid), str(firm.as_of), ob, sorted(files)))
        lab = firm.label_index()[pid]
        key[item] = {"firm": firm.firm_id, "pair_id": pid, "label": lab.verdict.value,
                     "stratum": study2._stratum(lab) if prefix != "anchor" else
                     ("fail" if lab.verdict.value == "fail" else "withheld")}

    anchor_dir = ROOT / "data" / "firms" / "northwind-robotics"
    anchor = subset_firm(northwind.load(anchor_dir, anchor_dir / "expectations.json"),
                         rb.rule_regimes())
    gone = overturned() or frozenset()
    fails = sorted(l.pair_id for l in anchor.labels if l.verdict.value == "fail")
    withheld = sorted(l.pair_id for l in anchor.labels
                      if l.verdict.value == "needs_evidence" and l.pair_id not in gone)
    for pid in fails + rng.sample(withheld, 20):
        add(anchor, pid, "anchor")

    firms = study2.load_firms(rb)
    pool: dict[str, list] = {}
    for f in firms:
        for l in f.labels:
            pool.setdefault(study2._stratum(l), []).append((f, l.pair_id))
    for s in ("fail", "near_miss", "control", "withheld"):
        for f, pid in rng.sample(sorted(pool[s], key=lambda x: (x[0].firm_id, x[1])), 10):
            add(f, pid, f.firm_id.split("-")[1])

    order = list(range(len(rows)))
    rng.shuffle(order)  # so strata and firms are interleaved for the expert
    shuffled = [rows[i] for i in order]
    for n, r in enumerate(shuffled, 1):
        old = r["item"]
        r["item"] = f"Q{n:03d}"
        key[r["item"] + "_final"] = key.pop(old)
    key = {k.replace("_final", ""): v for k, v in key.items()}

    with open(OUT / "labelling_form.csv", "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(shuffled[0]))
        w.writeheader()
        w.writerows(shuffled)
    (OUT / "INSTRUCTIONS.md").write_text(INSTRUCTIONS)
    # The answer key is kept OUT of the kit directory so it is never sent.
    (ROOT / "docs" / "expert_labelling_key.json").write_text(json.dumps(key, indent=2))
    print(f"{len(shuffled)} items -> {OUT}; key -> docs/expert_labelling_key.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
