---
phase: 15
status: passed
verified: 2026-02-28
---

# Phase 15: Validation and Result Contract - Verification

## Phase Goal
Callers receive a `RefinementResult` with a structured validation report and a clear accept/reject recommendation they can act on.

## Success Criteria Verification

| # | Criterion | Status | Evidence |
|---|-----------|--------|----------|
| 1 | `refine_calibration()` returns `RefinementResult` containing `CalibrationResult`, `ValidationReport`, and `accepted` boolean | PASS | Return annotation is `RefinementResult`; dataclass has fields `result`, `validation_report`, `accepted` |
| 2 | `ValidationReport` contains holdout reprojection error on configurable held-out fraction | PASS | `holdout_reproj_error` field; `holdout_fraction` param (default 0.2); `holdout_seed` param for reproducibility |
| 3 | `ValidationReport` contains triangulation consistency metric (before/after) | PASS | `triangulation_consistency_before` and `triangulation_consistency_after` fields measure ray intersection tightness |
| 4 | `ValidationReport` flags extrinsics drift with per-camera details | PASS | `camera_drifts: dict[str, CameraDrift]` with `translation_mm`, `rotation_deg`, `exceeded` per camera |
| 5 | `accepted` is `False` when any threshold exceeded | PASS | `build_validation_report()` uses any-fail logic; tested in `test_any_fail_rejects`, `test_reproj_fail` |

## Requirement Coverage

| Requirement | Status | Implementation |
|-------------|--------|----------------|
| VAL-01 | Complete | `split_holdout()` + `compute_holdout_reproj_error()` in `validation.py` |
| VAL-02 | Complete | `compute_triangulation_consistency()` in `validation.py` |
| VAL-03 | Complete | `compute_extrinsics_drift()` in `validation.py` |
| VAL-04 | Complete | `ValidationReport` dataclass + `build_validation_report()` |
| API-02 | Complete | `RefinementResult` dataclass in `schema.py`, exported from `aquacal` |

## Test Coverage

- `tests/unit/test_validation.py`: 15 tests covering holdout split, extrinsics drift, validation report logic
- `tests/unit/test_point_refinement.py`: 30 tests (13 fast, 17 slow) updated for `RefinementResult`, plus 2 new validation integration tests
- All 610 tests pass (`python -m pytest tests/ -m "not slow"`)

## Key Files

| File | Change |
|------|--------|
| `src/aquacal/config/schema.py` | Added `CameraDrift`, `ValidationReport`, `RefinementResult` dataclasses |
| `src/aquacal/calibration/validation.py` | NEW: holdout, reproj error, triangulation consistency, drift, report builder |
| `src/aquacal/calibration/point_refinement.py` | Updated `refine_calibration()` return type and added validation pipeline |
| `src/aquacal/__init__.py` | Exported `RefinementResult`, `ValidationReport`, `CameraDrift` |
| `tests/unit/test_validation.py` | NEW: 15 unit tests for validation module |
| `tests/unit/test_point_refinement.py` | Updated 30 tests + 2 new validation integration tests |
