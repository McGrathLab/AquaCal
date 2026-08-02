"""E5: refractive-index sensitivity (EXP-09).

**The question this experiment answers.** Reviewer point R2 worries that a small
error in the assumed refractive index `n_water` could ruin a calibration. This
experiment refutes that premise: because `n` and reconstructed depth are coupled
(`delta_depth/depth ~= delta_n/n`), index error maps almost entirely into a small
apparent-depth/scale bias rather than into reprojection residuals. The argument
needs BOTH quantities together -- the point is that the bias moves while the
residual does not.

**Real-rig geometry, not a grid family (D-09).** E5 sweeps `n_assumed` on a
scenario hand-assembled from `generate_real_rig_array()` /
`generate_real_rig_trajectory()` -- the rig's actual camera positions and a
board trajectory spanning the full tank footprint at oblique incidence angles,
not a near-normal best case. The three fixed presets used elsewhere in this
package have no preset for this geometry.

**No library parameter was added for E5 (D-23).** Each sweep point is exactly
`calibrate_synthetic(scenario, n_water=n_assumed)` as shipped:
`scenario.n_water` is the TRUE index used to generate the ground-truth
detections, and the `n_water` argument is the ASSUMED index the calibration
runs at -- the same mechanism E1's non-refractive arm already uses.

**Bias is expressed two ways (review M6):**
  - Against the band's OWN Δn = 0 control row (`scale_bias_pct_control`,
    `bias_over_control`) -- the internal comparison that isolates the index
    effect: same geometry, same noise, same seed, same pipeline, differing
    only in the assumed index.
  - Against E2's real-rig held-out noise floor, read LIVE from
    `experiments/results/real_rig_metrics.json` (`holdout_floor_pct`,
    `scale_bias_over_floor`), never hardcoded (D-13).

No column in `E5_COLUMNS` implies a pass/fail verdict -- the CSV reports
magnitudes, not judgements.

Invoked as `python -m experiments.e5_index_sensitivity`. Inherits the shared
five-flag CLI contract (`--seed`, `--out`, `--force`, `--smoke`, `--check`)
from `experiments._io.build_experiment_arg_parser` (D-21).

Emits into `--out`: `index_sensitivity.csv`.

**Scope note:** this module only defines the sweep machinery and is
unit-tested here. The production band is run by plan 19.2-13, in a later
wave, so E5's band never shares the machine with E4's benchmark grid
(review H4).
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
import tempfile
from collections.abc import Mapping
from pathlib import Path

import pandas as pd

from aquacal.core.board import BoardGeometry
from aquacal.datasets import calibrate_synthetic, generate_synthetic_detections
from aquacal.datasets.synthetic import (
    SyntheticScenario,
    board_clearance_floor,
    generate_real_rig_array,
    generate_real_rig_trajectory,
)
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
from experiments.e1_refractive_comparison import compute_scale_bias
from experiments.e4_benchmark_grid import GRID_BOARD_CONFIG

logger = logging.getLogger(__name__)

# Numeric tolerance, matching every other experiment script's declared
# reproducibility contract (D-22).
CHECK_RTOL = 1e-6

# Pinned so `datasets/pipelines.py`'s `scenario.name != "calibration"` branch
# (review L1) never accidentally selects the flat-1.0 initial_water_zs path --
# this string must never equal "calibration".
E5_SCENARIO_NAME = "e5_real_rig"

# E5's whole yardstick is E2's held-out floor, and E2 ran under
# CalibrationConfig.interface_normal_fixed = False (schema.py:333). Passing
# this explicitly to every calibrate_synthetic call keeps E5 tilt-enabled like
# E2, rather than silently comparing against the library's tilt-fixed default
# (review H1).
E5_NORMAL_FIXED = False

# The true index used to generate every held-out and calibration detection
# set. 1.333 is itself present in the band as the zero-Δn control row.
N_TRUE = 1.333

# Declared as a literal list, not a range()/arange() expression, so the swept
# values are data rather than derived at runtime (P4) and appear verbatim in
# the plan summary. Spans +/-0.01 around N_TRUE at ~0.002 steps (11 points).
N_ASSUMED_BAND: list[float] = [
    1.323,
    1.325,
    1.327,
    1.329,
    1.331,
    1.333,
    1.335,
    1.337,
    1.339,
    1.341,
    1.343,
]

E5_COLUMNS: list[str] = [
    "seed",
    "n_true",
    "n_assumed",
    "delta_n",
    "delta_n_over_n",
    "reprojection_rms_px",
    "reconstruction_mae_mm",
    "reconstruction_rmse_mm",
    "signed_mean_mm",
    "scale_bias_frac",
    "scale_bias_pct",
    "scale_bias_pct_control",
    "bias_over_control",
    "holdout_floor_pct",
    "scale_bias_over_floor",
    "num_comparisons",
    "num_frames",
]
E5_KEY_COLUMNS = ["n_assumed"]

# The real-rig board is the same literal the package's "realistic" preset
# builds inline -- imported from E4's grid module (plan 19.2-07's output)
# rather than declared a third time here.
BOARD_CONFIG = GRID_BOARD_CONFIG

# Distinct from the calibration-generation seed so the held-out set is never
# drawn from the same noise realization as the frames the calibration itself
# trained on.
HOLDOUT_SEED_OFFSET = 100_000

# The production band's calibration frame count and refine_intrinsics setting,
# lifted to named constants so the provenance sidecar (`build_provenance_
# sidecar`) can read the exact values `_run_full` uses rather than restating
# them as literals that could silently drift from the run (WR-04).
E5_N_FRAMES = 30
E5_REFINE_INTRINSICS = False

# Matches `generate_real_rig_trajectory`'s own internal `ROTATION_RANGE_DEG`
# (D-19.3-03 keeps that generator at 20 deg) -- must stay in step with it, or
# `_e5_real_rig_depth_range` below would derive a floor for the wrong tilt.
_E5_ROTATION_RANGE_DEG = 20.0


def _e5_real_rig_depth_range(water_zs: Mapping[str, float]) -> tuple[float, float]:
    """Single source of E5's `depth_range`, called at BOTH the calibration
    trajectory site and the held-out trajectory site (D-19.3-04).

    A calibration set and a held-out set built at different depths would
    silently make E5's generalization number measure the wrong thing --
    routing both call sites through this one function (rather than each
    independently passing `depth_range=None` and trusting the derivation to
    agree) makes that impossible by construction: same board, same
    `water_zs`, same rotation range in, same `depth_range` out, always.
    """
    return (
        board_clearance_floor(BOARD_CONFIG, water_zs, _E5_ROTATION_RANGE_DEG),
        2.0,
    )


def build_real_rig_scenario(
    n_frames: int, seed: int, n_true: float
) -> SyntheticScenario:
    """Build E5's scenario on the real rig's actual geometry.

    Unlike E1/E7, which use the package's three fixed presets, E5's
    scenario is hand-assembled from `generate_real_rig_array()` (12-camera
    real-rig geometry) and `generate_real_rig_trajectory()` (a board
    trajectory spanning the rig's full footprint at oblique incidence
    angles). This geometry -- not a synthetic grid family -- is deliberate:
    the R2 argument is about how index error maps into depth bias at
    REALISTIC incidence angles across the full tank, not a near-normal best
    case (D-09).

    Args:
        n_frames: Number of board poses to generate.
        seed: Random seed for both camera-array idealization bookkeeping
            (unused by `generate_real_rig_array`, which takes no seed) and
            the board trajectory.
        n_true: Refractive index recorded as this scenario's ground truth
            (`scenario.n_water`). Detections are NOT generated here --
            callers pass this same value to `generate_synthetic_detections`.

    Returns:
        A `SyntheticScenario` with `name=E5_SCENARIO_NAME`, pinned so
        `datasets/pipelines.py`'s `scenario.name != "calibration"` branch
        (review L1) never mistakes this scenario for the flat-1.0
        initial_water_zs path.
    """
    intrinsics, extrinsics, water_zs = generate_real_rig_array()
    board_poses = generate_real_rig_trajectory(
        n_frames=n_frames,
        board=BOARD_CONFIG,
        water_zs=water_zs,
        depth_range=_e5_real_rig_depth_range(water_zs),
        seed=seed,
    )
    return SyntheticScenario(
        name=E5_SCENARIO_NAME,
        board_config=BOARD_CONFIG,
        intrinsics=intrinsics,
        extrinsics=extrinsics,
        water_zs=water_zs,
        board_poses=board_poses,
        noise_std=0.5,
        description=(
            "E5 index-sensitivity scenario: real 12-camera rig geometry "
            "(generate_real_rig_array/generate_real_rig_trajectory), full-tank "
            "oblique-incidence board trajectory"
        ),
        n_air=1.0,
        n_water=n_true,
        seed=seed,
    )


def load_holdout_floor_pct(metrics_path: Path, square_size_m: float) -> float | None:
    """Read E2's held-out noise floor live and express it as a percentage (D-13).

    Reads `inter_corner_rmse_mm` out of the committed `real_rig_metrics.json`
    and divides by the board's own square size (in mm) -- the same
    denominator `compute_scale_bias`/`scale_bias_pct` use, so the two
    percentages are directly comparable. This value must NEVER be hardcoded:
    it is E5's yardstick for how the sweep's bias compares to E2's real-rig
    measurement floor.

    Args:
        metrics_path: Path to `real_rig_metrics.json`.
        square_size_m: The ChArUco board's square size, in metres.

    Returns:
        The held-out noise floor as a percentage of the board square size, or
        `None` if `metrics_path` does not exist (logged as a WARNING) --
        never a fabricated value.
    """
    if not metrics_path.exists():
        logger.warning(
            "Held-out noise floor file not found at %s; holdout_floor_pct and "
            "scale_bias_over_floor will be null.",
            metrics_path,
        )
        return None
    with open(metrics_path) as f:
        metrics = json.load(f)
    inter_corner_rmse_mm = metrics["inter_corner_rmse_mm"]
    square_size_mm = square_size_m * 1000.0
    return (inter_corner_rmse_mm / square_size_mm) * 100.0


def build_provenance_sidecar(
    seed: int, discard_stats: dict[str, int] | None = None
) -> dict:
    """Build E5's provenance sidecar in E3's exact shape (D-31, WR-04).

    Beyond the four EXP-11 fields (seed, AquaCal version, git SHA, environment),
    the sidecar carries the configuration WR-04 identifies as unreconstructable
    from `index_sensitivity.csv` alone: `refine_intrinsics` (which defaulted to
    `False` for the whole production band -- a best-case bound the CSV cannot
    reveal on its own), `normal_fixed` (`E5_NORMAL_FIXED`), the calibration
    frame count, the swept `n_assumed` band, `n_true`, and
    `HOLDOUT_SEED_OFFSET`. Every value is read from the same module constants
    `_run_full` uses (never restated as a literal), so the record cannot drift
    from the run it describes.

    `solver_config: {"seed": seed}` deliberately duplicates the top-level
    `seed` key, matching E3's documented convention
    (`e3_derived_quantities.build_provenance_sidecar`): the generic
    schema_version-keyed provenance check reads `solver_config["seed"]`.

    Args:
        seed: The seed the production band ran at (`args.seed`).
        discard_stats: The band-summed discard counters (plan 19.2-26's
            `discard_stats_out`, `run_band`'s own summation), or `None` if
            accounting was never requested for this call. `None` is kept
            distinguishable from a populated-but-all-zero dict: `None`
            means "never asked" (e.g. this sidecar was built for `--smoke`
            or `--check`, neither of which requests accounting), a
            populated dict means "asked, and this is what the run's own
            output counted" -- which is what plan 19.2-23's attribution
            gate (`discard_stats.pnp_guard_rejected > 0` "in the run's own
            output") needs to be runnable at all.

    Returns:
        A dict with `experiment == "e5"`, `schema_version`, `seed`,
        `solver_config["seed"]`, an `environment` block, the run
        configuration described above, and `discard_stats`.
    """
    return {
        "experiment": "e5",
        "schema_version": 1,
        "seed": seed,
        "solver_config": {"seed": seed},
        "environment": capture_environment(),
        "refine_intrinsics": E5_REFINE_INTRINSICS,
        "normal_fixed": E5_NORMAL_FIXED,
        "n_frames": E5_N_FRAMES,
        "n_assumed_band": list(N_ASSUMED_BAND),
        "n_true": N_TRUE,
        "holdout_seed_offset": HOLDOUT_SEED_OFFSET,
        "discard_stats": discard_stats,
    }


def build_row(
    evaluation,
    n_assumed: float,
    n_true: float,
    seed: int,
    square_size_m: float,
) -> dict:
    """Build one E5 row from a held-out evaluation.

    Returns exactly `E5_COLUMNS`, in order. The band-level columns
    (`scale_bias_pct_control`, `bias_over_control`, `holdout_floor_pct`,
    `scale_bias_over_floor`) cannot be computed from a single point -- they
    are left `None` here and filled in afterward by `add_control_columns`/
    `add_holdout_floor_columns` once the full band has run (D-13, review M6).

    Args:
        evaluation: A `HeldOutEvaluation` (or any object exposing the same
            `.reprojection.rms`, `.reconstruction.{mean,rmse,signed_mean,
            num_comparisons}`, `.num_frames` shape -- unit tests pass a
            hand-built fixture rather than a real `HeldOutEvaluation`).
        n_assumed: The refractive index the calibration assumed.
        n_true: The refractive index the held-out detections were generated
            at.
        seed: The seed this point ran at (review H5 -- every row carries its
            own seed).
        square_size_m: The ChArUco board's square size, in metres.

    Returns:
        A dict with exactly `E5_COLUMNS` as keys, in `E5_COLUMNS` order.
    """
    signed_mean_m = evaluation.reconstruction.signed_mean
    scale_bias_frac = compute_scale_bias(signed_mean_m, square_size_m)
    scale_bias_pct = (scale_bias_frac - 1.0) * 100.0
    delta_n = n_assumed - n_true

    row = {
        "seed": seed,
        "n_true": n_true,
        "n_assumed": n_assumed,
        "delta_n": delta_n,
        "delta_n_over_n": delta_n / n_true,
        "reprojection_rms_px": evaluation.reprojection.rms,
        "reconstruction_mae_mm": evaluation.reconstruction.mean * 1000.0,
        "reconstruction_rmse_mm": evaluation.reconstruction.rmse * 1000.0,
        "signed_mean_mm": signed_mean_m * 1000.0,
        "scale_bias_frac": scale_bias_frac,
        "scale_bias_pct": scale_bias_pct,
        "scale_bias_pct_control": None,
        "bias_over_control": None,
        "holdout_floor_pct": None,
        "scale_bias_over_floor": None,
        "num_comparisons": evaluation.reconstruction.num_comparisons,
        "num_frames": evaluation.num_frames,
    }
    return {col: row[col] for col in E5_COLUMNS}


def add_control_columns(df: pd.DataFrame, n_true: float) -> pd.DataFrame:
    """Fill `scale_bias_pct_control`/`bias_over_control` from the band's own Δn=0 row.

    The band's `n_assumed == n_true` row is the correct internal control
    (review M6): same geometry, same noise, same seed, same pipeline,
    differing only in the assumed index. Computed AFTER the whole band has
    run, from the band's own rows -- never from a hardcoded value, and never
    from a partial band.

    Args:
        df: A DataFrame with (at least) `n_assumed` and `scale_bias_pct`
            columns, covering the full swept band.
        n_true: The true index -- selects the control row via
            `n_assumed == n_true`.

    Returns:
        A copy of `df` with `scale_bias_pct_control` (identical on every
        row) and `bias_over_control` (`abs(scale_bias_pct -
        scale_bias_pct_control)`, `0.0` on the control row itself) filled
        in.

    Raises:
        ValueError: If no row has `n_assumed == n_true` -- the control row
            is mandatory, not optional.
    """
    control_rows = df.index[df["n_assumed"] == n_true]
    if len(control_rows) == 0:
        raise ValueError(
            f"No row with n_assumed == n_true ({n_true}) found; the Δn=0 "
            "control row is mandatory."
        )
    control_pct = float(df.loc[control_rows[0], "scale_bias_pct"])

    out = df.copy()
    out["scale_bias_pct_control"] = control_pct
    out["bias_over_control"] = (out["scale_bias_pct"] - control_pct).abs()
    return out


def add_holdout_floor_columns(
    df: pd.DataFrame, metrics_path: Path, square_size_m: float
) -> pd.DataFrame:
    """Fill `holdout_floor_pct`/`scale_bias_over_floor` from a live-read noise floor.

    Args:
        df: A DataFrame with (at least) a `scale_bias_pct` column.
        metrics_path: Path to `real_rig_metrics.json`.
        square_size_m: The ChArUco board's square size, in metres.

    Returns:
        A copy of `df` with `holdout_floor_pct` (identical on every row) and
        `scale_bias_over_floor` (`abs(scale_bias_pct) / holdout_floor_pct`)
        filled in. Both are `None`/NaN on every row if `metrics_path` is
        missing.
    """
    floor_pct = load_holdout_floor_pct(metrics_path, square_size_m)
    out = df.copy()
    out["holdout_floor_pct"] = floor_pct
    if floor_pct is None:
        out["scale_bias_over_floor"] = None
    else:
        out["scale_bias_over_floor"] = out["scale_bias_pct"].abs() / floor_pct
    return out


def run_index_point(
    n_assumed: float,
    n_true: float,
    n_frames: int,
    seed: int,
    refine_intrinsics: bool = False,
    discard_stats_out: dict[str, int] | None = None,
) -> dict:
    """Run one sweep point: calibrate at `n_assumed`, score against `n_true` ground truth.

    Builds a fresh scenario at `n_true`, calibrates it via the shipped
    `calibrate_synthetic(scenario, n_water=n_assumed, ...)` path (D-23 -- no
    library parameter was added for E5), generates a SEPARATE held-out
    detection set at `n_true` from a distinct board-pose set at a distinct
    seed, and scores the calibration against it via `evaluate_calibration`
    (never `evaluate_reconstruction`, which assumes rather than estimates
    board poses -- see the interfaces block in the plan).

    Args:
        n_assumed: The refractive index the calibration assumes.
        n_true: The refractive index the ground truth (both calibration
            detections and the held-out set) is generated at.
        n_frames: Number of calibration frames.
        seed: Seed for the calibration scenario/detections. The held-out set
            uses `seed + HOLDOUT_SEED_OFFSET` -- a distinct seed, distinct
            board poses.
        refine_intrinsics: Forwarded to `calibrate_synthetic`.
        discard_stats_out: Forwarded to `calibrate_synthetic`'s
            `discard_stats_out` sink (plan 19.2-26's counters). `None`
            (the default) disables accounting for this point, matching
            `calibrate_synthetic`'s own inert-when-omitted default.

    Returns:
        A dict with exactly `E5_COLUMNS` as keys (band-level columns left
        `None`, filled in by the caller after the whole band has run).
    """
    scenario = build_real_rig_scenario(n_frames, seed, n_true)
    board = BoardGeometry(scenario.board_config)

    result, _detections = calibrate_synthetic(
        scenario,
        n_water=n_assumed,
        refine_intrinsics=refine_intrinsics,
        seed=seed,
        normal_fixed=E5_NORMAL_FIXED,
        discard_stats_out=discard_stats_out,
    )

    holdout_seed = seed + HOLDOUT_SEED_OFFSET
    holdout_poses = generate_real_rig_trajectory(
        n_frames=n_frames,
        board=BOARD_CONFIG,
        water_zs=scenario.water_zs,
        depth_range=_e5_real_rig_depth_range(scenario.water_zs),
        seed=holdout_seed,
    )
    holdout_detections = generate_synthetic_detections(
        intrinsics=scenario.intrinsics,
        extrinsics=scenario.extrinsics,
        water_zs=scenario.water_zs,
        board=board,
        board_poses=holdout_poses,
        noise_std=scenario.noise_std,
        n_air=1.0,
        n_water=n_true,
        seed=holdout_seed,
    )

    evaluation = evaluate_calibration(result, holdout_detections, board)

    return build_row(
        evaluation,
        n_assumed=n_assumed,
        n_true=n_true,
        seed=seed,
        square_size_m=scenario.board_config.square_size,
    )


def run_band(
    band: list[float],
    n_true: float,
    n_frames: int,
    seed: int,
    metrics_path: Path,
    refine_intrinsics: bool = False,
    discard_stats_out: dict[str, int] | None = None,
) -> pd.DataFrame:
    """Run every point in `band` and assemble the finished, control-and-floor-filled DataFrame.

    Args:
        band: The list of `n_assumed` values to sweep.
        n_true: The true index every point's ground truth is generated at.
        n_frames: Number of calibration frames per point.
        seed: Seed for every point's calibration scenario/detections.
        metrics_path: Path to `real_rig_metrics.json` for the live-read
            noise floor.
        refine_intrinsics: Forwarded to each `run_index_point` call.
        discard_stats_out: If given, accumulates every point's per-point
            `discard_stats` counters SUMMED into this caller-owned dict
            (plan 19.2-23's attribution gate reads `pnp_guard_rejected` off
            the run's own output; E5 previously emitted nothing). Summed
            across the whole band rather than kept per-point: every point
            shares the same rig geometry and only `n_assumed` differs, so
            the attribution question -- did the guard activate anywhere in
            this run -- is answered at the band level, not per index value.
            `None` (the default) disables accounting entirely, matching
            `calibrate_synthetic`'s own inert-when-omitted default.

    Returns:
        A DataFrame with exactly `E5_COLUMNS`, every row's `scale_bias_pct_control`/
        `bias_over_control`/`holdout_floor_pct`/`scale_bias_over_floor` filled in.
    """
    rows = []
    for n_assumed in band:
        logger.info("Running n_assumed=%.4f (n_true=%.4f)...", n_assumed, n_true)
        point_stats: dict[str, int] | None = (
            {} if discard_stats_out is not None else None
        )
        row = run_index_point(
            n_assumed=n_assumed,
            n_true=n_true,
            n_frames=n_frames,
            seed=seed,
            refine_intrinsics=refine_intrinsics,
            discard_stats_out=point_stats,
        )
        if discard_stats_out is not None and point_stats:
            for key, value in point_stats.items():
                discard_stats_out[key] = discard_stats_out.get(key, 0) + value
        logger.info(
            "  reprojection_rms_px=%.4f scale_bias_pct=%.4f",
            row["reprojection_rms_px"],
            row["scale_bias_pct"],
        )
        rows.append(row)

    df = pd.DataFrame(rows, columns=E5_COLUMNS)
    df = add_control_columns(df, n_true)
    board = BoardGeometry(GRID_BOARD_CONFIG)
    df = add_holdout_floor_columns(df, metrics_path, board.config.square_size)
    return df[E5_COLUMNS]


def _default_metrics_path() -> Path:
    """Resolve `real_rig_metrics.json` relative to this file, never the process cwd (WR-06).

    `holdout_floor_pct` and `scale_bias_over_floor` -- the two columns this
    path feeds -- are the yardsticks E5's whole argument rests on. A
    cwd-relative miss degrades both to null with only a WARNING (see
    `load_holdout_floor_pct`), which is a silently degraded artifact of
    exactly the kind this phase exists to eliminate: in wave 5's re-run it
    would surface as two columns moving from populated to null,
    indistinguishable at a glance from a determinism defect. Anchoring to
    `__file__` (the same pattern `e3_derived_quantities.py` uses for
    `_E2_BENCHMARK_JSON_PATH`) makes resolution independent of the directory
    the process was launched from.
    """
    return (
        Path(__file__).resolve().parents[1]
        / "experiments"
        / "results"
        / "real_rig_metrics.json"
    )


def _run_full(args: argparse.Namespace) -> int:
    """Run the full N_ASSUMED_BAND at a well-conditioned frame count.

    Requests discard-stats accounting (plan 19.2-26's counters, summed by
    `run_band` across the whole band) so `e5_provenance.json` carries the
    evidence plan 19.2-23's attribution gate reads.
    """
    out_dir = resolve_out_dir(args.out)
    discard_stats: dict[str, int] = {}
    df = run_band(
        band=N_ASSUMED_BAND,
        n_true=N_TRUE,
        n_frames=E5_N_FRAMES,
        seed=args.seed,
        metrics_path=_default_metrics_path(),
        refine_intrinsics=E5_REFINE_INTRINSICS,
        discard_stats_out=discard_stats,
    )
    write_experiment_csv(
        df,
        out_dir / "index_sensitivity.csv",
        key_columns=E5_KEY_COLUMNS,
        force=args.force,
    )

    sidecar_path = out_dir / "e5_provenance.json"
    if args.force or not sidecar_path.exists():
        sidecar = build_provenance_sidecar(args.seed, discard_stats=discard_stats)
        sidecar_path.parent.mkdir(parents=True, exist_ok=True)
        with open(sidecar_path, "w") as f:
            json.dump(sidecar, f, indent=2, sort_keys=True)
    else:
        logger.info(
            "Skipping write to %s: file already exists and --force was not given "
            "(resumability).",
            sidecar_path,
        )

    print("\nE5 run complete.")
    return 0


def _run_check(args: argparse.Namespace) -> int:
    """Recompute the full band fresh and compare against the committed baseline (D-22).

    Never writes. Checks the committed baseline exists BEFORE re-running the
    band (WR-12) -- a missing baseline costs a message rather than eleven real
    calibrations (~22 min) -- then reruns `run_band` at the same seed/frame
    count as `_run_full` and compares the fresh DataFrame against the
    committed `index_sensitivity.csv` at `CHECK_RTOL`, proving the production
    run plan 19.2-13 committed is reproducible.
    """
    out_dir = resolve_out_dir(args.out)
    baseline_path = out_dir / "index_sensitivity.csv"
    if not baseline_path.exists():
        print(f"No committed baseline at {baseline_path} to check against.")
        return 1

    df = run_band(
        band=N_ASSUMED_BAND,
        n_true=N_TRUE,
        n_frames=E5_N_FRAMES,
        seed=args.seed,
        metrics_path=_default_metrics_path(),
        refine_intrinsics=E5_REFINE_INTRINSICS,
    )
    report = compare_experiment_csv(
        df,
        baseline_path,
        key_columns=E5_KEY_COLUMNS,
        rtol=CHECK_RTOL,
    )
    print(f"[index_sensitivity.csv] {report.message}")
    return exit_code_for(report)


def _run_smoke_at(out_dir: Path, args: argparse.Namespace) -> int:
    """Run 2 band points at a small frame count into an already-resolved `out_dir`."""
    smoke_band = [N_TRUE, N_ASSUMED_BAND[-1]]
    df = run_band(
        band=smoke_band,
        n_true=N_TRUE,
        n_frames=4,
        seed=args.seed,
        metrics_path=_default_metrics_path(),
        refine_intrinsics=False,
    )
    write_experiment_csv(
        df,
        out_dir / "index_sensitivity.csv",
        key_columns=E5_KEY_COLUMNS,
        force=True,
    )
    print(f"Smoke-wrote index_sensitivity.csv to {out_dir}")
    return 0


def _run_smoke(args: argparse.Namespace, parser: argparse.ArgumentParser) -> int:
    """Run 2 band points at a small frame count.

    Honors an explicitly-passed `--out`; otherwise falls back to a throwaway
    temp directory so a bare `--smoke` never pollutes the real
    `experiments/results` output (matching E7's pattern).
    """
    if args.out == parser.get_default("out"):
        with tempfile.TemporaryDirectory(prefix="e5_smoke_") as tmp:
            out_dir = resolve_out_dir(Path(tmp))
            return _run_smoke_at(out_dir, args)
    out_dir = resolve_out_dir(args.out)
    return _run_smoke_at(out_dir, args)


def build_arg_parser() -> argparse.ArgumentParser:
    """Build E5's CLI parser: the shared five-flag contract, no extra flags."""
    parser = argparse.ArgumentParser(
        description=__doc__, parents=[build_experiment_arg_parser()]
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    """CLI entry point for `python -m experiments.e5_index_sensitivity`."""
    parser = build_arg_parser()
    args = parser.parse_args(argv)
    validate_args(parser, args)

    logging.basicConfig(level=logging.INFO, format="%(message)s")

    if args.check:
        return _run_check(args)
    if args.smoke:
        return _run_smoke(args, parser)
    return _run_full(args)


if __name__ == "__main__":
    sys.exit(main())
