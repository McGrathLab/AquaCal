# E6 at three seeds — the first non-42 measurements ever taken

Measured 2026-08-03 by `experiments/e6_legal_seed_probe.sh`. Raw output is in
`seed_sweep_19_3/e6/seed_{62,28}/`, which is **gitignored** (`.gitignore:238`) — this file and
`e6_seed_band_42_62_28.csv` beside it are the durable record. Regenerating costs ~85 min per seed.

## Why these seeds, and why no code change was needed

E6 was believed seed-locked to 42. It is not. The frozen `GRID_DEPTH_RANGE[0]` =
1.181852154281008 must be cleared by **two** camera arrays per configuration — the calibration
array at `seed` and the holdout array at `seed + 1_000_000`. **29 of seeds 0–499 (5.8%) clear
both**, and can run today with no fix. Below 100: **28, 42, 52, 62, 72, 75, 94**. Full mechanism in
`.planning/debug/e6-seed-locked-clearance-floor.md`.

| seed | calibration floor | holdout floor | wall clock | result |
|---|---|---|---|---|
| 42 | 1.181852 (== constant, zero margin) | 1.181380 | 96.6 min | `{'ok': 14}` |
| 62 | 1.178591 | 1.179652 | 85 min | `{'ok': 14}` |
| 28 | 1.180858 | 1.179234 | 83 min | `{'ok': 14}` |

`degenerate_observations_at_solution == 0` on all 14 configurations at all three seeds.

## Headline: legality delivers convergence, and accuracy is reproducible

`reconstruction_rmse_mm` agrees to within ~5% on every configuration; `reprojection_rms_px` agrees
to three decimals. A fix phase does **not** need to budget for accuracy work.

## Two seed-fragile spots, both invisible while E6 was single-seed

### 1. `scale/double_scale` optimality — diagnostic only, no accuracy cost

| metric | s42 | s62 | s28 |
|---|---|---|---|
| `optimality_stage3_intrinsic_pass` | 0.00166 | **1.139** | **0.2241** |
| `optimality_stage3_interface_optimization` | 0.00853 | **2.511** | 0.00174 |
| `reconstruction_rmse_mm` | 0.7244 | 0.6619 | 0.6466 |

Both non-42 seeds are elevated on the intrinsic pass (2/2). This is the configuration whose
outlier collapse (`5e+01 -> 1e-02`) MF-08 credits to the 19.3 geometry fix. **Accuracy did not
degrade** — seed 62's reconstruction RMSE is slightly *better* than seed 42's. So the collapse
claim is seed-fragile **as a convergence-diagnostic statement**, not as an accuracy one.

Per the standing rule, optimality is quoted to one significant figure and supports an
order-of-magnitude reading only.

### 2. `layout/line` parameter recovery — the more consequential one

| metric | s42 | s62 | s28 |
|---|---|---|---|
| `xy_position_error_mm_mean` | 2.231 | 1.565 | **6.152** |
| `water_z_error_mm_mean` | 3.452 | 8.251 | **11.76** |
| `reconstruction_rmse_mm` | 0.4886 | 0.4660 | 0.4463 |
| `reprojection_rms_px` | 0.792 | 0.711 | 0.770 |

~4x spread on recovery, far above every other configuration, while reconstruction and reprojection
stay normal. **Bad parameter recovery with clean reconstruction is this project's documented
weak-observability signature** — and note that anti-pattern 2 applies directly: reprojection RMS
discriminates nothing here.

## What this does and does not license

**Does:** retire the claim that an E6 seed band is *structurally* impossible. It is obtainable
today from the 29 naturally-legal seeds. **MF-08 still says the silence is structural and needs
amending.**

**Does NOT:** license quoting a band. n = 3 (one published + two independent) is enough to show
both fragile spots are real rather than one unlucky seed, and enough to bound the accuracy risk.
It is not enough to state a range. Anti-pattern 7 binds.

**Open:** whether the `layout/line` instability persists across more seeds, and whether
`double_scale`'s intrinsic-pass optimality is elevated at every non-42 seed or only at some.
Both are answerable at ~85 min/seed with no code change.
