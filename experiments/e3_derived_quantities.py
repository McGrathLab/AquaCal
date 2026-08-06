"""E3: derived quantities and code constants (EXP-07).

Invoked as `python -m experiments.e3_derived_quantities`. Inherits the shared five-flag
CLI contract (`--seed`, `--out`, `--force`, `--smoke`, `--check`) from
`experiments._io.build_experiment_arg_parser` (D-21), plus one script-local flag
(`--include-per-camera-latex`).

Emits, into `--out` (default `experiments/results/`):
    - `code_constants.csv` -- declared-vs-source value, with a pass/fail column (tier 1)
    - `newton_iterations.csv` -- Newton root-find iteration-count distribution over the
      real rig's working volume, for BOTH shipped Newton loops -- `scalar` (per-point
      termination, byte-comparable to the pre-D-32 baseline) and `batch` (the vectorized,
      all-points-terminated loop production actually runs, D-32/CR-05) -- tier 2
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
across this file and E4's own per-cell grid CSV (D-16). That split does not hold: every
`tab:cpr` row is a tilt-enabled (`normal_fixed=False`) configuration, and the rows
previously assigned to E4 would have been produced by a run whose parameter vector is two
tilt DOF smaller -- a wrong number that looks right. E4's grid CSV still reports CPR
columns, but they describe E4's OWN configuration and do NOT feed `tab:cpr`. This module
never reads E4's grid CSV.
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

from aquacal.calibration._optim_common import (
    build_jacobian_sparsity,
    build_structural_column_groups,
)
from aquacal.config.schema import (
    BoardConfig,
    Detection,
    DetectionResult,
    FrameDetections,
)
from aquacal.core.board import BoardGeometry
from aquacal.core.camera import Camera
from aquacal.core.interface_model import Interface
from aquacal.core.refractive_geometry import (
    refractive_project_batch_newton_diagnostic,
    refractive_project_newton_diagnostic,
)
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
from experiments._render import write_latex_fragment

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
    "loop",
    "n_points",
    "iter_min",
    "iter_median",
    "iter_max",
    "n_not_converged",
    "incidence_deg_min",
    "incidence_deg_max",
    "residual_max_m",
]
NEWTON_KEY_COLUMNS = ["camera", "loop"]

# Fixed vocabulary for the `loop` column (D-32/CR-05). "scalar" rows come from
# `refractive_project_newton_diagnostic` (per-point termination, `_solve_newton_r_p`) and
# remain byte-comparable to the pre-D-32 committed baseline. "batch" rows come from
# `refractive_project_batch_newton_diagnostic` -- the vectorized, all-points-terminated
# loop the production residual path (`refractive_project_batch`) actually runs.
NEWTON_LOOP_SCALAR = "scalar"
NEWTON_LOOP_BATCH = "batch"
NEWTON_LOOP_VALUES = (NEWTON_LOOP_SCALAR, NEWTON_LOOP_BATCH)

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

CPR_COLUMNS = [
    "config_key",
    "n_cameras",
    "n_frames",
    "normal_fixed",
    "refine_intrinsics",
    "shared_interface",
    "n_params",
    "n_groups",
    "fd_reduction",
    "record_source",
]
CPR_KEY_COLUMNS = ["config_key"]

# The six published `tab:cpr` configurations (19.2-SOURCE-BRIEF.md Sec E3 Tier 3), as
# (n_cameras, n_frames, normal_fixed, refine_intrinsics). `normal_fixed=False` on every
# row is load-bearing (review H1): "tilt" in `tab:cpr` means tilt-ENABLED, matching
# `CalibrationConfig.interface_normal_fixed`'s default and E2's real-rig run. A row built
# at `normal_fixed=True` would report a P exactly 2 smaller and look entirely plausible.
# tilt+intrinsics (13, 200, ...) -- shared row COPIED from E2's benchmark.json; the rest
# (including its own per-camera row) are computed.
CPR_CONFIGS: list[tuple[int, int, bool, bool]] = [
    (3, 3, False, False),  # tilt
    (16, 200, False, False),  # tilt
    (8, 100, False, True),  # tilt+intrinsics
    (12, 100, False, True),  # tilt+intrinsics
    (13, 200, False, True),  # tilt+intrinsics
    (16, 200, False, True),  # tilt+intrinsics
]

# The one (n_cameras, n_frames, normal_fixed, refine_intrinsics) whose shared-interface row
# is copied from E2's committed record rather than computed here (D-16, review M1). The
# matching per-camera row is still computed: E2 ran shared-interface only, so copying its
# numbers into a shared_interface=False row would publish a fabricated per-camera value
# (review M1).
_COPIED_ROW_CONFIG = (13, 200, False, True)
_COPIED_ROW_STAGE = "stage3_intrinsic_pass"

# The committed E2 record tier 3's shared-interface 13/200 row copies from -- always this
# fixed repo-relative location, independent of --out (the copy source is a checked-in
# artifact, not a fresh run).
_E2_BENCHMARK_JSON_PATH = (
    Path(__file__).resolve().parents[1] / "experiments" / "results" / "benchmark.json"
)


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

    `solver_config: {"seed": seed}` is a deliberate, minimal duplicate of the top-level
    `seed` key (19.2-12, EXP-11 provenance close-out): the general "every committed
    benchmark-shaped record carries a seed" check reads `solver_config["seed"]`, matching
    every `assemble_benchmark_record`-produced file. E3's sidecar predates and does not use
    that assembler, but publishing the same seed at both the top level (for readers of this
    sidecar specifically) and inside `solver_config` (for the generic provenance check) is
    cheaper and less surprising than teaching every consumer this one file's exception.
    """
    return {
        "experiment": "e3",
        "schema_version": 1,
        "seed": seed,
        "solver_config": {"seed": seed},
        "environment": capture_environment(),
    }


def _summarize_newton_records(
    camera_label: str, loop: str, records: list[dict]
) -> dict:
    """Aggregate one camera's (or the pooled `ALL`) list of diagnostic dicts into one row.

    `records` holds only records over VALID points -- the degenerate cases are skipped by
    the caller and never enter these statistics. `loop` identifies which of the two
    shipped Newton loops (`NEWTON_LOOP_SCALAR` / `NEWTON_LOOP_BATCH`) these records were
    measured from; each record dict has the same shape regardless of loop
    (`n_iterations`, `converged`, `final_residual`, `r_p`, `incidence_angle_deg`) -- see
    `_batch_diagnostic_to_records`.
    """
    n_iterations = [r["n_iterations"] for r in records]
    incidence = [r["incidence_angle_deg"] for r in records]
    residuals = [r["final_residual"] for r in records]
    n_not_converged = sum(1 for r in records if not r["converged"])
    return {
        "camera": camera_label,
        "loop": loop,
        "n_points": len(records),
        "iter_min": int(np.min(n_iterations)),
        "iter_median": float(np.median(n_iterations)),
        "iter_max": int(np.max(n_iterations)),
        "n_not_converged": n_not_converged,
        "incidence_deg_min": float(np.min(incidence)),
        "incidence_deg_max": float(np.max(incidence)),
        "residual_max_m": float(np.max(residuals)),
    }


def _batch_diagnostic_to_records(diagnostics: dict) -> list[dict]:
    """Convert one `refractive_project_batch_newton_diagnostic` call's per-point arrays
    into one record dict per valid point, in the same shape
    `refractive_project_newton_diagnostic` returns, so both loops feed
    `_summarize_newton_records` unchanged.

    A point's `n_iterations` is the iteration at which its OWN `|delta|` first fell below
    tolerance (`converged_at_iteration`) if it converged; if it never did, `n_iterations`
    is `n_iterations_executed` -- the number of loop iterations that actually ran, which
    the batch diagnostic observed directly, not a value inferred from a residual
    threshold.
    """
    n_executed = diagnostics["n_iterations_executed"]
    records = []
    for i in range(len(diagnostics["point_index"])):
        converged = bool(diagnostics["converged"][i])
        converged_at = int(diagnostics["converged_at_iteration"][i])
        records.append(
            {
                "n_iterations": converged_at if converged else n_executed,
                "converged": converged,
                "final_residual": float(diagnostics["final_abs_delta"][i]),
                "r_p": float(diagnostics["r_p"][i]),
                "incidence_angle_deg": float(diagnostics["incidence_angle_deg"][i]),
            }
        )
    return records


def build_newton_iterations_df(n_frames: int, seed: int) -> pd.DataFrame:
    """Tier 2: measure the Newton root-find iteration distribution over the real rig's
    working volume, through BOTH shipped Newton loops (D-19, D-32/CR-05).

    Sweeps `generate_real_rig_trajectory`'s board poses (same substrate E5 uses, D-09/D-20)
    against `generate_real_rig_array`'s 12-camera geometry, calling
    `refractive_project_newton_diagnostic` (the scalar, per-point-terminated loop) once
    per board corner per pose per camera, AND `refractive_project_batch_newton_diagnostic`
    (the vectorized, all-points-terminated loop the production residual path actually
    runs, D-32) once per pose per camera over that pose's corners. `None`/excluded returns
    (the degenerate cases: camera at/below interface, point at/above interface, point
    directly below the camera) are skipped and never enter either loop's iteration
    statistics. Emits one row per camera per loop plus one pooled `ALL` row per loop (26
    rows total for 12 cameras + ALL, over 2 loops), each pooled row computed directly from
    that loop's per-point records (not by re-averaging the per-camera summaries).

    Never re-implements a Newton loop and never infers an iteration count from a residual
    -- both public diagnostics are the only sources (D-19, D-32).

    Does not assert or gate on the observed maximum: if it exceeds the shipped
    `max_iterations=10` cap, that is a finding for the manuscript, not a failure (D-20).
    """
    intrinsics, extrinsics, water_zs = generate_real_rig_array()
    board_poses = generate_real_rig_trajectory(
        n_frames=n_frames,
        board=_REAL_RIG_BOARD_CONFIG,
        water_zs=water_zs,
        depth_range=None,
        seed=seed,
    )
    board = BoardGeometry(_REAL_RIG_BOARD_CONFIG)
    cameras = {cam: Camera(cam, intrinsics[cam], extrinsics[cam]) for cam in intrinsics}
    interface = Interface(
        normal=_INTERFACE_NORMAL, camera_distances=water_zs, n_air=1.0, n_water=1.333
    )

    per_camera_scalar: dict[str, list[dict]] = {cam: [] for cam in cameras}
    per_camera_batch: dict[str, list[dict]] = {cam: [] for cam in cameras}
    for pose in board_poses:
        world_corners = board.transform_corners(pose.rvec, pose.tvec)
        corner_points = np.array(list(world_corners.values()), dtype=np.float64)
        for cam_name, camera in cameras.items():
            for point_3d in world_corners.values():
                diagnostic = refractive_project_newton_diagnostic(
                    camera, interface, point_3d
                )
                if diagnostic is None:
                    continue
                per_camera_scalar[cam_name].append(diagnostic)

            batch_diagnostics = refractive_project_batch_newton_diagnostic(
                camera, interface, corner_points
            )
            per_camera_batch[cam_name].extend(
                _batch_diagnostic_to_records(batch_diagnostics)
            )

    rows = []
    pooled_scalar_records: list[dict] = []
    pooled_batch_records: list[dict] = []
    for cam_name in sorted(cameras):
        scalar_records = per_camera_scalar[cam_name]
        pooled_scalar_records.extend(scalar_records)
        rows.append(
            _summarize_newton_records(cam_name, NEWTON_LOOP_SCALAR, scalar_records)
        )

        batch_records = per_camera_batch[cam_name]
        pooled_batch_records.extend(batch_records)
        rows.append(
            _summarize_newton_records(cam_name, NEWTON_LOOP_BATCH, batch_records)
        )

    pooled_scalar_row = _summarize_newton_records(
        "ALL", NEWTON_LOOP_SCALAR, pooled_scalar_records
    )
    pooled_batch_row = _summarize_newton_records(
        "ALL", NEWTON_LOOP_BATCH, pooled_batch_records
    )
    rows.append(pooled_scalar_row)
    rows.append(pooled_batch_row)

    logger.info(
        "Newton iterations (pooled, n=%d): scalar min=%d median=%.1f max=%d | "
        "batch min=%d median=%.1f max=%d",
        pooled_scalar_row["n_points"],
        pooled_scalar_row["iter_min"],
        pooled_scalar_row["iter_median"],
        pooled_scalar_row["iter_max"],
        pooled_batch_row["iter_min"],
        pooled_batch_row["iter_median"],
        pooled_batch_row["iter_max"],
    )

    return pd.DataFrame(rows, columns=NEWTON_COLUMNS)


def _make_detections(
    n_cams: int,
    n_frames: int,
    visibility: float = 1.0,
    corners_per_view: int = 4,
    seed: int = 0,
) -> DetectionResult:
    """Build a `DetectionResult` where each camera sees each frame with prob `visibility`.

    Adapted from `tests/unit/test_optim_common.py` (per P3, `experiments/` imports from
    `src/aquacal`, not from `tests/` -- tier 1's constants table is the single deliberate
    exception, and it is not this). Structural-only: this exists to give
    `build_jacobian_sparsity` a connectivity pattern to build a sparsity structure from, not
    to model real detections. At `visibility=1.0` (tier 3's usage) every camera sees every
    frame, matching `n_params`'s closed form (independent of visibility) and the theoretical
    lower-bound group count `build_structural_column_groups`' own docstring documents.
    """
    rng = np.random.default_rng(seed)
    camera_names = [f"cam{i}" for i in range(n_cams)]
    corner_ids = np.arange(corners_per_view, dtype=np.int32)

    frames = {}
    for frame_idx in range(n_frames):
        visible = [c for c in camera_names if rng.random() < visibility]
        if not visible:
            visible = [camera_names[rng.integers(n_cams)]]

        detections = {
            cam: Detection(
                corner_ids=corner_ids.copy(),
                corners_2d=rng.uniform(0.0, 1000.0, size=(corners_per_view, 2)),
            )
            for cam in visible
        }
        frames[frame_idx] = FrameDetections(frame_idx=frame_idx, detections=detections)

    return DetectionResult(
        frames=frames, camera_names=camera_names, total_frames=n_frames
    )


def _build_computed_cpr_row(
    config_key: str,
    n_cameras: int,
    n_frames: int,
    normal_fixed: bool,
    refine_intrinsics: bool,
    shared_interface: bool,
) -> dict:
    """Build one tier-3 CPR row by building a sparsity pattern and grouping it structurally.

    Never hand-rolls a grouping and never uses scipy's generic FD column-grouping colorer
    (`scipy.optimize._numdiff`'s greedy grouper) -- `n_params` and
    `n_groups` are read straight off `build_jacobian_sparsity`/`build_structural_column_groups`,
    the library's own functions.
    """
    detections = _make_detections(n_cameras, n_frames, visibility=1.0, seed=0)
    camera_order = [f"cam{i}" for i in range(n_cameras)]
    frame_order = list(range(n_frames))
    jac_sparsity = build_jacobian_sparsity(
        detections,
        reference_camera="cam0",
        camera_order=camera_order,
        frame_order=frame_order,
        min_corners=1,
        refine_intrinsics=refine_intrinsics,
        normal_fixed=normal_fixed,
        shared_interface=shared_interface,
    )
    groups = build_structural_column_groups(
        jac_sparsity,
        n_cameras,
        n_frames,
        refine_intrinsics=refine_intrinsics,
        normal_fixed=normal_fixed,
        shared_interface=shared_interface,
    )
    n_params = int(jac_sparsity.shape[1])
    n_groups = int(groups.max()) + 1
    return {
        "config_key": config_key,
        "n_cameras": n_cameras,
        "n_frames": n_frames,
        "normal_fixed": normal_fixed,
        "refine_intrinsics": refine_intrinsics,
        "shared_interface": shared_interface,
        "n_params": n_params,
        "n_groups": n_groups,
        "fd_reduction": n_params / n_groups,
        "record_source": "computed",
    }


def predict_jacobian_shape(
    n_cameras: int,
    n_frames: int,
    *,
    refine_intrinsics: bool,
    normal_fixed: bool,
    shared_interface: bool,
    visibility: float = 1.0,
    n_corners: int = 4,
) -> tuple[int, int]:
    """Predict `build_jacobian_sparsity`'s `(n_residuals, n_params)` shape by pure counting.

    Derived from the same parameter-block layout `build_jacobian_sparsity` encodes (read live
    from its source, `_optim_common.py:330-344`), never guessed: 2 tilt params if
    `normal_fixed=False` (else 0), 6 extrinsic DoF per non-reference camera, one dense water_z
    column if `shared_interface` else one per camera, 6 DoF per board frame, and 4 intrinsic
    parameters per camera when `refine_intrinsics`. This is counting only -- no array is ever
    allocated.

    `n_residuals` assumes full visibility (`visibility=1.0`): every camera observes every frame
    with `n_corners` corners and 2 residuals (x, y) per corner, exactly `_make_detections`'
    tier-3 usage (`visibility=1.0` is the only value COV-01 sweeps). A `visibility` below 1.0
    depends on `_make_detections`' own RNG draw and is not counting-derivable; this function
    raises rather than silently returning a wrong shape.

    Args:
        n_cameras: Number of cameras.
        n_frames: Number of board frames.
        refine_intrinsics: Whether intrinsics are in the parameter vector.
        normal_fixed: If False, 2 tilt params are prepended to the parameter vector.
        shared_interface: If True, one dense water_z column; if False, one per camera.
        visibility: Detection visibility fraction. Only `1.0` (full visibility) is supported.
        n_corners: Corners detected per (camera, frame) pair at full visibility.

    Returns:
        `(n_residuals, n_params)`, matching `build_jacobian_sparsity(...).shape` exactly at
        every size where building the real array is affordable.

    Raises:
        NotImplementedError: If `visibility != 1.0`.
    """
    if visibility != 1.0:
        raise NotImplementedError(
            "predict_jacobian_shape only supports visibility=1.0 (full connectivity); "
            "n_residuals below full visibility depends on _make_detections' RNG draw and "
            "is not derivable by counting alone."
        )
    n_tilt_params = 0 if normal_fixed else 2
    n_extrinsic_params = 6 * (n_cameras - 1)
    n_water_z_params = 1 if shared_interface else n_cameras
    n_pose_params = 6 * n_frames
    n_intrinsic_params = 4 * n_cameras if refine_intrinsics else 0
    n_params = (
        n_tilt_params
        + n_extrinsic_params
        + n_water_z_params
        + n_pose_params
        + n_intrinsic_params
    )
    n_residuals = 2 * n_cameras * n_frames * n_corners
    return (n_residuals, n_params)


def _build_copied_cpr_row(
    config_key: str,
    n_cameras: int,
    n_frames: int,
    normal_fixed: bool,
    refine_intrinsics: bool,
    benchmark_json_path: Path,
) -> dict:
    """Build the ONE shared-interface CPR row copied from E2's committed `benchmark.json`
    (D-16, review M1) -- never re-derived. Reads `stages.stage3_intrinsic_pass` specifically,
    since that is the pass `tab:cpr`'s "tilt+intrinsics" descriptor names (review M1 --
    `stage3_interface_optimization` reports a different count for the same problem).

    If the committed record is absent, emits null metrics with `record_source` set to
    `missing_e2_benchmark` and logs a WARNING -- never raises.
    """
    if not benchmark_json_path.exists():
        logger.warning(
            "E2 benchmark record not found at %s; emitting null CPR metrics for %s "
            "(record_source=missing_e2_benchmark).",
            benchmark_json_path,
            config_key,
        )
        return {
            "config_key": config_key,
            "n_cameras": n_cameras,
            "n_frames": n_frames,
            "normal_fixed": normal_fixed,
            "refine_intrinsics": refine_intrinsics,
            "shared_interface": True,
            "n_params": None,
            "n_groups": None,
            "fd_reduction": None,
            "record_source": "missing_e2_benchmark",
        }

    with open(benchmark_json_path) as f:
        record = json.load(f)
    stage = record["stages"][_COPIED_ROW_STAGE]
    return {
        "config_key": config_key,
        "n_cameras": n_cameras,
        "n_frames": n_frames,
        "normal_fixed": normal_fixed,
        "refine_intrinsics": refine_intrinsics,
        "shared_interface": True,
        "n_params": stage["n_params"],
        "n_groups": stage["n_groups"],
        "fd_reduction": stage["fd_reduction"],
        "record_source": "copied_from_e2_benchmark",
    }


def _cpr_config_key(
    n_cameras: int, n_frames: int, refine_intrinsics: bool, shared_interface: bool
) -> str:
    tilt_label = "tilt_intrinsics" if refine_intrinsics else "tilt"
    interface_label = "shared" if shared_interface else "percamera"
    return f"{n_cameras}cam_{n_frames}frame_{tilt_label}_{interface_label}"


def build_cpr_grouping_df(benchmark_json_path: Path) -> pd.DataFrame:
    """Tier 3: build all 12 `cpr_grouping.csv` rows (6 published configs x 2 interface
    modes, D-21). Exactly one row -- the shared-interface 13-camera/200-frame
    tilt+intrinsics row -- is copied from E2's `benchmark.json`; the rest are computed here.
    """
    rows = []
    for n_cameras, n_frames, normal_fixed, refine_intrinsics in CPR_CONFIGS:
        config = (n_cameras, n_frames, normal_fixed, refine_intrinsics)
        for shared_interface in (True, False):
            config_key = _cpr_config_key(
                n_cameras, n_frames, refine_intrinsics, shared_interface
            )
            if config == _COPIED_ROW_CONFIG and shared_interface:
                row = _build_copied_cpr_row(
                    config_key,
                    n_cameras,
                    n_frames,
                    normal_fixed,
                    refine_intrinsics,
                    benchmark_json_path,
                )
            else:
                row = _build_computed_cpr_row(
                    config_key,
                    n_cameras,
                    n_frames,
                    normal_fixed,
                    refine_intrinsics,
                    shared_interface,
                )
            rows.append(row)
    return pd.DataFrame(rows, columns=CPR_COLUMNS)


def _select_cpr_rows_for_latex(
    df: pd.DataFrame, include_per_camera: bool
) -> pd.DataFrame:
    """Default: shared-interface rows only (D-21 -- the supplement's sparsity table
    describes the production configuration). `include_per_camera=True` emits both modes.
    """
    if include_per_camera:
        return df
    return df[df["shared_interface"]]


def write_cpr_latex(
    df: pd.DataFrame, out_dir: Path, include_per_camera: bool, force: bool
) -> bool:
    """Write `cpr_grouping.tex` via `experiments._render.write_latex_fragment` -- no second
    LaTeX layer, no value recomputed at render time (P1).
    """
    path = out_dir / "cpr_grouping.tex"
    if path.exists() and not force:
        logger.info(
            "Skipping write to %s: file already exists and --force was not given "
            "(resumability).",
            path,
        )
        return False
    selected = _select_cpr_rows_for_latex(df, include_per_camera)
    path.parent.mkdir(parents=True, exist_ok=True)
    write_latex_fragment(selected, path, CPR_COLUMNS)
    return True


def _find_cpr_row(
    df: pd.DataFrame, n_cameras: int, n_frames: int, refine_intrinsics: bool
) -> pd.Series:
    """Look up one shared-interface `cpr_grouping.csv` row by its configuration.

    Raises rather than falling back to a placeholder: a missing row means `CPR_CONFIGS` was
    edited and the table is incomplete (no `\\TODO` branch, per Task 3's action).
    """
    match = df[
        (df["n_cameras"] == n_cameras)
        & (df["n_frames"] == n_frames)
        & (df["refine_intrinsics"] == refine_intrinsics)
        & df["shared_interface"]
    ]
    if match.empty:
        raise ValueError(
            f"cpr_grouping.csv is missing a shared-interface row for "
            f"n_cameras={n_cameras}, n_frames={n_frames}, "
            f"refine_intrinsics={refine_intrinsics} -- CPR_CONFIGS may have been edited."
        )
    return match.iloc[0]


def build_derived_values_latex_content(cpr_df: pd.DataFrame) -> str:
    """Regenerate the two derived prose asides (D-22) from `cpr_grouping.csv`'s own
    shared-interface rows -- no dependency on E4's grid, no `\\TODO` placeholder.
    """
    row_13_200 = _find_cpr_row(cpr_df, 13, 200, True)
    pose_params = 6 * int(row_13_200["n_frames"])
    total_params = int(row_13_200["n_params"])
    params_aside = f"{pose_params} of {total_params} parameters"

    row_8 = _find_cpr_row(cpr_df, 8, 100, True)
    row_12 = _find_cpr_row(cpr_df, 12, 100, True)
    reduction_aside = (
        f"{row_8['fd_reduction']:.1f}x to {row_12['fd_reduction']:.1f}x "
        "from eight to twelve cameras"
    )

    lines = [
        f"\\newcommand{{\\CPRParamsAside}}{{{params_aside}}}",
        f"\\newcommand{{\\CPRReductionAside}}{{{reduction_aside}}}",
    ]
    return "\n".join(lines) + "\n"


def write_derived_values_latex(
    out_dir: Path, cpr_df: pd.DataFrame, force: bool
) -> bool:
    """Write `cpr_derived_values.tex` -- two regenerated macro definitions, D-22."""
    path = out_dir / "cpr_derived_values.tex"
    if path.exists() and not force:
        logger.info(
            "Skipping write to %s: file already exists and --force was not given "
            "(resumability).",
            path,
        )
        return False
    content = build_derived_values_latex_content(cpr_df)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)
    return True


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


def _write_tier3(out_dir: Path, include_per_camera: bool, force: bool) -> None:
    cpr_df = build_cpr_grouping_df(_E2_BENCHMARK_JSON_PATH)
    write_experiment_csv(
        cpr_df, out_dir / "cpr_grouping.csv", key_columns=CPR_KEY_COLUMNS, force=force
    )
    write_cpr_latex(cpr_df, out_dir, include_per_camera=include_per_camera, force=force)
    write_derived_values_latex(out_dir, cpr_df, force=force)


def _run_check(out_dir: Path, seed: int) -> int:
    """`--check`: compare a fresh run against committed baselines, tier by tier.

    `seed` is the CLI's `--seed` (WR-05 closed): tier 2's recomputation uses the seed it
    was actually given rather than a hardcoded `seed=42`, so `--check --seed 7` cannot
    report a pass on a seed-42 recomputation it never ran.
    """
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
        fresh_newton = build_newton_iterations_df(n_frames=100, seed=seed)
        report = compare_experiment_csv(
            fresh_newton, newton_path, key_columns=NEWTON_KEY_COLUMNS, rtol=CHECK_RTOL
        )
        print(f"newton_iterations.csv: {report.message}")
        overall_passed = overall_passed and report.passed

    cpr_path = out_dir / "cpr_grouping.csv"
    if not cpr_path.exists():
        print(f"No committed baseline at {cpr_path} to check against.")
        overall_passed = False
    else:
        fresh_cpr = build_cpr_grouping_df(_E2_BENCHMARK_JSON_PATH)
        report = compare_experiment_csv(
            fresh_cpr, cpr_path, key_columns=CPR_KEY_COLUMNS, rtol=CHECK_RTOL
        )
        print(f"cpr_grouping.csv: {report.message}")
        overall_passed = overall_passed and report.passed

    return 0 if overall_passed else 1


def main(argv: list[str] | None = None) -> int:
    """CLI entry point for `python -m experiments.e3_derived_quantities`."""
    parser = build_arg_parser()
    args = parser.parse_args(argv)
    validate_args(parser, args)

    logging.basicConfig(level=logging.INFO, format="%(message)s")

    if args.check:
        out_dir = resolve_out_dir(args.out)
        return _run_check(out_dir, seed=args.seed)

    if args.smoke:
        # Honor an explicitly-passed --out; otherwise fall back to a throwaway temp
        # directory so a bare `--smoke` never pollutes experiments/results/.
        if args.out == parser.get_default("out"):
            with tempfile.TemporaryDirectory(prefix="e3_smoke_") as tmp:
                out_dir = resolve_out_dir(Path(tmp))
                _write_tier1_and_sidecar(out_dir, seed=args.seed, force=True)
                _write_tier2(out_dir, n_frames=3, seed=args.seed, force=True)
                _write_tier3(
                    out_dir,
                    include_per_camera=args.include_per_camera_latex,
                    force=True,
                )
        else:
            out_dir = resolve_out_dir(args.out)
            _write_tier1_and_sidecar(out_dir, seed=args.seed, force=True)
            _write_tier2(out_dir, n_frames=3, seed=args.seed, force=True)
            _write_tier3(
                out_dir, include_per_camera=args.include_per_camera_latex, force=True
            )
        return 0

    out_dir = resolve_out_dir(args.out)
    _write_tier1_and_sidecar(out_dir, seed=args.seed, force=args.force)
    _write_tier2(out_dir, n_frames=100, seed=args.seed, force=args.force)
    _write_tier3(
        out_dir, include_per_camera=args.include_per_camera_latex, force=args.force
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
