---
phase: 18-documentation-corrections-stage-model-reconciliation
plan: 08
subsystem: docs
tags: [sphinx, mermaid, huber-loss, stage-model, best-first, phase-gate]

# Dependency graph
requires:
  - phase: 18-documentation-corrections-stage-model-reconciliation
    provides: 18-02-SUMMARY.md (confirmed vocabulary contract) and 18-01/18-03/18-04's already-shipped edits to optimizer.md, guide/index.md, and troubleshooting.md
provides:
  - Every doc page and API reference on the three-stage / best-first model
  - The Huber loss name and formula matching schema.py's actual default
  - Closed-out DOCS-02 (BFS sweep) and DOCS-06 (Stage 4 rename) requirements
  - The completed phase gate: diagram regen, CI-equivalent Sphinx build, full test suite, grep guards, ruff, commit-type audit
affects: []

# Tech tracking
tech-stack:
  added: []
  patterns: []

key-files:
  created: []
  modified:
    - docs/guide/optimizer.md
    - docs/guide/glossary.md
    - docs/guide/index.md
    - docs/guide/troubleshooting.md
    - docs/api/calibration.rst
    - docs/api/index.rst
    - README.md
    - CLAUDE.md (local-only, gitignored, never committed)

key-decisions:
  - "D-04/D-05 applied verbatim per 18-02-SUMMARY.md: three stages, ex-Stage-4 demoted to a Stage 3 subsection titled around 'Stage 3's Second Pass'"
  - "D-08 applied: optimizer.md's loss section now names Huber and prints the Huber rho (quadratic below loss_scale=1.0px, linear above), replacing the mismatched soft-L1 label+formula"
  - "D-17 sweep confirmed by fresh grep at execution time, not just the plan's enumerated line list — no additional stray sites found beyond the plan's inventory"
  - "D-19 honored: CLAUDE.md edited locally only; git status --porcelain CLAUDE.md confirmed empty before and after the edit"
  - "D-18 honored: .planning/ and CHANGELOG.md untouched; git diff --name-only across this plan's 3 commits lists neither"

patterns-established: []

requirements-completed: [DOCS-02, DOCS-06]

# Metrics
duration: 35min
completed: 2026-07-24
---

# Phase 18 Plan 08: Doc Sweep, Loss Formula Correction, and Phase Gate Summary

**Rewrote `docs/guide/optimizer.md` onto the three-stage/Huber-loss model, swept the remaining doc/API/README/CLAUDE.md sites for stale four-stage and BFS language, collapsed troubleshooting.md's ten Stage 3/4 phrasings to Stage 3, and ran the full phase gate (806 tests passed, Sphinx build clean, both grep guards exact).**

## Performance

- **Duration:** ~35 min
- **Started:** 2026-07-24T16:03Z (approx.)
- **Completed:** 2026-07-24T16:38:33Z
- **Tasks:** 3
- **Files modified:** 8 (7 committed, 1 local-only/gitignored)

## Accomplishments
- `docs/guide/optimizer.md` fully restructured: three-stage mermaid diagram, three-stage prose, intrinsic refinement demoted to a `### Stage 3's Second Pass, with Intrinsics Unlocked (Optional)` subsection physically inside the Stage 3 section, "Why BFS?" retitled "Why best-first?" with its non-overlapping-FOV rationale paragraph preserved verbatim, and the loss section rewritten to name Huber and print the correct piecewise Huber rho with `loss_scale` (1.0 px) as the transition point, cross-linked to `docs/guide/configuration.md`.
- Remaining doc surfaces swept: `glossary.md` (Auxiliary camera Stages 2-4 → 2-3, Pose graph traversal term, See Also footer), `guide/index.md` (Four-stage → Three-stage bullet, completing D-16's second half), `api/calibration.rst` (four-stage prose, `Stage 4: Refinement` heading retitled without touching the `automodule` directive), `api/index.rst` (four-stage → three-stage), `README.md` (BFS-based → Best-first).
- `troubleshooting.md`: all ten `Stage 3/4` / `Stage 3 or 4` sites collapsed to `Stage 3`, including the YAML comment and two bold-emphasis occurrences; rewrote the one genuinely awkward heading-adjacent sentence rather than leaving a grammatical seam. `configuration.md` cross-links and `reject_outlier_frames` mentions confirmed unchanged (3 each).
- `CLAUDE.md`'s four-stage architecture block corrected locally to three-stage/best-first wording; confirmed gitignored both before and after the edit (`git status --porcelain CLAUDE.md` empty in both cases) and never staged or committed.
- Full phase gate executed and recorded (see Verification Results below).

## Task Commits

Each task was committed atomically:

1. **Task 1: Rewrite optimizer.md to the three-stage model and fix the loss formula** - `55d07fd` (docs)
2. **Task 2: Sweep the remaining doc pages, the API reference, README, and CLAUDE.md** - `8971c61` (docs) — CLAUDE.md's local-only edit is not part of this commit
3. **Task 3: Collapse troubleshooting's Stage 3/4 phrasings and run the phase gate** - `6376553` (docs)

_**Corrected 2026-07-24 after phase verification.** This originally claimed no `feat:` or
`fix:` commit appears in Phase 18. That claim was false: `34497f9 fix(18): repair
run_calibration_from_config docstring RST after wave 2` is an orchestrator-authored `fix:`
commit inside this phase. It is a docstring-only RST repair with no behavior change and was
mistyped — it should have been `docs(18):`. The `git log --oneline -20` window used to
"confirm" the original claim did not reach back far enough to include it._

_Release impact: none to the version. 22 unreleased `feat:` commits from Phases 16-17 already
force a minor bump to v1.9.0, and `575bdc8 fix(17-05)` means a "Bug Fixes" CHANGELOG section
exists regardless. The only cost is one misleading CHANGELOG line describing a docstring
repair as a bug fix. Left as-is rather than rewriting history through merge commits;
flagged for the user to decide._

_Every other Phase 18 commit is `docs:`/`refactor:`/`test:`/`chore:`._

## Files Created/Modified
- `docs/guide/optimizer.md` - three-stage mermaid + prose, Stage 3 second-pass subsection, corrected Huber loss formula, best-first terminology
- `docs/guide/glossary.md` - Stages 2-3, best-first traversal, three calibration stages
- `docs/guide/index.md` - "Three-stage calibration pipeline" bullet (completes D-16)
- `docs/guide/troubleshooting.md` - ten Stage 3/4 sites collapsed to Stage 3
- `docs/api/calibration.rst` - three-stage prose, "Stage 3's Second Pass: Refinement" heading (automodule directive untouched)
- `docs/api/index.rst` - three-stage calibration pipeline description
- `README.md` - "Best-first extrinsic initialization"
- `CLAUDE.md` - three-stage/best-first architecture block; **local-only, gitignored, never staged or committed**

## Decisions Made

No new decisions — this plan applied the vocabulary contract locked in `18-02-SUMMARY.md` and the scope boundaries fixed in `18-CONTEXT.md`/`18-VALIDATION.md`. See `key-decisions` above for the specific application points.

## Deviations from Plan

None - plan executed exactly as written. All three tasks matched their `<action>` specs; no Rule 1-4 triggers encountered.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Verification Results (Phase Gate)

All commands run from the repo root, in the order specified by the plan (`generate_all.py` standalone before the Sphinx build):

| Command | Result |
|---|---|
| `python docs/guide/_diagrams/generate_all.py` | Exit 0 — all 4 diagrams + hero image regenerated, no content changes (`git status --short docs/_static/diagrams/` empty) |
| `sphinx-build -W --keep-going -b html docs docs/_build/html` | Exit 0 — `build succeeded`, `docs/_build/html/guide/optimizer.html` renders 3 stage nodes (Stage 1 x9, Stage 2 x5, Stage 3 x11, Stage 4 x0) |
| `python -m pytest tests/` (full suite, slow included) | **806 passed**, 13 warnings, 282.81s — exceeds the ≥799 Phase 17 baseline |
| `ruff check` | `All checks passed!` |
| DOCS-02 grep guard: `grep -rniE "\bBFS\b\|breadth.first" src/ docs/ README.md --include=*.py --include=*.md --include=*.rst --include=*.yaml \| grep -v _build` | Exactly the two expected `extrinsics.py` lines (200, 208, inside `_find_connected_components`) — nothing else |
| DOCS-06 grep guard: `grep -rnE '"stage4"\|stage4_joint_refinement\|trace_stage4\|calibration_stage4\|Stage 4' src/ --include=*.py --include=*.yaml` | Zero matches |
| `git status --porcelain CLAUDE.md` | Empty (gitignored, never staged) |
| `git log v1.8.0..HEAD` | One `fix:` from Phase 18 (`34497f9`, mistyped docstring repair) — see correction above; no `feat:` |
| `git status --short` (post-commit) | Clean (CLAUDE.md's local edit doesn't appear, as expected) |

### Explicitly out of scope (unchanged, by design)
- `.planning/` and `CHANGELOG.md` — untouched historical records (D-18). Confirmed: none of this plan's 3 commits (`55d07fd`, `8971c61`, `6376553`) touch either path.
- `docs/tutorials/01_full_pipeline.ipynb` (lines 256, 276) and `docs/tutorials/02_synthetic_validation.ipynb` (lines 239, 249) — captured OUTPUT cells still show old "Stage 4" console strings. `nbsphinx_execute = "never"` means they don't re-execute during the docs build, so this is a silent-but-known gap, not a build failure. Regenerating requires a real 48-87 minute calibration run and is already escalated to the user / deferred to Phase 21 (DATA-03) per the plan's own scope note. Left untouched in this plan.
- `src/aquacal/calibration/extrinsics.py:200,208` (`_find_connected_components`) — genuinely FIFO BFS, correctly named, untouched.
- `docs/guide/optimizer.md`'s "98% sparse" claim, its `673`/`675`/`727` numbers, and its `diagrams/pose_graph.png` reference — all survived (positively verified by grep counts during Task 1).

## Next Phase Readiness

Phase 18 (Documentation Corrections & Stage-Model Reconciliation) is fully executed: every wave complete, the phase gate green, and both grep-guard requirements (DOCS-02, DOCS-06) satisfied exactly as specified. No blockers for phase completion. The known tutorial-notebook output drift is the only open scope item, and it is explicitly deferred (not a blocker) per this plan's own instructions.

## Self-Check: PASSED

All task commit hashes (`55d07fd`, `8971c61`, `6376553`) and the plan-metadata commit (`16468b1`) verified present in `git log`. `docs/guide/optimizer.md` and this SUMMARY.md verified present on disk.

---
*Phase: 18-documentation-corrections-stage-model-reconciliation*
*Completed: 2026-07-24*
