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

VERSION HISTORY
  1.0.0  Pilot (2026-09-22). Found invalid: 30 of the 140 subset pairs, including
         10 of the 20 planted violations, reached the prompt with no obligation
         text (engine rule ids absent from the rulebook), and every obligation's
         "requires" line was a list of mangled tokens that could not be matched
         to any export column and that named reference data no export contains
         (e.g. a federal-holiday calendar). Because needs_evidence was defined as
         "a required field is absent", a model following the prompt literally
         had to abstain on violations whose evidence was present.
  1.1.0  Obligation text for every pair; verbatim "information needed" prose in
         place of tokens; needs_evidence defined by the firm's records rather
         than by field names; and two reading rules, identical in both ablation
         conditions: match export columns by meaning, and supply reference
         knowledge yourself. The verdict menus are otherwise unchanged, and the
         evaluated pairs are the same frozen 140.
"""

from __future__ import annotations

from pathlib import Path

from nofalsegreen.schema import Firm, Obligation

PROMPT_VERSION = "1.1.0"

ABSTAIN_OFFERED = "abstain_offered"
ABSTAIN_WITHHELD = "abstain_withheld"

_SYSTEM = """You are auditing an employer's immigration-compliance records.

You will be given:
  1. the employer's source data exports, verbatim, as CSV
  2. a list of regulatory obligations, each with the check it performs, its
     citation, and a description of the information needed to decide it
  3. a list of (obligation, entity) pairs to return a verdict for

Evaluate each pair against the data actually present in the exports. Today's
date for the purpose of every deadline calculation is {as_of}. Do not use the
real current date.

Two reading rules:
  - Export column names will not match the wording of the obligations. Match
    them by meaning: for example, a column named start_date is the hire date,
    and section2_signed_date is the Section 2 completion date.
  - Reference knowledge is not evidence you need from the exports. Calendars
    and federal holidays, regulatory thresholds, and the evaluation date are
    yours to apply. Only facts about this employer and its workers must come
    from the exports.

Return one line per pair, in this exact format, and nothing else:

  <pair_id>\t<verdict>\t<evidence_field_or_dash>

{verdict_menu}

Return a line for every pair. Do not add commentary, headers, or explanation."""

_MENU_OFFERED = """Permitted verdicts:
  pass            the required evidence is present in the exports and satisfies the obligation
  fail            the required evidence is present in the exports and violates the obligation
  needs_evidence  the exports do not contain the firm-specific information needed to
                  decide this obligation for this entity, so it cannot be evaluated
                  either way
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


# Which source exports each regime's obligations can possibly be evaluated
# against. Sending only these keeps prompts inside small per-minute token
# quotas, and is also simply better prompting: an obligation about I-9 timing
# has no use for a PERM recruitment tracker.
#
# The roster is always included because it is the canonical anchor every other
# source joins to. When a regime is unknown, all sources are sent, so the
# mapping can only shrink prompts for regimes it knows about and never hides
# data from an obligation it has not classified.
REGIME_SOURCES: dict[str, tuple[str, ...]] = {
    "i9-everify": ("hris_roster_export", "i9_record_export", "everify_case_export"),
    # payroll added in v1.1: lca.wage.required_wage_greater_of is an lca-dol
    # rule whose planted violation is measured on the payroll-register basis.
    "lca-dol": ("hris_roster_export", "lca_export", "cms_case_export", "payroll_register"),
    "paf": ("hris_roster_export", "lca_export"),
    "wage-prevailing": ("hris_roster_export", "lca_export", "payroll_register"),
    "h1b-status": ("hris_roster_export", "cms_case_export", "lca_export"),
    "i129-supplement": ("hris_roster_export", "cms_case_export", "lca_export"),
    "l1-visa": ("hris_roster_export", "cms_case_export"),
    "f1-opt-stem": ("hris_roster_export", "i9_record_export"),
    "fdns-sitevisit": ("hris_roster_export", "lca_export", "cms_case_export"),
    "deadlines-penalties": (
        "hris_roster_export", "i9_record_export", "lca_export",
        "cms_case_export", "rfe_noid_export",
    ),
}


def sources_for_regimes(firm: Firm, regimes: set[str]) -> list[str]:
    """Source kinds needed by the given regimes. Unknown regime = send everything."""
    if not regimes or any(r not in REGIME_SOURCES for r in regimes):
        return sorted(firm.sources)
    needed: set[str] = set()
    for r in regimes:
        needed |= set(REGIME_SOURCES[r])
    return sorted(k for k in firm.sources if k in needed)


def _render_sources(
    firm: Firm, only: list[str] | None = None, max_chars_per_source: int = 40_000
) -> str:
    out = []
    items = sorted(firm.sources.items())
    if only is not None:
        items = [(k, v) for k, v in items if k in only]
    for kind, path in items:
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
        block = [f"- {o.rule_id}", f"    check:     {o.summary or '(see citation)'}"]
        if o.threshold:
            block.append(f"    threshold: {o.threshold}")
        block.append(f"    citation:  {o.citation}")
        needed = o.data_needed or ", ".join(o.evidence_required)
        if needed:
            block.append(f"    information needed: {needed}")
        lines.append("\n".join(block))
    return "\n".join(lines)


def user_prompt(
    firm: Firm,
    obligations: list[Obligation],
    pair_ids: list[str],
    *,
    scope_sources: bool = False,
) -> str:
    """Build the per-batch request.

    `scope_sources=True` sends only the exports the batch's regimes can be
    evaluated against. This is what makes the benchmark runnable inside small
    free-tier per-minute token quotas. It is reported alongside results,
    because it changes the prompt and therefore the measurement.
    """
    ob_index = {o.rule_id for o in obligations}
    wanted = {pid.split("::")[0] for pid in pair_ids}
    undefined = sorted(wanted - ob_index)
    if undefined:
        # v1.0 sent such pairs with no definition. A model cannot be scored on an
        # obligation it was never shown, so this is now a hard error.
        raise ValueError(
            f"{len(undefined)} rule id(s) in this batch have no obligation text: "
            f"{undefined[:5]}. Pass Rulebook.all_rules(), not Rulebook.obligations."
        )
    relevant = [o for o in obligations if o.rule_id in wanted]
    entity_labels = {e.entity_id: f"{e.entity_type}: {e.label}" for e in firm.entities}

    only = None
    if scope_sources:
        only = sources_for_regimes(firm, {o.regime for o in relevant})

    pair_lines = []
    for pid in pair_ids:
        rule_id, entity_id = pid.split("::", 1)
        pair_lines.append(f"{pid}\t[{entity_labels.get(entity_id, 'entity: ' + entity_id)}]")

    note = ""
    if only is not None and len(only) < len(firm.sources):
        withheld = sorted(set(firm.sources) - set(only))
        note = (
            "\n> Only the exports relevant to these obligations are shown. "
            f"Not shown: {', '.join(withheld)}. Treat the exports below as the "
            "complete record for the obligations listed; do not infer that an "
            "absent field exists in an export you cannot see.\n"
        )

    return (
        f"# Employer: {firm.name}\n"
        f"# Evaluation date: {firm.as_of}\n\n"
        f"## Source data exports\n{note}\n{_render_sources(firm, only)}\n"
        f"## Obligations\n\n{_render_obligations(relevant)}\n\n"
        f"## Pairs to evaluate ({len(pair_ids)})\n\n"
        + "\n".join(pair_lines)
    )
