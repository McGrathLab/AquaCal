"""Unit tests for experiments/_env_lock.py (plan 27-05, D-13, TDD).

Like `test_run_manifest.py`, these drive the REAL interpreter and the REAL
`pip freeze` rather than mocking `subprocess` globally: D-13's lockfile exists
to describe the environment the suite actually runs in, and a test that mocks
the freeze proves nothing about whether the freeze can be read on that box.

Only the "a failed freeze still writes a file and still exits 0" contract is
exercised with a monkeypatch, and it patches the one named helper under test.

Nothing here writes into `experiments/results/` -- every write goes to
`tmp_path`.
"""

from __future__ import annotations

import re
import sys
from datetime import datetime
from pathlib import Path

import pytest
from experiments._env_lock import (
    ENVIRONMENT_LOCK_FILENAME,
    build_arg_parser,
    build_environment_lock_text,
    main,
    write_environment_lock,
)

_UTC_PATTERN = re.compile(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z")


class TestBuildEnvironmentLockText:
    def test_header_names_the_running_interpreter(self):
        text = build_environment_lock_text()
        assert sys.executable in text

    def test_header_names_the_python_version_and_full_version_string(self):
        text = build_environment_lock_text()
        assert f"{sys.version_info.major}.{sys.version_info.minor}" in text
        # `sys.version` carries the compiler, which the bare version does not.
        assert sys.version.splitlines()[0] in text

    def test_header_carries_a_utc_timestamp_in_the_manifest_format(self):
        match = _UTC_PATTERN.search(build_environment_lock_text())
        assert match is not None
        parsed = datetime.fromisoformat(match.group(0).replace("Z", "+00:00"))
        assert parsed.utcoffset().total_seconds() == 0

    def test_header_records_the_blas_build_note(self):
        """D-13 also asks for the OpenBLAS build; `pip freeze` cannot give it."""
        text = build_environment_lock_text()
        assert "blas" in text.lower()

    def test_body_is_the_real_pip_freeze_output(self):
        """The transitive set is the whole point of the lock (D-13)."""
        text = build_environment_lock_text()
        lowered = text.lower()
        for distribution in ("numpy", "scipy", "opencv"):
            assert distribution in lowered, distribution

    def test_blas_note_degrades_to_a_reason_rather_than_raising(self, monkeypatch):
        monkeypatch.setattr("experiments._env_lock._resolve_blas_build", lambda: None)
        text = build_environment_lock_text()
        assert "numpy" in text.lower()  # the freeze half is unaffected

    def test_a_failed_freeze_writes_a_reason_not_an_empty_body(self, monkeypatch):
        monkeypatch.setattr("experiments._env_lock._run_pip_freeze", lambda: None)
        text = build_environment_lock_text()
        assert sys.executable in text  # header survives
        assert "unavailable" in text.lower()
        assert text.strip()


class TestWriteEnvironmentLock:
    def test_writes_the_named_file_and_returns_its_path(self, tmp_path):
        path = write_environment_lock(tmp_path)
        assert path == tmp_path / ENVIRONMENT_LOCK_FILENAME
        assert path.exists()
        assert path.read_text(encoding="utf-8").strip()

    def test_creates_the_output_directory_when_absent(self, tmp_path):
        path = write_environment_lock(tmp_path / "nested" / "out")
        assert path.exists()

    def test_second_write_raises_rather_than_silently_overwriting(self, tmp_path):
        write_environment_lock(tmp_path)
        with pytest.raises(FileExistsError):
            write_environment_lock(tmp_path)

    def test_force_permits_a_rewrite(self, tmp_path):
        write_environment_lock(tmp_path)
        path = write_environment_lock(tmp_path, force=True)
        assert path.exists()

    def test_a_failed_freeze_still_produces_a_file(self, tmp_path, monkeypatch):
        monkeypatch.setattr("experiments._env_lock._run_pip_freeze", lambda: None)
        path = write_environment_lock(tmp_path)
        assert path.exists()
        assert "unavailable" in path.read_text(encoding="utf-8").lower()


class TestArgParser:
    def test_out_is_required(self):
        with pytest.raises(SystemExit):
            build_arg_parser().parse_args([])

    def test_force_is_a_flag_defaulting_off(self):
        args = build_arg_parser().parse_args(["--out", "somewhere"])
        assert args.force is False
        assert Path(args.out) == Path("somewhere")


class TestMainCli:
    def test_main_writes_the_lock_and_returns_zero(self, tmp_path, capsys):
        assert main(["--out", str(tmp_path)]) == 0
        assert (tmp_path / ENVIRONMENT_LOCK_FILENAME).exists()
        assert ENVIRONMENT_LOCK_FILENAME in capsys.readouterr().out

    def test_main_returns_zero_when_the_freeze_fails(
        self, tmp_path, capsys, monkeypatch
    ):
        """D-13: the lockfile is an ARTIFACT, never a refusal."""
        monkeypatch.setattr("experiments._env_lock._run_pip_freeze", lambda: None)
        assert main(["--out", str(tmp_path)]) == 0
        assert (tmp_path / ENVIRONMENT_LOCK_FILENAME).exists()

    def test_main_returns_nonzero_only_when_the_write_itself_fails(
        self, tmp_path, capsys
    ):
        main(["--out", str(tmp_path)])
        assert main(["--out", str(tmp_path)]) == 1
        captured = capsys.readouterr()
        assert "already exists" in (captured.err + captured.out).lower()

    def test_main_force_rewrites_and_returns_zero(self, tmp_path):
        main(["--out", str(tmp_path)])
        assert main(["--out", str(tmp_path), "--force"]) == 0
