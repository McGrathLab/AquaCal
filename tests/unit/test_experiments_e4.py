"""Unit tests for `experiments/e4_benchmark_grid.py` (EXP-08).

Fast unit tests only: hand-built `benchmark.json` fixtures written directly
via `write_direct_call_benchmark`, no calibration solve of any kind is
invoked, and no real subprocess is spawned (`test_subprocess_status_mapping`
monkeypatches `subprocess.run`). None of these tests are marked slow --
that is `--smoke` and production-run territory (plan 19.2-09).
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import pandas as pd
import pytest

from aquacal.calibration._observability import SolverDiagnostics
from experiments._io import write_direct_call_benchmark
from experiments.e4_benchmark_grid import (
    _NULL_METRICS,
    DECLARED_CELLS,
    E2_BENCHMARK_PATH,
    GRID_BOARD_CONFIG,
    GRID_COLUMNS,
    GRID_SCENARIO_NAME,
    SKIPPED_EXIT_CODE,
    build_grid_dataframe,
    build_grid_scenario,
    run_cell_subprocess,
    write_grid_latex,
)
from experiments.e4_benchmark_grid import subprocess as e4_subprocess


def _write_fake_cell(
    cell_dir: Path, n_cameras: int, n_frames: int, seed: int = 42
) -> None:
    """Write a realistic-shaped per-cell benchmark.json fixture, no calibration run."""
    diag1 = SolverDiagnostics(
        nfev=10,
        njev=8,
        cost=1.0,
        optimality=0.01,
        status=2,
        message="`ftol` termination condition is satisfied.",
        ftol=1e-8,
        xtol=1e-8,
        gtol=1e-8,
        max_nfev_effective=100,
        max_nfev_source="scipy_auto",
        n_params=50,
        n_groups=5,
        n_residuals=200,
    )
    diag2 = SolverDiagnostics(
        nfev=5,
        njev=4,
        cost=0.5,
        optimality=0.02,
        status=3,
        message="`xtol` termination condition is satisfied.",
        ftol=1e-8,
        xtol=1e-8,
        gtol=1e-8,
        max_nfev_effective=80,
        max_nfev_source="scipy_auto",
        n_params=55,
        n_groups=6,
        n_residuals=200,
    )
    write_direct_call_benchmark(
        cell_dir / "benchmark.json",
        problem_shape={
            "n_cameras": n_cameras,
            "n_frames": n_frames,
            "n_observations": n_cameras * n_frames,
            "n_cameras_observing_per_frame_min": max(n_cameras - 1, 0),
            "n_cameras_observing_per_frame_median": float(n_cameras),
            "peak_bytes_baseline": 900,
        },
        timings={
            "stage3_interface_optimization": 1.0,
            "stage3_intrinsic_pass": 0.5,
        },
        diagnostics={
            "stage3_interface_optimization": diag1,
            "stage3_intrinsic_pass": diag2,
        },
        solver_config={
            "normal_fixed": False,
            "shared_interface": True,
            "refine_intrinsics": True,
            "n_air": 1.0,
            "n_water": 1.333,
        },
        accuracy={
            "reprojection_rms": 0.5,
            "validation_3d_error_mean": 0.001,
            "validation_3d_error_std": 0.002,
        },
        memory_readings={
            "_baseline": {"peak_bytes": 900, "mode": "psutil_peak_wset"},
            "stage3_interface_optimization": {
                "peak_bytes": 1000,
                "mode": "psutil_peak_wset",
            },
            "stage3_intrinsic_pass": {"peak_bytes": 1100, "mode": "psutil_peak_wset"},
        },
        seed=seed,
        force=True,
    )


def _write_fake_e2_record(path: Path) -> None:
    """Write a minimal but schema-shaped E2 benchmark.json fixture."""
    record = {
        "schema_version": 1,
        "problem_shape": {
            "n_cameras": 13,
            "n_frames_calibration": 200,
            "n_frames_holdout": 52,
        },
        "solver_config": {
            "interface_normal_fixed": False,
            "refine_intrinsics": True,
            "robust_loss": "huber",
            "loss_scale": 1.0,
            "seed": 42,
        },
        "accuracy": {
            "reprojection_rms": 1.0,
            "validation_3d_error_mean": 0.0002,
            "validation_3d_error_std": 0.0006,
        },
        "environment": {},
        "memory": {"mode": "psutil_peak_wset", "whole_run_peak_bytes": 123456},
        "stages": {
            "stage3_interface_optimization": {
                "n_params": 1269,
                "n_groups": 13,
                "n_residuals": 147950,
                "fd_reduction": 97.6,
                "nfev": 38,
                "njev": 28,
                "optimality": 0.1,
                "seconds": 1276.9,
                "memory": {
                    "cumulative_peak_bytes_as_of_stage_end": 9621364736,
                    "delta_bytes_since_previous_boundary": 9167876096,
                    "mode": "psutil_peak_wset",
                },
            },
            "stage3_intrinsic_pass": {
                "n_params": 1317,
                "n_groups": 17,
                "n_residuals": 147950,
                "fd_reduction": 77.5,
                "nfev": 26,
                "njev": 12,
                "optimality": 20813.6,
                "seconds": 632.9,
                "memory": {
                    "cumulative_peak_bytes_as_of_stage_end": 10499325952,
                    "delta_bytes_since_previous_boundary": 877961216,
                    "mode": "psutil_peak_wset",
                },
            },
        },
    }
    path.write_text(json.dumps(record))


@pytest.fixture
def full_grid_dir(tmp_path):
    """A tmp_path with all nine declared cells' benchmark.json + an E2 fixture."""
    cells_dir = tmp_path / "e4_cells"
    for n_cameras, n_frames in DECLARED_CELLS:
        cell_dir = cells_dir / f"cameras_{n_cameras}_frames_{n_frames}"
        _write_fake_cell(cell_dir, n_cameras, n_frames)

    e2_path = tmp_path / "e2_benchmark.json"
    _write_fake_e2_record(e2_path)

    cell_statuses = [
        {
            "n_cameras": n,
            "n_frames": f,
            "status": "ok",
            "status_reason": "",
            "exit_code": 0,
        }
        for n, f in DECLARED_CELLS
    ]
    return tmp_path, cell_statuses, e2_path


def test_grid_row_schema(full_grid_dir):
    out_dir, cell_statuses, e2_path = full_grid_dir
    df = build_grid_dataframe(out_dir, cell_statuses, e2_path)
    assert list(df.columns) == GRID_COLUMNS


def test_declared_cells_all_emit_rows(full_grid_dir):
    out_dir, cell_statuses, e2_path = full_grid_dir
    missing_cell = DECLARED_CELLS[0]
    missing_dir = (
        out_dir / "e4_cells" / f"cameras_{missing_cell[0]}_frames_{missing_cell[1]}"
    )
    shutil.rmtree(missing_dir)

    statuses = []
    for n, f in DECLARED_CELLS:
        if (n, f) == missing_cell:
            statuses.append(
                {
                    "n_cameras": n,
                    "n_frames": f,
                    "status": "failed",
                    "status_reason": "boom",
                    "exit_code": 1,
                }
            )
        else:
            statuses.append(
                {
                    "n_cameras": n,
                    "n_frames": f,
                    "status": "ok",
                    "status_reason": "",
                    "exit_code": 0,
                }
            )

    df = build_grid_dataframe(out_dir, statuses, e2_path)
    assert len(df) == 10

    failed_key = f"cameras_{missing_cell[0]}_frames_{missing_cell[1]}"
    failed_row = df[df["cell_key"] == failed_key].iloc[0]
    assert failed_row["status"] == "failed"
    assert failed_row["status_reason"] == "boom"
    assert pd.isna(failed_row["reprojection_rms"])
    assert pd.isna(failed_row["n_params_stage3_interface_optimization"])


def test_status_vocabulary(full_grid_dir):
    out_dir, cell_statuses, e2_path = full_grid_dir
    df = build_grid_dataframe(out_dir, cell_statuses, e2_path)
    assert set(df["status"]) <= {"ok", "failed", "skipped_existing"}


def test_timing_scope_and_record_source(full_grid_dir):
    out_dir, cell_statuses, e2_path = full_grid_dir
    df = build_grid_dataframe(out_dir, cell_statuses, e2_path)

    assembled = df[df["record_source"] == "assembled"]
    pipeline = df[df["record_source"] == "pipeline"]

    assert len(assembled) == 9
    assert (assembled["timing_scope"] == "optimization_only").all()

    assert len(pipeline) == 1
    assert (pipeline["timing_scope"] == "end_to_end").all()


def test_jacobian_elements_is_product(full_grid_dir):
    out_dir, cell_statuses, e2_path = full_grid_dir
    df = build_grid_dataframe(out_dir, cell_statuses, e2_path)

    ok_rows = df[df["status"] == "ok"]
    assert len(ok_rows) > 0
    for _, row in ok_rows.iterrows():
        n_res = row["n_residuals_stage3_interface_optimization"]
        n_params = row["n_params_stage3_interface_optimization"]
        expected = None if pd.isna(n_res) or pd.isna(n_params) else n_res * n_params
        actual = row["jacobian_elements_stage3_interface_optimization"]
        if expected is None:
            assert pd.isna(actual)
        else:
            assert actual == expected


def test_build_grid_scenario_shape():
    scenario = build_grid_scenario(3, 4, seed=42)
    assert len(scenario.intrinsics) == 3
    assert len(scenario.board_poses) == 4
    assert scenario.noise_std == 0.5
    assert scenario.board_config == GRID_BOARD_CONFIG
    assert scenario.name == GRID_SCENARIO_NAME

    with pytest.raises(ValueError):
        build_grid_scenario(3, 4, seed=42, name="calibration")


def test_grid_solver_config_is_self_describing(full_grid_dir):
    out_dir, cell_statuses, e2_path = full_grid_dir
    df = build_grid_dataframe(out_dir, cell_statuses, e2_path)

    ok_synthetic = df[(df["record_source"] == "assembled") & (df["status"] == "ok")]
    assert len(ok_synthetic) == 9
    assert not ok_synthetic["normal_fixed"].any()
    assert ok_synthetic["shared_interface"].all()
    assert ok_synthetic["seed"].notna().all()


def test_e2_benchmark_path_is_absolute():
    """CR-03: E2_BENCHMARK_PATH must be anchored to __file__, never cwd-relative
    (module-level constant already resolved at import time)."""
    assert E2_BENCHMARK_PATH.is_absolute()


def test_skipped_existing_cell_with_on_disk_record_keeps_its_metrics(full_grid_dir):
    """CR-01: a `skipped_existing` cell whose record IS on disk must keep the
    metric columns `aggregate()` just read successfully -- the resume path
    (D-24) exists precisely so a resumed run publishes what it already
    computed. This FAILS on EXPECTED_BASE, where the nulling rule fires on
    any non-"ok" status regardless of whether a record was actually read."""
    out_dir, cell_statuses, e2_path = full_grid_dir
    resumed_cell = DECLARED_CELLS[0]

    statuses = []
    for n, f in DECLARED_CELLS:
        if (n, f) == resumed_cell:
            statuses.append(
                {
                    "n_cameras": n,
                    "n_frames": f,
                    "status": "skipped_existing",
                    "status_reason": "",
                    "exit_code": SKIPPED_EXIT_CODE,
                }
            )
        else:
            statuses.append(
                {
                    "n_cameras": n,
                    "n_frames": f,
                    "status": "ok",
                    "status_reason": "",
                    "exit_code": 0,
                }
            )

    df = build_grid_dataframe(out_dir, statuses, e2_path)

    resumed_key = f"cameras_{resumed_cell[0]}_frames_{resumed_cell[1]}"
    resumed_row = df[df["cell_key"] == resumed_key].iloc[0]
    assert resumed_row["status"] == "skipped_existing"
    assert not pd.isna(resumed_row["reprojection_rms"])
    assert resumed_row["reprojection_rms"] == 0.5
    assert not pd.isna(resumed_row["n_params_stage3_interface_optimization"])
    assert resumed_row["n_params_stage3_interface_optimization"] == 50


def test_failed_cell_nulls_metrics_even_with_a_stale_on_disk_record(full_grid_dir):
    """A "failed" cell must null every metric column and preserve
    status_reason/exit_code, even when a (stale) benchmark.json happens to
    exist on disk for it -- unlike "skipped_existing", "failed" is never a
    legitimate resume outcome."""
    out_dir, cell_statuses, e2_path = full_grid_dir
    failed_cell = DECLARED_CELLS[1]

    statuses = []
    for n, f in DECLARED_CELLS:
        if (n, f) == failed_cell:
            statuses.append(
                {
                    "n_cameras": n,
                    "n_frames": f,
                    "status": "failed",
                    "status_reason": "OOM during Stage 3",
                    "exit_code": 137,
                }
            )
        else:
            statuses.append(
                {
                    "n_cameras": n,
                    "n_frames": f,
                    "status": "ok",
                    "status_reason": "",
                    "exit_code": 0,
                }
            )

    df = build_grid_dataframe(out_dir, statuses, e2_path)

    failed_key = f"cameras_{failed_cell[0]}_frames_{failed_cell[1]}"
    failed_row = df[df["cell_key"] == failed_key].iloc[0]
    assert failed_row["status"] == "failed"
    assert failed_row["status_reason"] == "OOM during Stage 3"
    assert failed_row["exit_code"] == 137
    for metric_col in _NULL_METRICS:
        if metric_col in ("timing_scope", "record_source"):
            continue
        assert pd.isna(failed_row[metric_col])


def test_missing_e2_benchmark_degrades_to_null_row_no_exception(full_grid_dir):
    """CR-03: a missing E2 benchmark.json must not raise after all nine
    cells have solved -- it costs a null real-rig row with a named
    record_source, not the entire run's CSV/LaTeX."""
    out_dir, cell_statuses, _ = full_grid_dir
    missing_e2_path = out_dir / "does_not_exist" / "benchmark.json"

    df = build_grid_dataframe(out_dir, cell_statuses, missing_e2_path)

    assert len(df) == 10
    real_rig_row = df.iloc[-1]
    assert real_rig_row["record_source"] == "missing_e2_benchmark"
    assert pd.isna(real_rig_row["reprojection_rms"])
    assert pd.isna(real_rig_row["n_params_stage3_interface_optimization"])
    # The nine synthetic cells are unaffected by the missing real-rig record.
    assert len(df[df["record_source"] == "assembled"]) == 9


def test_unreadable_e2_benchmark_degrades_to_null_row_no_exception(
    full_grid_dir, tmp_path
):
    """CR-03: an unparseable E2 benchmark.json (corrupt JSON) must degrade
    the same way a missing file does, not raise `json.JSONDecodeError`."""
    out_dir, cell_statuses, _ = full_grid_dir
    corrupt_e2_path = tmp_path / "corrupt_benchmark.json"
    corrupt_e2_path.write_text("{not valid json")

    df = build_grid_dataframe(out_dir, cell_statuses, corrupt_e2_path)

    assert len(df) == 10
    real_rig_row = df.iloc[-1]
    assert real_rig_row["record_source"] == "missing_e2_benchmark"
    assert pd.isna(real_rig_row["reprojection_rms"])


def test_aggregate_refusal_degrades_instead_of_losing_the_whole_run(
    full_grid_dir,
):
    """CR-03: if aggregate() refuses a record it does not recognize (e.g. a
    schema_version mismatch on one cell), build_grid_dataframe must not lose
    benchmark_grid.csv/.tex for every OTHER cell that already solved."""
    out_dir, cell_statuses, e2_path = full_grid_dir
    bad_cell = DECLARED_CELLS[2]
    bad_cell_path = (
        out_dir
        / "e4_cells"
        / f"cameras_{bad_cell[0]}_frames_{bad_cell[1]}"
        / "benchmark.json"
    )
    record = json.loads(bad_cell_path.read_text())
    record["schema_version"] = 999
    bad_cell_path.write_text(json.dumps(record))

    df = build_grid_dataframe(out_dir, cell_statuses, e2_path)

    assert len(df) == 10


class _FakeCompletedProcess:
    def __init__(self, returncode: int, stderr: str = "") -> None:
        self.returncode = returncode
        self.stdout = ""
        self.stderr = stderr


def test_subprocess_status_mapping(monkeypatch, tmp_path):
    codes = [0, SKIPPED_EXIT_CODE, 1, -9]
    calls: list[list[str]] = []

    def fake_run(cmd, **kwargs):
        calls.append(cmd)
        code = codes.pop(0)
        stderr = "boom" if code not in (0, SKIPPED_EXIT_CODE) else ""
        return _FakeCompletedProcess(code, stderr=stderr)

    monkeypatch.setattr(e4_subprocess, "run", fake_run)

    n_cameras, n_frames = DECLARED_CELLS[0]

    row_ok = run_cell_subprocess(n_cameras, n_frames, 42, tmp_path, False)
    row_skip = run_cell_subprocess(n_cameras, n_frames, 42, tmp_path, False)
    row_fail = run_cell_subprocess(n_cameras, n_frames, 42, tmp_path, False)
    row_signal = run_cell_subprocess(n_cameras, n_frames, 42, tmp_path, False)

    assert row_ok["status"] == "ok" and row_ok["exit_code"] == 0
    assert row_skip["status"] == "skipped_existing"
    assert row_skip["exit_code"] == SKIPPED_EXIT_CODE

    assert row_fail["status"] == "failed"
    assert row_fail["exit_code"] == 1
    assert row_fail["status_reason"]

    assert row_signal["status"] == "failed"
    assert row_signal["exit_code"] == -9
    assert row_signal["status_reason"]

    assert len(calls) == 4
    assert calls[0] == calls[0]  # command was captured, no real subprocess spawned


def test_latex_fragment_separates_real_rig(full_grid_dir, tmp_path):
    out_dir, cell_statuses, e2_path = full_grid_dir
    df = build_grid_dataframe(out_dir, cell_statuses, e2_path)

    tex_path = tmp_path / "benchmark_grid.tex"
    write_grid_latex(df, tex_path)
    text = tex_path.read_text()

    # write_latex_fragment LaTeX-escapes "_" as "\_" (_latex_escape), so the
    # cell key survives in the rendered fragment as "real\_rig\_..." rather
    # than the literal Python string.
    real_rig_key_rendered = "real\\_rig\\_13cam\\_200fr"
    assert real_rig_key_rendered in text
    assert "real-rig anchor row" in text.lower() or "real rig" in text.lower()

    real_rig_marker = text.index("real-rig anchor row")
    real_rig_cell_idx = text.index(real_rig_key_rendered)
    assert real_rig_cell_idx > real_rig_marker

    # The real-rig row's key must not appear before its own labeled block --
    # i.e. it is not folded into the earlier nine-cell blocks.
    assert real_rig_key_rendered not in text[:real_rig_marker]
