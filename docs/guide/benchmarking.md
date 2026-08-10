# Benchmarking & Diagnostics

Every calibration run writes a `benchmark.json` into `output_dir`, a machine-readable record
of the run's environment, solver diagnostics, and accuracy. Two further diagnostic surfaces
are opt-in and written under `output_dir/internals/`: a per-iteration optimization trace CSV
and a Jacobian conditioning report (JSON + NPZ).

This page documents the `benchmark.json` fields, the optimization trace CSV columns, and the
conditioning JSON/NPZ contents, field-by-field. For the exhaustive, always-current source of
truth, see {func}`aquacal.io.assemble_benchmark_record` and {func}`aquacal.io.write_benchmark_json`
— the way [Configuration Reference](configuration.md) points at
{class}`aquacal.config.schema.CalibrationConfig` for the exhaustive dataclass field list.

## benchmark.json

Written unconditionally to `output_dir/benchmark.json` at the end of every
`run_calibration_from_config` invocation — there is no config flag to disable it.

### schema_version

An integer, currently `1`. `experiments/_render.py` refuses to process an unrecognised
`schema_version` rather than guessing at a format it does not know.

### environment

| Key | Type | Meaning |
|-----|------|---------|
| `aquacal_version` | str | Installed `aquacal` package version |
| `git_sha` | str or `null` | 40-character git commit hash, or `null` outside a git checkout |
| `git_sha_source` | str | How `git_sha` was obtained — `"git_rev_parse"` when the run was inside a git checkout, `"unavailable"` otherwise |
| `python_version` | str | `platform.python_version()` |
| `numpy_version` | str | Installed NumPy version |
| `scipy_version` | str | Installed SciPy version |
| `opencv_version` | str | Installed OpenCV version |
| `os` | str | e.g. `"Windows 11"` |
| `cpu_model` | str | Raw `platform.processor()` string |
| `cpu_count_logical` | int or `null` | `null` when `psutil` is unavailable |
| `ram_total_bytes` | int or `null` | `null` when `psutil` is unavailable |

`git_sha` and `git_sha_source` are the provenance pair a reader must check together:
`git_sha_source` records *how* the sha was obtained, so a packaged install run outside any git
checkout is visible as `git_sha: null` / `git_sha_source: "unavailable"` rather than silently
missing.

```json
"environment": {
    "aquacal_version": "1.8.0",
    "cpu_count_logical": 20,
    "cpu_model": "Intel64 Family 6 Model 154 Stepping 3, GenuineIntel",
    "git_sha": "6c7f930bb56b019067b8eb7ac1f2c84d37be645e", // pragma: allowlist secret
    "git_sha_source": "git_rev_parse",
    "numpy_version": "2.4.2",
    "opencv_version": "4.13.0",
    "os": "Windows 11",
    "python_version": "3.12.12",
    "ram_total_bytes": 16857190400,
    "scipy_version": "1.17.0"
}
```

### solver_config

| Key | Type | Meaning |
|-----|------|---------|
| `robust_loss` | str | `optimization.robust_loss` in effect for this run |
| `loss_scale` | float | `optimization.loss_scale` in effect for this run |
| `refine_intrinsics` | bool | Whether Stage 3's second (intrinsics-unlocked) pass ran |
| `interface_normal_fixed` | bool | `interface.normal_fixed` in effect for this run |
| `seed` | int | The holdout-split seed (top-level `seed` config key) |

```json
"solver_config": {
    "interface_normal_fixed": false,
    "loss_scale": 1.0,
    "refine_intrinsics": true,
    "robust_loss": "huber",
    "seed": 42
}
```

### problem_shape

| Key | Type | Meaning |
|-----|------|---------|
| `n_cameras` | int | Number of primary (non-auxiliary) cameras |
| `n_frames_calibration` | int | Frames used for the joint bundle adjustment |
| `n_frames_holdout` | int | Frames held out for validation |

```json
"problem_shape": {
    "n_cameras": 13,
    "n_frames_calibration": 200,
    "n_frames_holdout": 52
}
```

### stages

The largest section. Keys are stage names matching the three-stage model —
`stage3_interface_optimization`, `stage3_intrinsic_pass`, `auxiliary_registration`, and
per-camera sub-stage keys such as `auxiliary_registration_e3v8250`.

| Key | Type | Meaning |
|-----|------|---------|
| `nfev` | int or `null` | Residual-function evaluation count |
| `njev` | int or `null` | Jacobian evaluation count |
| `cost` | float or `null` | `0.5 * sum(fun**2)` at the solution (scipy's convention) |
| `optimality` | float or `null` | First-order optimality (`||J^T f||_inf`-style, the `gtol` criterion) |
| `status` | int or `null` | scipy's `least_squares` termination status code |
| `message` | str or `null` | scipy's termination message |
| `ftol` / `xtol` / `gtol` | float or `null` | Convergence tolerances passed to `least_squares` |
| `max_nfev_effective` | int or `null` | The effective `max_nfev` bound actually in force |
| `max_nfev_source` | str or `null` | Where `max_nfev_effective` came from, e.g. `"scipy_auto"` |
| `n_params` | int or `null` | Parameter-vector length for this stage's solve |
| `n_groups` | int or `null` | Number of finite-difference column groups |
| `n_residuals` | int or `null` | Residual-vector length for this stage's solve |
| `fd_reduction` | float or `null` | `n_params / n_groups` — the finite-difference evaluation-count reduction |
| `seconds` | float or `null` | Wall-clock time for this stage boundary |
| `*_reason` | str | Paired with any `null` field above, naming why the quantity does not exist for that stage |
| `memory` | dict | Nested per-stage memory block (see below); present only when memory capture is enabled |

```json
"stage3_interface_optimization": {
    "cost": 32429.426134429148,
    "fd_reduction": 97.61538461538461,
    "ftol": 1e-08,
    "gtol": 1e-08,
    "max_nfev_effective": 126900,
    "max_nfev_source": "scipy_auto",
    "message": "`ftol` termination condition is satisfied.",
    "n_groups": 13,
    "n_params": 1269,
    "n_residuals": 147950,
    "nfev": 44,
    "njev": 35,
    "optimality": 0.10189957507438407,
    "seconds": 1591.4336815999995,
    "status": 2,
    "xtol": 1e-08
}
```

:::{admonition} A null field always comes with a reason
:class: tip

A `null` value in a stage block always means "not applicable to this stage," never "not
measured." For example, `auxiliary_registration_e3v8250` reports `n_params: null` paired with
`n_params_reason: "register_auxiliary_camera uses dense 2-point FD; no column-grouping
structure exists at this site"` — auxiliary registration has no column-grouping structure to
report a parameter count for, so the field is honestly absent rather than a guessed zero.
:::

:::{admonition} Quote optimality to one significant figure
:class: warning

`optimality` is a first-order stopping criterion (how close the gradient is to zero at the
reported solution), not an accuracy figure. It is trustworthy only on a well-conditioned
problem — on a degenerate or near-degenerate problem it can be small even when the solution
itself is poorly determined. Never quote it beyond one significant figure, and never present it
as an error bound.
:::

### memory

`mode` and `whole_run_peak_bytes`, plus a per-stage nested `memory` block. Memory capture is
opt-in (`benchmark_memory`); `mode` labels the measurement technique — e.g.
`psutil_peak_wset` — so a number is never comparable across modes (a `psutil_peak_wset` reading
and a `tracemalloc_python_heap` reading measure different things and must not be compared).

| Key | Type | Meaning |
|-----|------|---------|
| `mode` | str | Measurement technique for the whole-run peak, e.g. `"psutil_peak_wset"` |
| `whole_run_peak_bytes` | int | Peak resident memory across the entire run |

Per-stage nested block:

| Key | Type | Meaning |
|-----|------|---------|
| `mode` | str | Measurement technique for this reading |
| `cumulative_peak_bytes_as_of_stage_end` | int | Running maximum peak memory, as of this stage's end — **not a per-stage figure** |
| `commit_peak_bytes_as_of_stage_end` | int or `null` | Peak commit/pagefile charge (Windows only) |
| `commit_current_bytes_as_of_stage_end` | int or `null` | Current commit/pagefile charge (Windows only) |
| `delta_bytes_since_previous_boundary` | int or `null` | The per-stage delta — this is the number that isolates one stage's contribution |
| `ram_total_bytes` | int or `null` | Machine's total physical RAM |

```json
"memory": {
    "mode": "psutil_peak_wset",
    "whole_run_peak_bytes": 11016843264
}
```

`cumulative_peak_bytes_as_of_stage_end` is a running maximum, not a per-stage figure — to
isolate what one stage contributed, read `delta_bytes_since_previous_boundary` instead.

### accuracy

| Key | Type | Units | Meaning |
|-----|------|-------|---------|
| `reprojection_rms` | float | pixels | Root-mean-square reprojection error on the calibration set |
| `validation_3d_error_mean` | float | metres | Mean 3D triangulation error on the held-out set |
| `validation_3d_error_std` | float | metres | Standard deviation of 3D triangulation error on the held-out set |

```json
"accuracy": {
    "reprojection_rms": 0.9276607330387148,
    "validation_3d_error_mean": 0.00025817717557395474,
    "validation_3d_error_std": 0.0005726278222075551
}
```

## Optimization trace (`internals/trace_*.csv`)

Enabled by `internals.save_optimization_trace: true`. Written as three files —
`trace_stage3.csv`, `trace_stage3_rerun.csv`, `trace_stage3_intrinsic_pass.csv` — one per
bundle-adjustment stage, never merged.

| Column | Meaning | How to read it |
|--------|---------|-----------------|
| `iteration` | Accepted `trf` iteration count | Rejected trial steps are not rows — a gap in wall-clock progress between rows with no gap in `n_fev` growth is normal |
| `n_fev` | Cumulative residual evaluations | The gap between consecutive `n_fev` values is the number of trial steps the trust region rejected before accepting this iteration |
| `cost` | `0.5 * sum` of squared robust-weighted residuals | Must be monotonically non-increasing; a jump up is a bug signal |
| `step_norm` | Norm of the accepted parameter step | A collapse toward `0` with `cost` still falling means the trust region is shrinking (fine-tuning near a minimum) |
| `optimality` | First-order optimality (the `gtol` criterion) | Should trend toward `0`; see the "Quote optimality to one significant figure" warning above |
| `water_z` | Current shared interface height, in metres | The single most useful column for watching the interface converge |
| `tilt_rx` / `tilt_ry` | Interface normal tilt | `nan` when `interface.normal_fixed: true` |

```csv
iteration,n_fev,cost,step_norm,optimality,water_z,tilt_rx,tilt_ry
1,4,9126.77891150883,0.0,2069461.4136093126,1.0309232645981559,nan,nan
2,5,5547.744091265486,0.004022699836326897,2104253.140434162,1.0309451952806004,nan,nan
3,6,5340.47922331597,0.004022888345197495,2544423.389366667,1.031217974003452,nan,nan
```

## Conditioning (`internals/conditioning.json` + `.npz`)

Enabled by `internals.save_conditioning: true`.

### JSON scalars

| Key | Type | Meaning |
|-----|------|---------|
| `condition_number` | float or `null` | `null` when non-finite — JSON has no infinity representation, so a genuinely infinite condition number is recorded as `null`, not `Infinity` |
| `singular_values` | list[float] | The full singular-value spectrum |
| `rank` | int | Numerical rank at `rank_tolerance` |
| `rank_tolerance` | float | Tolerance used to compute `rank` |
| `n_params` | int | Parameter-vector length |
| `n_residuals` | int | Residual-vector length |
| `parameter_names` | list[str] | Ordered parameter names — see "Reading the correlation matrix" below |
| `correlation_npz` | str | Filename of the sibling `.npz` holding the correlation matrix |
| `stage` | str or `null` | The bundle-adjustment stage that produced this report |

### NPZ arrays

| Array | Shape | Meaning |
|-------|-------|---------|
| `correlation` | `(n, n)` | Full parameter correlation matrix at the solution |
| `singular_values` | `(n,)` | Same spectrum as the JSON `singular_values` key |
| `parameter_names` | `(n,)` | Same ordered names as the JSON `parameter_names` key |

The `(n, n)` correlation matrix is **never** serialized to JSON — it lives only in the NPZ, for
compact storage and exact float round-trip.

### Reading the correlation matrix

Row/column *i* of `correlation` is `parameter_names[i]`. The ordering is the packed parameter
vector documented in [Optimizer Pipeline](optimizer.md)'s "Parameters Optimized" section.

```python
import numpy as np

data = np.load("internals/conditioning.npz", allow_pickle=False)
correlation = data["correlation"]
names = list(data["parameter_names"])
name_to_index = {name: i for i, name in enumerate(names)}
value = correlation[name_to_index["water_z"], name_to_index["cam1_tz"]]
```

:::{admonition} The camera-height / interface-distance block
:class: note

`water_z` and each camera's `C_z` enter the model almost entirely through their difference
`h_c = water_z - C_z` (see [Refractive Geometry](refractive_geometry.md)), so a
high-magnitude off-diagonal correlation between the interface parameter and the camera
translation-Z parameters is the degeneracy signature of a layout that fails to
constrain water surface position independently of camera height. A layout that fails to
locate the water surface is expected to show a markedly higher off-diagonal in this block
than a well-conditioned grid layout. This is stated as a hypothesis, not a measured result —
see `.planning/MANUSCRIPT-FINDINGS.md` MF-12 for the `layout/line` conditioning hypothesis
this block would be tested against. That test has not been run.
:::

## See Also

- [Configuration Reference](configuration.md) — the `internals.save_optimization_trace` /
  `internals.save_conditioning` flags that produce these files
- [Optimizer Pipeline](optimizer.md) — parameter-vector ordering, needed to read the
  conditioning correlation matrix
- [CLI Reference](cli.md) — Command-line usage and options
- [Troubleshooting](troubleshooting.md) — Diagnosing and fixing common calibration issues
