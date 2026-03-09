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
