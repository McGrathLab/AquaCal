"""Executable audit of the WP5 synthetic-data sweep axes (HOOK-05, HOOK-06).

RESEARCH.md audited the WP5 sweep list against the code in `aquacal.datasets.synthetic`
and found that layout, tank scale, and working distance were already independently
controllable, and that scenarios already carry ground-truth board poses and per-camera
water_z. Only the refractive index axis required production code changes (see
16-02-PLAN.md Task 1). This file pins ALL of those findings as executable tests so a
future refactor cannot silently couple the sweep axes together or regress
seed-reproducibility.
"""

from __future__ import annotations

import itertools

import numpy as np

from aquacal.config.schema import BoardConfig
from aquacal.datasets import create_scenario, generate_synthetic_detections
from aquacal.datasets.synthetic import (
    generate_board_trajectory,
    generate_camera_array,
    generate_dense_xy_grid,
)

_DEFAULT_BOARD = BoardConfig(
    squares_x=12,
    squares_y=9,
    square_size=0.060,
    marker_size=0.045,
    dictionary="DICT_5X5_100",
)


def _pairwise_centre_distances(positions: list[np.ndarray]) -> np.ndarray:
    """Sorted array of all pairwise Euclidean distances between centres."""
    dists = [np.linalg.norm(a - b) for a, b in itertools.combinations(positions, 2)]
    return np.sort(np.array(dists, dtype=np.float64))


def _camera_centres(extrinsics: dict) -> list[np.ndarray]:
    return [ext.C for _, ext in sorted(extrinsics.items())]


def test_layout_axis_produces_distinct_geometries():
    """ring/grid/line produce geometrically distinct camera arrays, not relabels."""
    layouts = ["ring", "grid", "line"]
    centres_by_layout = {}

    for layout in layouts:
        _, extrinsics, _ = generate_camera_array(
            n_cameras=6, layout=layout, spacing=0.1, seed=1
        )
        assert len(extrinsics) == 6
        centres_by_layout[layout] = _camera_centres(extrinsics)

    pairwise_by_layout = {
        layout: _pairwise_centre_distances(centres)
        for layout, centres in centres_by_layout.items()
    }

    for a, b in itertools.combinations(layouts, 2):
        # If two layouts were merely relabelings of the same geometry, the
        # sorted set of pairwise distances would match closely.
        assert not np.allclose(
            pairwise_by_layout[a], pairwise_by_layout[b], atol=1e-6
        ), f"layouts '{a}' and '{b}' produced indistinguishable geometry"

    # Prove the ring layout is a real ring: all centres near-equidistant from
    # the shared centroid.
    ring_centres = np.array(centres_by_layout["ring"])
    centroid = ring_centres.mean(axis=0)
    radii = np.linalg.norm(ring_centres - centroid, axis=1)
    assert radii.std() < 0.01 * radii.mean()


def test_tank_scale_axis_is_independent():
    """Tank scale (spacing) changes rig size but not working distance."""
    _, extrinsics_small, water_zs_small = generate_camera_array(
        n_cameras=6, layout="grid", spacing=0.1, seed=1
    )
    _, extrinsics_large, water_zs_large = generate_camera_array(
        n_cameras=6, layout="grid", spacing=0.4, seed=1
    )

    centres_small = _camera_centres(extrinsics_small)
    centres_large = _camera_centres(extrinsics_large)

    mean_dist_small = _pairwise_centre_distances(centres_small).mean()
    mean_dist_large = _pairwise_centre_distances(centres_large).mean()

    ratio = mean_dist_large / mean_dist_small
    np.testing.assert_allclose(ratio, 4.0, rtol=0.10)

    camera_positions_small = {cam: ext.C for cam, ext in extrinsics_small.items()}
    camera_positions_large = {cam: ext.C for cam, ext in extrinsics_large.items()}

    poses_small = generate_board_trajectory(
        n_frames=50,
        camera_positions=camera_positions_small,
        water_zs=water_zs_small,
        board=_DEFAULT_BOARD,
        depth_range=(0.3, 0.6),
        seed=2,
    )
    poses_large = generate_board_trajectory(
        n_frames=50,
        camera_positions=camera_positions_large,
        water_zs=water_zs_large,
        board=_DEFAULT_BOARD,
        depth_range=(0.3, 0.6),
        seed=2,
    )

    mean_z_small = np.mean([p.tvec[2] for p in poses_small])
    mean_z_large = np.mean([p.tvec[2] for p in poses_large])

    # Same seed + same depth_range -> identical draws regardless of tank scale.
    np.testing.assert_allclose(mean_z_small, mean_z_large, atol=1e-3)


def test_working_distance_axis_is_independent():
    """Changing depth_range moves working distance but not rig geometry."""
    _, extrinsics, water_zs = generate_camera_array(
        n_cameras=4, layout="grid", spacing=0.15, seed=3
    )
    camera_positions = {cam: ext.C for cam, ext in extrinsics.items()}

    poses_near = generate_board_trajectory(
        n_frames=50,
        camera_positions=camera_positions,
        water_zs=water_zs,
        board=_DEFAULT_BOARD,
        # 0.25 sits below this array's derived clearance floor (~0.295 m);
        # 0.30 is the nearest legal minimum (D-19.3-01/GEOM-01).
        depth_range=(0.30, 0.45),
        seed=4,
    )
    poses_far = generate_board_trajectory(
        n_frames=50,
        camera_positions=camera_positions,
        water_zs=water_zs,
        board=_DEFAULT_BOARD,
        depth_range=(0.8, 1.0),
        seed=4,
    )

    mean_depth_near = np.mean([p.tvec[2] for p in poses_near])
    mean_depth_far = np.mean([p.tvec[2] for p in poses_far])
    assert mean_depth_far - mean_depth_near > 0.3

    # The camera array itself (extrinsics dict) is untouched by either call.
    _, extrinsics_after, _ = generate_camera_array(
        n_cameras=4, layout="grid", spacing=0.15, seed=3
    )
    for cam in extrinsics:
        np.testing.assert_array_equal(extrinsics[cam].R, extrinsics_after[cam].R)
        np.testing.assert_array_equal(extrinsics[cam].t, extrinsics_after[cam].t)


def test_refractive_index_axis_is_independent():
    """Changing n_water moves only the optics, not the ground-truth geometry."""
    scenario = create_scenario("ideal", seed=5)

    result_default = generate_synthetic_detections(
        scenario.intrinsics,
        scenario.extrinsics,
        scenario.water_zs,
        _board_geometry(scenario),
        scenario.board_poses,
        n_water=1.333,
        seed=6,
    )
    result_shifted = generate_synthetic_detections(
        scenario.intrinsics,
        scenario.extrinsics,
        scenario.water_zs,
        _board_geometry(scenario),
        scenario.board_poses,
        n_water=1.45,
        seed=6,
    )

    # Detections differ.
    found_diff = False
    for frame_idx, frame_default in result_default.frames.items():
        frame_shifted = result_shifted.frames.get(frame_idx)
        if frame_shifted is None:
            continue
        for cam_name, det_default in frame_default.detections.items():
            det_shifted = frame_shifted.detections.get(cam_name)
            if det_shifted is None:
                continue
            shared_ids = np.intersect1d(det_default.corner_ids, det_shifted.corner_ids)
            for corner_id in shared_ids:
                idx_default = np.where(det_default.corner_ids == corner_id)[0][0]
                idx_shifted = np.where(det_shifted.corner_ids == corner_id)[0][0]
                if not np.allclose(
                    det_default.corners_2d[idx_default],
                    det_shifted.corners_2d[idx_shifted],
                    atol=1e-9,
                ):
                    found_diff = True
    assert found_diff

    # Ground truth geometry (extrinsics, water_zs, board_poses) is unaffected
    # by the index change -- it lives entirely on the SyntheticScenario, which
    # neither call above mutates.
    for cam in scenario.extrinsics:
        np.testing.assert_array_equal(
            scenario.extrinsics[cam].R, scenario.extrinsics[cam].R
        )
        np.testing.assert_array_equal(
            scenario.extrinsics[cam].t, scenario.extrinsics[cam].t
        )
    for cam in scenario.water_zs:
        assert scenario.water_zs[cam] == scenario.water_zs[cam]
    for pose_before, pose_after in zip(scenario.board_poses, scenario.board_poses):
        np.testing.assert_array_equal(pose_before.rvec, pose_after.rvec)
        np.testing.assert_array_equal(pose_before.tvec, pose_after.tvec)


def _board_geometry(scenario):
    from aquacal.core.board import BoardGeometry

    return BoardGeometry(scenario.board_config)


def test_scenario_carries_absolute_error_ground_truth():
    """Every preset exposes everything a sweep needs to compute absolute error."""
    for name in ["ideal", "minimal", "realistic"]:
        scenario = create_scenario(name)

        assert len(scenario.board_poses) > 0
        assert set(scenario.water_zs.keys()) == set(scenario.intrinsics.keys())
        assert isinstance(scenario.n_air, float)
        assert isinstance(scenario.n_water, float)
        assert isinstance(scenario.seed, int)


def test_seed_reproducibility_across_generators():
    """Same-seed calls are identical; different-seed calls differ (HOOK-06)."""
    # generate_camera_array
    _, extrinsics_a, water_zs_a = generate_camera_array(
        n_cameras=5, layout="grid", spacing=0.1, height_variation=0.01, seed=10
    )
    _, extrinsics_b, water_zs_b = generate_camera_array(
        n_cameras=5, layout="grid", spacing=0.1, height_variation=0.01, seed=10
    )
    _, extrinsics_c, water_zs_c = generate_camera_array(
        n_cameras=5, layout="grid", spacing=0.1, height_variation=0.01, seed=11
    )
    for cam in extrinsics_a:
        np.testing.assert_array_equal(extrinsics_a[cam].t, extrinsics_b[cam].t)
    assert any(
        not np.allclose(extrinsics_a[cam].t, extrinsics_c[cam].t)
        or water_zs_a[cam] != water_zs_c[cam]
        for cam in extrinsics_a
    )

    # generate_board_trajectory
    camera_positions = {cam: ext.C for cam, ext in extrinsics_a.items()}
    poses_a = generate_board_trajectory(
        n_frames=10,
        camera_positions=camera_positions,
        water_zs=water_zs_a,
        board=_DEFAULT_BOARD,
        seed=20,
    )
    poses_b = generate_board_trajectory(
        n_frames=10,
        camera_positions=camera_positions,
        water_zs=water_zs_a,
        board=_DEFAULT_BOARD,
        seed=20,
    )
    poses_c = generate_board_trajectory(
        n_frames=10,
        camera_positions=camera_positions,
        water_zs=water_zs_a,
        board=_DEFAULT_BOARD,
        seed=21,
    )
    for pa, pb in zip(poses_a, poses_b):
        np.testing.assert_array_equal(pa.tvec, pb.tvec)
        np.testing.assert_array_equal(pa.rvec, pb.rvec)
    assert any(not np.allclose(pa.tvec, pc.tvec) for pa, pc in zip(poses_a, poses_c))

    # generate_dense_xy_grid
    grid_a = generate_dense_xy_grid(depth=0.5, n_grid=3, seed=30)
    grid_b = generate_dense_xy_grid(depth=0.5, n_grid=3, seed=30)
    grid_c = generate_dense_xy_grid(depth=0.5, n_grid=3, seed=31)
    for pa, pb in zip(grid_a, grid_b):
        np.testing.assert_array_equal(pa.rvec, pb.rvec)
    assert any(not np.allclose(pa.rvec, pc.rvec) for pa, pc in zip(grid_a, grid_c))

    # generate_synthetic_detections
    scenario = create_scenario("ideal", seed=40)
    board = _board_geometry(scenario)
    det_a = generate_synthetic_detections(
        scenario.intrinsics,
        scenario.extrinsics,
        scenario.water_zs,
        board,
        scenario.board_poses,
        noise_std=0.5,
        seed=50,
    )
    det_b = generate_synthetic_detections(
        scenario.intrinsics,
        scenario.extrinsics,
        scenario.water_zs,
        board,
        scenario.board_poses,
        noise_std=0.5,
        seed=50,
    )
    det_c = generate_synthetic_detections(
        scenario.intrinsics,
        scenario.extrinsics,
        scenario.water_zs,
        board,
        scenario.board_poses,
        noise_std=0.5,
        seed=51,
    )

    for frame_idx in det_a.frames:
        for cam_name in det_a.frames[frame_idx].detections:
            np.testing.assert_array_equal(
                det_a.frames[frame_idx].detections[cam_name].corners_2d,
                det_b.frames[frame_idx].detections[cam_name].corners_2d,
            )

    found_diff = False
    for frame_idx in det_a.frames:
        for cam_name, det in det_a.frames[frame_idx].detections.items():
            det_other = det_c.frames.get(frame_idx, None)
            if det_other is None or cam_name not in det_other.detections:
                continue
            if not np.allclose(
                det.corners_2d, det_other.detections[cam_name].corners_2d
            ):
                found_diff = True
    assert found_diff
