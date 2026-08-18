"""Unit tests for experiments/_run_manifest.py (plan 26-02, DRIVER-02, TDD).

These tests deliberately drive the REAL git repository and the REAL installed
distributions rather than mocking `subprocess`. The whole point of DRIVER-02 is
that the recording mechanism works on the box that runs the suite: a test that
mocks `git describe` proves nothing about whether `git describe` can be read.

Only the "degrades to None" contract is exercised with a monkeypatch, and it
patches the one named resolver under test -- never `subprocess` globally.
"""

from __future__ import annotations

import importlib.metadata
import json
import re
import subprocess
from datetime import datetime
from pathlib import Path

import cv2
import pytest
from experiments._run_manifest import (
    MANIFEST_SCHEMA_VERSION,
    REQUIRED_MANIFEST_FIELDS,
    RUN_MANIFEST_FILENAME,
    build_run_manifest,
    main,
    write_run_manifest,
)

# `git describe --tags --long` against a VERSION tag. The trailing `-dirty` is
# optional; the `-<n>-g<sha>` suffix is not, and it is the whole reason D-18
# prefers this over the installed distribution version.
_DESCRIBE_PATTERN = re.compile(r"^v?\d+\.\d+\.\d+-\d+-g[0-9a-f]+(-dirty)?$")

_REPO_ROOT = Path(__file__).resolve().parents[2]


class TestBuildRunManifest:
    def test_every_required_field_is_non_null(self):
        manifest = build_run_manifest()
        missing = sorted(
            name for name in REQUIRED_MANIFEST_FIELDS if manifest.get(name) is None
        )
        assert missing == [], f"null required manifest fields: {missing}"

    def test_manifest_carries_exactly_the_required_names(self):
        manifest = build_run_manifest()
        assert set(REQUIRED_MANIFEST_FIELDS) <= set(manifest)

    def test_schema_version_is_the_module_constant(self):
        assert build_run_manifest()["schema_version"] == MANIFEST_SCHEMA_VERSION

    def test_opencv_build_keeps_the_pypi_suffix_cv2_version_drops(self):
        """`4.13.0.90` vs `4.13.0` -- the `.90`/`.92` ambiguity D-20 names."""
        manifest = build_run_manifest()
        assert manifest["opencv_version"] == cv2.__version__
        assert manifest["opencv_build"] == importlib.metadata.version("opencv-python")
        assert manifest["opencv_build"].startswith(manifest["opencv_version"])
        assert len(manifest["opencv_build"]) > len(manifest["opencv_version"])

    def test_git_describe_is_a_version_anchor(self):
        describe = build_run_manifest()["git_describe"]
        assert _DESCRIBE_PATTERN.match(describe), describe

    def test_git_describe_distinguishes_commits_the_dist_version_cannot(self):
        """F-002: every commit after the tag reports the same dist version."""
        manifest = build_run_manifest()
        assert manifest["installed_distribution_version"] == importlib.metadata.version(
            "aquacal"
        )
        # The describe anchor carries a commit count and an abbreviated sha the
        # bare distribution version does not.
        assert manifest["git_describe"] != manifest["installed_distribution_version"]
        assert manifest["installed_distribution_version"] in manifest["git_describe"]

    def test_git_sha_is_forty_hex_and_matches_rev_parse(self):
        manifest = build_run_manifest()
        sha = manifest["git_sha"]
        assert re.fullmatch(r"[0-9a-f]{40}", sha), sha
        expected = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=_REPO_ROOT,
            capture_output=True,
            text=True,
            check=True,
        ).stdout.strip()
        assert sha == expected

    def test_git_dirty_is_a_bool_agreeing_with_the_describe_suffix(self):
        manifest = build_run_manifest()
        assert isinstance(manifest["git_dirty"], bool)
        assert manifest["git_dirty"] == manifest["git_describe"].endswith("-dirty")

    def test_utc_start_is_iso_8601_utc_ending_in_z(self):
        utc_start = build_run_manifest()["utc_start"]
        assert utc_start.endswith("Z"), utc_start
        parsed = datetime.fromisoformat(utc_start.replace("Z", "+00:00"))
        assert parsed.tzinfo is not None
        assert parsed.utcoffset().total_seconds() == 0

    def test_platform_fields_are_populated(self):
        manifest = build_run_manifest()
        for name in ("os", "kernel", "machine", "cpu_model"):
            assert isinstance(manifest[name], str) and manifest[name].strip()
        assert isinstance(manifest["cpu_count_logical"], int)
        assert isinstance(manifest["ram_total_bytes"], int)

    def test_resolver_failure_degrades_to_none_rather_than_raising(self, monkeypatch):
        """Mirrors `capture_environment`'s never-raise contract: the GATE, not
        the emitter, is what turns a None into a FAIL (D-21)."""
        monkeypatch.setattr(
            "experiments._run_manifest._resolve_git_describe", lambda: None
        )
        monkeypatch.setattr(
            "experiments._run_manifest._resolve_opencv_build", lambda: None
        )
        manifest = build_run_manifest()
        assert manifest["git_describe"] is None
        assert manifest["opencv_build"] is None
        # Everything else still resolved -- one dead resolver is not fatal.
        assert manifest["git_sha"] is not None


class TestWriteRunManifest:
    def test_writes_the_named_file_and_returns_its_path(self, tmp_path):
        path = write_run_manifest(tmp_path)
        assert path == tmp_path / RUN_MANIFEST_FILENAME
        assert path.exists()
        with open(path) as f:
            payload = json.load(f)
        assert payload["git_sha"] == build_run_manifest()["git_sha"]

    def test_creates_the_output_directory_when_absent(self, tmp_path):
        target = tmp_path / "nested" / "out"
        path = write_run_manifest(target)
        assert path.exists()

    def test_second_write_raises_rather_than_silently_overwriting(self, tmp_path):
        write_run_manifest(tmp_path)
        with pytest.raises(FileExistsError):
            write_run_manifest(tmp_path)

    def test_force_permits_a_rewrite(self, tmp_path):
        write_run_manifest(tmp_path)
        path = write_run_manifest(tmp_path, force=True)
        assert path.exists()


class TestMainCli:
    def test_main_writes_the_manifest_and_returns_zero(self, tmp_path, capsys):
        assert main(["--out", str(tmp_path)]) == 0
        assert (tmp_path / RUN_MANIFEST_FILENAME).exists()
        assert RUN_MANIFEST_FILENAME in capsys.readouterr().out

    def test_main_returns_nonzero_when_the_write_fails(self, tmp_path, capsys):
        main(["--out", str(tmp_path)])
        assert main(["--out", str(tmp_path)]) == 1
        captured = capsys.readouterr()
        assert "already exists" in (captured.err + captured.out).lower()

    def test_main_force_rewrites_and_returns_zero(self, tmp_path):
        main(["--out", str(tmp_path)])
        assert main(["--out", str(tmp_path), "--force"]) == 0
