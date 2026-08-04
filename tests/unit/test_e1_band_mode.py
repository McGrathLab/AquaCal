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
    BENCHMARK_FILENAMES,
    EXP2_COLUMNS,
    MODELS,
    build_arg_parser,
    main,
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

    def test_shared_five_flag_contract_unchanged(self):
        parser = build_experiment_arg_parser()
        options = sorted(
            a.option_strings[0] for a in parser._actions if a.option_strings
        )
        assert options == ["--check", "--force", "--out", "--seed", "--smoke"]
