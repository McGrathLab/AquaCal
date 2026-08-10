"""Tests for scripts/extract_frames.py.

The script lives outside the `aquacal` package (`scripts/`, per D-11), so it
is loaded by file path rather than imported normally. `VideoSet` and
`_discover_video_paths` are monkeypatched inside the loaded module so no real
AVI is ever decoded.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path
from types import ModuleType

import numpy as np
import pytest
from natsort import natsorted

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT_PATH = REPO_ROOT / "scripts" / "extract_frames.py"


def _load_extract_frames_module() -> ModuleType:
    spec = importlib.util.spec_from_file_location("extract_frames", SCRIPT_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def module() -> ModuleType:
    """Fresh, isolated load of scripts/extract_frames.py for each test."""
    return _load_extract_frames_module()


def _make_fake_video_set(frames_by_camera: dict[str, list[np.ndarray | None]]):
    """Build a fake VideoSet class yielding fixed per-camera frame lists.

    Args:
        frames_by_camera: camera_id -> list of frames (or None) to yield,
            aligned by index across cameras.

    Returns:
        A class with the same constructor/`iterate_frames` shape as
        `aquacal.io.video.VideoSet`, plus a `captured_steps` list recording
        every `step` value `iterate_frames` was called with.
    """
    captured_steps: list[int] = []
    n_frames = max((len(v) for v in frames_by_camera.values()), default=0)

    class FakeVideoSet:
        def __init__(self, video_paths: dict[str, str]) -> None:
            self.video_paths = video_paths

        def iterate_frames(self, start: int = 0, stop=None, step: int = 1):
            captured_steps.append(step)
            for idx in range(n_frames):
                frames = {
                    cam: (frame_list[idx] if idx < len(frame_list) else None)
                    for cam, frame_list in frames_by_camera.items()
                }
                yield idx, frames

    FakeVideoSet.captured_steps = captured_steps  # type: ignore[attr-defined]
    return FakeVideoSet


def _make_frame(seed: int = 0) -> np.ndarray:
    rng = np.random.default_rng(seed)
    return rng.integers(0, 255, size=(8, 8, 3), dtype=np.uint8)


def _patch_discovery(monkeypatch, module: ModuleType, camera_ids: list[str]) -> None:
    fake_paths = {cam: f"fake/{cam}.avi" for cam in camera_ids}
    monkeypatch.setattr(
        module, "_discover_video_paths", lambda video_dir, cameras: fake_paths
    )


def test_writes_zero_padded_png_names(tmp_path, monkeypatch, module) -> None:
    """Frames are written as frame0000.png, frame0001.png, ... per camera."""
    frames_by_camera = {
        "camA": [_make_frame(1), _make_frame(2), _make_frame(3)],
        "camB": [_make_frame(4), _make_frame(5), _make_frame(6)],
    }
    fake_vs_cls = _make_fake_video_set(frames_by_camera)
    monkeypatch.setattr(module, "VideoSet", fake_vs_cls)
    _patch_discovery(monkeypatch, module, list(frames_by_camera))

    out_dir = tmp_path / "out"
    rc = module.main(
        ["--video-dir", str(tmp_path), "--out-dir", str(out_dir), "--step", "1"]
    )

    assert rc == 0
    for cam in frames_by_camera:
        names = sorted(p.name for p in (out_dir / cam).glob("*.png"))
        assert names == ["frame0000.png", "frame0001.png", "frame0002.png"]
        assert sorted(names) == natsorted(names)


def test_step_is_passed_through(tmp_path, monkeypatch, module) -> None:
    """The fake iterate_frames is called with step=30 when --step is omitted."""
    frames_by_camera = {"camA": [_make_frame(1)]}
    fake_vs_cls = _make_fake_video_set(frames_by_camera)
    monkeypatch.setattr(module, "VideoSet", fake_vs_cls)
    _patch_discovery(monkeypatch, module, list(frames_by_camera))

    out_dir = tmp_path / "out"
    rc = module.main(["--video-dir", str(tmp_path), "--out-dir", str(out_dir)])

    assert rc == 0
    assert fake_vs_cls.captured_steps == [30]


def test_zero_frame_camera_is_nonzero_exit(tmp_path, monkeypatch, module) -> None:
    """A camera whose fake frames are all None makes main() return 1."""
    frames_by_camera = {
        "camA": [_make_frame(1), _make_frame(2)],
        "camB": [None, None],
    }
    fake_vs_cls = _make_fake_video_set(frames_by_camera)
    monkeypatch.setattr(module, "VideoSet", fake_vs_cls)
    _patch_discovery(monkeypatch, module, list(frames_by_camera))

    out_dir = tmp_path / "out"
    rc = module.main(
        ["--video-dir", str(tmp_path), "--out-dir", str(out_dir), "--step", "1"]
    )

    assert rc == 1
    assert list((out_dir / "camB").glob("*.png")) == []


def test_ragged_counts_rejected_without_flag(tmp_path, monkeypatch, module) -> None:
    """Unequal per-camera counts return 1, unless --allow-ragged is passed."""
    frames_by_camera = {
        "camA": [_make_frame(1), _make_frame(2), _make_frame(3)],
        "camB": [_make_frame(4), _make_frame(5), None],
    }
    fake_vs_cls = _make_fake_video_set(frames_by_camera)
    monkeypatch.setattr(module, "VideoSet", fake_vs_cls)
    _patch_discovery(monkeypatch, module, list(frames_by_camera))

    out_dir = tmp_path / "out"
    rc = module.main(
        ["--video-dir", str(tmp_path), "--out-dir", str(out_dir), "--step", "1"]
    )
    assert rc == 1

    out_dir_ragged = tmp_path / "out_ragged"
    rc_ragged = module.main(
        [
            "--video-dir",
            str(tmp_path),
            "--out-dir",
            str(out_dir_ragged),
            "--step",
            "1",
            "--allow-ragged",
        ]
    )
    assert rc_ragged == 0


def test_written_pngs_round_trip_lossless(tmp_path, monkeypatch, module) -> None:
    """A written PNG reads back bit-exact to the original array (D-07)."""
    import cv2

    original = _make_frame(42)
    frames_by_camera = {"camA": [original]}
    fake_vs_cls = _make_fake_video_set(frames_by_camera)
    monkeypatch.setattr(module, "VideoSet", fake_vs_cls)
    _patch_discovery(monkeypatch, module, list(frames_by_camera))

    out_dir = tmp_path / "out"
    rc = module.main(
        ["--video-dir", str(tmp_path), "--out-dir", str(out_dir), "--step", "1"]
    )
    assert rc == 0

    written = cv2.imread(str(out_dir / "camA" / "frame0000.png"))
    assert np.array_equal(written, original)
