# Probe: does re-tuning the baseline's Huber knee change E1's accuracy?

**Date:** 2026-08-17
**Sha:** `054d753` (Phase 24 complete, Phase 25 context captured)
**Script:** `probe_fscale.py` · **Raw:** `calls_{control,treatment}.json`,
`fscale_accuracy_comparison.csv` · **Logs:** `control.log`, `treatment.log`, `compare.log`
**Closes:** Finding 6's open item in `../2026-08-17-optimality-decomposition/FINDINGS.md`
**Opened by:** Phase 25 discussion, D-19

## Question

E1 optimizes both arms under `f_scale = 1.0`. Finding 6 measured that this knee suits the
refractive arm (4.5% of residuals past it) and not the baseline (29.4-47.7% past it), so the
baseline is fitted under a robust loss tuned to the *other* arm's residual scale. Does re-tuning
it change E1's accuracy — and therefore the 97-178x ratio?

Direction of risk when the probe was opened: a too-tight knee down-weights a third to a half of
the baseline's residuals, so the current setting, if it biases anything, **flatters** E1's ratio.

## Method

Finding 6's symmetric rule, `f_scale = 3 x median|r|`, applied to the **baseline arm only**:
2.8332 on the interface pass, 1.8522 on the intrinsic pass, from the medians Finding 6 measured
(0.9444 and 0.6174). The refractive arm was deliberately left at 1.0 rather than set to its own
1.007, so it reproduces the control exactly and serves as the in-run check that the patch hit only
the arm it was meant to.

Control and treatment both ran at `054d753`. `verify_23_optblocks/` was **not** used as the
control — it is at `a7f0f25`, before Phase 24 touched `_optim_common.py`.

Comparison is on **accuracy, not cost**: changing `f_scale` changes the objective, so costs are
not comparable across runs. (Cost did rise, 26067 -> 41040 and 15098 -> 19456, which is what a
wider knee does arithmetically and carries no information about fit quality.)

**Self-checks, all passed before any number was read:**

1. Exactly 4 solver calls in each run.
2. Every call's incoming `f_scale` was 1.0, so the override was a real change.
3. The untouched refractive arm reproduced the control **bit-for-bit** — `max|abs change|` across
   every refractive metric is `0.000e+00`, confirming the call-ordering assumption and that
   nothing leaked across arms.

## Finding 1 — the ratio does not materially move

| test depth | control | treatment | change |
|---|---|---|---|
| 1.1 m | 25.53x | 26.03x | +1.95% |
| 1.2 m | 16.42x | 16.19x | -1.41% |
| 1.3 m | 18.15x | 16.91x | **-6.83%** |
| 1.4 m | 28.84x | 27.86x | -3.38% |
| 1.5 m | 36.66x | 35.55x | -3.04% |
| 1.7 m | 60.76x | 59.71x | -1.72% |
| 2.0 m | 90.83x | 89.49x | -1.47% |
| **2.5 m** | **123.87x** | **122.52x** | **-1.09%** |

Largest movement anywhere is 6.83%, at a mid depth; the deepest point — the one the headline
number is quoted from — moves **1.09%**.

**Put that against the noise floor.** E1's committed seed band is **97-178x**, a spread of roughly
±30% about its centre. A 1-7% shift from re-tuning the loss is comfortably inside the band and an
order of magnitude smaller than seed-to-seed variation. Per the standing rule (*measure the noise
floor before attributing anything*), this is not a distinguishable effect.

## Finding 2 — the risk direction was right, the magnitude was negligible

The baseline's `z_rmse_mm` improves on average (mean -2.12%, e.g. 266.53 -> 263.63 mm at 2.5 m), so
the fairly-tuned baseline does fit slightly better and the ratio does shrink slightly — exactly the
sign predicted when the objection was raised. It is simply far too small to matter. The objection
was worth raising and does not survive measurement.

Per-metric, baseline arm:

| metric | mean rel change | max abs rel change |
|---|---|---|
| `xy_rmse_mm` | **-10.96%** | 11.29% |
| `z_rmse_mm` | -2.12% | 6.83% |
| `anisotropy_ratio` | +9.93% | 14.92% |
| `signed_mean_mm` | +6.45% | 7.50% |
| `rmse_mm` (exp2) | +1.27% | 2.84% |

The larger movers are `xy_rmse_mm` and the baseline's `anisotropy_ratio` — but both are
**non-refractive** quantities, and neither carries a published claim. The published ~2.3 anisotropy
is the **refractive** arm's, which is bit-identical between runs (2.4537 at 2.5 m in both).

## Finding 3 — one pass is close enough to the fixed point

`3 x median|r|` is self-referential: re-solving moves the median it was derived from. Measured
distance from self-consistency after one pass:

| pass | applied | implied at new solution | gap |
|---|---|---|---|
| interface | 2.8332 | 2.9601 | 4.5% |
| intrinsic | 1.8522 | 1.8994 | 2.5% |

Both within 5% of the fixed point, and the accuracy effect at this `f_scale` is already ~1-7%. A
second iteration would move `f_scale` by <5% and the accuracy by less again — it cannot turn a
negligible effect into a material one. **The one-pass reading stands.**

## Net position

**Finding 6's open item is closed by measurement.** The baseline being fitted under a knee tuned
to the other arm's residual scale is real, and it is worth ~1% on the headline ratio. E1's 97-178x
band is not measured against a materially handicapped baseline.

Combined with the optimality probe's Finding 4 (warm restarts recover no cost, so the baseline is
converged), both fairness objections raised against E1's comparison are now answered **in E1's
favour** — one on convergence, one on loss tuning.

## What this does and does not license

**Does** license stating in the DEGEN-05 verdict that the loss-tuning objection was measured and
closed, with the sign and the magnitude, rather than argued.

**Does not** license changing the library's `f_scale`. Nothing here says the symmetric rule is
better — only that the choice does not matter at the scale of E1's claim. Re-tuning the robust
loss remains an estimator-design change and stays post-submission.

**Does not** produce a number for the manuscript. No value here is §3-facing; this is a null
result about robustness, recorded so the objection is not re-litigated.

## Implementation note for anyone who picks the re-tuning up later

The two passes want different `f_scale` values (2.83 interface, 1.85 intrinsic), but
`PipelineConfig.loss_scale` (`schema.py:335`) is a **single field feeding both** — it reaches
`interface_estimation.py:543` and `refinement.py:356` as `f_scale` through
`pipeline.py:1025,1274`. `optimize_interface` and `joint_refinement` each take `loss_scale`
separately, so a direct caller can differentiate the passes; the config path cannot. Any real
implementation of a per-pass rule needs that seam widened. E1 currently hardcodes `1.0` at
`e1_refractive_comparison.py:755, 881, 1124`.

## Cost, measured

A full E1 single-seed run is **400 s of solver time** (refractive 88.6 + 60.1 s; non-refractive
158.0 + 93.3 s). Wall clock for both runs plus comparison was ~10 min.
