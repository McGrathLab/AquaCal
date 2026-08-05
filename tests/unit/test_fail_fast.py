"""Unit tests for D-19.4-11 fail-fast wiring in E4 and E6 (plan 19.4-07).

Every test here is deliberately cheap: failures are forced via monkeypatch
(never a real production-scale calibration), and the real subprocess hop is
never exercised -- `_run_full`'s own `run_cell_subprocess` call is faked so
these tests run in well under a second, consistent with the plan's own
constraint that this plan MUST NOT run E4 or E6 at production scale.
"""

from __future__ import annotations

import pandas as pd
import pytest

import experiments.e4_benchmark_grid as e4
import experiments.e6_generalization_sweep as e6

# ---------------------------------------------------------------------------
# E4 (Task 1): two-layer fail-fast -- child re-raise + outer cell-loop stop
# ---------------------------------------------------------------------------


def test_e4_help_lists_no_fail_fast(capsys):
    parser = e4.build_arg_parser()
    with pytest.raises(SystemExit):
        parser.parse_args(["--help"])
    captured = capsys.readouterr()
    assert "--no-fail-fast" in captured.out


def test_e4_run_grid_cell_default_swallows_exception_into_failed_row(
    tmp_path, monkeypatch
):
    """Default `fail_fast=False` preserves the original never-raises contract
    (this is also what the pre-existing direct-call tests in
    `test_experiments_e4.py` depend on)."""

    def _boom(*a, **k):
        raise ValueError("synthetic failure for test")

    monkeypatch.setattr(e4, "build_grid_scenario", _boom)
    row = e4.run_grid_cell(16, 200, seed=1, out_dir=tmp_path, force=True)
    assert row["status"] == "failed"
    assert "ValueError" in row["status_reason"]
    assert "synthetic failure for test" in row["status_reason"]


def test_e4_run_grid_cell_fail_fast_reraises(tmp_path, monkeypatch):
    def _boom(*a, **k):
        raise ValueError("synthetic failure for test")

    monkeypatch.setattr(e4, "build_grid_scenario", _boom)
    with pytest.raises(ValueError, match="synthetic failure for test"):
        e4.run_grid_cell(16, 200, seed=1, out_dir=tmp_path, force=True, fail_fast=True)


def test_e4_cell_cli_fail_fast_default_exits_nonzero_with_message(
    tmp_path, monkeypatch, capsys
):
    """`main(["--cell", ...])` is the child-process entry point
    `run_cell_subprocess` spawns; forcing an exception here proves the
    default (fail-fast ON) child path exits non-zero with a message naming
    the cell key and the exception type."""

    def _boom(*a, **k):
        raise ValueError("synthetic failure for test")

    monkeypatch.setattr(e4, "build_grid_scenario", _boom)
    exit_code = e4.main(
        ["--cell", "16x200", "--out", str(tmp_path), "--seed", "1", "--force"]
    )
    assert exit_code != 0
    err = capsys.readouterr().err
    assert "cameras_16_frames_200" in err
    assert "ValueError" in err
    assert "synthetic failure for test" in err


def test_e4_cell_cli_no_fail_fast_composes_without_error(tmp_path, monkeypatch):
    """`--no-fail-fast` composes with `--cell`/`--out`/`--force` without
    raising or crashing -- the single-cell exit code for a failed cell was
    already non-zero before this plan (D-33's own status mapping), so
    `--no-fail-fast` at cell granularity only needs to thread cleanly, not
    change that pre-existing value."""

    def _boom(*a, **k):
        raise ValueError("synthetic failure for test")

    monkeypatch.setattr(e4, "build_grid_scenario", _boom)
    exit_code = e4.main(
        [
            "--cell",
            "16x200",
            "--out",
            str(tmp_path),
            "--seed",
            "1",
            "--force",
            "--no-fail-fast",
        ]
    )
    assert exit_code == 1


def test_e4_no_fail_fast_composes_with_smoke_and_out(tmp_path):
    parser = e4.build_arg_parser()
    args = parser.parse_args(["--smoke", "--out", str(tmp_path), "--no-fail-fast"])
    e4._validate_e4_args(parser, args)
    assert args.no_fail_fast is True


def _fake_run_cell_subprocess_factory(calls, fail_at_index):
    def _fake(
        n_cameras, n_frames, seed, out_dir, force, timeout=None, no_fail_fast=False
    ):
        calls.append((n_cameras, n_frames, no_fail_fast))
        cell_key = f"cameras_{n_cameras}_frames_{n_frames}"
        if len(calls) == fail_at_index:
            return {
                "cell_key": cell_key,
                "n_cameras": n_cameras,
                "n_frames": n_frames,
                "status": "failed",
                "status_reason": (
                    "child exit_code=1: ValueError: depth_range[0]=0.5 is "
                    "below the derived clearance floor 1.1762 m"
                ),
                "exit_code": 1,
            }
        return {
            "cell_key": cell_key,
            "n_cameras": n_cameras,
            "n_frames": n_frames,
            "status": "ok",
            "status_reason": "",
            "exit_code": 0,
        }

    return _fake


def test_e4_run_full_default_stops_after_first_failing_cell(tmp_path, monkeypatch):
    calls: list[tuple[int, int, bool]] = []
    monkeypatch.setattr(
        e4, "run_cell_subprocess", _fake_run_cell_subprocess_factory(calls, 2)
    )

    parser = e4.build_arg_parser()
    args = parser.parse_args(["--out", str(tmp_path), "--seed", "1"])
    exit_code = e4._run_full(args)

    assert exit_code != 0
    # Exactly two invocations: the first (ok) plus the failing second cell --
    # no cell after the failure was invoked.
    assert len(calls) == 2
    assert all(no_fail_fast is False for (_, _, no_fail_fast) in calls)


def test_e4_run_full_prints_abort_message_with_cell_key_and_clearance_numbers(
    tmp_path, monkeypatch, capsys
):
    calls: list[tuple[int, int, bool]] = []
    monkeypatch.setattr(
        e4, "run_cell_subprocess", _fake_run_cell_subprocess_factory(calls, 1)
    )

    parser = e4.build_arg_parser()
    args = parser.parse_args(["--out", str(tmp_path), "--seed", "1"])
    exit_code = e4._run_full(args)

    assert exit_code != 0
    err = capsys.readouterr().err
    # First declared cell is (8, 50) -- CAMERA_COUNTS x FRAME_COUNTS, nested.
    assert "cameras_8_frames_50" in err
    assert "ValueError" in err
    assert "depth_range[0]=0.5" in err
    assert "clearance floor 1.1762" in err


def test_e4_run_full_no_fail_fast_runs_every_cell_and_exits_zero(tmp_path, monkeypatch):
    calls: list[tuple[int, int, bool]] = []
    monkeypatch.setattr(
        e4, "run_cell_subprocess", _fake_run_cell_subprocess_factory(calls, 2)
    )
    monkeypatch.setattr(
        e4, "build_grid_dataframe", lambda out_dir, statuses, path: pd.DataFrame()
    )
    monkeypatch.setattr(e4, "write_experiment_csv", lambda *a, **k: None)
    monkeypatch.setattr(e4, "write_grid_latex", lambda *a, **k: None)

    parser = e4.build_arg_parser()
    args = parser.parse_args(["--out", str(tmp_path), "--seed", "1", "--no-fail-fast"])
    exit_code = e4._run_full(args)

    assert exit_code == 0
    assert len(calls) == len(e4.DECLARED_CELLS)
    assert all(no_fail_fast is True for (_, _, no_fail_fast) in calls)


# ---------------------------------------------------------------------------
# E6 (Task 2): single-layer fail-fast in run_sweep's config loop
# ---------------------------------------------------------------------------


def test_e6_help_lists_no_fail_fast(capsys):
    parser = e6.build_arg_parser()
    with pytest.raises(SystemExit):
        parser.parse_args(["--help"])
    captured = capsys.readouterr()
    assert "--no-fail-fast" in captured.out


def test_e6_run_configuration_default_still_swallows_into_failed_row(
    tmp_path, monkeypatch
):
    """Unchanged existing contract: `run_configuration` never raises by
    default (pinned so this plan cannot regress `test_experiments_e6.py`'s
    own `_fail_fast` monkeypatch helpers, which depend on this)."""

    def _boom(**kwargs):
        raise RuntimeError("synthetic failure for test")

    monkeypatch.setattr(e6, "build_grid_scenario", _boom)
    configs = e6.build_axis_configurations()
    outcome = e6.run_configuration(configs[0], seed=42, n_frames=10, out_dir=tmp_path)
    assert outcome["status"] == "failed"
    assert "synthetic failure for test" in outcome["status_reason"]


def test_e6_run_sweep_default_stops_at_first_failing_configuration(
    tmp_path, monkeypatch
):
    calls: list[str] = []

    def _tracking_run_configuration(config, *a, **k):
        calls.append(config["config_key"])
        if len(calls) == 2:
            return {
                "status": "failed",
                "status_reason": "RuntimeError: synthetic failure for test",
                "metrics": None,
                "degenerate_observations_at_solution": None,
            }
        return {
            "status": "ok",
            "status_reason": "",
            "metrics": None,
            "degenerate_observations_at_solution": 0,
        }

    monkeypatch.setattr(e6, "run_configuration", _tracking_run_configuration)

    configs = e6.build_axis_configurations()
    # Distinct config_keys only -- run_sweep's cache means a repeated key
    # (the three baseline rows) would not add a new call.
    seen_keys = set()
    distinct_configs = []
    for c in configs:
        if c["config_key"] not in seen_keys:
            seen_keys.add(c["config_key"])
            distinct_configs.append(c)
    assert len(distinct_configs) >= 3

    with pytest.raises(e6.FailFastAbort) as excinfo:
        e6.run_sweep(
            distinct_configs,
            seed=42,
            n_frames=10,
            out_dir=tmp_path,
            fail_fast=True,
        )

    assert len(calls) == 2
    assert excinfo.value.config_key == calls[1]
    assert "synthetic failure for test" in excinfo.value.status_reason


def test_e6_run_sweep_no_fail_fast_continues_and_returns_all_rows(
    tmp_path, monkeypatch
):
    calls: list[str] = []

    def _tracking_run_configuration(config, *a, **k):
        calls.append(config["config_key"])
        status = "failed" if len(calls) == 2 else "ok"
        return {
            "status": status,
            "status_reason": "boom" if status == "failed" else "",
            "metrics": None,
            "degenerate_observations_at_solution": 0 if status == "ok" else None,
        }

    monkeypatch.setattr(e6, "run_configuration", _tracking_run_configuration)

    configs = e6.build_axis_configurations()
    seen_keys = set()
    distinct_configs = []
    for c in configs:
        if c["config_key"] not in seen_keys:
            seen_keys.add(c["config_key"])
            distinct_configs.append(c)

    df = e6.run_sweep(
        distinct_configs,
        seed=42,
        n_frames=10,
        out_dir=tmp_path,
        fail_fast=False,
    )

    assert len(calls) == len(distinct_configs)
    assert len(df) == len(distinct_configs)
    assert (df["status"] == "failed").sum() == 1


def test_e6_run_sweep_cached_failure_triggers_abort_in_fail_fast_mode(
    tmp_path, monkeypatch
):
    """A resumed run must not silently pass over a cached `status="failed"`
    checkpoint -- E6 treats a cached failure as a failure."""
    configs = e6.build_axis_configurations()
    config = configs[0]

    def _cached_failed(config, *a, **k):
        return {
            "status": "failed",
            "status_reason": "RuntimeError: cached failure from a prior run",
            "metrics": None,
            "degenerate_observations_at_solution": None,
        }

    monkeypatch.setattr(e6, "run_configuration", _cached_failed)

    with pytest.raises(e6.FailFastAbort) as excinfo:
        e6.run_sweep([config], seed=42, n_frames=10, out_dir=tmp_path, fail_fast=True)

    assert excinfo.value.config_key == config["config_key"]
    assert "cached failure from a prior run" in excinfo.value.status_reason


def test_e6_run_full_prints_abort_message_and_returns_nonzero(
    tmp_path, monkeypatch, capsys
):
    def _boom_run_sweep(configs, seed, n_frames, out_dir, **kwargs):
        assert kwargs.get("fail_fast") is True
        raise e6.FailFastAbort(
            "index_1.36",
            "RuntimeError: depth_range[0]=0.5 is below the derived clearance "
            "floor 1.1762 m",
        )

    monkeypatch.setattr(e6, "run_sweep", _boom_run_sweep)
    monkeypatch.setattr(e6, "capture_environment", lambda: {})

    parser = e6.build_arg_parser()
    args = parser.parse_args(["--out", str(tmp_path), "--seed", "1"])
    exit_code = e6._run_full(args)

    assert exit_code != 0
    err = capsys.readouterr().err
    assert "index_1.36" in err
    assert "clearance floor 1.1762" in err


def test_e6_run_full_no_fail_fast_forwards_flag_and_exits_zero(tmp_path, monkeypatch):
    calls = {}

    def _fake_run_sweep(configs, seed, n_frames, out_dir, **kwargs):
        calls["fail_fast"] = kwargs.get("fail_fast")
        return pd.DataFrame()

    monkeypatch.setattr(e6, "run_sweep", _fake_run_sweep)
    monkeypatch.setattr(e6, "capture_environment", lambda: {})
    monkeypatch.setattr(e6, "write_experiment_csv", lambda *a, **k: None)

    parser = e6.build_arg_parser()
    args = parser.parse_args(["--out", str(tmp_path), "--seed", "1", "--no-fail-fast"])
    exit_code = e6._run_full(args)

    assert exit_code == 0
    assert calls["fail_fast"] is False


def test_e6_smoke_is_unaffected_by_fail_fast_wiring():
    """`--smoke` (`_run_smoke_configs`) never forwards `fail_fast=True` to
    `run_sweep` -- fail-fast wiring must not change smoke behaviour. Checked
    at the source level (never instrumenting `_run_smoke_configs`'s own
    resume-path probe, which writes/reads real checkpoint files and is
    already covered by `test_experiments_e6.py`)."""
    import inspect

    source = inspect.getsource(e6._run_smoke_configs)
    assert "fail_fast" not in source
