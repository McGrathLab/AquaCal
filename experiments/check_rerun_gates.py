"""Machine-checkable post-run gates over the Phase 19.3 re-run's artifacts (D-19.3-18).

Reads the artifacts an output directory (e.g. `experiments/results/`) already carries --
never runs a calibration and never regenerates anything -- and reports PASS/FAIL/N/A per
gate, per experiment. Exits non-zero if any gate FAILs.

Four gates, applied per experiment:

    Gate 1 (guard count):     every row/cell has degenerate_observations_at_solution == 0.
                               A missing field cannot be read as zero and FAILs the same
                               as a non-zero value -- an un-instrumented artifact is not
                               evidence of a clean solve.
    Gate 2 (published status): no row is published with status == "degenerate". Reported
                               N/A (not skipped) for artifacts that carry no status column
                               at all -- those experiments record the guard count but do
                               not gate on it per row (plan 19.3-07's gating split).
    Gate 3 (provenance):       every artifact carries git_sha, seed, the water refractive
                               index, and a timestamp (this project's provenance sidecars
                               carry no explicit timestamp field, so the artifact file's
                               own filesystem mtime is used as that evidence). Every
                               git_sha found across the WHOLE run must be IDENTICAL --
                               a split sha means something was committed while a stage was
                               still running. Gate 3 also verifies the suite-level
                               `run_manifest.json` (DRIVER-02): it exists, every required
                               environment field is non-null (including the OpenCV PyPI
                               build suffix `cv2.__version__` drops), its git_sha agrees
                               with the artifacts', and the tree was not dirty. Those four
                               are ALL hard FAIL and never N/A -- a provenance mismatch
                               that only warns is a provenance mismatch that ships (D-21).
    Gate 4 (optimality):       first-order optimality is present (not null) per stage.

E3 runs no calibration at all, so gates 1, 2 and 4 are N/A for it -- reported explicitly
with a reason, never silently skipped, since a silently-skipped check that reports green is
a defect this project has already hit (see ORCHESTRATOR-NOTES section 5). Gate 3 still
applies to E3's `e3_provenance.json` sidecar, minus the water-index field it has no reason
to carry (E3 never touches a refractive index).

This script contains NO comparison against a recovered-parameter tolerance and NO gate on
reprojection error. Judging convergence by reprojection error is a known blocking
anti-pattern from Phase 19.2 (a synthetic cell shipped a plausible low value at an
optimality six orders of magnitude too high); the guard count and optimality PRESENCE are
what this script gates on instead. It also never prints an optimality value to more than
zero significant figures of precision (it checks presence only, never a magnitude).
"""

from __future__ import annotations

import argparse
import json
import math
import re
import sys
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

import pandas as pd

try:
    from experiments._run_manifest import (
        REQUIRED_MANIFEST_FIELDS,
        RUN_MANIFEST_FILENAME,
    )
except ModuleNotFoundError:  # pragma: no cover - script-path invocation
    # The driver invokes this file BY PATH (`"${GATE_PYTHON}"
    # experiments/check_rerun_gates.py <out_dir>`, rerun_19_5.sh:257), which
    # puts `experiments/` on sys.path but NOT the repository root, so the
    # sibling package import above cannot resolve. Adding the root here keeps
    # both invocation styles working; a bare `from _run_manifest import ...`
    # would instead break `python -m` and the unit tests.
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from experiments._run_manifest import (
        REQUIRED_MANIFEST_FIELDS,
        RUN_MANIFEST_FILENAME,
    )

# DRIVER-01 / D-04's completeness gate. Its ~100 lines live in their own module
# rather than in this 1,800-line one; this is the single import that wires them
# in. The sys.path fallback above has already run, so script-path invocation
# resolves it too.
from experiments._expectations import PROFILES, check_completeness

Verdict = Literal["PASS", "FAIL", "N/A"]

_GUARD_COLUMN = "degenerate_observations_at_solution"
_STATUS_COLUMN = "status"
_DEGENERATE_STATUS = "degenerate"


@dataclass(frozen=True)
class GateResult:
    """One gate's verdict against one artifact (or the whole run, for gate 3's
    cross-artifact check).

    Attributes:
        experiment: The experiment label (`"E1"`..`"E7"`, or `"ALL"` for the
            cross-artifact provenance-consistency check).
        gate: A short gate identifier, e.g. `"gate1_guard_count:<artifact>"`.
        verdict: One of `"PASS"`, `"FAIL"`, `"N/A"`.
        detail: A human-readable explanation of the verdict.
    """

    experiment: str
    gate: str
    verdict: Verdict
    detail: str


def legality_probe(
    seeds: Sequence[int], camera_counts: Sequence[int]
) -> list[GateResult]:
    """D-19.5-04's empirical re-verification of the 19.4 clearance-floor fix,
    at the queue's own seed list and `n_cameras` values, BEFORE any long
    stage runs.

    For each `(seed, n_cameras)` this performs the SAME two draws E4 and E6
    perform internally before any solve -- the calibration draw at `seed`
    and the holdout draw at `seed + 1_000_000`
    (`experiments/e4_benchmark_grid.py:902`,
    `experiments/e6_generalization_sweep.py:821`) -- builds the grid-family
    camera array for each draw via `generate_camera_array`, and checks
    whether the frozen `GRID_DEPTH_RANGE[0]` clears (is `>=`) that draw's own
    derived `board_clearance_floor`. A draw whose derived floor exceeds the
    frozen minimum is illegal: `build_grid_scenario` would then be asked to
    place a board within a depth range that cannot keep every corner
    submerged at that draw's water surface.

    This is a STRUCTURAL check over camera geometry only. It performs NO
    calibration solve -- no `least_squares`, no `calibrate_synthetic`, no
    pipeline call of any kind -- and completes in seconds, not minutes.

    Args:
        seeds: The calibration seeds the queue intends to run (the holdout
            draw at `seed + 1_000_000` is derived automatically for each).
        camera_counts: The `n_cameras` values the queue intends to run.

    Returns:
        One `GateResult` per `(seed, n_cameras, draw)` -- e.g.
        `legality_probe([42], [12])` returns exactly 2 results, one for the
        calibration draw and one for the holdout draw -- so a FAIL names
        exactly which combination is illegal.
    """
    # LAZY IMPORT, deliberately not at module level: this module is also
    # invoked as a bare script (`python experiments/check_rerun_gates.py
    # <out_dir>`, both rerun_19_4.sh's and rerun_19_5.sh's run_gate_check),
    # under which Python adds only the script's OWN directory to sys.path,
    # not the repo root -- a module-level `from experiments.e4_benchmark_grid
    # import ...` would make every ordinary gate check (check_e1..check_e7,
    # none of which needs this) fail with `ModuleNotFoundError: No module
    # named 'experiments'` on that invocation path. Deferring the import to
    # here keeps the existing bare-script invocation working, and costs
    # nothing since legality_probe is only ever called from a context where
    # cwd is the repo root (prelaunch_gate.sh's and rerun_19_5.sh's own
    # heredoc invocations, and this test file, all of which run with the
    # repo root on sys.path).
    from aquacal.datasets.synthetic import board_clearance_floor, generate_camera_array
    from experiments.e4_benchmark_grid import (
        GRID_BOARD_CONFIG,
        GRID_DEPTH_RANGE,
        GRID_HEIGHT_ABOVE_WATER,
        GRID_LAYOUT,
        GRID_SPACING,
    )

    results: list[GateResult] = []
    for seed in seeds:
        for n_cameras in camera_counts:
            for draw_name, draw_seed in (
                ("calibration", seed),
                ("holdout", seed + 1_000_000),
            ):
                _, _, water_zs = generate_camera_array(
                    n_cameras=n_cameras,
                    layout=GRID_LAYOUT,
                    spacing=GRID_SPACING,
                    height_above_water=GRID_HEIGHT_ABOVE_WATER,
                    seed=draw_seed,
                )
                floor = board_clearance_floor(GRID_BOARD_CONFIG, water_zs, 15.0)
                gate = f"legality_probe:seed={seed}:n_cameras={n_cameras}:{draw_name}"
                if GRID_DEPTH_RANGE[0] >= floor:
                    results.append(
                        GateResult(
                            "ALL",
                            gate,
                            "PASS",
                            f"seed={seed} n_cameras={n_cameras} {draw_name} draw "
                            f"(draw_seed={draw_seed}): derived floor {floor:.6f} "
                            f"<= frozen GRID_DEPTH_RANGE[0] "
                            f"{GRID_DEPTH_RANGE[0]:.6f} -- legal",
                        )
                    )
                else:
                    results.append(
                        GateResult(
                            "ALL",
                            gate,
                            "FAIL",
                            f"seed={seed} n_cameras={n_cameras} {draw_name} draw "
                            f"(draw_seed={draw_seed}): derived floor {floor:.6f} "
                            f"EXCEEDS frozen GRID_DEPTH_RANGE[0] "
                            f"{GRID_DEPTH_RANGE[0]:.6f} -- this seed/n_cameras "
                            "combination is illegal and must not enter the "
                            "queue's seed list (D-19.5-04)",
                        )
                    )
    return results


def _load_json(path: Path) -> dict | None:
    """Load a JSON artifact, or `None` if it does not exist.

    A file that exists but fails to parse is returned as a dict carrying only
    `_load_error`, so a caller can still produce a FAIL verdict naming the
    cause rather than crashing the whole gate run on one corrupt file.
    """
    if not path.exists():
        return None
    try:
        with open(path) as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError) as exc:
        return {"_load_error": f"{type(exc).__name__}: {exc}"}


def _load_csv(path: Path) -> pd.DataFrame | None:
    """Load a CSV artifact, or `None` if it does not exist."""
    if not path.exists():
        return None
    return pd.read_csv(path)


def _guard_count_from_record(record: dict) -> int | None:
    """Extract the final-solution guard count from any of the shapes this
    project's provenance records carry it in: a direct-call benchmark
    record's `problem_shape`, an E6 per-configuration checkpoint's top level,
    or a `discard_stats` block (E5's provenance sidecar). Returns `None` if
    none of the three shapes carries the field.
    """
    problem_shape = record.get("problem_shape")
    if isinstance(problem_shape, dict) and _GUARD_COLUMN in problem_shape:
        return problem_shape[_GUARD_COLUMN]
    if _GUARD_COLUMN in record:
        return record[_GUARD_COLUMN]
    discard_stats = record.get("discard_stats")
    if isinstance(discard_stats, dict) and _GUARD_COLUMN in discard_stats:
        return discard_stats[_GUARD_COLUMN]
    return None


#: The two axes plan 24-01 split the merged counter on, and the per-stage
#: denominator it records beside them. `cause` answers "what do I fix?";
#: `fate` answers "can I trust this record's optimality?". They are two
#: INDEPENDENT decompositions of the SAME set of invalid observations, not
#: disjoint buckets -- summing across the two axes double-counts.
_CAUSE_PREFIX = "degenerate_observations_cause_"
_FATE_PREFIX = "degenerate_observations_fate_"
_DENOMINATOR_PREFIX = "observations_evaluated__"


def _guard_breakdown_from_record(record: dict) -> dict | None:
    """Extract plan 24-01's split counters and per-stage denominators.

    Uses the SAME three read shapes as `_guard_count_from_record` -- a
    direct-call benchmark record's `problem_shape`, the record's top level, or
    a `discard_stats` block -- rather than a parallel lookup, because those
    three are exactly the shapes this project's provenance records carry
    discard accounting in.

    Args:
        record: A loaded provenance/benchmark record.

    Returns:
        A dict holding every `degenerate_observations_cause_*`,
        `degenerate_observations_fate_*` and `observations_evaluated__*` entry
        found, or `None` when the record carries none of them (any artifact
        predating plan 24-01's split).
    """
    for candidate in (
        record.get("discard_stats"),
        record.get("problem_shape"),
        record,
    ):
        if not isinstance(candidate, dict):
            continue
        breakdown = {
            key: value
            for key, value in candidate.items()
            if key.startswith((_CAUSE_PREFIX, _FATE_PREFIX, _DENOMINATOR_PREFIX))
        }
        if breakdown:
            return breakdown
    return None


def _sum_by_axis(breakdown: dict, prefix: str) -> dict[str, int]:
    """Collapse one axis's `<prefix><name>__<stage>` entries to `{name: count}`."""
    totals: dict[str, int] = {}
    for key, value in breakdown.items():
        if not key.startswith(prefix):
            continue
        name = key[len(prefix) :].split("__", 1)[0]
        totals[name] = totals.get(name, 0) + int(value)
    return totals


def _format_guard_breakdown(breakdown: dict) -> str:
    """Render the split for the gate's report line.

    Reports the dominant CAUSE and its fraction against the per-stage
    `observations_evaluated__*` denominator -- the number that retires the
    hand-reconstructed `198 / 73,975 = 0.268%`, because the denominator is now
    recorded by the same pass that produced the count instead of being
    reconstructed by hand. Also reports the fate split, with both axes
    LABELLED, so the two are never summed together.

    Deliberately descriptive only. Classifying what the production rig's 198
    actually are is DEGEN-04's (Phase 25); nothing here interprets either axis
    or feeds a verdict.
    """
    parts: list[str] = []
    causes = _sum_by_axis(breakdown, _CAUSE_PREFIX)
    if causes:
        dominant, dominant_count = max(causes.items(), key=lambda kv: kv[1])
        denominator = sum(
            int(value)
            for key, value in breakdown.items()
            if key.startswith(_DENOMINATOR_PREFIX)
        )
        fraction = (
            f", {dominant_count / denominator:.3%} of the {denominator} "
            "observation(s) evaluated"
            if denominator
            else ""
        )
        parts.append(f"dominant cause={dominant} ({dominant_count}){fraction}")
    fates = _sum_by_axis(breakdown, _FATE_PREFIX)
    if fates:
        rendered = ", ".join(f"{count} {name}" for name, count in sorted(fates.items()))
        parts.append(f"by fate: {rendered}")
    if not parts:
        return ""
    # "by cause"/"by fate" are two views of the SAME observations -- never add
    # one axis's numbers to the other's.
    return (
        " ["
        + "; ".join(parts)
        + " (cause and fate are separate axes over the same observations; "
        "never add them together)]"
    )


def _provenance_gaps(
    record: dict,
    *,
    require_water_index: bool,
    water_index_keys: tuple[str, ...] = ("n_water",),
) -> list[str]:
    """Return the names of any required provenance fields missing from `record`.

    Checks `environment.git_sha`, a seed (top-level or `solver_config.seed`),
    and -- when `require_water_index` -- the refractive index of water, read
    from `solver_config.n_water`, the per-configuration `config.n_water`
    block (E6), or any of `water_index_keys` at the record's top level (E5's
    sidecar names this field `n_true` rather than `n_water`, since E5 sweeps
    the ASSUMED index against a TRUE one).
    """
    gaps: list[str] = []
    environment = record.get("environment") or {}
    if not environment.get("git_sha"):
        gaps.append("git_sha")

    seed = record.get("seed")
    if seed is None:
        seed = (record.get("solver_config") or {}).get("seed")
    if seed is None:
        gaps.append("seed")

    if require_water_index:
        water_index = (record.get("solver_config") or {}).get("n_water")
        if water_index is None:
            config = record.get("config") or {}
            water_index = config.get("n_water")
        if water_index is None:
            for key in water_index_keys:
                if record.get(key) is not None:
                    water_index = record[key]
                    break
        if water_index is None:
            gaps.append("water refractive index (n_water/n_true)")

    return gaps


def _optimality_present(record: dict) -> bool:
    """True if every stage this record carries reports a non-null first-order
    optimality value.

    Handles both shapes this project uses: a direct-call/pipeline benchmark
    record's `stages` block (each stage a dict with an `optimality` key), and
    an E6 per-configuration checkpoint's flat `metrics` dict (keys prefixed
    `optimality_`). Returns False if neither shape is present, or if any
    present stage's value is null.
    """
    stages = record.get("stages")
    if isinstance(stages, dict) and stages:
        return all(
            isinstance(stage, dict) and stage.get("optimality") is not None
            for stage in stages.values()
        )
    metrics = record.get("metrics")
    if isinstance(metrics, dict):
        optimality_keys = [key for key in metrics if key.startswith("optimality_")]
        if optimality_keys:
            return all(metrics.get(key) is not None for key in optimality_keys)
    return False


def _check_json_artifact(
    experiment: str,
    label: str,
    record: dict | None,
    *,
    check_guard: bool,
    check_optimality: bool,
    require_water_index: bool,
    water_index_keys: tuple[str, ...] = ("n_water",),
) -> list[GateResult]:
    """Apply gates 1, 3 and (optionally) 4 to one JSON artifact.

    Gate 2 (published status) does not apply to a single JSON record -- it is
    a per-row check over a CSV -- so it is handled separately by
    `_check_status_column`.
    """
    results: list[GateResult] = []

    if record is None:
        if check_guard:
            results.append(
                GateResult(
                    experiment,
                    f"gate1_guard_count:{label}",
                    "FAIL",
                    f"{label} not found",
                )
            )
        results.append(
            GateResult(
                experiment, f"gate3_provenance:{label}", "FAIL", f"{label} not found"
            )
        )
        if check_optimality:
            results.append(
                GateResult(
                    experiment,
                    f"gate4_optimality:{label}",
                    "FAIL",
                    f"{label} not found",
                )
            )
        return results

    if "_load_error" in record:
        message = f"{label}: {record['_load_error']}"
        if check_guard:
            results.append(
                GateResult(experiment, f"gate1_guard_count:{label}", "FAIL", message)
            )
        results.append(
            GateResult(experiment, f"gate3_provenance:{label}", "FAIL", message)
        )
        if check_optimality:
            results.append(
                GateResult(experiment, f"gate4_optimality:{label}", "FAIL", message)
            )
        return results

    if check_guard:
        count = _guard_count_from_record(record)
        # The verdict is exactly `count > 0 -> degenerate`: no threshold, no
        # tolerance. Plan 24-01's fraction threshold scales WARNING VOLUME in
        # the library and is deliberately absent here -- no fraction of any
        # size appears in this module as a gate condition. The real-rig
        # gate-scope question stays deferred -- it cannot be decided until
        # DEGEN-04 (Phase 25) reports what the production rig's 198 are, so
        # there is no real-rig carve-out either.
        breakdown = _guard_breakdown_from_record(record)
        detail = _format_guard_breakdown(breakdown) if breakdown else ""
        if count is None:
            results.append(
                GateResult(
                    experiment,
                    f"gate1_guard_count:{label}",
                    "FAIL",
                    f"{label}: no {_GUARD_COLUMN!r} field found (cannot confirm "
                    "zero). From Phase 24 onward a clean run emits this field "
                    "at an explicit 0, so an absent field means an artifact "
                    "predating the instrumentation, not an unmeasurable run -- "
                    "regenerate it rather than reading the absence as clean",
                )
            )
        elif count == 0:
            results.append(
                GateResult(
                    experiment,
                    f"gate1_guard_count:{label}",
                    "PASS",
                    f"{label}: count=0{detail}",
                )
            )
        else:
            results.append(
                GateResult(
                    experiment,
                    f"gate1_guard_count:{label}",
                    "FAIL",
                    f"{label}: non-zero guard count ({count}) at the final solution -- "
                    f"optimality is unreliable here{detail}",
                )
            )

    gaps = _provenance_gaps(
        record,
        require_water_index=require_water_index,
        water_index_keys=water_index_keys,
    )
    if gaps:
        results.append(
            GateResult(
                experiment,
                f"gate3_provenance:{label}",
                "FAIL",
                f"{label}: missing provenance field(s) {gaps}",
            )
        )
    else:
        results.append(
            GateResult(
                experiment,
                f"gate3_provenance:{label}",
                "PASS",
                f"{label}: git_sha/seed/water-index present (timestamp = file mtime)",
            )
        )

    if check_optimality:
        if _optimality_present(record):
            results.append(
                GateResult(
                    experiment,
                    f"gate4_optimality:{label}",
                    "PASS",
                    f"{label}: optimality present per stage",
                )
            )
        else:
            results.append(
                GateResult(
                    experiment,
                    f"gate4_optimality:{label}",
                    "FAIL",
                    f"{label}: optimality missing or null for at least one stage",
                )
            )

    return results


def _validate_profile(profile: str | None, *, caller: str) -> None:
    """Reject an unknown profile name, naming the offender (P27-D-20).

    Mirrors `_expectations.check_completeness`'s validation exactly -- the only
    profile-aware checker that predates this one. `None` means "no profile
    selected" and every checker must then keep its pre-existing, strictest
    behaviour, so it is always legal.

    Args:
        profile: The caller's `profile` argument.
        caller: The checker's name, for the error message.

    Raises:
        ValueError: If `profile` is neither `None` nor a member of `PROFILES`.
    """
    if profile is None or profile in PROFILES:
        return
    raise ValueError(
        f"{caller}: unknown profile '{profile}'; valid profiles: {', '.join(PROFILES)}"
    )


def _check_guard_column(
    experiment: str, label: str, df: pd.DataFrame | None, column: str = _GUARD_COLUMN
) -> GateResult:
    """Gate 1 over an aggregated CSV: every row's guard-count column is zero."""
    if df is None:
        return GateResult(
            experiment, f"gate1_guard_count:{label}", "FAIL", f"{label} not found"
        )
    if column not in df.columns:
        return GateResult(
            experiment,
            f"gate1_guard_count:{label}",
            "FAIL",
            f"{label}: no {column!r} column present (cannot confirm zero)",
        )
    bad_mask = df[column].isna() | (df[column].fillna(1) != 0)
    if not bad_mask.any():
        return GateResult(
            experiment,
            f"gate1_guard_count:{label}",
            "PASS",
            f"{label}: {len(df)} row(s), guard count zero everywhere",
        )
    n_bad = int(bad_mask.sum())
    return GateResult(
        experiment,
        f"gate1_guard_count:{label}",
        "FAIL",
        f"{label}: {n_bad} of {len(df)} row(s) have a non-zero or missing guard count",
    )


def _check_status_column(
    experiment: str, label: str, df: pd.DataFrame | None, column: str = _STATUS_COLUMN
) -> GateResult:
    """Gate 2 over an aggregated CSV: no row is published with status=="degenerate".

    Reports N/A, not a silent skip, when `column` is absent -- some
    experiments record the guard count but never gate on it per row (plan
    19.3-07's harness-gating split).
    """
    if df is None:
        return GateResult(
            experiment, f"gate2_status:{label}", "FAIL", f"{label} not found"
        )
    if column not in df.columns:
        return GateResult(
            experiment,
            f"gate2_status:{label}",
            "N/A",
            f"{label}: no {column!r} column in this artifact (record-only, not gated "
            "per-row -- see plan 19.3-07's harness-gating split)",
        )
    bad = df[df[column] == _DEGENERATE_STATUS]
    if len(bad) == 0:
        return GateResult(
            experiment,
            f"gate2_status:{label}",
            "PASS",
            f"{label}: no row published with {column}=={_DEGENERATE_STATUS!r}",
        )
    return GateResult(
        experiment,
        f"gate2_status:{label}",
        "FAIL",
        f"{label}: {len(bad)} row(s) published with {column}=={_DEGENERATE_STATUS!r}",
    )


def check_e1(out_dir: Path) -> list[GateResult]:
    """E1 -- refractive vs non-refractive comparison. Two direct-call benchmark
    records; the fixed-header exp1/exp2/exp3 CSVs carry no status column."""
    results: list[GateResult] = []
    for filename in ("e1_benchmark_refractive.json", "e1_benchmark_nonrefractive.json"):
        record = _load_json(out_dir / filename)
        results += _check_json_artifact(
            "E1",
            filename,
            record,
            check_guard=True,
            check_optimality=True,
            require_water_index=True,
        )
    results.append(
        GateResult(
            "E1",
            "gate2_status",
            "N/A",
            "E1's exp1/exp2/exp3 CSVs are fixed byte-identical-header contracts with no "
            "status column (record-only per plan 19.3-07)",
        )
    )
    return results


def check_e3(out_dir: Path) -> list[GateResult]:
    """E3 -- derived quantities. Runs no calibration: only gate 3 applies, and
    even gate 3 skips the water-index field (E3 never touches one)."""
    record = _load_json(out_dir / "e3_provenance.json")
    results = _check_json_artifact(
        "E3",
        "e3_provenance.json",
        record,
        check_guard=False,
        check_optimality=False,
        require_water_index=False,
    )
    reason = (
        "E3 runs no calibration (N/A per this gate script's design, see plan 19.3-08)"
    )
    results.append(
        GateResult("E3", "gate1_guard_count", "N/A", f"no guard count: {reason}")
    )
    results.append(
        GateResult("E3", "gate2_status", "N/A", f"no per-cell status: {reason}")
    )
    results.append(
        GateResult("E3", "gate4_optimality", "N/A", f"no optimality: {reason}")
    )
    return results


def check_e4(out_dir: Path, *, profile: str | None = None) -> list[GateResult]:
    """E4 -- cameras x frames synthetic benchmark grid. Nine per-cell
    direct-call benchmark records plus the aggregated `benchmark_grid.csv`.

    Args:
        out_dir: The run's primary output directory.
        profile: `"smoke"` relaxes the two `benchmark_grid.csv` column gates
            from FAIL to `N/A` when the file is ABSENT -- E4's `--smoke` path
            writes no grid, and the manifest already tags that artifact
            `full`-only (P27-D-20). A grid that is PRESENT but malformed still
            FAILs at every profile. `None` (the default) and `"full"` keep the
            pre-existing behaviour exactly.

    Raises:
        ValueError: On an unknown profile.
    """
    _validate_profile(profile, caller="check_e4")
    results: list[GateResult] = []
    cells_dir = out_dir / "e4_cells"
    cell_paths = (
        sorted(cells_dir.glob("*/benchmark.json")) if cells_dir.exists() else []
    )
    if not cell_paths:
        for gate in ("gate1_guard_count", "gate3_provenance", "gate4_optimality"):
            results.append(
                GateResult(
                    "E4", gate, "FAIL", f"no per-cell benchmark.json under {cells_dir}"
                )
            )
    for cell_path in cell_paths:
        record = _load_json(cell_path)
        label = f"e4_cells/{cell_path.parent.name}/benchmark.json"
        results += _check_json_artifact(
            "E4",
            label,
            record,
            check_guard=True,
            check_optimality=True,
            require_water_index=True,
        )
    grid_path = out_dir / "benchmark_grid.csv"
    if profile == "smoke" and not grid_path.exists():
        # The gate stays VISIBLE, it just cannot judge: E4's --smoke path never
        # writes the grid, so its absence carries no information about the run.
        detail = (
            "benchmark_grid.csv not written by E4's collapsed smoke path "
            "(the manifest tags it full-only); nothing to judge at this profile"
        )
        results.append(
            GateResult("E4", "gate1_guard_count:benchmark_grid.csv", "N/A", detail)
        )
        results.append(
            GateResult("E4", "gate2_status:benchmark_grid.csv", "N/A", detail)
        )
        return results
    df = _load_csv(grid_path)
    results.append(_check_guard_column("E4", "benchmark_grid.csv", df))
    results.append(_check_status_column("E4", "benchmark_grid.csv", df))
    return results


def check_e5(out_dir: Path, *, profile: str | None = None) -> list[GateResult]:
    """E5 -- refractive-index sensitivity band. One environment-only
    provenance sidecar summing the guard count across the whole band; no
    per-row status or optimality is recorded for this experiment.

    Args:
        out_dir: The run's primary output directory.
        profile: `"smoke"` relaxes `gate1_guard_count` and `gate3_provenance`
            from FAIL to `N/A` when `e5_provenance.json` is ABSENT --
            `e5_index_sensitivity.py:871-889` (`_run_smoke_at`) returns before
            the sidecar write, and the manifest tags it `full`-only
            (P27-D-20). A sidecar that is PRESENT but bad still FAILs at every
            profile. `None` and `"full"` keep the pre-existing behaviour.

    Raises:
        ValueError: On an unknown profile.
    """
    _validate_profile(profile, caller="check_e5")
    sidecar_path = out_dir / "e5_provenance.json"
    if profile == "smoke" and not sidecar_path.exists():
        detail = (
            "e5_provenance.json not written by E5's collapsed smoke path "
            "(the manifest tags it full-only); nothing to judge at this profile"
        )
        results = [
            GateResult("E5", "gate1_guard_count:e5_provenance.json", "N/A", detail),
            GateResult("E5", "gate3_provenance:e5_provenance.json", "N/A", detail),
        ]
    else:
        record = _load_json(sidecar_path)
        results = _check_json_artifact(
            "E5",
            "e5_provenance.json",
            record,
            check_guard=True,
            check_optimality=False,
            require_water_index=True,
            water_index_keys=("n_true", "n_water"),
        )
    results.append(
        GateResult(
            "E5",
            "gate4_optimality",
            "N/A",
            "E5's committed artifacts record no per-stage optimality "
            "(record-only experiment; see plan 19.3-07)",
        )
    )
    results.append(
        GateResult(
            "E5",
            "gate2_status",
            "N/A",
            "index_sensitivity.csv carries no status column (record-only per plan 19.3-07)",
        )
    )
    return results


def check_e6(out_dir: Path, *, profile: str | None = None) -> list[GateResult]:
    """E6 -- index/layout/scale generalization sweep. Twelve per-configuration
    checkpoints plus the aggregated `generalization_sweep.csv`.

    Args:
        out_dir: The run's primary output directory.
        profile: `"smoke"` suppresses gate 4 over `e6_configs/*.json`: a
            collapsed smoke solve records no meaningful first-order
            optimality (P27-D-20). The gate is still EMITTED, as `N/A` naming
            that reason -- a suppressed gate must stay visible in the verdict
            block, never vanish. Gates 1 and 3 over the same record are
            unaffected. `None` and `"full"` keep the pre-existing behaviour.

    Raises:
        ValueError: On an unknown profile.
    """
    _validate_profile(profile, caller="check_e6")
    check_optimality = profile != "smoke"
    results: list[GateResult] = []
    configs_dir = out_dir / "e6_configs"
    config_paths = sorted(configs_dir.glob("*.json")) if configs_dir.exists() else []
    if not config_paths:
        for gate in ("gate1_guard_count", "gate3_provenance", "gate4_optimality"):
            results.append(
                GateResult(
                    "E6",
                    gate,
                    "FAIL",
                    f"no per-configuration checkpoint under {configs_dir}",
                )
            )
    for config_path in config_paths:
        record = _load_json(config_path)
        label = f"e6_configs/{config_path.name}"
        results += _check_json_artifact(
            "E6",
            label,
            record,
            check_guard=True,
            check_optimality=check_optimality,
            require_water_index=True,
        )
        if not check_optimality:
            results.append(
                GateResult(
                    "E6",
                    f"gate4_optimality:{label}",
                    "N/A",
                    f"{label}: a collapsed smoke solve records no meaningful "
                    "first-order optimality, so this gate cannot judge at the "
                    "smoke profile (it is suppressed, not deleted -- it FAILs "
                    "on the same record under full)",
                )
            )
    df = _load_csv(out_dir / "generalization_sweep.csv")
    results.append(_check_guard_column("E6", "generalization_sweep.csv", df))
    results.append(_check_status_column("E6", "generalization_sweep.csv", df))
    return results


def check_e7(out_dir: Path) -> list[GateResult]:
    """E7 -- shared-vs-per-camera interface ablation. Four per-arm direct-call
    benchmark records; `interface_ablation.csv` carries no status column."""
    results: list[GateResult] = []
    for arm in (
        "shared_fixed",
        "shared_refined",
        "percamera_fixed",
        "percamera_refined",
    ):
        filename = f"e7_benchmark_{arm}.json"
        record = _load_json(out_dir / filename)
        results += _check_json_artifact(
            "E7",
            filename,
            record,
            check_guard=True,
            check_optimality=True,
            require_water_index=True,
        )
    results.append(
        GateResult(
            "E7",
            "gate2_status",
            "N/A",
            "interface_ablation.csv carries no status column (record-only per plan 19.3-07)",
        )
    )
    return results


def check_band_csv(
    experiment: str,
    out_dir: Path,
    csv_name: str,
    sidecar_glob: str,
    band_sidecar: str | None = None,
) -> list[GateResult]:
    """Gate the `--seeds` band CSVs introduced by D-19.4-14 (SC-5a).

    A band exists to make a published number REGENERABLE: before this phase,
    MF-05's per-arm bands and MF-08's 97-178x ratio spread lived only in
    gitignored `seed_sweep_19_3/` output, so a reviewer had to take the summary
    tables on trust. The gate therefore checks the property that makes the
    artifact trustworthy -- that it really contains the N independent seeds its
    provenance claims -- not merely that a file appeared.

    D-260807-dcv: band mode must never overwrite the single-seed
    `e{1,7}_benchmark_*.json` production records, so the seeds a band run
    actually covers have nowhere to be recorded in them -- hence the
    band-owned sidecar (`band_sidecar`, e.g. `e1_seed_band_provenance.json`),
    which is preferred over the legacy `eN_benchmark_*.json` glob
    (`sidecar_glob`) when both are given. The legacy glob remains as a
    backwards-compatible fallback for any out_dir that predates the
    band-owned sidecar.

    Verdicts:
        N/A   the band CSV is absent (its stage has not run yet).
        FAIL  no `seed` column; or the count of DISTINCT seeds in the CSV
              disagrees with the length of `solver_config["seeds"]` recorded in
              the sidecar. A short band silently quoted as a 10-seed band is
              exactly the failure this catches.
        PASS  distinct-seed count matches the recorded seed list.

    Args:
        experiment: Experiment label, e.g. `"E7"`.
        out_dir: Root output directory.
        csv_name: Band CSV filename, e.g. `"interface_ablation_band.csv"`.
        sidecar_glob: Glob for the legacy provenance sidecars carrying
            `seeds` (the `eN_benchmark_*.json` fallback).
        band_sidecar: Exact filename of the band-owned provenance sidecar
            (e.g. `"e1_seed_band_provenance.json"`), checked FIRST when
            given. Not a glob -- `Path.glob` matches an exact filename
            pattern with no wildcards fine, so no second code path is
            needed.

    Returns:
        One `GateResult` for this band artifact.
    """
    csv_path = out_dir / csv_name
    gate = f"gate4_band:{csv_name}"
    if not csv_path.exists():
        return [
            GateResult(
                experiment,
                gate,
                "N/A",
                f"{csv_name} not present (its stage has not run yet)",
            )
        ]

    try:
        band = pd.read_csv(csv_path)
    except (OSError, ValueError) as exc:
        return [
            GateResult(
                experiment,
                gate,
                "FAIL",
                f"{csv_name} unreadable: {type(exc).__name__}: {exc}",
            )
        ]

    if "seed" not in band.columns:
        return [
            GateResult(
                experiment,
                gate,
                "FAIL",
                f"{csv_name} has no 'seed' column; a band CSV without it cannot be "
                "attributed to the seeds it claims to cover",
            )
        ]

    distinct = sorted({int(s) for s in band["seed"].tolist()})

    # Band-owned sidecar first (preferred, D-260807-dcv), then the legacy
    # eN_benchmark_*.json glob (backwards-compatible fallback).
    search_patterns = ([band_sidecar] if band_sidecar else []) + [sidecar_glob]

    recorded: list[int] | None = None
    sidecar_used: str | None = None
    for pattern in search_patterns:
        for path in sorted(out_dir.glob(pattern)):
            record = _load_json(path)
            if not isinstance(record, dict):
                continue
            seeds = record.get("solver_config", {}).get("seeds")
            if isinstance(seeds, list) and seeds:
                recorded = [int(s) for s in seeds]
                sidecar_used = path.name
                break
        if recorded is not None:
            break

    if recorded is None:
        return [
            GateResult(
                experiment,
                gate,
                "FAIL",
                f"{csv_name} exists with {len(distinct)} distinct seed(s) {distinct}, but no "
                f"sidecar matching '{sidecar_glob}' records solver_config['seeds'] -- the band "
                "cannot be verified against what was actually requested",
            )
        ]

    if len(distinct) != len(recorded):
        return [
            GateResult(
                experiment,
                gate,
                "FAIL",
                f"{csv_name} carries {len(distinct)} distinct seed(s) {distinct} but "
                f"{sidecar_used} records {len(recorded)} requested seed(s) {sorted(recorded)} -- "
                "a partial band must never be quoted as a full one",
            )
        ]

    return [
        GateResult(
            experiment,
            gate,
            "PASS",
            f"{csv_name}: {len(distinct)} distinct seed(s) {distinct} match "
            f"{sidecar_used}'s recorded seed list",
        )
    ]


# ---------------------------------------------------------------------------
# Phase 19.5's four new band gates (plan 19.5-09, COV-03/04/05/06/07).
#
# Each gate reads STATUS COUNTS or STRUCTURAL properties from the artifact
# itself -- never a process exit code -- matching this project's established
# rule that E4/E6 record a failure as a row and can still exit 0 (MF-07).
# ---------------------------------------------------------------------------

_E6_BAND_CSV = "generalization_sweep_band.csv"
_E6_BAND_SIDECAR = "e6_seed_band_provenance.json"
# SIX, not five. A five-seed unanimous sign test gives p = 0.031 one-sided but
# 0.0625 TWO-sided, so its significance would depend on which convention a
# reader applies -- the exact ambiguity that made plan 19.5-03 name its field
# `p_one_sided`. Six gives 0.031 under either convention. Raised to the user
# before the production launch on 2026-08-06 and approved with the runtime cost
# stated (the ceiling moved 26 h -> 30 h to pay for it). This constant stayed at
# 5 through that change and FAILed the run it was meant to certify.
# AUTHORITY: experiments/suite_expectations.json is the single source of truth
# for this band's shape (D-05). Keep this in step with that file's
# generalization_sweep_band.csv `rows.full`, which is configurations x seeds --
# 84 = 14 x 6 after D-40 dropped the scale axis. The coupling is a red test
# (tests/unit/test_expectations.py::TestShapeConstantReconciliation), not a plea.
_E6_EXPECTED_SEED_COUNT = 6
# NOT derived from the manifest and NOT changed: the `cameras` axis survives D-40.
_E6_EXPECTED_CAMERA_VALUES = (8, 12, 16)


def check_e6_seed_band(
    out_dir: Path, *, profile: str | None = None
) -> list[GateResult]:
    """COV-03/COV-04's E6 seed band: `generalization_sweep_band.csv` against
    `e6_seed_band_provenance.json`.

    Checks the CSV has exactly 5 distinct seeds contributing equal row
    counts, the `cameras` axis (COV-04) is present at all three camera
    counts, every row's `status` reads `"ok"` (a non-`"ok"` count is a FAIL
    naming the offending seed -- E6 exits 0 even when every configuration
    failed, MF-07), the sidecar's `solver_config["seeds"]` matches the CSV's
    distinct seeds, and the sidecar carries a `git_sha`.

    Args:
        out_dir: The run's primary output directory.
        profile: `"smoke"` makes the `cameras`-axis EXPECTATION
            profile-dependent -- a collapsed smoke band carries one camera
            count, so a short axis is `N/A` rather than FAIL (P27-D-20).
            `_E6_EXPECTED_CAMERA_VALUES` itself is NOT changed: that constant
            records that the axis survives P26-D-40, and it still governs at
            `full`. An absent `axis`/`axis_value` column pair stays FAIL at
            every profile. `None` and `"full"` keep the pre-existing
            behaviour.

    Raises:
        ValueError: On an unknown profile.
    """
    _validate_profile(profile, caller="check_e6_seed_band")
    csv_path = out_dir / _E6_BAND_CSV
    if not csv_path.exists():
        return [
            GateResult(
                "E6",
                "gate_e6_seed_band",
                "N/A",
                f"{_E6_BAND_CSV} not present (its stage has not run yet)",
            )
        ]

    try:
        band = pd.read_csv(csv_path)
    except (OSError, ValueError) as exc:
        return [
            GateResult(
                "E6",
                "gate_e6_seed_band:read",
                "FAIL",
                f"{_E6_BAND_CSV} unreadable: {type(exc).__name__}: {exc}",
            )
        ]

    if "seed" not in band.columns:
        return [
            GateResult(
                "E6",
                "gate_e6_seed_band:seed_column",
                "FAIL",
                f"{_E6_BAND_CSV} has no 'seed' column",
            )
        ]

    results: list[GateResult] = []
    distinct_seeds = sorted({int(s) for s in band["seed"].tolist()})

    if len(distinct_seeds) != _E6_EXPECTED_SEED_COUNT:
        results.append(
            GateResult(
                "E6",
                "gate_e6_seed_band:seed_count",
                "FAIL",
                f"{_E6_BAND_CSV} carries {len(distinct_seeds)} distinct seed(s) "
                f"{distinct_seeds}, expected exactly {_E6_EXPECTED_SEED_COUNT}",
            )
        )
    else:
        results.append(
            GateResult(
                "E6",
                "gate_e6_seed_band:seed_count",
                "PASS",
                f"{_E6_BAND_CSV}: {_E6_EXPECTED_SEED_COUNT} distinct seeds "
                f"{distinct_seeds}",
            )
        )

    per_seed_counts = band.groupby("seed").size()
    if per_seed_counts.nunique() > 1:
        results.append(
            GateResult(
                "E6",
                "gate_e6_seed_band:row_count",
                "FAIL",
                f"row counts differ per seed: {per_seed_counts.to_dict()} -- a "
                "partial seed would silently under-report",
            )
        )
    else:
        rows_per_seed = int(per_seed_counts.iloc[0]) if len(per_seed_counts) else 0
        results.append(
            GateResult(
                "E6",
                "gate_e6_seed_band:row_count",
                "PASS",
                f"row count = {len(band)}, uniform across seeds "
                f"({rows_per_seed} rows/seed)",
            )
        )

    if {"axis", "axis_value"}.issubset(band.columns):
        cameras_rows = band[band["axis"] == "cameras"]
        cameras_values = sorted({int(v) for v in cameras_rows["axis_value"].tolist()})
        missing = [v for v in _E6_EXPECTED_CAMERA_VALUES if v not in cameras_values]
        if missing and profile == "smoke":
            # The axis EXPECTATION is profile-dependent; the constant is not.
            results.append(
                GateResult(
                    "E6",
                    "gate_e6_seed_band:cameras_axis",
                    "N/A",
                    f"cameras axis present at {cameras_values}; the collapsed "
                    f"smoke band does not run {missing}, so the production "
                    "axis cannot be asserted at this profile (it still FAILs "
                    "on the same CSV under full)",
                )
            )
        elif missing:
            results.append(
                GateResult(
                    "E6",
                    "gate_e6_seed_band:cameras_axis",
                    "FAIL",
                    f"cameras axis missing value(s) {missing}; found {cameras_values}",
                )
            )
        else:
            results.append(
                GateResult(
                    "E6",
                    "gate_e6_seed_band:cameras_axis",
                    "PASS",
                    f"cameras axis present at {cameras_values}",
                )
            )
    else:
        results.append(
            GateResult(
                "E6",
                "gate_e6_seed_band:cameras_axis",
                "FAIL",
                f"{_E6_BAND_CSV} has no 'axis'/'axis_value' columns to locate "
                "the cameras axis",
            )
        )

    if "status" in band.columns:
        status_by_seed = (
            band.groupby("seed")["status"].value_counts().unstack(fill_value=0)
        )
        non_ok_seeds: dict[int, dict[str, int]] = {}
        for seed_val, row in status_by_seed.iterrows():
            non_ok = {
                str(status): int(count)
                for status, count in row.items()
                if status != "ok" and count > 0
            }
            if non_ok:
                non_ok_seeds[int(seed_val)] = non_ok
        if non_ok_seeds:
            results.append(
                GateResult(
                    "E6",
                    "gate_e6_seed_band:status_counts",
                    "FAIL",
                    f"non-'ok' status counts found: {non_ok_seeds} -- read from "
                    "the CSV's own 'status' column, never the process exit code",
                )
            )
        else:
            results.append(
                GateResult(
                    "E6",
                    "gate_e6_seed_band:status_counts",
                    "PASS",
                    f"every row status=='ok' across all {len(distinct_seeds)} seeds",
                )
            )
    else:
        results.append(
            GateResult(
                "E6",
                "gate_e6_seed_band:status_counts",
                "FAIL",
                f"{_E6_BAND_CSV} has no 'status' column -- cannot confirm "
                "convergence per row (E6 exits 0 even when every "
                "configuration fails)",
            )
        )

    sidecar = _load_json(out_dir / _E6_BAND_SIDECAR)
    if sidecar is None or "_load_error" in sidecar:
        results.append(
            GateResult(
                "E6",
                "gate_e6_seed_band:sidecar",
                "FAIL",
                f"{_E6_BAND_SIDECAR} missing or unreadable",
            )
        )
        return results

    recorded_seeds = (sidecar.get("solver_config") or {}).get("seeds")
    if not isinstance(recorded_seeds, list):
        results.append(
            GateResult(
                "E6",
                "gate_e6_seed_band:sidecar_seeds",
                "FAIL",
                f"{_E6_BAND_SIDECAR} carries no solver_config['seeds'] list",
            )
        )
    elif sorted({int(s) for s in recorded_seeds}) != distinct_seeds:
        results.append(
            GateResult(
                "E6",
                "gate_e6_seed_band:sidecar_seeds",
                "FAIL",
                f"sidecar solver_config['seeds']={sorted(recorded_seeds)} does "
                f"not match the CSV's distinct seeds {distinct_seeds}",
            )
        )
    else:
        results.append(
            GateResult(
                "E6",
                "gate_e6_seed_band:sidecar_seeds",
                "PASS",
                "sidecar solver_config['seeds'] matches the CSV's distinct seeds",
            )
        )

    git_sha = sidecar.get("git_sha") or (sidecar.get("environment") or {}).get(
        "git_sha"
    )
    if not git_sha:
        results.append(
            GateResult(
                "E6",
                "gate_e6_seed_band:sidecar_git_sha",
                "FAIL",
                f"{_E6_BAND_SIDECAR} carries no git_sha",
            )
        )
    else:
        results.append(
            GateResult(
                "E6",
                "gate_e6_seed_band:sidecar_git_sha",
                "PASS",
                f"{_E6_BAND_SIDECAR} git_sha={git_sha}",
            )
        )

    return results


_E5_BAND_CSV = "index_sensitivity_seed_band.csv"
_E5_BAND_SIDECAR = "e5_seed_band_provenance.json"
# Six for the same reason as _E6_EXPECTED_SEED_COUNT above -- E5's band runs the
# same seed list (42-47).
# AUTHORITY: experiments/suite_expectations.json. Keep in step with that file's
# index_sensitivity_seed_band.csv `rows.full` (66 = 11 configurations x 6 seeds).
_E5_EXPECTED_SEED_COUNT = 6


def check_e5_seed_band(out_dir: Path) -> list[GateResult]:
    """COV-05's E5 seed band: `index_sensitivity_seed_band.csv` against
    `e5_seed_band_provenance.json`.

    Checks the CSV has exactly 5 distinct seeds, and the sidecar carries
    BOTH `solver_config["seeds"]` AND the pre-existing `n_assumed_band`,
    plus a non-empty `scope` string -- the D-19.5-05 distinguishability
    requirement (this band bounds seed noise, NOT index sensitivity) stated
    in the artifact itself, enforced here at the gate.
    """
    csv_path = out_dir / _E5_BAND_CSV
    if not csv_path.exists():
        return [
            GateResult(
                "E5",
                "gate_e5_seed_band",
                "N/A",
                f"{_E5_BAND_CSV} not present (its stage has not run yet)",
            )
        ]

    try:
        band = pd.read_csv(csv_path)
    except (OSError, ValueError) as exc:
        return [
            GateResult(
                "E5",
                "gate_e5_seed_band:read",
                "FAIL",
                f"{_E5_BAND_CSV} unreadable: {type(exc).__name__}: {exc}",
            )
        ]

    if "seed" not in band.columns:
        return [
            GateResult(
                "E5",
                "gate_e5_seed_band:seed_column",
                "FAIL",
                f"{_E5_BAND_CSV} has no 'seed' column",
            )
        ]

    results: list[GateResult] = []
    distinct_seeds = sorted({int(s) for s in band["seed"].tolist()})

    if len(distinct_seeds) != _E5_EXPECTED_SEED_COUNT:
        results.append(
            GateResult(
                "E5",
                "gate_e5_seed_band:seed_count",
                "FAIL",
                f"{_E5_BAND_CSV} carries {len(distinct_seeds)} distinct seed(s) "
                f"{distinct_seeds}, expected exactly {_E5_EXPECTED_SEED_COUNT}",
            )
        )
    else:
        results.append(
            GateResult(
                "E5",
                "gate_e5_seed_band:seed_count",
                "PASS",
                f"{_E5_BAND_CSV}: {_E5_EXPECTED_SEED_COUNT} distinct seeds "
                f"{distinct_seeds}",
            )
        )

    sidecar = _load_json(out_dir / _E5_BAND_SIDECAR)
    if sidecar is None or "_load_error" in sidecar:
        results.append(
            GateResult(
                "E5",
                "gate_e5_seed_band:sidecar",
                "FAIL",
                f"{_E5_BAND_SIDECAR} missing or unreadable",
            )
        )
        return results

    solver_config = sidecar.get("solver_config") or {}
    if "seeds" not in solver_config:
        results.append(
            GateResult(
                "E5",
                "gate_e5_seed_band:sidecar_seeds",
                "FAIL",
                f"{_E5_BAND_SIDECAR} carries no solver_config['seeds']",
            )
        )
    else:
        results.append(
            GateResult(
                "E5",
                "gate_e5_seed_band:sidecar_seeds",
                "PASS",
                f"{_E5_BAND_SIDECAR} carries solver_config['seeds']",
            )
        )

    if "n_assumed_band" not in sidecar and "n_assumed_band" not in solver_config:
        results.append(
            GateResult(
                "E5",
                "gate_e5_seed_band:n_assumed_band",
                "FAIL",
                f"{_E5_BAND_SIDECAR} carries 'seeds' but no 'n_assumed_band' -- "
                "the D-19.5-05 distinguishability requirement (this band "
                "varies seed, not the assumed index) is not stated in the "
                "artifact",
            )
        )
    else:
        results.append(
            GateResult(
                "E5",
                "gate_e5_seed_band:n_assumed_band",
                "PASS",
                f"{_E5_BAND_SIDECAR} carries n_assumed_band alongside seeds",
            )
        )

    scope = sidecar.get("scope") or solver_config.get("scope")
    if not scope:
        results.append(
            GateResult(
                "E5",
                "gate_e5_seed_band:scope",
                "FAIL",
                f"{_E5_BAND_SIDECAR} carries no non-empty 'scope' string",
            )
        )
    else:
        results.append(
            GateResult(
                "E5",
                "gate_e5_seed_band:scope",
                "PASS",
                f"{_E5_BAND_SIDECAR} scope: {scope!r}",
            )
        )

    return results


_E2_BAND_SCOPE_JSON = "e2_band_scope.json"
_E2_METRICS_FILENAME = "real_rig_metrics.json"
_E2_METRICS_RTOL = 1e-6
_E2_SEED_DIR_RE = re.compile(r"seed_(\d+)_e2_out")
# AUTHORITY: experiments/suite_expectations.json. Keep in step with the
# e2_band stage's seed list; the manifest's e2_band entry is where that list is
# written down.
_E2_EXPECTED_RECORD_COUNT = 3


def _numeric_mismatches(
    expected: dict, actual: dict, *, rtol: float, path: str = ""
) -> list[str]:
    """Recursively compare numeric leaves shared by `expected` and `actual`.

    Keys present in only one dict are ignored (this is a reproduction check
    on shared numeric quantities, not a full schema diff). The `provenance`
    key is skipped entirely -- it documents WHERE each number came from, not
    a number itself.
    """
    mismatches: list[str] = []
    for key, expected_value in expected.items():
        if key == "provenance" or key not in actual:
            continue
        actual_value = actual[key]
        full_path = f"{path}.{key}" if path else key
        if isinstance(expected_value, dict) and isinstance(actual_value, dict):
            mismatches += _numeric_mismatches(
                expected_value, actual_value, rtol=rtol, path=full_path
            )
        elif isinstance(expected_value, list) and isinstance(actual_value, list):
            for i, (e, a) in enumerate(zip(expected_value, actual_value)):
                if isinstance(e, int | float) and isinstance(a, int | float):
                    if not math.isclose(e, a, rel_tol=rtol, abs_tol=1e-9):
                        mismatches.append(f"{full_path}[{i}]: {e} != {a}")
        elif isinstance(expected_value, int | float) and isinstance(
            actual_value, int | float
        ):
            if not math.isclose(
                expected_value, actual_value, rel_tol=rtol, abs_tol=1e-9
            ):
                mismatches.append(f"{full_path}: {expected_value} != {actual_value}")
    return mismatches


def check_e2_band(
    band_dir: Path,
    committed_metrics_path: Path | None = None,
) -> list[GateResult]:
    """COV-07's E2 calibration/holdout split-variance band.

    `band_dir` is the directory `--emit-band-configs`/`--band-dir` wrote
    into (e.g. `experiments/results_e2_band/`), NOT `experiments/results/`
    itself -- `emit_seed_variant_configs`'s release-tree write refusal means
    this band's per-seed metric records live in their own isolated
    directory, under `seed_{seed}_e2_out/real_rig_metrics.json` (plan
    19.5-07's exact `--out` naming).

    Checks: exactly 3 per-seed metric records exist; their metric values are
    NOT byte-identical to each other (identical values mean the seed never
    reached the split -- RESEARCH Pitfall 5's stated warning sign); the
    seed-42 record matches `committed_metrics_path` within a stated
    tolerance; `e2_band_scope.json` carries both "split variance" and "NOT
    measurement variance" (D-19.5-05).

    Args:
        band_dir: The E2 band directory.
        committed_metrics_path: The committed production
            `real_rig_metrics.json` to compare seed 42 against. Defaults to
            `experiments/results/real_rig_metrics.json`.
    """
    if committed_metrics_path is None:
        committed_metrics_path = Path("experiments/results/real_rig_metrics.json")

    if not band_dir.exists():
        return [
            GateResult(
                "E2",
                "gate_e2_band",
                "N/A",
                f"{band_dir} not present (its stage has not run yet)",
            )
        ]

    results: list[GateResult] = []
    records: dict[int, dict] = {}
    for seed_dir in sorted(band_dir.glob("seed_*_e2_out")):
        metrics_path = seed_dir / _E2_METRICS_FILENAME
        record = _load_json(metrics_path)
        if record is None or "_load_error" in record:
            results.append(
                GateResult(
                    "E2",
                    f"gate_e2_band:{seed_dir.name}",
                    "FAIL",
                    f"{seed_dir.name}/{_E2_METRICS_FILENAME} missing or unreadable",
                )
            )
            continue
        match = _E2_SEED_DIR_RE.match(seed_dir.name)
        if match is not None:
            records[int(match.group(1))] = record

    if len(records) != _E2_EXPECTED_RECORD_COUNT:
        results.append(
            GateResult(
                "E2",
                "gate_e2_band:record_count",
                "FAIL",
                f"found {len(records)} per-seed metric record(s) under "
                f"{band_dir}, expected exactly {_E2_EXPECTED_RECORD_COUNT}",
            )
        )
    else:
        results.append(
            GateResult(
                "E2",
                "gate_e2_band:record_count",
                "PASS",
                f"{_E2_EXPECTED_RECORD_COUNT} per-seed metric records found: "
                f"seeds {sorted(records)}",
            )
        )

    if len(records) >= 2:
        distinct_payloads = {json.dumps(r, sort_keys=True) for r in records.values()}
        if len(distinct_payloads) == 1:
            results.append(
                GateResult(
                    "E2",
                    "gate_e2_band:not_identical",
                    "FAIL",
                    "all per-seed metric records are byte-identical -- the "
                    "split never reached a different holdout partition "
                    "(RESEARCH Pitfall 5)",
                )
            )
        else:
            results.append(
                GateResult(
                    "E2",
                    "gate_e2_band:not_identical",
                    "PASS",
                    f"{len(distinct_payloads)} distinct metric record(s) "
                    f"across {len(records)} seeds",
                )
            )

    if 42 in records:
        committed = _load_json(committed_metrics_path)
        if committed is None or "_load_error" in committed:
            results.append(
                GateResult(
                    "E2",
                    "gate_e2_band:seed42_reproduction",
                    "FAIL",
                    f"committed {committed_metrics_path} missing or unreadable",
                )
            )
        else:
            mismatches = _numeric_mismatches(
                committed, records[42], rtol=_E2_METRICS_RTOL
            )
            if mismatches:
                results.append(
                    GateResult(
                        "E2",
                        "gate_e2_band:seed42_reproduction",
                        "FAIL",
                        f"seed-42 band record diverges from the committed "
                        f"{committed_metrics_path}: {mismatches}",
                    )
                )
            else:
                results.append(
                    GateResult(
                        "E2",
                        "gate_e2_band:seed42_reproduction",
                        "PASS",
                        f"seed-42 band record matches {committed_metrics_path} "
                        f"within rtol={_E2_METRICS_RTOL}",
                    )
                )

    scope = _load_json(band_dir / _E2_BAND_SCOPE_JSON)
    if scope is None or "_load_error" in scope:
        results.append(
            GateResult(
                "E2",
                "gate_e2_band:scope",
                "FAIL",
                f"{_E2_BAND_SCOPE_JSON} missing or unreadable under {band_dir}",
            )
        )
    else:
        scope_text = str(scope.get("scope", ""))
        if "split variance" in scope_text and "NOT measurement variance" in scope_text:
            results.append(
                GateResult(
                    "E2",
                    "gate_e2_band:scope",
                    "PASS",
                    f"{_E2_BAND_SCOPE_JSON} scope states both required phrases",
                )
            )
        else:
            results.append(
                GateResult(
                    "E2",
                    "gate_e2_band:scope",
                    "FAIL",
                    f"{_E2_BAND_SCOPE_JSON} scope missing required phrase(s): "
                    f"{scope_text!r}",
                )
            )

    return results


_E4_REPEAT_CSV = "benchmark_grid_repeat.csv"
# AUTHORITY: experiments/suite_expectations.json. Keep in step with that file's
# benchmark_grid_repeat.csv `rows.full` (6 = 2 repeats x these 3 cells).
_E4_REPEAT_CELLS = ((8, 100), (12, 100), (16, 100))
_E4_REPEAT_SECONDS_COLUMN = "seconds_stage3_interface_optimization"
_E4_REPEAT_NFEV_COLUMN = "nfev_stage3_interface_optimization"


def check_e4_repeat(out_dir: Path) -> list[GateResult]:
    """COV-06's E4 timing repeat: `benchmark_grid_repeat.csv`.

    Checks: the CSV has 6 rows over the three `REPEAT_CELLS` and two
    `repeat` values; every row with a non-null
    `seconds_stage3_interface_optimization` has a non-null
    `nfev_stage3_interface_optimization` (MF-03 -- wall-clock without nfev
    beside it is unreportable).
    """
    csv_path = out_dir / _E4_REPEAT_CSV
    if not csv_path.exists():
        return [
            GateResult(
                "E4",
                "gate_e4_repeat",
                "N/A",
                f"{_E4_REPEAT_CSV} not present (its stage has not run yet)",
            )
        ]

    try:
        df = pd.read_csv(csv_path)
    except (OSError, ValueError) as exc:
        return [
            GateResult(
                "E4",
                "gate_e4_repeat:read",
                "FAIL",
                f"{_E4_REPEAT_CSV} unreadable: {type(exc).__name__}: {exc}",
            )
        ]

    results: list[GateResult] = []

    if len(df) != 6:
        results.append(
            GateResult(
                "E4",
                "gate_e4_repeat:row_count",
                "FAIL",
                f"{_E4_REPEAT_CSV} has {len(df)} row(s), expected 6 (3 cells x "
                "2 repeats)",
            )
        )
    else:
        results.append(
            GateResult(
                "E4", "gate_e4_repeat:row_count", "PASS", f"{_E4_REPEAT_CSV}: 6 rows"
            )
        )

    if {"n_cameras", "n_frames"}.issubset(df.columns):
        cells = sorted({(int(r.n_cameras), int(r.n_frames)) for r in df.itertuples()})
        missing_cells = [c for c in _E4_REPEAT_CELLS if c not in cells]
        if missing_cells:
            results.append(
                GateResult(
                    "E4",
                    "gate_e4_repeat:cells",
                    "FAIL",
                    f"missing repeat cell(s) {missing_cells}; found {cells}",
                )
            )
        else:
            results.append(
                GateResult(
                    "E4",
                    "gate_e4_repeat:cells",
                    "PASS",
                    f"all three repeat cells present: {cells}",
                )
            )
    else:
        results.append(
            GateResult(
                "E4",
                "gate_e4_repeat:cells",
                "FAIL",
                f"{_E4_REPEAT_CSV} missing 'n_cameras'/'n_frames' column(s)",
            )
        )

    if "repeat" in df.columns:
        distinct_repeats = sorted({int(r) for r in df["repeat"].tolist()})
        if distinct_repeats != [1, 2]:
            results.append(
                GateResult(
                    "E4",
                    "gate_e4_repeat:repeat_labels",
                    "FAIL",
                    f"expected repeat values [1, 2], found {distinct_repeats}",
                )
            )
        else:
            results.append(
                GateResult(
                    "E4",
                    "gate_e4_repeat:repeat_labels",
                    "PASS",
                    "repeat labels [1, 2] present",
                )
            )
    else:
        results.append(
            GateResult(
                "E4",
                "gate_e4_repeat:repeat_labels",
                "FAIL",
                f"{_E4_REPEAT_CSV} has no 'repeat' column",
            )
        )

    if {_E4_REPEAT_SECONDS_COLUMN, _E4_REPEAT_NFEV_COLUMN}.issubset(df.columns):
        bad_rows = df[
            df[_E4_REPEAT_SECONDS_COLUMN].notna() & df[_E4_REPEAT_NFEV_COLUMN].isna()
        ]
        if len(bad_rows) > 0:
            results.append(
                GateResult(
                    "E4",
                    "gate_e4_repeat:nfev_beside_wallclock",
                    "FAIL",
                    f"{len(bad_rows)} row(s) carry a wall-clock "
                    f"{_E4_REPEAT_SECONDS_COLUMN} with no "
                    f"{_E4_REPEAT_NFEV_COLUMN} (MF-03)",
                )
            )
        else:
            results.append(
                GateResult(
                    "E4",
                    "gate_e4_repeat:nfev_beside_wallclock",
                    "PASS",
                    f"every row with a non-null {_E4_REPEAT_SECONDS_COLUMN} has "
                    f"a non-null {_E4_REPEAT_NFEV_COLUMN}",
                )
            )
    else:
        results.append(
            GateResult(
                "E4",
                "gate_e4_repeat:nfev_beside_wallclock",
                "FAIL",
                f"{_E4_REPEAT_CSV} missing {_E4_REPEAT_SECONDS_COLUMN!r} or "
                f"{_E4_REPEAT_NFEV_COLUMN!r} column",
            )
        )

    return results


def _collect_all_json_paths(out_dir: Path) -> list[Path]:
    """Every JSON artifact this run's gates read, for the cross-artifact
    git_sha consistency check."""
    paths: list[Path] = []
    for pattern in (
        "e1_benchmark_*.json",
        "e3_provenance.json",
        "e5_provenance.json",
        "e6_provenance.json",
        "e7_benchmark_*.json",
    ):
        paths.extend(sorted(out_dir.glob(pattern)))
    e4_cells = out_dir / "e4_cells"
    if e4_cells.exists():
        paths.extend(sorted(e4_cells.glob("*/benchmark.json")))
    e6_configs = out_dir / "e6_configs"
    if e6_configs.exists():
        paths.extend(sorted(e6_configs.glob("*.json")))
    return paths


def _collect_artifact_shas(out_dir: Path) -> dict[str, list[str]]:
    """Map every distinct `environment.git_sha` under `out_dir` to the artifacts
    carrying it.

    Factored out of `_check_git_sha_consistency` so the run-manifest gate can
    compare against the SAME sha set rather than re-deriving one. D-21 is
    explicit that Gate 3 already establishes sha agreement and does it better
    than a per-experiment assertion, so the manifest check reuses it.
    """
    shas: dict[str, list[str]] = {}
    for path in _collect_all_json_paths(out_dir):
        record = _load_json(path)
        if record is None or "_load_error" in record:
            continue
        sha = (record.get("environment") or {}).get("git_sha")
        if sha:
            shas.setdefault(sha, []).append(str(path.relative_to(out_dir)))
    return shas


def _check_git_sha_consistency(out_dir: Path) -> GateResult:
    """Gate 3's cross-artifact form: every git_sha found across the WHOLE run
    must be identical. This is the machine-checkable form of "commit nothing
    while a run is in flight" -- a split sha means exactly that happened.
    """
    shas = _collect_artifact_shas(out_dir)

    if len(shas) <= 1:
        only_sha = next(iter(shas), None)
        detail = (
            f"every artifact carries the same git_sha ({only_sha})"
            if only_sha
            else "no git_sha values found across any artifact to compare"
        )
        return GateResult("ALL", "gate3_git_sha_consistency", "PASS", detail)

    _MAX_SHOWN = 3
    parts = []
    for sha, files in shas.items():
        shown = files[:_MAX_SHOWN]
        suffix = "..." if len(files) > _MAX_SHOWN else ""
        parts.append(f"{sha}: {shown}{suffix}")
    detail = (
        "artifacts carry DIFFERENT git_sha values -- something was committed while the "
        "queue's run was in flight (" + "; ".join(parts) + ")"
    )
    return GateResult("ALL", "gate3_git_sha_consistency", "FAIL", detail)


def _check_run_manifest(out_dir: Path) -> list[GateResult]:
    """Gate 3's suite-level form (DRIVER-02, D-21): verify the run manifest.

    Four assertions, ALL of them hard FAIL and never "not applicable":

        1. `run_manifest.json` exists under `out_dir` and parses.
        2. Every name in `REQUIRED_MANIFEST_FIELDS` is present and non-null.
        3. Its `git_sha` agrees with the single sha `_check_git_sha_consistency`
           already establishes across the run's artifacts.
        4. The working tree was NOT dirty when the run started.

    A missing manifest is reported FAIL rather than skipped, on purpose. The todo
    DRIVER-02 comes from is explicit: a provenance mismatch that only warns is a
    provenance mismatch that ships, and an absent manifest is the loudest
    mismatch there is -- it is a run nobody can attribute to a commit.

    Note on assertion 4: dirtiness is recorded post-hoc only. D-47 cut the
    dirty-tree pre-flight REFUSAL because `experiments/results/` is tracked, so
    the run dirties its own tree and a refusal would kill every resume after the
    first crash. A gate verdict can never kill a run.
    """
    gate_prefix = "gate3_run_manifest"
    path = out_dir / RUN_MANIFEST_FILENAME
    manifest = _load_json(path)

    if manifest is None:
        return [
            GateResult(
                "ALL",
                f"{gate_prefix}_present",
                "FAIL",
                f"no {RUN_MANIFEST_FILENAME} under {out_dir} -- this run cannot be "
                "attributed to a commit or a machine (DRIVER-02, D-19)",
            )
        ]
    if "_load_error" in manifest:
        return [
            GateResult(
                "ALL",
                f"{gate_prefix}_present",
                "FAIL",
                f"{RUN_MANIFEST_FILENAME} could not be parsed: "
                f"{manifest['_load_error']}",
            )
        ]

    results = [
        GateResult(
            "ALL",
            f"{gate_prefix}_present",
            "PASS",
            f"{RUN_MANIFEST_FILENAME} found and parsed",
        )
    ]

    # 2. Required-field completeness. The field list is IMPORTED from the
    # emitter -- a second copy here is exactly the drift D-05 exists to prevent.
    null_fields = sorted(
        name for name in REQUIRED_MANIFEST_FIELDS if manifest.get(name) is None
    )
    if null_fields:
        results.append(
            GateResult(
                "ALL",
                f"{gate_prefix}_fields",
                "FAIL",
                "required manifest fields are missing or null: "
                + ", ".join(null_fields),
            )
        )
    else:
        results.append(
            GateResult(
                "ALL",
                f"{gate_prefix}_fields",
                "PASS",
                f"all {len(REQUIRED_MANIFEST_FIELDS)} required environment fields "
                "are present and non-null",
            )
        )

    # 3. Agreement with the sha set Gate 3 already collects.
    manifest_sha = manifest.get("git_sha")
    artifact_shas = _collect_artifact_shas(out_dir)
    disagreeing = sorted(sha for sha in artifact_shas if sha != manifest_sha)
    if not artifact_shas:
        # An empty set cannot disagree. Covering an empty tree is the
        # completeness gate's job, not Gate 3's -- do not widen this here.
        results.append(
            GateResult(
                "ALL",
                f"{gate_prefix}_git_sha",
                "PASS",
                f"manifest git_sha is {manifest_sha}; no artifact carries a "
                "git_sha to compare against",
            )
        )
    elif disagreeing:
        results.append(
            GateResult(
                "ALL",
                f"{gate_prefix}_git_sha",
                "FAIL",
                f"manifest git_sha ({manifest_sha}) disagrees with the sha(s) the "
                f"artifacts carry ({', '.join(disagreeing)}) -- the manifest does "
                "not describe the code that produced these artifacts",
            )
        )
    else:
        results.append(
            GateResult(
                "ALL",
                f"{gate_prefix}_git_sha",
                "PASS",
                f"manifest git_sha matches every artifact ({manifest_sha})",
            )
        )

    # 4. Dirty-tree state.
    git_dirty = manifest.get("git_dirty")
    if git_dirty is None:
        results.append(
            GateResult(
                "ALL",
                f"{gate_prefix}_clean_tree",
                "FAIL",
                "manifest records no git_dirty state, so the run cannot be shown "
                "to have come from a committed tree",
            )
        )
    elif git_dirty:
        results.append(
            GateResult(
                "ALL",
                f"{gate_prefix}_clean_tree",
                "FAIL",
                "the working tree was DIRTY when this run started "
                f"(git_describe: {manifest.get('git_describe')}) -- the recorded "
                "git_sha does not fully describe the code that ran",
            )
        )
    else:
        results.append(
            GateResult(
                "ALL",
                f"{gate_prefix}_clean_tree",
                "PASS",
                "the working tree was clean when this run started",
            )
        )

    return results


def run_all_gates(
    out_dir: Path, *, stage: str | None = None, profile: str | None = None
) -> list[GateResult]:
    """Run every gate over every experiment's artifacts under `out_dir`.

    Args:
        out_dir: Root output directory (e.g. `experiments/results/`).
        stage: Restrict the completeness gate to one stage's expected
            artifacts. Ignored when `profile` is not supplied.
        profile: The expectation profile (`"smoke"` or `"full"`). It selects
            the completeness gate -- `None`, the default, skips that gate
            entirely -- and, since P27-D-20, is also threaded into `check_e4`,
            `check_e5`, `check_e6` and `check_e6_seed_band`, where `"smoke"`
            turns four assertions a collapsed smoke run cannot satisfy from
            FAIL into a VISIBLE `N/A`. Nothing is suppressed at `"full"` or at
            `None`, so no pre-existing invocation changes behaviour.

    Returns:
        The full list of `GateResult`s across all six experiments plus the
        one cross-artifact git_sha-consistency check.
    """
    results: list[GateResult] = []
    results += check_e1(out_dir)
    results += check_e3(out_dir)
    results += check_e4(out_dir, profile=profile)
    results += check_e5(out_dir, profile=profile)
    results += check_e6(out_dir, profile=profile)
    results += check_e7(out_dir)
    # D-19.4-14's band artifacts. Only E7 and E1 have bands this phase -- E4 and
    # E6 bands cost ~39 h together and neither carries an accuracy claim, so
    # they are a Deferred Idea, not an omission.
    results += check_band_csv(
        "E7",
        out_dir,
        "interface_ablation_band.csv",
        "e7_benchmark_*.json",
        band_sidecar="e7_seed_band_provenance.json",
    )
    results += check_band_csv(
        "E1",
        out_dir,
        "exp1_band.csv",
        "e1_benchmark_*.json",
        band_sidecar="e1_seed_band_provenance.json",
    )
    # E1's SECOND band artifact: the parameter-level frame, keyed
    # (seed, camera, model) rather than (seed, test_depth_m, model). Same band,
    # same seeds, same sidecar -- only the CSV name differs, so check_band_csv
    # is reused as-is rather than widened.
    results += check_band_csv(
        "E1",
        out_dir,
        "exp1_parameter_band.csv",
        "e1_benchmark_*.json",
        band_sidecar="e1_seed_band_provenance.json",
    )
    # Phase 19.5's four new band gates (plan 19.5-09, COV-03/04/05/06/07).
    # check_e6_seed_band/check_e5_seed_band/check_e4_repeat all read directly
    # under out_dir. check_e2_band's artifacts live under an ISOLATED sibling
    # directory (out_dir.parent / "results_e2_band"), not out_dir itself --
    # emit_seed_variant_configs refuses to write into the release tree, and
    # this queue keeps the band in-repo but out of out_dir's own tree so a
    # `--check`/gate run against out_dir never confuses band output with the
    # single production run's own artifacts.
    results += check_e6_seed_band(out_dir, profile=profile)
    results += check_e5_seed_band(out_dir)
    results += check_e4_repeat(out_dir)
    results += check_e2_band(
        out_dir.parent / "results_e2_band",
        committed_metrics_path=out_dir / "real_rig_metrics.json",
    )
    results.append(_check_git_sha_consistency(out_dir))
    # DRIVER-02 / D-21: the suite-level run manifest, all hard FAIL.
    results += _check_run_manifest(out_dir)
    # DRIVER-01 / D-04: the completeness gate, last, and only when a profile
    # selects it. Every gate above judges artifacts it FINDS; this one is the
    # only one that notices an artifact that was never produced (F-001).
    if profile is not None:
        results += check_completeness(out_dir, profile=profile, stage=stage)
    return results


def build_arg_parser() -> argparse.ArgumentParser:
    """Build this script's CLI parser.

    `out_dir` is positional and unchanged. `--profile` and `--stage` are both
    OPTIONAL so every pre-existing call site -- including `rerun_19_5.sh:257`
    and its successor in the new driver -- keeps working unchanged.
    """
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "out_dir",
        type=Path,
        help="Output directory containing the re-run's artifacts (e.g. experiments/results/).",
    )
    parser.add_argument(
        "--profile",
        choices=PROFILES,
        default=None,
        help=(
            "Also run the completeness gate under this expectation profile. "
            "'smoke' asserts artifact existence only; 'full' asserts row "
            "counts. Omitted: the completeness gate does not run."
        ),
    )
    parser.add_argument(
        "--stage",
        default=None,
        help=(
            "Restrict the completeness gate to one stage id from "
            "experiments/suite_expectations.json. Omitted: the end-of-run "
            "roll-up over the whole manifest. Ignored without --profile."
        ),
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    """CLI entry point for `python experiments/check_rerun_gates.py <out_dir>`."""
    args = build_arg_parser().parse_args(argv)
    out_dir = Path(args.out_dir).resolve()
    results = run_all_gates(out_dir, stage=args.stage, profile=args.profile)

    for result in results:
        print(
            f"[{result.verdict:4s}] {result.experiment:3s} {result.gate:45s} {result.detail}"
        )

    n_pass = sum(1 for r in results if r.verdict == "PASS")
    n_na = sum(1 for r in results if r.verdict == "N/A")
    n_fail = sum(1 for r in results if r.verdict == "FAIL")
    print()
    print(f"TOTAL: {n_pass} PASS, {n_na} N/A, {n_fail} FAIL")
    return 1 if n_fail else 0


if __name__ == "__main__":
    sys.exit(main())
