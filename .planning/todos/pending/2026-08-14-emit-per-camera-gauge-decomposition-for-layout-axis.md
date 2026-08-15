---
created: 2026-08-14T00:00:00.000Z
title: The collinear-array caveat's four numbers come from an uncommitted zero-artifact re-solve and an undisclosed 10-of-12 camera subset
area: experiments
files:
  - experiments/e6_generalization_sweep.py
  - src/aquacal/datasets/pipelines.py
  - .planning/MANUSCRIPT-FINDINGS.md
---

## Problem

`supplement.tex` §12's collinear-array deployment caveat rests on four numbers that **cannot be
re-derived from any committed artifact**, and on a camera subset the prose does not disclose.

**The four numbers.** 79.5% and 4.6% (share of Z-error magnitude removed by a global datum
shift, line vs grid), and ~2.4 mm and ~0.6 mm (per-camera `h_c` error after datum removal).
MF-12 names its own source as "a **zero-artifact** re-solve of `layout/line` and `layout/grid`
at seed 43" — nothing was written to disk, and no analysis script exists in the repo.
`generalization_sweep_band.csv` carries only per-configuration `_mean` columns with no
per-camera values and no datum decomposition, so no aggregation of committed data reproduces
them.

**The undisclosed subset.** MF-12 computed the 2.4 / 0.6 mm figures "excluding `cam0` (the
reference, pinned at `C_z = 0` by construction, so its `h_c` error is *identically* the
`water_z` error) **and `cam1`** (which the solve leaves poorly constrained)". Both layouts run
12 cameras, so these are 10-of-12 averages. The supplement says "per-camera $h_c$ error" with
no qualification. The `cam0` exclusion is principled and arguably required; the `cam1`
exclusion is discretionary — the worst-behaved camera dropped from an error average after
seeing the data — and is the one a sceptical reviewer will want stated.

**What does reproduce**, and is worth preserving: the mechanism itself. Seed 43's
`water_z_error_mm_mean` is 18.8547 and its `z_position_error_mm_mean` is −18.4947 (opposite
sign conventions), and the difference is **0.3600 mm** — matching MF-12's reported `h_c` signed
mean to the digit. So the re-solve was faithful to the production run; only its output was
never kept.

## Solution

Emit the decomposition as a committed artifact so the caveat is reproducible from the archive.

- Re-solve `layout/line` and `layout/grid` — seed 43 at minimum, ideally all six seeds (42–47),
  since a six-seed table costs little inside a full sweep and makes the caveat a band rather
  than an anecdote.
- Call `compute_per_camera_errors` twice per solve, `gauge_correct_z=False` and `True`
  (`src/aquacal/datasets/pipelines.py:269`). The datum share is the reduction in Z-error
  magnitude between the two; the residual is the gauge-corrected per-camera `h_c` error.
- Commit a **per-camera** table — one row per (layout, seed, camera) — carrying raw Z error,
  gauge-corrected Z error, and `h_c` error. Per-camera rather than pre-aggregated is the whole
  point: it lets any reader apply or reject the `cam0`/`cam1` exclusions themselves rather than
  inheriting them.
- Add a ledger derivation for each of the four supplement numbers so
  `check_manuscript_numbers.py` covers them. They are currently `KEEP-VERIFIED`, which asserts
  rather than verifies.

This shares a call site with
`2026-08-14-e6-z-error-metrics-destroy-sign-and-skip-gauge-correction.md`; implement together.

## Do not

- Do not publish the aggregated 2.4 / 0.6 mm figures without stating their basis. If the
  per-camera table lands, the supplement can quote the subset average *and* the all-12 figure,
  which makes the exclusion visible instead of load-bearing.
- Do not drop `cam1` silently in the emitted artifact. Emit every camera; let the prose declare
  any exclusion.
- Do not re-derive the numbers by hand a second time. The reason this TODO exists is that the
  first hand-derivation was correct but unreproducible.
- Do not weaken MF-12's framing to make the fix easier. "About four times worse at recovering
  the physical standoff — not the thirty times the raw column suggests" is the correct reading
  and the supplement states it; the deficiency is provenance, not interpretation.

## Related

- `.planning/MANUSCRIPT-FINDINGS.md` MF-12 — origin of all four numbers and of the exclusion.
- Companion: `2026-08-14-e6-z-error-metrics-destroy-sign-and-skip-gauge-correction.md`.
- Filed from the AquaCal manuscript goal-4 audit
  (`Spinoffs/papers/aquacal/AUDIT-goal4.md`, findings F-007 and F-011, TODO ledger T-01/T-02).
