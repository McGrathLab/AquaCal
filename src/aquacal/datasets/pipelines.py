"""Shared experiment pipelines over synthetic scenarios."""

from __future__ import annotations

import time

import numpy as np

from aquacal.calibration._observability import SolverDiagnostics
from aquacal.calibration.extrinsics import build_pose_graph, estimate_extrinsics
from aquacal.calibration.interface_estimation import optimize_interface
from aquacal.calibration.refinement import joint_refinement
from aquacal.config.schema import (
    CalibrationMetadata,
    CalibrationResult,
    CameraCalibration,
    DetectionResult,
    DiagnosticsData,
    InterfaceParams,
    PerCameraErrors,
)
from aquacal.core.board import BoardGeometry
from aquacal.datasets.synthetic import SyntheticScenario, generate_synthetic_detections
from aquacal.io import capture_peak_memory
from aquacal.validation.reconstruction import DistanceErrors, compute_3d_distance_errors


def calibrate_synthetic(
    scenario: SyntheticScenario,
    n_water: float,
    refine_intrinsics: bool = True,
    seed: int = 42,
    diagnostics_out: dict[str, SolverDiagnostics] | None = None,
    timings_out: dict[str, float] | None = None,
    memory_out: dict[str, dict] | None = None,
    normal_fixed: bool = True,
    discard_stats_out: dict[str, int] | None = None,
) -> tuple[CalibrationResult, DetectionResult]:
    """Run full calibration pipeline (Stage 2 through Stage 3's second pass) on synthetic data.

    Args:
        scenario: Synthetic scenario with ground truth. ``scenario.n_air`` /
            ``scenario.n_water`` are the indices the ground-truth detections are
            generated at.
        n_water: Target refractive index for water (1.0 for non-refractive, 1.333 for
            refractive). This is the index the calibration assumes, which may
            deliberately differ from the scenario's own ``n_water`` — that mismatch
            is the mechanism the index-sensitivity experiment uses.
        refine_intrinsics: If True, run Stage 3's second pass, with intrinsics
            unlocked. If False, intrinsics are held at the scenario's ground-truth
            values (not air-estimated intrinsics) — this branch is a best-case bound,
            not a realistic "fixed from air calibration" scenario.
        seed: Seed forwarded to synthetic detection generation, so reproductions of
            a given run only need to pass the same seed. Default 42 preserves the
            pre-existing reproduction bar.
        diagnostics_out: Optional mapping supplying ``SolverDiagnostics`` instances to
            populate in place, keyed by the settled Phase-18 stage vocabulary
            (``"stage3_interface_optimization"``, ``"stage3_intrinsic_pass"``).
            When ``None`` (the default), no diagnostics are captured and behavior is
            byte-identical to omitting this argument entirely.
        timings_out: Optional mapping populated in place with wall-clock seconds per
            stage, keyed the same way as ``diagnostics_out``
            (``"stage3_interface_optimization"``, ``"stage3_intrinsic_pass"``).
            Mirrors ``run_calibration_from_config``'s internal ``_time_stage``
            instrumentation for direct-call experiments that bypass the pipeline
            (D-09). When ``None`` (the default), no timing is captured and behavior
            is byte-identical to omitting this argument entirely.
        memory_out: Optional mapping populated in place with ``capture_peak_memory``
            readings, keyed ``"_baseline"`` plus the settled Phase-18 stage names
            ``"stage3_interface_optimization"`` and ``"stage3_intrinsic_pass"``. The
            readings are monotonic high-water marks, so consecutive deltas attribute
            growth to a stage rather than reporting a stage's own allocation.
            ``"stage3_intrinsic_pass"`` is absent when ``refine_intrinsics=False``.
            When ``None`` (the default), no memory is captured and behavior is
            byte-identical to omitting this argument entirely.
        normal_fixed: Forwarded unchanged to both Stage-3 passes
            (``optimize_interface`` and ``joint_refinement``). ``True`` (the default)
            fixes the interface normal to ``[0, 0, -1]`` and matches
            ``optimize_interface``'s and ``joint_refinement``'s own defaults, so
            omitting it reproduces the historical behavior exactly. ``False`` adds
            the two interface-tilt parameters and matches
            ``CalibrationConfig.interface_normal_fixed``, which is the configuration
            E2's real-rig run and the manuscript's ``tab:cpr`` rows were produced
            under. A caller comparing synthetic results against those published
            numbers must pass ``False``.

    Returns:
        Tuple of (CalibrationResult, DetectionResult). The detections are needed
        downstream for reconstruction evaluation.
    """
    # Create board geometry
    board = BoardGeometry(scenario.board_config)

    # Generate synthetic detections
    detections = generate_synthetic_detections(
        intrinsics=scenario.intrinsics,
        extrinsics=scenario.extrinsics,
        water_zs=scenario.water_zs,
        board=board,
        board_poses=scenario.board_poses,
        noise_std=scenario.noise_std,
        seed=seed,
        n_air=scenario.n_air,
        n_water=scenario.n_water,
    )

    # Stage 2: Extrinsic initialization
    print("Stage 2: Extrinsic initialization...")
    # Use the camera closest to the world origin as reference — this matches
    # the reference camera from the original calibration (which defines the
    # world frame origin) and avoids coordinate-frame mismatch with GT.
    reference_camera = min(
        scenario.extrinsics,
        key=lambda c: np.linalg.norm(scenario.extrinsics[c].C),
    )
    interface_normal = np.array([0.0, 0.0, -1.0], dtype=np.float64)
    if memory_out is not None:
        memory_out["_baseline"] = capture_peak_memory()
    pose_graph = build_pose_graph(detections, min_cameras=2)
    initial_extrinsics = estimate_extrinsics(
        pose_graph,
        scenario.intrinsics,
        board,
        reference_camera,
        water_zs=scenario.water_zs if n_water != 1.0 else None,
        interface_normal=interface_normal,
        n_air=1.0,
        n_water=n_water,
        discard_stats_out=discard_stats_out,
    )

    # Stage 3: Joint refractive optimization
    print("Stage 3: Joint refractive optimization...")
    stage3_diagnostics_out = (
        diagnostics_out.get("stage3_interface_optimization")
        if diagnostics_out is not None
        else None
    )
    _t0 = time.perf_counter()
    opt_extrinsics, opt_distances, opt_poses, rms = optimize_interface(
        detections=detections,
        intrinsics=scenario.intrinsics,
        initial_extrinsics=initial_extrinsics,
        board=board,
        reference_camera=reference_camera,
        initial_water_zs=(
            scenario.water_zs
            if scenario.name != "calibration"
            else {cam: 1.0 for cam in scenario.intrinsics}
        ),
        interface_normal=interface_normal,
        n_air=1.0,
        n_water=n_water,
        loss="huber",
        loss_scale=1.0,
        min_corners=4,
        diagnostics_out=stage3_diagnostics_out,
        normal_fixed=normal_fixed,
        discard_stats_out=discard_stats_out,
    )
    if timings_out is not None:
        timings_out["stage3_interface_optimization"] = time.perf_counter() - _t0
    if memory_out is not None:
        memory_out["stage3_interface_optimization"] = capture_peak_memory()

    # Stage 3's second pass: intrinsic refinement (if requested)
    if refine_intrinsics:
        print("Stage 3's second pass: Intrinsic refinement...")
        stage3_result = (opt_extrinsics, opt_distances, opt_poses, rms)
        intrinsic_pass_diagnostics_out = (
            diagnostics_out.get("stage3_intrinsic_pass")
            if diagnostics_out is not None
            else None
        )
        _t0 = time.perf_counter()
        opt_extrinsics, opt_distances, opt_poses, opt_intrinsics, rms = (
            joint_refinement(
                stage3_result=stage3_result,
                detections=detections,
                intrinsics=scenario.intrinsics,
                board=board,
                reference_camera=reference_camera,
                refine_intrinsics=True,
                interface_normal=interface_normal,
                n_air=1.0,
                n_water=n_water,
                loss="huber",
                loss_scale=1.0,
                min_corners=4,
                diagnostics_out=intrinsic_pass_diagnostics_out,
                normal_fixed=normal_fixed,
                discard_stats_out=discard_stats_out,
            )
        )
        if timings_out is not None:
            timings_out["stage3_intrinsic_pass"] = time.perf_counter() - _t0
        if memory_out is not None:
            memory_out["stage3_intrinsic_pass"] = capture_peak_memory()
    else:
        # Use ground truth intrinsics
        opt_intrinsics = scenario.intrinsics

    # Build CalibrationResult
    cameras = {}
    for cam_name in scenario.intrinsics:
        cameras[cam_name] = CameraCalibration(
            name=cam_name,
            intrinsics=opt_intrinsics[cam_name],
            extrinsics=opt_extrinsics[cam_name],
            water_z=opt_distances[cam_name],
        )

    interface_params = InterfaceParams(
        normal=interface_normal,
        n_air=1.0,
        n_water=n_water,
    )

    diagnostics = DiagnosticsData(
        reprojection_error_rms=rms,
        reprojection_error_per_camera={},
        validation_3d_error_mean=0.0,
        validation_3d_error_std=0.0,
    )

    metadata = CalibrationMetadata(
        calibration_date="synthetic",
        software_version="test",
        config_hash="synthetic",
        num_frames_used=len(opt_poses),
        num_frames_holdout=0,
    )

    result = CalibrationResult(
        cameras=cameras,
        interface=interface_params,
        board=scenario.board_config,
        diagnostics=diagnostics,
        metadata=metadata,
    )

    return result, detections


def evaluate_reconstruction(
    calibration: CalibrationResult,
    board: BoardGeometry,
    test_detections: DetectionResult,
) -> DistanceErrors:
    """Evaluate reconstruction quality on test data.

    Args:
        calibration: Calibration result from ``calibrate_synthetic``.
        board: Board geometry.
        test_detections: Detection result for test poses.

    Returns:
        DistanceErrors with reconstruction error statistics and spatial measurements.
    """
    return compute_3d_distance_errors(
        calibration=calibration,
        detections=test_detections,
        board=board,
        include_per_pair=False,
        include_spatial=True,
    )


def compute_per_camera_errors(
    result: CalibrationResult,
    ground_truth: SyntheticScenario,
    *,
    gauge_correct_z: bool = False,
) -> dict[str, PerCameraErrors]:
    """Compute per-camera parameter errors vs ground truth.

    Args:
        result: Calibration result.
        ground_truth: Synthetic scenario with known ground truth.
        gauge_correct_z: A per-camera Z position error is only meaningful up to the
            world frame's Z datum, which the reference camera pins at zero by
            construction. Without this correction, a global datum offset the
            optimizer applied to the entire rig (an artifact of choosing where
            "Z=0" is, not a real geometric error) is charged entirely to every
            non-reference camera while the reference camera's own near-zero raw
            error is left uncorrected, making cross-camera Z-error comparisons
            attribution-confounded. ``gauge_correct_z=True`` subtracts the mean raw
            Z error across the non-reference (free) cameras from every camera's raw
            Z error, including the reference camera's own — revealing the
            systematic Z shift a model's biased geometry would apply to the entire
            rig, rather than an artifact of the reference camera's fixed position.
            This is why the reference camera's ``xy_position_error_mm`` is exactly
            ``0.0`` (it is pinned at the origin, a separate, unrelated geometric
            fact) while its ``z_position_error_mm`` after correction is a small
            nonzero residual, not zero. Default ``False`` so existing callers are
            unaffected.

    Returns:
        Dict keyed by camera name, each value a :class:`PerCameraErrors` mapping
        containing:
        - focal_length_error_pct: Relative error in fx (%)
        - z_position_error_mm: Signed Z position error (mm)
        - xy_position_error_mm: XY position error magnitude (mm)
        - k1_error: Absolute error in k1 distortion coefficient
        - k2_error: Absolute error in k2 distortion coefficient
        - gt_x_m, gt_y_m, gt_z_m: Ground-truth camera center (m)
        - est_x_m, est_y_m, est_z_m: Calibrated camera center (m)
        - reprojection_rms_px: Calibration-level reprojection RMS (px), repeated on
          every camera's row.
    """
    errors: dict[str, PerCameraErrors] = {}

    for cam_name in ground_truth.intrinsics:
        if cam_name not in result.cameras:
            continue

        gt_intr = ground_truth.intrinsics[cam_name]
        gt_extr = ground_truth.extrinsics[cam_name]

        cal = result.cameras[cam_name]
        cal_intr = cal.intrinsics
        cal_extr = cal.extrinsics

        # Focal length error (relative, %)
        fx_gt = gt_intr.K[0, 0]
        fx_cal = cal_intr.K[0, 0]
        focal_length_error_pct = (fx_cal - fx_gt) / fx_gt * 100

        # Camera position errors
        C_gt = gt_extr.C
        C_cal = cal_extr.C

        # Z position error (signed, mm)
        z_position_error_mm = (C_cal[2] - C_gt[2]) * 1000

        # XY position error (magnitude, mm)
        xy_diff = C_cal[:2] - C_gt[:2]
        xy_position_error_mm = np.linalg.norm(xy_diff) * 1000

        # Distortion coefficient errors
        k1_gt = gt_intr.dist_coeffs[0]
        k2_gt = gt_intr.dist_coeffs[1]
        k1_cal = cal_intr.dist_coeffs[0]
        k2_cal = cal_intr.dist_coeffs[1]

        k1_error = k1_cal - k1_gt
        k2_error = k2_cal - k2_gt

        errors[cam_name] = {
            "focal_length_error_pct": focal_length_error_pct,
            "z_position_error_mm": z_position_error_mm,
            "xy_position_error_mm": xy_position_error_mm,
            "k1_error": k1_error,
            "k2_error": k2_error,
            "gt_x_m": C_gt[0],
            "gt_y_m": C_gt[1],
            "gt_z_m": C_gt[2],
            "est_x_m": C_cal[0],
            "est_y_m": C_cal[1],
            "est_z_m": C_cal[2],
            "reprojection_rms_px": result.diagnostics.reprojection_error_rms,
        }

    if gauge_correct_z:
        # gauge_correct_z: subtract the free-camera mean raw Z error from every
        # camera's z_position_error_mm, including the reference camera's own.
        camera_names = sorted(
            ground_truth.intrinsics, key=lambda s: int(s.replace("cam", ""))
        )
        free_cameras = [c for c in camera_names if c != camera_names[0] and c in errors]
        mean_free_z = np.mean([errors[c]["z_position_error_mm"] for c in free_cameras])
        for cam_name in errors:
            errors[cam_name]["z_position_error_mm"] -= mean_free_z

    return errors
