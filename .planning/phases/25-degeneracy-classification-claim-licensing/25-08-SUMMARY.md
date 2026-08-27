# Plan 25-08 Summary — E1 noise-axis two-seed probe

**Requirement:** BAND-01 · **Wave:** 5 · **Executed by:** orchestrator (autonomous: false)
**Completed:** 2026-08-18 · **Tasks:** 3/3
**Scope:** rescoped mid-phase by **D-21** — a probe, not the band of record

## What happened

**Task 1 — registration.** `## Phase 25 additions` appended to the reshaped-artifacts todo,
mirroring Phase 24's form. Its first and most prominent point is the **timing split**: the code
emits `noise_std` as of Phase 25, `experiments/results/` stays at 160/240 rows with no `noise_std`
column through Phase 27, and **640/960 is a Phase 28 expectation no Phase 26 gate may assert**.
Also registers the two new library sidecars (absence must be treated as pass), the `.tex` comment
block, and the three fixed-contract CSVs that must stay byte-identical. Committed at `211214c`
**before** launch; pre-launch state recorded: tree clean, 160 and 240 rows.

**Task 2 — the probe.** `--seeds 43,44 --out .planning/probes/2026-08-18-e1-noise-axis`, launched
detached and unbuffered at `211214c`. Seeds 43 and 44 are both members of the committed ten, so
their rows stay comparable, and deliberately exclude seed 42, which is known pathological for E1.
`--smoke` was **not** used — it switches the scenario to `ideal`, collapses depths to 1.30 m and
flattens the noise list, i.e. it would erase the axis under test.

**Wall clock 44 min** (12:48–13:31), 8 cells / 16 solves, under the ~1.5 h estimate. Nothing
committed while in flight.

**All shape and contract checks passed exactly:**

| Check | Expected | Actual |
|---|---|---|
| `exp1_band.csv` rows | 128 | **128** |
| `exp1_parameter_band.csv` rows | 192 | **192** |
| distinct `noise_std` (both files) | 4 | **4** — {0.25, 0.5, 0.82, 1.2} |
| duplicate keys, `BAND_KEY_COLUMNS` | 0 | **0** |
| duplicate keys, `PARAMETER_BAND_KEY_COLUMNS` | 0 | **0** |
| `experiments/results/` | byte-unchanged | **unchanged, 160/240** |

The zero-duplicate result on the parameter band is the live confirmation that adding `noise_std` to
**both** key lists — the documented departure from D-12's literal text — was necessary.

**Task 3 — MF-22**, written provisional.

## The finding

**The ratio is a function of detection noise**, moving ~5.5× across the measured range:

| `noise_std` (px) | non-refractive | refractive | ratio |
|---|---|---|---|
| 0.25 | 76.35 | 1.02 | 74.6× |
| 0.50 | 77.36 | 2.05 | 37.7× |
| 0.82 | 76.76 | 3.54 | 21.7× |
| 1.20 | 78.06 | 5.77 | 13.5× |

The baseline is **flat** in noise (bias-limited by model misspecification); the refractive arm is
**nearly linear** in it (noise-limited). The ratio therefore falls roughly as 1/noise — which is
what a correctly-specified model versus a misspecified one should look like.

## Deviation / correction found

**D-13's 0.5 px `normal_fixed` isolator does not work as specified.** The probe's 0.5 px rows do
not reproduce the committed band, and the confound is **library version, not noise**: the committed
band's provenance is `git_sha = 3eb1f4a` (2026-08-13), which `git merge-base --is-ancestor`
confirms predates FIX-01 (`fb33db4`) and FIX-02 (`57ac430`), both 2026-08-17. At 0.5 px the
non-refractive arm differs by up to 13.22 mm (158%) against at most 0.39 mm (21%) on the refractive
arm — a 34× asymmetry concentrated in exactly the arm those fixes targeted. Recorded in MF-22 and
the probe FINDINGS. The noise-axis findings are unaffected, being internally controlled within one
probe.

One `detect-secrets` false positive (the provenance sidecar's own `git_sha`) was allowlisted by a
**surgical** single-entry addition to `.secrets.baseline`; a repo-wide rescan was tried, expanded
the baseline from 5 files to 172, and was reverted as too broad to land unreviewed. The two
`e1_benchmark_<model>.json` sidecars trip the same detector and were left untracked.

## What is NOT licensed

Two seeds cannot separate a noise effect from seed variance — the two disagree by ~50% at 0.25 px
(93.4× vs 60.5×). **No magnitude here is publishable**, and no comparison to the published 97–178×
band may be drawn from it (different statistic, different seed count, different library version).
Phase 28's four-level ten-seed run at the frozen sha, verified in Phase 29, is the sole source.
