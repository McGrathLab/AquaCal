"""Calibration pipeline modules."""

from aquacal.calibration.extrinsics import (
    Observation,
    PoseGraph,
    build_pose_graph,
    estimate_board_pose,
    estimate_extrinsics,
    refractive_solve_pnp,
)
from aquacal.calibration.frame_rejection import (
    FrameRejectionResult,
    compute_per_frame_rms,
    drop_frames,
    identify_outlier_frames,
)
from aquacal.calibration.interface_estimation import (
    optimize_interface,
)
from aquacal.calibration.intrinsics import (
    calibrate_intrinsics_all,
    calibrate_intrinsics_single,
    validate_view_diversity,
)
from aquacal.calibration.pipeline import (
    build_interface_spread_report,
    calibrate_from_detections,
    load_config,
    run_calibration,
    run_calibration_from_config,
    split_detections,
)
from aquacal.calibration.point_refinement import refine_calibration
from aquacal.calibration.refinement import (
    joint_refinement,
)

__all__ = [
    # intrinsics
    "calibrate_intrinsics_single",
    "calibrate_intrinsics_all",
    "validate_view_diversity",
    # extrinsics
    "Observation",
    "PoseGraph",
    "estimate_board_pose",
    "refractive_solve_pnp",
    "build_pose_graph",
    "estimate_extrinsics",
    # interface_estimation
    "optimize_interface",
    # frame rejection
    "FrameRejectionResult",
    "compute_per_frame_rms",
    "identify_outlier_frames",
    "drop_frames",
    # refinement
    "joint_refinement",
    # point refinement
    "refine_calibration",
    # pipeline
    "calibrate_from_detections",
    "load_config",
    "split_detections",
    "run_calibration",
    "run_calibration_from_config",
    "build_interface_spread_report",
]
