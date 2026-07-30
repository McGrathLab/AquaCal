# AquaCal: Technical Summary for Journal Article

## 1. Purpose and Problem Statement

AquaCal is a Python library for calibrating multi-camera arrays that observe an underwater volume through a flat air–water interface. Standard camera calibration assumes rectilinear light propagation from scene to sensor. When cameras are mounted in air and directed downward at underwater calibration targets, light refracts at the water surface according to Snell's law as it transitions between media with different refractive indices (n_water ≈ 1.333, n_air ≈ 1.000). A calibration procedure that ignores this refraction absorbs the refractive effect into biased focal lengths, biased camera Z positions, and contaminated distortion coefficients — producing systematic, depth-dependent 3D reconstruction errors that grow with both depth and incidence angle.

AquaCal addresses this by incorporating an explicit physical model of the flat air–water interface into every stage of the calibration pipeline: intrinsic estimation, extrinsic initialization, joint bundle adjustment, and optional post-hoc refinement.

## 2. Calibration Pipeline

The pipeline proceeds through four sequential stages, orchestrated by a single entry point that accepts either a YAML configuration file or pre-computed corner detections.

### 2.1 Stage 1: In-Air Intrinsic Calibration

Cameras are first calibrated individually using in-air video of a ChArUco board (no water present). The library detects ChArUco corners across video frames and selects up to a configurable maximum number of frames, prioritizing spatial coverage via a scoring function based on the standard deviation of normalized corner positions across the image.

Three distortion models are supported:

- **Pinhole (5-coefficient)**: Standard radial-tangential model [k1, k2, p1, p2, k3] via `cv2.calibrateCamera`.
- **Rational (8-coefficient)**: Adds denominator terms [k4, k5, k6] for wide-angle lenses via `cv2.CALIB_RATIONAL_MODEL`.
- **Fisheye (4-coefficient)**: Equidistant model [k1, k2, k3, k4] via `cv2.fisheye.calibrate`.

Post-calibration validation checks undistortion roundtrip error (< 1 px) and distortion polynomial monotonicity. If validation fails, the procedure automatically retries with progressively simpler models (fixing k3, then k2 and k3).

**Output per camera**: Camera matrix K (3×3), distortion coefficients, image size, and lens model flag.

### 2.2 Stage 2: Extrinsic Initialization via BFS Pose Graph

A bipartite pose graph connects camera nodes and frame nodes; an edge exists when a camera detects the board in a given frame. The graph must be fully connected (all cameras linked through chains of shared observations).

Starting from the reference camera fixed at the world origin (R = I, t = 0), a priority-based BFS traversal alternates between frame and camera nodes, prioritizing edges with the highest corner counts. At each step:

- **Camera → Frame**: A (refractive) PnP solve estimates the board pose in the camera frame, which is composed with the known camera-in-world transform to yield the board pose in world coordinates.
- **Frame → Camera**: A PnP solve estimates the board in camera frame, and the known board-in-world transform yields the world-to-camera extrinsics.

When approximate water surface positions are available, refractive PnP is used: an initial standard PnP guess is followed by a rough depth correction (t_z scaled by n_water) and then refined via Levenberg–Marquardt minimization of refractive reprojection error.

After BFS traversal, a multi-frame averaging pass re-estimates each board pose from all cameras that observe it and each camera pose from all frames it observes, using weighted chordal L2 mean rotation averaging (SVD-based).

### 2.3 Stage 3: Joint Refractive Bundle Adjustment

This is the core optimization stage. It jointly refines:

- **Non-reference camera extrinsics**: 6 parameters each (Rodrigues rotation vector + translation), for N − 1 cameras.
- **Global water surface height**: A single scalar water_z — the Z-coordinate of the water surface in the world frame, shared across all cameras.
- **Board poses**: 6 parameters each (Rodrigues + translation), for F observed frames.

Total parameter count: 6(N − 1) + 1 + 6F.

The parameter vector is laid out as:

```
[tilt_rx, tilt_ry (0 or 2)] | [rvec, tvec] × (N−1) | water_z | [rvec, tvec] × F
```

**Cost function**: For each (camera, frame) observation pair, all detected corner positions on the board are transformed to 3D world coordinates via the current board pose, then projected through the refractive model to pixel coordinates. Residuals are the difference between projected and observed pixel positions. A projection the refractive model cannot produce (corner at or above the interface, camera below it, or total internal reflection) is continued with the plain pinhole projection — the unique continuous extension across the interface, which keeps the residual differentiable in every parameter. Only a point behind the camera, where no extension exists, falls back to a flat 100 px penalty. A constant penalty was used for all such cases before 2026-07-30; because a constant has zero derivative it made the invalid region absorbing, which caused Stage 3 to diverge on plausible geometries (see `.planning/debug/stage3-diverges-new-geometry.md`).

**Optimizer**: `scipy.optimize.least_squares` with the Trust Region Reflective (TRF) method, Huber robust loss (f_scale = 1.0), and bound constraints (water_z ∈ [0.01, 2.0] m; optional tilt ∈ [−0.2, 0.2] rad).

**Degeneracy elimination**: Using a single global water_z rather than per-camera interface distances eliminates the degeneracy between camera height and interface distance. The per-camera physical gap is derived internally as h_c = water_z − C_z, preventing the two quantities from trading off independently.

**Optional tilt estimation**: When the interface normal is not constrained to [0, 0, −1], two additional degrees of freedom (rx, ry) allow the coordinate system to tilt with respect to the water surface.

#### 2.3.1 Auxiliary Camera Registration

Cameras that may degrade the joint optimization (e.g., wide-angle overview cameras with few shared observations) can be designated as auxiliary. These are excluded from Stages 2–4 and registered post-hoc against fixed board poses and water_z from Stage 3, via multi-frame refractive PnP initialization followed by a 6-parameter or 10-parameter (including fx, fy, cx, cy) refinement.

### 2.4 Stage 4: Optional Intrinsic Refinement

When enabled, Stage 4 extends the Stage 3 optimization by appending per-camera intrinsic parameters [fx, fy, cx, cy] to the parameter vector (4N additional parameters). Distortion coefficients are held fixed. This allows focal length and principal point to adjust in the presence of refraction, correcting any bias introduced during the in-air intrinsic calibration.

Bounds constrain each intrinsic parameter to [50%, 200%] of its initial value.

## 3. Refractive Geometry

### 3.1 Snell's Law (3D Vector Form)

Given an incident ray direction d, surface normal n, and refractive index ratio η = n_incident / n_transmitted:

```
cos θ_i = |d · n|
sin²θ_t = η² (1 − cos²θ_i)
```

If sin²θ_t > 1, total internal reflection occurs and the projection fails. Otherwise:

```
cos θ_t = √(1 − sin²θ_t)
d_refracted = η d + (cos θ_t − η cos θ_i) n̂
```

For air-to-water rays (η ≈ 0.750), the refracted ray bends toward the surface normal (more vertical) and total internal reflection cannot occur. For water-to-air rays (η ≈ 1.333), the refracted ray bends away from the normal and total internal reflection occurs for incidence angles exceeding arcsin(n_air / n_water) ≈ 48.6°.

### 3.2 Forward Projection: 3D Underwater Point → Pixel

The forward projection computes the pixel coordinates at which an underwater 3D point Q appears in a camera at position C, given the flat water surface at height water_z.

By the rotational symmetry of the flat interface about the vertical axis through the camera center, the problem reduces to a 1D root-finding problem for r_p, the horizontal distance from C to the interface point P where Snell's law is exactly satisfied:

```
f(r_p) = n_air · sin θ_air − n_water · sin θ_water = 0
```

where:

```
sin θ_air   = r_p / √(r_p² + h_c²)
sin θ_water = (r_q − r_p) / √((r_q − r_p)² + h_q²)
h_c = water_z − C_z       (camera-to-interface vertical gap)
h_q = Q_z − water_z       (interface-to-point vertical gap)
r_q = ‖Q_xy − C_xy‖      (total horizontal offset)
```

The function f is strictly monotonically increasing on (0, r_q) with f(0) < 0 and f(r_q) > 0, guaranteeing a unique solution and reliable convergence.

**Newton–Raphson solver**: Starting from the straight-line (pinhole) intersection r_p = r_q · h_c / (h_c + h_q), the solver iterates:

```
f'(r_p) = n_air h_c² / (r_p² + h_c²)^(3/2) + n_water h_q² / ((r_q − r_p)² + h_q²)^(3/2)
r_p ← r_p − f(r_p) / f'(r_p)
```

with clamping to [0, r_q]. Convergence to < 10⁻⁹ m is typically achieved in 2–4 iterations.

Once the interface point P = [C_x + r_p · d_x, C_y + r_p · d_y, water_z] is found, the final pixel is computed by projecting P through the standard pinhole-distortion camera model.

A Brent's method fallback is available for tilted (non-horizontal) interfaces, parameterizing the interface point by distance along the surface.

**Batch projection**: The Newton–Raphson loop is vectorized via NumPy broadcasting to project N points simultaneously, returning an (N, 2) array with NaN for invalid projections.

### 3.3 Back-Projection: Pixel → Refracted Ray

For triangulation and downstream 3D reconstruction, a pixel is back-projected to a ray in the water volume:

1. Undistort the pixel and form a unit direction vector in the camera frame; rotate to world frame via d_world = Rᵀ d_cam.
2. Intersect the world-frame ray with the Z = water_z plane.
3. Apply Snell's law (air → water) at the intersection to obtain the refracted ray direction.
4. Return the (intersection point, refracted direction) pair defining the ray in water.

### 3.4 Interface Model

The air–water interface is represented as:

- **Surface normal**: [0, 0, −1] (pointing upward, from water toward air)
- **Per-camera water_z**: All cameras share the same water_z value (the Z-coordinate of the interface plane in world frame)
- **Refractive indices**: n_air = 1.000 (default), n_water = 1.333 (default, fresh water at ~20°C)

The physical camera-to-water gap for each camera is computed internally as h_c = water_z − C_z, where C_z is the camera center's Z-coordinate in the world frame.

## 4. Optimization Engine

### 4.1 Jacobian Sparsity and Computation

Bundle adjustment problems have inherently sparse Jacobians: each observation depends only on the corresponding camera's parameters, the observed frame's board pose, and the global water_z.

The library builds an explicit binary sparsity pattern matrix relating each 2-residual observation block to the parameter blocks it depends on:

| Parameter block | Connected to residual if... |
|---|---|
| Tilt (rx, ry) | Observation is from the reference camera and tilt is estimated |
| Camera extrinsics (6) | Observation is from that camera |
| water_z (1) | Always — this is a dense column |
| Board pose (6) | Observation is from that frame |
| Camera intrinsics (4) | Observation is from that camera (Stage 4 only) |

**Sparse finite-difference Jacobian**: Rather than using the `jac_sparsity` parameter of `scipy.optimize.least_squares` (which forces the LSMR trust-region solver, which can diverge on ill-conditioned problems), the library computes the Jacobian via a custom callable. This callable uses `scipy.optimize._numdiff.approx_derivative` with the sparsity structure and column groupings from `group_columns()` to perform sparse finite differencing, then returns the result as a dense matrix. This approach combines the efficiency of sparse finite differencing (evaluating groups of structurally independent columns simultaneously) with the numerical stability of the exact QR trust-region solver.

For a typical 13-camera, 100-frame problem (~685 parameters), column grouping reduces the number of finite-difference evaluations from 685 to approximately 50 (a ~13× reduction).

For very large problems (where n_residuals × n_params > 500 million), the Jacobian is returned in sparse format and the LSMR solver is used as a fallback.

### 4.2 Robust Loss

The default configuration uses the Huber loss function (f_scale = 1.0 px), which behaves as squared loss for small residuals and transitions to linear loss for large residuals, providing robustness against outlier detections without discarding data.

## 5. Post-Calibration Capabilities

### 5.1 Point-Based Refinement

An additional API allows downstream refinement of an existing calibration using 3D-to-2D point correspondences (e.g., from tracked animal positions or manually identified landmarks). The optimization structure mirrors Stage 3 but replaces board poses with known 3D world points. Correspondences are weighted, and the optimizer scales residuals by √weight.

An optional holdout split (default 20%) is reserved for cross-validation.

### 5.2 Validation

The validation system computes:

- **Holdout reprojection error**: RMS pixel error on held-out correspondences not used during optimization.
- **Triangulation consistency**: Rays from multiple cameras are triangulated and compared against known inter-corner distances on the calibration board, both before and after refinement.
- **Camera drift detection**: Per-camera translation (mm) and rotation (degrees) shift between the original and refined calibrations, flagging cameras that exceed configurable thresholds (default: 50 mm translation, 2° rotation).

A `ValidationReport` summarizes these metrics and provides an overall accept/reject recommendation.

### 5.3 Diagnostics and Comparison

The library generates diagnostic outputs including:

- Per-camera RMS reprojection error
- Depth-stratified signed error analysis
- XY error heatmaps per depth slice
- Camera position plots (top-down view)

A multi-calibration comparison tool loads N calibration results and produces side-by-side CSV tables and PNG plots: per-camera RMS bar charts, camera position overlays, Z-position dumbbell charts, signed-error-vs-depth plots, and XY heatmap grids.

## 6. Coordinate System and Conventions

| Frame | Convention | Details |
|---|---|---|
| World | Z-down, right-handed | Origin at reference camera optical center. +X right, +Y forward, +Z down (into water). Units: meters. |
| Camera | OpenCV | +X right, +Y down, +Z forward (optical axis). Extrinsics: p_cam = R · p_world + t. Camera center: C = −Rᵀ t. |
| Pixel | Standard | (u, v) = (column, row), origin at top-left. |
| Board | Planar | Top-left interior corner at origin, all corners at Z = 0 in the board's plane. |
| Interface normal | [0, 0, −1] | Points upward, from water toward air. |

All internal computations use meters. Millimeters appear only in human-readable output.

## 7. Key Assumptions

1. **Flat water surface**: The interface is modeled as an infinite horizontal plane at a fixed Z-coordinate. Waves, surface curvature, and dynamic deformation are not modeled.
2. **Cameras in air**: All cameras are positioned above the water surface (C_z < water_z in the Z-down frame).
3. **Homogeneous media**: Constant refractive indices throughout each medium (no thermal gradients, salinity stratification, or turbidity effects).
4. **Hardware-synchronized cameras**: Frame indices are assumed consistent across all cameras.
5. **ChArUco calibration board**: A board with known geometry is placed underwater for calibration.
6. **Shared water surface height**: A single global water_z is used for all cameras, eliminating the camera-height / interface-distance degeneracy.

## 8. Software Architecture

### Public API

```python
# Pipeline entry points
run_calibration(config_path, verbose)         # End-to-end from YAML config
calibrate_from_detections(detections, ...)    # From pre-computed detections
load_config(config_path)                      # Parse YAML → CalibrationConfig

# Serialization
load_calibration(path)                        # Load CalibrationResult from JSON
save_calibration(result, path)                # Save CalibrationResult to JSON

# Post-hoc refinement
refine_calibration(result, correspondences, ...)
```

### CLI

```bash
aquacal calibrate config.yaml [-v]     # Full pipeline
aquacal init --intrinsic-dir ...       # Generate template config
aquacal compare dir1/ dir2/            # Cross-run comparison
```

### Key Data Types

| Type | Description |
|---|---|
| `CalibrationResult` | Final output: per-camera calibrations, interface parameters, board config, diagnostics, metadata |
| `CameraCalibration` | Per-camera: name, intrinsics, extrinsics, water_z, auxiliary flag |
| `CameraIntrinsics` | K (3×3), distortion coefficients, image size, fisheye flag |
| `CameraExtrinsics` | R (3×3 rotation), t (3-vector translation) |
| `InterfaceParams` | Surface normal, n_air, n_water |
| `PointCorrespondence` | 3D point + per-camera 2D observations + weight |
| `RefinementResult` | Refined calibration + validation report + acceptance flag |
| `ValidationReport` | Holdout error, triangulation consistency, per-camera drift, summary |

### Module Layout

| Module | Responsibility |
|---|---|
| `core/refractive_geometry.py` | Snell's law, forward/inverse refractive projection, ray tracing |
| `core/camera.py` | Camera and FisheyeCamera classes, projection/unprojection |
| `core/interface_model.py` | Interface representation, ray-plane intersection |
| `calibration/intrinsics.py` | Stage 1: in-air intrinsic calibration |
| `calibration/extrinsics.py` | Stage 2: BFS pose graph, refractive PnP |
| `calibration/interface_estimation.py` | Stage 3: joint refractive bundle adjustment |
| `calibration/refinement.py` | Stage 4: optional intrinsic refinement |
| `calibration/_optim_common.py` | Shared optimization: parameter packing, cost function, sparse Jacobian |
| `calibration/point_refinement.py` | Post-hoc refinement from 3D–2D correspondences |
| `calibration/pipeline.py` | End-to-end orchestration |
| `validation/` | Reprojection error, 3D reconstruction error, diagnostics, comparison |
| `config/schema.py` | All dataclasses and type definitions |
