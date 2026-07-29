"""E6: generalization sweep (EXP-10).

**What this is.** Three independent one-dimensional axes -- refractive index,
camera-array layout, and working-volume/rig scale -- each swept one axis at a
time through a single common baseline (D-11): E4's own 12-camera grid-family
cell, built by `experiments.e4_benchmark_grid.build_grid_scenario` and run at
E4's own imported `GRID_NORMAL_FIXED` (tilt-enabled). Camera count is E4's own
axis and is deliberately NOT re-swept here (D-11) -- re-treading it under a
different label would give the same numbers two origins.

Purpose: EXP-10 answers reviewer point R1.4, which asked for physical
experiments across multiple tanks, media, and layouts. Physical multi-medium
rigs are out of scope for this deadline; controlled synthetic sweeps isolate
each variable more cleanly than a single physical rig could, and E2's real-rig
run anchors them to reality.

**Every axis passes through the baseline.** `INDEX_AXIS_VALUES`'s first
element, `LAYOUT_AXIS_VALUES`'s `"grid"` entry, and `SCALE_AXIS_VALUES`'s
`"default"` entry are all literally the baseline value, so a figure module can
facet by axis and every facet has its anchor. The three baseline rows share
one `config_key`, so the underlying scene/calibration is computed exactly
once and reused for all three axis rows rather than recomputed three times.

**No verdict.** The stated finding -- that parameter recovery and held-out
accuracy hold across the sweep -- can genuinely fail (a wide-baseline ring or
line layout may disconnect the pose graph; a high index ratio may degrade
recovery). This module records what happened; it does not assert, threshold,
or name a verdict anywhere (D-12). Interpretation is manuscript work.

Invoked as `python -m experiments.e6_generalization_sweep`. Inherits the
shared five-flag CLI contract (`--seed`, `--out`, `--force`, `--smoke`,
`--check`) from `experiments._io.build_experiment_arg_parser` (D-21).

Emits `generalization_sweep.csv` (one row per axis value, tidy long format,
keyed on `(axis, axis_value)`) plus one small per-configuration JSON under
`--out/e6_configs/{config_key}.json`, written before the CSV is assembled, so
an interrupted sweep resumes per configuration instead of restarting the
longest sweep in the phase from zero (review M7).
"""

from __future__ import annotations

import argparse
import json
import logging
import tempfile
from pathlib import Path

import numpy as np
import pandas as pd

from aquacal.core.board import BoardGeometry
from aquacal.datasets.pipelines import calibrate_synthetic, compute_per_camera_errors
from aquacal.datasets.synthetic import generate_synthetic_detections
from aquacal.validation.evaluation import evaluate_calibration
from experiments._io import (
    build_experiment_arg_parser,
    compare_experiment_csv,
    exit_code_for,
    resolve_out_dir,
    validate_args,
    write_experiment_csv,
)
from experiments.e4_benchmark_grid import GRID_NORMAL_FIXED, build_grid_scenario

logger = logging.getLogger(__name__)

CHECK_RTOL = 1e-6

# ---------------------------------------------------------------------------
# Baseline and the three one-dimensional axes (D-11, amended D-11, review M2)
# ---------------------------------------------------------------------------

BASELINE_N_CAMERAS = 12
BASELINE_N_FRAMES = 100
BASELINE_LAYOUT = "grid"
BASELINE_N_WATER = 1.333
BASELINE_SCALE = "default"

# Water (1.333) through oil to resin (~1.55); ~0.03 steps. The FIRST element
# is BASELINE_N_WATER so the axis passes through the shared baseline. This
# axis demonstrates the arbitrary-index-ratio claim: AquaCal's refractive
# model is not tuned to water specifically.
INDEX_AXIS_VALUES: list[float] = [1.333, 1.36, 1.39, 1.42, 1.45, 1.48, 1.51, 1.55]

# "grid" IS the baseline layout, so the axis passes through it. Camera count
# stays fixed at BASELINE_N_CAMERAS for every value -- layout is varied, not
# array size (D-11).
LAYOUT_AXIS_VALUES: list[str] = ["grid", "ring", "line"]

# Three (label, depth_range, xy_extent, spacing) settings. "default" (None,
# None, None) is the underlying scene generators' own defaults -- the camera
# array's spacing=0.1 m and the board trajectory's depth_range=(0.3, 0.6) m /
# xy_extent=0.15 m (see `build_grid_scenario`'s own docstring) -- and is the
# baseline.
#
# `spacing` deliberately varies alongside `depth_range`/`xy_extent` (review
# M2): the camera array generator pins `spacing` at 0.1 m and the board
# trajectory generator defaults `xy_extent` to 0.15 m, so varying only
# the working volume changes the RATIO of working volume to camera baseline,
# not the scale itself. Each non-default setting scales all three together by
# the same factor (0.5x and 2x), so this axis measures "does accuracy hold as
# the whole rig/tank scales up or down together," not a ratio effect. The
# board's `square_size` is deliberately NOT scaled -- a real calibration
# target does not shrink with the tank (see
# `experiments.e4_benchmark_grid.build_grid_scenario`'s own docstring, which
# states this same rationale for GRID_BOARD_CONFIG).
SCALE_AXIS_VALUES: list[
    tuple[str, tuple[float, float] | None, float | None, float | None]
] = [
    ("half_scale", (0.15, 0.3), 0.075, 0.05),
    ("default", None, None, None),
    ("double_scale", (0.6, 1.2), 0.3, 0.2),
]

STATUS_VALUES = frozenset({"ok", "failed", "skipped_existing"})

E6_COLUMNS: list[str] = [
    "axis",
    "axis_value",
    "model",
    "config_key",
    "is_baseline",
    "seed",
    "n_cameras",
    "n_frames",
    "layout",
    "n_true",
    "n_assumed",
    "normal_fixed",
    "depth_range_min",
    "depth_range_max",
    "xy_extent",
    "spacing",
    "status",
    "status_reason",
    "reprojection_rms_px",
    "reconstruction_mae_mm",
    "reconstruction_rmse_mm",
    "signed_mean_mm",
    "focal_error_pct_mean",
    "xy_position_error_mm_mean",
    "z_position_error_mm_mean",
    "water_z_error_mm_mean",
    "num_comparisons",
    "num_frames",
]
assert len(E6_COLUMNS) == 28 and len(set(E6_COLUMNS)) == 28

E6_KEY_COLUMNS = ["axis", "axis_value"]

# Columns whose value is null for any row whose status is not "ok".
_METRIC_COLUMNS: list[str] = [
    "reprojection_rms_px",
    "reconstruction_mae_mm",
    "reconstruction_rmse_mm",
    "signed_mean_mm",
    "focal_error_pct_mean",
    "xy_position_error_mm_mean",
    "z_position_error_mm_mean",
    "water_z_error_mm_mean",
    "num_comparisons",
    "num_frames",
]

# Smoke mode's held-out/calibration frame count -- small so --smoke completes
# quickly even though camera count stays at the full BASELINE_N_CAMERAS (D-11
# forbids reducing it, so frame count is the only knob smoke mode has).
_SMOKE_N_FRAMES = 8


# ---------------------------------------------------------------------------
# Axis configuration table (P4: the sweep is data, not control flow)
# ---------------------------------------------------------------------------


def build_axis_configurations() -> list[dict]:
    """Expand the three axes into one flat list of configuration dicts.

    Each dict carries `axis`, `axis_value` (always a string, since the three
    axes' values are heterogeneous -- a float index, a layout name, a scale
    label -- and a tidy format needs one shared column), `is_baseline`,
    `config_key`, and the scene keywords `n_cameras`, `layout`, `n_water`,
    `depth_range`, `xy_extent`, `spacing` needed by `build_grid_scenario`.

    The baseline configuration appears once per axis (three entries total),
    each with a DIFFERENT `axis`/`axis_value` but the SAME `config_key`
    (`"baseline"`) -- `run_configuration` computes the underlying scene once
    per distinct `config_key`, so the three baseline rows share one run
    rather than tripling it.

    Returns:
        A list of length `len(INDEX_AXIS_VALUES) + len(LAYOUT_AXIS_VALUES) +
        len(SCALE_AXIS_VALUES)`, with exactly 3 entries carrying
        `is_baseline=True`.
    """
    configs: list[dict] = []

    for value in INDEX_AXIS_VALUES:
        is_baseline = value == BASELINE_N_WATER
        configs.append(
            {
                "axis": "index",
                "axis_value": str(value),
                "is_baseline": is_baseline,
                "config_key": "baseline" if is_baseline else f"index_{value}",
                "n_cameras": BASELINE_N_CAMERAS,
                "layout": BASELINE_LAYOUT,
                "n_water": value,
                "depth_range": None,
                "xy_extent": None,
                "spacing": None,
            }
        )

    for value in LAYOUT_AXIS_VALUES:
        is_baseline = value == BASELINE_LAYOUT
        configs.append(
            {
                "axis": "layout",
                "axis_value": value,
                "is_baseline": is_baseline,
                "config_key": "baseline" if is_baseline else f"layout_{value}",
                "n_cameras": BASELINE_N_CAMERAS,
                "layout": value,
                "n_water": BASELINE_N_WATER,
                "depth_range": None,
                "xy_extent": None,
                "spacing": None,
            }
        )

    for label, depth_range, xy_extent, spacing in SCALE_AXIS_VALUES:
        is_baseline = label == BASELINE_SCALE
        configs.append(
            {
                "axis": "scale",
                "axis_value": label,
                "is_baseline": is_baseline,
                "config_key": "baseline" if is_baseline else f"scale_{label}",
                "n_cameras": BASELINE_N_CAMERAS,
                "layout": BASELINE_LAYOUT,
                "n_water": BASELINE_N_WATER,
                "depth_range": depth_range,
                "xy_extent": xy_extent,
                "spacing": spacing,
            }
        )

    return configs


def build_smoke_configurations() -> list[dict]:
    """The baseline plus one non-baseline value from each axis (six rows, four scenes)."""
    configs = build_axis_configurations()
    baseline = [c for c in configs if c["is_baseline"]]
    non_baseline_by_axis: dict[str, dict] = {}
    for c in configs:
        if not c["is_baseline"] and c["axis"] not in non_baseline_by_axis:
            non_baseline_by_axis[c["axis"]] = c
    return baseline + list(non_baseline_by_axis.values())


# ---------------------------------------------------------------------------
# Water-surface recovery helper (review M5 -- not available from
# compute_per_camera_errors, so it has one tested origin here)
# ---------------------------------------------------------------------------


def compute_water_z_error_mm_mean(
    estimated_water_zs: dict[str, float], true_water_zs: dict[str, float]
) -> float:
    """Mean absolute per-camera water_z recovery error, in millimetres.

    `compute_per_camera_errors` returns focal length, Z/XY position, and
    distortion errors, but no water_z error -- index error couples directly
    into recovered interface depth, making this the single most diagnostic
    column on the index axis, so it is computed here with one tested origin
    rather than as an inline expression duplicated at each call site.

    Args:
        estimated_water_zs: Recovered water_z per camera (meters), typically
            `{cam: cal.water_z for cam, cal in result.cameras.items()}`.
        true_water_zs: Ground-truth water_z per camera (meters), typically
            `scenario.water_zs`.

    Returns:
        The mean, over cameras present in both dicts, of
        `abs(estimated - true) * 1000` (millimetres). `nan` if no camera is
        present in both.
    """
    errors_mm = [
        abs(estimated_water_zs[cam] - true_water_zs[cam]) * 1000.0
        for cam in true_water_zs
        if cam in estimated_water_zs
    ]
    if not errors_mm:
        return float("nan")
    return float(np.mean(errors_mm))


def compute_configuration_metrics(scenario, result, evaluation) -> dict:
    """Build one configuration's metric-only fields from a completed run.

    Pure computation over already-produced objects -- no calibration is run
    here. Aggregates `compute_per_camera_errors`' per-camera dict to
    cross-camera means (the library computes per-camera errors; this script
    only aggregates, P2) and reads held-out reconstruction accuracy off
    `evaluation.reconstruction`.

    Args:
        scenario: The `SyntheticScenario` the configuration was built from.
        result: The `CalibrationResult` returned by `calibrate_synthetic`.
        evaluation: The `HeldOutEvaluation` returned by `evaluate_calibration`
            on a held-out detection set.

    Returns:
        A dict with exactly the keys in `_METRIC_COLUMNS`.
    """
    per_camera_errors = compute_per_camera_errors(result, scenario)
    focal_vals = [e["focal_length_error_pct"] for e in per_camera_errors.values()]
    xy_vals = [e["xy_position_error_mm"] for e in per_camera_errors.values()]
    z_vals = [e["z_position_error_mm"] for e in per_camera_errors.values()]
    estimated_water_zs = {cam: cal.water_z for cam, cal in result.cameras.items()}

    reconstruction = evaluation.reconstruction
    return {
        "reprojection_rms_px": float(evaluation.reprojection.rms),
        "reconstruction_mae_mm": (
            float(reconstruction.mean * 1000.0) if reconstruction is not None else None
        ),
        "reconstruction_rmse_mm": (
            float(reconstruction.rmse * 1000.0) if reconstruction is not None else None
        ),
        "signed_mean_mm": (
            float(reconstruction.signed_mean * 1000.0)
            if reconstruction is not None
            else None
        ),
        "focal_error_pct_mean": float(np.mean(focal_vals)) if focal_vals else None,
        "xy_position_error_mm_mean": float(np.mean(xy_vals)) if xy_vals else None,
        "z_position_error_mm_mean": float(np.mean(z_vals)) if z_vals else None,
        "water_z_error_mm_mean": compute_water_z_error_mm_mean(
            estimated_water_zs, scenario.water_zs
        ),
        "num_comparisons": (
            reconstruction.num_comparisons if reconstruction is not None else None
        ),
        "num_frames": evaluation.num_frames,
    }


# ---------------------------------------------------------------------------
# Row builder (P4: identity/scene fields + status/metrics -> one E6_COLUMNS row)
# ---------------------------------------------------------------------------


def build_row(
    config: dict,
    seed: int,
    n_frames: int,
    metrics: dict | None,
    *,
    status: str,
    status_reason: str,
) -> dict:
    """Combine one configuration's identity fields with its (possibly null) metrics.

    Metric columns are null whenever `status` is not `"ok"`, regardless of
    what `metrics` contains -- a `"skipped_existing"` or `"failed"` row never
    silently carries a stale or partial number.

    Args:
        config: One entry from `build_axis_configurations()`.
        seed: The run seed.
        n_frames: The calibration frame count actually used.
        metrics: `compute_configuration_metrics()`'s output, or `None`.
        status: One of `STATUS_VALUES`.
        status_reason: Empty string on success, else a short description.

    Returns:
        A dict with exactly the keys of `E6_COLUMNS`, in that order.
    """
    depth_range = config["depth_range"]
    row: dict = {
        "axis": config["axis"],
        "axis_value": config["axis_value"],
        "model": "refractive",
        "config_key": config["config_key"],
        "is_baseline": config["is_baseline"],
        "seed": seed,
        "n_cameras": config["n_cameras"],
        "n_frames": n_frames,
        "layout": config["layout"],
        "n_true": config["n_water"],
        "n_assumed": config["n_water"],
        "normal_fixed": GRID_NORMAL_FIXED,
        "depth_range_min": depth_range[0] if depth_range is not None else None,
        "depth_range_max": depth_range[1] if depth_range is not None else None,
        "xy_extent": config["xy_extent"],
        "spacing": config["spacing"],
        "status": status,
        "status_reason": status_reason,
    }
    use_metrics = status == "ok" and metrics is not None
    for col in _METRIC_COLUMNS:
        row[col] = metrics.get(col) if use_metrics else None
    return {col: row[col] for col in E6_COLUMNS}


# ---------------------------------------------------------------------------
# Per-configuration runner (review M7: per-configuration checkpoint JSON)
# ---------------------------------------------------------------------------


def run_configuration(
    config: dict,
    seed: int,
    n_frames: int,
    out_dir: Path,
    *,
    refine_intrinsics: bool = True,
    force: bool = False,
) -> dict:
    """Run (or skip, if already cached) one distinct scene, checkpointing to JSON.

    Distinct SCENES are cached by `config["config_key"]` under
    `out_dir/e6_configs/{config_key}.json` -- not by `(axis, axis_value)` --
    because `build_axis_configurations()` deliberately gives the three
    baseline rows the same `config_key` (E6 is the largest sweep in the phase
    and the designated calendar-fallback casualty, so per-configuration
    resumability matters most here; review M7). This mirrors E4's per-cell
    mechanism (`run_grid_cell`): when the checkpoint file already exists and
    `force` is False, this returns `status="skipped_existing"` with null
    metrics rather than re-running the calibration -- an interrupted sweep's
    completed configurations are recorded, but a genuinely resumed CSV still
    requires re-running with `force=True` to fill every metric column.

    The held-out detection set is generated from a SECOND call to
    `build_grid_scenario` at `seed + 1_000_000` (never a direct call to the
    underlying scene generators), so E6 never reimplements scene
    construction -- only the second scenario's `board_poses` are used,
    paired with the FIRST scenario's own camera geometry, so held-out
    accuracy is scored against the same rig the calibration solved for.

    Args:
        config: One entry from `build_axis_configurations()`.
        seed: Seed forwarded to scenario/detection generation.
        n_frames: Calibration frame count for this run (independent of
            `BASELINE_N_FRAMES` so `--smoke` can use a smaller value).
        out_dir: Root output directory; checkpoints are written under
            `out_dir/e6_configs/`.
        refine_intrinsics: Forwarded to `calibrate_synthetic`.
        force: Overwrite an existing checkpoint instead of skipping it.

    Returns:
        A dict with `status` (one of `STATUS_VALUES`), `status_reason`, and
        `metrics` (`compute_configuration_metrics()`'s output, or `None`).
    """
    config_key = config["config_key"]
    config_path = Path(out_dir) / "e6_configs" / f"{config_key}.json"

    if config_path.exists() and not force:
        logger.info(
            "Skipping configuration %s: %s already exists (resumability).",
            config_key,
            config_path,
        )
        return {"status": "skipped_existing", "status_reason": "", "metrics": None}

    try:
        scenario = build_grid_scenario(
            n_cameras=config["n_cameras"],
            n_frames=n_frames,
            seed=seed,
            layout=config["layout"],
            depth_range=config["depth_range"],
            xy_extent=config["xy_extent"],
            spacing=config["spacing"],
            n_water=config["n_water"],
        )
        result, _detections = calibrate_synthetic(
            scenario,
            n_water=scenario.n_water,
            refine_intrinsics=refine_intrinsics,
            seed=seed,
            normal_fixed=GRID_NORMAL_FIXED,
        )

        board = BoardGeometry(scenario.board_config)
        holdout_seed = seed + 1_000_000
        holdout_scenario = build_grid_scenario(
            n_cameras=config["n_cameras"],
            n_frames=n_frames,
            seed=holdout_seed,
            layout=config["layout"],
            depth_range=config["depth_range"],
            xy_extent=config["xy_extent"],
            spacing=config["spacing"],
            n_water=config["n_water"],
        )
        holdout_detections = generate_synthetic_detections(
            intrinsics=scenario.intrinsics,
            extrinsics=scenario.extrinsics,
            water_zs=scenario.water_zs,
            board=board,
            board_poses=holdout_scenario.board_poses,
            noise_std=scenario.noise_std,
            n_air=scenario.n_air,
            n_water=scenario.n_water,
            seed=holdout_seed,
        )
        evaluation = evaluate_calibration(result, holdout_detections, board)
        metrics = compute_configuration_metrics(scenario, result, evaluation)
        outcome = {"status": "ok", "status_reason": "", "metrics": metrics}
    except Exception as exc:
        logger.warning(
            "Configuration %s failed: %s: %s", config_key, type(exc).__name__, exc
        )
        outcome = {
            "status": "failed",
            "status_reason": f"{type(exc).__name__}: {exc}",
            "metrics": None,
        }

    config_path.parent.mkdir(parents=True, exist_ok=True)
    with open(config_path, "w") as f:
        json.dump(
            {**outcome, "seed": seed, "n_frames": n_frames}, f, indent=2, sort_keys=True
        )
    return outcome


def run_sweep(
    configs: list[dict],
    seed: int,
    n_frames: int,
    out_dir: Path,
    *,
    refine_intrinsics: bool = True,
    force: bool = False,
) -> pd.DataFrame:
    """Run every distinct scene in `configs` once, then build one row per config.

    `run_configuration` is called once per distinct `config_key` (a plain
    in-memory cache dict, not a second file check) -- so the three baseline
    rows in `configs` reuse one computed result, satisfying "computed ONCE
    and reused for all three baseline rows" without duplicating I/O.

    Args:
        configs: `build_axis_configurations()` or `build_smoke_configurations()`.
        seed: Seed forwarded to every configuration.
        n_frames: Calibration frame count forwarded to every configuration.
        out_dir: Root output directory forwarded to `run_configuration`.
        refine_intrinsics: Forwarded to `calibrate_synthetic`.
        force: Forwarded to `run_configuration`.

    Returns:
        A `DataFrame` with exactly `E6_COLUMNS`, one row per entry in `configs`.
    """
    cache: dict[str, dict] = {}
    rows: list[dict] = []
    for config in configs:
        config_key = config["config_key"]
        if config_key not in cache:
            cache[config_key] = run_configuration(
                config,
                seed,
                n_frames,
                out_dir,
                refine_intrinsics=refine_intrinsics,
                force=force,
            )
        outcome = cache[config_key]
        row = build_row(
            config,
            seed,
            n_frames,
            outcome["metrics"],
            status=outcome["status"],
            status_reason=outcome["status_reason"],
        )
        rows.append(row)
        logger.info(
            "axis=%s axis_value=%s status=%s reprojection_rms_px=%s",
            row["axis"],
            row["axis_value"],
            row["status"],
            row["reprojection_rms_px"],
        )
    return pd.DataFrame(rows, columns=E6_COLUMNS)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def build_arg_parser() -> argparse.ArgumentParser:
    """Build E6's CLI parser: the shared five-flag contract, no script-local flags."""
    return argparse.ArgumentParser(
        description=__doc__, parents=[build_experiment_arg_parser()]
    )


def _run_check(args: argparse.Namespace) -> int:
    """`--check`: reconstitute rows from existing `e6_configs/` JSON, compare to committed CSV.

    Never runs a configuration -- a configuration with no checkpoint JSON on
    disk is reported as `status="failed"` rather than triggering a run, since
    a full re-run of the largest sweep in the phase would defeat the purpose
    of `--check`.
    """
    out_dir = resolve_out_dir(args.out)
    configs_dir = out_dir / "e6_configs"
    if not configs_dir.exists() or not any(configs_dir.glob("*.json")):
        print(
            f"--check reconstitutes rows from existing per-configuration JSON "
            f"files under {configs_dir} and never runs a configuration; found "
            "none there. Run the full sweep first "
            "(python -m experiments.e6_generalization_sweep)."
        )
        return 1

    committed_path = out_dir / "generalization_sweep.csv"
    if not committed_path.exists():
        print(f"No committed baseline at {committed_path} to check against.")
        return 1

    configs = build_axis_configurations()
    rows: list[dict] = []
    for config in configs:
        config_path = configs_dir / f"{config['config_key']}.json"
        if config_path.exists():
            with open(config_path) as f:
                cached = json.load(f)
            rows.append(
                build_row(
                    config,
                    cached.get("seed", args.seed),
                    cached.get("n_frames", BASELINE_N_FRAMES),
                    cached.get("metrics"),
                    status=cached.get("status", "failed"),
                    status_reason=cached.get("status_reason", ""),
                )
            )
        else:
            rows.append(
                build_row(
                    config,
                    args.seed,
                    BASELINE_N_FRAMES,
                    None,
                    status="failed",
                    status_reason=(
                        "no checkpoint JSON found under e6_configs for this "
                        "configuration"
                    ),
                )
            )

    df = pd.DataFrame(rows, columns=E6_COLUMNS)
    report = compare_experiment_csv(
        df, committed_path, key_columns=E6_KEY_COLUMNS, rtol=CHECK_RTOL
    )
    print(report.message)
    return exit_code_for(report)


def _run_smoke_configs(out_dir: Path, seed: int) -> int:
    """Run the reduced smoke config set, then probe the skip-if-exists path (review M7)."""
    configs = build_smoke_configurations()
    df = run_sweep(
        configs, seed, _SMOKE_N_FRAMES, out_dir, refine_intrinsics=False, force=True
    )
    write_experiment_csv(
        df, out_dir / "generalization_sweep.csv", key_columns=E6_KEY_COLUMNS, force=True
    )

    # Exercise the skip-if-exists path end to end (review M7): re-run the
    # first already-checkpointed configuration WITHOUT --force and confirm it
    # is skipped rather than recomputed, so CI proves the resumability
    # mechanism, not only the happy path.
    skip_probe = run_configuration(
        configs[0],
        seed,
        _SMOKE_N_FRAMES,
        out_dir,
        refine_intrinsics=False,
        force=False,
    )
    if skip_probe["status"] != "skipped_existing":
        logger.warning(
            "smoke skip-path probe did not report skipped_existing: %s",
            skip_probe["status"],
        )
        return 1

    logger.info(
        "smoke: %d rows, skip-path probe status=%s", len(df), skip_probe["status"]
    )
    return 0


def _run_smoke(args: argparse.Namespace) -> int:
    """`--smoke`: reduced config set (baseline + one value per axis) at small n_frames."""
    parser = build_arg_parser()
    if args.out == parser.get_default("out"):
        # Honor an explicitly-passed --out; otherwise use a throwaway temp
        # directory so a bare --smoke never pollutes experiments/results/.
        with tempfile.TemporaryDirectory(prefix="e6_smoke_") as tmp:
            return _run_smoke_configs(resolve_out_dir(Path(tmp)), args.seed)
    return _run_smoke_configs(resolve_out_dir(args.out), args.seed)


def _run_full(args: argparse.Namespace) -> int:
    """Run the full axis sweep and write `generalization_sweep.csv`."""
    out_dir = resolve_out_dir(args.out)
    configs = build_axis_configurations()
    df = run_sweep(
        configs,
        args.seed,
        BASELINE_N_FRAMES,
        out_dir,
        refine_intrinsics=True,
        force=args.force,
    )
    write_experiment_csv(
        df,
        out_dir / "generalization_sweep.csv",
        key_columns=E6_KEY_COLUMNS,
        force=args.force,
    )
    return 0


def main(argv: list[str] | None = None) -> int:
    """CLI entry point for `python -m experiments.e6_generalization_sweep`."""
    parser = build_arg_parser()
    args = parser.parse_args(argv)
    validate_args(parser, args)

    logging.basicConfig(level=logging.INFO, format="%(message)s")

    if args.check:
        return _run_check(args)

    if args.smoke:
        return _run_smoke(args)

    return _run_full(args)


if __name__ == "__main__":
    import sys

    sys.exit(main())
