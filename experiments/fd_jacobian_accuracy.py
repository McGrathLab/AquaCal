"""E-COV-02: finite-difference Jacobian accuracy vs. a Richardson reference (COV-02).

Invoked as `python -m experiments.fd_jacobian_accuracy`. Inherits the shared
five-flag CLI contract (`--seed`, `--out`, `--force`, `--smoke`, `--check`)
from `experiments._io.build_experiment_arg_parser` (D-21). No script-local
flags.

Answers R1.2's accuracy question -- is the shipped `2-point` finite-difference
Jacobian (`aquacal.calibration._optim_common.make_sparse_jacobian_func`) good
enough? -- WITHOUT deriving the analytic Jacobian (declined, WP3 item 5) and
WITHOUT any `src/aquacal/` change (D-19.5-03): every function here calls
`scipy.optimize._numdiff.approx_derivative` directly, at controlled
`rel_step`, through the identical `sparsity=(jac_sparsity, groups)` path
production uses.

Emits, into `--out` (default `experiments/results/`):
    - `fd_jacobian_accuracy.csv` -- one row per swept `rel_step`
    - `fd_jacobian_accuracy.json` -- provenance sidecar: git_sha, scipy_version,
      shipped_rel_step_default, problem size, newton_tolerance, scope, and the
      `newton_floor_probe` verdict

This module never touches `src/aquacal/` and never mutates production call
sites -- `make_sparse_jacobian_func` itself is not called; the exact same
`approx_derivative(..., method="2-point", sparsity=(jac_sparsity, groups),
bounds=bounds)` call it wraps is reproduced here directly, with `rel_step`
exposed (D-19.5-03's design decision).
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
import time

import numpy as np
import pandas as pd
import scipy
from numpy.typing import NDArray
from scipy.optimize._numdiff import _eps_for_method, approx_derivative

from aquacal.calibration._optim_common import (
    build_bounds,
    build_jacobian_sparsity,
    build_structural_column_groups,
    compute_residuals,
    pack_params,
)
from aquacal.config.schema import BoardConfig
from aquacal.core.board import BoardGeometry
from aquacal.datasets.synthetic import (
    generate_board_trajectory,
    generate_camera_array,
    generate_synthetic_detections,
)
from experiments._io import (
    build_experiment_arg_parser,
    compare_experiment_csv,
    resolve_out_dir,
    validate_args,
)

logger = logging.getLogger(__name__)

CHECK_RTOL = 1e-6

FD_ACCURACY_COLUMNS = [
    "rel_step",
    "max_rel_error",
    "median_rel_error",
    "argmax_column",
    "n_columns_above_1e_3",
    "induced_step_rel_change",
    "is_shipped_default",
    "seconds",
]
FD_ACCURACY_KEY_COLUMNS = ["rel_step"]

# The Newton inner-solve tolerance every projection call goes through
# (`refractive_geometry.py`'s `tolerance: float = 1e-9` default, read here as
# a literal to avoid importing a private symbol -- it is asserted against the
# library's live default in `tests/unit/test_fd_accuracy.py`).
NEWTON_TOLERANCE_DEFAULT = 1e-9

# The candidate step sweep: a decade ladder spanning the shipped default
# (~1.49e-8 for 2-point FD, read live at runtime -- see `shipped_rel_step`)
# by several orders in both directions. Shared by `_run_full` and `_run_check`
# so a `--check` recomputation sweeps exactly the steps the committed CSV was
# built from.
FULL_REL_STEP_SWEEP: list[float] = [
    1e-4,
    1e-5,
    1e-6,
    1e-7,
    1e-8,
    1e-9,
    1e-10,
    1e-11,
]

# The scope sentence D-19.5-05 requires live in the artifact, not only in
# prose: what this characterizes, and what it does not.
FD_ACCURACY_SCOPE = (
    "Characterizes the shipped 2-point finite-difference Jacobian's "
    "column-wise relative error on a small synthetic problem "
    "(n_cameras=4, n_frames=6, refine_intrinsics=False, normal_fixed=False, "
    "shared_interface=True). Does NOT characterize accuracy on the "
    "13-camera real rig or any larger problem."
)


def compare_jacobians(
    j_test: NDArray[np.float64], j_reference: NDArray[np.float64]
) -> dict:
    """Column-wise relative error of `j_test` against `j_reference`.

    A column's relative error is `norm(j_test[:, k] - j_reference[:, k]) /
    norm(j_reference[:, k])`. A column whose reference norm is exactly 0 (a
    parameter the residual truly does not depend on at this point) cannot
    produce a meaningful relative error -- it is skipped and counted in
    `n_columns_skipped` rather than producing `inf`/`NaN`. If `j_test`'s
    matching column is also exactly 0, that is expected (both agree it is a
    null column); if `j_test`'s column is nonzero while the reference's is
    zero, the column is still skipped here (a genuinely different finding
    about sparsity, not this function's job to flag) -- `n_columns_skipped`
    makes that count visible to a caller that wants to check for it.

    Args:
        j_test: Jacobian under test, shape (n_residuals, n_params).
        j_reference: Reference Jacobian, same shape.

    Returns:
        Dict with `max_rel_error` (float), `median_rel_error` (float),
        `argmax_column` (int | None, None only when every column is
        skipped), `n_columns` (int, total columns), `n_columns_skipped`
        (int, columns whose reference norm was exactly 0).
    """
    if j_test.shape != j_reference.shape:
        raise ValueError(
            f"compare_jacobians: shape mismatch j_test={j_test.shape} "
            f"j_reference={j_reference.shape}"
        )

    n_columns = j_test.shape[1]
    ref_norms = np.linalg.norm(j_reference, axis=0)
    diff_norms = np.linalg.norm(j_test - j_reference, axis=0)

    rel_errors: list[float] = []
    rel_error_columns: list[int] = []
    n_columns_skipped = 0
    for col in range(n_columns):
        if ref_norms[col] == 0.0:
            n_columns_skipped += 1
            continue
        rel_errors.append(diff_norms[col] / ref_norms[col])
        rel_error_columns.append(col)

    if not rel_errors:
        return {
            "max_rel_error": 0.0,
            "median_rel_error": 0.0,
            "argmax_column": None,
            "n_columns": n_columns,
            "n_columns_skipped": n_columns_skipped,
        }

    rel_errors_arr = np.asarray(rel_errors, dtype=np.float64)
    argmax_local = int(np.argmax(rel_errors_arr))
    return {
        "max_rel_error": float(rel_errors_arr[argmax_local]),
        "median_rel_error": float(np.median(rel_errors_arr)),
        "argmax_column": int(rel_error_columns[argmax_local]),
        "n_columns": n_columns,
        "n_columns_skipped": n_columns_skipped,
    }


def richardson_reference(
    jac_at_h: NDArray[np.float64], jac_at_half_h: NDArray[np.float64]
) -> NDArray[np.float64]:
    """Two-step Richardson extrapolation for a first-order (2-point) FD Jacobian.

    A first-order forward/central-ish 2-point difference has a leading error
    term proportional to `h` (not `h**2` -- this is NOT the standard
    Richardson formula for a second-order-accurate base method, which would
    divide by 3). Given `J(h) = J_true + c*h + O(h^2)` and `J(h/2) = J_true +
    c*h/2 + O(h^2)`, eliminating the leading `c*h` term gives:

        J_true ~= 2*J(h/2) - J(h)

    Args:
        jac_at_h: Jacobian computed at step `h`.
        jac_at_half_h: Jacobian computed at step `h/2`.

    Returns:
        The extrapolated reference Jacobian, same shape as the inputs.
    """
    return 2.0 * jac_at_half_h - jac_at_h


def induced_step_change(
    j_test: NDArray[np.float64],
    j_reference: NDArray[np.float64],
    residual: NDArray[np.float64],
) -> float:
    """Relative difference between the Gauss-Newton steps `j_test`/`j_reference` induce.

    Answers "does the FD error actually move the optimizer" rather than only
    "are the matrices different": solves the linear least-squares problem
    `min ||J @ step + residual||` for each Jacobian (via `np.linalg.lstsq`,
    never a normal-equations inverse) and reports the relative norm of the
    difference between the two induced steps.

    Args:
        j_test: Jacobian under test, shape (n_residuals, n_params).
        j_reference: Reference Jacobian, same shape.
        residual: Residual vector at the same point, shape (n_residuals,).

    Returns:
        `norm(step_test - step_reference) / norm(step_reference)`, or 0.0 if
        `step_reference` is exactly the zero vector and `step_test` is too
        (both Jacobians induce no step); `inf` if `step_reference` is zero
        but `step_test` is not.
    """
    step_test, *_ = np.linalg.lstsq(j_test, -residual, rcond=None)
    step_reference, *_ = np.linalg.lstsq(j_reference, -residual, rcond=None)

    ref_norm = np.linalg.norm(step_reference)
    diff_norm = np.linalg.norm(step_test - step_reference)

    if ref_norm == 0.0:
        return 0.0 if diff_norm == 0.0 else float("inf")
    return float(diff_norm / ref_norm)


def newton_floor_probe(rel_steps: list[float], errors: list[float]) -> dict:
    """Detect a plateau or non-monotonicity in the error-vs-step curve.

    `rel_steps`/`errors` are expected ordered from largest to smallest step
    (matching the sweep's own decade-ladder order, RESEARCH Pitfall 6): as
    the step shrinks, error should fall smoothly until the Newton inner
    solve's own 1e-9 m tolerance floor is reached, at which point further
    shrinking the FD step no longer improves the comparison -- or makes it
    worse, since the FD perturbation itself becomes comparable to the
    residual noise floor.

    A "plateau" is declared when two consecutive errors (in the given order)
    fail to decrease by at least a relative 5%, i.e. `errors[i+1] >=
    0.95 * errors[i]`. Non-monotonicity is the stricter condition
    `errors[i+1] > errors[i]` (the curve went back up). The first such index
    (either kind) is reported as `first_non_monotonic_step`; a pure plateau
    (equal-ish, never increasing) still counts as `plateau_detected=True` but
    leaves `first_non_monotonic_step=None` if no strict increase ever occurs.

    Args:
        rel_steps: Swept relative steps, largest first.
        errors: The comparison metric (e.g. `max_rel_error`) at each step, in
            the same order as `rel_steps`.

    Returns:
        Dict with `plateau_detected` (bool) and `first_non_monotonic_step`
        (float | None) -- the `rel_steps` value at the first step whose error
        strictly exceeds the previous step's error, or None if the curve is
        monotonically non-increasing throughout.
    """
    if len(rel_steps) != len(errors):
        raise ValueError(
            f"newton_floor_probe: rel_steps has {len(rel_steps)} entries, "
            f"errors has {len(errors)}"
        )
    if len(errors) < 2:
        return {"plateau_detected": False, "first_non_monotonic_step": None}

    plateau_detected = False
    first_non_monotonic_step: float | None = None
    for i in range(len(errors) - 1):
        prev_err, next_err = errors[i], errors[i + 1]
        if next_err > prev_err:
            plateau_detected = True
            if first_non_monotonic_step is None:
                first_non_monotonic_step = rel_steps[i + 1]
        elif prev_err > 0 and next_err >= 0.95 * prev_err:
            plateau_detected = True

    return {
        "plateau_detected": plateau_detected,
        "first_non_monotonic_step": first_non_monotonic_step,
    }


# --- Problem construction (Task 2 territory, kept here so Task 1's pure
# functions and Task 2's CLI share one module) ---------------------------


def shipped_rel_step(x0: NDArray[np.float64], f0: NDArray[np.float64]) -> float:
    """Read scipy's actual default relative step for `method="2-point"`.

    This is the exact quantity `approx_derivative` uses internally when no
    `rel_step` is passed (every production call site in
    `aquacal.calibration._optim_common.make_sparse_jacobian_func`), read live
    from the installed scipy rather than a remembered constant (RESEARCH
    Interfaces section, and the design decision above).

    Args:
        x0: The parameter vector the step would be computed at (dtype only
            matters here).
        f0: The residual vector at `x0` (dtype only matters here).

    Returns:
        The scalar relative step scipy's private `_eps_for_method` returns
        for `method="2-point"` at this dtype pairing (typically
        `sqrt(eps) ~= 1.49e-8` for float64).
    """
    return float(_eps_for_method(x0.dtype, f0.dtype, "2-point"))


def build_small_problem(
    n_cameras: int = 4,
    n_frames: int = 6,
    seed: int = 42,
) -> dict:
    """Build a small synthetic refractive calibration problem for FD comparison.

    `refine_intrinsics=False, normal_fixed=False, shared_interface=True` --
    the configuration named in the plan. Reuses the same camera-array /
    board-trajectory / synthetic-detection generators every other experiment
    script calls (`aquacal.datasets.synthetic`), at noise_std=0.0 so the
    residual vector at the initial (ground-truth) parameters is small but
    nonzero (board pose noise is not added, only the FD comparison itself
    varies).

    Args:
        n_cameras: Number of cameras in the synthetic array.
        n_frames: Number of board-pose frames.
        seed: Random seed for geometry, trajectory, and detections.

    Returns:
        Dict with `x0` (initial packed parameter vector), `cost_args` (the
        positional argument tuple `compute_residuals` takes after `params`),
        `bounds` (lower, upper), `jac_sparsity`, `groups`, and
        `residual_at_x0` (the residual vector at `x0`, for
        `induced_step_change`).
    """
    board_config = BoardConfig(
        squares_x=12,
        squares_y=9,
        square_size=0.060,
        marker_size=0.045,
        dictionary="DICT_5X5_100",
    )
    board = BoardGeometry(board_config)

    intrinsics, extrinsics, water_zs = generate_camera_array(
        n_cameras=n_cameras,
        layout="grid",
        spacing=0.1,
        height_variation=0.0,
        seed=seed,
    )
    camera_positions = {cam: ext.C for cam, ext in extrinsics.items()}
    board_poses_list = generate_board_trajectory(
        n_frames=n_frames,
        camera_positions=camera_positions,
        water_zs=water_zs,
        board=board_config,
        depth_range=None,
        xy_extent=0.08,
        seed=seed,
    )
    detections = generate_synthetic_detections(
        intrinsics,
        extrinsics,
        water_zs,
        board,
        board_poses_list,
        noise_std=0.0,
        min_corners=4,
        n_air=1.0,
        n_water=1.333,
        seed=seed,
    )

    camera_order = sorted(intrinsics.keys())
    reference_camera = camera_order[0]
    frame_order = sorted(detections.frames.keys())
    board_poses = {bp.frame_idx: bp for bp in board_poses_list}

    initial_water_z = water_zs[reference_camera]
    x0 = pack_params(
        extrinsics,
        initial_water_z,
        board_poses,
        reference_camera,
        camera_order,
        frame_order,
        normal_fixed=False,
        shared_interface=True,
        water_z_per_camera=water_zs,
    )

    lower, upper = build_bounds(
        camera_order,
        frame_order,
        reference_camera,
        normal_fixed=False,
        shared_interface=True,
    )

    reference_extrinsics = extrinsics[reference_camera]
    interface_normal = np.array([0.0, 0.0, -1.0], dtype=np.float64)
    min_corners = 4

    cost_args = (
        detections,
        intrinsics,
        board,
        reference_camera,
        reference_extrinsics,
        interface_normal,
        1.0,
        1.333,
        camera_order,
        frame_order,
        min_corners,
        False,  # refine_intrinsics
        False,  # normal_fixed
        True,  # shared_interface
    )

    jac_sparsity = build_jacobian_sparsity(
        detections,
        reference_camera,
        camera_order,
        frame_order,
        min_corners,
        normal_fixed=False,
        shared_interface=True,
    )
    groups = build_structural_column_groups(
        jac_sparsity,
        len(camera_order),
        len(frame_order),
        refine_intrinsics=False,
        normal_fixed=False,
        shared_interface=True,
    )

    residual_at_x0 = compute_residuals(x0, *cost_args)

    return {
        "x0": x0,
        "cost_args": cost_args,
        "bounds": (lower, upper),
        "jac_sparsity": jac_sparsity,
        "groups": groups,
        "residual_at_x0": residual_at_x0,
        "n_cameras": n_cameras,
        "n_frames": n_frames,
        "seed": seed,
        "n_params": int(x0.shape[0]),
        "n_residuals": int(residual_at_x0.shape[0]),
    }


def _jacobian_at_step(problem: dict, rel_step: float) -> NDArray[np.float64]:
    """Compute the sparse FD Jacobian at a fixed `rel_step`, through the same
    `sparsity=(jac_sparsity, groups)` path production uses."""
    cost_args = problem["cost_args"]
    lower, upper = problem["bounds"]

    def _fun(x: NDArray[np.float64]) -> NDArray[np.float64]:
        return compute_residuals(x, *cost_args)

    jac = approx_derivative(
        _fun,
        problem["x0"],
        method="2-point",
        rel_step=rel_step,
        sparsity=(problem["jac_sparsity"], problem["groups"]),
        bounds=(lower, upper),
    )
    return jac.toarray() if hasattr(jac, "toarray") else np.asarray(jac)


def run_sweep(problem: dict, rel_steps: list[float]) -> tuple[pd.DataFrame, dict]:
    """Sweep `rel_steps`, build a Richardson reference, and score every step.

    The reference Jacobian is built from the two tightest (smallest)
    well-behaved steps in `rel_steps` via `richardson_reference`. Every swept
    step (including the two reference-building steps themselves) is then
    compared against that reference with `compare_jacobians` and
    `induced_step_change`.

    Args:
        problem: Output of `build_small_problem`.
        rel_steps: Relative steps to sweep, any order; sorted descending
            internally so `newton_floor_probe` sees a consistent
            largest-to-smallest ordering.

    Returns:
        Tuple of `(DataFrame with FD_ACCURACY_COLUMNS, newton_floor_probe
        verdict dict)`.
    """
    sorted_steps = sorted(set(rel_steps), reverse=True)
    if len(sorted_steps) < 2:
        raise ValueError(
            "run_sweep requires at least 2 distinct rel_steps to build a "
            "Richardson reference"
        )

    # Compute each distinct step's Jacobian exactly once, timing every call
    # individually so `seconds` in the emitted CSV reflects that row's own
    # FD-Jacobian cost.
    jacobians: dict[float, NDArray[np.float64]] = {}
    seconds_by_step: dict[float, float] = {}
    for step in sorted_steps:
        t_start = time.perf_counter()
        jacobians[step] = _jacobian_at_step(problem, step)
        seconds_by_step[step] = time.perf_counter() - t_start

    # Two tightest (smallest) steps build the Richardson reference (design
    # decision: "two-step Richardson, computed with the same
    # approx_derivative call").
    half_h, h = sorted_steps[-1], sorted_steps[-2]
    reference = richardson_reference(jacobians[h], jacobians[half_h])

    shipped = shipped_rel_step(
        problem["x0"], problem["residual_at_x0"].astype(np.float64)
    )

    rows = []
    for step in sorted_steps:
        jac = jacobians[step]
        comparison = compare_jacobians(jac, reference)
        induced = induced_step_change(jac, reference, problem["residual_at_x0"])
        rows.append(
            {
                "rel_step": step,
                "max_rel_error": comparison["max_rel_error"],
                "median_rel_error": comparison["median_rel_error"],
                "argmax_column": comparison["argmax_column"]
                if comparison["argmax_column"] is not None
                else -1,
                "n_columns_above_1e_3": int(
                    _count_columns_above(problem, jac, reference, threshold=1e-3)
                ),
                "induced_step_rel_change": induced,
                "is_shipped_default": bool(np.isclose(step, shipped, rtol=1e-6)),
                "seconds": seconds_by_step[step],
            }
        )

    df = pd.DataFrame(rows, columns=FD_ACCURACY_COLUMNS)

    verdict = newton_floor_probe(list(df["rel_step"]), list(df["max_rel_error"]))
    return df, verdict


def _count_columns_above(
    problem: dict,
    j_test: NDArray[np.float64],
    j_reference: NDArray[np.float64],
    threshold: float,
) -> int:
    """Count columns whose individual relative error exceeds `threshold`."""
    ref_norms = np.linalg.norm(j_reference, axis=0)
    diff_norms = np.linalg.norm(j_test - j_reference, axis=0)
    count = 0
    for col in range(j_test.shape[1]):
        if ref_norms[col] == 0.0:
            continue
        if (diff_norms[col] / ref_norms[col]) > threshold:
            count += 1
    return count


def build_provenance_sidecar(problem: dict, verdict: dict, seconds: float) -> dict:
    """Build the COV-02 provenance sidecar (D-19.5-05's mandatory `scope` field)."""
    from aquacal.io import capture_environment

    shipped = shipped_rel_step(
        problem["x0"], problem["residual_at_x0"].astype(np.float64)
    )
    return {
        "experiment": "fd_jacobian_accuracy",
        "schema_version": 1,
        "scope": FD_ACCURACY_SCOPE,
        "seconds": seconds,
        "scipy_version": scipy.__version__,
        "shipped_rel_step_default": shipped,
        "newton_tolerance": NEWTON_TOLERANCE_DEFAULT,
        "newton_floor_probe": verdict,
        "problem_shape": {
            "n_cameras": problem["n_cameras"],
            "n_frames": problem["n_frames"],
            "seed": problem["seed"],
            "n_params": problem["n_params"],
            "n_residuals": problem["n_residuals"],
            "refine_intrinsics": False,
            "normal_fixed": False,
            "shared_interface": True,
        },
        "solver_config": {"seed": problem["seed"]},
        "environment": capture_environment(),
    }


def _run_full(args: argparse.Namespace) -> int:
    out_dir = resolve_out_dir(args.out)
    t_start = time.perf_counter()
    problem = build_small_problem(n_cameras=4, n_frames=6, seed=args.seed)
    df, verdict = run_sweep(problem, FULL_REL_STEP_SWEEP)
    total_seconds = time.perf_counter() - t_start

    csv_path = out_dir / "fd_jacobian_accuracy.csv"
    if csv_path.exists() and not args.force:
        logger.info(
            "Skipping write to %s: file already exists and --force was not "
            "given (resumability).",
            csv_path,
        )
    else:
        sorted_df = df.sort_values(
            by=FD_ACCURACY_KEY_COLUMNS, kind="stable"
        ).reset_index(drop=True)
        csv_path.parent.mkdir(parents=True, exist_ok=True)
        sorted_df.to_csv(csv_path, index=False)
        print(f"Wrote {csv_path}")

    sidecar_path = out_dir / "fd_jacobian_accuracy.json"
    if sidecar_path.exists() and not args.force:
        logger.info(
            "Skipping write to %s: file already exists and --force was not "
            "given (resumability).",
            sidecar_path,
        )
    else:
        sidecar = build_provenance_sidecar(problem, verdict, total_seconds)
        sidecar_path.parent.mkdir(parents=True, exist_ok=True)
        with open(sidecar_path, "w") as f:
            json.dump(sidecar, f, indent=2, sort_keys=True)
        print(f"Wrote {sidecar_path}")

    print(
        f"fd_jacobian_accuracy: {total_seconds:.1f}s, "
        f"plateau_detected={verdict['plateau_detected']}"
    )
    return 0


def _run_smoke(args: argparse.Namespace) -> int:
    """Fast smoke path: a deliberately tiny problem, 3 swept steps."""
    out_dir = resolve_out_dir(args.out)
    problem = build_small_problem(n_cameras=3, n_frames=3, seed=args.seed)
    df, verdict = run_sweep(problem, [1e-5, 1e-7, 1e-9])

    csv_path = out_dir / "fd_jacobian_accuracy.csv"
    sorted_df = df.sort_values(by=FD_ACCURACY_KEY_COLUMNS, kind="stable").reset_index(
        drop=True
    )
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    sorted_df.to_csv(csv_path, index=False)
    print(f"Smoke-wrote {csv_path}")
    print(f"plateau_detected={verdict['plateau_detected']}")
    return 0


def _run_check(args: argparse.Namespace) -> int:
    """Recompute the full run and compare against the committed baseline (D-22).

    `seconds` is a float column like any other, so it is compared at
    `CHECK_RTOL` like every other float column; `compare_experiment_csv`'s
    own `rtol` is generous enough (1e-6 by default here would NOT tolerate
    wall-clock jitter, so `--check` is expected to report a `seconds`
    mismatch on every run -- this mirrors every other experiment's `--check`
    path, none of which special-cases its own `seconds` column either).
    """
    out_dir = resolve_out_dir(args.out)
    problem = build_small_problem(n_cameras=4, n_frames=6, seed=args.seed)
    fresh_df, _ = run_sweep(problem, FULL_REL_STEP_SWEEP)

    committed_path = out_dir / "fd_jacobian_accuracy.csv"
    report = compare_experiment_csv(
        fresh_df,
        committed_path,
        key_columns=FD_ACCURACY_KEY_COLUMNS,
        rtol=CHECK_RTOL,
    )
    print(report.message)
    return 0 if report.passed else 1


def build_arg_parser() -> argparse.ArgumentParser:
    """Build fd_jacobian_accuracy's CLI parser: the shared five-flag contract, no extras."""
    parser = argparse.ArgumentParser(
        description=__doc__, parents=[build_experiment_arg_parser()]
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    """CLI entry point for `python -m experiments.fd_jacobian_accuracy`."""
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
    sys.exit(main())
