"""E1: refractive vs non-refractive synthetic comparison (EXP-06).

This is a port of `docs/tutorials/02_synthetic_validation.ipynb`'s `RIG_SIZE = "large"`
preset (cells `cell-rig-size` through `e3jl81minof`, D-12/D-19): E1 calibrates the same
synthetic "realistic" scenario twice -- once with the refractive model (`n_water=1.333`)
and once with the non-refractive model (`n_water=1.0`) -- and compares per-camera
parameter recovery, depth-generalization, and XY-vs-Z reconstruction anisotropy between
the two.

Invoked as `python -m experiments.e1_refractive_comparison`. Inherits the shared
five-flag CLI contract (`--seed`, `--out`, `--force`, `--smoke`, `--check`) from
`experiments._io.build_experiment_arg_parser` (D-21).

Emits into `--out`:
  exp1_parameter_errors.csv, exp2_depth_generalization.csv, exp3_xy_vs_z_anisotropy.csv
    -- FIXED CONTRACTS, byte-for-byte identical headers to the committed baselines the
    external figures repository (read-only, outside this repo) reads (D-19). Do not
    add, remove, reorder, or rename a column.
  exp2_spatial_errors.csv -- E1's own new output, no committed baseline (D-20); not
    compared by --check.
  e1_benchmark_refractive.json, e1_benchmark_nonrefractive.json -- two distinct
    direct-call provenance records (D-09), one per model, because E1 calibrates twice.

E1's reproduction bar (D-19, AMENDED 2026-07-27): within CHECK_RTOL is fully autonomous.
A divergence touching none of D-19's named headline numbers gets a written mechanism and
stays autonomous. Any named headline number moving beyond CHECK_RTOL escalates to the
user -- see `.planning/phases/19.1-experiment-suite-consolidation/19.1-06-PLAN.md`'s
ESCALATION RULE and `19.1-E1-REPRODUCTION.md`.

**D-19.3-11: this module RECORDS the final-solution guard count; it does not
GATE on it.** E1 has no per-row `status` column (its output is a fixed,
byte-identical-header contract, D-19) -- both `e1_benchmark_refractive.json`
and `e1_benchmark_nonrefractive.json` carry
`problem_shape.degenerate_observations_at_solution` (via
`_run_one_model`'s `discard_stats_out` sink), and a non-zero count logs one
prominent warning naming it and stating that first-order optimality is
unreliable for that arm. The actual pass/fail decision, when one is needed,
belongs to plan 19.3-08's queue script, which keeps the gate machine-
checkable without inventing a fourth status vocabulary here. `--smoke`'s
`create_scenario("ideal")` legitimately reports a non-zero count (12
observations, 0 of 1760 corners above the interface at 123.4 mm clearance --
extreme obliquity, not a breached surface, see `19.3-ORCHESTRATOR-NOTES.md`
section 4); that number appearing in smoke output is expected and must never
become an exit code, which is automatic here since nothing in this module
compares the count to anything.
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

import cv2
import numpy as np
import pandas as pd

from aquacal.calibration._observability import SolverDiagnostics
from aquacal.core.board import BoardGeometry
from aquacal.datasets import (
    calibrate_synthetic,
    compute_per_camera_errors,
    create_scenario,
    evaluate_reconstruction,
    generate_dense_xy_grid,
    generate_synthetic_detections,
)
from aquacal.validation.reconstruction import triangulate_charuco_corners
from experiments._io import (
    build_experiment_arg_parser,
    compare_experiment_csv,
    exit_code_for,
    resolve_out_dir,
    validate_args,
    write_direct_call_benchmark,
    write_experiment_csv,
)

logger = logging.getLogger(__name__)

# Numeric tolerance for --check (D-22: numeric, not byte-exact). Unchanged from this
# declaration for the lifetime of this plan -- see the ESCALATION RULE in
# 19.1-06-PLAN.md: raising this to force a pass is exactly the failure it forbids.
CHECK_RTOL = 1e-6

# The exact preset E1 reproduces, matching the notebook's RIG_SIZE = "large" path
# (verified against its stored output, 19.1-RESEARCH.md's cell-by-cell trace).
SCENARIO_NAME = "realistic"
TEST_DEPTHS = [1.10, 1.20, 1.30, 1.40, 1.50, 1.70, 2.00, 2.50]
N_GRID = 7
XY_EXTENT = 0.5
XY_CENTER = (-0.34, 0.55)
TILT_DEG = 3.0
MODELS = [("refractive", 1.333), ("non_refractive", 1.0)]

# E1 calibrates TWICE, so it emits two distinct direct-call benchmark records, one
# per model (RESEARCH Pattern 2) -- never a single shared file.
BENCHMARK_FILENAMES = {
    "refractive": "e1_benchmark_refractive.json",
    "non_refractive": "e1_benchmark_nonrefractive.json",
}

# Pinned key columns for sort-before-write / --check row realignment (Pitfall 5).
EXP1_KEY_COLUMNS = ["camera", "model"]
EXP2_KEY_COLUMNS = ["test_depth_m", "model"]
EXP3_KEY_COLUMNS = ["test_depth_m", "model"]
SPATIAL_KEY_COLUMNS = ["test_depth_m", "model", "x_m", "y_m", "z_m"]

# Pinned column order -- byte-identical to the committed baselines (D-19).
EXP1_COLUMNS = [
    "camera",
    "model",
    "focal_length_error_pct",
    "z_position_error_mm",
    "xy_position_error_mm",
    "gt_x_m",
    "gt_y_m",
    "gt_z_m",
    "est_x_m",
    "est_y_m",
    "est_z_m",
    "reprojection_rms_px",
]
EXP2_COLUMNS = [
    "test_depth_m",
    "model",
    "signed_mean_mm",
    "rmse_mm",
    "scale_factor",
    "calib_depth_min_m",
    "calib_depth_max_m",
]
EXP3_COLUMNS = [
    "test_depth_m",
    "model",
    "xy_rmse_mm",
    "z_rmse_mm",
    "anisotropy_ratio",
    "n_points",
]
SPATIAL_COLUMNS = ["test_depth_m", "model", "x_m", "y_m", "z_m", "signed_error_mm"]


def compute_scale_bias(signed_mean_m: float, square_size_m: float) -> float:
    """Convert a signed reconstruction bias into a depth/scale bias factor.

    This is the ONE origin of the scale-bias formula shared between E1's
    `scale_factor` column (`exp2_depth_generalization.csv`) and E5's
    `scale_bias_frac` column (`index_sensitivity.csv`) -- both quantities are
    computed by this single function (review L3/T-19.2-32).

    Args:
        signed_mean_m: Mean signed 3D distance error, in metres (+ = the
            reconstructed distance overestimates the true distance).
        square_size_m: The ChArUco board's square size, in metres -- the
            reference length the signed bias is expressed as a fraction of.

    Returns:
        A dimensionless scale factor: `1.0` means no bias, `> 1.0` means the
        reconstruction overestimates distances, `< 1.0` means it
        underestimates them.
    """
    return 1.0 + (signed_mean_m / square_size_m)


def compute_xyz_errors(calibration, test_poses, test_detections, board):
    """Decompose triangulated corner error into XY (lateral) and Z (depth) components.

    Ported from `docs/tutorials/02_synthetic_validation.ipynb` cell `jq300wte3tn` --
    the one genuinely novel piece of E1's logic (not already in
    `aquacal.datasets.pipelines`). For each frame, triangulates corners visible in 2+
    cameras via the already-public `triangulate_charuco_corners`, compares each
    triangulated position to its ground-truth position (from the board pose), and
    aggregates the XY/Z error components across every corner in every frame.

    Args:
        calibration: A `CalibrationResult` to evaluate.
        test_poses: List of `BoardPose` ground-truth poses for the test frames.
        test_detections: `DetectionResult` for the same test frames.
        board: `BoardGeometry` supplying each corner's board-frame position.

    Returns:
        A dict with `xy_rmse_mm`, `z_rmse_mm`, `xy_mean_signed_mm`, `z_mean_signed_mm`,
        `ratio` (`z_rmse_mm / xy_rmse_mm`, or `inf` if `xy_rmse_mm` is zero),
        `xy_errors_mm`/`z_errors_mm` (per-point arrays), and `n_points` (the number of
        triangulated corners contributing to the statistics).
    """
    poses_by_frame = {bp.frame_idx: bp for bp in test_poses}

    xy_errors = []
    z_errors = []
    signed_z_errors = []

    for frame_idx in test_detections.frames:
        tri_corners = triangulate_charuco_corners(
            calibration, test_detections, frame_idx
        )
        if not tri_corners:
            continue

        bp = poses_by_frame[frame_idx]
        R_board, _ = cv2.Rodrigues(bp.rvec)

        for corner_id, tri_pos in tri_corners.items():
            if corner_id not in board.corner_positions:
                continue
            p_board = board.corner_positions[corner_id]
            p_gt = R_board @ p_board + bp.tvec

            err = tri_pos - p_gt
            xy_errors.append(np.linalg.norm(err[:2]))
            z_errors.append(abs(err[2]))
            signed_z_errors.append(err[2])

    xy_arr = np.array(xy_errors)
    z_arr = np.array(z_errors)
    signed_z_arr = np.array(signed_z_errors)
    xy_rmse = np.sqrt(np.mean(xy_arr**2)) if len(xy_arr) else 0.0
    z_rmse = np.sqrt(np.mean(z_arr**2)) if len(z_arr) else 0.0
    ratio = z_rmse / xy_rmse if xy_rmse > 0 else float("inf")

    return {
        "xy_rmse_mm": xy_rmse * 1000,
        "z_rmse_mm": z_rmse * 1000,
        "xy_mean_signed_mm": (np.mean(xy_arr) * 1000) if len(xy_arr) else 0.0,
        "z_mean_signed_mm": (np.mean(signed_z_arr) * 1000)
        if len(signed_z_arr)
        else 0.0,
        "ratio": ratio,
        "xy_errors_mm": xy_arr * 1000,
        "z_errors_mm": z_arr * 1000,
        "n_points": len(xy_errors),
    }


def _run_one_model(scenario, n_water, seed):
    """Calibrate one model and return (result, detections, timings, diagnostics,
    discard_stats).

    `discard_stats["degenerate_observations_at_solution"]` (D-19.3-11) is the
    final-solution guard count `calibrate_synthetic` recorded via
    `discard_stats_out`; a non-zero count logs one prominent warning here so
    it is never silently swallowed, but this function never raises on it --
    the library records, the harness (or plan 19.3-08's queue script) gates.
    """
    diag_stage3 = SolverDiagnostics()
    diag_intrinsic_pass = SolverDiagnostics()
    timings: dict[str, float] = {}
    discard_stats: dict[str, int] = {}
    result, detections = calibrate_synthetic(
        scenario,
        n_water=n_water,
        refine_intrinsics=True,
        seed=seed,
        diagnostics_out={
            "stage3_interface_optimization": diag_stage3,
            "stage3_intrinsic_pass": diag_intrinsic_pass,
        },
        timings_out=timings,
        discard_stats_out=discard_stats,
    )
    diagnostics = {
        "stage3_interface_optimization": diag_stage3,
        "stage3_intrinsic_pass": diag_intrinsic_pass,
    }
    n_degenerate = discard_stats.get("degenerate_observations_at_solution", 0)
    if n_degenerate > 0:
        logger.warning(
            "n_water=%s: %d degenerate observation(s) recorded at the final "
            "solution -- first-order optimality is unreliable for this arm "
            "(D-19.3-11).",
            n_water,
            n_degenerate,
        )
    return result, detections, timings, diagnostics, discard_stats


def _build_dataframes(scenario, results, seed, test_depths=None):
    """Run the depth sweep and assemble the four output DataFrames.

    `results` is a dict keyed by model label ("refractive"/"non_refractive") mapping
    to `(CalibrationResult, DetectionResult)`. Follows the notebook's structure
    exactly (RESEARCH Pitfall 1): each test depth's poses and detections are
    generated ONCE and reused by both models' evaluation.

    Args:
        test_depths: Depths to sweep. Defaults to the module-level `TEST_DEPTHS`
            (the full eight-depth preset); `--smoke` passes a single trivial depth
            instead, without mutating the module constant.
    """
    depths = TEST_DEPTHS if test_depths is None else test_depths
    board = BoardGeometry(scenario.board_config)

    errors_by_model = {
        label: compute_per_camera_errors(result, scenario, gauge_correct_z=True)
        for label, (result, _detections) in results.items()
    }

    camera_names = sorted(
        scenario.intrinsics.keys(), key=lambda s: int(s.replace("cam", ""))
    )

    # Every field besides "camera"/"model" comes straight from the widened
    # compute_per_camera_errors dict (D-06.3) -- no inline gt_*/est_* assembly from
    # scenario.extrinsics/result.cameras (D-06(3) anti-pattern). Column selection
    # below (not key construction) is what drops the two distortion-coefficient
    # fields the library still returns but the committed schema never included.
    rows_exp1 = []
    for cam in camera_names:
        for label in results:
            row = dict(errors_by_model[label][cam])
            row["camera"] = cam
            row["model"] = label
            rows_exp1.append(row)
    df_exp1 = pd.DataFrame(rows_exp1)[EXP1_COLUMNS]

    _board_zs = [bp.tvec[2] for bp in scenario.board_poses]
    calib_depth_min_m, calib_depth_max_m = min(_board_zs), max(_board_zs)

    per_depth_poses: list = []
    per_depth_detections: list = []
    per_depth_results: dict[str, list[dict]] = {label: [] for label in results}
    per_depth_xyz: dict[str, list[dict]] = {label: [] for label in results}

    for depth in depths:
        depth_seed = 42 + int(depth * 100)
        test_poses = generate_dense_xy_grid(
            depth=depth,
            n_grid=N_GRID,
            xy_extent=XY_EXTENT,
            xy_center=XY_CENTER,
            tilt_deg=TILT_DEG,
            frame_offset=1000,
            seed=depth_seed,
        )
        test_detections = generate_synthetic_detections(
            intrinsics=scenario.intrinsics,
            extrinsics=scenario.extrinsics,
            water_zs=scenario.water_zs,
            board=board,
            board_poses=test_poses,
            noise_std=scenario.noise_std,
            seed=depth_seed,
        )
        per_depth_poses.append(test_poses)
        per_depth_detections.append(test_detections)

        for label, (result, _detections) in results.items():
            err = evaluate_reconstruction(result, board, test_detections)
            scale = compute_scale_bias(
                err.signed_mean, scenario.board_config.square_size
            )
            per_depth_results[label].append(
                {
                    "depth": depth,
                    "signed_mean_mm": err.signed_mean * 1000,
                    "rmse_mm": err.rmse * 1000,
                    "scale": scale,
                    "spatial": err.spatial,
                }
            )
            xyz = compute_xyz_errors(result, test_poses, test_detections, board)
            xyz["depth"] = depth
            per_depth_xyz[label].append(xyz)

    rows_exp2 = []
    rows_spatial = []
    for i, depth in enumerate(depths):
        for label in results:
            r = per_depth_results[label][i]
            rows_exp2.append(
                {
                    "test_depth_m": r["depth"],
                    "model": label,
                    "signed_mean_mm": r["signed_mean_mm"],
                    "rmse_mm": r["rmse_mm"],
                    "scale_factor": r["scale"],
                    "calib_depth_min_m": calib_depth_min_m,
                    "calib_depth_max_m": calib_depth_max_m,
                }
            )
            sp = r["spatial"]
            if sp is not None and len(sp.signed_errors) > 0:
                for j in range(len(sp.signed_errors)):
                    rows_spatial.append(
                        {
                            "test_depth_m": r["depth"],
                            "model": label,
                            "x_m": sp.positions[j, 0],
                            "y_m": sp.positions[j, 1],
                            "z_m": sp.positions[j, 2],
                            "signed_error_mm": sp.signed_errors[j] * 1000,
                        }
                    )
    df_exp2 = pd.DataFrame(rows_exp2, columns=EXP2_COLUMNS)
    df_spatial = pd.DataFrame(rows_spatial, columns=SPATIAL_COLUMNS)

    rows_exp3 = []
    for i, depth in enumerate(depths):
        for label in results:
            r = per_depth_xyz[label][i]
            rows_exp3.append(
                {
                    "test_depth_m": r["depth"],
                    "model": label,
                    "xy_rmse_mm": r["xy_rmse_mm"],
                    "z_rmse_mm": r["z_rmse_mm"],
                    "anisotropy_ratio": r["ratio"],
                    "n_points": r["n_points"],
                }
            )
    df_exp3 = pd.DataFrame(rows_exp3, columns=EXP3_COLUMNS)

    return df_exp1, df_exp2, df_spatial, df_exp3


def _run_full(args: argparse.Namespace) -> int:
    """Run E1 end to end and write all six artifacts (default mode)."""
    out_dir = resolve_out_dir(args.out)

    print(f"Creating scenario {SCENARIO_NAME!r} (seed={args.seed})...")
    scenario = create_scenario(SCENARIO_NAME, seed=args.seed)
    print(f"  Cameras: {len(scenario.intrinsics)}  Frames: {len(scenario.board_poses)}")

    results = {}
    timings_by_model = {}
    diagnostics_by_model = {}
    discard_stats_by_model = {}
    for label, n_water in MODELS:
        print(f"\nCalibrating {label} model (n_water={n_water})...")
        result, detections, timings, diagnostics, discard_stats = _run_one_model(
            scenario, n_water, args.seed
        )
        print(f"  Reprojection RMS: {result.diagnostics.reprojection_error_rms:.4f} px")
        results[label] = (result, detections)
        timings_by_model[label] = timings
        diagnostics_by_model[label] = diagnostics
        discard_stats_by_model[label] = discard_stats

    print("\nEvaluating depth sweep and anisotropy...")
    df_exp1, df_exp2, df_spatial, df_exp3 = _build_dataframes(
        scenario, results, args.seed
    )

    write_experiment_csv(
        df_exp1,
        out_dir / "exp1_parameter_errors.csv",
        key_columns=EXP1_KEY_COLUMNS,
        force=args.force,
    )
    write_experiment_csv(
        df_exp2,
        out_dir / "exp2_depth_generalization.csv",
        key_columns=EXP2_KEY_COLUMNS,
        force=args.force,
    )
    write_experiment_csv(
        df_spatial,
        out_dir / "exp2_spatial_errors.csv",
        key_columns=SPATIAL_KEY_COLUMNS,
        force=args.force,
    )
    write_experiment_csv(
        df_exp3,
        out_dir / "exp3_xy_vs_z_anisotropy.csv",
        key_columns=EXP3_KEY_COLUMNS,
        force=args.force,
    )

    for label, n_water in MODELS:
        result, _detections = results[label]
        record_path = out_dir / BENCHMARK_FILENAMES[label]
        write_direct_call_benchmark(
            record_path,
            problem_shape={
                "n_cameras": len(scenario.intrinsics),
                "n_frames_calibration": len(scenario.board_poses),
                "n_frames_holdout": 0,
                # D-19.3-11: the final-solution guard count, recorded (never
                # gated) for this arm.
                "degenerate_observations_at_solution": discard_stats_by_model[
                    label
                ].get("degenerate_observations_at_solution", 0),
            },
            timings=timings_by_model[label],
            diagnostics=diagnostics_by_model[label],
            solver_config={
                "robust_loss": "huber",
                "loss_scale": 1.0,
                "refine_intrinsics": True,
                "n_water": n_water,
                "n_air": 1.0,
                "shared_interface": True,
                "ftol": diagnostics_by_model[label][
                    "stage3_interface_optimization"
                ].ftol,
                "xtol": diagnostics_by_model[label][
                    "stage3_interface_optimization"
                ].xtol,
                "gtol": diagnostics_by_model[label][
                    "stage3_interface_optimization"
                ].gtol,
            },
            accuracy={"reprojection_rms_px": result.diagnostics.reprojection_error_rms},
            force=args.force,
        )
        print(f"Wrote {record_path}")

    print("\nE1 run complete.")
    return 0


def _run_smoke(args: argparse.Namespace) -> int:
    """Run E1 at trivial scale, writing to a temp directory, exercising all writers."""
    import tempfile

    with tempfile.TemporaryDirectory(prefix="e1_smoke_") as tmp_dir:
        tmp_path = Path(tmp_dir)
        scenario = create_scenario("ideal", seed=args.seed)
        # Must sit BELOW the water surface (~1.031 m) or the reconstruction
        # sweep finds nothing and silently returns NaN. Moved off the pre-fix
        # 0.30 m when D-19.3-09 raised the preset standoff; 1.30 is drawn from
        # TEST_DEPTHS so the smoke path exercises a depth the real run uses.
        smoke_depths = [1.30]

        results = {}
        timings_by_model = {}
        diagnostics_by_model = {}
        discard_stats_by_model = {}
        for label, n_water in MODELS:
            result, detections, timings, diagnostics, discard_stats = _run_one_model(
                scenario, n_water, args.seed
            )
            results[label] = (result, detections)
            timings_by_model[label] = timings
            diagnostics_by_model[label] = diagnostics
            discard_stats_by_model[label] = discard_stats

        df_exp1, df_exp2, df_spatial, df_exp3 = _build_dataframes(
            scenario, results, args.seed, test_depths=smoke_depths
        )

        write_experiment_csv(
            df_exp1,
            tmp_path / "exp1_parameter_errors.csv",
            key_columns=EXP1_KEY_COLUMNS,
            force=True,
        )
        write_experiment_csv(
            df_exp2,
            tmp_path / "exp2_depth_generalization.csv",
            key_columns=EXP2_KEY_COLUMNS,
            force=True,
        )
        write_experiment_csv(
            df_spatial,
            tmp_path / "exp2_spatial_errors.csv",
            key_columns=SPATIAL_KEY_COLUMNS,
            force=True,
        )
        write_experiment_csv(
            df_exp3,
            tmp_path / "exp3_xy_vs_z_anisotropy.csv",
            key_columns=EXP3_KEY_COLUMNS,
            force=True,
        )
        for label, n_water in MODELS:
            result, _detections = results[label]
            record_path = tmp_path / BENCHMARK_FILENAMES[label]
            write_direct_call_benchmark(
                record_path,
                problem_shape={
                    "n_cameras": len(scenario.intrinsics),
                    "n_frames_calibration": len(scenario.board_poses),
                    "n_frames_holdout": 0,
                    # D-19.3-11: recorded, never gated -- create_scenario
                    # "ideal" legitimately reports a non-zero count here
                    # (extreme obliquity, not a breached interface).
                    "degenerate_observations_at_solution": discard_stats_by_model[
                        label
                    ].get("degenerate_observations_at_solution", 0),
                },
                timings=timings_by_model[label],
                diagnostics=diagnostics_by_model[label],
                solver_config={
                    "robust_loss": "huber",
                    "loss_scale": 1.0,
                    "refine_intrinsics": True,
                    "n_water": n_water,
                    "n_air": 1.0,
                    "shared_interface": True,
                    "ftol": diagnostics_by_model[label][
                        "stage3_interface_optimization"
                    ].ftol,
                    "xtol": diagnostics_by_model[label][
                        "stage3_interface_optimization"
                    ].xtol,
                    "gtol": diagnostics_by_model[label][
                        "stage3_interface_optimization"
                    ].gtol,
                },
                accuracy={
                    "reprojection_rms_px": result.diagnostics.reprojection_error_rms
                },
                force=True,
            )
        print(f"Smoke-wrote all six artifacts to {tmp_path}")

    return 0


def _run_check(args: argparse.Namespace) -> int:
    """Recompute fresh and compare against the three committed CSVs at CHECK_RTOL.

    Never writes. Compares only the THREE files with a committed baseline
    (exp1_parameter_errors.csv, exp2_depth_generalization.csv,
    exp3_xy_vs_z_anisotropy.csv) -- exp2_spatial_errors.csv has no baseline and is
    deliberately excluded (D-20).
    """
    out_dir = resolve_out_dir(args.out)

    print(f"Creating scenario {SCENARIO_NAME!r} (seed={args.seed})...")
    scenario = create_scenario(SCENARIO_NAME, seed=args.seed)

    results = {}
    for label, n_water in MODELS:
        print(f"\nCalibrating {label} model (n_water={n_water})...")
        result, detections, _timings, _diagnostics, _discard_stats = _run_one_model(
            scenario, n_water, args.seed
        )
        results[label] = (result, detections)

    df_exp1, df_exp2, _df_spatial, df_exp3 = _build_dataframes(
        scenario, results, args.seed
    )

    reports = [
        ("exp1_parameter_errors.csv", df_exp1, EXP1_KEY_COLUMNS),
        ("exp2_depth_generalization.csv", df_exp2, EXP2_KEY_COLUMNS),
        ("exp3_xy_vs_z_anisotropy.csv", df_exp3, EXP3_KEY_COLUMNS),
    ]

    worst_exit = 0
    for name, df, key_columns in reports:
        report = compare_experiment_csv(
            df, out_dir / name, key_columns=key_columns, rtol=CHECK_RTOL
        )
        print(f"[{name}] {report.message}")
        worst_exit = max(worst_exit, exit_code_for(report))
    return worst_exit


def build_arg_parser() -> argparse.ArgumentParser:
    """Build E1's CLI parser: the shared five-flag contract, no extra flags."""
    parser = argparse.ArgumentParser(
        description=__doc__, parents=[build_experiment_arg_parser()]
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    """CLI entry point for `python -m experiments.e1_refractive_comparison`."""
    parser = build_arg_parser()
    args = parser.parse_args(argv)
    validate_args(parser, args)

    logging.basicConfig(level=logging.INFO, format="%(message)s")

    if args.smoke:
        return _run_smoke(args)
    if args.check:
        return _run_check(args)
    return _run_full(args)


if __name__ == "__main__":
    sys.exit(main())
