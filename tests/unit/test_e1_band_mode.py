"""Unit tests for `experiments/e1_refractive_comparison.py`'s `--seeds` band
mode (D-19.4-14, SC-5a).

Every test here runs at `--smoke` scale (the `"ideal"` scenario, single test
depth) and writes to a `tmp_path`-scoped `--out` directory -- never
`experiments/results/` and never the production 10-seed band (~57 min,
forbidden by this plan). None of these tests are marked slow.
"""

from __future__ import annotations

import json

import pandas as pd
import pytest

from experiments._io import build_experiment_arg_parser
from experiments.e1_refractive_comparison import (
    BAND_MERGED_COLUMNS,
    BENCHMARK_FILENAMES,
    EXP2_COLUMNS,
    EXP3_COLUMNS,
    MODELS,
    build_arg_parser,
    main,
    merge_band_columns,
)


class TestCli:
    def test_help_lists_seeds(self, capsys):
        with pytest.raises(SystemExit):
            main(["--help"])
        out = capsys.readouterr().out
        assert "--seeds" in out

    def test_seeds_with_check_exits_nonzero(self):
        with pytest.raises(SystemExit) as exc_info:
            main(["--seeds", "42,43", "--check"])
        assert exc_info.value.code != 0

    def test_seeds_with_check_error_names_both_flags(self, capsys):
        with pytest.raises(SystemExit):
            main(["--seeds", "42,43", "--check"])
        err = capsys.readouterr().err
        assert "--seeds" in err
        assert "--check" in err

    def test_validate_e1_args_directly_rejects_seeds_with_check(self):
        from experiments.e1_refractive_comparison import _validate_e1_args

        parser = build_arg_parser()
        args = parser.parse_args(["--seeds", "42,43", "--check"])
        with pytest.raises(SystemExit):
            _validate_e1_args(parser, args)


class TestMergeBandColumns:
    """Pure, instant tests for `merge_band_columns` -- no calibration run."""

    def _frames(self):
        df_exp2 = pd.DataFrame(
            {
                "test_depth_m": [1.1, 1.1, 1.3, 1.3],
                "model": [
                    "refractive",
                    "non_refractive",
                    "refractive",
                    "non_refractive",
                ],
                "signed_mean_mm": [1.0, 2.0, 3.0, 4.0],
                "rmse_mm": [1.1, 2.1, 3.1, 4.1],
                "scale_factor": [1.0, 1.0, 1.0, 1.0],
                "calib_depth_min_m": [0.5, 0.5, 0.5, 0.5],
                "calib_depth_max_m": [2.0, 2.0, 2.0, 2.0],
            }
        )
        df_exp3 = pd.DataFrame(
            {
                "test_depth_m": [1.1, 1.1, 1.3, 1.3],
                "model": [
                    "refractive",
                    "non_refractive",
                    "refractive",
                    "non_refractive",
                ],
                "xy_rmse_mm": [0.1, 0.2, 0.3, 0.4],
                "z_rmse_mm": [1.5, 2.5, 3.5, 4.5],
                "anisotropy_ratio": [10.0, 20.0, 30.0, 40.0],
                "n_points": [49, 49, 49, 49],
            }
        )
        return df_exp2, df_exp3

    def test_columns_are_exactly_band_merged_columns(self):
        df_exp2, df_exp3 = self._frames()
        merged = merge_band_columns(df_exp2, df_exp3)
        assert list(merged.columns) == BAND_MERGED_COLUMNS

    def test_row_count_unchanged_from_exp2(self):
        df_exp2, df_exp3 = self._frames()
        merged = merge_band_columns(df_exp2, df_exp3)
        assert len(merged) == len(df_exp2)

    def test_values_land_on_matching_key(self):
        df_exp2, df_exp3 = self._frames()
        merged = merge_band_columns(df_exp2, df_exp3)
        row = merged[
            (merged["test_depth_m"] == 1.3) & (merged["model"] == "non_refractive")
        ].iloc[0]
        assert row["z_rmse_mm"] == 4.5
        assert row["xy_rmse_mm"] == 0.4
        assert row["anisotropy_ratio"] == 40.0
        assert row["n_points"] == 49

    def test_duplicate_key_raises(self):
        df_exp2, df_exp3 = self._frames()
        dup_exp3 = pd.concat([df_exp3, df_exp3.iloc[[0]]], ignore_index=True)
        with pytest.raises(Exception):  # pd.errors.MergeError subclasses ValueError
            merge_band_columns(df_exp2, dup_exp3)

    def test_n_points_stays_integer_dtype(self):
        df_exp2, df_exp3 = self._frames()
        merged = merge_band_columns(df_exp2, df_exp3)
        assert pd.api.types.is_integer_dtype(merged["n_points"])


class TestBandMode:
    def test_band_csv_written_at_smoke_scale(self, tmp_path):
        exit_code = main(["--smoke", "--seeds", "42,43", "--out", str(tmp_path)])
        assert exit_code == 0

        band_path = tmp_path / "exp1_band.csv"
        assert band_path.exists()

        df = pd.read_csv(band_path)
        # --smoke uses a single test depth (1.30), so the smoke-scale
        # product is n_seeds * 1 depth * len(MODELS).
        assert len(df) == 2 * 1 * len(MODELS)
        assert "seed" in df.columns
        assert set(df.columns) >= set(EXP2_COLUMNS)
        assert sorted(df["seed"].unique().tolist()) == [42, 43]

    def test_band_csv_carries_exp3_columns(self, tmp_path):
        """The manuscript's headline z_rmse_mm ratio must be regenerable
        from exp1_band.csv (D-260807-dcv)."""
        main(["--smoke", "--seeds", "42,43", "--out", str(tmp_path)])
        df = pd.read_csv(tmp_path / "exp1_band.csv")
        for col in EXP3_COLUMNS:
            if col not in ("test_depth_m", "model"):
                assert col in df.columns
        assert df["z_rmse_mm"].notna().all()

    def test_band_mode_does_not_write_single_seed_csvs(self, tmp_path):
        main(["--smoke", "--seeds", "42,43", "--out", str(tmp_path)])
        assert not (tmp_path / "exp1_parameter_errors.csv").exists()
        assert not (tmp_path / "exp2_depth_generalization.csv").exists()
        assert not (tmp_path / "exp2_spatial_errors.csv").exists()
        assert not (tmp_path / "exp3_xy_vs_z_anisotropy.csv").exists()

    def test_band_mode_writes_benchmarks_with_seeds_list(self, tmp_path):
        main(["--smoke", "--seeds", "42,43", "--out", str(tmp_path)])
        for filename in BENCHMARK_FILENAMES.values():
            benchmark_path = tmp_path / filename
            assert benchmark_path.exists()
            with open(benchmark_path) as f:
                record = json.load(f)
            assert record["solver_config"]["seeds"] == [42, 43]

    def test_band_mode_writes_band_owned_sidecar(self, tmp_path):
        main(["--smoke", "--seeds", "42,43", "--out", str(tmp_path)])
        sidecar_path = tmp_path / "e1_seed_band_provenance.json"
        assert sidecar_path.exists()
        with open(sidecar_path) as f:
            record = json.load(f)
        assert record["experiment"] == "e1_seed_band"
        assert record["schema_version"] == 1
        assert record["solver_config"]["seeds"] == [42, 43]
        assert record["git_sha"]
        assert isinstance(record["seconds"], (int, float))
        assert isinstance(record["environment"], dict)
        assert record["scope"]

    def test_no_results_dir_modified(self, tmp_path):
        """Nothing under experiments/results/ is touched by a --seeds run."""
        import subprocess

        result = subprocess.run(
            ["git", "status", "--porcelain", "experiments/results/"],
            capture_output=True,
            text=True,
        )
        before = result.stdout
        main(["--smoke", "--seeds", "42,43", "--out", str(tmp_path)])
        result = subprocess.run(
            ["git", "status", "--porcelain", "experiments/results/"],
            capture_output=True,
            text=True,
        )
        after = result.stdout
        assert before == after


class TestSingleSeedPathUnaffected:
    def test_non_band_smoke_run_writes_no_band_csv(self, tmp_path):
        # `_run_smoke` always writes to its own ephemeral temp directory
        # regardless of --out (unlike the --seeds band path), so this only
        # asserts the plain --smoke run succeeds and never touches
        # exp1_band.csv anywhere under the caller-supplied --out.
        exit_code = main(["--smoke", "--out", str(tmp_path)])
        assert exit_code == 0
        assert not (tmp_path / "exp1_band.csv").exists()
        assert not (tmp_path / "e1_seed_band_provenance.json").exists()

    def test_shared_five_flag_contract_unchanged(self):
        parser = build_experiment_arg_parser()
        options = sorted(
            a.option_strings[0] for a in parser._actions if a.option_strings
        )
        assert options == ["--check", "--force", "--out", "--seed", "--smoke"]
