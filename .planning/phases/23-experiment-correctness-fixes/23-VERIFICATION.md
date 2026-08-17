---
phase: 23-experiment-correctness-fixes
verified: 2026-08-17T16:01:54Z
status: passed
score: 6/6 must-haves verified
overrides_applied: 0
---

# Phase 23: Experiment Correctness Fixes Verification Report

**Phase Goal:** The suite's E1, E6, E7, E4, E2, and synthetic-generator outputs are numerically and
textually correct, so downstream phases build the driver and run against a fixed, trustworthy
suite rather than a moving target.

**Verified:** 2026-08-17T16:01:54Z
**Status:** passed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths (ROADMAP § Phase 23 Success Criteria)

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | E1's non-refractive arm pins `water_z`, verified by recovered `water_z` reading GT 1.031 m (guard count 0 as corroboration only) | ✓ VERIFIED | `water_z_bounds` threaded end-to-end: `_optim_common.py:530` (param), `interface_estimation.py` (1 forward), `refinement.py` (1 forward), `pipelines.py:170,204` (both stage-3 passes). Orchestrator's Task 3 runtime probe (already established) measured `water_z_recovered_m = 1.030999999999`, guard count 0. `resolve_water_z_pin` and `WATER_Z_PIN_HALF_WIDTH` present in `e1_refractive_comparison.py`. |
| 2 | E1 and E7 solve with the interface normal free (`normal_fixed=False`), matching production DOF; combined pinned+free config measured | ✓ VERIFIED | `e1_refractive_comparison.py:420` passes `normal_fixed=False` to `calibrate_synthetic`; 3 benchmark writers record `"normal_fixed": False` (lines 691, 798, 1035). `e7_interface_ablation.py` declares `E7_NORMAL_FIXED = False` (:165), used at both solver call sites (:338, :371) and in the payload (:563). Orchestrator's runtime probe confirmed both arms' records show `normal_fixed: false`. |
| 3 | E6 reports signed, gauge-corrected Z error plus per-camera decomposition, both behind the collinear caveat | ✓ VERIFIED | `E6_COLUMNS` has 33 entries including `water_z_error_mm_signed_mean` and `z_position_error_mm_gauge_corrected_mean` (confirmed live: `python -c "..."` → `33 True True`). `compute_water_z_error_mm_signed` and `build_per_camera_rows`/`E6_PER_CAMERA_COLUMNS` present; `gauge_correct_z=True` called at the E6 call site while `git diff` shows `pipelines.py`'s default untouched by this plan. |
| 4 | E7's `fixed` rows are labelled vacuous-by-construction, not a measured `no_signature` verdict | ✓ VERIFIED | `degeneracy_verdict({...nan corr, zero signs, n_seeds=10...})` returns `vacuous_by_construction` (confirmed live). `VACUOUS_SCOPE_SUFFIX` present exactly once, wired into `build_focal_standoff_df`'s `scope` column — no schema change. |
| 5a | E4's aggregator resolves E2's benchmark row correctly under a custom `--out`, at both call sites including `_run_check` | ✓ VERIFIED | `resolve_e2_benchmark_path(out_dir)` defined at `e4_benchmark_grid.py:252`; called at both `_run_check` (:1959) and `_run_full` (:2055). `CHECK_EXCLUDED_COLUMNS = ("exit_code", "status_reason")` declared; `compare_experiment_csv` gained `exclude_columns` param in `_io.py:338`, forwarded at `:1979`. |
| 5b | The four stale provenance sites in `e2_real_rig.py`/`synthetic.py` describe what is true; `19.1-E2-FRAMESET-PROVENANCE.md` carries a supersession header, not an edit | ✓ VERIFIED | `21889922` appears ≥2x, `18645385` ≥2x (both sites corrected consistently) in `e2_real_rig.py`; `0.8240` (live value) appears 0 times (no hardcoded live value); `synthetic.py` names `1.0738404` and retains `WATER_Z: float = 1.031` unchanged. `19.1-E2-FRAMESET-PROVENANCE.md` opens with `> **SUPERSEDED...`; historical body preserved (verified via plan's own pure-insertion diff evidence). |
| 6 | FIX-05 is verified by something other than `--check`, or a `--check` whose contract excludes `exit_code`/`status_reason` | ✓ VERIFIED | `CHECK_EXCLUDED_COLUMNS` exclusion contract implemented in `_io.py`/`e4_benchmark_grid.py` as described above; FIX-05 was primarily verified via `tmp_path` unit tests per the plan's explicit correction that `--smoke` does not exercise `build_grid_dataframe`. |

**Score:** 6/6 truths verified

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `src/aquacal/calibration/_optim_common.py` | `water_z_bounds` override on `build_bounds` | ✓ VERIFIED | Param, docstring, override logic present at :530, :545, :585 |
| `src/aquacal/datasets/pipelines.py` | forwards `water_z_bounds` to both stage-3 passes | ✓ VERIFIED | Forwarded at :170 and :204; library default (`gauge_correct_z=False` on `compute_per_camera_errors`) untouched |
| `experiments/e1_refractive_comparison.py` | pin mechanism, `normal_fixed=False`, D-04 provenance, `water_z_recovered_m` | ✓ VERIFIED | `resolve_water_z_pin`, `build_water_z_provenance`, 3x `water_z_pin_mechanism`/`water_z_recovered_m` occurrences (writer coverage) |
| `experiments/e7_interface_ablation.py` | `normal_fixed=False` at both solver call sites + provenance | ✓ VERIFIED | `E7_NORMAL_FIXED` constant referenced at 3 sites |
| `experiments/e4_benchmark_grid.py` | out-dir-relative resolver + named `--check` exclusion | ✓ VERIFIED | `resolve_e2_benchmark_path`, `CHECK_EXCLUDED_COLUMNS`, both call sites wired |
| `experiments/_io.py` | `compare_experiment_csv(..., exclude_columns=())` | ✓ VERIFIED | Param present, header comparison unaffected |
| `experiments/e6_generalization_sweep.py` | signed + gauge-corrected columns, per-camera table | ✓ VERIFIED | 33-column `E6_COLUMNS`, `E6_PER_CAMERA_COLUMNS`, checkpoint schema_version 2 |
| `experiments/e7_focal_standoff_analysis.py` | `vacuous_by_construction` verdict + scope suffix | ✓ VERIFIED | Verified live via `degeneracy_verdict` call |
| `experiments/e2_real_rig.py` | 3 corrected provenance strings | ✓ VERIFIED | `21889922`/`18645385` counts confirmed, `0.8240` absent |
| `src/aquacal/datasets/synthetic.py` | corrected `height_above_water` docstring | ✓ VERIFIED | `1.0738404` present, `WATER_Z` constant unchanged |
| `.planning/phases/19.1-experiment-suite-consolidation/19.1-E2-FRAMESET-PROVENANCE.md` | supersession header, unmodified body | ✓ VERIFIED | First line is the header; original H1 intact below |
| `.planning/knowledge-base.md` | always-red-gate process finding (D-10) | ✓ VERIFIED | § "A verification gate that cannot pass is worse than no gate (D-10)" present at :265 |
| `tests/unit/test_stale_provenance_strings.py` | source-text regression guard | ✓ VERIFIED | File exists, all its tests pass |

### Key Link Verification

| From | To | Via | Status | Details |
|------|-----|-----|--------|---------|
| `e1_refractive_comparison.py::_run_one_model` | `pipelines.calibrate_synthetic` | `water_z_bounds` kwarg | ✓ WIRED | Confirmed via source read (Task 1 acceptance criteria matched) |
| `interface_estimation.py::optimize_interface` | `build_bounds` | `water_z_bounds=water_z_bounds` | ✓ WIRED | grep -c = 1 |
| `refinement.py::joint_refinement` | `build_bounds` | `water_z_bounds=water_z_bounds` | ✓ WIRED | grep -c = 1 |
| `e4_benchmark_grid.py::_run_check` | `resolve_e2_benchmark_path` | out-dir-relative resolution | ✓ WIRED | Called at :1959 |
| `e4_benchmark_grid.py::_run_full` | `resolve_e2_benchmark_path` | out-dir-relative resolution | ✓ WIRED | Called at :2055 |
| `e4_benchmark_grid.py::_run_check` | `compare_experiment_csv` | `exclude_columns=CHECK_EXCLUDED_COLUMNS` | ✓ WIRED | Confirmed at :1979 |
| `e6_generalization_sweep.py::compute_configuration_metrics` | `compute_per_camera_errors` | `gauge_correct_z=True` second call | ✓ WIRED | grep confirms presence; library default untouched |
| `e7_focal_standoff_analysis.py::degeneracy_verdict` | `e7_focal_standoff.csv` scope column | vacuous branch | ✓ WIRED | Live call returns correct verdict string |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| `resolve_water_z_pin` resolves scenario GT | live python import/call in prior orchestrator session | `1.031 None` | ✓ PASS (already established) |
| `degeneracy_verdict` vacuous classification | `python -c "import experiments.e7_focal_standoff_analysis as m; print(m.degeneracy_verdict(...))"` | `vacuous_by_construction` | ✓ PASS |
| E6 column count/names | `python -c "import experiments.e6_generalization_sweep as m; print(len(m.E6_COLUMNS), ...)"` | `33 True True` | ✓ PASS |
| E1/E7 `normal_fixed` wiring | grep + source read | `normal_fixed=False` at every call site | ✓ PASS |
| E4 resolver wiring | grep source read | both call sites use resolver | ✓ PASS |
| FIX-06 stale-string absence/presence | grep counts on `e2_real_rig.py`/`synthetic.py` | matches plan's acceptance criteria exactly | ✓ PASS |

### Probe Execution

No dedicated `scripts/*/tests/probe-*.sh` files exist for this phase; verification vehicles were unit
tests plus the orchestrator's already-established E1 runtime probe (Task 3 of plan 23-01, documented
above in `<already_established_do_not_redo>` and not re-run per CLAUDE.md guidance).

Targeted pytest re-run by this verifier (not the full suite):
```
python -m pytest tests/unit/test_stale_provenance_strings.py tests/unit/test_e7_focal_standoff.py tests/unit/test_experiments_io.py -q -m "not slow"
→ 68 passed

python -m pytest tests/unit/test_optim_common.py tests/unit/test_experiments_e1.py tests/unit/test_experiments_e4.py tests/unit/test_experiments_e6.py tests/unit/test_experiments_provenance.py -q -m "not slow"
→ 462 passed, 25 skipped, 2 deselected
```
Both exit 0, confirming the merged tree (`330f9ef`+) has no regression, corroborating the already-
established full-suite gate result (1865 passed, 25 skipped, 0 failed).

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|--------------|-------------|--------------|--------|----------|
| FIX-01 | 23-01 | Pin `water_z` in E1's non-refractive arm | ✓ SATISFIED | `water_z_bounds` threading + `resolve_water_z_pin`; runtime-probed 1.030999999999 m |
| FIX-02 | 23-01 | E1/E7 solve with interface normal free | ✓ SATISFIED | `normal_fixed=False` at every call site, AST test guards recurrence |
| FIX-03 | 23-03 | E6 signed/gauge-corrected Z error + per-camera table | ✓ SATISFIED | 33-column `E6_COLUMNS`, per-camera table wired |
| FIX-04 | 23-03 | E7 `fixed` rows labelled vacuous-by-construction | ✓ SATISFIED | `degeneracy_verdict` branch confirmed live |
| FIX-05 | 23-02 | E4 resolves E2 row relative to `--out`, both call sites | ✓ SATISFIED | `resolve_e2_benchmark_path` wired at both sites; exclusion contract implemented |
| FIX-06 | 23-04 | Four stale provenance strings corrected | ✓ SATISFIED | grep-verified counts match plan's acceptance criteria; supersession header confirmed |

**Orphaned requirements:** None. `.planning/REQUIREMENTS.md` § Experiment Correctness (FIX) lists
exactly FIX-01 through FIX-06, all six claimed by the four phase-23 plans (`requirements:` frontmatter
in `23-01`/`23-02`/`23-03`/`23-04-PLAN.md` covers the full set).

**Note:** `.planning/REQUIREMENTS.md`'s checkboxes (lines 28-58) and its tracking table (lines
214-219) still show `[ ]`/"Pending" for FIX-01..06, and `ROADMAP.md`'s own Phase 23 goal line is
marked `[x]` complete. This is a documentation-sync gap in `REQUIREMENTS.md`, not a code-correctness
gap — every requirement is independently verified against the codebase above. Flagged for the
orchestrator to update `REQUIREMENTS.md`'s tracking, not a phase-goal blocker.

### Anti-Patterns Found

None. Scanned all twelve files modified across the four plans for `TBD`/`FIXME`/`XXX`/`TODO`/`HACK`/
`PLACEHOLDER` markers — zero matches.

### Human Verification Required

None. All six success criteria are source-level/unit-test verifiable, and FIX-01/FIX-02's runtime
behavior was already established via the orchestrator's foreground E1 probe at commit `330f9ef`
(documented in the task prompt's `<already_established_do_not_redo>` block) — re-running it would
violate CLAUDE.md's "never background a long run" guidance for no additional evidentiary value.

### Gaps Summary

No gaps. All six ROADMAP.md § Phase 23 success criteria are verified directly against the codebase:
source reads, live Python calls, grep counts matching the plans' own acceptance criteria, and a
targeted (non-full-suite) pytest re-run — 530 tests total across the touched modules, all passing.
The one documentation-sync item (`REQUIREMENTS.md` checkboxes) does not affect the phase goal:
"the suite's outputs are numerically and textually correct" is a codebase property, verified true.

---

*Verified: 2026-08-17T16:01:54Z*
*Verifier: Claude (gsd-verifier)*
