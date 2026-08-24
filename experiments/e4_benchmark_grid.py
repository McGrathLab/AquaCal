"""E4: cameras x frames direct-call synthetic benchmark grid (EXP-08).

**What this is.** A direct-call synthetic benchmark grid over the cross product
`CAMERA_COUNTS x FRAME_COUNTS` = `{8, 12, 16} x {50, 100, 200}` (nine declared
cells, `DECLARED_CELLS`). Each cell builds a `generate_camera_array` +
`generate_board_trajectory` scene (`build_grid_scenario`), calibrates it via
`aquacal.datasets.pipelines.calibrate_synthetic`, and assembles a per-cell
`benchmark.json` via `experiments._io.write_direct_call_benchmark` (D-01) --
the same direct-call path E1 and E7 already run in production. This is a
rewrite of the module's previous contents, which subsampled a *real*
13-camera YAML and called the pipeline's config-driven entry point -- that path cannot
reach 16 cameras (unreachable from a 13-camera rig) and a single real run
takes 48-87 minutes, so a real nine-cell sweep is out of scope for a
2026-08-21 deadline.

**Every cell runs tilt-ENABLED** (`GRID_NORMAL_FIXED = False`), matching the
pipeline default (`schema.py`'s `interface_normal_fixed=False`), E2's
real-rig point, and every `tab:cpr` row -- and the row says so, because
`normal_fixed` and `shared_interface` are both `solver_config` keys and CSV
columns (review H1, L6).

**Every cell runs in its own child process** (`run_cell_subprocess`), so
`peak_bytes_*` is a genuine single-run high-water mark rather than a
process-lifetime maximum contaminated by earlier cells, and an OS-level OOM
kill becomes a non-zero exit code the parent records as `status=failed`
instead of a death `except Exception` can never observe (review H2, H3).
Every cell is additionally bounded by `CELL_TIMEOUT_SECONDS`: a
`subprocess.TimeoutExpired` is mapped onto a recorded `status=failed` row
with a reason distinguishable from a non-zero exit, never an exception
(D-33 gap 2).

**A cell cannot silently report a paged success as a clean `ok`** (D-33 gap
3): this box has no OOM killer, so a thrashing cell can otherwise succeed
via pagefile with an inflated wall-clock and an understated *resident*
peak. Each cell records commit/virtual memory alongside `peak_wset`
(`aquacal.io.benchmark.capture_peak_memory`'s additive fields), classifies
itself with a `memory_pressure` measurement CONDITION (never a pass/fail
verdict -- D-12 stands). A cell too large for the machine is not predicted:
it runs, and its failure is recorded from what actually happened -- an OOM
kills only that cell's child process and yields a `status="failed"` row with
its exit code, and a thrashing cell is bounded by the per-cell timeout.

**Every declared cell emits a row unconditionally** (D-04): `status` is one
of `ok`, `degenerate`, `failed`, `skipped_existing`; a cell with no
`benchmark.json` still produces a row via a left join onto the literal
`DECLARED_CELLS` list, so a coverage gap is countable, not invisible. A
`skipped_existing` cell whose record IS on disk keeps that record's metrics
(CR-01) -- the resume path (D-24) exists precisely so a resumed run publishes
what it already computed.

**A cell whose final solution recorded a non-zero
`degenerate_observations_at_solution` guard count is downgraded from `ok` (or
`skipped_existing`) to `degenerate`** in `build_grid_dataframe` (D-19.3-11,
plan 19.3-07) -- its metrics stay populated, but no consumer may read
`status="degenerate"` as converged. The count is recorded and warned about
for EVERY cell, including `SMOKE_CELLS`, but the gate itself only ever
applies to a `DECLARED_CELLS` cell: `build_grid_dataframe` is the sole gating
site and `_run_smoke_cells` never calls it, so `--smoke` cannot report a
false failure from this count.

Invoked as `python -m experiments.e4_benchmark_grid`. Inherits the shared
five-flag CLI contract (`--seed`, `--out`, `--force`, `--smoke`, `--check`)
from `experiments._io.build_experiment_arg_parser` (D-21), plus one
script-local flag: `--cell <n_cameras>x<n_frames>`, the CHILD-process entry
point `run_cell_subprocess` spawns to run exactly one cell and exit (review
H2, H3). `--cell` is not for interactive use.

`--check` re-aggregates the per-cell `benchmark.json` files ALREADY ON DISK
under `e4_cells/` and compares the resulting frame against the committed
`benchmark_grid.csv` at `CHECK_RTOL`. It never re-runs a cell, never spawns a
subprocess, and never writes -- it verifies the aggregation and the committed
CSV against the records, NOT the reproducibility of the nine calibrations
themselves (that would be a multi-hour operation). A reader must not read a
green `--check` as evidence the nine solves reproduce.

**`optimality_stage3_interface_optimization` ships with a caveat, and the
caveat travels inside the artifact** (D-17, DEGEN-05): the emitted
`benchmark_grid.tex` carries `OPTIMALITY_CAVEAT_TEX` as a LaTeX comment block
immediately before the two blocks that render the column, because the quantity
is volatile at a fixed solution (43x across restarts at unchanged cost),
incomparable across parameter blocks (three Coleman-Li scaling regimes), and
reliable only at large magnitudes. Derivation:
`.planning/probes/2026-08-17-optimality-decomposition/FINDINGS.md`.

Emits `benchmark_grid.csv` and `benchmark_grid.tex` into `--out`. The tenth
row -- the real 13-camera rig -- is never run here: it is E2's own
pipeline-written `experiments/results/benchmark.json` (`E2_BENCHMARK_PATH`),
read and folded in as a `record_source="pipeline"` row, rendered in its own
labeled LaTeX block rather than as a tenth point on the nine-cell synthetic
scaling curve (D-02).

**You AUTHOR the grid; you do NOT run it here.** The nine-cell production
execution is a separate plan. The only multi-cell execution this module
performs under test/CI is `--smoke`, over `SMOKE_CELLS` -- two trivial,
non-declared cells that still exercise the full subprocess hop.
"""

from __future__ import annotations

import argparse
import json
import logging
import subprocess
import sys
import tempfile
import time
from collections.abc import Mapping, Sequence
from pathlib import Path

import numpy as np
import pandas as pd
from numpy.typing import NDArray

from aquacal.calibration._observability import SolverDiagnostics
from aquacal.config.schema import BoardConfig
from aquacal.core.board import BoardGeometry
from aquacal.datasets.pipelines import calibrate_synthetic
from aquacal.datasets.synthetic import (
    SyntheticScenario,
    board_clearance_floor,
    generate_board_trajectory,
    generate_camera_array,
    generate_synthetic_detections,
)
from aquacal.validation.evaluation import evaluate_calibration
from experiments._io import (
    build_experiment_arg_parser,
    compare_experiment_csv,
    exit_code_for,
    resolve_out_dir,
    validate_args,
    write_direct_call_benchmark,
    write_experiment_csv,
)
from experiments._render import aggregate, write_latex_fragment

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Declared grid (D-01, D-03, D-04)
# ---------------------------------------------------------------------------

CAMERA_COUNTS = [8, 12, 16]
FRAME_COUNTS = [50, 100, 200]
DECLARED_CELLS: list[tuple[int, int]] = [
    (n_cameras, n_frames) for n_cameras in CAMERA_COUNTS for n_frames in FRAME_COUNTS
]

# COV-06 (plan 19.5-08): the repeat subset for E4's runtime spread. Exactly
# the three 100-frame cells, for two reasons, both load-bearing (see the
# plan's design_decision section):
# 1. These are exactly the cells MF-03's runtime-inversion finding rests on
#    (E4's runtime INVERTS with camera count at n_frames=200), so a repeat
#    here tests the claim that is actually made.
# 2. The 200-frame cells are the near_physical_ceiling ones (11.3 GiB peak on
#    a 15.7 GiB box, 72% of RAM) -- repeating those risks an OOM that would
#    abort the whole overnight queue for a number nobody is quoting.
REPEAT_CELLS: list[tuple[int, int]] = [(8, 100), (12, 100), (16, 100)]

GRID_NOISE_STD = 0.5
GRID_LAYOUT = "grid"
GRID_N_WATER = 1.333

# The pipeline default (schema.py's interface_normal_fixed=False). optimize_
# interface and joint_refinement both default normal_fixed=True, so this MUST
# be passed explicitly at every calibrate_synthetic call site -- omitting it
# silently solves a problem two tilt DOF smaller than the one E2 and
# tab:cpr describe (review H1). E6 imports this constant so its baseline is
# genuinely E4's 12-camera cell, not a lookalike.
GRID_NORMAL_FIXED = False

# The production configuration -- declared as a constant so it can be
# recorded in solver_config and the CSV rather than being an unstated
# assumption (review L6).
GRID_SHARED_INTERFACE = True

# datasets/pipelines.py branches on scenario.name != "calibration" to choose
# initial_water_zs between ground truth and a flat 1.0 (review L1) -- this
# value must never be "calibration". build_grid_scenario raises ValueError if
# a caller passes that reserved name.
GRID_SCENARIO_NAME = "grid_benchmark"

# Mirrors the board the synthetic-scenario presets build inline (synthetic.py's
# default_board); declared here so E6 imports this constant rather than
# declaring a third copy.
GRID_BOARD_CONFIG = BoardConfig(
    squares_x=12,
    squares_y=9,
    square_size=0.060,
    marker_size=0.045,
    dictionary="DICT_5X5_100",
)

CHECK_RTOL = 1e-6

# D-07/D-08: --check's named exclusion list, declared here (not in
# experiments/_io.py, which owns the shared MECHANISM only -- see
# compare_experiment_csv's exclude_columns docstring) because putting the
# list in the shared module would silently grant the exemption to every
# experiment's --check, including ones nobody has audited for always-red
# columns. Measured 2026-08-17 (.planning/probes/2026-08-17-phase-23-recon/
# e4_check_detail.py, 35 columns x 10 rows): all 33 OTHER columns reproduce
# to 1e-6 on the committed tree; only these two fail, and can never pass:
#
# - "exit_code": _run_check hardcodes "exit_code": None (no subprocess runs
#   under --check) while the committed CSV holds 0.0 from the real run that
#   produced it. Synthesizing "exit_code: 0" from the committed record was
#   considered and rejected -- it fabricates a field in a provenance
#   artifact (D-07).
# - "status_reason": an empty-string-versus-NaN round-trip through CSV.
#
# A third entry here is a deliberate decision requiring the same
# measurement-backed justification, not a silent inheritance (D-07: a named
# list beats a heuristic).
CHECK_EXCLUDED_COLUMNS: tuple[str, ...] = ("exit_code", "status_reason")

# The exit code run_grid_cell's --cell child returns when
# write_direct_call_benchmark skipped an existing file (force=False). Lets
# run_cell_subprocess map a skip onto status="skipped_existing" without
# parsing stdout (review H2, H3).
SKIPPED_EXIT_CODE = 3


def _fail_fast_abort_message(key: str, detail: str) -> str:
    """Format the D-19.4-11 fail-fast abort message.

    `detail` is the failure's own `status_reason` (or, in the direct
    `--cell` path, `f"{type(exc).__name__}: {exc}"`) -- both already carry
    the exception type and message verbatim, and for a clearance-floor
    rejection both the supplied minimum and the derived floor, since
    `generate_board_trajectory`'s own `ValueError` message already includes
    both numbers (D-19.3-01). Nothing here recomposes those numbers.
    """
    return (
        f"FAIL-FAST ABORT (D-19.4-11): {key} failed: {detail}\n"
        'Pass --no-fail-fast to record this as a status="failed" row and '
        "continue instead (19.2-21's pre-authorised use case)."
    )


# Two trivial, non-declared cells (3 cameras, 3-4 frames) that --smoke runs
# through the SAME subprocess hop as the real grid, so CI proves the parent/
# child contract works end to end rather than only the in-process path.
# --cell's own validation accepts DECLARED_CELLS *and* SMOKE_CELLS -- a fixed
# enumerated set, never an arbitrary pair -- which is why extending it here
# is not "loosening" --cell's validation (an undeclared, non-smoke pair like
# 7x13 is still rejected).
SMOKE_CELLS: list[tuple[int, int]] = [(3, 3), (3, 4)]
_ALLOWED_CELL_VALUES = frozenset(DECLARED_CELLS) | frozenset(SMOKE_CELLS)

# E2's real-rig tenth row: never run here, only read (D-02). Anchored to
# __file__ (never the process's cwd) the way E3's _E2_BENCHMARK_JSON_PATH is
# (e3_derived_quantities.py:153-155, CR-03) -- a cwd-relative path silently
# resolves to nothing when this module is invoked from any directory other
# than the repository root.
E2_BENCHMARK_PATH = (
    Path(__file__).resolve().parents[1] / "experiments" / "results" / "benchmark.json"
)


def resolve_e2_benchmark_path(out_dir: Path) -> tuple[Path | None, str]:
    """Resolve E2's real-rig `benchmark.json` relative to the active `--out`.

    FIX-05 (D-09): the module-level `E2_BENCHMARK_PATH` constant describes
    only the DEFAULT output tree. Passing it directly to `build_grid_dataframe`
    at every caller, regardless of `out_dir`, means a non-default `--out`
    either silently drops the real-rig row or -- worse -- pairs one machine's
    synthetic cells with another machine's real-rig row imported from the
    repo tree. This resolver is the single source of truth both
    `build_grid_dataframe` callers (`_run_check`, `_run_full`) must use.

    Three branches, in order:

    1. `out_dir/benchmark.json` exists: the native case -- E2 wrote its
       record into the same tree this grid run is writing into. Use it.
    2. `out_dir` resolves to the same directory as `E2_BENCHMARK_PATH`'s
       parent (i.e. the default tree): use the `__file__`-anchored constant.
       Kept as an explicit branch, even though it is path-equal to branch 1
       for the default directory, because it is what preserves the
       deliberate `__file__` anchoring documented on `E2_BENCHMARK_PATH` --
       a cwd-relative path silently resolves to nothing when the module is
       invoked from anywhere but the repo root.
    3. Otherwise: no native record exists under a non-default `--out`.
       Return `None` rather than falling back to the repo tree's record,
       which describes a different machine's run. **Never fall back across
       machines.**

    Args:
        out_dir: The active `--out` directory (already resolved by
            `resolve_out_dir`).

    Returns:
        A `(path_or_None, provenance_note)` tuple. `path_or_None` is `None`
        exactly when branch 3 applies; `provenance_note` is a human-readable
        string suitable for logging that names which branch was taken.
    """
    out_dir = Path(out_dir)
    candidate = out_dir / "benchmark.json"
    if candidate.exists():
        return candidate, "native: resolved relative to --out"
    if out_dir.resolve() == E2_BENCHMARK_PATH.parent:
        return E2_BENCHMARK_PATH, "default tree: __file__-anchored E2_BENCHMARK_PATH"
    return (
        None,
        f"absent: no benchmark.json under {out_dir} and --out is not the default "
        f"tree; refusing to import {E2_BENCHMARK_PATH}, which describes a "
        "different machine's run",
    )


# ---------------------------------------------------------------------------
# D-29: grid-family optical geometry -- real-rig-like rather than the
# unrealistic 0.15 m / (0.3, 0.6) m / 0.1 m the underlying generators
# default to. Declared here as named constants (not passed inline) so a
# reader can see, in one place, what the grid family assumes and why.
# ---------------------------------------------------------------------------

# Matches generate_real_rig_array's WATER_Z (1.031 m) so the grid family's
# cameras sit at a REPRESENTATIVE height above water, rather than the
# unrealistic 0.15 m the underlying generator otherwise defaults to
# (19.2-GAP-CONTEXT.md D-29).
#
# Reworded 2026-07-31. This previously said "the same height above water the
# real rig does", and that is no longer true: the real rig's interface
# re-measures at 1.0738 m. WATER_Z is now a frozen design constant rather than
# a calibrated value -- see its provenance note in datasets/synthetic.py. The
# coupling asserted here is to that constant, NOT to whatever the current
# calibration reports, and the two are not expected to agree. The synthetic
# grid approximates the real rig; it does not reproduce it.
#
# Keep this in step with WATER_Z if that ever changes -- but note that doing so
# invalidates the committed nine-cell grid, so neither is a cheap edit.
GRID_HEIGHT_ABOVE_WATER = 1.031

# Sized so a 12-camera "grid" array (side = ceil(sqrt(12)) = 4, so a 4x3
# layout) spans (side - 1) * GRID_SPACING = 3 * 0.43 =~ 1.29 m in X --
# matching generate_real_rig_array's measured ~1.3 m x 1.2 m footprint
# (D-29; 19.2-GAP-CONTEXT.md's verified proposal table). GRID_BOARD_CONFIG
# is deliberately NOT scaled alongside this constant -- a real calibration
# target does not shrink with the tank (see build_grid_scenario's own
# docstring, which states this same rationale).
GRID_SPACING = 0.43

# DERIVED, not restated (D-19.3-01): the minimum is `board_clearance_floor`
# applied to GRID_BOARD_CONFIG, the grid family's own water_zs (the deepest
# per-camera interface at GRID_HEIGHT_ABOVE_WATER/GRID_SPACING, i.e. the same
# inputs build_grid_scenario itself constructs from), and the 15-degree tilt
# `generate_board_trajectory` samples by default. The maximum stays a fixed
# 2.0 m ceiling (D-19.3-03) -- only the minimum is derived. This value MOVES
# if GRID_BOARD_CONFIG, GRID_HEIGHT_ABOVE_WATER, or GRID_SPACING change --
# that is the entire point of deriving rather than hardcoding it: it cannot
# silently go stale the way the old literal `(1.1, 2.0)` did the moment the
# board or tilt range changed underneath it.
#
# The anchor is the E6 baseline's own 12-camera array (D-11) built with
# GRID_HEIGHT_ABOVE_WATER/GRID_SPACING -- the same construction path
# build_grid_scenario itself uses -- so the derived floor cannot drift from
# what the actual grid cells build. The seed used here only affects the
# per-camera height_variation draw (+/- a few mm around GRID_HEIGHT_ABOVE_
# WATER); it does not affect any scenario's own RNG stream.
_GRID_BASELINE_N_CAMERAS = 12
_, _grid_baseline_extrinsics, _grid_baseline_water_zs = generate_camera_array(
    n_cameras=_GRID_BASELINE_N_CAMERAS,
    layout=GRID_LAYOUT,
    spacing=GRID_SPACING,
    height_above_water=GRID_HEIGHT_ABOVE_WATER,
    seed=42,
)


# D-19.4-12: kept as a water_zs-parameterized helper (demoted to hygiene, not
# thesis -- post-fix `max(water_zs) == height_above_water` at every seed
# (D-19.4-15), so a module constant would already be correct; deriving
# per-scenario stays right if a caller ever passes a different
# `height_above_water`, and costs nothing). Mirrors
# `experiments/e5_index_sensitivity.py`'s `_e5_real_rig_depth_range` --
# takes `water_zs` as a parameter rather than rebuilding a camera array
# internally.
#
# Placement note (deviation from D-19.4-12's literal "beside
# `default_xy_extent_for_layout`"): this helper is referenced at IMPORT TIME
# by the `GRID_DEPTH_RANGE` assignment immediately below, which itself must
# stay above `default_xy_extent_for_layout` in the file (declared-grid
# constants precede the scene-builder section). Defining the helper here,
# immediately before its only call site, keeps `GRID_DEPTH_RANGE`
# derivable without a forward reference; `default_xy_extent_for_layout`
# carries a comment naming this function as its sibling instead.
def derive_grid_depth_range(
    water_zs: Mapping[str, float],
    board: BoardConfig = GRID_BOARD_CONFIG,
    rotation_range_deg: float = 15.0,
) -> tuple[float, float]:
    """Derive the grid family's `depth_range` from a camera array's `water_zs`.

    D-19.4-12/D-19.4-15: post-fix, every camera in a `generate_camera_array`
    array shares one flat interface, so `max(water_zs.values()) ==
    height_above_water` exactly, at every seed and every camera count --
    the derived floor is therefore seed-invariant BY CONSTRUCTION, not by
    accident. Measured over 3,000 draws (500 seeds x {8,12,16} cameras x
    calibration and holdout): exactly one distinct derived floor,
    1.176215948246 (a drop of ~5.6 mm from the pre-fix constant, which was
    anchored on cam7's seed-42 jitter -- the deepest per-camera water
    surface under the old per-camera-interface defect).

    Kept as a function, not inlined as a frozen constant, so it stays
    correct if a caller passes a `water_zs` built at a different
    `height_above_water` (the helper derives; it does not memoize a single
    scenario's answer).

    Args:
        water_zs: Per-camera interface distances, e.g. a `generate_camera_
            array` baseline's third return value. NOT rebuilt internally --
            the caller owns scenario construction.
        board: ChArUco board specification forwarded to
            `board_clearance_floor`. Defaults to `GRID_BOARD_CONFIG`.
        rotation_range_deg: Tilt range forwarded to `board_clearance_floor`.
            Defaults to 15.0, matching `generate_board_trajectory`'s own
            default.

    Returns:
        `(derived_floor, 2.0)` -- the minimum is derived via
        `board_clearance_floor`; the maximum stays a fixed 2.0 m ceiling
        (D-19.3-03).
    """
    return (
        board_clearance_floor(board, water_zs, rotation_range_deg),
        2.0,
    )


GRID_DEPTH_RANGE = derive_grid_depth_range(_grid_baseline_water_zs)

# D-28: xy_extent scales with the array's OWN footprint span rather than a
# fixed 0.15 m, so every layout (grid/ring/line) exercises the same
# FRACTION of its own footprint instead of a fraction that differs per
# layout (today's 0.75x down to 0.14x, the root cause of D-27's confounded
# E6 layout axis). generate_real_rig_trajectory's own XY_EXTENT (0.7 m)
# against generate_real_rig_array's ~1.3 m footprint is ~=0.54x the span --
# the ratio this constant reproduces.
GRID_XY_EXTENT_RATIO = 0.54

# Floor so a small/tightly-spaced array still gets a usable working volume
# rather than a near-zero xy_extent.
GRID_XY_EXTENT_FLOOR = 0.05  # meters

# ---------------------------------------------------------------------------
# D-33: per-cell timeout and memory-pressure vocabulary. A cell too large
# for the machine is measured, not predicted -- see run_grid_cell.
# ---------------------------------------------------------------------------

# Per-cell subprocess timeout (D-33 gap 2). `None` means a cell runs to
# completion, however long that takes.
#
# This was 20 * 60, derived from the OLD unrealistic-geometry grid: it ran nine
# cells in ~27 minutes (~3 min/cell), and 20 minutes left "roughly 60% headroom
# over the worst projected healthy cell". Measurement on the D-29 geometry
# falsifies that premise -- healthy cells now take 4-16 minutes each (8x100 =
# 948 s, 16x100 = 955 s), so 8x100 already sits at 80% of the old bound, and
# scaling the measured 50->100 frame step (~2.3x per frame doubling) puts every
# n_frames=200 cell at 26-37 minutes. The bound would therefore have killed
# healthy cells and lost the entire 200-frame column a second time -- the same
# outcome the removed pre-flight memory guard produced, by a different route.
#
# A cell is still bounded by what it actually does rather than by a prediction:
# it runs in its own child process, so an OOM kills only that cell and is
# recorded as status="failed" with its exit code (D-04), and _classify_memory_
# pressure names a cell that completed under pressure. What is NOT bounded is a
# cell that pages indefinitely without dying; on an unattended run that is a
# real exposure, and the operator accepted it deliberately rather than restore a
# bound whose stated derivation no longer holds. If a future run must be bounded
# again, derive the value from measured per-cell times, not from the superseded
# ~3 min/cell figure above.
CELL_TIMEOUT_SECONDS = None

# Below the physical ceiling but still worth flagging: a cell that
# COMPLETED but whose observed peak approached the physical limit. This is
# purely informational (a measurement CONDITION, not a verdict -- D-12
# stands; no pass/fail column exists anywhere in this module's output).
MEMORY_NEAR_CEILING_FRACTION = 0.5

# memory_pressure vocabulary (D-33 gap 3) -- a fixed, small enumeration.
# NOT a pass/fail verdict column: it describes the CONDITION under which a
# measurement was taken, so a reader can distinguish a clean measurement
# from one taken close to the physical ceiling.
MEMORY_PRESSURE_CLEAN = "clean"
MEMORY_PRESSURE_NEAR_CEILING = "near_physical_ceiling"

GRID_KEY_COLUMNS = ["cell_key"]

# The settled Phase-18 stage vocabulary this module reports on.
_STAGE1 = "stage3_interface_optimization"
_STAGE2 = "stage3_intrinsic_pass"

# 36 columns, in order (D-02, D-04, D-14, D-15, D-16; review H1, H5, M3, L6;
# D-33 gap 3 adds memory_pressure; D-19.3-11/plan 19.3-07 appends
# degenerate_observations_at_solution last).
GRID_COLUMNS: list[str] = [
    "cell_key",
    "n_cameras",
    "n_frames",
    "seed",
    "status",
    "status_reason",
    "exit_code",
    "timing_scope",
    "record_source",
    "normal_fixed",
    "shared_interface",
    "n_observations",
    "memory_pressure",
    "seconds_stage3_interface_optimization",
    "seconds_stage3_intrinsic_pass",
    "peak_bytes_baseline",
    "peak_bytes_stage3_interface_optimization",
    "peak_bytes_stage3_intrinsic_pass",
    "memory_mode",
    "n_params_stage3_interface_optimization",
    "n_groups_stage3_interface_optimization",
    "fd_reduction_stage3_interface_optimization",
    "n_residuals_stage3_interface_optimization",
    "jacobian_elements_stage3_interface_optimization",
    "n_params_stage3_intrinsic_pass",
    "n_groups_stage3_intrinsic_pass",
    "fd_reduction_stage3_intrinsic_pass",
    "n_residuals_stage3_intrinsic_pass",
    "jacobian_elements_stage3_intrinsic_pass",
    "nfev_stage3_interface_optimization",
    "njev_stage3_interface_optimization",
    # D-17/DEGEN-05: a MEASUREMENT, never a converged/diverged verdict, and one
    # that must not be read as a like-for-like scalar. Measured 2026-08-17
    # (.planning/probes/2026-08-17-optimality-decomposition/FINDINGS.md): it is
    # VOLATILE at a fixed solution (92.78 -> 2.16 across restarts, 43x, at
    # unchanged cost -- the problem's directional curvature is ~3e8),
    # BLOCK-INCOMPARABLE (scipy trf reports max|g . v| and the Coleman-Li v runs
    # v = 1 unbounded extrinsics, v ~ 700 wide-bounded intrinsics, v ~ 2e-12
    # pinned water_z), and MAGNITUDE-DEPENDENT in reliability (92.78 is real to
    # 5 s.f.; 0.001146 against a 3-point reference of 0.001655 is not, so
    # differences between two SMALL values carry no information). The caveat
    # ships to the reader in benchmark_grid.tex as OPTIMALITY_CAVEAT_TEX --
    # keep the two in sync. Do NOT add a `#` comment line to the CSV instead
    # (it breaks pd.read_csv and --check), and do NOT co-opt the cell-status
    # reason column, which the status gate owns.
    "optimality_stage3_interface_optimization",
    "reprojection_rms",
    "validation_3d_error_mean",
    "validation_3d_error_std",
    # D-19.3-11/plan 19.3-07: the final-solution guard count this cell's
    # calibrate_synthetic call recorded via discard_stats_out. Appended last
    # so every existing column keeps its position. Populated whenever a
    # cell's metrics are populated (status in {"ok", "degenerate",
    # "skipped_existing" with an on-disk record}); null when no
    # benchmark.json was ever read for this cell.
    "degenerate_observations_at_solution",
]

# Metric columns (everything after status/status_reason/exit_code) that must
# be null whenever a row's status is not "ok" (D-04) -- also the fallback
# when a declared cell has no benchmark.json to read at all.
_NULL_METRICS: dict = {
    "seed": None,
    "timing_scope": "optimization_only",
    "record_source": "assembled",
    "normal_fixed": None,
    "shared_interface": None,
    "n_observations": None,
    "memory_pressure": None,
    "seconds_stage3_interface_optimization": None,
    "seconds_stage3_intrinsic_pass": None,
    "peak_bytes_baseline": None,
    "peak_bytes_stage3_interface_optimization": None,
    "peak_bytes_stage3_intrinsic_pass": None,
    "memory_mode": None,
    "n_params_stage3_interface_optimization": None,
    "n_groups_stage3_interface_optimization": None,
    "fd_reduction_stage3_interface_optimization": None,
    "n_residuals_stage3_interface_optimization": None,
    "jacobian_elements_stage3_interface_optimization": None,
    "n_params_stage3_intrinsic_pass": None,
    "n_groups_stage3_intrinsic_pass": None,
    "fd_reduction_stage3_intrinsic_pass": None,
    "n_residuals_stage3_intrinsic_pass": None,
    "jacobian_elements_stage3_intrinsic_pass": None,
    "nfev_stage3_interface_optimization": None,
    "njev_stage3_interface_optimization": None,
    "optimality_stage3_interface_optimization": None,
    "reprojection_rms": None,
    "validation_3d_error_mean": None,
    "validation_3d_error_std": None,
    "degenerate_observations_at_solution": None,
}

# Compact main-text summary view (WP2's placement plan: compact table in the
# main text, full grid in the supplement -- see write_grid_latex).
GRID_SUMMARY_COLUMNS = [
    "cell_key",
    "n_cameras",
    "n_frames",
    "seconds_stage3_interface_optimization",
    "seconds_stage3_intrinsic_pass",
    "peak_bytes_stage3_intrinsic_pass",
    "reprojection_rms",
]


# ---------------------------------------------------------------------------
# D-28: xy_extent scales with the array's own footprint span.
# ---------------------------------------------------------------------------


def _array_xy_span(camera_positions: dict[str, NDArray[np.float64]]) -> float:
    """The camera array's XY footprint span (D-28).

    Returns the Euclidean diagonal of the XY bounding box spanned by
    `camera_positions` -- a single representative number for a layout whose
    extent is asymmetric (e.g. `"line"`, whose Y range is zero) as well as
    one that is symmetric (`"ring"`).

    Args:
        camera_positions: Dict of camera center positions (from extrinsics).

    Returns:
        The XY bounding-box diagonal, in meters.
    """
    xs = np.array([float(p[0]) for p in camera_positions.values()])
    ys = np.array([float(p[1]) for p in camera_positions.values()])
    x_range = float(xs.max() - xs.min())
    y_range = float(ys.max() - ys.min())
    return float(np.hypot(x_range, y_range))


def _default_xy_extent(camera_positions: dict[str, NDArray[np.float64]]) -> float:
    """D-28's derived `xy_extent`: a fixed fraction of the array's own span.

    Args:
        camera_positions: Dict of camera center positions (from extrinsics).

    Returns:
        `GRID_XY_EXTENT_RATIO` of the array's span, floored at
        `GRID_XY_EXTENT_FLOOR` so a tiny array still gets a usable working
        volume.
    """
    span = _array_xy_span(camera_positions)
    return max(GRID_XY_EXTENT_RATIO * span, GRID_XY_EXTENT_FLOOR)


def default_xy_extent_for_layout(n_cameras: int, layout: str, spacing: float) -> float:
    """Convenience wrapper: D-28's derived `xy_extent` from
    `(n_cameras, layout, spacing)` alone, without building a full scenario.

    Used by E6 to derive its scale axis from E4's geometry constants rather
    than hardcoding a second copy (D-28). Camera XY positions do not depend
    on `seed` -- only per-camera roll and height jitter do
    (`generate_camera_array`) -- so any seed value yields the same span;
    `seed=0` is used here for clarity, not reproducibility. (D-19.4-09: the
    height jitter now lands on each camera's `C_z`, not on the shared
    `water_z`; XY positions were never affected by either jitter source, so
    the seed-independence claim itself is unchanged.)

    `derive_grid_depth_range` (below `GRID_DEPTH_RANGE`, D-19.4-12) is this
    function's sibling: both take a `generate_camera_array`-derived quantity
    and reduce it to a single scalar the grid family needs at import time.

    Args:
        n_cameras: Camera count for `generate_camera_array`.
        layout: `generate_camera_array`'s layout ("grid", "line", "ring").
        spacing: `generate_camera_array`'s spacing.

    Returns:
        The derived `xy_extent`, in meters.
    """
    _, extrinsics, _ = generate_camera_array(
        n_cameras=n_cameras, layout=layout, spacing=spacing, seed=0
    )
    camera_positions = {cam: ext.C for cam, ext in extrinsics.items()}
    return _default_xy_extent(camera_positions)


# ---------------------------------------------------------------------------
# Scene builder (D-01, D-03, amended D-03/D-11 -- E6's baseline)
# ---------------------------------------------------------------------------


def build_grid_scenario(
    n_cameras: int,
    n_frames: int,
    seed: int,
    *,
    layout: str = GRID_LAYOUT,
    depth_range: tuple[float, float] | None = None,
    xy_extent: float | None = None,
    spacing: float | None = None,
    height_above_water: float | None = None,
    n_water: float = GRID_N_WATER,
    name: str = GRID_SCENARIO_NAME,
) -> SyntheticScenario:
    """Build one grid-family synthetic scenario, E4's cell builder AND E6's baseline.

    Grid-family scenes come from `generate_camera_array` + `generate_board_
    trajectory` -- a DIFFERENT generator from the "realistic" preset's fixed
    real-rig array builder (a fixed 12-camera real-rig layout with no
    `n_cameras`/`layout` parameter). E4's 8/12/16-camera cells and E6's
    baseline (`build_grid_scenario(12, <baseline frames>, seed)`, D-11) are
    therefore identically constructed grid-family scenes; do not attempt to
    unify this generator with the "realistic" preset's fixed-rig builder.

    `layout`, `depth_range`, `xy_extent`, `spacing`, and `height_above_water`
    exist so E6 can vary exactly one axis at a time through this shared
    baseline (D-11) without duplicating scene-construction code a third time.
    `spacing`/`height_above_water` are E6's scale axis (review M2): the
    working volume (`depth_range`/`xy_extent`) and rig baseline (`spacing`/
    `height_above_water`) scale together at fixed board size -- the board's
    `square_size` is deliberately NOT scaled, since a real calibration target
    does not shrink with the tank.

    D-29: when not passed explicitly, `depth_range`, `spacing`, and
    `height_above_water` default to this module's `GRID_DEPTH_RANGE`,
    `GRID_SPACING`, and `GRID_HEIGHT_ABOVE_WATER` -- real-rig-like optical
    geometry -- rather than falling through to `generate_camera_array`'s and
    `generate_board_trajectory`'s own (unrealistic, 0.15 m / 0.1 m) defaults.
    D-28: when not passed explicitly, `xy_extent` defaults to
    `_default_xy_extent(camera_positions)`, a fixed fraction
    (`GRID_XY_EXTENT_RATIO`) of THIS scenario's own array span, rather than a
    fixed 0.15 m -- so every layout exercises the same fraction of its own
    footprint. `center` is deliberately never passed here: D-27's centroid
    default (in `generate_board_trajectory`) already centers the working
    volume on this scenario's own array, computed from the SAME
    `camera_positions` this function builds below.

    Args:
        n_cameras: Camera count for `generate_camera_array`.
        n_frames: Frame count for `generate_board_trajectory`.
        seed: Shared seed for both the camera array and the trajectory.
        layout: `generate_camera_array`'s layout ("grid", "line", "ring").
        depth_range: Forwarded to `generate_board_trajectory` when given;
            otherwise defaults to `GRID_DEPTH_RANGE` (D-29).
        xy_extent: Forwarded to `generate_board_trajectory` when given;
            otherwise defaults to `_default_xy_extent(camera_positions)`
            (D-28).
        spacing: Forwarded to `generate_camera_array` when given; otherwise
            defaults to `GRID_SPACING` (D-29).
        height_above_water: Forwarded to `generate_camera_array` when given;
            otherwise defaults to `GRID_HEIGHT_ABOVE_WATER` (D-29).
        n_water: Assumed AND true refractive index recorded on the returned
            scenario (E4 does not sweep index; that is E5/E6's axis).
        name: Scenario name recorded on the returned `SyntheticScenario`.
            MUST NOT be `"calibration"` -- `datasets/pipelines.py` branches
            on `scenario.name != "calibration"` to choose `initial_water_zs`
            between ground truth and a flat 1.0 (review L1); passing the
            reserved name here would silently change Stage-3 initialization
            for every grid cell.

    Returns:
        A `SyntheticScenario` built from the grid-family generators.

    Raises:
        ValueError: If `name == "calibration"`.
    """
    if name == "calibration":
        raise ValueError(
            "build_grid_scenario(name='calibration') is reserved: "
            "datasets/pipelines.py branches on scenario.name != 'calibration' "
            "to choose initial_water_zs between ground truth and a flat 1.0 "
            "(review L1) -- passing this name would silently change every "
            "grid cell's Stage-3 initialization."
        )

    resolved_spacing = GRID_SPACING if spacing is None else spacing
    resolved_height_above_water = (
        GRID_HEIGHT_ABOVE_WATER if height_above_water is None else height_above_water
    )
    intrinsics, extrinsics, water_zs = generate_camera_array(
        n_cameras=n_cameras,
        layout=layout,
        seed=seed,
        spacing=resolved_spacing,
        height_above_water=resolved_height_above_water,
    )

    camera_positions = {cam: ext.C for cam, ext in extrinsics.items()}
    resolved_depth_range = GRID_DEPTH_RANGE if depth_range is None else depth_range
    resolved_xy_extent = (
        _default_xy_extent(camera_positions) if xy_extent is None else xy_extent
    )
    board_poses = generate_board_trajectory(
        n_frames=n_frames,
        camera_positions=camera_positions,
        water_zs=water_zs,
        board=GRID_BOARD_CONFIG,
        depth_range=resolved_depth_range,
        xy_extent=resolved_xy_extent,
        seed=seed,
    )

    return SyntheticScenario(
        name=name,
        board_config=GRID_BOARD_CONFIG,
        intrinsics=intrinsics,
        extrinsics=extrinsics,
        water_zs=water_zs,
        board_poses=board_poses,
        noise_std=GRID_NOISE_STD,
        description=f"Grid-family benchmark scene: {n_cameras} cameras, {n_frames} frames",
        n_air=1.0,
        n_water=n_water,
        seed=seed,
    )


# ---------------------------------------------------------------------------
# D-33 gap 3: post-hoc memory-pressure classification
# ---------------------------------------------------------------------------


def _classify_memory_pressure(memory: dict) -> str:
    """Classify a completed cell's peak-memory readings as a measurement
    condition (D-33 gap 3) -- NOT a verdict (D-12 stands; no pass/fail
    column exists anywhere in this module's output).

    Compares the worst commit/peak figure across every boundary reading
    (Task 1's additive `commit_peak_bytes`, falling back to `peak_bytes`
    when commit figures are unavailable) against `ram_total_bytes` from the
    same readings. Degrades to `MEMORY_PRESSURE_CLEAN` when no reading
    carries a usable `ram_total_bytes` (e.g. off Windows) -- absence of the
    measurement is not evidence of pressure.

    Args:
        memory: The `memory_out` dict `calibrate_synthetic` populated,
            keyed by boundary name, each value a `capture_peak_memory()`
            reading.

    Returns:
        One of `MEMORY_PRESSURE_CLEAN` or `MEMORY_PRESSURE_NEAR_CEILING`.
    """
    readings = [r for r in memory.values() if isinstance(r, dict)]
    if not readings:
        return MEMORY_PRESSURE_CLEAN

    ram_total_bytes = next(
        (r["ram_total_bytes"] for r in readings if r.get("ram_total_bytes")),
        None,
    )
    if ram_total_bytes is None:
        return MEMORY_PRESSURE_CLEAN

    worst_peak = max(
        (r.get("commit_peak_bytes") or r.get("peak_bytes") or 0) for r in readings
    )
    if worst_peak >= MEMORY_NEAR_CEILING_FRACTION * ram_total_bytes:
        return MEMORY_PRESSURE_NEAR_CEILING
    return MEMORY_PRESSURE_CLEAN


# ---------------------------------------------------------------------------
# Per-cell runner (D-01, D-04, D-14; review H1, H2, H3, H5, M3)
# ---------------------------------------------------------------------------


def run_grid_cell(
    n_cameras: int,
    n_frames: int,
    seed: int,
    out_dir: Path,
    force: bool,
    fail_fast: bool = False,
) -> dict:
    """Run exactly one grid cell to completion and record its outcome.

    Runs the full direct-call path (`build_grid_scenario` ->
    `calibrate_synthetic` -> measured held-out accuracy ->
    `write_direct_call_benchmark`) for one `(n_cameras, n_frames)` cell,
    writing `out_dir/e4_cells/cameras_<n>_frames_<m>/benchmark.json`. Runs
    EXACTLY ONE cell and never loops -- it is invoked from a child process,
    one per cell (`run_cell_subprocess`), which is what makes the memory
    columns a genuine single-run peak and the OOM path reachable (review H2,
    H3): `capture_peak_memory()` is a process-lifetime high-water mark, so
    looping cells in one process would make cell 2's baseline already carry
    cell 1's peak.

    Never raises: any exception during the cell's own work (including a
    disconnected pose graph on a wide-baseline cell, an EXPECTED failure mode
    since `generate_board_trajectory` makes no per-frame camera-visibility
    guarantee -- it has no camera model and performs no projection) is caught and recorded as `status="failed"`
    with a populated `status_reason` (D-04) -- a status=failed row is the
    correct recorded outcome; a missing row is not.

    Args:
        n_cameras: Camera count for this cell.
        n_frames: Frame count for this cell.
        seed: Seed forwarded to scenario/detection generation and stamped
            into the written record's `solver_config["seed"]` (review H5).
        out_dir: Root output directory; the cell writes under
            `out_dir/e4_cells/cameras_<n_cameras>_frames_<n_frames>/`.
        force: Overwrite an existing `benchmark.json` for this cell instead
            of skipping (resumability, D-24).
        fail_fast: D-19.4-11. When `True`, an exception raised during the
            cell's own work is RE-RAISED after being logged, instead of
            being swallowed into a `status="failed"` dict -- so the CHILD
            process this function runs inside (via `--cell`) genuinely
            exits non-zero. Default `False` preserves this function's
            original never-raises contract for direct callers (unit tests,
            `--no-fail-fast`).

    Returns:
        A dict with at least `cell_key`, `n_cameras`, `n_frames`, `status`
        (`"ok"`, `"failed"`, or `"skipped_existing"` -- this function's own
        vocabulary; it never returns `"degenerate"` itself), and
        `status_reason`. A non-zero
        `discard_stats["degenerate_observations_at_solution"]` is still
        recorded into the written `benchmark.json`'s `problem_shape` and
        still logged as a warning here (D-19.3-11) -- the `ok` ->
        `degenerate` downgrade is applied downstream, in
        `build_grid_dataframe`, which is the sole gating site (see the
        module docstring).
    """
    cell_key = f"cameras_{n_cameras}_frames_{n_frames}"
    cell_path = Path(out_dir) / "e4_cells" / cell_key / "benchmark.json"

    if cell_path.exists() and not force:
        logger.info(
            "Skipping cell %s: %s already exists (resumability).", cell_key, cell_path
        )
        return {
            "cell_key": cell_key,
            "n_cameras": n_cameras,
            "n_frames": n_frames,
            "status": "skipped_existing",
            "status_reason": "",
        }

    # No pre-flight memory refusal. The projection this once used assumed
    # every camera saw all MAX_CORNERS_PER_VIEW corners in every frame, which
    # over-estimated residuals by ~3.76x against measurement (16x100: projected
    # 281,600, actual 74,810) and refused three cells -- the whole n_frames=200
    # column -- that measurement says fit comfortably. Calibrating that
    # assumption against an observed visibility fraction was rejected: every
    # rig's visibility differs, so a constant fitted to this one would be a
    # hidden hardware assumption in a library that must stay rig-agnostic.
    #
    # The failure modes it guarded are already covered downstream, by
    # measurement rather than projection: a true OOM kills only this cell's
    # child process and is recorded as status="failed" with its exit code
    # (D-04); a thrashing cell is bounded by the per-cell timeout; and a cell
    # that completed under memory pressure is named by _classify_memory_pressure
    # from its own readings. A cell that cannot fit now reports THAT it did not
    # fit, instead of a projection asserting it would not have.
    try:
        scenario = build_grid_scenario(n_cameras, n_frames, seed)
        board = BoardGeometry(GRID_BOARD_CONFIG)

        diag_stage3 = SolverDiagnostics()
        diag_intrinsic_pass = SolverDiagnostics()
        timings: dict[str, float] = {}
        memory: dict[str, dict] = {}

        discard_stats: dict[str, int] = {}
        result, detections = calibrate_synthetic(
            scenario,
            n_water=GRID_N_WATER,
            refine_intrinsics=True,
            seed=seed,
            diagnostics_out={
                "stage3_interface_optimization": diag_stage3,
                "stage3_intrinsic_pass": diag_intrinsic_pass,
            },
            timings_out=timings,
            memory_out=memory,
            normal_fixed=GRID_NORMAL_FIXED,
            discard_stats_out=discard_stats,
        )
        n_degenerate = discard_stats.get("degenerate_observations_at_solution", 0)
        if n_degenerate > 0:
            # D-19.3-11: recorded and warned about unconditionally, whether
            # this is a declared production cell or one of SMOKE_CELLS --
            # the GATE (ok -> degenerate) is applied downstream in
            # build_grid_dataframe, which only declared production cells
            # ever reach (SMOKE_CELLS never call it, see _run_smoke_cells),
            # so --smoke can never see a false failure from this count.
            #
            # GATE SCOPE (D-04, phase 25): this gate is SYNTHETIC-ONLY and does
            # not extend to real-rig runs. E4's geometry is *authored*, so an
            # unprojectable observation means the scenario was malformed and the
            # cell must fail; a physical rig's geometry is *given*, so a small
            # unprojectable fraction is a fact about the deployment rather than a
            # library defect. That was settled on MECHANISM -- which failure kind
            # dominates -- not on a count, because the real rig's published count
            # is a sum accumulated across solver stages. The tripwire that
            # re-opens it is a materially populated camera_model_failure bucket
            # (NAN_REASON_BEHIND_CAMERA with a positive h_q) in Phase 29's frozen
            # table. Long form: the "Gate scope" block in
            # src/aquacal/calibration/_observability.py; evidence (PROVISIONAL,
            # D-02): .planning/probes/2026-08-17-degeneracy-classification/.
            # None of that loosens the predicate here -- see D-05.
            logger.warning(
                "Cell %s recorded %d degenerate observation(s) at the final "
                "solution -- first-order optimality is unreliable for this "
                "cell (D-19.3-11).",
                cell_key,
                n_degenerate,
            )

        per_frame_counts = [len(fd.detections) for fd in detections.frames.values()]
        n_observations = sum(per_frame_counts)
        n_cameras_observing_min = min(per_frame_counts) if per_frame_counts else 0
        n_cameras_observing_median = (
            float(np.median(per_frame_counts)) if per_frame_counts else 0.0
        )

        # Separate held-out set at a different seed (never the calibration
        # detections) -- calibrate_synthetic hardcodes
        # DiagnosticsData.validation_3d_error_mean/_std to 0.0, so reading
        # those hardcoded fields off the CalibrationResult's own diagnostics
        # here would publish two fabricated zeros (review D-14 amendment).
        #
        # Built from a SECOND call to build_grid_scenario (mirroring E6's
        # own holdout pattern) rather than a bare generate_board_trajectory
        # call: after D-29, the latter would inherit generate_board_
        # trajectory's OWN defaults, scoring every cell's accuracy against a
        # working volume the calibration never saw -- a silent, plausible,
        # wrong number. Only the second scenario's board_poses are used,
        # paired with the FIRST scenario's own camera geometry below, so
        # held-out accuracy is scored against the same rig the calibration
        # solved for.
        holdout_seed = seed + 1_000_000
        holdout_scenario = build_grid_scenario(n_cameras, n_frames, holdout_seed)
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

        accuracy = {
            "reprojection_rms": evaluation.reprojection.rms,
            "validation_3d_error_mean": (
                evaluation.reconstruction.signed_mean
                if evaluation.reconstruction is not None
                else None
            ),
            "validation_3d_error_std": (
                evaluation.reconstruction.std
                if evaluation.reconstruction is not None
                else None
            ),
        }

        problem_shape = {
            "n_cameras": n_cameras,
            "n_frames": n_frames,
            "n_observations": n_observations,
            "n_cameras_observing_per_frame_min": n_cameras_observing_min,
            "n_cameras_observing_per_frame_median": n_cameras_observing_median,
            # The baseline peak-memory reading has no stage of its own in the
            # settled Phase-18 vocabulary, so assemble_benchmark_record()
            # (io/benchmark.py) discards it after using it to compute the
            # first real stage's delta. problem_shape is a free-form
            # passthrough dict, so stashing it here is how it survives into
            # the committed record for the peak_bytes_baseline column.
            "peak_bytes_baseline": memory.get("_baseline", {}).get("peak_bytes"),
            # D-33 gap 3: a measurement CONDITION, not a verdict (D-12
            # stands) -- lets a reader tell a clean measurement from one
            # taken close to the physical ceiling.
            "memory_pressure": _classify_memory_pressure(memory),
            # D-19.3-11/plan 19.3-07: the final-solution guard count,
            # stashed the same way peak_bytes_baseline is above -- problem_
            # shape is a free-form passthrough dict, so this is how the
            # count survives into the committed record and, via aggregate(),
            # becomes the `problem_shape.degenerate_observations_at_solution`
            # column build_grid_dataframe reads to decide status.
            "degenerate_observations_at_solution": n_degenerate,
        }
        solver_config = {
            "normal_fixed": GRID_NORMAL_FIXED,
            "shared_interface": GRID_SHARED_INTERFACE,
            "refine_intrinsics": True,
            "n_air": scenario.n_air,
            "n_water": GRID_N_WATER,
        }
        diagnostics = {
            "stage3_interface_optimization": diag_stage3,
            "stage3_intrinsic_pass": diag_intrinsic_pass,
        }

        write_direct_call_benchmark(
            cell_path,
            problem_shape=problem_shape,
            timings=timings,
            diagnostics=diagnostics,
            solver_config=solver_config,
            accuracy=accuracy,
            memory_readings=memory,
            seed=seed,
            force=force,
        )

        return {
            "cell_key": cell_key,
            "n_cameras": n_cameras,
            "n_frames": n_frames,
            "status": "ok",
            "status_reason": "",
        }
    except Exception as exc:
        logger.warning("Cell %s failed: %s: %s", cell_key, type(exc).__name__, exc)
        if fail_fast:
            # D-19.4-11: re-raise so the child process this function runs
            # inside (via --cell) exits non-zero instead of swallowing the
            # exception into a status="failed" dict the child then exits 0
            # on.
            raise
        return {
            "cell_key": cell_key,
            "n_cameras": n_cameras,
            "n_frames": n_frames,
            "status": "failed",
            "status_reason": f"{type(exc).__name__}: {exc}",
        }


def _invoke_subprocess_with_status_mapping(
    cmd: list[str], timeout: float | None
) -> tuple[str, str, int | None, float]:
    """Run `cmd` and map its outcome onto E4's status vocabulary.

    Shared by `run_cell_subprocess` (production) and this module's own
    real-child tests (D-33 gap 1) -- factored out so a genuine child
    process (no `monkeypatch` of `subprocess.run`) can exercise exactly the
    same mapping logic the parent path runs in production.

    Never raises: a non-zero exit is data (D-04), and a `TimeoutExpired` is
    mapped onto `status="failed"` with a reason distinguishable from a
    non-zero exit (D-33 gap 2) -- the SAME never-raises contract a non-zero
    exit already has.

    Args:
        cmd: The full command to spawn via `subprocess.run`.
        timeout: Optional subprocess timeout in seconds. `None` means wait
            indefinitely (production call sites always pass
            `CELL_TIMEOUT_SECONDS`; only ad-hoc/manual invocations should
            ever pass `None`).

    Returns:
        `(status, status_reason, exit_code, elapsed_seconds)`. `status` is
        one of `"ok"`, `"skipped_existing"`, or `"failed"`. `exit_code` is
        `None` only on a timeout (there was no exit).
    """
    t0 = time.perf_counter()
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        elapsed = time.perf_counter() - t0
        status = "failed"
        status_reason = (
            f"child exceeded timeout={timeout}s (D-33 gap 2); the run may be "
            "thrashing rather than merely slow"
        )
        return status, status_reason, None, elapsed

    elapsed = time.perf_counter() - t0
    if proc.returncode == 0:
        status, status_reason = "ok", ""
    elif proc.returncode == SKIPPED_EXIT_CODE:
        status, status_reason = "skipped_existing", ""
    else:
        stderr_tail = (proc.stderr or "")[-400:]
        status = "failed"
        status_reason = f"child exit_code={proc.returncode}: {stderr_tail}"

    return status, status_reason, proc.returncode, elapsed


def run_cell_subprocess(
    n_cameras: int,
    n_frames: int,
    seed: int,
    out_dir: Path,
    force: bool,
    timeout: float | None = None,
    no_fail_fast: bool = False,
) -> dict:
    """Run one cell in a child process (parent side; review H2, H3).

    Spawns `python -u -m experiments.e4_benchmark_grid --cell <n>x<m> --out
    <out_dir> --seed <seed> [--force]` via `subprocess.run`, using
    `sys.executable` so the child interpreter matches the parent's
    environment exactly. A subprocess per cell is what makes
    `capture_peak_memory()`'s reading a genuine single-run high-water mark
    (its own docstring documents it as monotonic within one process) and
    turns an OS-level OOM kill into a recordable exit code instead of a
    death `except Exception` can never observe.

    Never raises on a non-zero child exit -- that is data (D-04), not an
    exception (`subprocess.run` is never called with `check=True`) -- and
    never raises on a timeout either (D-33 gap 2): see
    `_invoke_subprocess_with_status_mapping`, which does the actual mapping.

    Args:
        n_cameras: Camera count for this cell.
        n_frames: Frame count for this cell.
        seed: Seed forwarded to the child's `--seed`.
        out_dir: Root output directory forwarded to the child's `--out`.
        force: Forwarded to the child's `--force` flag when True.
        timeout: Optional subprocess timeout in seconds. Production call
            sites always pass `CELL_TIMEOUT_SECONDS` explicitly.
        no_fail_fast: D-19.4-11. Forwarded to the child's own `--no-fail-fast`
            flag when `True`, so a direct `--cell` invocation of the spawned
            child sees the same opt-out the parent was given.

    Returns:
        A dict with `cell_key`, `n_cameras`, `n_frames`, `status` (`"ok"`,
        `"skipped_existing"`, or `"failed"`), `status_reason`, and
        `exit_code` (the child's raw return code, including a negative
        signal code or an OS OOM-kill code, or `None` on a timeout).
    """
    cell_key = f"cameras_{n_cameras}_frames_{n_frames}"
    cmd = [
        sys.executable,
        "-u",
        "-m",
        "experiments.e4_benchmark_grid",
        "--cell",
        f"{n_cameras}x{n_frames}",
        "--out",
        str(out_dir),
        "--seed",
        str(seed),
    ]
    if force:
        cmd.append("--force")
    if no_fail_fast:
        cmd.append("--no-fail-fast")

    status, status_reason, exit_code, elapsed = _invoke_subprocess_with_status_mapping(
        cmd, timeout
    )

    logger.info(
        "cell %s: status=%s exit_code=%s elapsed=%.1fs",
        cell_key,
        status,
        exit_code,
        elapsed,
    )

    return {
        "cell_key": cell_key,
        "n_cameras": n_cameras,
        "n_frames": n_frames,
        "status": status,
        "status_reason": status_reason,
        "exit_code": exit_code,
    }


# ---------------------------------------------------------------------------
# Row extraction (D-02, D-14, D-15, D-16)
# ---------------------------------------------------------------------------


def _get(row: pd.Series, column: str):
    """Read one column from an `aggregate()` row, `None` if absent or NaN."""
    if column not in row.index:
        return None
    value = row[column]
    if pd.isna(value):
        return None
    return value


def _jacobian_elements(n_residuals, n_params):
    """`n_residuals * n_params` (D-15), `None` if either input is `None`."""
    if n_residuals is None or n_params is None:
        return None
    return n_residuals * n_params


def _extract_assembled_row(row: pd.Series) -> dict:
    """Build one synthetic cell's metric columns from an `aggregate()` row."""
    n_params_1 = _get(row, f"{_STAGE1}.n_params")
    n_residuals_1 = _get(row, f"{_STAGE1}.n_residuals")
    n_params_2 = _get(row, f"{_STAGE2}.n_params")
    n_residuals_2 = _get(row, f"{_STAGE2}.n_residuals")

    return {
        "seed": _get(row, "solver_config.seed"),
        "timing_scope": "optimization_only",
        "record_source": "assembled",
        "normal_fixed": _get(row, "solver_config.normal_fixed"),
        "shared_interface": _get(row, "solver_config.shared_interface"),
        "n_observations": _get(row, "problem_shape.n_observations"),
        "memory_pressure": _get(row, "problem_shape.memory_pressure"),
        "degenerate_observations_at_solution": _get(
            row, "problem_shape.degenerate_observations_at_solution"
        ),
        "seconds_stage3_interface_optimization": _get(row, f"{_STAGE1}.seconds"),
        "seconds_stage3_intrinsic_pass": _get(row, f"{_STAGE2}.seconds"),
        "peak_bytes_baseline": _get(row, "problem_shape.peak_bytes_baseline"),
        "peak_bytes_stage3_interface_optimization": _get(
            row, f"{_STAGE1}.memory.cumulative_peak_bytes_as_of_stage_end"
        ),
        "peak_bytes_stage3_intrinsic_pass": _get(
            row, f"{_STAGE2}.memory.cumulative_peak_bytes_as_of_stage_end"
        ),
        "memory_mode": _get(row, "memory.mode"),
        "n_params_stage3_interface_optimization": n_params_1,
        "n_groups_stage3_interface_optimization": _get(row, f"{_STAGE1}.n_groups"),
        "fd_reduction_stage3_interface_optimization": _get(
            row, f"{_STAGE1}.fd_reduction"
        ),
        "n_residuals_stage3_interface_optimization": n_residuals_1,
        "jacobian_elements_stage3_interface_optimization": _jacobian_elements(
            n_residuals_1, n_params_1
        ),
        "n_params_stage3_intrinsic_pass": n_params_2,
        "n_groups_stage3_intrinsic_pass": _get(row, f"{_STAGE2}.n_groups"),
        "fd_reduction_stage3_intrinsic_pass": _get(row, f"{_STAGE2}.fd_reduction"),
        "n_residuals_stage3_intrinsic_pass": n_residuals_2,
        "jacobian_elements_stage3_intrinsic_pass": _jacobian_elements(
            n_residuals_2, n_params_2
        ),
        "nfev_stage3_interface_optimization": _get(row, f"{_STAGE1}.nfev"),
        "njev_stage3_interface_optimization": _get(row, f"{_STAGE1}.njev"),
        "optimality_stage3_interface_optimization": _get(row, f"{_STAGE1}.optimality"),
        "reprojection_rms": _get(row, "accuracy.reprojection_rms"),
        "validation_3d_error_mean": _get(row, "accuracy.validation_3d_error_mean"),
        "validation_3d_error_std": _get(row, "accuracy.validation_3d_error_std"),
    }


def _get_nested(d: dict, *keys):
    """Read a nested key path from a raw (non-pandas) dict, `None` if absent."""
    current = d
    for key in keys:
        if not isinstance(current, dict) or key not in current:
            return None
        current = current[key]
    return current


def _extract_pipeline_row(record: dict) -> dict:
    """Build E2's tenth row's metric columns from its raw `benchmark.json` dict.

    Read directly (never through `aggregate()`, which would rglob every
    `benchmark.json` under `experiments/results/` -- including E1's and E7's
    -- rather than this one file). E2's `solver_config` uses the pipeline's
    own key `"interface_normal_fixed"` (not `"normal_fixed"`) and has no
    `"shared_interface"` key at all (D-26: a flagged follow-up, not this
    plan's scope) -- both map to `None` here rather than being invented.
    """
    stages = record.get("stages", {})
    stage1 = stages.get(_STAGE1, {})
    stage2 = stages.get(_STAGE2, {})
    n_params_1 = stage1.get("n_params")
    n_residuals_1 = stage1.get("n_residuals")
    n_params_2 = stage2.get("n_params")
    n_residuals_2 = stage2.get("n_residuals")
    solver_config = record.get("solver_config", {})
    accuracy = record.get("accuracy", {})
    memory = record.get("memory", {})
    # D-01: read the guard count out of E2's own record instead of nulling it.
    # `discard_stats` is the canonical site; `problem_shape` is the fallback.
    # Absent from both stays `None` -- an un-instrumented record must remain
    # distinguishable from a measured zero, which is the property gate 1 rests
    # on. (Rationale in full at the dict entry below.)
    degenerate_at_solution = _get_nested(
        record, "discard_stats", "degenerate_observations_at_solution"
    )
    if degenerate_at_solution is None:
        degenerate_at_solution = _get_nested(
            record, "problem_shape", "degenerate_observations_at_solution"
        )

    return {
        "seed": solver_config.get("seed"),
        "timing_scope": "end_to_end",
        "record_source": "pipeline",
        "normal_fixed": solver_config.get("interface_normal_fixed"),
        "shared_interface": solver_config.get("shared_interface"),
        "n_observations": None,
        # D-26: E2 never recorded a memory_pressure classification (its
        # benchmark.json predates D-33); None rather than invented (D-14).
        "memory_pressure": None,
        "degenerate_observations_at_solution": degenerate_at_solution,
        "seconds_stage3_interface_optimization": stage1.get("seconds"),
        "seconds_stage3_intrinsic_pass": stage2.get("seconds"),
        "peak_bytes_baseline": None,
        "peak_bytes_stage3_interface_optimization": _get_nested(
            stage1, "memory", "cumulative_peak_bytes_as_of_stage_end"
        ),
        "peak_bytes_stage3_intrinsic_pass": _get_nested(
            stage2, "memory", "cumulative_peak_bytes_as_of_stage_end"
        ),
        "memory_mode": memory.get("mode"),
        "n_params_stage3_interface_optimization": n_params_1,
        "n_groups_stage3_interface_optimization": stage1.get("n_groups"),
        "fd_reduction_stage3_interface_optimization": stage1.get("fd_reduction"),
        "n_residuals_stage3_interface_optimization": n_residuals_1,
        "jacobian_elements_stage3_interface_optimization": _jacobian_elements(
            n_residuals_1, n_params_1
        ),
        "n_params_stage3_intrinsic_pass": n_params_2,
        "n_groups_stage3_intrinsic_pass": stage2.get("n_groups"),
        "fd_reduction_stage3_intrinsic_pass": stage2.get("fd_reduction"),
        "n_residuals_stage3_intrinsic_pass": n_residuals_2,
        "jacobian_elements_stage3_intrinsic_pass": _jacobian_elements(
            n_residuals_2, n_params_2
        ),
        "nfev_stage3_interface_optimization": stage1.get("nfev"),
        "njev_stage3_interface_optimization": stage1.get("njev"),
        "optimality_stage3_interface_optimization": stage1.get("optimality"),
        "reprojection_rms": accuracy.get("reprojection_rms"),
        "validation_3d_error_mean": accuracy.get("validation_3d_error_mean"),
        "validation_3d_error_std": accuracy.get("validation_3d_error_std"),
    }


def build_grid_dataframe(
    out_dir: Path, cell_statuses: list[dict], e2_benchmark_path: Path | None
) -> pd.DataFrame:
    """Build the ten-row grid frame: nine declared cells plus E2's real-rig row.

    Calls `aggregate(out_dir / "e4_cells")` to flatten every cell's
    `benchmark.json` unmodified (no second aggregator, P1), then LEFT-JOINS
    that onto the literal `DECLARED_CELLS` list -- not onto the aggregate's
    own rows -- so a cell with no `benchmark.json` at all still produces a
    row (D-04). `cell_statuses` (as returned by `run_grid_cell`/
    `run_cell_subprocess`) supplies `status`/`status_reason`/`exit_code`;
    metric columns are forced to `None` for any row whose status is not
    `"ok"`, even if a stale `benchmark.json` happens to exist on disk.

    Args:
        out_dir: Root output directory; cells are read from
            `out_dir/e4_cells/`.
        cell_statuses: One dict per declared cell (as `run_grid_cell`/
            `run_cell_subprocess` return), each with `n_cameras`, `n_frames`,
            `status`, `status_reason`, and (optionally) `exit_code`.
        e2_benchmark_path: Path to E2's pipeline-written `benchmark.json`, or
            `None`. Callers should supply the output of the module's
            `resolve_e2_benchmark_path` resolver rather than a bare constant
            (FIX-05, D-09) -- `None` means no native record exists for this
            `out_dir` and the row is emitted absent-and-marked rather than
            imported from another tree.

    Returns:
        A `DataFrame` with exactly `GRID_COLUMNS`, in order: nine synthetic
        rows (`record_source="assembled"`) plus E2's tenth row
        (`record_source="pipeline"`).
    """
    cells_dir = Path(out_dir) / "e4_cells"
    try:
        agg = aggregate(cells_dir)
    except Exception as exc:
        # CR-03: aggregate() refuses loudly (e.g. UnsupportedSchemaVersionError)
        # on a record it does not recognize. By this point every declared cell
        # may already have solved -- losing the whole run's CSV and LaTeX here
        # is the failure mode, whatever record triggered it (D-04: a row per
        # declared cell, never an aborted run). Degrade to no metrics read
        # rather than raise; affected cells fall back to _NULL_METRICS below.
        logger.warning(
            "aggregate(%s) failed (%s: %s); every cell's metric columns will be "
            "null for this run rather than losing benchmark_grid.csv/.tex "
            "entirely after the cells have already solved.",
            cells_dir,
            type(exc).__name__,
            exc,
        )
        agg = pd.DataFrame()

    metrics_by_cell: dict[tuple[int, int], dict] = {}
    if not agg.empty:
        for _, agg_row in agg.iterrows():
            key = (
                int(agg_row["problem_shape.n_cameras"]),
                int(agg_row["problem_shape.n_frames"]),
            )
            metrics_by_cell[key] = _extract_assembled_row(agg_row)

    status_by_cell = {(s["n_cameras"], s["n_frames"]): s for s in cell_statuses}

    rows: list[dict] = []
    for n_cameras, n_frames in DECLARED_CELLS:
        cell_key = f"cameras_{n_cameras}_frames_{n_frames}"
        status_entry = status_by_cell.get(
            (n_cameras, n_frames),
            {
                "status": "failed",
                "status_reason": "no status recorded for this declared cell",
                "exit_code": None,
            },
        )
        row: dict = {
            "cell_key": cell_key,
            "n_cameras": n_cameras,
            "n_frames": n_frames,
            "status": status_entry.get("status", "failed"),
            "status_reason": status_entry.get("status_reason", ""),
            "exit_code": status_entry.get("exit_code"),
        }

        metrics = metrics_by_cell.get((n_cameras, n_frames))
        # CR-01: null the metric columns only when the status is "failed" or
        # when no record was ever read for this cell -- never merely because
        # the status is not "ok". A "skipped_existing" cell's whole reason for
        # existing is the documented D-24 resume path: aggregate() already
        # read that cell's on-disk record successfully a few lines above, and
        # nulling it here would defeat the only reason the skip exists.
        if row["status"] == "failed" or metrics is None:
            row.update(_NULL_METRICS)
        else:
            row.update(metrics)
            # D-19.3-11/plan 19.3-07: a PRODUCTION cell (every DECLARED_CELLS
            # cell reaches here; SMOKE_CELLS never call build_grid_dataframe
            # at all -- see _run_smoke_cells) whose final solution recorded a
            # non-zero degenerate_observations_at_solution count can never
            # publish as converged. Exactly `> 0`, never a threshold --
            # metrics stay populated (this is the "populate metrics" branch,
            # not the null branch), only "status" and "status_reason" move.
            # This is NOT the same predicate as "is this a fresh, non-skipped
            # cell" (that is `row["status"] == "failed"` above, unchanged) --
            # a resumed `skipped_existing` cell with a positive count is
            # gated too, since its on-disk record is exactly as degenerate as
            # a freshly-run one would be.
            n_degenerate = row.get("degenerate_observations_at_solution")
            if row["status"] in ("ok", "skipped_existing") and (
                n_degenerate is not None and n_degenerate > 0
            ):
                row["status"] = "degenerate"
                row["status_reason"] = (
                    f"{n_degenerate} degenerate observation(s) recorded at "
                    "the final solution -- first-order optimality is "
                    "unreliable for this cell (D-19.3-11)"
                )

        rows.append(row)

    e2_record: dict | None = None
    if e2_benchmark_path is None:
        logger.warning(
            "No E2 benchmark record resolved for this out_dir; emitting a null "
            "real-rig row (record_source=missing_e2_benchmark) instead of "
            "importing another machine's record (FIX-05, D-09)."
        )
    else:
        e2_benchmark_path = Path(e2_benchmark_path)
        if not e2_benchmark_path.exists():
            logger.warning(
                "E2 benchmark record not found at %s; emitting a null real-rig row "
                "(record_source=missing_e2_benchmark) instead of raising after all "
                "declared cells have solved (CR-03).",
                e2_benchmark_path,
            )
        else:
            try:
                with open(e2_benchmark_path) as f:
                    e2_record = json.load(f)
            except (OSError, json.JSONDecodeError) as exc:
                logger.warning(
                    "E2 benchmark record at %s could not be read (%s: %s); "
                    "emitting a null real-rig row (record_source=missing_e2_benchmark) "
                    "instead of raising (CR-03).",
                    e2_benchmark_path,
                    type(exc).__name__,
                    exc,
                )

    if e2_record is None:
        e2_row = {
            "cell_key": "real_rig_13cam_200fr",
            "n_cameras": None,
            "n_frames": None,
            "status": "failed",
            "status_reason": (
                f"E2 benchmark.json missing or unreadable at {e2_benchmark_path}"
            ),
            "exit_code": None,
        }
        e2_row.update(_NULL_METRICS)
        e2_row["record_source"] = "missing_e2_benchmark"
    else:
        e2_row = {
            "cell_key": "real_rig_13cam_200fr",
            "n_cameras": e2_record.get("problem_shape", {}).get("n_cameras"),
            "n_frames": e2_record.get("problem_shape", {}).get("n_frames_calibration"),
            "status": "ok",
            "status_reason": "",
            "exit_code": None,
        }
        e2_row.update(_extract_pipeline_row(e2_record))
    rows.append(e2_row)

    return pd.DataFrame(rows, columns=GRID_COLUMNS)


# ---------------------------------------------------------------------------
# D-17 (DEGEN-05): the optimality caveat, shipped inside benchmark_grid.tex.
#
# `optimality_stage3_interface_optimization` reaches Zenodo in both
# benchmark_grid.csv and benchmark_grid.tex. A reader who meets the number must
# meet its caveat in the same artifact, so the caveat travels as a LaTeX comment
# block emitted immediately before the two blocks that carry the column. This is
# the FIX-04 labelling pattern (e7_focal_standoff.csv's `scope` column) applied
# to the .tex: no schema change, no CSV comment line (a leading `#` breaks
# pd.read_csv and E4's own --check), and no co-opting of the cell-status
# reason column, which the status gate owns.
#
# Every line MUST start with `%`. The block is concatenated verbatim into a
# LaTeX document; a non-comment line here would corrupt it.
# ---------------------------------------------------------------------------
OPTIMALITY_CAVEAT_TEX = """\
% ---------------------------------------------------------------------------
% CAVEAT on optimality_stage3_interface_optimization (D-17, DEGEN-05).
% Measured 2026-08-17; derivation and raw data in
% .planning/probes/2026-08-17-optimality-decomposition/FINDINGS.md
%
% This column is scipy trf's first-order optimality, max|g . v| over the
% parameter vector, with v the Coleman-Li scaling vector. It is a MEASUREMENT,
% never a converged/diverged verdict, and it has three properties a reader must
% know before comparing two of these values:
%
%   (1) VOLATILE AT A FIXED SOLUTION. Restarting a converged solve from its own
%       solution moves the reported value 92.78 -> 27.58 -> 2.16 -- a 43x swing
%       -- while the cost does not move at all (largest relative drop 1.8e-9).
%       The problem is genuinely, severely ill-conditioned: directional
%       curvature ~3e8, a narrow valley whose floor is flat in cost while the
%       gradient swings. A single reported value therefore locates a point on
%       that floor, not a distance from the minimum.
%
%   (2) NOT COMPARABLE ACROSS PARAMETER BLOCKS. The Coleman-Li vector v runs
%       three regimes in this problem: v = 1 for the unbounded extrinsics and
%       board poses, v ~ 700 for the wide-bounded intrinsics (0.5x fx to 2x fx),
%       and v ~ 2e-12 for a pinned water_z. One scalar mixes all three, so a
%       value dominated by one block cannot be read against a value dominated by
%       another. It is not a like-for-like maximum.
%
%   (3) MAGNITUDE-DEPENDENT IN RELIABILITY. Large values are trustworthy: 92.78
%       agrees with a central-difference reference Jacobian to five significant
%       figures. Small values are not: a reported 0.001146 sits against a
%       3-point reference of 0.001655, a 44% disagreement. DIFFERENCES BETWEEN
%       TWO SMALL OPTIMALITY VALUES CARRY NO INFORMATION.
%
% None of this is a defect in any number in the tables below. Finite-difference
% Jacobian noise was tested as the driver and falsified -- the gradient this
% column reports is real -- and the library's FD step rule tracked the 3-point
% reference in both the large- and small-gradient regimes.
% ---------------------------------------------------------------------------"""


def write_grid_latex(df: pd.DataFrame, path: Path) -> None:
    """Write `benchmark_grid.tex`: two synthetic views plus a separate real-rig block.

    Delegates all table formatting to `experiments._render.write_latex_
    fragment` (no second LaTeX layer, P1) three times -- a compact main-text
    summary over the nine synthetic rows, a full supplement grid over the
    same nine rows, and the real-rig row -- then concatenates the three
    fragments with a labeling comment between them.

    The real-rig row is rendered in its OWN block, never appended as a
    tenth point to the nine-cell scaling curve (D-02): the nine synthetic
    rows are optimization-only and mutually comparable; the real-rig row is
    end-to-end and pipeline-written, and mixing them into one table would
    silently compare unlike quantities. Do not "tidy" these three blocks
    into one table.

    Args:
        df: `build_grid_dataframe()`'s output.
        path: Destination `.tex` file path.
    """
    synthetic = df[df["record_source"] == "assembled"].reset_index(drop=True)
    real_rig = df[df["record_source"] == "pipeline"].reset_index(drop=True)

    path = Path(path)
    with tempfile.TemporaryDirectory(prefix="e4_latex_") as tmp:
        tmp_dir = Path(tmp)
        summary_path = tmp_dir / "summary.tex"
        full_path = tmp_dir / "full.tex"
        real_rig_path = tmp_dir / "real_rig.tex"

        write_latex_fragment(synthetic, summary_path, GRID_SUMMARY_COLUMNS)
        write_latex_fragment(synthetic, full_path, GRID_COLUMNS)
        write_latex_fragment(real_rig, real_rig_path, GRID_COLUMNS)

        blocks = [
            "% E4 compact summary (nine synthetic cells, main-text table)",
            summary_path.read_text(),
            # D-17: the caveat sits immediately before the only two blocks that
            # carry optimality_stage3_interface_optimization (the compact
            # summary above does not -- GRID_SUMMARY_COLUMNS omits it), so a
            # reader meets it before the number in every rendering order.
            OPTIMALITY_CAVEAT_TEX,
            "% E4 full grid (nine synthetic cells, supplement table)",
            full_path.read_text(),
            # See this function's docstring: the real-rig row is its own
            # block, never a tenth point on the nine-cell curve above (D-02).
            "% E4 real-rig anchor row (pipeline-written, end-to-end; see D-02)",
            real_rig_path.read_text(),
        ]
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("\n".join(blocks))


# ---------------------------------------------------------------------------
# COV-06: splicing two runs' cell rows into one repeat frame (plan 19.5-08)
# ---------------------------------------------------------------------------

# Columns compared for "same problem" preconditions before a timing
# comparison across repeats is considered meaningful (T-19.5-08-01).
_REPEAT_IDENTITY_COLUMNS: tuple[str, ...] = (
    "n_observations",
    "normal_fixed",
    "shared_interface",
    "seed",
)


def splice_repeat_records(
    frames: Sequence[pd.DataFrame], cells: Sequence[tuple[int, int]]
) -> pd.DataFrame:
    """Splice N independent E4 runs' rows for `cells` into one repeat frame (COV-06).

    A pure function over already-loaded DataFrames -- it opens no file and
    runs no solve. Each element of `frames` is one independent run's rows
    (e.g. the committed `benchmark_grid.csv` as run 1, a repeat directory's
    aggregated cells as run 2); this function only filters to `cells`,
    concatenates, labels each run with a 1-based `repeat` column (in
    argument order), validates that the splice is defensible, and adds two
    derived columns.

    Refuses (raises `ValueError`, naming the offending cell(s)) rather than
    silently producing a misleading spread when:
    - any frame is missing one of `cells` (T-19.5-08-01: a partial repeat
      must not be presented as a spread);
    - any spliced row has a null `nfev_stage3_interface_optimization` while
      its `seconds_stage3_interface_optimization` is non-null (T-19.5-08-02:
      MF-03 requires nfev beside every wall-clock figure);
    - the frames disagree, for the same cell, on any of
      `_REPEAT_IDENTITY_COLUMNS` (`n_observations`, `normal_fixed`,
      `shared_interface`, `seed`) -- these are the "same problem"
      preconditions that make a timing comparison meaningful.

    Adds `seconds_total` (the null-safe sum of the two stage seconds
    columns -- ordinary `+` already propagates `NaN` without raising) and,
    per cell, `seconds_total_spread_pct` (the run-to-run spread, `(max -
    min) / mean * 100`, broadcast to every row of that cell). Computes no
    p-value and no confidence interval: n=2 supports a spread, nothing more
    (T-19.5-08-03).

    Args:
        frames: One DataFrame per independent run, in the order the
            `repeat` column should number them (1-based).
        cells: The `(n_cameras, n_frames)` pairs to splice. Typically
            `REPEAT_CELLS`.

    Returns:
        The spliced frame, filtered to `cells`, sorted by `(n_cameras,
        n_frames, repeat)`.

    Raises:
        ValueError: Per the refusal conditions above.
    """
    cell_set = set(cells)
    pieces: list[pd.DataFrame] = []
    for repeat_index, frame in enumerate(frames, start=1):
        keys = list(zip(frame["n_cameras"], frame["n_frames"]))
        present = {
            (int(n_cameras), int(n_frames))
            for n_cameras, n_frames in keys
            if pd.notna(n_cameras) and pd.notna(n_frames)
        }
        missing = cell_set - present
        if missing:
            raise ValueError(
                f"splice_repeat_records: run {repeat_index} of {len(frames)} "
                f"is missing cell(s) {sorted(missing)} -- a partial repeat "
                "cannot be presented as a spread (T-19.5-08-01)"
            )
        mask = [
            pd.notna(n_cameras)
            and pd.notna(n_frames)
            and (int(n_cameras), int(n_frames)) in cell_set
            for n_cameras, n_frames in keys
        ]
        filtered = frame.loc[mask].copy()
        filtered["repeat"] = repeat_index
        pieces.append(filtered)

    spliced = pd.concat(pieces, ignore_index=True)

    wallclock_col = "seconds_stage3_interface_optimization"
    nfev_col = "nfev_stage3_interface_optimization"
    bad_nfev = spliced[spliced[wallclock_col].notna() & spliced[nfev_col].isna()]
    if not bad_nfev.empty:
        bad_cells = sorted(
            {(int(row.n_cameras), int(row.n_frames)) for row in bad_nfev.itertuples()}
        )
        raise ValueError(
            f"splice_repeat_records: cell(s) {bad_cells} have a non-null "
            f"{wallclock_col} but a null {nfev_col} -- MF-03 requires nfev "
            f"beside every wall-clock figure (T-19.5-08-02)"
        )

    for n_cameras, n_frames in cells:
        cell_rows = spliced[
            (spliced["n_cameras"] == n_cameras) & (spliced["n_frames"] == n_frames)
        ]
        for column in _REPEAT_IDENTITY_COLUMNS:
            if cell_rows[column].nunique(dropna=False) > 1:
                raise ValueError(
                    f"splice_repeat_records: cell ({n_cameras}, {n_frames}) "
                    f"disagrees on {column!r} across runs: "
                    f"{cell_rows[column].tolist()} -- these are not the same "
                    "problem, so a timing comparison is not meaningful "
                    "(T-19.5-08-01)"
                )

    spliced["seconds_total"] = (
        spliced["seconds_stage3_interface_optimization"]
        + spliced["seconds_stage3_intrinsic_pass"]
    )

    spread_by_cell: dict[tuple[int, int], float] = {}
    for n_cameras, n_frames in cells:
        cell_rows = spliced[
            (spliced["n_cameras"] == n_cameras) & (spliced["n_frames"] == n_frames)
        ]
        values = cell_rows["seconds_total"].dropna()
        if len(values) < 2 or values.mean() == 0:
            spread_by_cell[(n_cameras, n_frames)] = float("nan")
        else:
            spread_by_cell[(n_cameras, n_frames)] = (
                (values.max() - values.min()) / values.mean() * 100.0
            )

    spliced["seconds_total_spread_pct"] = [
        spread_by_cell.get((int(n_cameras), int(n_frames)), float("nan"))
        for n_cameras, n_frames in zip(spliced["n_cameras"], spliced["n_frames"])
    ]

    return spliced.sort_values(
        by=["n_cameras", "n_frames", "repeat"], kind="stable"
    ).reset_index(drop=True)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def build_arg_parser() -> argparse.ArgumentParser:
    """Build E4's CLI parser: the shared five-flag contract plus `--cell`."""
    parser = argparse.ArgumentParser(
        description=__doc__, parents=[build_experiment_arg_parser()]
    )
    parser.add_argument(
        "--cell",
        type=str,
        default=None,
        help="Run exactly one cell as '<n_cameras>x<n_frames>' (e.g. "
        "'16x200') and exit -- the child-process entry point "
        "run_cell_subprocess spawns. Not for direct interactive use. "
        "Mutually exclusive with --check and --smoke.",
    )
    parser.add_argument(
        "--no-fail-fast",
        action="store_true",
        default=False,
        help="D-19.4-11: by default, the full nine-cell run aborts and "
        "exits non-zero at the first cell that does not complete ok or "
        "skipped_existing. Pass --no-fail-fast to restore the old "
        "record-and-continue behaviour (every declared cell still gets a "
        "row, the run always exits 0) -- the sole intended use is "
        "19.2-21's pre-authorised 16x200 failing cell.",
    )
    parser.add_argument(
        "--splice-repeat",
        type=Path,
        default=None,
        help="COV-06 (plan 19.5-08): splice a completed repeat run into "
        "benchmark_grid_repeat.csv. Performs NO solve -- loads the "
        "committed benchmark_grid.csv (run 1) and aggregates "
        "<--splice-repeat directory>/e4_cells/ (run 2), splices "
        "REPEAT_CELLS via splice_repeat_records, and writes "
        "benchmark_grid_repeat.csv under --out. Mutually exclusive with "
        "--check and --smoke.",
    )
    return parser


def _validate_e4_args(
    parser: argparse.ArgumentParser, args: argparse.Namespace
) -> None:
    """Extend the shared five-flag validation with `--cell`'s constraints."""
    validate_args(parser, args)
    if args.cell is not None and (args.check or args.smoke):
        parser.error("--cell cannot be combined with --check or --smoke")
    if args.splice_repeat is not None and (args.check or args.smoke):
        parser.error("--splice-repeat cannot be combined with --check or --smoke")


def _parse_cell(parser: argparse.ArgumentParser, cell_str: str) -> tuple[int, int]:
    """Parse and validate a `--cell` value against the allowed cell set."""
    parts = cell_str.lower().split("x")
    n_cameras: int | None = None
    n_frames: int | None = None
    if len(parts) == 2:
        try:
            n_cameras, n_frames = int(parts[0]), int(parts[1])
        except ValueError:
            n_cameras = n_frames = None

    if n_cameras is None or (n_cameras, n_frames) not in _ALLOWED_CELL_VALUES:
        parser.error(
            f"--cell value {cell_str!r} must name a declared or smoke cell "
            f"of the form '<n_cameras>x<n_frames>'; valid values are "
            f"{sorted(_ALLOWED_CELL_VALUES)}"
        )
    return n_cameras, n_frames  # type: ignore[return-value]


def _aggregate_repeat_run(cells_dir: Path) -> pd.DataFrame:
    """Build a repeat run's splice-ready frame from its own `e4_cells/` tree.

    Reuses `aggregate()` (E4's existing per-cell flattening) and
    `_extract_assembled_row` (E4's existing column extraction) unmodified --
    no second aggregator, no re-derivation of any metric. Adds only
    `n_cameras`/`n_frames`, read off the same aggregate row, so the result
    carries the columns `splice_repeat_records` needs.

    Args:
        cells_dir: A repeat directory's `e4_cells/` subdirectory (i.e.
            `<repeat_out_dir>/e4_cells`).

    Returns:
        One row per cell found under `cells_dir`.
    """
    agg = aggregate(cells_dir)
    rows: list[dict] = []
    for _, agg_row in agg.iterrows():
        row = {
            "n_cameras": int(agg_row["problem_shape.n_cameras"]),
            "n_frames": int(agg_row["problem_shape.n_frames"]),
        }
        row.update(_extract_assembled_row(agg_row))
        rows.append(row)
    return pd.DataFrame(rows)


# D-19.5-05: every band this phase produces states what it varies and what it
# therefore bounds. This repeat varies only wall-clock across two runs of the
# SAME three 100-frame cells on ONE machine (n=2 per cell) -- it is not a
# distribution and not an environment-independent figure.
_SPLICE_REPEAT_SCOPE = (
    "COV-06 repeat (plan 19.5-08): run-to-run wall-clock variation of three "
    "100-frame cells (8,100)/(12,100)/(16,100) on ONE machine, n=2 per cell. "
    "Bounds run-to-run spread on this machine ONLY -- not a distribution, "
    "not an environment-independent figure (D-19.5-05)."
)


def _run_splice_repeat(args: argparse.Namespace) -> int:
    """`--splice-repeat <repeat_out_dir>`: splice a completed repeat, no solve.

    Loads the committed `experiments/results/benchmark_grid.csv` as run 1
    (the published record -- never re-run here, see the plan's
    design_decision), aggregates `<repeat_out_dir>/e4_cells/` as run 2, and
    calls `splice_repeat_records([run1, run2], REPEAT_CELLS)`. Writes
    `benchmark_grid_repeat.csv` (key columns `n_cameras`, `n_frames`,
    `repeat`) under `--out`, always overwriting -- regenerating the splice
    IS the point, the same convention `_run_band`-style callers use for
    their own band CSVs.

    Args:
        args: Parsed CLI namespace; `args.splice_repeat` names the repeat
            run's output directory, `args.out` the destination directory.

    Returns:
        0 on success.

    Raises:
        FileNotFoundError: If the committed `benchmark_grid.csv` is not
            found under `--out`.
        ValueError: Whatever `splice_repeat_records` raises (a partial or
            mismatched repeat).
    """
    out_dir = resolve_out_dir(args.out)
    committed_path = out_dir / "benchmark_grid.csv"
    if not committed_path.exists():
        raise FileNotFoundError(
            f"--splice-repeat requires a committed benchmark_grid.csv at "
            f"{committed_path} to use as run 1 -- it is never re-run here."
        )
    run1 = pd.read_csv(committed_path)

    repeat_out_dir = Path(args.splice_repeat)
    run2 = _aggregate_repeat_run(repeat_out_dir / "e4_cells")

    spliced = splice_repeat_records([run1, run2], REPEAT_CELLS)
    spliced["scope"] = _SPLICE_REPEAT_SCOPE

    write_experiment_csv(
        spliced,
        out_dir / "benchmark_grid_repeat.csv",
        key_columns=["n_cameras", "n_frames", "repeat"],
        force=True,
    )

    for n_cameras, n_frames in REPEAT_CELLS:
        cell_rows = spliced[
            (spliced["n_cameras"] == n_cameras) & (spliced["n_frames"] == n_frames)
        ]
        spread_pct = cell_rows["seconds_total_spread_pct"].iloc[0]
        print(
            f"cameras={n_cameras} frames={n_frames}: "
            f"seconds_total_spread_pct={spread_pct}"
        )

    return 0


def _run_check(args: argparse.Namespace) -> int:
    """`--check`: re-aggregate on-disk cells, compare against the committed CSV.

    Never re-runs a cell, never spawns a subprocess, never writes. Reports
    and returns non-zero if `e4_cells/` is empty or absent rather than
    trivially passing on an empty frame (review M9).
    """
    out_dir = resolve_out_dir(args.out)
    cells_dir = out_dir / "e4_cells"
    if not cells_dir.exists() or not any(cells_dir.rglob("benchmark.json")):
        print(
            f"--check re-aggregates existing per-cell benchmark.json files "
            f"under {cells_dir} and never re-runs a cell; found none there. "
            "Run the full grid first (python -m experiments.e4_benchmark_grid)."
        )
        return 1

    committed_path = out_dir / "benchmark_grid.csv"
    if not committed_path.exists():
        print(f"No committed baseline at {committed_path} to check against.")
        return 1

    cell_statuses = []
    for n_cameras, n_frames in DECLARED_CELLS:
        cell_file = (
            cells_dir / f"cameras_{n_cameras}_frames_{n_frames}" / "benchmark.json"
        )
        exists = cell_file.exists()
        cell_statuses.append(
            {
                "n_cameras": n_cameras,
                "n_frames": n_frames,
                "status": "ok" if exists else "failed",
                "status_reason": ""
                if exists
                else "no benchmark.json found under e4_cells for this declared cell",
                "exit_code": None,
            }
        )

    e2_path, e2_note = resolve_e2_benchmark_path(out_dir)
    logger.info("E2 real-rig record: %s (%s)", e2_path, e2_note)
    print(f"E2 real-rig record: {e2_path} ({e2_note})")

    # D-07: print what --check skips, unconditionally, pass or fail -- so a
    # reader of a green --check knows exactly what green does not cover.
    print(
        "--check excludes these columns from cell comparison (never "
        f"reproducible under --check, D-07): {', '.join(CHECK_EXCLUDED_COLUMNS)} "
        "-- exit_code: _run_check hardcodes None (no subprocess runs under "
        "--check) while the committed CSV holds the real run's exit code; "
        "status_reason: empty-string-versus-NaN round-trip through CSV."
    )

    df = build_grid_dataframe(out_dir, cell_statuses, e2_path)
    report = compare_experiment_csv(
        df,
        committed_path,
        key_columns=GRID_KEY_COLUMNS,
        rtol=CHECK_RTOL,
        exclude_columns=CHECK_EXCLUDED_COLUMNS,
    )
    print(report.message)
    return exit_code_for(report)


def _run_smoke_cells(out_dir: Path, seed: int) -> int:
    """Run `SMOKE_CELLS` through the real subprocess hop at trivial scale."""
    all_ok = True
    for n_cameras, n_frames in SMOKE_CELLS:
        row = run_cell_subprocess(
            n_cameras, n_frames, seed, out_dir, force=True, timeout=CELL_TIMEOUT_SECONDS
        )
        logger.info(
            "smoke cell %s: status=%s exit_code=%s",
            row["cell_key"],
            row["status"],
            row["exit_code"],
        )
        if row["status"] != "ok":
            all_ok = False
            logger.warning(
                "smoke cell %s did not complete ok: %s",
                row["cell_key"],
                row["status_reason"],
            )
    return 0 if all_ok else 1


def _run_smoke(args: argparse.Namespace) -> int:
    """`--smoke`: exercise the full code path, including the subprocess hop."""
    parser = build_arg_parser()
    if args.out == parser.get_default("out"):
        # Honor an explicitly-passed --out; otherwise use a throwaway temp
        # directory so a bare --smoke never pollutes experiments/results/.
        with tempfile.TemporaryDirectory(prefix="e4_smoke_") as tmp:
            return _run_smoke_cells(resolve_out_dir(Path(tmp)), args.seed)
    return _run_smoke_cells(resolve_out_dir(args.out), args.seed)


def _run_full(args: argparse.Namespace) -> int:
    """Run the nine declared cells (one subprocess each, sequentially) and render.

    D-19.4-11: by default (`args.no_fail_fast` False, fail-fast ON), the loop
    stops at the first cell whose status is neither `"ok"` nor
    `"skipped_existing"`, prints the abort message to stderr, and returns
    non-zero WITHOUT calling any subsequent cell. `--no-fail-fast` restores
    the pre-existing behaviour exactly: every declared cell still runs, every
    cell still gets a row (via `build_grid_dataframe`'s left join), and the
    function still returns 0 regardless of any cell's recorded status.
    """
    out_dir = resolve_out_dir(args.out)
    fail_fast = not args.no_fail_fast

    cell_statuses = []
    for n_cameras, n_frames in DECLARED_CELLS:
        # Cells run one at a time, never concurrently -- E4 is a wall-clock
        # and peak-memory benchmark and two cells sharing the box would
        # contaminate both measurements.
        row = run_cell_subprocess(
            n_cameras,
            n_frames,
            args.seed,
            out_dir,
            args.force,
            timeout=CELL_TIMEOUT_SECONDS,
            no_fail_fast=args.no_fail_fast,
        )
        cell_statuses.append(row)
        if fail_fast and row["status"] not in ("ok", "skipped_existing"):
            print(
                _fail_fast_abort_message(row["cell_key"], row["status_reason"]),
                file=sys.stderr,
            )
            return 1

    e2_path, e2_note = resolve_e2_benchmark_path(out_dir)
    logger.info("E2 real-rig record: %s (%s)", e2_path, e2_note)

    df = build_grid_dataframe(out_dir, cell_statuses, e2_path)
    write_experiment_csv(
        df,
        out_dir / "benchmark_grid.csv",
        key_columns=GRID_KEY_COLUMNS,
        force=args.force,
    )
    write_grid_latex(df, out_dir / "benchmark_grid.tex")
    return 0


def main(argv: list[str] | None = None) -> int:
    """CLI entry point for `python -m experiments.e4_benchmark_grid`."""
    parser = build_arg_parser()
    args = parser.parse_args(argv)
    _validate_e4_args(parser, args)

    logging.basicConfig(level=logging.INFO, format="%(message)s")

    if args.splice_repeat is not None:
        return _run_splice_repeat(args)

    if args.cell is not None:
        n_cameras, n_frames = _parse_cell(parser, args.cell)
        out_dir = resolve_out_dir(args.out)
        fail_fast = not args.no_fail_fast
        try:
            row = run_grid_cell(
                n_cameras, n_frames, args.seed, out_dir, args.force, fail_fast=fail_fast
            )
        except Exception as exc:
            # D-19.4-11: fail_fast=True made run_grid_cell re-raise instead
            # of swallowing the exception -- print the abort message with
            # the cell key and the exception, then exit non-zero.
            cell_key = f"cameras_{n_cameras}_frames_{n_frames}"
            print(
                _fail_fast_abort_message(cell_key, f"{type(exc).__name__}: {exc}"),
                file=sys.stderr,
            )
            return 1
        logger.info("cell %s: status=%s", row["cell_key"], row["status"])
        if row["status"] == "ok":
            return 0
        if row["status"] == "skipped_existing":
            return SKIPPED_EXIT_CODE
        return 1

    if args.check:
        return _run_check(args)

    if args.smoke:
        return _run_smoke(args)

    return _run_full(args)


if __name__ == "__main__":
    sys.exit(main())
