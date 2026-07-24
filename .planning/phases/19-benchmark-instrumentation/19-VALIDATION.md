---
phase: 19
slug: benchmark-instrumentation
status: planned
nyquist_compliant: true
wave_0_complete: true
created: 2026-07-24
planned: 2026-07-24
revised: 2026-07-24
---

# Phase 19 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest (existing; `tests/unit/` + `tests/synthetic/`) |
| **Config file** | `pyproject.toml` (pytest config + `slow` marker) |
| **Quick run command** | `python -m pytest tests/unit/ -q` |
| **Full suite command** | `python -m pytest tests/ -m "not slow" -q` |
| **Estimated runtime** | ~65 seconds full (775 passed / 31 deselected as of Phase 18) |

Supplementary gates this phase also needs, because it touches docstrings on autodoc'd
modules and adds an optional dependency:

| Gate | Command | Why this phase needs it |
|------|---------|-------------------------|
| Docs build | `python -m sphinx -W --keep-going -b html docs docs/_build/html` | Phase 18 proved a docstring edit can break `-W` only after merge; 19-05 edits docstrings on autodoc'd `CalibrationConfig` |
| Lint | `ruff check` | Project standard |
| Optional-extra resolution | `python -c "import tomllib; d=tomllib.load(open('pyproject.toml','rb')); assert 'bench' in d['project']['optional-dependencies']"` | D-01 adds psutil as an optional extra (19-04); it is currently installed but undeclared, so a passing import proves nothing about the extra itself |

---

## Sampling Rate

- **After every task commit:** Run `python -m pytest tests/unit/ -q`
- **After every plan wave:** Run `python -m pytest tests/ -m "not slow" -q` **and** the docs
  build, not just the tests
- **Before `/gsd:verify-work`:** Full suite green, docs build exits 0, `ruff check` clean
- **Max feedback latency:** ~65 seconds

---

## Revision Note (2026-07-24, plan-check iteration 1)

Two blockers from the plan-checker are now reflected below:

1. **BENCH-02 per-stage scope (D-18).** The original plan set narrowed "peak memory per
   stage" to one whole-run reading. Revised: `capture_peak_memory()` (19-04) is now a
   stateless, repeatable zero-poll read; 19-05 calls it at every existing stage boundary and
   attaches an explicitly-labelled `cumulative_peak_bytes_as_of_stage_end` +
   `delta_bytes_since_previous_boundary` pair inside each stage's own block in `"stages"`,
   plus a top-level `whole_run_peak_bytes`. No field is ever named bare `peak_bytes` inside a
   stage block.
2. **njev factual error.** The original 19-02 Task 2 asserted `njev is None` for
   `register_auxiliary_camera` on the false premise that `jac='2-point'` implies `njev=None`.
   Independently reproduced: SciPy scopes `njev=None` to `method='lm'` only; all four in-scope
   sites use `method='trf'`, so `njev` is always a populated `int`. Corrected in 19-01, 19-02,
   19-03 — every test and acceptance criterion touching `njev` now asserts a populated int at
   all four in-scope sites, with the single defensive `getattr`-fallback test in 19-01
   explicitly marked as a generic-robustness check, not a real-site behavior claim.

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 19-01 T1 | 19-01 | 1 | BENCH-01 | T-19-01a | SolverDiagnostics contract only; njev docstring correctly scopes the None case to method='lm', not '2-point' | unit | `python -c "from aquacal.calibration._observability import SolverDiagnostics; SolverDiagnostics()"` | ✅ | ⬜ pending |
| 19-01 T2 | 19-01 | 1 | BENCH-01 | T-19-01a | capture_solver_diagnostics never reads result.jac/result.fun/result.x; njev populated-int case is primary, missing-attribute case is explicitly labelled defensive-only | unit | `pytest tests/unit/test_observability.py -k capture_solver_diagnostics -q` | ✅ | ⬜ pending |
| 19-02 T1 | 19-02 | 2 | BENCH-01, BENCH-03, BENCH-06 | T-19-02a | Explicit ftol/xtol/gtol bit-identical to prior default; diagnostics captured unconditionally before the ConvergenceError raise; njev asserted as populated int under both use_sparse_jacobian values | unit + regression | `pytest tests/unit/test_interface_estimation.py -k diagnostics_out -q` | ✅ | ⬜ pending |
| 19-02 T2 | 19-02 | 2 | BENCH-01, BENCH-03 | T-19-02b | njev asserted as populated int (corrected from the plan-checker's flagged `is None` blocker); null P/n_groups carry a stated reason (D-15), a DIFFERENT null case from njev; no explicit tolerance kwargs added here (D-11) | unit | `pytest tests/unit/test_interface_estimation.py -k register_auxiliary_camera_diagnostics -q` | ✅ | ⬜ pending |
| 19-03 T1 | 19-03 | 2 | BENCH-01, BENCH-03, BENCH-06 | T-19-03a | Explicit ftol/xtol/gtol bit-identical to prior default; njev asserted as populated int under both use_sparse_jacobian values | unit + regression | `pytest tests/unit/test_refinement.py -k diagnostics_out -q` | ✅ | ⬜ pending |
| 19-03 T2 | 19-03 | 2 | BENCH-01, BENCH-03 | T-19-03b, T-19-03c | point_refinement's existing 200x max_nfev / explicit ftol/xtol untouched; njev asserted as populated int; no circular import | unit | `pytest tests/unit/test_point_refinement.py -k solver_diagnostics -q` | ✅ | ⬜ pending |
| 19-04 T1 | 19-04 | 1 | BENCH-02 | T-19-04-SC, T-19-04a | Never-fails environment capture; git subprocess call scoped to own repo path, wrapped in try/except+timeout | unit | `pytest tests/unit/test_benchmark.py -k CaptureEnvironment -q` | ✅ | ⬜ pending |
| 19-04 T2 | 19-04 | 1 | BENCH-02 | T-19-04b, T-19-04c | /proc read scoped to own PID only; NO background polling thread anywhere (removed per D-18); repeated calls proven monotonic and stateless | unit | `pytest tests/unit/test_benchmark.py -k CapturePeakMemory -q` | ✅ | ⬜ pending |
| 19-05 T1 | 19-05 | 3 | BENCH-02, BENCH-03 | — | Config flags follow existing internals-block convention; diagnostics_out AND capture_peak_memory() threaded at every pipeline stage boundary, memory reads strictly gated behind config.benchmark_memory | unit | `python -c "from aquacal.calibration.pipeline import load_config, run_calibration_from_config"` | ✅ | ⬜ pending |
| 19-05 T2 | 19-05 | 3 | BENCH-02, BENCH-03, BENCH-04 | T-19-05b, T-19-05d | Skipped stages absent from "stages", not present-as-null; memory keys (top-level and per-stage) absent unless requested; per-stage memory field names are explicit (cumulative + delta), never a bare peak_bytes; full json.dumps round-trip asserted | unit | `pytest tests/unit/test_benchmark.py -k "AssembleBenchmarkRecord or WriteBenchmarkJson" -q` | ✅ | ⬜ pending |
| 19-05 T3 | 19-05 | 3 | BENCH-02, BENCH-04 | T-19-05c | capture_peak_memory() gated strictly behind config.benchmark_memory at every boundary; integration test proves all three memory-flag states (on with data, off with no key anywhere, and the three-key stage shape) | integration | `pytest tests/synthetic/test_full_pipeline.py -k benchmark -q` | ✅ | ⬜ pending |
| 19-06 T1 | 19-06 | 4 | BENCH-05 | T-19-06a | Aggregator refuses (raises, names the file) on an unrecognized schema_version rather than coercing/dropping; tolerates fixtures missing the opt-in memory block (ragged columns -> NaN, not an error) | unit | `pytest tests/unit/test_benchmarks_runner.py -k Aggregate -q` | ✅ | ⬜ pending |
| 19-06 T2 | 19-06 | 4 | BENCH-05 | T-19-06b | sweep_runner.py imports only the public aquacal surface; no aquacal CLI subcommand added | unit | `pytest tests/unit/test_benchmarks_runner.py -q` | ✅ | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

All satisfied by the planned task set itself (each new-behavior task is `tdd="true"` with an
explicit `<behavior>` block specifying test cases before implementation, per the task-level
TDD convention — see plan-phase's task_breakdown rules). No separate Wave 0 scaffold plan was
needed because every new test file this phase requires is created inside the task that also
implements the behavior it tests (contract-first ordering: 19-01 defines `SolverDiagnostics`
before any consumer plan is scheduled).

- [x] `tests/unit/test_observability.py` — capture_solver_diagnostics, including the corrected njev-is-populated-for-trf finding (19-01 T2)
- [x] `tests/unit/test_interface_estimation.py` extensions — optimize_interface / register_auxiliary_camera diagnostics (njev asserted as populated int) + BENCH-06 regression (19-02 T1/T2)
- [x] `tests/unit/test_refinement.py` extensions — joint_refinement diagnostics (njev asserted as populated int) + BENCH-06 regression (19-03 T1)
- [x] `tests/unit/test_point_refinement.py` extensions — refine_calibration solver_diagnostics (njev asserted as populated int) (19-03 T2)
- [x] `tests/unit/test_benchmark.py` — environment capture, stateless repeatable peak-memory capture, per-stage record assembly with explicit cumulative/delta labelling, JSON write (19-04 T1/T2, 19-05 T2)
- [x] `tests/synthetic/test_full_pipeline.py` extension — end-to-end benchmark.json integration, all three memory-flag states (19-05 T3)
- [x] `tests/unit/test_benchmarks_runner.py` + `tests/unit/fixtures/benchmark_records/` — aggregator CSV/LaTeX + schema_version refusal + ragged-column tolerance for the opt-in memory block (19-06 T1/T2)
- [x] No new test framework install needed — pytest is already configured

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Peak-RSS numbers are *plausible* on a real run, and the per-stage deltas make sense | BENCH-02 | A unit test can prove the fields are populated and labelled, but not that the values are physically correct. The known peak is ~3.6 GB on the 13-camera rig, dominated by Stage 3's dense Jacobian; a run whose `stage3` delta is near zero while `stage3_intrinsic_pass`'s is large would indicate the boundaries are misattributed. | Run one real 13-camera calibration with `internals.benchmark_memory: true`. Confirm `stage3`'s `delta_bytes_since_previous_boundary` accounts for most of the ~3.6 GB, `memory.whole_run_peak_bytes` is of the same order, and `memory.mode` reads `psutil_peak_wset` on Windows. |
| A real-rig `benchmark.json` is complete | BENCH-04 | Synthetic fixtures cannot prove the real pipeline populates every stage block; BENCH-04 explicitly says "for real-rig runs as well as synthetic". | After a real run, open `output_dir/benchmark.json` and confirm no stage block is unexpectedly missing and the environment block has a real CPU/RAM. |
| The LaTeX fragment renders | BENCH-05 | Valid-looking LaTeX can still fail to compile inside the manuscript's table environment. | Paste the emitted fragment into the supplement and compile. |

> **Cross-phase note (not a Phase 19 gate).** BENCH-05's actual cameras x frames sweep is a
> multi-hour job — a single 13-camera run takes 48-87 min per `CLAUDE.md`. Phase 19 delivers
> and tests the runner (Plan 19-06); **executing** the sweep is downstream work and must not be
> treated as a completion criterion for this phase.

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references (satisfied inline per task, see above)
- [x] No watch-mode flags
- [x] Feedback latency < 65s
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** planned 2026-07-24, revised 2026-07-24 (plan-check iteration 1: BENCH-02
per-stage scope restored per D-18; njev factual error corrected across 19-01/19-02/19-03) —
6 plans (19-01..19-06) across 4 waves; see
`.planning/phases/19-benchmark-instrumentation/19-0{1..6}-PLAN.md`.
