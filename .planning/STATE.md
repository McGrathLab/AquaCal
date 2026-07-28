---
gsd_state_version: 1.0
milestone: v1.9
milestone_name: Publication Prep
status: executing
stopped_at: "Phase 19.2: D-26 replan COMPLETE -- 14 plans in 8 waves, ready to execute"
last_updated: "2026-07-28T21:26:12.628Z"
last_activity: 2026-07-28 -- Phase 19.2 planning complete
progress:
  total_phases: 9
  completed_phases: 5
  total_plans: 48
  completed_plans: 34
  percent: 56
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-07-23)

**Core value:** Accurate refractive camera calibration from standard ChArUco board observations — researchers can pip install aquacal, point it at their videos, and get a calibration result they trust.
**Current focus:** Phase 19.2 — experiment execution and provenance

## Current Position

Phase: 19.2
  **D-26 replan complete 2026-07-28: 14 plans in 8 waves, 0/14 executed.**
  Wave 1 = 19.2-01/02/03/04/14 (every src change, each exact-equality guarded).
  Plan 19.2-06 (the ~50 min E2 re-run) moved to wave 2; its launch gate is now
  "every src change passes its bit-identity test", not "git diff -- src/ is empty".
  New plan 19.2-14 adds seed to pipeline.py solver_config (EXP-11).
  Plan 19.2-05 gained a depends_on edge to 19.2-06. Production runs are serialized
  one per wave: 06 (w2), 09 (w5), 13 (w6), 11 (w7).
  Phases 16, 17, 18, 19, and 19.1 COMPLETE, verification PASSED.
Plan: Not started
  **Plan 19.1-08 is a blocking human gate (`autonomous: false`)** on E2's real-rig delta table —
  it must not be self-approved. `workflow.auto_advance` was set false on 2026-07-25 so the
  discuss→plan chain stopped before execute at the user's explicit request; restore it with
  `gsd-sdk query config-set workflow.auto_advance true` if you want chaining back.
Status: Ready to execute
  Phase 19 closed 2026-07-24: 6/6 plans across 4 waves, verifier scored 6/6 after a
  gap-closure round. The gates earned their keep — verifier caught a BENCH-04 key-mismatch
  (stage3.seconds always null) and code review caught a false "no least_squares" label
  (CR-01); both fixed in `5e246b1` with regression tests. 846 tests pass.
Last activity: 2026-07-28 -- Phase 19.2 planning complete
  Before that, Phase 18 closed 2026-07-24 (8/8, verified 5/5).
Unreleased on main: everything from Phases 16-19 plus quick task 3's `perf:` commit.
  Nothing is pushed yet — the next push to `main` will trigger python-semantic-release
  and cut a version. 22 `feat:` commits are present, so expect a minor bump to v1.9.0.
  Note: `34497f9 fix(18):` is a mistyped docstring-only repair that should have been
  `docs(18):`. It does NOT change the version (feat: already forces minor) but will add a
  misleading line to the CHANGELOG's Bug Fixes section. Left unrewritten pending user
  decision — rewriting it means rebasing through merge commits.

Milestone v1.6 Refinement API: COMPLETE (shipped 2026-03-09), phases 13-15.
v1.7–v1.8 shipped outside the milestone framework (see MILESTONES.md).
v1.9 phase numbering continues from **16** and spans **16-22** (7 phases).

v1.9 phase structure (revised order — experiment blocker first):

- ✅ Phase 16: Experiment Observability Hooks (HOOK-01..06) — COMPLETE 2026-07-23
- ✅ Phase 17: Per-Camera Interface Ablation Mode (IFACE-01..05) — COMPLETE 2026-07-23.
  Depended on Phase 16 (HOOK-03 conditioning diagnostics as the WP6 metric). Phases 16-17
  together were the milestone's longest pole and only true experiment blocker; sequenced
  first so WP5/WP6 experiments could start as early as possible against the deadline.
  **That chain is now closed — experiment execution is no longer gated on library work.**

- Phase 18: Documentation Corrections & Stage-Model Reconciliation (DOCS-01,02,03,04,06)
  — no dependency, independent of 16-17, may run in parallel. DOCS-01 (live ~12x vs
  43-52x error) can and should be fixed at any point regardless of scheduling.

- Phase 19: Benchmark Instrumentation (BENCH-01..05) — depends on Phase 18 (DOCS-06
  settles the stage-key schema before benchmark.json locks it in; this constraint is
  preserved from the original roadmap and still binding)

- Phase 20: Refractive Index Helper (INDEX-01..03) — fully standalone
- Phase 21: New-Feature Documentation & Dataset Refresh (DOCS-05, DATA-01,02,03) —
  depends on 16-20

- Phase 22: Release Cut (DOCS-07) — depends on Phase 21

**Hard deadline:** revised SoftwareX manuscript due 2026-08-21. This milestone builds
the tooling only — experiment execution (WP5/WP6) and manuscript prose happen separately,
so the code work must land with room to spare. The Hooks → Per-Camera Interface chain
(phases 16-17) is the true blocker for that experiment execution, hence sequenced first.

## Accumulated Context

### Roadmap Evolution

- Phase 19.1 inserted after Phase 19: Experiment Suite Consolidation — X1/X2/X3/X6 plus E2, E7, and E1 (EXP-01..06) from the desktop brief; every manuscript number traces to one script/output/figure (URGENT). Rescoped the same day when the phase was split; the execution half became 19.2.
- Phase 19.2 inserted after Phase 19.1: Experiment Execution and Provenance — E3/E4/E5/E6 + provenance close-out (EXP-07..11), split out of the original 19.1 along the source brief's wave 3/wave 4 boundary so E2's real-rig re-run is a phase gate rather than one item among eleven (URGENT)

### Decisions

Decisions are logged in PROJECT.md Key Decisions table.
Key v1.6 decisions:

- Refinement API accepts abstract float weights — caller defines "goodness"
- No CLI command for refinement — library API only
- Local _pack/_unpack in point_refinement.py (separate from board-pose _optim_common)
- Parameterized extensions on single function (refine_intrinsics, loss, normal_fixed)
- Any-fail accept/reject logic — conservative validation

Key v1.9 roadmap decisions:

- Reordered so Phase 16 (Hooks) and Phase 17 (Per-Camera Interface) run first — this
  chain is the only true experiment blocker (WP5/WP6), and the deadline requires
  experiments to start as early in the milestone as possible

- HOOK-03 (conditioning diagnostics) treated as a hard prerequisite for Phase 17 (IFACE),
  not a convenience — it's the only metric for the WP6 degeneracy argument

- Docs reconciliation (Phase 18, was 16) and Benchmark Instrumentation (Phase 19, was 17)
  moved after the experiment-blocker chain; DOCS-06 → BENCH-04 ordering constraint
  preserved (now Phase 18 → Phase 19)

- DOCS-01 (the ~12x vs 43-52x error) called out as fixable at any point independent of
  phase scheduling, even though it's formally grouped into Phase 18

- DOCS-05 and DATA-01/02/03 merged into one phase (21) — both need every other code
  phase finished first, so splitting them added a phase without adding sequencing value

- DOCS-07 (release cut) kept as its own single-requirement final phase — it's a capstone
  step, not incoherent with anything else

- [Phase 16]: HOOK-06 gap closure: config.seed now threaded into split_detections and recorded in CalibrationMetadata (backward-compatible via .get); config_hash distinguishes seed-only differences

Key v1.9 Phase 17 decisions:

- Every packing/structure function takes a trailing `shared_interface: bool = True` kwarg;
  the `True` branch is the untouched historical path, locked by exact-equality tests

- N per-camera `water_z` columns collapse into the *single* `water_z` FD group slot (two
  cameras' water_z columns never share a residual row), so the structural group count stays
  13 / 17-with-intrinsics — unchanged from shared mode

- The `initial_water_z` "must cover all cameras" hard-fail is gated on `shared_interface`
  in both dict branches, so a partial dict survives to the per-camera seed resolver

- Per-camera seeding is always individual (`water_z_per_camera`), never collapsed to a mean
  or to the reference camera (IFACE-04)

- The ablation headline number (per-camera water_z spread) is unconditional in per-camera
  mode: mm to console, meters to `internals/interface_spread.json`, no gating flag

- Per-camera tilt / interface normal explicitly out of scope — only `water_z` goes per-camera
- Full new-feature documentation for `shared_interface` (worked example, WP6 interpretation)
  deferred to Phase 21; Phase 17 shipped only an ablation-framed stub

### Pending Todos

Tracked as files in `.planning/todos/pending/` — see `/gsd-capture --list`. Do not
duplicate the list here; the two copies drifted apart between v1.6 and v1.8.

Open as of 2026-07-23:

- Reduce memory and CPU load during calibration (dense `.toarray()` Jacobian peak;
  CPU side partially addressed by quick task 3). **v1.9 measures and reports this
  peak but does not reduce it** — deliberate, see PROJECT.md Key Decisions. Stays open.

- Upload new Zenodo dataset with image-based inputs (confirmed still the 2026-02-14
  upload; serves the deprecated `initial_distances` key, which currently loads fine
  via the compat shim). **Now Phase 21 (DATA-01/02/03)** — do not action standalone;
  it carries a sequencing constraint (after all code phases + DOCS-06, before DOCS-07).
  Close it when Phase 21 lands.

### Blockers/Concerns

None.

### Phase 16 Plan Progress

- Plan 16-01 (Conditioning diagnostics, HOOK-03) — COMPLETE 2026-07-23. Commits
  `cd5dd00` (compute_conditioning core), `67f38b9` (JSON/NPZ writer + exports). Summary:
  `.planning/phases/16-experiment-observability-hooks/16-01-SUMMARY.md`. Added
  `aquacal.validation.conditioning` (blocked tall-skinny QR + single SVD of the (n,n) R
  factor); 12 new unit tests; no regressions (675 passed). `chunk_rows` left at the
  plan-specified default (8192), flagged for re-tuning against a real `result.jac` once
  plan 16-05 wires this into the pipeline.

- Plan 16-02 (Datasets: synthetic sweep-axis support, HOOK-05/HOOK-06) — COMPLETE
  2026-07-23. Commits `85e60c2` (feat), `25cf08a` (test). Summary:
  `.planning/phases/16-experiment-observability-hooks/16-02-SUMMARY.md`.
  Plumbed n_air/n_water through `generate_synthetic_detections`; `SyntheticScenario`
  now records n_air/n_water/seed; added executable sweep-axis audit
  (`tests/unit/test_synthetic_sweep_axes.py`). Zero behavior change to existing
  callers (defaults 1.0/1.333/42 preserved).

- Plan 16-03 (Observability config foundation + Stage-3/rerun/4 calibration dumps) —
  COMPLETE 2026-07-23. Commits `bb523a7` (config fields + YAML parsing + `aquacal init`),
  `afe54e8` (`internals/` directory helper), `ce94111` (`_dump_stage_calibration` + three
  call sites). Summary:
  `.planning/phases/16-experiment-observability-hooks/16-03-SUMMARY.md`. Added
  `CalibrationConfig.save_stage_calibrations/save_optimization_trace/save_conditioning/seed`,
  a new `internals:`/`seed:` YAML surface, `aquacal.io.ensure_internals_dir` +
  `warn_if_overwriting`, and default-on Stage-3/Stage-3-rerun/Stage-4 calibration JSON
  dumps under `output_dir/internals/`. `calibration_initial.json` (post-Stage-2)
  deliberately left untouched. Note: this plan's `requirements` frontmatter listed
  HOOK-02, but only the config *switch* (`save_optimization_trace`) was added here — the
  actual per-iteration trace is plan 16-04's job (`depends_on: ["16-03"]`), so HOOK-02 was
  intentionally left unchecked in REQUIREMENTS.md pending 16-04, not marked complete.
  No regressions: 679 passed (full unit suite), 684 passed/29 deselected
  (`tests/ -m "not slow"`).

- Plan 16-04 (Optimizer observability trace, HOOK-02) — COMPLETE 2026-07-23. Commits
  `048f8ba` (OptimizerObserver + scipy>=1.16 floor), `9928deb` (optional observer param
  on optimize_interface/joint_refinement), `29201f3` (per-stage trace CSVs wired into
  pipeline). Summary:
  `.planning/phases/16-experiment-observability-hooks/16-04-SUMMARY.md`. Added
  `aquacal.calibration._observability.OptimizerObserver`/`TraceRow`, wrapping
  scipy's `least_squares(callback=...)` (new in 1.16) to record per-iteration cost,
  step norm, and an unconstrained `||J^T f||_inf` optimality proxy (documented as
  NOT matching scipy's bound-scaled final optimality). `optimize_interface` and
  `joint_refinement` both gained a trailing `observer=None` param with a verified
  bit-identical-result guarantee when unset. Pipeline writes
  `internals/trace_stage3.csv`, `trace_stage3_rerun.csv`, `trace_stage4.csv` (one
  file per stage, never merged) when `config.save_optimization_trace` is true.
  `on_solution(result)` defined as a no-op extension point for plan 16-05's
  conditioning work. No regressions: 696 passed (full unit suite, +17 new),
  701 passed/29 deselected (`tests/ -m "not slow"`).

- Plan 16-05 (Wire conditioning diagnostics into the pipeline, HOOK-03) —
  COMPLETE 2026-07-23. Commits `ccc61ac` (labelled conditioning inside
  `on_solution`), `f5ea190` (enable on final reported stage, write once).
  Summary: `.planning/phases/16-experiment-observability-hooks/16-05-SUMMARY.md`.
  Added `build_parameter_labels` (mirrors `_optim_common.pack_params`'s layout
  exactly) and gave `OptimizerObserver` a `conditioning` flag: when set,
  `on_solution` calls `compute_conditioning(result.jac, ...)` (built in 16-01)
  while `result` is still in the optimizer function's scope, storing only the
  small `ConditioningReport` and letting `ConditioningMemoryError` propagate
  with the stage name prefixed. Pipeline creates observers when
  `save_optimization_trace OR save_conditioning` is set, enables conditioning
  only on whichever stage produces the final reported result (Stage 4 when
  `refine_intrinsics`, else Stage 3 — initial or the outlier-rejection rerun,
  whichever ran last), and writes exactly one `internals/conditioning.json` +
  `.npz` pair via a new pure `_select_conditioning_report` helper, tagged with
  the producing stage (`save_conditioning_report` gained an additive `stage`
  kwarg). No real 13-camera rig run was performed this session, so no sharper
  peak-memory/runtime figure exists yet for the deferred PERF-01 todo — the
  first `save_conditioning: true` real run will be the first data point.
  No regressions: 712 passed (full unit suite, +16 new), 717 passed/29
  deselected (`tests/ -m "not slow"`).

- Plan 16-06 (Seed threading & recording, HOOK-06 gap closure) — COMPLETE
  2026-07-23. Commits `e92a01d` (thread config.seed into split_detections),
  `f4f0249` (record seed in CalibrationMetadata). Summary:
  `.planning/phases/16-experiment-observability-hooks/16-06-SUMMARY.md`.
  Audit-driven plan: five of the six HOOK-06 entry points (all generators,
  `split_holdout`, `refine_calibration`) were already threaded and needed no
  code. Closed the two real gaps: `run_calibration_from_config`'s
  `split_detections` call now passes `seed=config.seed` (was silently always
  42, no config control), and `CalibrationMetadata` gained `seed: int | None
  = None`, written to `calibration_initial.json`, the final `calibration.json`,
  and every stage dump, with `.get("seed")` on deserialize for backward
  compatibility. `_compute_config_hash` now includes seed so seed-only config
  differences no longer collide. Zero behavior change verified: default seed
  (42) reproduces the exact pre-change split. No regressions: 718 passed
  (full unit suite, +1 net), 723 passed/29 deselected (`tests/ -m "not slow"`).

- Plan 16-07 (Standalone held-out evaluation, HOOK-04) — COMPLETE 2026-07-23. Commits
  `c5c8218` (feat: evaluate_calibration + move _estimate_validation_poses), `f04a093`
  (test: standalone behaviour + exact-equality legacy-equivalence regression),
  `c27c747` (refactor: pipeline calls evaluate_calibration), `375e1a1` (test: retarget
  mocks + refactor guards). Summary:
  `.planning/phases/16-experiment-observability-hooks/16-07-SUMMARY.md`. Added
  `aquacal.evaluate_calibration` (16th top-level public name) and
  `aquacal.validation.evaluation.HeldOutEvaluation`; moved `_estimate_validation_poses`
  out of `pipeline.py` into `validation/evaluation.py`; refactored
  `run_calibration_from_config`'s inline held-out block to call `evaluate_calibration`
  for both primary and auxiliary cameras (auxiliary reuses primary's poses instead of
  re-estimating), with a `temp_result`-construction reordering that carries no numerical
  effect. Guarded by an exact-equality (not approx) regression test proving the refactor
  changed no numbers, plus an executable WP4 test showing a >2x reprojection-RMS
  degradation when scoring against a held-out set generated at a different n_water.
  All six HOOK-01..06 requirements for Phase 16 are now complete. No regressions: 763
  passed (full unit suite, +45 net), 734 passed/29 deselected (`tests/ -m "not slow"`).

### Phase 17 Plan Progress

Phase 17 (Per-Camera Interface Ablation Mode) — COMPLETE 2026-07-23, all 5 plans, all of
IFACE-01..05. Verification PASSED (`17-VERIFICATION.md`): full suite **799 passed / 0 failed**
(40 min, slow tests included); fast suite 768 passed / 31 deselected. Roadmap commit `b2aea44`.

- Plan 17-01 (Per-camera water_z packing/structure layer, IFACE-02/IFACE-03) — COMPLETE.
  Threaded `shared_interface` through `pack_params`, `unpack_params`, `build_bounds`,
  `build_jacobian_sparsity`, `build_structural_column_groups`, and `build_parameter_labels`.
  `pack_params` also gained an optional `water_z_per_camera` dict; when it is None, per-camera
  mode seeds every camera from the scalar `water_z` (the trivial equal-seed case IFACE-05's
  recovery test needs). Sparsity emits N per-camera columns, each nonzero only in its own
  camera's residual rows; grouping collapses them into one slot so the count stays 13/17.
  IFACE-03 safety net parametrizes all 8 mode combinations.

- Plan 17-02 (`shared_interface` config surface, IFACE-01) — COMPLETE.
  `CalibrationConfig.shared_interface: bool = True` with an ablation-framed docstring;
  `load_config` parses `interface.shared_interface` early (right after `normal_fixed`, so it
  is in scope for the coverage gate) and passes it through with no cross-field validation;
  `aquacal init` emits a commented template line; `docs/guide/refractive_geometry.md` carries
  an ablation-only stub. Ablation framing deliberately repeated in three places.

- Plan 17-03 (Optimizer + pipeline integration, IFACE-01/IFACE-02) — COMPLETE.
  `optimize_interface` (Stage 3) and `joint_refinement` (Stage 4) both accept
  `shared_interface` and seed each camera from its own value (`initial_water_zs` /
  `distances_in`). `run_calibration_from_config` wires `config.shared_interface` into both
  stages and prints exactly one reason-bearing WARNING at pipeline start in per-camera mode.
  The observer's `water_z_index` formula (`0/2 + 6*(n_cams-1)`) is valid in both modes — it
  points at `camera_order[0]`'s water_z.

- Plan 17-04 (Per-camera seed resolver + spread report, IFACE-04) — COMPLETE.
  `_resolve_per_camera_water_z_seeds`: None fills 0.15 silently; a partial dict fills the
  missing cameras and warns naming them; an unknown key warns as a likely typo; an
  auxiliary-camera key is silently ignored. Uses `warnings.warn(UserWarning)` rather than
  `print` so each case is assertable. `_build_interface_spread_report` writes
  `internals/interface_spread.json` (meters, `std` = population/ddof=0) plus an mm console
  summary, tagged with the producing stage using the same selection logic as the
  conditioning report. Both guarded by `if not config.shared_interface`.

- Plan 17-05 (IFACE-05 correctness safety net) — COMPLETE, and it earned its keep.
  Added `tests/synthetic/test_per_camera_interface.py`: packing-layer bit-identity
  (rtol=0/atol=0), end-to-end shared-mode Stage-3 determinism, and equal-seed per-camera
  recovery to ~1e-15 on shared-interface ground truth. **The recovery test exposed a Rule-1
  bug plans 17-01/17-03 both missed**: `compute_residuals` called `unpack_params` without
  `shared_interface`, so per-camera mode read a single water_z and misaligned every later
  parameter block — Stage 3 diverged to RMS ~148 even starting from the noiseless optimum.
  Fixed (`575bdc8`) by threading `shared_interface` into `compute_residuals` and both
  optimizers' `cost_args`. See the `shared_interface`-unpack lesson in `knowledge-base.md`.

### Quick Tasks Completed

| # | Description | Date | Commit | Directory |
|---|-------------|------|--------|-----------|
| 2 | add explicit reject_outlier_frames parameter to generated configs | 2026-07-20 | 8b6eb0d | [2-add-explicit-reject-outlier-frames-param](./quick/2-add-explicit-reject-outlier-frames-param/) |
| 3 | use a structural column grouping for the FD Jacobian | 2026-07-23 | 3c8685c | [3-use-a-structural-column-grouping-for-the](./quick/3-use-a-structural-column-grouping-for-the/) |

### Phase 16 HOOK-03 conditioning route (settled by measurement, 2026-07-23)

Blocked tall-skinny QR — row-chunks of `result.jac` maintaining an `(n,n)` R via
`qr(..., mode='economic')`, then one `svd(R, full_matrices=False)` for spectrum and `V`.
Measured on a near-degenerate synthetic problem, this is not a preference:

- `eigh(J.T @ J)` returns sigma_min = **exactly 0.0** (cond = inf) and `inv(J.T@J)` gives an
  all-NaN correlation matrix. It fails precisely in the WP6 degeneracy regime HOOK-03 exists
  to measure. Forbidden in the plans, not even as a fallback.

- `svd(J, compute_uv=False)` gives the spectrum but no `V`, so it cannot produce the
  correlation matrix success criterion 3 requires.

- Blocked TSQR: peak extra memory is O(chunk·n), independent of m; sigma_min accurate to
  ~7e-8 relative. Because it is O(chunk), the memory pre-check is a cheap analytic guard —
  no `psutil` dependency.

**OOM trap, documented in plan 16-01:** `scipy.linalg.qr(J, mode='r')` returns R shaped
`(m, n)`, NOT `(n, n)` — only `mode='economic'` gives `(n, n)`. Feeding a `mode='r'` result
into `svd(R)` with default `full_matrices=True` allocates an m×m `U`: 12.8 GB at m=40000.
**This is what crashed the machine during the first planning session.** Full derivation in
the Addendum at the end of `16-RESEARCH.md`.

## Session Continuity

Last session: 2026-07-28T21:26:12.621Z
Stopped at: Phase 19.2: D-26 replan COMPLETE -- 14 plans in 8 waves, ready to execute
  written and committed (`102acad`). Six gray areas auto-resolved: the three-stage rename
  cuts through to machine keys (`timings`, `internals/` filenames, JSON stage tags) while
  Phases 16-17 sit unreleased; ex-Stage-4 becomes "Stage 3's optional intrinsic pass" /
  `stage3_intrinsic_pass`; the pose-graph figure is regenerated from the paper supplement's
  heap-replaying generator (renamed `pose_graph.png`); DOCS-04 gets a new
  `docs/guide/configuration.md`; sweeps cover `src/` + `docs/` + `README.md` only; the
  DOCS-01 numbers become test-asserted.
  Two flags carried into planning: (1) the paper's exact stage labels are unconfirmed —
  the manuscript is not in this repo, so the chosen vocabulary needs checking before the
  rename lands; (2) the DOCS-01 figures in the source worklist were measured with
  `group_columns`, which quick task 3 (`3c8685c`) replaced with
  `build_structural_column_groups` — re-derive against the shipped path.
  Both matched todos (Zenodo dataset 0.90, memory/CPU 0.40) were reviewed and declined
  rather than auto-folded; each is sequenced elsewhere by a locked decision.
  Nothing has been pushed: Phases 16-17 and quick task 3 sit unreleased on local `main`.
Previously: Phase 17 (Per-Camera Interface Ablation Mode) executed and verified — all 5
  plans done, all five IFACE-01..05 requirements satisfied, 799 tests passing. With
  Phase 16 already complete, the milestone's experiment-blocking chain is finished and
  WP5/WP6 execution is unblocked.
  Before that: Plan 16-07 (standalone held-out evaluation, HOOK-04) executed and committed,
  completing Phase 16 (Experiment Observability Hooks) — all 7 plans, all six HOOK-01..06
  requirements.
  Before that: Phase 16 context gathered. Roadmap for v1.9 was created and then revised to
  run the experiment-blocking chain first, so ROADMAP.md carries phases 16-22 in the
  order: Hooks (16) -> Per-Camera Interface (17) -> Docs Reconciliation (18) ->
  Benchmark Instrumentation (19) -> Index Helper (20) -> Docs/Dataset Refresh (21) ->
  Release Cut (22). All 29 requirements map to exactly one phase.

  Phase 16 CONTEXT.md then settled the observability design: flat per-hook config keys
  following `save_detailed_residuals`, config-only with no CLI flags, stage dumps on by
  default with trace and conditioning opt-in, artifacts in `output_dir/internals/`
  (not `diagnostics/` — a `diagnostics.json` file already sits at that level), trace as
  CSV, conditioning split across JSON scalars and an NPZ matrix, `evaluate_calibration`
  as a top-level export with conditioning in `aquacal.validation.*`.

  Two flags for planning: conditioning computes the full correlation matrix by explicit
  choice on a run already peaking at ~3.6 GB, so headroom needs verifying and the
  pre-check must refuse loudly rather than narrow the metric silently; and HOOK-05/HOOK-06
  look largely satisfied already, so both are audits rather than assumed work.

Resume file: .planning/phases/19.2-experiment-execution-and-provenance/19.2-CONTEXT.md
  (Read alongside `18-DISCUSSION-LOG.md` for the alternatives considered.)
