---
phase: 17-per-camera-interface-ablation-mode
plan: 05
subsystem: testing
tags: [testing, regression, bit-exactness, recovery, water_z, ablation, bugfix]

# Dependency graph
requires:
  - phase: 17-per-camera-interface-ablation-mode
    provides: shared_interface-threaded optimizers + pipeline (plans 17-01..17-04)
provides:
  - IFACE-05 safety net: shared-mode packing/structure bit-identity + shared-mode end-to-end determinism + equal-seed per-camera recovery
  - fix for a per-camera cost-function misalignment bug (compute_residuals) that broke the whole ablation
affects: []

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "the shared path is locked at both the unit (packing) and end-to-end (Stage 3) layers"

key-files:
  created:
    - tests/synthetic/test_per_camera_interface.py
  modified:
    - src/aquacal/calibration/_optim_common.py
    - src/aquacal/calibration/interface_estimation.py
    - src/aquacal/calibration/refinement.py
    - tests/unit/test_optim_common.py
    - tests/unit/test_interface_estimation.py

key-decisions:
  - "[Rule 1 - Bug] compute_residuals must receive shared_interface and pass it to unpack_params; plan 17-01's assumption that it needed no change was wrong and left per-camera mode reading a single water_z and misaligning every later parameter block"
  - "Recovery test uses the noiseless 'ideal' scenario so per-camera mode collapses to the shared solution at machine precision; documented mm tolerances stay robust for the low-noise case"

patterns-established:
  - "A correctness safety net that would fail loudly if the default path drifts or the per-camera parameterization misaligns"

requirements-completed: [IFACE-05]

# Metrics
duration: 45 min
completed: 2026-07-23
---

# Phase 17 Plan 05: IFACE-05 Correctness Safety Net Summary

**Proved shared-mode bit-identity and equal-seed per-camera recovery -- and in doing so caught a cost-function misalignment bug that had silently broken the entire ablation (per-camera Stage 3 diverged to RMS ~148 even from the perfect optimum).**

## Performance

- **Duration:** ~45 min (includes bug diagnosis)
- **Completed:** 2026-07-23T19:36:04Z
- **Tasks:** 2 (+ 1 unplanned Rule-1 bug fix)
- **Files modified:** 5 (1 created)

## Accomplishments
- Packing/structure-layer bit-identity: exact-equality assertions (rtol=0/atol=0) between the default and `shared_interface=True` for pack/bounds/sparsity/groups, plus the single-water_z layout.
- End-to-end shared-mode determinism: Stage 3 run twice on identical inputs yields bit-identical R/t, distances, and RMS.
- Equal-seed recovery: per-camera mode with equal seeds on shared-interface ground truth recovers the shared solution to machine precision (per-camera water_z agree, mean matches shared water_z, extrinsics/RMS match).
- **Found and fixed a Rule-1 bug**: the whole per-camera path was broken until this plan's recovery test exposed it.

## Task Commits

1. **Bug fix: compute_residuals shared_interface threading** - `575bdc8` (fix)
2. **Tasks 1-2: bit-identity + recovery tests** - `2bb5ba6` (test)

## Files Created/Modified
- `tests/synthetic/test_per_camera_interface.py` - shared bit-exact + equal-seed recovery (both @pytest.mark.slow)
- `tests/unit/test_optim_common.py` - shared-mode bit-identity + single-water_z layout
- `src/aquacal/calibration/_optim_common.py` - compute_residuals threads shared_interface to unpack_params (bug fix)
- `src/aquacal/calibration/interface_estimation.py` - shared_interface appended to cost_args (bug fix)
- `src/aquacal/calibration/refinement.py` - shared_interface appended to cost_args (bug fix)
- `tests/unit/test_interface_estimation.py` - strengthened the per-camera end-to-end test to assert RMS < 5.0 (fast-suite regression guard)

## Decisions Made
- Kept the recovery tolerances at a few millimeters (documented inline) even though noiseless recovery is exact to ~1e-15, so the guarantee stays robust for the low-noise case.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] compute_residuals ignored shared_interface, misaligning the per-camera parameter vector**
- **Found during:** Task 2 (equal-seed recovery test)
- **Issue:** `compute_residuals` called `unpack_params` without `shared_interface`, so in per-camera mode it read a single `water_z` and shifted every subsequent block (board poses, intrinsics). The optimizer optimized a scrambled vector: starting AT the noiseless shared optimum (RMS 0) it diverged to RMS ~148, and cold per-camera Stage 3 gave a 75mm water_z spread with RMS ~147. Plan 17-01 Task 1 explicitly said "Do not touch compute_residuals … downstream compute_residuals already indexes it per camera, so no change is needed there" — that rationale was incorrect.
- **Fix:** Added `shared_interface: bool = True` to `compute_residuals` (threaded into `unpack_params`) and appended `shared_interface` to `cost_args` in both `optimize_interface` and `joint_refinement`. Post-fix, per-camera mode recovers the shared solution to machine precision (water_z spread 5e-16, RMS 0.0).
- **Files modified:** src/aquacal/calibration/_optim_common.py, interface_estimation.py, refinement.py
- **Verification:** Recovery test passes at machine precision; the strengthened per-camera end-to-end unit test (RMS < 5.0) now guards it in the fast suite; full fast suite 768 passed.
- **Committed in:** `575bdc8`

---

**Total deviations:** 1 auto-fixed (1 Rule-1 bug)
**Impact on plan:** The bug fix was essential — without it the entire ablation produced garbage. The 17-03 end-to-end test passed pre-fix only because it checked `isfinite(rms)` (RMS 147 is finite); it was strengthened to an RMS bound. No scope creep beyond restoring correctness.

## Issues Encountered
- Pre-commit ruff-format (v0.15.1) reformatted the new test files on commit while the local `ruff format` reported no changes; committing the two test files together (no unstaged files to stash) let the hook apply cleanly.

## Next Phase Readiness
- Phase 17 is functionally complete and provably correct: shared path bit-unchanged, per-camera path recovers the shared solution on shared ground truth.
- Full new-feature documentation (worked example, WP6 interpretation) remains deferred to Phase 21 per CONTEXT.

---
*Phase: 17-per-camera-interface-ablation-mode*
*Completed: 2026-07-23*
