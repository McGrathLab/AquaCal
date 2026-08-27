---
created: 2026-08-12T00:00:00.000Z
title: Name (and pin) the OpenCV version wherever real-rig reproduction is claimed
area: packaging
files:
  - pyproject.toml
  - requirements.txt
  - docs/tutorials/01_full_pipeline.ipynb
  - src/aquacal/datasets/loader.py
  - experiments/README.md
---

## Problem

MF-20 (2026-08-12, branch `experiments/linux32gb-rerun`) established that the real-rig
numbers move with the **OpenCV version**, not just the AquaCal version. Re-running E2
against the published Zenodo archive on a second machine moved:

| quantity | archive ref (aquacal 1.8.0, OpenCV 4.13.0) | re-run (2.0.1, OpenCV 4.14.0) |
|---|---:|---:|
| `reprojection.rms` (px) | 0.92766 | 0.93827 (+1.14%) |
| `reconstruction.rmse` (m) | 6.2814e-04 | 6.7718e-04 (+7.81%) |
| `reconstruction.signed_mean` (m) | 4.3189e-05 | 4.7840e-05 (+10.8%) |
| aux `e3v8250` RMS (px) | 14.856 | 13.970 |
| `num_comparisons` | 7762 | 7762 (0.00%) |

**The mechanism is upstream of the solver.** Corner observations fell 23028 -> 22578
(-1.95%), concentrated in the auxiliary fisheye `e3v8250` (-348, -8.84%); four primaries
lost none. Downstream discard counters moved only -4/-6, so the loss is at *detection*,
not rejection.

**CONFIRMED by single-variable control (2026-08-12, `27c80e7`, `results_linux32gb/e2_cv413/`).**
The same E2 run on the same machine in a cloned env differing *only* in OpenCV
(4.13.0.92 vs 4.14.0.94) reproduces the Windows reference **exactly** under 4.13:
observations back to 23028 including the fisheye's 3935, and every one of the 61
diagnostics quantities within 1.26e-07 (worst). Verified independently against the
committed `experiments/results/real_rig_metrics.json`: all eight Section 3 quantities
agree to <=4.7e-09 relative.

So the attribution is no longer an elimination argument — it is a controlled experiment,
and it has a second, larger consequence: **holding OpenCV fixed, the 1.8.0 -> 2.0.1
library gap and the Windows -> Linux platform change are inert on real data, through the
full pipeline including detection.** Previously that was demonstrable only on E4's
synthetic cells, which never call the detector.

`detection.py:64` constructs `cv2.aruco.CharucoDetector` directly, so the corner output is
entirely OpenCV's.

**Why this needs an action rather than just a note.** Three artifacts are a matched set
behind a published DOI — the SoftwareX manuscript's Section 3, the Zenodo archive's
`reference_outputs/`, and the tutorial's expected-value table. All three currently invite
a reader to reproduce numbers that a routine `pip install` will not reproduce, because
nothing anywhere states which OpenCV produced them. The tutorial check is the sharpest
edge: it presents an expected-value comparison that now fails on a fresh environment for
a reason the reader cannot diagnose.

## Solution

Two independent pieces. (1) is the honest disclosure and is worth doing regardless;
(2) is the stronger guarantee and is a judgement call.

The control simplifies this considerably. **OpenCV is the only version that needs naming
or pinning** — the library version, OS, platform, NumPy and SciPy are all measured inert.
The claim to make is therefore short and strong: *reproducible from the archived dataset
with OpenCV 4.13*, without further hedging.

1. **State the OpenCV version wherever a real-rig number is claimed as reproducible.**
   - `experiments/README.md` §3 (the two E2 invocation paths) — the reference numbers
     were produced under **OpenCV 4.13.0**.
   - The tutorial's expected-value table — say which OpenCV the expected values came from,
     and that a different minor version can move them at the ~1-10% level without anything
     being wrong.
   - Anywhere `load_example("real-rig")`'s `reference_outputs/` is described as
     reproducible.
   - Every `benchmark.json` already records `opencv_version` in its `environment` block,
     so the machine-readable half is done — this is about the prose that points at it.

2. **Decide whether to tighten the dependency pin.** Currently `opencv-python>=4.6,<5.0`
   in both `pyproject.toml:33` and `requirements.txt` — the `<5.0` half of
   `2026-08-05-pin-opencv-below-5-0` has landed; that todo remains open for its
   constants-relocation research and is **not** superseded by this one.
   The tradeoff is real and should not be resolved by reflex:
   - A tight pin (e.g. `==4.13.*`) makes the published numbers reproducible by
     construction, at the cost of forcing a specific minor on every downstream consumer
     and going stale quickly.
   - A loose pin keeps the library easy to install and honest about the fact that
     detection is a moving floor.
   - A middle option: leave the runtime pin loose, and add a pinned **reproduction
     environment** (a lockfile or a documented `pip install opencv-python==4.13.0`) used
     only by the tutorial and the E2 reference path.
   The middle option is the recommendation — the reproduction claim is what needs
   pinning, not the library.

3. **Optional, low value, explicitly not required:** isolate whether the 4.14 change is
   `CharucoDetector` itself or `calibrateCamera` feeding different Stage-1 intrinsics back
   into detection (`detection.py:56-61`, called at `:230`). This is now purely internal to
   OpenCV and **affects no attribution and no manuscript claim** — do it only if 4.14
   support becomes a goal. See `.planning/debug/`'s OpenCV isolation note on the
   `experiments/linux32gb-rerun` branch.

## Do not

- Do not describe either OpenCV version's output as more correct. 450 corners were not
  detected; nothing measured says which run detected the right set.
- Do not "fix" the numbers by re-running E2 and updating the archive. The DOI is
  published, and Section 3 / `reference_outputs/` / the tutorial table must move together
  or not at all. The manuscript decision (2026-08-12) is to **keep the published numbers
  and name the environment** — this todo implements the library half of that decision.
