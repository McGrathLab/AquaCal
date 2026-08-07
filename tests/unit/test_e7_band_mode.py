"""Unit tests for `experiments/e7_interface_ablation.py`'s `--seeds` band mode
(D-19.4-14, SC-5a).

Every test here runs at `--smoke` scale (the `"minimal"` scenario) and writes
to a `tmp_path`-scoped `--out` directory -- never `experiments/results/` and
never the production 10-seed band (~56 min, forbidden by this plan). None of
these tests are marked slow.
"""

from __future__ import annotations

import json

import pandas as pd
import pytest

from experiments._io import build_experiment_arg_parser
from experiments.e7_interface_ablation import (
    ABLATION_COLUMNS,
    ARMS,
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

    def test_validate_e7_args_directly_rejects_seeds_with_check(self):
        from experiments.e7_interface_ablation import _validate_e7_args

        parser = build_arg_parser()
        args = parser.parse_args(["--seeds", "42,43", "--check"])
        with pytest.raises(SystemExit):
            _validate_e7_args(parser, args)


class TestBandMode:
    def test_band_csv_written_at_smoke_scale(self, tmp_path):
        exit_code = main(["--smoke", "--seeds", "42,43", "--out", str(tmp_path)])
        assert exit_code == 0

        band_path = tmp_path / "interface_ablation_band.csv"
        assert band_path.exists()

        df = pd.read_csv(band_path)
        n_cameras = len(pd.unique(df.loc[df["seed"] == 42, "camera"]))
        assert len(df) == 2 * n_cameras * len(ARMS)
        assert "seed" in df.columns
        assert set(df.columns) >= set(ABLATION_COLUMNS)
        assert sorted(df["seed"].unique().tolist()) == [42, 43]

    def test_band_mode_does_not_write_single_seed_csv(self, tmp_path):
        main(["--smoke", "--seeds", "42,43", "--out", str(tmp_path)])
        assert not (tmp_path / "interface_ablation.csv").exists()

    def test_band_mode_writes_benchmarks_with_seeds_list(self, tmp_path):
        main(["--smoke", "--seeds", "42,43", "--out", str(tmp_path)])
        for arm_name, _, _ in ARMS:
            benchmark_path = tmp_path / f"e7_benchmark_{arm_name}.json"
            assert benchmark_path.exists()
            with open(benchmark_path) as f:
                record = json.load(f)
            assert record["solver_config"]["seeds"] == [42, 43]

    def test_band_mode_writes_band_owned_sidecar(self, tmp_path):
        main(["--smoke", "--seeds", "42,43", "--out", str(tmp_path)])
        sidecar_path = tmp_path / "e7_seed_band_provenance.json"
        assert sidecar_path.exists()
        with open(sidecar_path) as f:
            record = json.load(f)
        assert record["experiment"] == "e7_seed_band"
        assert record["schema_version"] == 1
        assert record["solver_config"]["seeds"] == [42, 43]
        assert record["git_sha"]
        assert isinstance(record["seconds"], (int, float))
        assert isinstance(record["environment"], dict)
        assert record["scope"]

    def test_ablation_columns_unchanged(self, tmp_path):
        """E7 gains only the sidecar -- ABLATION_COLUMNS must not change."""
        main(["--smoke", "--seeds", "42,43", "--out", str(tmp_path)])
        df = pd.read_csv(tmp_path / "interface_ablation_band.csv")
        assert list(df.columns[: len(ABLATION_COLUMNS)]) == ABLATION_COLUMNS

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
        main(["--smoke", "--out", str(tmp_path)])
        assert (tmp_path / "interface_ablation.csv").exists()
        assert not (tmp_path / "interface_ablation_band.csv").exists()

    def test_shared_five_flag_contract_unchanged(self):
        parser = build_experiment_arg_parser()
        options = sorted(
            a.option_strings[0] for a in parser._actions if a.option_strings
        )
        assert options == ["--check", "--force", "--out", "--seed", "--smoke"]
