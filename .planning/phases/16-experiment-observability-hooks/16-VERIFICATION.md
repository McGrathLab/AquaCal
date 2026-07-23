---
phase: 16-experiment-observability-hooks
verified: 2026-07-23T00:00:00Z
status: passed
score: 7/7 must-haves verified
---

# Phase 16: Experiment Observability Hooks Verification Report

**Phase Goal:** Researchers can inspect optimizer internals and reproduce results needed for
the WP5/WP6 experiments, with ZERO change to numerical behavior. First half of the milestone's
longest pole and only true experiment blocker.
**Verified:** 2026-07-23
**Status:** passed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | HOOK-01: Each BA stage's intermediate calibration can be dumped as loadable calibration JSON | ✓ VERIFIED | `_dump_stage_calibration` in `pipeline.py`, called at 3 guarded sites (`config.save_stage_calibrations`); writes `internals/calibration_stage3.json`, `_stage3_rerun.json`, `_stage4.json`; `calibration_initial.json` (post-Stage-2) left untouched. Tests pass (`TestDumpStageCalibration`). |
| 2 | HOOK-02: Opt-in per-iteration CSV trace for each BA stage, zero change when off | ✓ VERIFIED | `OptimizerObserver` (`_observability.py`, 376 lines) wraps `least_squares(callback=...)`; `optimize_interface`/`joint_refinement` accept `observer=None` last-kwarg; when `None` no `callback` kwarg reaches scipy. Bit-identical-result tests pass in both entry points and in `test_observability.py`. Three distinct CSVs per stage (`trace_stage3.csv`, `_stage3_rerun.csv`, `_stage4.csv`), never merged. |
| 3 | HOOK-03: Conditioning diagnostics (spectrum, condition number, labelled correlation matrix) at solution, refusing loudly on OOM | ✓ VERIFIED | `compute_conditioning` (blocked tall-skinny QR + single `svd(R, full_matrices=False)`) in `validation/conditioning.py`; `on_solution` computes it from `result.jac` inside optimizer scope; `build_parameter_labels` mirrors `pack_params` layout; `_select_conditioning_report` picks the final-reported-stage's report; writes `internals/conditioning.json`(+stage key)/`.npz`. `ConditioningMemoryError` propagates uncaught from pipeline. No `eigh(` or `mode='r'`/`full_matrices=True` anywhere in `src/aquacal/`. |
| 4 | HOOK-04: Held-out evaluation callable standalone, same code path as pipeline | ✓ VERIFIED | `aquacal.evaluate_calibration` (top-level export, 16th public name) in `validation/evaluation.py`; pipeline refactored to call it (`_estimate_validation_poses` moved, not duplicated); `test_matches_legacy_inline_sequence` asserts exact equality (`==`, `assert_array_equal`, not `pytest.approx`) against a literal replica of the pre-refactor inline sequence. |
| 5 | HOOK-05: Synthetic generator sweep axes (refractive index, layout, tank-scale/working-distance) independently controllable, with ground truth returned | ✓ VERIFIED | `generate_synthetic_detections` accepts `n_air`/`n_water`, forwarded to `Interface`; `SyntheticScenario` records `n_air`/`n_water`/`seed`; `test_synthetic_sweep_axes.py` (327 lines, 6 tests) proves layout/scale/distance/index axes are independent and every generator is seed-reproducible. |
| 6 | HOOK-06: Every sweep entry point accepts a seed and threads it; surprising results reproducible from the artifact | ✓ VERIFIED | Pipeline's `split_detections` call now passes `seed=config.seed` (previously hardcoded 42); `CalibrationMetadata.seed` persisted with `.get("seed")` backward-compat deserialization; `_compute_config_hash` includes seed. All other generators/`split_holdout`/`refine_calibration` already threaded per audit. |
| 7 | Zero-change-to-numerical-behavior hard constraint holds across all touched optimizer paths | ✓ VERIFIED | Bit-exact regression tests exist and pass for: (a) `OptimizerObserver` wrapping (`test_wrappers_do_not_change_the_solution`), (b) `optimize_interface`/`joint_refinement` with vs. without observer (`np.testing.assert_array_equal` on R/t/water_z/poses/RMS), (c) `evaluate_calibration` vs. legacy inline sequence (exact `==`), (d) `split_detections` default seed=42 reproduces prior split byte-for-byte. Full suite: 763 passed, 0 failed (baseline 651). |

**Score:** 7/7 truths verified

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `src/aquacal/validation/conditioning.py` | `compute_conditioning`, `ConditioningReport`, `ConditioningMemoryError`, `save_conditioning_report`, `load_conditioning_report` | ✓ VERIFIED | 280 lines; all 5 exported from `aquacal.validation.__init__` under `# conditioning`; no `eigh(`/`mode='r'`/`full_matrices=True` |
| `tests/unit/test_conditioning.py` | Accuracy/chunk-invariance/memory/IO tests | ✓ VERIFIED | 176 lines, 12 tests, all pass |
| `src/aquacal/calibration/_observability.py` | `OptimizerObserver`, `TraceRow`, `build_parameter_labels` | ✓ VERIFIED | 376 lines; private module, correctly not in any `__init__.py __all__` |
| `tests/unit/test_observability.py` | Row capture, step-norm, optimality proxy, CSV shape, conditioning wiring | ✓ VERIFIED | 359 lines, 21 tests, all pass |
| `src/aquacal/io/internals.py` | `INTERNALS_DIRNAME`, `ensure_internals_dir`, `warn_if_overwriting` | ✓ VERIFIED | 49 lines, exported from `aquacal.io` |
| `src/aquacal/config/schema.py` | 4 new `CalibrationConfig` fields + `CalibrationMetadata.seed` | ✓ VERIFIED | `save_stage_calibrations=True`, `save_optimization_trace=False`, `save_conditioning=False`, `seed=42`; `CalibrationMetadata.seed: int \| None = None` |
| `src/aquacal/calibration/pipeline.py` | `load_config` parsing, `_dump_stage_calibration`, trace/conditioning wiring, `evaluate_calibration` call, `seed=config.seed` threading | ✓ VERIFIED | All present and grep-confirmed at correct call sites |
| `src/aquacal/validation/evaluation.py` | `evaluate_calibration`, `HeldOutEvaluation` | ✓ VERIFIED | 310 lines; exported from `aquacal.validation` and top-level `aquacal` |
| `tests/unit/test_evaluation.py` | Standalone behavior + legacy-equivalence regression test | ✓ VERIFIED | 320 lines, exact-equality regression test present |
| `src/aquacal/datasets/synthetic.py` | `n_air`/`n_water` plumbed, `SyntheticScenario` records `n_air`/`n_water`/`seed` | ✓ VERIFIED | Confirmed via grep and SUMMARY |
| `tests/unit/test_synthetic_sweep_axes.py` | Executable WP5 sweep-axis audit | ✓ VERIFIED | 327 lines, 6 tests, all pass |
| `pyproject.toml` / `requirements.txt` | `scipy>=1.16` floor | ✓ VERIFIED | Both files pin `scipy>=1.16` |

### Key Link Verification

| From | To | Via | Status | Details |
|------|-----|-----|--------|---------|
| `_observability.py` `on_solution` | `aquacal.validation.conditioning.compute_conditioning` | called with `result.jac` before Jacobian goes out of scope | ✓ WIRED | Local import inside `on_solution`; only the small report survives (verified by `test_observer_does_not_retain_jacobian_after_conditioning`) |
| `pipeline.py` | `output_dir/internals/conditioning.json`+`.npz` | `save_conditioning_report` on final-reported-stage's observer | ✓ WIRED | `_select_conditioning_report` helper unit-tested across 4 refine/re-run combinations; write not wrapped in try/except |
| `interface_estimation.py`/`refinement.py` | scipy `least_squares` callback | `observer.callback` passed only when observer supplied | ✓ WIRED | `**ls_kwargs` empty when `observer is None`; verified by inspection + bit-identical tests |
| `pipeline.py` | `evaluate_calibration` | inline held-out block replaced by call | ✓ WIRED | `grep -c "compute_3d_distance_errors(" pipeline.py` returns 0 (single call path in `validation/evaluation.py`) |
| `pipeline.py` | `split_detections` | `seed=config.seed` | ✓ WIRED | Grep-confirmed at call site; test asserts default 42 reproduces prior split |
| `generate_synthetic_detections` | `Interface` constructor | `n_air=n_air, n_water=n_water` | ✓ WIRED | Confirmed via SUMMARY and test `test_generate_detections_index_changes_projection` |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|-------------|--------------|--------|----------|
| HOOK-01 | 16-03 | Per-stage intermediate calibration dumps | ✓ SATISFIED | `_dump_stage_calibration`, 3 call sites, tests pass |
| HOOK-02 | 16-04 | Opt-in per-iteration BA trace | ✓ SATISFIED | `OptimizerObserver`, per-stage CSVs, scipy>=1.16 pinned |
| HOOK-03 | 16-01, 16-03, 16-05 | Conditioning diagnostics at solution | ✓ SATISFIED | Blocked-QR `compute_conditioning`, wired via `on_solution`, no forbidden `eigh`/OOM patterns |
| HOOK-04 | 16-07 | Standalone held-out evaluation | ✓ SATISFIED | `aquacal.evaluate_calibration`, shared code path, exact-equality regression test |
| HOOK-05 | 16-02 | Sweep-axis audit (index, layout, scale/distance) | ✓ SATISFIED | Index plumbed; all 4 axes proven independent by executable test |
| HOOK-06 | 16-02, 16-03, 16-06 | Seed threading and reproducibility | ✓ SATISFIED | Pipeline split seeded, metadata records seed, config_hash distinguishes seeds |

No orphaned requirements — `.planning/REQUIREMENTS.md` maps HOOK-01..06 to Phase 16 exactly, and every ID appears in at least one plan's `requirements:` frontmatter.

### Anti-Patterns Found

None. No TODO/FIXME/placeholder markers, no empty-return stubs, and no console.log-only implementations found in the phase's key files. The one deliberately loosened test tolerance (`test_chunk_size_invariance`'s sigma_min comparison, rtol 1e-9 → 1e-6 for the smallest singular value only) is documented in 16-01-SUMMARY.md as matching the algorithm's own measured accuracy floor (~7.2e-8, per RESEARCH.md's Addendum), not a masked bug — the other 39 singular values still hold to rtol=1e-9.

### Human Verification Required

None. All must-haves are backed by automated tests that were confirmed to pass, and the hard numerical-equivalence constraint is enforced by bit-exact assertions (`assert_array_equal`, `==`) rather than approximate comparisons, so no item requires manual/visual confirmation.

### Gaps Summary

No gaps found. All 6 requirement IDs (HOOK-01 through HOOK-06) are satisfied with real, substantive, wired implementations. The three plans that touched live optimizer paths (16-04's `least_squares` callback, 16-05's `result.jac`-based conditioning, 16-07's held-out evaluation refactor) each carry an explicit bit-exact equivalence/regression test, and all such tests pass. The two orchestrator-flagged non-negotiables are both confirmed: (1) the conditioning path uses blocked tall-skinny QR with no `eigh(J.T@J)` anywhere in `src/`, and `ConditioningMemoryError` propagates uncaught through the pipeline; (2) `scipy>=1.16` is pinned in both `pyproject.toml` and `requirements.txt`. Full test suite: 763 passed, 0 failed, matching the expected count exactly (baseline 651 + 112 net new tests across the phase's 7 plans). `ruff check` and `ruff format --check` are both clean on `src/aquacal`.

---

_Verified: 2026-07-23_
_Verifier: Claude (gsd-verifier)_
