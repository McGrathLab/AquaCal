"""Discard-accounting tests for plan 19.2-26.

Two independent obligations, and the second must not be allowed to substitute for
the first:

A. **Inertness.** Supplying ``discard_stats_out`` must not move a single number.
   Asserted by EXACT equality (``==`` / ``assert_array_equal``), never ``allclose``
   -- a tolerance-based comparison would pass on a change that genuinely moved a
   value in the last bits, which is precisely the claim under test. Also pinned
   against a frozen anchor generated from code that predates the counter edits.

B. **Counter correctness.** A clean scenario leaves every failure counter at zero,
   so a test asserting only zeros would pass against counters that never increment
   at all. The degenerate-pose test below therefore asserts a KNOWN count, and the
   two cross-module invariants are checked on both clean and degenerate paths.
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest

from aquacal.calibration._observability import (
    DEGENERACY_CAUSES,
    DEGENERACY_FATES,
    DISCARD_KEYS,
    DISCARD_STAGES,
    _bump,
    check_denominator_only,
    check_discard_invariants,
    degeneracy_cause_key,
    degeneracy_fate_key,
    observations_evaluated_key,
)
from aquacal.calibration.extrinsics import estimate_board_pose, refractive_solve_pnp
from aquacal.calibration.interface_estimation import optimize_interface
from aquacal.calibration.refinement import joint_refinement
from aquacal.config.schema import (
    BoardConfig,
    BoardPose,
    CameraExtrinsics,
    CameraIntrinsics,
    DegenerateObservationWarning,
)
from aquacal.core.board import BoardGeometry
from aquacal.datasets import create_scenario
from aquacal.datasets.pipelines import calibrate_synthetic
from aquacal.datasets.synthetic import generate_synthetic_detections

ANCHOR_PATH = Path(__file__).parent.parent / "fixtures" / "discard_anchor.json"

_MINIMAL_KWARGS = dict(n_water=1.0, refine_intrinsics=False, seed=1)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def make_degenerate_pose_inputs(
    discard_stats_out: dict[str, int] | None = None,
) -> tuple[NDArray, NDArray] | None:  # type: ignore[name-defined] # noqa: F821
    """Drive `estimate_board_pose` with a corner set too small to solve.

    Used by the plan's launch-gate smoke check as well as the tests here, so it
    must stay importable under this name.
    """
    board = BoardGeometry(create_scenario("minimal", seed=1).board_config)
    intrinsics = CameraIntrinsics(
        K=np.array([[800.0, 0.0, 640.0], [0.0, 800.0, 360.0], [0.0, 0.0, 1.0]]),
        dist_coeffs=np.zeros(5),
        image_size=(1280, 720),
    )
    # Three corners: below solvePnP's four-point minimum, so the too-few-corners
    # branch fires deterministically on every platform.
    corner_ids = np.array([0, 1, 2], dtype=np.int32)
    corners_2d = np.array([[100.0, 100.0], [200.0, 100.0], [150.0, 180.0]])
    return estimate_board_pose(
        intrinsics, corners_2d, corner_ids, board, discard_stats_out=discard_stats_out
    )


# ---------------------------------------------------------------------------
# A. Inertness
# ---------------------------------------------------------------------------


@pytest.mark.slow
def test_discard_stats_out_is_numerically_inert():
    """Omitting, passing None, and passing a live dict give bit-identical results."""
    scenario = create_scenario("minimal", seed=1)

    omitted, _ = calibrate_synthetic(scenario, **_MINIMAL_KWARGS)
    explicit_none, _ = calibrate_synthetic(
        scenario, **_MINIMAL_KWARGS, discard_stats_out=None
    )
    stats: dict[str, int] = {}
    instrumented, _ = calibrate_synthetic(
        scenario, **_MINIMAL_KWARGS, discard_stats_out=stats
    )

    for other, label in ((explicit_none, "explicit-None"), (instrumented, "populated")):
        assert (
            omitted.diagnostics.reprojection_error_rms
            == other.diagnostics.reprojection_error_rms
        ), label
        assert sorted(omitted.cameras) == sorted(other.cameras), label
        for cam in omitted.cameras:
            np.testing.assert_array_equal(
                omitted.cameras[cam].extrinsics.R, other.cameras[cam].extrinsics.R
            )
            np.testing.assert_array_equal(
                omitted.cameras[cam].extrinsics.t, other.cameras[cam].extrinsics.t
            )
            assert omitted.cameras[cam].water_z == other.cameras[cam].water_z, label

    # The instrumented run must actually have counted something, or the inertness
    # above is vacuous -- it would also pass if the parameter were ignored entirely.
    assert stats, "discard_stats_out was supplied but never populated"


@pytest.mark.slow
def test_matches_frozen_anchor():
    """Results still equal values captured BEFORE the counters were added.

    The anchor's provenance is what makes this meaningful: it was generated from a
    checkout without this plan's edits and committed before them. Regenerating it
    from instrumented code would make the test self-confirming and worthless.

    **REGENERATED 2026-08-01 (plan 19.3-04, D-19.3-09), for an unrelated
    reason.** `generate_camera_array`'s `height_above_water` default moved
    from the old shallow 0.15 m literal to the real-rig standoff
    (`WATER_Z` ~1.031 m), and the "minimal" preset this test runs no longer
    passes `height_above_water=0.15` explicitly, so it now inherits the new
    default -- `water_z` moved from ~0.196 to ~1.190 m as a direct, intended
    consequence (not a discard-counter regression; the original
    pre-instrumentation-vs-instrumented comparison this anchor was built for
    is now historical, same as `TestSolverConfigSeedIsInert` in
    `test_pipeline.py`).

    **REGENERATED again 2026-08-04 (plan 19.4-02, D-19.4-09), also for an
    unrelated reason.** `generate_camera_array`'s `height_variation` jitter
    moved from `water_z` onto `C_z` -- cam1 of the "minimal" preset now sits
    at a jittered camera height above a SHARED water plane instead of
    looking through its own slightly-deeper water plane at `C_z == 0`. The
    ground-truth `h_c = water_z - C_z` is unchanged (proven exactly in
    `tests/unit/test_synthetic_scenario_geometry.py`), but the calibrated
    (not ground-truth) `water_z` for this scenario is only weakly
    identified here -- `n_water=1.0` in `_MINIMAL_KWARGS` deliberately
    mismatches the scenario's `n_water=1.333` ground truth, degrading
    refraction to near-inert, which is why a millimeter-scale input jitter
    change can move the optimizer's converged (but weakly-constrained)
    interface estimate by tens of centimeters while reprojection RMS moves
    only in its sixth decimal digit. See
    `tests/fixtures/discard_anchor.json`'s `provenance.note` for the exact
    before/after values.
    """
    if not ANCHOR_PATH.is_file():
        pytest.skip(f"anchor not generated: {ANCHOR_PATH}")
    anchor = json.loads(ANCHOR_PATH.read_text())

    scenario = create_scenario("minimal", seed=1)
    result, _ = calibrate_synthetic(scenario, **_MINIMAL_KWARGS)

    assert (
        result.diagnostics.reprojection_error_rms == anchor["reprojection_error_rms"]
    ), "reprojection RMS moved against the pre-instrumentation anchor"

    assert sorted(result.cameras) == sorted(anchor["cameras"])
    for cam, expected in anchor["cameras"].items():
        np.testing.assert_array_equal(
            result.cameras[cam].extrinsics.R, np.array(expected["R"])
        )
        np.testing.assert_array_equal(
            result.cameras[cam].extrinsics.t, np.array(expected["t"])
        )
        assert result.cameras[cam].water_z == expected["water_z"]


# ---------------------------------------------------------------------------
# B. Counter correctness
# ---------------------------------------------------------------------------


def test_bump_is_a_noop_when_accounting_is_off():
    """_bump(None, ...) does nothing and never raises."""
    _bump(None, "pnp_guard_rejected")
    _bump(None, "pnp_guard_rejected", 5)


def test_counters_populate_on_a_known_degenerate_input():
    """A three-corner input trips the too-few-corners branch a KNOWN number of times.

    Asserts an exact count, not merely non-zero: a counter that fires on every call
    would also pass a non-zero check.
    """
    stats: dict[str, int] = {}
    for _ in range(3):
        assert make_degenerate_pose_inputs(discard_stats_out=stats) is None

    assert stats["pnp_too_few_corners"] == 3
    assert stats["pnp_attempts_total"] == 3
    assert stats["pnp_attempts_nonrefractive"] == 3
    assert stats.get("pnp_attempts_refractive", 0) == 0
    assert stats.get("pnp_solve_failed", 0) == 0
    assert stats.get("pnp_guard_rejected", 0) == 0


def test_refractive_attempt_does_not_pollute_the_nonrefractive_branch():
    """refractive_solve_pnp must not count its inner estimate_board_pose call.

    This is the failure mode that would break the denominator decomposition and,
    through it, send plan 19.2-06's differing-denominator halt into an input
    diagnosis for what is really a counter-scoping bug.
    """
    board = BoardGeometry(create_scenario("minimal", seed=1).board_config)
    intrinsics = CameraIntrinsics(
        K=np.array([[800.0, 0.0, 640.0], [0.0, 800.0, 360.0], [0.0, 0.0, 1.0]]),
        dist_coeffs=np.zeros(5),
        image_size=(1280, 720),
    )
    corner_ids = np.array([0, 1, 2], dtype=np.int32)
    corners_2d = np.array([[100.0, 100.0], [200.0, 100.0], [150.0, 180.0]])

    stats: dict[str, int] = {}
    assert (
        refractive_solve_pnp(
            intrinsics,
            corners_2d,
            corner_ids,
            board,
            water_z=1.0,
            discard_stats_out=stats,
        )
        is None
    )

    assert stats["pnp_attempts_refractive"] == 1
    assert stats.get("pnp_attempts_nonrefractive", 0) == 0, (
        "the inner estimate_board_pose call leaked into the non-refractive branch"
    )
    assert stats["pnp_attempts_total"] == 1
    assert stats["pnp_initial_guess_failed"] == 1
    # NOT check_discard_invariants: producer/consumer agreement is a whole-run
    # relation and this is a bare producer call with no consumer in the loop.
    assert not check_denominator_only(stats)


def test_invariants_catch_a_producer_consumer_mismatch():
    """check_discard_invariants is not vacuous -- it fails on a broken dict."""
    broken = {
        "pnp_attempts_total": 2,
        "pnp_attempts_refractive": 1,
        "pnp_attempts_nonrefractive": 1,
        "pnp_guard_rejected": 2,
        "pose_discarded_by_consumer": 1,
    }
    violations = check_discard_invariants(broken)
    assert any("producer/consumer mismatch" in v for v in violations), violations


def test_invariants_catch_a_split_denominator():
    """A denominator counting only one branch is caught."""
    broken = {
        "pnp_attempts_total": 10,
        "pnp_attempts_refractive": 4,
        "pnp_attempts_nonrefractive": 0,
    }
    violations = check_discard_invariants(broken)
    assert any("denominator mismatch" in v for v in violations), violations


def test_invariants_catch_an_undeclared_key():
    """A site instrumented without declaring its key in DISCARD_KEYS is caught."""
    violations = check_discard_invariants({"totally_made_up": 1})
    assert any("undeclared counter keys" in v for v in violations), violations


def _balanced_degeneracy_stats(total: int) -> dict[str, int]:
    """A minimal stats dict whose two degeneracy axes both sum to `total`."""
    stage = "stage3_interface_optimization"
    return {
        "degenerate_observations_at_solution": total,
        degeneracy_cause_key("above_interface", stage): total,
        degeneracy_fate_key("extended", stage): total,
    }


def test_degeneracy_cause_key_raises_on_unrecognized_cause_or_stage():
    """The closed vocabulary exists so a typo is caught, not silently bucketed."""
    with pytest.raises(ValueError) as excinfo:
        degeneracy_cause_key("corner_wandered_off", "stage3_interface_optimization")
    assert "corner_wandered_off" in str(excinfo.value)

    with pytest.raises(ValueError) as excinfo:
        degeneracy_cause_key("above_interface", "stage3_typo")
    assert "stage3_typo" in str(excinfo.value)


def test_degeneracy_fate_key_raises_on_unrecognized_fate_or_stage():
    with pytest.raises(ValueError) as excinfo:
        degeneracy_fate_key("evaporated", "stage3_interface_optimization")
    assert "evaporated" in str(excinfo.value)

    with pytest.raises(ValueError) as excinfo:
        degeneracy_fate_key("extended", "stage3_typo")
    assert "stage3_typo" in str(excinfo.value)


def test_unattributed_is_a_legal_stage():
    """D-03: an absent stage label is a legitimate call pattern, not an error.

    It must be visible as its own bucket rather than merged into a real stage.
    """
    assert "unattributed" in DISCARD_STAGES
    for cause in DEGENERACY_CAUSES:
        assert degeneracy_cause_key(cause, "unattributed") in DISCARD_KEYS
    for fate in DEGENERACY_FATES:
        assert degeneracy_fate_key(fate, "unattributed") in DISCARD_KEYS
    assert observations_evaluated_key("unattributed") in DISCARD_KEYS


def test_invariants_catch_a_cause_split_that_does_not_sum_to_the_merged_total():
    """Relation 3: the merged total equals the sum of the nine cause keys."""
    broken = _balanced_degeneracy_stats(5)
    broken[degeneracy_cause_key("above_interface", "stage3_interface_optimization")] = 4

    violations = check_discard_invariants(broken)
    offenders = [v for v in violations if "cause split mismatch" in v]
    assert offenders, violations
    assert "5" in offenders[0] and "4" in offenders[0]


def test_invariants_catch_a_fate_split_that_does_not_sum_to_the_merged_total():
    """Relation 4: the merged total independently equals the sum of the six fate keys.

    Two exact decompositions of one total is the cross-check neither axis provides
    alone.
    """
    broken = _balanced_degeneracy_stats(5)
    broken[degeneracy_fate_key("extended", "stage3_interface_optimization")] = 3

    violations = check_discard_invariants(broken)
    offenders = [v for v in violations if "fate split mismatch" in v]
    assert offenders, violations
    assert "5" in offenders[0] and "3" in offenders[0]


def test_invariants_catch_causes_exceeding_the_stage_denominator():
    """Relation 5: a stage cannot have more degenerate observations than it evaluated."""
    stage = "stage3_interface_optimization"
    broken = _balanced_degeneracy_stats(9)
    broken[observations_evaluated_key(stage)] = 4

    violations = check_discard_invariants(broken)
    assert any("degeneracy denominator mismatch" in v for v in violations), violations


def test_a_consistent_degeneracy_split_reports_no_violation():
    """The three new relations are not vacuously failing on well-formed input."""
    stage = "stage3_interface_optimization"
    good = _balanced_degeneracy_stats(6)
    good[observations_evaluated_key(stage)] = 100

    assert not check_denominator_only(good)


@pytest.mark.slow
def test_full_run_satisfies_both_invariants():
    """On a real (synthetic) calibration, both cross-checks hold and keys are declared."""
    scenario = create_scenario("minimal", seed=1)
    stats: dict[str, int] = {}
    calibrate_synthetic(scenario, **_MINIMAL_KWARGS, discard_stats_out=stats)

    assert stats
    assert set(stats) <= set(DISCARD_KEYS), sorted(set(stats) - set(DISCARD_KEYS))
    violations = check_discard_invariants(stats)
    assert not violations, violations

    # A clean synthetic scenario must not trip the degenerate-pose guard. This is
    # the over-counting guard: it fails if the counter fires indiscriminately.
    assert stats.get("pnp_guard_rejected", 0) == 0, stats


# ---------------------------------------------------------------------------
# C. Final-solution degeneracy guard count (plan 19.3-02, D-19.3-11)
# ---------------------------------------------------------------------------
#
# The library RECORDS the number of observations the refractive model could not
# project AT THE FINAL SOLUTION (never raises -- see DegenerateObservationWarning
# and the guard blocks in interface_estimation.py / refinement.py). These tests
# cover both solver stages (optimize_interface's Stage 3, joint_refinement's
# Stage 3 intrinsic pass) through the real public call shape, not by reaching
# into private guard internals.


def _build_three_camera_board_scene(seed: int, depth_range: tuple[float, float]):
    """A 3-camera scene with board poses constructed directly (no generators).

    Bypasses `generate_board_trajectory`/`generate_real_rig_trajectory` entirely --
    plan 19.3-01 makes those raise on a shallow `depth_range`, and this helper's
    whole purpose is to exercise depths those generators would now refuse to
    construct. `tvec[2]` is drawn from `depth_range` (world-frame board center
    height), matching the same construction pattern used by
    `tests/unit/test_optim_common.py::TestInvalidProjectionKeepsGradient`.

    Returns:
        (intrinsics, extrinsics, board, water_zs, detections) -- ready to pass
        straight into `optimize_interface`.
    """
    rng = np.random.default_rng(seed)
    K = np.array([[500.0, 0.0, 320.0], [0.0, 500.0, 240.0], [0.0, 0.0, 1.0]])
    cams = ("cam0", "cam1", "cam2")
    intrinsics = {
        c: CameraIntrinsics(K=K.copy(), dist_coeffs=np.zeros(5), image_size=(640, 480))
        for c in cams
    }
    extrinsics = {
        "cam0": CameraExtrinsics(R=np.eye(3), t=np.zeros(3)),
        "cam1": CameraExtrinsics(R=np.eye(3), t=np.array([0.1, 0.0, 0.0])),
        "cam2": CameraExtrinsics(R=np.eye(3), t=np.array([0.0, 0.1, 0.0])),
    }
    board = BoardGeometry(
        BoardConfig(
            squares_x=6,
            squares_y=5,
            square_size=0.04,
            marker_size=0.03,
            dictionary="DICT_4X4_50",
        )
    )
    water_z = 0.15
    water_zs = {c: water_z for c in cams}

    poses = []
    for i in range(40):
        rx, ry, rz = rng.uniform(-0.26, 0.26, 3)
        tx, ty = rng.uniform(-0.05, 0.05, 2)
        tz = rng.uniform(*depth_range)
        poses.append(
            BoardPose(
                frame_idx=i, rvec=np.array([rx, ry, rz]), tvec=np.array([tx, ty, tz])
            )
        )

    detections = generate_synthetic_detections(
        intrinsics,
        extrinsics,
        water_zs,
        board,
        poses,
        noise_std=0.5,
        min_corners=6,
        seed=seed,
    )
    return intrinsics, extrinsics, board, water_zs, detections


@pytest.mark.slow
def test_clean_run_records_present_and_zero_guard_count():
    """A synthetic run with `discard_stats_out={}` records the key at 0.

    Present-and-zero (not absent) is the load-bearing distinction established
    by 19.2-27: `{}` means "requested, and zero fired", `None` means
    "accounting never requested".
    """
    intrinsics, extrinsics, board, water_zs, detections = (
        _build_three_camera_board_scene(seed=0, depth_range=(0.3, 0.5))
    )
    stats: dict[str, int] = {}
    optimize_interface(
        detections,
        intrinsics,
        extrinsics,
        board,
        "cam0",
        initial_water_zs=water_zs,
        verbose=0,
        min_corners=6,
        discard_stats_out=stats,
    )
    assert stats["degenerate_observations_at_solution"] == 0
    assert "degenerate_observations_at_solution" in stats


@pytest.mark.slow
def test_none_records_nothing_and_never_raises():
    """`discard_stats_out=None` (the default) records nothing and does not raise."""
    intrinsics, extrinsics, board, water_zs, detections = (
        _build_three_camera_board_scene(seed=0, depth_range=(0.3, 0.5))
    )
    # Must not raise, and there is nothing to inspect afterward -- None stays None.
    optimize_interface(
        detections,
        intrinsics,
        extrinsics,
        board,
        "cam0",
        initial_water_zs=water_zs,
        verbose=0,
        min_corners=6,
        discard_stats_out=None,
    )


@pytest.mark.slow
def test_shallow_scenario_trips_the_guard_at_the_final_solution():
    """A deliberately shallow scene (built directly, not via a generator) records
    a positive guard count at the final least_squares solution.

    Seed 2 is pinned: this specific seed/depth-range combination was verified
    (2026-08-01) to leave 2 observations the refractive model cannot project
    at the converged solution -- a "the solver wandered" case (D-19.3-11 point
    3), not a construction-time violation (that is D-19.3-04's job, in a
    different plan).
    """
    intrinsics, extrinsics, board, water_zs, detections = (
        _build_three_camera_board_scene(seed=2, depth_range=(0.155, 0.18))
    )
    stats: dict[str, int] = {}
    with pytest.warns(DegenerateObservationWarning):
        optimize_interface(
            detections,
            intrinsics,
            extrinsics,
            board,
            "cam0",
            initial_water_zs=water_zs,
            verbose=0,
            min_corners=6,
            discard_stats_out=stats,
        )
    assert stats["degenerate_observations_at_solution"] > 0
    # check_discard_invariants is a whole-run-only check; a bare optimize_interface
    # call is not a full pipeline run (no PnP producer/consumer pairing to cross-
    # check here), so use the denominator-only subset, matching
    # test_refractive_attempt_does_not_pollute_the_nonrefractive_branch's usage.
    assert not check_denominator_only(stats), stats


@pytest.mark.slow
def test_joint_refinement_signature_accepts_and_bumps_discard_stats_out():
    """`joint_refinement` (Stage 3's intrinsic pass) also threads the sink.

    Runs the intrinsic pass on the same clean scene as
    `test_clean_run_records_present_and_zero_guard_count`, confirming the second
    solver stage records present-and-zero too.
    """
    intrinsics, extrinsics, board, water_zs, detections = (
        _build_three_camera_board_scene(seed=0, depth_range=(0.3, 0.5))
    )
    stage3_stats: dict[str, int] = {}
    stage3_result = optimize_interface(
        detections,
        intrinsics,
        extrinsics,
        board,
        "cam0",
        initial_water_zs=water_zs,
        verbose=0,
        min_corners=6,
        discard_stats_out=stage3_stats,
    )
    assert stage3_stats["degenerate_observations_at_solution"] == 0

    refine_stats: dict[str, int] = {}
    joint_refinement(
        stage3_result=stage3_result,
        detections=detections,
        intrinsics=intrinsics,
        board=board,
        reference_camera="cam0",
        refine_intrinsics=False,
        verbose=0,
        min_corners=6,
        discard_stats_out=refine_stats,
    )
    assert refine_stats["degenerate_observations_at_solution"] == 0
    assert "degenerate_observations_at_solution" in refine_stats
