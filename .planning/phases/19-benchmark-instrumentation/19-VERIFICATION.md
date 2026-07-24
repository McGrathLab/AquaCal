---
phase: 19-benchmark-instrumentation
verified: 2026-07-24T21:56:03Z
status: gaps_found
score: 5/6 must-haves verified
overrides_applied: 0
gaps:
  - truth: "Every calibration run (real-rig and synthetic) writes a benchmark.json into output_dir with problem shape, per-stage metrics, solver configuration, accuracy, and environment"
    status: partial
    reason: >
      benchmark.json's "stages"."stage3"."seconds" field is always null in every run,
      including real 13-camera runs, because assemble_benchmark_record() looks up wall-clock
      time with `timings.get(stage_name)` where stage_name is the SolverDiagnostics dict key
      ("stage3"), but pipeline.py's timings dict stores Stage 3's wall time under the
      Phase-18-settled key "stage3_interface_optimization" -- a different string. The two
      keys never match, so the single most computationally dominant stage in the pipeline
      (48-87 min on the real 13-camera rig, per CLAUDE.md) silently reports no timing at all.
      The same key-mismatch affects "stage3_rerun" (frame-rejection re-run) and
      "auxiliary_registration_{cam}" stage blocks. Live-reproduced with the real synthetic
      integration harness (not just static analysis): stage3.seconds is None while the
      console simultaneously prints "Stage 3 RMS: 0.000 pixels (7.0s)" for the same run.
      19-05-PLAN.md Task explicitly specified the correct mapping --
      `record["stages"]["stage3"]["seconds"] = timings.get("stage3_interface_optimization")`
      -- but the shipped assemble_benchmark_record() in src/aquacal/io/benchmark.py uses the
      generic `timings.get(stage_name)` instead, silently dropping the intended per-stage
      remapping. tests/unit/test_benchmark.py's unit tests did not catch this because they
      construct a self-consistent but unrealistic fixture (`timings={"stage3": 1.23}`) that
      uses "stage3" as the timings key directly, which never occurs in the real pipeline.
      tests/synthetic/test_full_pipeline.py's three benchmark.json integration tests never
      assert `stages["stage3"]["seconds"] is not None`, so the live pipeline's actual
      mismatch was never exercised by an assertion.
    artifacts:
      - path: "src/aquacal/io/benchmark.py"
        issue: "assemble_benchmark_record() line ~340 uses `stage_entry[\"seconds\"] = timings.get(stage_name)` with no stage-name remapping for stages whose SolverDiagnostics key differs from the pipeline's timings-dict key"
      - path: "src/aquacal/calibration/pipeline.py"
        issue: "solver_diagnostics dict is keyed \"stage3\"/\"stage3_rerun\" (line 1093, 1217) while timings dict is keyed \"stage3_interface_optimization\" (line 1096, 1222) for the same stage -- two different vocabularies for one stage, contradicting D-03's explicit instruction to reuse one settled key set"
      - path: "tests/unit/test_benchmark.py"
        issue: "TestAssembleBenchmarkRecord fixtures use timings={\"stage3\": ...} instead of the real pipeline's timings={\"stage3_interface_optimization\": ...}, masking the mismatch"
      - path: "tests/synthetic/test_full_pipeline.py"
        issue: "TestBenchmarkJsonIntegration's three tests never assert stages[\"stage3\"][\"seconds\"] is not None, so the live end-to-end pipeline's actual defect was never caught"
    missing:
      - "Either rename the pipeline's timings dict key from \"stage3_interface_optimization\" to \"stage3\" (matching the diagnostics dict) and thread that rename consistently, or have assemble_benchmark_record() accept/apply an explicit stage-name-to-timings-key mapping as 19-05-PLAN.md originally specified"
      - "A regression test asserting benchmark.json's stages.stage3.seconds (and stage3_rerun, auxiliary_registration_* if applicable) is a populated float, not null, from a real run through run_calibration_from_config -- not just from a hand-built assemble_benchmark_record() fixture"
---

# Phase 19: Benchmark Instrumentation Verification Report

**Phase Goal:** Every calibration run produces a trustworthy, machine-readable performance
record that a sweep can aggregate without hand computation.
**Verified:** 2026-07-24T21:56:03Z
**Status:** gaps_found
**Re-verification:** No — initial verification

## Environment Confirmation

- `python -c "import aquacal; print(aquacal.__file__)"` → `C:\Users\tucke\PycharmProjects\AquaCal\src\aquacal\__init__.py` — confirmed testing the main checkout, not a stale worktree.
- `python -m pytest tests/ -m "not slow" -q` → **841 passed, 31 deselected in 136.34s** — matches the expected count exactly.
- `python -m pytest tests/ -m "not slow" -q -k "bit_exact or explicit_tol or tolerance or diagnostics"` → **66 passed, 806 deselected**. Read both bit-exact regression test bodies (`test_optimize_interface_diagnostics_out_populated_and_bit_exact`, `test_joint_refinement_diagnostics_out_populated_and_bit_exact`): both use `np.testing.assert_array_equal` and Python `==` on `result.x`-derived outputs — exact equality, not `allclose`.
- `python -m sphinx -W --keep-going -b html docs docs/_build/html` → **build succeeded, exit 0**.
- `ruff check` → **All checks passed!**

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | Solver diagnostics (nfev, njev, cost, optimality, status, message) captured for Stage 3, intrinsic pass, interface estimation, and point refinement | ✓ VERIFIED | All four in-scope `least_squares` sites (`interface_estimation.py:349`/`715`, `refinement.py:252`, `point_refinement.py:681`) call `capture_solver_diagnostics` with real `result.nfev/njev/cost/optimality/status/message`. Out-of-scope sites (`extrinsics.py:189`, `evaluation.py:302`, both `method="lm"`) correctly excluded per D-07. Live-reproduced: a real run's `stage3` block shows `nfev=45, njev=33, cost=1.6e-23, optimality=1.3e-07, status=3` — all populated, `njev` a populated int as documented (not `None`, correcting the original `2-point` false premise). |
| 2 | Peak memory reported only behind opt-in flag, labeled with measurement mode, never by default | ✓ VERIFIED | `config.benchmark_memory` defaults `False` (`schema.py:364`); `capture_peak_memory()` calls (`pipeline.py:1086-1626`) are all gated behind `if config.benchmark_memory:`. Live-reproduced: default run's `benchmark.json` has no `"memory"` key anywhere (`test_benchmark_memory_false_has_no_memory_key_anywhere` passes; also independently reproduced). `benchmark_memory=True` run correctly adds `mode: "psutil_peak_wset"` (Windows) plus `cumulative_peak_bytes_as_of_stage_end`/`delta_bytes_since_previous_boundary` per D-18. |
| 3 | Each run reports P, column-group count, implied FD reduction, computed from the live run | ✓ VERIFIED | Live-reproduced: `stage3.n_params=117, n_groups=13, fd_reduction=9.0` read directly from `jac_sparsity.shape[1]` / `groups.max()+1` at the real call site (`interface_estimation.py:373-374`), not a restated constant. `assemble_benchmark_record` computes `fd_reduction = n_params/n_groups` only from already-recorded values (D-13). |
| 4 | Every calibration run (real-rig and synthetic) writes benchmark.json into output_dir with problem shape, per-stage metrics, solver configuration, accuracy, and environment | ✗ FAILED | `save_benchmark` defaults `True` and the file is written (`pipeline.py:1728-1760`) with `problem_shape`, `solver_config`, `accuracy`, `environment` all populated. **But** per-stage metrics are incomplete: `stages.stage3.seconds` is always `null` due to a dict-key mismatch between `timings["stage3_interface_optimization"]` and the diagnostics dict's `"stage3"` key. Live-reproduced twice (with and without `benchmark_memory`, with and without `refine_intrinsics`) — see gap detail below. |
| 5 | benchmarks/ runner sweeps cameras x frames grid, collects benchmark.json, emits CSV + LaTeX without recomputing | ✓ VERIFIED | `benchmarks/aggregate.py` reads every `benchmark.json`, refuses (raises `UnsupportedSchemaVersionError`, names the file) on an unrecognized `schema_version`, computes nothing not already recorded (confirmed by reading `aggregate()`/`write_latex_fragment()`). `benchmarks/sweep_runner.py` imports only `aquacal.calibration.{load_config, run_calibration_from_config}` — public surface, no CLI subcommand (D-12). Not executed as a real sweep — explicitly out of scope per phase context/emphasis; noted, not a gap. |
| 6 | Stage 3 and intrinsic pass pass ftol/xtol/gtol explicitly; max_nfev recorded with effective value incl. unset/auto case; bit-exact regression test | ✓ VERIFIED | `interface_estimation.py:359-361` and `refinement.py:262-264` both pass `ftol=1e-8, xtol=1e-8, gtol=1e-8` explicitly (SciPy 1.17 defaults, D-10). `max_nfev_effective=len(initial_params)*100, max_nfev_source="scipy_auto"` recorded at both sites. `point_refinement.py`'s distinct 200x multiplier is untouched and correctly excluded from the BENCH-06 target set (D-17), confirmed by `test_solver_diagnostics_max_nfev_source_point_refinement_200x_auto`. Bit-exact regression tests use `assert_array_equal`/`==`, confirmed by direct read. |

**Score:** 5/6 truths verified

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `src/aquacal/calibration/_observability.py` | `SolverDiagnostics`, `capture_solver_diagnostics` | ✓ VERIFIED | Present, substantive, wired at all 4 in-scope call sites |
| `src/aquacal/io/benchmark.py` | `capture_environment`, `capture_peak_memory`, `assemble_benchmark_record`, `write_benchmark_json` | ⚠️ HOLLOW (partial) | Exists, substantive, wired into `pipeline.py`; produces real JSON but with a per-stage `seconds` defect for `stage3`/`stage3_rerun`/`auxiliary_registration_*` |
| `benchmarks/aggregate.py` | CSV + LaTeX aggregator, schema_version refusal | ✓ VERIFIED | Exists, substantive, computes nothing not already recorded, refuses on unknown schema_version |
| `benchmarks/sweep_runner.py` | Grid sweep driver | ✓ VERIFIED | Exists, substantive, imports only public `aquacal` surface, unit-tested with `run_calibration_from_config` mocked |
| `pyproject.toml` `[project.optional-dependencies].bench` | `psutil>=5.9` extra | ✓ VERIFIED | Present at line 60-62, not a core dependency |

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
|----------|---------------|--------|---------------------|--------|
| `benchmark.json` `stages.stage3.*` (diagnostics fields) | `solver_diagnostics["stage3"]` | Real `least_squares` `OptimizeResult` via `capture_solver_diagnostics` | Yes | ✓ FLOWING |
| `benchmark.json` `stages.stage3.seconds` | `timings.get("stage3")` | `timings` dict, actually keyed `"stage3_interface_optimization"` | **No — always `None`** | ✗ DISCONNECTED |
| `benchmark.json` `memory.*` | `memory_readings` | `capture_peak_memory()` at each stage boundary | Yes (when `benchmark_memory=True`) | ✓ FLOWING |
| `benchmarks/aggregate.py` CSV columns | `benchmark.json` files on disk | `json.load` per file, `pd.json_normalize` | Yes | ✓ FLOWING |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| Full test suite green | `pytest tests/ -m "not slow" -q` | 841 passed, 31 deselected | ✓ PASS |
| BENCH-06 bit-exactness | `pytest -k "bit_exact or explicit_tol or tolerance or diagnostics"` | 66 passed; exact-equality assertions confirmed by reading test bodies | ✓ PASS |
| Docs build | `sphinx -W --keep-going -b html docs docs/_build/html` | exit 0, build succeeded | ✓ PASS |
| Lint | `ruff check` | All checks passed | ✓ PASS |
| Default run writes benchmark.json, no memory key | `_run_full_pipeline_with_mocked_video_io(scenario, tmp)` (live, not mocked pipeline internals) | `benchmark.json` written; `stage3.seconds == null` (should be a float) | ✗ FAIL — see gap |
| `benchmark_memory=True` per-stage memory | same, with `benchmark_memory=True` | `stage3.memory` populated correctly with `psutil_peak_wset`; `stage3.seconds` still `null` | ✗ FAIL (partial) — see gap |
| `refine_intrinsics=True` stage naming | same, with `refine_intrinsics=True` | `stage3_intrinsic_pass.seconds == 0.52` (correct, key matches); `stage3.seconds == null` (incorrect) | ✗ FAIL (partial) — see gap |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|------------|-------------|--------|----------|
| BENCH-01 | 19-01, 19-02, 19-03 | Solver diagnostics captured at 4 sites | ✓ SATISFIED | See Truth 1 |
| BENCH-02 | 19-04, 19-05 | Peak memory opt-in, labeled, per-stage | ✓ SATISFIED | See Truth 2 |
| BENCH-03 | 19-02, 19-03 | P, group count, FD reduction from live run | ✓ SATISFIED | See Truth 3 |
| BENCH-04 | 19-05 | benchmark.json with problem shape, per-stage metrics, solver config, accuracy, environment | ✗ BLOCKED | Per-stage `seconds` field missing for `stage3` (dominant stage) — see gap |
| BENCH-05 | 19-06 | benchmarks/ runner sweeps grid, CSV + LaTeX | ✓ SATISFIED | See Truth 5 |
| BENCH-06 | 19-02, 19-03 | Explicit ftol/xtol/gtol, max_nfev recorded, bit-exact regression | ✓ SATISFIED | See Truth 6 |

**Note:** `.planning/REQUIREMENTS.md`'s BENCH-01..06 checkboxes remain unchecked (`- [ ]`) as of this verification, unlike Phases 16-18 which flipped their requirement checkboxes to `[x]` on completion. This is a documentation bookkeeping gap, not evidence against the code-level findings above, but is worth closing alongside the `stage3.seconds` fix so REQUIREMENTS.md reflects the phase's actual (partial) completion state.

### Anti-Patterns Found

No `TBD`/`FIXME`/`XXX`/`TODO`/`HACK`/`PLACEHOLDER` markers found in any file touched by this phase (`benchmark.py`, `_observability.py`, `interface_estimation.py`, `refinement.py`, `point_refinement.py`, `aggregate.py`, `sweep_runner.py`, `pipeline.py`, `schema.py`).

**Minor inconsistency (informational, not a gap):** `refinement.py`'s `joint_refinement` calls `capture_solver_diagnostics` *after* the `if result.status <= 0: raise ConvergenceError` check (lines 268/271), while `interface_estimation.py`'s `optimize_interface` captures diagnostics *before* its equivalent raise (lines 365/387). This means `refinement.py`'s `diagnostics_out` is left unpopulated on a convergence failure, unlike `interface_estimation.py`. This has no observable effect on `benchmark.json` today because `pipeline.py` has no `except ConvergenceError` handler — a raised `ConvergenceError` aborts the whole run before `write_benchmark_json` is ever reached either way — but it is an inconsistency between the two BENCH-06 target sites worth aligning if the codebase later adds partial-failure benchmark capture.

## Known and Intentional (not reported as gaps, per phase instructions)

- `benchmarks/` is standalone scripts, not an `aquacal` CLI subcommand (D-12) — confirmed correct.
- The actual cameras x frames sweep is not executed (48-87 min per run); the runner is delivered and unit-tested with `run_calibration_from_config` mocked — confirmed correct scope boundary, reported as a note only.
- `point_refinement.py` keeps its 200x `max_nfev` multiplier (D-17) — confirmed correct, not a BENCH-06 target site.
- `CLAUDE.md` gitignored — not relevant here.

## Gaps Summary

One concrete, live-reproduced defect blocks full BENCH-04 achievement: `benchmark.json`'s
`stages.stage3.seconds` (and by the same root cause, `stage3_rerun` and
`auxiliary_registration_{cam}`) is always `null`, even on a real run, because
`assemble_benchmark_record()` looks up wall-clock time using the `SolverDiagnostics` dict's
stage-name key (`"stage3"`) against `pipeline.py`'s `timings` dict, which stores the same
stage's time under the Phase-18-settled key `"stage3_interface_optimization"` — a different
string. This was reproduced directly against the live pipeline (not a static-analysis
inference): a synthetic end-to-end run printed `Stage 3 RMS: 0.000 pixels (7.0s)` to console
while the same run's `benchmark.json` recorded `"stage3": {"seconds": null, ...}`. The
executor's own 19-05-PLAN.md specified the correct fix (`timings.get("stage3_interface_
optimization")`) but the shipped code used the generic, unmapped `timings.get(stage_name)`
instead. All other stages that happen to share their name with a `timings` key
(`stage3_intrinsic_pass`, `validation`) are unaffected and report `seconds` correctly. Every
other must-have (solver diagnostics capture, opt-in memory, P/group-count/FD-reduction
reporting, the aggregator, and explicit tolerances) is verified against the live codebase and
matches the phase's locked decisions exactly.

---

_Verified: 2026-07-24T21:56:03Z_
_Verifier: Claude (gsd-verifier)_
