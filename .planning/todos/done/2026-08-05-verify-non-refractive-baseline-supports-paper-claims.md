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

## Resolution (Phase 21, plan 12)

Steps 1, 2, 4, 5 of "How to settle it" are done, by measurement rather than source
reading. Recorded as **MF-18** in `.planning/MANUSCRIPT-FINDINGS.md`, routed through
MF-09's edit map (UPDATE 2026-08-10 section).

- **Step 1 (n=1 identity):** CONFIRMED numerically. At `n_air = n_water = 1.0`,
  `refractive_project`/`refractive_project_batch` agree with the plain pinhole
  projection to `atol=1e-12` for below-interface points. Pinned by
  `tests/unit/test_refractive_geometry.py::TestUnitIndexPinholeIdentity::test_projection_reduces_to_pinhole_at_unit_index`.
  Consequence: the baseline's reported optimality is pessimistic, not meaningless — the
  baseline **is** converged, and line 268's "sole experimental variable" framing stands.
- **Step 2 (behind-camera classification):** **Cannot be settled from committed
  artifacts** — `degenerate_observations_at_solution` in
  `e1_benchmark_nonrefractive.json` is a single merged counter for both the
  above-interface and behind-camera kinds, with no committed field that splits them.
  Named as an instrumentation gap in MF-18, not guessed around. A small constructed
  case (not committed) confirmed both mechanisms are real and reachable in the code.
- **Step 4 (prose consequence):** the cheapest option — leave L268/L271's convergence
  framing as-is — is now the correct one. The band-attachment edit MF-16 already
  specifies at L68/L281 remains the only action item; MF-18 adds none.
- **Step 5 (log as MF-NN, route through MF-09):** done — see MF-18 and MF-09's
  "UPDATE 2026-08-10" section.

**Step 3 (restart the n=1.0 arm from the ground-truth pose) is still OPEN.** It is now
moot for the specific convergence question this todo raised, but may still be of
independent interest for characterizing the non-refractive baseline's error
decomposition. Routed to HANDOFF.json's deferred post-Zenodo repair batch alongside the
related water_z-pinned-baseline item. This todo is left in `pending/` rather than moved
to `done/` because of this open step.

## Closed (2026-08-15, author decision)

The titled question is settled and the residue has owners. Closing.

- **The question this todo asks** — can the `n_water = 1.0` baseline carry §3's
  refractive-vs-non-refractive claims — is answered YES by MF-18: at unit index the refractive
  projector *is* the pinhole projector (`atol=1e-12`, pinned by
  `tests/unit/test_refractive_geometry.py::TestUnitIndexPinholeIdentity`), so the reported
  optimality is pessimistic rather than meaningless, the baseline is converged, and
  `main.tex:268`'s "sole experimental variable" framing stands.
- **Step 2** (split the merged degenerate-observation counter) is owned by
  `2026-08-15-degeneracy-counter-is-unobservable-and-merges-two-failure-kinds.md`, which covers
  it more thoroughly than this todo framed it.
- **Step 3** (restart the n=1.0 arm from the ground-truth pose) is superseded by
  `2026-08-15-pin-water-z-in-e1-non-refractive-arm.md`, which is the same experiment with a
  better rationale and **has already been measured**: pinning `water_z` at ground truth drives
  the arm's guard count 14,949 → 0 and optimality 9e+02 → 5e-01 while reproducing every
  non-refractive reconstruction number to ~4 significant figures (2.5 m Z-RMSE
  248.267 → 248.221 mm). That is step 3's "does it land in the same place" question, answered:
  yes, to −0.019%. The remaining work is landing the pin, which that todo owns.
- The misleading degeneracy this todo first noticed now has a named root cause — `water_z` is an
  **exact null direction** at unit index (cost constant to 13 significant figures over a 1.5 m
  sweep) — and a named fix, in the companion todo. Nothing here is dropped.

Related and still open: `2026-08-14-decide-whether-e1-may-carry-absolute-accuracy-claims.md`,
which carries this todo's genuinely unresolved half — that §3 quotes E1 numbers throughout while
E1 is documented as carrying no accuracy claim under D-19.3-17. That gap was always a separate
question and is tracked separately.
