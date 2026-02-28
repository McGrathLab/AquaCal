"""Unit tests for the point correspondence refinement API (refine_calibration)."""

from __future__ import annotations

import copy

import numpy as np
import pytest

from aquacal.calibration.point_refinement import refine_calibration
from aquacal.config.schema import (
    BoardConfig,
    CalibrationMetadata,
    CalibrationResult,
    CameraCalibration,
    CameraExtrinsics,
    CameraIntrinsics,
    DiagnosticsData,
    InsufficientDataError,
    InterfaceParams,
    PointCorrespondence,
)
from aquacal.core.camera import create_camera
from aquacal.core.interface_model import Interface
from aquacal.core.refractive_geometry import refractive_project_batch

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def calibration_result() -> CalibrationResult:
    """Build a complete CalibrationResult with 3 cameras for testing."""
    K = np.array(
        [[500.0, 0.0, 320.0], [0.0, 500.0, 240.0], [0.0, 0.0, 1.0]], dtype=np.float64
    )
    dist = np.zeros(5, dtype=np.float64)
    water_z = 0.15

    cameras = {
        "cam0": CameraCalibration(
            name="cam0",
            intrinsics=CameraIntrinsics(
                K=K.copy(), dist_coeffs=dist.copy(), image_size=(640, 480)
            ),
            extrinsics=CameraExtrinsics(
                R=np.eye(3, dtype=np.float64), t=np.zeros(3, dtype=np.float64)
            ),
            water_z=water_z,
        ),
        "cam1": CameraCalibration(
            name="cam1",
            intrinsics=CameraIntrinsics(
                K=K.copy(), dist_coeffs=dist.copy(), image_size=(640, 480)
            ),
            extrinsics=CameraExtrinsics(
                R=np.eye(3, dtype=np.float64),
                t=np.array([0.1, 0.0, 0.0], dtype=np.float64),
            ),
            water_z=water_z,
        ),
        "cam2": CameraCalibration(
            name="cam2",
            intrinsics=CameraIntrinsics(
                K=K.copy(), dist_coeffs=dist.copy(), image_size=(640, 480)
            ),
            extrinsics=CameraExtrinsics(
                R=np.eye(3, dtype=np.float64),
                t=np.array([0.0, 0.1, 0.0], dtype=np.float64),
            ),
            water_z=water_z,
        ),
    }

    interface = InterfaceParams(
        normal=np.array([0.0, 0.0, -1.0], dtype=np.float64),
        n_air=1.0,
        n_water=1.333,
    )

    board = BoardConfig(
        squares_x=6,
        squares_y=5,
        square_size=0.04,
        marker_size=0.03,
        dictionary="DICT_4X4_50",
    )

    diagnostics = DiagnosticsData(
        reprojection_error_rms=0.5,
        reprojection_error_per_camera={"cam0": 0.5, "cam1": 0.5, "cam2": 0.5},
        validation_3d_error_mean=0.0,
        validation_3d_error_std=0.0,
    )

    metadata = CalibrationMetadata(
        calibration_date="2026-02-28",
        software_version="1.6.0",
        config_hash="abc123",
        num_frames_used=10,
        num_frames_holdout=2,
    )

    return CalibrationResult(
        cameras=cameras,
        interface=interface,
        board=board,
        diagnostics=diagnostics,
        metadata=metadata,
    )


@pytest.fixture
def synthetic_correspondences(
    calibration_result: CalibrationResult,
) -> list[PointCorrespondence]:
    """Generate ~30 PointCorrespondence objects using true refractive projections.

    3D points distributed underwater (Z between 0.3 and 0.6), with small
    Gaussian noise (sigma=0.5 px) added to observed pixels. All weights = 1.0.
    """
    np.random.seed(42)
    n_points = 30
    water_z = 0.15
    interface_normal = np.array([0.0, 0.0, -1.0], dtype=np.float64)

    # Generate random underwater 3D points
    xs = np.random.uniform(-0.15, 0.15, n_points)
    ys = np.random.uniform(-0.15, 0.15, n_points)
    zs = np.random.uniform(0.3, 0.6, n_points)
    points_3d = np.column_stack([xs, ys, zs])

    correspondences = []
    for i in range(n_points):
        pt = points_3d[i : i + 1]  # shape (1, 3)
        observations = {}

        # Decide which cameras see this point (all 3 for most, 2 for some)
        # Use all 3 cameras for most points (25/30), 2 cameras for a few
        if i < 25:
            cam_names = ["cam0", "cam1", "cam2"]
        elif i < 27:
            cam_names = ["cam0", "cam1"]
        else:
            cam_names = ["cam1", "cam2"]

        valid = True
        for cam_name in cam_names:
            cam_cal = calibration_result.cameras[cam_name]
            camera = create_camera(cam_name, cam_cal.intrinsics, cam_cal.extrinsics)
            interface = Interface(
                normal=interface_normal,
                camera_distances={cam_name: water_z},
                n_air=1.0,
                n_water=1.333,
            )
            projected = refractive_project_batch(camera, interface, pt)
            pixel = projected[0]

            if np.isnan(pixel).any():
                valid = False
                break

            # Add small Gaussian noise
            noise = np.random.normal(0.0, 0.5, size=2)
            observations[cam_name] = pixel + noise

        if valid and len(observations) >= 2:
            correspondences.append(
                PointCorrespondence(
                    point_3d=points_3d[i].copy(),
                    observations=observations,
                    weight=1.0,
                )
            )

    return correspondences


@pytest.fixture
def perturbed_result(calibration_result: CalibrationResult) -> CalibrationResult:
    """Copy calibration_result but perturb cam1/cam2 extrinsics and water_z slightly.

    This simulates a 'close but not perfect' calibration that refinement should improve:
    - cam1.t += [0.005, 0, 0] (5 mm perturbation in X)
    - cam2.t += [0, 0.005, 0] (5 mm perturbation in Y)
    - water_z += 0.01 (1 cm perturbation)
    """
    perturbed = copy.deepcopy(calibration_result)
    perturbed_water_z = 0.15 + 0.01

    cam1 = perturbed.cameras["cam1"]
    cam1.extrinsics.t = cam1.extrinsics.t + np.array(
        [0.005, 0.0, 0.0], dtype=np.float64
    )
    cam1.water_z = perturbed_water_z

    cam2 = perturbed.cameras["cam2"]
    cam2.extrinsics.t = cam2.extrinsics.t + np.array(
        [0.0, 0.005, 0.0], dtype=np.float64
    )
    cam2.water_z = perturbed_water_z

    perturbed.cameras["cam0"].water_z = perturbed_water_z

    return perturbed


# ---------------------------------------------------------------------------
# Tests: Input Validation
# ---------------------------------------------------------------------------


class TestInputValidation:
    """Tests that refine_calibration() enforces input contract."""

    def test_empty_correspondences_raises(self, calibration_result):
        """Empty correspondence list raises ValueError."""
        with pytest.raises(ValueError, match="empty"):
            refine_calibration(calibration_result, [])

    def test_negative_weight_raises(
        self, calibration_result, synthetic_correspondences
    ):
        """Negative weight raises ValueError."""
        bad = PointCorrespondence(
            point_3d=np.array([0.0, 0.0, 0.4]),
            observations={
                "cam0": np.array([320.0, 240.0]),
                "cam1": np.array([350.0, 240.0]),
            },
            weight=-1.0,
        )
        with pytest.raises(ValueError, match="negative weight"):
            refine_calibration(calibration_result, [bad] + synthetic_correspondences)

    def test_unknown_camera_raises(self, calibration_result, synthetic_correspondences):
        """Observation for an unknown camera name raises ValueError."""
        bad = PointCorrespondence(
            point_3d=np.array([0.0, 0.0, 0.4]),
            observations={
                "cam0": np.array([320.0, 240.0]),
                "camX": np.array([400.0, 260.0]),
            },
            weight=1.0,
        )
        with pytest.raises(ValueError, match="camX"):
            refine_calibration(calibration_result, [bad] + synthetic_correspondences)

    def test_too_few_observations_raises(
        self, calibration_result, synthetic_correspondences
    ):
        """Correspondence with only 1 camera observation raises ValueError."""
        bad = PointCorrespondence(
            point_3d=np.array([0.0, 0.0, 0.4]),
            observations={"cam0": np.array([320.0, 240.0])},
            weight=1.0,
        )
        with pytest.raises(ValueError, match="at least 2"):
            refine_calibration(calibration_result, [bad] + synthetic_correspondences)

    def test_too_few_correspondences_raises(self, calibration_result):
        """Fewer than 10 active correspondences raises InsufficientDataError."""
        # Create 5 valid correspondences (below the 10 minimum threshold)
        corrs = []
        for i in range(5):
            corrs.append(
                PointCorrespondence(
                    point_3d=np.array([0.01 * i, 0.0, 0.4]),
                    observations={
                        "cam0": np.array([320.0 + i, 240.0]),
                        "cam1": np.array([350.0 + i, 240.0]),
                    },
                    weight=1.0,
                )
            )
        with pytest.raises(InsufficientDataError):
            refine_calibration(calibration_result, corrs)

    def test_zero_weight_silently_dropped(
        self, calibration_result, synthetic_correspondences
    ):
        """15 zero-weight + 15 valid correspondences: zero-weight are dropped, no error."""
        # Ensure we have enough active correspondences from synthetic
        # Make 15 zero-weight correspondences
        zero_weight = []
        for i in range(15):
            zero_weight.append(
                PointCorrespondence(
                    point_3d=np.array([0.01 * i, 0.0, 0.4]),
                    observations={
                        "cam0": np.array([320.0 + i, 240.0]),
                        "cam1": np.array([350.0 + i, 240.0]),
                    },
                    weight=0.0,
                )
            )
        # Use 15 valid ones from synthetic (all have weight=1)
        active = synthetic_correspondences[:15]
        result = refine_calibration(calibration_result, zero_weight + active)
        assert isinstance(result, CalibrationResult)

    def test_all_zero_weight_raises(self, calibration_result):
        """All zero-weight correspondences raises InsufficientDataError."""
        corrs = []
        for i in range(20):
            corrs.append(
                PointCorrespondence(
                    point_3d=np.array([0.01 * i, 0.0, 0.4]),
                    observations={
                        "cam0": np.array([320.0 + i, 240.0]),
                        "cam1": np.array([350.0 + i, 240.0]),
                    },
                    weight=0.0,
                )
            )
        with pytest.raises(InsufficientDataError):
            refine_calibration(calibration_result, corrs)

    def test_bad_point_shape_raises(
        self, calibration_result, synthetic_correspondences
    ):
        """point_3d with shape (2,) raises ValueError."""
        bad = PointCorrespondence(
            point_3d=np.array([0.0, 0.4]),  # wrong shape
            observations={
                "cam0": np.array([320.0, 240.0]),
                "cam1": np.array([350.0, 240.0]),
            },
            weight=1.0,
        )
        with pytest.raises(ValueError, match="point_3d"):
            refine_calibration(calibration_result, [bad] + synthetic_correspondences)

    def test_bad_pixel_shape_raises(
        self, calibration_result, synthetic_correspondences
    ):
        """Observation pixel with shape (3,) raises ValueError."""
        bad = PointCorrespondence(
            point_3d=np.array([0.0, 0.0, 0.4]),
            observations={
                "cam0": np.array([320.0, 240.0, 0.0]),  # wrong shape
                "cam1": np.array([350.0, 240.0]),
            },
            weight=1.0,
        )
        with pytest.raises(ValueError, match="shape"):
            refine_calibration(calibration_result, [bad] + synthetic_correspondences)


# ---------------------------------------------------------------------------
# Tests: Refinement Optimization
# ---------------------------------------------------------------------------


def _compute_reprojection_rms(
    result: CalibrationResult,
    correspondences: list[PointCorrespondence],
) -> float:
    """Compute RMS reprojection error for the given result and correspondences.

    Args:
        result: CalibrationResult to evaluate
        correspondences: Point correspondences used to compute reprojection error

    Returns:
        RMS reprojection error in pixels
    """
    water_z = result.cameras[sorted(result.cameras.keys())[0]].water_z
    interface_normal = np.array(result.interface.normal, dtype=np.float64)
    residuals = []

    for corr in correspondences:
        if corr.weight == 0.0:
            continue
        pt = np.asarray(corr.point_3d).reshape(1, 3)
        for cam_name, observed in corr.observations.items():
            cam_cal = result.cameras[cam_name]
            camera = create_camera(cam_name, cam_cal.intrinsics, cam_cal.extrinsics)
            interface = Interface(
                normal=interface_normal,
                camera_distances={cam_name: water_z},
                n_air=result.interface.n_air,
                n_water=result.interface.n_water,
            )
            projected = refractive_project_batch(camera, interface, pt)
            pixel = projected[0]
            if not np.isnan(pixel).any():
                diff = pixel - np.asarray(observed)
                residuals.extend(diff.tolist())

    if not residuals:
        return float("inf")
    return float(np.sqrt(np.mean(np.array(residuals) ** 2)))


class TestRefinementOptimization:
    """Tests that refine_calibration() actually improves calibration quality."""

    @pytest.mark.slow
    def test_refinement_reduces_reprojection_error(
        self, perturbed_result, synthetic_correspondences
    ):
        """Refinement from perturbed state reduces RMS reprojection error."""
        rms_before = _compute_reprojection_rms(
            perturbed_result, synthetic_correspondences
        )
        refined = refine_calibration(perturbed_result, synthetic_correspondences)
        rms_after = _compute_reprojection_rms(refined, synthetic_correspondences)

        assert rms_after < rms_before, (
            f"Expected RMS to decrease: before={rms_before:.4f}, after={rms_after:.4f}"
        )

    @pytest.mark.slow
    def test_intrinsics_unchanged(self, perturbed_result, synthetic_correspondences):
        """Intrinsics (K and dist_coeffs) are identical before and after refinement."""
        refined = refine_calibration(perturbed_result, synthetic_correspondences)

        for cam_name, cam_cal in perturbed_result.cameras.items():
            original_K = cam_cal.intrinsics.K
            refined_K = refined.cameras[cam_name].intrinsics.K
            np.testing.assert_array_equal(
                original_K,
                refined_K,
                err_msg=f"Intrinsic K changed for {cam_name}",
            )

            original_dist = cam_cal.intrinsics.dist_coeffs
            refined_dist = refined.cameras[cam_name].intrinsics.dist_coeffs
            np.testing.assert_array_equal(
                original_dist,
                refined_dist,
                err_msg=f"dist_coeffs changed for {cam_name}",
            )

    @pytest.mark.slow
    def test_extrinsics_change(self, perturbed_result, synthetic_correspondences):
        """At least one non-reference camera's extrinsics differ after refinement."""
        refined = refine_calibration(perturbed_result, synthetic_correspondences)

        camera_order = sorted(perturbed_result.cameras.keys())
        non_ref_cameras = camera_order[1:]  # cam1, cam2

        any_changed = False
        for cam_name in non_ref_cameras:
            t_before = perturbed_result.cameras[cam_name].extrinsics.t
            t_after = refined.cameras[cam_name].extrinsics.t
            if not np.allclose(t_before, t_after, atol=1e-6):
                any_changed = True
                break

        assert any_changed, (
            "Expected at least one non-reference camera extrinsics to change"
        )

    @pytest.mark.slow
    def test_reference_camera_fixed(self, perturbed_result, synthetic_correspondences):
        """Reference camera (cam0, first sorted) R and t unchanged after refinement."""
        reference = sorted(perturbed_result.cameras.keys())[0]
        ref_R_before = perturbed_result.cameras[reference].extrinsics.R.copy()
        ref_t_before = perturbed_result.cameras[reference].extrinsics.t.copy()

        refined = refine_calibration(perturbed_result, synthetic_correspondences)

        np.testing.assert_allclose(
            refined.cameras[reference].extrinsics.R,
            ref_R_before,
            atol=1e-10,
            err_msg="Reference camera R changed",
        )
        np.testing.assert_allclose(
            refined.cameras[reference].extrinsics.t,
            ref_t_before,
            atol=1e-10,
            err_msg="Reference camera t changed",
        )

    @pytest.mark.slow
    def test_water_z_positive(self, perturbed_result, synthetic_correspondences):
        """After refinement, water_z is positive for all cameras."""
        refined = refine_calibration(perturbed_result, synthetic_correspondences)

        for cam_name, cam_cal in refined.cameras.items():
            assert cam_cal.water_z > 0, (
                f"water_z non-positive for {cam_name}: {cam_cal.water_z}"
            )

    @pytest.mark.slow
    def test_returns_calibration_result(
        self, perturbed_result, synthetic_correspondences
    ):
        """Return type is CalibrationResult with all expected fields."""
        result = refine_calibration(perturbed_result, synthetic_correspondences)

        assert isinstance(result, CalibrationResult)
        assert hasattr(result, "cameras")
        assert hasattr(result, "interface")
        assert hasattr(result, "board")
        assert hasattr(result, "diagnostics")
        assert hasattr(result, "metadata")
        assert set(result.cameras.keys()) == set(perturbed_result.cameras.keys())

    def test_verbose_flag_accepted(self, perturbed_result, synthetic_correspondences):
        """refine_calibration with verbose=True runs without error."""
        # verbose=True just enables optimizer progress output, should not crash
        result = refine_calibration(
            perturbed_result, synthetic_correspondences, verbose=True
        )
        assert isinstance(result, CalibrationResult)


# ---------------------------------------------------------------------------
# Tests: Edge Cases
# ---------------------------------------------------------------------------


class TestEdgeCases:
    """Tests for edge case handling in refine_calibration()."""

    @pytest.mark.slow
    def test_already_optimal_calibration(self, calibration_result):
        """Ground truth calibration + noiseless correspondences: RMS stays small (<1 px)."""
        np.random.seed(42)
        water_z = 0.15
        interface_normal = np.array([0.0, 0.0, -1.0], dtype=np.float64)

        # Generate noiseless correspondences using ground truth
        corrs = []
        xs = np.random.uniform(-0.1, 0.1, 15)
        ys = np.random.uniform(-0.1, 0.1, 15)
        zs = np.random.uniform(0.3, 0.5, 15)

        for i in range(15):
            pt = np.array([[xs[i], ys[i], zs[i]]])
            observations = {}
            valid = True

            for cam_name in ["cam0", "cam1", "cam2"]:
                cam_cal = calibration_result.cameras[cam_name]
                camera = create_camera(cam_name, cam_cal.intrinsics, cam_cal.extrinsics)
                interface = Interface(
                    normal=interface_normal,
                    camera_distances={cam_name: water_z},
                    n_air=1.0,
                    n_water=1.333,
                )
                projected = refractive_project_batch(camera, interface, pt)
                pixel = projected[0]
                if np.isnan(pixel).any():
                    valid = False
                    break
                observations[cam_name] = pixel

            if valid and len(observations) >= 2:
                corrs.append(
                    PointCorrespondence(
                        point_3d=pt[0].copy(),
                        observations=observations,
                        weight=1.0,
                    )
                )

        assert len(corrs) >= 10, "Need at least 10 correspondences for this test"

        refined = refine_calibration(calibration_result, corrs)
        rms = _compute_reprojection_rms(refined, corrs)

        assert rms < 1.0, (
            f"Expected RMS < 1 px for noiseless ground truth; got {rms:.4f}"
        )

    @pytest.mark.slow
    def test_weighted_correspondences(
        self, perturbed_result, synthetic_correspondences
    ):
        """Mixed weights (2.0 and 0.5) complete without error."""
        # Assign alternating weights to test correspondences
        weighted = []
        for i, corr in enumerate(synthetic_correspondences):
            weight = 2.0 if i % 2 == 0 else 0.5
            weighted.append(
                PointCorrespondence(
                    point_3d=corr.point_3d.copy(),
                    observations=dict(corr.observations),
                    weight=weight,
                )
            )

        result = refine_calibration(perturbed_result, weighted)
        assert isinstance(result, CalibrationResult)


# ---------------------------------------------------------------------------
# Helpers for Phase 14 extension tests
# ---------------------------------------------------------------------------


def _generate_correspondences_from_result(
    result: CalibrationResult,
    n_points: int = 30,
    noise_sigma: float = 0.5,
    seed: int = 42,
) -> list[PointCorrespondence]:
    """Generate synthetic correspondences from a calibration result.

    Projects random underwater 3D points through each camera using the result's
    intrinsics, extrinsics, and water_z, then adds Gaussian pixel noise.

    Args:
        result: CalibrationResult to generate observations from.
        n_points: Number of 3D points to generate.
        noise_sigma: Standard deviation of pixel noise in pixels.
        seed: Random seed for reproducibility.

    Returns:
        List of PointCorrespondence objects.
    """
    rng = np.random.RandomState(seed)
    water_z = result.cameras[sorted(result.cameras.keys())[0]].water_z
    interface_normal = np.array([0.0, 0.0, -1.0], dtype=np.float64)
    cam_names = sorted(result.cameras.keys())

    xs = rng.uniform(-0.15, 0.15, n_points)
    ys = rng.uniform(-0.15, 0.15, n_points)
    zs = rng.uniform(0.3, 0.6, n_points)

    correspondences = []
    for i in range(n_points):
        pt = np.array([[xs[i], ys[i], zs[i]]])
        observations = {}
        valid = True

        for cam_name in cam_names:
            cam_cal = result.cameras[cam_name]
            camera = create_camera(cam_name, cam_cal.intrinsics, cam_cal.extrinsics)
            interface = Interface(
                normal=interface_normal,
                camera_distances={cam_name: water_z},
                n_air=result.interface.n_air,
                n_water=result.interface.n_water,
            )
            projected = refractive_project_batch(camera, interface, pt)
            pixel = projected[0]

            if np.isnan(pixel).any():
                valid = False
                break

            noise = rng.normal(0.0, noise_sigma, size=2)
            observations[cam_name] = pixel + noise

        if valid and len(observations) >= 2:
            correspondences.append(
                PointCorrespondence(
                    point_3d=pt[0].copy(),
                    observations=observations,
                    weight=1.0,
                )
            )

    return correspondences


# ---------------------------------------------------------------------------
# Tests: Intrinsics Refinement (Phase 14)
# ---------------------------------------------------------------------------


class TestIntrinsicsRefinement:
    """Tests for optional intrinsics refinement and input validation."""

    def test_invalid_loss_value(self, calibration_result, synthetic_correspondences):
        """Invalid loss string raises ValueError."""
        with pytest.raises(ValueError, match="Invalid loss"):
            refine_calibration(
                calibration_result, synthetic_correspondences, loss="softl1"
            )
        with pytest.raises(ValueError, match="Invalid loss"):
            refine_calibration(
                calibration_result, synthetic_correspondences, loss="mse"
            )

    def test_valid_loss_values_accepted(
        self, calibration_result, synthetic_correspondences
    ):
        """loss='linear', 'huber', and 'cauchy' are all accepted without error."""
        for loss_name in ["linear", "huber", "cauchy"]:
            result = refine_calibration(
                calibration_result,
                synthetic_correspondences,
                loss=loss_name,
                max_nfev=1,  # short-circuit: just prove parameter is accepted
            )
            assert isinstance(result, CalibrationResult)

    @pytest.mark.slow
    def test_intrinsics_change_when_enabled(self, calibration_result):
        """With refine_intrinsics=True and perturbed intrinsics, refinement moves toward truth."""
        # Create a result with perturbed intrinsics on cam1 and cam2
        perturbed = copy.deepcopy(calibration_result)
        # Shift cam1 fx by +20 pixels
        perturbed.cameras["cam1"].intrinsics.K[0, 0] += 20.0
        # Shift cam2 fy by -15 pixels
        perturbed.cameras["cam2"].intrinsics.K[1, 1] -= 15.0

        # Generate correspondences from ORIGINAL (correct) intrinsics
        corrs = _generate_correspondences_from_result(
            calibration_result, n_points=30, noise_sigma=0.3, seed=100
        )

        # Refine with intrinsics enabled
        refined = refine_calibration(
            perturbed, corrs, refine_intrinsics=True, intrinsics_bound_pct=0.1
        )

        # cam1: fx should have moved toward 500 (original) from 520 (perturbed)
        cam1_fx_perturbed = perturbed.cameras["cam1"].intrinsics.K[0, 0]
        cam1_fx_refined = refined.cameras["cam1"].intrinsics.K[0, 0]
        cam1_fx_original = calibration_result.cameras["cam1"].intrinsics.K[0, 0]
        error_before = abs(cam1_fx_perturbed - cam1_fx_original)
        error_after = abs(cam1_fx_refined - cam1_fx_original)
        assert error_after < error_before, (
            f"cam1 fx should move toward truth: "
            f"error_before={error_before:.2f}, error_after={error_after:.2f}"
        )

        # cam2: fy should have moved toward 500 (original) from 485 (perturbed)
        cam2_fy_perturbed = perturbed.cameras["cam2"].intrinsics.K[1, 1]
        cam2_fy_refined = refined.cameras["cam2"].intrinsics.K[1, 1]
        cam2_fy_original = calibration_result.cameras["cam2"].intrinsics.K[1, 1]
        error_before = abs(cam2_fy_perturbed - cam2_fy_original)
        error_after = abs(cam2_fy_refined - cam2_fy_original)
        assert error_after < error_before, (
            f"cam2 fy should move toward truth: "
            f"error_before={error_before:.2f}, error_after={error_after:.2f}"
        )

    @pytest.mark.slow
    def test_intrinsics_fixed_when_disabled(
        self, perturbed_result, synthetic_correspondences
    ):
        """With refine_intrinsics=False (default), intrinsics are exactly unchanged."""
        refined = refine_calibration(
            perturbed_result, synthetic_correspondences, refine_intrinsics=False
        )

        for cam_name, cam_cal in perturbed_result.cameras.items():
            np.testing.assert_array_equal(
                cam_cal.intrinsics.K,
                refined.cameras[cam_name].intrinsics.K,
                err_msg=f"K changed for {cam_name} with refine_intrinsics=False",
            )

    @pytest.mark.slow
    def test_intrinsics_bound_pct_limits_drift(
        self, calibration_result, synthetic_correspondences
    ):
        """Tight intrinsics_bound_pct=0.02 constrains all intrinsics within 2%."""
        refined = refine_calibration(
            calibration_result,
            synthetic_correspondences,
            refine_intrinsics=True,
            intrinsics_bound_pct=0.02,
        )

        bound_pct = 0.02
        for cam_name in sorted(calibration_result.cameras.keys()):
            base_K = calibration_result.cameras[cam_name].intrinsics.K
            refined_K = refined.cameras[cam_name].intrinsics.K

            for label, base_val, refined_val in [
                ("fx", base_K[0, 0], refined_K[0, 0]),
                ("fy", base_K[1, 1], refined_K[1, 1]),
                ("cx", base_K[0, 2], refined_K[0, 2]),
                ("cy", base_K[1, 2], refined_K[1, 2]),
            ]:
                lo = base_val * (1.0 - bound_pct)
                hi = base_val * (1.0 + bound_pct)
                assert lo - 1e-6 <= refined_val <= hi + 1e-6, (
                    f"{cam_name}.{label}: {refined_val:.4f} not within "
                    f"[{lo:.4f}, {hi:.4f}] (base={base_val:.4f})"
                )

    @pytest.mark.slow
    def test_normal_fixed_false_allows_tilt(self, calibration_result):
        """normal_fixed=False allows reference camera tilt to be optimized."""
        from aquacal.utils.transforms import rvec_to_matrix

        # Create a "true" calibration with small reference camera tilt
        true_result = copy.deepcopy(calibration_result)
        tilt_rvec = np.array([0.02, 0.01, 0.0])
        true_result.cameras["cam0"].extrinsics = CameraExtrinsics(
            R=rvec_to_matrix(tilt_rvec),
            t=np.zeros(3, dtype=np.float64),
        )

        # Generate correspondences from the tilted setup
        corrs = _generate_correspondences_from_result(
            true_result, n_points=30, noise_sigma=0.3, seed=200
        )

        # Create a perturbed version with reference camera at identity (no tilt)
        perturbed = copy.deepcopy(true_result)
        perturbed.cameras["cam0"].extrinsics = CameraExtrinsics(
            R=np.eye(3, dtype=np.float64),
            t=np.zeros(3, dtype=np.float64),
        )

        rms_before = _compute_reprojection_rms(perturbed, corrs)

        # Refine with tilt enabled
        refined = refine_calibration(perturbed, corrs, normal_fixed=False)

        # Reference camera R should have changed from identity
        ref_R = refined.cameras["cam0"].extrinsics.R
        assert not np.allclose(ref_R, np.eye(3), atol=1e-4), (
            "Reference camera R should have changed from identity with normal_fixed=False"
        )

        # RMS should decrease
        rms_after = _compute_reprojection_rms(refined, corrs)
        assert rms_after < rms_before, (
            f"RMS should decrease with tilt refinement: "
            f"before={rms_before:.4f}, after={rms_after:.4f}"
        )


# ---------------------------------------------------------------------------
# Tests: Robust Loss Functions (Phase 14)
# ---------------------------------------------------------------------------


class TestRobustLoss:
    """Tests for robust loss functions (Huber/Cauchy) vs linear loss."""

    @pytest.fixture
    def contaminated_correspondences(
        self, calibration_result, synthetic_correspondences
    ):
        """Add outlier correspondences with 50-100px shifted observations."""
        rng = np.random.RandomState(999)
        outliers = []
        for i in range(5):
            # Pick a clean correspondence and add large pixel shifts
            base = synthetic_correspondences[i]
            shifted_obs = {}
            for cam_name, pixel in base.observations.items():
                shift = rng.uniform(50, 100, size=2) * rng.choice([-1, 1], size=2)
                shifted_obs[cam_name] = pixel + shift
            outliers.append(
                PointCorrespondence(
                    point_3d=base.point_3d.copy(),
                    observations=shifted_obs,
                    weight=1.0,
                )
            )
        return synthetic_correspondences + outliers

    @pytest.mark.slow
    def test_huber_reduces_outlier_influence(
        self, perturbed_result, synthetic_correspondences, contaminated_correspondences
    ):
        """Huber loss gives lower clean-subset RMS than linear on contaminated data."""
        refined_linear = refine_calibration(
            perturbed_result, contaminated_correspondences, loss="linear"
        )
        refined_huber = refine_calibration(
            perturbed_result,
            contaminated_correspondences,
            loss="huber",
            f_scale=2.0,
        )

        # Evaluate on CLEAN correspondences only
        rms_linear = _compute_reprojection_rms(
            refined_linear, synthetic_correspondences
        )
        rms_huber = _compute_reprojection_rms(refined_huber, synthetic_correspondences)

        assert rms_huber < rms_linear, (
            f"Huber should have lower clean-subset RMS: "
            f"huber={rms_huber:.4f}, linear={rms_linear:.4f}"
        )

    @pytest.mark.slow
    def test_cauchy_reduces_outlier_influence(
        self, perturbed_result, synthetic_correspondences, contaminated_correspondences
    ):
        """Cauchy loss gives lower clean-subset RMS than linear on contaminated data."""
        refined_linear = refine_calibration(
            perturbed_result, contaminated_correspondences, loss="linear"
        )
        refined_cauchy = refine_calibration(
            perturbed_result,
            contaminated_correspondences,
            loss="cauchy",
            f_scale=2.0,
        )

        rms_linear = _compute_reprojection_rms(
            refined_linear, synthetic_correspondences
        )
        rms_cauchy = _compute_reprojection_rms(
            refined_cauchy, synthetic_correspondences
        )

        assert rms_cauchy < rms_linear, (
            f"Cauchy should have lower clean-subset RMS: "
            f"cauchy={rms_cauchy:.4f}, linear={rms_linear:.4f}"
        )

    @pytest.mark.slow
    def test_linear_loss_matches_default(
        self, perturbed_result, synthetic_correspondences
    ):
        """loss='linear' produces identical results to default (no loss arg)."""
        refined_default = refine_calibration(
            perturbed_result, synthetic_correspondences
        )
        refined_linear = refine_calibration(
            perturbed_result, synthetic_correspondences, loss="linear"
        )

        rms_default = _compute_reprojection_rms(
            refined_default, synthetic_correspondences
        )
        rms_linear = _compute_reprojection_rms(
            refined_linear, synthetic_correspondences
        )

        # Should be identical (or extremely close due to floating point)
        assert abs(rms_default - rms_linear) < 1e-6, (
            f"loss='linear' should match default: "
            f"default={rms_default:.6f}, linear={rms_linear:.6f}"
        )

        # Check extrinsics are also identical
        for cam_name in sorted(perturbed_result.cameras.keys()):
            np.testing.assert_allclose(
                refined_default.cameras[cam_name].extrinsics.t,
                refined_linear.cameras[cam_name].extrinsics.t,
                atol=1e-8,
                err_msg=f"{cam_name} extrinsics differ between default and loss='linear'",
            )

    @pytest.mark.slow
    def test_combined_intrinsics_and_robust_loss(self, calibration_result):
        """Combined refine_intrinsics=True and loss='huber' works without error."""
        # Perturb intrinsics slightly
        perturbed = copy.deepcopy(calibration_result)
        perturbed.cameras["cam1"].intrinsics.K[0, 0] += 10.0  # fx +10
        perturbed.cameras["cam1"].extrinsics.t = perturbed.cameras[
            "cam1"
        ].extrinsics.t + np.array([0.003, 0.0, 0.0], dtype=np.float64)
        # Perturb water_z
        for cam_name in perturbed.cameras:
            perturbed.cameras[cam_name].water_z += 0.005

        # Generate correspondences from original
        corrs = _generate_correspondences_from_result(
            calibration_result, n_points=30, noise_sigma=0.3, seed=300
        )

        rms_before = _compute_reprojection_rms(perturbed, corrs)

        refined = refine_calibration(
            perturbed,
            corrs,
            refine_intrinsics=True,
            loss="huber",
            f_scale=2.0,
        )

        assert isinstance(refined, CalibrationResult)

        # Intrinsics should have changed
        cam1_fx_before = perturbed.cameras["cam1"].intrinsics.K[0, 0]
        cam1_fx_after = refined.cameras["cam1"].intrinsics.K[0, 0]
        assert cam1_fx_before != cam1_fx_after, (
            "cam1 fx should change with refine_intrinsics=True"
        )

        # RMS should decrease
        rms_after = _compute_reprojection_rms(refined, corrs)
        assert rms_after < rms_before, (
            f"RMS should decrease with combined extensions: "
            f"before={rms_before:.4f}, after={rms_after:.4f}"
        )
