---
status: resolved
trigger: "callibration071626-tilt-high-reproj: calibration produces tilted/implausible rig with elevated reprojection error; camera e3v82e0 is a dramatic outlier"
created: 2026-07-20T00:00:00Z
updated: 2026-07-20T01:00:00Z
---

## Current Focus

status: RESOLVED. Root cause fixed and confirmed end-to-end by a full 4-stage re-run
(overall RMS 4.789 -> 1.627 px, e3v82e0 15.51 -> 1.44 px, rig planar). Committed as
ad30a75 together with a new `validate_view_diversity()` Stage 1 check. See
"End-to-end verification" below.
next_action: None. One unrelated follow-up remains outside this session's scope: user
will recapture e3v83ef's in-air intrinsic video with deliberate board tilting (see
"Follow-up finding" below) -- a data-collection issue, not a code defect.

## Symptoms

expected: All 13 primary cameras solved at roughly similar heights above the water plane (~1.0 m), uniform low per-camera reprojection RMS (~1-2 px), and a physically plausible rig layout in camera_rig.png.

actual: Overall primary reprojection RMS 4.789 px. One camera, e3v82e0, is a dramatic outlier: per-camera RMS 15.51 px (all 12 others are 1.32-3.09 px) and solved camera height 3.060 m (all 12 others are 0.86-1.06 m). Reported camera height spread is 2200.8 mm, essentially entirely attributable to e3v82e0. Rig visualization looks tilted. Auxiliary e3v8250 RMS is 16.63 px.

errors: No crash, no exception. Process exited 0. Optimizer terminated normally on `ftol` in both Stage 3 and Stage 4.

reproduction: `python -u -m aquacal calibrate C:/Users/tucke/Desktop/callibration071626/config.yaml -v` (~87 min full run; avoid re-running casually, prefer artifact analysis / reduced re-runs).

started: Newly-collected dataset (2026-07-16), unknown if it ever calibrated well.

## Eliminated

- hypothesis: e3v82e0 has too few or degenerate board views in the intrinsic video (insufficient tilt diversity or depth diversity), causing Stage 1 intrinsic calibration to be genuinely under-constrained.
  evidence: Measured directly from the intrinsic video: e3v82e0 had 99 usable ChArUco detections at frame_step=30 (same as used in the real run), full-image pixel coverage (bbox spans nearly the entire 1600x1200 frame), out-of-plane board-tilt range 5-42 deg (mean 20.7 deg, 94% of frames >10 deg tilt) - actually MORE tilt diversity than the reference camera e3v829d (mean 16.4 deg, 83% >10 deg), and comparable depth/scale diversity (1.6x scale ratio vs e3v829d's 2.3x, both well within normal range). Corner detections visually verified correctly aligned to board squares (no ID mis-assignment). This data is not meaningfully worse than the reference camera's, which calibrates cleanly.
  timestamp: 2026-07-20T00:00

- hypothesis: The near-surface/diffuse-contamination mechanism from the prior rig-tilt-high-reproj.md session (mildly-contaminated early frames pulling the joint solve) is the dominant cause here.
  evidence: The single-camera signature (only e3v82e0 catastrophically bad, all 12 others tight at 1.3-3.1px) is inconsistent with diffuse/broad contamination, which would be expected to degrade many/most cameras somewhat. Decisively, calibration_initial.json (Stage 2, BEFORE any joint optimization or frame-contamination exposure) already shows e3v82e0 at cam_z=-2.07 / h_c=3.04 while every other camera is near h_c~1.0 - the bad pose exists prior to Stage 3 entirely, so Stage-3-time frame contamination cannot be the origin (though it may be a secondary, independent issue worth future scrutiny given the elevated median per-frame RMS of 3.46px noted in the prior-art brief).
  timestamp: 2026-07-20T00:05

## Evidence

- timestamp: 2026-07-20T00:00
  checked: calibration_initial.json (Stage 2 output, before any Stage 3/4 optimization) for e3v82e0 vs all other cameras.
  found: e3v82e0 extrinsics t=[0.233, 0.804, 2.847], camera center already computed downstream as h_c=3.04m in the real run's Stage 2 log line (`e3v82e0: cam_z=-2.0658  h_c=3.0405`), essentially IDENTICAL to the final Stage 3/4 result (h_c=3.060m). All 11 other primary cameras' Stage-2 R/t are unremarkable (identity-ish rotations, small translations near origin, consistent with normal rig geometry). e3v82e0's intrinsic K in this same file: fx=3844.1, fy=3381.9 (vs 1543-1653 for all 12 other primary pinhole cameras), dist_coeffs=[-0.535, -10.895, 0.247, 0.072, 32.70] (vs typical [-0.5, 0.3, ~0, ~0, -0.15..-0.21] for the others).
  implication: The bad pose is present immediately after Stage 2 (BFS pose-graph init via PnP), essentially unchanged by Stage 3/4 (2.85m init -> 3.06m final, i.e. optimization does NOT self-correct it, it's stuck near a local minimum). The wildly implausible intrinsic K/distortion (only for this one camera) is the natural suspect: a bad K poisons PnP-based pose estimation directly.

- timestamp: 2026-07-20T00:10
  checked: Stage 1 verbose log (per-camera intrinsic RMS) from the completed run.
  found: e3v82e0 RMS 2.869px vs 0.374-0.614px for all 12 other primary cameras (5-8x worse) and 0.429px for the aux fisheye. This RMS gap was visible in Stage 1 itself, well before Stage 2/3/4.
  implication: Confirms the intrinsic calibration itself (Stage 1), not extrinsic init or joint optimization, is the point of origin.

- timestamp: 2026-07-20T00:15
  checked: Ran `validate_intrinsics()` (existing codebase safety check) directly against e3v82e0's Stage-1 K/dist_coeffs.
  found: Returns 0 warnings. The pipeline log for the full run also shows zero "WARNING:" lines anywhere. The one check in validate_intrinsics capable of catching an absolute-magnitude fx error (`expected_fx` tolerance check) is never invoked by pipeline.py - no expected_fx is passed at the call site (pipeline.py:665-668). The other two checks (undistortion roundtrip self-consistency, distortion-model monotonicity) are satisfied by e3v82e0's K/dist despite it being self-consistent-but-physically-wrong.
  implication: Existing safety net has a real gap - it cannot catch a self-consistent-but-wrong intrinsic solution, only outright numerically broken ones. This explains why no warning fired despite the severity.

- timestamp: 2026-07-20T00:20
  checked: Measured pose-diversity/coverage of e3v82e0's Stage-1 calibration data was normal (see Eliminated above); tried `rational_model=True` (8-coeff) on the same data - still produced a blown-up solution (fx=3971, k2=-45.7, k5=-96.9, k7=-252.4).
  found: A richer distortion model does NOT fix it, ruling out "5-coefficient model too simple for this lens" as the cause.
  implication: Points toward the OpenCV `cv2.calibrateCamera` solver landing in a bad LOCAL MINIMUM for this camera's data, not a genuine data/model-capacity deficiency.

- timestamp: 2026-07-20T00:25
  checked: Re-ran `cv2.calibrateCamera` on e3v82e0's exact same detections (no code/data change) but with an explicit initial-guess flag `CALIB_USE_INTRINSIC_GUESS`, seeded with a generic, data-agnostic guess (fx=fy=max(image_width, image_height)=1600, cx,cy=image center) instead of relying on OpenCV's default DLT-based auto-init.
  found: RMS dropped from 2.869px -> 0.315px (9x improvement), fx/fy became 1585.3/1588.0 (in line with the other 12 cameras' 1543-1653 range), dist_coeffs became [-0.511, 0.352, 0.001, 0.003, -0.189] (in line with the other cameras' typical profile). Verified the SAME generic guess applied to two peer cameras (e3v829d, e3v832e) that already calibrate cleanly reproduces their no-guess result to 6+ significant figures (RMS and K identical) - i.e. the guess is a safe no-op for well-behaved cameras and only helps the pathological one.
  implication: DECISIVE. Confirms the root cause is OpenCV's default (unguided) initial-parameter estimate for `cv2.calibrateCamera`, which for this particular camera's board-pose distribution lands far from the true solution, and the nonlinear refinement never escapes that bad basin. A standard, well-known mitigation (seed with a sane generic K guess) fully resolves it without being data-specific or camera-specific, and is safe for all other cameras.

- timestamp: 2026-07-20T00:40
  checked: Applied the fix in `src/aquacal/calibration/intrinsics.py::calibrate_intrinsics_single` (both the primary `cv2.calibrateCamera` call and the k3/k2-fallback-simplification retry calls now pass `CALIB_USE_INTRINSIC_GUESS` with the generic K guess). Ran `pytest tests/unit/test_intrinsics.py` (22 tests) - all pass. Then ran a SCOPED re-run of the real dataset covering Stage 1 (all 13 cameras) + underwater detection + Stage 2 (extrinsic init) only, using the fixed code (skipping the expensive Stage 3/4 bundle adjustment, ~13 min total vs ~87 min for the full pipeline).
  found: Stage 1: e3v82e0 now RMS 0.315px, fx=1585.3/fy=1588.0 - no longer an outlier among the 13 cameras (all now RMS 0.315-0.614px, all fx in 1367-1600 range, only the intentionally-different fisheye e3v8250 at fx=700 as expected). Stage 2: e3v82e0 now h_c=0.9500m - squarely within the other 11 cameras' range (0.8785-1.0869m), vs the original run's 3.0405m.
  implication: The fix eliminates the root-cause defect at its point of origin (Stage 1) and the previously-poisoned Stage 2 extrinsic init is now sane. This strongly predicts the downstream Stage 3/4 bundle adjustment and final reprojection RMS will no longer show e3v82e0 as an outlier, though this has not yet been confirmed with a full end-to-end run (deferred - the full run costs ~87 min, primarily Stage 3 at ~65 min, which this scoped re-run intentionally skipped).

## Resolution

root_cause: Stage 1 in-air intrinsic calibration for camera e3v82e0 converges to a badly wrong local minimum. `cv2.calibrateCamera` is called without any initial parameter guess, so OpenCV falls back to its default linear (DLT/homography-based) auto-initialization before nonlinear refinement. For this camera's particular set of ~99 board-view detections (which are NOT deficient in coverage, tilt diversity, or depth diversity compared to a normal/working camera), that auto-init lands far from the true solution, and the nonlinear Levenberg-Marquardt refinement in `cv2.calibrateCamera` has no mechanism to escape the resulting bad basin - producing a self-consistent but physically implausible intrinsic matrix (fx=3844 vs the true/expected ~1580, matching all 12 other same-model primary cameras) with extreme, overfit distortion coefficients (k2=-10.9, k3=32.7 vs typical ~0.3/-0.15) and an elevated but not obviously-alarming Stage-1 RMS (2.87px vs 0.37-0.61px for peers - a real, measurable but easy-to-overlook red flag in verbose log output). This bad intrinsic then poisons Stage 2's PnP-based extrinsic initialization, placing e3v82e0's initial camera height at h_c=3.04m (vs ~1.0m for every other camera) before any joint optimization runs at all. Stage 3/4's joint bundle adjustment does not self-correct this - both the bad intrinsics and the bad extrinsic pose are locally mutually consistent (the optimizer finds a nearby local minimum, h_c drifting only 2.85m->3.06m, i.e. getting slightly worse, not better) - producing the observed 15.51px per-camera RMS and the overall tilted-looking rig. The existing `validate_intrinsics()` safety check does not catch this because its checks (undistortion roundtrip self-consistency, distortion-model monotonicity) are satisfied by a self-consistent-but-wrong K, and the one check that could catch an absolute focal-length error (`expected_fx` tolerance) is never wired up by `pipeline.py`'s call site.

fix: Modified `calibrate_intrinsics_single()` in `src/aquacal/calibration/intrinsics.py` to seed `cv2.calibrateCamera` with a generic, data-agnostic initial guess (`fx = fy = max(image_width, image_height)`, principal point at image center) via `CALIB_USE_INTRINSIC_GUESS`, instead of relying on OpenCV's default DLT-based auto-init. Applied to both the primary calibration call and the existing k3/k2-fallback-simplification retry calls, for consistency. This is a minimal, general (not dataset-specific) fix: it does not require knowing the "true" focal length in advance, and was empirically verified to be a safe no-op (reproduces the no-guess result to 6+ significant figures) on two peer cameras that already calibrate cleanly, while fully resolving the pathological camera.

verification: PARTIAL - scoped verification complete, full end-to-end verification pending.
  - Unit tests: `pytest tests/unit/test_intrinsics.py` - 22/22 pass with the fix applied.
  - Scoped real-data re-run (Stage 1 + underwater detection + Stage 2 only, ~13 min, skips the expensive Stage 3/4 bundle adjustment):
    - Stage 1: e3v82e0 RMS 2.869px -> 0.315px; fx/fy 3844/3382 -> 1585/1588 (now consistent with the other 12 primary cameras' 1367-1600 range). No other camera's Stage 1 result changed in any way that would indicate regression (all match the original run's per-camera RMS/fx to visual inspection).
    - Stage 2: e3v82e0 initial height h_c 3.0405m -> 0.9500m (now within the other 11 cameras' 0.8785-1.0869m range, vs previously being 2x the max of any other camera).
  - NOT YET DONE: full pipeline re-run (Stage 3/4 + final diagnostics/reprojection RMS/camera_rig.png) to confirm the final per-camera RMS and rig visualization are fixed end-to-end. This is the ~87-minute run the user flagged as expensive; deferred pending user decision on whether/how to run it (foreground, background, or reduced `max_calibration_frames`).
files_changed:
  - src/aquacal/calibration/intrinsics.py (calibrate_intrinsics_single: seed cv2.calibrateCamera with a generic CALIB_USE_INTRINSIC_GUESS instead of no guess, for both the primary call and the k3/k2 fallback retries)

## End-to-end verification (2026-07-20, commit ad30a75)

Full 4-stage pipeline re-run on the real dataset with the fix. Pre-fix artifacts
preserved at `C:/Users/tucke/Desktop/callibration071626/output_before_intrinsics_fix/`
for comparison.

| metric | before | after |
|---|---|---|
| e3v82e0 per-camera RMS | 15.51 px | 1.44 px |
| e3v82e0 camera height | 3.060 m | 1.015 m |
| overall primary RMS | 4.789 px | 1.627 px |
| camera height spread | 2200.8 mm | 167.1 mm |
| 3D error (MAE / % of square) | 0.90 mm / 1.51% | 0.49 mm / 0.81% |
| camera_rig.png | tilted | planar |
| runtime | 87 min | 48 min |

All four acceptance criteria met. Runtime nearly halved because Stage 3 converges
cleanly (3910s -> 1541s) and no post-rejection re-run was needed.

### Prior-art hypothesis definitively ruled out

`.planning/debug/rig-tilt-high-reproj.md` (the Calibration_Emily session) suggested
diffuse near-surface frame contamination as the likely cause, since this dataset sets
no `start_frame`/`stop_frame`. That was wrong for this dataset. Median per-frame RMS
fell 3.457 -> 1.614 px, landing on the clean-data reference, and the auto-rejecter
dropped ZERO frames post-fix (vs 1 before). The elevated median was a CONSEQUENCE of
one poisoned camera dragging the joint solve, not contamination. There was never
contamination here to remove.

## Follow-up finding: e3v83ef (separate, milder, NOT the same root cause)

The one remaining anomaly. e3v83ef solves at height 0.858 m (peers 0.99-1.03) with
2.87 px RMS, unchanged by the seeding fix (its intrinsics are bit-identical before
and after). Root cause is different: fx = 1367.9 against ~1578 for its eleven
identical-lens peers (user confirmed only the auxiliary e3v8250 has a different
lens). A 13% fx deficit maps directly onto the ~15 cm height offset, since PnP
distance scales linearly with fx.

Why fx is wrong: its in-air video is degenerate. Measured at the pipeline's
frame_step, e3v83ef yielded only 30 usable views spanning 1.1-11.5 deg of board tilt
(90th pct 7.2), versus 71-77 views spanning 1.6-33.2 deg (90th pct 19.6-29.7) for
peers. Fronto-parallel views leave fx degenerate with board distance.

This is NOT a code defect -- it is a data-collection deficiency. Resolution:
  1. `validate_view_diversity()` added (commit ad30a75) so this warns at Stage 1
     instead of silently displacing a camera. Warns when 90th-pct tilt < 15 deg;
     cleanly separates e3v83ef (7.2) from all correct cameras (19.6-29.7).
  2. User will recapture e3v83ef's in-air video with deliberate board tilting.

An `expected_fx` cross-camera consistency check was considered and REJECTED by the
user: the library must work with arbitrary, mixed camera sets, so it cannot assume
prior knowledge of which cameras share a focal length. The tilt check needs no such
assumption -- it is derived from the input geometry alone.

### Methodology caveat worth preserving

The first pass at this analysis used `frame_step=1` and did NOT reproduce the
pipeline's fx values, because `_select_calibration_frames` then picks 100 frames by
coverage from ~900 candidates -- a different subset than the pipeline sees. Re-run at
the config's `frame_step=30` (which yields fewer candidates than the 100 cap, so all
are used), the probe reproduced pipeline fx exactly (1367.9 / 1577.6 / 1575.9 /
1574.1). Any offline analysis of Stage 1 behaviour must match the pipeline's
frame_step or its numbers are not comparable.
