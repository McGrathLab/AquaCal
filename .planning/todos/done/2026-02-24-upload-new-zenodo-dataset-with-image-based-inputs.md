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

## Disposition

Folded into the "Post-Review Updates" milestone as **Task Group F** (dataset
refresh + tutorial re-execution), scheduled after all code work so the published
artifacts reflect final behavior. Do not action this todo standalone — it now
carries a sequencing constraint relative to E6 and E7. Close it when F lands.

## Findings (2026-07-27) — SCOPE EXPANDED, now a publication blocker

Phase 19.1's E2 re-run established that **this todo's scope was too narrow**. It was written
as a config-hygiene item (`initial_distances` → `initial_water_z`). It is now also a
**frameset** problem, and that part blocks publication.

`Desktop\Aqua\AquaCal\release_calibration\diagnostics.json` is the exact source of every
manuscript §3 real-rig number — all nine reconcile to 4+ significant figures. The **published
Zenodo archive is not that run.** It is a ~4.3× frame-subsampled extraction of the same source
videos:

| Run | Usable frames | Validation frames | Comparisons |
|---|---|---|---|
| Release calibration (produces §3) | ~260 | 52 | **7,762** |
| Published Zenodo archive | 60 | 12 | 1,817 |

Ratio check: 7762/1817 = 4.27, 52/12 = 4.33.

So a reader who follows the published reproducibility path gets materially different numbers
from the ones in the paper. That is the same class of error as the two hand-carried numbers
already in publications — the failure "one number, one origin" exists to prevent.

**Consequence for closing this todo:** re-uploading with only the corrected `config.yaml` is
NO LONGER SUFFICIENT. The new archive must carry the full frameset. Source videos are on disk
at `Desktop\Aqua\AquaCal\raw_videos\{intrinsics,extrinsics}\*.avi` (13 + 13), with the
producing config at `release_calibration\config.yaml` (`frame_step: 30`,
`max_calibration_frames: 200`, `holdout_fraction: 0.2`, `refine_intrinsics` and
`refine_auxiliary_intrinsics` both true).

Tracked as **DATA-01a** in `REQUIREMENTS.md` and Phase 21 success criterion **2a** in
`ROADMAP.md`. Full analysis:
`.planning/phases/19.1-experiment-suite-consolidation/19.1-E2-FRAMESET-PROVENANCE.md`.

Sequencing constraint from the earlier finding still holds — do not action standalone; it
lands with Phase 21's DATA group.

## Resolved (2026-08-15, verified at milestone close)

Done by Phase 21 (DATA-01/01a/01b/02). `src/aquacal/datasets/data/manifest.json` now carries
`zenodo_record_id: 21889922`, `checksum: md5:dff1012fb772d627e0f3f106d5c6de84` and
`size_bytes: 4350418046` — all three updated together, none of them the 2026-02-14 values this
todo was filed against. The archive was published as a **new version** of record 18645385 so the
concept DOI and citation lineage survive (version DOI `10.5281/zenodo.21889922`).

It went further than this todo asked: the archive was regenerated from the **full** frameset
(13 x 262 extrinsic PNGs, not the ~4.3x subsampled extraction), so a fresh
`load_example("real-rig")` reproduces §3's `reconstruction.num_comparisons = 7762`. Verified end
to end from a genuinely cold cache. Detail in `.planning/milestones/v2.0-ROADMAP.md` Phase 21 and
`21-ARCHIVE-MANIFEST.md`.

Note the `initial_distances` compat shim in `pipeline.py` is now *unblocked* by this but is
still in the tree — retiring it is CLEAN-01, a separate breaking change.
