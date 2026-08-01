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

- [x] **BENCH-01**: Solver diagnostics (`nfev`, `njev`, final `cost`, `optimality`, `status`, termination message) are captured from every `least_squares` call — Stage 3, the intrinsic pass, interface estimation, and point refinement — instead of only `result.status`
- [x] **BENCH-02**: Peak memory per stage is captured behind an opt-in flag, with the measurement mode recorded alongside the number; never enabled by default, because `tracemalloc` distorts the timings being measured
- [x] **BENCH-03**: Each run records parameter count *P*, column-group count, and the implied FD evaluation reduction, measured from the live run rather than a separate script
- [x] **BENCH-04**: Every calibration run writes a machine-readable `benchmark.json` into `output_dir` carrying problem shape, per-stage metrics, solver configuration in force (tolerances, `max_nfev`, robust loss and scale, `refine_intrinsics`, `interface_normal_fixed`), accuracy, and environment (CPU, RAM, OS, Python/NumPy/SciPy versions, AquaCal version and git SHA) — for real-rig runs as well as synthetic
- [x] **BENCH-05**: A runner sweeps the cameras × frames grid, collects each `benchmark.json`, and emits a tidy CSV plus a LaTeX table fragment, computing nothing the pipeline did not record — delivered 2026-07-24 as `benchmarks/sweep_runner.py` + `benchmarks/aggregate.py`, relocated under `experiments/` by EXP-03 so the suite has one directory and one README (scope transfer, not a correction: the capability shipped and was verified in Phase 19; `sweep_runner.py` was never executed against a real calibration there, which is why the relocation is cheap)
- [x] **BENCH-06**: Stage 3 and Stage 4 pass `ftol`, `xtol`, and `gtol` to `least_squares` explicitly at their current effective values, and `max_nfev` is recorded with its effective value including the unset/auto case — so the termination criteria the paper supplement states, and that R3.2 asks for by name, are set and reported by AquaCal rather than inherited from SciPy; behavior must be bit-unchanged, asserted by regression test

### Experiment Hooks

WP5/WP6 enablement. Everything here is visibility and persistence — **no change to
numerical behavior**.

- [x] **HOOK-01**: Each pipeline stage's intermediate calibration (post-Stage-2 init, post-Stage-3, post-intrinsic-refinement) can be dumped to the output dir, extending the existing `calibration_initial.json` pattern
- [x] **HOOK-02**: An opt-in per-iteration trace for the bundle-adjustment stages records iteration index, cost, step norm, optimality, and the current interface parameters, persisted to the run's output dir
- [x] **HOOK-03**: Conditioning diagnostics are available at solution — the Jacobian's singular-value spectrum or condition number, plus the approximate parameter correlation matrix or at minimum the camera-height ↔ interface-distance block
- [x] **HOOK-04**: Held-out evaluation is callable standalone, so a calibration can be scored against a set generated under different assumptions (WP4 needs to calibrate at n=1.333 and evaluate against ground truth generated at a different n)
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

- [x] **IFACE-01**: A `shared_interface: bool = True` config flag exists, documented as an analysis/ablation option rather than a recommended setting
- [x] **IFACE-02**: `pack_params`, `unpack_params`, `build_jacobian_sparsity`, and `build_bounds` handle *N* per-camera `water_z` parameters when `shared_interface=False`, with the formerly-dense `water_z` column becoming N sparse columns
- [x] **IFACE-03**: `build_structural_column_groups` produces a valid grouping in every mode combination — shared/per-camera × intrinsics on/off × tilt on/off — asserted by test, because an invalid grouping yields a wrong Jacobian with no error raised
- [x] **IFACE-04**: Per-camera mode seeds from the per-camera `initial_water_z` dict values individually rather than collapsing them to a mean
- [x] **IFACE-05**: `shared_interface=True` is bit-unchanged from current behavior, and per-camera mode with equal initial values recovers the shared solution on shared-interface ground truth

### Documentation Reconciliation

A correction pass bringing the docs in line with the paper's formulation, not an expansion.
DOCS-04 and DOCS-05 are the exception — they cover features with no existing text.

- [x] **DOCS-01**: `docs/guide/optimizer.md` column-grouping numbers are corrected — group count is 13 (17 with intrinsic refinement) and constant in rig size, *P* is 673/675/727 not "~630", and the reduction is 43–52× not "~12×"
- [x] **DOCS-02**: BFS → best-first terminology is corrected across five doc sites and four `extrinsics.py` docstring sites, leaving `_find_connected_components` (genuinely BFS) untouched, and the two comments describing unimplemented scoring are fixed
- [x] **DOCS-03**: The glossary's pose-graph definition is corrected to a bipartite camera/frame graph, and `bfs_pose_graph.png` is replaced with the corrected figure whose generator replays the library's own heap logic
- [x] **DOCS-04**: v1.7–v1.8 features (`reject_outlier_frames`, `detection.start_frame`/`stop_frame`, intrinsics seeding, fronto-parallel warning) are documented in the configuration reference and relevant guide pages, not only in troubleshooting
- [ ] **DOCS-05**: Everything this milestone adds is documented — `calc-index`, the `benchmark.json` schema, the trace and conditioning flags, and `shared_interface` framed as an ablation option
- [x] **DOCS-06**: Docs **and code surfaces** present the paper's three-stage model — console output, timing keys, `benchmark.json` keys, module and schema docstrings, and CLI config comments — and the documented loss default is corrected from soft-L1 to `huber`
- [ ] **DOCS-07**: A release is cut and the manuscript's C1 metadata cell and the Zenodo archive reference are updated to the version the published artifacts actually reflect

### Dataset and Tutorial Refresh

The published dataset and tutorial outputs are frozen at 2026-02, two feature releases
behind. Nothing re-executes the notebooks automatically (`nbsphinx_execute = "never"`), so
this cannot be an assumed side effect.

- [ ] **DATA-01**: The real-rig dataset config is regenerated through current `aquacal init` (not hand-patched), with every difference from the shipped config confirmed deliberate, settling whether the shipped `initial_distances` was a scalar or carried pre-v1.4 physical-gap semantics
- [ ] **DATA-01a** *(added 2026-07-27, Phase 19.1 finding — PUBLICATION BLOCKER)*: The regenerated archive contains **the same frameset that produced the manuscript's §3 numbers**, not the ~4.3× subsampled extraction currently published. The shipped archive yields 60 usable frames → 12 validation → 1,817 comparisons; §3 comes from `Desktop\Aqua\AquaCal\release_calibration` at `frame_step: 30` / `max_calibration_frames: 200`, yielding ~260 usable → 52 validation → **7,762 comparisons**. Acceptance: a fresh `load_example("real-rig")` run reproduces `diagnostics.json`'s `reconstruction.num_comparisons = 7762` and the other eight §3 quantities within tolerance. Source videos are on disk at `Desktop\Aqua\AquaCal\raw_videos\{intrinsics,extrinsics}\*.avi` (13 + 13) with the producing config at `release_calibration\config.yaml`. Full analysis: `.planning/phases/19.1-experiment-suite-consolidation/19.1-E2-FRAMESET-PROVENANCE.md`.
- [ ] **DATA-01b** *(added 2026-07-27, Phase 19.1 finding)*: The regenerated archive carries the run's **reference outputs** alongside its inputs, so it is self-contained: `calibration.json` (2.1 MB), `reprojection_residuals.csv` (1.2 MB), `reconstruction_errors.csv` (0.6 MB), and the regenerable `exp2_spatial_errors.csv` / `interface_ablation_conditioning.npz`. These move OUT of `experiments/results/` in git. Rationale: split artifacts by function, not size — `--check` baselines and offline CI need only ~20 KB of small CSVs (`camera_parameters.csv`, `exp{1,2,3}`, `interface_ablation.csv`), which stay versioned; nothing reads `calibration.json` programmatically, and the figures repo keeps its own copies of the residual/reconstruction CSVs. **Acceptance: after this lands, the `exclude: ^experiments/results/` on `check-added-large-files` in `.pre-commit-config.yaml` is REMOVED and the 1000 KB guard passes repo-wide.** `experiments/results/` should fall from 4.1 MB to ~0.7 MB.
- [ ] **DATA-02**: A new Zenodo version is published and `manifest.json`'s `zenodo_record_id`, `checksum`, and `size_bytes` are updated together, with `load_example("real-rig")` verified to download, checksum, and extract at the path the notebook resolves
- [ ] **DATA-03**: Both tutorial notebooks are re-executed with fresh committed outputs, and any narration the outputs contradict is updated — including the three-stage framing and the runtime estimate

### Experiment Suite

Added 2026-07-25 with the insertion of Phases 19.1 and 19.2. Source:
`aquacal-experiment-suite.md` (copied into both phase directories as `*-SOURCE-BRIEF.md`).
Every quantitative claim in the manuscript and supplement must trace to one committed
script, one committed output file, and one figure generator. The paper has already been
bitten twice by hand-carried numbers — provenance is the deliverable here, not just results.

Phase 19.1 (consolidation + the two risk-carrying runs):

- [x] **EXP-01**: `calibrate_synthetic`, `compute_per_camera_errors`, and `evaluate_reconstruction` are importable from the installed package as `aquacal.datasets.pipelines` (with `tests/synthetic/experiment_helpers.py` left as a re-export shim), and `aquacal.datasets.__all__` also exports `generate_camera_array`, `generate_real_rig_array`, and `generate_board_trajectory` — so a pip-installed reader can run the tutorial and every script uses the public API a user would write
- [x] **EXP-02**: An `experiments/` directory outside `src/` holds `_io.py` (paths, sidecar, CSV writing, CLI parsing — I/O only), `_render.py` (CSV → LaTeX, recomputing nothing), and `results/`, with a README mapping one command to each paper artifact and its expected runtime; every script honours `--seed`, `--out`, `--force`, `--smoke`, `--check`, and `--smoke` runs in CI
- [x] **EXP-03**: `tests/synthetic/experiments.py` is deleted with its unique content salvaged, `compare_refractive.py` has moved to `experiments/` as E1's CLI entry point, the Phase 19 `benchmarks/` runner has moved under `experiments/`, stale path references are swept (`.planning/architecture.md`, `.planning/codebase/STRUCTURE.md`, `.planning/codebase/CONCERNS.md:21-34`), and no two implementations of the same experiment remain
- [x] **EXP-04**: E2's real-rig re-run against the current library emits `real_rig_metrics.json` and a `benchmark.json`, and every §3 real-rig number is confirmed unchanged or recorded as moved — the committed run predates v1.7 outlier rejection and v1.8 intrinsics seeding entirely
- [x] **EXP-05**: E7 reports per-camera surface-height spread, camera-height drift, focal/standoff drift and correlation, and the conditioning report across all four `shared_interface` × `refine_intrinsics` configurations on identical data, with reprojection RMSE explicitly not the headline metric (a degeneracy is a flat valley — RMSE stays low in both arms)
- [x] **EXP-06**: The ported E1 reproduces every value in the committed `exp{1,2,3}` CSVs or explains each divergence, keeping the notebook's long-format schema, and the gauge-freedom mean-shift correction (mean Z error across free cameras, subtracted before export) survives the port with an explanation attached

Phase 19.2 (the remaining new results and the provenance close-out):

- [x] **EXP-07**: E3 emits `code_constants.csv` (declared vs source value with pass/fail), `newton_iterations.csv`, and `cpr_grouping.csv` covering the six existing `tab:cpr` rows plus per-camera-mode rows, validating the *P* formula against live `pack_params` length; tier 1's constants are also asserted in the test suite so CI breaks when a default changes
- [x] **EXP-08**: E4 runs the cameras {8,12,16} × frames {50,100,200} grid plus E2's real rig as a tenth point, all on one machine, reporting only what `benchmark.json` recorded
- [x] **EXP-09**: E5 sweeps `n_assumed` in a fine band around 1.333 on the real rig's geometry and reports depth/scale bias and held-out RMSE against Δn, showing the bias moves while the reprojection residual does not
- [x] **EXP-10**: E6 sweeps refractive index (1.33→1.55), layout (grid/ring/line), and scale one axis at a time through a common baseline, emitting tidy long-format rows carrying which axis varied
- [x] **EXP-11**: Every committed result across E1–E7 carries its seed, AquaCal version, git SHA, and environment — reusing `benchmark.json` rather than hand-rolling a sidecar, with a minimal sidecar for E3's tiers 1–2 which never run a calibration — and `experiments/README.md`'s provenance table maps every paper artifact to its script, data file, and figure generator

**Deliberately not requirements here.** X4 (demoting notebook 02 to `RIG_SIZE="small"`) is
Phase 21 work, landing with the tutorial re-execution under DATA-03. X5 (the three new figure
modules for E5/E6/E7) lives in the separate `DissertationFigures` repository, so no AquaCal
phase can satisfy it — it is a downstream handoff, tracked in the phase context, not a
success criterion.

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
5. **BENCH-06 must precede BENCH-04.** `OptimizeResult` does not report the termination
   tolerances back, so `benchmark.json` can only record values the caller passed. Until
   Stage 3 and Stage 4 set them explicitly, the "solver configuration in force" block is
   inferred from SciPy's defaults rather than observed. Verified 2026-07-24: neither stage
   sets them — `interface_estimation.py:337-348` and `refinement.py:237-248` pass only
   `method`, `loss`, `f_scale`, `bounds`, `jac`, `verbose`, and `**ls_kwargs`, and
   `ls_kwargs` carries only `callback`.
6. **HOOK-03 (conditioning diagnostics) precedes IFACE.** The Hooks → Per-Camera Interface
   chain is the milestone's longest pole and only true experiment blocker, so it is
   sequenced first in the roadmap — ahead of the documentation and benchmark phases,
   which are otherwise independent of it.
7. **EXP-01 precedes every other EXP requirement.** Every experiment script imports the
   promoted verbs and the widened generator surface; nothing in the suite can start first.
   Verified 2026-07-25: `src/aquacal/datasets/pipelines.py` does not exist and
   `datasets.__all__` still exports only `create_scenario`,
   `generate_synthetic_detections`, and `SyntheticScenario`.
8. **EXP-04 (E2) runs before the rest of the suite.** Two feature releases landed since the
   committed real-rig run, so §3's real-rig paragraph is the most likely place the revision
   springs a leak — and fixing it is a prose edit under a word limit already at ~3,916 of
   4,000. Twenty minutes of compute buys the earliest possible warning.
9. **EXP-04 precedes EXP-08.** E4's tenth grid point is E2's real rig, and it reuses E2's
   `benchmark.json` so the wall-clock and hardware spec come from one record.
10. **The `benchmark.json` schema is settled and must not be revisited.** It locked in
    Phase 19; changing it after the E4 grid runs means re-running the grid.
11. **One machine for the whole E4 grid.** A grid split across machines is not a scaling
    curve. Which machine's spec goes in the paper is an open input, needed by 19.2 and not
    before.

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
| HOOK-04 | Phase 16 | Complete |
| HOOK-05 | Phase 16 | Complete |
| HOOK-06 | Phase 16 | Complete |
| IFACE-01 | Phase 17 | Complete |
| IFACE-02 | Phase 17 | Complete |
| IFACE-03 | Phase 17 | Complete |
| IFACE-04 | Phase 17 | Complete |
| IFACE-05 | Phase 17 | Complete |
| DOCS-01 | Phase 18 | Complete |
| DOCS-02 | Phase 18 | Complete |
| DOCS-03 | Phase 18 | Complete |
| DOCS-04 | Phase 18 | Complete |
| DOCS-06 | Phase 18 | Complete |
| BENCH-01 | Phase 19 | Complete |
| BENCH-02 | Phase 19 | Complete |
| BENCH-03 | Phase 19 | Complete |
| BENCH-04 | Phase 19 | Complete |
| BENCH-05 | Phase 19 | Complete |
| BENCH-06 | Phase 19 | Complete |
| EXP-01 | Phase 19.1 | Complete |
| EXP-02 | Phase 19.1 | Complete |
| EXP-03 | Phase 19.1 | Complete |
| EXP-04 | Phase 19.1 | Complete |
| EXP-05 | Phase 19.1 | Complete |
| EXP-06 | Phase 19.1 | Complete |
| EXP-07 | Phase 19.2 | Complete |
| EXP-08 | Phase 19.2 | Complete |
| EXP-09 | Phase 19.2 | Complete |
| EXP-10 | Phase 19.2 | Complete |
| EXP-11 | Phase 19.2 | Complete |
| INDEX-01 | Phase 20 | Pending |
| INDEX-02 | Phase 20 | Pending |
| INDEX-03 | Phase 20 | Pending |
| DOCS-05 | Phase 21 | Pending |
| DATA-01 | Phase 21 | Pending |
| DATA-01a | Phase 21 | Pending |
| DATA-01b | Phase 21 | Pending |
| DATA-02 | Phase 21 | Pending |
| DATA-03 | Phase 21 | Pending |
| DOCS-07 | Phase 22 | Pending |

**Coverage:**
- v1 requirements: 40 total
- Mapped to phases: 40
- Unmapped: 0 ✓

---
*Requirements defined: 2026-07-23*
*Updated 2026-07-23 after roadmap revision — reordered phases so the Hooks → Per-Camera
Interface experiment-blocking chain runs first (phases 16-17), ahead of docs reconciliation
and benchmark instrumentation (phases 18-19); coverage 29/29*
*Last updated: 2026-07-25 — inserted Phases 19.1 and 19.2 from `aquacal-experiment-suite.md`,
adding EXP-01..11 (29 → 40) and sequencing constraints 7-11. BENCH-05's wording generalized
off the `benchmarks/` directory name: the capability shipped and was verified in Phase 19,
and EXP-03 relocates the runner under `experiments/` as a scope transfer, not a correction.
X4 (notebook demotion) stays Phase 21 work under DATA-03; X5 (figure modules) is out of
scope for any AquaCal phase — it lives in the DissertationFigures repository.*
