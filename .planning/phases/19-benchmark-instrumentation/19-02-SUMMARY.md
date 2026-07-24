---
phase: 19-benchmark-instrumentation
plan: 02
subsystem: calibration
tags: [scipy, least_squares, observability, dataclass, unit-testing, benchmark]

# Dependency graph
requires:
  - phase: 19-benchmark-instrumentation
    provides: "SolverDiagnostics dataclass + capture_solver_diagnostics() helper (plan 19-01)"
provides:
  - "optimize_interface passes ftol=1e-8, xtol=1e-8, gtol=1e-8 explicitly to least_squares (BENCH-06), bit-exact by regression test"
  - "optimize_interface accepts diagnostics_out: SolverDiagnostics | None = None, populated with nfev/njev/cost/optimality/status/message/tolerances/max_nfev/n_params/n_groups"
  - "register_auxiliary_camera accepts diagnostics_out: SolverDiagnostics | None = None, populated with the same fields except n_params/n_groups (null-with-reason, D-15) and without explicit tolerance kwargs (D-11)"
affects: [19-03-plan, 19-04-plan, benchmark-json-plan]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "capture_solver_diagnostics called unconditionally immediately after least_squares returns, before any error-path raise or result.x slicing"
    - "diagnostics_out threaded as a trailing keyword-only out-parameter; no return tuple extended"

key-files:
  created: []
  modified:
    - src/aquacal/calibration/interface_estimation.py
    - tests/unit/test_interface_estimation.py

key-decisions:
  - "groups (from build_structural_column_groups) captured into a named local variable at optimize_interface's jac_sparsity construction site instead of recomputed a second time for diagnostics capture (BENCH-03's 'measured from the live run')"
  - "register_auxiliary_camera's least_squares call itself gets zero explicit ftol/xtol/gtol kwargs, per D-11 -- only capture_solver_diagnostics records the SciPy-default values in force"

requirements-completed: [BENCH-01, BENCH-03, BENCH-06]

# Metrics
duration: 45min
completed: 2026-07-24
---

# Phase 19 Plan 02: Interface Estimation Diagnostics + Tolerances Summary

**Wired `capture_solver_diagnostics` into both `interface_estimation.py` `least_squares` call sites, and made `optimize_interface`'s termination tolerances explicit (`ftol=xtol=gtol=1e-8`), proven bit-exact by an exact-equality regression test.**

## Performance

- **Duration:** 45 min
- **Started:** 2026-07-24 (approx, see git log)
- **Completed:** 2026-07-24
- **Tasks:** 2
- **Files modified:** 2

## Accomplishments
- `optimize_interface` now passes `ftol=1e-8, xtol=1e-8, gtol=1e-8` explicitly to `least_squares` (BENCH-06), and accepts a trailing `diagnostics_out: SolverDiagnostics | None = None` parameter populated via `capture_solver_diagnostics` unconditionally, immediately after `least_squares` returns and before the `ConvergenceError` raise check (so a failed run's diagnostics are still captured).
- `n_params`/`n_groups` for `optimize_interface` are read from the already-built `jac_sparsity`/`groups` local variables (no recomputation) when `use_sparse_jacobian=True`; null-with-reason when `False` (D-15).
- `register_auxiliary_camera` now accepts the same trailing `diagnostics_out` parameter, populated after its `least_squares` call, before `result.x` is sliced. It does **not** gain explicit `ftol`/`xtol`/`gtol` kwargs on the `least_squares` call itself (D-11 — not a BENCH-06 target); `capture_solver_diagnostics` still records the SciPy-default values (`1e-8` each) as "in force". `n_params`/`n_groups` stay `None` with a stated reason (no column-grouping structure at this site).
- `njev` is asserted as a populated `int` (never `None`) at both sites in new tests, since both use `method="trf"` — corrected per 19-RESEARCH.md's Pitfall 5.
- New bit-exact regression test (`test_optimize_interface_diagnostics_out_populated_and_bit_exact`, parametrized over `use_sparse_jacobian`) proves the pre-existing implicit-tolerance code path and the new explicit-tolerance + `diagnostics_out` code path produce exactly equal `result.x`-derived outputs (`np.testing.assert_array_equal`, not `allclose`) for extrinsics, distances, board poses, and `rms_error`.
- New `test_register_auxiliary_camera_diagnostics_out_populated_with_njev_and_null_grouping_reasons` test asserts `njev` is populated, and `n_params`/`n_groups` are `None` with a non-empty reason string each.

## Task Commits

Each task was committed atomically:

1. **Task 1: optimize_interface — explicit tolerances + diagnostics capture + bit-exact test** - `4a7d46e` (feat)
2. **Task 2: register_auxiliary_camera — diagnostics capture (no tolerance change)** - `510ecbf` (feat)

**Plan metadata:** (this commit, appended after SUMMARY.md is written)

## Files Created/Modified
- `src/aquacal/calibration/interface_estimation.py` - `optimize_interface` gains explicit `ftol=1e-8, xtol=1e-8, gtol=1e-8` on its `least_squares` call and a trailing `diagnostics_out` parameter populated via `capture_solver_diagnostics`; `groups` captured into a named local variable at the sparse-Jacobian build site; `register_auxiliary_camera` gains the same trailing `diagnostics_out` parameter (no tolerance change) and its own `capture_solver_diagnostics` call with null-with-reason `n_params`/`n_groups`
- `tests/unit/test_interface_estimation.py` - Added `test_optimize_interface_diagnostics_out_populated_and_bit_exact` (parametrized over `use_sparse_jacobian`) to `TestOptimizeInterfaceObserver`; added `test_register_auxiliary_camera_diagnostics_out_populated_with_njev_and_null_grouping_reasons` to `TestRegisterAuxiliaryCamera`; imported `SolverDiagnostics`

## Decisions Made
- Captured `build_structural_column_groups(...)`'s return value into a named `groups` local variable at `optimize_interface`'s Jacobian-sparsity build site (previously it was an inline expression passed directly to `make_sparse_jacobian_func`) so the diagnostics capture call can read `int(groups.max()) + 1` without a second computation, matching BENCH-03's "measured from the live run rather than a separate script" intent.
- Followed D-11 literally for `register_auxiliary_camera`: its `least_squares(...)` call gained zero explicit `ftol=`/`xtol=`/`gtol=` keyword arguments. Only the `capture_solver_diagnostics(...)` call passes `ftol=1e-8, xtol=1e-8, gtol=1e-8` as the *recorded* values in force (SciPy's actual defaults for this SciPy version, verified in 19-RESEARCH.md), which is a description of the runtime state, not a behavior-affecting kwarg to `least_squares`.

## Deviations from Plan

### Documentation-only acceptance-criterion mismatches (not functional issues)

**1. [Not a Rule 1-4 case — plan-authoring grep pattern didn't survive ruff formatting] Two acceptance-criteria grep patterns from the plan text don't literally match the final, ruff-formatted code, though the underlying functional requirement is satisfied and verified by passing tests.**
- **Found during:** Task 1 and Task 2 final verification
- **Issue 1:** Task 1's acceptance criterion `grep -n "ftol=1e-8, xtol=1e-8, gtol=1e-8" src/aquacal/calibration/interface_estimation.py` (all three kwargs on one line) does not match, because `least_squares(...)` was already a long multi-line call and ruff's formatter (which the pre-commit hook runs and reported "Passed" against) places each of `ftol=1e-8,`/`xtol=1e-8,`/`gtol=1e-8,` on its own line rather than collapsing them onto one line. The substance — `optimize_interface`'s `least_squares` call receiving exactly these three explicit values — is correct and is what the bit-exact regression test verifies.
- **Issue 2:** Task 2's acceptance criterion `grep -c "ftol=1e-8" src/aquacal/calibration/interface_estimation.py` returning exactly `1` is inconsistent with Task 1's own `<action>` text, which explicitly instructs passing `ftol=1e-8` as a literal keyword argument to *both* the `least_squares(...)` call **and** the `capture_solver_diagnostics(...)` call within `optimize_interface` — i.e., Task 1 alone already produces 2 occurrences of the literal string `ftol=1e-8` before Task 2 makes any edit. Task 2 adds one more occurrence via its own `capture_solver_diagnostics(...)` call (never to `least_squares` itself, per D-11), for a correct total of 3. The actual `grep -c "ftol=1e-8"` result is `3`, all attributable to `capture_solver_diagnostics`/`least_squares` calls whose presence and correctness are independently confirmed by `grep -c "ftol=1e-8" register_auxiliary_camera` count of 1 occurrence inside that function, zero of which are on its `least_squares` call.
- **Fix:** None needed — no code change. Verified via direct reading of both `least_squares` call sites (register_auxiliary_camera's has zero explicit tolerance kwargs; optimize_interface's has exactly one `ftol=1e-8` on its `least_squares` call and one more on its adjacent `capture_solver_diagnostics` call) and via the passing bit-exact regression test and the passing `njev`/null-grouping-reason tests.
- **Files affected:** None (verification-only finding).
- **Verification:** `python -m pytest tests/unit/test_interface_estimation.py -q` (42 passed); manual read of both call sites confirms `register_auxiliary_camera`'s `least_squares(...)` call has no `ftol=`/`xtol=`/`gtol=` kwargs.

---

**Total deviations:** 0 code deviations; 1 documentation-only note about acceptance-criteria grep patterns not surviving code formatting/the plan's own multi-site tolerance-kwarg design.
**Impact on plan:** None on functionality — all `must_haves`/`success_criteria` semantic requirements are met and verified by passing tests, `ruff check`, and a bit-exact regression test.

## Issues Encountered

**Worktree base was stale at spawn time.** `git merge-base HEAD e1652d27605e285a5e370f3301a86e3e3be9e371` returned `b4da55b132722d4b061a832fc7cabe7b9f3c4b62` (the v1.8.0 release commit), not the expected `e1652d27605e285a5e370f3301a86e3e3be9e371`. Corrected per the mandatory `worktree_branch_check` step via `git reset --hard e1652d27605e285a5e370f3301a86e3e3be9e371` before any edit. Confirmed `HEAD` landed on the expected commit before proceeding.

**Editable install resolves to the main repo, not the worktree** (same environment quirk documented in 19-01-SUMMARY.md). Worked around by exporting `PYTHONPATH="$(pwd)/src"` for every verification command; confirmed via `python -c "import aquacal.calibration.interface_estimation as m; print(m.__file__)"` resolving inside this worktree before running any tests.

## User Setup Required

None - no external service configuration required.

## Verification Results

- `python -m pytest tests/unit/test_interface_estimation.py -k diagnostics_out -q` (with worktree `PYTHONPATH`): **2 passed** (Task 1's parametrized bit-exact test, both `use_sparse_jacobian` values)
- `python -m pytest tests/unit/test_interface_estimation.py -k register_auxiliary_camera_diagnostics -q`: **1 passed**
- `python -m pytest tests/unit/test_interface_estimation.py -q`: **42 passed** (39 pre-existing + 3 new: 2 parametrized `diagnostics_out` cases + 1 `register_auxiliary_camera` diagnostics test)
- `python -m pytest tests/ -m "not slow" -q`: **801 passed, 31 deselected** (baseline at wave-2 start was 798 passed / 31 deselected; +3 matches the 3 new tests added, zero regressions)
- `ruff check`: **All checks passed!**
- `python -m sphinx -W --keep-going -b html docs docs/_build/html`: **build succeeded**, zero warnings

## Self-Check: PASSED

## Next Phase Readiness

`optimize_interface(..., diagnostics_out=...)` and `register_auxiliary_camera(..., diagnostics_out=...)` are available for downstream plans (`benchmark.json` writer, pipeline wiring) to consume `SolverDiagnostics` from both `interface_estimation.py` call sites. The remaining two BENCH-01/BENCH-06 call sites (`refinement.py:237`, `point_refinement.py:674`) are out of scope for this plan (19-03's responsibility per D-07). No blockers.

---
*Phase: 19-benchmark-instrumentation*
*Completed: 2026-07-24*
