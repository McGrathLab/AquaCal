---
created: 2026-08-15T00:00:00.000Z
title: Two documentation-of-record strings are stale — real_rig_metrics.json's provenance quotes a superseded value, and synthetic.py calls a frozen constant the real-rig standoff
area: docs
files:
  - experiments/e2_real_rig.py
  - src/aquacal/datasets/synthetic.py
---

## Problem

Two strings that exist to tell the next reader where a number came from currently tell them
something false. Neither is inherited by the manuscript; both are traps for whoever reads these
files as documentation.

**1. `real_rig_metrics.json`'s provenance for `mean_per_camera_reprojection_px`.**
`e2_real_rig.py:289` writes the provenance string
`"(release diagnostics.json: 0.8786 px, quoted as 0.88)"` while the field itself holds
**0.8240** and the manuscript quotes **0.82**. The 0.8786/0.88 pair is the superseded
pre-correction value. The file is the documentation-of-record for §3's numbers and is currently
self-contradicting; the full-suite run regenerates it, so the string should be right before the
run, not after.

**2. `synthetic.py:184` misdescribes `WATER_Z`.** The `height_above_water` docstring calls the
module-level `WATER_Z` (1.031 m) "the real-rig standoff". It is not: the rig's estimated
`water_z` is **1.0738404** m and its per-camera $h_c$ range is 1.047–1.113 m. `:290` gets it right
— "a FROZEN DESIGN CONSTANT, not a live measurement" — so the module contradicts itself within a
hundred lines. The manuscript does not inherit the error (`main.tex:257` says "idealized version
… approximately 1 m" and quotes neither number), but the next person generating a scenario would.

## Solution

- Rewrite the provenance string to quote the value the field actually holds, and to name the
  derivation rather than a historical release value: the mean of
  `result.diagnostics.reprojection_error_per_camera`, as `:287` already says correctly on the
  line above. If the release comparison is worth keeping, mark it explicitly as superseded.
- Fix `synthetic.py:184` to describe 1.031 m as a frozen design constant *approximating* the rig
  standoff, consistent with `:290`. One docstring.

## Do not

- Do not change the value of `WATER_Z`. It is frozen by design (D-19.3-09) and every synthetic
  result in the manuscript depends on it; the defect is the description, not the constant.
- Do not "reconcile" it toward 1.0738 to match the rig. The synthetic rig is an approximation of
  the hardware by intent, and the manuscript frames it that way.

## Related

- Filed from the AquaCal manuscript goal-4 audit
  (`Spinoffs/papers/aquacal/AUDIT-goal4.md`, V-012 and the Pass A residual-risk log, TODO ledger
  T-08/T-10).
