---
phase: 17-per-camera-interface-ablation-mode
plan: 04
subsystem: calibration
tags: [pipeline, water_z, ablation, seed-resolution, spread-report, internals-json]

# Dependency graph
requires:
  - phase: 17-per-camera-interface-ablation-mode
    provides: shared_interface-threaded pipeline + optimizers (plan 17-03), config flag + partial-dict loader gate (plan 17-02)
provides:
  - _resolve_per_camera_water_z_seeds (None/partial/unknown/auxiliary rules, IFACE-04)
  - _build_interface_spread_report + always-on internals/interface_spread.json (meters) + mm console summary
affects: [21]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "per-camera seed resolution + spread report guarded by `if not config.shared_interface` so shared mode is byte-for-byte untouched"

key-files:
  created: []
  modified:
    - src/aquacal/calibration/pipeline.py
    - tests/unit/test_pipeline.py

key-decisions:
  - "Seed resolver uses warnings.warn(UserWarning) (not print) so the None/partial/unknown/auxiliary cases are cleanly assertable with pytest.warns/recwarn"
  - "Spread stat `std` is the population standard deviation (numpy default ddof=0), documented in the helper docstring"
  - "interface_spread.json stage tag reuses the same selection logic as the conditioning report (stage4 if refine_intrinsics, else stage3_rerun if the rerun fired, else stage3)"

patterns-established:
  - "The ablation headline number (per-camera water_z spread) is unconditional in per-camera mode: mm to console, meters to JSON, no gating flag"

requirements-completed: [IFACE-04]

# Metrics
duration: 25 min
completed: 2026-07-23
---

# Phase 17 Plan 04: Seed Resolver + Spread Report Summary

**Added the per-camera water_z seed resolver (None/partial/unknown/auxiliary rules) and the always-on interface-spread report (mm console + `internals/interface_spread.json` in meters), both scoped strictly to the per-camera path.**

## Performance

- **Duration:** ~25 min
- **Completed:** 2026-07-23T19:36:04Z
- **Tasks:** 3
- **Files modified:** 2

## Accomplishments
- `_resolve_per_camera_water_z_seeds`: None fills 0.15 silently; a partial dict fills missing cameras and warns naming them; an unknown key warns as a likely typo; an auxiliary-camera key is silently ignored. Wired into the per-camera Stage-3 branch only.
- `_build_interface_spread_report`: per_camera (meters, sorted) plus min/max/mean/std(population)/range stats.
- Per-camera mode always prints an mm spread summary and writes `internals/interface_spread.json` (meters), tagged with the producing stage; shared mode writes nothing new.
- Full edge-case + math test coverage.

## Task Commits

1. **Tasks 1-2: seed resolver + spread report + wiring** - `8fdfc08` (feat)
2. **Task 3: tests** - `386defa` (test)

## Files Created/Modified
- `src/aquacal/calibration/pipeline.py` - two pure helpers + per-camera-branch wiring; hoisted `import json`/`import warnings` to module scope
- `tests/unit/test_pipeline.py` - seed-resolver edge cases + spread-report math/JSON round-trip

## Decisions Made
- Combined Tasks 1 and 2 into a single feat commit since both are additive helpers in the same file with intertwined wiring; tests committed separately.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
- ruff-format reformatted the new test block on first commit attempt (line-length wrap); re-added and committed cleanly. No behavior change.

## Next Phase Readiness
- The ablation's headline number (per-camera water_z spread) is now produced end to end. 17-05 provides the correctness safety net (bit-exactness + equal-seed recovery).
- The full new-feature write-up (worked example, WP6 interpretation) is deferred to Phase 21 per CONTEXT.

---
*Phase: 17-per-camera-interface-ablation-mode*
*Completed: 2026-07-23*
