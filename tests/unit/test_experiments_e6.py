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


def test_status_vocabulary():
    """The row builder's status values come from {ok, failed, skipped_existing}."""
    assert m.STATUS_VALUES == {"ok", "failed", "skipped_existing"}
    configs = m.build_axis_configurations()
    config = configs[0]
    for status in sorted(m.STATUS_VALUES):
        row = m.build_row(
            config,
            seed=42,
            n_frames=10,
            metrics=_sample_metrics() if status == "ok" else None,
            status=status,
            status_reason="" if status == "ok" else "reason",
        )
        assert row["status"] in m.STATUS_VALUES
        if status != "ok":
            for col in m._METRIC_COLUMNS:
                assert row[col] is None


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

    monkeypatch.setattr(m, "compute_per_camera_errors", lambda result, scenario: {})

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
    """generalization_sweep.csv's header carries 30 columns: the original 28
    (unchanged by the provenance work, plan 19.2-23) plus the two optimality
    columns Task 1 of plan 19.2-27 adds (WR-02)."""
    assert len(m.E6_COLUMNS) == 30


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
