---
phase: quick-3
plan: 01
subsystem: optimization
tags: [finite-differences, jacobian, sparsity, column-grouping, scipy, bundle-adjustment]

# Dependency graph
requires:
  - phase: P.3
    provides: Sparse Jacobian via custom jac callable with sparsity=(pattern, groups)
provides:
  - build_structural_column_groups() deriving an optimal FD column grouping from the parameter layout
  - Optional groups= parameter on make_sparse_jacobian_func (defaults to group_columns)
  - Stage 3 and Stage 4 always run at the theoretical minimum group count (13 / 17)
affects: [performance, memory-reduction, stage-3-optimization, stage-4-refinement]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "A priori structural graph coloring in place of scipy's generic greedy colorer"
    - "Length assertion tying a derived layout to its source-of-truth builder"

key-files:
  created: []
  modified:
    - src/aquacal/calibration/_optim_common.py
    - src/aquacal/calibration/refinement.py
    - src/aquacal/calibration/interface_estimation.py
    - tests/unit/test_optim_common.py

key-decisions:
  - "groups= defaults to None so point_refinement.py keeps the group_columns path unchanged"
  - "Tilt params reuse extrinsic group slots 0 and 1 rather than taking their own"
  - "Compact raw group ids via np.unique(return_inverse=True) so degenerate configs stay contiguous"
  - "Assert the derived column count against jac_sparsity.shape[1] so a layout change fails loudly"

patterns-established:
  - "build_structural_column_groups is kept physically adjacent to build_jacobian_sparsity because they must agree on column order"
  - "Grouping-validity tests assert the pattern property (no shared row per group), not a hardcoded grouping"

requirements-completed: [QUICK-3]

# Metrics
duration: 11min
completed: 2026-07-23
---

# Quick Task 3: Structural FD Column Grouping Summary

**Replaced SciPy's greedy column colorer with a grouping derived from the known parameter layout, cutting the joint bundle adjustment to its theoretical minimum of 13 finite-difference groups (17 with intrinsic refinement) at any camera visibility.**

## Performance

- **Duration:** 11 min
- **Started:** 2026-07-23T13:59:05Z
- **Completed:** 2026-07-23T14:10:08Z
- **Tasks:** 2
- **Files modified:** 4

## Accomplishments

- `build_structural_column_groups()` assigns each parameter column a group from the
  layout directly: extrinsic column `j` gets `j % 6`, board-placement column `j` gets
  `7 + (j % 6)`, `water_z` gets its own slot, intrinsic column `j` gets `13 + (j % 4)`,
  and tilt reuses extrinsic slots 0/1 (safe because tilt appears only in reference-camera
  rows and the reference camera has no extrinsic columns).
- `make_sparse_jacobian_func` gained an optional `groups` parameter defaulting to `None`,
  preserving the `group_columns` path for `point_refinement.py`, which uses a different
  (point-correspondence) sparsity structure where the layout argument does not apply.
- Measured at 12 cameras / 60 frames / 0.72 visibility: greedy produced 16 groups (base)
  and 20 groups (tilt + intrinsics) against a lower bound of 13 and 17. The structural
  grouping hits 13 and 17 exactly — 3 fewer full residual evaluations per Jacobian in the
  configuration used for real-rig runs.
- Test suite asserts the safety-critical property directly: no group contains two columns
  sharing a residual row, at visibility 1.0 / 0.7 / 0.4 in both configurations. An invalid
  grouping silently yields a *wrong* Jacobian rather than raising, so this is the guard for
  the whole change.

## Task Commits

1. **Task 1: Add build_structural_column_groups and thread it through both call sites** - `3c8685c` (perf)
2. **Task 2: Test validity, equivalence, and group count** - `a0df1c7` (test)

## Files Created/Modified

- `src/aquacal/calibration/_optim_common.py` - Added `build_structural_column_groups()`
  immediately after `build_jacobian_sparsity()` (the two must agree on column order);
  added `groups: NDArray[np.intp] | None = None` to `make_sparse_jacobian_func`.
- `src/aquacal/calibration/refinement.py` - Stage 4 passes the structural grouping with
  its local `refine_intrinsics` / `normal_fixed`.
- `src/aquacal/calibration/interface_estimation.py` - Stage 3 passes the structural
  grouping with `refine_intrinsics=False` (this stage never refines intrinsics).
- `tests/unit/test_optim_common.py` - Added `TestBuildStructuralColumnGroups` (10 tests)
  plus `_make_detections` / `_make_pattern` / `_patterned_residuals` helpers.
  `TestMakeSparseJacobianFunc` untouched.

## Decisions Made

- **`groups=None` default rather than always-structural.** `point_refinement.py:665`
  builds a point-correspondence sparsity pattern, not a board-observation one, so the
  layout-derived grouping would be wrong there. Defaulting to `None` keeps that call site
  bit-for-bit unchanged without needing to touch it.
- **Compaction via `np.unique(..., return_inverse=True)[1]`.** SciPy requires group ids
  `0..m-1`. Degenerate configs leave gaps in the raw ids (`n_cams == 1` produces no
  extrinsic columns, so raw ids 0-5 are never assigned). `np.unique` returns contiguous
  ids ordered by raw value, which is exactly the renumbering needed. Covered by a
  dedicated test.
- **Length assertion instead of silent trust.** The function reconstructs a layout owned
  by `build_jacobian_sparsity`. Taking `jac_sparsity` as the first argument (mirroring
  `group_columns(jac_sparsity)`) lets the length check live inside the function, so a
  future parameter-layout change trips an `AssertionError` naming both counts rather than
  producing a wrong Jacobian.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

- `ruff format` reflowed the `_make_pattern` signature after the test file was written;
  ran the formatter and re-verified. An em-dash in one test comment was replaced with
  ASCII `--` to match the surrounding source style.

## Verification

All four plan-level verification steps pass:

1. Full unit suite: **646 passed** (`python -m pytest tests/unit/ -q`). The 12 warnings are
   the pre-existing fronto-parallel intrinsics warnings already tracked in STATE.md pending
   todos — unrelated to this change.
2. Synthetic pipeline: **34 passed** in 5m13s (`python -m pytest tests/synthetic/ -q`).
   No accuracy regression, as expected for an output-neutral change.
3. `git diff --stat` lists exactly the four files in `files_modified`.
   `point_refinement.py` is unmodified.
4. Lint clean: `ruff check src/ tests/` and `ruff format --check src/ tests/` both pass.

Equivalence was verified numerically as well: `approx_derivative` with the structural
grouping and with `group_columns` produce bit-identical Jacobians (`rtol=0, atol=0`) on a
nonlinear residual honoring the sparsity pattern. This confirms the change alters only how
FD perturbations are batched, not any calibration output.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Committed as `perf:`, so python-semantic-release will cut a patch release on the next
  push to `main`. No manual version or CHANGELOG edit was made.
- The supplement's §5.2 claim of 13 / 17 evaluations is now true of the shipped code on
  realistic visibility patterns, not just as mathematics.
- Relates to the standing "reduce memory and CPU load during calibration" todo: this
  trims ~15-23% of residual evaluations per Jacobian, but the dense `.toarray()` Jacobian
  remains the suspected driver of the ~3.6 GB Stage 3 peak. That is untouched here.

## Self-Check: PASSED

All four modified files exist on disk. Both task commits (`3c8685c`, `a0df1c7`) are present
in `git log`. `git show --stat 3c8685c` confirms Task 1 touched exactly the three source
files claimed.

---
*Phase: quick-3*
*Completed: 2026-07-23*
