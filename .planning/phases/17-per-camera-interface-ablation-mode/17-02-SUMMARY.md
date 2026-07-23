---
phase: 17-per-camera-interface-ablation-mode
plan: 02
subsystem: config
tags: [config, yaml-loader, cli, docs, ablation, shared_interface]

# Dependency graph
requires: []
provides:
  - CalibrationConfig.shared_interface field (default True, ablation-framed docstring)
  - load_config pass-through of interface.shared_interface + conditional missing-camera coverage gate
  - aquacal init commented shared_interface template line
  - refractive_geometry.md ablation-only docs stub
affects: [17-03, 17-04]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "shared_interface is pass-through at the loader (no cross-field validation); per-camera edge cases handled downstream"

key-files:
  created: []
  modified:
    - src/aquacal/config/schema.py
    - src/aquacal/calibration/pipeline.py
    - src/aquacal/cli.py
    - docs/guide/refractive_geometry.md
    - tests/unit/test_pipeline.py

key-decisions:
  - "The initial_water_z 'must cover all cameras' hard-fail is gated on shared_interface in BOTH dict branches (deprecated initial_distances + modern initial_water_z): raises in shared mode, skipped in per-camera mode so a partial dict reaches plan 17-04's seed resolver"
  - "shared_interface parsed early (right after normal_fixed) so it is in scope before the coverage gate"

patterns-established:
  - "Ablation framing repeated in three places: field docstring, generated config comment, docs stub"

requirements-completed: [IFACE-01]

# Metrics
duration: 20 min
completed: 2026-07-23
---

# Phase 17 Plan 02: shared_interface Config Surface Summary

**Exposed the `shared_interface` ablation flag across config schema, YAML loader, `aquacal init`, and docs, and made the `initial_water_z` coverage hard-fail conditional so a partial dict survives in per-camera mode.**

## Performance

- **Duration:** ~20 min
- **Completed:** 2026-07-23T19:36:04Z
- **Tasks:** 3
- **Files modified:** 5

## Accomplishments
- `CalibrationConfig.shared_interface: bool = True` with a docstring framing it as analysis/ablation only.
- `load_config` parses `interface.shared_interface` early (default True), passes it to the config, and gates the "must cover all cameras" raise on it in both dict branches.
- `aquacal init` emits `# shared_interface: true  # set false for per-camera water_z ablation (analysis only, not recommended)`.
- `refractive_geometry.md` carries a short ablation-only stub; four loader tests prove parse + the conditional coverage gate (accepted in per-camera mode, still rejected in shared mode).

## Task Commits

1. **Task 1: CalibrationConfig field** - `3231c1c` (feat)
2. **Task 2: loader + init template** - `f24585c` (feat)
3. **Task 3: docs stub + loader tests** - `fe5e70b` (test)

## Files Created/Modified
- `src/aquacal/config/schema.py` - shared_interface field + docstring
- `src/aquacal/calibration/pipeline.py` - early parse, conditional coverage gate (both branches), config construction
- `src/aquacal/cli.py` - commented shared_interface init line
- `docs/guide/refractive_geometry.md` - ablation-only stub
- `tests/unit/test_pipeline.py` - shared_interface loader + coverage-gate tests

## Decisions Made
- Followed the plan's instruction to change the coverage gate in both the deprecated `initial_distances` branch and the modern `initial_water_z` branch identically (used a single replace across both).

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Config flag now reaches `CalibrationConfig`, ready for 17-03 to wire it into the optimizers and emit the ablation WARNING.
- Partial `initial_water_z` dicts now reach the pipeline in per-camera mode, ready for 17-04's seed resolver.

---
*Phase: 17-per-camera-interface-ablation-mode*
*Completed: 2026-07-23*
