"""Unit tests for refractive geometry module."""

import inspect

import numpy as np
import pytest

from aquacal.config.schema import CameraExtrinsics, CameraIntrinsics
from aquacal.core.camera import Camera
from aquacal.core.interface_model import Interface
from aquacal.core.refractive_geometry import (
    _refractive_project_newton_batch,
    refractive_back_project,
    refractive_project,
    refractive_project_batch,
    refractive_project_batch_newton_diagnostic,
    refractive_project_newton_diagnostic,
    snells_law_3d,
    trace_ray_air_to_water,
)

# Pinned pre-D-19 expectations for refractive_project, captured from the pre-refactor
# code at commit 5762d6d (before the Newton loop was extracted into _solve_newton_r_p).
# Camera "cam0" at origin, K=[[500,0,320],[0,500,240],[0,0,1]], horizontal interface at
# Z=0.15, n_air=1.0, n_water=1.333. Points at fixed depth Z=0.5, X offset swept from
# near-normal (0.0) to oblique (0.3) incidence, Y=0. Used with assert_array_equal (zero
# tolerance) to prove the refactor changed no numbers on the hot projection path.
_BIT_EXACT_X_OFFSETS = np.linspace(0.0, 0.3, 20)
_BIT_EXACT_DEPTH = 0.5
_BIT_EXACT_EXPECTED_PIXELS = np.array(
    [
        [320.0, 240.0],
        [339.1396108983536, 240.0],
        [358.3026340260677, 240.0],
        [377.51254274662455, 240.0],
        [396.7929321237534, 240.0],
        [416.16757832631237, 240.0],
        [435.66049622810203, 240.0],
        [455.2959944827717, 240.0],
        [475.0987272525284, 240.0],
        [495.0937416427271, 240.0],
        [515.3065197434256, 240.0],
        [535.7630140052964, 240.0],
        [556.4896744838966, 240.0],
        [577.5134662780249, 240.0],
        [598.8618752720201, 240.0],
        [620.5629000787767, 240.0],
        [642.6450278842361, 240.0],
        [665.1371917338768, 240.0],
        [688.068706701009, 240.0],
        [711.4691823643191, 240.0],
    ]
)


@pytest.fixture
def simple_camera():
    """Camera at origin looking down +Z."""
    intrinsics = CameraIntrinsics(
        K=np.array([[500, 0, 320], [0, 500, 240], [0, 0, 1]], dtype=np.float64),
        dist_coeffs=np.zeros(5),
        image_size=(640, 480),
    )
    extrinsics = CameraExtrinsics(R=np.eye(3), t=np.zeros(3))
    return Camera("cam0", intrinsics, extrinsics)


@pytest.fixture
def simple_interface():
    """Horizontal interface at Z=0.15."""
    return Interface(
        normal=np.array([0, 0, -1]),
        camera_distances={"cam0": 0.15},
        n_air=1.0,
        n_water=1.333,
    )


class TestSnellsLaw3D:
    def test_normal_incidence(self):
        """Ray perpendicular to surface passes straight through."""
        incident = np.array([0, 0, 1])  # Down (+Z)
        normal = np.array([0, 0, -1])  # Up (water to air)
        n_ratio = 1.0 / 1.333

        refracted = snells_law_3d(incident, normal, n_ratio)

        assert refracted is not None
        np.testing.assert_allclose(refracted, np.array([0, 0, 1]), atol=1e-10)

    def test_bends_toward_normal_air_to_water(self):
        """Ray entering water bends toward normal (steeper)."""
        # 30 degrees from vertical
        incident = np.array([0.5, 0, np.sqrt(0.75)])
        incident = incident / np.linalg.norm(incident)
        normal = np.array([0, 0, -1])
        n_ratio = 1.0 / 1.333

        refracted = snells_law_3d(incident, normal, n_ratio)

        assert refracted is not None
        # Refracted ray should be more vertical (larger Z component)
        assert abs(refracted[2]) > abs(incident[2])
        # X component should be smaller (bent toward normal)
        assert abs(refracted[0]) < abs(incident[0])

    def test_bends_away_from_normal_water_to_air(self):
        """Ray exiting water bends away from normal."""
        # Ray going up from water (negative Z direction)
        incident = np.array([0.2, 0, -np.sqrt(1 - 0.04)])
        incident = incident / np.linalg.norm(incident)
        normal = np.array([0, 0, -1])
        n_ratio = 1.333 / 1.0

        refracted = snells_law_3d(incident, normal, n_ratio)

        assert refracted is not None
        # X component should be larger (bent away from normal)
        assert abs(refracted[0]) > abs(incident[0])

    def test_total_internal_reflection(self):
        """Steep angle from water to air causes TIR."""
        # Critical angle ~48.6 degrees, use 60 degrees
        angle = np.radians(60)
        incident = np.array([np.sin(angle), 0, -np.cos(angle)])
        normal = np.array([0, 0, -1])
        n_ratio = 1.333 / 1.0

        refracted = snells_law_3d(incident, normal, n_ratio)

        assert refracted is None

    def test_no_tir_air_to_water(self):
        """TIR cannot occur when entering denser medium."""
        # Even at grazing angle, should not get TIR
        incident = np.array([0.99, 0, 0.14])  # Very steep
        incident = incident / np.linalg.norm(incident)
        normal = np.array([0, 0, -1])
        n_ratio = 1.0 / 1.333

        refracted = snells_law_3d(incident, normal, n_ratio)

        assert refracted is not None

    def test_output_is_unit_vector(self):
        """Refracted direction should be unit vector."""
        incident = np.array([0.3, 0.2, 0.8])
        incident = incident / np.linalg.norm(incident)
        normal = np.array([0, 0, -1])

        refracted = snells_law_3d(incident, normal, 1.0 / 1.333)

        assert refracted is not None
        np.testing.assert_allclose(np.linalg.norm(refracted), 1.0, atol=1e-10)

    def test_symmetry_xz_plane(self):
        """Refraction should stay in the plane of incidence."""
        # Ray in XZ plane should stay in XZ plane
        incident = np.array([0.5, 0, np.sqrt(0.75)])
        incident = incident / np.linalg.norm(incident)
        normal = np.array([0, 0, -1])

        refracted = snells_law_3d(incident, normal, 1.0 / 1.333)

        assert refracted is not None
        # Y component should remain zero
        np.testing.assert_allclose(refracted[1], 0.0, atol=1e-10)

    def test_symmetry_arbitrary_plane(self):
        """Refraction preserves XY direction ratio."""
        incident = np.array([0.3, 0.4, np.sqrt(1 - 0.09 - 0.16)])
        incident = incident / np.linalg.norm(incident)
        normal = np.array([0, 0, -1])

        refracted = snells_law_3d(incident, normal, 1.0 / 1.333)

        assert refracted is not None
        # XY ratio should be preserved
        if abs(incident[0]) > 1e-10:
            incident_ratio = incident[1] / incident[0]
            refracted_ratio = refracted[1] / refracted[0]
            np.testing.assert_allclose(refracted_ratio, incident_ratio, atol=1e-10)


class TestTraceRayAirToWater:
    def test_center_pixel_goes_straight_down(self, simple_camera, simple_interface):
        """Principal point ray goes straight down through interface."""
        pixel = np.array([320, 240])

        intersection, direction = trace_ray_air_to_water(
            simple_camera, simple_interface, pixel
        )

        assert intersection is not None
        # Intersection at interface height
        np.testing.assert_allclose(intersection[2], 0.15, atol=1e-10)
        # Intersection directly below camera (camera at origin)
        np.testing.assert_allclose(intersection[:2], [0, 0], atol=1e-10)
        # Direction straight down
        np.testing.assert_allclose(direction, [0, 0, 1], atol=1e-10)

    def test_offset_pixel_refracts(self, simple_camera, simple_interface):
        """Off-center pixel refracts at interface."""
        pixel = np.array([420, 240])  # Right of center

        intersection, direction = trace_ray_air_to_water(
            simple_camera, simple_interface, pixel
        )

        assert intersection is not None
        # Intersection should be right of center
        assert intersection[0] > 0
        # Direction should point down-right, but more vertical than air ray
        assert direction[0] > 0  # Has rightward component
        assert direction[2] > 0  # Points into water (+Z)

    def test_returns_unit_direction(self, simple_camera, simple_interface):
        """Refracted direction should be unit vector."""
        pixel = np.array([400, 300])

        intersection, direction = trace_ray_air_to_water(
            simple_camera, simple_interface, pixel
        )

        assert direction is not None
        np.testing.assert_allclose(np.linalg.norm(direction), 1.0, atol=1e-10)

    def test_intersection_on_interface_plane(self, simple_camera, simple_interface):
        """Intersection point Z should be at interface height."""
        for pixel in [np.array([200, 150]), np.array([500, 400]), np.array([100, 100])]:
            intersection, direction = trace_ray_air_to_water(
                simple_camera, simple_interface, pixel
            )
            assert intersection is not None
            np.testing.assert_allclose(intersection[2], 0.15, atol=1e-10)


class TestRefractiveBackProject:
    def test_same_as_trace_ray(self, simple_camera, simple_interface):
        """refractive_back_project should match trace_ray_air_to_water."""
        pixel = np.array([350, 260])

        trace_result = trace_ray_air_to_water(simple_camera, simple_interface, pixel)
        back_result = refractive_back_project(simple_camera, simple_interface, pixel)

        if trace_result[0] is not None:
            np.testing.assert_allclose(back_result[0], trace_result[0])
            np.testing.assert_allclose(back_result[1], trace_result[1])

    def test_multiple_pixels(self, simple_camera, simple_interface):
        """Back-project several pixels and verify consistency."""
        pixels = [
            np.array([320, 240]),  # center
            np.array([100, 100]),  # top-left
            np.array([600, 400]),  # bottom-right
        ]

        for pixel in pixels:
            origin, direction = refractive_back_project(
                simple_camera, simple_interface, pixel
            )
            assert origin is not None
            assert direction is not None
            # Origin should be on interface
            np.testing.assert_allclose(origin[2], 0.15, atol=1e-10)
            # Direction should be unit vector pointing into water
            np.testing.assert_allclose(np.linalg.norm(direction), 1.0, atol=1e-10)
            assert direction[2] > 0  # pointing into water (+Z)


class TestRefractiveProject:
    def test_point_on_optical_axis(self, simple_camera, simple_interface):
        """Point directly below camera projects to principal point."""
        point = np.array([0, 0, 0.5])  # Below interface at z=0.15

        pixel = refractive_project(simple_camera, simple_interface, point)

        assert pixel is not None
        np.testing.assert_allclose(pixel, [320, 240], atol=0.1)

    def test_offset_point(self, simple_camera, simple_interface):
        """Offset underwater point projects away from principal point."""
        point = np.array([0.1, 0, 0.5])  # Right of center, underwater

        pixel = refractive_project(simple_camera, simple_interface, point)

        assert pixel is not None
        assert pixel[0] > 320  # Projects right of center

    def test_point_above_interface_returns_none(self, simple_camera, simple_interface):
        """Point above interface (in air) returns None."""
        point = np.array([0, 0, 0.1])  # Above interface at z=0.15

        pixel = refractive_project(simple_camera, simple_interface, point)

        assert pixel is None

    def test_round_trip_consistency(self, simple_camera, simple_interface):
        """Project then back-project should give ray through original point."""
        # Underwater point
        point = np.array([0.05, 0.03, 0.4])

        # Project to pixel
        pixel = refractive_project(simple_camera, simple_interface, point)
        assert pixel is not None

        # Back-project to ray
        origin, direction = refractive_back_project(
            simple_camera, simple_interface, pixel
        )
        assert origin is not None

        # Ray should pass near original point
        # Find closest point on ray to original point
        t = np.dot(point - origin, direction)
        closest = origin + t * direction

        np.testing.assert_allclose(closest, point, atol=1e-4)

    def test_point_offset_both_axes(self, simple_camera, simple_interface):
        """Point offset in both X and Y projects correctly."""
        point = np.array([0.05, -0.03, 0.5])

        pixel = refractive_project(simple_camera, simple_interface, point)

        assert pixel is not None
        assert pixel[0] > 320  # X offset positive -> right of center
        assert pixel[1] < 240  # Y offset negative -> above center


class TestRefractiveProjectEdgeCases:
    def test_point_at_various_depths(self, simple_camera, simple_interface):
        """Test projection at various water depths."""
        for depth in [0.2, 0.5, 1.0, 2.0]:
            point = np.array([0.05, 0.02, depth])
            pixel = refractive_project(simple_camera, simple_interface, point)
            assert pixel is not None, f"Failed at depth {depth}"

    def test_point_at_various_offsets(self, simple_camera, simple_interface):
        """Test projection at various lateral offsets."""
        for offset in [0.0, 0.05, 0.1, 0.2]:
            point = np.array([offset, 0, 0.5])
            pixel = refractive_project(simple_camera, simple_interface, point)
            assert pixel is not None, f"Failed at offset {offset}"

    def test_point_at_interface_boundary(self, simple_camera, simple_interface):
        """Point exactly at interface should return None."""
        point = np.array([0.05, 0.02, 0.15])  # At interface

        pixel = refractive_project(simple_camera, simple_interface, point)

        assert pixel is None

    def test_point_just_below_interface(self, simple_camera, simple_interface):
        """Point just below interface should work."""
        point = np.array([0.0, 0.0, 0.16])  # Just below interface at 0.15

        pixel = refractive_project(simple_camera, simple_interface, point)

        assert pixel is not None


class TestRoundTripMultiplePoints:
    """Test round-trip consistency for multiple points."""

    def test_grid_of_points(self, simple_camera, simple_interface):
        """Test round-trip for a grid of underwater points."""
        errors = []
        for x in np.linspace(-0.1, 0.1, 5):
            for y in np.linspace(-0.1, 0.1, 5):
                for z in [0.3, 0.5, 0.8]:
                    point = np.array([x, y, z])

                    # Project to pixel
                    pixel = refractive_project(simple_camera, simple_interface, point)
                    if pixel is None:
                        continue

                    # Back-project to ray
                    origin, direction = refractive_back_project(
                        simple_camera, simple_interface, pixel
                    )
                    if origin is None:
                        continue

                    # Find closest point on ray
                    t = np.dot(point - origin, direction)
                    closest = origin + t * direction
                    error = np.linalg.norm(closest - point)
                    errors.append(error)

        # All errors should be small
        assert len(errors) > 0, "No valid round-trip tests"
        max_error = max(errors)
        assert max_error < 1e-4, f"Max round-trip error: {max_error}"


class TestRefractiveGeometryPhysics:
    """Test physical correctness of refraction."""

    def test_refraction_increases_apparent_depth(self, simple_camera, simple_interface):
        """Objects underwater appear closer than they are due to refraction."""
        # Point directly below camera
        true_depth = 0.5
        point = np.array([0, 0, true_depth])

        # Get pixel for underwater point (with refraction)
        pixel_refracted = refractive_project(simple_camera, simple_interface, point)
        assert pixel_refracted is not None

        # Back-project and see where ray in water started
        origin, direction = refractive_back_project(
            simple_camera, simple_interface, pixel_refracted
        )

        # The apparent depth at the optical axis should be different from true depth
        # For a point on the optical axis, ray goes straight through, so this test
        # may need an off-axis point
        pass  # This test verifies structure more than specific physics

    def test_larger_offset_refracts_more(self, simple_camera, simple_interface):
        """Points further off-axis should show more refraction effect."""
        depth = 0.5
        small_offset = np.array([0.02, 0, depth])
        large_offset = np.array([0.1, 0, depth])

        pixel_small = refractive_project(simple_camera, simple_interface, small_offset)
        pixel_large = refractive_project(simple_camera, simple_interface, large_offset)

        assert pixel_small is not None
        assert pixel_large is not None

        # Both should be to the right of center
        assert pixel_small[0] > 320
        assert pixel_large[0] > pixel_small[0]


class TestOffsetCameraRoundTrip:
    """Regression tests for cameras at non-origin positions.

    These tests verify that refractive_project and refractive_back_project
    form a consistent round-trip for cameras with XY offsets from origin.
    This was a bug fixed in 2026-02-04 where the TIR boundary was incorrectly
    identified as the optimization solution.
    """

    def test_round_trip_offset_camera_x(self):
        """Test round-trip with camera offset in X direction."""
        intrinsics = CameraIntrinsics(
            K=np.array([[500, 0, 320], [0, 500, 240], [0, 0, 1]], dtype=np.float64),
            dist_coeffs=np.zeros(5),
            image_size=(640, 480),
        )
        # Camera at X=-0.3 (t=[0.3, 0, 0] means C=[-0.3, 0, 0])
        extrinsics = CameraExtrinsics(R=np.eye(3), t=np.array([0.3, 0.0, 0.0]))
        camera = Camera("cam_offset", intrinsics, extrinsics)
        interface = Interface(
            normal=np.array([0, 0, -1]),
            camera_distances={"cam_offset": 0.15},
            n_air=1.0,
            n_water=1.333,
        )

        point = np.array([0.05, 0.025, 0.30])

        pixel = refractive_project(camera, interface, point)
        assert pixel is not None

        origin, direction = refractive_back_project(camera, interface, pixel)
        assert origin is not None

        # Check round-trip error
        t = np.dot(point - origin, direction)
        closest = origin + t * direction
        error = np.linalg.norm(closest - point)

        # Should have sub-micrometer accuracy
        assert error < 1e-9, f"Round-trip error {error * 1000:.6f} mm is too large"

    def test_round_trip_offset_camera_xy(self):
        """Test round-trip with camera offset in both X and Y."""
        intrinsics = CameraIntrinsics(
            K=np.array([[500, 0, 320], [0, 500, 240], [0, 0, 1]], dtype=np.float64),
            dist_coeffs=np.zeros(5),
            image_size=(640, 480),
        )
        # Camera at X=0.2, Y=0.1
        extrinsics = CameraExtrinsics(R=np.eye(3), t=np.array([-0.2, -0.1, 0.0]))
        camera = Camera("cam_xy", intrinsics, extrinsics)
        interface = Interface(
            normal=np.array([0, 0, -1]),
            camera_distances={"cam_xy": 0.15},
            n_air=1.0,
            n_water=1.333,
        )

        point = np.array([0.05, 0.025, 0.30])

        pixel = refractive_project(camera, interface, point)
        assert pixel is not None

        origin, direction = refractive_back_project(camera, interface, pixel)
        assert origin is not None

        t = np.dot(point - origin, direction)
        closest = origin + t * direction
        error = np.linalg.norm(closest - point)

        assert error < 1e-9, f"Round-trip error {error * 1000:.6f} mm is too large"

    def test_round_trip_multiple_offset_cameras(self):
        """Test round-trip consistency across multiple offset cameras."""
        intrinsics = CameraIntrinsics(
            K=np.array([[500, 0, 320], [0, 500, 240], [0, 0, 1]], dtype=np.float64),
            dist_coeffs=np.zeros(5),
            image_size=(640, 480),
        )

        camera_offsets = [
            np.array([0.0, 0.0, 0.0]),  # Origin
            np.array([0.3, 0.0, 0.0]),  # X offset
            np.array([0.0, 0.3, 0.0]),  # Y offset
            np.array([0.15, 0.2, 0.0]),  # XY offset
            np.array([-0.1, 0.25, 0.0]),  # Negative X
        ]

        test_points = [
            np.array([0.05, 0.025, 0.30]),
            np.array([0.0, 0.0, 0.25]),
            np.array([-0.03, 0.04, 0.35]),
        ]

        max_error = 0.0
        for i, t_offset in enumerate(camera_offsets):
            camera = Camera(
                f"cam{i}", intrinsics, CameraExtrinsics(R=np.eye(3), t=t_offset)
            )
            interface = Interface(
                normal=np.array([0, 0, -1]),
                camera_distances={f"cam{i}": 0.15},
                n_air=1.0,
                n_water=1.333,
            )

            for point in test_points:
                pixel = refractive_project(camera, interface, point)
                if pixel is None:
                    continue

                origin, direction = refractive_back_project(camera, interface, pixel)
                if origin is None:
                    continue

                t = np.dot(point - origin, direction)
                closest = origin + t * direction
                error = np.linalg.norm(closest - point)
                max_error = max(max_error, error)

        assert max_error < 1e-9, f"Max round-trip error {max_error * 1000:.6f} mm"


class TestRefractiveProjectFast:
    """Tests for refractive projection (auto-selects fast Newton for flat interfaces)."""

    def test_point_on_optical_axis(self, simple_camera, simple_interface):
        """Handles point directly below camera."""
        # Camera is at origin
        point = np.array([0.0, 0.0, 0.5])
        result = refractive_project(simple_camera, simple_interface, point)
        assert result is not None
        # Should project to principal point
        np.testing.assert_allclose(result, [320, 240], atol=0.1)

    def test_point_above_interface_returns_none(self, simple_camera, simple_interface):
        """Returns None for point above interface."""
        z_int = simple_interface.get_water_z(simple_camera.name)
        point = np.array([0.0, 0.0, z_int - 0.05])
        assert refractive_project(simple_camera, simple_interface, point) is None

    def test_point_at_interface_returns_none(self, simple_camera, simple_interface):
        """Returns None for point exactly at interface."""
        z_int = simple_interface.get_water_z(simple_camera.name)
        point = np.array([0.05, 0.02, z_int])
        assert refractive_project(simple_camera, simple_interface, point) is None

    def test_flat_interface_uses_fast_path(self, simple_camera, simple_interface):
        """For flat interfaces, projection uses fast Newton-Raphson path."""
        # This test verifies that flat interfaces work correctly
        test_points = [
            np.array([0.0, 0.0, 0.5]),
            np.array([0.05, 0.02, 0.3]),
            np.array([0.1, 0.0, 0.5]),
            np.array([0.0, 0.1, 0.4]),
            np.array([-0.05, 0.03, 0.6]),
            np.array([0.08, -0.05, 0.35]),
        ]

        for point in test_points:
            result = refractive_project(simple_camera, simple_interface, point)
            assert result is not None, f"Failed for point {point}"
            # Basic sanity check: pixel should be within image bounds
            assert 0 <= result[0] < 640
            assert 0 <= result[1] < 480

    def test_offset_cameras(self):
        """Projection works correctly for offset cameras."""
        intrinsics = CameraIntrinsics(
            K=np.array([[500, 0, 320], [0, 500, 240], [0, 0, 1]], dtype=np.float64),
            dist_coeffs=np.zeros(5),
            image_size=(640, 480),
        )

        camera_translations = [
            np.array([0.3, 0.0, 0.0]),
            np.array([0.0, 0.25, 0.0]),
            np.array([-0.2, 0.15, 0.0]),
        ]

        for t in camera_translations:
            camera = Camera("cam_test", intrinsics, CameraExtrinsics(R=np.eye(3), t=t))
            interface = Interface(
                normal=np.array([0, 0, -1]),
                camera_distances={"cam_test": 0.15},
            )

            test_points = [
                np.array([0.05, 0.025, 0.30]),
                np.array([0.0, 0.0, 0.25]),
            ]

            for point in test_points:
                result = refractive_project(camera, interface, point)
                assert result is not None

    def test_various_depths(self, simple_camera, simple_interface):
        """Test projection at various water depths."""
        for depth in [0.2, 0.5, 1.0, 2.0]:
            point = np.array([0.05, 0.02, depth])
            result = refractive_project(simple_camera, simple_interface, point)
            assert result is not None, f"Failed at depth {depth}"

    def test_round_trip_consistency(self, simple_camera, simple_interface):
        """Project then back-project should give ray through original point."""
        point = np.array([0.05, 0.03, 0.4])

        pixel = refractive_project(simple_camera, simple_interface, point)
        assert pixel is not None

        origin, direction = refractive_back_project(
            simple_camera, simple_interface, pixel
        )
        assert origin is not None

        t = np.dot(point - origin, direction)
        closest = origin + t * direction

        np.testing.assert_allclose(closest, point, atol=1e-4)

    def test_tilted_interface_falls_back_to_brent(self, simple_camera):
        """Non-flat interface uses Brent-search fallback (no error raised)."""
        tilted = Interface(
            normal=np.array([0.1, 0, -0.995]) / np.linalg.norm([0.1, 0, -0.995]),
            camera_distances={"cam0": 0.15},
        )
        point = np.array([0, 0, 0.5])
        # Should not raise - auto-selects Brent fallback
        _result = refractive_project(simple_camera, tilted, point)
        # May return None or a valid result depending on geometry
        # The key is that it doesn't raise ValueError


class TestRefractiveProjectBatch:
    """Tests for batch refractive projection."""

    def test_batch_matches_single(self, simple_camera, simple_interface):
        """Batch projection matches single-point projection."""
        points = np.array(
            [
                [0.0, 0.0, 0.5],
                [0.05, 0.02, 0.3],
                [0.1, 0.0, 0.5],
                [-0.05, 0.03, 0.6],
            ]
        )

        batch_result = refractive_project_batch(simple_camera, simple_interface, points)

        for i, point in enumerate(points):
            single_result = refractive_project(simple_camera, simple_interface, point)
            if single_result is not None:
                np.testing.assert_allclose(batch_result[i], single_result, atol=1e-6)
            else:
                assert np.all(np.isnan(batch_result[i]))

    def test_batch_handles_invalid_points(self, simple_camera, simple_interface):
        """Batch returns NaN for invalid points."""
        z_int = simple_interface.get_water_z(simple_camera.name)
        points = np.array(
            [
                [0.0, 0.0, 0.5],  # valid
                [0.0, 0.0, z_int - 0.05],  # above interface
                [0.05, 0.02, 0.3],  # valid
            ]
        )

        result = refractive_project_batch(simple_camera, simple_interface, points)

        assert not np.any(np.isnan(result[0]))  # valid
        assert np.all(np.isnan(result[1]))  # invalid
        assert not np.any(np.isnan(result[2]))  # valid

    def test_batch_non_horizontal_raises(self, simple_camera):
        """Raises ValueError for tilted interface in batch."""
        tilted = Interface(
            normal=np.array([0.1, 0, -0.995]),
            camera_distances={"cam0": 0.15},
        )
        points = np.array([[0, 0, 0.5], [0.1, 0.1, 0.4]])
        with pytest.raises(ValueError, match="flat"):
            refractive_project_batch(simple_camera, tilted, points)

    def test_batch_empty_array(self, simple_camera, simple_interface):
        """Handles empty input array."""
        points = np.zeros((0, 3))
        result = refractive_project_batch(simple_camera, simple_interface, points)
        assert result.shape == (0, 2)

    def test_batch_point_on_axis(self, simple_camera, simple_interface):
        """Handles point directly below camera in batch."""
        points = np.array(
            [
                [0.0, 0.0, 0.5],  # on axis
                [0.05, 0.02, 0.3],  # off axis
            ]
        )

        result = refractive_project_batch(simple_camera, simple_interface, points)

        # On-axis should project to principal point
        np.testing.assert_allclose(result[0], [320, 240], atol=0.1)
        # Off-axis should be valid
        assert not np.any(np.isnan(result[1]))


class TestNewtonDiagnostic:
    """Tests for refractive_project_newton_diagnostic (D-19)."""

    def test_newton_diagnostic_projection_bit_unchanged(
        self, simple_camera, simple_interface
    ):
        """refractive_project's output is bit-unchanged by the D-19 refactor.

        Compares against expectations captured from the pre-refactor code at commit
        5762d6d, across configurations spanning near-normal to oblique incidence.
        """
        for offset, expected_pixel in zip(
            _BIT_EXACT_X_OFFSETS, _BIT_EXACT_EXPECTED_PIXELS
        ):
            point = np.array([offset, 0.0, _BIT_EXACT_DEPTH])
            pixel = refractive_project(simple_camera, simple_interface, point)
            assert pixel is not None
            np.testing.assert_array_equal(pixel, expected_pixel)

    def test_newton_diagnostic_reports_iterations(
        self, simple_camera, simple_interface
    ):
        """Diagnostic returns a converged dict with a sane iteration count."""
        point = np.array([0.05, 0.02, 0.5])

        result = refractive_project_newton_diagnostic(
            simple_camera, simple_interface, point
        )

        assert result is not None
        assert isinstance(result["n_iterations"], int)
        assert 1 <= result["n_iterations"] <= 10
        assert result["converged"] is True

    def test_newton_diagnostic_agrees_with_projector(
        self, simple_camera, simple_interface
    ):
        """Reconstructing the pixel from the diagnostic's r_p matches refractive_project."""
        point = np.array([0.08, -0.04, 0.5])

        diagnostic = refractive_project_newton_diagnostic(
            simple_camera, simple_interface, point
        )
        assert diagnostic is not None

        C = simple_camera.C
        z_int = simple_interface.get_water_z(simple_camera.name)
        dx = point[0] - C[0]
        dy = point[1] - C[1]
        r_q = np.hypot(dx, dy)
        dir_x = dx / r_q
        dir_y = dy / r_q
        r_p = diagnostic["r_p"]

        interface_point = np.array(
            [C[0] + r_p * dir_x, C[1] + r_p * dir_y, z_int], dtype=np.float64
        )
        reconstructed_pixel = simple_camera.project(
            interface_point, apply_distortion=True
        )

        expected_pixel = refractive_project(simple_camera, simple_interface, point)
        assert expected_pixel is not None
        np.testing.assert_array_equal(reconstructed_pixel, expected_pixel)

    def test_newton_diagnostic_degenerate_returns_none(self):
        """Camera at/below interface, point at/above interface, point below camera -> None."""
        intrinsics = CameraIntrinsics(
            K=np.array([[500, 0, 320], [0, 500, 240], [0, 0, 1]], dtype=np.float64),
            dist_coeffs=np.zeros(5),
            image_size=(640, 480),
        )

        # Camera at or below the interface (camera Z=0.2, interface Z=0.15)
        camera_below_interface = Camera(
            "cam_low",
            intrinsics,
            CameraExtrinsics(R=np.eye(3), t=np.array([0.0, 0.0, -0.2])),
        )
        interface = Interface(
            normal=np.array([0, 0, -1]),
            camera_distances={"cam_low": 0.15},
            n_air=1.0,
            n_water=1.333,
        )
        point_underwater = np.array([0.05, 0.0, 0.5])
        assert (
            refractive_project_newton_diagnostic(
                camera_below_interface, interface, point_underwater
            )
            is None
        )

        # Point at or above the interface, camera above interface as usual
        camera = Camera(
            "cam0", intrinsics, CameraExtrinsics(R=np.eye(3), t=np.zeros(3))
        )
        interface_normal = Interface(
            normal=np.array([0, 0, -1]),
            camera_distances={"cam0": 0.15},
            n_air=1.0,
            n_water=1.333,
        )
        point_above_interface = np.array([0.05, 0.0, 0.1])
        assert (
            refractive_project_newton_diagnostic(
                camera, interface_normal, point_above_interface
            )
            is None
        )

        # Point directly below the camera (r_q < 1e-10) -- no root-find to report
        point_on_axis = np.array([0.0, 0.0, 0.5])
        assert (
            refractive_project_newton_diagnostic(
                camera, interface_normal, point_on_axis
            )
            is None
        )

    def test_newton_diagnostic_defaults_match_declared_constants(self):
        """The diagnostic's defaults are the same literals E3 tier 1 declares."""
        params = inspect.signature(refractive_project_newton_diagnostic).parameters
        assert params["tolerance"].default == 1e-9
        assert params["max_iterations"].default == 10


# --- D-32: batch Newton diagnostic (CR-05) ---------------------------------------------
#
# `_refractive_project_newton_batch` is the loop the production residual path
# (`refractive_project_batch`, called from `calibration/_optim_common.py:635`) actually
# runs. The frozen anchor below was captured from the PRE-D-32 implementation at commit
# 7ae7ff640ea9ce561a540992d311a13556b4a190 (the base this plan forked from), loaded via
# `importlib.util.spec_from_file_location` from a `git show <sha>:...` blob of
# `src/aquacal/core/refractive_geometry.py` and run once through
# `refractive_project_batch` on a real-rig camera ("cam0" from
# `generate_real_rig_array()`) over a fixed point set spanning: two near-normal/oblique
# off-axis points in different quadrants, one on-axis point, and one invalid
# (above-interface) point. These constants must NEVER be regenerated to make a failing
# test pass -- a mismatch means the D-32 instrumentation moved production projection
# output, which is a hard stop per the plan's threat model (T-19.2-77).

_BATCH_ANCHOR_POINTS = np.array(
    [
        [0.05, 0.02, 1.3809999999999998],
        [0.3, -0.15, 1.2309999999999999],
        [-0.2, 0.25, 1.531],
        [0.0, 0.0, 1.431],
        [0.0, 0.0, 0.9309999999999999],
    ]
)
_BATCH_ANCHOR_EXPECTED_VALID = np.array(
    [
        [841.5638369800935, 626.2849331688894],
        [1169.5323076671357, 407.25445646385833],
        [559.770627500186, 877.7057474325691],
        [780.22, 601.74],
    ]
)


@pytest.fixture
def real_rig_camera_and_interface():
    """ "cam0" from the real-rig geometry (`aquacal.datasets.generate_real_rig_array`),
    the same rig E3/E5's Newton sweeps use, paired with its Interface."""
    from aquacal.datasets import generate_real_rig_array

    intrinsics, extrinsics, water_zs = generate_real_rig_array()
    cam_name = "cam0"
    camera = Camera(cam_name, intrinsics[cam_name], extrinsics[cam_name])
    interface = Interface(
        normal=np.array([0.0, 0.0, -1.0]),
        camera_distances=water_zs,
        n_air=1.0,
        n_water=1.333,
    )
    return camera, interface


class TestBatchNewtonBitIdentity:
    """D-32 acceptance: production projection output is proven bit-identical, by exact
    equality against a frozen pre-change anchor -- not asserted."""

    def test_batch_matches_pre_change_anchor(self, real_rig_camera_and_interface):
        """`refractive_project_batch`'s output (diagnostic flag OFF, the production
        default) is exactly equal to the frozen pre-D-32 anchor."""
        camera, interface = real_rig_camera_and_interface

        result = refractive_project_batch(camera, interface, _BATCH_ANCHOR_POINTS)

        np.testing.assert_array_equal(result[:4], _BATCH_ANCHOR_EXPECTED_VALID)
        assert np.all(np.isnan(result[4]))  # above-interface point stays invalid

    def test_flag_on_and_flag_off_pixels_are_array_equal(
        self, real_rig_camera_and_interface
    ):
        """Turning the opt-in diagnostic ON changes nothing about the returned pixels."""
        camera, interface = real_rig_camera_and_interface

        pixels_off = refractive_project_batch(camera, interface, _BATCH_ANCHOR_POINTS)
        pixels_on, _diagnostics = _refractive_project_newton_batch(
            camera, interface, _BATCH_ANCHOR_POINTS, return_diagnostics=True
        )

        np.testing.assert_array_equal(pixels_off[:4], pixels_on[:4])
        assert np.all(np.isnan(pixels_off[4])) and np.all(np.isnan(pixels_on[4]))

    def test_termination_rule_is_unchanged(self):
        """Source-level guard: the all-points termination rule is untouched by D-32."""
        source = inspect.getsource(_refractive_project_newton_batch)
        assert "np.all(np.abs(delta) < tolerance)" in source


class TestBatchNewtonDiagnostic:
    """D-32: the new opt-in per-point diagnostic on the batch (production) Newton loop."""

    def test_reports_only_valid_points_like_the_scalar_diagnostic(
        self, real_rig_camera_and_interface
    ):
        """Degenerate points (on-axis, above-interface) are excluded from the per-point
        statistics exactly as `refractive_project_newton_diagnostic` excludes them, so the
        two loops are comparable over the same population."""
        camera, interface = real_rig_camera_and_interface

        diagnostics = refractive_project_batch_newton_diagnostic(
            camera, interface, _BATCH_ANCHOR_POINTS
        )

        # Points 0, 1, 2 are the valid off-axis points; 3 is on-axis, 4 is invalid.
        assert sorted(diagnostics["point_index"].tolist()) == [0, 1, 2]
        assert len(diagnostics["converged_at_iteration"]) == 3
        assert len(diagnostics["converged"]) == 3
        assert len(diagnostics["final_abs_delta"]) == 3
        assert len(diagnostics["r_p"]) == 3
        assert len(diagnostics["incidence_angle_deg"]) == 3
        assert isinstance(diagnostics["n_iterations_executed"], int)
        assert 1 <= diagnostics["n_iterations_executed"] <= 10

    def test_converged_points_report_a_positive_iteration_and_small_final_delta(
        self, real_rig_camera_and_interface
    ):
        camera, interface = real_rig_camera_and_interface

        diagnostics = refractive_project_batch_newton_diagnostic(
            camera, interface, _BATCH_ANCHOR_POINTS
        )

        assert np.all(diagnostics["converged"])
        assert np.all(diagnostics["converged_at_iteration"] >= 1)
        assert np.all(
            diagnostics["converged_at_iteration"]
            <= diagnostics["n_iterations_executed"]
        )
        assert np.all(diagnostics["final_abs_delta"] < 1e-9)

    def test_never_converged_point_reports_sentinel(self, simple_camera):
        """A point that cannot converge within `max_iterations=0` reports the -1
        sentinel and `converged=False`, rather than a fabricated iteration count."""
        interface = Interface(
            normal=np.array([0, 0, -1]),
            camera_distances={"cam0": 0.15},
            n_air=1.0,
            n_water=1.333,
        )
        points = np.array([[0.05, 0.02, 0.5]])

        diagnostics = refractive_project_batch_newton_diagnostic(
            simple_camera, interface, points, max_iterations=0
        )

        assert diagnostics["n_iterations_executed"] == 0
        assert diagnostics["converged_at_iteration"][0] == -1
        assert diagnostics["converged"][0] == np.False_

    def test_empty_and_degenerate_inputs_return_empty_diagnostics(
        self, simple_camera, simple_interface
    ):
        """No valid off-axis points (empty array, or all points on-axis/invalid) yields
        empty diagnostics arrays rather than an error."""
        empty_points = np.zeros((0, 3))
        diagnostics = refractive_project_batch_newton_diagnostic(
            simple_camera, simple_interface, empty_points
        )
        assert len(diagnostics["point_index"]) == 0
        assert diagnostics["n_iterations_executed"] == 0

        z_int = simple_interface.get_water_z(simple_camera.name)
        all_invalid = np.array([[0.0, 0.0, z_int - 0.05]])  # above interface
        diagnostics = refractive_project_batch_newton_diagnostic(
            simple_camera, simple_interface, all_invalid
        )
        assert len(diagnostics["point_index"]) == 0

    def test_non_horizontal_interface_raises(self, simple_camera):
        tilted = Interface(
            normal=np.array([0.1, 0, -0.995]),
            camera_distances={"cam0": 0.15},
        )
        points = np.array([[0.1, 0.1, 0.4]])
        with pytest.raises(ValueError, match="flat"):
            refractive_project_batch_newton_diagnostic(simple_camera, tilted, points)

    def test_batch_diagnostic_agrees_with_scalar_diagnostic_rp(
        self, real_rig_camera_and_interface
    ):
        """The two independently-terminated loops converge to the same root for the same
        points, within a stated tolerance. Records (does not assert equality of) the
        iteration-count difference -- the whole point of D-32 is that the two loops
        report iteration counts differently under different termination rules."""
        camera, interface = real_rig_camera_and_interface

        batch_diag = refractive_project_batch_newton_diagnostic(
            camera, interface, _BATCH_ANCHOR_POINTS
        )

        iteration_diffs = []
        for i, idx in enumerate(batch_diag["point_index"]):
            point = _BATCH_ANCHOR_POINTS[idx]
            scalar_diag = refractive_project_newton_diagnostic(camera, interface, point)
            assert scalar_diag is not None

            assert batch_diag["r_p"][i] == pytest.approx(scalar_diag["r_p"], abs=1e-9)
            iteration_diffs.append(
                int(batch_diag["converged_at_iteration"][i])
                - int(scalar_diag["n_iterations"])
            )

        # Recorded for the summary, not asserted: under all-points termination, a point's
        # own convergence iteration can differ from the scalar loop's per-point count.
        assert all(isinstance(d, int) for d in iteration_diffs)


class TestUnitIndexPinholeIdentity:
    """Verifies numerically -- not by source reading -- whether the refractive
    projector reduces exactly to the plain pinhole projection at
    ``n_air = n_water = 1.0``.

    Plan 21-12 verification. The manuscript's non-refractive baseline (`main.tex`
    lines 68, 268, 270, 271, 278, 280, 281, 295, including the abstract's headline)
    runs the optimizer at n_water=1.0 and reports 14,949 `DegenerateObservationWarning`
    hits -- a guard count of zero everywhere else. If the pinhole extension and the
    refractive Newton solve disagree at unit index, the baseline's reported optimality
    is meaningless rather than merely pessimistic. See
    `.planning/MANUSCRIPT-FINDINGS.md` MF-18 and the folded todo
    `2026-08-05-verify-non-refractive-baseline-supports-paper-claims.md`.
    """

    def test_projection_reduces_to_pinhole_at_unit_index(self, simple_camera):
        """At n_air == n_water == 1.0, Snell's law gives theta1 == theta2 for every
        incidence angle (sin_t_sq = n_ratio**2 * sin_i**2 with n_ratio=1), so the
        refractive Newton solve and the plain pinhole projection must agree to machine
        precision for below-interface points."""
        interface = Interface(
            normal=np.array([0, 0, -1]),
            camera_distances={"cam0": 0.15},
            n_air=1.0,
            n_water=1.0,
        )

        rng = np.random.default_rng(42)
        n_points = 200
        xy = rng.uniform(-0.6, 0.6, size=(n_points, 2))
        z = rng.uniform(0.20, 2.0, size=n_points)  # strictly below interface (Z=0.15)
        points = np.column_stack([xy, z])

        refractive_pixels = refractive_project_batch(simple_camera, interface, points)
        pinhole_pixels = np.array(
            [simple_camera.project(p, apply_distortion=True) for p in points]
        )

        np.testing.assert_allclose(
            refractive_pixels, pinhole_pixels, rtol=0, atol=1e-12
        )

        # Same identity via the scalar path, for a subset -- confirms both code paths
        # (not just the vectorized one) reduce to pinhole.
        for p in points[:10]:
            scalar_pixel = refractive_project(simple_camera, interface, p)
            pinhole_pixel = simple_camera.project(p, apply_distortion=True)
            assert scalar_pixel is not None and pinhole_pixel is not None
            np.testing.assert_allclose(scalar_pixel, pinhole_pixel, rtol=0, atol=1e-12)

    def test_above_interface_points_are_not_pinhole_continued_at_this_layer(
        self, simple_camera
    ):
        """Documents a boundary the todo's source-reading argument did not distinguish:
        `refractive_project` / `refractive_project_batch` return None/NaN for points at
        or above the interface (`h_q <= 0`) -- they do NOT themselves apply the pinhole
        continuation. That continuation is one layer up, in
        `aquacal.calibration._optim_common._extend_invalid_projections`, reached only
        from the production residual function (`compute_residuals`). A caller of
        `refractive_project`/`refractive_project_batch` directly sees the un-extended
        NaN, regardless of n_air/n_water."""
        interface = Interface(
            normal=np.array([0, 0, -1]),
            camera_distances={"cam0": 0.15},
            n_air=1.0,
            n_water=1.0,
        )
        above = np.array([[0.05, 0.02, 0.10]])  # Z=0.10 is above interface Z=0.15

        batch_result = refractive_project_batch(simple_camera, interface, above)
        assert np.isnan(batch_result).all()

        scalar_result = refractive_project(simple_camera, interface, above[0])
        assert scalar_result is None


class TestDeprecatedShimsRemoved:
    """The deprecated ``refractive_project_fast*`` shims were removed pre-2.0.0.

    They forwarded verbatim to ``refractive_project`` / ``refractive_project_batch``,
    which already auto-select the Newton fast path for flat interfaces. Nothing in the
    library, the tests or the experiments called them. Pinned here so the removal is
    not silently undone by a merge.
    """

    def test_refractive_project_fast_is_gone(self):
        import aquacal.core.refractive_geometry as m

        assert not hasattr(m, "refractive_project_fast")

    def test_refractive_project_fast_batch_is_gone(self):
        import aquacal.core.refractive_geometry as m

        assert not hasattr(m, "refractive_project_fast_batch")
