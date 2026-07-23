"""Tests for optimization common utilities (_optim_common.py)."""

import numpy as np
import pytest
import scipy.sparse
from scipy.optimize._numdiff import approx_derivative, group_columns

from aquacal.calibration._optim_common import (
    build_bounds,
    build_jacobian_sparsity,
    build_structural_column_groups,
    make_sparse_jacobian_func,
    pack_params,
    unpack_params,
)
from aquacal.config.schema import (
    BoardPose,
    CameraExtrinsics,
    Detection,
    DetectionResult,
    FrameDetections,
)


def _toy_cost(params, A):
    """Simple quadratic cost: residuals = A @ params.

    For this linear function f(x) = A @ x, the Jacobian is exactly A.
    """
    return A @ params


def _make_detections(n_cams, n_frames, visibility, corners_per_view=4, seed=0):
    """Build a DetectionResult where each camera sees each frame with prob `visibility`.

    At least one camera is guaranteed per frame so no frame is empty.

    Args:
        n_cams: Number of cameras, named ``cam0``..``cam{n_cams-1}``.
        n_frames: Number of frames, indexed ``0``..``n_frames-1``.
        visibility: Probability that a given camera sees a given frame.
        corners_per_view: Corners detected in each (camera, frame) view.
        seed: Seed for the visibility draws and corner coordinates.

    Returns:
        DetectionResult with the requested partial visibility pattern.
    """
    rng = np.random.default_rng(seed)
    camera_names = [f"cam{i}" for i in range(n_cams)]
    corner_ids = np.arange(corners_per_view, dtype=np.int32)

    frames = {}
    for frame_idx in range(n_frames):
        visible = [c for c in camera_names if rng.random() < visibility]
        if not visible:
            # Guarantee a non-empty frame.
            visible = [camera_names[rng.integers(n_cams)]]

        detections = {
            cam: Detection(
                corner_ids=corner_ids.copy(),
                corners_2d=rng.uniform(0.0, 1000.0, size=(corners_per_view, 2)),
            )
            for cam in visible
        }
        frames[frame_idx] = FrameDetections(frame_idx=frame_idx, detections=detections)

    return DetectionResult(
        frames=frames,
        camera_names=camera_names,
        total_frames=n_frames,
    )


def _make_pattern(
    n_cams, n_frames, visibility, refine_intrinsics, normal_fixed, seed=0
):
    """Build a board-observation sparsity pattern for the given configuration."""
    detections = _make_detections(n_cams, n_frames, visibility, seed=seed)
    return build_jacobian_sparsity(
        detections,
        reference_camera="cam0",
        camera_order=[f"cam{i}" for i in range(n_cams)],
        frame_order=list(range(n_frames)),
        min_corners=1,
        refine_intrinsics=refine_intrinsics,
        normal_fixed=normal_fixed,
    )


def _patterned_residuals(x, masked_coeff):
    """Nonlinear residuals honoring a sparsity pattern.

    Row ``i`` depends only on the columns where the pattern is nonzero, because
    ``masked_coeff`` is a dense coefficient matrix multiplied elementwise by the
    pattern. ``sin`` makes the function nonlinear, so the finite-difference
    result genuinely depends on how columns are grouped.
    """
    return np.sin(masked_coeff @ x)


# (normal_fixed, refine_intrinsics, expected_group_count)
_CONFIGS = [(True, False, 13), (False, True, 17)]


class TestBuildStructuralColumnGroups:
    """Tests for the structural finite-difference column grouping."""

    @pytest.mark.parametrize("visibility", [1.0, 0.7, 0.4])
    @pytest.mark.parametrize("normal_fixed, refine_intrinsics, _expected", _CONFIGS)
    def test_grouping_is_valid(
        self, visibility, normal_fixed, refine_intrinsics, _expected
    ):
        """No two columns in a group share a residual row, at any visibility."""
        S = _make_pattern(4, 5, visibility, refine_intrinsics, normal_fixed)
        groups = build_structural_column_groups(
            S,
            4,
            5,
            refine_intrinsics=refine_intrinsics,
            normal_fixed=normal_fixed,
        )

        for group_id in np.unique(groups):
            cols = np.flatnonzero(groups == group_id)
            overlap = S[:, cols].sum(axis=1).max()
            assert overlap <= 1, (
                f"Group {group_id} has {overlap} columns sharing a residual row"
            )

        assert set(groups.tolist()) == set(range(groups.max() + 1))

    def test_fd_jacobian_matches_group_columns(self):
        """Structural grouping yields the same FD Jacobian as group_columns."""
        S = _make_pattern(4, 5, 0.7, refine_intrinsics=True, normal_fixed=False)
        structural = build_structural_column_groups(
            S, 4, 5, refine_intrinsics=True, normal_fixed=False
        )

        rng = np.random.default_rng(42)
        masked_coeff = S * rng.normal(size=S.shape)
        x0 = rng.normal(size=S.shape[1])

        def f(x):
            return _patterned_residuals(x, masked_coeff)

        J_structural = approx_derivative(
            f, x0, method="2-point", sparsity=(S, structural)
        )
        J_greedy = approx_derivative(
            f, x0, method="2-point", sparsity=(S, group_columns(S))
        )

        # A valid grouping only changes how FD perturbations are batched, so
        # the difference quotients -- and hence the Jacobians -- are identical.
        np.testing.assert_allclose(
            J_structural.toarray(), J_greedy.toarray(), rtol=0, atol=0
        )

    @pytest.mark.parametrize("normal_fixed, refine_intrinsics, expected", _CONFIGS)
    def test_group_count_hits_lower_bound(
        self, normal_fixed, refine_intrinsics, expected
    ):
        """Group count equals the max nonzeros per row (13 base, 17 w/ intrinsics)."""
        S = _make_pattern(4, 5, 0.7, refine_intrinsics, normal_fixed)
        groups = build_structural_column_groups(
            S,
            4,
            5,
            refine_intrinsics=refine_intrinsics,
            normal_fixed=normal_fixed,
        )

        lower_bound = S.sum(axis=1).max()
        assert groups.max() + 1 == lower_bound
        assert lower_bound == expected

    def test_single_camera_yields_contiguous_groups(self):
        """Degenerate n_cams == 1 (no extrinsic columns) still compacts to 0..m-1."""
        S = _make_pattern(1, 5, 1.0, refine_intrinsics=False, normal_fixed=True)
        groups = build_structural_column_groups(S, 1, 5)

        assert set(groups.tolist()) == set(range(groups.max() + 1))
        for group_id in np.unique(groups):
            cols = np.flatnonzero(groups == group_id)
            assert S[:, cols].sum(axis=1).max() <= 1


def _make_extrinsics(camera_order):
    """Build a per-camera extrinsics dict with distinct translations."""
    rng = np.random.default_rng(1)
    return {
        cam: CameraExtrinsics(R=np.eye(3), t=rng.normal(size=3)) for cam in camera_order
    }


def _make_board_poses(frame_order):
    """Build a per-frame board-pose dict with distinct rvec/tvec."""
    rng = np.random.default_rng(2)
    return {
        f: BoardPose(frame_idx=f, rvec=rng.normal(size=3), tvec=rng.normal(size=3))
        for f in frame_order
    }


# shared_interface x refine_intrinsics x normal_fixed (8 combinations)
_MODE_MATRIX = [
    (shared, refine, nf)
    for shared in (True, False)
    for refine in (True, False)
    for nf in (True, False)
]


class TestPerCameraInterface:
    """IFACE-02/03/04: per-camera water_z packing, sparsity, and grouping."""

    @pytest.mark.parametrize(
        "shared_interface, refine_intrinsics, normal_fixed", _MODE_MATRIX
    )
    def test_grouping_valid_all_modes(
        self, shared_interface, refine_intrinsics, normal_fixed
    ):
        """IFACE-03: valid grouping in every mode combination (8 total)."""
        n_cams, n_frames = 4, 5
        camera_order = [f"cam{i}" for i in range(n_cams)]
        detections = _make_detections(n_cams, n_frames, visibility=1.0)
        S = build_jacobian_sparsity(
            detections,
            reference_camera="cam0",
            camera_order=camera_order,
            frame_order=list(range(n_frames)),
            min_corners=1,
            refine_intrinsics=refine_intrinsics,
            normal_fixed=normal_fixed,
            shared_interface=shared_interface,
        )
        groups = build_structural_column_groups(
            S,
            n_cams,
            n_frames,
            refine_intrinsics=refine_intrinsics,
            normal_fixed=normal_fixed,
            shared_interface=shared_interface,
        )

        # (a) no group has two columns sharing a residual row
        for group_id in np.unique(groups):
            cols = np.flatnonzero(groups == group_id)
            assert S[:, cols].sum(axis=1).max() <= 1, (
                f"Group {group_id} has columns sharing a residual row"
            )
        # (b) group ids are contiguous 0..m-1
        assert set(groups.tolist()) == set(range(groups.max() + 1))
        # (c) one group entry per column
        assert len(groups) == S.shape[1]
        # (d) group count == max nonzeros per row (the lower bound)
        assert groups.max() + 1 == S.sum(axis=1).max()
        # per-camera lower bound equals the shared lower bound (13 / 17)
        expected = 13 + (4 if refine_intrinsics else 0)
        assert groups.max() + 1 == expected

    @pytest.mark.parametrize(
        "refine_intrinsics, normal_fixed", [(False, True), (True, False)]
    )
    def test_per_camera_group_count_equals_shared(
        self, refine_intrinsics, normal_fixed
    ):
        """Per-camera mode does NOT increase the group count vs shared mode."""
        n_cams, n_frames = 4, 5
        camera_order = [f"cam{i}" for i in range(n_cams)]
        detections = _make_detections(n_cams, n_frames, visibility=1.0)
        common = dict(
            reference_camera="cam0",
            camera_order=camera_order,
            frame_order=list(range(n_frames)),
            min_corners=1,
            refine_intrinsics=refine_intrinsics,
            normal_fixed=normal_fixed,
        )
        S_shared = build_jacobian_sparsity(detections, shared_interface=True, **common)
        S_pc = build_jacobian_sparsity(detections, shared_interface=False, **common)
        g_shared = build_structural_column_groups(
            S_shared,
            n_cams,
            n_frames,
            refine_intrinsics=refine_intrinsics,
            normal_fixed=normal_fixed,
            shared_interface=True,
        )
        g_pc = build_structural_column_groups(
            S_pc,
            n_cams,
            n_frames,
            refine_intrinsics=refine_intrinsics,
            normal_fixed=normal_fixed,
            shared_interface=False,
        )
        assert g_pc.max() + 1 == g_shared.max() + 1

    def test_per_camera_pack_unpack_roundtrip(self):
        """IFACE-04 packing layer: each camera's water_z round-trips individually."""
        camera_order = ["cam0", "cam1", "cam2"]
        frame_order = [0, 1]
        extrinsics = _make_extrinsics(camera_order)
        board_poses = _make_board_poses(frame_order)
        water_z_per_camera = {"cam0": 0.11, "cam1": 0.19, "cam2": 0.27}

        packed = pack_params(
            extrinsics,
            0.15,
            board_poses,
            "cam0",
            camera_order,
            frame_order,
            shared_interface=False,
            water_z_per_camera=water_z_per_camera,
        )
        _, distances, _, _ = unpack_params(
            packed,
            "cam0",
            extrinsics["cam0"],
            camera_order,
            frame_order,
            shared_interface=False,
        )

        for cam, expected in water_z_per_camera.items():
            assert distances[cam] == pytest.approx(expected)
        # Distinct values preserved -- not collapsed to a mean or all-equal.
        assert len({round(v, 9) for v in distances.values()}) == 3

    def test_per_camera_sparsity_columns(self):
        """N water_z columns, each residual depends on exactly one (its camera's)."""
        n_cams, n_frames = 3, 4
        camera_order = [f"cam{i}" for i in range(n_cams)]
        S = build_jacobian_sparsity(
            _make_detections(n_cams, n_frames, visibility=1.0),
            reference_camera="cam0",
            camera_order=camera_order,
            frame_order=list(range(n_frames)),
            min_corners=1,
            shared_interface=False,
        )
        n_extrinsic = 6 * (n_cams - 1)
        water_z_cols = list(range(n_extrinsic, n_extrinsic + n_cams))

        # Exactly n_cams water_z columns, each touched by at least one residual.
        for c in water_z_cols:
            assert S[:, c].sum() > 0
        # Every residual depends on exactly one water_z column (its own camera's).
        per_row = S[:, water_z_cols].sum(axis=1)
        assert per_row.max() == 1
        assert per_row.min() == 1

    def test_per_camera_fd_jacobian_matches_group_columns(self):
        """Per-camera structural grouping yields the same FD Jacobian as group_columns."""
        n_cams, n_frames = 4, 5
        camera_order = [f"cam{i}" for i in range(n_cams)]
        S = build_jacobian_sparsity(
            _make_detections(n_cams, n_frames, visibility=0.7),
            reference_camera="cam0",
            camera_order=camera_order,
            frame_order=list(range(n_frames)),
            min_corners=1,
            refine_intrinsics=True,
            normal_fixed=False,
            shared_interface=False,
        )
        structural = build_structural_column_groups(
            S,
            n_cams,
            n_frames,
            refine_intrinsics=True,
            normal_fixed=False,
            shared_interface=False,
        )

        rng = np.random.default_rng(42)
        masked_coeff = S * rng.normal(size=S.shape)
        x0 = rng.normal(size=S.shape[1])

        def f(x):
            return _patterned_residuals(x, masked_coeff)

        J_structural = approx_derivative(
            f, x0, method="2-point", sparsity=(S, structural)
        )
        J_greedy = approx_derivative(
            f, x0, method="2-point", sparsity=(S, group_columns(S))
        )
        np.testing.assert_allclose(
            J_structural.toarray(), J_greedy.toarray(), rtol=0, atol=0
        )

    def test_shared_mode_bit_identity_default(self):
        """Omitting shared_interface equals passing shared_interface=True, exactly."""
        n_cams, n_frames = 4, 5
        camera_order = [f"cam{i}" for i in range(n_cams)]
        frame_order = list(range(n_frames))
        detections = _make_detections(n_cams, n_frames, visibility=0.7)
        extrinsics = _make_extrinsics(camera_order)
        board_poses = _make_board_poses(frame_order)

        p_default = pack_params(
            extrinsics, 0.15, board_poses, "cam0", camera_order, frame_order
        )
        p_shared = pack_params(
            extrinsics,
            0.15,
            board_poses,
            "cam0",
            camera_order,
            frame_order,
            shared_interface=True,
        )
        np.testing.assert_array_equal(p_default, p_shared)

        lo_d, up_d = build_bounds(camera_order, frame_order, "cam0")
        lo_s, up_s = build_bounds(
            camera_order, frame_order, "cam0", shared_interface=True
        )
        np.testing.assert_array_equal(lo_d, lo_s)
        np.testing.assert_array_equal(up_d, up_s)

        S_d = build_jacobian_sparsity(detections, "cam0", camera_order, frame_order, 1)
        S_s = build_jacobian_sparsity(
            detections, "cam0", camera_order, frame_order, 1, shared_interface=True
        )
        np.testing.assert_array_equal(S_d, S_s)

        g_d = build_structural_column_groups(S_d, n_cams, n_frames)
        g_s = build_structural_column_groups(
            S_s, n_cams, n_frames, shared_interface=True
        )
        np.testing.assert_array_equal(g_d, g_s)


class TestSharedModeBitIdentityIFACE05:
    """IFACE-05: the shared path is bit-identical with/without shared_interface=True.

    Locks the packing/structure layer so any future change that perturbs the
    default single-water_z behavior fails loudly. Complements the end-to-end
    regression in tests/synthetic/test_per_camera_interface.py.
    """

    N_CAMS = 4
    N_FRAMES = 3

    def _fixture(self):
        camera_order = [f"cam{i}" for i in range(self.N_CAMS)]
        frame_order = list(range(self.N_FRAMES))
        detections = _make_detections(self.N_CAMS, self.N_FRAMES, visibility=0.8)
        extrinsics = _make_extrinsics(camera_order)
        board_poses = _make_board_poses(frame_order)
        return camera_order, frame_order, detections, extrinsics, board_poses

    @pytest.mark.parametrize(
        "refine_intrinsics, normal_fixed", [(False, True), (True, False)]
    )
    def test_pack_and_structure_exactly_equal(self, refine_intrinsics, normal_fixed):
        camera_order, frame_order, detections, extrinsics, board_poses = self._fixture()
        # Intrinsics are only needed by pack/bounds when refining.
        intrinsics = None
        if refine_intrinsics:
            from aquacal.config.schema import CameraIntrinsics

            intrinsics = {
                cam: CameraIntrinsics(
                    K=np.array([[900.0, 0, 640.0], [0, 900.0, 360.0], [0, 0, 1]]),
                    dist_coeffs=np.zeros(5),
                    image_size=(1280, 720),
                )
                for cam in camera_order
            }

        pack_kw = dict(
            intrinsics=intrinsics,
            refine_intrinsics=refine_intrinsics,
            normal_fixed=normal_fixed,
        )
        p_default = pack_params(
            extrinsics, 0.15, board_poses, "cam0", camera_order, frame_order, **pack_kw
        )
        p_shared = pack_params(
            extrinsics,
            0.15,
            board_poses,
            "cam0",
            camera_order,
            frame_order,
            shared_interface=True,
            **pack_kw,
        )
        np.testing.assert_array_equal(p_default, p_shared)

        bounds_kw = dict(
            base_intrinsics=intrinsics,
            refine_intrinsics=refine_intrinsics,
            normal_fixed=normal_fixed,
        )
        lo_d, up_d = build_bounds(camera_order, frame_order, "cam0", **bounds_kw)
        lo_s, up_s = build_bounds(
            camera_order, frame_order, "cam0", shared_interface=True, **bounds_kw
        )
        np.testing.assert_array_equal(lo_d, lo_s)
        np.testing.assert_array_equal(up_d, up_s)

        S_d = build_jacobian_sparsity(
            detections,
            "cam0",
            camera_order,
            frame_order,
            1,
            refine_intrinsics=refine_intrinsics,
            normal_fixed=normal_fixed,
        )
        S_s = build_jacobian_sparsity(
            detections,
            "cam0",
            camera_order,
            frame_order,
            1,
            refine_intrinsics=refine_intrinsics,
            normal_fixed=normal_fixed,
            shared_interface=True,
        )
        np.testing.assert_array_equal(S_d, S_s)

        g_d = build_structural_column_groups(
            S_d,
            self.N_CAMS,
            self.N_FRAMES,
            refine_intrinsics=refine_intrinsics,
            normal_fixed=normal_fixed,
        )
        g_s = build_structural_column_groups(
            S_s,
            self.N_CAMS,
            self.N_FRAMES,
            refine_intrinsics=refine_intrinsics,
            normal_fixed=normal_fixed,
            shared_interface=True,
        )
        np.testing.assert_array_equal(g_d, g_s)

    @pytest.mark.parametrize(
        "refine_intrinsics, normal_fixed", [(False, True), (True, False)]
    )
    def test_single_water_z_layout(self, refine_intrinsics, normal_fixed):
        """Shared mode packs exactly one water_z at the expected index."""
        camera_order, frame_order, _, extrinsics, board_poses = self._fixture()
        intrinsics = None
        if refine_intrinsics:
            from aquacal.config.schema import CameraIntrinsics

            intrinsics = {
                cam: CameraIntrinsics(
                    K=np.array([[900.0, 0, 640.0], [0, 900.0, 360.0], [0, 0, 1]]),
                    dist_coeffs=np.zeros(5),
                    image_size=(1280, 720),
                )
                for cam in camera_order
            }

        packed = pack_params(
            extrinsics,
            0.15,
            board_poses,
            "cam0",
            camera_order,
            frame_order,
            intrinsics=intrinsics,
            refine_intrinsics=refine_intrinsics,
            normal_fixed=normal_fixed,
        )

        n_tilt = 0 if normal_fixed else 2
        n_extrinsic = 6 * (self.N_CAMS - 1)
        n_pose = 6 * self.N_FRAMES
        n_intr = 4 * self.N_CAMS if refine_intrinsics else 0
        expected_len = n_tilt + n_extrinsic + 1 + n_pose + n_intr
        assert len(packed) == expected_len
        # The single water_z sits right after the extrinsic block.
        water_z_idx = n_tilt + n_extrinsic
        assert packed[water_z_idx] == pytest.approx(0.15)


class TestMakeSparseJacobianFunc:
    """Tests for make_sparse_jacobian_func with dense_threshold behavior."""

    def test_small_problem_returns_dense_array(self):
        """Small problem (below threshold) returns numpy.ndarray (dense)."""
        # Create a small sparsity pattern (10 residuals x 5 params = 50 elements)
        jac_sparsity = np.ones((10, 5), dtype=np.int8)

        # Create simple linear cost function with known Jacobian
        A = np.random.randn(10, 5)
        cost_func = _toy_cost
        cost_args = (A,)
        bounds = (
            -np.inf * np.ones(5),
            np.inf * np.ones(5),
        )

        # Use default dense_threshold (500M >> 50 elements)
        jac_func = make_sparse_jacobian_func(
            cost_func,
            cost_args,
            jac_sparsity,
            bounds,
            dense_threshold=500_000_000,
        )

        # Evaluate Jacobian at arbitrary point
        params = np.random.randn(5)
        J = jac_func(params, A)

        # Should return numpy.ndarray (dense)
        assert isinstance(J, np.ndarray)
        assert not scipy.sparse.issparse(J)
        assert J.shape == (10, 5)

    def test_large_problem_returns_sparse_matrix(self):
        """Large problem (exceeds threshold) returns sparse matrix."""
        # Create a small sparsity pattern but force sparse path with threshold=0
        jac_sparsity = np.ones((10, 5), dtype=np.int8)

        A = np.random.randn(10, 5)
        cost_func = _toy_cost
        cost_args = (A,)
        bounds = (
            -np.inf * np.ones(5),
            np.inf * np.ones(5),
        )

        # Set dense_threshold=0 to force sparse path
        jac_func = make_sparse_jacobian_func(
            cost_func,
            cost_args,
            jac_sparsity,
            bounds,
            dense_threshold=0,
        )

        # Evaluate Jacobian at arbitrary point
        params = np.random.randn(5)
        J = jac_func(params, A)

        # Should return sparse matrix
        assert scipy.sparse.issparse(J)
        assert J.shape == (10, 5)

    def test_threshold_boundary_behavior(self):
        """Threshold boundary: equal returns dense, exceeds returns sparse."""
        # Create sparsity pattern of known size (100 x 100 = 10,000 elements)
        jac_sparsity = np.ones((100, 100), dtype=np.int8)

        A = np.random.randn(100, 100)
        cost_func = _toy_cost
        cost_args = (A,)
        bounds = (
            -np.inf * np.ones(100),
            np.inf * np.ones(100),
        )
        params = np.random.randn(100)

        # Case 1: dense_threshold = 10,000 (equal) -> should return dense
        jac_func_dense = make_sparse_jacobian_func(
            cost_func,
            cost_args,
            jac_sparsity,
            bounds,
            dense_threshold=10_000,
        )
        J_dense = jac_func_dense(params, A)
        assert isinstance(J_dense, np.ndarray)
        assert not scipy.sparse.issparse(J_dense)

        # Case 2: dense_threshold = 9,999 (exceeds) -> should return sparse
        jac_func_sparse = make_sparse_jacobian_func(
            cost_func,
            cost_args,
            jac_sparsity,
            bounds,
            dense_threshold=9_999,
        )
        J_sparse = jac_func_sparse(params, A)
        assert scipy.sparse.issparse(J_sparse)

    def test_both_paths_produce_correct_jacobian(self):
        """Both dense and sparse paths produce correct Jacobian values."""
        # For linear cost f(x) = A @ x, the Jacobian is exactly A
        # Finite differences should recover this (up to numerical precision)

        # Create test problem
        jac_sparsity = np.ones((20, 10), dtype=np.int8)
        A = np.random.randn(20, 10)
        cost_func = _toy_cost
        cost_args = (A,)
        bounds = (
            -np.inf * np.ones(10),
            np.inf * np.ones(10),
        )
        params = np.random.randn(10)

        # Get dense Jacobian
        jac_func_dense = make_sparse_jacobian_func(
            cost_func,
            cost_args,
            jac_sparsity,
            bounds,
            dense_threshold=500_000_000,  # Force dense
        )
        J_dense = jac_func_dense(params, A)

        # Get sparse Jacobian
        jac_func_sparse = make_sparse_jacobian_func(
            cost_func,
            cost_args,
            jac_sparsity,
            bounds,
            dense_threshold=0,  # Force sparse
        )
        J_sparse = jac_func_sparse(params, A)

        # Convert sparse to dense for comparison
        J_sparse_dense = (
            J_sparse.toarray() if hasattr(J_sparse, "toarray") else J_sparse
        )

        # Both should match the true Jacobian (A) within FD tolerance
        # For a linear function, 2-point FD is exact up to floating-point precision
        np.testing.assert_allclose(J_dense, A, atol=1e-6)
        np.testing.assert_allclose(J_sparse_dense, A, atol=1e-6)

        # Both paths should produce identical results
        np.testing.assert_allclose(J_dense, J_sparse_dense, atol=1e-10)
