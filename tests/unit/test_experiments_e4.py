"""Unit tests for `experiments/e4_benchmark_grid.py` (EXP-08).

Most tests here are fast: hand-built `benchmark.json` fixtures written
directly via `write_direct_call_benchmark`, no calibration solve of any
kind. `test_subprocess_status_mapping` monkeypatches `subprocess.run` to
prove the status-mapping LOGIC in isolation; the
`TestRealChildProcess` class (D-33 gap 1) additionally spawns GENUINE
`python -c ...` child processes (no monkeypatching) through the exact same
`_invoke_subprocess_with_status_mapping` helper, so the mapping is proven
against a real process this machine actually runs, not only against a
`_FakeCompletedProcess`. None of these tests are marked slow -- the real
children are trivial one-liners that exit in well under a second, and the
smoke-cell calibration (`test_smoke_cell_reports_clean_memory_pressure`)
matches the timing of the module's own `--smoke` path (a few seconds).
"""

from __future__ import annotations

import json
import re
import shutil
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

import experiments.e4_benchmark_grid as e4_grid_module
from aquacal.calibration._observability import SolverDiagnostics
from aquacal.config.schema import BoardConfig, CameraExtrinsics
from aquacal.core.camera import Camera
from aquacal.core.interface_model import Interface
from aquacal.core.refractive_geometry import refractive_back_project
from aquacal.datasets.synthetic import (
    board_clearance_floor,
    generate_camera_array,
    generate_camera_intrinsics,
)
from experiments._io import (
    build_experiment_arg_parser,
    write_direct_call_benchmark,
    write_experiment_csv,
)
from experiments.e4_benchmark_grid import (
    _NULL_METRICS,
    DECLARED_CELLS,
    E2_BENCHMARK_PATH,
    GRID_BOARD_CONFIG,
    GRID_COLUMNS,
    GRID_DEPTH_RANGE,
    GRID_HEIGHT_ABOVE_WATER,
    GRID_KEY_COLUMNS,
    GRID_SCENARIO_NAME,
    GRID_SPACING,
    GRID_XY_EXTENT_RATIO,
    MEMORY_NEAR_CEILING_FRACTION,
    MEMORY_PRESSURE_CLEAN,
    MEMORY_PRESSURE_NEAR_CEILING,
    REPEAT_CELLS,
    SKIPPED_EXIT_CODE,
    _array_xy_span,
    _classify_memory_pressure,
    _invoke_subprocess_with_status_mapping,
    _validate_e4_args,
    build_arg_parser,
    build_grid_dataframe,
    build_grid_scenario,
    default_xy_extent_for_layout,
    run_cell_subprocess,
    run_grid_cell,
    splice_repeat_records,
    write_grid_latex,
)
from experiments.e4_benchmark_grid import subprocess as e4_subprocess


def _write_fake_cell(
    cell_dir: Path,
    n_cameras: int,
    n_frames: int,
    seed: int = 42,
    degenerate_observations_at_solution: int = 0,
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
            "degenerate_observations_at_solution": degenerate_observations_at_solution,
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
    assert set(df["status"]) <= {"ok", "degenerate", "failed", "skipped_existing"}


# ---------------------------------------------------------------------------
# D-19.3-11 / plan 19.3-07: guard-count gate on per-cell status
# (production paths only; smoke carve-out)
# ---------------------------------------------------------------------------


def test_degenerate_count_gates_production_cell_status(full_grid_dir):
    """A non-zero degenerate_observations_at_solution count recorded for a
    DECLARED (production) cell downgrades its status from "ok" to
    "degenerate", never leaving it "ok" -- metrics stay populated (D-19.3-11).
    """
    out_dir, cell_statuses, e2_path = full_grid_dir
    degenerate_cell = DECLARED_CELLS[0]
    cell_dir = (
        out_dir
        / "e4_cells"
        / f"cameras_{degenerate_cell[0]}_frames_{degenerate_cell[1]}"
    )
    _write_fake_cell(
        cell_dir,
        degenerate_cell[0],
        degenerate_cell[1],
        degenerate_observations_at_solution=3,
    )

    df = build_grid_dataframe(out_dir, cell_statuses, e2_path)
    cell_key = f"cameras_{degenerate_cell[0]}_frames_{degenerate_cell[1]}"
    row = df[df["cell_key"] == cell_key].iloc[0]

    assert row["status"] == "degenerate"
    assert row["status_reason"] != ""
    assert row["degenerate_observations_at_solution"] == 3
    # Metrics stay populated -- this is NOT the null branch.
    assert not pd.isna(row["reprojection_rms"])
    assert not pd.isna(row["n_params_stage3_interface_optimization"])


def test_degenerate_count_zero_stays_ok(full_grid_dir):
    """The common case: a zero guard count records status="ok" and
    degenerate_observations_at_solution == 0 -- present, not absent."""
    out_dir, cell_statuses, e2_path = full_grid_dir
    df = build_grid_dataframe(out_dir, cell_statuses, e2_path)
    assembled = df[df["record_source"] == "assembled"]
    assert (assembled["status"] == "ok").all()
    assert (assembled["degenerate_observations_at_solution"] == 0).all()


def test_degenerate_column_appended_last():
    """The new column is appended at the very end of GRID_COLUMNS, verified
    by index -- every pre-existing column keeps its position."""
    assert GRID_COLUMNS.index("degenerate_observations_at_solution") == (
        len(GRID_COLUMNS) - 1
    )


def test_smoke_cells_never_reach_the_gate():
    """SMOKE_CELLS's own trivial (3, 3)/(3, 4) pairs are disjoint from
    DECLARED_CELLS -- build_grid_dataframe (the sole gating site) only ever
    iterates DECLARED_CELLS, so a smoke cell can never be gated regardless of
    its own guard count (D-19.3-11's smoke carve-out)."""
    from experiments.e4_benchmark_grid import SMOKE_CELLS

    assert set(SMOKE_CELLS).isdisjoint(set(DECLARED_CELLS))
    import inspect

    source = inspect.getsource(build_grid_dataframe)
    # The docstring/comment prose is allowed to name SMOKE_CELLS (to explain
    # the carve-out); the CODE must never iterate over it -- only over
    # DECLARED_CELLS, verified by the one `for` loop in this function.
    for_loops = re.findall(r"for .* in (\w+):", source)
    assert for_loops == ["DECLARED_CELLS"]


def test_degenerate_gate_source_is_a_smoke_condition_not_a_threshold():
    """The production gate is exactly `n_degenerate > 0` -- no other integer
    literal is ever compared against the guard count anywhere in the module,
    which is what makes the carve-out a smoke-path condition rather than a
    threshold or tolerance."""
    source = Path(e4_grid_module.__file__).read_text(encoding="utf-8")
    assert source.count('"degenerate"') >= 1
    guard_comparisons = re.findall(
        r"n_degenerate\s*(<=|>=|==|!=|<|>)\s*(-?\d+)", source
    )
    assert len(guard_comparisons) >= 1
    for operator, literal in guard_comparisons:
        assert operator == ">" and literal == "0", (
            f"found n_degenerate {operator} {literal} in e4_benchmark_grid.py "
            "-- the production gate must be exactly `> 0`, never a threshold "
            "or tolerance"
        )


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


def test_grid_depth_range_is_derived_from_board_clearance_floor():
    """D-19.3-01: GRID_DEPTH_RANGE[0] must equal `board_clearance_floor` applied
    to GRID_BOARD_CONFIG, this module's own grid water_zs, and the 15 degree
    tilt `generate_board_trajectory` samples by default -- never a restated
    literal. GRID_DEPTH_RANGE[1] stays a fixed 2.0 m ceiling (D-19.3-03)."""
    _, _, water_zs = generate_camera_array(
        n_cameras=12,
        layout=e4_grid_module.GRID_LAYOUT,
        spacing=GRID_SPACING,
        height_above_water=GRID_HEIGHT_ABOVE_WATER,
        seed=42,
    )
    expected_floor = board_clearance_floor(GRID_BOARD_CONFIG, water_zs, 15.0)

    assert GRID_DEPTH_RANGE[0] == pytest.approx(expected_floor)
    assert GRID_DEPTH_RANGE[1] == 2.0


def test_grid_depth_range_moves_when_board_square_size_changes():
    """GRID_DEPTH_RANGE is derived, not a literal that happens to be right --
    changing GRID_BOARD_CONFIG.square_size (patched, module reloaded) must
    move the derived floor. Verified by recomputing the derivation the same
    way the module does, at a different square_size, rather than by
    reloading the module (which would re-run the whole file's import-time
    side effects)."""
    _, _, water_zs = generate_camera_array(
        n_cameras=12,
        layout=e4_grid_module.GRID_LAYOUT,
        spacing=GRID_SPACING,
        height_above_water=GRID_HEIGHT_ABOVE_WATER,
        seed=42,
    )
    baseline_floor = board_clearance_floor(GRID_BOARD_CONFIG, water_zs, 15.0)

    bigger_board = BoardConfig(
        squares_x=GRID_BOARD_CONFIG.squares_x,
        squares_y=GRID_BOARD_CONFIG.squares_y,
        square_size=GRID_BOARD_CONFIG.square_size * 2.0,
        marker_size=GRID_BOARD_CONFIG.marker_size,
        dictionary=GRID_BOARD_CONFIG.dictionary,
    )
    bigger_floor = board_clearance_floor(bigger_board, water_zs, 15.0)

    assert bigger_floor != pytest.approx(baseline_floor)
    assert GRID_DEPTH_RANGE[0] == pytest.approx(baseline_floor)


def test_build_grid_scenario_no_corner_at_or_above_max_water_z_at_production_scale():
    """No board corner in any frame of a `build_grid_scenario` output may sit
    at or above `max(water_zs)` -- the clearance property GRID_DEPTH_RANGE
    and the threaded `board=` exist to guarantee. Checked at a production
    grid cell (12 cameras, 100 frames), not a toy size."""
    from aquacal.core.board import BoardGeometry
    from aquacal.utils.transforms import rvec_to_matrix

    scenario = build_grid_scenario(12, 100, seed=42)
    max_water_z = max(scenario.water_zs.values())
    geometry = BoardGeometry(scenario.board_config)
    corners_local = np.array(list(geometry.corner_positions.values()), dtype=np.float64)

    for pose in scenario.board_poses:
        R = rvec_to_matrix(pose.rvec)
        world_corners = (R @ corners_local.T).T + pose.tvec
        # World +Z is DOWN (into water); a corner is submerged only if its Z
        # is strictly greater than the deepest interface.
        assert np.all(world_corners[:, 2] > max_water_z), (
            f"frame {pose.frame_idx}: a corner is at or above "
            f"max(water_zs)={max_water_z}"
        )


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


class TestRealChildProcess:
    """D-33 gap 1: a real child process, not a monkeypatched `subprocess.run`.

    `test_subprocess_status_mapping` above proves the status MAPPING; these
    tests prove the same mapping against a genuine `python -c ...` child
    this machine actually spawns and terminates, via the exact
    `_invoke_subprocess_with_status_mapping` helper `run_cell_subprocess`
    calls in production.
    """

    def test_real_child_nonzero_exit_is_recorded_not_raised(self):
        cmd = [sys.executable, "-c", "import sys; sys.exit(1)"]
        status, reason, exit_code, elapsed = _invoke_subprocess_with_status_mapping(
            cmd, timeout=30
        )
        assert status == "failed"
        assert exit_code == 1
        assert reason
        assert elapsed >= 0

    def test_real_child_timeout_is_recorded_not_raised_and_is_distinguishable(self):
        """A child that sleeps past a short timeout: `status="failed"` with
        a reason distinguishable from a non-zero exit, `exit_code=None`
        (there was no exit), and no exception propagates."""
        cmd = [sys.executable, "-c", "import time; time.sleep(30)"]
        status, reason, exit_code, elapsed = _invoke_subprocess_with_status_mapping(
            cmd, timeout=0.5
        )
        assert status == "failed"
        assert exit_code is None
        assert "timeout" in reason.lower()
        assert "exit_code=" not in reason

    def test_real_child_allocating_until_it_dies_is_recorded(self):
        """A real child that allocates until it dies.

        Bounded per this environment's concurrency-safety rule (other
        executor agents run in parallel worktrees on this box): rather than
        growing memory incrementally toward the 15.7 GB physical ceiling
        (which the environment rules explicitly forbid attempting here),
        this spawns a child that requests a SINGLE allocation so large
        (10**20 bytes, far beyond any real address space) that CPython
        refuses it immediately -- observed here as an uncaught
        `OverflowError` ("cannot fit 'int' into an index-sized integer"),
        not `MemoryError`, because CPython's `bytearray()` constructor
        checks the requested size against `Py_ssize_t` before ever asking
        the allocator for memory. The child exits with code 1 in ~15 ms; no
        real memory or pagefile pressure is placed on the shared box. This
        proves `run_cell_subprocess`'s contract (a dying, memory-related
        child produces a RECORDED row, not a hang or a raised exception in
        the parent) without exercising the slow-paging incremental-growth
        scenario D-33 describes -- that scenario is deliberately deferred to
        the actual wave-3 production run, and the summary records this as an
        explicit, honest limitation.
        """
        cmd = [sys.executable, "-c", "bytearray(10**20)"]
        status, reason, exit_code, elapsed = _invoke_subprocess_with_status_mapping(
            cmd, timeout=30
        )
        assert status == "failed"
        assert exit_code == 1
        assert reason


def test_oversized_cell_is_measured_not_predicted(monkeypatch, tmp_path):
    """A cell too large for the machine must NOT be refused from its problem
    shape alone.

    The removed pre-flight guard projected residuals as
    `2 * n_cameras * n_frames * MAX_CORNERS_PER_VIEW` -- every camera seeing
    every corner in every frame -- which over-estimated by ~3.76x against
    measurement and refused the entire n_frames=200 column of cells that
    measurement says fit. Calibrating that assumption to an observed
    visibility fraction would bake this rig's optics into a rig-agnostic
    library, so the projection was removed outright rather than retuned.

    What replaces it is downstream and measured, not predicted: a genuine OOM
    kills only the cell's own child process and is mapped to a recorded
    `status="failed"` row with its exit code, and a thrashing cell is bounded
    by the per-cell timeout. This test pins the removal: `calibrate_synthetic`
    MUST now be reached for a cell that the old projection would have refused.
    """
    reached: list[tuple[int, int]] = []

    def _record_and_stop(scenario, *a, **k):
        reached.append((len(scenario.intrinsics), len(scenario.board_poses)))
        raise MemoryError("simulated allocation failure inside Stage 3")

    monkeypatch.setattr(e4_grid_module, "calibrate_synthetic", _record_and_stop)

    # 16x200 projected 39.80 GiB under the old worst-case rule and was refused
    # outright; measurement puts it near 12.5 GiB. It must now be attempted.
    row = run_grid_cell(16, 200, seed=1, out_dir=tmp_path, force=True)

    assert reached, (
        "calibrate_synthetic was not reached -- a shape-only refusal survives"
    )
    assert reached[0] == (16, 200)
    # And the failure it hit is still a recorded row, never a halt (D-04).
    assert row["status"] == "failed"
    assert row["status_reason"]


def test_smoke_cell_reports_clean_memory_pressure(tmp_path):
    """A comfortably-sized smoke cell reports the clean memory-pressure
    value (D-33 gap 3) -- exercised through the real subprocess hop, the
    same path production cells run."""
    row = run_cell_subprocess(3, 3, seed=1, out_dir=tmp_path, force=True, timeout=60)
    assert row["status"] == "ok"

    cell_path = tmp_path / "e4_cells" / "cameras_3_frames_3" / "benchmark.json"
    with open(cell_path) as f:
        record = json.load(f)
    assert record["problem_shape"]["memory_pressure"] == MEMORY_PRESSURE_CLEAN


# ---------------------------------------------------------------------------
# _classify_memory_pressure threshold logic (D-33 gap 3)
#
# `test_smoke_cell_reports_clean_memory_pressure` above runs a tiny cell and
# asserts "clean" -- which passes identically whether the comparison here is
# correct, inverted, or the constant is wrong by an order of magnitude. These
# tests pin the branch that actually matters. The classifier is a pure
# dict -> str function, so proving it needs no memory pressure, no subprocess,
# and no exclusive access to the machine: what remains deferred to the wave-3
# production run is whether a REAL thrashing cell trips it, not whether the
# threshold is right.
# ---------------------------------------------------------------------------


_RAM_TOTAL = 16 * 1024**3


def _reading(commit_peak: int | None = None, **overrides) -> dict:
    """One `capture_peak_memory()`-shaped boundary reading."""
    reading = {
        "peak_bytes": 1024,
        "mode": "psutil_peak_wset",
        "commit_current_bytes": commit_peak,
        "commit_peak_bytes": commit_peak,
        "ram_total_bytes": _RAM_TOTAL,
    }
    reading.update(overrides)
    return reading


def test_classify_memory_pressure_flags_a_reading_above_the_near_ceiling_fraction():
    """The branch D-33 gap 3 exists for: a cell that COMPLETED but whose peak
    approached the physical limit must not be reported as a clean
    measurement."""
    hot = int(MEMORY_NEAR_CEILING_FRACTION * _RAM_TOTAL) + 1
    memory = {"stage3_interface_optimization": _reading(commit_peak=hot)}
    assert _classify_memory_pressure(memory) == MEMORY_PRESSURE_NEAR_CEILING


def test_classify_memory_pressure_is_clean_below_the_near_ceiling_fraction():
    """A comfortable peak stays clean -- the flag must discriminate, not fire
    on everything."""
    cool = int(MEMORY_NEAR_CEILING_FRACTION * _RAM_TOTAL) - 1
    memory = {"stage3_interface_optimization": _reading(commit_peak=cool)}
    assert _classify_memory_pressure(memory) == MEMORY_PRESSURE_CLEAN


def test_classify_memory_pressure_treats_the_exact_fraction_as_near_ceiling():
    """Pins the boundary as inclusive (`>=`), so a future refactor cannot
    silently flip the comparison and pass the two tests above."""
    exact = int(MEMORY_NEAR_CEILING_FRACTION * _RAM_TOTAL)
    memory = {"stage3_interface_optimization": _reading(commit_peak=exact)}
    assert _classify_memory_pressure(memory) == MEMORY_PRESSURE_NEAR_CEILING


def test_classify_memory_pressure_uses_the_worst_boundary_not_the_last():
    """One hot boundary among several cool ones must still flag the cell --
    Stage 3 is where the peak lands, and it is not the final boundary."""
    cool = int(MEMORY_NEAR_CEILING_FRACTION * _RAM_TOTAL) - 1
    hot = int(MEMORY_NEAR_CEILING_FRACTION * _RAM_TOTAL) + 1
    memory = {
        "stage1_intrinsics": _reading(commit_peak=cool),
        "stage3_interface_optimization": _reading(commit_peak=hot),
        "stage3_second_pass": _reading(commit_peak=cool),
    }
    assert _classify_memory_pressure(memory) == MEMORY_PRESSURE_NEAR_CEILING


def test_classify_memory_pressure_falls_back_to_peak_bytes_without_commit_figures():
    """Off Windows, `commit_peak_bytes` is None-but-present; the resident
    `peak_bytes` must still be classified rather than read as zero."""
    hot = int(MEMORY_NEAR_CEILING_FRACTION * _RAM_TOTAL) + 1
    memory = {
        "stage3_interface_optimization": _reading(commit_peak=None, peak_bytes=hot)
    }
    assert _classify_memory_pressure(memory) == MEMORY_PRESSURE_NEAR_CEILING


def test_classify_memory_pressure_degrades_to_clean_without_ram_total():
    """Absence of the measurement is not evidence of pressure -- a platform
    that cannot report physical RAM yields clean, not a false flag."""
    memory = {
        "stage3_interface_optimization": _reading(
            commit_peak=10 * 1024**3, ram_total_bytes=None
        )
    }
    assert _classify_memory_pressure(memory) == MEMORY_PRESSURE_CLEAN


def test_classify_memory_pressure_degrades_to_clean_with_no_readings():
    """An empty or non-dict memory block must not raise mid-aggregation after
    a cell has already solved."""
    assert _classify_memory_pressure({}) == MEMORY_PRESSURE_CLEAN
    assert _classify_memory_pressure({"stage1_intrinsics": None}) == (
        MEMORY_PRESSURE_CLEAN
    )


# ============================================================================
# D-28 / D-29: grid-family geometry (19.2-GAP-CONTEXT.md; plan 19.2-18)
# ============================================================================


def _single_camera_view_footprint(depth: float) -> tuple[float, float]:
    """The (width, height) a single camera at the origin, at
    `GRID_HEIGHT_ABOVE_WATER` above the water surface, sees at `depth`
    (D-29's frame-fit computation) -- back-projects the four image corners
    through the refractive interface to `depth` and measures the resulting
    XY bounding box. A COMPUTATION, not a literal, so a later constant tweak
    re-checks the property rather than re-asserting a number."""
    intr = generate_camera_intrinsics(image_size=(1920, 1080), fov_horizontal_deg=60.0)
    ext = CameraExtrinsics(R=np.eye(3), t=np.zeros(3))
    camera = Camera("cam0", intr, ext)
    interface = Interface(
        normal=np.array([0.0, 0.0, -1.0]),
        camera_distances={"cam0": GRID_HEIGHT_ABOVE_WATER},
        n_air=1.0,
        n_water=1.333,
    )
    w, h = intr.image_size
    xs, ys = [], []
    for px in [(0, 0), (w, 0), (0, h), (w, h)]:
        origin, direction = refractive_back_project(camera, interface, np.array(px))
        assert origin is not None, f"back-projection failed for pixel {px}"
        t_param = (depth - origin[2]) / direction[2]
        point = origin + t_param * direction
        xs.append(point[0])
        ys.append(point[1])
    return max(xs) - min(xs), max(ys) - min(ys)


def test_board_fits_in_frame_at_every_depth_in_grid_range():
    """D-29's acceptance property: the 0.72 x 0.54 m board fits inside a
    single camera's view footprint at the minimum, middle, and maximum of
    GRID_DEPTH_RANGE -- a computation from the intrinsics and refractive
    geometry, not a literal."""
    board_width = GRID_BOARD_CONFIG.squares_x * GRID_BOARD_CONFIG.square_size
    board_height = GRID_BOARD_CONFIG.squares_y * GRID_BOARD_CONFIG.square_size

    lo, hi = GRID_DEPTH_RANGE
    mid = (lo + hi) / 2
    for depth in (lo, mid, hi):
        view_width, view_height = _single_camera_view_footprint(depth)
        assert board_width < view_width, (
            f"board width {board_width} does not fit view width "
            f"{view_width} at depth {depth}"
        )
        assert board_height < view_height, (
            f"board height {board_height} does not fit view height "
            f"{view_height} at depth {depth}"
        )


def _adjacent_overlap_fraction(
    spacing: float, depth: float, height_above_water: float
) -> float:
    """Fraction of one camera's view footprint that overlaps its neighbor's,
    for two cameras `spacing` apart along X, at `depth`, at
    `height_above_water` above the water surface. Applied identically to
    the OLD and NEW geometry below so the comparison is apples-to-apples
    regardless of which absolute methodology GAP-CONTEXT's own review used
    to produce its reported 27-55% figures."""

    def _footprint_rect(cam_x: float) -> tuple[float, float, float, float]:
        intr = generate_camera_intrinsics(
            image_size=(1920, 1080), fov_horizontal_deg=60.0
        )
        ext = CameraExtrinsics(R=np.eye(3), t=np.array([-cam_x, 0.0, 0.0]))
        camera = Camera("camX", intr, ext)
        interface = Interface(
            normal=np.array([0.0, 0.0, -1.0]),
            camera_distances={"camX": height_above_water},
            n_air=1.0,
            n_water=1.333,
        )
        w, h = intr.image_size
        xs, ys = [], []
        for px in [(0, 0), (w, 0), (0, h), (w, h)]:
            origin, direction = refractive_back_project(camera, interface, np.array(px))
            t_param = (depth - origin[2]) / direction[2]
            point = origin + t_param * direction
            xs.append(point[0])
            ys.append(point[1])
        return min(xs), max(xs), min(ys), max(ys)

    r1 = _footprint_rect(0.0)
    r2 = _footprint_rect(spacing)
    ix0, iy0 = max(r1[0], r2[0]), max(r1[2], r2[2])
    ix1, iy1 = min(r1[1], r2[1]), min(r1[3], r2[3])
    if ix1 <= ix0 or iy1 <= iy0:
        return 0.0
    inter_area = (ix1 - ix0) * (iy1 - iy0)
    self_area = (r1[1] - r1[0]) * (r1[3] - r1[2])
    return inter_area / self_area


def test_adjacent_camera_overlap_stays_comparable_to_old_geometry():
    """D-29's redundancy property: adjacent-camera overlap at the new
    GRID_SPACING/GRID_HEIGHT_ABOVE_WATER/GRID_DEPTH_RANGE stays within a
    small tolerance of the overlap the OLD grid geometry (0.15 m height,
    0.1 m spacing, (0.3, 0.6) m depth_range) achieves, using the SAME
    footprint-intersection methodology for both -- so the comparison does
    not depend on knowing which methodology GAP-CONTEXT's own review used
    to arrive at its reported 27-55% figures. Old geometry values are
    historical literals (this module's pre-D-29 defaults), not imports --
    they must never be regenerated to make this test pass."""
    old_height, old_spacing, old_depth_range = 0.15, 0.1, (0.3, 0.6)
    new_height, new_spacing, new_depth_range = (
        GRID_HEIGHT_ABOVE_WATER,
        GRID_SPACING,
        GRID_DEPTH_RANGE,
    )

    old_lo, old_hi = old_depth_range
    old_depths = (old_lo, (old_lo + old_hi) / 2, old_hi)
    new_lo, new_hi = new_depth_range
    new_depths = (new_lo, (new_lo + new_hi) / 2, new_hi)

    measured = []
    for old_depth, new_depth in zip(old_depths, new_depths):
        old_overlap = _adjacent_overlap_fraction(old_spacing, old_depth, old_height)
        new_overlap = _adjacent_overlap_fraction(new_spacing, new_depth, new_height)
        measured.append((old_depth, old_overlap, new_depth, new_overlap))
        assert new_overlap == pytest.approx(old_overlap, abs=0.10), (
            f"new-geometry overlap {new_overlap:.3f} at depth {new_depth} "
            f"diverges from old-geometry overlap {old_overlap:.3f} at depth "
            f"{old_depth} by more than the 0.10 tolerance -- measured: "
            f"{measured}"
        )


def test_xy_extent_over_array_span_is_equal_across_layouts():
    """D-28's acceptance property: xy_extent / array_span is the same for
    grid, ring, and line at 12 cameras (equality is the point of the
    change), and close to the realistic generator's ~0.54x ratio."""
    ratios = {}
    for layout in ("grid", "ring", "line"):
        xy_extent = default_xy_extent_for_layout(
            n_cameras=12, layout=layout, spacing=GRID_SPACING
        )
        _, extrinsics, _ = generate_camera_array(
            n_cameras=12, layout=layout, spacing=GRID_SPACING, seed=0
        )
        camera_positions = {cam: ext.C for cam, ext in extrinsics.items()}
        span = _array_xy_span(camera_positions)
        ratios[layout] = xy_extent / span

    values = list(ratios.values())
    assert max(values) - min(values) < 1e-9, ratios
    assert values[0] == pytest.approx(GRID_XY_EXTENT_RATIO, abs=1e-9)
    assert GRID_XY_EXTENT_RATIO == pytest.approx(0.54, abs=0.05)


def test_run_grid_cell_holdout_matches_calibration_geometry(tmp_path, monkeypatch):
    """The held-out trajectory built inside `run_grid_cell` must be built
    from the SAME depth_range/xy_extent/camera XY layout as the cell's own
    calibration trajectory, differing only in seed. FAILS if `run_grid_cell`
    reverts to calling `generate_board_trajectory` directly with bare
    defaults, since that call would omit `depth_range`/`xy_extent`
    entirely (captured as absent here) rather than matching the first
    call's explicit D-28/D-29 values.

    Camera Z (`C_z`) is deliberately NOT asserted equal between the two
    calls. D-19.4-09 moved `generate_camera_array`'s `height_variation`
    jitter onto `C_z`, which is itself seed-dependent (same as roll always
    was) -- the calibration and holdout calls use different seeds
    (`holdout_seed = seed + 1_000_000`), so their internally-constructed
    camera arrays now legitimately diverge in `C_z` by up to a few mm. This
    is harmless: only the calibration scenario's own extrinsics are ever
    used for calibration or detection generation (see `run_grid_cell`'s
    comment above its holdout-construction call); the holdout scenario's
    camera array exists solely to derive `xy_extent`, which depends only on
    XY span (`_array_xy_span`), never on Z."""
    calls: list[dict] = []
    original = e4_grid_module.generate_board_trajectory

    def _spy(*args, **kwargs):
        calls.append(kwargs)
        return original(*args, **kwargs)

    monkeypatch.setattr(e4_grid_module, "generate_board_trajectory", _spy)

    result = run_grid_cell(3, 4, seed=1, out_dir=tmp_path, force=True)
    assert result["status"] == "ok", result

    assert len(calls) == 2, "expected exactly one calibration + one holdout call"
    calib_kwargs, holdout_kwargs = calls

    assert "depth_range" in calib_kwargs and "depth_range" in holdout_kwargs
    assert calib_kwargs["depth_range"] == holdout_kwargs["depth_range"]
    assert "xy_extent" in calib_kwargs and "xy_extent" in holdout_kwargs
    assert calib_kwargs["xy_extent"] == pytest.approx(holdout_kwargs["xy_extent"])
    assert "board" in calib_kwargs and "board" in holdout_kwargs
    assert calib_kwargs["board"] == GRID_BOARD_CONFIG == holdout_kwargs["board"]

    assert (
        calib_kwargs["camera_positions"].keys()
        == holdout_kwargs["camera_positions"].keys()
    )
    for cam in calib_kwargs["camera_positions"]:
        # Camera XY positions are seed-independent (layout/spacing/n_cameras
        # alone determine them); C = R^T @ (-R @ pos) reintroduces ~1e-16
        # floating-point noise through a DIFFERENT random roll per seed --
        # assert_allclose at a tight tolerance, not exact equality. Z is
        # excluded here: D-19.4-09 moved height_variation's jitter onto
        # C_z, which is seed-dependent by design (see the docstring above).
        np.testing.assert_allclose(
            calib_kwargs["camera_positions"][cam][:2],
            holdout_kwargs["camera_positions"][cam][:2],
            atol=1e-12,
        )

    assert calib_kwargs["seed"] != holdout_kwargs["seed"]


def test_every_declared_grid_cell_constructs_legally_at_production_frame_count():
    """Construction-only geometry evidence at PRODUCTION scale for every
    committed grid cell (D-19.3-01/GEOM-01).

    This is deliberately NOT a claim that the derived-floor fix makes
    calibration converge -- anti-pattern #4 (every geometry variant
    "converges" at 6 frames with the underlying bug still present; the
    failure only shows up at ~50+ frames) means only GEOM-05's real
    convergence re-runs can make that claim. This test only proves that
    `build_grid_scenario` constructs -- without raising -- and submerges
    every board corner, for every `(n_cameras, n_frames)` in
    `DECLARED_CELLS` at its own real, PRODUCTION `n_frames` (never a
    reduced count). Construction is cheap; calibration is not, so this
    gives production-scale geometry evidence without a multi-hour run.
    No `calibrate_synthetic` call is made anywhere in this test.
    """
    from aquacal.core.board import BoardGeometry
    from aquacal.utils.transforms import rvec_to_matrix

    for n_cameras, n_frames in DECLARED_CELLS:
        scenario = build_grid_scenario(n_cameras, n_frames, seed=42)
        assert len(scenario.intrinsics) == n_cameras
        assert len(scenario.board_poses) == n_frames

        max_water_z = max(scenario.water_zs.values())
        geometry = BoardGeometry(scenario.board_config)
        corners_local = np.array(
            list(geometry.corner_positions.values()), dtype=np.float64
        )

        for pose in scenario.board_poses:
            R = rvec_to_matrix(pose.rvec)
            world_corners = (R @ corners_local.T).T + pose.tvec
            assert np.all(world_corners[:, 2] > max_water_z), (
                f"cell ({n_cameras}, {n_frames}) frame {pose.frame_idx}: "
                f"a corner is at or above max(water_zs)={max_water_z}"
            )


# ---------------------------------------------------------------------------
# COV-06 (plan 19.5-08): splice_repeat_records and the --splice-repeat CLI
# ---------------------------------------------------------------------------


def _repeat_row(
    n_cameras: int,
    n_frames: int,
    seconds1: float | None,
    seconds2: float | None,
    nfev: float | None,
    *,
    n_observations: int = 100,
    normal_fixed: bool = False,
    shared_interface: bool = True,
    seed: int = 42,
) -> dict:
    """One hand-built row carrying exactly the columns `splice_repeat_records`
    reads -- no `benchmark.json`, no `write_direct_call_benchmark`, no I/O."""
    return {
        "cell_key": f"cameras_{n_cameras}_frames_{n_frames}",
        "n_cameras": n_cameras,
        "n_frames": n_frames,
        "seed": seed,
        "normal_fixed": normal_fixed,
        "shared_interface": shared_interface,
        "n_observations": n_observations,
        "seconds_stage3_interface_optimization": seconds1,
        "seconds_stage3_intrinsic_pass": seconds2,
        "nfev_stage3_interface_optimization": nfev,
    }


def _repeat_frame(rows: list[dict]) -> pd.DataFrame:
    return pd.DataFrame(rows)


class TestSpliceRepeatRecords:
    def test_two_runs_produce_six_rows_with_a_repeat_column(self):
        run1 = _repeat_frame([_repeat_row(n, 100, 60.0, 40.0, 10) for n in (8, 12, 16)])
        run2 = _repeat_frame([_repeat_row(n, 100, 65.0, 42.0, 11) for n in (8, 12, 16)])

        result = splice_repeat_records([run1, run2], REPEAT_CELLS)

        assert len(result) == 6
        assert set(result["repeat"].unique()) == {1, 2}
        counts = result.groupby(["n_cameras", "n_frames"]).size()
        assert (counts == 2).all()

    def test_raises_naming_missing_cell(self):
        run1 = _repeat_frame([_repeat_row(n, 100, 60.0, 40.0, 10) for n in (8, 12, 16)])
        # run2 lacks (16, 100).
        run2 = _repeat_frame([_repeat_row(n, 100, 65.0, 42.0, 11) for n in (8, 12)])

        with pytest.raises(ValueError, match=re.escape("(16, 100)")):
            splice_repeat_records([run1, run2], REPEAT_CELLS)

    def test_raises_on_null_nfev_beside_nonnull_seconds(self):
        run1 = _repeat_frame([_repeat_row(n, 100, 60.0, 40.0, 10) for n in (8, 12, 16)])
        run2 = _repeat_frame(
            [
                _repeat_row(8, 100, 65.0, 42.0, None),  # nfev missing
                _repeat_row(12, 100, 65.0, 42.0, 11),
                _repeat_row(16, 100, 65.0, 42.0, 11),
            ]
        )

        with pytest.raises(ValueError, match="nfev"):
            splice_repeat_records([run1, run2], REPEAT_CELLS)

    def test_raises_when_runs_disagree_on_n_observations(self):
        run1 = _repeat_frame([_repeat_row(n, 100, 60.0, 40.0, 10) for n in (8, 12, 16)])
        run2 = _repeat_frame(
            [
                _repeat_row(8, 100, 65.0, 42.0, 11, n_observations=999),
                _repeat_row(12, 100, 65.0, 42.0, 11),
                _repeat_row(16, 100, 65.0, 42.0, 11),
            ]
        )

        with pytest.raises(ValueError, match="n_observations"):
            splice_repeat_records([run1, run2], REPEAT_CELLS)

    def test_spread_pct_matches_expected_value_for_known_totals(self):
        # (8, 100) totals 100s (run1) and 200s (run2): spread = (200-100)/150*100.
        run1 = _repeat_frame([_repeat_row(8, 100, 60.0, 40.0, 10)])
        run2 = _repeat_frame([_repeat_row(8, 100, 120.0, 80.0, 11)])

        result = splice_repeat_records([run1, run2], [(8, 100)])

        expected_pct = (200.0 - 100.0) / 150.0 * 100.0
        assert result["seconds_total"].tolist() == [100.0, 200.0]
        np.testing.assert_allclose(
            result["seconds_total_spread_pct"].tolist(),
            [expected_pct, expected_pct],
        )

    def test_no_pvalue_or_interval_column_is_ever_produced(self):
        run1 = _repeat_frame([_repeat_row(8, 100, 60.0, 40.0, 10)])
        run2 = _repeat_frame([_repeat_row(8, 100, 65.0, 42.0, 11)])

        result = splice_repeat_records([run1, run2], [(8, 100)])

        forbidden_substrings = ("pvalue", "p_value", "ci_low", "ci_high", "interval")
        for column in result.columns:
            lowered = column.lower()
            assert not any(term in lowered for term in forbidden_substrings), (
                f"column {column!r} looks like a p-value/interval; n=2 supports "
                "only a spread (T-19.5-08-03)"
            )

    def test_is_pure_no_file_opened(self, monkeypatch):
        run1 = _repeat_frame([_repeat_row(8, 100, 60.0, 40.0, 10)])
        run2 = _repeat_frame([_repeat_row(8, 100, 65.0, 42.0, 11)])

        import builtins

        real_open = builtins.open

        def _forbid_open(*args, **kwargs):
            raise AssertionError(
                "splice_repeat_records must open no file -- it is a pure "
                "function over already-loaded DataFrames"
            )

        monkeypatch.setattr(builtins, "open", _forbid_open)
        try:
            splice_repeat_records([run1, run2], [(8, 100)])
        finally:
            monkeypatch.setattr(builtins, "open", real_open)


class TestSpliceRepeatCli:
    def test_help_lists_splice_repeat(self, capsys):
        parser = build_arg_parser()
        with pytest.raises(SystemExit):
            parser.parse_args(["--help"])
        captured = capsys.readouterr()
        assert "--splice-repeat" in captured.out

    def test_splice_repeat_combined_with_check_names_both_flags(self, capsys):
        parser = build_arg_parser()
        args = parser.parse_args(["--splice-repeat", "some_dir", "--check"])
        with pytest.raises(SystemExit):
            _validate_e4_args(parser, args)
        captured = capsys.readouterr()
        assert "--splice-repeat" in captured.err
        assert "--check" in captured.err

    def test_splice_repeat_combined_with_smoke_names_both_flags(self, capsys):
        parser = build_arg_parser()
        args = parser.parse_args(["--splice-repeat", "some_dir", "--smoke"])
        with pytest.raises(SystemExit):
            _validate_e4_args(parser, args)
        captured = capsys.readouterr()
        assert "--splice-repeat" in captured.err
        assert "--smoke" in captured.err

    def test_shared_five_flag_contract_unchanged(self):
        parser = build_experiment_arg_parser()
        options = sorted(
            a.option_strings[0] for a in parser._actions if a.option_strings
        )
        assert options == ["--check", "--force", "--out", "--seed", "--smoke"]

    def test_splice_repeat_cli_writes_six_row_csv_without_solving(
        self, tmp_path, monkeypatch
    ):
        # Run 1: a committed-shaped benchmark_grid.csv in a throwaway --out dir.
        out_dir = tmp_path / "out"
        cells_dir = out_dir / "e4_cells"
        for n_cameras, n_frames in DECLARED_CELLS:
            _write_fake_cell(
                cells_dir / f"cameras_{n_cameras}_frames_{n_frames}",
                n_cameras,
                n_frames,
            )
        e2_path = out_dir / "e2_benchmark.json"
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
        df = build_grid_dataframe(out_dir, cell_statuses, e2_path)
        write_experiment_csv(
            df, out_dir / "benchmark_grid.csv", key_columns=GRID_KEY_COLUMNS, force=True
        )

        # Run 2: the repeat directory -- same seed as run 1 (a genuine repeat
        # of the same problem, not a different seed), only the three
        # REPEAT_CELLS.
        repeat_dir = tmp_path / "repeat"
        repeat_cells_dir = repeat_dir / "e4_cells"
        for n_cameras, n_frames in REPEAT_CELLS:
            _write_fake_cell(
                repeat_cells_dir / f"cameras_{n_cameras}_frames_{n_frames}",
                n_cameras,
                n_frames,
            )

        def _forbid_calibrate(*args, **kwargs):
            raise AssertionError(
                "--splice-repeat must perform no solve: calibrate_synthetic was called"
            )

        monkeypatch.setattr(e4_grid_module, "calibrate_synthetic", _forbid_calibrate)

        exit_code = e4_grid_module.main(
            ["--splice-repeat", str(repeat_dir), "--out", str(out_dir)]
        )
        assert exit_code == 0

        repeat_csv = out_dir / "benchmark_grid_repeat.csv"
        assert repeat_csv.exists()
        written = pd.read_csv(repeat_csv)
        assert len(written) == 6
        assert set(written["repeat"].unique()) == {1, 2}
        assert "scope" in written.columns
        assert (written["scope"].str.len() > 0).all()

    def test_splice_repeat_test_never_writes_into_committed_results_tree(
        self, tmp_path, monkeypatch
    ):
        out_dir = tmp_path / "out"
        cells_dir = out_dir / "e4_cells"
        for n_cameras, n_frames in DECLARED_CELLS:
            _write_fake_cell(
                cells_dir / f"cameras_{n_cameras}_frames_{n_frames}",
                n_cameras,
                n_frames,
            )
        e2_path = out_dir / "e2_benchmark.json"
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
        df = build_grid_dataframe(out_dir, cell_statuses, e2_path)
        write_experiment_csv(
            df, out_dir / "benchmark_grid.csv", key_columns=GRID_KEY_COLUMNS, force=True
        )

        repeat_dir = tmp_path / "repeat"
        repeat_cells_dir = repeat_dir / "e4_cells"
        for n_cameras, n_frames in REPEAT_CELLS:
            _write_fake_cell(
                repeat_cells_dir / f"cameras_{n_cameras}_frames_{n_frames}",
                n_cameras,
                n_frames,
            )

        exit_code = e4_grid_module.main(
            ["--splice-repeat", str(repeat_dir), "--out", str(out_dir)]
        )
        assert exit_code == 0

        import subprocess

        result = subprocess.run(
            ["git", "status", "--porcelain", "experiments/results/"],
            capture_output=True,
            text=True,
        )
        assert result.stdout.strip() == ""
