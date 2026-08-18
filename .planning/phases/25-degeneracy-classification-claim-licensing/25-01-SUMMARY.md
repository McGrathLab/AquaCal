---
phase: 25-degeneracy-classification-claim-licensing
plan: 01
subsystem: calibration
tags: [degeneracy, observability, optimization, out-parameters, numpy]

# Dependency graph
requires:
  - phase: 24
    provides: "`degeneracy_breakdown_out`, its D-06b allocate-only-when-requested discipline, the `NAN_REASON_*` int8 codes, and the `DISCARD_STAGES` entry-time validation"
provides:
  - "`compute_residuals(..., degeneracy_details_out=, observation_depths_out=)` — two opt-in per-observation sinks, inert when None"
  - "`DEGENERACY_DETAIL_ROW_CAP_PER_STAGE` (50k) and `OBSERVATION_DEPTH_ROW_CAP_PER_STAGE` (200k)"
  - "`optimize_interface` and `joint_refinement` accept and forward both sinks, stamping `stage`, `n_flagged_at_stage` / `n_observations_at_stage`, and `truncated`"
  - "7 unit tests, including an i/k index-space guard and an exact-equality geometry check"
affects: [25-02, 25-03, 26]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Opt-in per-observation out-parameter sink, zero cost when None (extends the Phase 24 aggregate-sink pattern to row granularity)"
    - "Caller-side stamping of stage/provenance columns onto library-produced rows"

key-files:
  created:
    - .planning/phases/25-degeneracy-classification-claim-licensing/25-01-SUMMARY.md
  modified:
    - src/aquacal/calibration/_optim_common.py
    - src/aquacal/calibration/interface_estimation.py
    - src/aquacal/calibration/refinement.py
    - tests/unit/test_optim_common.py
    - tests/unit/test_discard_accounting.py

key-decisions:
  - "The flagged-row sink is guarded independently of `degeneracy_breakdown_out` rather than nested inside `if record_degeneracy:` — a detail sink that silently emits nothing unless a breakdown dict is also supplied would be a coupling bug, and every stated acceptance criterion still holds."
  - "The angle column is `chord_incidence_deg`, never `exit_angle_deg`: the refracted exit angle is unrecoverable for a flagged observation because the Newton loop runs only over `valid_indices`."
  - "The two row caps deliberately differ (50k vs 200k) because the two populations differ by ~370x, not because either was tuned."
  - "The `truncated` / `n_*_at_stage` stamps are applied at the call site, from the independent counter, so the aggregate is never derived from `len(rows)`."

patterns-established:
  - "Row-cap discipline: stop appending at the cap, warn exactly once on the transition, and stamp every emitted row so the artifact alone discloses truncation."
  - "Index-space discipline: `k` over the flagged subset, `i` over the full point set, with an inline comment naming the hazard and a test built to make a mix visible."

requirements-completed: [DEGEN-04]

# Metrics
duration: 55min
completed: 2026-08-18
---

# Phase 25 Plan 01: Per-Observation Degeneracy Detail Sinks Summary

**`compute_residuals` can now emit one raw-geometry row per flagged observation and one `h_q` row per evaluated observation, both opt-in and bit-identically inert when unused, with `stage` and truncation provenance stamped at the two post-solve call sites.**

## Performance

- **Duration:** ~55 min
- **Tasks:** 2 of 2
- **Files modified:** 5 (3 library, 2 test)
- **Commits:** 2 task commits + this docs commit

## Accomplishments

### Task 1 — the two sinks in `compute_residuals` (`a1ca422`)

- Added `degeneracy_details_out: list[dict] | None = None` and
  `observation_depths_out: list[dict] | None = None`, both immediately after
  `degeneracy_breakdown_out`.
- Added `DEGENERACY_DETAIL_ROW_CAP_PER_STAGE = 50_000` and
  `OBSERVATION_DEPTH_ROW_CAP_PER_STAGE = 200_000` in the `#:` Sphinx-comment form used by
  `INVALID_PROJECTION_PENALTY_PX`, with comments stating why the two values differ (E2's
  flagged population is ~198 rows; its evaluated population is 73,975 per stage, so the
  flagged cap would truncate exactly the table D-09 needs complete).
- Widened the `nan_reason` allocation condition to
  `record_degeneracy or record_details or record_all_depths` and extended its D-06b comment
  to name both new sinks. The array is still allocated only on the single post-solve
  evaluation.
- The flagged block recomputes `h_c`, `h_q`, `r_q` from the expressions transcribed verbatim
  from `refractive_geometry.py:661,675,676-679`, plus
  `chord_incidence_deg = degrees(arctan2(r_q, h_c + h_q))`.
- The full-population block sits outside `if invalid.any():` so a clean (camera, frame) pair
  still contributes its rows.
- Both blocks stop at their cap and warn exactly once on the transition, per sink.
- Docstring entries written in the register of `degeneracy_breakdown_out`'s: meters, +Z-down
  world frame, `h_q` as a statement about the *estimate* evaluated *at the solution*,
  `nan_reason` as an int8 code with no bucket name in the library, `chord_incidence_deg` as a
  surrogate and explicitly not the refracted angle, and `stage` as the caller's to add.
- 5 tests added to `tests/unit/test_optim_common.py` in a new
  `TestPerObservationDetailSinks`, reusing `TestInvalidProjectionKeepsGradient._packed`.

### Task 2 — threading and stamping at both call sites (`34b4354`)

- `optimize_interface` and `joint_refinement` gained the two parameters in the slot after
  `discard_stage`, with identical diffs and identical docstring entries.
- Each post-solve site allocates a local list only when the caller passed one, forwards it to
  `compute_residuals` beside the existing `invalid_count_out=` / `degeneracy_breakdown_out=`,
  then stamps every row in place before extending the caller's list:
  `stage = resolved_discard_stage`, `n_flagged_at_stage = n_invalid` (from `invalid_counts[0]`),
  `truncated = len(rows) < n_invalid`; and for the depth sink,
  `n_observations_at_stage = degeneracy_breakdown["observations_evaluated"]`.
- The existing D-06b comment block at each site was extended to name the two new sinks and to
  quantify why they must not reach `cost_args` (~480M rows on E1's non-refractive arm).
- Nothing was added to `cost_args`; `grep -c "cost_args.append\|cost_args +"` outside comments
  is 0.
- 2 tests added to `tests/unit/test_discard_accounting.py`.

## Verification

| Check | Result |
|---|---|
| `pytest tests/unit/test_optim_common.py -q` | 66 passed |
| `pytest tests/unit/test_discard_accounting.py -q` (with the above) | 102 passed total, 98.6 s |
| `pytest tests/unit/test_optim_common.py -k "detail_sink or observation_depths" -q` | 5 passed |
| `pytest -k "detail_rows_carry_a_legal_stage_label or row_cap_truncates" -q` | 2 passed |
| `grep -n "chord_incidence_deg" _optim_common.py` | 4 hits |
| `grep -c "exit_angle_deg" _optim_common.py` | 0 |
| bucket names outside comments in `_optim_common.py` | 8, unchanged from the pre-edit baseline (`git show HEAD:...`) |
| `grep -c "degeneracy_details_out"` in `interface_estimation.py` / `refinement.py` | 9 / 9 — equal and non-zero |
| `grep -rn "discard_stage=" src/` | the same 5 sites; no sixth added |
| `ruff check` / `ruff format --check` | clean on all 5 touched files |

All test runs used `PYTHONPATH="$(pwd)/src"` and were verified to resolve `aquacal` inside the
worktree, not the main checkout. The full suite was **not** run — that is the orchestrator's
post-merge gate.

### Mutation checks (the tests were verified to fail on the bug they exist to catch)

Two deliberate mutations were introduced and reverted:

1. `nan_reason[i]` → `nan_reason[k]` in the flagged row →
   `test_detail_sink_index_spaces_do_not_cross` fails on
   `all(r["nan_reason"] != NAN_REASON_NONE)`.
2. `detection.corner_ids[i]` → `[k]` →
   `test_detail_sink_recomputed_geometry_matches_projector` fails on `h_q_m`.

The index-space test alone does not catch mutation 2; the geometry test does. Both are needed.

## Deviations from Plan

### Auto-fixed / adjusted

**1. [Rule 2 — missing critical functionality] The flagged-row sink is guarded independently of `record_degeneracy`**

- **Found during:** Task 1
- **Issue:** The plan's wording placed the detail sub-block *inside* `if record_degeneracy:`.
  That would make `degeneracy_details_out` silently emit nothing whenever a caller supplied it
  without also supplying a `degeneracy_breakdown_out` dict — an invisible coupling between two
  independent opt-in parameters, and exactly the kind of silent-no-op defect this project has
  been bitten by before.
- **Fix:** The `if degeneracy_details_out is not None:` block sits at the same level as
  `if record_degeneracy:`, both inside `if invalid.any():`. Every acceptance criterion in the
  plan still holds, and the tests that compare row count against the breakdown pass both sinks.
- **Files modified:** `src/aquacal/calibration/_optim_common.py`
- **Commit:** `a1ca422`

**2. [Rule 3 — blocking] The row-cap test needed a scene with more than 3 flagged observations**

- **Found during:** Task 2
- **Issue:** The plan named no scene for the row-cap test, and the existing pinned degenerate
  scene (`seed=2, depth_range=(0.155, 0.18)`) yields only 2 flagged observations — fewer than
  the patched cap of 3, so truncation would never trigger.
- **Fix:** Swept 24 (seed, depth_range) combinations through `optimize_interface` to find a
  scene that both flags enough observations and solves fast. `seed=5,
  depth_range=(0.151, 0.175)` yields **14** flagged in ~2.7 s and is now pinned in the test,
  which asserts `n_flagged > 3` up front so a future drift in that count fails loudly rather
  than silently disarming the test. `seed=0, depth_range=(0.152, 0.17)` (3 flagged, ~1 s) is
  pinned for the stage-label test.
- **Files modified:** `tests/unit/test_discard_accounting.py`
- **Commit:** `34b4354`

**3. [Rule 1 — bug] The partially-flagged test scene had to be re-derived from the board's corner table**

- **Found during:** Task 1
- **Issue:** `test_detail_sink_index_spaces_do_not_cross` needs a view whose flagged corner ids
  are non-contiguous, so an off-by-index-space read lands on a wrong value. Parking the tilted
  board at `z = water_z` flagged all 20 corners, because the charuco board's local origin is at
  a corner (x from 0 to 0.132 m), not at the board center — so the whole board sat at or below
  the interface.
- **Fix:** Read the board's actual transformed corner table (z spans 0.0903 m under a 0.6 rad
  tilt about Y) and offset the pose to 0.195 m so the crossing lands mid-board. The flagged set
  is now the two columns nearest the surface in every row — `{3,4,8,9,13,14,18,19}` — which is
  genuinely non-contiguous. The test asserts non-contiguity explicitly rather than assuming it.
- **Files modified:** `tests/unit/test_optim_common.py`
- **Commit:** `a1ca422`

### Not deviations

- **STATE.md and ROADMAP.md were deliberately not touched** — the orchestrator owns those
  writes after the wave merges.
- No package was installed; Phase 25 adds no dependency.

## Interfaces Delivered (for plans 25-02 and 25-03)

```python
compute_residuals(
    ...,
    degeneracy_details_out: list[dict] | None = None,
    observation_depths_out: list[dict] | None = None,
) -> NDArray[np.float64]
```

Flagged row as it leaves `compute_residuals`:
`{"camera": str, "frame_idx": int, "corner_id": int, "h_q_m": float, "h_c_m": float,
"r_q_m": float, "chord_incidence_deg": float, "extended": bool, "nan_reason": int}`

…plus, stamped by `optimize_interface` / `joint_refinement`:
`{"stage": str, "n_flagged_at_stage": int, "truncated": bool}`

Full-population row:
`{"camera": str, "frame_idx": int, "corner_id": int, "h_q_m": float, "nan_reason": int}`

…plus `{"stage": str, "n_observations_at_stage": int, "truncated": bool}`.

Module constants: `DEGENERACY_DETAIL_ROW_CAP_PER_STAGE = 50_000`,
`OBSERVATION_DEPTH_ROW_CAP_PER_STAGE = 200_000` (both in
`aquacal.calibration._optim_common`).

## Known Stubs

None. No hardcoded empty value, placeholder string, or unwired data path was introduced.

## Notes for the Next Plan

- **The library still spells no bucket name.** `nan_reason` leaves as an int8 code and
  `chord_incidence_deg` as a raw angle. Plan 25-03's classifier in
  `experiments/_degeneracy.py` owns the taxonomy, and the sink deliberately gives it nothing to
  disagree with.
- **`chord_incidence_deg` is not an exit angle.** Any downstream prose or column heading that
  calls it one would be wrong: the Newton loop never ran for these points, so no refraction
  point exists.
- **`truncated` is per-row, not a header field.** Both the flagged and the depth rows carry it,
  so a CSV writer can emit it as an ordinary column and a reader of the file alone cannot
  mistake a capped table for a complete one.

## Self-Check: PASSED

- All 5 modified files and the SUMMARY exist on disk.
- Both task commits exist in `git log`: `a1ca422`, `34b4354`.
- Neither commit deleted a tracked file (`git diff --diff-filter=D` empty for both).
- Working tree clean apart from this SUMMARY at the time of the check.
- STATE.md and ROADMAP.md are untouched.
