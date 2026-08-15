# OpenCV 4.13 -> 4.14 ChArUco detection drift

**Filed:** 2026-08-12, from the second-machine E2 re-run (MF-20)
**Updated:** 2026-08-12 — the main experiment is **DONE**; only a sub-question remains
**Relates to:** MF-20, MF-19, `2026-08-05-pin-opencv-below-5-0.md`

## Resolved

OpenCV was confirmed as the **entire** cause by a single-variable control
(`experiments/results_linux32gb/e2_cv413/`): the same E2 run on the same machine in a cloned env
differing only in `opencv-python` (4.13.0.92 vs 4.14.0.94).

Under **4.13**, Linux reproduces the Windows reference exactly — all 13 cameras' observation
counts identical (23028, including the fisheye's 3935 that 4.14 lost 348 of), and **1.264e-07**
worst-case relative difference across all 61 numeric diagnostics quantities. Under **4.14** the
same quantities move up to 1.1e-01.

Two consequences, both recorded in MF-20 and `linux32gb_scope.json`:

- The 1.8.0 -> 2.0.1 and Windows -> Linux gaps are **inert on real data**, not just synthetic.
- DATA-01a's undefined tolerance stops mattering: §3 reproduces from the published archive at the
  numerical floor, provided OpenCV is 4.13.

## Still open

**1. Which OpenCV change?** Two routes remain confounded *within* OpenCV:

- `cv2.aruco.CharucoDetector` (`src/aquacal/io/detection.py:64`) changed its corner output, and/or
- `calibrateCamera` produced different Stage-1 intrinsics, fed back into detection via
  `CharucoParameters` (`detection.py:56-61`, called at `:230`).

To separate them, add an arm that pins Stage-1 intrinsics to the archive's
`reference_calibration.json` and re-detects under both versions. This no longer affects any
attribution — it is a mechanism question, worth doing only if the fix needs to be targeted.

**2. ~~Does the pin belong in `pyproject.toml`?~~ RESOLVED 2026-08-13.** It does, and it landed:
`pyproject.toml:40` and `requirements.txt:12` both read `opencv-python==4.13.*` (`fa9ec3a`,
quick task 260813-clj). The decision went to *pinning to reproduce §3* rather than re-baselining
on a current OpenCV. `2026-08-05-pin-opencv-below-5-0.md` is closed.

**3. Packaging-build ambiguity.** PyPI ships both `4.13.0.90` and `4.13.0.92`, and both report
`cv2.__version__ == 4.13.0`, which is all the Windows record stored. The control used `.92`. Any
difference between those two builds is unaccounted for — likely nil, not proven.
