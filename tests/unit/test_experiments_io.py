"""Unit tests for experiments._io (EXP-02): CLI contract, --check comparator,
determinism, resumability, and the direct-call benchmark.json wrapper.

All tests are fast: no calibration, no download, and none are marked slow.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd
import pytest

from experiments._io import (
    add_baseline_dir_argument,
    build_experiment_arg_parser,
    compare_experiment_csv,
    compare_experiment_csv_if_present,
    exit_code_for,
    resolve_baseline_dir,
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

    def test_exclude_columns_ignores_differences_only_in_named_columns(self, tmp_path):
        """D-07/D-08: excluding a column skips it in the cell comparison, and
        the report still fails when a NON-excluded column differs."""
        committed = _exp1_frame()
        committed_path = tmp_path / "exp1_parameter_errors.csv"
        committed.to_csv(committed_path, index=False)

        # Differ ONLY in "gt_x_m" (a non-key float column).
        fresh = committed.copy()
        fresh.loc[0, "gt_x_m"] = fresh.loc[0, "gt_x_m"] + 100.0

        report = compare_experiment_csv(
            fresh,
            committed_path,
            key_columns=EXP1_KEY_COLUMNS,
            rtol=CHECK_RTOL,
            exclude_columns=("gt_x_m",),
        )
        assert report.passed is True

        # Now also differ in a NON-excluded column -- must still fail.
        fresh.loc[1, "reprojection_rms_px"] = fresh.loc[1, "reprojection_rms_px"] * (
            1 + 10 * CHECK_RTOL
        )
        report2 = compare_experiment_csv(
            fresh,
            committed_path,
            key_columns=EXP1_KEY_COLUMNS,
            rtol=CHECK_RTOL,
            exclude_columns=("gt_x_m",),
        )
        assert report2.passed is False
        assert "reprojection_rms_px" in report2.worst_cell

    def test_exclude_columns_never_exempts_the_header_comparison(self, tmp_path):
        """D-07: a header difference must still fail even when the differing
        column is named in exclude_columns -- the schema contract is never
        excludable."""
        committed = _exp1_frame()
        committed_path = tmp_path / "exp1_parameter_errors.csv"
        committed.to_csv(committed_path, index=False)

        fresh = committed.drop(columns=["gt_x_m"]).copy()

        report = compare_experiment_csv(
            fresh,
            committed_path,
            key_columns=EXP1_KEY_COLUMNS,
            rtol=CHECK_RTOL,
            exclude_columns=("gt_x_m",),
        )
        assert report.passed is False
        assert "Header mismatch" in report.message

    def test_exclude_columns_default_reproduces_todays_exact_behavior(self, tmp_path):
        """Omitting exclude_columns must leave today's outcome and message
        byte-identical on an unchanged fixture."""
        committed = _exp1_frame()
        committed_path = tmp_path / "exp1_parameter_errors.csv"
        committed.to_csv(committed_path, index=False)

        fresh = committed.copy()

        report_default = compare_experiment_csv(
            fresh, committed_path, key_columns=EXP1_KEY_COLUMNS, rtol=CHECK_RTOL
        )
        report_explicit_empty = compare_experiment_csv(
            fresh,
            committed_path,
            key_columns=EXP1_KEY_COLUMNS,
            rtol=CHECK_RTOL,
            exclude_columns=(),
        )
        assert report_default == report_explicit_empty
        assert report_default.passed is True
        assert (
            report_default.message
            == "Fresh output matches committed baseline within tolerance."
        )

    def test_check_passes_on_mixed_empty_and_real_string_column(self, tmp_path):
        """Regression for 19.2-11/19.2-12 (review H upstream finding 2): a
        `status_reason`-shaped column with MOSTLY empty strings but at least
        one real string (E6's actual shape: 13 "ok" rows + 1
        `KeyError: 'cam11'` row) must not be misclassified as mismatched.

        This is a DIFFERENT defect class from the all-empty-string column
        19.2-09 fixed (which round-trips to an all-NaN float64 column): a
        column with at least one real string stays object/str-dtype on
        read-back, but its "" cells still round-trip through CSV as an empty
        field indistinguishable from a missing value, so pandas reads them
        back as `NaN` sitting inside an otherwise string-dtype column. A
        naive `!=` compare then reports every "" row as mismatched against a
        `NaN`, even though they mean the same thing here.
        """
        committed = pd.DataFrame(
            {
                "axis": ["index", "layout"],
                "axis_value": ["1.333", "line"],
                "status_reason": ["", "KeyError: 'cam11'"],
            }
        )
        committed_path = tmp_path / "generalization_sweep.csv"
        committed.to_csv(committed_path, index=False)

        # Read back what write_experiment_csv's own round-trip would produce
        # for `fresh` -- constructed directly (not re-read from CSV) so this
        # test exercises the exact fresh-DataFrame shape run_sweep() builds.
        fresh = committed.copy()

        report = compare_experiment_csv(
            fresh, committed_path, key_columns=["axis", "axis_value"], rtol=CHECK_RTOL
        )
        assert report.passed is True
        assert exit_code_for(report) == 0

    def test_check_still_fails_when_mixed_string_column_genuinely_differs(
        self, tmp_path
    ):
        """The mixed-column NaN/"" normalization must not mask a real mismatch."""
        committed = pd.DataFrame(
            {
                "axis": ["index", "layout"],
                "axis_value": ["1.333", "line"],
                "status_reason": ["", "KeyError: 'cam11'"],
            }
        )
        committed_path = tmp_path / "generalization_sweep.csv"
        committed.to_csv(committed_path, index=False)

        fresh = committed.copy()
        fresh.loc[1, "status_reason"] = "KeyError: 'cam99'"

        report = compare_experiment_csv(
            fresh, committed_path, key_columns=["axis", "axis_value"], rtol=CHECK_RTOL
        )
        assert report.passed is False
        assert "status_reason" in report.worst_cell

    def test_check_row_count_mismatch_reports_not_raises(self, tmp_path):
        """Regression for CR-04 case 1: a fresh frame with more rows than the
        committed baseline (same header) must return a failing
        `ComparisonReport` naming the extra key, never raise. This FAILS on
        EXPECTED_BASE with `ValueError: Can only compare identically-labeled
        Series objects` because the old code sorted both frames and compared
        positionally without checking length first. A row-count mismatch that
        also differs in key set is reported via the key-set-mismatch path
        (it subsumes the plain row-count case -- see task 1's action)."""
        committed = _exp1_frame(["cam0", "cam1"])
        committed_path = tmp_path / "exp1_parameter_errors.csv"
        committed.to_csv(committed_path, index=False)

        fresh = _exp1_frame(["cam0", "cam1", "cam2"])

        report = compare_experiment_csv(
            fresh, committed_path, key_columns=EXP1_KEY_COLUMNS, rtol=CHECK_RTOL
        )
        assert report.passed is False
        assert "cam2" in report.message
        assert str(committed_path) in report.message
        assert exit_code_for(report) == 1

    def test_check_key_set_mismatch_at_equal_length_names_both_sides(self, tmp_path):
        """Regression for WR-10: equal row counts but a differing key set must
        be reported as its own failure mode naming the fresh-only and
        committed-only keys, not silently compared positionally (row i of one
        frame against a different row i of the other)."""
        committed = _exp1_frame(["cam0", "cam1"])
        committed_path = tmp_path / "exp1_parameter_errors.csv"
        committed.to_csv(committed_path, index=False)

        fresh = _exp1_frame(["cam0", "cam2"])

        report = compare_experiment_csv(
            fresh, committed_path, key_columns=EXP1_KEY_COLUMNS, rtol=CHECK_RTOL
        )
        assert report.passed is False
        assert "cam2" in report.message
        assert "cam1" in report.message
        assert exit_code_for(report) == 1

    def test_check_duplicate_key_reports_not_raises(self, tmp_path):
        """Equal key sets (per unique value) but a duplicate key on one side
        must be reported as its own structural failure, not compared
        positionally."""
        committed = _exp1_frame(["cam0", "cam1"])
        committed_path = tmp_path / "exp1_parameter_errors.csv"
        committed.to_csv(committed_path, index=False)

        fresh = pd.concat([_exp1_frame(["cam0"]), _exp1_frame(["cam0"])]).reset_index(
            drop=True
        )
        fresh = pd.concat([fresh, _exp1_frame(["cam1"])]).reset_index(drop=True)

        report = compare_experiment_csv(
            fresh, committed_path, key_columns=EXP1_KEY_COLUMNS, rtol=CHECK_RTOL
        )
        assert report.passed is False
        assert exit_code_for(report) == 1

    def test_check_matching_keys_still_names_worst_cell_from_true_counterpart(
        self, tmp_path
    ):
        """Key-based alignment must still identify the same worst cell as
        today's positional comparison when keys match (WR-10 closure must not
        change a passing verdict's cell identification)."""
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

    def test_check_worst_cell_loop_tolerates_nonnumeric_in_float_column(self, tmp_path):
        """Regression for CR-04 case 2: a column that is all-NaN float in
        `fresh` and carries a real string in `committed` in exactly ONE row
        out of several (e.g. `status_reason` in `generalization_sweep.csv`:
        13 empty rows + 1 `KeyError: 'cam11'` row) lands in `float_columns`
        (classified by dtype in EITHER frame), fails the frame-level
        assert_frame_equal as intended, but must not raise inside the
        worst-cell loop when it calls `to_numpy(dtype=float)`. This FAILS on
        EXPECTED_BASE with `ValueError: could not convert string to float:
        "KeyError: 'cam11'"`.
        """
        committed = pd.DataFrame(
            {
                "axis": ["index", "layout", "layout"],
                "axis_value": ["1.333", "grid", "line"],
                "status_reason": ["", "", "KeyError: 'cam11'"],
            }
        )
        committed_path = tmp_path / "generalization_sweep.csv"
        committed.to_csv(committed_path, index=False)

        # fresh's status_reason column is all-NaN float (e.g. every cell
        # unset because the fresh run never populated a reason) -- the shape
        # that triggers CR-04 case 2 rather than case 1 (which is
        # all-empty-string in fresh, already handled).
        fresh = pd.DataFrame(
            {
                "axis": ["index", "layout", "layout"],
                "axis_value": ["1.333", "grid", "line"],
                "status_reason": [float("nan"), float("nan"), float("nan")],
            }
        )

        report = compare_experiment_csv(
            fresh,
            committed_path,
            key_columns=["axis", "axis_value"],
            rtol=CHECK_RTOL,
        )
        assert report.passed is False
        assert "status_reason" in report.message

    def test_check_numeric_mismatch_worst_rtol_unchanged_by_coercion(self, tmp_path):
        """The to_numeric coercion in the worst-cell loop must not change the
        worst_rtol value for a purely numeric mismatch -- pinned against the
        EXPECTED_BASE value for this exact fixture (10x rtol offset on
        row 1's reprojection_rms_px, matching
        test_check_fails_outside_rtol_and_names_worst_cell)."""
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
        assert report.worst_rtol == pytest.approx(10 * CHECK_RTOL, rel=1e-3)

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
        """Phase 26 / DRIVER-04 (D-28) moved the committed baselines to
        experiments/pre_rerun_baseline/ so the frozen sha ships with an empty
        experiments/results/. This asserts a property of the COMMITTED record,
        so the archive is its subject. Anchored to the repo root rather than
        cwd (WR-06) and guarded, so a fresh clone -- which has neither tree --
        skips rather than erroring.
        """
        import pathlib

        baseline = (
            pathlib.Path(__file__).resolve().parents[2]
            / "experiments"
            / "pre_rerun_baseline"
            / "results"
            / "e1_benchmark_refractive.json"
        )
        if not baseline.exists():
            pytest.skip(f"committed baseline absent (fresh clone): {baseline}")
        record = json.loads(baseline.read_text())
        assert "seed" not in record["solver_config"]


class TestBaselineDir:
    """Phase 26 / DRIVER-03 (D-12, ruling A4): `--check` must be able to read its
    baselines from the archive DRIVER-04 moved them into, and a baseline that is
    absent by policy must report N/A rather than raise.
    """

    def test_shared_parser_still_exposes_exactly_five_flags(self):
        """`--baseline-dir` is SCRIPT-LOCAL: the shared five-flag contract (D-21)
        must not have widened to serve the two scripts that need it.
        """
        parser = build_experiment_arg_parser()
        options = sorted(o for a in parser._actions for o in a.option_strings)
        assert options == ["--check", "--force", "--out", "--seed", "--smoke"]
        assert not hasattr(parser.parse_args([]), "baseline_dir")

    def test_add_baseline_dir_argument_adds_one_optional_path_flag(self):
        parser = argparse.ArgumentParser(add_help=False)
        returned = add_baseline_dir_argument(parser)
        assert returned is parser

        args = parser.parse_args([])
        assert args.baseline_dir is None

        args = parser.parse_args(["--baseline-dir", "experiments/pre_rerun_baseline"])
        assert isinstance(args.baseline_dir, Path)
        assert str(args.baseline_dir).replace("\\", "/") == (
            "experiments/pre_rerun_baseline"
        )

    def test_add_baseline_dir_argument_rejects_a_duplicate_flag(self):
        parser = argparse.ArgumentParser(add_help=False)
        add_baseline_dir_argument(parser)
        with pytest.raises(argparse.ArgumentError):
            add_baseline_dir_argument(parser)

    def test_resolve_baseline_dir_falls_back_to_out_dir(self, tmp_path):
        assert resolve_baseline_dir(None, tmp_path) == Path(tmp_path)

    def test_resolve_baseline_dir_prefers_the_explicit_directory(self, tmp_path):
        archive = tmp_path / "pre_rerun_baseline" / "results"
        assert resolve_baseline_dir(archive, tmp_path) == Path(archive)

    def test_resolve_baseline_dir_never_creates_anything(self, tmp_path):
        archive = tmp_path / "does_not_exist"
        resolve_baseline_dir(archive, tmp_path)
        assert not archive.exists()

    def test_if_present_returns_none_for_a_missing_baseline(self, tmp_path):
        """Ruling A4: E2's reprojection_residuals.csv / reconstruction_errors.csv
        are gitignored by DATA-01b policy, so neither experiments/results/ nor the
        archive holds them. N/A beats a FileNotFoundError raised after a 50-87
        minute calibration.
        """
        missing = tmp_path / "reprojection_residuals.csv"
        report = compare_experiment_csv_if_present(
            _exp1_frame(),
            missing,
            key_columns=EXP1_KEY_COLUMNS,
            rtol=CHECK_RTOL,
        )
        assert report is None

    def test_if_present_matches_compare_when_the_baseline_exists(self, tmp_path):
        committed = _exp1_frame()
        committed_path = tmp_path / "exp1_parameter_errors.csv"
        committed.to_csv(committed_path, index=False)
        fresh = committed.copy()

        direct = compare_experiment_csv(
            fresh, committed_path, key_columns=EXP1_KEY_COLUMNS, rtol=CHECK_RTOL
        )
        guarded = compare_experiment_csv_if_present(
            fresh, committed_path, key_columns=EXP1_KEY_COLUMNS, rtol=CHECK_RTOL
        )
        assert guarded == direct
        assert guarded is not None
        assert guarded.passed

    def test_if_present_forwards_exclude_columns(self, tmp_path):
        committed = _exp1_frame()
        committed_path = tmp_path / "exp1_parameter_errors.csv"
        committed.to_csv(committed_path, index=False)
        fresh = committed.copy()
        fresh.loc[0, "reprojection_rms_px"] = 999.0

        unguarded = compare_experiment_csv_if_present(
            fresh, committed_path, key_columns=EXP1_KEY_COLUMNS, rtol=CHECK_RTOL
        )
        assert unguarded is not None and not unguarded.passed

        excluded = compare_experiment_csv_if_present(
            fresh,
            committed_path,
            key_columns=EXP1_KEY_COLUMNS,
            rtol=CHECK_RTOL,
            exclude_columns=("reprojection_rms_px",),
        )
        assert excluded is not None and excluded.passed

    def test_compare_experiment_csv_itself_still_raises_on_a_missing_baseline(
        self, tmp_path
    ):
        """The totality contract at `_io.py:348-357` deliberately propagates I/O
        errors (D-13). Ruling A4 puts the guard in the CALLER; this test exists so
        a future "helpful" fix inside `compare_experiment_csv` fails loudly.
        """
        with pytest.raises(FileNotFoundError):
            compare_experiment_csv(
                _exp1_frame(),
                tmp_path / "absent.csv",
                key_columns=EXP1_KEY_COLUMNS,
                rtol=CHECK_RTOL,
            )


class TestBaselineDirE3Plumbing:
    """Phase 26 / DRIVER-03: E3's `--check` argument plumbing (D-10, D-12).

    Deliberately drives the parser and the resolution helper only. `_run_check`
    recomputes a Newton sweep over the rig's working volume -- it is an
    experiment, not a unit test, and this suite never runs one. E3 has no
    dedicated CLI test file, so these live beside the helper tests to keep
    `-k baseline` a single selector.
    """

    def test_e3_parser_exposes_baseline_dir_and_all_five_shared_flags(self):
        from experiments.e3_derived_quantities import build_arg_parser

        parser = build_arg_parser()
        options = {o for a in parser._actions for o in a.option_strings}
        assert {"--seed", "--out", "--force", "--smoke", "--check"} <= options
        assert "--baseline-dir" in options

    def test_e3_check_resolves_baselines_under_baseline_dir(self, tmp_path):
        from experiments.e3_derived_quantities import build_arg_parser

        archive = tmp_path / "pre_rerun_baseline" / "results"
        out = tmp_path / "fresh"
        args = build_arg_parser().parse_args(
            ["--check", "--baseline-dir", str(archive), "--out", str(out)]
        )
        assert args.check is True
        assert resolve_baseline_dir(args.baseline_dir, out) == archive
        # A --check run writes nowhere, and resolution creates nothing.
        assert not archive.exists()

    def test_e3_check_without_the_flag_resolves_under_out(self, tmp_path):
        from experiments.e3_derived_quantities import build_arg_parser

        out = tmp_path / "fresh"
        args = build_arg_parser().parse_args(["--check", "--out", str(out)])
        assert args.baseline_dir is None
        assert resolve_baseline_dir(args.baseline_dir, out) == out

    def test_e3_rejects_baseline_dir_with_force(self, capsys):
        from experiments.e3_derived_quantities import (
            _validate_e3_args,
            build_arg_parser,
        )

        parser = build_arg_parser()
        args = parser.parse_args(["--check", "--force", "--baseline-dir", "x"])
        with pytest.raises(SystemExit):
            _validate_e3_args(parser, args)
        err = capsys.readouterr().err
        assert "--baseline-dir" in err
        assert "--force" in err

    def test_e3_rejects_baseline_dir_without_check(self, capsys):
        from experiments.e3_derived_quantities import (
            _validate_e3_args,
            build_arg_parser,
        )

        parser = build_arg_parser()
        args = parser.parse_args(["--baseline-dir", "x"])
        with pytest.raises(SystemExit):
            _validate_e3_args(parser, args)
        err = capsys.readouterr().err
        assert "--baseline-dir" in err
        assert "--check" in err

    def test_e3_main_exits_nonzero_for_baseline_dir_with_force(self):
        from experiments.e3_derived_quantities import main

        with pytest.raises(SystemExit) as excinfo:
            main(["--check", "--force", "--baseline-dir", "x"])
        assert excinfo.value.code != 0

    def test_e3_run_check_accepts_baseline_dir_keyword(self):
        """Signature-level assertion: `_run_check` gained a keyword-only
        `baseline_dir` defaulting to None, so existing callers keep working.
        """
        import inspect

        from experiments.e3_derived_quantities import _run_check

        sig = inspect.signature(_run_check)
        param = sig.parameters["baseline_dir"]
        assert param.kind is inspect.Parameter.KEYWORD_ONLY
        assert param.default is None
