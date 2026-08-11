"""Tests for aquacal.datasets synthetic data generation and loading."""

from pathlib import Path

import numpy as np
import pytest

import aquacal.datasets as datasets_module
from aquacal.config.schema import BoardConfig
from aquacal.core.board import BoardGeometry
from aquacal.datasets import (
    SyntheticScenario,
    board_clearance_floor,
    calibrate_synthetic,
    clear_cache,
    compute_per_camera_errors,
    create_scenario,
    evaluate_reconstruction,
    generate_board_trajectory,
    generate_camera_array,
    generate_dense_xy_grid,
    generate_real_rig_array,
    generate_synthetic_detections,
    get_cache_info,
    list_datasets,
    load_example,
    worst_upward_corner_excursion,
)
from aquacal.datasets._manifest import get_manifest
from aquacal.datasets.synthetic import generate_real_rig_trajectory

_DEFAULT_BOARD = BoardConfig(
    squares_x=12,
    squares_y=9,
    square_size=0.060,
    marker_size=0.045,
    dictionary="DICT_5X5_100",
)

# ============================================================================
# Clearance floor derivation tests (GEOM-01, D-19.3-01)
# ============================================================================


def test_worst_upward_corner_excursion_reference_15deg():
    """Reproduces the phase reference excursion (131.3 mm) to within 2 mm at
    15 deg tilt."""
    excursion = worst_upward_corner_excursion(_DEFAULT_BOARD, 15.0)
    assert excursion == pytest.approx(0.1313, abs=0.002)


def test_worst_upward_corner_excursion_reference_20deg():
    """Reproduces the phase reference excursion (172.0 mm) to within 2 mm at
    20 deg tilt."""
    excursion = worst_upward_corner_excursion(_DEFAULT_BOARD, 20.0)
    assert excursion == pytest.approx(0.1720, abs=0.002)


def test_board_clearance_floor_reference_15deg():
    """Reproduces the phase reference floor (1.181 m) to within 2 mm at
    15 deg tilt, anchored on the deepest water_z (1.0367)."""
    floor = board_clearance_floor(_DEFAULT_BOARD, {"c": 1.0367}, 15.0)
    assert floor == pytest.approx(1.181, abs=0.002)


def test_board_clearance_floor_reference_20deg():
    """Reproduces the phase reference floor (1.226 m) to within 2 mm at
    20 deg tilt, anchored on the deepest water_z (1.0367)."""
    floor = board_clearance_floor(_DEFAULT_BOARD, {"c": 1.0367}, 20.0)
    assert floor == pytest.approx(1.226, abs=0.002)


def test_board_clearance_floor_uses_deepest_water_z_not_mean():
    """The floor anchors on max(water_zs), not the mean and not a frozen
    constant like WATER_Z."""
    water_zs = {"a": 1.0, "b": 1.0367, "c": 1.02}
    floor = board_clearance_floor(_DEFAULT_BOARD, water_zs, 15.0)
    excursion = worst_upward_corner_excursion(_DEFAULT_BOARD, 15.0)
    expected = max(water_zs.values()) + 1.1 * excursion
    assert floor == pytest.approx(expected)


def test_derived_floor_moves_with_square_size():
    """Doubling square_size strictly increases the derived floor -- proves
    the floor is DERIVED, not hardcoded (D-19.3-01)."""
    small_board = BoardConfig(
        squares_x=12,
        squares_y=9,
        square_size=0.060,
        marker_size=0.045,
        dictionary="DICT_5X5_100",
    )
    large_board = BoardConfig(
        squares_x=12,
        squares_y=9,
        square_size=0.120,
        marker_size=0.045,
        dictionary="DICT_5X5_100",
    )
    water_zs = {"c": 1.0367}
    floor_small = board_clearance_floor(small_board, water_zs, 15.0)
    floor_large = board_clearance_floor(large_board, water_zs, 15.0)
    assert floor_large > floor_small


def test_derived_floor_moves_with_rotation_range():
    """Raising rotation_range_deg from 15 to 20 strictly increases the
    derived floor."""
    water_zs = {"c": 1.0367}
    floor_15 = board_clearance_floor(_DEFAULT_BOARD, water_zs, 15.0)
    floor_20 = board_clearance_floor(_DEFAULT_BOARD, water_zs, 20.0)
    assert floor_20 > floor_15


def test_derived_floor_moves_with_squares_y():
    """Changing squares_y changes the derived floor (a different board
    shape has a different corner cloud)."""
    board_9 = BoardConfig(
        squares_x=12,
        squares_y=9,
        square_size=0.060,
        marker_size=0.045,
        dictionary="DICT_5X5_100",
    )
    board_13 = BoardConfig(
        squares_x=12,
        squares_y=13,
        square_size=0.060,
        marker_size=0.045,
        dictionary="DICT_5X5_100",
    )
    water_zs = {"c": 1.0367}
    floor_9 = board_clearance_floor(board_9, water_zs, 15.0)
    floor_13 = board_clearance_floor(board_13, water_zs, 15.0)
    assert floor_9 != floor_13


def test_board_clearance_floor_margin_factor_applies_to_excursion_only():
    """`(1.0 + margin_factor)` multiplies the derived excursion only -- it is
    never added directly to max(water_zs)."""
    water_zs = {"c": 1.0367}
    excursion = worst_upward_corner_excursion(_DEFAULT_BOARD, 15.0)
    floor_default = board_clearance_floor(_DEFAULT_BOARD, water_zs, 15.0)
    floor_explicit = board_clearance_floor(
        _DEFAULT_BOARD, water_zs, 15.0, margin_factor=0.1
    )
    assert floor_default == pytest.approx(floor_explicit)
    assert floor_default == pytest.approx(max(water_zs.values()) + 1.1 * excursion)
    # A larger margin_factor increases the floor by scaling the excursion,
    # not by a flat additive bump to max(water_zs).
    floor_bigger_margin = board_clearance_floor(
        _DEFAULT_BOARD, water_zs, 15.0, margin_factor=0.2
    )
    assert floor_bigger_margin == pytest.approx(
        max(water_zs.values()) + 1.2 * excursion
    )


# ============================================================================
# Board re-centring and clearance enforcement tests
# (D-19.3-02/03/04/05/19, GEOM-01)
# ============================================================================


def _grid_array_for_recentring_tests(n_cameras=6, seed=1):
    _, extrinsics, water_zs = generate_camera_array(
        n_cameras=n_cameras, layout="grid", spacing=0.1, seed=seed
    )
    camera_positions = {cam: ext.C for cam, ext in extrinsics.items()}
    return camera_positions, water_zs


def test_board_trajectory_poses_are_centred_on_board_centre():
    """Every pose's world-frame corner-cloud mean sits inside depth_range and
    the center +/- xy_extent box -- tvec places the board CENTRE, not a
    corner (D-19.3-19)."""
    camera_positions, water_zs = _grid_array_for_recentring_tests()
    center = (0.1, -0.2)
    xy_extent = 0.15
    depth_range = board_clearance_floor(_DEFAULT_BOARD, water_zs, 15.0), 2.0
    board_geom = BoardGeometry(_DEFAULT_BOARD)

    poses = generate_board_trajectory(
        n_frames=30,
        camera_positions=camera_positions,
        water_zs=water_zs,
        board=_DEFAULT_BOARD,
        depth_range=depth_range,
        xy_extent=xy_extent,
        center=center,
        seed=5,
    )

    for pose in poses:
        world_corners = board_geom.transform_corners(pose.rvec, pose.tvec)
        mean_xyz = np.mean(np.array(list(world_corners.values())), axis=0)
        assert depth_range[0] - 1e-9 <= mean_xyz[2] <= depth_range[1] + 1e-9
        assert abs(mean_xyz[0] - center[0]) <= xy_extent + 1e-6
        assert abs(mean_xyz[1] - center[1]) <= xy_extent + 1e-6


def test_board_trajectory_no_corner_submerged_over_500_frames():
    """No board corner is ever at or above the deepest interface, across 500
    frames of the default grid generator."""
    camera_positions, water_zs = _grid_array_for_recentring_tests()
    board_geom = BoardGeometry(_DEFAULT_BOARD)
    max_water_z = max(water_zs.values())

    poses = generate_board_trajectory(
        n_frames=500,
        camera_positions=camera_positions,
        water_zs=water_zs,
        board=_DEFAULT_BOARD,
        seed=11,
    )

    # World +Z is DOWN, so "at or above the interface" means corner Z <=
    # max_water_z. No corner may reach or cross that line.
    min_corner_z = min(
        float(pos[2])
        for pose in poses
        for pos in board_geom.transform_corners(pose.rvec, pose.tvec).values()
    )
    assert min_corner_z > max_water_z


def test_real_rig_trajectory_no_corner_submerged_over_500_frames():
    """No board corner is ever at or above the deepest interface, across 500
    frames of the real-rig generator."""
    _, _, water_zs = generate_real_rig_array()
    board_geom = BoardGeometry(_DEFAULT_BOARD)
    max_water_z = max(water_zs.values())

    poses = generate_real_rig_trajectory(
        n_frames=500,
        board=_DEFAULT_BOARD,
        water_zs=water_zs,
        seed=13,
    )

    min_corner_z = min(
        float(pos[2])
        for pose in poses
        for pos in board_geom.transform_corners(pose.rvec, pose.tvec).values()
    )
    assert min_corner_z > max_water_z


def test_board_trajectory_illegal_depth_range_raises_value_error():
    """An explicit depth_range below the derived floor raises ValueError
    naming both the floor and the supplied minimum."""
    camera_positions, water_zs = _grid_array_for_recentring_tests()
    floor = board_clearance_floor(_DEFAULT_BOARD, water_zs, 15.0)
    illegal_min = floor - 0.05

    with pytest.raises(ValueError, match=r"[Ff]loor"):
        generate_board_trajectory(
            n_frames=1,
            camera_positions=camera_positions,
            water_zs=water_zs,
            board=_DEFAULT_BOARD,
            depth_range=(illegal_min, 2.0),
        )


def test_board_trajectory_legal_depth_range_at_floor_does_not_raise():
    """A depth_range whose minimum equals the derived floor is legal."""
    camera_positions, water_zs = _grid_array_for_recentring_tests()
    floor = board_clearance_floor(_DEFAULT_BOARD, water_zs, 15.0)

    poses = generate_board_trajectory(
        n_frames=1,
        camera_positions=camera_positions,
        water_zs=water_zs,
        board=_DEFAULT_BOARD,
        depth_range=(floor, 2.0),
    )
    assert len(poses) == 1


def test_real_rig_trajectory_illegal_depth_range_raises_value_error():
    """An explicit depth_range below the derived floor raises ValueError for
    the real-rig generator too."""
    _, _, water_zs = generate_real_rig_array()
    floor = board_clearance_floor(_DEFAULT_BOARD, water_zs, 20.0)
    illegal_min = floor - 0.05

    with pytest.raises(ValueError, match=r"[Ff]loor"):
        generate_real_rig_trajectory(
            n_frames=1,
            board=_DEFAULT_BOARD,
            water_zs=water_zs,
            depth_range=(illegal_min, 2.0),
        )


def test_board_trajectory_requires_board_keyword():
    """Omitting `board=` raises TypeError, not ValueError and not a silent
    success (D-19.3-05)."""
    camera_positions, water_zs = _grid_array_for_recentring_tests()

    with pytest.raises(TypeError):
        generate_board_trajectory(
            n_frames=1,
            camera_positions=camera_positions,
            water_zs=water_zs,
        )


def test_real_rig_trajectory_requires_board_keyword():
    """Omitting `board=` raises TypeError for the real-rig generator too."""
    with pytest.raises(TypeError):
        generate_real_rig_trajectory(n_frames=1)


def test_board_trajectory_rng_determinism_only_tvec_offset():
    """For a fixed seed, the sampled (x, y, z, rx, ry, rz) sequence is
    unchanged from pre-fix -- only tvec is offset by the centroid re-centring
    (D-19.3-19). rvec must be bit-identical to the pre-fix stream."""
    camera_positions, water_zs = _grid_array_for_recentring_tests()

    def _pre_fix_stream(n_frames, camera_positions, water_zs, seed):
        xs = [float(p[0]) for p in camera_positions.values()]
        ys = [float(p[1]) for p in camera_positions.values()]
        cx, cy = float(np.mean(xs)), float(np.mean(ys))
        rng = np.random.default_rng(seed)
        depth_range = board_clearance_floor(_DEFAULT_BOARD, water_zs, 15.0), 2.0
        xy_extent = 0.15
        rows = []
        for _ in range(n_frames):
            _ = cx + rng.uniform(-xy_extent, xy_extent)
            _ = cy + rng.uniform(-xy_extent, xy_extent)
            _ = rng.uniform(depth_range[0], depth_range[1])
            max_tilt = np.deg2rad(15.0)
            rx = rng.uniform(-max_tilt, max_tilt)
            ry = rng.uniform(-max_tilt, max_tilt)
            rz = rng.uniform(-np.pi, np.pi)
            rows.append((rx, ry, rz))
        return rows

    expected_rvecs = _pre_fix_stream(
        n_frames=5, camera_positions=camera_positions, water_zs=water_zs, seed=42
    )
    poses = generate_board_trajectory(
        n_frames=5,
        camera_positions=camera_positions,
        water_zs=water_zs,
        board=_DEFAULT_BOARD,
        seed=42,
    )
    for pose, (rx, ry, rz) in zip(poses, expected_rvecs):
        np.testing.assert_array_equal(pose.rvec, np.array([rx, ry, rz]))


# ============================================================================
# create_scenario Tests
# ============================================================================


def test_create_scenario_ideal():
    """Test ideal preset returns 4 cameras and 20 frames."""
    scenario = create_scenario("ideal")

    assert isinstance(scenario, SyntheticScenario)
    assert scenario.name == "ideal"
    assert len(scenario.intrinsics) == 4
    assert len(scenario.extrinsics) == 4
    assert len(scenario.water_zs) == 4
    assert len(scenario.board_poses) == 20
    assert scenario.noise_std == 0.0


def test_create_scenario_minimal():
    """Test minimal preset returns 2 cameras and 10 frames."""
    scenario = create_scenario("minimal")

    assert isinstance(scenario, SyntheticScenario)
    assert scenario.name == "minimal"
    assert len(scenario.intrinsics) == 2
    assert len(scenario.extrinsics) == 2
    assert len(scenario.water_zs) == 2
    assert len(scenario.board_poses) == 10
    assert scenario.noise_std == 0.3


def test_create_scenario_realistic():
    """Test realistic preset returns 12 cameras and 30 frames."""
    scenario = create_scenario("realistic")

    assert isinstance(scenario, SyntheticScenario)
    assert scenario.name == "realistic"
    assert len(scenario.intrinsics) == 12
    assert len(scenario.extrinsics) == 12
    assert len(scenario.water_zs) == 12
    assert len(scenario.board_poses) == 30
    assert scenario.noise_std == 0.5


def test_create_scenario_invalid_name():
    """Test that unknown name raises ValueError."""
    with pytest.raises(ValueError, match="Unknown scenario.*unknown"):
        create_scenario("unknown")


def test_create_scenario_reproducibility():
    """Test that same preset with same seed produces identical output."""
    scenario1 = create_scenario("ideal", seed=42)
    scenario2 = create_scenario("ideal", seed=42)

    # Check intrinsics are identical
    for cam in scenario1.intrinsics:
        assert np.allclose(scenario1.intrinsics[cam].K, scenario2.intrinsics[cam].K)

    # Check extrinsics are identical
    for cam in scenario1.extrinsics:
        assert np.allclose(scenario1.extrinsics[cam].R, scenario2.extrinsics[cam].R)
        assert np.allclose(scenario1.extrinsics[cam].t, scenario2.extrinsics[cam].t)

    # Check board poses are identical
    assert len(scenario1.board_poses) == len(scenario2.board_poses)
    for pose1, pose2 in zip(scenario1.board_poses, scenario2.board_poses):
        assert np.allclose(pose1.rvec, pose2.rvec)
        assert np.allclose(pose1.tvec, pose2.tvec)


def test_create_scenario_different_seeds():
    """Test that different seeds produce different output."""
    scenario1 = create_scenario("ideal", seed=42)
    scenario2 = create_scenario("ideal", seed=99)

    # Extrinsics should differ (different random rolls)
    cam1_t = scenario1.extrinsics["cam1"].t
    cam1_t_other = scenario2.extrinsics["cam1"].t
    assert not np.allclose(cam1_t, cam1_t_other)


def test_create_scenario_board_config_consistency():
    """Test that all presets use the same ChArUco board config."""
    ideal = create_scenario("ideal")
    minimal = create_scenario("minimal")
    realistic = create_scenario("realistic")

    for scenario in [ideal, minimal, realistic]:
        assert scenario.board_config.squares_x == 12
        assert scenario.board_config.squares_y == 9
        assert np.isclose(scenario.board_config.square_size, 0.060)
        assert np.isclose(scenario.board_config.marker_size, 0.045)
        assert scenario.board_config.dictionary == "DICT_5X5_100"


def test_create_scenario_reference_camera_at_origin():
    """Test that cam0 is always at origin with identity rotation."""
    for name in ["ideal", "minimal"]:
        scenario = create_scenario(name)
        cam0_extrinsics = scenario.extrinsics["cam0"]
        assert np.allclose(cam0_extrinsics.R, np.eye(3))
        assert np.allclose(cam0_extrinsics.t, np.zeros(3))


# ============================================================================
# Real-rig standoff finished into the library (D-19.3-09, GEOM-02)
# ============================================================================


def test_generate_camera_array_default_height_is_water_z():
    """generate_camera_array's height_above_water default equals the
    module-level WATER_Z, not the old 0.15 m shallow-tank value."""
    import inspect

    from aquacal.datasets.synthetic import WATER_Z, generate_camera_array

    default = (
        inspect.signature(generate_camera_array)
        .parameters["height_above_water"]
        .default
    )
    assert default == WATER_Z
    assert default > 1.0


def test_generate_board_trajectory_has_no_min_cameras_per_frame():
    """The dead `min_cameras_per_frame` parameter is gone from the signature.

    D-05: it was declared but referenced zero times in the body, so the
    docstring's per-frame visibility guarantee was never enforced. It is
    dropped rather than implemented -- implementing the filter would change
    every existing seed's trajectory and invalidate the published seed bands.

    Note this is NOT `CalibrationConfig.min_cameras_per_frame`, which is a
    different, live field driving real frame filtering in the pipeline.
    """
    import inspect

    from aquacal.datasets.synthetic import generate_board_trajectory

    params = inspect.signature(generate_board_trajectory).parameters
    assert "min_cameras_per_frame" not in params


@pytest.mark.parametrize("name", ["ideal", "minimal", "realistic"])
def test_create_scenario_presets_construct_at_real_rig_standoff(name):
    """Every preset's cameras sit at the real-rig standoff -- no 0.15 m rig
    survives (D-19.3-09)."""
    scenario = create_scenario(name)
    assert min(scenario.water_zs.values()) > 1.0


def test_create_scenario_presets_share_board_field_for_field():
    """All three presets' board_config values are equal field-for-field
    (D-19.3-08: board size is constant across every scenario)."""
    ideal = create_scenario("ideal")
    minimal = create_scenario("minimal")
    realistic = create_scenario("realistic")

    for a, b in [(ideal, minimal), (ideal, realistic), (minimal, realistic)]:
        assert a.board_config.squares_x == b.board_config.squares_x
        assert a.board_config.squares_y == b.board_config.squares_y
        assert a.board_config.square_size == b.board_config.square_size
        assert a.board_config.marker_size == b.board_config.marker_size
        assert a.board_config.dictionary == b.board_config.dictionary
        assert a.board_config.legacy_pattern == b.board_config.legacy_pattern


@pytest.mark.parametrize("name", ["ideal", "minimal", "realistic"])
def test_create_scenario_presets_no_corner_submerged(name):
    """No board corner is at or above the deepest interface in any frame of
    any preset (D-19.3-01/D-19.3-09 combined: the library cannot construct a
    mis-framed rig by accident)."""
    scenario = create_scenario(name)
    board_geom = BoardGeometry(scenario.board_config)
    max_water_z = max(scenario.water_zs.values())

    min_corner_z = min(
        float(pos[2])
        for pose in scenario.board_poses
        for pos in board_geom.transform_corners(pose.rvec, pose.tvec).values()
    )
    assert min_corner_z > max_water_z


# ============================================================================
# Dataset Loading / Manifest Tests
# ============================================================================


def test_list_datasets():
    """Test listing all available datasets."""
    datasets = list_datasets()

    assert isinstance(datasets, list)
    assert "real-rig" in datasets


def test_load_example_nonexistent():
    """Test that loading nonexistent dataset raises ValueError."""
    with pytest.raises(ValueError, match="Unknown dataset.*nonexistent"):
        load_example("nonexistent")


def test_manifest_loading():
    """Test that manifest loads and has expected structure."""
    manifest = get_manifest()

    assert isinstance(manifest, dict)
    assert "version" in manifest
    assert "datasets" in manifest

    datasets = manifest["datasets"]
    assert "real-rig" in datasets

    # Real-rig should not be included (requires download)
    assert datasets["real-rig"]["included"] is False
    assert datasets["real-rig"]["type"] == "real"
    # Pins the PUBLISHED record the shipped manifest points at. Bump this
    # deliberately whenever a new Zenodo version is minted -- a silent drift
    # here means load_example() fetches the wrong archive.
    assert datasets["real-rig"]["zenodo_record_id"] == 21889922
    assert datasets["real-rig"]["checksum"] == "md5:dff1012fb772d627e0f3f106d5c6de84"
    assert datasets["real-rig"]["size_bytes"] == 4350418046


# ============================================================================
# Cache Management Tests
# ============================================================================


def test_get_cache_dir(tmp_path, monkeypatch):
    """Test cache directory creation and .gitignore."""
    from aquacal.datasets.download import get_cache_dir

    monkeypatch.chdir(tmp_path)

    cache_dir = get_cache_dir()

    assert cache_dir.exists()
    assert cache_dir.is_dir()
    assert cache_dir.name == "aquacal_data"

    gitignore = cache_dir / ".gitignore"
    assert gitignore.exists()
    assert gitignore.read_text() == "*\n"


def test_clear_cache(tmp_path, monkeypatch):
    """Test clearing the cache."""
    from aquacal.datasets.download import get_cache_dir

    monkeypatch.chdir(tmp_path)

    cache_dir = get_cache_dir()
    dataset_dir = cache_dir / "medium"
    dataset_dir.mkdir()
    (dataset_dir / "test.txt").write_text("test")

    downloads_dir = cache_dir / "downloads"
    downloads_dir.mkdir()
    (downloads_dir / "medium.zip").write_text("fake zip")

    clear_cache("medium")

    assert not dataset_dir.exists()
    assert not (downloads_dir / "medium.zip").exists()
    assert cache_dir.exists()
    assert downloads_dir.exists()

    (cache_dir / "large").mkdir()
    clear_cache()

    assert not cache_dir.exists()


def test_get_cache_info(tmp_path, monkeypatch):
    """Test getting cache information."""
    monkeypatch.chdir(tmp_path)

    info = get_cache_info()
    assert info["cached_datasets"] == []
    assert info["total_size_mb"] == 0.0

    from aquacal.datasets.download import get_cache_dir

    cache_dir = get_cache_dir()
    medium_dir = cache_dir / "medium"
    medium_dir.mkdir()
    (medium_dir / "test.txt").write_text("x" * 1024)

    large_dir = cache_dir / "large"
    large_dir.mkdir()
    (large_dir / "test.txt").write_text("x" * 2048)

    info = get_cache_info()
    assert set(info["cached_datasets"]) == {"medium", "large"}
    assert info["total_size_mb"] > 0
    assert "aquacal_data" in info["cache_dir"]


# ============================================================================
# Refractive Index Plumbing Tests (HOOK-05)
# ============================================================================


def _small_scenario_detections_inputs():
    """Build a small camera array + trajectory + board for detection tests."""
    intrinsics, extrinsics, water_zs = generate_camera_array(
        n_cameras=3,
        layout="grid",
        spacing=0.1,
        height_above_water=0.15,
        height_variation=0.0,
        seed=1,
    )
    camera_positions = {cam: ext.C for cam, ext in extrinsics.items()}
    board_poses = generate_board_trajectory(
        n_frames=5,
        camera_positions=camera_positions,
        water_zs=water_zs,
        board=_DEFAULT_BOARD,
        depth_range=None,
        xy_extent=0.08,
        seed=1,
    )
    board_config = _DEFAULT_BOARD
    board = BoardGeometry(board_config)
    return intrinsics, extrinsics, water_zs, board, board_poses


def test_generate_detections_default_index_unchanged():
    """Omitting n_air/n_water reproduces explicit 1.0/1.333 bit-identically."""
    intrinsics, extrinsics, water_zs, board, board_poses = (
        _small_scenario_detections_inputs()
    )

    result_default = generate_synthetic_detections(
        intrinsics, extrinsics, water_zs, board, board_poses, seed=7
    )
    result_explicit = generate_synthetic_detections(
        intrinsics,
        extrinsics,
        water_zs,
        board,
        board_poses,
        n_air=1.0,
        n_water=1.333,
        seed=7,
    )

    assert result_default.frames.keys() == result_explicit.frames.keys()
    for frame_idx in result_default.frames:
        det_default = result_default.frames[frame_idx].detections
        det_explicit = result_explicit.frames[frame_idx].detections
        assert det_default.keys() == det_explicit.keys()
        for cam_name in det_default:
            np.testing.assert_array_equal(
                det_default[cam_name].corners_2d, det_explicit[cam_name].corners_2d
            )
            np.testing.assert_array_equal(
                det_default[cam_name].corner_ids, det_explicit[cam_name].corner_ids
            )


def test_generate_detections_index_changes_projection():
    """A different n_water measurably changes projected pixel coordinates."""
    intrinsics, extrinsics, water_zs, board, board_poses = (
        _small_scenario_detections_inputs()
    )

    result_default = generate_synthetic_detections(
        intrinsics, extrinsics, water_zs, board, board_poses, n_water=1.333, seed=7
    )
    result_shifted = generate_synthetic_detections(
        intrinsics, extrinsics, water_zs, board, board_poses, n_water=1.50, seed=7
    )

    max_diff = 0.0
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
                diff = np.linalg.norm(
                    det_default.corners_2d[idx_default]
                    - det_shifted.corners_2d[idx_shifted]
                )
                max_diff = max(max_diff, diff)

    assert max_diff > 0.5


def test_scenario_records_index_and_seed():
    """create_scenario records the requested seed and refractive indices."""
    scenario = create_scenario("ideal", seed=7, n_water=1.40)

    assert scenario.seed == 7
    assert np.isclose(scenario.n_water, 1.40)
    assert np.isclose(scenario.n_air, 1.0)


def test_scenario_defaults_backward_compatible():
    """create_scenario without new args keeps the pre-change defaults."""
    scenario = create_scenario("ideal")

    assert np.isclose(scenario.n_water, 1.333)
    assert np.isclose(scenario.n_air, 1.0)
    assert scenario.seed == 42


# ============================================================================
# Widened Export Surface Tests (Phase 19.1 EXP-01)
# ============================================================================


def test_all_exports():
    """Every one of the seven widened aquacal.datasets.__all__ names imports and is
    callable/typed; generate_real_rig_trajectory is deliberately absent."""
    widened_names = [
        "calibrate_synthetic",
        "compute_per_camera_errors",
        "evaluate_reconstruction",
        "generate_board_trajectory",
        "generate_camera_array",
        "generate_dense_xy_grid",
        "generate_real_rig_array",
    ]
    for name in widened_names:
        assert name in datasets_module.__all__
        assert callable(getattr(datasets_module, name))

    assert callable(calibrate_synthetic)
    assert callable(compute_per_camera_errors)
    assert callable(evaluate_reconstruction)
    assert callable(generate_board_trajectory)
    assert callable(generate_camera_array)
    assert callable(generate_dense_xy_grid)
    assert callable(generate_real_rig_array)

    assert "generate_real_rig_trajectory" not in datasets_module.__all__


# ============================================================================
# D-27 -- centroid-default board trajectory, and its containment gate
# (19.2-GAP-CONTEXT.md D-27; plan 19.2-18)
# ============================================================================


def test_board_trajectory_default_centers_on_grid_array_centroid():
    """The default trajectory's mean XY sits at the centroid of a grid array,
    not at cam0's origin (D-27)."""
    _, extrinsics, water_zs = generate_camera_array(
        n_cameras=12, layout="grid", spacing=0.1, seed=1
    )
    camera_positions = {cam: ext.C for cam, ext in extrinsics.items()}
    centroid = np.mean(np.array([p[:2] for p in camera_positions.values()]), axis=0)

    poses = generate_board_trajectory(
        n_frames=500,
        camera_positions=camera_positions,
        water_zs=water_zs,
        board=_DEFAULT_BOARD,
        xy_extent=0.15,
        seed=1,
    )
    mean_xy = np.mean(np.array([p.tvec[:2] for p in poses]), axis=0)

    np.testing.assert_allclose(mean_xy, centroid, atol=0.02)


def test_board_trajectory_default_centers_on_line_array_centroid():
    """The default trajectory's mean XY sits at the centroid of a line array
    -- roughly 0.55 m from cam0 for a 12-camera line at spacing 0.1 (D-27's
    audited offset)."""
    _, extrinsics, water_zs = generate_camera_array(
        n_cameras=12, layout="line", spacing=0.1, seed=1
    )
    camera_positions = {cam: ext.C for cam, ext in extrinsics.items()}
    centroid = np.mean(np.array([p[:2] for p in camera_positions.values()]), axis=0)

    poses = generate_board_trajectory(
        n_frames=500,
        camera_positions=camera_positions,
        water_zs=water_zs,
        board=_DEFAULT_BOARD,
        xy_extent=0.15,
        seed=1,
    )
    mean_xy = np.mean(np.array([p.tvec[:2] for p in poses]), axis=0)

    np.testing.assert_allclose(mean_xy, centroid, atol=0.02)
    # cam0 sits at the origin (generate_camera_array's own recentring), so
    # the centroid's distance from the origin IS the offset D-27 measured.
    offset_from_origin = np.linalg.norm(centroid)
    assert offset_from_origin == pytest.approx(0.55, abs=0.05)


def test_board_trajectory_explicit_center_zero_reproduces_pre_d27_stream():
    """`center=(0.0, 0.0)` reproduces the pre-D-27 algorithm's RNG stream
    exactly -- proving the RNG call order/count is unchanged by D-27.

    `_pre_d27_generate_board_trajectory` below is a FROZEN HISTORICAL
    REFERENCE that predates GEOM-01 -- it is deliberately exempt from the
    D-19.3-01 clearance rule (it has no `board` parameter and does not
    re-centre). Because D-19.3-19's re-centring legitimately moves `tvec`
    (subtracting `R @ centroid_local`), this test now compares the SAMPLED
    rotation sequence (`rvec`) only, not `tvec` -- `rvec` stays bit-identical
    because the RNG call order/count is unchanged by either D-27 or
    D-19.3-19; `tvec` does not, by design.
    """
    _, extrinsics, water_zs = generate_camera_array(
        n_cameras=6, layout="grid", spacing=0.1, seed=3
    )
    camera_positions = {cam: ext.C for cam, ext in extrinsics.items()}

    def _pre_d27_generate_board_trajectory(
        n_frames,
        camera_positions,
        water_zs,
        depth_range=(0.3, 0.6),
        xy_extent=0.15,
        rotation_range_deg=15.0,
        seed=42,
    ):
        """Reimplementation of generate_board_trajectory as it existed
        before D-27 (sampling about the origin) and before GEOM-01 (no
        board-required clearance enforcement, no re-centring). Frozen
        historical reference, used ONLY to prove the RNG stream (rvec) is
        unchanged by either later change."""
        from aquacal.config.schema import BoardPose

        rng = np.random.default_rng(seed)
        poses = []
        for frame_idx in range(n_frames):
            x = rng.uniform(-xy_extent, xy_extent)
            y = rng.uniform(-xy_extent, xy_extent)
            z = rng.uniform(depth_range[0], depth_range[1])
            tvec = np.array([x, y, z], dtype=np.float64)
            max_tilt = np.deg2rad(rotation_range_deg)
            rx = rng.uniform(-max_tilt, max_tilt)
            ry = rng.uniform(-max_tilt, max_tilt)
            rz = rng.uniform(-np.pi, np.pi)
            rvec = np.array([rx, ry, rz], dtype=np.float64)
            poses.append(BoardPose(frame_idx=frame_idx, rvec=rvec, tvec=tvec))
        return poses

    pre_d27_poses = _pre_d27_generate_board_trajectory(
        n_frames=20,
        camera_positions=camera_positions,
        water_zs=water_zs,
        seed=99,
    )
    post_d27_poses = generate_board_trajectory(
        n_frames=20,
        camera_positions=camera_positions,
        water_zs=water_zs,
        board=_DEFAULT_BOARD,
        seed=99,
        center=(0.0, 0.0),
    )

    assert len(pre_d27_poses) == len(post_d27_poses)
    for pre, post in zip(pre_d27_poses, post_d27_poses):
        # tvec is NOT compared: D-19.3-19's re-centring legitimately offsets
        # it by -(R @ centroid_local), which the frozen pre-D-27/pre-GEOM-01
        # reference does not apply.
        np.testing.assert_array_equal(pre.rvec, post.rvec)


# ----------------------------------------------------------------------
# Frozen-anchor exact-equality tests (D-27 containment gate, items 1 & 2).
#
# REGENERATED under plan 19.3-01 (D-19.3-01/D-19.3-19, GEOM-01): the prior
# anchor's depth_range, (1.1, 2.0), is now illegal (below this generator's
# own derived clearance floor, ~1.220 m), and its tvec values were
# corner-pivoted rather than centre-pivoted. This is the established
# "anchors are regenerated deliberately and the regeneration is recorded"
# pattern (precedent: the `ideal` anchor regenerated under D-27, `4ed8259`).
# See the plan's SUMMARY for the old/new values and reason.
#
# The regenerated anchors below were captured by calling
# generate_real_rig_trajectory(n_frames=100, board=<default 12x9 board>,
# depth_range=None, seed=42) and create_scenario("realistic", seed=42)
# directly and recording every rvec/tvec component with repr() (Python's
# shortest round-trip float representation). rvec is bit-identical to the
# pre-fix anchor (the RNG stream is unaffected by either D-27 or D-19.3-19);
# tvec is NOT (D-19.3-19's re-centring is the point of this regeneration).
# generate_real_rig_trajectory and create_scenario("realistic") ->
# generate_real_rig_array are still NOT modified by D-27 (they never call
# generate_board_trajectory) -- a mismatch here means either D-27 leaked
# into the realistic path, or this plan's own re-centring/floor logic
# regressed. Do not regenerate again without recording why.
# ----------------------------------------------------------------------

_ANCHOR_RIG_TRAJECTORY_CSV = """\
0.13778887781030985,-0.28331765834144146,2.988423371570267,0.36973622244319254,0.6307090238048252,1.8966756493207828
-0.034637149560451996,-0.09019999508893539,2.6814435075521947,0.3872245378405243,1.0054416324546758,1.3384269622021736
-0.19042329507215702,0.038107370197046686,-2.740617007691522,0.05559574822911384,1.311150997020011,1.539410086061846
-0.10156003329139843,0.3286092123329461,2.4700528534335957,0.4845503239104345,0.7188600272474559,1.8130951851361716
-0.3184850528884824,-0.2413514648865306,1.1501304935075938,0.11153321461753962,-0.23160852979846547,1.6546242701392424
-0.09043618574771511,-0.02125405325342733,-1.9511089940600619,-0.0809846070732195,1.5606598323112393,1.4587521419977696
0.11855253292695794,-0.04387623776953359,2.0902787534896143,-0.5276907561739278,0.3619498837624756,1.3633305288999265
0.2127656592417702,-0.07855491062418202,-1.3299737473283346,-0.33183754556977335,0.5312440603995285,1.8469971367501836
-0.34392601649586474,0.20031100366589832,1.0357884800150252,-0.05193190473387521,-0.29306051329785543,1.512202942700293
0.04799040804546384,-0.25146913432958706,-2.421978978318367,0.0405327582039816,1.2935265750161964,1.5281961412220109
0.18500410303730558,0.09405112987062553,0.3366493029818076,-0.3190821817061945,0.21386876217548662,1.6385394089266978
-0.044179596686131695,-0.19925748779824318,-0.5747314817771554,-0.617551413642684,0.2599974245515265,1.1824180883607724
-0.15262283528446413,-0.14409874094561378,1.0173514663217542,0.17452447715912806,-0.18721851414950286,1.2926522731728616
-0.06535429963985728,0.2192275852320567,-2.092470856528834,-0.286513367665845,1.3090778076524292,1.7899065098756537
-0.026614714083719238,-0.2364769090114615,0.006564515578761032,-1.299140171479669,-0.23674488657041348,1.7192211052794064
-0.08306285378409145,-0.13857070279098152,0.8185896748658563,-0.8777300003751299,0.46221641400960944,1.5680940623566098
0.32246540214645275,0.2852431325168137,1.2547969288986494,-0.43501742685872646,-0.37265771112418766,1.241473123017885
0.1514179166439114,-0.03535234063419912,-1.4310484722006673,-0.9164533926903617,1.475587808201661,1.821293737800004
-0.20778957035521992,-0.1354678320102385,0.4977512316168209,-1.0698126089591242,0.7875512290113835,1.6010154454855703
0.15321404670012523,-0.04740800163781078,0.7999050373756575,-0.8507506691791323,0.6919371584930304,1.7568934691269713
-0.05877752151721172,-0.32001367642337036,-0.037756796231025014,-0.5165717694722606,0.5586223882034718,1.2031977088432644
0.06118745424011568,-0.22996949113007564,2.6711084815715385,-0.21603945103323785,0.1060650785214791,1.3092609085517544
-0.3331457451321311,0.32013472345671995,-0.11119078498794632,-0.5211005594389352,0.18614221097156486,1.8394398706896757
-0.006487741836801231,0.3056605276659263,0.45068064480196446,-0.11054133545911443,-0.351697939085177,1.6750511708471292
0.014432059497029914,-0.04264784611648753,-3.0057999508281092,-0.10820372352140945,0.472306801843817,1.475646103004771
0.037724344793466924,-0.27326568357460446,1.08221642189499,0.16891006907617745,0.7456052566434659,1.2805170280357216
0.18755133044751876,-0.27384848055311933,2.6138795129812875,-0.28280366946700763,0.8122762934852564,1.765871774335701
-0.09011324550220245,0.23023667427867872,1.9368011201909,-0.4119367641757606,-0.29732652929889225,1.6802758646234526
0.010511859239668131,-0.17036850637605994,2.739742552621779,-0.23824619397524616,1.2607019894119342,1.4630620364391598
0.34374298996554403,0.27344231605434915,1.56205025509892,-0.6141635549276971,-0.38219373107839755,1.465926623570821
-0.1285057641128196,0.18990050186777158,1.0157476734757687,0.23245442184865406,0.7420764087554842,1.6942530817160204
-0.1658338440253862,0.30495310771296297,-1.6275298772514581,-0.6924687646944093,0.29222968970613483,1.8875500371333693
-0.2239129615255716,0.06938227727447288,2.3534427116171566,-0.5112952136307416,0.955281151951802,1.3985919140693208
0.3293969853072584,0.0005174455840490366,-2.237457979819937,-0.7444121753600447,0.6469949545457602,1.873968959636716
0.12402915197081332,-0.2640107167301019,0.0397721333542127,-1.2982281809679197,-0.04359671246397262,1.2204804833964975
0.21231897271792738,0.1503825457626371,1.5015807820530807,0.11630770242573463,0.35257849361532356,1.3184081483090762
-0.0715039097437698,-0.13896402835298607,-0.0717285585146743,-1.1688894156984888,-0.1657443815759604,1.9152315310097445
0.29657223126881854,-0.3317106513964122,0.3468195285329818,-0.2992612084786953,0.9149191186794272,1.2876709328596785
-0.05646885782589106,0.32549127779069814,0.6034531593462247,-0.26583967288776844,-0.33910967936261777,1.4166492636378172
0.1988023911514582,-0.3366134260642497,-2.455820696744471,0.3785028881371675,1.3220263626409887,1.5423676434283748
0.021481226617767135,0.07401300521676601,2.3105719912430267,0.47841527918858995,0.8855958616715089,1.3920984728199102
-0.05174406509964091,0.10606786529209106,2.3090117379523516,0.1617203383073304,0.3481635768002014,1.5213432820557145
0.17175036788688708,0.2210066892285693,-2.480110969082276,-0.29538256837787114,0.537840929200891,1.4829299084657712
0.22665836347140428,-0.1324113766757423,-2.2376186382299834,-0.9224943866453656,1.0475931578725253,1.3338364389604407
-0.2418234695481199,-0.2684385758269333,-3.008715748068679,0.5175844027300383,0.3160039733552521,1.3576264991292013
0.06363038735874804,0.12616253995339666,-0.6683395507644048,-1.326212079064411,0.11412217121935081,1.300041473937422
0.24513611983726108,-0.3187145314135886,-2.0012045131364506,-0.6429277503862577,0.9144292972211694,1.843032091121478
-0.0584598551645068,-0.3146799878825193,-0.7941057882660534,-1.0545759153200307,0.2593256522886771,1.5623949742790697
-0.31278962418695805,0.29659557658766683,-2.518846418666709,-0.17408477746794082,0.3334803441555608,1.881465454757367
0.21085384148033598,0.1951121308734553,0.895248826254039,0.1154194163927295,0.7497366193751276,1.9530160924151185
0.009929436556259386,0.24963244913417276,-0.23373847952058036,-0.28042389041341714,-0.09754246204839553,1.7164904484152528
-0.25148909194178365,-0.015444576312084513,-0.5221994981150369,-0.8650857932538736,0.7171471525319415,1.4542638161086119
-0.1204308150118224,-0.08414994702745887,1.1670598590751782,-0.6402465181553648,0.006999462256135347,1.5345144521846459
-0.013327035158366418,-0.11982648387294983,0.22264335082287223,-0.8687444156971401,0.9072768449641389,1.9052839608627927
0.02284445824374809,0.09279401058660647,-1.33105753237724,-0.12614937597189202,1.0043195935756637,1.8795228445659835
0.25182941668052966,-0.256840671913333,0.7186691052120038,-0.08675903864497064,-0.2028907162016927,1.638555200837846
0.30434340986744973,-0.25313701849847936,2.8832296188508897,-0.5698643427543644,1.0045203059549486,1.2503549692739837
0.2060290244699105,0.31138563196647956,-1.5495380876635259,-0.1264917133439995,0.9616275542586966,1.9415367063490543
-0.22948196094070578,0.04534408085510849,0.45509434156894946,-0.390674791126854,-0.3293658316224614,1.7734063364170416
0.2089122228933042,-0.005478088956118843,0.6257640484663267,-0.5087803432386561,0.24151076354296225,1.755295923217708
-0.28783340873831265,0.1102093636788608,-0.5113991286002681,-0.09431543661665498,-0.008191821329353456,1.3847556284101432
0.2781123152504292,0.1832820143485147,-1.4417714877842795,-0.20106896161644416,1.052442627287228,1.5517113775832985
-0.24589359317636084,0.3044744077711086,-0.3901604411079638,-0.8644806732832885,0.22411386536827282,1.4778848971898226
0.304483150797436,0.19568735867910908,-0.12962485157339865,-0.827924287565438,0.7020264386526596,1.6552386629135343
0.3149932953793359,-0.26635219977823743,2.2024680627631277,-0.16893655354257459,1.1338689568232445,1.7016779599186076
0.12991977188334264,-0.34047695537507533,-0.28702871095795546,-0.47245510320301676,-0.08950196864275878,1.5499133492465642
-0.04027233658209356,-0.13828076709369672,2.629147969811706,0.47924379240254666,0.2995534226229454,1.6014200689148794
0.2647315579125074,-0.15086036980201722,2.116783639364664,0.38613852690359585,-0.13016519119115696,1.9239557351129588
0.10480703244434886,-0.28592631184804995,2.4946344184068474,-0.524924569244658,1.2412176395815078,1.7348547531391822
0.19322047316174434,-0.21069319614942542,2.5801160752750523,-0.6353708815194253,0.21270215747143648,1.3020849872672722
-0.31300182093393547,0.07394972442851,1.8942660843737729,0.16732612407969716,-0.3029173423130185,1.322418577571227
0.21011240702150308,0.29865755125967136,1.709707495212803,-0.46109186919717027,0.7730143849970794,1.2086054867649088
-0.20819536225201554,-0.2618526696953069,0.02846905100754782,-0.35212554573224414,0.8012831649662295,1.2199342514016145
-0.24070674000006165,0.16379642195571537,-1.9286771944862526,-0.08166943302406611,1.0875968548790418,1.905251376958126
0.0778721273538836,-0.3110174527999806,0.7307908109418664,-0.7311370454309357,0.49437982447118833,1.9007318568260134
-0.22819981252047522,-0.2850325086039398,-1.9884193665097447,-1.0461773304167987,1.4320431832736196,1.6674531851260703
0.0952309878787011,0.050553915540744676,-2.2297123698511214,0.3496156349104827,0.85679124425617,1.8584367297911852
0.13946991997443814,0.10418439648681943,2.7683363214243446,0.6374959743450017,0.35851494534325523,1.6272912272378537
-0.018033628820066094,-0.2658363160695363,-2.2990513710652554,-0.7829727382743575,0.9180960880595727,1.4676256193962087
0.07748392498004958,0.09398885472010948,-0.554108478826886,-1.0155355450317387,0.25497731139276736,1.5773344968229865
-0.12772953975849977,-0.32389133696432565,-0.5127076436201179,-0.8193947164857172,0.11121181570252806,1.587044542417509
0.04591744871323605,0.14102412626343502,0.9295877295861636,-0.3861160652382159,-0.20011388836724608,1.6763548880225732
0.03430925210710034,-0.04787913204284139,0.7917597687700977,-0.18756442690655412,-0.06786056310722921,1.814988011000883
0.26976010450157534,0.2939533772808182,0.022826342132531874,-0.8257618951834258,0.34702452178488424,1.824041312052075
0.23553732244311937,-0.004089902280665525,-2.413643385508479,-0.2275440769371718,1.3243579374760313,1.5026119167029164
-0.1531621112275826,-0.11579907693590671,-2.0546364973382865,-0.9851242297657664,1.3884821841461623,1.2134271108991075
0.2284101393164451,0.24891747811417603,-0.8026042064850993,-0.9547960893873384,0.951861354523277,1.3015749546335857
-0.09430407619528386,0.3200439437577069,3.113095094366992,-0.5219825309325998,0.8954410176754297,1.2900704123816007
0.1434006952900343,-0.07830126811399168,0.8852293987803508,0.014515716749059458,-0.0753181265506655,1.699108147841748
-0.23474587384917495,-0.23324100655419688,2.113062177126709,-0.698124003833531,-0.0035548692834844187,1.7068125897279645
0.3423090974540752,-0.2502132718863811,-0.3251824023823513,0.0131401966080954,0.5467349440943812,1.7425725550873097
-0.04623096028375828,-0.021413839602335893,-2.194886438337388,-0.4855212416894544,0.3280351596101327,1.797408269103663
-0.18650428867647817,-0.14516997339253768,-0.0615906575566032,-1.0986256174726252,0.9282285578260031,1.24897473406781
-0.17895387626989742,0.2398699434286184,0.8644953012801873,-0.24497068499873237,0.18823498512919756,1.3829253752439878
-0.30849847722389795,-0.09312491509915166,0.24835820046667179,-0.3730298946551517,0.5178090605548866,1.8649162457501418
0.18753743591047117,0.24575319150744318,0.030105774978861355,-0.8556188630496684,0.8102831110709035,1.629206130378862
-0.11128861899650244,-0.000825918752528465,0.1973613913231782,-0.019726410990221988,0.4086240025848712,1.9096154974951012
0.09133813448501527,-0.22514287809935302,-1.0124999026725234,-1.219977798673288,0.5516124829473192,1.854554444118101
-0.036158106012888935,-0.13436586723478885,0.6187504430878801,-0.8927012480518481,-0.46037903106630834,1.9246243782627546
0.09338891918817116,0.336364005612333,0.7562297929292088,-1.0948501765850516,-0.1192275704963523,1.8057434055575752"""

_ANCHOR_REALISTIC_BOARD_POSES_CSV = """\
0.13778887781030985,-0.28331765834144146,2.988423371570267,0.36973622244319254,0.6307090238048252,1.8966756493207828
-0.034637149560451996,-0.09019999508893539,2.6814435075521947,0.3872245378405243,1.0054416324546758,1.3384269622021736
-0.19042329507215702,0.038107370197046686,-2.740617007691522,0.05559574822911384,1.311150997020011,1.539410086061846
-0.10156003329139843,0.3286092123329461,2.4700528534335957,0.4845503239104345,0.7188600272474559,1.8130951851361716
-0.3184850528884824,-0.2413514648865306,1.1501304935075938,0.11153321461753962,-0.23160852979846547,1.6546242701392424
-0.09043618574771511,-0.02125405325342733,-1.9511089940600619,-0.0809846070732195,1.5606598323112393,1.4587521419977696
0.11855253292695794,-0.04387623776953359,2.0902787534896143,-0.5276907561739278,0.3619498837624756,1.3633305288999265
0.2127656592417702,-0.07855491062418202,-1.3299737473283346,-0.33183754556977335,0.5312440603995285,1.8469971367501836
-0.34392601649586474,0.20031100366589832,1.0357884800150252,-0.05193190473387521,-0.29306051329785543,1.512202942700293
0.04799040804546384,-0.25146913432958706,-2.421978978318367,0.0405327582039816,1.2935265750161964,1.5281961412220109
0.18500410303730558,0.09405112987062553,0.3366493029818076,-0.3190821817061945,0.21386876217548662,1.6385394089266978
-0.044179596686131695,-0.19925748779824318,-0.5747314817771554,-0.617551413642684,0.2599974245515265,1.1824180883607724
-0.15262283528446413,-0.14409874094561378,1.0173514663217542,0.17452447715912806,-0.18721851414950286,1.2926522731728616
-0.06535429963985728,0.2192275852320567,-2.092470856528834,-0.286513367665845,1.3090778076524292,1.7899065098756537
-0.026614714083719238,-0.2364769090114615,0.006564515578761032,-1.299140171479669,-0.23674488657041348,1.7192211052794064
-0.08306285378409145,-0.13857070279098152,0.8185896748658563,-0.8777300003751299,0.46221641400960944,1.5680940623566098
0.32246540214645275,0.2852431325168137,1.2547969288986494,-0.43501742685872646,-0.37265771112418766,1.241473123017885
0.1514179166439114,-0.03535234063419912,-1.4310484722006673,-0.9164533926903617,1.475587808201661,1.821293737800004
-0.20778957035521992,-0.1354678320102385,0.4977512316168209,-1.0698126089591242,0.7875512290113835,1.6010154454855703
0.15321404670012523,-0.04740800163781078,0.7999050373756575,-0.8507506691791323,0.6919371584930304,1.7568934691269713
-0.05877752151721172,-0.32001367642337036,-0.037756796231025014,-0.5165717694722606,0.5586223882034718,1.2031977088432644
0.06118745424011568,-0.22996949113007564,2.6711084815715385,-0.21603945103323785,0.1060650785214791,1.3092609085517544
-0.3331457451321311,0.32013472345671995,-0.11119078498794632,-0.5211005594389352,0.18614221097156486,1.8394398706896757
-0.006487741836801231,0.3056605276659263,0.45068064480196446,-0.11054133545911443,-0.351697939085177,1.6750511708471292
0.014432059497029914,-0.04264784611648753,-3.0057999508281092,-0.10820372352140945,0.472306801843817,1.475646103004771
0.037724344793466924,-0.27326568357460446,1.08221642189499,0.16891006907617745,0.7456052566434659,1.2805170280357216
0.18755133044751876,-0.27384848055311933,2.6138795129812875,-0.28280366946700763,0.8122762934852564,1.765871774335701
-0.09011324550220245,0.23023667427867872,1.9368011201909,-0.4119367641757606,-0.29732652929889225,1.6802758646234526
0.010511859239668131,-0.17036850637605994,2.739742552621779,-0.23824619397524616,1.2607019894119342,1.4630620364391598
0.34374298996554403,0.27344231605434915,1.56205025509892,-0.6141635549276971,-0.38219373107839755,1.465926623570821"""

_ANCHOR_REALISTIC_EXTRINSICS_CSV = """\
cam0:1.0,0.0,0.0,0.0,1.0,0.0,0.0,0.0,1.0,-0.0,-0.0,0.0,1.031
cam1:1.0,0.0,0.0,0.0,1.0,0.0,0.0,0.0,1.0,-0.208,-0.2419,0.0,1.031
cam10:1.0,0.0,0.0,0.0,1.0,0.0,0.0,0.0,1.0,0.6639,-0.0038,0.0,1.031
cam11:1.0,0.0,0.0,0.0,1.0,0.0,0.0,0.0,1.0,0.3364,0.0573,0.0,1.031
cam2:1.0,0.0,0.0,0.0,1.0,0.0,0.0,0.0,1.0,-0.3353,-0.573,0.0,1.031
cam3:1.0,0.0,0.0,0.0,1.0,0.0,0.0,0.0,1.0,-0.2227,-0.8684,0.0,1.031
cam4:1.0,0.0,0.0,0.0,1.0,0.0,0.0,0.0,1.0,-0.0039,-1.149,0.0,1.031
cam5:1.0,0.0,0.0,0.0,1.0,0.0,0.0,0.0,1.0,0.3363,-1.193,0.0,1.031
cam6:1.0,0.0,0.0,0.0,1.0,0.0,0.0,0.0,1.0,0.6801,-1.1523,0.0,1.031
cam7:1.0,0.0,0.0,0.0,1.0,0.0,0.0,0.0,1.0,0.8868,-0.8828,0.0,1.031
cam8:1.0,0.0,0.0,0.0,1.0,0.0,0.0,0.0,1.0,1.0023,-0.5654,0.0,1.031
cam9:1.0,0.0,0.0,0.0,1.0,0.0,0.0,0.0,1.0,0.8949,-0.2677,0.0,1.031"""


def _parse_pose_csv(csv_text: str) -> np.ndarray:
    """Parse a "rx,ry,rz,tx,ty,tz" per line anchor into an (n, 6) array."""
    rows = [
        [float(v) for v in line.split(",")] for line in csv_text.strip().splitlines()
    ]
    return np.array(rows, dtype=np.float64)


def test_generate_real_rig_trajectory_matches_frozen_anchor():
    """generate_real_rig_trajectory is bit-identical to the GEOM-01 anchor
    (D-27 containment gate item 1).

    REGENERATED under D-19.3-19/D-19.3-01 (see the plan's SUMMARY for the
    before/after values and reason): the pre-fix anchor's depth_range,
    (1.1, 2.0), is now illegal -- it sits below this generator's own derived
    clearance floor (~1.220 m) -- and its tvec values were corner-pivoted,
    not centre-pivoted. rvec is unchanged (the RNG stream is bit-identical
    across both D-27 and D-19.3-19); tvec is deliberately different, offset
    by the corner-cloud centroid re-centring.
    """
    poses = generate_real_rig_trajectory(
        n_frames=100, board=_DEFAULT_BOARD, depth_range=None, seed=42
    )
    actual = np.array(
        [np.concatenate([p.rvec, p.tvec]) for p in poses], dtype=np.float64
    )
    expected = _parse_pose_csv(_ANCHOR_RIG_TRAJECTORY_CSV)

    assert actual.shape == expected.shape == (100, 6)
    np.testing.assert_array_equal(actual, expected)


def test_create_scenario_realistic_matches_frozen_anchor():
    """create_scenario("realistic") is bit-identical on board poses,
    extrinsics, and water_zs to the GEOM-01 anchor (D-27 containment gate
    item 2). REGENERATED under plan 19.3-01 -- see the frozen-anchor block
    comment above and the plan's SUMMARY for the old/new tvec values."""
    scenario = create_scenario("realistic", seed=42)

    actual_poses = np.array(
        [np.concatenate([p.rvec, p.tvec]) for p in scenario.board_poses],
        dtype=np.float64,
    )
    expected_poses = _parse_pose_csv(_ANCHOR_REALISTIC_BOARD_POSES_CSV)
    assert actual_poses.shape == expected_poses.shape == (30, 6)
    np.testing.assert_array_equal(actual_poses, expected_poses)

    expected_ext_lines = _ANCHOR_REALISTIC_EXTRINSICS_CSV.strip().splitlines()
    assert len(expected_ext_lines) == len(scenario.extrinsics) == 12
    for line in expected_ext_lines:
        cam_name, values_str = line.split(":", 1)
        values = [float(v) for v in values_str.split(",")]
        expected_R = np.array(values[:9], dtype=np.float64).reshape(3, 3)
        expected_t = np.array(values[9:12], dtype=np.float64)
        expected_water_z = values[12]

        ext = scenario.extrinsics[cam_name]
        np.testing.assert_array_equal(ext.R, expected_R)
        np.testing.assert_array_equal(ext.t, expected_t)
        assert scenario.water_zs[cam_name] == expected_water_z


# ----------------------------------------------------------------------
# Source-scanning grep-gate: no realistic-path caller passes `center`
# (D-27 containment gate item 4).
# ----------------------------------------------------------------------

_REPO_ROOT = Path(__file__).resolve().parents[2]


def _extract_call_args(source: str, func_name: str) -> list[str]:
    """Return the raw argument text of every `func_name(...)` call in
    `source`, matching parentheses so a call spanning multiple lines is
    captured whole."""
    calls = []
    marker = f"{func_name}("
    start = 0
    while True:
        idx = source.find(marker, start)
        if idx == -1:
            break
        depth = 0
        i = idx + len(marker) - 1
        arg_start = i + 1
        while i < len(source):
            if source[i] == "(":
                depth += 1
            elif source[i] == ")":
                depth -= 1
                if depth == 0:
                    calls.append(source[arg_start:i])
                    break
            i += 1
        start = idx + len(marker)
    return calls


def test_realistic_scenario_never_passes_center():
    """create_scenario("realistic")'s branch never passes `center` to
    generate_real_rig_trajectory -- that function has no `center` parameter
    at all, and D-27's centroid default is scoped to generate_board_
    trajectory (the grid family) only (D-27 containment gate item 4)."""
    import inspect

    from aquacal.datasets import synthetic as synthetic_module

    source = inspect.getsource(synthetic_module.create_scenario)
    realistic_branch = source.split('elif name == "realistic":')[1].split(
        "valid_names"
    )[0]

    assert "center" not in realistic_branch, (
        "create_scenario('realistic') must never pass `center` -- "
        "generate_real_rig_trajectory has no such parameter, and routing "
        "the realistic path through a center-aware call would silently "
        "reintroduce the non-determinism the D-27 containment audit "
        "proved absent from this path."
    )


def test_e3_e5_never_pass_center_to_real_rig_trajectory():
    """Neither experiments/e3_derived_quantities.py nor experiments/
    e5_index_sensitivity.py -- both structurally-immune callers of
    generate_real_rig_trajectory per the D-27 containment audit -- ever
    pass a `center` keyword (D-27 containment gate item 4)."""
    for rel_path in (
        "experiments/e3_derived_quantities.py",
        "experiments/e5_index_sensitivity.py",
    ):
        source = (_REPO_ROOT / rel_path).read_text()
        calls = _extract_call_args(source, "generate_real_rig_trajectory")
        assert calls, (
            f"expected at least one generate_real_rig_trajectory(...) call "
            f"in {rel_path}"
        )
        for call_args in calls:
            assert "center" not in call_args, (
                f"{rel_path} passes `center` to generate_real_rig_trajectory, "
                "which has no such parameter and is a structurally-immune "
                "path under the D-27 containment audit -- this would either "
                "raise a TypeError or (if the function is later given a "
                "`center` parameter) silently move a published number."
            )
