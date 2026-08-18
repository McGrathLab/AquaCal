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
**Source of truth (COMMITTED as of 2026-08-05, phase 19.4):**
**`experiments/results/interface_ablation_band.csv`** — every banded number in this entry
regenerates from that file. It supersedes the gitignored working copies this entry originally
cited (`Desktop/Aqua/AquaCal/seed_sweep_19_2/e7_interface_ablation/seed_{42..46}/` and
`seed_sweep_19_3/`), which are retained only as historical provenance; analysis in
`.planning/phases/19.2-.../analyze_e7_spread.py`
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

> **RE-MEASURED ON THE CORRECTED GEOMETRY, 2026-08-03 (phase 19.3).** Everything below was
> measured on the PRE-depth-fix geometry. Phase 19.3 corrected the scenario construction and
> re-ran E7 at ten seeds. **The `fixed` pairing STRENGTHENED to unanimity; the `refined` pairing
> WEAKENED below conventional significance.** Both are reported; neither is adjusted to fit.
>
> | pairing | pre-fix | corrected geometry |
> |---|---|---|
> | `fixed` | 9/10, crosses zero (seed 49, -0.020 tie), sign test p = 0.0107 | **10/10, does NOT cross zero**, range [+0.919, +1.879], **p = 0.00098** |
> | `refined` | 9/10, crosses zero (seed 48, -1.000 real reversal), p = 0.0107 | **8/10**, crosses zero, range [-0.471, +2.524], **p = 0.055** |
>
> **What this changes.** The primary result — the fixed-intrinsics pairing, which this entry
> already identifies as "the primary result" — is now unanimous at ten seeds with no zero
> crossing, which is stronger evidence than the pre-fix record. The `refined` pairing, always the
> weaker of the two, fell to 8/10 and its sign test (p = 0.055) no longer clears a conventional
> 0.05 threshold. **"A tendency, not a rule" remains the correct characterisation for `refined`;
> for `fixed` on corrected geometry it is now unanimous.**
>
> The refined arms' seed instability also roughly halved (11.101 -> 6.558 mm shared,
> 10.915 -> 5.182 mm per-camera), so the corrected geometry improved conditioning as well.
>
> Per-arm corrected-geometry spread, mean `|camera_height_drift_mm|`:
>
> | arm | min | max | range | mean |
> |---|---|---|---|---|
> | `shared_fixed` | 0.039 | 1.092 | **1.053** | 0.579 |
> | `percamera_fixed` | 1.419 | 2.254 | 0.835 | 1.787 |
> | `shared_refined` | 0.491 | 7.050 | 6.558 | 2.950 |
> | `percamera_refined` | 2.059 | 7.240 | 5.182 | 3.794 |

> **REPRODUCED, NOT REPLACED — phase 19.4, 2026-08-05.** E7 is INERT under 19.4's
> single-flat-interface fix: its production `"realistic"` scenario resolves to
> `generate_real_rig_array()`'s frozen shared `WATER_Z` and never reaches
> `generate_camera_array`. The re-run recomputed this entry's statistics from the newly
> committed **`experiments/results/interface_ablation_band.csv`** and they match exactly —
> `fixed` 10/10 shared-better, range [+0.919, +1.879], no zero crossing; `refined` 8/10,
> crosses zero, range [-0.471, +2.524]; and all sixteen cells of the per-arm table above.
> **What changed is not the numbers but their standing:** they now have a committed,
> regenerable artifact behind them instead of gitignored scratch output.
>
> **One nuance a reviewer may raise.** This entry's p-values are ONE-SIDED sign tests
> (0.00098 = 2⁻¹⁰; 0.055 = 56/1024). Two-sided they are **0.00195** and **0.109**. The
> `fixed` pairing clears 0.05 either way; `refined` does not clear it under either
> convention, which reinforces — rather than changes — this entry's existing
> "a tendency, not a rule" framing for `refined`. The one-sided choice is not corrected
> here because it is the published framing; it is recorded so the decision is visible.

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

**Both optimality columns were checked, not just the interface pass.** MF-07 flagged three E6
configurations, and one of them — `layout/ring` — was flagged on the *intrinsic* pass (4.20) while
its interface pass was healthy (0.0016). Checking only the interface column would have missed it.
Post-fix, the worst value across `optimality_stage3_interface_optimization` AND
`optimality_stage3_intrinsic_pass`, over all fourteen configurations, is **1e-02** (one significant
figure — the measure varies ~2x run to run and no finer statement is supportable). All three of
MF-07's flagged configurations are clean on both passes.

### What moved, per experiment

Optimality is quoted to ONE significant figure throughout; it varies ~2x run to run and no finer
comparison is supportable.

| exp | headline movement | optimality (1 s.f.) | degenerate count | accuracy claim |
|---|---|---|---|---|
| **E1** | deepest-point ratio 134.3x -> 128.1x, **NOT resolvable** (seed band 97-178x) | refr 2e-3; non-refr 9e+2 | refr 0; non-refr 0 -> 14,949 (bookkeeping, see below) | **NONE** — see below |
| **E3** | tier 2 moved 134 cells; iter_max 7 -> 6; incidence 62.92 -> 57.50 deg; points 104,052 -> **105,600** | n/a (no calibration) | n/a | **NONE** — no seed band |
| **E4** | worst-cell RMS 0.92 -> 0.71 px (16x50), 0.85 -> 0.71 (12x50); 3D error ~3.5e-5 -> ~2.9e-5 m | 3e-2 -> 4e-3 (12x100) | un-instrumented -> **0** on all 9 cells | **NONE** — no seed band |
| **E5** | reconstruction RMSE +0.009 mm across the band; the 1.341 outlier (0.80 px) resolved to 0.71 | n/a (not recorded) | **0** | **NONE** — single seed, see below |
| **E6** | index/1.42 **5e+01 -> 1e-02**; scale/half_scale **3e+01 -> 8e-03**; layout/ring intrinsic **4e+00 -> 2e-03**; all 14 <= 1e-02 on BOTH passes | see left | per-config 3-38 -> **0** | **NONE** — no seed band |

> ### RE-MEASURED AGAIN under phase 19.4's single-flat-interface fix (2026-08-05)
>
> The table above records movement under phase 19.3's **depth** fix and is retained unchanged as
> the historical record. Phase 19.4 corrected a *different* upstream defect — the ground truth gave
> each camera its own water surface (see MF-10) — and re-ran the suite once under a single git sha,
> `2a623f9`. **Only E4 and E6 moved. E1, E3, E5 and E7 are inert and were confirmed unchanged by
> byte-comparison**, which corrects this entry's earlier implication that E7's numbers move: they
> do not.
>
> **Source of truth:** `experiments/results/` at `0ffbe15`, against
> `experiments/archive/e{4,6}-2026-08-04-pre-interface-fix/` (verified content-identical to the
> pre-run committed baseline at `2a623f9`).
>
> | exp | movement under the interface fix | status / guard | accuracy claim |
> |---|---|---|---|
> | **E4** | `n_observations` -0.15% to -0.40% (9 cells); `validation_3d_error_mean` 0.0350 -> 0.0335 mm on average but moves BOTH directions per cell (-17% to +9%); `reprojection_rms` unchanged within ±0.06%; optimality stays <= 2e-02 throughout | all 9 cells `ok` before and after; guard count **0** before and after | **NONE — reports movement, no accuracy claim** (D-19.3-17: E4 has no seed band) |
> | **E6** | `water_z_error_mm_mean` is the whole story: **~3.41 mm in every configuration before, 0.027-2.518 mm (mean 0.67) after**. Pre-fix it was near-CONSTANT — exactly 3.4057 in 10 of 14 rows, unresponsive to index, layout or scale. `depth_range_min` moved on the 2 scale configs only (1.181852 -> 1.176216, the re-derived clearance floor) | all 14 configs `ok` before and after — legal-configuration count **14 -> 14**; guard count **0** before and after | **NONE — reports movement, no accuracy claim** (D-19.3-17: E6 has no seed band) |
>
> **Why the E6 number is the phase's clearest evidence.** A water-surface error that sits at
> 3.4057 mm regardless of refractive index, rig layout, or scene scale is not responding to the
> experiment's variable — it is the ground-truth defect showing through. After the fix the same
> column varies with configuration, as an estimate should. This is a MECHANISM statement, not an
> effect size: one seed, one trajectory.
>
> **E4's accuracy column moves in both directions** and its mean shift (0.0350 -> 0.0335 mm) is far
> inside the seed-to-seed variation this design cannot measure. Do not read it as an improvement.
>
> **Banded numbers in this entry now name their artifacts.** The E1 deepest-point ratio spread
> (97-178x) and the "2 of 10 seeds exceed 2 mm" finding both regenerate from the newly committed
> **`experiments/results/exp1_band.csv`**; E7's band regenerates from
> **`experiments/results/interface_ablation_band.csv`**. Neither previously existed outside
> gitignored `seed_sweep_19_3/` output.
>
> **Unchanged by 19.4:** E1's `14,949` guard count reproduces exactly, so the bookkeeping finding
> below stands as written.
| **E7** | shared_fixed water_z err 0.92 -> **0.63 mm**; percamera_fixed 3.18 -> **2.24 mm**; `fixed` pairing now **10/10** shared-better, no zero crossing | — | **0** on all four arms | **supported** — corrected-geometry band |

### Accuracy claims: what is and is not supportable

D-19.3-17 permits "accuracy unaffected" only where a measured seed band licenses it. Applying that
rule strictly gives a **more restrictive** answer than this phase's planning assumed:

- **E7 — supported, and now on a CORRECTED-GEOMETRY band (re-measured 2026-08-03).** An earlier
  version of this entry justified the claim against MF-05's *pre-fix* 10-seed band, which is the
  same cross-geometry weakness that invalidated E1's. E7 was therefore re-run at ten seeds on the
  corrected geometry. Per-arm mean `|camera_height_drift_mm|`:

  | arm | corrected band | mean | pre-fix range |
  |---|---|---|---|
  | `shared_fixed` | 0.039 - 1.092 | 0.579 | 1.484 |
  | `percamera_fixed` | 1.419 - 2.254 | 1.787 | 1.273 |
  | `shared_refined` | 0.491 - 7.050 | 2.950 | **11.101** |
  | `percamera_refined` | 2.059 - 7.240 | 3.794 | **10.915** |

  Every production (seed-42) value falls inside its corrected band, so the claim holds on
  like-for-like evidence. **The corrected geometry roughly halved the refined arms' seed
  instability** (11.1 -> 6.6 mm and 10.9 -> 5.2 mm) — a real conditioning improvement.

  **Correction to an earlier reading.** A session note argued that both refined arms moving ~+6 mm
  in the same direction "is not the signature of seed noise". That was wrong: MF-05 records the
  refined arms' between-arm correlation as **r = +0.961**, so common-mode movement is precisely
  what seed noise looks like there. Seed 42 drew near the top of both bands (7.42 and 7.48 against
  band maxima of 7.417 and 7.479). No systematic effect is required or evidenced.
- **E1 — NONE, revised 2026-08-03.** An earlier version of this entry gave E1 a PARTIAL claim,
  on the grounds that `xy_position_error_mm` moved only 0.45x its seed band. That band was
  measured on the **pre-fix** geometry (19.2 plan 24) — the same cross-geometry comparison this
  phase re-ran E1 to eliminate. Re-measured on the corrected geometry, the bands are different
  and **both** metrics fall outside:

  | refractive metric | pre-fix band | corrected band | delta | verdict |
  |---|---|---|---|---|
  | `z_position_error_mm` | 0.105 | 0.157 | +0.252 | **1.60x — outside** |
  | `xy_position_error_mm` | 0.262 | **0.058** | -0.117 | **2.01x — outside** |

  The corrected-geometry `xy` band is 4.5x narrower than the pre-fix one, which is why the old
  comparison read as "within noise" and the new one does not. E1 therefore carries **no**
  accuracy claim. Note this is a statement about the calibrated *volume having changed*, not
  about a library defect — but it cannot be phrased as "accuracy unaffected".
- **E5 — NONE. This corrects an inherited assumption.** RESEARCH flagged E5's band as
  inherited-not-verified. `e5_provenance.json` settles it: `"seed": 42` (single) with an
  11-point `n_assumed_band`. **E5's band varies the assumed refractive index, not the seed**, so it
  cannot bound seed noise and licenses no accuracy claim. E5 moves into the no-claim group.
- **E3, E4, E6 — NONE.** A single-seed before/after cannot support an accuracy claim however
  plausible the delta and its mechanism look: 19.2's "fixed code is worse on 5 of 6 metrics" table
  was overturned by measuring the noise floor, and phase 19.1 recorded the same lesson
  independently.

  > **REVISED 2026-08-03.** An earlier version of this subsection said E4 and E6 *cannot* be
  > seed-swept as shipped, that only seed 42 yields a complete E6 sweep, that each configuration
  > builds its own floor, and that the `depth_range=None` fix is inert at seed 42. **All four
  > statements are wrong** and are corrected below. They were written from a partial model of the
  > failure; the full diagnosis is `.planning/debug/e6-seed-locked-clearance-floor.md` (status
  > `diagnosed`), which supersedes F12 in `19.3-CODE-TRACE-FINDINGS.md`. E6's verdict is
  > **unchanged** — it still carries no accuracy claim — but the *reason* is that no band has been
  > measured, **not** that none can exist.

  **The mechanism, established rather than inferred.** `GRID_DEPTH_RANGE[0]`
  (`e4_benchmark_grid.py:258`) is evaluated once at import from a seed-42 camera array, while
  `generate_board_trajectory`'s guard re-derives the floor from each scenario's own `water_zs`.
  `max(water_zs)` is a pure function of `(seed, n_cameras)`: it is **invariant to layout and
  spacing** (verified over 180 arrays, 20 seeds x 3 layouts x 3 spacings — all 9 combinations give
  one floor per seed) and **does** vary with `n_cameras` (11 of 23 seeds differ across {8, 12, 16}).
  `run_configuration` builds **two** scenarios inside one `try` with a blanket `except` — the
  calibration scene at `seed` (`e6:759`) and the held-out scene at `seed + 1_000_000` (`e6:787`) —
  and **both** are checked against the same frozen constant. The printed floor identifies which
  site raised, matching at 4 dp for **72/72** seed x configuration failure records.

  That resolves the two failure modes:

  | seed | result | why |
  |---|---|---|
  | 42 | `{'ok': 14}` | calibration floor equals the constant *by construction* (zero margin); holdout clears by ~0.5 mm |
  | 43-46 | `{'failed': 14}` in ~1 s | **calibration** draw fails; raises before Stage 2 ever runs |
  | 47, 50 | `{'failed': 14}` after 74 / 84 min | calibration passes, Stage 2 + Stage 3 run **to convergence**, then the **holdout** draw fails and the finished solve is discarded |

  An earlier draft carried a per-seed slack table predicting 42/47/50 legal. Its method was right —
  a standalone `generate_camera_array` call *is* the call `build_grid_scenario` makes — but it was
  **incomplete**, modelling only the calibration array. Legality requires both draws to clear.

  **E6 is NOT seed-locked to 42, and it converges off 42.** Over seeds 0-499 at E6's
  `n_cameras=12`, the calibration array is legal in 114/500 (22.8%), the holdout array in 117/500
  (23.4%), and **both in 29/500 (5.8%)** — independently re-derived by the orchestrator, not taken
  from the session's return text. Legal seeds below 100: **28, 42, 52, 62, 72, 75, 94.** Two of
  them were run end-to-end with no source change:

  | seed | wall clock | result | guard count |
  |---|---|---|---|
  | 42 | 96.6 min | `{'ok': 14}` | 0 on all 14 |
  | 62 | 85 min | `{'ok': 14}` | 0 on all 14 |
  | 28 | 83 min | `{'ok': 14}` | 0 on all 14 |

  Accuracy is highly reproducible across the three: `reconstruction_rmse_mm` agrees within ~5% on
  every configuration (baseline 0.4869 / 0.4689 / 0.4762; half_scale 0.3596 / 0.3380 / 0.3435) and
  `reprojection_rms_px` to three decimals. **n = 3 is not a band and no band may be quoted from it**
  — which is why E6's accuracy verdict stays NONE. Durable record:
  `evidence/e6_seed_band_42_62_28.md` and the `.csv` beside it; the raw output under
  `seed_sweep_19_3/e6/seed_{62,28}/` is gitignored and costs ~85 min/seed to regenerate.

  **Two seed-fragile spots surfaced, both invisible while E6 was single-seed.**
  (a) `scale/double_scale` optimality: `optimality_stage3_intrinsic_pass` is 0.00166 at seed 42 but
  elevated on **both** non-42 seeds (1.139 and 0.2241), while that row's `reconstruction_rmse_mm`
  is if anything slightly better off 42 (0.6619 vs 0.7244). **The optimality collapse this entry
  credits to the geometry fix is therefore seed-fragile as a convergence-diagnostic statement** —
  it is not an accuracy statement and was never claimed as one.
  (b) `layout/line` parameter recovery: `xy_position_error_mm_mean` 2.231 / 1.565 / 6.152 and
  `water_z_error_mm_mean` 3.452 / 8.251 / 11.76 (~4x spread, far above every other configuration)
  while reconstruction and reprojection stay clean — this project's documented weak-observability
  signature.

  **E4 remains unbanded, and for a stronger reason than E6.** It sweeps `n_cameras` ∈ {8, 12, 16},
  which *does* move the floor, giving up to **six** independent legality draws per seed against one
  frozen constant. Its published nine-cell grid is safe at seed 42 (all six draws clear) but must
  not be assumed safe at any other seed.

  **The fix is specified but deliberately not applied here** — it lands in a phase created after
  19.3 closes. Note for that phase: the guard's own suggested remedy, `depth_range=None`, is
  **NOT inert**. It is bit-identical for the calibration scene but shifts the **holdout** scene's
  board depths by up to **0.469 mm**, silently moving every published E4 and E6 held-out accuracy
  number. *An earlier version of this subsection asserted the opposite; that assertion covered only
  the calibration scenario and is retracted.* The form that is bit-inert for both is
  `max(GRID_DEPTH_RANGE[0], board_clearance_floor(GRID_BOARD_CONFIG, water_zs, 15.0))`, verified on
  all 100 poses' `rvec` and `tvec`.

  **Independent of all the above and still true:** E6 records a per-configuration failure as a
  `status="failed"` row rather than raising, so a run in which all 14 configurations died still
  **exits 0**. Check `status` counts, never the exit code.

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
  driving the guard count to **0** and optimality from 9e+02 to 5e-01 (one significant figure).

**Consequence: the refractive-vs-non-refractive comparison is unaffected by the projection guard.**

> **RETRACTED 2026-08-03.** An earlier version of this section decomposed the
> `~135x -> ~128x` change and attributed it to the scenario geometry correction,
> citing MF-06's measurement of the projection guard at -0.0015 mm. **That
> decomposition was measuring noise and assigning it a cause.** A five-seed sweep
> on the corrected geometry shows the deepest-point ratio is not a stable
> quantity. The text below replaces it.

**The `~135x -> ~128x` change is NOT resolvable above seed noise.** Measured across
seeds on the corrected geometry:

Ten seeds (42-51) on the corrected geometry:

| seed | non-refr Z-RMSE | refr Z-RMSE | ratio | | seed | non-refr | refr | ratio |
|---|---|---|---|---|---|---|---|---|
| 42 | 248.3 | 1.938 | 128.1x | | 47 | 199.3 | 1.516 | 131.4x |
| 43 | 252.1 | 1.416 | **178.0x** | | 48 | 238.4 | 1.779 | 134.0x |
| 44 | 205.5 | 2.111 | **97.3x** | | 49 | 237.2 | 1.493 | 158.9x |
| 45 | 231.0 | 1.505 | 153.4x | | 50 | 223.4 | 2.254 | 99.1x |
| 46 | 229.8 | 1.457 | 157.8x | | 51 | 223.5 | 1.428 | 156.5x |

**Band: 97.3x - 178.0x, mean 139.5, sd 25.1** (n = 10).

**What this band covers, precisely.** E1's evaluation test set is NOT reseeded:
`_build_dataframes` accepts a `seed` argument and never uses it, deriving test poses
and their detection noise from a hardcoded `depth_seed = 42 + int(depth * 100)`
(`e1_refractive_comparison.py:327`). Verified empirically -- `n_points` per depth is
byte-identical across all ten seeds. The band therefore measures **calibration-scenario
variance against a fixed test set**, which is exactly what a reader reproducing via
`--seed N` will observe, so it is the right number for reproducibility. It is a lower
bound on total variance if the evaluation set were also resampled. **If that dead
parameter is ever wired up, every band recorded here becomes incomparable and must be
re-measured.** The reported change is **7x**
-- about **0.09x of the band, or 0.28 sd**. Pre-fix and post-fix are statistically
indistinguishable.

**This is better news for the manuscript than it first appears.** The published
`~135x` sits **0.18 sd from the ten-seed mean** -- it is not a lucky draw but an
essentially representative value. The abstract's companion figure, 1.9 mm at 2.5 m,
is likewise conservative: the ten-seed mean of that quantity is 1.69 mm. The
published numbers are defensible; what is not defensible is treating a 7x
difference between two single-seed runs as a measured change.

**Consequences, stated plainly:**

1. **`~135x -> ~128x` must NOT be presented as a corrected number requiring a §3
   edit.** Nothing measurable moved. Reporting a 7x shift against an 81x noise floor
   is exactly the error this milestone has already made twice -- 19.2's "fixed code
   is worse on 5 of 6 metrics" table, overturned by measuring the noise floor, and
   phase 19.1's independent version of the same lesson.
2. **The archive still reproduces the paper** (256.97 mm / 1.914 mm / 134.3x against
   the published 257 / 1.9 / ~135x), which remains useful: it confirms the pre-fix
   artifacts are a faithful record of the submitted state. It just cannot support an
   attribution claim.
3. **A separate and more serious issue surfaces: the published `~135x` is itself a
   single-seed draw from a wide distribution.** A reader reproducing E1 at another
   seed can legitimately obtain anything from ~97x to ~178x. The ratio inherits noise
   from both of its terms -- the refractive Z-RMSE alone varies 1.24 - 2.11 mm across
   seeds and depths.

**What IS robust:** the non-refractive baseline's depth error (205 - 252 mm) and the
refractive model's (1.2 - 2.1 mm) are separated by **two orders of magnitude** on
every seed tested. That statement is seed-stable and is the defensible form of the
claim. A precise multiplier is not.

**Do not pin `water_z` in the refractive arm.** There it is genuinely observable and estimating it
is the method's contribution; pinning it inflates the ratio to a flattering 168x and breaks §3's
stable-anisotropy claim (free: 1.95-2.19, matching the published ~2.3; pinned: drifts 2.21 -> 1.46).

### Determinism

**16 of 308 cells moved between repeats, before 63 of 308.** Twelve of fourteen configurations
reproduce exactly; movement is in `index/1.51` and `index/1.55`, eight cells each. On the full
post-fix schema (25 columns, including the optimality and guard columns the pre-fix pair could not
carry) it is 20 of 350. Computed by the same code path that produced the pre-fix figure, pinned by
a self-test that re-derives 63/308 before reporting anything (`determinism_probe.py --report`). The
two E6 repeats used structurally isolated output directories, and repeat 2 provably re-solved (zero
resume-skip lines).

> **CORRECTED 2026-08-14 — this entry read "8 of 308 ... all movement in `index/1.48`" until
> today, which was the phase 19.3 measurement.** Phase 19.4's interface fix requeued **both** E6
> repeats (`0ffbe15`), so the pair this statistic describes was replaced after the statistic was
> written; re-running `determinism_probe.py --report` against the current artifacts gives 16 of
> 308. The self-test still re-derives the 63/308 baseline exactly, so only the post-fix half had
> aged. MF-08's own 19.4 subsection records that E6 moved under that fix — the determinism figure
> simply was not re-derived alongside the numbers that were. **The direction of the claim is
> unchanged and still large (63 → 16); the size is halved.** Found while tracing the figure's
> provenance for the response letter, which now quotes 16.
>
> **The magnitudes, measured the same day, because the cell count alone invites a misreading.**
> The two runs carry the same `git_sha` (`2a623f9`), version and seed, so this is genuine
> run-to-run non-determinism on identical inputs — but it is bimodal. Every *accuracy* quantity
> agrees to **1e-9 relative or better** (`reconstruction_rmse_mm` 3.3e-9 worst, `reprojection_rms_px`
> 1.2e-10, `reconstruction_mae_mm` 2.7e-9); parameter errors agree to 1e-6–6e-5; and the whole of
> the visible movement is in the **convergence diagnostic**, where `optimality_stage3_intrinsic_pass`
> differs by **55%** on `index/1.55` (0.00235 against 0.00519). That is rule 9.1 appearing in the
> data rather than in the prose: optimality varies ~2× between runs of identical code, which is why
> it is never quoted beyond one significant figure. **The cause is not established here** — the
> pre-fix kink explanation no longer applies, and nothing measured rules for or against
> floating-point summation order, so it is reported as observed.

This is a **reported statistic, not a gate**. There is no tolerance in it and nothing to loosen.
The pre-fix cross-tabulation of movement against per-configuration degenerate count (correlation
0.19, no threshold rule) **has no post-fix counterpart**: the guard count is now zero for all
fourteen configurations, so the predictor has no variance and the correlation is undefined. That is
reported as undefined rather than as an improvement.

### §3 numbers requiring the author's edit

| quantity | submitted (v1.6.0) | seed-42 post-fix | seed band (n=4) | verdict |
|---|---|---|---|---|
| deepest non-refractive Z-RMSE | 257 mm | 248 mm | **199 - 252 mm** (n=10) | within noise |
| deepest refractive Z-RMSE | 1.9 mm | 1.94 mm | **1.42 - 2.25 mm** (n=10, mean 1.69) | within noise; published value is conservative |
| **abstract's improvement ratio** | **~135x** | 128x | **97 - 178x** (mean 139.5, sd 25.1, n=10) | **within noise — do NOT "correct" it**; published value is 0.18 sd from the mean |
| refractive Z/XY anisotropy | ~2.3 | ~2.1 | not yet banded | probably within noise |
| non-refractive Z/XY range | 0.4 - 5.8 | 0.9 - 12.6 | not yet banded | unknown |
| non-refractive focal drift | 5.7% | 5.3 - 7.0% | not yet banded | unknown |

**The honest summary is that §3's numbers did not measurably move.** The single-seed post-fix
values differ from the published ones, but every difference measured so far is small against its
own seed band. The rows marked "not yet banded" are not claims — they are single-seed
observations, and they should not be edited into the manuscript until a band exists for them.

Every qualitative claim in §3 survives, with one caveat: the refractive model maintains a stable
anisotropy ratio and the non-refractive baseline's depth error climbs steeply with range while its
lateral error grows far more slowly. The "sub-2 mm at every depth" bound is seed-sensitive — see
above.

### Which §3 claims are seed-robust, and which are not — a ranking for the revision

Ten seeds on the corrected geometry, ordered by stability. This is the most directly
actionable output of the re-measurement: it says which numbers the manuscript can state
sharply and which it cannot.

| claim | 10-seed spread | relative spread | verdict |
|---|---|---|---|
| inter-corner distance RMSE (refractive) | 0.4194 - 0.4216 mm | **0.5%** | **rock solid** — sub-mm on every seed |
| non-refr vs refr separation, order of magnitude | 199-252 mm vs 1.4-2.3 mm | — | **rock solid** — two orders on every seed |
| deepest refractive Z-RMSE | 1.42 - 2.25 mm | 46% | fragile as a bound |
| "below 2 mm at every depth" | fails on 2 of 10 seeds | — | **not a safe bright line** |
| **depth-axis improvement ratio** | **97 - 178x** | **80%** | **most fragile number in §3** |

**The abstract currently leads with the most seed-fragile quantity.** It opens with
"1.9 mm depth-axis RMSE at 2.5 m — a ~135x improvement", then mentions the
sub-millimetre inter-corner result second. The stability ordering is the reverse: the
inter-corner figure varies by 0.5% across seeds while the ratio varies by 80%.

Suggested for the revision (the author's call): lead with the inter-corner result,
which can be stated sharply and survives any reproduction, and give the depth-axis
advantage as "two orders of magnitude" rather than a specific multiplier. Nothing needs
to be retracted — every published value is inside its band, and ~135x sits near the mean
— but a precise multiplier invites a reviewer to reproduce it and get 97x or 178x.

**Why the two differ so much:** inter-corner distance is a *relative* measurement between
nearby points, so common-mode error cancels. Absolute Z-RMSE inherits the full
depth/`water_z` uncertainty. The robustness gap is structural, not incidental.

### Two §3 statements that are seed-sensitive or stale — found by tracing, not by the numbers check

**(a) The calibration depth range moved.** §3 says the calibration trajectory *"stayed within
0.10-0.84 m below the surface, so the deepest test depths probed extrapolation roughly 0.6 m
beyond the calibrated volume."* Measured post-fix (water_z = 1.031 m):

| measure | §3 | post-fix |
|---|---|---|
| calibration depth below surface | 0.10 - 0.84 m | corners **0.15 - 0.93 m**; centres 0.21 - 0.86 m |
| extrapolation beyond the volume | ~0.6 m | 0.54 m (corners) / 0.61 m (centres) |

Pre-fix the pose pivot was a board CORNER sampling `depth_range=(1.1, 2.0)`; post-fix it is the
board CENTRE against a derived floor (D-19.3-19 / D-19.3-01), so the calibrated volume genuinely
shifted — narrower at the top, deeper at the bottom. "Roughly 0.6 m" survives if measured to the
board centre and becomes ~0.54 m measured to the deepest corner. This is descriptive prose rather
than a table, which is exactly why a numbers-check over the result CSVs never touches it.

**(b) "Sub-2 mm at every depth" is seed-sensitive.** §3 states the refractive model *"holds its
Z-RMSE below 2 mm at every depth"*. Across the corrected-geometry seed sweep:

Across ten seeds the maximum refractive Z-RMSE at any depth ranges **1.457 - 2.254 mm**, and
**2 of 10 seeds exceed the stated bound**:

| seed | 42 | 43 | 44 | 45 | 46 | 47 | 48 | 49 | 50 | 51 |
|---|---|---|---|---|---|---|---|---|---|---|
| max refr Z-RMSE (mm) | 1.938 | 1.928 | **2.111** | 1.765 | 1.457 | 1.548 | 1.779 | 1.636 | **2.254** | 1.479 |

The claim is true for the reported run (seed 42 maxes at 1.938 mm) but fails on **20% of seeds** —
a bright line a reproduction can cross. **Compounding this, the paper never states which seed produced §3's
synthetic numbers, and E1's benchmark records carry no `seed` field** (the documented
seedless-legacy exemption in `tests/unit/test_experiments_provenance.py`). A reader therefore
cannot reproduce the exact run, and a different seed can break a stated bound.

Recommended for the revision: state the seed, and phrase the bound with its spread (e.g.
"approximately 2 mm across the tested volume") rather than as a strict inequality.

### A known reporting caveat in `benchmark_grid.csv`

The table's tenth row, `real_rig_13cam_200fr`, is **not** computed by E4 — it is copied from E2's
benchmark record, which is dated 2026-07-31 at commit `6c7f930b` and carries no degenerate-count
field. E2 is deliberately out of scope for this phase. Eleven of that row's fields moved relative
to the archived copy; **that movement is an E2-record refresh, not a geometry effect**, and must not
be read as one. The refresh is specifically `faa05b3` (MF-04): the degenerate-PnP guard rejected 10
poses of 3548 and moved E2's solve to a converged basin, changing `reprojection_rms` 1.019 -> 0.928
among others. **See MF-04 for that movement; it is not phase 19.3's and must not be attributed to
the geometry correction.** The gate's cross-artifact `git_sha` consistency check does not enumerate that
record, so its PASS covers the other nine rows. Recommended follow-up: widen the check to include
the E2 record it feeds from.

### What may and may not be said

**May be said.** A benchmark-construction flaw was found by the convergence instrumentation the
reviewers' own questions prompted, corrected at the source, and all six affected experiments
re-measured in a single frozen run. Convergence is now readable across the suite: every calibration
experiment reports a zero degenerate-observation count, E6's three non-converged configurations are
gone (verified on BOTH the interface and intrinsic optimality columns), and run-to-run reproduction
improved from 63 to 16 cells of 308 (corrected 2026-08-14; see the Determinism section above). The synthetic results are unchanged in substance: the
depth-axis improvement is two orders of magnitude, and the originally published ratio falls inside
the measured seed band. E7's accuracy is unchanged within its 10-seed band.

**May not be said.** That accuracy is unaffected for E1, E3, E4, E5 or E6 — none has a
corrected-geometry seed band supporting it, and E1's two metrics both fall OUTSIDE the band that
was measured. That the `~135x -> ~128x` difference is a real change, or that it is attributable to
any specific cause — it is 0.09x of the seed band and both an earlier version of this entry and a
session narrative asserted a decomposition that was measuring noise. That the fix *improved*
accuracy anywhere; nothing here measures that. That optimality improved by any specific factor
beyond one significant figure. That the determinism statistic is a pass. That the refractive model
is "below 2 mm at every depth" as an unconditional bound — seed 44 reaches 2.111 mm. That E6's
optimality collapse holds at seeds other than 42 — `scale/double_scale` is elevated on the
intrinsic pass at both non-42 seeds measured (n=3), so the collapse is a seed-42 observation about
a convergence *diagnostic*, not a general result. It carries no accuracy consequence either way.

---

## MF-09 — The edit map: every finding located in the pre-revision manuscript, with a verdict

**Status:** OPEN — this is the entry to work from when editing. It does not add measurements; it
maps MF-01 through MF-08 onto the actual submitted text and rules on each.
**Found:** 2026-08-03, by reading the manuscript against the findings file rather than by running
anything
**Source of truth for the manuscript side:**
`OneDrive - Georgia Institute of Technology/Thesis/Spinoffs/papers/aquacal/main.tex` and
`supplement.tex`, both dated 2026-06-29 12:56 — the source of the committed `main.pdf` of the same
timestamp. Code version C1 = **v1.6.0**. Line numbers below are `main.tex` unless marked.
**Source of truth for the measurement side:** MF-01, MF-04, MF-08 as cited per row.
**Why this entry exists:** MF-01–MF-08 each name "where the prose is" in general terms
(e.g. "§3's real-rig numbers", "the supplement's convergence claim"). Nobody had checked those
against the actual file. Doing so found three location errors and one edit that is already
unnecessary — see § "Corrections to earlier entries' locations".

### The ruling, in one line

**Most of §3's headline numbers must NOT be edited.** The re-measurement's main service was
establishing a noise floor, and it is wide enough to convert several apparent corrections into
noise. Four things genuinely need changing; six things must be left alone.

### Group 1 — Changes that improve the numbers (MF-04)

| location | published | corrected | delta |
|---|---|---|---|
| abstract L69, §3 L301 | inter-corner RMSE **0.674 mm** | **0.628 mm** | −6.8% |
| §3 L301 | MAE **0.268 mm** | **0.258 mm** | −3.7% |
| abstract L69, L301, L351 | **0.45%** mean relative error | **0.43%** | −3.72% |
| L301 | 7,762 comparisons | 7,762 | **unchanged** |

**Cause:** the degenerate-PnP guard rejects 10 poses of 3,548 whose translations reached
3.09e12 m. `n_params`, `n_groups`, `n_residuals` (147,950) and `n_comparisons` (7,762) are all
identical across the two runs — the data and the problem are unchanged; only initialization
differed.

**Do not present this as an accuracy improvement.** The published record's
`stage3_intrinsic_pass` first-order optimality was **2.08e4**; the re-run reaches **18.4**. The
published numbers came from a solve that had not converged, behind a 1.019 px RMS that looked
entirely publishable. MF-04's framing governs: a defect in pose initialization allowed a
non-converged solution to be reported, the defect is fixed, and §3 now reports a converged solve.
The improvement is a consequence of fixing a correctness bug.

**`mean_reprojection_px` (1.019 → 0.928) does not appear in the manuscript** and needs no edit.

### Group 2 — Changes that weaken a stated claim

| location | published | measured | why it matters |
|---|---|---|---|
| **L280** and figure caption **L295** | "$Z$-RMSE **below 2 mm** at every depth" / "maintains sub-2 mm $Z$-RMSE at all depths" | **fails on 2 of 10 seeds** — seed 44 → 2.111 mm, seed 50 → 2.254 mm | a strict inequality a reproduction can cross |
| **L204** *and* supplement **L226** | Newton converges in "**2--4 steps**" / "two to four steps" | **2–6**, median 4.0, zero non-convergence | 1.5x under-provisioning |

**On the sub-2 mm bound.** True for the reported run — seed 42 maxes at 1.938 mm — but the paper
never states which seed produced §3's synthetic numbers, and E1's benchmark records carry no
`seed` field (the documented seedless-legacy exemption). A reader cannot reproduce the exact run,
and 20% of seeds break the bound. MF-08's recommendation stands: state the seed, and phrase the
bound with its spread rather than as a strict inequality.

**On the Newton range.** Per MF-01 this is not a simple 4→6 swap. The production batch loop
terminates on `np.all(...)`, so every point pays for the batch's slowest point: the per-point
production cost is the **max**, while the median 4 describes *individual* root-find difficulty.
Report both quantities and say which is which. Quoting 6 alone would overstate individual cost as
badly as "two to four" understates production's.

### Group 3 — Stale descriptive prose (MF-08)

| location | published | post-fix |
|---|---|---|
| **L274** | calibration trajectory "stayed within **0.10--0.84 m** below the surface" | corners **0.15–0.93 m**; centres 0.21–0.86 m |
| **L274** | "extrapolation roughly **0.6 m** beyond the calibrated volume" | **0.54 m** to deepest corner; **0.61 m** to centre |

Pre-fix the pose pivot was a board CORNER against `depth_range=(1.1, 2.0)`; post-fix it is the
board CENTRE against a derived floor (D-19.3-19 / D-19.3-01), so the calibrated volume genuinely
shifted — narrower at the top, deeper at the bottom. **"Roughly 0.6 m" survives** if measured to
the board centre.

### Group 4 — A number the paper understates in its own favour (MF-08)

**L227** states that CPR column grouping reduces finite-difference evaluations "by roughly an
order of magnitude for a typical 12-camera, 100-frame problem." Measured on **exactly the case
the sentence names**: **42x**. The paper understates its own result by roughly 4x. This is a free
improvement and the only edit in this entry that strengthens a claim.

### Group 5 — Numbers that moved but must NOT be edited

| location | published | post-fix (seed 42) | 10-seed band | verdict |
|---|---|---|---|---|
| abstract **L68**, **L281** | **~135x** | 128x | **97–178x** (mean 139.5, sd 25.1) | published is **0.18 sd from the mean** |
| abstract **L68**, **L281**, caption **L295** | **1.9 mm** | 1.94 mm | 1.42–2.25 (mean 1.69) | published is **conservative** |
| **L281**, caption **L295** | **257 mm** | 248 mm | 199–252 mm | see caveat |
| **L280** | $Z/XY \approx$ **2.3** | ~2.1 | not banded | do not edit |
| **L280** | non-refr $Z/XY$ **0.4–5.8** | 0.9–12.6 | not banded | do not edit |
| **L270** | non-refr focal drift **5.7%** | 5.3–7.0% | not banded | do not edit |

**The `135x -> 128x` difference is 7x against an 81x band — 0.09x of the band, 0.28 sd.**
An earlier revision of MF-08 reported it as a corrected §3 number *and* decomposed it to the
geometry fix; both are retracted there. Editing it would publish noise, and would be the third
instance of this milestone's recurring error.

**Caveat on the 257 mm figure, stated more sharply than MF-08 does.** MF-08's §3 table marks it
"within noise", but **257 sits just above the corrected-geometry band maximum of 252 mm**. This is
not a contradiction — 257 is a pre-fix value being compared against a post-fix band, and the
geometry correction moved the calibrated volume — but it is the only headline figure not strictly
inside its band, and it should be known before a reviewer recomputes it. It is not grounds for an
edit; the three "not banded" rows below it are the stronger reason to leave this whole group alone.

**The rows marked "not banded" are not claims.** They are single-seed observations and must not be
edited into the manuscript until a band exists.

### Group 6 — Not a correction: E6 is absent from the manuscript

**The generalization sweep does not appear in `main.tex` at all** — no mention of the sweep, the
layout axis, or the scale axis. E6 was built for the revision (reviewer point R1.4), so everything
from it is **new content**, not an edit to existing prose. Practical consequence: E6's seed
fragilities constrain what may be written in new text; they contradict nothing already published.

### Corrections to earlier entries' locations

Found by checking the manuscript rather than by re-measuring. Each is a place an author following
an earlier entry literally would have made an incomplete edit.

1. **MF-01 mislocates the Newton claim.** It says "supplement, the refractive-projection
   convergence claim". The claim appears in **both** `supplement.tex:226` ("two to four steps")
   **and `main.tex:204`** ("solves this in 2--4 steps"). Editing only the supplement leaves the
   same understatement in the body.
2. **MF-04's `water_z` and camera-height movement has an unnamed manuscript location.** MF-04
   records that `water_z` moved 1.030555 -> 1.073840 m and that `camera_height_range_m` also
   moved, but names no location. It is **Figure `rig-3d`'s caption, L262**: "the estimated water
   surface at $z_w \approx \SI{1.03}{\meter}$" and "estimated camera heights range from 1.01 to
   \SI{1.08}{\meter}". Both move under the re-run. Note the caption also ties these to "the
   physically measured distance of ~1 m", so the sentence needs reading as a whole, not a
   find-and-replace.
3. **MF-04's "representative of" edit is already unnecessary.** MF-04 asks that any claim the
   synthetic rig *matches* the deployment be softened. **L267 already reads** "a 12-camera rig
   configured as an **idealized version** of the real-world setup". No edit needed in the body.
   (The supplement was not audited for this at the same depth.)

### The highest-value change is not a number

The abstract (**L68**) leads with "1.9 mm depth-axis RMSE at 2.5 m --- a ~135x improvement" and
mentions the sub-millimetre inter-corner result second. **The stability ordering is the reverse:**

| claim | 10-seed relative spread |
|---|---|
| inter-corner distance RMSE | **0.5%** (0.4194–0.4216 mm) |
| depth-axis improvement ratio | **80%** (97–178x) |

Leading with the inter-corner figure and giving the depth-axis advantage as "two orders of
magnitude" rather than a specific multiplier **retracts nothing** — every published value is
inside or conservative to its band — while removing the one invitation for a reviewer to
reproduce the headline and obtain 97x or 178x. MF-08 reaches the same recommendation; this entry
adds that it is the single lowest-risk, highest-value edit available.

### Scope note

This entry covers the manuscript comparison only. **It does not fold in the 2026-08-03 E6
seed-band measurement** (seeds 62 and 28, both `{'ok': 14}`), which contradicts MF-08's claim that
E6's accuracy silence is *structural* rather than a measurement backlog item. That amendment to
MF-08 is still outstanding and is deliberately not made here. See
`.planning/debug/e6-seed-locked-clearance-floor.md`.

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
> fourteen generalization configurations converge to first-order optimality at or below 2e-2, every
> calibration experiment reports a zero out-of-domain observation count, and run-to-run
> reproducibility improved from 63 to 16 of 308 compared cells.
>
> We note explicitly that this was a defect in benchmark construction and convergence *diagnosis*,
> not in the calibration result. Before the correction, reconstruction accuracy was statistically
> indistinguishable between the affected and unaffected configurations (0.594 mm versus 0.562 mm
> mean RMSE), and the single worst-converged configuration had the best reconstruction accuracy in
> the table.
>
> The reported synthetic results are unchanged in substance. We re-ran the synthetic validation
> across ten random seeds to establish a noise floor. The depth-axis improvement over non-refractive
> calibration varies between roughly 97x and 178x depending on the seed (mean 140), and the
> originally reported figure of ~135x falls close to the centre of that distribution rather than at
> its edge. We have accordingly rephrased the claim in
> terms that are stable across seeds: the non-refractive baseline's depth error at the most
> extrapolated test depth is two orders of magnitude larger than the refractive model's
> (approximately 199-252 mm against 1.4-2.3 mm). We also now state the random seed used for the
> reported run, which the original submission omitted.

> **CORRECTED 2026-08-14 — this block said "205-252 mm against 1.4-2.1 mm" until today.** Both
> outer bounds were wrong against the committed band: recomputing the deepest test point from
> `experiments/results/exp1_band.csv` gives non-refractive **199.29-252.06 mm** (mean 228.83) and
> refractive **1.42-2.25 mm** (mean 1.69) over the ten seeds. The draft's 205 and 2.1 appear to
> predate the committed band. This block is the one the response letter was to be drafted from, so
> the error was one paste away from reaching the document a reviewer reads most adversarially; the
> letter was written from the artifacts instead and quotes 229 mm with the 199-252 band.

---


### UPDATE 2026-08-07 — what phase 19.5's bands changed in this map

The rows above stand. Four things are added or resolved, and one row's cited artifact was wrong
until today.

**The `~135x` row is now backed by a committed artifact — it was not before.** The row cites the
97-178x band, but the band was regenerable only from gitignored `seed_sweep_19_3/` output:
`exp1_band.csv` carried a scale-corrected `rmse_mm`, not the raw `z_rmse_mm` the ratio is built
from. Quick task 260807-dcv added the column and re-ran the ten seeds, which reproduced the band
exactly. See **MF-16**. Anyone editing L68/L281 should now cite `exp1_band.csv` directly.

**`~135x` survives; `257 mm` does not.** The ratio of the two arms' means at 2.5 m is **135.4x**,
so the published figure holds as a ratio of means over n=10 rather than as seed 42's value
(128.1x). The millimetre figure should become **~229 mm (n=10, range 199-252)**. This resolves the
"see caveat" on the `257 mm` row.

**Three new destinations, none of which existed when this map was written:**

| where | what to add | source |
|---|---|---|
| R1.3's response | accuracy improves from N=8 to N=12 (~6 sd) then **plateaus**; N=12 and N=16 indistinguishable (~0.4 sd), n=6 seeds per point | MF-11 |
| R2's response, §3 index discussion | index-induced scale bias stays below the holdout noise floor across seeds 42-47 (n=6); reconstruction effect of +/-0.01 is ~5x below seed noise | MF-13 |
| §3 layout discussion / deployment guidance | collinear arrays do not locate the water surface reliably (worst seed 18.9 mm, 12x worse camera XY error), and the failure is invisible to reprojection and reconstruction | MF-12 |

**Two figure changes.** `fig:aquacal-exp3-rmse` and the depth-generalization figure can now carry
**per-depth error bars** (10 seeds x 8 depths x 2 models). They reveal the non-monotone dip at
1.4 m and that the refractive arm is far more stable, not merely more accurate — sd 0.17-0.31 mm
against 6-17 mm. Captions must state these are calibration-scenario variance against a **fixed
test set** (`depth_seed` is hardcoded), not full replication spread.

**One standing prohibition is reinforced, not changed.** MF-14 measures a ~1.85x wall-clock spread
at identical `nfev` on the same machine and sha. Any timing sentence must report `nfev` beside
wall-clock, and no runtime difference anywhere in the paper may be attributed to a code change.

### UPDATE 2026-08-10 — MF-18 closes the convergence-certification question for L268/L271; no new edit

**Group 2 and Group 5 stand unchanged.** MF-18 (phase 21 plan 12) settles, by measurement, the
open question the folded todo raised: whether the `n_water=1.0` baseline's reported optimality
and reprojection RMS can be trusted, given it is the only arm in the entire suite that ever
triggers `DegenerateObservationWarning` (14,949 hits at the committed E1 record). **They can be
trusted.** At `n_air = n_water = 1.0` the refractive projector and the pinhole model agree to
`atol=1e-12` (`tests/unit/test_refractive_geometry.py::TestUnitIndexPinholeIdentity::test_projection_reduces_to_pinhole_at_unit_index`),
so this arm's C0-but-not-C1 kink has zero magnitude and the guard's disqualification does not
bite here specifically.

**No new location or edit is added by this entry.** L268's "sole experimental variable" framing
already stands (Group 5 treats it as correct); L271's 1.376 px RMS citation is now confirmed
admissible rather than merely unchallenged. The band-attachment edit at L68/L281 that MF-16
already specifies (state `97-178x` alongside `~135x`) remains the only action item touching this
comparison — MF-18 does not add to it.

**One thing MF-18 explicitly does NOT license:** treating E1's absolute numbers (any of L270,
271, 278, 280's specific values) as certified accurate in the sense of D-19.3-17's seed-band
gate. `experiments/e1_refractive_comparison.py:42`'s "E1 carries NO accuracy claim" stands
independently of convergence — MF-18 answers "is the solve converged," not "is the D-19.3-17
gate satisfied." Only MF-16's ratio band clears that gate, and only for the ratio.

**Instrumentation gap, not a manuscript action.** MF-18 also finds that
`degenerate_observations_at_solution` merges above-interface and behind-camera guard hits into
one counter with no committed way to split them. This affects nothing publishable — the
convergence question is settled independently of the split — and is recorded as a small
low-priority fix for the post-Zenodo repair batch, not as anything requiring a manuscript
response.

## MF-10 — Synthetic validation ran against a ground truth where each camera had its own water surface

**Status:** OPEN — needs a disclosure sentence in §3 before resubmission
**Found:** 2026-08-04, phase 19.4 planning, by auditing the scenario generators rather than by
running anything
**Corrected and re-measured:** 2026-08-05, phase 19.4 plan 09 (queue run at git sha `2a623f9`,
artifacts committed `0ffbe15`)
**Source of truth:** `19.4-RESCOPE-PROPOSAL.md` (the five-source audit and the pixel measurement);
`experiments/results/` at `0ffbe15` against
`experiments/archive/e{4,6}-2026-08-04-pre-interface-fix/`
**Where the prose is:** §3 Synthetic validation — the scenario description, not the results.
Follow MF-09's location conventions before editing.
**Relates to:** MF-08 (its E4/E6 rows are re-measured under this fix)

### The defect, stated precisely

The method, and the manuscript describing it, rest on a **single flat refracting interface**: one
water surface, shared by every camera. `generate_camera_array` did not build that. It gave **each
camera its own water surface**, so the synthetic ground truth that validated the method violated
the premise the method assumes.

An audit of all five scenario sources found **two affected**. The other three — including
`generate_real_rig_array()`, which E1, E5 and E7 run in production — use a frozen shared
`WATER_Z` and were never affected. This is why only E4 and E6 moved.

**The magnitude, measured rather than argued.** Over **31,680 corner observations**, the
displacement between the per-camera surfaces and a single shared one was **mean 1.42 px, max
6.33 px**, against a reprojection RMS of ~0.4-0.9 px. *The modelling error was larger than the
residual being reported.* That is what makes this disclosable rather than negligible.

**The 1.42 px figure is one seed and one trajectory. It is NOT an effect size** and must never be
quoted as one. Its only job is to establish that the defect was real and dominant relative to the
residual — a threshold judgment, not a measurement of impact.

### What it changed, and what it did not

Re-running the full suite once under a single git sha moved **only E4 and E6**. E1, E3, E5 and E7
were confirmed inert by byte-comparison of their committed artifacts, not merely by source-level
argument. Detailed movement is tabulated in MF-08's 19.4 subsection; neither E4 nor E6 carries an
accuracy claim, because neither has a seed band.

The clearest signature is E6's `water_z_error_mm_mean`: **~3.41 mm in every configuration before
the fix — exactly 3.4057 in 10 of 14 rows, unmoved by refractive index, layout or scale — and
0.027-2.518 mm after**. An error that ignores the experiment's own variable is the ground truth
showing through, not the estimator.

### The consequence for the manuscript is favourable, and should be stated plainly

**The correction strengthens E7's published conclusion rather than weakening it.** E7 compares a
shared interface model against a per-camera one. On the corrected geometry there genuinely *is*
one surface, so "shared" is the correct model — and the `fixed` pairing is unanimous, 10/10 with
no zero crossing (`experiments/results/interface_ablation_band.csv`). The earlier geometry was, if
anything, biased *against* the conclusion the paper draws.

**Recommended disclosure.** A sentence in §3 stating that the synthetic scenario generator was
found to place a separate interface per camera, that this was corrected and the affected
experiments re-measured before resubmission, and that the corrected geometry is the one reported.
Reviewers who read the generator would find this first; disclosing it costs a sentence, and not
disclosing it costs the paper's credibility on exactly the point it claims as its contribution.

---

## MF-11 — E6's seed band: accuracy improves with camera count and then plateaus at 12

**Status:** OPEN — R1.3's "stably adapts to N>10" has no measured answer in the current prose
**Found:** 2026-08-07, phase 19.5 plan 10 (the production queue), analysed plan 11
**Source of truth:** `experiments/results/generalization_sweep_band.csv` (102 rows, seeds 42-47,
17 configurations per seed) + `experiments/results/e6_seed_band_provenance.json`, both at git sha
`2a2f0fa`
**Where the prose is:** R1.3's response; §3 wherever camera count is discussed. Follow MF-09's
location conventions before editing.
**Discharges:** COV-03, COV-04.

### The band

**102 rows, `status="ok"` on every one** — `ok=17` for each of seeds 42-47 individually, zero
non-`ok`. This is the seed band D-19.3-17 requires before E6 may carry an accuracy claim at all,
and E6 did not have one until now.

### Accuracy vs camera count (COV-04) — the new result

`reconstruction_mae_mm`, n=6 seeds per point:

| N | mean (mm) | sd | min | max |
|---|---|---|---|---|
| 8 | 0.3773 | 0.0067 | 0.3670 | 0.3837 |
| 12 | 0.3345 | 0.0057 | 0.3266 | 0.3428 |
| 16 | 0.3371 | 0.0076 | 0.3272 | 0.3475 |

**8 to 12 improves by 0.043 mm, roughly 6 sd — real. 12 to 16 differs by 0.0026 mm, about 0.4 sd
— within noise.** Accuracy improves with camera count and then **plateaus at 12**; N=12 and N=16
are indistinguishable at this geometry.

R1.3 asked whether the method "stably adapts to N>10". Nothing measured accuracy-vs-N before —
E4 measured timing-vs-N only. **This is a measurement, not an explanation:** the plateau is what
was observed, and no mechanism for it is claimed.

### COV-03's two named seed-fragile spots, adjudicated

| spot | metric | band (n=6) | verdict |
|---|---|---|---|
| `scale/double_scale` | intrinsic-pass optimality | 2e-3 to 2e-2 (1 s.f.) | **Converged at every seed.** Varies ~7x across seeds but every value is small. Not fragile in the way that mattered. |
| `layout/line` | `water_z_error_mm_mean` | 1.258 - 18.855 mm | **Fragile — see MF-12, which this entry does not attempt to summarise.** |

Optimality is quoted to ONE significant figure throughout; it varies ~2x run to run and no finer
statement is supportable.

---

## MF-12 — The line layout's 18.9 mm water-surface error is ~80% datum shift; the real standoff error is ~2.4 mm

**Status:** OPEN — no prose warns against collinear arrays, and the metric that reported this
cannot distinguish the two cases
**Found:** 2026-08-07, phase 19.5 plan 11, analysing plan 10's band; **mechanism measured the same
day** by re-solving the configuration and reading signed values
**Source of truth:** `experiments/results/generalization_sweep_band.csv`, `layout` axis, at
`2a2f0fa`, plus a zero-artifact re-solve of `layout/line` and `layout/grid` at seed 43
**Where the prose is:** §3's layout discussion and any deployment guidance on camera placement.
**Relates to:** MF-11 (same band); the knowledge-base entry "A mean-absolute error metric can hide
whether two errors add or cancel".

### What the band reported

Ranked by spread **ratio**, `layout/line` is unremarkable — five index configurations exceed it
(up to 47x) purely because their minima sit near zero, which inflates a ratio without meaning.
**Ranked by magnitude it is the clear outlier:**

| config | `water_z_error_mm_mean` | max |
|---|---|---|
| **layout/line** | **5.245 mm** | **18.855 mm** |
| scale/double_scale | 1.716 | 2.518 |
| layout/grid (baseline) | 1.025 | 1.687 |
| layout/ring | 0.778 | 1.357 |

Camera XY position error is also **12x** grid's (1.838 mm against 0.155 mm), and one seed of six
reached 18.9 mm — a heavy tail, not a uniform degradation.

### What it actually is

`water_z_error_mm_mean` is a mean **absolute** error, so the committed artifacts cannot say whether
the surface error and the camera-Z error **add** or **cancel**. Re-solving both layouts at seed 43
and reading signed values settles it:

| | LINE | GRID |
|---|---|---|
| water_z error (signed) | **-18.8547 mm** | -0.8326 mm |
| camera Z error, raw (signed mean) | **-18.4955 mm** | -0.2184 mm |
| camera Z error, **gauge-corrected** | 1.6814 | 0.0199 |
| **`h_c` error (signed mean)** | **-0.3592 mm** | -0.6142 mm |
| gauge correction removes | **79.5%** of the Z-error magnitude | **4.6%** |

`Cz_raw` reproduces the committed `z_position_error_mm_mean` of -18.4955 exactly, so the re-solve
is faithful to the production run.

**The surface and the cameras move together, in the same direction, by nearly the same amount.**
The physical camera-to-surface gap `h_c = water_z - C_z` — the quantity that actually enters the
refraction geometry — is off by **0.36 mm in the signed mean**, against an 18.85 mm world-frame
surface error. Roughly **80% of the apparent error is a global Z datum shift**: the rig and the
water surface slid through the world frame together.

The 79.5%-vs-4.6% contrast is the discriminator. A grid array barely admits such a shift; a
collinear array admits it almost freely. **This is the camera-height / interface-distance
degeneracy** Phase 16's HOOK-03 conditioning diagnostics were built to measure (success criterion 3
names that parameter block, for the WP6 argument) — a collinear array has no baseline perpendicular
to its own axis, so the geometric diversity that would pin the datum is largely absent.

### The residual is real, and smaller by an order of magnitude

Removing the datum does not clear the line layout. Per-camera `h_c` errors, excluding `cam0` (the
reference, pinned at `C_z = 0` by construction, so its `h_c` error is *identically* the `water_z`
error) and `cam1` (which the solve leaves poorly constrained):

- **LINE: ~2.4 mm** mean absolute
- **GRID: ~0.6 mm** mean absolute

So the line layout is genuinely about **4x worse at recovering the physical interface standoff** —
a real finding, and one worth stating in deployment guidance — but it is **not** an 18.9 mm failure
to locate the water surface. The headline number is dominated by a gauge artifact that no accuracy
metric should charge against the method.

### Why it hides from every accuracy metric

The worst seed's error costs **0.11 px** of reprojection RMS (0.815 vs 0.705) and **0.045 mm** of
reconstruction MAE (0.382 vs 0.337). A coordinated datum shift is very nearly unobservable in the
data — which is exactly why it is a datum shift rather than an error.

**This is the project's weak-observability signature**: recovered geometry drifts while error
metrics stay clean. It is a concrete reason a low reprojection error cannot certify rig geometry.
The novel part here is that most of the drift turned out to be **gauge, not geometry** — the
opposite of what the raw column suggested.

### The metric defect this exposed

Two problems, both fixable and neither yet fixed:

1. **`water_z_error_mm_mean` is mean-absolute**, so it destroys the sign that distinguishes a
   harmless datum shift from a real standoff failure. Add `water_z_error_mm_signed`.
2. **E6 calls `compute_per_camera_errors(result, scenario)` without `gauge_correct_z`**, which
   defaults to `False`. The library documents that flag as removing "a global datum offset the
   optimizer applied to the entire rig (an artifact of choosing where Z=0 is, not a real geometric
   error)". E6's Z errors are therefore reported uncorrected, and `layout/line`'s are ~80% artifact.

**Proposed for the post-Zenodo re-run:** report `water_z_error_mm_signed` and a per-camera
`interface_standoff_error_mm` **alongside** the existing column, not instead of it — if the rig and
surface drift together, `h_c` looks perfect while the reconstruction is displaced, so replacing one
with the other would trade a visible failure mode for an invisible one. Exclude the reference
camera from any `h_c` mean, or report it separately: its `h_c` error equals the `water_z` error by
construction and otherwise dominates the average.

### Still worth doing

The conditioning diagnostic would convert the mechanism from strongly-evidenced to directly
measured: run Phase 16's HOOK-03 diagnostic on a line solve and a grid solve at the same seed and
compare the camera-height / interface-distance correlation block. One calibration each, no new
code. The gauge-correction contrast already predicts what it will show.

---

## MF-13 — Index sensitivity sits far below seed noise; E5 regains a bounded accuracy claim

**Status:** OPEN — R2's headline is currently stated against one run's number
**Found:** 2026-08-07, phase 19.5 plan 10, analysed plan 11
**Source of truth:** `experiments/results/index_sensitivity_seed_band.csv` (66 rows, seeds 42-47,
11 assumed indices per seed) + `experiments/results/e5_seed_band_provenance.json`, at `2a2f0fa`
**Where the prose is:** R2's response and §3's refractive-index discussion.
**Discharges:** COV-05. **Supersedes:** MF-08's "E5 — NONE" verdict, and the reason given for it.

### The measurement

Across the full swept range of +/-0.010 in assumed index, against seed noise at each point:

| metric | effect of +/-0.01 | seed sd | verdict |
|---|---|---|---|
| reconstruction MAE | 0.0040 mm | 0.0205 mm | **noise is 5.1x larger** |
| reconstruction RMSE | 0.0071 mm | 0.0396 mm | **noise is 5.6x larger** |
| reprojection RMS | 0.0024 px | 0.0020 px | comparable, and **not monotone** in delta_n |
| scale bias | 0.0245 pp | 0.0110 pp | ~2 sd |

`scale_bias_over_floor` runs **0.035 - 0.058**: index-induced bias is 3-6% of the holdout noise
floor, at every seed.

Two further points the data supports. At the **correct** index the scale bias is 0.0483% —
*larger* than the change a +/-0.01 error produces, so getting the index right does not remove the
dominant bias and is not its cause. And for scale, fresh water 1.333 to seawater ~1.339 is
delta_n ~0.006 while temperature contributes ~1e-4 per degC, so the swept range covers realistic
misestimation generously.

### The claim this licenses, and its limit

E5 was demoted under D-19.3-17 because `e5_provenance.json` varies the **assumed index**, not the
seed, and so could not bound seed noise. **That gap is now closed**, and the claim is restored in
this bounded form and no wider:

> Index-induced scale bias remains below the holdout noise floor across seeds 42-47 (n=6).

**It must NOT become "the method is insensitive to refractive index."** That generalises past a
+/-0.010 sweep at one geometry with 30 frames, and says nothing about gross errors such as
mistaking water for acrylic.

This wording is also the evidence the roadmap cites for deferring Phase 20 (the temperature/
salinity helper): a hand-entered 1.333 is adequate for accuracy at this geometry.

---

## MF-14 — A wall-clock noise floor at constant computational work

**Status:** OPEN — any shipped timing table must report nfev beside wall-clock
**Found:** 2026-08-07, phase 19.5 plan 10
**Source of truth:** `experiments/results/benchmark_grid_repeat.csv` (6 rows, 3 cells x 2
repeats) + `experiments/results_e4_repeat/repeat_stdout.log`, at `2a2f0fa`
**Discharges:** COV-06. **Strengthens:** MF-03.

| cell | nfev | repeat 1 | repeat 2 | ratio | `seconds_total_spread_pct` |
|---|---|---|---|---|---|
| 8x100 | 29 | 678.18 s | 360.35 s | 1.88x | 61.21 |
| 12x100 | 20 | 577.89 s | 302.72 s | 1.91x | 62.50 |
| 16x100 | 40 | 1120.98 s | 598.80 s | 1.87x | 60.73 |

**`nfev` is identical within every cell** while wall-clock moves ~1.85x, first-run-slower in all
three. Same code, same git sha, same machine, minutes apart, with the two repeats scheduled
back-to-back specifically so neither met different memory pressure.

This is an empirical **noise floor for wall-clock at constant computational work**, and it is the
same order of magnitude as 19.4's unexplained ~2x observation. It does **not** explain 19.4 —
different stages, n=1 there — but it establishes that a ~2x wall-clock difference sits inside this
machine's demonstrated run-to-run range with the algorithm held fixed. It is the strongest
support MF-03's nfev-beside-wall-clock requirement has.

**The standing prohibition holds:** no runtime figure here is attributed to any code change, in
either direction.

*Recording gaps, reported not fixed:* repeat-2 rows carry an empty `cell_key` and `status`, and
each cell's `benchmark.json` is overwritten by repeat 2, so repeat 1's per-stage detail survives
only in the committed `repeat_stdout.log`.

---

## MF-15 — E2's band measures split variance on fixed data, and says so

**Status:** OPEN — the scope qualifier must appear in prose, not only in the artifact
**Found:** 2026-08-07, phase 19.5 plan 10
**Source of truth:** `experiments/results_e2_band/seed_{42,43,44}_e2_out/real_rig_metrics.json`
plus `e2_band_scope.json`, at `2a2f0fa`
**Discharges:** COV-07.

Three seeds, three **distinct** metric records. **Seed 42 reproduces the committed
`experiments/results/real_rig_metrics.json` exactly** — identical key sets and not one differing
value, which is stronger than the gate's `rtol=1e-6` check.

**Scope, which must be stated wherever the band is quoted:** this is **split variance on fixed
data, NOT measurement variance.** `config.seed` threads into `split_detections`; it does not
resample the rig, the images, or the detections. A reader who took it for reproducibility spread
would be overstating it.

---

## MF-16 — E1's band is now regenerable, and the "upper bounds" caveat is unnecessary

**Status:** OPEN — L68 and L281 need the millimetre figure corrected
**Found:** 2026-08-07, quick task 260807-dcv
**Source of truth:** `experiments/results/exp1_band.csv` (160 rows, 12 columns, seeds 42-51) plus
`experiments/results/e1_seed_band_provenance.json`, at git sha `cda9d0e`
**Where the prose is:** the abstract's improvement ratio (L68) and §3's deepest-point sentence
(L281).
**Corrects:** MF-08's artifact citation for the 97-178x spread.

### MF-08's citation was wrong

MF-08 states the spread "regenerates from `experiments/results/exp1_band.csv`". It did not. That
CSV carried `rmse_mm`, a **scale-corrected** residual; computing the ratio from it gives
**1.1x-2.9x**, a different quantity by two orders of magnitude. The raw `z_rmse_mm` the ratio is
built from lived only in the seedless `exp3_xy_vs_z_anisotropy.csv` (seed 42, no seed column) and
in gitignored `seed_sweep_19_3/` output. **No committed artifact held a 10-seed band of the
quantity the abstract's headline uses.**

Root cause was a code gap: `_run_band`'s runner computed four dataframes and returned only
`df_exp2`, discarding the one holding `z_rmse_mm`. Re-running the band would have reproduced the
same gap indefinitely. Fixed in `cda9d0e`; the band re-run at `fea64a9` now carries the column.

### The band, reproduced exactly

| seed | 42 | 43 | 44 | 45 | 46 | 47 | 48 | 49 | 50 | 51 |
|---|---|---|---|---|---|---|---|---|---|---|
| ratio | 128.1 | **178.0** | **97.3** | 153.4 | 157.8 | 131.4 | 134.0 | 158.9 | 99.1 | 156.5 |

**97.3x - 178.0x, mean 139.5, sd 25.1 (population), n=10** — every value matching what was
measured on 2026-08-03. E1's determinism is now confirmed three times over.

### The "upper bounds" caveat is NOT needed

An earlier reading treated `gate1_guard_count`'s 14,949 guards on the non-refractive arm as
evidence the baseline had not converged, which would have made the ratios upper bounds. **MF-08
had already settled this the other way.** At `n_water = 1.0` the refractive model reduces to
pinhole, so `water_z` cannot affect any projection while still gating the domain test — an exact
null direction. Sweeping `water_z` over 1.5 m leaves the cost constant to 13 significant figures
while the guard count climbs to 14,949, and pinning `water_z` at ground truth reproduces every
non-refractive number to ~4 significant figures with guard count 0 and optimality 5e-01. The
comparison is unaffected by the guard.

### What the prose should say

The paper reads "257 mm ... approximately 135x" (L281) and "~135x" (L68). Corrected-geometry seed
42 is 248.3 mm / 128.1x — but the **ratio of the two arms' means at 2.5 m is 135.4x**, essentially
the published figure. So:

- **`~135x` stands**, as a ratio of means over n=10 rather than as one seed's value.
- **`257 mm` is stale** and should become **~229 mm (n=10, range 199-252)**.
- §3 has room to state the band, `97-178x`, which the abstract does not need to carry.

Two caveats that **are** required. The deepest test point sits **~0.6 m outside the calibrated
volume** (1.18-1.90 m), and the non-refractive curve is non-monotone — 49.5 mm at 1.1 m, a minimum
of 9.5 mm at 1.3 m, 248 mm at 2.5 m — so the headline ratio is the most favourable point in the
sweep by a wide margin. And the evaluation test set is **not reseeded** (`depth_seed = 42 +
int(depth*100)` is hardcoded, verified by `n_points` being byte-identical across all ten seeds),
so the band measures calibration-scenario variance against a fixed test set, not full replication.

### Per-depth error bars are now available

10 seeds x 8 depths x 2 models, for both figures. The regenerated figures should carry them: they
show the non-monotone dip at 1.4 m, and that the refractive arm is not merely better but **far
more stable** (sd 0.17-0.31 mm against 6-17 mm) — arguably a stronger argument than the ratio, and
currently invisible. The caption must state that they are calibration-scenario variance against a
fixed test set.

---

## MF-17 — E7's `fixed` arms are vacuous, not null

**Status:** OPEN — a reader cannot currently tell the two apart
**Found:** 2026-08-06, phase 19.5 plan 03; confirmed plan 11
**Source of truth:** `experiments/results/e7_focal_standoff.csv`
**Discharges:** COV-08 (in part).

The `refined` arms answer the L149 focal/standoff degeneracy question WP6 planned and MF-05 never
reported. **The `fixed`-arm rows are vacuous by construction** — intrinsics are never refined, so
focal-drift variance is identically zero — yet the CSV labels them `no_signature`, the same label
a genuine null carries.

**Those two rows must not become a manuscript claim.** A statistic that is undefined by
construction is not evidence of absence.

---

## MF-18 — At n_water=1.0 the refractive projector IS the pinhole model; the baseline is converged, but E1's own no-accuracy-claim statement still stands

**Status:** OPEN — needs the reframing described below; no manuscript prose edited here
**Found:** 2026-08-10, phase 21 plan 12, settling the folded todo
`2026-08-05-verify-non-refractive-baseline-supports-paper-claims.md` by measurement rather than
source reading
**Source of truth:** `tests/unit/test_refractive_geometry.py::TestUnitIndexPinholeIdentity::test_projection_reduces_to_pinhole_at_unit_index`
(regenerable — run the node id directly); `experiments/results/e1_benchmark_nonrefractive.json`
(the committed `degenerate_observations_at_solution: 14949` count); `experiments/e1_refractive_comparison.py:42`
**Where the prose is:** `main.tex` lines 68, 268, 270, 271, 278, 280, 281, 295 (per MF-09's
location conventions) — the entire refractive-vs-non-refractive comparison, including the
abstract's headline.
**Relates to:** MF-16 (the 97-178x band this baseline feeds), MF-09 (the edit map this entry
routes into).

### What was measured

Constructed a camera, a horizontal interface, and 200 random below-interface points spanning a
range of incidence angles, with `n_air = n_water = 1.0`. Projected them through
`refractive_project_batch` (the vectorized Newton solve) and separately through
`camera.project(..., apply_distortion=True)` (the plain pinhole model). **They agree to
`rtol=0, atol=1e-12`** — tighter than the plan's floor tolerance — on every point, both through
the vectorized batch path and the scalar `refractive_project` path (spot-checked on a 10-point
subset). This is expected from the algebra (`snells_law_3d`'s `sin_t_sq = n_ratio**2 * sin_i**2`
is identically `sin_i**2` at `n_ratio=1`, i.e. `theta1 == theta2` for every incidence angle) but
had not been verified numerically before this plan — the todo said so explicitly.

**Consequence for convergence certification: the baseline's reported optimality is pessimistic,
not meaningless, and it IS converged.** The `n_water=1.0` arm's C0-but-not-C1 kink at the
refractive/pinhole boundary, which `DegenerateObservationWarning` warns makes optimality
"UNRELIABLE as a convergence measure," has **zero magnitude** on this arm specifically — the two
models it kinks between are numerically identical there. Line 268's "refraction modeling is the
sole experimental variable" framing **stands**: the arms differ only in refraction modeling, not
in solve quality.

### A boundary the todo's source-reading argument did not distinguish (found while writing the test)

`refractive_project`/`refractive_project_batch` return `None`/`NaN` for points at or above the
interface (`h_q <= 0`) **themselves** — they do not apply the pinhole continuation. That
continuation is one layer up, in `_optim_common._extend_invalid_projections`, reached only from
the production residual function (`compute_residuals`). This does not change the identity result
above (the identity is about what the *continued* residual evaluates to, and at n_ratio=1 the
Newton solve that finds the refraction point for below-interface observations is exactly the
straight-line pinhole solve) — it is recorded because a reader checking `refractive_project`
directly, rather than through the optimizer's residual path, would see un-extended NaN and could
mistake that for a disagreement.

### The degenerate observations: instrumentation gap, not a settled classification

The todo asked whether any of the 14,949 guard hits on the `n_water=1.0` arm are the
*behind-camera* kind (NaN via `_optim_common.py`'s `unextendable` path, penalized with the flat
`INVALID_PROJECTION_PENALTY_PX = 100.0` px) rather than the *above-interface* kind (extended with
a real pinhole pixel and a real gradient). **The committed artifact cannot answer this.**
`e1_benchmark_nonrefractive.json`'s `problem_shape.degenerate_observations_at_solution: 14949` is
a single merged count — `interface_estimation.py`'s guard bumps one counter
(`n_invalid` from `compute_residuals`) for both kinds without ever separating them, and no other
committed field distinguishes them. **This is an instrumentation gap, named rather than guessed
around**, per the plan's explicit instruction not to guess.

A small constructed case (not E1 itself, and not committed as a test — this is exploratory,
reported for the mechanism only) confirms both kinds exist and behave as the code says: a point
placed above the interface but still in front of the camera gets a finite pinhole-extended pixel
(`_extend_invalid_projections` returns real coordinates); a point placed behind the camera's own
image plane stays `NaN` after the extension attempt and falls to the flat penalty. Both paths are
real and reachable; the committed count cannot say how E1's 14,949 hits split between them.
**Recommended fix, out of scope for this plan:** `interface_estimation.py`'s guard could bump two
counters instead of one — this is a small, low-risk instrumentation change belonging with
HANDOFF.json's post-Zenodo repair batch, not urgent for the manuscript since it does not change
what may be claimed (see below).

### The independent tension this measurement does NOT resolve

`experiments/e1_refractive_comparison.py:42` states plainly: **"E1 carries NO accuracy claim
(D-19.3-17 demoted it)"** — only E7 survived that gate (MF-08). Yet every number in `main.tex`'s
table (L68, 268, 270, 271, 278, 280, 281, 295) is an E1 output. **This measurement does not close
that gap.** Establishing that the baseline is *converged* is a necessary condition for the
comparison to be meaningful; it is not the same as E1 having a seed-band-backed accuracy claim.
MF-16 restores a *ratio band* (97-178x, regenerable from `exp1_band.csv`) for the depth-axis
improvement specifically — that licenses stating the ratio's spread, not a general accuracy claim
for either arm's absolute numbers. Cross-referencing precisely: MF-16 licenses "the depth-axis
improvement is two orders of magnitude, 97-178x depending on seed"; it does not license "E1's
absolute error numbers are accurate" for either arm.

### The specific hazard at L271, now resolved rather than merely flagged

L271 quotes the baseline's **1.376 px** reprojection RMS as evidence of "residual systematic error
a pinhole model cannot absorb." The `DegenerateObservationWarning` states reprojection RMS
"cannot be trusted to judge convergence" for an arm with kinked residuals. **Because this arm's
kink has zero magnitude (the identity above), that disqualification does not apply here** — the
1.376 px figure is not disqualified evidence after all. The claim may still overstate what a
single RMS number can support (a separate, softer concern about interpretation, not convergence),
but the *specific* hazard the todo named — that the cited evidence is disallowed by the library's
own guard — is resolved in the baseline's favor.

### Recommended prose action

Of the todo's four options (reframe ratios as bounds; attach the MF-08/MF-16 seed band to the
abstract's ~135x; move the headline comparison onto a claim E7 can support; do nothing), the
**cheapest is now correct and sufficient**: do nothing to the convergence framing at L268 and
L271 — the baseline is converged and the cited RMS is admissible evidence. The band attachment
MF-16 already recommends (state `97-178x` alongside `~135x`, per MF-09 Group 5) remains the right
edit for the *ratio's* seed-sensitivity, independently of this entry. No new edit is required by
this finding beyond what MF-16/MF-09 already specify. Route through MF-09 (below) rather than
edited directly here.

### Recommended next (not run here)

Todo step 3 — restarting the `n=1.0` arm from the ground-truth pose to separate model
misspecification from solve-path dependence — is **not** run by this plan (out of scope,
requires an E1 run). It is now moot for the specific "is the baseline converged" question this
todo raised (settled above), but may still be of independent interest for characterizing the
non-refractive baseline's error decomposition. Routed to HANDOFF.json's deferred post-Zenodo
batch alongside the related water_z-pinned-baseline item.

---

## MF-19 — §3's real-rig numbers predate the current library and are no longer reproducible from it

**Found:** 2026-08-10, plan 21-08 (D-15 gate 1), while verifying the regenerated Zenodo archive.

### The finding

`release_calibration/diagnostics.json` — established by 19.1 as the exact source of every §3
real-rig number — is dated **2026-02-19** and was produced by a release-era library (~`v1.4.2`).
The current library does not reproduce it, from the archive **or from the original videos**.

| §3 quantity | §3 as published (Feb-19 lib) | Current library | Delta |
|---|---:|---:|---:|
| mean primary reprojection RMS (px) | 0.8786 | 0.8240 | -6.21% |
| max primary RMS (px) | 2.4079 | 2.0816 | -13.55% |
| aux `e3v8250` RMS (px) | 15.134 | 14.856 | -1.84% |
| inter-corner MAE (mm) | 0.268 | 0.258 | -3.72% |
| inter-corner RMSE (mm) | 0.674 | 0.628 | -6.81% |
| mean relative error | 0.4469% | 0.4303% | -3.72% |
| `water_z` (m) | 1.0306 | 1.0738 | **+4.20%** |
| camera heights (m) | 1.0083–1.0815 | 1.0472–1.1125 | — |
| `num_comparisons` | 7762 | **7762** | **0.00%** |

The identity of the extreme-height camera also changes (min: `e3v83e9` -> `e3v83f0`).

### This is NOT an archive defect — the decisive control

The regenerated archive was initially compared against `release_calibration/`, which varies
*both* the frame source and five months of library changes. Holding the library fixed and
varying only the frame source — the archive's image set vs `experiments/results/`'s Jul-31
**video** run (`git_sha 6c7f930`, `aquacal 1.8.0`, identical `problem_shape`):

| Quantity | Archive (images) | Experiments (video) | Delta |
|---|---:|---:|---:|
| `reprojection_rms` | 0.927660749239 | 0.927660733039 | 1e-6 % |
| `validation_3d_error_mean` | 0.000258177176 | 0.000258177176 | 0 % |
| `validation_3d_error_std` | 0.000572627835 | 0.000572627822 | 1e-6 % |

Agreement at the floating-point floor. The video->image conversion is faithful; the archive
reproduces the run. **The discrepancy is entirely library drift.**

### Mechanism

Structural proof the reference predates the current code: it carries **no `frame_rejection`,
`discard_stats` or `timings` keys at all** — those blocks did not exist when it was written.
55 commits have touched `src/aquacal/calibration/` and `src/aquacal/core/` since 2026-06-01,
including:

- `7e0cb90 fix(calibration): keep a gradient where the refractive model cannot project` —
  `compute_residuals` had substituted the **constant 100.0 px** for a failed refractive
  projection. A constant has identically zero derivative, so every clamped observation
  contributed no gradient and Stage 3 could terminate via `xtol` at a bad point.

The accuracy metrics all improve, consistent with a corrected optimizer. **`water_z`'s +4.2%
is a geometry shift, not an accuracy improvement, and should not be described as "better"
without further work** — cf. MF-12, where the line layout's failure to locate the water
surface was the finding.

### Consequence for the manuscript

§3 reports numbers the shipped library no longer produces. Two coherent resolutions, both the
user's call (open as of 2026-08-10):

1. **Update §3 to current-library numbers.** They are already computed and committed
   (`experiments/results/benchmark.json`, Jul-31). Accuracy claims strengthen slightly. Requires
   re-checking every §3 figure and any prose quoting 0.88 px / 0.268 mm / 1.03 m, via MF-09's
   edit map.
2. **State the reproduction version explicitly** — publish the archive and say §3's numbers
   correspond to `v1.4.2`. Cheaper, but ships a paper whose numbers the shipped library does not
   reproduce, which is exactly what a reader would try.

Do not widen a tolerance or edit §3 to match without deciding which of these is intended.

### RESOLVED 2026-08-11 — resolution 1, §3 updated to current-library numbers

The user chose resolution 1. Applied to `main.tex`:

| Line | Was | Now |
|---|---|---|
| 69 (abstract) | 0.674 mm RMSE, 0.45% | **0.628 mm, 0.43%** |
| 300 | mean 0.88 px, 0.54–2.41 px | **0.82 px, 0.55–2.08 px** |
| 301 | MAE 0.268 mm, RMSE 0.674 mm, 0.45% | **0.258 mm, 0.628 mm, 0.43%** |
| 302 | signed mean +0.044 mm | **+0.043 mm** |
| 303 | aux fisheye 15.1 px | **14.9 px** |

`7,762` comparisons is unchanged. Per this finding, the accuracy improvements were **not**
narrated as improvements and no new claim was added — the numbers were replaced in place.

### Open manuscript work item — the rig figure (user-owned)

`main.tex:262`, the rig figure caption, still says `z_w ≈ 1.03 m` with camera heights
1.01–1.08 m. Left alone deliberately: the figure it captions,
`figures/aquacal_zenodo_camera_rig_3d.pdf` (2026-05-05), draws the water plane at the old
`z_w`, so editing the caption alone would make caption and figure disagree.

Correct values once the figure is regenerated: `z_w ≈ 1.07 m`, heights **1.05–1.11 m**. The
extreme-height camera identities also change (`e3v83e9`/`e3v83f1` -> `e3v83f0`/`e3v83ee`).

The figure's input is current and on disk — `experiments/results/camera_parameters.csv`
(Jul-31, 1.8.0, `water_z_m = 1.0738403981732678`). The generator
`figures/aquacal/zenodo_e2e.py` named at `experiments/README.md:74` is not in the repo; the
user holds it outside the repo. Regeneration is the user's, not a task to be picked up here.

**This does not block the Zenodo publish.** It is a manuscript concern only — the archive
carries no dependency on this figure.

### Related archive-side issue (not a manuscript matter)

`reference_outputs/` in the built archive mixes two runs five months apart:
`calibration.json` from the Jul-31 experiments run, `diagnostics.json` from the Feb-19 release
run. A reader gets a close match from `aquacal compare` and a 2–14% divergence from the
tutorial's `diagnostics.json` check. Needs fixing before publish; the gate-1 run produced a
current-library `diagnostics.json` matching the shipped `calibration.json` to 1e-6%.

---

## MF-20 — Real-rig drift continues across platform, and its mechanism is detection, not the solver

**Status:** CONFIRMED by single-variable OpenCV control — extends MF-19 with a mechanism
MF-19's library-drift analysis does not cover
**Found:** 2026-08-12, second-machine re-run of E4 and E2 on 32 GB Linux; confirmed same day
**Source of truth:** `experiments/results_linux32gb/` (see `linux32gb_scope.json`), at `d27bda7`;
the OpenCV control is `experiments/results_linux32gb/e2_cv413/`
**Extends:** MF-19. **Constrains:** MF-14, MF-03.

### The finding

MF-19 established that §3's numbers predate the current library, and proved via a fixed-library
control (archive images vs Jul-31 video, both `aquacal 1.8.0`, Windows) that the archive
faithfully reproduces the run — agreement at 1e-6%, so the drift was *entirely* library drift.

Re-running the same archive on a second machine adds a third step to that sequence, and this one
is **not** attributable to aquacal's calibration code:

| §3 quantity | §3 published (~v1.4.2) | archive ref (1.8.0, Win) | this run (2.0.1, Linux) |
|---|---:|---:|---:|
| aux `e3v8250` RMS (px) | 15.134 | 14.856 | **13.970** |
| `reprojection.rms` (px) | — | 0.92766 | **0.93827** (+1.14%) |
| `reconstruction.rmse` (m) | 6.74e-04 | 6.2814e-04 | **6.7718e-04** (+7.81%) |
| `reconstruction.signed_mean` (m) | — | 4.3189e-05 | **4.7840e-05** (+10.8%) |
| `num_comparisons` | 7762 | 7762 | **7762** (0.00%) |

### The mechanism is upstream of the solver

The solver is not disagreeing — **it is handed a different observation set.** Corner observations
fell 23028 -> 22578 (-1.95%), and the loss is concentrated, not diffuse:

| camera | aux | archive ref | this run | delta |
|---|---|---:|---:|---:|
| `e3v8250` | yes | 3935 | 3587 | **-348 (-8.84%)** |
| `e3v83ef` | | 1677 | 1638 | -39 (-2.33%) |
| `e3v83ee` | | 1600 | 1569 | -31 (-1.94%) |
| `e3v82e0`, `831e`, `832e`, `8334` | | | | **0** |

### Confirmed by direct experiment (2026-08-12, same day)

The elimination argument below was superseded within hours by a **single-variable control**: the
same E2 run on the same machine in a cloned env differing *only* in OpenCV (4.13.0.92 vs
4.14.0.94 — identical numpy 2.4.6, scipy 1.17.1, Python 3.11.15, aquacal 2.0.1 off the same
working tree, same `config_paper.yaml` but `output_dir`).

**Under OpenCV 4.13, Linux reproduces the Windows reference exactly.**

| | Windows ref (4.13) | ours, 4.13 | rel | ours, 4.14 | rel |
|---|---:|---:|---:|---:|---:|
| observations, all 13 cameras | 23028 | **23028** | **0** | 22578 | -1.95% |
| aux `e3v8250` | 3935 | **3935** | **0** | 3587 | -8.84% |
| `reprojection.num_observations` | 19093 | **19093** | **0** | 18991 | 5.3e-03 |
| `reprojection.rms` | 0.927660749 | 0.927660731 | **2.0e-08** | 0.938265914 | 1.1e-02 |
| `reconstruction.rmse` | 6.28138593e-04 | 6.28138581e-04 | **1.9e-08** | 6.77175275e-04 | 7.8e-02 |
| `reconstruction.signed_mean` | 4.31890151e-05 | 4.31890137e-05 | **3.3e-08** | 4.78402956e-05 | 1.1e-01 |
| `degenerate_observations_at_solution` | 198 | **198** | **0** | 194 | 2.0e-02 |
| `water_z` | 1.07384041 | 1.07384040 | **1.1e-08** | 1.07286112 | 9.1e-04 |

Worst relative difference across **all 61** numeric diagnostics quantities: **1.264e-07**.
Artifacts: `experiments/results_linux32gb/e2_cv413/`.

**Two consequences beyond the attribution.**

1. **The 1.8.0 -> 2.0.1 and Windows -> Linux gaps are inert on real data, not just synthetic.**
   Holding OpenCV fixed, Linux / aquacal 2.0.1 / numpy 2.4.6 reproduces Windows / aquacal 1.8.0 /
   numpy 2.4.2 to 1e-07 *through the full real-rig pipeline including detection*. Previously this
   was only demonstrable on E4's synthetic cells, which never call the detector.
2. **DATA-01a's undefined tolerance stops mattering.** The eight §3 quantities that moved 1.1-10.8%
   under 4.14 reproduce at the numerical floor under 4.13. The published archive reproduces §3
   completely; the drift was never the archive and never the library.

Still open, and now purely internal to OpenCV: whether the change is `CharucoDetector` itself or
`calibrateCamera` feeding different Stage-1 intrinsics back into detection
(`detection.py:56-61`, called at `:230`). That distinction no longer affects any attribution.

**Consequence for `pyproject.toml`:** the constraint is `opencv-python>=4.6,<5.0`, which permits
both versions. Reproducing §3 requires 4.13. See the `2026-08-05-pin-opencv-below-5-0` todo.

### The original elimination argument (superseded, retained for the record)

Five points fixed the attribution before the control above was run, and between them they close
off every alternative:

1. **Not downstream rejection.** `degenerate_observations_at_solution` moved -4 and
   `pnp_attempts_total` -6, with `pnp_guard_rejected` and `pose_discarded_by_consumer` unchanged
   at 10. Rejection accounts for ~10 of the 450; the rest were never detected.
2. **Not aquacal's detection code.** `git diff 6c7f930b d27bda7 -- src/aquacal/io/detection.py`
   is **empty**, and nothing matching detect/charuco/aruco/fisheye changed anywhere in `src/`
   between the two records' commits. Despite 1.8.0 -> 2.0.1, the detection path is byte-identical.
3. **Not the 1.8.0 -> 2.0.1 gap, and not the platform.** E4's nine synthetic cells crossed the
   *same* version gap and the *same* Windows -> Linux platform change in the same session and
   reproduced final stage cost to **1e-13..1e-15** relative. That is a direct empirical control:
   whatever moved between these library versions, and whatever differs between the two platforms'
   BLAS and floating-point behaviour, is inert on the solve path at the 1e-13 level. It cannot
   produce a 1e-02 movement in E2. (E4 is synthetic and never calls the detector, so this
   controls the *solver*, not detection — which is precisely the point.)
4. **Not the video -> pre-extracted-image change.** MF-19's fixed-library control already settled
   this: archive images vs the Jul-31 video run, both `aquacal 1.8.0` on Windows, agree to
   **1e-6%**. The input is identical in practice.
5. **Not run-to-run noise.** The two Linux E2 runs differ by ~1e-09 relative on `reprojection_rms`
   — seven orders of magnitude below the ~1e-02 cross-platform drift. (E4's synthetic cells are
   *byte-identical* across repeats; only the real-data path shows even 1e-09.)

With the solver, the platform, the library gap, the frame source, and run-to-run noise all
independently controlled, **OpenCV 4.13.0 -> 4.14.0 is the only remaining candidate**;
`detection.py:64` constructs `cv2.aruco.CharucoDetector` directly, so its corner output is
entirely OpenCV's.

**Not isolated:** `detect_charuco` is also parameterized by Stage-1 intrinsics
(`detection.py:56-61`, called at `:230`), so an OpenCV change to `calibrateCamera` feeds back into
detection. Separating the detector from the intrinsics it consumes needs 4.13 and 4.14 side by
side and was **not** done. Relevant to the open `2026-08-05-pin-opencv-below-5-0` todo.

### Contrast with the synthetic cells

E4's nine synthetic cells crossed the *same* platform and version gap and reproduced to
1e-13..1e-15 relative on final cost and <=2.4e-09 on `reprojection_rms`. Synthetic scenes are
generated in-process; real data passes through an image-detection front-end whose output is
version-dependent at the ~2% observation level. **Nothing downstream of that front-end can be
tighter than it is** — which is the cleanest available statement of why synthetic reproducibility
does not transfer to real-rig reproducibility.

### Consequence for the manuscript

Any real-rig reproducibility claim must name an **OpenCV version**, and that is now the *only*
version it must name: with OpenCV pinned, the library version and the platform do not move the
numbers at all (1e-07 across 61 quantities). MF-19's "current library" column is really
"current library **with that OpenCV**" — the machine turns out not to matter.

This also removes the reason to doubt the archive. §3 is reproducible from the published bytes
today, on either platform, provided OpenCV is 4.13.

---

## MF-21 — The DEGEN-05 verdict: both fairness objections against E1 are answered in E1's favour, and the shipped `optimality` scalar now carries its caveat

**Status:** CLOSED — verdict carried forward from three measured probes; **nothing here was
re-derived** and no solve was run to write this entry
**Found:** 2026-08-17 (optimality decomposition, warm restart, FD-noise discriminator);
2026-08-17 (Huber knee). Recorded 2026-08-18, Phase 25 plan 25-05.
**Source of truth:** `.planning/probes/2026-08-17-optimality-decomposition/FINDINGS.md` (probe sha
`a7f0f25`) and `.planning/probes/2026-08-17-huber-knee/FINDINGS.md` (probe sha `054d753`)
**Opened by:** DEGEN-05, raised in `23-01-SUMMARY.md` § Evidence as an unexplained gap — E1's
non-refractive arm reported `optimality_intrinsic` = 92.78 against the refractive arm's 0.0247 on
the same scenario and seed, with no explanation on record.
**Decisions:** D-15, D-16, D-17, D-18, D-19 (`25-CONTEXT.md`)

### 1. The verdict on E1's comparison — converged, and the caveat that travels with it

**E1's non-refractive baseline is converged, so the 97–178× band is strengthened, not caveated.**
Restarting each solve from its own solution with the trust region reset (two successive restarts)
recovers essentially no cost — the largest relative drop across all four solves is **1.8e-9**
(non-refractive intrinsic pass, 15097.61231 → 15097.61228); the other three are 0, 2.6e-13 and
2.1e-12. The fairness objection raised when DEGEN-05 was opened — that an under-converged baseline
would carry larger error than its true optimum and so **inflate** the refractive-to-non-refractive
ratio — does not materialise. The one caveat that does travel with the band is that the baseline
arm is **severely ill-conditioned** (directional curvature ~3e8: cost fell 2.7e-5 over a step of
~3e-7 while the gradient fell ~90). That is a property of fitting a pinhole model to refracted
data — **expected, not a defect, and explicitly not a reason to qualify the accuracy claim.**
These two statements belong in the same paragraph and must never be separated: this project's own
Phase 23 documents already made the misreading once, taking ill-conditioning for under-convergence.

### 2. The Huber knee objection is closed by measurement, not argument

Finding 6 of the optimality probe measured that E1's `f_scale = 1.0` suits the refractive arm
(4.5% of residuals past the knee) and not the baseline (29.4–47.7% past it), so the baseline was
being fitted under a robust loss tuned to the *other* arm's residual scale. Measured at `054d753`:
re-tuning the baseline arm only, to the symmetric rule `f_scale = 3 × median|r|` (**2.8332**
interface pass, **1.8522** intrinsic pass), moves E1's z_rmse ratio by **-1.09%** at the deepest
test point (123.87× → 122.52×) and by at most 6.83% anywhere.

- **The risk direction was right; the magnitude is negligible.** The fairly-tuned baseline does fit
  slightly better (mean z_rmse **-2.12%**), so the ratio does shrink — exactly the predicted sign.
  Against a committed seed band of **97–178×** (a ~±30% spread), a 1–7% shift is an order of
  magnitude inside the noise floor and is not a distinguishable effect.
- **The attribution is validated by an in-run control.** The untouched refractive arm reproduced
  the control **bit-for-bit** (`max|abs change|` = 0.000e+00 across every refractive metric),
  confirming the patch reached only the arm it was meant to.
- **The larger movers carry no published claim.** `xy_rmse_mm` (-10.96% mean) and the baseline's
  `anisotropy_ratio` (+9.93% mean) are both non-refractive quantities. The published ~2.3
  anisotropy is the **refractive** arm's, bit-identical between runs (2.4537 at 2.5 m in both).
- One pass lands within 5% of the rule's self-consistent fixed point (2.8332 → implied 2.9601;
  1.8522 → 1.8994), so no second iteration is needed.

**The library's `f_scale` is deliberately unchanged.** Nothing measured says the symmetric rule is
better — only that the choice does not matter at the scale of E1's claim. Re-tuning the robust loss
is an estimator-design change and stays post-submission.

**Net position: both fairness objections against E1's comparison are now answered in E1's favour**
— one on convergence (warm restarts recover nothing), one on loss tuning (the knee is worth ~1% on
the headline ratio). No §3-facing number changes as a result. This is a null result, recorded so
the objections are not re-litigated.

### 3. The `optimality` caveat, and the mechanism Phase 23 documented wrongly

`optimality_stage3_interface_optimization` ships in `benchmark_grid.csv` / `benchmark_grid.tex` and
in `generalization_sweep.csv` to Zenodo. It is scipy `trf`'s `max|g · v|` with `v` the Coleman-Li
scaling vector, and it has three properties a reader must know:

1. **Volatile at a fixed solution.** 92.78 → 27.58 → **2.16** across restarts, a **43×** swing,
   while cost does not move. The genuine conditioning gap is ~2.16 vs 0.00116, not the 3751× the
   headline numbers implied.
2. **Not comparable across parameter blocks.** `v` runs three regimes here — `v = 1` for unbounded
   extrinsics and board poses, `v ≈ 700` for wide-bounded intrinsics (0.5·fx to 2·fx), `v ≈ 2e-12`
   for a pinned `water_z`. One scalar mixes all three; it is not a like-for-like maximum.
3. **Magnitude-dependent in reliability.** Large values are trustworthy — 92.78 agrees with a
   central-difference reference Jacobian to five significant figures. Small ones are not — a
   reported 0.001146 against a 3-point reference of 0.001655 is a 44% disagreement. **Differences
   between two small optimality values carry no information.** This is sharper than the existing
   "never quote optimality beyond 1 significant figure" rule and supersedes it in practice.

Finite-difference noise was tested as the driver of (1) and **falsified**: the gradient is real,
and the library's FD step rule tracked the 3-point reference in both the large- and small-gradient
regimes. No benchmark record needs re-interpreting on those grounds.

**Correction to four Phase 23 documents (Finding 1).** `23-VALIDATION.md:72-74`,
`23-RESEARCH.md:76`, `23-01-PLAN.md:103` and `23-01-SUMMARY.md:153` all state that
`optimality_intrinsic` rises *because* `water_z` is pinned against a ~2e-12-wide box. **The pinned
`water_z` contributes 0.00% of the reported optimality** (1.95e-11 of 92.78): Coleman-Li sets `v`
to the distance to the bound the negative gradient points toward, so pinning *crushes* that slot's
contribution rather than inflating it. The raw gradient on the slot is indeed large (9.75–11.57) —
that half of the intuition was right — but it never reaches the reported number, which is literally
the max **extrinsic** gradient component. **Those documents' acceptance criteria are unaffected**:
every one was phrased on recovered `water_z`, deliberately, and all still pass. Per D-18 the four
documents carry supersession headers pointing at the probe, bodies untouched, so the phase record
stays honest about what was believed when (landed at `02fe224`).

**Action taken (D-17, plan 25-05):** the caveat now ships inside the artifact the number ships in —
`OPTIMALITY_CAVEAT_TEX` in `experiments/e4_benchmark_grid.py` is emitted into `benchmark_grid.tex`
immediately before the two blocks that render the column, with a matching inline comment on
`GRID_COLUMNS` and a pointer on E6's column list. This is the FIX-04 labelling pattern (MF-17),
which is the shape the probe itself identified.

### Consequence for the manuscript

**None directly — no §3 number moves.** What this licenses is a *statement*: if a reviewer
challenges E1's comparison as unfair to the baseline, both available forms of that challenge have
been measured and closed, with sign and magnitude, and the answer is in E1's favour. Do not quote
92.78, 2.16 or the 43× swing as a result about the method — they are properties of a diagnostic
scalar, not of the calibration. Do not describe the baseline's ill-conditioning without the
converged-baseline sentence beside it.

### Forward note — the seam for anyone picking the re-tuning up later

The two passes want different `f_scale` values (2.83 interface, 1.85 intrinsic), but
`CalibrationConfig.loss_scale` (`src/aquacal/config/schema.py:335` — D-19 names the class
`PipelineConfig`; the verified name is `CalibrationConfig`) is a **single field feeding both**,
reaching `interface_estimation.py:543` and `refinement.py:356` as `f_scale` via
`pipeline.py:1025,1274`. `optimize_interface` and `joint_refinement` each take `loss_scale`
separately, so a **direct caller can differentiate the passes while the config path cannot** — any
real per-pass rule needs that seam widened. E1 currently hardcodes `1.0` at
`e1_refractive_comparison.py:755, 881, 1124`.

**Cost datum:** a full E1 single-seed run is **400 s of solver time** (refractive 88.6 + 60.1 s;
non-refractive 158.0 + 93.3 s) — the cheapest solve in the suite, useful for sizing any further E1
work.

### Why this entry has no verification criterion

By design (D-19; `25-RESEARCH.md` § What is explicitly NOT testable, item 1). There is no
measurement to schedule, no artifact to produce and no criterion to write — the convergence
question was already answered and must not be re-derived. The evidence for this entry is that it
exists and cites the two probes.

---

## MF-22 — E1's accuracy ratio is a function of detection noise, so the claim needs a stated domain (BAND-01)

**Status:** **PROVISIONAL on every magnitude; the direction is settled.** The band of record is
Phase 28's, verified in Phase 29 — **no number in this entry may be published**
**Found:** 2026-08-18, Phase 25 plan 25-08's two-seed noise probe
**Source of truth:** `.planning/probes/2026-08-18-e1-noise-axis/FINDINGS.md` and its
`exp1_band.csv` (128 rows), produced at sha `211214c`
**Affects:** any sentence quoting E1's refractive-vs-non-refractive ratio, including the
abstract's headline number

### The finding

E1's headline ratio was measured at **one** detection-noise level — the `realistic` scenario's
default of **0.5 px**. It is not a constant of the method. Across `{0.25, 0.5, 0.82, 1.2}` px the
mean ratio moves by a factor of ~5.5:

| `noise_std` (px) | non-refractive `z_rmse_mm` | refractive `z_rmse_mm` | ratio |
|---|---|---|---|
| 0.25 | 76.35 | 1.02 | 74.6× |
| 0.50 | 77.36 | 2.05 | 37.7× |
| 0.82 | 76.76 | 3.54 | 21.7× |
| 1.20 | 78.06 | 5.77 | 13.5× |

The mechanism is asymmetric and favourable to the method: **the non-refractive baseline is flat in
noise** (76.3 → 78.1 mm, ~2% — its error is model misspecification, which swamps detection noise),
while **the refractive arm scales nearly linearly** with it (1.02 → 5.77 mm). The ratio therefore
falls roughly as 1/noise. A correctly-specified model *should* be noise-limited; a misspecified one
*should* be bias-limited. That is exactly what is observed.

### What this means for the manuscript

**A ratio quoted without its noise level is not a well-defined quantity.** The stated domain
(D-14) now sits in `e1_refractive_comparison.py`'s module header and in the band provenance
`scope` string: the `realistic` scenario's single 12-camera synthetic geometry, ten seeds, eight
test depths, detection noise 0.25–1.2 px. Any §3 or abstract sentence quoting the ratio must carry
the noise level it was measured at.

### What is NOT licensed by this entry

- **No magnitude above is publishable.** Two seeds cannot separate a noise effect from seed
  variance, and the two disagree by ~50% at the extreme (93.4× vs 60.5× at 0.25 px).
- **No comparison to the published 97–178× band may be drawn from this table.** Three things
  differ at once: statistic (mean-of-means here, not the published band's construction), seed
  count (2 vs 10), and library version (see below). The 97–178× band is not restated, revised or
  challenged by this entry.
- Phase 28's four-level ten-seed run at the frozen sha, verified in Phase 29, is the **sole**
  source for anything that ships.

### A correction that travels with this entry

**D-13's `normal_fixed` isolator cannot be evaluated against the committed band.** D-13 records
that the 0.5 px row should reproduce the committed band, isolating the noise axis from FIX-02's
freed normal. It does not, and the confound is version, not noise: the committed band's provenance
is `git_sha = 3eb1f4a`, **2026-08-13**, which `git merge-base --is-ancestor` confirms **predates
FIX-01 (`fb33db4`) and FIX-02 (`57ac430`), both 2026-08-17**. At 0.5 px the non-refractive arm
differs by up to 13.22 mm (158%) while the refractive arm differs by at most 0.39 mm (21%) — a 34×
asymmetry concentrated in precisely the arm those two fixes targeted. If the isolation is still
wanted, both arms must be produced at the same sha.

The noise-axis findings above are unaffected: they are measured within a single probe — same
library, same seeds, same geometry — and are internally controlled.
