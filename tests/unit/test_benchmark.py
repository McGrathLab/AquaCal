"""Unit tests for aquacal.io.benchmark (BENCH-02, BENCH-04 capture primitives)."""

from __future__ import annotations

import subprocess
import sys
import tracemalloc

import pytest
from aquacal.io.benchmark import capture_environment, capture_peak_memory


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
