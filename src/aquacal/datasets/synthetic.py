"""Synthetic data generation for testing and validation.

This module provides functions to generate synthetic calibration data with known
ground truth. The main entry point is ``create_scenario()`` which returns
predefined test scenarios with complete ground truth.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from numpy.typing import NDArray

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


def generate_camera_array(
    n_cameras: int,
    layout: str = "grid",
    spacing: float = 0.1,
    height_above_water: float = 0.15,
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
        height_above_water: Mean interface distance (meters)
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
    - Common ``water_z = 1.031 m`` (the calibrated value).

    Returns:
        Tuple of ``(intrinsics, extrinsics, water_zs)`` dicts keyed by
        camera name (cam0 … cam11).
    """
    IMAGE_SIZE = (1600, 1200)
    WATER_Z = 1.031

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


def generate_board_trajectory(
    n_frames: int,
    camera_positions: dict[str, NDArray[np.float64]],
    water_zs: dict[str, float],
    depth_range: tuple[float, float] = (0.3, 0.6),
    xy_extent: float = 0.15,
    rotation_range_deg: float = 15.0,
    min_cameras_per_frame: int = 2,
    seed: int = 42,
) -> list[BoardPose]:
    """
    Generate board poses ensuring pose graph connectivity.

    Creates a trajectory that ensures:
    - Each frame is visible by at least min_cameras_per_frame cameras
    - The pose graph is connected (can chain from reference to all cameras)
    - Board stays within reasonable depth range underwater

    Args:
        n_frames: Number of frames to generate
        camera_positions: Dict of camera center positions (from extrinsics)
        water_zs: Per-camera interface distances
        depth_range: (min_z, max_z) for board center in world coords
        xy_extent: Maximum XY offset from origin
        rotation_range_deg: Maximum board tilt from horizontal
        min_cameras_per_frame: Minimum cameras that must see board
        seed: Random seed

    Returns:
        List of BoardPose objects with frame indices 0 to n_frames-1
    """
    rng = np.random.default_rng(seed)

    poses: list[BoardPose] = []
    for frame_idx in range(n_frames):
        # Position: random within extent, random depth
        x = rng.uniform(-xy_extent, xy_extent)
        y = rng.uniform(-xy_extent, xy_extent)
        z = rng.uniform(depth_range[0], depth_range[1])
        tvec = np.array([x, y, z], dtype=np.float64)

        # Rotation: small tilts, full in-plane rotation
        max_tilt = np.deg2rad(rotation_range_deg)
        rx = rng.uniform(-max_tilt, max_tilt)
        ry = rng.uniform(-max_tilt, max_tilt)
        rz = rng.uniform(-np.pi, np.pi)
        rvec = np.array([rx, ry, rz], dtype=np.float64)

        poses.append(BoardPose(frame_idx=frame_idx, rvec=rvec, tvec=tvec))

    return poses


def generate_real_rig_trajectory(
    n_frames: int = 100,
    depth_range: tuple[float, float] = (1.1, 2.0),
    seed: int = 42,
) -> list[BoardPose]:
    """Generate board trajectory appropriate for the real rig geometry.

    The real rig has cameras at Z ≈ 0 with water surface at Z ≈ 1.03 m, so
    the board should be below the water surface (default 1.1–2.0 m, i.e.
    ~70–970 mm below the surface).

    Trajectory covers the full field of view:

    - Positions sweep across the ~1.3 × 1.2 m footprint of the camera array
    - Ensures connectivity by visiting regions seen by multiple cameras

    Args:
        n_frames: Number of frames to generate
        depth_range: (min_z, max_z) for board center in world coords
        seed: Random seed

    Returns:
        List of BoardPose objects
    """
    rng = np.random.default_rng(seed)

    # The rig spans ~1.3m in X (-1.00 to +0.34) and ~1.2m in Y (0 to 1.19).
    # Center of the rig footprint is approximately (-0.34, 0.55).
    # Board should move throughout this area to ensure all cameras see it.
    X_CENTER, Y_CENTER = -0.34, 0.55
    XY_EXTENT = 0.7  # +/-700mm from center to ensure full coverage
    ROTATION_RANGE_DEG = 20.0

    poses: list[BoardPose] = []
    for frame_idx in range(n_frames):
        # Position: random within footprint, random depth
        x = X_CENTER + rng.uniform(-XY_EXTENT, XY_EXTENT)
        y = Y_CENTER + rng.uniform(-XY_EXTENT, XY_EXTENT)
        z = rng.uniform(depth_range[0], depth_range[1])
        tvec = np.array([x, y, z], dtype=np.float64)

        # Rotation: small tilts, full in-plane rotation
        max_tilt = np.deg2rad(ROTATION_RANGE_DEG)
        rx = rng.uniform(-max_tilt, max_tilt)
        ry = rng.uniform(-max_tilt, max_tilt)
        rz = rng.uniform(-np.pi, np.pi)
        rvec = np.array([rx, ry, rz], dtype=np.float64)

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

    Args:
        intrinsics: Per-camera intrinsics
        extrinsics: Per-camera extrinsics
        water_zs: Per-camera interface distances
        board: Board geometry
        board_poses: List of board poses
        noise_std: Gaussian noise standard deviation (pixels)
        min_corners: Minimum corners for valid detection
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


def create_scenario(name: str, seed: int = 42) -> SyntheticScenario:
    """Create a predefined test scenario with complete ground truth.

    Available scenarios:

    - ``'ideal'``: 4 cameras, 20 frames, 0 noise — verify math correctness
    - ``'minimal'``: 2 cameras, 10 frames, 0.3 px noise — edge case
    - ``'realistic'``: 12 cameras matching actual hardware, 30 frames, 0.5 px noise

    All presets use the same ChArUco board (12x9 squares, 60 mm square size,
    45 mm marker size, DICT_5X5_100).

    Args:
        name: Scenario name (``'ideal'``, ``'minimal'``, or ``'realistic'``)
        seed: Random seed for reproducibility

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
        intrinsics, extrinsics, distances = generate_camera_array(
            n_cameras=4,
            layout="grid",
            spacing=0.1,
            height_above_water=0.15,
            height_variation=0.0,
            seed=seed,
        )
        camera_positions = {cam: ext.C for cam, ext in extrinsics.items()}
        board_poses = generate_board_trajectory(
            n_frames=20,
            camera_positions=camera_positions,
            water_zs=distances,
            depth_range=(0.25, 0.45),
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
            description="Ideal conditions: 4 cameras, 20 frames, 0 noise",
        )

    elif name == "minimal":
        intrinsics, extrinsics, distances = generate_camera_array(
            n_cameras=2,
            layout="line",
            spacing=0.15,
            height_above_water=0.15,
            height_variation=0.003,
            seed=seed,
        )
        camera_positions = {cam: ext.C for cam, ext in extrinsics.items()}
        board_poses = generate_board_trajectory(
            n_frames=10,
            camera_positions=camera_positions,
            water_zs=distances,
            depth_range=(0.25, 0.40),
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
            description="Minimal scenario: 2 cameras, 10 frames, 0.3px noise",
        )

    elif name == "realistic":
        intrinsics, extrinsics, distances = generate_real_rig_array()
        board_poses = generate_real_rig_trajectory(
            n_frames=30,
            depth_range=(1.1, 2.0),
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
        )

    valid_names = ["ideal", "minimal", "realistic"]
    raise ValueError(f"Unknown scenario: '{name}'. Valid names: {valid_names}")
