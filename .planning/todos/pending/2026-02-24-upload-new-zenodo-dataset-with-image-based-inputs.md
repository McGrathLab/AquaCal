---
created: 2026-02-24T22:29:13.552Z
title: Upload new Zenodo dataset with image-based inputs
area: docs
files:
  - docs/tutorials/aquacal_data/real-rig/real-rig/config.yaml
  - src/aquacal/datasets/download.py
  - src/aquacal/datasets/data/manifest.json
---

## Problem

The real-rig dataset on Zenodo needs to be re-uploaded with the corrected `config.yaml`:
- `initial_distances` (deprecated) replaced with `initial_water_z: 1.0` (scalar)
- Config now matches current `load_config()` spec

The 01_full_pipeline notebook's zenodo path now runs calibration from scratch via
`run_calibration()` instead of loading a reference calibration. The dataset ZIP on
Zenodo must contain the updated config so fresh downloads work out of the box.

Additionally, `manifest.json` checksum/size may need updating after re-upload, and
the Zenodo record URL/DOI in `download.py` may change if a new version is created.

## Solution

1. Create a new ZIP of `docs/tutorials/aquacal_data/real-rig/real-rig/` with the updated config
2. Upload to Zenodo as a new version of the existing record
3. Update `manifest.json` with new checksum, size, and URL if changed
4. Verify `load_example("real-rig")` downloads and extracts correctly

## Findings (2026-07-23)

**Still open — confirmed not uploaded.** Zenodo record 18645385 shows
`real-rig-calib.zip` with md5 `c66380aaa8cbca6bc04a3157baacbee8`, identical to
the value written into `manifest.json` on 2026-02-14 (commit `5eba1d8`) and never
changed since. That is byte-for-byte the original upload, predating this todo by
ten days.

**Severity is lower than the problem statement implies.** `pipeline.py:257` has a
backward-compatibility branch for `initial_distances` whose behavior is identical
to the `initial_water_z` branch — same positivity validation, same scalar/dict
handling, same resulting per-camera dict. Verified by reconstructing the shipped
config (local copy with the key swapped back) and calling `load_config()`: it
loads, expands to 1.0 across all 13 cameras, and emits one deprecation
`UserWarning`. `load_example("real-rig")` is not broken.

So this is a hygiene item, not a bug. Two consequences worth keeping in view:

- The compat shim in `pipeline.py` cannot be removed until the dataset is
  re-uploaded, or `load_example("real-rig")` breaks for real.
- One thing remains unverified: whether the shipped `initial_distances` is the
  scalar `1.0` (harmless) or a per-camera dict carrying pre-v1.4 *physical gap*
  semantics. The loader would silently reinterpret such values as water-surface Z.
  Settling this needs one download of the record, or is moot once re-uploaded.
