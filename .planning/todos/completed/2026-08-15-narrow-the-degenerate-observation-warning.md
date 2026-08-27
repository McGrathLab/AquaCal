---
created: 2026-08-15T00:00:00.000Z
title: The degenerate-observation warning is measurably over-broad and its cause list is incomplete
area: library
resolves_phase: 24
files:
  - src/aquacal/calibration/refinement.py
  - src/aquacal/calibration/interface_estimation.py
  - src/aquacal/config/schema.py
---

> **Split 2026-08-15.** This todo previously bundled a text fix with a policy decision (does the
> production degeneracy gate apply to real-rig runs?). The two were wrongly sequenced: the
> decision cannot be made sensibly until `2026-08-15-classify-the-198-unprojectable-observations.md`
> reports what the 198 actually are. The decision half now lives in
> `2026-08-15-decide-degeneracy-gate-scope-for-real-rig-runs.md` and is deferred. What remains here
> is unambiguous and lands in the fix pass.

## Problem

`refinement.py:322–332` tells the user that first-order optimality "is UNRELIABLE as a convergence
measure here, and neither it nor the reprojection RMS can be trusted to judge convergence", then
instructs: "Fix the scenario geometry so no corner sits at or above the interface; do not re-tune
the solver." `interface_estimation.py:426` carries the same wording.

That text is calibrated for the failure it was written for — E6-style wrong scenario geometry
parking whole frames across the boundary. It is measurably wrong about a sub-percent tail on a
physical rig, and the production calibration is exactly that case at 198 of 73,975 observations.

**Measured directly against the unmodified library:**

- The continuation is **C0** — values agree to ~5e-6 px at `h_q = ±1e-8`.
- It is **not C1** — one-sided `∂px/∂h_q` differ by a stable ratio of **0.7035**, converging under
  step refinement, identical for the u and v components. The kink is real.
- But the kink is a property of the boundary surface `h_q = 0`, and the flagged observations are
  not sitting *on* it — they are on the pinhole side, where the objective is smooth.
- Above the interface the **`water_z` gradient is identically zero** (the one-sided derivative
  scales exactly inversely with the finite-difference step). So the one true consequence is bounded:
  `water_z` is estimated from 73,777 of 73,975 observations. **0.268%.**

**The cause list is also incomplete.** Both warnings name "corners at or above the water surface,
or behind a camera". ~~The guard's other live trigger is **beyond-critical-angle obliquity**~~ —
**REFUTED 2026-08-15, see the struck Solution bullet below; this paragraph is retained only to
show what was believed.** ~~a
corner whose water-side exit angle exceeds `arcsin(1/1.333) = 48.61°` cannot leave the water, so~~
forward projection returns NaN. `19.3-ORCHESTRATOR-NOTES.md` §4 records this firing on
`create_scenario("ideal")` with **0 of 1760 corners above the surface**.

**And the instruction is not actionable for the case that most often triggers it.** "Fix the
scenario geometry" is right for an authored synthetic scenario and meaningless to a user
calibrating hardware they did not author.

## Solution

- Narrow the consequence clause to what is true: the continuation is continuous but not
  differentiable at the boundary; observations continued through it carry no `water_z` gradient;
  the reported optimality remains meaningful for the parameters that do retain gradient.
- Scale the alarm to the count. Whole-frame degeneracy warrants the current volume; a sub-percent
  tail does not.
- ~~Add beyond-critical-angle obliquity to the cause list in both warnings.~~ **CONTESTED
  2026-08-15 — do not action as written.** The projection path has no TIR check (`refract_ray`,
  the only one, has zero callers in `src/`), and measurement found **0 unprojectable corners** on
  both `ideal` (7,040 obs) and `realistic` (31,680 obs) at ground truth — `realistic` projects
  cleanly at chord incidences up to 61.5°, past the 48.61° critical angle. The correct cause list
  is `h_q <= 0` (above surface), `h_c <= 0` (camera submerged), and behind-camera (flat penalty,
  not a pinhole continuation). See
  `2026-08-15-degeneracy-instrumentation-the-rerun-must-emit.md` Finding 3, which also proposes the
  better explanation for `ideal`'s 12: the guard counts at the **solution**, not at ground truth.
- Replace the unconditional "fix the scenario geometry" with advice that distinguishes synthetic
  scenarios (where it is the fix) from measured rigs (where it is not available).

## Do not

- Do not claim the continuation is smooth. It is C0 and not C1 — `refinement.py:322–332` is correct
  on that point, and `_optim_common.py:50–61` never asserted otherwise (it raises the C0-not-C1
  objection against a hinge penalty the code deliberately does not use). The genuinely wrong
  statement is in commit `7e0cb90`'s message, which claims smoothness in `water_z`.
- Do not weaken the warning to the point where E6's real failure mode stops being loud. The defect
  is that one text serves two very different situations, not that it is too strong.
- Do not touch the synthetic production gate here. That is the deferred decision.

## Related

- `2026-08-15-degeneracy-counter-is-unobservable-and-merges-two-failure-kinds.md` — the counter
  split lets the warning name *which* kind fired.
- `2026-08-15-decide-degeneracy-gate-scope-for-real-rig-runs.md` — the deferred half.
- Filed from the AquaCal manuscript goal-4 audit
  (`Spinoffs/papers/aquacal/AUDIT-goal4.md`, finding F-006).

## Scope boundary — artifacts, not prose

Library work only. The manuscript tree (`Spinoffs/papers/aquacal/`) is read-only from this repo.
