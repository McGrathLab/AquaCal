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
import sys
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


class TestThreadRegimeRecord:
    """D-14: BOTH regimes are recorded, or the numbers are uninterpretable.

    The cap applies to the stages the pool runs 4-5 wide; the four
    `serial_alone` timing stages are left at the library default because every
    historical measurement was taken unpinned.
    """

    def test_cap_is_present_and_none_when_the_variable_is_unset(self, monkeypatch):
        """Present, never absent -- `_run_manifest`'s stated rule."""
        monkeypatch.delenv("SUITE_THREAD_CAP", raising=False)
        manifest = build_run_manifest()
        assert "blas_thread_cap" in manifest
        assert manifest["blas_thread_cap"] is None

    def test_cap_is_read_from_the_driver_contract_variable(self, monkeypatch):
        monkeypatch.setenv("SUITE_THREAD_CAP", "2")
        assert build_run_manifest()["blas_thread_cap"] == 2

    def test_a_non_integer_cap_is_recorded_verbatim_rather_than_dropped(
        self, monkeypatch
    ):
        monkeypatch.setenv("SUITE_THREAD_CAP", "not-a-number")
        assert build_run_manifest()["blas_thread_cap"] == "not-a-number"

    def test_the_unpinned_list_is_exactly_the_four_timing_stages(self):
        manifest = build_run_manifest()
        assert sorted(manifest["blas_thread_unpinned_stages"]) == sorted(
            ["e4", "e4_repeat", "e2_timing", "e2_memory"]
        )

    def test_the_pinned_list_is_the_concurrent_stages_from_the_expectations(self):
        expectations = json.loads(
            (_REPO_ROOT / "experiments" / "suite_expectations.json").read_text(
                encoding="utf-8"
            )
        )
        expected = [
            stage["id"]
            for stage in expectations["stages"]
            if stage.get("concurrency") == "concurrent"
        ]
        manifest = build_run_manifest()
        assert sorted(manifest["blas_thread_cap_stages"]) == sorted(expected)

    def test_the_two_lists_are_disjoint_and_cover_every_stage(self):
        manifest = build_run_manifest()
        pinned = set(manifest["blas_thread_cap_stages"])
        unpinned = set(manifest["blas_thread_unpinned_stages"])
        assert pinned & unpinned == set()
        expectations = json.loads(
            (_REPO_ROOT / "experiments" / "suite_expectations.json").read_text(
                encoding="utf-8"
            )
        )
        assert pinned | unpinned == {s["id"] for s in expectations["stages"]}

    def test_a_missing_expectations_manifest_degrades_to_none_not_a_raise(
        self, monkeypatch, tmp_path
    ):
        monkeypatch.setattr(
            "experiments._run_manifest._SUITE_EXPECTATIONS_PATH",
            tmp_path / "absent.json",
        )
        manifest = build_run_manifest()
        assert manifest["blas_thread_cap_stages"] is None
        assert manifest["blas_thread_unpinned_stages"] is None
        assert manifest["git_sha"] is not None  # one dead source is not fatal

    def test_an_unparseable_expectations_manifest_degrades_to_none(
        self, monkeypatch, tmp_path
    ):
        broken = tmp_path / "broken.json"
        broken.write_text("{not json", encoding="utf-8")
        monkeypatch.setattr(
            "experiments._run_manifest._SUITE_EXPECTATIONS_PATH", broken
        )
        manifest = build_run_manifest()
        assert manifest["blas_thread_cap_stages"] is None
        assert manifest["blas_thread_unpinned_stages"] is None

    def test_the_new_keys_are_not_required_fields(self):
        """Gate 3 turns a None in that tuple into a FAIL, and an unset cap on a
        serial local run is legitimate, not a defect."""
        assert "blas_thread_cap" not in REQUIRED_MANIFEST_FIELDS
        assert "blas_thread_cap_stages" not in REQUIRED_MANIFEST_FIELDS
        assert "blas_thread_unpinned_stages" not in REQUIRED_MANIFEST_FIELDS
        assert len(REQUIRED_MANIFEST_FIELDS) == 17


class TestBothInterpretersAreRecorded:
    """D-30: the manifest's versions may describe an interpreter that computed
    nothing, and until now nothing said so.

    This manifest is written under `GATE_PYTHON`; every stage runs bare
    `python -u -m experiments.<mod>`. On the run machine that gap is concrete:
    D-26 records a pre-existing environment carrying the EXCLUDED OpenCV
    4.14.0, so a gate interpreter resolved there would stamp 4.14.0 onto a
    manifest whose stages ran 4.13 -- with the git shas agreeing, so Gate 3
    stays green. A mismatch is RECORDED, NEVER REFUSED: it is legitimate on the
    Windows development box by design.
    """

    def test_the_gate_interpreter_is_the_one_writing_the_manifest(self):
        assert build_run_manifest()["gate_interpreter"] == sys.executable

    def test_the_stage_interpreter_comes_from_the_driver_contract_variable(
        self, monkeypatch
    ):
        monkeypatch.setenv("SUITE_STAGE_PYTHON", "python")
        manifest = build_run_manifest()
        assert manifest["stage_interpreter_declared"] == "python"
        assert manifest["stage_interpreter"] is not None

    def test_the_keys_are_present_even_when_the_driver_did_not_declare_one(
        self, monkeypatch
    ):
        """Present, never absent -- the same rule the thread cap follows.

        An unset variable means the manifest was written outside the driver,
        which is a legitimate state and not a defect.
        """
        monkeypatch.delenv("SUITE_STAGE_PYTHON", raising=False)
        manifest = build_run_manifest()
        assert manifest["stage_interpreter_declared"] is None
        assert manifest["stage_interpreter"] is None
        assert manifest["interpreters_agree"] is None

    def test_an_unresolvable_stage_interpreter_degrades_rather_than_raising(
        self, monkeypatch
    ):
        monkeypatch.setenv("SUITE_STAGE_PYTHON", "definitely-not-an-interpreter")
        manifest = build_run_manifest()
        assert manifest["stage_interpreter"] is None
        assert manifest["interpreters_agree"] is None

    def test_a_disagreement_is_recorded_as_false_and_never_raises(
        self, monkeypatch, tmp_path
    ):
        """The whole point: a mismatch must be VISIBLE, not fatal."""
        monkeypatch.setattr(
            "experiments._run_manifest.shutil.which",
            lambda _name: str(tmp_path / "some_other_python"),
        )
        monkeypatch.setenv("SUITE_STAGE_PYTHON", "python")
        manifest = build_run_manifest()
        assert manifest["interpreters_agree"] is False

    def test_the_interpreter_keys_are_not_required_fields(self):
        """A None verdict must not become a Gate 3 FAIL."""
        for key in (
            "gate_interpreter",
            "stage_interpreter",
            "stage_interpreter_declared",
            "interpreters_agree",
        ):
            assert key not in REQUIRED_MANIFEST_FIELDS
