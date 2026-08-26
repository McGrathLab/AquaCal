---
created: 2026-08-26T00:00:00.000Z
title: GSD's `check.decision-coverage-plan` returns "no trackable decisions" against a CONTEXT.md holding 37 of them — it does not recognise the dotted-phase `D-29.2-NN` ID format
area: tooling
resolves_phase: 30
files: []
---

## What happened

During `/gsd-plan-phase 29.2`, the planner ran `check.decision-coverage-plan` against
`.planning/phases/29.2-merge-release-and-publish/29.2-CONTEXT.md`. The handler returned
**`"no trackable decisions"`**. That CONTEXT.md contains **37** decision IDs, every one of the form
`D-29.2-NN` (plus the `02b` / `02c` / `28b` suffixed variants).

The gate did not fail. It did not warn. It reported nothing to count and passed.

## Why this matters more than it looks

**This is the second time this project has been misled by the same gate.** `STATE.md` already
records the Phase 28 instance:

> Decision coverage gate: **2/2 passed — this is a NARROW pass.** The gate counts only IDs in the
> hyphenated `D-NN` form, so 2/2 means **`D-28` and `D-12` only**. […] Do not read `2/2` as "all
> decisions verified".

Phase 28's failure was a *partial* count that looked complete. Phase 29.2's is a *total* miss that
looks like a non-applicable check. The second shape is worse: `2/2` at least invites the question
"two of what?", whereas "no trackable decisions" reads as "this phase has no decisions to track"
and stops the reader.

## What it cost here

The planner ran an equivalent audit by hand and found **D-29.2-01 and D-29.2-34 covered in
substance but with no traceable ID citation**; plans 02, 05 and 06 were patched. Had the manual
audit not been run, two locked decisions would have entered execution unciteable — on a phase whose
steps include five one-way doors.

## What would fix it

The ID regex needs to accept a dotted phase segment. Currently it matches `D-<digits>-<digits>`;
it needs `D-<digits>(\.<digits>)?-<digits>` at minimum, and ideally a trailing lowercase suffix
(`D-29.2-02b`). Inserted phases (`29.1`, `29.2`) are a normal GSD feature — `/gsd-phase --insert`
creates them — so any project that uses insertion silently loses this gate.

**Do not "fix" it by renumbering decisions to the hyphenated form.** STATE.md already rules on this
for Phase 28's IDs: they are cited across research, plans and prior-phase docs and *must not* be
renumbered to make a gate broader. The gate is what should change.

## Evidence

- `.planning/STATE.md` § *Phase 28 planning gates (2026-08-24)* — the prior instance, already ruled on
- `.planning/phases/29.2-merge-release-and-publish/29.2-CONTEXT.md` — 37 `D-29.2-NN` IDs
- `.planning/phases/29.2-merge-release-and-publish/29.2-01-PLAN.md` … `-08-PLAN.md` — the manual
  audit's output; plans 02/05/06 carry the patched citations
