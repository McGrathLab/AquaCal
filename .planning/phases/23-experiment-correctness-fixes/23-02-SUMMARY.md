---
phase: 23-experiment-correctness-fixes
plan: 02
subsystem: experiments
tags: [experiments, e4, provenance, verification-gates, pandas]

# Dependency graph
requires: []
provides:
  - "resolve_e2_benchmark_path(out_dir): out-dir-relative resolution of E2's real-rig benchmark.json, never falling back across machines"
  - "compare_experiment_csv(..., exclude_columns=...): shared mechanism for excluding checking-path artifacts from --check's cell comparison, header contract untouched"
  - "CHECK_EXCLUDED_COLUMNS: E4's named, measurement-backed --check exclusion list"
  - "always-red-gate process finding in .planning/knowledge-base.md § Known Issues"
affects: [26-full-suite-driver-and-handoff-readiness]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Provenance resolver returns (value_or_None, human-readable_note) rather than raising or silently falling back across machine boundaries"
    - "Verification-gate exclusion lists are named module-level constants at the consuming call site, not defaults in the shared comparison helper"

key-files:
  created: []
  modified:
    - experiments/e4_benchmark_grid.py
    - experiments/_io.py
    - tests/unit/test_experiments_e4.py
    - tests/unit/test_experiments_io.py
    - .planning/knowledge-base.md

key-decisions:
  - "D-09: fixed both build_grid_dataframe callers (_run_check at :1876, _run_full at :1954), not just the main aggregation path -- the corrected call-site names per the 2026-08-17 planning correction (build_grid_dataframe is never called from _run_smoke_cells)"
  - "D-07: CHECK_EXCLUDED_COLUMNS is a named, exactly-two-entry list local to e4_benchmark_grid.py, not a default in the shared compare_experiment_csv mechanism -- growing it requires a deliberate decision"
  - "D-08: the exclude_columns mechanism lives in experiments/_io.py (shared), the list lives in e4_benchmark_grid.py (E4-local) -- Phase 26 (DRIVER-03) documents this same contract"
  - "The header comparison in compare_experiment_csv is never affected by exclude_columns -- a genuine schema change still fails loudly even for a named column"

requirements-completed: [FIX-05]

# Metrics
duration: 45min
completed: 2026-08-17
---

# Phase 23 Plan 02: E4 --out-relative E2 resolution and the named --check exclusion contract

**FIX-05 landed as two commits: a resolver that stops E4's aggregator from ever importing another machine's real-rig row under `--out`, and a named two-column `--check` exclusion that turns a structurally always-red gate into a real one.**

## Performance

- **Duration:** ~45 min
- **Tasks:** 2
- **Files modified:** 5

## Accomplishments

- Added `resolve_e2_benchmark_path(out_dir)` to `experiments/e4_benchmark_grid.py`: three explicit branches (native `benchmark.json` under `--out`, the `__file__`-anchored default-tree constant, or `None` — never fall back across machines).
- Both `build_grid_dataframe` callers (`_run_check`, `_run_full`) now resolve through it and log the provenance note; `build_grid_dataframe` accepts `e2_benchmark_path=None` and degrades to the existing `record_source="missing_e2_benchmark"` row rather than raising.
- Added a keyword-only `exclude_columns: tuple[str, ...] = ()` parameter to `compare_experiment_csv` (`experiments/_io.py`): drops named columns from the cell-level comparison only, after the (unmodified) header check, defaulting to today's exact byte-identical behavior.
- Declared `CHECK_EXCLUDED_COLUMNS = ("exit_code", "status_reason")` in `e4_benchmark_grid.py` with its measurement and rationale; `_run_check` passes it and prints what was skipped on every run, pass or fail.
- Recorded the always-red-gate pattern as a process finding in `.planning/knowledge-base.md` § Known Issues (D-10).
- Ran `python -u -m experiments.e4_benchmark_grid --check` once, read-only, against the default tree: exit 0, nothing written.

## Task Commits

1. **Task 1: FIX-05 — resolve E2's real-rig record relative to --out at both call sites** - `e89e1fb` (fix)
2. **Task 2: The named --check exclusion (D-07/D-08), plus the always-red process finding (D-10)** - `2a5c18d` (fix)

**Plan metadata:** (this commit, docs)

## Files Created/Modified

- `experiments/e4_benchmark_grid.py` — `resolve_e2_benchmark_path`, `CHECK_EXCLUDED_COLUMNS`, both callers updated
- `experiments/_io.py` — `compare_experiment_csv(..., exclude_columns=())`
- `tests/unit/test_experiments_e4.py` — 6 new tests (resolver branches, both-callers source guard, exclusion list, `_run_check` source guard)
- `tests/unit/test_experiments_io.py` — 3 new tests (`exclude_columns` behavior, header contract untouched, default reproduces today's exact behavior)
- `.planning/knowledge-base.md` — new § Known Issues entry, "A verification gate that cannot pass is worse than no gate (D-10)"

## Evidence

**Pre-fix `--check` baseline** (measured 2026-08-17, `.planning/probes/2026-08-17-phase-23-recon/e4_check_detail.py`, 35 columns x 10 rows, run against the committed tree before this plan's changes):

- 9 of 10 cells mismatched.
- Mismatching columns exactly `exit_code` and `status_reason`.
- 33 of 35 columns (33 metric columns) reproduced to 1e-6 — the aggregation itself was already sound; only the two checking-path artifacts failed.
- `exit_code`: `_run_check` hardcodes `"exit_code": None` (no subprocess runs under `--check`) while the committed CSV holds `0.0` from the real run.
- `status_reason`: an empty-string-versus-`NaN` round-trip through CSV.

**Two call sites that imported `E2_BENCHMARK_PATH` directly** (both now fixed):

- `_run_check` at `e4_benchmark_grid.py:1876` (pre-fix line number; verified against the corrected planning-inputs note, since `_run_smoke_cells` never calls `build_grid_dataframe`).
- `_run_full` at `e4_benchmark_grid.py:1954` (pre-fix line number).

**Post-fix resolution rule, in one sentence:** both callers now resolve E2's record via `resolve_e2_benchmark_path(out_dir)`, which returns the native `out_dir/benchmark.json` if present, else the `__file__`-anchored default-tree constant if `out_dir` is the default tree, else `None` — a non-default `--out` with no native record never imports the repo tree's record.

**Post-fix `--check` corroboration** (2026-08-17, read-only, default tree): exit 0; stdout named both `exit_code` and `status_reason` as skipped; `git status --porcelain experiments/results` produced no output before or after.

### Ledger candidate

None from this plan — see `23-CONTEXT.md` § Amendment 2026-08-17: no plan in this phase writes `.planning/MANUSCRIPT-FINDINGS.md`. The bound-hit table ledger candidate belongs to plan 23-01.

## Decisions Made

- **D-09 (corrected 2026-08-17):** the two call sites are `_run_check` and `_run_full`; `_run_smoke_cells` never calls `build_grid_dataframe` (verified against source, contradicting the original planning inputs).
- **D-07/D-08:** the exclusion mechanism is shared (`experiments/_io.py`), the list is E4-local (`e4_benchmark_grid.py`) — see key-decisions above.
- Kept `build_grid_dataframe`'s existing marked-absent-row degradation contract (`record_source="missing_e2_benchmark"`) rather than the todo's literal wording ("emit the CSV without the real-rig row") — preserves `GRID_COLUMNS`/`write_grid_latex`'s stable schema, satisfying the todo's actual intent ("absent and announced, never silently imported") without a header change that would itself defeat `--check`.

## Deviations from Plan

None — plan executed exactly as written, including the 2026-08-17 correction block naming the true call sites.

## Issues Encountered

- Two test-fixture missteps caught and fixed during development (not deviations from the plan's substance): one new `--check`-exclusion test initially chose a *key* column (`model`) to differ, which produces a key-set mismatch rather than a cell mismatch — switched to a non-key float column (`gt_x_m`). One new resolver test asserted the "default tree" branch's provenance note specifically, but on this machine `experiments/results/benchmark.json` already exists, so branch 1 (native) fires first and is path-equal to branch 2 by design — relaxed the assertion to check the resolved path and its absoluteness, which is what the plan's acceptance criteria actually require.

## User Setup Required

None — no external service configuration required.

## Next Phase Readiness

- FIX-05 is complete; `experiments/e4_benchmark_grid.py`'s `--check` and full-run paths are both out-dir-safe.
- The `exclude_columns` mechanism in `experiments/_io.py` is available for Phase 26 (DRIVER-03) to document as the formal `--check` contract; this plan's list and Phase 26's documentation must not diverge (D-08).
- No blockers for the next plan in this wave.

---
*Phase: 23-experiment-correctness-fixes*
*Completed: 2026-08-17*

## Self-Check: PASSED

All modified files (experiments/e4_benchmark_grid.py, experiments/_io.py,
tests/unit/test_experiments_e4.py, tests/unit/test_experiments_io.py,
.planning/knowledge-base.md) and this SUMMARY.md verified present on disk.
Both task commits (e89e1fb, 2a5c18d) verified present in git log.
