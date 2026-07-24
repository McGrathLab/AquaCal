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
- [ ] **Phase 18: Documentation Corrections & Stage-Model Reconciliation** - Fix live doc errors and reconcile the three-stage model across code and docs before instrumentation locks in a schema
- [ ] **Phase 19: Benchmark Instrumentation** - Every calibration run produces a trustworthy, machine-readable performance record
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
  - [ ] 18-04-PLAN.md — DOCS-03: heap-replaying pose_graph.py generator, figure rename, bipartite glossary definition (DOCS-03)
  - [ ] 18-05-PLAN.md — DOCS-02 code side: extrinsics.py terminology, scoring comments, first-discovery invariant (DOCS-02)
  - [ ] 18-06-PLAN.md — DOCS-06 code side: pipeline.py stage keys/tags/filenames + lockstep tests + auxiliary label loses its stage number (DOCS-06)
  - [ ] 18-07-PLAN.md — DOCS-06 code side: schema/CLI/example-config/module docstrings (DOCS-06)
- Wave 3:
  - [ ] 18-08-PLAN.md — DOCS-02/DOCS-06 docs side: three-stage sweep, huber loss formula, phase gate (DOCS-02, DOCS-06)

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
  5. A `benchmarks/` runner sweeps the cameras x frames grid, collects each `benchmark.json`,
     and emits a tidy CSV plus a LaTeX table fragment without recomputing anything.
  6. Stage 3 and Stage 4 pass `ftol`, `xtol`, and `gtol` explicitly rather than inheriting
     SciPy's defaults, `max_nfev`'s effective value is recorded including the unset/auto case,
     and a regression test asserts the change is bit-unchanged — so the tolerances the paper
     supplement states are a property AquaCal sets, not one it happens to inherit.
**Plans**: TBD

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
**Requirements**: DOCS-05, DATA-01, DATA-02, DATA-03
**Success Criteria** (what must be TRUE):
  1. `calc-index`, the `benchmark.json` schema, the trace and conditioning flags, and
     `shared_interface` (framed as an ablation option) are all documented.
  2. The real-rig dataset config is regenerated through current `aquacal init` (not
     hand-patched), with every difference from the shipped config confirmed deliberate,
     settling whether `initial_distances` was a scalar or carried pre-v1.4 semantics.
  3. A new Zenodo version is published; `manifest.json`'s `zenodo_record_id`, `checksum`,
     and `size_bytes` are updated together; `load_example("real-rig")` is verified to
     download, checksum, and extract at the path the notebook resolves.
  4. Both tutorial notebooks are re-executed with fresh committed outputs, and any narration
     the outputs contradict (including the three-stage framing and runtime estimate) is updated.
**Plans**: TBD

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
| 18. Documentation Corrections & Stage-Model Reconciliation | v1.9 | 3/8 | In Progress|  |
| 19. Benchmark Instrumentation | v1.9 | 0/TBD | Not started | - |
| 20. Refractive Index Helper | v1.9 | 0/TBD | Not started | - |
| 21. New-Feature Documentation & Dataset Refresh | v1.9 | 0/TBD | Not started | - |
| 22. Release Cut | v1.9 | 0/TBD | Not started | - |
