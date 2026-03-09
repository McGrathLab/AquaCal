"""Synthetic ground truth generation for full pipeline testing.

This module re-exports ``create_scenario`` from the public ``aquacal.datasets``
API and provides additional test-specific utilities.
"""

from __future__ import annotations

from aquacal.datasets.synthetic import (
    SyntheticScenario,  # noqa: F401
    compute_calibration_errors,  # noqa: F401
    create_scenario,  # noqa: F401
    generate_board_trajectory,  # noqa: F401
    generate_camera_array,  # noqa: F401
    generate_camera_intrinsics,  # noqa: F401
    generate_dense_xy_grid,  # noqa: F401
    generate_real_rig_array,  # noqa: F401
    generate_real_rig_trajectory,  # noqa: F401
    generate_synthetic_detections,  # noqa: F401
)
