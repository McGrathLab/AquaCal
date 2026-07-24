---
phase: 19-benchmark-instrumentation
plan: 03
subsystem: calibration
tags: [scipy, least_squares, observability, dataclass, unit-testing, refinement]

# Dependency graph
requires:
  - phase: 19-benchmark-instrumentation
    plan: 01
    provides: "SolverDiagnostics dataclass and capture_solver_diagnostics() helper in _observability.py"
provides:
  - "joint_refinement(diagnostics_out=...) trailing keyword parameter, wired to capture_solver_diagnostics"
  - "joint_refinement passes ftol=1e-8, xtol=1e-8, gtol=1e-8 explicitly to least_squares (BENCH-06, bit-exact)"
  - "RefinementResult.solver_diagnostics field (default None, additive)"
  - "refine_calibration unconditionally populates RefinementResult.solver_diagnostics"
affects: [19-05-plan, 19-06-plan]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "diagnostics_out trailing keyword out-parameter threaded through a function's existing signature, never added to a positional return tuple (mirrors observer= convention already established in refinement.py)"
    - "TYPE_CHECKING-guarded cross-module import (config.schema -> calibration._observability) to avoid a load-time circular import, relying on the module's existing `from __future__ import annotations`"

key-files:
  created: []
  modified:
    - src/aquacal/calibration/refinement.py
    - src/aquacal/calibration/point_refinement.py
    - src/aquacal/config/schema.py
    - tests/unit/test_refinement.py
    - tests/unit/test_point_refinement.py

key-decisions:
  - "Captured the groups array from build_structural_column_groups into a named local variable (previously inlined directly into make_sparse_jacobian_func's call) so joint_refinement's diagnostics capture can read groups.max()+1 without re-deriving it"
  - "point_refinement.py's gtol is recorded from the fixed literal 1e-8 (SciPy's own implicit default) rather than added as an explicit least_squares kwarg -- per D-11/D-17 this site is NOT a BENCH-06 target, so only its ftol/xtol (already explicit, untouched) and the SciPy-default gtol are honestly reported"
  - "n_groups is recorded as None with a reason at the point_refinement.py site (it passes no groups= argument to make_sparse_jacobian_func, so it falls back to SciPy's generic group_columns() colorer, not the structural grouping used by joint_refinement/optimize_interface)"

requirements-completed: [BENCH-01, BENCH-03, BENCH-06]

# Metrics
duration: 45min
completed: 2026-07-24
---

# Phase 19 Plan 03: Wire Solver Diagnostics into joint_refinement and refine_calibration Summary

**Wired Plan 19-01's `SolverDiagnostics`/`capture_solver_diagnostics` contract into `joint_refinement` (Stage 3's second pass, with explicit `ftol=xtol=gtol=1e-8` proven bit-exact) and `refine_calibration` (diagnostics surfaced on `RefinementResult.solver_diagnostics`, never in `benchmark.json`, per D-14).**

## Performance

- **Duration:** ~45 min
- **Started:** 2026-07-24T16:53:00-04:00 (approx, first commit at 16:58)
- **Completed:** 2026-07-24T17:04:00-04:00
- **Tasks:** 2
- **Files modified:** 5

## Accomplishments
- `joint_refinement` gained a trailing `diagnostics_out: SolverDiagnostics | None = None` parameter, populated via `capture_solver_diagnostics` immediately after the existing `result.status <= 0` convergence check
- `joint_refinement`'s `least_squares` call now passes `ftol=1e-8, xtol=1e-8, gtol=1e-8` explicitly (SciPy's own current defaults); a new bit-exact regression test proves `result.x`-derived outputs (extrinsics, distances, board poses, intrinsics, rms_error) are identical with vs. without `diagnostics_out` + explicit tolerances, for both `use_sparse_jacobian=True` and `use_sparse_jacobian=False`
- `RefinementResult` gained a `solver_diagnostics: SolverDiagnostics | None = None` final field, added via a `TYPE_CHECKING`-guarded import to avoid a `config.schema <-> calibration._observability` circular import
- `refine_calibration` now unconditionally captures diagnostics from its own `least_squares` call and attaches them to every `RefinementResult` it returns, with `max_nfev_source` correctly branched across all three cases (`"explicit"`, `"point_refinement_200x_auto"`, `"scipy_auto"`) and `n_groups` honestly recorded as `None` with a reason (this site uses SciPy's generic `group_columns()` colorer, not the structural grouping `joint_refinement`/`optimize_interface` use)
- `njev` is asserted as a populated `int` (never `None`) in new tests at both call sites, confirming both use `method="trf"`

## Task Commits

Each task was committed atomically:

1. **Task 1: joint_refinement — explicit tolerances + diagnostics capture + bit-exact test** - `7829607` (feat)
2. **Task 2: RefinementResult.solver_diagnostics + refine_calibration wiring** - `3dece3e` (feat)

**Plan metadata:** (this commit, appended after SUMMARY.md is written)

## Files Created/Modified
- `src/aquacal/calibration/refinement.py` - `joint_refinement` gains `diagnostics_out` parameter, explicit `ftol/xtol/gtol`, `capture_solver_diagnostics` call; `groups` array captured to a named local for `n_groups` derivation
- `src/aquacal/calibration/point_refinement.py` - `refine_calibration` builds a local `SolverDiagnostics()`, calls `capture_solver_diagnostics` after `least_squares` (before the existing non-convergence warning), passes `solver_diagnostics=diag` into both `RefinementResult(...)` construction sites (validated and unvalidated paths); `point_refinement.py`'s existing `ftol`/`xtol`/200x `max_nfev` logic is untouched (D-17)
- `src/aquacal/config/schema.py` - `RefinementResult` gains `solver_diagnostics: SolverDiagnostics | None = None` as its final field, via a `TYPE_CHECKING`-guarded import
- `tests/unit/test_refinement.py` - New `TestJointRefinementDiagnostics` class: bit-exact regression test (parametrized over `use_sparse_jacobian`) plus a `diagnostics_out=None` safety test
- `tests/unit/test_point_refinement.py` - New `TestSolverDiagnostics` class: unconditional population, `gtol` recorded as SciPy's default, `n_groups_reason` content, and all three `max_nfev_source` branches

## Decisions Made
- Used `TYPE_CHECKING`-guarded import for `SolverDiagnostics` in `schema.py` per the plan's explicit fallback instruction, rather than attempting the direct top-level import first. Verified this was the correct call: a direct top-level `from aquacal.calibration._observability import SolverDiagnostics` at module scope in `schema.py` would trigger `aquacal.calibration/__init__.py`, which imports `pipeline.py`, which imports back `from aquacal.config.schema import (...)` while `schema.py` is still mid-initialization -- a real circular import, not just a theoretical one. `python -c "import aquacal"` was run to confirm the guarded version resolves cleanly.
- Named the `groups` local variable in `joint_refinement` (previously the `build_structural_column_groups(...)` call was inlined directly as the `groups=` keyword argument to `make_sparse_jacobian_func`) so the post-solve diagnostics capture can read `groups.max()+1` without re-invoking the builder. Zero behavior change -- same array, just bound to a name first.

## Deviations from Plan

None - plan executed exactly as written, including the explicit `TYPE_CHECKING` fallback the plan anticipated for the `config.schema <-> calibration._observability` import edge (T-19-03c), which was in fact required.

## Issues Encountered

**Worktree base was stale at spawn time (same class of issue as Plan 19-01).** `git merge-base HEAD e1652d27605e285a5e370f3301a86e3e3be9e371` returned `b4da55b132722d4b061a832fc7cabe7b9f3c4b62` (the v1.8.0 release commit) instead of the expected phase-19-execution-start marker. Corrected via the mandatory `worktree_branch_check` step (`git reset --hard e1652d27605e285a5e370f3301a86e3e3be9e371`, working tree was clean at the time) before any edit. Confirmed `HEAD` landed on the expected commit before proceeding.

**Editable install resolves to the main repo, not the worktree (same as Plan 19-01).** Worked around by exporting `PYTHONPATH="$(pwd)/src"` for every verification command; confirmed via `python -c "import aquacal.calibration.refinement as m; print(m.__file__)"` that imports correctly resolved to this worktree's own files, not the main checkout's.

**One test assertion had to be corrected against the plan's own logic.** My first draft of `test_solver_diagnostics_max_nfev_source_scipy_auto` asserted `max_nfev_effective is None`, but the plan's action explicitly specifies `max_nfev_effective=effective_max_nfev if effective_max_nfev is not None else n_params * 100` -- meaning the *recorded* diagnostic value is always the computed SciPy auto-formula (`n_params * 100`), even though the value *passed to* `least_squares` (`effective_max_nfev`) stays `None` in the scipy_auto branch. Fixed the test assertion to expect `n_params * 100`; this matches D-17's requirement that `max_nfev`'s "effective auto value" be recorded, not the raw unset value.

## User Setup Required

None - no external service configuration required.

## Verification Results

All commands run with `PYTHONPATH="$(pwd)/src"` set; import path confirmed inside the worktree before verification (`python -c "import aquacal.calibration.refinement as m; print(m.__file__)"` printed the worktree path, not the main checkout).

- `python -m pytest tests/unit/test_refinement.py tests/unit/test_point_refinement.py -q`: **54 passed**
- `python -c "import aquacal"`: exits 0 (no circular-import regression from the `schema.py` change)
- `python -m pytest tests/ -m "not slow" -q`: **807 passed, 31 deselected** (wave-2 baseline was 798 passed / 31 deselected; +9 matches the 3 new `test_refinement.py` tests + 6 new `test_point_refinement.py` tests, zero regressions)
- `ruff check src/aquacal/calibration/refinement.py src/aquacal/calibration/point_refinement.py src/aquacal/config/schema.py tests/unit/test_refinement.py tests/unit/test_point_refinement.py`: **All checks passed!**
- `python -m sphinx -W --keep-going -b html docs docs/_build/html`: **build succeeded**, zero warnings

## Self-Check: PASSED

## Next Phase Readiness

`joint_refinement(diagnostics_out=...)` and `refine_calibration(...).solver_diagnostics` are both available for downstream plans (BENCH-04's `benchmark.json` writer will consume `joint_refinement`'s diagnostics via the pipeline; `refine_calibration`'s diagnostics stay on its own result object per D-14 and are not expected to feed `benchmark.json`). No blockers. The remaining two D-07 in-scope call sites (`interface_estimation.py:337`, `interface_estimation.py:672`) are Plan 19-02's responsibility, not this plan's.

---
*Phase: 19-benchmark-instrumentation*
*Completed: 2026-07-24*
