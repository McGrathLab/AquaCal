"""Unit tests for aquacal.io.benchmark (BENCH-01..04)."""

from __future__ import annotations

import dataclasses
import json
import subprocess
import sys
import tracemalloc

import numpy as np
import pytest

from aquacal.calibration._observability import SolverDiagnostics
from aquacal.calibration.interface_estimation import optimize_interface
from aquacal.config.schema import (
    BoardConfig,
    BoardPose,
    CameraExtrinsics,
    CameraIntrinsics,
)
from aquacal.core.board import BoardGeometry
from aquacal.io.benchmark import (
    assemble_benchmark_record,
    capture_environment,
    capture_peak_memory,
    write_benchmark_json,
)

sys.path.insert(0, ".")
from tests.synthetic.ground_truth import generate_synthetic_detections


class TestCaptureEnvironment:
    def test_returns_dict_with_nonempty_version(self):
        env = capture_environment()
        assert isinstance(env, dict)
        assert isinstance(env["aquacal_version"], str)
        assert env["aquacal_version"] != ""

    def test_always_returns_core_string_fields(self):
        env = capture_environment()
        for key in (
            "python_version",
            "numpy_version",
            "scipy_version",
            "opencv_version",
            "os",
            "cpu_model",
        ):
            assert isinstance(env[key], str)
            assert env[key] != ""

    def test_psutil_available_populates_cpu_and_ram(self):
        env = capture_environment()
        pytest.importorskip("psutil")
        assert isinstance(env["cpu_count_logical"], int)
        assert env["cpu_count_logical"] > 0
        assert isinstance(env["ram_total_bytes"], int)
        assert env["ram_total_bytes"] > 0

    def test_psutil_missing_degrades_gracefully(self, monkeypatch):
        monkeypatch.setitem(sys.modules, "psutil", None)
        env = capture_environment()
        assert env["cpu_count_logical"] is None
        assert env["ram_total_bytes"] is None
        # Never raises, and unrelated fields remain populated.
        assert env["aquacal_version"] != ""

    def test_inside_git_checkout_records_sha(self):
        env = capture_environment()
        assert env["git_sha_source"] == "git_rev_parse"
        assert isinstance(env["git_sha"], str)
        assert len(env["git_sha"]) == 40
        int(env["git_sha"], 16)  # hex string

    def test_git_subprocess_failure_degrades_gracefully(self, monkeypatch):
        def _raise(*args, **kwargs):
            raise FileNotFoundError("git not found")

        monkeypatch.setattr(subprocess, "run", _raise)
        env = capture_environment()
        assert env["git_sha"] is None
        assert env["git_sha_source"] == "unavailable"
        # Never raises, and unrelated fields remain populated.
        assert env["aquacal_version"] != ""

    def test_git_subprocess_timeout_degrades_gracefully(self, monkeypatch):
        def _raise(*args, **kwargs):
            raise subprocess.TimeoutExpired(cmd=["git"], timeout=5)

        monkeypatch.setattr(subprocess, "run", _raise)
        env = capture_environment()
        assert env["git_sha"] is None
        assert env["git_sha_source"] == "unavailable"

    def test_never_raises_with_no_git_root_found(self, tmp_path):
        # A directory tree with no .git anywhere -- simulates a pip install
        # run outside any git checkout.
        env = capture_environment(repo_hint_path=tmp_path)
        assert env["git_sha"] is None
        assert env["git_sha_source"] == "unavailable"
        assert env["aquacal_version"] != ""


class TestCapturePeakMemory:
    def test_returns_dict_with_exactly_two_keys(self):
        reading = capture_peak_memory()
        assert set(reading.keys()) == {"peak_bytes", "mode"}

    def test_windows_dev_machine_reports_peak_wset(self):
        reading = capture_peak_memory()
        if sys.platform.startswith("win"):
            assert reading["mode"] == "psutil_peak_wset"
            assert reading["peak_bytes"] > 0

    def test_linux_mocked_reads_proc_status_vmhwm(self, monkeypatch, tmp_path):
        import platform

        monkeypatch.setattr(platform, "system", lambda: "Linux")

        proc_status = tmp_path / "status"
        proc_status.write_text("VmHWM:    123456 kB\nOther: 1\n")

        real_open = open

        def _fake_open(path, *args, **kwargs):
            if str(path).startswith("/proc/") and str(path).endswith("/status"):
                return real_open(proc_status, *args, **kwargs)
            return real_open(path, *args, **kwargs)

        monkeypatch.setattr("aquacal.io.benchmark.open", _fake_open, raising=False)

        reading = capture_peak_memory()
        assert reading == {"peak_bytes": 123456 * 1024, "mode": "proc_status_vmhwm"}

    def test_darwin_mocked_with_psutil_uses_rss_sampled(self, monkeypatch):
        import platform

        monkeypatch.setattr(platform, "system", lambda: "Darwin")

        pytest.importorskip("psutil")
        reading = capture_peak_memory()
        assert reading["mode"] == "psutil_rss_sampled"
        assert reading["peak_bytes"] > 0

    def test_psutil_unavailable_falls_back_to_tracemalloc(self, monkeypatch):
        import platform

        monkeypatch.setattr(platform, "system", lambda: "Darwin")
        monkeypatch.setitem(sys.modules, "psutil", None)

        reading = capture_peak_memory()
        assert reading["mode"] == "tracemalloc_python_heap"
        assert reading["peak_bytes"] >= 0

    def test_tracemalloc_fallback_does_not_restart_existing_trace(self, monkeypatch):
        import platform

        monkeypatch.setattr(platform, "system", lambda: "Darwin")
        monkeypatch.setitem(sys.modules, "psutil", None)

        was_tracing = tracemalloc.is_tracing()
        if not was_tracing:
            tracemalloc.start()
        try:
            reading = capture_peak_memory()
            assert reading["mode"] == "tracemalloc_python_heap"
            assert tracemalloc.is_tracing()
        finally:
            if not was_tracing:
                tracemalloc.stop()

    def test_repeated_calls_never_raise_and_are_monotonic(self):
        readings = [capture_peak_memory() for _ in range(3)]
        for reading in readings:
            assert reading["mode"] != "unavailable"
        for prev, cur in zip(readings, readings[1:]):
            assert cur["peak_bytes"] >= prev["peak_bytes"]

    def test_no_background_thread_spawned(self):
        import threading

        before = threading.active_count()
        capture_peak_memory()
        capture_peak_memory()
        after = threading.active_count()
        assert after == before

    def test_never_raises_on_unexpected_error(self, monkeypatch):
        import platform

        def _raise():
            raise RuntimeError("boom")

        monkeypatch.setattr(platform, "system", _raise)
        reading = capture_peak_memory()
        assert reading == {"peak_bytes": None, "mode": "unavailable"}


# --- Fixtures for real, NumPy-typed SolverDiagnostics (Task 2) ---
#
# Mirrors tests/unit/test_interface_estimation.py's fixture pattern: a tiny
# 3-camera synthetic problem, real enough that optimize_interface's
# `least_squares` call and `capture_solver_diagnostics` produce genuine
# solver-reported values (nfev, cost, optimality, ...), not hand-built
# Python floats. This is the "real path" the round-trip test below exercises
# (a hand-built dict of Python floats would not catch a defensive-cast bug).


@pytest.fixture
def _bench_board_config() -> BoardConfig:
    return BoardConfig(
        squares_x=6,
        squares_y=5,
        square_size=0.04,
        marker_size=0.03,
        dictionary="DICT_4X4_50",
    )


@pytest.fixture
def _bench_board(_bench_board_config) -> BoardGeometry:
    return BoardGeometry(_bench_board_config)


@pytest.fixture
def _bench_intrinsics() -> dict[str, CameraIntrinsics]:
    K = np.array([[500, 0, 320], [0, 500, 240], [0, 0, 1]], dtype=np.float64)
    dist = np.zeros(5, dtype=np.float64)
    return {
        cam: CameraIntrinsics(
            K=K.copy(), dist_coeffs=dist.copy(), image_size=(640, 480)
        )
        for cam in ("cam0", "cam1", "cam2")
    }


@pytest.fixture
def _bench_extrinsics() -> dict[str, CameraExtrinsics]:
    return {
        "cam0": CameraExtrinsics(
            R=np.eye(3, dtype=np.float64), t=np.zeros(3, dtype=np.float64)
        ),
        "cam1": CameraExtrinsics(
            R=np.eye(3, dtype=np.float64),
            t=np.array([0.1, 0.0, 0.0], dtype=np.float64),
        ),
        "cam2": CameraExtrinsics(
            R=np.eye(3, dtype=np.float64),
            t=np.array([0.0, 0.1, 0.0], dtype=np.float64),
        ),
    }


@pytest.fixture
def _bench_distances() -> dict[str, float]:
    return {"cam0": 0.15, "cam1": 0.15, "cam2": 0.15}


@pytest.fixture
def _bench_board_poses(_bench_board) -> list[BoardPose]:
    poses = []
    for i in range(3):
        x_offset = 0.05 * (i - 1)
        y_offset = 0.02 * i
        poses.append(
            BoardPose(
                frame_idx=i,
                rvec=np.array([0.1 * (i % 3), 0.1 * (i % 2), 0.0], dtype=np.float64),
                tvec=np.array([x_offset, y_offset, 0.4], dtype=np.float64),
            )
        )
    return poses


@pytest.fixture
def real_solver_diagnostics(
    _bench_board,
    _bench_intrinsics,
    _bench_extrinsics,
    _bench_distances,
    _bench_board_poses,
) -> SolverDiagnostics:
    """A `SolverDiagnostics` populated from a real `optimize_interface()` call."""
    np.random.seed(42)
    detections = generate_synthetic_detections(
        _bench_intrinsics,
        _bench_extrinsics,
        _bench_distances,
        _bench_board,
        _bench_board_poses,
        noise_std=0.5,
        min_corners=4,
    )
    diag = SolverDiagnostics()
    optimize_interface(
        detections=detections,
        intrinsics=_bench_intrinsics,
        initial_extrinsics=_bench_extrinsics,
        board=_bench_board,
        reference_camera="cam0",
        verbose=0,
        use_sparse_jacobian=True,
        diagnostics_out=diag,
    )
    return diag


class TestAssembleBenchmarkRecord:
    def test_json_round_trip_with_real_numpy_typed_diagnostics(
        self, real_solver_diagnostics
    ):
        """The full round-trip must succeed with a REAL, solver-produced
        SolverDiagnostics (not a hand-built dict of plain Python floats) --
        this is the test that would catch a numpy-scalar-leakage regression.
        """
        record = assemble_benchmark_record(
            problem_shape={"n_cameras": np.int64(3), "n_frames_calibration": 3},
            timings={"stage3": 1.23},
            diagnostics={"stage3": real_solver_diagnostics},
            solver_config={"robust_loss": "huber", "loss_scale": 1.0},
            accuracy={"reprojection_rms": np.float64(0.42)},
            environment=capture_environment(),
        )
        # Must not raise TypeError from a leaked numpy scalar.
        dumped = json.dumps(record)
        reloaded = json.loads(dumped)
        assert reloaded["schema_version"] == 1
        assert "stage3" in reloaded["stages"]

    def test_schema_version_defaults_to_one(self, real_solver_diagnostics):
        record = assemble_benchmark_record(
            problem_shape={},
            timings={},
            diagnostics={"stage3": real_solver_diagnostics},
            solver_config={},
            accuracy={},
            environment={},
        )
        assert record["schema_version"] == 1

    def test_skipped_stage_absent_from_stages(self, real_solver_diagnostics):
        """D-14: a stage not present in `diagnostics` is absent from `stages`,
        never present as a null/empty block."""
        record = assemble_benchmark_record(
            problem_shape={},
            timings={"stage3": 1.0},
            diagnostics={"stage3": real_solver_diagnostics},
            solver_config={},
            accuracy={},
            environment={},
        )
        assert "stage3_intrinsic_pass" not in record["stages"]
        assert set(record["stages"].keys()) == {"stage3"}

    def test_every_solver_diagnostics_field_appears_in_stage_dict(
        self, real_solver_diagnostics
    ):
        record = assemble_benchmark_record(
            problem_shape={},
            timings={},
            diagnostics={"stage3": real_solver_diagnostics},
            solver_config={},
            accuracy={},
            environment={},
        )
        stage3 = record["stages"]["stage3"]
        for field in dataclasses.fields(SolverDiagnostics):
            assert field.name in stage3

    def test_fd_reduction_derived_when_n_params_and_n_groups_present(
        self, real_solver_diagnostics
    ):
        assert real_solver_diagnostics.n_params is not None
        assert real_solver_diagnostics.n_groups is not None
        record = assemble_benchmark_record(
            problem_shape={},
            timings={},
            diagnostics={"stage3": real_solver_diagnostics},
            solver_config={},
            accuracy={},
            environment={},
        )
        expected = real_solver_diagnostics.n_params / real_solver_diagnostics.n_groups
        assert record["stages"]["stage3"]["fd_reduction"] == expected

    def test_no_memory_key_anywhere_when_memory_readings_none(
        self, real_solver_diagnostics
    ):
        record = assemble_benchmark_record(
            problem_shape={},
            timings={},
            diagnostics={"stage3": real_solver_diagnostics},
            solver_config={},
            accuracy={},
            environment={},
            memory_readings=None,
        )
        assert "memory" not in record
        assert all("memory" not in v for v in record["stages"].values())

    def test_memory_attribution_exact_field_names_and_deltas(
        self, real_solver_diagnostics
    ):
        memory_readings = {
            "_baseline": {"peak_bytes": 1000, "mode": "psutil_peak_wset"},
            "stage3": {"peak_bytes": 1500, "mode": "psutil_peak_wset"},
            "validation": {"peak_bytes": 1800, "mode": "psutil_peak_wset"},
        }
        record = assemble_benchmark_record(
            problem_shape={},
            timings={"stage3": 1.0, "validation": 0.5},
            diagnostics={"stage3": real_solver_diagnostics},
            solver_config={},
            accuracy={},
            environment={},
            memory_readings=memory_readings,
        )

        stage3_memory = record["stages"]["stage3"]["memory"]
        assert set(stage3_memory.keys()) == {
            "cumulative_peak_bytes_as_of_stage_end",
            "delta_bytes_since_previous_boundary",
            "mode",
        }
        assert "peak_bytes" not in stage3_memory
        assert stage3_memory["delta_bytes_since_previous_boundary"] == 500

        validation_memory = record["stages"]["validation"]["memory"]
        assert validation_memory["delta_bytes_since_previous_boundary"] == 300
        assert (
            record["stages"]["validation"]["solver_diagnostics_reason"]
            == "no in-scope least_squares solver diagnostics were captured for this stage"
        )

        assert record["memory"]["whole_run_peak_bytes"] == 1800
        assert record["memory"]["mode"] == "psutil_peak_wset"

        assert "_baseline" not in record["stages"]

    def test_stage_present_in_diagnostics_but_absent_from_memory_readings_has_no_memory_key(
        self, real_solver_diagnostics
    ):
        memory_readings = {
            "_baseline": {"peak_bytes": 1000, "mode": "psutil_peak_wset"},
            "validation": {"peak_bytes": 1800, "mode": "psutil_peak_wset"},
        }
        record = assemble_benchmark_record(
            problem_shape={},
            timings={"stage3": 1.0, "validation": 0.5},
            diagnostics={"stage3": real_solver_diagnostics},
            solver_config={},
            accuracy={},
            environment={},
            memory_readings=memory_readings,
        )
        assert "memory" not in record["stages"]["stage3"]

    def test_stage3_interface_optimization_seconds_resolves_from_timings(
        self, real_solver_diagnostics
    ):
        """Regression: the diagnostics key and the timings key must agree so
        `seconds` is populated. Before the fix the pipeline recorded diagnostics
        under `stage3` while timing lived under `stage3_interface_optimization`,
        leaving `stages.stage3.seconds` null in every real run."""
        record = assemble_benchmark_record(
            problem_shape={},
            timings={"stage3_interface_optimization": 7.0},
            diagnostics={"stage3_interface_optimization": real_solver_diagnostics},
            solver_config={},
            accuracy={},
            environment={},
        )
        assert record["stages"]["stage3_interface_optimization"]["seconds"] == 7.0

    def test_aux_aggregate_memory_boundary_is_not_falsely_labelled_no_solver(
        self, real_solver_diagnostics
    ):
        """CR-01 regression: the single `auxiliary_registration` memory boundary
        spans per-camera `auxiliary_registration_<cam>` diagnostics stages. It
        must NOT synthesize a block claiming no least_squares ran — that stage
        genuinely calls the solver once per auxiliary camera."""
        memory_readings = {
            "_baseline": {"peak_bytes": 1000, "mode": "psutil_peak_wset"},
            "auxiliary_registration": {"peak_bytes": 2200, "mode": "psutil_peak_wset"},
        }
        record = assemble_benchmark_record(
            problem_shape={},
            timings={"auxiliary_registration": 3.0},
            diagnostics={"auxiliary_registration_cam5": real_solver_diagnostics},
            solver_config={},
            accuracy={},
            environment={},
            memory_readings=memory_readings,
        )
        aux = record["stages"]["auxiliary_registration"]
        reason = aux["solver_diagnostics_reason"]
        assert "no in-scope least_squares" not in reason
        assert "aggregate boundary" in reason
        assert "auxiliary_registration_cam5" in reason
        # The aggregate boundary carries the aggregate wall time...
        assert aux["seconds"] == 3.0
        # ...and the per-camera diagnostics stage still exists with real solver data.
        assert "auxiliary_registration_cam5" in record["stages"]
        assert record["stages"]["auxiliary_registration_cam5"]["nfev"] is not None

    def test_null_seconds_carry_a_reason_never_a_silent_null(
        self, real_solver_diagnostics
    ):
        """D-15: a stage whose wall time cannot be resolved gets an explicit
        `seconds_reason`, not a bare null. Covers the folded `stage3_rerun` and
        the per-camera `auxiliary_registration_<cam>` cases."""
        record = assemble_benchmark_record(
            problem_shape={},
            timings={"stage3_interface_optimization": 7.0},
            diagnostics={
                "stage3_rerun": real_solver_diagnostics,
                "auxiliary_registration_cam5": real_solver_diagnostics,
            },
            solver_config={},
            accuracy={},
            environment={},
        )
        rerun = record["stages"]["stage3_rerun"]
        assert rerun["seconds"] is None
        assert "folded into stage3_interface_optimization" in rerun["seconds_reason"]
        aux = record["stages"]["auxiliary_registration_cam5"]
        assert aux["seconds"] is None
        assert "per-camera wall time" in aux["seconds_reason"]


class TestWriteBenchmarkJson:
    def test_writes_json_that_round_trips(self, tmp_path, real_solver_diagnostics):
        record = assemble_benchmark_record(
            problem_shape={"n_cameras": 3},
            timings={"stage3": 1.0},
            diagnostics={"stage3": real_solver_diagnostics},
            solver_config={},
            accuracy={},
            environment=capture_environment(),
        )
        path = tmp_path / "benchmark.json"
        write_benchmark_json(record, path)
        assert path.exists()
        with open(path) as f:
            reloaded = json.load(f)
        assert reloaded["schema_version"] == 1
        assert reloaded["problem_shape"]["n_cameras"] == 3

    def test_warns_on_overwrite(self, tmp_path, real_solver_diagnostics, caplog):
        record = assemble_benchmark_record(
            problem_shape={},
            timings={},
            diagnostics={"stage3": real_solver_diagnostics},
            solver_config={},
            accuracy={},
            environment={},
        )
        path = tmp_path / "benchmark.json"
        write_benchmark_json(record, path)
        with caplog.at_level("WARNING"):
            write_benchmark_json(record, path)
        assert any(
            "Overwriting existing internals artifact" in message
            for message in caplog.messages
        )
