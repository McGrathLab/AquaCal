---
phase: 18-documentation-corrections-stage-model-reconciliation
plan: 05
subsystem: docs
tags: [vocabulary, best-first, extrinsics, comment-accuracy]

# Dependency graph
requires:
  - phase: 18-documentation-corrections-stage-model-reconciliation
    provides: 18-02-SUMMARY.md's confirmed vocabulary contract (best-first term)
provides:
  - Corrected traversal terminology and behavior-accurate loop comments in estimate_extrinsics
affects: []

# Tech tracking
tech-stack:
  added: []
  patterns: []

key-files:
  created: []
  modified:
    - src/aquacal/calibration/extrinsics.py

key-decisions:
  - "Applied the confirmed 'best-first' term (per 18-02-SUMMARY.md) at all four estimate_extrinsics BFS sites; _find_connected_components' two genuine BFS mentions (lines 200, 208) left untouched"
  - "Rewrote both misleading 'Score each neighboring ... by corner count' comments to describe the actual filter-and-push behavior, naming the shared heap as where prioritisation really happens"
  - "Added the finalised-on-first-discovery invariant to the estimate_extrinsics docstring, contrasted explicitly with Prim's algorithm"

patterns-established: []

requirements-completed: [DOCS-02]

# Metrics
duration: 15min
completed: 2026-07-24
---

# Phase 18 Plan 05: Extrinsics Traversal Terminology & Comment Accuracy Summary

**Corrected four BFS-to-best-first terminology sites and two misleading neighbour-scoring comments in `estimate_extrinsics`, and documented the finalised-on-first-discovery invariant that distinguishes the traversal from Prim's algorithm — all comment/docstring-only changes with zero behavioral impact.**

## Performance

- **Duration:** 15 min
- **Started:** 2026-07-24
- **Completed:** 2026-07-24
- **Tasks:** 2
- **Files modified:** 1

## Accomplishments
- Replaced all four "BFS" mentions in `estimate_extrinsics`'s docstring, Args entry, and inline comment with "best-first traversal" / "best-first", per the confirmed vocabulary contract in `18-02-SUMMARY.md`
- Left `_find_connected_components`'s two genuine BFS mentions (docstring + inline comment, lines 200/208) completely untouched — verified via targeted grep counts, not a file-wide substitution
- Rewrote both "Score each neighboring ... by corner count" comments (camera-node and frame-node branches), which previously described a per-loop scoring/sorting step that does not exist, to state what the loops actually do: filter unvisited neighbours in adjacency/sorted order and push each onto the shared heap, where the real corner-count prioritisation happens
- Added the "finalised on first discovery" invariant to the docstring, naming the contrast with Prim's algorithm explicitly — the property that makes the terminology choice matter

## Task Commits

Each task was committed atomically:

1. **Task 1: Correct the four traversal-terminology sites in estimate_extrinsics** - `bfee0ad`
2. **Task 2: Fix the two misleading neighbour-scoring comments and add the first-discovery invariant** - `4d33261`

## Files Created/Modified
- `src/aquacal/calibration/extrinsics.py` - docstring/comment corrections only; no executable statement changed

## Decisions Made

No new decisions — this plan implements the vocabulary contract already confirmed in `18-02-SUMMARY.md` (D-02, D-11) and the behavior-describing fixes locked in `18-CONTEXT.md` (D-12, D-13), which apply regardless of the checkpoint's terminology outcome.

## Deviations from Plan

None - plan executed exactly as written. All acceptance criteria matched on the first attempt:
- `grep -c "BFS"` returns exactly 2 (both inside `_find_connected_components`)
- `grep -c "Score each neighboring"` returns 0
- `grep -ciE "first discovery|finalis|finaliz"` returns 1
- `grep -ci "Prim"` returns 1
- `sorted(pose_graph.adjacency.get(node, []))` call count unchanged (1)
- `heapq.heappush` count unchanged (2)
- Full diff confined to comment/docstring lines (manually inspected)

## Issues Encountered

None.

## Verification Results

- `python -m pytest tests/unit/test_extrinsics.py -q` — 34 passed
- `python -m pytest tests/unit/test_extrinsics.py tests/unit/test_pipeline.py -q` — 118 passed
- `python -m pytest tests/ -m "not slow"` — 775 passed, 31 deselected
- `ruff check src/aquacal/calibration/extrinsics.py` — all checks passed
- `git diff -U0` confirms every changed line sits inside a docstring or comment; no `def`, `if`, `for`, `heapq`, or assignment line appears in either commit's diff

## User Setup Required

None.

## Next Phase Readiness

DOCS-02's code-side terminology correction is complete for `extrinsics.py`. No blockers for downstream plans (18-06, 18-07, 18-08), which consume the same vocabulary contract independently.

## Self-Check: PASSED

- FOUND: src/aquacal/calibration/extrinsics.py
- FOUND: bfee0ad (git log --oneline --all)
- FOUND: 4d33261 (git log --oneline --all)

---
*Phase: 18-documentation-corrections-stage-model-reconciliation*
*Completed: 2026-07-24*
