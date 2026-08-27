"""The suite expectation manifest and the completeness gate that reads it.

`experiments/suite_expectations.json` is the single source of truth for every
stage, artifact, profile, row count and wall-clock estimate the v2.1 full-suite
re-run produces (D-05). This module loads it and turns it into `GateResult`s.

**Why this gate exists.** This project's injury has never been "we kept running
after a gate failed". It has been a run that exited 0 and looked green while a
band CSV was never produced at all (F-001). Every other gate in
`check_rerun_gates.py` judges artifacts it *finds*; over an empty tree Gate 3
reports `no git_sha values found across any artifact to compare` and PASSES --
measured, not predicted (plan 26-01 ran it). A cross-artifact consistency gate
that reports success BECAUSE there are no artifacts is not evidence of a
complete run, and must never be read as one. This module is the authority on
"were the artifacts produced at all", and it is the only gate that FAILs over an
empty tree.

Two profiles (D-06 as simplified by D-49):

- `smoke` asserts artifact EXISTENCE only. A present-but-short artifact passes.
- `full` asserts row counts as well. This is the frozen Phase 28 run.

The split is what makes Phase 25's D-21 satisfiable: when D-21 was written, the
committed tree still held the pre-ruling-A1 band and the frozen sha would emit a
different shape, so a gate asserting the frozen shape unconditionally would have
failed every run until Phase 28. Phase 28 has since run and the committed tree
now carries the frozen shape; the split stays because `smoke` must still pass on
a deliberately short artifact. Row counts live in `suite_expectations.json` and
in the band sidecars, never in this docstring.
"""

from __future__ import annotations

import json
from pathlib import Path, PurePosixPath
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:  # pragma: no cover - typing only
    from experiments.check_rerun_gates import GateResult

EXPECTATIONS_PATH = Path(__file__).resolve().with_name("suite_expectations.json")

PROFILES: tuple[str, ...] = ("smoke", "full")

# The directory every stage writes into by default. An artifact declaring any
# OTHER directory is resolved as a SIBLING of out_dir, matching how
# `check_e2_band` already resolves `out_dir.parent / "results_e2_band"` -- a
# construction plan 26-01 verified still works against the archived baseline.
# Do not replace it with an absolute path; that is the property that makes
# `--baseline-dir` cheap.
PRIMARY_OUT_DIR = "experiments/results"

# Every `dir` in the manifest is written as a path from the repository root, and
# every one of them lives under this directory. `_resolve_dir` strips it and
# re-roots the remainder at `out_dir.parent`, which is what keeps the whole
# family relocatable in one move (D-29.1-17).
MANIFEST_DIR_ROOT = PurePosixPath(PRIMARY_OUT_DIR).parts[0]

# The CLOSED vocabulary a conditional artifact's `condition.holds_when` may draw
# from (D-29.1-18). Two members suffice today. `load_expectations` rejects
# anything outside this set, so the vocabulary cannot grow by accident -- a
# predicate the evaluator does not understand would otherwise become a silent
# N/A, which is how a gate quietly stops gating.
HOLDS_WHEN = frozenset({"nonzero_number", "boolean_true"})

# The keys every `condition` object must carry, all non-empty.
CONDITION_KEYS = ("description", "source", "pointer", "holds_when")


def _gate_result_cls() -> type[GateResult]:
    """Return `check_rerun_gates.GateResult`, imported late.

    `check_rerun_gates` imports THIS module at its top, so a module-level import
    in the other direction is a cycle: `_expectations` would be executing before
    `GateResult` is defined. A late import inside the call is the documented
    resolution -- there is deliberately no second result type, because the
    existing verdict-block formatting in `main()` must apply unchanged.
    """
    from experiments.check_rerun_gates import GateResult

    return GateResult


def load_expectations(path: Path | None = None) -> dict[str, Any]:
    """Load and validate the expectation manifest.

    Args:
        path: Manifest location. Defaults to `EXPECTATIONS_PATH`.

    Returns:
        The parsed manifest.

    Raises:
        ValueError: On a dangling `stage` or `depends_on` reference, a
            `produces` entry with no artifact, an artifact absent from its own
            stage's `produces`, or a duplicate `(dir, name)` pair. The message
            always names the offending id, because a manifest error that does
            not say which entry is wrong costs more than no check at all.
    """
    manifest_path = EXPECTATIONS_PATH if path is None else Path(path)
    with open(manifest_path, encoding="utf-8") as handle:
        manifest = json.load(handle)

    stage_ids = {stage["id"] for stage in manifest["stages"]}
    if len(stage_ids) != len(manifest["stages"]):
        raise ValueError(f"{manifest_path}: duplicate stage id")

    for stage in manifest["stages"]:
        dangling = [dep for dep in stage["depends_on"] if dep not in stage_ids]
        if dangling:
            raise ValueError(
                f"{manifest_path}: stage '{stage['id']}' depends_on undeclared "
                f"stage(s) {dangling}"
            )

    seen: set[tuple[str, str]] = set()
    by_stage: dict[str, set[str]] = {sid: set() for sid in stage_ids}
    for artifact in manifest["artifacts"]:
        stage_id = artifact["stage"]
        if stage_id not in stage_ids:
            raise ValueError(
                f"{manifest_path}: artifact '{artifact['name']}' names "
                f"undeclared stage '{stage_id}'"
            )
        key = (artifact["dir"], artifact["name"])
        if key in seen:
            raise ValueError(f"{manifest_path}: duplicate artifact {key}")
        seen.add(key)
        by_stage[stage_id].add(artifact["name"])
        _validate_condition(manifest_path, artifact)

    for stage in manifest["stages"]:
        declared = by_stage[stage["id"]]
        missing = [name for name in stage["produces"] if name not in declared]
        if missing:
            raise ValueError(
                f"{manifest_path}: stage '{stage['id']}' produces "
                f"{missing}, which no artifact entry declares"
            )
        unlisted = sorted(declared - set(stage["produces"]))
        if unlisted:
            raise ValueError(
                f"{manifest_path}: artifact(s) {unlisted} name stage "
                f"'{stage['id']}' but are absent from its produces list"
            )

    return manifest


def _validate_condition(manifest_path: Path, artifact: dict[str, Any]) -> None:
    """Validate one artifact's `condition` object (D-29.1-18).

    A conditional artifact MUST declare the predicate that makes its absence
    acceptable, and a non-conditional one must not carry a predicate nothing
    would ever evaluate. Every message names the offending artifact, because a
    manifest error that does not say which entry is wrong costs more than no
    check at all.

    Raises:
        ValueError: If a conditional entry has no `condition`, if the object is
            not a mapping, if any of `CONDITION_KEYS` is absent or empty, if
            `holds_when` is outside `HOLDS_WHEN`, or if a non-conditional entry
            declares a `condition`.
    """
    name = artifact["name"]
    condition = artifact.get("condition")

    if not artifact["conditional"]:
        if condition is not None:
            raise ValueError(
                f"{manifest_path}: artifact '{name}' is not conditional but "
                "declares a 'condition'. Nothing would ever evaluate it; "
                "either mark the artifact conditional or drop the predicate."
            )
        return

    if condition is None:
        raise ValueError(
            f"{manifest_path}: conditional artifact '{name}' declares no "
            "'condition'. An absence with no machine-evaluable predicate can "
            "only be scored PASS by assumption, which is the false-PASS class "
            "D-29.1-18 exists to remove."
        )
    if not isinstance(condition, dict):
        raise ValueError(
            f"{manifest_path}: conditional artifact '{name}' declares a "
            f"'condition' of type {type(condition).__name__}, not an object."
        )
    for key in CONDITION_KEYS:
        if not condition.get(key):
            raise ValueError(
                f"{manifest_path}: conditional artifact '{name}' has a "
                f"'condition' with no non-empty '{key}'. All of "
                f"{list(CONDITION_KEYS)} are required."
            )
    if condition["holds_when"] not in HOLDS_WHEN:
        raise ValueError(
            f"{manifest_path}: conditional artifact '{name}' declares "
            f"holds_when='{condition['holds_when']}', which is not one of "
            f"{sorted(HOLDS_WHEN)}. The vocabulary is deliberately closed so "
            "it cannot grow by accident."
        )


def _resolve_dir(out_dir: Path, artifact_dir: str) -> Path:
    """Resolve an artifact's declared directory against the run's `out_dir`.

    The primary directory resolves to `out_dir` itself. Every other declared
    directory resolves as a SIBLING of `out_dir`, by its path relative to the
    manifest's own `experiments/` root (`MANIFEST_DIR_ROOT`) rather than by its
    last path component alone.

    **This is a widening, not a re-pointing (D-29.1-17).** Until this change the
    resolver kept only `Path(artifact_dir).name`, so a NESTED non-primary
    directory could not be written down in the manifest at all -- which is the
    single-line reason `e2_production`'s two conditional artifacts could not
    simply have their `dir` corrected to the invocation tree their writer
    actually writes into. Every single-component non-primary entry
    (`experiments/results_e2_band`, `experiments/results_e2_timing`,
    `experiments/results_e2_memory`) resolves to a byte-identical path under
    both rules, because stripping one leading component from a two-component
    path leaves exactly the last component. `tests/unit/test_expectations.py`
    asserts that equivalence against the pre-change rule rather than assuming
    it.

    **The limitation this does NOT fix, stated because the next person will hit
    it.** The resolution is anchored at `out_dir.parent`, so it tracks a
    relocated `--out` only for directories that move WITH it. A run that
    repoints the invocation tree independently -- `SUITE_E2_INVOCATION_DIR`,
    `run_experiment_suite.sh:405` -- is not tracked, and the gate would look
    under `<out_dir>/../results_e2_invocations/...` for files written elsewhere.
    That is the pre-existing behaviour of all three sibling entries above and is
    not introduced here. It cannot bite the two entries added today: both are
    `full`-only, and the production invocation directory is the default one.

    Args:
        out_dir: The run's primary output directory.
        artifact_dir: The artifact's declared `dir`, as written in the manifest.

    Returns:
        The directory the artifact is expected in for this run.
    """
    if artifact_dir == PRIMARY_OUT_DIR:
        return out_dir
    parts = PurePosixPath(artifact_dir).parts
    if parts and parts[0] == MANIFEST_DIR_ROOT:
        parts = parts[1:]
    if not parts:
        return out_dir.parent
    return out_dir.parent.joinpath(*parts)


class _PredicateUnevaluable(Exception):
    """The condition could not be evaluated, so the verdict must be N/A.

    Carries the reason, which every N/A message quotes verbatim. A gate that
    cannot make a judgement must say so rather than report the judgement it
    would have preferred (D-29.1-18).
    """


def _resolve_source(out_dir: Path, source: str) -> Path:
    """Resolve a `condition.source` against the run's `out_dir`.

    The source is written in the SAME vocabulary as an artifact's `dir` plus a
    filename, so it moves with `--out` exactly as the artifacts do and needs no
    second resolution rule.
    """
    declared = PurePosixPath(source)
    return _resolve_dir(out_dir, str(declared.parent)) / declared.name


def _load_predicate_source(path: Path) -> Any:
    """Parse a predicate source, or raise `_PredicateUnevaluable`."""
    if not path.is_file():
        raise _PredicateUnevaluable(f"its source {path} does not exist")
    suffix = path.suffix.lower()
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise _PredicateUnevaluable(f"its source {path} could not be read: {exc}")
    if suffix == ".json":
        try:
            return json.loads(text)
        except ValueError as exc:
            raise _PredicateUnevaluable(
                f"its source {path} is not readable as JSON: {exc}"
            )
    if suffix in (".yaml", ".yml"):
        try:
            import yaml
        except ImportError as exc:  # pragma: no cover - PyYAML is a hard dep
            raise _PredicateUnevaluable(
                f"its source {path} is YAML and PyYAML is unavailable: {exc}"
            )
        try:
            return yaml.safe_load(text)
        except Exception as exc:  # noqa: BLE001 - any parse failure is one verdict
            raise _PredicateUnevaluable(
                f"its source {path} is not readable as YAML: {exc}"
            )
    raise _PredicateUnevaluable(
        f"its source {path} has an unsupported format '{suffix or path.name}'; "
        "predicate sources must be .json, .yaml or .yml"
    )


def _read_pointer(document: Any, pointer: str, path: Path) -> Any:
    """Walk a dotted `pointer` into a parsed predicate source."""
    value = document
    walked: list[str] = []
    for key in pointer.split("."):
        if not isinstance(value, dict) or key not in value:
            walked_text = ".".join(walked) or "<root>"
            raise _PredicateUnevaluable(
                f"its pointer '{pointer}' does not resolve in {path}: "
                f"'{key}' is absent under {walked_text}"
            )
        value = value[key]
        walked.append(key)
    return value


def _condition_holds(value: Any, holds_when: str) -> bool:
    """Apply one member of the closed `HOLDS_WHEN` vocabulary to a read value."""
    if holds_when == "nonzero_number":
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise _PredicateUnevaluable(
                f"holds_when='nonzero_number' read {value!r}, which is not a number"
            )
        return value != 0
    if holds_when == "boolean_true":
        if not isinstance(value, bool):
            raise _PredicateUnevaluable(
                f"holds_when='boolean_true' read {value!r}, which is not a boolean"
            )
        return value is True
    # Unreachable while `_validate_condition` guards the vocabulary; kept so a
    # future member added to HOLDS_WHEN without an evaluator becomes an N/A with
    # a reason rather than a silent PASS.
    raise _PredicateUnevaluable(  # pragma: no cover - guarded by validation
        f"holds_when='{holds_when}' has no evaluator in this module"
    )


def _evaluate_condition(out_dir: Path, condition: dict[str, Any]) -> tuple[bool, Any]:
    """Evaluate a `condition`, returning `(held, value_read)`.

    Raises:
        _PredicateUnevaluable: When the source is missing or unparseable, the
            pointer does not resolve, or the value has the wrong type for the
            declared `holds_when`. The caller turns this into N/A, never PASS.
    """
    source_path = _resolve_source(out_dir, condition["source"])
    document = _load_predicate_source(source_path)
    value = _read_pointer(document, condition["pointer"], source_path)
    return _condition_holds(value, condition["holds_when"]), value


def _misplacement_search_dirs(
    out_dir: Path, manifest: dict[str, Any]
) -> tuple[Path, ...]:
    """Every directory a missing conditional artifact is searched for in.

    The set is the primary out directory plus every directory ANY artifact
    entry declares, resolved the same way the artifacts themselves are. It is
    deliberately BOUNDED to directories the manifest knows about: a copy
    landing somewhere entirely undeclared is still invisible to this search.
    An honest limitation stated is worth more than a filesystem walk, which
    would make the gate's cost and its verdicts depend on whatever else happens
    to be on disk.

    The production manifest depends on this bound: E2's timing and memory
    invocations write byproduct copies of `degenerate_observations.csv` into
    their own trees, which are not declared and must not be reported as
    misplacements of the classification copy.
    """
    directories = [out_dir]
    for artifact in manifest["artifacts"]:
        resolved = _resolve_dir(out_dir, artifact["dir"])
        if resolved not in directories:
            directories.append(resolved)
    return tuple(directories)


def _data_row_count(path: Path) -> int | None:
    """Count DATA rows in a CSV -- never lines, and never `grep -c`.

    Returns `None` if the file cannot be parsed, so the caller can FAIL with a
    verdict naming the cause rather than crashing the whole gate run.
    """
    from experiments.check_rerun_gates import _load_csv

    try:
        frame = _load_csv(path)
    except Exception:  # noqa: BLE001 - any parse failure is one verdict, not a crash
        return None
    if frame is None:
        return None
    return int(len(frame))


def check_completeness(
    out_dir: Path,
    *,
    profile: str,
    stage: str | None = None,
    manifest: dict[str, Any] | None = None,
) -> list[GateResult]:
    """Verify that a run produced the artifacts the manifest expects.

    Args:
        out_dir: The run's primary output directory.
        profile: `"smoke"` (existence only) or `"full"` (existence plus rows).
        stage: Restrict the verdicts to this stage's `produces` list. `None`
            gives the end-of-run roll-up over the whole manifest.
        manifest: A pre-loaded manifest, for tests. Defaults to the committed
            one.

    Returns:
        One `GateResult` per expected artifact.

    Raises:
        ValueError: On an unknown profile or an unknown stage id.
    """
    gate_result = _gate_result_cls()
    if profile not in PROFILES:
        raise ValueError(
            f"unknown profile '{profile}'; valid profiles: {', '.join(PROFILES)}"
        )
    data = load_expectations() if manifest is None else manifest

    stage_ids = {entry["id"]: entry for entry in data["stages"]}
    if stage is not None and stage not in stage_ids:
        raise ValueError(
            f"unknown stage '{stage}'; valid stages: {', '.join(sorted(stage_ids))}"
        )

    out_dir = Path(out_dir)
    # Resolved once for the whole roll-up: the misplacement search is a property
    # of the manifest, not of the artifact being judged.
    search_dirs = _misplacement_search_dirs(out_dir, data)
    results: list[GateResult] = []
    for artifact in data["artifacts"]:
        if profile not in artifact["profiles"]:
            continue
        if stage is not None and artifact["stage"] != stage:
            continue
        results.append(
            _check_artifact(
                out_dir, artifact, profile, gate_result, search_dirs=search_dirs
            )
        )
    return results


def _check_artifact(
    out_dir: Path,
    artifact: dict[str, Any],
    profile: str,
    gate_result: type[GateResult],
    *,
    search_dirs: tuple[Path, ...],
) -> GateResult:
    """One artifact's completeness verdict.

    A CONDITIONAL artifact that is absent gets one of three verdicts, never an
    unexamined PASS (D-29.1-18):

    - FAIL if a file of that name is present in any OTHER directory the
      manifest declares -- a misplaced artifact is never silently green, and
      this outranks the predicate.
    - PASS if the declared predicate evaluates and shows the condition did not
      hold. The message names the source, the pointer and the value read, so
      the verdict is auditable from the gate's own output.
    - N/A if the predicate cannot be evaluated. Never PASS: a gate must not
      claim a judgement it could not make.

    `search_dirs` is bounded to directories the manifest knows about; see
    `_misplacement_search_dirs` for what that does and does not catch.
    """
    name = artifact["name"]
    gate = f"completeness:{name}"
    experiment = artifact["stage"]
    expected_dir = _resolve_dir(out_dir, artifact["dir"])
    path = expected_dir / name

    if not path.exists():
        if artifact["conditional"]:
            return _check_absent_conditional(
                artifact,
                gate_result,
                experiment=experiment,
                gate=gate,
                out_dir=out_dir,
                expected_path=path,
                expected_dir=expected_dir,
                search_dirs=search_dirs,
            )
        return gate_result(
            experiment,
            gate,
            "FAIL",
            f"{name}: NOT FOUND at {path}. Stage '{experiment}' is expected to "
            f"produce it under the '{profile}' profile.",
        )

    if profile == "smoke":
        return gate_result(
            experiment,
            gate,
            "PASS",
            f"{name}: present at {path} (the smoke profile asserts existence "
            "only -- D-49).",
        )

    expected = artifact["rows"].get("full")
    if expected is None:
        return gate_result(
            experiment,
            gate,
            "PASS",
            f"{name}: present at {path}; no row count is pinned for it "
            f"({artifact['rows_rationale']})",
        )

    actual = _data_row_count(path)
    if actual is None:
        return gate_result(
            experiment,
            gate,
            "FAIL",
            f"{name}: present at {path} but could not be read as a table, so "
            f"its row count cannot be compared against the expected {expected}.",
        )
    if actual != expected:
        return gate_result(
            experiment,
            gate,
            "FAIL",
            f"{name}: expected {expected} data row(s), found {actual} at "
            f"{path}. Derivation: {artifact['rows_rationale']}",
        )
    return gate_result(
        experiment,
        gate,
        "PASS",
        f"{name}: {actual} data row(s) at {path}, as expected.",
    )


def _check_absent_conditional(
    artifact: dict[str, Any],
    gate_result: type[GateResult],
    *,
    experiment: str,
    gate: str,
    out_dir: Path,
    expected_path: Path,
    expected_dir: Path,
    search_dirs: tuple[Path, ...],
) -> GateResult:
    """The verdict for a conditional artifact absent from its expected path.

    This is the branch the 2026-08-20 roll-up got wrong. It used to return PASS
    with no evaluation of the condition at all, so two artifacts whose condition
    HELD -- and which had been written into a directory the manifest did not
    name -- were reported as legitimately absent. A FAIL announces itself; a
    false PASS does not (D-29.1-16).
    """
    name = artifact["name"]
    condition = artifact["condition"]
    predicate = (
        f"{condition['source']} :: {condition['pointer']} "
        f"(holds_when='{condition['holds_when']}'; {condition['description']})"
    )

    misplaced = [
        directory / name
        for directory in search_dirs
        if directory != expected_dir and (directory / name).is_file()
    ]
    if misplaced:
        found = ", ".join(str(candidate) for candidate in misplaced)
        return gate_result(
            experiment,
            gate,
            "FAIL",
            f"{name}: NOT FOUND at its expected path {expected_path}, but a "
            f"file of that name IS present at {found}. A conditional artifact "
            "written outside the directory the manifest declares is a manifest "
            "that no longer describes the run -- it is never scored by its "
            "predicate, and never silently green (D-29.1-18). Either correct "
            f"the artifact's 'dir' or find out why the writer moved. Predicate "
            f"not consulted: {predicate}.",
        )

    try:
        held, value = _evaluate_condition(out_dir, condition)
    except _PredicateUnevaluable as exc:
        return gate_result(
            experiment,
            gate,
            "N/A",
            f"{name}: not found at {expected_path}, and its condition could "
            f"NOT be evaluated -- {exc}. Predicate: {predicate}. The verdict is "
            "N/A rather than PASS because a gate must not claim a judgement it "
            "could not make (D-29.1-18).",
        )

    if held:
        return gate_result(
            experiment,
            gate,
            "FAIL",
            f"{name}: NOT FOUND at {expected_path}, but its condition HELD: "
            f"{predicate} read {value!r}. The artifact was therefore expected "
            "to be written and is missing -- its absence is evidence of an "
            "incomplete run, not of a condition that did not arise.",
        )
    return gate_result(
        experiment,
        gate,
        "PASS",
        f"{name}: not found at {expected_path}, and its condition did NOT "
        f"hold: {predicate} read {value!r}. Its absence is what that condition "
        "predicts, not evidence of an incomplete run (Phase 25 D-08, as made "
        "machine-evaluable by D-29.1-18).",
    )
