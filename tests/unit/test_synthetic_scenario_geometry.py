"""Scenario-invariant geometry proofs for the single-flat-interface fix.

SC-1 / SC-2 (D-19.4-09): every synthetic scenario source must model ONE flat
water surface shared by all cameras, with the per-camera interface distance
(``h_c = water_z - C_z``) preserved exactly by moving the jitter onto camera
height (``C_z``) instead of the water surface (``water_z``).

The absence of a test like this one is why the per-camera-water-surface
defect shipped: three of five scenario sources (``"ideal"``, ``"realistic"``,
``generate_real_rig_array``) were already correct, but nothing asserted the
invariant across every source, so ``generate_camera_array``'s jitter
silently gave each camera its own interface plane. This file is a
ground-truth-construction check only -- no calibration solve runs here.
"""

from __future__ import annotations

import numpy as np
import pytest

from aquacal.datasets import (
    create_scenario,
    generate_camera_array,
    generate_real_rig_array,
)

# ============================================================================
# SC-1: every scenario source yields exactly ONE distinct water_z
# ============================================================================


@pytest.mark.parametrize("name", ["ideal", "minimal", "realistic"])
@pytest.mark.parametrize("seed", [0, 1, 42, 99])
def test_create_scenario_water_zs_single_shared_plane(name, seed):
    """SC-1 (D-19.4-09): every preset's water_zs has exactly one distinct
    value -- one flat interface shared by all cameras, at every seed."""
    scenario = create_scenario(name, seed=seed)
    assert len(set(scenario.water_zs.values())) == 1


def test_generate_real_rig_array_water_zs_single_shared_plane():
    """SC-1 (D-19.4-09): the real-rig generator already models one shared
    plane -- confirmed here as a scenario source, not just by inspection."""
    _, _, water_zs = generate_real_rig_array()
    assert len(set(water_zs.values())) == 1


@pytest.mark.parametrize("layout", ["grid", "line", "ring"])
@pytest.mark.parametrize("n_cameras", [2, 8, 12, 16])
@pytest.mark.parametrize("seed", [0, 1, 42, 99])
def test_generate_camera_array_water_zs_single_shared_plane(layout, n_cameras, seed):
    """SC-1 (D-19.4-09): generate_camera_array yields exactly one distinct
    water_z at every layout, camera count and seed -- the direct fix for the
    defect this file exists to catch."""
    _, _, water_zs = generate_camera_array(
        n_cameras=n_cameras, layout=layout, seed=seed
    )
    assert len(set(water_zs.values())) == 1


# ============================================================================
# SC-2: h_c = water_z - C_z is preserved exactly per camera
# ============================================================================


def test_generate_camera_array_hc_preservation_matches_replayed_rng_stream():
    """SC-2 (D-19.4-09): h_c = water_z - C_z equals height_above_water plus
    the exact per-camera delta this generator draws, replayed independently
    from the same seeded numpy Generator stream (no re-import of pre-fix
    code). Exact float equality only -- blocking anti-pattern 3 forbids
    relaxing this to a tolerance."""
    n_cameras = 12
    layout = "grid"
    height_above_water = 1.031
    height_variation = 0.005
    seed = 42

    _, extrinsics, water_zs = generate_camera_array(
        n_cameras=n_cameras,
        layout=layout,
        height_above_water=height_above_water,
        height_variation=height_variation,
        seed=seed,
    )

    # Replay the exact per-iteration draw order the generator uses: roll
    # first (skipped for i == 0), then delta (skipped for i == 0) -- see
    # D-19.4-09 and the RNG-ordering constraint in synthetic.py.
    rng = np.random.default_rng(seed)
    expected_deltas: dict[str, float] = {}
    for i in range(n_cameras):
        cam_name = f"cam{i}"
        if i == 0:
            expected_deltas[cam_name] = 0.0
            continue
        rng.uniform(-0.1, 0.1)  # roll -- drawn, value unused here
        delta = rng.normal(0, height_variation)
        expected_deltas[cam_name] = delta

    for cam_name, expected_delta in expected_deltas.items():
        h_c = water_zs[cam_name] - extrinsics[cam_name].C[2]
        assert h_c == height_above_water + expected_delta


# ============================================================================
# The jitter is RELOCATED, not removed
# ============================================================================


def test_generate_camera_array_jitter_relocated_to_camera_height():
    """The C_z <-> water_z degeneracy E7 exists to probe must survive: with
    non-zero height_variation, camera heights scatter (not all zero) while
    cam0 -- the reference camera -- stays exactly at C_z == 0.0."""
    _, extrinsics, _ = generate_camera_array(
        n_cameras=12,
        layout="grid",
        height_variation=0.005,
        seed=42,
    )
    c_zs = {ext.C[2] for ext in extrinsics.values()}
    assert len(c_zs) > 1
    assert extrinsics["cam0"].C[2] == 0.0


def test_generate_camera_array_zero_variation_is_true_no_op():
    """height_variation=0.0 is a true no-op (unchanged from pre-fix): every
    camera sits at C_z == 0.0 and every water_z equals height_above_water
    exactly."""
    height_above_water = 1.031
    _, extrinsics, water_zs = generate_camera_array(
        n_cameras=12,
        layout="grid",
        height_above_water=height_above_water,
        height_variation=0.0,
        seed=42,
    )
    for ext in extrinsics.values():
        assert ext.C[2] == 0.0
    for water_z in water_zs.values():
        assert water_z == height_above_water
