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
