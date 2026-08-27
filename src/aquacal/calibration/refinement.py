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
    build_parameter_block_slices,
    build_structural_column_groups,
    compute_residuals,
    make_sparse_jacobian_func,
    pack_params,
    unpack_params,
)
from aquacal.calibration.interface_estimation import (
    DEGENERACY_WARNING_FRACTION_THRESHOLD as _DEGENERACY_WARNING_FRACTION_THRESHOLD,
)
from aquacal.calibration.interface_estimation import (
    _format_degenerate_observation_warning,
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

#: Degenerate fraction at or above which the warning switches to its loud variant.
#: Held line-for-line parallel with the matching constant in
#: `interface_estimation.py` -- the two staying in sync is why that
#: cross-reference exists.
#:
#: **1%, and this scales WARNING VOLUME ONLY.** The `count > 0 -> degenerate` gate
#: is untouched by this constant -- no threshold, no tolerance.
#:
#: Justified by two measurements, quoted rather than paraphrased:
#:
#: - the production rig is **198 / 73,975 = 0.268%**;
#: - E1's degenerate arm logged **14,949** against a scenario with observations
#:   in the tens of thousands, i.e. tens of percent.
#:
#: Two orders of magnitude apart, so the value is not delicate. 1% is roughly 4x
#: the measured rig value and errs toward staying loud -- a rig that degraded to
#: 1% would still shout.
#:
#: 5% was rejected: a rig at 3%, a tenfold degradation, would then be reported
#: quietly, and that trend is exactly what a user would want shouted at. Making it
#: a caller parameter was also rejected -- that is the same shape as the `water_z`
#: bounds generalization this milestone deferred, i.e. source surgery days before
#: a freeze.
DEGENERACY_WARNING_FRACTION_THRESHOLD = _DEGENERACY_WARNING_FRACTION_THRESHOLD


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
    degeneracy_details_out: list[dict] | None = None,
    observation_depths_out: list[dict] | None = None,
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
        degeneracy_details_out: Optional list, purely observational, defaulting to
            None. When supplied it is EXTENDED with one row per flagged
            observation at the final solution (DEGEN-04), as produced by
            `compute_residuals`' `degeneracy_details_out` sink, with three
            columns stamped on here that the library core cannot know: `stage`
            (this call's `resolved_discard_stage`, already validated against
            `DISCARD_STAGES` at entry, so every row carries a closed-vocabulary
            label -- D-07), `n_flagged_at_stage` (the exact aggregate, taken from
            the independent counter and never from row count) and `truncated`
            (D-10, so a reader of the artifact alone can never mistake a
            row-capped table for a complete one).
        observation_depths_out: Optional list, purely observational, defaulting to
            None. The full-population twin of `degeneracy_details_out` (D-09):
            one `h_q` row per EVALUATED observation, stamped with `stage`,
            `n_observations_at_stage` and `truncated`. ~74k rows per stage on the
            production rig, hence off by default and reached only through an
            explicit config flag.

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
        parameter_labels=build_parameter_labels(
            camera_order,
            frame_order,
            reference_camera,
            refine_intrinsics=refine_intrinsics,
            normal_fixed=normal_fixed,
            shared_interface=shared_interface,
        ),
        parameter_blocks=build_parameter_block_slices(
            camera_order,
            frame_order,
            reference_camera,
            refine_intrinsics=refine_intrinsics,
            normal_fixed=normal_fixed,
            shared_interface=shared_interface,
        ),
        bounds=(lower, upper),
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
    # signatures would catch the drift. That rule now covers two more sinks --
    # `degeneracy_details_out` (one row per flagged observation, DEGEN-04) and
    # `observation_depths_out` (one row per evaluated observation, D-09) -- and
    # it binds them harder than the counters: a per-observation sink threaded
    # into the callable scipy invokes would allocate ~480M rows on E1's
    # non-refractive arm.
    invalid_counts: list[int] = []
    degeneracy_breakdown: dict[str, int] = {}
    detail_rows: list[dict] | None = [] if degeneracy_details_out is not None else None
    depth_rows: list[dict] | None = [] if observation_depths_out is not None else None
    compute_residuals(
        result.x,
        *cost_args,
        invalid_count_out=invalid_counts,
        degeneracy_breakdown_out=degeneracy_breakdown,
        degeneracy_details_out=detail_rows,
        observation_depths_out=depth_rows,
    )
    n_invalid = invalid_counts[0] if invalid_counts else 0
    # D-07 + D-10, stamped here because this is where the stage label and the
    # independently exact aggregate both live. `resolved_discard_stage` was
    # validated against `DISCARD_STAGES` at entry, so the stamp inherits the
    # closed vocabulary for free; `truncated` compares emitted rows against a
    # count that never came from `len(rows)`.
    if degeneracy_details_out is not None:
        _truncated = len(detail_rows) < n_invalid
        for _row in detail_rows:
            _row["stage"] = resolved_discard_stage
            _row["n_flagged_at_stage"] = n_invalid
            _row["truncated"] = _truncated
        degeneracy_details_out.extend(detail_rows)
    if observation_depths_out is not None:
        _n_evaluated = degeneracy_breakdown["observations_evaluated"]
        _truncated = len(depth_rows) < _n_evaluated
        for _row in depth_rows:
            _row["stage"] = resolved_discard_stage
            _row["n_observations_at_stage"] = _n_evaluated
            _row["truncated"] = _truncated
        observation_depths_out.extend(depth_rows)
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
    # D-08: no hard raise for any cause, `interface_below_camera` included. A
    # transient solver excursion must not abort a solve that converged, and the
    # suite runs unattended on a machine nobody is watching. It counts and warns
    # like the other causes; the text is what distinguishes it.
    #
    # The rendered text branches on cause AND fraction against
    # DEGENERACY_WARNING_FRACTION_THRESHOLD above, names the three real causes,
    # and keeps the two fates' consequences apart: an `extended` observation sits
    # on a pinhole continuation that is C0 but not C1 and carries zero water_z
    # gradient (every other parameter keeps full gradient), while a `penalized`
    # one carries no gradient at all. The old clause asserting that the reported
    # optimality stays a meaningful quantity for the surviving parameters must
    # not be restored -- it was measured false the same day it was written.
    if n_invalid > 0:
        warnings.warn(
            _format_degenerate_observation_warning(
                "Stage 3's intrinsic pass",
                n_invalid,
                degeneracy_breakdown,
                getattr(result, "optimality", float("nan")),
                result.status,
            ),
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
