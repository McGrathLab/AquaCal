"""Tests for standalone held-out evaluation (aquacal.evaluate_calibration)."""

import subprocess
import sys

import numpy as np
import pytest

from aquacal.calibration.interface_estimation import _compute_initial_board_poses
from aquacal.calibration.pipeline import _filter_cameras
from aquacal.config.schema import (
    CalibrationMetadata,
    CalibrationResult,
    CameraCalibration,
    DiagnosticsData,
    InterfaceParams,
)
from aquacal.core.board import BoardGeometry
from aquacal.datasets import create_scenario, generate_synthetic_detections
from aquacal.validation.evaluation import (
    HeldOutEvaluation,
    _estimate_validation_poses,
    evaluate_calibration,
)
from aquacal.validation.reconstruction import compute_3d_distance_errors
from aquacal.validation.reprojection import compute_reprojection_errors


def _build_result(scenario) -> CalibrationResult:
    """Build a CalibrationResult from a SyntheticScenario's ground truth."""
    cameras = {}
    for cam_name in scenario.intrinsics:
        cameras[cam_name] = CameraCalibration(
            name=cam_name,
            intrinsics=scenario.intrinsics[cam_name],
            extrinsics=scenario.extrinsics[cam_name],
            water_z=scenario.water_zs[cam_name],
        )

    return CalibrationResult(
        cameras=cameras,
        interface=InterfaceParams(
            normal=np.array([0.0, 0.0, -1.0], dtype=np.float64),
            n_air=scenario.n_air,
            n_water=scenario.n_water,
        ),
        board=scenario.board_config,
        diagnostics=DiagnosticsData(
            reprojection_error_rms=0.0,
            reprojection_error_per_camera={},
            validation_3d_error_mean=0.0,
            validation_3d_error_std=0.0,
        ),
        metadata=CalibrationMetadata(
            calibration_date="2026-07-23",
            software_version="test",
            config_hash="test",
            num_frames_used=len(scenario.board_poses),
            num_frames_holdout=0,
        ),
    )


@pytest.fixture
def scenario():
    return create_scenario("minimal")


@pytest.fixture
def board(scenario):
    return BoardGeometry(scenario.board_config)


@pytest.fixture
def full_result(scenario):
    return _build_result(scenario)


@pytest.fixture
def matched_detections(scenario, board):
    """Held-out detections generated at the scenario's own (matched) n_water."""
    return generate_synthetic_detections(
        scenario.intrinsics,
        scenario.extrinsics,
        scenario.water_zs,
        board,
        scenario.board_poses,
        noise_std=0.0,
        min_corners=4,
        n_air=scenario.n_air,
        n_water=scenario.n_water,
        seed=scenario.seed,
    )


class TestEvaluateCalibration:
    """Standalone behaviour of evaluate_calibration()."""

    def test_evaluate_returns_expected_shape(
        self, full_result, matched_detections, board
    ):
        evaluation = evaluate_calibration(
            full_result, matched_detections, board, min_corners=4
        )

        assert isinstance(evaluation, HeldOutEvaluation)
        assert np.isfinite(evaluation.reprojection.rms)
        assert evaluation.reconstruction is not None
        assert evaluation.num_frames == len(matched_detections.frames)
        assert len(evaluation.board_poses) == len(matched_detections.frames)

    def test_evaluate_on_ground_truth_is_near_zero(
        self, full_result, matched_detections, board
    ):
        evaluation = evaluate_calibration(
            full_result, matched_detections, board, min_corners=4
        )

        assert evaluation.reprojection.rms < 0.1

    def test_evaluate_detects_perturbed_refractive_index(
        self, scenario, full_result, board
    ):
        # Matched-index held-out set: scored against calibration's own n_water.
        matched = generate_synthetic_detections(
            scenario.intrinsics,
            scenario.extrinsics,
            scenario.water_zs,
            board,
            scenario.board_poses,
            noise_std=0.0,
            min_corners=4,
            n_air=scenario.n_air,
            n_water=scenario.n_water,
            seed=scenario.seed,
        )
        # Perturbed-index held-out set: generated at a different n_water. This is
        # the WP4 "evaluate under perturbed assumptions" use case.
        perturbed = generate_synthetic_detections(
            scenario.intrinsics,
            scenario.extrinsics,
            scenario.water_zs,
            board,
            scenario.board_poses,
            noise_std=0.0,
            min_corners=4,
            n_air=scenario.n_air,
            n_water=1.45,
            seed=scenario.seed,
        )

        matched_eval = evaluate_calibration(full_result, matched, board, min_corners=4)
        perturbed_eval = evaluate_calibration(
            full_result, perturbed, board, min_corners=4
        )

        assert perturbed_eval.reprojection.rms > matched_eval.reprojection.rms * 2

    def test_cameras_filter_changes_metrics_not_poses(
        self, full_result, matched_detections, board
    ):
        first_cam = sorted(full_result.cameras)[0]

        eval_all = evaluate_calibration(
            full_result, matched_detections, board, min_corners=4, cameras=None
        )
        eval_one = evaluate_calibration(
            full_result,
            matched_detections,
            board,
            min_corners=4,
            cameras={first_cam},
        )

        # Poses are estimated using the full calibration regardless of `cameras`.
        assert set(eval_all.board_poses) == set(eval_one.board_poses)
        for idx in eval_all.board_poses:
            np.testing.assert_array_equal(
                eval_all.board_poses[idx].rvec, eval_one.board_poses[idx].rvec
            )
            np.testing.assert_array_equal(
                eval_all.board_poses[idx].tvec, eval_one.board_poses[idx].tvec
            )

        # But the metrics are computed over different camera subsets.
        assert set(eval_one.reprojection.per_camera) <= {first_cam}
        assert set(eval_all.reprojection.per_camera) != set(
            eval_one.reprojection.per_camera
        )

    def test_supplied_board_poses_skip_estimation(
        self, full_result, matched_detections, board
    ):
        first = evaluate_calibration(
            full_result, matched_detections, board, min_corners=4
        )
        second = evaluate_calibration(
            full_result,
            matched_detections,
            board,
            min_corners=4,
            board_poses=first.board_poses,
        )

        assert set(second.board_poses) == set(first.board_poses)
        for idx in first.board_poses:
            np.testing.assert_array_equal(
                second.board_poses[idx].rvec, first.board_poses[idx].rvec
            )
            np.testing.assert_array_equal(
                second.board_poses[idx].tvec, first.board_poses[idx].tvec
            )
        assert second.reprojection.rms == first.reprojection.rms

    def test_include_reconstruction_false(self, full_result, matched_detections, board):
        evaluation = evaluate_calibration(
            full_result,
            matched_detections,
            board,
            min_corners=4,
            include_reconstruction=False,
        )

        assert evaluation.reconstruction is None

    def test_no_import_cycle(self):
        for code in (
            "import aquacal.validation; import aquacal",
            "import aquacal; import aquacal.validation",
        ):
            proc = subprocess.run(
                [sys.executable, "-c", code], capture_output=True, text=True
            )
            assert proc.returncode == 0, proc.stderr

    def test_top_level_export(self):
        import aquacal
        from aquacal import evaluate_calibration as top_level_evaluate_calibration

        assert top_level_evaluate_calibration is not None
        assert "evaluate_calibration" in aquacal.__all__


# --- Legacy-equivalence regression test ---
#
# This is the CONTEXT.md-mandated regression guard for the phase's one deliberate
# refactor of numerically-sensitive code: moving the pipeline's inline held-out
# evaluation block behind `evaluate_calibration`. It replicates
# `run_calibration_from_config`'s inline sequence literally (as of phase 16, prior
# to the task-3 refactor) and asserts `evaluate_calibration` reproduces it exactly.
# Update this test only if the pipeline's held-out semantics are intentionally
# changed — do not loosen the equality checks to make a real divergence pass.


def test_matches_legacy_inline_sequence(scenario, full_result, board):
    """evaluate_calibration must reproduce pipeline.py's inline held-out block bit for bit."""
    dets = generate_synthetic_detections(
        scenario.intrinsics,
        scenario.extrinsics,
        scenario.water_zs,
        board,
        scenario.board_poses,
        noise_std=0.3,
        min_corners=4,
        n_air=scenario.n_air,
        n_water=scenario.n_water,
        seed=scenario.seed,
    )

    intrinsics = {name: cam.intrinsics for name, cam in full_result.cameras.items()}
    extrinsics = {name: cam.extrinsics for name, cam in full_result.cameras.items()}
    water_zs = {name: cam.water_z for name, cam in full_result.cameras.items()}
    interface_normal = full_result.interface.normal
    n_air = full_result.interface.n_air
    n_water = full_result.interface.n_water

    primary_names = set(full_result.cameras.keys())

    # --- Legacy sequence, copied verbatim from the pre-refactor pipeline ---
    legacy_initial = _compute_initial_board_poses(
        dets,
        intrinsics,
        extrinsics,
        board,
        min_corners=4,
        n_water=n_water,
    )
    legacy_poses = _estimate_validation_poses(
        dets,
        legacy_initial,
        intrinsics,
        extrinsics,
        water_zs,
        board,
        interface_normal,
        n_air,
        n_water,
    )
    legacy_target = _filter_cameras(full_result, primary_names)
    legacy_reproj = compute_reprojection_errors(legacy_target, dets, legacy_poses)
    legacy_3d = compute_3d_distance_errors(
        legacy_target, dets, board, include_spatial=True
    )

    # --- New path ---
    ev = evaluate_calibration(
        full_result, dets, board, min_corners=4, cameras=primary_names
    )

    assert ev.reprojection.rms == legacy_reproj.rms  # exact, not approx
    assert ev.reconstruction.mean == legacy_3d.mean
    assert ev.reconstruction.std == legacy_3d.std
    assert ev.reconstruction.rmse == legacy_3d.rmse
    assert set(ev.board_poses) == set(legacy_poses)
    for idx in legacy_poses:
        np.testing.assert_array_equal(ev.board_poses[idx].rvec, legacy_poses[idx].rvec)
        np.testing.assert_array_equal(ev.board_poses[idx].tvec, legacy_poses[idx].tvec)
    np.testing.assert_array_equal(
        sorted(ev.reprojection.per_camera), sorted(legacy_reproj.per_camera)
    )
