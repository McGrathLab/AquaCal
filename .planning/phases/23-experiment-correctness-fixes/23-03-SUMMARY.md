---
phase: 23-experiment-correctness-fixes
plan: 03
subsystem: experiments
tags: [e6, e7, gauge-correction, reporting, provenance]

# Dependency graph
requires: []
provides:
  - "E6's water_z_error_mm_signed_mean and z_position_error_mm_gauge_corrected_mean aggregate columns"
  - "E6's per-camera decomposition table (generalization_sweep_per_camera[.csv|_band.csv])"
  - "E7's vacuous_by_construction verdict distinguishing an undefined statistic from a measured null"
  - "the reproducible derivation recipe for MF-12's four quantities"
affects: [26-full-suite-driver, 28-suite-execution, 30-post-submission-reconciliation]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "*_out sink idiom (per_camera_rows_out) extended to E6's run_configuration/run_sweep"
    - "checkpoint schema_version bump with a warned, non-raising fallback for older checkpoints"

key-files:
  created: []
  modified:
    - experiments/e6_generalization_sweep.py
    - experiments/e7_focal_standoff_analysis.py
    - tests/unit/test_experiments_e6.py
    - tests/unit/test_e7_focal_standoff.py

key-decisions:
  - "FIX-03 and FIX-04 shipped as two separate commits (D-14), FIX-03 before FIX-04, so either can be bisected out"
  - "compute_per_camera_errors' gauge_correct_z=False default is untouched; E6's call site opts in with a second call"
  - "Every camera (including cam0/cam1) is emitted in the per-camera table; the cam0/cam1 exclusion is a reader-side filter, not baked into the artifact"
  - "vacuous_by_construction requires THREE conditions (n_seeds >= 2, zero signs, undefined correlation) so a genuinely null measured result cannot be misclassified"

patterns-established:
  - "New aggregate/table columns are always appended, never inserted, so old artifacts stay comparable"

requirements-completed: [FIX-03, FIX-04]

# Metrics
duration: ~70min
completed: 2026-08-17
---

# Phase 23 Plan 03: E6/E7 Reporting and Labelling Fixes Summary

**E6 now reports signed and gauge-corrected water_z/Z-position error plus a per-camera h_c decomposition table; E7's two `fixed` rows now read `vacuous_by_construction` instead of a measured `no_signature`.**

## Performance

- **Duration:** ~70 min
- **Started:** 2026-08-17T13:00:00Z (approx.)
- **Completed:** 2026-08-17T14:04:42Z
- **Tasks:** 3
- **Files modified:** 4 (2 source, 2 test)

## Accomplishments

- FIX-03: `E6_COLUMNS` grew from 31 to 33 entries (`water_z_error_mm_signed_mean`,
  `z_position_error_mm_gauge_corrected_mean`), appended at the end without touching any existing
  column or its position.
- FIX-03: a new per-camera table (`generalization_sweep_per_camera.csv` from `_run_full`/
  `_run_smoke_configs`, `generalization_sweep_per_camera_band.csv` from `_run_seed_band`) carries one
  row per (configuration, seed, camera), every camera present, with an `is_reference_camera` flag and
  the `h_c_error_mm_signed` identity.
- FIX-03: the checkpoint schema bumped 1 -> 2 to carry `per_camera_rows`, with a warned (never
  raised) fallback for older checkpoints.
- FIX-04: `degeneracy_verdict` gained a `vacuous_by_construction` branch (three conditions, checked
  before the p-value comparison), and `build_focal_standoff_df` appends a same-row reason to the
  existing free-text `scope` column for exactly those rows -- no schema change.
- Task 3: this file's `## Evidence` section below records the reproducible derivation of MF-12's four
  quantities against the committed `generalization_sweep_band.csv`, per D-06/D-12's amendment (no
  `.planning/MANUSCRIPT-FINDINGS.md` write from this plan).

## Task Commits

Each task was committed atomically:

1. **Task 1: FIX-03 -- signed and gauge-corrected E6 columns plus the per-camera decomposition table**
   - `bbcdbde` (feat)
2. **Task 2: FIX-04 -- label E7's fixed rows vacuous-by-construction, in the existing scope column**
   - `0633ff3` (feat)
3. **Task 3: Record the reproducible derivation of MF-12's four quantities** -- this SUMMARY.md file
   (committed with the plan's final commit)

## Files Created/Modified

- `experiments/e6_generalization_sweep.py` -- appended two aggregate columns, added
  `compute_water_z_error_mm_signed` and `build_per_camera_rows`, threaded `per_camera_rows_out`
  through `run_configuration`/`run_sweep`, bumped checkpoint `schema_version` to 2, wired the new CSV
  writer into `_run_full`/`_run_seed_band`/`_run_smoke_configs`.
- `experiments/e7_focal_standoff_analysis.py` -- added the `vacuous_by_construction` branch to
  `degeneracy_verdict` and `VACUOUS_SCOPE_SUFFIX`, wired into `build_focal_standoff_df`.
- `tests/unit/test_experiments_e6.py` -- new tests for the signed helper, `build_per_camera_rows`,
  checkpoint round-trip (v2 restore, v1 warn-and-skip); updated `test_e6_columns_count` and
  `test_degenerate_column_appended_last` for the new 33-column shape; fixed a monkeypatch signature
  broken by the new `gauge_correct_z` call site.
- `tests/unit/test_e7_focal_standoff.py` -- new tests for the vacuous branch and
  `build_focal_standoff_df`'s row-level scope/verdict split; updated
  `test_constant_focal_drift_counts_seeds_but_gives_vacuous_verdict` (was `..._no_signature`) and
  `TestDegeneracyVerdict`'s hand-built association dicts to carry the three new required keys.

## Decisions Made

- Followed D-01 through D-14 and the 23-CONTEXT.md amendment as specified; no new architectural
  decisions were required during execution.
- Where an existing test's hand-built fixture omitted keys my new code now reads
  (`n_seeds_negative`/`n_seeds_positive`/`mean_within_seed_correlation` in `TestDegeneracyVerdict`,
  the `gauge_correct_z` kwarg in a `compute_per_camera_errors` monkeypatch), the fixtures were
  extended to match the real call signature/shape rather than loosening the new code to tolerate
  partial dicts -- real callers always provide the complete association/errors shape.

## Deviations from Plan

None beyond the test-fixture updates described above and in "Decisions Made," which are direct,
in-scope consequences of the plan's own instructions (updating `test_e6_columns_count` and
`test_degenerate_column_appended_last` was explicitly called out in the plan; the association-dict
and monkeypatch fixes are the same category of "existing test exercises the changed code path,"
Rule 1).

## Issues Encountered

- The plan's `<verify>` command for Task 2
  (`python -m pytest tests/unit/test_e7_focal_standoff.py tests/unit/test_e7_band_mode.py -x -q -m "not slow"`)
  includes `tests/unit/test_e7_band_mode.py`, which exercises `experiments/e7_interface_ablation.py`
  (a different module, untouched by this plan) via five real `--smoke --seeds` solves. On this
  machine that combination exceeded the tool's timeout even filtered to `-m "not slow"`. Verified
  instead: `tests/unit/test_e7_focal_standoff.py` alone (the file this plan actually modifies) --
  20/20 passed in ~1s. `test_e7_band_mode.py` was not modified by this plan and its slowness is a
  pre-existing property of `e7_interface_ablation.py`'s smoke path, not something this plan's diff
  could have introduced; per this project's CLAUDE.md policy, a command that risks exceeding the
  tool's ceiling is out of scope for an executor, and the orchestrator's post-merge full-suite gate
  is the correct place to catch any regression there.

## Evidence

Cross-referencing `.planning/MANUSCRIPT-FINDINGS.md` MF-12 (the E6 gauge decomposition) and MF-17
(E7's fixed arms are vacuous, not null). Per the 23-CONTEXT.md amendment dated 2026-08-17, this
section is the durable record of this plan's derivation; `.planning/MANUSCRIPT-FINDINGS.md` is not
written by this plan (no citable artifact survives a git-ignored in-phase run, and this phase measures
nothing new -- see 23-CONTEXT.md's amendment for the full rationale). The ledger pass is the user's.

### 1. What reproduces from committed data today, exactly

Seed 43, `layout`/`line`, from the already-committed `experiments/results/generalization_sweep_band.csv`
(read-only; not modified by this plan):

- `water_z_error_mm_mean` = 18.854672
- `z_position_error_mm_mean` = -18.495458
- Signed difference: `-water_z_error_mm_mean - z_position_error_mm_mean` = **-0.359214**

This matches MF-12's reported `h_c` signed mean of **-0.3592 mm**. MF-12's earlier "0.3600" figure was
a rounding of this same quantity, not a second measurement -- both round to 0.36 mm, so the claim
survives, but -0.359214 (not -0.360000) is the number that reproduces from committed columns today.
Verified live during Task 1:

```
python -c "import pandas as pd; d=pd.read_csv('experiments/results/generalization_sweep_band.csv'); \
  r=d[(d.seed==43)&(d.axis=='layout')&(d.axis_value=='line')].iloc[0]; \
  print(round(-r.water_z_error_mm_mean - r.z_position_error_mm_mean, 6))"
-0.359214
```

The same identity on the `layout`/`grid` baseline row (seed 43) reproduces MF-12's grid-axis figure:
`water_z_error_mm_mean` = 0.832572, `z_position_error_mm_mean` = -0.218396, signed difference =
**-0.614176**, matching MF-12's reported grid `h_c` signed mean of -0.6142 mm.

### 2. Where each of MF-12's four quantities now comes from, by artifact/column/aggregation

These four are the quantities in 23-CONTEXT.md's table (LINE seed 43 / GRID). None is recomputed by
this plan -- FIX-03 only emits the columns; the suite runs (and the numbers land) at the frozen sha in
Phase 28.

1. **Gauge-corrected camera Z error** (LINE 1.6814 / GRID 0.0199) --
   `z_position_error_mm_gauge_corrected_mean` in `generalization_sweep.csv` /
   `generalization_sweep_band.csv` (cross-camera mean of `compute_per_camera_errors(...,
   gauge_correct_z=True)`'s `z_position_error_mm`), and per camera as
   `z_position_error_mm_gauge_corrected` in `generalization_sweep_per_camera.csv` /
   `generalization_sweep_per_camera_band.csv`.
2. **`h_c` error signed mean** (LINE -0.3592 mm / GRID -0.6142 mm) -- the mean of
   `h_c_error_mm_signed` over the rows of one `(axis, axis_value, seed)` group in the per-camera
   table. `h_c_error_mm_signed` is computed per row as
   `water_z_error_mm_signed - z_position_error_mm_raw`.
3. **"gauge correction removes X% of the Z-error magnitude"** (LINE 79.5% / GRID 4.6%) --
   `1 - mean(|z_position_error_mm_gauge_corrected|) / mean(|z_position_error_mm_raw|)` over the same
   `(axis, axis_value, seed)` group in the per-camera table (or equivalently, over
   `z_position_error_mm_gauge_corrected_mean`/`z_position_error_mm_mean`'s absolute-value analogues
   at the aggregate level -- the per-camera table is the finer-grained source).
4. **"per-camera `h_c` error after datum removal, excluding cam0 and cam1"** (LINE ~2.4 mm / GRID
   ~0.6 mm) -- mean of `|h_c_error_mm_signed|` over the group **filtered** by
   `is_reference_camera == False` and `camera != "cam1"`. **This exclusion is a reader-side filter
   over an artifact that emits every camera, not a property of the data.** `cam0`'s exclusion is
   principled: it is pinned at `C_z = 0` by construction, so its `h_c` error is identically its
   `water_z` error (`is_reference_camera == True` marks this in the table). `cam1`'s exclusion is
   discretionary, made by MF-12's original hand analysis after seeing the data -- the all-12-camera
   figure is equally derivable from the same rows by simply not applying that filter.

### 3. The identity that makes the table checkable

Per camera, because `h_c = water_z - C_z`:

```
h_c_error_mm_signed == water_z_error_mm_signed - z_position_error_mm_raw
```

On the committed seed-43, layout=line aggregate row this reproduces as
`-18.854672 - (-18.495458) == -0.359214` (section 1 above) -- the per-camera table's row-level
identity and the aggregate-column identity are the same relationship at two different grains, which is
why the aggregate check above is sufficient corroboration without re-deriving anything by hand a
second time.

### 4. What changed and what did not

`water_z_error_mm_mean` and `z_position_error_mm_mean` keep their pre-existing (mean-absolute /
raw-signed-mean) definitions unchanged, so every prior run stays comparable byte-for-byte on those
columns. The two new aggregate columns and the per-camera table are strictly additive. Both sit
behind MF-12's collinear caveat: the correct reading of the line-axis result is "about four times
worse at recovering the physical standoff -- not the thirty times the raw column suggests" (LINE
`h_c` -0.36 mm vs. GRID `h_c` -0.61 mm is roughly comparable in magnitude, while the RAW
`water_z_error_mm_mean` column reads 18.9 mm vs. 0.83 mm, a ~23x difference that is mostly gauge).
The deficiency this plan fixes was provenance (no reproducible artifact backed the reading), not the
interpretation itself, which was already correct.

### 5. The seed-coverage correction

The layout axis already ran all six seeds (42-47) in the committed `generalization_sweep_band.csv` --
what was seed-43-only was MF-12's original **hand analysis**, not the underlying sweep. FIX-03's
per-camera band table (`generalization_sweep_per_camera_band.csv`, written by `_run_seed_band`)
therefore turns MF-12's single-seed caveat into a six-seed band with no extra solve: the same 102 rows
of `generalization_sweep_band.csv` already cover all six seeds on every axis, and the new per-camera
table spans the identical seed set.

### 6. FIX-04's one-line consequence

`e7_focal_standoff.csv`'s two `fixed` rows now read `verdict == "vacuous_by_construction"` with a
same-row reason appended to `scope` (see `VACUOUS_SCOPE_SUFFIX` in
`experiments/e7_focal_standoff_analysis.py`), so MF-17's observation (E7's fixed arms are vacuous, not
null) is now discharged in the artifact itself rather than requiring the manuscript's care to read
correctly. The published `shared_refined` result (10/10 seeds, p = 0.000977) is a `refined`-arm
verdict, computed on a defined, nonzero-variance statistic, and is untouched by this plan --
`degeneracy_verdict`'s new branch only fires when `n_seeds_negative == n_seeds_positive == 0` AND
`mean_within_seed_correlation` is undefined, which the refined arms' measured 10/10 result does not
satisfy.

### Ledger candidate

Per 23-CONTEXT.md's amendment, this note flags what a reviewer would want transcribed into
`.planning/MANUSCRIPT-FINDINGS.md` without an executor acting on it: sections 1-2 above (the
reproducible -0.359214/-0.614176 identity and the per-quantity artifact/column/aggregation map) are
the direct evidentiary backing for MF-12's existing prose, and section 6 is the direct evidentiary
backing for MF-17's existing prose. Transcribing either is the user's call.

## Self-Check

- `experiments/e6_generalization_sweep.py` exists: FOUND
- `experiments/e7_focal_standoff_analysis.py` exists: FOUND
- `tests/unit/test_experiments_e6.py` exists: FOUND
- `tests/unit/test_e7_focal_standoff.py` exists: FOUND
- Commit `bbcdbde` (Task 1, FIX-03): FOUND in `git log --oneline`
- Commit `0633ff3` (Task 2, FIX-04): FOUND in `git log --oneline`
- `git diff --stat -- Spinoffs/ experiments/results/ .planning/MANUSCRIPT-FINDINGS.md`: empty (no
  changes to the manuscript tree, committed results, or the findings ledger)
- `git status --porcelain experiments/results`: empty

## Next Phase Readiness

- FIX-03 and FIX-04 land cleanly; no solver behavior changed in this plan (both fixes are reporting/
  labelling only).
- The new artifact names (`generalization_sweep_per_camera.csv`,
  `generalization_sweep_per_camera_band.csv`) are recorded here for Phase 26 (DRIVER-01/DRIVER-03) to
  register in the suite driver's stage list and the completeness gate's expected-artifact list --
  this plan does not touch either.
- `e7_focal_standoff.csv`'s two `fixed` rows change verdict string and gain `scope` text; any
  expectation sheet or hand-verification list downstream (Phase 26/28/29) must carry the new expected
  verdicts.
- The four numeric MF-12 quantities themselves (gauge-corrected Z error, `h_c` signed mean,
  percent-removed, per-camera excluding cam0/cam1) are not yet re-measured against the new columns --
  they land when the suite runs at the frozen sha in Phase 28. Section 1's -0.359214/-0.614176 pair
  is the one identity that already reproduces from committed data today.

---
*Phase: 23-experiment-correctness-fixes*
*Completed: 2026-08-17*
