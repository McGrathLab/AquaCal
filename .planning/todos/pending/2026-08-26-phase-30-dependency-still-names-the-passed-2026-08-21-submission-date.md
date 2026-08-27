---
created: 2026-08-26T00:00:00.000Z
title: Roadmap hygiene — Phase 30's dependency still names the passed 2026-08-21 submission date, the same defect Phase 29's criterion 6 was amended away from on 2026-08-25
area: planning
resolves_phase: 30
files:
  - .planning/ROADMAP.md
---

## The defect

`.planning/ROADMAP.md` § **Phase 30: Post-Submission Reconciliation** reads:

> **Goal**: After the **2026-08-21** SoftwareX submission, …
> **Depends on**: Phase 29, and the **2026-08-21** SoftwareX submission (calendar dependency — this
> phase does not start before the submission ships)

**That date has passed.** The re-freeze and re-run were still in flight when it went by; the
production run at `rerun-freeze-02` did not finish until 2026-08-25.

## Why this is not a nitpick

**Phase 29's success criterion 6 carried the identical defect and was amended for exactly this
reason on 2026-08-25**, by the author:

> This criterion read *"before the 2026-08-21 submission"*. That date passed while the re-freeze and
> re-run were in flight, which made the criterion ungradeable as written… The criterion is therefore
> **re-scoped from a date to the event it always meant** — publication must precede submission,
> whenever submission happens. **Pinning it to a calendar date is what broke it once and would break
> it again on any further slip.**

Phase 30 will mis-gate the same way, for the same reason, until it gets the same treatment. Phase
28's `28-RUN-RECORD.md` flagged the Phase 29 instance upward rather than silently reinterpreting it;
this todo does the same for the Phase 30 instance.

## The fix

Re-scope Phase 30's dependency from a **calendar date** to the **submission event** — *"this phase
does not start before the SoftwareX submission ships"* — and drop the date from the goal sentence.
Nothing else about Phase 30 changes: POST-01, POST-03 and POST-04, and all three success criteria,
are untouched.

**Not done in Phase 29**, because amending a phase's dependency is the author's ruling, exactly as
the 2026-08-25 amendment to criterion 6 was. Filed rather than applied.

## Related

Phase 29.2 (inserted 2026-08-26) already sits between Phase 29 and Phase 30 precisely because of an
ordering loop this same date-pinning obscured: Phase 30 waits for submission; submission waits for
Record B's publication (RUN-05); Record B's publication waits for `2.1.0` to exist; `2.1.0` waits
for the release cut. **The release therefore has to land before submission, which puts it before
Phase 30 begins, not inside it.**

## Evidence

- `.planning/ROADMAP.md` § *Phase 29* success criterion 6, **AMENDED 2026-08-25**
- `.planning/ROADMAP.md` § *Phase 30* and § *Phase 29.2*
- `.planning/phases/28-full-suite-production-run/28-RUN-RECORD.md` § *Open items handed forward*,
  item 3 — where the Phase 29 instance was first flagged upward
- `.planning/phases/29-gate-verification-results-commit/29-PHASE-RECORD.md` § *Open items handed
  forward*, item 7
