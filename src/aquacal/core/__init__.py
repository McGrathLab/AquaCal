"""Core geometry modules."""

from aquacal.core.board import BoardGeometry
from aquacal.core.camera import Camera, undistort_points
from aquacal.core.interface_model import Interface, ray_plane_intersection
from aquacal.core.refractive_geometry import (
    NAN_REASON_ABOVE_INTERFACE,
    NAN_REASON_BEHIND_CAMERA,
    NAN_REASON_INTERFACE_BELOW_CAMERA,
    NAN_REASON_NONE,
    refractive_back_project,
    refractive_project,
    refractive_project_batch,
    refractive_project_batch_newton_diagnostic,
    refractive_project_newton_diagnostic,
    snells_law_3d,
    trace_ray_air_to_water,
)

__all__ = [
    "BoardGeometry",
    "Camera",
    "undistort_points",
    "Interface",
    "ray_plane_intersection",
    "snells_law_3d",
    "trace_ray_air_to_water",
    "refractive_project",
    "refractive_project_batch",
    "refractive_back_project",
    "refractive_project_newton_diagnostic",
    "refractive_project_batch_newton_diagnostic",
    "NAN_REASON_NONE",
    "NAN_REASON_INTERFACE_BELOW_CAMERA",
    "NAN_REASON_ABOVE_INTERFACE",
    "NAN_REASON_BEHIND_CAMERA",
]
