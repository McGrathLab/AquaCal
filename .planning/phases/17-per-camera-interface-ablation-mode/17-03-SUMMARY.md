---
phase: 17-per-camera-interface-ablation-mode
plan: 03
subsystem: calibration
tags: [bundle-adjustment, optimizer, pipeline, water_z, ablation, shared_interface]

# Dependency graph
requires:
  - phase: 17-per-camera-interface-ablation-mode
    provides: shared_interface-aware _optim_common functions (plan 17-01) + config flag (plan 17-02)
provides:
  - optimize_interface (Stage 3) and joint_refinement (Stage 4) accept shared_interface and seed per-camera water_z individually
  - pipeline wiring of config.shared_interface into both BA stages
  - single reason-bearing ablation WARNING at pipeline start
affects: [17-04, 17-05]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "per-camera seeding is individual: pack_params receives water_z_per_camera=initial_water_zs (Stage 3) / distances_in (Stage 4), never collapsed to the reference"

key-files:
  created: []
  modified:
    - src/aquacal/calibration/interface_estimation.py
    - src/aquacal/calibration/refinement.py
    - src/aquacal/calibration/pipeline.py
    - tests/unit/test_interface_estimation.py

key-decisions:
  - "The ablation WARNING is a single print in the pipeline's existing '  WARNING:' style, emitted once right after the banner, carrying the full reason (ablation-only; shared-interface assumption underlies the central claim; not for production)"
  - "observer water_z_index kept as the first-water_z index formula (0/2 + 6*(n_cams-1)) -- valid in both modes (points at camera_order[0]'s water_z)"

patterns-established:
  - "Optimizers thread shared_interface to every _optim_common call and build_parameter_labels; default True leaves the pipeline path unchanged"

requirements-completed: [IFACE-01, IFACE-02]

# Metrics
duration: 25 min
completed: 2026-07-23
---

# Phase 17 Plan 03: Optimizer + Pipeline Integration Summary

**Threaded `shared_interface` into Stage 3 (`optimize_interface`) and Stage 4 (`joint_refinement`) with individual per-camera seeding, and wired `config.shared_interface` into the pipeline behind a single reason-bearing ablation WARNING.**

## Performance

- **Duration:** ~25 min
- **Completed:** 2026-07-23T19:36:04Z
- **Tasks:** 3
- **Files modified:** 4

## Accomplishments
- `optimize_interface` gains `shared_interface`, threaded into every `_optim_common` call plus `build_parameter_labels`; per-camera mode seeds each camera from its own `initial_water_zs` value via `water_z_per_camera`.
- `joint_refinement` gains `shared_interface`, seeding each camera's Stage-4 start from its own Stage-3 `distances_in` value.
- `run_calibration_from_config` passes `config.shared_interface` into both BA stages and emits exactly one WARNING (with the full reason) at start when per-camera mode is active.
- End-to-end test runs `optimize_interface(shared_interface=False)` and confirms one water_z per camera.

## Task Commits

1. **Task 1: optimize_interface (Stage 3)** - `b3320d2` (feat)
2. **Task 2: joint_refinement (Stage 4)** - `e6c6f5f` (feat)
3. **Task 3: pipeline wiring + WARNING + test** - `1a8ce3a` (feat)

## Files Created/Modified
- `src/aquacal/calibration/interface_estimation.py` - shared_interface-aware optimize_interface
- `src/aquacal/calibration/refinement.py` - shared_interface-aware joint_refinement
- `src/aquacal/calibration/pipeline.py` - config wiring + single ablation WARNING
- `tests/unit/test_interface_estimation.py` - per-camera end-to-end test

## Decisions Made
- Used a print-based WARNING consistent with the pipeline's existing `  WARNING:` lines rather than `warnings.warn`, so the single emission lands on the pipeline's stdout stream alongside the banner.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None.

## Next Phase Readiness
- Per-camera water_z now flows end to end through both BA stages. 17-04 can add the seed resolver (partial/None/unknown/aux handling) and the spread report; 17-05 can add the bit-exactness and equal-seed recovery guarantees.
- Note: a partial `config.initial_water_z` dict currently reaches `optimize_interface` unresolved; 17-04's `_resolve_per_camera_water_z_seeds` fills it before the optimizer call.

---
*Phase: 17-per-camera-interface-ablation-mode*
*Completed: 2026-07-23*
