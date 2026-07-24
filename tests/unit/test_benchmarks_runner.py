"""Unit tests for `benchmarks/aggregate.py` and `benchmarks/sweep_runner.py` (BENCH-05).

`benchmarks/` is a standalone, repo-root harness -- NOT part of the shipped
`aquacal` package (D-12). These tests import it via `sys.path` manipulation,
matching the same pattern this test suite already uses for `tests/synthetic`
helpers (see `test_benchmark.py`).
"""

from __future__ import annotations

import shutil
import sys
import warnings
from pathlib import Path
from unittest.mock import patch

import pandas as pd
import pytest
import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from benchmarks.aggregate import (  # noqa: E402
    SUPPORTED_SCHEMA_VERSION,
    UnsupportedSchemaVersionError,
    aggregate,
    write_csv,
    write_latex_fragment,
)
from benchmarks.sweep_runner import run_sweep  # noqa: E402

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


class TestWriteLatexFragment:
    def test_produces_tabular_with_one_line_per_row(self, tmp_path):
        _copy_fixture("benchmark_valid_with_memory.json", tmp_path / "run_a")
        _copy_fixture("benchmark_valid_no_memory.json", tmp_path / "run_b")
        df = aggregate(tmp_path)

        tex_path = tmp_path / "table.tex"
        write_latex_fragment(
            df,
            tex_path,
            ["problem_shape.n_cameras", "accuracy.reprojection_rms"],
        )

        content = tex_path.read_text()
        assert "\\begin{tabular}" in content
        assert "\\end{tabular}" in content
        # Header + hline separators + 2 data rows.
        assert content.count("\\\\") >= 2

    def test_no_warning_when_memory_mode_uniform(self, tmp_path):
        df = pd.DataFrame(
            {
                "problem_shape.n_cameras": [3, 3],
                "memory.mode": ["psutil_peak_wset", "psutil_peak_wset"],
            }
        )
        with warnings.catch_warnings():
            warnings.simplefilter("error")
            write_latex_fragment(
                df, tmp_path / "table.tex", ["problem_shape.n_cameras"]
            )

    def test_no_warning_when_memory_mode_absent(self, tmp_path):
        df = pd.DataFrame({"problem_shape.n_cameras": [3, 3]})
        with warnings.catch_warnings():
            warnings.simplefilter("error")
            write_latex_fragment(
                df, tmp_path / "table.tex", ["problem_shape.n_cameras"]
            )

    def test_warns_on_mixed_memory_mode_two_rows(self, tmp_path):
        df = pd.DataFrame(
            {
                "problem_shape.n_cameras": [3, 13],
                "memory.mode": ["psutil_peak_wset", "psutil_rss_sampled"],
            }
        )
        with pytest.warns(UserWarning, match="memory.mode"):
            write_latex_fragment(
                df, tmp_path / "table.tex", ["problem_shape.n_cameras"]
            )

    def test_warns_on_mixed_stage_level_memory_mode(self, tmp_path):
        df = pd.DataFrame(
            {
                "problem_shape.n_cameras": [3, 13],
                "stage3.memory.mode": ["psutil_peak_wset", "psutil_rss_sampled"],
            }
        )
        with pytest.warns(UserWarning, match="memory.mode"):
            write_latex_fragment(
                df, tmp_path / "table.tex", ["problem_shape.n_cameras"]
            )


@pytest.fixture
def base_sweep_config(tmp_path) -> Path:
    """A minimal, real-shaped calibration YAML config for run_sweep tests."""
    config_dir = tmp_path / "config_src"
    config_dir.mkdir()
    data = {
        "board": {
            "squares_x": 6,
            "squares_y": 5,
            "square_size": 0.04,
            "marker_size": 0.03,
        },
        "cameras": ["cam0", "cam1", "cam2"],
        "paths": {
            "intrinsic_videos": {
                "cam0": "cam0_intrinsic.mp4",
                "cam1": "cam1_intrinsic.mp4",
                "cam2": "cam2_intrinsic.mp4",
            },
            "extrinsic_videos": {
                "cam0": "cam0_extrinsic.mp4",
                "cam1": "cam1_extrinsic.mp4",
                "cam2": "cam2_extrinsic.mp4",
            },
            "output_dir": str(tmp_path / "base_output"),
        },
    }
    config_path = config_dir / "base_config.yaml"
    with open(config_path, "w") as f:
        yaml.safe_dump(data, f)
    return config_path


class TestRunSweep:
    def _fake_run_calibration_from_config(self, config):
        """Mimics benchmark.json's side effect without running a real solve."""
        config.output_dir.mkdir(parents=True, exist_ok=True)
        with open(config.output_dir / "benchmark.json", "w") as f:
            f.write('{"schema_version": 1, "stages": {}}')
        return None

    def test_returns_one_output_dir_per_grid_cell_and_does_not_raise(
        self, base_sweep_config, tmp_path
    ):
        output_root = tmp_path / "sweep_output"
        with patch(
            "benchmarks.sweep_runner.run_calibration_from_config",
            side_effect=self._fake_run_calibration_from_config,
        ) as mock_run:
            output_dirs = run_sweep([2], [10], base_sweep_config, output_root)

        assert len(output_dirs) == 1
        mock_run.assert_called_once()

    def test_grid_cell_count_matches_camera_x_frame_product(
        self, base_sweep_config, tmp_path
    ):
        output_root = tmp_path / "sweep_output"
        with patch(
            "benchmarks.sweep_runner.run_calibration_from_config",
            side_effect=self._fake_run_calibration_from_config,
        ) as mock_run:
            output_dirs = run_sweep([1, 2], [5, 10], base_sweep_config, output_root)

        assert len(output_dirs) == 4
        assert mock_run.call_count == 4

    def test_never_calls_real_run_calibration_from_config(
        self, base_sweep_config, tmp_path
    ):
        """No test in this module performs a real, un-mocked calibration."""
        output_root = tmp_path / "sweep_output"
        with patch("benchmarks.sweep_runner.run_calibration_from_config") as mock_run:
            mock_run.side_effect = self._fake_run_calibration_from_config
            run_sweep([2], [10], base_sweep_config, output_root)
            assert mock_run.called

    def test_requesting_more_cameras_than_available_raises(
        self, base_sweep_config, tmp_path
    ):
        output_root = tmp_path / "sweep_output"
        with patch(
            "benchmarks.sweep_runner.run_calibration_from_config",
            side_effect=self._fake_run_calibration_from_config,
        ):
            with pytest.raises(ValueError):
                run_sweep([99], [10], base_sweep_config, output_root)
