# Tutorial 03: Calibrate the Real Rig from the Command Line

This tutorial walks through a complete AquaCal calibration of a real 13-camera underwater rig,
driven entirely by the `aquacal` command-line tool, and reproduces the numbers published in the
AquaCal paper's Section 3. You will download the published Zenodo dataset, run the CLI against
two different configurations, and confirm your local output matches the paper's reference
numbers file-for-file — not by eyeballing a console transcript, but by diffing your own JSON
output against a file inside the archive itself.

This is the only tutorial in this documentation that uses real hardware data — [Tutorial
01](01_full_pipeline.ipynb) and [Tutorial 02](02_synthetic_validation.ipynb) are both fast,
synthetic-only notebooks. **Prerequisites:** `pip install aquacal`, and roughly 4.4 GB of free
disk space for the dataset (downloaded once and cached).

## 1. Get the dataset

The dataset is fetched through {func}`aquacal.datasets.load_example`, which downloads the
archive from Zenodo, validates its checksum against the manifest shipped with the package,
extracts it, and caches it locally:

```bash
python -c "from aquacal.datasets import load_example; print(load_example('real-rig').cache_path)"
```

This downloads and extracts about 4.4 GB exactly once — subsequent calls return the cached path
immediately, so it is safe to call `load_example('real-rig')` at the start of any script. The
command prints the directory the archive was extracted to; that directory has the following
layout:

```text
real-rig/
├── README.md                              # dataset description
├── config_paper.yaml                      # frame_step: 1 over pre-subsampled frames -- REPRODUCES Section 3
├── config_quickstart_not_paper.yaml       # frame_step: 5 -- fast first contact, does NOT reproduce Section 3
├── reference_calibration.json             # copy of the paper run's calibration, read by load_example()
├── extrinsic/<camera>/frame0000.png ... frame0261.png   # 13 cameras x 262 underwater frames
├── intrinsic/<camera>/frame0000.png ...                 # 13 cameras, ragged frame counts (in-air)
└── reference_outputs/                     # the paper run's own outputs
    ├── calibration.json
    ├── diagnostics.json
    ├── reprojection_residuals.csv
    ├── reconstruction_errors.csv
    ├── exp2_spatial_errors.csv
    └── interface_ablation_conditioning.npz
```

:::{admonition} Two configs ship in this archive
:class: warning

`config_paper.yaml` reproduces the paper's Section 3 numbers exactly, and takes roughly 50
minutes. `config_quickstart_not_paper.yaml` subsamples the frames for a fast first run — its
numbers **do not** reproduce Section 3 and must not be quoted as a reference result. Use it only
to confirm your environment works before committing to the full run.
:::

## 2. A fast first run

`cd` into the cache directory printed in step 1, then run the quickstart config with verbose
output:

```bash
aquacal calibrate config_quickstart_not_paper.yaml -v
```

`-v` surfaces optimizer progress as the run proceeds; `python -u` is only needed when piping
output to a file or log, since Python otherwise block-buffers stdout on a pipe. Watch for the
three-stage model in the console output — in-air intrinsic calibration, extrinsic
initialization via best-first pose-graph traversal, and joint refractive bundle adjustment —
always exactly three stages. This run writes its results into `output/` inside the cache
directory.

**This run's numbers are not a reference result.** Its purpose is only to confirm the pipeline
runs end-to-end on your machine quickly. Compare against Section 3 only after the full run in
step 3. On most machines this quickstart run completes in a few minutes — a useful sanity check
before committing to the ~50-minute full run.

## 3. Reproduce the paper's numbers

```bash
aquacal calibrate config_paper.yaml -v
```

This run takes roughly 50 minutes and peaks at roughly 11 GiB of memory on a 16 GB machine —
give it the machine to itself. It writes its results into `output/`, overwriting the quickstart
run's output from step 2. If you want to keep both runs, pass `-o path/to/output` (or
`--output-dir`) to redirect one of the two invocations before running the second.

### What you should see

Every number in this table is read from `reference_outputs/diagnostics.json` inside the
archive — the paper run's own output — so you can diff your `output/diagnostics.json` against
it directly.

**These values were produced under OpenCV 4.13.0.** ChArUco corner detection is entirely
OpenCV's (AquaCal calls `cv2.aruco.CharucoDetector` directly), so a different OpenCV minor
version can detect a slightly different corner set and move every number below at the ~1–10%
level with nothing wrong on either side — measured between 4.13.0 and 4.14.0: 1.95% fewer
corner observations, `reconstruction.rmse` +7.8%, mean reprojection +1.1%. Check yours with
`python -c "import cv2; print(cv2.__version__)"`, and note that your own run's
`output/benchmark.json` records it under `environment.opencv_version`. AquaCal pins
`opencv-python==4.13.*` so a plain install reproduces the table; if you have deliberately
installed a different minor, expect small offsets rather than a matching diff.

| Quantity | Reference value | Where it comes from |
|---|---|---|
| Mean reprojection error | 0.82404 px | `reference_outputs/diagnostics.json` -> mean of the 12 values in `reprojection.per_camera` |
| Per-camera reprojection range | 0.55372 px (`e3v829d`) - 2.08155 px (`e3v83f0`) | `reference_outputs/diagnostics.json` -> `reprojection.per_camera` |
| Auxiliary fisheye camera reprojection | 14.85638 px | `reference_outputs/diagnostics.json` -> `auxiliary_cameras.e3v8250.reprojection_rms` |
| Inter-corner mean absolute error | 0.00025818 m | `reference_outputs/diagnostics.json` -> `reconstruction.mean` |
| Inter-corner RMSE | 0.00062814 m | `reference_outputs/diagnostics.json` -> `reconstruction.rmse` |
| Mean relative error | 0.43030 % | `reference_outputs/diagnostics.json` -> `reconstruction.percent_error` |
| Comparisons | 7762 | `reference_outputs/diagnostics.json` -> `reconstruction.num_comparisons` |
| Recovered water_z | 1.07384 m | `reference_outputs/diagnostics.json` -> `camera_heights.water_z` |
| Camera height range | 1.04718 m (`e3v83f0`) - 1.11250 m (`e3v83ee`) | `reference_outputs/diagnostics.json` -> `camera_heights.per_camera_height` |

A pasted console transcript is not a substitute for this table — always diff your own
`output/diagnostics.json` against the archive's `reference_outputs/diagnostics.json` rather than
trusting a number copied from prose. Small numerical differences (well below the table's
significant figures) can appear across machines due to floating-point non-determinism in
parallelized linear algebra; large differences indicate the wrong config was used, or that the
environment does not match the one this tutorial assumes. The concrete diff command:

```bash
python -c "import json; d=json.load(open('output/diagnostics.json')); r=json.load(open('reference_outputs/diagnostics.json')); print(d['reconstruction']['num_comparisons'], r['reconstruction']['num_comparisons'])"
```

Both numbers printed should be `7762`.

## 4. Inspect the result

Compare your run directly against the archive's reference calibration with `aquacal compare`:

```bash
aquacal compare output/ reference_outputs/ -o comparison_output/
```

This writes `metrics_summary.csv`, `per_camera_metrics.csv`, `parameter_diffs.csv`, and several
PNG plots (`rms_bar_chart.png`, `position_overlay.png`, `z_position_dumbbell.png`,
`xy_error_heatmaps.png`) to `comparison_output/`, letting you see per-camera differences between
your run and the paper's. When both directories carry reconstruction data, `aquacal compare`
additionally writes `depth_error_comparison.png` and `depth_binned_errors.csv`, breaking
reconstruction error down by depth.

`output/` also contains `calibration.json` (the loadable calibration result),
`spatial_measurements.csv` and `reprojection_residuals.csv` (per-corner residuals), plus
`benchmark.json` (solver diagnostics and peak memory). If you enabled the optional
`internals.save_optimization_trace` or `internals.save_conditioning` config flags, you will
also find per-iteration trace CSVs and a conditioning `.npz` under `output/internals/`. See the
[Benchmarking & Diagnostics](../guide/benchmarking.md) guide page for the field-by-field schema of
all three.

## 5. Run it on your own rig

To calibrate your own multi-camera rig, generate a starting config by scanning your own
intrinsic and extrinsic video directories:

```bash
aquacal init --intrinsic-dir /path/to/in_air_videos --extrinsic-dir /path/to/underwater_videos
```

Edit the generated `config.yaml` — measure your physical ChArUco board, fill in refractive
indices, and adjust detection/optimization settings — before running `aquacal calibrate`. The
same three-stage pipeline you just ran against the archive runs identically against your own
rig; the only difference is the config file and video directories you point it at.

See the [Configuration Reference](../guide/configuration.md) for every YAML key and the [CLI
Reference](../guide/cli.md) for the full command-line surface, including `aquacal compare` for
comparing multiple runs against each other once you have more than one calibration to evaluate.

## Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| Checksum mismatch on download | Partial or interrupted download | Delete the dataset cache directory and re-run `load_example('real-rig')` to re-download |
| `0 frames detected` / video reading returns nothing | Wrong Python environment | Run inside the AquaCal environment, not a bare system Python — OpenCV's video backend can silently fail to decode frames in an unrelated environment |
| Calibration process killed / out of memory | `config_paper.yaml` needs roughly 11 GiB peak memory | Close other applications before running, or use `config_quickstart_not_paper.yaml` for a lighter first pass |
| Numbers don't match Section 3 | Ran the wrong config | Confirm you ran `config_paper.yaml`, not `config_quickstart_not_paper.yaml` — only the paper config reproduces Section 3 |
| Numbers are close but off by ~1–10%, with the right config | Different OpenCV version | The reference values came from **OpenCV 4.13.0**, and corner detection changes across minor versions. Check with `python -c "import cv2; print(cv2.__version__)"` and compare against `environment.opencv_version` in your `output/benchmark.json`; `pip install "opencv-python==4.13.*"` to match. Neither version is more correct — this shifts the numbers, it does not break the calibration |
| `aquacal calibrate` exits with code `2` | Config file failed validation | Run `aquacal calibrate <config> --dry-run` to see the specific validation error without running the full pipeline |
| Download stalls indefinitely | No internet access on first run | The archive is fetched from Zenodo on first call to `load_example`; confirm network access, then retry |
| `output/` from step 2 was overwritten before you could inspect it | Both steps 2 and 3 write to the default `output/` | Re-run step 3 with `-o output_paper/` to keep the two runs' outputs separate |

## See Also

- [CLI Reference](../guide/cli.md) — full command-line syntax, options, and exit codes
- [Configuration Reference](../guide/configuration.md) — every YAML configuration key
- [Benchmarking & Diagnostics](../guide/benchmarking.md) — reading `benchmark.json`, optimizer
  traces, and conditioning diagnostics
- [Tutorial 01: Calibrate Your Rig](01_full_pipeline.ipynb) — the synthetic, Python-API
  walkthrough
- [Tutorial 02: Why Refractive Calibration Matters](02_synthetic_validation.ipynb) — synthetic
  refractive-vs-non-refractive comparison
