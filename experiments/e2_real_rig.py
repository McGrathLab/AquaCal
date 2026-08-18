"""E2: re-run the real 13-camera rig calibration against the current library (EXP-04).

This is a port of `docs/tutorials/01_full_pipeline.ipynb`'s `DATA_SOURCE = "zenodo"`
export cell (cell-26, D-12/D-14): E2 is the ONE experiment in this suite that goes
through the full pipeline (`aquacal.run_calibration`), so its `benchmark.json` is
the genuine pipeline-written record, not a hand-rolled sidecar (D-15).

Invoked as `python -m experiments.e2_real_rig`. Inherits the shared five-flag CLI
contract (`--seed`, `--out`, `--force`, `--smoke`, `--check`) from
`experiments._io.build_experiment_arg_parser` (D-21).

Emits exactly six artifacts into `--out`:
  camera_parameters.csv, reprojection_residuals.csv, reconstruction_errors.csv,
  real_rig_metrics.json, benchmark.json (copied, not reconstructed), calibration.json
  (copied).

The three CSV headers are FIXED CONTRACTS the external figures repository (read-only,
outside this repo) reads byte-for-byte (D-14) -- do not add, remove, reorder, or
rename a column.

E2 IS A MULTI-INVOCATION STAGE (D-15/D-16). Its runs are the production/classification
run, the seed band (`--emit-band-configs`), and timing and memory as two DISTINCT runs.
`internals.benchmark_memory` and `internals.log_all_observation_depths` are YAML config
keys, not CLI flags, so `--emit-invocation-configs` GENERATES the three variant configs
from one source config rather than the repo committing three hand-written copies. It is
generated because the release config lives at an absolute Windows path outside this repo
(`C:/Users/tucke/Desktop/Aqua/AquaCal/release_calibration/config.yaml`,
`rerun_19_5.sh:209`): three committed copies would hard-code that path three times over
and Phase 27 would have to edit each one for the Linux machine, where generating from a
single `--config` value means Phase 27 overrides one variable.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import logging
import re
import shutil
import sys
import tempfile
from pathlib import Path
from typing import Sequence

import numpy as np
import pandas as pd

from experiments._io import (
    add_baseline_dir_argument,
    build_experiment_arg_parser,
    compare_experiment_csv_if_present,
    exit_code_for,
    parse_seed_list,
    resolve_baseline_dir,
    resolve_out_dir,
    validate_args,
    write_experiment_csv,
)

logger = logging.getLogger(__name__)

# Numeric tolerance for --check (D-22: numeric, not byte-exact -- BLAS-level
# last-digit differences must not fail a clean re-run's comparison).
CHECK_RTOL = 1e-6

# Pinned column order -- byte-identical to the committed baselines the figures
# repo reads (D-14). Do not reorder.
CAMERA_PARAMS_COLUMNS = [
    "camera",
    "x_m",
    "y_m",
    "z_m",
    "fx_px",
    "fy_px",
    "cx_px",
    "cy_px",
    "water_z_m",
    "h_c_m",
    "reprojection_rms_px",
]
RECONSTRUCTION_COLUMNS = ["x_m", "y_m", "z_m", "signed_error_m", "frame_idx"]
RESIDUALS_COLUMNS = ["residual_x_px", "residual_y_px", "camera", "is_auxiliary"]

# Sort keys for byte-stable CSV writes and for --check's row realignment
# (RESEARCH Pitfall 5). None of these three CSVs has a single natural key, so
# sorting on the full column set is what makes row order byte-stable.
CAMERA_PARAMS_KEY_COLUMNS = ["camera"]
RECONSTRUCTION_KEY_COLUMNS = ["frame_idx", "x_m", "y_m", "z_m"]
RESIDUALS_KEY_COLUMNS = ["camera", "residual_x_px", "residual_y_px"]

DATASET_NAME = "real-rig"


def _dataset_is_cached() -> bool:
    """Check whether the `real-rig` Zenodo dataset is already cached locally.

    Never triggers a download -- reads `aquacal.datasets.download.get_cache_dir()`
    directly rather than calling `load_example`, so smoke mode can decide whether
    to skip before any network I/O could occur (D-25/P7).

    Returns:
        True if `<cache_dir>/real-rig` already exists on disk.
    """
    from aquacal.datasets.download import get_cache_dir

    return (get_cache_dir() / DATASET_NAME).exists()


def build_camera_parameters_df(result) -> pd.DataFrame:
    """Build the `camera_parameters.csv` DataFrame from a fresh `CalibrationResult`.

    Ported from `docs/tutorials/01_full_pipeline.ipynb` cell-26. Every column is
    ASSEMBLED from already-computed pipeline fields (P2) -- no new computation.
    There is no ground-truth water-surface-height column: that column only
    appears for synthetic runs (`scenario is not None`), and E2 is real data.

    Args:
        result: A `CalibrationResult` from `aquacal.run_calibration`.

    Returns:
        A `DataFrame` with columns `CAMERA_PARAMS_COLUMNS`, one row per camera
        (primary and auxiliary).
    """
    rows = []
    for cam in sorted(result.cameras):
        cc = result.cameras[cam]
        C = cc.extrinsics.C
        K = cc.intrinsics.K
        rows.append(
            {
                "camera": cam,
                "x_m": float(C[0]),
                "y_m": float(C[1]),
                "z_m": float(C[2]),
                "fx_px": float(K[0, 0]),
                "fy_px": float(K[1, 1]),
                "cx_px": float(K[0, 2]),
                "cy_px": float(K[1, 2]),
                "water_z_m": float(cc.water_z),
                "h_c_m": float(cc.water_z - C[2]),
                "reprojection_rms_px": float(
                    result.diagnostics.reprojection_error_per_camera.get(
                        cam, float("nan")
                    )
                ),
            }
        )
    return pd.DataFrame(rows, columns=CAMERA_PARAMS_COLUMNS)


def build_residuals_df(result) -> pd.DataFrame:
    """Build the `reprojection_residuals.csv` DataFrame from a fresh result.

    NOTE on a plan-vs-code divergence (deviation, Rule 1): a fresh call to
    `aquacal.run_calibration` never populates a live `ReprojectionErrors` object
    the way the notebook's *synthetic* branch does (that variable, called
    `reprojection_result` in the notebook, is only ever set on the
    `synthetic-small`/`synthetic-large` branches -- confirmed by reading
    `docs/tutorials/01_full_pipeline.ipynb` cell-7 in full). The Zenodo/real-rig
    branch has always relied on the "loaded-from-saved-calibration" fallback --
    `result.diagnostics.per_corner_residuals` / `per_corner_camera_labels` --
    which are populated here because the shipped dataset's `config.yaml` sets
    `validation.save_detailed_residuals: true` (confirmed in
    `19.1-E2-DATASET-FINDINGS.md`). This function therefore reads
    `per_corner_residuals`/`per_corner_camera_labels` directly rather than a
    nonexistent live "reprojection_result" object.

    Args:
        result: A `CalibrationResult` from `aquacal.run_calibration`.

    Returns:
        A `DataFrame` with columns `RESIDUALS_COLUMNS`.

    Raises:
        RuntimeError: If `per_corner_residuals`/`per_corner_camera_labels` are
            `None` -- which would mean the dataset's config no longer sets
            `save_detailed_residuals: true`.
    """
    residuals = result.diagnostics.per_corner_residuals
    labels = result.diagnostics.per_corner_camera_labels
    if residuals is None or labels is None:
        raise RuntimeError(
            "result.diagnostics.per_corner_residuals/per_corner_camera_labels "
            "are None -- expected them populated because the real-rig dataset's "
            "config.yaml sets validation.save_detailed_residuals: true. Without "
            "them, reprojection_residuals.csv cannot be built."
        )
    aux_set = {name for name, cc in result.cameras.items() if cc.is_auxiliary}
    df = pd.DataFrame(
        {
            "residual_x_px": np.asarray(residuals)[:, 0],
            "residual_y_px": np.asarray(residuals)[:, 1],
            "camera": list(labels),
            "is_auxiliary": [lbl in aux_set for lbl in labels],
        }
    )
    return df[RESIDUALS_COLUMNS]


def build_reconstruction_df(spatial) -> pd.DataFrame:
    """Build the `reconstruction_errors.csv` DataFrame from loaded spatial measurements.

    Args:
        spatial: A `SpatialMeasurements` instance, typically from
            `load_spatial_measurements(output_dir / "spatial_measurements.csv")`
            (A3's resolved YES verdict -- see `19.1-E2-DATASET-FINDINGS.md`).

    Returns:
        A `DataFrame` with columns `RECONSTRUCTION_COLUMNS`.
    """
    df = pd.DataFrame(
        {
            "x_m": spatial.positions[:, 0],
            "y_m": spatial.positions[:, 1],
            "z_m": spatial.positions[:, 2],
            "signed_error_m": spatial.signed_errors,
            "frame_idx": spatial.frame_indices,
        }
    )
    return df[RECONSTRUCTION_COLUMNS]


def build_real_rig_metrics(result, spatial, square_size_m: float) -> dict:
    """Assemble `real_rig_metrics.json`'s content (D-16's nine §3 quantities).

    Every value is ASSEMBLED from already-computed pipeline fields (P2), except
    the inter-corner MAE and mean-relative-error percentage, which RESEARCH
    explicitly permits deriving inline in three lines from the loaded
    per-measurement signed errors -- this is exactly what
    `compute_3d_distance_errors` does internally, applied to already-saved
    per-point data instead of re-triangulating (the Zenodo path retains no
    `detections` to re-triangulate from).

    Args:
        result: A `CalibrationResult` from `aquacal.run_calibration`.
        spatial: The `SpatialMeasurements` loaded from
            `output_dir/spatial_measurements.csv`.
        square_size_m: `result.board.square_size`, the board's known square
            size in meters, used for the percent-relative-error derivation.

    Returns:
        A dict with the nine named quantities plus a `provenance` sub-object
        naming, for each one, which pipeline field or file it came from.
    """
    per_cam = result.diagnostics.reprojection_error_per_camera
    aux_names = [name for name, cc in result.cameras.items() if cc.is_auxiliary]
    primary_vals = {
        cam: v for cam, v in per_cam.items() if cam not in aux_names and not np.isnan(v)
    }

    signed_errors = np.asarray(spatial.signed_errors, dtype=float)
    mae_m = float(np.mean(np.abs(signed_errors)))
    rmse_m = float(np.sqrt(np.mean(signed_errors**2)))
    percent_relative = float(mae_m / square_size_m * 100)

    water_z_values = {round(float(cc.water_z), 9) for cc in result.cameras.values()}
    water_z_m = float(next(iter(sorted(water_z_values))))

    heights = [
        float(cc.water_z - cc.extrinsics.C[2])
        for name, cc in result.cameras.items()
        if name not in aux_names
    ]

    return {
        "mean_reprojection_px": float(result.diagnostics.reprojection_error_rms),
        # NOT the same statistic as the line above, and the manuscript's §3
        # "mean reprojection error" is THIS one (added 2026-07-27). §3's 0.88 px is
        # the mean of the per-camera RMS values (release diagnostics.json gives
        # 0.8786), whereas `mean_reprojection_px` above is the single pooled RMS over
        # all observations (release gives 1.0191). Comparing one against the other
        # silently mixes two statistics under one label -- exactly the "one number,
        # one origin" failure this suite exists to prevent -- so both are emitted
        # explicitly and the delta table must compare like with like.
        "mean_per_camera_reprojection_px": float(
            sum(primary_vals.values()) / len(primary_vals)
        ),
        "reprojection_range_px": [
            float(min(primary_vals.values())),
            float(max(primary_vals.values())),
        ],
        "auxiliary_reprojection_px": {
            name: float(per_cam[name]) for name in aux_names if name in per_cam
        },
        "inter_corner_mae_mm": mae_m * 1000,
        "inter_corner_rmse_mm": rmse_m * 1000,
        "mean_relative_error_pct": percent_relative,
        "n_comparisons": int(len(signed_errors)),
        "water_z_m": water_z_m,
        "camera_height_range_m": [float(min(heights)), float(max(heights))],
        "provenance": {
            "mean_reprojection_px": (
                "result.diagnostics.reprojection_error_rms -- the POOLED RMS over "
                "all observations. This is NOT the quantity the manuscript's §3 "
                "calls 'mean reprojection error'; see "
                "mean_per_camera_reprojection_px."
            ),
            "mean_per_camera_reprojection_px": (
                "mean of result.diagnostics.reprojection_error_per_camera over "
                "primary (non-auxiliary) cameras -- this IS the §3 quantity, computed "
                "from THIS run. Do NOT read it as the manuscript's 0.88 px: that came "
                "from the 2026-07 release_calibration diagnostics.json (0.8786 px) and "
                "is SUPERSEDED as a description of this field (see "
                "MANUSCRIPT-FINDINGS MF-19)."
            ),
            "reprojection_range_px": (
                "min/max of result.diagnostics.reprojection_error_per_camera "
                "over primary (non-auxiliary) cameras"
            ),
            "auxiliary_reprojection_px": (
                "result.diagnostics.reprojection_error_per_camera, keyed by "
                "each auxiliary camera's name"
            ),
            "inter_corner_mae_mm": (
                "mean(abs(signed_errors)) from "
                "output_dir/spatial_measurements.csv (load_spatial_measurements), "
                "converted to mm"
            ),
            "inter_corner_rmse_mm": (
                "sqrt(mean(signed_errors**2)) from "
                "output_dir/spatial_measurements.csv (load_spatial_measurements), "
                "converted to mm"
            ),
            "mean_relative_error_pct": (
                "inter_corner_mae_mm / (result.board.square_size * 1000) * 100"
            ),
            "n_comparisons": (
                "len(signed_errors) from output_dir/spatial_measurements.csv"
            ),
            "water_z_m": (
                "cc.water_z (shared across all cameras under shared_interface); "
                "identical to camera_parameters.csv's water_z_m column"
            ),
            "camera_height_range_m": (
                "min/max of cc.water_z - cc.extrinsics.C[2] over primary cameras; "
                "identical to camera_parameters.csv's h_c_m column"
            ),
        },
    }


def _build_stub_result():
    """Build a minimal, valid `CalibrationResult` for smoke-mode CSV/JSON coverage.

    Used only when `--smoke` is passed and the dataset IS cached (P7: smoke mode
    must exercise the CSV/JSON writing code paths even though it never runs the
    full calibration). Two cameras (one auxiliary) is enough to exercise every
    column and the `is_auxiliary` branch.

    Returns:
        A `CalibrationResult` with fabricated but schema-valid values.
    """
    from aquacal.config.schema import (
        BoardConfig,
        CalibrationMetadata,
        CalibrationResult,
        CameraCalibration,
        CameraExtrinsics,
        CameraIntrinsics,
        DiagnosticsData,
        InterfaceParams,
    )

    identity = np.eye(3)
    intrinsics = CameraIntrinsics(
        K=np.array([[1000.0, 0.0, 320.0], [0.0, 1000.0, 240.0], [0.0, 0.0, 1.0]]),
        dist_coeffs=np.zeros(5),
        image_size=(640, 480),
    )
    cam0 = CameraCalibration(
        name="cam0",
        intrinsics=intrinsics,
        extrinsics=CameraExtrinsics(R=identity, t=np.zeros(3)),
        water_z=1.0,
        is_auxiliary=False,
    )
    aux0 = CameraCalibration(
        name="aux0",
        intrinsics=intrinsics,
        extrinsics=CameraExtrinsics(R=identity, t=np.array([0.1, 0.0, 0.0])),
        water_z=1.0,
        is_auxiliary=True,
    )
    diagnostics = DiagnosticsData(
        reprojection_error_rms=1.0,
        reprojection_error_per_camera={"cam0": 1.0, "aux0": 5.0},
        validation_3d_error_mean=0.001,
        validation_3d_error_std=0.0005,
        per_corner_residuals=np.array(
            [[0.1, -0.2], [0.3, 0.1], [1.0, -1.0], [0.5, 0.5]]
        ),
        per_corner_camera_labels=["cam0", "cam0", "aux0", "aux0"],
    )
    return CalibrationResult(
        cameras={"cam0": cam0, "aux0": aux0},
        interface=InterfaceParams(normal=np.array([0.0, 0.0, -1.0])),
        board=BoardConfig(
            squares_x=12,
            squares_y=9,
            square_size=0.06,
            marker_size=0.045,
            dictionary="DICT_5X5_100",
        ),
        diagnostics=diagnostics,
        metadata=CalibrationMetadata(
            calibration_date="stub",
            software_version="stub",
            config_hash="stub",
            num_frames_used=0,
            num_frames_holdout=0,
            seed=42,
        ),
    )


def _build_stub_spatial():
    """Build a minimal `SpatialMeasurements` for smoke-mode CSV coverage."""
    from aquacal.validation.reconstruction import SpatialMeasurements

    return SpatialMeasurements(
        positions=np.array([[0.0, 0.0, 1.0], [0.1, 0.1, 1.1]]),
        signed_errors=np.array([0.0005, -0.0003]),
        frame_indices=np.array([0, 1], dtype=np.int32),
    )


def _run_smoke(args: argparse.Namespace) -> int:
    """Execute `--smoke` mode: visible SKIPPED if the dataset is absent (D-25/P7).

    When the dataset IS cached, exercises the CSV/JSON writer code paths against
    a stub result written to a throwaway temp directory -- never the real
    `--out` directory, and never a full calibration run.

    Args:
        args: Parsed CLI namespace.

    Returns:
        Process exit code (always 0 for smoke mode).
    """
    if not _dataset_is_cached():
        print(
            "SKIPPED: real-rig dataset not cached locally (would require a "
            "~164 MB Zenodo download); skipping the full run in smoke mode."
        )
        return 0

    print(
        "Dataset is cached locally; exercising CSV/JSON writer code paths "
        "against a stub result (smoke mode does not run the full calibration)."
    )
    stub_result = _build_stub_result()
    stub_spatial = _build_stub_spatial()

    with tempfile.TemporaryDirectory(prefix="e2_smoke_") as tmp_dir:
        tmp_path = Path(tmp_dir)
        df_cameras = build_camera_parameters_df(stub_result)
        df_residuals = build_residuals_df(stub_result)
        df_reconstruction = build_reconstruction_df(stub_spatial)
        metrics = build_real_rig_metrics(
            stub_result, stub_spatial, stub_result.board.square_size
        )

        write_experiment_csv(
            df_cameras,
            tmp_path / "camera_parameters.csv",
            key_columns=CAMERA_PARAMS_KEY_COLUMNS,
            force=True,
        )
        write_experiment_csv(
            df_residuals,
            tmp_path / "reprojection_residuals.csv",
            key_columns=RESIDUALS_KEY_COLUMNS,
            force=True,
        )
        write_experiment_csv(
            df_reconstruction,
            tmp_path / "reconstruction_errors.csv",
            key_columns=RECONSTRUCTION_KEY_COLUMNS,
            force=True,
        )
        import json

        (tmp_path / "real_rig_metrics.json").write_text(json.dumps(metrics, indent=2))
        print(f"Smoke-wrote three CSVs and real_rig_metrics.json to {tmp_path}")

    return 0


def _fold_check_reports(reports) -> int:
    """Print one verdict line per compared artifact and fold them to an exit code.

    A `None` report means the baseline file does not exist. That is an N/A --
    not a failure -- because two of E2's three artifacts are gitignored by
    deliberate DATA-01b policy (ruling A4). But an all-N/A `--check` is
    VACUOUS and must never read as a pass: it compared nothing, so it exits
    nonzero with an explicit message (T-26-18).

    Args:
        reports: Sequence of `(name, baseline_path, report_or_None)` triples.

    Returns:
        0 if at least one baseline was present and every present baseline
        matched; 1 otherwise.
    """
    worst_exit = 0
    n_absent = 0
    for name, baseline_path, report in reports:
        if report is None:
            n_absent += 1
            print(
                f"[{name}] N/A -- no committed baseline at {baseline_path} "
                "(gitignored by deliberate DATA-01b policy; ships only in the "
                "Zenodo archive). Not counted as a failure."
            )
            continue
        print(f"[{name}] {report.message}")
        worst_exit = max(worst_exit, exit_code_for(report))

    if reports and n_absent == len(reports):
        print(
            "VACUOUS CHECK: every baseline was absent, so nothing was compared. "
            "Exiting nonzero -- an all-N/A --check is not a reproduction claim. "
            "Point --baseline-dir at a tree that holds the baselines, or use "
            "check_e2_band's real_rig_metrics.json comparison instead."
        )
        return 1
    return worst_exit


def _run_check(args: argparse.Namespace) -> int:
    """Execute `--check` mode: run the real calibration, diff against baselines.

    Never writes. Compares the freshly built DataFrames against the CSVs in
    `resolve_baseline_dir(args.baseline_dir, args.out)` at `CHECK_RTOL`,
    printing the worst offending cell per file.

    HONEST CONTRACT (SP-5, ruling A4) -- CONTEXT's "`--check` survives on E3 and
    E2 only" is optimistic for E2, and DRIVER-03's contract table must not
    repeat it uncorrected. Of the THREE artifacts compared here, only
    `camera_parameters.csv` has a committed baseline. `reprojection_residuals.csv`
    and `reconstruction_errors.csv` are gitignored by deliberate DATA-01b policy
    (`.gitignore:238-239`) and ship only in the Zenodo archive, so neither
    `experiments/results/` nor the `experiments/pre_rerun_baseline/` archive
    holds them. Before this function used `compare_experiment_csv_if_present`,
    a clean checkout raised `FileNotFoundError` AFTER a 50-87 minute
    calibration had already run. It now reports those two as N/A.

    The better-anchored alternative, for anyone choosing a reproduction signal:
    `check_e2_band` already compares `real_rig_metrics.json` NUMERICALLY at
    `_E2_METRICS_RTOL = 1e-6` (`check_rerun_gates.py:1340`). That is a working
    mechanism where this `--check` is, on one of three artifacts, not.

    Args:
        args: Parsed CLI namespace.

    Returns:
        0 if every PRESENT baseline matched within tolerance and at least one
        was present; 1 otherwise (including the all-absent vacuous case).
    """
    out_dir = resolve_out_dir(args.out)
    baseline_dir = resolve_baseline_dir(getattr(args, "baseline_dir", None), out_dir)
    result, spatial, _output_dir = _run_real_calibration(args)

    df_cameras = build_camera_parameters_df(result)
    df_residuals = build_residuals_df(result)
    df_reconstruction = build_reconstruction_df(spatial)

    camera_params_path = baseline_dir / "camera_parameters.csv"
    residuals_path = baseline_dir / "reprojection_residuals.csv"
    reconstruction_path = baseline_dir / "reconstruction_errors.csv"

    reports = [
        (
            "camera_parameters.csv",
            camera_params_path,
            compare_experiment_csv_if_present(
                df_cameras,
                camera_params_path,
                key_columns=CAMERA_PARAMS_KEY_COLUMNS,
                rtol=CHECK_RTOL,
            ),
        ),
        (
            "reprojection_residuals.csv",
            residuals_path,
            compare_experiment_csv_if_present(
                df_residuals,
                residuals_path,
                key_columns=RESIDUALS_KEY_COLUMNS,
                rtol=CHECK_RTOL,
            ),
        ),
        (
            "reconstruction_errors.csv",
            reconstruction_path,
            compare_experiment_csv_if_present(
                df_reconstruction,
                reconstruction_path,
                key_columns=RECONSTRUCTION_KEY_COLUMNS,
                rtol=CHECK_RTOL,
            ),
        ),
    ]

    return _fold_check_reports(reports)


def _run_real_calibration(args: argparse.Namespace):
    """Download (if needed)/load the real-rig dataset and run the full pipeline.

    Mirrors `docs/tutorials/01_full_pipeline.ipynb` cell-7's Zenodo branch: the
    dataset's `config.yaml` uses paths relative to the dataset's own cache
    directory, so the process `cwd` is temporarily changed to
    `dataset.cache_path` for the duration of the `run_calibration` call and
    restored afterward regardless of outcome.

    Args:
        args: Parsed CLI namespace (`args.seed` is logged but not threaded into
            the dataset's own config, which pins its own `seed`/`initial_water_z`
            -- the dataset is a real published archive, not a synthetic
            generator call).

    Returns:
        A `(result, spatial)` tuple: the full `CalibrationResult`, and the
        `SpatialMeasurements` loaded from `output_dir/spatial_measurements.csv`.
    """
    import os

    from aquacal import run_calibration
    from aquacal.datasets import load_example

    if getattr(args, "config", None) is not None:
        # Explicit-config path (added 2026-07-27; claim corrected 2026-08-17). The
        # PUBLISHED Zenodo archive is NO LONGER frame-subsampled. Record 21889922
        # (4.35 GB), which the manifest was repointed to in 25655f7, ships
        # 13 x 262 extrinsic frames plus its own config_paper.yaml at
        # frame_step: 1 / max_calibration_frames: 200, and a fresh run off it
        # gives 262 usable frames -> 210/52 split -> 200 calibration frames and
        # reconstruction.num_comparisons = 7762 (verified 2026-08-12). The
        # ~4.3x-subsampled extraction (60 usable -> 12 validation -> 1,817
        # comparisons) was the RETIRED record 18645385, not this one. So this
        # branch is not required to reach the section-3 frameset; it exists to
        # point at a different capture or a variant config. Whether the current
        # library reproduces section-3's VALUES is separate and open (MF-19).
        # See .planning/phases/19.1-experiment-suite-consolidation/
        # 19.1-E2-FRAMESET-PROVENANCE.md -- read its supersession header first;
        # its frameset table describes the retired record.
        config_path = Path(args.config).resolve()
        if not config_path.is_file():
            raise FileNotFoundError(f"--config path does not exist: {config_path}")
        run_root = config_path.parent
        logger.info("E2 real-rig run: using explicit config %s", config_path)
        original_cwd = os.getcwd()
        os.chdir(run_root)
        try:
            print("Running full calibration pipeline from explicit config...")
            result = run_calibration(str(config_path), verbose=True)
        finally:
            os.chdir(original_cwd)

        from aquacal import load_config

        cfg = load_config(str(config_path))
        output_dir = Path(cfg.output_dir)
        if not output_dir.is_absolute():
            output_dir = (run_root / output_dir).resolve()
        from aquacal.validation.reconstruction import load_spatial_measurements

        spatial = load_spatial_measurements(output_dir / "spatial_measurements.csv")
        return result, spatial, output_dir

    print(f"Loading dataset {DATASET_NAME!r} (cached locally if already downloaded)...")
    dataset = load_example(DATASET_NAME)
    config_path = dataset.cache_path / "config.yaml"

    logger.info(
        "E2 real-rig run: --seed=%s was parsed but is NOT threaded into this "
        "run -- the dataset ships its own config.yaml with its own seed/"
        "initial_water_z, and E2 reproduces a published archive as a reader "
        "would, not a synthetic scenario.",
        args.seed,
    )

    original_cwd = os.getcwd()
    os.chdir(dataset.cache_path)
    try:
        print("Running full calibration pipeline (Stages 1-4, ~15-20 min)...")
        result = run_calibration(str(config_path), verbose=True)
    finally:
        os.chdir(original_cwd)

    output_dir = dataset.cache_path / "output"
    from aquacal.validation.reconstruction import load_spatial_measurements

    spatial = load_spatial_measurements(output_dir / "spatial_measurements.csv")
    return result, spatial, output_dir


def _run_full(args: argparse.Namespace) -> int:
    """Execute the default (non-smoke, non-check) mode: run E2 for the record.

    Args:
        args: Parsed CLI namespace.

    Returns:
        Process exit code (0 on success).
    """
    out_dir = resolve_out_dir(args.out)
    result, spatial, output_dir = _run_real_calibration(args)

    df_cameras = build_camera_parameters_df(result)
    df_residuals = build_residuals_df(result)
    df_reconstruction = build_reconstruction_df(spatial)
    metrics = build_real_rig_metrics(result, spatial, result.board.square_size)

    write_experiment_csv(
        df_cameras,
        out_dir / "camera_parameters.csv",
        key_columns=CAMERA_PARAMS_KEY_COLUMNS,
        force=args.force,
    )
    write_experiment_csv(
        df_residuals,
        out_dir / "reprojection_residuals.csv",
        key_columns=RESIDUALS_KEY_COLUMNS,
        force=args.force,
    )
    write_experiment_csv(
        df_reconstruction,
        out_dir / "reconstruction_errors.csv",
        key_columns=RECONSTRUCTION_KEY_COLUMNS,
        force=args.force,
    )

    import json

    metrics_path = out_dir / "real_rig_metrics.json"
    if not metrics_path.exists() or args.force:
        metrics_path.write_text(json.dumps(metrics, indent=2, sort_keys=True))
        print(f"Wrote {metrics_path}")
    else:
        print(f"Skipping {metrics_path}: already exists and --force was not given.")

    # benchmark.json and calibration.json are COPIED from the pipeline's own
    # writes -- never reconstructed (D-15).
    for artifact_name in ("benchmark.json", "calibration.json"):
        src = output_dir / artifact_name
        dst = out_dir / artifact_name
        if not src.exists():
            raise FileNotFoundError(
                f"Expected the pipeline to have written {src}, but it does not "
                "exist. This is the genuine pipeline record E2 is supposed to "
                "copy, not construct."
            )
        if dst.exists() and not args.force:
            print(f"Skipping copy to {dst}: already exists and --force was not given.")
            continue
        shutil.copy2(src, dst)
        print(f"Copied {src} -> {dst}")

    print("E2 real-rig run complete.")
    return 0


# ---------------------------------------------------------------------------
# COV-07: seed-variant config generation (split/holdout band, D-19.5-05)
# ---------------------------------------------------------------------------

_SEED_LINE_RE = re.compile(r"^seed:(\s|$)")
_TOP_LEVEL_KEY_RE = re.compile(r"^(\S)")
_OUTPUT_DIR_LINE_RE = re.compile(r"^(\s+)output_dir:\s*(.*)$")


def _line_ending(line: str) -> str:
    """Return the line-ending characters of `line` (`\\r\\n`, `\\n`, or `''`)."""
    if line.endswith("\r\n"):
        return "\r\n"
    if line.endswith("\n"):
        return "\n"
    return ""


def _find_top_level_index(lines: list[str], key: str) -> int | None:
    """Return the index of the top-level (column-0) `{key}:` line, or `None`."""
    pattern = re.compile(rf"^{re.escape(key)}:\s*(#.*)?$")
    for i, line in enumerate(lines):
        if pattern.match(line):
            return i
    return None


def build_seed_variant_config(source_text: str, seed: int, output_dir: str) -> str:
    """Return `source_text` with `seed:` and `paths.output_dir` set (COV-07).

    A pure text-to-text transform: the top-level `seed:` key is replaced if
    present or inserted (immediately before the top-level `paths:` block, or
    at end of file if there is no `paths:` block) if absent, and the
    `paths.output_dir` value is replaced in place. Every other line --
    comments, blank lines, key order, camera lists, video paths -- survives
    byte-for-byte. A `yaml.safe_load`/`safe_dump` round-trip is deliberately
    NOT used: it destroys comments and reorders keys, which would make the
    "only two keys changed" assertion this function exists to satisfy
    unverifiable.

    Args:
        source_text: The full text of a source `config.yaml`.
        seed: The value to write into the top-level `seed:` key.
        output_dir: The value to write into `paths.output_dir` (written as a
            double-quoted YAML scalar, verbatim).

    Returns:
        The transformed config text.

    Raises:
        ValueError: If no `paths.output_dir` line is found to rewrite.
    """
    lines = source_text.splitlines(keepends=True)
    default_ending = "\r\n" if "\r\n" in source_text else "\n"

    # --- seed: replace if present, else insert before `paths:` (or at EOF) ---
    seed_idx = next(
        (i for i, line in enumerate(lines) if _SEED_LINE_RE.match(line)), None
    )
    if seed_idx is not None:
        ending = _line_ending(lines[seed_idx]) or default_ending
        lines[seed_idx] = f"seed: {seed}{ending}"
    else:
        paths_idx = _find_top_level_index(lines, "paths")
        insert_idx = paths_idx if paths_idx is not None else len(lines)
        ending = default_ending
        if insert_idx > 0:
            ending = _line_ending(lines[insert_idx - 1]) or default_ending
        lines.insert(insert_idx, f"seed: {seed}{ending}")

    # --- paths.output_dir: replace value in place, scoped to the paths block ---
    paths_idx = _find_top_level_index(lines, "paths")
    output_dir_idx = None
    indent = None
    if paths_idx is not None:
        for i in range(paths_idx + 1, len(lines)):
            line = lines[i]
            stripped = line.rstrip("\r\n")
            if stripped == "":
                continue
            if _TOP_LEVEL_KEY_RE.match(stripped):
                break  # left the paths: block
            match = _OUTPUT_DIR_LINE_RE.match(line)
            if match:
                output_dir_idx = i
                indent = match.group(1)
                break

    if output_dir_idx is None:
        raise ValueError(
            "build_seed_variant_config: no 'paths.output_dir' line found in "
            "source_text to rewrite"
        )

    quoted_output_dir = json.dumps(output_dir)
    ending = _line_ending(lines[output_dir_idx]) or default_ending
    lines[output_dir_idx] = f"{indent}output_dir: {quoted_output_dir}{ending}"

    return "".join(lines)


def emit_seed_variant_configs(
    source_path: Path, seeds: Sequence[int], band_dir: Path
) -> list[Path]:
    """Write one seed-variant `config.yaml` per seed into `band_dir` (COV-07).

    Each variant differs from `source_path` in exactly two keys: the
    top-level `seed:` and `paths.output_dir` (set to
    `band_dir / f"seed_{seed}"`). Refuses to write if `band_dir` resolves
    inside `source_path.parent` -- the release tree that produced the
    manuscript's Section 3 numbers must never be a variant's write target
    (T-19.5-07-01).

    Args:
        source_path: Path to the source `config.yaml` (read-only; never
            modified by this function).
        seeds: The seeds to emit variants for, in order.
        band_dir: Directory to write `config_seed{seed}.yaml` files into.

    Returns:
        The list of written variant config paths, in seed order.

    Raises:
        ValueError: If `band_dir` resolves inside `source_path.parent`.
    """
    source_path = Path(source_path).resolve()
    resolved_band_dir = Path(band_dir).resolve()
    source_dir = source_path.parent

    if resolved_band_dir == source_dir or source_dir in resolved_band_dir.parents:
        raise ValueError(
            f"emit_seed_variant_configs: band_dir {resolved_band_dir} resolves "
            f"inside the source config's own directory {source_dir}; a band run "
            "would overwrite or pollute the release tree that produced the "
            "manuscript's Section 3 numbers. Choose a band_dir outside it."
        )

    resolved_band_dir.mkdir(parents=True, exist_ok=True)
    source_text = source_path.read_text()

    written: list[Path] = []
    for seed in seeds:
        output_dir = resolved_band_dir / f"seed_{seed}"
        variant_text = build_seed_variant_config(
            source_text, seed, output_dir.as_posix()
        )
        variant_path = resolved_band_dir / f"config_seed{seed}.yaml"
        variant_path.write_text(variant_text)
        written.append(variant_path)

    return written


# ---------------------------------------------------------------------------
# D-15/D-16: E2 invocation-config generation (classification/timing/memory)
# ---------------------------------------------------------------------------
#
# WHY GENERATED, NOT HAND-WRITTEN AND COMMITTED: the release config lives at an
# absolute Windows path OUTSIDE this repo
# (`C:/Users/tucke/Desktop/Aqua/AquaCal/release_calibration/config.yaml`,
# `rerun_19_5.sh:209`). Three committed hand-written copies would duplicate that
# path three times over, and Phase 27 (Linux portability) would have to edit
# every one of them. Generated from a single `--config` value, Phase 27
# overrides one variable.

E2_INVOCATION_VARIANTS: tuple[dict, ...] = (
    {
        "name": "classification",
        "filename": "config_e2_classification.yaml",
        "internals": {
            "log_all_observation_depths": True,
            "benchmark_memory": False,
        },
        "purpose": (
            "Production / classification run. Carries Phase 25's per-observation "
            "h_q sidecar (D-16); carries NO memory instrumentation, because "
            "peak-RSS sampling perturbs the wall clock this run's artifacts are "
            "read alongside."
        ),
    },
    {
        "name": "timing",
        "filename": "config_e2_timing.yaml",
        "internals": {
            "log_all_observation_depths": False,
            "benchmark_memory": False,
        },
        "purpose": (
            "Timing run. Carries NEITHER perturbing internals key: "
            "benchmark_memory costs 2.7-5.5% wall clock (D-15) and "
            "log_all_observation_depths writes an ~11 MB per-stage sidecar on "
            "the 13-camera rig (D-16). A flag that perturbs the quantity being "
            "measured cannot ride along with it."
        ),
    },
    {
        "name": "memory",
        "filename": "config_e2_memory.yaml",
        "internals": {
            "log_all_observation_depths": False,
            "benchmark_memory": True,
        },
        "purpose": (
            "Memory run. Carries benchmark_memory only. This is a SEPARATE "
            "invocation from the timing run, inherited and non-negotiable "
            "(D-15): one run cannot honestly produce both numbers."
        ),
    },
)


def _yaml_scalar(value: object) -> str:
    """Render `value` as a YAML scalar for in-place config rewriting."""
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)):
        return str(value)
    return json.dumps(str(value))


def _rewrite_output_dir_in_place(
    lines: list[str], output_dir: str, default_ending: str
) -> None:
    """Rewrite the `paths.output_dir` value of `lines` in place.

    A deliberate near-duplicate of the corresponding stanza inside
    `build_seed_variant_config`: the band generator is production-proven
    (D-19.5-07) and is not refactored here to serve a sibling.

    Args:
        lines: Config lines with line endings kept; mutated in place.
        output_dir: The value to write (as a double-quoted YAML scalar).
        default_ending: Line ending to use if the target line carries none.

    Raises:
        ValueError: If no `paths.output_dir` line is found to rewrite.
    """
    paths_idx = _find_top_level_index(lines, "paths")
    output_dir_idx = None
    indent = None
    if paths_idx is not None:
        for i in range(paths_idx + 1, len(lines)):
            stripped = lines[i].rstrip("\r\n")
            if stripped == "":
                continue
            if _TOP_LEVEL_KEY_RE.match(stripped):
                break  # left the paths: block
            match = _OUTPUT_DIR_LINE_RE.match(lines[i])
            if match:
                output_dir_idx = i
                indent = match.group(1)
                break

    if output_dir_idx is None:
        raise ValueError(
            "build_internals_variant_config: no 'paths.output_dir' line found "
            "in source_text to rewrite"
        )

    ending = _line_ending(lines[output_dir_idx]) or default_ending
    lines[output_dir_idx] = f"{indent}output_dir: {json.dumps(output_dir)}{ending}"


def build_internals_variant_config(
    source_text: str, output_dir: str, overrides: dict
) -> str:
    """Return `source_text` with `paths.output_dir` and `internals.*` set (D-15).

    A pure text-to-text transform, exactly like `build_seed_variant_config`:
    each `internals.<key>` in `overrides` is replaced in place when the key
    already exists, or inserted at the end of the `internals:` block when it
    does not (the block itself is created at end of file, at top-level
    indentation, when absent). Every other line -- comments, blank lines, key
    order, camera lists, video paths -- survives byte-for-byte. When every
    override key pre-exists, exactly `1 + len(overrides)` lines change.

    A `yaml.safe_load`/`safe_dump` round-trip is deliberately NOT used: it
    destroys comments and reorders keys, which would make that "only N lines
    changed" assertion unverifiable. This matters more here than for the seed
    band, because CONTEXT notes `--smoke` cannot catch a bad production YAML --
    a human diff is the only review this config gets before a 48-87 minute run.

    Args:
        source_text: The full text of a source `config.yaml`.
        output_dir: The value to write into `paths.output_dir`.
        overrides: Mapping of `internals` key -> value to set.

    Returns:
        The transformed config text.

    Raises:
        ValueError: If no `paths.output_dir` line is found to rewrite.
    """
    lines = source_text.splitlines(keepends=True)
    default_ending = "\r\n" if "\r\n" in source_text else "\n"

    # Rewrite output_dir FIRST so a source config without one raises before any
    # other mutation is attempted.
    _rewrite_output_dir_in_place(lines, output_dir, default_ending)

    internals_idx = _find_top_level_index(lines, "internals")
    if internals_idx is None:
        if lines and _line_ending(lines[-1]) == "":
            lines[-1] = lines[-1] + default_ending
        lines.append(f"internals:{default_ending}")
        internals_idx = len(lines) - 1
        indent = "  "
        insert_idx = len(lines)
        block_end = len(lines)
    else:
        indent = None
        block_end = len(lines)
        last_child_idx = internals_idx
        for i in range(internals_idx + 1, len(lines)):
            stripped = lines[i].rstrip("\r\n")
            if stripped == "":
                continue
            if _TOP_LEVEL_KEY_RE.match(stripped):
                block_end = i
                break
            if indent is None:
                indent = re.match(r"^(\s+)", lines[i]).group(1)
            last_child_idx = i
        indent = indent or "  "
        insert_idx = last_child_idx + 1

    # Pass 1: replace keys that already exist inside the internals block.
    missing: list[str] = []
    for key, value in overrides.items():
        key_re = re.compile(r"^(\s+)" + re.escape(key) + r":(.*)$")
        replaced = False
        for i in range(internals_idx + 1, block_end):
            match = key_re.match(lines[i].rstrip("\r\n"))
            if match:
                ending = _line_ending(lines[i]) or default_ending
                # Preserve any trailing inline comment: the schema's own
                # `internals` comments are the only documentation a reviewer
                # of a generated production config gets. Every `internals` key
                # this generator sets is a bool, so a `#` in the remainder is
                # unambiguously a comment and never part of a quoted value.
                rest = match.group(2)
                comment = "  " + rest[rest.index("#") :].rstrip() if "#" in rest else ""
                lines[i] = (
                    f"{match.group(1)}{key}: {_yaml_scalar(value)}{comment}{ending}"
                )
                replaced = True
                break
        if not replaced:
            missing.append(key)

    # Pass 2: insert the keys that were absent, in `overrides` order.
    for offset, key in enumerate(missing):
        lines.insert(
            insert_idx + offset,
            f"{indent}{key}: {_yaml_scalar(overrides[key])}{default_ending}",
        )

    return "".join(lines)


def emit_invocation_configs(source_path: Path, target_dir: Path) -> list[Path]:
    """Write E2's three invocation-variant configs into `target_dir` (D-15/D-16).

    Emits exactly `config_e2_classification.yaml`, `config_e2_timing.yaml` and
    `config_e2_memory.yaml`, in that order, plus an `e2_invocation_scope.json`
    sidecar recording the source config's sha256, each variant's filename,
    `internals` settings and output directory. Each variant gets a DISTINCT
    `paths.output_dir`, so the completeness gate can attribute every E2 artifact
    to the invocation that produced it (D-16).

    No variant sets both `benchmark_memory` and `log_all_observation_depths`
    true -- that is the entire point of the split.

    Refuses to write if `target_dir` resolves inside `source_path.parent`, for
    the same reason `emit_seed_variant_configs` does (T-19.5-07-01): the release
    tree that produced the manuscript's Section 3 numbers must never be a
    generated config's write target.

    Args:
        source_path: Path to the source release `config.yaml` (read-only;
            never modified by this function).
        target_dir: Directory to write the three variants and the sidecar into.

    Returns:
        The three written config paths, in classification/timing/memory order.

    Raises:
        ValueError: If `target_dir` resolves inside `source_path.parent`, or if
            the source config has no `paths.output_dir` line.
    """
    source_path = Path(source_path).resolve()
    resolved_target = Path(target_dir).resolve()
    source_dir = source_path.parent

    if resolved_target == source_dir or source_dir in resolved_target.parents:
        raise ValueError(
            f"emit_invocation_configs: target_dir {resolved_target} resolves "
            f"inside the source config's own directory {source_dir}; a "
            "generated invocation config would overwrite or pollute the "
            "release tree that produced the manuscript's Section 3 numbers. "
            "Choose a target_dir outside it."
        )

    resolved_target.mkdir(parents=True, exist_ok=True)
    source_text = source_path.read_text()

    written: list[Path] = []
    variant_records: list[dict] = []
    for spec in E2_INVOCATION_VARIANTS:
        output_dir = resolved_target / f"e2_{spec['name']}"
        variant_text = build_internals_variant_config(
            source_text, output_dir.as_posix(), spec["internals"]
        )
        variant_path = resolved_target / spec["filename"]
        variant_path.write_text(variant_text)
        written.append(variant_path)
        variant_records.append(
            {
                "name": spec["name"],
                "filename": spec["filename"],
                "internals": dict(spec["internals"]),
                "output_dir": output_dir.as_posix(),
                "purpose": spec["purpose"],
            }
        )

    scope_record = {
        "source_config": str(source_path),
        "source_config_sha256": hashlib.sha256(source_path.read_bytes()).hexdigest(),
        "variants": variant_records,
        "n": len(variant_records),
        "scope": (
            "E2 is an explicitly multi-invocation stage (D-15). These three "
            "configs differ from the source config in exactly paths.output_dir "
            "and two internals keys. Timing and memory are two DISTINCT runs "
            "because internals.benchmark_memory costs 2.7-5.5% wall clock, so "
            "one run cannot honestly produce both numbers; and "
            "internals.log_all_observation_depths (an ~11 MB per-stage sidecar "
            "on the 13-camera rig) rides the classification run ONLY, never the "
            "timing run (D-16). Each variant writes its own output_dir so every "
            "artifact is attributable to its invocation."
        ),
    }
    scope_path = resolved_target / "e2_invocation_scope.json"
    scope_path.write_text(json.dumps(scope_record, indent=2, sort_keys=True))

    return written


def build_arg_parser() -> argparse.ArgumentParser:
    """Build E2's CLI parser: the shared five-flag contract, no extra flags.

    Returns:
        A configured `argparse.ArgumentParser`.
    """
    parser = argparse.ArgumentParser(
        description=__doc__, parents=[build_experiment_arg_parser()]
    )
    parser.add_argument(
        "--config",
        type=Path,
        default=None,
        help=(
            "Run against an explicit config.yaml instead of the published Zenodo "
            "archive's own config_paper.yaml. NOT required to reproduce the "
            "manuscript's section-3 FRAMESET: record 21889922 (4.35 GB; the "
            "manifest was repointed to it in 25655f7) ships 13 x 262 extrinsic "
            "frames plus config_paper.yaml at frame_step: 1 / "
            "max_calibration_frames: 200, which yields 262 usable frames -> "
            "210/52 split -> 200 calibration frames and reproduces "
            "reconstruction.num_comparisons = 7762 exactly (verified 2026-08-12). "
            "The retired record 18645385 (164 MB) was the ~4.3x subsampled one. "
            "Whether the CURRENT library reproduces section-3's VALUES is a "
            "separate, open question (MANUSCRIPT-FINDINGS MF-19); this flag makes "
            "no claim about it. Use --config to point at a different capture or a "
            "variant config; omit it to run the published archive as shipped."
        ),
    )
    parser.add_argument(
        "--emit-band-configs",
        action="store_true",
        default=False,
        help=(
            "COV-07: emit N seed-variant config.yaml files (each differing "
            "from --config in exactly the top-level seed: key and "
            "paths.output_dir) plus e2_band_scope.json into --band-dir, and "
            "exit without running any calibration. Requires --config and "
            "--band-dir; cannot be combined with --check or --smoke."
        ),
    )
    parser.add_argument(
        "--band-seeds",
        type=str,
        default="42,43,44",
        help=(
            "Comma-separated seed list for --emit-band-configs (D-19.5-07's "
            "design decision: seed 42 reproduces the currently committed "
            "record). Default '42,43,44'."
        ),
    )
    parser.add_argument(
        "--band-dir",
        type=Path,
        default=None,
        help=(
            "Directory to write seed-variant configs into for "
            "--emit-band-configs. Must not resolve inside --config's own "
            "directory -- the release tree that produced the manuscript's "
            "Section 3 numbers must never be a variant's write target."
        ),
    )
    parser.add_argument(
        "--emit-invocation-configs",
        action="store_true",
        default=False,
        help=(
            "D-15/D-16: emit E2's three invocation-variant config.yaml files "
            "(classification, timing, memory) plus e2_invocation_scope.json "
            "into --invocation-dir, and exit without running any calibration. "
            "They exist because internals.benchmark_memory costs 2.7-5.5%% wall "
            "clock, so ONE run cannot honestly produce both the timing and the "
            "memory number; and internals.log_all_observation_depths writes an "
            "~11 MB per-stage sidecar on the 13-camera rig, so it rides the "
            "classification run only and NEVER the timing run -- a flag that "
            "perturbs the quantity being measured cannot ride along with it. "
            "Requires --config and --invocation-dir; cannot be combined with "
            "--check, --smoke, --force or --emit-band-configs."
        ),
    )
    parser.add_argument(
        "--invocation-dir",
        type=Path,
        default=None,
        help=(
            "Directory to write the three --emit-invocation-configs variants "
            "into. Must not resolve inside --config's own directory -- the "
            "release tree that produced the manuscript's Section 3 numbers "
            "must never be a generated config's write target."
        ),
    )
    add_baseline_dir_argument(parser)
    return parser


def _validate_e2_args(
    parser: argparse.ArgumentParser, args: argparse.Namespace
) -> None:
    """Enforce COV-07's `--emit-band-configs` cross-flag constraints (D-19.5-07).

    Args:
        parser: The parser `args` was produced from (used only to call
            `parser.error()`, which prints usage and exits nonzero).
        args: The parsed namespace to validate.

    Raises:
        SystemExit: Via `parser.error()`, when `--emit-band-configs` is
            combined with `--check`/`--smoke`, or given without both
            `--config` and `--band-dir`. Also raised by the shared
            `validate_args` for `--check`/`--force` together.
    """
    validate_args(parser, args)
    if args.emit_band_configs and (args.check or args.smoke):
        parser.error("--emit-band-configs cannot be combined with --check or --smoke")
    if args.emit_band_configs and args.config is None:
        parser.error("--emit-band-configs requires --config")
    if args.emit_band_configs and args.band_dir is None:
        parser.error("--emit-band-configs requires --band-dir")

    # D-15/D-16: --emit-invocation-configs writes configs and runs nothing, so
    # every flag that implies a run (or a second generator) is a conflict. The
    # message names the offending pair, not just the flag.
    if args.emit_invocation_configs:
        for flag, present in (
            ("--check", args.check),
            ("--smoke", args.smoke),
            ("--force", args.force),
            ("--emit-band-configs", args.emit_band_configs),
        ):
            if present:
                parser.error(
                    f"--emit-invocation-configs cannot be combined with {flag}"
                )
        if args.config is None:
            parser.error("--emit-invocation-configs requires --config")
        if args.invocation_dir is None:
            parser.error("--emit-invocation-configs requires --invocation-dir")


def _run_emit_band_configs(args: argparse.Namespace) -> int:
    """Emit COV-07's seed-variant configs and band-scope sidecar; no calibration.

    Writes `band_dir / config_seed{seed}.yaml` for each seed in
    `args.band_seeds`, plus `band_dir / e2_band_scope.json` recording the
    source config's path and hash, the seeds, and the band's scope statement
    (D-19.5-05: this band bounds split variance, NOT measurement variance).

    Args:
        args: Parsed CLI namespace. `args.config` and `args.band_dir` are
            both required (enforced by `_validate_e2_args`).

    Returns:
        0. Errors propagate as exceptions/`SystemExit`, not a nonzero return.
    """
    source_path = Path(args.config).resolve()
    band_dir = Path(args.band_dir).resolve()
    seeds = parse_seed_list(args.band_seeds)

    variant_paths = emit_seed_variant_configs(source_path, seeds, band_dir)
    for path in variant_paths:
        print(f"Wrote {path}")

    source_config_sha256 = hashlib.sha256(source_path.read_bytes()).hexdigest()
    scope_record = {
        "source_config": str(source_path),
        "source_config_sha256": source_config_sha256,
        "seeds": list(seeds),
        "n": len(seeds),
        "scope": (
            "This band varies the calibration/holdout split seed "
            "(config.seed, threaded to split_detections) on fixed real data. "
            "It bounds split variance, NOT measurement variance -- the "
            "underlying frames, detections, and camera videos are identical "
            "across every seed in this band (D-19.5-05)."
        ),
    }
    scope_path = band_dir / "e2_band_scope.json"
    scope_path.write_text(json.dumps(scope_record, indent=2, sort_keys=True))
    print(f"Wrote {scope_path}")

    return 0


def _run_emit_invocation_configs(args: argparse.Namespace) -> int:
    """Emit D-15/D-16's three invocation configs and sidecar; no calibration.

    Args:
        args: Parsed CLI namespace. `args.config` and `args.invocation_dir` are
            both required (enforced by `_validate_e2_args`).

    Returns:
        0. Errors propagate as exceptions/`SystemExit`, not a nonzero return.
    """
    source_path = Path(args.config).resolve()
    target_dir = Path(args.invocation_dir).resolve()

    for path in emit_invocation_configs(source_path, target_dir):
        print(f"Wrote {path}")
    print(f"Wrote {target_dir / 'e2_invocation_scope.json'}")
    return 0


def main(argv: list[str] | None = None) -> int:
    """CLI entry point for `python -m experiments.e2_real_rig`.

    Args:
        argv: Argument list (defaults to `sys.argv[1:]` via `argparse`).

    Returns:
        Process exit code.
    """
    parser = build_arg_parser()
    args = parser.parse_args(argv)
    _validate_e2_args(parser, args)

    logging.basicConfig(level=logging.INFO, format="%(message)s")

    if args.emit_invocation_configs:
        return _run_emit_invocation_configs(args)

    if args.emit_band_configs:
        return _run_emit_band_configs(args)

    if args.smoke:
        return _run_smoke(args)
    if args.check:
        return _run_check(args)
    return _run_full(args)


if __name__ == "__main__":
    sys.exit(main())
