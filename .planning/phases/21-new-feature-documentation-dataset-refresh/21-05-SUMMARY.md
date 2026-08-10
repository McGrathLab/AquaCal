---
phase: 21-new-feature-documentation-dataset-refresh
plan: 05
subsystem: docs
tags: [requirements, roadmap, dependency-pin, opencv, traceability]

# Dependency graph
requires:
  - phase: 21-new-feature-documentation-dataset-refresh
    provides: CONTEXT.md decisions D-01/D-02/D-05/D-17/D-18/D-19 and the folded 2026-02-24/2026-08-05 todos
provides:
  - Reworded DOCS-05 requirement text (drops calc-index, names benchmarking.md and the CLI tutorial)
  - Reworded DATA-02 acceptance text (points at the CLI tutorial and e2_real_rig.py, not "the notebook")
  - Reworded DATA-03 text recording the real-data narration's move to the CLI tutorial
  - DATA-01 amendment note recording the initial_water_z scalar resolution
  - Confirmation that pyproject.toml and requirements.txt already carry `opencv-python>=4.6,<5.0`
  - Confirmation that ROADMAP.md's Phase 21 Requirements line already lists DATA-01b
affects: [21-06, 21-07, 21-08, 21-09, 21-10, 21-11, 21-12]

# Tech tracking
tech-stack:
  added: []
  patterns: []

key-files:
  created: []
  modified:
    - .planning/REQUIREMENTS.md

key-decisions:
  - "ROADMAP.md's Phase 21 Requirements line already contained DATA-01b (`DOCS-05, DATA-01, DATA-01a, DATA-01b, DATA-02, DATA-03`) — the plan's premise that it was omitted is stale; no edit made to ROADMAP.md, consistent with the parallel_execution guard restricting this plan to content corrections only."
  - "pyproject.toml:33 and requirements.txt:10 already read `opencv-python>=4.6,<5.0` — the folded todo 2026-08-05-pin-opencv-below-5-0.md was already satisfied before this plan ran; CONTEXT.md's 'unbounded above' framing was stale, matching 21-PATTERNS.md's note."

requirements-completed: [DOCS-05, DATA-02, DATA-03]

# Metrics
duration: 12min
completed: 2026-08-10
---

# Phase 21 Plan 05: Requirements Reconciliation & OpenCV Pin Audit Summary

**Reworded DOCS-05/DATA-02/DATA-03 requirement text with dated amendment notes to match what Phase 21 actually ships, and confirmed the OpenCV `<5.0` upper bound and the ROADMAP's DATA-01b listing were already in place.**

## Performance

- **Duration:** 12 min
- **Started:** 2026-08-10T15:27:00Z (approx)
- **Completed:** 2026-08-10T15:39:52Z
- **Tasks:** 2 (1 committed, 1 verification-only with no changes needed)
- **Files modified:** 1 (`.planning/REQUIREMENTS.md`)

## Accomplishments

- DOCS-05 no longer promises `aquacal calc-index` (Phase 20's deferred INDEX-02 deliverable); it now names `docs/guide/benchmarking.md` and `docs/tutorials/03_cli_walkthrough.md` as the deliverables this phase ships, with a dated amendment note explaining the removal (D-01).
- DATA-02's acceptance text no longer references "the path the notebook resolves" (which goes vacuous once D-18 deletes notebook 01's Zenodo branch); it now names the CLI tutorial and `experiments/e2_real_rig.py` as the actual consumers, with an amendment note (D-18).
- DATA-03's text records that the real-data narration originally anticipated for the notebooks moves to the CLI tutorial, and that both notebooks become fast, synthetic-only, with an amendment note (D-17/D-19).
- DATA-01 carries a new note recording the folded 2026-02-24 todo's resolution: the shipped archive config used a scalar `initial_water_z`, not the deprecated `initial_distances` form.
- Verified (no edit needed) that `pyproject.toml` and `requirements.txt` already pin `opencv-python>=4.6,<5.0`, and that the installed `cv2.__version__` (4.13.0, AquaCal conda env) satisfies the pin.
- Verified (no edit needed) that ROADMAP.md's Phase 21 `**Requirements**:` line already lists `DATA-01b` alongside the other five IDs, matching the traceability table.
- Audited the repo for other unbounded OpenCV constraints: none found. No `environment.yml` exists in the repo; no `.github/workflows/*.yml` references `opencv`; `[project.optional-dependencies]` extras (`dev`, `docs`, `bench`) carry no `opencv` entry. `example_config.yaml:10` mentions "pre-OpenCV 4.6" only in a comment, not a version constraint.

## Task Commits

Each task was committed atomically:

1. **Task 1: Reword DOCS-05, DATA-02, DATA-03 and add DATA-01b to the ROADMAP phase entry** - `de35d4a` (docs)
2. **Task 2: Verify the OpenCV upper bound** - no commit (verification-only; both files already satisfied the pin, `git diff --stat pyproject.toml requirements.txt` showed 0 changed lines)

**Plan metadata:** commit pending (this SUMMARY + REQUIREMENTS.md/ROADMAP.md/REQUIREMENTS.md final commit)

## Files Created/Modified

- `.planning/REQUIREMENTS.md` - DOCS-05, DATA-01, DATA-02, DATA-03 entries reworded/annotated with dated amendment notes; no checkbox states changed

## Decisions Made

- **ROADMAP.md left untouched.** Task 1's action step called for editing ROADMAP.md's Phase 21 `**Requirements**:` line to add `DATA-01b`, but that line already read `DOCS-05, DATA-01, DATA-01a, DATA-01b, DATA-02, DATA-03` (confirmed via `grep -n "### Phase 21:" -A 20 .planning/ROADMAP.md` and `grep -n "DATA-01b" .planning/ROADMAP.md`, both showing it present at line 561). Since the `<verify>` automated check (`assert 'DATA-01b' in rd[j:j+1200]`) and all acceptance criteria for Task 1 passed without any ROADMAP.md edit, and the `parallel_execution` guard for this plan restricts ROADMAP.md changes to substantive content corrections only, no edit was made. This is a stale premise in the plan/context, not a defect requiring a fix — documented here per the deviation-tracking convention rather than as a Rule 1/2/3 auto-fix, since nothing was broken.
- **pyproject.toml / requirements.txt left untouched.** Task 2's action step is explicitly "a verification task first and an edit task only if verification fails." Both files already contained the exact required string `opencv-python>=4.6,<5.0` (`pyproject.toml:33`, `requirements.txt:10`), confirmed by grep before any edit was attempted. Per the task's own instructions, when both already match, "change nothing" and record the folded todo's status in the SUMMARY — done here.

## Deviations from Plan

None - plan executed exactly as written. Both "no edit needed" outcomes above are explicitly the paths the plan's own task text anticipates ("verification task first, edit task only if verification fails"; "the omission is a roadmap bug" — but no omission was found), not deviations from stated instructions.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- `.planning/REQUIREMENTS.md`'s DOCS-05/DATA-01/DATA-02/DATA-03 text now matches what Phase 21 ships, with an auditable amendment trail for downstream plans (21-06 through 21-12) and for phase-close verification.
- The OpenCV upper bound is confirmed live in both dependency declarations and binds against the installed `cv2==4.13.0` in the AquaCal conda env — no supply-chain risk (T-21-05-01) remains open.
- ROADMAP.md's Phase 21 requirement list already matches the traceability table; no follow-up needed.
- No blockers for subsequent Phase 21 plans.

---
*Phase: 21-new-feature-documentation-dataset-refresh*
*Completed: 2026-08-10*

## Self-Check: PASSED

- FOUND: `.planning/phases/21-new-feature-documentation-dataset-refresh/21-05-SUMMARY.md`
- FOUND: commit `de35d4a` in `git log --oneline --all`
