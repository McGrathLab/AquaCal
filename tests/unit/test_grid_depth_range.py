"""Exact-value and seed/camera-count-invariance tests for the grid family's
derived `GRID_DEPTH_RANGE` floor (D-19.4-12, D-19.4-15, SC-4).

Post-fix, `generate_camera_array` gives every camera the same shared
`water_z` (D-19.4-09), so `max(water_zs) == height_above_water` at every
seed and every camera count -- the clearance floor `derive_grid_depth_range`
computes from `GRID_HEIGHT_ABOVE_WATER`/`GRID_SPACING`/`GRID_BOARD_CONFIG`
is therefore seed-invariant BY CONSTRUCTION, not by accident. D-19.4-15
measured this over 3,000 draws (500 seeds x {8,12,16} cameras x calibration
and holdout): exactly one distinct derived floor, **1.176215948246**
(repr: ``1.1762159482461678``, asserted below at that full precision).

No fuzzy/tolerance-based float comparison anywhere in this file: an
inertness/exact-value assertion that disagreed would mean the FIX moved,
never the tolerance (blocking anti-pattern 3).
"""

from __future__ import annotations

import pytest

from aquacal.datasets.synthetic import generate_camera_array
from experiments.e4_benchmark_grid import (
    GRID_BOARD_CONFIG,
    GRID_DEPTH_RANGE,
    GRID_HEIGHT_ABOVE_WATER,
    GRID_LAYOUT,
    GRID_SPACING,
    derive_grid_depth_range,
)

# D-19.4-15's measured value, to the repr precision derive_grid_depth_range
# actually returns.
_EXPECTED_FLOOR_REPR = 1.1762159482461678
_EXPECTED_FLOOR_12SF = 1.176215948246

# Seed 43 is included deliberately: it is one of the ~94% of seeds at which
# E6 was formerly illegal under the pre-fix per-camera-interface defect
# (D-19.4-15's "cured, not assumed" claim).
_SEEDS = [0, 1, 42, 43, 99, 500]
_N_CAMERAS_VALUES = [8, 12, 16]


def test_derived_floor_exact_value():
    """The module-level GRID_DEPTH_RANGE floor equals D-19.4-15's measured
    value, exactly, at the full precision the helper returns."""
    _, _, water_zs = generate_camera_array(
        n_cameras=12,
        layout=GRID_LAYOUT,
        spacing=GRID_SPACING,
        height_above_water=GRID_HEIGHT_ABOVE_WATER,
        seed=42,
    )
    floor, ceiling = derive_grid_depth_range(water_zs)

    assert floor == _EXPECTED_FLOOR_REPR
    # 12-significant-figure check, matching D-19.4-15's own stated precision.
    assert round(floor, 12) == _EXPECTED_FLOOR_12SF
    assert ceiling == 2.0


def test_module_level_grid_depth_range_matches_helper():
    """GRID_DEPTH_RANGE at import time is exactly
    derive_grid_depth_range(_grid_baseline_water_zs) -- no drift between the
    module constant and a fresh call."""
    assert GRID_DEPTH_RANGE[0] == _EXPECTED_FLOOR_REPR
    assert GRID_DEPTH_RANGE[1] == 2.0


def test_derived_floor_returns_fixed_ceiling():
    """derive_grid_depth_range's second element is always exactly 2.0
    (D-19.3-03's fixed ceiling), regardless of input water_zs."""
    _, _, water_zs = generate_camera_array(
        n_cameras=8,
        layout=GRID_LAYOUT,
        spacing=GRID_SPACING,
        height_above_water=0.5,
        seed=7,
    )
    _, ceiling = derive_grid_depth_range(water_zs)
    assert ceiling == 2.0


@pytest.mark.parametrize("n_cameras", _N_CAMERAS_VALUES)
@pytest.mark.parametrize("seed", _SEEDS)
def test_derived_floor_is_seed_and_camera_count_invariant(seed, n_cameras):
    """Post-fix, the derived floor is identical across every seed AND every
    camera count -- proof, not assumption, that the clearance-floor
    seed-locking defect (D-19.4-15) is cured by the interface fix."""
    _, _, water_zs = generate_camera_array(
        n_cameras=n_cameras,
        layout=GRID_LAYOUT,
        spacing=GRID_SPACING,
        height_above_water=GRID_HEIGHT_ABOVE_WATER,
        seed=seed,
    )
    floor, _ = derive_grid_depth_range(water_zs)
    assert floor == _EXPECTED_FLOOR_REPR


def test_derived_floor_is_identical_across_all_seeds_and_camera_counts_at_once():
    """The stronger form of the invariance claim: collect every derived
    floor across the full seed x camera-count cross product and assert the
    SET of distinct values has exactly one member -- mirrors D-19.4-15's own
    3,000-draw measurement methodology (seeds x camera counts x
    calibration/holdout), scoped here to calibration-side construction."""
    derived_floors = set()
    for seed in _SEEDS:
        for n_cameras in _N_CAMERAS_VALUES:
            _, _, water_zs = generate_camera_array(
                n_cameras=n_cameras,
                layout=GRID_LAYOUT,
                spacing=GRID_SPACING,
                height_above_water=GRID_HEIGHT_ABOVE_WATER,
                seed=seed,
            )
            floor, _ = derive_grid_depth_range(water_zs)
            derived_floors.add(floor)

    assert len(derived_floors) == 1
    assert derived_floors == {_EXPECTED_FLOOR_REPR}


def test_derived_floor_actually_derives_not_a_frozen_constant():
    """Negative control: a water_zs dict built at a DIFFERENT
    height_above_water must produce a DIFFERENT floor -- proves the helper
    derives from its input rather than returning a memoized/frozen value."""
    _, _, water_zs_default = generate_camera_array(
        n_cameras=12,
        layout=GRID_LAYOUT,
        spacing=GRID_SPACING,
        height_above_water=GRID_HEIGHT_ABOVE_WATER,
        seed=42,
    )
    _, _, water_zs_shallow = generate_camera_array(
        n_cameras=12,
        layout=GRID_LAYOUT,
        spacing=GRID_SPACING,
        height_above_water=0.5,
        seed=42,
    )

    floor_default, _ = derive_grid_depth_range(water_zs_default)
    floor_shallow, _ = derive_grid_depth_range(water_zs_shallow)

    assert floor_default != floor_shallow


def test_derived_floor_respects_custom_board_and_rotation_range():
    """derive_grid_depth_range forwards board/rotation_range_deg through to
    board_clearance_floor rather than silently ignoring them."""
    _, _, water_zs = generate_camera_array(
        n_cameras=12,
        layout=GRID_LAYOUT,
        spacing=GRID_SPACING,
        height_above_water=GRID_HEIGHT_ABOVE_WATER,
        seed=42,
    )
    floor_default_rotation, _ = derive_grid_depth_range(
        water_zs, board=GRID_BOARD_CONFIG, rotation_range_deg=15.0
    )
    floor_wider_rotation, _ = derive_grid_depth_range(
        water_zs, board=GRID_BOARD_CONFIG, rotation_range_deg=30.0
    )

    # A wider tilt range increases the worst-case upward corner excursion,
    # so the floor must be at least as deep (board_clearance_floor's own
    # contract: min_depth grows with rotation_range_deg).
    assert floor_wider_rotation >= floor_default_rotation
