"""Evidence class of an obligation: is the missing evidence a FIELD or a DOCUMENT?

DECLARED 2026-09-30, BEFORE ANY RATE WAS COMPUTED BY CLASS. Section 9 of the
paper states the hypothesis: models abstain more reliably when the missing
evidence is a field (an absent column is visible) than when it is a document
(absence of a record nobody expected to see is a harder inference).

The classification is mechanical, applied to the rulebook's own verbatim
"information needed" text, so that no per-obligation judgment made while
results exist can move an obligation between classes:

  document  the text names a document, notice, posting, memo, file, list,
            summary, copy, clause, or a presence flag for one. The evidence
            is the existence or content of a record that has no export
            column.
  field     everything else: the evidence is dates, enums, amounts, and
            counts that an HRIS, CMS, or I-9 export would carry as columns.

The pattern is deliberately broad on the document side, so an obligation that
mixes both kinds of evidence is classed as document. The full assignment for
the evaluated subset is printed by `python3 -m nofalsegreen.evidence_class`
and is committed with this file.
"""

from __future__ import annotations

import re

DECLARED_ON = "2026-09-30"

_DOCUMENT = re.compile(
    r"\b(memo|notice|notices|posting|postings|public access|paf|exhibit|copy|"
    r"letter|summary|clause|acknowledg\w*|itinerary|lease|contract|sow|"
    r"checklist|storage|retention|file)\b"
    # Presence flags, including camelCase ones such as wageRateDocPresent.
    r"|present\b|\w+Present\b|\w*(?:Doc|Document|Copy|Notice|Memo)\w*",
    re.IGNORECASE,
)


def evidence_class(data_needed: str | None) -> str:
    """'document' or 'field' for one obligation's information-needed text."""
    if not data_needed:
        return "field"
    return "document" if _DOCUMENT.search(data_needed) else "field"


if __name__ == "__main__":
    import sys
    from collections import Counter
    from pathlib import Path

    root = Path(__file__).resolve().parent.parent
    sys.path.insert(0, str(root))
    from nofalsegreen import northwind
    from nofalsegreen.rulebook import Rulebook
    from nofalsegreen.subset import subset_firm

    anchor = root / "data" / "firms" / "northwind-robotics"
    rb = Rulebook.load(root / "rulebook" / "rulebook.json")
    firm = subset_firm(northwind.load(anchor, anchor / "expectations.json"), rb.rule_regimes())
    by = rb.by_id()
    rules = Counter(l.pair_id.split("::")[0] for l in firm.labels
                    if l.verdict.value == "needs_evidence")
    per_class: Counter = Counter()
    for rid, n in sorted(rules.items()):
        o = by.get(rid)
        c = evidence_class(getattr(o, "data_needed", None))
        per_class[c] += n
        print(f"{c:<9}{n:>3}  {rid}")
    print(f"\nwithheld pairs by class: {dict(per_class)}")
