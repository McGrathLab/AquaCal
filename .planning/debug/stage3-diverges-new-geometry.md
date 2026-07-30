---
status: awaiting_human_verify
blocked_on: "user decision -- E2 shows 10 Stage-2 PnP guard rejections, so its
  numbers can move; whether to re-run E2 is the user's call"
trigger: "Stage 3 refractive bundle adjustment diverges (RMS 12.8-150 px, first-order optimality up to 2.4e6) on plausible synthetic rig geometries instead of converging to the expected ~0.7 px. Goal is to fix the underlying library weakness, NOT to work around it by retuning experiment geometry constants."
created: 2026-07-30
updated: 2026-07-30
phase: 19.2-experiment-execution-and-provenance
---

# Debug: Stage 3 diverges on redesigned grid geometry

## Symptoms

**Expected:** Stage 3 converges to ~0.7 px reprojection RMS with first-order
optimality ~0.005, as the OLD grid geometry did on all nine E4 cells.

**Actual:** Solves diverge. Optimality reaches 4.3e4 to 2.4e6; RMS reaches
12.8 px and, in one variant, 150 px. `xtol` termination fires (step collapses)
while the gradient is still enormous.

**Error messages:** None. No exception is raised — the solver reports success
via `xtol` termination. The failure is visible ONLY in the optimality column.

**Timeline:** Introduced by the D-27/D-28/D-29 grid-family geometry redesign
(plan 19.2-18, merged in gap wave 2). The OLD geometry converged on all nine
cells. Discovered when plan 19.2-21 re-ran E4's grid on the new geometry.

**Reproduction (~7 min):** `scratchpad/bisect_geometry.py` — 8 cameras x 50
frames, seed 42. Reproduces the production failure to the digit: optimality
4.347e4 vs the committed `benchmark.json`'s 43466.96.

## Production evidence (plan 19.2-21, unmerged)

| cell | optimality | RMS | verdict |
|---|---|---|---|
| 8x50 | 4.3e4 | 12.8 px | diverged |
| 8x100 | 1.6e10 | 4.6 px | diverged |
| 12x100 | 6.4e9 | **0.79 px** | diverged behind a GOOD RMS |
| 16x100 | 2.4e4 | 0.71 px | diverged behind a GOOD RMS |
| 12x50 | 0.0055 | 0.85 px | converged |
| 16x50 | 0.0087 | 0.92 px | converged |

`12x100` is the important row: a publishable-looking 0.79 px RMS sitting on
optimality 6.4e9. Phase 19.1 precedent — E7's missing-refraction-params defect
was caught by optimality 1.5e11 and NOT by the science numbers.

## Geometry bisect (8x50, seed 42) — all variants vary only
## `build_grid_scenario` kwargs, no source edits

| variant | depth below water | optimality | RMS | verdict |
|---|---|---|---|---|
| control (all new) | 0.10-0.95 m | 4.35e4 | 14.78 px | broken |
| water at 0.15 (same standoff) | 0.98-1.83 m | 0.0018 | 0.497 px | fixed |
| depth_range (1.5, 2.4) | 0.50-1.35 m | 0.0020 | 0.500 px | fixed |
| depth_range (2.0, 2.9) | 1.00-1.85 m | 2.39e6 | 150.3 px | broken, worse |
| xy_extent 0.15 (old) | 0.10-0.95 m | 0.0017 | 0.500 px | fixed |
| spacing 0.1 (old) | 0.10-0.95 m | 0.0028 | 0.499 px | fixed |

## Eliminated

- hypothesis: Interface tilt estimation (`normal_fixed=False`) destabilises the
  solve.
  evidence: The OLD grid ALSO ran `normal_fixed=False` and converged on all nine
  cells (optimality 0.0025-0.0136). Confirmed from the committed
  `benchmark_grid.csv` on main.

- hypothesis: Near-surface board poses (shallowest ~0.069 m below the interface)
  cause weak observability.
  evidence: `old_xy_extent` and `old_spacing` keep the IDENTICAL 0.10-0.95 m
  depth-below-interface band as the broken control and converge fine.

- hypothesis: The board is too deep / too far from the cameras.
  evidence: `depth_range (2.0, 2.9)` is deeper than a passing variant and fails
  WORSE. Behaviour is NON-MONOTONIC in depth: (1.1,2.0) fail, (1.5,2.4) pass,
  (2.0,2.9) fail. A genuine geometric property would not do this.

- hypothesis: Insufficient observing-camera coverage per frame.
  evidence: A passing variant has `min=1` observing camera; the worst failing
  variant has `min=4` and the best median coverage in the table.

## Current Focus (fourth continuation session, 2026-07-30)

status: executing the user's three decisions. NOTHING COMMITTED; HEAD is still
  35d76a6828550a5a81d47e7eb820f9e34cdb2fe3.

next_action: AWAIT USER DECISION on whether to re-run E2. The Stage-2-only
  rejection count on E2's release frameset is **10 of 3538 calls** -- NON-ZERO,
  so fix #2 CAN have moved E2's numbers and the §3 hard-stop risk is live. Per
  the user's own framing this is a decision for the user, not something to act
  on. Everything else is done and verified.

### Decision 1 — above-interface penalty REMOVED, and re-verified

`ABOVE_INTERFACE_PENALTY_PX_PER_M` and its use are DELETED (not zeroed).
`_extend_invalid_projections` now takes `(camera, points_3d)` and returns only
the pinhole extension. The rationale is recorded in `Resolution.fix_rationale`
as the C1/optimality argument; the accuracy and monotonicity measurements are
recorded there as corroboration, not as the ground.

Also corrected, since the claim is now false: the renamed regression test
`test_cost_grows_with_height_above_interface` (was
`test_penalty_grows_with_height_above_interface`), whose docstring now states
that the restoring force comes from the continuation and that a hinge is
deliberately absent.

**(a) Six bisect variants, 8 cameras x 50 frames, seed 42, instrumented**
(`scratchpad/sweep_nopenalty.log`) — ALL FULL RANK:

    variant                    cond   rank      sv_min   init_err   opt         rms     ext-branch hits
    control_all_new            1271   345/345   84.26    0.9444 m   0.0009103   0.500   10942 calls / 108824 obs
    deep_water_same_standoff   1007   345/345   104      0.0066 m   0.003124    0.498   0 / 0
    board_deeper_1.5_2.4       1796   345/345   61.12    0.0229 m   0.002332    0.501   0 / 0
    board_deeper_2.0_2.9       2510   345/345   45.99    0.0066 m   0.005471    0.500   0 / 0
    old_xy_extent              1227   345/345   106.3    0.0265 m   0.001719    0.501   0 / 0
    old_spacing                1461   345/345   87.27    0.0040 m   0.002750    0.499   0 / 0

Optimality 9.1e-4 to 5.5e-3, i.e. ~1e-3 on every variant. Bar (a) MET.

**(b) Previously-converging variants UNCHANGED, by instrumented branch-hit
count — measured, not asserted.** Same run. The five variants that do not enter
the extension branch report a MEASURED zero hit count over the whole solve
(every iteration, not just at x0), and every reported digit of
`deep_water_same_standoff`, `board_deeper_1.5_2.4`, `old_xy_extent` and
`old_spacing` is identical to the with-penalty sweep in `sweep_final.log`
(0.003124, 0.002332, 0.001719, 0.002750). Removing the penalty is therefore
provably inert on them: the code that changed is not executed. Only
`control_all_new` -- the variant the fix exists for, 10942 branch entries --
moves, 0.002211 -> 0.0009103, i.e. converges BETTER. Bar (b) MET on the same
terms the third session met it.

**(c) `~/anaconda3/envs/AquaCal/python.exe -m pytest tests/ -m "not slow" -q`**
(`scratchpad/pytest_notslow_nopenalty.log`):

    1109 passed, 6 skipped, 39 deselected  (179 s)   0 failed

Against the 1106 / 6 / 39 baseline: +3 collected, all three the new
`TestInvalidProjectionKeepsGradient` regression tests. Skips and deselects
unchanged. The two E3 failures the third session left standing are resolved by
Decision 2 below, honestly and without weakening the gate. `ruff check` and
`ruff format --check` clean over `src/`, `tests/` and `experiments/`.

### Decision 2 — E3 declared constant CORRECTED (not adjusted to pass)

The row's key stays `invalid_tir_penalty_px` (it is a CSV primary key with
downstream provenance), but everything the row ASSERTS now matches the code:

  - **claim** was "Invalid/TIR configurations take a fixed 100 px penalty".
    That is false: TIR, above-interface and camera-below-interface observations
    are now continued with the pinhole projection. It now reads: a projection
    with no continuous extension -- the point lies behind the camera -- takes a
    fixed 100 px penalty; every other unprojectable observation is continued
    with the plain pinhole projection instead.
  - **source** moves from `...compute_residuals` to
    `...INVALID_PROJECTION_PENALTY_PX`, the constant that actually holds it.
  - **read_via / accessor** moves from `source_regex` to a new `attribute`, and
    `_invalid_tir_penalty`'s regex over `inspect.getsource(compute_residuals)`
    is replaced by a live read of the module constant. Its docstring claimed
    "No callable or signature surface exposes this value"; fix #1 gave the value
    a name, so that claim was itself false and is corrected.
  - The structural gate is TIGHTENED, not weakened:
    `source_regex_count == 2` becomes `== 1`, because
    `register_auxiliary_camera`'s `f_scale=` literal is now the only value with
    no live surface. The test is renamed and documents that the ceiling may only
    be raised by demonstrating a new value has no live surface either.

`experiments/e3_derived_quantities.py` needed NO edit -- it only renders the
table. Rendered in-process: 9 rows, all PASS.
`tests/unit/test_experiments_e3_constants.py` + `tests/unit/test_experiments_e3.py`:
46 passed.

**Consequence to carry forward:** `experiments/results/code_constants.csv` on
disk is now STALE in its `claim`, `source` and `read_via` columns for that row.
It is a committed experiment artifact, so it was deliberately NOT hand-edited --
E3 must be re-run to regenerate it (~10 s).

### Decision 3 — E2 Stage-2-only rejection count: **10, NON-ZERO**

`scratchpad/e2_stage2_rejections.py` -> `scratchpad/e2_stage2_rejections.log`.
Release frameset (`Desktop/Aqua/AquaCal/release_calibration/config.yaml`), with
`output_dir` redirected into the scratchpad and `pipeline.optimize_interface`
replaced by a sentinel raise, so Stage 3 never started and no committed E2
artifact was touched. Ran Stage 1 + Stage 2 only.

    total refractive_solve_pnp calls : 3538
    returned None                    : 10
    pre-existing (solvePnP failed)   : 0
    NEW GUARD rejections             : 10

Attribution is exact, not inferred: `refractive_solve_pnp` has exactly three
return-None paths (pre-existing `estimate_board_pose` failure; the new
non-finite check; the new self-check), so a None whose `estimate_board_pose`
succeeds is attributable to the new guard. All ten pre-existing paths were
clear, so all ten Nones are the new guard.

Every rejected observation is near-minimal on a 12x9 board: eight had 12
corners, two had 8. That is the same signature as the synthetic blowup (8
corners, the dataset minimum), and it confirms the third session's prediction
that real footage carries MORE such views than synthetic, not fewer.

**Consequence:** fix #2 changes E2's Stage-2 output, so E2's numbers CAN move
and the §3 hard-stop risk is live. Per the user's instruction this is reported
and NOT acted on: whether to re-run E2 is a decision for the user.

---

## Current Focus (third continuation session, 2026-07-30)

status: investigating the two blocking open items. NOTHING COMMITTED; HEAD is
  still 35d76a6828550a5a81d47e7eb820f9e34cdb2fe3.

hypothesis (ITEM 1): the fix-#1-alone anti-improvement on `board_deeper_2.0_2.9`
  is NOT a water_z null space. It is the ABOVE_INTERFACE penalty being LINEAR
  and UNBOUNDED, fed board poses ~5.3e9 m above the interface by a blown-up
  Stage 2. The old flat clamp capped those same rows at 100 px.
test: fix-#1-only isolation (extrinsics.py at HEAD, restored afterwards from a
  sha256-verified backup); Jacobian column-norm attribution by parameter block
  at x0 and at the final iterate; residual composition at x0.
expecting: near-zero columns concentrated in the BLOWN-UP cameras and their
  frames, water_z column norm far from zero, and residual magnitudes ~1e12 px.
next_action: AWAIT USER DECISION on whether to drop
  `ABOVE_INTERFACE_PENALTY_PX_PER_M` (evidence below; NOT applied). Both
  blocking items are answered. Nothing in the working tree was changed by this
  session -- `git diff --stat` is byte-identical to the handover
  (+91/+27/+25/+20/+2/+16/+187) and HEAD is still 35d76a6.

### ITEM 1 — the coordinator's premise is REFUTED, and the mechanism is found

**Premise check (fresh, independent re-measurement of the current tree,
`scratchpad/sweep_session3.log`):**

    variant                    cond    rank      sv_min   init_err   opt        rms
    control_all_new            1271    345/345   84.26    0.9444 m   0.002211   0.500
    deep_water_same_standoff   1007    345/345   104      0.0066 m   0.003124   0.498
    board_deeper_1.5_2.4       1796    345/345   61.12    0.0229 m   0.002332   0.501
    board_deeper_2.0_2.9       2510    345/345   45.99    0.0066 m   0.005471   0.500
    old_xy_extent              1227    345/345   106.3    0.0265 m   0.001719   0.501
    old_spacing                1461    345/345   87.27    0.0040 m   0.002750   0.499

Every digit reproduces `sweep_final.log`. `board_deeper_2.0_2.9` on the CURRENT
tree is **rank 345/345, cond 2510, optimality 0.005471, final camera-centre
error 0.0021 m**. The cited rank 58 / cond 2.415e17 / optimality 1.448e7 are the
**fix-#1-only** intermediate state, exactly as the handover said. Reproduced
independently under a fix-#1-only isolation (`scratchpad/item1_fix1only.log`):
`opt=1.44824e+07 cond=2.415e+17 rank=58/345`.

**The fix-#1-alone anti-improvement — MECHANISM CONFIRMED, and it is NOT the
hypothesised water_z null space.**

Column-norm attribution by parameter block at x0 and at the final iterate under
fix #1 alone (`scratchpad/item1_fix1only.log`):

  - `water_z` column norm is **6379 at x0 and 29252 at the final iterate** --
    nowhere near zero. The water_z column is NOT in the null space. Hypothesis
    REFUTED.
  - The near-zero columns belong to the **blown-up cameras** (cam2/3/5/6/7, the
    ones Stage 2 places 8.98e8 - 1.03e10 m from the origin) and to the frames
    they dominate: 208 of 224 near-zero columns at the final iterate are
    board-pose columns spread over 47 of 50 frames.
  - Direct cause, measured at x0 (`scratchpad/item1_resid_composition.py`):

        fix #1 only  : Stage-2 |C| = cam5 1.034e10 m, cam6 5.418e9, cam7 5.285e9
                       worst board-pose above-interface violation = 5,288,728,032 m
                       => penalty term = 1000 px/m * 5.29e9 m = 5.28873e+12 px
                       max|r| = 5.28873e12, rms = 2.008e12, cost = 9.68e28
                       21,190 of 48,018 residual rows exceed 1e9
        both fixes   : Stage-2 |C| max 0.957 m
                       worst violation = 0.0 m over ALL 50 frames
                       max|r| = 5.42 px, rms = 0.877, cost = 1.84e4
                       0 rows exceed 1e6

**So the anti-improvement is this:** `ABOVE_INTERFACE_PENALTY_PX_PER_M` is
LINEAR and UNBOUNDED. Under fix #1 alone, Stage 2 hands Stage 3 board poses
5.3e9 m above the interface, and the penalty turns 44% of the residual rows into
~1e12 px values. The old flat clamp capped those same rows at exactly 100 px.
The Jacobian's dynamic range then spans ~1e13 and everything that is not one of
those rows is numerically invisible -- hence rank 58 and optimality 1.45e7.
Comparing 2.39e6 against 1.448e7 is not comparing two solves: it is comparing
two different residual SCALES on the same catastrophic divergence (rms 150 px
vs 6.97e11 px). Neither iterate is meaningful.

**Second finding: fix #1 does NOT restore rank when the invalidity is
camera-side.** The pinhole extension's derivative scales as f/Z. At Z ~ 1e10 m
that is ~1e-7 px/m, numerically zero at any relative tolerance -- which is why
16 camera columns for cam2/3/5/6/7 are still near-zero at the final iterate.

**Third finding: the Resolution's smoothness claim NEEDS QUALIFYING (corrected
below).** Measured at the fix-#1-only final iterate: of 10,362 invalid
observations, **6,992 (67%) carry a ZERO above-interface penalty**, because
their invalidity is camera-side (`h_c <= 0`, 2,828) or behind-camera (4,337),
not `h_q <= 0`. For those the extension is the plain pinhole projection, which
does not depend on `water_z` at all. The claim "smooth in ... water_z, so the
null space is REMOVED, not merely reduced" is true only for `h_q <= 0`
invalidity, where the penalty supplies d/d(water_z) = +1000 px/m.

**Is `board_deeper_2.0_2.9` physically meaningful?** The GEOMETRY is plausible
(board 1.00-1.85 m below the interface, cameras 1.031 m above it) and its
Stage-2 blowup originates in an ordinary near-minimal 8-corner oblique view, of
which real footage has MORE than synthetic. So it must not be dismissed as an
unphysical artifact. What makes the fix-#1-alone pathology unreachable is fix
#2: the 5.3e9 m board pose requires a Stage-2 blowup, and fix #2 rejects
precisely the PnP result that generates it, at its entry point. On the current
tree the worst above-interface violation across all 50 frames is 0.0 m and the
penalty term is never active at x0.

### ITEM 2 — 16x100 is (b), a residual of fix #1, and it is NOT a divergence

`scratchpad/item2b_16x100.log`, 16x100 seed 42, one variable changed per row:

    variant          optimality   rms      status  cond      rank     final_err max/med   water_z err
    A baseline          153.168   0.4993     4      1211    693/693   0.00184 / 0.00105 m   2.21 mm
    B penalty_zero    0.0060859   0.4991     2      1345    693/693   0.00183 / 0.00105 m   0.28 mm
    C linear_loss       455.564   0.4993     2      1283    693/693   0.00183 / 0.00106 m   2.17 mm
    D flat_clamp      1.17962e9   0.8861     3     1.304e8  693/693   0.00265 / 0.00178 m   1.62 mm

Answer to the (a)/(b)/(c) question: **(b), with the important correction that
16x100 has NOT diverged.**

  - **(c) is refuted.** cond 1211 and rank 693/693: the problem is well
    conditioned and full rank, comparable to every converged variant
    (cond 1007-2510).
  - **The solution is correct.** Final camera-centre error 1.84 mm max /
    1.05 mm median, against 1.8-2.2 mm for all six converged sweep variants.
    RMS 0.4993 px is the noise floor. Nothing about this answer is wrong.
  - **The optimality of 153 is a measurement artifact of the penalty's
    non-differentiability.** `max(0, water_z - Q_z)` is C0 but not C1 at the
    interface; its derivative jumps by 1000 px/m across it. Where the solution
    parks an observation at the interface there is no stationary point, so
    first-order optimality cannot reach zero.
  - **Gradient attribution (scipy's own `result.grad`,
    `scratchpad/item2_16x100_grad.log`) localises it to two entries:**

        frame:70[5]  (board-pose t_z)   g = -150.959
        water_z                         g = +150.478
        frame:70[0..2] (board rotation) g = -88.8, -58.4, -11.0
        everything else                 |g| <= 9.03

    Equal-and-opposite in t_z and water_z is the exact signature of the hinge,
    whose derivative is -1 in Q_z and +1 in water_z. Frame 70 holds two of the
    three unprojectable observations, at h_q = **-3.3e-7 m and -3.5e-4 m** --
    i.e. 0.0003 mm and 0.35 mm ABOVE the interface. Their penalty CONTRIBUTION
    is 0.0003-0.37 px, negligible in cost; only their DERIVATIVE shows up.
  - **The flagged huber suspect is REFUTED.** `loss="linear"` makes the number
    WORSE (455.564, not better), because without huber the hinge gradient is not
    down-weighted at all. Huber annealing would not have helped.
  - **Fix #1 improves the ANSWER on this cell too, not only the diagnostic:**
    D (pre-fix behaviour) reaches 2.65 mm / 1.78 mm against A's 1.84 / 1.05 mm.

**Consequence, and it is the finding that matters:** fix #1 as written corrupts
`optimality`, the very instrument this session and E4's grid use as the
convergence discriminator. Any cell whose solution leaves one observation a
fraction of a millimetre above the interface reports a large optimality while
being fully converged, and the new `DegenerateObservationWarning` names it as a
suspected divergence. 16x100 is the first instance; it is a FALSE POSITIVE.

### IS THE PENALTY LOAD-BEARING? — measured, and the answer is NO

Both Items trace to ONE property of fix #1: `ABOVE_INTERFACE_PENALTY_PX_PER_M`
applied to a HINGE, `max(0, water_z - Q_z)`, which is unbounded, linear, and
non-differentiable at the interface. So the term was ablated entirely --
a REMOVAL, not a retuning -- to test whether it carries any of the fix's weight.

Six geometry-bisect variants, penalty = 0 (`scratchpad/sweep_penalty0.log`):

    variant                    cond   rank      final_err   opt (pen=0)  opt (pen=1000)
    control_all_new            1271   345/345   0.0019 m    0.0009103    0.002211
    deep_water_same_standoff   1007   345/345   0.0018 m    0.003124     0.003124
    board_deeper_1.5_2.4       1796   345/345   0.0022 m    0.002332     0.002332
    board_deeper_2.0_2.9       2510   345/345   0.0021 m    0.005471     0.005471
    old_xy_extent              1227   345/345   0.0020 m    0.001719     0.001719
    old_spacing                1461   345/345   0.0018 m    0.002750     0.002750

All six full rank. The five that never enter the extension branch are
bit-identical, as expected. `control_all_new` -- the variant the whole fix was
built for, 7460 branch entries -- converges BETTER without the penalty.

Production cells, penalty = 0 (`scratchpad/cells_penalty0.log`,
`item2b_16x100.log`):

    cell     opt (pen=1000)  opt (pen=0)   final_err max  (1000 -> 0)   water_z err (1000 -> 0)
    8x100    0.0055892       0.00289297    0.00185 -> 0.00181 m         2.11 -> 0.79 mm
    12x100   0.0292268       0.034696      0.00195 -> 0.00192 m         1.46 -> 0.27 mm
    16x100   153.168         0.00608586    0.00184 -> 0.00183 m         2.21 -> 0.28 mm

    12x50 / 16x50 not re-measured: both have a MEASURED zero branch-entry count,
    so penalty = 0 is bit-identical there by construction.

And the three new regression tests in
`tests/unit/test_optim_common.py::TestInvalidProjectionKeepsGradient` all still
PASS with the constant zeroed (verified with an autouse fixture, 3 passed).
Measured directly, the cost is monotone in height above the interface with or
without the penalty:

    penalty=1000  costs(z=0.20,0.10,0.05,0.02,0.0) = 1.302e6, 1.373e7, 8.142e7, 6.915e8, 4.324e41
    penalty=   0  costs(z=0.20,0.10,0.05,0.02,0.0) = 1.302e6, 1.090e7, 6.774e7, 6.403e8, 4.324e41

i.e. the restoring gradient that pushes a lifted board back underwater comes
from the PINHOLE CONTINUATION, not from the penalty. The penalty was never
supplying it.

**Recommendation (NOT APPLIED — see below):** drop the
`ABOVE_INTERFACE_PENALTY_PX_PER_M` term. The a-priori argument, independent of
any failing case: a residual that is C0 but not C1 has no stationary point at
the kink, so `optimality` -- this project's primary convergence discriminator
and the manuscript's -- cannot reach zero there BY CONSTRUCTION. Introducing
non-differentiability at exactly the set of points the continuous extension
exists to serve defeats the purpose of extending continuously. Secondarily, the
term is linear and unbounded, which is what turned Item 1's bad Stage-2 init into
a 9.7e28 objective where the old flat clamp gave a bounded one.

**Why it was NOT applied here.** (1) The session's standing constraint forbids
choosing a value for this constant because it makes failing cases pass; zero is
still a value, and it was found by ablating the two failing cases, so the
decision belongs to the user even though an independent argument exists.
(2) Applying it invalidates the verified state and requires the FULL bar to be
re-run. (3) The current fix is not WRONG -- it produces correct answers on every
configuration measured, 16x100 included. This is a diagnostic-integrity
improvement, not a correctness repair.

**A third option, UNMEASURED:** keep a penalty but make it C1 at the interface
(quadratic in the violation). That preserves the explicit "a submerged target
cannot be above the water surface" constraint while restoring differentiability.
It introduces a new constant with new units (px/m^2) and has not been tested.

**Argument AGAINST removal, recorded for balance:** the penalty is the only term
that explicitly encodes the physical impossibility of an above-water submerged
target. Without it the constraint is purely data-driven. That sufficed on all
ten configurations measured here, but the real 13-camera rig is unmeasured.

---

## Current Focus (previous session)

**ROOT CAUSE CONFIRMED.** The earlier claim that "conditioning at the solution
does NOT sort the variants (cond 449-1711, full rank everywhere)" is
**WITHDRAWN** — that measurement was taken at 6 FRAMES. At 50 frames the
picture inverts completely and conditioning sorts pass/fail perfectly.

reasoning_checkpoint:
  hypothesis: >
    `compute_residuals` replaces a failed (NaN) refractive projection with the
    CONSTANT 100.0 px (`_optim_common.py:637-640`). A constant has identically
    zero derivative in every parameter, so each NaN-clamped observation
    contributes an exactly-zero Jacobian row. When every observation of a frame
    is clamped, that frame's 6 board-pose columns are exactly zero, producing an
    exact 6-dimensional null space; TRF's step collapses and the solve
    terminates on `xtol` while the gradient on the real parameters is ~1e4.
    The projections fail because Stage-2's refractive PnP places the initial
    board pose ABOVE the water surface (h_q <= 0), which the new shallow grid
    geometry makes reachable. The flat penalty makes that region ABSORBING:
    with zero gradient there is no force to push the pose back below the
    interface, so a normally-recoverable bad init becomes unrecoverable.
  confirming_evidence:
    - "8x50 control: 6 numerically-zero Jacobian columns at x0, all belonging to frame 25; independent 50-frame conditioning sweep reports rank 339/345 (deficiency exactly 6), sv_min 2.1e-12, cond 4.118e16."
    - "Frame 25 at x0: all 58 of its corner observations are NaN-clamped; its PnP board pose spans Z in [0.7956, 1.0288] while water_z = 1.0306 -- the ENTIRE board is above the water surface. Ground truth for that frame is Z in [1.1938, 1.3341], safely below."
    - "The sparsity pattern has ZERO structural zero columns, so this is a numeric, not structural, degeneracy -- it cannot be seen by inspecting the layout, only by evaluating J."
    - "Perfect 11/11 sorting on 'any NaN-clamped observation at x0': all six geometry-bisect variants plus five production cells. Every PASSING configuration (deep_water_same_standoff, board_deeper_1.5_2.4, old_xy_extent, old_spacing, 12x50, 16x50) has EXACTLY 0 NaN-clamped observations. Every FAILING configuration has >0 (8x50: 115; board_deeper_2.0_2.9: 12383 across 23 fully-flat frames -> 144 zero columns and rank 186/345; 8x100: 496; 12x100: 10; 16x100: 15)."
    - "Full conditioning sweep completed: rank-deficient <=> broken, full-rank <=> converged, with no exceptions."
  falsification_test: >
    Any configuration with zero NaN-clamped observations that still diverges, or
    any configuration with NaN-clamped observations that converges cleanly,
    refutes this. Tested 11 configurations; no counterexample.
  fix_rationale: >
    Replace the flat constant with the CONTINUOUS EXTENSION of the refractive
    projection across the interface. As h_q -> 0+ the refraction point converges
    to the target point itself, so the refractive projection converges exactly
    to the plain pinhole projection; the pinhole model is therefore the unique
    continuous extension into h_q <= 0. It is smooth in all six board-pose DOF,
    in the extrinsics and in water_z, so the null space is removed rather than
    merely shrunk. An added penalty proportional to the distance the point sits
    ABOVE the interface (zero at the interface, so continuity is preserved)
    keeps the physically impossible half-space non-optimal while still supplying
    a gradient that pushes the pose back underwater. This addresses the root
    cause -- the absence of a gradient -- not the symptom.
  blind_spots: >
    (1) Bit-identity rests on the measured fact that every converging synthetic
    configuration has ZERO invalid projections, so the new branch is never
    entered. The real 13-camera rig (E2) has not been re-measured and could have
    occasional invalid projections; if so its numbers would move. The new
    warning makes that audible rather than silent.
    (2) 8x100 / 12x100 / 16x100 have NaN-clamped observations but no
    fully-flat frame at x0, so their divergence is the absorbing-trap variant of
    the mechanism rather than an x0 null space; the fix is the same but the
    causal chain there is inferred from the trap argument, not directly
    observed at x0.

next_action: Implement the continuous-extension fix and the invalid-projection
  guard, then re-run the 50-frame conditioning sweep and the production cells.

---

## Continuation session (2026-07-30, second agent)

status: CHECKPOINT — bars (a) and (c) resolved, bar (b) UNMET by construction.
  Needs a user decision on the Stage-2 guard's non-inertness. NOTHING COMMITTED;
  HEAD is still 35d76a6828550a5a81d47e7eb820f9e34cdb2fe3.

next_action: Await the user's decision between (1) keep both fixes and accept a
  non-inert Stage-2 change, re-measuring E2; (2) keep only the NaN-clamp fix,
  leaving bar (a) unmet for board_deeper_2.0_2.9; (3) run the cheap Stage-2-only
  rejection count on E2's frameset FIRST and decide with that number in hand.
  Also needs a decision on the E3 declared constant (see Out-of-scope revert).

**Scope handed over:**
1. Revert out-of-scope `tests/unit/test_experiments_e3_constants.py`. DONE — see
   "Out-of-scope revert" below.
2. Root-cause and fix the Stage-2 blowup on `board_deeper_2.0_2.9` as a SECOND,
   INDEPENDENT root cause (not folded into the NaN-clamp finding).
3. Prove the bit-identity claim by instrumenting the new branch and showing a
   zero hit count, rather than asserting it.
4. Do NOT commit. HEAD must stay `35d76a6`.

### Out-of-scope revert (constraint 2)

`tests/unit/test_experiments_e3_constants.py` reverted with `git checkout --`.
Exactly one test then fails, and it is NOT a spurious failure — it is the
declared-constants gate doing its job:

    FAILED tests/unit/test_experiments_e3_constants.py::
      TestDeclaredConstantsMatchLiveValues::
      test_declared_value_matches_live_read[invalid_tir_penalty_px]
    AssertionError: diff[invalid] = literal not found in compute_residuals
    assert None is not None
    (at tests/unit/test_experiments_e3_constants.py:137, inside
     `_invalid_tir_penalty`, regex r"diff\[invalid\]\s*=\s*(\d+\.?\d*)"
     over `inspect.getsource(compute_residuals)`)

The E3 table declares `invalid_tir_penalty_px = 100.0` with the claim
"Invalid/TIR configurations take a fixed 100 px penalty". That claim is now
FALSE by design: the flat 100 px survives only for points behind the camera.
This is a manuscript-facing declared constant, so the correct resolution is a
user decision, not a test edit. Left failing and reported.

### SECOND ROOT CAUSE (independent of the NaN-clamp finding) — CONFIRMED

reasoning_checkpoint:
  hypothesis: >
    `cv2.solvePnP` reports `success=True` on a degenerate corner configuration
    and returns a translation of order 1e12 m. `estimate_board_pose` returns it
    unchecked, `refractive_solve_pnp`'s LM cannot recover (every residual is the
    flat 100 px invalid penalty, so the fit is blind), and
    `estimate_extrinsics`'s best-first traversal then anchors cameras off that
    single garbage board pose. `_refine_poses_multi_frame` weights poses by
    corner count in a plain weighted mean, so one 1e12 m pose with weight 8
    destroys the average rather than being outvoted. Nothing anywhere between
    `cv2.solvePnP` and `estimate_extrinsics`'s return validates the pose, so
    Stage 2 returns camera centres ~1e10 m from the origin as a success.
  confirming_evidence:
    - "board_deeper_2.0_2.9, 8x50 seed 42: EXACTLY ONE observation of 352 is blown up -- cam5 frame 37, 8 corners (the minimum in the dataset), |t| = 4.04e12 m. The PLAIN cv2.solvePnP seed is already 3.09e12 m, so the blowup originates in solvePnP, not in the refractive LM refinement."
    - "Every other observation in that variant is physically sane: |t| median 2.48 m, range 0.065-3.05 m."
    - "That single pose poisons exactly the cameras reached through it: cam3 8.98e8 m, cam5 1.03e10 m, cam6 5.42e9 m, cam7 5.28e9 m; cam0/1/2/4 are fine at 0.000-0.006 m. Stage 2 returns this with no error and no warning."
    - "PnP-quality probe over all six variants (1881 observations): the two populations separate with NO overlap and NO threshold. A healthy pose projects 100% of the corners it was fitted to, at reprojection RMS 0.60-0.84 px. A degenerate pose projects ZERO of them (8/8, 10/10, 11/11 unprojectable, RMS = inf). There is no intermediate case anywhere in the sweep."
  falsification_test: >
    A degenerate pose that still projects some of its own corners, or a healthy
    pose that projects none, would refute the discriminator. None found in 1881
    observations across six variants.
  fix_rationale: >
    Reject, inside `refractive_solve_pnp`, any refined pose that the refractive
    model cannot project a SINGLE one of its own fitted corners with (plus a
    non-finite guard on the LM solution). This is threshold-free -- the rule is
    "a pose that explains none of its own observations is not a pose" -- so it
    introduces no tuned constant and stays camera-agnostic. All four call sites
    in `extrinsics.py` already handle a None return with `continue`, so the
    traversal simply anchors off another observation. This removes the ENTRY
    POINT rather than clamping the symptom downstream.
  blind_spots: >
    NOT inert. Measured below: it changes Stage-2 output on two variants that
    already converged. It could therefore move E2 / the real 13-camera rig.
    See "Inertness measurement" and "E2 exposure" below.

### Stage-2 inertness measurement (sha256 over all R and t, 8x50 seed 42)

    variant                    baseline sha256      with fix             max centre err
    control_all_new            14f836f4c26698dd..   14f836f4c26698dd..   0.944409  -> 0.944409   IDENTICAL
    deep_water_same_standoff   3cda7c7544923312..   461e605229d40639..   0.024341  -> 0.006611   CHANGED
    board_deeper_1.5_2.4       0849fc52cec59d11..   a548ef80312f57d7..   0.029344  -> 0.022936   CHANGED
    board_deeper_2.0_2.9       f9b07bd11e8b1730..   74f02a2ebb32b5bb..   1.03414e+10 -> 0.006615 FIXED
    old_xy_extent              c6fb04ef49b335b9..   c6fb04ef49b335b9..   0.026531  -> 0.026531   IDENTICAL
    old_spacing                5fb58e23482fd306..   5fb58e23482fd306..   0.004042  -> 0.004042   IDENTICAL

Three of six are bit-identical; three change, and every change is an IMPROVEMENT
in Stage-2 camera-centre error. But "improved" is not "inert", and D-26 asks for
inert. This is the honest cost of fixing root cause #2 at its entry point.

### Verification bar (a) — MET

50-frame conditioning sweep, 8 cameras, seed 42, BOTH fixes in the tree
(`scratchpad/sweep_final.log`):

    variant                    cond    rank      sv_min   init_err   opt        rms
    control_all_new            1271    345/345   84.26    0.9444 m   0.002211   0.500
    deep_water_same_standoff   1007    345/345   104      0.0066 m   0.003124   0.498
    board_deeper_1.5_2.4       1796    345/345   61.12    0.0229 m   0.002332   0.501
    board_deeper_2.0_2.9       2510    345/345   45.99    0.0066 m   0.005471   0.500
    old_xy_extent              1227    345/345   106.3    0.0265 m   0.001719   0.501
    old_spacing                1461    345/345   87.27    0.0040 m   0.002750   0.499

ALL SIX are full rank 345/345 with optimality 1.7e-3 to 5.5e-3, including both
previously-diverging variants. `board_deeper_2.0_2.9` moved
cond 2.415e17 -> 2510, rank 58/345 -> 345/345, opt 1.448e7 -> 0.005471,
rms 6.97e11 -> 0.500, Stage-2 init 1.034e10 m -> 0.0066 m.

### Verification bar (b) — the requested PROOF holds, the requested CONCLUSION does not

The branch was instrumented, not asserted: `_extend_invalid_projections` was
wrapped with a counter over the WHOLE solve, every iteration
(`scratchpad/sweep_instrumented.py`).

    variant                    extension-branch calls   observations extended
    control_all_new            7460                     67210
    deep_water_same_standoff   0                        0
    board_deeper_1.5_2.4       0                        0
    board_deeper_2.0_2.9       0                        0
    old_xy_extent              0                        0
    old_spacing                0                        0

MEASURED zero hit count on every converging variant. The previous agent's
blind-spot #1 is therefore discharged **for the continuous-extension fix**: that
fix is provably inert wherever no projection fails.

BUT the converging variants' numbers still moved, and the instrumentation shows
exactly why: not through the extension branch (0 hits) but through the NEW
Stage-2 guard.

    variant                    opt: NaN-clamp fix only -> both fixes
    deep_water_same_standoff   0.001763 -> 0.003124     CHANGED (Stage-2 guard)
    board_deeper_1.5_2.4       0.001992 -> 0.002332     CHANGED (Stage-2 guard)
    old_xy_extent              0.001719 -> 0.001719     unchanged
    old_spacing                0.002750 -> 0.002750     unchanged

So bar (b)'s literal requirement -- "previously converging configurations
numerically UNCHANGED" -- is NOT met for two of four, and the cause is the fix
that the known-conflict section required be added. The zero-hit-count evidence
bar (b) actually asked for is in hand and cleanly attributes the movement.

### Verification bar (c) — counts and reconciliation

`~/anaconda3/envs/AquaCal/python.exe -m pytest tests/ -m "not slow" -q`:

    2 failed, 1107 passed, 6 skipped, 39 deselected  (195 s)

Reconciliation against the stated baseline of 1106 passed / 6 skipped /
39 deselected:

  - Total run count 1106 -> 1109, i.e. +3. All three are new and all three are in
    `tests/unit/test_optim_common.py::TestInvalidProjectionKeepsGradient`, the
    regression tests for root cause #1. Skips (6) and deselects (39) are
    unchanged, so no pre-existing test changed collection state.
  - The previous agent's "1109 passed" is the same 1109 total, with the 2
    failures below suppressed by its out-of-scope edit to the E3 declared
    constants. Reverting that edit restores them. There is no third number.
  - The 2 failures share ONE root, the reverted regex (see "Out-of-scope
    revert"): both call `_invalid_tir_penalty` at
    `tests/unit/test_experiments_e3_constants.py:137`.
      1. `test_experiments_e3_constants.py::TestDeclaredConstantsMatchLiveValues
         ::test_declared_value_matches_live_read[invalid_tir_penalty_px]`
      2. `test_experiments_e3.py::TestBuildCodeConstantsDfShape
         ::test_build_code_constants_df_shape`
  - None of the original 1106 changed state: 1106 originally passing
    = 1107 now passing - 3 new + 2 now failing.

**Consequence beyond the test suite:** failure 2 is NOT merely a test. Per D-18
the import direction is inverted -- `experiments/e3_derived_quantities.py:211`
imports `DECLARED_CONSTANTS` from the test module and calls `entry.live()`. So
with the E3 file reverted, **experiment E3 itself raises and cannot run.** The
declared-constants table is the manuscript-facing authority for
`invalid_tir_penalty_px`, whose declared claim ("Invalid/TIR configurations take
a fixed 100 px penalty") root cause #1 deliberately makes false. Updating it is
a manuscript decision, not a test repair, so it is left for the user.

Slow suite: `-m "slow"` -> **1 failed, 38 passed** (255 s).
`test_pipeline.py::TestSolverConfigSeedIsInert::test_matches_pre_change_anchor`,
`assert 0.1500000000000007 == 0.15000000000000047` -- the identical 2-ulp
`water_z` mismatch the previous agent verified as PRE-EXISTING by stashing all
`src/` changes. Every camera `R` and `t` still matches under
`assert_array_equal`, which is independent evidence that the Stage-2 guard is
inert on that pipeline scenario.

### E4 production cells re-run with BOTH fixes (`scratchpad/cells_stage2fix.log`)

    cell     production   NaN-fix only   both fixes   degen obs   verdict
    8x50     4.3e4  DIV   0.002211       0.002211     0           converged, unchanged vs NaN-fix
    8x100    1.6e10 DIV   0.004639       0.005589     4           converged, CHANGED
    12x50    0.0055 conv  0.005465       0.005465     0           converged, UNCHANGED
    12x100   6.4e9  DIV   0.01074        0.02923      2           converged, CHANGED
    16x50    0.0087 conv  0.008684       0.001685     0           converged, CHANGED (5x better)
    16x100   2.4e4  DIV   194.4          153.2        3           STILL DIVERGED

Four of six diverging-or-converging cells now converge; 16x100 does not (see
below). Note the bar-(b)-relevant row: of the two production cells that ALREADY
converged, `12x50` is unchanged to every reported digit but **`16x50` moved,
0.008684 -> 0.001685**. It moved in the good direction, but it moved, and it did
so with 0 degenerate observations — i.e. via the Stage-2 guard, not the
extension branch.

### E2 / real 13-camera rig exposure (NOT re-run — constraint 4)

The two fixes have very different exposure, and they must not be lumped together.

**Fix #1, continuous extension (`_optim_common.py`) — LOW risk, cheaply provable.**
The branch is entered if and only if `refractive_project_batch` returns NaN for
at least one observation at some Stage-3 iterate. If it is never entered, the
residual vector is bit-identical to the old code and every downstream number is
bit-identical by construction. Measured 0 hits on 5 of 6 synthetic variants.
CAN it move E2? Yes, in principle — the real rig has not been measured.
Decisive measurement: wrap `_optim_common._extend_invalid_projections` with the
counter from `scratchpad/sweep_instrumented.py` and run E2 once.
`calls == 0` proves E2's numbers are bit-identical without re-deriving anything;
`calls > 0` means they can move and the §3 delta needs adjudicating.
Caveat on shortcuts: counting only at x0 is a NECESSARY but NOT SUFFICIENT
screen — zero invalid projections at x0 does not preclude the solver visiting an
invalid iterate later. Only a full-solve count settles it.

**Fix #2, Stage-2 PnP self-check (`extrinsics.py`) — HIGHER risk, and the real
one to worry about.** It is NOT inert: measured to change Stage-2 output on 3 of
6 synthetic variants and to move E4 cell optimality (8x100 0.004639 -> 0.005589,
12x100 0.01074 -> 0.02923). Degenerate `cv2.solvePnP` results come from
near-minimal, poorly-conditioned corner sets — the blown-up observation here had
8 corners, the dataset minimum. Real 13-camera footage has MORE short, partial,
oblique views than clean synthetic data, so the prior probability that E2's
frameset contains at least one such observation is HIGHER than synthetic, not
lower. Treat "E2 is unaffected" as unproven and unlikely, not as the default.
Decisive measurement, and it is CHEAP — it does NOT need a 48-87 min run:
instrument `refractive_solve_pnp` with a rejection counter and run **Stage 2
only** on E2's release frameset, stopping before Stage 3. Zero rejections proves
E2 is unaffected by fix #2; any rejection means E2 must be re-run and its §3
numbers re-checked. (Cost is dominated by ChArUco detection over the 13 videos,
not by the solve.)

Supporting evidence that fix #2 is at least not gratuitously disruptive:
`test_pipeline.py::TestSolverConfigSeedIsInert::test_matches_pre_change_anchor`
still matches every camera `R` and `t` bit-for-bit against its frozen anchor with
both fixes in the tree; only the pre-existing 2-ulp `water_z` value differs. That
is one synthetic pipeline scenario, not the real rig, so it is supporting
evidence and not proof.

### 16x100 — explicitly OUT of scope for this session

Stated plainly, per the handover's request for no ambiguity: **16x100 is OUT.**

Reasons:
1. Its dominant mechanism is a THIRD one, distinct from both root causes fixed
   here. The previous agent measured only 3 unprojectable observations at its
   solution, so neither the flat-penalty null space nor a degenerate Stage-2 PnP
   explains a residual optimality of ~194.
2. Its leading candidate — `loss="huber", f_scale=1.0` applied from iteration
   zero with no annealing (`interface_estimation.py:349-358`, hardcoded at
   `:721-726`) — is a change to the LOSS CONFIGURATION. That alters every solve
   in the library, including E1, E2 and E7. Its inertness surface is the exact
   opposite of the two surgical, entry-point changes made here, and it cannot be
   proven inert by a hit-count argument because it has no "branch not taken".
   Bundling it into this diff would destroy the reviewability of both.
3. None of this session's verification bars (a)/(b)/(c) covers it.

It is no longer SILENT, which was the actionable half of the problem: the new
`DegenerateObservationWarning` fires on it and names its optimality, where
previously it shipped a publishable-looking 0.71 px RMS with nothing to indicate
the solve had failed. Recorded as open follow-up 1.

### The coordinator's "library weakness" framing — checked, both halves accurate

Verified rather than assumed:

(a) **"`optimize_interface` proceeds on an exactly-singular Jacobian instead of
detecting it."** CONFIRMED. `aquacal.validation.conditioning.compute_conditioning`
diagnoses this correctly — every rank/sv_min number in this session came from it
— but nothing on the production path calls it. `optimize_interface` checks only
`result.status <= 0`, and TRF's `xtol` termination (status 3) is a *success*
code, so a step-collapse on a singular Jacobian returns as success. Only
PARTIALLY addressed here: the new `DegenerateObservationWarning` fires on the
CAUSE (unprojectable observations) and prints the optimality, which is what made
16x100 audible. It is not a rank check. A genuine post-solve conditioning gate on
the production path remains absent and is a real, separate improvement.

(b) **"`estimate_extrinsics` can return a 1e10 m result with no sanity check on
the way out."** CONFIRMED, and demonstrated live (cam5 1.03e10 m, cam6 5.42e9 m,
cam7 5.28e9 m returned as success). Fixed here at the ENTRY point rather than the
exit: rejecting the one unexplainable PnP pose removes the 1e10 m result
altogether, so an exit guard had nothing left to catch on any measured scenario.
An exit guard would still be worthwhile defence-in-depth, but it needs a
data-derived plausibility scale to stay camera-agnostic, and inventing one was
out of proportion to this session. Not added.

### Minor separate bug — RECORDED, not fixed (outside in-scope files)

`src/aquacal/validation/conditioning.py:167` emits
`RuntimeWarning: invalid value encountered in divide` at
`corr = cov / np.outer(d, d)`. When the problem is rank-deficient, `Vk` drops the
null directions, so `cov`'s diagonal entry for a parameter lying in the null
space is exactly 0, giving `d[i] = 0` and a whole NaN row and column in the
correlation matrix. `np.fill_diagonal(corr, 1.0)` at :168 repairs only the
diagonal and `np.clip` at :169 propagates the NaN, so `ConditioningReport
.correlation` is silently NaN for exactly the rank-deficient problems where a
user would most want to read it. Observed live on `board_deeper_2.0_2.9` before
the Stage-2 fix. Fix deferred: `conditioning.py` is outside the in-scope file
list for this session.

## Resolution

root_cause: |
  `compute_residuals` (`_optim_common.py:637-640`) replaced a failed refractive
  projection (NaN) with the CONSTANT 100.0 px. A constant has identically zero
  derivative in every parameter, so each such observation contributed an
  exactly-zero Jacobian row. Two consequences:

  1. A frame whose observations were ALL invalid contributed an exact
     6-dimensional null space (its board-pose columns were exactly zero),
     collapsing TRF's trust-region step and forcing `xtol` termination while
     first-order optimality was still ~1e4.
  2. More fundamentally, the invalid region was ABSORBING: with zero gradient
     there was no force pushing the pose back into the valid region, so a
     normally-recoverable bad initialization became permanently unrecoverable.

  The projections failed because Stage-2's refractive PnP places some initial
  board poses ABOVE the water surface (`h_q <= 0` at
  `refractive_geometry.py:635`). The D-27/D-28/D-29 grid redesign seats the
  board only 0.069-0.95 m below the interface, so an ordinary PnP error of
  0.2-0.4 m lifts a whole board out of the water. The old geometry sat deep
  enough that this never happened, which is why the regression appeared exactly
  at that redesign.

fix: |
  Replace the flat constant with the CONTINUOUS EXTENSION of the refractive
  projection across the interface.

  - `_optim_common._extend_invalid_projections` (new): projects an
    unprojectable point with the plain pinhole model. This is the unique
    continuous extension -- as a point approaches the interface from below the
    refraction point converges to the point itself, so the refractive
    projection converges exactly to the pinhole projection. It is smooth in all
    six board-pose DOF and in the extrinsics.

    **CORRECTED 2026-07-30 (third session), AMENDED (fourth session).** The
    original wording read "smooth ... and in water_z, so the null space is
    REMOVED, not merely reduced". Two qualifications, both measured:
      (i) The pinhole extension does NOT depend on water_z at all, so an
          extended residual is exactly water_z-independent. (The third session
          recorded a partial exception -- the above-interface penalty supplied
          a d/d(water_z) of +1000 px/m for `h_q <= 0` invalidity -- but that
          term has since been REMOVED, so the exception is gone and the
          extension is water_z-independent in every invalidity branch.)
      (ii) "Null space REMOVED" is exact only in the mathematical sense. The
          extension's derivative scales as f/Z, so for a camera placed ~1e10 m
          away by a blown-up Stage 2 it is ~1e-7 px/m -- nonzero, but
          numerically zero at any relative rank tolerance. Rank is restored in
          practice only when Stage 2 is sane, which is what fix #2 guarantees.
  - **NO above-interface penalty term.** `ABOVE_INTERFACE_PENALTY_PX_PER_M` was
    added in the first session and REMOVED OUTRIGHT in the fourth (user
    decision, 2026-07-30). The constant is deleted, not set to zero: a live
    constant with a zero value invites a later "restoration" of a term that is
    structurally wrong. See `fix_rationale` below.
  - `INVALID_PROJECTION_PENALTY_PX = 100.0` (the historical flat value) now
    applies only to a point behind the camera, where no continuous extension
    exists. Because it is now a named module-level constant rather than a bare
    `diff[invalid] = 100.0` literal, E3's declared-constants table reads it live
    off the attribute instead of by a regex over `compute_residuals`' source.

fix_rationale: |
  **Why the above-interface penalty was removed (the argument that decides it).**
  Applying a penalty at a HINGE -- `max(0, water_z - Q_z)` -- makes the residual
  C0 but not C1 at the interface. A function with a kink has no stationary point
  there, so first-order `optimality` CANNOT REACH ZERO BY CONSTRUCTION wherever
  that branch fires. `optimality` is the convergence discriminator this project
  and the manuscript rely on -- it is what caught E7's missing-refraction-params
  defect in Phase 19.1 and what exposed this very bug behind a publishable
  0.79 px RMS. Introducing non-differentiability at exactly the set of points
  the continuous extension exists to serve defeats the purpose of extending
  continuously, and silently invalidates the instrument. Removing the kink
  restores the diagnostic. This argument depends on no failing case.

  **Corroboration (NOT the justification).** Two measurements, both independent
  of the cells that were failing:
    - ACCURACY improves everywhere the term was active. Final `water_z` error on
      the production cells moves 2.11 -> 0.79 mm (8x100), 1.46 -> 0.27 mm
      (12x100), 2.21 -> 0.28 mm (16x100), with final camera-centre error
      unchanged or slightly better in every case.
    - The restoring gradient is not the penalty's. Cost is monotone in height
      above the interface with the term present AND absent
      (`1.302e6, 1.090e7, 6.774e7, 6.403e8` at z = 0.20, 0.10, 0.05, 0.02 with
      the term removed), so the force pushing a lifted board back underwater
      comes from the pinhole continuation.

  The "16x100 goes 153 -> 0.0061" figure is deliberately NOT the ground for this
  change: it is a failing case, and choosing a constant's value by ablating
  failing cases is what this session's constraints forbid.

  **Recorded counter-argument.** The penalty was the only term explicitly
  encoding the physical impossibility of an above-water submerged target.
  Without it, that constraint is purely data-driven. Measured sufficient on all
  ten configurations tested here; the real 13-camera rig is not measured. If a
  future case needs the constraint back, it must be re-introduced in a C1 form
  (quadratic in the violation), never as a hinge.
  - Degeneracy guard: `optimize_interface` and `joint_refinement` re-evaluate
    the residuals at the solution and raise a new
    `DegenerateObservationWarning` when any observation could not be projected,
    naming the count, the first-order optimality and the termination status.
    This is what makes the failure audible -- previously an `xtol`-terminated
    divergence was returned as success behind a publishable-looking RMS.
  - `compute_residuals` gains an optional `invalid_count_out` sink (default
    None, no behaviour change) used by the guard.

verification: |
  **SUPERSEDED IN PART.** Everything below was measured WITH the above-interface
  penalty in the tree. The penalty has since been removed (fourth session), and
  the authoritative post-removal numbers are in "Decision 1" in the fourth
  session's Current Focus: all six bisect variants 345/345 full rank at
  optimality 9.1e-4 to 5.5e-3, the five non-entering variants bit-identical to
  the table below under a MEASURED zero branch-hit count, and 1109 passed /
  0 failed. The BEFORE column and the mechanism narrative below still stand.

  50-frame conditioning sweep, 8 cameras, seed 42 (BEFORE -> AFTER):

  variant                    cond              rank         opt              rms
  control_all_new            4.118e16 -> 1271  339 -> 345   4.347e4 -> 0.0022  14.244 -> 0.500
  deep_water_same_standoff   1007     -> 1007  345 -> 345   0.001763 (same)    0.498 (same)
  board_deeper_1.5_2.4       1796     -> 1796  345 -> 345   0.001992 (same)    0.501 (same)
  old_xy_extent              1227     -> 1227  345 -> 345   0.001719 (same)    0.501 (same)
  old_spacing                1461     -> 1461  345 -> 345   0.002750 (same)    0.499 (same)
  board_deeper_2.0_2.9       3.011e16 -> 2.415e17  186 -> 58  2.39e6 -> 1.448e7  (still broken)

  - The failing control now converges DESPITE an unchanged 0.9444 m Stage-2 init
    error, which is the direct proof that the fix removed the absorbing trap
    rather than improving the initialization.
  - All four previously-passing variants are BIT-IDENTICAL (every reported digit
    unchanged), satisfying D-26's inertness requirement for those paths.
  E4 production cells through the FULL `calibrate_synthetic` path (Stage 3 plus
  the intrinsic pass), seed 42, `scratchpad/cells_fixed.log`:

  cell     BEFORE optimality  AFTER optimality  AFTER rms   degenerate obs at solution
  8x50     4.3e4  DIVERGED    0.002211  OK      0.499 px    0
  8x100    1.6e10 DIVERGED    0.004639  OK      0.499 px    4 of 30837
  12x50    0.0055 converged   0.005465  OK      0.499 px    0   (UNCHANGED)
  12x100   6.4e9  DIVERGED    0.01074   OK      0.499 px    4 of 34861
  16x50    0.0087 converged   0.008684  OK      0.499 px    0   (UNCHANGED)
  16x100   2.4e4  DIVERGED    194.4  STILL BAD  0.499 px    3 of 37405

  Three of the four diverging cells now converge, including 12x100, which had
  hidden its divergence behind a publishable 0.79 px RMS on optimality 6.4e9.
  Both previously-converging cells reproduce their production optimality to the
  reported precision (0.005465 ~ 0.0055, 0.008684 ~ 0.0087), i.e. unchanged.

  16x100 is improved 125x (2.4e4 -> 194.4) but is NOT converged, and its
  intrinsic pass is worse still (563.6, `xtol`). It carries only 3 unprojectable
  observations at the solution, so the flat-penalty mechanism is no longer the
  dominant obstacle there. It needs its own investigation -- see below. The
  important change is that it is no longer SILENT: the new guard fires on it and
  names optimality 194.4, where previously it shipped a 0.71 px RMS with nothing
  to indicate the solve had failed.

  Note on RMS comparison: the harness reports
  `result.diagnostics.reprojection_error_rms` while the production
  `benchmark.json` reports a differently-pooled RMS, so RMS is NOT comparable
  across the two (pre-fix the harness gave 14.78 px where production gave
  12.8 px on the same 8x50 cell). Optimality IS comparable and reproduces to the
  digit, which is why it is used as the discriminator throughout.

  - Test suite (AquaCal conda env): `-m "not slow"` 1109 passed, 0 failed
    (was 1104 passed + 2 failed before the E3 declared-constant update; the
    +3 are the new regression tests). `-m "slow"` 38 passed, 1 failed.
  - The one slow failure, `TestSolverConfigSeedIsInert::test_matches_pre_change_anchor`,
    is PRE-EXISTING: verified by stashing every `src/` change and re-running,
    which produced the IDENTICAL mismatch (`0.1500000000000007` vs the frozen
    anchor `0.15000000000000047`, a 2-ulp water_z difference; every R and t
    matched exactly under `assert_array_equal`). That the fixed tree reproduces
    the pristine tree's value to the last bit is additional direct evidence that
    this change is numerically inert on that pipeline scenario. Per that test's
    own docstring the anchor must never be regenerated to make it pass, so this
    is reported as a plan 19.2-14 finding, not touched here.
  - `ruff check` and `ruff format --check` clean.
  - Regression tests added in `tests/unit/test_optim_common.py`
    (`TestInvalidProjectionKeepsGradient`). Confirmed RED under the old rule: the
    toy scenario produced exactly 6 zero Jacobian columns for the above-water
    frame and a cost of exactly 840000.0 at all three heights above the
    interface -- perfectly flat.

files_changed:
  - src/aquacal/calibration/_optim_common.py
  - src/aquacal/calibration/interface_estimation.py
  - src/aquacal/calibration/refinement.py
  - src/aquacal/config/schema.py
  - src/aquacal/config/__init__.py
  - src/aquacal/calibration/extrinsics.py
  - tests/unit/test_optim_common.py
  - tests/unit/test_experiments_e3_constants.py

## Open follow-ups added by the fourth session (RECORDED, not fixed)

A. **D-18 import inversion: `experiments/e3_derived_quantities.py:211` imports
   `DECLARED_CONSTANTS` from a TEST module** (`tests.unit.test_experiments_e3_constants`)
   and calls `entry.live()`. An `experiments/` module therefore has a hard
   runtime dependency on `tests/`, resolved only by a PEP 420 namespace portion
   plus a `sys.path` bootstrap. The concrete cost was visible in the third
   session: reverting a test-file edit made **experiment E3 itself unrunnable**,
   not merely red. Deliberately NOT restructured here -- it is phase work
   needing its own plan.
   **Recommendation:** move `DECLARED_CONSTANTS` (and the `DeclaredConstant`
   NamedTuple and the live accessors) into `experiments/` -- e.g.
   `experiments/_declared_constants.py` -- and have the test module IMPORT it.
   That inverts the dependency to the correct direction (tests depend on
   shipped code) while preserving the property the current design was chosen
   for: the table is declared exactly once and CI is the gate that breaks first
   when a library default moves. It also removes the `sys.path` bootstrap and
   the PEP 420 fragility described in that module's own docstring. Do NOT
   solve it by creating `tests/unit/__init__.py` -- that module's docstring
   already records why (pytest collection semantics change for the whole
   directory).

B. **`experiments/results/code_constants.csv` is stale** in the `claim`,
   `source` and `read_via` columns for `invalid_tir_penalty_px`. Not hand-edited
   (it is a generated experiment artifact). Re-run E3 (~10 s) to regenerate.

C. **`src/aquacal/validation/conditioning.py:167` silently returns a NaN
   correlation matrix on rank-deficient problems.** Left UNFIXED at the user's
   explicit instruction -- outside this session's scope. Full diagnosis is under
   "Minor separate bug" below.

D. **Two out-of-scope documents still assert the old flat-penalty behaviour**
   and are now factually wrong. Not edited (outside the in-scope file list):
     - `.planning/inbox/library-summary.md:56` -- "Failed projections (e.g., due
       to total internal reflection) receive a 100 px penalty".
     - `.planning/codebase/ARCHITECTURE.md:317` -- "Cost function assigns high
       residual (100.0 px)".
   `.planning/knowledge-base.md:52` and the 19.1/19.2 phase documents also cite
   `_optim_common.py:639` as "the 100 px penalty"; those are historical phase
   records, but the knowledge-base entry is live guidance and should be
   re-worded.

## Open follow-ups (NOT fixed here)

0. **[SUPERSEDED 2026-07-30, third session]** Follow-up 1 below is RESOLVED as a
   diagnosis: 16x100 has NOT diverged. See "ITEM 2" in the third-session Current
   Focus. Its optimality is an artifact of the above-interface penalty's
   non-differentiability; the huber-from-iteration-zero suspect named in
   follow-up 1 is REFUTED by direct measurement (`loss="linear"` gives 455.564,
   worse than huber's 153.168). Follow-up 3 below is likewise resolved: the
   `board_deeper_2.0_2.9` Stage-2 blowup is fix #2's subject and no longer
   occurs on the current tree.

1. **16x100 still diverges** at optimality 194.4 (first pass, status 4) and
   563.6 (intrinsic pass, status 3), with only 3 unprojectable observations at
   the solution. A different mechanism dominates there. The leading untested
   candidate is the one recorded as secondary suspect: `least_squares` is called
   with `loss="huber", f_scale=1.0` px applied from iteration zero with no
   annealing (`interface_estimation.py:349-358`, and hardcoded at `:721-726`).
   With Stage-2 init errors near 1 m the starting residuals are tens of pixels,
   so huber down-weights every gradient by ~1/|r| exactly when the solver most
   needs signal. This was NOT investigated in this session.

2. **`_compute_initial_board_poses` admits physically impossible poses.** It
   returns board poses that place the entire target above the water surface,
   which cannot happen for a submerged target. The continuous-extension fix
   makes those recoverable, but rejecting or clamping them at the source would
   remove the entry point altogether and is cheap. Deliberately NOT done here to
   keep the change minimal and its inertness argument simple.

3. **`board_deeper_2.0_2.9`: Stage 2 blows up to ~1e10 m.** See below.

## Second, unrelated defect found (NOT fixed here)

`board_deeper_2.0_2.9` still diverges, but NOT through this mechanism. Its
Stage-2 initialization error is **10,341,382,931 m**, and that value is
BIT-IDENTICAL before and after the fix -- Stage 2 has already blown up by ~1e10
before Stage 3 is ever entered. This is a distinct upstream defect in
`estimate_extrinsics` on that geometry, pre-existing and untouched. It is a
bisect probe variant, not one of E4's production cells. The new
`DegenerateObservationWarning` now fires loudly on it instead of it passing
silently.

## Constraints

- **Fix the library, not the experiment.** Retuning `GRID_*` constants in
  `experiments/e4_benchmark_grid.py` to dodge the failure is explicitly NOT
  the goal.
- Phase 19.2 is mid-flight. Wave 3 (plan 19.2-21) is unmerged on branch
  `worktree-agent-a1a99b5a5289e9e05` and MUST NOT be merged.
- D-26: `src` changes land and are proven inert before any experiment yielding
  a publishable result.

## Environment gotchas

- Use `~/anaconda3/envs/AquaCal/python.exe`. Git Bash `python` is Anaconda base
  and has no numpy (39 collection errors that look like a breakage).
- `PYTHONPATH` must point at the tree under test; the editable install resolves
  to the MAIN checkout.
- `DiagnosticsData.reprojection_error_rms`, not `reprojection_rms`.
  `SolverDiagnostics.optimality` is a direct attribute.
- **A 6-frame smoke run converges on EVERY variant.** The failure needs ~50
  frames. Never conclude a fix works from a low-frame-count run.

## Key files

- `src/aquacal/calibration/extrinsics.py` — Stage 2 (`build_pose_graph`,
  `estimate_extrinsics`)
- `src/aquacal/calibration/interface_estimation.py` — `optimize_interface`
- `src/aquacal/calibration/_optim_common.py` — param packing, cost, sparsity
- `src/aquacal/validation/conditioning.py` — `compute_conditioning`

## Related prior sessions

`.planning/debug/rig-tilt-high-reproj.md` and
`.planning/debug/callibration071626-tilt-high-reproj.md` are OPEN sessions on a
superficially similar symptom. Project memory records that the tilted-rig
symptom has had multiple unrelated root causes, so do not assume they share one
with this bug — but check them before re-deriving anything.

## Evidence

- timestamp: 2026-07-30
  observation: Control variant reproduces production 8x50 optimality to the
  digit (4.347e4 vs 43466.96), so the harness is faithful to the production
  path.

- timestamp: 2026-07-30
  observation: At 6 frames ALL six variants converge (optimality 0.001-0.007,
  RMS ~0.49 px). The defect is frame-count dependent.

- timestamp: 2026-07-30
  checked: 50-frame conditioning sweep completed (`scratchpad/cond50.log`).
  found: |
    variant                    cond       rank     sv_min    init_err   opt        rms
    control_all_new            4.118e+16  339/345  2.1e-12   0.9444 m   4.347e+04  14.244
    deep_water_same_standoff   1007       345/345  104       0.0243 m   0.001763    0.498
    board_deeper_1.5_2.4       1796       345/345  61.12     0.0293 m   0.001992    0.501
    board_deeper_2.0_2.9       3.011e+16  186/345  1.707e-12 1.03e10 m  2.39e+06  150.410
    old_xy_extent              1227       345/345  106.3     0.0265 m   0.001719    0.501
    old_spacing                1461       345/345  87.27     0.0040 m   0.002750    0.499
  implication: At 50 frames rank deficiency sorts pass/fail with NO exceptions.
    The debug file's earlier "full rank everywhere" claim was a 6-frame artifact
    and is withdrawn. Deficiency is an exact multiple of 6 (6 and 159 ~ 26x6),
    i.e. whole board-pose blocks.

- timestamp: 2026-07-30
  checked: Zero-Jacobian-column probe at x0 (`scratchpad/zerocol_probe.py`),
    all six variants. Structural (sparsity) vs numeric (evaluated J) columns.
  found: |
    variant                    struct_zero  numeric_zero  NaN-clamped obs   fully-flat frames
    control_all_new            0            6             115 / 14930 (0.77%)   [25]
    deep_water_same_standoff   0            0             0                     []
    board_deeper_1.5_2.4       0            0             0                     []
    board_deeper_2.0_2.9       0            144           12383 / 24009 (51.6%) 23 frames
    old_xy_extent              0            0             0                     []
    old_spacing                0            0             0                     []
  implication: The degeneracy is NUMERIC, not structural — invisible in the
    sparsity pattern, so no amount of inspecting the parameter layout finds it.
    The manager's suspect #4 (a frame packed with 6 params but contributing zero
    RESIDUALS) is REFUTED: structural zero columns are 0 everywhere, every
    packed frame does contribute residual rows. The rows are simply CONSTANT.

- timestamp: 2026-07-30
  checked: Which invalidity branch of `refractive_project_batch` fires
    (`scratchpad/nan_cause.py`), 8x50 control.
  found: water_z = 1.0306. Frame 25's Stage-2 PnP initial board pose spans
    Z in [0.7956, 1.0288] — the ENTIRE board above the water surface — while
    ground truth is Z in [1.1938, 1.3341]. Seven further frames (1, 18, 20, 30,
    32, 35, 40) are PARTIALLY above water at init. The firing branch is
    `h_q = Q_z - z_int <= 0` at `refractive_geometry.py:635`, not `h_c <= 0`
    and not a Newton failure.
  implication: The new grid geometry seats the board only 0.069-0.95 m below the
    interface, so an ordinary PnP error of ~0.2-0.4 m lifts a whole board above
    the surface. The old geometry sat deep enough that this never happened.
    This also explains the NON-MONOTONICITY in depth: whether any single frame
    crosses the surface is a discrete accident of that frame's pose error.

- timestamp: 2026-07-30
  checked: Production cells probed at x0 for NaN-clamped observations.
  found: |
    cell     NaN-clamped / total obs     fully-flat frames   production verdict
    8x50     115 / 14930  (0.770%)       [25]                diverged (4.3e4)
    8x100    496 / 30837  (1.608%)       []                  diverged (1.6e10)
    12x100   10  / 34861  (0.029%)       []                  diverged (6.4e9)
    16x100   15  / 37405  (0.040%)       []                  diverged (2.4e4)
    12x50    0   / 16615  (0.000%)       []                  CONVERGED (0.0055)
    16x50    0   / 18108  (0.000%)       []                  CONVERGED (0.0087)
  implication: "any NaN-clamped observation at x0" sorts pass/fail 11/11 across
    the six bisect variants and five production cells, with zero exceptions —
    including the two cells (12x100, 16x100) that hid divergence behind a
    publishable-looking 0.79 / 0.71 px RMS. Only 10 flat observations out of
    34861 are enough to wreck 12x100, because a flat residual is not merely
    uninformative — it is an ABSORBING trap with no gradient out.
