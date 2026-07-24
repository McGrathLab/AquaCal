---
phase: 19-benchmark-instrumentation
plan: 01
subsystem: calibration
tags: [scipy, least_squares, observability, dataclass, unit-testing]

# Dependency graph
requires: []
provides:
  - "SolverDiagnostics dataclass (14 fields) as a mutable out-parameter in _observability.py"
  - "capture_solver_diagnostics() helper that populates a SolverDiagnostics from a returned OptimizeResult"
  - "D-15 null-with-reason convention implemented for n_params/n_groups"
  - "njev correctly documented as populated int for method='trf', None only for method='lm'"
affects: [19-02-plan, 19-03-plan]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Mutable out-parameter dataclass (mirrors TraceRow) populated by a pure capture helper, never returned via a function's public return tuple"
    - "No-op-when-None out-parameter: capture_solver_diagnostics(result, None, ...) is a safe no-op so every call site can call it unconditionally"

key-files:
  created:
    - none (both files pre-existed; only extended)
  modified:
    - src/aquacal/calibration/_observability.py
    - tests/unit/test_observability.py

key-decisions:
  - "SolverDiagnostics and capture_solver_diagnostics are NOT added to aquacal.calibration.__init__'s __all__, matching the existing OptimizerObserver precedent (private-module helpers used only as trailing keyword parameters)"
  - "njev docstrings scope the None case strictly to method='lm'; the dataclass and helper never claim None means jac='2-point', correcting the original (now-fixed) research pitfall"

requirements-completed: [BENCH-01]

# Metrics
duration: 25min
completed: 2026-07-24
---

# Phase 19 Plan 01: Solver Diagnostics Contract Summary

**Added the `SolverDiagnostics` dataclass and `capture_solver_diagnostics()` helper to `_observability.py` as the interface-first contract Plans 19-02/19-03 will wire into the four in-scope `least_squares` call sites, with njev correctly documented as always-populated for `method='trf'`.**

## Performance

- **Duration:** 25 min
- **Started:** 2026-07-24T00:00:00Z (approx, see git log)
- **Completed:** 2026-07-24
- **Tasks:** 2
- **Files modified:** 2

## Accomplishments
- `SolverDiagnostics` dataclass: 14 fields (`nfev`, `njev`, `cost`, `optimality`, `status`, `message`, `ftol`, `xtol`, `gtol`, `max_nfev_effective`, `max_nfev_source`, `n_params`, `n_params_reason`, `n_groups`, `n_groups_reason`), all defaulting to `None`, constructible with zero or all arguments
- `capture_solver_diagnostics(result, diagnostics_out, *, ftol, xtol, gtol, max_nfev_effective, max_nfev_source, n_params=None, n_groups=None, n_params_reason=None, n_groups_reason=None)`: mutates `diagnostics_out` in place, no-op when `diagnostics_out is None`, casts every numpy scalar field to native Python `int`/`float`
- `njev` read defensively via `getattr(result, "njev", None)` but documented (dataclass + helper docstrings, both directions) as always a populated `int` at this codebase's four in-scope `method='trf'` call sites — `None` occurs only for `method='lm'`, which no in-scope site uses
- `TestCaptureSolverDiagnostics` (6 new tests) covering: no-op with `diagnostics_out=None`, native-type casting from numpy scalars, the defensive missing-`njev`-attribute case (explicitly documented as generic-robustness only, not a `jac='2-point'` claim), tolerances/`max_nfev` recorded verbatim, and the D-15 null-with-reason convention for `n_params`/`n_groups` both populated and absent

## Task Commits

Each task was committed atomically:

1. **Task 1: Define the SolverDiagnostics dataclass contract** - `ff43bc1` (feat)
2. **Task 2: Implement capture_solver_diagnostics() and test it** - `8400c33` (feat)

**Plan metadata:** (this commit, appended after SUMMARY.md is written)

## Files Created/Modified
- `src/aquacal/calibration/_observability.py` - Added `SolverDiagnostics` dataclass (after `TraceRow`) and `capture_solver_diagnostics()` module-level function (after `build_parameter_labels`, before `OptimizerObserver`)
- `tests/unit/test_observability.py` - Added `TestCaptureSolverDiagnostics` class with 6 tests; added `types`, `SolverDiagnostics`, `capture_solver_diagnostics` imports

## Decisions Made
- Followed the plan's explicit instruction that `SolverDiagnostics`/`capture_solver_diagnostics` must NOT be exported via `aquacal/calibration/__init__.py`'s `__all__`, matching the existing `OptimizerObserver` precedent (verified `OptimizerObserver` is absent from `__all__` before writing).
- Placed `capture_solver_diagnostics` between `build_parameter_labels` and `OptimizerObserver` (plan specified `SolverDiagnostics`'s placement after `TraceRow`/before `build_parameter_labels`, but was silent on the helper's exact placement; chosen location keeps related dataclass+helper physically adjacent to their downstream consumer class without disturbing the existing `TraceRow` → `build_parameter_labels` ordering the plan pinned).

## Deviations from Plan

None - plan executed exactly as written. `tests/unit/test_observability.py` already existed (from the Phase 16/17 `OptimizerObserver` work); the plan anticipated this ("a new `TestCaptureSolverDiagnostics` class if the file already exists") and that is exactly what was done.

## Issues Encountered

**Worktree base was stale at spawn time.** `git merge-base HEAD 8fdb652942d59f75fd56a1784a2f0f7ea0ee8d6e` returned `b4da55b132722d4b061a832fc7cabe7b9f3c4b62` (the v1.8.0 release commit), not the expected `8fdb652942d59f75fd56a1784a2f0f7ea0ee8d6e` (the phase-19-execution-start marker). Corrected per the mandatory `worktree_branch_check` step via `git reset --hard 8fdb652942d59f75fd56a1784a2f0f7ea0ee8d6e` before any edit. Confirmed `HEAD` landed on the expected commit before proceeding.

**Editable install resolves to the main repo, not the worktree.** `pip show aquacal` reports `Editable project location: C:\Users\tucke\PycharmProjects\AquaCal` (no worktree-specific `.pth`), so bare `python -c "import aquacal..."` and bare `pytest` from inside the worktree silently exercised the main repo's `src/aquacal`, not this worktree's edits. Worked around by exporting `PYTHONPATH="$(pwd)/src"` (worktree root) for every verification command in this plan, which the `sys.path` inspection confirmed correctly resolves imports to the worktree's own `_observability.py`. This is an environment quirk, not a plan/code defect — flagging here in case Plans 19-02/19-03 hit the same thing.

## User Setup Required

None - no external service configuration required.

## Verification Results

- `python -m pytest tests/unit/test_observability.py -q` (with worktree `PYTHONPATH`): **32 passed** (26 pre-existing + 6 new `TestCaptureSolverDiagnostics` tests)
- `python -m pytest tests/ -m "not slow" -q`: **781 passed, 31 deselected** (baseline was 775 passed / 31 deselected; +6 matches the 6 new tests added, zero regressions)
- `ruff check src/aquacal/calibration/_observability.py tests/unit/test_observability.py`: **All checks passed!**
- `python -m sphinx -W --keep-going -b html docs docs/_build/html`: **build succeeded**, zero warnings — `_observability.py`'s new docstrings (including the corrected njev scoping) render cleanly through autodoc

## Self-Check: PASSED

## Next Phase Readiness

`from aquacal.calibration._observability import SolverDiagnostics, capture_solver_diagnostics` is available for Plans 19-02 and 19-03 to wire into the four in-scope `least_squares` call sites (`interface_estimation.py:337`, `interface_estimation.py:672`, `refinement.py:237`, `point_refinement.py:674`) without further contract changes. No blockers.

---
*Phase: 19-benchmark-instrumentation*
*Completed: 2026-07-24*
