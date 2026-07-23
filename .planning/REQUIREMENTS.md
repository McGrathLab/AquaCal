# Requirements: AquaCal v1.9 Publication Prep

**Defined:** 2026-07-23
**Core Value:** Accurate refractive camera calibration from standard ChArUco board observations — researchers can `pip install aquacal`, point it at their videos, and get a calibration result they trust.

**Driver:** The AquaCal SoftwareX paper is in minor revision; the revised manuscript is due
**2026-08-21**. Several reviewer responses (R1.2, R1.5, R2, R3.2, R4.2, R4.3) depend on
library capabilities that do not exist yet. This milestone gathers all remaining *code-side*
work into one sweep so the revision experiments run against a stable library.

**Source documents:** `aquacal-post-review-milestone.md` (task groups A–F),
`aquacal-docs-accuracy-fixes.md` (line-level documentation findings).

**Guiding constraint:** the paper describes the library as it will be at submission. Every
feature added here needs a documentation entry, or it becomes another paper/code divergence
like the ones this milestone exists to close.

## v1 Requirements

Requirements for this milestone. Each maps to exactly one roadmap phase.

### Benchmark Instrumentation

Answers R1.5, R3.2, and the cost half of R1.2. Per-stage wall-clock timing already exists
(`_time_stage`, `pipeline.py:582`); this group extends and exposes it rather than building
it from scratch.

- [ ] **BENCH-01**: Solver diagnostics (`nfev`, `njev`, final `cost`, `optimality`, `status`, termination message) are captured from every `least_squares` call — Stage 3, the intrinsic pass, interface estimation, and point refinement — instead of only `result.status`
- [ ] **BENCH-02**: Peak memory per stage is captured behind an opt-in flag, with the measurement mode recorded alongside the number; never enabled by default, because `tracemalloc` distorts the timings being measured
- [ ] **BENCH-03**: Each run records parameter count *P*, column-group count, and the implied FD evaluation reduction, measured from the live run rather than a separate script
- [ ] **BENCH-04**: Every calibration run writes a machine-readable `benchmark.json` into `output_dir` carrying problem shape, per-stage metrics, solver configuration in force (tolerances, `max_nfev`, robust loss and scale, `refine_intrinsics`, `interface_normal_fixed`), accuracy, and environment (CPU, RAM, OS, Python/NumPy/SciPy versions, AquaCal version and git SHA) — for real-rig runs as well as synthetic
- [ ] **BENCH-05**: A `benchmarks/` runner sweeps the cameras × frames grid, collects each `benchmark.json`, and emits a tidy CSV plus a LaTeX table fragment, computing nothing the pipeline did not record

### Experiment Hooks

WP5/WP6 enablement. Everything here is visibility and persistence — **no change to
numerical behavior**.

- [x] **HOOK-01**: Each pipeline stage's intermediate calibration (post-Stage-2 init, post-Stage-3, post-intrinsic-refinement) can be dumped to the output dir, extending the existing `calibration_initial.json` pattern
- [x] **HOOK-02**: An opt-in per-iteration trace for the bundle-adjustment stages records iteration index, cost, step norm, optimality, and the current interface parameters, persisted to the run's output dir
- [x] **HOOK-03**: Conditioning diagnostics are available at solution — the Jacobian's singular-value spectrum or condition number, plus the approximate parameter correlation matrix or at minimum the camera-height ↔ interface-distance block
- [ ] **HOOK-04**: Held-out evaluation is callable standalone, so a calibration can be scored against a set generated under different assumptions (WP4 needs to calibrate at n=1.333 and evaluate against ground truth generated at a different n)
- [x] **HOOK-05**: The synthetic generator is audited against the WP5 sweep list — refractive index, layout, and tank-scale/working-distance independently controllable — and returns ground-truth board poses and the true interface height alongside detections, so sweeps can compute absolute error
- [x] **HOOK-06**: Every sweep entry point accepts a seed and threads it through, so a surprising result is reproducible

### Refractive Index Helper

WP4 secondary deliverable. Deliberately kept out of the calibration path — no config-schema
integration; the user transfers the estimate to their config by hand.

- [ ] **INDEX-01**: `water_refractive_index(temperature_c, salinity_g_per_l, wavelength_nm, ...)` is a pure function with no I/O or pipeline dependency, using a published empirical formulation cited in its docstring, with the validity envelope documented and out-of-envelope inputs rejected or warned
- [ ] **INDEX-02**: `aquacal calc-index` CLI subcommand prints the estimated index, the inputs that produced it, and the config key (`n_water`) to paste it into, in greppable form
- [ ] **INDEX-03**: Tests cover known reference values (distilled water at 20 °C ≈ 1.333), monotonicity in temperature and in salinity, and rejection of out-of-envelope inputs

### Per-Camera Interface Mode

Enables the WP6 ablation answering R4.2 and feeding R4.3. The forward model is already
per-camera (`Interface.camera_distances` is a `dict[str, float]`), so this is an *optimizer*
change — the geometry code learns nothing new.

- [ ] **IFACE-01**: A `shared_interface: bool = True` config flag exists, documented as an analysis/ablation option rather than a recommended setting
- [ ] **IFACE-02**: `pack_params`, `unpack_params`, `build_jacobian_sparsity`, and `build_bounds` handle *N* per-camera `water_z` parameters when `shared_interface=False`, with the formerly-dense `water_z` column becoming N sparse columns
- [ ] **IFACE-03**: `build_structural_column_groups` produces a valid grouping in every mode combination — shared/per-camera × intrinsics on/off × tilt on/off — asserted by test, because an invalid grouping yields a wrong Jacobian with no error raised
- [ ] **IFACE-04**: Per-camera mode seeds from the per-camera `initial_water_z` dict values individually rather than collapsing them to a mean
- [ ] **IFACE-05**: `shared_interface=True` is bit-unchanged from current behavior, and per-camera mode with equal initial values recovers the shared solution on shared-interface ground truth

### Documentation Reconciliation

A correction pass bringing the docs in line with the paper's formulation, not an expansion.
DOCS-04 and DOCS-05 are the exception — they cover features with no existing text.

- [ ] **DOCS-01**: `docs/guide/optimizer.md` column-grouping numbers are corrected — group count is 13 (17 with intrinsic refinement) and constant in rig size, *P* is 673/675/727 not "~630", and the reduction is 43–52× not "~12×"
- [ ] **DOCS-02**: BFS → best-first terminology is corrected across five doc sites and four `extrinsics.py` docstring sites, leaving `_find_connected_components` (genuinely BFS) untouched, and the two comments describing unimplemented scoring are fixed
- [ ] **DOCS-03**: The glossary's pose-graph definition is corrected to a bipartite camera/frame graph, and `bfs_pose_graph.png` is replaced with the corrected figure whose generator replays the library's own heap logic
- [ ] **DOCS-04**: v1.7–v1.8 features (`reject_outlier_frames`, `detection.start_frame`/`stop_frame`, intrinsics seeding, fronto-parallel warning) are documented in the configuration reference and relevant guide pages, not only in troubleshooting
- [ ] **DOCS-05**: Everything this milestone adds is documented — `calc-index`, the `benchmark.json` schema, the trace and conditioning flags, and `shared_interface` framed as an ablation option
- [ ] **DOCS-06**: Docs **and code surfaces** present the paper's three-stage model — console output, timing keys, `benchmark.json` keys, module and schema docstrings, and CLI config comments — and the documented loss default is corrected from soft-L1 to `huber`
- [ ] **DOCS-07**: A release is cut and the manuscript's C1 metadata cell and the Zenodo archive reference are updated to the version the published artifacts actually reflect

### Dataset and Tutorial Refresh

The published dataset and tutorial outputs are frozen at 2026-02, two feature releases
behind. Nothing re-executes the notebooks automatically (`nbsphinx_execute = "never"`), so
this cannot be an assumed side effect.

- [ ] **DATA-01**: The real-rig dataset config is regenerated through current `aquacal init` (not hand-patched), with every difference from the shipped config confirmed deliberate, settling whether the shipped `initial_distances` was a scalar or carried pre-v1.4 physical-gap semantics
- [ ] **DATA-02**: A new Zenodo version is published and `manifest.json`'s `zenodo_record_id`, `checksum`, and `size_bytes` are updated together, with `load_example("real-rig")` verified to download, checksum, and extract at the path the notebook resolves
- [ ] **DATA-03**: Both tutorial notebooks are re-executed with fresh committed outputs, and any narration the outputs contradict is updated — including the three-stage framing and the runtime estimate

## Sequencing Constraints

Not requirements, but binding on the roadmap:

1. **DOCS-06 must precede BENCH-04.** The stage rename touches the timing keys that
   `benchmark.json` will carry. Settling the schema after the experiments run means
   re-running the grid.
2. **IFACE-03 is coordinated with the shipped structural grouping.** This is the one place
   a silent-wrong-answer bug can enter — an invalid grouping produces an incorrect Jacobian
   without raising.
3. **DOCS-01 should land early** regardless of phase ordering. It is a live factual error in
   currently published documentation, understating the optimization by ~4× and contradicting
   the paper supplement.
4. **DATA-* runs after all code work and after DOCS-06**, and **before DOCS-07**, so the
   release named in the manuscript is the one whose behavior the published artifacts reflect.
5. **HOOK-03 (conditioning diagnostics) precedes IFACE.** The Hooks → Per-Camera Interface
   chain is the milestone's longest pole and only true experiment blocker, so it is
   sequenced first in the roadmap — ahead of the documentation and benchmark phases,
   which are otherwise independent of it.

## Future Requirements

Deferred. Tracked but not in this roadmap.

### Performance

- **PERF-01**: Reduce peak memory during Stage 3 (dense `.toarray()` Jacobian, ~3.6 GB on the 13-camera rig) — this milestone measures and reports it only
- **PERF-02**: Analytic Jacobian for refractive projection, removing FD evaluation cost entirely

### Cleanup

- **CLEAN-01**: Retire the `initial_distances` compatibility shim in `pipeline.py` — unblocked by DATA-02, but still a breaking change for users with pre-v1.4 configs

## Out of Scope

| Feature | Reason |
|---------|--------|
| Running the WP5/WP6 experiments | This milestone builds the tooling; execution happens separately against the stabilized library |
| Manuscript prose and figures | Written outside the repo; this milestone only ensures the code matches what the prose will claim |
| Structural FD column grouping | Already shipped (quick task 3, `3c8685c`) — do not redo |
| Reducing peak memory | The dense `.toarray()` trades memory for solver stability; `jac_sparsity` forces LSMR, observed to diverge here. Too risky before 2026-08-21 |
| `n_water` config-schema integration for the index helper | Deliberate — the helper stays out of the calibration path, printing an estimate the user transfers by hand |
| Presenting per-camera interface as a recommended mode | The paper's central claim is that the shared parameter is the correct model |

## Traceability

Which phases cover which requirements. Populated during roadmap creation.

| Requirement | Phase | Status |
|-------------|-------|--------|
| HOOK-01 | Phase 16 | Complete |
| HOOK-02 | Phase 16 | Complete |
| HOOK-03 | Phase 16 | Complete |
| HOOK-04 | Phase 16 | Pending |
| HOOK-05 | Phase 16 | Complete |
| HOOK-06 | Phase 16 | Complete |
| IFACE-01 | Phase 17 | Pending |
| IFACE-02 | Phase 17 | Pending |
| IFACE-03 | Phase 17 | Pending |
| IFACE-04 | Phase 17 | Pending |
| IFACE-05 | Phase 17 | Pending |
| DOCS-01 | Phase 18 | Pending |
| DOCS-02 | Phase 18 | Pending |
| DOCS-03 | Phase 18 | Pending |
| DOCS-04 | Phase 18 | Pending |
| DOCS-06 | Phase 18 | Pending |
| BENCH-01 | Phase 19 | Pending |
| BENCH-02 | Phase 19 | Pending |
| BENCH-03 | Phase 19 | Pending |
| BENCH-04 | Phase 19 | Pending |
| BENCH-05 | Phase 19 | Pending |
| INDEX-01 | Phase 20 | Pending |
| INDEX-02 | Phase 20 | Pending |
| INDEX-03 | Phase 20 | Pending |
| DOCS-05 | Phase 21 | Pending |
| DATA-01 | Phase 21 | Pending |
| DATA-02 | Phase 21 | Pending |
| DATA-03 | Phase 21 | Pending |
| DOCS-07 | Phase 22 | Pending |

**Coverage:**
- v1 requirements: 29 total
- Mapped to phases: 29
- Unmapped: 0 ✓

---
*Requirements defined: 2026-07-23*
*Last updated: 2026-07-23 after roadmap revision — reordered phases so the Hooks →
Per-Camera Interface experiment-blocking chain runs first (phases 16-17), ahead of docs
reconciliation and benchmark instrumentation (phases 18-19); coverage still 29/29*
