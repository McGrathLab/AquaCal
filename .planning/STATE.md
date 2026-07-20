---
gsd_state_version: 1.0
milestone: v1.6
milestone_name: Refinement API
status: complete
last_updated: "2026-03-09"
progress:
  total_phases: 15
  completed_phases: 15
  total_plans: 36
  completed_plans: 36
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-03-09)

**Core value:** Accurate refractive camera calibration from standard ChArUco board observations — researchers can pip install aquacal, point it at their videos, and get a calibration result they trust.
**Current focus:** Planning next milestone

## Current Position

Milestone v1.6 Refinement API: COMPLETE (shipped 2026-03-09)
All 3 phases (13-15), 6 plans complete.

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

- Design better hero image for README (deferred from Phase 11)
- Reduce memory and CPU load during calibration

### Blockers/Concerns

None.

## Session Continuity

Last session: 2026-07-20
Stopped at: Completed quick task 2 (reject_outlier_frames config discoverability)
Resume file: None
