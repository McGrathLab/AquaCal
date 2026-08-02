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

**Status:** RESOLVED (2026-08-01, phase 19.2 plan 19.2-25); **numbers regenerated 2026-08-02**
(phase 19.3 plan 10) on the corrected scenario geometry — the provenance caveat is closed; a prose
edit is still needed, and the required framing has changed (see below)
**Found:** 2026-07-29, phase 19.2 plan 19.2-05 (E3 tier 2, per D-20)
**Resolved by:** D-32 option (c) — instrumenting the production batch path directly, decided
2026-07-29 (`19.2-GAP-CONTEXT.md` § D-32), implemented in plan 19.2-20, regenerated with
provenance by plan 19.2-23
**Source of truth:** `experiments/results/newton_iterations.csv` — now carries a `loop` column
with two values, `scalar` and `batch`, for every camera and the pooled `ALL` row
**Where the prose is:** supplement, the refractive-projection convergence claim

> **RESOLUTION.** `newton_iterations.csv` now reports both shipped Newton loops. The `scalar`
> rows describe `_solve_newton_r_p` via `refractive_project_newton_diagnostic` — unchanged from
> the original measurement. The `batch` rows are new: they describe the loop production
> actually runs, `calibration/_optim_common.py:635` → `refractive_project_batch` →
> `_refractive_project_newton_batch`, instrumented through an opt-in `return_diagnostics` flag
> that is off by default and proven bit-identical to pre-D-32 production output when unset
> (`19.2-20-SUMMARY.md`).
>
> **Why option (c), and not (a) or (b) — both considered and rejected, recorded so they are not
> silently reopened** (`19.2-GAP-CONTEXT.md` § D-32):
> - **(a) Migrate the batch loop onto the shared `_solve_newton_r_p` helper.** Rejected: the
>   helper is scalar, so calling it per-point would destroy vectorization in the hottest loop of
>   every residual evaluation, and switching the batch to per-point termination stops iterating
>   earlier — shifting results at ~1e-16 and propagating through the bundle adjustment, which
>   risks moving a §3 number (a D-08 hard stop). Retained as a desirable code-quality follow-up,
>   explicitly out of scope here.
> - **(b) Correct the diagnostic's docstring and restate the CSV's scope as the scalar path.**
>   Rejected: zero risk and cheap, but it documents the mismatch rather than fixing it — the
>   published convergence number would still not describe what production runs.
> - **(c) Instrument the batch path itself (chosen).** Makes the published number actually
>   describe the loop production runs, touches production numerics not at all (the diagnostic
>   flag is off by default and proven inert), and yields the one quantity the batch previously
>   could not report — per-point convergence.

> **NUMBERS REGENERATED 2026-08-02 (phase 19.3 plan 10).** The table below was originally read
> out of a `newton_iterations.csv` produced on the pre-depth-fix scenario geometry, in which
> synthetic board corners protruded through the water surface. Phase 19.3 corrected that geometry
> and plan 09 regenerated the file, moving 134 cells (measured by plan 19.3-05). The pre-fix table
> is preserved verbatim below the current one, and the pre-fix CSV is archived at
> `experiments/archive/e3-2026-08-02-pre-depth-fix/newton_iterations.csv` — the two versions are
> traceable rather than one silently replacing the other. **The entry's conclusion is unchanged in
> kind and is restated, not softened, below.**

The supplement says the Newton solve for the refraction point converges in **"two to four
steps."** Measured over the real rig's full working volume (105,600 points, 12 cameras), both
loops, from `newton_iterations.csv`'s pooled `ALL` rows:

| quantity | scalar | batch |
|---|---|---|
| iterations, min | 2 | 2 |
| iterations, **median** | **4.0** (identical on every camera) | **4.0** (identical on every camera) |
| iterations, **max** | **6** (6 on every camera) | **6** (6 on every camera) |
| not converged | **0** | **0** |
| incidence angle range | 0.08 deg - 57.50 deg | 0.08 deg - 57.50 deg |
| max residual | ~1.0e-9 m (at tolerance) | ~1.0e-9 m (at tolerance) |

**Pre-fix values, for traceability** (104,052 points, superseded — do not quote):

| quantity | scalar | batch |
|---|---|---|
| iterations, median | 4.0 | 4.0 |
| iterations, max | 7 (6-7 per camera) | 7 (6-7 per camera) |
| incidence angle range | 0.13 deg - 62.92 deg | 0.13 deg - 62.92 deg |

**What moved, and why.** The corrected geometry re-centres board poses on the board centre and
enforces a depth-clearance floor, so the sampled rays are less oblique: peak incidence fell from
62.92 deg to 57.50 deg, and the iteration tail with it, from 7 to 6. The point count rose from
104,052 to **105,600** — which is exactly 12 cameras x 100 frames x 88 corners, i.e. **every
corner is now valid**. Pre-fix, 129 corners per camera were being dropped as unprojectable. That
increase is the depth-clearance fix showing up directly in this file.

The two loops' *per-point* convergence-iteration distributions are effectively identical (the
tiny residual differences, e.g. `9.989e-10` vs `9.999e-10`, are the two implementations' own
arithmetic, not a scope difference) — each point still takes the same number of Newton steps to
reach its own root regardless of which loop finds it.

**Does the "two to four steps" prose edit still need making? YES — unchanged in kind, slightly
smaller in magnitude.** The understatement is now 4 -> 6 rather than 4 -> 7:

| | pre-fix | post-fix |
|---|---|---|
| supplement's claim | "two to four steps" | "two to four steps" |
| measured range | 2 - 7 | **2 - 6** |
| under-provisioning factor vs median | 7/4 = 1.75x | **6/4 = 1.5x** |

The median is **still 4.0** and zero points still fail to converge, so the supplement's typical
case remains correct and the tail is still understated. A reader sizing a compute budget from
"typically four steps" would under-provision by 1.5x rather than 1.75x — smaller, but the same
error of kind, and still not a rounding detail. **The edit specified below is therefore still
required; only the number 7 becomes 6.** Note also that per-camera spread collapsed: pre-fix
`iter_max` varied 6-7 across cameras, post-fix it is 6 on every camera, so the tail is now
uniform rather than camera-dependent.

**The median/max framing must be restated against the batch loop's actual termination rule, and
this SHARPENS the entry's original conclusion rather than replacing it.** The per-point
iteration counts above describe *when each point's own delta would cross tolerance if it
terminated independently* — but the production batch loop does not terminate per point: it
runs `np.all(np.abs(delta) < tolerance)`, so **every point in a batch keeps iterating until the
slowest point in that batch converges.** A point whose own root would be found in 2 steps still
pays for however many steps the batch's hardest point needs, up to the measured max of 6. So the
production **per-point cost is the batch's max, not its median** — a reader sizing a compute
budget from "typically four steps" would under-provision by 1.5x (post-fix; 1.75x pre-fix), not
merely fail to see an occasional tail case. This is stronger than the original entry's "misses that the distribution
runs to 7" framing, and it rests on the batch measurement now committed rather than on the
scalar table alone.

Convergence itself is never in question in either loop: zero points failed to converge and every
residual sits at the solver tolerance in both `scalar` and `batch` rows. So this remains a prose
accuracy problem, not a correctness problem in the library — the computed refraction points are
not known to be wrong, and this finding does not weaken any accuracy claim. It is a provenance
correction, now completed, layered under a prose correction that still needs the author's edit.

**Suggested framing for the edit** (wording is the author's call, and has changed from the
original entry): do not lead with the median. State the effective per-point cost under
production's all-points termination — "every point costs up to the batch's slowest point, up to
6 steps over the calibrated volume (individual points would converge in as few as 2, median 4,
if evaluated independently)" — rather than "typically four steps." The batch's own median/max
are worth reporting as characterizing the *individual* root-find difficulty, but they no longer
describe the batch's *per-point wall-clock cost*, which the all-points termination rule
equalizes upward toward the tail.

**Do not** silently change the number to 6 as if it were now "the" iteration count. The
per-point root-find genuinely converges in a median of 4 steps; what changed is which quantity
that number describes. Quoting 6 without the batch-termination explanation above would overstate
typical *individual* root-find cost as badly as "two to four" understates *production's*
per-point cost — the fix is to report both quantities and say which is which, not to swap one
number for the other.

---

## MF-02 — E4's memory curve does not bound a real deployment of the same camera count

**Status:** RESOLVED (2026-08-01, phase 19.2 plan 19.2-25) — re-measured against the current
grid; still needs a prose edit, and the edit's direction has reversed from the original entry.
The original entry's numbers are **SUPERSEDED**, preserved below with a staleness notice rather
than overwritten (same discipline as `code_constants.csv` in plan 23). The mechanism the entry
identifies (peak memory tracks residual count, not camera count) still holds; its headline
comparison does not.
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
>
> **Resolution (2026-08-01, plan 19.2-25): the gap INVERTED, not narrowed or closed.** The
> original entry warned a reader would under-provision by ~3× if they sized a real deployment
> off the E4 grid. That warning **no longer applies in its original direction** — E4's 16×200
> cell (10.45 GiB overall peak) now exceeds E2's 13-camera real rig (9.78 GiB), so a reader
> using the grid as a sizing guide today would, if anything, slightly **over**-provision for a
> same-or-larger real deployment, not under-provision. The 16-vs-13-camera comparison is still
> not apples-to-apples (E4's cell has fewer cameras and more residuals, for the reasons given
> above), so neither figure should be read as a tight bound in either direction — but the
> specific, quantified 3× under-provisioning risk this entry existed to warn about is gone.
> **The suggested framing below (present the grid as a scaling curve in problem size, not a
> per-camera-count capacity table) is unaffected by the inversion and remains the recommended
> edit** — it was already about not treating camera count as the sizing variable, and the
> inversion is further evidence for that, not against it.

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

**Status:** open — needs a prose edit. **D-36's criterion is DECIDED; seeds 47–51 LANDED
2026-08-01 and CHANGED THE CONCLUSION from "always" to "usually" — see the paired-difference
section, which supersedes the five-seed claim.**
**Found:** 2026-07-31, plan 19.2-24 + D-36 five-seed sweep (10/10 runs succeeded)
**Source of truth:** `Desktop/Aqua/AquaCal/seed_sweep_19_2/e7_interface_ablation/seed_{42..46}/`;
analysis in `.planning/phases/19.2-.../analyze_e7_spread.py`
**Where the prose is:** wherever the shared-vs-per-camera interface comparison is claimed

> **D-36's criterion: AMENDED to the paired difference — user decision, 2026-07-31.**
>
> D-36 as written says: *"If the shared-vs-per-camera gap is smaller than the spread, E7 does not
> support a directional conclusion."* Applied literally — gap between the arms' means versus their
> **marginal** spreads — both pairings fail and E7 would support nothing.
>
> That reading misfires on this design. **The seeds are paired**: one seed builds one scenario and
> both arms are evaluated on it, so the marginal spread is mostly *scenario difficulty*, which is
> common to both arms and cancels in the comparison. Measured: the refined arms correlate at
> **r = +0.98** — seed 43 draws a hard scene and both arms land at 11.6/12.4 mm; seed 45 draws an
> easy one and both land at 0.45/3.08. Comparing a within-seed gap against a between-seed spread
> asks whether the effect is large relative to variation the design already controls for. The
> criterion is therefore the **per-seed difference**, not the marginal spread.
>
> **The cost of that amendment, recorded honestly.** At n = 5 the sign test's floor is
> 2⁻⁵ = 0.031, so 5/5 is the *only* outcome that could have cleared 0.05. The p-value says
> "unanimous", not "unanimous by a wide margin", and the design has no power to spare. The effect
> is also modest against the levels: ~1.2 mm on arms spanning 11 mm.
>
> **Seeds 47–51 ran 2026-08-01 and unanimity BROKE — 9/10, not 10/10.** This entry was rewritten
> accordingly. The extra seeds were commissioned as a real test rather than a confirmation
> exercise, and they earned that framing: at 5/5 the honest-looking conclusion was "shared is
> always better", which is false.
>
> **What survived and what did not.** The sign test *improved* (p 0.031 → 0.0107), so the
> tendency is better evidenced than before. But the common-mode justification for amending D-36
> holds only for the `refined` pairing (r = +0.961); at ten seeds the `fixed` arms are nearly
> uncorrelated (r = +0.199), so the five-seed correlation that motivated the amendment was itself
> a small-sample artifact there. The amendment remains the right criterion — a per-seed
> difference is still the correct question — but it is carried by the sign test, not by
> correlation, for `fixed`.

### Per-arm spread — what bounds any ABSOLUTE claim

mean `|camera_height_drift_mm|`, by seed:

| arm | 42 | 43 | 44 | 45 | 46 | mean | range |
|---|---|---|---|---|---|---|---|
| `shared_fixed` | 1.112 | 1.211 | 1.260 | 0.562 | 1.633 | 1.156 | **1.070** |
| `percamera_fixed` | 2.362 | 2.480 | 1.609 | 2.036 | 1.920 | 2.081 | 0.870 |
| `shared_refined` | 1.213 | 11.550 | 4.462 | 0.450 | 0.996 | 3.734 | **11.101** |
| `percamera_refined` | 2.194 | 12.437 | 4.637 | 3.082 | 2.330 | 4.936 | **10.243** |

**Extended to ten seeds (2026-08-01), seeds 47–51 added:**

| arm | min | max | **range** |
|---|---|---|---|
| `shared_fixed` | 0.149 | 1.633 | 1.484 |
| `percamera_fixed` | 1.207 | 2.480 | 1.273 |
| `shared_refined` | 0.450 | 11.550 | **11.101** |
| `percamera_refined` | 1.522 | 12.437 | **10.915** |

The refined arms' 11 mm swing is confirmed at ten seeds, not a five-seed artifact. Note
`shared_fixed` reaches as low as 0.149 mm and `percamera_fixed` never goes below 1.207 mm —
the fixed arms barely overlap, which is why the fixed pairing survives on the sign test despite
its near-zero between-arm correlation.

### Paired difference — UPDATED to ten seeds, 2026-08-01. **Unanimity BROKE.**

> **The five-seed version of this section claimed 5/5 with no sign change in either pairing, and
> concluded that this "retires the Phase 19.1 worry that E7 once showed per-camera beating
> shared." Seeds 47–51 falsified that.** Both statements are withdrawn. The extra seeds were
> commissioned as a genuine test of unanimity, and unanimity is what they broke.

`percamera − shared`, so positive means shared is better. Seeds 42–46 then 47–51:

| pairing | shared better in | paired diff mean | range | crosses zero | sign test | between-arm r |
|---|---|---|---|---|---|---|
| fixed | **9/10** | +1.001 | [−0.020, +1.777] | **yes** (seed 49) | p = 0.0107 | +0.199 |
| refined | **9/10** | +0.980 | [−1.000, +2.632] | **yes** (seed 48) | p = 0.0107 | +0.961 |

**The two exceptions are not equivalent.** `fixed`'s exception (seed 49, −0.020 mm) is a tie:
its magnitude is 1/50th of the mean effect and it is better read as "no difference on that
scenario" than as a reversal. `refined`'s exception (seed 48, **−1.000 mm**) is a *real*
reversal whose magnitude equals the mean effect itself (+0.980 mm) — on that scenario,
per-camera genuinely won by about as much as shared usually wins by.

**The evidence for the tendency got STRONGER even as unanimity broke.** 9/10 at n = 10 gives an
exact one-tailed sign test of p = 0.0107, against 5/5 at n = 5 giving p = 0.031. Five extra
seeds bought more power than the reversal cost.

**But the pairing justification now applies to only one arm.** The amendment to D-36 rested on
the arms being highly correlated so that marginal spread is common-mode. At ten seeds that holds
for `refined` (r = +0.961) and **fails for `fixed` (r = +0.199)** — the fixed arms are nearly
uncorrelated, so pairing buys little there, and the five-seed correlation that motivated the
amendment was itself a small-sample artifact for that pairing. The `fixed` result stands on the
sign test alone, not on common-mode cancellation.

### What may and may not be claimed

**May:** a *tendency*, quantified and qualified. A shared interface produces less camera-height
drift than per-camera interfaces on 9 of 10 scenarios, mean paired difference ~+1.0 mm
(p = 0.0107 one-tailed, both pairings). State the exception count and that one refined reversal
was of full effect size.

**May NOT:**
- **"Shared is better," unqualified.** It is better usually, not always, and the counterexample
  is not negligible.
- Any absolute refined-arm number as a point estimate — `shared_refined` still spans
  0.450–11.550 mm.
- That E7 no longer ever shows per-camera beating shared. **It does, at seed 48.** The Phase
  19.1 concern is live, not retired.

**Caveats that belong in the prose:** one metric; scenario-generator seed variation only, not
real-data variation; and the effect size (~1 mm) is comparable in magnitude to both the
counterexample and to run-to-run variation in the refined arms.

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

## MF-07 — Three E6 configurations did not converge, and were published as `status="ok"`

**Status:** RESOLVED BY MF-08 (2026-08-02, phase 19.3) — the diagnosed cause was corrected and all
six affected experiments re-measured. All fourteen E6 configurations now sit at or below 1e-02
first-order optimality with a zero degenerate-observation count. The author decision this entry
asked for is no longer needed: the affected rows were regenerated rather than adjudicated.
**This entry recorded the question; MF-08 answers it.**
**Found:** 2026-08-01, plan 19.2-28, on the first run of the optimality capture plan 19.2-27 added
**Source of truth:** `experiments/results/generalization_sweep.csv`,
`experiments/results/e6_configs/*.json`; full analysis in `19.2-28-SUMMARY.md`
**Where the prose is:** wherever E6's index / layout / scale comparisons are claimed

WR-02 was recorded as a blind spot: E6 captured no solver diagnostics, so nothing in any committed
record distinguished a diverged solve from a converged one. Plan 27 closed it. On the very first run
it exposed this:

| axis | axis_value | RMS px | optimality (interface) | optimality (intrinsic) |
|---|---|---|---|---|
| index | **1.42** | 0.789 | **51.92** | 0.054 |
| scale | **half_scale** | 1.007 | **27.32** | **140.31** |
| layout | **ring** | 0.705 | 0.0016 | **4.20** |
| the other eleven | | 0.70–0.78 | 0.0016–0.035 | 0.002–0.117 |

**Three of fourteen sit 3–4 orders of magnitude above the rest, and every one was published under
`status="ok"` behind an entirely plausible reprojection RMS.** This is the third instance of that
failure in this milestone, after E4's 12×100 cell (0.79 px RMS on optimality 6.4e9) and MF-04's §3
record.

### The accuracy evidence says the answers are fine

| group | n | reconstruction RMSE mean | max |
|---|---|---|---|
| high-optimality | 3 | 0.5938 mm | 0.7174 |
| healthy | 11 | 0.5622 mm | 0.7516 |

Indistinguishable — and `half_scale`, the worst-converged row, has the **best** reconstruction
accuracy in the table (0.4935 mm), while the **worst** reconstruction belongs to `double_scale`,
which is healthy on optimality. These are synthetic scenarios scored against ground truth, so
reconstruction error is the direct measure of correctness.

### Diagnosed cause: board corners protrude through the water surface

Measured on the baseline scenario: **61 of 8800 corners (0.69%)** sit at or above the interface,
worst protrusion **66 mm**, because `GRID_DEPTH_RANGE` starts at 1.100 m while the board needs
~1.18 m of depth to stay submerged at the default 15° tilt. Those observations fall outside the
refractive model's domain and are continued with a pinhole extension, which is C0-but-not-C1 — and
optimality is a max-norm, so a handful of kinks dominates it.
`corr(degenerate count, optimality) = 0.646`.

**The kink is real physics, not a modelling artifact** — above the surface there is no water, so the
straight line IS the correct projection, and a flat interface genuinely gives a derivative
discontinuity. The fix is to stop putting corners on the interface (a real calibration keeps the
board underwater), NOT to blend the two models with an arbitrary width.

### What may and may not be said

**May:** that E6's sweep now records the convergence evidence for every configuration, and that
eleven of fourteen converge cleanly.

**May NOT, pending the decision:** quote the `index=1.42`, `scale=half_scale`, or `layout=ring` rows
as converged results without stating their optimality. Note these are load-bearing — one of three
scale rows, one of eight index rows, and one of three layout rows, the layout axis being the one
plan 19.2-22 reported as unconfounded for the first time.

**Never:** quote optimality to more than one significant figure. It varies ~2× between runs of
identical code (measured, `19.2-28-SUMMARY.md`); it supports an order-of-magnitude reading
(1e-3 healthy vs 1e1–1e9 broken) and nothing finer.

**Fix owner:** phase 19.3 (`.planning/phases/19.3-scenario-geometry-and-convergence/19.3-SEED.md`),
which will re-run E1/E4/E5/E6/E7 on corrected geometry. E2 is real data and unaffected.

---

## MF-08 — A benchmark-construction flaw moved six experiments; convergence is now readable

**Status:** OPEN — needs the author's edit to §3's synthetic numbers before resubmission
**Found:** 2026-08-01 (phase 19.2 plan 28, via the optimality capture plan 27 added); corrected and
re-measured 2026-08-02, phase 19.3
**Source of truth:** `experiments/results/` and `experiments/results_e6_repeat2/` at commit
`22e75ef`, against `experiments/archive/e{1,3,4,5,6,7}-2026-08-02-pre-depth-fix/`
**Where the prose is:** §3 Synthetic validation, the abstract's improvement ratio, and the
supplement's convergence claim (via MF-01)
**Answers:** MF-07 (E6 non-convergence). **Moves the numbers in:** MF-01.

### The defect, stated precisely

Every synthetic scenario generated by `generate_board_trajectory` / `generate_real_rig_trajectory`
allowed calibration-board corners to protrude through the water surface. On the baseline scenario
**61 of 8,800 corners (0.69%)** sat at or above the interface, worst protrusion **66 mm**. Those
observations fall outside the refractive model's domain and are continued with a pinhole extension,
which is C0-but-not-C1 at the boundary. First-order optimality is a max-norm, so a handful of kinks
dominates it — **the convergence diagnostic became unreadable**.

**What the defect did NOT do: it did not affect accuracy.** Measured before the fix, the
high-optimality group's reconstruction RMSE (0.5938 mm mean, n=3) is indistinguishable from the
healthy group's (0.5622 mm, n=11), and `half_scale` — the worst-converged configuration in the
table at optimality 27-140 — had the **best** reconstruction accuracy of all fourteen at 0.4935 mm.
This was a defect in how the benchmark was *constructed* and *diagnosed*, not in what the library
computes.

The fix derives a depth-clearance floor and re-centres board poses on the board centre rather than
a corner. Post-fix, **zero corners sit at or above the interface in any scenario**, measured
directly against each scenario's own corner cloud.

### What moved, per experiment

Optimality is quoted to ONE significant figure throughout; it varies ~2x run to run and no finer
comparison is supportable.

| exp | headline movement | optimality (1 s.f.) | degenerate count | accuracy claim |
|---|---|---|---|---|
| **E1** | deepest-point Z-RMSE 257 -> 248 mm; ratio ~135x -> **~128x** | refr 2e-3; non-refr 9e+2 | refr 0; non-refr 0 -> 14,949 (bookkeeping, see below) | **partial only** — see below |
| **E3** | tier 2 moved 134 cells; iter_max 7 -> 6; incidence 62.92 -> 57.50 deg; points 104,052 -> **105,600** | n/a (no calibration) | n/a | **NONE** — no seed band |
| **E4** | worst-cell RMS 0.92 -> 0.71 px (16x50), 0.85 -> 0.71 (12x50); 3D error ~3.5e-5 -> ~2.9e-5 m | 3e-2 -> 4e-3 (12x100) | un-instrumented -> **0** on all 9 cells | **NONE** — no seed band |
| **E5** | reconstruction RMSE +0.009 mm across the band; the 1.341 outlier (0.80 px) resolved to 0.71 | n/a (not recorded) | **0** | **NONE** — single seed, see below |
| **E6** | index/1.42 **5e+01 -> 1e-02**; scale/half_scale **3e+01 -> 8e-03**; all 14 now <= 1e-02 | see left | per-config 3-38 -> **0** | **NONE** — no seed band |
| **E7** | percamera_fixed control RMS 0.98 -> 0.50 px; shared_fixed water_z err 0.92 -> 0.63 mm | — | **0** on all four arms | **supported** — see below |

### Accuracy claims: what is and is not supportable

D-19.3-17 permits "accuracy unaffected" only where a measured seed band licenses it. Applying that
rule strictly gives a **more restrictive** answer than this phase's planning assumed:

- **E7 — supported.** 10-seed band (D-36). Every arm's movement is inside E7's own known seed
  instability: the refined arms are documented as varying by >10 mm run to run, and the largest
  movement here is +4.1 mm (percamera_refined water_z error, 3.4 -> 7.5 mm). No directional
  conclusion is drawn from the refined arms, consistent with that instability.
- **E1 — PARTIAL, not blanket.** 5-seed band (19.2 plan 24). `xy_position_error_mm` moved
  -0.117 mm against a band of 0.262 mm (**0.45x band — within noise**). But
  `z_position_error_mm` moved **+0.252 mm against a band of 0.105 mm — 2.41x the band, i.e.
  outside seed noise.** E1 therefore may NOT carry a blanket "accuracy unaffected" statement.
  The movement is attributable to the scenario itself having changed (deeper, re-centred working
  volume), not to a library defect — but it is a real change in the measured depth-axis accuracy
  and must be reported as such, not absorbed.
- **E5 — NONE. This corrects an inherited assumption.** RESEARCH flagged E5's band as
  inherited-not-verified. `e5_provenance.json` settles it: `"seed": 42` (single) with an
  11-point `n_assumed_band`. **E5's band varies the assumed refractive index, not the seed**, so it
  cannot bound seed noise and licenses no accuracy claim. E5 moves into the no-claim group.
- **E3, E4, E6 — NONE.** No seed sweep has ever been run for any of them. A single-seed
  before/after cannot support an accuracy claim however plausible the delta and its mechanism look:
  19.2's "fixed code is worse on 5 of 6 metrics" table was overturned by measuring the noise floor,
  and phase 19.1 recorded the same lesson independently.

### E1's 14,949 degenerate observations are bookkeeping, not contamination

E1's non-refractive arm is the paper's pinhole baseline (`n_water = 1.0`). It reports 14,949
degenerate observations, which looks alarming next to a headline of "zero everywhere". It is not a
contamination of the comparison, and this was established rather than assumed:

- At `n_water = 1.0` the refractive model reduces to pinhole (the paper states this itself), so
  `water_z` cannot affect any projection — but it still gates the domain test. It is an **exact
  null direction**: holding all other parameters fixed and sweeping `water_z` over 1.5 m leaves the
  cost constant to 13 significant figures (relative variation 2.6e-15) while the guard count climbs
  0 -> 374 -> 5,572 -> 14,949. The n=1.333 control over the same sweep moves the cost by five
  orders of magnitude, so the probe is not blind.
- Re-running both arms with `water_z` pinned at ground truth reproduces every non-refractive
  reconstruction number to ~4 significant figures (2.5 m Z-RMSE 248.267 -> 248.221 mm) while
  driving the guard count to **0** and optimality from 874 to 0.525.

**Consequence: the refractive-vs-non-refractive comparison is unaffected by the projection guard.**
The ~135x -> ~128x change comes from the corrected scenario geometry and other v1.6.0 -> v1.8.0
changes, not from a compromised baseline. That decomposition is not attempted here — the re-run
carries all causes at once, and separating them would need a factorial old-geometry/new-code run.

**Do not pin `water_z` in the refractive arm.** There it is genuinely observable and estimating it
is the method's contribution; pinning it inflates the ratio to a flattering 168x and breaks §3's
stable-anisotropy claim (free: 1.95-2.19, matching the published ~2.3; pinned: drifts 2.21 -> 1.46).

### Determinism

**8 of 308 cells moved between repeats, before 63 of 308.** Thirteen of fourteen configurations
reproduced exactly; all movement is in `index/1.48`. Computed by the same code path that produced
the pre-fix figure, pinned by a self-test that re-derives 63/308 before reporting anything
(`determinism_probe.py --report`). The two E6 repeats used structurally isolated output
directories, and repeat 2 provably re-solved (zero resume-skip lines).

This is a **reported statistic, not a gate**. There is no tolerance in it and nothing to loosen.
The pre-fix cross-tabulation of movement against per-configuration degenerate count (correlation
0.19, no threshold rule) **has no post-fix counterpart**: the guard count is now zero for all
fourteen configurations, so the predictor has no variance and the correlation is undefined. That is
reported as undefined rather than as an improvement.

### §3 numbers requiring the author's edit

| quantity | submitted (v1.6.0) | corrected |
|---|---|---|
| deepest-point non-refractive Z-RMSE | 257 mm | **248 mm** |
| deepest-point refractive Z-RMSE | 1.9 mm | 1.94 mm |
| **abstract's improvement ratio** | **~135x** | **~128x** |
| refractive Z/XY anisotropy | ~2.3 | **~2.1** |
| non-refractive Z/XY range | 0.4 - 5.8 | **0.9 - 12.6** |
| non-refractive focal drift | 5.7% | 5.3 - 7.0% |

Every qualitative claim in §3 survives: the refractive model holds sub-2 mm Z-RMSE at every depth,
maintains a stable anisotropy ratio, and the non-refractive baseline's depth error still climbs
steeply with range while its lateral error grows far more slowly.

### A known reporting caveat in `benchmark_grid.csv`

The table's tenth row, `real_rig_13cam_200fr`, is **not** computed by E4 — it is copied from E2's
benchmark record, which is dated 2026-07-31 at commit `6c7f930b` and carries no degenerate-count
field. E2 is deliberately out of scope for this phase. Eleven of that row's fields moved relative
to the archived copy; **that movement is an E2-record refresh, not a geometry effect**, and must not
be read as one. The gate's cross-artifact `git_sha` consistency check does not enumerate that
record, so its PASS covers the other nine rows. Recommended follow-up: widen the check to include
the E2 record it feeds from.

### What may and may not be said

**May be said.** A benchmark-construction flaw was found by the convergence instrumentation the
reviewers' own questions prompted, corrected at the source, and all six affected experiments
re-measured in a single frozen run. Convergence is now readable across the suite: every calibration
experiment reports a zero degenerate-observation count, E6's three non-converged configurations are
gone, and run-to-run reproduction improved from 63 to 8 cells of 308. E7's accuracy is unchanged
within its 10-seed band.

**May not be said.** That accuracy is unaffected for E3, E4, E5 or E6 — none has a seed band. That
E1's accuracy is unaffected without qualification — its depth-axis error moved 2.4x its own seed
band. That the fix *improved* accuracy anywhere; nothing here measures that. That optimality
improved by any specific factor beyond one significant figure. That the determinism statistic is a
pass.

---

## Reviewer-response prose (draft — for the author to place; the manuscript tree is read-only here)

> **On the convergence diagnostics added in response to the reviewers' questions.**
>
> Instrumenting first-order optimality across the synthetic suite, as the reviewers' questions
> prompted, surfaced a flaw in how our synthetic benchmarks were constructed rather than in the
> calibration itself. Board poses were sampled such that a small fraction of target corners
> (0.69% at the baseline configuration, worst case 66 mm) protruded through the modelled water
> surface. Such observations lie outside the refractive projection's domain and are continued with
> a pinhole extension that is continuous but not continuously differentiable at the boundary.
> Because first-order optimality is a max-norm, a handful of these points dominated it, and the
> diagnostic could not distinguish a converged solve from an unconverged one. Three of fourteen
> configurations in the generalization sweep were affected.
>
> We corrected the scenario construction — deriving an explicit depth-clearance floor and
> re-centring board poses on the board centre — and re-measured all six affected experiments in a
> single run at one commit. No board corner now reaches the interface in any scenario. All
> fourteen generalization configurations converge to first-order optimality at or below 1e-2, every
> calibration experiment reports a zero out-of-domain observation count, and run-to-run
> reproducibility improved from 63 to 8 of 308 compared cells.
>
> We note explicitly that this was a defect in benchmark construction and convergence *diagnosis*,
> not in the calibration result. Before the correction, reconstruction accuracy was statistically
> indistinguishable between the affected and unaffected configurations (0.594 mm versus 0.562 mm
> mean RMSE), and the single worst-converged configuration had the best reconstruction accuracy in
> the table. The corrected synthetic numbers are accordingly close to those originally reported:
> the depth-axis improvement over non-refractive calibration at the most extrapolated test depth is
> 128x, against the 135x previously stated.

---
