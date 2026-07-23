---
gsd_state_version: 1.0
milestone: v1.9
milestone_name: Publication Prep
status: planning
last_updated: "2026-07-23"
progress:
  total_phases: 0
  completed_phases: 0
  total_plans: 0
  completed_plans: 0
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-03-09)

**Core value:** Accurate refractive camera calibration from standard ChArUco board observations — researchers can pip install aquacal, point it at their videos, and get a calibration result they trust.
**Current focus:** v1.9 Publication Prep — defining requirements

## Current Position

Phase: Not started (defining requirements)
Plan: —
Status: Defining requirements
Last activity: 2026-07-23 — Milestone v1.9 Publication Prep started

Milestone v1.6 Refinement API: COMPLETE (shipped 2026-03-09), phases 13-15.
v1.7–v1.8 shipped outside the milestone framework (see MILESTONES.md).
v1.9 phase numbering continues from **16**.

**Hard deadline:** revised SoftwareX manuscript due 2026-08-21. This milestone builds
the tooling only — experiment execution (WP5/WP6) and manuscript prose happen separately,
so the code work must land with room to spare.

## Accumulated Context

### Decisions

Decisions are logged in PROJECT.md Key Decisions table.
Key v1.6 decisions:
- Refinement API accepts abstract float weights — caller defines "goodness"
- No CLI command for refinement — library API only
- Local _pack/_unpack in point_refinement.py (separate from board-pose _optim_common)
- Parameterized extensions on single function (refine_intrinsics, loss, normal_fixed)
- Any-fail accept/reject logic — conservative validation

### Pending Todos

Tracked as files in `.planning/todos/pending/` — see `/gsd:check-todos`. Do not
duplicate the list here; the two copies drifted apart between v1.6 and v1.8.

Open as of 2026-07-23:

- Reduce memory and CPU load during calibration (dense `.toarray()` Jacobian peak;
  CPU side partially addressed by quick task 3). **v1.9 measures and reports this
  peak but does not reduce it** — deliberate, see PROJECT.md Key Decisions. Stays open.
- Upload new Zenodo dataset with image-based inputs (confirmed still the 2026-02-14
  upload; serves the deprecated `initial_distances` key, which currently loads fine
  via the compat shim). **Folded into v1.9 Task Group F** — do not action standalone;
  it carries a sequencing constraint. Close it when F lands.

### Blockers/Concerns

None.

### Quick Tasks Completed

| # | Description | Date | Commit | Directory |
|---|-------------|------|--------|-----------|
| 2 | add explicit reject_outlier_frames parameter to generated configs | 2026-07-20 | 8b6eb0d | [2-add-explicit-reject-outlier-frames-param](./quick/2-add-explicit-reject-outlier-frames-param/) |
| 3 | use a structural column grouping for the FD Jacobian | 2026-07-23 | 3c8685c | [3-use-a-structural-column-grouping-for-the](./quick/3-use-a-structural-column-grouping-for-the/) |

## Session Continuity

Last session: 2026-07-23
Stopped at: Completed quick task 3 (structural FD column grouping). Stages 3 and 4
  now group Jacobian columns from the known parameter layout instead of scipy's
  greedy colorer, hitting the theoretical minimum of 13 groups (17 with intrinsic
  refinement) at any visibility, vs 16/20 measured for the greedy on a 12-cam
  0.72-visibility pattern. Output-neutral: FD Jacobians verified bit-identical.
  Commits 3c8685c, a0df1c7.
Resume file: None
