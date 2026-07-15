"""Automatic per-frame outlier rejection for refractive bundle adjustment.

Catastrophically-bad frames (e.g. the ChArUco board partly out of the water,
surface ripples, motion blur, or a mis-detection) inject large, spatially
coherent reprojection residuals. Because every corner in a single board pose
moves together, a robust loss only partially suppresses their collective
leverage on the affected cameras' extrinsics. This module identifies such
frames from post-Stage-3 per-frame reprojection error and lets the pipeline
drop them and re-optimize on the cleaned set.

The rejection rule is deliberately conservative so that already-clean datasets
are unaffected (no-op): a frame is rejected only if its per-frame RMS exceeds
both a relative bound (``k * median``) and an absolute floor (in pixels). A
guardrail caps the fraction of frames that may be removed, so a genuinely
broken dataset surfaces loudly instead of being silently gutted.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from aquacal.config.schema import (
    BoardPose,
    CameraExtrinsics,
    CameraIntrinsics,
    DetectionResult,
    Vec3,
)
from aquacal.core.board import BoardGeometry
from aquacal.core.camera import Camera
from aquacal.core.interface_model import Interface
from aquacal.core.refractive_geometry import refractive_project

__all__ = [
    "FrameRejectionResult",
    "compute_per_frame_rms",
    "identify_outlier_frames",
    "drop_frames",
]


@dataclass
class FrameRejectionResult:
    """Outcome of the per-frame outlier rejection decision.

    Attributes:
        rejected_frames: Sorted list of frame indices flagged as outliers and
            removed from the optimization set. Empty when nothing is rejected.
        threshold_px: The RMS threshold (pixels) used for the decision, i.e.
            ``max(k * median_rms, absolute_floor_px)``.
        median_rms_px: Median per-frame RMS (pixels) across all evaluated frames.
        per_frame_rms: Mapping frame_idx -> per-frame RMS (pixels) for every
            evaluated frame (both kept and rejected).
        guardrail_triggered: True if the fraction of frames that WOULD be
            rejected exceeded ``max_reject_fraction``; when True no frames are
            rejected (rejected_frames is empty) and a warning is expected.
        num_evaluated: Number of frames with computable per-frame RMS.
    """

    rejected_frames: list[int]
    threshold_px: float
    median_rms_px: float
    per_frame_rms: dict[int, float]
    guardrail_triggered: bool = False
    num_evaluated: int = 0
    detail: dict[int, float] = field(default_factory=dict)

    def to_diagnostics_dict(self) -> dict[str, object]:
        """Serialize to a JSON-friendly dict for diagnostics.json."""
        return {
            "enabled": True,
            "rejected_frames": list(self.rejected_frames),
            "num_rejected": len(self.rejected_frames),
            "num_evaluated": int(self.num_evaluated),
            "threshold_px": float(self.threshold_px),
            "median_rms_px": float(self.median_rms_px),
            "guardrail_triggered": bool(self.guardrail_triggered),
            "rejected_frame_rms_px": {
                str(idx): float(self.per_frame_rms[idx])
                for idx in self.rejected_frames
                if idx in self.per_frame_rms
            },
        }


def compute_per_frame_rms(
    detections: DetectionResult,
    intrinsics: dict[str, CameraIntrinsics],
    extrinsics: dict[str, CameraExtrinsics],
    distances: dict[str, float],
    board_poses: list[BoardPose],
    board: BoardGeometry,
    interface_normal: Vec3,
    n_air: float,
    n_water: float,
) -> dict[int, float]:
    """Compute per-frame reprojection RMS (pixels) for a set of board poses.

    For each frame, aggregates the raw pixel residuals (``detected - projected``,
    NOT robust/Huber-weighted cost) of every corner across every camera that
    observed the board, then returns the root-mean-square. This is a single cheap
    forward-projection pass, comparable to one optimizer cost evaluation.

    CRITICAL - pose source: ``board_poses`` MUST be estimated INDEPENDENTLY per
    frame (e.g. per-frame PnP + 6-DOF refine against fixed cameras), NOT taken
    from the joint Stage-3 solution. A high-leverage outlier frame biases the
    shared extrinsics to fit itself, so with the *jointly-optimized* poses it
    reports a deceptively LOW residual and escapes rejection. Independent
    per-frame poses cannot reconcile a geometrically-inconsistent frame across
    cameras, so genuine outliers surface at a large residual (the same quantity
    holdout validation reports).

    Args:
        detections: Detections used for optimization (frame_idx -> per-camera).
        intrinsics: Per-camera intrinsics (fixed; Stage 3 does not refine them).
        extrinsics: Camera extrinsics (post-Stage-3).
        distances: Per-camera interface distances (water_z - C_z).
        board_poses: INDEPENDENTLY estimated per-frame board poses (see note
            above). One BoardPose per frame to evaluate.
        board: Board geometry.
        interface_normal: Interface normal vector (3,).
        n_air: Refractive index of air.
        n_water: Refractive index of water.

    Returns:
        Dict mapping frame_idx to per-frame RMS reprojection error in pixels.
        Frames with no projectable observations are omitted.
    """
    pose_by_frame = {bp.frame_idx: bp for bp in board_poses}

    per_frame_rms: dict[int, float] = {}
    for frame_idx, board_pose in pose_by_frame.items():
        frame_det = detections.frames.get(frame_idx)
        if frame_det is None:
            continue

        corners_3d = board.transform_corners(board_pose.rvec, board_pose.tvec)

        sq_sum = 0.0
        n_obs = 0
        for cam_name, detection in frame_det.detections.items():
            if cam_name not in extrinsics or cam_name not in intrinsics:
                continue

            camera = Camera(cam_name, intrinsics[cam_name], extrinsics[cam_name])
            interface = Interface(
                normal=np.asarray(interface_normal, dtype=np.float64),
                camera_distances={cam_name: distances[cam_name]},
                n_air=n_air,
                n_water=n_water,
            )

            for i, corner_id in enumerate(detection.corner_ids):
                projected = refractive_project(
                    camera, interface, corners_3d[int(corner_id)]
                )
                if projected is not None:
                    d = detection.corners_2d[i] - projected
                    sq_sum += float(d[0] ** 2 + d[1] ** 2)
                    n_obs += 1

        if n_obs > 0:
            per_frame_rms[frame_idx] = float(np.sqrt(sq_sum / n_obs))

    return per_frame_rms


def identify_outlier_frames(
    per_frame_rms: dict[int, float],
    k: float = 5.0,
    absolute_floor_px: float = 5.0,
    max_reject_fraction: float = 0.25,
) -> FrameRejectionResult:
    """Flag frames whose per-frame RMS is a catastrophic outlier.

    A frame is flagged when its RMS exceeds ``max(k * median, absolute_floor_px)``.
    The relative term adapts to the dataset's noise level; the absolute floor
    prevents over-rejection when the median RMS is tiny (e.g. a clean dataset at
    ~1 px would otherwise reject frames at 5-6 px, which are still fine).

    Guardrail: if the flagged fraction would exceed ``max_reject_fraction``, no
    frames are rejected (the result is a no-op with ``guardrail_triggered=True``)
    so a broadly-broken dataset is surfaced loudly rather than silently gutted.

    Args:
        per_frame_rms: Mapping frame_idx -> per-frame RMS (pixels).
        k: Relative multiplier on the median per-frame RMS (default 5.0).
        absolute_floor_px: Minimum RMS (pixels) a frame must exceed to be
            considered an outlier, regardless of the relative bound (default 5.0).
        max_reject_fraction: Maximum fraction of evaluated frames that may be
            rejected before the guardrail suppresses rejection (default 0.25).

    Returns:
        FrameRejectionResult describing the decision.
    """
    if k <= 0:
        raise ValueError(f"k must be > 0, got {k}")
    if not 0.0 < max_reject_fraction <= 1.0:
        raise ValueError(
            f"max_reject_fraction must be in (0, 1], got {max_reject_fraction}"
        )

    if not per_frame_rms:
        return FrameRejectionResult(
            rejected_frames=[],
            threshold_px=float("inf"),
            median_rms_px=float("nan"),
            per_frame_rms={},
            guardrail_triggered=False,
            num_evaluated=0,
        )

    values = np.array(list(per_frame_rms.values()), dtype=np.float64)
    median_rms = float(np.median(values))
    threshold = max(k * median_rms, absolute_floor_px)

    flagged = sorted(idx for idx, rms in per_frame_rms.items() if rms > threshold)

    num_evaluated = len(per_frame_rms)
    guardrail_triggered = len(flagged) > max_reject_fraction * num_evaluated

    rejected = [] if guardrail_triggered else flagged

    return FrameRejectionResult(
        rejected_frames=rejected,
        threshold_px=float(threshold),
        median_rms_px=median_rms,
        per_frame_rms=dict(per_frame_rms),
        guardrail_triggered=guardrail_triggered,
        num_evaluated=num_evaluated,
    )


def drop_frames(
    detections: DetectionResult,
    frames_to_drop: list[int],
) -> DetectionResult:
    """Return a new DetectionResult with the given frames removed.

    Args:
        detections: Source detections.
        frames_to_drop: Frame indices to exclude.

    Returns:
        New DetectionResult without the dropped frames. The original is
        unmodified.
    """
    drop = set(frames_to_drop)
    kept = {idx: fd for idx, fd in detections.frames.items() if idx not in drop}
    return DetectionResult(
        frames=kept,
        camera_names=detections.camera_names,
        total_frames=len(kept),
    )
