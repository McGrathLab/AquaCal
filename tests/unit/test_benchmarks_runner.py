"""Unit tests for `benchmarks/aggregate.py` and `benchmarks/sweep_runner.py` (BENCH-05).

`benchmarks/` is a standalone, repo-root harness -- NOT part of the shipped
`aquacal` package (D-12). These tests import it via `sys.path` manipulation,
matching the same pattern this test suite already uses for `tests/synthetic`
helpers (see `test_benchmark.py`).
"""

from __future__ import annotations

import shutil
import sys
from pathlib import Path

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from benchmarks.aggregate import (  # noqa: E402
    SUPPORTED_SCHEMA_VERSION,
    UnsupportedSchemaVersionError,
    aggregate,
    write_csv,
)

FIXTURES_DIR = Path(__file__).parent / "fixtures" / "benchmark_records"


def _copy_fixture(name: str, dest_dir: Path, dest_name: str | None = None) -> None:
    dest_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy(FIXTURES_DIR / name, dest_dir / (dest_name or "benchmark.json"))


class TestAggregate:
    def test_two_valid_files_yield_two_rows(self, tmp_path):
        _copy_fixture("benchmark_valid_with_memory.json", tmp_path / "run_a")
        _copy_fixture("benchmark_valid_no_memory.json", tmp_path / "run_b")

        df = aggregate(tmp_path)

        assert len(df) == 2

    def test_bad_schema_version_raises_and_names_file(self, tmp_path):
        _copy_fixture("benchmark_valid_with_memory.json", tmp_path / "run_a")
        bad_dir = tmp_path / "run_bad"
        _copy_fixture("benchmark_bad_schema.json", bad_dir)
        bad_path = bad_dir / "benchmark.json"

        with pytest.raises(UnsupportedSchemaVersionError) as excinfo:
            aggregate(tmp_path)

        assert str(bad_path) in str(excinfo.value)
        assert "999" in str(excinfo.value)

    def test_bad_schema_version_does_not_return_partial_dataframe(self, tmp_path):
        _copy_fixture("benchmark_valid_with_memory.json", tmp_path / "run_a")
        _copy_fixture("benchmark_bad_schema.json", tmp_path / "run_bad")

        with pytest.raises(UnsupportedSchemaVersionError):
            aggregate(tmp_path)

    def test_row_missing_memory_block_yields_nan_not_error(self, tmp_path):
        _copy_fixture("benchmark_valid_with_memory.json", tmp_path / "run_a")
        _copy_fixture("benchmark_valid_no_memory.json", tmp_path / "run_b")

        df = aggregate(tmp_path)

        assert "memory.whole_run_peak_bytes" in df.columns
        # run_b has no top-level "memory" block at all.
        no_memory_row = df[df["problem_shape.n_cameras"] == 13].iloc[0]
        assert pd.isna(no_memory_row["memory.whole_run_peak_bytes"])

    def test_flattened_columns_use_stage_name_not_stages_prefix(self, tmp_path):
        _copy_fixture("benchmark_valid_with_memory.json", tmp_path / "run_a")

        df = aggregate(tmp_path)

        assert "stage3.nfev" in df.columns
        assert "stage3.memory.cumulative_peak_bytes_as_of_stage_end" in df.columns
        assert not any(col.startswith("stages.") for col in df.columns)

    def test_does_not_recompute_fd_reduction(self, tmp_path):
        """D-13/D-06: fd_reduction is read verbatim, never recomputed."""
        _copy_fixture("benchmark_valid_with_memory.json", tmp_path / "run_a")

        df = aggregate(tmp_path)

        row = df.iloc[0]
        # The fixture's own recorded value (67 / 13), not a value this
        # aggregator derives independently.
        assert row["stage3.fd_reduction"] == pytest.approx(67 / 13)

    def test_supported_schema_version_constant_is_one(self):
        assert SUPPORTED_SCHEMA_VERSION == 1

    def test_empty_directory_returns_empty_dataframe(self, tmp_path):
        df = aggregate(tmp_path)
        assert len(df) == 0


class TestWriteCsv:
    def test_round_trips_with_same_row_count(self, tmp_path):
        _copy_fixture("benchmark_valid_with_memory.json", tmp_path / "run_a")
        _copy_fixture("benchmark_valid_no_memory.json", tmp_path / "run_b")
        df = aggregate(tmp_path)

        csv_path = tmp_path / "aggregated.csv"
        write_csv(df, csv_path)

        reloaded = pd.read_csv(csv_path)
        assert len(reloaded) == len(df)
