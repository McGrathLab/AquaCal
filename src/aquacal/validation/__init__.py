"""Validation and diagnostics modules."""

from aquacal.validation.comparison import (
    ComparisonResult,
    compare_calibrations,
    write_comparison_report,
)
from aquacal.validation.conditioning import (
    ConditioningMemoryError,
    ConditioningReport,
    compute_conditioning,
    load_conditioning_report,
    save_conditioning_report,
)
from aquacal.validation.diagnostics import (
    plot_error_distribution,
    plot_per_camera_error,
)
from aquacal.validation.evaluation import HeldOutEvaluation, evaluate_calibration

__all__ = [
    # diagnostics
    "plot_per_camera_error",
    "plot_error_distribution",
    # comparison
    "compare_calibrations",
    "ComparisonResult",
    "write_comparison_report",
    # conditioning
    "ConditioningMemoryError",
    "ConditioningReport",
    "compute_conditioning",
    "load_conditioning_report",
    "save_conditioning_report",
    # evaluation
    "evaluate_calibration",
    "HeldOutEvaluation",
]
