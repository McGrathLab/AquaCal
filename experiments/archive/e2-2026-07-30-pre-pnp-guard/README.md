# E2 baseline — archived 2026-07-30, before the degenerate-PnP guard

Byte-for-byte copies of E2's six committed artifacts as they stood at commit
`35d76a6828550a5a81d47e7eb820f9e34cdb2fe3`, taken BEFORE the Stage-2
degenerate-PnP guard landed.

## Why this exists

Two defects were fixed in `src/aquacal/calibration/` on 2026-07-30 (see
`.planning/debug/stage3-diverges-new-geometry.md`):

1. **Flat NaN clamp** in `compute_residuals` — proven inert on every converging
   configuration by an instrumented branch-hit count of zero. Cannot move E2.
2. **Unvalidated `cv2.solvePnP`** in `refractive_solve_pnp` — `success=True` was
   returned for degenerate near-minimal oblique views with `|t|` up to 3.09e12 m,
   which `_refine_poses_multi_frame` then folded into a weighted mean. This fix
   is **NOT inert**: it already moved the synthetic cells 8x100, 12x100 and
   16x50 (all improved).

Because fix 2 is not inert and real footage contains *more* near-minimal oblique
views than synthetic data, E2's numbers may move. Those numbers feed the
manuscript's Section 3, so this archive exists to make the before/after diff
trivial whenever the re-run happens.

## Provenance

- Source: `experiments/results/` at commit
  `35d76a6828550a5a81d47e7eb820f9e34cdb2fe3`
- Produced by plan 19.2-06 (E2 re-run with `benchmark_memory: true`), which
  reproduced every Section-3 number at 0.000% delta against the manuscript.

## What is copied here, and what is not

Only the two small files carrying the manuscript-facing numbers are copied:
`real_rig_metrics.json` (the Section-3 values) and `camera_parameters.csv`.

The other four are NOT duplicated — they are already immutable in git at the
commit above, and copying them tripped the repo's own `check-added-large-files`
and `detect-secrets` hooks (`calibration.json` 2.2 MB,
`reprojection_residuals.csv` 1.2 MB; `benchmark.json` carries a git SHA that
reads as a high-entropy string). Bypassing those hooks to store a redundant copy
would be the wrong trade. Retrieve them with:

```bash
git show 35d76a6:experiments/results/benchmark.json
git show 35d76a6:experiments/results/calibration.json
git show 35d76a6:experiments/results/reprojection_residuals.csv
git show 35d76a6:experiments/results/reconstruction_errors.csv
```

## Why it is NOT under `experiments/results/`

`tests/unit/test_experiments_provenance.py` globs `experiments/results/` at
collection time and asserts every discovered artifact carries its provenance
record. Archived copies placed there would be swept into that gate as if they
were live results. This directory is deliberately outside that glob.

## How to use it

After any E2 re-run, diff the regenerated `real_rig_metrics.json` against the
copy here. A moved Section-3 number is expected ONLY as a consequence of fix 2
above; anything else is a defect. Do not delete this directory until the
manuscript's numbers have been reconciled.
