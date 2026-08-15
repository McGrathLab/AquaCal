---
created: 2026-08-15T00:00:00.000Z
title: Make the degeneracy question answerable from the re-run's artifacts — split the counter by stage as well as kind, and correct the cause list before it ships in a warning
area: observability
files:
  - src/aquacal/calibration/_observability.py
  - src/aquacal/calibration/refinement.py
  - src/aquacal/calibration/interface_estimation.py
  - src/aquacal/calibration/_optim_common.py
  - src/aquacal/datasets/pipelines.py
---

## Why this exists

Filed 2026-08-15 from measurements taken while scoping the fix milestone (findings report:
`Desktop/aquacal-scoping-probes-findings-2026-08-15.md`). Three facts turned up that change what
the sibling degeneracy todos should do, and one of them would otherwise put a **false statement into
a user-facing warning**.

The unifying point: the full-suite re-run is the last chance to make the degeneracy question
answerable without yet another run. Today the artifacts cannot distinguish a benign, exactly-modelled
observation from one that would invalidate a calibration. Fixing that is a small, additive
instrumentation change — but it has to land *before* the run, not after.

---

## Finding 1 — the pinhole continuation is not merely "continuous", it is **exactly correct** for the case that fires

`_optim_common.py:50-61` justifies the pinhole extension as *"the unique continuous extension"* — a
numerical-continuity argument about not putting a jump in the residual. True, and the C0-not-C1
reasoning is right. But it undersells the actual situation for the dominant trigger.

The projection path's invalid conditions are exactly two (`_refractive_project_newton_batch`, which
is what `refractive_project_batch` at `_optim_common.py:695` resolves to):

| trigger | meaning | is the pinhole continuation right? |
|---|---|---|
| `h_q <= 0` | corner at or **above** the water surface | **Yes — exactly, not approximately** |
| `h_c <= 0` | **camera** at or below the surface | **No — genuinely wrong** |
| `r_q < 1e-10` | corner directly beneath the camera | not invalid; handled correctly as an on-axis case |

When `h_q <= 0`, the corner is in air and the camera is in air (`h_c > 0` is checked first), so the
light path **never crosses the interface**. Air the whole way. A pinhole projection with
air-calibrated intrinsics *is* the correct physical model for that observation — it is not a
fallback. (At `n_water = 1.0` it is exact for a second, independent reason: MF-18 pins refractive ==
pinhole to `atol=1e-12` at unit index.)

**Consequence for the warning rewrite:** the alarm is aimed at the wrong thing. Nothing is
mis-modelled in the common case. The one real consequence is narrower and already measured — an
above-surface observation carries **zero `water_z` gradient**, so `water_z` is estimated from fewer
observations (73,777 of 73,975 on the real rig, 0.268%). Every other parameter keeps full gradient.

**`h_c <= 0` is the case that deserves alarm and currently gets none of its own.** A camera at or
below the surface sends the *entire* batch to the pinhole path with air-calibrated intrinsics, used
underwater where effective focal length scales with `n_water`. That is a real modelling error. It
presumably never fires on a rig whose cameras sit above the water by construction — but it is
indistinguishable in the record from the benign case, so nobody would know if it did.

**Behind-camera is a third distinct behaviour**, not a pinhole continuation at all: it keeps NaN
through `_extend_invalid_projections` and then takes a flat `INVALID_PROJECTION_PENALTY_PX`
(`_optim_common.py:709`) — a constant with no gradient.

---

## Finding 2 — SUPERSEDED 2026-08-15, absorbed and extended elsewhere

> **This finding now lives in
> `2026-08-15-degeneracy-counter-is-unobservable-and-merges-two-failure-kinds.md` § "Third defect",
> in a stronger form — read that, not this.** It was written there independently and went further:
> the production path (`run_calibration_from_config`) declares one `discard_stats` dict at
> `pipeline.py:766` and passes it to **six** bump sites with no reset, so the real rig's 198 is a
> sum over up to six evaluations and double-counts observations unprojectable in two stages. What
> was "flagged, not established" below is now **established** for E2. The per-stage split and the
> keep-the-merged-key requirement are specified there.
>
> Retained below only as the E1-side evidence trail that first surfaced it.

### Original text — `degenerate_observations_at_solution` accumulates across stages

It is not a count at the solution. It is a running total over up to three separate final-solution
evaluations.

- `_bump()` accumulates: `stats[key] = stats.get(key, 0) + n` (`_observability.py:113`)
- `calibrate_synthetic` passes **the same dict object** to interface estimation
  (`pipelines.py:129`), Stage-3 joint refinement (`:159`), and the intrinsic pass (`:192`)
- both writers use it: `interface_estimation.py:413`, `refinement.py:319`

**Measured proof:** `experiments/rerun_19_4.log:1033` reports `1134`, which is two separate warnings
summing — `70` from Stage 3 (`pipelines.py:140`) plus `1064` from the intrinsic pass
(`pipelines.py:177`). The other four occurrences carry a single warning and so happen to look
correct.

So the counter merges along **two** axes, not one. The sibling todo
`2026-08-15-degeneracy-counter-is-unobservable-and-merges-two-failure-kinds.md` scopes the split by
**kind**; it also needs splitting by **stage**, or the result is still a number summed over three
solves.

**This reaches the real rig's 198.** That figure is currently reasoned about as a solution-state
count — the 0.268% argument in
`2026-08-15-decide-degeneracy-gate-scope-for-real-rig-runs.md` divides it by a single observation
total. If 198 is a sum over Stage 3 plus the intrinsic pass, that denominator needs restating.
**Flagged, not established** — it was outside the probe's scope and must be checked against E2's own
record rather than inferred from E1's mechanism.

---

## Finding 3 — beyond-critical-angle obliquity is NOT a trigger, and must not be written into the warning

`2026-08-15-narrow-the-degenerate-observation-warning.md` currently instructs: *"Add
beyond-critical-angle obliquity to the cause list in both warnings."* **Do not do this as written.**
It would ship a cause that the projection path cannot produce.

Evidence, in increasing strength:

1. **There is no TIR check in the projection path.** The only one in the library is
   `sin_t_sq > 1.0` inside `refract_ray` — and `refract_ray` has **zero callers anywhere in
   `src/`**. The residual path never evaluates it.
2. **Measured directly (2026-08-15, ground-truth geometry, seed 42):**

   | preset | cameras × frames | corner observations | unprojectable | max straight-line incidence |
   |---|---|---|---|---|
   | `ideal` | 4 × 20 | 7,040 | **0** | 27.4° |
   | `realistic` | 12 × 30 | 31,680 | **0** | **61.5°** |

   `realistic` projects every corner cleanly at chord incidences up to 61.5°, well past the
   48.61° water-side critical angle. Obliquity at these geometries does not trigger the guard.
3. **`ideal` produces zero unprojectable corners at ground truth**, contradicting the inference in
   `19.3-ORCHESTRATOR-NOTES.md` §4 that its geometry is intrinsically responsible.

**The likely real explanation, and it is a better one — but it is a HYPOTHESIS, confirm it during
the run.** The guard counts at the **optimizer's solution**, not at the scenario's ground truth.
`19.3-ORCHESTRATOR-NOTES.md` §4's "0/1760 corners above the surface" is a ground-truth statement;
the guard count is a solution-state statement. They are not comparable, which is exactly why that
note reached for obliquity to explain the gap. During optimization the estimated `water_z` and board
poses move, and a corner near the surface can end up above the *estimated* interface even when it
was below the true one. That would make the count a diagnostic of solver excursion rather than of
authored geometry — a more useful reading, and one the per-stage split in Finding 2 would expose
directly.

---

## What this todo still owes, after the overlap was absorbed

**The counter split (per kind, per stage, keep the merged key) is specified in
`…-merges-two-failure-kinds.md` and is NOT restated here.** The per-observation emission for the
real rig is specified as item 1 of
`2026-08-15-classify-the-198-unprojectable-observations.md`'s Solution — also not restated.

What remains uniquely here:

1. **Add `camera_submerged` (`h_c <= 0`) as its own kind, not folded into "extended".** The sibling
   todo's split is `extended` vs `penalized`, which maps to above-interface vs behind-camera. A
   submerged camera is a *third* kind with a different meaning — it is the one case where the
   pinhole continuation is genuinely wrong (air-calibrated intrinsics used underwater, where
   effective focal length scales with `n_water`). It should be distinguishable, and arguably should
   fail loudly rather than count quietly. It presumably never fires on this rig; the point is that
   nobody could tell if it did.
2. **Record the observation denominator** alongside the count, per stage. Every "0.268%"-style claim
   currently reconstructs it by hand from a different artifact, and
   `2026-08-15-decide-degeneracy-gate-scope-for-real-rig-runs.md` leans on exactly such a
   reconstruction.
3. **Correct the cause list before it ships in a warning** — Finding 3 below. This is the one item
   with a deadline attached: it is currently written as an instruction to *add* a false cause.

## Do not

- **Do not add beyond-critical-angle obliquity to any warning's cause list** until someone
  demonstrates the projection path can produce it. See Finding 3.
- **Do not treat this as a correctness fix to the pinhole continuation.** The continuation is right;
  the bookkeeping and the label around it are not. Changing the projection maths is out of scope and
  would move every synthetic number in the suite.
- Do not drop or rename the merged key. The production gate and the re-run gates read it.
- Do not soften the synthetic `count > 0 -> degenerate` gate while doing this — that is the separate
  deferred policy decision, and `19.3-07-PLAN.md` is explicit that it stays exact.
- Do not assert that the real rig's 198 is a cross-stage sum. Check it.

## Related

- `2026-08-15-degeneracy-counter-is-unobservable-and-merges-two-failure-kinds.md` — **owns the
  counter split.** It absorbed the per-stage finding on 2026-08-15 and extended it to the
  production path's six bump sites. This todo adds only the `camera_submerged` kind and the
  denominator.
- `2026-08-15-narrow-the-degenerate-observation-warning.md` — Finding 1 gives it a sharper
  consequence clause; **Finding 3 contradicts one of its Solution bullets**.
- `2026-08-15-classify-the-198-unprojectable-observations.md` — **owns the per-observation
  emission.** Finding 3 here retires its obliquity/TIR bucket and supplies the real three-way NaN
  inventory.
- `2026-08-15-decide-degeneracy-gate-scope-for-real-rig-runs.md` — its 0.268% denominator argument
  depends on 198 being a solution-state count, which Finding 2 puts in question.
- `2026-08-15-pin-water-z-in-e1-non-refractive-arm.md` — after it lands, the rig's 198 is the only
  non-zero count left in the suite.
- Measurements and raw data: `Desktop/aquacal-scoping-probes-findings-2026-08-15.md`.
