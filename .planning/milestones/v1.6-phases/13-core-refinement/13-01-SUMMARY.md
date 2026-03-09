---
phase: 13-core-refinement
plan: 01
subsystem: api
tags: [bundle-adjustment, scipy, sparse-jacobian, refraction, point-correspondence]

# Dependency graph
requires:
  - phase: 12-optim-common
    provides: make_sparse_jacobian_func for sparse Jacobian construction
  - phase: core
    provides: refractive_project_batch, Camera, Interface, CameraExtrinsics
provides:
  - PointCorrespondence dataclass in config/schema.py
  - refine_calibration() function in calibration/point_refinement.py
  - Public API: from aquacal import refine_calibration, PointCorrespondence
affects: [14-robust-loss, 15-refinement-result]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - Local _pack/_unpack_refine_params functions for point-correspondence-specific parameter layout (no board poses)
    - Zero-weight soft-disable pattern for correspondences
    - Non-convergence logging without raising exception (return best-effort result)
    - Per-camera RMS computed from interleaved [x, y] residual pairs

key-files:
  created:
    - src/aquacal/calibration/point_refinement.py
  modified:
    - src/aquacal/config/schema.py
    - src/aquacal/__init__.py
    - src/aquacal/calibration/__init__.py

key-decisions:
  - "reference_camera = first in sorted camera_order, consistent with existing pipeline convention"
  - "minimum 10 active correspondences threshold to prevent ill-conditioned bundle adjustment"
  - "non-convergence logs warning but returns best-effort result — Phase 15 RefinementResult will expose status explicitly"
  - "InsufficientDataError (not ValueError) when active correspondence count too low — matches existing error hierarchy"

patterns-established:
  - "Point correspondence bundle adjustment: only extrinsics + water_z optimized; intrinsics fixed"
  - "Use make_sparse_jacobian_func from _optim_common for sparse Jacobian reuse pattern"

requirements-completed: [API-01, API-03, OPT-01]

# Metrics
duration: 6min
completed: 2026-02-28
---

# Phase 13 Plan 01: Core Refinement Summary

**PointCorrespondence dataclass and refine_calibration() with sparse bundle adjustment over extrinsics and water_z using 3D-to-2D point correspondences**

## Performance

- **Duration:** 6 min
- **Started:** 2026-02-28T18:06:21Z
- **Completed:** 2026-02-28T18:12:15Z
- **Tasks:** 3
- **Files modified:** 4

## Accomplishments
- PointCorrespondence dataclass added to config/schema.py and exported from public API
- refine_calibration() implemented with full input validation, sparse Jacobian, and non-convergence handling
- Public API: `from aquacal import refine_calibration, PointCorrespondence` works with no errors
- Existing Stage 4 tests (13 tests) pass with no regressions

## Task Commits

Each task was committed atomically:

1. **Task 1: Define PointCorrespondence dataclass and add to public API** - `52c0ceb` (feat)
2. **Task 2: Implement refine_calibration() with point correspondence bundle adjustment** - `929d64c` (feat)
3. **Task 3: Wire refine_calibration into public API and calibration package** - `3832637` (feat)

**Plan metadata:** TBD (docs: complete plan)

## Files Created/Modified
- `src/aquacal/config/schema.py` - Added PointCorrespondence dataclass (after Detection, before FrameDetections)
- `src/aquacal/calibration/point_refinement.py` - New file: refine_calibration() with full implementation
- `src/aquacal/__init__.py` - Added PointCorrespondence and refine_calibration to imports and __all__
- `src/aquacal/calibration/__init__.py` - Added refine_calibration under # point refinement section

## Decisions Made
- Reference camera = first in sorted camera order (consistent with existing pipeline)
- Minimum 10 active correspondences required for stable optimization (after zero-weight filtering)
- Non-convergence returns best-effort result with a warning log — no ConvergenceError raised
- Local _pack/_unpack functions rather than modifying _optim_common (which is board-pose-specific)

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
- Ruff pre-commit hook auto-fixed minor style issues in point_refinement.py (line length, whitespace). Re-staged and committed cleanly on second attempt.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- refine_calibration() is fully functional and importable from public API
- Ready for Phase 14: add robust loss function support (huber/soft_l1) to refine_calibration()
- Ready for Phase 15: wrap in RefinementResult to expose convergence status programmatically

---
*Phase: 13-core-refinement*
*Completed: 2026-02-28*

## Self-Check: PASSED

- FOUND: src/aquacal/calibration/point_refinement.py
- FOUND: src/aquacal/config/schema.py
- FOUND: .planning/phases/13-core-refinement/13-01-SUMMARY.md
- FOUND commit 52c0ceb (Task 1)
- FOUND commit 929d64c (Task 2)
- FOUND commit 3832637 (Task 3)
