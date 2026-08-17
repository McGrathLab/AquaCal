---
created: 2026-08-17
type: code-quality
priority: medium
source: .planning/phases/24-degeneracy-instrumentation/24-REVIEW.md
resolves_phase: 25
---

# Close the seven open Phase 24 review warnings

The Phase 24 code review raised 12 findings. Both Criticals (CR-01, CR-02) and three
Warnings (WR-01, WR-03, WR-04) were fixed during the phase gate — see the resolution log at
the end of `24-REVIEW.md`. **Seven Warnings remain open: WR-02 and WR-05 through WR-10.**

None falsifies a Phase 24 must-have; verification passed 5/5 with these outstanding. They are
edge-case correctness gaps, one docs gap, and two code-organization notes.

## Why this is worth a todo rather than silence

Phase 27 freezes the library at a single sha and Phase 28 runs the whole suite once, end to
end, on another machine. An edge-case defect that survives into the freeze is expensive in a
way it is not today. Close these before the freeze, not after.

Two are worth checking first, because they touch artifacts rather than style:

- **WR-05** — `docs/guide/benchmarking.md`'s `stages` table omits this phase's two new
  fields. A reader consulting the documented schema will not find what the artifact carries.
- **WR-02** — read the finding before deciding; it was ranked immediately below the three
  that were fixed.

## How to work it

Read the full findings in `.planning/phases/24-degeneracy-instrumentation/24-REVIEW.md`.
Verify each against the code before fixing — of the five findings acted on during the gate,
all five were confirmed genuine, but the review is advisory and a finding is not evidence.

Do not re-derive the inertness or Coleman-Li arguments; the review's "Verified clean" section
records what was checked and cleared, specifically so the next reviewer does not repeat it.
