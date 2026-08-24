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
    compared by --check. Carries the SIX degeneracy columns (DEGEN-01/DEGEN-02 via
    plan 24-02): `degenerate_observations_at_solution` plus three
    `degenerate_observations_cause_*` and two `degenerate_observations_fate_*`.
    Cause and fate are two INDEPENDENT AXES over the same set of invalid
    observations, not disjoint buckets -- **never add a cause column to a fate
    column.** Each axis sums independently and exactly to
    `degenerate_observations_at_solution`, so a row where the two axes disagree is
    a bookkeeping bug, visible by eye. The counter is a per-MODEL quantity, so
    every row of a model repeats that model's six values. The three FIXED-CONTRACT
    CSVs above deliberately did NOT gain these columns (D-19 pins their headers
    byte-for-byte for an external figures repository).
  e1_degeneracy_breakdown.json -- the per-stage half D-09 keeps out of the CSVs:
    the full cause x stage and fate x stage breakdown and the per-stage
    `observations_evaluated__*` denominators, keyed by model label, written as the
    raw `discard_stats` dict.
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
never reaches `generate_camera_array`). **That demotion is qualified as of
2026-08-15 -- see STATED DOMAIN immediately below, which is the other half
of this and must be read with it.**

**STATED DOMAIN (BAND-01, D-14).** E1's absolute-accuracy numbers are to be
quoted ONLY over this domain: the `realistic` scenario's single 12-camera
synthetic geometry, ten seeds, detection noise from 0.25 px to 1.2 px, and
the eight test depths of `TEST_DEPTHS` (1.10 m to 2.50 m). Outside it --
another rig geometry, a noisier detector, a deeper test point -- E1's
numbers are unlicensed. This sentence states the domain the claim WILL BE
quoted over; it is NOT a measured result of the phase that wrote it. The
four-level ten-seed band that establishes the domain (640 band rows / 960
parameter-band rows, ~7 h) is EXECUTED IN Phase 28 at the frozen sha and
verified in Phase 29 (D-21). Phase 25 ran a two-seed probe only, which
licenses no manuscript-facing number, because two seeds cannot separate a
noise effect from seed variance. What already supports the claim is
measured and independent of that band: warm-restarting each solve from its
own solution recovers no cost (largest relative drop 1.8e-9), so the
non-refractive baseline is CONVERGED and the comparison is fair -- the
97-178x band is strengthened, not caveated
(`.planning/probes/2026-08-17-optimality-decomposition/FINDINGS.md`). The
one caveat that travels with the band, stated here in the same paragraph so
it can never be read as under-convergence: the non-refractive baseline arm
is **severely ill-conditioned** (directional curvature ~3e8). That is a
property of fitting a pinhole model to refracted data -- expected, not a
defect, and explicitly NOT a reason to qualify the accuracy claim (D-16).

**Why the band's numbers moved (D-13, anti-confusion note -- no emitter and
no computed delta by decision).** Two things changed at once: the
`NOISE_LEVELS` axis above, and FIX-02 freeing the interface normal
(`normal_fixed=False`). No attribution is computed between them, because
the old normal-fixed version will not be published and no manuscript-facing
number depends on the split. Read a moved number accordingly: it is not a
regression and does not need its cause re-derived. If the two must be
separated, THE 0.5 px ROW IS THE CLEAN `normal_fixed` ISOLATOR -- 0.5 px is
the preset default the committed baseline was produced at, so the noise
axis contributes nothing there and any residual move is FIX-02's.

A `--seeds` run NEVER writes
`exp1_parameter_errors.csv`, `exp2_depth_generalization.csv`,
`exp2_spatial_errors.csv`, or `exp3_xy_vs_z_anisotropy.csv` -- those remain
exclusively the single-seed run's artifacts. The band CSV write always
overwrites (force implied for that file only, mirroring E7); no other
artifact's overwrite behavior changes. `--seeds` is mutually exclusive with
`--check`. Each of `e1_benchmark_refractive.json` and
`e1_benchmark_nonrefractive.json` written during a band run additively
carries a `seeds` list holding the resolved seed list, reflecting the LAST
seed's diagnostics/timings/accuracy (one provenance record cannot represent
N independent solves). Since plan 26-13 they ALSO carry
`solver_config["seed"]` naming that last seed -- the two are different
statements: `seed` names what this record measured, `seeds` what the band
swept, and `gate3_provenance` requires the former. The band's OWN provenance
still lives in a separate, band-owned `e1_seed_band_provenance.json` sidecar
(see below), which is what represents the N solves as a set.

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
from experiments._degeneracy import (
    DEGENERACY_COLUMNS,
    summarize_degeneracy_columns,
    write_degeneracy_breakdown,
)
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

# BAND-01/D-11: the detection-noise axis the seed band sweeps, in pixels. Band
# mode ONLY (D-12) -- `_run_smoke`, `_run_check` and the single-seed run keep
# today's behaviour at the scenario preset's own default.
#
# 0.5 px IS the preset default and therefore the level that reproduces the
# committed 160/240-row baseline and E1's `--check` bar. It MUST stay in this
# list: drop it and the band no longer contains the rows the reproduction gate
# compares against, and the clean `normal_fixed` isolator (D-13) disappears
# with it. 0.82 px is the PRODUCTION RIG's measured detection noise and is the
# level that makes the claim transferable; nothing justified 0.5 px physically.
# 0.25 px brackets a well-behaved detector and 1.2 px a deliberately
# pessimistic one -- the P1 probe ran 0.5/0.82/1.2 px on seed 42 and the top
# level neither destabilized the solve nor produced a degenerate observation,
# so the set is kept as locked.
#
# The `n_cameras` GEOMETRY AXIS (`n_cameras in {8, 12, 16}`, considered
# alongside this one) IS EXPLICITLY SKIPPED, NOT FORGOTTEN -- the 2026-08-15
# decision in
# `.planning/todos/pending/2026-08-14-decide-whether-e1-may-carry-absolute-accuracy-claims.md`
# skips it deliberately. E1's `SCENARIO_NAME = "realistic"` resolves to
# `generate_real_rig_array()`, whose 12-camera layout IS the manuscript's
# synthetic rig; varying the camera count would move the geometry the claim is
# quoted over rather than widen its domain. The stated domain in this module's
# docstring is therefore written over ONE geometry and a RANGE of noise, which
# is what the accuracy claim actually needs (D-14). A reader looking for the
# geometry axis should meet this note, not an unexplained omission.
NOISE_LEVELS = [0.25, 0.5, 0.82, 1.2]

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

# D-01/FIX-01: at n_water=1.0 the refractive projector IS the pinhole projector
# (tests/unit/test_refractive_geometry.py::TestUnitIndexPinholeIdentity, agreement
# to atol=1e-12), so water_z is an EXACT null direction in this arm -- the cost is
# flat to 13 significant figures over a 1.5 m sweep while the domain guard climbs
# 0 -> 14,949. A degenerate bounds interval of this half-width around the
# scenario's own ground-truth water_z pins the parameter without removing it from
# the problem. Measured 2026-08-17 (probe_pinned_normal_free.py, both stage-3
# passes patched): recovered water_z = 1.030999999999 m against GT 1.031 m.
WATER_Z_PIN_HALF_WIDTH = 1e-12


def resolve_water_z_pin(scenario, n_water: float) -> float | None:
    """Return the water_z value to pin the non-refractive arm at, or None.

    Returns `None` whenever `n_water != 1.0` -- the refractive arm must stay
    unpinned (water_z is genuinely observable there; pinning it inflates the
    headline ratio to a flattering 168x and breaks the manuscript's
    stable-anisotropy claim, `.planning/MANUSCRIPT-FINDINGS.md:972`).

    At `n_water == 1.0`, reads the scenario's own ground-truth `water_zs` and
    returns the single shared value. Raises `ValueError` if the scenario's
    cameras do not share one water_z -- a shared pin is undefined for a
    non-shared ground truth (E1's `SCENARIO_NAME = "realistic"` scenario
    always shares one, via `generate_real_rig_array`).
    """
    if n_water != 1.0:
        return None
    distinct = set(scenario.water_zs.values())
    if len(distinct) != 1:
        raise ValueError(
            f"resolve_water_z_pin: scenario '{scenario.name}' does not share a "
            f"single water_z across cameras -- found {sorted(distinct)}. A "
            "shared pin is undefined for a non-shared ground truth."
        )
    return next(iter(distinct))


def build_water_z_provenance(pin: float | None) -> dict:
    """D-04 provenance triple for a benchmark record's `solver_config`.

    Both arms carry the same key set (`water_z_pinned_m`, `water_z_pin_mechanism`,
    `water_z_pin_reason`) so a reader diffing the non-refractive and refractive
    records finds both the asymmetry and its justification without leaving the
    artifact.
    """
    if pin is None:
        return {
            "water_z_pinned_m": None,
            "water_z_pin_mechanism": None,
            "water_z_pin_reason": (
                "deliberately NOT pinned: under refraction water_z is genuinely "
                "observable and estimating it is the method's contribution "
                "(.planning/MANUSCRIPT-FINDINGS.md:972)."
            ),
        }
    return {
        "water_z_pinned_m": pin,
        "water_z_pin_mechanism": (
            "degenerate bounds interval (lb = ub -/+ 1e-12) on the water_z "
            "slot, threaded from the experiment to build_bounds at BOTH "
            "stage-3 passes (interface_estimation.py and refinement.py); the "
            "parameter stays packed and is not removed from the problem"
        ),
        "water_z_pin_reason": (
            "at n_water=1.0 the refractive projector IS the pinhole projector "
            "(tests/unit/test_refractive_geometry.py::"
            "TestUnitIndexPinholeIdentity, agreement to atol=1e-12), so "
            "water_z is an exact null direction in this arm -- sweeping it "
            "over 1.5 m leaves the cost constant to 13 significant figures "
            "while the domain-guard count climbs 0 -> 14,949 -- and pinning "
            "it is therefore a reparameterization of a null space, not a "
            "model change. measurement: "
            ".planning/MANUSCRIPT-FINDINGS.md:892-903"
        ),
    }


# Pinned key columns for sort-before-write / --check row realignment (Pitfall 5).
EXP1_KEY_COLUMNS = ["camera", "model"]
EXP2_KEY_COLUMNS = ["test_depth_m", "model"]
EXP3_KEY_COLUMNS = ["test_depth_m", "model"]
SPATIAL_KEY_COLUMNS = ["test_depth_m", "model", "x_m", "y_m", "z_m"]
# D-19.4-14: the band CSV carries every seed's rows, so `seed` joins the key
# columns -- (test_depth_m, model) alone is no longer unique once multiple
# seeds are concatenated (mirrors E7's BAND_KEY_COLUMNS convention).
#
# BAND-01: `noise_std` joins them for exactly the same reason. The band now
# sweeps NOISE_LEVELS inside each seed, so (seed, test_depth_m, model) names
# FOUR rows, not one. `write_experiment_csv` validates only that the key
# columns EXIST -- it sorts by them and never checks uniqueness -- so omitting
# `noise_std` here does not fail loudly: it writes a 640-row file in which
# every key appears four times, and `compare_experiment_csv` is then reporting
# on rows it cannot align.
BAND_KEY_COLUMNS = ["seed", "noise_std", "test_depth_m", "model"]
# A SECOND band key shape, not an extension of BAND_KEY_COLUMNS. EXP1's rows
# are keyed by (camera, model) and have NO depth axis at all, so its columns
# cannot be merged into exp1_band.csv without reindexing them onto a depth
# they do not vary over -- that would fabricate a depth dependence the
# parameter errors do not have. Hence a separate `exp1_parameter_band.csv`.
#
# BAND-01, and a DOCUMENTED DEPARTURE from D-12's literal text, which says
# "only exp1_band.csv gains the column". D-12's rationale is protecting the
# three FIXED-CONTRACT CSVs (exp1_parameter_errors.csv,
# exp2_depth_generalization.csv, exp3_xy_vs_z_anisotropy.csv) that the
# external figures repository reads byte-for-byte -- and those are untouched.
# `exp1_parameter_band.csv` is not one of them: it is a band artifact from the
# same D-19.4-14 precedent, written unconditionally from the same accumulator
# as exp1_band.csv, so the noise axis lands in it whether or not the key list
# admits it. Leaving it out is strictly worse here than on exp1_band.csv,
# because this file has NO depth column to disambiguate the four rows with --
# 960 rows collapse onto 240 distinct keys. The column therefore goes in both
# lists; the tension is settled here rather than rediscovered.
PARAMETER_BAND_KEY_COLUMNS = ["seed", "noise_std", "camera", "model"]

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
SPATIAL_COLUMNS = [
    "test_depth_m",
    "model",
    "x_m",
    "y_m",
    "z_m",
    "signed_error_mm",
    # DEGEN-01/DEGEN-02 via plan 24-02, D-09 as revised 2026-08-17. APPENDED,
    # never inserted. This is the ONLY `_build_dataframes` output that may
    # carry them: `EXP1_COLUMNS`, `EXP2_COLUMNS` and `EXP3_COLUMNS` pin
    # byte-identical headers for an external, read-only figures repository
    # (D-19, "do not add, remove, reorder, or rename a column"), whereas
    # `exp2_spatial_errors.csv` is E1's own output with no committed baseline
    # and is not compared by `--check` (D-20). The counter is a per-MODEL
    # quantity, so every row of a given model repeats that model's values --
    # no per-point split of it is fabricated.
    #
    # `cause` and `fate` are two INDEPENDENT AXES over the same set of
    # degenerate observations, not disjoint buckets. NEVER add a cause column
    # to a fate column -- that double-counts. EACH AXIS SUMS INDEPENDENTLY TO
    # `degenerate_observations_at_solution`, so a row where the two axes
    # disagree is a bookkeeping bug, visible by eye.
    #
    # The per-stage breakdown and the `observations_evaluated__*` denominators
    # live in the `e1_degeneracy_breakdown.json` sidecar, not here.
    "degenerate_observations_at_solution",
    "degenerate_observations_cause_above_interface",
    "degenerate_observations_cause_behind_camera",
    "degenerate_observations_cause_interface_below_camera",
    "degenerate_observations_fate_extended",
    "degenerate_observations_fate_penalized",
]
assert tuple(SPATIAL_COLUMNS[-6:]) == DEGENERACY_COLUMNS

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
    discard_stats, water_z_pin).

    `discard_stats["degenerate_observations_at_solution"]` (D-19.3-11) is the
    final-solution guard count `calibrate_synthetic` recorded via
    `discard_stats_out`; a non-zero count logs one prominent warning here so
    it is never silently swallowed, but this function never raises on it --
    the library records, the harness (or plan 19.3-08's queue script) gates.

    `water_z_pin` (FIX-01) is the resolved pin value (or `None`) from
    `resolve_water_z_pin` -- all four of E1's call sites (`_run_full`,
    `_run_smoke`, `_run_check`, `_run_band`) reach the solver through this one
    function, so the pin is resolved and applied here rather than at each
    caller.
    """
    diag_stage3 = SolverDiagnostics()
    diag_intrinsic_pass = SolverDiagnostics()
    timings: dict[str, float] = {}
    discard_stats: dict[str, int] = {}
    water_z_pin = resolve_water_z_pin(scenario, n_water)
    water_z_bounds = (
        (water_z_pin - WATER_Z_PIN_HALF_WIDTH, water_z_pin + WATER_Z_PIN_HALF_WIDTH)
        if water_z_pin is not None
        else None
    )
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
        # FIX-02: the library signature defaults normal_fixed=True, but
        # CalibrationConfig.interface_normal_fixed defaults to False, and E2's
        # real-rig run and the manuscript's tab:cpr rows were produced at
        # False -- so omitting this argument silently solved a problem two
        # tilt DOF smaller. The one recorded rationale for the old True
        # default (19.2-01-SUMMARY.md:105) is about keeping already-committed
        # Phase-19.1 records bit-identical; that premise is gone because the
        # v2.1 re-run replaces every artifact by design.
        normal_fixed=False,
        water_z_bounds=water_z_bounds,
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
    return result, detections, timings, diagnostics, discard_stats, water_z_pin


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


def _build_dataframes(
    scenario, results, seed, test_depths=None, discard_stats_by_model=None
):
    """Run the depth sweep and assemble the four output DataFrames.

    `results` is a dict keyed by model label ("refractive"/"non_refractive") mapping
    to `(CalibrationResult, DetectionResult)`. Follows the notebook's structure
    exactly (RESEARCH Pitfall 1): each test depth's poses and detections are
    generated ONCE and reused by both models' evaluation.

    Args:
        test_depths: Depths to sweep. Defaults to the module-level `TEST_DEPTHS`
            (the full eight-depth preset); `--smoke` passes a single trivial depth
            instead, without mutating the module constant.
        discard_stats_by_model: Each model label's raw `discard_stats` dict
            from `_run_one_model`, used to fill `exp2_spatial_errors.csv`'s
            six appended degeneracy columns. `None` (the default) writes
            `None` in all six rather than `0` -- `0` means "measured and found
            clean", `None` means "never measured for this row".
    """
    depths = TEST_DEPTHS if test_depths is None else test_depths
    board = BoardGeometry(scenario.board_config)
    # Per-MODEL, computed once: the counter is a property of the model's
    # solve, not of any individual reconstructed point.
    degeneracy_by_model = {
        label: summarize_degeneracy_columns(
            None
            if discard_stats_by_model is None
            else discard_stats_by_model.get(label)
        )
        for label in results
    }

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
                            **degeneracy_by_model[label],
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
    water_z_pin_by_model = {}
    for label, n_water in MODELS:
        print(f"\nCalibrating {label} model (n_water={n_water})...")
        result, detections, timings, diagnostics, discard_stats, water_z_pin = (
            _run_one_model(scenario, n_water, args.seed)
        )
        print(f"  Reprojection RMS: {result.diagnostics.reprojection_error_rms:.4f} px")
        results[label] = (result, detections)
        timings_by_model[label] = timings
        diagnostics_by_model[label] = diagnostics
        discard_stats_by_model[label] = discard_stats
        water_z_pin_by_model[label] = water_z_pin

    print("\nEvaluating depth sweep and anisotropy...")
    df_exp1, df_exp2, df_spatial, df_exp3 = _build_dataframes(
        scenario, results, args.seed, discard_stats_by_model=discard_stats_by_model
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
            seed=args.seed,
            solver_config={
                "robust_loss": "huber",
                "loss_scale": 1.0,
                "refine_intrinsics": True,
                "n_water": n_water,
                "n_air": 1.0,
                "shared_interface": True,
                "normal_fixed": False,
                "ftol": diagnostics_by_model[label][
                    "stage3_interface_optimization"
                ].ftol,
                "xtol": diagnostics_by_model[label][
                    "stage3_interface_optimization"
                ].xtol,
                "gtol": diagnostics_by_model[label][
                    "stage3_interface_optimization"
                ].gtol,
                **build_water_z_provenance(water_z_pin_by_model[label]),
            },
            accuracy={
                "reprojection_rms_px": result.diagnostics.reprojection_error_rms,
                "water_z_recovered_m": float(
                    next(iter(result.cameras.values())).water_z
                ),
            },
            force=args.force,
        )
        print(f"Wrote {record_path}")

    # D-09's sidecar half, keyed by model label: the cause x stage and
    # fate x stage breakdown plus the per-stage `observations_evaluated__*`
    # denominators, none of which belong in a CSV. The RAW dict is written,
    # unaggregated -- same structural argument as D-11, so a counter added to
    # the library later arrives here without this script naming it. Each
    # arm's per-block `optimality_by_block` decomposition needs no work here:
    # it is a `SolverDiagnostics` field, so `assemble_benchmark_record`
    # already emits it beside that stage's `optimality` in
    # `e1_benchmark_<model>.json`.
    write_degeneracy_breakdown(
        out_dir / "e1_degeneracy_breakdown.json",
        {label: dict(stats) for label, stats in discard_stats_by_model.items()},
        force=args.force,
    )

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
        water_z_pin_by_model = {}
        for label, n_water in MODELS:
            result, detections, timings, diagnostics, discard_stats, water_z_pin = (
                _run_one_model(scenario, n_water, args.seed)
            )
            results[label] = (result, detections)
            timings_by_model[label] = timings
            diagnostics_by_model[label] = diagnostics
            discard_stats_by_model[label] = discard_stats
            water_z_pin_by_model[label] = water_z_pin

        df_exp1, df_exp2, df_spatial, df_exp3 = _build_dataframes(
            scenario,
            results,
            args.seed,
            test_depths=smoke_depths,
            discard_stats_by_model=discard_stats_by_model,
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
                seed=args.seed,
                solver_config={
                    "robust_loss": "huber",
                    "loss_scale": 1.0,
                    "refine_intrinsics": True,
                    "n_water": n_water,
                    "n_air": 1.0,
                    "shared_interface": True,
                    "normal_fixed": False,
                    "ftol": diagnostics_by_model[label][
                        "stage3_interface_optimization"
                    ].ftol,
                    "xtol": diagnostics_by_model[label][
                        "stage3_interface_optimization"
                    ].xtol,
                    "gtol": diagnostics_by_model[label][
                        "stage3_interface_optimization"
                    ].gtol,
                    **build_water_z_provenance(water_z_pin_by_model[label]),
                },
                accuracy={
                    "reprojection_rms_px": result.diagnostics.reprojection_error_rms,
                    "water_z_recovered_m": float(
                        next(iter(result.cameras.values())).water_z
                    ),
                },
                force=True,
            )
        write_degeneracy_breakdown(
            tmp_path / "e1_degeneracy_breakdown.json",
            {label: dict(stats) for label, stats in discard_stats_by_model.items()},
            # Smoke write into a throwaway tmp dir -- nothing committed to clobber.
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
        result, detections, _timings, _diagnostics, _discard_stats, _water_z_pin = (
            _run_one_model(scenario, n_water, args.seed)
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
    """`--seeds`: run E1's depth-generalization path once per seed and per
    noise level, emit the band CSV and per-model provenance (D-19.4-14, SC-5a,
    D-260807-dcv, BAND-01).

    BAND-01/D-11/D-12: each seed is run once per level of `NOISE_LEVELS`, with
    `scenario.noise_std` overridden before the solve, and every emitted row is
    stamped with the effective level in a `noise_std` column. The axis is band
    mode's ALONE -- `_run_smoke`, `_run_check` and the single-seed run are
    untouched -- and it collapses to one level under `--smoke`. At production
    scale this takes `exp1_band.csv` from 160 to 640 rows (10 seeds x 4 levels
    x 8 depths x 2 models) and `exp1_parameter_band.csv` from 240 to 960 (10
    seeds x 4 levels x 12 cameras x 2 models).

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
    `exp1_parameter_errors.csv` -- and `e1_seed_band_provenance.json`, which is
    where the band's own seed record lives.

    The two `e1_benchmark_<model>.json` sidecars are written ONLY when they are
    absent (D-07): band mode may create them, carrying
    `solver_config["seeds"] = seeds` and `solver_config["seed"] = seeds[-1]`,
    and never overwrites an existing one -- not even under `--force`, which is
    deliberately not honoured at that one call site. When they already exist the
    run says so and leaves them byte-identical; nothing is lost, because
    `e1_seed_band_provenance.json` records the seeds this band actually swept.
    Deliberately does NOT write
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
    # BAND-01: the noise axis collapses under --smoke exactly as the depth
    # sweep does on the line above. `None` means "leave scenario.noise_std at
    # the preset default", which is the pre-BAND-01 behaviour. Without this
    # collapse every smoke-scale band test (and there are eight of them in
    # tests/unit/test_e1_band_mode.py) would run FOUR times the solves.
    noise_levels = [None] if smoke else NOISE_LEVELS

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
    last_water_z_pin_by_model: dict = {}
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
        nonlocal last_water_z_pin_by_model

        # BAND-01/D-11: the noise loop is nested INSIDE the runner, wrapping
        # the two-model loop -- not outside around `run_seed_band`. Outside,
        # the `last_*` accumulators and the benchmark payload ("taken from the
        # LAST seed") would be ambiguous across four calls of the whole band.
        noise_frames: list[pd.DataFrame] = []
        for noise in noise_levels:
            scenario = create_scenario(scenario_name, seed=seed)
            # D-11: override the scenario's own noise level rather than
            # changing `create_scenario`'s signature (a public-API change two
            # phases before a freeze is what forced v2.0.0 last time). This
            # ONE line is the whole of the axis: `_run_one_model` generates
            # the calibration detections from `scenario.noise_std`, and
            # `_build_dataframes` generates the evaluation set's detections
            # from the same attribute -- so calibration noise and evaluation
            # noise track together for free, which is what a rig-level claim
            # needs.
            if noise is not None:
                scenario.noise_std = noise
            # Never null: when `noise is None` (smoke) the effective level is
            # whatever the preset chose.
            effective_noise = float(scenario.noise_std)

            results: dict = {}
            timings_by_model: dict = {}
            diagnostics_by_model: dict = {}
            discard_stats_by_model: dict = {}
            water_z_pin_by_model: dict = {}
            for label, n_water in MODELS:
                result, detections, timings, diagnostics, discard_stats, water_z_pin = (
                    _run_one_model(scenario, n_water, seed)
                )
                results[label] = (result, detections)
                timings_by_model[label] = timings
                diagnostics_by_model[label] = diagnostics
                discard_stats_by_model[label] = discard_stats
                water_z_pin_by_model[label] = water_z_pin

            df_exp1, df_exp2, _df_spatial, df_exp3 = _build_dataframes(
                scenario, results, seed, test_depths=depths
            )
            # Stamped here, mirroring the existing `.assign(seed=seed)` idiom.
            # `run_seed_band` deliberately does NOT learn about noise: its
            # "call runner once per seed, stamp `seed`, concatenate" contract
            # is shared with E7.
            exp1_frames.append(df_exp1.assign(seed=seed, noise_std=effective_noise))
            noise_frames.append(
                merge_band_columns(df_exp2, df_exp3).assign(noise_std=effective_noise)
            )

            last_results = results
            last_timings_by_model = timings_by_model
            last_diagnostics_by_model = diagnostics_by_model
            last_discard_stats_by_model = discard_stats_by_model
            last_water_z_pin_by_model = water_z_pin_by_model
            last_scenario = scenario

        return pd.concat(noise_frames, ignore_index=True)

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

    # The parameter-level band. `seed` and `noise_std` lead (BAND-01: both are
    # key columns -- see PARAMETER_BAND_KEY_COLUMNS), then all of EXP1_COLUMNS --
    # emitting the full set rather than only the two columns the manuscript
    # needs costs nothing and keeps the per-camera position errors available.
    # EXP1_COLUMNS itself and the single-seed exp1_parameter_errors.csv are
    # untouched: those stay byte-identical to their committed baselines (D-19).
    parameter_band_df = pd.concat(exp1_frames, ignore_index=True)[
        ["seed", "noise_std", *EXP1_COLUMNS]
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
    # e1_benchmark_<model>.json records below are single-seed records that band
    # mode may CREATE when they are absent and NEVER overwrites when they
    # exist, so the seeds actually run here have nowhere else to be recorded.
    #
    # D-07: that policy is ENFORCED, not aspirational. The mechanism is the
    # literal `force=False` at the write_direct_call_benchmark call below --
    # this function's own `force` argument is deliberately not honoured there,
    # and only there. Before phase 29.1 the policy was stated in this comment
    # and contradicted by the call, which passed `force=force`; the resumability
    # guard was all that kept it true, and `--force` removed even that.
    #
    # Two corrections to the sources that filed this, both relied on when the
    # defect was written up and both wrong:
    #
    #   1. A clean experiments/results/ does NOT remove the skip. Stage `e1`
    #      runs with --force (run_experiment_suite.sh's run_stage_e1) and
    #      `e1_band` depends_on `e1`, so both records already exist by the time
    #      the band runs. That is why the skip fired on 2026-08-20 despite a
    #      clean start. The live hazards are (a) a --force band run and (b) a
    #      standalone band into a fresh --out with no preceding single-seed run,
    #      where the write proceeds and stamps the records with seeds[-1].
    #   2. gate3_provenance does NOT depend on this write. `_run_full` already
    #      stamps seed=args.seed onto both records (see :829-871), so nothing
    #      downstream needs band mode to republish them.
    #
    # ASYMMETRY, deliberate: e7_interface_ablation.py's _run_band carries the
    # identical call and the identical comment and is out of phase 29.1's scope,
    # so E7 still passes `force=force` there. Tracked in
    # .planning/todos/pending/2026-08-20-e7-band-mirrors-e1-benchmark-overwrite-hazard.md.
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
                    "STATED DOMAIN (BAND-01, D-14): E1's absolute-accuracy "
                    "numbers are to be quoted ONLY over the 'realistic' "
                    "scenario's single 12-camera synthetic geometry, ten "
                    "seeds, detection noise from 0.25 px to 1.2 px, and the "
                    "eight test depths 1.10-2.50 m. That is the domain the "
                    "claim WILL BE quoted over, not a measured result of the "
                    "phase that wrote this sentence: the four-level ten-seed "
                    "band establishing it (640/960 rows) is executed in Phase "
                    "28 at the frozen sha and verified in Phase 29 (D-21). "
                    "Supporting evidence, already measured: warm restarts "
                    "recover no cost (largest relative drop 1.8e-9), so the "
                    "non-refractive baseline is converged and the comparison "
                    "is fair. The caveat travelling with it, stated together "
                    "so it cannot be read as under-convergence: that baseline "
                    "arm is severely ill-conditioned (~3e8 directional "
                    "curvature), which is a property of fitting a pinhole "
                    "model to refracted data -- expected, not a defect, and "
                    "not a reason to qualify the accuracy claim (D-16). "
                    "This band varies the SEED and (BAND-01) the DETECTION "
                    "NOISE across E1's depth-generalization "
                    "and xy-vs-z anisotropy sweep on the 'realistic' synthetic "
                    "scenario, and bounds seed-to-seed variance of "
                    "exp1_band.csv's metrics -- including z_rmse_mm, the column "
                    "the manuscript's deepest-test-point refractive-vs-"
                    "non-refractive ratio is computed from -- on that synthetic "
                    "scenario only. It ALSO bounds seed-to-seed variance of the "
                    "parameter-level columns emitted in exp1_parameter_band.csv "
                    "(focal_length_error_pct, reprojection_rms_px, and the "
                    "per-camera position errors), over the same seeds and the "
                    "same scenario. It is NOT a physical-rig or real-data claim: "
                    "D-19.3-17's demotion of E1's own accuracy claim is "
                    "qualified, not reversed, by the stated domain above -- "
                    "E1 bounds estimator variance under stated noise, and E2 "
                    "carries the accuracy claim against reality."
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
            "normal_fixed": False,
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
            **build_water_z_provenance(last_water_z_pin_by_model[label]),
        }
        wrote = write_direct_call_benchmark(
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
            # The record reflects the LAST seed's diagnostics/timings/accuracy
            # (see this function's docstring), so that is the seed it is
            # labelled with. `solver_config["seeds"]` still carries the full
            # list -- one names what this record measured, the other what the
            # band swept. Plan 26-13.
            seed=seeds[-1],
            solver_config=solver_config,
            accuracy={
                "reprojection_rms_px": result.diagnostics.reprojection_error_rms,
                "water_z_recovered_m": float(
                    next(iter(result.cameras.values())).water_z
                ),
            },
            # Force is NOT implied for any artifact besides the band CSVs
            # (D-19.4-14), and this is the ONE place where the run's own
            # --force is deliberately not honoured either (D-07). Honouring it
            # is exactly what would turn the policy stated above into a lie:
            # a forced band run would silently republish two records the
            # single-seed stage owns, stamped with seeds[-1]'s values. The
            # literal below is the enforcement; the resumability guard is only
            # a second line of defence.
            force=False,
        )
        # D-06: the log reports what happened, not what was attempted. The
        # writer returns False when it skipped, and printing "Wrote" over that
        # return is the defect this branch replaces. The skip line is worded
        # differently from _io's own logger.info skip message on purpose --
        # two identical claims in one log is the shape the defect had.
        if wrote:
            print(f"Wrote {record_path}")
        else:
            print(
                f"Kept existing {record_path}: band mode never overwrites the "
                "single-seed benchmark record (D-07)."
            )


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
