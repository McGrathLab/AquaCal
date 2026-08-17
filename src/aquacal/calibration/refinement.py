"""Stage 3's second pass, with intrinsics unlocked.

This module implements the final optional refinement pass that re-optimizes
all parameters from Stage 3, with the option to also refine camera intrinsics
(focal length and principal point).
"""

import warnings

import numpy as np
from scipy.optimize import least_squares

from aquacal.calibration._observability import (
    DEGENERACY_CAUSES,
    DEGENERACY_FATES,
    DISCARD_STAGES,
    OptimizerObserver,
    SolverDiagnostics,
    _bump,
    build_parameter_labels,
    capture_solver_diagnostics,
    degeneracy_cause_key,
    degeneracy_fate_key,
    observations_evaluated_key,
)
from aquacal.calibration._optim_common import (
    build_bounds,
    build_jacobian_sparsity,
    build_structural_column_groups,
    compute_residuals,
    make_sparse_jacobian_func,
    pack_params,
    unpack_params,
)
from aquacal.config.schema import (
    BoardPose,
    CameraExtrinsics,
    CameraIntrinsics,
    ConvergenceError,
    DegenerateObservationWarning,
    DetectionResult,
    Vec3,
)
from aquacal.core.board import BoardGeometry


def joint_refinement(
    stage3_result: tuple[
        dict[str, CameraExtrinsics],
        dict[str, float],
        list[BoardPose],
        float,
    ],
    detections: DetectionResult,
    intrinsics: dict[str, CameraIntrinsics],
    board: BoardGeometry,
    reference_camera: str,
    refine_intrinsics: bool = False,
    interface_normal: Vec3 | None = None,
    n_air: float = 1.0,
    n_water: float = 1.333,
    loss: str = "huber",
    loss_scale: float = 1.0,
    min_corners: int = 4,
    use_sparse_jacobian: bool = True,
    verbose: int = 1,
    normal_fixed: bool = True,
    observer: OptimizerObserver | None = None,
    shared_interface: bool = True,
    diagnostics_out: SolverDiagnostics | None = None,
    discard_stats_out: dict[str, int] | None = None,
    water_z_bounds: tuple[float, float] | None = None,
    discard_stage: str | None = None,
) -> tuple[
    dict[str, CameraExtrinsics],
    dict[str, float],
    list[BoardPose],
    dict[str, CameraIntrinsics],
    float,
]:
    """
    Jointly refine all calibration parameters, optionally including intrinsics.

    This is Stage 3's second pass, with intrinsics unlocked. It takes the output
    of Stage 3's first pass and performs additional optimization. When
    refine_intrinsics=True, it also optimizes focal lengths and principal points.

    Args:
        stage3_result: Output tuple from optimize_interface:
            (extrinsics, water_zs, board_poses, rms_error)
        detections: Underwater ChArUco detections
        intrinsics: Per-camera intrinsic parameters (used as initial values)
        board: ChArUco board geometry
        reference_camera: Camera name fixed at origin
        refine_intrinsics: If True, also optimize fx, fy, cx, cy per camera
        interface_normal: Interface normal vector. If None, uses [0, 0, -1].
        n_air: Refractive index of air
        n_water: Refractive index of water
        loss: Robust loss function ("linear", "huber", "soft_l1", "cauchy")
        loss_scale: Scale parameter for robust loss in pixels
        min_corners: Minimum corners per detection to include
        use_sparse_jacobian: Use sparse Jacobian structure (default True).
            Dramatically improves performance for large parameter counts.
        verbose: Verbosity level for scipy.optimize.least_squares (default 0).
            0 = silent, 1 = one-line per iteration, 2 = full per-iteration report.
        normal_fixed: If False, estimate reference camera tilt (2 DOF) to account
            for non-perpendicular camera-to-water-surface alignment.
        observer: Optional read-only observer for per-iteration tracing and
            solution-point diagnostics. Has no effect on the returned values.
        shared_interface: If True (default), all cameras share a single global
            water_z. If False (analysis/ablation only), each camera refines its
            own water_z, seeded individually from the Stage-3 per-camera
            distances (never collapsed to the reference camera's value).
        diagnostics_out: Optional `SolverDiagnostics` out-parameter. If provided,
            populated in place after `least_squares` returns with terminal
            solver diagnostics (nfev, njev, cost, optimality, status, message,
            the explicit ftol/xtol/gtol, max_nfev's effective value, and
            P/n_groups when `use_sparse_jacobian=True`). Has no effect on the
            returned values. Default None (no capture).
        discard_stats_out: Optional counter dict populated in place with the
            same final-solution degeneracy guard count `optimize_interface`
            records (plan 19.3-02, D-19.3-11). Bumped unconditionally after
            the guard's post-solve `compute_residuals` call, so a clean run
            records an explicit 0 rather than an absent key. `None` (the
            default) disables accounting entirely; has no effect on the
            returned values.
        water_z_bounds: Optional `(lower, upper)` override forwarded to
            `build_bounds` for the water_z slot(s). Omitting this here while
            passing it to `optimize_interface` leaves `water_z` free during
            this intrinsic-refinement pass — measured 2026-08-17: a pin held
            through Stage 3's first pass drifted from 1.031 m to 0.0425 m by
            the end of this pass when the override was not also threaded
            here. See `build_bounds` for the degenerate-interval mechanism
            (D-01).
        discard_stage: Optional label routing this call's degeneracy counts to a
            stage-specific set of `DISCARD_KEYS` entries. Must be one of
            `DISCARD_STAGES`; `None` (the default) routes to the declared
            `"unattributed"` bucket. An unrecognized string raises `ValueError`
            at entry, before the solve.

            **The stage cannot be derived, which is why it is an explicit
            argument (D-02).** This one function bumps under two different stage
            identities -- Stage 3 joint and Stage 3's intrinsic pass are the same
            function, called twice. `OptimizerObserver.stage` already carries this
            vocabulary, but the observer is opt-in and `None` on an ordinary run,
            so deriving the label from it would silently collapse the split for
            every production run the counter exists for.

    Returns:
        Tuple of:
        - dict[str, CameraExtrinsics]: Refined extrinsics for all cameras
        - dict[str, float]: Refined interface distances per camera (derived from water_z)
        - list[BoardPose]: Refined board poses
        - dict[str, CameraIntrinsics]: Refined intrinsics (modified if refine_intrinsics=True,
          otherwise copies of input)
        - float: Final RMS reprojection error in pixels

    Raises:
        ConvergenceError: If optimization fails to converge
        ValueError: If reference_camera not in stage3_result extrinsics

    Notes:
        - When refine_intrinsics=False, this is essentially re-running Stage 3
          optimization from the Stage 3 solution (useful for verifying convergence)
        - Distortion coefficients are NOT refined (kept fixed)
        - Intrinsic bounds: fx, fy in [0.5*initial, 2.0*initial],
          cx, cy in [0, image_width] and [0, image_height]
    """
    # Validate the discard stage label ONCE, at entry, before the solve (D-03).
    # An unrecognized string is a programming error; raising it after a
    # multi-minute solve would waste the solve. `None` maps to the declared
    # "unattributed" bucket. See the matching block in interface_estimation.py.
    resolved_discard_stage = (
        discard_stage if discard_stage is not None else ("unattributed")
    )
    if resolved_discard_stage not in DISCARD_STAGES:
        raise ValueError(
            f"unrecognized discard_stage {discard_stage!r}; legal stages are "
            f"{list(DISCARD_STAGES)} (or None for {'unattributed'!r})"
        )
    # D-04: emit this stage's degeneracy keys at zero up front, so a clean run
    # produces an explicit zero rather than no key at all -- a zero that is
    # present is evidence, a column that is absent is not. `_bump(..., n=0)`
    # creates the key at 0 if absent, and the inert path is preserved exactly:
    # when `discard_stats_out is None` there is no dict and no keys.
    for _cause in DEGENERACY_CAUSES:
        _bump(
            discard_stats_out, degeneracy_cause_key(_cause, resolved_discard_stage), 0
        )
    for _fate in DEGENERACY_FATES:
        _bump(discard_stats_out, degeneracy_fate_key(_fate, resolved_discard_stage), 0)
    _bump(discard_stats_out, observations_evaluated_key(resolved_discard_stage), 0)
    _bump(discard_stats_out, "degenerate_observations_at_solution", 0)

    # Validate inputs
    extrinsics_in, distances_in, poses_in, _ = stage3_result
    if reference_camera not in extrinsics_in:
        raise ValueError(
            f"reference_camera '{reference_camera}' not in stage3_result extrinsics. "
            f"Available cameras: {list(extrinsics_in.keys())}"
        )

    # Setup
    if interface_normal is None:
        interface_normal = np.array([0.0, 0.0, -1.0], dtype=np.float64)
    else:
        interface_normal = np.asarray(interface_normal, dtype=np.float64)

    camera_order = sorted(extrinsics_in.keys())
    board_poses_dict = {bp.frame_idx: bp for bp in poses_in}
    frame_order = sorted(board_poses_dict.keys())

    if not frame_order:
        raise ConvergenceError("No board poses from Stage 3")

    reference_extrinsics = extrinsics_in[reference_camera]

    # Compute water_z from Stage 3 output
    # C_z_ref = 0 since reference camera is at origin, so water_z = d_ref
    water_z = extrinsics_in[reference_camera].C[2] + distances_in[reference_camera]

    # Pack initial parameters. In per-camera mode each camera is seeded from its
    # own Stage-3 water_z (distances_in), never collapsed to the reference.
    initial_params = pack_params(
        extrinsics_in,
        water_z,
        board_poses_dict,
        reference_camera,
        camera_order,
        frame_order,
        intrinsics=intrinsics,
        refine_intrinsics=refine_intrinsics,
        normal_fixed=normal_fixed,
        shared_interface=shared_interface,
        water_z_per_camera=distances_in,
    )

    # Build bounds
    lower, upper = build_bounds(
        camera_order,
        frame_order,
        reference_camera,
        base_intrinsics=intrinsics,
        refine_intrinsics=refine_intrinsics,
        normal_fixed=normal_fixed,
        shared_interface=shared_interface,
        water_z_bounds=water_z_bounds,
    )

    # Build cost function args
    cost_args = (
        detections,
        intrinsics,
        board,
        reference_camera,
        reference_extrinsics,
        interface_normal,
        n_air,
        n_water,
        camera_order,
        frame_order,
        min_corners,
        refine_intrinsics,
        normal_fixed,
        shared_interface,
    )

    # Build sparse Jacobian if enabled
    jac = "2-point"
    jac_sparsity = None
    groups = None
    if use_sparse_jacobian:
        jac_sparsity = build_jacobian_sparsity(
            detections,
            reference_camera,
            camera_order,
            frame_order,
            min_corners,
            refine_intrinsics=refine_intrinsics,
            normal_fixed=normal_fixed,
            shared_interface=shared_interface,
        )
        groups = build_structural_column_groups(
            jac_sparsity,
            len(camera_order),
            len(frame_order),
            refine_intrinsics=refine_intrinsics,
            normal_fixed=normal_fixed,
            shared_interface=shared_interface,
        )
        jac = make_sparse_jacobian_func(
            compute_residuals,
            cost_args,
            jac_sparsity,
            (lower, upper),
            groups=groups,
        )

    # Run optimization
    ls_kwargs = {}
    if observer is not None:
        observer.configure_layout(
            water_z_index=(0 if normal_fixed else 2) + 6 * (len(camera_order) - 1),
            normal_fixed=normal_fixed,
            parameter_labels=build_parameter_labels(
                camera_order,
                frame_order,
                reference_camera,
                refine_intrinsics=refine_intrinsics,
                normal_fixed=normal_fixed,
                shared_interface=shared_interface,
            ),
        )
        cost_func = observer.wrap_fun(compute_residuals)
        jac = observer.wrap_jac(jac)
        ls_kwargs["callback"] = observer.callback
    else:
        cost_func = compute_residuals

    result = least_squares(
        cost_func,
        x0=initial_params,
        args=cost_args,
        method="trf",
        loss=loss,
        f_scale=loss_scale,
        bounds=(lower, upper),
        jac=jac,
        verbose=verbose,
        ftol=1e-8,
        xtol=1e-8,
        gtol=1e-8,
        **ls_kwargs,
    )

    # Capture diagnostics BEFORE the convergence check so a failed solve still
    # records nfev/cost/status/message — matching optimize_interface's ordering.
    # Capturing after the raise would silently drop diagnostics for exactly the
    # runs (non-convergence) where they are most diagnostic.
    capture_solver_diagnostics(
        result,
        diagnostics_out,
        ftol=1e-8,
        xtol=1e-8,
        gtol=1e-8,
        max_nfev_effective=len(initial_params) * 100,
        max_nfev_source="scipy_auto",
        n_params=jac_sparsity.shape[1] if use_sparse_jacobian else None,
        n_groups=(int(groups.max()) + 1) if use_sparse_jacobian else None,
        n_params_reason=(
            None
            if use_sparse_jacobian
            else "use_sparse_jacobian=False; no column-grouping structure was built"
        ),
        n_groups_reason=(
            None
            if use_sparse_jacobian
            else "use_sparse_jacobian=False; no column-grouping structure was built"
        ),
        n_residuals=jac_sparsity.shape[0] if use_sparse_jacobian else None,
        n_residuals_reason=(
            None
            if use_sparse_jacobian
            else "use_sparse_jacobian=False; no column-grouping structure was built"
        ),
    )

    if result.status <= 0:
        raise ConvergenceError(f"Optimization failed: {result.message}")

    # Degeneracy guard -- see the matching block in interface_estimation.
    #
    # D-06b: this `compute_residuals` call already runs AFTER `least_squares`
    # returns, and every diagnostic out-parameter is threaded here and ONLY here.
    # Nothing below is added to `cost_args` and nothing is threaded into the
    # callable scipy invokes -- doing so would allocate a reason array on every
    # one of thousands of residual evaluations, and nothing in the type
    # signatures would catch the drift.
    invalid_counts: list[int] = []
    degeneracy_breakdown: dict[str, int] = {}
    compute_residuals(
        result.x,
        *cost_args,
        invalid_count_out=invalid_counts,
        degeneracy_breakdown_out=degeneracy_breakdown,
    )
    n_invalid = invalid_counts[0] if invalid_counts else 0
    for _cause in DEGENERACY_CAUSES:
        _bump(
            discard_stats_out,
            degeneracy_cause_key(_cause, resolved_discard_stage),
            degeneracy_breakdown[_cause],
        )
    for _fate in DEGENERACY_FATES:
        _bump(
            discard_stats_out,
            degeneracy_fate_key(_fate, resolved_discard_stage),
            degeneracy_breakdown[_fate],
        )
    _bump(
        discard_stats_out,
        observations_evaluated_key(resolved_discard_stage),
        degeneracy_breakdown["observations_evaluated"],
    )
    # The merged key is retained unchanged so the production gate and
    # check_rerun_gates.py keep reading the same number.
    _bump(discard_stats_out, "degenerate_observations_at_solution", n_invalid)
    if n_invalid > 0:
        warnings.warn(
            f"Stage 3's intrinsic pass finished with {n_invalid} observation(s) "
            f"the refractive model could not project (corners at or above the "
            f"water surface, or behind a camera). These were continued with a "
            f"pinhole extension, which puts the residual on a C0-but-not-C1 "
            f"kink at the refractive/pinhole boundary -- first-order "
            f"optimality ({getattr(result, 'optimality', float('nan')):.4g}, "
            f"termination status {result.status}) is UNRELIABLE as a "
            f"convergence measure here, and neither it nor the reprojection "
            f"RMS can be trusted to judge convergence. Fix the scenario "
            f"geometry so no corner sits at or above the interface; do not "
            f"re-tune the solver.",
            DegenerateObservationWarning,
            stacklevel=2,
        )

    if observer is not None:
        observer.on_solution(result)

    # Unpack results
    ext_out, dist_out, poses_out, intr_out = unpack_params(
        result.x,
        reference_camera,
        reference_extrinsics,
        camera_order,
        frame_order,
        base_intrinsics=intrinsics,
        refine_intrinsics=refine_intrinsics,
        normal_fixed=normal_fixed,
        shared_interface=shared_interface,
    )

    # Convert board poses dict to sorted list
    poses_list = [poses_out[idx] for idx in sorted(poses_out.keys())]

    rms_error = np.sqrt(np.mean(result.fun**2))

    return ext_out, dist_out, poses_list, intr_out, rms_error
