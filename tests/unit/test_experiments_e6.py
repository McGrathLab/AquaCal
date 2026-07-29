"""Unit tests for `experiments/e6_generalization_sweep.py` (EXP-10).

Fast unit tests only: hand-built fixtures directly constructed, no actual
calibration solve of any kind, none marked slow. `--smoke` (which does
exercise a real, small solve) is verified separately by the plan's own
`<verify>` block, not by pytest.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pandas as pd
import pytest

import experiments.e4_benchmark_grid as e4
import experiments.e6_generalization_sweep as m

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
    """No E6_COLUMNS name implies a pass/fail verdict (D-12)."""
    pattern = re.compile(r"pass|fail|verdict|acceptable|holds|degraded")
    assert not any(pattern.search(c) for c in m.E6_COLUMNS)


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
    """D-28/D-29: SCALE_AXIS_VALUES' half_scale/default/double_scale rescale
    around E4's NEW baseline geometry (GRID_DEPTH_RANGE/GRID_SPACING) rather
    than the old, now-stale absolute numbers -- and remain a factor-of-two
    ladder, derived from E4's constants rather than hardcoded a second time."""
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

    # depth_range is expressed relative to the water surface, so scaling by
    # 0.5x/2x must keep the board strictly below GRID_HEIGHT_ABOVE_WATER
    # (never move it into air) at both ends of the ladder.
    assert half_depth_range[0] > e4.GRID_HEIGHT_ABOVE_WATER
    assert half_depth_range[1] > half_depth_range[0]
    assert double_depth_range[0] > e4.GRID_HEIGHT_ABOVE_WATER
    assert double_depth_range[1] > double_depth_range[0]

    half_below = (
        half_depth_range[0] - e4.GRID_HEIGHT_ABOVE_WATER,
        half_depth_range[1] - e4.GRID_HEIGHT_ABOVE_WATER,
    )
    double_below = (
        double_depth_range[0] - e4.GRID_HEIGHT_ABOVE_WATER,
        double_depth_range[1] - e4.GRID_HEIGHT_ABOVE_WATER,
    )
    assert double_below[0] == pytest.approx(4.0 * half_below[0])
    assert double_below[1] == pytest.approx(4.0 * half_below[1])


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


def test_e6_columns_unchanged_by_provenance_work():
    """generalization_sweep.csv's header is untouched by this plan (28 columns)."""
    assert len(m.E6_COLUMNS) == 28


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
