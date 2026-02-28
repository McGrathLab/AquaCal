# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-02-28)

**Core value:** Accurate refractive camera calibration from standard ChArUco board observations — researchers can pip install aquacal, point it at their videos, and get a calibration result they trust.
**Current focus:** v1.6 Refinement API — Phase 13: Core Refinement

## Current Position

Phase: 13 of 15 (Core Refinement)
Plan: 0 of TBD in current phase
Status: Ready to plan
Last activity: 2026-02-28 — Roadmap created for v1.6 milestone

Progress: [░░░░░░░░░░] 0% (v1.6)

## Performance Metrics

**Velocity:**
- Total plans completed (v1.6): 0
- Average duration: —
- Total execution time: —

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| - | - | - | - |

**Recent Trend:**
- Last 5 plans: —
- Trend: —

*Updated after each plan completion*

## Accumulated Context

### Decisions

Decisions are logged in PROJECT.md Key Decisions table.
Recent decisions affecting current work:

- [v1.6 start]: Refinement API accepts abstract float weights — what "goodness" means is the caller's domain
- [v1.6 start]: No CLI command for refinement in v1.6 — library API only
- [v1.6 start]: Board poses are irrelevant for point-correspondence refinement; only extrinsics + water_z optimized by default

### Pending Todos

- Design better hero image for README (deferred from Phase 11)
- Reduce memory and CPU load during calibration
- Check version field in JSON output reads local version properly
- Upload new Zenodo dataset with image-based inputs (updated config.yaml)

### Blockers/Concerns

None.

## Session Continuity

Last session: 2026-02-28
Stopped at: Roadmap created — ready to plan Phase 13
Resume file: None
