---
phase: 18-documentation-corrections-stage-model-reconciliation
plan: 07
subsystem: docs
tags: [vocabulary, stage-model, docstrings, config-template]

# Dependency graph
requires:
  - phase: 18-documentation-corrections-stage-model-reconciliation
    provides: 18-02-SUMMARY.md (confirmed vocabulary contract)
provides:
  - Three-stage-model docstrings/comments across the remaining src/ surfaces
    not owned by plan 18-06 (schema.py, cli.py, example_config.yaml,
    refinement.py, _optim_common.py, _observability.py, conditioning.py,
    intrinsics.py) plus the two tests/synthetic/ helper files
affects: [18-08]

# Tech tracking
tech-stack:
  added: []
  patterns: []

key-files:
  created: []
  modified:
    - src/aquacal/config/schema.py
    - src/aquacal/cli.py
    - src/aquacal/config/example_config.yaml
    - src/aquacal/calibration/refinement.py
    - src/aquacal/calibration/_optim_common.py
    - src/aquacal/calibration/_observability.py
    - src/aquacal/validation/conditioning.py
    - src/aquacal/calibration/intrinsics.py
    - tests/synthetic/experiment_helpers.py
    - tests/synthetic/experiments.py

key-decisions:
  - "Used the D-05 revised prose label 'Stage 3's second pass, with intrinsics unlocked' verbatim per 18-02-SUMMARY.md, not the earlier inferred 'optional intrinsic pass'"
  - "Used 'Auxiliary camera registration' with no stage number for refine_auxiliary_intrinsics per D-23, never 'Stage 3b'/'Stage 4b'"
  - "Fixed one stray Stage 3/4 comment in intrinsics.py not listed in the plan's interfaces block (Rule 2 deviation) — required for the phase-level combined grep guard to pass"

patterns-established: []

requirements-completed: [DOCS-06]

# Metrics
duration: ~35min
completed: 2026-07-24
---

# Phase 18 Plan 07: Correct Remaining Code-Side Stage-Model Docstrings Summary

**Rewrote every remaining "Stage 4"/"Stage 4b" docstring, comment, and template string in `src/` (outside `pipeline.py`, owned by plan 18-06) and two `tests/synthetic/` helper files onto the confirmed three-stage model, with zero numeric, control-flow, or signature changes.**

## Performance

- **Duration:** ~35 min
- **Started:** 2026-07-24
- **Completed:** 2026-07-24
- **Tasks:** 2 (plus one Rule 2 deviation commit)
- **Files modified:** 10

## Accomplishments

- Corrected nine stage references in `schema.py`'s `CalibrationConfig` docstring/comments (`max_calibration_frames`, `refine_intrinsics`, `auxiliary_cameras`, `refine_auxiliary_intrinsics`, `reject_outlier_frames`, `save_stage_calibrations`, plus the inline field comment and one additional `CameraCalibration.is_auxiliary` docstring site found by the full-file grep)
- Updated `aquacal init`'s two generated-config comment strings (`cli.py`) and the matching three comments in the shipped `example_config.yaml`, keeping both copies in sync
- Corrected `refinement.py`'s module docstring and `joint_refinement`'s docstring, `_optim_common.py`'s module docstring, and the `stage:` enumeration Args entries in `_observability.py` and `conditioning.py` (now listing `stage3_intrinsic_pass`, matching what `pipeline.py` passes after plan 18-06)
- Updated four `tests/synthetic/` helper prose/print-string sites in `experiment_helpers.py` and `experiments.py`
- Found and fixed one additional stray "Stage 3/4" comment in `intrinsics.py` that the plan's own interfaces block missed, closing the gap needed for the phase-level combined grep guard

## Task Commits

Each task was committed atomically:

1. **Task 1: Correct the user-facing config surfaces** - `8ef1556` - schema.py, cli.py, example_config.yaml
2. **Task 2: Correct the remaining module and stage-tag docstrings** - `6d6fdbc` - refinement.py, _optim_common.py, _observability.py, conditioning.py, tests/synthetic/experiment_helpers.py, tests/synthetic/experiments.py
3. **Deviation (Rule 2): fix stray Stage 3/4 comment in intrinsics.py** - `050a547`

## Files Created/Modified

- `src/aquacal/config/schema.py` - nine `CalibrationConfig` docstring/comment sites plus one `CameraCalibration.is_auxiliary` docstring site corrected to the three-stage model
- `src/aquacal/cli.py` - `aquacal init` generated-config comments corrected
- `src/aquacal/config/example_config.yaml` - shipped example config comments corrected to match `cli.py`
- `src/aquacal/calibration/refinement.py` - module docstring and `joint_refinement` docstring corrected
- `src/aquacal/calibration/_optim_common.py` - module docstring corrected
- `src/aquacal/calibration/_observability.py` - `stage:` Args enumeration now lists `stage3_intrinsic_pass`
- `src/aquacal/validation/conditioning.py` - `stage:` Args enumeration now lists `stage3_intrinsic_pass`
- `src/aquacal/calibration/intrinsics.py` - one stray comment corrected (deviation, see below)
- `tests/synthetic/experiment_helpers.py` - docstring, section comment, and print string corrected
- `tests/synthetic/experiments.py` - plot annotation string corrected

## Decisions Made

- Followed the 18-02 vocabulary contract exactly: "Stage 3's second pass, with intrinsics unlocked" for the ex-Stage-4 prose label, "Auxiliary camera registration" (no stage number) for `refine_auxiliary_intrinsics`, and `stage3_intrinsic_pass` for the machine stage tag in docstring enumerations.
- For `save_stage_calibrations`, replaced the old prose ("Stage 3, the post-outlier-rejection re-run, and Stage 4 when enabled") with the literal on-disk tag names (`stage3`, `stage3_rerun`, `stage3_intrinsic_pass`) per the plan's explicit instruction, since this docstring describes files that appear on disk.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing critical functionality/accuracy] Stray "Stage 3/4" comment in `intrinsics.py` not in the plan's interfaces list**

- **Found during:** Task 2, running the phase-level combined grep guard (`grep -rnE '"stage4"|Stage 4|Stage 4b|Stages 3-4|Stage 3/4' src/ --include=*.py --include=*.yaml`) as specified in the plan's acceptance criteria.
- **Issue:** `src/aquacal/calibration/intrinsics.py:410` contained a comment referencing "the joint bundle adjustment (Stage 3/4)". This site was not listed in the plan's `<interfaces>` block, which claimed to be "the complete list" per a full-tree grep, and the file is not in this plan's `files_modified` frontmatter. It is also not owned by plan 18-06 (which owns only `pipeline.py` and six `tests/unit/` files).
- **Fix:** Changed "the joint bundle adjustment (Stage 3/4)" to "the joint bundle adjustment (Stage 3)" — comment-only, no executable line touched.
- **Files modified:** `src/aquacal/calibration/intrinsics.py`
- **Commit:** `050a547`

## Verification Results

- `python -m pytest tests/unit/test_cli.py tests/unit/test_schema.py -q` — 61 passed
- `python -m pytest tests/ -m "not slow" -q` — 775 passed, 31 deselected
- `ruff check src/ tests/synthetic/` — all checks passed
- `python -c "import yaml,pathlib; yaml.safe_load(...)"` on `example_config.yaml` — parses cleanly
- `grep -cE "Stage 4|Stage 4b|Stages 3-4|Stage 3/4" src/aquacal/config/schema.py` → 0
- `grep -cE "Stage 4|Stage 4b" src/aquacal/cli.py` → 0
- `grep -cE "Stage 4|Stage 4b|Stage 3/4" src/aquacal/config/example_config.yaml` → 0
- `grep -c "stage3_intrinsic_pass" src/aquacal/config/schema.py` → 1
- `grep -cE "Stage 3b|Stage 4b" src/aquacal/config/schema.py` → 0
- `grep -c "Auxiliary camera registration" src/aquacal/config/schema.py` → 2
- `grep -c "refine_intrinsics: bool = False" src/aquacal/config/schema.py` → 1
- `grep -c "def joint_refinement" src/aquacal/calibration/refinement.py` → 1 (unchanged)
- `test -f src/aquacal/calibration/refinement.py` → exists (module not renamed)
- **Combined phase-level grep guard** (`grep -rnE '"stage4"|Stage 4|Stage 4b|Stages 3-4|Stage 3/4' src/ --include=*.py --include=*.yaml`), run within this worktree (which does not contain plan 18-06's `pipeline.py` changes): only `src/aquacal/calibration/pipeline.py` still matches, and every match there is a site plan 18-06 owns and is renaming in its own worktree. Zero matches remain anywhere in this plan's scope. This criterion should be re-run once both plans merge to `main` to confirm the combined tree is fully clean.
- `grep -crE "Stage 4" tests/synthetic/` → 0

## Issues Encountered

None beyond the one deviation documented above.

## User Setup Required

None.

## Next Phase Readiness

Plan 18-07 is complete. The combined `src/`-wide "Stage 4" grep guard depends on plan 18-06 (which owns `pipeline.py`) also landing — once both plans merge, re-running `grep -rnE '"stage4"|Stage 4|Stage 4b|Stages 3-4|Stage 3/4' src/ --include=*.py --include=*.yaml` should return zero matches. No blockers for plan 18-08.

---
*Phase: 18-documentation-corrections-stage-model-reconciliation*
*Completed: 2026-07-24*
