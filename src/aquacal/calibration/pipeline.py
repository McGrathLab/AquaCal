"""End-to-end calibration pipeline orchestration."""

from __future__ import annotations

import contextlib
import hashlib
import importlib.metadata
import json
import random
import time
import warnings
from collections.abc import Iterator
from datetime import datetime
from pathlib import Path

import cv2
import numpy as np
import yaml

from aquacal.calibration._observability import (
    OptimizerObserver,
    SolverDiagnostics,
    check_discard_invariants,
)
from aquacal.calibration.extrinsics import build_pose_graph, estimate_extrinsics
from aquacal.calibration.frame_rejection import (
    compute_per_frame_rms,
    drop_frames,
    identify_outlier_frames,
)
from aquacal.calibration.interface_estimation import (
    _compute_initial_board_poses,
    optimize_interface,
    register_auxiliary_camera,
)
from aquacal.calibration.intrinsics import calibrate_intrinsics_all
from aquacal.calibration.refinement import joint_refinement
from aquacal.config.schema import (
    BoardConfig,
    BoardPose,
    CalibrationConfig,
    CalibrationMetadata,
    CalibrationResult,
    CameraCalibration,
    CameraExtrinsics,
    CameraIntrinsics,
    DetectionResult,
    DiagnosticsData,
    FrameDetections,
    InterfaceParams,
    Vec3,
)
from aquacal.core.board import BoardGeometry
from aquacal.io.benchmark import (
    assemble_benchmark_record,
    capture_environment,
    capture_peak_memory,
    write_benchmark_json,
)
from aquacal.io.detection import detect_all_frames
from aquacal.io.internals import ensure_internals_dir, warn_if_overwriting
from aquacal.io.serialization import save_calibration
from aquacal.utils.transforms import matrix_to_rvec
from aquacal.validation.conditioning import save_conditioning_report
from aquacal.validation.diagnostics import (
    generate_diagnostic_report,
    save_diagnostic_report,
)
from aquacal.validation.evaluation import (
    _estimate_validation_poses,
    evaluate_calibration,
)
from aquacal.validation.reprojection import compute_reprojection_errors


def calibrate_from_detections(
    detections: DetectionResult,
    intrinsics: dict[str, CameraIntrinsics],
    board: BoardGeometry,
    *,
    reference_camera: str | None = None,
    n_air: float = 1.0,
    n_water: float = 1.333,
    loss: str = "huber",
    loss_scale: float = 1.0,
    min_corners: int = 4,
    verbose: int = 0,
    discard_stats_out: dict[str, int] | None = None,
) -> tuple[CalibrationResult, dict[int, BoardPose]]:
    """Run Stages 2-3 on pre-computed detections and return a CalibrationResult.

    This is a high-level convenience function that takes detections and intrinsics
    (typically from synthetic data or a previous detection step) and runs the
    extrinsic initialization (Stage 2) and joint refractive optimization (Stage 3).

    Args:
        detections: Detected corners across all cameras and frames.
        intrinsics: Per-camera intrinsic parameters.
        board: Board geometry used for detection.
        reference_camera: Name of the reference camera (identity extrinsics).
            Defaults to the first camera in sorted order.
        n_air: Refractive index of air.
        n_water: Refractive index of water.
        loss: Robust loss function for Stage 3 ('huber', 'cauchy', etc.).
        loss_scale: Scale parameter for the robust loss.
        min_corners: Minimum corners per detection to use.
        verbose: Verbosity level (0=silent, 1=summary, 2=per-iteration).

    Returns:
        Tuple of (CalibrationResult, board_poses) where board_poses maps
        frame index to the optimized BoardPose.

    Example:
        >>> from aquacal.datasets import create_scenario, generate_synthetic_detections
        >>> from aquacal.calibration import calibrate_from_detections
        >>> scenario = create_scenario("minimal")
        >>> board = BoardGeometry(scenario.board_config)
        >>> detections = generate_synthetic_detections(
        ...     scenario.intrinsics, scenario.extrinsics, scenario.water_zs,
        ...     board, scenario.board_poses, noise_std=scenario.noise_std,
        ... )
        >>> result, poses = calibrate_from_detections(
        ...     detections, scenario.intrinsics, board,
        ... )
        >>> print(f"RMS: {result.diagnostics.reprojection_error_rms:.3f} px")
    """
    camera_names = sorted(intrinsics.keys())
    if reference_camera is None:
        reference_camera = camera_names[0]
    interface_normal = np.array([0.0, 0.0, -1.0], dtype=np.float64)

    # Stage 2: Extrinsic initialization
    pose_graph = build_pose_graph(detections, min_cameras=2)
    initial_extrinsics = estimate_extrinsics(
        pose_graph,
        intrinsics,
        board,
        reference_camera,
    )

    # Stage 3: Joint refractive optimization
    opt_extrinsics, opt_distances, opt_poses_list, rms = optimize_interface(
        detections=detections,
        intrinsics=intrinsics,
        initial_extrinsics=initial_extrinsics,
        board=board,
        reference_camera=reference_camera,
        interface_normal=interface_normal,
        n_air=n_air,
        n_water=n_water,
        loss=loss,
        loss_scale=loss_scale,
        min_corners=min_corners,
        verbose=verbose,
        discard_stats_out=discard_stats_out,
        discard_stage="stage3_interface_optimization",
    )
    board_poses = {bp.frame_idx: bp for bp in opt_poses_list}

    # Build CalibrationResult
    interface_params = InterfaceParams(
        normal=interface_normal,
        n_air=n_air,
        n_water=n_water,
    )
    result = _build_calibration_result(
        intrinsics=intrinsics,
        extrinsics=opt_extrinsics,
        water_z_values=opt_distances,
        board_config=board.config,
        interface_params=interface_params,
        diagnostics=DiagnosticsData(
            reprojection_error_rms=rms,
            reprojection_error_per_camera={},
            validation_3d_error_mean=0.0,
            validation_3d_error_std=0.0,
        ),
        metadata=CalibrationMetadata(
            calibration_date=datetime.now().isoformat(),
            software_version=importlib.metadata.version("aquacal"),
            config_hash="",
            num_frames_used=len(board_poses),
            num_frames_holdout=0,
        ),
    )

    # Compute per-camera reprojection errors
    reproj = compute_reprojection_errors(result, detections, board_poses)
    result.diagnostics.reprojection_error_rms = reproj.rms
    result.diagnostics.reprojection_error_per_camera = reproj.per_camera

    return result, board_poses


def load_config(config_path: str | Path) -> CalibrationConfig:
    """
    Load calibration configuration from YAML file.

    Args:
        config_path: Path to config.yaml file

    Returns:
        CalibrationConfig populated from file

    Raises:
        FileNotFoundError: If config file doesn't exist
        ValueError: If config is invalid or missing required fields
    """
    config_path = Path(config_path)
    if not config_path.exists():
        raise FileNotFoundError(f"Config file not found: {config_path}")

    with open(config_path, "r") as f:
        data = yaml.safe_load(f)

    # Validate required sections
    required = ["board", "cameras", "paths"]
    for key in required:
        if key not in data:
            raise ValueError(f"Missing required config section: {key}")

    # Build BoardConfig (extrinsic/underwater board)
    board_data = data["board"]
    board = BoardConfig(
        squares_x=board_data["squares_x"],
        squares_y=board_data["squares_y"],
        square_size=board_data["square_size"],
        marker_size=board_data["marker_size"],
        dictionary=board_data.get("dictionary", "DICT_4X4_50"),
        legacy_pattern=board_data.get("legacy_pattern", False),
    )

    # Build optional intrinsic BoardConfig (if provided)
    intrinsic_board = None
    if "intrinsic_board" in data:
        intrinsic_data = data["intrinsic_board"]
        intrinsic_board = BoardConfig(
            squares_x=intrinsic_data["squares_x"],
            squares_y=intrinsic_data["squares_y"],
            square_size=intrinsic_data["square_size"],
            marker_size=intrinsic_data["marker_size"],
            dictionary=intrinsic_data.get("dictionary", "DICT_4X4_50"),
            legacy_pattern=intrinsic_data.get("legacy_pattern", False),
        )

    # Build paths
    paths = data["paths"]
    intrinsic_paths = {k: Path(v) for k, v in paths["intrinsic_videos"].items()}
    extrinsic_paths = {k: Path(v) for k, v in paths["extrinsic_videos"].items()}
    output_dir = Path(paths["output_dir"])

    # Auxiliary cameras (parsed early since initial_water_z references it)
    auxiliary_cameras = data.get("auxiliary_cameras", [])
    if auxiliary_cameras:
        overlap = set(data["cameras"]) & set(auxiliary_cameras)
        if overlap:
            raise ValueError(
                f"auxiliary_cameras must not overlap with cameras. "
                f"Overlap: {sorted(overlap)}"
            )
        for aux_cam in auxiliary_cameras:
            if aux_cam not in intrinsic_paths:
                raise ValueError(
                    f"Auxiliary camera '{aux_cam}' missing from paths.intrinsic_videos"
                )
            if aux_cam not in extrinsic_paths:
                raise ValueError(
                    f"Auxiliary camera '{aux_cam}' missing from paths.extrinsic_videos"
                )

    # Interface settings
    interface = data.get("interface", {})
    n_air = interface.get("n_air", 1.0)
    n_water = interface.get("n_water", 1.333)
    # D-02: default False (estimate tilt), matching both
    # CalibrationConfig.interface_normal_fixed and the configuration guide.
    normal_fixed = interface.get("normal_fixed", False)
    # Analysis/ablation flag: pass-through only, no cross-field validation here.
    # Must be in scope before the initial_water_z dict branches so the
    # missing-camera coverage gate can be conditioned on it.
    shared_interface = bool(interface.get("shared_interface", True))

    # Parse initial_water_z (optional)
    initial_water_z = None
    if "initial_water_z" in interface:
        raw_distances = interface["initial_water_z"]

        # Handle scalar format (apply to all cameras including auxiliary)
        if isinstance(raw_distances, (int, float)):
            if raw_distances <= 0:
                raise ValueError(
                    f"initial_water_z must be positive, got {raw_distances}"
                )
            initial_water_z = {
                cam: float(raw_distances) for cam in data["cameras"] + auxiliary_cameras
            }
        # Handle dict format (per-camera)
        elif isinstance(raw_distances, dict):
            # Validate all cameras are covered. In per-camera mode
            # (shared_interface=False) a partial dict is allowed through so the
            # pipeline's per-camera seed resolver can fill the missing cameras
            # (0.15m) and warn; in shared mode a partial dict still hard-fails.
            missing_cameras = set(data["cameras"]) - set(raw_distances.keys())
            if missing_cameras and shared_interface:
                raise ValueError(
                    f"initial_water_z dict must cover all cameras. "
                    f"Missing: {sorted(missing_cameras)}"
                )

            # Validate all distances are positive
            for cam, dist in raw_distances.items():
                if dist <= 0:
                    raise ValueError(
                        f"initial_water_z['{cam}'] must be positive, got {dist}"
                    )

            # Warn about extra cameras (not in cameras or auxiliary list)
            extra_cameras = (
                set(raw_distances.keys())
                - set(data["cameras"])
                - set(auxiliary_cameras)
            )
            if extra_cameras:
                import sys

                print(
                    f"Warning: initial_water_z contains cameras not in cameras list: "
                    f"{sorted(extra_cameras)}",
                    file=sys.stderr,
                )

            initial_water_z = {k: float(v) for k, v in raw_distances.items()}
        else:
            raise ValueError(
                f"initial_water_z must be a number or dict, got {type(raw_distances).__name__}"
            )

    # Optimization settings
    opt = data.get("optimization", {})
    robust_loss = opt.get("robust_loss", "huber")
    loss_scale = opt.get("loss_scale", 1.0)
    max_cal_frames_raw = opt.get("max_calibration_frames", None)
    max_cal_frames = int(max_cal_frames_raw) if max_cal_frames_raw is not None else None
    refine_intrinsics = opt.get("refine_intrinsics", False)
    refine_auxiliary_intrinsics = opt.get("refine_auxiliary_intrinsics", False)
    reject_outlier_frames = bool(opt.get("reject_outlier_frames", True))
    frame_rejection_k = float(opt.get("frame_rejection_k", 5.0))
    frame_rejection_floor_px = float(opt.get("frame_rejection_floor_px", 5.0))
    frame_rejection_max_fraction = float(opt.get("frame_rejection_max_fraction", 0.25))
    # Detection settings
    det = data.get("detection", {})
    min_corners = det.get("min_corners", 8)
    min_cameras = det.get("min_cameras", 2)
    frame_step = det.get("frame_step", 1)
    extrinsic_start_frame = int(det.get("start_frame", 0))
    stop_frame_raw = det.get("stop_frame")
    extrinsic_stop_frame = int(stop_frame_raw) if stop_frame_raw is not None else None

    # Camera model settings
    rational_model_cameras = data.get("rational_model_cameras", [])
    fisheye_cameras = data.get("fisheye_cameras", [])

    # Validate fisheye_cameras: must be subset of auxiliary_cameras
    if fisheye_cameras:
        non_aux = set(fisheye_cameras) - set(auxiliary_cameras)
        if non_aux:
            raise ValueError(
                f"fisheye_cameras must be a subset of auxiliary_cameras. "
                f"Not in auxiliary_cameras: {sorted(non_aux)}"
            )
        # Validate no overlap with rational_model_cameras
        overlap = set(fisheye_cameras) & set(rational_model_cameras)
        if overlap:
            raise ValueError(
                f"fisheye_cameras and rational_model_cameras must be disjoint. "
                f"Overlap: {sorted(overlap)}"
            )

    # Validation settings
    val = data.get("validation", {})
    holdout_fraction = val.get("holdout_fraction", 0.2)
    save_detailed = val.get("save_detailed_residuals", True)

    # Observability hooks (see output_dir/internals/)
    internals = data.get("internals", {})
    save_stage_calibrations = bool(internals.get("save_stage_calibrations", True))
    save_optimization_trace = bool(internals.get("save_optimization_trace", False))
    save_conditioning = bool(internals.get("save_conditioning", False))
    save_benchmark = bool(internals.get("save_benchmark", True))
    benchmark_memory = bool(internals.get("benchmark_memory", False))
    log_all_observation_depths = bool(
        internals.get("log_all_observation_depths", False)
    )

    # Reproducibility
    seed = int(data.get("seed", 42))

    return CalibrationConfig(
        board=board,
        camera_names=data["cameras"],
        intrinsic_video_paths=intrinsic_paths,
        extrinsic_video_paths=extrinsic_paths,
        output_dir=output_dir,
        intrinsic_board=intrinsic_board,
        n_air=n_air,
        n_water=n_water,
        interface_normal_fixed=normal_fixed,
        robust_loss=robust_loss,
        loss_scale=loss_scale,
        min_corners_per_frame=min_corners,
        min_cameras_per_frame=min_cameras,
        frame_step=frame_step,
        extrinsic_start_frame=extrinsic_start_frame,
        extrinsic_stop_frame=extrinsic_stop_frame,
        holdout_fraction=holdout_fraction,
        max_calibration_frames=max_cal_frames,
        refine_intrinsics=refine_intrinsics,
        refine_auxiliary_intrinsics=refine_auxiliary_intrinsics,
        reject_outlier_frames=reject_outlier_frames,
        frame_rejection_k=frame_rejection_k,
        frame_rejection_floor_px=frame_rejection_floor_px,
        frame_rejection_max_fraction=frame_rejection_max_fraction,
        save_detailed_residuals=save_detailed,
        save_stage_calibrations=save_stage_calibrations,
        save_optimization_trace=save_optimization_trace,
        save_conditioning=save_conditioning,
        save_benchmark=save_benchmark,
        benchmark_memory=benchmark_memory,
        log_all_observation_depths=log_all_observation_depths,
        seed=seed,
        shared_interface=shared_interface,
        initial_water_z=initial_water_z,
        rational_model_cameras=rational_model_cameras,
        auxiliary_cameras=auxiliary_cameras,
        fisheye_cameras=fisheye_cameras,
    )


def split_detections(
    detections: DetectionResult,
    holdout_fraction: float,
    seed: int = 42,
) -> tuple[DetectionResult, DetectionResult]:
    """
    Split detections into calibration and validation sets.

    Randomly assigns entire frames to either set (not individual detections).

    Args:
        detections: Full detection result
        holdout_fraction: Fraction of frames for validation (0.0 to 1.0)
        seed: Random seed for reproducibility

    Returns:
        Tuple of (calibration_detections, validation_detections)
    """
    frame_indices = list(detections.frames.keys())

    rng = random.Random(seed)
    rng.shuffle(frame_indices)

    n_holdout = int(len(frame_indices) * holdout_fraction)
    holdout_indices = set(frame_indices[:n_holdout])
    calibration_indices = set(frame_indices[n_holdout:])

    cal_frames = {idx: detections.frames[idx] for idx in calibration_indices}
    val_frames = {idx: detections.frames[idx] for idx in holdout_indices}

    cal_detections = DetectionResult(
        frames=cal_frames,
        camera_names=detections.camera_names,
        total_frames=len(cal_frames),
    )
    val_detections = DetectionResult(
        frames=val_frames,
        camera_names=detections.camera_names,
        total_frames=len(val_frames),
    )

    return cal_detections, val_detections


def _subsample_detections(
    detections: DetectionResult,
    max_frames: int,
) -> DetectionResult:
    """Uniformly subsample detection frames to at most max_frames.

    Selects frames at uniform temporal intervals from the sorted frame indices,
    preserving the first and last frames.

    Args:
        detections: Full detection result
        max_frames: Maximum number of frames to keep

    Returns:
        New DetectionResult with at most max_frames frames
    """
    frame_indices = sorted(detections.frames.keys())
    if len(frame_indices) <= max_frames:
        return detections

    # Uniform selection: np.linspace to pick evenly spaced indices
    selected_positions = np.round(
        np.linspace(0, len(frame_indices) - 1, max_frames)
    ).astype(int)
    selected_frames = {frame_indices[i] for i in selected_positions}

    return DetectionResult(
        frames={k: v for k, v in detections.frames.items() if k in selected_frames},
        camera_names=detections.camera_names,
        total_frames=detections.total_frames,
    )


def _save_board_reference_images(
    board: BoardGeometry,
    intrinsic_board: BoardGeometry | None,
    output_dir: Path,
) -> None:
    """
    Save reference PNG images of configured board(s) for visual verification.

    Generates grayscale ChArUco board images at 800x600 resolution with 50px
    margin. Saves extrinsic board always; saves intrinsic board only if it
    differs from extrinsic board.

    Args:
        board: Extrinsic board geometry
        intrinsic_board: Intrinsic board geometry (may be same as board)
        output_dir: Directory to save images
    """
    # Generate and save extrinsic board image
    cv_board = board.get_opencv_board()
    board_img = cv_board.generateImage((800, 600), marginSize=50)
    cv2.imwrite(str(output_dir / "board_extrinsic.png"), board_img)

    # Save intrinsic board image only if it differs from extrinsic board
    if intrinsic_board is not board:
        cv_intr_board = intrinsic_board.get_opencv_board()
        intr_img = cv_intr_board.generateImage((800, 600), marginSize=50)
        cv2.imwrite(str(output_dir / "board_intrinsic.png"), intr_img)


def run_calibration(
    config_path: str | Path, verbose: bool = False
) -> CalibrationResult:
    """
    Run complete calibration pipeline from config file.

    Loads configuration from YAML and delegates to run_calibration_from_config().

    Args:
        config_path: Path to config.yaml file
        verbose: If True, enable per-iteration progress output from optimizers

    Returns:
        Complete CalibrationResult

    Raises:
        FileNotFoundError: If config or video files not found
        CalibrationError: If any calibration stage fails

    Example:
        >>> from aquacal import run_calibration
        >>> result = run_calibration("config.yaml", verbose=True)
        >>> print(f"Calibrated {len(result.cameras)} cameras")
        >>> print(f"Water surface at Z = {result.cameras['cam0'].water_z:.3f} m")

    Note:
        For details on the optimizer pipeline, see the
        :doc:`Optimizer Guide </guide/optimizer>` guide.
    """
    config = load_config(config_path)
    return run_calibration_from_config(config, verbose=verbose)


@contextlib.contextmanager
def _time_stage(timings: dict[str, float], key: str) -> Iterator[None]:
    """Record elapsed wall time of the wrapped block into ``timings[key]``."""
    t0 = time.perf_counter()
    try:
        yield
    finally:
        timings[key] = time.perf_counter() - t0


def _select_conditioning_report(
    stage3_intrinsic_pass_obs: OptimizerObserver | None,
    rerun_obs: OptimizerObserver | None,
    stage3_obs: OptimizerObserver | None,
    refine_intrinsics: bool,
):
    """Pick the conditioning report from whichever stage produced the final result.

    Exactly one report is selected per run: Stage 3's second pass (intrinsics
    unlocked) when it ran (that pass is the final reported result), else the
    Stage-3 outlier-rejection re-run's if it fired, else the initial Stage-3
    solve's.

    Args:
        stage3_intrinsic_pass_obs: Observer for Stage 3's second pass, or
            `None` if that pass was skipped or not observed.
        rerun_obs: Observer for the Stage-3 outlier-rejection re-run, or `None`
            if the re-run did not fire or was not observed.
        stage3_obs: Observer for the initial Stage-3 solve, or `None` if not
            observed.
        refine_intrinsics: Whether Stage 3's second pass ran.

    Returns:
        The winning observer's `ConditioningReport`, or `None` if the winning
        observer is `None` or produced no report (e.g. `save_conditioning` was
        off for that observer).
    """
    if refine_intrinsics:
        obs = stage3_intrinsic_pass_obs
    elif rerun_obs is not None:
        obs = rerun_obs
    else:
        obs = stage3_obs
    return obs.conditioning_report if obs is not None else None


def _resolve_per_camera_water_z_seeds(
    initial_water_z: dict[str, float] | None,
    camera_order: list[str],
    auxiliary_cameras: list[str],
    default: float = 0.15,
) -> dict[str, float]:
    """Resolve per-camera water_z seeds for the ablation (per-camera) path.

    Rules (per-camera path only; shared mode never routes through here, which
    protects the IFACE-05 bit-exactness guarantee):
    - ``initial_water_z is None`` -> every camera gets ``default``, silently.
    - dict provided -> each camera in ``camera_order`` uses its provided value
      if present, else ``default``; if any were defaulted, warn once naming
      them.
    - any key NOT in ``camera_order``: silently ignored if it is an auxiliary
      camera (legitimately has no water_z parameter), otherwise warned as a
      likely typo.

    Args:
        initial_water_z: Raw (possibly partial or None) config dict.
        camera_order: Primary optimized camera names (each gets a water_z param).
        auxiliary_cameras: Auxiliary camera names, excluded from joint BA.
        default: Fallback seed in meters for missing cameras.

    Returns:
        Dict covering exactly ``camera_order``, one seed (meters) per camera.
    """
    if initial_water_z is None:
        return {cam: default for cam in camera_order}

    resolved: dict[str, float] = {}
    defaulted: list[str] = []
    for cam in camera_order:
        if cam in initial_water_z:
            resolved[cam] = float(initial_water_z[cam])
        else:
            resolved[cam] = default
            defaulted.append(cam)

    if defaulted:
        warnings.warn(
            f"initial_water_z did not cover all cameras; defaulted to {default}m: "
            f"{sorted(defaulted)}",
            UserWarning,
            stacklevel=2,
        )

    unknown = [
        key
        for key in initial_water_z
        if key not in camera_order and key not in auxiliary_cameras
    ]
    if unknown:
        warnings.warn(
            f"initial_water_z contains unknown camera name(s) (likely a typo): "
            f"{sorted(unknown)}",
            UserWarning,
            stacklevel=2,
        )

    return resolved


def build_interface_spread_report(
    distances: dict[str, float],
    stage: str,
) -> dict:
    """Build the per-camera water_z spread report (meters).

    Args:
        distances: Final per-camera water_z values (meters), one per optimized
            camera.
        stage: Producing-stage tag ("stage3", "stage3_rerun", or
            "stage3_intrinsic_pass"),
            matching the conditioning-report stage tag.

    Returns:
        A JSON-serializable dict with the producing stage, ``unit`` ("meters"),
        a ``per_camera`` map (sorted by name), and ``stats`` with
        min/max/mean/std/range in meters. ``std`` is the population standard
        deviation (numpy default, ddof=0).
    """
    cams = sorted(distances)
    values = np.array([distances[cam] for cam in cams], dtype=np.float64)
    return {
        "stage": stage,
        "unit": "meters",
        "per_camera": {cam: float(distances[cam]) for cam in cams},
        "stats": {
            "min": float(values.min()),
            "max": float(values.max()),
            "mean": float(values.mean()),
            "std": float(values.std()),
            "range": float(np.ptp(values)),
        },
    }


def run_calibration_from_config(
    config: CalibrationConfig, verbose: bool = False
) -> CalibrationResult:
    """
    Run complete calibration pipeline from configuration object.

    Pipeline stages:

    1. Detect ChArUco in intrinsic (in-air) videos
    2. Run Stage 1: Intrinsic calibration
    3. Detect ChArUco in extrinsic (underwater) videos
    4. Split underwater detections into calibration/validation sets
    5. Run Stage 2: Extrinsic initialization
    6. Run Stage 3: Interface and pose optimization, optionally followed by
       Stage 3's second pass (the intrinsic pass) with intrinsics unlocked
    7. Run validation on held-out data
    8. Generate and save diagnostics
    9. Save final calibration result

    Args:
        config: Complete calibration configuration
        verbose: If True, enable per-iteration progress output from optimizers

    Returns:
        CalibrationResult with all calibrations and diagnostics

    Raises:
        CalibrationError: If any stage fails
        InsufficientDataError: If not enough detections
        ConnectivityError: If pose graph is disconnected
    """
    board = BoardGeometry(config.board)

    # Intrinsic board: use separate board if provided, else fall back to extrinsic board
    intrinsic_board = (
        BoardGeometry(config.intrinsic_board) if config.intrinsic_board else board
    )

    # Create output directory
    config.output_dir.mkdir(parents=True, exist_ok=True)

    # Accumulator for per-stage wall-clock timings (seconds). Skipped stages
    # are simply absent from this dict.
    timings: dict[str, float] = {}

    # Accumulator for discard counts (plan 19.2-26). Always on: a handful of
    # integer increments at per-(camera, frame) granularity, never in a hot loop.
    # A discard that no artifact records cannot be audited after the fact -- the
    # degenerate-PnP guard was entirely silent before this.
    discard_stats: dict[str, int] = {}

    # Accumulators for the per-observation degeneracy sinks (plan 25-01).
    # `degeneracy_details` is always on: it holds one row per FLAGGED
    # observation, a population that is empty on a clean rig and of order a few
    # hundred rows when it is not, so the cost is negligible and the payoff is
    # that a non-zero degeneracy count stops being a bare number.
    # `observation_depths` holds one row per EVALUATED observation (~74k per
    # stage) and stays None unless the config asks for it -- None is what makes
    # plan 25-01's sink bit-identically inert, so the ordinary run pays nothing.
    #
    # Both accumulate ACROSS stage-3 calls, including the second `_run_stage3`
    # invocation when `reject_outlier_frames` fires. The resulting double-count
    # is expected and is inherited from the Phase 24 counters (the published 198
    # is itself a cross-stage sum); the per-row `stage` stamp is what makes the
    # distinct count recoverable downstream.
    degeneracy_details: list[dict] = []
    observation_depths: list[dict] | None = (
        [] if config.log_all_observation_depths else None
    )

    # Accumulator for per-stage solver diagnostics (BENCH-01/BENCH-04), keyed
    # by benchmark.json stage name. Populated unconditionally (cheap; no
    # extra least_squares calls), consumed only if config.save_benchmark.
    # NOTE: named solver_diagnostics (not `diagnostics`) to avoid colliding
    # with the pre-existing local `diagnostics: DiagnosticsData` variable
    # built later in this function.
    solver_diagnostics: dict[str, SolverDiagnostics] = {}

    # Accumulator for per-stage-boundary peak-memory readings (BENCH-02,
    # D-18), keyed by boundary name in temporal order. Left empty (and never
    # populated) when config.benchmark_memory is False.
    memory_readings: dict[str, dict] = {}

    # Save board reference images for visual verification
    _save_board_reference_images(board, intrinsic_board, config.output_dir)

    print("=" * 60)
    print("AquaCal Calibration Pipeline")
    print("=" * 60)

    # Single ablation warning, emitted once at start (not per stage).
    if not config.shared_interface:
        print(
            "  WARNING: Per-camera interface mode is active (shared_interface=false): "
            "each camera solves its own water_z. This is for degeneracy/ablation "
            "analysis only. The shared-interface assumption underlies AquaCal's "
            "central modeling claim; per-camera mode is NOT recommended for "
            "production calibration."
        )

    # --- Stage 1: Intrinsic Calibration ---
    print("\n[Stage 1] Intrinsic calibration (in-air)...")
    with _time_stage(timings, "stage1_intrinsics"):
        intrinsics_results = calibrate_intrinsics_all(
            video_paths={k: str(v) for k, v in config.intrinsic_video_paths.items()},
            board=intrinsic_board,
            min_corners=config.min_corners_per_frame,
            frame_step=config.frame_step,
            rational_model_cameras=config.rational_model_cameras or None,
            fisheye_cameras=config.fisheye_cameras or None,
            discard_stats_out=discard_stats,
            progress_callback=lambda name, cur, total: print(
                f"  Calibrating {name} ({cur}/{total})..."
            ),
        )
    # Extract just intrinsics from (intrinsics, error) tuples
    intrinsics = {name: result[0] for name, result in intrinsics_results.items()}
    for name, (_, rms) in intrinsics_results.items():
        print(f"  {name}: RMS {rms:.3f} px")
    print(f"  Calibrated {len(intrinsics)} cameras")

    # Validate intrinsics
    from aquacal.calibration.intrinsics import validate_intrinsics

    for name, (intr, _) in intrinsics_results.items():
        warnings = validate_intrinsics(intr, camera_name=name)
        for w in warnings:
            print(f"  WARNING: {w}")

    # --- Detect in underwater videos ---
    print("\n[Detection] Detecting ChArUco in underwater videos...")

    def _detection_progress(current: int, total: int) -> None:
        """Print detection progress at ~10% intervals."""
        if total > 0 and (current % max(1, total // 10) == 0 or current == total):
            print(f"  Frame {current}/{total} ({100 * current // total}%)")

    with _time_stage(timings, "detection_underwater"):
        all_detections = detect_all_frames(
            video_paths={k: str(v) for k, v in config.extrinsic_video_paths.items()},
            board=board,
            intrinsics={k: (v.K, v.dist_coeffs) for k, v in intrinsics.items()},
            min_corners=config.min_corners_per_frame,
            frame_step=config.frame_step,
            start_frame=config.extrinsic_start_frame,
            stop_frame=config.extrinsic_stop_frame,
            progress_callback=_detection_progress,
        )
    if config.extrinsic_start_frame > 0:
        print(
            f"  Skipping first {config.extrinsic_start_frame} extrinsic frames "
            f"(start_frame={config.extrinsic_start_frame}, applied uniformly to all cameras)"
        )
    if config.extrinsic_stop_frame is not None:
        print(
            f"  Skipping extrinsic frames at/after index {config.extrinsic_stop_frame} "
            f"(stop_frame={config.extrinsic_stop_frame}, applied uniformly to all cameras)"
        )
    usable_frames = all_detections.get_frames_with_min_cameras(
        config.min_cameras_per_frame
    )
    print(f"  Found {len(usable_frames)} usable frames")

    # --- Split calibration/validation ---
    print(
        f"\n[Split] Holdout fraction: {config.holdout_fraction} (seed: {config.seed})"
    )
    cal_detections, val_detections = split_detections(
        all_detections, config.holdout_fraction, seed=config.seed
    )
    print(f"  Calibration frames: {len(cal_detections.frames)}")
    print(f"  Validation frames: {len(val_detections.frames)}")

    # --- Filter to primary cameras for Stages 2-3 ---
    primary_camera_set = set(config.camera_names)
    primary_intrinsics = {
        k: v for k, v in intrinsics.items() if k in primary_camera_set
    }

    # Filter detection frames to primary cameras only
    primary_cal_frames = {}
    for frame_idx, frame_det in cal_detections.frames.items():
        primary_dets = {
            k: v for k, v in frame_det.detections.items() if k in primary_camera_set
        }
        if primary_dets:
            primary_cal_frames[frame_idx] = FrameDetections(
                frame_idx=frame_idx, detections=primary_dets
            )
    primary_cal_detections = DetectionResult(
        frames=primary_cal_frames,
        camera_names=config.camera_names,
        total_frames=cal_detections.total_frames,
    )

    # --- Stage 2: Extrinsic Initialization ---
    print("\n[Stage 2] Extrinsic initialization...")
    reference_camera = config.camera_names[0]
    interface_normal = np.array([0.0, 0.0, -1.0], dtype=np.float64)
    with _time_stage(timings, "stage2_extrinsic_init"):
        pose_graph = build_pose_graph(
            primary_cal_detections, config.min_cameras_per_frame
        )
        extrinsics = estimate_extrinsics(
            pose_graph,
            primary_intrinsics,
            board,
            reference_camera,
            water_zs=config.initial_water_z,
            interface_normal=interface_normal,
            n_air=config.n_air,
            n_water=config.n_water,
            progress_callback=lambda cam, cur, total: print(
                "  Averaging poses..."
                if cam == "_averaging"
                else f"  Located {cam} ({cur}/{total})"
            ),
            discard_stats_out=discard_stats,
        )
    print(f"  Initialized {len(extrinsics)} camera poses")

    # Build initial CalibrationResult for saving and visualization
    initial_interface_dists = {}
    for cam_name in extrinsics:
        if config.initial_water_z is not None:
            initial_interface_dists[cam_name] = config.initial_water_z.get(
                cam_name, 0.15
            )
        else:
            initial_interface_dists[cam_name] = 0.15

    initial_result = _build_calibration_result(
        intrinsics=primary_intrinsics,
        extrinsics=extrinsics,
        water_z_values=initial_interface_dists,
        board_config=config.board,
        interface_params=InterfaceParams(
            normal=interface_normal,
            n_air=config.n_air,
            n_water=config.n_water,
        ),
        diagnostics=DiagnosticsData(
            reprojection_error_rms=0.0,
            reprojection_error_per_camera={},
            validation_3d_error_mean=0.0,
            validation_3d_error_std=0.0,
        ),
        metadata=CalibrationMetadata(
            calibration_date=datetime.now().isoformat(),
            software_version=importlib.metadata.version("aquacal"),
            config_hash=_compute_config_hash(config),
            num_frames_used=0,
            num_frames_holdout=0,
            seed=config.seed,
        ),
    )

    # Save pre-optimization calibration
    save_calibration(initial_result, config.output_dir / "calibration_initial.json")
    print("  Saved calibration_initial.json")

    # Save initial camera rig visualization (pre-optimization)
    try:
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt

        from aquacal.validation.diagnostics import plot_camera_rig

        fig = plot_camera_rig(
            initial_result,
            title="Stage 2: Initial Camera Positions (pre-optimization)",
        )
        fig.savefig(
            str(config.output_dir / "camera_rig_initial.png"),
            dpi=150,
            bbox_inches="tight",
        )
        plt.close(fig)
        print("  Saved camera_rig_initial.png")
    except Exception as e:
        print(f"  Warning: Could not save camera_rig_initial.png: {e}")

    # --- Subsample for optimization if configured ---
    optim_detections = primary_cal_detections
    if (
        config.max_calibration_frames is not None
        and len(primary_cal_detections.frames) > config.max_calibration_frames
    ):
        optim_detections = _subsample_detections(
            primary_cal_detections, config.max_calibration_frames
        )
        print(
            f"\n[Frame Selection] Subsampled {len(primary_cal_detections.frames)} -> {len(optim_detections.frames)} frames for optimization"
        )

    # --- Stage 3: Interface Optimization ---
    print("\n[Stage 3] Interface and pose optimization...")

    # In per-camera mode, resolve the (possibly None / partial) initial_water_z
    # dict into a full per-camera seed dict (fills missing cameras with 0.15m,
    # warns as needed). Shared mode passes config.initial_water_z through
    # unchanged to protect IFACE-05 bit-exactness.
    if config.shared_interface:
        stage3_initial_water_zs = config.initial_water_z
    else:
        stage3_initial_water_zs = _resolve_per_camera_water_z_seeds(
            config.initial_water_z,
            config.camera_names,
            config.auxiliary_cameras,
        )

    def _run_stage3(dets, observer=None, diagnostics_out=None):
        """Run Stage 3 interface optimization on the given detection set."""
        return optimize_interface(
            detections=dets,
            intrinsics=primary_intrinsics,
            initial_extrinsics=extrinsics,
            board=board,
            reference_camera=reference_camera,
            initial_water_zs=stage3_initial_water_zs,
            interface_normal=interface_normal,
            n_air=config.n_air,
            n_water=config.n_water,
            loss=config.robust_loss,
            loss_scale=config.loss_scale,
            min_corners=config.min_corners_per_frame,
            verbose=2 if verbose else 1,
            normal_fixed=config.interface_normal_fixed,
            observer=observer,
            shared_interface=config.shared_interface,
            diagnostics_out=diagnostics_out,
            discard_stats_out=discard_stats,
            discard_stage="stage3_interface_optimization",
            degeneracy_details_out=degeneracy_details,
            observation_depths_out=observation_depths,
        )

    # Observers are needed when EITHER the per-iteration trace (HOOK-02) or
    # conditioning diagnostics (HOOK-03) are requested.
    observe = config.save_optimization_trace or config.save_conditioning

    stage3_observer = (
        OptimizerObserver(
            stage="stage3",
            conditioning=config.save_conditioning and not config.refine_intrinsics,
        )
        if observe
        else None
    )
    if config.benchmark_memory:
        memory_readings["_baseline"] = capture_peak_memory()

    t0 = time.perf_counter()
    stage3_extrinsics, stage3_distances, stage3_poses, stage3_rms = _run_stage3(
        optim_detections,
        observer=stage3_observer,
        diagnostics_out=solver_diagnostics.setdefault(
            "stage3_interface_optimization", SolverDiagnostics()
        ),
    )
    elapsed = time.perf_counter() - t0
    timings["stage3_interface_optimization"] = elapsed
    print(f"  Stage 3 RMS: {stage3_rms:.3f} pixels ({elapsed:.1f}s)")

    if config.benchmark_memory:
        memory_readings["stage3_interface_optimization"] = capture_peak_memory()

    if stage3_observer is not None and config.save_optimization_trace:
        stage3_observer.write_trace_csv(
            ensure_internals_dir(config.output_dir) / "trace_stage3.csv"
        )
        print("  Saved internals/trace_stage3.csv")

    if config.save_stage_calibrations:
        _dump_stage_calibration(
            "stage3",
            config,
            primary_intrinsics,
            stage3_extrinsics,
            stage3_distances,
            interface_normal,
        )
        print("  Saved internals/calibration_stage3.json")

    # --- Automatic per-frame outlier rejection (optional) ---
    # A few catastrophically-bad frames (board out of water, ripples,
    # mis-detections) inject large coherent residuals that a robust loss only
    # partially suppresses, biasing the affected cameras' extrinsics. Identify
    # them from per-frame RMS, drop them, and re-run Stage 3 once.
    #
    # IMPORTANT: the per-frame RMS must be computed against INDEPENDENTLY
    # estimated board poses (per-frame PnP + 6-DOF refine with fixed cameras),
    # NOT the jointly-optimized Stage-3 poses. A high-leverage outlier frame
    # biases the shared extrinsics to fit ITSELF, so with the joint poses it
    # hides with a low residual. An independent per-frame fit cannot reconcile a
    # geometrically-inconsistent (e.g. near-surface) frame across cameras, so it
    # surfaces at a large residual - the same quantity holdout validation reports.
    frame_rejection_info = None
    stage3_rerun_observer = None
    if config.reject_outlier_frames:
        rej_initial_poses = _compute_initial_board_poses(
            optim_detections,
            primary_intrinsics,
            stage3_extrinsics,
            board,
            config.min_corners_per_frame,
            stage3_distances,
            interface_normal,
            config.n_air,
            config.n_water,
            discard_stats_out=discard_stats,
        )
        rej_independent_poses = _estimate_validation_poses(
            optim_detections,
            rej_initial_poses,
            primary_intrinsics,
            stage3_extrinsics,
            stage3_distances,
            board,
            interface_normal,
            config.n_air,
            config.n_water,
        )
        per_frame_rms = compute_per_frame_rms(
            detections=optim_detections,
            intrinsics=primary_intrinsics,
            extrinsics=stage3_extrinsics,
            distances=stage3_distances,
            board_poses=list(rej_independent_poses.values()),
            board=board,
            interface_normal=interface_normal,
            n_air=config.n_air,
            n_water=config.n_water,
        )
        rejection = identify_outlier_frames(
            per_frame_rms,
            k=config.frame_rejection_k,
            absolute_floor_px=config.frame_rejection_floor_px,
            max_reject_fraction=config.frame_rejection_max_fraction,
        )
        frame_rejection_info = rejection.to_diagnostics_dict()

        if rejection.guardrail_triggered:
            n_flagged = sum(
                1 for rms in per_frame_rms.values() if rms > rejection.threshold_px
            )
            print(
                f"  [Frame Rejection] WARNING: {n_flagged}/{rejection.num_evaluated} "
                f"frames exceed the outlier threshold ({rejection.threshold_px:.2f} px), "
                f"more than the {config.frame_rejection_max_fraction:.0%} guardrail. "
                f"Rejection SUPPRESSED - dataset may be broadly contaminated; "
                f"review calibration inputs. Proceeding with all frames."
            )
        elif rejection.rejected_frames:
            print(
                f"  [Frame Rejection] Dropping {len(rejection.rejected_frames)} "
                f"outlier frame(s) (RMS > {rejection.threshold_px:.2f} px, "
                f"median={rejection.median_rms_px:.2f} px): "
                f"{rejection.rejected_frames}"
            )
            optim_detections = drop_frames(optim_detections, rejection.rejected_frames)
            print(
                f"  [Frame Rejection] Re-running Stage 3 on "
                f"{len(optim_detections.frames)} cleaned frames..."
            )
            # The initial Stage-3 solve can't know in advance whether this
            # re-run will fire, so when it does, conditioning (if enabled) runs
            # a second time here and this later report wins -- see
            # _select_conditioning_report. A bounded, deliberate duplication
            # chosen over trying to predict the rejection outcome.
            stage3_rerun_observer = (
                OptimizerObserver(
                    stage="stage3_rerun",
                    conditioning=config.save_conditioning
                    and not config.refine_intrinsics,
                )
                if observe
                else None
            )
            t0 = time.perf_counter()
            stage3_extrinsics, stage3_distances, stage3_poses, stage3_rms = _run_stage3(
                optim_detections,
                observer=stage3_rerun_observer,
                diagnostics_out=solver_diagnostics.setdefault(
                    "stage3_rerun", SolverDiagnostics()
                ),
            )
            elapsed = time.perf_counter() - t0
            timings["stage3_interface_optimization"] += elapsed
            print(
                f"  Stage 3 RMS (after rejection): {stage3_rms:.3f} pixels "
                f"({elapsed:.1f}s)"
            )

            if config.benchmark_memory:
                memory_readings["stage3_rerun"] = capture_peak_memory()

            if stage3_rerun_observer is not None and config.save_optimization_trace:
                stage3_rerun_observer.write_trace_csv(
                    ensure_internals_dir(config.output_dir) / "trace_stage3_rerun.csv"
                )
                print("  Saved internals/trace_stage3_rerun.csv")

            if config.save_stage_calibrations:
                _dump_stage_calibration(
                    "stage3_rerun",
                    config,
                    primary_intrinsics,
                    stage3_extrinsics,
                    stage3_distances,
                    interface_normal,
                )
                print("  Saved internals/calibration_stage3_rerun.json")
        else:
            print(
                f"  [Frame Rejection] No outlier frames "
                f"(median={rejection.median_rms_px:.2f} px, "
                f"threshold={rejection.threshold_px:.2f} px). No frames dropped."
            )

    if not config.interface_normal_fixed:
        ref_R = stage3_extrinsics[reference_camera].R
        ref_rvec = matrix_to_rvec(ref_R)
        tilt_deg = np.degrees(np.linalg.norm(ref_rvec[:2]))
        print(f"  Estimated reference camera tilt: {tilt_deg:.2f} degrees")

    # Water surface and camera heights
    # Get water_z from any camera (all have same value after optimization)
    water_z = list(stage3_distances.values())[0]
    print(f"  Water surface Z: {water_z:.4f} m")
    print("  Camera heights above water (h_c):")

    heights = []
    for cam_name in sorted(stage3_extrinsics.keys()):
        C = stage3_extrinsics[cam_name].C
        cam_z = C[2]
        h_c = water_z - cam_z  # camera-to-water vertical distance
        heights.append(h_c)
        print(f"    {cam_name}: cam_z={cam_z:.4f}  h_c={h_c:.4f}")

    heights = np.array(heights)
    print(f"  Camera height spread: {np.ptp(heights):.4f} m")

    # --- Stage 3's second pass: intrinsics unlocked (optional) ---
    refine_intrinsics = config.refine_intrinsics
    stage3_intrinsic_pass_observer = None

    if refine_intrinsics:
        print("\n[Stage 3: intrinsic pass] Second pass, with intrinsics unlocked...")
        stage3_result = (stage3_extrinsics, stage3_distances, stage3_poses, stage3_rms)
        stage3_intrinsic_pass_observer = (
            OptimizerObserver(
                stage="stage3_intrinsic_pass", conditioning=config.save_conditioning
            )
            if observe
            else None
        )
        t0 = time.perf_counter()
        (
            final_extrinsics,
            final_distances,
            final_poses,
            final_intrinsics,
            final_rms,
        ) = joint_refinement(
            stage3_result=stage3_result,
            detections=optim_detections,
            intrinsics=primary_intrinsics,
            board=board,
            reference_camera=reference_camera,
            refine_intrinsics=True,
            interface_normal=interface_normal,
            n_air=config.n_air,
            n_water=config.n_water,
            loss=config.robust_loss,
            loss_scale=config.loss_scale,
            verbose=2 if verbose else 1,
            normal_fixed=config.interface_normal_fixed,
            observer=stage3_intrinsic_pass_observer,
            shared_interface=config.shared_interface,
            diagnostics_out=solver_diagnostics.setdefault(
                "stage3_intrinsic_pass", SolverDiagnostics()
            ),
            discard_stats_out=discard_stats,
            discard_stage="stage3_intrinsic_pass",
            degeneracy_details_out=degeneracy_details,
            observation_depths_out=observation_depths,
        )
        elapsed = time.perf_counter() - t0
        timings["stage3_intrinsic_pass"] = elapsed
        print(f"  Stage 3 intrinsic pass RMS: {final_rms:.3f} pixels ({elapsed:.1f}s)")

        if config.benchmark_memory:
            memory_readings["stage3_intrinsic_pass"] = capture_peak_memory()

        if (
            stage3_intrinsic_pass_observer is not None
            and config.save_optimization_trace
        ):
            stage3_intrinsic_pass_observer.write_trace_csv(
                ensure_internals_dir(config.output_dir)
                / "trace_stage3_intrinsic_pass.csv"
            )
            print("  Saved internals/trace_stage3_intrinsic_pass.csv")

        # Water surface and camera heights after refinement
        water_z_final = list(final_distances.values())[0]
        print(f"  Water surface Z (after refinement): {water_z_final:.4f} m")
        print("  Camera heights above water (h_c):")

        heights_final = []
        for cam_name in sorted(final_extrinsics.keys()):
            C = final_extrinsics[cam_name].C
            cam_z = C[2]
            h_c = water_z_final - cam_z
            heights_final.append(h_c)
            print(f"    {cam_name}: cam_z={cam_z:.4f}  h_c={h_c:.4f}")

        heights_final = np.array(heights_final)
        print(f"  Camera height spread: {np.ptp(heights_final):.4f} m")

        if config.save_stage_calibrations:
            _dump_stage_calibration(
                "stage3_intrinsic_pass",
                config,
                final_intrinsics,
                final_extrinsics,
                final_distances,
                interface_normal,
            )
            print("  Saved internals/calibration_stage3_intrinsic_pass.json")
    else:
        print("\n[Stage 3: intrinsic pass] Skipped (refine_intrinsics=False)")
        final_extrinsics = stage3_extrinsics
        final_distances = stage3_distances
        final_poses = stage3_poses
        final_intrinsics = primary_intrinsics
        final_rms = stage3_rms

    # --- Conditioning diagnostics (HOOK-03) ---
    # Exactly one report is written per run, from whichever stage produced the
    # final reported result. Not wrapped in try/except: a memory refusal must
    # fail the run loudly rather than be silently swallowed.
    if config.save_conditioning:
        conditioning_stage = (
            "stage3_intrinsic_pass"
            if refine_intrinsics
            else ("stage3_rerun" if stage3_rerun_observer is not None else "stage3")
        )
        conditioning_report = _select_conditioning_report(
            stage3_intrinsic_pass_observer,
            stage3_rerun_observer,
            stage3_observer,
            refine_intrinsics,
        )
        if conditioning_report is not None:
            internals_dir = ensure_internals_dir(config.output_dir)
            save_conditioning_report(
                conditioning_report,
                internals_dir / "conditioning.json",
                internals_dir / "conditioning.npz",
                stage=conditioning_stage,
            )
            print(
                f"  Saved internals/conditioning.json (+ .npz) "
                f"[stage: {conditioning_stage}]"
            )

    # --- Per-camera interface spread report (IFACE-04) ---
    # The ablation's headline number: always written in per-camera mode (not
    # gated behind any save flag). Console line is millimeters (human display);
    # the JSON file is meters (machine-readable). Shared mode writes nothing.
    if not config.shared_interface:
        spread_stage = (
            "stage3_intrinsic_pass"
            if refine_intrinsics
            else ("stage3_rerun" if stage3_rerun_observer is not None else "stage3")
        )
        spread_report = build_interface_spread_report(final_distances, spread_stage)
        s = spread_report["stats"]
        print(
            "  [Per-Camera Interface] water_z spread (mm): "
            f"min={s['min'] * 1000:.2f} max={s['max'] * 1000:.2f} "
            f"mean={s['mean'] * 1000:.2f} std={s['std'] * 1000:.2f} "
            f"range={s['range'] * 1000:.2f}"
        )
        internals_dir = ensure_internals_dir(config.output_dir)
        spread_path = internals_dir / "interface_spread.json"
        warn_if_overwriting(spread_path)
        with open(spread_path, "w") as f:
            json.dump(spread_report, f, indent=2, sort_keys=True)
        print("  Saved internals/interface_spread.json")

    # Convert poses list to dict
    board_poses_dict = {bp.frame_idx: bp for bp in final_poses}

    # --- Auxiliary camera registration (post-hoc, after Stage 3) ---
    aux_extrinsics = {}
    aux_distances = {}
    if config.auxiliary_cameras:
        dof_description = (
            "10-DOF refinement (extrinsics plus focal length and principal point)"
            if config.refine_auxiliary_intrinsics
            else "6-DOF refinement (extrinsics only)"
        )
        print(
            f"\n[Auxiliary camera registration] Registering "
            f"{len(config.auxiliary_cameras)} auxiliary camera(s) via {dof_description}..."
        )

        # Derive water_z from Stage 3 output (reference camera has C_z = 0)
        water_z = float(final_distances[reference_camera])

        # Time the full auxiliary registration loop as a single stage.
        with _time_stage(timings, "auxiliary_registration"):
            for aux_cam in config.auxiliary_cameras:
                # Count observations
                n_frames = 0
                n_corners = 0
                for frame_idx, frame_det in all_detections.frames.items():
                    if (
                        aux_cam in frame_det.detections
                        and frame_idx in board_poses_dict
                    ):
                        n_frames += 1
                        n_corners += frame_det.detections[aux_cam].num_corners

                print(f"  {aux_cam}: {n_frames} frames, {n_corners} corners")

                try:
                    result = register_auxiliary_camera(
                        camera_name=aux_cam,
                        intrinsics=intrinsics[aux_cam],
                        detections=all_detections,
                        board_poses=board_poses_dict,
                        board=board,
                        water_z=water_z,
                        interface_normal=interface_normal,
                        n_air=config.n_air,
                        n_water=config.n_water,
                        refine_intrinsics=config.refine_auxiliary_intrinsics,
                        verbose=2 if verbose else 1,
                        diagnostics_out=solver_diagnostics.setdefault(
                            f"auxiliary_registration_{aux_cam}", SolverDiagnostics()
                        ),
                        discard_stats_out=discard_stats,
                    )

                    # Handle variable-length return
                    if config.refine_auxiliary_intrinsics:
                        aux_ext, aux_dist, aux_rms, aux_intr = result
                        intrinsics[aux_cam] = aux_intr
                        print(
                            f"  {aux_cam}: RMS {aux_rms:.2f} px, interface_d={aux_dist:.4f}m (intrinsics refined)"
                        )
                    else:
                        aux_ext, aux_dist, aux_rms = result
                        print(
                            f"  {aux_cam}: RMS {aux_rms:.2f} px, interface_d={aux_dist:.4f}m"
                        )

                    aux_extrinsics[aux_cam] = aux_ext
                    aux_distances[aux_cam] = aux_dist
                except Exception as e:
                    print(f"  {aux_cam}: FAILED - {e}")

        if config.benchmark_memory:
            memory_readings["auxiliary_registration"] = capture_peak_memory()

        # Merge auxiliary cameras into working dicts so validation includes them
        if aux_extrinsics:
            final_extrinsics.update(aux_extrinsics)
            final_distances.update(aux_distances)
            final_intrinsics.update({cam: intrinsics[cam] for cam in aux_extrinsics})

    # Estimate board poses for validation frames
    print("\n[Validation] Estimating board poses for held-out frames...")
    _validation_t0 = time.perf_counter()

    # Build temporary CalibrationResult for validation functions.
    # Built BEFORE pose estimation (rather than after, as previously) because
    # evaluate_calibration takes an already-built CalibrationResult. This is a
    # pure construction reordering: temp_result is assembled from
    # final_intrinsics/final_extrinsics/final_distances, none of which pose
    # estimation mutates, so it carries no numerical effect.
    interface_params = InterfaceParams(
        normal=interface_normal,
        n_air=config.n_air,
        n_water=config.n_water,
    )

    # Determine primary and auxiliary cameras
    aux_cam_names = set(config.auxiliary_cameras) if config.auxiliary_cameras else set()
    primary_cam_names = set(final_intrinsics.keys()) - aux_cam_names

    # Build full result with all cameras (for board pose estimation and plots)
    temp_result = _build_calibration_result(
        intrinsics=final_intrinsics,
        extrinsics=final_extrinsics,
        water_z_values=final_distances,
        board_config=config.board,
        interface_params=interface_params,
        diagnostics=DiagnosticsData(
            reprojection_error_rms=0.0,
            reprojection_error_per_camera={},
            validation_3d_error_mean=0.0,
            validation_3d_error_std=0.0,
        ),
        metadata=CalibrationMetadata(
            calibration_date="",
            software_version="",
            config_hash="",
            num_frames_used=0,
            num_frames_holdout=0,
        ),
        auxiliary_cameras=aux_cam_names,
    )

    primary_eval = evaluate_calibration(
        temp_result,
        val_detections,
        board,
        min_corners=config.min_corners_per_frame,
        cameras=primary_cam_names,
    )
    board_poses_dict.update(primary_eval.board_poses)
    print(f"  Estimated {len(primary_eval.board_poses)} validation frame poses")

    # --- Validation ---
    print("\n[Validation] Computing errors on held-out data...")

    # --- Primary camera validation ---
    primary_result = _filter_cameras(temp_result, primary_cam_names)

    primary_reproj = primary_eval.reprojection
    primary_3d = primary_eval.reconstruction

    # Save spatial measurements if available
    if primary_3d.spatial is not None and len(primary_3d.spatial.positions) > 0:
        from aquacal.validation.reconstruction import save_spatial_measurements

        spatial_csv_path = config.output_dir / "spatial_measurements.csv"
        save_spatial_measurements(primary_3d.spatial, spatial_csv_path)

    # Print primary camera metrics
    if np.isnan(primary_reproj.rms):
        print("  Primary cameras:")
        print("    Reprojection RMS: N/A (no valid observations)")
    else:
        print("  Primary cameras:")
        print(f"    Reprojection RMS: {primary_reproj.rms:.3f} pixels")

    if np.isnan(primary_3d.mean):
        print("    3D distance error: N/A (no valid comparisons)")
    else:
        print(
            f"    3D distance error: MAE {primary_3d.mean * 1000:.2f} mm, "
            f"RMSE {primary_3d.rmse * 1000:.2f} mm "
            f"({primary_3d.percent_error:.1f}% of square size)"
        )
        if abs(primary_3d.signed_mean) > 0.0005:  # > 0.5mm bias
            sign = "+" if primary_3d.signed_mean > 0 else ""
            bias_type = (
                "overestimate" if primary_3d.signed_mean > 0 else "underestimate"
            )
            print(
                f"    Scale bias: {sign}{primary_3d.signed_mean * 1000:.2f} mm ({bias_type})"
            )

    # --- Auxiliary camera validation (if any) ---
    aux_reproj = None
    if aux_cam_names:
        aux_eval = evaluate_calibration(
            temp_result,
            val_detections,
            board,
            min_corners=config.min_corners_per_frame,
            cameras=aux_cam_names,
            board_poses=primary_eval.board_poses,  # reuse, do not re-estimate
            include_reconstruction=False,
        )
        aux_reproj = aux_eval.reprojection

        print("  Auxiliary cameras:")
        for cam_name in sorted(aux_cam_names):
            if cam_name in aux_reproj.per_camera:
                rms = aux_reproj.per_camera[cam_name]
                print(f"    {cam_name}: RMS {rms:.3f} pixels")
            else:
                print(f"    {cam_name}: RMS N/A (no valid observations)")

    # Store primary metrics for later use
    reproj_errors = primary_reproj
    reconstruction_errors = primary_3d
    timings["validation"] = time.perf_counter() - _validation_t0

    if config.benchmark_memory:
        memory_readings["validation"] = capture_peak_memory()

    # --- Generate Diagnostics ---
    print("\n[Diagnostics] Generating report...")
    with _time_stage(timings, "diagnostics_generate"):
        diagnostic_report = generate_diagnostic_report(
            calibration=primary_result,  # Use primary-only for summary stats
            detections=val_detections,
            board_poses=board_poses_dict,
            reprojection_errors=reproj_errors,
            reconstruction_errors=reconstruction_errors,
            board=board,
            auxiliary_reprojection=aux_reproj,
        )

    # Build timings payload AFTER all timed regions and BEFORE the save call
    # (the save itself is intentionally not in the timing block).
    timings_payload = {
        "seconds_per_stage": dict(timings),
        "total_seconds": float(sum(timings.values())),
    }

    # Save diagnostics (uses full temp_result for plots, but report has primary-only stats)
    save_diagnostic_report(
        diagnostic_report,
        temp_result,  # Full result for plots
        val_detections,
        config.output_dir,
        save_images=True,
        auxiliary_reprojection=aux_reproj,
        timings=timings_payload,
        frame_rejection=frame_rejection_info,
        discard_stats=dict(discard_stats),
        degeneracy_details=degeneracy_details,
        observation_depths=observation_depths,
    )
    print(f"  Saved diagnostics to {config.output_dir}")

    # ONE summary line, after the counts are final -- never one per event. These
    # sites fire thousands of times on a real rig; per-event logging would both
    # drown the log and cost wall-clock that benchmark.json publishes.
    if discard_stats:
        _violations = check_discard_invariants(discard_stats)
        print(
            "  Discards: "
            + ", ".join(f"{k}={discard_stats[k]}" for k in sorted(discard_stats))
        )
        if _violations:
            # Not raised: this is an accounting self-check, and a broken counter
            # must never take down a calibration that is otherwise fine.
            print(f"  WARNING: discard-counter invariant violated: {_violations}")

    # --- Build Final Result ---
    # Merge primary + auxiliary per-camera errors so all cameras appear in diagnostics
    all_per_camera = dict(reproj_errors.per_camera)
    if aux_reproj is not None:
        all_per_camera.update(aux_reproj.per_camera)

    # Merge primary + auxiliary residuals and camera labels
    if config.save_detailed_residuals:
        all_residuals = reproj_errors.residuals
        all_labels = (
            reproj_errors.camera_labels.tolist()
            if reproj_errors.camera_labels is not None
            else []
        )
        if aux_reproj is not None and len(aux_reproj.residuals) > 0:
            all_residuals = np.concatenate(
                [reproj_errors.residuals, aux_reproj.residuals]
            )
            aux_labels = (
                aux_reproj.camera_labels.tolist()
                if aux_reproj.camera_labels is not None
                else []
            )
            all_labels = all_labels + aux_labels
    else:
        all_residuals = None
        all_labels = None

    diagnostics = DiagnosticsData(
        reprojection_error_rms=reproj_errors.rms,
        reprojection_error_per_camera=all_per_camera,
        validation_3d_error_mean=reconstruction_errors.mean,
        validation_3d_error_std=reconstruction_errors.std,
        per_corner_residuals=all_residuals,
        per_corner_camera_labels=all_labels or None,
        per_frame_errors=(
            reproj_errors.per_frame if config.save_detailed_residuals else None
        ),
    )

    metadata = CalibrationMetadata(
        calibration_date=datetime.now().isoformat(),
        software_version=importlib.metadata.version("aquacal"),
        config_hash=_compute_config_hash(config),
        num_frames_used=len(optim_detections.frames),
        num_frames_holdout=len(val_detections.frames),
        seed=config.seed,
    )

    result = _build_calibration_result(
        intrinsics=final_intrinsics,
        extrinsics=final_extrinsics,
        water_z_values=final_distances,
        board_config=config.board,
        interface_params=interface_params,
        diagnostics=diagnostics,
        metadata=metadata,
        auxiliary_cameras=set(config.auxiliary_cameras),
    )

    # --- Save Calibration ---
    print("\n[Save] Saving calibration result...")
    output_path = config.output_dir / "calibration.json"
    save_calibration(result, output_path)
    print(f"  Saved to {output_path}")

    # --- Save benchmark.json (BENCH-04) ---
    if config.save_benchmark:
        problem_shape = {
            "n_cameras": len(final_intrinsics),
            "n_frames_calibration": len(optim_detections.frames),
            "n_frames_holdout": len(val_detections.frames),
            # The merged degeneracy total is recorded in BOTH places, on
            # purpose (D-11):
            #   * the whole `discard_stats` dict goes in as its own top-level
            #     block below, which is the structural half -- every future
            #     counter then reaches benchmark.json automatically. DEGEN-01's
            #     defect was precisely a field that existed in `discard_stats`
            #     and was never written into `problem_shape`, and a hand-picked
            #     field list reproduces that defect's exact shape.
            #   * this mirror exists only so the pre-existing read shape keeps
            #     working -- check_rerun_gates.py's first lookup is
            #     `record["problem_shape"][key]`, and every existing consumer
            #     keeps its key.
            # Accepted cost: some duplication with diagnostics.json.
            "degenerate_observations_at_solution": discard_stats.get(
                "degenerate_observations_at_solution", 0
            ),
        }
        solver_config = {
            "robust_loss": config.robust_loss,
            "loss_scale": config.loss_scale,
            "refine_intrinsics": config.refine_intrinsics,
            "interface_normal_fixed": config.interface_normal_fixed,
            # Provenance only (EXP-11): the master seed that drove the holdout split
            # (split_detections). Not read by anything that computes.
            "seed": config.seed,
        }
        accuracy = {
            # Copied verbatim from the already-computed DiagnosticsData-feeding
            # variables (D-06) -- never recomputed here.
            "reprojection_rms": float(reproj_errors.rms),
            "validation_3d_error_mean": float(reconstruction_errors.mean),
            "validation_3d_error_std": float(reconstruction_errors.std),
        }
        benchmark_record = assemble_benchmark_record(
            problem_shape=problem_shape,
            timings=timings,
            diagnostics=solver_diagnostics,
            solver_config=solver_config,
            accuracy=accuracy,
            environment=capture_environment(),
            # Explicit None (not just an empty dict) so the all-memory-keys-
            # absent behavior is unambiguous even if the collector happened
            # to end up empty for an unrelated reason.
            memory_readings=memory_readings if config.benchmark_memory else None,
            # Copied, as the save_diagnostic_report call above already does,
            # so the record can never alias a dict that later mutates.
            discard_stats=dict(discard_stats),
        )
        write_benchmark_json(benchmark_record, config.output_dir / "benchmark.json")
        print("  Saved benchmark.json")

    print("\n" + "=" * 60)
    print("Calibration complete!")
    print("  Primary cameras:")
    if np.isnan(reproj_errors.rms):
        print("    Reprojection RMS: N/A")
    else:
        print(f"    Reprojection RMS: {reproj_errors.rms:.3f} pixels")
    if np.isnan(reconstruction_errors.mean):
        print("    3D error: N/A")
    else:
        print(
            f"    3D error: MAE {reconstruction_errors.mean * 1000:.2f} mm, "
            f"RMSE {reconstruction_errors.rmse * 1000:.2f} mm "
            f"({reconstruction_errors.percent_error:.1f}%)"
        )
    if aux_cam_names:
        print("  Auxiliary cameras:")
        for cam_name in sorted(aux_cam_names):
            if aux_reproj and cam_name in aux_reproj.per_camera:
                rms = aux_reproj.per_camera[cam_name]
                print(f"    {cam_name}: RMS {rms:.3f} pixels")
    print("=" * 60)

    return result


def _filter_cameras(
    result: CalibrationResult,
    camera_names: set[str],
) -> CalibrationResult:
    """
    Create a new CalibrationResult containing only the specified cameras.

    Args:
        result: Original CalibrationResult
        camera_names: Set of camera names to include

    Returns:
        New CalibrationResult with filtered cameras
    """
    filtered_cameras = {
        name: calib for name, calib in result.cameras.items() if name in camera_names
    }

    return CalibrationResult(
        cameras=filtered_cameras,
        interface=result.interface,
        board=result.board,
        diagnostics=result.diagnostics,
        metadata=result.metadata,
    )


def _build_calibration_result(
    intrinsics: dict[str, CameraIntrinsics],
    extrinsics: dict[str, CameraExtrinsics],
    water_z_values: dict[str, float],
    board_config: BoardConfig,
    interface_params: InterfaceParams,
    diagnostics: DiagnosticsData,
    metadata: CalibrationMetadata,
    auxiliary_cameras: set[str] | None = None,
) -> CalibrationResult:
    """
    Assemble final CalibrationResult from components.

    Args:
        intrinsics: Per-camera intrinsic parameters
        extrinsics: Per-camera extrinsic parameters
        water_z_values: Per-camera interface distances
        board_config: Board configuration used
        interface_params: Interface parameters (normal, refractive indices)
        diagnostics: Validation diagnostics
        metadata: Calibration metadata
        auxiliary_cameras: Set of auxiliary camera names

    Returns:
        Complete CalibrationResult
    """
    cameras = {}
    for cam_name in intrinsics:
        cameras[cam_name] = CameraCalibration(
            name=cam_name,
            intrinsics=intrinsics[cam_name],
            extrinsics=extrinsics[cam_name],
            water_z=water_z_values[cam_name],
            is_auxiliary=cam_name in (auxiliary_cameras or set()),
        )

    return CalibrationResult(
        cameras=cameras,
        interface=interface_params,
        board=board_config,
        diagnostics=diagnostics,
        metadata=metadata,
    )


def _dump_stage_calibration(
    stage: str,
    config: CalibrationConfig,
    intrinsics: dict[str, CameraIntrinsics],
    extrinsics: dict[str, CameraExtrinsics],
    water_z_values: dict[str, float],
    interface_normal: Vec3,
    auxiliary_cameras: set[str] | None = None,
) -> Path:
    """Write one bundle-adjustment stage's intermediate calibration.

    Purely additive observability hook (HOOK-01): builds a `CalibrationResult`
    from the stage's intermediate extrinsics/water_z (following the same
    zeroed-`DiagnosticsData` template as the unconditional post-Stage-2
    `calibration_initial.json` dump) and writes it to
    `output_dir/internals/calibration_{stage}.json`. Does not read or mutate
    any value flowing into `calibration_initial.json` or `calibration.json`.

    Args:
        stage: Stage label used in the output filename, e.g. "stage3",
            "stage3_rerun", "stage3_intrinsic_pass".
        config: Calibration configuration (used for output_dir, board, n_air,
            n_water, and config_hash).
        intrinsics: Per-camera intrinsic parameters at this stage.
        extrinsics: Per-camera extrinsic parameters at this stage.
        water_z_values: Per-camera interface distances at this stage.
        interface_normal: Interface normal vector, shape (3,).
        auxiliary_cameras: Set of auxiliary camera names, if any.

    Returns:
        Path to the written JSON file.
    """
    internals_dir = ensure_internals_dir(config.output_dir)
    path = internals_dir / f"calibration_{stage}.json"
    warn_if_overwriting(path)

    result = _build_calibration_result(
        intrinsics=intrinsics,
        extrinsics=extrinsics,
        water_z_values=water_z_values,
        board_config=config.board,
        interface_params=InterfaceParams(
            normal=interface_normal,
            n_air=config.n_air,
            n_water=config.n_water,
        ),
        diagnostics=DiagnosticsData(
            reprojection_error_rms=0.0,
            reprojection_error_per_camera={},
            validation_3d_error_mean=0.0,
            validation_3d_error_std=0.0,
        ),
        metadata=CalibrationMetadata(
            calibration_date=datetime.now().isoformat(),
            software_version=importlib.metadata.version("aquacal"),
            config_hash=_compute_config_hash(config),
            num_frames_used=0,
            num_frames_holdout=0,
            seed=config.seed,
        ),
        auxiliary_cameras=auxiliary_cameras,
    )

    save_calibration(result, path)
    return path


def _compute_config_hash(config: CalibrationConfig) -> str:
    """
    Compute hash of configuration for reproducibility tracking.

    Args:
        config: Calibration configuration

    Returns:
        Hex string hash of configuration
    """
    # Create deterministic string representation
    hash_input = (
        f"{config.board.squares_x},{config.board.squares_y},"
        f"{config.board.square_size},{config.board.marker_size},"
        f"{config.n_air},{config.n_water},"
        f"{config.robust_loss},{config.loss_scale},"
        f"{config.holdout_fraction},{config.seed}"
    )

    # Include intrinsic_board if provided
    if config.intrinsic_board is not None:
        hash_input += (
            f",intrinsic:{config.intrinsic_board.squares_x},"
            f"{config.intrinsic_board.squares_y},"
            f"{config.intrinsic_board.square_size},"
            f"{config.intrinsic_board.marker_size}"
        )

    # Include initial_water_z if provided
    if config.initial_water_z is not None:
        # Sort by camera name for deterministic hash
        sorted_distances = sorted(config.initial_water_z.items())
        distance_str = ",".join(f"{cam}:{dist}" for cam, dist in sorted_distances)
        hash_input += f",init_dist:{distance_str}"

    return hashlib.md5(hash_input.encode()).hexdigest()[:12]
