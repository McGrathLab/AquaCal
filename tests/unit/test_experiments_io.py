"""Unit tests for experiments._io (EXP-02): CLI contract, --check comparator,
determinism, resumability, and the direct-call benchmark.json wrapper.

All tests are fast: no calibration, no download, and none are marked slow.
"""

from __future__ import annotations

import json

import pandas as pd
import pytest

from experiments._io import (
    build_experiment_arg_parser,
    compare_experiment_csv,
    exit_code_for,
    validate_args,
    write_direct_call_benchmark,
    write_experiment_csv,
)

# The real committed exp1_parameter_errors.csv header (D-19/D-06.3), used
# verbatim so a header-contract change breaks these tests intentionally.
EXP1_COLUMNS = [
    "camera",
    "model",
    "focal_length_error_pct",
    "z_position_error_mm",
    "xy_position_error_mm",
    "gt_x_m",
    "gt_y_m",
    "gt_z_m",
    "est_x_m",
    "est_y_m",
    "est_z_m",
    "reprojection_rms_px",
]
EXP1_KEY_COLUMNS = ["camera", "model"]
CHECK_RTOL = 1e-6


_CAMERA_VALUES = {
    "cam0": 0,
    "cam1": 1,
    "cam2": 2,
}


def _exp1_frame(camera_order: list[str] | None = None) -> pd.DataFrame:
    cameras = camera_order or ["cam0", "cam1", "cam2"]
    rows = []
    for cam in cameras:
        i = _CAMERA_VALUES[cam]
        rows.append(
            {
                "camera": cam,
                "model": "refractive",
                "focal_length_error_pct": 0.1 + i,
                "z_position_error_mm": 1.0 + i,
                "xy_position_error_mm": 0.5 + i,
                "gt_x_m": 0.0 + i,
                "gt_y_m": 0.0 + i,
                "gt_z_m": 0.0,
                "est_x_m": 0.0 + i,
                "est_y_m": 0.0 + i,
                "est_z_m": 0.001 * i,
                "reprojection_rms_px": 0.5,
            }
        )
    return pd.DataFrame(rows, columns=EXP1_COLUMNS)


class TestCli:
    def test_cli_five_flags_and_defaults(self):
        parser = build_experiment_arg_parser()
        options = sorted(o for a in parser._actions for o in a.option_strings)
        assert options == ["--check", "--force", "--out", "--seed", "--smoke"]

        args = parser.parse_args([])
        assert args.seed == 42
        assert str(args.out).replace("\\", "/").endswith("experiments/results")
        assert args.force is False
        assert args.smoke is False
        assert args.check is False

    def test_cli_check_and_force_mutually_exclusive(self, capsys):
        parser = build_experiment_arg_parser()
        args = parser.parse_args(["--check", "--force"])
        with pytest.raises(SystemExit):
            validate_args(parser, args)
        captured = capsys.readouterr()
        assert "mutually exclusive" in captured.err

    def test_cli_seed_overrides_default(self):
        parser = build_experiment_arg_parser()
        args = parser.parse_args(["--seed", "7"])
        assert args.seed == 7


class TestCheckComparator:
    def test_check_passes_within_rtol(self, tmp_path):
        committed = _exp1_frame()
        committed_path = tmp_path / "exp1_parameter_errors.csv"
        committed.to_csv(committed_path, index=False)

        fresh = committed.copy()
        fresh.loc[0, "reprojection_rms_px"] = fresh.loc[0, "reprojection_rms_px"] * (
            1 + 0.5 * CHECK_RTOL
        )

        report = compare_experiment_csv(
            fresh, committed_path, key_columns=EXP1_KEY_COLUMNS, rtol=CHECK_RTOL
        )
        assert report.passed is True
        assert exit_code_for(report) == 0

    def test_check_fails_outside_rtol_and_names_worst_cell(self, tmp_path):
        committed = _exp1_frame()
        committed_path = tmp_path / "exp1_parameter_errors.csv"
        committed.to_csv(committed_path, index=False)

        fresh = committed.copy()
        fresh.loc[1, "reprojection_rms_px"] = fresh.loc[1, "reprojection_rms_px"] * (
            1 + 10 * CHECK_RTOL
        )

        report = compare_experiment_csv(
            fresh, committed_path, key_columns=EXP1_KEY_COLUMNS, rtol=CHECK_RTOL
        )
        assert report.passed is False
        assert "reprojection_rms_px" in report.worst_cell
        assert "cam1" in report.worst_cell
        assert exit_code_for(report) == 1

    def test_check_non_float_columns_exact(self, tmp_path):
        committed = _exp1_frame()
        committed_path = tmp_path / "exp1_parameter_errors.csv"
        committed.to_csv(committed_path, index=False)

        fresh = committed.copy()
        fresh.loc[0, "model"] = "nonrefractive"

        report = compare_experiment_csv(
            fresh, committed_path, key_columns=EXP1_KEY_COLUMNS, rtol=1.0
        )
        assert report.passed is False

    def test_check_realigns_on_key_columns_not_row_index(self, tmp_path):
        committed = _exp1_frame()
        committed_shuffled = committed.iloc[::-1].reset_index(drop=True)
        committed_path = tmp_path / "exp1_parameter_errors.csv"
        committed_shuffled.to_csv(committed_path, index=False)

        fresh = committed.copy()  # original (non-shuffled) order

        report = compare_experiment_csv(
            fresh, committed_path, key_columns=EXP1_KEY_COLUMNS, rtol=CHECK_RTOL
        )
        assert report.passed is True

    def test_check_header_mismatch_fails(self, tmp_path):
        committed = _exp1_frame()
        committed_path = tmp_path / "exp1_parameter_errors.csv"
        committed.to_csv(committed_path, index=False)

        fresh = committed.drop(columns=["k1_error"], errors="ignore").copy()
        fresh["extra_column"] = 1.0

        report = compare_experiment_csv(
            fresh, committed_path, key_columns=EXP1_KEY_COLUMNS, rtol=CHECK_RTOL
        )
        assert report.passed is False
        assert "extra_column" in report.message or "Header mismatch" in report.message

    def test_check_never_writes(self, tmp_path):
        committed = _exp1_frame()
        committed_path = tmp_path / "exp1_parameter_errors.csv"
        committed.to_csv(committed_path, index=False)
        mtime_before = committed_path.stat().st_mtime
        bytes_before = committed_path.read_bytes()

        fresh = committed.copy()
        fresh.loc[0, "reprojection_rms_px"] = 999.0

        compare_experiment_csv(
            fresh, committed_path, key_columns=EXP1_KEY_COLUMNS, rtol=CHECK_RTOL
        )

        assert committed_path.stat().st_mtime == mtime_before
        assert committed_path.read_bytes() == bytes_before


class TestDeterminism:
    def test_determinism_writer_sorts_by_key_columns(self, tmp_path):
        frame_a = _exp1_frame(["cam2", "cam0", "cam1"])
        frame_b = _exp1_frame(["cam1", "cam2", "cam0"])

        path_a = tmp_path / "a.csv"
        path_b = tmp_path / "b.csv"
        write_experiment_csv(frame_a, path_a, key_columns=EXP1_KEY_COLUMNS, force=True)
        write_experiment_csv(frame_b, path_b, key_columns=EXP1_KEY_COLUMNS, force=True)

        assert path_a.read_bytes() == path_b.read_bytes()

    def test_determinism_no_timestamp_in_csv(self, tmp_path):
        frame = _exp1_frame()
        path = tmp_path / "exp1.csv"
        write_experiment_csv(frame, path, key_columns=EXP1_KEY_COLUMNS, force=True)

        text = path.read_text()
        assert not any(str(year) in text for year in range(2000, 2100))
        for banned in ("timestamp", "wall_clock", "host"):
            assert banned not in text.lower()


class TestResume:
    def test_resume_skips_existing_without_force(self, tmp_path):
        frame = _exp1_frame()
        path = tmp_path / "exp1.csv"

        wrote = write_experiment_csv(
            frame, path, key_columns=EXP1_KEY_COLUMNS, force=True
        )
        assert wrote is True
        bytes_before = path.read_bytes()

        frame_changed = frame.copy()
        frame_changed.loc[0, "reprojection_rms_px"] = 999.0
        wrote_again = write_experiment_csv(
            frame_changed, path, key_columns=EXP1_KEY_COLUMNS, force=False
        )
        assert wrote_again is False
        assert path.read_bytes() == bytes_before

        wrote_forced = write_experiment_csv(
            frame_changed, path, key_columns=EXP1_KEY_COLUMNS, force=True
        )
        assert wrote_forced is True
        assert path.read_bytes() != bytes_before

    def test_writer_rejects_missing_key_column(self, tmp_path):
        frame = _exp1_frame()
        path = tmp_path / "exp1.csv"
        with pytest.raises(ValueError):
            write_experiment_csv(frame, path, key_columns=["not_a_column"], force=True)


class TestRecord:
    def test_record_assembles_at_schema_version_1(self, tmp_path):
        from aquacal.calibration._observability import SolverDiagnostics

        path = tmp_path / "benchmark.json"
        write_direct_call_benchmark(
            path,
            problem_shape={"n_cameras": 3},
            timings={"stage3_interface_optimization": 1.0},
            diagnostics={"stage3_interface_optimization": SolverDiagnostics()},
            solver_config={"robust_loss": "huber"},
            accuracy={"reprojection_rms_px": 0.5},
        )
        record = json.loads(path.read_text())
        assert record["schema_version"] == 1

    def test_record_omits_memory_key(self, tmp_path):
        from aquacal.calibration._observability import SolverDiagnostics

        path = tmp_path / "benchmark.json"
        write_direct_call_benchmark(
            path,
            problem_shape={},
            timings={"stage3_interface_optimization": 1.0},
            diagnostics={"stage3_interface_optimization": SolverDiagnostics()},
            solver_config={},
            accuracy={},
        )
        record = json.loads(path.read_text())
        assert "memory" not in record

    def test_record_rejects_unsettled_stage_key(self, tmp_path):
        from aquacal.calibration._observability import SolverDiagnostics

        path = tmp_path / "benchmark.json"
        with pytest.raises(ValueError, match="stage4"):
            write_direct_call_benchmark(
                path,
                problem_shape={},
                timings={"stage4": 1.0},
                diagnostics={"stage4": SolverDiagnostics()},
                solver_config={},
                accuracy={},
            )

        with pytest.raises(ValueError, match="stage3"):
            write_direct_call_benchmark(
                path,
                problem_shape={},
                timings={"stage3": 1.0},
                diagnostics={"stage3": SolverDiagnostics()},
                solver_config={},
                accuracy={},
            )

    def test_record_environment_block_present(self, tmp_path):
        from aquacal.calibration._observability import SolverDiagnostics
        from aquacal.io import capture_environment

        path = tmp_path / "benchmark.json"
        write_direct_call_benchmark(
            path,
            problem_shape={},
            timings={"stage3_interface_optimization": 1.0},
            diagnostics={"stage3_interface_optimization": SolverDiagnostics()},
            solver_config={},
            accuracy={},
        )
        record = json.loads(path.read_text())
        expected_keys = set(capture_environment().keys())
        assert expected_keys.issubset(record["environment"].keys())


class TestMemoryReadings:
    def test_no_memory_key_when_memory_readings_omitted(self, tmp_path):
        """Byte-shape-identical to E1's/E7's committed records: omitting
        memory_readings must leave the record with no "memory" key at all."""
        from aquacal.calibration._observability import SolverDiagnostics

        path = tmp_path / "benchmark.json"
        write_direct_call_benchmark(
            path,
            problem_shape={},
            timings={"stage3_interface_optimization": 1.0},
            diagnostics={"stage3_interface_optimization": SolverDiagnostics()},
            solver_config={},
            accuracy={},
        )
        record = json.loads(path.read_text())
        assert "memory" not in record

    def test_memory_key_present_when_memory_readings_supplied(self, tmp_path):
        from aquacal.calibration._observability import SolverDiagnostics

        path = tmp_path / "benchmark.json"
        write_direct_call_benchmark(
            path,
            problem_shape={},
            timings={"stage3_interface_optimization": 1.0},
            diagnostics={"stage3_interface_optimization": SolverDiagnostics()},
            solver_config={},
            accuracy={},
            memory_readings={
                "_baseline": {"peak_bytes": 1000, "mode": "psutil_peak_wset"},
                "stage3_interface_optimization": {
                    "peak_bytes": 1500,
                    "mode": "psutil_peak_wset",
                },
            },
        )
        record = json.loads(path.read_text())
        assert "memory" in record

    def test_memory_readings_baseline_key_not_subject_to_stage_allowlist(
        self, tmp_path
    ):
        """_baseline is legitimately outside the settled stage vocabulary;
        passing it via memory_readings must not raise."""
        from aquacal.calibration._observability import SolverDiagnostics

        path = tmp_path / "benchmark.json"
        wrote = write_direct_call_benchmark(
            path,
            problem_shape={},
            timings={"stage3_interface_optimization": 1.0},
            diagnostics={"stage3_interface_optimization": SolverDiagnostics()},
            solver_config={},
            accuracy={},
            memory_readings={"_baseline": {"peak_bytes": 1000, "mode": "m"}},
        )
        assert wrote is True

    def test_unsettled_stage_key_in_timings_still_raises(self, tmp_path):
        """The stage-key allowlist still guards timings/diagnostics even when
        memory_readings is supplied."""
        from aquacal.calibration._observability import SolverDiagnostics

        path = tmp_path / "benchmark.json"
        with pytest.raises(ValueError, match="stage4"):
            write_direct_call_benchmark(
                path,
                problem_shape={},
                timings={"stage4": 1.0},
                diagnostics={"stage4": SolverDiagnostics()},
                solver_config={},
                accuracy={},
                memory_readings={"_baseline": {"peak_bytes": 1000, "mode": "m"}},
            )


class TestSeed:
    def test_no_seed_key_when_seed_omitted(self, tmp_path):
        from aquacal.calibration._observability import SolverDiagnostics

        path = tmp_path / "benchmark.json"
        write_direct_call_benchmark(
            path,
            problem_shape={},
            timings={"stage3_interface_optimization": 1.0},
            diagnostics={"stage3_interface_optimization": SolverDiagnostics()},
            solver_config={"robust_loss": "huber"},
            accuracy={},
        )
        record = json.loads(path.read_text())
        assert "seed" not in record["solver_config"]

    def test_seed_stamped_into_solver_config_alongside_existing_keys(self, tmp_path):
        from aquacal.calibration._observability import SolverDiagnostics

        path = tmp_path / "benchmark.json"
        write_direct_call_benchmark(
            path,
            problem_shape={},
            timings={"stage3_interface_optimization": 1.0},
            diagnostics={"stage3_interface_optimization": SolverDiagnostics()},
            solver_config={"robust_loss": "huber", "loss_scale": 1.0},
            accuracy={},
            seed=1234,
        )
        record = json.loads(path.read_text())
        assert record["solver_config"]["seed"] == 1234
        assert record["solver_config"]["robust_loss"] == "huber"
        assert record["solver_config"]["loss_scale"] == 1.0

    def test_seed_conflict_with_existing_solver_config_key_raises(self, tmp_path):
        from aquacal.calibration._observability import SolverDiagnostics

        path = tmp_path / "benchmark.json"
        with pytest.raises(ValueError, match="seed"):
            write_direct_call_benchmark(
                path,
                problem_shape={},
                timings={"stage3_interface_optimization": 1.0},
                diagnostics={"stage3_interface_optimization": SolverDiagnostics()},
                solver_config={"seed": 42},
                accuracy={},
                seed=1234,
            )

    def test_seed_does_not_mutate_callers_solver_config_dict(self, tmp_path):
        from aquacal.calibration._observability import SolverDiagnostics

        path = tmp_path / "benchmark.json"
        solver_config = {"robust_loss": "huber"}
        original = dict(solver_config)
        write_direct_call_benchmark(
            path,
            problem_shape={},
            timings={"stage3_interface_optimization": 1.0},
            diagnostics={"stage3_interface_optimization": SolverDiagnostics()},
            solver_config=solver_config,
            accuracy={},
            seed=1234,
        )
        assert solver_config == original
        assert "seed" not in solver_config


class TestCommittedRecordUntouchedBySeed:
    def test_e1_committed_record_has_no_seed_key(self):
        import pathlib

        record = json.loads(
            pathlib.Path("experiments/results/e1_benchmark_refractive.json").read_text()
        )
        assert "seed" not in record["solver_config"]
