---
phase: 18-documentation-corrections-stage-model-reconciliation
plan: 06
subsystem: calibration-pipeline
tags: [rename, three-stage-model, machine-surface, no-compat-shim]

# Dependency graph
requires:
  - phase: 18-documentation-corrections-stage-model-reconciliation
    provides: 18-02-SUMMARY.md (confirmed vocabulary contract - stage3_intrinsic_pass, D-05 revised prose, D-23 auxiliary-camera label)
provides:
  - "pipeline.py's machine-readable surfaces (timing keys, OptimizerObserver stage tags, internals/ artifact filenames, console output) present the three-stage model with no ex-Stage-4 vocabulary remaining"
  - "Settled stage3_intrinsic_pass schema for Phase 19 (BENCH-04) to write into benchmark.json"
affects: [19-experiment-grid-and-benchmarking]

# Tech tracking
tech-stack:
  added: []
  patterns: []

key-files:
  created: []
  modified:
    - src/aquacal/calibration/pipeline.py
    - tests/unit/test_pipeline.py
    - tests/unit/test_refinement.py

key-decisions:
  - "D-06 implemented exactly: timings key, OptimizerObserver stage tag, trace CSV filename, and _dump_stage_calibration tag all renamed stage4 -> stage3_intrinsic_pass; stage3 and stage3_rerun untouched"
  - "D-05 implemented: console/section-comment prose now reads Stage 3's second pass / intrinsic pass rather than Stage 4"
  - "D-23 implemented: auxiliary-camera registration label collapsed to unconditional 'Auxiliary camera registration' with no stage number; 6-DOF/10-DOF distinction moved into the printed message body"
  - "No backward-compatibility shim added (D-03) - old stage4 literals and filenames do not exist anywhere in pipeline.py or its asserting tests after this plan"

patterns-established: []

requirements-completed: [DOCS-06]

# Metrics
duration: ~55min
completed: 2026-07-24
---

# Phase 18 Plan 06: Pipeline Stage-Model Rename Summary

**Renamed every ex-Stage-4 machine-readable surface in `pipeline.py` (timing key, observer tag, trace/calibration artifact filenames, and console prose) to the confirmed three-stage vocabulary, and dropped the auxiliary-camera registration's stage-numbered label entirely, with all asserting tests moved in the same commits as their renames.**

## Performance

- **Duration:** ~55 min
- **Started:** 2026-07-24
- **Completed:** 2026-07-24
- **Tasks:** 2
- **Files modified:** 3 (`pipeline.py`, `test_pipeline.py`, `test_refinement.py`)

## Accomplishments
- Renamed the four stage-tagged chokepoints (`timings["stage4_joint_refinement"]`, `OptimizerObserver(stage="stage4")`, `trace_stage4.csv`, `_dump_stage_calibration("stage4", ...)`) to `stage3_intrinsic_pass` everywhere, including both stage-selection expressions (`conditioning_stage`, `spread_stage`) and the local identifiers (`stage4_observer` -> `stage3_intrinsic_pass_observer`, `stage4_obs` param -> `stage3_intrinsic_pass_obs`).
- Moved every corresponding test literal in `test_pipeline.py` and `test_refinement.py` in the same commits, including the source-text guard `assert "trace_stage4.csv" in source` (now asserts `"trace_stage3_intrinsic_pass.csv"`).
- Brought console output, section comments, and the pipeline-stages docstring list onto the three-stage model, per D-05's confirmed prose.
- Collapsed the auxiliary-camera registration's conditional `"Stage 4b"`/`"Stage 3b"` label to the unconditional `"Auxiliary camera registration"` (D-23, no stage number), preserving the 6-DOF/10-DOF distinction in the printed message body rather than the label.
- Verified via `git diff` that no numeric literal, tolerance, or optimizer argument changed anywhere in `pipeline.py`.

## Task Commits

Each task was committed atomically:

1. **Task 1: Rename the four stage-tagged chokepoints and their test assertions** - `8afddfc`
   - `src/aquacal/calibration/pipeline.py`: timing key, observer tag, trace filename, `_dump_stage_calibration` tag, both stage-selection expressions, `_select_conditioning_report`'s parameter/docstring, and the two enumerated-tag docstrings all renamed to `stage3_intrinsic_pass`.
   - `tests/unit/test_pipeline.py`: `_dump_stage_calibration` call/filename assertion, `trace_stage4.csv` source-text guard, `_observer_with_report`/`_select_conditioning_report` expectations, `_build_interface_spread_report` call, all renamed.
   - `tests/unit/test_refinement.py`: module docstring and both `OptimizerObserver(stage="stage4")` constructions renamed.

2. **Task 2: Update pipeline console output and prose to the three-stage model** - `e301ae9`
   - Console bracket tags (`[Stage 4]` -> `[Stage 3: intrinsic pass]`), the RMS print line, the section comment, the docstring pipeline-stages list, and the auxiliary-camera label/comment all updated. No test changes were needed for this task -- no test in `test_pipeline.py` asserted on the changed console strings.

## Files Created/Modified
- `src/aquacal/calibration/pipeline.py` - four machine-surface chokepoints, two stage-selection expressions, console prose, docstrings, and the auxiliary-camera label all renamed/updated to the three-stage model
- `tests/unit/test_pipeline.py` - all asserting literals moved in lockstep with the Task 1 rename
- `tests/unit/test_refinement.py` - module docstring and `OptimizerObserver(stage=...)` literals moved in lockstep

## Decisions Made

No new decisions were required -- this plan implements decisions already locked by 18-02-SUMMARY.md (D-05 revised, D-06, D-23) and 18-CONTEXT.md (D-03). One execution-time judgment call, not a deviation from any must-have: the module docstring in `test_refinement.py` (`"""Unit tests for Stage 4 joint refinement."""`) is prose, not a `stage4` machine literal, and 18-02-SUMMARY.md does not specify exact test-docstring wording; it was renamed to `"""Unit tests for joint refinement (Stage 3's second pass, with intrinsics unlocked)."""` to match D-05's confirmed prose label rather than inventing new wording.

## Deviations from Plan

None - plan executed as written for both tasks. All acceptance-criteria greps and both automated verify commands passed:
- `grep -rnE '"stage4"|stage4_joint_refinement|trace_stage4|calibration_stage4'` returns zero matches restricted to `pipeline.py` and its asserting tests (see Known Out-of-Scope Note below for two unrelated files).
- `grep -c "stage3_intrinsic_pass" src/aquacal/calibration/pipeline.py` = 19 (>= 6 required).
- `grep -c "stage3_intrinsic_pass" tests/unit/test_pipeline.py` = 12 (>= 4 required).
- `grep -cE "Stage 4|Stage-4|stage 4"` = 0; `Stage 4b` = 0; `Stage 3b` = 0.
- `grep -c "Auxiliary camera registration"` = 2 (label + section comment).
- `grep -cE "6-DOF|6 DOF"` = 2; `grep -cE "10-DOF|10 DOF"` = 1.
- `grep -ci "intrinsic pass"` = 4.
- `grep -c '"auxiliary_registration"'` = 1 (unchanged, stage-agnostic key not touched).
- `ruff check src/aquacal/calibration/pipeline.py` exits 0.
- `python -m pytest tests/unit/test_pipeline.py tests/unit/test_refinement.py tests/unit/test_observability.py tests/unit/test_diagnostics.py tests/unit/test_internals.py tests/unit/test_interface_estimation.py -q` -> 203 passed.
- `python -m pytest tests/ -m "not slow"` -> 775 passed, 31 deselected.
- `python -m pytest tests/` (full suite, slow included) -> 806 passed (>= 799 baseline from Phase 17).

## Known Out-of-Scope Note (not a stub, not a blocker)

Two docstring examples outside this plan's assigned scope still mention `"stage4"` as an illustrative example string, not a machine literal that the code emits or a test asserts on:
- `src/aquacal/validation/conditioning.py:204` -- `save_conditioning_report`'s `stage:` Args entry, `(e.g. "stage3", "stage4")`
- `src/aquacal/calibration/_observability.py:178` -- `OptimizerObserver.__init__`'s `stage:` Args entry, `(e.g. "stage3", "stage3_rerun", "stage4")`

This plan's top-level SCOPE instruction restricts edits to `src/aquacal/calibration/pipeline.py` and its asserting tests only, explicitly deferring docstring/example surfaces in other files to plan 18-07 (which runs in parallel in this wave). Neither file is code that emits, reads, or asserts a `"stage4"` value in this codebase after this plan -- both are illustrative examples in an unrelated module's docstring. Flagging here so a follow-up (18-07 or a future doc pass) can sweep these two remaining examples if desired; they do not affect DOCS-06's must-haves, which are scoped to `pipeline.py`.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

`pipeline.py`'s `timings`/`internals/` schema is settled at `stage3_intrinsic_pass` before Phase 19 (BENCH-04) writes these keys into `benchmark.json`, per this plan's stated purpose. No blockers for 18-07 or 18-08, which proceed independently per 18-02-SUMMARY.md's per-plan verdict table.

---
*Phase: 18-documentation-corrections-stage-model-reconciliation*
*Completed: 2026-07-24*

## Self-Check: PASSED

- FOUND: `.planning/phases/18-documentation-corrections-stage-model-reconciliation/18-06-SUMMARY.md`
- FOUND: commit `8afddfc` (Task 1)
- FOUND: commit `e301ae9` (Task 2)
