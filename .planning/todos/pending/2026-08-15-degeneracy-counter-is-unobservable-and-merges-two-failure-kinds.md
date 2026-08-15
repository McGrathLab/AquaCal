---
created: 2026-08-15T00:00:00.000Z
title: The degeneracy counter never reaches the production benchmark record, merges two distinct failure kinds, and is not persisted at all by E5 or the band runs
area: observability
files:
  - src/aquacal/calibration/pipeline.py
  - src/aquacal/calibration/interface_estimation.py
  - src/aquacal/calibration/refinement.py
  - src/aquacal/calibration/_observability.py
  - experiments/e5_index_sensitivity.py
---

## Problem

`degenerate_observations_at_solution` is the library's own gate quantity — the project's rule
(`19.3-07-PLAN.md:120–128`) is that a production configuration recording a non-zero count is
`status == "degenerate"`, never `"ok"`. Three separate defects make that quantity hard or
impossible to read off the committed artifacts.

**1. It never reaches the production `benchmark.json`.** The counter is bumped at
`interface_estimation.py:413` and `refinement.py:319`, accumulated by
`run_calibration_from_config` into `discard_stats` (`pipeline.py:1623`), and written into
`diagnostics.json`. But `pipeline.py:1709`'s `problem_shape` dict — the payload
`io/benchmark.py:458` writes into `benchmark.json` — does not carry it. Experiment scripts that
thread `discard_stats_out` themselves (E1 `:322`, E4 `:873`, E7 `:329`) do get the field into
their benchmark records; the production pipeline writer does not. The headline 13-camera
calibration's count of **198** therefore survives only in `diagnostics.json`, which is why the
manuscript audit needed three artifacts to establish a number that belongs in the benchmark
record.

**2. It merges two failure kinds that have opposite consequences.** One `_bump` covers both
pinhole-extended observations (above the interface, or beyond the critical angle — the
continuation is C0, retains gradient in board pose and extrinsics, carries *zero* gradient in
`water_z`) and behind-camera observations (flat `INVALID_PROJECTION_PENALTY_PX`, identically
zero Jacobian). `MANUSCRIPT-FINDINGS.md:1878–1882` already recommended splitting the counter
and filed it as "small, low-risk, belongs with the post-Zenodo repair batch"; it was never
actioned. The audit had to downgrade a claim from verified to probable purely because the
merged count cannot tell the two apart.

**3. E5 and the band runs do not persist it anywhere.** `index_sensitivity.csv` has no such
column (verified: its header ends `...num_comparisons,num_frames`). `19.2-29-SUMMARY.md`
records E5 hitting 3 degenerate observations and
`2026-08-05-verify-non-refractive-baseline-supports-paper-claims.md` logs counts of **14907,
2128 and 1134** from the 19.4 production queue — none of which appear in any committed
artifact. The audit's sweep over committed artifacts was exhaustive and still missed these,
because they exist only in run logs.

## Solution

Land all three before the full-suite re-run; two of them change artifact schemas, so a run
without them reproduces the same blind spots.

- Add `degenerate_observations_at_solution` to `pipeline.py:1709`'s `problem_shape`. The value
  is already in scope in `discard_stats`. One line.
- Split the counter at both bump sites into `degenerate_observations_extended` and
  `degenerate_observations_penalized`, and keep the existing merged key as their sum so no
  consumer (`_observability.py:89`, `check_rerun_gates.py:212`, the E4/E6 gates) breaks. The
  distinction is available where the guard fires — the penalized branch is exactly the
  behind-camera case in `_optim_common.py:701–709`.
- Give every experiment that can produce a non-zero count a persisted column: E5's
  `index_sensitivity.csv` and its seed-band sibling, and the band runs. E1/E4/E6/E7 already
  thread `discard_stats_out`; E5 threads it internally (`e5_index_sensitivity.py:460, 579`)
  but does not write it out.

## Do not

- Do not drop or rename the merged key. It is what the production gate and the re-run gates
  read, and the manuscript's ledger quotes it.
- Do not add a threshold or tolerance while touching this. `19.3-07-PLAN.md` is emphatic: the
  production gate stays exactly `count > 0 -> degenerate`. Whether that gate should apply to
  real-rig runs at all is a separate question — see
  `2026-08-15-degeneracy-gate-scope-and-warning-text.md`.
- Do not treat a non-zero count as a bug to be suppressed. On a physical rig it is a fact about
  the deployment; the point of this work is to make it visible, not to make it go away.

## Related

- `.planning/MANUSCRIPT-FINDINGS.md:1878–1882` — the split-the-counter recommendation, unactioned.
- Companion: `2026-08-15-classify-the-198-unprojectable-observations.md` (composes with the split).
- Companion: `2026-08-15-degeneracy-gate-scope-and-warning-text.md`.
- Overlaps `2026-08-05-verify-non-refractive-baseline-supports-paper-claims.md`, which logs the
  three unrecorded 19.4 counts.
- Filed from the AquaCal manuscript goal-4 audit
  (`Spinoffs/papers/aquacal/AUDIT-goal4.md`, findings F-003 and F-009a, TODO ledger T-05/T-12/T-14).
