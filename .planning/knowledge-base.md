# AquaCal Knowledge Base

## Table of Contents
- Architecture (1 entry)
- Optimization & Performance (2 entries)
- Coordinate Frames & Geometry (2 entries)
- Calibration Lessons (1 entry)
- Known Issues & Workarounds (0 entries)
- Debugging Recipes (0 entries)

## Architecture

### Water-Z reparameterization to break height/distance degeneracy
**Context**: Camera Z position (in extrinsics) and interface distance are mathematically degenerate — the optimizer can trade one for the other, reaching valid but nonphysical solutions where cameras appear at very different heights above the water surface.
**Insight**: A single global `water_z` parameter replaces N independent per-camera interface distances. Each camera's distance is derived as `d_i = water_z - C_z_i`. This eliminates the degeneracy by construction: moving a camera's Z also changes its interface distance, so the optimizer can't play them against each other. The reference camera has `C_z = 0` (at origin), so `water_z = d_ref`. Auxiliary cameras use a 6-param (extrinsics-only) optimization since their distance is derived from the known `water_z`.
**References**: `src/aquacal/calibration/_optim_common.py:pack_params` (line 20), `src/aquacal/calibration/interface_estimation.py:optimize_interface` (line 140), CHANGELOG entry "P.18 Replace Per-Camera Interface Distances with Global Water Surface Z".
**Added**: 2026-02-12

## Optimization & Performance

### Sparse Jacobian without LSMR: custom callable approach
**Context**: Bundle adjustment in Stages 3/4 uses `scipy.optimize.least_squares`. The obvious way to exploit Jacobian sparsity — passing `jac_sparsity` — forces the LSMR trust-region solver, which diverges on our ill-conditioned problems while the dense exact (QR) solver converges fine.
**Insight**: Use a custom `jac` callable that computes the Jacobian via `scipy.optimize._numdiff.approx_derivative` with `sparsity=(pattern, groups)` and returns `.toarray()` (dense). This gives sparse finite-difference efficiency (only `len(groups)` evaluations instead of `n_params`) with the exact TR solver's stability. `group_columns()` from `scipy.optimize._numdiff` computes optimal column groupings — e.g. 13 groups instead of 33 columns for the 3-camera test case. For large problems, a `dense_threshold` parameter falls back to returning sparse (LSMR) to avoid OOM (e.g. 13-camera, 629-frame rig would need 13.5 GiB dense).
**References**: `src/aquacal/calibration/_optim_common.py:make_sparse_jacobian_func` (line 498), `group_columns` and `approx_derivative` imported from `scipy.optimize._numdiff` (line 10). `tr_solver='exact'` is incompatible with `jac_sparsity` parameter — see scipy docs.
**Added**: 2026-02-12

### Block-sparse Jacobian structure in bundle adjustment
**Context**: The Stage 3/4 cost function has natural sparsity: each reprojection residual depends only on one camera's extrinsics, the global water_z, and one board pose. Understanding this structure is essential for anyone modifying the sparsity pattern or adding new parameter types.
**Insight**: The Jacobian has a block-sparse structure where each row (residual) touches at most ~14 columns: 6 extrinsic params for one camera + 1 water_z + 6 board pose params (+ optionally 4 intrinsic params). Column grouping exploits this — independent columns can be finite-differenced simultaneously. This reduces function evaluations by 10-15x (e.g. ~50 groups instead of ~685 columns for a 13-camera rig). Adding a new parameter type requires updating `build_jacobian_sparsity()` to mark which residuals depend on it.
**References**: `src/aquacal/calibration/_optim_common.py:build_jacobian_sparsity` (line 200), `make_sparse_jacobian_func` (line 498). See also "Sparse Jacobian without LSMR" entry above for the solver-side details.
**Added**: 2026-02-12

## Coordinate Frames & Geometry

### `interface_distance` is a Z-coordinate, not a physical gap
**Context**: The name `interface_distance` suggests a camera-to-water distance, but all downstream code treats it as the Z-coordinate of the water surface.
**Insight**: Functions like Newton projection, Brent projection, and `get_interface_point` compute the camera-to-water gap internally as `h_c = interface_distance - C_z`. So `interface_distance` must be the absolute water surface Z, not the per-camera gap. When deriving from the global `water_z` parameter, the correct assignment is `interface_distance = water_z` for all cameras. Deriving it as `water_z - C_z` double-counts `C_z` because downstream code subtracts it again. This was the root cause of bug B.6.
**References**: `src/aquacal/calibration/_optim_common.py:unpack_params` (line 165), `src/aquacal/core/refractive_geometry.py` (line ~346), `src/aquacal/core/interface_model.py` (line ~81), `tasks/archive/b6_debug_report.md`.
**Added**: 2026-02-12

### Top-down camera rig plot CW/CCW flip from Y-axis convention
**Context**: The world frame is defined by the reference camera, where Y = camera-Y-down. Plotting with standard Y-up convention mirrors CW/CCW camera ordering in the top-down view.
**Insight**: Call `ax.invert_yaxis()` on the top-down subplot to match the camera Y-down convention. Z-negation and `invert_zaxis()` do NOT affect CW/CCW — they only change the vertical display direction. The CW/CCW flip is purely a Y-axis mismatch. This was the root cause of bug B.7.
**References**: `src/aquacal/validation/diagnostics.py:plot_camera_rig` (line 547), `tasks/archive/b7_report.md`.
**Added**: 2026-02-12

## Calibration Lessons

### water_z is unobservable in non-refractive mode (n_air == n_water)
**Context**: When running calibration with n_air=n_water=1.0 as a comparison baseline, water_z moves significantly (1.0 -> 0.35 -> 0.47) despite having zero analytical gradient.
**Insight**: With equal refractive indices, the projected pixel is exactly independent of water_z (Newton-Raphson converges in 0 iterations to the pinhole solution; the interface point lies on the C-to-Q ray, so perspective division cancels). Stage 3 movement is caused by the `h_q <= 0` boundary penalty driving water_z below all board corners. Stage 4 drift is accumulated numerical noise in a flat cost valley. The final water_z value is arbitrary and meaningless; all other parameters (extrinsics, intrinsics, board poses) are unaffected.
**References**: `_refractive_project_newton` line 357 (h_q guard), `compute_residuals` (invalid-projection handling), `dev/tasks/water_z_nonrefractive_report.md`.
**Added**: 2026-02-13
**UPDATED 2026-07-30**: the stated mechanism no longer exists. The flat 100 px
penalty this entry blames for "driving water_z below all board corners" was
removed — invalid projections are now continued with the pinhole extension, which
is differentiable, so that spurious driver is gone. The CONCLUSION (water_z is
analytically unobservable when n_air == n_water, and its final value is
meaningless) still holds and is independent of the penalty. The explanation for
the observed *movement* has NOT been re-measured since the change and should be
re-derived before being cited. See `.planning/debug/stage3-diverges-new-geometry.md`.

### Fronto-parallel board views leave focal length degenerate
**Context**: One camera on a 13-camera rig solved 15 cm out of the rig plane with 2.9 px reprojection error, while its intrinsics passed every `validate_intrinsics()` check. Its fx was 1367.9 against ~1578 for eleven identical-lens peers.
**Insight**: Focal length is recovered from perspective foreshortening. When board views are near fronto-parallel, the projection is nearly a pure scaling and fx becomes degenerate with board distance -- they can be scaled together with almost no change in reprojection error. The optimizer settles anywhere along that valley, producing a *self-consistent* calibration (low RMS, sane distortion, centered principal point) whose fx is badly wrong. Downstream, PnP distance scales linearly with fx, so a 13% fx deficit displaced the camera ~15 cm toward the water. `validate_intrinsics()` cannot detect this -- all of its checks pass. `validate_view_diversity()` (added `16fd84f`) inspects the input geometry instead and warns when 90th-percentile board tilt < 15 deg. Measured separation on the real rig: bad camera 7.2 deg, correct cameras 19.6-29.7 deg. A cross-camera `expected_fx` check was rejected as a fix: the library must support arbitrary mixed camera sets and cannot assume prior knowledge of shared focal lengths.
**References**: `src/aquacal/calibration/intrinsics.py:validate_view_diversity`, `.planning/debug/callibration071626-tilt-high-reproj.md`.
**Added**: 2026-07-20

### cv2.calibrateCamera needs an explicit initial guess
**Context**: One camera calibrated to fx=3844 against ~1580 for its peers, with distortion k2=-10.9, k3=+32.7 and Stage 1 RMS 2.87 px vs 0.37-0.61 px. Its board-view data was verified to be as good as a normal camera's.
**Insight**: Without `CALIB_USE_INTRINSIC_GUESS`, OpenCV auto-initializes K from a homography/DLT decomposition that can be badly ill-conditioned for some board-pose distributions, and the nonlinear refinement never escapes the resulting basin. A richer distortion model does not help (rational 8-coeff produced fx=3971). Seeding `fx = fy = max(image_width, image_height)` with the principal point at the image center fixes it and reproduces the unguided result to 6+ significant figures on well-behaved cameras, so it is a safe no-op where calibration already worked. A bad K here poisons Stage 2 PnP directly -- the camera was already misplaced in `calibration_initial.json`, before any joint optimization -- and Stage 3/4 does not self-correct, because the wrong intrinsics and wrong pose are locally mutually consistent.
**References**: `src/aquacal/calibration/intrinsics.py:calibrate_intrinsics_single`, `.planning/debug/callibration071626-tilt-high-reproj.md`.
**Added**: 2026-07-20

## Known Issues & Workarounds

### A subagent executor that backgrounds a long test run will stall and never finish
**Context**: Phase 19.3 plan 07's executor committed its two code tasks correctly, then launched
the test suite as a background job and returned before it completed — leaving no SUMMARY.md.
Resumed with explicit "run everything in the foreground" instructions, it did exactly the same
thing again: ~78 min and ~300k tokens on the second attempt with zero progress. The orchestrator
took the task over and finished it in one foreground run. Phase 19.2 hit the same class of
failure repeatedly with production sweeps.
**Insight**: The agent's *return text* is not evidence of what happened. It read as though work
were still legitimately in flight ("I'll wait for the notification"), which is indistinguishable
from a stall. **Always verify a subagent's claim against the filesystem and git before acting on
it** — `git log --oneline HEAD..<worktree-branch>` for committed work, and an `ls` for the
expected SUMMARY.md. Doing that is what revealed the plan was two-thirds done rather than failed,
so resuming/taking over was correct and re-running the whole plan would have been waste.
**How to apply**:
- Tell executors explicitly: run long commands **synchronously**; never launch a background job
  and return waiting on it.
- Tell them what *not* to run — plan 08 writes a queue script but must not execute the ~9 h
  sweep; without that sentence an executor may try, and then stall for hours.
- Split a ~10 min suite into `-m "not slow"` then `-m "slow"` rather than one unfiltered run, so
  each call finishes inside the tool's 10-minute ceiling. (The two together are still required —
  `-m "not slow"` deselects the bit-identity suites that are often the actual evidence.)
- If an executor stalls twice on the same step, stop resuming it and finish that step in the
  orchestrator. Note in the SUMMARY who measured what, so later readers know which numbers came
  from the executor and which from the orchestrator.
**References**: `.planning/phases/19.3-scenario-geometry-and-convergence/19.3-07-SUMMARY.md`
(its header records the takeover), `19.3-ORCHESTRATOR-NOTES.md`.
**Added**: 2026-08-02

### Neither CLAUDE.md nor .claude/ is tracked in this repo
**Context**: Attempted to record the pitfall above in `.claude/rules/`, believing it was tracked.
**Insight**: `.gitignore:214` ignores `.claude/` and `:216` ignores `CLAUDE.md`. `git ls-files
.claude/` returns **zero** — the rules files are local-only, not committed-but-ignored. Anything
written to either location persists only on that one machine and is invisible to collaborators
and to a fresh clone. Durable, shareable project lessons belong in `.planning/knowledge-base.md`
(this file), which CLAUDE.md itself designates as the home for accumulated gotchas.
**Added**: 2026-08-02

## Debugging Recipes

### Offline Stage 1 analysis must match the pipeline's frame_step
**Context**: An offline probe reproducing Stage 1 intrinsic calibration produced fx values (841, 1300) that did not match the pipeline's (1368, 1578) for the same cameras and videos.
**Insight**: `_select_calibration_frames` caps at `max_frames` (default 100). At `frame_step=1` a video yields ~900-2200 candidate views and the probe picks 100 *by coverage*; at the config's `frame_step=30` it yields only ~30-77 candidates, all of which are used. These are entirely different frame sets, so fx differs materially. Re-run at the pipeline's frame_step, the probe reproduced its fx exactly (1367.9 / 1577.6 / 1575.9 / 1574.1). Always pass the config's `detection.frame_step` when analyzing Stage 1 behaviour offline. A corollary worth noting: fx that shifts by ~20% purely from a different frame subset is itself evidence that fx is weakly constrained for that camera.
**References**: `src/aquacal/calibration/intrinsics.py:_select_calibration_frames`, `.planning/debug/callibration071626-tilt-high-reproj.md`.
**Added**: 2026-07-20
