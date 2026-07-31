# Manuscript Findings

Measured results from the v1.9 experiment suite that **contradict, understate, or otherwise
require a change to** prose in the manuscript or supplement.

This file exists because experiment output and manuscript prose live in different trees: the
manuscript is read-only from here (OneDrive), so a finding surfaced by a script has no natural
place to land. Anything recorded here needs a human editing pass on the paper before submission.

Each entry names the artifact that is the citable source, so the correction is made against
measured data rather than against this summary.

---

## MF-01 — Newton iteration count: the supplement understates the tail

**Status:** open — needs a prose edit, **and its source is under review (see caveat below)**
**Found:** 2026-07-29, phase 19.2 plan 19.2-05 (E3 tier 2, per D-20)
**Source of truth:** `experiments/results/newton_iterations.csv`
**Where the prose is:** supplement, the refractive-projection convergence claim

> **⚠ Provenance caveat added 2026-07-29 (phase 19.2 code review CR-05, confirmed in source).**
> `newton_iterations.csv` is produced by `refractive_project_newton_diagnostic`, which routes
> through the shared `_solve_newton_r_p` helper. But production residual evaluation does **not**
> use that path: `calibration/_optim_common.py:635` projects via `refractive_project_batch` →
> `_refractive_project_newton_batch`, a separately inlined Newton loop that never calls
> `_solve_newton_r_p` and terminates on `np.all(np.abs(delta) < tolerance)` — all points at once,
> with no per-point convergence flag.
>
> Two consequences for the numbers below. (1) `not converged = 0` is measured for a loop the
> optimizer never runs. (2) The per-point iteration counts do not transfer: under all-points
> termination every point in a batch iterates until the *slowest* converges, so production
> per-point cost behaves like the tail, not the median — which if anything sharpens this entry's
> "understates the tail" conclusion, but on different evidence than what is tabulated here.
>
> **Resolve before citing.** Either migrate `_refractive_project_newton_batch` onto
> `_solve_newton_r_p` and regenerate, or correct the diagnostic's docstring and restate the CSV's
> scope as the scalar path. The measured distribution below is not known to be wrong — it is
> known to describe a different loop than the one the prose is about.

The supplement says the Newton solve for the refraction point converges in **"two to four
steps."** Measured over the real rig's full working volume (104,052 points, 12 cameras):

| quantity | value |
|---|---|
| iterations, min | 2 |
| iterations, **median** | **4.0** (identical on every camera) |
| iterations, **max** | **7** (6-7 per camera) |
| not converged | **0** |
| incidence angle range | 0.13 deg - 62.92 deg |
| max residual | ~1e-9 m (at tolerance) |

**The claim is right about typical behavior and wrong about the tail.** Min 2 / median 4 matches
"two to four steps" exactly. What it misses is that the distribution runs to 7 at high incidence
angles. Convergence itself is never in question: zero points failed to converge and every residual
sits at the solver tolerance.

So this is not a correctness problem in the library, and it is not grounds for weakening any
accuracy claim. It is a prose accuracy problem: a reader sizing a compute budget or reimplementing
the solver from the paper would under-provision the iteration cap.

**Suggested framing for the edit** (wording is the author's call): report the median with the
observed maximum, e.g. "typically four steps (median 4, range 2-7 over the calibrated volume,
with the upper tail at high incidence angles)."

**Do not** silently change the number to 7 — the median genuinely is 4, and 7 is the tail. Quoting
only the max would overstate typical cost as badly as "two to four" understates the tail.

---

## MF-02 — E4's memory curve does not bound a real deployment of the same camera count

**Status:** ⚠ **SUPERSEDED as to its numbers — see the staleness notice below.** The mechanism it
identifies still holds; its headline comparison does not.
**Found:** 2026-07-29, phase 19.2 (orchestrator analysis of the committed E4 grid vs E2's record)
**Source of truth:** `experiments/results/benchmark_grid.csv` (all values below are columns in it)
**Where the prose is:** wherever `benchmark_grid.csv`'s cameras × frames scaling is discussed

> **⚠ Staleness notice added 2026-07-31.** Every E4 figure below was measured on the pre-re-run
> grid. The grid was re-measured on 2026-07-30 (`5b17cd4`) after the D-29 geometry redesign and
> the PnP-guard fix, and E4's cells moved by roughly 3×:
>
> | E4 16×200 | this entry | current CSV (`5b17cd4`) | ratio |
> |---|---|---|---|
> | residuals | 54,460 | **143,098** | 2.63× |
> | peak, stage-3 interface | 3.11 GiB | **9.99 GiB** | 3.21× |
> | overall peak | 3.31 GiB | **10.45 GiB** | 3.16× |
>
> **This inverts the entry's conclusion.** E4's 16×200 cell now peaks *above* E2's real rig
> (10.45 vs 9.78 GiB), so "fewer cameras, ~3× the memory" and "do not present 16 cameras ≈ 3.3 GiB
> as a deployment figure" no longer describe the committed data. E2's row is unchanged (147,950
> residuals, 8.96 / 9.78 GiB) — it was not re-run — so the movement is entirely E4's.
>
> **What survives:** the mechanism. Peak memory still tracks residual count rather than camera
> count, and the dense-Jacobian explanation is unaffected. What changed is the observation density
> of E4's synthetic scenes, which is now far closer to the real rig's — 143,098 vs 147,950
> residuals at comparable parameter counts. The gap this entry exists to warn about has largely
> closed.
>
> **Numbers retained, not corrected, deliberately** — the same reasoning that keeps
> `code_constants.csv` stale for plan 23. Rewriting them in place would erase the evidence that
> the grid moved. Re-derive from the current CSV before citing anything here.

E4's 16-camera × 200-frame cell peaks at **3.31 GiB**, while E2's real rig at **13** cameras ×
200 frames peaks at **9.78 GiB** — fewer cameras, ~3× the memory. Both numbers are correct. A
reader who takes the grid as a deployment sizing guide would under-provision by roughly 3×.

| | params | **residuals** | Jacobian (dense) | peak, stage-3 interface |
|---|---|---|---|---|
| E4 16×200 (synthetic) | 1005 | 54,460 | 0.41 GiB | 3.11 GiB |
| E2 real rig 13×200 | 1269 | **147,950** | 1.40 GiB | 8.96 GiB |
| ratio | 1.26× | **2.72×** | 3.43× | 2.88× |

(The 3.31 / 9.78 GiB figures quoted above are the max across all stages; the table compares the
stage-3 interface optimization like-for-like. The real rig's overall peak lands in the
intrinsic-refinement pass.)

**Peak memory tracks residual count, not camera count.** The Jacobian is `n_residuals × n_params`
held **dense** — the library computes a sparse-FD Jacobian and then calls `.toarray()`, because
`jac_sparsity` forces LSMR, which diverges on these problems where dense QR converges. Peak scales
with the Jacobian (3.43×) far more closely than with parameters (1.26×). Camera count inflates the
parameter block, which is the small one.

**It is not a smaller calibration board.** E4's `GRID_BOARD_CONFIG` deliberately mirrors
`synthetic.py`'s `default_board`, commented "matches real hardware" — 12×9 squares, 60 mm square,
45 mm marker, `DICT_5X5_100`, giving 11×8 = **88 interior corners** in both the synthetic and real
cases. The difference is observation *density*, on two compounding axes:

- **Board-observing views:** E4's 16×200 cell records 1395 observations out of 16×200 = 3200
  possible camera-frame pairs — **44%**. (E4's own probe noted a median of 9 of 16 cameras
  observing.)
- **Corners per observing view:** 27,230 corners / 1395 observations = **19.5 of 88 (22%)**. The
  real rig averages 28.5 corners per camera-frame *pair* before accounting for non-observing
  pairs, so its per-observing-view density is materially higher.

Synthetic cameras see a modest slice of the board; a real ChArUco target filling the frame yields
several times the corners per view. Same board, sparser scenes.

**Suggested framing for the edit** (wording is the author's call): present the grid as a *scaling
curve in problem size* rather than a per-camera-count capacity table, and state that the real-rig
point is the one to size against, because synthetic observation density is lower than a real
deployment's. Do not present "16 cameras ≈ 3.3 GiB" as a deployment figure.

**Caveat on the data itself:** `n_observations` is not recorded for the real-rig row (it is a
pipeline-written record and the column is null), so the real rig's corners-per-observing-view
cannot be computed from committed data — only its corners-per-camera-frame-pair. Recording that
field for pipeline runs would make this comparison exact.

---

## MF-03 — E4's runtime inverts with camera count, and it is not a memory effect

**Status:** open — needs prose wherever the grid's runtime is presented as a scaling curve
**Found:** 2026-07-31, phase 19.2 (orchestrator analysis of the re-measured grid at `5b17cd4`)
**Source of truth:** `experiments/results/benchmark_grid.csv` (all values below are columns in it)
**Where the prose is:** wherever `benchmark_grid.csv`'s runtime scaling is discussed

E4's wall-clock **falls as camera count rises** at fixed frames — the opposite of problem size:

| n_frames | 8 cam | 12 cam | 16 cam |
|---|---|---|---|
| 200 | **3760 s** | 1971 s | **595 s** |
| 100 | 1171 s | 370 s | 164 s |
| 50 | 472 s | 330 s | 83 s |

(`seconds_stage3_interface_optimization`. The three `n_frames=200` cells are the only ones
carrying `memory_pressure=near_physical_ceiling`, which is what makes the memory reading tempting.)

**The inversion is convergence behavior, not memory.** It is fully explained by iteration count:
`nfev_stage3_interface_optimization` runs **107 / 110 / 118** at 8 cameras against **14 / 12 / 18**
at 16. Fewer cameras is a more weakly constrained problem, so the solver takes up to ~8× more
evaluations. Attributing this axis to paging would be wrong, and the `nfev` column is committed
alongside the timings, so a reader can check it.

**Normalizing removes the anomaly completely.** Dividing by residual-equivalent evaluations
(`nfev + njev × n_groups`, since the FD Jacobian dominates at 13 groups) and by
`n_residuals_stage3_interface_optimization` gives a per-residual cost in µs:

| n_frames | 8 cam | 12 cam | 16 cam | mean | `memory_pressure` |
|---|---|---|---|---|---|
| 50 | 13.03 | 12.79 | 13.55 | **13.1** | clean |
| 100 | 14.40 | 14.88 | 15.45 | **14.9** | clean |
| 200 | 21.07 | 20.65 | 20.79 | **20.8** | near_physical_ceiling |

Per-residual cost is **independent of camera count** — within 5% at every frame level — and depends
only on frame count. So there are two separate effects on two different axes, and conflating them
is the failure mode this entry exists to prevent:

- **Camera axis** — runtime inverts with problem size. Iteration count. No memory component.
- **Frame axis** — per-residual cost rises. This is where memory pressure lives.

**The frame-axis step is where the memory signature is.** The clean→clean step (50→100) costs
**+14%**; the clean→near-ceiling step (100→200) costs **+40%**. That ~26-point excess appears
exactly where `memory_pressure` flips and is flat across all three camera counts.

**Do not report that excess as a paging cost.** `_classify_memory_pressure` compares peak against
**total** RAM at `MEMORY_NEAR_CEILING_FRACTION = 0.5`, and the module's own docstring is explicit
that this is a measurement *condition*, not a verdict. Free RAM at run time and hard-fault counts
were never recorded, so pagefile I/O cannot be separated from ordinary working-set cache growth.
"Consistent with memory pressure" is the defensible claim; "paging cost N seconds" is not.

**Suggested framing for the edit** (wording is the author's call): present runtime per residual
evaluation rather than raw wall-clock, and state the iteration-count effect explicitly — a reader
who assumes a monotonic cost curve in N will otherwise read the table as an error. If raw
wall-clock is reported, the `nfev` column must be reported beside it.

**Two caveats on the data itself.**
- The `real_rig_13cam_200fr` row is **not comparable** to the nine grid cells: it is
  `timing_scope=end_to_end` / `record_source=pipeline` against `optimization_only` / `assembled`,
  and its `memory_pressure` is null because E2's `benchmark.json` predates D-33 — absent, not
  measured clean. It must not appear in the same timing table.
- The nine cells are one coherent measurement session on one machine. A Windows Defender exclusion
  was added to the project tree on 2026-07-31, changing I/O characteristics, so fresh timings are
  not splice-compatible with these. Re-run the whole grid or none of it.

---

## MF-04 — Section 3's published numbers came from a solve that had not converged

**Status:** open — needs a prose edit AND a decision on how to characterise it
**Found:** 2026-07-31, phase 19.2 plan 19.2-06 (the D-34 E2 re-run)
**Source of truth:** `experiments/results/real_rig_metrics.json` and `benchmark.json` at `faa05b3`;
baseline `experiments/archive/e2-2026-07-30-pre-pnp-guard/` and `git show 35d76a6:...`
**Where the prose is:** every §3 real-rig number

### The numbers moved

| quantity | published | re-run | delta |
|---|---|---|---|
| `mean_reprojection_px` | 1.019136 | 0.927661 | **−8.98%** |
| `mean_per_camera_reprojection_px` | 0.878634 | 0.824039 | −6.21% |
| `inter_corner_rmse_mm` | 0.674074 | 0.628139 | −6.81% |
| `inter_corner_mae_mm` | 0.268155 | 0.258177 | −3.72% |
| `mean_relative_error_pct` | 0.446925 | 0.430295 | −3.72% |
| `water_z_m` | 1.030555 | **1.073840** | **+4.20%** |
| `n_comparisons` | 7762 | 7762 | **0** |

`camera_height_range_m`, `reprojection_range_px` and `auxiliary_reprojection_px` also moved.

### Attribution is unusually clean

The degenerate-PnP guard (`7e0cb90`) rejected **exactly 10 poses of 3548 attempted**, measured from
`diagnostics.json`'s `discard_stats` rather than remembered. Frame rejection did not fire (0 of 200,
guardrail clear). And `n_params`, `n_groups`, `n_residuals` (147,950) and `n_comparisons` (7,762) are
all **identical** across the two runs — **the data and the problem are unchanged; only the
initialization differed.** Ten poses with translations up to 3.09e12 m were poisoning a weighted
mean, and removing them moved the solve to a different basin.

### The headline, which is not "the numbers improved slightly"

**The published record had not converged.** Its `stage3_intrinsic_pass` first-order optimality was
**2.08e4**; the re-run reaches **18.4**, a ~1000× improvement. Its reprojection RMS of 1.019 px
looked entirely publishable.

This is the project's own blocking anti-pattern #2 — *optimality is the discriminator; RMS agrees
with a broken solve* — found in the manuscript's own numbers rather than in a synthetic sweep. The
same failure mode was caught in E4's grid cells (`.continue-here.md`), where a cell shipped 0.79 px
RMS on optimality 6.4e9.

**Suggested framing (the author's call).** The honest description is not "we refined the
calibration and the numbers improved." It is that a defect in pose initialization allowed a
non-converged solution to be reported, that the defect is fixed, and that §3 now reports a
converged solve. The improvement is a *consequence* of fixing a correctness bug, not a tuning gain,
and describing it as the latter would understate what was wrong.

**Do NOT describe the movement as within noise.** E2 has no measured seed-noise band and cannot get
one without a second full run at a different config seed — verified at
`experiments/e2_real_rig.py:550-581`, where the `--config` branch returns before the seed log and
never reads `args.seed`. E1's and E7's bands are not E2's.

### Downstream: the synthetic rig's interface constant

`water_z` moving 1.0306 → 1.0738 m matters beyond §3. `datasets/synthetic.py`'s `WATER_Z = 1.031`
was documented as *"the calibrated value"* and is what `create_scenario("realistic")` — and
therefore E1, E3, E5, E7 — is built on. E4/E6's `GRID_HEIGHT_ABOVE_WATER` is coupled to it by D-29.

**Resolved 2026-07-31 by decision, not by re-derivation.** `WATER_Z` stays at **1.031** and is
relabelled a **frozen design constant** with its provenance recorded in source: it came from a
calibration now known not to have converged, it is deliberately not updated to 1.0738, and it must
not track future calibrations. The rationale is that the synthetic rig **approximates** the real one
and never promised correspondence — it already departs via common averaged intrinsics, all cameras
at Z = 0, and all optical axes aligned to +Z where real ones deviate up to 5°. The interface height
is the least of those idealizations.

**Consequence for prose:** any manuscript claim that the synthetic rig *matches* the deployment
should read *representative of* it. If §3 or the supplement states the synthetic water depth as the
calibrated value, that sentence needs the same correction the source comments received.

---

## MF-05 — E7's shared-vs-per-camera claim IS supported, but only as a comparison

**Status:** open — needs a prose edit, **and a decision on D-36's criterion (see the box)**
**Found:** 2026-07-31, plan 19.2-24 + D-36 five-seed sweep (10/10 runs succeeded)
**Source of truth:** `Desktop/Aqua/AquaCal/seed_sweep_19_2/e7_interface_ablation/seed_{42..46}/`;
analysis in `.planning/phases/19.2-.../analyze_e7_spread.py`
**Where the prose is:** wherever the shared-vs-per-camera interface comparison is claimed

> **⚠ This entry rests on a criterion that differs from D-36 as written, and that difference
> changes the answer. It needs the author's decision before being relied on.**
>
> D-36 says: *"If the shared-vs-per-camera gap is smaller than the spread, E7 does not support a
> directional conclusion."* Applied literally — gap between the arms' means versus their marginal
> spreads — **both pairings fail**, and E7 would support nothing.
>
> That test is wrong for this design. **The seeds are paired**: one seed builds one scenario and
> both arms are evaluated on it, so the marginal spread contains scenario variation common to both
> arms that cancels in the comparison. Measured: the refined arms correlate at **r = +0.98** across
> seeds — a bad seed makes both arms bad together. The correct test is on the per-seed difference.

### Per-arm spread — what bounds any ABSOLUTE claim

mean `|camera_height_drift_mm|`, by seed:

| arm | 42 | 43 | 44 | 45 | 46 | mean | range |
|---|---|---|---|---|---|---|---|
| `shared_fixed` | 1.112 | 1.211 | 1.260 | 0.562 | 1.633 | 1.156 | **1.070** |
| `percamera_fixed` | 2.362 | 2.480 | 1.609 | 2.036 | 1.920 | 2.081 | 0.870 |
| `shared_refined` | 1.213 | 11.550 | 4.462 | 0.450 | 0.996 | 3.734 | **11.101** |
| `percamera_refined` | 2.194 | 12.437 | 4.637 | 3.082 | 2.330 | 4.936 | **10.243** |

### Paired difference — what supports the COMPARISON

`percamera − shared`, so positive means shared is better:

| pairing | 42 | 43 | 44 | 45 | 46 | shared better in | crosses zero | sign test |
|---|---|---|---|---|---|---|---|---|
| fixed | +1.251 | +1.269 | +0.349 | +1.474 | +0.287 | **5/5** | no | p = 0.031 |
| refined | +0.981 | +0.887 | +0.176 | +2.632 | +1.334 | **5/5** | no | p = 0.031 |

**The levels wander by 11 mm; the difference never changes sign.**

### What may and may not be claimed

**May:** the directional result. A shared interface produces less camera-height drift than
per-camera interfaces, consistently across five seeds, on both fixed and refined arms. Quote the
paired difference *with its range* — fixed +0.926 mm [+0.287, +1.474], refined +1.202 mm
[+0.176, +2.632].

**May not:** any absolute refined-arm number as a point estimate. `shared_refined` ranges
0.450–11.550 mm across seeds. D-36's underlying concern was entirely justified — it applies to
absolute values, not to the comparison.

**Caveats that belong in the prose:** n = 5, so p = 0.031 one-tailed is suggestive rather than
decisive; this is one metric; and it bounds scenario-generator seed variation only, not real-data
variation.

**This also retires the Phase 19.1 worry** that E7 once showed per-camera beating shared. Across
five seeds it does not, in either pairing.

---

## MF-06 — E1's movement under the PnP guard is not resolvable above seed noise

**Status:** open — needs no prose change, but the regenerated values should be adopted
**Found:** 2026-07-31, plan 19.2-24 five-seed sweep
**Source of truth:** `seed_sweep_19_2/e1_refractive_comparison/seed_{42..46}/exp1_parameter_errors.csv`
**Where the prose is:** §3's synthetic refractive-vs-non-refractive comparison

E1's committed CSVs predate `7e0cb90`. Regenerating at seed 42 on guarded code moves them, and the
recorded blast radius (159 / 44 / 48 cells across three CSVs) makes that expected. **D-19 requires a
headline divergence to halt**, so each headline delta was judged against E1's own five-seed range
rather than against an inherited three-seed band:

| model | metric | delta (s42) | 5-seed band | band ÷ delta |
|---|---|---|---|---|
| refractive | `focal_length_error_pct` | +0.014892 | 0.151117 | **10.1×** |
| refractive | `z_position_error_mm` | −0.001494 | 0.104601 | 70.0× |
| refractive | `xy_position_error_mm` | +0.014212 | 0.261548 | 18.4× |
| refractive | `reprojection_rms_px` | −0.000002 | 0.004145 | 2670× |
| non_refractive | (all four) | ≤0.0066 | 1.11–4.54 | 209–5611× |

**Every delta is smaller than E1's own seed range. No D-19 halt.**

**One number needs care in prose.** `refractive focal_length_error_pct` moved **+59% relative** —
0.0252 → 0.0401. That is a near-zero absolute (a delta of 0.015 *percentage points*) and must not be
reported as a large error. The same trap is recorded in `.continue-here.md`: *do not report the
eye-catching relative figures without checking the absolute column.*

**Suggested framing:** adopt the regenerated values and describe them as re-measured on corrected
code, not as a change in accuracy. The honest statement is the one Phase 19.2 reached for E1 before:
this removes the evidence that the fix is harmful; it does not prove the fix is exactly neutral.

---

<!-- Append new findings above this line as MF-07, MF-08, ...
     Candidate sources still to mine: E5 index sensitivity (19.2-13, run) and E6 generalization
     sweep (19.2-11, run) - both complete and committed, neither yet mined for prose conflicts.
     E4 grid was re-measured 2026-07-30 (`5b17cd4`); MF-02's E4 figures predate that and are
     superseded - see the staleness notice in that entry. Its 16x200 cell now peaks at 10.45 GiB,
     not the 3.31 GiB MF-02 quotes. -->
