---
created: 2026-08-15T00:00:00.000Z
title: The production degeneracy gate's scope over real-rig runs is written down nowhere, and the warning it raises is measurably over-broad
area: policy
files:
  - src/aquacal/calibration/refinement.py
  - src/aquacal/calibration/interface_estimation.py
  - src/aquacal/config/schema.py
  - experiments/e4_benchmark_grid.py
  - experiments/e6_generalization_sweep.py
---

## Problem

Two halves of the same question: what a non-zero `degenerate_observations_at_solution` means,
and how the library says so.

**1. The gate's scope is undocumented, and the real rig sits outside it by accident.**
`19.3-07-PLAN.md:120–128` mandates that a PRODUCTION configuration recording
`degenerate_observations_at_solution > 0` gets `status == "degenerate"`, **never `"ok"`**, and
is excluded from every aggregation, table and published summary — with no threshold and no fuzz
factor. Every synthetic production cell measures 0 and passes. The **headline real-rig
calibration measures 198 and is published as converged.**

The gate does not literally apply, because it is implemented in `e4_benchmark_grid.py` and
`e6_generalization_sweep.py` — the synthetic harnesses — and E2 runs through neither. The
distinction is defensible and probably right: in a synthetic scenario the geometry is *authored*,
so an unprojectable observation means the scenario is malformed and the cell should be discarded;
on a physical rig the geometry is *given*, and a small unprojectable fraction is a fact about the
deployment rather than a construction error. But that argument exists nowhere in writing. A
reviewer reading the repository finds a project that discards synthetic cells at `count > 0` and
publishes a real calibration at `count = 198`, with no sentence reconciling the two.

**2. The warning's consequence clause is over-broad.** `refinement.py:322–332` tells the user
first-order optimality "is UNRELIABLE as a convergence measure here, and neither it nor the
reprojection RMS can be trusted to judge convergence", then instructs "Fix the scenario geometry
so no corner sits at or above the interface". That text is calibrated for the failure it was
written for — E6-style wrong scenario geometry parking whole frames across the boundary — and it
is measurably wrong about a sub-percent tail on a physical rig:

- The continuation is **C0** (values agree to ~5e-6 px at $h_q = \pm 10^{-8}$) and **not C1**
  (one-sided $\partial\text{px}/\partial h_q$ ratio 0.7035, stable under step refinement). The
  kink is real, but it is a property of the boundary surface $h_q = 0$, and the 198 are not
  sitting *on* it — they are on the pinhole side, where the objective is smooth.
- The one true consequence is bounded: above the interface the `water_z` gradient is identically
  zero, so `water_z` is estimated from 73,777 of 73,975 observations. **0.268%.**
- The instruction "fix the scenario geometry" is not actionable for a user calibrating hardware
  they did not author.

The `interface_estimation.py:426` warning shares the wording. `refinement.py`'s "corners at or
above the water surface, or behind a camera" is also incomplete — the guard's other live trigger
is beyond-critical-angle obliquity, which fires with zero corners above the surface.

## Solution

- **Record the gate's scope decision** where the gate lives, not only in a planning file: either
  the gate is synthetic-only by design (state the authored-vs-given-geometry rationale in
  `_observability.py` and the harnesses' guard blocks), or it extends to real-rig runs and the
  production pipeline must report `status` accordingly. Decide it; do not leave it implicit.
- **Narrow the warning's consequence clause** to what is true: the continuation is continuous but
  not differentiable at the boundary, observations continued through it carry no `water_z`
  gradient, and the reported optimality remains meaningful for the parameters that do retain
  gradient. Scale the alarm to the count — whole-frame degeneracy warrants the current text; a
  sub-percent tail does not.
- **Complete the cause list** in both warnings: add beyond-critical-angle obliquity alongside
  above-surface and behind-camera.
- Replace the unconditional "fix the scenario geometry" instruction with advice that
  distinguishes synthetic scenarios (where it is the right fix) from measured rigs (where it is
  not available).

## Do not

- Do not soften the synthetic gate itself into a threshold while doing this. `19.3-07-PLAN.md` is
  explicit that it stays exactly `count > 0 -> degenerate`, with a smoke-path carve-out only.
- Do not weaken the warning to the point where E6's real failure mode stops being loud. The
  defect is that one text serves two very different situations, not that the text is too strong.
- Do not claim the continuation is smooth. It is C0 and not C1 — `refinement.py:322–332` is
  correct on that point and `_optim_common.py:50–61` never asserted otherwise (it raises the
  C0-not-C1 objection against a hinge penalty the code deliberately does not use). The genuinely
  wrong statement is in commit `7e0cb90`'s message, which claims smoothness in `water_z`.

## Related

- `2026-08-15-degeneracy-counter-is-unobservable-and-merges-two-failure-kinds.md` — the counter
  split makes the warning able to say *which* kind fired.
- `2026-08-15-classify-the-198-unprojectable-observations.md`.
- Filed from the AquaCal manuscript goal-4 audit
  (`Spinoffs/papers/aquacal/AUDIT-goal4.md`, findings F-006 and F-009b, TODO ledger T-09/T-11).
  The C0/C1 and zero-gradient results there were measured directly against the unmodified library.
