---
phase: 17-per-camera-interface-ablation-mode
plan: 01
subsystem: calibration
tags: [bundle-adjustment, jacobian-sparsity, water_z, optimizer, ablation]

# Dependency graph
requires:
  - phase: 16-experiment-observability-hooks
    provides: build_parameter_labels in _observability.py (labels the packed vector)
provides:
  - shared_interface flag threaded through pack_params, unpack_params, build_bounds, build_jacobian_sparsity, build_structural_column_groups, build_parameter_labels
  - per-camera water_z parameterization (N contiguous params replacing the single global water_z) at the packing/structure layer
affects: [17-03, 17-04, 17-05]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "shared_interface=True default branch stays bit-identical to prior single-water_z behavior"
    - "per-camera water_z columns collapse into the single water_z group slot (group count invariant)"

key-files:
  created: []
  modified:
    - src/aquacal/calibration/_optim_common.py
    - src/aquacal/calibration/_observability.py
    - tests/unit/test_optim_common.py
    - tests/unit/test_observability.py

key-decisions:
  - "pack_params gained both shared_interface and an optional water_z_per_camera dict; when the dict is None per-camera mode seeds every camera from the scalar water_z (trivial equal-seed for IFACE-05 recovery)"
  - "N per-camera water_z columns share one FD group slot because two cameras' water_z columns never touch the same residual row -- group count stays 13 (17 with refine_intrinsics), unchanged from shared mode"

patterns-established:
  - "Every packing/structure function takes a trailing shared_interface: bool = True kwarg; the True branch is the untouched historical path"

requirements-completed: [IFACE-02, IFACE-03]

# Metrics
duration: 35 min
completed: 2026-07-23
---

# Phase 17 Plan 01: Per-Camera Water_z Packing/Structure Layer Summary

**Threaded `shared_interface` through the six packing/sparsity/grouping/label functions so a single global `water_z` becomes N per-camera parameters, with the default path proven bit-identical and the FD group count held at 13/17.**

## Performance

- **Duration:** ~35 min
- **Completed:** 2026-07-23T19:36:04Z
- **Tasks:** 3
- **Files modified:** 4

## Accomplishments
- `pack_params` / `unpack_params` / `build_bounds` accept `shared_interface`; per-camera mode packs, bounds, and round-trips N distinct `water_z` values individually.
- `build_jacobian_sparsity` emits N per-camera `water_z` columns, each nonzero only in that camera's residual rows; `build_structural_column_groups` collapses them into the single `water_z` slot so the group count stays 13 (17 with `refine_intrinsics`).
- `build_parameter_labels` emits one `{cam}_water_z` label per camera, aligned with `pack_params`'s per-camera emission order.
- IFACE-03 safety-net test parametrizes all 8 mode combinations; a shared-mode bit-identity guard proves the default is unchanged.

## Task Commits

1. **Task 1: pack/unpack/bounds** - `82ab1d3` (feat)
2. **Task 2: sparsity/grouping/labels** - `07de913` (feat)
3. **Task 3: tests** - `2f4cde5` (test)

## Files Created/Modified
- `src/aquacal/calibration/_optim_common.py` - shared_interface-aware pack/unpack/sparsity/bounds/grouping
- `src/aquacal/calibration/_observability.py` - shared_interface-aware build_parameter_labels
- `tests/unit/test_optim_common.py` - 8-mode grouping validity + per-camera pack/unpack/sparsity + bit-identity guard
- `tests/unit/test_observability.py` - per-camera parameter-label length + ordering

## Decisions Made
- Added an optional `water_z_per_camera` dict to `pack_params` alongside `shared_interface`; None falls back to the scalar `water_z` for every camera (enables trivial equal-seed recovery in 17-05).

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Packing/structure layer ready for 17-03 to thread `shared_interface` into `optimize_interface` / `joint_refinement`.
- Default shared path is bit-identical, so 17-05's IFACE-05 regression has a stable baseline.

---
*Phase: 17-per-camera-interface-ablation-mode*
*Completed: 2026-07-23*
