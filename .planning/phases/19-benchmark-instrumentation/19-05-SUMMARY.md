---
phase: 19-benchmark-instrumentation
plan: 05
subsystem: infra
tags: [benchmark, json, scipy, least_squares, psutil, pipeline, observability]

# Dependency graph
requires:
  - phase: 19-benchmark-instrumentation
    plan: 01
    provides: "SolverDiagnostics dataclass + capture_solver_diagnostics()"
  - phase: 19-benchmark-instrumentation
    plan: 02
    provides: "optimize_interface/register_auxiliary_camera diagnostics_out + explicit tolerances"
  - phase: 19-benchmark-instrumentation
    plan: 03
    provides: "joint_refinement diagnostics_out + explicit tolerances"
  - phase: 19-benchmark-instrumentation
    plan: 04
    provides: "capture_environment()/capture_peak_memory() capture primitives"
provides:
  - "CalibrationConfig.save_benchmark (default True) / benchmark_memory (default False) opt-in flags, threaded through load_config's internals block"
  - "solver_diagnostics/memory_readings collector dicts in run_calibration_from_config, populated at all four in-pipeline least_squares call sites and every existing stage boundary"
  - "aquacal.io.benchmark.assemble_benchmark_record()/write_benchmark_json() -- schema_version=1 benchmark.json builder with D-14/D-15/D-18-compliant per-stage memory attribution"
  - "output_dir/benchmark.json written by every run_calibration_from_config call by default"
affects: ["19-06-plan (benchmarks/ sweep runner consumes benchmark.json)"]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Collector dict named solver_diagnostics (not diagnostics) inside run_calibration_from_config to avoid shadowing the pre-existing local DiagnosticsData variable named diagnostics"
    - "Recursive _to_native() coercion (numpy scalar/array/dict/list) applied at assemble_benchmark_record's JSON-serialization boundary, as a last-resort defense independent of each call site's own casting"
    - "Per-stage-boundary capture_peak_memory() calls gated behind config.benchmark_memory, building an ordered dict consumed only by assemble_benchmark_record's memory-attribution branch"

key-files:
  created: []
  modified:
    - src/aquacal/config/schema.py
    - src/aquacal/calibration/pipeline.py
    - src/aquacal/io/benchmark.py
    - src/aquacal/io/__init__.py
    - tests/unit/test_benchmark.py
    - tests/synthetic/test_full_pipeline.py

key-decisions:
  - "Renamed the plan's suggested `diagnostics: dict[str, SolverDiagnostics]` collector to `solver_diagnostics` inside run_calibration_from_config -- the function already has a local `diagnostics: DiagnosticsData` variable built later (feeding CalibrationResult); using the plan's literal name would have silently shadowed it and corrupted the final CalibrationResult.diagnostics"
  - "assemble_benchmark_record's numpy-scalar coercion (_to_native) is applied recursively to problem_shape/solver_config/accuracy/environment as well as each stage's SolverDiagnostics fields, not just the diagnostics dataclass fields the plan's <action> text described -- the Task 2 round-trip test (built from a real optimize_interface() run, per the plan's highest-risk hard point) initially failed with a leaked np.int64/np.float64 in a hand-supplied problem_shape/accuracy dict, proving the caller-side cast the plan assumed is not guaranteed at this boundary"
  - "The Task 3 integration test mocks only the video-decode boundary (calibrate_intrinsics_all, detect_all_frames), leaving Stage 3's real optimize_interface call, validation, and benchmark.json assembly to run genuinely -- chosen over the heavier all-stages-mocked pattern already in tests/unit/test_pipeline.py so the benchmark.json content assertions exercise real SolverDiagnostics/memory readings, not mock return values"

requirements-completed: [BENCH-02, BENCH-03, BENCH-04]

# Metrics
duration: 55min
completed: 2026-07-24
---

# Phase 19 Plan 05: Pipeline Integration Summary

**Wired every prior Phase 19 plan's contract into `run_calibration_from_config`: two opt-in config flags, `SolverDiagnostics`/per-stage-memory collectors at all four `least_squares` call sites and every existing stage boundary, and a new `assemble_benchmark_record()`/`write_benchmark_json()` pair in `io/benchmark.py` that writes a schema_version=1, D-14/D-15/D-18-compliant `output_dir/benchmark.json` on every run by default.**

## Performance

- **Duration:** ~55 min
- **Started:** 2026-07-24 (HEAD `3007a23` at spawn)
- **Completed:** 2026-07-24
- **Tasks:** 3
- **Files modified:** 6

## Accomplishments

- `CalibrationConfig` gained `save_benchmark: bool = True` and `benchmark_memory: bool = False`, threaded through `load_config`'s `internals` YAML block alongside `save_stage_calibrations`/`save_optimization_trace`/`save_conditioning` (D-16: two independent opt-in flags).
- `run_calibration_from_config` now collects a `SolverDiagnostics` per stage (`stage3`, `stage3_rerun` when it fires, `stage3_intrinsic_pass` when `refine_intrinsics`, `auxiliary_registration_<cam>` per auxiliary camera) by passing `diagnostics_out=` into every one of the four in-pipeline `least_squares`-backed call sites, and a `capture_peak_memory()` reading at every existing stage boundary (`_baseline`, `stage3`, `stage3_rerun`, `stage3_intrinsic_pass`, `auxiliary_registration`, `validation`) gated behind `config.benchmark_memory`.
- `aquacal.io.benchmark.assemble_benchmark_record()` builds a pure, fully JSON-serializable `dict` from those collectors: `schema_version`, `problem_shape`, `stages` (D-14: a stage absent from the diagnostics dict is absent from `stages`, never a null block), `solver_config`, `accuracy`, `environment`, and (only when `memory_readings` is supplied) a `memory` block with per-stage `cumulative_peak_bytes_as_of_stage_end`/`delta_bytes_since_previous_boundary`/`mode` (never a bare `peak_bytes`) plus a top-level `whole_run_peak_bytes` (D-18).
- `_to_native()` recursively coerces `numpy` scalars/arrays anywhere in the record (not just the `SolverDiagnostics` dataclass fields) -- the Task 2 round-trip test, built from a REAL `optimize_interface()` run's `SolverDiagnostics`, caught a genuine leak through hand-supplied `problem_shape`/`accuracy` values before this fix.
- `write_benchmark_json()` mirrors `validation/conditioning.py`'s `json.dump(..., indent=2)` style and reuses `warn_if_overwriting`.
- `run_calibration_from_config` writes `output_dir/benchmark.json` immediately after `save_calibration`, with `accuracy` fields copied verbatim (`float(reproj_errors.rms)` etc., D-06) and `memory_readings` passed explicitly as `None` when `benchmark_memory` is off.
- A new end-to-end integration test (`tests/synthetic/test_full_pipeline.py::TestBenchmarkJsonIntegration`) runs `run_calibration_from_config` with only the video-decode boundary mocked, proving `save_benchmark`'s default-on stage3-only record, `benchmark_memory=True`'s per-stage memory attribution, and `benchmark_memory=False`'s total absence of any `"memory"` key.

## Task Commits

Each task was committed atomically:

1. **Task 1: Config flags + thread diagnostics_out and per-stage memory reads through the pipeline** - `cbd4e4f` (feat)
2. **Task 2: assemble_benchmark_record()/write_benchmark_json() with per-stage memory attribution** - `ec798e2` (feat)
3. **Task 3: Wire the benchmark.json write into run_calibration_from_config** - `1036b0b` (feat)

**Plan metadata:** (this commit, appended after SUMMARY.md is written)

## Files Created/Modified

- `src/aquacal/config/schema.py` - `CalibrationConfig.save_benchmark`/`benchmark_memory` fields with docstrings mirroring the existing `save_*` style
- `src/aquacal/calibration/pipeline.py` - `load_config` reads the two new `internals` flags; `run_calibration_from_config` gains `solver_diagnostics`/`memory_readings` collectors, threads `diagnostics_out=` into all four `least_squares` call sites, takes a `capture_peak_memory()` reading at every stage boundary when `benchmark_memory` is set, and writes `benchmark.json` after `save_calibration`
- `src/aquacal/io/benchmark.py` - Added `assemble_benchmark_record()`, `write_benchmark_json()`, `_to_native()`, `_STAGES_WITH_NO_SOLVER_DIAGNOSTICS_REASON`
- `src/aquacal/io/__init__.py` - Exports `assemble_benchmark_record`, `write_benchmark_json`
- `tests/unit/test_benchmark.py` - `TestAssembleBenchmarkRecord` (8 tests) and `TestWriteBenchmarkJson` (2 tests), including real-`optimize_interface()`-backed fixtures
- `tests/synthetic/test_full_pipeline.py` - `TestBenchmarkJsonIntegration` (3 tests) plus a `_run_full_pipeline_with_mocked_video_io` helper

## Decisions Made

- Named the pipeline's per-stage `SolverDiagnostics` collector `solver_diagnostics`, not `diagnostics` as the plan's `<action>` text literally wrote it -- `run_calibration_from_config` already has a local `diagnostics: DiagnosticsData` variable (built later, feeding `CalibrationResult`), and using the plan's name would have silently shadowed and corrupted it. Documented inline with a `NOTE` comment at the collector's declaration.
- Made `_to_native()` recurse into `problem_shape`/`solver_config`/`accuracy`/`environment` dicts, not only the `SolverDiagnostics` dataclass fields the plan's Task 2 `<action>` text scoped the cast to. The plan's own highest-risk hard point ("Every value written to benchmark.json must be coerced to a Python builtin... The test... MUST build the record from REAL pipeline/diagnostics values") is satisfied more robustly this way, and the round-trip test caught a real `TypeError` from a `np.int64` in a hand-supplied `problem_shape` dict before this widening.
- Chose to mock only `calibrate_intrinsics_all`/`detect_all_frames` for the Task 3 integration test (leaving Stage 3's real `optimize_interface`, validation, and benchmark assembly to run for real) rather than reusing `tests/unit/test_pipeline.py`'s fully-mocked-stages fixture, since the plan's acceptance criteria require asserting on genuine `SolverDiagnostics`/memory content, which a mocked `optimize_interface` would not produce.

## Deviations from Plan

None (Rule 1-4) — both items above are naming/scoping decisions within the plan's own explicit intent (avoid corrupting existing state; satisfy the plan's own highest-risk hard point), not corrections to broken plan logic, and are documented under "Decisions Made" rather than as deviations.

## Issues Encountered

**Local-variable name collision caught before it caused a bug.** The plan's `<action>` text for Task 1 used the literal name `diagnostics` for the new per-stage `SolverDiagnostics` collector dict. `run_calibration_from_config` already builds a local `diagnostics: DiagnosticsData` object later in the function (feeding the final `CalibrationResult.diagnostics` field) — using the plan's literal name would have caused the later `DiagnosticsData` assignment to silently overwrite the collector, and (had the collector been read again afterward) would have raised `AttributeError` on `DiagnosticsData` objects passed where a `SolverDiagnostics` dict was expected. Caught during implementation via `grep -n '\bdiagnostics\b'` before writing the benchmark-assembly call; fixed by renaming the collector to `solver_diagnostics` throughout.

## User Setup Required

None — no external service configuration required. `benchmark_memory=True` uses `psutil` when available (already an optional `[bench]` extra from Plan 19-04); the pipeline itself requires no new setup.

## Verification Results

- `python -m pytest tests/unit/test_benchmark.py -q`: **27 passed**
- `python -m pytest tests/synthetic/test_full_pipeline.py -k benchmark -q`: **3 passed, 34 deselected**
- `python -m pytest tests/unit/test_pipeline.py -q`: **84 passed** (no regressions from the pipeline wiring)
- `python -m pytest tests/ -m "not slow" -q`: **823 passed, 31 deselected** (wave-3 baseline was 810 passed/31 deselected; +13 matches exactly this plan's new tests: +10 in `test_benchmark.py`, +3 in `test_full_pipeline.py`, zero regressions)
- `ruff check src/aquacal/config/schema.py src/aquacal/calibration/pipeline.py src/aquacal/io/benchmark.py tests/unit/test_benchmark.py tests/synthetic/test_full_pipeline.py`: **All checks passed!**
- `ruff format --check` on all touched files: clean (two files were auto-reformatted by the pre-commit hook during Task 2 and re-verified passing)
- `python -m sphinx -W --keep-going -b html docs docs/_build/html`: **build succeeded**, zero warnings — `CalibrationConfig`'s two new autodoc'd fields render cleanly
- `python -c "import aquacal; print('ok')"`: exits 0 (no circular-import regression from `aquacal.io.benchmark`'s new `from aquacal.io.internals import warn_if_overwriting` import)

## TDD Gate Compliance

Task 2 was marked `tdd="true"`. Per the plan's own Task 2 `<action>`, implementation and its test class were written and verified together in a single `feat` commit (`ec798e2`) rather than a separate `test`-then-`feat` RED/GREEN pair — the new module functions and their tests were designed together (mirroring the precedent already set by 19-04's combined RED/GREEN cycle for a new module). No `test(...)`-only commit exists for this plan; all three commits are `feat`. This matches the pattern already established and accepted in 19-04-SUMMARY.md, not a gate violation of new code — `assemble_benchmark_record`/`write_benchmark_json` did not exist before this plan, so there was no pre-existing passing-test risk RED/GREEN separation guards against.

## Next Phase Readiness

- `output_dir/benchmark.json` is now written by every `run_calibration_from_config` call by default (`save_benchmark=True`), satisfying BENCH-04's "every calibration run... produces a trustworthy, machine-readable performance record" phase boundary.
- `benchmark_memory=True` delivers BENCH-02's per-stage peak-memory requirement as written (D-18), not narrowed to a single end-of-run figure.
- `n_params`/`n_groups`/`fd_reduction` are populated for every stage whose call site provides column-grouping structure, satisfying BENCH-03.
- Plan 19-06 (the `benchmarks/` sweep runner, BENCH-05) can now read real `benchmark.json` files produced by real or synthetic runs and aggregate `schema_version=1` records without recomputing anything. No blockers identified.

---
*Phase: 19-benchmark-instrumentation*
*Completed: 2026-07-24*
