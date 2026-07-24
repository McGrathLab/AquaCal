---
phase: 18-documentation-corrections-stage-model-reconciliation
plan: 04
subsystem: docs
tags: [matplotlib, sphinx, pose-graph, heap-traversal, diagram-generation]

# Dependency graph
requires:
  - phase: 18-01
    provides: corrected optimizer.md numeric section (43-52x, 673/675/727, 13/17 groups)
provides:
  - Heap-replaying pose_graph.py generator (imports aquacal.calibration.extrinsics.build_pose_graph)
  - Regenerated docs/_static/diagrams/pose_graph.png
  - Corrected bipartite pose-graph glossary definition
affects: [18-08]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "generate(output_dir) -> None contract, consistent with sparsity_pattern.py and the retired bfs_pose_graph.py"
    - "Diagram edge classification derived by replaying the library's own priority-heap loop against a small synthetic DetectionResult fixture, never a hardcoded edge list"

key-files:
  created:
    - docs/_static/scripts/pose_graph.py
  modified:
    - docs/guide/_diagrams/generate_all.py
    - docs/guide/optimizer.md
    - docs/guide/glossary.md
  deleted:
    - docs/_static/scripts/bfs_pose_graph.py
    - docs/_static/diagrams/bfs_pose_graph.png

key-decisions:
  - "Single-panel figure layout chosen over the supplement's six-panel port, per the plan's Claude's-discretion clause, to avoid LaTeX-mathtext (\\textbf) and figure-legend-cropping risk from a from-scratch six-panel port under time constraints; both edge types, direction semantics, and the redundant edge are preserved"
  - "Traversal replay sorts adjacency neighbours for both node types (library's own camera-branch iteration is unsorted); verified by manual trace that neighbour order within one heap pop does not change which edges are discovered, only its ordering — so this is a determinism convenience, not a behavioral divergence from the library"
  - "Glossary Pose graph entry rewritten wholesale (not surgically preserving 'via BFS traversal') using neutral phrasing 'Used in Stage 2 for extrinsic initialization', deferring the confirmed 'best-first' term to plan 18-08 per the plan's explicit instruction not to front-run the 18-02 checkpoint"

requirements-completed: []  # DOCS-03 NOT yet complete — Task 3 (human visual verification) is pending

# Metrics
duration: in progress (partial — Tasks 1-2 only)
completed: null
---

# Phase 18 Plan 04: Pose Graph Regeneration (Tasks 1-2 of 3) Summary

**PARTIAL — CHECKPOINT PENDING.** Tasks 1 and 2 are complete and committed; Task 3 is a
blocking `checkpoint:human-verify` that requires a human to visually inspect the regenerated
figure. This summary will be completed/replaced by a continuation agent after the human
responds.

**New `pose_graph.py` generator classifies discovery vs. redundant edges by replaying
`estimate_extrinsics`'s real priority-heap loop against a live `build_pose_graph` call — no
hardcoded edge list — producing a single-panel `pose_graph.png` with 4 camera nodes, 3 frame
nodes, 6 numbered directed discovery edges, and 1 undirected redundant edge.**

## Performance (partial)

- **Tasks completed:** 2 of 3
- **Commits:** 2 (task) + this partial summary

## Accomplishments (Tasks 1-2 only)

- Replaced the hand-authored `bfs_pose_graph.py` (hardcoded `EDGES`/`BFS_EDGES` constants)
  with `pose_graph.py`, which builds a small 4-camera/3-frame `DetectionResult` fixture
  (corner counts taken from the paper supplement's own worked example), calls the real
  `aquacal.calibration.extrinsics.build_pose_graph`, and replays the priority-heap loop to
  derive which edges are discovery edges vs. redundant observation edges.
- Manually traced the replay against the fixture topology and confirmed it produces exactly
  6 directed discovery edges (cam0→F1, cam0→F2, F2→cam1, cam1→F3, F3→cam2, F3→cam3) and
  exactly 1 undirected redundant edge (cam2–F1), over 4 cameras and 3 frames — matching the
  plan's expected topology.
- Rewired `docs/guide/_diagrams/generate_all.py` to import/call the new generator and
  announce "Generating pose graph diagram..." instead of the BFS-named string.
- Regenerated `docs/_static/diagrams/pose_graph.png`, deleted the old
  `docs/_static/diagrams/bfs_pose_graph.png` (no dual-file period).
- Updated `docs/guide/optimizer.md`'s image directive and alt text to reference the new file
  and describe the bipartite structure with directed discovery edges (left the checkpoint-
  gated `Why BFS?` heading, the `BFS traversal` bullet, and the `(BFS/PnP)` mermaid label
  untouched — those are plan 18-08's scope).
- Corrected `docs/guide/glossary.md`'s `Pose graph` definition to describe the real bipartite
  structure (camera nodes and frame nodes, an edge from each camera to each frame it
  observes), replacing the backwards "edges connect observations of the same board pose"
  text. Did not write "best-first" into the glossary (plan 18-02 checkpoint not yet resolved).

## Task Commits

1. **Task 1: Write the heap-replaying pose_graph.py generator and rewire generate_all.py** -
   `f93e0e8` (docs)
2. **Task 2: Regenerate the figure, delete the old PNG, and update its references** -
   `9ae1f55` (docs)

_Task 3 (checkpoint:human-verify) not yet executed — pending human response._

## Files Created/Modified

- `docs/_static/scripts/pose_graph.py` - new heap-replaying generator (304 lines)
- `docs/_static/scripts/bfs_pose_graph.py` - deleted
- `docs/guide/_diagrams/generate_all.py` - rewired import/call/print string
- `docs/_static/diagrams/pose_graph.png` - regenerated (new)
- `docs/_static/diagrams/bfs_pose_graph.png` - deleted
- `docs/guide/optimizer.md` - image directive + alt text updated (line ~73 only)
- `docs/guide/glossary.md` - `Pose graph` definition corrected (line ~34-35 only)

## Verification Performed (Tasks 1-2)

- `python docs/guide/_diagrams/generate_all.py` exits 0, prints
  `Generating pose graph diagram...` and `Saved: ...pose_graph.png`.
- All Task 1 grep/ruff acceptance criteria passed: `from aquacal` present, `heapq`/`heappush`/
  `heappop` present, no `EDGES=`/`BFS_EDGES=` constant, exactly one `def generate(output_dir`,
  `pose_graph.png` present and `bfs_pose_graph` absent from the new file, `from palette import`
  present, no standalone `BFS` word anywhere in the file, `ruff check` passes.
- All Task 2 grep/build criteria passed: `pose_graph.png` referenced exactly once in
  `optimizer.md`, old alt text `![BFS pose graph]` gone, `bipartite` present in `glossary.md`,
  old backwards sentence gone, `Why BFS?` heading count unchanged at 1, no `best-first` in
  `glossary.md`.
- `sphinx-build -W --keep-going -b html docs docs/_build/html` exits 0 (build succeeded,
  `docs/_build/html/_static/diagrams/pose_graph.png` exists).
- `python -m pytest tests/ -m "not slow"` — **775 passed, 31 deselected** (no regressions; no
  source files under `src/` were touched by this plan).

## Decisions Made

See `key-decisions` in frontmatter above:
1. Single-panel layout chosen over the six-panel port (risk/time tradeoff, explicitly
   permitted by the plan's discretion clause).
2. Sorted adjacency iteration in the replay for deterministic rendering — verified by manual
   trace to not change the discovery/redundant edge classification versus the library's own
   unsorted camera-branch order.
3. Glossary sentence rewritten wholesale with neutral "Used in Stage 2..." phrasing rather
   than trying to surgically preserve a "via BFS traversal" fragment, per the plan's explicit
   fallback instruction.

## Deviations from Plan

**1. [Rule 1 - Bug] Removed an unused local variable flagged by the ruff pre-commit hook**
- **Found during:** Task 1, first commit attempt
- **Issue:** `directed_lookup` dict was computed but never read (F841).
- **Fix:** Removed the dead assignment; `discovery_set`/`badge_lookup` already carry
  everything the render step needs.
- **Files modified:** `docs/_static/scripts/pose_graph.py`
- **Verification:** `ruff check` passes; figure regenerated bit-identically before/after.
- **Committed in:** `f93e0e8` (folded into Task 1's commit before it succeeded)

**2. [Rule 1 - Bug] Docstring accidentally referenced the retired `bfs_pose_graph.py` filename**
- **Found during:** Task 1, acceptance-criteria self-check
- **Issue:** The module docstring's first draft said "Unlike the retired
  ``bfs_pose_graph.py``...", which violates the acceptance criterion that
  `grep -c "bfs_pose_graph" docs/_static/scripts/pose_graph.py` return 0.
- **Fix:** Reworded the docstring to describe the new behavior without naming the old file.
- **Files modified:** `docs/_static/scripts/pose_graph.py`
- **Verification:** `grep -c "bfs_pose_graph" docs/_static/scripts/pose_graph.py` returns 0.
- **Committed in:** `f93e0e8`

---

**Total deviations:** 2 auto-fixed (both Rule 1, both caught by acceptance-criteria checks
before commit). No scope creep.

## Issues Encountered

None beyond the two auto-fixed items above.

## Next Steps

**BLOCKED on Task 3** — a human must visually inspect
`docs/_static/diagrams/pose_graph.png` and confirm the five conditions in the plan's
`<how-to-verify>` (4 camera nodes / 3 frame nodes in two columns; exactly 6 directed
discovery edges with correct direction; exactly 1 undirected redundant edge with no
arrowhead; no orphan legend keys; title reads "Stage 2: Pose Graph" with no "BFS" text
anywhere in the image). The generated figure and the manual heap-replay trace above both
indicate these conditions hold, but per the plan's explicit instruction this is a human-only
check that the executor must not self-approve.

A continuation agent will resume at Task 3 once the human responds, and will replace this
partial summary with the final one (updating `requirements-completed: [DOCS-03]`, `duration`,
and `completed`).
