# Configuration Reference

AquaCal calibration runs are driven entirely by a YAML configuration file. All distances are
in meters. Run `aquacal init --intrinsic-dir ... --extrinsic-dir ...` to generate a starting
config scanned from your video directories, then edit it by hand for your rig.

This page documents every top-level YAML section in the order they appear in
`example_config.yaml`, plus several always-on v1.7/v1.8 behaviors that have no config key of
their own. For the exhaustive dataclass field list (including types and validation), see
{class}`aquacal.config.schema.CalibrationConfig` in the [API reference](../api/config.rst).

## board

ChArUco board geometry, used for detection and pose estimation.

| Key | Type | Default | Meaning |
|-----|------|---------|---------|
| `squares_x` | int | required | Number of chessboard squares in X direction |
| `squares_y` | int | required | Number of chessboard squares in Y direction |
| `square_size` | float | required | Square size in meters |
| `marker_size` | float | required | ArUco marker size in meters |
| `dictionary` | str | required | ArUco dictionary name (e.g. `"DICT_4X4_50"`) |
| `legacy_pattern` | bool | `false` | Set `true` if the board has a marker in the top-left cell (pre-OpenCV 4.6 pattern) |

```yaml
board:
  squares_x: 8
  squares_y: 6
  square_size: 0.030     # meters (30mm)
  marker_size: 0.022     # meters (22mm)
  dictionary: "DICT_4X4_50"
  # legacy_pattern: false
```

An optional sibling `intrinsic_board:` section (same keys) lets you use a different physical
board for in-air intrinsic calibration than for underwater extrinsic calibration. If omitted,
the `board:` section above is used for both.

## cameras

A flat list of camera names. **The first camera listed is the reference camera** — it defines
the world coordinate origin (`R = I`, `t = 0`).

```yaml
cameras:
  - cam0
  - cam1
  - cam2
  - cam3
```

Camera names are arbitrary strings matched against your video filenames (or the `--pattern`
regex passed to `aquacal init`; see the [CLI Reference](cli.md)).

Related optional lists (documented fully in the {ref}`Camera Models <camera-models>` section of
the Optimizer Pipeline guide):

- `rational_model_cameras` — cameras using the 8-coefficient rational distortion model
- `auxiliary_cameras` — cameras registered post-hoc, excluded from joint optimization
- `fisheye_cameras` — auxiliary cameras using the equidistant fisheye model (must be a subset
  of `auxiliary_cameras`)

## paths

Video file locations and where output is written.

| Key | Type | Meaning |
|-----|------|---------|
| `intrinsic_videos` | dict[str, path] | Per-camera in-air calibration video paths |
| `extrinsic_videos` | dict[str, path] | Per-camera underwater calibration video paths |
| `output_dir` | path | Directory for calibration output (created if missing) |

```yaml
paths:
  intrinsic_videos:
    cam0: "/path/to/intrinsic/cam0.mp4"
    cam1: "/path/to/intrinsic/cam1.mp4"
  extrinsic_videos:
    cam0: "/path/to/extrinsic/cam0.mp4"
    cam1: "/path/to/extrinsic/cam1.mp4"
  output_dir: "/path/to/calibration_output"
```

Every camera name in `cameras` must have an entry in both `intrinsic_videos` and
`extrinsic_videos`.

## interface

Refractive interface (air-water boundary) parameters.

| Key | Type | Default | Meaning |
|-----|------|---------|---------|
| `n_air` | float | `1.0` | Refractive index of air |
| `n_water` | float | `1.333` | Refractive index of water (fresh water at 20C) |
| `normal_fixed` | bool | `false` | If `true`, assume the interface normal is exactly `[0, 0, -1]` (perpendicular to the reference camera); if `false`, tilt is estimated |
| `initial_water_z` | dict[str, float] or `null` | `null` | Optional approximate camera-to-water-surface distances (meters) per camera. Improves Stage 3 initialization. Doesn't need to be exact — within 2-3x of the true value is sufficient. When omitted, all cameras default to 0.15m. |
| `shared_interface` | bool | `true` | Analysis/ablation option — see below |

```yaml
interface:
  n_air: 1.0
  n_water: 1.333
  normal_fixed: false
  # initial_water_z:
  #   cam0: 0.20
  #   cam1: 0.20
```

:::{admonition} shared_interface is an ablation option, not a recommended setting
:class: warning

`shared_interface` defaults to `true`: all cameras share a single global `water_z`, which is
the shared-interface assumption underlying AquaCal's central modeling claim. Setting it to
`false` gives each camera its own independently-optimized `water_z`, which exists only for
degeneracy/ablation analysis (e.g. quantifying how tightly the shared value is actually
constrained by the data). Do not use per-camera mode for production calibration — it is not a
co-equal alternative to the shared model.
:::

## optimization

Bundle-adjustment (Stage 3) settings, including the v1.7/v1.8 outlier-rejection machinery.

| Key | Type | Default | Meaning |
|-----|------|---------|---------|
| `robust_loss` | str | `"huber"` | Robust loss function: `"huber"`, `"soft_l1"`, or `"linear"` |
| `loss_scale` | float | `1.0` | Residual scale for the robust loss, in pixels |
| `max_calibration_frames` | int or `null` | `null` | Cap on frames used for the joint bundle adjustment (`null` = no limit). Stages 1-2 always use all frames. |
| `refine_intrinsics` | bool | `false` | Also optimize per-camera focal lengths and principal points in the joint refractive bundle adjustment's second pass. Only enable after the first pass converges reliably. |
| `refine_auxiliary_intrinsics` | bool | `false` | Also refine auxiliary camera intrinsics. Requires `auxiliary_cameras` to be set. Independent of `refine_intrinsics`. |
| `reject_outlier_frames` | bool | `true` | See below |
| `frame_rejection_k` | float | `5.0` | See below |
| `frame_rejection_floor_px` | float | `5.0` | See below |
| `frame_rejection_max_fraction` | float | `0.25` | See below |

```yaml
optimization:
  robust_loss: "huber"
  loss_scale: 1.0
  # max_calibration_frames: 150
  # refine_intrinsics: false
  # refine_auxiliary_intrinsics: false
  reject_outlier_frames: true
  # frame_rejection_k: 5.0
  # frame_rejection_floor_px: 5.0
  # frame_rejection_max_fraction: 0.25
```

(configuration-frame-rejection)=
### Automatic outlier-frame rejection

`reject_outlier_frames` (default `true`) runs after the main joint refractive bundle
adjustment: per-frame reprojection RMS is scored against **independently estimated**
per-frame board poses (not the poses from the joint solve, which would be circular), any
catastrophic outliers are dropped, and the bundle adjustment is re-run once on the cleaned
set. This is a no-op on clean data, so the default only matters for datasets with genuinely
bad frames (board out of water, rippled surface, mis-detections).

Three keys tune the rejection threshold:

- `frame_rejection_k: 5.0` — a frame is flagged if its per-frame RMS exceeds `k` times the
  median per-frame RMS.
- `frame_rejection_floor_px: 5.0` — a frame must *also* exceed this absolute pixel floor to be
  rejected, regardless of the relative bound. This prevents over-rejection when the median RMS
  is already tiny.
- `frame_rejection_max_fraction: 0.25` — guardrail. If more than this fraction of frames would
  be dropped, rejection is suppressed entirely and a warning is emitted, so a broadly
  contaminated dataset surfaces loudly instead of being silently gutted.

See {ref}`Contaminated Frames <contaminated-frames>` in the Troubleshooting guide for the
diagnostic workflow this pairs with.

## detection

Corner-detection thresholds and frame sampling, including the v1.7 frame-trimming options.

| Key | Type | Default | Meaning |
|-----|------|---------|---------|
| `min_corners` | int | `8` | Minimum corners per frame to use a detection |
| `min_cameras` | int | `2` | Minimum cameras that must see the board for a frame to be used |
| `frame_step` | int | `1` | Process every Nth frame (`1` = all frames) |
| `start_frame` | int or `null` | `0` | See below |
| `stop_frame` | int or `null` | `null` | See below |

```yaml
detection:
  min_corners: 8
  min_cameras: 2
  frame_step: 5
  # start_frame: 0
  # stop_frame: null
```

:::{admonition} YAML key vs. dataclass field name
:class: tip

The frame-trim YAML keys do not match their `CalibrationConfig` field names one-for-one:
`detection.start_frame` maps to `CalibrationConfig.extrinsic_start_frame`, and
`detection.stop_frame` maps to `CalibrationConfig.extrinsic_stop_frame`. The rename exists in
code to make clear these only apply to the extrinsic-stage frame iterator.
:::

(configuration-frame-trimming)=
### Manual frame trimming (`start_frame` / `stop_frame`)

`start_frame` (inclusive) and `stop_frame` (exclusive) trim the range of frames processed in
the **extrinsic** calibration videos. The trim is applied uniformly across all extrinsic
cameras via a single synchronized frame iterator, so frame-index alignment (video sync) is
preserved; it has no effect on the intrinsic calibration videos.

Use this to skip contaminated segments at the start (board being lowered in, surface still
settling) or end (board being lifted out) of a capture. The discrimination rule between this
and automatic outlier rejection: automatic rejection reliably catches *discrete* catastrophic
frames wherever they occur, but a *contiguous segment of mildly* contaminated frames (each only
a few pixels off) may never exceed a safe rejection threshold. For those, prefer trimming by
`start_frame` / `stop_frame` — position in the capture is the meaningful signal there, not
per-frame RMS. See {ref}`Contaminated Frames <contaminated-frames>` in the Troubleshooting
guide for the full diagnostic workflow.

## validation

Held-out validation settings.

| Key | Type | Default | Meaning |
|-----|------|---------|---------|
| `holdout_fraction` | float | `0.2` | Fraction of frames held out for validation (selected whole, not per-detection) |
| `save_detailed_residuals` | bool | `true` | Save per-corner residual data |

```yaml
validation:
  holdout_fraction: 0.2
  save_detailed_residuals: true
```

## internals

Opt-in diagnostic artifact dumps under `output_dir/internals/`, introduced for experiment
observability. Bare key list — see {class}`aquacal.config.schema.CalibrationConfig` for full
semantics of each flag.

| Key | Type | Default | Meaning |
|-----|------|---------|---------|
| `save_stage_calibrations` | bool | `true` | Dump each bundle-adjustment stage's intermediate calibration as loadable JSON |
| `save_optimization_trace` | bool | `false` | Per-iteration CSV trace (cost, step norm, optimality) for each bundle-adjustment stage — see [Benchmarking & Diagnostics](benchmarking.md) for the CSV column schema |
| `save_conditioning` | bool | `false` | Jacobian singular-value spectrum and full parameter correlation matrix at the solution. Expensive — off by default. — see [Benchmarking & Diagnostics](benchmarking.md) for the JSON/NPZ schema |
| `save_benchmark` | bool | `true` | Write `output_dir/benchmark.json`, the run's machine-readable environment / solver-diagnostic / accuracy record. Cheap, on by default — see [Benchmarking & Diagnostics](benchmarking.md) for the field-by-field schema |
| `benchmark_memory` | bool | `false` | Add the per-stage-boundary peak-RSS `memory` block to `benchmark.json`. This is the **only** switch that produces that block — see [Benchmarking & Diagnostics](benchmarking.md) for the `memory` section, which is absent from the file without it |

```yaml
internals:
  save_stage_calibrations: true
  # save_optimization_trace: false
  # save_conditioning: false
  # save_benchmark: true
  # benchmark_memory: false
```

## seed

Top-level integer, threaded into the calibration/validation frame holdout split for
reproducibility.

| Key | Type | Default | Meaning |
|-----|------|---------|---------|
| `seed` | int | `42` | Master seed controlling the holdout split |

```yaml
seed: 42
```

## In-air intrinsic calibration behavior

Two v1.8 behaviors affect Stage 1 (in-air intrinsic calibration) but have **no config key** —
they are always-on.

### Seeded `cv2.calibrateCamera` initial guess

:::{admonition} Why AquaCal seeds the intrinsic guess
:class: tip

`cv2.calibrateCamera` is invoked with `CALIB_USE_INTRINSIC_GUESS` and a physically plausible
seed — `fx = fy = max(image width, image height)`, principal point at the image center —
instead of letting OpenCV fall back to its default DLT/homography-based auto-init.

The homography-based auto-init can be badly ill-conditioned for some board-pose distributions,
sending the nonlinear refinement into a wildly wrong local minimum (fx off by 2-3x, with huge,
physically implausible distortion coefficients) even though the same detections converge
cleanly from a sane starting point. Because this then poisons extrinsic initialization
downstream, AquaCal always supplies the seed. It has been verified to reproduce the unguided
result to 6+ significant figures for well-behaved cameras, so it is a safe default in every
case — there is nothing to configure.

See `src/aquacal/calibration/intrinsics.py` (around `calibrate_intrinsics_single`) for the
implementation.
:::

### Fronto-parallel view-diversity warning

:::{admonition} "calibration board views are nearly fronto-parallel"
:class: warning

After in-air calibration, {func}`aquacal.calibration.intrinsics.validate_view_diversity`
inspects the distribution of board-view tilt angles. Focal length is recovered from
perspective foreshortening: when every board view is close to fronto-parallel, the projection
is nearly a pure scaling and focal length becomes degenerate with board distance — fx and
board-Z can trade off almost exactly with no meaningful change in reprojection error, so a
self-consistent but badly wrong fx can pass Stage 1's own residual checks.

If the 90th-percentile tilt across your calibration views falls below 15 degrees, a
`UserWarning` naming the camera is emitted. **What to do:** re-shoot the in-air calibration
video with the board held at varied orientations (roughly +/-30 degrees about both axes) so
the degeneracy is broken, then re-run calibration.
:::

## See Also

- [CLI Reference](cli.md) — Command-line usage and options
- [Optimizer Pipeline](optimizer.md) — Understanding the calibration stages
- [Troubleshooting](troubleshooting.md) — Diagnosing and fixing common calibration issues
- [Glossary](glossary.md) — Definitions of key terms
- [Benchmarking & Diagnostics](benchmarking.md) — `benchmark.json`, trace CSV, and conditioning output schemas
