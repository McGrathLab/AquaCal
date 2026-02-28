# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-02-28)

**Core value:** Accurate refractive camera calibration from standard ChArUco board observations — researchers can pip install aquacal, point it at their videos, and get a calibration result they trust.
**Current focus:** v1.6 Refinement API

## Current Position

Phase: Not started (defining requirements)
Plan: —
Status: Defining requirements
Last activity: 2026-02-28 — Milestone v1.6 started

## Accumulated Context

### Decisions

Decisions are logged in PROJECT.md Key Decisions table.
- [Phase quick]: rig_from_calibration returns 4-tuple including BoardConfig for real board geometry reuse

### Pending Todos

- Design better hero image for README (deferred from Phase 11 — user wants to rethink concept)
- Reduce memory and CPU load during calibration
- Check version field in JSON output reads local version properly
- Upload new Zenodo dataset with image-based inputs (updated config.yaml)

### Blockers/Concerns

None.

### Quick Tasks Completed

| # | Description | Date | Commit | Directory |
|---|-------------|------|--------|-----------|
| 1 | Add calibration-file-based synthetic rig to 02_synthetic_validation | 2026-02-23 | a24c8d6 | [1-add-calibration-file-based-synthetic-rig](./quick/1-add-calibration-file-based-synthetic-rig/) |

## Session Continuity

Last session: 2026-02-28 (v1.6 milestone started)
Stopped at: Defining requirements
Resume file: N/A

**Next step:** Define requirements, then create roadmap
