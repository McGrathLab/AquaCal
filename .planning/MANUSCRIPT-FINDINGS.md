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

**Status:** RESOLVED (2026-08-01, phase 19.2 plan 19.2-25) — the provenance caveat is closed;
a prose edit is still needed, and the required framing has changed (see below)
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

The supplement says the Newton solve for the refraction point converges in **"two to four
steps."** Measured over the real rig's full working volume (104,052 points, 12 cameras), both
loops, from `newton_iterations.csv`'s pooled `ALL` rows:

| quantity | scalar | batch |
|---|---|---|
| iterations, min | 2 | 2 |
| iterations, **median** | **4.0** (identical on every camera) | **4.0** (identical on every camera) |
| iterations, **max** | **7** (6-7 per camera) | **7** (6-7 per camera) |
| not converged | **0** | **0** |
| incidence angle range | 0.13 deg - 62.92 deg | 0.13 deg - 62.92 deg |
| max residual | ~1.0e-9 m (at tolerance) | ~1.0e-9 m (at tolerance) |

The two loops' *per-point* convergence-iteration distributions are effectively identical (the
tiny residual differences, e.g. `9.989e-10` vs `9.999e-10`, are the two implementations' own
arithmetic, not a scope difference) — each point still takes the same number of Newton steps to
reach its own root regardless of which loop finds it.

**The median/max framing must be restated against the batch loop's actual termination rule, and
this SHARPENS the entry's original conclusion rather than replacing it.** The per-point
iteration counts above describe *when each point's own delta would cross tolerance if it
terminated independently* — but the production batch loop does not terminate per point: it
runs `np.all(np.abs(delta) < tolerance)`, so **every point in a batch keeps iterating until the
slowest point in that batch converges.** A point whose own root would be found in 2 steps still
pays for however many steps the batch's hardest point needs, up to the measured max of 7. So the
production **per-point cost is the batch's max, not its median** — a reader sizing a compute
budget from "typically four steps" would under-provision by nearly 2x, not merely fail to see an
occasional tail case. This is stronger than the original entry's "misses that the distribution
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
7 steps over the calibrated volume (individual points would converge in as few as 2, median 4,
if evaluated independently)" — rather than "typically four steps." The batch's own median/max
are worth reporting as characterizing the *individual* root-find difficulty, but they no longer
describe the batch's *per-point wall-clock cost*, which the all-points termination rule
equalizes upward toward the tail.

**Do not** silently change the number to 7 as if it were now "the" iteration count. The
per-point root-find genuinely converges in a median of 4 steps; what changed is which quantity
that number describes. Quoting 7 without the batch-termination explanation above would overstate
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
