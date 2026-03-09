---
status: complete
phase: 15-validation-and-result-contract
source: 15-VERIFICATION.md, 15-01-PLAN.md, 15-02-PLAN.md
started: 2026-02-28T12:00:00Z
updated: 2026-02-28T12:08:00Z
---

## Current Test

[testing complete]

## Tests

### 1. Public API Exports
expected: Running `python -c "from aquacal import RefinementResult, ValidationReport, CameraDrift; print('OK')"` prints "OK" without errors.
result: pass

### 2. refine_calibration Returns RefinementResult
expected: Running `python -c "from aquacal import refine_calibration; import inspect; sig = inspect.signature(refine_calibration); print(sig.return_annotation)"` shows `RefinementResult` as the return annotation.
result: pass

### 3. ValidationReport Contains All Required Fields
expected: `ValidationReport` has fields: `holdout_reproj_error` (float), `triangulation_consistency_before` (float), `triangulation_consistency_after` (float), `camera_drifts` (dict), `accepted` (bool), `summary` (str). Verify with: `python -c "from aquacal import ValidationReport; import dataclasses; print([f.name for f in dataclasses.fields(ValidationReport)])"`.
result: pass

### 4. CameraDrift Contains Per-Camera Metrics
expected: `CameraDrift` has fields: `translation_mm` (float), `rotation_deg` (float), `exceeded` (bool). Verify with: `python -c "from aquacal import CameraDrift; import dataclasses; print([f.name for f in dataclasses.fields(CameraDrift)])"`.
result: pass

### 5. Validation Unit Tests Pass
expected: Running `python -m pytest tests/unit/test_validation.py -v` shows all 15 tests passing (holdout split, extrinsics drift, validation report logic).
result: pass

### 6. Point Refinement Tests Pass with RefinementResult
expected: Running `python -m pytest tests/unit/test_point_refinement.py -v -m "not slow"` shows all fast tests passing, confirming existing tests were updated for the new return type.
result: pass

### 7. Full Test Suite (Non-Slow) Passes
expected: Running `python -m pytest tests/ -m "not slow"` shows all ~610 tests passing with no failures.
result: pass

## Summary

total: 7
passed: 7
issues: 0
pending: 0
skipped: 0

## Gaps

[none yet]
