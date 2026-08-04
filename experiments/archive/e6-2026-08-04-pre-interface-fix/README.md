# E6 baseline — archived 2026-08-04, before the single-flat-interface fix

A byte-for-byte copy of E6's manuscript-facing CSV, plus recorded pointers
to the run-level and per-configuration provenance records, as they stood at
commit `22e75ef2b424c9b0234502e5229345a9f5912b11`, taken BEFORE Phase 19.4's
single-flat-interface fix.

## Why this exists

`generate_camera_array` (`src/aquacal/datasets/synthetic.py:255-260`) applied
its `height_variation` jitter to `water_z` — the world-frame Z of the water
*surface*, shared by every camera per the paper's whole premise — while
holding every camera at `C_z = 0`. That gave the synthetic ground truth one
water surface PER CAMERA instead of one shared plane. Measured over 31,680
corner observations (one seed, one trajectory — not an effect size, see the
caveat below): mean displacement **1.42 px**, max **6.33 px**, against an
E4/E6 reprojection RMS of only ~0.4–0.9 px. D-19.4-09 moves the jitter from
`water_z` to `C_z`, so `h_c = water_z - C_z` (the physical camera-to-water
gap) is preserved exactly per camera while every camera now looks through
the SAME surface.

E6 carries two specific consequences beyond the shared defect:

1. **`GRID_DEPTH_RANGE[0]` re-derives from `1.181852154` to `1.176215948`**
   — a 5.636 mm drop, exactly equal to cam7's seed-42 jitter, the camera
   whose water surface sat deepest under the old per-camera-surface model.
   The old constant was anchored on `max(water_zs) = 1.031 + 5.636 mm`;
   post-fix, `max(water_zs) == height_above_water` exactly, because there is
   only one surface to take the max of.
2. **E6's seed-locking (legal at only ~6% of seeds) is CURED by this fix.**
   Measured over 3,000 draws (500 seeds x {8,12,16} cameras x calibration
   and holdout scenarios): exactly one distinct derived floor,
   `1.176215948246`, at every single draw. The per-scenario clearance-floor
   guard can no longer fire, because there is no per-camera surface spread
   left to raise the floor. This is D-19.4-15, and it is the origin defect
   this entire phase was created to fix (originally misdiagnosed as a
   clearance-floor bug — see `19.4-CONTEXT.md` § SUPERSESSION).

**This is ONE seed, ONE trajectory** for the pixel-displacement figures
above. The 1.42 px / 6.33 px numbers are enough to establish that the
defect is real and dominant — they are NOT an effect size, and must not be
quoted as one anywhere near the manuscript (blocking anti-pattern 7,
`19.4-CONTEXT.md`). The seed-locking cure (item 2 above), by contrast, IS a
3,000-draw measurement and is reported as such.

## Provenance

- Source: `experiments/results/` at commit
  `22e75ef2b424c9b0234502e5229345a9f5912b11`
  (`feat(19.3-09): add the scripted pre-launch abort gate and archive E3`) —
  the commit recorded in `e6_provenance.json`'s own `environment.git_sha`
  field, i.e. the commit that PRODUCED these artifacts, not the commit that
  landed them in git.
- Produced by `experiments.e6_generalization_sweep` (the 14-config
  generalization sweep: baseline, 6 index points, 2 layouts, 2 scales, plus
  3 `is_baseline` duplicates noted as an open defect in
  `19.3-CONTEXT.md`'s Deferred Ideas).

## What is copied here, and what is not

Copied (small, no `git_sha`/high-entropy content, well under the 1000 KB
`check-added-large-files` limit):

- `generalization_sweep.csv` — the full 14-config generalization sweep table

**Not** copied: `e6_provenance.json` (the run-level sidecar) or the twelve
`e6_configs/*.json` per-configuration checkpoints. Each is
`assemble_benchmark_record`-shaped (or carries the same schema) and its
`environment.git_sha` field is a 40-hex string that `detect-secrets` reads
as a high-entropy hex string — the same reason the E2 precedent
(`experiments/archive/e2-2026-07-30-pre-pnp-guard/`) excluded
`benchmark.json`. Retrieve them with:

```bash
git show 22e75ef2b424c9b0234502e5229345a9f5912b11:experiments/results/e6_provenance.json
git show 22e75ef2b424c9b0234502e5229345a9f5912b11:experiments/results/e6_configs/baseline.json
git show 22e75ef2b424c9b0234502e5229345a9f5912b11:experiments/results/e6_configs/index_1.36.json
git show 22e75ef2b424c9b0234502e5229345a9f5912b11:experiments/results/e6_configs/index_1.39.json
git show 22e75ef2b424c9b0234502e5229345a9f5912b11:experiments/results/e6_configs/index_1.42.json
git show 22e75ef2b424c9b0234502e5229345a9f5912b11:experiments/results/e6_configs/index_1.45.json
git show 22e75ef2b424c9b0234502e5229345a9f5912b11:experiments/results/e6_configs/index_1.48.json
git show 22e75ef2b424c9b0234502e5229345a9f5912b11:experiments/results/e6_configs/index_1.51.json
git show 22e75ef2b424c9b0234502e5229345a9f5912b11:experiments/results/e6_configs/index_1.55.json
git show 22e75ef2b424c9b0234502e5229345a9f5912b11:experiments/results/e6_configs/layout_line.json
git show 22e75ef2b424c9b0234502e5229345a9f5912b11:experiments/results/e6_configs/layout_ring.json
git show 22e75ef2b424c9b0234502e5229345a9f5912b11:experiments/results/e6_configs/scale_double_scale.json
git show 22e75ef2b424c9b0234502e5229345a9f5912b11:experiments/results/e6_configs/scale_half_scale.json
```

## Why it is NOT under `experiments/results/`

`tests/unit/test_experiments_provenance.py` globs `experiments/results/` at
collection time and asserts every discovered artifact carries its provenance
record. Archived copies placed there would be swept into that gate as if
they were live results. This directory is deliberately outside that glob.

## How to use it

After the single-flat-interface re-run, diff the regenerated
`generalization_sweep.csv` against the copy here. A moved reprojection
number and a moved optimality/degenerate-guard-count are both expected
consequences of this fix. E6 has no measured seed band for the grid family
(D-19.4-13's Deferred Ideas), so do not claim a quantified accuracy delta
from this diff alone — report the direction and magnitude of movement.
Separately, confirm the post-fix seed-43 run (D-19.4-15, D-19.4-13) — a
formerly-failing seed under the old per-camera floor — now completes, as the
end-to-end evidence that the seed-locking origin defect is gone. Do not
delete this directory until the manuscript's numbers have been reconciled
against the re-run.
