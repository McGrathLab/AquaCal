---
phase: 14-optimization-extensions
status: passed
verified: 2026-02-28
requirements: [OPT-02, OPT-03]
---

# Phase 14: Optimization Extensions - Verification

## Goal
Callers can enable optional intrinsics refinement and apply robust loss functions to tolerate outlier observations.

## Success Criteria Verification

### 1. refine_intrinsics=True causes fx, fy, cx, cy to be optimized
- **Status:** PASS
- **Evidence:** `refine_intrinsics` parameter exists in `refine_calibration()` signature. When True, fx/fy/cx/cy are packed into the parameter vector and included in bundle adjustment. Test `test_intrinsics_change_when_enabled` proves intrinsics move toward ground truth when enabled.
- **File:** `src/aquacal/calibration/point_refinement.py` (lines 55-101, pack/unpack with intrinsics)

### 2. Intrinsics remain fixed when refine_intrinsics=False (default)
- **Status:** PASS
- **Evidence:** Default value is `False`. Test `test_intrinsics_fixed_when_disabled` uses `np.testing.assert_array_equal` to prove K matrices are identical before and after. Existing test `test_intrinsics_unchanged` also verifies this from Phase 13.
- **File:** `tests/unit/test_point_refinement.py` (TestIntrinsicsRefinement::test_intrinsics_fixed_when_disabled)

### 3. Caller can select Huber or Cauchy loss function
- **Status:** PASS
- **Evidence:** `loss` parameter accepts "linear", "huber", "cauchy". Invalid values raise `ValueError`. Test `test_valid_loss_values_accepted` proves all three are accepted. The `loss` and `f_scale` parameters are passed through to `scipy.optimize.least_squares`.
- **File:** `src/aquacal/calibration/point_refinement.py` (loss validation, least_squares call)

### 4. Robust loss reduces influence of high-residual correspondences
- **Status:** PASS
- **Evidence:** Tests `test_huber_reduces_outlier_influence` and `test_cauchy_reduces_outlier_influence` both prove that contaminated data (50-100px outlier shifts) produces lower clean-subset RMS with robust loss than with linear loss.
- **File:** `tests/unit/test_point_refinement.py` (TestRobustLoss class)

## Requirements Traceability

| Requirement | Description | Status |
|-------------|-------------|--------|
| OPT-02 | Optional intrinsics refinement (fx, fy, cx, cy per camera) | Verified |
| OPT-03 | Robust loss functions (Huber/Cauchy) for outlier tolerance | Verified |

## Test Results

```
28 passed in 13.98s
- 18 original Phase 13 tests: all pass (backward compatibility)
- 6 TestIntrinsicsRefinement tests: all pass
- 4 TestRobustLoss tests: all pass
```

## Self-Check: PASSED

All 4 success criteria verified. Both requirements (OPT-02, OPT-03) are satisfied.
No gaps found.
