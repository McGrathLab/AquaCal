"""Stage 3 refractive optimization for interface estimation.

This module implements joint optimization of camera extrinsics, per-camera
interface distances, and board poses using underwater ChArUco detections.
"""

import warnings

import numpy as np
from numpy.typing import NDArray
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
from aquacal.calibration.extrinsics import _average_rotations, refractive_solve_pnp
from aquacal.config.schema import (
    BoardPose,
    CameraExtrinsics,
    CameraIntrinsics,
    ConvergenceError,
    DegenerateObservationWarning,
    DetectionResult,
    InsufficientDataError,
    Vec3,
)
from aquacal.core.board import BoardGeometry
from aquacal.utils.transforms import (
    compose_poses,
    invert_pose,
    matrix_to_rvec,
    rvec_to_matrix,
)


def _compute_initial_board_poses(
    detections: DetectionResult,
    intrinsics: dict[str, CameraIntrinsics],
    extrinsics: dict[str, CameraExtrinsics],
    board: BoardGeometry,
    min_corners: int = 4,
    water_zs: dict[str, float] | None = None,
    interface_normal: NDArray[np.float64] | None = None,
    n_air: float = 1.0,
    n_water: float = 1.333,
    discard_stats_out: dict[str, int] | None = None,
) -> dict[int, BoardPose]:
    """
    Compute initial board poses via refractive PnP for each frame.

    For each frame, uses the camera with the most detected corners to estimate
    the board pose using refractive_solve_pnp, which accounts for refraction
    at the air-water interface.

    Args:
        detections: Detection results
        intrinsics: Per-camera intrinsics
        extrinsics: Per-camera extrinsics (for transforming to world frame)
        board: Board geometry
        min_corners: Minimum corners required for PnP
        water_zs: Per-camera interface distances. If None,
            defaults to 0.15m for all cameras.
        interface_normal: Interface normal vector. If None, uses [0, 0, -1].
        n_air: Refractive index of air (default 1.0)
        n_water: Refractive index of water (default 1.333)

    Returns:
        Dict mapping frame_idx to BoardPose (in world frame)
    """
    if water_zs is None:
        water_zs = {cam: 0.15 for cam in intrinsics.keys()}

    board_poses = {}

    for frame_idx, frame_det in detections.frames.items():
        # Find camera with most corners
        best_cam = None
        best_count = 0
        for cam_name, det in frame_det.detections.items():
            if det.num_corners >= min_corners and det.num_corners > best_count:
                best_cam = cam_name
                best_count = det.num_corners

        if best_cam is None:
            _bump(discard_stats_out, "frame_no_camera_meets_min_corners")
            continue

        det = frame_det.detections[best_cam]

        result = refractive_solve_pnp(
            intrinsics[best_cam],
            det.corners_2d,
            det.corner_ids,
            board,
            water_zs.get(best_cam, 0.15),
            interface_normal,
            n_air,
            n_water,
        )
        if result is None:
            continue

        rvec_bc, tvec_bc = result

        # Transform board pose from camera frame to world frame
        # board_in_world = camera_in_world @ board_in_camera
        ext = extrinsics[best_cam]
        R_cw, t_cw = invert_pose(ext.R, ext.t)  # camera in world
        R_bc = rvec_to_matrix(rvec_bc)
        R_bw, t_bw = compose_poses(R_cw, t_cw, R_bc, tvec_bc)
        rvec_bw = matrix_to_rvec(R_bw)

        board_poses[frame_idx] = BoardPose(
            frame_idx=frame_idx,
            rvec=rvec_bw,
            tvec=t_bw,
        )

    return board_poses


def optimize_interface(
    detections: DetectionResult,
    intrinsics: dict[str, CameraIntrinsics],
    initial_extrinsics: dict[str, CameraExtrinsics],
    board: BoardGeometry,
    reference_camera: str,
    initial_water_zs: dict[str, float] | None = None,
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
) -> tuple[dict[str, CameraExtrinsics], dict[str, float], list[BoardPose], float]:
    """
    Jointly optimize camera extrinsics, interface distances, and board poses.

    This is Stage 3 of the calibration pipeline. It refines the initial estimates
    from Stage 2 by accounting for refraction at the air-water interface.

    Internally, a single global water_z parameter replaces N per-camera interface
    distances. Per-camera distances are derived as d_i = water_z - C_z_i, where
    C_z_i is the camera center's Z coordinate. This eliminates the degeneracy
    between camera height and interface distance by construction.

    Note:
        For details on the optimizer implementation and sparse Jacobian structure,
        see the :doc:`Optimizer Guide </guide/optimizer>` guide.

    Args:
        detections: Underwater ChArUco detections from detect_all_frames
        intrinsics: Per-camera intrinsic parameters (fixed during optimization)
        initial_extrinsics: Initial camera extrinsics from Stage 2
        board: ChArUco board geometry
        reference_camera: Camera name to fix at origin (extrinsics not optimized)
        initial_water_zs: Optional initial distances per camera.
            If None, defaults to 0.15m for all cameras.
        interface_normal: Interface normal vector. If None, uses [0, 0, -1].
            Normal is fixed during optimization.
        n_air: Refractive index of air (default 1.0)
        n_water: Refractive index of water (default 1.333)
        loss: Robust loss function ("linear", "huber", "soft_l1", "cauchy")
        loss_scale: Scale parameter for robust loss in pixels
        min_corners: Minimum corners per detection to include in optimization
        use_sparse_jacobian: Use sparse Jacobian structure (default True).
            Dramatically improves performance for large camera arrays.
        verbose: Verbosity level for scipy.optimize.least_squares (default 1).
            0 = silent, 1 = one-line per iteration, 2 = full per-iteration report.
        normal_fixed: If False, estimate reference camera tilt (2 DOF) to account
            for non-perpendicular camera-to-water-surface alignment.
        observer: Optional read-only observer for per-iteration tracing and
            solution-point diagnostics. Has no effect on the returned values.
        shared_interface: If True (default), all cameras share a single global
            water_z. If False (analysis/ablation only), each camera solves its
            own water_z, seeded individually from initial_water_zs; the returned
            distances dict then holds each camera's independently-solved value.
        diagnostics_out: Optional `SolverDiagnostics` instance to populate in
            place with terminal solver diagnostics (BENCH-01/BENCH-03/BENCH-06).
            Has no effect on the returned values.
        water_z_bounds: Optional `(lower, upper)` override forwarded to
            `build_bounds` for the water_z slot(s). See `build_bounds` for the
            degenerate-interval pinning mechanism (D-01). Omitting this leaves
            the default `[0.01, 2.0]` unchanged.
        discard_stage: Optional label routing this call's degeneracy counts to a
            stage-specific set of `DISCARD_KEYS` entries. Must be one of
            `DISCARD_STAGES`; `None` (the default) routes to the declared
            `"unattributed"` bucket, because an absent label is a legitimate call
            pattern (unit tests, direct calls) and must stay visible rather than
            be merged into a real stage. An unrecognized string raises
            `ValueError` at entry, before the solve.

    Returns:
        Tuple of:
        - dict[str, CameraExtrinsics]: Optimized extrinsics for all cameras
        - dict[str, float]: Optimized interface distances per camera (derived from water_z)
        - list[BoardPose]: Optimized board poses for each frame used
        - float: Final RMS reprojection error in pixels

    Raises:
        InsufficientDataError: If no valid frames for optimization
        ConvergenceError: If optimization fails to converge
        ValueError: If reference_camera not in initial_extrinsics
    """
    # Validate the discard stage label ONCE, at entry, before the solve (D-03).
    # An unrecognized string is a programming error; raising it after a
    # multi-minute solve would waste the solve. `None` maps to the declared
    # "unattributed" bucket. See the matching block in refinement.py.
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

    # Validate reference camera
    if reference_camera not in initial_extrinsics:
        raise ValueError(
            f"reference_camera '{reference_camera}' not in initial_extrinsics. "
            f"Available cameras: {list(initial_extrinsics.keys())}"
        )

    # Set default interface normal
    if interface_normal is None:
        interface_normal = np.array([0.0, 0.0, -1.0], dtype=np.float64)
    else:
        interface_normal = np.asarray(interface_normal, dtype=np.float64)

    # Set default interface distances
    if initial_water_zs is None:
        initial_water_zs = {cam: 0.15 for cam in initial_extrinsics.keys()}

    # Create ordered lists for consistent parameter packing
    camera_order = sorted(initial_extrinsics.keys())

    # Compute initial board poses
    initial_board_poses = _compute_initial_board_poses(
        detections,
        intrinsics,
        initial_extrinsics,
        board,
        min_corners,
        water_zs=initial_water_zs,
        interface_normal=interface_normal,
        n_air=n_air,
        n_water=n_water,
        discard_stats_out=discard_stats_out,
    )

    # Filter to frames with valid board poses
    frame_order = sorted(initial_board_poses.keys())

    # Check for sufficient data
    if len(frame_order) == 0:
        raise InsufficientDataError(
            "No valid frames for optimization. "
            f"Need at least {min_corners} corners per detection."
        )

    # Compute initial water_z from reference camera
    # C_z_ref = 0 since reference camera is at origin, so water_z = d_ref
    initial_water_z = initial_water_zs[reference_camera]

    # Pack initial parameters. In per-camera mode each camera is seeded from its
    # own initial_water_zs value (never collapsed to the reference camera's).
    initial_params = pack_params(
        initial_extrinsics,
        initial_water_z,
        initial_board_poses,
        reference_camera,
        camera_order,
        frame_order,
        normal_fixed=normal_fixed,
        shared_interface=shared_interface,
        water_z_per_camera=initial_water_zs,
    )

    # Build bounds
    lower, upper = build_bounds(
        camera_order,
        frame_order,
        reference_camera,
        normal_fixed=normal_fixed,
        shared_interface=shared_interface,
        water_z_bounds=water_z_bounds,
    )

    # Reference extrinsics (fixed during optimization)
    reference_extrinsics = initial_extrinsics[reference_camera]

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
        False,  # refine_intrinsics
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
            normal_fixed=normal_fixed,
            shared_interface=shared_interface,
        )
        groups = build_structural_column_groups(
            jac_sparsity,
            len(camera_order),
            len(frame_order),
            refine_intrinsics=False,
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
                refine_intrinsics=False,
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

    # Degeneracy guard. An observation the refractive model cannot project is
    # continued with a pinhole extension so the solve keeps a gradient, but the
    # model does not actually explain that observation. Historically this was
    # silent: such observations were pinned to a flat penalty, which left the
    # reprojection RMS looking publishable while first-order optimality was
    # orders of magnitude from a solution. Make it audible.
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
            f"Stage 3 finished with {n_invalid} observation(s) the refractive "
            f"model could not project (corners at or above the water surface, "
            f"or behind a camera). These were continued with a pinhole "
            f"extension, which puts the residual on a C0-but-not-C1 kink at "
            f"the refractive/pinhole boundary -- first-order optimality "
            f"({getattr(result, 'optimality', float('nan')):.4g}, termination "
            f"status {result.status}) is UNRELIABLE as a convergence measure "
            f"here, and neither it nor the reprojection RMS can be trusted to "
            f"judge convergence. Fix the scenario geometry so no corner sits "
            f"at or above the interface; do not re-tune the solver.",
            DegenerateObservationWarning,
            stacklevel=2,
        )

    if observer is not None:
        observer.on_solution(result)

    # Unpack optimized parameters
    opt_extrinsics, opt_distances, opt_board_poses, _ = unpack_params(
        result.x,
        reference_camera,
        reference_extrinsics,
        camera_order,
        frame_order,
        normal_fixed=normal_fixed,
        shared_interface=shared_interface,
    )

    # Compute final RMS error
    rms_error = np.sqrt(np.mean(result.fun**2))

    # Convert board_poses dict to list
    board_poses_list = [opt_board_poses[frame_idx] for frame_idx in frame_order]

    return opt_extrinsics, opt_distances, board_poses_list, rms_error


def _multi_frame_pnp_init(
    obs_frames: list[tuple[int, NDArray[np.int32], NDArray[np.float64]]],
    board_poses: dict[int, BoardPose],
    intrinsics: CameraIntrinsics,
    board: BoardGeometry,
    water_z: float,
    interface_normal: NDArray[np.float64],
    n_air: float,
    n_water: float,
    top_n: int = 10,
    outlier_threshold: float = 0.5,
    discard_stats_out: dict[str, int] | None = None,
) -> tuple[NDArray[np.float64], NDArray[np.float64]] | None:
    """Multi-frame PnP initialization for robust camera pose estimation.

    Runs refractive PnP on multiple frames, filters outliers based on C_z,
    and returns a weighted average pose. This is more robust than single-frame
    PnP for overhead cameras where depth is ill-conditioned.

    Args:
        obs_frames: List of (frame_idx, corner_ids, corners_2d) tuples
        board_poses: Fixed board poses from Stage 3 (frame_idx -> BoardPose)
        intrinsics: Camera intrinsic parameters
        board: Board geometry
        water_z: Global water surface Z from Stage 3
        interface_normal: Interface normal vector
        n_air: Refractive index of air
        n_water: Refractive index of water
        top_n: Number of top frames to use (by corner count)
        outlier_threshold: Maximum deviation from median C_z in meters

    Returns:
        Tuple of (rvec, tvec) in world frame, or None if all frames fail
    """
    # Sort frames by corner count and take top N
    sorted_frames = sorted(obs_frames, key=lambda x: len(x[1]), reverse=True)
    selected_frames = sorted_frames[:top_n]

    # Run PnP on each frame and collect results
    pnp_results = []
    for frame_idx, corner_ids, corners_2d in selected_frames:
        pnp_result = refractive_solve_pnp(
            intrinsics,
            corners_2d,
            corner_ids,
            board,
            water_z,
            interface_normal,
            n_air,
            n_water,
            discard_stats_out=discard_stats_out,
        )

        if pnp_result is None:
            _bump(discard_stats_out, "interface_pnp_failed")
            continue

        rvec_bc, tvec_bc = pnp_result

        # Transform to world frame
        bp = board_poses[frame_idx]
        R_bw = rvec_to_matrix(bp.rvec)
        R_bc = rvec_to_matrix(rvec_bc)
        R_wb, t_wb = invert_pose(R_bw, bp.tvec)
        R_wc, t_wc = compose_poses(R_bc, tvec_bc, R_wb, t_wb)

        # Compute camera center in world frame
        C = -R_wc.T @ t_wc
        C_z = C[2]

        num_corners = len(corner_ids)
        pnp_results.append((R_wc, t_wc, C_z, num_corners))

    if len(pnp_results) == 0:
        return None

    # Filter outliers based on C_z
    C_z_values = np.array([r[2] for r in pnp_results])
    median_C_z = np.median(C_z_values)

    filtered_results = []
    for R_wc, t_wc, C_z, num_corners in pnp_results:
        if abs(C_z - median_C_z) <= outlier_threshold:
            filtered_results.append((R_wc, t_wc, num_corners))

    # Fallback: if all filtered out, use the one closest to median
    if len(filtered_results) == 0:
        closest_idx = np.argmin(np.abs(C_z_values - median_C_z))
        R_wc, t_wc, C_z, num_corners = pnp_results[closest_idx]
        return matrix_to_rvec(R_wc), t_wc

    # Fallback: if only one survives, use it
    if len(filtered_results) == 1:
        R_wc, t_wc, _ = filtered_results[0]
        return matrix_to_rvec(R_wc), t_wc

    # Average rotations and translations, weighted by corner count
    rotations = [r[0] for r in filtered_results]
    translations = [r[1] for r in filtered_results]
    weights = [float(r[2]) for r in filtered_results]

    # Normalize weights
    total_weight = sum(weights)
    normalized_weights = [w / total_weight for w in weights]

    # Average rotation using weighted chordal L2 mean
    R_avg = _average_rotations(rotations, normalized_weights)

    # Average translation with same weights
    t_avg = np.zeros(3, dtype=np.float64)
    for t, w in zip(translations, normalized_weights):
        t_avg += w * t

    return matrix_to_rvec(R_avg), t_avg


def register_auxiliary_camera(
    camera_name: str,
    intrinsics: CameraIntrinsics,
    detections: DetectionResult,
    board_poses: dict[int, BoardPose],
    board: BoardGeometry,
    water_z: float,
    interface_normal: Vec3 | None = None,
    n_air: float = 1.0,
    n_water: float = 1.333,
    min_corners: int = 4,
    refine_intrinsics: bool = False,
    verbose: int = 0,
    diagnostics_out: SolverDiagnostics | None = None,
    discard_stats_out: dict[str, int] | None = None,
) -> (
    tuple[CameraExtrinsics, float, float]
    | tuple[CameraExtrinsics, float, float, CameraIntrinsics]
):
    """Register a single auxiliary camera against fixed board poses.

    Estimates the camera's extrinsics by minimizing refractive reprojection
    error against known board poses from Stage 3. The interface distance is
    derived from the known global water_z and the camera's Z position:
    d = water_z - C_z. This is a 6-parameter problem (extrinsics only)
    with no degeneracy. Optionally refines intrinsics (fx, fy, cx, cy) for
    a 10-parameter optimization.

    Args:
        camera_name: Name of the auxiliary camera
        intrinsics: Camera intrinsic parameters (initial values, refined if refine_intrinsics=True)
        detections: Full detection results (must contain this camera's detections)
        board_poses: Fixed board poses from Stage 3 (frame_idx -> BoardPose)
        board: Board geometry
        water_z: Global water surface Z from Stage 3 (required)
        interface_normal: Interface normal (default [0, 0, -1])
        n_air: Refractive index of air
        n_water: Refractive index of water
        min_corners: Minimum corners per detection
        refine_intrinsics: If True, also optimize fx, fy, cx, cy (10 params total).
            Distortion coefficients are kept fixed.
        verbose: Verbosity level
        diagnostics_out: Optional `SolverDiagnostics` instance to populate in
            place with terminal solver diagnostics (BENCH-01). This site does
            not set explicit tolerances (not a BENCH-06 target, D-11); `n_params`
            and `n_groups` stay `None` with a stated reason since this site uses
            no column-grouping structure. Has no effect on the returned values.

    Returns:
        When refine_intrinsics=False: Tuple of (extrinsics, water_z, rms_error)
        When refine_intrinsics=True: Tuple of (extrinsics, water_z, rms_error, refined_intrinsics)

    Raises:
        InsufficientDataError: If no usable frames found
    """
    from aquacal.core.camera import create_camera
    from aquacal.core.interface_model import Interface
    from aquacal.core.refractive_geometry import refractive_project

    if interface_normal is None:
        interface_normal = np.array([0.0, 0.0, -1.0], dtype=np.float64)
    else:
        interface_normal = np.asarray(interface_normal, dtype=np.float64)

    # --- Step 1: Collect observations ---
    obs_frames = []
    total_corners = 0

    for frame_idx, frame_det in detections.frames.items():
        if camera_name not in frame_det.detections:
            continue
        if frame_idx not in board_poses:
            continue
        det = frame_det.detections[camera_name]
        if det.num_corners < min_corners:
            continue
        obs_frames.append((frame_idx, det.corner_ids, det.corners_2d))
        total_corners += det.num_corners

    if len(obs_frames) == 0:
        raise InsufficientDataError(
            f"No usable frames for auxiliary camera '{camera_name}'. "
            f"Need frames with both detections (>={min_corners} corners) "
            f"and existing board poses."
        )

    # --- Step 2: Initial guess via multi-frame refractive PnP ---
    pnp_result = _multi_frame_pnp_init(
        obs_frames,
        board_poses,
        intrinsics,
        board,
        water_z,
        interface_normal,
        n_air,
        n_water,
        discard_stats_out=discard_stats_out,
    )

    if pnp_result is None:
        raise InsufficientDataError(
            f"Multi-frame refractive PnP failed for auxiliary camera '{camera_name}'. "
            f"Tried {len(obs_frames)} frames but all PnP attempts failed."
        )

    initial_rvec, initial_tvec = pnp_result

    # --- Step 3: Build parameter vector ---
    if refine_intrinsics:
        # [rvec(3), tvec(3), fx, fy, cx, cy] = 10 params
        x0 = np.concatenate(
            [
                initial_rvec,
                initial_tvec,
                [
                    intrinsics.K[0, 0],
                    intrinsics.K[1, 1],
                    intrinsics.K[0, 2],
                    intrinsics.K[1, 2],
                ],
            ]
        )
    else:
        # [rvec(3), tvec(3)] = 6 params (extrinsics only)
        x0 = np.concatenate([initial_rvec, initial_tvec])

    # --- Step 4: Residual function ---
    def residuals(x):
        rvec = x[:3]
        tvec = x[3:6]

        # Build camera intrinsics (refined or original)
        if refine_intrinsics:
            fx, fy, cx, cy = x[6], x[7], x[8], x[9]
            K_refined = intrinsics.K.copy()
            K_refined[0, 0] = fx
            K_refined[1, 1] = fy
            K_refined[0, 2] = cx
            K_refined[1, 2] = cy
            camera_intrinsics = CameraIntrinsics(
                K=K_refined,
                dist_coeffs=intrinsics.dist_coeffs,
                image_size=intrinsics.image_size,
                is_fisheye=intrinsics.is_fisheye,
            )
        else:
            camera_intrinsics = intrinsics

        R = rvec_to_matrix(rvec)
        ext = CameraExtrinsics(R=R, t=tvec)
        # Interface distance is the water surface Z-coordinate
        iface_dist = water_z

        camera = create_camera(camera_name, camera_intrinsics, ext)
        interface = Interface(
            normal=interface_normal,
            camera_distances={camera_name: iface_dist},
            n_air=n_air,
            n_water=n_water,
        )

        resid = []
        for frame_idx, corner_ids, corners_2d in obs_frames:
            bp = board_poses[frame_idx]
            corners_3d = board.transform_corners(bp.rvec, bp.tvec)

            for i, cid in enumerate(corner_ids):
                pt_3d = corners_3d[int(cid)]
                projected = refractive_project(camera, interface, pt_3d)
                if projected is not None:
                    resid.append(projected[0] - corners_2d[i, 0])
                    resid.append(projected[1] - corners_2d[i, 1])
                else:
                    resid.append(100.0)
                    resid.append(100.0)

        return np.array(resid, dtype=np.float64)

    # --- Step 5: Bounds ---
    if refine_intrinsics:
        # Add bounds for fx, fy, cx, cy
        fx0, fy0 = intrinsics.K[0, 0], intrinsics.K[1, 1]
        w, h = intrinsics.image_size
        lower = np.array([-np.inf] * 6 + [0.5 * fx0, 0.5 * fy0, 0.0, 0.0])
        upper = np.array([np.inf] * 6 + [2.0 * fx0, 2.0 * fy0, float(w), float(h)])
    else:
        # All unbounded for 6-param extrinsics
        lower = np.full(6, -np.inf)
        upper = np.full(6, np.inf)

    # --- Step 6: Optimize ---
    result = least_squares(
        residuals,
        x0=x0,
        method="trf",
        loss="huber",
        f_scale=1.0,
        bounds=(lower, upper),
        verbose=verbose,
    )

    capture_solver_diagnostics(
        result,
        diagnostics_out,
        ftol=1e-8,
        xtol=1e-8,
        gtol=1e-8,
        max_nfev_effective=len(x0) * 100,
        max_nfev_source="scipy_auto",
        n_params=None,
        n_groups=None,
        n_params_reason=(
            "register_auxiliary_camera uses dense 2-point FD; no "
            "column-grouping structure exists at this site"
        ),
        n_groups_reason=(
            "register_auxiliary_camera uses dense 2-point FD; no "
            "column-grouping structure exists at this site"
        ),
        n_residuals=None,
        n_residuals_reason=(
            "register_auxiliary_camera uses dense 2-point FD; no "
            "column-grouping structure exists at this site"
        ),
    )

    # --- Step 7: Extract results ---
    opt_rvec = result.x[:3]
    opt_tvec = result.x[3:6]

    opt_R = rvec_to_matrix(opt_rvec)
    opt_extrinsics = CameraExtrinsics(R=opt_R, t=opt_tvec)

    # Derive final interface distance (water surface Z-coordinate)
    opt_iface_dist = float(water_z)

    rms_error = float(np.sqrt(np.mean(result.fun**2)))

    if refine_intrinsics:
        # Extract refined intrinsics
        fx, fy, cx, cy = result.x[6], result.x[7], result.x[8], result.x[9]
        K_refined = intrinsics.K.copy()
        K_refined[0, 0] = fx
        K_refined[1, 1] = fy
        K_refined[0, 2] = cx
        K_refined[1, 2] = cy
        refined_intrinsics = CameraIntrinsics(
            K=K_refined,
            dist_coeffs=intrinsics.dist_coeffs,
            image_size=intrinsics.image_size,
            is_fisheye=intrinsics.is_fisheye,
        )
        return opt_extrinsics, opt_iface_dist, rms_error, refined_intrinsics
    else:
        return opt_extrinsics, opt_iface_dist, rms_error
