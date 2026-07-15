---
status: awaiting_human_decision
trigger: "rig-tilt-high-reproj: after aquacal calibrate on Calibration_Emily dataset, rig visualization shows tilt out of plane and bimodal reprojection error across cameras"
created: 2026-07-14T00:00:00Z
updated: 2026-07-14T00:00:00Z
---

## Current Focus

hypothesis: Option B pose-source fix WORKS (correctly caught & dropped the catastrophic training frame 30), but Option B does NOT fully fix THIS dataset's tilt. Root cause: the tilt is driven by a CONTIGUOUS EARLY SEGMENT of MILDLY-contaminated near-surface/rippled frames (2-4px each) that overlap legitimate noisy frames in reprojection RMS and cannot be separated by any safe RMS threshold. Only removing the whole early segment (Option A / start_frame) fixes it.
test: DONE - re-verification run output_autoreject2 complete.
expecting: n/a.
next_action: STOP + CHECKPOINT (per instructions: does-not-match -> report + propose tuning, do NOT commit Option B). Option B stays UNCOMMITTED on working tree pending decision. Option A (start_frame) already committed (9f3ccf5) and is the proven fix for this dataset.

## Option B re-verification RESULT (output_autoreject2, start_frame=0 + auto-reject ON)

Pose-source fix confirmed working: rejecter now evaluates INDEPENDENT per-frame poses, correctly flagged frame 30 (34.86px > 7.38px threshold) and dropped it. Training Stage 3 RMS 4.499 -> 1.206px after rejection. Frames 0 & 60 (catastrophic) are in HOLDOUT (random split), not the optimization set, so not evaluated - correct (they don't bias extrinsics).

BUT success criteria NOT met - final rig still biased, ~identical to ORIGINAL, NOT manual-trim:
  metric            original   manual-trim   auto-reject2(B)
  overall RMS(px)     8.16        1.31          8.23
  e3v829d (px)       12.98        1.12         13.10
  e3v82e0 (px)       14.94        1.25         15.06
  e3v832e (px)       15.14        1.32         15.28
  e3v8334 (px)       11.77        1.08         11.86
  rig tilt (deg)      5.44        3.00          5.46
  height_spread(mm)  154.8       107.9         155.4
  water_z (m)        1.0040      1.0245        1.0051
  rejected_frames      -        (trim 20 fr)   [30]

WHY B didn't fix the tilt (decisive finding):
- Removing the single catastrophic training frame (30) fixed the RMS NUMBER (it was the dominant squared-error contributor) but NOT the underlying rig tilt.
- The tilt is caused by the CONTIGUOUS EARLY SEGMENT (~first 20s, frames 90-570) of MILDLY-contaminated near-surface/rippled frames at 2-4px each. Independent per-frame RMS after removing 30: next-worst are 90=3.13, 390=3.03, 360=2.89, 420=2.67, 450=2.58, 180=2.55, 540=2.49 - all EARLY - interleaved with legitimate noisier MID-video frames (1740=2.73, 870=2.67). Good and mildly-bad frames OVERLAP at 2-3px.
- Critically, this mild contamination pulls the tilt along a near-null-space direction that barely affects reprojection RMS (SAME paradox as the original bug: low/plausible reprojection + excellent 3D reconstruction while geometry is tilted). So an RMS-threshold rejecter fundamentally cannot see it. Lowering the threshold to ~2.2px to catch the mild early frames would also drop legitimate mid-video noisy frames (over-rejection, fragile) and still relies on a signal (reprojection RMS) that is nearly blind to the tilt.
- Manual trim (Option A) fixes it because it discriminates by TIME/VIDEO-POSITION (the whole early segment is unreliable), which is the physically-meaningful signal for "board being placed / ripples settling", not per-frame reprojection RMS.

Assessment: Option B (with the pose-source fix) is a CORRECT and VALUABLE safeguard for DISCRETE catastrophic outlier frames (it works - dropped frame 30, would fully fix a dataset whose contamination is a few discrete bad frames). It is NOT the right tool for GRADIENT / contiguous near-surface contamination, for which Option A (start_frame) is correct and already proven. NOT COMMITTED - awaiting decision.

## Option B first-attempt FAILURE + root cause (pose-source bug)

Symptom: auto-reject run (start_frame=0) rejected 0 frames; output byte-identical to original (RMS 8.16, 4 bad cameras 12-15px). diagnostics frame_rejection: num_evaluated=129, median_rms=1.498, threshold=7.49, rejected=[]. Yet holdout validation of the same data measured frame 0=45.98px, 60=32.64px.

Ruled out (coordinator hypotheses):
- H1 robust/Huber residuals: NO. compute_per_frame_rms uses RAW pixel residuals (detected - refractive_project), verified by code read. Not the bug.
- H2/H3 indexing/dilution: partial - frames 0 & 60 ARE in the 32-frame HOLDOUT (random split seed=42), NOT in the 129 optimization frames the rejecter evaluated. But that alone isn't the core bug (frame 30, a training frame, was also bad).

ACTUAL root cause: the rejecter computed per-frame RMS against the JOINTLY-OPTIMIZED Stage-3 board poses (stage3_poses). A high-leverage outlier frame biases the shared extrinsics to fit ITSELF during the joint solve, so post-fit it reports a LOW residual and hides (median 1.50, max <7.49). This is the classic outlier-leverage masking problem.

Cheap experiment (detection only, no re-optimization; scratchpad/experiment_pnp.py): recomputed per-frame RMS over ALL 161 frames using INDEPENDENTLY-estimated per-frame poses (per-frame PnP init + 6-DOF refine with fixed cameras - the exact method holdout validation uses) against the auto-reject FINAL extrinsics. Result:
  frame 0 = 45.69px, frame 60 = 36.49px, frame 30 = 34.86px, ALL OTHERS < 3.2px.
  threshold 7.51px -> would reject [0, 60, 30]. Clean separation. Note frame 30 is a TRAINING frame, so this method cleans the optimization set too.
Conclusion: independent per-frame poses expose outliers that joint poses mask. Fix = source poses independently.

FIX (Step-2 correction):
- pipeline.py rejection block: before computing per-frame RMS, estimate INDEPENDENT per-frame poses via _compute_initial_board_poses (PnP init) + _estimate_validation_poses (6-DOF per-frame refine, fixed cameras) using the post-Stage-3 extrinsics/distances, and feed THOSE to compute_per_frame_rms (instead of stage3_poses). Reuses existing, proven validation machinery. Clear comment explains the leverage-masking rationale.
- frame_rejection.py compute_per_frame_rms docstring: added a CRITICAL note that board_poses MUST be independently estimated, not joint, or high-leverage outliers are masked.
- Regression test TestIndependentPoseRejectionEndToEnd: builds a geometrically-inconsistent frame (cam0 sees pose A, cam1 sees pose B - unreconcilable, like a near-surface frame), runs the pipeline's independent-pose path, asserts the frame's RMS spikes and it is rejected. This would have caught the bug. Full non-slow suite: 628 passed. Ruff clean.

## Step 1 - Option A committed
commit 9f3ccf5 "feat(detection): add detection.start_frame to skip leading extrinsic frames" (5 files: schema, detection, pipeline, cli, example_config). Pre-commit hooks (ruff/format) passed.

## Step 2 - Option B implemented (automatic per-frame outlier rejection)
New module: src/aquacal/calibration/frame_rejection.py
  - compute_per_frame_rms(): one cheap forward-projection pass over optim frames using post-Stage-3 extrinsics/poses; returns frame_idx -> RMS(px).
  - identify_outlier_frames(): rejects frame if RMS > max(k*median, floor_px). Relative rule adapts to noise; absolute floor prevents over-rejecting clean low-median data. Guardrail: if flagged fraction > max_reject_fraction, SUPPRESS rejection + warn (don't gut a broadly-broken dataset). Returns FrameRejectionResult with .to_diagnostics_dict().
  - drop_frames(): returns new DetectionResult without dropped frames (original unmodified).
Pipeline integration (pipeline.py): after Stage 3, if reject_outlier_frames, compute per-frame RMS -> identify outliers -> if any (within guardrail) drop them, RE-RUN Stage 3 once on cleaned set, then Stage 4 runs on cleaned set. Logs which frames dropped & why. Records summary in diagnostics.json under new top-level "frame_rejection" key (save_diagnostic_report gained a frame_rejection param).
Config: CalibrationConfig gained reject_outlier_frames(True), frame_rejection_k(5.0), frame_rejection_floor_px(5.0), frame_rejection_max_fraction(0.25); parsed from optimization.* in load_config; documented in cli.py + example_config.yaml.
Default rationale: reject_outlier_frames defaults TRUE but is a NO-OP on clean data (median~1.3px -> threshold max(6.5,5)=6.5px; no clean frame exceeds it) and only adds one cheap reprojection pass + a re-run ONLY when catastrophic frames are actually found. So existing good datasets are unaffected.
Tests: tests/unit/test_frame_rejection.py (14 tests) - threshold math (relative+floor), guardrail cap + boundary, median-masking limitation, empty/invalid input, to_diagnostics_dict, drop_frames immutability, and compute_per_frame_rms on synthetic data (perfect->~0; corrupted pose->high RMS flagged). Full non-slow suite: 627 passed. Ruff check + format clean.

## Trim Strategy (Option A - data-side, sync-safe)

Chosen mechanism: config/parameter-level uniform start offset (PREFERRED option 1 - no video re-encoding).
- Added `detection.start_frame` (YAML) -> `CalibrationConfig.extrinsic_start_frame` -> `detect_all_frames(start_frame=...)` -> `VideoSet.iterate_frames(start=...)`.
- Sync safety: a SINGLE synchronized iterator reads frame `frame_idx` from ALL cameras at the same index in one loop; `start` shifts every camera's first index identically. No per-camera divergence possible by construction. Verified empirically: iterate_frames(start=600, step=30) yields first frame_idx=600 with 13/13 cameras present at each index.
- Scope: applied ONLY to the extrinsic detection call (pipeline.py:663). Intrinsic calibration (`calibrate_intrinsics_all`) is untouched, per constraint.
- Original videos untouched; original output/ untouched. New config: Calibration_Emily/config_trimmed.yaml -> output_trimmed/.

Cutoff = 600 frames (20s at 30fps) justification:
- Video: 4830 frames, 30fps, 161s, all 13 cameras identical count (aligned).
- frame_step=30 -> 161 processed frames (matches 129 train + 32 holdout).
- Catastrophic holdout frames: 0 (45.98px), 60 (32.64px). Mildly elevated (2.3-2.5px vs ~1-1.5px baseline): 330/510/540/570 (t=11-19s). Cut at 600 (t=20s) removes ALL measured contamination + buffer for unmeasured early training frames.
- Retains frames 600..4800 = 141 processed (~113 train after 0.8 split) - well above need, under max_calibration_frames=200 so no subsampling loss.
- "Slightly generous" per guidance; board was near the 4 low-Y cameras at start so a modest buffer is warranted without starving those cameras (they have 650-950 obs across the full video).

## Symptoms

expected: Camera rig approximately parallel to water surface plane (uniform height above water). Reprojection error low and roughly uniform across cameras (single-digit px or better).

actual: Rig visualization shows tilt out of plane. Reprojection error elevated and bimodal across cameras.

errors: No crash. Calibration-quality problem. diagnostics.json recommendations flag elevated RMS and 4 high-error cameras "check lens/mounting".

reproduction: `python -m aquacal calibrate "C:/Users/tucke/Desktop/Calibration_Emily/config.yaml"` - full run takes ~23 min. Prefer diagnosing from existing output artifacts before re-running.

started: Fresh dataset (Calibration_Emily) calibrated for first time 2026-07-14. Not a regression.

## Eliminated

- hypothesis: The optimized interface *normal* vector itself is tilted away from vertical by near-surface frames (since `normal_fixed: false`), and this tilted normal propagates through the whole rig to cause the visual tilt and bimodal reprojection error.
  evidence: calibration.json `interface.normal` is exactly `[0, 0, -1]` (unchanged from default). Inspecting `_optim_common.py`/`pipeline.py`, when `normal_fixed=False` the tilt is NOT applied to `interface.normal` at all — it's applied as 2 extra rotation DOF (rx, ry) on the REFERENCE camera's R matrix instead (see `pipeline.py:822-832`). Computed reference camera (e3v829d) rotation from identity: only 0.77 degrees. This is negligible and cannot explain either the 5.4-degree camera-center-plane tilt or the 12-15px bimodal reprojection error.
  timestamp: 2026-07-14T00:10

- hypothesis: The 5.4-degree rig-plane tilt (from best-fit plane through camera centers, 154.8mm height spread) is itself a symptom of the same optimization bug (i.e. is caused by the contaminated frames pulling camera heights off).
  evidence: The 4 "bad" (high-reprojection) cameras do NOT correspond to the height-spread extremes. e.g. e3v832e (bad) is highest (1.0506m) but e3v831e/e3v83f0/e3v83eb (all GOOD, ~1.3-1.8px RMS) are the lowest (~0.895-0.905m). Good and bad cameras interleave across the full height range. This suggests the height/tilt spread is largely a real physical characteristic of the camera rig mounting (up to 150mm variation across mounts) rather than a pure optimization artifact - though it may be mildly amplified by the same bias.
  timestamp: 2026-07-14T00:20

## Evidence

- timestamp: 2026-07-14T00:00
  checked: diagnostics.json summary + per-camera reprojection + camera heights
  found: RMS 8.16px/9812 obs. Bad cameras (px): e3v829d=12.98 (REFERENCE), e3v82e0=14.94, e3v832e=15.14, e3v8334=11.77. Good cameras: 1.3-2.2px (8 of them). Aux fisheye e3v8250=19.93 (expected). Reconstruction excellent (0.59mm mean, 0.99% error, 4490 comparisons/32 frames). water_z=1.004m. Camera heights range 0.896-1.050m (spread 154.8mm). Heights of bad cameras: e3v829d=1.004, e3v82e0=0.995, e3v832e=1.050, e3v8334=0.972 - not obviously separated from good cameras by height alone (e.g. e3v83ef=1.025 is good, e3v831e=0.896 is good).
  implication: Bimodal error is NOT simply explained by camera height/tilt alone since good and bad cameras interleave in height. Need to check which cameras are bad - is it geometric position in rig, or intrinsics from Stage 1, or reference-camera coupling?

- timestamp: 2026-07-14T00:15
  checked: calibration.json camera centers (world XY) for all 12 primary cameras, computed via C = -R^T t.
  found: The 4 bad cameras (e3v829d y=0, e3v82e0 y=-0.06, e3v832e y=0.25, e3v8334 y=-0.01) are ALL clustered at low world-Y (near the world origin / reference camera). The 8 good cameras all have world-Y >= 0.27, up to 1.2. i.e. the bad cameras form a spatially contiguous cluster on ONE side of the rig.
  implication: The bad cameras' shared geometric trait is "positioned near one end of the rig" (near y=0), not lens/mounting defects as diagnostics.json speculates. This is consistent with those cameras being the ones with a direct view of wherever the board was during a specific (bad) portion of the extrinsic video.

- timestamp: 2026-07-14T00:25
  checked: Extracted per-corner residuals + camera_labels from calibration.json diagnostics (12305 obs). Computed mean_err vs RMS per camera.
  found: Bad cameras have mean_err << RMS (e.g. e3v829d mean=5.74px but RMS=12.98px; e3v832e mean=6.22px but RMS=15.14px), while good cameras have mean_err ~= RMS (e.g. e3v82f9 mean=1.72 RMS=2.17). This is the signature of a small number of very large outlier residuals dominating a squared-error (RMS) metric, not uniform per-camera degradation.
  implication: A handful of catastrophic observations/frames are responsible for the bad cameras' elevated RMS, not a systematic lens/intrinsic defect affecting all their observations equally.

- timestamp: 2026-07-14T00:30
  checked: `diagnostics.per_frame_errors` in calibration.json (32 holdout-validation frames, keyed by frame_idx, frame_step=30).
  found: 30 of 32 frames have RMS between 0.7-2.5px. TWO frames are catastrophic outliers: frame 0 = 45.98px, frame 60 = 32.64px (i.e. the first two sampled frames of the video). Correlation coefficient between frame_idx and per-frame RMS = -0.46 (early frames systematically worse).
  implication: Directly confirms the user's hypothesis - frames at the very start of the extrinsic video (board out of water / rippled surface) are catastrophically bad, far worse than any other frame in the dataset, and this is not noise - it's isolated to the first ~2 seconds of the video (frame_step=30, so raw frames 0 and 60).

- timestamp: 2026-07-14T00:35
  checked: quiver_e3v829d.png, quiver_e3v82e0.png (visually inspected), quiver_e3v832e.png, quiver_e3v8334.png (via Read tool) vs quiver_e3v82f9.png (good camera, for comparison).
  found: All 4 bad-camera quiver plots show a SPATIALLY LOCALIZED cluster of large (20-90px), directionally coherent residual vectors concentrated in a specific sub-region of the image (e.g. e3v829d: upper-middle region v<400; e3v832e and e3v8334: similar tight clusters), while the rest of each image has near-zero residuals (small dots). The good camera (e3v82f9) shows uniformly small residuals everywhere, no coherent cluster. A coherent, spatially localized vector field (not scattered/random) is the signature of one or a few specific bad board POSES (not per-corner detector noise) - i.e. a handful of contaminated frames, not random measurement noise or a lens defect.
  implication: Strongly confirms: a small number of specific frames (matching the 2 catastrophic frames found in per_frame_errors, likely several more in the 129-frame training set) are the cause. These bad frames happen to be visible mainly to the 4 cameras clustered near where the board entered/was near the water surface at the start of the video, giving them outsized leverage over those cameras' bundle-adjusted extrinsics despite Huber robust loss (scale=1.0px) - because Huber only linearly down-weights (not fully suppresses) outliers, and ALL corners within a single bad board-pose frame are correlated/offset together, giving that one bad frame collective leverage on the per-camera extrinsic parameters it's coupled to.

</evidence>

## Resolution

root_cause: A small number of frames near the start of the extrinsic calibration video (frame 0, frame 60, and likely several nearby frames not sampled in the 32-frame holdout set) capture the ChArUco board at/above the water surface or during surface ripples. Because the underwater refractive projection model is highly sensitive near-grazing/near-surface geometry, these frames produce catastrophic (30-100px) per-corner reprojection residuals, while >99% of frames are fine (0.7-2.5px). The 4 cameras clustered on one side of the rig (e3v829d, e3v82e0, e3v832e, e3v8334 - all at low world-Y, i.e. nearest to where the board entered the water) are the ones with a direct view of the board during these bad frames. Because all corners within one bad board-pose frame are offset together (correlated, not independent per-corner noise), the Huber robust loss (loss_scale=1.0px, which only linearly down-weights rather than fully suppressing outliers) does not fully neutralize the bad frames' collective leverage on those 4 cameras' bundle-adjusted extrinsics - producing the spatially-coherent (non-random) high-residual clusters visible in their quiver plots, and inflating their RMS to 12-15px vs ~1.3-2.2px for the 8 unaffected cameras. The 3D reconstruction metric stays excellent (0.59mm) because it is dominated by the many good, well-conditioned frames/points and multi-camera redundancy, masking the extrinsic bias. The 154.8mm/5.4-degree camera-height "tilt" does not cleanly correlate with good/bad camera grouping and is likely mostly a real physical characteristic of the rig mounting, not an artifact of this bug (this was actively ruled out - see Eliminated).

fix: APPLIED (Option A - data-side trim via new code option). Coordinator approved Option A first to confirm diagnosis. Code changes (all backward-compatible, default start_frame=0 preserves existing behavior):
  - src/aquacal/config/schema.py: added `CalibrationConfig.extrinsic_start_frame: int = 0` + docstring.
  - src/aquacal/io/detection.py: added `start_frame: int = 0` param to `detect_all_frames`, passed to `iterate_frames(start=start_frame, step=frame_step)`; fixed progress total to `(total_frames - start_frame)//frame_step`.
  - src/aquacal/calibration/pipeline.py: parse `detection.start_frame`, store on config, pass `start_frame=config.extrinsic_start_frame` to the EXTRINSIC detect_all_frames call only (intrinsic path untouched); added a log line when >0.
  - src/aquacal/cli.py + config/example_config.yaml: documented the new `detection.start_frame` option.
  Applied for THIS dataset via Calibration_Emily/config_trimmed.yaml (start_frame=600 -> output_trimmed/).

  NOTE: This code option enables the data-side trim but does NOT auto-detect bad frames. If Option A confirms the diagnosis, Option B (automatic per-frame outlier rejection) remains the candidate general/robust fix. Original candidate approaches:
  (A) Data-side, no code change: trim/re-clip the extrinsic videos to exclude the first ~2-5 seconds where the board is at/above the surface, then re-run calibration. Cheapest to try, but manual/fragile and doesn't protect against similar contamination in future datasets.
  (B) Code-side robustness fix: add automatic frame-level outlier rejection to the pipeline (e.g. after Stage 3, compute per-frame RMS and drop frames exceeding some multiple of the median before Stage 4 / finalization, then optionally re-optimize once more). This generalizes to any future dataset with a few contaminated frames and doesn't rely on the user manually curating video content.
  (C) Tuning-side: tighten robust loss further (e.g. lower loss_scale, or switch to a fully-redescending loss) - lower risk of code changes but may not fully suppress a clustered/correlated outlier frame (Huber's leverage issue is structural, not just a scale-tuning issue).
  Recommendation: (B) is the most robust general fix and directly addresses the code gap (no existing mechanism rejects anomalous frames), but requires implementation + a ~23min full pipeline run to verify. (A) is a valid quick sanity check if the user wants fast confirmation of the diagnosis before investing in the code fix.
verification: CONFIRMED via full pipeline re-run with start_frame=600 (output_trimmed/, exit 0, ~15min). Diagnosis decisively validated - trimming the first 20s of contaminated frames fixed the bimodal reprojection error:
  - Overall reprojection RMS: 8.16px -> 1.31px.
  - The 4 previously-bad cameras ALL dropped to normal: e3v829d 12.98->1.12, e3v82e0 14.94->1.25, e3v832e 15.14->1.32, e3v8334 11.77->1.08. Bimodality is gone: all 12 primary cameras now 1.08-1.86px.
  - 3D reconstruction (already good) further improved: mean 0.59mm->0.33mm, percent_error 0.99%->0.54%.
  - depth_errors SMOKING GUN resolved: old near-surface bin spanned depth -0.064m (board ABOVE water) with 18.13px; new minimum depth is +0.029m (board never above surface anymore) at 0.75px. The old deepest-bin spike (5.23px) also dropped to ~1.12px. The catastrophic near-surface bin no longer exists.
  - Rig tilt (camera-center plane vs world Z): 5.44deg -> 3.01deg; height spread 154.8mm -> 107.9mm; estimated reference-camera tilt param 0.77deg->2.60deg (small). The residual ~3deg/108mm does NOT vanish, consistent with the Eliminated hypothesis that most of the height spread is REAL physical rig-mounting variation, not an optimization artifact.
  - Observations 9812->8884 (~9% fewer, from removing ~20/161 processed frames); 113 train + 28 holdout frames retained - ample. Aux fisheye e3v8250 unchanged (~20px, expected/separate issue).
  - Regression check: 173 relevant unit tests (detection/config/video/pipeline/schema) pass with the new start_frame plumbing (default 0 = unchanged behavior).
  Original output/ and raw videos untouched; comparison artifacts in output_trimmed/.
files_changed:
  - src/aquacal/config/schema.py (added CalibrationConfig.extrinsic_start_frame)
  - src/aquacal/io/detection.py (added start_frame param, propagated to iterate_frames)
  - src/aquacal/calibration/pipeline.py (parse detection.start_frame, wire to extrinsic detection only)
  - src/aquacal/cli.py (documented start_frame in generated config template)
  - src/aquacal/config/example_config.yaml (documented start_frame)
  - Calibration_Emily/config_trimmed.yaml (new; start_frame=600, output_trimmed/) [user data dir, not repo]
