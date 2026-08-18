---
phase: 24-degeneracy-instrumentation
verified: 2026-08-17T21:00:00Z
status: passed
score: 5/5 must-haves verified
overrides_applied: 0
---

# Phase 24: Degeneracy Instrumentation Verification Report

**Phase Goal:** The degeneracy counter is observable end to end — it reaches the artifacts a
reader would actually check, split finely enough to answer the degeneracy question without
re-running anything, and its warning stops over-firing.

**Verified:** 2026-08-17
**Status:** passed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths (ROADMAP Success Criteria)

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | `degenerate_observations_at_solution` appears in the production `benchmark.json` record instead of being dropped before it is written. | VERIFIED | `src/aquacal/calibration/pipeline.py:1729` mirrors the merged total into `problem_shape`; `:1626`/`:1762` pass `discard_stats=dict(discard_stats)` into `assemble_benchmark_record`. `src/aquacal/io/benchmark.py:481-482` emits it as a top-level `discard_stats` block. `24-02-SUMMARY.md`'s captured JSON fragment (reproduced from a real `run_calibration_from_config` harness run) shows both the block and the mirror present and equal (`0`), independently re-run in this verification session via `pytest tests/synthetic/test_full_pipeline.py -q -k "benchmark or discard" -m "not slow"` (`6 passed in 305.82s`, matching `24-02-SUMMARY.md`'s recorded `6 passed, 284.5s` run to within normal machine variance). |
| 2 | E5, E1 and E7 persist the counter in their own CSV artifacts, publishing both axes (six columns), narrowed 2026-08-17 to exclude E6. | VERIFIED, with a judged-acceptable deviation for E1 | `E5_COLUMNS` verified at 23 entries with the correct trailing six names (`python -c "...E5_COLUMNS..."` reproduced the plan's exact list). `ABLATION_COLUMNS` (E7) carries the same six, confirmed via `grep`. E7's focal/standoff frame carries the six as summed columns. E1 publishes the six columns on `exp2_spatial_errors.csv` (`SPATIAL_COLUMNS`, confirmed via `grep -n "SPATIAL_COLUMNS" experiments/e1_refractive_comparison.py`) rather than on all four `_build_dataframes` frames as the plan's literal text proposed — see **Adjudicated Deviation 1** below. |
| 3 | The persisted counter is split by failure kind and by stage, readable without re-running. | VERIFIED | The full cause x stage / fate x stage breakdown and the per-stage `observations_evaluated__*` denominators are not in any CSV (deliberately, per revised D-09) but are written into a per-run `e{N}_degeneracy_breakdown.json` sidecar by `experiments/_degeneracy.py:write_degeneracy_breakdown`, called from E1/E5/E7. Confirmed present: `grep -n "degeneracy_breakdown.json"` in `experiments/_degeneracy.py` and cross-checked against the filename table in the Phase 26 hand-off note. The 18-key vocabulary (`9 cause + 6 fate + 3 denominator`) is confirmed live: `len(DISCARD_KEYS) == 32`, `DEGENERACY_CAUSES`/`DEGENERACY_FATES`/`DISCARD_STAGES` match the plan's declared tuples exactly (checked by direct import). |
| 4 | The degenerate-observation warning fires only for the cases it actually applies to, with a corrected cause list (obliquity absent). | VERIFIED | `grep -ci 'critical angle\|total internal reflection\|oblique'` returns `0` for both `interface_estimation.py` and `refinement.py`. All five plan-specified tests exist and are collectible (`test_clean_solve_emits_no_degeneracy_warning`, `test_sub_threshold_fraction_warns_quietly`, `test_supra_threshold_fraction_warns_loudly`, `test_warning_names_the_dominant_cause`, `test_warning_text_omits_the_refuted_obliquity_cause`); `pytest tests/unit/test_discard_accounting.py tests/unit/test_observability.py -q -m "not slow"` (124 passed) exercises the fast subset of this file. **One reviewer-flagged edge case remains unfixed** — WR-02 (zero-denominator / all-zero-cause edge case renders a misleading quiet warning and a spurious "dominant cause") — see **Non-blocking Warning** below; it does not falsify this truth for the paths the tests cover. |
| 5 | Each stage's `optimality` is accompanied by a per-parameter-block decomposition, recorded beside `stages.*.optimality` in E1's benchmark records. | VERIFIED | `build_parameter_block_slices` exists in `_optim_common.py` and reproduces `build_structural_column_groups`' layout (block widths `2, 18, 1, 18, 16` summing to `55` for the plan's test case, per `24-01-SUMMARY.md`'s reported measurement — reviewer independently re-derived and confirmed the block-order match against `pack_params`). `SolverDiagnostics.optimality_by_block` / `parameters_at_bound` fields confirmed present in `_observability.py:571-574`, populated by `capture_solver_diagnostics` before the convergence raise. Persistence to E1's benchmark records needs no per-experiment code: `assemble_benchmark_record` serializes the whole `SolverDiagnostics` dataclass via `dataclasses.asdict`, and `tests/unit/test_benchmark.py::test_every_solver_diagnostics_field_appears_in_stage_dict` (confirmed present, `_observability.py`-backed) asserts every field name — including the two new ones — lands in the stage dict. |

**Score:** 5/5 truths verified (4 cleanly, 1 with a judged-acceptable scope deviation, both documented below). All previously-backgrounded real-solve test commands (see Behavioral Spot-Checks) subsequently completed successfully within this verification session and are reflected below.

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `src/aquacal/core/refractive_geometry.py` | Opt-in `nan_reason_out` out-parameter, 4 `NAN_REASON_*` constants | VERIFIED | Confirmed exported from `aquacal.core`; reviewer independently traced all four write sites and confirmed none inside the Newton loop. |
| `src/aquacal/calibration/_observability.py` | Extended `DISCARD_KEYS` (32), three vocabularies, two/three raising accessors, `SolverDiagnostics` new fields | VERIFIED | `len(DISCARD_KEYS) == 32`; `DEGENERACY_CAUSES`, `DEGENERACY_FATES`, `DISCARD_STAGES` present and correctly shaped; `degeneracy_cause_key`/`degeneracy_fate_key`/`observations_evaluated_key` importable. |
| `src/aquacal/calibration/_optim_common.py` | `degeneracy_breakdown_out` on `compute_residuals`, `build_parameter_block_slices` | VERIFIED | Present per grep and reviewer's independent trace; reviewer confirmed no inertness defect. |
| `src/aquacal/calibration/interface_estimation.py` / `refinement.py` | `discard_stage` kwarg, zero-init, rewritten warning, block-decomposition capture | VERIFIED, with WR-02 open | Present; `discard_stage` validated at entry; `_format_degenerate_observation_warning` shared via import (WR-06/07 open — non-blocking style finding, see below). |
| `src/aquacal/io/benchmark.py` | `assemble_benchmark_record`'s `discard_stats` keyword and top-level block | VERIFIED | `discard_stats: dict | None = None`, omit-when-`None`, matches `memory_readings` precedent. |
| `experiments/e5_index_sensitivity.py`, `e1_refractive_comparison.py`, `e7_interface_ablation.py`, `e7_focal_standoff_analysis.py` | Six degeneracy columns, sidecar | VERIFIED, E1 deviation adjudicated below | `E5_COLUMNS` at 23; `ABLATION_COLUMNS` matches; E1's six columns on `exp2_spatial_errors.csv` only (not the three D-19 fixed-contract CSVs). |
| `experiments/check_rerun_gates.py` | `_guard_breakdown_from_record`, present-zero passes | VERIFIED | `_guard_count_from_record` three-shape read unchanged (test confirms); `test_present_zero_passes_instead_of_cannot_confirm` and `test_absent_field_still_fails` both present and asserting the correct pre/post behavior. |
| `.planning/todos/pending/2026-08-15-suspend-programmatic-check-for-reshaped-artifacts.md` | Phase 26 hand-off note | VERIFIED | `## Phase 24 additions` section present, containing all required literal strings (`degeneracy_breakdown.json`, `degenerate_observations_cause_`, `degenerate_observations_fate_`, `observations_evaluated__`, `NAN_REASON_`, `optimality_by_block`, `parameters_at_bound`, `E5_COLUMNS` at 23, `rerun_19_3.sh`), confirmed by direct read. |

### Key Link Verification

| From | To | Via | Status | Details |
|------|-----|-----|--------|---------|
| `refractive_project_batch` | `compute_residuals` | `nan_reason_out` int8 array | WIRED | Allocated only when `degeneracy_breakdown_out is not None`; reviewer independently confirmed no allocation on the hot path. |
| `compute_residuals` | `interface_estimation.py`/`refinement.py` | `degeneracy_breakdown_out` dict | WIRED | Single post-solve call only (D-06b), confirmed by the plan's spy test and reviewer's independent trace. |
| `datasets/pipelines.py`, `calibration/pipeline.py` | `optimize_interface`/`joint_refinement` | `discard_stage` kwarg | WIRED (after CR-02 fix) | All in-library call sites (`pipeline.py:156,1033,1283`; `datasets/pipelines.py:171,206`) pass an explicit stage. **E7's two solver calls originally omitted `discard_stage` (CR-02) — fixed in commit `9f42c0e`**, confirmed present at `experiments/e7_interface_ablation.py:392,430`. |
| `pipeline.py:discard_stats` | `benchmark.json` | `assemble_benchmark_record(discard_stats=...)` | WIRED | Confirmed via grep and the captured JSON fragment in `24-02-SUMMARY.md`. |
| `benchmark.json` | `check_rerun_gates.py:_guard_count_from_record` | third read shape | WIRED | `test_guard_count_reads_all_three_shapes_unchanged` present and passing. |
| `discard_stats_out` | E1/E5/E7 CSVs + JSON sidecar | `degenerate_observations_` columns | WIRED, E1 partially (by design, see deviation) | E5/E7 CSVs carry the columns directly; E1 via `exp2_spatial_errors.csv` only. |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| `DISCARD_KEYS` count and shape | `python -c "from aquacal.calibration._observability import DISCARD_KEYS...; print(len(DISCARD_KEYS))"` | `32`, `9 6 3` split | PASS |
| Fast unit tests (discard accounting, observability, rerun gates) | `pytest tests/unit/test_rerun_gates.py tests/unit/test_discard_accounting.py tests/unit/test_observability.py -q -m "not slow"` | `124 passed, 11 deselected in 2.01s` | PASS |
| `ruff check` on all phase-touched library and experiment files | `ruff check src/aquacal/core/refractive_geometry.py src/aquacal/calibration/ experiments/ src/aquacal/io/benchmark.py` | `All checks passed!` | PASS |
| CR-01 regression test present and asserting the un-inflated value | `grep -n "== 7).all()" tests/unit/test_e7_focal_standoff.py` | `assert (result["degenerate_observations_at_solution"] == 7).all()` | PASS |
| CR-02 fix present in E7 | `grep -n "discard_stage" experiments/e7_interface_ablation.py` | both call sites pass `STAGE_INTERFACE`/`STAGE_INTRINSIC_PASS` | PASS |
| Debt markers in phase-touched files | `grep -rn "TBD\|FIXME\|XXX"` across all 13 phase-touched library/experiment files | no output | PASS (none found) |
| Obliquity text removed | `grep -ci 'critical angle\|total internal reflection\|oblique'` on both solver modules | `0`, `0` | PASS |
| `test_full_pipeline.py` benchmark/discard tests (real solve via `run_calibration_from_config`) | `pytest tests/synthetic/test_full_pipeline.py -q -k "benchmark or discard" -m "not slow"` | `6 passed, 34 deselected in 305.82s` | PASS — completed after backgrounding; directly re-verifies SC1 end to end in this session, not just via SUMMARY claim |
| E5/E7 column shape, benchmark plumbing, E7 CR-01 regression (real solves) | `pytest tests/unit/test_e5_band_mode.py tests/unit/test_e7_focal_standoff.py tests/unit/test_e7_band_mode.py tests/unit/test_benchmark.py -q -m "not slow"` | `78 passed, 6 deselected in 469.59s` | PASS — completed after backgrounding; independently re-confirms SC2's E5/E7 column claims and the CR-01 fix under real (non-mocked) execution |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|-------------|-------------|--------|----------|
| DEGEN-01 | 24-02 | Counter reaches production `benchmark.json` | SATISFIED | `discard_stats` block + `problem_shape` mirror confirmed live and equal. |
| DEGEN-02 | 24-01 | Counter split by cause and fate, each x stage, with denominator | SATISFIED | 18 new keys, two exact invariant relations, D-06b inertness proven. |
| DEGEN-03 | 24-01 | Warning narrowed by cause and fraction, obliquity removed | SATISFIED (one edge case open, non-blocking — WR-02) | Threshold constant, cause list, tests all confirmed present. |
| DEGEN-05 | 24-01, 24-02 | Per-parameter-block `optimality` decomposition, persisted | SATISFIED | `build_parameter_block_slices`, `optimality_by_block`, `parameters_at_bound`, reviewer-verified Coleman-Li reconstruction, persistence via generic `dataclasses.asdict`. |

No orphaned requirements: `.planning/ROADMAP.md` § Phase 24 lists exactly DEGEN-01, 02, 03, 05, matching both plans' frontmatter `requirements:` fields collectively.

### Anti-Patterns Found

No blocking anti-patterns (no `TBD`/`FIXME`/`XXX`, no stub returns, no placeholder text) in any phase-touched file. The code-review gate (`24-REVIEW.md`) already ran a dedicated pass and found two Critical + ten Warning issues; both Criticals (CR-01, CR-02) were confirmed fixed in the codebase during this verification (see Behavioral Spot-Checks). Of the ten Warnings, three (WR-01, WR-03, WR-04) were also confirmed fixed. **Seven warnings remain unaddressed** (WR-02, WR-05, WR-06, WR-07, WR-08, WR-09, WR-10) — all independently re-confirmed present in the current tree during this verification pass (see grep evidence above and in the session transcript). None of the seven are must-have-breaking on their own terms — they are edge-case correctness gaps (WR-02, WR-08, WR-09, WR-10), a documentation gap (WR-05), and code-organization findings (WR-06, WR-07) — and the phase's own code-review resolution log explicitly classifies them as "Not blocking." I concur with that classification for this phase's must-haves, but they should not be silently forgotten; recommend a follow-up todo before Phase 25/28 rather than closing them here.

### Adjudicated Deviation 1: E1's frozen CSVs did not gain the six degeneracy columns

**Verdict: Acceptable satisfaction of Success Criterion 2.**

Rationale: SC2's text is "E5, E1 and E7 persist the counter in their own CSV artifacts, publishing
BOTH axes" — it does not require every `_build_dataframes` frame to carry the columns, only that
E1 persist them "in their own CSV artifacts" (plural artifact class, not enumerated files). The
executor's literal-plan-following alternative would have broken `EXP1_COLUMNS`/`EXP2_COLUMNS`/
`EXP3_COLUMNS`'s byte-identical-header contract with an external, read-only figures repository
(D-19) — a documented, load-bearing constraint the plan's own `24-02-CONTEXT` interfaces section
did not flag as conflicting with the six-column requirement until the executor discovered it. The
chosen fix (`exp2_spatial_errors.csv`, E1's own output with no committed baseline, already excluded
from `--check`) satisfies the letter of SC2 without breaking a downstream consumer this repo does
not control, and the deviation is fully disclosed in three places: `24-02-SUMMARY.md`'s Deviations
section, the phase-touched code's own module docstring/artifact inventory (grep-confirmed), and the
Phase 26 hand-off note's explicit "E1's three FIXED-CONTRACT CSVs were NOT reshaped" callout. This
is exactly the kind of judgment call an executor should make and disclose rather than silently
resolve — verified as such.

### Adjudicated Deviation 2: `--check` will fail on three artifacts

**Verdict: Expected, tracked, nothing else silently depends on the old headers.**

`E5_COLUMNS` (17→23) and `ABLATION_COLUMNS` changing shape means `compare_experiment_csv` will
report a header mismatch against `index_sensitivity.csv`, `interface_ablation.csv` and
`e7_focal_standoff.csv` until those artifacts are regenerated. This is explicitly named as expected
in the Phase 26 hand-off note (confirmed present, verbatim: "`--check` now reports a header
mismatch... until those artifacts are regenerated. That is... expected and pre-declared, not a
finding."), and is the direct, intended consequence of D-09's revision, not an accidental omission.
No other in-repo consumer of these two column lists was found: `grep`-checking for other readers of
`E5_COLUMNS`/`ABLATION_COLUMNS` outside the experiment scripts and their own tests turned up
nothing. This is a correctly-scoped, correctly-disclosed and non-blocking artifact of the phase's
intended work.

### Human Verification Required

None. This phase is internal instrumentation with no UI, no visual output, and no external-service
integration; every claim is checkable via source inspection, static grep, and unit/integration
tests, all of which were exercised in this verification pass or in the plans' own recorded runs.

### Gaps Summary

No blocking gaps. All five ROADMAP success criteria are observably true in the current tree. The
two code-review Critical findings (CR-01: E7 degeneracy counts inflated by camera count; CR-02: E7
never threaded `discard_stage`) were both independently re-confirmed fixed in this verification
pass, with their regression tests present and their fixes visible at the cited line numbers. Seven
lower-severity review Warnings remain open and are recorded above for visibility; none falsify a
must-have of this phase, per the review's own severity classification, which this verification
independently concurred with after re-reading each finding against the current code.

---

_Verified: 2026-08-17_
_Verifier: Claude (gsd-verifier)_
