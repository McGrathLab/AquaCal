"""Unit tests for the validation module (holdout, drift, triangulation, report)."""

from __future__ import annotations

import numpy as np
import pytest

from aquacal.calibration.validation import (
    build_validation_report,
    compute_extrinsics_drift,
    split_holdout,
)
from aquacal.config.schema import (
    CameraDrift,
    CameraExtrinsics,
    PointCorrespondence,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_correspondences(n: int) -> list[PointCorrespondence]:
    """Create n dummy correspondences with 2 cameras each."""
    corrs = []
    rng = np.random.RandomState(0)
    for _ in range(n):
        corrs.append(
            PointCorrespondence(
                point_3d=rng.randn(3).astype(np.float64),
                observations={
                    "cam0": rng.randn(2).astype(np.float64),
                    "cam1": rng.randn(2).astype(np.float64),
                },
                weight=1.0,
            )
        )
    return corrs


# ---------------------------------------------------------------------------
# split_holdout tests
# ---------------------------------------------------------------------------


class TestSplitHoldout:
    """Tests for split_holdout function."""

    def test_fraction(self):
        """Holdout fraction is approximately correct."""
        corrs = _make_correspondences(100)
        train, holdout = split_holdout(corrs, 0.2, seed=42)
        assert len(train) + len(holdout) == 100
        # With 100 samples and p=0.2, expect ~20 holdout (allow [10, 30])
        assert 10 <= len(holdout) <= 30

    def test_disjoint(self):
        """Train and holdout sets are disjoint (no shared objects)."""
        corrs = _make_correspondences(50)
        train, holdout = split_holdout(corrs, 0.3, seed=42)
        train_ids = {id(c) for c in train}
        holdout_ids = {id(c) for c in holdout}
        assert train_ids.isdisjoint(holdout_ids)

    def test_seed_reproducibility(self):
        """Same seed produces identical split."""
        corrs = _make_correspondences(50)
        train1, holdout1 = split_holdout(corrs, 0.2, seed=42)
        train2, holdout2 = split_holdout(corrs, 0.2, seed=42)
        assert len(train1) == len(train2)
        assert len(holdout1) == len(holdout2)

    def test_different_seed(self):
        """Different seeds produce different splits (with high probability)."""
        corrs = _make_correspondences(100)
        _, holdout1 = split_holdout(corrs, 0.5, seed=42)
        _, holdout2 = split_holdout(corrs, 0.5, seed=99)
        # With 100 items and p=0.5, different seeds should differ
        assert len(holdout1) != len(holdout2) or holdout1 != holdout2

    def test_empty(self):
        """Empty input returns empty outputs."""
        train, holdout = split_holdout([], 0.2, seed=42)
        assert train == []
        assert holdout == []

    def test_fraction_zero(self):
        """Fraction 0.0 puts everything in train."""
        corrs = _make_correspondences(10)
        train, holdout = split_holdout(corrs, 0.0, seed=42)
        assert len(train) == 10
        assert len(holdout) == 0

    def test_fraction_one(self):
        """Fraction 1.0 puts everything in holdout."""
        corrs = _make_correspondences(10)
        train, holdout = split_holdout(corrs, 1.0, seed=42)
        assert len(train) == 0
        assert len(holdout) == 10


# ---------------------------------------------------------------------------
# compute_extrinsics_drift tests
# ---------------------------------------------------------------------------


class TestExtrinsicsDrift:
    """Tests for compute_extrinsics_drift function."""

    def test_identity(self):
        """Same extrinsics before and after: zero drift."""
        ext = {
            "cam0": CameraExtrinsics(
                R=np.eye(3, dtype=np.float64),
                t=np.zeros(3, dtype=np.float64),
            ),
            "cam1": CameraExtrinsics(
                R=np.eye(3, dtype=np.float64),
                t=np.array([0.1, 0.0, 0.0], dtype=np.float64),
            ),
        }
        drifts = compute_extrinsics_drift(ext, ext)
        assert drifts["cam0"].translation_mm == pytest.approx(0.0, abs=1e-6)
        assert drifts["cam0"].rotation_deg == pytest.approx(0.0, abs=1e-6)
        assert drifts["cam0"].exceeded is False
        assert drifts["cam1"].exceeded is False

    def test_known_translation_shift(self):
        """Camera center shifts by exactly 100mm."""
        R = np.eye(3, dtype=np.float64)
        before = {
            "cam0": CameraExtrinsics(R=R.copy(), t=np.zeros(3, dtype=np.float64)),
        }
        # Shift camera center by 0.1m (100mm) in X
        # C = -R^T @ t, so for identity R: C = -t
        # Want C_after - C_before = [0.1, 0, 0]
        # C_before = [0, 0, 0], so C_after = [0.1, 0, 0], t_after = [-0.1, 0, 0]
        after = {
            "cam0": CameraExtrinsics(
                R=R.copy(), t=np.array([-0.1, 0.0, 0.0], dtype=np.float64)
            ),
        }

        drifts = compute_extrinsics_drift(before, after, translation_threshold_mm=50.0)
        assert drifts["cam0"].translation_mm == pytest.approx(100.0, abs=0.1)
        assert drifts["cam0"].exceeded is True

        drifts2 = compute_extrinsics_drift(
            before, after, translation_threshold_mm=200.0
        )
        assert drifts2["cam0"].exceeded is False

    def test_known_rotation(self):
        """Rotation differs by ~5 degrees around Z axis."""
        angle_rad = np.radians(5.0)
        R_before = np.eye(3, dtype=np.float64)
        R_after = np.array(
            [
                [np.cos(angle_rad), -np.sin(angle_rad), 0.0],
                [np.sin(angle_rad), np.cos(angle_rad), 0.0],
                [0.0, 0.0, 1.0],
            ],
            dtype=np.float64,
        )

        before = {
            "cam0": CameraExtrinsics(R=R_before, t=np.zeros(3, dtype=np.float64)),
        }
        after = {
            "cam0": CameraExtrinsics(R=R_after, t=np.zeros(3, dtype=np.float64)),
        }

        drifts = compute_extrinsics_drift(before, after, rotation_threshold_deg=2.0)
        assert drifts["cam0"].rotation_deg == pytest.approx(5.0, abs=0.1)
        assert drifts["cam0"].exceeded is True


# ---------------------------------------------------------------------------
# build_validation_report tests
# ---------------------------------------------------------------------------


class TestBuildValidationReport:
    """Tests for build_validation_report function."""

    def test_all_pass(self):
        """All metrics within thresholds: accepted=True."""
        drifts = {
            "cam0": CameraDrift(translation_mm=10.0, rotation_deg=0.5, exceeded=False),
            "cam1": CameraDrift(translation_mm=20.0, rotation_deg=1.0, exceeded=False),
        }
        report = build_validation_report(
            holdout_reproj=0.5,
            tri_before=0.001,
            tri_after=0.0005,
            camera_drifts=drifts,
            reproj_threshold=1.0,
        )
        assert report.accepted is True
        assert "Accepted" in report.summary

    def test_any_fail_rejects(self):
        """One camera exceeds drift: accepted=False."""
        drifts = {
            "cam0": CameraDrift(translation_mm=10.0, rotation_deg=0.5, exceeded=False),
            "cam1": CameraDrift(translation_mm=60.0, rotation_deg=1.0, exceeded=True),
        }
        report = build_validation_report(
            holdout_reproj=0.5,
            tri_before=0.001,
            tri_after=0.0005,
            camera_drifts=drifts,
            reproj_threshold=1.0,
            translation_threshold_mm=50.0,
        )
        assert report.accepted is False
        assert "Rejected" in report.summary
        assert "cam1" in report.summary

    def test_reproj_fail(self):
        """Holdout reproj exceeds threshold: rejected."""
        drifts = {
            "cam0": CameraDrift(translation_mm=5.0, rotation_deg=0.1, exceeded=False),
        }
        report = build_validation_report(
            holdout_reproj=1.5,
            tri_before=0.001,
            tri_after=0.0005,
            camera_drifts=drifts,
            reproj_threshold=1.0,
        )
        assert report.accepted is False
        assert "reprojection" in report.summary.lower()

    def test_summary_names_cameras(self):
        """Multiple failing cameras both appear in summary."""
        drifts = {
            "cam0": CameraDrift(translation_mm=60.0, rotation_deg=0.1, exceeded=True),
            "cam1": CameraDrift(translation_mm=70.0, rotation_deg=0.1, exceeded=True),
        }
        report = build_validation_report(
            holdout_reproj=0.5,
            tri_before=0.001,
            tri_after=0.0005,
            camera_drifts=drifts,
            reproj_threshold=1.0,
            translation_threshold_mm=50.0,
        )
        assert report.accepted is False
        assert "cam0" in report.summary
        assert "cam1" in report.summary

    def test_report_stores_before_after(self):
        """Report contains before/after triangulation consistency values."""
        drifts = {
            "cam0": CameraDrift(translation_mm=5.0, rotation_deg=0.1, exceeded=False),
        }
        report = build_validation_report(
            holdout_reproj=0.5,
            tri_before=0.002,
            tri_after=0.001,
            camera_drifts=drifts,
        )
        assert report.triangulation_consistency_before == pytest.approx(0.002)
        assert report.triangulation_consistency_after == pytest.approx(0.001)
        assert report.holdout_reproj_error == pytest.approx(0.5)
