---
phase: 16-experiment-observability-hooks
plan: 03
subsystem: infra
tags: [config, cli, io, yaml, calibration-pipeline, observability]

# Dependency graph
requires: []
provides:
  - "CalibrationConfig.save_stage_calibrations, save_optimization_trace, save_conditioning, seed fields"
  - "internals: YAML config section and top-level seed: key, parsed by load_config"
  - "aquacal.io.ensure_internals_dir / warn_if_overwriting / INTERNALS_DIRNAME"
  - "pipeline._dump_stage_calibration and its three call sites (stage3, stage3_rerun, stage4)"
affects: [16-04, 16-05, 16-06, 19-benchmark-instrumentation]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Flat save_* config keys on CalibrationConfig, parsed from a dedicated YAML section, no nested sub-dataclass"
    - "output_dir/internals/ as the artifact directory for optimizer-guts observability, separate from diagnostics.json"

key-files:
  created:
    - src/aquacal/io/internals.py
    - tests/unit/test_internals.py
  modified:
    - src/aquacal/config/schema.py
    - src/aquacal/calibration/pipeline.py
    - src/aquacal/cli.py
    - src/aquacal/io/__init__.py
    - tests/unit/test_schema.py
    - tests/unit/test_cli.py
    - tests/unit/test_pipeline.py

key-decisions:
  - "internals: as the YAML section name (matches the artifact directory), seed: kept top-level rather than nested under validation: since it is a run-level knob"
  - "Stage dump call sites use stage3 / stage3_rerun / stage4 filenames, mirroring the trace filenames plan 16-04 will use"
  - "calibration_initial.json left untouched and unconditional - it is the pre-existing post-Stage-2 dump HOOK-01 extends, not something to move under the new flag"

patterns-established:
  - "Config-only observability switches (no CLI flags) so benchmark.json (Phase 19) has one source of truth"

requirements-completed: [HOOK-01, HOOK-02, HOOK-03, HOOK-06]

# Metrics
duration: 45min
completed: 2026-07-23
---

# Phase 16 Plan 03: Observability Config Foundation & Stage Calibration Dumps Summary

**Four new flat `CalibrationConfig` fields (`save_stage_calibrations`, `save_optimization_trace`, `save_conditioning`, `seed`) parsed from a new `internals:`/`seed:` YAML surface, an `output_dir/internals/` directory helper with clobber warnings, and default-on Stage-3/Stage-3-rerun/Stage-4 calibration JSON dumps.**

## Performance

- **Duration:** ~45 min
- **Completed:** 2026-07-23T17:17:48Z
- **Tasks:** 3/3 completed
- **Files modified:** 7 modified, 2 created

## Accomplishments
- `CalibrationConfig` carries `save_stage_calibrations=True`, `save_optimization_trace=False`, `save_conditioning=False`, `seed=42`, matching the `save_detailed_residuals` precedent exactly (flat, no nested sub-dataclass)
- `load_config` parses a new `internals:` YAML section and top-level `seed:` key, with full backward compatibility for configs that omit both
- `aquacal init` emits the new keys (active `save_stage_calibrations`, commented-out opt-in `save_optimization_trace`/`save_conditioning`) with zero new CLI flags
- `aquacal.io.ensure_internals_dir` / `warn_if_overwriting` / `INTERNALS_DIRNAME` give every future hook plan (16-04..16-07) a shared, tested place to write artifacts, distinct from the `diagnostics.json` report
- `_dump_stage_calibration` writes a `load_calibration`-readable JSON at each bundle-adjustment stage boundary (post-initial-Stage-3, post-outlier-rejection re-run, post-Stage-4), guarded by `config.save_stage_calibrations`, without touching `calibration_initial.json` or any value flowing into `calibration.json`

## Task Commits

Each task was committed atomically:

1. **Task 1: Add the four config fields, YAML parsing, and generated-config coverage** - `bb523a7` (feat)
2. **Task 2: Add the internals/ directory helper** - `afe54e8` (feat)
3. **Task 3: Dump each bundle-adjustment stage's intermediate calibration** - `ce94111` (feat)

_No TDD tasks in this plan; each commit is a single feat commit with accompanying tests._

## Files Created/Modified
- `src/aquacal/config/schema.py` - Four new `CalibrationConfig` fields + docstring entries
- `src/aquacal/calibration/pipeline.py` - `load_config` parsing of `internals:`/`seed:`, `_dump_stage_calibration` helper, three guarded call sites
- `src/aquacal/cli.py` - Generated-config text gains `internals:` and `seed:` (no argparse changes)
- `src/aquacal/io/internals.py` - New module: `INTERNALS_DIRNAME`, `ensure_internals_dir`, `warn_if_overwriting`
- `src/aquacal/io/__init__.py` - Exports the three new internals.py names
- `tests/unit/test_schema.py` - Default-field assertions on `CalibrationConfig`
- `tests/unit/test_cli.py` - Generated-config parsing assertions (active + commented-out keys)
- `tests/unit/test_pipeline.py` - `load_config` round-trip tests, new `TestDumpStageCalibration` class, updated `save_calibration` call-count expectations (2 -> 3) in two existing `TestRunCalibrationFromConfig` tests

## Decisions Made
- `internals:` chosen as the YAML section name (mirrors the artifact directory name); `seed:` kept top-level rather than under `validation:`, since it is a run-level reproducibility knob, not validation-specific
- Stage dump filenames: `calibration_stage3.json`, `calibration_stage3_rerun.json`, `calibration_stage4.json` - chosen to mirror the per-stage trace filenames plan 16-04 will introduce, so the two hooks reference the same stage vocabulary
- `seed` is recorded on `CalibrationConfig` and therefore folds into `_compute_config_hash`, satisfying HOOK-06's "recorded in outputs" gap identified in CONTEXT.md; it is not (and was not asked to be) threaded into the `split_detections` call site in this plan - that call already defaults to `seed=42`, matching the new config default, and `pipeline.py:462`'s frame-shuffle seeding was independently confirmed already-threaded per CONTEXT.md's audit

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Updated two existing mock-based pipeline tests for the new default-on save_calibration call**
- **Found during:** Task 3 verification (`python -m pytest tests/unit/test_pipeline.py -q`)
- **Issue:** `test_run_calibration_from_config_stages_order` and `test_run_calibration_from_config_saves_calibration` hard-coded `save_calibration.call_count == 2` (calibration_initial.json + calibration.json). With `save_stage_calibrations` defaulting to `True`, the new Stage-3 internals dump adds a third call, which is the intended default behavior per HOOK-01/CONTEXT.md, not a bug in the new code - the pre-existing tests simply predated this hook.
- **Fix:** Updated both assertions to `call_count == 3` and added an explicit check that the middle call targets `internals/calibration_stage3.json`.
- **Files modified:** `tests/unit/test_pipeline.py`
- **Verification:** `python -m pytest tests/unit/test_pipeline.py -q` -> 62 passed
- **Committed in:** `ce94111` (Task 3 commit)

---

**Total deviations:** 1 auto-fixed (1 bug/test-update)
**Impact on plan:** Necessary consequence of the plan's own default-on behavior; no scope creep.

## Issues Encountered
None.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Config surface, `internals/` directory helper, and stage-dump pattern are in place and tested; plans 16-04 (trace) and 16-05/16-06 (conditioning) can add their own artifacts under `output_dir/internals/` using `ensure_internals_dir`/`warn_if_overwriting` without further config plumbing.
- Full unit suite: 679 passed. `tests/ -m "not slow"`: 684 passed, 29 deselected. No regressions against the pre-phase baseline (651 passed) beyond the expected additions from this plan and the concurrently-landed 16-01/16-02 plans.
- `ruff check` and `ruff format --check` clean on `src/aquacal`.
- `aquacal init --help` shows no new flags; a generated config's `internals:`/`seed:` keys parse to the intended values end-to-end.

---
*Phase: 16-experiment-observability-hooks*
*Completed: 2026-07-23*

## Self-Check: PASSED

All created/modified files and all three task commit hashes (`bb523a7`, `afe54e8`, `ce94111`) verified present.
