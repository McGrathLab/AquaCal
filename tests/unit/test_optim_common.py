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


# (normal_fixed, refine_intrinsics, expected_P, expected_groups) for a 13-camera,
# 100-frame rig. These are the exact numbers quoted in docs/guide/optimizer.md's
# "Sparse Jacobian Strategy" section -- if this tuple ever needs to change, that
# doc section must be updated in the same commit (DOCS-01 / D-20).
_DOCUMENTED_CONFIGS = [
    (True, False, 673, 13),
    (False, False, 675, 13),
    (False, True, 727, 17),
]


class TestDocumentedGroupingNumbers:
    """Pins the exact numbers quoted in docs/guide/optimizer.md's sparse-Jacobian
    section to the shipped `build_structural_column_groups` path (DOCS-01).

    These tests exist so that a future change to the parameter layout or the
    sparsity-building code fails a test rather than silently rotting the prose
    in `docs/guide/optimizer.md`. Every number asserted below is quoted verbatim
    in that doc; if a test here changes, `docs/guide/optimizer.md` must change
    in the same commit.
    """

    @pytest.mark.parametrize(
        "normal_fixed, refine_intrinsics, expected_P, expected_groups",
        _DOCUMENTED_CONFIGS,
    )
    def test_parameter_and_group_counts_match_optimizer_md(
        self, normal_fixed, refine_intrinsics, expected_P, expected_groups
    ):
        """P, group count, and max row-nonzeros for a 13-camera, 100-frame rig.

        These are exactly the numbers `docs/guide/optimizer.md` quotes: P = 673
        (interface normal fixed), 675 (tilt enabled), 727 (tilt + intrinsic
        refinement), with group counts 13, 13, 17 respectively. Derived live
        from `build_jacobian_sparsity` + `build_structural_column_groups` --
        not from scipy's generic greedy grouper (D-21), which is not the
        shipped path.
        """
        S = _make_pattern(13, 100, 1.0, refine_intrinsics, normal_fixed)
        groups = build_structural_column_groups(
            S,
            13,
            100,
            refine_intrinsics=refine_intrinsics,
            normal_fixed=normal_fixed,
        )

        assert S.shape[1] == expected_P
        assert groups.max() + 1 == expected_groups
        assert int(S.sum(axis=1).max()) == expected_groups

    @pytest.mark.parametrize(
        "normal_fixed, refine_intrinsics, expected_P, expected_groups",
        _DOCUMENTED_CONFIGS,
    )
    def test_fd_reduction_matches_optimizer_md(
        self, normal_fixed, refine_intrinsics, expected_P, expected_groups
    ):
        """The FD-evaluation reduction (P / group count) is the 43-52x range
        `docs/guide/optimizer.md` quotes for the sparse-Jacobian column
        grouping (measured 51.8x / 51.9x / 42.8x for the three configurations).

        The ratio is computed from the live `build_structural_column_groups`
        path, not from the parametrized constants -- otherwise this assertion
        would be arithmetic on literals and could not fail on a real
        regression.

        The raw ratio for the intrinsic-refinement case is 727/17 = 42.76..,
        which rounds to the documented 42.8/43 but is not literally >= 43, so
        this asserts on the rounded value (matching how the docs quote it) to
        avoid a boundary-precision false negative.
        """
        S = _make_pattern(13, 100, 1.0, refine_intrinsics, normal_fixed)
        groups = build_structural_column_groups(
            S,
            13,
            100,
            refine_intrinsics=refine_intrinsics,
            normal_fixed=normal_fixed,
        )

        live_P = S.shape[1]
        live_groups = groups.max() + 1
        assert live_P == expected_P
        assert live_groups == expected_groups

        reduction = live_P / live_groups
        assert 43 <= round(reduction) <= 52

    def test_group_count_is_invariant_to_rig_size(self):
        """Group count is fixed by one observation's structure, not the rig.

        `docs/guide/optimizer.md` states that the column-group count does not
        grow with the rig: a single residual row involves exactly one camera
        and one frame, so the group count is bounded by that single
        observation's column count regardless of how many cameras or frames
        exist. This test guards that invariant directly: group count stays at
        13 for 4, 13, and 20 cameras, while the parameter count P grows.
        """
        expected_group_count = 13
        seen_P = set()

        for n_cams in (4, 13, 20):
            S = _make_pattern(
                n_cams, 30, 1.0, refine_intrinsics=False, normal_fixed=True
            )
            groups = build_structural_column_groups(
                S, n_cams, 30, refine_intrinsics=False, normal_fixed=True
            )

            assert groups.max() + 1 == expected_group_count
            seen_P.add(S.shape[1])

        assert len(seen_P) == 3, (
            "P must differ across rig sizes while groups stay fixed"
        )


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


class TestInvalidProjectionKeepsGradient:
    """A board pose above the water surface must not flatten the objective.

    Regression guard for the Stage-3 divergence traced to `compute_residuals`
    substituting a CONSTANT 100.0 px for every observation the refractive model
    could not project. A constant has identically zero derivative, so a frame
    whose observations were all invalid contributed an exact 6-dimensional null
    space: rank 339/345, sv_min 2.1e-12, cond 4.1e16, `xtol` termination at
    first-order optimality 4.3e4 behind a 14 px RMS. Worse, the flat region was
    ABSORBING -- with no gradient there was no force to push the pose back below
    the interface, so an ordinary bad initialization became unrecoverable.

    These tests pin the two properties that fix depends on: an unprojectable
    observation still varies with the parameters, and the fact that it happened
    is reported rather than silently absorbed.
    """

    @staticmethod
    def _scene():
        """A 3-camera scene whose frame 1 board sits ABOVE the water surface."""
        from aquacal.config.schema import BoardConfig, CameraIntrinsics
        from aquacal.core.board import BoardGeometry

        K = np.array([[500, 0, 320], [0, 500, 240], [0, 0, 1]], dtype=np.float64)
        cams = ("cam0", "cam1", "cam2")
        intrinsics = {
            cam: CameraIntrinsics(
                K=K.copy(),
                dist_coeffs=np.zeros(5, dtype=np.float64),
                image_size=(640, 480),
            )
            for cam in cams
        }
        extrinsics = {
            "cam0": CameraExtrinsics(R=np.eye(3), t=np.zeros(3)),
            "cam1": CameraExtrinsics(R=np.eye(3), t=np.array([0.1, 0.0, 0.0])),
            "cam2": CameraExtrinsics(R=np.eye(3), t=np.array([0.0, 0.1, 0.0])),
        }
        board = BoardGeometry(
            BoardConfig(
                squares_x=6,
                squares_y=5,
                square_size=0.04,
                marker_size=0.03,
                dictionary="DICT_4X4_50",
            )
        )
        water_z = 0.15
        # All three frames are generated underwater so detections exist for each.
        poses = [
            BoardPose(
                frame_idx=i,
                rvec=np.array([0.05 * i, 0.05, 0.0]),
                tvec=np.array([0.02 * (i - 1), 0.0, 0.40]),
            )
            for i in range(3)
        ]
        return intrinsics, extrinsics, board, water_z, poses, list(cams)

    def _packed(self, lift_frame1_above_water):
        """Build (params, cost_args) with frame 1 optionally lifted above water."""
        import sys

        sys.path.insert(0, ".")
        from tests.synthetic.ground_truth import generate_synthetic_detections

        intrinsics, extrinsics, board, water_z, poses, cams = self._scene()
        np.random.seed(7)
        detections = generate_synthetic_detections(
            intrinsics,
            extrinsics,
            {c: water_z for c in cams},
            board,
            poses,
            noise_std=0.0,
            min_corners=4,
        )
        # Perturb the *parameter vector*, not the data: frame 1's board is moved
        # to Z = 0.05 < water_z = 0.15, i.e. entirely above the interface. Its
        # detections still exist, so the residual loop keeps all its rows.
        solve_poses = {
            p.frame_idx: BoardPose(
                frame_idx=p.frame_idx,
                rvec=p.rvec.copy(),
                tvec=(
                    np.array([p.tvec[0], p.tvec[1], 0.05])
                    if (lift_frame1_above_water and p.frame_idx == 1)
                    else p.tvec.copy()
                ),
            )
            for p in poses
        }
        frame_order = sorted(solve_poses)
        params = pack_params(
            extrinsics, water_z, solve_poses, "cam0", cams, frame_order
        )
        cost_args = (
            detections,
            intrinsics,
            board,
            "cam0",
            extrinsics["cam0"],
            np.array([0.0, 0.0, -1.0]),
            1.0,
            1.333,
            cams,
            frame_order,
            4,
        )
        return params, cost_args, cams, frame_order

    def test_above_water_frame_has_no_zero_jacobian_columns(self):
        """The lifted frame's 6 pose columns must all carry a nonzero derivative.

        Under the old flat penalty every one of these columns was exactly 0.0.
        """
        from aquacal.calibration._optim_common import compute_residuals

        params, cost_args, cams, frame_order = self._packed(True)
        jac_sparsity = build_jacobian_sparsity(
            cost_args[0], "cam0", cams, frame_order, 4
        )
        jac_func = make_sparse_jacobian_func(
            compute_residuals,
            cost_args,
            jac_sparsity,
            build_bounds(cams, frame_order, "cam0"),
            groups=build_structural_column_groups(
                jac_sparsity, len(cams), len(frame_order)
            ),
        )
        J = jac_func(params, *cost_args)
        J = J.toarray() if hasattr(J, "toarray") else np.asarray(J)

        # Sanity: the scenario really does exercise the invalid branch.
        counts = []
        compute_residuals(params, *cost_args, invalid_count_out=counts)
        assert counts[0] > 0, "scenario did not produce any invalid projections"

        pose_block_start = 6 * (len(cams) - 1) + 1  # normal_fixed, shared water_z
        lifted = pose_block_start + frame_order.index(1) * 6
        column_magnitudes = np.abs(J[:, lifted : lifted + 6]).max(axis=0)
        assert np.all(column_magnitudes > 0.0), (
            "board-pose columns of an above-water frame are exactly zero; the "
            f"objective is flat there. Column magnitudes: {column_magnitudes}"
        )
        assert not np.any(np.abs(J).max(axis=0) == 0.0), (
            "some parameter has an identically-zero Jacobian column"
        )

    def test_valid_scene_reports_no_invalid_projections(self):
        """With every board underwater the invalid branch is never entered.

        This is the bit-identity argument: the continuous-extension code runs
        only when at least one projection fails, so any configuration that
        converged before is numerically untouched.
        """
        from aquacal.calibration._optim_common import compute_residuals

        params, cost_args, _, _ = self._packed(False)
        counts = []
        compute_residuals(params, *cost_args, invalid_count_out=counts)
        assert counts == [0]

    def test_cost_grows_with_height_above_interface(self):
        """The residual must increase as the board rises further above water.

        A monotone response is what supplies the gradient that pushes the pose
        back underwater; the old constant penalty was flat in this direction.
        The restoring force comes from the pinhole continuation itself -- there
        is deliberately no extra above-interface penalty term, because a hinge
        would make the residual C0-but-not-C1 and stop first-order optimality
        from ever reaching zero at the interface.
        """
        from aquacal.calibration._optim_common import compute_residuals

        params, cost_args, cams, frame_order = self._packed(True)
        pose_block_start = 6 * (len(cams) - 1) + 1
        z_index = pose_block_start + frame_order.index(1) * 6 + 5

        costs = []
        for z in (0.10, 0.05, 0.0):
            p = params.copy()
            p[z_index] = z
            r = compute_residuals(p, *cost_args)
            costs.append(float(r @ r))
        assert costs[0] < costs[1] < costs[2], (
            f"cost is not monotone in height above the interface: {costs}"
        )


class TestDegeneracyBreakdownOut:
    """Phase 24 / DEGEN-02: `compute_residuals`' six-key cause/fate/denominator fill.

    Reuses `TestInvalidProjectionKeepsGradient`'s scene, which already produces a
    known invalid population by lifting frame 1 above the water surface.
    """

    @staticmethod
    def _packed(lift_frame1_above_water):
        return TestInvalidProjectionKeepsGradient()._packed(lift_frame1_above_water)

    def test_degeneracy_breakdown_out_defaults_to_none_and_records_nothing(self):
        """The default path is byte-for-byte what every existing caller gets."""
        from aquacal.calibration._optim_common import compute_residuals

        params, cost_args, _, _ = self._packed(True)

        without_kwarg = compute_residuals(params, *cost_args)
        explicit_none = compute_residuals(
            params, *cost_args, degeneracy_breakdown_out=None
        )
        breakdown: dict[str, int] = {}
        instrumented = compute_residuals(
            params, *cost_args, degeneracy_breakdown_out=breakdown
        )

        np.testing.assert_array_equal(without_kwarg, explicit_none)
        np.testing.assert_array_equal(without_kwarg, instrumented)
        assert breakdown, "a supplied dict must be filled"

    def test_clean_scene_fills_six_keys_with_zero_counts_and_a_real_denominator(self):
        from aquacal.calibration._optim_common import compute_residuals

        params, cost_args, _, _ = self._packed(False)
        breakdown: dict[str, int] = {}
        compute_residuals(params, *cost_args, degeneracy_breakdown_out=breakdown)

        assert set(breakdown) == {
            "above_interface",
            "behind_camera",
            "interface_below_camera",
            "extended",
            "penalized",
            "observations_evaluated",
        }
        for key in (
            "above_interface",
            "behind_camera",
            "interface_below_camera",
            "extended",
            "penalized",
        ):
            assert breakdown[key] == 0, breakdown
        assert breakdown["observations_evaluated"] > 0

    def test_degeneracy_breakdown_causes_sum_to_invalid_count_out(self):
        from aquacal.calibration._optim_common import compute_residuals

        params, cost_args, _, _ = self._packed(True)
        counts: list[int] = []
        breakdown: dict[str, int] = {}
        compute_residuals(
            params,
            *cost_args,
            invalid_count_out=counts,
            degeneracy_breakdown_out=breakdown,
        )

        assert counts[0] > 0, "scenario did not produce any invalid projections"
        by_cause = (
            breakdown["above_interface"]
            + breakdown["behind_camera"]
            + breakdown["interface_below_camera"]
        )
        assert by_cause == counts[0]
        assert breakdown["observations_evaluated"] >= counts[0]

    def test_degeneracy_breakdown_fates_sum_to_invalid_count_out(self):
        """The second, independent decomposition of the same invalid set."""
        from aquacal.calibration._optim_common import compute_residuals

        params, cost_args, _, _ = self._packed(True)
        counts: list[int] = []
        breakdown: dict[str, int] = {}
        compute_residuals(
            params,
            *cost_args,
            invalid_count_out=counts,
            degeneracy_breakdown_out=breakdown,
        )

        assert breakdown["extended"] + breakdown["penalized"] == counts[0]

    def test_interface_below_camera_batch_is_attributed_to_that_cause_only(self):
        """A water surface estimated below every camera center: one cause, no others.

        This is a statement about the ESTIMATE -- the free `water_z` parameter has
        excursed below the (also free) camera centers -- and never a claim that
        hardware was submerged.
        """
        from aquacal.calibration._optim_common import compute_residuals

        params, cost_args, cams, _ = self._packed(False)
        water_z_index = 6 * (len(cams) - 1)  # normal_fixed, shared water_z
        params = params.copy()
        params[water_z_index] = -0.05  # below every camera center at Z = 0

        counts: list[int] = []
        breakdown: dict[str, int] = {}
        compute_residuals(
            params,
            *cost_args,
            invalid_count_out=counts,
            degeneracy_breakdown_out=breakdown,
        )

        assert counts[0] > 0
        assert breakdown["interface_below_camera"] == counts[0]
        assert breakdown["above_interface"] == 0
        assert breakdown["behind_camera"] == 0


class TestWaterZBoundsOverride:
    """FIX-01 (D-01): a `water_z_bounds` override reaching `build_bounds` pins the
    water_z slot(s) without touching the default [0.01, 2.0] bound when omitted.
    """

    N_CAMS = 3
    N_FRAMES = 2

    def _order(self):
        camera_order = [f"cam{i}" for i in range(self.N_CAMS)]
        frame_order = list(range(self.N_FRAMES))
        return camera_order, frame_order

    @pytest.mark.parametrize("normal_fixed", [True, False])
    @pytest.mark.parametrize("shared_interface", [True, False])
    def test_override_pins_exactly_the_water_z_slot(
        self, normal_fixed, shared_interface
    ):
        camera_order, frame_order = self._order()
        pin_lo, pin_hi = 1.031 - 1e-12, 1.031 + 1e-12

        lower, upper = build_bounds(
            camera_order,
            frame_order,
            "cam0",
            normal_fixed=normal_fixed,
            shared_interface=shared_interface,
            water_z_bounds=(pin_lo, pin_hi),
        )
        lower_default, upper_default = build_bounds(
            camera_order,
            frame_order,
            "cam0",
            normal_fixed=normal_fixed,
            shared_interface=shared_interface,
        )

        n_tilt_params = 0 if normal_fixed else 2
        n_extrinsic_params = 6 * (self.N_CAMS - 1)
        n_water_z_params = 1 if shared_interface else self.N_CAMS
        water_z_idx = n_tilt_params + n_extrinsic_params

        water_z_slice = slice(water_z_idx, water_z_idx + n_water_z_params)
        np.testing.assert_allclose(lower[water_z_slice], pin_lo)
        np.testing.assert_allclose(upper[water_z_slice], pin_hi)

        # Everything outside the water_z slot is untouched relative to the
        # default-bound call.
        mask = np.ones_like(lower, dtype=bool)
        mask[water_z_slice] = False
        np.testing.assert_array_equal(lower[mask], lower_default[mask])
        np.testing.assert_array_equal(upper[mask], upper_default[mask])

    def test_omitting_override_leaves_default_bound_byte_identical(self):
        """Not passing water_z_bounds must reproduce today's [0.01, 2.0] exactly."""
        camera_order, frame_order = self._order()
        lower_a, upper_a = build_bounds(camera_order, frame_order, "cam0")
        lower_b, upper_b = build_bounds(
            camera_order, frame_order, "cam0", water_z_bounds=None
        )
        np.testing.assert_array_equal(lower_a, lower_b)
        np.testing.assert_array_equal(upper_a, upper_b)

        n_extrinsic_params = 6 * (self.N_CAMS - 1)
        water_z_idx = n_extrinsic_params
        assert lower_a[water_z_idx] == pytest.approx(0.01)
        assert upper_a[water_z_idx] == pytest.approx(2.0)
