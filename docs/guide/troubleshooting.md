# Troubleshooting

This page provides practical solutions to common calibration issues.

## Reference Camera Choice

**Problem:** Stage 3 optimization converges but produces poor extrinsic estimates or high validation errors.

**Why it happens:** The reference camera (first camera in your config's `cameras` list) defines the world coordinate origin. If the reference camera has poor intrinsic calibration, all other cameras inherit these errors during extrinsic initialization.

**Solution:**
1. Check Stage 1 RMS reprojection errors (printed during `aquacal calibrate`)
2. Set the camera with the **lowest Stage 1 RMS** as your reference camera
3. Edit your config: move that camera to the first position in the `cameras` list
4. Re-run calibration

**Example:**
```
Stage 1 complete.
  cam0: RMS = 0.42 pixels  ← good
  cam1: RMS = 1.89 pixels  ← poor intrinsics
  cam2: RMS = 0.38 pixels  ← best, use as reference
```
In this case, set `cam2` as the reference camera (first in config).

---

## High RMS in Stage 1 (Intrinsic Calibration)

**Problem:** Stage 1 reports RMS reprojection error > 1.0 pixels for one or more cameras.

**Possible causes:**
- Too few calibration frames
- Poor spatial coverage (board always in center of frame)
- Board measurements in config don't match physical board
- Low-quality video (motion blur, compression artifacts)

**Solutions:**

### 1. Lower `frame_step` for more data
Edit your config:
```yaml
detection:
  frame_step: 5  # Change to 2 or 1 for more frames
```
This uses more frames from your in-air videos, improving intrinsic estimates.

### 2. Verify board measurements
Measure your physical ChArUco board with calipers:
- `square_size`: Distance between inner corners of adjacent squares (in meters)
- `marker_size`: Black marker side length (in meters)

Even 1mm error can degrade calibration.

### 3. Check video quality
- Ensure board is fully visible and in focus
- Move board to different positions and orientations (not just center)
- Avoid motion blur (hold board steady or use faster shutter speed)

### 4. Use `max_calibration_frames` to speed up iterations
If Stage 1 is good but Stage 3 is slow, limit optimization frames:
```yaml
optimization:
  max_calibration_frames: 150  # Use subset for faster Stage 3
```
This speeds up iteration time while you debug other issues.

---

## Bad Round-Trip Errors or Diverging Optimization

**Problem:** Stage 3 fails to converge, or validation errors are much higher than training errors.

**Possible causes:**
- Disconnected pose graph (no overlapping camera views)
- Too few shared observations between cameras
- Initial water_z estimates are far from true value
- Overfitted intrinsic model (rare, but see next section)

**Solutions:**

### 1. Check for pose graph connectivity
All cameras must observe the calibration board in at least some **shared frames**. If cameras have completely non-overlapping views, extrinsic initialization will fail.

**Fix:** Ensure underwater videos include frames where the board is visible to multiple cameras simultaneously.

### 2. Improve initial water_z estimates
Add `initial_water_z` (approximate camera-to-water Z-distances) to your config:
```yaml
interface:
  initial_water_z:
    cam0: 0.20  # Measure with a ruler (meters)
    cam1: 0.22
    cam2: 0.18
```
Better initialization helps Stage 3 converge faster and more reliably.

### 3. Check water_z bounds
Ensure the final water_z value is within the optimization bounds `[0.01, 2.0]` meters. If your cameras are farther than 2m from the water surface, you'll need to modify the bounds in the source code.

---

(camera-layout-looks-wrong)=
## Camera Layout Looks Wrong Despite Low Errors

**Problem:** The recovered camera positions look physically implausible — most often the cameras appear *out of plane* (their heights/depths scatter by centimeters, or the whole rig looks tilted) by much more than your real mounting could account for — yet Stage 3 reprojection RMS is low **and** 3D validation error is small.

**Why it happens:** Low reprojection error only certifies that your parameters are self-consistent in the directions the data actually *constrains*. It does **not** certify that every camera parameter was independently measured. In a downward-looking refractive array, the **out-of-plane arrangement of the cameras (their depth/height along the viewing axis) is only weakly observable**, so large deviations there cost almost nothing in residual. The optimizer isn't wrong; it is sliding freely along a "soft" direction the geometry barely pins down. Concretely, that direction is soft because:

- **Cameras measure bearings, not range.** Each corner tightly fixes the *direction* to a point but only weakly its *depth*. Depth separation between cameras comes from cross-camera parallax plus the known board scale — and for a top-down array over a limited board-depth range, the parallax that would separate camera *heights* is thin.
- **Small height spread vs. working distance.** If the cameras span, say, ~10 cm in height but sit ~1 m from the board, height differences barely move where corners land — poor signal-to-noise on exactly that coordinate.
- **Refraction supplies compensating degrees of freedom.** Each camera's camera-to-interface distance equals `water_z − C_z`, so a camera's height and its distance to the interface trade off almost exactly; the free per-frame board poses absorb the rest. A camera placed too high can produce nearly the same refracted rays as a correctly-placed one — at ~zero reprojection cost. (The axial camera-to-interface distance being weakly observable is a known property of flat-refractive calibration.)

Because these modes are so soft, ordinary sub-pixel detection noise and small unmodeled effects get *amplified* into centimeter-scale scatter in the recovered layout. **Low error ≠ faithful metric camera layout.**

**When NOT to worry (the common case):**
- Stage 3 RMS is low **and** the holdout 3D validation error is small, **and**
- you use the calibration for **triangulation/reconstruction within the captured volume**.

The soft-mode deformation is self-consistent, so it preserves ray geometry — including for held-out points — which is exactly why 3D validation stays accurate even when the drawn camera positions look off. For reconstruction, this calibration is fine.

**When to actually worry:**
- **You need the metric camera layout itself** (e.g. reporting inter-camera distances, comparing against a CAD/survey of the rig, or feeding poses to another system). Then don't trust the out-of-plane numbers until you've excited that mode (see below) — a low RMS alone won't tell you they're right.
- **The apparent misarrangement comes *with* elevated or bimodal errors** — e.g. a few cameras at 10–15 px while the rest are ~1–2 px, or validation 3D error that is also high. That is not benign soft-mode wander; it is **bias**, usually from contaminated frames (board at/above the surface, ripples, mis-detections) that inject a coherent error along the same soft direction. See {ref}`Contaminated Frames <contaminated-frames>` below.
- **The layout changes substantially run-to-run or when you change the frame subset.** Large sensitivity to which frames you use is a direct symptom of an under-excited soft mode.

**What to do (to make the layout trustworthy):**
1. **Excite the weak direction.** Present the board across a **wide depth range** and with **strong tilts**, and get corners out toward the **image edges** (larger incidence angles carry more refractive-geometry information). Ensure frames with genuine cross-camera parallax.
2. **Add what you know as a prior.** Provide measured `initial_water_z` per camera; if the mounting plane is known, that constrains heights.
3. **Remove bias first.** Trim contaminated segments with `detection.start_frame` / `detection.stop_frame` and keep automatic `reject_outlier_frames` on, so a biased soft-mode tilt isn't mistaken for real geometry.

For the underlying theory, see the [Refractive Geometry](refractive_geometry.md) and [Optimizer Pipeline](optimizer.md) guides.

---

(contaminated-frames)=
## Contaminated Frames (Board Near the Surface, Ripples)

**Problem:** A subset of cameras show much higher reprojection RMS than the rest (e.g. 10–15 px vs. 1–2 px), and/or the rig looks tilted — typically the cameras physically nearest where the board enters the water.

**Why it happens:** Frames where the ChArUco board is at or above the water surface, or where the surface is rippled, violate the flat-interface refraction model. Near the surface, refractive projection is extremely sensitive to geometry, so these frames produce large, spatially-coherent residuals that a robust loss only partially suppresses. Their leverage biases the extrinsics of nearby cameras — and, because the bias lies along the weakly-observed out-of-plane direction (see {ref}`Camera Layout Looks Wrong <camera-layout-looks-wrong>`), it can tilt the rig while barely raising overall RMS. Such segments are common at the **start** (board being lowered in) and **end** (board lifted out) of a capture.

**Solutions:**

### 1. Trim contaminated start/end segments
If the board is out of the water or the surface is settling at the start (or end) of the extrinsic capture, skip those frames. These apply uniformly across all cameras, preserving frame-index (video) synchronization, and affect only the extrinsic stage:
```yaml
detection:
  start_frame: 600   # Skip the first N frames (board entering / ripples settling)
  stop_frame: 5400   # Stop at frame N, exclusive (board being lifted out)
```
Full key reference: {ref}`Manual frame trimming <configuration-frame-trimming>` in the
[Configuration Reference](configuration.md).

### 2. Keep automatic outlier-frame rejection on
By default (`reject_outlier_frames: true`), after Stage 3 the pipeline scores each frame by its reprojection RMS against **independently estimated** per-frame board poses, drops catastrophic outliers, and re-optimizes once. This is a no-op on clean data. It reliably catches *discrete* bad frames anywhere in the capture; a guardrail suppresses rejection (and warns) if more than `frame_rejection_max_fraction` of frames would be dropped, so a broadly-contaminated dataset surfaces loudly instead of being silently gutted. Tune with:
```yaml
optimization:
  reject_outlier_frames: true
  frame_rejection_k: 5.0             # Reject if RMS > k × median RMS ...
  frame_rejection_floor_px: 5.0      # ... and above this absolute pixel floor
  frame_rejection_max_fraction: 0.25 # Guardrail
```
Full key reference: {ref}`Automatic outlier-frame rejection <configuration-frame-rejection>` in
the [Configuration Reference](configuration.md).

> **Note:** Automatic rejection catches *discrete catastrophic* frames well, but a *contiguous segment of mildly* contaminated frames (each only a few pixels off) may not exceed any safe threshold. For those, prefer trimming by `start_frame` / `stop_frame` — position in the capture is the meaningful signal. The best fix is a clean capture: keep the board fully submerged and the surface calm while collecting extrinsic frames.

Check the `frame_rejection` block in `diagnostics.json` to see what was flagged and why.

---

(camera-models-and-overfitting)=
## Camera Models and Overfitting

**Problem:** Stage 1 RMS is very low (< 0.2 pixels), but Stage 3 validation errors are high or undistortion produces artifacts.

**Possible cause:** Overfitted distortion model. With few calibration frames, higher-order distortion coefficients can fit noise rather than true lens distortion, causing the model to "blow up" outside the calibrated image region.

**Camera models in AquaCal:**

| Model | Distortion Coeffs | When to Use | Auto-Simplification |
|-------|-------------------|-------------|---------------------|
| **Standard (pinhole)** | 5 params: k1, k2, p1, p2, k3 | Most cameras, moderate distortion | ✅ Yes (automatic) |
| **Rational** | 8 params: k1-k6, p1, p2 | Wide-angle lenses, extreme barrel/pincushion distortion | ❌ No |
| **Fisheye** | 4 params: k1-k4 (equidistant) | Ultra-wide or fisheye lenses (> 120° FOV) | ❌ No |

**Auto-simplification (standard model only):**
If the full 5-parameter model produces a bad undistortion roundtrip (monotonicity check fails), AquaCal automatically retries with simpler models:
1. Fix k3 to 0 (4-parameter model: k1, k2, p1, p2)
2. Fix k3 and k2 to 0 (3-parameter model: k1, p1, p2)

This prevents overfitting when calibration data is sparse.

**Solutions:**

### If using rational or fisheye models:
These models do NOT auto-simplify. If you suspect overfitting:
1. Remove the camera from `rational_model_cameras` or `fisheye_cameras` in your config
2. Let it use the standard 5-parameter model (with auto-simplification)
3. Re-run calibration

### Signs of overfitting:
- Stage 1 RMS < 0.2 pixels but high round-trip error warnings in console
- Distortion correction produces visible artifacts at image edges
- Validation RMS >> training RMS in Stage 3

### When to use each model:
- **Standard**: Default for most lenses (up to moderate wide-angle)
- **Rational**: Use only if standard model gives RMS > 1.0 pixels and you have 50+ calibration frames
- **Fisheye**: Use only for true fisheye lenses (GoPro, ultra-wide security cameras)

For detailed theory, see the {ref}`Camera Models <camera-models>` section in the Optimizer Pipeline guide.

---

## Allowed Camera Combinations

**Problem:** Config validation fails with `ValueError` about camera lists.

**Rules:**
- `fisheye_cameras` must be a **subset** of `auxiliary_cameras`
- `fisheye_cameras` must **not overlap** with `rational_model_cameras`
- `auxiliary_cameras` must **not overlap** with `cameras` (primary cameras)

**Example (valid):**
```yaml
cameras:
  - cam0  # Reference camera
  - cam1  # Primary camera

auxiliary_cameras:
  - cam2  # Auxiliary (registered post-hoc)
  - cam3  # Auxiliary (fisheye)

rational_model_cameras:
  - cam1  # Wide-angle primary camera

fisheye_cameras:
  - cam3  # Subset of auxiliary_cameras
```

**Example (invalid):**
```yaml
cameras:
  - cam0

auxiliary_cameras:
  - cam1

fisheye_cameras:
  - cam0  # ERROR: cam0 is in cameras, not auxiliary_cameras

rational_model_cameras:
  - cam1  # ERROR: cam1 is in both rational and fisheye

fisheye_cameras:
  - cam1
```

---

## Memory and Performance Issues

**Problem:** Calibration consumes too much RAM or takes too long.

**Solution:** Limit the number of frames used in Stage 3 optimization:
```yaml
optimization:
  max_calibration_frames: 100  # Reduce from default (null = no limit)
```

- Stage 1 (intrinsics) always uses all detected frames (controlled by `frame_step`)
- Stage 2 (extrinsic init) uses all frames for pose graph construction
- **Stage 3** can be limited to a random subset for faster optimization

Reducing to 100-150 frames typically has minimal impact on calibration quality while significantly reducing memory usage and runtime.

---

## No Detections Found

**Problem:** `aquacal calibrate` fails with "No ChArUco board detected in any frame".

**Possible causes:**
- Wrong board configuration (dictionary, dimensions)
- Board out of focus or too small in frame
- Poor lighting or motion blur

**Solutions:**
1. **Verify board config matches your physical board:**
   - Check `dictionary` (e.g., `DICT_4X4_50` vs. `DICT_6X6_250`)
   - Verify `squares_x` and `squares_y` match board layout
   - Confirm `legacy_pattern` setting (check if top-left cell has a marker)

2. **Improve video quality:**
   - Ensure board fills at least 30% of frame
   - Check focus (board should be sharp)
   - Increase lighting to avoid motion blur

3. **Lower `min_corners` threshold:**
   ```yaml
   detection:
     min_corners: 8  # Lower to 4 or 6 if board is partially visible
   ```

---

## See Also

- [CLI Reference](cli.md) — Command-line usage and options
- [Optimizer Pipeline](optimizer.md) — Understanding the calibration stages
- [Configuration Reference](configuration.md) — Every config key, its default, and what it controls
- [Glossary](glossary.md) — Definitions of key terms
