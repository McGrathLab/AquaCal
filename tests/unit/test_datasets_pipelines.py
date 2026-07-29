"""Zero-numerical-change and export-surface tests for aquacal.datasets.pipelines."""

from __future__ import annotations

import numpy as np
import pytest

import aquacal.datasets.pipelines as pipelines_module
import tests.synthetic.experiment_helpers as experiment_helpers_shim
from aquacal.calibration._observability import SolverDiagnostics
from aquacal.core.board import BoardGeometry
from aquacal.datasets import create_scenario, generate_synthetic_detections
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

    board = BoardGeometry(scenario.board_config)
    errors = evaluate_reconstruction(result, board, detections)
    assert errors is not None


@pytest.mark.slow
def test_memory_out_default_unchanged():
    """Passing memory_out=None (the default) or omitting it entirely produce identical results."""
    scenario = create_scenario("minimal", seed=1)

    result_omitted, _ = calibrate_synthetic(scenario, **_MINIMAL_KWARGS)
    result_explicit_none, _ = calibrate_synthetic(
        scenario, **_MINIMAL_KWARGS, memory_out=None
    )

    np.testing.assert_array_equal(
        result_omitted.diagnostics.reprojection_error_rms,
        result_explicit_none.diagnostics.reprojection_error_rms,
    )
    for cam in result_omitted.cameras:
        np.testing.assert_array_equal(
            result_omitted.cameras[cam].extrinsics.R,
            result_explicit_none.cameras[cam].extrinsics.R,
        )
        np.testing.assert_array_equal(
            result_omitted.cameras[cam].extrinsics.t,
            result_explicit_none.cameras[cam].extrinsics.t,
        )
        np.testing.assert_array_equal(
            result_omitted.cameras[cam].water_z,
            result_explicit_none.cameras[cam].water_z,
        )


@pytest.mark.slow
def test_memory_out_populates_settled_keys():
    """A fresh memory_out dict is populated with _baseline and stage3_interface_optimization,
    each a dict with peak_bytes and mode keys, and no key outside the settled vocabulary."""
    scenario = create_scenario("minimal", seed=1)
    memory_out: dict[str, dict] = {}

    calibrate_synthetic(scenario, **_MINIMAL_KWARGS, memory_out=memory_out)

    assert "_baseline" in memory_out
    assert "stage3_interface_optimization" in memory_out
    allowed_keys = {
        "_baseline",
        "stage3_interface_optimization",
        "stage3_intrinsic_pass",
    }
    assert set(memory_out.keys()) <= allowed_keys
    for reading in memory_out.values():
        assert "peak_bytes" in reading
        assert "mode" in reading


def test_n_true_default_scenario_unchanged():
    """The shipped detection path at the default scenario index (1.333) exactly matches an
    explicit generate_synthetic_detections(n_air=1.0, n_water=1.333, ...) call."""
    scenario = create_scenario("minimal", seed=1)
    board = BoardGeometry(scenario.board_config)

    _, shipped_detections = calibrate_synthetic(
        scenario, n_water=1.333, refine_intrinsics=False, seed=1
    )

    explicit_detections = generate_synthetic_detections(
        intrinsics=scenario.intrinsics,
        extrinsics=scenario.extrinsics,
        water_zs=scenario.water_zs,
        board=board,
        board_poses=scenario.board_poses,
        noise_std=scenario.noise_std,
        seed=1,
        n_air=1.0,
        n_water=1.333,
    )

    for frame_idx, frame in shipped_detections.frames.items():
        for cam_name, detection in frame.detections.items():
            explicit_detection = explicit_detections.frames[frame_idx].detections[
                cam_name
            ]
            np.testing.assert_array_equal(
                detection.corners_2d, explicit_detection.corners_2d
            )


def test_n_true_scenario_index_reaches_detections():
    """Two scenarios identical except n_water=1.333 vs n_water=1.55 produce different
    detection corner arrays through calibrate_synthetic's own detection path.

    seed=3 (not 1): 19.2-18's D-27 recentred "minimal"'s board trajectory on
    the array centroid rather than the origin (a deliberate, non-inert
    change to this preset -- see 19.2-GAP-CONTEXT.md D-27's containment
    audit). seed=1's shifted (n_water=1.55) scenario no longer has any of
    its 10 frames retain 2+ camera visibility post-recentring -- a
    connectivity edge case inherent to "minimal"'s tiny 2-camera/10-frame
    geometry, not a defect in the recentring itself. seed=3 reliably
    retains connectivity for both scenarios.
    """
    scenario_default = create_scenario("minimal", seed=3)
    scenario_shifted = create_scenario("minimal", seed=3, n_water=1.55)

    _, detections_default = calibrate_synthetic(
        scenario_default, n_water=1.333, refine_intrinsics=False, seed=3
    )
    _, detections_shifted = calibrate_synthetic(
        scenario_shifted, n_water=1.333, refine_intrinsics=False, seed=3
    )

    common_frame_idx = next(iter(detections_default.frames))
    common_camera = next(iter(detections_default.frames[common_frame_idx].detections))
    corners_default = (
        detections_default.frames[common_frame_idx].detections[common_camera].corners_2d
    )
    corners_shifted = (
        detections_shifted.frames[common_frame_idx].detections[common_camera].corners_2d
    )

    assert not np.array_equal(corners_default, corners_shifted)


@pytest.mark.slow
def test_normal_fixed_default_unchanged():
    """Passing normal_fixed=True (the default) or omitting it entirely produce identical
    results — the guard that E1's and E7's committed records cannot have moved."""
    scenario = create_scenario("minimal", seed=1)

    result_omitted, _ = calibrate_synthetic(scenario, **_MINIMAL_KWARGS)
    result_explicit_true, _ = calibrate_synthetic(
        scenario, **_MINIMAL_KWARGS, normal_fixed=True
    )

    np.testing.assert_array_equal(
        result_omitted.diagnostics.reprojection_error_rms,
        result_explicit_true.diagnostics.reprojection_error_rms,
    )
    for cam in result_omitted.cameras:
        np.testing.assert_array_equal(
            result_omitted.cameras[cam].extrinsics.R,
            result_explicit_true.cameras[cam].extrinsics.R,
        )
        np.testing.assert_array_equal(
            result_omitted.cameras[cam].extrinsics.t,
            result_explicit_true.cameras[cam].extrinsics.t,
        )
        np.testing.assert_array_equal(
            result_omitted.cameras[cam].water_z,
            result_explicit_true.cameras[cam].water_z,
        )


@pytest.mark.slow
def test_normal_fixed_false_changes_problem_size():
    """With normal_fixed=False, stage3_interface_optimization's n_params is exactly 2
    greater than the same scenario at normal_fixed=True — proving the flag reaches the
    packer and adds the two interface-tilt DOF, rather than being accepted and dropped."""
    scenario = create_scenario("minimal", seed=1)

    diagnostics_fixed = {"stage3_interface_optimization": SolverDiagnostics()}
    calibrate_synthetic(
        scenario,
        n_water=1.0,
        refine_intrinsics=False,
        seed=1,
        diagnostics_out=diagnostics_fixed,
        normal_fixed=True,
    )

    diagnostics_tilted = {"stage3_interface_optimization": SolverDiagnostics()}
    calibrate_synthetic(
        scenario,
        n_water=1.0,
        refine_intrinsics=False,
        seed=1,
        diagnostics_out=diagnostics_tilted,
        normal_fixed=False,
    )

    n_params_fixed = diagnostics_fixed["stage3_interface_optimization"].n_params
    n_params_tilted = diagnostics_tilted["stage3_interface_optimization"].n_params
    assert n_params_tilted - n_params_fixed == 2
