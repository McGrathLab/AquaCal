"""Unit tests for `experiments/e5_index_sensitivity.py`'s `--seeds` band mode
(D-19.5-05, COV-05).

Every test here runs at `--smoke` scale (2 `n_assumed` points, 4 calibration
frames) and writes to a `tmp_path`-scoped `--out` directory -- never
`experiments/results/` and never the production 11-point, N-seed band
(~22 min for a single seed, forbidden by this plan). None of these tests are
marked slow.
"""

from __future__ import annotations

import json

import pandas as pd
import pytest

from experiments._io import build_experiment_arg_parser
from experiments.e5_index_sensitivity import (
    E5_COLUMNS,
    N_ASSUMED_BAND,
    N_TRUE,
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

    def test_validate_e5_args_directly_rejects_seeds_with_check(self):
        from experiments.e5_index_sensitivity import _validate_e5_args

        parser = build_arg_parser()
        args = parser.parse_args(["--seeds", "42,43", "--check"])
        with pytest.raises(SystemExit):
            _validate_e5_args(parser, args)


class TestBandMode:
    """--smoke --seeds 42,43 runs 2 seeds x 2 smoke n_assumed points ==
    {N_TRUE, N_ASSUMED_BAND[-1]} -- mirrors `_run_smoke_at`'s own smoke band.
    """

    def test_band_csv_written_at_smoke_scale(self, tmp_path):
        exit_code = main(["--smoke", "--seeds", "42,43", "--out", str(tmp_path)])
        assert exit_code == 0

        band_path = tmp_path / "index_sensitivity_seed_band.csv"
        assert band_path.exists()

        df = pd.read_csv(band_path)
        n_single_seed_points = 2  # {N_TRUE, N_ASSUMED_BAND[-1]}, smoke scale
        assert len(df) == 2 * n_single_seed_points
        assert "seed" in df.columns
        assert set(df.columns) >= set(E5_COLUMNS)
        assert sorted(df["seed"].unique().tolist()) == [42, 43]

    def test_band_mode_does_not_write_single_seed_artifacts(self, tmp_path):
        main(["--smoke", "--seeds", "42,43", "--out", str(tmp_path)])
        assert not (tmp_path / "index_sensitivity.csv").exists()
        assert not (tmp_path / "e5_provenance.json").exists()

    def test_sidecar_has_seeds_and_n_assumed_band_and_scope(self, tmp_path):
        main(["--smoke", "--seeds", "42,43", "--out", str(tmp_path)])
        sidecar_path = tmp_path / "e5_seed_band_provenance.json"
        assert sidecar_path.exists()
        with open(sidecar_path) as f:
            sidecar = json.load(f)

        # D-19.5-05: an artifact must never be readable as the wrong band --
        # both lists present, plus a non-empty scope string distinguishing them.
        assert sidecar["solver_config"]["seeds"] == [42, 43]
        assert sidecar["n_assumed_band"] == list(N_ASSUMED_BAND)
        assert isinstance(sidecar["scope"], str)
        assert len(sidecar["scope"]) > 0

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
    def test_non_band_smoke_run_writes_no_seed_band_csv(self, tmp_path):
        # `_run_smoke` always writes to its own ephemeral temp directory
        # regardless of --out (unlike the --seeds band path), so this only
        # asserts the plain --smoke run succeeds and never touches
        # index_sensitivity_seed_band.csv anywhere under the caller-supplied
        # --out.
        exit_code = main(["--smoke", "--out", str(tmp_path)])
        assert exit_code == 0
        assert not (tmp_path / "index_sensitivity_seed_band.csv").exists()

    def test_shared_five_flag_contract_unchanged(self):
        parser = build_experiment_arg_parser()
        options = sorted(
            a.option_strings[0] for a in parser._actions if a.option_strings
        )
        assert options == ["--check", "--force", "--out", "--seed", "--smoke"]

    def test_n_true_and_n_assumed_band_unchanged_by_band_module_additions(self):
        # Sanity check that Task 1's additions did not perturb the existing
        # module-level constants the single-seed path depends on.
        assert N_TRUE == 1.333
        assert len(N_ASSUMED_BAND) == 11
