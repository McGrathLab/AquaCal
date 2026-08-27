---
created: 2026-08-13T00:00:00.000Z
title: E1's band carries no parameter-level columns, so §3's focal-drift and reprojection-RMS edits have no committed artifact
area: experiments
files:
  - experiments/e1_refractive_comparison.py
  - experiments/check_rerun_gates.py
  - tests/unit/test_e1_band_mode.py
  - tests/unit/test_experiments_provenance.py
---

## Problem

The SoftwareX revision has to edit four §3 sentences whose published values came from the
**pre-depth-fix** E1 run (archived at `experiments/archive/e1-2026-08-02-pre-depth-fix/`).
Traced 2026-08-13: every one of them reproduces byte-exactly from that archive under a
single definition — **mean absolute value across the 12 cameras**.

| main.tex | published | archive (pre-fix) | live seed 42 |
|---|---|---|---|
| L270 focal drift, refractive | 0.033% | **0.0328%** | 0.1416% |
| L270 focal drift, non-refractive | 5.7% | **5.6987%** | 6.1499% |
| L271 reprojection RMS, non-refractive | 1.376 px | **1.376449** | 1.266876 |
| L271 reprojection RMS, refractive | 0.498 px | **0.498449** | 0.499036 |

(The signed mean gives 0.0252%, not 0.033% — the definition is unambiguously mean-abs.)

The two reconstruction-side rows (L278 inter-corner U-shape, L280 anisotropy) are fine:
`exp1_band.csv` already carries `rmse_mm`, `xy_rmse_mm`, `z_rmse_mm` and
`anisotropy_ratio` across seeds 42–51, so those edits can quote a committed band.

**`focal_length_error_pct` and `reprojection_rms_px` are not in any committed artifact
per-seed.** They exist only in `exp1_parameter_errors.csv`, which is a single-seed
artifact, and in gitignored `seed_sweep_19_3/e1/seed_*/` output (`.gitignore:254`;
`git ls-files` confirms untracked). This is the same defect D-260807-dcv fixed for
`z_rmse_mm`, on a different pair of columns.

**Why it blocks rather than inconveniences.** Computed over the ten seeds in
`seed_sweep_19_3/` (whose seed-42 file is byte-identical to
`experiments/results/exp1_parameter_errors.csv`, so the sweep is post-fix and consistent
with the live run):

```
refractive    focal mean-abs   mean 0.0539%   range 0.0186–0.1416%   seed42 = 0.1416%  <- WORST of 10
non_refr      focal mean-abs   mean 7.0324%   range 6.1499–8.4343%   seed42 = 6.1499%  <- BEST of 10
refractive    reproj RMS px    mean 0.4977    range 0.4955–0.5021    seed42 = 0.4990
non_refr      reproj RMS px    mean 1.2453    range 1.1134–1.4386    seed42 = 1.2669
```

**Seed 42 is the single worst seed for the refractive arm's focal drift** (2.6× the
ten-seed mean) and simultaneously the most flattering seed for the non-refractive
baseline. Editing §3 to a bare seed-42 value would publish the worst case for the
method the paper advocates, understate the baseline's failure, and reintroduce an
unbanded accuracy number — the exact thing the project's own gate forbids (no accuracy
claim without a measured seed band; `experiments/README.md`, MF-08/D-19.3-17). The
banded values are both more defensible and better for the paper: 0.054% mean against
7.03%.

Manuscript-side context is in `Spinoffs/papers/aquacal/REVISION-ROADMAP.md` §5b. The
author has decided (2026-08-13) that all pre-fix numbers get updated; this todo supplies
the artifact that update needs.

## Solution

`_run_band` in `experiments/e1_refractive_comparison.py:~782` already computes the
parameter-level frame per seed and **discards it**:

```python
_df_exp1, df_exp2, _df_spatial, df_exp3 = _build_dataframes(...)
...
return merge_band_columns(df_exp2, df_exp3)   # _df_exp1 dropped on the floor
```

So the measurement exists; only the emission is missing. No new solves are required
beyond re-running `--seeds 42-51`.

**The key shapes do not match, so this cannot go into `exp1_band.csv`.**
`BAND_KEY_COLUMNS = ["seed", "test_depth_m", "model"]`; EXP1 is keyed by
`(camera, model)` with no depth axis. Do **not** try to widen `merge_band_columns` or
reindex EXP1 onto the depth axis — it would fabricate a depth dependence the parameter
errors do not have. Emit a **second** band artifact instead:

1. **Add `exp1_parameter_band.csv`**, keyed `["seed", "camera", "model"]`, carrying
   EXP1's non-key columns (at minimum `focal_length_error_pct` and
   `reprojection_rms_px`; emitting all of `EXP1_COLUMNS` costs nothing and keeps the
   per-camera position errors available for S-section use).
   - Leave `EXP1_COLUMNS` and `exp1_parameter_errors.csv` untouched — the single-seed
     CSV must stay byte-identical to its committed baseline (D-19).
   - Follow `exp1_band.csv`'s own conventions: `force=True` implied for band output,
     written only under `--seeds`.
2. **Register it in the two gates that will otherwise reject it:**
   - `tests/unit/test_experiments_provenance.py:~136` — add an entry pointing at
     `e1_seed_band_provenance.json`, mirroring the `exp1_band.csv` entry's wording.
     That entry's existing note ("previously existed per-seed only in gitignored sweep
     output") describes this case verbatim.
   - `experiments/check_rerun_gates.py:~1683` — extend E1's `check_band_csv` coverage,
     or add a second call, so the new CSV's seed column is checked against the sidecar's
     `solver_config["seeds"]`.
3. **Extend `e1_seed_band_provenance.json`'s `scope` string** to say the band now also
   bounds seed-to-seed variance of the parameter-level columns. Keep the existing scope
   qualifier intact — this is still calibration-scenario variance on the `"realistic"`
   synthetic scenario only, not a physical-rig claim, and the sidecar should continue to
   neither assert nor deny an accuracy claim for E1 (D-19.3-17 demoted E1's own).
4. **Add a test in `tests/unit/test_e1_band_mode.py`** mirroring the existing
   `z_rmse_mm` regenerability test (`:146`) — assert the new CSV exists under `--seeds`,
   carries all requested seeds, and is absent from a single-seed run
   (cf. the negative assertion at `:209`).
5. **Re-run** `--seeds 42-51` and commit the artifact, so the manuscript's §3 edit
   quotes a committed, regenerable band.

## Run notes (verified on the Windows box, 2026-08-13)

**No pinned or quiescent environment is required.** E1 does reach OpenCV — Stage 2's
`refractive_solve_pnp` wraps `cv2.solvePnP` (`extrinsics.py:111`) — but MF-20's OpenCV
sensitivity is confined to `CharucoDetector` on real images, and E1 synthesizes its
observations analytically. Measured directly: the 12-camera/100-frame **synthetic** E4 cell
agrees across `main` (Windows, OpenCV 4.13.0, NumPy 2.4.2, aquacal 1.8.0) and
`origin/experiments/linux32gb-rerun` (Linux, 4.14.0, 2.4.6, 2.0.1) to **~4e-8** relative on
`validation_3d_error_mean` and **~1e-10** on `reprojection_rms`, with four environment axes
varying at once.

**The `AquaCal` conda env matches the reference environment exactly** on every axis recorded
by the existing band's sidecar: Python 3.12.12, OpenCV 4.13.0, NumPy 2.4.2, SciPy 1.17.0.

**Refresh the editable install before running — this is not optional.**
`aquacal.__version__` resolves through `_get_version("aquacal")`, i.e. installed
distribution metadata, and the env's dist-info is stale at **1.8.0** while `pyproject.toml`
is at **2.0.1** (bumped 2026-08-11, `2ba0f8e`). The install is editable
(`__editable__.aquacal-1.8.0.pth`), so the **code that runs is the current 2.0.1 working
tree** while `capture_environment()` would stamp the new artifact `aquacal_version: 1.8.0`.
That mislabels a 2.0.1 result as 1.8.0 in a provenance record. Run
`pip install -e . --no-deps` in the `AquaCal` env first, and confirm
`python -c "import aquacal; print(aquacal.__version__)"` reports 2.0.1.
(Root cause and the standing fix are filed separately as
`2026-08-13-editable-install-metadata-can-mislabel-artifact-provenance.md`; this run is the
first that would have realized the defect.)

**Seed-42 self-check: compare to a tolerance, not bit-identity.** The re-run's seed-42 rows
should match `experiments/results/exp1_parameter_errors.csv` and
`seed_sweep_19_3/e1/seed_42/` (verified byte-identical to each other on 2026-08-13), but
those were produced 2026-08-04/07 under genuinely pre-2.0.1 code, so the library gap is in
play. Assert agreement to **~1e-7 relative**; the 1.8.0 -> 2.0.1 gap is measured inert both
on synthetic cells (above) and on real data (MF-20). Movement beyond that tolerance is a
finding, not a nuisance — stop and report it rather than committing the artifact.

**Budget ~70 minutes.** The existing 10-seed band took 68.7 min on this machine in this env
(`e1_seed_band_provenance.json`).

**Do not commit anything while the run is in flight.** `capture_environment()` shells out to
`git rev-parse`; a mid-run commit makes the recorded SHA describe code that did not produce
the artifact (knowledge-base: "Commit nothing during a production run"). `_run_band` captures
the environment once before the seed loop, which narrows but does not remove the hazard.

**Ignore the `seconds` the sidecar records.** MF-14 puts this machine's wall-clock noise floor
at ~1.85x at constant computational work, and no manuscript number comes from E1 timing.

## Do not

- Do not merge EXP1's columns into `exp1_band.csv`. The key shapes are incompatible and
  the result would imply a depth dependence that does not exist.
- Do not modify `EXP1_COLUMNS`, `exp1_parameter_errors.csv`, `EXP2_COLUMNS` or
  `EXP3_COLUMNS`. The single-seed CSVs are pinned byte-identical to their committed
  baselines and the archive diffs depend on that.
- Do not read the movement from 0.033% to 0.054% as the refractive model getting worse,
  or narrate it as any kind of regression. Per
  `experiments/archive/e1-2026-08-02-pre-depth-fix/README.md`, the depth-clearance fix
  corrected the **scenario geometry**, not the calibration, and accuracy was measured
  indistinguishable between the high- and low-optimality groups. The old numbers are not
  wrong; they describe a geometry the generator no longer produces.
- Do not promote `seed_sweep_19_3/` out of `.gitignore` as a shortcut. It is unversioned
  sweep output with no provenance sidecar; the point of this todo is a gated artifact.
- Do not re-run E1's single-seed production artifacts while doing this. Band mode
  deliberately does not overwrite `e1_benchmark_<model>.json`, and that separation is
  load-bearing (D-260807-dcv).
