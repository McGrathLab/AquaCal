---
created: 2026-08-14T00:00:00.000Z
title: E6's Z-error metrics are mean-absolute and un-gauge-corrected, so ~80% of the line layout's reported error is a datum artifact
area: experiments
files:
  - experiments/e6_generalization_sweep.py
  - src/aquacal/datasets/pipelines.py
  - .planning/MANUSCRIPT-FINDINGS.md
---

## Problem

MF-12 identified two defects in how E6 reports Z errors and proposed fixes for both. Neither
has been actioned. Both must land **before** the full-suite re-run, because both change the
CSV schema and the values written into it — fixing them afterwards means re-running.

**1. `water_z_error_mm_mean` is a mean *absolute* error.** It therefore destroys the sign that
distinguishes a harmless global datum shift from a real standoff failure. This is exactly the
distinction MF-12 had to recover by hand: the `layout/line` configuration reports a 18.9 mm
worst-seed water-surface error, of which roughly 80% is the rig and the surface sliding
through the world frame *together*, leaving the physical camera-to-surface gap `h_c` off by
only 0.36 mm.

**2. E6 never passes `gauge_correct_z`.** `experiments/e6_generalization_sweep.py:518`:

```python
per_camera_errors = compute_per_camera_errors(result, scenario)
```

`compute_per_camera_errors` declares `gauge_correct_z: bool = False`
(`src/aquacal/datasets/pipelines.py:269-273`), and its own docstring says that without the
correction "a global datum offset the optimizer applied to the entire rig (an artifact of
choosing where 'Z=0' is, not a real geometric error) is charged entirely to every
non-reference camera", making cross-camera Z comparisons "attribution-confounded".

**E1 already gets this right and E6 does not**, which is the sharpest argument for the fix:
`experiments/e1_refractive_comparison.py:391` passes `gauge_correct_z=True`. The two
experiments currently report Z errors on different bases.

## Why this is urgent rather than tidy

`supplement.tex` §12 carries the collinear-array deployment caveat, and it is the one
deployment warning the manuscript issues. Its numbers currently come from a hand-run
reconstruction of what these metrics should have reported. If the re-run reproduces the same
uncorrected mean-absolute column, the next person to read `generalization_sweep_band.csv`
draws the same wrong conclusion the raw column invited the first time — that a collinear array
is thirty times worse at locating the water surface, rather than about four times worse at
recovering the physical standoff.

## Solution

- Add `water_z_error_mm_signed` alongside the existing mean-absolute column. Append it, do not
  replace — existing consumers key on the current column and existing artifacts must stay
  readable.
- Either pass `gauge_correct_z=True` at `e6_generalization_sweep.py:518`, or emit both the raw
  and gauge-corrected per-camera Z errors. **Emitting both is preferable**: the raw value is
  what a user sees in their own diagnostics, and the corrected value is what supports a
  geometric claim. Publishing only the corrected column would hide the datum shift rather than
  explain it.
- Bump the CSV schema version if E6 guards its column set; record the bump in the SUMMARY.
- Add per-camera `h_c` error to the emitted record — see the companion TODO
  `2026-08-14-emit-per-camera-gauge-decomposition-for-layout-axis.md`, which needs the same
  call site and should be implemented in one pass.

## Do not

- Do not remove or redefine `water_z_error_mm_mean`. Committed artifacts and the current
  supplement both reference it; a redefinition under the same name makes old and new runs
  silently incomparable.
- Do not apply the correction inside `compute_per_camera_errors` by changing its default.
  `gauge_correct_z=False` is the documented default and other callers rely on it; the fix
  belongs at E6's call site.
- Do not treat this as cosmetic because reprojection and reconstruction look clean. That is
  the point of the finding: MF-12 measured the worst collinear seed costing only 0.11 px of
  reprojection RMS and 0.045 mm of reconstruction MAE, so a calibration that has slid its
  datum passes every accuracy check available at calibration time.

## Related

- `.planning/MANUSCRIPT-FINDINGS.md` MF-12, "The metric defect this exposed" — the origin of
  both items, both listed there as "fixable and neither yet fixed".
- Companion: `2026-08-14-emit-per-camera-gauge-decomposition-for-layout-axis.md`.
- Filed from the AquaCal manuscript goal-4 audit
  (`Spinoffs/papers/aquacal/AUDIT-goal4.md`, TODO ledger T-03/T-04).
