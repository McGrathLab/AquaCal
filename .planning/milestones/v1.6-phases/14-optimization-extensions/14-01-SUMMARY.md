---
phase: 14-optimization-extensions
plan: 01
subsystem: api
tags: [bundle-adjustment, scipy, sparse-jacobian, intrinsics, robust-loss, refraction]

requires:
  - phase: 13-core-refinement
    provides: refine_calibration() with extrinsics + water_z optimization
provides:
  - Extended refine_calibration() with optional intrinsics refinement (fx/fy/cx/cy)
  - Robust loss function support (Huber/Cauchy) via scipy native API
  - 2-DOF reference camera tilt optimization (normal_fixed=False)
  - Intrinsic drift warning logging
  - Configurable intrinsic bounds (intrinsics_bound_pct)
affects: [14-02, 15-validation]

tech-stack:
  added: []
  patterns: [local pack/unpack/sparsity/bounds extension matching _optim_common layout]

key-files:
  created: []
  modified:
    - src/aquacal/calibration/point_refinement.py

key-decisions:
  - "Local _pack/_unpack/_sparsity/_bounds extended (not reusing _optim_common directly) because point refinement has no board poses"
  - "Intrinsic bounds use configurable percentage (intrinsics_bound_pct) rather than fixed 50%/200% range from _optim_common"
  - "Loss validation checks against {'linear', 'huber', 'cauchy'} before other validation to fail fast"
  - "Auto-scale max_nfev to 200*n_params when intrinsics enabled and caller didn't set it"
  - "Intrinsic drift warning threshold at 5% of initial value"

patterns-established:
  - "Extended parameter layout: [tilt(2)] + extrinsics(6*(n-1)) + water_z(1) + [intrinsics(4*n)]"

requirements-completed: [OPT-02, OPT-03]

duration: 5min
completed: 2026-02-28
---

# Plan 14-01: Optimization Extensions Summary

**Extended refine_calibration() with optional intrinsics refinement, Huber/Cauchy robust loss, and 2-DOF reference camera tilt**

## Performance

- **Duration:** 5 min
- **Tasks:** 1
- **Files modified:** 1

## Accomplishments
- refine_calibration() now accepts refine_intrinsics, intrinsics_bound_pct, normal_fixed, loss, and f_scale keyword arguments
- All 18 existing tests pass unchanged (full backward compatibility)
- Invalid loss values raise ValueError with helpful message
- _pack/_unpack/_sparsity/_bounds functions support extended parameter layout
- Intrinsic drift warning logged when any param shifts >5% from initial
- Auto-scaled max_nfev when intrinsics enabled and caller didn't set it

## Task Commits

1. **Task 1: Extend refine_calibration signature and refactor helpers** - `6f98e17` (feat)

## Files Created/Modified
- `src/aquacal/calibration/point_refinement.py` - Extended with intrinsics, loss, and tilt support

## Decisions Made
- Used local pack/unpack/sparsity/bounds functions rather than _optim_common, since point refinement has no board poses and a different residual structure
- Intrinsic bounds use configurable percentage rather than the wide 50%/200% range in _optim_common
- CalibrationMetadata is a frozen dataclass with fixed fields, so extension info is not stored in metadata (deferred to Phase 15 RefinementResult)

## Deviations from Plan
None - plan executed exactly as written.

## Issues Encountered
None.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Implementation ready for Plan 14-02 testing
- All new parameters have backward-compatible defaults

---
*Phase: 14-optimization-extensions*
*Completed: 2026-02-28*
