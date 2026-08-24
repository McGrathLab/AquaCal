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

import ast
import importlib
import itertools
import json
import pathlib

import pytest

from experiments._expectations import (
    EXPECTATIONS_PATH,
    HOLDS_WHEN,
    PROFILES,
    _resolve_dir,
    check_completeness,
    load_expectations,
)

MANIFEST = load_expectations()
MANIFEST_TEXT = EXPECTATIONS_PATH.read_text(encoding="utf-8")
STAGES = {stage["id"]: stage for stage in MANIFEST["stages"]}
ARTIFACTS = MANIFEST["artifacts"]

PRIMARY_DIR = "experiments/results"

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
PROVENANCE_TEST = REPO_ROOT / "tests" / "unit" / "test_experiments_provenance.py"

# Artifacts whose header a module-level constant pins. Discovered from the
# manifest, so a newly registered artifact with a constant is covered the moment
# it is added -- and an artifact with no constant is simply not parametrised
# rather than silently asserted about.
PINNED_ARTIFACTS = [a for a in ARTIFACTS if a["columns_constant"] is not None]


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
    """Write an ``n_rows``-row stand-in for ``artifact`` under ``root``.

    The directory is resolved by the gate's OWN `_resolve_dir` rather than by a
    second copy of the rule here. A fixture that re-implements the resolution
    can agree with a broken resolver and disagree with a fixed one, which is the
    two-sources-of-truth shape this manifest exists to end.
    """
    directory = _resolve_dir(root / "results", artifact["dir"])
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

    def test_smoke_unwritable_artifacts_are_full_only(self):
        """P27-D-20 class 1: three artifacts no smoke code path can write.

        Each is produced only by a full-run branch, so tagging it `smoke` made
        the completeness gate assert something no code emits:

        - `structural_scaling.csv` -- `e3_derived_quantities.py:1106-1126`, the
          `--smoke` branch, writes tiers 1-3 and returns without calling
          `_write_tier4` (this file's only writer).
        - `e5_provenance.json` -- `e5_index_sensitivity.py:871-889`
          (`_run_smoke_at`) writes `index_sensitivity.csv` and returns before
          the sidecar write.
        - `fd_jacobian_accuracy.json` -- `fd_jacobian_accuracy.py:652-666`
          (`_run_smoke`) writes the CSV and returns before the sidecar write.

        This guards the retag against a silent revert.
        """
        smoke_unwritable = {
            "structural_scaling.csv",
            "e5_provenance.json",
            "fd_jacobian_accuracy.json",
        }
        by_name = {artifact["name"]: artifact for artifact in ARTIFACTS}
        for name in smoke_unwritable:
            artifact = by_name[name]
            assert artifact["profiles"] == ["full"], (
                f"{name} is tagged {artifact['profiles']}, but no --smoke code "
                "path writes it (P27-D-20 class 1)"
            )
            assert artifact["rows_rationale"], name
            assert "full-only" in artifact["rows_rationale"], (
                f"{name}'s retag must carry its reason -- a changed tag with an "
                "unchanged rationale is the FIX-06 shape"
            )

    def test_fd_jacobian_csv_stays_smoke_writable(self):
        """Only the `.json` sidecar moved; `_run_smoke` does write the CSV."""
        by_name = {artifact["name"]: artifact for artifact in ARTIFACTS}
        assert by_name["fd_jacobian_accuracy.csv"]["profiles"] == ["smoke", "full"]

    def test_declared_profiles_are_the_known_ones(self):
        assert MANIFEST["profiles"] == list(PROFILES)
        for artifact in ARTIFACTS:
            assert artifact["profiles"], artifact["name"]
            assert set(artifact["profiles"]) <= set(PROFILES), artifact["name"]


class TestResolveDirIsAWidening:
    """D-29.1-17: the nested-directory resolution must not re-point anything.

    `_resolve_dir` used to keep only ``Path(artifact_dir).name``, which is why
    a nested invocation-tree path could not be written into the manifest at
    all. The replacement resolves the declared path RELATIVE to the manifest's
    ``experiments/`` root. For every single-component non-primary entry the two
    rules agree by construction -- and this class asserts that agreement rather
    than assuming it, so a widening that silently moved an existing entry fails
    here.
    """

    @staticmethod
    def _old_rule(out_dir: pathlib.Path, artifact_dir: str) -> pathlib.Path:
        """The pre-29.1-09 resolution, kept verbatim as the reference."""
        if artifact_dir == PRIMARY_DIR:
            return out_dir
        return out_dir.parent / pathlib.Path(artifact_dir).name

    @pytest.mark.parametrize(
        "artifact_dir",
        sorted({a["dir"] for a in ARTIFACTS}),
    )
    def test_declared_dirs_resolve_as_before_or_are_newly_expressible(
        self, artifact_dir, tmp_path
    ):
        out_dir = tmp_path / "results"
        new = _resolve_dir(out_dir, artifact_dir)
        old = self._old_rule(out_dir, artifact_dir)
        nested = len(pathlib.PurePosixPath(artifact_dir).parts) > 2
        if nested:
            assert new != old, (
                f"{artifact_dir} is nested, so the old last-component rule "
                "could not express it; the two rules must differ here"
            )
        else:
            assert new == old, (
                f"{artifact_dir} resolved to {new} under the new rule and "
                f"{old} under the old one -- this was meant to be a widening, "
                "not a re-pointing"
            )

    def test_the_three_pre_existing_siblings_are_byte_identical(self, tmp_path):
        out_dir = tmp_path / "results"
        for name in ("results_e2_band", "results_e2_timing", "results_e2_memory"):
            assert _resolve_dir(out_dir, f"experiments/{name}") == tmp_path / name

    def test_the_primary_dir_still_resolves_to_out_dir_itself(self, tmp_path):
        out_dir = tmp_path / "results"
        assert _resolve_dir(out_dir, PRIMARY_DIR) == out_dir

    def test_a_nested_dir_resolves_through_every_component(self, tmp_path):
        out_dir = tmp_path / "results"
        assert (
            _resolve_dir(
                out_dir, "experiments/results_e2_invocations/e2_classification"
            )
            == tmp_path / "results_e2_invocations" / "e2_classification"
        )


# --------------------------------------------------------------------------- #
# Conditional artifacts and their machine-evaluated predicates (D-29.1-18)
# --------------------------------------------------------------------------- #

CONDITIONAL_NAME = "conditional_artifact.csv"
SIBLING_DIR = "experiments/results_elsewhere"
PREDICATE_SOURCE = "experiments/results/predicate.json"


def _artifact_entry(name: str, directory: str, **overrides) -> dict:
    """A minimal manifest artifact entry, for synthetic manifests."""
    entry = {
        "name": name,
        "dir": directory,
        "stage": "synthetic_stage",
        "profiles": ["full"],
        "rows": {},
        "rows_rationale": "synthetic entry, no row count pinned",
        "columns_constant": None,
        "columns": None,
        "extra_columns": [],
        "conditional": False,
        "immutable": False,
        "shape_only_columns": [],
    }
    entry.update(overrides)
    return entry


def _synthetic_manifest(condition: dict | None, *, with_sibling_dir: bool = False):
    """A manifest holding one conditional artifact and, optionally, a sibling
    directory the misplacement search is therefore allowed to look in."""
    artifacts = [
        _artifact_entry(
            CONDITIONAL_NAME, PRIMARY_DIR, conditional=True, condition=condition
        )
    ]
    if with_sibling_dir:
        artifacts.append(_artifact_entry("sibling_marker.csv", SIBLING_DIR))
    return {
        "profiles": list(PROFILES),
        "stages": [
            {
                "id": "synthetic_stage",
                "produces": [a["name"] for a in artifacts],
                "depends_on": [],
                "profiles": list(PROFILES),
                "out_dir": PRIMARY_DIR,
            }
        ],
        "artifacts": artifacts,
    }


def _write_predicate_source(root: pathlib.Path, value, *, pointer_root="discard_stats"):
    """Write the synthetic predicate source under the primary out dir."""
    out_dir = root / "results"
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / "predicate.json"
    path.write_text(json.dumps({pointer_root: {"flagged": value}}), encoding="utf-8")
    return path


def _condition(holds_when="nonzero_number", pointer="discard_stats.flagged", **over):
    condition = {
        "description": "at least one observation was flagged",
        "source": PREDICATE_SOURCE,
        "pointer": pointer,
        "holds_when": holds_when,
    }
    condition.update(over)
    return condition


def _conditional_verdict(root: pathlib.Path, manifest: dict):
    out_dir = root / "results"
    out_dir.mkdir(parents=True, exist_ok=True)
    results = check_completeness(out_dir, profile="full", manifest=manifest)
    return next(r for r in results if CONDITIONAL_NAME in r.gate)


class TestConditionalArtifacts:
    """A conditional artifact's absence is PASS only when a MACHINE-EVALUATED
    predicate shows the condition did not hold (D-29.1-18).

    The defect this class exists to keep dead: before 29.1-09 the conditional
    branch returned PASS on absence with no evaluation of the condition at all,
    so the 2026-08-20 roll-up reported "legitimately absent when the condition
    did not hold" for two artifacts whose condition HELD and which had been
    written into a directory the manifest did not name. A FAIL announces
    itself; a false PASS does not.
    """

    def test_present_artifact_is_checked_not_excused(self, tmp_path):
        manifest = _synthetic_manifest(_condition())
        (tmp_path / "results").mkdir(parents=True, exist_ok=True)
        (tmp_path / "results" / CONDITIONAL_NAME).write_text("a\n1\n", encoding="utf-8")
        verdict = _conditional_verdict(tmp_path, manifest)
        assert verdict.verdict == "PASS", verdict.detail
        assert "present at" in verdict.detail

    def test_absent_and_condition_did_not_hold_passes(self, tmp_path):
        _write_predicate_source(tmp_path, 0)
        verdict = _conditional_verdict(tmp_path, _synthetic_manifest(_condition()))
        assert verdict.verdict == "PASS", verdict.detail

    def test_a_pass_names_the_source_the_pointer_and_the_value(self, tmp_path):
        _write_predicate_source(tmp_path, 0)
        verdict = _conditional_verdict(tmp_path, _synthetic_manifest(_condition()))
        assert "predicate.json" in verdict.detail
        assert "discard_stats.flagged" in verdict.detail
        assert "0" in verdict.detail

    def test_absent_but_condition_held_fails(self, tmp_path):
        """The false-PASS case. Against the pre-29.1-09 branch this is PASS."""
        _write_predicate_source(tmp_path, 198)
        verdict = _conditional_verdict(tmp_path, _synthetic_manifest(_condition()))
        assert verdict.verdict == "FAIL", verdict.detail

    def test_a_fail_names_the_source_the_pointer_and_the_value(self, tmp_path):
        _write_predicate_source(tmp_path, 198)
        verdict = _conditional_verdict(tmp_path, _synthetic_manifest(_condition()))
        assert "predicate.json" in verdict.detail
        assert "discard_stats.flagged" in verdict.detail
        assert "198" in verdict.detail

    def test_a_missing_predicate_source_is_na_never_pass(self, tmp_path):
        """The second false-PASS case: a judgement the gate could not make."""
        verdict = _conditional_verdict(tmp_path, _synthetic_manifest(_condition()))
        assert verdict.verdict == "N/A", verdict.detail
        assert "predicate.json" in verdict.detail

    def test_an_unresolvable_pointer_is_na_and_names_the_pointer(self, tmp_path):
        _write_predicate_source(tmp_path, 0)
        condition = _condition(pointer="discard_stats.no_such_field")
        verdict = _conditional_verdict(tmp_path, _synthetic_manifest(condition))
        assert verdict.verdict == "N/A", verdict.detail
        assert "no_such_field" in verdict.detail

    def test_an_unparseable_predicate_source_is_na(self, tmp_path):
        out_dir = tmp_path / "results"
        out_dir.mkdir(parents=True, exist_ok=True)
        (out_dir / "predicate.json").write_text("{not json", encoding="utf-8")
        verdict = _conditional_verdict(tmp_path, _synthetic_manifest(_condition()))
        assert verdict.verdict == "N/A", verdict.detail

    def test_a_non_numeric_value_under_nonzero_number_is_na(self, tmp_path):
        _write_predicate_source(tmp_path, "many")
        verdict = _conditional_verdict(tmp_path, _synthetic_manifest(_condition()))
        assert verdict.verdict == "N/A", verdict.detail

    def test_boolean_true_predicate_holds_and_fails_on_absence(self, tmp_path):
        _write_predicate_source(tmp_path, True)
        manifest = _synthetic_manifest(_condition(holds_when="boolean_true"))
        verdict = _conditional_verdict(tmp_path, manifest)
        assert verdict.verdict == "FAIL", verdict.detail

    def test_boolean_false_predicate_does_not_hold_and_passes(self, tmp_path):
        _write_predicate_source(tmp_path, False)
        manifest = _synthetic_manifest(_condition(holds_when="boolean_true"))
        verdict = _conditional_verdict(tmp_path, manifest)
        assert verdict.verdict == "PASS", verdict.detail

    def test_a_non_boolean_value_under_boolean_true_is_na(self, tmp_path):
        _write_predicate_source(tmp_path, 1)
        manifest = _synthetic_manifest(_condition(holds_when="boolean_true"))
        verdict = _conditional_verdict(tmp_path, manifest)
        assert verdict.verdict == "N/A", verdict.detail

    def test_a_yaml_predicate_source_is_read(self, tmp_path):
        out_dir = tmp_path / "results"
        out_dir.mkdir(parents=True, exist_ok=True)
        (out_dir / "predicate.yaml").write_text(
            "internals:\n  log_all: false\n", encoding="utf-8"
        )
        condition = _condition(
            holds_when="boolean_true",
            pointer="internals.log_all",
            source="experiments/results/predicate.yaml",
        )
        verdict = _conditional_verdict(tmp_path, _synthetic_manifest(condition))
        assert verdict.verdict == "PASS", verdict.detail

    def test_misplaced_artifact_fails_naming_both_paths(self, tmp_path):
        """Absent where expected, present in a directory the manifest names."""
        _write_predicate_source(tmp_path, 0)
        elsewhere = tmp_path / "results_elsewhere"
        elsewhere.mkdir(parents=True, exist_ok=True)
        (elsewhere / CONDITIONAL_NAME).write_text("a\n1\n", encoding="utf-8")
        manifest = _synthetic_manifest(_condition(), with_sibling_dir=True)
        verdict = _conditional_verdict(tmp_path, manifest)
        assert verdict.verdict == "FAIL", verdict.detail
        assert str(tmp_path / "results" / CONDITIONAL_NAME) in verdict.detail
        assert str(elsewhere / CONDITIONAL_NAME) in verdict.detail

    def test_misplacement_overrides_a_predicate_that_did_not_hold(self, tmp_path):
        """FAIL "whatever the predicate says" -- the predicate here says PASS."""
        _write_predicate_source(tmp_path, 0)
        elsewhere = tmp_path / "results_elsewhere"
        elsewhere.mkdir(parents=True, exist_ok=True)
        (elsewhere / CONDITIONAL_NAME).write_text("a\n1\n", encoding="utf-8")
        manifest = _synthetic_manifest(_condition(), with_sibling_dir=True)
        assert _conditional_verdict(tmp_path, manifest).verdict == "FAIL"

    def test_misplacement_overrides_an_unevaluable_predicate(self, tmp_path):
        elsewhere = tmp_path / "results_elsewhere"
        elsewhere.mkdir(parents=True, exist_ok=True)
        (elsewhere / CONDITIONAL_NAME).write_text("a\n1\n", encoding="utf-8")
        manifest = _synthetic_manifest(_condition(), with_sibling_dir=True)
        assert _conditional_verdict(tmp_path, manifest).verdict == "FAIL"

    def test_a_copy_in_an_undeclared_directory_is_not_searched(self, tmp_path):
        """The stated limitation: the search set is bounded to declared dirs.

        The timing and memory invocation trees hold byproduct copies of
        `degenerate_observations.csv` and are deliberately not declared, so this
        is the behaviour the production manifest depends on -- not an oversight.
        """
        _write_predicate_source(tmp_path, 0)
        undeclared = tmp_path / "somewhere_undeclared"
        undeclared.mkdir(parents=True, exist_ok=True)
        (undeclared / CONDITIONAL_NAME).write_text("a\n1\n", encoding="utf-8")
        verdict = _conditional_verdict(tmp_path, _synthetic_manifest(_condition()))
        assert verdict.verdict == "PASS", verdict.detail

    def test_a_non_conditional_artifacts_absence_still_fails(self, tmp_path):
        manifest = _synthetic_manifest(_condition(), with_sibling_dir=True)
        out_dir = tmp_path / "results"
        out_dir.mkdir(parents=True, exist_ok=True)
        results = check_completeness(out_dir, profile="full", manifest=manifest)
        verdict = next(r for r in results if "sibling_marker.csv" in r.gate)
        assert verdict.verdict == "FAIL", verdict.detail
        assert "NOT FOUND" in verdict.detail

    def test_conditional_set_is_exactly_the_two_known_sidecars(self):
        conditional = sorted(a["name"] for a in ARTIFACTS if a["conditional"])
        assert conditional == [
            "all_observation_depths.csv",
            "degenerate_observations.csv",
        ]

    def test_the_committed_conditional_entries_carry_a_complete_condition(self):
        for artifact in ARTIFACTS:
            if not artifact["conditional"]:
                continue
            condition = artifact.get("condition")
            assert isinstance(condition, dict), artifact["name"]
            for key in ("description", "source", "pointer", "holds_when"):
                assert condition.get(key), (artifact["name"], key)
            assert condition["holds_when"] in HOLDS_WHEN, artifact["name"]

    @staticmethod
    def _run_output_root():
        """`(root, which)` for the tree that holds a run's output, or `(None, None)`.

        Live first, then the 29.1-06 archive. This is `resolve_results_dir`'s
        live-or-archive rule (`tests/unit/_baseline_paths.py`) with the NEWER
        archive as the fallback, and the choice of archive is the whole point:
        this test's subject is the two CONDITIONAL artifacts, which only the
        2026-08-20 run produced. `pre_rerun_baseline/` predates the condition
        mechanism entirely, so falling back there would assert against a tree
        that could not satisfy the claim under any correct manifest.

        Plan 29.1-06 emptied `experiments/results/` deliberately -- the
        re-freeze tag must ship an empty output tree or the driver's own D-24
        pre-flight refuses to start (`run_experiment_suite.sh:1059-1064`). The
        live branch therefore re-tightens automatically the moment the re-run
        repopulates it, which is the property this rule exists to provide.
        """
        for root, which in (
            (REPO_ROOT / "experiments" / "results", "live"),
            (
                REPO_ROOT / "experiments" / "freeze01_run_output" / "results",
                "freeze01 archive",
            ),
        ):
            if root.is_dir() and any(path.is_file() for path in root.rglob("*")):
                return root, which
        return None, None

    def test_the_committed_conditions_resolve_to_files_that_exist(self):
        """Both predicate sources are artifacts THIS run produces, so the
        predicate is a statement about this run and a stale artifact from
        another one cannot satisfy it.

        The resolved subject is NAMED in every assertion, for the reason
        `resolve_results_dir` returns its `which`: a test that silently
        switched what it validates is no better than one that silently
        validates nothing. When no tree holds a run at all -- a fresh clone of
        the re-freeze tag, before the suite has run -- this SKIPS naming both
        trees it looked in, rather than passing vacuously.
        """
        root, which = self._run_output_root()
        if root is None:
            pytest.skip(
                "no run output on disk: neither experiments/results nor "
                "experiments/freeze01_run_output/results holds a file. A fresh "
                "clone of the re-freeze tag has neither until the suite has run."
            )
        for artifact in ARTIFACTS:
            if not artifact["conditional"]:
                continue
            source = artifact["condition"]["source"]
            directory = _resolve_dir(root, str(pathlib.PurePosixPath(source).parent))
            path = directory / pathlib.PurePosixPath(source).name
            assert path.is_file(), (artifact["name"], which, str(path))

    def test_the_holds_when_vocabulary_is_closed_and_small(self):
        assert HOLDS_WHEN == frozenset({"nonzero_number", "boolean_true"})


class TestConditionValidation:
    """`_validate_manifest` rejects a conditional entry the gate could not
    reason about, and always names the offending artifact."""

    @staticmethod
    def _load_mutated(tmp_path, mutate):
        mutated = json.loads(json.dumps(MANIFEST))
        for artifact in mutated["artifacts"]:
            if artifact["conditional"]:
                mutate(artifact)
                break
        path = tmp_path / "mutated_expectations.json"
        path.write_text(json.dumps(mutated), encoding="utf-8")
        return load_expectations(path)

    def test_the_committed_manifest_still_loads(self):
        assert load_expectations()

    def test_a_conditional_entry_with_no_condition_is_rejected(self, tmp_path):
        with pytest.raises(ValueError, match="degenerate_observations.csv"):
            self._load_mutated(tmp_path, lambda a: a.pop("condition"))

    def test_a_condition_missing_a_key_is_rejected_naming_the_key(self, tmp_path):
        with pytest.raises(ValueError, match="pointer"):
            self._load_mutated(tmp_path, lambda a: a["condition"].pop("pointer"))

    def test_an_unrecognised_holds_when_is_rejected(self, tmp_path):
        def mutate(artifact):
            artifact["condition"]["holds_when"] = "vibes"

        with pytest.raises(ValueError, match="degenerate_observations.csv"):
            self._load_mutated(tmp_path, mutate)

    def test_an_unrecognised_holds_when_names_the_allowed_values(self, tmp_path):
        def mutate(artifact):
            artifact["condition"]["holds_when"] = "vibes"

        with pytest.raises(ValueError, match="nonzero_number"):
            self._load_mutated(tmp_path, mutate)

    def test_a_non_conditional_entry_may_not_carry_a_condition(self, tmp_path):
        mutated = json.loads(json.dumps(MANIFEST))
        target = next(a for a in mutated["artifacts"] if not a["conditional"])
        target["condition"] = {
            "description": "d",
            "source": PREDICATE_SOURCE,
            "pointer": "a.b",
            "holds_when": "nonzero_number",
        }
        path = tmp_path / "mutated_expectations.json"
        path.write_text(json.dumps(mutated), encoding="utf-8")
        with pytest.raises(ValueError, match=target["name"]):
            load_expectations(path)


# --------------------------------------------------------------------------- #
# The manifest's own contents
# --------------------------------------------------------------------------- #


class TestForbiddenLiterals:
    """The cheapest and highest-value test in this file.

    Two rulings constrain what the E1 noise band may expect, and they forbid
    four different row counts between them:

    - **Phase 25 D-21** forbids 640 and 960, and forbids requiring a
      ``noise_std`` column anywhere in ``experiments/results/``. Those are the
      ten-seed four-level shape, which does not exist until Phase 28; a gate
      asserting them fails every run until then.
    - **Ruling A1** (author, 2026-08-18) forbids the ragged 352 / 528 shape of
      D-41. ``_run_band`` is a strict cartesian ``seeds x NOISE_LEVELS``
      (``e1_refractive_comparison.py:1091, :1120``) and cannot express a ragged
      grid, and two invocations would overwrite each other (``force=True`` at
      ``:1177, :1202``). The uniform 4 x 4 grid gives 256 / 384.
    """

    FORBIDDEN_ROW_COUNTS = (640, 960, 352, 528)

    @pytest.mark.parametrize("forbidden", FORBIDDEN_ROW_COUNTS)
    def test_no_artifact_declares_a_forbidden_row_count(self, forbidden):
        offenders = [
            artifact["name"]
            for artifact in ARTIFACTS
            if forbidden in artifact["rows"].values()
        ]
        assert offenders == [], (
            f"{offenders} declare an expected row count of {forbidden}. "
            "Phase 25 D-21 forbids 640 and 960 (they are the Phase 28 shape, "
            "unreachable before then); ruling A1 forbids 352 and 528 (the "
            "ragged D-41 grid, which _run_band cannot express). The uniform "
            "E1 noise grid is 4 seeds x 4 noise levels = 256 / 384 rows."
        )

    @pytest.mark.parametrize("forbidden", FORBIDDEN_ROW_COUNTS)
    def test_forbidden_literal_appears_nowhere_in_the_manifest(self, forbidden):
        assert str(forbidden) not in MANIFEST_TEXT, (
            f"the literal {forbidden} appears in {EXPECTATIONS_PATH.name}. "
            "Phase 25 D-21 forbids 640/960 and ruling A1 forbids 352/528 -- "
            "even in prose, because the next reader will copy it."
        )

    def test_no_results_artifact_requires_a_noise_std_column(self):
        """Phase 25 D-21: no expectation may REQUIRE ``noise_std`` in
        ``experiments/results/``.

        The noise axis is a full-profile band property of ``exp1_band.csv`` and
        ``exp1_parameter_band.csv`` alone -- it belongs in their ``rows`` and
        ``extra_columns`` entries and nowhere else.
        """
        allowed = {"exp1_band.csv", "exp1_parameter_band.csv"}
        offenders = [
            artifact["name"]
            for artifact in ARTIFACTS
            if artifact["dir"] == PRIMARY_DIR
            and artifact["name"] not in allowed
            and "noise_std" in json.dumps(artifact)
        ]
        assert offenders == [], (
            f"{offenders} name a noise_std column while living under "
            "experiments/results. Phase 25 D-21 forbids it: the committed "
            "tree has no such column and will not until Phase 28."
        )

    def test_no_expectation_names_results_e6_repeat2(self):
        """D-42 reverses D-09: ``e6_repeat2`` is OFF under BOTH profiles.

        The determinism statistic it produces is a response-letter number, not a
        section 3 number, and it is produced by ``determinism_probe.py``
        comparing two repeats rather than by the stage alone. It costs ~2.8 h.
        """
        assert "results_e6_repeat2" not in MANIFEST_TEXT
        assert "e6_repeat2" not in set(STAGES)
        assert "e6_repeat2" not in {a["stage"] for a in ARTIFACTS}


class TestStageArtifactCoupling:
    """BIDIRECTIONAL, in the shape `test_experiments_provenance.py` proved.

    A one-way assertion catches a stage that lost its artifact but not an
    artifact that lost its stage, and the second is exactly the drift D-05
    exists to prevent.
    """

    def test_every_artifact_names_a_declared_stage(self):
        undeclared = sorted({a["stage"] for a in ARTIFACTS} - set(STAGES))
        assert undeclared == []

    def test_every_stage_produces_only_declared_artifacts(self):
        by_stage: dict[str, set[str]] = {sid: set() for sid in STAGES}
        for artifact in ARTIFACTS:
            by_stage[artifact["stage"]].add(artifact["name"])
        for stage_id, stage in STAGES.items():
            assert set(stage["produces"]) <= by_stage[stage_id], stage_id

    def test_every_artifact_appears_in_its_stages_produces(self):
        for artifact in ARTIFACTS:
            assert artifact["name"] in STAGES[artifact["stage"]]["produces"], (
                f"{artifact['name']} names stage '{artifact['stage']}' but is "
                "absent from its produces list"
            )

    def test_every_depends_on_edge_names_a_declared_stage(self):
        for stage in STAGES.values():
            for dependency in stage["depends_on"]:
                assert dependency in STAGES, (stage["id"], dependency)

    def test_the_five_ordering_constraints_are_expressed_as_depends_on(self):
        """Array order cannot express a temporal constraint; `depends_on` can.

        O1 e7_focal_standoff after e7_band (it reads a hardcoded, cwd-relative
        `experiments/results/interface_ablation_band.csv`). O2 and O4 after
        e2_production -- O4 because `resolve_e2_benchmark_path` returns None on
        branch 3 and SILENTLY drops E4's real-rig row. O3 fd_jacobian free.
        O5 e3 is one stage, not two. Plus D-52 constraint 1, e6_band after
        e6_repeat1.
        """
        assert "e7_band" in STAGES["e7_focal_standoff"]["depends_on"]
        assert "e2_production" in STAGES["reconstruction_bootstrap"]["depends_on"]
        assert "e2_production" in STAGES["e4"]["depends_on"]
        assert STAGES["fd_jacobian"]["depends_on"] == ["preflight"]
        assert "e6_repeat1" in STAGES["e6_band"]["depends_on"]
        assert "--check" in STAGES["e3"]["invocation"]
        assert "--force" in STAGES["e3"]["invocation"]

    def test_the_dependency_graph_is_acyclic(self):
        pending = {sid: set(s["depends_on"]) for sid, s in STAGES.items()}
        resolved: set[str] = set()
        while pending:
            ready = {sid for sid, deps in pending.items() if deps <= resolved}
            assert ready, f"cycle among {sorted(pending)}"
            resolved |= ready
            pending = {sid: deps for sid, deps in pending.items() if sid not in ready}


class TestConcurrencySafety:
    """D-52's three hard constraints on the stage model."""

    def test_concurrent_stages_sharing_results_write_disjoint_filenames(self):
        """D-52 constraint 3, verified against the manifest -- not by
        inspection, which is what the constraint itself asks for."""
        concurrent = [
            stage
            for stage in STAGES.values()
            if stage["concurrency"] == "concurrent" and stage["out_dir"] == PRIMARY_DIR
        ]
        for left, right in itertools.combinations(concurrent, 2):
            overlap = set(left["produces"]) & set(right["produces"])
            assert overlap == set(), (
                f"concurrent stages '{left['id']}' and '{right['id']}' both "
                f"write {sorted(overlap)} into {PRIMARY_DIR}"
            )

    def test_serial_alone_is_exactly_the_four_timing_stages(self):
        """Review H4's rationale is TIMING INTEGRITY, so the exemption applies
        only where a timing number is produced."""
        alone = sorted(
            sid for sid, s in STAGES.items() if s["concurrency"] == "serial_alone"
        )
        assert alone == ["e2_memory", "e2_timing", "e4", "e4_repeat"]

    def test_every_stage_declares_a_known_concurrency_and_frame_class(self):
        for stage in STAGES.values():
            assert stage["concurrency"] in {"serial_alone", "concurrent"}
            assert stage["frame_class"] in {"none", "30", "100", "200"}

    def test_e6_repeat1_and_e6_band_can_never_overlap(self):
        """D-52 constraint 1. `run_stage_e6_repeat1` removes `e6_configs/` and
        `generalization_sweep.csv` under the SHARED out_dir that `e6_band` also
        writes, so a depends_on edge is the only expression of 'never overlap'
        a concurrency pool can honour."""
        assert "e6_repeat1" in STAGES["e6_band"]["depends_on"]
        assert STAGES["e6_repeat1"]["out_dir"] == STAGES["e6_band"]["out_dir"]


class TestColumnConstants:
    """The manifest's declared column counts against the imported constants.

    D-07's coupling: a schema-changing fix that forgets to update the manifest
    produces a red test here rather than a silently wrong expectation.
    """

    @pytest.mark.parametrize(
        "artifact",
        PINNED_ARTIFACTS,
        ids=[f"{a['stage']}-{a['name']}" for a in PINNED_ARTIFACTS],
    )
    def test_declared_columns_match_the_imported_constant(self, artifact):
        dotted = artifact["columns_constant"]
        module_name, _, constant_name = dotted.partition(":")
        module = importlib.import_module(module_name)
        constant = getattr(module, constant_name, None)
        assert constant is not None, (
            f"{artifact['name']} names {dotted}, but {module_name} has no "
            f"attribute {constant_name}"
        )
        assert len(constant) == artifact["columns"], (
            f"{artifact['name']} declares {artifact['columns']} columns but "
            f"{dotted} has {len(constant)}. One of the two moved; the manifest "
            "is the source of truth for the expectation and the constant is "
            "the source of truth for the header."
        )

    def test_the_named_d07_constants_are_covered_by_columns_entries(self):
        """D-07's named list, plus the constants D-07 omitted."""
        required = {
            "E5_COLUMNS",
            "ABLATION_COLUMNS",
            "SPATIAL_COLUMNS",
            "DEGENERATE_OBSERVATION_COLUMNS",
            "OBSERVATION_DEPTH_COLUMNS",
            "GRID_COLUMNS",
            "EXP1_COLUMNS",
            "EXP2_COLUMNS",
            "EXP3_COLUMNS",
            "E6_COLUMNS",
            "E6_PER_CAMERA_COLUMNS",
            "FD_ACCURACY_COLUMNS",
            "CAMERA_PARAMS_COLUMNS",
            "RECONSTRUCTION_COLUMNS",
            "RESIDUALS_COLUMNS",
            "CODE_CONSTANTS_COLUMNS",
            "NEWTON_COLUMNS",
            "CPR_COLUMNS",
            "SCALING_COLUMNS",
        }
        declared = {a["columns_constant"].partition(":")[2] for a in PINNED_ARTIFACTS}
        missing = sorted(required - declared)
        assert missing == [], f"{missing} pin a header no artifact entry names"

    def test_every_pinned_artifact_declares_an_integer_columns_count(self):
        for artifact in PINNED_ARTIFACTS:
            assert isinstance(artifact["columns"], int), artifact["name"]

    def test_unpinned_artifacts_declare_no_columns_count(self):
        for artifact in ARTIFACTS:
            if artifact["columns_constant"] is None:
                assert artifact["columns"] is None, artifact["name"]

    def test_extra_columns_are_never_part_of_the_pinned_columns(self):
        """`extra_columns` are what the WRITER appends beyond the pinned
        header. A name in both would mean the manifest double-counts it."""
        for artifact in PINNED_ARTIFACTS:
            if not artifact["extra_columns"]:
                continue
            dotted = artifact["columns_constant"]
            module_name, _, constant_name = dotted.partition(":")
            constant = set(getattr(importlib.import_module(module_name), constant_name))
            overlap = constant & set(artifact["extra_columns"])
            assert overlap == set(), (artifact["name"], sorted(overlap))


class TestShapeConstantReconciliation:
    """`check_rerun_gates.py`'s own hardcoded shape constants against the
    manifest.

    These constants are a SECOND encoding of the same numbers -- the exact
    two-sources-of-truth failure D-05 exists to prevent. They carry an authority
    comment naming this manifest; this class is what makes that comment binding.
    """

    def test_e6_band_rows_are_configurations_times_the_gates_seed_count(self):
        from experiments.check_rerun_gates import _E6_EXPECTED_SEED_COUNT

        rows = next(
            a for a in ARTIFACTS if a["name"] == "generalization_sweep_band.csv"
        )["rows"]["full"]
        assert rows % _E6_EXPECTED_SEED_COUNT == 0
        assert rows // _E6_EXPECTED_SEED_COUNT == 14, (
            "D-40 leaves 14 of E6's 17 band configurations (the scale axis is "
            "dropped); the manifest and the gate constant disagree"
        )

    def test_e5_band_rows_are_configurations_times_the_gates_seed_count(self):
        from experiments.check_rerun_gates import _E5_EXPECTED_SEED_COUNT

        rows = next(
            a for a in ARTIFACTS if a["name"] == "index_sensitivity_seed_band.csv"
        )["rows"]["full"]
        assert rows % _E5_EXPECTED_SEED_COUNT == 0
        assert rows // _E5_EXPECTED_SEED_COUNT == 11

    def test_e4_repeat_rows_are_two_repeats_of_the_gates_cell_list(self):
        from experiments.check_rerun_gates import _E4_REPEAT_CELLS

        rows = next(a for a in ARTIFACTS if a["name"] == "benchmark_grid_repeat.csv")[
            "rows"
        ]["full"]
        assert rows == 2 * len(_E4_REPEAT_CELLS)

    def test_the_cameras_axis_survives_d40(self):
        from experiments.check_rerun_gates import _E6_EXPECTED_CAMERA_VALUES

        assert _E6_EXPECTED_CAMERA_VALUES == (8, 12, 16)
        assert "cameras" in STAGES["e6_band"]["invocation"]
        assert "scale" not in STAGES["e6_band"]["invocation"]


class TestCsvToRecordReconciliation:
    """The manifest against `test_experiments_provenance.CSV_TO_RECORD`.

    Research flags `CSV_TO_RECORD` as a SECOND artifact inventory that will
    drift from the manifest unless one reads the other. This test is that link.

    Its keys are read with `ast` rather than by importing the module, so the
    reconciliation cannot pass vacuously because an import failed.
    """

    @staticmethod
    def _csv_to_record_keys() -> list[str]:
        tree = ast.parse(PROVENANCE_TEST.read_text(encoding="utf-8"))
        for node in tree.body:
            target = None
            if isinstance(node, ast.AnnAssign):
                target = node.target
            elif isinstance(node, ast.Assign) and len(node.targets) == 1:
                target = node.targets[0]
            if isinstance(target, ast.Name) and target.id == "CSV_TO_RECORD":
                assert isinstance(node.value, ast.Dict)
                return [
                    key.value
                    for key in node.value.keys
                    if isinstance(key, ast.Constant)
                ]
        raise AssertionError(f"CSV_TO_RECORD not found in {PROVENANCE_TEST}")

    def test_the_keys_were_actually_found(self):
        keys = self._csv_to_record_keys()
        assert len(keys) >= 20, (
            "parsed too few CSV_TO_RECORD keys to be a real reconciliation; "
            "the parse, not the manifest, is what failed"
        )

    def test_every_csv_to_record_key_is_a_manifest_artifact(self):
        names = {a["name"] for a in ARTIFACTS}
        missing = sorted(set(self._csv_to_record_keys()) - names)
        assert missing == [], (
            f"{missing} are covered by CSV_TO_RECORD but absent from "
            f"{EXPECTATIONS_PATH.name}. Two artifact inventories that do not "
            "read each other WILL drift -- that is the failure D-05 exists to "
            "prevent."
        )


class TestWallClockBudget:
    """D-38: a per-stage estimate summing to a stated total, so Phases 27 and
    28 schedule against a number rather than a hope."""

    @staticmethod
    def _midpoint(value) -> float:
        if isinstance(value, list):
            return (value[0] + value[1]) / 2
        return float(value)

    def test_every_stage_carries_a_non_empty_source(self):
        for stage in STAGES.values():
            source = stage["est_hours"]["source"]
            assert isinstance(source, str) and source.strip(), stage["id"]

    def test_e7_band_states_its_uncertainty_rather_than_closing_it(self):
        """A probe was offered and DECLINED by the author on 2026-08-18, so the
        estimate is a range with an explicit `unmeasured` marker. Do not
        schedule a probe for it."""
        est = STAGES["e7_band"]["est_hours"]
        assert isinstance(est["value"], list)
        assert "unmeasured" in est["source"]

    def test_serial_total_agrees_with_the_sum_of_the_stage_estimates(self):
        total = sum(
            self._midpoint(stage["est_hours"]["value"]) for stage in STAGES.values()
        )
        stated = self._midpoint(MANIFEST["wall_clock_summary"]["serial_total_hours"])
        assert abs(stated - total) <= 0.15 * total, (
            f"wall_clock_summary states {stated} h but the stages sum to {total:.2f} h"
        )

    def test_the_dominant_stage_really_is_the_longest(self):
        summary = MANIFEST["wall_clock_summary"]
        longest = max(
            STAGES.values(), key=lambda s: self._midpoint(s["est_hours"]["value"])
        )
        assert summary["dominant_stage"] == longest["id"]

    def test_the_summary_names_the_machine_each_figure_refers_to(self):
        """A budget that silently mixes the 20-core Windows box with the
        32-core Linux target is worthless."""
        summary = MANIFEST["wall_clock_summary"]
        assert "Windows" in summary["machine"]
        assert "Linux" in summary["target_machine"]

    def test_concurrency_total_is_below_the_serial_total(self):
        summary = MANIFEST["wall_clock_summary"]
        assert self._midpoint(
            summary["expected_total_with_concurrency_hours"]
        ) < self._midpoint(summary["serial_total_hours"])


class TestExpectationSheet:
    """D-08: ``experiments/EXPECTATIONS.md``'s generated region is RENDERED
    from the manifest, never hand-maintained.

    DRIVER-03 requires a written hand-verification sheet to exist BEFORE the
    frozen run, because the run is what it will be checked against. A sheet
    that drifted from the manifest is worse than no sheet: a hand-verifier
    comparing a finished tree against stale expectations produces a confident
    wrong verdict, which is the same failure class as F-001 (a run that exited
    0 while a band CSV was never produced at all).

    CONTEXT amendment section D's D-44 proposed cutting this renderer and this
    test, on the grounds that the sheet is authored once and frozen days later.
    ``26-VALIDATION.md``'s contract requires them, and plan 26-09 resolved the
    conflict in favour of keeping both: they are cheap, and they make D-05's
    "one list" claim literally true rather than aspirational.
    """

    @staticmethod
    def _sheet_module():
        return importlib.import_module("experiments.render_expectation_sheet")

    @staticmethod
    def _drifted_manifest():
        """A copy of the manifest with exactly one pinned row count moved."""
        drifted = json.loads(json.dumps(MANIFEST))
        for artifact in drifted["artifacts"]:
            if artifact["rows"].get("full") is not None:
                artifact["rows"]["full"] += 1
                return drifted
        raise AssertionError("no artifact pins a full-profile row count")

    def test_the_sheet_has_exactly_one_generated_region(self):
        sheet = self._sheet_module()
        text = sheet.SHEET_PATH.read_text(encoding="utf-8")
        assert text.count(sheet.BEGIN_MARKER) == 1
        assert text.count(sheet.END_MARKER) == 1

    def test_the_committed_sheet_is_up_to_date_with_the_manifest(self):
        """The freshness assertion itself."""
        sheet = self._sheet_module()
        text = sheet.SHEET_PATH.read_text(encoding="utf-8")
        _, generated, _ = sheet.split_sheet(text)
        assert generated == sheet.render_sheet(), (
            "experiments/EXPECTATIONS.md's generated region no longer matches "
            "experiments/suite_expectations.json. Regenerate it with: "
            "python -m experiments.render_expectation_sheet --write"
        )

    def test_check_exits_zero_against_the_committed_sheet(self):
        assert self._sheet_module().main(["--check"]) == 0

    def test_a_stale_sheet_makes_check_exit_non_zero(self, monkeypatch):
        """The gate genuinely fails when the manifest moves under the sheet."""
        sheet = self._sheet_module()
        monkeypatch.setattr(
            sheet, "load_expectations", lambda *a, **k: self._drifted_manifest()
        )
        assert sheet.main(["--check"]) != 0

    def test_a_stale_sheet_names_the_regeneration_command(self, monkeypatch, capsys):
        """A failure that does not say how to fix it costs more than no check."""
        sheet = self._sheet_module()
        monkeypatch.setattr(
            sheet, "load_expectations", lambda *a, **k: self._drifted_manifest()
        )
        sheet.main(["--check"])
        captured = capsys.readouterr()
        assert "render_expectation_sheet --write" in captured.out + captured.err

    def test_rendering_the_sheet_twice_is_idempotent(self):
        sheet = self._sheet_module()
        once = sheet.replace_generated_region(
            sheet.SHEET_PATH.read_text(encoding="utf-8"), sheet.render_sheet()
        )
        twice = sheet.replace_generated_region(once, sheet.render_sheet())
        assert once == twice

    def test_regenerating_the_sheet_never_touches_the_hand_written_prose(self):
        """Everything outside the markers is prose the renderer must not own."""
        sheet = self._sheet_module()
        text = sheet.SHEET_PATH.read_text(encoding="utf-8")
        head, _, tail = sheet.split_sheet(text)
        rewritten = sheet.replace_generated_region(text, "regenerated\n")
        new_head, new_generated, new_tail = sheet.split_sheet(rewritten)
        assert (new_head, new_tail) == (head, tail)
        assert new_generated == "regenerated\n"

    def test_every_full_profile_artifact_has_a_row_in_the_sheet(self):
        """The sheet is the hand-verifier's checklist; an artifact missing from
        it is an artifact nobody looks at."""
        generated = self._sheet_module().render_sheet()
        missing = [
            artifact["name"]
            for artifact in ARTIFACTS
            if "full" in artifact["profiles"] and artifact["name"] not in generated
        ]
        assert missing == []

    def test_the_sheet_carries_each_conditional_predicates_description(self):
        """The sheet is the hand-verification document (D-29.1-18).

        A reader judging a finished run needs to know what makes an absence
        acceptable, not merely that the artifact is conditional. The one-line
        `description` is surfaced; the machine-readable source, pointer and
        `holds_when` stay in the manifest, which remains the authority.
        """
        generated = self._sheet_module().render_sheet()
        conditional = [a for a in ARTIFACTS if a["conditional"]]
        assert conditional, "the manifest declares no conditional artifacts"
        for artifact in conditional:
            assert artifact["condition"]["description"] in generated, artifact["name"]

    def test_the_sheet_does_not_leak_the_whole_condition_object(self):
        """Only the description belongs in the sheet."""
        generated = self._sheet_module().render_sheet()
        for artifact in ARTIFACTS:
            if not artifact["conditional"]:
                continue
            assert artifact["condition"]["pointer"] not in generated
            assert artifact["condition"]["holds_when"] not in generated

    def test_the_sheet_marks_every_shape_only_column(self):
        """Existence and row count are not correctness: a gauge-corrected column
        populated with uncorrected values passes every completeness check. The
        sheet is where that gap is closed, so it must name those columns."""
        generated = self._sheet_module().render_sheet()
        shape_only = {
            column
            for artifact in ARTIFACTS
            for column in artifact["shape_only_columns"]
        }
        assert shape_only, "the manifest declares no shape-only columns at all"
        assert [c for c in sorted(shape_only) if c not in generated] == []
