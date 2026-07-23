---
gsd_state_version: 1.0
milestone: v1.9
milestone_name: Publication Prep
status: roadmapped
last_updated: "2026-07-23"
progress:
  total_phases: 7
  completed_phases: 0
  total_plans: 0
  completed_plans: 0
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-07-23)

**Core value:** Accurate refractive camera calibration from standard ChArUco board observations — researchers can pip install aquacal, point it at their videos, and get a calibration result they trust.
**Current focus:** v1.9 Publication Prep — roadmap approved, ready for phase planning

## Current Position

Phase: 16 (Experiment Observability Hooks) — not started
Plan: —
Status: Roadmap created (revised), awaiting `/gsd:plan-phase 16`
Last activity: 2026-07-23 — ROADMAP.md reordered so the experiment-blocking chain
  (Hooks then Per-Camera Interface) runs first; REQUIREMENTS.md traceability updated
  to match

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

### Quick Tasks Completed

| # | Description | Date | Commit | Directory |
|---|-------------|------|--------|-----------|
| 2 | add explicit reject_outlier_frames parameter to generated configs | 2026-07-20 | 8b6eb0d | [2-add-explicit-reject-outlier-frames-param](./quick/2-add-explicit-reject-outlier-frames-param/) |
| 3 | use a structural column grouping for the FD Jacobian | 2026-07-23 | 3c8685c | [3-use-a-structural-column-grouping-for-the](./quick/3-use-a-structural-column-grouping-for-the/) |

## Session Continuity

Last session: 2026-07-23
Stopped at: Phase 16 context gathered. Roadmap for v1.9 was created and then revised to
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
