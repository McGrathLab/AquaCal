---
created: 2026-08-05T00:00:00.000Z
title: Pin opencv-python below 5.0
area: packaging
files:
  - pyproject.toml
  - requirements.txt
  - src/aquacal/calibration/intrinsics.py
---

## Problem

The dependency is currently unbounded above (`opencv-python>=4.6` in both
`pyproject.toml:33` and `requirements.txt:10`), so a fresh install today can
resolve to OpenCV 5.0 and break out of the box.

**Observed failure:** `cv2.fisheye` no longer has the attribute
`CALIB_RECOMPUTE_EXTRINSIC` — the constant was moved in 5.0. It raises an
`AttributeError` at the point of use, not at import.

**Single call site:** `src/aquacal/calibration/intrinsics.py:369-370`

```python
fisheye_flags = (
    cv2.fisheye.CALIB_RECOMPUTE_EXTRINSIC + cv2.fisheye.CALIB_CHECK_COND
)
```

`cv2.fisheye.CALIB_CHECK_COND` on the same line is a likely second casualty —
verify both, not just the one that threw. Note the blast radius is narrow: this
is the only place any `cv2.fisheye.CALIB_*` flag is referenced, and it only runs
for cameras listed in `fisheye_cameras`. The other `cv2.fisheye` uses
(`projectPoints`, `undistortPoints`, `calibrate`) are functions, not constants,
and may well be unaffected — but they are untested on 5.x.

## Solution

1. Change both pins to `opencv-python>=4.6,<5.0`. This is the stopgap and can
   land on its own.
2. Find where the constants moved in 5.0 (top-level `cv2.CALIB_*`, or a renamed
   submodule) and record it here — currently only the symptom is known.
3. Then decide whether 5.x support is worth a follow-up: a getattr-with-fallback
   shim at the one call site may be nearly free, but that only holds if the
   other `cv2.fisheye` functions are also 5.x-clean, which nobody has checked.
4. The pin change touches packaging metadata only, so it lands as a `fix:`
   commit for semantic-release.

## Resolved (2026-08-15, verified at milestone close)

Pinned tighter than this todo asked. Both `pyproject.toml:40` and `requirements.txt:12` now read
`opencv-python==4.13.*` (quick task 260813-clj, commit `fa9ec3a`), not merely `<5.0`.

The tightening was deliberate and is load-bearing: MF-20's single-variable control showed that
OpenCV 4.14 alone moves §3's quantities by up to 1.1e-01, while 4.13 reproduces the Windows
reference at 1.264e-07. A `<5.0` ceiling would have permitted both. The reproduction claims name
the version explicitly.

Residual, tracked in `2026-08-12-isolate-opencv-detection-drift-4-13-vs-4-14.md`: `4.13.*` still
permits both the `.90` and `.92` builds, which both report `cv2.__version__ == 4.13.0`. Any
difference between them is unaccounted for — likely nil, not proven.
