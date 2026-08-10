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

## Gates

| Gate | Description | Status |
|---|---|---|
| 1 | Section 3 reproduction from the archive (~50 min solve) | pending — plan 21-08 |
| 2 | Checksum, size, extraction layout | **PASS** |
| 3 | CLI tutorial commands run verbatim against the archive | pending — plan 21-08 |
| 4 | Both configs load and validate under v2.0.0 | **PASS** |

**Do not proceed to the publish checkpoint (21-09) until plan 21-08 marks gates 1 and 3
PASS.**
