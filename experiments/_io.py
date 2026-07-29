"""Shared I/O layer for every `experiments/eN_*.py` script (EXP-02).

This module is I/O only: it performs no scientific computation (P3). It
provides the five-flag argparse contract every experiment script shares
(D-21), a sorted CSV writer with a per-configuration resumability guard
(D-22/D-24), a numeric `--check` comparator (D-22), and a direct-call
`benchmark.json` wrapper for experiments that bypass
`run_calibration_from_config` (D-09). A future reader must not add
statistics, aggregation, or any other computed scientific quantity here --
that belongs in `aquacal.datasets.pipelines` (P2).
"""

from __future__ import annotations

import argparse
import logging
from pathlib import Path
from typing import TYPE_CHECKING, NamedTuple

import pandas as pd

from aquacal.io import (
    assemble_benchmark_record,
    capture_environment,
    write_benchmark_json,
)
from aquacal.io.internals import warn_if_overwriting

if TYPE_CHECKING:
    from aquacal.calibration._observability import SolverDiagnostics

logger = logging.getLogger(__name__)

# The settled Phase-18 stage vocabulary (do not invent an experiment-local
# stage name -- this is the same class of drift the Phase 19 verifier caught
# when `stage3.seconds` was always null).
_SETTLED_STAGE_KEYS = frozenset(
    {"stage3_interface_optimization", "stage3_intrinsic_pass"}
)


def build_experiment_arg_parser() -> argparse.ArgumentParser:
    """Build the shared five-flag CLI parent parser every experiment shares (D-21).

    Built with `add_help=False` so each script's own parser can extend it via
    `parents=[build_experiment_arg_parser()]` without a duplicate `-h`/`--help`
    conflict.

    Returns:
        An `argparse.ArgumentParser` exposing exactly `--seed`, `--out`,
        `--force`, `--smoke`, `--check` -- no more, no fewer.
    """
    parser = argparse.ArgumentParser(add_help=False, description=__doc__)
    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Random seed for scenario/detection generation (default: 42).",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=Path("experiments/results"),
        help="Output directory for this experiment's artifacts "
        "(default: experiments/results).",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Overwrite existing per-configuration output files instead of "
        "skipping them (default: skip, for resumability).",
    )
    parser.add_argument(
        "--smoke",
        action="store_true",
        help="Run a fast, reduced-size smoke variant instead of the full "
        "experiment (default: off).",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Compare freshly produced output against the committed baseline "
        "at a numeric tolerance instead of writing (default: off). Mutually "
        "exclusive with --force.",
    )
    return parser


def validate_args(parser: argparse.ArgumentParser, args: argparse.Namespace) -> None:
    """Enforce cross-flag constraints not expressible by `argparse` alone (D-21).

    Scripts call this immediately after `parser.parse_args()`.

    Args:
        parser: The parser `args` was produced from (used only to call
            `parser.error()`, which prints usage and exits nonzero).
        args: The parsed namespace to validate.

    Raises:
        SystemExit: Via `parser.error()`, when both `--check` and `--force`
            are set. This is a hard error, not a silent preference for
            either flag (D-21).
    """
    if args.check and args.force:
        parser.error("--check and --force are mutually exclusive")


def resolve_out_dir(out: Path) -> Path:
    """Resolve, create, and log an experiment's output directory (D-21).

    Reuses the established in-repo discipline (resolve to an absolute path,
    log it, rely on `warn_if_overwriting` at each individual write) rather
    than adding a new `..`-traversal guard, which RESEARCH's Security Domain
    assessment judged disproportionate for a single-user local CLI.

    Args:
        out: The `--out` path as parsed (may be relative).

    Returns:
        The resolved absolute `Path`, created (with parents) if it did not
        already exist.
    """
    resolved = Path(out).resolve()
    resolved.mkdir(parents=True, exist_ok=True)
    logger.info("Experiment output directory: %s", resolved)
    return resolved


def write_experiment_csv(
    df: pd.DataFrame,
    path: Path,
    *,
    key_columns: list[str],
    force: bool,
) -> bool:
    """Sort and write an experiment CSV, honoring the resumability guard (D-24).

    Sorts `df` by `key_columns` (ascending, stable sort) before writing so a
    clean re-run produces byte-stable row order (D-22/P6). Skips the write
    entirely -- without touching `path` -- when `path` already exists and
    `force` is False.

    Args:
        df: The `DataFrame` to write.
        path: Destination `.csv` file path.
        key_columns: Columns to sort by before writing. Every name must be
            present in `df.columns`.
        force: When True, overwrite `path` even if it already exists. When
            False (default caller behavior), an existing `path` is left
            untouched and this function returns without writing.

    Returns:
        True if the file was written, False if the write was skipped because
        `path` already existed and `force` was False.

    Raises:
        ValueError: If any of `key_columns` is not a column of `df`. A silent
            unsorted write is exactly the failure mode RESEARCH's Pitfall 5
            warns against.
    """
    missing = [c for c in key_columns if c not in df.columns]
    if missing:
        raise ValueError(
            f"key_columns {missing} not present in DataFrame columns {list(df.columns)}"
        )

    path = Path(path)
    if path.exists() and not force:
        logger.info(
            "Skipping write to %s: file already exists and --force was not "
            "given (resumability).",
            path,
        )
        return False

    warn_if_overwriting(path)
    sorted_df = df.sort_values(by=key_columns, kind="stable").reset_index(drop=True)
    path.parent.mkdir(parents=True, exist_ok=True)
    sorted_df.to_csv(path, index=False)
    return True


class ComparisonReport(NamedTuple):
    """Result of `compare_experiment_csv`'s numeric comparison (D-22).

    Attributes:
        passed: True if the fresh DataFrame matched the committed baseline
            within tolerance (and with an identical header set).
        worst_cell: A human-readable description of the single worst-offending
            cell (its key-column values, its column name, the committed
            value, the fresh value, and the relative difference), or `None`
            if `passed` is True.
        worst_rtol: The relative difference of the worst-offending cell, or
            0.0 if `passed` is True.
        n_mismatched_cells: Count of float cells outside `rtol`, plus any
            non-float cells that differ at all.
        message: A full human-readable summary, suitable for printing to the
            console on `--check` failure.
    """

    passed: bool
    worst_cell: str | None
    worst_rtol: float
    n_mismatched_cells: int
    message: str


def exit_code_for(report: ComparisonReport) -> int:
    """Map a `ComparisonReport` to a process exit code (D-22).

    Args:
        report: The result of `compare_experiment_csv`.

    Returns:
        0 if `report.passed`, else 1.
    """
    return 0 if report.passed else 1


def compare_experiment_csv(
    fresh: pd.DataFrame,
    committed_path: Path,
    *,
    key_columns: list[str],
    rtol: float,
) -> ComparisonReport:
    """Compare a freshly produced DataFrame against a committed baseline CSV (D-22).

    Never writes to `committed_path` or anywhere else. Sorts both frames by
    `key_columns` before comparing (RESEARCH Pitfall 5: a committed CSV whose
    rows are shuffled relative to the fresh frame must still compare as
    passed). Float columns compare at `rtol`; non-float (object/string/int)
    columns must compare exactly.

    Args:
        fresh: The freshly computed `DataFrame` to check.
        committed_path: Path to the repo-committed baseline CSV.
        key_columns: Columns identifying each row, used to realign the two
            frames before comparing (not row index -- Pitfall 5).
        rtol: Relative tolerance applied to float columns only.

    Returns:
        A `ComparisonReport` describing the outcome. On a header mismatch,
        `passed` is False and `message` names the offending column(s) rather
        than reporting a tolerance failure.
    """
    committed = pd.read_csv(committed_path)

    fresh_columns = list(fresh.columns)
    committed_columns = list(committed.columns)
    if fresh_columns != committed_columns:
        message = (
            f"Header mismatch: fresh columns {fresh_columns} != "
            f"committed columns {committed_columns} (committed file: "
            f"{committed_path})"
        )
        return ComparisonReport(
            passed=False,
            worst_cell=message,
            worst_rtol=float("inf"),
            n_mismatched_cells=max(len(set(fresh_columns) ^ set(committed_columns)), 1),
            message=message,
        )

    fresh_sorted = fresh.sort_values(by=key_columns, kind="stable").reset_index(
        drop=True
    )
    committed_sorted = committed.sort_values(by=key_columns, kind="stable").reset_index(
        drop=True
    )

    # A column that is all empty strings in `fresh` (e.g. status_reason on an
    # all-"ok" grid) round-trips through CSV as an all-NaN float64 column on
    # `committed`, which would otherwise misclassify it as a float column
    # below and crash `to_numpy(dtype=float)` on the empty-string side. Bring
    # `committed` back to object dtype with "" in place of NaN wherever
    # `fresh` is itself an object (string) column, so the exact non-float
    # comparison sees "" == "" rather than a spurious dtype-driven mismatch.
    for col in fresh_sorted.columns:
        fresh_is_stringlike = pd.api.types.is_object_dtype(
            fresh_sorted[col]
        ) or pd.api.types.is_string_dtype(fresh_sorted[col])
        if fresh_is_stringlike and pd.api.types.is_float_dtype(committed_sorted[col]):
            committed_sorted[col] = committed_sorted[col].fillna("").astype(object)

    float_columns = [
        c
        for c in fresh_columns
        if pd.api.types.is_float_dtype(fresh_sorted[c])
        or pd.api.types.is_float_dtype(committed_sorted[c])
    ]
    non_float_columns = [c for c in fresh_columns if c not in float_columns]

    # A column that is MOSTLY empty strings but carries at least one real
    # string (e.g. E6's status_reason: 13 "" rows plus one genuine
    # "KeyError: 'cam11'" row) never triggers the all-NaN-column branch
    # above, because a column with a real string present is not classified
    # as float-dtype by pandas on read-back -- it stays object/"str" dtype.
    # But the "" cells still round-trip through CSV as an EMPTY FIELD
    # indistinguishable from a genuinely missing value, so `pd.read_csv`
    # reads them back as `NaN` (a float) sitting inside an otherwise
    # string-dtype column. Comparing that NaN against fresh's "" via `!=`
    # then reports every "" row as mismatched, even though "" and the
    # round-tripped NaN mean the same thing here (review of 19.2-11: this
    # is a DIFFERENT defect class from the all-NaN-column case above, not
    # covered by it, and not benign -- fixed here rather than dismissed by
    # analogy). Since every non-float column in this codebase's committed
    # CSVs is a categorical/status string that is never legitimately
    # missing, normalizing `NaN` -> `""` on both sides before the exact
    # comparison is safe generally, not just for the E6 case that surfaced
    # it.
    for col in non_float_columns:
        fresh_sorted[col] = fresh_sorted[col].where(fresh_sorted[col].notna(), "")
        committed_sorted[col] = committed_sorted[col].where(
            committed_sorted[col].notna(), ""
        )

    # Non-float columns must compare exactly, regardless of rtol.
    mismatched_non_float: list[tuple[int, str]] = []
    for col in non_float_columns:
        mask = fresh_sorted[col].astype(object) != committed_sorted[col].astype(object)
        for row_idx in fresh_sorted.index[mask]:
            mismatched_non_float.append((row_idx, col))

    # Float columns compare at rtol -- delegate to pandas' battle-hardened
    # comparator rather than a hand-rolled loop (RESEARCH "Don't Hand-Roll").
    float_mismatch_error: AssertionError | None = None
    if float_columns:
        try:
            pd.testing.assert_frame_equal(
                fresh_sorted[float_columns],
                committed_sorted[float_columns],
                check_exact=False,
                rtol=rtol,
                check_dtype=False,
            )
        except AssertionError as exc:
            float_mismatch_error = exc

    if not mismatched_non_float and float_mismatch_error is None:
        return ComparisonReport(
            passed=True,
            worst_cell=None,
            worst_rtol=0.0,
            n_mismatched_cells=0,
            message="Fresh output matches committed baseline within tolerance.",
        )

    # Assemble the worst-offending-cell report.
    worst_rtol = 0.0
    worst_cell: str | None = None
    n_mismatched_cells = len(mismatched_non_float)

    for col in float_columns:
        fresh_vals = fresh_sorted[col].to_numpy(dtype=float)
        committed_vals = committed_sorted[col].to_numpy(dtype=float)
        denom = committed_vals.copy()
        denom[denom == 0] = 1.0
        rel_diff = abs(fresh_vals - committed_vals) / abs(denom)
        for row_idx in fresh_sorted.index:
            cell_rtol = rel_diff[row_idx]
            if cell_rtol > rtol:
                n_mismatched_cells += 1
                if cell_rtol > worst_rtol:
                    worst_rtol = cell_rtol
                    key_values = {k: fresh_sorted.loc[row_idx, k] for k in key_columns}
                    worst_cell = (
                        f"key={key_values} column={col!r} "
                        f"committed={committed_vals[row_idx]!r} "
                        f"fresh={fresh_vals[row_idx]!r} rel_diff={cell_rtol!r}"
                    )

    if worst_cell is None and mismatched_non_float:
        row_idx, col = mismatched_non_float[0]
        key_values = {k: fresh_sorted.loc[row_idx, k] for k in key_columns}
        worst_cell = (
            f"key={key_values} column={col!r} (non-float, exact-compare) "
            f"committed={committed_sorted.loc[row_idx, col]!r} "
            f"fresh={fresh_sorted.loc[row_idx, col]!r}"
        )
        worst_rtol = float("inf")

    message = (
        f"{n_mismatched_cells} cell(s) mismatched against {committed_path}. "
        f"Worst: {worst_cell}"
    )
    return ComparisonReport(
        passed=False,
        worst_cell=worst_cell,
        worst_rtol=worst_rtol,
        n_mismatched_cells=n_mismatched_cells,
        message=message,
    )


def write_direct_call_benchmark(
    path: Path,
    *,
    problem_shape: dict,
    timings: dict,
    diagnostics: dict[str, "SolverDiagnostics"],
    solver_config: dict,
    accuracy: dict,
    memory_readings: dict | None = None,
    seed: int | None = None,
    force: bool = False,
) -> bool:
    """Write a schema-1 `benchmark.json` for a direct-call experiment (D-09).

    For experiments (E1, E7) that bypass `run_calibration_from_config` and
    therefore never get a pipeline-written `benchmark.json`. Reuses
    `aquacal.io.assemble_benchmark_record` and `write_benchmark_json`
    unmodified -- one schema suite-wide, no hand-rolled sidecar format.

    Memory readings are forwarded to `assemble_benchmark_record` when
    supplied; the default `None` preserves the historical behavior exactly,
    so E1's and E7's already-committed records are unchanged and no
    `memory` key appears in them. 19.1's D-11 deferral ("always passes
    `memory_readings=None`") is superseded by 19.2's D-24 now that
    `calibrate_synthetic` can supply readings via `memory_out`.

    `solver_config["seed"]` is a deliberate additive extension of the
    constraint-10 settled schema, not schema drift: it adds a key INSIDE the
    pass-through `solver_config` dict, which `assemble_benchmark_record`
    forwards unmodified and whose key set nothing validates, so it changes
    no top-level key, no stage block, and requires no schema version bump --
    `_render.aggregate` continues to flatten it without edit. It is required
    because EXP-11 and ROADMAP SC5 demand a seed on every committed result
    and, verified against `e1_benchmark_refractive.json`, no benchmark
    record carries one today.

    Args:
        path: Destination `benchmark.json` path.
        problem_shape: Passed through to `assemble_benchmark_record`.
        timings: Wall-clock seconds per stage. Every key must be one of the
            settled Phase-18 stage names (`stage3_interface_optimization`,
            `stage3_intrinsic_pass`).
        diagnostics: `SolverDiagnostics` per stage, keyed the same way as
            `timings`.
        solver_config: Passed through to `assemble_benchmark_record`. Must
            not already contain a `"seed"` key when `seed` is also given.
        accuracy: Passed through to `assemble_benchmark_record`.
        memory_readings: Optional dict keyed by `"_baseline"` plus the
            settled stage names, whose values are `capture_peak_memory()`
            results (D-24). Forwarded to `assemble_benchmark_record`
            unmodified; not subject to the `_SETTLED_STAGE_KEYS` allowlist
            below since `"_baseline"` is legitimately not a stage name.
            Defaults to `None`, which preserves the historical no-`memory`-
            key shape exactly.
        seed: Optional run seed (review H5). When given, stamped into a
            SHALLOW COPY of `solver_config` as `solver_config["seed"]` --
            the caller's dict is never mutated, since E4 reuses one config
            dict across cells. Defaults to `None`, which preserves the
            historical no-`seed`-key shape exactly.
        force: Honor the same resumability discipline as
            `write_experiment_csv` -- skip (returning False) if `path`
            already exists and `force` is False.

    Returns:
        True if the file was written, False if the write was skipped because
        `path` already existed and `force` was False.

    Raises:
        ValueError: If any key in `timings` or `diagnostics` is not one of
            the settled stage keys -- guarding against an experiment-local
            stage vocabulary drifting the same way `stage3.seconds` did in
            the Phase 19 verifier's finding. Also raised if `seed` is given
            while `solver_config` already contains a `"seed"` key, so one
            published value never has two origins.
    """
    for label, block in (("timings", timings), ("diagnostics", diagnostics)):
        unsettled = [k for k in block if k not in _SETTLED_STAGE_KEYS]
        if unsettled:
            raise ValueError(
                f"{label} contains unsettled stage key(s) {unsettled}; only "
                f"{sorted(_SETTLED_STAGE_KEYS)} are permitted"
            )

    if seed is not None:
        if "seed" in solver_config:
            raise ValueError(
                f"solver_config already contains seed={solver_config['seed']!r}; "
                f"refusing to also apply seed={seed!r} via the seed= parameter "
                "-- one published seed cannot have two origins"
            )
        solver_config = {**solver_config, "seed": seed}

    path = Path(path)
    if path.exists() and not force:
        logger.info(
            "Skipping write to %s: file already exists and --force was not "
            "given (resumability).",
            path,
        )
        return False

    record = assemble_benchmark_record(
        problem_shape=problem_shape,
        timings=timings,
        diagnostics=diagnostics,
        solver_config=solver_config,
        accuracy=accuracy,
        environment=capture_environment(),
        memory_readings=memory_readings,
    )
    write_benchmark_json(record, path)
    return True
