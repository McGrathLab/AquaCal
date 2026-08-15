---
created: 2026-08-15T00:00:00.000Z
title: E6's Z-error reporting is mean-absolute and un-gauge-corrected, and the per-camera decomposition behind the collinear caveat was never committed — one call site, one fix
area: experiments
resolves_phase: 23
files:
  - experiments/e6_generalization_sweep.py
  - src/aquacal/datasets/pipelines.py
  - .planning/MANUSCRIPT-FINDINGS.md
---

> **Merged 2026-08-15** from `2026-08-14-e6-z-error-metrics-destroy-sign-and-skip-gauge-correction.md`
> (T-03/T-04) and `2026-08-14-emit-per-camera-gauge-decomposition-for-layout-axis.md` (T-01/T-02).
> Both changed the same call site and each instructed the implementer to do it with the other.
> Kept apart, the live risk was one landing without the other and producing a half-corrected
> column — worse than either original state.

## Problem

Three defects in how E6 reports Z error, all rooted at one line.

**1. `water_z_error_mm_mean` is a mean *absolute* error**, so it destroys the sign that separates
a harmless global datum shift from a real standoff failure. `layout/line` reports an 18.9 mm
worst-seed water-surface error of which roughly 80% is the rig and the surface sliding through the
world frame *together*, leaving the physical camera-to-surface gap `h_c` off by only **0.36 mm**.

**2. E6 never passes `gauge_correct_z`.** `experiments/e6_generalization_sweep.py:518`:

```python
per_camera_errors = compute_per_camera_errors(result, scenario)
```

`compute_per_camera_errors` declares `gauge_correct_z: bool = False`
(`src/aquacal/datasets/pipelines.py:269-273`), and its own docstring says that without the
correction "a global datum offset the optimizer applied to the entire rig … is charged entirely
to every non-reference camera", making cross-camera Z comparisons "attribution-confounded".
**E1 already passes `gauge_correct_z=True`** (`e1_refractive_comparison.py:391`) — the two
experiments currently report Z errors on different bases.

**3. The decomposition behind the collinear caveat is not a committed artifact, and it hides a
camera subset.** Four numbers — 79.5% and 4.6% (share of Z-error magnitude removed by a global
datum shift, line vs grid) and ~2.4 mm / ~0.6 mm (per-camera `h_c` error after datum removal) —
come from what MF-12 calls a **zero-artifact** re-solve at seed 43. Nothing was written to disk
and no analysis script exists. `generalization_sweep_band.csv` carries only per-configuration
`_mean` columns, so no aggregation of committed data reproduces them. Worse, the 2.4 / 0.6 figures
exclude **`cam0` and `cam1` of 12** — `cam0` principled (the pinned reference, whose `h_c` error is
*identically* the `water_z` error), `cam1` discretionary ("poorly constrained", i.e. the
worst-behaved camera dropped after seeing the data) — and the prose says "per-camera" unqualified.

**What does reproduce, and is worth preserving:** the mechanism. Seed 43's
`water_z_error_mm_mean` is 18.8547 and `z_position_error_mm_mean` is −18.4947 (opposite sign
conventions); the difference is **0.3600 mm**, matching MF-12's reported `h_c` signed mean to the
digit. The re-solve was faithful to the production run — only its output was never kept.

## Why it must land before the run

All three change the CSV schema and the values written into it. A re-run that reproduces the
uncorrected mean-absolute column invites the next reader to the same wrong conclusion the raw
column invited the first time — that a collinear array is thirty times worse at locating the water
surface, rather than about four times worse at recovering the physical standoff.

## Solution — one pass at `e6_generalization_sweep.py:518`

- Add `water_z_error_mm_signed` **alongside** the existing mean-absolute column. Append, do not
  replace; existing artifacts must stay readable.
- Call `compute_per_camera_errors` twice, `gauge_correct_z=False` and `True`, and **emit both**.
  The raw value is what a user sees in their own diagnostics; the corrected value is what supports
  a geometric claim. Publishing only the corrected column would hide the datum shift rather than
  explain it.
- Emit a **per-camera** table — one row per (configuration, seed, camera) — carrying raw Z error,
  gauge-corrected Z error, and `h_c` error. Per-camera rather than pre-aggregated is the whole
  point: it lets any reader apply or reject the `cam0`/`cam1` exclusions themselves.
- Run the layout axis at **all six seeds (42–47)**, not seed 43 alone. Inside a full sweep the
  extra five cost almost nothing and turn the caveat from an anecdote into a band.
- Bump the CSV schema version if E6 guards its column set, and record the bump in the SUMMARY.
- Record the exact derivation of the four quantities — which columns, which aggregation, which
  cameras — in `.planning/MANUSCRIPT-FINDINGS.md`, so ledger rows can be written on the manuscript
  side against a real artifact.

## Do not

- Do not remove or redefine `water_z_error_mm_mean`. A redefinition under the same name makes old
  and new runs silently incomparable.
- Do not change `compute_per_camera_errors`' default. `gauge_correct_z=False` is documented and
  other callers rely on it; the fix belongs at E6's call site.
- Do not drop `cam1` silently in the emitted artifact. Emit every camera; any exclusion is
  declared downstream, not baked into the data.
- Do not emit only the aggregated 2.4 / 0.6 mm figures — emit the per-camera rows so both the
  subset average and the all-12 figure are derivable.
- Do not re-derive the four numbers by hand a second time. The reason this exists is that the
  first hand-derivation was correct but unreproducible.
- Do not treat this as cosmetic because reprojection and reconstruction look clean. That is the
  finding: MF-12 measured the worst collinear seed costing only 0.11 px of reprojection RMS and
  0.045 mm of reconstruction MAE, so a calibration that has slid its datum passes every accuracy
  check available at calibration time.
- Do not weaken MF-12's framing to make the fix easier. "About four times worse at recovering the
  physical standoff — not the thirty times the raw column suggests" is the correct reading; the
  deficiency is provenance, not interpretation.

## Related

- `.planning/MANUSCRIPT-FINDINGS.md` MF-12, "The metric defect this exposed" — origin of all
  three defects and of the camera exclusion.
- Filed from the AquaCal manuscript goal-4 audit
  (`Spinoffs/papers/aquacal/AUDIT-goal4.md`, findings F-007 and F-011, TODO ledger T-01–T-04).

## Scope boundary — artifacts, not prose

Library and experiment work only. The manuscript tree (`Spinoffs/papers/aquacal/` — `main.tex`,
`supplement.tex`, `response-letter.md`, `numbers-ledger.tsv`) is **read-only from this repo**.
Where a fix has a manuscript consequence the deliverable is the **evidence, not the sentence**:
emit the artifact, record the derivation in `.planning/MANUSCRIPT-FINDINGS.md`, and let the
manuscript session write the prose and the ledger rows. References to `supplement.tex` line
numbers here are motivation, never work orders.

## Register the outputs with the driver and the gate (added 2026-08-15)

**Last step of this fix, not an afterthought.**
`2026-08-15-make-the-suite-driver-cover-every-invocation.md` requires that every schema- or
value-changing fix add its outputs to the suite driver's stage list and to the completeness gate's
expected-artifact list, and asks each such todo to say so. This is that clause — it was missing
from every one of them until now, which is exactly the unenforced coupling that todo warned about.

For this fix specifically: E6 gains `water_z_error_mm_signed`, the gauge-corrected columns, and a new per-camera table (one row per configuration x seed x camera). The per-camera table is a NEW artifact the gate does not know exists, and the layout axis moves from one seed to six -- both change expected row counts.

Also add the same expectations to the sheet in
`2026-08-15-suspend-programmatic-check-for-reshaped-artifacts.md`, since hand-verification is the
only check covering these artifacts during this run.
