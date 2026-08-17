# Phase 23 pre-planning recon — findings

**Date:** 2026-08-15 · **Status:** scratch, nothing committed, no tracked file modified
**Scope:** read-only measurement and search, run while the author was away, to turn open
questions in the FIX todos into facts before phase 23 is planned.

`git status` was clean at start and verified unchanged after every command that ran code.

---

## F-1 — No design rationale exists for E7 running tilt-fixed. FIX-02's check is discharged.

FIX-02 asks: *"check MF-05 and the 19.2/19.5 plans for a recorded rationale, not to reverse the
decision but so that if one exists it is answered rather than silently overridden."*

**Searched:** every `normal_fixed` occurrence across `.planning/phases/19.2-*/` and
`19.5-*/` (28 files), plus MF-05 in `MANUSCRIPT-FINDINGS.md`.

**Result: no scientific/design rationale exists.** Exactly one rationale is recorded anywhere,
and it is about provenance, not about the ablation:

> `19.2-01-SUMMARY.md:105` — "Kept `normal_fixed`'s default at `True` (matching
> `optimize_interface`/`joint_refinement`'s own library defaults) rather than flipping any
> default, **so every already-committed Phase-19.1 record (E1, E7) stays bit-identical and is
> never re-run** — appending it last in the signature was the mechanism that made this a
> zero-signature-break change."

**This rationale is answered, not overridden.** Its entire purpose was to avoid invalidating
committed artifacts. The v2.1 re-run replaces every artifact by design, so the premise is gone —
the same structure as FIX-01's `HANDOFF.json:119` deferral, which was overridden for the same
reason.

Every *other* planning document treats `normal_fixed=False` as the correct configuration and
treats the `True` default as a hazard:

- `19.2-07-PLAN.md:65` (review finding **H1**) — "Every cell passes `normal_fixed=False` …
  omitting it silently solves a problem two tilt DOF smaller and nothing in the committed record
  would reveal it." Passing it is called **MANDATORY**.
- `19.2-05-PLAN.md:396` — "`normal_fixed=False` on every row is **load-bearing, not incidental**.
  'tilt' in `tab:cpr` means tilt-ENABLED, which is also `CalibrationConfig.interface_normal_fixed`'s
  default and therefore what E2's real-rig run produced. A row built at `normal_fixed=True` would
  report a `P` exactly 2 smaller" — i.e. *a wrong number that looks right*.

MF-05 concerns the shared-vs-per-camera claim and says nothing about tilt.

**Conclusion for planning:** E1 and E7 were omissions, precisely as FIX-02 states. No rationale
needs answering in the artifact. Cite `19.2-01-SUMMARY.md:105` in the plan so the decision record
shows the question was asked and closed.

---

## F-2 — FIX-02's "unrecoverable from their artifacts" claim is verified, and the omission is
## *invisible* because the neighbouring key IS recorded

| record | `solver_config` keys | `normal_fixed` recorded? |
|---|---|---|
| `e4_cells/*/benchmark.json` | `n_air, n_water, **normal_fixed**, refine_intrinsics, seed, shared_interface` | **yes** |
| `e1_benchmark_refractive.json` | `ftol, gtol, loss_scale, n_air, n_water, refine_intrinsics, robust_loss, **shared_interface**, xtol` | **no** |
| `e1_benchmark_nonrefractive.json` | same as above | **no** |
| `e1_seed_band_provenance.json` | `seeds` | **no** |
| `e7_seed_band_provenance.json` | `seeds` | **no** |

`normal_fixed` appears nowhere in any of the four E1/E7 records (whole-file string search, not
just `solver_config`).

**The sharp part:** E1/E7 *do* record `shared_interface` — the other interface-model flag. A
reader seeing `shared_interface` present and `normal_fixed` absent would reasonably infer the
latter was considered and deemed inapplicable. It was not; it was never passed. That is why this
survived a targeted audit (V-006 checked E4 only).

---

## F-3 — E4's `--check` is structurally incapable of passing, and it is *also* on FIX-05's
## defective path

Ran `python -m experiments.e4_benchmark_grid --check` (fast, seconds; `git status` verified
unchanged — it does not write, as documented).

**Result: `9 cell(s) mismatched`.** Enumerated every column by hand
(`scratchpad/e4_check_detail.py`, 35 columns × 10 rows):

```
MISMATCHING COLUMNS: ['exit_code', 'status_reason']

### exit_code       (9/10 rows)   committed=0.0   fresh=None
### status_reason  (10/10 rows)   committed=NaN   fresh=''
```

**All 33 metric/numeric columns reproduce to 1e-6. The aggregation is sound.** Both failures are
harness artifacts that cannot ever clear:

- `exit_code` — `_run_check` hardcodes `"exit_code": None` (`e4_benchmark_grid.py:1872`) because
  no subprocess is spawned, while the committed CSV holds `0.0` from the real run. This can never
  match by construction.
- `status_reason` — empty-string vs `NaN` round-trip through CSV.

### Two consequences for phase 23

1. **FIX-05's stated test strategy needs a caveat it doesn't carry.** The todo says to test with
   `--check` (correctly — it's seconds, versus 3.15 h for the grid). But `--check` is **red on the
   committed tree today**, so a naive before/after gives red→red and would mask a real regression.
   The plan must either exclude these two columns from the comparison or fix the harness, and must
   record the current red baseline so "still red" is not read as "no change".
2. **`_run_check` is itself on the defective path.** Line 1876 calls
   `build_grid_dataframe(out_dir, cell_statuses, E2_BENCHMARK_PATH)` — the module-level constant
   FIX-05 exists to remove. So `--check --out <dir>` reproduces the very defect FIX-05 fixes.
   **FIX-05's fix must cover `_run_check`, not just the main run path.** The todo names only
   `:226` and does not mention `_run_check`.

The real-rig row (`real_rig_13cam_200fr`) is present in both frames on the default out dir,
consistent with FIX-05's account that the defect manifests only under `--out`.

---

## F-4 — FIX-06 has at least four stale sites, not three, and the unnamed one is the worst

FIX-06 names `e2_real_rig.py:850` (help), `e2_real_rig.py:289` (provenance), `synthetic.py:184`
(WATER_Z). It also instructs: *"Check the surrounding module docstring and any
19.1-E2-FRAMESET-PROVENANCE.md references for the same stale claim."* Doing so:

**Site 4 — `e2_real_rig.py:555-563`, a code comment, NOT named in the todo.** It is the same
retired claim in its most detailed and most wrong form, carrying concrete false frame counts:

> "The PUBLISHED Zenodo archive is a ~4.3x frame-subsampled extraction of the capture that
> produced the manuscript's section-3 numbers (60 usable frames -> 12 validation -> 1,817
> comparisons, versus ~260 -> 52 -> 7,762)."

Verified 2026-08-12 against record `21889922`: the archive ships **262** extrinsic frames →
210/52 split → 200 calibration frames, reproducing `num_comparisons = 7762`. So the parenthetical
is false in both halves. This comment sits directly above the `--config` branch it justifies.

**Site 5 — `19.1-E2-FRAMESET-PROVENANCE.md:35-48, 81`,** which site 4 cites as its authority.
Lines 36-37 tabulate the 192 MB / 60-frame / 1,817-comparison archive and line 45 states the
"~4.3× frame-subsampled" conclusion with a ratio check at line 48. As a *historical* record of
what was true at phase 19.1 this is correct and should not be rewritten — but it is the cited
authority for a now-false claim, so it needs a supersession header pointing at `25655f7`
(the manifest repoint) rather than a silent edit.

**Site 6 (judgment call, low priority) — `docs/tutorials/03_cli_walkthrough.md:33`** describes
`config_paper.yaml` as "frame_step: 1 over pre-subsampled frames". The surrounding tutorial is
otherwise correct for the new archive (262 frames, reproduces §3). "Pre-subsampled" is defensible
(frames were extracted from video) but reads as an echo of the retired claim. Flagging, not
asserting — the author should decide.

**Grep evidence:** `subsampl` across `src/ experiments/ docs/` returns only the two
`e2_real_rig.py` sites plus legitimate uses (`pipeline.py:_subsample_detections`,
`schema.py:250`, `images.py:211`, `e4_benchmark_grid.py:10`, `README.md:138`, and the tutorial's
correct description of `config_quickstart_not_paper.yaml`). The retired record id `18645385`
appears nowhere in tracked source. So four is the complete set in code; site 5 is in planning.

---

## F-5 — E1 has no solve caching, so FIX-01/FIX-02 carry no stale-result hazard

E6 keys scenario identity on `normal_fixed` (`_SCENARIO_IDENTITY_KEYS`, `19.5-06-PLAN.md:88`) and
checkpoints per configuration, so changing the flag correctly invalidates its cache. **E1 has no
equivalent** — `--force` in `e1_refractive_comparison.py` governs file overwrite only, never solve
reuse. Adding `normal_fixed` to E1 cannot silently reuse a stale solve.

---

## F-6 — The FIX-01 / FIX-02 interaction (probe running; see PROBE RESULT below)

**Correction to my own earlier framing.** I initially told the author that freeing the normal
might add null directions to E1's non-refractive arm "for the same reason" `water_z` is null at
unit index. That analogy is **not exact**, and the difference matters:

- `water_z` at n=1.0 is a **pointwise** null direction: change it alone, holding everything else,
  and the cost is unchanged to 13 significant figures. That is what the committed measurement
  shows.
- `normal_fixed=False` does **not** add an interface parameter. It frees the *reference camera's*
  `rx, ry` (`_optim_common.py:218-223`: `R_ref = rvec_to_matrix([rx, ry, 0])`, `t = 0`), leaving
  `interface_normal` fixed at `[0,0,-1]`. Rotating the reference camera alone *does* change its
  own projections, so it is **not** pointwise-null even at n=1.0.

The real concern is therefore **gauge**, not pointwise nullity: at n=1.0 the interface is
irrelevant to projection, so the rig's absolute orientation relative to world Z is unobservable —
it can be absorbed by a compensating rotation of the other cameras and every board pose. Freeing
`rx, ry` there adds 2 gauge DOF to an arm that FIX-01 is simultaneously de-rank-deficiencying.
Whether that re-trips the projection guard is an **empirical** question, not an analytic one,
which is why it needs a solve rather than a sweep.

**Probe design** (`scratchpad/probe_normal_fixed.py`, mirrors `_run_one_model` exactly, adds
`normal_fixed` as the only knob, seed 42, `realistic` scenario, `refine_intrinsics=True`):

| arm | n_water | normal_fixed | purpose |
|---|---|---|---|
| A | 1.0 | True | reproduce the committed baseline — validates the harness |
| B | 1.0 | False | **FIX-02 alone on the non-refractive arm — the open question** |
| C | 1.333 | False | refractive control — FIX-02's effect on the arm that carries the claim |

Committed baseline for arm A: `degenerate_observations_at_solution = 14,949`, optimality ~9e+02.
If arm A does not reproduce that, the probe is wrong and B/C mean nothing — check A first.

**What the probe cannot answer:** the combination FIX-01 + FIX-02 (water_z pinned *and* normal
free), because pinning `water_z` is FIX-01's implementation work and does not exist yet. If arm B
shows the guard count climbing, the plan must sequence FIX-01 and FIX-02 together and re-measure
the pair — they cannot be planned as independent single-file edits.

### PROBE RESULT — my hypothesis was WRONG, and the truth is more dangerous

| metric | A: n=1.0, `normal_fixed=True` | B: n=1.0, `normal_fixed=False` |
|---|---|---|
| `degenerate_observations_at_solution` | **14,949** | **0** |
| `cost_interface` | 26067.020583**52** | 26067.020584**82** |
| `cost_intrinsic` | 15097.62107**9** | 15097.61228**9** |
| `optimality_interface` | 3.96e-03 | 7.28e+00 |
| `optimality_intrinsic` | 873.98 | 49.65 |
| **`water_z` estimate** (GT = **1.031 m**) | **1.990 m** | **0.0120 m** |
| termination | `xtol`, 38 f-evals | `ftol`, 26 f-evals |
| elapsed | 190 s | 138 s |

**Arm A validates the harness:** 14,949 degenerate observations exactly, and optimality 873.98 ≈
the "9e+02" in `MANUSCRIPT-FINDINGS.md`. The probe reproduces the committed baseline.

**Arm B does not fight FIX-01 — it independently zeroes the guard count.** But it does so
*without fixing anything*, and that is the finding:

- `water_z` lands at **0.0120 m** against a ground truth of **1.031 m** — off by 1.02 m.
- The interface-stage cost is **identical to arm A to 10 significant figures** (26067.020583 vs
  26067.020584). This independently re-derives the null-direction result: `water_z` is free to go
  anywhere and the fit does not notice.
- The guard cleared for a purely geometric reason. The guard counts observations on the wrong
  side of the interface. At `water_z = 1.99 m` the surface sits *above* much of the target volume,
  so 14,949 observations read as "in air" → flagged. At `water_z = 0.012 m` the surface sits just
  below the cameras, so everything is trivially underwater → nothing flagged. **Both estimates are
  badly wrong; only one of them trips the counter.**

### Why this matters more than the interaction I was worried about

**FIX-01's acceptance test becomes vacuous once FIX-02 lands in the same phase.** FIX-01 says:

> "Expect the arm's `degenerate_observations_at_solution` to read 0 afterwards. **That is the
> check.**"

Arm B shows that check passing with `water_z` off by a metre and nothing pinned. If FIX-02 lands
first — or if both land and the implementer verifies with the stated criterion — **the phase can
report FIX-01 as verified when it was never implemented**, or conclude FIX-01 is unnecessary
because "the count is already zero."

FIX-01 anticipated exactly this failure mode in prose and then specified the criterion that walks
into it:

> "Do not treat the guard count going to zero as the goal in itself. The goal is not estimating a
> parameter that cannot be estimated; zero is the symptom clearing."

Arm B is that sentence, measured.

### Recommended change to the plan (author's call)

1. **Replace FIX-01's acceptance criterion.** Guard count is a *necessary* signal, not a
   sufficient one. The criterion that actually tests the pin is the recovered `water_z` itself:
   pinned, it is exactly `WATER_Z = 1.031 m` by construction. Suggest asserting the estimate
   equals ground truth (the pin makes this trivially true and therefore a real check that the pin
   is wired), **plus** guard count 0, **plus** the reconstruction numbers reproducing to ~4
   significant figures as the committed measurement predicts.
2. **Sequence FIX-01 and FIX-02 together for E1's non-refractive arm, and measure the pair.** The
   combination (water_z pinned *and* normal free) is still unmeasured — it is the configuration
   the re-run will actually use, and no probe covers it because pinning does not exist yet.
3. **Do not let "guard count 0" appear as a standalone success criterion anywhere** in the phase,
   including in the driver's completeness gate.

**Optimality is not a usable tiebreaker here.** It moves in opposite directions across the two
stages (interface 3.96e-03 → 7.28; intrinsic 874 → 49.7), which is consistent with the project's
existing knowledge that a hinged/flat residual makes `optimality` unreliable as a convergence
signal.

### Arm C — the refractive control is clean, and FIX-02 is safe for the arm that carries the claim

| metric | A: n=1.0 fixed | B: n=1.0 free | **C: n=1.333 free** |
|---|---|---|---|
| degenerate observations | 14,949 | 0 | **0** |
| `cost_interface` | 26067.02 | 26067.02 | **3688.80** |
| `optimality_interface` | 3.96e-03 | 7.28e+00 | **1.15e-03** |
| `optimality_intrinsic` | 873.98 | 49.65 | **0.0247** |
| `water_z` (GT 1.031 m) | 1.990 m | 0.0120 m | **1.02357 m → −7.43 mm** |

**The control is not blind, and it is well-conditioned.** With the normal free at n=1.333,
`water_z` is recovered to **−7.43 mm** of ground truth and optimality is 1.15e-03 / 0.0247 —
one to four orders of magnitude better than either non-refractive arm. Cost is 7× lower, as it
should be when the model matches the data.

This is the positive half of the picture: `water_z` is genuinely observable under refraction (as
`MANUSCRIPT-FINDINGS.md:972` insists), and freeing the interface normal does not destabilise the
arm E1's accuracy claim rests on. **FIX-02 is safe for the refractive arm on this evidence.**

It also re-proves the probe's validity by the same logic the original `water_z` sweep used: the
n=1.333 control *moves* where the n=1.0 arm does not.

**Not measured, and the one thing still open:** FIX-01 + FIX-02 together (pinned `water_z`, free
normal) at n=1.0 — the configuration the re-run will actually use. Pinning is FIX-01's
implementation work and does not exist yet, so no probe can reach it. **Measure it as part of
FIX-01's plan, not after.**

---

## F-7 — FIX-03 is smaller than written: the layout axis ALREADY runs at six seeds

FIX-03 instructs: *"Run the layout axis at all six seeds (42–47), not seed 43 alone. Inside a full
sweep the extra five cost almost nothing."*

**The committed band already has all six.** `generalization_sweep_band.csv` (102 rows):

```
axis      n_seeds  seeds
cameras      6     [42, 43, 44, 45, 46, 47]
index        6     [42, 43, 44, 45, 46, 47]
layout       6     [42, 43, 44, 45, 46, 47]     <-- including layout
scale        6     [42, 43, 44, 45, 46, 47]
```

What was seed-43-only was **MF-12's hand analysis**, not the sweep. So FIX-03's seed-coverage
sub-item is already satisfied; what is missing is the *per-camera decomposition* at those seeds.
The stated cost ("the extra five cost almost nothing") is already paid. Net: FIX-03 is a
column/artifact addition, not a re-scoping of the axis.

**The seed-43 `line` mechanism reproduces from committed data**, confirming FIX-03's premise:

| | value |
|---|---|
| `water_z_error_mm_mean` (line, seed 43) | 18.854672 |
| `z_position_error_mm_mean` (line, seed 43) | −18.495458 |
| difference | **0.359214** |

FIX-03 states this difference is "0.3600 mm, matching MF-12's reported `h_c` signed mean to the
digit." The exact committed value is **0.3592**, not 0.3600. Both round to 0.36, so the claim
survives — but the implementer should be told the exact figure so nobody chases a 0.0008 mm
phantom while trying to reproduce "to the digit."

**Confirmed:** the band carries only `_mean` aggregates and no per-camera columns
(`per-camera columns: ['n_cameras']` only), so the per-camera table really is a new artifact, as
FIX-03 says.

---

## F-8 — DEGEN-01's scope is slightly wrong: E6 *does* persist the degeneracy column

Checked every committed CSV in `experiments/results/` for
`degenerate_observations_at_solution`:

| persists it | does NOT persist it |
|---|---|
| `benchmark_grid.csv` (E4) | `exp1_band.csv`, `exp1_parameter_band.csv`, `exp1_parameter_errors.csv` (E1) |
| `benchmark_grid_repeat.csv` (E4) | `exp2_depth_generalization.csv`, `exp3_xy_vs_z_anisotropy.csv` |
| `generalization_sweep.csv` (E6) | `index_sensitivity.csv`, `index_sensitivity_seed_band.csv` (E5) |
| `generalization_sweep_band.csv` (E6) | `interface_ablation.csv`, `interface_ablation_band.csv` (E7) |
| | `e7_focal_standoff.csv`, `e7_trace_*.csv` (E7) |

DEGEN-01 says the counter is "not persisted at all by E5 **or the band runs**." True for E5, E1
and E7 — **false for E6's band**, which persists it in all 102 rows (all zero). Phase 24 should
narrow the claim rather than re-implement something E6 already has.

**Where E1's 14,949 actually lives:** `e1_benchmark_nonrefractive.json` →
`problem_shape.degenerate_observations_at_solution = 14949` (and `= 0` in the refractive record).
It is in **no CSV at all**. FIX-01's implementer needs that path to verify the fix.

---

## F-9 — The E2 sanity control has an empirically measured tolerance, and a seed caveat

The Phase 29 criterion added on 2026-08-15 says E2 should reproduce to ~1e-8, citing F-001's
Windows→Linux span. That is independently confirmed on a §3 quantity:

| run | `mean_per_camera_reprojection_px` |
|---|---|
| `results/` (Windows, seed 42) | 0.8240385366779744 |
| `results_linux32gb/e2_cv413/` (Linux, OpenCV 4.13) | 0.8240385336120196 |
| | **abs diff 3.07e-09 · rel diff 3.72e-09** |

**Caveat that must go into the criterion:** this tolerance holds only for the *same seed and same
config*. The E2 seed band is four orders of magnitude wider:

| run | value |
|---|---|
| `results_e2_band/seed_42_e2_out/` | 0.8240385366779744 |
| `results_e2_band/seed_43_e2_out/` | 0.7610308525600887 |
| `results_e2_band/seed_44_e2_out/` | 0.9103471711816913 |

So the control is "seed 42 vs seed 42 at ~1e-8", never "the new run vs any committed E2 number."
Comparing across seeds would show ~0.07 px of movement and look like a broken run.

(`results_linux32gb/e2_memory` and `e2_timing` sit at 0.8244381 — 4e-4 away, a different
configuration. They are not the control either.)

---

## F-10 — FIX-04 and FIX-06 premises verified exactly; FIX-04 has a ready-made home

**FIX-04** — `e7_focal_standoff.csv` reads exactly as described:

```
arm                 n_seeds  mean_within_seed_corr  n_neg  n_pos  p_one_sided  verdict
percamera_fixed        10           NaN               0      0      1.000000   no_signature
percamera_refined      10           0.437056          1      9      0.010742   signature_present
shared_fixed           10           NaN               0      0      1.000000   no_signature
shared_refined         10           0.955956          0     10      0.000977   signature_present
```

The mechanism is visible one level down: in `interface_ablation_band.csv` the `fixed` arms have
`focal_drift_pct = 0.0` **exactly**, for every camera and seed. Variance is identically zero, so
the correlation is undefined, not null.

**Implementation note the todo doesn't give:** the CSV already carries a long free-text `scope`
column. FIX-04's requirement to "say why in the same row, so the CSV is self-explaining" has a
natural home there, alongside the new verdict string — no new prose column strictly needed.

**Also note:** this file is a *re-analysis* of `interface_ablation_band.csv` (D-19.5-05), not a
re-run. So FIX-02 moving E7's band values propagates here automatically. **`shared_refined`'s
`n_seeds_positive = 10, p = 0.000977` is the exact published result the new Phase 29 before/after
check must watch.**

**FIX-06 site 2** — confirmed. `experiments/results/real_rig_metrics.json` holds
`mean_per_camera_reprojection_px = 0.8240385366779744` while its own provenance string says
*"(release diagnostics.json: 0.8786 px, quoted as 0.88)"*. The 0.8786 value is real but belongs to
`experiments/archive/e2-2026-07-30-pre-pnp-guard/`, i.e. it is the pre-PnP-guard number. Superseded,
exactly as the todo says.

---

## F-11 — FIX-02 breaks no existing test, and the test it asks for genuinely does not exist

Searched every test touching `normal_fixed`:

- `tests/unit/test_datasets_pipelines.py:311` `test_normal_fixed_default_unchanged` — asserts
  omitting == passing `True` at the **library** level. FIX-02 changes **experiment call sites**,
  not library defaults (which are explicitly deferred to post-submission), so this stays valid.
- `tests/unit/test_datasets_pipelines.py:341` `test_normal_fixed_false_changes_problem_size` —
  asserts `n_params` is exactly +2 at `normal_fixed=False`. Stays valid, and usefully documents
  the two DOF.
- `tests/synthetic/test_guard_inertness.py` already parametrizes over **both** `normal_fixed`
  values, so the projection guard is covered at `False`.

**No test asserts that each experiment passes `normal_fixed` explicitly** — the test FIX-02 asks
for is a genuine gap, and the cheapest recurrence-preventer in the phase.

---

## What this changes about phase 23's shape

The roadmap describes phase 23 as *"six independent single-file fixes"*. Three findings above
push against "independent":

- **FIX-01 and FIX-02 both change E1's non-refractive arm** and may interact (F-6, pending).
- **FIX-05 is two call sites, not one** — the main path and `_run_check` (F-3).
- **FIX-06 is four-to-six sites across two trees, not three strings** (F-4), and one of them is a
  planning document needing a supersession header rather than an edit.

None of this changes the phase boundary. It changes the plan decomposition inside it.
