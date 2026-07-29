"""Unit tests for `experiments/e5_index_sensitivity.py`.

Fast, hand-built-fixture tests only (matching `test_experiments_e1.py`'s
discipline): no `create_scenario`, no `calibrate_synthetic`/
`optimize_interface`, nothing marked slow.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import pandas as pd
import pytest

from aquacal.io import capture_environment
from experiments.e1_refractive_comparison import compute_scale_bias
from experiments.e5_index_sensitivity import (
    E5_COLUMNS,
    E5_N_FRAMES,
    E5_NORMAL_FIXED,
    E5_REFINE_INTRINSICS,
    HOLDOUT_SEED_OFFSET,
    N_ASSUMED_BAND,
    N_TRUE,
    add_control_columns,
    add_holdout_floor_columns,
    build_provenance_sidecar,
    build_row,
    load_holdout_floor_pct,
)
from tests.unit.test_experiments_provenance import (
    REQUIRED_ENVIRONMENT_KEYS,
    _record_seed,
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


class TestProvenanceSidecar:
    """Task 1: `build_provenance_sidecar` carries the four EXP-11 fields plus
    the run configuration WR-04 says index_sensitivity.csv cannot
    reconstruct on its own."""

    def test_sidecar_carries_the_four_exp11_fields(self):
        sidecar = build_provenance_sidecar(seed=42)
        assert sidecar["experiment"] == "e5"
        assert "schema_version" in sidecar
        assert sidecar["seed"] == 42
        assert sidecar["solver_config"]["seed"] == 42
        expected_keys = set(capture_environment().keys())
        assert set(sidecar["environment"].keys()) == expected_keys
        missing = REQUIRED_ENVIRONMENT_KEYS - set(sidecar["environment"])
        assert not missing, f"sidecar environment missing keys {missing}"

    def test_sidecar_carries_the_run_configuration_matching_module_constants(self):
        """Every configuration value in the sidecar equals the value the
        module itself uses, read from the module -- not restated as a
        literal in this test (per the plan's acceptance criteria)."""
        sidecar = build_provenance_sidecar(seed=7)
        assert sidecar["refine_intrinsics"] == E5_REFINE_INTRINSICS
        assert sidecar["normal_fixed"] == E5_NORMAL_FIXED
        assert sidecar["n_frames"] == E5_N_FRAMES
        assert sidecar["n_assumed_band"] == list(N_ASSUMED_BAND)
        assert sidecar["n_true"] == N_TRUE
        assert sidecar["holdout_seed_offset"] == HOLDOUT_SEED_OFFSET

    def test_sidecar_passes_the_provenance_suites_own_checks(self, tmp_path):
        """Write the sidecar to tmp_path and assert it would pass
        TestEnvironmentPresence and TestSeedProvenance exactly as those
        checks are written in test_experiments_provenance.py."""
        sidecar = build_provenance_sidecar(seed=99)
        sidecar_path = tmp_path / "e5_provenance.json"
        sidecar_path.write_text(json.dumps(sidecar, sort_keys=True))

        record = json.loads(sidecar_path.read_text())

        # TestEnvironmentPresence.test_every_benchmark_record_has_environment
        assert "environment" in record
        missing = REQUIRED_ENVIRONMENT_KEYS - set(record["environment"])
        assert not missing

        # TestSeedProvenance.test_every_benchmark_record_carries_a_seed
        assert _record_seed(record) is not None

    def test_refine_intrinsics_defaulted_false_for_the_production_band(self):
        """The production band ran with intrinsics pinned at ground truth --
        the sidecar must record that value, not silently change it."""
        assert E5_REFINE_INTRINSICS is False


class TestDefaultMetricsPathAnchoring:
    """Task 2 (WR-06): `_default_metrics_path` must not depend on cwd."""

    def test_resolves_to_the_same_path_from_two_different_working_directories(
        self, tmp_path, monkeypatch
    ):
        from experiments.e5_index_sensitivity import _default_metrics_path

        original_cwd = Path.cwd()

        monkeypatch.chdir(tmp_path)
        path_from_tmp = _default_metrics_path()

        monkeypatch.chdir(original_cwd)
        path_from_original = _default_metrics_path()

        assert path_from_tmp == path_from_original
        assert path_from_tmp.is_absolute()

    def test_resolves_to_an_existing_file_from_a_foreign_directory(
        self, tmp_path, monkeypatch
    ):
        """Invoked from a directory OTHER than the repository root (a fresh
        tmp_path), the resolved path must still be absolute and exist."""
        from experiments.e5_index_sensitivity import _default_metrics_path

        monkeypatch.chdir(tmp_path)
        resolved = _default_metrics_path()
        assert resolved.is_absolute()
        assert resolved.exists(), resolved


class TestCheckGuardsMissingBaseline:
    """Task 2 (WR-12): `--check` must not re-run the band when there is no
    committed baseline to compare against."""

    def test_run_check_reports_missing_baseline_without_running_the_band(
        self, tmp_path
    ):
        from argparse import Namespace

        from experiments.e5_index_sensitivity import _run_check

        args = Namespace(out=tmp_path, seed=42, force=False, smoke=False, check=True)

        with patch("experiments.e5_index_sensitivity.run_band") as mock_run_band:
            exit_code = _run_check(args)

        assert exit_code != 0
        mock_run_band.assert_not_called()
