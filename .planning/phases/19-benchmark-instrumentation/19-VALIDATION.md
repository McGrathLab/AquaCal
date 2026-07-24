---
phase: 19
slug: benchmark-instrumentation
status: planned
nyquist_compliant: true
wave_0_complete: true
created: 2026-07-24
planned: 2026-07-24
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

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 19-01 T1 | 19-01 | 1 | BENCH-01 | T-19-01a | SolverDiagnostics contract only, no result.jac retention (no logic to violate this yet) | unit | `python -c "from aquacal.calibration._observability import SolverDiagnostics; SolverDiagnostics()"` | ✅ | ⬜ pending |
| 19-01 T2 | 19-01 | 1 | BENCH-01 | T-19-01a | capture_solver_diagnostics never reads result.jac/result.fun/result.x | unit | `pytest tests/unit/test_observability.py -k capture_solver_diagnostics -q` | ✅ | ⬜ pending |
| 19-02 T1 | 19-02 | 2 | BENCH-01, BENCH-03, BENCH-06 | T-19-02a | Explicit ftol/xtol/gtol bit-identical to prior default; diagnostics captured unconditionally before the ConvergenceError raise | unit + regression | `pytest tests/unit/test_interface_estimation.py -k diagnostics_out -q` | ✅ | ⬜ pending |
| 19-02 T2 | 19-02 | 2 | BENCH-01, BENCH-03 | T-19-02b | Null P/n_groups carry a stated reason (D-15); no explicit tolerance kwargs added here (D-11) | unit | `pytest tests/unit/test_interface_estimation.py -k register_auxiliary_camera_diagnostics -q` | ✅ | ⬜ pending |
| 19-03 T1 | 19-03 | 2 | BENCH-01, BENCH-03, BENCH-06 | T-19-03a | Explicit ftol/xtol/gtol bit-identical to prior default | unit + regression | `pytest tests/unit/test_refinement.py -k diagnostics_out -q` | ✅ | ⬜ pending |
| 19-03 T2 | 19-03 | 2 | BENCH-01, BENCH-03 | T-19-03b, T-19-03c | point_refinement's existing 200x max_nfev / explicit ftol/xtol untouched; no circular import | unit | `pytest tests/unit/test_point_refinement.py -k solver_diagnostics -q` | ✅ | ⬜ pending |
| 19-04 T1 | 19-04 | 1 | BENCH-02 | T-19-04-SC, T-19-04a | Never-fails environment capture; git subprocess call scoped to own repo path, wrapped in try/except+timeout | unit | `pytest tests/unit/test_benchmark.py -k CaptureEnvironment -q` | ✅ | ⬜ pending |
| 19-04 T2 | 19-04 | 1 | BENCH-02 | T-19-04b, T-19-04c | /proc read scoped to own PID only; polling fallback tightly bracketed and mock-only in tests | unit | `pytest tests/unit/test_benchmark.py -k CapturePeakMemory -q` | ✅ | ⬜ pending |
| 19-05 T1 | 19-05 | 3 | BENCH-03 | — | Config flags follow existing internals-block convention; diagnostics_out threaded at every pipeline least_squares site | unit | `python -c "from aquacal.calibration.pipeline import load_config, run_calibration_from_config"` | ✅ | ⬜ pending |
| 19-05 T2 | 19-05 | 3 | BENCH-03, BENCH-04 | T-19-05b | Skipped stages absent from "stages", not present-as-null; memory key absent unless requested; full json.dumps round-trip asserted | unit | `pytest tests/unit/test_benchmark.py -k "AssembleBenchmarkRecord or WriteBenchmarkJson" -q` | ✅ | ⬜ pending |
| 19-05 T3 | 19-05 | 3 | BENCH-04 | T-19-05c | capture_peak_memory() gated strictly behind config.benchmark_memory | integration | `pytest tests/synthetic/test_full_pipeline.py -k benchmark -q` | ✅ | ⬜ pending |
| 19-06 T1 | 19-06 | 4 | BENCH-05 | T-19-06a | Aggregator refuses (raises, names the file) on an unrecognized schema_version rather than coercing/dropping | unit | `pytest tests/unit/test_benchmarks_runner.py -k Aggregate -q` | ✅ | ⬜ pending |
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

- [x] `tests/unit/test_observability.py` — capture_solver_diagnostics (19-01 T2)
- [x] `tests/unit/test_interface_estimation.py` extensions — optimize_interface / register_auxiliary_camera diagnostics + BENCH-06 regression (19-02 T1/T2)
- [x] `tests/unit/test_refinement.py` extensions — joint_refinement diagnostics + BENCH-06 regression (19-03 T1)
- [x] `tests/unit/test_point_refinement.py` extensions — refine_calibration solver_diagnostics (19-03 T2)
- [x] `tests/unit/test_benchmark.py` — environment capture, peak-memory capture, record assembly, JSON write (19-04 T1/T2, 19-05 T2)
- [x] `tests/synthetic/test_full_pipeline.py` extension — end-to-end benchmark.json integration (19-05 T3)
- [x] `tests/unit/test_benchmarks_runner.py` + `tests/unit/fixtures/benchmark_records/` — aggregator CSV/LaTeX + schema_version refusal (19-06 T1/T2)
- [x] No new test framework install needed — pytest is already configured

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Peak-RSS number is *plausible* on a real run | BENCH-02 | A unit test can prove the field is populated and labelled, but not that the value is physically correct. The known peak is ~3.6 GB on the 13-camera rig; a reading of a few MB would mean the measurement is silently capturing the wrong thing (the exact `tracemalloc` failure mode D-01 exists to avoid). | Run one real 13-camera calibration with `internals.benchmark_memory: true`. Confirm the reported peak is of order GB, not MB, and that `memory.mode` reads `psutil_peak_wset` on Windows. |
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

**Approval:** planned 2026-07-24 — 6 plans (19-01..19-06) across 4 waves; see
`.planning/phases/19-benchmark-instrumentation/19-0{1..6}-PLAN.md`.
