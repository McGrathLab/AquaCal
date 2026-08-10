---
phase: 21-new-feature-documentation-dataset-refresh
plan: 12
subsystem: testing
tags: [pytest, refractive-geometry, manuscript, snells-law]

# Dependency graph
requires: []
provides:
  - "A regression test pinning that refractive_project/refractive_project_batch reduce
    exactly to the pinhole model at n_air=n_water=1.0"
  - "MF-18: measured settlement of whether the n_water=1.0 non-refractive baseline's
    optimality/RMS are trustworthy convergence evidence, routed through MF-09"
  - "The 2026-08-05 folded todo carries a Resolution section; step 3 remains open in
    HANDOFF.json's post-Zenodo batch"
affects: [manuscript-revision, phase-22-release-cut]

# Tech tracking
tech-stack:
  added: []
  patterns: []

key-files:
  created: []
  modified:
    - tests/unit/test_refractive_geometry.py
    - .planning/MANUSCRIPT-FINDINGS.md
    - .planning/todos/pending/2026-08-05-verify-non-refractive-baseline-supports-paper-claims.md

key-decisions:
  - "Left the todo file in pending/ rather than moving to done/, since todo step 3
    (restart the n=1.0 arm from ground truth) remains genuinely open"
  - "No manuscript prose edit recommended beyond what MF-16 already specifies at
    L68/L281 -- MF-18 confirms the cheapest of the todo's four prose options is correct"

patterns-established: []

requirements-completed: [DOCS-05]

# Metrics
duration: 35min
completed: 2026-08-10
---

# Phase 21 Plan 12: n_water=1.0 baseline convergence verification Summary

**Numerically confirmed the refractive projector reduces to the pinhole model at n_air=n_water=1.0 (atol=1e-12), settling that the non-refractive baseline is converged and routing the finding through MF-18/MF-09.**

## Performance

- **Duration:** ~35 min
- **Started:** 2026-08-10 (worktree base `caede4d`)
- **Completed:** 2026-08-10
- **Tasks:** 2/2 completed
- **Files modified:** 3

## Accomplishments

- Settled, by measurement rather than the todo's source-reading argument, whether the
  `n_water=1.0` non-refractive baseline used throughout `main.tex` (lines 68, 268, 270,
  271, 278, 280, 281, 295, including the abstract's headline) is a converged solve.
  **It is.** At `n_air = n_water = 1.0`, `refractive_project`/`refractive_project_batch`
  agree with the plain pinhole projection to `rtol=0, atol=1e-12` for below-interface
  points (tighter than the plan's floor tolerance), on both the vectorized batch path
  and the scalar path. This is pinned by a new committed regression test.
- Found and documented a boundary the todo's source-reading argument did not
  distinguish: `refractive_project`/`refractive_project_batch` return `None`/`NaN` for
  points at or above the interface themselves — the pinhole continuation used in
  production lives one layer up, in `_optim_common._extend_invalid_projections`,
  reached only via the residual function. Recorded as a second test and as prose in
  MF-18 so a future reader checking the projector directly is not confused by the
  un-extended `NaN`.
- Classified the degenerate-observation question: the committed E1 artifact
  (`e1_benchmark_nonrefractive.json`'s `degenerate_observations_at_solution: 14949`)
  is a **single merged counter** for the above-interface and behind-camera kinds — no
  committed field distinguishes them, and this is stated explicitly as an
  instrumentation gap rather than inferred around. A small uncommitted constructed
  case confirmed both mechanisms exist and behave as the source predicts (above-
  interface points get a real pinhole-extended pixel with gradient; genuinely
  behind-camera points stay `NaN` after the extension attempt and fall to the flat
  `INVALID_PROJECTION_PENALTY_PX` penalty).
- Wrote **MF-18** in `.planning/MANUSCRIPT-FINDINGS.md`, recording the measured
  tolerance, the L271 hazard resolution (the 1.376 px RMS citation is no longer
  disqualified evidence, since this arm's kink has zero magnitude), the independent
  tension that `e1_refractive_comparison.py:42` still states E1 carries no accuracy
  claim, and a cross-reference to MF-16 clarifying precisely what its ratio band does
  and does not license.
- Updated **MF-09**'s edit map with an "UPDATE 2026-08-10" section: no new manuscript
  edit is required beyond MF-16's existing band-attachment recommendation at
  L68/L281 — the cheapest of the todo's four prose options turned out to be
  sufficient.
- Left the folded todo in `.planning/todos/pending/` with a `## Resolution (Phase 21,
  plan 12)` section naming MF-18 and explicitly listing todo step 3 (restart the
  `n=1.0` arm from the ground-truth pose) as still open, routed to HANDOFF.json's
  deferred post-Zenodo repair batch.

## Task Commits

1. **Task 1: Verify the n=1 identity numerically and classify the degenerate observations** - `2751021` (test)
2. **Task 2: Write the finding into MANUSCRIPT-FINDINGS.md and route it through MF-09** - `e6b5e35` (docs)

## Files Created/Modified

- `tests/unit/test_refractive_geometry.py` - Added `TestUnitIndexPinholeIdentity` with
  two tests: the pinhole-identity regression (the citable artifact for MF-18) and a
  documentation test for the above-interface `None`/`NaN` boundary.
- `.planning/MANUSCRIPT-FINDINGS.md` - New MF-18 entry; new "UPDATE 2026-08-10" section
  in MF-09's edit map.
- `.planning/todos/pending/2026-08-05-verify-non-refractive-baseline-supports-paper-claims.md` -
  Resolution section added; file left in `pending/` because step 3 is still open.

## Decisions Made

- **No manuscript edit beyond what MF-16 already specifies.** Of the todo's four prose
  options (reframe ratios as bounds; attach the seed band to the abstract; move the
  headline comparison onto a claim E7 can support; do nothing), the measurement shows
  the cheapest — leave L268/L271's convergence framing as-is — is correct, since the
  guard's disqualification does not apply to an arm whose kink has zero magnitude.
- **Todo left in `pending/`, not moved to `done/`.** The plan's acceptance criteria
  permit either; since todo step 3 remains genuinely open (not run by this plan, out
  of scope — requires an E1 run), leaving it in `pending/` with an explicit Resolution
  section more accurately reflects state than a move to `done/` would.
- **The behind-camera vs above-interface classification is reported as an
  instrumentation gap, not guessed around**, per the plan's explicit instruction. A
  small uncommitted script confirmed the mechanism (both paths are real and
  reachable) without attempting to force a classification the committed artifact
  cannot support.

## Deviations from Plan

None - plan executed exactly as written. No source files under `src/` were touched
(`git diff --stat src/` is empty), no E1 run was executed
(`git status --porcelain experiments/results` is empty), and no manuscript file was
edited.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- MF-18 and MF-09's edit map are ready for the manuscript-revision author to consult
  alongside MF-16 when editing L68/L281.
- Todo step 3 (restart the n=1.0 arm from ground truth) is confirmed still open and
  routed to HANDOFF.json's post-Zenodo repair batch — not a blocker for this
  milestone's SoftwareX deadline.
- This plan was explicitly droppable against the 2026-08-21 deadline; it completed
  without needing to be dropped.

---
*Phase: 21-new-feature-documentation-dataset-refresh*
*Completed: 2026-08-10*
