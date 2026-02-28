# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-02-28)

**Core value:** Accurate refractive camera calibration from standard ChArUco board observations — researchers can pip install aquacal, point it at their videos, and get a calibration result they trust.
**Current focus:** v1.6 Refinement API — Phase 13: Core Refinement

## Current Position

Phase: 13 of 15 (Core Refinement)
Plan: 1 of TBD in current phase
Status: In progress
Last activity: 2026-02-28 — Completed plan 13-01 (Core Refinement API)

Progress: [█░░░░░░░░░] 10% (v1.6)

## Performance Metrics

**Velocity:**
- Total plans completed (v1.6): 1
- Average duration: 6 min
- Total execution time: 6 min

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| 13-core-refinement | 1 | 6 min | 6 min |

**Recent Trend:**
- Last 5 plans: 13-01 (6 min)
- Trend: —

*Updated after each plan completion*

## Accumulated Context

### Decisions

Decisions are logged in PROJECT.md Key Decisions table.
Recent decisions affecting current work:

- [v1.6 start]: Refinement API accepts abstract float weights — what "goodness" means is the caller's domain
- [v1.6 start]: No CLI command for refinement in v1.6 — library API only
- [v1.6 start]: Board poses are irrelevant for point-correspondence refinement; only extrinsics + water_z optimized by default
- [13-01]: reference_camera = first in sorted camera_order — consistent with existing pipeline convention
- [13-01]: minimum 10 active correspondences threshold for stable bundle adjustment
- [13-01]: non-convergence logs warning and returns best-effort result — Phase 15 RefinementResult will expose status explicitly
- [13-01]: local _pack/_unpack functions in point_refinement.py (not modifying _optim_common which is board-pose-specific)

### Pending Todos

- Design better hero image for README (deferred from Phase 11)
- Reduce memory and CPU load during calibration
- Check version field in JSON output reads local version properly
- Upload new Zenodo dataset with image-based inputs (updated config.yaml)

### Blockers/Concerns

None.

## Session Continuity

Last session: 2026-02-28
Stopped at: Completed 13-01-PLAN.md (Core Refinement API)
Resume file: None
