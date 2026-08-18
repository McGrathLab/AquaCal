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

The split is what makes Phase 25's D-21 satisfiable: E1's band is 160/240 rows
in the committed tree and a different shape at the frozen sha, so a gate
asserting the frozen shape unconditionally would fail every run until Phase 28.
"""

from __future__ import annotations

import json
from pathlib import Path
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


def _resolve_dir(out_dir: Path, artifact_dir: str) -> Path:
    """Resolve an artifact's declared directory against the run's `out_dir`."""
    if artifact_dir == PRIMARY_OUT_DIR:
        return out_dir
    return out_dir.parent / Path(artifact_dir).name


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
    results: list[GateResult] = []
    for artifact in data["artifacts"]:
        if profile not in artifact["profiles"]:
            continue
        if stage is not None and artifact["stage"] != stage:
            continue
        results.append(_check_artifact(out_dir, artifact, profile, gate_result))
    return results


def _check_artifact(
    out_dir: Path,
    artifact: dict[str, Any],
    profile: str,
    gate_result: type[GateResult],
) -> GateResult:
    """One artifact's completeness verdict."""
    name = artifact["name"]
    gate = f"completeness:{name}"
    experiment = artifact["stage"]
    path = _resolve_dir(out_dir, artifact["dir"]) / name

    if not path.exists():
        if artifact["conditional"]:
            return gate_result(
                experiment,
                gate,
                "PASS",
                f"{name}: not found at {path} -- this artifact is conditional "
                "and is legitimately absent when the condition did not hold "
                "(Phase 25 D-08). Its absence is not evidence of an incomplete "
                "run.",
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
