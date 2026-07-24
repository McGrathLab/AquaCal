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

import json
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
