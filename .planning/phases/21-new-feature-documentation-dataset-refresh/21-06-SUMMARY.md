---
phase: 21-new-feature-documentation-dataset-refresh
plan: 06
status: complete
completed: 2026-08-10
requirements: [DATA-01a]
---

# 21-06: Production Frame Extraction

Both extractions ran to completion outside any executor subagent, detached and
unbuffered, per CLAUDE.md's long-run rules. Two defects in plan 21-01's extractor were
found and fixed here before the archive was assembled; both are described below because
each would have shipped silently.

## Interpreter confirmed before launch

```
C:\Users\tucke\anaconda3\envs\AquaCal\python.exe
cv2 4.13.0
```

Git Bash's bare `python` is Anaconda base, where `VideoCapture.read()` returns `None` on
these AVIs and the run would produce 13 empty directories. Confirmed the AquaCal env
first, as the plan requires.

## Task 1 — extrinsic extraction

Smoke test first (13 cameras x 3 frames, exit 0), then:

```
nohup python -u scripts/extract_frames.py \
  --video-dir "C:/Users/tucke/Desktop/Aqua/AquaCal/raw_videos/extrinsics" \
  --out-dir   "C:/Users/tucke/Desktop/Aqua/AquaCal/archive_staging/real-rig/extrinsic" \
  --step 30 > /c/Users/tucke/Desktop/Aqua/AquaCal/extract_extrinsic.log 2>&1 &
disown
```

- Exit code: 0, final log line `TOTAL: 13 cameras, 3406 frames, 3798937145 bytes`
- Wall clock: **61.6 min** (12:27:33 -> 13:29:07)
- 13 directories, **exactly 262 PNGs each**, `frame0000.png`..`frame0261.png`, no gaps
  or misnames in any directory
- Total **3,798,937,145 bytes (3.80 GB)** — inside the 3.0–5.5 GB band
- Spot check: `(1200, 1600, 3) uint8`
- `git status --porcelain` showed no new untracked files (staging is outside the repo)

`CAP_PROP_FRAME_COUNT` is 7860 per extrinsic video; 7860 / 30 = 262 confirms D-09.

## Task 2 — intrinsic extraction

```
nohup python -u scripts/extract_frames.py \
  --video-dir "C:/Users/tucke/Desktop/Aqua/AquaCal/raw_videos/intrinsics" \
  --out-dir   "C:/Users/tucke/Desktop/Aqua/AquaCal/archive_staging/real-rig/intrinsic" \
  --step 30 --per-camera --allow-ragged > /c/Users/tucke/Desktop/Aqua/AquaCal/extract_intrinsic.log 2>&1 &
disown
```

- Exit code: 0, final log line `TOTAL: 13 cameras, 561 frames, 541502452 bytes`
- Wall clock: **9.4 min** (15:15:26 -> 15:24:50)
- Total **541,502,452 bytes (541.5 MB)** — inside the 150–700 MB band
- Ragged by design, and every camera matches its own source length:

| camera | source frames | /30 expected | extracted |
|---|---|---|---|
| e3v8250 (aux fisheye) | 3480 | 116 | 116 |
| e3v829d | 1500 | 50 | 50 |
| e3v82e0 | 1230 | 41 | 41 |
| e3v82f9 | 1020 | 34 | 34 |
| e3v831e | 1020 | 34 | 34 |
| e3v832e | 1320 | 44 | 44 |
| e3v8334 | 1050 | 35 | 35 |
| e3v83e9 | 1020 | 34 | 34 |
| e3v83eb | 1140 | 38 | 38 |
| e3v83ee | 930 | 31 | 31 |
| e3v83ef | 1110 | 37 | 37 |
| e3v83f0 | 990 | 33 | 33 |
| e3v83f1 | 1020 | 34 | 34 |
| **total** | | **561** | **561** |

`--step 30` was left unchanged, as the plan requires: the release run applied
`detection.frame_step: 30` globally.

Staging total: **4.1 GB** across `extrinsic/` and `intrinsic/`.

## Deviation 1 — PNG compression (commit `2132854`)

The extractor called `cv2.imwrite` with no compression parameter. Measured output was
**2.36 MB/frame** against CONTEXT.md D-07's sizing table of **1,205 KB/frame**. Projected
over 262 x 13 that is **8.02 GB**, outside the 3.0–5.5 GB band this plan's own
`<verify>` block asserts — the production run would have taken an hour and then failed
its own acceptance check.

Compression levels 1/3/6/9 were all verified bit-identical on read-back, so this is
size and encode time only, never pixel data. Level 9 measures 1.23 MB/frame, matching
D-07's 1,205 KB almost exactly — evidence the decision was costed at maximum compression
and the implementation simply omitted the parameter. Re-smoked at 1.12 MB/frame,
projecting 3.80 GB; the production run landed at exactly that.

Pinned by a regression test. No round-trip check can catch this — the output was already
lossless and correct, and only file size reveals it.

## Deviation 2 — intrinsic truncation (commit `aeaa29d`)

The first intrinsic run **passed this plan's automated verify** (13 dirs, all non-empty,
387 MB inside the band) while being wrong: every camera returned exactly 31 frames, the
shortest video's count (930/30). Expected 561; produced 403. The auxiliary fisheye
`e3v8250` lost 116 -> 31.

Cause: `VideoSet.frame_count` is `min(counts)` (`io/video.py:87`) and `iterate_frames`
stops there. That is right for the extrinsic rig, whose synchronization is physically
meaningful, and wrong for the intrinsic set, whose recordings are independent.
`calibrate_intrinsics_all` (`intrinsics.py:568-585`) calls `calibrate_intrinsics_single`
per camera, reading each video to its own length — so the release run behind Section 3
saw all 561 frames.

Why nothing caught it:

- `--allow-ragged` relaxes the count *check*, not the iteration. Truncation makes the
  counts uniform, so the guard meant to protect this case had nothing to flag.
- The size band passed: 387 MB sits inside 150–700 MB.
- The existing unit-test double yields `max` frames padded with `None` — more permissive
  than the real `VideoSet` — so no test could expose it.

Had this shipped, the archive would carry a smaller intrinsic set than the calibration
that produced Section 3, with the fisheye at 27% of its frames. It would have surfaced
as a D-15 gate 1 failure after a ~50 minute solve in plan 21-08, or as quietly different
Section 3 numbers with no obvious cause.

Fixed by adding `--per-camera`, which opens one `VideoSet` per video. Added a *faithful*
truncating test double plus tests pinning both modes, so synchronized and per-camera
behaviour stay distinguishable.

## Self-Check: PASSED

- Both extractions exited 0 with `TOTAL:` final lines
- Extrinsic: 13 x 262 = 3406 PNGs, 3.80 GB, no naming gaps
- Intrinsic: 13 dirs, 561 PNGs, 541.5 MB, per-camera counts equal source length / 30
- Repo untouched by both runs
- Neither long run executed inside an executor subagent
