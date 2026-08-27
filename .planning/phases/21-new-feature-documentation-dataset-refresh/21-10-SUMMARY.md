---
phase: 21-new-feature-documentation-dataset-refresh
plan: 10
status: complete
completed: 2026-08-11
requirements: [DATA-02]
---

# 21-10: The library points at the published archive — DATA-02 closed

Commit `25655f7`. `manifest.json` is the single seam between the published archive and every
consumer, and all three of its pointer fields moved together. The whole download path was
then proved end to end from a genuinely cold cache — the one D-15 check that could not run
before publication, because a Zenodo draft is not publicly downloadable.

## Task 1 — `manifest.json`

`git show 25655f7 -- src/aquacal/datasets/data/manifest.json` changes exactly four lines, and
`manifest.json` is the only file under `src/` in the commit:

| Field | Before | After |
|---|---|---|
| `zenodo_record_id` | `18645385` | `21889922` |
| `checksum` | `md5:c66380aaa8cbca6bc04a3157baacbee8` | `md5:dff1012fb772d627e0f3f106d5c6de84` |
| `size_bytes` | `164023590` | `4350418046` |
| `description` | "9+ camera production rig — download from Zenodo" | "13-camera production rig (12 primary + 1 auxiliary fisheye) — download from Zenodo" |

`zenodo_filename` stayed `real-rig-calib.zip` — Zenodo lists that exact name, so the tutorial
and every consumer that assumes it are unaffected. `version`, `type` and `included` untouched.
The `md5:` prefix is retained because `download_with_progress` parses the `algorithm:hash`
form. No library code changed: `loader.py`, `_manifest.py` and `download.py` were already
generic, exactly as the plan predicted.

The three values are read from `21-ARCHIVE-MANIFEST.md` and nowhere else, and the description
change is the reason the diff is four lines rather than three.

## Task 2 — cold-cache end-to-end verification

**Genuinely cold.** The stale 354 MB cache was deleted first, so this exercised the real
path: HTTP fetch of the full 4.35 GB from the live record, md5 validation against the newly
written manifest value, and extraction.

Cache root is `C:\Users\tucke\PycharmProjects\AquaCal\aquacal_data`. The archive extracts to
the nested layout that `loader.py:60`'s `if (_cache_path / name).exists()` branch resolves —
`aquacal_data/real-rig/real-rig` — so the resolved `cache_path` ends in `real-rig` as
required.

Contents confirmed on disk:

| Check | Result |
|---|---|
| `extrinsic/` camera directories | **13** |
| Extrinsic PNGs | **3,406** (= 262 x 13) |
| Intrinsic PNGs | **561** (ragged by design) |
| `config_paper.yaml`, `config_quickstart_not_paper.yaml` | both present |
| `README.md`, `reference_calibration.json`, `reference_outputs/diagnostics.json` | all present |
| `reference_calibration.json` | parses into a `CalibrationResult` |

The shipped `diagnostics.json` and `reference_calibration.json` both report
`water_z 1.0738404142952647` — the archive this phase built, not a stale one.

**DATA-02's reworded acceptance** — both real consumers resolve the same directory: the CLI
tutorial's `config_paper.yaml` sits at the resolved `cache_path`, and
`experiments/e2_real_rig.py`'s default `load_example("real-rig")` resolves there too. **E2
itself was not run** — it is a ~50 minute calibration and out of this phase's scope.

Measured download throughput was **~1.4 MB/s, about 50 minutes** for the archive. Reported as
measured; no runtime is attributed to any code change.

## Follow-up, deliberately not fixed here

**`download_with_progress` has no HTTP Range/resume support.** Any interruption restarts the
transfer from zero. This was invisible when the archive was 164 MB and is material at 4.35 GB
with a ~50 minute window. The user reviewed it and explicitly deprioritised it as "a
convenience". It is recorded here as deferred work against the download path, **not as a
defect of this plan** — the plan's job was to point the manifest at the published record and
prove the path works, and it does.

## Deviation — the manifest evidence is not under a `## Post-publish verification` heading

The plan asked for a `## Post-publish verification` section appended to
`21-ARCHIVE-MANIFEST.md`. `25655f7` instead folded the post-publish evidence into the
**PUBLISHED 2026-08-11** block at the top of the transcription values (the live-API size/md5
confirmation and the `HEAD` check), and put the cold-cache evidence — deleted stale cache,
full 4.35 GB download, md5 pass, nested-layout extraction, 13/3406/561, the `water_z` value,
the ~1.4 MB/s throughput — in the commit message rather than in the document. Every fact the
section was supposed to carry exists and is durable; it is split across two places instead of
one, and a reader of `21-ARCHIVE-MANIFEST.md` alone will not find the cold-cache numbers.

## Consequence picked up by the next plan

`tests/unit/test_datasets.py::test_manifest_loading` hardcoded `zenodo_record_id == 18645385`
and this commit broke it. The full suite had already completed before `25655f7` landed, so
nothing caught it here. Plan 21-11 fixed it and, while doing so, widened the assertion to pin
record id, checksum and size together — silent drift in any one of them means `load_example`
fetches the wrong archive.

## Self-Check: PASSED

- `25655f7` exists and touches exactly `manifest.json` plus `21-ARCHIVE-MANIFEST.md`
- `src/aquacal/datasets/data/manifest.json` now reads `21889922` /
  `md5:dff1012fb772d627e0f3f106d5c6de84` / `4350418046`, all three matching the published record
- `aquacal_data/real-rig/real-rig` holds 13 extrinsic camera directories, 3,406 extrinsic PNGs,
  561 intrinsic PNGs, both configs, `README.md`, `reference_calibration.json` and
  `reference_outputs/`
- Shipped `water_z` is `1.0738404142952647`
