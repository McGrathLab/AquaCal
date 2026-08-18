"""The expectation manifest and the completeness gate that reads it (plan 26-03).

`experiments/suite_expectations.json` is the single source of truth for every
stage, artifact, profile, row count and wall-clock estimate the v2.1 full-suite
re-run produces (D-05). This file is what makes that claim enforceable rather
than aspirational.

The highest-value test here is the cheapest one: `TestForbiddenLiterals`. Phase
25's D-21 and the author's 2026-08-18 ruling A1 both constrain what the E1 noise
band may expect, and a manifest that quietly asserts the wrong shape produces a
gate that fails every run until Phase 28 -- or, worse, one that passes because it
asserted nothing.

Structured after `tests/unit/test_experiments_provenance.py`: a module-level
expectation source, collection-time discovery that degrades to an empty list
rather than erroring when a tree is absent, and BIDIRECTIONAL assertions.
"""

from __future__ import annotations

import importlib
import json
import pathlib

import pytest
from experiments._expectations import (
    PROFILES,
    check_completeness,
    load_expectations,
)

MANIFEST = load_expectations()
STAGES = {stage["id"]: stage for stage in MANIFEST["stages"]}
ARTIFACTS = MANIFEST["artifacts"]

PRIMARY_DIR = "experiments/results"


# --------------------------------------------------------------------------- #
# Synthetic output trees
# --------------------------------------------------------------------------- #


def _resolve_constant(dotted: str) -> list[str]:
    """Import ``module:CONSTANT`` and return it as a list of column names."""
    module_name, _, constant_name = dotted.partition(":")
    module = importlib.import_module(module_name)
    return list(getattr(module, constant_name))


def _header_for(artifact: dict) -> list[str]:
    """The CSV header a synthetic stand-in for ``artifact`` should carry.

    Taken from the artifact's declared column constant where one pins it, so the
    fixtures exercise the real coupling rather than a stub. Artifacts with no
    pinning constant get a single placeholder column -- the completeness gate
    judges row counts and existence, never headers.
    """
    if artifact["columns_constant"] is None:
        return ["placeholder"]
    return _resolve_constant(artifact["columns_constant"]) + artifact["extra_columns"]


def _write_stub(root: pathlib.Path, artifact: dict, n_rows: int) -> pathlib.Path:
    """Write an ``n_rows``-row stand-in for ``artifact`` under ``root``."""
    directory = (
        root / "results"
        if artifact["dir"] == PRIMARY_DIR
        else root / pathlib.Path(artifact["dir"]).name
    )
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / artifact["name"]
    if artifact["name"].endswith(".csv"):
        header = _header_for(artifact)
        row = ",".join("0" for _ in header)
        path.write_text(
            ",".join(header) + "\n" + "".join(f"{row}\n" for _ in range(n_rows)),
            encoding="utf-8",
        )
    elif artifact["name"].endswith(".json"):
        path.write_text(json.dumps({"stub": True}), encoding="utf-8")
    else:
        path.write_text("% stub\n", encoding="utf-8")
    return path


def _build_tree(root: pathlib.Path, profile: str, n_rows: int = 1) -> pathlib.Path:
    """Build a synthetic output tree holding every artifact expected under
    ``profile``, each with ``n_rows`` data rows. Returns the ``out_dir`` the
    gate should be pointed at.
    """
    for artifact in ARTIFACTS:
        if profile in artifact["profiles"]:
            _write_stub(root, artifact, n_rows)
    out_dir = root / "results"
    out_dir.mkdir(parents=True, exist_ok=True)
    return out_dir


def _verdicts(results, verdict: str) -> list:
    return [r for r in results if r.verdict == verdict]


# --------------------------------------------------------------------------- #
# The completeness gate
# --------------------------------------------------------------------------- #


class TestCompletenessGate:
    """`check_completeness` emits GateResults and never a second result type."""

    def test_emits_gate_results_from_check_rerun_gates(self, tmp_path):
        from experiments.check_rerun_gates import GateResult

        out_dir = _build_tree(tmp_path, "smoke")
        results = check_completeness(out_dir, profile="smoke")
        assert results
        assert all(isinstance(r, GateResult) for r in results)

    def test_empty_tree_rolls_up_to_at_least_one_fail(self, tmp_path):
        """The F-001 class Gate 3 passes silently.

        `_check_git_sha_consistency` returns PASS over an empty tree with `no
        git_sha values found across any artifact to compare` -- a cross-artifact
        consistency gate reporting success BECAUSE there are no artifacts. The
        completeness gate is the authority on "were the artifacts produced at
        all", and it must never agree.
        """
        empty = tmp_path / "results"
        empty.mkdir()
        results = check_completeness(empty, profile="full")
        assert _verdicts(results, "FAIL"), (
            "an empty tree rolled up to zero FAIL verdicts -- this is the "
            "vacuous-PASS class (F-001) the completeness gate exists to kill"
        )

    def test_missing_artifact_detail_names_the_file(self, tmp_path):
        empty = tmp_path / "results"
        empty.mkdir()
        results = check_completeness(empty, profile="full")
        fails = _verdicts(results, "FAIL")
        assert any("benchmark_grid.csv" in r.detail for r in fails)

    def test_stage_selector_restricts_to_that_stages_produces(self, tmp_path):
        out_dir = _build_tree(tmp_path, "full")
        roll_up = check_completeness(out_dir, profile="full")
        scoped = check_completeness(out_dir, profile="full", stage="e6_band")
        assert 0 < len(scoped) < len(roll_up)
        produced = set(STAGES["e6_band"]["produces"])
        assert all(any(name in r.gate for name in produced) for r in scoped)

    def test_unknown_stage_raises_naming_the_stage(self, tmp_path):
        out_dir = _build_tree(tmp_path, "full")
        with pytest.raises(ValueError, match="not_a_stage"):
            check_completeness(out_dir, profile="full", stage="not_a_stage")

    def test_unknown_profile_raises(self, tmp_path):
        out_dir = _build_tree(tmp_path, "full")
        with pytest.raises(ValueError, match="wishful"):
            check_completeness(out_dir, profile="wishful")

    def test_sibling_directory_artifact_resolves_from_out_dir_parent(self, tmp_path):
        """Matches how `check_e2_band` already resolves `results_e2_band/`.

        Plan 26-01 proved that resolution works against the archive by a live
        gate run. Rewriting it to an absolute path would break the property that
        makes `--baseline-dir` cheap, so the completeness gate copies it.
        """
        out_dir = _build_tree(tmp_path, "full")
        sibling = tmp_path / "results_e2_band" / "e2_band_scope.json"
        assert sibling.exists()
        results = check_completeness(out_dir, profile="full", stage="e2_band")
        assert results
        assert not _verdicts(results, "FAIL")

        sibling.unlink()
        results = check_completeness(out_dir, profile="full", stage="e2_band")
        assert _verdicts(results, "FAIL")


class TestProfiles:
    """`smoke` asserts existence only; `full` asserts row counts (D-06/D-49)."""

    def test_smoke_tree_yields_no_fail_verdicts(self, tmp_path):
        out_dir = _build_tree(tmp_path, "smoke")
        results = check_completeness(out_dir, profile="smoke")
        assert results
        assert not _verdicts(results, "FAIL"), [
            r.detail for r in _verdicts(results, "FAIL")
        ]

    def test_smoke_passes_a_present_but_short_artifact(self, tmp_path):
        out_dir = _build_tree(tmp_path, "smoke", n_rows=1)
        results = check_completeness(out_dir, profile="smoke", stage="e6_band")
        assert results
        assert not _verdicts(results, "FAIL")

    def test_full_fails_the_same_short_artifact(self, tmp_path):
        out_dir = _build_tree(tmp_path, "full", n_rows=1)
        results = check_completeness(out_dir, profile="full", stage="e6_band")
        fails = _verdicts(results, "FAIL")
        assert fails, "a 1-row generalization_sweep_band.csv must FAIL under full"

    def test_full_row_mismatch_detail_carries_expected_and_actual(self, tmp_path):
        out_dir = _build_tree(tmp_path, "full", n_rows=1)
        results = check_completeness(out_dir, profile="full", stage="e6_band")
        detail = next(
            r.detail
            for r in _verdicts(results, "FAIL")
            if "generalization_sweep_band.csv" in r.detail
        )
        assert "84" in detail, detail
        assert "1" in detail, detail

    def test_no_e1_or_e2_artifact_is_expected_under_smoke(self):
        """Ruling A5 / research SP-7.

        Both scripts ALWAYS write to a `TemporaryDirectory` under `--smoke`
        (`e1_refractive_comparison.py:893`, `e2_real_rig.py:428-431`), so a
        smoke-profile existence expectation for a single-seed E1 or any E2
        artifact is unsatisfiable. The `--seeds` band path IS checked before the
        smoke branch, which is why E1's band CSVs are the one exception.
        """
        e1_e2_single_seed_stages = {
            "e1",
            "e2_production",
            "e2_band",
            "e2_timing",
            "e2_memory",
            "reconstruction_bootstrap",
            "e7_focal_standoff",
        }
        offenders = [
            artifact["name"]
            for artifact in ARTIFACTS
            if artifact["stage"] in e1_e2_single_seed_stages
            and "smoke" in artifact["profiles"]
        ]
        assert offenders == [], (
            f"{offenders} are expected under the smoke profile, but the stage "
            "that produces them writes nothing to --out under --smoke"
        )

    def test_declared_profiles_are_the_known_ones(self):
        assert MANIFEST["profiles"] == list(PROFILES)
        for artifact in ARTIFACTS:
            assert artifact["profiles"], artifact["name"]
            assert set(artifact["profiles"]) <= set(PROFILES), artifact["name"]


class TestConditionalArtifacts:
    """A conditional artifact's ABSENCE is PASS, not FAIL (Phase 25 D-08)."""

    def test_missing_degenerate_observations_csv_passes(self, tmp_path):
        out_dir = _build_tree(tmp_path, "full")
        (out_dir / "degenerate_observations.csv").unlink()
        results = check_completeness(out_dir, profile="full", stage="e2_production")
        verdict = next(r for r in results if "degenerate_observations.csv" in r.gate)
        assert verdict.verdict == "PASS", verdict.detail
        assert "conditional" in verdict.detail.lower()

    def test_conditional_set_is_exactly_the_two_known_sidecars(self):
        conditional = sorted(a["name"] for a in ARTIFACTS if a["conditional"])
        assert conditional == [
            "all_observation_depths.csv",
            "degenerate_observations.csv",
        ]
