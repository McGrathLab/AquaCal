# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-02-19)

**Core value:** Accurate refractive camera calibration from standard ChArUco board observations — researchers can pip install aquacal, point it at their videos, and get a calibration result they trust.
**Current focus:** Planning next milestone

## Current Position

Phase: N/A (between milestones)
Plan: N/A
Status: MILESTONE COMPLETE
Last activity: 2026-02-23 - Completed quick task 1: Add calibration-file-based synthetic rig to 02_synthetic_validation

Progress: All v1.2 + v1.4 milestones shipped (12 phases, 30 plans)

## Accumulated Context

### Decisions

Decisions are logged in PROJECT.md Key Decisions table.
- [Phase quick]: rig_from_calibration returns 4-tuple including BoardConfig for real board geometry reuse

### Pending Todos

- Design better hero image for README (deferred from Phase 11 — user wants to rethink concept)
- Reduce memory and CPU load during calibration
- Check version field in JSON output reads local version properly

### Blockers/Concerns

None.

### Quick Tasks Completed

| # | Description | Date | Commit | Directory |
|---|-------------|------|--------|-----------|
| 1 | Add calibration-file-based synthetic rig to 02_synthetic_validation | 2026-02-23 | a24c8d6 | [1-add-calibration-file-based-synthetic-rig](./quick/1-add-calibration-file-based-synthetic-rig/) |

## Session Continuity

Last session: 2026-02-19 (v1.4 milestone archived)
Stopped at: Milestone complete
Resume file: N/A

**Next step:** `/gsd:new-milestone` to start next milestone (questioning → research → requirements → roadmap)
