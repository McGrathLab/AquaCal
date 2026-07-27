# `experiments/` — paper experiment scripts

This directory holds the scripts that produce the SoftwareX manuscript's numbers and
figure inputs. It is **not part of the installed `aquacal` package**:
`pyproject.toml`'s `[tool.setuptools.packages.find]` scopes discovery to
`where = ["src"]`, so `experiments/` never ships in the wheel regardless of what lives
here. Each script is invoked directly as a module:

```bash
python -m experiments.e1_refractive_comparison
python -m experiments.e2_real_rig
python -m experiments.e7_interface_ablation
```

`experiments/` is linted (`ruff`) and covered by `pre-commit run --all-files` like the
rest of the repo, but it is **not pytest-collected** — its own logic is unit-tested
under `tests/unit/test_experiments_*.py` (schema, CLI parsing, the `--check` comparator),
and its measurement logic lives in `aquacal.datasets.pipelines` (the library computes;
the experiment orchestrates and writes files — P2/P3).

## 1. The uniform CLI contract

Every script in this directory shares one `argparse` parent
(`experiments._io.build_experiment_arg_parser`), giving each of them the identical five
flags:

| Flag | Default | Meaning |
|---|---|---|
| `--seed` | `42` | Random seed for scenario/detection generation. |
| `--out` | `experiments/results/` | Output directory for this experiment's artifacts. |
| `--force` | off | Overwrite existing per-configuration output files instead of skipping them. |
| `--smoke` | off | Run a fast, reduced-size variant that exercises the code paths without a full calibration — this is what CI's `experiments-smoke` job runs. |
| `--check` | off | Recompute fresh, compare against the committed baseline at a numeric tolerance, and print the worst offending cell. Never writes. |

`--check` and `--force` are **mutually exclusive** and this is enforced as a hard error
(`parser.error(...)`), not a silent preference for either flag — a script that quietly
picked one over the other would make it too easy to accidentally overwrite a committed
baseline while trying to verify it, or vice versa.

`--check` compares **numerically**, at a tolerance declared as a module constant in each
script (`CHECK_RTOL`, currently `1e-6` in every script), rather than byte-for-byte. A
strict byte compare across platforms fails on ordinary BLAS-level last-digit differences
in the nonlinear least-squares solver's exact convergence trajectory — and the
predictable consequence of a check that fails on harmless noise is that someone disables
the check entirely, which is precisely the determinism failure `--check` exists to catch.
Non-float columns still compare exactly; only float columns get the tolerance.
Determinism itself (sorted-key CSV writing, comparator correctness) is asserted
separately by unit tests, not by `--check` runs against a moving baseline.

## 2. Provenance table

One row per artifact committed under `experiments/results/`. Every runtime below is a
**measured** value from this phase's wave-3/4 execution, not a pre-run estimate.

| Paper artifact | Experiment | Command | Output file(s) | Figure generator | Runtime |
|---|---|---|---|---|---|
| §3 focal drift, RMS px, per-camera parameter errors | E1 | `python -m experiments.e1_refractive_comparison` | `exp1_parameter_errors.csv` | `figures/aquacal/synthetic_validation.py` | ~20 min (19.1-06-SUMMARY.md records ~90 min total across four calibration-pairs run during this phase — a `--check` pair, an isolated headline-verification pair, and a `--force` pair — i.e. ~20-25 min per default two-model, eight-depth invocation) |
| Depth-generalization RMSE/signed-error curves | E1 | ″ | `exp2_depth_generalization.csv` | ″ | (same run) |
| Exp-2 spatial-error heatmaps | E1 | ″ | `exp2_spatial_errors.csv` (gitignored — no committed baseline, D-20; ~11 MB, exceeds the repo's 1000 KB `check-added-large-files` gate; regenerate on demand with `--force`) | ″ | (same run) |
| XY-vs-Z anisotropy ratios | E1 | ″ | `exp3_xy_vs_z_anisotropy.csv` | ″ | (same run) |
| E1's two direct-call provenance records (one per model, since E1 calibrates twice) | E1 | ″ | `e1_benchmark_refractive.json`, `e1_benchmark_nonrefractive.json` | — (provenance only) | (same run) |
| §3 real-rig: mean/per-camera reprojection, auxiliary fisheye RMS, inter-corner MAE/RMSE, comparison count | E2 | `python -m experiments.e2_real_rig --config <release config>` | `real_rig_metrics.json` | — (prose) | ~50 min (full local-frameset run against the release config; see `19.1-E2-FRAMESET-PROVENANCE.md`) |
| Fig. `aquacal_zenodo_camera_rig_3d.pdf` — camera positions, recovered water surface `z_w`, per-camera heights | E2 | ″ | `camera_parameters.csv` (**not** `calibration.json` — D-14's correction; the figure generator reads three CSVs, never the calibration JSON) | `figures/aquacal/zenodo_e2e.py` | (same run) |
| 3D reconstruction error distribution | E2 | ″ | `reconstruction_errors.csv` | ″ | (same run) |
| Reprojection error histogram | E2 | ″ | `reprojection_residuals.csv` | ″ | (same run) |
| E2's genuine pipeline-written provenance record (E2 is the one experiment that goes through `run_calibration`, so this is not a hand-rolled sidecar) | E2 | ″ | `benchmark.json` (copied, not reconstructed) | — (provenance only) | (same run) |
| The run's primary calibration artifact | E2 | ″ | `calibration.json` (copied, not reconstructed) | — (raw result, not a figure input) | (same run) |
| R4.2/R4.3 ablation table + trace panel | E7 | `python -m experiments.e7_interface_ablation` | `interface_ablation.csv` (48 rows: 4 arms x 12 cameras) | new figure module (Phase 19.2) | ~7 min for all four arms (measured; regenerable via `--force`) |
| Conditioning / singular-value spectrum, height-distance correlation | E7 | ″ | `interface_ablation_conditioning.json` (+ a gitignored `.npz` — 3.1 MB of dense correlation matrices, exceeds the repo's large-file gate; all scientific content is in the committed `.json`) | ″ | (same run) |
| Per-arm optimizer convergence traces | E7 | ″ | `e7_trace_shared_fixed.csv`, `e7_trace_shared_refined.csv`, `e7_trace_percamera_fixed.csv`, `e7_trace_percamera_refined.csv` | ″ | (same run) |
| E7's four per-arm direct-call provenance records | E7 | ″ | `e7_benchmark_shared_fixed.json`, `e7_benchmark_shared_refined.json`, `e7_benchmark_percamera_fixed.json`, `e7_benchmark_percamera_refined.json` | — (provenance only) | (same run) |

`e4_benchmark_grid.py` is present in this directory as a **relocated skeleton only**
(D-03: it is `benchmarks/sweep_runner.py`, moved here by `git mv` and not rewritten in
substance). **It is deliberately not run in this phase.** Running the cameras-x-frames
grid is Phase 19.2 / EXP-08 — a single 13-camera calibration run already takes
48-87 minutes (`CLAUDE.md`), so a real sweep is out of scope for this phase's automated
verification.

## 3. E2 has two invocation paths — read this before citing a number

`python -m experiments.e2_real_rig` (no `--config`) runs against the **published Zenodo
archive**. This is the path a reader without the raw videos follows, and it is the
default so that path stays available. It currently reproduces a **1,817-comparison**
run (60 usable frames -> 12 validation frames), not the manuscript's §3 numbers.

`python -m experiments.e2_real_rig --config <release config>` runs the **full frameset**
from local raw videos (`Desktop\Aqua\AquaCal\raw_videos\`) using the same
`detection.frame_step: 30` / `optimization.max_calibration_frames: 200` /
`validation.holdout_fraction: 0.2` settings as the release calibration, and reproduces §3
**exactly** — all nine named quantities at 0.000% delta, 7,762 comparisons (see
`19.1-E2-DELTA-TABLE.md`).

**The published Zenodo archive currently ships only the smaller, 60-frame extraction.**
A reader following the default (no-`--config`) path today reproduces the
1,817-comparison numbers, not §3's. Closing that gap — regenerating the published
archive to the full frameset — is tracked as **DATA-01a** in Phase 21 and is a
prerequisite for publication, not a nice-to-have (`19.1-E2-FRAMESET-PROVENANCE.md`).
The committed CSVs in `experiments/results/` come from the full-frameset local-video run,
which the published archive cannot currently reproduce; that gap closes when Phase 21's
DATA-01/02/03 lands.

## 4. The gauge-freedom correction

A per-camera Z position error is only meaningful up to the world frame's Z datum, which
the reference camera (`cam0`) pins at zero by construction — it sits at the world-frame
origin, `p_cam = R @ p_world + t`. Without correction, a global datum offset that the
optimizer applied to the entire rig (an artifact of *where* "Z=0" is chosen, not a real
geometric error) gets charged entirely to the non-reference cameras while the reference
camera's own near-zero raw error is left uncorrected, confounding any cross-camera Z-error
comparison.

`aquacal.datasets.pipelines.compute_per_camera_errors(..., gauge_correct_z=True)` (E1
passes `True`; the default is `False` so no existing caller's behavior changes) subtracts
the mean raw Z error of the non-reference ("free") cameras from **every** camera's Z
error, including the reference camera's own. This is why a reference camera's row reads:

- `xy_position_error_mm == 0.0` — the reference camera is pinned at the world origin, a
  separate, purely geometric fact with zero optimizable freedom, unrelated to the Z
  correction.
- `z_position_error_mm` after correction is a **small nonzero residual**, not `0.0` — the
  correction reveals the systematic Z shift the model applied to the whole rig, which is
  a real (if small) quantity, not an artifact of the reference camera's fixed position.

## 5. What "fixed intrinsics" means in E7

E7's two fixed-intrinsics arms hold camera intrinsics at `scenario.intrinsics` — ground
truth (`intrinsics_source = ground_truth_fixed` in the emitted CSV) — not at an
independently-estimated in-air Stage-1 calibration. This is deliberate, not a shortcut:
E7's primary result is a **geometric degeneracy** in the extrinsics/interface
parameterization, which exists regardless of intrinsic accuracy. Perturbing the
intrinsics would inject a second, unrelated error source (focal error propagating into
recovered height) into an arm whose whole purpose is isolating the first one. Because the
intrinsics are exact, no focal error can propagate into the recovered heights — this
makes the fixed-intrinsics, per-camera arm the **strongest possible case** for per-camera
mode, and a degeneracy demonstrated under best-case conditions is the stronger claim,
because noise cannot be blamed for it.

## 6. How to read E7's output

The failure E7 demonstrates is a **height/distance** degeneracy
(`C_z_i` against `water_z_i` — the per-camera height and per-camera interface distance),
**never** a focal-length or standoff-distance failure. Naive per-camera mode packs `N`
free `water_z_i` parameters beside `N` free camera centers `C_z_i`; only the *sum*
(`camera_height + water_z`, the absolute surface height) is physically meaningful and
must be common to all cameras, because every camera in the rig looks through the same
flat surface — but nothing in that parameterization enforces it, and a fixed sum with
compensating errors in each addend fits the 2D observations equally well.

`reprojection_rms_px_control` is a recorded **control**, not evidence: a height/distance
degeneracy is a flat cost valley, so RMSE stays low in both the shared and per-camera
arms even though the per-camera arm's recovered heights scatter by more than a
centimeter across cameras that physically share one water surface. If RMSE had also
degraded sharply in the per-camera arm, the flat-valley framing would need
re-examining — the column is explicitly suffixed `_control` rather than presented as if
it were the finding.

The refine-intrinsics-ON arms are **AquaCal's own design rationale for importing
Stage-1 in-air intrinsics** rather than re-deriving them jointly with everything else —
they are **not** "what CalibMar produces." CalibMar solves each camera independently in
its own local frame and has no such redundancy; it works correctly in its intended
regime. The refine-ON arms here measure a design choice AquaCal made for its own
architecture, not a competing tool's behavior.

## 7. Reproducing a number

```bash
# E1 — synthetic refractive-vs-non-refractive comparison (~20 min)
python -m experiments.e1_refractive_comparison --check   # compare fresh vs. committed
python -m experiments.e1_refractive_comparison --force   # regenerate the committed CSVs

# E2 — real-rig re-run against the published archive (a reader's default path)
python -m experiments.e2_real_rig

# E2 — real-rig re-run against the full local-video frameset (reproduces §3 exactly)
python -m experiments.e2_real_rig --config <path/to/release/config.yaml>

# E7 — shared-vs-per-camera interface ablation (~7 min, four arms)
python -m experiments.e7_interface_ablation --force
```

Every committed result has a `benchmark.json`-shaped provenance record next to it
(`schema_version: 1`) carrying its seed, AquaCal version, git SHA, and the Python/NumPy/
SciPy/OS environment it ran under — either the genuine pipeline-written record (E2, via
`run_calibration_from_config`) or a direct-call record assembled from the same pure
`aquacal.io.assemble_benchmark_record` (E1, E7 — both call `calibrate_synthetic`
directly and never touch the pipeline's own config-driven entry point, so there is no
pipeline `benchmark.json` for them to reuse). No experiment invents a second sidecar
format.
