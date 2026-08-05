---
created: 2026-08-05T00:00:00.000Z
title: Verify the n_water=1.0 baseline can carry the paper's refractive-vs-non-refractive claims
area: manuscript
files:
  - experiments/e1_refractive_comparison.py
  - src/aquacal/calibration/_optim_common.py
  - .planning/MANUSCRIPT-FINDINGS.md
  - "OneDrive - Georgia Institute of Technology/Thesis/Spinoffs/papers/aquacal/main.tex"
---

## Problem

Raised 2026-08-05 while watching the 19.4 production queue. Every
`DegenerateObservationWarning` in the entire run comes from the `n_water=1.0`
arm — the refractive arm reports **zero**:

```
n_water=1.0: 14949 degenerate observation(s) …   (also 14907, 2128, 1134)
```

The guard states that first-order optimality *and* reprojection RMS "cannot be
trusted to judge convergence" for that arm. So **the non-refractive baseline's
solve cannot be certified converged** — and that baseline is the comparison
point for a large block of §3 and the abstract's headline.

### The claims that depend on it

All from `main.tex`:

| line | claim |
|---|---|
| 68 | **abstract**: 1.9 mm depth RMSE, "${\sim}135\times$ improvement over non-refractive calibration" |
| 268 | protocol: baseline "run in the same optimization framework with $n_\text{water}=1.0$, **so that refraction modeling is the sole experimental variable**" |
| 270 | focal drift 0.033% refractive vs **5.7%** non-refractive |
| 271 | reprojection RMS 0.498 px vs **1.376 px** ("nearly 3× higher") |
| 278 | baseline U-shape: 0.82 → 0.50 → 0.96 mm |
| 280 | $Z$/$XY$ ratio stable 2.3 vs **swinging 0.4–5.8** |
| 281, 295 | deepest point: **257 mm** vs 1.9 mm, "approximately $135\times$" |

### The tension worth naming

`e1_refractive_comparison.py:34` says plainly: **"E1 carries NO accuracy claim
(D-19.3-17 demoted it)."** Only E7 survived that gate. Yet every number in the
table above is an E1 output. The paper leans on numbers the project has already
declined to certify — that gap is the actual finding here, and it is independent
of the degenerate-observation question.

Compounding it, MF-08 records a **97–178× spread** in the deepest-point ratio
across seeds. The abstract's "~135×" is one seed inside that band, quoted to
three digits. See also the robustness ranking: the abstract leads with the most
fragile claim in the paper.

## What is already established (do not re-litigate)

1. **The guard is about convergence certification, not accuracy.** E1's accuracy
   is measured against known ground truth, which does not route through
   optimality. Anti-pattern #2 (never judge convergence by reprojection RMS) is
   the guard working, not a new failure.
2. **At n=1 the pinhole fallback is arguably exact, not approximate.** The
   trigger is a geometric predicate (`refractive_geometry.py:531-533`,
   `h_q <= 0`) evaluated before any Snell computation and independent of
   `n_water`. With `n_air = n_water = 1.0`, Snell gives θ₁ = θ₂, so the
   refractive projection *is* the pinhole projection everywhere and the
   C0-but-not-C1 kink has zero magnitude on that arm. **This reasoning is from
   source reading and has not been verified numerically — verify before relying
   on it.**
3. **The boards are not protruding in ground truth.** The refractive arm reports
   zero degenerate observations. The n=1.0 optimizer is *lifting board poses
   above the interface itself*, because a straight-line model cannot fit
   refracted observations — a symptom of the effect E1 measures, not a scenario
   defect.
4. **E1 is inert under 19.4** (resolves to `generate_real_rig_array()`'s frozen
   shared `water_z`, never reaches `generate_camera_array`), so none of this
   moved this phase. 14949 matches the known MF-08 guard count.

## The open question

If the baseline is reported at a **non-converged** solution, its error is
inflated by an unknown amount, and line 268's "sole experimental variable"
framing is wrong: the arms differ in refraction modeling *and* in whether the
solve reached its optimum. Every ratio in the table is then an upper bound of
unknown tightness rather than a measurement.

Note the specific hazard at line 271: the paper quotes the baseline's 1.376 px
reprojection RMS as evidence of "residual systematic error a pinhole model
cannot absorb." That is exactly the quantity the guard says is untrustworthy for
this arm. The claim may still be true — but the cited evidence is the disallowed
one.

## How to settle it

1. Confirm point 2 numerically: on the n=1.0 arm, check that the pinhole
   extension and the refractive projector agree to machine precision for
   below-interface points, and that the reported optimality is therefore
   pessimistic rather than meaningless. If they agree, the baseline **is**
   converged and most of this dissolves.
2. Check whether any degenerate observations are the *behind-camera* kind
   (which yields NaN, `_optim_common.py:68-69`) rather than above-interface.
   Final costs are finite, which suggests none — but that is an inference, not
   a check.
3. Establish whether the baseline's error is dominated by model misspecification
   or by an unconverged solve — e.g. restart the n=1.0 arm from the ground-truth
   pose and see whether it lands in the same place.
4. Decide the prose consequence. Options, in increasing cost: reframe the ratios
   as bounds; attach the MF-08 seed band to the abstract's ~135×; or move the
   headline comparison onto a claim E7 can support. **Do not resolve this by
   relaxing a gate or re-tuning the solver** (anti-patterns #3, #5).
5. Log the outcome as a new MF-NN and route the prose edits through MF-09, which
   is the manuscript edit map.

## Sequencing

Blocked until the 19.4 production queue finishes and its artifacts are
committed — investigating requires running E1, which must not happen while the
queue holds the tree. Not a 19.4 obligation; plan 10 already owns three separate
items. Belongs to the manuscript-revision work (phases 20–22, SoftwareX deadline
2026-08-21).
