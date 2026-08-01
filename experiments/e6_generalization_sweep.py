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

**Provenance (D-31, EXP-11).** `_run_full` also writes `e6_provenance.json`
beside the CSV -- E3's minimal sidecar shape (`experiment`, `schema_version`,
`seed`, `solver_config.seed`, `environment`) -- and every per-configuration
checkpoint under `e6_configs/` is itself self-describing: `schema_version`,
`environment`, `solver_config.seed`, and the full configuration identity that
produced it. The `seed` column on `generalization_sweep.csv` is no longer the
only provenance this experiment carries.
"""

from __future__ import annotations

import argparse
import json
import logging
import tempfile
from pathlib import Path

import numpy as np
import pandas as pd

from aquacal.calibration._observability import SolverDiagnostics
from aquacal.core.board import BoardGeometry
from aquacal.datasets.pipelines import calibrate_synthetic, compute_per_camera_errors
from aquacal.datasets.synthetic import generate_synthetic_detections
from aquacal.io import capture_environment
from aquacal.validation.evaluation import evaluate_calibration
from experiments._io import (
    build_experiment_arg_parser,
    compare_experiment_csv,
    exit_code_for,
    resolve_out_dir,
    validate_args,
    write_experiment_csv,
)
from experiments.e4_benchmark_grid import (
    GRID_DEPTH_RANGE,
    GRID_HEIGHT_ABOVE_WATER,
    GRID_NORMAL_FIXED,
    GRID_SPACING,
    build_grid_scenario,
    default_xy_extent_for_layout,
)

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
# None, None) is `build_grid_scenario`'s own default geometry -- D-29's
# real-rig-like GRID_HEIGHT_ABOVE_WATER / GRID_DEPTH_RANGE / GRID_SPACING and
# D-28's derived xy_extent (see `build_grid_scenario`'s own docstring) -- and
# is the baseline.
#
# `spacing` deliberately varies alongside `depth_range`/`xy_extent` (review
# M2), so varying only the working volume changes the RATIO of working
# volume to camera baseline, not the scale itself. Each non-default setting
# scales all three together by the same factor (0.5x and 2x) relative to
# E4's own new geometry constants (D-28, D-29) -- imported and derived here
# rather than hardcoding a second copy of absolute numbers -- so this axis
# measures "does accuracy hold as the whole rig/tank scales up or down
# together," not a ratio effect. `height_above_water` is deliberately NOT
# swept by this axis (unchanged from `build_grid_scenario`'s own default at
# every scale value): `depth_range` is expressed relative to the water
# surface below so that scaling by 0.5x/2x moves the board within the water
# rather than through the surface into air. The board's `square_size` is
# deliberately NOT scaled -- a real calibration target does not shrink with
# the tank (see `experiments.e4_benchmark_grid.build_grid_scenario`'s own
# docstring, which states this same rationale for GRID_BOARD_CONFIG).
_BASELINE_DEPTH_BELOW_WATER: tuple[float, float] = (
    GRID_DEPTH_RANGE[0] - GRID_HEIGHT_ABOVE_WATER,
    GRID_DEPTH_RANGE[1] - GRID_HEIGHT_ABOVE_WATER,
)
_BASELINE_XY_EXTENT: float = default_xy_extent_for_layout(
    n_cameras=BASELINE_N_CAMERAS, layout=BASELINE_LAYOUT, spacing=GRID_SPACING
)


def _scaled_depth_range(factor: float) -> tuple[float, float]:
    """Scale the baseline's depth-below-water interval by `factor`, then
    re-express it as an absolute Z (world-frame) depth_range by adding back
    `GRID_HEIGHT_ABOVE_WATER` -- keeping the board underwater at every
    scale factor."""
    lo, hi = _BASELINE_DEPTH_BELOW_WATER
    return (
        GRID_HEIGHT_ABOVE_WATER + factor * lo,
        GRID_HEIGHT_ABOVE_WATER + factor * hi,
    )


SCALE_AXIS_VALUES: list[
    tuple[str, tuple[float, float] | None, float | None, float | None]
] = [
    (
        "half_scale",
        _scaled_depth_range(0.5),
        0.5 * _BASELINE_XY_EXTENT,
        0.5 * GRID_SPACING,
    ),
    ("default", None, None, None),
    (
        "double_scale",
        _scaled_depth_range(2.0),
        2.0 * _BASELINE_XY_EXTENT,
        2.0 * GRID_SPACING,
    ),
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
    # WR-02: the first-order solver optimality that distinguishes a converged
    # solve from a diverged one -- e.g. the `double_scale` row that published
    # 1536 px RMS / 1.33 km reconstruction RMSE under status="ok" with nothing
    # in the record to flag it (19.2-22-SUMMARY.md). A MEASUREMENT (D-12): no
    # converged/diverged verdict is derived from it anywhere in this module.
    # Null whenever status != "ok"; optimality_stage3_intrinsic_pass is also
    # null whenever refine_intrinsics=False, since that pass never runs.
    "optimality_stage3_interface_optimization",
    "optimality_stage3_intrinsic_pass",
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
assert len(E6_COLUMNS) == 30 and len(set(E6_COLUMNS)) == 30

E6_KEY_COLUMNS = ["axis", "axis_value"]

# Columns whose value is null for any row whose status is not "ok".
_METRIC_COLUMNS: list[str] = [
    "optimality_stage3_interface_optimization",
    "optimality_stage3_intrinsic_pass",
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


def compute_configuration_metrics(
    scenario,
    result,
    evaluation,
    diag_stage3_interface_optimization: SolverDiagnostics | None = None,
    diag_stage3_intrinsic_pass: SolverDiagnostics | None = None,
) -> dict:
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
        diag_stage3_interface_optimization: The `SolverDiagnostics` sink
            passed to `calibrate_synthetic`'s `diagnostics_out` for the
            interface-optimization solve (WR-02), or `None` if the caller
            did not capture diagnostics -- `optimality` is then null rather
            than fabricated.
        diag_stage3_intrinsic_pass: The `SolverDiagnostics` sink for the
            intrinsic pass, or `None`. Also carries `optimality=None` when
            `refine_intrinsics=False`, since that pass never runs.

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
        "optimality_stage3_interface_optimization": (
            diag_stage3_interface_optimization.optimality
            if diag_stage3_interface_optimization is not None
            else None
        ),
        "optimality_stage3_intrinsic_pass": (
            diag_stage3_intrinsic_pass.optimality
            if diag_stage3_intrinsic_pass is not None
            else None
        ),
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
# Provenance (D-31, EXP-11) and configuration-identity guard (WR-03)
# ---------------------------------------------------------------------------


def build_provenance_sidecar(seed: int, environment: dict | None = None) -> dict:
    """Build E6's minimal provenance sidecar, in E3's exact shape (D-31).

    E6 runs many small calibrations, none of which is a single canonical
    "the" run whose `problem_shape`/`timings` `write_direct_call_benchmark`
    expects -- exactly the situation E3's minimal sidecar exists for
    (`experiments/e3_derived_quantities.py:build_provenance_sidecar`). This is
    the only sidecar format E6 uses; do not invent a second one.

    `solver_config: {"seed": seed}` deliberately duplicates the top-level
    `seed` -- the generic provenance check
    (`tests/unit/test_experiments_provenance.py::_record_seed`) reads
    `solver_config["seed"]`, matching every `assemble_benchmark_record`-shaped
    file, while the top-level `seed` remains for a reader of this sidecar
    specifically.

    Args:
        seed: The run seed.
        environment: A pre-captured `capture_environment()` block to reuse --
            `_run_full`/`_run_smoke_configs` pass the SAME block used to
            stamp every per-configuration checkpoint, so the sidecar names
            the same commit as the sweep it describes -- or `None` to
            capture fresh here (e.g. a standalone caller/test).
    """
    return {
        "experiment": "e6",
        "schema_version": 1,
        "seed": seed,
        "solver_config": {"seed": seed},
        "environment": environment
        if environment is not None
        else capture_environment(),
    }


def _resolve_config_identity(config: dict) -> dict:
    """The full configuration identity to record in a checkpoint: `config`
    plus the resolved `normal_fixed` (every run uses the same
    `GRID_NORMAL_FIXED`, but recording it keeps the identity self-contained)."""
    return {**config, "normal_fixed": GRID_NORMAL_FIXED}


# The fields that determine which SCENE `run_configuration` builds (WR-03).
# Deliberately excludes `axis`, `axis_value`, `is_baseline`, and `config_key`
# -- those only LABEL which row a configuration illustrates and do not change
# what gets computed. The three `is_baseline` configurations (`index/1.333`,
# `layout/grid`, `scale/default`) are, by `build_axis_configurations`'
# construction, the SAME scene under three different labels; comparing full
# identity (including the label fields) guaranteed a mismatch no correct run
# could avoid. Comparing only this set is a fix at the cause, not a loosened
# guard: every field that actually changes the scene is still compared, so a
# checkpoint that predates an axis-value edit (e.g. a changed `n_water`,
# `layout`, or scale geometry) still degrades to `status="failed"` below.
_SCENARIO_IDENTITY_KEYS: tuple[str, ...] = (
    "n_cameras",
    "layout",
    "n_water",
    "depth_range",
    "xy_extent",
    "spacing",
    "normal_fixed",
)


def _scenario_identity(identity: dict) -> dict:
    """Restrict a full configuration identity to `_SCENARIO_IDENTITY_KEYS`."""
    return {key: identity.get(key) for key in _SCENARIO_IDENTITY_KEYS}


def _config_identity_matches(config: dict, cached_config: object) -> bool:
    """True if a checkpoint's recorded config identity matches the one
    recomputed for `config` right now, on the fields that determine the
    SCENE (WR-03, T-19.2-63; scope narrowed from full-identity to
    `_SCENARIO_IDENTITY_KEYS`).

    Both sides are compared through a JSON round-trip so tuple/list
    equivalence (e.g. `depth_range`, a tuple in-memory but a list once
    written to and read back from JSON) never produces a false mismatch --
    `cached_config` already went through exactly one such round-trip when it
    was read off disk.
    """
    expected = json.loads(json.dumps(_resolve_config_identity(config), sort_keys=True))
    actual = json.loads(json.dumps(cached_config, sort_keys=True))
    if not isinstance(actual, dict):
        return False
    return _scenario_identity(actual) == _scenario_identity(expected)


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
    environment: dict | None = None,
) -> dict:
    """Run (or skip, if already cached) one distinct scene, checkpointing to JSON.

    Distinct SCENES are cached by `config["config_key"]` under
    `out_dir/e6_configs/{config_key}.json` -- not by `(axis, axis_value)` --
    because `build_axis_configurations()` deliberately gives the three
    baseline rows the same `config_key` (E6 is the largest sweep in the phase
    and the designated calendar-fallback casualty, so per-configuration
    resumability matters most here; review M7). This mirrors E4's per-cell
    mechanism (`run_grid_cell`): when the checkpoint file already exists,
    parses cleanly, and `force` is False, this returns the checkpoint's
    RECORDED outcome -- status, status_reason, and metrics, exactly as
    written -- rather than discarding them (CR-02, WR-08).

    A checkpoint whose recorded `status` is `"failed"` is ALSO treated as a
    skip candidate, not automatically retried: the skip path is one read site
    for every status rather than a special case per status, and the recorded
    `status_reason` survives the re-entry so the resulting row stays
    explicable. To retry a known failure, re-run with `force=True`. (WR-08's
    alternative -- never skip a failed configuration -- was considered and
    rejected here in favor of this uniform skip path; either choice was
    acceptable, this is the one taken.)

    A checkpoint that exists but fails to parse (corrupt or truncated JSON,
    e.g. from a process killed mid-write) is treated as absent: the
    configuration is re-run below and a fresh checkpoint is written, rather
    than raising out of the longest sweep in the phase.

    Every checkpoint additionally carries `schema_version`, an `environment`
    block, `solver_config: {"seed": seed}`, and the full configuration
    identity that produced it (`config` plus the resolved `normal_fixed`) --
    D-31, WR-03. The `schema_version` opts the file into
    `tests/unit/test_experiments_provenance.py`'s environment/seed checks; the
    recorded configuration identity lets `_reconstitute_row` (used by
    `_run_check`) refuse a cached result whose configuration no longer
    matches what would be recomputed for that `config_key` today (e.g. after
    an axis-value list edit).

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
        environment: A pre-captured `capture_environment()` block to stamp
            this checkpoint with, or `None` to capture fresh here. `run_sweep`
            captures ONCE per sweep and passes the same block to every call
            so one sweep names one commit (measured 2026-07-31:
            `capture_environment()` shells out to `git rev-parse` per call,
            so a commit landing mid-sweep previously split `git_sha` across
            the artifact set -- `baseline.json` recorded `3d5c3e6`, the other
            eleven `3d0aa3e`). `None` remains supported so a direct,
            standalone call (as several unit tests make) still produces a
            complete, self-describing checkpoint.

    Returns:
        A dict with `status` (one of `STATUS_VALUES`), `status_reason`, and
        `metrics` (`compute_configuration_metrics()`'s output, or `None`).
    """
    config_key = config["config_key"]
    config_path = Path(out_dir) / "e6_configs" / f"{config_key}.json"

    if config_path.exists() and not force:
        try:
            with open(config_path) as f:
                cached = json.load(f)
        except (OSError, json.JSONDecodeError) as exc:
            logger.warning(
                "Checkpoint %s is corrupt or unreadable (%s: %s); re-running "
                "configuration %s instead of skipping.",
                config_path,
                type(exc).__name__,
                exc,
                config_key,
            )
        else:
            logger.info(
                "Skipping configuration %s: %s already exists (resumability).",
                config_key,
                config_path,
            )
            return {
                "status": cached.get("status", "failed"),
                "status_reason": cached.get("status_reason", ""),
                "metrics": cached.get("metrics"),
            }

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
        diag_stage3 = SolverDiagnostics()
        diag_intrinsic_pass = SolverDiagnostics()
        result, _detections = calibrate_synthetic(
            scenario,
            n_water=scenario.n_water,
            refine_intrinsics=refine_intrinsics,
            seed=seed,
            normal_fixed=GRID_NORMAL_FIXED,
            diagnostics_out={
                "stage3_interface_optimization": diag_stage3,
                "stage3_intrinsic_pass": diag_intrinsic_pass,
            },
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
        metrics = compute_configuration_metrics(
            scenario, result, evaluation, diag_stage3, diag_intrinsic_pass
        )
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
    checkpoint = {
        **outcome,
        "seed": seed,
        "n_frames": n_frames,
        "schema_version": 1,
        "environment": environment
        if environment is not None
        else capture_environment(),
        "solver_config": {"seed": seed},
        "config": _resolve_config_identity(config),
    }
    with open(config_path, "w") as f:
        json.dump(checkpoint, f, indent=2, sort_keys=True)
    return outcome


def run_sweep(
    configs: list[dict],
    seed: int,
    n_frames: int,
    out_dir: Path,
    *,
    refine_intrinsics: bool = True,
    force: bool = False,
    environment: dict | None = None,
) -> pd.DataFrame:
    """Run every distinct scene in `configs` once, then build one row per config.

    `run_configuration` is called once per distinct `config_key` (a plain
    in-memory cache dict, not a second file check) -- so the three baseline
    rows in `configs` reuse one computed result, satisfying "computed ONCE
    and reused for all three baseline rows" without duplicating I/O.

    The environment is captured ONCE -- here if the caller did not already
    capture one, otherwise the caller's own block is reused -- and the same
    block is stamped on every checkpoint this call writes, not once per
    configuration, so one sweep names one commit (see `run_configuration`'s
    `environment` parameter docstring).

    Args:
        configs: `build_axis_configurations()` or `build_smoke_configurations()`.
        seed: Seed forwarded to every configuration.
        n_frames: Calibration frame count forwarded to every configuration.
        out_dir: Root output directory forwarded to `run_configuration`.
        refine_intrinsics: Forwarded to `calibrate_synthetic`.
        force: Forwarded to `run_configuration`.
        environment: A pre-captured `capture_environment()` block to reuse
            (e.g. so a caller can stamp the same block on this sweep's
            provenance sidecar), or `None` to capture fresh here.

    Returns:
        A `DataFrame` with exactly `E6_COLUMNS`, one row per entry in `configs`.
    """
    environment = environment if environment is not None else capture_environment()
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
                environment=environment,
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


def _reconstitute_row(config: dict, configs_dir: Path, default_seed: int) -> dict:
    """Rebuild one `--check` row from `configs_dir`'s checkpoint, or a failed
    placeholder if no checkpoint exists for `config["config_key"]`.

    Also the single enforcement site for WR-03 (T-19.2-63): when the cached
    checkpoint carries a `config` identity (D-31; the twelve committed
    checkpoints predate this and are only regenerated in wave 4, so their
    absence of a `config` key is trusted rather than flagged), it is compared
    against the configuration recomputed for this `config_key` right now. A
    mismatch degrades the row to `status="failed"` with an explanatory reason
    instead of silently trusting metrics that may belong to a different
    configuration -- e.g. after an axis-value list edit.
    """
    config_path = configs_dir / f"{config['config_key']}.json"
    if not config_path.exists():
        return build_row(
            config,
            default_seed,
            BASELINE_N_FRAMES,
            None,
            status="failed",
            status_reason=(
                "no checkpoint JSON found under e6_configs for this configuration"
            ),
        )

    with open(config_path) as f:
        cached = json.load(f)

    status = cached.get("status", "failed")
    status_reason = cached.get("status_reason", "")
    metrics = cached.get("metrics")
    cached_config = cached.get("config")
    if cached_config is not None and not _config_identity_matches(
        config, cached_config
    ):
        status = "failed"
        status_reason = (
            f"cached config for {config['config_key']} does not match the "
            "recomputed configuration identity (WR-03) -- the checkpoint may "
            "predate an axis-value edit; re-run with --force"
        )
        metrics = None

    return build_row(
        config,
        cached.get("seed", default_seed),
        cached.get("n_frames", BASELINE_N_FRAMES),
        metrics,
        status=status,
        status_reason=status_reason,
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
    rows = [_reconstitute_row(config, configs_dir, args.seed) for config in configs]

    df = pd.DataFrame(rows, columns=E6_COLUMNS)
    report = compare_experiment_csv(
        df, committed_path, key_columns=E6_KEY_COLUMNS, rtol=CHECK_RTOL
    )
    print(report.message)
    return exit_code_for(report)


def _run_smoke_configs(out_dir: Path, seed: int) -> int:
    """Run the reduced smoke config set, then probe the skip-if-exists path (review M7)."""
    environment = capture_environment()
    configs = build_smoke_configurations()
    df = run_sweep(
        configs,
        seed,
        _SMOKE_N_FRAMES,
        out_dir,
        refine_intrinsics=False,
        force=True,
        environment=environment,
    )
    write_experiment_csv(
        df, out_dir / "generalization_sweep.csv", key_columns=E6_KEY_COLUMNS, force=True
    )
    with open(out_dir / "e6_provenance.json", "w") as f:
        json.dump(
            build_provenance_sidecar(seed, environment=environment),
            f,
            indent=2,
            sort_keys=True,
        )

    # Exercise the skip-if-exists path end to end (review M7, CR-02): re-run
    # the first already-checkpointed configuration WITHOUT --force and
    # confirm the cached checkpoint comes back VERBATIM -- proving the resume
    # path returns the recorded outcome (not a discarded/nulled one) and
    # never rewrites the checkpoint it is skipping.
    config_key = configs[0]["config_key"]
    config_path = out_dir / "e6_configs" / f"{config_key}.json"
    with open(config_path) as f:
        cached_before = json.load(f)

    skip_probe = run_configuration(
        configs[0],
        seed,
        _SMOKE_N_FRAMES,
        out_dir,
        refine_intrinsics=False,
        force=False,
    )
    if (
        skip_probe["status"] != cached_before.get("status")
        or skip_probe["metrics"] != cached_before.get("metrics")
        or skip_probe["status_reason"] != cached_before.get("status_reason", "")
    ):
        logger.warning(
            "smoke skip-path probe did not return the cached checkpoint verbatim: "
            "got status=%s metrics=%s, expected status=%s metrics=%s",
            skip_probe["status"],
            skip_probe["metrics"],
            cached_before.get("status"),
            cached_before.get("metrics"),
        )
        return 1

    with open(config_path) as f:
        cached_after = json.load(f)
    if cached_after != cached_before:
        logger.warning(
            "smoke skip-path probe mutated the on-disk checkpoint for %s", config_key
        )
        return 1

    logger.info(
        "smoke: %d rows, skip-path probe status=%s (cached, not recomputed)",
        len(df),
        skip_probe["status"],
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
    """Run the full axis sweep, write `generalization_sweep.csv`, and (D-31)
    the `e6_provenance.json` sidecar beside it.

    Captures the environment ONCE, here, and passes it to both `run_sweep`
    (which stamps every per-configuration checkpoint from it) and the
    provenance sidecar, so the whole artifact set -- checkpoints and sidecar
    alike -- names one commit rather than whatever was HEAD when each piece
    happened to be written.
    """
    out_dir = resolve_out_dir(args.out)
    environment = capture_environment()
    configs = build_axis_configurations()
    df = run_sweep(
        configs,
        args.seed,
        BASELINE_N_FRAMES,
        out_dir,
        refine_intrinsics=True,
        force=args.force,
        environment=environment,
    )
    write_experiment_csv(
        df,
        out_dir / "generalization_sweep.csv",
        key_columns=E6_KEY_COLUMNS,
        force=args.force,
    )
    with open(out_dir / "e6_provenance.json", "w") as f:
        json.dump(
            build_provenance_sidecar(args.seed, environment=environment),
            f,
            indent=2,
            sort_keys=True,
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
