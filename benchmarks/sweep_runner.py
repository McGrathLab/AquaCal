"""Drive the cameras x frames benchmark sweep grid (BENCH-05).

Standalone script, NOT part of the shipped `aquacal` package (D-12): it lives
at the repository root under `benchmarks/`, is never imported by
`src/aquacal`, and adds no `aquacal` CLI subcommand. It imports only the
public `aquacal` package surface (`aquacal.calibration.load_config`,
`aquacal.calibration.run_calibration_from_config`) -- never a private
module such as `aquacal.calibration._observability`.

This module is written and unit-tested (with `run_calibration_from_config`
mocked) but is NOT invoked by this phase's tests or automation. It is run
manually for the actual paper sweep: a single 13-camera calibration run
takes 48-87 minutes, so a real sweep is explicitly out of scope for Phase
19's automated verification.
"""

from __future__ import annotations

import argparse
import copy
from pathlib import Path

import yaml

from aquacal.calibration import load_config, run_calibration_from_config


def run_sweep(
    camera_counts: list[int],
    frame_counts: list[int],
    base_config_path: Path,
    output_root: Path,
) -> list[Path]:
    """Run one calibration per (n_cameras, n_frames) grid cell.

    For each `(n_cameras, n_frames)` pair, builds a `CalibrationConfig` by
    subsampling `base_config_path`'s `cameras` list to the first `n_cameras`
    entries and capping `optimization.max_calibration_frames` at `n_frames`,
    writes a per-cell YAML config under `output_root`, loads it via
    `load_config`, and calls `run_calibration_from_config` -- which writes
    `output_dir/benchmark.json` as a side effect (`config.save_benchmark`
    defaults to `True`).

    Args:
        camera_counts: Camera-count grid values. Each must not exceed the
            number of cameras listed in `base_config_path`.
        frame_counts: Frame-count grid values, applied as
            `optimization.max_calibration_frames`.
        base_config_path: Path to a real calibration YAML config whose
            `cameras` list and video paths are subsampled/reused for every
            grid cell.
        output_root: Directory under which each grid cell's config and
            `output_dir` are written.

    Returns:
        List of each grid cell's `output_dir` path, in the order the grid
        was iterated (`camera_counts` outer loop, `frame_counts` inner loop).

    Raises:
        ValueError: If any `n_cameras` in `camera_counts` exceeds the number
            of cameras in the base config.
    """
    base_config_path = Path(base_config_path)
    output_root = Path(output_root)
    output_root.mkdir(parents=True, exist_ok=True)

    with open(base_config_path) as f:
        base_data = yaml.safe_load(f)

    all_cameras = base_data["cameras"]

    output_dirs: list[Path] = []
    for n_cameras in camera_counts:
        if n_cameras > len(all_cameras):
            raise ValueError(
                f"Requested n_cameras={n_cameras} exceeds the "
                f"{len(all_cameras)} cameras available in {base_config_path}"
            )
        for n_frames in frame_counts:
            cell_data = copy.deepcopy(base_data)
            cell_data["cameras"] = all_cameras[:n_cameras]

            optimization = dict(cell_data.get("optimization", {}))
            optimization["max_calibration_frames"] = n_frames
            cell_data["optimization"] = optimization

            cell_name = f"cameras_{n_cameras}_frames_{n_frames}"
            cell_output_dir = output_root / cell_name

            paths = dict(cell_data.get("paths", {}))
            paths["output_dir"] = str(cell_output_dir)
            cell_data["paths"] = paths

            cell_config_path = output_root / f"config_{cell_name}.yaml"
            with open(cell_config_path, "w") as f:
                yaml.safe_dump(cell_data, f)

            config = load_config(cell_config_path)
            run_calibration_from_config(config)

            output_dirs.append(cell_output_dir)

    return output_dirs


def _build_arg_parser() -> argparse.ArgumentParser:
    """Build the CLI argument parser for `python benchmarks/sweep_runner.py`.

    Returns:
        A configured `argparse.ArgumentParser`.
    """
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--cameras", type=int, nargs="+", required=True, help="Camera-count grid."
    )
    parser.add_argument(
        "--frames", type=int, nargs="+", required=True, help="Frame-count grid."
    )
    parser.add_argument(
        "--config", type=Path, required=True, help="Base calibration YAML config."
    )
    parser.add_argument(
        "--output-root", type=Path, required=True, help="Sweep output root directory."
    )
    return parser


if __name__ == "__main__":
    from benchmarks.aggregate import aggregate, write_csv, write_latex_fragment

    args = _build_arg_parser().parse_args()
    run_sweep(args.cameras, args.frames, args.config, args.output_root)
    aggregated = aggregate(args.output_root)
    write_csv(aggregated, args.output_root / "sweep.csv")
    write_latex_fragment(
        aggregated,
        args.output_root / "sweep.tex",
        list(aggregated.columns),
    )
