"""Unit tests for E3 tier 3: the `P` formula validated against live `pack_params` (D-22, EXP-07).

Fast unit tests -- minimal fixtures constructed directly, no `create_scenario`, no calibration,
none marked slow.

Adapts (does not import) `_make_detections`/`_make_pattern`/`_make_extrinsics`/`_make_board_poses`
from `tests/unit/test_optim_common.py` so this file stands alone.
"""

from __future__ import annotations

import numpy as np
import pytest

from aquacal.calibration._optim_common import (
    build_jacobian_sparsity,
    build_structural_column_groups,
    pack_params,
)
from aquacal.config.schema import (
    BoardPose,
    CameraExtrinsics,
    CameraIntrinsics,
    Detection,
    DetectionResult,
    FrameDetections,
)


def _make_detections(n_cams, n_frames, visibility, corners_per_view=4, seed=0):
    """Build a DetectionResult where each camera sees each frame with prob `visibility`.

    At least one camera is guaranteed per frame so no frame is empty. Adapted from
    `tests/unit/test_optim_common.py`.
    """
    rng = np.random.default_rng(seed)
    camera_names = [f"cam{i}" for i in range(n_cams)]
    corner_ids = np.arange(corners_per_view, dtype=np.int32)

    frames = {}
    for frame_idx in range(n_frames):
        visible = [c for c in camera_names if rng.random() < visibility]
        if not visible:
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
    n_cams,
    n_frames,
    visibility,
    refine_intrinsics,
    normal_fixed,
    shared_interface=True,
    seed=0,
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
        shared_interface=shared_interface,
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


def _make_intrinsics(camera_order):
    """Build a per-camera intrinsics dict, only needed when refine_intrinsics=True."""
    K = np.array([[500.0, 0, 320], [0, 500.0, 240], [0, 0, 1]], dtype=np.float64)
    dist = np.zeros(5, dtype=np.float64)
    return {
        cam: CameraIntrinsics(
            K=K.copy(), dist_coeffs=dist.copy(), image_size=(640, 480)
        )
        for cam in camera_order
    }


def expected_P(
    n_cams, n_frames, refine_intrinsics, normal_fixed, shared_interface=True
):
    """Closed-form parameter count `P`, mirroring `pack_params`' block layout.

    Each term below was verified against `pack_params`' body (`_optim_common.py`), not copied
    from the supplement on faith:
    - `2` reference-camera tilt params (rx, ry) when `not normal_fixed`, else `0`.
    - `6 * (n_cams - 1)` extrinsic params: one (rvec(3), tvec(3)) block per non-reference
      camera in `camera_order`.
    - `1` water_z param when `shared_interface`, else `n_cams` (one per camera, reference
      included).
    - `6 * n_frames` board-pose params: one (rvec(3), tvec(3)) block per frame.
    - `4 * n_cams` intrinsic params (fx, fy, cx, cy per camera) when `refine_intrinsics`,
      else `0`.
    """
    tilt = 0 if normal_fixed else 2
    extrinsics = 6 * (n_cams - 1)
    water_z = 1 if shared_interface else n_cams
    poses = 6 * n_frames
    intrinsics = 4 * n_cams if refine_intrinsics else 0
    return tilt + extrinsics + water_z + poses + intrinsics


# (n_cams, n_frames, normal_fixed, refine_intrinsics, shared_interface). Six configurations
# spanning two rig sizes and all three boolean axes (D-22).
_CONFIGS = [
    (3, 4, True, False, True),
    (3, 4, False, True, True),
    (3, 4, True, False, False),
    (5, 6, False, False, True),
    (5, 6, True, True, True),
    (5, 6, False, True, False),
]


def _pack_params_for_config(
    n_cams, n_frames, normal_fixed, refine_intrinsics, shared_interface
):
    camera_order = [f"cam{i}" for i in range(n_cams)]
    frame_order = list(range(n_frames))
    extrinsics = _make_extrinsics(camera_order)
    board_poses = _make_board_poses(frame_order)
    intrinsics = _make_intrinsics(camera_order) if refine_intrinsics else None
    water_z_per_camera = (
        None
        if shared_interface
        else {cam: 0.15 + 0.01 * i for i, cam in enumerate(camera_order)}
    )
    return pack_params(
        extrinsics,
        0.15,
        board_poses,
        reference_camera="cam0",
        camera_order=camera_order,
        frame_order=frame_order,
        intrinsics=intrinsics,
        refine_intrinsics=refine_intrinsics,
        normal_fixed=normal_fixed,
        shared_interface=shared_interface,
        water_z_per_camera=water_z_per_camera,
    )


class TestPackParamsLengthMatchesLibrary:
    """`pytest -k pack_params` selects both configuration sweeps (D-22)."""

    @pytest.mark.parametrize(
        "n_cams, n_frames, normal_fixed, refine_intrinsics, shared_interface", _CONFIGS
    )
    def test_pack_params_length_matches_sparsity_columns(
        self, n_cams, n_frames, normal_fixed, refine_intrinsics, shared_interface
    ):
        """`len(pack_params(...))` equals `build_jacobian_sparsity(...).shape[1]`."""
        params = _pack_params_for_config(
            n_cams, n_frames, normal_fixed, refine_intrinsics, shared_interface
        )
        S = _make_pattern(
            n_cams,
            n_frames,
            visibility=1.0,
            refine_intrinsics=refine_intrinsics,
            normal_fixed=normal_fixed,
            shared_interface=shared_interface,
        )
        assert len(params) == S.shape[1]

    @pytest.mark.parametrize(
        "n_cams, n_frames, normal_fixed, refine_intrinsics, shared_interface", _CONFIGS
    )
    def test_pack_params_length_matches_closed_form(
        self, n_cams, n_frames, normal_fixed, refine_intrinsics, shared_interface
    ):
        """`len(pack_params(...))` equals the closed-form `expected_P`, restating the
        supplement's formula in code and validating it against the live packer rather than
        trusting the arithmetic."""
        params = _pack_params_for_config(
            n_cams, n_frames, normal_fixed, refine_intrinsics, shared_interface
        )
        assert len(params) == expected_P(
            n_cams, n_frames, refine_intrinsics, normal_fixed, shared_interface
        )


class TestPerCameraModeGrowsPWithoutGrowingGroups:
    """D-21's prediction, confirmed by measurement rather than assumed."""

    def test_per_camera_mode_grows_p_without_growing_groups(self):
        n_cams, n_frames = 4, 5
        normal_fixed, refine_intrinsics = True, False

        S_shared = _make_pattern(
            n_cams,
            n_frames,
            visibility=1.0,
            refine_intrinsics=refine_intrinsics,
            normal_fixed=normal_fixed,
            shared_interface=True,
        )
        S_pc = _make_pattern(
            n_cams,
            n_frames,
            visibility=1.0,
            refine_intrinsics=refine_intrinsics,
            normal_fixed=normal_fixed,
            shared_interface=False,
        )

        # P strictly grows: N per-camera water_z columns replace the single shared column.
        assert S_pc.shape[1] > S_shared.shape[1]
        assert S_pc.shape[1] - S_shared.shape[1] == n_cams - 1

        groups_shared = build_structural_column_groups(
            S_shared,
            n_cams,
            n_frames,
            refine_intrinsics=refine_intrinsics,
            normal_fixed=normal_fixed,
            shared_interface=True,
        )
        groups_pc = build_structural_column_groups(
            S_pc,
            n_cams,
            n_frames,
            refine_intrinsics=refine_intrinsics,
            normal_fixed=normal_fixed,
            shared_interface=False,
        )

        # Group count unchanged: two cameras' water_z columns never share a residual row, so
        # they collapse into the same FD group slot the shared water_z column occupied.
        assert groups_pc.max() + 1 == groups_shared.max() + 1
