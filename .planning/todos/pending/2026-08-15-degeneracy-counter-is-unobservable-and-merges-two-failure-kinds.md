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
  - experiments/check_rerun_gates.py
  - tests/unit/test_e5_band_mode.py
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

## ⚠ Third defect, found by the 2026-08-15 scoping probe and confirmed for E2

**`degenerate_observations_at_solution` is a running total across optimization stages. The name
asserts something false, and the real rig's 198 is not a solution-state count.**

Measured in E1's band log: line 1033's reported `1134` is two warnings summing — **70** from Stage 3
(`pipelines.py:140`) plus **1064** from the intrinsic pass (`:177`). The other four lines carry a
single warning and so happen to look correct.

Mechanically confirmed in source, for both the synthetic and the production path:

- `_bump()` accumulates: `stats[key] = stats.get(key, 0) + n` (`_observability.py:113`).
- `calibrate_synthetic` passes **one** `discard_stats_out` dict to three call sites
  (`pipelines.py:129`, `:159`, `:192`).
- **`run_calibration_from_config`** declares `discard_stats: dict[str, int] = {}` once at
  `pipeline.py:766` and passes that same object to **six** call sites (`:808`, `:915`, `:1031`,
  `:1107`, `:1280`, `:1439`) with **no reset between stages**.

  **Measured correction (2026-08-15): for E2 the sum has exactly two terms, not six.** Only
  `interface_estimation.py:413` and `refinement.py:319` bump *this* key; the other four call sites
  bump `pnp_*` counters. E2's `benchmark.json` carries exactly two stages with residuals —
  `stage3_interface_optimization` (nfev 44) and `stage3_intrinsic_pass` (nfev 15), both at
  `n_residuals = 147950`. So **198 = interface-optimization count + intrinsic-pass count**, the
  double-counting factor is at most 2, and the intrinsic pass's own count — being last — is the
  closest thing to a true solution-state number. An earlier "up to six" framing in this todo
  overstated it and is superseded here.

**So the counter merges along three axes, not two:** failure kind, *and* stage, *and* repeated
evaluation of the same observation across stages.

**The split must therefore be per-stage as well as per-kind.** A split by failure kind alone still
leaves a number that sums across up to six solves, which measures nothing at a solution. Emit
per-stage counts keyed by the same stage vocabulary the diagnostics already use
(`stage3_interface_optimization`, `stage3_intrinsic_pass`, …), and keep the merged key as the total
so existing consumers and `check_rerun_gates.py` do not break.

**Manuscript consequence, handled on the other side:** the drafted F-003 disclosure quotes "198 of
73,975 observations (0.27%)" and "`water_z` estimated from the remaining 99.7%" — both assume a
solution-state count and are wrong against a cross-stage sum. The audit's F-006 0.268% inherits it.
Flagged to the manuscript session; **do not attempt to fix the prose from this repo.** What this
TODO owes them is a counter whose value means what its name says.

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
- **Update `check_rerun_gates.py` in the same commit.** It reads `_GUARD_COLUMN` from three
  locations (`:212–218`) and warns "cannot confirm zero" when the field is absent (`:355`) — which
  is exactly the production `benchmark.json` gap above. Plumbing the field lets the gate see the
  headline run for the first time; splitting the counter without touching the gate would leave it
  reading a key that no longer means what it did.
- **While `test_e5_band_mode.py` is open, put its `TestBandMode` tests on a `scope="module"`
  fixture** mirroring `test_e6_band_mode.py:74`. Absorbed from the retired
  `2026-08-06-e5-band-tests-rerun-the-band-per-test.md`: E5's five tests currently re-run the band
  per test (317 s against E6's 93.89 s for six tests). The ~210 s saving is incidental — the reason
  to do it here is that these tests need updating for the new column anyway, and refactoring them
  while already editing them is free. Test-time only; changes no artifact and does not gate the run.

## Do not

- Do not drop or rename the merged key. It is what the production gate and the re-run gates
  read, and the manuscript's ledger quotes it.
- Do not add a threshold or tolerance while touching this. `19.3-07-PLAN.md` is emphatic: the
  production gate stays exactly `count > 0 -> degenerate`. Whether that gate should apply to
  real-rig runs at all is a separate question — see
  `2026-08-15-decide-degeneracy-gate-scope-for-real-rig-runs.md` (it was split out of
  `…-narrow-the-degenerate-observation-warning.md`, which this line used to point at).
- Do not treat a non-zero count as a bug to be suppressed. On a physical rig it is a fact about
  the deployment; the point of this work is to make it visible, not to make it go away.

## Related

- `.planning/MANUSCRIPT-FINDINGS.md:1878–1882` — the split-the-counter recommendation, unactioned.
- Companion: `2026-08-15-classify-the-198-unprojectable-observations.md` (composes with the split).
- Companion: `2026-08-15-narrow-the-degenerate-observation-warning.md`.
- Overlaps `2026-08-05-verify-non-refractive-baseline-supports-paper-claims.md`, which logs the
  three unrecorded 19.4 counts.
- Filed from the AquaCal manuscript goal-4 audit
  (`Spinoffs/papers/aquacal/AUDIT-goal4.md`, findings F-003 and F-009a, TODO ledger T-05/T-12/T-14).

## Scope boundary — artifacts, not prose

This TODO is library and experiment work only. The manuscript tree (`Spinoffs/papers/aquacal/` —
`main.tex`, `supplement.tex`, `response-letter.md`, `numbers-ledger.tsv`) is **read-only from this
repo and must not be edited here**, including "obviously correct" single-number updates.

Where a fix has a manuscript consequence, the deliverable is the **evidence, not the sentence**:
emit the artifact, and record the derivation in `.planning/MANUSCRIPT-FINDINGS.md`. Incorporating
it into the paper — prose, ledger rows, captions, figure captions — happens in the manuscript
session, which owns that tree and the word budget.

References to `main.tex` / `supplement.tex` line numbers anywhere in this file are **motivation and
provenance**, never work orders.

## Register the outputs with the driver and the gate (added 2026-08-15)

**Last step of this fix, not an afterthought.**
`2026-08-15-make-the-suite-driver-cover-every-invocation.md` requires that every schema- or
value-changing fix add its outputs to the suite driver's stage list and to the completeness gate's
expected-artifact list, and asks each such todo to say so. This is that clause — it was missing
from every one of them until now, which is exactly the unenforced coupling that todo warned about.

For this fix specifically: the split adds per-kind and per-stage columns wherever the counter is recorded, and gives E5 and the band runs a persisted column they have never had. The gate should assert the columns exist AND that the synthetic counts are zero once the `water_z` pin lands -- a zero that is present is evidence; a column that is absent is not.

Also add the same expectations to the sheet in
`2026-08-15-suspend-programmatic-check-for-reshaped-artifacts.md`, since hand-verification is the
only check covering these artifacts during this run.
