---
created: 2026-08-15T00:00:00.000Z
title: Nobody knows what the production rig's 198 unprojectable observations actually are
area: experiments
files:
  - src/aquacal/calibration/_optim_common.py
  - src/aquacal/core/refractive_geometry.py
  - experiments/e2_real_rig.py
---

## Problem

The headline 13-camera calibration records `degenerate_observations_at_solution = 198` of
73,975 observations (0.27%), identically in the Zenodo archive's `diagnostics.json` and in all
three `results_e2_band/seed_{42,43,44}/diagnostics.json`. The manuscript is about to disclose
that count. **What the 198 are is not established**, and no committed artifact can settle it:
`calibration.json` stores no per-frame board placements and `reprojection_residuals.csv` carries
only residuals and a camera label.

The guard has **two** trigger conditions, not one:

- **Breached interface** — the board raised through the water surface. Now the leading
  explanation: `reconstruction_errors.csv` shows **31 of 7762 validation corners (0.40%)
  reconstructing up to 51.7 mm above the interface, concentrated in 2 of 52 frames**. That rate
  matches the 198's 0.27%, and the same board, operator and session produced both frame sets.
- **Beyond the critical angle** — `refractive_geometry.py:516` records the *air-side* incidence
  angle, but forward projection runs water→air, so a corner is visible only if its water-side
  exit angle stays under $\theta_c = \arcsin(1/1.333) = 48.75°$. `19.3-ORCHESTRATOR-NOTES.md` §4
  records this firing on `create_scenario("ideal")` with **0 of 1760 corners above the surface**
  — proof that a non-zero count is not evidence of a breach. Measured air-side maxima in
  `newton_iterations.csv` are 53.2–57.5°, i.e. water-side 39.2°, comfortably inside the limit,
  consistent with only a thin tail crossing it.

The two are not exclusive. The remaining work is apportioning them, not discovering which
applies.

## Solution

Fold the instrumented run into the full suite — standalone it costs a run, inside a sweep it
costs a patch.

1. Patch `_optim_common.compute_residuals` to record, for each observation flagged invalid at
   the solution: `(camera, frame_idx, corner_id, h_q, r_q, water-side exit angle,
   pinhole-extension succeeded?)`. `h_q = Q_z - z_int` is already computed at
   `refractive_geometry.py:629`; the exit angle follows from `r_q`, `h_q` and $n_w$.
2. Re-run E2 from the archive's `config_paper.yaml` **under OpenCV 4.13** — the pin matters, the
   count is 198 at 4.13 and 194 at 4.14 (`MANUSCRIPT-FINDINGS.md:2102`).
3. Classify into (a) `h_q <= 0`, at or above the interface; (b) `h_q > 0` but exit angle >
   48.75°, obliquity/TIR; (c) neither — a third mechanism worth understanding.
4. Commit the per-observation table so the answer is reproducible rather than reported.

**What each outcome buys.** Mostly (a): the disclosure can name the mechanism plainly ("in a
small number of frames the board was raised through the surface"), which is a better sentence
than the cause-agnostic one currently drafted, and it is benign — those observations carry zero
`water_z` gradient, so they cannot bias the interface estimate. Mostly (b): the 198 are a fixed
geometric property of a wide array over a large tank, equally benign and equally nameable.
Mixed: report the split.

## Do not

- Do not attempt the cheaper partial — instrumenting `refractive_project_batch` alone and
  evaluating it once at the committed solution. **Already attempted and rejected:** it needs
  per-frame board placements that `calibration.json` does not store, so it requires the pipeline
  to re-emit them, which is most of the run anyway.
- Do not assert a cause in the manuscript ahead of this. The disclosure sentence was
  deliberately rewritten to claim only what the counter measures, and it is true whatever the
  answer. This TODO improves the sentence; it does not gate it.
- Do not run under OpenCV 4.14 and compare against the published 198.

## Related

- Depends on the counter split in
  `2026-08-15-degeneracy-counter-is-unobservable-and-merges-two-failure-kinds.md` — with the
  split landed, the pinhole-extended/penalized breakdown is free and the classification is the
  remaining half.
- `19.3-ORCHESTRATOR-NOTES.md` §4 — the `ideal` precedent that disproves the breach-only reading.
- Filed from the AquaCal manuscript goal-4 audit
  (`Spinoffs/papers/aquacal/AUDIT-goal4.md`, findings F-009a and F-010, TODO ledger T-06).
  Author deferred the standalone run 2026-08-14; this is the folded-in version.
