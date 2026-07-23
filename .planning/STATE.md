---
gsd_state_version: 1.0
milestone: v1.2
milestone_name: Publication Prep
status: unknown
last_updated: "2026-07-23T20:58:13.882Z"
progress:
  total_phases: 14
  completed_phases: 12
  total_plans: 42
  completed_plans: 41
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-07-23)

**Core value:** Accurate refractive camera calibration from standard ChArUco board observations — researchers can pip install aquacal, point it at their videos, and get a calibration result they trust.
**Current focus:** v1.9 Publication Prep — Phase 16 COMPLETE, ready for Phase 17 planning

## Current Position

Phase: 16 (Experiment Observability Hooks) — COMPLETE
Plan: 7/7 plans complete (16-01, 16-02, 16-03, 16-04, 16-05, 16-06, 16-07); plan-checker
  PASSED first iteration
Status: Phase 16 complete. Ready for `/gsd:plan-phase 17`.
Last activity: 2026-07-23 — plan 16-07 (standalone held-out evaluation, HOOK-04) executed;
  see "Phase 16 Plan Progress" below for details.
  An earlier planning session crashed the machine mid-research-followup; recovered from
  its transcript, see the HOOK-03 note below.

Milestone v1.6 Refinement API: COMPLETE (shipped 2026-03-09), phases 13-15.
v1.7–v1.8 shipped outside the milestone framework (see MILESTONES.md).
v1.9 phase numbering continues from **16** and spans **16-22** (7 phases).

v1.9 phase structure (revised order — experiment blocker first):
- Phase 16: Experiment Observability Hooks (HOOK-01..06) — no dependency, first phase
- Phase 17: Per-Camera Interface Ablation Mode (IFACE-01..05) — depends on Phase 16
  (needs HOOK-03 conditioning diagnostics as the WP6 metric). Phases 16-17 together are
  the milestone's longest pole and only true experiment blocker; sequenced first so
  WP5/WP6 experiments can start as early as possible against the deadline.
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

### Pending Todos

Tracked as files in `.planning/todos/pending/` — see `/gsd:check-todos`. Do not
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

Last session: 2026-07-23
Stopped at: Plan 16-07 (standalone held-out evaluation, HOOK-04) executed and committed.
  Phase 16 (Experiment Observability Hooks) is now COMPLETE — all 7 plans done, all six
  HOOK-01..06 requirements satisfied. Next step is `/gsd:plan-phase 17`.
Previously: Phase 16 context gathered. Roadmap for v1.9 was created and then revised to
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

  Next step is `/gsd:plan-phase 16`.
Resume file: .planning/phases/16-experiment-observability-hooks/16-CONTEXT.md
