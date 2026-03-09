---
phase: quick
plan: 1
subsystem: datasets
tags: [synthetic, calibration, notebook, validation]

# Dependency graph
requires: []
provides:
  - "rig_from_calibration() function in public datasets API"
  - "Calibration file support in 02_synthetic_validation notebook"
affects: [tutorials, datasets]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Load real rig geometry from calibration.json for synthetic experiments"

key-files:
  created: []
  modified:
    - src/aquacal/datasets/synthetic.py
    - src/aquacal/datasets/__init__.py
    - tests/synthetic/ground_truth.py
    - docs/tutorials/02_synthetic_validation.ipynb

key-decisions:
  - "rig_from_calibration returns 4-tuple (intrinsics, extrinsics, water_zs, board_config) to include board config from calibration file"
  - "Calibration preset auto-derives experiment depth parameters from mean water_z"

patterns-established:
  - "3-way RIG_SIZE toggle pattern in notebooks: small/large/calibration"

requirements-completed: [QUICK-1]

# Metrics
duration: 6min
completed: 2026-02-23
---

# Quick Task 1: Add Calibration File-Based Synthetic Rig Summary

**New rig_from_calibration() function lets the synthetic validation notebook run all 3 experiments using real rig geometry from calibration.json**

## Performance

- **Duration:** 6 min
- **Started:** 2026-02-23T15:31:39Z
- **Completed:** 2026-02-23T15:37:53Z
- **Tasks:** 2
- **Files modified:** 4

## Accomplishments
- Added `rig_from_calibration()` to the public `aquacal.datasets` API, loading intrinsics/extrinsics/water_zs/board_config from a saved calibration.json
- Updated 02_synthetic_validation.ipynb with a third `RIG_SIZE = "calibration"` option that uses real rig geometry for all 3 experiments
- Existing "small" and "large" presets are completely unchanged in behavior
- All 584 tests pass with no regressions

## Task Commits

Each task was committed atomically:

1. **Task 1: Add rig_from_calibration() to datasets/synthetic.py and export it** - `8743756` (feat)
2. **Task 2: Update 02_synthetic_validation.ipynb to support calibration file rig** - `e849bca` (feat)

## Files Created/Modified
- `src/aquacal/datasets/synthetic.py` - Added `rig_from_calibration()` function with full docstring
- `src/aquacal/datasets/__init__.py` - Added `rig_from_calibration` to imports and `__all__`
- `tests/synthetic/ground_truth.py` - Added `rig_from_calibration` re-export
- `docs/tutorials/02_synthetic_validation.ipynb` - Added calibration file support to all experiment cells

## Decisions Made
- Returns a 4-tuple including BoardConfig (not just 3-tuple like other rig generators) so the notebook can use the real board config too
- Experiment depth parameters are auto-derived from mean water_z rather than hardcoded, making the calibration preset work with any rig geometry

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Feature is complete and ready for use
- User can set `RIG_SIZE = "calibration"` with their calibration.json path to run experiments

---
*Quick Task: 1*
*Completed: 2026-02-23*
