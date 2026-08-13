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

One row per artifact committed under `experiments/results/`. Every artifact below now has a
genuine four-field provenance record behind it — seed, AquaCal version, git SHA, and the
Python/NumPy/SciPy/OS environment — whether that record is a `benchmark.json`-shaped file
(E1, E2, E4, E7), a minimal calibration-free sidecar (E3's `e3_provenance.json`), or the
provenance sidecars wave 5 added for E5 and E6 (`e5_provenance.json`, `e6_provenance.json`).
This is a change from earlier in the phase: before wave 5 (plans 19.2-16/19), E5 and E6
carried only a `seed` column with no version/SHA/environment fields, and this section's
opening claim narrowed for them a few paragraphs down without saying so. See §2's closing
paragraph (below the table) for exactly which record covers which artifact, asserted
mechanically by `tests/unit/test_experiments_provenance.py`.

Every runtime below is a **measured** value from this phase's wave-3/4/5 execution, not a
pre-run estimate.

| Paper artifact | Experiment | Command | Output file(s) | Figure generator | Runtime |
|---|---|---|---|---|---|
| §3 focal drift, RMS px, per-camera parameter errors | E1 | `python -m experiments.e1_refractive_comparison` | `exp1_parameter_errors.csv` | `DissertationFigures/src/dissertationfigures/figures/aquacal/synthetic_validation.py` (a different repository) | ~20 min (19.1-06-SUMMARY.md records ~90 min total across four calibration-pairs run during this phase — a `--check` pair, an isolated headline-verification pair, and a `--force` pair — i.e. ~20-25 min per default two-model, eight-depth invocation) |
| Depth-generalization RMSE/signed-error curves | E1 | ″ | `exp2_depth_generalization.csv` | ″ | (same run) |
| Exp-2 spatial-error heatmaps | E1 | ″ | `exp2_spatial_errors.csv` (gitignored — no committed baseline, D-20; ~11 MB, exceeds the repo's 1000 KB `check-added-large-files` gate; regenerate on demand with `--force`) | ″ | (same run) |
| XY-vs-Z anisotropy ratios | E1 | ″ | `exp3_xy_vs_z_anisotropy.csv` | ″ | (same run) |
| E1's two direct-call provenance records (one per model, since E1 calibrates twice) | E1 | ″ | `e1_benchmark_refractive.json`, `e1_benchmark_nonrefractive.json` | — (provenance only) | (same run) |
| §3 real-rig: mean/per-camera reprojection, auxiliary fisheye RMS, inter-corner MAE/RMSE, comparison count | E2 | `python -m experiments.e2_real_rig --config <release config>` | `real_rig_metrics.json` | — (prose) | ~50 min (full local-frameset run against the release config; see `19.1-E2-FRAMESET-PROVENANCE.md`) |
| Fig. `aquacal_zenodo_camera_rig_3d.pdf` — camera positions, recovered water surface `z_w`, per-camera heights | E2 | ″ | `camera_parameters.csv` (**not** `calibration.json` — D-14's correction; the figure generator reads three CSVs, never the calibration JSON) | `DissertationFigures/src/dissertationfigures/figures/aquacal/zenodo_e2e.py` (a different repository) | (same run) |
| 3D reconstruction error distribution | E2 | ″ | `reconstruction_errors.csv` — **not in this repo**, see DATA-01b below | ″ | (same run) |
| Reprojection error histogram | E2 | ″ | `reprojection_residuals.csv` — **not in this repo**, see DATA-01b below | ″ | (same run) |
| E2's genuine pipeline-written provenance record (E2 is the one experiment that goes through `run_calibration`, so this is not a hand-rolled sidecar) | E2 | ″ | `benchmark.json` (copied, not reconstructed) | — (provenance only) | (same run) |
| The run's primary calibration artifact | E2 | ″ | `calibration.json` (copied, not reconstructed) — **not in this repo**, see DATA-01b below | — (raw result, not a figure input) | (same run) |
| R4.2/R4.3 ablation table + trace panel | E7 | `python -m experiments.e7_interface_ablation` | `interface_ablation.csv` (48 rows: 4 arms x 12 cameras) | new figure module (Phase 19.2) | ~7 min for all four arms (measured; regenerable via `--force`) |
| Conditioning / singular-value spectrum, height-distance correlation | E7 | ″ | `interface_ablation_conditioning.json` (+ a gitignored `.npz` — 3.1 MB of dense correlation matrices, exceeds the repo's large-file gate; all scientific content is in the committed `.json`) | ″ | (same run) |
| Per-arm optimizer convergence traces | E7 | ″ | `e7_trace_shared_fixed.csv`, `e7_trace_shared_refined.csv`, `e7_trace_percamera_fixed.csv`, `e7_trace_percamera_refined.csv` | ″ | (same run) |
| E7's four per-arm direct-call provenance records | E7 | ″ | `e7_benchmark_shared_fixed.json`, `e7_benchmark_shared_refined.json`, `e7_benchmark_percamera_fixed.json`, `e7_benchmark_percamera_refined.json` | — (provenance only) | (same run) |
| Supplement solver constants: bounds, `f_scale`, penalty, Newton tolerance (tier 1) | E3 | `python -m experiments.e3_derived_quantities` | `code_constants.csv` | table + CI assertion (declared in `tests/unit/test_experiments_e3_constants.py`, rendered here) | ~10 s (measured, 19.2-12) |
| Supplement "converges … in N steps" (tier 2) | E3 | ″ | `newton_iterations.csv` | prose value | (same run) |
| Supplement `tab:cpr` (all six rows, both interface modes) | E3 | ″ | `cpr_grouping.csv` | `cpr_grouping.tex` (E3's own LaTeX fragment IS its figure generator — no separate module) | (same run) |
| Supplement `\CPRParamsAside`/`\CPRReductionAside` (D-22's two derived prose asides) | E3 | ″ | `cpr_derived_values.tex` | ″ (the fragment itself is the rendered output) | (same run) |
| E3's environment-only provenance sidecar (tiers 1-2 never run a calibration, so there is no `benchmark.json` to reuse) | E3 | ″ | `e3_provenance.json` | — (provenance only) | (same run) |
| **NEW** main-text runtime table + supplement full cameras-x-frames grid | E4 | `python -m experiments.e4_benchmark_grid` | `benchmark_grid.csv`, `benchmark_grid.tex` | new figure module (Phase 19.2) | ~3.15 h summed per-cell wall-clock across the nine re-measured cells (~3.5 h including one killed-and-resumed launch; measured, 19.2-21-SUMMARY.md — re-run on the D-29 grid geometry after fixing two library defects, superseding the earlier ~27 min figure from a since-discarded grid) |
| E4's nine per-cell direct-call provenance records | E4 | ″ | `experiments/results/e4_cells/cameras_<n>_frames_<m>/benchmark.json` (nine files) | — (provenance only) | (same run) |
| **NEW** R2 sensitivity panel (index-error band) | E5 | `python -m experiments.e5_index_sensitivity` | `index_sensitivity.csv` | `DissertationFigures/src/dissertationfigures/figures/aquacal/` — a downstream handoff (X5, a different repository; no AquaCal phase produces this module) | ~21.1 min (1264 s, measured, 19.2-23-SUMMARY.md — re-run to add `e5_provenance.json`; superseded the earlier ~22.5 min figure) |
| E5's environment-only provenance sidecar (E5 has no per-row `benchmark.json`; this is the four-field record — seed, version, git SHA, environment — covering `index_sensitivity.csv`) | E5 | ″ | `e5_provenance.json` | — (provenance only) | (same run) |
| **NEW** R1.4 generalization table (index/layout/scale axes) | E6 | `python -m experiments.e6_generalization_sweep` | `generalization_sweep.csv` | `DissertationFigures/src/dissertationfigures/figures/aquacal/` — a downstream handoff (X5, a different repository; no AquaCal phase produces this module) | ~107 min (measured, 19.2-22-SUMMARY.md — a 3.2x increase over the earlier ~33.5 min figure, expected: the D-29 geometry puts the board at realistic distance with more observations per frame) |
| E6's environment-only provenance sidecar (the record covering `generalization_sweep.csv` itself) | E6 | ″ | `e6_provenance.json` | — (provenance only) | (same run) |
| E6's twelve per-configuration checkpoints — since plan 19.2-16 (WR-03) each one also carries `schema_version`, a four-field `environment` block, and `seed`, so these are provenance records that double as resumability checkpoints, not checkpoints alone | E6 | ″ | `experiments/results/e6_configs/*.json` | — (provenance + checkpoint) | (same run) |

> ### ⚠ Three `generalization_sweep.csv` rows did not converge — read before citing E6
>
> Since plan 19.2-27, E6 records `optimality_stage3_interface_optimization` and
> `optimality_stage3_intrinsic_pass` per configuration. On the first run carrying them
> (`19.2-28-SUMMARY.md`), **three of fourteen rows came back 3–4 orders of magnitude above the other
> eleven — and all three are published under `status="ok"` with a plausible reprojection RMS**:
> `index=1.42` (optimality 51.9), `scale=half_scale` (27.3 / 140.3), and `layout=ring` (4.20 on the
> intrinsic pass), against 0.0016–0.117 for the rest.
>
> **Accuracy appears unaffected** — reconstruction RMSE is indistinguishable between the flagged and
> healthy groups, and the worst reconstruction in the table belongs to a *healthy* configuration.
> The diagnosed cause is that board corners protrude through the water surface (61/8800 = 0.69% of
> corners), so those observations leave the refractive model's domain and are continued with a
> pinhole extension whose derivative discontinuity inflates a max-norm gradient.
>
> **Consequences for anyone using this table.** Do not quote those three rows as converged results
> without stating their optimality — see **MF-07** in `.planning/MANUSCRIPT-FINDINGS.md`, where the
> decision is recorded as OPEN. And never quote optimality to more than one significant figure: it
> varies ~2x between runs of identical code, so it supports an order-of-magnitude reading and
> nothing finer. Phase 19.3 owns the fix and will re-run E1/E4/E5/E6/E7 on corrected geometry.

`e4_benchmark_grid.py` is now a **direct-call synthetic benchmark grid** (D-03/D-26): it
builds `generate_camera_array` + `generate_board_trajectory` scenes and calibrates them via
the same direct-call path E1/E7 use, rather than subsampling a real 13-camera YAML through
the pipeline's config-driven entry point. A real 13-camera rig run already takes 48-87
minutes (`CLAUDE.md`) and cannot reach 16 cameras (unreachable from a 13-camera rig), so a
real cameras-x-frames sweep was out of scope for this phase's deadline. The nine-cell grid
was re-measured in Phase 19.2 wave 6 on the D-29 grid geometry, after fixing two library
defects (a flat NaN clamp with a zero-derivative absorbing region, and an unvalidated
`cv2.solvePnP` success flag) that had left four of the first attempt's six completed cells
not converged; all nine cells now converge (`status=ok`, first-order optimality between
9.1e-4 and 3.5e-2 on every cell — see `19.2-21-SUMMARY.md`) and the CSV is now committed,
alongside E2's real-rig row folded in as a tenth, separately-labeled point.

Two columns exist specifically so a reader cannot compare the nine synthetic rows against
E2's real-rig row as if they measured the same thing: `timing_scope` is `optimization_only`
for the nine synthetic cells (Stage 3 wall-clock only) and `end_to_end` for the real-rig row
(includes detection loading, auxiliary registration, and validation); `record_source` is
`assembled` (built from a per-cell `benchmark.json` by this script) for the synthetic cells
and `pipeline` (written directly by `run_calibration_from_config`) for the real-rig row.
`benchmark_grid.tex` renders the real-rig row in its own labeled block, never as a tenth
point on the nine-cell scaling curve.

`python -m experiments.e4_benchmark_grid --check` re-aggregates the nine per-cell
`benchmark.json` files already committed under `e4_cells/` and compares the result against
the committed `benchmark_grid.csv` — it never re-runs a cell (a full re-run is now ~3.15 h,
summed across the nine re-measured cells) and is not evidence the nine calibrations
themselves reproduce, only that the aggregation and the committed CSV agree with the on-disk
per-cell records. Because `_run_check` never re-runs a cell, its freshly-built comparison
frame always reports `exit_code=None` for every cell, while the committed CSV carries the
real per-run exit codes (`0`); `--check` against this committed CSV therefore always exits 1,
with every mismatch confined to the `exit_code` column — this is a structural property of
the check's re-aggregation design, not a data defect, confirmed again on the re-measured
grid (19.2-21-SUMMARY.md).

### DATA-01b — three E2 artifacts live in the Zenodo archive, not in this repo

`calibration.json`, `reprojection_residuals.csv` and `reconstruction_errors.csv` were removed
from version control once the Zenodo `real-rig` archive was published, so that the repo-wide
1000 KB `check-added-large-files` guard could be restored with no exclusion. They ship inside
the archive under `reference_outputs/`.

| Artifact | Where to get it now |
|---|---|
| `reconstruction_errors.csv` | Archive `reference_outputs/` — **byte-identical** to the removed copy |
| `reprojection_residuals.csv` | Archive `reference_outputs/` — **byte-identical** to the removed copy |
| `calibration.json` | Archive `reference_outputs/` — **equivalent, not identical** (see below) |

```python
from aquacal.datasets import load_example
ref = load_example("real-rig").cache_path / "reference_outputs"
```

Or regenerate all three locally, which takes about 50 minutes:

```bash
python -m experiments.e2_real_rig --out experiments/results --force
```

**The `calibration.json` caveat.** The archive ships the **2026-08-10 image-source** run, while
the file removed from this repo was the **2026-07-31 video-source** run. Both are library
`1.8.0` and they agree to ~1.5e-8 on `water_z` — the floating-point floor, and the same
equivalence MF-19's control established when it held the library fixed and varied only the frame
source. For any purpose short of byte-comparison the archive copy is the same artifact. If you
need those exact bytes, take them from git history at `25655f7`, not from the archive.

`reconstruction_bootstrap.py` resolves its input automatically: an explicit
`--reconstruction-errors` path, else a local `experiments/results/` copy, else the published
archive. It never downloads at import time.

### Which committed artifacts are pre- and which are post-D-27

D-27 (plan 19.2-18) changed `generate_board_trajectory`'s sampling volume to center on the
camera array's centroid rather than the origin — a deliberate, **non-inert** change for the
grid family (E4, E6), which calls `generate_board_trajectory` directly through
`build_grid_scenario`. It never fires for the "realistic" family (E1, E2, E3, E5, E7), which
builds its scenes through `generate_real_rig_trajectory` or the real video frameset instead —
a structurally different code path that D-27 never touches.

- **Structurally unaffected, and proven so mechanically, not asserted:** E1, E2, E3, E5, E7.
  Plan 19.2-18 backs this with three independent proofs — two frozen-anchor exact-equality
  tests (`generate_real_rig_trajectory` and `create_scenario("realistic")` bit-identical
  pre/post D-27), a source-scanning grep-gate (no realistic-path caller — `create_scenario`,
  `e3_derived_quantities.py`, `e5_index_sensitivity.py` — ever passes an explicit `center`
  override), and four passing `--check` reproductions (E1, E3, E5, E7) against the still-
  committed baselines, all recorded in `19.2-18-SUMMARY.md` § Task 3. Wave 5 (plan 19.2-23)
  regenerated E3's and E5's artifacts for an unrelated reason (adding provenance sidecars) and
  found them unchanged in substance — E3's `code_constants.csv` passes with exactly the one
  declared, D-27-unrelated exemption, and `cpr_grouping.csv` is byte-for-byte identical — which
  is a second, independent confirmation that D-27 left the realistic family alone. E2 never
  runs a synthetic scenario generator at all. E1's and E7's committed CSVs did move in this
  phase, but for a documented, unrelated reason (the degenerate-PnP guard, `7e0cb90`) — see
  `MANUSCRIPT-FINDINGS.md` MF-06 and MF-05, which regenerate them across multiple seeds rather
  than `--check` them, precisely because that non-D-27 change is not inert and a stale-baseline
  `--check` would fail on a non-defect. **Correction to an earlier draft of this section:** the
  two `e1_refractive_comparison --check` / `e7_interface_ablation --check` runs originally
  planned as final-tree confirmation (19.2-24-PLAN.md's original Task 2) were withdrawn under
  D-35 in favor of that full regeneration, which the plan's own reasoning calls the stronger
  evidence — they are not part of the citable record and are not cited here.
- **Regenerated after D-27, on the redesigned geometry:** E4 (`19.2-21-SUMMARY.md`, the
  nine-cell grid re-run) and E6 (`19.2-22-SUMMARY.md`, the three-axis sweep re-run). Both
  committed artifacts postdate D-27 by construction — there is no pre-D-27 baseline for either
  to be compared against, because D-27 is bundled with D-28/D-29's geometry rescale in the same
  commits (`d5d9dde`, `a2b244d`) that this wave's grid and sweep runs are built on.

### `cpr_grouping.csv` is the sole origin of `tab:cpr`

**`cpr_grouping.csv` supplies all six `tab:cpr` rows, in both interface modes** — every row
is a tilt-enabled (`normal_fixed=False`) configuration, matching
`CalibrationConfig.interface_normal_fixed`'s default and E2's real-rig run. Exactly one row
(the shared-interface 13-camera/200-frame tilt+intrinsics row) is copied verbatim from E2's
committed `benchmark.json`; the rest are computed by `experiments.e3_derived_quantities`
directly against the library's own `build_jacobian_sparsity`/`build_structural_column_groups`.
An earlier design split `tab:cpr` across this file and E4's own per-cell grid CSV; that split
was withdrawn (review H1) because E4's cells run at a real, sparser scene (some frames have
zero observing cameras and are dropped, changing the parameter count) rather than the
idealized full-visibility fixture `tab:cpr`'s numbers describe — four of the six rows would
have come from the wrong solver configuration. **`benchmark_grid.csv` also carries
`n_params`/`n_groups`/`fd_reduction` columns, but they describe E4's own runs and feed no
published table.** The `normal_fixed`/`shared_interface` columns present in both files are
what let a reader tell a `cpr_grouping.csv` row from a `benchmark_grid.csv` cell apart.

### Every cell in E4 and E6 runs tilt-enabled

E4's nine cells and E6's sweep both run at `normal_fixed=False`
(`experiments.e4_benchmark_grid.GRID_NORMAL_FIXED`, imported by E6 rather than restated),
matching `CalibrationConfig.interface_normal_fixed`'s default and E2's real-rig run. This is
why every synthetic-grid CSV in this directory carries a `normal_fixed` column — a reader
comparing a row here against a differently-configured run elsewhere can check it rather than
assume it.

### The seed carve-out

E1's and E7's Phase-19.1 records (`e1_benchmark_refractive.json`,
`e1_benchmark_nonrefractive.json`, and E7's four `e7_benchmark_*.json` arms) predate
`solver_config["seed"]`, which plan 19.2-02 added to the direct-call write path after these
six records were already committed. They are not re-run to backfill it — re-running them
costs roughly 90 minutes for records the manuscript already cites and produces no new
information. The gap is named explicitly, not inferred: `tests/unit/test_experiments_
provenance.py`'s `SEEDLESS_LEGACY_RECORDS` set exempts exactly these six files from the
otherwise-universal "every committed record carries a seed" check, and a companion test
fails the moment any of the six is regenerated with a seed (at which point the exemption
must be removed by hand). Every record and CSV committed by Phase 19.2 itself — the nine E4
cells, `benchmark_grid.csv`, `index_sensitivity.csv`, `generalization_sweep.csv`, and E2's
refreshed `benchmark.json` — carries a seed.

### The four scripts with no row in the table above

The provenance table has one row per *paper artifact*, so four of the eleven runnable scripts
in this directory do not appear in it. That is not a licence to treat them as dead code — three
of them carry unit tests. They are listed here so the directory's own map points at everything
in it.

| Script | What it is | Tests | Paper artifact |
|---|---|---|---|
| `e7_focal_standoff_analysis.py` | Pure re-analysis of the committed `interface_ablation_band.csv` for the focal-drift/standoff pairing (COV-08, E7 half) that WP6 planned and MF-05 never reported. Never regenerates its input. | `tests/unit/test_e7_focal_standoff.py` | None committed — analysis output only |
| `reconstruction_bootstrap.py` | Frame-clustered bootstrap CI over `reconstruction_errors.csv`, resolved from a local copy or the published archive (COV-08, bootstrap half, D-19.5-05). The resampling unit is the frame, not the row. Performs no calibration. | `tests/unit/test_reconstruction_bootstrap.py` | None committed — CI band only |
| `check_rerun_gates.py` | Machine-checkable post-run gates (D-19.3-18) over an output directory's existing artifacts. Reports PASS/FAIL/N/A per gate per experiment and exits non-zero on any FAIL. Runs nothing and regenerates nothing. | `tests/unit/test_rerun_gates.py` | None — a verification tool, not a producer |
| `fd_jacobian_accuracy.py` | **One-off diagnostic, no test coverage and no paper artifact.** Compares the shipped 2-point finite-difference Jacobian against a Richardson reference (E-COV-02 / R1.2) without deriving the analytic Jacobian. Referenced only from `.planning/phases/.../19.5-02-PLAN.md`. Do not read it as an E-series experiment: nothing in CI or the manuscript depends on it. | — none — | None |

The first three inherit the same five-flag CLI contract described in §1; so does
`fd_jacobian_accuracy.py`.

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

**Both paths' reference numbers were produced under OpenCV 4.13.0** — name that version
before citing either. The real-rig numbers move with the OpenCV version, not just the
AquaCal version: `detection.py:64` constructs `cv2.aruco.CharucoDetector` directly, so the
corner set is entirely OpenCV's, and a single-variable control (2026-08-12, same machine,
cloned env differing *only* in OpenCV) reproduced this repo's committed numbers to <=4.7e-09
relative under 4.13.0 while 4.14.0 detected 450 fewer corners and moved `reconstruction.rmse`
by +7.8%. Nothing measured says which version detected the *right* set — neither is "more
correct" — so the environment is named rather than the numbers changed. Holding OpenCV fixed,
the aquacal 1.8.0 -> 2.0.1 gap and the Windows -> Linux platform change are both inert on
real data (MF-20). Every `benchmark.json` records `opencv_version` in its `environment` block.

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

**Precondition — a source checkout must carry a *current* editable install.** Run
`pip install -e . --no-deps` in the environment you are about to use, and re-run it after
**any** change to `pyproject.toml`'s `version`. `aquacal.__version__` and the
`environment.aquacal_version` field written into every record below both resolve through
`importlib.metadata.version("aquacal")` — i.e. *installed distribution metadata*, which an
editable install writes once and never refreshes. The `.pth` still resolves imports to the
working tree, so between a version bump and the next reinstall the code that runs is the new
tree while every artifact it produces is stamped with the old version. Nothing fails loudly;
you simply get a confident, plausible, wrong provenance record. `experiments/prelaunch_gate.sh`'s
`ENV_VERSION_MATCH` check asserts this before a queue launches, and `benchmark.json`'s
`environment.aquacal_version_declared` records the declared version beside the installed one so
an escaped case is visible after the fact.

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

# E3 — derived quantities and code constants (~10 s)
python -m experiments.e3_derived_quantities --check   # compare fresh vs. committed
python -m experiments.e3_derived_quantities --force   # regenerate the committed CSVs/fragments

# E4 — cameras x frames synthetic benchmark grid (~27 min, nine cells)
python -m experiments.e4_benchmark_grid --check   # re-aggregate committed per-cell records
python -m experiments.e4_benchmark_grid --force   # re-run all nine cells

# E5 — refractive-index sensitivity band on real-rig geometry (~22.5 min)
python -m experiments.e5_index_sensitivity --check
python -m experiments.e5_index_sensitivity --force

# E6 — index/layout/scale generalization sweep (~33.5 min)
python -m experiments.e6_generalization_sweep --check
python -m experiments.e6_generalization_sweep --force
```

Every committed result has a provenance record next to it carrying its seed, AquaCal
version, git SHA, and the Python/NumPy/SciPy/OS environment it ran under. This is now true
without exception — as of wave 5 (plans 19.2-16/19), it no longer narrows for E5 or E6.
There are three shapes of record, not one:

- A `benchmark.json`-shaped record (`schema_version: 1`, a `stages` block) — either the
  genuine pipeline-written record (E2, via `run_calibration_from_config`) or a direct-call
  record assembled from the same pure `aquacal.io.assemble_benchmark_record` (E1, E7, E4's
  nine cells — all call `calibrate_synthetic` directly and never touch the pipeline's own
  config-driven entry point, so there is no pipeline `benchmark.json` for them to reuse).
- E3's tiers 1–2 never run a calibration at all, so they use a separate minimal sidecar
  (`e3_provenance.json`) carrying the same seed/version/git-SHA/environment fields without a
  `stages` block.
- `index_sensitivity.csv` and `generalization_sweep.csv` are backed by `e5_provenance.json`
  and `e6_provenance.json` respectively — the same minimal, `stages`-free shape as E3's
  sidecar, added by plans 19.2-16 and 19.2-19. Before those plans, these two CSVs carried
  only a `seed` column and no version/SHA/environment fields; that gap is what this
  paragraph used to describe, and it is closed. E6's twelve `e6_configs/*.json` checkpoints
  carry the same fields individually, per-configuration, in addition to `e6_provenance.json`
  covering the CSV as a whole.

`tests/unit/test_experiments_provenance.py`'s `CSV_TO_RECORD` names the covering record for
every committed CSV. No experiment invents a fourth sidecar shape beyond the three above.

Every committed result's provenance is asserted mechanically, not by inspection, in
`tests/unit/test_experiments_provenance.py` — the six Phase-19.1 records that predate the
seed key are named there explicitly (see "The seed carve-out" above), and a CSV committed
without an entry in that test's `CSV_TO_RECORD` mapping fails CI.

## 8. Pre-fix artifact archive

`experiments/archive/` preserves committed artifacts from before a non-inert fix, so a
reader diffing the manuscript's numbers has one artifact to diff against instead of
reconstructing "before" from git history. See `experiments/archive/README.md` for the
index and the convention (partial copy plus `git show <sha>:<path>` pointers for anything
that trips `check-added-large-files` or `detect-secrets`).
