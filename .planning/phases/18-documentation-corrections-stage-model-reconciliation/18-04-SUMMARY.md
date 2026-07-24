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
  - Regenerated docs/_static/diagrams/pose_graph.png, human-verified with correct edge direction
  - Corrected bipartite pose-graph glossary definition
affects: [18-08]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "generate(output_dir) -> None contract, consistent with sparsity_pattern.py and the retired bfs_pose_graph.py"
    - "Diagram edge classification derived by replaying the library's own priority-heap loop against a small synthetic DetectionResult fixture, never a hardcoded edge list"
    - "When collapsing a directed edge into an unordered key (e.g. frozenset) for membership testing, keep a parallel ordered lookup for anything that needs direction back — collapsing loses direction silently, with no error, only a rendering bug"

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
  - "Single-panel figure layout chosen over the paper supplement's six-panel port, per the plan's Claude's-discretion clause: avoids LaTeX-mathtext (\\textbf) rendering risk and figure-legend-cropping risk from porting a from-scratch six-panel layout under time constraints. Both edge types, direction semantics, and the redundant edge are preserved; this was a deliberate scope choice, not an oversight, and a later reader wanting the six-panel walkthrough would need a new plan, not a bug fix."
  - "Traversal replay sorts adjacency neighbours for both node types (the library's own camera-branch iteration is unsorted); verified by manual trace that neighbour order within one heap pop does not change which edges are discovered, only the order they're recorded in — a determinism convenience, not a behavioral divergence from the library."
  - "Glossary Pose graph entry rewritten wholesale (not surgically preserving 'via BFS traversal') using neutral phrasing 'Used in Stage 2 for extrinsic initialization', deferring the confirmed 'best-first' term to plan 18-08 per the plan's explicit instruction not to front-run the 18-02 checkpoint."
  - "Round-1 checkpoint failure (backwards arrows) was caught by the human-verify gate rather than by any automated check — file-existence and grep-guard tests cannot assert arrow direction, which is exactly why the plan specified a human check for this task. The gate worked as designed."

requirements-completed: [DOCS-03]

# Metrics
duration: ~70min (across two checkpoint rounds)
completed: 2026-07-24
---

# Phase 18 Plan 04: Pose Graph Regeneration Summary

**Replaced the hardcoded BFS pose-graph figure generator with one that derives its edges by replaying AquaCal's real priority-heap traversal, fixed a human-caught arrow-direction bug, and corrected the glossary's backwards pose-graph definition — human-approved "for now."**

## Performance

- **Duration:** ~70 min (two checkpoint rounds — round 1 caught a bug, round 2 approved)
- **Tasks:** 3 of 3 complete
- **Files modified:** 6 (1 created, 2 deleted, 3 modified)

## Accomplishments

- Replaced the hand-authored `bfs_pose_graph.py` (hardcoded `EDGES`/`BFS_EDGES` constants)
  with `pose_graph.py`, which builds a small 4-camera/3-frame `DetectionResult` fixture
  (corner counts taken from the paper supplement's own worked example), calls the real
  `aquacal.calibration.extrinsics.build_pose_graph`, and replays the priority-heap loop to
  derive which edges are discovery edges vs. redundant observation edges — so the figure
  cannot drift from the library's actual traversal.
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
  untouched — those remain plan 18-08's scope).
- Corrected `docs/guide/glossary.md`'s `Pose graph` definition to describe the real bipartite
  structure (camera nodes and frame nodes, an edge from each camera to each frame it
  observes), replacing the backwards "edges connect observations of the same board pose"
  text. Did not write "best-first" into the glossary (plan 18-02/18-08 scope).
- **Caught and fixed a real arrow-direction bug at the human-verify gate** (see "Checkpoint
  History" below) — exactly the class of defect a file-existence check cannot catch, which
  is why the plan specified a human check for this task.
- **Human approved the corrected figure**, with an explicit hedge: *"good catch. diagram
  looks good for now."* Recorded verbatim, not upgraded to an unqualified sign-off.

## Task Commits

1. **Task 1: Write the heap-replaying pose_graph.py generator and rewire generate_all.py** -
   `f93e0e8` (docs)
2. **Task 2: Regenerate the figure, delete the old PNG, and update its references** -
   `9ae1f55` (docs)
3. **Checkpoint round 1 fix: correct discovery-edge arrow direction** - `0be6b78` (docs)
4. **Partial summary updates during the checkpoint** - `1505d2b`, `fd1b856` (docs; superseded
   by this final summary)
5. **Task 3: Human visual verification** - approved, no code change required (see below)

## Files Created/Modified

- `docs/_static/scripts/pose_graph.py` - new heap-replaying generator (~310 lines)
- `docs/_static/scripts/bfs_pose_graph.py` - deleted
- `docs/guide/_diagrams/generate_all.py` - rewired import/call/print string
- `docs/_static/diagrams/pose_graph.png` - regenerated (new), human-verified after the round-1 fix
- `docs/_static/diagrams/bfs_pose_graph.png` - deleted
- `docs/guide/optimizer.md` - image directive + alt text updated (line ~73 only)
- `docs/guide/glossary.md` - `Pose graph` definition corrected (line ~34-35 only)

## Decisions Made

1. **Single-panel layout, not the paper supplement's six-panel port.** The plan explicitly
   allowed either under its discretion clause. A from-scratch six-panel port under time
   constraints carried two concrete risks the supplement source itself flagged: LaTeX
   `\textbf` in matplotlib titles (requires either mathtext-compatible markup or full usetex,
   neither confirmed working in this docs build) and figure-level-legend cropping under
   `bbox_inches="tight"` (the supplement's own code comments call this out as a trap it had
   to work around). The single panel preserves every semantic requirement — both edge types,
   direction, the redundant edge, numbered discovery order — at lower implementation risk.
   Documented here explicitly so a future reader does not mistake this for an oversight.
2. Sorted adjacency iteration in the replay for deterministic rendering — verified by manual
   trace that this does not change the discovery/redundant edge classification versus the
   library's own unsorted camera-branch order (every unvisited neighbour of a popped node is
   resolved in the same pass regardless of iteration order).
3. Glossary sentence rewritten wholesale with neutral "Used in Stage 2 for extrinsic
   initialization" phrasing rather than trying to surgically preserve a "via BFS traversal"
   fragment, per the plan's explicit fallback instruction — avoids front-running the 18-02
   vocabulary checkpoint.

## Checkpoint History

### Round 1 — FAILED (condition 2: arrow direction)

The human reviewed the first-round figure and reported condition 2 failed: three discovery
edges (F2→cam1, F3→cam2, F3→cam3) rendered backwards — every arrowhead pointed rightward
camera→frame regardless of which endpoint the traversal actually discovered from.

**Root cause:** `generate()` built `discovery_set` as a `frozenset` of each discovery pair
for membership testing. A `frozenset` is unordered, so it preserved *that* an edge was a
discovery edge but not *which direction* it was discovered in. The draw loop then always
called `_draw_edge(ax, node_pos[cam], node_pos[frame], ...)` — always camera→frame — for
every edge in `all_edges` (which is always stored as `(cam, frame)` independent of discovery
direction).

**Fix (commit `0be6b78`):** Added `discovery_direction`, a lookup from the same frozenset key
to the ordered `(from_node, to_node)` tuple that `_replay_traversal` already produced
correctly. The draw loop now looks up `discovery_direction[key]` for directed edges and draws
`src_pos -> dst_pos` from that ordered pair, falling back to `(cam, frame)` only for the
undirected redundant edge (which has no arrowhead and so no direction to get wrong). No
hardcoded edge list was introduced and the PNG was never hand-retouched — the fix corrected
the classification-to-rendering pipeline, preserving the "generated from the live traversal"
property the whole plan exists to guarantee.

**This is exactly what the human-verify gate is for.** File-existence checks, grep guards,
and `ruff check` all passed on the round-1 figure — none of them can assert arrow direction,
which is a semantic property of the rendering, not the presence of a string or a file. The
gate caught a real bug that no automated check in this plan's verification suite could have
caught.

### Round 2 — APPROVED

After the fix, all five visual conditions were re-confirmed:
1. 4 camera nodes + 3 frame nodes in two columns — unchanged, correct.
2. **Exactly 6 directed discovery edges, all pointing the correct direction** — cam0→F1,
   cam0→F2, cam1→F3 rightward (known camera → newly determined frame); F2→cam1, F3→cam2,
   F3→cam3 leftward (known frame → newly determined camera). This was the failing condition
   in round 1; confirmed fixed.
3. Exactly 1 undirected redundant edge (cam2–F1), grey, no arrowhead — unchanged, correct.
4. Every legend key corresponds to a drawn element — unchanged, correct.
5. Title reads "Stage 2: Pose Graph", no "BFS" text anywhere in the image — unchanged,
   correct.

**Human's approval, recorded verbatim:** *"good catch. diagram looks good for now."* This is
recorded as-is, including the "for now" hedge — not upgraded to an unqualified sign-off. If a
later plan revisits this figure (e.g. the 18-08 vocabulary lock, or any future six-panel
port), that hedge is the signal this was accepted as adequate for the current milestone, not
declared final.

**Cosmetic point raised and left as-is:** the figure carries a red inline annotation
"reference (R=I, t=0)" pointing at cam0, with no corresponding legend entry. The human was
shown this explicitly and did not ask for it to change — left as-is per instruction.

## Deviations from Plan

**1. [Rule 1 - Bug] Removed an unused local variable flagged by the ruff pre-commit hook**
- **Found during:** Task 1, first commit attempt
- **Issue:** `directed_lookup` dict was computed but never read (F841).
- **Fix:** Removed the dead assignment; `discovery_set`/`badge_lookup` already carried
  everything the render step needed at that point.
- **Files modified:** `docs/_static/scripts/pose_graph.py`
- **Verification:** `ruff check` passes; figure regenerated bit-identically before/after.
- **Committed in:** `f93e0e8`

**2. [Rule 1 - Bug] Docstring accidentally referenced the retired `bfs_pose_graph.py` filename**
- **Found during:** Task 1, acceptance-criteria self-check
- **Issue:** The module docstring's first draft said "Unlike the retired
  ``bfs_pose_graph.py``...", which violates the acceptance criterion that
  `grep -c "bfs_pose_graph" docs/_static/scripts/pose_graph.py` return 0.
- **Fix:** Reworded the docstring to describe the new behavior without naming the old file.
- **Files modified:** `docs/_static/scripts/pose_graph.py`
- **Verification:** `grep -c "bfs_pose_graph" docs/_static/scripts/pose_graph.py` returns 0.
- **Committed in:** `f93e0e8`

**3. [Rule 1 - Bug, caught at the human-verify gate] Discovery-edge arrow direction lost through an unordered frozenset key**
- **Found during:** Task 3, checkpoint round 1 (human visual review)
- **Issue:** Three of six discovery edges rendered with arrows pointing the wrong way; see
  "Checkpoint History — Round 1" above for full root-cause detail.
- **Fix:** Added an ordered `discovery_direction` lookup alongside the existing frozenset
  membership test; draw loop uses it for directed edges. See commit `0be6b78`.
- **Files modified:** `docs/_static/scripts/pose_graph.py`,
  `docs/_static/diagrams/pose_graph.png`
- **Verification:** Pixel-level crop inspection confirmed all six edges point the correct
  direction; `ruff check`, `sphinx-build -W --keep-going`, and
  `python -m pytest tests/ -m "not slow"` (775 passed / 31 deselected) all still pass; human
  re-reviewed and approved.
- **Committed in:** `0be6b78`

---

**Total deviations:** 3 auto-fixed (2 Rule 1 during Task 1's own acceptance checks, 1 Rule 1
caught at the Task 3 human-verify gate). No scope creep — all three were corrections to this
plan's own new code, not unrelated work.

## Issues Encountered

None beyond the three deviations documented above. The round-1 checkpoint failure was not an
"issue" in the problem-solving sense — it was the human-verify gate performing exactly its
intended function (catching a semantic rendering defect no automated check could assert).

## Self-Check Verification (final, after human approval)

- `ruff check docs/_static/scripts/pose_graph.py` — **All checks passed!**
- `sphinx-build -W --keep-going -b html docs docs/_build/html` — **build succeeded** (exit 0);
  `docs/_build/html/_static/diagrams/pose_graph.png` copied into the built site.
- `python -m pytest tests/ -m "not slow"` — **775 passed, 31 deselected**, no regressions (no
  files under `src/` were touched by this plan).
- File existence: `docs/_static/scripts/pose_graph.py` FOUND;
  `docs/_static/diagrams/pose_graph.png` FOUND; `docs/_static/scripts/bfs_pose_graph.py`
  CONFIRMED ABSENT; `docs/_static/diagrams/bfs_pose_graph.png` CONFIRMED ABSENT.
- Commit existence: `f93e0e8`, `9ae1f55`, `0be6b78`, `fd1b856` all FOUND in `git log --oneline
  --all`.

## Self-Check: PASSED

## User Setup Required

None — no external service configuration required.

## Next Phase Readiness

DOCS-03 is fully satisfied: the glossary's pose-graph definition describes the correct
bipartite structure, and the figure is regenerated from a script that replays the library's
own heap logic, with correct edge direction confirmed by the human. No hardcoded edge list
remains anywhere in the generator; the old filename is gone from the source tree with no
dual-file period. No checkpoint-gated DOCS-02/DOCS-06 wording was touched — plan 18-08 remains
free to make those edits once the 18-02 vocabulary checkpoint resolves.

---
*Phase: 18-documentation-corrections-stage-model-reconciliation*
*Completed: 2026-07-24*
