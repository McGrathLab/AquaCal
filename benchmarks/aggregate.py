"""Aggregate `benchmark.json` records into a tidy CSV / LaTeX table (BENCH-05).

Standalone script, NOT part of the shipped `aquacal` package: it lives at the
repository root under `benchmarks/`, is never imported by `src/aquacal`, and
adds no `aquacal` CLI subcommand (D-12). It is a pure aggregator -- it reads
every `benchmark.json` under a directory tree, flattens each into one tidy
row, and concatenates them. It computes no derived quantity the pipeline did
not already record (D-13/D-06): if a column looks like it needs computing
(e.g. `fd_reduction`, a per-stage memory delta), that computation belongs
upstream in `aquacal.io.benchmark.assemble_benchmark_record`, not here.

Run manually, e.g.:

    python benchmarks/aggregate.py --root output/sweep --csv sweep.csv
"""

from __future__ import annotations

import argparse
import json
import warnings
from pathlib import Path

import pandas as pd

SUPPORTED_SCHEMA_VERSION = 1


class UnsupportedSchemaVersionError(ValueError):
    """Raised when a `benchmark.json`'s `schema_version` is not recognized.

    D-04: a sweep can span days and a code change. A `benchmark.json` whose
    `schema_version` this aggregator does not recognize must never be
    silently coerced or dropped -- it must stop the whole aggregation and
    name the offending file, so a mixed-schema CSV can never be produced.
    """


def _flatten_record(record: dict) -> dict:
    """Promote each `stages.<name>` block to a top-level key before flattening.

    `record["stages"]` is a dict keyed by stage name (e.g. `"stage3"`,
    `"validation"`). Promoting those keys to the top level (rather than
    leaving them nested under a literal `"stages"` key) is what produces the
    documented column names like `stage3.nfev` and
    `stage3.memory.cumulative_peak_bytes_as_of_stage_end`, instead of
    `stages.stage3.nfev`.

    Args:
        record: One parsed `benchmark.json` document.

    Returns:
        A shallow copy of `record` with `"stages"` removed and each of its
        entries merged in at the top level. Purely structural -- no values
        are read, computed, or modified.
    """
    flat = {key: value for key, value in record.items() if key != "stages"}
    for stage_name, stage_data in record.get("stages", {}).items():
        flat[stage_name] = stage_data
    return flat


def aggregate(root_dir: Path) -> pd.DataFrame:
    """Read every `benchmark.json` under `root_dir` into one tidy DataFrame.

    Globs `root_dir.rglob("benchmark.json")`, `json.load`s each file, checks
    `schema_version` before flattening (refusing loudly on a mismatch --
    D-04), and concatenates the flattened records into one row-per-file
    `DataFrame`. Computes no derived value: every column is read verbatim
    from the JSON (D-13/D-06). Fixture rows that omit the opt-in `"memory"`
    key entirely produce `NaN` in the corresponding memory columns for that
    row -- correct `pandas` ragged-column behavior, not an error.

    Args:
        root_dir: Directory tree to search (recursively) for `benchmark.json`
            files.

    Returns:
        A `DataFrame` with one row per `benchmark.json` file found, columns
        named by dotted-path flattening (e.g. `problem_shape.n_cameras`,
        `stage3.nfev`, `stage3.memory.cumulative_peak_bytes_as_of_stage_end`).
        Empty `DataFrame` if no files are found.

    Raises:
        UnsupportedSchemaVersionError: If any file's `schema_version` does
            not equal `SUPPORTED_SCHEMA_VERSION`. Raised immediately on the
            first mismatch found (directory iteration order is sorted for
            determinism) -- the rest of the directory is not processed, so a
            partial CSV can never be mistaken for a complete one.
    """
    root_dir = Path(root_dir)
    flattened_frames = []

    for path in sorted(root_dir.rglob("benchmark.json")):
        with open(path) as f:
            record = json.load(f)

        version = record.get("schema_version")
        if version != SUPPORTED_SCHEMA_VERSION:
            raise UnsupportedSchemaVersionError(
                f"{path}: schema_version={version!r}, expected "
                f"{SUPPORTED_SCHEMA_VERSION}"
            )

        flattened_frames.append(pd.json_normalize(_flatten_record(record)))

    if not flattened_frames:
        return pd.DataFrame()

    return pd.concat(flattened_frames, ignore_index=True)


def write_csv(df: pd.DataFrame, path: Path) -> None:
    """Write `df` to `path` as a CSV re-readable by `pandas.read_csv`.

    Args:
        df: The `DataFrame` returned by `aggregate()`.
        path: Destination `.csv` file path.
    """
    df.to_csv(Path(path), index=False)


def _mixed_memory_mode_values(df: pd.DataFrame) -> set:
    """Collect every distinct non-null `memory.mode` value across `df`.

    Looks at any column named exactly `"memory.mode"` or ending in
    `".memory.mode"` -- the top-level and per-stage flattened columns
    `aggregate()` produces.

    Args:
        df: The `DataFrame` to inspect.

    Returns:
        The set of distinct non-null values found across all matching
        columns. Empty if no such column exists or all values are null.
    """
    mode_columns = [
        column
        for column in df.columns
        if column == "memory.mode" or column.endswith(".memory.mode")
    ]
    distinct_values: set = set()
    for column in mode_columns:
        distinct_values.update(df[column].dropna().unique().tolist())
    return distinct_values


# LaTeX special characters that must be escaped in tabular cell/header text.
# Values in benchmark.json (SciPy termination messages, CPU model strings,
# environment fields) routinely contain '_', '%', '&', etc.; emitted raw they
# corrupt or break compilation of the fragment.
_LATEX_SPECIALS = {
    "\\": r"\textbackslash{}",
    "&": r"\&",
    "%": r"\%",
    "$": r"\$",
    "#": r"\#",
    "_": r"\_",
    "{": r"\{",
    "}": r"\}",
    "~": r"\textasciitilde{}",
    "^": r"\textasciicircum{}",
}


def _latex_escape(text: str) -> str:
    """Escape LaTeX special characters in a header or cell string.

    Backslash is handled first (its replacement introduces braces the other
    substitutions must not re-escape).
    """
    out = text.replace("\\", _LATEX_SPECIALS["\\"])
    for char, repl in _LATEX_SPECIALS.items():
        if char == "\\":
            continue
        out = out.replace(char, repl)
    return out


def write_latex_fragment(df: pd.DataFrame, path: Path, columns: list[str]) -> None:
    """Write a minimal LaTeX `tabular` fragment for `columns` of `df`.

    Pure formatting: one row per DataFrame row, one column per the
    caller-specified `columns` list, values taken directly from the
    already-aggregated `df` (no new computation, D-13).

    Warns (`UserWarning`) when `df` mixes more than one distinct non-null
    `memory.mode` value across rows -- e.g. `psutil_peak_wset` (a true OS
    high-water mark) alongside `psutil_rss_sampled` (an instantaneous
    reading). Tabulating those side by side (e.g. averaging) would silently
    understate the reported peak in a paper table. Does not warn when the
    value is uniform across rows or the column is entirely absent.

    Args:
        df: The DataFrame to tabulate (typically `aggregate()`'s output).
        path: Destination `.tex` file path.
        columns: Ordered list of column names to include, one LaTeX table
            column each.
    """
    distinct_modes = _mixed_memory_mode_values(df)
    if len(distinct_modes) > 1:
        warnings.warn(
            "write_latex_fragment: DataFrame mixes multiple memory.mode "
            f"values: {sorted(distinct_modes)}. Tabulating these together "
            "(e.g. averaging) would silently blend a true high-water-mark "
            "reading with a weaker instantaneous sample.",
            UserWarning,
            stacklevel=2,
        )

    column_spec = "|" + "l|" * len(columns)
    lines = [f"\\begin{{tabular}}{{{column_spec}}}", "\\hline"]
    lines.append(" & ".join(_latex_escape(c) for c in columns) + " \\\\")
    lines.append("\\hline")
    for _, row in df.iterrows():
        cells = []
        for column in columns:
            value = row[column] if column in row.index else None
            cells.append(
                "" if value is None or pd.isna(value) else _latex_escape(str(value))
            )
        lines.append(" & ".join(cells) + " \\\\")
    lines.append("\\hline")
    lines.append("\\end{tabular}")

    Path(path).write_text("\n".join(lines) + "\n")


def _build_arg_parser() -> argparse.ArgumentParser:
    """Build the CLI argument parser for `python benchmarks/aggregate.py`.

    Returns:
        A configured `argparse.ArgumentParser`.
    """
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--root", type=Path, required=True, help="Directory tree to search."
    )
    parser.add_argument("--csv", type=Path, default=None, help="Output CSV path.")
    parser.add_argument(
        "--latex", type=Path, default=None, help="Output LaTeX fragment path."
    )
    parser.add_argument(
        "--latex-columns",
        nargs="*",
        default=None,
        help="Columns to include in the LaTeX fragment (required with --latex).",
    )
    return parser


if __name__ == "__main__":
    args = _build_arg_parser().parse_args()
    aggregated = aggregate(args.root)
    if args.csv is not None:
        write_csv(aggregated, args.csv)
    if args.latex is not None:
        if not args.latex_columns:
            raise SystemExit("--latex requires --latex-columns")
        write_latex_fragment(aggregated, args.latex, args.latex_columns)
