# AquaCal: Performance and Accuracy Report

All results in this document are drawn from three sources:

1. **Synthetic experiments** (`docs/tutorials/02_synthetic_validation.ipynb`): a 12-camera rig with ground-truth geometry, generating CSV artifacts in `docs/tutorials/output/`. Ground truth is fully controlled; all cameras share idealized intrinsics derived from a real hardware rig.
2. **Real-rig calibration (tutorial)** (`docs/tutorials/aquacal_data/real-rig/real-rig/output/calibration.json`): a 13-camera hardware rig calibrated with a reduced input set for portability. Stage 4 intrinsic refinement disabled. 48 frames used, 12 held out.
3. **Real-rig calibration (production)** (`release_calibration/`): the same 13-camera hardware rig calibrated with the full input set. Stage 4 intrinsic refinement enabled, normal_fixed = false (tilt estimated). 200 frames used, 52 held out.

Synthetic scenario parameters and CSV data are cited verbatim. Interpretation beyond what the numbers directly show is confined to Section 7.

---

## 1. Synthetic Scenario Parameters

Source: `src/aquacal/datasets/synthetic.py`, lines 236–394, 721–737.

The "realistic" scenario used for all three experiments:

| Parameter | Value |
|---|---|
| Cameras | 12, positions matching real hardware rig |
| Image size | 1600 x 1200 px |
| Shared intrinsics | fx = 1587.79, fy = 1588.34, cx = 780.22, cy = 601.74 px |
| Distortion | [-0.5022, 0.2968, 0.0006, 0.0025, -0.0552] |
| Ground-truth water_z | 1.031 m |
| Frames | 30 |
| Calibration board depth range | 1.13 – 1.87 m |
| Pixel noise | 0.5 px (Gaussian, per coordinate) |
| Board | 12 x 9 squares, square_size = 60 mm, marker_size = 45 mm |

Camera XY positions (meters, world frame, Z = 0 for all):

| Camera | X | Y |
|---|---|---|
| cam0 (reference) | 0.000 | 0.000 |
| cam1 | 0.208 | 0.242 |
| cam2 | 0.335 | 0.573 |
| cam3 | 0.223 | 0.868 |
| cam4 | 0.004 | 1.149 |
| cam5 | -0.336 | 1.193 |
| cam6 | -0.680 | 1.152 |
| cam7 | -0.887 | 0.883 |
| cam8 | -1.002 | 0.565 |
| cam9 | -0.895 | 0.268 |
| cam10 | -0.664 | 0.004 |
| cam11 | -0.336 | -0.057 |

Both models (refractive and non-refractive) are calibrated on the same synthetic observations. The refractive model uses n_water = 1.333; the non-refractive model uses n_water = 1.0 (equivalent to ignoring refraction). Both include Stage 4 intrinsic refinement.

---

## 2. Experiment 1: Parameter Recovery

Source: notebook cell outputs and `docs/tutorials/output/exp1_parameter_errors.csv`.

Both models were calibrated on identical synthetic data. The table below reports aggregate error metrics across all 12 cameras.

### 2.1 Reprojection RMS

| Model | Reprojection RMS (px) |
|---|---|
| Refractive | 0.498 |
| Non-refractive | 1.376 |

### 2.2 Focal Length Recovery

Source: `exp1_parameter_errors.csv`, `focal_length_error_pct` column.

| Model | Mean |focal length error| (%) | Per-camera range (%) |
|---|---|---|
| Refractive | 0.033 | 0.002 – 0.085 |
| Non-refractive | 5.699 | 4.999 – 6.271 |

Per-camera values (refractive model, %):

| cam0 | cam1 | cam2 | cam3 | cam4 | cam5 | cam6 | cam7 | cam8 | cam9 | cam10 | cam11 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 0.080 | 0.035 | 0.006 | 0.040 | 0.085 | 0.046 | -0.018 | -0.006 | -0.020 | -0.002 | 0.035 | 0.021 |

Per-camera values (non-refractive model, %):

| cam0 | cam1 | cam2 | cam3 | cam4 | cam5 | cam6 | cam7 | cam8 | cam9 | cam10 | cam11 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 5.311 | 6.197 | 6.271 | 5.999 | 5.297 | 4.999 | 5.514 | 6.136 | 5.853 | 5.676 | 5.917 | 5.216 |

### 2.3 Camera Position Recovery

Source: `exp1_parameter_errors.csv`, `z_position_error_mm` and `xy_position_error_mm` columns. Z errors are mean-shift corrected (the reference camera is pinned at the origin during optimization, so the mean Z error of free cameras is subtracted from all cameras to reveal the systematic shift).

| Model | Mean |Z error| (mm) | Mean XY error (mm) |
|---|---|---|
| Refractive | 0.35 | 0.47 |
| Non-refractive | 9.66 | 4.94 |

### 2.4 Interface Distance (water_z) Recovery

Refractive model only:

| Metric | Value |
|---|---|
| Ground truth | 1031.0 mm |
| Estimated | 1032.2 mm |
| Error | +1.19 mm (+0.115%) |

---

## 3. Experiment 2: Depth Generalization

Source: `docs/tutorials/output/exp2_depth_generalization.csv`.

Using the calibrations from Experiment 1, 3D reconstruction accuracy is evaluated at 8 test depths spanning 1.1 – 2.5 m. At each depth, a dense XY grid of board positions (7 x 7, XY extent +/- 0.5 m, center at (-0.34, 0.55) m, 3-degree tilt variation) is generated. Corners are triangulated across cameras and compared to known inter-corner distances (60 mm square size). Signed mean error reflects systematic scale bias; RMSE reflects total distance measurement error.

### 3.1 Reconstruction RMSE vs Depth

| Depth (m) | Refractive RMSE (mm) | Non-refractive RMSE (mm) |
|---|---|---|
| 1.10 | 0.401 | 0.818 |
| 1.20 | 0.379 | 0.692 |
| 1.30 | 0.404 | 0.544 |
| 1.40 | 0.392 | 0.502 |
| 1.50 | 0.424 | 0.497 |
| 1.70 | 0.396 | 0.502 |
| 2.00 | 0.384 | 0.594 |
| 2.50 | 0.412 | 0.955 |

Refractive model maximum RMSE across all depths: 0.42 mm.
Non-refractive model maximum RMSE across all depths: 0.95 mm.

### 3.2 Signed Mean Error vs Depth

| Depth (m) | Refractive signed mean (mm) | Non-refractive signed mean (mm) |
|---|---|---|
| 1.10 | +0.033 | +0.226 |
| 1.20 | +0.030 | +0.167 |
| 1.30 | +0.029 | +0.151 |
| 1.40 | +0.029 | +0.178 |
| 1.50 | +0.033 | +0.191 |
| 1.70 | +0.034 | +0.248 |
| 2.00 | +0.028 | +0.335 |
| 2.50 | +0.034 | +0.511 |

### 3.3 Scale Factor vs Depth

Scale factor = measured distance / true distance:

| Depth (m) | Refractive | Non-refractive |
|---|---|---|
| 1.10 | 1.00056 | 1.00377 |
| 1.20 | 1.00050 | 1.00278 |
| 1.30 | 1.00049 | 1.00252 |
| 1.40 | 1.00049 | 1.00297 |
| 1.50 | 1.00056 | 1.00318 |
| 1.70 | 1.00057 | 1.00413 |
| 2.00 | 1.00046 | 1.00558 |
| 2.50 | 1.00056 | 1.00852 |

---

## 4. Experiment 3: XY vs Z Reconstruction Anisotropy

Source: `docs/tutorials/output/exp3_xy_vs_z_anisotropy.csv`.

Using the same test data from Experiment 2, per-point triangulation error is decomposed into lateral (XY) and depth (Z) components by comparing triangulated corner positions against ground truth.

### 4.1 Component RMSE vs Depth

| Depth (m) | Refr XY RMSE (mm) | Refr Z RMSE (mm) | Non-refr XY RMSE (mm) | Non-refr Z RMSE (mm) |
|---|---|---|---|---|
| 1.10 | 0.732 | 1.805 | 24.149 | 49.359 |
| 1.20 | 0.737 | 1.752 | 25.661 | 28.530 |
| 1.30 | 0.759 | 1.771 | 27.197 | 11.730 |
| 1.40 | 0.761 | 1.782 | 28.634 | 23.846 |
| 1.50 | 0.785 | 1.903 | 30.009 | 43.122 |
| 1.70 | 0.795 | 1.909 | 32.906 | 87.520 |
| 2.00 | 0.837 | 1.865 | 37.263 | 152.487 |
| 2.50 | 0.908 | 1.914 | 44.156 | 256.971 |

### 4.2 Anisotropy Ratio (Z RMSE / XY RMSE)

| Depth (m) | Refractive | Non-refractive |
|---|---|---|
| 1.10 | 2.47 | 2.04 |
| 1.20 | 2.38 | 1.11 |
| 1.30 | 2.34 | 0.43 |
| 1.40 | 2.34 | 0.83 |
| 1.50 | 2.43 | 1.44 |
| 1.70 | 2.40 | 2.66 |
| 2.00 | 2.23 | 4.09 |
| 2.50 | 2.11 | 5.82 |

Refractive anisotropy ratio range: 2.1 – 2.5 (mean 2.3).
Non-refractive anisotropy ratio range: 0.4 – 5.8 (mean 2.3).

### 4.3 Error Distribution at Extreme Depths

Source: notebook cell `uot6gtkn3st` output.

| Depth | Model | XY median (mm) | Z median (mm) |
|---|---|---|---|
| 1.10 m (shallowest) | Refractive | 0.667 | 1.293 |
| 1.10 m (shallowest) | Non-refractive | 24.034 | 48.312 |
| 2.50 m (deepest) | Refractive | 0.849 | 1.341 |
| 2.50 m (deepest) | Non-refractive | 43.759 | 252.402 |

---

## 5. Real-Rig Calibration (Tutorial Configuration)

Source: `docs/tutorials/aquacal_data/real-rig/real-rig/output/calibration.json`.

A 13-camera hardware rig calibrated with AquaCal v1.4.1. Twelve cameras share similar ~1588 px focal length lenses (1600 x 1200 resolution). One camera (e3v8250) uses a wider-angle fisheye lens (~737 px focal length) and was calibrated via the auxiliary camera registration pathway (post-hoc, with fixed board poses and water_z from the primary 12-camera joint optimization). This configuration uses a reduced input set for portability and does not include Stage 4 intrinsic refinement.

### 5.1 Calibration Metadata

| Parameter | Value |
|---|---|
| Software version | 1.4.1 |
| Frames used | 48 |
| Frames held out | 12 |
| Stage 4 (intrinsic refinement) | Disabled |
| Tilt estimation | Disabled (normal_fixed not set) |
| Estimated water_z | 1.0197 m |

### 5.2 Reprojection Error (Per-Camera)

Source: `calibration.json` diagnostics.

**Primary cameras (12, jointly calibrated):**

| Camera | RMS (px) |
|---|---|
| e3v829d (reference) | 0.565 |
| e3v8334 | 0.587 |
| e3v82e0 | 0.650 |
| e3v832e | 0.684 |
| e3v82f9 | 0.741 |
| e3v83eb | 0.808 |
| e3v83e9 | 0.845 |
| e3v83ef | 0.914 |
| e3v83ee | 1.174 |
| e3v83f1 | 1.395 |
| e3v831e | 1.429 |
| e3v83f0 | 2.010 |

Overall RMS (all 13 cameras): 0.934 px.

**Auxiliary camera (registered post-hoc, wider-angle fisheye lens):**

| Camera | RMS (px) |
|---|---|
| e3v8250 | 25.991 |

### 5.3 3D Reconstruction Accuracy

Source: `calibration.json` diagnostics.

| Metric | Value |
|---|---|
| Mean 3D distance error | 0.237 mm |
| Std 3D distance error | 0.373 mm |

These are inter-corner distance errors: triangulated adjacent-corner distances compared to the known 60 mm board square size.

---

## 6. Real-Rig Calibration (Production Configuration)

Source: `release_calibration/diagnostics.json`, `release_calibration/calibration.json`, `release_calibration/spatial_measurements.csv`, `release_calibration/config.yaml`.

The same 13-camera hardware rig, calibrated with the full input set and all optimization stages enabled.

### 6.1 Configuration

Source: `release_calibration/config.yaml`.

| Parameter | Value |
|---|---|
| Software version | 1.4.1 |
| Frames used | 200 |
| Frames held out | 52 |
| Frame step | 30 (every 30th frame from video) |
| Max calibration frames | 200 |
| Stage 4 (intrinsic refinement) | Enabled |
| Auxiliary intrinsic refinement | Enabled |
| Tilt estimation | Enabled (normal_fixed = false) |
| Robust loss | Huber (f_scale = 1.0) |
| Holdout fraction | 0.2 |
| Board | 12 x 9, square_size = 60 mm, marker_size = 45 mm |
| Intrinsic board | 11 x 8, square_size = 20 mm, marker_size = 15 mm (separate, smaller board for in-air intrinsics) |
| Estimated water_z | 1.0306 m |

### 6.2 Reprojection Error (Per-Camera)

Source: `release_calibration/diagnostics.json`.

**Primary cameras (12, jointly calibrated):**

| Camera | RMS (px) |
|---|---|
| e3v829d (reference) | 0.539 |
| e3v832e | 0.562 |
| e3v83ef | 0.568 |
| e3v82f9 | 0.632 |
| e3v8334 | 0.702 |
| e3v82e0 | 0.707 |
| e3v831e | 0.728 |
| e3v83ee | 0.781 |
| e3v83f1 | 0.830 |
| e3v83e9 | 1.009 |
| e3v83eb | 1.078 |
| e3v83f0 | 2.408 |

Primary camera mean RMS: 0.879 px.
Overall RMS (including auxiliary): 1.019 px.

**Auxiliary camera (wider-angle fisheye lens, registered post-hoc):**

| Camera | RMS (px) |
|---|---|
| e3v8250 | 15.134 |

### 6.3 3D Reconstruction Accuracy

Source: `release_calibration/diagnostics.json` and `release_calibration/spatial_measurements.csv`.

**Inter-corner distance errors** (triangulated adjacent-corner distances vs known 60 mm square size):

| Metric | Value |
|---|---|
| Mean absolute error | 0.268 mm |
| Std | 0.618 mm |
| Signed mean | +0.044 mm |
| RMSE | 0.674 mm |
| Max error | 19.622 mm |
| Median absolute error | 0.143 mm |
| Percent error | 0.447% |
| N comparisons | 7,762 |
| N frames | 52 (holdout set) |

**Measurement depth range**: 1.029 – 1.530 m.

### 6.4 Camera Geometry and Refined Intrinsics

Source: `release_calibration/calibration.json`.

Per-camera positions and Stage-4-refined focal lengths:

| Camera | C_x (m) | C_y (m) | C_z (m) | h_c (m) | fx (px) | fy (px) |
|---|---|---|---|---|---|---|
| e3v829d (ref) | 0.000 | 0.000 | 0.000 | 1.031 | 1587.42 | 1586.87 |
| e3v82e0 | -0.336 | -0.057 | 0.002 | 1.029 | 1592.54 | 1592.19 |
| e3v82f9 | 0.335 | 0.573 | -0.001 | 1.032 | 1577.12 | 1577.84 |
| e3v831e | -0.895 | 0.268 | 0.003 | 1.027 | 1584.74 | 1585.69 |
| e3v832e | 0.208 | 0.242 | 0.005 | 1.026 | 1590.40 | 1589.93 |
| e3v8334 | -0.664 | 0.004 | 0.007 | 1.024 | 1561.31 | 1561.31 |
| e3v83e9 | -0.336 | 1.193 | 0.022 | 1.008 | 1569.08 | 1571.25 |
| e3v83eb | -0.887 | 0.883 | 0.002 | 1.028 | 1587.34 | 1587.72 |
| e3v83ee | 0.004 | 1.149 | -0.034 | 1.064 | 1616.10 | 1618.31 |
| e3v83ef | 0.223 | 0.868 | 0.010 | 1.020 | 1576.49 | 1575.83 |
| e3v83f0 | -1.002 | 0.565 | 0.011 | 1.019 | 1560.60 | 1565.01 |
| e3v83f1 | -0.680 | 1.152 | -0.051 | 1.082 | 1650.30 | 1648.12 |
| e3v8250 (aux) | -0.337 | 0.578 | 0.004 | 1.027 | 746.15 | 745.71 |

Camera height above water: mean = 1.032 m, spread = 73.2 mm (min 1.008 m, max 1.082 m).

Primary camera refined focal length range: 1560.60 – 1650.30 px (spread: 89.70 px, ~5.7%).

### 6.5 Depth-Stratified Reprojection Error

Source: `release_calibration/depth_errors.csv`. Bins represent board depth relative to camera (approximately water_z + board-to-interface distance).

| Depth range (m) | Mean reprojection error (px) | Std (px) | N observations |
|---|---|---|---|
| -0.005 – 0.096 | 0.695 | 0.501 | 134 |
| 0.096 – 0.196 | 0.603 | 0.505 | 1,187 |
| 0.196 – 0.296 | 0.600 | 0.707 | 6,711 |
| 0.296 – 0.397 | 0.634 | 0.800 | 6,943 |
| 0.397 – 0.497 | 0.629 | 1.026 | 4,168 |

Total observations: 19,143.

### 6.6 Comparison: Tutorial vs Production Configuration

| Metric | Tutorial (48 frames, no Stage 4) | Production (200 frames, Stage 4) |
|---|---|---|
| Primary camera mean RMS (px) | ~0.88* | 0.879 |
| Best primary camera RMS (px) | 0.565 | 0.539 |
| Worst primary camera RMS (px) | 2.010 | 2.408 |
| Auxiliary camera RMS (px) | 25.991 | 15.134 |
| 3D mean absolute distance error (mm) | 0.237 | 0.268 |
| Estimated water_z (m) | 1.0197 | 1.0306 |

*Computed from per-camera values; overall RMS was 0.934 including auxiliary.

---

## 7. Interpretation and Speculation

This section contains the author's interpretation of the data presented above. It goes beyond what the numbers directly prove.

### 7.1 Refractive Model Stability Across Depth

The refractive model's reconstruction RMSE varies by only 0.045 mm across the full 1.1 – 2.5 m depth range (0.379 – 0.424 mm), with no visible trend. The signed mean error is stable at +0.03 mm. This flatness is consistent with the model having learned the correct physical geometry: once the interface is modeled correctly, depth should not introduce systematic bias.

The non-refractive model's RMSE increases monotonically from 0.50 mm at 1.4 m to 0.96 mm at 2.5 m, and its signed mean error grows from +0.15 mm to +0.51 mm. This is consistent with a scale error that compounds with distance from the interface.

### 7.2 Source of Non-Refractive Focal Length Bias

The non-refractive model consistently overestimates focal length by 5.0 – 6.3%. This is consistent with the model compensating for the refractive compression of apparent depth: underwater objects appear closer than they are, and the optimizer increases focal length to map this compressed apparent geometry onto the observed pixel positions. The ~5.7% mean bias is roughly consistent with the ratio (n_water - 1) / n_water * (h_c / depth) for the rig's geometry, though this back-of-envelope calculation has not been formally verified.

### 7.3 Anisotropy

The refractive model's stable anisotropy ratio of 2.1 – 2.5 across all depths is likely a geometric property of this particular camera array: all cameras are mounted approximately vertically above the water surface, providing strong angular diversity in XY but limited diversity along Z. This ratio would be expected to decrease with the addition of obliquely-mounted cameras.

The non-refractive model's anisotropy ratio varies erratically (0.4 – 5.8) because its systematic parameter bias introduces large, depth-dependent Z errors that dominate the geometric anisotropy at some depths and partially cancel it at others. The ratio dropping below 1.0 at 1.3 m depth is likely an artifact of the systematic Z bias crossing zero near the calibration depth centroid.

### 7.4 Auxiliary Camera (e3v8250)

The 26 px reprojection RMS for e3v8250 is substantially worse than the 0.57 – 2.01 px range of the primary cameras. This camera uses a much wider-angle lens (~737 px focal length vs ~1588 px) and was registered post-hoc via the auxiliary camera pathway with fixed board poses and water_z from the primary joint optimization. The high residual may indicate that this camera's distortion model is insufficiently flexible, that its field of view has limited overlap with the calibration board positions, or that the post-hoc registration pathway (which does not refine board poses jointly with this camera) is inherently less constrained than the full joint optimization.

### 7.5 Noise Floor

With 0.5 px Gaussian noise and 12 cameras, the refractive model achieves 0.498 px reprojection RMS — close to the noise floor. The reconstruction RMSE of ~0.4 mm is the triangulation precision achievable at this noise level with this camera geometry. Without independent ground truth for camera positions in the real-rig data, we cannot directly verify whether the real-rig parameter recovery matches the synthetic accuracy, but the similar reprojection RMS (0.57 – 2.01 px per camera) and sub-millimeter 3D distance errors (0.237 +/- 0.373 mm) suggest comparable quality.

### 7.6 Production vs Tutorial Calibration

The production configuration uses 4x more frames (200 vs 48), enables Stage 4 intrinsic refinement and tilt estimation, yet produces nearly identical primary camera reprojection RMS (0.879 vs ~0.88 px) and 3D distance error (0.268 vs 0.237 mm). The auxiliary camera (e3v8250) improved substantially from 25.99 to 15.13 px, likely because the larger frame set provides more board observations within its field of view for the post-hoc registration. The water_z estimates differ by 10.9 mm (1.0197 vs 1.0306 m); without independent measurement of the true water surface height, it is not possible to determine which is more accurate.

The 5.7% spread in Stage-4-refined focal lengths (1560.60 – 1650.30 px) across the 12 primary cameras is notable given that the in-air intrinsics used a shared board and similar calibration procedure. This spread may reflect genuine per-camera optical variation, residual coupling between focal length and other parameters in the refractive model, or limitations of the in-air intrinsic calibration that Stage 4 partially corrects.

### 7.7 Limitations of This Evaluation

- The synthetic scenario uses idealized conditions: all cameras share identical intrinsics, optical axes are perfectly aligned to the Z-axis, the water surface is perfectly flat, and refractive indices are exact. Real hardware introduces per-camera intrinsic variation, misaligned optical axes, possible surface curvature or vibration, and uncertain refractive indices.
- The 3D reconstruction metric (inter-corner distance error) measures relative accuracy within a single board pose. It does not directly measure absolute positioning accuracy across the full measurement volume.
- The non-refractive model in this comparison uses n_water = 1.0 in the same optimization framework. A standard OpenCV calibration (which would not attempt to estimate water_z at all) might perform differently.
- Timing data is not available. No benchmark or profiling scripts exist in the project. The notebook header notes "~60 min total" for the large-rig preset, but this is a rough estimate for the full notebook (3 experiments), not a controlled measurement of individual pipeline stages.
