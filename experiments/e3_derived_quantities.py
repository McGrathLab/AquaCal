"""E3: derived quantities and code constants (EXP-07).

Invoked as `python -m experiments.e3_derived_quantities`. Inherits the shared five-flag
CLI contract (`--seed`, `--out`, `--force`, `--smoke`, `--check`) from
`experiments._io.build_experiment_arg_parser` (D-21), plus one script-local flag
(`--include-per-camera-latex`).

Emits, into `--out` (default `experiments/results/`):
    - `code_constants.csv` -- declared-vs-source value, with a pass/fail column (tier 1)
    - `newton_iterations.csv` -- Newton root-find iteration-count distribution over the
      real rig's working volume (tier 2)
    - `cpr_grouping.csv` -- P / groups / fd_reduction for all six `tab:cpr` configurations,
      in both interface modes (tier 3)
    - `cpr_grouping.tex` -- LaTeX fragment of the shared-interface `tab:cpr` rows (default),
      or both interface modes with `--include-per-camera-latex`
    - `cpr_derived_values.tex` -- two regenerated derived prose asides (D-22)
    - `e3_provenance.json` -- minimal environment-only provenance sidecar

**Tier 1 is DECLARED in `tests/unit/test_experiments_e3_constants.py` and only RENDERED
here (D-18).** The inverted import direction (an `experiments/` script importing from
`tests/`) is deliberate: `experiments/` never ships, because `pyproject.toml` scopes
package discovery to `where = ["src"]`, so nothing leaks into the wheel. CI is the gate
that breaks first when a library default changes -- this script only turns the declared
table into a human-readable CSV. This module never re-declares a claim, source, or value.

**Tier 3 owns every `tab:cpr` row (review H1).** The original design split `tab:cpr`
across this file and E4's `benchmark_grid.csv` (D-16). That split does not hold: every
`tab:cpr` row is a tilt-enabled (`normal_fixed=False`) configuration, and the rows
previously assigned to E4 would have been produced by a run whose parameter vector is two
tilt DOF smaller -- a wrong number that looks right. `benchmark_grid.csv` still reports
CPR columns, but they describe E4's OWN configuration and do NOT feed `tab:cpr`.
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
import tempfile
from pathlib import Path

import numpy as np
import pandas as pd

from aquacal.config.schema import BoardConfig
from aquacal.core.board import BoardGeometry
from aquacal.core.camera import Camera
from aquacal.core.interface_model import Interface
from aquacal.core.refractive_geometry import refractive_project_newton_diagnostic
from aquacal.datasets import generate_real_rig_array
from aquacal.datasets.synthetic import generate_real_rig_trajectory
from aquacal.io import capture_environment
from experiments._io import (
    build_experiment_arg_parser,
    compare_experiment_csv,
    resolve_out_dir,
    validate_args,
    write_experiment_csv,
)

logger = logging.getLogger(__name__)

CHECK_RTOL = 1e-6

CODE_CONSTANTS_COLUMNS = [
    "key",
    "claim",
    "source",
    "read_via",
    "declared_value",
    "source_value",
    "pass_fail",
]
CODE_CONSTANTS_KEY_COLUMNS = ["key"]

NEWTON_COLUMNS = [
    "camera",
    "n_points",
    "iter_min",
    "iter_median",
    "iter_max",
    "n_not_converged",
    "incidence_deg_min",
    "incidence_deg_max",
    "residual_max_m",
]
NEWTON_KEY_COLUMNS = ["camera"]

# Same board config `create_scenario("realistic")` uses for the real-rig scenario
# (aquacal.datasets.synthetic._create_scenario's default_board) -- matches real hardware.
_REAL_RIG_BOARD_CONFIG = BoardConfig(
    squares_x=12,
    squares_y=9,
    square_size=0.060,
    marker_size=0.045,
    dictionary="DICT_5X5_100",
)
_INTERFACE_NORMAL = np.array([0.0, 0.0, -1.0], dtype=np.float64)


def _import_declared_constants():
    """Import `DECLARED_CONSTANTS`, bootstrapping `sys.path` from `__file__` (review L2).

    `tests/__init__.py` exists but `tests/unit/__init__.py` does not, so
    `tests.unit.test_experiments_e3_constants` resolves only via PEP 420 namespace-portion
    semantics, and only when the repository root is on `sys.path` -- which today depends on
    the working directory. Deriving the repo root from `__file__` (never the process's
    current working directory) makes this import robust to the caller's working
    directory, including CI's
    `experiments-smoke` job.
    """
    repo_root = Path(__file__).resolve().parents[1]
    repo_root_str = str(repo_root)
    if repo_root_str not in sys.path:
        sys.path.insert(0, repo_root_str)
    try:
        from tests.unit.test_experiments_e3_constants import DECLARED_CONSTANTS
    except ImportError as exc:
        raise ImportError(
            "Could not import DECLARED_CONSTANTS from "
            "tests.unit.test_experiments_e3_constants after inserting repository root "
            f"{repo_root_str!r} at the front of sys.path. This module requires "
            "tests/unit/test_experiments_e3_constants.py to be importable as a PEP 420 "
            "namespace-package member of tests/ from the repository root."
        ) from exc
    return DECLARED_CONSTANTS


def build_code_constants_df() -> pd.DataFrame:
    """Render tier 1: one row per `DECLARED_CONSTANTS` entry, source value read live.

    Does NOT raise on a mismatch -- the CSV is the artifact and CI (via
    `tests/unit/test_experiments_e3_constants.py`) is the gate. A `FAIL` row must be
    visible in the committed file rather than aborting this script's run.
    """
    declared_constants = _import_declared_constants()
    rows = []
    for entry in declared_constants:
        source_value = entry.live()
        rows.append(
            {
                "key": entry.key,
                "claim": entry.claim,
                "source": entry.source,
                "read_via": entry.read_via,
                "declared_value": repr(entry.declared_value),
                "source_value": repr(source_value),
                "pass_fail": "PASS" if source_value == entry.declared_value else "FAIL",
            }
        )
    return pd.DataFrame(rows, columns=CODE_CONSTANTS_COLUMNS)


def build_provenance_sidecar(seed: int) -> dict:
    """Build E3's minimal, environment-only provenance sidecar (Part 4 Rule 2 carve-out).

    Tiers 1 and 2 never run a calibration, so there is no `benchmark.json` to reuse (unlike
    E1/E7's `write_direct_call_benchmark`). This is the only sidecar format E3 uses.
    """
    return {
        "experiment": "e3",
        "schema_version": 1,
        "seed": seed,
        "environment": capture_environment(),
    }


def _summarize_newton_records(camera_label: str, records: list[dict]) -> dict:
    """Aggregate one camera's (or the pooled `ALL`) list of diagnostic dicts into one row.

    `records` holds only the non-`None` `refractive_project_newton_diagnostic` returns --
    the degenerate cases are skipped by the caller and never enter these statistics.
    """
    n_iterations = [r["n_iterations"] for r in records]
    incidence = [r["incidence_angle_deg"] for r in records]
    residuals = [r["final_residual"] for r in records]
    n_not_converged = sum(1 for r in records if not r["converged"])
    return {
        "camera": camera_label,
        "n_points": len(records),
        "iter_min": int(np.min(n_iterations)),
        "iter_median": float(np.median(n_iterations)),
        "iter_max": int(np.max(n_iterations)),
        "n_not_converged": n_not_converged,
        "incidence_deg_min": float(np.min(incidence)),
        "incidence_deg_max": float(np.max(incidence)),
        "residual_max_m": float(np.max(residuals)),
    }


def build_newton_iterations_df(n_frames: int, seed: int) -> pd.DataFrame:
    """Tier 2: measure the Newton root-find iteration distribution over the real rig's
    working volume, through the shipped `refractive_project_newton_diagnostic` (D-19).

    Sweeps `generate_real_rig_trajectory`'s board poses (same substrate E5 uses, D-09/D-20)
    against `generate_real_rig_array`'s 12-camera geometry, calling the diagnostic once per
    board corner per pose per camera. `None` returns (the three degenerate cases) are
    skipped and never enter the iteration statistics. Emits one row per camera plus one
    pooled `ALL` row, the pooled row computed directly from the per-point records (not by
    re-averaging the per-camera summaries).

    Never re-implements the Newton loop and never infers an iteration count from a
    residual -- the public diagnostic is the only source (D-19).

    Does not assert or gate on the observed maximum: if it exceeds four, that is a finding
    for the manuscript, not a failure (D-20).
    """
    intrinsics, extrinsics, water_zs = generate_real_rig_array()
    board_poses = generate_real_rig_trajectory(
        n_frames=n_frames, depth_range=(1.1, 2.0), seed=seed
    )
    board = BoardGeometry(_REAL_RIG_BOARD_CONFIG)
    cameras = {cam: Camera(cam, intrinsics[cam], extrinsics[cam]) for cam in intrinsics}
    interface = Interface(
        normal=_INTERFACE_NORMAL, camera_distances=water_zs, n_air=1.0, n_water=1.333
    )

    per_camera_records: dict[str, list[dict]] = {cam: [] for cam in cameras}
    for pose in board_poses:
        world_corners = board.transform_corners(pose.rvec, pose.tvec)
        for cam_name, camera in cameras.items():
            for point_3d in world_corners.values():
                diagnostic = refractive_project_newton_diagnostic(
                    camera, interface, point_3d
                )
                if diagnostic is None:
                    continue
                per_camera_records[cam_name].append(diagnostic)

    rows = []
    pooled_records: list[dict] = []
    for cam_name in sorted(cameras):
        records = per_camera_records[cam_name]
        pooled_records.extend(records)
        rows.append(_summarize_newton_records(cam_name, records))
    pooled_row = _summarize_newton_records("ALL", pooled_records)
    rows.append(pooled_row)

    logger.info(
        "Newton iterations (pooled, n=%d): min=%d median=%.1f max=%d",
        pooled_row["n_points"],
        pooled_row["iter_min"],
        pooled_row["iter_median"],
        pooled_row["iter_max"],
    )

    return pd.DataFrame(rows, columns=NEWTON_COLUMNS)


def build_arg_parser() -> argparse.ArgumentParser:
    """Build E3's CLI parser, extending the shared five-flag contract (D-21)."""
    parser = argparse.ArgumentParser(
        description=__doc__, parents=[build_experiment_arg_parser()]
    )
    parser.add_argument(
        "--include-per-camera-latex",
        action="store_true",
        help="Also render shared_interface=False rows into cpr_grouping.tex (default: "
        "off). The supplement's sparsity table describes the production (shared-interface) "
        "configuration; per-camera mode belongs where E7 frames it as a deliberate "
        "ablation (D-21).",
    )
    return parser


def _write_tier1_and_sidecar(out_dir: Path, seed: int, force: bool) -> None:
    code_constants_df = build_code_constants_df()
    write_experiment_csv(
        code_constants_df,
        out_dir / "code_constants.csv",
        key_columns=CODE_CONSTANTS_KEY_COLUMNS,
        force=force,
    )

    sidecar_path = out_dir / "e3_provenance.json"
    if force or not sidecar_path.exists():
        sidecar = build_provenance_sidecar(seed)
        sidecar_path.parent.mkdir(parents=True, exist_ok=True)
        with open(sidecar_path, "w") as f:
            json.dump(sidecar, f, indent=2, sort_keys=True)
    else:
        logger.info(
            "Skipping write to %s: file already exists and --force was not given "
            "(resumability).",
            sidecar_path,
        )


def _write_tier2(out_dir: Path, n_frames: int, seed: int, force: bool) -> None:
    newton_df = build_newton_iterations_df(n_frames=n_frames, seed=seed)
    write_experiment_csv(
        newton_df,
        out_dir / "newton_iterations.csv",
        key_columns=NEWTON_KEY_COLUMNS,
        force=force,
    )
    # Tier 3 (Task 3) call site goes here.


def _run_check(out_dir: Path) -> int:
    """`--check`: compare a fresh run against committed baselines, tier by tier."""
    overall_passed = True

    code_constants_path = out_dir / "code_constants.csv"
    if not code_constants_path.exists():
        print(f"No committed baseline at {code_constants_path} to check against.")
        overall_passed = False
    else:
        fresh_code_constants = build_code_constants_df()
        report = compare_experiment_csv(
            fresh_code_constants,
            code_constants_path,
            key_columns=CODE_CONSTANTS_KEY_COLUMNS,
            rtol=CHECK_RTOL,
        )
        print(f"code_constants.csv: {report.message}")
        overall_passed = overall_passed and report.passed

    newton_path = out_dir / "newton_iterations.csv"
    if not newton_path.exists():
        print(f"No committed baseline at {newton_path} to check against.")
        overall_passed = False
    else:
        fresh_newton = build_newton_iterations_df(n_frames=100, seed=42)
        report = compare_experiment_csv(
            fresh_newton, newton_path, key_columns=NEWTON_KEY_COLUMNS, rtol=CHECK_RTOL
        )
        print(f"newton_iterations.csv: {report.message}")
        overall_passed = overall_passed and report.passed

    # Tier 3 (Task 3) --check comparison goes here.

    return 0 if overall_passed else 1


def main(argv: list[str] | None = None) -> int:
    """CLI entry point for `python -m experiments.e3_derived_quantities`."""
    parser = build_arg_parser()
    args = parser.parse_args(argv)
    validate_args(parser, args)

    logging.basicConfig(level=logging.INFO, format="%(message)s")

    if args.check:
        out_dir = resolve_out_dir(args.out)
        return _run_check(out_dir)

    if args.smoke:
        # Honor an explicitly-passed --out; otherwise fall back to a throwaway temp
        # directory so a bare `--smoke` never pollutes experiments/results/.
        if args.out == parser.get_default("out"):
            with tempfile.TemporaryDirectory(prefix="e3_smoke_") as tmp:
                out_dir = resolve_out_dir(Path(tmp))
                _write_tier1_and_sidecar(out_dir, seed=args.seed, force=True)
                _write_tier2(out_dir, n_frames=3, seed=args.seed, force=True)
                # Tier 3 (Task 3) call site goes here.
        else:
            out_dir = resolve_out_dir(args.out)
            _write_tier1_and_sidecar(out_dir, seed=args.seed, force=True)
            _write_tier2(out_dir, n_frames=3, seed=args.seed, force=True)
            # Tier 3 (Task 3) call site goes here.
        return 0

    out_dir = resolve_out_dir(args.out)
    _write_tier1_and_sidecar(out_dir, seed=args.seed, force=args.force)
    _write_tier2(out_dir, n_frames=100, seed=args.seed, force=args.force)
    # Tier 3 (Task 3) call site goes here.
    return 0


if __name__ == "__main__":
    sys.exit(main())
