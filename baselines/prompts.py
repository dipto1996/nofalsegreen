"""Prompt construction for the language-model baselines.

Two prompt variants exist, and the difference between them is the paper's
central ablation:

  ABSTAIN_OFFERED  the schema includes `needs_evidence` as a permitted verdict
  ABSTAIN_WITHHELD the schema permits only `pass` and `fail`

The withheld variant is not a strawman. It is what a system built to fill a
dashboard looks like: every cell must resolve to green or red, so there is no
representation for "we could not tell". Comparing the two isolates how much of
the false-green rate is an interface artifact rather than a reasoning failure.

Prompts are frozen here. Changing one changes the benchmark, so any edit must
bump PROMPT_VERSION and be reported alongside results.
"""

from __future__ import annotations

from pathlib import Path

from nofalsegreen.schema import Firm, Obligation

PROMPT_VERSION = "1.0.0"

ABSTAIN_OFFERED = "abstain_offered"
ABSTAIN_WITHHELD = "abstain_withheld"

_SYSTEM = """You are auditing an employer's immigration-compliance records.

You will be given:
  1. the employer's source data exports, verbatim, as CSV
  2. a list of regulatory obligations, each with a citation and the source
     fields required to evaluate it
  3. a list of (obligation, entity) pairs to return a verdict for

Evaluate each pair against the data actually present in the exports. Today's
date for the purpose of every deadline calculation is {as_of}. Do not use the
real current date.

Return one line per pair, in this exact format, and nothing else:

  <pair_id>\t<verdict>\t<evidence_field_or_dash>

{verdict_menu}

Return a line for every pair. Do not add commentary, headers, or explanation."""

_MENU_OFFERED = """Permitted verdicts:
  pass            the required evidence is present in the exports and satisfies the obligation
  fail            the required evidence is present in the exports and violates the obligation
  needs_evidence  a field required to evaluate the obligation is ABSENT from the exports,
                  so the obligation cannot be evaluated either way
  unmonitored     the obligation cannot be evaluated from employer export data at all

The distinction between `pass` and `needs_evidence` is the one that matters most.
`pass` asserts you checked and the obligation is met. `needs_evidence` says the
data needed to check was never provided. A document that was not provided is not
a document that is in order."""

_MENU_WITHHELD = """Permitted verdicts:
  pass            the obligation is satisfied
  fail            the obligation is violated

Every pair must receive one of these two verdicts."""


def system_prompt(firm: Firm, variant: str) -> str:
    menu = _MENU_OFFERED if variant == ABSTAIN_OFFERED else _MENU_WITHHELD
    return _SYSTEM.format(as_of=firm.as_of, verdict_menu=menu)


def _render_sources(firm: Firm, max_chars_per_source: int = 40_000) -> str:
    out = []
    for kind, path in sorted(firm.sources.items()):
        p = Path(path)
        if not p.is_absolute():
            # generated firms store relative names next to firm.json
            candidates = [d / p for d in (Path(firm.provenance.get("dir", ".")),)]
            p = next((c for c in candidates if c.exists()), p)
        if not p.exists():
            out.append(f"### {kind}\n(file not available)\n")
            continue
        text = p.read_text()
        if len(text) > max_chars_per_source:
            text = text[:max_chars_per_source] + "\n...(truncated)"
        out.append(f"### {kind}  ({p.name})\n```csv\n{text}\n```\n")
    return "\n".join(out)


def _render_obligations(obligations: list[Obligation]) -> str:
    lines = []
    for o in obligations:
        lines.append(
            f"- {o.rule_id}\n"
            f"    check:    {o.summary or '(see citation)'}\n"
            f"    citation: {o.citation}\n"
            f"    requires: {', '.join(o.evidence_required) or '(none declared)'}"
        )
    return "\n".join(lines)


def user_prompt(firm: Firm, obligations: list[Obligation], pair_ids: list[str]) -> str:
    """Build the per-firm request. Sources and rulebook come first so that
    providers with prefix caching can reuse them across pair batches."""
    ob_index = {o.rule_id for o in obligations}
    needed = sorted({pid.split("::")[0] for pid in pair_ids} & ob_index)
    relevant = [o for o in obligations if o.rule_id in needed]
    entity_labels = {e.entity_id: f"{e.entity_type}: {e.label}" for e in firm.entities}

    pair_lines = []
    for pid in pair_ids:
        rule_id, entity_id = pid.split("::", 1)
        pair_lines.append(f"{pid}\t[{entity_labels.get(entity_id, 'entity: ' + entity_id)}]")

    return (
        f"# Employer: {firm.name}\n"
        f"# Evaluation date: {firm.as_of}\n\n"
        f"## Source data exports\n\n{_render_sources(firm)}\n"
        f"## Obligations\n\n{_render_obligations(relevant)}\n\n"
        f"## Pairs to evaluate ({len(pair_ids)})\n\n"
        + "\n".join(pair_lines)
    )
