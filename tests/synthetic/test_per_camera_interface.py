"""IFACE-05 safety net: shared-mode bit-exactness + equal-seed per-camera recovery.

Two guarantees make the per-camera interface ablation trustworthy:

1. The default shared path is stable and side-effect-free (running Stage 3 twice
   on identical inputs yields bit-identical numbers).
2. When the ground truth really is a single shared interface, per-camera mode
   seeded with equal initial values recovers that shared solution: the N
   per-camera water_z values agree with each other and their mean matches the
   shared-mode water_z, with matching extrinsics and RMS.

The scenario is the deterministic, noiseless ``ideal`` preset (4 cameras,
20 frames) so the recovery tolerances can be tight.
"""

import numpy as np
import pytest

from aquacal.calibration.extrinsics import build_pose_graph, estimate_extrinsics
from aquacal.calibration.interface_estimation import optimize_interface
from aquacal.core.board import BoardGeometry

from .ground_truth import create_scenario, generate_synthetic_detections

INTERFACE_NORMAL = np.array([0.0, 0.0, -1.0], dtype=np.float64)
REFERENCE_CAMERA = "cam0"


def _stage2_inputs():
    """Build the fixed shared-interface scenario and run Stage 2 once."""
    scenario = create_scenario("ideal", seed=42)
    board = BoardGeometry(scenario.board_config)
    detections = generate_synthetic_detections(
        intrinsics=scenario.intrinsics,
        extrinsics=scenario.extrinsics,
        water_zs=scenario.water_zs,
        board=board,
        board_poses=scenario.board_poses,
        noise_std=0.0,
        seed=42,
    )
    pose_graph = build_pose_graph(detections, min_cameras=2)
    initial_extrinsics = estimate_extrinsics(
        pose_graph, scenario.intrinsics, board, REFERENCE_CAMERA
    )
    return scenario, board, detections, initial_extrinsics


def _run_stage3(
    scenario, board, detections, initial_extrinsics, shared_interface, initial_water_zs
):
    return optimize_interface(
        detections=detections,
        intrinsics=scenario.intrinsics,
        initial_extrinsics=initial_extrinsics,
        board=board,
        reference_camera=REFERENCE_CAMERA,
        initial_water_zs=initial_water_zs,
        interface_normal=INTERFACE_NORMAL,
        n_air=1.0,
        n_water=1.333,
        loss="huber",
        loss_scale=1.0,
        min_corners=4,
        verbose=0,
        shared_interface=shared_interface,
    )


@pytest.mark.slow
def test_shared_mode_end_to_end_bit_exact():
    """Stage 3 in shared mode is deterministic: identical inputs -> identical numbers."""
    scenario, board, detections, initial_extrinsics = _stage2_inputs()

    ext1, dist1, _, rms1 = _run_stage3(
        scenario, board, detections, initial_extrinsics, True, None
    )
    ext2, dist2, _, rms2 = _run_stage3(
        scenario, board, detections, initial_extrinsics, True, None
    )

    np.testing.assert_array_equal(rms1, rms2)
    for cam in ext1:
        np.testing.assert_array_equal(ext1[cam].R, ext2[cam].R)
        np.testing.assert_array_equal(ext1[cam].t, ext2[cam].t)
        np.testing.assert_array_equal(dist1[cam], dist2[cam])


@pytest.mark.slow
def test_equal_seed_per_camera_recovers_shared_solution():
    """Per-camera mode with equal seeds recovers the shared solution on shared truth."""
    scenario, board, detections, initial_extrinsics = _stage2_inputs()
    camera_order = sorted(scenario.intrinsics)

    # Shared-mode reference solution (initial_water_zs=None -> 0.15 for all).
    ext_s, dist_s, _, rms_s = _run_stage3(
        scenario, board, detections, initial_extrinsics, True, None
    )
    shared_water_z = dist_s[REFERENCE_CAMERA]  # all cameras equal in shared mode

    # Per-camera mode seeded with the SAME equal start (0.15m everywhere).
    equal_seeds = {cam: 0.15 for cam in camera_order}
    ext_p, dist_p, _, rms_p = _run_stage3(
        scenario, board, detections, initial_extrinsics, False, equal_seeds
    )

    values = np.array([dist_p[cam] for cam in camera_order])

    # (1) The per-camera water_z values collapse back to a single interface.
    #     Noiseless shared ground truth -> agreement within a few millimeters.
    assert np.ptp(values) < 5e-3, (
        f"per-camera water_z spread too large: {np.ptp(values)}"
    )

    # (2) Their mean matches the shared-mode water_z (a Z-coordinate, meters).
    assert abs(values.mean() - shared_water_z) < 5e-3

    # (3) Camera centers match the shared-mode extrinsics (meters).
    for cam in camera_order:
        np.testing.assert_allclose(ext_p[cam].C, ext_s[cam].C, atol=5e-3)

    # (4) Final reprojection RMS matches (pixels).
    assert abs(rms_p - rms_s) < 0.1
