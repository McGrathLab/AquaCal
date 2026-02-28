"""Tests for aquacal.datasets synthetic data generation and loading."""

import numpy as np
import pytest

from aquacal.datasets import (
    SyntheticScenario,
    clear_cache,
    create_scenario,
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
