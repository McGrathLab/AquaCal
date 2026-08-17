"""Unit tests for `experiments/e1_refractive_comparison.py`'s `compute_xyz_errors`.

This covers the one genuinely novel piece of E1's ported logic (see
`experiments/e1_refractive_comparison.py`'s `compute_xyz_errors`, ported from
`docs/tutorials/02_synthetic_validation.ipynb` cell `jq300wte3tn`). These are
fast unit tests -- minimal fixtures constructed directly, no `create_scenario`,
no calibration, none are marked slow.
"""

from __future__ import annotations

import numpy as np
import pytest

from aquacal.config.schema import (
    BoardConfig,
    BoardPose,
    CalibrationMetadata,
    CalibrationResult,
    CameraCalibration,
    CameraExtrinsics,
    CameraIntrinsics,
    Detection,
    DetectionResult,
    DiagnosticsData,
    FrameDetections,
    InterfaceParams,
)
from aquacal.core.board import BoardGeometry
from aquacal.core.camera import Camera
from aquacal.core.interface_model import Interface
from aquacal.core.refractive_geometry import refractive_project
from aquacal.datasets import create_scenario
from experiments.e1_refractive_comparison import (
    _run_one_model,
    build_water_z_provenance,
    compute_xyz_errors,
    resolve_water_z_pin,
)


@pytest.fixture
def board_config():
    """Small ChArUco board config, matching E1's test-fixture scale."""
    return BoardConfig(
        squares_x=5,
        squares_y=4,
        square_size=0.04,
        marker_size=0.03,
        dictionary="DICT_4X4_50",
    )


@pytest.fixture
def board_geometry(board_config):
    return BoardGeometry(board_config)


@pytest.fixture
def interface_params():
    return InterfaceParams(
        normal=np.array([0.0, 0.0, -1.0]),
        n_air=1.0,
        n_water=1.333,
    )


@pytest.fixture
def camera_intrinsics():
    return CameraIntrinsics(
        K=np.array([[800.0, 0.0, 320.0], [0.0, 800.0, 240.0], [0.0, 0.0, 1.0]]),
        dist_coeffs=np.zeros(5),
        image_size=(640, 480),
    )


def _make_calibration(camera_intrinsics, interface_params, board_config):
    cam1 = CameraCalibration(
        name="cam1",
        intrinsics=camera_intrinsics,
        extrinsics=CameraExtrinsics(R=np.eye(3), t=np.array([0.0, 0.0, 0.5])),
        water_z=0.3,
    )
    cam2 = CameraCalibration(
        name="cam2",
        intrinsics=camera_intrinsics,
        extrinsics=CameraExtrinsics(
            R=np.array([[0.866, 0.0, 0.5], [0.0, 1.0, 0.0], [-0.5, 0.0, 0.866]]),
            t=np.array([0.2, 0.0, 0.5]),
        ),
        water_z=0.3,
    )
    diagnostics = DiagnosticsData(
        reprojection_error_rms=0.0,
        reprojection_error_per_camera={},
        validation_3d_error_mean=0.0,
        validation_3d_error_std=0.0,
    )
    metadata = CalibrationMetadata(
        calibration_date="2025-01-01",
        software_version="0.1.0",
        config_hash="test",
        num_frames_used=0,
        num_frames_holdout=0,
    )
    return CalibrationResult(
        cameras={"cam1": cam1, "cam2": cam2},
        interface=interface_params,
        board=board_config,
        diagnostics=diagnostics,
        metadata=metadata,
    )


def _make_detections(calibration, corner_ids, corner_positions_3d, frame_idx=0):
    """Project known 3D corner positions into pixel detections for both cameras."""
    frame_detections = {}
    for cam_name, cam_calib in calibration.cameras.items():
        camera = Camera(cam_name, cam_calib.intrinsics, cam_calib.extrinsics)
        interface = Interface(
            normal=calibration.interface.normal,
            camera_distances={cam_name: cam_calib.water_z},
            n_air=calibration.interface.n_air,
            n_water=calibration.interface.n_water,
        )
        detected_ids = []
        detected_pixels = []
        for corner_id in corner_ids:
            pixel = refractive_project(
                camera, interface, corner_positions_3d[corner_id]
            )
            if pixel is not None:
                detected_ids.append(corner_id)
                detected_pixels.append(pixel)
        if detected_ids:
            frame_detections[cam_name] = Detection(
                corner_ids=np.array(detected_ids, dtype=np.int32),
                corners_2d=np.array(detected_pixels, dtype=np.float64),
            )
    frame_det = FrameDetections(frame_idx=frame_idx, detections=frame_detections)
    return DetectionResult(
        frames={frame_idx: frame_det},
        camera_names=list(calibration.cameras.keys()),
        total_frames=1,
    )


def _corner_ground_truth_positions(board_geometry, corner_ids, tvec):
    """GT corner positions at identity rotation (R_board = I), given tvec."""
    return {cid: board_geometry.corner_positions[cid] + tvec for cid in corner_ids}


def test_compute_xyz_errors_decomposes_known_offset(
    board_config, board_geometry, interface_params, camera_intrinsics
):
    """A pure-Z offset between triangulated and GT positions is recovered as z_rmse_mm."""
    calibration = _make_calibration(camera_intrinsics, interface_params, board_config)
    corner_ids = [0, 1, 2, 3, 4]
    tvec = np.array([0.0, 0.0, 0.6])
    gt_positions = _corner_ground_truth_positions(board_geometry, corner_ids, tvec)

    z_offset = 0.01  # 10 mm known Z offset
    true_positions = {
        cid: pos + np.array([0.0, 0.0, z_offset]) for cid, pos in gt_positions.items()
    }
    test_detections = _make_detections(calibration, corner_ids, true_positions)

    board_pose = BoardPose(frame_idx=0, rvec=np.zeros(3), tvec=tvec)
    test_poses = [board_pose]

    result = compute_xyz_errors(
        calibration, test_poses, test_detections, board_geometry
    )

    # Triangulation itself carries a small numerical residual (sub-0.1mm, from the
    # refractive back-projection solve) -- the tolerance below recovers the *known*
    # offset, not exact zero-noise reproduction.
    assert result["z_rmse_mm"] == pytest.approx(z_offset * 1000, abs=0.1)
    assert result["xy_rmse_mm"] == pytest.approx(0.0, abs=0.1)


def test_compute_xyz_errors_decomposes_known_xy_offset(
    board_config, board_geometry, interface_params, camera_intrinsics
):
    """The mirror case: a pure-XY offset is recovered as xy_rmse_mm, z_rmse_mm near zero."""
    calibration = _make_calibration(camera_intrinsics, interface_params, board_config)
    corner_ids = [0, 1, 2, 3, 4]
    tvec = np.array([0.0, 0.0, 0.6])
    gt_positions = _corner_ground_truth_positions(board_geometry, corner_ids, tvec)

    xy_offset = 0.008  # 8 mm known XY offset (along X only)
    true_positions = {
        cid: pos + np.array([xy_offset, 0.0, 0.0]) for cid, pos in gt_positions.items()
    }
    test_detections = _make_detections(calibration, corner_ids, true_positions)

    board_pose = BoardPose(frame_idx=0, rvec=np.zeros(3), tvec=tvec)
    test_poses = [board_pose]

    result = compute_xyz_errors(
        calibration, test_poses, test_detections, board_geometry
    )

    assert result["xy_rmse_mm"] == pytest.approx(xy_offset * 1000, abs=0.1)
    assert result["z_rmse_mm"] == pytest.approx(0.0, abs=0.1)


def test_compute_xyz_errors_anisotropy_ratio(
    board_config, board_geometry, interface_params, camera_intrinsics
):
    """anisotropy_ratio == z_rmse_mm / xy_rmse_mm; n_points == triangulated corner count."""
    calibration = _make_calibration(camera_intrinsics, interface_params, board_config)
    corner_ids = [0, 1, 2, 3, 4]
    tvec = np.array([0.0, 0.0, 0.6])
    gt_positions = _corner_ground_truth_positions(board_geometry, corner_ids, tvec)

    offset = np.array([0.006, 0.0, 0.02])
    true_positions = {cid: pos + offset for cid, pos in gt_positions.items()}
    test_detections = _make_detections(calibration, corner_ids, true_positions)

    board_pose = BoardPose(frame_idx=0, rvec=np.zeros(3), tvec=tvec)
    test_poses = [board_pose]

    result = compute_xyz_errors(
        calibration, test_poses, test_detections, board_geometry
    )

    assert result["ratio"] == pytest.approx(
        result["z_rmse_mm"] / result["xy_rmse_mm"], rel=1e-9
    )
    assert result["n_points"] == len(corner_ids)


def test_compute_xyz_errors_deterministic(
    board_config, board_geometry, interface_params, camera_intrinsics
):
    """Two calls on identical inputs give bit-identical results."""
    calibration = _make_calibration(camera_intrinsics, interface_params, board_config)
    corner_ids = [0, 1, 2, 3, 4]
    tvec = np.array([0.0, 0.0, 0.6])
    gt_positions = _corner_ground_truth_positions(board_geometry, corner_ids, tvec)

    offset = np.array([0.006, 0.0, 0.02])
    true_positions = {cid: pos + offset for cid, pos in gt_positions.items()}
    test_detections = _make_detections(calibration, corner_ids, true_positions)

    board_pose = BoardPose(frame_idx=0, rvec=np.zeros(3), tvec=tvec)
    test_poses = [board_pose]

    result_1 = compute_xyz_errors(
        calibration, test_poses, test_detections, board_geometry
    )
    result_2 = compute_xyz_errors(
        calibration, test_poses, test_detections, board_geometry
    )

    for key in ("xy_rmse_mm", "z_rmse_mm", "ratio", "n_points"):
        np.testing.assert_array_equal(result_1[key], result_2[key])


# ---------------------------------------------------------------------------
# D-19.3-11 / plan 19.3-07: E1 records (never gates on) the final-solution
# guard count.
# ---------------------------------------------------------------------------


def test_run_one_model_records_degenerate_count():
    """_run_one_model returns a discard_stats dict whose
    degenerate_observations_at_solution key is present and integer-typed on
    a clean run -- the package's cheap "minimal" preset, refine_intrinsics
    left at _run_one_model's own default (True), matching E1's real call
    shape."""
    scenario = create_scenario("minimal", seed=1)
    (
        _result,
        _detections,
        _timings,
        _diagnostics,
        discard_stats,
        _water_z_pin,
    ) = _run_one_model(scenario, n_water=1.333, seed=1)
    assert "degenerate_observations_at_solution" in discard_stats
    assert isinstance(discard_stats["degenerate_observations_at_solution"], int)


def test_run_one_model_never_raises_on_a_positive_count():
    """create_scenario("ideal") legitimately trips the guard (extreme
    obliquity, not a breached interface, per 19.3-ORCHESTRATOR-NOTES.md
    section 4) -- _run_one_model must complete and record the count, never
    raise."""
    scenario = create_scenario("ideal", seed=1)
    (
        _result,
        _detections,
        _timings,
        _diagnostics,
        discard_stats,
        _water_z_pin,
    ) = _run_one_model(scenario, n_water=1.333, seed=1)
    assert discard_stats["degenerate_observations_at_solution"] >= 0


# ---------------------------------------------------------------------------
# FIX-01 (D-01/D-03/D-04): resolve_water_z_pin / build_water_z_provenance.
# ---------------------------------------------------------------------------


def test_resolve_water_z_pin_none_for_refractive_index():
    """The refractive arm (n_water != 1.0) must never be pinned."""
    scenario = create_scenario("realistic", seed=42)
    assert resolve_water_z_pin(scenario, 1.333) is None


def test_resolve_water_z_pin_reads_scenario_ground_truth():
    """The non-refractive arm's pin is the scenario's own shared water_z,
    never a hardcoded literal -- 1.031 m for the 'realistic' scenario."""
    scenario = create_scenario("realistic", seed=42)
    pin = resolve_water_z_pin(scenario, 1.0)
    assert pin == pytest.approx(1.031)
    assert pin == pytest.approx(next(iter(scenario.water_zs.values())))


def test_resolve_water_z_pin_raises_on_non_shared_water_z():
    """A hand-built scenario stub whose cameras disagree on water_z cannot be
    pinned to a single shared value -- resolve_water_z_pin must raise rather
    than silently picking one."""
    from types import SimpleNamespace

    stub = SimpleNamespace(name="stub", water_zs={"cam0": 1.031, "cam1": 1.040})
    with pytest.raises(ValueError, match="resolve_water_z_pin"):
        resolve_water_z_pin(stub, 1.0)


def test_build_water_z_provenance_pinned():
    prov = build_water_z_provenance(1.031)
    assert prov["water_z_pinned_m"] == 1.031
    assert prov["water_z_pin_mechanism"]
    assert prov["water_z_pin_reason"]


def test_build_water_z_provenance_unpinned():
    prov = build_water_z_provenance(None)
    assert prov["water_z_pinned_m"] is None
    assert prov["water_z_pin_reason"]
    assert set(prov.keys()) == {
        "water_z_pinned_m",
        "water_z_pin_mechanism",
        "water_z_pin_reason",
    }


def test_water_z_bounds_threads_through_both_stage3_call_sites():
    """Source-level assertion, not a solve: both stage-3 call sites
    (`interface_estimation.optimize_interface` and `refinement.joint_refinement`)
    must forward `water_z_bounds=water_z_bounds` to `build_bounds`, and
    `calibrate_synthetic` must forward it to BOTH of them. This is a
    source-level check specifically because a first-pass-only fix is a
    measured, silent failure mode (Trap 1): a pin held through Stage 3's
    first pass drifted from 1.031 m to 0.0425 m by the end of the
    intrinsic-refinement pass when the override was not also threaded
    there. A behavioral test that only checks the first pass would pass a
    broken fix, so this asserts the forwarding exists at the source level
    in all three functions instead.
    """
    import inspect

    from aquacal.calibration.interface_estimation import optimize_interface
    from aquacal.calibration.refinement import joint_refinement
    from aquacal.datasets.pipelines import calibrate_synthetic

    assert "water_z_bounds=water_z_bounds" in inspect.getsource(optimize_interface)
    assert "water_z_bounds=water_z_bounds" in inspect.getsource(joint_refinement)
    # Two forwards -- to optimize_interface and to joint_refinement. The
    # parameter's own signature line reads `water_z_bounds: ... = None,`
    # (a type-annotated default), which does not itself contain the
    # substring `water_z_bounds=`.
    assert (
        inspect.getsource(calibrate_synthetic).count("water_z_bounds=water_z_bounds")
        == 2
    )
