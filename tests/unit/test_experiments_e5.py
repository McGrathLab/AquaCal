"""Unit tests for `experiments/e5_index_sensitivity.py`.

Fast, hand-built-fixture tests only (matching `test_experiments_e1.py`'s
discipline): no `create_scenario`, no `calibrate_synthetic`/
`optimize_interface`, nothing marked slow -- with one deliberate exception
(plan 19.2-27 Task 5's inertness proof, which runs the package's cheap
'minimal' preset once with and once without `discard_stats_out`; still not
marked slow).
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import numpy as np
import pandas as pd
import pytest

import experiments.e5_index_sensitivity as e5mod
from aquacal.datasets import create_scenario
from aquacal.datasets.pipelines import calibrate_synthetic
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
    run_band,
    run_index_point,
)
from tests.unit._baseline_paths import baseline_file, resolve_results_dir
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
    """compute_scale_bias reproduces at least 3 committed exp2_depth_generalization.csv rows.

    Reads the COMMITTED baseline, which Phase 26 / DRIVER-04 (D-28) moved to
    experiments/pre_rerun_baseline/ so the frozen sha ships with an empty
    experiments/results/. Anchored to the repo root rather than cwd (WR-06) and
    guarded, so a fresh clone -- which has neither tree -- skips rather than
    erroring, matching how this module's discovery helpers already degrade.
    """
    # Plan 26-14: resolved per file. compute_scale_bias must reproduce whichever committed
    # CSV is current -- checking it against the frozen run's own output after Phase 28 is
    # strictly stronger than checking it against the archive forever.
    baseline = baseline_file("exp2_depth_generalization.csv")
    if not baseline.exists():
        pytest.skip(f"committed baseline absent (fresh clone): {baseline}")
    df = pd.read_csv(baseline)
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
        tmp_path), the resolved path must still be absolute and must point at a
        committed baseline that actually exists.

        ⚠ Phase 26 / DRIVER-04 (D-28) emptied experiments/results/, so the
        second half of that invariant now holds via the archive. The subject of
        this test is WR-06 (cwd-independence), which is unchanged; the existence
        leg is kept REAL rather than deleted, by accepting either location. It
        re-tightens on its own once Phase 28's run repopulates
        experiments/results/.

        The production constant `_default_metrics_path` still names
        experiments/results/, which is out of plan 26-01's scope -- repointing
        it is D-12's `--baseline-dir` work. See 26-01-SUMMARY.md
        § Findings for plan 26-03.
        """
        from experiments.e5_index_sensitivity import _default_metrics_path

        monkeypatch.chdir(tmp_path)
        resolved = _default_metrics_path()
        assert resolved.is_absolute()
        # Plan 26-14. 26-01 wrote that this "re-tightens on its own once Phase 28's run
        # repopulates experiments/results/" -- it did not: the disjunction below would
        # have stayed permissive forever, so a broken production path could be rescued by
        # the archive indefinitely. Now the fallback is allowed ONLY while the live tree
        # is unpopulated, and the existence leg becomes exact the moment it is.
        _, which = resolve_results_dir()
        if which == "live":
            assert resolved.exists(), resolved
        else:
            archived = (
                resolved.parents[1] / "pre_rerun_baseline" / "results" / resolved.name
            )
            assert resolved.exists() or archived.exists(), (resolved, archived)


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


# ---------------------------------------------------------------------------
# Plan 19.2-27 Task 4: E5 emits discard_stats so plan 19.2-23's attribution
# gate is runnable against evidence E5 actually produces.
# ---------------------------------------------------------------------------


class TestDiscardStatsProvenance:
    """`build_provenance_sidecar` carries `discard_stats`, and `None`
    (accounting never requested) is distinguishable from a populated dict
    whose counters happen to all be zero (accounting requested, nothing
    discarded)."""

    def test_sidecar_discard_stats_absent_by_default_is_none(self):
        sidecar = build_provenance_sidecar(seed=1)
        assert sidecar["discard_stats"] is None

    def test_sidecar_carries_a_populated_discard_stats_dict(self):
        sidecar = build_provenance_sidecar(
            seed=1, discard_stats={"pnp_guard_rejected": 3, "pnp_attempts_total": 40}
        )
        assert sidecar["discard_stats"] == {
            "pnp_guard_rejected": 3,
            "pnp_attempts_total": 40,
        }

    def test_absent_is_distinguishable_from_populated_zero(self):
        """`None` (never requested) != `{}` (requested, nothing discarded) --
        the exact distinction WR-04/D-14's absent-metric convention
        requires: absence must never be silently coerced into a zero."""
        absent = build_provenance_sidecar(seed=1)
        zero = build_provenance_sidecar(seed=1, discard_stats={})
        assert absent["discard_stats"] is None
        assert zero["discard_stats"] == {}
        assert absent["discard_stats"] != zero["discard_stats"]


def test_run_band_sums_discard_stats_across_points(monkeypatch):
    """run_band SUMS each point's discard_stats into the caller's dict -- the
    chosen aggregation shape (plan 19.2-27 Task 4). Every point in the band
    shares the same rig geometry and calibration frame count; only
    `n_assumed` differs. The attribution question plan 19.2-23's gate asks
    ("did the PnP guard activate anywhere in this run?") is a band-level
    question, not a per-index-value one, so summing rather than keeping a
    per-point breakdown is the more faithful shape here.

    `run_index_point` is monkeypatched so this stays a fast unit test of the
    aggregation logic, not a real calibration."""
    call_sinks: list[dict | None] = []

    def _fake_run_index_point(
        n_assumed,
        n_true,
        n_frames,
        seed,
        refine_intrinsics=False,
        discard_stats_out=None,
    ):
        call_sinks.append(discard_stats_out)
        if discard_stats_out is not None:
            discard_stats_out["pnp_attempts_total"] = 4
            if n_assumed == n_true:
                discard_stats_out["pnp_guard_rejected"] = 1
        evaluation = _make_evaluation()
        return build_row(
            evaluation,
            n_assumed=n_assumed,
            n_true=n_true,
            seed=seed,
            square_size_m=SQUARE_SIZE_M,
        )

    monkeypatch.setattr(e5mod, "run_index_point", _fake_run_index_point)

    band = [1.323, N_TRUE, 1.343]
    discard_stats: dict = {}
    df = run_band(
        band=band,
        n_true=N_TRUE,
        n_frames=4,
        seed=42,
        metrics_path=Path("does-not-exist.json"),
        refine_intrinsics=False,
        discard_stats_out=discard_stats,
    )

    assert len(df) == 3
    # 3 points x 4 pnp_attempts_total = 12; exactly one point (the n_true
    # control) recorded a guard rejection.
    assert discard_stats == {"pnp_attempts_total": 12, "pnp_guard_rejected": 1}
    # Every point got its OWN empty dict, never the caller's accumulator
    # directly -- otherwise a point that raised partway through would leave
    # the accumulator holding a partial, unsummed write.
    assert all(sink is not None and sink is not discard_stats for sink in call_sinks)


def test_run_band_discard_stats_out_none_disables_accounting(monkeypatch):
    """discard_stats_out=None (the default) is forwarded to every point as
    None -- accounting stays off, matching calibrate_synthetic's own
    inert-when-omitted default (plan 19.2-26)."""
    received: list[dict | None] = []

    def _fake_run_index_point(
        n_assumed,
        n_true,
        n_frames,
        seed,
        refine_intrinsics=False,
        discard_stats_out=None,
    ):
        received.append(discard_stats_out)
        evaluation = _make_evaluation()
        return build_row(
            evaluation,
            n_assumed=n_assumed,
            n_true=n_true,
            seed=seed,
            square_size_m=SQUARE_SIZE_M,
        )

    monkeypatch.setattr(e5mod, "run_index_point", _fake_run_index_point)

    run_band(
        band=[N_TRUE],
        n_true=N_TRUE,
        n_frames=4,
        seed=1,
        metrics_path=Path("does-not-exist.json"),
    )

    assert received == [None]


def test_run_index_point_forwards_discard_stats_out(monkeypatch):
    """run_index_point passes its discard_stats_out straight through to
    calibrate_synthetic -- proven by a monkeypatched calibrate_synthetic
    that records the kwarg it received, never a real solve."""
    received_kwargs: dict = {}

    def _fake_calibrate_synthetic(scenario, **kwargs):
        received_kwargs.update(kwargs)

        class _Cam:
            water_z = scenario.n_water

        class _Result:
            cameras = {"cam0": _Cam()}

        return _Result(), object()

    def _fake_evaluate_calibration(result, detections, board):
        return _make_evaluation()

    monkeypatch.setattr(e5mod, "calibrate_synthetic", _fake_calibrate_synthetic)
    monkeypatch.setattr(e5mod, "evaluate_calibration", _fake_evaluate_calibration)

    stats: dict = {}
    row = run_index_point(
        n_assumed=1.335, n_true=N_TRUE, n_frames=4, seed=1, discard_stats_out=stats
    )

    assert received_kwargs.get("discard_stats_out") is stats
    assert row["n_assumed"] == 1.335


def test_calibration_and_holdout_trajectories_share_one_depth_range(monkeypatch):
    """D-19.3-04: E5's calibration trajectory and its held-out trajectory
    must resolve to the SAME `depth_range` (and the same `board`) -- a
    calibration set and a held-out set built at different depths would
    silently make E5's generalization number measure the wrong thing. Proven
    by spying on `generate_real_rig_trajectory`'s two call sites (never a
    real solve, matching this module's own monkeypatched-`calibrate_synthetic`
    discipline)."""
    calls: list[dict] = []
    original = e5mod.generate_real_rig_trajectory

    def _spy(*args, **kwargs):
        calls.append(kwargs)
        return original(*args, **kwargs)

    monkeypatch.setattr(e5mod, "generate_real_rig_trajectory", _spy)

    def _fake_calibrate_synthetic(scenario, **kwargs):
        class _Cam:
            water_z = scenario.n_water

        class _Result:
            cameras = {"cam0": _Cam()}

        return _Result(), object()

    def _fake_evaluate_calibration(result, detections, board):
        return _make_evaluation()

    monkeypatch.setattr(e5mod, "calibrate_synthetic", _fake_calibrate_synthetic)
    monkeypatch.setattr(e5mod, "evaluate_calibration", _fake_evaluate_calibration)

    run_index_point(n_assumed=1.335, n_true=N_TRUE, n_frames=4, seed=1)

    assert len(calls) == 2, "expected exactly one calibration + one holdout call"
    calib_kwargs, holdout_kwargs = calls

    assert "depth_range" in calib_kwargs and "depth_range" in holdout_kwargs
    assert calib_kwargs["depth_range"] == holdout_kwargs["depth_range"]
    assert "board" in calib_kwargs and "board" in holdout_kwargs
    assert calib_kwargs["board"] == holdout_kwargs["board"] == e5mod.BOARD_CONFIG
    assert calib_kwargs["seed"] != holdout_kwargs["seed"]


# ---------------------------------------------------------------------------
# Plan 19.2-27 Task 5: discard_stats_out is numerically inert
# ---------------------------------------------------------------------------


def test_discard_stats_out_sink_is_numerically_inert():
    """Passing `discard_stats_out` through `calibrate_synthetic` does not
    perturb any returned value -- matches E5's own call shape
    (`normal_fixed=E5_NORMAL_FIXED`, `refine_intrinsics=E5_REFINE_
    INTRINSICS`). Uses the package's cheap 'minimal' preset so this stays in
    the fast suite; a passivity proof, not a convergence study (plan 26's
    pattern)."""
    scenario = create_scenario("minimal", seed=1)
    kwargs = dict(
        n_water=1.0,
        refine_intrinsics=E5_REFINE_INTRINSICS,
        seed=1,
        normal_fixed=E5_NORMAL_FIXED,
    )

    omitted, _ = calibrate_synthetic(scenario, **kwargs)

    stats: dict[str, int] = {}
    instrumented, _ = calibrate_synthetic(scenario, **kwargs, discard_stats_out=stats)

    assert (
        omitted.diagnostics.reprojection_error_rms
        == instrumented.diagnostics.reprojection_error_rms
    )
    assert sorted(omitted.cameras) == sorted(instrumented.cameras)
    for cam in omitted.cameras:
        np.testing.assert_array_equal(
            omitted.cameras[cam].extrinsics.R,
            instrumented.cameras[cam].extrinsics.R,
        )
        np.testing.assert_array_equal(
            omitted.cameras[cam].extrinsics.t,
            instrumented.cameras[cam].extrinsics.t,
        )
        assert omitted.cameras[cam].water_z == instrumented.cameras[cam].water_z

    # The instrumented run must have actually populated the sink -- every
    # PnP attempt bumps pnp_attempts_total unconditionally on entry
    # (_observability.py), so a clean minimal run still leaves the sink
    # non-empty even with zero discards. A vacuous (never-populated) sink
    # would make the inertness proof above meaningless.
    assert stats, "discard_stats_out was supplied but never populated"


# ---------------------------------------------------------------------------
# D-19.3-11 / plan 19.3-07: E5 records (never gates on) the final-solution
# guard count.
# ---------------------------------------------------------------------------


def test_discard_stats_out_carries_degenerate_count_on_a_clean_run():
    """`degenerate_observations_at_solution` is present and integer-typed in
    `discard_stats_out` on a clean run -- present-and-zero, per plan 19.3-02's
    convention for this same key, matching E5's own call shape."""
    scenario = create_scenario("minimal", seed=1)
    stats: dict[str, int] = {}
    calibrate_synthetic(
        scenario,
        n_water=1.0,
        refine_intrinsics=E5_REFINE_INTRINSICS,
        seed=1,
        normal_fixed=E5_NORMAL_FIXED,
        discard_stats_out=stats,
    )
    assert "degenerate_observations_at_solution" in stats
    assert isinstance(stats["degenerate_observations_at_solution"], int)


def test_run_index_point_sink_carries_degenerate_count():
    """run_index_point's discard_stats_out sink (already forwarded straight
    through to calibrate_synthetic) carries degenerate_observations_at_solution
    end to end -- exercised through E5's own real call shape, not a mock."""
    stats: dict[str, int] = {}
    run_index_point(
        n_assumed=N_TRUE,
        n_true=N_TRUE,
        n_frames=4,
        seed=1,
        refine_intrinsics=False,
        discard_stats_out=stats,
    )
    assert "degenerate_observations_at_solution" in stats
    assert isinstance(stats["degenerate_observations_at_solution"], int)
