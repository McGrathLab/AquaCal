"""Unit tests for `tests/unit/_baseline_paths.py` (plan 26-14).

Every case drives a SANDBOX repo root rather than the real one, so both branches are
exercised regardless of what `experiments/results/` happens to hold today. A resolver whose
two branches can only be distinguished by the repository's current state would be untestable
at exactly the moment it matters -- the Phase 28 transition.
"""

from __future__ import annotations

from tests.unit._baseline_paths import (
    archive_results_dir,
    baseline_file,
    live_results_dir,
    resolve_results_dir,
)


def _make_root(tmp_path, live_files=(), archive_files=()):
    """Build a sandbox repo root with the two trees populated as named."""
    live = tmp_path / "experiments" / "results"
    archive = tmp_path / "experiments" / "pre_rerun_baseline" / "results"
    for directory, names in ((live, live_files), (archive, archive_files)):
        for name in names:
            path = directory / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("{}")
    return tmp_path


class TestResolveResultsDir:
    def test_missing_live_tree_resolves_to_the_archive(self, tmp_path):
        root = _make_root(tmp_path, archive_files=["benchmark.json"])
        resolved, which = resolve_results_dir(root)
        assert which == "archive"
        assert resolved == archive_results_dir(root)

    def test_present_but_empty_live_tree_resolves_to_the_archive(self, tmp_path):
        """26-09's move leaves the live directory PRESENT and EMPTY.

        This is the case a bare `.exists()` check would get wrong, and it is the state the
        repository is in between DRIVER-04 and Phase 28.
        """
        root = _make_root(tmp_path, archive_files=["benchmark.json"])
        live_results_dir(root).mkdir(parents=True, exist_ok=True)
        assert live_results_dir(root).is_dir()

        resolved, which = resolve_results_dir(root)
        assert which == "archive"
        assert resolved == archive_results_dir(root)

    def test_populated_live_tree_wins(self, tmp_path):
        root = _make_root(
            tmp_path, live_files=["benchmark.json"], archive_files=["benchmark.json"]
        )
        resolved, which = resolve_results_dir(root)
        assert which == "live"
        assert resolved == live_results_dir(root)

    def test_a_file_nested_one_level_down_counts_as_populated(self, tmp_path):
        """E4's records live in `e4_cells/<cell>/benchmark.json`.

        A run that produced only those must still resolve to the live tree, so the check
        walks the tree rather than reading the top level.
        """
        root = _make_root(
            tmp_path,
            live_files=["e4_cells/cameras_8_frames_50/benchmark.json"],
            archive_files=["benchmark.json"],
        )
        _, which = resolve_results_dir(root)
        assert which == "live"


class TestArchiveResultsDirNeverFollowsLive:
    def test_archive_is_returned_even_when_live_is_populated(self, tmp_path):
        """The carve-out's guarantee.

        `SEEDLESS_LEGACY_RECORDS` names six archived Phase-19.1 files that genuinely lack a
        seed. Records written by today's code carry one (plan 26-13), so a carve-out that
        followed the live tree would invert into a false failure.
        """
        root = _make_root(
            tmp_path,
            live_files=["e1_benchmark_refractive.json"],
            archive_files=["e1_benchmark_refractive.json"],
        )
        assert archive_results_dir(root) != live_results_dir(root)
        assert archive_results_dir(root).name == "results"
        assert archive_results_dir(root).parent.name == "pre_rerun_baseline"


class TestBaselineFile:
    def test_prefers_the_live_copy(self, tmp_path):
        root = _make_root(
            tmp_path, live_files=["benchmark.json"], archive_files=["benchmark.json"]
        )
        assert baseline_file("benchmark.json", repo_root=root) == (
            live_results_dir(root) / "benchmark.json"
        )

    def test_falls_back_per_file_not_per_tree(self, tmp_path):
        """A partial run leaves some artifacts live and others only archived.

        Resolution is per file so a half-populated tree does not hide the archived copy of
        something the run did not write.
        """
        root = _make_root(
            tmp_path,
            live_files=["benchmark.json"],
            archive_files=["benchmark.json", "cpr_grouping.csv"],
        )
        assert baseline_file("cpr_grouping.csv", repo_root=root) == (
            archive_results_dir(root) / "cpr_grouping.csv"
        )
