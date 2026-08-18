# Probe: what are the production rig's 198 unprojectable observations?

**Date:** 2026-08-18
**Sha:** `7118e0b` (Phase 25 waves 1-2 merged; instrumentation from plans 25-01/25-02/25-03)
**Config:** `config_paper_instrumented.yaml` · **Raw:** `degenerate_observations.csv`,
`degeneracy_classification.csv` · **Log:** `e2_instrumented.log`
**Opened requirement:** DEGEN-04 (Phase 25) · **Feeds:** D-04's gate-scope decision (criterion 2)

> ## PROVISIONAL — no number here reaches the manuscript
>
> This run settles the **mechanism**, not any published quantity. **No count in this document may
> reach `MANUSCRIPT-FINDINGS.md`, the disclosure sentence, or any §3-facing number** (D-02).
> **Phase 29's frozen table is the sole source of every number.** The run is one local
> instrumented E2 at a sha that is not the frozen sha; it exists so the gate-scope call and the
> disclosure sentence are settled *before* the freeze rather than discovered mid-run.

## Question

The production rig's calibration reports 198 observations that cannot be projected through the
refractive model at the solution. Nobody knew what they were. The manuscript needs to disclose the
count and say what it is, and the deferred degeneracy-gate scope decision for real-rig runs
(D-04) cannot be made without knowing the dominant failure kind.

## Method and its self-check

One instrumented E2 run against the archive's paper-reproduction config, differing from
`config_paper.yaml` in exactly one key (`internals.log_all_observation_depths: true`). Pinned to
**OpenCV 4.13.0** — the pin matters, 4.13 produces 198 and 4.14 produces 194 (D-01).

Wall clock **53 min** (10:40–11:33), clean exit, 3D error MAE 0.26 mm / RMSE 0.63 mm.

The classification is derived from the `nan_reason` **code** emitted at the flagging site, never
from a geometry predicate re-derived after the fact — plan 25-03's classifier contains no `h_q`
comparison, and its unit test pins two rows at an identical positive `h_q_m = 0.37` with different
codes and asserts different buckets, so a geometry-derived classifier cannot pass it.

**Self-check — two independent counters agree.** The per-observation sidecar (plan 25-01/25-02,
new in this phase) holds 198 rows. Phase 24's aggregate counter, computed by separate code on the
same run, reports `degenerate_observations_cause_above_interface__stage3_intrinsic_pass = 198`.
The sidecar's own `n_flagged_at_stage` stamp reads 198 with `truncated = false`, so the table is
complete and no row-cap truncation occurred. Row count, aggregate stamp, and Phase 24's
independent counter are the same number.

## Result

**All 198 are one bucket.**

| Bucket | `nan_reason` | Count | Share |
|---|---|---|---|
| `above_interface` | 2 | **198** | **100%** |
| `interface_below_camera` | 1 | 0 | — |
| `camera_model_failure` | 3 | 0 | — |

Split by stage — there is **no cross-stage double counting** here:

| Stage | Observations evaluated | Flagged | Fate |
|---|---|---|---|
| `stage3_interface_optimization` | 73,975 | **0** | — |
| `stage3_intrinsic_pass` | 73,975 | **198** | 198 extended, 0 penalized |

198 / 73,975 = **0.27%** of the observations evaluated at that stage.

Geometry of the flagged rows (`h_q_m` is the corner's height relative to the water surface;
negative means **above** it):

| | mean | min | median | max |
|---|---|---|---|---|
| `h_q_m` (m) | −0.0218 | −0.0640 | −0.0183 | −0.0013 |
| `h_c_m` (m) | 1.0785 | 1.0472 | 1.0763 | 1.1125 |
| `chord_incidence_deg` | 15.41 | 2.80 | 14.86 | 29.82 |

They are **not** scattered across the dataset. 8 cameras, 8 frames, 23 corner ids, clustering into
two short bursts:

| Frame | Rows | Cameras | `h_q_m` range (m) |
|---|---|---|---|
| 22 | 35 | 5 | −0.0640 … −0.0019 |
| 23 | 29 | 4 | −0.0567 … −0.0016 |
| 24 | 23 | 4 | −0.0395 … −0.0023 |
| 25 | 19 | 4 | −0.0411 … −0.0060 |
| 26 | 10 | 4 | −0.0194 … −0.0046 |
| 102 | 20 | 5 | −0.0239 … −0.0013 |
| 104 | 49 | 5 | −0.0445 … −0.0055 |
| 105 | 13 | 4 | −0.0128 … −0.0031 |

## Findings

1. **The 198 are board corners physically above the water surface, not a solver failure.** Every
   flagged row carries `nan_reason = 2` (`above_interface`) and a negative `h_q_m` — the corner
   sits 1.3 mm to 64 mm *above* the interface, where there is no water to refract through and the
   refractive projection is undefined by construction. Nothing here indicates a numerical problem,
   a conditioning problem, or a bug.

2. **It is a data-acquisition artifact confined to two moments.** All 198 come from 8 of the run's
   frames in two contiguous bursts (22–26 and 102–105) — the calibration board was breaking the
   surface, or sitting within centimetres of it, on two passes. The depth magnitudes are
   millimetric to centimetric, consistent with the board riding at the surface rather than being
   grossly mispositioned.

3. **They occur only in the intrinsic pass, and every one was extended, not penalized.** Zero
   observations were flagged during `stage3_interface_optimization`; all 198 appear in
   `stage3_intrinsic_pass`, and all 198 took the `extended` fate. The count is therefore a
   *distinct* count from one stage, not a cross-stage sum — the double-counting caveat that
   applies to a stage-agnostic `len()` over the sidecar does not apply to this run.

4. **The bucket that dominates is the one the pre-registered expectation named**, and the other
   two buckets are empty — not merely small. There is no mixed population to disentangle and no
   residual "unknown" category.

## Net position

The mechanism is settled: **the production rig's unprojectable observations are corners above the
water surface during two board passes near the interface, 0.27% of the observations evaluated at
the affected stage, all extended rather than penalized.** The manuscript can disclose the count and
say what it is in one sentence, without hedging about an unknown cause.

For D-04's gate-scope decision, the input this probe was run to produce: the dominant — here,
*sole* — bucket is a **data-geometry condition, not a solver pathology**, it is confined to
identifiable frames, and it does not indicate the calibration is unsound. A gate that fails a
real-rig run on a nonzero count would fail this run, which produced 0.26 mm MAE.

**Every number above is provisional.** Phase 29's frozen table is the sole source for anything
that ships.

---

## What was kept, and what was not

Committed here: `FINDINGS.md`, `degenerate_observations.csv` (26 KB, the run's own sidecar),
`degeneracy_classification.csv` (the provisional classified table with its in-body provenance
stamp), `config_paper_instrumented.yaml` (the exact config consumed), `e2_instrumented.log`,
`real_rig_metrics.json`, `camera_parameters.csv`.

**`all_observation_depths.csv` was left in the archive cache** at
`aquacal_data/real-rig/real-rig/output/all_observation_depths.csv` — it is **11 MB**, which is over
the plan's "a few MB" threshold for committing raw probe data, and nothing in this finding depends
on it: the classification is derived entirely from the 198-row sidecar, and the full-population
depth table exists only as the D-09 flag's proof-of-life. It is regenerable by re-running the same
config. The archive itself is not in git, so the file is untracked where it sits.

`benchmark.json` is also left untracked, for a different reason: the repo's `detect-secrets`
pre-commit hook flags its `git_sha` field (`7118e0b...`) as a hex high-entropy string. That is a
false positive, but the correct response is neither to edit a generated artifact nor to bypass the
hook, so the file stays untracked in the probe directory. Its `git_sha` incidentally confirms the
run's provenance is intact: it equals the launch sha exactly, so no commit landed mid-run. Every
number this finding quotes from it is reproduced in the tables above.

Three further calibration outputs (`calibration.json` 2.2 MB, `reprojection_residuals.csv` 1.3 MB,
`reconstruction_errors.csv` 626 KB) are likewise left untracked in the probe directory — they are
ordinary E2 outputs, not evidence for this finding, and Phase 29's frozen run regenerates them.
