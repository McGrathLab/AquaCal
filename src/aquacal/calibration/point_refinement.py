"""Point correspondence refinement for existing calibrations.

Provides refine_calibration(), which performs bundle adjustment over extrinsics
and water_z using 3D-to-2D point correspondences supplied by downstream consumers.
Optionally refines camera intrinsics (fx, fy, cx, cy), reference camera tilt,
and supports robust loss functions (Huber/Cauchy) for outlier tolerance.
"""

from __future__ import annotations

import copy
import logging
from typing import TYPE_CHECKING

import numpy as np
from numpy.typing import NDArray
from scipy.optimize import least_squares

from aquacal.calibration._optim_common import make_sparse_jacobian_func
from aquacal.calibration.validation import (
    build_validation_report,
    compute_extrinsics_drift,
    compute_holdout_reproj_error,
    compute_triangulation_consistency,
    split_holdout,
)
from aquacal.config.schema import (
    CalibrationResult,
    CameraCalibration,
    CameraExtrinsics,
    CameraIntrinsics,
    DiagnosticsData,
    InsufficientDataError,
    PointCorrespondence,
    RefinementResult,
)
from aquacal.core.camera import create_camera
from aquacal.core.interface_model import Interface
from aquacal.core.refractive_geometry import refractive_project_batch
from aquacal.utils.transforms import matrix_to_rvec, rvec_to_matrix

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)

# Minimum number of active (non-zero weight) correspondences required
_MIN_CORRESPONDENCES = 10

# Valid loss function names for scipy.optimize.least_squares
_VALID_LOSSES = {"linear", "huber", "cauchy"}

# Threshold for logging intrinsic drift warnings (5% of initial value)
_INTRINSIC_DRIFT_WARN_PCT = 0.05


def _pack_refine_params(
    extrinsics: dict[str, CameraExtrinsics],
    water_z: float,
    reference_camera: str,
    camera_order: list[str],
    intrinsics: dict[str, CameraIntrinsics] | None = None,
    refine_intrinsics: bool = False,
    normal_fixed: bool = True,
) -> NDArray[np.float64]:
    """Pack optimization parameters into a 1D array.

    Parameter layout:
    - If not normal_fixed: reference camera tilt rx, ry (2)
    - For each non-reference camera (sorted order, skip reference): rvec (3), tvec (3)
    - water_z (1): single shared parameter
    - If refine_intrinsics, for each camera in camera_order: fx (1), fy (1), cx (1), cy (1)

    Args:
        extrinsics: Camera extrinsics dict.
        water_z: Global water surface Z coordinate.
        reference_camera: Name of reference camera (skipped in extrinsics packing).
        camera_order: Ordered list of camera names.
        intrinsics: Per-camera intrinsics (required if refine_intrinsics=True).
        refine_intrinsics: Whether to include intrinsics in parameter vector.
        normal_fixed: If False, prepend 2 tilt params (rx, ry) for reference camera.

    Returns:
        1D parameter vector.
    """
    params: list[float] = []

    # Pack reference camera tilt (if estimating)
    if not normal_fixed:
        rvec = matrix_to_rvec(extrinsics[reference_camera].R)
        params.extend(rvec[:2].tolist())

    for cam_name in camera_order:
        if cam_name == reference_camera:
            continue
        ext = extrinsics[cam_name]
        rvec = matrix_to_rvec(ext.R)
        params.extend(rvec.tolist())
        params.extend(ext.t.tolist())

    params.append(water_z)

    # Pack intrinsics if refining
    if refine_intrinsics:
        for cam_name in camera_order:
            K = intrinsics[cam_name].K
            params.extend([K[0, 0], K[1, 1], K[0, 2], K[1, 2]])

    return np.array(params, dtype=np.float64)


def _unpack_refine_params(
    params: NDArray[np.float64],
    reference_camera: str,
    reference_extrinsics: CameraExtrinsics,
    camera_order: list[str],
    base_intrinsics: dict[str, CameraIntrinsics] | None = None,
    refine_intrinsics: bool = False,
    normal_fixed: bool = True,
) -> tuple[dict[str, CameraExtrinsics], float, dict[str, CameraIntrinsics]]:
    """Unpack 1D parameter array into extrinsics dict, water_z, and intrinsics.

    Args:
        params: 1D parameter vector.
        reference_camera: Name of reference camera.
        reference_extrinsics: Fixed extrinsics for reference camera (used when
            normal_fixed=True; ignored when False since tilt comes from params).
        camera_order: Ordered list of camera names.
        base_intrinsics: Base intrinsics (for dist_coeffs and image_size).
            Required if refine_intrinsics=True.
        refine_intrinsics: Whether intrinsics are included in params.
        normal_fixed: If False, first 2 params are tilt (rx, ry) for reference camera.

    Returns:
        Tuple of (extrinsics_dict, water_z, intrinsics_dict).
        When refine_intrinsics=False, intrinsics_dict is empty.
    """
    idx = 0

    # Unpack reference camera tilt (if estimating)
    if not normal_fixed:
        rx, ry = params[0], params[1]
        idx = 2
        R_ref = rvec_to_matrix(np.array([rx, ry, 0.0]))
        ref_ext = CameraExtrinsics(R=R_ref, t=np.zeros(3, dtype=np.float64))
    else:
        ref_ext = reference_extrinsics

    extrinsics_out: dict[str, CameraExtrinsics] = {}

    for cam_name in camera_order:
        if cam_name == reference_camera:
            extrinsics_out[cam_name] = ref_ext
        else:
            rvec = params[idx : idx + 3]
            tvec = params[idx + 3 : idx + 6]
            idx += 6
            R = rvec_to_matrix(rvec)
            extrinsics_out[cam_name] = CameraExtrinsics(R=R, t=tvec.copy())

    water_z = float(params[idx])
    idx += 1

    # Unpack intrinsics
    intrinsics_out: dict[str, CameraIntrinsics] = {}
    if refine_intrinsics:
        for cam_name in camera_order:
            fx, fy, cx, cy = params[idx : idx + 4]
            idx += 4
            base = base_intrinsics[cam_name]
            K_new = np.array(
                [[fx, 0, cx], [0, fy, cy], [0, 0, 1]],
                dtype=np.float64,
            )
            intrinsics_out[cam_name] = CameraIntrinsics(
                K=K_new,
                dist_coeffs=base.dist_coeffs.copy(),
                image_size=base.image_size,
            )

    return extrinsics_out, water_z, intrinsics_out


def _build_point_jac_sparsity(
    active_correspondences: list[PointCorrespondence],
    reference_camera: str,
    camera_order: list[str],
    refine_intrinsics: bool = False,
    normal_fixed: bool = True,
) -> NDArray[np.int8]:
    """Build Jacobian sparsity pattern for point correspondence residuals.

    Each residual pair (x, y) for a (correspondence, camera) observation depends on:
    - Tilt params: 2 (only if normal_fixed=False AND camera is reference)
    - That camera's extrinsic params (6, or 0 if reference camera)
    - water_z (1) -- dense column, ALL residuals depend on it
    - That camera's intrinsic params (4, if refine_intrinsics)

    Args:
        active_correspondences: Filtered list of correspondences (weight > 0).
        reference_camera: Name of reference camera (no extrinsic params).
        camera_order: Ordered list of camera names.
        refine_intrinsics: Whether intrinsics columns are present.
        normal_fixed: If False, 2 tilt params are prepended.

    Returns:
        Sparsity matrix of shape (n_residuals, n_params) with 1s where Jacobian
        may be non-zero.
    """
    n_cams = len(camera_order)
    n_tilt_params = 0 if normal_fixed else 2
    n_extrinsic_params = 6 * (n_cams - 1)
    n_water_z_params = 1
    n_intrinsic_params = 4 * n_cams if refine_intrinsics else 0
    n_params = (
        n_tilt_params + n_extrinsic_params + n_water_z_params + n_intrinsic_params
    )

    # Camera index to extrinsic block start offset
    cam_to_ext_offset: dict[str, int] = {}
    ext_idx = 0
    for cam_name in camera_order:
        if cam_name != reference_camera:
            cam_to_ext_offset[cam_name] = ext_idx
            ext_idx += 1

    cam_to_cam_idx = {cam: i for i, cam in enumerate(camera_order)}
    water_z_col = n_tilt_params + n_extrinsic_params

    residual_rows = []
    for corr in active_correspondences:
        for cam_name in corr.observations:
            row = np.zeros(n_params, dtype=np.int8)

            # 0. Tilt params (reference camera residuals depend on tilt)
            if not normal_fixed and cam_name == reference_camera:
                row[0:2] = 1

            # 1. Camera extrinsics (if not reference)
            if cam_name in cam_to_ext_offset:
                ext_start = n_tilt_params + cam_to_ext_offset[cam_name] * 6
                row[ext_start : ext_start + 6] = 1

            # 2. water_z affects ALL cameras (dense column)
            row[water_z_col] = 1

            # 3. Camera intrinsics (if refining)
            if refine_intrinsics:
                cam_idx = cam_to_cam_idx[cam_name]
                intr_start = (
                    n_tilt_params + n_extrinsic_params + n_water_z_params + cam_idx * 4
                )
                row[intr_start : intr_start + 4] = 1

            # Two residuals (x and y) with same sparsity pattern
            residual_rows.append(row)
            residual_rows.append(row.copy())

    return np.array(residual_rows, dtype=np.int8)


def _build_point_bounds(
    camera_order: list[str],
    reference_camera: str,
    base_intrinsics: dict[str, CameraIntrinsics] | None = None,
    refine_intrinsics: bool = False,
    normal_fixed: bool = True,
    intrinsics_bound_pct: float = 0.1,
) -> tuple[NDArray[np.float64], NDArray[np.float64]]:
    """Build lower and upper bounds for point refinement optimization.

    Args:
        camera_order: Ordered list of camera names.
        reference_camera: Name of reference camera.
        base_intrinsics: Base intrinsics (required if refine_intrinsics=True).
        refine_intrinsics: Whether intrinsics are being refined.
        normal_fixed: If False, 2 tilt bounds are prepended.
        intrinsics_bound_pct: Maximum allowed fractional drift for each intrinsic
            parameter from its initial value (e.g. 0.1 = 10%).

    Returns:
        Tuple of (lower_bounds, upper_bounds) arrays.
    """
    n_cams = len(camera_order)
    n_tilt_params = 0 if normal_fixed else 2
    n_extrinsic_params = 6 * (n_cams - 1)
    n_water_z_params = 1
    n_intrinsic_params = 4 * n_cams if refine_intrinsics else 0
    total = n_tilt_params + n_extrinsic_params + n_water_z_params + n_intrinsic_params

    lower = np.full(total, -np.inf)
    upper = np.full(total, np.inf)

    # Tilt bounds: [-0.2, 0.2] radians (~11 degrees)
    if not normal_fixed:
        lower[0:2] = -0.2
        upper[0:2] = 0.2

    # Water surface Z bound: [0.01, 2.0] meters
    water_z_idx = n_tilt_params + n_extrinsic_params
    lower[water_z_idx] = 0.01
    upper[water_z_idx] = 2.0

    # Intrinsic bounds: each param within +/- intrinsics_bound_pct of initial value
    if refine_intrinsics:
        intr_start = n_tilt_params + n_extrinsic_params + n_water_z_params
        for i, cam_name in enumerate(camera_order):
            base = base_intrinsics[cam_name]
            fx, fy = base.K[0, 0], base.K[1, 1]
            cx, cy = base.K[0, 2], base.K[1, 2]
            offset = intr_start + i * 4

            lower[offset] = fx * (1.0 - intrinsics_bound_pct)
            upper[offset] = fx * (1.0 + intrinsics_bound_pct)
            lower[offset + 1] = fy * (1.0 - intrinsics_bound_pct)
            upper[offset + 1] = fy * (1.0 + intrinsics_bound_pct)
            lower[offset + 2] = cx * (1.0 - intrinsics_bound_pct)
            upper[offset + 2] = cx * (1.0 + intrinsics_bound_pct)
            lower[offset + 3] = cy * (1.0 - intrinsics_bound_pct)
            upper[offset + 3] = cy * (1.0 + intrinsics_bound_pct)

    return lower, upper


def _compute_point_residuals(
    params: NDArray[np.float64],
    active_correspondences: list[PointCorrespondence],
    reference_camera: str,
    reference_extrinsics: CameraExtrinsics,
    camera_order: list[str],
    intrinsics_map: dict,
    interface_normal: NDArray[np.float64],
    n_air: float,
    n_water: float,
    refine_intrinsics: bool = False,
    normal_fixed: bool = True,
    base_intrinsics: dict[str, CameraIntrinsics] | None = None,
) -> NDArray[np.float64]:
    """Compute weighted reprojection residuals for all point correspondences.

    Args:
        params: Current parameter vector.
        active_correspondences: Filtered correspondences (weight > 0).
        reference_camera: Name of reference camera.
        reference_extrinsics: Fixed extrinsics for reference camera.
        camera_order: Ordered list of camera names.
        intrinsics_map: Dict mapping camera name to CameraIntrinsics (used when
            refine_intrinsics=False).
        interface_normal: Interface normal vector.
        n_air: Refractive index of air.
        n_water: Refractive index of water.
        refine_intrinsics: Whether intrinsics are in the param vector.
        normal_fixed: Whether reference camera tilt is fixed.
        base_intrinsics: Base intrinsics for unpacking (required when
            refine_intrinsics=True).

    Returns:
        1D residual array [r0_x, r0_y, r1_x, r1_y, ...] in pixels (weighted).
    """
    extrinsics, water_z, refined_intrinsics = _unpack_refine_params(
        params,
        reference_camera,
        reference_extrinsics,
        camera_order,
        base_intrinsics=base_intrinsics,
        refine_intrinsics=refine_intrinsics,
        normal_fixed=normal_fixed,
    )

    # Use refined intrinsics if available, otherwise use fixed intrinsics_map
    active_intrinsics = refined_intrinsics if refine_intrinsics else intrinsics_map

    residuals = []

    for corr in active_correspondences:
        sqrt_w = np.sqrt(corr.weight)
        point_3d = corr.point_3d.reshape(1, 3)

        for cam_name, observed_pixel in corr.observations.items():
            camera = create_camera(
                cam_name, active_intrinsics[cam_name], extrinsics[cam_name]
            )

            interface = Interface(
                normal=interface_normal,
                camera_distances={cam_name: water_z},
                n_air=n_air,
                n_water=n_water,
            )

            projected = refractive_project_batch(camera, interface, point_3d)
            diff = projected[0] - observed_pixel

            # NaN penalty: projection failed (total internal reflection, etc.)
            if np.isnan(diff).any():
                diff = np.array([100.0, 100.0])

            residuals.extend((diff * sqrt_w).tolist())

    if residuals:
        return np.array(residuals, dtype=np.float64)
    return np.array([], dtype=np.float64)


def refine_calibration(
    result: CalibrationResult,
    correspondences: list[PointCorrespondence],
    *,
    refine_intrinsics: bool = False,
    intrinsics_bound_pct: float = 0.1,
    normal_fixed: bool = True,
    loss: str = "linear",
    f_scale: float = 1.0,
    verbose: bool = False,
    ftol: float = 1e-8,
    xtol: float = 1e-8,
    max_nfev: int | None = None,
    validate: bool = True,
    holdout_fraction: float = 0.2,
    holdout_seed: int = 42,
    reproj_threshold: float = 1.0,
    translation_threshold_mm: float = 50.0,
    rotation_threshold_deg: float = 2.0,
) -> RefinementResult:
    """Refine an existing calibration using 3D-to-2D point correspondences.

    Performs bundle adjustment over camera extrinsics and water_z to minimize
    reprojection error on the provided point correspondences. Optionally refines
    camera intrinsics (fx, fy, cx, cy) and reference camera tilt, and supports
    robust loss functions for outlier tolerance.

    When ``validate=True`` (default), a fraction of correspondences is held out
    and used to compute a ``ValidationReport`` with holdout reprojection error,
    triangulation consistency, and per-camera extrinsics drift metrics. The
    report includes an accept/reject recommendation based on configurable
    thresholds.

    Args:
        result: Existing calibration to refine.
        correspondences: List of PointCorrespondence objects, each providing a
            3D world point and its observed 2D pixel locations across cameras.
        refine_intrinsics: If True, include fx, fy, cx, cy for each camera in
            the optimization. Default False (intrinsics stay fixed).
        intrinsics_bound_pct: Maximum allowed fractional drift for each intrinsic
            parameter from its initial value. Only used when refine_intrinsics=True.
            Default 0.1 (10%).
        normal_fixed: If True (default), reference camera orientation is fixed.
            If False, include 2-DOF tilt (rx, ry) for the reference camera.
        loss: Loss function for the optimizer. One of "linear" (default, squared
            loss), "huber", or "cauchy". Robust losses reduce outlier influence.
        f_scale: Soft margin for robust loss inlier/outlier threshold, in pixels.
            Only meaningful when loss != "linear". Default 1.0.
        verbose: If True, print optimizer progress. Default False.
        ftol: Relative tolerance for cost function change. Default 1e-8.
        xtol: Relative tolerance for parameter change. Default 1e-8.
        max_nfev: Maximum number of function evaluations. Default None (auto-scaled
            based on problem size; when refine_intrinsics=True and max_nfev is not
            set, uses 200 * n_params).
        validate: If True (default), hold out a fraction of correspondences and
            produce a ValidationReport with accept/reject recommendation. If False,
            all correspondences are used for optimization and validation_report
            is None.
        holdout_fraction: Fraction of active correspondences to hold out for
            validation (0.0 to 1.0). Default 0.2.
        holdout_seed: Random seed for holdout split reproducibility. Default 42.
        reproj_threshold: Maximum allowed holdout reprojection error in pixels.
            Default 1.0.
        translation_threshold_mm: Maximum allowed camera translation drift in mm.
            Default 50.0.
        rotation_threshold_deg: Maximum allowed camera rotation drift in degrees.
            Default 2.0.

    Returns:
        A RefinementResult containing:
        - ``result``: The refined CalibrationResult with updated extrinsics,
          water_z, and optionally intrinsics.
        - ``validation_report``: ValidationReport with holdout metrics and
          accept/reject recommendation, or None if validate=False.
        - ``accepted``: True/False recommendation, or None if validate=False.

    Raises:
        ValueError: If correspondences is empty, contains negative weights,
            fewer than 2 observations per correspondence, invalid shapes,
            references camera names not in result.cameras, or loss is not one of
            "linear", "huber", "cauchy".
        InsufficientDataError: If fewer than 10 active (non-zero-weight)
            correspondences remain after filtering zero-weight entries.

    Notes:
        Non-convergence is logged as a warning but does not raise an exception.
        The best-effort result is returned regardless of convergence status.
        When validate=True, the optimization uses only the train split (not
        holdout), so the holdout reprojection error is an unbiased estimate.

    Example:
        >>> from aquacal import refine_calibration, PointCorrespondence
        >>> import numpy as np
        >>> corr = PointCorrespondence(
        ...     point_3d=np.array([0.1, 0.2, 0.5]),
        ...     observations={"cam0": np.array([320.0, 240.0]),
        ...                   "cam1": np.array([400.0, 260.0])},
        ... )
        >>> result = refine_calibration(calibration, [corr, ...])
        >>> print(result.accepted)  # True/False/None
        >>> print(result.validation_report.summary)  # Human-readable
        >>> refined_cal = result.result  # The CalibrationResult
    """
    # --- Validate loss parameter ---
    if loss not in _VALID_LOSSES:
        raise ValueError(
            f"Invalid loss function '{loss}'. Must be one of: {sorted(_VALID_LOSSES)}"
        )

    # --- Input validation ---
    if not correspondences:
        raise ValueError("correspondences must not be empty")

    known_cameras = set(result.cameras.keys())

    for i, corr in enumerate(correspondences):
        if corr.weight < 0.0:
            raise ValueError(
                f"Correspondence {i} has negative weight {corr.weight}. "
                "Weights must be non-negative."
            )

        point_3d = np.asarray(corr.point_3d, dtype=np.float64)
        if point_3d.shape != (3,):
            raise ValueError(
                f"Correspondence {i}: point_3d must have shape (3,), "
                f"got {point_3d.shape}"
            )

        if len(corr.observations) < 2:
            raise ValueError(
                f"Correspondence {i} has only {len(corr.observations)} observation(s). "
                "Each correspondence must be observed in at least 2 cameras."
            )

        for cam_name, pixel in corr.observations.items():
            if cam_name not in known_cameras:
                raise ValueError(
                    f"Correspondence {i}: camera '{cam_name}' not found in "
                    f"result.cameras. Known cameras: {sorted(known_cameras)}"
                )
            pixel_arr = np.asarray(pixel, dtype=np.float64)
            if pixel_arr.shape != (2,):
                raise ValueError(
                    f"Correspondence {i}, camera '{cam_name}': observation must "
                    f"have shape (2,), got {pixel_arr.shape}"
                )

    # Filter zero-weight correspondences (soft-disable pattern)
    active = [c for c in correspondences if c.weight > 0.0]

    if len(active) < _MIN_CORRESPONDENCES:
        raise InsufficientDataError(
            f"Only {len(active)} active correspondences after filtering zero-weight "
            f"entries. At least {_MIN_CORRESPONDENCES} are required for stable "
            "bundle adjustment."
        )

    # --- Setup ---
    camera_order = sorted(result.cameras.keys())
    reference_camera = camera_order[0]
    reference_extrinsics = result.cameras[reference_camera].extrinsics

    # Determine shared water_z from input result
    water_z_initial = result.cameras[reference_camera].water_z

    extrinsics_init: dict[str, CameraExtrinsics] = {
        name: cam.extrinsics for name, cam in result.cameras.items()
    }
    intrinsics_map = {name: cam.intrinsics for name, cam in result.cameras.items()}

    interface_normal = np.array(result.interface.normal, dtype=np.float64)
    n_air = result.interface.n_air
    n_water = result.interface.n_water

    # Normalise observations to float64 arrays (defensive copy)
    active_normalised: list[PointCorrespondence] = []
    for corr in active:
        active_normalised.append(
            PointCorrespondence(
                point_3d=np.asarray(corr.point_3d, dtype=np.float64),
                observations={
                    k: np.asarray(v, dtype=np.float64)
                    for k, v in corr.observations.items()
                },
                weight=float(corr.weight),
            )
        )

    # --- Holdout split (if validating) ---
    holdout_set: list[PointCorrespondence] = []
    if validate:
        train_set, holdout_set = split_holdout(
            active_normalised, holdout_fraction, seed=holdout_seed
        )
        if len(train_set) < 6:
            logger.warning(
                "refine_calibration: only %d correspondences in train set after "
                "holdout split (holdout=%d). Results may be unreliable.",
                len(train_set),
                len(holdout_set),
            )
        # Compute triangulation consistency BEFORE refinement on holdout set
        tri_before = compute_triangulation_consistency(result, holdout_set)
        # Use train set for optimization
        optim_correspondences = train_set
    else:
        optim_correspondences = active_normalised

    # --- Pack parameters ---
    x0 = _pack_refine_params(
        extrinsics_init,
        water_z_initial,
        reference_camera,
        camera_order,
        intrinsics=intrinsics_map if refine_intrinsics else None,
        refine_intrinsics=refine_intrinsics,
        normal_fixed=normal_fixed,
    )

    n_params = len(x0)

    # Auto-scale max_nfev when intrinsics are enabled and caller didn't set it
    effective_max_nfev = max_nfev
    if refine_intrinsics and max_nfev is None:
        effective_max_nfev = 200 * n_params

    # --- Bounds ---
    bounds = _build_point_bounds(
        camera_order,
        reference_camera,
        base_intrinsics=intrinsics_map if refine_intrinsics else None,
        refine_intrinsics=refine_intrinsics,
        normal_fixed=normal_fixed,
        intrinsics_bound_pct=intrinsics_bound_pct,
    )

    # --- Cost function args (uses optim_correspondences, not full active set) ---
    cost_args = (
        optim_correspondences,
        reference_camera,
        reference_extrinsics,
        camera_order,
        intrinsics_map,
        interface_normal,
        n_air,
        n_water,
        refine_intrinsics,
        normal_fixed,
        intrinsics_map if refine_intrinsics else None,
    )

    # --- Sparse Jacobian ---
    jac_sparsity = _build_point_jac_sparsity(
        optim_correspondences,
        reference_camera,
        camera_order,
        refine_intrinsics=refine_intrinsics,
        normal_fixed=normal_fixed,
    )
    jac = make_sparse_jacobian_func(
        _compute_point_residuals,
        cost_args,
        jac_sparsity,
        bounds,
    )

    # --- Optimize ---
    verbosity = 1 if verbose else 0
    opt_result = least_squares(
        _compute_point_residuals,
        x0=x0,
        args=cost_args,
        method="trf",
        bounds=bounds,
        jac=jac,
        loss=loss,
        f_scale=f_scale,
        ftol=ftol,
        xtol=xtol,
        max_nfev=effective_max_nfev,
        verbose=verbosity,
    )

    if opt_result.status <= 0:
        logger.warning(
            "refine_calibration: optimization did not converge (status=%d, message=%s). "
            "Returning best-effort result.",
            opt_result.status,
            opt_result.message,
        )

    # --- Unpack and build output CalibrationResult ---
    extrinsics_out, water_z_out, intrinsics_out = _unpack_refine_params(
        opt_result.x,
        reference_camera,
        reference_extrinsics,
        camera_order,
        base_intrinsics=intrinsics_map if refine_intrinsics else None,
        refine_intrinsics=refine_intrinsics,
        normal_fixed=normal_fixed,
    )

    # Log intrinsic drift warnings
    if refine_intrinsics:
        for cam_name in camera_order:
            base_K = intrinsics_map[cam_name].K
            refined_K = intrinsics_out[cam_name].K
            labels = ["fx", "fy", "cx", "cy"]
            base_vals = [base_K[0, 0], base_K[1, 1], base_K[0, 2], base_K[1, 2]]
            refined_vals = [
                refined_K[0, 0],
                refined_K[1, 1],
                refined_K[0, 2],
                refined_K[1, 2],
            ]

            for label, base_val, refined_val in zip(labels, base_vals, refined_vals):
                if base_val == 0.0:
                    continue
                drift_pct = abs(refined_val - base_val) / abs(base_val)
                if drift_pct > _INTRINSIC_DRIFT_WARN_PCT:
                    logger.warning(
                        "refine_calibration: intrinsic drift warning for %s.%s: "
                        "%.1f -> %.1f (%.1f%% change, threshold %.1f%%)",
                        cam_name,
                        label,
                        base_val,
                        refined_val,
                        drift_pct * 100,
                        _INTRINSIC_DRIFT_WARN_PCT * 100,
                    )

    cameras_out: dict[str, CameraCalibration] = {}
    for cam_name, cam_cal in result.cameras.items():
        # Use refined intrinsics when available, otherwise copy from input
        out_intrinsics = (
            intrinsics_out[cam_name] if refine_intrinsics else cam_cal.intrinsics
        )
        cameras_out[cam_name] = CameraCalibration(
            name=cam_name,
            intrinsics=out_intrinsics,
            extrinsics=extrinsics_out[cam_name],
            water_z=water_z_out,
            is_auxiliary=cam_cal.is_auxiliary,
        )

    # Compute final RMS from opt_result.fun (raw residuals regardless of loss)
    final_residuals = opt_result.fun
    rms_error = (
        float(np.sqrt(np.mean(final_residuals**2))) if len(final_residuals) > 0 else 0.0
    )

    # Per-camera RMS from residuals
    # Residuals are interleaved [x, y] pairs per observation
    per_camera_residuals: dict[str, list[float]] = {n: [] for n in camera_order}
    res_idx = 0
    for corr in optim_correspondences:
        for cam_name in corr.observations:
            rx = final_residuals[res_idx]
            ry = final_residuals[res_idx + 1]
            per_camera_residuals[cam_name].append(rx)
            per_camera_residuals[cam_name].append(ry)
            res_idx += 2

    reprojection_error_per_camera: dict[str, float] = {}
    for cam_name, vals in per_camera_residuals.items():
        if vals:
            reprojection_error_per_camera[cam_name] = float(
                np.sqrt(np.mean(np.array(vals, dtype=np.float64) ** 2))
            )
        else:
            reprojection_error_per_camera[cam_name] = 0.0

    diagnostics_out = DiagnosticsData(
        reprojection_error_rms=rms_error,
        reprojection_error_per_camera=reprojection_error_per_camera,
        validation_3d_error_mean=0.0,
        validation_3d_error_std=0.0,
        per_corner_residuals=None,
        per_corner_camera_labels=None,
        per_frame_errors=None,
    )

    cal_result = CalibrationResult(
        cameras=cameras_out,
        interface=copy.copy(result.interface),
        board=copy.copy(result.board),
        diagnostics=diagnostics_out,
        metadata=copy.copy(result.metadata),
    )

    # --- Build validation report ---
    if validate and holdout_set:
        holdout_reproj = compute_holdout_reproj_error(cal_result, holdout_set)
        tri_after = compute_triangulation_consistency(cal_result, holdout_set)

        extrinsics_before = {
            name: cam.extrinsics for name, cam in result.cameras.items()
        }
        extrinsics_after = {
            name: cam.extrinsics for name, cam in cal_result.cameras.items()
        }
        camera_drifts = compute_extrinsics_drift(
            extrinsics_before,
            extrinsics_after,
            translation_threshold_mm=translation_threshold_mm,
            rotation_threshold_deg=rotation_threshold_deg,
        )

        validation_report = build_validation_report(
            holdout_reproj=holdout_reproj,
            tri_before=tri_before,
            tri_after=tri_after,
            camera_drifts=camera_drifts,
            reproj_threshold=reproj_threshold,
            translation_threshold_mm=translation_threshold_mm,
            rotation_threshold_deg=rotation_threshold_deg,
        )

        return RefinementResult(
            result=cal_result,
            validation_report=validation_report,
            accepted=validation_report.accepted,
        )

    return RefinementResult(
        result=cal_result,
        validation_report=None,
        accepted=None,
    )
