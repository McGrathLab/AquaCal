"""Standalone held-out evaluation of a calibration against a detection set.

The core entry point, ``evaluate_calibration``, scores an existing
``CalibrationResult`` against any ``DetectionResult`` (typically a held-out
validation split) without needing to run the full pipeline. This makes it
possible to, for example, score a calibration computed at one refractive
index against ground truth generated at a different one (WP4).

This module also hosts ``_estimate_validation_poses``, moved here verbatim
from ``aquacal.calibration.pipeline`` because it is the per-frame pose
refinement step that ``evaluate_calibration`` needs.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from numpy.typing import NDArray

from aquacal.config.schema import (
    BoardPose,
    CalibrationResult,
    CameraExtrinsics,
    CameraIntrinsics,
    DetectionResult,
)
from aquacal.core.board import BoardGeometry
from aquacal.validation.reconstruction import DistanceErrors, compute_3d_distance_errors
from aquacal.validation.reprojection import (
    ReprojectionErrors,
    compute_reprojection_errors,
)


@dataclass
class HeldOutEvaluation:
    """Result of scoring a calibration against a held-out detection set.

    Attributes:
        reprojection: Reprojection error statistics (existing ``ReprojectionErrors``
            type, unchanged).
        reconstruction: 3D distance error statistics (existing ``DistanceErrors``
            type, unchanged), or None when ``include_reconstruction=False``.
        board_poses: Board poses estimated (or supplied) for the held-out frames,
            keyed by frame index. Returned so callers can reuse them, e.g. to score
            auxiliary cameras against the same poses used for primary cameras.
        num_frames: Number of held-out frames with an estimated/supplied board pose.
    """

    reprojection: ReprojectionErrors
    reconstruction: DistanceErrors | None
    board_poses: dict[int, BoardPose]
    num_frames: int


def _filter_calibration_cameras(
    calibration: CalibrationResult, camera_names: set[str]
) -> CalibrationResult:
    """Build a copy of ``calibration`` containing only the given cameras.

    Identical in effect to ``aquacal.calibration.pipeline._filter_cameras``, but
    duplicated here (rather than imported) so this module does not depend on
    ``pipeline`` — pipeline already depends on ``aquacal.validation``, and an
    import in the other direction would create a cycle.

    Args:
        calibration: Full CalibrationResult.
        camera_names: Set of camera names to keep.

    Returns:
        New CalibrationResult with only the requested cameras.
    """
    filtered_cameras = {
        name: calib
        for name, calib in calibration.cameras.items()
        if name in camera_names
    }
    return CalibrationResult(
        cameras=filtered_cameras,
        interface=calibration.interface,
        board=calibration.board,
        diagnostics=calibration.diagnostics,
        metadata=calibration.metadata,
    )


def evaluate_calibration(
    calibration: CalibrationResult,
    detections: DetectionResult,
    board: BoardGeometry,
    min_corners: int = 8,
    cameras: set[str] | None = None,
    board_poses: dict[int, BoardPose] | None = None,
    include_reconstruction: bool = True,
) -> HeldOutEvaluation:
    """Score a calibration against a held-out detection set.

    Estimates a 6-DOF board pose per held-out frame (via refractive PnP
    initialization followed by per-frame refinement with cameras fixed) using
    the FULL calibration — every camera present in ``calibration`` — then
    computes reprojection and (optionally) 3D reconstruction error metrics,
    optionally restricted to a subset of cameras via ``cameras``.

    Scoring a calibration against detections generated at a different
    refractive index than the calibration's own ``n_air``/``n_water`` is
    exactly the intended WP4 usage: it measures how calibration accuracy
    degrades under a perturbed refractive-index assumption. There is no
    ``n_water`` override parameter here — ``n_air``, ``n_water``, and the
    interface normal always come from ``calibration.interface``, and the
    "different assumption" is encoded in the held-out ``detections`` instead.

    Args:
        calibration: Complete calibration to score, including all cameras
            (primary and auxiliary). Board poses are always estimated from
            this full calibration; ``cameras`` only restricts which cameras
            the error metrics are computed over afterward.
        detections: Held-out detection set (2D corner observations).
        board: Board geometry matching ``calibration.board``.
        min_corners: Minimum corners required per detection for the initial
            PnP-based pose estimate. Ignored when ``board_poses`` is supplied.
        cameras: If given, restrict reprojection/reconstruction metrics to
            this subset of camera names. If None, use all cameras in
            ``calibration``.
        board_poses: If given, skip pose estimation entirely and use these
            poses as-is (e.g. poses estimated for primary cameras, reused to
            score auxiliary cameras against the same ground truth).
        include_reconstruction: If False, skip 3D distance-error computation
            and return ``reconstruction=None``.

    Returns:
        HeldOutEvaluation with reprojection error, optional reconstruction
        error, the board poses used, and the number of held-out frames.

    Example:
        >>> from aquacal import evaluate_calibration, load_calibration
        >>> from aquacal.datasets import create_scenario, generate_synthetic_detections
        >>> from aquacal.core.board import BoardGeometry
        >>> calibration = load_calibration("calibration.json")
        >>> scenario = create_scenario("minimal", n_water=1.45)
        >>> board = BoardGeometry(scenario.board_config)
        >>> detections = generate_synthetic_detections(
        ...     scenario.intrinsics, scenario.extrinsics, scenario.water_zs,
        ...     board, scenario.board_poses, n_water=1.45,
        ... )
        >>> evaluation = evaluate_calibration(calibration, detections, board)
        >>> print(f"RMS: {evaluation.reprojection.rms:.3f} px")

    Note:
        Stable. Joins ``aquacal``'s deliberately small public API.
    """
    intrinsics: dict[str, CameraIntrinsics] = {
        name: cam.intrinsics for name, cam in calibration.cameras.items()
    }
    extrinsics: dict[str, CameraExtrinsics] = {
        name: cam.extrinsics for name, cam in calibration.cameras.items()
    }
    water_z_values: dict[str, float] = {
        name: cam.water_z for name, cam in calibration.cameras.items()
    }

    interface_normal: NDArray[np.float64] = calibration.interface.normal
    n_air = calibration.interface.n_air
    n_water = calibration.interface.n_water

    if board_poses is None:
        # Function-local import to avoid an import cycle at package load:
        # aquacal.calibration.interface_estimation is not imported at module
        # level here because aquacal.calibration.pipeline imports from
        # aquacal.validation, and a module-level import in this direction
        # would create a load-order coupling.
        from aquacal.calibration.interface_estimation import (
            _compute_initial_board_poses,
        )

        initial_poses = _compute_initial_board_poses(
            detections,
            intrinsics,
            extrinsics,
            board,
            min_corners=min_corners,
            n_water=n_water,
        )
        board_poses = _estimate_validation_poses(
            detections,
            initial_poses,
            intrinsics,
            extrinsics,
            water_z_values,
            board,
            interface_normal,
            n_air,
            n_water,
        )

    target = (
        calibration
        if cameras is None
        else _filter_calibration_cameras(calibration, cameras)
    )

    reprojection = compute_reprojection_errors(target, detections, board_poses)

    reconstruction = None
    if include_reconstruction:
        reconstruction = compute_3d_distance_errors(
            target, detections, board, include_spatial=True
        )

    return HeldOutEvaluation(
        reprojection=reprojection,
        reconstruction=reconstruction,
        board_poses=board_poses,
        num_frames=len(board_poses),
    )


def _estimate_validation_poses(
    detections: DetectionResult,
    initial_poses: dict[int, BoardPose],
    intrinsics: dict[str, CameraIntrinsics],
    extrinsics: dict[str, CameraExtrinsics],
    water_z_values: dict[str, float],
    board: BoardGeometry,
    interface_normal: np.ndarray,
    n_air: float,
    n_water: float,
) -> dict[int, BoardPose]:
    """Refine board poses for validation frames via per-frame optimization.

    For each frame, minimizes refractive reprojection error over the 6 pose
    parameters (rvec, tvec) while holding all camera parameters fixed.

    Args:
        detections: Detection results for validation frames
        initial_poses: PnP-initialized board poses
        intrinsics: Per-camera intrinsics
        extrinsics: Per-camera extrinsics
        water_z_values: Per-camera interface distances
        board: Board geometry
        interface_normal: Interface normal vector
        n_air: Refractive index of air
        n_water: Refractive index of water

    Returns:
        Dict mapping frame_idx to refined BoardPose
    """
    from scipy.optimize import least_squares

    from aquacal.core.camera import create_camera
    from aquacal.core.interface_model import Interface
    from aquacal.core.refractive_geometry import refractive_project

    refined_poses = {}

    for frame_idx, initial_pose in initial_poses.items():
        if frame_idx not in detections.frames:
            continue
        frame_det = detections.frames[frame_idx]

        # Build cameras and interface objects
        cameras = {}
        for cam_name in frame_det.detections:
            if cam_name not in intrinsics:
                continue
            cameras[cam_name] = create_camera(
                cam_name, intrinsics[cam_name], extrinsics[cam_name]
            )

        interface = Interface(
            normal=interface_normal,
            camera_distances=water_z_values,
            n_air=n_air,
            n_water=n_water,
        )

        # Cost function: refractive reprojection residuals for this frame
        def frame_residuals(params):
            rvec = params[:3]
            tvec = params[3:]
            corners_3d = board.transform_corners(rvec, tvec)

            residuals = []
            for cam_name, det in frame_det.detections.items():
                if cam_name not in cameras:
                    continue
                camera = cameras[cam_name]
                for i, corner_id in enumerate(det.corner_ids):
                    pt_3d = corners_3d[int(corner_id)]
                    projected = refractive_project(camera, interface, pt_3d)
                    if projected is not None:
                        residuals.append(det.corners_2d[i, 0] - projected[0])
                        residuals.append(det.corners_2d[i, 1] - projected[1])
                    else:
                        residuals.append(100.0)
                        residuals.append(100.0)

            return residuals if residuals else [0.0, 0.0]

        x0 = np.concatenate([initial_pose.rvec, initial_pose.tvec])

        result = least_squares(frame_residuals, x0, method="lm", max_nfev=100)

        refined_poses[frame_idx] = BoardPose(
            frame_idx=frame_idx,
            rvec=result.x[:3],
            tvec=result.x[3:],
        )

    return refined_poses
