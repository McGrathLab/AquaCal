"""Unit tests for `experiments/e6_generalization_sweep.py` (EXP-10).

Fast unit tests only: hand-built fixtures directly constructed, no actual
calibration solve of any kind, none marked slow. `--smoke` (which does
exercise a real, small solve) is verified separately by the plan's own
`<verify>` block, not by pytest.
"""

from __future__ import annotations

import re

import pandas as pd
import pytest

import experiments.e4_benchmark_grid as e4
import experiments.e6_generalization_sweep as m


def _sample_metrics() -> dict:
    """A hand-built metrics dict with exactly `_METRIC_COLUMNS`' keys."""
    return {
        "reprojection_rms_px": 0.42,
        "reconstruction_mae_mm": 1.1,
        "reconstruction_rmse_mm": 1.5,
        "signed_mean_mm": -0.2,
        "focal_error_pct_mean": 0.05,
        "xy_position_error_mm_mean": 0.3,
        "z_position_error_mm_mean": 0.4,
        "water_z_error_mm_mean": 0.6,
        "num_comparisons": 1000,
        "num_frames": 20,
    }


def test_e6_row_schema():
    """The row builder over a hand-built metrics fixture returns exactly E6_COLUMNS, in order."""
    configs = m.build_axis_configurations()
    config = configs[0]
    row = m.build_row(
        config,
        seed=42,
        n_frames=10,
        metrics=_sample_metrics(),
        status="ok",
        status_reason="",
    )
    assert list(row.keys()) == m.E6_COLUMNS
    assert row["axis"] in {"index", "layout", "scale"}


def test_every_axis_passes_through_baseline():
    """Each axis's config list contains exactly one is_baseline=True entry at the baseline value."""
    configs = m.build_axis_configurations()
    baseline_by_axis = {
        "index": str(m.BASELINE_N_WATER),
        "layout": m.BASELINE_LAYOUT,
        "scale": m.BASELINE_SCALE,
    }
    for axis, baseline_value in baseline_by_axis.items():
        axis_configs = [c for c in configs if c["axis"] == axis]
        baseline_entries = [c for c in axis_configs if c["is_baseline"]]
        assert len(baseline_entries) == 1
        assert baseline_entries[0]["axis_value"] == baseline_value


def test_baseline_scene_is_shared():
    """The three baseline configurations share one config_key (computed once, review M7)."""
    configs = m.build_axis_configurations()
    baseline_keys = {c["config_key"] for c in configs if c["is_baseline"]}
    assert baseline_keys == {"baseline"}
    assert sum(1 for c in configs if c["is_baseline"]) == 3


def test_no_verdict_column():
    """No E6_COLUMNS name implies a pass/fail verdict (D-12)."""
    pattern = re.compile(r"pass|fail|verdict|acceptable|holds|degraded")
    assert not any(pattern.search(c) for c in m.E6_COLUMNS)


def test_water_z_error_helper():
    """A known 3mm discrepancy on one camera, 0 on the rest, gives the expected mm mean."""
    true_water_zs = {"cam0": 1.0, "cam1": 1.0, "cam2": 1.0}
    estimated_water_zs = {"cam0": 1.0, "cam1": 1.003, "cam2": 1.0}
    result = m.compute_water_z_error_mm_mean(estimated_water_zs, true_water_zs)
    assert result == pytest.approx(1.0, abs=1e-6)


def test_tilt_configuration_matches_e4():
    """The imported GRID_NORMAL_FIXED is E4's own constant, is False, and lands on every row."""
    assert m.GRID_NORMAL_FIXED is e4.GRID_NORMAL_FIXED
    assert m.GRID_NORMAL_FIXED is False

    configs = m.build_axis_configurations()
    rows = [
        m.build_row(
            c,
            seed=42,
            n_frames=10,
            metrics=_sample_metrics(),
            status="ok",
            status_reason="",
        )
        for c in configs
    ]
    df = pd.DataFrame(rows, columns=m.E6_COLUMNS)
    assert (df["normal_fixed"] == m.GRID_NORMAL_FIXED).all()


def test_seed_column_populated():
    """Every row of a hand-built frame carries a non-null seed."""
    configs = m.build_axis_configurations()
    rows = [
        m.build_row(
            c,
            seed=7,
            n_frames=10,
            metrics=_sample_metrics(),
            status="ok",
            status_reason="",
        )
        for c in configs
    ]
    df = pd.DataFrame(rows, columns=m.E6_COLUMNS)
    assert df["seed"].notna().all()


def test_camera_count_not_swept():
    """Every configuration's n_cameras equals BASELINE_N_CAMERAS (camera count is E4's axis, D-11)."""
    configs = m.build_axis_configurations()
    assert all(c["n_cameras"] == m.BASELINE_N_CAMERAS for c in configs)


def test_status_vocabulary():
    """The row builder's status values come from {ok, failed, skipped_existing}."""
    assert m.STATUS_VALUES == {"ok", "failed", "skipped_existing"}
    configs = m.build_axis_configurations()
    config = configs[0]
    for status in sorted(m.STATUS_VALUES):
        row = m.build_row(
            config,
            seed=42,
            n_frames=10,
            metrics=_sample_metrics() if status == "ok" else None,
            status=status,
            status_reason="" if status == "ok" else "reason",
        )
        assert row["status"] in m.STATUS_VALUES
        if status != "ok":
            for col in m._METRIC_COLUMNS:
                assert row[col] is None
