---
phase: 19-benchmark-instrumentation
reviewed: 2026-07-24T00:00:00Z
depth: standard
files_reviewed: 15
files_reviewed_list:
  - src/aquacal/calibration/pipeline.py
  - src/aquacal/calibration/interface_estimation.py
  - src/aquacal/calibration/refinement.py
  - src/aquacal/calibration/point_refinement.py
  - src/aquacal/config/schema.py
  - src/aquacal/io/benchmark.py
  - src/aquacal/calibration/_observability.py
  - benchmarks/aggregate.py
  - benchmarks/sweep_runner.py
  - tests/unit/test_benchmark.py
  - tests/unit/test_observability.py
  - tests/unit/test_benchmarks_runner.py
  - tests/unit/test_interface_estimation.py
  - tests/unit/test_refinement.py
  - tests/unit/test_point_refinement.py
  - tests/synthetic/test_full_pipeline.py
findings:
  critical: 1
  warning: 2
  info: 0
  total: 3
status: issues_found
---

# Phase 19: Code Review Report

**Reviewed:** 2026-07-24
**Depth:** standard
**Files Reviewed:** 15 (source) + tests
**Status:** issues_found

## Summary

Focused on the phase's own stated top priority: did any instrumentation change solver
behavior or numerical output. It did not — the `ftol`/`xtol`/`gtol=1e-8` additions to
`optimize_interface`/`joint_refinement` are SciPy 1.17's own implicit defaults (verified by
inspection against `19-RESEARCH.md` Q2), the bit-exactness regression tests in
`test_interface_estimation.py`/`test_refinement.py` correctly use `assert_array_equal`/`==`
(not `allclose`), `diagnostics_out`/`capture_solver_diagnostics` only ever read `result.*`
scalar fields after `least_squares` returns and never feed back into the solve, and
`point_refinement.py`'s 200x `max_nfev` auto-scale multiplier is untouched. `capture_peak_memory`
is correctly gated behind `config.benchmark_memory` everywhere it's called in `pipeline.py`, and
`_to_native` correctly recurses through nested containers (verified against a test fixture built
from a *real* `optimize_interface()` run, not hand-built Python floats).

One genuine data-integrity bug was found in the benchmark.json assembly for auxiliary-camera
registration (Critical), plus two lower-severity robustness/quality issues.

## Critical Issues

### CR-01: `benchmark.json` falsely claims "no least_squares call" for the auxiliary_registration boundary when auxiliary cameras were actually registered via least_squares

**File:** `src/aquacal/calibration/pipeline.py:1444-1496` and `src/aquacal/io/benchmark.py:361-392`

**Issue:** When `config.auxiliary_cameras` is non-empty and `config.benchmark_memory=True`, the
pipeline records a memory boundary under the key `"auxiliary_registration"`
(`pipeline.py:1495-1496`, `memory_readings["auxiliary_registration"] = capture_peak_memory()`),
but the corresponding solver diagnostics for that same loop are stored under
per-camera keys `"auxiliary_registration_{aux_cam}"`
(`pipeline.py:1472-1474`, `solver_diagnostics.setdefault(f"auxiliary_registration_{aux_cam}", ...)`).

In `assemble_benchmark_record` (`benchmark.py:361-392`), the memory-attribution loop checks
`if boundary_name in record["stages"]` to decide whether to attach the memory block to an
existing (diagnostics-derived) stage entry, or to synthesize a new one. Because
`"auxiliary_registration"` never matches any of the `"auxiliary_registration_{aux_cam}"` keys
already in `record["stages"]`, the `else` branch fires and synthesizes:

```python
record["stages"]["auxiliary_registration"] = {
    "seconds": timings.get("auxiliary_registration"),
    "solver_diagnostics_reason": _STAGES_WITH_NO_SOLVER_DIAGNOSTICS_REASON,  # "no least_squares call occurs in this stage; solver diagnostics are not applicable"
    "memory": memory_block,
}
```

This is factually false whenever at least one auxiliary camera was registered: `register_auxiliary_camera`
(`interface_estimation.py:715-723`) calls `least_squares` once per auxiliary camera inside exactly
this boundary, and those calls' diagnostics *are* captured, just under differently-named keys
that sit right next to (but not inside) this synthesized block. The resulting `benchmark.json`
simultaneously contains real per-camera diagnostics under `stages.auxiliary_registration_camX`
*and* a sibling `stages.auxiliary_registration` block asserting the opposite. This directly
contradicts the module's own stated contract in `benchmark.py`'s docstring ("never invents
metrics a run did not produce (D-14, D-15)") and `assemble_benchmark_record`'s own docstring for
`diagnostics` ("A stage this run did not execute is simply absent... never invents an empty
block for it") — here a stage that *did* run least_squares gets an invented "not applicable" block.

No test exercises `benchmark_memory=True` together with a non-empty `auxiliary_cameras` list
(confirmed via grep across `test_full_pipeline.py`/`test_benchmark.py`), so this combination is
untested and the defect ships silently.

**Fix:** Before synthesizing the "no solver diagnostics" placeholder, check whether any
diagnostics key is prefixed by the boundary name, and if so attach the memory block to a
distinctly-named entry instead of asserting inapplicability:

```python
else:
    has_related_diagnostics = any(
        k == boundary_name or k.startswith(f"{boundary_name}_")
        for k in diagnostics  # the `diagnostics` param already available in this function
    )
    record["stages"][boundary_name] = {
        "seconds": timings.get(boundary_name),
        "memory": memory_block,
        **(
            {}
            if has_related_diagnostics
            else {"solver_diagnostics_reason": _STAGES_WITH_NO_SOLVER_DIAGNOSTICS_REASON}
        ),
    }
```

Alternatively (and more simply), rename the pipeline's memory boundary key so it cannot be
mistaken for a stage name — e.g. `memory_readings["auxiliary_registration_loop"]` — and update the
reason text at that boundary to explicitly note it spans N per-camera `least_squares` calls
reported individually under `auxiliary_registration_<camera>`.

## Warnings

### WR-01: `capture_solver_diagnostics` capture-vs-raise ordering is inconsistent between `optimize_interface` and `joint_refinement`, silently dropping diagnostics on convergence failure for one of the two BENCH-06 target sites

**File:** `src/aquacal/calibration/interface_estimation.py:349-391` vs.
`src/aquacal/calibration/refinement.py:252-294`

**Issue:** In `optimize_interface`, `capture_solver_diagnostics` is called *before* the
`if result.status <= 0: raise ConvergenceError(...)` check (interface_estimation.py:365-388) —
this was a deliberate choice, per `19-02-PLAN.md`: "capture happens unconditionally before the
raise, matching D-08's 'additive, not a refactor of error handling'". In `joint_refinement`, the
order is reversed: the `ConvergenceError` raise (refinement.py:268-269) happens *before*
`capture_solver_diagnostics` is called (refinement.py:271-291). `19-03-PLAN.md`'s own action text
for this site literally instructs "Immediately after the `if result.status <= 0: raise
ConvergenceError(...)` check, call `capture_solver_diagnostics(...)`" — i.e. the plan itself
diverges from the rationale stated for the sibling site.

Net effect: when Stage 3's second pass (`stage3_intrinsic_pass`, the site that calls
`joint_refinement`) fails to converge, `diagnostics_out` is never populated (all fields stay at
their `None` defaults) and the exception propagates before any diagnostics are captured — whereas
the equivalent failure in `optimize_interface`'s Stage 3 first pass *would* leave a fully
populated (if terminal-failure) `SolverDiagnostics` behind for post-mortem inspection. This is an
inconsistency between two near-identical call sites with no test covering either failure path
(no test in `test_interface_estimation.py` or `test_refinement.py` triggers `ConvergenceError`
while `diagnostics_out` is set), so nothing currently catches or documents the difference.

**Fix:** Move the `capture_solver_diagnostics(...)` call in `joint_refinement` to before the
`if result.status <= 0: raise ConvergenceError(...)` check, matching `optimize_interface`'s
ordering and its stated rationale — diagnostics should reflect the actual terminal solver state
regardless of whether the caller is about to raise.

### WR-02: `write_latex_fragment` does not escape LaTeX special characters in cell/column values

**File:** `benchmarks/aggregate.py:148-192`

**Issue:** `write_latex_fragment` writes `columns` (header row, line 181) and every `df` cell
value (line 183-188) directly into the `.tex` fragment via `str(value)` with no escaping of
LaTeX-special characters (`_`, `%`, `&`, `#`, `\`, `{`, `}`). Columns and cell values are sourced
from flattened `benchmark.json` records, which can legitimately contain such characters —
camera names (a common convention includes underscores, e.g. `cam_0`), git SHAs are safe, but
`SolverDiagnostics.message` (SciPy's raw termination message string, passed through verbatim by
`capture_solver_diagnostics`) and `cpu_model` (raw `platform.processor()` output) are
uncontrolled strings that can contain `%`, `_`, or `&`. Any such value breaks LaTeX compilation
of the emitted fragment (an unescaped `%` comments out the remainder of the row; an unescaped `&`
silently shifts every subsequent column) rather than raising — the corruption is silent until a
human notices a garbled or truncated table in the compiled paper.

**Fix:** Escape LaTeX special characters before writing each header/cell string, e.g.:

```python
_LATEX_ESCAPE = str.maketrans({
    "_": r"\_", "%": r"\%", "&": r"\&", "#": r"\#",
    "{": r"\{", "}": r"\}", "\\": r"\textbackslash{}",
})

def _escape_latex(value: str) -> str:
    return value.translate(_LATEX_ESCAPE)
```
and apply it to every header/cell string immediately before appending to `lines`.

---

_Reviewed: 2026-07-24_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
