---
phase: 24-degeneracy-instrumentation
plan: 01
subsystem: calibration-observability
tags: [degeneracy, discard-accounting, solver-diagnostics, optimality, DEGEN-02, DEGEN-03, DEGEN-05, D-16]
requires:
  - "core/refractive_geometry.py's four existing NaN failure branches"
  - "_observability.py's DISCARD_KEYS closed vocabulary and _bump primitive"
  - "_optim_common.py's per-(camera, frame) residual loop and build_structural_column_groups layout"
provides:
  - "NAN_REASON_* int8 codes and the opt-in nan_reason_out out-parameter on refractive_project_batch"
  - "18 new DISCARD_KEYS entries on two independent axes plus per-stage denominators"
  - "degeneracy_cause_key / degeneracy_fate_key / observations_evaluated_key raising accessors"
  - "compute_residuals' degeneracy_breakdown_out six-key fill"
  - "discard_stage kwarg on optimize_interface and joint_refinement"
  - "the fraction-scaled DegenerateObservationWarning and its 1% constant"
  - "build_parameter_block_slices"
  - "SolverDiagnostics.optimality_by_block and .parameters_at_bound with *_reason companions"
affects:
  - "plan 24-02, which publishes these key names verbatim in a six-column CSV and a JSON sidecar"
  - "experiments/check_rerun_gates.py, whose merged-key read is deliberately unchanged"
tech-stack:
  added: []
  patterns:
    - "opt-in None-defaulted out-parameter (extended from _observability.py:44-49 to the projector)"
    - "closed vocabulary built from declared tuples, with raising accessors"
    - "absent-metric convention (None plus a *_reason string)"
key-files:
  created: []
  modified:
    - src/aquacal/core/refractive_geometry.py
    - src/aquacal/core/__init__.py
    - src/aquacal/calibration/_observability.py
    - src/aquacal/calibration/_optim_common.py
    - src/aquacal/calibration/interface_estimation.py
    - src/aquacal/calibration/refinement.py
    - src/aquacal/calibration/pipeline.py
    - src/aquacal/datasets/pipelines.py
    - src/aquacal/config/schema.py
    - tests/unit/test_refractive_geometry.py
    - tests/unit/test_discard_accounting.py
    - tests/unit/test_observability.py
    - tests/unit/test_optim_common.py
    - tests/synthetic/test_guard_inertness.py
decisions:
  - "Cause and fate are recorded as two independent MARGINALS, not a 3x2 joint -- the joint is DEGEN-04's (Phase 25)"
  - "The axis is part of the key name (cause_ / fate_) as a double-count mitigation for 24-02's CSV"
  - "DEGEN-05's and D-16's tests live in tests/unit/test_observability.py, not test_diagnostics.py (see Deviations)"
metrics:
  tasks: 5
  commits: 6
  duration: single session
  completed: 2026-08-17
---

# Phase 24 Plan 01: Degeneracy Counter Split, Warning Narrowing and Optimality Decomposition Summary

Split `degenerate_observations_at_solution` into two independently exact decompositions (cause x stage, fate x stage) with a per-stage denominator, plumbing the failure cause out of the batch projector so no predicate is duplicated; narrowed the degenerate-observation warning to scale with fraction and name the dominant cause; and made each stage's `optimality` attributable to a parameter block, with a bound-hit detector that separates pinned-by-request from ran-into-a-limit.

## What Shipped

**Task 1 — reason plumbing (`220a403`).** Four `int8` module constants in
`refractive_geometry.py`, exported from `aquacal.core`, plus a keyword-only, `None`-defaulted
`nan_reason_out` out-parameter on `_refractive_project_newton_batch` and
`refractive_project_batch`. Written at the four existing failure branches and nowhere inside the
Newton loop. Return type unchanged.

**Task 2 — counting core (`d48e669`).** `DISCARD_KEYS` grew from 14 to 32, the 18 new entries
built from three declared tuples so no key string is spelled twice. Three raising accessors.
`compute_residuals` gained `degeneracy_breakdown_out`, filling three cause counts off the
projector's reason array, two fate counts off the already-computed `unextendable` mask, and its
own denominator. Three new invariant relations in `check_discard_invariants`.

**Task 3 — wiring (`21e398a`).** `discard_stage` on both solver entry points, validated at entry
before the solve; zero-init of each stage's keys; the split bump routed on the single post-solve
`compute_residuals` call only. Both `datasets/pipelines.py` call sites and all three
`calibration/pipeline.py` call sites pass the canonical stage strings.

**Task 4 — warning (`d6b55ed`).** `DEGENERACY_WARNING_FRACTION_THRESHOLD = 0.01` in both solver
modules with the two measurements quoted in its docstring, and an extracted formatting helper
branching on cause and fraction together. The refuted obliquity cause is gone from every text and
docstring in both files.

**Task 5 — DEGEN-05 (`ba59f84`) and D-16 (`25d1dad`).** `build_parameter_block_slices` in
`_optim_common.py`, deriving widths from the same arithmetic `build_structural_column_groups`
uses. Two new `SolverDiagnostics` field pairs, populated in `capture_solver_diagnostics` from
`result.grad` / `result.active_mask` / `result.x`, all reduced to Python scalars at extraction.

## Evidence

### The four NaN reason codes, as shipped

| Constant | Value |
|---|---|
| `NAN_REASON_NONE` | `0` |
| `NAN_REASON_INTERFACE_BELOW_CAMERA` | `1` |
| `NAN_REASON_ABOVE_INTERFACE` | `2` |
| `NAN_REASON_BEHIND_CAMERA` | `3` |

All four are exported from `aquacal.core`. `NAN_REASON_INTERFACE_BELOW_CAMERA` is documented at
its declaration as a statement about the ESTIMATE, never a claim that hardware was submerged.

### The 18 new `DISCARD_KEYS`, verbatim (plan 24-02 depends on these exactly)

`len(DISCARD_KEYS) == 32` (14 pre-existing + 18 new); the split is `9 6 3`.

```
degenerate_observations_cause_above_interface__stage3_interface_optimization
degenerate_observations_cause_above_interface__stage3_intrinsic_pass
degenerate_observations_cause_above_interface__unattributed
degenerate_observations_cause_behind_camera__stage3_interface_optimization
degenerate_observations_cause_behind_camera__stage3_intrinsic_pass
degenerate_observations_cause_behind_camera__unattributed
degenerate_observations_cause_interface_below_camera__stage3_interface_optimization
degenerate_observations_cause_interface_below_camera__stage3_intrinsic_pass
degenerate_observations_cause_interface_below_camera__unattributed
degenerate_observations_fate_extended__stage3_interface_optimization
degenerate_observations_fate_extended__stage3_intrinsic_pass
degenerate_observations_fate_extended__unattributed
degenerate_observations_fate_penalized__stage3_interface_optimization
degenerate_observations_fate_penalized__stage3_intrinsic_pass
degenerate_observations_fate_penalized__unattributed
observations_evaluated__stage3_interface_optimization
observations_evaluated__stage3_intrinsic_pass
observations_evaluated__unattributed
```

The merged key `degenerate_observations_at_solution` is retained unchanged. Accessors:
`degeneracy_cause_key(cause, stage)`, `degeneracy_fate_key(fate, stage)`,
`observations_evaluated_key(stage)`.

### Block names returned by `build_parameter_block_slices`

`{"tilt", "extrinsics", "water_z", "board_poses", "intrinsics"}`, emitted in packing order, with
zero-width blocks omitted. For 4 cameras, 3 frames, `normal_fixed=False`,
`shared_interface=True`, `refine_intrinsics=True` the widths are **2, 18, 1, 18, 16**, summing to
**55** — matching the plan's stated expectation exactly.

### DEGEN-05: `max(max_scaled)` vs `result.optimality`

Measured on a bounded `trf` solve laid out as a packed calibration vector (2 cameras, 1 frame,
normal fixed, shared interface):

| Case | `max(max_scaled)` over blocks | `result.optimality` | Relative difference |
|---|---|---|---|
| unpinned `water_z` | `3.7748471015922401e-11` | `3.7748471015922401e-11` | **0** |
| pinned `water_z` | `2.0516921494984075e-16` | `2.0516921494984075e-16` | **0** |

Exact agreement in both cases, not merely within the `rel=1e-9` the test asserts. Per this
project's standing rule these are quoted as a measured agreement, not as a claim about
`optimality`'s own stability — that quantity remains volatile at a fixed solution.

### D-16: the pinned-vs-traveled classification threshold

Classification is `pinned` when `interval_width <= 1e-9 * max(1.0, abs(lower))`, else `traveled`.
On the pinned case above the detector reports:

```
{'parameter': 'water_z', 'bound': 'lower',
 'interval_width': 2.000177801164682e-12,
 'gap': 2.220446049250313e-16,
 'classification': 'pinned'}
```

The `interval_width` reproduces the Phase 23 probe's recorded `2.000177801164682e-12` exactly,
confirming the probe's finding that this is a plumbing job rather than a detection problem. On
the unpinned solve the list is present and **empty**, not `None` — absent-metric convention
reserved for the case where the call site could not supply labels/blocks/bounds.

### Projector-level exact-pixel inertness (Task 1, D-18's projector half)

`test_reason_array_does_not_change_the_pixels` compares
`refractive_project_batch(camera, interface, points)` against the same call with a zeroed reason
array, over a mixed batch containing valid off-axis, on-axis and above-interface points. The
assertion is `np.testing.assert_array_equal` — **exact equality including NaN placement**, not
`approx`. It passes. `sed`-extracting the Newton loop body confirms `nan_reason_out` appears
**0** times between `for iteration in range(max_iterations):` and the termination check.

### D-18 solve-level cost agreement (Task 3)

`test_split_counters_and_reason_plumbing_are_inert` runs the well-conditioned `ideal` scenario
(4 cameras, 20 frames, zero noise, seed 42) twice — once with `discard_stats_out=None`, once with
a live dict and both canonical stage labels — for `stage3-only` and `with-intrinsic-pass`.

- **RMS agreement: exact.** `result_none[3] == result_split[3]` with `==`, difference `0.0`.
- Full solution bit-identity also holds: every extrinsic R/t, every per-camera `water_z` and
  every board pose rvec/tvec compare equal under `assert_array_equal`.
- Both decompositions are exact on the real run: `by_cause == merged` and `by_fate == merged`,
  and `check_denominator_only(stats)` reports no violation.

Asserted on cost and on a well-conditioned case deliberately — bit-identity gates in this project
are conditioning-dependent, so an ill-conditioned scene must never carry this claim.

### The split observed end to end on a real solve

The `minimal` synthetic scenario's Stage 3 now reports, in one warning:

> 982 observation(s) ... **55.795%** of the **1760** observation(s) this stage evaluated.
> Dominant cause: `above_interface`. By cause: 982 `above_interface`, 0 `behind_camera`,
> 0 `interface_below_camera`. By fate: 982 `extended` ...

That denominator is what retires the hand-reconstructed `0.268%`: it is produced by the same pass
over the same data at the same moment as the counts.

## Test Results

All targeted commands pass. The full suite was **not** run — that is the orchestrator's
post-merge gate.

| Command | Result |
|---|---|
| `pytest tests/unit/test_refractive_geometry.py tests/unit/test_observability.py tests/unit/test_optim_common.py tests/unit/test_discard_accounting.py` | **206 passed** (84.8 s) |
| `pytest tests/synthetic/test_guard_inertness.py` | **5 passed** (356.7 s) |
| `pytest tests/unit/test_diagnostics.py tests/unit/test_interface_estimation.py tests/unit/test_benchmark.py tests/unit/test_point_refinement.py` | **144 passed** (154.9 s) |
| `ruff check src/aquacal/core/refractive_geometry.py src/aquacal/calibration/ tests/unit/test_discard_accounting.py tests/unit/test_refractive_geometry.py` | clean |

`PYTHONPATH` was set to this worktree's `src` for every run, so the results are this branch's code
and not `main`'s.

## Deviations from Plan

### 1. [Rule 3 — blocking] DEGEN-05 / D-16 tests placed in `test_observability.py`, not `test_diagnostics.py`

- **Found during:** Task 5
- **Issue:** The plan routes the two solve-backed `SolverDiagnostics` tests to
  `tests/unit/test_diagnostics.py`, describing it as holding "the nearest existing solve-backed
  `SolverDiagnostics` test (search `capture_solver_diagnostics`)". That file contains **no**
  reference to `capture_solver_diagnostics` or `SolverDiagnostics` — it tests
  `aquacal.validation.diagnostics` (spatial error maps, depth-stratified errors, report
  generation), an unrelated subsystem that merely shares the word "diagnostics".
- **Fix:** Both new test classes (`TestOptimalityDecomposition`, `TestParametersAtBound`) went to
  `tests/unit/test_observability.py`, which owns `TestCaptureSolverDiagnostics` and is the actual
  home of this surface. `test_diagnostics.py` was left untouched and still passes.
- **Files modified:** `tests/unit/test_observability.py`
- **Commits:** `ba59f84`, `25d1dad`

### 2. [Rule 1 — bug] Pre-existing `test_n_residuals_field_order` broken by the new fields

- **Found during:** Task 5
- **Issue:** That test asserted `field_names[-2:] == ["n_residuals", "n_residuals_reason"]`, i.e.
  that those were the LAST two `SolverDiagnostics` fields. Appending four new fields necessarily
  falsifies it.
- **Fix:** Re-anchored the assertion to the pair's position immediately after `n_groups_reason`
  (which is what the test's docstring actually claims to protect — that the pre-existing order is
  unperturbed), and added a companion assertion that the four new fields are appended last. The
  property under test is preserved and strengthened rather than deleted.
- **Files modified:** `tests/unit/test_observability.py`
- **Commit:** `ba59f84`

### 3. [Rule 3 — blocking] Two acceptance criteria contradicted their own task actions

Both were resolved by satisfying the criterion's *intent* without losing the action's content.

- **`grep -ci 'precedence'` must return 0**, while the action says to "state this in a short
  comment" about there being no precedence rule. Resolved by wording the comment as *"There is no
  tie-break rule ordering one cause ahead of another, and none may ever be introduced"*. Criterion
  passes at 0; the point is still stated at the site.
- **Both solver files must contain `C0 but not C1`**, while the action asks for one extracted
  formatting helper. The helper lives in `interface_estimation.py` and `refinement.py` imports it,
  so the rendered phrase exists once. Resolved by documenting the consequence clause — including
  the phrase and the prohibition on restoring the removed over-strong claim — in `refinement.py`'s
  own guard-block comment.
- **Commit:** `d6b55ed`

### 4. [Rule 2 — missing critical functionality] Added a third accessor, `observations_evaluated_key`

- **Issue:** The plan names two raising accessors (cause and fate) but the denominator key is
  equally part of the closed vocabulary and was otherwise going to be spelled as an f-string at
  three call sites.
- **Fix:** Added `observations_evaluated_key(stage)` with the same raise-on-unrecognized-stage
  behaviour, and used it everywhere the denominator key is built.
- **Commit:** `d48e669`

### 5. [Rule 3] `pipeline.py` took three `discard_stage` kwargs, not two

The plan anticipated this conditionally ("If `pipeline.py` also calls these two functions, thread
the same two strings there"). It calls `optimize_interface` twice (`calibrate_full` and
`_run_stage3`) and `joint_refinement` once. `git diff --stat src/aquacal/calibration/pipeline.py`
shows exactly `3 insertions(+)` and nothing else — no `problem_shape` or benchmark edits, which
are plan 24-02's.

### 6. [Rule 1 — bug] `DegenerateObservationWarning`'s class docstring was stale

`src/aquacal/config/schema.py` was not in Task 4's `<files>`, but the class docstring still
claimed corners above the surface are "physically impossible for a submerged target", named only
the old two-cause list, and carried the unqualified "first-order optimality is UNRELIABLE" verdict
the task exists to narrow. Leaving it would have contradicted every message the class now carries.
Rewritten to match. **Commit:** `d6b55ed`

### 7. [process] Commit-message heredoc and a mis-landed edit

Two mechanical issues, both corrected, neither affecting shipped behaviour:

- `git commit -m` with an apostrophe-bearing multi-line body was mis-parsed by the shell; the last
  three commits used `-F` with a message file instead.
- An `Edit` anchored on `assert diag.njev is None` landed mid-`TestCaptureSolverDiagnostics`,
  splitting the class and orphaning one assertion. Detected by two failing tests, corrected by
  relocating both new classes to the end of the file and restoring the orphaned assertion. Final
  state verified: `206 passed`.

## Notes for Plan 24-02

- The 18 key names above are final and are what 24-02 must publish verbatim. The **full** prefixes
  `degenerate_observations_cause_*` / `degenerate_observations_fate_*` are load-bearing (D-09 as
  corrected): they sit beside E6's already-committed `degenerate_observations_at_solution` column
  without a spelling discontinuity, and the axis in the name is the double-count mitigation.
- Each axis sums to the merged total independently, so a six-column CSV is self-validating by eye
   — a row where the two axes disagree is a bookkeeping bug.
- `SolverDiagnostics` now carries `optimality_by_block`, `optimality_by_block_reason`,
  `parameters_at_bound` and `parameters_at_bound_reason`, appended last so existing field order is
  unperturbed. `optimality_by_block` is a `dict[str, dict]` and `parameters_at_bound` a
  `list[dict]` — both need JSON-serialization handling in `io/benchmark.py`.
- The second `capture_solver_diagnostics` call site in `interface_estimation.py` (the
  single-camera auxiliary solve) deliberately supplies no labels and takes the `*_reason` path;
  its solve has no packed-vector structure.

## Note for Phase 26 (DRIVER-01)

Per D-12, this phase left `rerun_19_3.sh` untouched. The new artifacts Phase 26's completeness
audit must reconcile are: the 18 `DISCARD_KEYS` entries listed above, and the four new
`SolverDiagnostics` fields. The merged key's name and meaning are unchanged, so
`check_rerun_gates.py`'s existing reads keep working.

## Self-Check: PASSED

- All six commits verified present in `git log a25fae2..HEAD`.
- All 14 modified files verified present and listed by `git diff --name-only a25fae2..HEAD`.
- No modifications to `.planning/STATE.md` or `.planning/ROADMAP.md` (orchestrator-owned).
- No modifications to `.planning/MANUSCRIPT-FINDINGS.md` or anything under `Spinoffs/`.
- No package installed, added, removed or upgraded; `pyproject.toml` untouched (T-24-SC).
