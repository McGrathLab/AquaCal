# Roadmap: AquaCal

## Milestones

- ✅ **v1.2 MVP** — Phases 1-6 (shipped 2026-02-15)
- ✅ **v1.4 QA & Polish** — Phases 7-12 (shipped 2026-02-19)
- ✅ **v1.6 Refinement API** — Phases 13-15 (shipped 2026-03-09)
- 🚧 **v1.9 Publication Prep** — Phases 16-22 (in progress)

**Interim releases v1.7–v1.8** shipped outside the GSD framework (debug sessions,
quick tasks) — no phases. See `.planning/MILESTONES.md`. v1.9 phase numbering
continues from 16.

## Phases

<details>
<summary>✅ v1.2 MVP (Phases 1-6) — SHIPPED 2026-02-15</summary>

- [x] Phase 1: Foundation and Cleanup (3/3 plans) — completed 2026-02-14
- [x] Phase 2: CI/CD Automation (3/3 plans) — completed 2026-02-14
- [x] Phase 3: Public Release (3/3 plans) — completed 2026-02-14
- [x] Phase 4: Example Data (3/3 plans) — completed 2026-02-14
- [x] Phase 5: Documentation Site (4/4 plans) — completed 2026-02-14
- [x] Phase 6: Interactive Tutorials (4/4 plans) — completed 2026-02-15

See `.planning/milestones/v1.2-ROADMAP.md` for full details.

</details>

<details>
<summary>✅ v1.4 QA & Polish (Phases 7-12) — SHIPPED 2026-02-19</summary>

- [x] Phase 7: Infrastructure Check (1/1 plans) — completed 2026-02-15
- [x] Phase 8: CLI QA Execution (1/1 plans) — completed 2026-02-15
- [x] Phase 9: Bug Triage (0/0 plans — no bugs found) — completed 2026-02-17
- [x] Phase 10: Documentation Audit (3/3 plans) — completed 2026-02-16
- [x] Phase 11: Documentation Visuals (2/2 plans) — completed 2026-02-17
- [x] Phase 12: Tutorial Verification (3/3 plans) — completed 2026-02-19

See `.planning/milestones/v1.4-ROADMAP.md` for full details.

</details>

<details>
<summary>✅ v1.6 Refinement API (Phases 13-15) — SHIPPED 2026-03-09</summary>

- [x] Phase 13: Core Refinement (2/2 plans) — completed 2026-02-28
- [x] Phase 14: Optimization Extensions (2/2 plans) — completed 2026-02-28
- [x] Phase 15: Validation and Result Contract (2/2 plans) — completed 2026-02-28

See `.planning/milestones/v1.6-ROADMAP.md` for full details.

</details>

### 🚧 v1.9 Publication Prep (Phases 16-22, In Progress)

**Milestone Goal:** Build all remaining code-side tooling the SoftwareX reviewer
responses depend on, so the revision experiments (due 2026-08-21) run against a
stable library rather than a moving target.

**Ordering note:** the experiment-blocking chain (Hooks → Per-Camera Interface) runs
first so WP5/WP6 experiments can start as early as possible against the deadline. Docs
reconciliation and benchmarking follow, independent of that chain except where DOCS-06
must settle the stage-key schema before benchmark.json locks it in.

- [x] **Phase 16: Experiment Observability Hooks** - Researchers can inspect and reproduce optimizer internals needed for WP5/WP6 without changing numeric behavior
 (completed 2026-07-23)
- [x] **Phase 17: Per-Camera Interface Ablation Mode** - A per-camera `water_z` ablation is available and trustworthy without disturbing the default shared-interface behavior
 (completed 2026-07-23)
- [x] **Phase 18: Documentation Corrections & Stage-Model Reconciliation** - Fix live doc errors and reconcile the three-stage model across code and docs before instrumentation locks in a schema
 (completed 2026-07-24)
- [x] **Phase 19: Benchmark Instrumentation** - Every calibration run produces a trustworthy, machine-readable performance record
 (completed 2026-07-24)
- [x] **Phase 19.5: Experiment Coverage and Uncertainty Bands** (INSERTED) - Every experiment the reviewer response leans on carries a measured uncertainty band or says plainly that it does not, and R1.2/R1.3 get their first experimental answer
  (Phases 19.1-19.4 are likewise inserted decimals; see Phase Details. 19.5 is the next phase.)
- [ ] **Phase 20: Refractive Index Helper** - Users can estimate `n_water` from environmental conditions and transfer it into their config by hand
- [ ] **Phase 21: New-Feature Documentation & Dataset Refresh** - Every capability this milestone added is documented, and the published dataset/tutorials reflect the current library
- [ ] **Phase 22: Release Cut** - The version referenced by the manuscript and Zenodo archive is the one whose behavior the published artifacts reflect

## Phase Details

### Phase 16: Experiment Observability Hooks
**Goal**: Researchers can inspect optimizer internals and reproduce results needed for the
WP5/WP6 experiments, with zero change to numerical behavior. This is the first half of the
milestone's longest pole and only true experiment blocker — sequenced first so the
experiments can start as early as possible against the 2026-08-21 deadline.
**Depends on**: Nothing (first phase of milestone)
**Requirements**: HOOK-01, HOOK-02, HOOK-03, HOOK-04, HOOK-05, HOOK-06
**Success Criteria** (what must be TRUE):
  1. Each stage's intermediate calibration (post-Stage-2, post-Stage-3, post-intrinsic-refinement)
     can be dumped to the output dir, extending the existing `calibration_initial.json` pattern.
  2. An opt-in per-iteration trace for the bundle-adjustment stages records iteration index,
     cost, step norm, optimality, and current interface parameters.
  3. Conditioning diagnostics are available at solution: the Jacobian's singular-value
     spectrum or condition number, plus the parameter correlation matrix (or at minimum the
     camera-height / interface-distance block) — giving the WP6 degeneracy argument a metric.
  4. Held-out evaluation is callable standalone, scoring a calibration against a set
     generated under different assumptions (e.g., different refractive index).
  5. The synthetic generator independently controls refractive index, layout, and
     tank-scale/working-distance, and returns ground-truth board poses and true interface
     height so sweeps can compute absolute error.
  6. Every sweep entry point accepts and threads a seed, so a surprising result reproduces.
**Plans**: 7 plans (5 waves) — all complete 2026-07-23
- [x] 16-01-PLAN.md — Conditioning core: blocked tall-skinny QR + SVD, correlation matrix, JSON/NPZ report
- [x] 16-02-PLAN.md — Synthetic generator: refractive index plumbed through, WP5 sweep-axis audit
- [x] 16-03-PLAN.md — Config keys, internals/ artifact dir, per-stage calibration dumps
- [x] 16-04-PLAN.md — Per-iteration optimization trace via scipy callback, one CSV per BA stage
- [x] 16-05-PLAN.md — Conditioning wired to the final reported stage, labelled parameters
- [x] 16-06-PLAN.md — Pipeline holdout seed threading and seed recording in outputs
- [x] 16-07-PLAN.md — Standalone evaluate_calibration, pipeline refactor, equivalence regression test

### Phase 17: Per-Camera Interface Ablation Mode
**Goal**: A per-camera `water_z` ablation is available for the WP6 experiment and is provably
correct, without disturbing the default shared-interface behavior the paper's central claim
rests on. This is the second half of the milestone's longest pole and only true experiment
blocker.
**Depends on**: Phase 16 (HOOK-03 conditioning diagnostics are the metric the WP6 ablation
argument needs; this is a prerequisite, not a convenience)
**Requirements**: IFACE-01, IFACE-02, IFACE-03, IFACE-04, IFACE-05
**Success Criteria** (what must be TRUE):
  1. A `shared_interface: bool = True` config flag exists and is documented as an
     analysis/ablation option, not a recommended setting.
  2. `pack_params`, `unpack_params`, `build_jacobian_sparsity`, and `build_bounds` correctly
     handle N per-camera `water_z` parameters when `shared_interface=False`.
  3. `build_structural_column_groups` produces a valid grouping in every mode combination
     (shared/per-camera x intrinsics on/off x tilt on/off), asserted by test.
  4. Per-camera mode seeds from the per-camera `initial_water_z` dict values individually
     rather than collapsing them to a mean.
  5. `shared_interface=True` is bit-unchanged from current behavior, and per-camera mode
     with equal initial values recovers the shared solution on shared-interface ground truth.
**Plans**: 5 plans — all complete 2026-07-23
- [x] 17-01-PLAN.md — Optimizer core: per-camera water_z packing, sparsity, bounds, grouping, labels (IFACE-02, IFACE-03)
- [x] 17-02-PLAN.md — Config surface: shared_interface field, YAML loader pass-through, init template, docs stub (IFACE-01)
- [x] 17-03-PLAN.md — Thread shared_interface through Stage 3/4 optimizers + pipeline wiring + ablation WARNING (IFACE-01, IFACE-02)
- [x] 17-04-PLAN.md — Per-camera seed resolution + water_z spread reporting (console mm + internals JSON) (IFACE-04)
- [x] 17-05-PLAN.md — Bit-exactness + equal-seed recovery tests (IFACE-05)

**Verification**: PASSED 2026-07-23 (`17-VERIFICATION.md`) — all five IFACE requirements traced;
full suite 799 passed. Execution caught and fixed a real bug: `compute_residuals` unpacked
without `shared_interface`, misaligning every per-camera parameter block (fix `575bdc8`).

### Phase 18: Documentation Corrections & Stage-Model Reconciliation
**Goal**: Fix live factual errors in published docs and reconcile the paper's three-stage
model across both code and documentation surfaces, so the stage keys are settled before
benchmark instrumentation writes them into `benchmark.json`.
**Depends on**: Nothing (independent of Phases 16-17; may run in parallel with them)
**Note**: DOCS-01 (the wrong ~12x column-grouping claim, actually 43-52x) is a live factual
error in currently published docs, so it is a candidate for pulling forward. Decided
2026-07-23 to leave it here and fix it with the rest of the docs pass — do not split it
out as a quick task.
**Requirements**: DOCS-01, DOCS-02, DOCS-03, DOCS-04, DOCS-06
**Success Criteria** (what must be TRUE):
  1. `docs/guide/optimizer.md` states the correct column-grouping numbers (13 groups, 17 with
     intrinsic refinement; P = 673/675/727; 43-52x reduction), matching the paper supplement.
  2. Every doc site and `extrinsics.py` docstring that misuses "BFS" now reads "best-first",
     except `_find_connected_components` (genuinely BFS), which is untouched.
  3. The glossary's pose-graph definition describes a bipartite camera/frame graph, and
     `bfs_pose_graph.png` is regenerated from a script that replays the library's own heap logic.
  4. `reject_outlier_frames`, `start_frame`/`stop_frame`, intrinsics seeding, and the
     fronto-parallel warning are documented in the configuration reference and guide pages,
     not only in troubleshooting.
  5. Console output, timing keys, module/schema docstrings, and CLI config comments all
     present the same three-stage model, and the documented loss default reads `huber`.
**Plans**: 8 plans in 3 waves
- Wave 1 (parallel, not gated on the manuscript checkpoint):
  - [x] 18-01-PLAN.md — DOCS-01: pin 673/675/727 + 13/13/17 + 43-52x with a live test, then correct optimizer.md's four numeric errors (DOCS-01)
  - [x] 18-02-PLAN.md — Record the confirmed manuscript vocabulary contract; autonomous, no longer a blocking checkpoint (DOCS-02, DOCS-06)
  - [x] 18-03-PLAN.md — DOCS-04: new docs/guide/configuration.md, guide-index registration, troubleshooting cross-links (DOCS-04)
- Wave 2:
  - [x] 18-04-PLAN.md — DOCS-03: heap-replaying pose_graph.py generator, figure rename, bipartite glossary definition (DOCS-03)
  - [x] 18-05-PLAN.md — DOCS-02 code side: extrinsics.py terminology, scoring comments, first-discovery invariant (DOCS-02)
  - [x] 18-06-PLAN.md — DOCS-06 code side: pipeline.py stage keys/tags/filenames + lockstep tests + auxiliary label loses its stage number (DOCS-06)
  - [x] 18-07-PLAN.md — DOCS-06 code side: schema/CLI/example-config/module docstrings (DOCS-06)
- Wave 3:
  - [x] 18-08-PLAN.md — DOCS-02/DOCS-06 docs side: three-stage sweep, huber loss formula, phase gate (DOCS-02, DOCS-06)

### Phase 19: Benchmark Instrumentation
**Goal**: Every calibration run produces a trustworthy, machine-readable performance record
that a sweep can aggregate without hand computation.
**Depends on**: Phase 18 (stage-model rename must settle before benchmark.json keys are
written — this constraint is preserved and still binding; settling the schema after the
experiment grid runs would force a re-run)
**Requirements**: BENCH-01, BENCH-02, BENCH-03, BENCH-04, BENCH-05, BENCH-06
**Success Criteria** (what must be TRUE):
  1. Solver diagnostics (`nfev`, `njev`, `cost`, `optimality`, `status`, termination message)
     are captured for Stage 3, the intrinsic pass, interface estimation, and point refinement.
  2. Peak memory is reported only behind an explicit opt-in flag, labeled with its
     measurement mode, and never appears by default.
  3. Each run reports parameter count P, column-group count, and the implied FD reduction,
     all computed from the live run.
  4. Every calibration run (real-rig and synthetic) writes a `benchmark.json` into
     `output_dir` with problem shape, per-stage metrics, solver configuration, accuracy,
     and environment (hardware, OS, package versions, AquaCal version/git SHA).
  5. A runner sweeps the cameras x frames grid, collects each `benchmark.json`, and emits a
     tidy CSV plus a LaTeX table fragment without recomputing anything.
     *(Delivered 2026-07-24 as `benchmarks/sweep_runner.py` + `benchmarks/aggregate.py`.
     Relocated under `experiments/` by Phase 19.1 so the suite has one directory and one
     README — a scope transfer, not a correction: the capability shipped and was verified
     here. `sweep_runner.py` was never executed against a real calibration in this phase,
     which is why the relocation is cheap.)*
  6. Stage 3 and Stage 4 pass `ftol`, `xtol`, and `gtol` explicitly rather than inheriting
     SciPy's defaults, `max_nfev`'s effective value is recorded including the unset/auto case,
     and a regression test asserts the change is bit-unchanged — so the tolerances the paper
     supplement states are a property AquaCal sets, not one it happens to inherit.
**Plans**: 6 plans in 4 waves
- Wave 1 (parallel):
  - [x] 19-01-PLAN.md — SolverDiagnostics dataclass + capture_solver_diagnostics() contract (BENCH-01)
  - [x] 19-04-PLAN.md — capture_environment() + capture_peak_memory() + [bench] extra (BENCH-02)
- Wave 2 (parallel, depends on 19-01):
  - [x] 19-02-PLAN.md — optimize_interface + register_auxiliary_camera: explicit tolerances + diagnostics capture (BENCH-01, BENCH-03, BENCH-06)
  - [x] 19-03-PLAN.md — joint_refinement + refine_calibration: explicit tolerances + diagnostics capture (BENCH-01, BENCH-03, BENCH-06)
- Wave 3 (depends on 19-02, 19-03, 19-04):
  - [x] 19-05-PLAN.md — Pipeline integration: config flags, diagnostics wiring, benchmark.json assembly and write (BENCH-03, BENCH-04)
- Wave 4 (depends on 19-05):
  - [x] 19-06-PLAN.md — benchmarks/ runner: CSV + LaTeX aggregator with schema_version refusal, sweep_runner skeleton (BENCH-05)

### Phase 19.1: Experiment Suite Consolidation (INSERTED)

**Goal**: One experiments directory, one implementation of every experiment, and the shared
verbs importable from the installed package — with the two experiments that carry revision
risk (E2, E7) run against the instrumented library as the first real exercise of the scaffold.
**Depends on**: Phase 18 (DOCS-06 settles the stage keys the scripts read), Phase 19
(`benchmark.json` is the run record every experiment emits). Phases 16-17 supply the
observability hooks and the per-camera interface ablation mode.
**Requirements**: EXP-01, EXP-02, EXP-03, EXP-04, EXP-05, EXP-06
**Source brief**: `19.1-SOURCE-BRIEF.md` (Parts 0-1, experiments E1/E2/E7, wave 3)
**Success Criteria** (what must be TRUE):
  1. The shared experiment verbs (`calibrate_synthetic`, `compute_per_camera_errors`,
     `evaluate_reconstruction`) are importable from the installed package as
     `aquacal.datasets.pipelines`, and `aquacal.datasets.__all__` also exports
     `generate_camera_array`, `generate_real_rig_array`, and `generate_board_trajectory` —
     so the tutorial and the experiment scripts use the same public API a user would.
  2. An `experiments/` directory exists outside `src/` with `_io.py` (I/O only), `_render.py`
     (reads CSV, recomputes nothing), a `results/` directory for committed outputs, and a
     README mapping one command to each paper artifact with its expected runtime.
  3. Every experiment script honours the same CLI contract (`--seed`, `--out`, `--force`,
     `--smoke`, `--check`), and `--smoke` is wired into CI so the suite cannot silently break
     against the library it measures.
  4. `tests/synthetic/experiments.py` is gone with its unique content salvaged,
     `compare_refractive.py` has moved to `experiments/` as E1's CLI entry point, the Phase 19
     `benchmarks/` runner has moved under `experiments/`, and no two implementations of the
     same experiment remain in the repo.
  5. E2's real-rig re-run against the current library (v1.7 outlier rejection + v1.8 intrinsics
     seeding) emits `real_rig_metrics.json` and a `benchmark.json`, and every §3 real-rig number
     is either confirmed unchanged or recorded as moved with its new value.
  6. E7 reports per-camera surface-height spread, camera-height drift, focal/standoff drift and
     correlation, and the conditioning report across all four shared/per-camera x fixed/refined
     configurations — with reprojection RMSE explicitly NOT the headline metric.
  7. The ported E1 reproduces every value in the committed `exp{1,2,3}` CSVs, or each
     divergence is explained, and the notebook's gauge-freedom mean-shift correction survives
     the port with an explanation attached.
**Plans:** 8/8 plans complete

Plans:
- Wave 1 (parallel):
  - [x] 19.1-01-PLAN.md — Promote the experiment verbs to `aquacal.datasets.pipelines`, widen `__all__`, shim `experiment_helpers.py`, promote `build_interface_spread_report` (EXP-01)
  - [x] 19.1-02-PLAN.md — Create the `experiments/` package; relocate `benchmarks/aggregate.py` → `_render.py` and `sweep_runner.py` → `e4_benchmark_grid.py`; move the test file (EXP-02, EXP-03)
- Wave 2 (depends on 19.1-02):
  - [x] 19.1-03-PLAN.md — `experiments/_io.py`: five-flag CLI parent, sorted CSV writer, numeric `--check` comparator, resumability, direct-call `benchmark.json` wrapper (EXP-02)
- Wave 3 (depends on 19.1-01, 19.1-03):
  - [x] 19.1-04-PLAN.md — E2 real-rig re-run: resolve A3 by dataset inspection, port notebook 01's export cell, run, write the nine-quantity §3 delta table (EXP-04)
- Wave 4 (parallel, depends on 19.1-04):
  - [x] 19.1-05-PLAN.md — E7 four-arm interface ablation: spread, height drift, focal/standoff, conditioning, traces; RMSE demoted to a control (EXP-05)
  - [x] 19.1-06-PLAN.md — E1 port: reproduce the three committed `exp{1,2,3}` CSVs or explain each divergence; gauge correction via the library keyword (EXP-06)
- Wave 5 (depends on 19.1-04, 19.1-05, 19.1-06):
  - [x] 19.1-07-PLAN.md — Delete `experiments.py` (20-def keep/drop table) and `compare_refractive.py`, delete both notebook export cells, X6 stale-path sweep, `experiments/README.md`, `--smoke` CI job (EXP-02, EXP-03, EXP-06)
- Wave 6 (depends on 19.1-04, 19.1-07):
  - [x] 19.1-08-PLAN.md — BLOCKING non-auto-approvable human gate: user adjudicates E2's nine §3 numbers (EXP-04)

### Phase 19.2: Experiment Execution and Provenance (INSERTED)

**Goal**: The remaining new results the reviewer responses depend on exist, are committed, and
every number in the manuscript and supplement traces to one script, one output file, and one
figure generator.
**Depends on**: Phase 19.1 (the scaffold, the CLI contract, and the public verbs every script
imports; E4's real-rig grid point reuses E2's `benchmark.json`)
**Requirements**: EXP-07, EXP-08, EXP-09, EXP-10, EXP-11
**Source brief**: `19.2-SOURCE-BRIEF.md` (experiments E3/E4/E5/E6, Parts 3-4, wave 4)
**Success Criteria** (what must be TRUE):
  1. E3 emits `code_constants.csv` (declared vs source value with a pass/fail column),
     `newton_iterations.csv`, and `cpr_grouping.csv` covering the six existing `tab:cpr` rows
     plus the per-camera-mode rows, with tier 1's constants also asserted in the test suite so
     CI breaks when a default changes.
  2. E4 runs the cameras {8,12,16} x frames {50,100,200} grid plus the E2 real rig as a tenth
     point, all on one machine, reporting only what `benchmark.json` recorded.
  3. E5 sweeps `n_assumed` in a fine band around 1.333 on the real rig's geometry and reports
     depth/scale bias and held-out RMSE against delta-n — showing the bias moves while the
     reprojection residual does not.
  4. E6 sweeps refractive index, layout, and scale one axis at a time through a common
     baseline, emitting tidy long-format rows carrying which axis varied.
  5. Every committed result across E1-E7 carries its seed, AquaCal version, git SHA, and
     environment — reusing `benchmark.json` rather than hand-rolling a sidecar, with a minimal
     sidecar for E3's tiers 1-2 which never run a calibration.
  6. `experiments/README.md`'s provenance table is complete: every paper artifact maps to its
     producing script, its data file, and its figure generator.
**Plans:** 29/29 plans complete
(D-26: all `src` changes land and are proven contained before any experiment yielding a publishable
result — see `19.2-GAP-CONTEXT.md` § "D-26 reconciliation")

Plans:
- [x] 19.2-01-PLAN.md — wave 1 — `calibrate_synthetic` gains `memory_out` (D-06), honours the scenario's own `n_air`/`n_water` (D-23), and gains a `normal_fixed` passthrough so the grid can run tilt-enabled (review H1); all three exact-equality guarded
- [x] 19.2-02-PLAN.md — wave 1 — `SolverDiagnostics.n_residuals` for the Jacobian element count (D-15), plus `memory_readings` (D-24) and an additive `seed` (review H5) threaded through `write_direct_call_benchmark`
- [x] 19.2-03-PLAN.md — wave 1 — public Newton iteration diagnostic sharing the private projector's loop, exported from `aquacal.core` (D-19)
- [x] 19.2-04-PLAN.md — wave 1 — the declared-constants table owned by `tests/` (D-18, now 9 rows covering all three Huber `f_scale` sites) and the `P`-formula validation against live `pack_params` (D-22)
- [x] 19.2-14-PLAN.md — wave 1 — **NEW (D-26)** — `seed` added to `run_calibration_from_config`'s `solver_config`, so a pipeline-written `benchmark.json` carries its seed; frozen-anchor exact-equality guard proves the addition inert
- [x] 19.2-06-PLAN.md — wave 2 — E2 re-run against the local release frameset with `benchmark_memory: true`; a moved section-3 number is a hard stop (D-07/D-08). **Moved from wave 1 by D-26**: its launch gate is now "every `src` change is covered by a passing exact-equality bit-identity test", replacing the withdrawn `git diff .. -- src/` is-empty check
- [x] 19.2-05-PLAN.md — wave 3 — E3 `experiments/e3_derived_quantities.py`: tiers 1-3, all six `tab:cpr` rows in both interface modes (review H1 retires the D-16 split), LaTeX fragments, environment-only sidecar. Now `depends_on` 19.2-06 — its 13/200 row copies from E2's refreshed record
- [x] 19.2-07-PLAN.md — wave 3 — E4 rewritten as a direct-call synthetic grid, tilt-enabled and self-describing, one subprocess per cell so peak memory is per-run and an OOM is a recorded exit code (D-01..D-04, D-14, D-15; review H1/H2/H3/H5)
- [x] 19.2-08-PLAN.md — wave 4 — E5 `experiments/e5_index_sensitivity.py`: index band on real-rig geometry, bias vs both its own Δn = 0 control and the live-read E2 noise floor (code and tests only)
- [x] 19.2-10-PLAN.md — wave 4 — E6 `experiments/e6_generalization_sweep.py`: three one-dimensional axes through E4's 12-camera baseline at E4's own tilt configuration (D-11, D-12; review M2/M4/M5/M7)
- [x] 19.2-09-PLAN.md — wave 5 — E4 production run, **alone on the box**: one measured probe cell, then nine cells plus E2's tenth point, `benchmark_grid.csv` + LaTeX
- [x] 19.2-13-PLAN.md — wave 6 — E5 production run and `index_sensitivity.csv` (split out of 19.2-08 so it never shares the machine with E4's grid — review H4)
- [x] 19.2-11-PLAN.md — wave 7 — E6 production run and `generalization_sweep.csv` (sequenced last; the compressible sweep), with a baseline cross-check against E4's 12/100 cell
- [x] 19.2-12-PLAN.md — wave 8 — EXP-11 close-out: provenance key-presence and seed tests with an explicit six-member legacy carve-out (E2's refreshed record is NOT exempt), README table completion, CI smoke wiring, derived-values verification

Gap-closure plans (verification `gaps_found` 5/7; `19.2-GAP-CONTEXT.md` D-27..D-33, review CR-01..CR-05):
- [x] 19.2-15-PLAN.md — wave 1 — CR-04: make `compare_experiment_csv` total — a row-count or key-set mismatch produces a report, not a `ValueError` (third bug in this function this phase; fixed as a contract, not a fourth dtype case)
- [x] 19.2-16-PLAN.md — wave 1 — CR-02/WR-08: E6's resume path returns the checkpoint it wrote (metrics and failure reason survive), plus D-31's E6 half — an `e6_provenance.json` sidecar and self-describing checkpoints
- [x] 19.2-17-PLAN.md — wave 1 — CR-01/CR-03 and all three D-33 gaps: lossless E4 resume, guarded aggregation, per-cell timeout, a real-child failure test, and commit/virtual memory plus a pre-flight ceiling so a paged success cannot report `status=ok`
- [x] 19.2-18-PLAN.md — wave 2 — D-27/D-28/D-29: the board volume centres on the array centroid, `xy_extent` scales with the footprint, and the grid family moves to real-rig optical geometry — with D-27's containment gate (frozen anchors, grep-gate, four `--check` reproductions) standing in for D-26's blanket inertness proof
- [x] 19.2-19-PLAN.md — wave 2 — D-31's E5 half: an `e5_provenance.json` sidecar carrying the run configuration (WR-04), with `E5_COLUMNS` deliberately unchanged so wave 5's re-run is a determinism proof; plus WR-06/WR-12
- [x] 19.2-20-PLAN.md — wave 2 — D-32/CR-05: opt-in per-point instrumentation on the batch Newton loop the optimizer actually runs, proven bit-identical on production output, with E3 tier 2 rewired onto it
- [x] 19.2-21-PLAN.md — wave 3 — E4's nine-cell grid re-run on the new geometry, **alone on the box**; 16×200 is pre-authorised to fail as a recorded row
- [x] 19.2-22-PLAN.md — wave 4 — E6's sweep re-run, **alone on the box**, re-anchored to E4's new 12×100 cell; `layout_line` is the direct empirical test of D-27
- [x] 19.2-23-PLAN.md — wave 5 — E5's band re-run for provenance and E3's fast tiers, **alone on the box**; a moved science column is a hard stop, and only `newton_iterations.csv` may change schema
- [x] 19.2-24-PLAN.md — wave 6 — widen the EXP-11 gate to all four fields per artifact, per file (WR-11), and re-assert E1's and E7's reproduction on the shipping tree
- [x] 19.2-25-PLAN.md — wave 6 — make the README's universal provenance claim true, record the pre/post-D-27 boundary, close EXP-07/09/10/11 in `REQUIREMENTS.md`, and resolve MF-01 and MF-02 against fresh measurements

### Phase 19.3: Scenario Geometry and Convergence (INSERTED)

**Goal**: The synthetic scenarios are physically valid — board corners stay below the water
surface at every frame — so first-order optimality is a trustworthy convergence diagnostic
again; the five affected experiments are re-measured and the correction is reported.
**Depends on**: Phase 19.2 (a coherent baseline to measure the fix against; D-29's grid-family
geometry is what this phase finishes)
**Requirements**: GEOM-01, GEOM-02, GEOM-03, GEOM-04, GEOM-05, GEOM-06
**Source brief**: `19.3-SEED.md` (diagnosis, physics reasoning, four locked user decisions)
**Success Criteria** (what must be TRUE):
  1. Board poses are re-centred so `tvec` positions the board centre (the code positioned
     corner (0,0,0) while the docstring promised the centre), and both trajectory generators
     take a required `BoardConfig` and raise `ValueError` when `depth_range` violates a
     clearance floor derived from the board's own corner cloud and the rotation range —
     1.181 m at 15°, 1.226 m at 20°. A derivation, not a hardcoded constant.
  2. The real-rig standoff is finished into the library: `generate_camera_array`'s default
     `height_above_water` and both `create_scenario` presets move off 0.15 m, so no scenario
     can be constructed mis-framed. `default_board` stays shared and unchanged.
  3. E6's scale axis anchors at the derived floor rather than the water surface, so every
     scale value is legal by construction, and its docstring prose matches what it now
     measures.
  4. The pinhole continuation is demoted to a recorded numerical guard: the library counts
     hits on the final solution evaluation and the experiment harnesses gate on a non-zero
     count, so a degenerate cell can never be published as `status="ok"`. The change is
     proven inert by exact-equality test, keeping E2 out of scope.
  5. `DegenerateObservationWarning` no longer advises judging convergence on optimality —
     the advice that is wrong in precisely the situation that emits it.
  6. E1/E3/E4/E5/E6/E7 are re-measured on corrected geometry (~9 h, chained, detached), and the
     paired determinism sweep reports the cell reproduction count against the 63/308 pre-fix
     baseline as a pre-declared statistic. (E3 added 2026-08-02 — omitted from the seed's
     blast-radius table but affected via `generate_real_rig_trajectory`; tier 2 only.)
  7. MF-08 records the before/after with pre-fix artifacts archived, claiming "accuracy
     unaffected" only where a measured seed band supports it (E1/E5/E7 yes; E3/E4/E6 report the
     diagnostic improvement without an accuracy claim).
     **Met, and stricter than written:** only **E7** qualified. E1's band was pre-fix geometry
     (the corrected band is 4.5x narrower and both metrics fall outside); E5's band varies the
     assumed index, not the seed. See REQUIREMENTS.md § GEOM-06.
**Note**: ships a breaking change (`generate_board_trajectory` is a public export gaining a
required parameter) — cuts **v2.0.0**. Phases 21 and 22 must know before resolving version
strings.

> **HANDOFF TO PHASES 21 AND 22 — the milestone cuts v2.0.0, not a v1.9.x.**
> Confirmed on phase close, 2026-08-04 (D-19.3-06, Sequencing Constraint 13). Plan 19.3-01 made
> `board` a **required** parameter of `generate_board_trajectory` and `generate_real_rig_trajectory`,
> both public exports. Any caller that omitted it now raises `TypeError`, so the next release is a
> **major** bump. Both phases resolve version strings and must read this before writing one.
> The closing commit is scoped `feat!:` so python-semantic-release cuts the major bump on the
> first push. **Never hand-edit the version or CHANGELOG.**
>
> **Carried forward, deliberately unfixed:** the E4/E6 clearance-floor defect (`GRID_DEPTH_RANGE`
> frozen at import from a seed-42 array) is diagnosed but not applied — it gets its own phase by
> user decision. Planning input: `.planning/debug/e6-seed-locked-clearance-floor.md`.
**Plans**: 10 plans across 7 waves

Plans:
- [x] 19.3-01-PLAN.md — wave 1 — re-centre board poses on the board centre, derive the clearance floor from the corner cloud, make `board` required and raise `ValueError` on an illegal `depth_range` (GEOM-01)
- [x] 19.3-02-PLAN.md — wave 1 — record the final-solution guard count into `discard_stats`, correct the `DegenerateObservationWarning` text, and prove the change inert by exact equality (GEOM-04)
- [x] 19.3-03-PLAN.md — wave 1 — archive the five experiments' pre-depth-fix artifacts under the established `experiments/archive/` convention (GEOM-06)
- [x] 19.3-04-PLAN.md — wave 2 — move `generate_camera_array`'s default and both `create_scenario` presets onto the real-rig standoff; regenerate the affected anchors (GEOM-02)
- [x] 19.3-05-PLAN.md — wave 2 — derive `GRID_DEPTH_RANGE`, thread the board through `build_grid_scenario`, and update E3's and E5's three hardcoded call sites (GEOM-01)
- [x] 19.3-06-PLAN.md — wave 3 — anchor E6's scale axis at the derived floor and correct the axis prose (GEOM-03)
- [x] 19.3-07-PLAN.md — wave 4 — gate E4/E6 cell status on the guard count, record it in E1/E5/E7, and take the full unfiltered suite green at the code-wave boundary (GEOM-04)
- [x] 19.3-08-PLAN.md — wave 5 — verify E6's resume mechanism, write the machine-checkable gate script, and write the chained detached re-run queue (GEOM-05)
- [x] 19.3-09-PLAN.md — wave 6 — freeze the tree and execute the ~9 h detached serial re-run of E1/E4/E5/E6x2/E7 (GEOM-05) — ran in **6 h 02 min**, all seven stages exit 0, one git sha (`22e75ef`) across every artifact
- [x] 19.3-10-PLAN.md — wave 7 — report the cell reproduction count against 63/308, write MF-08, and draft the reviewer-response prose (GEOM-05, GEOM-06) — **8 of 308**, before 63 of 308

### Phase 19.4: Single Flat Interface (INSERTED)

**End state this serves**: good-quality, CURRENT numbers across ALL experiments, ready for
analysis and transfer into the publication — a result set a reviewer could re-run and reproduce,
and the author can lift numbers from directly. The interface fix is the means, not the end.
**Goal**: Every synthetic scenario models **one flat water surface shared by all cameras**,
matching the physical premise the method and the manuscript rest on. The per-camera interface
*distance* variation is preserved by moving it onto camera height. The two affected experiments
(E4, E6) are re-measured; the four unaffected ones (E1, E3, E5, E7) are proven unaffected.
**Depends on**: Phase 19.3
**Requirements**: SC-1, SC-2, SC-3, SC-4, SC-5, SC-5a, SC-6, SC-7, SC-8 (this phase's Success
Criteria below ARE its requirement set; REQUIREMENTS.md maps no IDs to 19.4)
**Source brief**: `19.4-RESCOPE-PROPOSAL.md` (the five-source audit and the pixel measurement);
`19.4-CONTEXT.md` (decisions D-19.4-09..17, plus § CORRECTION: E7 is inert)
**Success Criteria** (what must be TRUE):
  1. Every synthetic scenario source yields exactly ONE distinct `water_z`, asserted by a test
     covering all three `create_scenario` presets, `generate_real_rig_array`, and
     `generate_camera_array` across layouts and seeds.
  2. The jitter moves from `water_z` to `C_z` with each camera's `h_c` preserved exactly.
  3. E1, E3, E5 **and E7** are PROVEN bit-inert, not assumed.
  4. `GRID_DEPTH_RANGE` re-derived; the clearance floor is seed-invariant by construction.
  5. E4 and E6 re-measured. E7's 10-seed band is produced as a committed artifact so the
     milestone's only surviving accuracy claim becomes regenerable — its numbers are reproduced,
     not replaced.
  5a. E1 and E7 gain a `--seeds` mode emitting a committed band CSV, so every banded number in
     MF-08 is regenerable by running the experiment rather than trusting a planning document.
     Today the bands live only in gitignored `seed_sweep_19_3/` output.
  6. Long runs abort on the first failed cell and exit non-zero.
  7. The verification queue runs risk-first (e6, e4 early) so both high-risk stages complete
     inside 4 h, and a src defect triggers abort-and-restart rather than a midstream edit that
     would split the one-git-sha-per-artifact property.
  8. **Before the queue launches**, a coverage matrix confirms each reviewer point is still
     answered by the experiment assigned to it — read against the pre-review paper, the reviewer
     responses, and the response plan that spawned the experiment chain. A gap amends the queue
     BEFORE launch, not after.
**Note**: **published numbers WILL move** for E4 and E6 — the opposite of 19.3's constraint.
(Corrected 2026-08-04 during planning: E7 was originally listed here. E7 runs the `"realistic"`
scenario, which resolves to `generate_real_rig_array`'s frozen shared `WATER_Z`, and never calls
`generate_camera_array` — so it is inert. See `19.4-CONTEXT.md` § CORRECTION.)
Measured impact of the defect: mean 1.42 px, max 6.33 px over 31,680 corner observations, against
an E4/E6 reprojection RMS of ~0.4-0.9 px. The modelling error exceeds the residual it was being
measured against.
**Verification cost**: ~9 h 30 min, one overnight run — full seven-stage queue 6 h 02 min, E7
band +50 min, E1 band +57 min, E6 at formerly-failing seed 43 +99.6 min. Measured from 19.3's
queue, not estimated.
**Plans**: 10 plans in 6 waves

> **SUPERSEDED SCOPE.** This phase was created as "Grid-Family Clearance Floor Fix" and planned
> with 7 plans and decisions D-19.4-01..08 before the root cause was understood. That scope is
> cancelled — the clearance floor only moved with the seed because the ground truth gave each
> camera its own water surface. Plans deleted; see `git show aa9ad7f`. The directory name is
> historical.

Plans:
- [x] 19.4-01-PLAN.md — wave 1 — archive E4's and E6's pre-interface-fix artifacts with provenance READMEs (SC-5, D-19.4-10)
- [x] 19.4-02-PLAN.md — wave 1 — move `generate_camera_array`'s jitter from `water_z` to `C_z` and add the scenario-invariant one-water_z test (SC-1, SC-2, D-19.4-09)
- [x] 19.4-03-PLAN.md — wave 1 — pre-run reviewer-intent coverage matrix; GATES the queue (SC-8, D-19.4-17)
- [x] 19.4-05-PLAN.md — wave 1 — shared `parse_seed_list`/`run_seed_band` in `_io.py` plus E7's `--seeds` band (SC-5a, D-19.4-14)
- [x] 19.4-04-PLAN.md — wave 2 — `derive_grid_depth_range` helper, floor re-derived to 1.176215948246, E1/E3/E5/E7 inertness proof (SC-3, SC-4, D-19.4-12/15)
- [x] 19.4-06-PLAN.md — wave 2 — E1's `--seeds` band over the depth-generalization rows (SC-5a, D-19.4-14)
- [x] 19.4-07-PLAN.md — wave 3 — fail-fast in E4 and E6 with a `--no-fail-fast` opt-out (SC-6, D-19.4-11)
- [x] 19.4-08-PLAN.md — wave 4 — write the risk-first resumable queue, extend the gate script, narrow the prelaunch gate (SC-7, D-19.4-16)
- [x] 19.4-09-PLAN.md — wave 5 — execute the ~9 h 30 min production queue once, under one git sha (SC-5, SC-7, D-19.4-13/16)
- [x] 19.4-10-PLAN.md — wave 6 — inertness verdict by byte-comparison, MF-05/MF-08 updates, new interface finding, phase closure (SC-3, SC-5, SC-5a, SC-8)

### Phase 19.5: Experiment Coverage and Uncertainty Bands (INSERTED)

**Goal**: Every experiment the reviewer response leans on either carries a measured
uncertainty band or states plainly that it does not — and the two reviewer comments with no
experimental answer at all (R1.2 accuracy, R1.3 scaling) get one. Phases 19.2-19.4 established
that the experiments are *correct*; this phase establishes what may be *claimed* from them.

**Why now, and why it is cheap**: 19.4's single-flat-interface fix made the grid family's
clearance floor seed-invariant (`generate_camera_array` now returns one shared
`height_above_water`), so `GRID_DEPTH_RANGE` is correct by construction and the ~5.8%-of-seeds
legality trap that made E4 and E6 un-sweepable is gone. The seed bands D-19.3-17 requires were
blocked by that trap; they are now merely a matter of runtime.

**Depends on**: Phase 19.4 (the seed-invariant clearance floor is the enabler; the committed
`experiments/results/` at `0ffbe15` is the baseline every band is measured against)

**Requirements**: COV-01, COV-02, COV-03, COV-04, COV-05, COV-06, COV-07, COV-08, COV-09
(defined in REQUIREMENTS.md § Experiment Coverage and Uncertainty; the Success Criteria below
map one-to-one onto them in order)

**Scope decision (user, 2026-08-05)**: Tier A + Tier B + the E2 replicate band are IN. The
Stage-2 basin-of-attraction study for R4.3 is OUT — R4.3 keeps its prose-plus-optimality answer.

**Sequencing (user, 2026-08-05)**: cheap-first. Land and verify every zero-runtime item, then
assemble all remaining solves into a SINGLE risk-first overnight queue under one frozen git sha,
following the 19.4 pattern (`rerun_19_4.sh`). Do not interleave production runs with commits —
per-cell `git rev-parse` splits an artifact's recorded SHA.

**Constraint**: experiment scripts only. No non-inert `src/` change. If a diagnostic hook is
unavoidable, it takes the D-32/E3 pattern — opt-in flag, off by default, proven bit-identical to
current production output when unset.

**Success Criteria** (what must be TRUE):
  1. **R1.3 has an experimental answer.** A purely structural sweep (no calibration solve)
     records `n_params`, `n_groups`, `fd_reduction`, nnz and Jacobian element count over camera
     counts well past the reviewer's "N>10" and a range of frame counts, showing the group count
     pins at 13/17 independent of N, and locating the 500 M-element dense→sparse/LSMR boundary
     as a disclosed scaling limit rather than an unstated one.
  2. **R1.2 has an accuracy answer, not only a cost answer.** The shipped finite-difference
     Jacobian is compared against a tighter-step/Richardson reference, reporting column-wise
     relative error and the induced change in the optimizer step, plus a step-size sweep showing
     the shipped choice sits in the flat region. The full analytic derivation stays declined.
  3. **E6 carries a seed band.** The generalization sweep — the entire R1.4 substitute, and
     content that appears nowhere in the submitted manuscript — is measured at multiple seeds, so
     it can make an accuracy claim under D-19.3-17 instead of none. The two known seed-fragile
     spots are adjudicated: `scale/double_scale` intrinsic-pass optimality and `layout/line`'s
     ~4x `water_z_error_mm` spread.
  4. **E6 gains a camera-count axis.** Accuracy vs `n_cameras` is measured, not just timing vs
     `n_cameras` (E4). R1.3's "stably adapts" is an accuracy question that nothing currently
     answers.
  5. **E5 carries a seed band.** R2's headline — index-induced scale bias sits below the holdout
     noise floor — is stated against a measured floor rather than a single run's one number.
  6. **E4's runtime numbers carry a repeat.** At least the run-to-run spread of a subset is
     measured, given every 200-frame cell ran at `near_physical_ceiling` and 19.4 observed an
     unexplained ~2x environmental slowdown. Any shipped timing table reports `nfev` beside
     wall-clock (MF-03).
  7. **E2 carries a band.** The real-rig headline — the abstract's second number — is measured
     across calibration/holdout splits by varying `config.seed`. Its scope is stated exactly:
     split variance on fixed data, NOT measurement variance.
  8. **Two zero-runtime analyses of already-committed data land.** E7's `focal_drift_pct` /
     `standoff_m` columns are analyzed for the L149 focal/standoff degeneracy WP6 planned and
     MF-05 never reported; and a bootstrap CI over the 7,762 committed inter-corner comparisons
     gives the real-rig headline a stated interval, labelled as metric sampling variance only.
  9. **Every band lands in MANUSCRIPT-FINDINGS.md** as an MF entry naming its citable artifact,
     and MF-09's edit map is updated wherever a band changes what may be claimed.

**Plans:** 9/11 plans executed

Plans:
- [x] 19.5-01-PLAN.md -- COV-01: structural scaling sweep to N=128, 13/17 group pinning, the 500 M dense/sparse boundary located analytically (leaves `cpr_grouping.csv` untouched)
- [x] 19.5-02-PLAN.md -- COV-02: FD Jacobian accuracy vs a Richardson reference, step sweep, Newton 1e-9 floor adjudicated -- `experiments/` only, no `src/` change
- [x] 19.5-03-PLAN.md -- COV-08a: E7 focal/standoff paired re-analysis across the ten committed seeds and four arms
- [x] 19.5-04-PLAN.md -- COV-08b: frame-clustered bootstrap over the 7,762 committed comparisons (52 frames), scoped "metric sampling variance only"
- [x] 19.5-05-PLAN.md -- COV-05: E5 `--seeds` band, named apart from its existing `n_assumed_band` (code only)
- [x] 19.5-06-PLAN.md -- COV-03/04: E6 `--seeds` band with mandatory per-seed isolated dirs, plus an opt-in `cameras` axis (code only)
- [x] 19.5-07-PLAN.md -- COV-07: E2 seed-variant config generator; `--seed` is a red herring on the `--config` path (code only)
- [x] 19.5-08-PLAN.md -- COV-06: E4 repeat splice over the three 100-frame cells, `nfev` beside wall-clock (code only)
- [x] 19.5-09-PLAN.md -- Writes `rerun_19_5.sh`, the four new band gates and the D-19.5-04 legality probe. Budget as planned: ~15 h nominal, **26 h ceiling** -- revised before launch to ~17 h / **30 h** for six-seed bands
- [x] 19.5-10-PLAN.md -- **Orchestrator only.** Ran the one queue 2026-08-06/07: five stages, 16 h 31 m (0.97x of nominal), 102/102 E6 rows `ok`, no commit mid-run, one frozen sha `2a2f0fa`
- [x] 19.5-11-PLAN.md -- COV-09: MF-11..MF-17 written, MF-09 edit map updated, COV-01..COV-09 discharged with a per-requirement artifact table

### Phase 20: Refractive Index Helper
**Goal**: Users can estimate `n_water` from environmental conditions and transfer the
estimate into their config by hand.
**Depends on**: Nothing (fully standalone)
**Requirements**: INDEX-01, INDEX-02, INDEX-03
**Success Criteria** (what must be TRUE):
  1. `water_refractive_index(temperature_c, salinity_g_per_l, wavelength_nm, ...)` is a pure
     function with no I/O or pipeline dependency, citing a published empirical formulation
     and documenting its validity envelope, rejecting or warning on out-of-envelope inputs.
  2. `aquacal calc-index` prints the estimated index, the inputs that produced it, and the
     `n_water` config key to paste it into, in greppable form.
  3. Tests cover the known reference value (distilled water at 20C ~= 1.333), monotonicity
     in temperature and salinity, and rejection of out-of-envelope inputs.
**Plans**: TBD

### Phase 21: New-Feature Documentation & Dataset Refresh
**Goal**: Every capability this milestone added is discoverable in the docs, and the
published dataset and tutorial outputs reflect the current library rather than 2026-02.
**Depends on**: Phase 16, Phase 17, Phase 18, Phase 19, Phase 20 (documents and exercises
everything built in this milestone; dataset regeneration needs the settled stage model)
**Requirements**: DOCS-05, DATA-01, DATA-01a, DATA-01b, DATA-02, DATA-03
**Success Criteria** (what must be TRUE):
  1. `calc-index`, the `benchmark.json` schema, the trace and conditioning flags, and
     `shared_interface` (framed as an ablation option) are all documented.
  2. The real-rig dataset config is regenerated through current `aquacal init` (not
     hand-patched), with every difference from the shipped config confirmed deliberate,
     settling whether `initial_distances` was a scalar or carried pre-v1.4 semantics.
  2a. **PUBLICATION BLOCKER (added 2026-07-27, Phase 19.1 finding).** The regenerated archive
     carries the frameset that produced the manuscript's §3 numbers — a fresh
     `load_example("real-rig")` run reproduces `reconstruction.num_comparisons = 7762` and the
     other eight §3 quantities, not the currently-published ~4.3× subsampled extraction's
     1,817. Without this the published dataset does not reproduce the published numbers, which
     is the "one number, one origin" failure the milestone exists to prevent. See
     `.planning/phases/19.1-experiment-suite-consolidation/19.1-E2-FRAMESET-PROVENANCE.md`.
  3. A new Zenodo version is published; `manifest.json`'s `zenodo_record_id`, `checksum`,
     and `size_bytes` are updated together; `load_example("real-rig")` is verified to
     download, checksum, and extract at the path the notebook resolves.
  4. Both tutorial notebooks are re-executed with fresh committed outputs, and any narration
     the outputs contradict (including the three-stage framing and runtime estimate) is updated.
**Plans**: 12 plans in 7 waves
(Phase 20 is DEFERRED by user decision 2026-08-07 on measured evidence — MF-13. Phase 21's
dependency on it is documentation-shaped and does not block; `calc-index` documentation rides
with Phase 20 whenever it lands. See `21-CONTEXT.md` D-01.)

Plans:
- Wave 1 (parallel, no dependencies):
  - [ ] 21-01-PLAN.md — `scripts/extract_frames.py`: deterministic every-30th-frame AVI -> lossless PNG extractor with zero-frame and ragged-count guards, plus unit tests (DATA-01a)
  - [ ] 21-02-PLAN.md — new `docs/guide/benchmarking.md`: `benchmark.json` field-by-field, the eight trace CSV columns with interpretation, the conditioning JSON/NPZ; forward links from `configuration.md`; D-04 verify-only pass (DOCS-05)
  - [ ] 21-03-PLAN.md — new `docs/tutorials/03_cli_walkthrough.md`: the docs' first end-to-end CLI worked example, every number attributed inline to the archive's own `reference_outputs/` (DOCS-05, DATA-02)
  - [ ] 21-04-PLAN.md — notebooks go fast and synthetic-only: 01's Zenodo branch deleted, 02 demoted to `RIG_SIZE = "small"`, full editorial pass, both re-executed (DATA-03)
  - [ ] 21-05-PLAN.md — reword DOCS-05 / DATA-02 / DATA-03, add DATA-01b to this phase's requirement line, verify the OpenCV `<5.0` pin (DOCS-05, DATA-02, DATA-03)
- Wave 2 (depends on 21-01):
  - [ ] 21-06-PLAN.md — **LONG, not autonomous**: the production extraction, 12 GB of AVI -> ~4.4 GB of lossless PNG, 13 x 262 extrinsic frames plus the intrinsic set (DATA-01a)
- Wave 3 (depends on 21-06):
  - [ ] 21-07-PLAN.md — archive assembly: `config_paper.yaml` + `config_quickstart_not_paper.yaml`, the DATA-01b reference outputs, the zip, and D-15 gates 2 and 4 (DATA-01, DATA-01b, DATA-02)
- Wave 4 (depends on 21-07, 21-03):
  - [ ] 21-08-PLAN.md — **LONG, not autonomous**: D-15 gate 1 (~50 min §3 reproduction from the zipped bytes, `num_comparisons = 7762`) and gate 3 (the tutorial's commands verbatim); D-16 halt on any miss (DATA-01a, DATA-02)
- Wave 5 (depends on 21-08):
  - [ ] 21-09-PLAN.md — **BLOCKING HUMAN GATE**: the user uploads and publishes a new version of Zenodo record 18645385 by hand in the web UI; no token, values pre-computed for transcription (DATA-02)
- Wave 6 (parallel, depends on 21-09):
  - [ ] 21-10-PLAN.md — `manifest.json`'s three fields updated together; cold-cache `load_example("real-rig")` verified end to end (DATA-02)
  - [ ] 21-11-PLAN.md — DATA-01b repo surgery: three artifacts out of git, the `check-added-large-files` exclusion removed, `reconstruction_bootstrap.py` repointed, README provenance repaired (DATA-01b)
- Wave 7 (independent; **droppable** if the 2026-08-21 deadline forces a scope cut):
  - [ ] 21-12-PLAN.md — folded todo: verify numerically whether the `n_water = 1.0` baseline is converged, and record the consequence for §3's refractive-vs-non-refractive claims as an MF entry (DOCS-05)

### Phase 22: Release Cut
**Goal**: The version referenced by the manuscript and the Zenodo archive is the one whose
behavior the published artifacts actually reflect.
**Depends on**: Phase 21 (dataset/tutorial refresh must land before the release it's cut against)
**Requirements**: DOCS-07
**Success Criteria** (what must be TRUE):
  1. A release is cut incorporating all v1.9 work.
  2. The manuscript's C1 metadata cell is updated to the released version.
  3. The Zenodo archive reference is updated to match the same version.
**Plans**: TBD

## Progress

| Phase | Milestone | Plans Complete | Status | Completed |
|-------|-----------|----------------|--------|-----------|
| 1. Foundation and Cleanup | v1.2 | 3/3 | Complete | 2026-02-14 |
| 2. CI/CD Automation | v1.2 | 3/3 | Complete | 2026-02-14 |
| 3. Public Release | v1.2 | 3/3 | Complete | 2026-02-14 |
| 4. Example Data | v1.2 | 3/3 | Complete | 2026-02-14 |
| 5. Documentation Site | v1.2 | 4/4 | Complete | 2026-02-14 |
| 6. Interactive Tutorials | v1.2 | 4/4 | Complete | 2026-02-15 |
| 7. Infrastructure Check | v1.4 | 1/1 | Complete | 2026-02-15 |
| 8. CLI QA Execution | v1.4 | 1/1 | Complete | 2026-02-15 |
| 9. Bug Triage | v1.4 | 0/0 | Complete | 2026-02-17 |
| 10. Documentation Audit | v1.4 | 3/3 | Complete | 2026-02-16 |
| 11. Documentation Visuals | v1.4 | 2/2 | Complete | 2026-02-17 |
| 12. Tutorial Verification | v1.4 | 3/3 | Complete | 2026-02-19 |
| 13. Core Refinement | v1.6 | 2/2 | Complete | 2026-02-28 |
| 14. Optimization Extensions | v1.6 | 2/2 | Complete | 2026-02-28 |
| 15. Validation and Result Contract | v1.6 | 2/2 | Complete | 2026-02-28 |
| 16. Experiment Observability Hooks | v1.9 | 7/7 | Complete | 2026-07-23 |
| 17. Per-Camera Interface Ablation Mode | v1.9 | 5/5 | Complete | 2026-07-23 |
| 18. Documentation Corrections & Stage-Model Reconciliation | v1.9 | 8/8 | Complete    | 2026-07-24 |
| 19. Benchmark Instrumentation | v1.9 | 6/6 | Complete    | 2026-07-24 |
| 19.1 Experiment Suite Consolidation | v1.9 | 8/8 | Complete    | 2026-07-27 |
| 19.2 Experiment Execution and Provenance | v1.9 | 29/29 | Complete   | 2026-08-01 |
| 19.3 Scenario Geometry and Convergence | v1.9 | 10/10 | Complete   | 2026-08-04 |
| 19.4 Single Flat Interface | v1.9 | 10/10 | Complete   | 2026-08-05 |
| 20. Refractive Index Helper | v1.9 | 0/TBD | Not started | - |
| 21. New-Feature Documentation & Dataset Refresh | v1.9 | 0/12 | Planned | - |
| 22. Release Cut | v1.9 | 0/TBD | Not started | - |
