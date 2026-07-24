"""Stage 3's second pass, with intrinsics unlocked.

This module implements the final optional refinement pass that re-optimizes
all parameters from Stage 3, with the option to also refine camera intrinsics
(focal length and principal point).
"""

import numpy as np
from scipy.optimize import least_squares

from aquacal.calibration._observability import (
    OptimizerObserver,
    SolverDiagnostics,
    build_parameter_labels,
    capture_solver_diagnostics,
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

    if result.status <= 0:
        raise ConvergenceError(f"Optimization failed: {result.message}")

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
