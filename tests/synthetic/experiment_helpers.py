"""Thin re-export shim for the promoted experiment verbs.

Kept for backward compatibility with any code still importing from this path;
the real implementations live in ``aquacal.datasets.pipelines``.
"""

from __future__ import annotations

from aquacal.datasets.pipelines import (  # noqa: F401
    calibrate_synthetic,
    compute_per_camera_errors,
    evaluate_reconstruction,
)
