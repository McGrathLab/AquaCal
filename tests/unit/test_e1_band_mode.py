"""Unit tests for `experiments/e1_refractive_comparison.py`'s `--seeds` band
mode (D-19.4-14, SC-5a).

Every test here runs at `--smoke` scale (the `"ideal"` scenario, single test
depth) and writes to a `tmp_path`-scoped `--out` directory -- never
`experiments/results/` and never the production 10-seed band (~57 min,
forbidden by this plan). None of these tests are marked slow.
"""

from __future__ import annotations

import json
import types

import pandas as pd
import pytest

import experiments.e1_refractive_comparison as e1
from aquacal.calibration._observability import SolverDiagnostics
from experiments._io import build_experiment_arg_parser
from experiments.e1_refractive_comparison import (
    BAND_MERGED_COLUMNS,
    BENCHMARK_FILENAMES,
    EXP1_COLUMNS,
    EXP2_COLUMNS,
    EXP3_COLUMNS,
    MODELS,
    PARAMETER_BAND_KEY_COLUMNS,
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

    def test_parameter_band_csv_carries_exp1_columns(self, tmp_path):
        """The parameter-level columns behind the manuscript's focal-drift and
        reprojection-RMS sentences must be regenerable per seed from a
        committed artifact, not only from gitignored sweep output."""
        exit_code = main(["--smoke", "--seeds", "42,43", "--out", str(tmp_path)])
        assert exit_code == 0

        band_path = tmp_path / "exp1_parameter_band.csv"
        assert band_path.exists()

        df = pd.read_csv(band_path)
        assert set(df.columns) >= set(EXP1_COLUMNS) | {"seed"}
        # All requested seeds present -- a band missing one silently narrows
        # the span its sidecar claims.
        assert sorted(df["seed"].unique().tolist()) == [42, 43]
        assert df["focal_length_error_pct"].notna().all()
        assert df["reprojection_rms_px"].notna().all()

    def test_parameter_band_keyed_by_seed_camera_model(self, tmp_path):
        """(seed, camera, model) is unique -- EXP1 has no depth axis, which is
        why this is a second CSV rather than columns on exp1_band.csv."""
        main(["--smoke", "--seeds", "42,43", "--out", str(tmp_path)])
        df = pd.read_csv(tmp_path / "exp1_parameter_band.csv")
        assert not df.duplicated(subset=PARAMETER_BAND_KEY_COLUMNS).any()

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
        assert not (tmp_path / "exp1_parameter_band.csv").exists()
        assert not (tmp_path / "e1_seed_band_provenance.json").exists()

    def test_shared_five_flag_contract_unchanged(self):
        parser = build_experiment_arg_parser()
        options = sorted(
            a.option_strings[0] for a in parser._actions if a.option_strings
        )
        assert options == ["--check", "--force", "--out", "--seed", "--smoke"]


# --- BAND-01: the noise_std axis -------------------------------------------
#
# These tests drive `_run_band` at PRODUCTION scale (10 seeds x 4 noise levels)
# with every solve stubbed out, so the 640/960 shape and the key-uniqueness
# contract are pinned without a single calibration running. A real band of that
# shape is ~7 h and belongs to Phase 28 (D-21); nothing here may run one.

BAND_SEEDS = [42, 43, 44, 45, 46, 47, 48, 49, 50, 51]
STUB_CAMERAS = [f"cam{i}" for i in range(12)]
PRESET_NOISE = 0.5


class _StubScenario:
    """Stand-in for `SyntheticScenario`: only the attributes `_run_band` reads,
    plus the mutable `noise_std` the axis writes."""

    def __init__(self, name: str, seed: int) -> None:
        self.name = name
        self.seed = seed
        self.noise_std = PRESET_NOISE
        self.intrinsics = dict.fromkeys(STUB_CAMERAS)
        self.board_poses = list(range(20))


def _patch_band_internals(monkeypatch):
    """Stub the solve and the dataframe assembly so `_run_band`'s own loop,
    stamping, key columns and CSV writes are the only things exercised."""

    def _fake_create_scenario(scenario_name, seed=0, **kwargs):
        return _StubScenario(scenario_name, seed)

    def _fake_run_one_model(scenario, n_water, seed):
        # Real `SolverDiagnostics` instances, not namespaces:
        # `write_direct_call_benchmark` calls `dataclasses.asdict` on them.
        diagnostics = {
            key: SolverDiagnostics()
            for key in ("stage3_interface_optimization", "stage3_intrinsic_pass")
        }
        result = types.SimpleNamespace(
            diagnostics=types.SimpleNamespace(reprojection_error_rms=0.4),
            cameras={STUB_CAMERAS[0]: types.SimpleNamespace(water_z=1.031)},
        )
        return result, object(), {}, diagnostics, {}, None

    def _fake_build_dataframes(scenario, results, seed, test_depths=None, **kwargs):
        depths = e1.TEST_DEPTHS if test_depths is None else test_depths
        labels = list(results)
        exp1_rows = [
            dict.fromkeys(EXP1_COLUMNS, 0.0) | {"camera": camera, "model": label}
            for label in labels
            for camera in STUB_CAMERAS
        ]
        exp2_rows = [
            dict.fromkeys(EXP2_COLUMNS, 0.0) | {"test_depth_m": depth, "model": label}
            for label in labels
            for depth in depths
        ]
        exp3_rows = [
            dict.fromkeys(EXP3_COLUMNS, 0.0)
            | {"test_depth_m": depth, "model": label, "n_points": 49}
            for label in labels
            for depth in depths
        ]
        return (
            pd.DataFrame(exp1_rows, columns=EXP1_COLUMNS),
            pd.DataFrame(exp2_rows, columns=EXP2_COLUMNS),
            pd.DataFrame([]),
            pd.DataFrame(exp3_rows, columns=EXP3_COLUMNS),
        )

    monkeypatch.setattr(e1, "create_scenario", _fake_create_scenario)
    monkeypatch.setattr(e1, "_run_one_model", _fake_run_one_model)
    monkeypatch.setattr(e1, "_build_dataframes", _fake_build_dataframes)


class TestNoiseAxis:
    """BAND-01: the `noise_std` axis's shape, keys and smoke collapse."""

    def test_noise_axis_shape_at_band_scale(self, tmp_path, monkeypatch):
        """Ten seeds x four noise levels: 640 band rows and 960 parameter-band
        rows. The 960 figure is anticipated by no committed document -- this is
        where it becomes checked."""
        _patch_band_internals(monkeypatch)
        e1._run_band(BAND_SEEDS, tmp_path, smoke=False, force=True)

        band = pd.read_csv(tmp_path / "exp1_band.csv")
        assert len(band) == 640
        assert "noise_std" in band.columns
        assert sorted(band["noise_std"].unique().tolist()) == [0.25, 0.5, 0.82, 1.2]

        parameter_band = pd.read_csv(tmp_path / "exp1_parameter_band.csv")
        assert len(parameter_band) == 960
        assert "noise_std" in parameter_band.columns
        assert sorted(parameter_band["noise_std"].unique().tolist()) == [
            0.25,
            0.5,
            0.82,
            1.2,
        ]

    def test_band_csvs_have_no_duplicate_keys(self, tmp_path, monkeypatch):
        """PITFALL B1's tripwire. `write_experiment_csv` sorts by the key
        columns and never validates uniqueness, so dropping `noise_std` from
        either list writes a file whose every key names four rows -- silently.
        The key lists are read from the module rather than hardcoded here, so
        this fails if either one is narrowed later."""
        _patch_band_internals(monkeypatch)
        e1._run_band(BAND_SEEDS, tmp_path, smoke=False, force=True)

        band = pd.read_csv(tmp_path / "exp1_band.csv")
        assert not band.duplicated(subset=e1.BAND_KEY_COLUMNS).any()

        parameter_band = pd.read_csv(tmp_path / "exp1_parameter_band.csv")
        assert not parameter_band.duplicated(subset=PARAMETER_BAND_KEY_COLUMNS).any()

    def test_smoke_band_runs_one_noise_level(self, tmp_path, monkeypatch):
        """PITFALL B2: `--smoke` collapses the axis exactly as it collapses the
        depth sweep, so the eight real-solve smoke tests above do not
        quadruple. The expected row count is the pre-BAND-01 smoke count,
        n_seeds x 1 depth x len(MODELS) -- unquadrupled."""
        _patch_band_internals(monkeypatch)
        e1._run_band([42, 43], tmp_path, smoke=True, force=True)

        band = pd.read_csv(tmp_path / "exp1_band.csv")
        assert band["noise_std"].nunique() == 1
        assert len(band) == 2 * 1 * len(MODELS)

        parameter_band = pd.read_csv(tmp_path / "exp1_parameter_band.csv")
        assert parameter_band["noise_std"].nunique() == 1
        assert len(parameter_band) == 2 * len(STUB_CAMERAS) * len(MODELS)


class TestBandBenchmarkWritePolicy:
    """D-06/D-07: band mode may CREATE `e1_benchmark_<model>.json` when it is
    absent, and must NEVER overwrite one that exists -- enforced at the call
    site with a literal `force=False`, not delegated to the resumability
    guard. Its log says which of the two happened.

    Every test here uses `_patch_band_internals`, so no calibration runs and
    nothing under `experiments/results/` is read or written.
    """

    def _existing_records(self, out_dir):
        """Pre-create both single-seed benchmark records with sentinel bytes."""
        paths = {}
        for label, filename in BENCHMARK_FILENAMES.items():
            path = out_dir / filename
            path.write_text(
                json.dumps(
                    {"sentinel": label, "solver_config": {"seed": 7}},
                    indent=2,
                )
            )
            paths[label] = path
        return paths

    def test_force_band_run_leaves_existing_records_byte_identical(
        self, tmp_path, monkeypatch
    ):
        """The `--force` case is the live hazard D-07 names: without a literal
        `force=False` at the call, a forced band run silently republishes two
        records another stage owns, stamped with `seeds[-1]`."""
        _patch_band_internals(monkeypatch)
        paths = self._existing_records(tmp_path)
        before = {label: path.read_bytes() for label, path in paths.items()}

        e1._run_band([42, 43], tmp_path, smoke=True, force=True)

        for label, path in paths.items():
            assert path.read_bytes() == before[label], label

    def test_unforced_band_run_leaves_existing_records_byte_identical(
        self, tmp_path, monkeypatch
    ):
        _patch_band_internals(monkeypatch)
        paths = self._existing_records(tmp_path)
        before = {label: path.read_bytes() for label, path in paths.items()}

        e1._run_band([42, 43], tmp_path, smoke=True, force=False)

        for label, path in paths.items():
            assert path.read_bytes() == before[label], label

    def test_kept_records_are_logged_and_no_write_is_claimed(
        self, tmp_path, monkeypatch, capsys
    ):
        """D-06: the defect was a log claiming two writes the guard skipped."""
        _patch_band_internals(monkeypatch)
        paths = self._existing_records(tmp_path)

        e1._run_band([42, 43], tmp_path, smoke=True, force=True)
        out = capsys.readouterr().out

        for label, path in paths.items():
            assert f"Wrote {path}" not in out, label
            kept = [
                line
                for line in out.splitlines()
                if str(path) in line and "Kept existing" in line
            ]
            assert len(kept) == 1, (label, out)

    def test_empty_out_dir_creates_both_records_and_confirms_each(
        self, tmp_path, monkeypatch, capsys
    ):
        """The other half of the policy: band mode still CREATES the records
        when they are absent -- a standalone band into a fresh --out."""
        _patch_band_internals(monkeypatch)

        e1._run_band([42, 43], tmp_path, smoke=True, force=False)
        out = capsys.readouterr().out

        for filename in BENCHMARK_FILENAMES.values():
            path = tmp_path / filename
            assert path.exists(), filename
            assert f"Wrote {path}" in out, filename
            assert "Kept existing" not in out

    def test_created_records_carry_seeds_list_and_last_seed(
        self, tmp_path, monkeypatch
    ):
        """`seeds` names what the band swept; `seed` names what this record
        measured. Both must survive the write-policy change."""
        _patch_band_internals(monkeypatch)

        e1._run_band([42, 43], tmp_path, smoke=True, force=False)

        for filename in BENCHMARK_FILENAMES.values():
            with open(tmp_path / filename) as f:
                record = json.load(f)
            assert record["solver_config"]["seeds"] == [42, 43], filename
            assert record["solver_config"]["seed"] == 43, filename

    def test_band_owned_outputs_still_written_when_records_are_kept(
        self, tmp_path, monkeypatch
    ):
        """Force stays implied for the three band-owned outputs (D-19.4-14).
        Narrowing the benchmark write must not narrow these."""
        _patch_band_internals(monkeypatch)
        self._existing_records(tmp_path)
        band_owned = [
            tmp_path / "exp1_band.csv",
            tmp_path / "exp1_parameter_band.csv",
            tmp_path / "e1_seed_band_provenance.json",
        ]
        for path in band_owned:
            path.write_text("stale sentinel\n")
        before = {path: path.read_bytes() for path in band_owned}

        e1._run_band([42, 43], tmp_path, smoke=True, force=False)

        for path in band_owned:
            assert path.exists(), path.name
            assert path.read_bytes() != before[path], path.name


class TestBandScopeIsDerived:
    """D-08/D-10: `e1_seed_band_provenance.json`'s `scope` field states the
    domain THIS run swept, computed at write time, rather than a literal that
    can outlive the conditions that produced it.

    Every expected value below is built from the module's own constants and
    from the emitted frames, never hardcoded -- a test that froze `4` or `256`
    into itself would be the same defect one level up.
    """

    def _scope(self, tmp_path, monkeypatch, seeds, smoke):
        _patch_band_internals(monkeypatch)
        e1._run_band(list(seeds), tmp_path, smoke=smoke, force=False)
        with open(tmp_path / "e1_seed_band_provenance.json") as f:
            record = json.load(f)
        return record["scope"], record

    def test_scope_states_the_seed_count_and_list_that_were_run(
        self, tmp_path, monkeypatch
    ):
        seeds = [42, 43, 44, 45]
        scope, record = self._scope(tmp_path, monkeypatch, seeds, smoke=False)
        assert f"{len(seeds)} seed(s) {seeds}" in scope
        # The derived string and the machine-readable field cannot disagree.
        assert record["solver_config"]["seeds"] == seeds

    def test_scope_states_the_emitted_row_counts(self, tmp_path, monkeypatch):
        scope, _ = self._scope(tmp_path, monkeypatch, [42, 43, 44, 45], smoke=False)
        band_rows = len(pd.read_csv(tmp_path / "exp1_band.csv"))
        parameter_rows = len(pd.read_csv(tmp_path / "exp1_parameter_band.csv"))
        assert f"{band_rows} rows of exp1_band.csv" in scope
        assert f"{parameter_rows} rows of exp1_parameter_band.csv" in scope
        # Ruling A1's arithmetic, checked rather than trusted: the production
        # shape is 256/384, and it is what the strings above must carry.
        assert (band_rows, parameter_rows) == (256, 384)

    def test_scope_states_the_noise_levels_and_depths_that_were_run(
        self, tmp_path, monkeypatch
    ):
        scope, _ = self._scope(tmp_path, monkeypatch, [42, 43, 44, 45], smoke=False)
        expected_noise = sorted(round(float(v), 6) for v in e1.NOISE_LEVELS)
        expected_depths = sorted(round(float(v), 6) for v in e1.TEST_DEPTHS)
        assert f"{len(expected_noise)} detection-noise level(s) " in scope
        assert f"{expected_noise} px" in scope
        assert f"{len(expected_depths)} test depth(s) {expected_depths} m" in scope

    def test_smoke_band_scope_describes_its_own_collapsed_axes(
        self, tmp_path, monkeypatch
    ):
        """A --smoke band must be truthful about ONE noise level and ONE depth
        rather than describing the production grid -- the exact way the old
        literal lied."""
        scope, _ = self._scope(tmp_path, monkeypatch, [42, 43], smoke=True)
        assert "2 seed(s) [42, 43]" in scope
        assert "1 detection-noise level(s) " in scope
        assert f"[{PRESET_NOISE}] px" in scope
        assert "1 test depth(s) [1.3] m" in scope
        assert f"{len(pd.read_csv(tmp_path / 'exp1_band.csv'))} rows of " in scope
        # The production figures must not appear in a smoke run's scope.
        assert "256 rows" not in scope
        assert "384 rows" not in scope

    def test_scope_cites_ruling_a1_for_the_seed_axis(self, tmp_path, monkeypatch):
        """A stable cross-reference is a citation, not a recomputed value, so
        it stays -- and it is the only place a reader can learn why the seed
        axis is the size it is."""
        scope, _ = self._scope(tmp_path, monkeypatch, [42, 43], smoke=True)
        assert "RULING A1" in scope
        assert "run_stage_e1_band" in scope

    def test_scope_carries_no_forward_looking_schedule_clause(
        self, tmp_path, monkeypatch
    ):
        """A schedule is not a domain, and it is the half of the old string
        that needed re-dating after every run."""
        scope, _ = self._scope(tmp_path, monkeypatch, [42, 43], smoke=True)
        for clause in (
            "WILL BE quoted over",
            "is executed in Phase",
            "verified in Phase 29",
            "ten seeds",
            "640/960",
        ):
            assert clause not in scope, clause

    def test_scope_preserves_the_static_claims(self, tmp_path, monkeypatch):
        """The parts that are genuinely static claims rather than measurements
        survive: the scenario restriction, the warm-restart evidence, the
        ill-conditioning caveat (D-16) and D-19.3-17's qualification."""
        scope, _ = self._scope(tmp_path, monkeypatch, [42, 43], smoke=True)
        assert "12-camera synthetic geometry" in scope
        assert "1.8e-9" in scope
        assert "ill-conditioned" in scope
        assert "D-16" in scope
        assert "D-19.3-17" in scope
        assert "E2 carries the accuracy claim against reality" in scope
