---
phase: 16-experiment-observability-hooks
plan: 07
subsystem: validation
tags: [evaluate_calibration, held-out-evaluation, refractive-index, public-api, regression-test]

# Dependency graph
requires:
  - phase: 16-06
    provides: seed threading & recording in CalibrationMetadata
provides:
  - "aquacal.evaluate_calibration top-level export (standalone held-out evaluation)"
  - "aquacal.validation.evaluation.HeldOutEvaluation container type"
  - "One shared held-out evaluation code path used by both the pipeline and standalone callers"
affects: [17-per-camera-interface-ablation-mode, 21-new-feature-documentation-and-dataset-refresh]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Function-local import to avoid an import cycle (aquacal.validation.evaluation lazily imports aquacal.calibration.interface_estimation._compute_initial_board_poses inside evaluate_calibration, not at module level)"
    - "Duplicated a tiny filtering helper (_filter_calibration_cameras) rather than importing pipeline's private _filter_cameras, to keep validation/ independent of calibration/pipeline.py"

key-files:
  created:
    - src/aquacal/validation/evaluation.py
    - tests/unit/test_evaluation.py
  modified:
    - src/aquacal/validation/__init__.py
    - src/aquacal/__init__.py
    - src/aquacal/calibration/pipeline.py
    - tests/unit/test_pipeline.py

key-decisions:
  - "evaluate_calibration takes no n_water override parameter; n_air/n_water/normal always come from calibration.interface, and the WP4 'perturbed assumption' use case is encoded in the held-out detections instead"
  - "HeldOutEvaluation is a thin container around the pipeline's existing ReprojectionErrors/DistanceErrors types, not a new metric type, so standalone and pipeline-internal numbers stay directly comparable"
  - "Marked evaluate_calibration/HeldOutEvaluation stable, since CONTEXT.md places it in the deliberately small public API and its fields are pre-existing types"

patterns-established:
  - "Zero-numerical-change refactors of pipeline internals must ship with an exact-equality (not approx) regression test written before the refactor, replicating the pre-refactor sequence literally at the seam"

requirements-completed: [HOOK-04]

# Metrics
duration: 55min
completed: 2026-07-23
---

# Phase 16 Plan 07: Standalone Held-Out Evaluation (HOOK-04) Summary

**`aquacal.evaluate_calibration(calibration, detections, board)` scores any calibration against any held-out detection set standalone (no pipeline, no videos), sharing one implementation with the pipeline via a bit-identical regression test.**

## Performance

- **Duration:** ~55 min
- **Tasks:** 3
- **Files modified:** 6 (2 created, 4 modified)

## Accomplishments
- New `aquacal.validation.evaluation` module: `HeldOutEvaluation` dataclass + `evaluate_calibration()`, which estimates held-out board poses from the FULL calibration, then computes `ReprojectionErrors`/`DistanceErrors` (optionally camera-filtered, optionally reusing supplied poses).
- `evaluate_calibration` exported as `aquacal.evaluate_calibration` (16th top-level public name) and from `aquacal.validation`, alongside `HeldOutEvaluation`.
- `_estimate_validation_poses` moved verbatim from `pipeline.py` into `validation/evaluation.py`; pipeline now imports it.
- `run_calibration_from_config`'s inline held-out block (pose estimation + primary/auxiliary reprojection + 3D reconstruction) replaced with two `evaluate_calibration` calls (primary, then auxiliary reusing primary's poses), with all console output, the `timings["validation"]` key, and the `spatial_measurements.csv` write byte-identical to before.
- Exact-equality regression test (`test_matches_legacy_inline_sequence`) proves `evaluate_calibration` reproduces the pre-refactor inline sequence bit for bit — not approximated.
- Executable WP4 test (`test_evaluate_detects_perturbed_refractive_index`): scoring a calibration against a held-out set generated at a different `n_water` produces measurably (>2x) worse reprojection error than scoring against the matched-index set.

## Task Commits

Each task was committed atomically (split further where a file spanned multiple concerns):

1. **Task 1: Create validation/evaluation.py and export it** - `c5c8218` (feat) + `f04a093` (test, combined with task 2's regression test — see below)
2. **Task 2: Write the legacy-equivalence regression test** - included in `f04a093` (test)
3. **Task 3: Refactor the pipeline to call evaluate_calibration** - `c27c747` (refactor) + `375e1a1` (test: mock retargeting + refactor guard tests)

**Plan metadata:** (this commit) `docs(16-07): complete standalone held-out evaluation plan`

## Files Created/Modified
- `src/aquacal/validation/evaluation.py` - `HeldOutEvaluation`, `evaluate_calibration`, moved `_estimate_validation_poses`
- `src/aquacal/validation/__init__.py` - exports `evaluate_calibration`/`HeldOutEvaluation`
- `src/aquacal/__init__.py` - top-level `evaluate_calibration` export
- `src/aquacal/calibration/pipeline.py` - held-out block now calls `evaluate_calibration`; `_estimate_validation_poses` removed (imported instead); `compute_3d_distance_errors` import dropped (no longer called directly)
- `tests/unit/test_evaluation.py` - standalone behaviour tests + `test_matches_legacy_inline_sequence`
- `tests/unit/test_pipeline.py` - retargeted `compute_reprojection_errors`/`compute_3d_distance_errors` mocks to `aquacal.validation.evaluation` (they're no longer called through a pipeline-local reference); added `TestSharedEvaluationRefactor` (2 new tests)

## Decisions Made
- No `n_water` override parameter on `evaluate_calibration` — matches CONTEXT.md's locked decision that the "perturbed assumption" lives in the held-out detections, not the calibration being scored.
- Duplicated a small camera-filtering helper (`_filter_calibration_cameras`) inside `validation/evaluation.py` instead of importing `pipeline._filter_cameras`, per the plan's explicit instruction to keep `validation/` independent of `calibration/pipeline.py`.
- Marked both new symbols stable in their docstrings (plan left this to discretion; stable was appropriate given CONTEXT.md's explicit placement in the small public API).

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Retargeted two pre-existing test mocks broken by the refactor**
- **Found during:** Task 3 (pipeline refactor)
- **Issue:** `tests/unit/test_pipeline.py` had two fixtures (`TestRunCalibrationFromConfig.mock_calibration_stages`, `TestAuxiliaryCameraSeparation.mock_calibration_stages_with_aux`) that patched `aquacal.calibration.pipeline.compute_reprojection_errors` / `.compute_3d_distance_errors`. After the refactor, the held-out block calls these functions through `evaluate_calibration`'s own imports in `aquacal.validation.evaluation`, not through pipeline-module-level references, so the patches silently stopped intercepting calls (and `compute_3d_distance_errors` was no longer even imported in `pipeline.py`, which would have raised `AttributeError` on patch).
- **Fix:** Retargeted both patches to `aquacal.validation.evaluation.compute_reprojection_errors` / `.compute_3d_distance_errors`.
- **Files modified:** `tests/unit/test_pipeline.py`
- **Verification:** `python -m pytest tests/unit/test_pipeline.py -q` — 74 passed (was 72 before Task 3's two new tests).
- **Committed in:** `375e1a1` (Task 3 test commit)

---

**Total deviations:** 1 auto-fixed (Rule 1 — bug in test mocking exposed by the refactor)
**Impact on plan:** Necessary to keep the existing test suite meaningful (rather than silently testing nothing); no scope creep beyond what the refactor required.

## Issues Encountered
None beyond the deviation above.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- HOOK-04 is complete; all six HOOK requirements for Phase 16 are now done.
- `aquacal.evaluate_calibration` is ready for the WP4 experiment script (score a calibration against ground truth generated at a different refractive index).
- Full test suite green: 763 passed (`python -m pytest tests/`, including slow tests), 734 passed / 29 deselected (`-m "not slow"`).
- Phase 17 (Per-Camera Interface Ablation Mode) can proceed; it depends on Phase 16's HOOK-03 conditioning diagnostics (already shipped in plan 16-05), not on this plan directly.

## Self-Check: PASSED

- FOUND: src/aquacal/validation/evaluation.py
- FOUND: tests/unit/test_evaluation.py
- FOUND: .planning/phases/16-experiment-observability-hooks/16-07-SUMMARY.md
- FOUND commit: c5c8218
- FOUND commit: f04a093
- FOUND commit: c27c747
- FOUND commit: 375e1a1

---
*Phase: 16-experiment-observability-hooks*
*Completed: 2026-07-23*
