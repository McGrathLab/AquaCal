# Probe: does E1's ratio depend on detection noise?

**Date:** 2026-08-18
**Sha:** `211214c` (Phase 25, waves 1-4 merged)
**Invocation:** `python -u -m experiments.e1_refractive_comparison --seeds 43,44 --out .planning/probes/2026-08-18-e1-noise-axis`
**Raw:** `exp1_band.csv` (128 rows), `exp1_parameter_band.csv` (192 rows),
`e1_seed_band_provenance.json` · **Log:** `e1_noise_probe.log`
**Opened requirement:** BAND-01 (Phase 25) · **Wall clock:** 44 min, 8 cells

> ## PROVISIONAL — two seeds, no §3-facing number
>
> This is the **probe** D-21 authorises, not the band of record. **The band of record — four noise
> levels × ten seeds, 640/960 rows — is executed by Phase 28 at the frozen sha and verified in
> Phase 29.** Two seeds **cannot separate a noise effect from seed variance**; only the *direction*
> below is licensed, never a magnitude. No number here may reach `MANUSCRIPT-FINDINGS.md`'s
> published claims, the abstract, or §3.

## Question

E1's headline accuracy ratio was measured at a **single** detection-noise level — the `realistic`
scenario's default of **0.5 px**. BAND-01 exists because a claim quoted over "detection noise"
without a stated domain is unlicensed. Does the ratio actually depend on noise, and how much?

## Method and its self-check

`scenario.noise_std` is overridden before each solve (D-11), so calibration and evaluation
detections track together. Four levels `{0.25, 0.5, 0.82, 1.2}` px × two seeds (43, 44 — both
members of the committed ten, deliberately not anchored on seed 42, which is known pathological
for E1) × eight test depths × two models = 8 cells, 16 solves.

**Shape and key self-check, all passing:** 128 band rows and 192 parameter-band rows exactly as
predicted; four distinct `noise_std` values in both files; and **zero duplicate keys** under
`BAND_KEY_COLUMNS = [seed, noise_std, test_depth_m, model]` and
`PARAMETER_BAND_KEY_COLUMNS = [seed, noise_std, camera, model]`. That last check is the live
confirmation that adding `noise_std` to **both** key lists (the documented departure from D-12's
literal text) was necessary: without it the parameter band would have written 192 rows over 48
distinct keys and `write_experiment_csv` would not have complained.

`experiments/results/` is byte-unchanged — still 160 and 240 rows, no `noise_std` column (D-21).

## Result

Mean `z_rmse_mm` over both seeds and all eight depths:

| `noise_std` (px) | non-refractive | refractive | ratio |
|---|---|---|---|
| 0.25 | 76.35 | 1.02 | **74.6×** |
| 0.50 | 77.36 | 2.05 | **37.7×** |
| 0.82 | 76.76 | 3.54 | **21.7×** |
| 1.20 | 78.06 | 5.77 | **13.5×** |

Per seed, to show how wide the spread is on two seeds alone:

| Seed | 0.25 | 0.50 | 0.82 | 1.20 |
|---|---|---|---|---|
| 43 | 93.4× | 45.3× | 26.5× | 16.6× |
| 44 | 60.5× | 31.4× | 17.9× | 11.2× |

## Findings

1. **The ratio is strongly noise-dependent — it is not a constant of the method.** Across the
   measured range it moves by a factor of ~5.5 (74.6× down to 13.5×). A ratio quoted without its
   noise level is therefore not a well-defined quantity, which is precisely what BAND-01 was
   opened to fix.

2. **The mechanism is asymmetric, and it is the expected one.** The non-refractive baseline is
   **flat** in noise (76.3 → 78.1 mm, ~2%): its error is dominated by model misspecification, and
   detection noise is negligible beside it. The refractive arm scales **nearly linearly** with
   noise (1.02 → 5.77 mm for a 4.8× noise increase). The ratio therefore falls roughly as 1/noise.
   This is what a correctly-specified model versus a misspecified one should look like, and it is
   a point in the method's favour: the refractive model's error is noise-limited, not bias-limited.

3. **The direction is robust to seed even though the magnitude is not.** Both seeds are monotone
   decreasing across all four levels, but they disagree by ~50% at the extreme (93.4× vs 60.5× at
   0.25 px). Two seeds are enough to establish the trend and nowhere near enough to bound it.

4. **The 0.5 px isolator does NOT work as D-13 assumes — the comparison is confounded.** D-13
   records that "the 0.5 px row is the clean `normal_fixed` isolator (the noise axis contributes
   nothing at that level)", the intent being that probe rows at 0.5 px should reproduce the
   committed band. **They do not**, and the reason is not the noise axis:

   - Committed band provenance: `git_sha = 3eb1f4a`, **2026-08-13**.
   - **That sha predates FIX-01 (`fb33db4`) and FIX-02 (`57ac430`), both 2026-08-17** — verified
     with `git merge-base --is-ancestor`.
   - The probe contains both fixes.

   So comparing them compares **two different library versions**, not two noise levels. The
   observed movement confirms this: at 0.5 px the **non-refractive** arm moves by up to 13.22 mm
   (158% relative) while the **refractive** arm moves by at most 0.39 mm (21%) — a 34× asymmetry,
   concentrated in exactly the arm FIX-01 (pinned `water_z`) and FIX-02 (freed interface normal)
   targeted.

   **The noise-axis findings above are unaffected**, because they are measured *within* this probe
   — same library, same seeds, same geometry — and are internally controlled. What is void is only
   the cross-artifact comparison D-13 proposed.

## Net position

**The noise axis works, and it matters.** The ratio is a function of detection noise, falling
roughly as 1/noise because the baseline is bias-limited and the refractive arm is noise-limited.
E1's accuracy claim genuinely needs a stated noise domain; without one it is not a well-defined
number.

**No magnitude here is quotable.** Two seeds, and a library that has moved since the committed
band. Phase 28's ten-seed run at the frozen sha is the sole source for every published number, and
Phase 29 verifies it.

**One correction to carry forward:** D-13's `normal_fixed` isolator cannot be evaluated by
comparing against the committed band, because that artifact predates Phase 23's fixes. If the
isolation is still wanted, it needs both arms produced at the same sha.
