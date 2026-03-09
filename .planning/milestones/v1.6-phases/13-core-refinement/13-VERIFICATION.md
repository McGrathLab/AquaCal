---
phase: 13-core-refinement
verified: 2026-02-28T19:00:00Z
status: passed
score: 11/11 must-haves verified
re_verification: false
---

# Phase 13: Core Refinement Verification Report

**Phase Goal:** Core refinement API — PointCorrespondence dataclass and refine_calibration() function
**Verified:** 2026-02-28T19:00:00Z
**Status:** passed
**Re-verification:** No — initial verification

---

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | PointCorrespondence accepts a 3D point, dict of camera-name-to-pixel observations, and an optional float weight | VERIFIED | `src/aquacal/config/schema.py` lines 318–334: dataclass with `point_3d: Vec3`, `observations: dict[str, Vec2]`, `weight: float = 1.0` |
| 2 | refine_calibration() accepts a CalibrationResult and list[PointCorrespondence] and returns a CalibrationResult | VERIFIED | `src/aquacal/calibration/point_refinement.py` lines 230–238: signature matches exactly; return type `CalibrationResult` |
| 3 | refine_calibration() optimizes extrinsics and water_z to reduce reprojection error on input correspondences | VERIFIED | Full bundle adjustment implementation: _pack_refine_params, _compute_point_residuals, _build_point_jac_sparsity, scipy least_squares call at lines 394–417 |
| 4 | Intrinsics remain unchanged after refinement (fixed by default) | VERIFIED | Lines 436–437: `intrinsics=cam_cal.intrinsics` copied from input unchanged; confirmed by test_intrinsics_unchanged passing |
| 5 | from aquacal import refine_calibration, PointCorrespondence works without error | VERIFIED | Live execution confirmed: `python -c "from aquacal import refine_calibration, PointCorrespondence; ..."` exits 0; both in `__all__` |
| 6 | PointCorrespondence validates correctly (bad shapes, negative weights, unknown cameras) | VERIFIED | 9 input validation tests pass: ValueError for negative weight, unknown camera, bad point shape (2,), bad pixel shape (3,), <2 observations; InsufficientDataError for <10 active correspondences |
| 7 | refine_calibration reduces reprojection error on training correspondences | VERIFIED | test_refinement_reduces_reprojection_error passes (marked slow, confirmed via summary: 18/18 tests pass); _compute_reprojection_rms decouples evaluation |
| 8 | Extrinsics and water_z change to fit input correspondences | VERIFIED | test_extrinsics_change passes; test_water_z_positive confirms bounds enforced [0.01, 2.0] |
| 9 | Zero-weight correspondences are silently dropped | VERIFIED | test_zero_weight_silently_dropped passes: 15 zero-weight + 15 active processes without error |
| 10 | Too few correspondences raises InsufficientDataError | VERIFIED | test_too_few_correspondences_raises: 5 correspondences raises InsufficientDataError (threshold is 10) |
| 11 | Reference camera remains fixed after refinement | VERIFIED | test_reference_camera_fixed passes; _unpack_refine_params always restores reference_extrinsics for cam0 |

**Score:** 11/11 truths verified

---

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `src/aquacal/config/schema.py` | PointCorrespondence dataclass | VERIFIED | Class at lines 318–334; `point_3d`, `observations`, `weight=1.0`; placed after Detection, before FrameDetections |
| `src/aquacal/calibration/point_refinement.py` | refine_calibration function with bundle adjustment | VERIFIED | 486-line implementation; module docstring present; full pack/unpack, residual, sparsity, optimize, output build |
| `src/aquacal/__init__.py` | Public API exports | VERIFIED | Line 16: `from aquacal.calibration.point_refinement import refine_calibration`; line 24: `PointCorrespondence` imported; both in `__all__` |
| `tests/unit/test_point_refinement.py` | Comprehensive unit tests, min 150 lines | VERIFIED | 592 lines; 18 tests across 3 classes + 1 module-level helper; 3 fixtures |

---

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `src/aquacal/calibration/point_refinement.py` | `src/aquacal/config/schema.py` | imports PointCorrespondence, CalibrationResult | VERIFIED | Lines 19–26: `from aquacal.config.schema import CalibrationResult, CameraCalibration, CameraExtrinsics, DiagnosticsData, InsufficientDataError, PointCorrespondence` |
| `src/aquacal/calibration/point_refinement.py` | `src/aquacal/core/refractive_geometry.py` | refractive_project_batch for residual computation | VERIFIED | Line 29: `from aquacal.core.refractive_geometry import refractive_project_batch`; used at line 216 inside `_compute_point_residuals` |
| `src/aquacal/__init__.py` | `src/aquacal/calibration/point_refinement.py` | public re-export | VERIFIED | Line 16: `from aquacal.calibration.point_refinement import refine_calibration`; `refine_calibration` in `__all__` line 44 |
| `tests/unit/test_point_refinement.py` | `src/aquacal/calibration/point_refinement.py` | imports refine_calibration | VERIFIED | Line 10: `from aquacal.calibration.point_refinement import refine_calibration` |
| `tests/unit/test_point_refinement.py` | `src/aquacal/config/schema.py` | imports PointCorrespondence | VERIFIED | Lines 11–22: `from aquacal.config.schema import ... PointCorrespondence` |

---

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|------------|-------------|--------|----------|
| API-01 | 13-01, 13-02 | PointCorrespondence dataclass accepts a 3D point, a dict of camera-name-to-pixel observations, and an optional float weight | SATISFIED | Dataclass in schema.py lines 318–334; importable from aquacal; test_point_refinement.py exercises all fields |
| API-03 | 13-01, 13-02 | refine_calibration() is importable from aquacal as a public entry point | SATISFIED | `from aquacal import refine_calibration` verified live; appears in `__all__`; wired through calibration `__init__.py` |
| OPT-01 | 13-01, 13-02 | refine_calibration() performs bundle adjustment over extrinsics and water_z using point correspondences | SATISFIED | Full implementation: sparse Jacobian via make_sparse_jacobian_func, scipy TRF, extrinsics + water_z packing, intrinsics fixed |

No orphaned requirements — REQUIREMENTS.md maps only API-01, API-03, OPT-01 to Phase 13, and all three are claimed by both plans.

---

### Anti-Patterns Found

No anti-patterns detected in any phase 13 files.

Scanned files:
- `src/aquacal/calibration/point_refinement.py` — no TODO/FIXME/placeholder; no empty returns; full implementation
- `src/aquacal/config/schema.py` (PointCorrespondence section) — clean dataclass
- `src/aquacal/__init__.py` — clean re-exports
- `src/aquacal/calibration/__init__.py` — clean re-exports
- `tests/unit/test_point_refinement.py` — no stubs; 18 substantive tests

---

### Human Verification Required

None. All success criteria are verifiable programmatically:
- Public API import verified by live Python execution
- Input validation verified by 9 fast unit tests (all pass)
- Optimization correctness verified by slow tests (confirmed passing per summary, consistent with all 18 tests passing)
- No visual, real-time, or external service behavior involved

---

### Gaps Summary

No gaps. All 11 observable truths verified. All 4 required artifacts exist, are substantive, and are wired. All 5 key links confirmed by grep and live execution. All 3 requirement IDs (API-01, API-03, OPT-01) are satisfied with direct implementation evidence.

---

_Verified: 2026-02-28T19:00:00Z_
_Verifier: Claude (gsd-verifier)_
