"""Validation logic for calibration refinement results.

Provides holdout splitting, reprojection error computation, triangulation
consistency metrics, and extrinsics drift detection used by refine_calibration()
to produce a ValidationReport.
"""

from __future__ import annotations

import logging

import numpy as np
from numpy.typing import NDArray

from aquacal.config.schema import (
    CalibrationResult,
    CameraDrift,
    CameraExtrinsics,
    PointCorrespondence,
    ValidationReport,
)
from aquacal.core.camera import create_camera
from aquacal.core.interface_model import Interface
from aquacal.core.refractive_geometry import (
    refractive_back_project,
    refractive_project_batch,
)
from aquacal.triangulation.triangulate import point_to_ray_distance, triangulate_rays

logger = logging.getLogger(__name__)


def split_holdout(
    correspondences: list[PointCorrespondence],
    holdout_fraction: float,
    seed: int = 42,
) -> tuple[list[PointCorrespondence], list[PointCorrespondence]]:
    """Split correspondences into train and holdout sets.

    Each correspondence is independently assigned to holdout with probability
    ``holdout_fraction``, using a seeded random state for reproducibility.
    Same data + same seed = same split every time.

    Args:
        correspondences: List of correspondences to split.
        holdout_fraction: Fraction of correspondences to hold out (0.0 to 1.0).
        seed: Random seed for reproducibility.

    Returns:
        Tuple of (train, holdout) lists. Together they contain all input
        correspondences with no overlap.
    """
    if not correspondences:
        return [], []

    if holdout_fraction <= 0.0:
        return list(correspondences), []

    if holdout_fraction >= 1.0:
        return [], list(correspondences)

    rng = np.random.RandomState(seed)
    mask = rng.random(len(correspondences)) < holdout_fraction

    train = [c for c, is_holdout in zip(correspondences, mask) if not is_holdout]
    holdout = [c for c, is_holdout in zip(correspondences, mask) if is_holdout]

    return train, holdout


def compute_holdout_reproj_error(
    calibration: CalibrationResult,
    holdout: list[PointCorrespondence],
) -> float:
    """Compute RMS reprojection error on held-out correspondences.

    For each holdout correspondence, reprojects the known 3D point through
    each observing camera using the refractive model and computes pixel error
    against the observed 2D location.

    Args:
        calibration: Calibration result to evaluate.
        holdout: Held-out correspondences with known 3D points and observations.

    Returns:
        RMS reprojection error in pixels. Returns 0.0 if holdout is empty.
    """
    if not holdout:
        return 0.0

    errors_sq: list[float] = []

    for corr in holdout:
        point_3d = np.asarray(corr.point_3d, dtype=np.float64).reshape(1, 3)

        for cam_name, observed_pixel in corr.observations.items():
            if cam_name not in calibration.cameras:
                continue

            cam_cal = calibration.cameras[cam_name]
            camera = create_camera(cam_name, cam_cal.intrinsics, cam_cal.extrinsics)
            interface = Interface(
                normal=calibration.interface.normal,
                camera_distances={cam_name: cam_cal.water_z},
                n_air=calibration.interface.n_air,
                n_water=calibration.interface.n_water,
            )

            projected = refractive_project_batch(camera, interface, point_3d)
            diff = projected[0] - np.asarray(observed_pixel, dtype=np.float64)

            if not np.isnan(diff).any():
                errors_sq.append(float(np.sum(diff**2)))

    if not errors_sq:
        return 0.0

    return float(np.sqrt(np.mean(errors_sq)))


def compute_triangulation_consistency(
    calibration: CalibrationResult,
    correspondences: list[PointCorrespondence],
) -> float:
    """Measure triangulation consistency as mean ray intersection residual.

    For each correspondence with 2+ observations, back-projects pixel
    observations into refracted rays and triangulates. The consistency metric
    is the mean point-to-ray distance across all rays, measuring how tightly
    rays converge at the triangulated point.

    Args:
        calibration: Calibration result to evaluate.
        correspondences: Correspondences with pixel observations.

    Returns:
        Mean ray intersection residual in meters. Returns 0.0 if no valid
        triangulations.
    """
    if not correspondences:
        return 0.0

    # Build shared interface with all cameras
    camera_distances = {
        cam_name: calibration.cameras[cam_name].water_z
        for cam_name in calibration.cameras
    }
    interface = Interface(
        normal=calibration.interface.normal,
        camera_distances=camera_distances,
        n_air=calibration.interface.n_air,
        n_water=calibration.interface.n_water,
    )

    all_distances: list[float] = []

    for corr in correspondences:
        rays: list[tuple[NDArray[np.float64], NDArray[np.float64]]] = []

        for cam_name, pixel in corr.observations.items():
            if cam_name not in calibration.cameras:
                continue

            cam_cal = calibration.cameras[cam_name]
            camera = create_camera(cam_name, cam_cal.intrinsics, cam_cal.extrinsics)

            pixel_arr = np.asarray(pixel, dtype=np.float64)
            result = refractive_back_project(camera, interface, pixel_arr)
            if result[0] is not None:
                rays.append((result[0], result[1]))

        if len(rays) < 2:
            continue

        try:
            point = triangulate_rays(rays)
        except ValueError:
            continue

        for origin, direction in rays:
            d = direction / np.linalg.norm(direction)
            dist = point_to_ray_distance(point, origin, d)
            all_distances.append(dist)

    if not all_distances:
        return 0.0

    return float(np.mean(all_distances))


def compute_extrinsics_drift(
    before: dict[str, CameraExtrinsics],
    after: dict[str, CameraExtrinsics],
    translation_threshold_mm: float = 50.0,
    rotation_threshold_deg: float = 2.0,
) -> dict[str, CameraDrift]:
    """Compute per-camera extrinsics drift between two calibrations.

    Args:
        before: Camera extrinsics before refinement.
        after: Camera extrinsics after refinement.
        translation_threshold_mm: Maximum allowed translation shift in mm.
        rotation_threshold_deg: Maximum allowed rotation shift in degrees.

    Returns:
        Dict mapping camera name to CameraDrift with translation (mm),
        rotation (degrees), and whether thresholds were exceeded.
    """
    drifts: dict[str, CameraDrift] = {}

    for cam_name in before:
        if cam_name not in after:
            continue

        ext_before = before[cam_name]
        ext_after = after[cam_name]

        # Translation: camera center shift in mm
        C_before = ext_before.C
        C_after = ext_after.C
        translation_mm = float(np.linalg.norm(C_after - C_before) * 1000.0)

        # Rotation: angle of relative rotation in degrees
        R_rel = ext_after.R @ ext_before.R.T
        # Clamp trace to valid range for arccos
        trace_val = np.trace(R_rel)
        cos_angle = np.clip((trace_val - 1.0) / 2.0, -1.0, 1.0)
        rotation_deg = float(np.degrees(np.arccos(cos_angle)))

        exceeded = (
            translation_mm > translation_threshold_mm
            or rotation_deg > rotation_threshold_deg
        )

        drifts[cam_name] = CameraDrift(
            translation_mm=translation_mm,
            rotation_deg=rotation_deg,
            exceeded=exceeded,
        )

    return drifts


def build_validation_report(
    holdout_reproj: float,
    tri_before: float,
    tri_after: float,
    camera_drifts: dict[str, CameraDrift],
    reproj_threshold: float = 1.0,
    translation_threshold_mm: float = 50.0,
    rotation_threshold_deg: float = 2.0,
) -> ValidationReport:
    """Build a ValidationReport with accept/reject recommendation.

    The recommendation is ``accepted=False`` when ANY threshold is exceeded
    (any-fail rejects). The summary string names the specific camera(s) and
    metric(s) that caused rejection.

    Args:
        holdout_reproj: RMS reprojection error on holdout set (pixels).
        tri_before: Triangulation consistency before refinement (meters).
        tri_after: Triangulation consistency after refinement (meters).
        camera_drifts: Per-camera drift metrics.
        reproj_threshold: Maximum allowed holdout reprojection error (pixels).
        translation_threshold_mm: Maximum translation drift threshold (mm).
        rotation_threshold_deg: Maximum rotation drift threshold (degrees).

    Returns:
        ValidationReport with all metrics and accept/reject recommendation.
    """
    failures: list[str] = []

    # Check holdout reprojection error
    if holdout_reproj > reproj_threshold:
        failures.append(
            f"holdout reprojection error {holdout_reproj:.2f}px "
            f"exceeds {reproj_threshold:.1f}px threshold"
        )

    # Check per-camera drift
    for cam_name, drift in sorted(camera_drifts.items()):
        if drift.exceeded:
            reasons: list[str] = []
            if drift.translation_mm > translation_threshold_mm:
                reasons.append(
                    f"translation drift {drift.translation_mm:.1f}mm "
                    f"exceeds {translation_threshold_mm:.0f}mm threshold"
                )
            if drift.rotation_deg > rotation_threshold_deg:
                reasons.append(
                    f"rotation drift {drift.rotation_deg:.2f}deg "
                    f"exceeds {rotation_threshold_deg:.1f}deg threshold"
                )
            failures.append(f"{cam_name} {', '.join(reasons)}")

    accepted = len(failures) == 0

    if accepted:
        summary = (
            f"Accepted: holdout reproj {holdout_reproj:.2f}px, "
            f"triangulation consistency {tri_before:.4f}m -> {tri_after:.4f}m, "
            f"all cameras within drift thresholds"
        )
    else:
        summary = "Rejected: " + "; ".join(failures)

    return ValidationReport(
        holdout_reproj_error=holdout_reproj,
        triangulation_consistency_before=tri_before,
        triangulation_consistency_after=tri_after,
        camera_drifts=camera_drifts,
        accepted=accepted,
        summary=summary,
    )
