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
                               still running.
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
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

import pandas as pd

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
        if count is None:
            results.append(
                GateResult(
                    experiment,
                    f"gate1_guard_count:{label}",
                    "FAIL",
                    f"{label}: no {_GUARD_COLUMN!r} field found (cannot confirm zero)",
                )
            )
        elif count == 0:
            results.append(
                GateResult(
                    experiment,
                    f"gate1_guard_count:{label}",
                    "PASS",
                    f"{label}: count=0",
                )
            )
        else:
            results.append(
                GateResult(
                    experiment,
                    f"gate1_guard_count:{label}",
                    "FAIL",
                    f"{label}: non-zero guard count ({count}) at the final solution -- "
                    "optimality is unreliable here",
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


def check_e4(out_dir: Path) -> list[GateResult]:
    """E4 -- cameras x frames synthetic benchmark grid. Nine per-cell
    direct-call benchmark records plus the aggregated `benchmark_grid.csv`."""
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
    df = _load_csv(out_dir / "benchmark_grid.csv")
    results.append(_check_guard_column("E4", "benchmark_grid.csv", df))
    results.append(_check_status_column("E4", "benchmark_grid.csv", df))
    return results


def check_e5(out_dir: Path) -> list[GateResult]:
    """E5 -- refractive-index sensitivity band. One environment-only
    provenance sidecar summing the guard count across the whole band; no
    per-row status or optimality is recorded for this experiment."""
    record = _load_json(out_dir / "e5_provenance.json")
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


def check_e6(out_dir: Path) -> list[GateResult]:
    """E6 -- index/layout/scale generalization sweep. Twelve per-configuration
    checkpoints plus the aggregated `generalization_sweep.csv`."""
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
            check_optimality=True,
            require_water_index=True,
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
) -> list[GateResult]:
    """Gate the `--seeds` band CSVs introduced by D-19.4-14 (SC-5a).

    A band exists to make a published number REGENERABLE: before this phase,
    MF-05's per-arm bands and MF-08's 97-178x ratio spread lived only in
    gitignored `seed_sweep_19_3/` output, so a reviewer had to take the summary
    tables on trust. The gate therefore checks the property that makes the
    artifact trustworthy -- that it really contains the N independent seeds its
    provenance claims -- not merely that a file appeared.

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
        sidecar_glob: Glob for the provenance sidecars carrying `seeds`.

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

    recorded: list[int] | None = None
    sidecar_used: str | None = None
    for path in sorted(out_dir.glob(sidecar_glob)):
        record = _load_json(path)
        if not isinstance(record, dict):
            continue
        seeds = record.get("solver_config", {}).get("seeds")
        if isinstance(seeds, list) and seeds:
            recorded = [int(s) for s in seeds]
            sidecar_used = path.name
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


def _check_git_sha_consistency(out_dir: Path) -> GateResult:
    """Gate 3's cross-artifact form: every git_sha found across the WHOLE run
    must be identical. This is the machine-checkable form of "commit nothing
    while a run is in flight" -- a split sha means exactly that happened.
    """
    shas: dict[str, list[str]] = {}
    for path in _collect_all_json_paths(out_dir):
        record = _load_json(path)
        if record is None or "_load_error" in record:
            continue
        sha = (record.get("environment") or {}).get("git_sha")
        if sha:
            shas.setdefault(sha, []).append(str(path.relative_to(out_dir)))

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


def run_all_gates(out_dir: Path) -> list[GateResult]:
    """Run every gate over every experiment's artifacts under `out_dir`.

    Args:
        out_dir: Root output directory (e.g. `experiments/results/`).

    Returns:
        The full list of `GateResult`s across all six experiments plus the
        one cross-artifact git_sha-consistency check.
    """
    results: list[GateResult] = []
    results += check_e1(out_dir)
    results += check_e3(out_dir)
    results += check_e4(out_dir)
    results += check_e5(out_dir)
    results += check_e6(out_dir)
    results += check_e7(out_dir)
    # D-19.4-14's band artifacts. Only E7 and E1 have bands this phase -- E4 and
    # E6 bands cost ~39 h together and neither carries an accuracy claim, so
    # they are a Deferred Idea, not an omission.
    results += check_band_csv(
        "E7", out_dir, "interface_ablation_band.csv", "e7_benchmark_*.json"
    )
    results += check_band_csv("E1", out_dir, "exp1_band.csv", "e1_benchmark_*.json")
    results.append(_check_git_sha_consistency(out_dir))
    return results


def build_arg_parser() -> argparse.ArgumentParser:
    """Build this script's single-argument CLI parser."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "out_dir",
        type=Path,
        help="Output directory containing the re-run's artifacts (e.g. experiments/results/).",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    """CLI entry point for `python experiments/check_rerun_gates.py <out_dir>`."""
    args = build_arg_parser().parse_args(argv)
    out_dir = Path(args.out_dir).resolve()
    results = run_all_gates(out_dir)

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
