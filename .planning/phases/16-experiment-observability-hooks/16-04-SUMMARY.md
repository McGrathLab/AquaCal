---
phase: 16-experiment-observability-hooks
plan: 04
subsystem: calibration
tags: [optimization, observability, scipy, bundle-adjustment, csv]

# Dependency graph
requires: ["16-03"]
provides:
  - "aquacal.calibration._observability.OptimizerObserver / TraceRow / TRACE_CSV_HEADER"
  - "optimize_interface(..., observer=...) and joint_refinement(..., observer=...)"
  - "pipeline per-stage trace CSVs: internals/trace_stage3.csv, trace_stage3_rerun.csv, trace_stage4.csv"
affects: [16-05, 16-06]

# Tech tracking
tech-stack:
  added: ["scipy>=1.16 (least_squares callback support)"]
  patterns:
    - "Optional trailing observer=None parameter on BA entry points; when None, the least_squares call path is byte-for-byte identical to before this plan"
    - "fun/jac wrapping caches only scalar/1D state (never a 2D Jacobian) to compute an optimality proxy without pinning memory"

key-files:
  created:
    - src/aquacal/calibration/_observability.py
    - tests/unit/test_observability.py
  modified:
    - src/aquacal/calibration/interface_estimation.py
    - src/aquacal/calibration/refinement.py
    - src/aquacal/calibration/pipeline.py
    - pyproject.toml
    - requirements.txt
    - tests/unit/test_interface_estimation.py
    - tests/unit/test_refinement.py
    - tests/unit/test_pipeline.py

key-decisions:
  - "optimality is an unconstrained ||J^T f||_inf proxy, not scipy's Coleman-Li bound-scaled optimality on the final result - documented in the module docstring, TraceRow docstring, and here"
  - "on_solution(result) defined now as a documented no-op extension point so plan 16-05 (conditioning) does not need to reopen interface_estimation.py or refinement.py"
  - "One CSV per traced stage (stage3, stage3_rerun, stage4) - never merged, since iteration numbering restarts per stage and a merged file would make the iteration axis meaningless"

requirements-completed: [HOOK-02]

# Metrics
duration: 40min
completed: 2026-07-23
---

# Phase 16 Plan 04: Optimizer Observability Trace (HOOK-02) Summary

**`OptimizerObserver` wraps scipy's `least_squares(callback=...)` (new in scipy 1.16) to record a per-iteration CSV trace of cost, step norm, and an unconstrained optimality proxy for each bundle-adjustment stage, with zero change to the solver's numerical output.**

## Performance

- **Duration:** ~40 min
- **Completed:** 2026-07-23T17:32:57Z
- **Tasks:** 3/3 completed
- **Files modified:** 6 modified, 2 created (plus the 3 test files already counted above)

## Accomplishments

- `src/aquacal/calibration/_observability.py` defines `TraceRow` (iteration, n_fev, cost, step_norm, optimality, water_z, tilt_rx, tilt_ry) and `OptimizerObserver`, whose `wrap_fun`/`wrap_jac` cache only a 1D residual vector and a scalar optimality value between calls -- never a 2D Jacobian -- so peak memory on the 13-camera rig (already ~3.6 GB) is unaffected
- `optimality` is computed as `||J^T f||_inf` at each accepted iteration: exact when `jac` is a real callable, `nan` for every row when `jac="2-point"` (the `use_sparse_jacobian=False` path) -- this proxy intentionally does not match scipy's final bound-scaled `optimality`, and that caveat is documented in three places (module docstring, `TraceRow` docstring, this summary)
- `optimize_interface` (Stage 3) and `joint_refinement` (Stage 4) both gained a trailing `observer: OptimizerObserver | None = None` parameter; when `None`, the `least_squares` call receives no `callback` kwarg and uses the original `compute_residuals`/`jac` objects unchanged -- verified both by code inspection (an empty `**ls_kwargs` dict) and by a dedicated bit-identical-result test per function
- `on_solution(result)` is a documented no-op hook called immediately after each solve returns; plan 16-05 will fill it in to compute Jacobian conditioning while `result.jac` is still in scope, without needing to touch these two call sites again
- The pipeline creates one `OptimizerObserver` per traced stage only when `config.save_optimization_trace` is `True`, and writes three independently-named CSVs: `internals/trace_stage3.csv`, `internals/trace_stage3_rerun.csv` (only when the outlier-rejection re-run fires), and `internals/trace_stage4.csv` (only when `refine_intrinsics` is on) -- the re-run intentionally gets its own file rather than being appended to Stage 3's, since iteration numbering restarts per stage
- `scipy>=1.16` is now the floor in both `pyproject.toml` and `requirements.txt` (installed: 1.17.0); this is a real new minimum-version constraint, not a side effect, since `least_squares(callback=...)` did not exist before 1.16.0

## Task Commits

Each task was committed atomically:

1. **Task 1: Create the OptimizerObserver and bump the scipy floor** - `048f8ba` (feat)
2. **Task 2: Accept an optional observer in optimize_interface and joint_refinement** - `9928deb` (feat)
3. **Task 3: Wire per-stage trace files into the pipeline** - `29201f3` (feat)

_No TDD tasks in this plan; each commit is a single feat commit with accompanying tests._

## Files Created/Modified

- `src/aquacal/calibration/_observability.py` - New module: `TraceRow`, `OptimizerObserver` (wrap_fun, wrap_jac, callback, on_solution, write_trace_csv, configure_layout)
- `src/aquacal/calibration/interface_estimation.py` - `optimize_interface` accepts `observer=None`; when set, wraps `compute_residuals`/`jac` and adds `callback=observer.callback` via `**ls_kwargs` (empty when `observer is None`)
- `src/aquacal/calibration/refinement.py` - Identical wiring in `joint_refinement`; `water_z_index` uses the same `(0 if normal_fixed else 2) + 6*(len(camera_order)-1)` slice, unaffected by `refine_intrinsics` since intrinsics are packed after board poses
- `src/aquacal/calibration/pipeline.py` - `_run_stage3(dets, observer=None)`; three observer-creation-and-write sites gated on `config.save_optimization_trace`, using `ensure_internals_dir`/`OptimizerObserver.write_trace_csv`
- `pyproject.toml`, `requirements.txt` - `scipy` -> `scipy>=1.16`
- `tests/unit/test_observability.py` - 10 tests against a real Rosenbrock-style `least_squares(method="trf")` problem: row capture, monotonic cost, exact step-norm reconstruction, optimality-proxy cross-check, `nan` handling for `jac="2-point"`, bit-identical-solution guard, no-Jacobian-retained guard, CSV round-trip and overwrite-warning
- `tests/unit/test_interface_estimation.py` - `TestOptimizeInterfaceObserver`: bit-identical result with/without observer, final-row `water_z` matches `unpack_params`'s water_z exactly, tilt columns finite/`nan` correctly under `normal_fixed`
- `tests/unit/test_refinement.py` - `TestJointRefinementObserver`: same two guarantees for `joint_refinement`
- `tests/unit/test_pipeline.py` - `TestStage3ObserverWiring`: a real `optimize_interface` call with an observer produces a CSV with the exact header, plus a source-guard test pinning the three distinct trace filenames against a future accidental merge

## Decisions Made

- `optimality` is documented as an unconstrained proxy in the module docstring, the `TraceRow` field docstring, and here -- it will not bit-match scipy's final `result.optimality`, which applies Coleman-Li bound scaling this proxy skips
- `on_solution` is defined now (empty body) purely as plan 16-05's extension point, so that plan can add conditioning diagnostics without reopening `interface_estimation.py` or `refinement.py`
- The zero-numerical-change guarantee is enforced by never adding a `callback=None` kwarg or a wrapped `fun`/`jac` to the `least_squares` call when `observer is None` -- verified by inspection (`**ls_kwargs` is empty) and by the bit-identical-result tests in both BA entry points

## Deviations from Plan

None - plan executed exactly as written, including the research correction (Stage 3 = `interface_estimation.py:301`, Stage 4/intrinsic pass = `refinement.py:201`; `point_refinement.py:674` was correctly left untouched, confirmed by `grep -n "point_refinement" src/aquacal/calibration/_observability.py` returning nothing).

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required. The installed scipy (1.17.0) already satisfies the new `>=1.16` floor.

## Next Phase Readiness

- `OptimizerObserver.on_solution` is ready for plan 16-05 to attach conditioning computation (Jacobian singular-value spectrum + correlation matrix) at the solution point, without modifying `interface_estimation.py` or `refinement.py` again.
- Full unit suite: 696 passed (up from the 679 baseline after 16-03; +17 new tests, 0 regressions). `tests/ -m "not slow"`: 701 passed, 29 deselected (up from 684 baseline).
- `ruff check` and `ruff format --check` clean on `src/aquacal`.
- `grep -n "scipy" pyproject.toml requirements.txt` shows `scipy>=1.16` in both files.
- `grep -n "point_refinement" src/aquacal/calibration/_observability.py` returns nothing, confirming the trace was not attached to the wrong function (the v1.6 public refinement API in `point_refinement.py` is out of scope, per the plan's research correction).

---
*Phase: 16-experiment-observability-hooks*
*Completed: 2026-07-23*

## Self-Check: PASSED

All created/modified files and all three task commit hashes (`048f8ba`, `9928deb`, `29201f3`) verified present.
