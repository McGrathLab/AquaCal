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
    DISCARD_KEYS,
    _bump,
    check_denominator_only,
    check_discard_invariants,
)
from aquacal.calibration.extrinsics import estimate_board_pose, refractive_solve_pnp
from aquacal.config.schema import CameraIntrinsics
from aquacal.core.board import BoardGeometry
from aquacal.datasets import create_scenario
from aquacal.datasets.pipelines import calibrate_synthetic

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
