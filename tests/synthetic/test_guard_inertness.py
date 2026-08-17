"""Exact-equality inertness proof for the guard-count recording sink (plan 19.3-02).

D-19.3-11 requires that recording the final-solution degeneracy guard count into
``discard_stats`` (via the ``discard_stats_out`` parameter on both
``optimize_interface`` and ``joint_refinement``) moves NOT ONE recovered
calibration value. Per Sequencing Constraint 12, if this recording change is not
proven inert here, E2 -- a 48-87 minute real-data run whose Section-3 numbers
were re-verified at 0.000% delta on 2026-07-31 (`faa05b3`) -- re-enters this
phase's scope.

Following the 19.2 plan 27 proof pattern (`19.2-27-SUMMARY.md`) exactly:

1. Run the package's cheapest legal synthetic scenario ("ideal": 4 cameras, 20
   frames, 0 noise) twice with the same seed -- once with ``discard_stats_out=None``,
   once with ``discard_stats_out={}`` -- using the exact call shape (same
   ``normal_fixed``, ``refine_intrinsics``, ``shared_interface``) real experiment
   call sites use.
2. Assert EVERY returned calibration value is bit-identical: extrinsics R/t,
   per-camera water_z, every board pose rvec/tvec, and the final RMS. Exact
   equality only (``==`` / ``np.testing.assert_array_equal``) -- NEVER a
   fuzzy/tolerance-based comparison. A failure here is a blocking finding, not
   something to loosen (see this module-level docstring's Sequencing
   Constraint 12 note; this module must not be edited to add a tolerance).
3. Assert the sink was actually populated (not vacuously ignored): the
   ``discard_stats_out={}`` run has the key present and int-typed; the
   ``discard_stats_out=None`` run recorded nothing.
4. Cover both solver stages: at least one parametrization exercises
   ``refine_intrinsics=True`` (joint_refinement's new ``discard_stats_out``
   parameter), and a second exercises ``normal_fixed=False`` (the real-rig /
   E2-matching configuration), both against ``optimize_interface`` alone and
   the full Stage-3 + intrinsic-pass pipeline.

This module is marked ``@pytest.mark.slow`` -- it runs full least_squares solves,
twice per parametrization. It is this phase's single most load-bearing test:
``pytest -m "not slow"`` deselecting it would make a green fast run worthless
evidence for Sequencing Constraint 12. Run this file UNFILTERED (no ``-m``
selector) to get real signal.
"""

from __future__ import annotations

import numpy as np
import pytest

from aquacal.calibration._observability import (
    DEGENERACY_CAUSES,
    DEGENERACY_FATES,
    DISCARD_STAGES,
    check_denominator_only,
    degeneracy_cause_key,
    degeneracy_fate_key,
    observations_evaluated_key,
)
from aquacal.calibration.extrinsics import build_pose_graph, estimate_extrinsics
from aquacal.calibration.interface_estimation import optimize_interface
from aquacal.calibration.refinement import joint_refinement
from aquacal.core.board import BoardGeometry

from .ground_truth import create_scenario, generate_synthetic_detections


def _stage2_inputs(seed: int):
    """Build the "ideal" scenario (cheapest, deterministic) and run Stage 2 once.

    Stage 2 (pose-graph extrinsic initialization) is not instrumented by this
    plan and is run only once, shared between both Stage-3 runs being compared
    -- the inertness claim under test is about `discard_stats_out` on
    `optimize_interface`/`joint_refinement`, not about Stage 2.
    """
    scenario = create_scenario("ideal", seed=seed)
    board = BoardGeometry(scenario.board_config)
    detections = generate_synthetic_detections(
        intrinsics=scenario.intrinsics,
        extrinsics=scenario.extrinsics,
        water_zs=scenario.water_zs,
        board=board,
        board_poses=scenario.board_poses,
        noise_std=scenario.noise_std,
        seed=seed,
    )
    reference_camera = min(
        scenario.extrinsics,
        key=lambda c: np.linalg.norm(scenario.extrinsics[c].C),
    )
    pose_graph = build_pose_graph(detections, min_cameras=2)
    initial_extrinsics = estimate_extrinsics(
        pose_graph, scenario.intrinsics, board, reference_camera
    )
    return scenario, board, detections, reference_camera, initial_extrinsics


def _run_full_calibration(
    scenario,
    board,
    detections,
    reference_camera,
    initial_extrinsics,
    *,
    normal_fixed: bool,
    refine_intrinsics: bool,
    shared_interface: bool,
    discard_stats_out: dict[str, int] | None,
    discard_stage_stage3: str | None = None,
    discard_stage_intrinsic_pass: str | None = None,
):
    """Replicate `calibrate_synthetic`'s Stage 3 (+ optional intrinsic pass) call
    shape exactly, but return board poses too (which `calibrate_synthetic`'s
    `CalibrationResult` does not expose) so this test can assert on them.
    """
    interface_normal = np.array([0.0, 0.0, -1.0], dtype=np.float64)

    opt_extrinsics, opt_distances, opt_poses, rms = optimize_interface(
        detections=detections,
        intrinsics=scenario.intrinsics,
        initial_extrinsics=initial_extrinsics,
        board=board,
        reference_camera=reference_camera,
        initial_water_zs=scenario.water_zs,
        interface_normal=interface_normal,
        n_air=1.0,
        n_water=scenario.n_water,
        loss="huber",
        loss_scale=1.0,
        min_corners=4,
        normal_fixed=normal_fixed,
        shared_interface=shared_interface,
        discard_stats_out=discard_stats_out,
        discard_stage=discard_stage_stage3,
    )

    if refine_intrinsics:
        stage3_result = (opt_extrinsics, opt_distances, opt_poses, rms)
        opt_extrinsics, opt_distances, opt_poses, _opt_intrinsics, rms = (
            joint_refinement(
                stage3_result=stage3_result,
                detections=detections,
                intrinsics=scenario.intrinsics,
                board=board,
                reference_camera=reference_camera,
                refine_intrinsics=True,
                interface_normal=interface_normal,
                n_air=1.0,
                n_water=scenario.n_water,
                loss="huber",
                loss_scale=1.0,
                min_corners=4,
                normal_fixed=normal_fixed,
                shared_interface=shared_interface,
                discard_stats_out=discard_stats_out,
                discard_stage=discard_stage_intrinsic_pass,
            )
        )

    return opt_extrinsics, opt_distances, opt_poses, rms


def _assert_bit_identical(result_none, result_populated):
    """Assert every returned calibration value is bit-identical between two runs.

    Exact equality only -- `==` / `np.testing.assert_array_equal`. Never a
    fuzzy/tolerance-based comparison: that would pass on a change that
    genuinely moved a value in the last bits, which is exactly the claim
    under test.
    """
    ext_a, dist_a, poses_a, rms_a = result_none
    ext_b, dist_b, poses_b, rms_b = result_populated

    assert rms_a == rms_b

    assert sorted(ext_a) == sorted(ext_b)
    for cam in ext_a:
        np.testing.assert_array_equal(ext_a[cam].R, ext_b[cam].R)
        np.testing.assert_array_equal(ext_a[cam].t, ext_b[cam].t)
        assert dist_a[cam] == dist_b[cam]

    poses_a_by_frame = {p.frame_idx: p for p in poses_a}
    poses_b_by_frame = {p.frame_idx: p for p in poses_b}
    assert sorted(poses_a_by_frame) == sorted(poses_b_by_frame)
    for frame_idx in poses_a_by_frame:
        np.testing.assert_array_equal(
            poses_a_by_frame[frame_idx].rvec, poses_b_by_frame[frame_idx].rvec
        )
        np.testing.assert_array_equal(
            poses_a_by_frame[frame_idx].tvec, poses_b_by_frame[frame_idx].tvec
        )


@pytest.mark.slow
@pytest.mark.parametrize(
    "normal_fixed,refine_intrinsics,shared_interface",
    [
        # calibrate_synthetic's own defaults (matches E1/E7's un-overridden call shape).
        (True, False, True),
        # Exercises joint_refinement's new discard_stats_out parameter
        # (Stage 3's intrinsic pass) -- required coverage per the plan.
        (True, True, True),
        # Matches E2's real-rig / tab:cpr configuration (interface_normal_fixed=False).
        (False, True, True),
    ],
    ids=["stage3-only", "with-intrinsic-pass", "normal-unfixed-with-intrinsic-pass"],
)
def test_guard_count_recording_is_inert(
    normal_fixed, refine_intrinsics, shared_interface
):
    """Recording the guard count moves zero calibration numbers, for both solver
    stages and both `normal_fixed` values real call sites use."""
    seed = 42
    scenario, board, detections, reference_camera, initial_extrinsics = _stage2_inputs(
        seed
    )

    result_none = _run_full_calibration(
        scenario,
        board,
        detections,
        reference_camera,
        initial_extrinsics,
        normal_fixed=normal_fixed,
        refine_intrinsics=refine_intrinsics,
        shared_interface=shared_interface,
        discard_stats_out=None,
    )

    stats: dict[str, int] = {}
    result_populated = _run_full_calibration(
        scenario,
        board,
        detections,
        reference_camera,
        initial_extrinsics,
        normal_fixed=normal_fixed,
        refine_intrinsics=refine_intrinsics,
        shared_interface=shared_interface,
        discard_stats_out=stats,
    )

    _assert_bit_identical(result_none, result_populated)

    # The sink must have actually been populated, not vacuously ignored -- a
    # populated-zero and an absent key must stay distinguishable (None vs {}).
    assert "degenerate_observations_at_solution" in stats
    assert isinstance(stats["degenerate_observations_at_solution"], int)


@pytest.mark.slow
@pytest.mark.parametrize(
    "normal_fixed,refine_intrinsics,shared_interface",
    [
        (True, False, True),
        (True, True, True),
    ],
    ids=["stage3-only", "with-intrinsic-pass"],
)
def test_split_counters_and_reason_plumbing_are_inert(
    normal_fixed, refine_intrinsics, shared_interface
):
    """D-18, solve-level companion: phase 24's split counters move no numbers.

    Supplying `discard_stats_out` is now what causes `compute_residuals` to
    allocate the projector's `nan_reason_out` array on the post-solve evaluation,
    so this single comparison covers BOTH the new counters and the reason
    plumbing reaching the projector. The projector's own exact-pixel inertness is
    proven separately at the unit level in
    `tests/unit/test_refractive_geometry.py::TestBatchNanReason`.

    Asserted on **cost** (the returned RMS) and on the "ideal" scenario, which is
    well conditioned. This project's rule is that bit-identity gates are
    conditioning-dependent, so an ill-conditioned scene must never be the vehicle
    for this claim -- see `.planning/knowledge-base.md` § "Bit-identity gates
    depend on conditioning".

    Why this is verified here rather than left to Phase 29's E2 sanity control:
    that control fires four phases later against a tree that also contains Phase
    23's solver-touching changes, so a failure there would not attribute to this
    phase -- and by then the freeze has happened.
    """
    seed = 42
    scenario, board, detections, reference_camera, initial_extrinsics = _stage2_inputs(
        seed
    )

    result_none = _run_full_calibration(
        scenario,
        board,
        detections,
        reference_camera,
        initial_extrinsics,
        normal_fixed=normal_fixed,
        refine_intrinsics=refine_intrinsics,
        shared_interface=shared_interface,
        discard_stats_out=None,
    )

    stats: dict[str, int] = {}
    result_split = _run_full_calibration(
        scenario,
        board,
        detections,
        reference_camera,
        initial_extrinsics,
        normal_fixed=normal_fixed,
        refine_intrinsics=refine_intrinsics,
        shared_interface=shared_interface,
        discard_stats_out=stats,
        discard_stage_stage3="stage3_interface_optimization",
        discard_stage_intrinsic_pass="stage3_intrinsic_pass",
    )

    # Cost agreement is the load-bearing assertion; bit-identity of the whole
    # solution is asserted too because this scenario is well conditioned.
    assert result_none[3] == result_split[3]
    _assert_bit_identical(result_none, result_split)

    # The split actually landed, and both decompositions are exact.
    merged = stats["degenerate_observations_at_solution"]
    by_cause = sum(stats.get(k, 0) for k in _cause_keys())
    by_fate = sum(stats.get(k, 0) for k in _fate_keys())
    assert by_cause == merged
    assert by_fate == merged
    # `check_denominator_only`: producer/consumer agreement is a whole-run
    # relation and this harness runs Stage 3 only. Relations 3-5 hold regardless.
    assert not check_denominator_only(stats), check_denominator_only(stats)

    stage_key = observations_evaluated_key("stage3_interface_optimization")
    assert stage_key in stats
    assert stats[stage_key] > 0


def _cause_keys():
    return [
        degeneracy_cause_key(cause, stage)
        for cause in DEGENERACY_CAUSES
        for stage in DISCARD_STAGES
    ]


def _fate_keys():
    return [
        degeneracy_fate_key(fate, stage)
        for fate in DEGENERACY_FATES
        for stage in DISCARD_STAGES
    ]
