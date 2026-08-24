# The v2.1 full-suite re-run: hand-verification sheet

**Read this before judging a finished run.** It is written *before* the run, on purpose, because
the run is what it will be checked against — a sheet assembled afterwards from what the run
happened to produce records the run, not the expectation.

§7 below is delimited by a pair of generated-region HTML comment markers, and everything between
them is rendered from `experiments/suite_expectations.json` by
`experiments/render_expectation_sheet.py`; `tests/unit/test_expectations.py -k sheet` fails when
the two drift apart. Everything outside those markers — §§1–6 — is hand-written, and the renderer
never touches it. Regenerate with:

```bash
python -m experiments.render_expectation_sheet --write
python -m experiments.render_expectation_sheet --check   # exits 1 if stale
```

## 1. What this sheet is for

DRIVER-03 replaces bit-identity reproduction with written expectations **wherever a schema moved**.
Four did, in Phases 23–25, and a fifth changed its verdict strings; a `--check` against the
pre-re-run baselines therefore pre-declares a header mismatch for those artifacts and would be
red for a reason that is not a defect.

So: **hand-verify this run against this sheet** (D-13). Phase 29 re-baselines the committed
artifacts against the frozen output and restores automated checking. Until then the automated
verdicts you *can* trust are the completeness gate (`experiments/_expectations.py`, which is the
only gate that FAILs over an empty tree) and the numeric gates in
`experiments/check_rerun_gates.py`.

## 2. The `--check` contract across the deliberate re-base

The mechanism is `compare_experiment_csv(..., exclude_columns=())` in `experiments/_io.py`
(definition at `:332`, contract documented at `:365-382`). That docstring already names Phase 26 /
DRIVER-03 and warns that it and this section must not diverge — if you change one, change both.

**The key property, stated once so it is not re-derived from memory:** `exclude_columns` affects
the **CELL-level comparison ONLY**. The full-header comparison is never affected, so **a genuine
schema change still fails loudly** even when the differing column is named in the exclusion list.
The exclusion list is not a way to make `--check` quiet.

**The sole in-repo exclusion list** is `CHECK_EXCLUDED_COLUMNS = ("exit_code", "status_reason")`
at `experiments/e4_benchmark_grid.py:215`. Both columns are artifacts of the *checking path
itself* — `_run_check` re-aggregates the committed per-cell `benchmark.json` files and never runs
a subprocess, so it can only report `exit_code=None` while the committed CSV carries real exit
codes. The list is **named, not heuristic** (D-07): the next such column must be a deliberate
decision rather than a silently inherited exemption. Phase 26 adds no new exclusion list.

| Script | `_run_check`? | `compare_experiment_csv` call sites | Schema state at the re-base |
|---|---|---|---|
| `e1_refractive_comparison.py` | yes | 1 | `SPATIAL_COLUMNS` moved 6 → 12. Header mismatch pre-declared. |
| `e2_real_rig.py` | yes | 3, via `compare_experiment_csv_if_present` | Two of the three artifacts have no committed baseline at all — see §3. |
| `e3_derived_quantities.py` | yes | 3 | Unmoved. **One of only two `--check` paths that is still a real reproduction signal**, which is why it runs before its own `--force` and reads `--baseline-dir`. |
| `e4_benchmark_grid.py` | yes | 1 | Structurally **always red** on `exit_code` and `status_reason`; all 33 metric columns reproduce to 1e-6. |
| `e5_index_sensitivity.py` | yes | 1 | `E5_COLUMNS` moved 17 → 23. Header mismatch pre-declared. |
| `e6_generalization_sweep.py` | yes | 1 | `E6_COLUMNS` moved 31 → 33. Header mismatch pre-declared. |
| `e7_interface_ablation.py` | yes | 1 | `ABLATION_COLUMNS` moved 17 → 23, and `e7_focal_standoff.csv`'s verdict strings changed. Header mismatch pre-declared. |
| `fd_jacobian_accuracy.py` | yes | 1 | No committed baseline before this run — it was never invoked by any driver. |

A pre-declared header mismatch is **expected output, not a finding**. Report it as such; do not
"fix" it by regenerating a baseline mid-run.

## 3. The E2 honesty note (SP-5)

"`--check` survives on E3 and E2 only" is optimistic for E2. E2 compares three artifacts, and only
**`camera_parameters.csv`** has a committed baseline. `reprojection_residuals.csv` and
`reconstruction_errors.csv` are gitignored by deliberate DATA-01b policy (`.gitignore:238-239`)
and ship only in the Zenodo archive, so plan 26-06 made E2's `--check` report **N/A** for them
rather than a pass. An all-N/A `--check` compared nothing and must never be read as a green
verdict.

**The better-anchored E2 control** is `check_e2_band`'s numeric comparison of
`real_rig_metrics.json` at `_E2_METRICS_RTOL = 1e-6` (`experiments/check_rerun_gates.py:1378`).
Prefer it. It also depends on the local tree being warm — the 4.35 GB frameset and a 48–87 minute
calibration — which is why it is a control and not a smoke check.

## 4. Existence and row count are not correctness

**A gauge-corrected column populated with uncorrected values passes every completeness check.** The
gate asserts that a file exists and has the right number of rows. It cannot see that
`z_position_error_mm_gauge_corrected_mean` was written without the correction applied, or that
`water_z_error_mm_signed` lost its sign, or that a column is uniformly zero.

That is this sheet's job, not the gate's. The generated region below marks **shape-only columns**
explicitly: those are the cells where existence and count prove nothing, and where a human has to
read the values. In practice they are E6's gauge-corrected and signed error columns, E3's Newton
iteration counts, and E4's two `CHECK_EXCLUDED_COLUMNS`.

Concretely, for each shape-only column ask: does the sign distribution look like the physics, or
has the magnitude survived while the sign was averaged away? An 18.9 mm error that was 80% gauge
is this project's canonical example — chase the sign before believing a magnitude.

## 5. Two reading rules for the hand-verifier

**Rule 1 — never quote `optimality` to more than one significant figure.** It varies ~2× between
runs of identical code (`experiments/README.md`, the E6 convergence callout). It supports an
order-of-magnitude reading and nothing finer. A row whose `optimality` is 3–4 orders of magnitude
above its neighbours is a real signal; a row that moved from 0.0016 to 0.0031 is not.

**Rule 2 — the degeneracy breakdown's two marginals are never additive together.** The 32
`DISCARD_KEYS` in `src/aquacal/calibration/_observability.py` split
`degenerate_observations_at_solution` on **two independent axes**: CAUSE (why the refractive
projection failed — `above_interface`, `behind_camera`, `interface_below_camera`) and FATE (what
the residual then did — `extended` keeps a gradient, `penalized` is a flat constant with none).
Each axis decomposes the same total **exactly**: the total equals the sum of the nine `cause_*`
keys **and, independently,** the sum of the six `fate_*` keys. Summing a cause column and a fate
column doubles the true count. If a breakdown's parts do not each sum to the total, that is a
defect in the run, not an interesting result.

## 6. What this sheet CANNOT certify

Stated so nobody over-reads it:

- **That the `full`-profile row counts are CORRECT rather than merely self-consistent.** Every row
  count below is derived from the manifest, and the manifest's derivations are cross-checked
  against the code's own shape constants — but only **Phase 28 actually produces** those rows. If
  a derivation is wrong, this sheet will confidently expect the wrong number and the gate will
  confidently assert it.
- **That E2's ~1e-8 control reproduces.** It needs the 4.35 GB local frameset and a 48–87 minute
  calibration. Nothing in Phase 26 ran one.
- **That the concurrency model does not OOM at 4–5 wide.** The 4-wide pool is a measured
  recommendation from a probe taken on E1 — the cheapest and smallest solve in the suite — not a
  measurement of `e6_band` and `e4` sharing a 15.7 GiB box. `SUITE_SERIAL=1` is the escape hatch,
  and a suspected memory interaction is a reason to use it.
- **That any artifact's numbers are publishable.** Provenance, gates and row counts establish that
  a run happened and produced what it should. Which numbers may be cited, and with what error
  bars, is `.planning/MANUSCRIPT-FINDINGS.md`'s question.

## 7. The manifest, rendered

<!-- BEGIN GENERATED -->
*This region is generated from `experiments/suite_expectations.json`.*
*Do not edit it by hand — run `python -m experiments.render_expectation_sheet --write`.*

### Shape of the run

- **20 stages**, **62 declared artifacts** (62 expected under the `full` profile, of which 20 pin a row count).
- **2 conditional** artifact(s): absent only when a MACHINE-EVALUATED predicate shows the condition did not hold. Each one's predicate is summarised in its `Conditional` cell below; an absence the gate cannot adjudicate is reported N/A, never PASS, and an artifact found outside its declared directory is a FAIL (D-29.1-18).
- **3 immutable** artifact(s): the re-run must not change them.
- **5 artifact(s) carry shape-only columns** — present and correctly counted proves nothing about their values. Those are the cells a hand-verifier actually has to read.
- Serial wall clock **28.3-31.3 h**; with the concurrency pool **15-17 h**. Dominant stage `e6_band` at 8.9 h.

### Stages, in execution order

| # | Stage | Concurrency | Est. h | Profiles | Output directory |
|---|---|---|---|---|---|
| 1 | `preflight` | concurrent | 0.02 | smoke, full | `experiments/results` |
| 2 | `prelaunch_probe` | concurrent | 0.01 | smoke, full | `experiments/results` |
| 3 | `e3` | concurrent | 0.005 | smoke, full | `experiments/results` |
| 4 | `fd_jacobian` | concurrent | 0.05 | smoke, full | `experiments/results` |
| 5 | `e1` | concurrent | 0.09 | smoke, full | `experiments/results` |
| 6 | `e7` | concurrent | 0.09 | smoke, full | `experiments/results` |
| 7 | `e7_focal_standoff` | concurrent | 0.02 | full | `experiments/results` |
| 8 | `reconstruction_bootstrap` | concurrent | 0.06 | full | `experiments/results` |
| 9 | `e5` | concurrent | 0.76 | smoke, full | `experiments/results` |
| 10 | `e4_repeat` | serial_alone | 0.99 | full | `experiments/results_e4_repeat` |
| 11 | `e2_production` | concurrent | 0.8-1.45 | full | `experiments/results` |
| 12 | `e2_timing` | serial_alone | 0.8-1.45 | full | `experiments/results_e2_timing` |
| 13 | `e2_memory` | serial_alone | 0.8-1.45 | full | `experiments/results_e2_memory` |
| 14 | `e7_band` | concurrent | 1-2 | smoke, full | `experiments/results` |
| 15 | `e5_band` | concurrent | 2.34 | smoke, full | `experiments/results` |
| 16 | `e2_band` | concurrent | 2.42 | full | `experiments/results_e2_band` |
| 17 | `e6_repeat1` | concurrent | 2.78 | smoke, full | `experiments/results` |
| 18 | `e1_band` | concurrent | 2.8 | smoke, full | `experiments/results` |
| 19 | `e4` | serial_alone | 3.57 | full | `experiments/results` |
| 20 | `e6_band` | concurrent | 8.9 | smoke, full | `experiments/results` |

### Every expected artifact

`Rows (full)` is the exact data-row count the completeness gate asserts under the `full` profile; `not pinned` means the artifact is a JSON sidecar or otherwise has no table shape to assert. `Shape-only columns` are columns whose PRESENCE is checked and whose VALUES are not — read them by hand.

| Artifact | Stage | Directory | Rows (`full`) | Conditional | Immutable | Shape-only columns |
|---|---|---|---|---|---|---|
| `run_manifest.json` | `preflight` | `experiments/results` | not pinned | no | no | — |
| `environment_lock.txt` | `preflight` | `experiments/results` | not pinned | no | no | — |
| `exp1_parameter_errors.csv` | `e1` | `experiments/results` | 24 | no | yes | — |
| `exp2_depth_generalization.csv` | `e1` | `experiments/results` | 16 | no | yes | — |
| `exp3_xy_vs_z_anisotropy.csv` | `e1` | `experiments/results` | 16 | no | yes | — |
| `exp2_spatial_errors.csv` | `e1` | `experiments/results` | not pinned | no | no | — |
| `e1_benchmark_refractive.json` | `e1` | `experiments/results` | not pinned | no | no | — |
| `e1_benchmark_nonrefractive.json` | `e1` | `experiments/results` | not pinned | no | no | — |
| `e1_degeneracy_breakdown.json` | `e1` | `experiments/results` | not pinned | no | no | — |
| `exp1_band.csv` | `e1_band` | `experiments/results` | 256 | no | no | — |
| `exp1_parameter_band.csv` | `e1_band` | `experiments/results` | 384 | no | no | — |
| `e1_seed_band_provenance.json` | `e1_band` | `experiments/results` | not pinned | no | no | — |
| `code_constants.csv` | `e3` | `experiments/results` | 9 | no | no | — |
| `newton_iterations.csv` | `e3` | `experiments/results` | 26 | no | no | `mean_iterations`, `max_iterations` |
| `cpr_grouping.csv` | `e3` | `experiments/results` | 12 | no | no | — |
| `structural_scaling.csv` | `e3` | `experiments/results` | 84 | no | no | — |
| `e3_provenance.json` | `e3` | `experiments/results` | not pinned | no | no | — |
| `cpr_grouping.tex` | `e3` | `experiments/results` | not pinned | no | no | — |
| `cpr_derived_values.tex` | `e3` | `experiments/results` | not pinned | no | no | — |
| `index_sensitivity.csv` | `e5` | `experiments/results` | 11 | no | no | — |
| `e5_provenance.json` | `e5` | `experiments/results` | not pinned | no | no | — |
| `e5_degeneracy_breakdown.json` | `e5` | `experiments/results` | not pinned | no | no | — |
| `index_sensitivity_seed_band.csv` | `e5_band` | `experiments/results` | 66 | no | no | — |
| `e5_seed_band_provenance.json` | `e5_band` | `experiments/results` | not pinned | no | no | — |
| `e5_seed_band_degeneracy_breakdown.json` | `e5_band` | `experiments/results` | not pinned | no | no | — |
| `generalization_sweep.csv` | `e6_repeat1` | `experiments/results` | 14 | no | no | `z_position_error_mm_gauge_corrected_mean`, `water_z_error_mm_signed_mean` |
| `generalization_sweep_per_camera.csv` | `e6_repeat1` | `experiments/results` | not pinned | no | no | `z_position_error_mm_gauge_corrected`, `water_z_error_mm_signed`, `h_c_error_mm_signed` |
| `e6_provenance.json` | `e6_repeat1` | `experiments/results` | not pinned | no | no | — |
| `generalization_sweep_band.csv` | `e6_band` | `experiments/results` | 84 | no | no | `z_position_error_mm_gauge_corrected_mean`, `water_z_error_mm_signed_mean` |
| `generalization_sweep_per_camera_band.csv` | `e6_band` | `experiments/results` | not pinned | no | no | — |
| `e6_seed_band_provenance.json` | `e6_band` | `experiments/results` | not pinned | no | no | — |
| `interface_ablation.csv` | `e7` | `experiments/results` | 48 | no | no | — |
| `interface_ablation_conditioning.json` | `e7` | `experiments/results` | not pinned | no | no | — |
| `e7_benchmark_shared_fixed.json` | `e7` | `experiments/results` | not pinned | no | no | — |
| `e7_benchmark_shared_refined.json` | `e7` | `experiments/results` | not pinned | no | no | — |
| `e7_benchmark_percamera_fixed.json` | `e7` | `experiments/results` | not pinned | no | no | — |
| `e7_benchmark_percamera_refined.json` | `e7` | `experiments/results` | not pinned | no | no | — |
| `e7_trace_shared_fixed.csv` | `e7` | `experiments/results` | not pinned | no | no | — |
| `e7_trace_shared_refined.csv` | `e7` | `experiments/results` | not pinned | no | no | — |
| `e7_trace_percamera_fixed.csv` | `e7` | `experiments/results` | not pinned | no | no | — |
| `e7_trace_percamera_refined.csv` | `e7` | `experiments/results` | not pinned | no | no | — |
| `e7_degeneracy_breakdown.json` | `e7` | `experiments/results` | not pinned | no | no | — |
| `interface_ablation_band.csv` | `e7_band` | `experiments/results` | 480 | no | no | — |
| `e7_seed_band_provenance.json` | `e7_band` | `experiments/results` | not pinned | no | no | — |
| `e7_seed_band_degeneracy_breakdown.json` | `e7_band` | `experiments/results` | not pinned | no | no | — |
| `e7_focal_standoff.csv` | `e7_focal_standoff` | `experiments/results` | 4 | no | no | — |
| `benchmark_grid.csv` | `e4` | `experiments/results` | 10 | no | no | `exit_code`, `status_reason` |
| `benchmark_grid.tex` | `e4` | `experiments/results` | not pinned | no | no | — |
| `benchmark_grid_repeat.csv` | `e4_repeat` | `experiments/results` | 6 | no | no | — |
| `benchmark.json` | `e2_production` | `experiments/results` | not pinned | no | no | — |
| `camera_parameters.csv` | `e2_production` | `experiments/results` | 13 | no | no | — |
| `real_rig_metrics.json` | `e2_production` | `experiments/results` | not pinned | no | no | — |
| `reconstruction_errors.csv` | `e2_production` | `experiments/results` | not pinned | no | no | — |
| `reprojection_residuals.csv` | `e2_production` | `experiments/results` | not pinned | no | no | — |
| `degenerate_observations.csv` | `e2_production` | `experiments/results_e2_invocations/e2_classification` | not pinned | yes — absent only if NOT: E2's calibration flagged at least one observation as degenerate at its solution | no | — |
| `all_observation_depths.csv` | `e2_production` | `experiments/results_e2_invocations/e2_classification` | not pinned | yes — absent only if NOT: E2's classification invocation was configured to log every observation's depth | no | — |
| `e2_band_scope.json` | `e2_band` | `experiments/results_e2_band` | not pinned | no | no | — |
| `benchmark.json` | `e2_timing` | `experiments/results_e2_timing` | not pinned | no | no | — |
| `benchmark.json` | `e2_memory` | `experiments/results_e2_memory` | not pinned | no | no | — |
| `reconstruction_bootstrap.json` | `reconstruction_bootstrap` | `experiments/results` | not pinned | no | no | — |
| `fd_jacobian_accuracy.csv` | `fd_jacobian` | `experiments/results` | 8 | no | no | — |
| `fd_jacobian_accuracy.json` | `fd_jacobian` | `experiments/results` | not pinned | no | no | — |

<!-- END GENERATED -->
