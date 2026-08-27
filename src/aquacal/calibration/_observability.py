"""Opt-in observation of the bundle-adjustment optimizers. Read-only: never changes the numbers.

`OptimizerObserver` wraps the `fun`/`jac` callables passed to `scipy.optimize.least_squares`
and supplies a `callback` so that each accepted `trf` iteration is recorded as a `TraceRow`.
Wrapping is purely observational -- the wrapped callables return the inner results unchanged,
and passing an observer must not alter `result.x` or `result.cost` in any way.

Column layout note: `optimality` here is an *unconstrained* proxy, `||J^T f||_inf`, computed
from the residual/Jacobian pair at each accepted step. It intentionally does NOT match the
`optimality` scipy reports on the final `OptimizeResult`, which applies Coleman-Li bound
scaling that this proxy skips. When the Jacobian is computed via `"2-point"` (i.e.
`use_sparse_jacobian=False`), there is no `jac` callable to wrap, so `optimality` is `nan`
for every row.
"""

from __future__ import annotations

import csv
import logging
import math
from dataclasses import dataclass
from functools import wraps
from pathlib import Path
from typing import TYPE_CHECKING, Callable

import numpy as np
from numpy.typing import NDArray

from aquacal.io.internals import warn_if_overwriting

if TYPE_CHECKING:
    from aquacal.validation.conditioning import ConditioningReport

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Discard accounting (plan 19.2-26)
# ---------------------------------------------------------------------------
#
# The calibration path drops observations, poses and video frames at a number of
# sites. Before this, every one of those was silent: a bare `return None` or
# `continue`, with no counter and no log anywhere in the module. A discard that no
# artifact records cannot be audited after the fact, so a change in what the solve
# sees became a change in a published number with no trace.
#
# Counting is opt-in through an out-parameter that defaults to None, matching the
# `memory_out` pattern established by plan 19.2-01. When it is None -- the default,
# and what every existing caller gets -- `_bump` does one `is not None` test and
# returns, so behaviour is byte-for-byte what it was.
#
# NOTHING HERE MAY BE CALLED FROM A PER-POINT OR PER-RESIDUAL LOOP. Every site
# instrumented is per-(camera, frame) or per-video-frame. `benchmark.json`'s
# wall-clock is published and E4's nine-cell grid is already committed at 5b17cd4;
# a counter in the projection hot path would move those numbers. The failure
# branches in core/refractive_geometry.py now write an int8 reason code through an
# opt-in out-parameter that is None on every production iteration, all of them
# outside the Newton loop -- so the prohibition stated here, that nothing may be
# COUNTED from a per-point loop, is intact.

# ---------------------------------------------------------------------------
# Degeneracy split vocabularies (phase 24, DEGEN-02)
# ---------------------------------------------------------------------------
#
# TWO INDEPENDENT AXES, NOT A CROSS PRODUCT. With the failure cause now available
# per point from the projector's `nan_reason_out` array, cause and fate are
# independent facts about an invalid observation, and each one partitions the
# invalid set exactly. They are recorded as MARGINALS.
#
# Why not the 3x2 joint: it would be 18 kind keys plus 3 denominators, tripling
# the vocabulary to answer a question nobody has asked. The per-observation joint
# is explicitly DEGEN-04's (Phase 25); this phase reports the split and does not
# interpret it. The two marginals answer both questions that ARE asked -- "what
# went wrong" and "does it still carry gradient" -- and each yields an exact,
# derived invariant (relations 3 and 4 in `check_discard_invariants`).
#
# THE COLLISION HAZARD AND WHY THE NAMES CARRY THE AXIS. `behind_camera` is a
# CAUSE (the projector could not place a pixel) while `penalized` is a FATE (the
# pinhole extension could not place one either). They are correlated but not
# identical, so a bare `degenerate_observations_behind_camera__stage3_...` would be
# ambiguous about which axis it meant. The `cause_`/`fate_` prefixes are therefore
# a mitigation, not cosmetics: plan 24-02 publishes BOTH axes side by side in one
# CSV, where a reader who summed a cause column and a fate column together would
# double the true total.

# ---------------------------------------------------------------------------
# Gate scope: the degeneracy gate is SYNTHETIC-ONLY (phase 25, DEGEN-04, D-04)
# ---------------------------------------------------------------------------
#
# THE DECISION. The production degeneracy gate -- a recorded
# `degenerate_observations_at_solution > 0` forcing a cell's status to
# "degenerate" -- applies to the SYNTHETIC harnesses only
# (`experiments/e4_benchmark_grid.py`, `experiments/e6_generalization_sweep.py`).
# It does NOT extend to real-rig runs, and the production pipeline deliberately
# reports no such status.
#
# WHY: AUTHORED GEOMETRY VERSUS GIVEN GEOMETRY. A synthetic scenario's geometry
# is *authored* -- every camera pose, water height and board placement was chosen
# by the harness. An observation that cannot be projected at the solution
# therefore means the scenario itself was malformed, and the cell must fail
# rather than contribute a number. A physical rig's geometry is *given*: the
# board went where the operator put it, and a small unprojectable fraction is a
# fact about the deployment -- a calibration board riding at or breaking the
# water surface on a pass -- not a defect in this library. Gating a real run on
# it would discard a sound calibration for describing its own session honestly.
#
# WHY THIS WAS SETTLED ON MECHANISM, NOT ON A COUNT. The count was never
# load-bearing. The production rig's published figure is a sum accumulated across
# solver stages through one un-reset `discard_stats` dict, so it may double-count
# an observation invalid in two stages; that invalidated the original
# 0.268%-of-observations argument outright. What licenses the decision is instead
# WHICH FAILURE KIND DOMINATES. The instrumented probe at
# `.planning/probes/2026-08-17-degeneracy-classification/` measured it: every
# flagged observation was `above_interface` (`NAN_REASON_ABOVE_INTERFACE`, a
# corner sitting millimetres to centimetres ABOVE the water surface, where the
# refractive projection is undefined by construction), the other two causes were
# empty -- not small, empty -- and they were confined to a handful of frames in
# two bursts on an otherwise healthy run. That is a data-geometry condition, not
# a solver pathology. Every number in that probe is PROVISIONAL: Phase 29's
# frozen table is the sole source of any count that ships (D-02), and no figure
# from the probe may be quoted as a published quantity.
#
# THE TRIPWIRE THAT RE-OPENS THIS. If Phase 29's frozen table shows a MATERIALLY
# POPULATED `camera_model_failure` bucket -- `NAN_REASON_BEHIND_CAMERA` recorded
# with a POSITIVE `h_q`, i.e. the corner was legitimately under water and the
# camera model still failed to place a pixel -- then the geometry was fine and
# the projection was not. That is a library limitation rather than a deployment
# fact, and it is a DIFFERENT decision: this rationale is void and the gate's
# scope must be revisited. Nothing else re-opens it; a change in the raw count
# alone does not.
#
# WHAT MUST NEVER BE RESTORED. The synthetic gate predicate is exactly
# `count > 0 -> degenerate`, with a smoke-path carve-out and nothing else
# (D-05, `19.3-07-PLAN.md`). It must NOT be softened into a threshold, a
# tolerance or a fraction-of-observations rule. "Real rigs tolerate a few" is an
# argument about real rigs, which this decision has already removed from the
# gate's scope -- it is not a reason to loosen the synthetic one.
#
# This block is PROSE ONLY. No bucket vocabulary, constant or accessor belongs
# here: the taxonomy lives in `experiments/_degeneracy.py` (D-06), and the
# library emits raw reason codes, never classified names.

#: Why the refractive projection failed. Read off the projector's reason array,
#: never re-derived at the call site.
_DEGENERACY_CAUSES: tuple[str, ...] = (
    "above_interface",
    "behind_camera",
    "interface_below_camera",
)

#: What the residual then did. Read off the existing `unextendable` mask.
#: `extended` = continued by the pinhole extension, keeps a gradient; `penalized`
#: = flat INVALID_PROJECTION_PENALTY_PX, no gradient at all.
_DEGENERACY_FATES: tuple[str, ...] = ("extended", "penalized")

#: The solver stages that bump these counters. `"unattributed"` is a declared,
#: legal bucket (D-03) so an absent stage label is visible rather than merged into
#: a real stage.
_DISCARD_STAGES: tuple[str, ...] = (
    "stage3_interface_optimization",
    "stage3_intrinsic_pass",
    "unattributed",
)

#: Every counter key this module may emit. `diagnostics.json` consumers can rely on
#: the vocabulary being closed -- an unknown key means someone added a site without
#: declaring it here.
DISCARD_KEYS: tuple[str, ...] = (
    # Denominators.
    "pnp_attempts_total",
    "pnp_attempts_refractive",
    "pnp_attempts_nonrefractive",
    # Producer-side failures, one per distinct failure mode. These are deliberately
    # NOT merged: they carry different diagnoses, and plan 19.2-06's gate reads
    # `pnp_guard_rejected` specifically.
    "pnp_too_few_corners",
    "pnp_solve_failed",
    "pnp_initial_guess_failed",
    "pnp_nonfinite_refinement",
    "pnp_guard_rejected",
    # Consumer side -- the same events counted where they are used. Redundant on
    # purpose: the two sides must agree, which is a cross-check no single counter
    # can provide. See `check_discard_invariants`.
    "pose_discarded_by_consumer",
    # Other discards, none of which are PnP failures.
    "observation_absent",
    "frame_no_camera_meets_min_corners",
    "interface_pnp_failed",
    "video_frame_unreadable",
    # Convergence-diagnostic guard count (plan 19.3-02, D-19.3-11). Bumped on the
    # FINAL solution evaluation of each solver stage (optimize_interface's Stage 3
    # and joint_refinement's Stage 3 intrinsic pass) -- never a running per-iteration
    # count. Because `_bump` accumulates into one caller dict threaded to both
    # stages, the value IN AGGREGATE is the cross-stage SUM, not a single stage's
    # count.
    #
    # Phase 24 (DEGEN-02) splits it on two INDEPENDENT axes, each of which
    # decomposes this same total exactly:
    #   - CAUSE: why the refractive projection failed (read off the projector's
    #     `nan_reason_out` array).
    #   - FATE:  what the residual then did (`extended` keeps a gradient,
    #     `penalized` is a flat constant with none).
    # This key equals the sum of the nine `..._cause_*` keys AND, independently,
    # the sum of the six `..._fate_*` keys. The two axes describe the SAME set of
    # observations from two angles and MUST NEVER BE ADDED TOGETHER -- summing a
    # cause column and a fate column doubles the true total.
    #
    # This key is never dropped and never renamed: the production gate and
    # `experiments/check_rerun_gates.py` read it by name. The split keys below are
    # where the diagnosis lives.
    "degenerate_observations_at_solution",
    # Phase 24 (DEGEN-02): the cause x stage, fate x stage and per-stage
    # denominator keys, built from the three closed tuples below so no key string
    # is ever spelled twice.
    *tuple(
        f"degenerate_observations_cause_{cause}__{stage}"
        for cause in _DEGENERACY_CAUSES
        for stage in _DISCARD_STAGES
    ),
    *tuple(
        f"degenerate_observations_fate_{fate}__{stage}"
        for fate in _DEGENERACY_FATES
        for stage in _DISCARD_STAGES
    ),
    # D-10: the observation denominator, produced by the same pass over the same
    # data at the same moment as the counts it is the denominator for. Never
    # derived from `n_residuals / 2` (None whenever use_sparse_jacobian=False) nor
    # from `problem_shape` totals (observations that COULD have existed).
    *tuple(f"observations_evaluated__{stage}" for stage in _DISCARD_STAGES),
)

#: Public aliases of the three closed vocabularies (see the private tuples above).
DEGENERACY_CAUSES: tuple[str, ...] = _DEGENERACY_CAUSES
DEGENERACY_FATES: tuple[str, ...] = _DEGENERACY_FATES
DISCARD_STAGES: tuple[str, ...] = _DISCARD_STAGES


def degeneracy_cause_key(cause: str, stage: str) -> str:
    """Build the flat `DISCARD_KEYS` entry for a (cause, stage) pair.

    Args:
        cause: One of `DEGENERACY_CAUSES`.
        stage: One of `DISCARD_STAGES`. `"unattributed"` is legal, not an error --
            an absent stage label is a legitimate call pattern (unit tests, direct
            calls to `joint_refinement`) and must be visible rather than merged
            into a real stage.

    Returns:
        The flat key string.

    Raises:
        ValueError: If either argument is outside its closed vocabulary. Catching
            that is what the closed vocabulary is for.
    """
    if cause not in _DEGENERACY_CAUSES:
        raise ValueError(
            f"unrecognized degeneracy cause {cause!r}; legal causes are "
            f"{list(_DEGENERACY_CAUSES)}"
        )
    if stage not in _DISCARD_STAGES:
        raise ValueError(
            f"unrecognized discard stage {stage!r}; legal stages are "
            f"{list(_DISCARD_STAGES)}"
        )
    return f"degenerate_observations_cause_{cause}__{stage}"


def degeneracy_fate_key(fate: str, stage: str) -> str:
    """Build the flat `DISCARD_KEYS` entry for a (fate, stage) pair.

    Args:
        fate: One of `DEGENERACY_FATES`.
        stage: One of `DISCARD_STAGES` (`"unattributed"` included -- see
            `degeneracy_cause_key`).

    Returns:
        The flat key string.

    Raises:
        ValueError: If either argument is outside its closed vocabulary.
    """
    if fate not in _DEGENERACY_FATES:
        raise ValueError(
            f"unrecognized degeneracy fate {fate!r}; legal fates are "
            f"{list(_DEGENERACY_FATES)}"
        )
    if stage not in _DISCARD_STAGES:
        raise ValueError(
            f"unrecognized discard stage {stage!r}; legal stages are "
            f"{list(_DISCARD_STAGES)}"
        )
    return f"degenerate_observations_fate_{fate}__{stage}"


def observations_evaluated_key(stage: str) -> str:
    """Build the flat per-stage denominator key.

    Args:
        stage: One of `DISCARD_STAGES`.

    Returns:
        The flat key string.

    Raises:
        ValueError: If `stage` is outside the closed vocabulary.
    """
    if stage not in _DISCARD_STAGES:
        raise ValueError(
            f"unrecognized discard stage {stage!r}; legal stages are "
            f"{list(_DISCARD_STAGES)}"
        )
    return f"observations_evaluated__{stage}"


#: The nine cause keys, in declaration order.
_DEGENERACY_CAUSE_KEYS: tuple[str, ...] = tuple(
    degeneracy_cause_key(cause, stage)
    for cause in _DEGENERACY_CAUSES
    for stage in _DISCARD_STAGES
)

#: The six fate keys, in declaration order.
_DEGENERACY_FATE_KEYS: tuple[str, ...] = tuple(
    degeneracy_fate_key(fate, stage)
    for fate in _DEGENERACY_FATES
    for stage in _DISCARD_STAGES
)

#: Producer-side failure keys whose total must equal `pose_discarded_by_consumer`.
_PRODUCER_FAILURE_KEYS: tuple[str, ...] = (
    "pnp_too_few_corners",
    "pnp_solve_failed",
    "pnp_initial_guess_failed",
    "pnp_nonfinite_refinement",
    "pnp_guard_rejected",
)


def _bump(stats: dict[str, int] | None, key: str, n: int = 1) -> None:
    """Increment a discard counter, or do nothing when accounting is off.

    Args:
        stats: The caller's counter dict, or None to disable accounting. When None
            this is a single identity test -- the inert default path.
        key: One of `DISCARD_KEYS`.
        n: Amount to add. Defaults to 1.
    """
    if stats is None:
        return
    stats[key] = stats.get(key, 0) + n


def check_discard_invariants(stats: dict[str, int]) -> list[str]:
    """Check the cross-checks that make the redundant counters worth carrying.

    **Scope: this is a WHOLE-RUN check.** Relation 1 below holds only when every
    producer was reached through a consumer site, which is true of a pipeline run
    and false of a direct unit-test call to `estimate_board_pose` or
    `refractive_solve_pnp`. Calling this on counters from a bare producer call will
    report a spurious producer/consumer mismatch -- use `check_denominator_only`
    there instead. Relation 2 holds unconditionally.

    Two independent relations must hold for any complete run. Both are cheap and
    both catch a whole class of instrumentation bug that no single counter can:

    1. Producer/consumer agreement (WHOLE-RUN ONLY -- see Scope). Every pose
       rejected by a producer is discarded by exactly one consumer, so the consumer
       total equals the producer total. A mismatch means a site was instrumented on
       one side only.
    2. Denominator decomposition. `pnp_attempts_total` is the sum of the refractive
       and non-refractive branch counts. A denominator that silently counts one
       branch is the failure mode that would send plan 19.2-06's differing-
       denominator halt into an input diagnosis (wrong frameset) for what is
       actually a counter-scoping bug.
    3. Cause decomposition (phase 24). `degenerate_observations_at_solution` equals
       the sum of the nine `..._cause_*` keys.
    4. Fate decomposition (phase 24). The same total equals the sum of the six
       `..._fate_*` keys. Two independent exact decompositions of one total is a
       cross-check neither axis provides alone, and it is what makes plan 24-02's
       six-column CSV self-validating by eye.
    5. Denominator sanity (phase 24). Each stage's three cause counts sum to at
       most that stage's `observations_evaluated__*`, when that denominator is
       present and non-zero.

    Relations 3-5 hold unconditionally, so they flow through
    `check_denominator_only` unchanged.

    Args:
        stats: A populated counter dict.

    Returns:
        A list of human-readable violation strings, empty when all invariants hold.
    """
    violations: list[str] = []

    consumed = stats.get("pose_discarded_by_consumer", 0)
    produced = sum(stats.get(k, 0) for k in _PRODUCER_FAILURE_KEYS)
    if consumed != produced:
        violations.append(
            f"producer/consumer mismatch: pose_discarded_by_consumer={consumed} "
            f"but producer failures sum to {produced} "
            f"({ {k: stats.get(k, 0) for k in _PRODUCER_FAILURE_KEYS} })"
        )

    total = stats.get("pnp_attempts_total", 0)
    split = stats.get("pnp_attempts_refractive", 0) + stats.get(
        "pnp_attempts_nonrefractive", 0
    )
    if total != split:
        violations.append(
            f"denominator mismatch: pnp_attempts_total={total} but "
            f"refractive+nonrefractive={split}"
        )

    merged = stats.get("degenerate_observations_at_solution", 0)

    by_cause = sum(stats.get(k, 0) for k in _DEGENERACY_CAUSE_KEYS)
    if merged != by_cause:
        violations.append(
            f"degeneracy cause split mismatch: "
            f"degenerate_observations_at_solution={merged} but the nine cause keys "
            f"sum to {by_cause}"
        )

    by_fate = sum(stats.get(k, 0) for k in _DEGENERACY_FATE_KEYS)
    if merged != by_fate:
        violations.append(
            f"degeneracy fate split mismatch: "
            f"degenerate_observations_at_solution={merged} but the six fate keys "
            f"sum to {by_fate}"
        )

    for stage in _DISCARD_STAGES:
        denominator = stats.get(observations_evaluated_key(stage), 0)
        if denominator <= 0:
            continue
        stage_causes = sum(
            stats.get(degeneracy_cause_key(cause, stage), 0)
            for cause in _DEGENERACY_CAUSES
        )
        if stage_causes > denominator:
            violations.append(
                f"degeneracy denominator mismatch for stage {stage!r}: cause counts "
                f"sum to {stage_causes} but only {denominator} observations were "
                f"evaluated"
            )

    unknown = sorted(set(stats) - set(DISCARD_KEYS))
    if unknown:
        violations.append(f"undeclared counter keys: {unknown}")

    return violations


def check_denominator_only(stats: dict[str, int]) -> list[str]:
    """Check the invariants that hold for ANY counter dict, run-scoped or not.

    The denominator decomposition and the closed-vocabulary check are true of a
    single producer call as much as of a whole run. Producer/consumer agreement is
    not -- see `check_discard_invariants`'s Scope note.

    Args:
        stats: A counter dict, possibly from a single direct producer call.

    Returns:
        A list of human-readable violation strings, empty when all hold.
    """
    return [
        v
        for v in check_discard_invariants(stats)
        if not v.startswith("producer/consumer mismatch")
    ]


TRACE_CSV_HEADER = [
    "iteration",
    "n_fev",
    "cost",
    "step_norm",
    "optimality",
    "water_z",
    "tilt_rx",
    "tilt_ry",
]


@dataclass
class TraceRow:
    """One accepted `trf` iteration's worth of per-iteration optimizer diagnostics.

    Attributes:
        iteration: scipy's accepted-iteration count (`intermediate_result.nit`).
        n_fev: Cumulative residual-function evaluation count.
        cost: `0.5 * sum(fun**2)` at this iteration (scipy's convention).
        step_norm: Euclidean norm of `x_i - x_{i-1}`; `0.0` for the first row.
        optimality: Unconstrained `||J^T f||_inf` proxy; `nan` if unavailable
            (e.g. `jac="2-point"` or a stale residual/Jacobian pair).
        water_z: Global water-surface Z parameter sliced from `x`.
        tilt_rx: Reference-camera tilt about X, or `nan` when `normal_fixed=True`.
        tilt_ry: Reference-camera tilt about Y, or `nan` when `normal_fixed=True`.
    """

    iteration: int
    n_fev: int
    cost: float
    step_norm: float
    optimality: float
    water_z: float
    tilt_rx: float
    tilt_ry: float


@dataclass
class SolverDiagnostics:
    """Terminal `least_squares` diagnostics for one solver call, filled in place.

    A mutable out-parameter: construct with all defaults (`SolverDiagnostics()`),
    pass it to a `least_squares`-wrapping function, and read the fields back after
    that function returns. `capture_solver_diagnostics` is the sole intended writer
    of these fields -- populate via that helper immediately after `least_squares`
    returns, never by reading `result.jac`/`result.fun`/`result.x` directly (see
    `capture_solver_diagnostics`'s docstring for why).

    Absent-metric convention (D-15): a metric a given call site cannot produce
    (e.g. `n_params`/`n_groups` for a site with no column-grouping structure) is
    recorded as `None` together with a `*_reason` string explaining why -- never
    silently omitted. This lets a downstream aggregator (BENCH-05) distinguish
    "not applicable here" from "failed to measure".

    Attributes:
        nfev: Residual-function evaluation count (BENCH-01). Always populated as
            an int by `capture_solver_diagnostics` at a real call site.
        njev: Jacobian evaluation count (BENCH-01). Always a populated int at this
            codebase's four in-scope call sites -- all four use `method='trf'`,
            for which SciPy populates `njev` regardless of whether `jac` is a
            callable or the string `'2-point'`. `None` occurs only for SciPy's
            `'lm'` method, which no in-scope site uses (see 19-RESEARCH.md
            Pitfall 5, corrected 2026-07-24). Do NOT document or assume `None`
            means `jac='2-point'` -- that claim was independently reproduced as
            false.
        cost: `0.5 * sum(fun**2)` at the returned solution (BENCH-01).
        optimality: SciPy's own first-order optimality measure on the final
            `OptimizeResult` (BENCH-01) -- Coleman-Li bound-scaled, distinct from
            `TraceRow.optimality`'s per-iteration unconstrained proxy.
        status: SciPy's termination status code (BENCH-01).
        message: SciPy's human-readable termination message (BENCH-01).
        ftol: Explicit function-tolerance passed to `least_squares` (BENCH-06).
        xtol: Explicit parameter-tolerance passed to `least_squares` (BENCH-06).
        gtol: Explicit gradient-tolerance passed to `least_squares` (BENCH-06).
        max_nfev_effective: The effective `max_nfev` value in force for this call,
            including SciPy's computed auto value when the caller left `max_nfev`
            unset (BENCH-06).
        max_nfev_source: One of `"explicit"`, `"scipy_auto"`, or a call-site
            specific label (e.g. `"point_refinement_200x_auto"`) describing where
            `max_nfev_effective` came from (BENCH-06). Not validated against a
            fixed enum -- any caller-supplied string is accepted.
        n_params: Packed parameter-vector length `P` for this solve, when the
            call site's structure makes it meaningful (BENCH-03). `None` with
            `n_params_reason` set when not applicable.
        n_params_reason: Explanation for why `n_params` is `None`. Populated only
            when `n_params` is `None`.
        n_groups: Number of finite-difference column groups used for this solve's
            sparse Jacobian, when applicable (BENCH-03). `None` with
            `n_groups_reason` set when not applicable.
        n_groups_reason: Explanation for why `n_groups` is `None`. Populated only
            when `n_groups` is `None`.
        n_residuals: Residual-row count `M` of this solve's Jacobian
            (`jac_sparsity.shape[0]`), when the call site built a sparsity
            structure (EXP-08). `M * n_params` is the dense Jacobian element
            count the supplement's dense/QR-regime claim is about. `None` with
            `n_residuals_reason` set when the call site has no sparsity
            structure -- the same absent-metric convention as `n_params`/
            `n_groups`.
        n_residuals_reason: Explanation for why `n_residuals` is `None`.
            Populated only when `n_residuals` is `None`.
        optimality_by_block: Per-parameter-block decomposition of `optimality`
            (DEGEN-05), keyed by the block names `build_parameter_block_slices`
            returns. Each entry carries `max_scaled` (float), `max_unscaled`
            (float), `argmax_parameter` (str, from `build_parameter_labels`) and
            `n_params` (int). `None` with `optimality_by_block_reason` set when
            the call site could not supply labels, blocks or bounds.

            **Why the decomposition exists.** `optimality` is a single scalar
            that mixes three Coleman-Li scaling regimes -- ``v = 1`` for
            unbounded extrinsics and board poses, ``v`` around 700 for
            wide-bounded intrinsics, and ``v`` around 2e-12 for a pinned slot --
            so it is NOT a like-for-like maximum across blocks. Reading it as one
            number invites attributing a large value to whichever block the
            reader already suspects. The maximum `max_scaled` over blocks equals
            `result.optimality`, since scipy reports ``norm(g * v, inf)``.
        optimality_by_block_reason: Explanation for why `optimality_by_block` is
            `None`. Populated only when it is `None`.
        parameters_at_bound: Which parameters terminated ON a bound rather than
            at an interior minimum (D-16), read from scipy's own `active_mask`.
            Each entry carries `parameter` (str label), `bound` (`"lower"` or
            `"upper"`), `interval_width` (float), `gap` (float) and
            `classification` (`"pinned"` or `"traveled"`). `None` with
            `parameters_at_bound_reason` set when the call site could not supply
            labels, blocks or bounds.

            **The classification is load-bearing.** A pinned parameter is
            legitimately at its bound by construction, so a detector that flagged
            "on a bound" without separating pinned-by-request from
            ran-into-a-limit would fire on E1's non-refractive arm every single
            run and be trained away, exactly as the always-red gate in
            `knowledge-base.md` was. The bound-interval width discriminates them
            cheaply.
        parameters_at_bound_reason: Explanation for why `parameters_at_bound` is
            `None`. Populated only when it is `None`.
    """

    nfev: int | None = None
    njev: int | None = None
    cost: float | None = None
    optimality: float | None = None
    status: int | None = None
    message: str | None = None
    ftol: float | None = None
    xtol: float | None = None
    gtol: float | None = None
    max_nfev_effective: int | None = None
    max_nfev_source: str | None = None
    n_params: int | None = None
    n_params_reason: str | None = None
    n_groups: int | None = None
    n_groups_reason: str | None = None
    n_residuals: int | None = None
    n_residuals_reason: str | None = None
    optimality_by_block: dict[str, dict] | None = None
    optimality_by_block_reason: str | None = None
    parameters_at_bound: list[dict] | None = None
    parameters_at_bound_reason: str | None = None


def build_parameter_labels(
    camera_order: list[str],
    frame_order: list[int],
    reference_camera: str,
    refine_intrinsics: bool = False,
    normal_fixed: bool = True,
    shared_interface: bool = True,
) -> list[str]:
    """Build a human-readable name for each entry of the packed parameter vector.

    Mirrors `_optim_common.pack_params`'s layout exactly (same argument order, same
    conditional blocks) so that `labels[i]` names `x[i]` for any `x` produced by
    `pack_params` with the same arguments. This is the only way the conditioning
    correlation matrix's rows/columns become readable -- e.g. finding `water_z`
    and each camera's `_tvec_z` to inspect the camera-height / water_z coupling.

    Args:
        camera_order: Ordered list of camera names, matching `pack_params`.
        frame_order: Ordered list of frame indices, matching `pack_params`.
        reference_camera: Name of the reference camera (skipped in extrinsics
            packing).
        refine_intrinsics: Whether intrinsics are included in the parameter
            vector.
        normal_fixed: If False, the first two labels are the reference camera's
            tilt rx/ry.
        shared_interface: If True (default), a single `water_z` label is emitted.
            If False, one `{cam}_water_z` label per camera in camera_order is
            emitted, matching pack_params' per-camera emission order.

    Returns:
        List of parameter names, one per entry of the packed vector, in the
        same order `pack_params` emits values.
    """
    labels: list[str] = []

    if not normal_fixed:
        labels.extend(["ref_tilt_rx", "ref_tilt_ry"])

    for cam_name in camera_order:
        if cam_name == reference_camera:
            continue
        labels.extend(
            [
                f"{cam_name}_rvec_x",
                f"{cam_name}_rvec_y",
                f"{cam_name}_rvec_z",
                f"{cam_name}_tvec_x",
                f"{cam_name}_tvec_y",
                f"{cam_name}_tvec_z",
            ]
        )

    if shared_interface:
        labels.append("water_z")
    else:
        for cam_name in camera_order:
            labels.append(f"{cam_name}_water_z")

    for frame_idx in frame_order:
        labels.extend(
            [
                f"frame{frame_idx}_rvec_x",
                f"frame{frame_idx}_rvec_y",
                f"frame{frame_idx}_rvec_z",
                f"frame{frame_idx}_tvec_x",
                f"frame{frame_idx}_tvec_y",
                f"frame{frame_idx}_tvec_z",
            ]
        )

    if refine_intrinsics:
        for cam_name in camera_order:
            labels.extend(
                [
                    f"{cam_name}_fx",
                    f"{cam_name}_fy",
                    f"{cam_name}_cx",
                    f"{cam_name}_cy",
                ]
            )

    return labels


def capture_solver_diagnostics(
    result,
    diagnostics_out: SolverDiagnostics | None,
    *,
    ftol: float,
    xtol: float,
    gtol: float,
    max_nfev_effective: int | None,
    max_nfev_source: str,
    n_params: int | None = None,
    n_groups: int | None = None,
    n_params_reason: str | None = None,
    n_groups_reason: str | None = None,
    n_residuals: int | None = None,
    n_residuals_reason: str | None = None,
    parameter_labels: list[str] | None = None,
    parameter_blocks: dict[str, slice] | None = None,
    bounds: tuple | None = None,
) -> None:
    """Populate a `SolverDiagnostics` in place from a returned `OptimizeResult`.

    Must be called only after `least_squares` returns.

    **Pitfall 4, narrowed by phase 24 rather than silently violated.**
    `result.fun` (length M) and `result.jac` (M x P) remain FORBIDDEN here:
    retaining them inflates the very peak-memory measurement BENCH-02 depends on
    being honest. `result.grad`, `result.active_mask` and `result.x` are all
    length P, and phase 24 reads them -- but only to reduce them immediately to
    Python scalars and strings via `float()`/`int()`/`str()` at the point of
    extraction, so no numpy array ever survives on the dataclass.

    `njev` is read defensively via `getattr` for reuse-safety, but at every one
    of this codebase's four in-scope call sites (all `method='trf'`) it is
    always populated as an int -- the `None` branch is not expected there; see
    19-RESEARCH.md Pitfall 5, corrected.

    No-op when `diagnostics_out is None`, so every call site can call this
    unconditionally regardless of whether the caller opted into diagnostics
    capture.

    Args:
        result: The final `scipy.optimize.OptimizeResult` from `least_squares`.
        diagnostics_out: The `SolverDiagnostics` instance to mutate in place, or
            `None` to skip capture entirely.
        ftol: Explicit function-tolerance passed to `least_squares` (BENCH-06).
        xtol: Explicit parameter-tolerance passed to `least_squares` (BENCH-06).
        gtol: Explicit gradient-tolerance passed to `least_squares` (BENCH-06).
        max_nfev_effective: The effective `max_nfev` in force for this call,
            including SciPy's computed auto value when left unset (BENCH-06).
        max_nfev_source: Provenance label for `max_nfev_effective`, e.g.
            `"explicit"` or `"scipy_auto"` (BENCH-06).
        n_params: Packed parameter-vector length `P`, when applicable (BENCH-03).
        n_groups: Finite-difference column-group count, when applicable
            (BENCH-03).
        n_params_reason: Explanation recorded when `n_params` is `None` (D-15).
        n_groups_reason: Explanation recorded when `n_groups` is `None` (D-15).
        n_residuals: Residual-row count `M` of this solve's Jacobian, when
            applicable (EXP-08).
        n_residuals_reason: Explanation recorded when `n_residuals` is `None`
            (D-15).
        parameter_labels: Labels from `build_parameter_labels`, packed with the
            same arguments as the solved vector. Required for
            `optimality_by_block` and `parameters_at_bound`.
        parameter_blocks: Block slices from
            `_optim_common.build_parameter_block_slices`, packed with the same
            arguments. Required for the same two fields.
        bounds: The `(lower, upper)` tuple passed to `least_squares`. Required
            for the same two fields.

            When any of these three is `None`, both new fields are recorded as
            `None` with a `*_reason` naming what was missing (D-15).
    """
    if diagnostics_out is None:
        return

    diagnostics_out.nfev = int(result.nfev)
    njev = getattr(result, "njev", None)
    diagnostics_out.njev = int(njev) if njev is not None else None
    diagnostics_out.cost = float(result.cost)
    diagnostics_out.optimality = float(result.optimality)
    diagnostics_out.status = int(result.status)
    diagnostics_out.message = str(result.message)

    diagnostics_out.ftol = ftol
    diagnostics_out.xtol = xtol
    diagnostics_out.gtol = gtol
    diagnostics_out.max_nfev_effective = max_nfev_effective
    diagnostics_out.max_nfev_source = max_nfev_source
    diagnostics_out.n_params = n_params
    diagnostics_out.n_groups = n_groups
    diagnostics_out.n_params_reason = n_params_reason
    diagnostics_out.n_groups_reason = n_groups_reason
    diagnostics_out.n_residuals = n_residuals
    diagnostics_out.n_residuals_reason = n_residuals_reason

    missing = [
        name
        for name, value in (
            ("parameter_labels", parameter_labels),
            ("parameter_blocks", parameter_blocks),
            ("bounds", bounds),
        )
        if value is None
    ]
    if missing:
        reason = (
            f"call site supplied no {', '.join(missing)}; the packed-vector "
            f"layout is unavailable at this site"
        )
        diagnostics_out.optimality_by_block = None
        diagnostics_out.optimality_by_block_reason = reason
        diagnostics_out.parameters_at_bound = None
        diagnostics_out.parameters_at_bound_reason = reason
        return

    diagnostics_out.optimality_by_block = _decompose_optimality(
        result, parameter_labels, parameter_blocks, bounds
    )
    diagnostics_out.optimality_by_block_reason = None
    diagnostics_out.parameters_at_bound = _detect_parameters_at_bound(
        result, parameter_labels, bounds
    )
    diagnostics_out.parameters_at_bound_reason = None


#: A bound interval this narrow (relative to its own magnitude) is a pin by
#: request, not a limit the solver travelled into. The probe measured the pinned
#: `water_z` slot at a bound gap of 2.000177801164682e-12 with `active_mask = 1`,
#: while every other block reported 0.
_PINNED_INTERVAL_RTOL = 1e-9


def _coleman_li_scaling(
    x: NDArray[np.float64],
    grad: NDArray[np.float64],
    lower: NDArray[np.float64],
    upper: NDArray[np.float64],
) -> NDArray[np.float64]:
    """Compute scipy `trf`'s Coleman-Li scaling vector `v`, elementwise.

    `v = upper - x` where the gradient points toward the upper bound and that
    bound is finite; `v = x - lower` where it points toward a finite lower bound;
    `1.0` otherwise. scipy reports `optimality` as `norm(grad * v, inf)`, so this
    is what makes the per-block maxima add up to the reported scalar.
    """
    v = np.ones_like(x, dtype=np.float64)
    toward_upper = (grad < 0) & np.isfinite(upper)
    toward_lower = (grad > 0) & np.isfinite(lower)
    v[toward_upper] = upper[toward_upper] - x[toward_upper]
    v[toward_lower] = x[toward_lower] - lower[toward_lower]
    return v


def _decompose_optimality(
    result,
    parameter_labels: list[str],
    parameter_blocks: dict[str, slice],
    bounds: tuple,
) -> dict[str, dict]:
    """Attribute `result.optimality` to each structural parameter block."""
    x = np.asarray(result.x, dtype=np.float64)
    grad = np.asarray(result.grad, dtype=np.float64)
    lower = np.asarray(bounds[0], dtype=np.float64)
    upper = np.asarray(bounds[1], dtype=np.float64)

    scaled = np.abs(grad * _coleman_li_scaling(x, grad, lower, upper))
    unscaled = np.abs(grad)

    by_block: dict[str, dict] = {}
    for name, block in parameter_blocks.items():
        block_scaled = scaled[block]
        if block_scaled.size == 0:
            continue
        argmax = int(np.argmax(block_scaled))
        by_block[name] = {
            "max_scaled": float(block_scaled[argmax]),
            "max_unscaled": float(np.max(unscaled[block])),
            "argmax_parameter": str(parameter_labels[block.start + argmax]),
            "n_params": int(block_scaled.size),
        }
    return by_block


def _detect_parameters_at_bound(
    result,
    parameter_labels: list[str],
    bounds: tuple,
) -> list[dict]:
    """List parameters scipy's `active_mask` reports as terminating on a bound.

    D-16. `active_mask` is `-1` at a lower bound, `+1` at an upper bound and `0`
    in the interior, so this is a plumbing job rather than a detection problem --
    the signal is already computed by scipy on the real solve.
    """
    x = np.asarray(result.x, dtype=np.float64)
    active_mask = np.asarray(result.active_mask)
    lower = np.asarray(bounds[0], dtype=np.float64)
    upper = np.asarray(bounds[1], dtype=np.float64)

    at_bound: list[dict] = []
    for i in np.flatnonzero(active_mask):
        i = int(i)
        is_lower = active_mask[i] < 0
        active_bound = lower[i] if is_lower else upper[i]
        interval_width = float(upper[i] - lower[i])
        # An infinite interval is never a pin. Without the isfinite guard,
        # a one-sided bound gives `inf <= 1e-9 * inf` -> `inf <= inf` -> True,
        # reporting the WIDEST possible interval as pinned-by-request. That is
        # silent in exactly the direction D-16 exists to prevent: it trains the
        # signal away. Scale on both ends, not just `lower`, so a pin at a large
        # upper bound with a zero lower bound is not measured against 1.0.
        scale = max(1.0, abs(float(lower[i])), abs(float(upper[i])))
        pinned = np.isfinite(interval_width) and (
            interval_width <= _PINNED_INTERVAL_RTOL * scale
        )
        at_bound.append(
            {
                "parameter": str(parameter_labels[i]),
                "bound": "lower" if is_lower else "upper",
                "interval_width": interval_width,
                "gap": float(abs(x[i] - active_bound)),
                "classification": "pinned" if pinned else "traveled",
            }
        )
    return at_bound


class OptimizerObserver:
    """Read-only observer for a single `least_squares` bundle-adjustment call.

    Attach via `wrap_fun`/`wrap_jac`/`callback` before calling `least_squares`, then call
    `on_solution(result)` afterward and `write_trace_csv(path)` to persist the trace.

    Never retains a reference to a Jacobian matrix -- only a scalar `optimality` value is
    cached between the `jac` wrapper and the `callback`.
    """

    def __init__(
        self,
        stage: str,
        water_z_index: int | None = None,
        normal_fixed: bool = True,
        conditioning: bool = False,
    ) -> None:
        """Create an observer for one bundle-adjustment stage.

        Args:
            stage: Human-readable stage name (e.g. "stage3", "stage3_rerun",
                "stage3_intrinsic_pass"), used only for logging/debugging context.
            water_z_index: Index of `water_z` within the packed parameter vector `x`.
                If `None`, `water_z`/`tilt_rx`/`tilt_ry` are recorded as `nan`. Set via
                `configure_layout` if not known at construction time.
            normal_fixed: If `False`, `x[0]`/`x[1]` are the reference camera's tilt
                rx/ry and are recorded; if `True`, both are `nan`.
            conditioning: If `True`, `on_solution` computes Jacobian conditioning
                diagnostics (singular-value spectrum, condition number, parameter
                correlation) from `result.jac`. If `False`, `on_solution` is a no-op.
        """
        self.stage = stage
        self.water_z_index = water_z_index
        self.normal_fixed = normal_fixed
        self.conditioning = conditioning
        self.parameter_labels: list[str] | None = None
        self.conditioning_report: ConditioningReport | None = None

        self.rows: list[TraceRow] = []

        self._x_prev: NDArray[np.float64] | None = None
        self._f_cached: NDArray[np.float64] | None = None
        self._x_cached: NDArray[np.float64] | None = None
        self._last_optimality: float = math.nan

    def configure_layout(
        self,
        water_z_index: int,
        normal_fixed: bool,
        parameter_labels: list[str] | None = None,
    ) -> None:
        """Set the parameter-vector layout indices used to slice interface params.

        Args:
            water_z_index: Index of `water_z` within the packed parameter vector.
            normal_fixed: Whether the reference camera's tilt is fixed (excluded
                from the parameter vector).
            parameter_labels: Optional per-parameter names (from
                `build_parameter_labels`) used to label the conditioning
                correlation matrix. Ignored unless `conditioning=True`.
        """
        self.water_z_index = water_z_index
        self.normal_fixed = normal_fixed
        self.parameter_labels = parameter_labels

    def wrap_fun(self, fun: Callable) -> Callable:
        """Wrap a residual function, caching its result for the optimality proxy.

        Args:
            fun: The inner residual function, called as `fun(x, *args, **kwargs)`.

        Returns:
            A wrapper with the same call signature that returns the inner result
            unchanged, after caching a copy of `(x, residuals)`.
        """

        @wraps(fun)
        def wrapped(x, *args, **kwargs):
            result = fun(x, *args, **kwargs)
            self._x_cached = np.array(x, copy=True)
            self._f_cached = np.array(result, copy=True)
            return result

        return wrapped

    def wrap_jac(self, jac):
        """Wrap a Jacobian callable, computing the optimality proxy as a side effect.

        Args:
            jac: The inner Jacobian callable (`jac(x, *args, **kwargs) -> J`), or the
                string `"2-point"` when finite differences are used instead of an
                explicit callable.

        Returns:
            A wrapper with the same call signature that returns `J` unchanged, after
            computing and caching `||J^T f||_inf` (or leaving it `nan` if the cached
            residual does not match `x`). If `jac` is a string, it is returned
            unchanged and `optimality` stays `nan` for every row.
        """
        if isinstance(jac, str):
            return jac

        @wraps(jac)
        def wrapped(x, *args, **kwargs):
            J = jac(x, *args, **kwargs)
            if self._f_cached is not None and np.array_equal(x, self._x_cached):
                if hasattr(J, "dot") and not isinstance(J, np.ndarray):
                    # Sparse matrix: J.T.dot(f) avoids densifying J.
                    grad = J.T.dot(self._f_cached)
                else:
                    grad = J.T @ self._f_cached
                self._last_optimality = float(np.linalg.norm(grad, np.inf))
            else:
                self._last_optimality = math.nan
            return J

        return wrapped

    def callback(self, intermediate_result) -> None:
        """scipy `least_squares(callback=...)` hook; fired once per accepted iteration.

        Args:
            intermediate_result: `scipy.optimize.OptimizeResult` with `x`, `fun`,
                `nit`, `nfev`, `cost` populated (per the scipy 1.16+ `callback`
                contract). No other fields are guaranteed to be present.
        """
        x = np.asarray(intermediate_result.x)

        if self._x_prev is None:
            step_norm = 0.0
        else:
            step_norm = float(np.linalg.norm(x - self._x_prev))
        self._x_prev = np.array(x, copy=True)

        water_z = math.nan
        tilt_rx = math.nan
        tilt_ry = math.nan
        if self.water_z_index is not None:
            water_z = float(x[self.water_z_index])
            if not self.normal_fixed:
                tilt_rx = float(x[0])
                tilt_ry = float(x[1])

        self.rows.append(
            TraceRow(
                iteration=int(intermediate_result.nit),
                n_fev=int(intermediate_result.nfev),
                cost=float(intermediate_result.cost),
                step_norm=step_norm,
                optimality=self._last_optimality,
                water_z=water_z,
                tilt_rx=tilt_rx,
                tilt_ry=tilt_ry,
            )
        )

    def on_solution(self, result) -> None:
        """Compute Jacobian conditioning diagnostics at the solution, if enabled.

        Called once, immediately after `least_squares` returns, while `result.jac`
        is still alive in the caller's scope. When `self.conditioning` is `True`,
        computes a `ConditioningReport` via `compute_conditioning` and stores it
        on `self.conditioning_report` -- only that small `(n, n)` report survives;
        `result`/`result.jac` are never retained as attributes on this observer.

        Args:
            result: The final `scipy.optimize.OptimizeResult` from `least_squares`.

        Raises:
            ConditioningMemoryError: Re-raised (with this observer's stage name
                prefixed to the message) if the conditioning computation's
                analytic memory pre-check refuses the allocation. This
                propagates all the way out -- the caller must not narrow the
                metric to keep the run alive.
        """
        if not self.conditioning:
            return

        # Local import: avoids a calibration -> validation import at module load.
        from aquacal.validation.conditioning import (
            ConditioningMemoryError,
            compute_conditioning,
        )

        try:
            self.conditioning_report = compute_conditioning(
                result.jac,
                parameter_names=self.parameter_labels,
            )
        except ConditioningMemoryError as exc:
            raise ConditioningMemoryError(f"[{self.stage}] {exc}") from exc

    def write_trace_csv(self, path: Path) -> None:
        """Write the captured per-iteration trace to a CSV file.

        Args:
            path: Destination file path. Parent directories are created if needed.
                If `path` already exists, a warning is logged before overwriting.
        """
        path = Path(path)
        warn_if_overwriting(path)
        path.parent.mkdir(parents=True, exist_ok=True)

        if not self.rows:
            logger.warning(
                "OptimizerObserver for stage '%s' recorded zero accepted "
                "iterations; writing header-only trace to %s.",
                self.stage,
                path,
            )

        with open(path, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(TRACE_CSV_HEADER)
            for row in self.rows:
                writer.writerow(
                    [
                        row.iteration,
                        row.n_fev,
                        row.cost,
                        row.step_norm,
                        row.optimality,
                        row.water_z,
                        row.tilt_rx,
                        row.tilt_ry,
                    ]
                )
