"""Unit tests for joint refinement (Stage 3's second pass, with intrinsics unlocked)."""

import sys

import numpy as np
import pytest

from aquacal.calibration._observability import OptimizerObserver, SolverDiagnostics
from aquacal.calibration._optim_common import pack_params, unpack_params
from aquacal.calibration.refinement import joint_refinement
from aquacal.config.schema import (
    BoardConfig,
    BoardPose,
    CameraExtrinsics,
    CameraIntrinsics,
    ConvergenceError,
    DetectionResult,
)
from aquacal.core.board import BoardGeometry

sys.path.insert(0, ".")
from tests.synthetic.ground_truth import generate_synthetic_detections


@pytest.fixture
def board_config() -> BoardConfig:
    """Board configuration for testing."""
    return BoardConfig(
        squares_x=6,
        squares_y=5,
        square_size=0.04,
        marker_size=0.03,
        dictionary="DICT_4X4_50",
    )


@pytest.fixture
def board(board_config) -> BoardGeometry:
    """BoardGeometry instance."""
    return BoardGeometry(board_config)


@pytest.fixture
def intrinsics() -> dict[str, CameraIntrinsics]:
    """Ground truth intrinsics for 3 cameras."""
    K = np.array([[500, 0, 320], [0, 500, 240], [0, 0, 1]], dtype=np.float64)
    dist = np.zeros(5, dtype=np.float64)
    return {
        "cam0": CameraIntrinsics(
            K=K.copy(), dist_coeffs=dist.copy(), image_size=(640, 480)
        ),
        "cam1": CameraIntrinsics(
            K=K.copy(), dist_coeffs=dist.copy(), image_size=(640, 480)
        ),
        "cam2": CameraIntrinsics(
            K=K.copy(), dist_coeffs=dist.copy(), image_size=(640, 480)
        ),
    }


@pytest.fixture
def ground_truth_extrinsics() -> dict[str, CameraExtrinsics]:
    """Ground truth camera extrinsics."""
    return {
        "cam0": CameraExtrinsics(
            R=np.eye(3, dtype=np.float64),
            t=np.zeros(3, dtype=np.float64),
        ),
        "cam1": CameraExtrinsics(
            R=np.eye(3, dtype=np.float64),
            t=np.array([0.1, 0.0, 0.0], dtype=np.float64),
        ),
        "cam2": CameraExtrinsics(
            R=np.eye(3, dtype=np.float64),
            t=np.array([0.0, 0.1, 0.0], dtype=np.float64),
        ),
    }


@pytest.fixture
def ground_truth_distances() -> dict[str, float]:
    """Ground truth interface distances.

    With a single water_z parameter, distances are derived as d_i = water_z - C_z_i.
    cam0: C_z = 0 (identity R, t=0) -> d = water_z
    cam1: C_z = 0 (identity R, t=[0.3,0,0]) -> d = water_z
    cam2: C_z = 0 (identity R, t=[0,0.3,0]) -> d = water_z
    All cameras share C_z=0, so all distances must equal water_z = 0.15.
    """
    return {"cam0": 0.15, "cam1": 0.15, "cam2": 0.15}


@pytest.fixture
def synthetic_board_poses() -> list[BoardPose]:
    """Board poses for 10 frames underwater."""
    poses = []
    for i in range(10):
        x_offset = 0.05 * (i % 4 - 1.5)
        y_offset = 0.05 * (i // 4 - 1)
        poses.append(
            BoardPose(
                frame_idx=i,
                rvec=np.array([0.1 * (i % 3), 0.1 * (i % 2), 0.0], dtype=np.float64),
                tvec=np.array([x_offset, y_offset, 0.4], dtype=np.float64),
            )
        )
    return poses


@pytest.fixture
def stage3_result(
    ground_truth_extrinsics, ground_truth_distances, synthetic_board_poses
):
    """Simulated Stage 3 output."""
    return (
        ground_truth_extrinsics,
        ground_truth_distances,
        synthetic_board_poses,
        0.5,  # RMS error
    )


class TestPackUnpackWithIntrinsics:
    """Test parameter packing and unpacking with intrinsics."""

    def test_round_trip_without_intrinsics(
        self,
        ground_truth_extrinsics,
        ground_truth_distances,
        synthetic_board_poses,
        intrinsics,
    ):
        """Pack/unpack round-trip without refining intrinsics."""
        camera_order = ["cam0", "cam1", "cam2"]
        frame_order = [0, 1, 2]
        board_poses_dict = {bp.frame_idx: bp for bp in synthetic_board_poses[:3]}
        water_z = 0.15  # All cameras at C_z=0, so water_z = distance

        packed = pack_params(
            ground_truth_extrinsics,
            water_z,
            board_poses_dict,
            "cam0",
            camera_order,
            frame_order,
            intrinsics=intrinsics,
            refine_intrinsics=False,
        )

        ext_out, dist_out, poses_out, intr_out = unpack_params(
            packed,
            "cam0",
            ground_truth_extrinsics["cam0"],
            camera_order,
            frame_order,
            base_intrinsics=intrinsics,
            refine_intrinsics=False,
        )

        # Verify extrinsics
        for cam in camera_order:
            np.testing.assert_allclose(ext_out[cam].R, ground_truth_extrinsics[cam].R)
            np.testing.assert_allclose(ext_out[cam].t, ground_truth_extrinsics[cam].t)
            assert abs(dist_out[cam] - ground_truth_distances[cam]) < 1e-10
            np.testing.assert_allclose(intr_out[cam].K, intrinsics[cam].K)

        # Verify board poses
        for frame_idx in frame_order:
            np.testing.assert_allclose(
                poses_out[frame_idx].rvec, board_poses_dict[frame_idx].rvec
            )
            np.testing.assert_allclose(
                poses_out[frame_idx].tvec, board_poses_dict[frame_idx].tvec
            )

    def test_round_trip_with_intrinsics(
        self,
        ground_truth_extrinsics,
        ground_truth_distances,
        synthetic_board_poses,
        intrinsics,
    ):
        """Pack/unpack round-trip with intrinsics."""
        camera_order = ["cam0", "cam1", "cam2"]
        frame_order = [0, 1, 2]
        board_poses_dict = {bp.frame_idx: bp for bp in synthetic_board_poses[:3]}
        water_z = 0.15

        packed = pack_params(
            ground_truth_extrinsics,
            water_z,
            board_poses_dict,
            "cam0",
            camera_order,
            frame_order,
            intrinsics=intrinsics,
            refine_intrinsics=True,
        )

        ext_out, dist_out, poses_out, intr_out = unpack_params(
            packed,
            "cam0",
            ground_truth_extrinsics["cam0"],
            camera_order,
            frame_order,
            base_intrinsics=intrinsics,
            refine_intrinsics=True,
        )

        # Verify intrinsics are recovered
        for cam in camera_order:
            np.testing.assert_allclose(intr_out[cam].K, intrinsics[cam].K)
            # Distortion coeffs should be preserved
            np.testing.assert_allclose(
                intr_out[cam].dist_coeffs, intrinsics[cam].dist_coeffs
            )

    def test_parameter_count_without_intrinsics(
        self,
        ground_truth_extrinsics,
        ground_truth_distances,
        synthetic_board_poses,
        intrinsics,
    ):
        """Verify parameter count without intrinsics refinement."""
        camera_order = ["cam0", "cam1", "cam2"]
        frame_order = [0, 1, 2]
        board_poses_dict = {bp.frame_idx: bp for bp in synthetic_board_poses[:3]}
        water_z = 0.15

        packed = pack_params(
            ground_truth_extrinsics,
            water_z,
            board_poses_dict,
            "cam0",
            camera_order,
            frame_order,
            refine_intrinsics=False,
        )

        # Expected: 6*(3-1) + 1 + 6*3 = 12 + 1 + 18 = 31
        expected_count = 6 * (len(camera_order) - 1) + 1 + 6 * len(frame_order)
        assert len(packed) == expected_count

    def test_parameter_count_with_intrinsics(
        self,
        ground_truth_extrinsics,
        ground_truth_distances,
        synthetic_board_poses,
        intrinsics,
    ):
        """Verify parameter count with intrinsics refinement."""
        camera_order = ["cam0", "cam1", "cam2"]
        frame_order = [0, 1, 2]
        board_poses_dict = {bp.frame_idx: bp for bp in synthetic_board_poses[:3]}
        water_z = 0.15

        packed = pack_params(
            ground_truth_extrinsics,
            water_z,
            board_poses_dict,
            "cam0",
            camera_order,
            frame_order,
            intrinsics=intrinsics,
            refine_intrinsics=True,
        )

        # Expected: 6*(3-1) + 1 + 6*3 + 4*3 = 12 + 1 + 18 + 12 = 43
        expected_count = (
            6 * (len(camera_order) - 1)
            + 1
            + 6 * len(frame_order)
            + 4 * len(camera_order)
        )
        assert len(packed) == expected_count


class TestJointRefinement:
    """Test joint refinement function."""

    def test_without_intrinsics_maintains_quality(
        self,
        board,
        intrinsics,
        ground_truth_extrinsics,
        ground_truth_distances,
        synthetic_board_poses,
        stage3_result,
    ):
        """Refinement without intrinsics maintains or improves RMS."""
        detections = generate_synthetic_detections(
            intrinsics,
            ground_truth_extrinsics,
            ground_truth_distances,
            board,
            synthetic_board_poses,
            noise_std=0.5,
            min_corners=4,
        )

        ext_opt, dist_opt, poses_opt, intr_opt, rms = joint_refinement(
            stage3_result=stage3_result,
            detections=detections,
            intrinsics=intrinsics,
            board=board,
            reference_camera="cam0",
            refine_intrinsics=False,
        )

        assert rms < 2.0
        # Intrinsics should be unchanged
        for cam in intrinsics:
            np.testing.assert_allclose(intr_opt[cam].K, intrinsics[cam].K)

    def test_with_intrinsics_can_refine(
        self,
        board,
        intrinsics,
        ground_truth_extrinsics,
        ground_truth_distances,
        synthetic_board_poses,
    ):
        """Refinement with intrinsics allows intrinsic parameters to change."""
        # Create detections with ground truth intrinsics
        detections = generate_synthetic_detections(
            intrinsics,
            ground_truth_extrinsics,
            ground_truth_distances,
            board,
            synthetic_board_poses,
            noise_std=0.3,
        )

        stage3_result = (
            ground_truth_extrinsics,
            ground_truth_distances,
            synthetic_board_poses,
            1.0,
        )

        # Run with intrinsics refinement enabled
        ext_opt, dist_opt, poses_opt, intr_opt, rms = joint_refinement(
            stage3_result=stage3_result,
            detections=detections,
            intrinsics=intrinsics,
            board=board,
            reference_camera="cam0",
            refine_intrinsics=True,
        )

        # Optimization should complete successfully
        assert rms < 2.0

        # Intrinsics should be returned (may be slightly different from input)
        for cam in intrinsics:
            assert intr_opt[cam] is not None
            # Verify intrinsics are within reasonable bounds
            assert (
                0.5 * intrinsics[cam].K[0, 0]
                <= intr_opt[cam].K[0, 0]
                <= 2.0 * intrinsics[cam].K[0, 0]
            )
            assert (
                0.5 * intrinsics[cam].K[1, 1]
                <= intr_opt[cam].K[1, 1]
                <= 2.0 * intrinsics[cam].K[1, 1]
            )

    def test_reference_camera_unchanged(
        self,
        board,
        intrinsics,
        ground_truth_extrinsics,
        ground_truth_distances,
        synthetic_board_poses,
        stage3_result,
    ):
        """Reference camera extrinsics remain fixed."""
        detections = generate_synthetic_detections(
            intrinsics,
            ground_truth_extrinsics,
            ground_truth_distances,
            board,
            synthetic_board_poses,
            noise_std=0.5,
            min_corners=4,
        )

        ext_opt, _, _, _, _ = joint_refinement(
            stage3_result=stage3_result,
            detections=detections,
            intrinsics=intrinsics,
            board=board,
            reference_camera="cam0",
        )

        np.testing.assert_allclose(
            ext_opt["cam0"].R, ground_truth_extrinsics["cam0"].R, atol=1e-10
        )
        np.testing.assert_allclose(
            ext_opt["cam0"].t, ground_truth_extrinsics["cam0"].t, atol=1e-10
        )

    def test_raises_for_invalid_reference(self, board, intrinsics, stage3_result):
        """Raises ValueError for invalid reference camera."""
        detections = DetectionResult(frames={}, camera_names=["cam0"], total_frames=0)

        with pytest.raises(ValueError, match="reference"):
            joint_refinement(
                stage3_result=stage3_result,
                detections=detections,
                intrinsics=intrinsics,
                board=board,
                reference_camera="camX",
            )

    def test_distances_positive(
        self,
        board,
        intrinsics,
        ground_truth_extrinsics,
        ground_truth_distances,
        synthetic_board_poses,
        stage3_result,
    ):
        """Interface distances are positive (cameras above water surface)."""
        np.random.seed(42)

        detections = generate_synthetic_detections(
            intrinsics,
            ground_truth_extrinsics,
            ground_truth_distances,
            board,
            synthetic_board_poses,
            noise_std=0.5,
            min_corners=4,
        )

        _, dist_opt, _, _, _ = joint_refinement(
            stage3_result=stage3_result,
            detections=detections,
            intrinsics=intrinsics,
            board=board,
            reference_camera="cam0",
        )

        for cam, dist in dist_opt.items():
            assert dist > 0, f"Negative distance for {cam}: {dist}"

    def test_intrinsic_bounds_enforced(
        self,
        board,
        intrinsics,
        ground_truth_extrinsics,
        ground_truth_distances,
        synthetic_board_poses,
        stage3_result,
    ):
        """Intrinsic parameters stay within bounds."""
        detections = generate_synthetic_detections(
            intrinsics,
            ground_truth_extrinsics,
            ground_truth_distances,
            board,
            synthetic_board_poses,
            noise_std=0.5,
            min_corners=4,
        )

        _, _, _, intr_opt, _ = joint_refinement(
            stage3_result=stage3_result,
            detections=detections,
            intrinsics=intrinsics,
            board=board,
            reference_camera="cam0",
            refine_intrinsics=True,
        )

        for cam in intrinsics:
            base = intrinsics[cam]
            opt = intr_opt[cam]

            # Focal lengths within [0.5x, 2x]
            assert 0.5 * base.K[0, 0] <= opt.K[0, 0] <= 2.0 * base.K[0, 0]
            assert 0.5 * base.K[1, 1] <= opt.K[1, 1] <= 2.0 * base.K[1, 1]

            # Principal point within image
            w, h = base.image_size
            assert 0 <= opt.K[0, 2] <= w
            assert 0 <= opt.K[1, 2] <= h

    def test_distortion_coeffs_unchanged(
        self,
        board,
        intrinsics,
        ground_truth_extrinsics,
        ground_truth_distances,
        synthetic_board_poses,
        stage3_result,
    ):
        """Distortion coefficients remain unchanged even when refining intrinsics."""
        detections = generate_synthetic_detections(
            intrinsics,
            ground_truth_extrinsics,
            ground_truth_distances,
            board,
            synthetic_board_poses,
            noise_std=0.5,
            min_corners=4,
        )

        _, _, _, intr_opt, _ = joint_refinement(
            stage3_result=stage3_result,
            detections=detections,
            intrinsics=intrinsics,
            board=board,
            reference_camera="cam0",
            refine_intrinsics=True,
        )

        for cam in intrinsics:
            np.testing.assert_allclose(
                intr_opt[cam].dist_coeffs, intrinsics[cam].dist_coeffs
            )

    def test_returns_correct_number_of_poses(
        self,
        board,
        intrinsics,
        ground_truth_extrinsics,
        ground_truth_distances,
        synthetic_board_poses,
        stage3_result,
    ):
        """Returns the correct number of board poses."""
        detections = generate_synthetic_detections(
            intrinsics,
            ground_truth_extrinsics,
            ground_truth_distances,
            board,
            synthetic_board_poses,
            noise_std=0.5,
            min_corners=4,
        )

        _, _, poses_opt, _, _ = joint_refinement(
            stage3_result=stage3_result,
            detections=detections,
            intrinsics=intrinsics,
            board=board,
            reference_camera="cam0",
        )

        assert len(poses_opt) == len(synthetic_board_poses)

    def test_empty_board_poses_raises_error(
        self, board, intrinsics, ground_truth_extrinsics, ground_truth_distances
    ):
        """Raises ConvergenceError when no board poses in Stage 3 result."""
        # Empty stage3 result
        stage3_result = (ground_truth_extrinsics, ground_truth_distances, [], 0.0)

        detections = DetectionResult(
            frames={}, camera_names=["cam0", "cam1", "cam2"], total_frames=0
        )

        with pytest.raises(ConvergenceError, match="No board poses"):
            joint_refinement(
                stage3_result=stage3_result,
                detections=detections,
                intrinsics=intrinsics,
                board=board,
                reference_camera="cam0",
            )


class TestJointRefinementObserver:
    """Tests for the optional OptimizerObserver wiring in joint_refinement."""

    def test_joint_refinement_observer_does_not_change_result(
        self,
        board,
        intrinsics,
        ground_truth_extrinsics,
        ground_truth_distances,
        synthetic_board_poses,
        stage3_result,
    ):
        """Passing an observer must not change any returned value."""
        detections = generate_synthetic_detections(
            intrinsics,
            ground_truth_extrinsics,
            ground_truth_distances,
            board,
            synthetic_board_poses,
            noise_std=0.5,
            min_corners=4,
        )

        ext_no_obs, dist_no_obs, poses_no_obs, intr_no_obs, rms_no_obs = (
            joint_refinement(
                stage3_result=stage3_result,
                detections=detections,
                intrinsics=intrinsics,
                board=board,
                reference_camera="cam0",
                verbose=0,
            )
        )

        observer = OptimizerObserver(stage="stage3_intrinsic_pass")
        ext_obs, dist_obs, poses_obs, intr_obs, rms_obs = joint_refinement(
            stage3_result=stage3_result,
            detections=detections,
            intrinsics=intrinsics,
            board=board,
            reference_camera="cam0",
            verbose=0,
            observer=observer,
        )

        for cam in intrinsics:
            np.testing.assert_array_equal(ext_obs[cam].R, ext_no_obs[cam].R)
            np.testing.assert_array_equal(ext_obs[cam].t, ext_no_obs[cam].t)
            assert dist_obs[cam] == dist_no_obs[cam]
            np.testing.assert_array_equal(intr_obs[cam].K, intr_no_obs[cam].K)

        assert rms_obs == rms_no_obs
        for bp_obs, bp_no_obs in zip(poses_obs, poses_no_obs):
            np.testing.assert_array_equal(bp_obs.rvec, bp_no_obs.rvec)
            np.testing.assert_array_equal(bp_obs.tvec, bp_no_obs.tvec)

    def test_joint_refinement_observer_traces_water_z(
        self,
        board,
        intrinsics,
        ground_truth_extrinsics,
        ground_truth_distances,
        synthetic_board_poses,
        stage3_result,
    ):
        """The observer's final trace row water_z matches the returned solution."""
        detections = generate_synthetic_detections(
            intrinsics,
            ground_truth_extrinsics,
            ground_truth_distances,
            board,
            synthetic_board_poses,
            noise_std=0.5,
            min_corners=4,
        )

        observer = OptimizerObserver(stage="stage3_intrinsic_pass")
        _, dist_opt, _, _, _ = joint_refinement(
            stage3_result=stage3_result,
            detections=detections,
            intrinsics=intrinsics,
            board=board,
            reference_camera="cam0",
            verbose=0,
            observer=observer,
        )

        assert len(observer.rows) > 0
        # Reference camera has C_z=0, so its distance equals water_z exactly.
        assert observer.rows[-1].water_z == dist_opt["cam0"]


class TestJointRefinementDiagnostics:
    """Tests for diagnostics_out wiring and explicit ftol/xtol/gtol on joint_refinement."""

    @pytest.mark.parametrize("use_sparse_jacobian", [True, False])
    def test_joint_refinement_diagnostics_out_populated_and_bit_exact(
        self,
        board,
        intrinsics,
        ground_truth_extrinsics,
        ground_truth_distances,
        synthetic_board_poses,
        stage3_result,
        use_sparse_jacobian,
    ):
        """diagnostics_out is populated correctly and never changes the result."""
        detections = generate_synthetic_detections(
            intrinsics,
            ground_truth_extrinsics,
            ground_truth_distances,
            board,
            synthetic_board_poses,
            noise_std=0.5,
            min_corners=4,
        )

        ext_no_diag, dist_no_diag, poses_no_diag, intr_no_diag, rms_no_diag = (
            joint_refinement(
                stage3_result=stage3_result,
                detections=detections,
                intrinsics=intrinsics,
                board=board,
                reference_camera="cam0",
                verbose=0,
                use_sparse_jacobian=use_sparse_jacobian,
            )
        )

        diag = SolverDiagnostics()
        ext_diag, dist_diag, poses_diag, intr_diag, rms_diag = joint_refinement(
            stage3_result=stage3_result,
            detections=detections,
            intrinsics=intrinsics,
            board=board,
            reference_camera="cam0",
            verbose=0,
            use_sparse_jacobian=use_sparse_jacobian,
            diagnostics_out=diag,
        )

        # Bit-exact regression: diagnostics_out + explicit tolerances must not
        # change any returned value.
        for cam in intrinsics:
            np.testing.assert_array_equal(ext_diag[cam].R, ext_no_diag[cam].R)
            np.testing.assert_array_equal(ext_diag[cam].t, ext_no_diag[cam].t)
            assert dist_diag[cam] == dist_no_diag[cam]
            np.testing.assert_array_equal(intr_diag[cam].K, intr_no_diag[cam].K)
        assert rms_diag == rms_no_diag
        for bp_diag, bp_no_diag in zip(poses_diag, poses_no_diag):
            np.testing.assert_array_equal(bp_diag.rvec, bp_no_diag.rvec)
            np.testing.assert_array_equal(bp_diag.tvec, bp_no_diag.tvec)

        # Diagnostics population.
        assert diag.nfev is not None and isinstance(diag.nfev, int)
        assert diag.njev is not None and isinstance(diag.njev, int)
        assert diag.cost is not None
        assert diag.optimality is not None
        assert diag.status is not None
        assert diag.message is not None
        assert diag.ftol == 1e-8
        assert diag.xtol == 1e-8
        assert diag.gtol == 1e-8
        assert diag.max_nfev_source == "scipy_auto"

        if use_sparse_jacobian:
            assert diag.n_params is not None
            assert diag.n_groups is not None
            assert diag.n_params_reason is None
            assert diag.n_groups_reason is None
        else:
            assert diag.n_params is None
            assert diag.n_groups is None
            assert diag.n_params_reason is not None
            assert diag.n_groups_reason is not None

    def test_joint_refinement_diagnostics_out_none_is_safe(
        self,
        board,
        intrinsics,
        ground_truth_extrinsics,
        ground_truth_distances,
        synthetic_board_poses,
        stage3_result,
    ):
        """diagnostics_out=None (the default) must not raise or change behavior."""
        detections = generate_synthetic_detections(
            intrinsics,
            ground_truth_extrinsics,
            ground_truth_distances,
            board,
            synthetic_board_poses,
            noise_std=0.5,
            min_corners=4,
        )

        ext, dist, poses, intr, rms = joint_refinement(
            stage3_result=stage3_result,
            detections=detections,
            intrinsics=intrinsics,
            board=board,
            reference_camera="cam0",
            verbose=0,
            diagnostics_out=None,
        )
        assert rms >= 0.0
