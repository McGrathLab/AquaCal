"""Tests for optimization common utilities (_optim_common.py)."""

import numpy as np
import pytest
import scipy.sparse
from scipy.optimize._numdiff import approx_derivative, group_columns

from aquacal.calibration._optim_common import (
    build_jacobian_sparsity,
    build_structural_column_groups,
    make_sparse_jacobian_func,
)
from aquacal.config.schema import Detection, DetectionResult, FrameDetections


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
