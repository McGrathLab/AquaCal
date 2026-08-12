# Isolate the OpenCV 4.13 -> 4.14 ChArUco detection drift

**Filed:** 2026-08-12, from the second-machine E2 re-run (MF-20)
**Relates to:** MF-20, MF-19, `2026-08-05-pin-opencv-below-5-0.md`

## What we know

Re-running E2 against the published archive on 32 GB Linux lost **450 corner observations**
(23028 -> 22578, -1.95%) versus the archive reference, concentrated in the auxiliary fisheye
`e3v8250` (-348, -8.84%) while four primaries lost none. Accuracy moved 1.1% (`reprojection.rms`)
to 10.8% (`reconstruction.signed_mean`).

MF-20 closes off every alternative explanation:

- not downstream rejection (discard counters moved only -4/-6)
- not aquacal's detection code (`git diff 6c7f930b d27bda7 -- src/aquacal/io/detection.py` empty)
- not the 1.8.0 -> 2.0.1 gap, and not the platform (E4 crossed both, reproduced to 1e-13)
- not the video -> image frame source (MF-19's fixed-library control, 1e-6%)
- not run-to-run noise (~1e-09 between two Linux E2 runs)

That leaves **OpenCV 4.13.0 -> 4.14.0**.

## What is still open

Two routes are confounded *within* OpenCV and were not separated:

1. `cv2.aruco.CharucoDetector` (`src/aquacal/io/detection.py:64`) changed its corner output, and
2. `calibrateCamera` produced different Stage-1 intrinsics, which are fed back into detection via
   `CharucoParameters` (`detection.py:56-61`, called at `:230`).

## Proposed experiment

Run E2 twice on THIS machine, varying only the OpenCV version (4.13.0, then 4.14.0), everything
else pinned. ~22 min per run plus env setup. Compare per-camera observation counts against the
tables in MF-20.

To separate route 1 from route 2, add a third arm that pins Stage-1 intrinsics to the archive's
`reference_calibration.json` and re-detects — isolating the detector from the intrinsics it
consumes.

## Why it matters

Real-rig reproducibility claims currently cannot name a version boundary. If the drift is the
detector, an OpenCV floor/ceiling belongs in `pyproject.toml` alongside the existing
pin-below-5.0 todo, and any §3 reproduction instruction must state an OpenCV version.
