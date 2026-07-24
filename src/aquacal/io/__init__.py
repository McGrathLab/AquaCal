"""Input/output modules."""

# Public API - will be populated as modules are implemented
__all__ = [
    # From video.py (Task 3.1):
    "VideoSet",
    # From images.py (Phase 6):
    "ImageSet",
    # From frameset.py (Phase 6):
    "FrameSet",
    # From detection.py (Task 3.2):
    "detect_charuco",
    "detect_all_frames",
    # From serialization.py (Task 3.3):
    "save_calibration",
    "load_calibration",
    # From internals.py (Phase 16 observability hooks):
    "INTERNALS_DIRNAME",
    "ensure_internals_dir",
    "warn_if_overwriting",
    # From benchmark.py (Phase 19 benchmark instrumentation):
    "capture_environment",
    "capture_peak_memory",
    "assemble_benchmark_record",
    "write_benchmark_json",
]

# Imports will be added as modules are implemented:
from aquacal.io.benchmark import (
    assemble_benchmark_record,
    capture_environment,
    capture_peak_memory,
    write_benchmark_json,
)
from aquacal.io.detection import detect_all_frames, detect_charuco
from aquacal.io.frameset import FrameSet
from aquacal.io.images import ImageSet
from aquacal.io.internals import (
    INTERNALS_DIRNAME,
    ensure_internals_dir,
    warn_if_overwriting,
)
from aquacal.io.serialization import load_calibration, save_calibration
from aquacal.io.video import VideoSet
