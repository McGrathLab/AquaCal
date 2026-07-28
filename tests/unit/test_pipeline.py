"""Unit tests for calibration pipeline orchestration."""

import json
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import numpy as np
import pytest
import yaml

from aquacal.calibration.pipeline import (
    _build_calibration_result,
    _compute_config_hash,
    _dump_stage_calibration,
    _resolve_per_camera_water_z_seeds,
    _save_board_reference_images,
    build_interface_spread_report,
    load_config,
    run_calibration,
    run_calibration_from_config,
    split_detections,
)
from aquacal.config.schema import (
    BoardConfig,
    BoardPose,
    CalibrationConfig,
    CalibrationMetadata,
    CalibrationResult,
    CameraExtrinsics,
    CameraIntrinsics,
    Detection,
    DetectionResult,
    DiagnosticsData,
    FrameDetections,
    InterfaceParams,
)
from aquacal.core.board import BoardGeometry
from aquacal.datasets import create_scenario, generate_synthetic_detections
from aquacal.io.serialization import load_calibration

# --- Fixtures ---


@pytest.fixture
def sample_board_config():
    """Create a sample BoardConfig."""
    return BoardConfig(
        squares_x=7,
        squares_y=5,
        square_size=0.03,
        marker_size=0.022,
        dictionary="DICT_4X4_50",
    )


@pytest.fixture
def sample_intrinsics():
    """Create sample CameraIntrinsics."""
    return CameraIntrinsics(
        K=np.array([[1000, 0, 640], [0, 1000, 360], [0, 0, 1]], dtype=np.float64),
        dist_coeffs=np.zeros(5, dtype=np.float64),
        image_size=(1280, 720),
    )


@pytest.fixture
def sample_extrinsics():
    """Create sample CameraExtrinsics."""
    return CameraExtrinsics(
        R=np.eye(3, dtype=np.float64),
        t=np.zeros(3, dtype=np.float64),
    )


@pytest.fixture
def sample_detection_result():
    """Create a sample DetectionResult with 10 frames."""
    frames = {}
    for i in range(10):
        detections = {}
        for cam in ["cam0", "cam1"]:
            detections[cam] = Detection(
                corner_ids=np.array([0, 1, 2, 3], dtype=np.int32),
                corners_2d=np.array(
                    [[100, 100], [200, 100], [100, 200], [200, 200]], dtype=np.float64
                ),
            )
        frames[i] = FrameDetections(frame_idx=i, detections=detections)

    return DetectionResult(
        frames=frames,
        camera_names=["cam0", "cam1"],
        total_frames=10,
    )


@pytest.fixture
def valid_config_yaml():
    """Generate valid YAML config content."""
    return {
        "board": {
            "squares_x": 7,
            "squares_y": 5,
            "square_size": 0.03,
            "marker_size": 0.022,
            "dictionary": "DICT_4X4_50",
        },
        "cameras": ["cam0", "cam1"],
        "paths": {
            "intrinsic_videos": {
                "cam0": "/path/to/cam0_inair.mp4",
                "cam1": "/path/to/cam1_inair.mp4",
            },
            "extrinsic_videos": {
                "cam0": "/path/to/cam0_uw.mp4",
                "cam1": "/path/to/cam1_uw.mp4",
            },
            "output_dir": "/path/to/output",
        },
        "interface": {
            "n_air": 1.0,
            "n_water": 1.333,
            "normal_fixed": False,
        },
        "optimization": {
            "robust_loss": "huber",
            "loss_scale": 1.0,
        },
        "detection": {
            "min_corners": 8,
            "min_cameras": 2,
        },
        "validation": {
            "holdout_fraction": 0.2,
            "save_detailed_residuals": True,
        },
    }


# --- Test load_config ---


class TestLoadConfig:
    """Tests for load_config function."""

    def test_load_config_valid(self, valid_config_yaml):
        """Test loading a valid config file."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(valid_config_yaml, f)
            f.flush()
            config = load_config(f.name)

        assert config.board.squares_x == 7
        assert config.board.squares_y == 5
        assert config.board.square_size == 0.03
        assert config.board.marker_size == 0.022
        assert config.board.dictionary == "DICT_4X4_50"
        assert config.camera_names == ["cam0", "cam1"]
        assert config.n_air == 1.0
        assert config.n_water == 1.333
        assert config.robust_loss == "huber"
        assert config.loss_scale == 1.0
        assert config.min_corners_per_frame == 8
        assert config.min_cameras_per_frame == 2
        assert config.holdout_fraction == 0.2
        assert config.save_detailed_residuals is True
        assert config.save_stage_calibrations is True
        assert config.save_optimization_trace is False
        assert config.save_conditioning is False
        assert config.seed == 42

    def test_load_config_missing_file(self):
        """Test that missing file raises FileNotFoundError."""
        with pytest.raises(FileNotFoundError, match="Config file not found"):
            load_config("/nonexistent/path/config.yaml")

    def test_load_config_missing_board_section(self, valid_config_yaml):
        """Test that missing 'board' section raises ValueError."""
        del valid_config_yaml["board"]
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(valid_config_yaml, f)
            f.flush()
            with pytest.raises(
                ValueError, match="Missing required config section: board"
            ):
                load_config(f.name)

    def test_load_config_missing_cameras_section(self, valid_config_yaml):
        """Test that missing 'cameras' section raises ValueError."""
        del valid_config_yaml["cameras"]
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(valid_config_yaml, f)
            f.flush()
            with pytest.raises(
                ValueError, match="Missing required config section: cameras"
            ):
                load_config(f.name)

    def test_load_config_missing_paths_section(self, valid_config_yaml):
        """Test that missing 'paths' section raises ValueError."""
        del valid_config_yaml["paths"]
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(valid_config_yaml, f)
            f.flush()
            with pytest.raises(
                ValueError, match="Missing required config section: paths"
            ):
                load_config(f.name)

    def test_load_config_defaults(self):
        """Test that defaults are applied for optional sections."""
        minimal_config = {
            "board": {
                "squares_x": 7,
                "squares_y": 5,
                "square_size": 0.03,
                "marker_size": 0.022,
            },
            "cameras": ["cam0"],
            "paths": {
                "intrinsic_videos": {"cam0": "/path/cam0.mp4"},
                "extrinsic_videos": {"cam0": "/path/cam0_uw.mp4"},
                "output_dir": "/output",
            },
        }
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(minimal_config, f)
            f.flush()
            config = load_config(f.name)

        # Check defaults
        assert config.board.dictionary == "DICT_4X4_50"
        assert config.intrinsic_board is None  # Should default to None
        assert config.n_air == 1.0
        assert config.n_water == 1.333
        assert config.robust_loss == "huber"
        assert config.loss_scale == 1.0
        assert config.min_corners_per_frame == 8
        assert config.min_cameras_per_frame == 2
        assert config.holdout_fraction == 0.2
        assert config.save_detailed_residuals is True
        assert config.initial_water_z is None  # Should default to None
        assert config.refine_intrinsics is False
        # Observability hooks and seed default (config omits both sections
        # entirely, exercising backward compatibility with existing configs)
        assert config.save_stage_calibrations is True
        assert config.save_optimization_trace is False
        assert config.save_conditioning is False
        assert config.seed == 42

    def test_load_config_with_internals_and_seed(self, valid_config_yaml):
        """Test that an `internals:` section and top-level `seed:` load correctly."""
        valid_config_yaml["internals"] = {
            "save_stage_calibrations": False,
            "save_optimization_trace": True,
            "save_conditioning": True,
        }
        valid_config_yaml["seed"] = 7
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(valid_config_yaml, f)
            f.flush()
            config = load_config(f.name)

        assert config.save_stage_calibrations is False
        assert config.save_optimization_trace is True
        assert config.save_conditioning is True
        assert config.seed == 7

    def test_load_config_with_intrinsic_board(self, valid_config_yaml):
        """Test loading config with separate intrinsic_board section."""
        # Add intrinsic_board to the config
        valid_config_yaml["intrinsic_board"] = {
            "squares_x": 12,
            "squares_y": 9,
            "square_size": 0.025,
            "marker_size": 0.018,
            "dictionary": "DICT_4X4_100",
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(valid_config_yaml, f)
            f.flush()
            config = load_config(f.name)

        # Check extrinsic board (main board)
        assert config.board.squares_x == 7
        assert config.board.squares_y == 5
        assert config.board.square_size == 0.03
        assert config.board.marker_size == 0.022
        assert config.board.dictionary == "DICT_4X4_50"

        # Check intrinsic board
        assert config.intrinsic_board is not None
        assert config.intrinsic_board.squares_x == 12
        assert config.intrinsic_board.squares_y == 9
        assert config.intrinsic_board.square_size == 0.025
        assert config.intrinsic_board.marker_size == 0.018
        assert config.intrinsic_board.dictionary == "DICT_4X4_100"

    def test_load_config_with_refine_intrinsics(self, valid_config_yaml):
        """Test loading config with refine_intrinsics: true."""
        valid_config_yaml["optimization"]["refine_intrinsics"] = True

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(valid_config_yaml, f)
            f.flush()
            config = load_config(f.name)

        assert config.refine_intrinsics is True

    def test_load_config_without_intrinsic_board(self, valid_config_yaml):
        """Test that intrinsic_board is None when section is absent."""
        # Make sure intrinsic_board is not in the config
        if "intrinsic_board" in valid_config_yaml:
            del valid_config_yaml["intrinsic_board"]

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(valid_config_yaml, f)
            f.flush()
            config = load_config(f.name)

        # intrinsic_board should be None (backward compatible)
        assert config.intrinsic_board is None

    def test_load_config_without_initial_water_z(self, valid_config_yaml):
        """Test that initial_water_z is None when not provided."""
        # Ensure initial_water_z is not in config
        if "initial_water_z" in valid_config_yaml.get("interface", {}):
            del valid_config_yaml["interface"]["initial_water_z"]

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(valid_config_yaml, f)
            f.flush()
            config = load_config(f.name)

        # initial_water_z should be None (backward compatible)
        assert config.initial_water_z is None

    def test_load_config_with_per_camera_initial_water_z(self, valid_config_yaml):
        """Test loading config with per-camera initial_water_z."""
        valid_config_yaml["interface"]["initial_water_z"] = {
            "cam0": 0.25,
            "cam1": 0.28,
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(valid_config_yaml, f)
            f.flush()
            config = load_config(f.name)

        assert config.initial_water_z is not None
        assert config.initial_water_z == {"cam0": 0.25, "cam1": 0.28}

    def test_load_config_with_scalar_initial_water_z(self, valid_config_yaml):
        """Test loading config with scalar initial_water_z (expanded to all cameras)."""
        valid_config_yaml["interface"]["initial_water_z"] = 0.3

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(valid_config_yaml, f)
            f.flush()
            config = load_config(f.name)

        assert config.initial_water_z is not None
        assert config.initial_water_z == {"cam0": 0.3, "cam1": 0.3}

    def test_load_config_with_incomplete_initial_water_z_dict(self, valid_config_yaml):
        """Test that incomplete initial_water_z dict raises ValueError."""
        # Only provide value for cam0, not cam1
        valid_config_yaml["interface"]["initial_water_z"] = {"cam0": 0.25}

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(valid_config_yaml, f)
            f.flush()
            with pytest.raises(
                ValueError, match="initial_water_z dict must cover all cameras"
            ):
                load_config(f.name)

    def test_load_config_shared_interface_default_true(self, valid_config_yaml):
        """shared_interface defaults to True when omitted from the config."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(valid_config_yaml, f)
            f.flush()
            config = load_config(f.name)

        assert config.shared_interface is True

    def test_load_config_shared_interface_false(self, valid_config_yaml):
        """interface.shared_interface: false is parsed through to the config."""
        valid_config_yaml["interface"]["shared_interface"] = False

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(valid_config_yaml, f)
            f.flush()
            config = load_config(f.name)

        assert config.shared_interface is False

    def test_load_config_partial_water_z_accepted_in_per_camera_mode(
        self, valid_config_yaml
    ):
        """A partial initial_water_z dict loads without raising in per-camera mode.

        The missing-camera coverage gate is skipped when shared_interface is
        False, leaving the partial dict for the pipeline's per-camera seed
        resolver to fill later.
        """
        valid_config_yaml["interface"]["shared_interface"] = False
        valid_config_yaml["interface"]["initial_water_z"] = {"cam0": 0.25}

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(valid_config_yaml, f)
            f.flush()
            config = load_config(f.name)

        # Partial dict passed through unchanged (missing cam1 filled downstream).
        assert config.shared_interface is False
        assert config.initial_water_z == {"cam0": 0.25}

    def test_load_config_partial_water_z_still_raises_in_shared_mode(
        self, valid_config_yaml
    ):
        """The same partial dict still hard-fails when shared_interface is True."""
        valid_config_yaml["interface"]["shared_interface"] = True
        valid_config_yaml["interface"]["initial_water_z"] = {"cam0": 0.25}

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(valid_config_yaml, f)
            f.flush()
            with pytest.raises(
                ValueError, match="initial_water_z dict must cover all cameras"
            ):
                load_config(f.name)

    def test_load_config_with_negative_scalar_initial_water_z(self, valid_config_yaml):
        """Test that negative scalar initial_water_z raises ValueError."""
        valid_config_yaml["interface"]["initial_water_z"] = -0.15

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(valid_config_yaml, f)
            f.flush()
            with pytest.raises(ValueError, match="initial_water_z must be positive"):
                load_config(f.name)

    def test_load_config_with_negative_dict_initial_water_z(self, valid_config_yaml):
        """Test that negative value in initial_water_z dict raises ValueError."""
        valid_config_yaml["interface"]["initial_water_z"] = {
            "cam0": 0.25,
            "cam1": -0.15,
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(valid_config_yaml, f)
            f.flush()
            with pytest.raises(
                ValueError, match="initial_water_z\\['cam1'\\] must be positive"
            ):
                load_config(f.name)

    def test_load_config_with_extra_cameras_in_initial_water_z(
        self, valid_config_yaml, capsys
    ):
        """Test that extra cameras in initial_water_z dict produce a warning."""
        valid_config_yaml["interface"]["initial_water_z"] = {
            "cam0": 0.25,
            "cam1": 0.28,
            "cam2": 0.30,  # Extra camera not in cameras list
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(valid_config_yaml, f)
            f.flush()
            config = load_config(f.name)

        # Check warning was printed to stderr
        captured = capsys.readouterr()
        assert "cam2" in captured.err
        assert "not in cameras list" in captured.err

        # Config should still load successfully with all cameras
        assert config.initial_water_z is not None
        assert "cam0" in config.initial_water_z
        assert "cam1" in config.initial_water_z
        assert "cam2" in config.initial_water_z

    def test_load_config_with_invalid_type_initial_water_z(self, valid_config_yaml):
        """Test that invalid type for initial_water_z raises ValueError."""
        valid_config_yaml["interface"]["initial_water_z"] = "invalid"

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(valid_config_yaml, f)
            f.flush()
            with pytest.raises(
                ValueError, match="initial_water_z must be a number or dict"
            ):
                load_config(f.name)

    def test_load_config_with_frame_step(self, valid_config_yaml):
        """Test loading config with frame_step specified."""
        valid_config_yaml["detection"]["frame_step"] = 5

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(valid_config_yaml, f)
            f.flush()
            config = load_config(f.name)

        assert config.frame_step == 5

    def test_load_config_without_frame_step(self, valid_config_yaml):
        """Test loading config without frame_step defaults to 1."""
        # Make sure frame_step is not in the config
        if "frame_step" in valid_config_yaml.get("detection", {}):
            del valid_config_yaml["detection"]["frame_step"]

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(valid_config_yaml, f)
            f.flush()
            config = load_config(f.name)

        assert config.frame_step == 1

    def test_load_config_with_start_and_stop_frame(self, valid_config_yaml):
        """Test loading config with detection.start_frame and stop_frame."""
        valid_config_yaml["detection"]["start_frame"] = 600
        valid_config_yaml["detection"]["stop_frame"] = 2400

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(valid_config_yaml, f)
            f.flush()
            config = load_config(f.name)

        assert config.extrinsic_start_frame == 600
        assert config.extrinsic_stop_frame == 2400

    def test_load_config_start_and_stop_frame_defaults(self, valid_config_yaml):
        """Without start_frame/stop_frame, defaults are 0 and None."""
        valid_config_yaml["detection"].pop("start_frame", None)
        valid_config_yaml["detection"].pop("stop_frame", None)

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(valid_config_yaml, f)
            f.flush()
            config = load_config(f.name)

        assert config.extrinsic_start_frame == 0
        assert config.extrinsic_stop_frame is None

    def test_load_config_with_legacy_pattern_true(self, valid_config_yaml):
        """Test loading config with legacy_pattern: true."""
        valid_config_yaml["board"]["legacy_pattern"] = True

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(valid_config_yaml, f)
            f.flush()
            config = load_config(f.name)

        assert config.board.legacy_pattern is True

    def test_load_config_with_legacy_pattern_false(self, valid_config_yaml):
        """Test loading config with legacy_pattern: false."""
        valid_config_yaml["board"]["legacy_pattern"] = False

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(valid_config_yaml, f)
            f.flush()
            config = load_config(f.name)

        assert config.board.legacy_pattern is False

    def test_load_config_without_legacy_pattern_defaults_false(self, valid_config_yaml):
        """Test that legacy_pattern defaults to False when omitted."""
        # Ensure legacy_pattern is not in the config
        if "legacy_pattern" in valid_config_yaml["board"]:
            del valid_config_yaml["board"]["legacy_pattern"]

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(valid_config_yaml, f)
            f.flush()
            config = load_config(f.name)

        assert config.board.legacy_pattern is False

    def test_load_config_with_intrinsic_board_legacy_pattern(self, valid_config_yaml):
        """Test loading config with legacy_pattern in intrinsic_board section."""
        valid_config_yaml["intrinsic_board"] = {
            "squares_x": 12,
            "squares_y": 9,
            "square_size": 0.025,
            "marker_size": 0.018,
            "dictionary": "DICT_4X4_100",
            "legacy_pattern": True,
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(valid_config_yaml, f)
            f.flush()
            config = load_config(f.name)

        assert config.intrinsic_board.legacy_pattern is True

    def test_load_config_intrinsic_board_legacy_pattern_defaults_false(
        self, valid_config_yaml
    ):
        """Test that intrinsic_board legacy_pattern defaults to False when omitted."""
        valid_config_yaml["intrinsic_board"] = {
            "squares_x": 12,
            "squares_y": 9,
            "square_size": 0.025,
            "marker_size": 0.018,
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(valid_config_yaml, f)
            f.flush()
            config = load_config(f.name)

        assert config.intrinsic_board.legacy_pattern is False

    def test_load_config_fisheye_cameras_valid(self, valid_config_yaml):
        """Fisheye cameras load correctly when subset of auxiliary_cameras."""
        valid_config_yaml["auxiliary_cameras"] = ["aux_cam"]
        valid_config_yaml["fisheye_cameras"] = ["aux_cam"]
        valid_config_yaml["paths"]["intrinsic_videos"]["aux_cam"] = (
            "/path/to/aux_inair.mp4"
        )
        valid_config_yaml["paths"]["extrinsic_videos"]["aux_cam"] = (
            "/path/to/aux_uw.mp4"
        )

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(valid_config_yaml, f)
            f.flush()
            config = load_config(f.name)

        assert config.fisheye_cameras == ["aux_cam"]

    def test_load_config_fisheye_cameras_not_in_auxiliary_raises(
        self, valid_config_yaml
    ):
        """ValueError if fisheye_cameras entry is not in auxiliary_cameras."""
        valid_config_yaml["fisheye_cameras"] = [
            "cam0"
        ]  # cam0 is primary, not auxiliary

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(valid_config_yaml, f)
            f.flush()
            with pytest.raises(ValueError, match="subset of auxiliary_cameras"):
                load_config(f.name)

    def test_load_config_fisheye_rational_overlap_raises(self, valid_config_yaml):
        """ValueError if fisheye_cameras overlaps with rational_model_cameras."""
        valid_config_yaml["auxiliary_cameras"] = ["aux_cam"]
        valid_config_yaml["fisheye_cameras"] = ["aux_cam"]
        valid_config_yaml["rational_model_cameras"] = ["aux_cam"]
        valid_config_yaml["paths"]["intrinsic_videos"]["aux_cam"] = (
            "/path/to/aux_inair.mp4"
        )
        valid_config_yaml["paths"]["extrinsic_videos"]["aux_cam"] = (
            "/path/to/aux_uw.mp4"
        )

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(valid_config_yaml, f)
            f.flush()
            with pytest.raises(ValueError, match="disjoint"):
                load_config(f.name)

    def test_load_config_fisheye_cameras_defaults_empty(self, valid_config_yaml):
        """fisheye_cameras defaults to empty list when not in config."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(valid_config_yaml, f)
            f.flush()
            config = load_config(f.name)

        assert config.fisheye_cameras == []


# --- Test split_detections ---


class TestSplitDetections:
    """Tests for split_detections function."""

    def test_split_detections_reproducible(self, sample_detection_result):
        """Test that same seed produces same split."""
        cal1, val1 = split_detections(sample_detection_result, 0.2, seed=42)
        cal2, val2 = split_detections(sample_detection_result, 0.2, seed=42)

        assert set(cal1.frames.keys()) == set(cal2.frames.keys())
        assert set(val1.frames.keys()) == set(val2.frames.keys())

    def test_split_detections_different_seed(self, sample_detection_result):
        """Test that different seeds produce different splits."""
        cal1, val1 = split_detections(sample_detection_result, 0.3, seed=42)
        cal2, val2 = split_detections(sample_detection_result, 0.3, seed=123)

        # With 10 frames and 30% holdout, different seeds should give different results
        assert set(cal1.frames.keys()) != set(cal2.frames.keys())

    def test_split_detections_fraction(self, sample_detection_result):
        """Test that holdout fraction is approximately respected."""
        cal, val = split_detections(sample_detection_result, 0.2, seed=42)

        # With 10 frames and 0.2 holdout, expect ~2 in validation
        total = len(cal.frames) + len(val.frames)
        assert total == 10
        assert len(val.frames) == 2
        assert len(cal.frames) == 8

    def test_split_detections_preserves_frames(self, sample_detection_result):
        """Test that all frames are in exactly one of the two sets."""
        cal, val = split_detections(sample_detection_result, 0.3, seed=42)

        cal_indices = set(cal.frames.keys())
        val_indices = set(val.frames.keys())
        original_indices = set(sample_detection_result.frames.keys())

        # No overlap
        assert cal_indices.isdisjoint(val_indices)

        # Union equals original
        assert cal_indices.union(val_indices) == original_indices

    def test_split_detections_zero_holdout(self, sample_detection_result):
        """Test with zero holdout fraction."""
        cal, val = split_detections(sample_detection_result, 0.0, seed=42)

        assert len(cal.frames) == 10
        assert len(val.frames) == 0

    def test_split_detections_full_holdout(self, sample_detection_result):
        """Test with full holdout fraction."""
        cal, val = split_detections(sample_detection_result, 1.0, seed=42)

        assert len(cal.frames) == 0
        assert len(val.frames) == 10

    def test_split_detections_default_seed_is_42(self, sample_detection_result):
        """Omitting seed must reproduce the seed=42 split exactly (backward compat)."""
        cal_default, val_default = split_detections(sample_detection_result, 0.2)
        cal_42, val_42 = split_detections(sample_detection_result, 0.2, seed=42)

        assert set(cal_default.frames.keys()) == set(cal_42.frames.keys())
        assert set(val_default.frames.keys()) == set(val_42.frames.keys())

    def test_pipeline_passes_config_seed_to_split(self):
        """Wiring guard: the pipeline call site must thread config.seed through."""
        import inspect

        import aquacal.calibration.pipeline as pipeline_module

        source = inspect.getsource(pipeline_module)
        assert "seed=config.seed" in source


# --- Test _build_calibration_result ---


class TestBuildCalibrationResult:
    """Tests for _build_calibration_result function."""

    def test_build_calibration_result(
        self, sample_intrinsics, sample_extrinsics, sample_board_config
    ):
        """Test that components are assembled correctly."""
        intrinsics = {"cam0": sample_intrinsics, "cam1": sample_intrinsics}
        extrinsics = {"cam0": sample_extrinsics, "cam1": sample_extrinsics}
        water_zs = {"cam0": 0.15, "cam1": 0.16}
        interface_params = InterfaceParams(
            normal=np.array([0, 0, -1], dtype=np.float64),
            n_air=1.0,
            n_water=1.333,
        )
        diagnostics = DiagnosticsData(
            reprojection_error_rms=0.5,
            reprojection_error_per_camera={"cam0": 0.4, "cam1": 0.6},
            validation_3d_error_mean=0.001,
            validation_3d_error_std=0.0005,
        )
        metadata = CalibrationMetadata(
            calibration_date="2025-01-01T00:00:00",
            software_version="0.1.0",
            config_hash="abc123",
            num_frames_used=80,
            num_frames_holdout=20,
        )

        result = _build_calibration_result(
            intrinsics=intrinsics,
            extrinsics=extrinsics,
            water_z_values=water_zs,
            board_config=sample_board_config,
            interface_params=interface_params,
            diagnostics=diagnostics,
            metadata=metadata,
        )

        assert len(result.cameras) == 2
        assert "cam0" in result.cameras
        assert "cam1" in result.cameras

        # Check camera calibration assembly
        cam0 = result.cameras["cam0"]
        assert cam0.name == "cam0"
        assert cam0.water_z == 0.15
        assert np.allclose(cam0.intrinsics.K, sample_intrinsics.K)
        assert np.allclose(cam0.extrinsics.R, sample_extrinsics.R)

        # Check other fields
        assert result.board.squares_x == 7
        assert result.interface.n_water == 1.333
        assert result.diagnostics.reprojection_error_rms == 0.5
        assert result.metadata.num_frames_used == 80


# --- Test _dump_stage_calibration ---


class TestDumpStageCalibration:
    """Tests for _dump_stage_calibration function."""

    @pytest.fixture
    def scenario(self):
        """A tiny two-camera scenario with realistic intrinsics/extrinsics."""
        return create_scenario("minimal")

    @pytest.fixture
    def dump_config(self, tmp_path, scenario):
        """Minimal CalibrationConfig pointing at a tmp_path output_dir."""
        return CalibrationConfig(
            board=scenario.board_config,
            camera_names=list(scenario.intrinsics.keys()),
            intrinsic_video_paths={},
            extrinsic_video_paths={},
            output_dir=tmp_path,
        )

    def test_dump_stage_calibration_writes_loadable_json(self, dump_config, scenario):
        """The dumped calibration must round-trip through load_calibration."""
        interface_normal = np.array([0.0, 0.0, -1.0], dtype=np.float64)

        path = _dump_stage_calibration(
            "stage3",
            dump_config,
            scenario.intrinsics,
            scenario.extrinsics,
            scenario.water_zs,
            interface_normal,
        )

        loaded = load_calibration(path)

        assert set(loaded.cameras.keys()) == set(scenario.intrinsics.keys())
        for cam_name, water_z in scenario.water_zs.items():
            assert loaded.cameras[cam_name].water_z == pytest.approx(water_z)
        assert np.allclose(loaded.interface.normal, interface_normal)

    def test_dump_stage_calibration_path_layout(self, dump_config, scenario):
        """The returned path must be output_dir/internals/calibration_stage3.json."""
        interface_normal = np.array([0.0, 0.0, -1.0], dtype=np.float64)

        path = _dump_stage_calibration(
            "stage3",
            dump_config,
            scenario.intrinsics,
            scenario.extrinsics,
            scenario.water_zs,
            interface_normal,
        )

        assert path == dump_config.output_dir / "internals" / "calibration_stage3.json"

    def test_dump_stage_calibration_warns_on_overwrite(
        self, dump_config, scenario, caplog
    ):
        """Calling twice for the same stage should log a warning on the second call."""
        interface_normal = np.array([0.0, 0.0, -1.0], dtype=np.float64)

        _dump_stage_calibration(
            "stage3",
            dump_config,
            scenario.intrinsics,
            scenario.extrinsics,
            scenario.water_zs,
            interface_normal,
        )

        with caplog.at_level("WARNING"):
            _dump_stage_calibration(
                "stage3",
                dump_config,
                scenario.intrinsics,
                scenario.extrinsics,
                scenario.water_zs,
                interface_normal,
            )

        assert any(
            "calibration_stage3.json" in record.getMessage()
            for record in caplog.records
        )

    def test_dump_stage_calibration_respects_stage_name(self, dump_config, scenario):
        """Different stage names should produce correspondingly named files."""
        interface_normal = np.array([0.0, 0.0, -1.0], dtype=np.float64)

        rerun_path = _dump_stage_calibration(
            "stage3_rerun",
            dump_config,
            scenario.intrinsics,
            scenario.extrinsics,
            scenario.water_zs,
            interface_normal,
        )
        stage3_intrinsic_pass_path = _dump_stage_calibration(
            "stage3_intrinsic_pass",
            dump_config,
            scenario.intrinsics,
            scenario.extrinsics,
            scenario.water_zs,
            interface_normal,
        )

        assert rerun_path.name == "calibration_stage3_rerun.json"
        assert (
            stage3_intrinsic_pass_path.name == "calibration_stage3_intrinsic_pass.json"
        )


class TestStage3ObserverWiring:
    """Behavioral + source-guard tests for the per-stage trace wiring (HOOK-02)."""

    def test_run_stage3_accepts_observer(self, tmp_path):
        """optimize_interface, called the way the pipeline calls it, accepts an
        observer and produces a header-correct trace CSV."""
        from aquacal.calibration._observability import (
            TRACE_CSV_HEADER,
            OptimizerObserver,
        )
        from aquacal.calibration.interface_estimation import optimize_interface
        from aquacal.core.board import BoardGeometry
        from aquacal.datasets import create_scenario, generate_synthetic_detections

        scenario = create_scenario("minimal")
        board = BoardGeometry(scenario.board_config)
        reference_camera = sorted(scenario.intrinsics.keys())[0]
        detections = generate_synthetic_detections(
            scenario.intrinsics,
            scenario.extrinsics,
            scenario.water_zs,
            board,
            scenario.board_poses,
            noise_std=scenario.noise_std,
        )

        observer = OptimizerObserver(stage="stage3")
        optimize_interface(
            detections=detections,
            intrinsics=scenario.intrinsics,
            initial_extrinsics=scenario.extrinsics,
            board=board,
            reference_camera=reference_camera,
            initial_water_zs=scenario.water_zs,
            verbose=0,
            observer=observer,
        )

        assert len(observer.rows) > 0

        path = tmp_path / "trace_stage3.csv"
        observer.write_trace_csv(path)

        import csv

        with open(path, newline="") as f:
            reader = csv.DictReader(f)
            assert reader.fieldnames == TRACE_CSV_HEADER

    def test_trace_filenames_are_distinct_per_stage(self):
        """Guard the 'one file per stage' decision against a future merge."""
        source = Path("src/aquacal/calibration/pipeline.py").read_text()
        assert "trace_stage3.csv" in source
        assert "trace_stage3_rerun.csv" in source
        assert "trace_stage3_intrinsic_pass.csv" in source


class TestConditioningWiring:
    """Wiring + stage-selection tests for HOOK-03 conditioning diagnostics."""

    def test_conditioning_artifact_names(self):
        """Source-guard: pipeline.py must reference the conditioning artifact
        names and the writer function (full config pipeline needs videos, so
        this is a wiring guard rather than an end-to-end run)."""
        source = Path("src/aquacal/calibration/pipeline.py").read_text()
        assert "conditioning.json" in source
        assert "conditioning.npz" in source
        assert "save_conditioning_report" in source

    def test_conditioning_stage_selection_logic(self):
        """_select_conditioning_report picks the correct observer's report
        across all four refine/re-run combinations."""
        from aquacal.calibration._observability import OptimizerObserver
        from aquacal.calibration.pipeline import _select_conditioning_report

        def _observer_with_report(stage, marker):
            obs = OptimizerObserver(stage=stage)
            obs.conditioning_report = marker
            return obs

        stage3_obs = _observer_with_report("stage3", "stage3_report")
        rerun_obs = _observer_with_report("stage3_rerun", "rerun_report")
        stage3_intrinsic_pass_obs = _observer_with_report(
            "stage3_intrinsic_pass", "stage3_intrinsic_pass_report"
        )

        # refine_intrinsics=True: Stage 3's second pass always wins, regardless
        # of re-run.
        assert (
            _select_conditioning_report(
                stage3_intrinsic_pass_obs, rerun_obs, stage3_obs, True
            )
            == "stage3_intrinsic_pass_report"
        )
        assert (
            _select_conditioning_report(
                stage3_intrinsic_pass_obs, None, stage3_obs, True
            )
            == "stage3_intrinsic_pass_report"
        )

        # refine_intrinsics=False, re-run fired: re-run wins.
        assert (
            _select_conditioning_report(None, rerun_obs, stage3_obs, False)
            == "rerun_report"
        )

        # refine_intrinsics=False, re-run did not fire: initial Stage 3 wins.
        assert (
            _select_conditioning_report(None, None, stage3_obs, False)
            == "stage3_report"
        )

    def test_conditioning_stage_selection_returns_none_when_no_observer(self):
        from aquacal.calibration.pipeline import _select_conditioning_report

        assert _select_conditioning_report(None, None, None, True) is None
        assert _select_conditioning_report(None, None, None, False) is None

    def test_conditioning_report_json_records_stage(self, tmp_path):
        from aquacal.validation.conditioning import (
            ConditioningReport,
            save_conditioning_report,
        )

        report = ConditioningReport(
            singular_values=np.array([2.0, 1.0]),
            condition_number=2.0,
            correlation=np.eye(2),
            rank=2,
            rank_tolerance=1e-12,
            n_params=2,
            n_residuals=4,
            parameter_names=["water_z", "cam1_tvec_z"],
        )
        json_path = tmp_path / "conditioning.json"
        npz_path = tmp_path / "conditioning.npz"
        save_conditioning_report(report, json_path, npz_path, stage="stage3")

        import json

        with open(json_path) as f:
            payload = json.load(f)

        assert payload["stage"] == "stage3"

    def test_observers_created_when_only_conditioning_enabled(self):
        """The pipeline must gate observer creation on the trace flag OR the
        conditioning flag, not the trace flag alone."""
        source = Path("src/aquacal/calibration/pipeline.py").read_text()
        assert "save_optimization_trace or config.save_conditioning" in source


# --- Test _compute_config_hash ---


class TestSaveBoardReferenceImages:
    """Tests for _save_board_reference_images function."""

    def test_save_board_reference_images_with_separate_intrinsic_board(
        self, sample_board_config
    ):
        """Test that both board images are saved when intrinsic board differs."""
        from aquacal.core.board import BoardGeometry

        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir)

            # Create two different board configurations
            board = BoardGeometry(sample_board_config)
            intrinsic_board_config = BoardConfig(
                squares_x=12,
                squares_y=9,
                square_size=0.025,
                marker_size=0.018,
                dictionary="DICT_4X4_100",
            )
            intrinsic_board = BoardGeometry(intrinsic_board_config)

            # Call the function
            _save_board_reference_images(board, intrinsic_board, output_dir)

            # Verify both images exist
            extrinsic_path = output_dir / "board_extrinsic.png"
            intrinsic_path = output_dir / "board_intrinsic.png"

            assert extrinsic_path.exists(), "board_extrinsic.png not saved"
            assert intrinsic_path.exists(), "board_intrinsic.png not saved"

            # Verify images are not empty
            assert extrinsic_path.stat().st_size > 0
            assert intrinsic_path.stat().st_size > 0

    def test_save_board_reference_images_without_separate_intrinsic_board(
        self, sample_board_config
    ):
        """Test that only extrinsic image is saved when intrinsic board is same."""
        from aquacal.core.board import BoardGeometry

        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir)

            # Create a single board used for both intrinsic and extrinsic
            board = BoardGeometry(sample_board_config)
            intrinsic_board = board  # Same object

            # Call the function
            _save_board_reference_images(board, intrinsic_board, output_dir)

            # Verify only extrinsic image exists
            extrinsic_path = output_dir / "board_extrinsic.png"
            intrinsic_path = output_dir / "board_intrinsic.png"

            assert extrinsic_path.exists(), "board_extrinsic.png not saved"
            assert not intrinsic_path.exists(), (
                "board_intrinsic.png should not be saved when boards are identical"
            )

            # Verify extrinsic image is not empty
            assert extrinsic_path.stat().st_size > 0


class TestComputeConfigHash:
    """Tests for _compute_config_hash function."""

    def test_compute_config_hash_deterministic(self, sample_board_config):
        """Test that same config produces same hash."""
        config = CalibrationConfig(
            board=sample_board_config,
            camera_names=["cam0", "cam1"],
            intrinsic_video_paths={"cam0": Path("/a"), "cam1": Path("/b")},
            extrinsic_video_paths={"cam0": Path("/c"), "cam1": Path("/d")},
            output_dir=Path("/out"),
        )

        hash1 = _compute_config_hash(config)
        hash2 = _compute_config_hash(config)

        assert hash1 == hash2
        assert len(hash1) == 12  # Truncated to 12 hex chars

    def test_compute_config_hash_different_config(self, sample_board_config):
        """Test that different configs produce different hashes."""
        config1 = CalibrationConfig(
            board=sample_board_config,
            camera_names=["cam0"],
            intrinsic_video_paths={"cam0": Path("/a")},
            extrinsic_video_paths={"cam0": Path("/c")},
            output_dir=Path("/out"),
            n_water=1.333,
        )

        config2 = CalibrationConfig(
            board=sample_board_config,
            camera_names=["cam0"],
            intrinsic_video_paths={"cam0": Path("/a")},
            extrinsic_video_paths={"cam0": Path("/c")},
            output_dir=Path("/out"),
            n_water=1.4,  # Different refractive index
        )

        hash1 = _compute_config_hash(config1)
        hash2 = _compute_config_hash(config2)

        assert hash1 != hash2

    def test_compute_config_hash_includes_intrinsic_board(self, sample_board_config):
        """Test that intrinsic_board is included in hash when provided."""
        intrinsic_board_config = BoardConfig(
            squares_x=12,
            squares_y=9,
            square_size=0.025,
            marker_size=0.018,
            dictionary="DICT_4X4_100",
        )

        config1 = CalibrationConfig(
            board=sample_board_config,
            camera_names=["cam0"],
            intrinsic_video_paths={"cam0": Path("/a")},
            extrinsic_video_paths={"cam0": Path("/c")},
            output_dir=Path("/out"),
            intrinsic_board=None,
        )

        config2 = CalibrationConfig(
            board=sample_board_config,
            camera_names=["cam0"],
            intrinsic_video_paths={"cam0": Path("/a")},
            extrinsic_video_paths={"cam0": Path("/c")},
            output_dir=Path("/out"),
            intrinsic_board=intrinsic_board_config,
        )

        hash1 = _compute_config_hash(config1)
        hash2 = _compute_config_hash(config2)

        # Different intrinsic_board should produce different hash
        assert hash1 != hash2

    def test_compute_config_hash_includes_initial_water_z(self, sample_board_config):
        """Test that initial_water_z is included in hash when provided."""
        config1 = CalibrationConfig(
            board=sample_board_config,
            camera_names=["cam0", "cam1"],
            intrinsic_video_paths={"cam0": Path("/a"), "cam1": Path("/b")},
            extrinsic_video_paths={"cam0": Path("/c"), "cam1": Path("/d")},
            output_dir=Path("/out"),
            initial_water_z=None,
        )

        config2 = CalibrationConfig(
            board=sample_board_config,
            camera_names=["cam0", "cam1"],
            intrinsic_video_paths={"cam0": Path("/a"), "cam1": Path("/b")},
            extrinsic_video_paths={"cam0": Path("/c"), "cam1": Path("/d")},
            output_dir=Path("/out"),
            initial_water_z={"cam0": 0.25, "cam1": 0.28},
        )

        config3 = CalibrationConfig(
            board=sample_board_config,
            camera_names=["cam0", "cam1"],
            intrinsic_video_paths={"cam0": Path("/a"), "cam1": Path("/b")},
            extrinsic_video_paths={"cam0": Path("/c"), "cam1": Path("/d")},
            output_dir=Path("/out"),
            initial_water_z={"cam0": 0.30, "cam1": 0.28},
        )

        hash1 = _compute_config_hash(config1)
        hash2 = _compute_config_hash(config2)
        hash3 = _compute_config_hash(config3)

        # Different initial_water_z should produce different hashes
        assert hash1 != hash2
        assert hash2 != hash3
        assert hash1 != hash3

    def test_config_hash_changes_with_seed(self, sample_board_config):
        """Two configs differing only by seed must hash differently."""
        config1 = CalibrationConfig(
            board=sample_board_config,
            camera_names=["cam0"],
            intrinsic_video_paths={"cam0": Path("/a")},
            extrinsic_video_paths={"cam0": Path("/c")},
            output_dir=Path("/out"),
            seed=42,
        )

        config2 = CalibrationConfig(
            board=sample_board_config,
            camera_names=["cam0"],
            intrinsic_video_paths={"cam0": Path("/a")},
            extrinsic_video_paths={"cam0": Path("/c")},
            output_dir=Path("/out"),
            seed=7,
        )

        hash1 = _compute_config_hash(config1)
        hash2 = _compute_config_hash(config2)

        assert hash1 != hash2


# --- Test run_calibration ---


class TestRunCalibration:
    """Tests for run_calibration function."""

    def test_run_calibration_loads_config_and_delegates(self, valid_config_yaml):
        """Test that run_calibration loads config and calls run_calibration_from_config."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(valid_config_yaml, f)
            f.flush()

            with patch(
                "aquacal.calibration.pipeline.run_calibration_from_config"
            ) as mock_run:
                mock_run.return_value = MagicMock(spec=CalibrationResult)

                _result = run_calibration(f.name)

                # Verify run_calibration_from_config was called
                mock_run.assert_called_once()

                # Verify the config was passed
                called_config = mock_run.call_args[0][0]
                assert isinstance(called_config, CalibrationConfig)
                assert called_config.board.squares_x == 7


# --- Test run_calibration_from_config (integration with mocks) ---


class TestRunCalibrationFromConfig:
    """Integration tests for run_calibration_from_config with mocked stages."""

    @pytest.fixture
    def mock_calibration_stages(
        self, sample_intrinsics, sample_extrinsics, sample_detection_result
    ):
        """Create mocks for all calibration stage functions."""
        with (
            patch("aquacal.calibration.pipeline.calibrate_intrinsics_all") as mock_intr,
            patch("aquacal.calibration.pipeline.detect_all_frames") as mock_detect,
            patch("aquacal.calibration.pipeline.build_pose_graph") as mock_pose_graph,
            patch("aquacal.calibration.pipeline.estimate_extrinsics") as mock_ext,
            patch("aquacal.calibration.pipeline.optimize_interface") as mock_opt,
            patch(
                "aquacal.validation.evaluation.compute_reprojection_errors"
            ) as mock_reproj,
            patch(
                "aquacal.validation.evaluation.compute_3d_distance_errors"
            ) as mock_3d,
            patch(
                "aquacal.calibration.pipeline.generate_diagnostic_report"
            ) as mock_diag,
            patch(
                "aquacal.calibration.pipeline.save_diagnostic_report"
            ) as mock_save_diag,
            patch("aquacal.calibration.pipeline.save_calibration") as mock_save_cal,
        ):
            # Setup return values
            mock_intr.return_value = {
                "cam0": (sample_intrinsics, 0.5),
                "cam1": (sample_intrinsics, 0.6),
            }
            mock_detect.return_value = sample_detection_result
            mock_pose_graph.return_value = MagicMock()
            mock_ext.return_value = {
                "cam0": sample_extrinsics,
                "cam1": sample_extrinsics,
            }
            mock_opt.return_value = (
                {"cam0": sample_extrinsics, "cam1": sample_extrinsics},  # extrinsics
                {"cam0": 0.15, "cam1": 0.16},  # distances
                [BoardPose(0, np.zeros(3), np.array([0, 0, 0.5]))],  # poses
                0.8,  # rms
            )

            # Mock reprojection errors
            mock_reproj_result = MagicMock()
            mock_reproj_result.rms = 0.7
            mock_reproj_result.per_camera = {"cam0": 0.6, "cam1": 0.8}
            mock_reproj_result.per_frame = {0: 0.7}
            mock_reproj_result.residuals = np.array([[0.1, 0.2]])
            mock_reproj.return_value = mock_reproj_result

            # Mock 3D errors
            mock_3d_result = MagicMock()
            mock_3d_result.mean = 0.001
            mock_3d_result.std = 0.0005
            mock_3d_result.signed_mean = 0.0002
            mock_3d_result.rmse = 0.0011
            mock_3d_result.percent_error = 2.5
            mock_3d_result.num_frames = 8
            mock_3d.return_value = mock_3d_result

            # Mock diagnostic report
            mock_diag.return_value = MagicMock()
            mock_save_diag.return_value = {"json": Path("/out/diagnostics.json")}

            yield {
                "intrinsics": mock_intr,
                "detect": mock_detect,
                "pose_graph": mock_pose_graph,
                "extrinsics": mock_ext,
                "optimize": mock_opt,
                "reproj": mock_reproj,
                "3d": mock_3d,
                "diag": mock_diag,
                "save_diag": mock_save_diag,
                "save_cal": mock_save_cal,
            }

    def test_run_calibration_from_config_stages_order(
        self, mock_calibration_stages, sample_board_config
    ):
        """Test that all stages are called in correct order."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config = CalibrationConfig(
                board=sample_board_config,
                camera_names=["cam0", "cam1"],
                intrinsic_video_paths={
                    "cam0": Path("/path/cam0.mp4"),
                    "cam1": Path("/path/cam1.mp4"),
                },
                extrinsic_video_paths={
                    "cam0": Path("/path/cam0_uw.mp4"),
                    "cam1": Path("/path/cam1_uw.mp4"),
                },
                output_dir=Path(tmpdir),
            )

            result = run_calibration_from_config(config)

            # Verify all stages were called
            mock_calibration_stages["intrinsics"].assert_called_once()
            mock_calibration_stages["detect"].assert_called_once()
            mock_calibration_stages["pose_graph"].assert_called_once()
            mock_calibration_stages["extrinsics"].assert_called_once()
            mock_calibration_stages["optimize"].assert_called_once()
            mock_calibration_stages["reproj"].assert_called_once()
            mock_calibration_stages["3d"].assert_called_once()
            mock_calibration_stages["diag"].assert_called_once()
            mock_calibration_stages["save_diag"].assert_called_once()
            # save_cal called 3 times: calibration_initial.json, the default-on
            # internals/calibration_stage3.json dump, and calibration.json
            assert mock_calibration_stages["save_cal"].call_count == 3

            # Verify result
            assert isinstance(result, CalibrationResult)
            assert len(result.cameras) == 2

    def test_run_calibration_from_config_saves_calibration(
        self, mock_calibration_stages, sample_board_config
    ):
        """Test that calibration is saved to output_dir."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config = CalibrationConfig(
                board=sample_board_config,
                camera_names=["cam0", "cam1"],
                intrinsic_video_paths={
                    "cam0": Path("/path/cam0.mp4"),
                    "cam1": Path("/path/cam1.mp4"),
                },
                extrinsic_video_paths={
                    "cam0": Path("/path/cam0_uw.mp4"),
                    "cam1": Path("/path/cam1_uw.mp4"),
                },
                output_dir=Path(tmpdir),
            )

            run_calibration_from_config(config)

            # Verify save_calibration was called 3 times: calibration_initial.json,
            # the default-on internals/calibration_stage3.json dump, and calibration.json
            assert mock_calibration_stages["save_cal"].call_count == 3
            # First call: calibration_initial.json
            initial_call_args = mock_calibration_stages["save_cal"].call_args_list[0]
            assert str(initial_call_args[0][1]).endswith("calibration_initial.json")
            # Second call: internals/calibration_stage3.json (HOOK-01 stage dump)
            stage3_call_args = mock_calibration_stages["save_cal"].call_args_list[1]
            assert str(stage3_call_args[0][1]).endswith(
                str(Path("internals") / "calibration_stage3.json")
            )
            # Third call: calibration.json
            final_call_args = mock_calibration_stages["save_cal"].call_args_list[2]
            assert str(final_call_args[0][1]).endswith("calibration.json")

    def test_run_calibration_from_config_saves_diagnostics(
        self, mock_calibration_stages, sample_board_config
    ):
        """Test that diagnostics are saved to output_dir."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config = CalibrationConfig(
                board=sample_board_config,
                camera_names=["cam0", "cam1"],
                intrinsic_video_paths={
                    "cam0": Path("/path/cam0.mp4"),
                    "cam1": Path("/path/cam1.mp4"),
                },
                extrinsic_video_paths={
                    "cam0": Path("/path/cam0_uw.mp4"),
                    "cam1": Path("/path/cam1_uw.mp4"),
                },
                output_dir=Path(tmpdir),
            )

            run_calibration_from_config(config)

            # Verify save_diagnostic_report was called
            mock_calibration_stages["save_diag"].assert_called_once()
            call_args = mock_calibration_stages["save_diag"].call_args
            # Fourth positional arg is output_dir (report, calibration, detections, output_dir)
            assert call_args[0][3] == Path(tmpdir)
            # save_images should be True
            assert call_args[1]["save_images"] is True

    def test_run_calibration_from_config_prints_progress(
        self, mock_calibration_stages, sample_board_config, capsys
    ):
        """Test that progress is printed to stdout."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config = CalibrationConfig(
                board=sample_board_config,
                camera_names=["cam0", "cam1"],
                intrinsic_video_paths={
                    "cam0": Path("/path/cam0.mp4"),
                    "cam1": Path("/path/cam1.mp4"),
                },
                extrinsic_video_paths={
                    "cam0": Path("/path/cam0_uw.mp4"),
                    "cam1": Path("/path/cam1_uw.mp4"),
                },
                output_dir=Path(tmpdir),
            )

            run_calibration_from_config(config)

            captured = capsys.readouterr()

            # Check for key progress messages
            assert "AquaCal Calibration Pipeline" in captured.out
            assert "[Stage 1]" in captured.out
            assert "[Stage 2]" in captured.out
            assert "[Stage 3]" in captured.out
            assert "[Validation]" in captured.out
            assert "[Diagnostics]" in captured.out
            assert "[Save]" in captured.out
            assert "Calibration complete!" in captured.out

    def test_run_calibration_from_config_uses_intrinsic_board(
        self, mock_calibration_stages, sample_board_config
    ):
        """Test that intrinsic_board is passed to calibrate_intrinsics_all when provided."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create a different board for intrinsics
            intrinsic_board_config = BoardConfig(
                squares_x=12,
                squares_y=9,
                square_size=0.025,
                marker_size=0.018,
                dictionary="DICT_4X4_100",
            )

            config = CalibrationConfig(
                board=sample_board_config,
                intrinsic_board=intrinsic_board_config,
                camera_names=["cam0", "cam1"],
                intrinsic_video_paths={
                    "cam0": Path("/path/cam0.mp4"),
                    "cam1": Path("/path/cam1.mp4"),
                },
                extrinsic_video_paths={
                    "cam0": Path("/path/cam0_uw.mp4"),
                    "cam1": Path("/path/cam1_uw.mp4"),
                },
                output_dir=Path(tmpdir),
            )

            run_calibration_from_config(config)

            # Verify calibrate_intrinsics_all was called with intrinsic board
            mock_calibration_stages["intrinsics"].assert_called_once()
            call_args = mock_calibration_stages["intrinsics"].call_args

            # Check that the board parameter has the intrinsic board config
            board_arg = call_args[1]["board"]
            assert board_arg.config.squares_x == 12
            assert board_arg.config.squares_y == 9
            assert board_arg.config.square_size == 0.025
            assert board_arg.config.marker_size == 0.018

    def test_run_calibration_from_config_falls_back_to_extrinsic_board(
        self, mock_calibration_stages, sample_board_config
    ):
        """Test that extrinsic board is used for intrinsics when intrinsic_board is None."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config = CalibrationConfig(
                board=sample_board_config,
                intrinsic_board=None,  # No separate intrinsic board
                camera_names=["cam0", "cam1"],
                intrinsic_video_paths={
                    "cam0": Path("/path/cam0.mp4"),
                    "cam1": Path("/path/cam1.mp4"),
                },
                extrinsic_video_paths={
                    "cam0": Path("/path/cam0_uw.mp4"),
                    "cam1": Path("/path/cam1_uw.mp4"),
                },
                output_dir=Path(tmpdir),
            )

            run_calibration_from_config(config)

            # Verify calibrate_intrinsics_all was called with extrinsic board
            mock_calibration_stages["intrinsics"].assert_called_once()
            call_args = mock_calibration_stages["intrinsics"].call_args

            # Check that the board parameter has the extrinsic board config
            board_arg = call_args[1]["board"]
            assert board_arg.config.squares_x == 7
            assert board_arg.config.squares_y == 5
            assert board_arg.config.square_size == 0.03
            assert board_arg.config.marker_size == 0.022

    def test_run_calibration_from_config_passes_initial_water_z(
        self, mock_calibration_stages, sample_board_config
    ):
        """Test that initial_water_z is passed to optimize_interface."""
        with tempfile.TemporaryDirectory() as tmpdir:
            initial_water_z = {"cam0": 0.25, "cam1": 0.28}
            config = CalibrationConfig(
                board=sample_board_config,
                camera_names=["cam0", "cam1"],
                intrinsic_video_paths={
                    "cam0": Path("/path/cam0.mp4"),
                    "cam1": Path("/path/cam1.mp4"),
                },
                extrinsic_video_paths={
                    "cam0": Path("/path/cam0_uw.mp4"),
                    "cam1": Path("/path/cam1_uw.mp4"),
                },
                output_dir=Path(tmpdir),
                initial_water_z=initial_water_z,
            )

            run_calibration_from_config(config)

            # Verify optimize_interface was called with initial_water_z
            mock_calibration_stages["optimize"].assert_called_once()
            call_args = mock_calibration_stages["optimize"].call_args

            # Check that initial_water_z was passed
            assert call_args[1]["initial_water_zs"] == initial_water_z

    def test_run_calibration_from_config_estimates_validation_poses(
        self, mock_calibration_stages, sample_board_config, capsys
    ):
        """Test that validation frame board poses are estimated and reported."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config = CalibrationConfig(
                board=sample_board_config,
                camera_names=["cam0", "cam1"],
                intrinsic_video_paths={
                    "cam0": Path("/path/cam0.mp4"),
                    "cam1": Path("/path/cam1.mp4"),
                },
                extrinsic_video_paths={
                    "cam0": Path("/path/cam0_uw.mp4"),
                    "cam1": Path("/path/cam1_uw.mp4"),
                },
                output_dir=Path(tmpdir),
                holdout_fraction=0.2,
            )

            run_calibration_from_config(config)

            captured = capsys.readouterr()

            # Check that validation pose estimation message is printed
            assert (
                "[Validation] Estimating board poses for held-out frames"
                in captured.out
            )
            assert "Estimated" in captured.out
            assert "validation frame poses" in captured.out


# --- Test Auxiliary Camera Separation ---


class TestAuxiliaryCameraSeparation:
    """Tests for auxiliary camera metric separation from primary cameras."""

    @pytest.fixture
    def mock_calibration_stages_with_aux(
        self, sample_intrinsics, sample_extrinsics, sample_detection_result
    ):
        """Create mocks for all calibration stage functions, including auxiliary camera."""
        with (
            patch("aquacal.calibration.pipeline.calibrate_intrinsics_all") as mock_intr,
            patch("aquacal.calibration.pipeline.detect_all_frames") as mock_detect,
            patch("aquacal.calibration.pipeline.build_pose_graph") as mock_pose_graph,
            patch("aquacal.calibration.pipeline.estimate_extrinsics") as mock_ext,
            patch("aquacal.calibration.pipeline.optimize_interface") as mock_opt,
            patch("aquacal.calibration.pipeline.register_auxiliary_camera") as mock_aux,
            patch(
                "aquacal.validation.evaluation.compute_reprojection_errors"
            ) as mock_reproj,
            patch(
                "aquacal.validation.evaluation.compute_3d_distance_errors"
            ) as mock_3d,
            patch(
                "aquacal.calibration.pipeline.generate_diagnostic_report"
            ) as mock_diag,
            patch(
                "aquacal.calibration.pipeline.save_diagnostic_report"
            ) as mock_save_diag,
            patch("aquacal.calibration.pipeline.save_calibration") as mock_save_cal,
        ):
            # Setup return values
            mock_intr.return_value = {
                "cam0": (sample_intrinsics, 0.5),
                "cam1": (sample_intrinsics, 0.6),
                "aux_cam": (sample_intrinsics, 0.7),
            }

            # Create detection result with auxiliary camera
            frames = {}
            for i in range(10):
                detections = {}
                for cam in ["cam0", "cam1", "aux_cam"]:
                    detections[cam] = Detection(
                        corner_ids=np.array([0, 1, 2, 3], dtype=np.int32),
                        corners_2d=np.array(
                            [[100, 100], [200, 100], [100, 200], [200, 200]],
                            dtype=np.float64,
                        ),
                    )
                frames[i] = FrameDetections(frame_idx=i, detections=detections)

            detection_result_with_aux = DetectionResult(
                frames=frames,
                camera_names=["cam0", "cam1", "aux_cam"],
                total_frames=10,
            )

            mock_detect.return_value = detection_result_with_aux
            mock_pose_graph.return_value = MagicMock()
            mock_ext.return_value = {
                "cam0": sample_extrinsics,
                "cam1": sample_extrinsics,
            }
            mock_opt.return_value = (
                {"cam0": sample_extrinsics, "cam1": sample_extrinsics},  # extrinsics
                {"cam0": 0.15, "cam1": 0.16},  # distances
                [BoardPose(0, np.zeros(3), np.array([0, 0, 0.5]))],  # poses
                0.8,  # rms
            )

            # Mock auxiliary camera registration
            mock_aux.return_value = (
                sample_extrinsics,  # extrinsics
                0.17,  # distance
                1.5,  # rms (higher than primary)
            )

            # Mock reprojection errors - will be called multiple times
            def reproj_side_effect(calibration, detections, poses):
                # Count cameras to determine if primary or auxiliary
                num_cams = len(calibration.cameras)
                if num_cams == 2:
                    # Primary cameras only
                    result = MagicMock()
                    result.rms = 0.7
                    result.per_camera = {"cam0": 0.6, "cam1": 0.8}
                    result.per_frame = {0: 0.7}
                    result.residuals = np.array([[0.1, 0.2]])
                    result.num_observations = 100
                    return result
                elif num_cams == 1:
                    # Auxiliary camera only
                    result = MagicMock()
                    result.rms = 1.5
                    result.per_camera = {"aux_cam": 1.5}
                    result.per_frame = {0: 1.5}
                    result.residuals = np.array([[0.3, 0.4]])
                    result.num_observations = 50
                    return result
                else:
                    # Full result (shouldn't be used for metrics)
                    result = MagicMock()
                    result.rms = 1.0
                    result.per_camera = {"cam0": 0.6, "cam1": 0.8, "aux_cam": 1.5}
                    result.per_frame = {0: 1.0}
                    result.residuals = np.array([[0.2, 0.3]])
                    result.num_observations = 150
                    return result

            mock_reproj.side_effect = reproj_side_effect

            # Mock 3D errors
            mock_3d_result = MagicMock()
            mock_3d_result.mean = 0.001
            mock_3d_result.std = 0.0005
            mock_3d_result.signed_mean = 0.0002
            mock_3d_result.rmse = 0.0011
            mock_3d_result.percent_error = 2.5
            mock_3d_result.num_frames = 8
            mock_3d.return_value = mock_3d_result

            # Mock diagnostic report
            mock_diag.return_value = MagicMock()
            mock_save_diag.return_value = {"json": Path("/out/diagnostics.json")}

            yield {
                "intrinsics": mock_intr,
                "detect": mock_detect,
                "pose_graph": mock_pose_graph,
                "extrinsics": mock_ext,
                "optimize": mock_opt,
                "aux": mock_aux,
                "reproj": mock_reproj,
                "3d": mock_3d,
                "diag": mock_diag,
                "save_diag": mock_save_diag,
                "save_cal": mock_save_cal,
            }

    def test_auxiliary_cameras_excluded_from_diagnostics_data(
        self, mock_calibration_stages_with_aux, sample_board_config
    ):
        """Test that DiagnosticsData contains only primary camera metrics."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config = CalibrationConfig(
                board=sample_board_config,
                camera_names=["cam0", "cam1"],
                auxiliary_cameras=["aux_cam"],
                intrinsic_video_paths={
                    "cam0": Path("/path/cam0.mp4"),
                    "cam1": Path("/path/cam1.mp4"),
                    "aux_cam": Path("/path/aux_cam.mp4"),
                },
                extrinsic_video_paths={
                    "cam0": Path("/path/cam0_uw.mp4"),
                    "cam1": Path("/path/cam1_uw.mp4"),
                    "aux_cam": Path("/path/aux_cam_uw.mp4"),
                },
                output_dir=Path(tmpdir),
            )

            result = run_calibration_from_config(config)

            # Overall RMS is primary-only; per-camera dict includes all cameras
            assert result.diagnostics.reprojection_error_rms == 0.7  # Primary only
            assert "cam0" in result.diagnostics.reprojection_error_per_camera
            assert "cam1" in result.diagnostics.reprojection_error_per_camera
            assert "aux_cam" in result.diagnostics.reprojection_error_per_camera

    def test_auxiliary_cameras_in_final_result(
        self, mock_calibration_stages_with_aux, sample_board_config
    ):
        """Test that auxiliary cameras are in final CalibrationResult with is_auxiliary=True."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config = CalibrationConfig(
                board=sample_board_config,
                camera_names=["cam0", "cam1"],
                auxiliary_cameras=["aux_cam"],
                intrinsic_video_paths={
                    "cam0": Path("/path/cam0.mp4"),
                    "cam1": Path("/path/cam1.mp4"),
                    "aux_cam": Path("/path/aux_cam.mp4"),
                },
                extrinsic_video_paths={
                    "cam0": Path("/path/cam0_uw.mp4"),
                    "cam1": Path("/path/cam1_uw.mp4"),
                    "aux_cam": Path("/path/aux_cam_uw.mp4"),
                },
                output_dir=Path(tmpdir),
            )

            result = run_calibration_from_config(config)

            # Verify all cameras in final result
            assert len(result.cameras) == 3
            assert "aux_cam" in result.cameras
            assert result.cameras["aux_cam"].is_auxiliary is True
            assert result.cameras["cam0"].is_auxiliary is False
            assert result.cameras["cam1"].is_auxiliary is False

    def test_auxiliary_cameras_saved_in_diagnostics_json(
        self, mock_calibration_stages_with_aux, sample_board_config
    ):
        """Test that auxiliary camera metrics appear in diagnostics.json."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config = CalibrationConfig(
                board=sample_board_config,
                camera_names=["cam0", "cam1"],
                auxiliary_cameras=["aux_cam"],
                intrinsic_video_paths={
                    "cam0": Path("/path/cam0.mp4"),
                    "cam1": Path("/path/cam1.mp4"),
                    "aux_cam": Path("/path/aux_cam.mp4"),
                },
                extrinsic_video_paths={
                    "cam0": Path("/path/cam0_uw.mp4"),
                    "cam1": Path("/path/cam1_uw.mp4"),
                    "aux_cam": Path("/path/aux_cam_uw.mp4"),
                },
                output_dir=Path(tmpdir),
            )

            run_calibration_from_config(config)

            # Verify save_diagnostic_report was called with auxiliary_reprojection
            save_diag_calls = mock_calibration_stages_with_aux["save_diag"].call_args
            assert "auxiliary_reprojection" in save_diag_calls[1]
            aux_reproj = save_diag_calls[1]["auxiliary_reprojection"]
            assert aux_reproj is not None
            assert "aux_cam" in aux_reproj.per_camera

    def test_no_auxiliary_cameras_no_regression(
        self, mock_calibration_stages_with_aux, sample_board_config
    ):
        """Test that pipeline still works when no auxiliary cameras are configured."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config = CalibrationConfig(
                board=sample_board_config,
                camera_names=["cam0", "cam1"],
                auxiliary_cameras=[],  # No auxiliary cameras
                intrinsic_video_paths={
                    "cam0": Path("/path/cam0.mp4"),
                    "cam1": Path("/path/cam1.mp4"),
                },
                extrinsic_video_paths={
                    "cam0": Path("/path/cam0_uw.mp4"),
                    "cam1": Path("/path/cam1_uw.mp4"),
                },
                output_dir=Path(tmpdir),
            )

            result = run_calibration_from_config(config)

            # Verify result is valid
            assert isinstance(result, CalibrationResult)
            assert len(result.cameras) == 2
            assert all(not cam.is_auxiliary for cam in result.cameras.values())

    def test_auxiliary_cameras_printed_separately(
        self, mock_calibration_stages_with_aux, sample_board_config, capsys
    ):
        """Test that auxiliary camera metrics are printed separately in console output."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config = CalibrationConfig(
                board=sample_board_config,
                camera_names=["cam0", "cam1"],
                auxiliary_cameras=["aux_cam"],
                intrinsic_video_paths={
                    "cam0": Path("/path/cam0.mp4"),
                    "cam1": Path("/path/cam1.mp4"),
                    "aux_cam": Path("/path/aux_cam.mp4"),
                },
                extrinsic_video_paths={
                    "cam0": Path("/path/cam0_uw.mp4"),
                    "cam1": Path("/path/cam1_uw.mp4"),
                    "aux_cam": Path("/path/aux_cam_uw.mp4"),
                },
                output_dir=Path(tmpdir),
            )

            run_calibration_from_config(config)

            captured = capsys.readouterr()

            # Check that primary and auxiliary are printed separately
            assert "Primary cameras:" in captured.out
            assert "Auxiliary cameras:" in captured.out
            assert "aux_cam: RMS" in captured.out


class TestSharedEvaluationRefactor:
    """Tests guarding the HOOK-04 refactor: pipeline calls evaluate_calibration."""

    def test_pipeline_uses_shared_evaluation(self):
        """The held-out block is a call to evaluate_calibration, one code path."""
        source = Path("src/aquacal/calibration/pipeline.py").read_text(encoding="utf-8")

        assert "evaluate_calibration(" in source
        # No second compute_3d_distance_errors call path inside pipeline.py itself
        # (evaluate_calibration is the sole caller now).
        assert "compute_3d_distance_errors(" not in source

    def test_estimate_validation_poses_moved(self):
        """_estimate_validation_poses moved to validation/evaluation.py."""
        source = Path("src/aquacal/calibration/pipeline.py").read_text(encoding="utf-8")

        assert "def _estimate_validation_poses" not in source

        # Still resolves via the import, proving the move did not break importers.
        from aquacal.calibration.pipeline import _estimate_validation_poses

        assert callable(_estimate_validation_poses)


class TestResolvePerCameraWaterZSeeds:
    """IFACE-04 seed-resolution rules for the per-camera path."""

    CAMERAS = ["cam0", "cam1", "cam2"]
    AUX = ["aux0"]

    def test_none_fills_default_silently(self, recwarn):
        """initial_water_z is None -> every camera gets 0.15, no warning."""
        resolved = _resolve_per_camera_water_z_seeds(None, self.CAMERAS, self.AUX)
        assert resolved == {"cam0": 0.15, "cam1": 0.15, "cam2": 0.15}
        assert len(recwarn) == 0

    def test_partial_dict_fills_and_warns(self):
        """Missing cameras are filled with 0.15 and named in a single warning."""
        with pytest.warns(UserWarning, match="defaulted to 0.15m") as record:
            resolved = _resolve_per_camera_water_z_seeds(
                {"cam0": 0.22}, self.CAMERAS, self.AUX
            )
        assert resolved == {"cam0": 0.22, "cam1": 0.15, "cam2": 0.15}
        message = str(record[0].message)
        assert "cam1" in message and "cam2" in message

    def test_unknown_key_warns_as_typo(self):
        """A key matching no primary or auxiliary camera warns as a likely typo."""
        with pytest.warns(UserWarning, match="unknown camera name") as record:
            resolved = _resolve_per_camera_water_z_seeds(
                {"cam0": 0.2, "cam1": 0.2, "cam2": 0.2, "typo9": 0.3},
                self.CAMERAS,
                self.AUX,
            )
        assert set(resolved.keys()) == set(self.CAMERAS)
        assert "typo9" in str(record[0].message)

    def test_auxiliary_key_silently_ignored(self, recwarn):
        """An auxiliary-camera key is a valid exclusion, not a typo -> no warning."""
        resolved = _resolve_per_camera_water_z_seeds(
            {"cam0": 0.2, "cam1": 0.2, "cam2": 0.2, "aux0": 0.3},
            self.CAMERAS,
            self.AUX,
        )
        assert set(resolved.keys()) == set(self.CAMERAS)
        assert "aux0" not in resolved
        # No warning about the auxiliary key (all primaries were covered).
        assert len(recwarn) == 0


class TestBuildInterfaceSpreadReport:
    """Per-camera water_z spread report (meters + stats)."""

    def test_report_math_and_schema(self):
        distances = {"cam0": 0.10, "cam1": 0.20, "cam2": 0.30}
        report = build_interface_spread_report(distances, "stage3")

        assert report["stage"] == "stage3"
        assert report["unit"] == "meters"
        assert report["per_camera"] == {"cam0": 0.10, "cam1": 0.20, "cam2": 0.30}

        values = np.array([0.10, 0.20, 0.30])
        stats = report["stats"]
        assert stats["min"] == pytest.approx(values.min())
        assert stats["max"] == pytest.approx(values.max())
        assert stats["mean"] == pytest.approx(values.mean())
        assert stats["std"] == pytest.approx(values.std())  # population std (ddof=0)
        assert stats["range"] == pytest.approx(np.ptp(values))

    def test_report_json_round_trips(self):
        report = build_interface_spread_report(
            {"cam0": 0.12, "cam1": 0.18}, "stage3_intrinsic_pass"
        )
        assert json.loads(json.dumps(report)) == report


class TestSolverConfigSeedIsInert:
    """D-26 zero-numerical-change guard for plan 19.2-14 (EXP-11).

    Proves that adding `solver_config["seed"]` to `run_calibration_from_config`
    changed no calibration number. The frozen constants below were captured
    from `src/aquacal/calibration/pipeline.py` as it existed at commit
    e1d6548dbe807eb0abc0d0e8f8c1f9c0065d7477 -- the commit immediately BEFORE
    the Task 1 edit (`877634a`) that added the `seed` key. Capture procedure:
    the pre-change file was loaded via `importlib.util.spec_from_file_location`
    from a `git show <sha>:...` blob and run once through the same
    `run_calibration_from_config` entry point exercised below, with only the
    video-decode boundary mocked. These constants must NEVER be regenerated
    to make a failing test pass -- a mismatch here means the addition was not
    inert and is a finding to report, not a tolerance to loosen.
    """

    # Frozen anchor, scenario "ideal" (4 cameras, 20 frames, 0 noise), seed=99,
    # captured at commit e1d6548dbe807eb0abc0d0e8f8c1f9c0065d7477.
    _ANCHOR_CAMERAS = {
        "cam0": {
            "R": [[1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0]],
            "t": [0.0, 0.0, 0.0],
            "water_z": 0.15000000000000047,
        },
        "cam1": {
            "R": [
                [0.9984993371509613, -0.054763799257274454, -9.217086465271786e-17],
                [0.054763799257274454, 0.9984993371509613, -2.422545075173034e-16],
                [1.0529932447921676e-16, 2.3684333844864933e-16, 1.0],
            ],
            "t": [
                -0.09984993371509608,
                -0.005476379925727421,
                -1.184025295478873e-17,
            ],
            "water_z": 0.15000000000000047,
        },
        "cam2": {
            "R": [
                [0.9974292528492325, -0.07165811580429554, 2.1964919671058154e-16],
                [0.07165811580429554, 0.9974292528492325, -2.559759473441722e-16],
                [-2.0074178008606616e-16, 2.7105754548107973e-16, 1.0],
            ],
            "t": [
                0.007165811580429521,
                -0.09974292528492322,
                -2.1668899675048093e-18,
            ],
            "water_z": 0.15000000000000047,
        },
        "cam3": {
            "R": [
                [0.996707967334501, 0.08107544543156972, -6.4662664298548575e-18],
                [-0.08107544543156972, 0.996707967334501, -2.757665631684116e-16],
                [-1.5912917674467915e-17, 2.753829860654885e-16, 1.0],
            ],
            "t": [
                -0.10777834127660704,
                -0.09156325219029311,
                1.0739560128998414e-17,
            ],
            "water_z": 0.15000000000000047,
        },
    }
    _ANCHOR_REPROJECTION_RMS = 2.1586323025826994e-13
    _ANCHOR_VALIDATION_3D_ERROR_MEAN = 1.9506001752094764e-16

    @staticmethod
    def _run_ideal_pipeline(tmp_path):
        """Run run_calibration_from_config end to end (video-decode boundary
        mocked only) on the deterministic 'ideal' scenario at seed=99, and
        return the same numbers the pre-change anchor above was captured
        with: per-camera extrinsics/water_z plus the written benchmark.json's
        accuracy block."""
        scenario = create_scenario("ideal")
        board = BoardGeometry(scenario.board_config)
        detections = generate_synthetic_detections(
            intrinsics=scenario.intrinsics,
            extrinsics=scenario.extrinsics,
            water_zs=scenario.water_zs,
            board=board,
            board_poses=scenario.board_poses,
            noise_std=scenario.noise_std,
            n_air=scenario.n_air,
            n_water=scenario.n_water,
            seed=scenario.seed,
        )
        config = CalibrationConfig(
            board=scenario.board_config,
            camera_names=list(scenario.intrinsics.keys()),
            intrinsic_video_paths={
                cam: Path(f"/fake/{cam}_intrinsic.mp4") for cam in scenario.intrinsics
            },
            extrinsic_video_paths={
                cam: Path(f"/fake/{cam}_extrinsic.mp4") for cam in scenario.intrinsics
            },
            output_dir=tmp_path,
            save_stage_calibrations=False,
            seed=99,
        )
        with (
            patch("aquacal.calibration.pipeline.calibrate_intrinsics_all") as mock_intr,
            patch("aquacal.calibration.pipeline.detect_all_frames") as mock_detect,
        ):
            mock_intr.return_value = {
                cam: (intr, 0.1) for cam, intr in scenario.intrinsics.items()
            }
            mock_detect.return_value = detections
            result = run_calibration_from_config(config)

        with open(tmp_path / "benchmark.json") as f:
            record = json.load(f)

        cameras = {}
        for cam_name in sorted(result.cameras):
            cam = result.cameras[cam_name]
            cameras[cam_name] = {
                "R": cam.extrinsics.R.tolist(),
                "t": cam.extrinsics.t.tolist(),
                "water_z": float(cam.water_z),
            }
        return cameras, record["accuracy"]

    @pytest.mark.slow
    def test_same_process_repeat_is_bit_exact(self, tmp_path):
        """Two identical-argument runs of the current (post-edit) code agree
        exactly. This alone does NOT prove inertness across the edit (it
        cannot see a change made to the code itself) -- see
        test_matches_pre_change_anchor for that."""
        cameras_1, accuracy_1 = self._run_ideal_pipeline(tmp_path / "run1")
        cameras_2, accuracy_2 = self._run_ideal_pipeline(tmp_path / "run2")

        assert cameras_1.keys() == cameras_2.keys()
        for cam_name in cameras_1:
            np.testing.assert_array_equal(
                cameras_1[cam_name]["R"], cameras_2[cam_name]["R"]
            )
            np.testing.assert_array_equal(
                cameras_1[cam_name]["t"], cameras_2[cam_name]["t"]
            )
            assert cameras_1[cam_name]["water_z"] == cameras_2[cam_name]["water_z"]
        assert accuracy_1["reprojection_rms"] == accuracy_2["reprojection_rms"]
        np.testing.assert_array_equal(
            accuracy_1["validation_3d_error_mean"],
            accuracy_2["validation_3d_error_mean"],
        )

    @pytest.mark.slow
    def test_matches_pre_change_anchor(self, tmp_path):
        """The current (post-edit) code's numbers exactly match the frozen
        pre-change anchor captured at commit
        e1d6548dbe807eb0abc0d0e8f8c1f9c0065d7477 -- proving the added
        solver_config["seed"] key moved no calibration number."""
        cameras, accuracy = self._run_ideal_pipeline(tmp_path)

        assert cameras.keys() == self._ANCHOR_CAMERAS.keys()
        for cam_name, anchor_cam in self._ANCHOR_CAMERAS.items():
            np.testing.assert_array_equal(cameras[cam_name]["R"], anchor_cam["R"])
            np.testing.assert_array_equal(cameras[cam_name]["t"], anchor_cam["t"])
            assert cameras[cam_name]["water_z"] == anchor_cam["water_z"]
        assert accuracy["reprojection_rms"] == self._ANCHOR_REPROJECTION_RMS
        assert (
            accuracy["validation_3d_error_mean"]
            == self._ANCHOR_VALIDATION_3D_ERROR_MEAN
        )
