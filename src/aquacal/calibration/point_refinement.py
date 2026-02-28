"""Point correspondence refinement for existing calibrations.

Provides refine_calibration(), which performs bundle adjustment over extrinsics
and water_z using 3D-to-2D point correspondences supplied by downstream consumers.
Intrinsics remain fixed throughout refinement.
"""

from __future__ import annotations

import copy
import logging
from typing import TYPE_CHECKING

import numpy as np
from numpy.typing import NDArray
from scipy.optimize import least_squares

from aquacal.calibration._optim_common import make_sparse_jacobian_func
from aquacal.config.schema import (
    CalibrationResult,
    CameraCalibration,
    CameraExtrinsics,
    DiagnosticsData,
    InsufficientDataError,
    PointCorrespondence,
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


def _pack_refine_params(
    extrinsics: dict[str, CameraExtrinsics],
    water_z: float,
    reference_camera: str,
    camera_order: list[str],
) -> NDArray[np.float64]:
    """Pack optimization parameters into a 1D array.

    Parameter layout:
    - For each non-reference camera (sorted order, skip reference): rvec (3), tvec (3)
    - water_z (1): single shared parameter

    Args:
        extrinsics: Camera extrinsics dict
        water_z: Global water surface Z coordinate
        reference_camera: Name of reference camera (skipped in extrinsics packing)
        camera_order: Ordered list of camera names

    Returns:
        1D parameter vector
    """
    params: list[float] = []

    for cam_name in camera_order:
        if cam_name == reference_camera:
            continue
        ext = extrinsics[cam_name]
        rvec = matrix_to_rvec(ext.R)
        params.extend(rvec.tolist())
        params.extend(ext.t.tolist())

    params.append(water_z)

    return np.array(params, dtype=np.float64)


def _unpack_refine_params(
    params: NDArray[np.float64],
    reference_camera: str,
    reference_extrinsics: CameraExtrinsics,
    camera_order: list[str],
) -> tuple[dict[str, CameraExtrinsics], float]:
    """Unpack 1D parameter array into extrinsics dict and water_z.

    Args:
        params: 1D parameter vector
        reference_camera: Name of reference camera
        reference_extrinsics: Fixed extrinsics for reference camera
        camera_order: Ordered list of camera names

    Returns:
        Tuple of (extrinsics_dict, water_z)
    """
    idx = 0
    extrinsics_out: dict[str, CameraExtrinsics] = {}

    for cam_name in camera_order:
        if cam_name == reference_camera:
            extrinsics_out[cam_name] = reference_extrinsics
        else:
            rvec = params[idx : idx + 3]
            tvec = params[idx + 3 : idx + 6]
            idx += 6
            R = rvec_to_matrix(rvec)
            extrinsics_out[cam_name] = CameraExtrinsics(R=R, t=tvec.copy())

    water_z = float(params[idx])

    return extrinsics_out, water_z


def _build_point_jac_sparsity(
    active_correspondences: list[PointCorrespondence],
    reference_camera: str,
    camera_order: list[str],
) -> NDArray[np.int8]:
    """Build Jacobian sparsity pattern for point correspondence residuals.

    Each residual pair (x, y) for a (correspondence, camera) observation depends on:
    - That camera's extrinsic params (6, or 0 if reference camera)
    - water_z (1) — dense column, ALL residuals depend on it

    Args:
        active_correspondences: Filtered list of correspondences (weight > 0)
        reference_camera: Name of reference camera (no extrinsic params)
        camera_order: Ordered list of camera names

    Returns:
        Sparsity matrix of shape (n_residuals, n_params) with 1s where Jacobian
        may be non-zero.
    """
    n_cams = len(camera_order)
    n_extrinsic_params = 6 * (n_cams - 1)
    n_water_z_params = 1
    n_params = n_extrinsic_params + n_water_z_params

    # Camera index to extrinsic block start offset
    cam_to_ext_offset: dict[str, int] = {}
    ext_idx = 0
    for cam_name in camera_order:
        if cam_name != reference_camera:
            cam_to_ext_offset[cam_name] = ext_idx
            ext_idx += 1

    water_z_col = n_extrinsic_params  # last column

    residual_rows = []
    for corr in active_correspondences:
        for cam_name in corr.observations:
            row = np.zeros(n_params, dtype=np.int8)

            # Camera extrinsics (if not reference)
            if cam_name in cam_to_ext_offset:
                ext_start = cam_to_ext_offset[cam_name] * 6
                row[ext_start : ext_start + 6] = 1

            # water_z affects ALL cameras (dense column)
            row[water_z_col] = 1

            # Two residuals (x and y) with same sparsity pattern
            residual_rows.append(row)
            residual_rows.append(row.copy())

    return np.array(residual_rows, dtype=np.int8)


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
) -> NDArray[np.float64]:
    """Compute weighted reprojection residuals for all point correspondences.

    Args:
        params: Current parameter vector (extrinsics + water_z)
        active_correspondences: Filtered correspondences (weight > 0)
        reference_camera: Name of reference camera
        reference_extrinsics: Fixed extrinsics for reference camera
        camera_order: Ordered list of camera names
        intrinsics_map: Dict mapping camera name to CameraIntrinsics (fixed)
        interface_normal: Interface normal vector
        n_air: Refractive index of air
        n_water: Refractive index of water

    Returns:
        1D residual array [r0_x, r0_y, r1_x, r1_y, ...] in pixels (weighted).
    """
    extrinsics, water_z = _unpack_refine_params(
        params, reference_camera, reference_extrinsics, camera_order
    )

    residuals = []

    for corr in active_correspondences:
        sqrt_w = np.sqrt(corr.weight)
        point_3d = corr.point_3d.reshape(1, 3)

        for cam_name, observed_pixel in corr.observations.items():
            camera = create_camera(
                cam_name, intrinsics_map[cam_name], extrinsics[cam_name]
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
    verbose: bool = False,
    ftol: float = 1e-8,
    xtol: float = 1e-8,
    max_nfev: int | None = None,
) -> CalibrationResult:
    """Refine an existing calibration using 3D-to-2D point correspondences.

    Performs bundle adjustment over camera extrinsics and water_z to minimize
    reprojection error on the provided point correspondences. Camera intrinsics
    remain unchanged.

    Args:
        result: Existing calibration to refine.
        correspondences: List of PointCorrespondence objects, each providing a
            3D world point and its observed 2D pixel locations across cameras.
        verbose: If True, print optimizer progress. Default False.
        ftol: Relative tolerance for cost function change. Default 1e-8.
        xtol: Relative tolerance for parameter change. Default 1e-8.
        max_nfev: Maximum number of function evaluations. Default None (scipy
            chooses automatically based on problem size).

    Returns:
        A new CalibrationResult with updated extrinsics and water_z. Intrinsics
        are copied unchanged from the input result. The diagnostics field is
        updated with the final reprojection RMS from this refinement.

    Raises:
        ValueError: If correspondences is empty, contains negative weights,
            fewer than 2 observations per correspondence, invalid shapes, or
            references camera names not in result.cameras.
        InsufficientDataError: If fewer than 10 active (non-zero-weight)
            correspondences remain after filtering zero-weight entries.

    Notes:
        Non-convergence is logged as a warning but does not raise an exception.
        The best-effort result is returned regardless of convergence status.
        Compare the diagnostics.reprojection_error_rms before and after to
        assess refinement quality.

    Example:
        >>> from aquacal import refine_calibration, PointCorrespondence
        >>> import numpy as np
        >>> corr = PointCorrespondence(
        ...     point_3d=np.array([0.1, 0.2, 0.5]),
        ...     observations={"cam0": np.array([320.0, 240.0]),
        ...                   "cam1": np.array([400.0, 260.0])},
        ... )
        >>> refined = refine_calibration(result, [corr, ...])
    """
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

    # --- Pack parameters ---
    x0 = _pack_refine_params(
        extrinsics_init, water_z_initial, reference_camera, camera_order
    )

    # --- Bounds ---
    n_cams = len(camera_order)
    n_extrinsic_params = 6 * (n_cams - 1)
    n_params = n_extrinsic_params + 1  # extrinsics + water_z

    lower = np.full(n_params, -np.inf)
    upper = np.full(n_params, np.inf)
    # water_z bounded to [0.01, 2.0] meters
    lower[n_extrinsic_params] = 0.01
    upper[n_extrinsic_params] = 2.0

    bounds = (lower, upper)

    # --- Cost function args ---
    cost_args = (
        active_normalised,
        reference_camera,
        reference_extrinsics,
        camera_order,
        intrinsics_map,
        interface_normal,
        n_air,
        n_water,
    )

    # --- Sparse Jacobian ---
    jac_sparsity = _build_point_jac_sparsity(
        active_normalised, reference_camera, camera_order
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
        ftol=ftol,
        xtol=xtol,
        max_nfev=max_nfev,
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
    extrinsics_out, water_z_out = _unpack_refine_params(
        opt_result.x, reference_camera, reference_extrinsics, camera_order
    )

    cameras_out: dict[str, CameraCalibration] = {}
    for cam_name, cam_cal in result.cameras.items():
        cameras_out[cam_name] = CameraCalibration(
            name=cam_name,
            intrinsics=cam_cal.intrinsics,  # unchanged
            extrinsics=extrinsics_out[cam_name],
            water_z=water_z_out,
            is_auxiliary=cam_cal.is_auxiliary,
        )

    # Compute final RMS
    final_residuals = opt_result.fun
    rms_error = (
        float(np.sqrt(np.mean(final_residuals**2))) if len(final_residuals) > 0 else 0.0
    )

    # Per-camera RMS from residuals
    # Residuals are interleaved [x, y] pairs per observation
    per_camera_residuals: dict[str, list[float]] = {n: [] for n in camera_order}
    res_idx = 0
    for corr in active_normalised:
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

    return CalibrationResult(
        cameras=cameras_out,
        interface=copy.copy(result.interface),
        board=copy.copy(result.board),
        diagnostics=diagnostics_out,
        metadata=copy.copy(result.metadata),
    )
