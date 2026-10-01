"""Section 9 analyses, computed from the retained replies. No API calls.

Every analysis here was named in Section 9 before any v1.1 result existed; the
ones the evaluated data cannot support are reported as such, not dropped.

    python3 scripts/analysis.py        # -> docs/analysis_results.json

QUALITATIVE EXCERPT RULE, declared 2026-09-30 before any excerpt was read for
selection: for each finished run under abstain_offered, in the frozen subset's
pair order, take the FIRST false green (a `pass` on a withheld-evidence pair)
whose reply line names an evidence field (anything but "-"). One per model,
so no model is represented by its worst moment chosen from many. The verbatim
reply line is quoted with the label the generator fixed.
"""

from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

from baselines.prompts import PROMPT_VERSION  # noqa: E402
from nofalsegreen import northwind  # noqa: E402
from nofalsegreen.evidence_class import evidence_class  # noqa: E402
from nofalsegreen.rulebook import Rulebook  # noqa: E402
from nofalsegreen.subset import subset_firm  # noqa: E402
from score_views import ANCHOR, CACHE, predictions_by_run  # noqa: E402

LLM = ROOT / "docs" / "llm_results.json"
OUT = ROOT / "docs" / "analysis_results.json"


def decompose(labels, preds) -> dict:
    """Every pair lands in exactly one outcome."""
    p = {x.pair_id: x.verdict.value for x in preds}
    out: Counter = Counter()
    for lab in labels:
        got = p.get(lab.pair_id)
        truth = lab.verdict.value
        if got is None:
            out["unanswered"] += 1
        elif got == truth:
            out["correct"] += 1
        elif truth == "fail":
            out["missed_violation"] += 1          # fail called pass / needs_evidence / unmonitored
        elif got == "pass":
            out["false_green"] += 1                # withheld evidence called compliant
        elif got == "fail":
            out["unsupported_violation"] += 1      # withheld evidence called a violation
        else:
            out["other_wrong"] += 1                # e.g. unmonitored on a withheld pair
    return dict(out)


def by_evidence_class(labels, preds, rb) -> dict:
    by = rb.by_id()
    p = {x.pair_id: x.verdict.value for x in preds}
    acc: dict[str, Counter] = {"field": Counter(), "document": Counter()}
    for lab in labels:
        if lab.verdict.value != "needs_evidence":
            continue
        rid = lab.pair_id.split("::")[0]
        c = evidence_class(getattr(by.get(rid), "data_needed", None))
        got = p.get(lab.pair_id)
        acc[c]["n"] += 1
        if got is not None:
            acc[c]["answered"] += 1
            acc[c]["false_green"] += got == "pass"
            acc[c]["abstained"] += got == "needs_evidence"
    res = {}
    for c, a in acc.items():
        res[c] = {
            "n_withheld": a["n"], "n_answered": a["answered"],
            "n_false_green": a["false_green"], "n_abstained": a["abstained"],
            "fgr": round(a["false_green"] / a["n"], 4) if a["n"] else None,
            "fgr_answered": round(a["false_green"] / a["answered"], 4) if a["answered"] else None,
        }
    return res


def first_cited_false_green(labels, cache: dict, model: str, variant: str, firm_id: str):
    """Apply the declared excerpt rule to the raw replies of one run."""
    truth = {l.pair_id: l for l in labels}
    order = [l.pair_id for l in labels]
    lines: dict[str, str] = {}
    for key, v in cache.items():
        parts = key.split("|")
        if len(parts) != 6 or parts[0] != PROMPT_VERSION or parts[1] != model \
                or parts[2] != variant or parts[3] != firm_id:
            continue
        text = v.get("text", "") if isinstance(v, dict) else v
        for line in text.splitlines():
            cols = [c.strip() for c in line.split("\t")]
            if len(cols) >= 3 and cols[0] in truth:
                lines[cols[0]] = line.strip()
    for pid in order:
        line = lines.get(pid)
        if not line or truth[pid].verdict.value != "needs_evidence":
            continue
        cols = [c.strip() for c in line.split("\t")]
        if cols[1].lower() == "pass" and cols[2] not in ("-", "dash", ""):
            return {"pair_id": pid, "reply_line": line, "label": "needs_evidence",
                    "label_note": truth[pid].note}
    return None


def main() -> int:
    rb = Rulebook.load(ROOT / "rulebook" / "rulebook.json")
    firm = subset_firm(northwind.load(ANCHOR, ANCHOR / "expectations.json"), rb.rule_regimes())
    cache = json.loads(CACHE.read_text())
    finished = {k for k, v in json.loads(LLM.read_text()).get("runs", {}).items()
                if v.get("per_firm")}
    runs = predictions_by_run(firm, cache)

    labels = firm.labels
    out = {
        "prompt_version": PROMPT_VERSION,
        "n_pairs": len(labels),
        "label_mix": dict(Counter(l.verdict.value for l in labels)),
        "not_measurable": {
            "false_alarm_rate": "the evaluated subset has no conforming (pass) pairs",
            "near_miss_controls": "the evaluated subset has no conforming (pass) pairs",
            "evidence_pointer_accuracy": "anchor labels record no ground-truth evidence fields",
            "consistency_drift": "no system under test exposes headline counts",
        },
        "runs": {},
    }
    for (model, variant), preds in sorted(runs.items()):
        key = f"{model}::{variant}"
        if key not in finished:
            continue
        entry = {
            "model": model, "variant": variant,
            "n_answered": len(preds),
            "decomposition": decompose(labels, preds),
            "by_evidence_class": by_evidence_class(labels, preds, rb),
        }
        if variant.endswith("offered"):
            entry["excerpt"] = first_cited_false_green(labels, cache, model, variant, firm.firm_id)
        out["runs"][key] = entry

    OUT.write_text(json.dumps(out, indent=2))
    print(f"wrote {OUT}: {len(out['runs'])} finished run(s)")
    for k, e in out["runs"].items():
        bc = e["by_evidence_class"]
        print(f"  {k.split('/')[-1]:<48} {e['decomposition']}")
        print(f"  {'':<48} FGR field {bc['field']['fgr']}  document {bc['document']['fgr']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
