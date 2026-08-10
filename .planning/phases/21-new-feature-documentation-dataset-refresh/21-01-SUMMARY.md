---
phase: 21-new-feature-documentation-dataset-refresh
plan: 01
subsystem: infra
tags: [opencv, video, dataset, cli-script]

# Dependency graph
requires: []
provides:
  - "scripts/extract_frames.py: deterministic every-Nth-frame AVI -> lossless PNG extractor"
  - "tests/unit/test_extract_frames.py: 5 fast unit tests covering naming, step default, and both guards"
affects: [21-06, 21-07]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "scripts/ directory for non-package, non-public data-prep utilities (argparse build_arg_parser()/main(argv)/if __name__ skeleton, no experiments/ smoke/check/force machinery)"

key-files:
  created:
    - scripts/extract_frames.py
    - tests/unit/test_extract_frames.py
  modified: []

key-decisions:
  - "Camera id derived from AVI filename stem up to first '-', validated against [A-Za-z0-9_-]+ before use as a directory name (T-21-01-01 mitigation)"
  - "--limit stops writing per camera once each camera reaches the cap, rather than truncating the whole VideoSet iteration at a global frame count, so ragged fake/real inputs still produce equal per-camera counts under the smoke-test aid"

patterns-established:
  - "scripts/<tool>.py loaded by tests via importlib.util.spec_from_file_location, since scripts/ is outside the package import path"

requirements-completed: [DATA-01a]

# Metrics
duration: 25min
completed: 2026-08-10
---

# Phase 21 Plan 01: Frame Extraction Tool Summary

**`scripts/extract_frames.py` — a committed, non-package CLI tool that reads synchronized per-camera AVIs via `VideoSet.iterate_frames(step=...)` and writes every Nth frame as lossless PNG into `<out-dir>/<camera>/frame%04d.png`, with non-zero exit guards against silent zero-frame and ragged extractions.**

## Performance

- **Duration:** ~25 min
- **Tasks:** 2 completed
- **Files modified:** 2 (both new)

## Accomplishments
- New `scripts/` directory (did not exist before this plan, per D-11) with a lint-clean, docstringed extraction tool
- Extractor calls `aquacal.io.video.VideoSet.iterate_frames` rather than reimplementing frame decoding (D-11's explicit constraint)
- Output layout matches `ImageSet`'s natsort-stable read-back contract exactly (`frame{idx:04d}.png`)
- Zero-frame and ragged-count guards return non-zero exit rather than silently producing an incomplete/empty archive
- 5 fast unit tests (all monkeypatched, no real AVI decode, <1s total) covering naming, the `step=30` default, and both guards including the lossless round-trip property

## Task Commits

Each task was committed atomically:

1. **Task 1: Write scripts/extract_frames.py** - `35cd5ae` (feat)
2. **Task 2: Unit tests for naming, step arithmetic, and the guards** - `ec2ce56` (test)

## Files Created/Modified
- `scripts/extract_frames.py` - AVI -> lossless PNG extractor CLI; `build_arg_parser()`, `_camera_id_from_path()`, `_discover_video_paths()`, `main(argv) -> int`
- `tests/unit/test_extract_frames.py` - 5 unit tests; loads the script by file path and monkeypatches `VideoSet` + `_discover_video_paths`

## Decisions Made
- Validated camera ids against `[A-Za-z0-9_-]+` before using them as directory path segments, per the plan's threat model T-21-01-01 (Tampering: `--out-dir` path handling) — a crafted AVI filename cannot inject a `../` path segment.
- `--limit` is interpreted as "stop writing more frames for a camera once it has written N", checked per-frame-index across all cameras, so the smoke-test aid still produces equal per-camera counts under normal (non-ragged) fake inputs, matching the acceptance criteria's framing of it as a smoke-test-only convenience.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- `scripts/extract_frames.py` is ready for plan 21-06's production 12 GB extraction run (out of scope here, per the plan's explicit boundary — it was NOT run in this plan).
- The tool's `--allow-ragged` flag is in place for 21-06's intrinsic-video pass (differing per-camera video lengths), while the default (no flag) enforces equal counts for the extrinsic pass.

---
*Phase: 21-new-feature-documentation-dataset-refresh*
*Completed: 2026-08-10*

## Self-Check: PASSED
