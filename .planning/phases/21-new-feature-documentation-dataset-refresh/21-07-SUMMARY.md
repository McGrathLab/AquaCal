---
phase: 21-new-feature-documentation-dataset-refresh
plan: 07
status: complete
completed: 2026-08-10
requirements: [DATA-01, DATA-01b, DATA-02]
---

# 21-07: Archive Assembly and D-15 Gates 2 & 4

One archive now carries both configs, the full frameset, and the paper run's own
reference outputs. Its md5 and byte size were computed from the final zip bytes before
any upload, and recorded in `21-ARCHIVE-MANIFEST.md`. Gates 2 and 4 are PASS; gates 1
and 3 remain for plan 21-08.

Interpreter confirmed before every step: `C:\Users\tucke\anaconda3\envs\AquaCal\python.exe`,
cv2 4.13.0. All multi-gigabyte steps ran outside any executor subagent, detached and
unbuffered.

## Task 1 — configs and README

`config_paper.yaml` is `release_calibration/config.yaml` with only the required changes:
26 relative image directories (`extrinsic/<camera>/`, `intrinsic/<camera>/`),
`output_dir: output`, and `detection.frame_step: 1` (the frames on disk are already
every-30th, D-09).

Verified against the release config:

- `cameras` list equal element-for-element, in order
- `max_calibration_frames: 200`, `refine_intrinsics: true`,
  `refine_auxiliary_intrinsics: true`, `robust_loss: huber`, `loss_scale: 1.0`,
  `holdout_fraction: 0.2`, `n_water: 1.333`, `n_air: 1.0`, `normal_fixed: false`
- `initial_water_z`: 13-entry mapping, every value `1.0`
- `initial_distances` appears **0 times** in both configs
- All 26 path values relative; **no `C:` and no `.avi` anywhere** (T-21-07-02)

`config_quickstart_not_paper.yaml` is the same file with `frame_step: 5` and
`max_calibration_frames: 150`. First line reads
`# QUICKSTART CONFIG -- the numbers this produces do NOT reproduce the paper's Section 3.`

`README.md` is 66 lines, names both configs, and carries no DOI or record-id literal —
21-09 mints those.

### Camera-order divergence confirmed (T-21-07-04)

The plan flagged that the currently *published* archive config transposes two cameras
against the release config. Verified:

```
release  : [e3v829d, e3v82e0, e3v82f9, e3v831e, ...]
published: [e3v829d, e3v82f9, e3v82e0, e3v831e, ...]
diff at positions 1 and 2
```

`config_paper.yaml` uses the **release** order. The reference camera at position 0
(`e3v829d`) is the same in both, so the world origin is unaffected — the transposition is
real but not origin-shifting.

## Task 2 — reference outputs, zip build, scratch extraction

All six reference outputs were **copied**, never moved, and each md5-verified
source-to-destination; `git status --porcelain` was clean afterwards, confirming nothing
left `experiments/results/` (T-21-07-03 — that deletion is plan 21-11's and is gated on
the publish). Per-file md5 and byte sizes are recorded in `21-ARCHIVE-MANIFEST.md`
(T-21-07-05).

`reference_calibration.json` at the archive root is byte-identical to
`reference_outputs/calibration.json` (md5 `dbb0837...`), which is the filename
`load_example` looks for.

Zip build (`shutil.make_archive`, detached): exit 0, launched 15:26:41, complete by
15:28 — under 2 minutes, as expected since PNG is already deflated.

```
md5        729f002c132f88e10224146e5b407a57
size_bytes 4350417815
```

Zip shape: **4,007 entries**, single top-level `real-rig`, **3,406** extrinsic PNGs
(262 x 13), **561** intrinsic PNGs, 4.35 GB — inside the 3.5–5.5 GB band and landing
almost exactly on D-10's predicted ~4.4 GB.

Scratch extraction (detached): exit 0, `<scratch>/real-rig/config_paper.yaml` present.

## Task 3 — gates 2 and 4

**Gate 2 PASS.** Extraction resolves to the nested layout `loader.py:60` expects. All 13
extrinsic directories report 262 PNGs in the extracted copy. Top-level listing with
per-entry sizes is in the manifest.

**Gate 4 PASS.** Both configs load under `-W error::DeprecationWarning` with exit 0:

```
config_paper.yaml ok  frame_step= 1  max_calibration_frames= 200  cameras= 12
config_quickstart_not_paper.yaml ok  frame_step= 5  max_calibration_frames= 150  cameras= 12
```

### DATA-01's open question, settled

`interface.initial_water_z` ships as a **13-entry per-camera dict, every value `1.0`** —
not a scalar, and not carrying pre-v1.4 physical-gap semantics. The deprecated
`initial_distances` shim was **never exercised**: the literal appears 0 times in both
configs and the `-W error::DeprecationWarning` run exited 0. This closes the folded
2026-02-24 todo's question for the shipped archive.

### Deviation — the plan's gate-4 import path was stale

The plan's snippet imports `load_config` from `aquacal.config`, where it does not exist;
the loader is `aquacal.calibration.pipeline.load_config` (`pipeline.py:194`). The plan
anticipated this risk by requiring the import path be confirmed first. Corrected; the
gate's intent and strictness are unchanged. The plan's field names `c.cameras` and
`c.frame_step` are likewise `c.camera_names` and `c.frame_step` on `CalibrationConfig`.

## Task 4 — scratch deletion

Precondition asserted first: `grep -c 'checksum: md5:'` on the manifest returned 1, so
the gate evidence was durably recorded before its source was removed. Deletion ran
detached from 15:32:18.

Post-conditions verified: `archive_scratch` gone; `real-rig-calib.zip` still present with
`os.path.getsize` equal to the manifest's `size_bytes` (4350417815); `archive_staging/real-rig/`
intact with both subtrees; repo clean. Free disk after: 36 GB.

## Self-Check: PASSED

- One archive holds both configs, the full frameset and the run's own reference outputs
- The fast config's filename and first line both say its numbers do not reproduce the paper
- Both configs load and validate under v2.0.0 semantics — gate 4
- The zip extracts to the nested layout `loader.py:60` resolves — gate 2
- md5, size_bytes and zip name were computed and written down before any upload
- Every multi-GB step ran outside an executor subagent

**Gates 1 and 3 are NOT satisfied here. Do not proceed to 21-09 until 21-08 marks them PASS.**
