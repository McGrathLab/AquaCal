"""Stage 2: Extrinsic initialization via pose graph."""

from __future__ import annotations

import heapq
from collections import deque
from collections.abc import Callable
from dataclasses import dataclass, field

import cv2
import numpy as np
from numpy.typing import NDArray
from scipy.optimize import least_squares

from aquacal.calibration._observability import _bump
from aquacal.config.schema import (
    CameraExtrinsics,
    CameraIntrinsics,
    ConnectivityError,
    DetectionResult,
)
from aquacal.core.board import BoardGeometry
from aquacal.core.camera import Camera
from aquacal.core.interface_model import Interface
from aquacal.core.refractive_geometry import refractive_project
from aquacal.utils.transforms import compose_poses, invert_pose, rvec_to_matrix


@dataclass
class Observation:
    """A single camera's observation of the board in one frame."""

    camera: str
    frame_idx: int
    corner_ids: NDArray[np.int32]  # shape (N,)
    corners_2d: NDArray[np.float64]  # shape (N, 2)


@dataclass
class PoseGraph:
    """
    Graph connecting cameras through shared board observations.

    Cameras connect indirectly: if cameras A and B both see the board in
    frame F, they are linked through that frame's board pose node.

    Attributes:
        camera_names: List of all camera names in the graph
        frame_indices: List of frame indices with 2+ camera observations
        observations: All camera-board observations
        adjacency: Dict mapping each node to its neighbors for connectivity analysis.
                   Node names: camera names (str) and frame indices prefixed with "f" (e.g., "f42")
    """

    camera_names: list[str]
    frame_indices: list[int]
    observations: list[Observation]
    adjacency: dict[str, set[str]] = field(default_factory=dict)


def estimate_board_pose(
    intrinsics: CameraIntrinsics,
    corners_2d: NDArray[np.float64],
    corner_ids: NDArray[np.int32],
    board: BoardGeometry,
    discard_stats_out: dict[str, int] | None = None,
) -> tuple[NDArray[np.float64], NDArray[np.float64]] | None:
    """
    Estimate board pose relative to camera using PnP.

    Args:
        intrinsics: Camera intrinsic parameters
        corners_2d: Detected corner positions, shape (N, 2)
        corner_ids: Corner IDs corresponding to corners_2d, shape (N,)
        board: Board geometry for 3D corner positions
        discard_stats_out: Optional counter dict, populated in place. When None
            (the default) no accounting happens and behaviour is unchanged.
            Counts `pnp_attempts_nonrefractive`, `pnp_too_few_corners` and
            `pnp_solve_failed`.

    Returns:
        Tuple of (rvec, tvec) representing board pose in camera frame,
        or None if PnP fails (e.g., too few points).
        - rvec: Rodrigues rotation vector, shape (3,)
        - tvec: Translation vector, shape (3,)

    Note:
        `refractive_solve_pnp` calls this for its initial guess but deliberately
        does NOT pass `discard_stats_out` down -- doing so would count a refractive
        attempt in the non-refractive branch and break the denominator
        decomposition `check_discard_invariants` enforces. That inner failure is
        counted there as `pnp_initial_guess_failed` instead.

    Example:
        >>> result = estimate_board_pose(intrinsics, corners, ids, board)
        >>> if result is not None:
        ...     rvec, tvec = result
    """
    _bump(discard_stats_out, "pnp_attempts_total")
    _bump(discard_stats_out, "pnp_attempts_nonrefractive")

    if len(corner_ids) < 4:
        _bump(discard_stats_out, "pnp_too_few_corners")
        return None

    # Get 3D points in board frame
    object_points = board.get_corner_array(corner_ids).astype(np.float32)
    image_points = corners_2d.astype(np.float32)

    # Run PnP
    success, rvec, tvec = cv2.solvePnP(
        object_points,
        image_points,
        intrinsics.K.astype(np.float64),
        intrinsics.dist_coeffs.astype(np.float64),
        flags=cv2.SOLVEPNP_ITERATIVE,
    )

    if not success:
        _bump(discard_stats_out, "pnp_solve_failed")
        return None

    return rvec.flatten().astype(np.float64), tvec.flatten().astype(np.float64)


def refractive_solve_pnp(
    intrinsics: CameraIntrinsics,
    corners_2d: NDArray[np.float64],
    corner_ids: NDArray[np.int32],
    board: BoardGeometry,
    water_z: float,
    interface_normal: NDArray[np.float64] | None = None,
    n_air: float = 1.0,
    n_water: float = 1.333,
    discard_stats_out: dict[str, int] | None = None,
) -> tuple[NDArray[np.float64], NDArray[np.float64]] | None:
    """
    Estimate board pose with refractive correction using LM refinement.

    Uses standard solvePnP as initial guess, applies rough depth correction,
    then refines by minimizing refractive reprojection error.

    The key trick: use an identity-extrinsics camera so camera frame = world
    frame. Board corners transformed by the candidate pose become "world points"
    that get projected through the refractive interface.

    Args:
        intrinsics: Camera intrinsic parameters
        corners_2d: Detected corner positions, shape (N, 2)
        corner_ids: Corner IDs corresponding to corners_2d, shape (N,)
        board: Board geometry for 3D corner positions
        water_z: Distance from camera to water surface in meters
        interface_normal: Interface normal vector. If None, uses [0, 0, -1].
        n_air: Refractive index of air (default 1.0)
        n_water: Refractive index of water (default 1.333)
        discard_stats_out: Optional counter dict, populated in place. When None
            (the default) no accounting happens and behaviour is unchanged.
            Counts `pnp_attempts_refractive`, `pnp_initial_guess_failed`,
            `pnp_nonfinite_refinement` and `pnp_guard_rejected`.

    Returns:
        Tuple of (rvec, tvec) representing board pose in camera frame, or None
        if PnP fails or if the refined pose does not explain its own data (see
        note below).

    Note:
        ``cv2.solvePnP`` reports ``success=True`` for degenerate configurations
        -- a near-minimal, nearly collinear corner set can return a translation
        of order 1e12 m. The returned pose is self-checked here and rejected if
        the refractive model cannot project a single one of the corners the
        pose was fitted to. That is a threshold-free test: a pose which explains
        none of its own observations is not a pose. Returning None lets the
        caller fall back to another observation, which every call site in this
        module already handles.
    """
    _bump(discard_stats_out, "pnp_attempts_total")
    _bump(discard_stats_out, "pnp_attempts_refractive")

    # Get initial guess from standard PnP. `discard_stats_out` is deliberately NOT
    # threaded into this call -- see estimate_board_pose's Note. This attempt is
    # already counted as refractive above; counting it again in the non-refractive
    # branch would break the denominator decomposition.
    result = estimate_board_pose(intrinsics, corners_2d, corner_ids, board)
    if result is None:
        _bump(discard_stats_out, "pnp_initial_guess_failed")
        return None

    rvec_init, tvec_init = result

    # Apply rough depth correction for refraction
    tvec_init[2] *= n_water

    if interface_normal is None:
        interface_normal = np.array([0.0, 0.0, -1.0], dtype=np.float64)

    # Set up identity-extrinsics camera (camera frame = world frame)
    identity_ext = CameraExtrinsics(R=np.eye(3), t=np.zeros(3))
    camera = Camera("_pnp", intrinsics, identity_ext)
    interface = Interface(
        normal=interface_normal,
        camera_distances={"_pnp": water_z},
        n_air=n_air,
        n_water=n_water,
    )

    # Get 3D object points in board frame
    object_points = board.get_corner_array(corner_ids).astype(np.float64)
    image_points = corners_2d.astype(np.float64)
    n_pts = len(object_points)

    def residuals(x: NDArray[np.float64]) -> NDArray[np.float64]:
        rvec = x[:3]
        tvec = x[3:]
        R = rvec_to_matrix(rvec)
        # Board corners in camera frame (= world frame for identity camera)
        pts_cam = (R @ object_points.T).T + tvec
        resid = np.empty(n_pts * 2, dtype=np.float64)
        for i, pt in enumerate(pts_cam):
            projected = refractive_project(camera, interface, pt)
            if projected is None:
                resid[2 * i] = 100.0
                resid[2 * i + 1] = 100.0
            else:
                resid[2 * i] = projected[0] - image_points[i, 0]
                resid[2 * i + 1] = projected[1] - image_points[i, 1]
        return resid

    x0 = np.concatenate([rvec_init, tvec_init])

    result_opt = least_squares(residuals, x0, method="lm", max_nfev=200)

    if not np.all(np.isfinite(result_opt.x)):
        _bump(discard_stats_out, "pnp_nonfinite_refinement")
        return None

    rvec_out = result_opt.x[:3].astype(np.float64)
    tvec_out = result_opt.x[3:].astype(np.float64)

    # Self-check: reject a pose that explains none of its own data. A degenerate
    # solvePnP result places the board where the refractive model cannot project
    # any corner at all, so every residual above was the flat invalid penalty --
    # the fit was blind. A merely imprecise pose still projects all its corners.
    pts_cam = (rvec_to_matrix(rvec_out) @ object_points.T).T + tvec_out
    if not any(refractive_project(camera, interface, pt) is not None for pt in pts_cam):
        _bump(discard_stats_out, "pnp_guard_rejected")
        return None

    return rvec_out, tvec_out


def _find_connected_components(
    adjacency: dict[str, set[str]],
    camera_names: list[str],
) -> list[set[str]]:
    """Find connected components in the pose graph using BFS."""
    visited: set[str] = set()
    components: list[set[str]] = []

    for start in camera_names:
        if start in visited:
            continue

        # BFS from this camera
        component: set[str] = set()
        queue = deque([start])

        while queue:
            node = queue.popleft()
            if node in visited:
                continue
            visited.add(node)
            component.add(node)

            for neighbor in sorted(adjacency.get(node, [])):
                if neighbor not in visited:
                    queue.append(neighbor)

        components.append(component)

    return components


def build_pose_graph(
    detections: DetectionResult,
    min_cameras: int = 2,
) -> PoseGraph:
    """
    Build pose graph from detection results.

    Creates a bipartite graph where cameras and frames are nodes,
    connected by observation edges. Only includes frames where
    at least min_cameras see the board.

    Args:
        detections: Detection results from detect_all_frames
        min_cameras: Minimum cameras per frame to include (default 2)

    Returns:
        PoseGraph with adjacency structure for connectivity analysis

    Raises:
        ConnectivityError: If the graph is not connected (some cameras
            cannot be linked to others through shared observations).
            Error message includes details about disconnected components.

    Example:
        >>> detections = detect_all_frames(videos, board)
        >>> pose_graph = build_pose_graph(detections, min_cameras=2)
        >>> print(f"Graph has {len(pose_graph.frame_indices)} usable frames")
    """
    # Filter frames with enough cameras
    usable_frames = detections.get_frames_with_min_cameras(min_cameras)

    if not usable_frames:
        raise ConnectivityError(
            f"No frames with {min_cameras}+ cameras detecting the board"
        )

    # Collect observations and build adjacency
    observations: list[Observation] = []
    adjacency: dict[str, set[str]] = {}
    camera_set: set[str] = set()

    for frame_idx in usable_frames:
        frame_node = f"f{frame_idx}"
        if frame_node not in adjacency:
            adjacency[frame_node] = set()

        frame_det = detections.frames[frame_idx]
        for cam_name, det in frame_det.detections.items():
            camera_set.add(cam_name)

            # Add observation
            observations.append(
                Observation(
                    camera=cam_name,
                    frame_idx=frame_idx,
                    corner_ids=det.corner_ids,
                    corners_2d=det.corners_2d,
                )
            )

            # Build adjacency (bipartite: cameras <-> frames)
            if cam_name not in adjacency:
                adjacency[cam_name] = set()
            adjacency[cam_name].add(frame_node)
            adjacency[frame_node].add(cam_name)

    camera_names = sorted(camera_set)

    # Check connectivity
    components = _find_connected_components(adjacency, camera_names)
    if len(components) > 1:
        # Format error message with component details
        comp_strs = []
        for i, comp in enumerate(components):
            cameras_in_comp = [n for n in comp if not n.startswith("f")]
            comp_strs.append(f"Component {i + 1}: {cameras_in_comp}")
        raise ConnectivityError(
            f"Pose graph is not connected. Found {len(components)} components:\n"
            + "\n".join(comp_strs)
        )

    return PoseGraph(
        camera_names=camera_names,
        frame_indices=sorted(usable_frames),
        observations=observations,
        adjacency=adjacency,
    )


def _average_rotations(
    rotations: list[NDArray[np.float64]],
    weights: list[float],
) -> NDArray[np.float64]:
    """Compute weighted chordal L2 mean of rotation matrices.

    Projects the weighted sum of rotation matrices back to SO(3) via SVD.

    Args:
        rotations: List of 3x3 rotation matrices
        weights: List of non-negative weights (one per rotation)

    Returns:
        3x3 rotation matrix representing the weighted average
    """
    M = np.zeros((3, 3), dtype=np.float64)
    for R, w in zip(rotations, weights):
        M += w * R

    U, _, Vt = np.linalg.svd(M)
    R_avg = U @ Vt

    # Ensure proper rotation (det = +1)
    if np.linalg.det(R_avg) < 0:
        U[:, -1] *= -1
        R_avg = U @ Vt

    return R_avg


def _refine_poses_multi_frame(
    camera_poses: dict[str, tuple[NDArray, NDArray]],
    board_poses: dict[int, tuple[NDArray, NDArray]],
    obs_index: dict[tuple[str, int], Observation],
    pose_graph: PoseGraph,
    intrinsics: dict[str, CameraIntrinsics],
    board: BoardGeometry,
    reference_camera: str,
    water_zs: dict[str, float] | None = None,
    interface_normal: NDArray[np.float64] | None = None,
    n_air: float = 1.0,
    n_water: float = 1.333,
    discard_stats_out: dict[str, int] | None = None,
) -> tuple[dict[str, tuple[NDArray, NDArray]], dict[int, tuple[NDArray, NDArray]]]:
    """Refine poses via one pass of multi-frame averaging.

    Step A: For each frame, re-estimate board pose from all cameras that see it,
    then average. Step B: For each non-reference camera, re-estimate camera pose
    from all frames it sees, then average.

    Args:
        camera_poses: Dict of camera_name -> (R, t) world->camera
        board_poses: Dict of frame_idx -> (R, t) board->world
        obs_index: Dict of (camera_name, frame_idx) -> Observation
        pose_graph: The pose graph
        intrinsics: Per-camera intrinsics
        board: Board geometry
        reference_camera: Camera fixed at world origin
        water_zs: Optional per-camera interface distances
        interface_normal: Interface normal vector
        n_air: Refractive index of air
        n_water: Refractive index of water

    Returns:
        Tuple of (refined_camera_poses, refined_board_poses)
    """
    refined_board_poses = dict(board_poses)
    refined_camera_poses = dict(camera_poses)

    # Step A: Refine board poses
    for frame_idx in sorted(board_poses.keys()):
        frame_node = f"f{frame_idx}"
        cam_neighbors = sorted(pose_graph.adjacency.get(frame_node, []))

        rotations = []
        translations = []
        weights = []

        for cam_name in cam_neighbors:
            if cam_name not in camera_poses:
                continue
            obs_maybe = obs_index.get((cam_name, frame_idx))
            if obs_maybe is None:
                _bump(discard_stats_out, "observation_absent")
                continue
            obs = obs_maybe

            # PnP: board in camera frame
            if water_zs is not None and cam_name in water_zs:
                result = refractive_solve_pnp(
                    intrinsics[cam_name],
                    obs.corners_2d,
                    obs.corner_ids,
                    board,
                    water_zs[cam_name],
                    interface_normal,
                    n_air,
                    n_water,
                    discard_stats_out=discard_stats_out,
                )
            else:
                result = estimate_board_pose(
                    intrinsics[cam_name],
                    obs.corners_2d,
                    obs.corner_ids,
                    board,
                    discard_stats_out=discard_stats_out,
                )
            if result is None:
                _bump(discard_stats_out, "pose_discarded_by_consumer")
                continue

            rvec_bc, tvec_bc = result
            R_bc = cv2.Rodrigues(rvec_bc)[0].astype(np.float64)

            # board_in_world = cam_in_world @ board_in_cam
            cam_R, cam_t = camera_poses[cam_name]
            R_cw, t_cw = invert_pose(cam_R, cam_t)
            R_bw, t_bw = compose_poses(R_cw, t_cw, R_bc, tvec_bc)

            rotations.append(R_bw)
            translations.append(t_bw)
            weights.append(float(len(obs.corner_ids)))

        if len(rotations) >= 1:
            R_avg = _average_rotations(rotations, weights)
            w_total = sum(weights)
            t_avg = sum(w * t for w, t in zip(weights, translations)) / w_total
            refined_board_poses[frame_idx] = (R_avg, t_avg)

    # Step B: Refine camera poses
    for cam_name in sorted(camera_poses.keys()):
        if cam_name == reference_camera:
            continue

        cam_neighbors = sorted(pose_graph.adjacency.get(cam_name, []))

        rotations = []
        translations = []
        weights = []

        for frame_node in cam_neighbors:
            frame_idx = int(frame_node[1:])
            if frame_idx not in refined_board_poses:
                continue
            obs_maybe = obs_index.get((cam_name, frame_idx))
            if obs_maybe is None:
                _bump(discard_stats_out, "observation_absent")
                continue
            obs = obs_maybe

            # PnP: board in camera frame
            if water_zs is not None and cam_name in water_zs:
                result = refractive_solve_pnp(
                    intrinsics[cam_name],
                    obs.corners_2d,
                    obs.corner_ids,
                    board,
                    water_zs[cam_name],
                    interface_normal,
                    n_air,
                    n_water,
                    discard_stats_out=discard_stats_out,
                )
            else:
                result = estimate_board_pose(
                    intrinsics[cam_name],
                    obs.corners_2d,
                    obs.corner_ids,
                    board,
                    discard_stats_out=discard_stats_out,
                )
            if result is None:
                _bump(discard_stats_out, "pose_discarded_by_consumer")
                continue

            rvec_bc, tvec_bc = result
            R_bc = cv2.Rodrigues(rvec_bc)[0].astype(np.float64)

            # world_in_cam = board_in_cam @ world_in_board
            R_bw, t_bw = refined_board_poses[frame_idx]
            R_wb, t_wb = invert_pose(R_bw, t_bw)
            R_wc, t_wc = compose_poses(R_bc, tvec_bc, R_wb, t_wb)

            rotations.append(R_wc)
            translations.append(t_wc)
            weights.append(float(len(obs.corner_ids)))

        if len(rotations) >= 1:
            R_avg = _average_rotations(rotations, weights)
            w_total = sum(weights)
            t_avg = sum(w * t for w, t in zip(weights, translations)) / w_total
            refined_camera_poses[cam_name] = (R_avg, t_avg)

    return refined_camera_poses, refined_board_poses


def estimate_extrinsics(
    pose_graph: PoseGraph,
    intrinsics: dict[str, CameraIntrinsics],
    board: BoardGeometry,
    reference_camera: str | None = None,
    water_zs: dict[str, float] | None = None,
    interface_normal: NDArray[np.float64] | None = None,
    n_air: float = 1.0,
    n_water: float = 1.333,
    progress_callback: Callable[[str, int, int], None] | None = None,
    discard_stats_out: dict[str, int] | None = None,
) -> dict[str, CameraExtrinsics]:
    """
    Estimate camera extrinsics by chaining poses through the graph.

    Uses a best-first traversal from reference camera, ordered by observation
    corner count (highest first), computing each camera's pose relative to
    world frame (centered at reference camera).

    The algorithm fixes the reference camera at world origin (R=I, t=0),
    then runs a best-first traversal through the pose graph. When visiting a
    frame node from a known camera, it computes the board pose via PnP. When visiting a
    camera node from a known frame, it computes the camera pose via PnP
    and inversion.

    Each node popped from the heap is finalised on first discovery: every one of
    its unvisited neighbours is resolved in that single pass and marked visited
    immediately, so a node is never re-prioritised or recomputed even if an edge
    carrying more corners is discovered later. This distinguishes the traversal
    from Prim's algorithm, which would keep updating a frontier node's best edge
    until the node is extracted.

    Args:
        pose_graph: Pose graph from build_pose_graph
        intrinsics: Dict mapping camera names to intrinsics
        board: Board geometry
        reference_camera: Camera to place at world origin.
            If None, uses first camera name (sorted).
        water_zs: Optional dict mapping camera names to interface
            distances in meters. When provided, uses refractive PnP for
            cameras with known distances.
        interface_normal: Interface normal vector. If None, uses [0, 0, -1].
        n_air: Refractive index of air (default 1.0)
        n_water: Refractive index of water (default 1.333)
        progress_callback: Optional callback(camera_name, cameras_located, total_cameras)
            called after each camera is located during the best-first traversal

    Returns:
        Dict mapping camera names to CameraExtrinsics.
        Reference camera has R=I, t=0.

    Raises:
        ValueError: If reference_camera not in pose_graph
        ValueError: If intrinsics missing for any camera in graph

    Example:
        >>> extrinsics = estimate_extrinsics(pose_graph, intrinsics, board)
        >>> cam0_pose = extrinsics['cam0']
        >>> print(f"cam0 at world origin: {np.allclose(cam0_pose.t, 0)}")
    """
    # Validate reference camera
    if reference_camera is None:
        reference_camera = pose_graph.camera_names[0]
    elif reference_camera not in pose_graph.camera_names:
        raise ValueError(f"Reference camera '{reference_camera}' not in pose graph")

    # Validate intrinsics
    for cam in pose_graph.camera_names:
        if cam not in intrinsics:
            raise ValueError(f"Missing intrinsics for camera '{cam}'")

    # Index observations by (camera, frame) for quick lookup
    obs_index: dict[tuple[str, int], Observation] = {}
    for obs in pose_graph.observations:
        obs_index[(obs.camera, obs.frame_idx)] = obs

    # Initialize poses
    # camera_poses: R, t transforming world -> camera
    # board_poses: R, t transforming board -> world (for each frame)
    camera_poses: dict[str, tuple[NDArray, NDArray]] = {}
    board_poses: dict[int, tuple[NDArray, NDArray]] = {}

    # Reference camera at origin
    camera_poses[reference_camera] = (
        np.eye(3, dtype=np.float64),
        np.zeros(3, dtype=np.float64),
    )

    # Report progress for reference camera
    total_cameras = len(pose_graph.camera_names)
    if progress_callback is not None:
        progress_callback(reference_camera, 1, total_cameras)

    # Best-first traversal to propagate poses, ordered by corner count (highest first)
    # Heap entries: (-num_corners, node_name) — negative for max-heap behavior
    visited_cameras: set[str] = {reference_camera}
    visited_frames: set[int] = set()

    # Seed heap with reference camera (max priority)
    heap: list[tuple[int, str]] = [(0, reference_camera)]

    while heap:
        _priority, node = heapq.heappop(heap)

        if not node.startswith("f"):
            # Camera node - propagate to connected frames
            cam_name = node
            if cam_name not in camera_poses:
                continue
            cam_R, cam_t = camera_poses[cam_name]

            # Collect unvisited neighboring frames with a usable observation, in
            # adjacency order. No scoring or sorting happens here: each is pushed
            # onto the shared heap with priority -len(obs.corner_ids), and the
            # corner-count prioritisation happens globally via that heap.
            frame_neighbors = []
            for neighbor in pose_graph.adjacency.get(cam_name, []):
                frame_idx = int(neighbor[1:])  # "f42" -> 42
                if frame_idx in visited_frames:
                    continue
                obs_maybe = obs_index.get((cam_name, frame_idx))
                if obs_maybe is None:
                    _bump(discard_stats_out, "observation_absent")
                    continue
                frame_neighbors.append((frame_idx, obs_maybe))

            for frame_idx, obs in frame_neighbors:
                if frame_idx in visited_frames:
                    continue

                if water_zs is not None and cam_name in water_zs:
                    result = refractive_solve_pnp(
                        intrinsics[cam_name],
                        obs.corners_2d,
                        obs.corner_ids,
                        board,
                        water_zs[cam_name],
                        interface_normal,
                        n_air,
                        n_water,
                        discard_stats_out=discard_stats_out,
                    )
                else:
                    result = estimate_board_pose(
                        intrinsics[cam_name],
                        obs.corners_2d,
                        obs.corner_ids,
                        board,
                        discard_stats_out=discard_stats_out,
                    )
                if result is None:
                    _bump(discard_stats_out, "pose_discarded_by_consumer")
                    continue

                rvec_bc, tvec_bc = result  # board in camera frame
                R_bc: NDArray[np.float64] = cv2.Rodrigues(rvec_bc)[0].astype(np.float64)

                # board_in_world = cam_in_world @ board_in_cam
                R_cw, t_cw = invert_pose(cam_R, cam_t)  # camera in world
                R_bw, t_bw = compose_poses(R_cw, t_cw, R_bc, tvec_bc)  # board in world

                board_poses[frame_idx] = (R_bw, t_bw)
                visited_frames.add(frame_idx)
                # Priority: negative corner count for max-heap; tie-break by name
                heapq.heappush(heap, (-len(obs.corner_ids), f"f{frame_idx}"))

        else:
            # Frame node - propagate to connected cameras
            frame_idx = int(node[1:])
            if frame_idx not in board_poses:
                continue

            R_bw, t_bw = board_poses[frame_idx]

            # Collect unvisited neighboring cameras with a usable observation, in
            # sorted() order. No scoring or sorting by corner count happens here:
            # each is pushed onto the shared heap with priority -len(obs.corner_ids),
            # and the corner-count prioritisation happens globally via that heap.
            cam_neighbors = []
            for neighbor in sorted(pose_graph.adjacency.get(node, [])):
                cam_name = neighbor
                if cam_name in visited_cameras:
                    continue
                obs_maybe = obs_index.get((cam_name, frame_idx))
                if obs_maybe is None:
                    _bump(discard_stats_out, "observation_absent")
                    continue
                cam_neighbors.append((cam_name, obs_maybe))

            for cam_name, obs in cam_neighbors:
                if cam_name in visited_cameras:
                    continue

                if water_zs is not None and cam_name in water_zs:
                    result = refractive_solve_pnp(
                        intrinsics[cam_name],
                        obs.corners_2d,
                        obs.corner_ids,
                        board,
                        water_zs[cam_name],
                        interface_normal,
                        n_air,
                        n_water,
                        discard_stats_out=discard_stats_out,
                    )
                else:
                    result = estimate_board_pose(
                        intrinsics[cam_name],
                        obs.corners_2d,
                        obs.corner_ids,
                        board,
                        discard_stats_out=discard_stats_out,
                    )
                if result is None:
                    _bump(discard_stats_out, "pose_discarded_by_consumer")
                    continue

                rvec_bc, tvec_bc = result  # board in camera frame
                R_bc = cv2.Rodrigues(rvec_bc)[0].astype(np.float64)

                # world_in_cam = board_in_cam @ world_in_board
                R_wb, t_wb = invert_pose(R_bw, t_bw)
                R_wc, t_wc = compose_poses(R_bc, tvec_bc, R_wb, t_wb)

                camera_poses[cam_name] = (R_wc, t_wc)
                visited_cameras.add(cam_name)
                if progress_callback is not None:
                    progress_callback(cam_name, len(visited_cameras), total_cameras)
                heapq.heappush(heap, (-len(obs.corner_ids), cam_name))

    # Multi-frame averaging refinement pass
    if progress_callback is not None:
        progress_callback("_averaging", len(visited_cameras), total_cameras)
    camera_poses, board_poses = _refine_poses_multi_frame(
        camera_poses,
        board_poses,
        obs_index,
        pose_graph,
        intrinsics,
        board,
        reference_camera,
        water_zs,
        interface_normal,
        n_air,
        n_water,
        discard_stats_out=discard_stats_out,
    )

    # Convert to CameraExtrinsics
    extrinsics_result: dict[str, CameraExtrinsics] = {}
    for cam_name in pose_graph.camera_names:
        if cam_name not in camera_poses:
            raise ValueError(f"Could not determine pose for camera '{cam_name}'")
        R, t = camera_poses[cam_name]
        extrinsics_result[cam_name] = CameraExtrinsics(R=R, t=t)

    return extrinsics_result
