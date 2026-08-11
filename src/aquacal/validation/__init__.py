"""Validation and diagnostics modules."""

from aquacal.validation.comparison import (
    ComparisonResult,
    compare_calibrations,
    write_comparison_report,
)

# Experimental conditioning API: deliberately importable but not re-exported via
# __all__ (their own docstrings warn the return shape may change, and
# docs/api/validation.rst does not document them). Keep the imports so
# `from aquacal.validation import compute_conditioning` keeps working.
from aquacal.validation.conditioning import (  # noqa: F401
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
    # evaluation
    "evaluate_calibration",
    "HeldOutEvaluation",
]
