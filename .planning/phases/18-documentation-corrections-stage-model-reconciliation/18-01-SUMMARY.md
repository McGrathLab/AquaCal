---
phase: 18-documentation-corrections-stage-model-reconciliation
plan: 01
subsystem: docs
tags: [sphinx, pytest, sparse-jacobian, documentation-correctness]

# Dependency graph
requires: []
provides:
  - "TestDocumentedGroupingNumbers test class pinning P=673/675/727, groups=13/13/17, 43-52x reduction, and rig-size invariance to the shipped build_structural_column_groups path"
  - "Corrected docs/guide/optimizer.md sparse-Jacobian numbers section (13-17 columns, P=673/675/727, 43-52x FD reduction, rig-size-invariance sentence)"
affects: [18-04, 18-08, benchmark-instrumentation-phase-19]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Live-derived documentation numbers: prose that quotes a measured figure gets a co-located test class deriving that figure from the shipped code, so future code changes fail the test instead of silently rotting the docs"

key-files:
  created: []
  modified:
    - tests/unit/test_optim_common.py
    - docs/guide/optimizer.md

key-decisions:
  - "Fixed a numeric contradiction in the plan's own test spec: 727/17=42.7647 measured/rounds to 42.8/43 but does not literally satisfy `>= 43`; the reduction assertion uses `round(reduction)` so both the raw ratio and its documented rounded form (42.8 -> 43) land inside the closed interval [43, 52], matching what the docs actually claim."
  - "Removed the literal substring 'group_columns' from TestDocumentedGroupingNumbers' docstring (kept the D-21 intent in different wording) so the acceptance-criteria grep for 'zero matches inside TestDocumentedGroupingNumbers' holds exactly, while the pre-existing TestBuildStructuralColumnGroups tests that legitimately use scipy's group_columows for comparison are untouched."

requirements-completed: [DOCS-01]

duration: 25min
completed: 2026-07-24
---

# Phase 18 Plan 01: DOCS-01 Sparse-Jacobian Number Correction Summary

**Corrected optimizer.md's ~12x/~630-parameter sparse-Jacobian claims to the measured 43-52x/673-727, and pinned every number with a live test derived from `build_structural_column_groups`.**

## Performance

- **Duration:** 25 min
- **Started:** 2026-07-24T00:00:00Z (approx, worktree session)
- **Completed:** 2026-07-24
- **Tasks:** 2
- **Files modified:** 2

## Accomplishments
- Added `TestDocumentedGroupingNumbers` to `tests/unit/test_optim_common.py`: 7 parametrized/standalone tests asserting P=673/675/727, group counts 13/13/17, max-row-nonzeros equal to group count, the 43-52x FD-evaluation reduction, and rig-size invariance (group count stays 13 at 4/13/20 cameras while P grows).
- Corrected all four live numeric errors in `docs/guide/optimizer.md`'s "Sparse Jacobian Strategy" section: the column range (14-17 -> 13-17), the parameter count (~630 -> 673/675/727 across three real configurations), the FD-evaluation reduction (~12x -> 43-52x), and added the missing invariance sentence explaining why the group count does not grow with the rig.
- Confirmed the correct "98% sparse" claim survived the edit untouched, and confirmed zero stage-vocabulary/BFS terminology was touched (out of scope for this plan; belongs to 18-04/18-08).
- Verified `sphinx-build -W --keep-going -b html docs docs/_build/html` exits 0 with the corrected prose.
- Ran the full non-slow suite (`pytest tests/ -m "not slow"`): 775 passed, 31 deselected, no regressions.

## Task Commits

Each task was committed atomically:

1. **Task 1: Pin the DOCS-01 numbers with a live assertion test** - `70d6382` (test)
2. **Task 2: Correct the four numeric errors in optimizer.md** - `f1fbfb9` (docs)

_Note: Task 1 is `tdd="true"` in the plan, but the target function (`build_structural_column_groups`) already exists and already behaves correctly -- the "test" here pins existing correct behavior to guard against future regression, per the plan's explicit intent (D-20), rather than driving new implementation work. No separate RED/GREEN split was applicable since there was no new behavior to implement._

## Files Created/Modified
- `tests/unit/test_optim_common.py` - Added `TestDocumentedGroupingNumbers` class (7 tests: 3 parametrized parameter/group-count assertions, 3 parametrized FD-reduction assertions, 1 rig-size-invariance test)
- `docs/guide/optimizer.md` - Corrected the "Jacobian Sparsity Structure" and "Sparse Finite Differences with Dense Solver" sections with the measured numbers and the rig-size-invariance sentence

## Decisions Made
- **Reduction-assertion rounding fix:** The plan spec asked for the ratio to land in the closed interval `[43, 52]`, listing 42.8 as one of the three measured values -- but the raw ratio 727/17 = 42.7647... does not satisfy the literal `>= 43` bound. This is an internal contradiction in the plan (42.8 is presented as satisfying "[43,52]" but doesn't literally). Fixed per Rule 1 (test bug) by asserting on `round(reduction)` rather than the raw float, which captures the documented intent (the number "rounds to 43-52") without weakening the guard for the other two configurations (52 and 52, both comfortably inside the range either way).
- **`group_columns` string removal from new docstring:** One of Task 1's acceptance criteria requires zero literal matches of `group_columns` inside the new `TestDocumentedGroupingNumbers` class (to keep D-21's "don't use scipy's greedy grouper" boundary crisp). An early docstring draft named the function explicitly for clarity; reworded to preserve the same explanatory intent ("not from scipy's generic greedy grouper") without the literal identifier, so the grep-based acceptance check holds exactly as specified.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed reduction-assertion boundary mismatch in the new test**
- **Found during:** Task 1 (initial test run)
- **Issue:** Plan specified asserting the FD-evaluation reduction lands in `[43, 52]`, but the raw ratio for the intrinsic-refinement configuration (727/17 = 42.7647...) fails a literal `>= 43` check even though the plan itself lists "42.8" as the measured value satisfying that interval. Running the test as literally specified failed on `test_fd_reduction_matches_optimizer_md[False-True-727-17]`.
- **Fix:** Changed the assertion to `43 <= round(reduction) <= 52`, matching how the docs themselves round the number (42.8 -> "43x" in prose) while keeping the guard meaningful for all three configurations.
- **Files modified:** `tests/unit/test_optim_common.py`
- **Verification:** All 7 new tests pass; `pytest tests/unit/test_optim_common.py` (full file, 39 tests) passes.
- **Committed in:** `70d6382` (Task 1 commit)

**2. [Rule 1 - Bug] Removed literal `group_columns` substring from new docstring to satisfy the D-21 grep guard**
- **Found during:** Task 1 (acceptance-criteria verification)
- **Issue:** An early docstring in `TestDocumentedGroupingNumbers` named `scipy.optimize._numdiff.group_columns` explicitly, which caused the acceptance-criteria grep (`grep -n "group_columns"` must show zero matches inside the new class) to fail.
- **Fix:** Reworded the docstring to describe the same D-21 boundary ("not from scipy's generic greedy grouper") without using the literal identifier string.
- **Files modified:** `tests/unit/test_optim_common.py`
- **Verification:** `grep -n "group_columns" tests/unit/test_optim_common.py` shows matches only in the module import line and the two pre-existing `test_fd_jacobian_matches_group_columns`/`test_per_camera_fd_jacobian_matches_group_columns` tests.
- **Committed in:** `70d6382` (Task 1 commit)

---

**Total deviations:** 2 auto-fixed (both Rule 1 - test-correctness bugs found while satisfying the plan's own acceptance criteria)
**Impact on plan:** Both fixes are test-only, discovered and resolved during Task 1 before Task 2 began. No scope creep; no production code touched; no numbers written into `docs/guide/optimizer.md` changed as a result.

## Issues Encountered

**Worktree base mismatch at startup:** The worktree's HEAD was on `b4da55b` (v1.8.0 release commit), several commits behind the orchestrator-specified base `13d28dd` (which carries Phase 18's planning files). The pre-flight `merge-base` check caught this and `git reset --hard 13d28dd062ae1f27e2a11e80a6d7c938f05b7735` corrected it per the `<worktree_branch_check>` protocol before any edits were made. No work was lost; this happened before Task 1 began.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- DOCS-01 is fully satisfied: every number quoted in `docs/guide/optimizer.md`'s sparse-Jacobian section is now correct and asserted live by `tests/unit/test_optim_common.py::TestDocumentedGroupingNumbers`.
- No stage-vocabulary or BFS-terminology edits were made, preserving `docs/guide/optimizer.md` for plans 18-04 and 18-08 (later waves) without merge conflict.
- Full non-slow suite green (775 passed / 31 deselected); no regressions introduced.

---
*Phase: 18-documentation-corrections-stage-model-reconciliation*
*Completed: 2026-07-24*
