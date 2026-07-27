"""Tests for aquacal.datasets synthetic data generation and loading."""

import numpy as np
import pytest

import aquacal.datasets as datasets_module
from aquacal.core.board import BoardGeometry
from aquacal.datasets import (
    SyntheticScenario,
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
)
from aquacal.datasets._manifest import get_manifest

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
    assert datasets["real-rig"]["zenodo_record_id"] == 18645385


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
        depth_range=(0.25, 0.45),
        xy_extent=0.08,
        seed=1,
    )
    from aquacal.config.schema import BoardConfig

    board_config = BoardConfig(
        squares_x=12,
        squares_y=9,
        square_size=0.060,
        marker_size=0.045,
        dictionary="DICT_5X5_100",
    )
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
