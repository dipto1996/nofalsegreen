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
# Added 2026-10-03 after review (prompt text of the other two variants is
# unchanged, so PROMPT_VERSION stays 1.1.0): the offered menu with ONLY the
# `needs_evidence` verdict and the sentences that define it removed. `pass`,
# `fail` and `unmonitored` keep their offered-condition definitions word for
# word, and the closing warning is kept. This is the one-variable ablation;
# ABSTAIN_WITHHELD changes four things at once (see the paper, Section 7).
ABSTAIN_REMOVED_ONLY = "abstain_removed_only"
# Added 2026-10-03, after abstain_removed_only showed models routing withheld
# pairs to `unmonitored` instead: BOTH non-committal verdicts removed, but `pass`
# and `fail` keep their evidence-anchored offered-condition definitions and the
# closing warning is kept. Against ABSTAIN_WITHHELD this isolates the redefinition
# of `pass` (plus the warning); against ABSTAIN_OFFERED, the removal of every
# abstention channel.
ABSTAIN_CLOSED = "abstain_closed"

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


_MENU_REMOVED_ONLY = """Permitted verdicts:
  pass            the required evidence is present in the exports and satisfies the obligation
  fail            the required evidence is present in the exports and violates the obligation
  unmonitored     the obligation cannot be evaluated from employer export data at all

A document that was not provided is not a document that is in order."""


_MENU_CLOSED = """Permitted verdicts:
  pass            the required evidence is present in the exports and satisfies the obligation
  fail            the required evidence is present in the exports and violates the obligation

A document that was not provided is not a document that is in order.

Every pair must receive one of these two verdicts."""


# Paraphrase study (docs/STUDY3B_PARAPHRASE.md, declared 2026-10-04 before any
# call): the offered and dashboard schemas reworded throughout, same meaning,
# same verdict tokens. Tests whether the Study 3 effects depend on one wording.
ABSTAIN_OFFERED_PARA = "abstain_offered_para"
ABSTAIN_WITHHELD_PARA = "abstain_withheld_para"

_SYSTEM_PARA = """Your task is to review an employer's records for immigration compliance.

Inputs:
  (a) the employer's data exports, copied verbatim in CSV form
  (b) the regulatory obligations to assess, each with its check, its legal
      citation and the information required to decide it
  (c) the (obligation, entity) pairs that need a verdict

Judge every pair using only what the exports actually contain. Treat {as_of}
as today's date for all deadline arithmetic; ignore the real calendar date.

How to read the data:
  - Column names in the exports differ from the language of the obligations,
    so match by meaning. For instance, start_date means the hire date, and
    section2_signed_date means the date Section 2 was completed.
  - General knowledge, such as calendars, federal holidays, regulatory
    thresholds and the evaluation date, is yours to supply. Only facts
    specific to this employer and its workers have to come from the exports.

Answer with exactly one line per pair, formatted as below, and with no other text:

  <pair_id>\t<verdict>\t<evidence_field_or_dash>

{verdict_menu}

Every pair needs a line. Add no headings, notes or commentary."""

_MENU_OFFERED_PARA = """Allowed verdicts:
  pass            the exports contain the evidence the obligation requires, and
                  that evidence shows the obligation is met
  fail            the exports contain the evidence the obligation requires, and
                  that evidence shows the obligation is breached
  needs_evidence  the firm-specific information required to decide this
                  obligation for this entity is missing from the exports, so no
                  judgement either way is possible
  unmonitored     employer export data could never show whether this
                  obligation is met

Keep `pass` and `needs_evidence` apart above all else. `pass` means you verified
that the obligation is met. `needs_evidence` means the data required to verify it
was not supplied. A record that was never supplied cannot be a record in good order."""

_MENU_WITHHELD_PARA = """Allowed verdicts:
  pass            the obligation is met
  fail            the obligation is breached

Give every pair one of these two verdicts."""


# Study 4 (docs/STUDY4_DECLARATION.md, declared before any call): the three
# things the offered -> dashboard change bundles, varied one at a time in a 2x2x2
# factorial. Variant "fx_o{O}d{D}w{W}":
#   O  1 = the two abstaining verdicts are listed with their offered definitions
#   D  1 = pass/fail defined by the required evidence; 0 = bare definitions
#   W  1 = the one-sentence warning is present
# Every menu ends with the same closing sentence, so menus differ only in O, D, W.
_FX_PASS = {1: "pass            the required evidence is present in the exports and satisfies the obligation",
            0: "pass            the obligation is satisfied"}
_FX_FAIL = {1: "fail            the required evidence is present in the exports and violates the obligation",
            0: "fail            the obligation is violated"}
_FX_ABSTAIN = """needs_evidence  the exports do not contain the firm-specific information needed to
                  decide this obligation for this entity, so it cannot be evaluated
                  either way
  unmonitored     the obligation cannot be evaluated from employer export data at all"""
_FX_WARNING = "A document that was not provided is not a document that is in order."
FACTORIAL = tuple(f"fx_o{o}d{d}w{w}" for o in (1, 0) for d in (1, 0) for w in (1, 0))


def _menu_factorial(variant: str) -> str:
    o, d, w = (int(variant[i]) for i in (4, 6, 8))
    lines = ["Permitted verdicts:", "  " + _FX_PASS[d], "  " + _FX_FAIL[d]]
    if o:
        lines.append("  " + _FX_ABSTAIN)
    out = "\n".join(lines)
    if w:
        out += "\n\n" + _FX_WARNING
    return out + "\n\nEvery pair must receive one of the verdicts listed above."


# Study 4 evidence-gating prompt: the offered menu, plus a requirement to name
# the column that IS the required record before committing.
CITE_FIRST = "cite_first"
_MENU_CITE_FIRST = _MENU_OFFERED + """

Before you give `pass` or `fail`, identify the column that is itself the required
record (for example, the Section 2 completion date in the I-9 export, or wages
actually paid in the payroll register) and give it as the evidence field, in the
form <export>.<column>. If no export contains that record, the verdict is
`needs_evidence`, even when other columns suggest the obligation is met."""


# Study 9 (docs/STUDY9_DECLARATION.md): domain-neutral prompts for records checked against
# stated decision contracts. The contract for each rule names the only columns that
# establish each fact; the menus mirror the offered and dashboard schemas.
CONTRACT_OFFERED = "contract_offered"
CONTRACT_FORCED = "contract_forced"
CONTRACT_EVIDENCE_FIRST = "contract_evidence_first"
CONTRACT_EXTRACT = "contract_extract"
# Study 10 (docs/STUDY10_DECLARATION.md): the same rules with the evidence described rather
# than bound to named columns, and the system prompt without the binding sentence.
CONTRACT_SEM_OFFERED = "contract_sem_offered"
CONTRACT_SEM_FORCED = "contract_sem_forced"
# Study 12 (docs/STUDY12_DECLARATION.md): the "match by meaning" reading rule of the
# original prompt, added to the described-evidence prompt (and, below, removed from the
# original offered prompt).
CONTRACT_SEM_MEANING_OFFERED = "contract_sem_meaning_offered"
ABSTAIN_OFFERED_NOMATCH = "abstain_offered_nomatch"
_MEANING_RULE = """Column names will not match the wording of the rules. Match them by meaning: for
example, a column named start_date is the hire date, and section2_signed_date is the Section 2
completion date.

"""
CONTRACT_VARIANTS = (CONTRACT_OFFERED, CONTRACT_FORCED, CONTRACT_EVIDENCE_FIRST, CONTRACT_EXTRACT,
                     CONTRACT_SEM_OFFERED, CONTRACT_SEM_FORCED, CONTRACT_SEM_MEANING_OFFERED)

_SYSTEM_CONTRACT = """You are checking an organisation's records against stated decision rules.

You will be given:
  1. the organisation's records, verbatim, as CSV tables
  2. the decision rules; each rule states its predicate and, for every fact it needs, the
     only table columns that establish that fact
  3. a list of (rule, entity) pairs to return a verdict for

A fact is established only by the columns the rule names for it. Other columns, however
they are named, do not establish it. Business days exclude weekends and US federal holidays.

Return one line per pair, in this exact format, and nothing else:

  <pair_id>\t<verdict>\t<evidence_or_dash>

{verdict_menu}

Return a line for every pair. Do not add commentary, headers, or explanation."""

_MENU_CONTRACT_OFFERED = """Permitted verdicts:
  pass            the named columns establish every fact and the rule is satisfied
  fail            the named columns establish that the rule is violated
  needs_evidence  the named columns do not establish enough to decide, or they conflict
  unmonitored     the rule cannot apply to this entity

In the evidence field, give the table.column you relied on."""

_MENU_CONTRACT_FORCED = """Permitted verdicts:
  pass            the rule is satisfied
  fail            the rule is violated

Every pair must receive one of these two verdicts. In the evidence field, give the
table.column you relied on."""

_MENU_CONTRACT_EVIDENCE_FIRST = _MENU_CONTRACT_OFFERED + """

Before you give `pass` or `fail`, find the value of every fact in a column the rule names
for it. If any fact has no value in its named columns, or its named values disagree with no
stated priority, the verdict is `needs_evidence`, even when other columns suggest an answer.
A missing fact does not prevent `fail` if the facts that are established already violate
the rule whatever the missing value is."""

_MENU_CONTRACT_EXTRACT = """Do not decide the rule yourself. Return one line per pair, in this exact format, reporting
the value of every fact the rule needs, read only from the columns the rule names for it:

  <pair_id>\tfacts\t<fact name>=<value> from <table>.<column> | <fact name>=ABSENT | <fact name>=CONFLICT

Write ABSENT when no named column has a value for that entity, and CONFLICT when the named
columns hold disagreeing values and the rule states no priority (when it states a priority,
report the prevailing value). Use exactly the fact names in the rule. Dates as YYYY-MM-DD,
amounts as plain numbers."""


_SYSTEM_SEM = _SYSTEM_CONTRACT.replace("""  2. the decision rules; each rule states its predicate and, for every fact it needs, the
     only table columns that establish that fact""", """  2. the decision rules; each rule states its predicate and the information it needs""").replace(
    """A fact is established only by the columns the rule names for it. Other columns, however
they are named, do not establish it. """, "")
_MENU_SEM_OFFERED = """Permitted verdicts:
  pass            the records establish every fact and the rule is satisfied
  fail            the records establish that the rule is violated
  needs_evidence  the records do not establish enough to decide, or they conflict
  unmonitored     the rule cannot apply to this entity

In the evidence field, give the table.column you relied on."""


def _contract_system(variant: str) -> str:
    if variant == CONTRACT_SEM_OFFERED:
        return _SYSTEM_SEM.replace("{verdict_menu}", _MENU_SEM_OFFERED)
    if variant == CONTRACT_SEM_MEANING_OFFERED:
        return _SYSTEM_SEM.replace("Business days exclude", _MEANING_RULE + "Business days exclude").replace(
            "{verdict_menu}", _MENU_SEM_OFFERED)
    if variant == CONTRACT_SEM_FORCED:
        return _SYSTEM_SEM.replace("{verdict_menu}", _MENU_CONTRACT_FORCED)
    if variant == CONTRACT_EXTRACT:
        head = _SYSTEM_CONTRACT.split("Return one line per pair")[0]
        return head + _MENU_CONTRACT_EXTRACT + "\n\nReturn a line for every pair. Do not add commentary, headers, or explanation."
    menu = {CONTRACT_OFFERED: _MENU_CONTRACT_OFFERED, CONTRACT_FORCED: _MENU_CONTRACT_FORCED,
            CONTRACT_EVIDENCE_FIRST: _MENU_CONTRACT_EVIDENCE_FIRST}[variant]
    return _SYSTEM_CONTRACT.replace("{verdict_menu}", menu)


def base_variant(variant: str) -> str:
    """The schema a (possibly paraphrased) condition implements."""
    return variant[:-len("_para")] if variant.endswith("_para") else variant


def system_prompt(firm: Firm, variant: str) -> str:
    if variant in (ABSTAIN_OFFERED_PARA, ABSTAIN_WITHHELD_PARA):
        menu = {ABSTAIN_OFFERED_PARA: _MENU_OFFERED_PARA, ABSTAIN_WITHHELD_PARA: _MENU_WITHHELD_PARA}[variant]
        return _SYSTEM_PARA.format(as_of=firm.as_of, verdict_menu=menu)
    if variant in CONTRACT_VARIANTS:
        return _contract_system(variant)
    if variant == ABSTAIN_OFFERED_NOMATCH:
        nomatch = _SYSTEM.replace("""Two reading rules:
  - Export column names will not match the wording of the obligations. Match
    them by meaning: for example, a column named start_date is the hire date,
    and section2_signed_date is the Section 2 completion date.
  - Reference""", """One reading rule:
  - Reference""")
        assert nomatch != _SYSTEM
        return nomatch.format(as_of=firm.as_of, verdict_menu=_MENU_OFFERED)
    if variant in FACTORIAL:
        return _SYSTEM.format(as_of=firm.as_of, verdict_menu=_menu_factorial(variant))
    if variant == CITE_FIRST:
        return _SYSTEM.format(as_of=firm.as_of, verdict_menu=_MENU_CITE_FIRST)
    menu = {ABSTAIN_OFFERED: _MENU_OFFERED, ABSTAIN_WITHHELD: _MENU_WITHHELD,
            ABSTAIN_REMOVED_ONLY: _MENU_REMOVED_ONLY, ABSTAIN_CLOSED: _MENU_CLOSED}[variant]
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
    # actual_wage_system added 2026-10-03, before Study 3: the same rule needs the
    # employer's actual wage, which only generated firms export. Without it a
    # generated firm's wage pairs were sent without their deciding export
    # (paper, Section 11). The anchor firm has no such export, so its prompts
    # are unchanged.
    "lca-dol": ("hris_roster_export", "lca_export", "cms_case_export", "payroll_register",
                "actual_wage_system"),
    "paf": ("hris_roster_export", "lca_export"),
    "wage-prevailing": ("hris_roster_export", "lca_export", "payroll_register", "actual_wage_system"),
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
            # Never send a prompt without its data: a model asked to judge
            # obligations against a missing export can only abstain or guess,
            # and the reply would be scored as if it had seen the records.
            raise FileNotFoundError(f"source export {kind!r} not found at {p}")
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
        f"# {firm.provenance.get('header', 'Employer')}: {firm.name}\n"
        f"# Evaluation date: {firm.as_of}\n\n"
        f"## Source data exports\n{note}\n{_render_sources(firm, only)}\n"
        f"## Obligations\n\n{_render_obligations(relevant)}\n\n"
        f"## Pairs to evaluate ({len(pair_ids)})\n\n"
        + "\n".join(pair_lines)
    )
