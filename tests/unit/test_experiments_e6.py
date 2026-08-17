"""Unit tests for `experiments/e6_generalization_sweep.py` (EXP-10).

Fast unit tests only: hand-built fixtures directly constructed, no actual
calibration solve of any kind, none marked slow -- with one deliberate
exception (plan 19.2-27 Task 5's inertness proof, which runs the package's
cheap 'minimal' preset once with and once without the new sinks; still not
marked slow). `--smoke` (the E6-specific real, small solve) is verified
separately by the plan's own `<verify>` block, not by pytest.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

import experiments.e4_benchmark_grid as e4
import experiments.e6_generalization_sweep as m
from aquacal.calibration._observability import SolverDiagnostics
from aquacal.datasets import create_scenario
from aquacal.datasets.pipelines import calibrate_synthetic

REQUIRED_ENVIRONMENT_KEYS = {
    "aquacal_version",
    "git_sha",
    "python_version",
    "numpy_version",
    "scipy_version",
}


def _sample_metrics() -> dict:
    """A hand-built metrics dict with exactly `_METRIC_COLUMNS`' keys."""
    return {
        "optimality_stage3_interface_optimization": 1.2e-6,
        "optimality_stage3_intrinsic_pass": 3.4e-7,
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
        "water_z_error_mm_signed_mean": -0.6,
        "z_position_error_mm_gauge_corrected_mean": 0.1,
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
    """No E6_COLUMNS name implies a pass/fail verdict (D-12).

    Tokenized on `_` rather than a raw substring search: plan 19.2-27 Task 1
    adds `optimality_stage3_intrinsic_pass`, whose `pass` token names a
    SOLVER STAGE (E4's own established vocabulary, `stage3_intrinsic_pass`
    -- the intrinsics-refinement pass), not a verdict. A raw substring match
    on "pass" would false-positive on that legitimate name; excluding
    `intrinsic_pass` specifically (rather than dropping the `pass` token
    check for every column) keeps the guard meaningful for any OTHER column
    that might use "pass"/"fail" as a real verdict.
    """
    verdict_tokens = {
        "pass",
        "fail",
        "verdict",
        "acceptable",
        "holds",
        "degraded",
        "converged",
        "diverged",
    }
    for col in m.E6_COLUMNS:
        tokens = set(col.split("_"))
        if "intrinsic" in tokens and "pass" in tokens:
            tokens.discard("pass")
        assert not (tokens & verdict_tokens), col


def test_water_z_error_helper():
    """A known 3mm discrepancy on one camera, 0 on the rest, gives the expected mm mean."""
    true_water_zs = {"cam0": 1.0, "cam1": 1.0, "cam2": 1.0}
    estimated_water_zs = {"cam0": 1.0, "cam1": 1.003, "cam2": 1.0}
    result = m.compute_water_z_error_mm_mean(estimated_water_zs, true_water_zs)
    assert result == pytest.approx(1.0, abs=1e-6)


def test_water_z_error_signed_vs_absolute_are_provably_different():
    """The signed helper preserves sign; the absolute helper (pre-existing)
    does not -- the two columns are provably different quantities (FIX-03,
    23-03)."""
    true_water_zs = {"cam0": 1.0, "cam1": 1.0, "cam2": 1.0}
    estimated_water_zs = {"cam0": 1.003, "cam1": 0.997, "cam2": 1.0}
    signed = m.compute_water_z_error_mm_signed(estimated_water_zs, true_water_zs)
    assert signed == pytest.approx(0.0, abs=1e-9)

    estimated_water_zs_all_negative = {"cam0": 0.997, "cam1": 1.0, "cam2": 1.0}
    signed_negative = m.compute_water_z_error_mm_signed(
        estimated_water_zs_all_negative, true_water_zs
    )
    absolute_negative = m.compute_water_z_error_mm_mean(
        estimated_water_zs_all_negative, true_water_zs
    )
    assert signed_negative == pytest.approx(-1.0, abs=1e-9)
    assert absolute_negative == pytest.approx(1.0, abs=1e-9)


def test_compute_water_z_error_mm_signed_matches_committed_identity_shape():
    """Mirrors the acceptance criterion's hand-built pair: signed and
    absolute diverge for a single-camera discrepancy."""
    estimated = {"c0": 1.0, "c1": 0.997}
    true = {"c0": 1.0, "c1": 1.0}
    assert m.compute_water_z_error_mm_signed(estimated, true) == pytest.approx(
        -1.5, abs=1e-9
    )
    assert m.compute_water_z_error_mm_mean(estimated, true) == pytest.approx(
        1.5, abs=1e-9
    )


def test_build_per_camera_rows_shape_and_identity(monkeypatch):
    """One row per camera, exactly E6_PER_CAMERA_COLUMNS' keys,
    is_reference_camera true for exactly one camera, and the
    h_c_error_mm_signed identity holds for every row (FIX-03, 23-03)."""

    class _StubScenario:
        intrinsics = {"cam0": object(), "cam1": object(), "cam2": object()}
        water_zs = {"cam0": 1.0, "cam1": 1.0, "cam2": 1.0}

    class _StubCal:
        def __init__(self, water_z):
            self.water_z = water_z

    class _StubResult:
        cameras = {
            "cam0": _StubCal(1.0005),
            "cam1": _StubCal(0.999),
            "cam2": _StubCal(1.002),
        }

    scenario = _StubScenario()
    result = _StubResult()

    def _fake_per_camera_errors(result, scenario, gauge_correct_z=False):
        base = {
            "cam0": {"z_position_error_mm": 0.0},
            "cam1": {"z_position_error_mm": -1.2},
            "cam2": {"z_position_error_mm": 2.4},
        }
        if gauge_correct_z:
            return {
                k: {"z_position_error_mm": v["z_position_error_mm"] + 0.1}
                for k, v in base.items()
            }
        return base

    monkeypatch.setattr(m, "compute_per_camera_errors", _fake_per_camera_errors)

    config = {"axis": "layout", "axis_value": "line", "config_key": "layout_line"}
    rows = m.build_per_camera_rows(config, seed=43, scenario=scenario, result=result)

    assert len(rows) == 3
    for row in rows:
        assert set(row.keys()) == set(m.E6_PER_CAMERA_COLUMNS)

    reference_rows = [r for r in rows if r["is_reference_camera"]]
    assert len(reference_rows) == 1
    assert reference_rows[0]["camera"] == "cam0"

    for row in rows:
        assert row["h_c_error_mm_signed"] == pytest.approx(
            row["water_z_error_mm_signed"] - row["z_position_error_mm_raw"], abs=1e-9
        )


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


def test_scale_axis_is_a_factor_of_two_ladder_about_the_new_baseline():
    """D-19.3-07: SCALE_AXIS_VALUES' half_scale/default/double_scale rescale
    the working-volume depth EXTENT above the derived clearance floor
    (`GRID_DEPTH_RANGE[0]`), keeping the floor itself fixed at every scale
    value -- and remain a factor-of-two ladder, derived from E4's constants
    rather than hardcoded a second time. `xy_extent`/`spacing` still scale
    directly."""
    labels = [v[0] for v in m.SCALE_AXIS_VALUES]
    assert labels == ["half_scale", "default", "double_scale"]

    half, default, double = m.SCALE_AXIS_VALUES
    assert default[1] is None and default[2] is None and default[3] is None

    half_depth_range, half_xy_extent, half_spacing = half[1], half[2], half[3]
    double_depth_range, double_xy_extent, double_spacing = (
        double[1],
        double[2],
        double[3],
    )

    assert half_spacing == pytest.approx(0.5 * e4.GRID_SPACING)
    assert double_spacing == pytest.approx(2.0 * e4.GRID_SPACING)
    assert double_xy_extent == pytest.approx(4.0 * half_xy_extent)

    # The floor (GRID_DEPTH_RANGE[0]) is FIXED for every scale value -- only
    # the extent above it scales (D-19.3-07). This is what makes every scale
    # value legal by construction: the clearance floor never moves.
    floor = e4.GRID_DEPTH_RANGE[0]
    assert half_depth_range[0] == pytest.approx(floor)
    assert double_depth_range[0] == pytest.approx(floor)
    assert half_depth_range[1] > half_depth_range[0]
    assert double_depth_range[1] > double_depth_range[0]

    baseline_extent = e4.GRID_DEPTH_RANGE[1] - floor
    half_extent = half_depth_range[1] - floor
    double_extent = double_depth_range[1] - floor
    assert half_extent == pytest.approx(0.5 * baseline_extent)
    assert double_extent == pytest.approx(2.0 * baseline_extent)
    assert double_extent == pytest.approx(4.0 * half_extent)

    # The baseline scale value reproduces GRID_DEPTH_RANGE exactly.
    assert m._scaled_depth_range(1.0) == pytest.approx(e4.GRID_DEPTH_RANGE)


def test_scale_axis_legal_at_production_frame_count():
    """GEOM-03/D-19.3-07: every SCALE_AXIS_VALUES entry -- and, as a broader
    regression net, every INDEX_AXIS_VALUES/LAYOUT_AXIS_VALUES entry too --
    builds a legal scenario at PRODUCTION frame count (BASELINE_N_FRAMES),
    with construction never raising and no board corner in any frame at or
    above `max(water_zs)`.

    Production frame count matters here, not a smoke value: anti-pattern #4
    is a geometry variant that converges (or merely constructs without
    raising) at a small frame count while the underlying bug only surfaces
    with ~50+ frames worth of sampled board poses. This test asserts the
    literal it uses matches the sweep's own configured baseline frame count
    rather than hardcoding a small number, so a future change to
    BASELINE_N_FRAMES cannot silently downgrade this test back to a smoke
    check.

    Construction only -- no `calibrate_synthetic` call anywhere in this test.
    """
    from aquacal.core.board import BoardGeometry
    from aquacal.utils.transforms import rvec_to_matrix

    assert m.BASELINE_N_FRAMES == 100, (
        "this test intentionally asserts against the sweep's own "
        "BASELINE_N_FRAMES rather than hardcoding a literal"
    )
    n_frames = m.BASELINE_N_FRAMES

    configs = m.build_axis_configurations()
    assert any(c["axis"] == "scale" for c in configs)
    assert any(c["axis"] == "index" for c in configs)
    assert any(c["axis"] == "layout" for c in configs)

    for config in configs:
        scenario = m.build_grid_scenario(
            n_cameras=config["n_cameras"],
            n_frames=n_frames,
            seed=42,
            layout=config["layout"],
            depth_range=config["depth_range"],
            xy_extent=config["xy_extent"],
            spacing=config["spacing"],
            n_water=config["n_water"],
        )
        max_water_z = max(scenario.water_zs.values())
        geometry = BoardGeometry(scenario.board_config)
        corners_local = np.array(
            list(geometry.corner_positions.values()), dtype=np.float64
        )
        for pose in scenario.board_poses:
            R = rvec_to_matrix(pose.rvec)
            world_corners = (R @ corners_local.T).T + pose.tvec
            assert np.all(world_corners[:, 2] > max_water_z), (
                f"axis={config['axis']} axis_value={config['axis_value']} "
                f"frame {pose.frame_idx}: a corner is at or above "
                f"max(water_zs)={max_water_z}"
            )


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


# ---------------------------------------------------------------------------
# COV-04: the n_cameras axis, opt-in and inert by default (plan 19.5-06 Task 1)
# ---------------------------------------------------------------------------


def test_default_call_unchanged_14_configs_3_baseline():
    """build_axis_configurations() with no arguments still returns exactly
    14 dicts with exactly 3 carrying is_baseline=True -- the cameras axis
    must never leak into the default call."""
    configs = m.build_axis_configurations()
    assert len(configs) == 14
    assert sum(1 for c in configs if c["is_baseline"]) == 3
    assert all(c["axis"] != "cameras" for c in configs)


def test_opt_in_call_17_configs_4_baseline():
    """build_axis_configurations(include_cameras_axis=True) returns exactly
    17 dicts with exactly 4 carrying is_baseline=True."""
    configs = m.build_axis_configurations(include_cameras_axis=True)
    assert len(configs) == 17
    assert sum(1 for c in configs if c["is_baseline"]) == 4
    cameras_configs = [c for c in configs if c["axis"] == "cameras"]
    assert len(cameras_configs) == 3
    assert {c["axis_value"] for c in cameras_configs} == {"8", "12", "16"}


def test_opt_in_call_first_14_equal_default_call():
    """The cameras axis only appends -- it never reorders the first 14
    entries relative to the default call's own return value."""
    default_configs = m.build_axis_configurations()
    opt_in_configs = m.build_axis_configurations(include_cameras_axis=True)
    assert opt_in_configs[:14] == default_configs


def test_cameras_axis_non_baseline_rows_have_no_scale_geometry():
    """Every axis == 'cameras' non-baseline dict has xy_extent is None and
    spacing is None -- geometry is derived from n_cameras alone, exactly as
    the baseline's own geometry is."""
    configs = m.build_axis_configurations(include_cameras_axis=True)
    cameras_non_baseline = [
        c for c in configs if c["axis"] == "cameras" and not c["is_baseline"]
    ]
    assert len(cameras_non_baseline) == 2
    for c in cameras_non_baseline:
        assert c["xy_extent"] is None
        assert c["spacing"] is None
        assert c["depth_range"] is None


def test_cameras_axis_baseline_shares_baseline_config_key():
    """The cameras=12 (BASELINE_N_CAMERAS) row is_baseline=True and shares
    config_key 'baseline' with the other three axes' baseline rows (the same
    scene, computed once)."""
    configs = m.build_axis_configurations(include_cameras_axis=True)
    cameras_baseline = [
        c for c in configs if c["axis"] == "cameras" and c["is_baseline"]
    ]
    assert len(cameras_baseline) == 1
    assert cameras_baseline[0]["config_key"] == "baseline"
    assert cameras_baseline[0]["n_cameras"] == m.BASELINE_N_CAMERAS

    baseline_keys = {c["config_key"] for c in configs if c["is_baseline"]}
    assert baseline_keys == {"baseline"}


def test_scenario_identity_keys_still_excludes_seed():
    """_SCENARIO_IDENTITY_KEYS remains without 'seed' -- the isolated-
    directory workaround (Task 2), not a fix to the identity tuple, is how
    the seed-blind checkpoint cache is handled."""
    assert "seed" not in m._SCENARIO_IDENTITY_KEYS
    assert "n_cameras" in m._SCENARIO_IDENTITY_KEYS


def test_status_vocabulary():
    """The row builder's status values come from {ok, degenerate, failed, skipped_existing}
    (D-19.3-11 adds "degenerate")."""
    assert m.STATUS_VALUES == {"ok", "degenerate", "failed", "skipped_existing"}
    configs = m.build_axis_configurations()
    config = configs[0]
    for status in sorted(m.STATUS_VALUES):
        row = m.build_row(
            config,
            seed=42,
            n_frames=10,
            metrics=_sample_metrics() if status in {"ok", "degenerate"} else None,
            status=status,
            status_reason="" if status == "ok" else "reason",
        )
        assert row["status"] in m.STATUS_VALUES
        if status not in {"ok", "degenerate"}:
            for col in m._METRIC_COLUMNS:
                assert row[col] is None
        else:
            for col in m._METRIC_COLUMNS:
                assert row[col] is not None


# ---------------------------------------------------------------------------
# WR-02: solver optimality is recorded, as a measurement, not a verdict
# (plan 19.2-27 Task 1)
# ---------------------------------------------------------------------------


def test_optimality_columns_present_and_ordered():
    """Both optimality columns exist in E6_COLUMNS and _METRIC_COLUMNS."""
    assert "optimality_stage3_interface_optimization" in m.E6_COLUMNS
    assert "optimality_stage3_intrinsic_pass" in m.E6_COLUMNS
    assert "optimality_stage3_interface_optimization" in m._METRIC_COLUMNS
    assert "optimality_stage3_intrinsic_pass" in m._METRIC_COLUMNS


def test_optimality_reaches_built_row():
    """A hand-built metrics dict's optimality values flow through build_row unchanged."""
    configs = m.build_axis_configurations()
    config = configs[0]
    metrics = _sample_metrics()
    row = m.build_row(
        config, seed=42, n_frames=10, metrics=metrics, status="ok", status_reason=""
    )
    assert (
        row["optimality_stage3_interface_optimization"]
        == metrics["optimality_stage3_interface_optimization"]
    )
    assert (
        row["optimality_stage3_intrinsic_pass"]
        == metrics["optimality_stage3_intrinsic_pass"]
    )


def test_optimality_null_when_status_not_ok():
    """Both optimality columns null out on a non-'ok' row, like every other metric."""
    configs = m.build_axis_configurations()
    config = configs[0]
    row = m.build_row(
        config,
        seed=42,
        n_frames=10,
        metrics=None,
        status="failed",
        status_reason="synthetic failure",
    )
    assert row["optimality_stage3_interface_optimization"] is None
    assert row["optimality_stage3_intrinsic_pass"] is None


def test_compute_configuration_metrics_reads_diagnostics_optimality(monkeypatch):
    """compute_configuration_metrics reads .optimality off the SolverDiagnostics
    sinks it is given, and nulls out when a sink is absent (e.g.
    refine_intrinsics=False, so the intrinsic pass never runs)."""
    diag_interface = SolverDiagnostics()
    diag_interface.optimality = 1.5e-6
    diag_intrinsic = SolverDiagnostics()
    diag_intrinsic.optimality = 2.5e-7

    class _StubScenario:
        water_zs: dict = {}

    class _StubResult:
        cameras: dict = {}

    class _StubReconstruction:
        mean = 0.001
        rmse = 0.0012
        signed_mean = 0.0002
        num_comparisons = 10

    class _StubReprojection:
        rms = 0.3

    class _StubEvaluation:
        reprojection = _StubReprojection()
        reconstruction = _StubReconstruction()
        num_frames = 5

    monkeypatch.setattr(
        m,
        "compute_per_camera_errors",
        lambda result, scenario, gauge_correct_z=False: {},
    )

    metrics = m.compute_configuration_metrics(
        _StubScenario(),
        _StubResult(),
        _StubEvaluation(),
        diag_interface,
        diag_intrinsic,
    )
    assert metrics["optimality_stage3_interface_optimization"] == 1.5e-6
    assert metrics["optimality_stage3_intrinsic_pass"] == 2.5e-7

    metrics_no_diag = m.compute_configuration_metrics(
        _StubScenario(), _StubResult(), _StubEvaluation()
    )
    assert metrics_no_diag["optimality_stage3_interface_optimization"] is None
    assert metrics_no_diag["optimality_stage3_intrinsic_pass"] is None


def test_no_optimality_thresholding_in_e6_source():
    """D-12: optimality is recorded as a measurement -- no comparison
    operator is ever applied to it anywhere in the module. A threshold
    (`if diag.optimality < X`) would encode a convergence verdict in code
    even without a named verdict column, which is exactly what D-12
    forbids. Narrower than a bare word search for "verdict" (which would
    also flag this module's own prose correctly explaining the D-12
    principle in its docstrings) -- this checks the CODE, not the comments."""
    source = Path(m.__file__).read_text(encoding="utf-8")
    thresholding = re.compile(r"optimality\s*(<=|>=|==|!=|<|>)")
    assert not thresholding.search(source), (
        "found a comparison operator applied to optimality in "
        "e6_generalization_sweep.py -- D-12 forbids deriving a verdict from it"
    )


# ---------------------------------------------------------------------------
# CR-02 / WR-08: resume path returns the checkpoint it wrote (Task 1)
# ---------------------------------------------------------------------------


def test_resume_returns_cached_ok_metrics(tmp_path):
    """A force=False re-entry over an 'ok' checkpoint returns its cached metrics,
    not None -- CR-02. On EXPECTED_BASE this fails: the skip branch returns
    `metrics: None` unconditionally without opening the file."""
    configs = m.build_axis_configurations()
    config = configs[0]
    configs_dir = tmp_path / "e6_configs"
    configs_dir.mkdir()
    metrics = _sample_metrics()
    checkpoint = {
        "status": "ok",
        "status_reason": "",
        "metrics": metrics,
        "seed": 42,
        "n_frames": 100,
    }
    (configs_dir / f"{config['config_key']}.json").write_text(json.dumps(checkpoint))

    outcome = m.run_configuration(config, seed=42, n_frames=100, out_dir=tmp_path)

    assert outcome["status"] == "ok"
    assert outcome["metrics"] == metrics
    row = m.build_row(
        config,
        seed=42,
        n_frames=100,
        metrics=outcome["metrics"],
        status=outcome["status"],
        status_reason=outcome["status_reason"],
    )
    for col in m._METRIC_COLUMNS:
        assert row[col] is not None


def test_resume_returns_cached_failed_reason(tmp_path):
    """A force=False re-entry over a 'failed' checkpoint returns the recorded
    status_reason, not "" -- WR-08. On EXPECTED_BASE this fails: the skip
    branch always returns `status_reason: ""`."""
    configs = m.build_axis_configurations()
    config = configs[0]
    configs_dir = tmp_path / "e6_configs"
    configs_dir.mkdir()
    checkpoint = {
        "status": "failed",
        "status_reason": "KeyError: 'cam11'",
        "metrics": None,
        "seed": 42,
        "n_frames": 100,
    }
    (configs_dir / f"{config['config_key']}.json").write_text(json.dumps(checkpoint))

    outcome = m.run_configuration(config, seed=42, n_frames=100, out_dir=tmp_path)

    assert outcome["status"] == "failed"
    assert outcome["status_reason"] == "KeyError: 'cam11'"
    assert outcome["metrics"] is None


def test_resume_survives_corrupt_checkpoint(tmp_path, monkeypatch):
    """A truncated/corrupt (non-JSON) checkpoint degrades to a re-run, never an
    exception out of run_configuration. `build_grid_scenario` is monkeypatched
    to fail fast so this stays a fast unit test rather than a real solve."""
    configs = m.build_axis_configurations()
    config = configs[0]
    configs_dir = tmp_path / "e6_configs"
    configs_dir.mkdir()
    (configs_dir / f"{config['config_key']}.json").write_text("{not valid json")

    def _boom(**kwargs):
        raise RuntimeError("synthetic failure for the corrupt-checkpoint test")

    monkeypatch.setattr(m, "build_grid_scenario", _boom)

    outcome = m.run_configuration(config, seed=42, n_frames=100, out_dir=tmp_path)

    assert outcome["status"] == "failed"
    assert "synthetic failure" in outcome["status_reason"]


def test_force_true_still_reruns_and_overwrites(tmp_path, monkeypatch):
    """force=True re-runs and overwrites an existing checkpoint, unchanged."""
    configs = m.build_axis_configurations()
    config = configs[0]
    configs_dir = tmp_path / "e6_configs"
    configs_dir.mkdir()
    stale_checkpoint = {
        "status": "ok",
        "status_reason": "",
        "metrics": _sample_metrics(),
        "seed": 42,
        "n_frames": 100,
    }
    (configs_dir / f"{config['config_key']}.json").write_text(
        json.dumps(stale_checkpoint)
    )

    def _boom(**kwargs):
        raise RuntimeError("forced re-run reached the scenario builder")

    monkeypatch.setattr(m, "build_grid_scenario", _boom)

    outcome = m.run_configuration(
        config, seed=42, n_frames=100, out_dir=tmp_path, force=True
    )

    assert outcome["status"] == "failed"
    assert "forced re-run reached the scenario builder" in outcome["status_reason"]


def test_resume_restores_per_camera_rows_from_schema_v2_checkpoint(tmp_path):
    """A schema_version: 2 checkpoint's per_camera_rows are restored into
    per_camera_rows_out on resume (FIX-03, 23-03)."""
    configs = m.build_axis_configurations()
    config = configs[0]
    configs_dir = tmp_path / "e6_configs"
    configs_dir.mkdir()
    per_camera_rows = [
        {
            "axis": config["axis"],
            "axis_value": config["axis_value"],
            "config_key": config["config_key"],
            "seed": 42,
            "camera": "cam0",
            "is_reference_camera": True,
            "z_position_error_mm_raw": 0.0,
            "z_position_error_mm_gauge_corrected": 0.1,
            "water_z_error_mm_signed": -0.36,
            "h_c_error_mm_signed": -0.36,
        }
    ]
    checkpoint = {
        "status": "ok",
        "status_reason": "",
        "metrics": _sample_metrics(),
        "seed": 42,
        "n_frames": 100,
        "schema_version": 2,
        "per_camera_rows": per_camera_rows,
    }
    (configs_dir / f"{config['config_key']}.json").write_text(json.dumps(checkpoint))

    sink: list[dict] = []
    m.run_configuration(
        config, seed=42, n_frames=100, out_dir=tmp_path, per_camera_rows_out=sink
    )

    assert sink == per_camera_rows


def test_resume_from_schema_v1_checkpoint_warns_and_adds_no_rows(tmp_path, caplog):
    """A schema_version: 1 checkpoint (predating FIX-03) resumes with no
    per-camera rows, logs a warning naming the config key, and does not
    raise (FIX-03, 23-03)."""
    configs = m.build_axis_configurations()
    config = configs[0]
    configs_dir = tmp_path / "e6_configs"
    configs_dir.mkdir()
    checkpoint = {
        "status": "ok",
        "status_reason": "",
        "metrics": _sample_metrics(),
        "seed": 42,
        "n_frames": 100,
        "schema_version": 1,
    }
    (configs_dir / f"{config['config_key']}.json").write_text(json.dumps(checkpoint))

    sink: list[dict] = []
    with caplog.at_level("WARNING"):
        outcome = m.run_configuration(
            config, seed=42, n_frames=100, out_dir=tmp_path, per_camera_rows_out=sink
        )

    assert outcome["status"] == "ok"
    assert sink == []
    assert any(config["config_key"] in rec.message for rec in caplog.records)


def test_false_resume_concession_removed():
    """The docstring no longer claims a resumed CSV requires --force to fill
    every metric column -- that sentence described the CR-02 defect as an
    intentional limitation."""
    source = Path(m.__file__).read_text(encoding="utf-8")
    assert "requires re-running with `force=True`" not in source


# ---------------------------------------------------------------------------
# D-31: four-field provenance -- sidecar plus self-describing checkpoints (Task 2)
# ---------------------------------------------------------------------------


def test_checkpoint_has_provenance_keys(tmp_path, monkeypatch):
    """Every checkpoint written by run_configuration is self-describing: it
    carries schema_version, an environment block, and solver_config['seed']
    in addition to the pre-existing fields."""
    configs = m.build_axis_configurations()
    config = configs[0]

    def _fail_fast(**kwargs):
        raise RuntimeError("keep this test fast -- fail before any real solve")

    monkeypatch.setattr(m, "build_grid_scenario", _fail_fast)

    outcome = m.run_configuration(config, seed=42, n_frames=100, out_dir=tmp_path)
    assert outcome["status"] == "failed"

    checkpoint_path = tmp_path / "e6_configs" / f"{config['config_key']}.json"
    with open(checkpoint_path) as f:
        checkpoint = json.load(f)

    required_keys = {
        "schema_version",
        "environment",
        "seed",
        "solver_config",
        "status",
        "status_reason",
        "metrics",
        "n_frames",
        "config",
    }
    assert required_keys <= set(checkpoint)
    assert checkpoint["solver_config"]["seed"] == 42
    assert REQUIRED_ENVIRONMENT_KEYS <= set(checkpoint["environment"])


def test_provenance_sidecar_shape():
    """E6's provenance sidecar matches E3's exact shape (D-31)."""
    sidecar = m.build_provenance_sidecar(seed=42)
    assert sidecar["experiment"] == "e6"
    assert "schema_version" in sidecar
    assert sidecar["seed"] == 42
    assert sidecar["solver_config"]["seed"] == 42
    assert REQUIRED_ENVIRONMENT_KEYS <= set(sidecar["environment"])


def test_provenance_sidecar_reuses_a_passed_environment():
    """build_provenance_sidecar stamps the CALLER's environment block when
    given one, rather than capturing a second, potentially different, one."""
    fixed_environment = {
        "aquacal_version": "x",
        "git_sha": "fixed-sha",
        "python_version": "y",
        "numpy_version": "z",
        "scipy_version": "w",
    }
    sidecar = m.build_provenance_sidecar(seed=42, environment=fixed_environment)
    assert sidecar["environment"] == fixed_environment


# ---------------------------------------------------------------------------
# Provenance (D-31, EXP-11): environment captured ONCE per sweep, not once
# per configuration (plan 19.2-27 Task 3)
# ---------------------------------------------------------------------------


def test_run_sweep_captures_environment_once(tmp_path, monkeypatch):
    """Every checkpoint written within one run_sweep call carries an
    IDENTICAL git_sha, and capture_environment is called exactly once for
    the whole sweep -- not once per configuration.

    Measured cause (2026-07-31): `capture_environment()` shells out to `git
    rev-parse` per call, so a commit landing mid-sweep previously split
    `git_sha` across the artifact set (`baseline.json` recorded one sha, the
    other eleven checkpoints recorded another). On EXPECTED_BASE (before
    this fix), `run_configuration` calls `capture_environment()` itself for
    every configuration, so this test's call-count assertion fails there.
    """
    call_count = {"n": 0}

    def _fake_capture_environment():
        call_count["n"] += 1
        return {
            "aquacal_version": "x",
            "git_sha": f"sha-{call_count['n']}",
            "python_version": "y",
            "numpy_version": "z",
            "scipy_version": "w",
        }

    monkeypatch.setattr(m, "capture_environment", _fake_capture_environment)

    def _fail_fast(**kwargs):
        raise RuntimeError("keep this test fast -- fail before any real solve")

    monkeypatch.setattr(m, "build_grid_scenario", _fail_fast)

    configs = m.build_axis_configurations()
    # Three distinct config_keys, each a separate run_configuration call
    # (and therefore a separate checkpoint write): the shared "baseline" key
    # plus two of the non-baseline index-axis entries.
    selected = [
        c
        for c in configs
        if c["config_key"] in {"baseline", "index_1.36", "index_1.39"}
    ]
    assert {c["config_key"] for c in selected} == {
        "baseline",
        "index_1.36",
        "index_1.39",
    }

    m.run_sweep(selected, seed=42, n_frames=10, out_dir=tmp_path, force=True)

    assert call_count["n"] == 1, (
        f"capture_environment was called {call_count['n']} times for one "
        "sweep of 3 distinct configurations; expected exactly 1"
    )

    configs_dir = tmp_path / "e6_configs"
    written = sorted(configs_dir.glob("*.json"))
    assert len(written) == 3
    git_shas = set()
    for path in written:
        with open(path) as f:
            checkpoint = json.load(f)
        git_shas.add(checkpoint["environment"]["git_sha"])
    assert len(git_shas) == 1, f"checkpoints disagree on git_sha: {git_shas}"


def test_e6_columns_count():
    """generalization_sweep.csv's header carries 33 columns: the original 31
    (28 base + two optimality columns, WR-02, plus
    degenerate_observations_at_solution) plus the two FIX-03 (23-03) columns
    -- water_z_error_mm_signed_mean and
    z_position_error_mm_gauge_corrected_mean -- appended at the end.
    degenerate_observations_at_solution stays PRESENT but is no longer last;
    its invariant moved to test_degenerate_column_appended_last, which now
    checks its fixed index rather than "is the final column"."""
    assert len(m.E6_COLUMNS) == 33
    assert "degenerate_observations_at_solution" in m.E6_COLUMNS
    assert "water_z_error_mm_signed_mean" in m.E6_COLUMNS
    assert "z_position_error_mm_gauge_corrected_mean" in m.E6_COLUMNS
    assert m.E6_COLUMNS[-1] == "z_position_error_mm_gauge_corrected_mean"


# ---------------------------------------------------------------------------
# WR-03: cached config identity must match the recomputed configuration
# ---------------------------------------------------------------------------


def test_config_identity_matches_helper():
    configs = m.build_axis_configurations()
    config = configs[0]
    identity = m._resolve_config_identity(config)
    cached_config = json.loads(json.dumps(identity))
    assert m._config_identity_matches(config, cached_config)

    mutated = dict(cached_config)
    mutated["n_water"] = (mutated.get("n_water") or 1.0) + 100.0
    assert not m._config_identity_matches(config, mutated)


def test_baseline_configs_match_despite_differing_axis_labels():
    """Plan 19.2-27 Task 2 (WR-03 collision fix): the three `is_baseline`
    configurations (`index/1.333`, `layout/grid`, `scale/default`) are the
    SAME scene under three different `axis`/`axis_value` labels
    (`build_axis_configurations`' own docstring). A checkpoint recorded from
    ANY ONE of them must match all three -- comparing full identity
    (including the label fields) previously guaranteed a mismatch no
    correct run could avoid, since `axis`/`axis_value` necessarily differ
    across the three. This is the failure `--check` could not pass for any
    baseline row (19.2-22-SUMMARY.md § `--check`)."""
    configs = m.build_axis_configurations()
    baseline_configs = [c for c in configs if c["is_baseline"]]
    assert len(baseline_configs) == 3
    assert {c["axis"] for c in baseline_configs} == {"index", "layout", "scale"}

    # A checkpoint identity recorded from the FIRST baseline config (the
    # "index" axis's row) -- exactly what `run_configuration` would write
    # after computing this shared scene once.
    recorded = json.loads(json.dumps(m._resolve_config_identity(baseline_configs[0])))

    for config in baseline_configs:
        assert m._config_identity_matches(config, recorded), (
            f"baseline config axis={config['axis']!r} axis_value="
            f"{config['axis_value']!r} did not match the identity recorded "
            f"from axis={baseline_configs[0]['axis']!r}"
        )


def test_scenario_field_mutation_still_trips_wr03_after_the_restriction(tmp_path):
    """The restricted (scenario-only) identity comparison still catches a
    checkpoint that predates a SCENARIO change -- proving Task 2 fixed the
    collision at its cause rather than loosening the guard into a no-op.
    Mutates `layout` (not `n_water`, to exercise a different
    scenario-determining field than `test_reconstitute_row_flags_mismatched_
    config` already covers) on one of the three baseline configurations,
    which under the OLD full-identity comparison would ALSO have tripped --
    the discriminating claim here is that it STILL trips under the NEW
    restricted comparison, i.e. `layout` was not accidentally dropped from
    `_SCENARIO_IDENTITY_KEYS`."""
    config = [c for c in m.build_axis_configurations() if c["is_baseline"]][0]
    configs_dir = tmp_path / "e6_configs"
    configs_dir.mkdir()
    identity = json.loads(json.dumps(m._resolve_config_identity(config)))
    assert identity["layout"] == "grid"
    mutated = {**identity, "layout": "ring"}
    checkpoint = {
        "status": "ok",
        "status_reason": "",
        "metrics": _sample_metrics(),
        "seed": 42,
        "n_frames": 100,
        "config": mutated,
    }
    (configs_dir / f"{config['config_key']}.json").write_text(json.dumps(checkpoint))

    row = m._reconstitute_row(config, configs_dir, default_seed=42)

    assert row["status"] == "failed"
    assert "does not match" in row["status_reason"]
    for col in m._METRIC_COLUMNS:
        assert row[col] is None


def test_axis_label_mutation_alone_does_not_trip_wr03(tmp_path):
    """The mirror case: mutating ONLY a presentational field (`axis_value`)
    -- not a scenario field -- must NOT degrade the row, since it changes no
    property of the scene that was actually computed. This is the specific
    behavior the Task 2 fix adds; on EXPECTED_BASE (full-identity
    comparison) this test fails."""
    config = [c for c in m.build_axis_configurations() if c["is_baseline"]][0]
    configs_dir = tmp_path / "e6_configs"
    configs_dir.mkdir()
    identity = json.loads(json.dumps(m._resolve_config_identity(config)))
    # axis_value is a string on every config (build_axis_configurations casts
    # even the float index values via str()); mutate it to another axis's
    # label while leaving every scenario-determining field untouched.
    relabeled = {**identity, "axis": "layout", "axis_value": "grid"}
    checkpoint = {
        "status": "ok",
        "status_reason": "",
        "metrics": _sample_metrics(),
        "seed": 42,
        "n_frames": 100,
        "config": relabeled,
    }
    (configs_dir / f"{config['config_key']}.json").write_text(json.dumps(checkpoint))

    row = m._reconstitute_row(config, configs_dir, default_seed=42)

    assert row["status"] == "ok"
    assert row["reprojection_rms_px"] is not None


def test_reconstitute_row_flags_mismatched_config(tmp_path):
    """_run_check's row reconstitution refuses a cached checkpoint whose
    recorded config does not match the recomputed configuration (WR-03,
    T-19.2-63) -- it does not silently trust stale cached metrics."""
    config = m.build_axis_configurations()[0]
    configs_dir = tmp_path / "e6_configs"
    configs_dir.mkdir()
    identity = m._resolve_config_identity(config)
    mismatched = {**identity, "n_water": (identity.get("n_water") or 1.0) + 999.0}
    checkpoint = {
        "status": "ok",
        "status_reason": "",
        "metrics": _sample_metrics(),
        "seed": 42,
        "n_frames": 100,
        "config": mismatched,
    }
    (configs_dir / f"{config['config_key']}.json").write_text(json.dumps(checkpoint))

    row = m._reconstitute_row(config, configs_dir, default_seed=42)

    assert row["status"] == "failed"
    assert "does not match" in row["status_reason"]
    for col in m._METRIC_COLUMNS:
        assert row[col] is None


def test_reconstitute_row_accepts_matching_config(tmp_path):
    config = m.build_axis_configurations()[0]
    configs_dir = tmp_path / "e6_configs"
    configs_dir.mkdir()
    identity = json.loads(json.dumps(m._resolve_config_identity(config)))
    checkpoint = {
        "status": "ok",
        "status_reason": "",
        "metrics": _sample_metrics(),
        "seed": 42,
        "n_frames": 100,
        "config": identity,
    }
    (configs_dir / f"{config['config_key']}.json").write_text(json.dumps(checkpoint))

    row = m._reconstitute_row(config, configs_dir, default_seed=42)

    assert row["status"] == "ok"
    assert row["reprojection_rms_px"] is not None


def test_reconstitute_row_missing_config_is_backward_compatible(tmp_path):
    """A pre-D-31 checkpoint with no `config` key is trusted, not flagged -- the
    twelve committed checkpoints are only regenerated in wave 4."""
    config = m.build_axis_configurations()[0]
    configs_dir = tmp_path / "e6_configs"
    configs_dir.mkdir()
    checkpoint = {
        "status": "ok",
        "status_reason": "",
        "metrics": _sample_metrics(),
        "seed": 42,
        "n_frames": 100,
    }
    (configs_dir / f"{config['config_key']}.json").write_text(json.dumps(checkpoint))

    row = m._reconstitute_row(config, configs_dir, default_seed=42)

    assert row["status"] == "ok"


def test_reconstitute_row_missing_checkpoint_is_failed():
    config = m.build_axis_configurations()[0]
    with pytest.MonkeyPatch.context():
        row = m._reconstitute_row(config, Path("does-not-exist"), default_seed=42)
    assert row["status"] == "failed"
    assert "no checkpoint JSON found" in row["status_reason"]


# ---------------------------------------------------------------------------
# Plan 19.2-27 Task 5: diagnostics_out is numerically inert
# ---------------------------------------------------------------------------


def test_diagnostics_out_sink_is_numerically_inert():
    """Passing `diagnostics_out` (E6's new sink, WR-02) through
    `calibrate_synthetic` does not perturb any returned value -- matches
    E6's own call shape (`normal_fixed=GRID_NORMAL_FIXED`). Uses the
    package's cheap 'minimal' preset so this stays in the fast suite; a
    passivity proof, not a convergence study (plan 26's pattern)."""
    scenario = create_scenario("minimal", seed=1)
    kwargs = dict(
        n_water=1.0,
        refine_intrinsics=False,
        seed=1,
        normal_fixed=m.GRID_NORMAL_FIXED,
    )

    omitted, _ = calibrate_synthetic(scenario, **kwargs)

    diag_stage3 = SolverDiagnostics()
    diag_intrinsic_pass = SolverDiagnostics()
    instrumented, _ = calibrate_synthetic(
        scenario,
        **kwargs,
        diagnostics_out={
            "stage3_interface_optimization": diag_stage3,
            "stage3_intrinsic_pass": diag_intrinsic_pass,
        },
    )

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

    # The instrumented run must have actually populated the sink, or the
    # inertness proof above is vacuous -- it would also pass if
    # diagnostics_out were silently ignored. refine_intrinsics=False means
    # the intrinsic pass never runs, so only the interface-optimization
    # sink is expected to be populated.
    assert diag_stage3.nfev is not None


# ---------------------------------------------------------------------------
# D-19.3-11 / plan 19.3-07: guard-count gate on per-configuration status
# (production paths only; smoke carve-out)
# ---------------------------------------------------------------------------


class _StubScenario:
    """Minimal scenario stand-in -- run_configuration reads these attributes
    off it before passing them on to calibrate_synthetic/generate_synthetic_
    detections/evaluate_calibration (all monkeypatched below, so none of
    these values are ever dereferenced beyond attribute access)."""

    board_config = None
    water_zs: dict = {}
    n_water = 1.333
    intrinsics: dict = {}
    extrinsics: dict = {}
    noise_std = 0.5
    n_air = 0
    board_poses: list = []


def _patch_run_configuration_internals(monkeypatch, *, degenerate_count: int):
    """Stub every solve/build step run_configuration calls except the
    status-decision logic itself, so these tests exercise the real gate
    without running an actual calibration solve."""

    def _fake_build_grid_scenario(**kwargs):
        return _StubScenario()

    def _fake_calibrate_synthetic(scenario, **kwargs):
        sink = kwargs.get("discard_stats_out")
        if sink is not None:
            sink["degenerate_observations_at_solution"] = degenerate_count
        return object(), object()

    monkeypatch.setattr(m, "build_grid_scenario", _fake_build_grid_scenario)
    monkeypatch.setattr(m, "calibrate_synthetic", _fake_calibrate_synthetic)
    monkeypatch.setattr(m, "BoardGeometry", lambda config: object())
    monkeypatch.setattr(m, "generate_synthetic_detections", lambda **kwargs: object())
    monkeypatch.setattr(
        m, "evaluate_calibration", lambda result, detections, board: object()
    )
    monkeypatch.setattr(
        m, "compute_configuration_metrics", lambda *a, **k: _sample_metrics()
    )


def test_degenerate_count_gates_production_status(tmp_path, monkeypatch):
    """A non-zero degenerate_observations_at_solution count on a PRODUCTION
    (is_smoke=False, the default) run sets status="degenerate", never "ok",
    with a non-empty status_reason and populated metrics (D-19.3-11)."""
    configs = m.build_axis_configurations()
    config = configs[0]
    _patch_run_configuration_internals(monkeypatch, degenerate_count=3)

    outcome = m.run_configuration(config, seed=42, n_frames=10, out_dir=tmp_path)

    assert outcome["status"] == "degenerate"
    assert outcome["status_reason"] != ""
    assert outcome["metrics"] is not None
    assert outcome["degenerate_observations_at_solution"] == 3

    row = m.build_row(
        config,
        seed=42,
        n_frames=10,
        metrics=outcome["metrics"],
        status=outcome["status"],
        status_reason=outcome["status_reason"],
        degenerate_count=outcome["degenerate_observations_at_solution"],
    )
    assert row["status"] == "degenerate"
    assert row["degenerate_observations_at_solution"] == 3
    for col in m._METRIC_COLUMNS:
        assert row[col] is not None


def test_degenerate_count_not_gated_on_smoke(tmp_path, monkeypatch):
    """The SAME non-zero count on a --smoke (is_smoke=True) run is still
    recorded, but does NOT set status="degenerate" -- the smoke carve-out
    (D-19.3-11, plan 19.3-07). `ideal`/`minimal`-style smoke-only geometry
    legitimately trips the guard; --smoke must not report a false failure."""
    configs = m.build_axis_configurations()
    config = configs[0]
    _patch_run_configuration_internals(monkeypatch, degenerate_count=3)

    outcome = m.run_configuration(
        config, seed=42, n_frames=10, out_dir=tmp_path, is_smoke=True
    )

    assert outcome["status"] == "ok"
    assert outcome["status_reason"] == ""
    assert outcome["degenerate_observations_at_solution"] == 3


def test_degenerate_column_not_gated_when_zero(tmp_path, monkeypatch):
    """A zero degenerate count (the common case) still records status="ok"
    and degenerate_observations_at_solution == 0 -- present-and-zero, not
    absent, matching plan 19.3-02's own convention for this same key."""
    configs = m.build_axis_configurations()
    config = configs[0]
    _patch_run_configuration_internals(monkeypatch, degenerate_count=0)

    outcome = m.run_configuration(config, seed=42, n_frames=10, out_dir=tmp_path)

    assert outcome["status"] == "ok"
    assert outcome["degenerate_observations_at_solution"] == 0


def test_degenerate_gate_source_is_a_smoke_condition_not_a_threshold():
    """The carve-out is threaded through an explicit is_smoke condition, not
    a numeric threshold: no integer literal is ever compared against the
    guard count except `> 0`."""
    source = Path(m.__file__).read_text(encoding="utf-8")
    assert source.count('"degenerate"') >= 2  # STATUS_VALUES membership + assignment
    guard_comparisons = re.findall(
        r"n_degenerate\s*(<=|>=|==|!=|<|>)\s*(-?\d+)", source
    )
    for operator, literal in guard_comparisons:
        assert operator == ">" and literal == "0", (
            f"found n_degenerate {operator} {literal} in "
            "e6_generalization_sweep.py -- the production gate must be "
            "exactly `> 0`, never a threshold or tolerance"
        )
    assert len(guard_comparisons) >= 2  # production branch + smoke-carve-out branch


def test_degenerate_column_appended_last():
    """`degenerate_observations_at_solution` was appended at the very end of
    E6_COLUMNS by plan 19.3-07; FIX-03 (23-03) appended TWO MORE columns
    after it, so the invariant this test checks moved: it is no longer the
    final column, but its own index (fixed once the two optimality columns
    and the base 28 landed) has not moved -- every pre-existing column,
    including this one, kept its position when the new pair was appended."""
    assert (
        m.E6_COLUMNS.index("degenerate_observations_at_solution")
        == len(m.E6_COLUMNS) - 3
    )
