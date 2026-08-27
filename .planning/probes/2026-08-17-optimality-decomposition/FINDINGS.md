# Probe: per-block decomposition of E1's reported `optimality`

**Date:** 2026-08-17
**Sha:** `a7f0f25` (Phase 23 complete; library identical to the `330f9ef` verification run)
**Script:** `probe_optimality_blocks.py` · **Raw:** `optimality_blocks.json` · **Log:** `probe_run.log`
**Opened requirement:** DEGEN-05 (Phase 24)

## Question

Phase 23's verification left E1's non-refractive arm at `optimality_intrinsic` = 92.78 against the
refractive arm's 0.0247 on the same scenario and seed. Is that a benign artifact of pinning
`water_z`, or is the arm terminating non-stationary?

## Method and its self-check

`scipy.optimize.least_squares` was monkeypatched in `interface_estimation` and `refinement`. For
`trf` (always selected here, since bounds are finite) scipy reports `optimality = ||g · v||∞`,
where `v` is the Coleman-Li scaling vector. The probe reimplements `v` and **requires that its
reconstruction reproduce scipy's reported number before any attribution is believed**.

All four solver calls reconstructed to `rel_err = 0.00e+00`. Block layout was derived from the
bounds vector, not assumed, and recovered 12 cameras / 30 frames — the known rig. The
decomposition is therefore trustworthy.

## Result

Calls 1-2 are the refractive arm, 3-4 the non-refractive arm (pass 1 = interface, pass 2 = intrinsic).

| Call | Arm / pass | reported `optimality` | dominant block | `water_z` raw \|g\| | `water_z` scaled | share |
|---|---|---|---|---|---|---|
| 1 | refractive, interface | 0.00114616 | water_z | 0.00112212 | 0.001146 | 100% |
| 2 | refractive, intrinsic | 0.0247357 | extrinsics | 0.00665913 | 0.006502 | 26% |
| 3 | non-refractive, interface | 1.44454 | extrinsics | **11.5661** | **2.11e-11** | **0.00%** |
| 4 | non-refractive, intrinsic | 92.7841 | extrinsics | **9.74971** | **1.95e-11** | **0.00%** |

## Finding 1 — the documented explanation is wrong

`23-VALIDATION.md:72-74`, `23-RESEARCH.md:76`, `23-01-PLAN.md:103` and `23-01-SUMMARY.md:153` all
state that `optimality_intrinsic` rises *because* `water_z` is pinned against a ~2e-12-wide box,
"the unprojected component of the gradient along that direction cannot be driven to zero by
definition."

**The pinned `water_z` contributes 0.00% of the reported optimality** (1.95e-11 out of 92.78). The
reasoning inverts the scaling: Coleman-Li sets `v` to the *distance to the bound the negative
gradient points toward*. Pinned, that distance is ~1.8e-12, so the contribution is crushed toward
zero rather than inflated. The documented claim describes an *unscaled* projected gradient, which
is not the quantity scipy reports.

Note the raw gradient on that slot **is** large (11.57 / 9.75) — that part of the intuition was
right. It simply never reaches the reported number.

**Consequence:** the pin does not explain the 49.65 → 92.78 rise. The likelier explanation is that
holding `water_z` at 1.031 instead of letting it drift to 0.012 moves every *other* parameter to a
different solution point. That is a hypothesis this probe did not test.

## Finding 2 — the real gap is in extrinsics, and it is not a scale effect

Extrinsics are unbounded, so `v = 1` and their scaled value *is* the raw gradient. Both arms are
extrinsics-dominated; the reported optimality is literally the max extrinsic gradient component.

- non-refractive: **92.78** · refractive: **0.0247** → ratio **3751x**
- cost 15097.61 vs 3680.03 → residual magnitude ratio only **2.03x**

A ~2x difference in residual scale cannot produce a ~3750x difference in gradient. **The gap is
not explained by the non-refractive arm simply having larger residuals.**

Both passes terminated `status = 2` (`ftol`), never `gtol` (1e-8). So the non-refractive arm
stopped because *cost stopped moving*, with the gradient still far from zero — the signature of a
stalled trust region or a very flat ill-conditioned valley, not of a stationary point.

> **PARTLY SUPERSEDED by Findings 4-5 (warm-restart test, same day).** The inference that the arm
> is "not stationary" does not survive: restarts recover no cost, and the 92.78 itself is unstable
> at a fixed solution (92.78 → 2.16). The *measurement* above is correct; the *interpretation* of
> it as non-stationarity was wrong. The genuine conditioning gap is ~2.16 vs 0.00116, not 3751x.

## Finding 3 — `optimality` is not comparable across blocks

Call 4's intrinsics block reports scaled 49.97 against a raw gradient of 0.068 — the CL distance
scaling *inflates* it by ~730x, because intrinsic bounds are wide (`0.5·fx` to `2·fx`).

So a single reported `optimality` mixes three regimes: `v = 1` (unbounded extrinsics and poses),
`v ≈ 700` (wide-bounded intrinsics), `v ≈ 2e-12` (a pinned slot). **The scalar is not a like-for-like
maximum and should never be read as one.** This is independent of anything Phase 23 changed and
strengthens the case for DEGEN-05 shipping the decomposition rather than the scalar alone.

## What this does and does not license

**Does not** license a claim that E1's numbers are wrong. Cost matched the unpinned solve to ~9
significant figures, the recovered `water_z` sits at ground truth to 1e-12, and the full test suite
is green. Nothing here contradicts a Phase 23 acceptance criterion — every one of those was phrased
on recovered `water_z`, deliberately, and they all still pass.

**Does** establish that the non-refractive arm is not demonstrably stationary, and that this was
never measured before. Direction of risk is unchanged from when DEGEN-05 was opened: an
under-converged *baseline* arm has larger error than its true optimum, which **inflates** E1's
refractive-to-non-refractive ratio rather than penalizing it. The 97-178x band is the exposed
number.

> **SUPERSEDED by Finding 4 (same day).** The warm-restart test answered this: the baseline is
> converged, restarts recover ~0 cost, and E1's ratio is **not** inflated by under-optimization.
> The risk described in this paragraph was real to raise and turned out not to materialize. Read
> Finding 4 as the settled position; this paragraph is kept to show what was believed before the
> follow-up ran.

## Open, for Phase 24/25

1. Is the extrinsic gradient at termination genuinely non-stationary, or is the trust region
   collapsing on an ill-conditioned but effectively-converged valley? Discriminator: restart the
   solver from its own solution and see whether cost decreases further.
2. Does the same extrinsics-dominated pattern appear in the *refractive* arm at a smaller scale
   (0.0247 is also extrinsics-dominated), i.e. is this a property of the problem rather than of the
   non-refractive arm?
3. Corrections needed in the Phase 23 documents, which now carry a falsified mechanism:
   `23-VALIDATION.md:72-74`, `23-RESEARCH.md:76`, `23-01-PLAN.md:103`, `23-01-SUMMARY.md:153`.
   Left un-edited here deliberately — those are committed phase artifacts, and amending them is the
   user's call.

---

# Follow-up: warm-restart test (2026-08-17)

**Script:** `probe_warm_restart.py` · **Raw:** `warm_restart.json` · **Log:** `warm_restart.log`

## Probe defect on the first attempt — recorded deliberately

The first run passed `x0` positionally while E1 passes it as a keyword, so every
restart raised `got multiple values for argument 'x0'` and **zero restarts ran**.
The verdict logic then defaulted to `"stalled at/near a minimum"` on an empty
restart list — i.e. it reported the reassuring answer having measured nothing.

Fixed twice over: the call now handles both calling conventions, and an empty
restart list yields `INDETERMINATE -- no restart completed` rather than a
conclusion. This is the same class of defect as FIX-05's always-red `--check`,
in the opposite direction — a gate that cannot fail is as useless as one that
cannot pass.

## Finding 4 — both arms are converged in cost; the comparison is fair

Restarting each solve from its own solution (trust region reset, two successive
restarts) recovers essentially nothing:

| Solve | base cost | after 2 restarts | relative drop |
|---|---|---|---|
| refractive, interface | 3688.797145 | 3688.797145 | 0 |
| refractive, intrinsic | 3680.034008 | 3680.034008 | 2.6e-13 |
| non-refractive, interface | 26067.02058 | 26067.02058 | 2.1e-12 |
| non-refractive, intrinsic | 15097.61231 | 15097.61228 | 1.8e-9 |

**E1's non-refractive baseline is not under-optimized.** The ratio is therefore
not inflated by a badly-converged baseline, and the fairness objection raised
when DEGEN-05 was opened is answered in E1's favour. This *strengthens* the
97-178x band rather than threatening it.

## Finding 5 — `optimality` is unstable at a fixed solution

Cost does not move, yet the reported optimality collapses on restart:

| Solve | base | restart 1 | restart 2 |
|---|---|---|---|
| non-refractive, intrinsic | 92.78 | 27.58 | **2.16** |
| non-refractive, interface | 1.4445 | 0.0039 | 0.0041 |
| refractive, intrinsic | 0.0247 | 0.00121 | 0.00116 |
| refractive, interface | 0.00114616 | 0.00114616 | 0.00114616 |

A 43x range at the same solution point. Consistency check: call 1 moved exactly
zero in cost and its optimality is bit-identical across all three runs, so the
effect tracks tiny movements in `x` rather than being random.

Two candidate causes, not separable from this data:

1. **Extreme gradient sensitivity** — a narrow, high-curvature valley where cost
   changes quadratically but the gradient changes fast.
2. **Finite-difference Jacobian noise** — the gradient is `J^T r` with `J` built
   by finite differences. Near a minimum the true gradient is ~0, so the computed
   one is dominated by FD error, which scales with residual magnitude. This would
   also explain why the arm with ~2x larger residuals shows a far larger
   optimality.

(2) is the more consequential hypothesis: if FD error dominates, then
`optimality` in **every** benchmark record this library writes is partly
measuring Jacobian noise rather than conditioning. `experiments/fd_jacobian_accuracy.py`
already exists and is the natural instrument. Discriminator: recompute the
gradient at a fixed solution with a higher-accuracy (or analytic) Jacobian and
see whether the reported optimality falls.

The genuine conditioning gap survives either way: after restarts, non-refractive
2.16 vs refractive 0.00116. The arm really is worse-conditioned -- roughly 43x
less dramatically than the headline number implied.

## Finding 6 — the Huber knee explains the arms' asymmetry

Measured independently of the restart machinery, so unaffected by the defect above:

| Solve | median \|r\| | p90 \|r\| | past knee (`f_scale` = 1.0) |
|---|---|---|---|
| refractive, interface | 0.3357 | 0.8232 | **4.5%** |
| refractive, intrinsic | 0.3351 | 0.8226 | **4.5%** |
| non-refractive, interface | 0.9444 | 2.8225 | **47.7%** |
| non-refractive, intrinsic | 0.6174 | 1.8233 | **29.4%** |

The refractive arm sits almost entirely inside the quadratic region; a third to a
half of the non-refractive arm's residuals are past the knee, in the linear
regime where curvature collapses. A 6-10x difference in how much of the problem
is effectively linearized is a sufficient explanation for the non-refractive
arm's earlier `ftol` trip and larger apparent gradient.

**Open, and now an estimator question rather than a convergence one:** the
baseline is optimized under a robust loss whose knee suits the *other* arm's
residual scale. A symmetric rule -- `f_scale = 3 x median|r|` -- reproduces the
status quo for the refractive arm almost exactly (3 x 0.3357 = 1.007 vs the
current 1.0) while moving the baseline to ~2.8 / ~1.9. That rule changes nothing
about the method and only re-tunes the baseline, so it is the defensible form of
the test. Comparison metric must be **accuracy, not cost** -- changing `f_scale`
changes the objective, so costs are not comparable across runs.

---

# Follow-up 2: FD-noise discriminator (2026-08-17)

**Script:** `probe_fd_noise.py` · **Raw:** `fd_noise.json` · **Log:** `fd_noise.log`

Self-validation gate passed on all four calls: the production Jacobian
reproduced scipy's *reported* optimality to `rel_err = 0.00e+00`, confirming the
huber `rho` triple, `scale_for_robust_loss_function`, and Coleman-Li norm were
reimplemented correctly before any Jacobian was swapped.

## Finding 7 — FD noise is NOT the driver; the gradient is real

| Call | reported (production J) | 3-point J | production / 3-point |
|---|---|---|---|
| 1 refractive, interface | 0.00114616 | 0.00165518 | 0.69 |
| 2 refractive, intrinsic | 0.0247357 | 0.0244392 | 1.012 |
| 3 non-refractive, interface | 1.44454 | 1.44444 | 1.000 |
| 4 non-refractive, intrinsic | **92.7841** | **92.7843** | **1.000** |

**The 92.78 agrees with a central-difference Jacobian to five significant
figures.** Hypothesis 2 (FD noise dominating a near-zero true gradient) is
falsified. `optimality` in this library measures a real gradient, not Jacobian
error, and no benchmark record needs re-interpreting on those grounds.

## Finding 8 — hypothesis 1 confirmed: severe ill-conditioning

With the gradient established as real and accurate, the warm-restart result
(Finding 5) admits only one reading: the restart genuinely moved to a nearby
point with a far smaller gradient while cost barely changed. Order of magnitude
from call 4 -- cost fell 2.7e-5 against a gradient of 92.78, so the step was
~3e-7; the gradient fell ~90 over that step, implying directional curvature
~3e8.

So the solution sits in an extremely narrow, high-curvature valley. Cost is flat
along the floor while the gradient swings by 43x. **This is genuine
ill-conditioning, measured -- not an artifact, and not the pin.**

## Finding 9 — the library's FD step choice is validated, and the failure mode is magnitude-dependent

The step-size sweep is a strong positive result for the library:

| Call | production | 2-pt 1e-6 | 2-pt 1e-8 | 2-pt 1e-10 |
|---|---|---|---|---|
| 1 | 0.00114616 | 1.3256 | 127.93 | 6793.3 |
| 4 | 92.7841 | 92.7843 | 92.7839 | 98.286 |

Naive step choices are catastrophic where the true gradient is small (call 1
inflates by 6 orders at `rel_step` 1e-10), and harmless where it is large (call 4
is stable across every step tried). The production Jacobian tracks the 3-point
reference in both regimes, so **whatever step rule the library uses is doing its
job**.

The practical consequence is a *magnitude-dependent* reliability rule, which is
sharper than the existing "never quote optimality beyond 1 significant figure":

- **large optimality values are trustworthy** (92.78 is real to 5 s.f.)
- **small ones are not** -- call 1's production 0.001146 against the 3-point
  reference 0.001655 is a 44% disagreement, so differences between two small
  optimality values carry no information

That asymmetry matters for anyone comparing the refractive arm's 0.0247 against
the non-refractive 92.78: the *large* number is solid, the *small* one is soft,
and the gap is real regardless.

## Net position across all three probes

1. E1's baseline is converged; the comparison is fair; the 97-178x band stands. ✓
2. The pinned `water_z` contributes 0.00% of reported optimality — the mechanism
   in Phase 23's documents is wrong, though its acceptance criteria are unaffected. ✓
3. `optimality` is a real gradient measure, not FD noise. ✓
4. It is nonetheless **unstable at a fixed solution (43x)** because the problem is
   genuinely, severely ill-conditioned — and it mixes three Coleman-Li scaling
   regimes across parameter blocks, so it is not comparable across blocks either.

Nothing here is a defect in any shipped number. The open item is **interpretive**:
`optimality_stage3_interface_optimization` ships in `benchmark_grid.csv` and
`benchmark_grid.tex` to Zenodo, where a reader meets a volatile, block-incomparable,
magnitude-dependent quantity with no caveat attached. That is the same shape as
MF-17 (E7's vacuous `no_signature` nulls), which FIX-04 has just addressed by
labelling.
