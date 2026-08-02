"""Synthetic data generation for testing and validation.

This module provides functions to generate synthetic calibration data with known
ground truth. The main entry point is ``create_scenario()`` which returns
predefined test scenarios with complete ground truth.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

import numpy as np
from numpy.typing import NDArray
from scipy.spatial.transform import Rotation

from aquacal.config.schema import (
    BoardConfig,
    BoardPose,
    CalibrationResult,
    CameraExtrinsics,
    CameraIntrinsics,
    Detection,
    DetectionResult,
    FrameDetections,
)
from aquacal.core.board import BoardGeometry
from aquacal.core.camera import Camera
from aquacal.core.interface_model import Interface
from aquacal.core.refractive_geometry import refractive_project
from aquacal.utils.transforms import rvec_to_matrix


@dataclass
class SyntheticScenario:
    """Complete synthetic test scenario with ground truth.

    Attributes:
        name: Scenario name
        board_config: ChArUco board specification
        intrinsics: Per-camera intrinsics
        extrinsics: Per-camera extrinsics
        water_zs: Per-camera interface distances (Z-coordinate of water surface)
        board_poses: List of board poses for all frames
        noise_std: Gaussian noise standard deviation applied to detections (pixels)
        description: Human-readable description
        images: Optional dict of rendered images (camera_name -> frame_idx -> image)
        n_air: Refractive index of the medium above the interface, recorded as
            ground truth. Does not by itself generate detections at this index —
            callers must also pass it to ``generate_synthetic_detections``.
        n_water: Refractive index of the medium below the interface, recorded as
            ground truth. Does not by itself generate detections at this index —
            callers must also pass it to ``generate_synthetic_detections``.
        seed: Random seed used to generate this scenario's geometry and
            trajectory, recorded for reproducibility (HOOK-06).
    """

    name: str
    board_config: BoardConfig
    intrinsics: dict[str, CameraIntrinsics]
    extrinsics: dict[str, CameraExtrinsics]
    water_zs: dict[str, float]
    board_poses: list[BoardPose]
    noise_std: float
    description: str
    images: dict[str, dict[int, NDArray]] | None = None
    n_air: float = 1.0
    n_water: float = 1.333
    seed: int = 42


def generate_camera_intrinsics(
    image_size: tuple[int, int] = (1920, 1080),
    fov_horizontal_deg: float = 60.0,
    principal_point_offset: tuple[float, float] = (0.0, 0.0),
    distortion_k1: float = 0.0,
    distortion_k2: float = 0.0,
) -> CameraIntrinsics:
    """
    Generate camera intrinsics with specified parameters.

    Args:
        image_size: (width, height) in pixels
        fov_horizontal_deg: Horizontal field of view in degrees
        principal_point_offset: Offset from image center (pixels)
        distortion_k1: First radial distortion coefficient
        distortion_k2: Second radial distortion coefficient

    Returns:
        CameraIntrinsics with computed K matrix and distortion
    """
    width, height = image_size

    # Compute focal length from horizontal FOV
    # fov = 2 * atan(width / (2 * fx))
    # => fx = width / (2 * tan(fov/2))
    fov_rad = np.deg2rad(fov_horizontal_deg)
    fx = width / (2 * np.tan(fov_rad / 2))
    fy = fx  # Square pixels

    # Principal point at image center plus offset
    cx = width / 2 + principal_point_offset[0]
    cy = height / 2 + principal_point_offset[1]

    K = np.array(
        [
            [fx, 0.0, cx],
            [0.0, fy, cy],
            [0.0, 0.0, 1.0],
        ],
        dtype=np.float64,
    )

    # Distortion coefficients: [k1, k2, p1, p2, k3]
    dist_coeffs = np.array(
        [distortion_k1, distortion_k2, 0.0, 0.0, 0.0], dtype=np.float64
    )

    return CameraIntrinsics(K=K, dist_coeffs=dist_coeffs, image_size=image_size)


def _rotation_z(angle: float) -> NDArray[np.float64]:
    """Create rotation matrix for rotation around Z axis."""
    c, s = np.cos(angle), np.sin(angle)
    return np.array(
        [
            [c, -s, 0],
            [s, c, 0],
            [0, 0, 1],
        ],
        dtype=np.float64,
    )


# FROZEN DESIGN CONSTANT -- do NOT re-derive from a calibration.
#
# Provenance: this value came from an early calibration of the real rig,
# which has since been SUPERSEDED. The 2026-07-31 re-run of that rig, on
# code carrying the degenerate-PnP guard, puts its interface at 1.0738 m --
# and the run it originally came from is now known not to have converged
# (its Stage-3 intrinsic pass sat at first-order optimality 2.08e4, where
# the re-run reaches 18.4).
#
# It is deliberately NOT updated to 1.0738, and must not be updated to
# whatever the next calibration reports. The exact value is IMMATERIAL:
# the synthetic rig approximates the real one, it does not reproduce it,
# and ~1 m of air gap is what the geometry needs to be representative.
# Tracking a measured quantity here is what created the problem -- every
# bug fix that improved the calibration silently invalidated this constant
# and, through it, every experiment built on the scenario.
#
# Changing it is a real cost, not a cosmetic edit: E4 and E6's grid family
# is deliberately coupled to this value (D-29,
# experiments/e4_benchmark_grid.py GRID_HEIGHT_ABOVE_WATER), so a change
# here invalidates the committed nine-cell benchmark grid as well as every
# realistic-path experiment (E1, E3, E5, E7).
#
# D-19.3-09: this constant is also generate_camera_array's default
# height_above_water below, and both the "ideal" and "minimal"
# create_scenario presets' standoff -- it is no longer specific to the
# real-rig array. The library can no longer construct a mis-framed rig
# (cameras a few tens of cm from a board framed for 1-2 m) by accident.
WATER_Z: float = 1.031


def generate_camera_array(
    n_cameras: int,
    layout: str = "grid",
    spacing: float = 0.1,
    height_above_water: float = WATER_Z,
    height_variation: float = 0.005,
    image_size: tuple[int, int] = (1920, 1080),
    fov_deg: float = 60.0,
    seed: int = 42,
) -> tuple[dict[str, CameraIntrinsics], dict[str, CameraExtrinsics], dict[str, float]]:
    """
    Generate a realistic camera array with known ground truth.

    Args:
        n_cameras: Number of cameras (2-14)
        layout: Camera arrangement - "grid", "line", or "ring"
        spacing: Distance between adjacent cameras (meters)
        height_above_water: Mean interface distance (meters). Defaults to the
            module-level ``WATER_Z`` (the real-rig standoff, ~1.031 m;
            D-19.3-09) -- not a shallow 0.15 m tank. A lens framed for a
            1-2 m board-to-camera range needs a standoff in that range to
            avoid over-filling the frame; pass an explicit shallower value
            only when that mismatch is intentional.
        height_variation: Std dev of per-camera height variation (meters)
        image_size: Image dimensions (width, height)
        fov_deg: Horizontal field of view
        seed: Random seed for reproducibility

    Returns:
        Tuple of (intrinsics, extrinsics, water_zs) dicts keyed by camera name.
        Camera "cam0" is always the reference camera at origin with identity rotation.
    """
    rng = np.random.default_rng(seed)

    intrinsics: dict[str, CameraIntrinsics] = {}
    extrinsics: dict[str, CameraExtrinsics] = {}
    distances: dict[str, float] = {}

    # Generate camera positions based on layout
    positions: list[NDArray[np.float64]] = []

    if layout == "grid":
        # Arrange in rough square grid
        side = int(np.ceil(np.sqrt(n_cameras)))
        for i in range(n_cameras):
            row, col = i // side, i % side
            x = (col - (side - 1) / 2) * spacing
            y = (row - (side - 1) / 2) * spacing
            positions.append(np.array([x, y, 0.0], dtype=np.float64))
    elif layout == "line":
        for i in range(n_cameras):
            positions.append(np.array([i * spacing, 0.0, 0.0], dtype=np.float64))
    elif layout == "ring":
        angles = np.linspace(0, 2 * np.pi, n_cameras, endpoint=False)
        radius = spacing * n_cameras / (2 * np.pi)
        for a in angles:
            positions.append(
                np.array(
                    [radius * np.cos(a), radius * np.sin(a), 0.0], dtype=np.float64
                )
            )
    else:
        raise ValueError(f"Unknown layout: {layout}")

    # Center positions so cam0 is at origin
    offset = positions[0].copy()
    positions = [p - offset for p in positions]

    for i, pos in enumerate(positions):
        cam_name = f"cam{i}"

        # Intrinsics: same for all cameras
        intrinsics[cam_name] = generate_camera_intrinsics(
            image_size=image_size,
            fov_horizontal_deg=fov_deg,
        )

        # Extrinsics: cameras look straight down
        # Add small random roll for realism (but not for reference camera)
        if i == 0:
            roll = 0.0
        else:
            roll = rng.uniform(-0.1, 0.1)  # radians

        R = _rotation_z(roll)
        t = -R @ pos

        extrinsics[cam_name] = CameraExtrinsics(R=R, t=t)

        # Interface distance with small variation
        if i == 0:
            dist = height_above_water  # Reference camera: exact height
        else:
            dist = height_above_water + rng.normal(0, height_variation)
        distances[cam_name] = dist

    return intrinsics, extrinsics, distances


def generate_real_rig_array() -> tuple[
    dict[str, CameraIntrinsics], dict[str, CameraExtrinsics], dict[str, float]
]:
    """Generate camera array matching the real-world 12-camera rig.

    Geometry is derived from an actual calibration of the AquaCal hardware rig
    (12 cameras, e3v8250 excluded) with the following idealizations applied:

    - Common intrinsics: focal length, principal point, and distortion are
      averaged across all 12 cameras.
    - All cameras placed at Z = 0 (average real Z ≈ 0).
    - All optical axes aligned to world +Z (looking straight down); real
      cameras deviate < 5 deg.
    - XY positions preserved from the real calibration.
    - Common ``water_z = 1.031 m`` -- a FROZEN DESIGN CONSTANT, not a live
      measurement. See the module-level ``WATER_Z`` constant (above, near
      ``generate_camera_array``) before changing or "updating" it.

    This rig is an **approximation** of the real hardware, not a replica. No
    claim of numerical correspondence is made or intended, and none should be
    added: the idealizations above (common intrinsics, Z = 0, axes aligned to
    +Z) already depart from the real array by more than any plausible drift in
    the interface height.

    Returns:
        Tuple of ``(intrinsics, extrinsics, water_zs)`` dicts keyed by
        camera name (cam0 … cam11).
    """
    IMAGE_SIZE = (1600, 1200)

    # Uses the frozen module-level WATER_Z constant (defined above, near
    # generate_camera_array) -- see its own comment block for the full
    # provenance and the reason it must never be re-derived from a
    # calibration.

    # Averaged intrinsics across 12 real cameras
    K = np.array(
        [
            [1587.79, 0.0, 780.22],
            [0.0, 1588.34, 601.74],
            [0.0, 0.0, 1.0],
        ],
        dtype=np.float64,
    )
    dist_coeffs = np.array(
        [-0.5022, 0.2968, 0.0006, 0.0025, -0.0552],
        dtype=np.float64,
    )
    common_intrinsics = CameraIntrinsics(
        K=K, dist_coeffs=dist_coeffs, image_size=IMAGE_SIZE
    )

    # XY positions from real calibration (world frame, Z forced to 0).
    # Derived from C = -R^T @ t for each camera in calibration.json,
    # excluding e3v8250.  Ordered CCW from the reference camera (cam0)
    # when viewed from above, so cam indices trace a spatial loop around
    # the rig.
    _POSITIONS_XY: list[tuple[float, float]] = [
        (0.0000, 0.0000),  # cam0  (reference, e3v829d)
        (0.2080, 0.2419),  # cam1  (e3v832e)
        (0.3353, 0.5730),  # cam2  (e3v82f9)
        (0.2227, 0.8684),  # cam3  (e3v83ef)
        (0.0039, 1.1490),  # cam4  (e3v83ee)
        (-0.3363, 1.1930),  # cam5  (e3v83e9)
        (-0.6801, 1.1523),  # cam6  (e3v83f1)
        (-0.8868, 0.8828),  # cam7  (e3v83eb)
        (-1.0023, 0.5654),  # cam8  (e3v83f0)
        (-0.8949, 0.2677),  # cam9  (e3v831e)
        (-0.6639, 0.0038),  # cam10 (e3v8334)
        (-0.3364, -0.0573),  # cam11 (e3v82e0)
    ]

    intrinsics: dict[str, CameraIntrinsics] = {}
    extrinsics: dict[str, CameraExtrinsics] = {}
    water_zs: dict[str, float] = {}

    R_identity = np.eye(3, dtype=np.float64)

    for i, (cx, cy) in enumerate(_POSITIONS_XY):
        cam_name = f"cam{i}"
        intrinsics[cam_name] = common_intrinsics
        t = np.array([-cx, -cy, 0.0], dtype=np.float64)
        extrinsics[cam_name] = CameraExtrinsics(R=R_identity.copy(), t=t)
        water_zs[cam_name] = WATER_Z

    return intrinsics, extrinsics, water_zs


# Module-level memoisation cache for `worst_upward_corner_excursion`. Keyed on
# the `BoardConfig` field values plus `rotation_range_deg` so the (fairly
# expensive) rotation sweep runs at most once per distinct (board, tilt)
# combination -- not once per frame and not once per preset import.
_EXCURSION_CACHE: dict[tuple, float] = {}


def worst_upward_corner_excursion(
    board: BoardConfig, rotation_range_deg: float
) -> float:
    """Compute the largest distance any board corner rises above the board
    CENTRE over the generators' rotation sampling box (D-19.3-01).

    Evaluated deterministically -- NOT by random sampling and NOT by a
    closed-form combination of the two tilt angles via a diagonal (root-2)
    scaling factor, both rejected by D-19.3-01 because the closed form
    over-approximates once ``rz`` spans the full +/-pi range and a random
    sample is not a bound. The board-local corner cloud (from
    ``BoardGeometry(board).corner_positions``) is re-centred on its own
    centroid -- matching D-19.3-19's re-centred pose semantics, where a pose's
    ``tvec`` places the board centre, not a corner -- then swept over
    ``rvec = (rx, ry, rz)`` with ``rx, ry`` each spanning
    ``linspace(-theta, +theta, 41)`` (``theta = deg2rad(rotation_range_deg)``)
    and ``rz`` spanning ``linspace(-pi, pi, 180, endpoint=False)``. Because a
    world corner's Z offset from the centre is ``R[2, :] @ local``, only each
    rotation's third matrix row is needed, built vectorised via
    ``Rotation.from_rotvec(rvecs).as_matrix()[:, 2, :]``. World +Z is DOWN
    (into water), so "upward" excursion is ``max(-(R[2, :] @ local))`` over
    all sampled rotations and all corners.

    Results are memoised on a hashable key built from ``board``'s field
    values and ``rotation_range_deg`` -- the sweep is not re-run per frame or
    per preset import.

    Args:
        board: ChArUco board specification. The corner cloud is derived from
            ``BoardGeometry(board).corner_positions``, so the excursion moves
            whenever any of ``squares_x``, ``squares_y`` or ``square_size``
            changes -- it is never a restated constant.
        rotation_range_deg: Maximum board tilt from horizontal, in degrees.
            Matches the generators' ``rotation_range_deg`` /
            ``ROTATION_RANGE_DEG`` sampling box.

    Returns:
        Worst-case upward excursion above the board centre, in meters.

    Example:
        >>> default_board = BoardConfig(
        ...     squares_x=12, squares_y=9, square_size=0.060,
        ...     marker_size=0.045, dictionary="DICT_5X5_100",
        ... )
        >>> excursion = worst_upward_corner_excursion(default_board, 15.0)
        >>> 0.12 < excursion < 0.14
        True
    """
    cache_key = (
        board.squares_x,
        board.squares_y,
        board.square_size,
        board.marker_size,
        board.dictionary,
        board.legacy_pattern,
        float(rotation_range_deg),
    )
    cached = _EXCURSION_CACHE.get(cache_key)
    if cached is not None:
        return cached

    geometry = BoardGeometry(board)
    corners_local = np.array(list(geometry.corner_positions.values()), dtype=np.float64)
    centroid = corners_local.mean(axis=0)
    corners_centered = corners_local - centroid

    theta = np.deg2rad(rotation_range_deg)
    rx_vals = np.linspace(-theta, theta, 41)
    ry_vals = np.linspace(-theta, theta, 41)
    rz_vals = np.linspace(-np.pi, np.pi, 180, endpoint=False)

    rx_grid, ry_grid, rz_grid = np.meshgrid(rx_vals, ry_vals, rz_vals, indexing="ij")
    rvecs = np.stack([rx_grid.ravel(), ry_grid.ravel(), rz_grid.ravel()], axis=1)
    # Only the third row of each rotation matrix is needed, since a corner's
    # world Z offset from the pivot is R[2, :] @ local.
    third_rows = Rotation.from_rotvec(rvecs).as_matrix()[:, 2, :]  # (N, 3)

    worst = 0.0
    for local in corners_centered:
        z_offsets = third_rows @ local  # (N,), world +Z is DOWN
        upward = -z_offsets
        worst = max(worst, float(np.max(upward)))

    _EXCURSION_CACHE[cache_key] = worst
    return worst


def board_clearance_floor(
    board: BoardConfig,
    water_zs: Mapping[str, float],
    rotation_range_deg: float,
    margin_factor: float = 0.1,
) -> float:
    """Derive the minimum legal board-centre depth that keeps every corner
    submerged (D-19.3-01).

    ``min_depth = max(water_zs) + (1.0 + margin_factor) *
    worst_upward_corner_excursion(board, rotation_range_deg)``.

    The bound itself -- ``worst_upward_corner_excursion`` -- is derived from
    the board's own corner cloud and the sampled rotation range; it is never
    hardcoded. ``margin_factor`` (default 0.1, i.e. ``k = 0.1``) is a
    *declared safety factor applied to that derived quantity* -- categorically
    different from adding an arbitrary constant to make a failing case pass
    (19.2 anti-pattern #6). This is safe **only so long as `margin_factor` is
    never adjusted in response to a failing run**: if a scenario fails the
    clearance check, the scenario's depth range moves, not `margin_factor`.

    Uses ``max(water_zs.values())`` -- the DEEPEST per-camera interface --
    not the mean and not a frozen constant like ``WATER_Z``, because
    interface tilt makes ``water_zs`` vary per camera and the constraint
    binds on the deepest one.

    Args:
        board: ChArUco board specification, forwarded to
            ``worst_upward_corner_excursion``.
        water_zs: Per-camera interface distances (Z-coordinate of the water
            surface in world frame). The floor is anchored at the deepest
            value.
        rotation_range_deg: Maximum board tilt from horizontal, in degrees,
            forwarded to ``worst_upward_corner_excursion``.
        margin_factor: Fractional safety factor applied to the derived
            excursion (default 0.1). See the safety-factor framing above --
            never adjust this to make a failing scenario pass.

    Returns:
        Minimum legal board-centre depth (Z, meters) below which a corner
        could rise above the deepest interface.
    """
    excursion = worst_upward_corner_excursion(board, rotation_range_deg)
    return max(water_zs.values()) + (1.0 + margin_factor) * excursion


def generate_board_trajectory(
    n_frames: int,
    camera_positions: dict[str, NDArray[np.float64]],
    water_zs: dict[str, float],
    *,
    board: BoardConfig,
    depth_range: tuple[float, float] | None = None,
    xy_extent: float = 0.15,
    rotation_range_deg: float = 15.0,
    min_cameras_per_frame: int = 2,
    seed: int = 42,
    center: tuple[float, float] | None = None,
) -> list[BoardPose]:
    """
    Generate board poses ensuring pose graph connectivity.

    Creates a trajectory that ensures:
    - Each frame is visible by at least min_cameras_per_frame cameras
    - The pose graph is connected (can chain from reference to all cameras)
    - Board stays within reasonable depth range underwater, with every corner
      kept below the deepest interface (D-19.3-01, enforced via
      ``board_clearance_floor``)

    D-19.3-19: poses are re-centred so ``tvec`` genuinely places the board
    CENTRE in world coordinates, matching this docstring's ``depth_range``
    claim (which, pre-fix, was documentation of intent that the code did not
    implement -- the pose positioned a corner, not the centre). After
    sampling ``rvec``, the sampled ``(x, y, z)`` is treated as the desired
    world position of the centroid of ``BoardGeometry(board).corner_positions``,
    and ``tvec`` is computed as ``sampled_xyz - R @ centroid_local`` so that
    ``R @ centroid_local + tvec == sampled_xyz``. The RNG call order and
    count are unchanged, so the sampled ``(x, y, z, rx, ry, rz)`` sequence
    stays bit-identical for a given seed -- only ``tvec`` is offset from what
    it would have been pre-fix.

    D-19.3-05: ``board`` is a REQUIRED keyword-only parameter (deliberately
    breaking this codebase's usual trailing-kwarg-with-safe-default pattern).
    An optional path that could skip the clearance check is the exact defect
    shape this fix removes, so there is no default and no way to bypass it.

    D-19.3-04: when ``depth_range`` is omitted (``None``), it resolves to
    ``(board_clearance_floor(board, water_zs, rotation_range_deg), 2.0)`` --
    the derived floor and a fixed 2.0 m ceiling. When ``depth_range`` IS
    supplied and its minimum is below the derived floor, this raises
    ``ValueError`` naming both the floor and the supplied minimum, before any
    pose is emitted. No clamping and no warn-and-continue.

    D-27: ``center`` defaults to the CENTROID of ``camera_positions``, not to
    the origin and not to this function's pre-D-27 behaviour.
    ``generate_camera_array`` recentres every layout so that ``cam0`` sits at
    the origin, and ``cam0`` is never the middle of the array under any
    layout -- it is a corner under ``"grid"`` and an end under ``"line"``.
    Sampling the working volume about the origin therefore pins the
    calibration volume to an arbitrary corner camera, by an amount that
    differs per layout (see ``19.2-GAP-CONTEXT.md`` D-27). There is no
    scenario in which that is the desired behaviour, so the default is
    corrected rather than preserved for backwards compatibility. Pass
    ``center=(0.0, 0.0)`` explicitly to reproduce the pre-D-27 behaviour
    exactly for a given seed -- the RNG call order and count are unchanged,
    so the sampled offsets from ``center`` are bit-identical to the old
    offsets from the origin.

    Args:
        n_frames: Number of frames to generate
        camera_positions: Dict of camera center positions (from extrinsics).
            Used to compute the default ``center`` (the mean of the XY
            positions) when ``center`` is not passed explicitly.
        water_zs: Per-camera interface distances
        board: ChArUco board specification. Required -- used to derive the
            clearance floor (D-19.3-01) and to compute the corner centroid
            for re-centring (D-19.3-19).
        depth_range: (min_z, max_z) for the board CENTRE in world coords.
            Defaults to ``(board_clearance_floor(...), 2.0)`` when ``None``.
            Raises ``ValueError`` if an explicit minimum is below the
            derived floor.
        xy_extent: Maximum XY offset from ``center``
        rotation_range_deg: Maximum board tilt from horizontal
        min_cameras_per_frame: Minimum cameras that must see board
        seed: Random seed
        center: (x, y) centre of the sampled working volume. Defaults to the
            centroid of ``camera_positions``' XY coordinates (D-27). Pass
            ``(0.0, 0.0)`` explicitly to reproduce pre-D-27 behaviour.

    Returns:
        List of BoardPose objects with frame indices 0 to n_frames-1

    Raises:
        ValueError: If ``depth_range[0]`` is below the derived clearance
            floor.
    """
    if center is None:
        xs = [float(p[0]) for p in camera_positions.values()]
        ys = [float(p[1]) for p in camera_positions.values()]
        cx, cy = float(np.mean(xs)), float(np.mean(ys))
    else:
        cx, cy = center

    floor = board_clearance_floor(board, water_zs, rotation_range_deg)
    if depth_range is None:
        depth_range = (floor, 2.0)
    elif depth_range[0] < floor:
        raise ValueError(
            f"depth_range[0]={depth_range[0]!r} is below the derived "
            f"clearance floor {floor:.4f} m (board={board!r}, "
            f"rotation_range_deg={rotation_range_deg}). A board centre "
            f"shallower than {floor:.4f} m can raise a corner above the "
            "deepest interface (D-19.3-01). Either raise depth_range[0] to "
            "at least the derived floor, or pass depth_range=None to use "
            "the derived default."
        )

    rng = np.random.default_rng(seed)

    geometry = BoardGeometry(board)
    centroid_local = np.mean(
        np.array(list(geometry.corner_positions.values()), dtype=np.float64),
        axis=0,
    )

    poses: list[BoardPose] = []
    for frame_idx in range(n_frames):
        # Position: random within extent (about center), random depth --
        # this is the world position of the board CENTRE (D-19.3-19).
        x = cx + rng.uniform(-xy_extent, xy_extent)
        y = cy + rng.uniform(-xy_extent, xy_extent)
        z = rng.uniform(depth_range[0], depth_range[1])
        sampled_xyz = np.array([x, y, z], dtype=np.float64)

        # Rotation: small tilts, full in-plane rotation
        max_tilt = np.deg2rad(rotation_range_deg)
        rx = rng.uniform(-max_tilt, max_tilt)
        ry = rng.uniform(-max_tilt, max_tilt)
        rz = rng.uniform(-np.pi, np.pi)
        rvec = np.array([rx, ry, rz], dtype=np.float64)

        R = rvec_to_matrix(rvec)
        tvec = sampled_xyz - R @ centroid_local

        poses.append(BoardPose(frame_idx=frame_idx, rvec=rvec, tvec=tvec))

    return poses


def generate_real_rig_trajectory(
    n_frames: int = 100,
    *,
    board: BoardConfig,
    depth_range: tuple[float, float] | None = None,
    water_zs: Mapping[str, float] | None = None,
    seed: int = 42,
) -> list[BoardPose]:
    """Generate board trajectory appropriate for the real rig geometry.

    The real rig has cameras at Z ≈ 0 with water surface at Z ≈ 1.03 m, so
    the board should be below the water surface. The default ``depth_range``
    is derived (D-19.3-01): ``(board_clearance_floor(board, water_zs, 20.0),
    2.0)``, which is ~1.220 m for this generator's own ``water_zs`` default
    (all cameras exactly ``WATER_Z = 1.031``) -- slightly below the phase
    reference figure of 1.226 m, because that reference was computed at
    ``max(water_zs) = 1.0367`` (the tilt-varied grid family), while this
    generator's own array has no interface tilt at all. That difference is
    the per-scenario derivation working correctly, not a defect.

    Trajectory covers the full field of view:

    - Positions sweep across the ~1.3 × 1.2 m footprint of the camera array
    - Ensures connectivity by visiting regions seen by multiple cameras

    D-19.3-19: poses are re-centred so ``tvec`` places the board CENTRE, not
    a corner -- see ``generate_board_trajectory``'s docstring for the full
    rationale, which applies identically here. The RNG call order and count
    are unchanged, so the sampled ``(x, y, z, rx, ry, rz)`` sequence stays
    bit-identical for a given seed; only ``tvec`` is offset.

    D-19.3-05: ``board`` is a REQUIRED keyword-only parameter, matching
    ``generate_board_trajectory``.

    D-19.3-04: when ``depth_range`` is omitted (``None``), it resolves to
    the derived ``(floor, 2.0)``. When supplied and below the derived floor,
    raises ``ValueError`` naming both the floor and the supplied value.

    Args:
        n_frames: Number of frames to generate
        board: ChArUco board specification. Required -- used to derive the
            clearance floor (D-19.3-01) and to compute the corner centroid
            for re-centring (D-19.3-19).
        depth_range: (min_z, max_z) for the board CENTRE in world coords.
            Defaults to the derived ``(floor, 2.0)`` when ``None``.
        water_zs: Per-camera interface distances used to derive the
            clearance floor. Defaults to ``generate_real_rig_array()``'s
            ``water_zs`` (all equal to the frozen ``WATER_Z``) when
            ``None``.
        seed: Random seed

    Returns:
        List of BoardPose objects

    Raises:
        ValueError: If ``depth_range[0]`` is below the derived clearance
            floor.
    """
    rng = np.random.default_rng(seed)

    # The rig spans ~1.3m in X (-1.00 to +0.34) and ~1.2m in Y (0 to 1.19).
    # Center of the rig footprint is approximately (-0.34, 0.55).
    # Board should move throughout this area to ensure all cameras see it.
    X_CENTER, Y_CENTER = -0.34, 0.55
    XY_EXTENT = 0.7  # +/-700mm from center to ensure full coverage
    ROTATION_RANGE_DEG = 20.0

    if water_zs is None:
        _, _, water_zs = generate_real_rig_array()

    floor = board_clearance_floor(board, water_zs, ROTATION_RANGE_DEG)
    if depth_range is None:
        depth_range = (floor, 2.0)
    elif depth_range[0] < floor:
        raise ValueError(
            f"depth_range[0]={depth_range[0]!r} is below the derived "
            f"clearance floor {floor:.4f} m (board={board!r}, "
            f"rotation_range_deg={ROTATION_RANGE_DEG}). A board centre "
            f"shallower than {floor:.4f} m can raise a corner above the "
            "deepest interface (D-19.3-01). Either raise depth_range[0] to "
            "at least the derived floor, or pass depth_range=None to use "
            "the derived default."
        )

    geometry = BoardGeometry(board)
    centroid_local = np.mean(
        np.array(list(geometry.corner_positions.values()), dtype=np.float64),
        axis=0,
    )

    poses: list[BoardPose] = []
    for frame_idx in range(n_frames):
        # Position: random within footprint, random depth -- world position
        # of the board CENTRE (D-19.3-19).
        x = X_CENTER + rng.uniform(-XY_EXTENT, XY_EXTENT)
        y = Y_CENTER + rng.uniform(-XY_EXTENT, XY_EXTENT)
        z = rng.uniform(depth_range[0], depth_range[1])
        sampled_xyz = np.array([x, y, z], dtype=np.float64)

        # Rotation: small tilts, full in-plane rotation
        max_tilt = np.deg2rad(ROTATION_RANGE_DEG)
        rx = rng.uniform(-max_tilt, max_tilt)
        ry = rng.uniform(-max_tilt, max_tilt)
        rz = rng.uniform(-np.pi, np.pi)
        rvec = np.array([rx, ry, rz], dtype=np.float64)

        R = rvec_to_matrix(rvec)
        tvec = sampled_xyz - R @ centroid_local

        poses.append(BoardPose(frame_idx=frame_idx, rvec=rvec, tvec=tvec))

    return poses


def generate_dense_xy_grid(
    depth: float,
    n_grid: int = 7,
    xy_extent: float = 0.5,
    xy_center: tuple[float, float] = (0.0, 0.0),
    tilt_deg: float = 3.0,
    frame_offset: int = 0,
    seed: int = 42,
) -> list[BoardPose]:
    """Generate board poses at a regular XY grid at a fixed depth.

    Used for dense spatial coverage in reconstruction evaluation and heatmaps.
    Each grid position has a small random tilt and random in-plane rotation.

    Args:
        depth: Z coordinate for all board poses (meters)
        n_grid: Number of grid positions per axis (total poses = n_grid^2)
        xy_extent: Grid spans from -xy_extent to +xy_extent around xy_center
            in X and Y (meters)
        xy_center: (x, y) center of the grid (meters). Should match the
            centroid of the camera array for best coverage.
        tilt_deg: Maximum random tilt from horizontal (degrees)
        frame_offset: Starting frame index (default 0)
        seed: Random seed for reproducible tilts and rotations

    Returns:
        List of n_grid^2 BoardPose objects with frame indices starting from
        frame_offset.
    """
    rng = np.random.default_rng(seed)

    # Generate grid positions centered on xy_center
    cx, cy = xy_center
    x_values = np.linspace(cx - xy_extent, cx + xy_extent, n_grid)
    y_values = np.linspace(cy - xy_extent, cy + xy_extent, n_grid)

    poses: list[BoardPose] = []
    frame_idx = frame_offset

    for x in x_values:
        for y in y_values:
            tvec = np.array([x, y, depth], dtype=np.float64)

            # Small random tilt + random in-plane rotation
            max_tilt = np.deg2rad(tilt_deg)
            rx = rng.uniform(-max_tilt, max_tilt)
            ry = rng.uniform(-max_tilt, max_tilt)
            rz = rng.uniform(-np.pi, np.pi)
            rvec = np.array([rx, ry, rz], dtype=np.float64)

            poses.append(BoardPose(frame_idx=frame_idx, rvec=rvec, tvec=tvec))
            frame_idx += 1

    return poses


def generate_synthetic_detections(
    intrinsics: dict[str, CameraIntrinsics],
    extrinsics: dict[str, CameraExtrinsics],
    water_zs: dict[str, float],
    board: BoardGeometry,
    board_poses: list[BoardPose],
    noise_std: float = 0.0,
    min_corners: int = 8,
    n_air: float = 1.0,
    n_water: float = 1.333,
    seed: int = 42,
) -> DetectionResult:
    """
    Generate synthetic detections by projecting through refractive interface.

    For each board pose and camera:
    1. Transform board corners to world coordinates
    2. Project each corner through refractive interface
    3. Add Gaussian noise to pixel coordinates
    4. Filter corners outside image bounds
    5. Only include camera if >= min_corners visible

    Generating detections at a refractive index different from the one used
    during calibration is exactly the WP4 evaluation-under-perturbed-assumptions
    setup: it measures how calibration accuracy degrades when the assumed
    refractive index does not match the true one.

    Args:
        intrinsics: Per-camera intrinsics
        extrinsics: Per-camera extrinsics
        water_zs: Per-camera interface distances
        board: Board geometry
        board_poses: List of board poses
        noise_std: Gaussian noise standard deviation (pixels)
        min_corners: Minimum corners for valid detection
        n_air: Refractive index of the medium above the interface
        n_water: Refractive index of the medium below the interface
        seed: Random seed for noise

    Returns:
        DetectionResult matching format from real detection pipeline
    """
    rng = np.random.default_rng(seed)
    interface_normal = np.array([0.0, 0.0, -1.0], dtype=np.float64)
    frames: dict[int, FrameDetections] = {}

    for bp in board_poses:
        corners_3d = board.transform_corners(bp.rvec, bp.tvec)
        detections_dict: dict[str, Detection] = {}

        for cam_name in intrinsics:
            camera = Camera(cam_name, intrinsics[cam_name], extrinsics[cam_name])
            interface = Interface(
                normal=interface_normal,
                camera_distances={cam_name: water_zs[cam_name]},
                n_air=n_air,
                n_water=n_water,
            )

            corner_ids: list[int] = []
            corners_2d: list[NDArray[np.float64]] = []

            for corner_id in range(board.num_corners):
                point_3d = corners_3d[corner_id]
                projected = refractive_project(camera, interface, point_3d)

                if projected is not None:
                    # Check if within image bounds
                    w, h = intrinsics[cam_name].image_size
                    if 0 <= projected[0] < w and 0 <= projected[1] < h:
                        corner_ids.append(corner_id)
                        px = projected.copy()
                        if noise_std > 0:
                            px += rng.normal(0, noise_std, 2)
                        corners_2d.append(px)

            if len(corner_ids) >= min_corners:
                detections_dict[cam_name] = Detection(
                    corner_ids=np.array(corner_ids, dtype=np.int32),
                    corners_2d=np.array(corners_2d, dtype=np.float64),
                )

        if detections_dict:
            frames[bp.frame_idx] = FrameDetections(
                frame_idx=bp.frame_idx,
                detections=detections_dict,
            )

    return DetectionResult(
        frames=frames,
        camera_names=list(intrinsics.keys()),
        total_frames=len(board_poses),
    )


def compute_calibration_errors(
    result: CalibrationResult,
    ground_truth: SyntheticScenario,
) -> dict[str, float]:
    """
    Compare calibration result to ground truth.

    Computes:
    - focal_length_error_percent: Max relative error in fx, fy
    - principal_point_error_px: Max error in cx, cy
    - rotation_error_deg: Max rotation error across cameras
    - translation_error_mm: Max translation error across cameras
    - water_z_error_mm: Max interface distance error

    Args:
        result: Calibration result from pipeline
        ground_truth: Synthetic scenario with known truth

    Returns:
        Dict of error metrics
    """
    max_focal_error_pct = 0.0
    max_pp_error_px = 0.0
    max_rotation_error_deg = 0.0
    max_translation_error_mm = 0.0
    max_interface_error_mm = 0.0

    for cam_name in ground_truth.intrinsics:
        if cam_name not in result.cameras:
            continue

        gt_intr = ground_truth.intrinsics[cam_name]
        gt_extr = ground_truth.extrinsics[cam_name]
        gt_dist = ground_truth.water_zs[cam_name]

        cal = result.cameras[cam_name]
        cal_intr = cal.intrinsics
        cal_extr = cal.extrinsics
        cal_dist = cal.water_z

        # Focal length error (relative)
        fx_gt, fy_gt = gt_intr.K[0, 0], gt_intr.K[1, 1]
        fx_cal, fy_cal = cal_intr.K[0, 0], cal_intr.K[1, 1]
        fx_err = abs(fx_cal - fx_gt) / fx_gt * 100
        fy_err = abs(fy_cal - fy_gt) / fy_gt * 100
        max_focal_error_pct = max(max_focal_error_pct, fx_err, fy_err)

        # Principal point error (absolute, pixels)
        cx_gt, cy_gt = gt_intr.K[0, 2], gt_intr.K[1, 2]
        cx_cal, cy_cal = cal_intr.K[0, 2], cal_intr.K[1, 2]
        pp_err = np.sqrt((cx_cal - cx_gt) ** 2 + (cy_cal - cy_gt) ** 2)
        max_pp_error_px = max(max_pp_error_px, pp_err)

        # Rotation error
        # Compute relative rotation: R_err = R_cal @ R_gt.T
        R_err = cal_extr.R @ gt_extr.R.T
        # Rotation angle from rotation matrix: angle = arccos((trace(R) - 1) / 2)
        trace = np.trace(R_err)
        # Clamp to valid range for arccos
        cos_angle = np.clip((trace - 1) / 2, -1.0, 1.0)
        angle_rad = np.arccos(cos_angle)
        angle_deg = np.rad2deg(angle_rad)
        max_rotation_error_deg = max(max_rotation_error_deg, angle_deg)

        # Translation error (in mm)
        # Camera center position difference
        C_gt = gt_extr.C
        C_cal = cal_extr.C
        trans_err_mm = np.linalg.norm(C_cal - C_gt) * 1000
        max_translation_error_mm = max(max_translation_error_mm, trans_err_mm)

        # Interface distance error (in mm)
        dist_err_mm = abs(cal_dist - gt_dist) * 1000
        max_interface_error_mm = max(max_interface_error_mm, dist_err_mm)

    return {
        "focal_length_error_percent": max_focal_error_pct,
        "principal_point_error_px": max_pp_error_px,
        "rotation_error_deg": max_rotation_error_deg,
        "translation_error_mm": max_translation_error_mm,
        "water_z_error_mm": max_interface_error_mm,
    }


def create_scenario(
    name: str, seed: int = 42, n_air: float = 1.0, n_water: float = 1.333
) -> SyntheticScenario:
    """Create a predefined test scenario with complete ground truth.

    Available scenarios:

    - ``'ideal'``: 4 cameras, 20 frames, 0 noise — verify math correctness
    - ``'minimal'``: 2 cameras, 10 frames, 0.3 px noise — edge case
    - ``'realistic'``: 12 cameras matching actual hardware, 30 frames, 0.5 px noise

    All presets use the same ChArUco board (12x9 squares, 60 mm square size,
    45 mm marker size, DICT_5X5_100) and share the real-rig standoff
    (D-19.3-09) -- none of them is a shallow-tank rig framed for a
    mismatched board-to-camera distance.

    ``create_scenario`` does not itself generate detections, so ``n_air`` and
    ``n_water`` are recorded on the returned scenario as ground-truth metadata
    only. Callers must pass the same values to ``generate_synthetic_detections``
    to actually generate detections at that refractive index.

    Args:
        name: Scenario name (``'ideal'``, ``'minimal'``, or ``'realistic'``)
        seed: Random seed for reproducibility
        n_air: Refractive index of the medium above the interface, recorded
            as ground truth on the returned scenario
        n_water: Refractive index of the medium below the interface, recorded
            as ground truth on the returned scenario

    Returns:
        SyntheticScenario with complete ground truth (intrinsics, extrinsics,
        interface distances, board poses).

    Raises:
        ValueError: If scenario name is not recognized.

    Examples:
        >>> from aquacal.datasets import create_scenario
        >>> scenario = create_scenario('ideal')
        >>> print(f"{len(scenario.intrinsics)} cameras, {len(scenario.board_poses)} frames")
        4 cameras, 20 frames
        >>>
        >>> scenario = create_scenario('realistic')
        >>> print(f"{len(scenario.intrinsics)} cameras")
        12 cameras
    """
    # Common board config (matches real hardware)
    default_board = BoardConfig(
        squares_x=12,
        squares_y=9,
        square_size=0.060,
        marker_size=0.045,
        dictionary="DICT_5X5_100",
    )

    if name == "ideal":
        # D-19.3-09: height_above_water is no longer passed explicitly, so
        # this preset falls through to generate_camera_array's own default
        # (the module-level WATER_Z, the real-rig standoff) instead of the
        # old 0.15 m shallow-tank value.
        intrinsics, extrinsics, distances = generate_camera_array(
            n_cameras=4,
            layout="grid",
            spacing=0.1,
            height_variation=0.0,
            seed=seed,
        )
        camera_positions = {cam: ext.C for cam, ext in extrinsics.items()}
        # depth_range is derived (D-19.3-01/GEOM-01) rather than the pre-fix
        # literal (0.25, 0.45), which sits below this preset's own derived
        # clearance floor.
        # xy_extent (0.08) is intentionally NOT re-derived here even though
        # the standoff just moved: whether it needs D-28-style derivation
        # from the new footprint is an open question (CONTEXT.md "Claude's
        # Discretion"), and deriving it alongside this geometry fix would
        # smuggle an observability change in with it -- the same reasoning
        # D-19.3-03 used to reject unifying the tilt ranges. Left open,
        # recorded in the SUMMARY.
        board_poses = generate_board_trajectory(
            n_frames=20,
            camera_positions=camera_positions,
            water_zs=distances,
            board=default_board,
            depth_range=None,
            xy_extent=0.08,
            seed=seed,
        )
        return SyntheticScenario(
            name="ideal",
            board_config=default_board,
            intrinsics=intrinsics,
            extrinsics=extrinsics,
            water_zs=distances,
            board_poses=board_poses,
            noise_std=0.0,
            description=(
                "Ideal conditions: 4 cameras, 20 frames, 0 noise, real-rig standoff"
            ),
            n_air=n_air,
            n_water=n_water,
            seed=seed,
        )

    elif name == "minimal":
        # D-19.3-09: height_above_water is no longer passed explicitly --
        # see the "ideal" branch's comment above; the same reasoning applies
        # here.
        intrinsics, extrinsics, distances = generate_camera_array(
            n_cameras=2,
            layout="line",
            spacing=0.15,
            height_variation=0.003,
            seed=seed,
        )
        camera_positions = {cam: ext.C for cam, ext in extrinsics.items()}
        # depth_range is derived (D-19.3-01/GEOM-01) -- see the "ideal"
        # branch's comment above; the same reasoning applies here.
        # xy_extent (0.06) is likewise intentionally NOT re-derived -- see
        # the "ideal" branch's comment above for why this is a deliberate
        # non-change with the derivation question left open.
        board_poses = generate_board_trajectory(
            n_frames=10,
            camera_positions=camera_positions,
            water_zs=distances,
            board=default_board,
            depth_range=None,
            xy_extent=0.06,
            seed=seed,
        )
        return SyntheticScenario(
            name="minimal",
            board_config=default_board,
            intrinsics=intrinsics,
            extrinsics=extrinsics,
            water_zs=distances,
            board_poses=board_poses,
            noise_std=0.3,
            description=(
                "Minimal scenario: 2 cameras, 10 frames, 0.3px noise, real-rig standoff"
            ),
            n_air=n_air,
            n_water=n_water,
            seed=seed,
        )

    elif name == "realistic":
        intrinsics, extrinsics, distances = generate_real_rig_array()
        # depth_range is derived (D-19.3-01/GEOM-01) rather than the pre-fix
        # literal (1.1, 2.0), which sits below the derived clearance floor
        # (~1.220 m) for this generator's own water_zs. D-19.3-10 records
        # that this specific call site's movement was expected: E1 and E7's
        # "realistic" runs move for exactly this reason.
        board_poses = generate_real_rig_trajectory(
            n_frames=30,
            board=default_board,
            depth_range=None,
            water_zs=distances,
            seed=seed,
        )
        return SyntheticScenario(
            name="realistic",
            board_config=default_board,
            intrinsics=intrinsics,
            extrinsics=extrinsics,
            water_zs=distances,
            board_poses=board_poses,
            noise_std=0.5,
            description="12-camera rig matching real hardware (idealized geometry)",
            n_air=n_air,
            n_water=n_water,
            seed=seed,
        )

    valid_names = ["ideal", "minimal", "realistic"]
    raise ValueError(f"Unknown scenario: '{name}'. Valid names: {valid_names}")
