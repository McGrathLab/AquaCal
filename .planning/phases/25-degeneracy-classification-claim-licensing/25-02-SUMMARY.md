---
phase: 25-degeneracy-classification-claim-licensing
plan: 02
subsystem: calibration
tags: [degeneracy, observability, config, csv-sidecar, diagnostics]

# Dependency graph
requires:
  - phase: 25
    plan: 01
    provides: "`optimize_interface` / `joint_refinement` accepting `degeneracy_details_out=` and `observation_depths_out=`, with `stage` / `n_*_at_stage` / `truncated` already stamped"
provides:
  - "`CalibrationConfig.log_all_observation_depths: bool = False`, reachable from YAML as `internals: {log_all_observation_depths: true}`"
  - "run-scoped `degeneracy_details` (always on) and `observation_depths` (None unless the flag is set) accumulators in `run_calibration_from_config`, filled by both stage-3 calls"
  - "`save_diagnostic_report(..., degeneracy_details=, observation_depths=)` writing `degenerate_observations.csv` and `all_observation_depths.csv`, non-empty only"
  - "`DEGENERATE_OBSERVATION_COLUMNS` and `OBSERVATION_DEPTH_COLUMNS` — the pinned column orders"
  - "3 unit tests (1 config round-trip, 2 sidecar presence/absence)"
affects: [25-06, 26, 29]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Config-flag path copied end to end from `save_conditioning`: field + `Attributes:` entry + `bool()`-coerced `internals` parse + constructor arg + `aquacal init` template line"
    - "Presence-is-the-signal artifact: an empty population writes NO file, so the sidecar's existence is itself the alarm"
    - "Column order pinned in a module constant and applied via `DataFrame.reindex`, so the artifact's shape never depends on dict insertion order"

key-files:
  created:
    - .planning/phases/25-degeneracy-classification-claim-licensing/25-02-SUMMARY.md
  modified:
    - src/aquacal/config/schema.py
    - src/aquacal/calibration/pipeline.py
    - src/aquacal/cli.py
    - src/aquacal/validation/diagnostics.py
    - tests/unit/test_pipeline.py
    - tests/unit/test_diagnostics.py

key-decisions:
  - "The column order lives in a module constant (`DEGENERATE_OBSERVATION_COLUMNS`) rather than as a literal at the write site, so the test can assert against the same object the writer uses and a future column addition cannot drift the two apart."
  - "`if degeneracy_details:` (truthiness) rather than `is not None` — it collapses the `None` and `[]` cases into the one contract D-08 states, and the test pins BOTH inputs so the collapse is deliberate rather than incidental."
  - "The config-flag test went into `tests/unit/test_pipeline.py`, not `test_internals.py`: `load_config` lives in `pipeline.py` and the two real analogs (the defaults blocks and `test_load_config_with_internals_and_seed`) are both in that file."

patterns-established:
  - "Mutation-verify a column-order assertion by deleting the `reindex` call: the hand-built test rows are written with their keys deliberately OUT of documented order, so a writer relying on insertion order fails loudly."

requirements-completed: [DEGEN-04]

# Metrics
duration: 50min
completed: 2026-08-18
---

# Phase 25 Plan 02: Config Flag and User-Facing Degeneracy Sidecar Summary

**A user whose rig flags even one observation now finds `degenerate_observations.csv` beside `diagnostics.json` without asking for it, while the ~10 MB full-population `h_q` table stays behind a default-off config field whose state is recorded in the run's own provenance.**

## Performance

- **Duration:** ~50 min
- **Tasks:** 3 of 3
- **Files modified:** 6 (4 library, 2 test)
- **Commits:** 3 task commits + this docs commit

## Accomplishments

### Task 1 — the D-09 config flag and its four plumbing hops (`fdb78a6`)

- `CalibrationConfig.log_all_observation_depths: bool = False` added immediately after
  `benchmark_memory` in the observability cluster, with the same trailing-inline-comment form.
- `Attributes:` docstring entry written in the register of `save_conditioning`'s: what it turns
  on, where the output lands (`output_dir/all_observation_depths.csv`), the ~74k rows/stage and
  ~10 MB cost on the 13-camera rig, that it is off by default, and that it is consumed only by
  the post-solve residual evaluation and never inside the solve.
- `load_config` parses it as
  `bool(internals.get("log_all_observation_depths", False))` — the same coercion every sibling
  `internals` flag uses (T-25-04) — and passes it to the constructor beside `benchmark_memory=`.
- `cli.py`'s `internals:` template gained the commented line, in `save_conditioning`'s style.
- Tests: the `False` default asserted in **both** defaults blocks in `test_pipeline.py`
  (`:170` valid-config and `:249` omitted-sections backward-compatibility), plus a new
  `test_log_all_observation_depths_defaults_off_and_round_trips` asserting both the
  absent-key `False` and the explicit `True` round-trip through `load_config`.

### Task 2 — threading both sinks through the two stage-3 calls (`ab62613`)

- Two run-scoped accumulators declared beside `discard_stats`:
  `degeneracy_details: list[dict] = []` always, and
  `observation_depths: list[dict] | None = [] if config.log_all_observation_depths else None`
  — so the ordinary run exercises plan 25-01's `None` inert path and pays nothing.
- Both passed into `optimize_interface(...)` inside `_run_stage3` and into
  `joint_refinement(...)` in the intrinsic pass.
- A comment at the accumulator records that both accumulate **across** stage-3 calls,
  including the second `_run_stage3` invocation when `reject_outlier_frames` fires; that
  double-count is inherited from the Phase 24 counters (the published 198 is itself a
  cross-stage sum) and the per-row `stage` stamp is what makes the distinct count recoverable.
- No sixth `discard_stage=` site was added and `pipeline.py:156`'s
  `_calibrate_from_detections` helper was left alone.

### Task 3 — the D-08 sidecar and the full-population table (`a212d5a`)

- `save_diagnostic_report` gained `degeneracy_details: list[dict] | None = None` and
  `observation_depths: list[dict] | None = None`, appended last exactly as `discard_stats` was.
- Non-empty writes `output_dir/degenerate_observations.csv` (key `degenerate_observations`) and
  `output_dir/all_observation_depths.csv` (key `all_observation_depths`); `None` or `[]` writes
  **no file and registers no key** — D-08's exact contract.
- `DEGENERATE_OBSERVATION_COLUMNS` and `OBSERVATION_DEPTH_COLUMNS` module constants pin the
  documented order, applied via `DataFrame.reindex(columns=...)`.
- Docstring entries written in `discard_stats`' register, including the "why this exists"
  clause, the meters units on `h_q_m`/`h_c_m`/`r_q_m`, `nan_reason` as an int8 code whose
  taxonomy lives in `experiments/_degeneracy.py` (the library spells no bucket name, D-06), and
  that `truncated` + `n_*_at_stage` let a reader of the file alone detect truncation (D-10).
  Both files added to the `Creates:` and `Returns:` lists.
- The single `pipeline.py` call site passes both accumulators.
- 2 tests added to `TestSaveDiagnosticReport`.

## Verification

| Check | Result |
|---|---|
| `pytest tests/unit/test_pipeline.py -q` (after Task 1) | 89 passed, 177 s |
| `pytest tests/unit/test_pipeline.py tests/unit/test_discard_accounting.py -q` (after Task 2) | 125 passed, 298 s |
| `pytest tests/unit/test_diagnostics.py -q` (after Task 3) | 36 passed, 3.8 s |
| `pytest tests/unit/test_pipeline.py -q` (after Task 3) | 89 passed, 160 s |
| `pytest tests/unit/test_diagnostics.py -k degenerate_sidecar -v` | 2 passed |
| `grep -rn "discard_stage=" src/ \| wc -l` | 5 — the same five sites, no sixth |
| `grep -vE '^\s*#' pipeline.py \| grep -c "degeneracy_details_out"` | 2 |
| `grep -vE '^\s*#' pipeline.py \| grep -c "degeneracy_details="` | 1 |
| `grep -vE '^\s*#' diagnostics.py \| grep -c "degenerate_observations.csv"` | 4 (>= 1) |
| `grep -c PipelineConfig` in schema.py / pipeline.py | 0 / 0 — the wrong class name was not introduced |
| `ruff check` / `ruff format --check` on all 6 touched files | clean |

All test runs used `PYTHONPATH="$(pwd)/src"` and `aquacal.__file__` was verified to resolve
inside the worktree. The full suite was **not** run — that is the orchestrator's post-merge
gate. No calibration and no experiment was run.

### Mutation check

Deleting the `.reindex(columns=list(DEGENERATE_OBSERVATION_COLUMNS))` call made
`test_degenerate_sidecar_written_when_rows_present` fail on the column-list assertion, and
left the absent-case test passing. The test rows are hand-built with `truncated` first and
`stage` last precisely so insertion order cannot accidentally match the documented order. The
mutation was reverted.

## Deviations from Plan

### Auto-fixed

**1. [Rule 3 — blocking] `ruff format` reflowed two of the lines this plan added**

- **Found during:** Task 1
- **Issue:** The `bool(internals.get("log_all_observation_depths", False))` assignment and the
  new test's `def` line both exceed the line-length limit, so the pre-commit `ruff format` hook
  would have rejected the commit.
- **Fix:** Ran `ruff format` on both files before staging. Baseline formatting of the
  pre-edit `pipeline.py` was confirmed clean first, so the reflow is attributable to this
  plan's lines and not to a pre-existing violation.
- **Files modified:** `src/aquacal/calibration/pipeline.py`, `tests/unit/test_pipeline.py`
- **Commit:** `fdb78a6`

### Process note (no code impact)

During Task 3 a `git checkout -- src/aquacal/validation/diagnostics.py`, intended to revert the
deliberate mutation, discarded the whole unstaged task's edits to that file. All of them were
reconstructed and the tests re-run green before committing; the committed state is the intended
state. The lesson: **stage before mutating**, or revert the mutation by re-applying the inverse
edit rather than by a file-level checkout.

### Not deviations

- **STATE.md and ROADMAP.md were deliberately not touched** — the orchestrator owns those
  writes after the wave merges.
- `experiments/` and `tests/unit/test_discard_accounting.py` were not modified; the latter was
  only *read* (executed) as a regression gate, which is plan 25-03's file.
- No package was installed.

## Interfaces Delivered (for plan 25-06 and Phase 26)

```yaml
internals:
  log_all_observation_depths: true   # E2 only; default false
```

```python
save_diagnostic_report(
    ...,
    degeneracy_details: list[dict] | None = None,
    observation_depths: list[dict] | None = None,
) -> dict[str, Path]   # keys "degenerate_observations" / "all_observation_depths" when written
```

`degenerate_observations.csv` columns, in order:
`camera, frame_idx, corner_id, stage, h_q_m, h_c_m, r_q_m, chord_incidence_deg, extended,
nan_reason, n_flagged_at_stage, truncated`

`all_observation_depths.csv` columns, in order:
`camera, frame_idx, corner_id, stage, h_q_m, nan_reason, n_observations_at_stage, truncated`

Both orders are importable as
`aquacal.validation.diagnostics.DEGENERATE_OBSERVATION_COLUMNS` /
`OBSERVATION_DEPTH_COLUMNS` — a downstream reader should assert against these rather than
hard-coding the list.

## Known Stubs

None. No hardcoded empty value, placeholder string, or unwired data path was introduced. Both
sinks are wired end to end: solver → run-scoped accumulator → report writer → CSV on disk.

## Threat Flags

None. This plan adds no network endpoint, auth path, or schema change at a trust boundary. The
one external input (`internals.log_all_observation_depths` from a local, user-authored YAML) is
`bool()`-coerced per T-25-04, and T-25-05's disk-exhaustion path stays mitigated by the
default-off flag plus plan 25-01's `OBSERVATION_DEPTH_ROW_CAP_PER_STAGE`.

## Notes for the Next Plan

- **`chord_incidence_deg` is not an exit angle.** The CSV header and the docstring both say so;
  any downstream prose or LaTeX caption calling it a refracted angle would be wrong.
- **The sidecar's absence is meaningful, not a failure.** A consumer must treat a missing
  `degenerate_observations.csv` as "nothing was flagged", never as "the writer broke".
- **The rows are the cross-stage union.** A `stage`-agnostic `len()` over the CSV will
  double-count any observation flagged in both stage-3 passes; group by `stage` first.

## Self-Check: PASSED

- All 6 modified files and the SUMMARY exist on disk.
- All 3 task commits exist in `git log`: `fdb78a6`, `ab62613`, `a212d5a`.
- No commit deleted a tracked file (`git diff --diff-filter=D 10f7c4e..HEAD` is empty).
- STATE.md and ROADMAP.md are untouched.
