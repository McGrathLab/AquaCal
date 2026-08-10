---
phase: 21-new-feature-documentation-dataset-refresh
plan: 07
artifact: archive-manifest
status: pre-publish
computed: 2026-08-10
---

# 21 Archive Manifest — `real-rig-calib.zip`

Values computed from the final zip bytes and nothing else, **before** any upload.
Plan 21-09's human step transcribes these into Zenodo; plan 21-10 writes them into
`src/aquacal/datasets/data/manifest.json`.

## Transcription values

```
zenodo_filename: real-rig-calib.zip
size_bytes: 4350417815
checksum: md5:729f002c132f88e10224146e5b407a57
zenodo_record_id: TBD — minted in plan 21-09
```

`checksum` is written in the `md5:` prefixed form `download.py` expects.

## Archive contents

Built with `shutil.make_archive(..., root_dir=archive_staging, base_dir='real-rig')`.

- Total entries: **4,007**
- Single top-level entry: **`real-rig`** — required by `loader.py:60`, whose
  `if (_cache_path / name).exists()` branch resolves the nested folder
- Extrinsic PNGs: **3,406** (= 262 x 13)
- Intrinsic PNGs: **561** (ragged by design)

### Top-level listing of the extracted archive

| Entry | Bytes |
|---|---:|
| `README.md` | 2,948 |
| `config_paper.yaml` | 2,466 |
| `config_quickstart_not_paper.yaml` | 2,342 |
| `extrinsic/` (dir) | 3,798,937,145 |
| `intrinsic/` (dir) | 541,502,452 |
| `reference_calibration.json` | 2,226,463 |
| `reference_outputs/` (dir) | 19,070,999 |

### `reference_outputs/` provenance

Each file was **copied** (never moved) and md5-verified source-to-destination. The
repo-side deletion is plan 21-11 and is gated on the publish in 21-09.

| File | Bytes | md5 |
|---|---:|---|
| `calibration.json` | 2,226,463 | `dbb083759a87344721964f5e1f370cc0` |
| `reprojection_residuals.csv` | 1,258,603 | `e374d40d69e65371a7e01b3cfb212c9a` |
| `reconstruction_errors.csv` | 649,854 | `f2838c7d30dbfc0d4347a882e672ff0e` |
| `exp2_spatial_errors.csv` | 11,673,575 | `eb58014dfe75429632ce1f3ba7b0432f` |
| `interface_ablation_conditioning.npz` | 3,259,691 | `54e6f71ccc970c5f274a363881a11046` |
| `diagnostics.json` | 2,813 | `a8448eedb6725681e4f6e362b3df30a5` |
| `reference_calibration.json` (root) | 2,226,463 | `dbb083759a87344721964f5e1f370cc0` |

`reference_calibration.json` is byte-identical to `reference_outputs/calibration.json`;
`load_example` looks for that exact filename at the archive root.

## Gate 2 evidence — checksum, size, extraction layout

Extraction-path assertion, against the scratch extraction of the real zip:

```
C:/Users/tucke/Desktop/Aqua/AquaCal/archive_scratch/real-rig/config_paper.yaml  ->  exists
```

Per-camera extrinsic counts in the **extracted** copy — all 13 directories report
**262**:

```
[262, 262, 262, 262, 262, 262, 262, 262, 262, 262, 262, 262, 262]
```

## Gate 4 evidence — both configs load and validate under v2.0.0

```
$ python -W error::DeprecationWarning -c "
  import os; os.chdir('<scratch>/real-rig')
  from aquacal.calibration.pipeline import load_config
  for name in ('config_paper.yaml','config_quickstart_not_paper.yaml'):
      c=load_config(name)
      print(name,'ok  frame_step=',c.frame_step,' max_calibration_frames=',c.max_calibration_frames,' cameras=',len(c.camera_names))
  "
config_paper.yaml ok  frame_step= 1  max_calibration_frames= 200  cameras= 12
config_quickstart_not_paper.yaml ok  frame_step= 5  max_calibration_frames= 150  cameras= 12
EXIT=0
```

Exit 0 under `-W error::DeprecationWarning` — no deprecation path was exercised for
either config.

**Note on the plan's command.** The plan's gate-4 snippet imports `load_config` from
`aquacal.config`, where it does not exist; the loader is
`aquacal.calibration.pipeline.load_config` (`pipeline.py:194`). The plan anticipated this
by requiring the import path be confirmed first. Corrected here; the gate's intent is
unchanged.

### DATA-01's open question, settled

`interface.initial_water_z` in the shipped configs is a **13-entry per-camera dict, every
value `1.0`** — not a scalar, and not carrying pre-v1.4 physical-gap semantics.

```
type: dict  entries: 13
distinct values: [1.0]
n_water 1.333  n_air 1.0  interface_normal_fixed False
refine_intrinsics True  refine_auxiliary_intrinsics True
robust_loss huber  loss_scale 1.0  holdout 0.2
auxiliary_cameras ['e3v8250']  fisheye_cameras ['e3v8250']
```

The deprecated `initial_distances` shim in `pipeline.py` was **never exercised**: the
literal string appears 0 times in both configs (`grep -c` returns 0 for each), and the
`-W error::DeprecationWarning` run exited 0. This closes the folded 2026-02-24 todo's
question for the shipped archive.

## HALT - gate 1 FAILED

Gate 1 ran on 2026-08-10 against the zip's exact bytes. `num_comparisons` is **exactly
7762** — the frameset is right — but **eight of the nine quantities miss the declared
>= 4 significant figure requirement**, by 1.8% to 13.6%.

Run: `python -u -m aquacal calibrate config_paper.yaml -v`, exit 0, 53 min
(15:44:13 -> 16:37:13), from `gate1_scratch/real-rig/` (extracted from
`real-rig-calib.zip`, not from the staging tree). `git_sha` held at `71d1145` for the
whole run; `n_frames_holdout` = 52.

| # | Quantity | Fresh run | Reference (§3) | Delta % | Verdict |
|---|---|---:|---:|---:|---|
| 1 | mean primary reprojection_rms (px) | 0.824039 | 0.878634 | -6.2137 | FAIL |
| 2a | min primary rms [`e3v829d` / `e3v829d`] | 0.553718 | 0.539376 | +2.6590 | FAIL |
| 2b | max primary rms [`e3v83f0` / `e3v83f0`] | 2.081551 | 2.407876 | -13.5524 | FAIL |
| 3 | aux `e3v8250` reprojection_rms (px) | 14.856381 | 15.134315 | -1.8364 | FAIL |
| 4 | reconstruction.mean (m) | 0.000258 | 0.000268 | -3.7209 | FAIL |
| 5 | reconstruction.rmse (m) | 0.000628 | 0.000674 | -6.8146 | FAIL |
| 6 | reconstruction.percent_error | 0.430295 | 0.446925 | -3.7209 | FAIL |
| 7 | reconstruction.num_comparisons | 7762 | 7762 | 0.0000 | **PASS (exact)** |
| 8 | camera_heights.water_z (m) | 1.073840 | 1.030555 | +4.2002 | FAIL |
| 9a | min camera height [`e3v83f0` / `e3v83e9`] | 1.047177 | 1.008284 | +3.8573 | FAIL |
| 9b | max camera height [`e3v83ee` / `e3v83f1`] | 1.112502 | 1.081528 | +2.8639 | FAIL |

Note rows 9a/9b: the **identity** of the extreme-height camera changed, not just the
value.

### The plan's three hypotheses are ruled out by evidence

1. **Wrong `frame_step` in an extraction** — ruled out. Extrinsic: `CAP_PROP_FRAME_COUNT`
   7860 / 30 = 262, and all 13 directories hold exactly 262 with no naming gaps.
   Intrinsic: every camera's count equals its own source length / 30 (561 total).
   Decisively, `num_comparisons` is an integer count and lands exactly on 7762 — the
   frameset-sensitive quantity is correct.
2. **Camera-order difference in `config_paper.yaml`** — ruled out. Verified equal to
   `release_calibration/config.yaml` element-for-element, in order (the transposition
   exists only in the *previously published* archive config, which was not used).
3. **Missing or extra frame in a camera directory** — ruled out, same evidence as 1.

### Leading hypothesis: library drift, not archive defect

`reference_outputs/diagnostics.json` is dated **2026-02-19** and was produced by a
release-era library (around `v1.4.2`). The fresh run is `aquacal_version 1.8.0`,
`git_sha 71d1145`.

Structural proof the reference predates the current library: the reference JSON has **no
`frame_rejection`, `discard_stats` or `timings` keys at all** — those blocks did not
exist when it was written. The key sets are otherwise identical.

There have been **55 commits to `src/aquacal/calibration/` and `src/aquacal/core/` since
2026-06-01**, at least one of which is an optimizer-correctness fix that must move these
numbers:

- `7e0cb90 fix(calibration): keep a gradient where the refractive model cannot project` —
  `compute_residuals` had replaced a failed refractive projection with the **constant
  100.0 px**, which has identically zero derivative, so every clamped observation
  contributed no gradient. Stage 3 could report success via `xtol` while sitting at a
  bad point.

The direction of the deltas is consistent with this: the fresh run has **lower**
reprojection RMS (0.824 vs 0.879), lower reconstruction error (0.258 vs 0.268 mm) and a
markedly lower worst-camera RMS (2.08 vs 2.41). `water_z` moves +4.2%, which is a
geometry shift rather than an accuracy improvement and should not be characterised as
"better" without further work.

**This is stated as a hypothesis, not a conclusion.** It is supported by the structural
key difference and the commit history, but has not been demonstrated causally.

### The decisive test (not yet run)

Run `config_paper.yaml` against **this same archive** using the release-era library
(~`v1.4.2`, the state as of 2026-02-19) and compare against §3:

- If it reproduces all nine to >= 4 significant figures, the archive is vindicated and
  the entire discrepancy is library drift. The decision then belongs to the user: publish
  the archive and reconcile §3 against the current library, or pin the reproduction
  version.
- If it does **not** reproduce §3, the cause is in the archive or the config and this
  hypothesis is wrong.

Cost: one ~50 minute solve. `gate1_scratch/` has been left in place for it.

### What was NOT done, per D-16

- The tolerance was **not** widened.
- §3 was **not** edited to match what the archive produces.
- Plan 21-09 was **not** started. No DOI has been minted.

## Gates

| Gate | Description | Status |
|---|---|---|
| 1 | Section 3 reproduction from the archive (~50 min solve) | **FAIL — see HALT above** |
| 2 | Checksum, size, extraction layout | **PASS** |
| 3 | CLI tutorial commands run verbatim against the archive | blocked by gate 1 |
| 4 | Both configs load and validate under v2.0.0 | **PASS** |

**Do not proceed to the publish checkpoint (21-09). Gate 1 is FAIL and a minted DOI
cannot be withdrawn.**
