---
phase: 16-experiment-observability-hooks
plan: 05
subsystem: calibration
tags: [conditioning, jacobian, observability, wp6, hook-03]

# Dependency graph
requires: ["16-01", "16-04"]
provides:
  - "aquacal.calibration._observability.build_parameter_labels"
  - "OptimizerObserver(conditioning=...).on_solution computes a labelled ConditioningReport"
  - "aquacal.calibration.pipeline._select_conditioning_report"
  - "output_dir/internals/conditioning.json + conditioning.npz (config.save_conditioning)"
affects: [17]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "on_solution computes conditioning inside the optimizer function's scope,
       while result.jac is still alive, so only the small (n, n) report survives
       past the call -- never result or result.jac itself"
    - "Parameter labels built by a function that mirrors pack_params's layout
       argument-for-argument, so a layout change to one is caught by
       build_structural_column_groups' existing assertion pattern applied the
       same way here (length-match tests)"
    - "Exactly one conditioning report per run, selected post-hoc from whichever
       observer's solve is the final reported result; the Stage-3 outlier
       rejection re-run is the one case where two conditioning passes can occur
       in the same run, and the later one wins"

key-files:
  created: []
  modified:
    - src/aquacal/calibration/_observability.py
    - src/aquacal/calibration/interface_estimation.py
    - src/aquacal/calibration/refinement.py
    - src/aquacal/calibration/pipeline.py
    - src/aquacal/validation/conditioning.py
    - tests/unit/test_observability.py
    - tests/unit/test_pipeline.py

key-decisions:
  - "Kept compute_conditioning/ConditioningMemoryError imports local to on_solution
     (and to the monkeypatch-target import path), per the plan's 'avoids a
     calibration -> validation import at module load' note; used a
     TYPE_CHECKING-only import for the ConditioningReport type hint so no runtime
     import cost is paid unless conditioning=True actually fires. Verified no
     circular-import risk exists either way (aquacal.validation never imports
     aquacal.calibration)."
  - "Trace-CSV writes are now gated on `config.save_optimization_trace`
     explicitly (not just 'observer is not None'), because observers can now
     exist solely for conditioning. Without this guard a conditioning-only run
     would also silently start emitting trace_stage{3,3_rerun,4}.csv files."
  - "save_conditioning_report's new `stage` kwarg is additive-only (JSON gains
     one key); load_conditioning_report and ConditioningReport were
     deliberately left unchanged, since only the JSON write side needs
     provenance -- the report object itself has no notion of which stage
     produced it."

requirements-completed: [HOOK-03]

# Metrics
duration: 45min
completed: 2026-07-23
---

# Phase 16 Plan 05: Wire Conditioning Diagnostics Into the Pipeline (HOOK-03) Summary

**`OptimizerObserver.on_solution` now computes a fully-labelled `ConditioningReport` from `result.jac` at the solution -- inside the optimizer's own scope, so only a ~4 MB `(n, n)` report survives -- and the pipeline writes exactly one `internals/conditioning.json`/`.npz` pair per run, tagged with the stage that produced it.**

## What Was Built

**`src/aquacal/calibration/_observability.py`:**
- `build_parameter_labels(camera_order, frame_order, reference_camera, refine_intrinsics=False, normal_fixed=True) -> list[str]`: mirrors `_optim_common.pack_params`'s layout argument-for-argument (tilt -> per-camera extrinsics, skipping the reference camera -> `water_z` -> per-frame board poses -> per-camera intrinsics if refining), so `labels[i]` names `x[i]` for any `x` `pack_params` would produce with the same arguments. This is what makes the correlation matrix's rows/columns readable by name -- `water_z` and each camera's `_tvec_z` entry are directly findable for the camera-height coupling argument.
- `OptimizerObserver` gained `conditioning: bool = False`, `self.conditioning_report: ConditioningReport | None`, and `self.parameter_labels` (settable via an extended `configure_layout(..., parameter_labels=None)`). `on_solution` is no longer a no-op: when `conditioning=True` it calls `compute_conditioning(result.jac, parameter_names=self.parameter_labels)` (imported locally, matching the plan's module-load-avoidance note) and stores only the resulting report; `ConditioningMemoryError` is caught only to re-raise with `[{stage}]` prefixed onto the message, then propagates.

**`src/aquacal/calibration/interface_estimation.py` / `refinement.py`:** both call sites that already invoke `observer.configure_layout(...)` (added in plan 16-04) now also pass `parameter_labels=build_parameter_labels(...)` -- a one-line addition each, no restructuring.

**`src/aquacal/calibration/pipeline.py`:**
- `observe = config.save_optimization_trace or config.save_conditioning` now gates observer *creation* for all three stages (previously trace-flag-only).
- `conditioning=` is set per observer: Stage-4 observer gets `config.save_conditioning` (Stage 4 is the final reported result whenever `refine_intrinsics`); both Stage-3 observers (initial and outlier-rejection re-run) get `config.save_conditioning and not config.refine_intrinsics`. Since the initial Stage-3 solve can't know in advance whether the re-run will fire, conditioning can compute twice in the same run when it does -- documented in-line as a deliberate, bounded duplication.
- Trace-CSV writes are now gated on `config.save_optimization_trace` explicitly (not merely "observer exists"), since observers can now exist purely for conditioning.
- New pure helper `_select_conditioning_report(stage4_obs, rerun_obs, stage3_obs, refine_intrinsics)`: Stage-4's report wins when `refine_intrinsics`, else the re-run's if it fired, else the initial Stage-3 solve's. Returns `None` if the winning observer is `None` or produced no report.
- After Stage 3/4 resolve, if `config.save_conditioning` and a report was selected, writes `internals/conditioning.json` + `.npz` via `save_conditioning_report(..., stage=conditioning_stage)` and prints `Saved internals/conditioning.json (+ .npz) [stage: {stage}]`. Not wrapped in try/except, per the plan's refuse-loudly requirement.

**`src/aquacal/validation/conditioning.py`:** `save_conditioning_report` gained an optional `stage: str | None = None` kwarg, written into the JSON payload as `"stage"` -- the one-key additive change the plan specified. `load_conditioning_report` and `ConditioningReport` are unchanged.

**Tests:**
- `tests/unit/test_observability.py`: 4 parameterized layout tests (`refine_intrinsics` x `normal_fixed`) verifying label count matches `pack_params` output length and the `water_z` index formula; a reference-camera-has-no-extrinsic-labels guard; and 4 `on_solution` tests covering populated-when-enabled, no-op-when-disabled, no-Jacobian-retained, and memory-error-propagates-with-stage-name (via `monkeypatch` on `aquacal.validation.conditioning.compute_conditioning`, which works because the import inside `on_solution` is resolved at call time).
- `tests/unit/test_pipeline.py`: a `TestConditioningWiring` class with a source-guard for the artifact names/writer reference, a full 4-combination unit test of `_select_conditioning_report`, a none-observer-returns-none guard, a JSON-records-stage round-trip test, and a source-guard confirming observer creation is gated on the combined `save_optimization_trace or config.save_conditioning` condition.

## Task Commits

1. **Task 1: Compute labelled conditioning inside on_solution** - `ccc61ac` (feat)
2. **Task 2: Enable conditioning on the final reported stage and write it once** - `f5ea190` (feat)

## Deviations from Plan

None -- plan executed exactly as written. The trace-CSV write-gating change (adding an explicit `config.save_optimization_trace` check alongside "observer is not None") is a direct, necessary consequence of the plan's own Task 2 instruction to create observers on the combined flag; not a deviation from the plan's intent, but called out here since it touches lines the plan itself didn't explicitly dictate at that granularity.

## `result.jac` Shape / Runtime Note (for the deferred PERF-01 todo)

No real 13-camera rig run was executed in this session (that run takes 48-87 minutes and is out of scope for this plan's verification, which is unit-test-driven). No sharper peak-memory or runtime figure is available to hand off to PERF-01 beyond what 16-01's SUMMARY already flagged: `chunk_rows` remains at its plan-specified default of 8192, still untested against a real `result.jac`. The first real run with `save_conditioning: true` enabled will be the first opportunity to capture the actual `(m, n)` shape and wall-clock cost of the blocked-QR + single-SVD conditioning pass on the full rig; that data point should be captured then (e.g. in Phase 17's WP6 experiment notes) rather than estimated here.

## Verification

- `python -m pytest tests/unit/test_observability.py -v`: 21 passed (11 new).
- `python -m pytest tests/unit/test_pipeline.py -v -k "conditioning"`: 5 passed.
- `python -m pytest tests/unit/test_conditioning.py -q`: 12 passed (unchanged, confirms `save_conditioning_report`'s additive `stage` kwarg didn't break existing callers).
- `python -m pytest tests/unit/ -q`: 712 passed (up from 696 baseline; +16 new tests across both tasks), 0 failed.
- `python -m pytest tests/ -m "not slow" -q`: 717 passed, 29 deselected, 0 failed (up from 701 baseline).
- `ruff check src/aquacal && ruff format --check src/aquacal`: clean.
- `grep -n "except ConditioningMemoryError" src/aquacal/calibration/pipeline.py`: empty -- the pipeline never catches the refusal.
- `grep -rn "eigh(" src/aquacal/`: empty -- the forbidden Gram-matrix route was never introduced.

## Issues Encountered

None.

## User Setup Required

None.

## Next Phase Readiness

- `output_dir/internals/conditioning.json` + `.npz` are now produced by any run with `save_conditioning: true` in its config's `internals:` section, with the producing stage recorded in the JSON.
- Parameter names in the correlation matrix let Phase 17's WP6 per-camera interface ablation directly query the `water_z` row/column and each camera's `_tvec_z` entry for the camera-height degeneracy argument -- HOOK-03 is now fully unblocked for that phase.
- `ConditioningMemoryError` refusals propagate all the way out of `run_calibration_from_config` and name `save_conditioning` in the message, so a future large-rig run that can't afford conditioning fails loudly and instructs the user to disable the flag rather than silently reporting a narrower metric.

---
*Phase: 16-experiment-observability-hooks*
*Completed: 2026-07-23*

## Self-Check: PASSED

- FOUND: src/aquacal/calibration/_observability.py
- FOUND: src/aquacal/calibration/pipeline.py
- FOUND: src/aquacal/validation/conditioning.py
- FOUND: .planning/phases/16-experiment-observability-hooks/16-05-SUMMARY.md
- FOUND: ccc61ac
- FOUND: f5ea190
