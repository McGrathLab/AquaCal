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
- Reduce memory and CPU load during calibration (Stage 3 on the 13-camera rig peaks
  at ~3.6 GB and ~26-65 min; the dense `.toarray()` Jacobian is the suspected driver)
- Recapture e3v83ef's in-air intrinsic video with deliberate board tilting — its
  current video has only 30 usable views spanning 1.1-11.5 deg, leaving fx 13% low
  and the camera 15 cm off the rig plane (data issue, not a code defect)
- Consider a perspective-warped synthetic fixture in tests/unit/test_intrinsics.py —
  the current affine-warped fixture has ~0 board tilt, so it now (correctly) trips
  the new fronto-parallel warning in 12 tests

### Blockers/Concerns

None.

### Quick Tasks Completed

| # | Description | Date | Commit | Directory |
|---|-------------|------|--------|-----------|
| 2 | add explicit reject_outlier_frames parameter to generated configs | 2026-07-20 | 8b6eb0d | [2-add-explicit-reject-outlier-frames-param](./quick/2-add-explicit-reject-outlier-frames-param/) |

## Session Continuity

Last session: 2026-07-20
Stopped at: Resolved debug session callibration071626-tilt-high-reproj (Stage 1
  intrinsics local minimum on camera e3v82e0; fixed by seeding cv2.calibrateCamera,
  verified end-to-end: rig RMS 4.789 -> 1.627 px). Added validate_view_diversity()
  Stage 1 check for fronto-parallel board captures. Commit 16fd84f.
Resume file: None
