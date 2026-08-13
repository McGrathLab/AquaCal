"""E1: refractive vs non-refractive synthetic comparison (EXP-06).

This is a port of `docs/tutorials/02_synthetic_validation.ipynb`'s `RIG_SIZE = "large"`
preset (cells `cell-rig-size` through `e3jl81minof`, D-12/D-19): E1 calibrates the same
synthetic "realistic" scenario twice -- once with the refractive model (`n_water=1.333`)
and once with the non-refractive model (`n_water=1.0`) -- and compares per-camera
parameter recovery, depth-generalization, and XY-vs-Z reconstruction anisotropy between
the two.

Invoked as `python -m experiments.e1_refractive_comparison`. Inherits the shared
five-flag CLI contract (`--seed`, `--out`, `--force`, `--smoke`, `--check`) from
`experiments._io.build_experiment_arg_parser` (D-21), plus a script-local
`--seeds` flag (D-19.4-14).

Emits into `--out`:
  exp1_parameter_errors.csv, exp2_depth_generalization.csv, exp3_xy_vs_z_anisotropy.csv
    -- FIXED CONTRACTS, byte-for-byte identical headers to the committed baselines the
    external figures repository (read-only, outside this repo) reads (D-19). Do not
    add, remove, reorder, or rename a column.
  exp2_spatial_errors.csv -- E1's own new output, no committed baseline (D-20); not
    compared by --check.
  e1_benchmark_refractive.json, e1_benchmark_nonrefractive.json -- two distinct
    direct-call provenance records (D-09), one per model, because E1 calibrates twice.
  exp1_band.csv, e1_seed_band_provenance.json -- written only by `--seeds`
    (see below); never written by any of the three modes above.

**`--seeds` band mode (D-19.4-14, SC-5a, D-260807-dcv).** `--seeds 42,43,...`
runs E1's depth-generalization path once per listed seed and emits
`exp1_band.csv` (one row per seed x test_depth x model -- 10 seeds x 8 depths
x 2 models = 160 rows at production scale). Its columns are
`exp2_depth_generalization.csv`'s columns PLUS `exp3_xy_vs_z_anisotropy.csv`'s
four non-key columns (`xy_rmse_mm`, `z_rmse_mm`, `anisotropy_ratio`,
`n_points`) PLUS `seed` -- this GAINS COLUMNS on the artifact that already
existed rather than adding a sibling file. `exp3_xy_vs_z_anisotropy.csv`
itself is still written only by the single-seed run. This is the committed,
regenerable artifact behind MF-08's 97-178x deepest-point ratio spread and
the "2 of 10 seeds exceed 2 mm" finding, both of which previously lived only
in gitignored `seed_sweep_19_3/` output -- and now, with `z_rmse_mm` merged
in, is also the regenerable source for the abstract/L281 ~135x headline
ratio, which was previously computable only from the seedless
`exp3_xy_vs_z_anisotropy.csv` or that same gitignored sweep output. **E1
carries NO accuracy claim (D-19.3-17 demoted it)** -- this band exists for
reproducibility, not because E1's numbers move: E1's production
`SCENARIO_NAME = "realistic"` resolves to `generate_real_rig_array()`'s
frozen shared `water_z` and is INERT under this phase's interface fix (it
never reaches `generate_camera_array`). A `--seeds` run NEVER writes
`exp1_parameter_errors.csv`, `exp2_depth_generalization.csv`,
`exp2_spatial_errors.csv`, or `exp3_xy_vs_z_anisotropy.csv` -- those remain
exclusively the single-seed run's artifacts. The band CSV write always
overwrites (force implied for that file only, mirroring E7); no other
artifact's overwrite behavior changes. `--seeds` is mutually exclusive with
`--check`. Each of `e1_benchmark_refractive.json` and
`e1_benchmark_nonrefractive.json` written during a band run additively
carries a `seeds` list holding the resolved seed list, reflecting the LAST
seed's diagnostics/timings/accuracy (one provenance record cannot represent
N independent solves) -- these are seedless legacy records that band mode
must never overwrite with a single seed's values, which is why the band's
OWN provenance lives in a separate, band-owned `e1_seed_band_provenance.json`
sidecar (see below).

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
import json
import logging
import sys
import time
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
from aquacal.io import capture_environment
from aquacal.validation.reconstruction import triangulate_charuco_corners
from experiments._io import (
    build_experiment_arg_parser,
    compare_experiment_csv,
    exit_code_for,
    parse_seed_list,
    resolve_out_dir,
    run_seed_band,
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
# D-19.4-14: the band CSV carries every seed's rows, so `seed` joins the key
# columns -- (test_depth_m, model) alone is no longer unique once multiple
# seeds are concatenated (mirrors E7's BAND_KEY_COLUMNS convention).
BAND_KEY_COLUMNS = ["seed", "test_depth_m", "model"]
# A SECOND band key shape, not an extension of BAND_KEY_COLUMNS. EXP1's rows
# are keyed by (camera, model) and have NO depth axis at all, so its columns
# cannot be merged into exp1_band.csv without reindexing them onto a depth
# they do not vary over -- that would fabricate a depth dependence the
# parameter errors do not have. Hence a separate `exp1_parameter_band.csv`.
PARAMETER_BAND_KEY_COLUMNS = ["seed", "camera", "model"]

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

# D-260807-dcv: the manuscript's ~135x headline ratio (main.tex L68/L281) is raw
# `z_rmse_mm` at the deepest test point, and `z_rmse_mm` previously lived ONLY in
# the seedless `exp3_xy_vs_z_anisotropy.csv` and in gitignored `seed_sweep_19_3/`
# output -- so the published 10-seed band was not regenerable from any committed
# artifact. `_run_band` now merges EXP3's non-key columns onto the band CSV so
# the headline quantity travels with the band. EXP2_COLUMNS/EXP3_COLUMNS
# themselves are untouched -- the single-seed CSVs they pin stay byte-identical.
BAND_MERGED_COLUMNS = EXP2_COLUMNS + [c for c in EXP3_COLUMNS if c not in EXP2_COLUMNS]


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


def merge_band_columns(df_exp2: pd.DataFrame, df_exp3: pd.DataFrame) -> pd.DataFrame:
    """Merge EXP3's non-key columns (including `z_rmse_mm`) onto an EXP2 frame.

    `_build_dataframes` returns both frames built from the SAME `depths` list
    object and the SAME per-depth loop (L359-446), so their `(test_depth_m,
    model)` keys are identical float/str values from a single source -- a
    float-keyed merge is safe here specifically because both sides share that
    one generation site, not in general. `validate="one_to_one"` is kept as
    the executable guard rather than relying on that invariant silently: a
    duplicated key in either input raises instead of silently fanning out
    into extra rows. `seed` is deliberately NOT a merge key -- `run_seed_band`
    stamps the `seed` column onto the returned frame AFTER the runner
    returns, so neither `df_exp2` nor `df_exp3` carries it yet.

    Args:
        df_exp2: `exp2_depth_generalization.csv`-shaped frame, columns
            `EXP2_COLUMNS`.
        df_exp3: `exp3_xy_vs_z_anisotropy.csv`-shaped frame, columns
            `EXP3_COLUMNS`.

    Returns:
        A frame with columns `BAND_MERGED_COLUMNS` (EXP2_COLUMNS then EXP3's
        non-key columns) and the same row count as `df_exp2`.
    """
    merged = pd.merge(
        df_exp2,
        df_exp3,
        on=EXP3_KEY_COLUMNS,
        how="left",
        validate="one_to_one",
    )
    return merged.reindex(columns=BAND_MERGED_COLUMNS)


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


def _run_band(seeds: list[int], out_dir: Path, smoke: bool, force: bool) -> None:
    """`--seeds`: run E1's depth-generalization path once per seed, emit the
    band CSV and per-model provenance (D-19.4-14, SC-5a, D-260807-dcv).

    Writes `exp1_band.csv` (force implied -- see the module docstring's
    "--seeds band mode" section), now carrying `BAND_MERGED_COLUMNS` --
    `EXP2_COLUMNS` plus EXP3's non-key columns (`xy_rmse_mm`, `z_rmse_mm`,
    `anisotropy_ratio`, `n_points`) via `merge_band_columns`, so the
    manuscript's headline `z_rmse_mm` ratio is regenerable from this
    artifact -- and `exp1_parameter_band.csv`, keyed
    `PARAMETER_BAND_KEY_COLUMNS` and carrying `seed` plus all of
    `EXP1_COLUMNS`, so the parameter-level columns (`focal_length_error_pct`,
    `reprojection_rms_px` and the per-camera position errors) are likewise
    regenerable per seed rather than existing only in the single-seed
    `exp1_parameter_errors.csv` -- and `e1_seed_band_provenance.json`, plus both
    `e1_benchmark_<model>.json` sidecars, additively carrying
    `solver_config["seeds"] = seeds`. Deliberately does NOT write
    `exp1_parameter_errors.csv`, `exp2_depth_generalization.csv`,
    `exp2_spatial_errors.csv`, or `exp3_xy_vs_z_anisotropy.csv` -- those
    remain exclusively the single-seed run's artifacts.

    The benchmark payload (`problem_shape`/`timings`/`diagnostics`/
    `accuracy`) is taken from the LAST seed in `seeds`'s run, since a single
    provenance record cannot represent N independent solves; `seeds` records
    which N were actually run so a reader is never left assuming it reflects
    only the last one. Mirrors `e7_interface_ablation._run_band` exactly
    (D-19.4-14) so the two scripts' `--seeds` behavior stays symmetrical.
    """
    scenario_name = "ideal" if smoke else SCENARIO_NAME
    depths = [1.30] if smoke else None

    # Captured ONCE before the seed loop -- capture_environment() shells out to
    # `git rev-parse` per call, and a per-cell call is what split an artifact's
    # recorded SHA before (CLAUDE.md / knowledge-base "Commit nothing during a
    # production run").
    environment = capture_environment()
    start = time.monotonic()

    last_results: dict = {}
    last_timings_by_model: dict = {}
    last_diagnostics_by_model: dict = {}
    last_discard_stats_by_model: dict = {}
    last_scenario = None
    # `run_seed_band` returns ONE concatenated frame and stamps `seed` onto it
    # itself; it cannot return two, and its signature is shared with E7 so it
    # must not grow one. The parameter-level frames are therefore accumulated
    # here and stamped with `seed` inside the runner, mirroring how the five
    # `last_*` accumulators above are carried out of the closure.
    exp1_frames: list[pd.DataFrame] = []

    def _runner(seed: int) -> pd.DataFrame:
        nonlocal last_results, last_timings_by_model, last_diagnostics_by_model
        nonlocal last_discard_stats_by_model, last_scenario

        scenario = create_scenario(scenario_name, seed=seed)
        results: dict = {}
        timings_by_model: dict = {}
        diagnostics_by_model: dict = {}
        discard_stats_by_model: dict = {}
        for label, n_water in MODELS:
            result, detections, timings, diagnostics, discard_stats = _run_one_model(
                scenario, n_water, seed
            )
            results[label] = (result, detections)
            timings_by_model[label] = timings
            diagnostics_by_model[label] = diagnostics
            discard_stats_by_model[label] = discard_stats

        df_exp1, df_exp2, _df_spatial, df_exp3 = _build_dataframes(
            scenario, results, seed, test_depths=depths
        )
        exp1_frames.append(df_exp1.assign(seed=seed))

        last_results = results
        last_timings_by_model = timings_by_model
        last_diagnostics_by_model = diagnostics_by_model
        last_discard_stats_by_model = discard_stats_by_model
        last_scenario = scenario

        return merge_band_columns(df_exp2, df_exp3)

    band_df = run_seed_band(_runner, seeds)
    elapsed_seconds = time.monotonic() - start
    write_experiment_csv(
        band_df,
        out_dir / "exp1_band.csv",
        key_columns=BAND_KEY_COLUMNS,
        # Force is implied for the band CSV only (D-19.4-14): regenerating
        # the band on demand is the entire point of it being reproducible.
        force=True,
    )

    # The parameter-level band. `seed` leads, then all of EXP1_COLUMNS --
    # emitting the full set rather than only the two columns the manuscript
    # needs costs nothing and keeps the per-camera position errors available.
    # EXP1_COLUMNS itself and the single-seed exp1_parameter_errors.csv are
    # untouched: those stay byte-identical to their committed baselines (D-19).
    parameter_band_df = pd.concat(exp1_frames, ignore_index=True)[
        ["seed", *EXP1_COLUMNS]
    ]
    write_experiment_csv(
        parameter_band_df,
        out_dir / "exp1_parameter_band.csv",
        key_columns=PARAMETER_BAND_KEY_COLUMNS,
        # Force is implied for band output, same as exp1_band.csv above
        # (D-19.4-14).
        force=True,
    )

    # Band-owned provenance (D-260807-dcv, mirrors E5/E6's pattern): the
    # e1_benchmark_<model>.json records below are seedless legacy records that
    # band mode must never overwrite with a single seed's values, so the
    # seeds actually run here have nowhere else to be recorded.
    sidecar_path = out_dir / "e1_seed_band_provenance.json"
    with open(sidecar_path, "w") as f:
        json.dump(
            {
                "experiment": "e1_seed_band",
                "schema_version": 1,
                "git_sha": environment.get("git_sha"),
                "seconds": elapsed_seconds,
                "environment": environment,
                "solver_config": {"seeds": list(seeds)},
                # D-260807-dcv: this band varies ONLY the seed, across E1's
                # depth-generalization and xy-vs-z anisotropy sweep on the
                # "realistic" synthetic scenario -- it bounds seed-to-seed
                # variance of those metrics on that synthetic scenario only,
                # not a physical-rig or real-data claim. z_rmse_mm is the
                # column the manuscript's deepest-test-point
                # refractive-vs-non-refractive ratio is computed from; this
                # band exists so that ratio is regenerable from a committed
                # artifact. It ALSO covers exp1_parameter_band.csv's
                # parameter-level columns, which previously existed per-seed
                # only in gitignored sweep output.
                "scope": (
                    "This band varies the SEED across E1's depth-generalization "
                    "and xy-vs-z anisotropy sweep on the 'realistic' synthetic "
                    "scenario, and bounds seed-to-seed variance of "
                    "exp1_band.csv's metrics -- including z_rmse_mm, the column "
                    "the manuscript's deepest-test-point refractive-vs-"
                    "non-refractive ratio is computed from -- on that synthetic "
                    "scenario only. It ALSO bounds seed-to-seed variance of the "
                    "parameter-level columns emitted in exp1_parameter_band.csv "
                    "(focal_length_error_pct, reprojection_rms_px, and the "
                    "per-camera position errors), over the same seeds and the "
                    "same scenario. It is NOT a physical-rig or real-data claim, "
                    "and this sidecar neither asserts nor denies an accuracy "
                    "claim for E1 (D-19.3-17 already demoted E1's own)."
                ),
            },
            f,
            indent=2,
            sort_keys=True,
        )
    print(f"Wrote {sidecar_path}")

    for label, n_water in MODELS:
        result, _detections = last_results[label]
        record_path = out_dir / BENCHMARK_FILENAMES[label]
        solver_config = {
            "robust_loss": "huber",
            "loss_scale": 1.0,
            "refine_intrinsics": True,
            "n_water": n_water,
            "n_air": 1.0,
            "shared_interface": True,
            "ftol": last_diagnostics_by_model[label][
                "stage3_interface_optimization"
            ].ftol,
            "xtol": last_diagnostics_by_model[label][
                "stage3_interface_optimization"
            ].xtol,
            "gtol": last_diagnostics_by_model[label][
                "stage3_interface_optimization"
            ].gtol,
            "seeds": list(seeds),
        }
        write_direct_call_benchmark(
            record_path,
            problem_shape={
                "n_cameras": len(last_scenario.intrinsics),
                "n_frames_calibration": len(last_scenario.board_poses),
                "n_frames_holdout": 0,
                "degenerate_observations_at_solution": last_discard_stats_by_model[
                    label
                ].get("degenerate_observations_at_solution", 0),
            },
            timings=last_timings_by_model[label],
            diagnostics=last_diagnostics_by_model[label],
            solver_config=solver_config,
            accuracy={"reprojection_rms_px": result.diagnostics.reprojection_error_rms},
            # Force is NOT implied for any artifact besides the band CSV
            # (D-19.4-14) -- normal resumability applies here.
            force=force,
        )
        print(f"Wrote {record_path}")


def build_arg_parser() -> argparse.ArgumentParser:
    """Build E1's CLI parser, extending the shared five-flag contract (D-21)
    with a script-local `--seeds` flag (D-19.4-14)."""
    parser = argparse.ArgumentParser(
        description=__doc__, parents=[build_experiment_arg_parser()]
    )
    parser.add_argument(
        "--seeds",
        type=str,
        default=None,
        help="Comma-separated seed list (e.g. '42,43,44') to run a "
        "reproducible band instead of a single seed, emitting exp1_band.csv "
        "(D-19.4-14). Mutually exclusive with --check. The band CSV write "
        "always overwrites (force implied for that file only); no other "
        "artifact's overwrite behavior changes. A --seeds run never writes "
        "exp1_parameter_errors.csv, exp2_depth_generalization.csv, "
        "exp2_spatial_errors.csv, or exp3_xy_vs_z_anisotropy.csv.",
    )
    return parser


def _validate_e1_args(
    parser: argparse.ArgumentParser, args: argparse.Namespace
) -> None:
    """Extend the shared five-flag validation with `--seeds`'s constraints
    (D-19.4-14)."""
    validate_args(parser, args)
    if args.seeds is not None and args.check:
        parser.error("--seeds cannot be combined with --check")


def main(argv: list[str] | None = None) -> int:
    """CLI entry point for `python -m experiments.e1_refractive_comparison`."""
    parser = build_arg_parser()
    args = parser.parse_args(argv)
    _validate_e1_args(parser, args)

    logging.basicConfig(level=logging.INFO, format="%(message)s")

    if args.check:
        return _run_check(args)

    if args.seeds is not None:
        seeds = parse_seed_list(args.seeds)
        out_dir = resolve_out_dir(args.out)
        _run_band(seeds, out_dir, smoke=args.smoke, force=args.force)
        return 0

    if args.smoke:
        return _run_smoke(args)
    return _run_full(args)


if __name__ == "__main__":
    sys.exit(main())
