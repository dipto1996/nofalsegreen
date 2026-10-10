# Material moved from Paper 1 for Paper 2 (verbatim, 2026-10-09)

This text appeared in Paper 1 up to commit 10e2e99 (also its public history); it was removed from Paper 1 for use in Paper 2.

## §1 paragraph

**Rule engines make it too.** The commercial engine our rulebook derives from (§4; see
Competing interests) had the same substitution written into deterministic code. Reviews in
June and July 2026 found that two I-9 evaluators skipped employees whose records lacked the deciding
dates, dropping them from monitoring and leaving the dashboard green; that a wage rule let a
salary of record decide whether wages were paid; and that the required-wage rule passed
without the employer's actual-wage benchmark. Each now returns `needs_evidence` (Appendix H).
The engine was written with AI coding assistance and the defects were found in AI-assisted
review, so this shows that the shortcut is easy to build into a system, not how human
engineers behave.

## §8 practitioner questions

**For practitioners evaluating an AI system's compliance verdicts.** The experiments suggest
five questions for counsel and compliance teams that deploy or review such systems:

1. **What does "compliant" mean?** Does the system's `pass` mean the required record was
   found and satisfies the rule, or that compliance is probable? The two differ most when the
   record is missing.
2. **Can the cited source establish the fact?** An onboarding date, a status flag or a salary
   of record can sit beside the required record without being it. A verdict that cites such a
   column has not checked the obligation.
3. **Does the system name what is missing?** A useful "cannot tell" identifies the record to
   request; a system with no such verdict will fill the gap with `pass` or `fail`.
4. **Is the verdict stable when reassuring but irrelevant fields are added?** If adding a
   "Complete" flag turns gaps into passes, the system is reading the flag, not the record.
5. **Does a safeguard keep the useful decisions?** Refusing everything has no false greens. A
   safeguard is worth adopting only if it removes unsupported decisions while keeping correct
   ones and limiting the extra review it creates.


## Appendix H: The same error in a rule engine

The defects below were found and fixed in the private repository of the engine that the
rulebook comes from (Settle AI Inc.), between 2026-06-28 and 2026-07-14. Commit identifiers
are given for the record; the repository is not public. In each case the engine returned a
verdict that the available record could not support.

| Defect | What the code did | Fix |
|---|---|---|
| Silent skip, I-9 Section 2 and reverification | An evaluator skipped an employee whose record lacked the deciding dates, so the employee left monitoring and the dashboard stayed green | Emit a visible `needs_evidence` finding (commits `16de553c`, `407eb438`; an internal review note calls it "a verified production defect") |
| Salary of record as wages paid | The material-change wage check returned pass or fail from the HR salary of record | Retired: a salary of record "proves nothing about wages paid"; it never passes alone (commits `1b181e00`, `4b2605ec`) |
| Required wage without the actual-wage limb | The greater-of rule passed on the prevailing wage alone when the employer's actual-wage benchmark was unknown | The would-be pass becomes `needs_evidence` (commit `55c5e6fb`) |
| Fabricated provenance | Wage cohorts were stamped with a prevailing-wage source and an "ok" document status that no input supplied | Stored as unknown, so the rules ask for the record (commit `c47a945b`) |

Because the repository is private, the logic of each defect is restated below as pseudocode
(paraphrased, not copied), so that the claim can be checked against the description.

```text
# silent skip (I-9 Section 2; reverification)
before: for worker in workers:
            record = i9_records.get(worker)
            if record is None or record.section2_date is None: continue   # worker leaves monitoring
            emit(check(record))
after:      if record is None or record.section2_date is None:
                emit(needs_evidence(worker, missing="Section 2 date")); continue

# salary of record as wages paid
before: verdict = PASS if roster.salary >= lca.required_wage else FAIL
after:  verdict = NEEDS_EVIDENCE unless payroll.periods cover the span; salary alone never passes

# greater-of rule without the actual-wage limb
before: required = lca.prevailing_wage; verdict = PASS if paid >= required else FAIL
after:  if actual_wage_benchmark is None and paid >= lca.prevailing_wage: verdict = NEEDS_EVIDENCE
        else: required = max(lca.prevailing_wage, actual_wage_benchmark); ...

# fabricated provenance
before: cohort.pw_source = "OES"; cohort.pw_doc_status = "ok"
after:  cohort.pw_source = mapped_column or "unknown"   # "unknown" is read as an evidence request
```

The engine's rules were written with AI coding assistance, and the defects were found by
AI-assisted review (Codex), so the table is not evidence about human engineers. It shows
that a system built to fill a dashboard acquires these substitutions easily, and that each
fix is the same: return `needs_evidence` when the record that decides the obligation is
absent.

## Appendix I: AI pilot runs of the expert protocol

The expert protocol is a workbook of 50 items and 8 statements (`docs/expert_review_v3/`,
built by `scripts/build_expert_kit_v3.py`). Its 50 items are:

- 20 unassessable pairs on proxy-column firms;
- 10 unassessable pairs on plain firms;
- 20 decidable violations and controls, some on the legal boundary.

Each item shows the employer's records inline, and the reviewer answers blind to the
construction label. No human expert has completed it.

**What was run.** Two AI systems completed it as a pilot, at the author's request:

- Claude (Anthropic) completed version 2. Its own answers flagged five defects in the
  workbook, all fixed in version 3: identifiers repeated across firms, two items with
  identical records, no stated rule on status extensions, no holiday calendar, and no wage
  item that could fail.
- Codex (OpenAI) completed version 3.

Both are scored against their own version's labels (`scripts/score_ai_pilot.py`,
`docs/ai_pilot_review/results.json`).

**Results.** Each agreed with all 50 labels:

- every proxy-column item was answered `needs_evidence`;
- every planted violation was answered `fail`;
- every control was answered `pass`.

On the evidence statements, both strongly disagreed that an I-9 status flag, an onboarding
date or a future authorisation end date shows I-9 timeliness, and both strongly disagreed
that an LCA's wage shows the wages paid. Both strongly agreed that a missing record should be
reported as needing evidence. Claude disagreed, and Codex strongly disagreed, that a salary of
record shows the required wage was paid and that an HR status field can mark an item compliant
for triage.

**What this shows.** These runs are not expert validation:

- **Not blind to the study.** Both systems worked with the author on this project, and Codex
  had reviewed earlier drafts of the paper, so neither was blind to the evidence standard.
- **Correlated errors.** Systems of the same kind as the models under test may share their
  errors.

The runs show that the protocol can be completed as designed, and that a careful reader of
the standard reproduces the labels. Whether practitioners accept that standard remains open
(§9).

