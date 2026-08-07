---
quick_id: 260807-dcv
slug: e1-e7-band-provenance-emit-z-rmse-column
status: complete
date: 2026-08-07
commits:
  - cda9d0e  # code: merge, sidecars, gate
  - fea64a9  # artifacts: regenerated band + sidecar + CSV_TO_RECORD correction
---

# Quick task 260807-dcv — E1/E7 band provenance

## What was wrong

The manuscript's headline claim — `~135x` improvement over non-refractive calibration, in the
abstract (`main.tex` L68) and §3 (L281) — is built from raw `z_rmse_mm` at the deepest test point
(2.5 m). That column existed in exactly two places: `exp3_xy_vs_z_anisotropy.csv`, which is
**seed 42 alone with no seed column**, and the **gitignored** `seed_sweep_19_3/`. So the published
10-seed band (97.3x-178.0x, mean 139.5, n=10) was **not regenerable from any committed artifact**.

MF-08 states the band "regenerates from `experiments/results/exp1_band.csv`". It did not: that CSV
carried `rmse_mm`, a **scale-corrected** residual, and computing the ratio from it gives
**1.1x-2.9x** — a different quantity by two orders of magnitude.

Root cause was a code gap, not a sizing exclusion. `_run_band`'s runner did:

```python
_df_exp1, df_exp2, _df_spatial, _df_exp3 = _build_dataframes(...)
return df_exp2
```

discarding three frames including the one holding `z_rmse_mm`. Re-running the band would have
reproduced the same gap indefinitely.

Separately, `gate4_band` had FAILed for **both** E1 and E7 since 19.4: band mode must never
overwrite the single-seed `e{1,7}_benchmark_*.json` production records, so the seeds a band covers
had nowhere to be recorded.

## What was done

**Code (`cda9d0e`).** `merge_band_columns` merges EXP3's non-key columns
(`xy_rmse_mm`, `z_rmse_mm`, `anisotropy_ratio`, `n_points`) onto the band frame under
`validate="one_to_one"`, so a duplicated `(test_depth_m, model)` key raises rather than silently
fanning rows out. `exp1_band.csv` GAINS COLUMNS rather than gaining a sibling file.
`EXP2_COLUMNS`/`EXP3_COLUMNS` are untouched, so the single-seed CSVs they pin stay byte-identical.
Pure output plumbing — no calibration, solver or numeric behaviour changed.

E1 and E7 now write band-owned sidecars (`e{1,7}_seed_band_provenance.json`) recording
`solver_config['seeds']`, on the pattern 19.5 established for E6/E5. `check_band_csv` gains a
`band_sidecar` parameter searched BEFORE the legacy `eN_benchmark_*.json` glob, which stays as a
fallback; the FAIL text is unchanged so the expected residual failures stay honest.

**Re-run (`fea64a9`).** Ten seeds at `cda9d0e`, launched 14:27:28Z, finished 15:43Z — **76 min**,
20/20 solves. No `--force`: force is implied for the band CSV alone, so resumability left every
other artifact untouched.

## The result

**All ten seeds reproduce MF-08's published band to every digit:**

| seed | 42 | 43 | 44 | 45 | 46 | 47 | 48 | 49 | 50 | 51 |
|---|---|---|---|---|---|---|---|---|---|---|
| ratio | 128.1 | **178.0** | **97.3** | 153.4 | 157.8 | 131.4 | 134.0 | 158.9 | 99.1 | 156.5 |

**97.3x - 178.0x, mean 139.5, sd 25.1 (population), n=10.**

`exp1_band.csv`: 8 -> 12 columns, still exactly **160 rows**, 10 distinct seeds. The sidecar records
seeds 42-51 and `git_sha = cda9d0e`.

This is the second independent confirmation of E1's determinism — 19.4 already found E1's CSVs
byte-identical across `2a623f9..0ffbe15`, and these ratios now match values measured 2026-08-03.

**Nothing else moved.** `e1_benchmark_{refractive,nonrefractive}.json` are byte-unchanged, and a
`--seeds` run never writes `exp1_parameter_errors.csv`, `exp2_depth_generalization.csv`,
`exp2_spatial_errors.csv` or `exp3_xy_vs_z_anisotropy.csv` — so every artifact the manuscript's
figures are built from is untouched, `exp3` included.

## Gates: 100 PASS / 7 N/A / 9 FAIL (was 99 / 7 / 10)

`gate4_band:exp1_band.csv` **PASSes** — "10 distinct seed(s) match `e1_seed_band_provenance.json`'s
recorded seed list".

**EXPECTED RESIDUAL FAIL, not a defect:** `gate4_band:interface_ablation_band.csv` (E7) still FAILs.
E7's sidecar-writing code shipped in `cda9d0e`, but the sidecar does not exist until E7's band is
re-run, and that re-run is **deliberately deferred until after the Zenodo regeneration** — E7's
claim, unlike E1's, IS reproducible from its committed CSV (`camera_height_drift_mm`, 480 rows, all
four arms, all ten seeds), so it was not manuscript-blocking. The remaining 8 FAILs are the
pre-existing set (6 seedless-legacy provenance records, 2 guard counts).

## Tests

| command | result |
|---|---|
| `test_e1_band_mode.py test_e7_band_mode.py test_rerun_gates.py test_experiments_provenance.py` | 372 passed, 27 skipped, 0 failed (28m42s) |
| `test_experiments_provenance.py` (after the CSV_TO_RECORD correction) | 291 passed, 27 skipped |
| full unfiltered `pytest tests/` | see the closing commit |

## Lessons

**A targeted test file can exceed the 600 s ceiling too.** The executor stalled exactly as
CLAUDE.md predicts — it backgrounded a long run and ended its turn — but the cause was the
dispatch brief, not the agent: it was told to run "the files it touched", and
`test_e1_band_mode.py` runs real band solves. The same command auto-backgrounded on the
orchestrator at 600 s and took 28 minutes. The existing rule ("never give an executor the full
suite") needs extending: name the specific fast tests, or have the orchestrator run them.

**The worktree forked from a stale base again** — `b4da55b`, the v1.8.0 tag, 609 commits behind.
Fourth occurrence. The executor correctly reported instead of self-recovering. Re-dispatching on
the main checkout worked and also removed the PYTHONPATH trap.

**MF-08's artifact citation was wrong, and a gate had been pointing at it for two phases.**
`gate4_band`'s E1 FAIL was documented as recording-only bookkeeping since 19.4. It was in fact
flagging that the paper's most prominent number had no citable artifact. A FAIL tolerated long
enough stops being read.
