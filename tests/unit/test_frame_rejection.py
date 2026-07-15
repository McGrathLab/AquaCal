"""Tests for automatic per-frame outlier rejection."""

import sys

import numpy as np
import pytest

from aquacal.calibration.frame_rejection import (
    compute_per_frame_rms,
    drop_frames,
    identify_outlier_frames,
)
from aquacal.calibration.interface_estimation import _compute_initial_board_poses
from aquacal.calibration.pipeline import _estimate_validation_poses
from aquacal.config.schema import (
    BoardConfig,
    BoardPose,
    CameraExtrinsics,
    CameraIntrinsics,
    Detection,
    DetectionResult,
    FrameDetections,
)
from aquacal.core.board import BoardGeometry

sys.path.insert(0, ".")
from tests.synthetic.ground_truth import generate_synthetic_detections


# ---------------------------------------------------------------------------
# identify_outlier_frames: threshold math + guardrail
# ---------------------------------------------------------------------------
class TestIdentifyOutlierFrames:
    def test_no_outliers_on_clean_data(self):
        """Clean data (all near median) rejects nothing."""
        per_frame = {i: 1.2 + 0.1 * (i % 3) for i in range(20)}
        res = identify_outlier_frames(per_frame, k=5.0, absolute_floor_px=5.0)
        assert res.rejected_frames == []
        assert not res.guardrail_triggered
        assert res.num_evaluated == 20

    def test_flags_catastrophic_outliers(self):
        """A couple of catastrophic frames are flagged; normal ones are not."""
        per_frame = {i: 1.3 for i in range(30)}
        per_frame[0] = 45.0
        per_frame[5] = 32.0
        res = identify_outlier_frames(per_frame, k=5.0, absolute_floor_px=5.0)
        assert res.rejected_frames == [0, 5]
        assert not res.guardrail_triggered
        # threshold = max(5 * median(~1.3), 5.0) = 6.5
        assert res.threshold_px == pytest.approx(6.5, abs=1e-6)

    def test_absolute_floor_prevents_over_rejection(self):
        """With a tiny median, the absolute floor keeps mid-range frames safe."""
        # median ~0.3 px -> relative bound 5*0.3 = 1.5 px would wrongly flag 2 px
        per_frame = {i: 0.3 for i in range(10)}
        per_frame[3] = 2.0  # above relative bound (1.5) but below floor (5.0)
        res = identify_outlier_frames(per_frame, k=5.0, absolute_floor_px=5.0)
        assert res.rejected_frames == []
        assert res.threshold_px == pytest.approx(5.0)

    def test_relative_bound_applies_when_above_floor(self):
        """When the relative bound exceeds the floor, it governs rejection."""
        per_frame = {i: 4.0 for i in range(10)}  # median 4 -> relative 20
        per_frame[2] = 25.0  # above relative bound (20)
        per_frame[7] = 12.0  # above floor (5) but below relative bound (20)
        res = identify_outlier_frames(per_frame, k=5.0, absolute_floor_px=5.0)
        assert res.rejected_frames == [2]
        assert res.threshold_px == pytest.approx(20.0)

    def test_guardrail_suppresses_mass_rejection(self):
        """If too many frames would be dropped, rejection is suppressed.

        Majority stays good (so the median is not masked and frames ARE
        flagged), but the flagged fraction (3/10 = 0.30) exceeds the 0.25 cap.
        """
        per_frame = {i: 1.3 for i in range(10)}
        for i in range(3):
            per_frame[i] = 10.0  # above threshold (6.5) but not median-masking
        res = identify_outlier_frames(
            per_frame, k=5.0, absolute_floor_px=5.0, max_reject_fraction=0.25
        )
        assert res.guardrail_triggered
        assert res.rejected_frames == []

    def test_guardrail_boundary_allows_rejection_at_cap(self):
        """Rejecting exactly at the cap fraction is allowed (strict >)."""
        per_frame = {i: 1.3 for i in range(10)}
        per_frame[0] = 50.0  # 1/10 = 0.1 <= 0.25
        res = identify_outlier_frames(
            per_frame, k=5.0, absolute_floor_px=5.0, max_reject_fraction=0.25
        )
        assert not res.guardrail_triggered
        assert res.rejected_frames == [0]

    def test_empty_input(self):
        res = identify_outlier_frames({})
        assert res.rejected_frames == []
        assert res.num_evaluated == 0
        assert not res.guardrail_triggered

    def test_invalid_params(self):
        with pytest.raises(ValueError):
            identify_outlier_frames({0: 1.0}, k=0.0)
        with pytest.raises(ValueError):
            identify_outlier_frames({0: 1.0}, max_reject_fraction=0.0)
        with pytest.raises(ValueError):
            identify_outlier_frames({0: 1.0}, max_reject_fraction=1.5)

    def test_to_diagnostics_dict(self):
        # 10 frames so a single rejection (1/10 = 0.1) is within the guardrail.
        per_frame = {i: 1.2 + 0.1 * (i % 2) for i in range(10)}
        per_frame[0] = 45.0
        res = identify_outlier_frames(per_frame, k=5.0, absolute_floor_px=5.0)
        d = res.to_diagnostics_dict()
        assert d["enabled"] is True
        assert d["rejected_frames"] == [0]
        assert d["num_rejected"] == 1
        assert d["num_evaluated"] == 10
        assert d["guardrail_triggered"] is False
        assert "0" in d["rejected_frame_rms_px"]
        assert d["rejected_frame_rms_px"]["0"] == pytest.approx(45.0)


# ---------------------------------------------------------------------------
# drop_frames
# ---------------------------------------------------------------------------
class TestDropFrames:
    def _make_detections(self, frame_indices):
        frames = {}
        for idx in frame_indices:
            det = Detection(
                corner_ids=np.array([0, 1], dtype=np.int32),
                corners_2d=np.zeros((2, 2), dtype=np.float64),
            )
            frames[idx] = FrameDetections(frame_idx=idx, detections={"cam0": det})
        return DetectionResult(
            frames=frames, camera_names=["cam0"], total_frames=len(frames)
        )

    def test_drops_requested_frames(self):
        dets = self._make_detections([0, 30, 60, 90])
        out = drop_frames(dets, [0, 60])
        assert sorted(out.frames.keys()) == [30, 90]
        assert out.total_frames == 2

    def test_original_unmodified(self):
        dets = self._make_detections([0, 30, 60])
        _ = drop_frames(dets, [0])
        assert sorted(dets.frames.keys()) == [0, 30, 60]

    def test_drop_nothing(self):
        dets = self._make_detections([0, 30])
        out = drop_frames(dets, [])
        assert sorted(out.frames.keys()) == [0, 30]


# ---------------------------------------------------------------------------
# compute_per_frame_rms with synthetic data
# ---------------------------------------------------------------------------
@pytest.fixture
def board_config() -> BoardConfig:
    return BoardConfig(
        squares_x=6,
        squares_y=5,
        square_size=0.04,
        marker_size=0.03,
        dictionary="DICT_4X4_50",
    )


@pytest.fixture
def board(board_config) -> BoardGeometry:
    return BoardGeometry(board_config)


@pytest.fixture
def intrinsics() -> dict[str, CameraIntrinsics]:
    K = np.array([[500, 0, 320], [0, 500, 240], [0, 0, 1]], dtype=np.float64)
    dist = np.zeros(5, dtype=np.float64)
    return {
        "cam0": CameraIntrinsics(
            K=K.copy(), dist_coeffs=dist.copy(), image_size=(640, 480)
        ),
        "cam1": CameraIntrinsics(
            K=K.copy(), dist_coeffs=dist.copy(), image_size=(640, 480)
        ),
    }


@pytest.fixture
def extrinsics() -> dict[str, CameraExtrinsics]:
    return {
        "cam0": CameraExtrinsics(
            R=np.eye(3, dtype=np.float64), t=np.zeros(3, dtype=np.float64)
        ),
        "cam1": CameraExtrinsics(
            R=np.eye(3, dtype=np.float64),
            t=np.array([0.08, 0.0, 0.0], dtype=np.float64),
        ),
    }


@pytest.fixture
def distances() -> dict[str, float]:
    return {"cam0": 0.15, "cam1": 0.16}


@pytest.fixture
def board_poses() -> list[BoardPose]:
    poses = []
    for i in range(5):
        x_offset = 0.03 * (i % 3 - 1)
        poses.append(
            BoardPose(
                frame_idx=i,
                rvec=np.array([0.05 * i, 0.0, 0.0], dtype=np.float64),
                tvec=np.array([x_offset, 0.0, 0.35], dtype=np.float64),
            )
        )
    return poses


class TestComputePerFrameRms:
    def test_perfect_data_near_zero(
        self, intrinsics, extrinsics, distances, board, board_poses
    ):
        detections = generate_synthetic_detections(
            intrinsics,
            extrinsics,
            distances,
            board,
            board_poses,
            noise_std=0.0,
            min_corners=4,
        )
        per_frame = compute_per_frame_rms(
            detections=detections,
            intrinsics=intrinsics,
            extrinsics=extrinsics,
            distances=distances,
            board_poses=board_poses,
            board=board,
            interface_normal=np.array([0.0, 0.0, -1.0]),
            n_air=1.0,
            n_water=1.333,
        )
        assert len(per_frame) > 0
        for rms in per_frame.values():
            assert rms < 1e-6

    def test_corrupted_pose_produces_high_rms(
        self, intrinsics, extrinsics, distances, board, board_poses
    ):
        """A frame whose board pose is wrong shows a large per-frame RMS,
        and identify_outlier_frames flags exactly that frame."""
        detections = generate_synthetic_detections(
            intrinsics,
            extrinsics,
            distances,
            board,
            board_poses,
            noise_std=0.0,
            min_corners=4,
        )
        # Corrupt the pose used for reprojection of frame 2 (simulates a bad
        # board pose from a contaminated frame the optimizer couldn't fit).
        corrupted = list(board_poses)
        bad = corrupted[2]
        corrupted[2] = BoardPose(
            frame_idx=bad.frame_idx,
            rvec=bad.rvec.copy(),
            tvec=bad.tvec + np.array([0.05, 0.05, 0.0]),
        )
        per_frame = compute_per_frame_rms(
            detections=detections,
            intrinsics=intrinsics,
            extrinsics=extrinsics,
            distances=distances,
            board_poses=corrupted,
            board=board,
            interface_normal=np.array([0.0, 0.0, -1.0]),
            n_air=1.0,
            n_water=1.333,
        )
        assert per_frame[2] > 10.0
        others = [rms for idx, rms in per_frame.items() if idx != 2]
        assert all(o < 1e-3 for o in others)

        res = identify_outlier_frames(per_frame, k=5.0, absolute_floor_px=5.0)
        assert res.rejected_frames == [2]


class TestIndependentPoseRejectionEndToEnd:
    """Regression guard for the pose-source bug.

    A geometrically-inconsistent frame (different cameras see the board at
    different poses, as happens near the surface where refraction breaks down)
    cannot be reconciled by a single independently-fitted per-frame pose, so it
    surfaces at a large RMS and is rejected. This mirrors the pipeline flow
    (per-frame PnP + refine -> per-frame RMS -> reject) and would have caught the
    bug where jointly-optimized poses masked the outlier.
    """

    def _six_good_poses(self):
        poses = []
        for i in range(6):
            x_offset = 0.02 * (i % 3 - 1)
            poses.append(
                BoardPose(
                    frame_idx=i,
                    rvec=np.array([0.03 * i, 0.0, 0.0], dtype=np.float64),
                    tvec=np.array([x_offset, 0.0, 0.35], dtype=np.float64),
                )
            )
        return poses

    def test_inconsistent_frame_is_rejected_via_independent_poses(
        self, intrinsics, extrinsics, distances, board
    ):
        poses = self._six_good_poses()

        # Consistent detections for all frames.
        good = generate_synthetic_detections(
            intrinsics,
            extrinsics,
            distances,
            board,
            poses,
            noise_std=0.0,
            min_corners=4,
        )

        # Build an INCONSISTENT frame 2: cam0 sees pose A, cam1 sees a very
        # different pose B. No single board pose can satisfy both cameras.
        pose_a = poses[2]
        pose_b = BoardPose(
            frame_idx=2,
            rvec=np.array([0.5, 0.4, 0.0], dtype=np.float64),
            tvec=np.array([0.06, 0.05, 0.34], dtype=np.float64),
        )
        det_a = generate_synthetic_detections(
            {"cam0": intrinsics["cam0"]},
            {"cam0": extrinsics["cam0"]},
            {"cam0": distances["cam0"]},
            board,
            [pose_a],
            noise_std=0.0,
            min_corners=4,
        )
        det_b = generate_synthetic_detections(
            {"cam1": intrinsics["cam1"]},
            {"cam1": extrinsics["cam1"]},
            {"cam1": distances["cam1"]},
            board,
            [pose_b],
            noise_std=0.0,
            min_corners=4,
        )
        # Both single-camera sets are keyed by the pose's frame_idx (== 2).
        merged = dict(good.frames[2].detections)
        merged["cam0"] = det_a.frames[2].detections["cam0"]
        merged["cam1"] = det_b.frames[2].detections["cam1"]
        good.frames[2] = FrameDetections(frame_idx=2, detections=merged)

        normal = np.array([0.0, 0.0, -1.0])

        # Pipeline-style INDEPENDENT per-frame pose estimation.
        init = _compute_initial_board_poses(
            good, intrinsics, extrinsics, board, 4, distances, normal, 1.0, 1.333
        )
        independent = _estimate_validation_poses(
            good,
            init,
            intrinsics,
            extrinsics,
            distances,
            board,
            normal,
            1.0,
            1.333,
        )

        per_frame = compute_per_frame_rms(
            detections=good,
            intrinsics=intrinsics,
            extrinsics=extrinsics,
            distances=distances,
            board_poses=list(independent.values()),
            board=board,
            interface_normal=normal,
            n_air=1.0,
            n_water=1.333,
        )

        # The inconsistent frame stands out far above the others.
        assert 2 in per_frame
        others = [rms for idx, rms in per_frame.items() if idx != 2]
        assert per_frame[2] > 5.0
        assert per_frame[2] > 3 * (max(others) if others else 0.0)

        res = identify_outlier_frames(per_frame, k=5.0, absolute_floor_px=5.0)
        assert 2 in res.rejected_frames
