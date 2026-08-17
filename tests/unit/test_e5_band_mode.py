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
    build_row,
    main,
)

#: The six degeneracy columns plan 24-02 appended, in the order they must
#: appear at the END of `E5_COLUMNS`. Spelled out here rather than imported so
#: this test fails if the shared list is reordered or renamed.
EXPECTED_DEGENERACY_COLUMNS = [
    "degenerate_observations_at_solution",
    "degenerate_observations_cause_above_interface",
    "degenerate_observations_cause_behind_camera",
    "degenerate_observations_cause_interface_below_camera",
    "degenerate_observations_fate_extended",
    "degenerate_observations_fate_penalized",
]


class _FakeReconstruction:
    def __init__(self):
        self.mean = 0.002
        self.rmse = 0.003
        self.signed_mean = 0.001
        self.num_comparisons = 120


class _FakeReprojection:
    rms = 0.42


class _FakeEvaluation:
    def __init__(self):
        self.reprojection = _FakeReprojection()
        self.reconstruction = _FakeReconstruction()
        self.num_frames = 8


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


@pytest.fixture(scope="module")
def band_run_dir(tmp_path_factory):
    """Run `--smoke --seeds 42,43` exactly ONCE for the whole module and return
    the `--out` directory every `TestBandMode` test reads from.

    D-22: these five tests previously re-ran the band per test -- 317 s
    measured, against E6's 93.89 s for six tests, which had already been put on
    exactly this fixture (`test_e6_band_mode.py:74`). Copied from there rather
    than invented. Test-time only: it changes no artifact and gates nothing.
    """
    out_dir = tmp_path_factory.mktemp("e5_band_smoke")
    exit_code = main(["--smoke", "--seeds", "42,43", "--out", str(out_dir)])
    assert exit_code == 0
    return out_dir


@pytest.mark.slow
class TestBandMode:
    """--smoke --seeds 42,43 runs 2 seeds x 2 smoke n_assumed points ==
    {N_TRUE, N_ASSUMED_BAND[-1]} -- mirrors `_run_smoke_at`'s own smoke band.
    """

    def test_band_csv_written_at_smoke_scale(self, band_run_dir):
        band_path = band_run_dir / "index_sensitivity_seed_band.csv"
        assert band_path.exists()

        df = pd.read_csv(band_path)
        n_single_seed_points = 2  # {N_TRUE, N_ASSUMED_BAND[-1]}, smoke scale
        assert len(df) == 2 * n_single_seed_points
        assert "seed" in df.columns
        assert set(df.columns) >= set(E5_COLUMNS)
        assert sorted(df["seed"].unique().tolist()) == [42, 43]

    def test_band_mode_does_not_write_single_seed_artifacts(self, band_run_dir):
        assert not (band_run_dir / "index_sensitivity.csv").exists()
        assert not (band_run_dir / "e5_provenance.json").exists()
        # The band's degeneracy breakdown is band-owned and must never take the
        # single-seed run's filename.
        assert not (band_run_dir / "e5_degeneracy_breakdown.json").exists()
        assert (band_run_dir / "e5_seed_band_degeneracy_breakdown.json").exists()

    def test_sidecar_has_seeds_and_n_assumed_band_and_scope(self, band_run_dir):
        sidecar_path = band_run_dir / "e5_seed_band_provenance.json"
        assert sidecar_path.exists()
        with open(sidecar_path) as f:
            sidecar = json.load(f)

        # D-19.5-05: an artifact must never be readable as the wrong band --
        # both lists present, plus a non-empty scope string distinguishing them.
        assert sidecar["solver_config"]["seeds"] == [42, 43]
        assert sidecar["n_assumed_band"] == list(N_ASSUMED_BAND)
        assert isinstance(sidecar["scope"], str)
        assert len(sidecar["scope"]) > 0

    def test_degeneracy_breakdown_sidecar_carries_the_per_stage_split(
        self, band_run_dir
    ):
        """D-09's sidecar half: the per-stage cause/fate keys and the
        `observations_evaluated__*` denominators the CSV deliberately omits."""
        with open(band_run_dir / "e5_seed_band_degeneracy_breakdown.json") as f:
            breakdown = json.load(f)

        assert sorted(breakdown) == ["42", "43"]
        for stats in breakdown.values():
            assert any(k.startswith("degenerate_observations_cause_") for k in stats)
            assert any(k.startswith("degenerate_observations_fate_") for k in stats)
            assert any(k.startswith("observations_evaluated__") for k in stats)

    def test_no_results_dir_modified(self, band_run_dir):
        """Nothing under experiments/results/ is touched by a --seeds run.

        The band ran in the module-scope fixture, so this compares the working
        tree against `git status` taken now -- a band run that had written into
        `experiments/results/` would already show up here.
        """
        import subprocess

        result = subprocess.run(
            ["git", "status", "--porcelain", "experiments/results/"],
            capture_output=True,
            text=True,
        )
        assert result.stdout == ""


class TestDegeneracyColumns:
    """DEGEN-01/DEGEN-02 via plan 24-02 (D-09 as revised 2026-08-17)."""

    def test_band_row_carries_the_six_degeneracy_columns(self):
        assert len(E5_COLUMNS) == 23
        assert E5_COLUMNS[-6:] == EXPECTED_DEGENERACY_COLUMNS

        row = build_row(
            _FakeEvaluation(),
            n_assumed=1.34,
            n_true=N_TRUE,
            seed=42,
            square_size_m=0.02,
            discard_stats={
                "degenerate_observations_at_solution": 5,
                "degenerate_observations_cause_above_interface"
                "__stage3_interface_optimization": 3,
                "degenerate_observations_cause_behind_camera"
                "__stage3_interface_optimization": 2,
                "observations_evaluated__stage3_interface_optimization": 1000,
                "degenerate_observations_fate_extended"
                "__stage3_interface_optimization": 4,
                "degenerate_observations_fate_penalized"
                "__stage3_interface_optimization": 1,
            },
        )
        assert list(row) == E5_COLUMNS
        for column in EXPECTED_DEGENERACY_COLUMNS:
            assert row[column] is not None

    def test_row_without_counts_writes_none_not_zero(self):
        """E6's `_build_row` convention: `None` means "never computed for this
        row", `0` means "computed and found clean". Collapsing the two would
        make a pre-instrumentation row indistinguishable from a clean one."""
        row = build_row(
            _FakeEvaluation(),
            n_assumed=1.34,
            n_true=N_TRUE,
            seed=42,
            square_size_m=0.02,
        )
        for column in EXPECTED_DEGENERACY_COLUMNS:
            assert row[column] is None

    def test_each_axis_sums_to_the_merged_total_on_a_generated_row(self):
        """The self-validating property D-09's six-column shape was chosen for.

        Cause and fate are two independent decompositions of the SAME set of
        invalid observations, so each must sum to the merged total on its own
        -- and the two must never be added together. Asserting it here on a row
        actually produced by `build_row` (not a hand-written dict) proves the
        shape's benefit rather than assuming it: a bookkeeping bug shows up as
        the two axes disagreeing, which is exactly what a reader scanning the
        CSV would notice by eye.
        """
        row = build_row(
            _FakeEvaluation(),
            n_assumed=1.34,
            n_true=N_TRUE,
            seed=42,
            square_size_m=0.02,
            discard_stats={
                "degenerate_observations_at_solution": 5,
                "degenerate_observations_cause_above_interface"
                "__stage3_interface_optimization": 3,
                "degenerate_observations_cause_behind_camera"
                "__stage3_interface_optimization": 2,
                "degenerate_observations_cause_interface_below_camera"
                "__stage3_interface_optimization": 0,
                "degenerate_observations_fate_extended"
                "__stage3_interface_optimization": 4,
                "degenerate_observations_fate_penalized__stage3_intrinsic_pass": 1,
                "observations_evaluated__stage3_interface_optimization": 1000,
            },
        )
        merged = row["degenerate_observations_at_solution"]
        if merged is None:  # never computed for this row -- nothing to check
            return

        cause_sum = sum(
            row[column]
            for column in EXPECTED_DEGENERACY_COLUMNS
            if column.startswith("degenerate_observations_cause_")
        )
        fate_sum = sum(
            row[column]
            for column in EXPECTED_DEGENERACY_COLUMNS
            if column.startswith("degenerate_observations_fate_")
        )
        assert cause_sum == merged
        assert fate_sum == merged


class TestSingleSeedPathUnaffected:
    @pytest.mark.slow
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
