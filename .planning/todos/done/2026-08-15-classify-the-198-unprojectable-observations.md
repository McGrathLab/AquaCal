---
created: 2026-08-15T00:00:00.000Z
title: Nobody knows what the production rig's 198 unprojectable observations actually are
area: experiments
resolves_phase: 25
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

> **⚠ Trigger (b) below was REFUTED on 2026-08-15 — see the section at the end of this file
> before building anything on it.** The projection path has no TIR check, and zero
> unprojectable corners were measured on both presets at ground truth. The two bullets are
> retained to show what was believed and why.

- **Breached interface** — the board raised through the water surface. Now the leading
  explanation: `reconstruction_errors.csv` shows **31 of 7762 validation corners (0.40%)
  reconstructing up to 51.7 mm above the interface, concentrated in 2 of 52 frames**. That rate
  matches the 198's 0.27%, and the same board, operator and session produced both frame sets.
- **Beyond the critical angle** — `refractive_geometry.py:516` records the *air-side* incidence
  angle, but forward projection runs water→air, so a corner is visible only if its water-side
  exit angle stays under $\theta_c = \arcsin(1/1.333) = 48.61°$. `19.3-ORCHESTRATOR-NOTES.md` §4
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

   **There is exactly one E2 run in the suite, and this is it.** Make the logging a permanent,
   always-on diagnostic rather than a temporary patch: the flagged population is a few hundred rows
   on a 73,975-observation solve, so the cost is nil, and a permanent diagnostic means the next
   person to meet a non-zero count gets the answer for free. Do **not** run E2 twice — once
   instrumented and once clean — which would put two real-rig records in a suite whose entire
   premise is one source of truth.
3. Classify into (a) `h_q <= 0`, at or above the interface; (b) `h_q > 0` but exit angle >
   48.61°, obliquity/TIR **(refuted — see below; expect this bucket to be empty)**; (c) neither
   — a third mechanism worth understanding.
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

---

## ⚠ Trigger (b) — obliquity / TIR — appears EMPTY BY CONSTRUCTION (2026-08-15)

The Problem section above gives the guard "two trigger conditions", the second being
beyond-critical-angle obliquity, and concludes "the remaining work is apportioning them, not
discovering which applies". Measurement and source reading both say bucket (b) cannot be populated
by the projection path. **Check this before building the classifier around three buckets.**

**1. There is no TIR check in the path.** The library's only one is `sin_t_sq > 1.0` inside
`refract_ray` — and `refract_ray` has **zero callers anywhere in `src/`**. The residual path runs
`_optim_common.py:695` → `refractive_project_batch` → `_refractive_project_newton_batch`, which
never evaluates it.

**2. TIR cannot fire for this direction of travel, geometrically.** The Newton solve returns the
crossing point satisfying `n_a sin θ_a = n_w sin θ_w` with θ_a < 90°, so
`sin θ_w = sin θ_a / 1.333 < 1/1.333` and **θ_w < 48.61° always, at the solution, by construction**.
A submerged point viewed from an above-water camera always admits a valid path.

**3. Measured, ground-truth geometry, seed 42:**

| preset | cameras × frames | corner observations | unprojectable | max straight-line incidence |
|---|---|---|---|---|
| `ideal` | 4 × 20 | 7,040 | **0** | 27.4° |
| `realistic` | 12 × 30 | 31,680 | **0** | **61.5°** |

`realistic` projects every corner cleanly at chord incidences up to 61.5° — well past 48.61°.

**4. The `ideal` precedent is misread.** `19.3-ORCHESTRATOR-NOTES.md` §4 infers obliquity because
`ideal` showed 12 flagged observations with "0/1760 corners above the surface". But that 0/1760 is a
**ground-truth** statement and the guard counts at the **optimizer's solution**. They are not
comparable, which is precisely why the note reached for obliquity to explain the gap. `ideal`
produces **zero** unprojectable corners at ground truth, so its geometry is not intrinsically
responsible.

## The actual NaN inventory for the residual path

Complete, from source. Newton non-convergence does **not** produce NaN — the loop exits after
`max_iterations` and uses the current `r_p`.

| # | condition | meaning |
|---|---|---|
| 1 | `h_c <= 0` | camera at/below the surface → **entire batch** NaN |
| 2 | `h_q <= 0` | corner at/above the surface (at the **estimated** interface, not the true one) |
| 3 | `camera.project(interface_point)` returns `None` | the interface-crossing point fails the camera model — a camera-model failure, not TIR |

So the classification buckets should be **(a) `h_q <= 0` at the estimated geometry, (b) camera-model
projection failure on the crossing point, (c) camera submerged** — with the obliquity/TIR bucket
retired unless someone demonstrates it. Item 1 of the Solution already records `h_q`, `r_q` and the
extension-succeeded flag, which distinguishes all three; the exit-angle column is still worth
emitting, but as evidence that (b) is not TIR rather than as a bucket boundary.

**Leading explanation, unchanged and arguably strengthened:** breached interface. Retiring (b)
removes the alternative that was competing with it for the 0.27%.

Method and raw data: `Desktop/aquacal-scoping-probes-findings-2026-08-15.md` §2 and the follow-up
degeneracy-cause probe.

### Bucket (c) is eliminated for E2, by measurement (2026-08-15)

The camera-submerged condition (`h_c <= 0`) **cannot fire on the real rig**. Measured from
`experiments/results/camera_parameters.csv`: `h_c` runs **1.0472–1.1125 m across all 13 cameras**,
every value positive. Emit the bucket anyway — it costs nothing and the assertion is worth having
in the artifact — but a non-empty (c) on E2 would mean the recovered geometry is grossly wrong,
not that the rig was flooded.

So for E2 the live buckets reduce to **(a) `h_q <= 0` at the estimated geometry** and **(b)
camera-model projection failure on the crossing point**.

## Instrumentation design — hook point, scope, and sizing (2026-08-15)

**Hook the existing post-solve counting evaluation, not the optimizer's cost function.** Both bump
sites already perform a dedicated residual evaluation at `result.x` whose only purpose is counting
— `interface_estimation.py:410–413` and `refinement.py:318–319`, both calling
`compute_residuals(result.x, *cost_args, invalid_count_out=...)`. `invalid_count_out` is opt-in and
stays `None` throughout the optimization. Extend that call with a detail sink.

**This is a ~1000× decision, not a style preference:**

| hook | calls per stage | E2 rows | worst case in the suite |
|---|---|---|---|
| **post-solve at `result.x`** (existing) | 1 | **~198 total** | ~198 |
| inside `compute_residuals` (the FD-evaluated cost fn) | ≈ nfev × (1 + 17 CPR groups) ≈ 800 | ~160k | **~480M rows, tens of GB** |

The worst case is real and would run unattended overnight: E1's non-refractive arm flags 14,949
observations on *every* evaluation, so per-call logging across 10 seeds × 4 noise levels is roughly
480 million rows. **Post-pin the entire suite's flagged population is E2's ~198** — the `water_z`
pin zeroes E1's non-refractive arm, the P1 probe measured zero on the refractive arm at every noise
level including 1.2 px, and E5/E6/E7 record zero in every committed artifact.

**Add a hard row cap per stage** (order 50k), log that truncation occurred, and keep the count
exact. Not because we expect to hit it, but because unattended-overnight is exactly when a
pathological configuration fills a disk.

### Log raw quantities; classify offline

Record `(camera, frame_idx, corner_id, h_q, h_c, r_q, exit angle, extension-succeeded, **stage**)`
and do the bucketing afterwards. **The taxonomy has been revised twice in two days** — obliquity
retired, camera-model failure added — and there is exactly one E2 run. A classifier that stores
bucket *labels* has to be right in advance; one that stores raw geometry does not.

`stage` is mandatory, not optional: the counter is a cross-stage sum, so a per-observation record
without its stage cannot be reconciled against the total.

### `h_q` for all observations — E2 only

Log `h_q` for the **entire** observation set, not just the flagged ones, **on E2 and nowhere else**.

- **E2 — yes.** ~74k rows per stage, ~10 MB. Its geometry is *given*, so the distribution of how
  close the real board came to the surface is a fact about the deployment that nothing else
  records. It is the difference between "198 corners were above the interface" and "the board was
  skimming the surface in these frames" — a count versus an explanation.
- **E1, E4, E5, E7 — no.** Authored geometry: the interface is generated at exactly `[0, 0, -1]`
  with `WATER_Z` frozen, so the distribution is a property of the scenario generator and derivable
  analytically. Full logging across E1's 40 runs would be tens of GB for zero information.
- **E6 — no.** Tempting (does the collinear datum slide correlate with board-to-interface
  proximity?) but speculative, and 14 configurations × 6 seeds is where the footprint would hurt.
  Flagged-only, which is free at zero rows.

**Flagged-only logging is permanently on; full-population logging is behind a flag the suite driver
passes for E2.** A user calibrating their own rig should not get a 10 MB sidecar on every run —
which makes this one more flag the driver must pass explicitly, so register it there
(`2026-08-15-make-the-suite-driver-cover-every-invocation.md`).

### ⚠ Hook the optimizer's residual path, not the reprojection export

`per_corner_residuals` (in `calibration.json`) and `reprojection_residuals.csv` both hold **23,028
observations across 13 cameras including the auxiliary fisheye** — which is excluded from Stages 2
and 3 entirely. The stage-3 residual vector covers **73,975 observations over 12 cameras**
(`n_residuals = 147950`). They differ by more than 3×.

The exports are a post-hoc reprojection evaluation, **not** the optimizer's residual vector.
Anything built against them silently measures the wrong population. This also kills a shortcut that
looked promising: hunting the flat 100 px `INVALID_PROJECTION_PENALTY_PX` in the exported residuals
to detect behind-camera cases. The exports top out at 75.98 px with nothing at or above 99 — but
that is **not evidence**, because a penalty could fire inside the solve and never reach the export.
Recorded so nobody re-runs that check and draws a conclusion from it.

## Register the outputs with the driver and the gate (added 2026-08-15)

**Last step of this fix, not an afterthought.**
`2026-08-15-make-the-suite-driver-cover-every-invocation.md` requires that every schema- or
value-changing fix add its outputs to the suite driver's stage list and to the completeness gate's
expected-artifact list, and asks each such todo to say so. This is that clause — it was missing
from every one of them until now, which is exactly the unenforced coupling that todo warned about.

For this fix specifically: the per-observation classification log is a NEW artifact produced only by the instrumented E2 run. It is the one output in this milestone that cannot be regenerated afterwards -- P4 established no committed artifact holds per-frame board placements -- so if the completeness gate does not require it, a run that omits the instrumentation looks clean and the question needs another full E2.

Also add the same expectations to the sheet in
`2026-08-15-suspend-programmatic-check-for-reshaped-artifacts.md`, since hand-verification is the
only check covering these artifacts during this run.

---

## Resolved — 2026-08-24 (phase 29.1, plan 05)

**Answer: the 198 are above-water board corners.** The classification is settled in
`.planning/MANUSCRIPT-FINDINGS.md` § **MF-24**, which carries the full derivation, every figure
tied to a named artifact path, and both surviving findings from this file. Read MF-24, not this
file, for the verdict.

### Why this closes without the work item being executed

**The opening premise was overtaken, not wrong.** This file states: *"What the 198 are is not
established, and no committed artifact can settle it."* That was true on 2026-08-15. Phase 24's
DEGEN-02 `discard_stats` threading and Phase 25's DEGEN-04 per-observation sink did not exist yet,
and the Solution section above is a design sketch **for the instrumentation that has since been
built and run**. Its four steps were all executed — by Phases 24 and 25, and by the 2026-08-20
production run at `rerun-freeze-01` — not skipped:

1. *"Patch `compute_residuals` to record per-observation geometry"* — DEGEN-04, plan 25-01,
   hooked at the post-solve counting evaluation exactly as the *Instrumentation design* section
   below specifies.
2. *"Re-run E2 under OpenCV 4.13"* — the 2026-08-20 production run, cv2 4.13.0.92, one E2 run in
   the suite.
3. *"Classify into buckets"* — `experiments/_degeneracy.py`'s `OBSERVATION_BUCKETS`, keyed on the
   library's `nan_reason` code, with the taxonomy owned outside the solver as this file asked.
4. *"Commit the per-observation table so the answer is reproducible rather than reported"* —
   **`experiments/results_e2_invocations/e2_classification/degenerate_observations.csv`**,
   198 rows × 12 columns, committed in `83da9b3`.

### The artifacts that settle it

| artifact | what it establishes |
|---|---|
| `experiments/results_e2_invocations/e2_classification/degenerate_observations.csv` | The per-observation table this file said could not exist. All 198 rows in `stage3_intrinsic_pass`, all `extended=True`, none `truncated`, `nan_reason = 2` (`above_interface`) throughout; `h_q_m` −0.064021 … −0.001251 m; 8 frames in two clusters (22-26, 102/104/105) across 8 cameras; `chord_incidence_deg` 2.797 … 29.822°. |
| `experiments/results/benchmark.json` (`discard_stats`) | 198/198 `above_interface`, 0 `behind_camera`, 0 `interface_below_camera`, 198 `extended`, 0 `penalized`, all in the intrinsic pass, over 73,975 evaluated observations. |
| `experiments/results/reconstruction_errors.csv` | The independent corroboration on a **disjoint** frame set: 31 of 7,762 held-out validation corners above the interface, up to 51.73 mm, in frames 21 and 103 — the two frames flanking the flagged clusters. |
| `experiments/results/camera_parameters.csv` | Bucket (c) eliminated by measurement: `h_c` 1.047177 … 1.112502 m across all 13 cameras. |
| `experiments/results_e2_band/seed_{42,43,44}/diagnostics.json` | The verdict is seed-invariant (100 % `above_interface`, 100 % `extended` on every seed) while the *count* is not: 198 / 210 / 183. MF-24 records this as a new §3 caveat. |

**The count was decomposed, never re-derived.** 198 is unchanged.

### What was preserved, and where

This file held two findings recorded nowhere else. Both are carried into MF-24 **in full, with
their reasoning**, not as one-line summaries:

1. **The residual-path-vs-export population trap** — the stage-3 residual vector covers 73,975
   observations over 12 cameras while `reprojection_residuals.csv` and `per_corner_residuals` hold
   23,028 over 13 including the auxiliary fisheye. Including the corollary that kills the shortcut:
   hunting the flat `INVALID_PROJECTION_PENALTY_PX` in the exports cannot detect behind-camera
   cases, so the exports' 75.98 px maximum is not evidence.
2. **The refutation of the obliquity/TIR trigger** — all three 2026-08-15 legs (no TIR check on the
   path, `θ_w < 48.61°` by construction, zero unprojectable corners at ground truth on both
   presets), plus the misreading of the `ideal` precedent, plus **a fourth leg this run supplies**:
   the flagged population's own chord incidence tops out at 29.822° against a 48.61° critical
   angle. MF-24 also records the caveat that `chord_incidence_deg` is a straight-chord surrogate
   rather than a refracted exit angle, so leg 4 is corroboration and legs 1-2 remain what make the
   refutation absolute.

### What is NOT closed by this

- **The manuscript sentence.** Nothing under `Spinoffs/papers/aquacal/` was edited. MF-24 records
  what the disclosure may now say; writing it belongs to the manuscript session, per this file's
  own *Scope boundary — artifacts, not prose*.
- **The driver/gate registration clause** (*Register the outputs with the driver and the gate*).
  Already discharged by the run itself — the classification invocation is in the suite driver and
  `degenerate_observations.csv` is an expected artifact in `suite_expectations.json`. Its
  `conditional` scoring is separately defective and is fixed by **plan 29.1-09**, not here.
