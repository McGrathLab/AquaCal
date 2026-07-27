"""Zero-numerical-change and export-surface tests for aquacal.datasets.pipelines."""

from __future__ import annotations

import numpy as np
import pytest

import aquacal.datasets.pipelines as pipelines_module
import tests.synthetic.experiment_helpers as experiment_helpers_shim
from aquacal.datasets import create_scenario
from aquacal.datasets.pipelines import (
    calibrate_synthetic,
    compute_per_camera_errors,
    evaluate_reconstruction,
)

_MINIMAL_KWARGS = dict(n_water=1.0, refine_intrinsics=False, seed=1)


def _minimal_result():
    """Calibrate the cheap 'minimal' scenario with intrinsics held at ground truth."""
    scenario = create_scenario("minimal", seed=1)
    result, detections = calibrate_synthetic(scenario, **_MINIMAL_KWARGS)
    return scenario, result, detections


def test_shim_reexports():
    """tests.synthetic.experiment_helpers re-exports pipelines.py's verbs by identity."""
    assert (
        experiment_helpers_shim.calibrate_synthetic
        is pipelines_module.calibrate_synthetic
    )
    assert (
        experiment_helpers_shim.compute_per_camera_errors
        is pipelines_module.compute_per_camera_errors
    )
    assert (
        experiment_helpers_shim.evaluate_reconstruction
        is pipelines_module.evaluate_reconstruction
    )


def test_widened_keys_present():
    """All twelve documented keys appear for every camera's error dict."""
    scenario, result, _ = _minimal_result()
    errors = compute_per_camera_errors(result, scenario)

    expected_keys = {
        "focal_length_error_pct",
        "z_position_error_mm",
        "xy_position_error_mm",
        "k1_error",
        "k2_error",
        "gt_x_m",
        "gt_y_m",
        "gt_z_m",
        "est_x_m",
        "est_y_m",
        "est_z_m",
        "reprojection_rms_px",
    }
    assert errors  # non-empty
    for cam_errors in errors.values():
        assert set(cam_errors.keys()) == expected_keys


def test_default_unchanged_gauge():
    """Default gauge_correct_z=False leaves z_position_error_mm at its raw value."""
    scenario, result, _ = _minimal_result()
    errors = compute_per_camera_errors(result, scenario)

    for cam_name, cam_errors in errors.items():
        C_gt = scenario.extrinsics[cam_name].C
        C_cal = result.cameras[cam_name].extrinsics.C
        raw_z_error_mm = (C_cal[2] - C_gt[2]) * 1000
        np.testing.assert_array_equal(cam_errors["z_position_error_mm"], raw_z_error_mm)


def test_gauge_correction_subtracts_free_camera_mean():
    """gauge_correct_z=True subtracts the free-camera mean raw Z error from every camera,
    including the reference camera, which is not left at exactly 0.0."""
    scenario, result, _ = _minimal_result()
    raw_errors = compute_per_camera_errors(result, scenario, gauge_correct_z=False)
    corrected_errors = compute_per_camera_errors(result, scenario, gauge_correct_z=True)

    camera_names = sorted(scenario.intrinsics, key=lambda s: int(s.replace("cam", "")))
    reference_camera = camera_names[0]
    free_cameras = [c for c in camera_names if c != reference_camera]

    mean_free_raw_z = np.mean(
        [raw_errors[c]["z_position_error_mm"] for c in free_cameras]
    )

    for cam_name in camera_names:
        expected = raw_errors[cam_name]["z_position_error_mm"] - mean_free_raw_z
        np.testing.assert_array_equal(
            corrected_errors[cam_name]["z_position_error_mm"], expected
        )

    # The reference camera's corrected Z error must not be a hardcoded zero.
    assert corrected_errors[reference_camera]["z_position_error_mm"] != 0.0


def test_reference_camera_xy_error_is_exactly_zero():
    """The reference camera's xy_position_error_mm is exactly 0.0 regardless of gauge_correct_z."""
    scenario, result, _ = _minimal_result()
    camera_names = sorted(scenario.intrinsics, key=lambda s: int(s.replace("cam", "")))
    reference_camera = camera_names[0]

    for gauge_correct_z in (False, True):
        errors = compute_per_camera_errors(
            result, scenario, gauge_correct_z=gauge_correct_z
        )
        assert errors[reference_camera]["xy_position_error_mm"] == 0.0


@pytest.mark.slow
def test_seed_threads_through():
    """calibrate_synthetic(seed=7) is deterministic and differs from seed=8."""
    scenario = create_scenario("minimal", seed=1)

    result_a, _ = calibrate_synthetic(
        scenario, n_water=1.0, refine_intrinsics=False, seed=7
    )
    result_b, _ = calibrate_synthetic(
        scenario, n_water=1.0, refine_intrinsics=False, seed=7
    )
    result_c, _ = calibrate_synthetic(
        scenario, n_water=1.0, refine_intrinsics=False, seed=8
    )

    for cam in result_a.cameras:
        np.testing.assert_array_equal(
            result_a.cameras[cam].extrinsics.R, result_b.cameras[cam].extrinsics.R
        )
        np.testing.assert_array_equal(
            result_a.cameras[cam].extrinsics.t, result_b.cameras[cam].extrinsics.t
        )
    np.testing.assert_array_equal(
        result_a.diagnostics.reprojection_error_rms,
        result_b.diagnostics.reprojection_error_rms,
    )

    same_extrinsics = all(
        np.array_equal(
            result_a.cameras[cam].extrinsics.t, result_c.cameras[cam].extrinsics.t
        )
        for cam in result_a.cameras
    )
    assert not same_extrinsics


@pytest.mark.slow
def test_bit_exact_repeat():
    """Two identical-argument calibrate_synthetic calls are bit-exact."""
    scenario = create_scenario("minimal", seed=1)

    result_1, _ = calibrate_synthetic(
        scenario, n_water=1.0, refine_intrinsics=False, seed=3
    )
    result_2, _ = calibrate_synthetic(
        scenario, n_water=1.0, refine_intrinsics=False, seed=3
    )

    np.testing.assert_array_equal(
        result_1.diagnostics.reprojection_error_rms,
        result_2.diagnostics.reprojection_error_rms,
    )
    for cam in result_1.cameras:
        np.testing.assert_array_equal(
            result_1.cameras[cam].extrinsics.R, result_2.cameras[cam].extrinsics.R
        )
        np.testing.assert_array_equal(
            result_1.cameras[cam].extrinsics.t, result_2.cameras[cam].extrinsics.t
        )
        np.testing.assert_array_equal(
            result_1.cameras[cam].water_z, result_2.cameras[cam].water_z
        )


def test_evaluate_reconstruction_signature_frozen():
    """evaluate_reconstruction's positional argument order stays (calibration, board, test_detections)."""
    scenario, result, detections = _minimal_result()
    from aquacal.core.board import BoardGeometry

    board = BoardGeometry(scenario.board_config)
    errors = evaluate_reconstruction(result, board, detections)
    assert errors is not None
