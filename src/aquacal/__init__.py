"""AquaCal: Refractive multi-camera calibration library."""

from importlib.metadata import version as _get_version

__version__ = _get_version("aquacal")

# Load/save calibration results
# Run calibration
from aquacal.calibration.pipeline import (
    calibrate_from_detections,
    load_config,
    run_calibration,
)

# Refinement API
from aquacal.calibration.point_refinement import refine_calibration

# Core types
from aquacal.config.schema import (
    CalibrationResult,
    CameraCalibration,
    CameraDrift,
    CameraExtrinsics,
    CameraIntrinsics,
    PointCorrespondence,
    RefinementResult,
    ValidationReport,
)
from aquacal.io.serialization import load_calibration, save_calibration

__all__ = [
    "__version__",
    # Load/save
    "load_calibration",
    "save_calibration",
    # Core types
    "CalibrationResult",
    "CameraDrift",
    "CameraCalibration",
    "CameraIntrinsics",
    "CameraExtrinsics",
    "PointCorrespondence",
    "RefinementResult",
    "ValidationReport",
    # Run calibration
    "calibrate_from_detections",
    "run_calibration",
    "load_config",
    # Refinement API
    "refine_calibration",
]
