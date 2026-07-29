"""Unit tests for `experiments/e5_index_sensitivity.py`.

Fast, hand-built-fixture tests only (matching `test_experiments_e1.py`'s
discipline): no `create_scenario`, no `calibrate_synthetic`/
`optimize_interface`, nothing marked slow.
"""

from __future__ import annotations

import json
import re
from types import SimpleNamespace

import pandas as pd
import pytest

from experiments.e1_refractive_comparison import compute_scale_bias
from experiments.e5_index_sensitivity import (
    E5_COLUMNS,
    add_control_columns,
    add_holdout_floor_columns,
    build_row,
    load_holdout_floor_pct,
)

SQUARE_SIZE_M = 0.060


def _make_evaluation(
    reprojection_rms=0.5,
    mean=0.0005,
    rmse=0.0006,
    signed_mean=0.0003,
    num_comparisons=100,
    num_frames=10,
):
    """Build a `HeldOutEvaluation`-shaped fixture without touching the real dataclass."""
    reconstruction = SimpleNamespace(
        mean=mean,
        rmse=rmse,
        signed_mean=signed_mean,
        num_comparisons=num_comparisons,
    )
    reprojection = SimpleNamespace(rms=reprojection_rms)
    return SimpleNamespace(
        reprojection=reprojection,
        reconstruction=reconstruction,
        num_frames=num_frames,
    )


def test_e5_row_schema():
    """The row builder over a hand-built fixture returns exactly E5_COLUMNS, in order."""
    evaluation = _make_evaluation()
    row = build_row(
        evaluation,
        n_assumed=1.335,
        n_true=1.333,
        seed=42,
        square_size_m=SQUARE_SIZE_M,
    )
    assert list(row.keys()) == E5_COLUMNS


def test_scale_bias_matches_e1_committed_column():
    """compute_scale_bias reproduces at least 3 committed exp2_depth_generalization.csv rows."""
    df = pd.read_csv("experiments/results/exp2_depth_generalization.csv")
    sample = df.head(3)
    for _, row in sample.iterrows():
        signed_mean_m = row["signed_mean_mm"] / 1000.0
        expected = row["scale_factor"]
        actual = compute_scale_bias(signed_mean_m, SQUARE_SIZE_M)
        assert actual == pytest.approx(expected, rel=1e-9)


def test_noise_floor_read_live(tmp_path):
    """load_holdout_floor_pct reads inter_corner_rmse_mm live and divides by square size (mm)."""
    metrics_path = tmp_path / "real_rig_metrics.json"
    metrics_path.write_text(json.dumps({"inter_corner_rmse_mm": 0.674}))

    result = load_holdout_floor_pct(metrics_path, SQUARE_SIZE_M)

    expected = (0.674 / (SQUARE_SIZE_M * 1000.0)) * 100.0
    assert result == pytest.approx(expected, rel=1e-9)

    # These literals must never appear hardcoded in the module -- the value
    # must come from a live read of the (test-local) metrics file, never a
    # fabricated default. 1.123 is the WP4 percentage (0.674 / 60 * 100).
    with open("experiments/e5_index_sensitivity.py") as f:
        source = f.read()
    assert "0.674" not in source
    assert "1.123" not in source
    assert not re.search(r"=\s*60\b", source)


def test_noise_floor_missing_file_returns_none(tmp_path):
    """A missing metrics file degrades to None, never a fabricated value."""
    missing_path = tmp_path / "does_not_exist.json"
    result = load_holdout_floor_pct(missing_path, SQUARE_SIZE_M)
    assert result is None


def test_delta_n_columns():
    """delta_n == n_assumed - n_true; delta_n_over_n == delta_n / n_true."""
    evaluation = _make_evaluation()
    row = build_row(
        evaluation,
        n_assumed=1.341,
        n_true=1.333,
        seed=42,
        square_size_m=SQUARE_SIZE_M,
    )
    expected_delta_n = 1.341 - 1.333
    assert row["delta_n"] == pytest.approx(expected_delta_n)
    assert row["delta_n_over_n"] == pytest.approx(expected_delta_n / 1.333)


def test_control_columns_derive_from_zero_delta_row():
    """scale_bias_pct_control is identical on every row and equals the control row's
    own scale_bias_pct; bias_over_control is abs(scale_bias_pct - control), including
    exactly 0.0 on the control row itself."""
    n_true = 1.333
    band = [1.323, n_true, 1.343]
    rows = []
    for n_assumed in band:
        evaluation = _make_evaluation(signed_mean=0.0001 * (n_assumed - n_true) * 1000)
        rows.append(
            build_row(
                evaluation,
                n_assumed=n_assumed,
                n_true=n_true,
                seed=42,
                square_size_m=SQUARE_SIZE_M,
            )
        )
    df = pd.DataFrame(rows, columns=E5_COLUMNS)

    out = add_control_columns(df, n_true)

    assert out["scale_bias_pct_control"].nunique() == 1
    control_row = out[out["n_assumed"] == n_true].iloc[0]
    assert control_row["scale_bias_pct_control"] == pytest.approx(
        control_row["scale_bias_pct"]
    )
    assert control_row["bias_over_control"] == pytest.approx(0.0, abs=1e-12)

    expected_bias_over_control = (
        out["scale_bias_pct"] - out["scale_bias_pct_control"]
    ).abs()
    pd.testing.assert_series_equal(
        out["bias_over_control"],
        expected_bias_over_control,
        check_names=False,
    )


def test_holdout_floor_columns_fill_from_live_read(tmp_path):
    """add_holdout_floor_columns fills holdout_floor_pct/scale_bias_over_floor live."""
    metrics_path = tmp_path / "real_rig_metrics.json"
    metrics_path.write_text(json.dumps({"inter_corner_rmse_mm": 0.674}))

    evaluation = _make_evaluation()
    row = build_row(
        evaluation, n_assumed=1.335, n_true=1.333, seed=42, square_size_m=SQUARE_SIZE_M
    )
    df = pd.DataFrame([row], columns=E5_COLUMNS)

    out = add_holdout_floor_columns(df, metrics_path, SQUARE_SIZE_M)

    expected_floor = (0.674 / (SQUARE_SIZE_M * 1000.0)) * 100.0
    assert out.loc[0, "holdout_floor_pct"] == pytest.approx(expected_floor, rel=1e-9)
    expected_ratio = abs(out.loc[0, "scale_bias_pct"]) / expected_floor
    assert out.loc[0, "scale_bias_over_floor"] == pytest.approx(
        expected_ratio, rel=1e-9
    )


def test_seed_column_populated():
    """Every row of a hand-built frame carries a non-null seed."""
    n_true = 1.333
    rows = []
    for n_assumed in [1.323, n_true, 1.343]:
        evaluation = _make_evaluation()
        rows.append(
            build_row(
                evaluation,
                n_assumed=n_assumed,
                n_true=n_true,
                seed=123,
                square_size_m=SQUARE_SIZE_M,
            )
        )
    df = pd.DataFrame(rows, columns=E5_COLUMNS)
    assert df["seed"].notnull().all()
    assert (df["seed"] == 123).all()


def test_no_pass_fail_column():
    """E5_COLUMNS contains no column whose name implies a verdict."""
    verdict_pattern = re.compile(r"pass|fail|verdict|acceptable", re.IGNORECASE)
    assert not any(verdict_pattern.search(c) for c in E5_COLUMNS)
