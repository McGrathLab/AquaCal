---
phase: 19-benchmark-instrumentation
verified: 2026-07-24T22:40:00Z
status: passed
score: 6/6 must-haves verified
overrides_applied: 0
re_verification:
  previous_status: gaps_found
  previous_score: 5/6
  gaps_closed:
    - "Every calibration run (real-rig and synthetic) writes a benchmark.json into output_dir with problem shape, per-stage metrics, solver configuration, accuracy, and environment"
  gaps_remaining: []
  regressions: []
---

# Phase 19: Benchmark Instrumentation Verification Report

**Phase Goal:** Every calibration run produces a trustworthy, machine-readable performance
record that a sweep can aggregate without hand computation.
**Verified:** 2026-07-24T22:40:00Z
**Status:** passed
**Re-verification:** Yes — after gap closure (commit `5e246b1`)

## Environment Confirmation

- `python -c "import aquacal; print(aquacal.__file__)"` → `C:\Users\tucke\PycharmProjects\AquaCal\src\aquacal\__init__.py` — confirmed testing the main checkout.
- `python -m pytest tests/synthetic/test_full_pipeline.py -q -k "benchmark or Benchmark"` → **3 passed, 34 deselected**.
- `python -m pytest tests/ -m "not slow" -q` → **846 passed, 31 deselected in 143.00s** — exactly the expected count (was 841, +5 new regression tests).
- `python -m sphinx -W --keep-going -b html docs docs/_build/html` → **build succeeded, exit 0**.
- `ruff check` → **All checks passed!**

## Gap Closure Verification (BENCH-04)

**Original gap:** `benchmark.json`'s `stages.stage3.seconds` was always `null` because the
`SolverDiagnostics` dict was keyed `"stage3"` while `pipeline.py`'s `timings` dict stored the
same stage's wall time under `"stage3_interface_optimization"` — a silent key mismatch.

**Fix verified by direct code read** (not just tests):

- `src/aquacal/calibration/pipeline.py:1094` — `solver_diagnostics.setdefault("stage3_interface_optimization", SolverDiagnostics())` — the diagnostics dict key was renamed to match the timings key (`timings["stage3_interface_optimization"] = elapsed` at line 1098). Both dicts now share one vocabulary, closing the root cause rather than papering over it with a remap table.
- `src/aquacal/io/benchmark.py:251-274` — `_resolve_stage_seconds(stage_name, timings)` now does an exact-match lookup first (the common, now-working case), and for the two structurally unmeasurable sub-stages (`stage3_rerun`, `auxiliary_registration_<cam>`) returns `(None, reason)` — an explicit `seconds_reason` string — rather than a silent, ambiguous `null` (D-15). This also correctly extends the fix to the two other stage blocks the original gap report flagged as affected by the same root cause.
- Live-reproduced via the exact regression test the gap called for: `tests/synthetic/test_full_pipeline.py::TestBenchmarkJsonIntegration::test_default_run_writes_benchmark_json` (lines 566-576) now asserts:
  ```python
  assert "stage3_interface_optimization" in record["stages"]
  assert record["stages"]["stage3_interface_optimization"]["seconds"] is not None
  assert record["stages"]["stage3_interface_optimization"]["seconds"] > 0
  ```
  This test was read directly and confirmed present with this exact assertion, and passes (see full-suite run above). This is the identical console-vs-JSON discrepancy the verifier live-reproduced in the initial pass ("Stage 3 RMS: ... (7.0s)" vs `seconds: null`) — now guarded end-to-end through the real pipeline, not a hand-built fixture.

**Gap: CLOSED.**

## Code-Review Findings Fixed in the Same Commit (spot-checked)

1. **CR-01 — aggregate memory boundary falsely labeled "no solver diagnostics":** `src/aquacal/io/benchmark.py:410-429` — when a memory boundary name (e.g. `auxiliary_registration`) has no exact stage match but prefix-matches per-item sub-stages (`auxiliary_registration_<cam>`), the code now names the sub-stages and explains the aggregate relationship instead of fabricating a "no least_squares call occurs" claim. Regression test `tests/unit/test_benchmark.py::TestAssembleBenchmarkRecord::test_aux_aggregate_memory_boundary_is_not_falsely_labelled_no_solver` exists and passes (1 passed).
2. **WR-01 — asymmetric diagnostics-capture-vs-raise ordering:** `src/aquacal/calibration/refinement.py:272` (`capture_solver_diagnostics(...)`) now runs before the `raise ConvergenceError(...)` at line 295, matching `optimize_interface`'s existing before-raise ordering. Regression test `tests/unit/test_refinement.py::...::test_diagnostics_captured_before_convergence_error_is_raised` exists and passes (1 passed).
3. **WR-02 — unescaped LaTeX in the aggregator:** `benchmarks/aggregate.py:166` (`_latex_escape`) is applied to every header (line 213) and cell (line 220) in `write_latex_fragment`. Regression test `tests/unit/test_benchmarks_runner.py::TestWriteLatexFragment::test_latex_special_characters_are_escaped` exists and passes (1 passed).

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | Solver diagnostics (nfev, njev, cost, optimality, status, message) captured for Stage 3, intrinsic pass, interface estimation, and point refinement | ✓ VERIFIED | Unchanged from initial verification; confirmed no regression via full-suite pass (846/846 relevant tests green). |
| 2 | Peak memory reported only behind opt-in flag, labeled with measurement mode, never by default | ✓ VERIFIED | `config.benchmark_memory` still defaults `False`; memory-block tests still pass. The CR-01 fix only changes the *label* attached to an aggregate boundary when memory is opted in — it does not change the opt-in gating. |
| 3 | Each run reports P, column-group count, implied FD reduction, computed from the live run | ✓ VERIFIED | Unchanged; `fd_reduction` computation in `assemble_benchmark_record` (lines 371-377) untouched by this fix. |
| 4 | Every calibration run (real-rig and synthetic) writes benchmark.json into output_dir with problem shape, per-stage metrics, solver configuration, accuracy, and environment | ✓ VERIFIED | **Gap closed.** `stages.stage3_interface_optimization.seconds` now resolves to a real, positive float via the matched key, live-reproduced through `run_calibration_from_config`, guarded by an integration-level regression assertion. |
| 5 | benchmarks/ runner sweeps cameras x frames grid, collects benchmark.json, emits CSV + LaTeX without recomputing | ✓ VERIFIED | Unchanged core behavior; LaTeX emission now also correctly escapes special characters (WR-02), strictly an improvement, no regression. |
| 6 | Stage 3 and intrinsic pass pass ftol/xtol/gtol explicitly; max_nfev recorded with effective value incl. unset/auto case; bit-exact regression test | ✓ VERIFIED | Unchanged; bit-exact tests still pass with exact-equality assertions. |

**Score:** 6/6 truths verified

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `src/aquacal/calibration/_observability.py` | `SolverDiagnostics`, `capture_solver_diagnostics` | ✓ VERIFIED | Unchanged, still wired at all 4 in-scope call sites. |
| `src/aquacal/io/benchmark.py` | `capture_environment`, `capture_peak_memory`, `assemble_benchmark_record`, `write_benchmark_json` | ✓ VERIFIED | `assemble_benchmark_record` now resolves `seconds` correctly for every stage via the shared vocabulary + honest `seconds_reason` fallback (D-15). No more silent nulls for `stage3`/`stage3_interface_optimization`. |
| `benchmarks/aggregate.py` | CSV + LaTeX aggregator, schema_version refusal | ✓ VERIFIED | Plus WR-02 LaTeX escaping fix, regression-tested. |
| `benchmarks/sweep_runner.py` | Grid sweep driver | ✓ VERIFIED | Unchanged. |
| `pyproject.toml` `[project.optional-dependencies].bench` | `psutil>=5.9` extra | ✓ VERIFIED | Unchanged. |

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
|----------|---------------|--------|---------------------|--------|
| `benchmark.json` `stages.stage3_interface_optimization.*` (diagnostics fields) | `solver_diagnostics["stage3_interface_optimization"]` | Real `least_squares` `OptimizeResult` via `capture_solver_diagnostics` | Yes | ✓ FLOWING |
| `benchmark.json` `stages.stage3_interface_optimization.seconds` | `timings["stage3_interface_optimization"]` | Same key now used by both diagnostics dict and timings dict — matched | Yes, > 0, integration-test-guarded | ✓ FLOWING (was ✗ DISCONNECTED) |
| `benchmark.json` `stages.stage3_rerun.seconds` | N/A — structurally folded into `stage3_interface_optimization` | `_resolve_stage_seconds` returns `(None, "wall time is folded into stage3_interface_optimization")` | N/A — explicit reason, not a silent gap | ✓ HONEST NULL (D-15) |
| `benchmark.json` `memory.*` | `memory_readings` | `capture_peak_memory()` at each stage boundary | Yes (when `benchmark_memory=True`) | ✓ FLOWING |
| `benchmarks/aggregate.py` CSV columns | `benchmark.json` files on disk | `json.load` per file, `pd.json_normalize` | Yes | ✓ FLOWING |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| Full test suite green | `pytest tests/ -m "not slow" -q` | 846 passed, 31 deselected | ✓ PASS |
| Benchmark integration tests | `pytest tests/synthetic/test_full_pipeline.py -q -k "benchmark or Benchmark"` | 3 passed, 34 deselected | ✓ PASS |
| Default run's stage3 seconds is populated and positive | Read `test_default_run_writes_benchmark_json` body + run | Assertion present, test passes | ✓ PASS |
| Docs build | `sphinx -W --keep-going -b html docs docs/_build/html` | exit 0, build succeeded | ✓ PASS |
| Lint | `ruff check` | All checks passed | ✓ PASS |
| CR-01 regression (aux memory boundary label) | `pytest tests/unit/test_benchmark.py -k test_aux_aggregate_memory_boundary_is_not_falsely_labelled_no_solver` | 1 passed | ✓ PASS |
| WR-01 regression (diagnostics-before-raise ordering) | `pytest tests/unit/test_refinement.py -k test_diagnostics_captured_before_convergence_error_is_raised` | 1 passed | ✓ PASS |
| WR-02 regression (LaTeX escaping) | `pytest tests/unit/test_benchmarks_runner.py -k test_latex_special_characters_are_escaped` | 1 passed | ✓ PASS |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|------------|-------------|--------|----------|
| BENCH-01 | 19-01, 19-02, 19-03 | Solver diagnostics captured at 4 sites | ✓ SATISFIED | See Truth 1 |
| BENCH-02 | 19-04, 19-05 | Peak memory opt-in, labeled, per-stage | ✓ SATISFIED | See Truth 2 |
| BENCH-03 | 19-02, 19-03 | P, group count, FD reduction from live run | ✓ SATISFIED | See Truth 3 |
| BENCH-04 | 19-05 | benchmark.json with problem shape, per-stage metrics, solver config, accuracy, environment | ✓ SATISFIED | Gap closed — see Truth 4 and Gap Closure Verification above |
| BENCH-05 | 19-06 | benchmarks/ runner sweeps grid, CSV + LaTeX | ✓ SATISFIED | See Truth 5 |
| BENCH-06 | 19-02, 19-03 | Explicit ftol/xtol/gtol, max_nfev recorded, bit-exact regression | ✓ SATISFIED | See Truth 6 |

**Note (unchanged, informational only):** `.planning/REQUIREMENTS.md`'s BENCH-01..06 checkboxes and the requirement-tracking table still read `- [ ]` / "Pending" as of this re-verification. This is a documentation bookkeeping item, not a code-level gap — all six requirements are satisfied in the codebase. Worth flipping to `[x]`/`Phase 19 Complete` in a follow-up doc commit, consistent with how Phases 16-18 closed out.

### Anti-Patterns Found

No `TBD`/`FIXME`/`XXX`/`TODO`/`HACK`/`PLACEHOLDER` markers found in any file touched by the fix commit (`pipeline.py`, `refinement.py`, `benchmark.py`, `aggregate.py`, and the four touched test files).

The previously noted diagnostics-capture-ordering inconsistency between `refinement.py` and `interface_estimation.py` (WR-01) has been resolved, not just noted — confirmed by direct code read.

## Known and Intentional (not reported as gaps, per phase instructions)

- `benchmarks/` is standalone scripts, not an `aquacal` CLI subcommand (D-12) — confirmed correct.
- The actual cameras x frames sweep is not executed (48-87 min per run); the runner is delivered and unit-tested with `run_calibration_from_config` mocked — confirmed correct scope boundary, reported as a note only.
- `point_refinement.py` keeps its 200x `max_nfev` multiplier (D-17) — confirmed correct, not a BENCH-06 target site.

## Gaps Summary

None. The single BENCH-04 gap from the initial verification (`stages.stage3.seconds` always
`null` due to a diagnostics/timings key mismatch) is closed by commit `5e246b1`: the diagnostics
and memory dict keys were renamed to `stage3_interface_optimization`, matching the pipeline's
settled timings vocabulary (D-03), and `_resolve_stage_seconds` now returns either a real
measured value or an explicit `seconds_reason` string — never a silent, ambiguous null (D-15).
The fix was verified against the live code path (not just test claims): the diagnostics dict key
at `pipeline.py:1094` and the timings key at `pipeline.py:1098` were read directly and confirmed
identical, and the exact integration-level regression assertion the gap report called for
(`test_default_run_writes_benchmark_json` asserting `seconds is not None and > 0`) was read and
confirmed present and passing. All three code-review findings fixed alongside the gap (CR-01,
WR-01, WR-02) were independently spot-checked against their source files and regression tests,
all confirmed real. Full test suite (846 passed, 31 deselected — the expected +5 count), docs
build (exit 0), and lint (clean) all pass. No regressions found in the five previously-verified
truths.

---

_Verified: 2026-07-24T22:40:00Z_
_Verifier: Claude (gsd-verifier)_
