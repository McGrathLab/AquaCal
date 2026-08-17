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
from collections.abc import Callable, Sequence
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


def parse_seed_list(value: str) -> list[int]:
    """Parse a comma-separated seed list into explicit integers (D-19.4-14).

    Chosen over an integer count so the exact seeds an experiment's band ran
    at are auditable in the committed provenance JSON rather than derived
    from a rule a reader would have to re-execute to check. This is the
    shared parsing primitive a script-local `--seeds` flag calls; it is
    deliberately NOT wired into `build_experiment_arg_parser` itself, since
    that shared parser's own docstring promises exactly five flags. Reusing
    this function is what lets E4 and E6 add a `--seeds` mode later as
    configuration (a script-local flag calling this same parser), not new
    parsing code (D-19.4-14).

    Args:
        value: A comma-separated string of integer seeds, e.g. `"42,43,44"`.
            Surrounding whitespace around each token is tolerated.

    Returns:
        The parsed seeds, in the order they appeared in `value`.

    Raises:
        ValueError: If `value` is empty, contains an empty token (e.g. a
            trailing comma), contains a token that does not parse as an
            integer, or contains a duplicate seed -- each message names the
            offending token so the caller does not have to re-derive which
            one failed.
    """
    tokens = [token.strip() for token in value.split(",")]
    if value.strip() == "" or any(token == "" for token in tokens):
        raise ValueError(
            f"parse_seed_list({value!r}) contains an empty token; expected "
            "a comma-separated list of integers, e.g. '42,43,44'"
        )

    seeds: list[int] = []
    for token in tokens:
        try:
            seed = int(token)
        except ValueError as exc:
            raise ValueError(
                f"parse_seed_list({value!r}) could not parse token {token!r} "
                "as an integer"
            ) from exc
        seeds.append(seed)

    seen: set[int] = set()
    for seed in seeds:
        if seed in seen:
            raise ValueError(
                f"parse_seed_list({value!r}) contains duplicate seed {seed}; "
                "a repeated seed silently halves the band's own width"
            )
        seen.add(seed)

    return seeds


def run_seed_band(
    runner: Callable[[int], pd.DataFrame], seeds: Sequence[int]
) -> pd.DataFrame:
    """Run `runner` once per seed and concatenate the results into one band (D-19.4-14).

    This is the shared band-execution primitive: an experiment script wires
    its own per-seed run into `runner`, and this function owns only the
    "call once per seed, stamp `seed`, concatenate" mechanics. Adding a band
    mode to E4/E6 later is then a matter of writing their own `runner`
    closures and calling this function -- configuration, not new code
    (D-19.4-14).

    Args:
        runner: A callable taking a single `seed: int` and returning the
            `DataFrame` of rows that seed produced. Called once per element
            of `seeds`, in order.
        seeds: The seeds to run, in the order to run them.

    Returns:
        The row-wise concatenation (`ignore_index=True`) of every frame
        `runner` returned, in seed order, with a `seed` column present and
        correct on every row (added if `runner`'s own frame did not already
        carry one).

    Raises:
        Exception: Whatever `runner` raises, propagated immediately and
            unmodified. A failing seed must not be swallowed into a partial
            band (D-19.4-11's fail-fast posture) -- there is no
            `try`/`except` here.

    Adding E4/E6 later (deferred, D-19.4-13/D-19.4-14): a future caller
    supplies (1) a `runner(seed) -> DataFrame` closure that wraps that
    experiment's EXISTING per-cell or per-configuration loop (E4's grid
    sweep, E6's generalization sweep) and returns the one seed's rows, (2) a
    script-local `--seeds` argument on that script's own `build_arg_parser`
    (mirroring E1's and E7's `--seeds` flags), and (3) a `_validate_*_args`
    extension rejecting `--seeds` combined with `--check`, exactly like
    `experiments.e1_refractive_comparison._validate_e1_args` and
    `experiments.e7_interface_ablation._validate_e7_args`. No change to
    `run_seed_band` or to `parse_seed_list` is needed -- that is the entire
    point of this being the shared primitive. This is deliberately NOT done
    in this
    phase: a 10-seed E6 band is ~16.6 h and a 10-seed E4 band is ~22.1 h,
    ~39 h together, and neither E4 nor E6 carries an accuracy claim that a
    band would defend.
    """
    frames: list[pd.DataFrame] = []
    for seed in seeds:
        frame = runner(seed).copy()
        frame["seed"] = seed
        frames.append(frame)
    return pd.concat(frames, ignore_index=True)


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
    exclude_columns: tuple[str, ...] = (),
) -> ComparisonReport:
    """Compare a freshly produced DataFrame against a committed baseline CSV (D-22).

    Never writes to `committed_path` or anywhere else. Aligns the two frames
    on `key_columns` before comparing (RESEARCH Pitfall 5: a committed CSV
    whose rows are shuffled relative to the fresh frame must still compare as
    passed) rather than by row position. Float columns compare at `rtol`;
    non-float (object/string/int) columns must compare exactly.

    Totality contract: this function returns a `ComparisonReport` for every
    `(fresh, committed_path, key_columns, rtol)` whose committed file is
    readable as a CSV, including a row-count mismatch, a key-set mismatch, a
    duplicate key, and a non-numeric cell inside a column pandas classified
    as float. The only exceptions it may propagate are I/O errors reading
    `committed_path` (e.g. the file does not exist or is not valid CSV). A
    caller extending this function is extending a total function, not adding
    a new special case to a partial one -- see the CR-04 history in the
    body below (`ee8af31`, `ac75e35`, and the key-alignment fix that replaced
    positional sort-and-compare).

    Args:
        fresh: The freshly computed `DataFrame` to check.
        committed_path: Path to the repo-committed baseline CSV.
        key_columns: Columns identifying each row, used to realign the two
            frames before comparing (not row index -- Pitfall 5).
        rtol: Relative tolerance applied to float columns only.
        exclude_columns: Column names to drop from the CELL-level comparison
            only (D-07/D-08). The full-header comparison above is NEVER
            affected by this parameter -- a genuine schema change still
            fails loudly even if the differing column is named here. This is
            the mechanism for columns that are artifacts of the *checking
            path* itself (e.g. a value only a live subprocess would produce)
            rather than of the run being checked; the caller declares and
            justifies its own list at the call site -- there is no default
            list here, because a named list beats a heuristic (D-07: the
            next such column should require a deliberate decision, not
            silently inherit an exemption). A name not present in the
            frames is silently ignored. Defaults to `()`, which leaves
            today's exact behavior and message byte-identical. Phase 26
            (DRIVER-03) documents this contract; the two must not diverge
            (D-08).

    Returns:
        A `ComparisonReport` describing the outcome. On a header mismatch, a
        row-count mismatch, a key-set mismatch, or a duplicate key, `passed`
        is False and `message` names the offending structural difference
        rather than reporting a tolerance failure or raising.
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

    # Align on key_columns explicitly, and classify the structural outcome
    # BEFORE any cell-level comparison. Sorting both frames and comparing
    # positionally (the prior approach) raises `ValueError: Can only compare
    # identically-labeled Series objects` the moment the two frames differ in
    # length, and silently mis-pairs row i of one frame against row i of the
    # other whenever the key sets merely happen to have equal length (WR-10)
    # -- e.g. a row-count mismatch, or two frames whose keys differ but whose
    # counts coincide.
    fresh_keys = list(fresh.set_index(key_columns).index)
    committed_keys = list(committed.set_index(key_columns).index)
    fresh_key_set = set(fresh_keys)
    committed_key_set = set(committed_keys)

    if fresh_key_set != committed_key_set:
        fresh_only = sorted(map(str, fresh_key_set - committed_key_set))
        committed_only = sorted(map(str, committed_key_set - fresh_key_set))
        _MAX_SHOWN = 10
        message = (
            f"Key set mismatch on {key_columns} (committed file: "
            f"{committed_path}): {len(fresh_only)} key(s) only in fresh "
            f"{fresh_only[:_MAX_SHOWN]}"
            f"{'...' if len(fresh_only) > _MAX_SHOWN else ''}, "
            f"{len(committed_only)} key(s) only in committed "
            f"{committed_only[:_MAX_SHOWN]}"
            f"{'...' if len(committed_only) > _MAX_SHOWN else ''}"
        )
        return ComparisonReport(
            passed=False,
            worst_cell=message,
            worst_rtol=float("inf"),
            n_mismatched_cells=max(len(fresh_only) + len(committed_only), 1),
            message=message,
        )

    if len(fresh_keys) != len(fresh_key_set) or len(committed_keys) != len(
        committed_key_set
    ):
        # Same key set (by unique value) but a different row count means at
        # least one side has a duplicate key -- key-based alignment cannot
        # pair rows unambiguously in that case.
        message = (
            f"Duplicate key(s) on {key_columns} (committed file: "
            f"{committed_path}): fresh has {len(fresh_keys)} row(s) / "
            f"{len(fresh_key_set)} unique key(s), committed has "
            f"{len(committed_keys)} row(s) / {len(committed_key_set)} "
            "unique key(s)."
        )
        return ComparisonReport(
            passed=False,
            worst_cell=message,
            worst_rtol=float("inf"),
            n_mismatched_cells=max(
                abs(len(fresh_keys) - len(fresh_key_set))
                + abs(len(committed_keys) - len(committed_key_set)),
                1,
            ),
            message=message,
        )

    # Key sets are equal and each key is unique on both sides: align by key
    # (not row position) so every subsequent comparison names the true
    # counterpart row.
    fresh_sorted = fresh.sort_values(by=key_columns, kind="stable").reset_index(
        drop=True
    )
    committed_sorted = committed.sort_values(by=key_columns, kind="stable").reset_index(
        drop=True
    )

    # D-07/D-08: drop the caller-named excluded columns from the CELL-level
    # comparison only -- the header comparison above already ran on the
    # unmodified column set, so a genuine schema change still fails even for
    # a column named here. A name not present in the frames is ignored
    # (the caller's declared intent, not an error).
    excluded_present = [c for c in exclude_columns if c in fresh_sorted.columns]
    if excluded_present:
        fresh_sorted = fresh_sorted.drop(columns=excluded_present)
        committed_sorted = committed_sorted.drop(columns=excluded_present)
    compare_columns = [c for c in fresh_columns if c not in excluded_present]

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
        for c in compare_columns
        if pd.api.types.is_float_dtype(fresh_sorted[c])
        or pd.api.types.is_float_dtype(committed_sorted[c])
    ]
    non_float_columns = [c for c in compare_columns if c not in float_columns]

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
        message = "Fresh output matches committed baseline within tolerance."
        if excluded_present:
            message += f" (excluded from cell comparison: {excluded_present})"
        return ComparisonReport(
            passed=True,
            worst_cell=None,
            worst_rtol=0.0,
            n_mismatched_cells=0,
            message=message,
        )

    # Assemble the worst-offending-cell report.
    worst_rtol = 0.0
    worst_cell: str | None = None
    n_mismatched_cells = len(mismatched_non_float)

    for col in float_columns:
        # `float_columns` classifies by dtype in EITHER frame (see above), so
        # a column that is float-classified because `fresh` is all-NaN can
        # still carry a real non-numeric string on the `committed` side (the
        # third member of the CSV dtype round-trip family, after `ee8af31`
        # and `ac75e35`): e.g. a `status_reason` column that is all-NaN in a
        # fresh run but holds `"KeyError: 'cam11'"` in one committed row.
        # `to_numpy(dtype=float)` would raise `ValueError: could not convert
        # string to float` on that cell. Coerce with `pd.to_numeric(...,
        # errors="coerce")` on BOTH sides instead of adding a fourth dtype
        # special case: any non-numeric cell becomes NaN, which then compares
        # as a mismatch below (never silently skipped -- a NaN-vs-value pair
        # must still count against n_mismatched_cells, or this fix would hide
        # the very defect it exists to surface).
        # Track "genuinely missing" (NaN in the RAW, pre-coercion column) so
        # a real non-numeric string that `to_numeric` coerces away (e.g.
        # committed's "KeyError: 'cam11'") is never confused with a
        # legitimate missing value -- only both-sides-raw-NaN is a match.
        fresh_raw_isna = fresh_sorted[col].isna().to_numpy()
        committed_raw_isna = committed_sorted[col].isna().to_numpy()
        both_genuinely_missing = fresh_raw_isna & committed_raw_isna

        fresh_vals = pd.to_numeric(fresh_sorted[col], errors="coerce").to_numpy(
            dtype=float
        )
        committed_vals = pd.to_numeric(committed_sorted[col], errors="coerce").to_numpy(
            dtype=float
        )
        denom = committed_vals.copy()
        denom[denom == 0] = 1.0
        rel_diff = abs(fresh_vals - committed_vals) / abs(denom)
        for row_idx in fresh_sorted.index:
            if both_genuinely_missing[row_idx]:
                # Both sides were NaN before coercion too (e.g. both
                # genuinely missing) -- not a mismatch.
                continue
            # A cell where coercion produced NaN on either side but the two
            # sides were not BOTH genuinely missing (one is a real
            # non-numeric string, or one is missing and the other a real
            # value) must still count as a mismatch -- silently skipping it
            # would hide the very defect this coercion exists to surface.
            cell_rtol = (
                float("inf")
                if (pd.isna(fresh_vals[row_idx]) or pd.isna(committed_vals[row_idx]))
                else rel_diff[row_idx]
            )
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
    if excluded_present:
        message += f" (excluded from cell comparison: {excluded_present})"
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
