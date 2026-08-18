---
phase: 26-full-suite-driver-handoff-readiness
plan: 04
subsystem: experiments
tags: [driver, check, baseline, cli, DRIVER-03]
requires:
  - "26-01 (the archive at experiments/pre_rerun_baseline/)"
  - "experiments/_io.compare_experiment_csv (unchanged)"
provides:
  - "experiments._io.add_baseline_dir_argument"
  - "experiments._io.resolve_baseline_dir"
  - "experiments._io.compare_experiment_csv_if_present"
  - "experiments.e3_derived_quantities --baseline-dir"
  - "experiments.e3_derived_quantities._validate_e3_args"
affects:
  - "26-06 (E2 consumes compare_experiment_csv_if_present + --baseline-dir)"
  - "26-07 (the driver stage that passes --baseline-dir)"
tech-stack:
  added: []
  patterns:
    - "Script-local argparse flag helper, deliberately outside the shared five-flag parent parser"
    - "Caller-side guard wrapping a total function rather than weakening its totality contract"
key-files:
  created: []
  modified:
    - experiments/_io.py
    - experiments/e3_derived_quantities.py
    - tests/unit/test_experiments_io.py
decisions:
  - "D-12 implemented as a script-local flag: build_experiment_arg_parser still exposes exactly five flags"
  - "Ruling A4 implemented as compare_experiment_csv_if_present; compare_experiment_csv still raises on a missing baseline"
  - "E3 treats a missing baseline as a FAILURE, not N/A -- all three of its baselines are committed by design"
  - "_validate_e3_args runs BEFORE the shared validate_args so the script-local flag is named in the error"
metrics:
  duration: "~35 min"
  completed: 2026-08-18
  tasks: 2
  commits: 4
---

# Phase 26 Plan 04: `--baseline-dir` and the Missing-Baseline N/A Guard Summary

E3's `--check` can now read its committed baselines from the archive DRIVER-04 moved them
into, and a baseline that is absent by DATA-01b policy reports N/A from a caller-side
wrapper instead of raising `FileNotFoundError` after a 50–87 minute calibration.

## What Was Built

**Task 1 — `experiments/_io.py` helpers** (`375f895`, tests `7bd9905`)

Three module-level helpers, placed immediately before `write_direct_call_benchmark` so a
reader meets the guard and the guarded function together:

- `add_baseline_dir_argument(parser)` — adds exactly one optional `--baseline-dir` of type
  `Path` defaulting to `None`, returns the parser, and raises `argparse.ArgumentError` on a
  duplicate rather than silently defining the flag twice. Its docstring states why it is
  script-local (widening `build_experiment_arg_parser` would change the CLI of all ten
  experiment scripts to serve two) and names both callers, E3 here and E2 in plan 26-06.
- `resolve_baseline_dir(baseline_dir, out_dir)` — `Path(baseline_dir)` when given, else
  `Path(out_dir)`. Unlike `resolve_out_dir` it neither creates nor logs: a `--check` run
  that mkdir'd its own baseline tree would manufacture the exact "nothing to compare
  against" state it exists to detect. A test asserts nothing is created.
- `compare_experiment_csv_if_present(...)` — the ruling-A4 guard. Returns `None` for a
  missing path, otherwise exactly what `compare_experiment_csv` returns. Its docstring
  states that the guard is here and not inside `compare_experiment_csv` because that
  function's totality contract at `:348-357` deliberately excludes I/O errors, names the
  concrete motivating case (E2's `reprojection_residuals.csv` and
  `reconstruction_errors.csv`, gitignored at `.gitignore:238-239`, present in neither
  `experiments/results/` nor the archive), and explicitly declines to extend `exit_code_for`
  to accept `None` — whether an absent baseline is benign is a per-call-site judgement.

The `exclude_columns` docstring block gained the DRIVER-03 contract it already promised to
stay in step with (D-13): cell-level only, the full-header comparison is never affected,
the sole in-repo list is `CHECK_EXCLUDED_COLUMNS` at `e4_benchmark_grid.py:215`, and
Phase 26 adds no new exclusion list.

**Task 2 — E3 plumbing** (`18f448a`, tests `7f0fe8a`)

`build_arg_parser` calls `add_baseline_dir_argument`; a new `_validate_e3_args` rejects
`--baseline-dir` with `--force` and `--baseline-dir` without `--check`; `_run_check` gained
a keyword-only `baseline_dir: Path | None = None` and resolves all three baseline paths
under `resolve_baseline_dir(baseline_dir, out_dir)`, printing the resolved directory
(T-26-11). The three write paths still target `out_dir` — only the read path moved.

The D-10 rationale was **written**, not merely rewritten: the retired "capture state before
`--force` destroys it" wording was not present anywhere in E3 (`grep -c` was already 0), so
the operative reason now appears in `_run_check`'s docstring — E3 is one of only two
experiments whose `--check` is still a real reproduction signal — carrying RESEARCH SP-5's
honest qualification that E2 survives on one of three artifacts and only on a warm tree.

## Deviations from Plan

**1. [Rule 3 — blocking] `_run_check` compares three baselines, not four**

- **Found during:** Task 2
- **Issue:** The plan's `<interfaces>` and `<action>` refer to "the four `out_dir /
  "<name>.csv"` baseline paths (and `structural_scaling.csv`)". On disk `_run_check` makes
  exactly three comparisons: `code_constants.csv`, `newton_iterations.csv`,
  `cpr_grouping.csv`. `structural_scaling.csv` is written by `_write_tier4` but has never
  been part of `--check`.
- **Fix:** Threaded `baseline_dir` through the three comparisons that exist. Adding a
  fourth comparison would be a new `--check` behavior, out of scope for a plan whose
  success criterion is that the read path moves and nothing else does.
- **Files modified:** `experiments/e3_derived_quantities.py`
- **Commit:** `18f448a`

**2. [Rule 2 — missing functionality] `_validate_e3_args` runs before the shared `validate_args`**

- **Found during:** Task 2
- **Issue:** The plan's acceptance requires `--check --force --baseline-dir X` to name
  "both offending flags". The shared `validate_args` fires first on `--check`/`--force` and
  its message never mentions `--baseline-dir`, so the user's newly added flag would be
  silently subsumed by a pre-existing error.
- **Fix:** `main` calls `_validate_e3_args(parser, args)` before `validate_args(parser,
  args)`, and the docstring states why. Bare `--check --force` still produces the shared
  "mutually exclusive" message unchanged.
- **Files modified:** `experiments/e3_derived_quantities.py`
- **Commit:** `18f448a`

**3. [Rule 1 — judgement] E3 keeps its `if not <path>.exists()` branches**

The plan permitted swapping them for `compare_experiment_csv_if_present` only if it
simplified the branch. It does not: E3 must treat an absent baseline as a **failure**
(`overall_passed = False`), because all three of its baselines are committed by design, so
a missing one means the archive was resolved wrongly — the opposite of E2's policy-absent
pair. The existing printed message text is preserved so log-scraping does not break. The
N/A guard remains available and unused here; plan 26-06 is its consumer.

## Contracts Preserved

| Contract | Evidence |
|---|---|
| `build_experiment_arg_parser` exposes exactly five flags | `test_shared_parser_still_exposes_exactly_five_flags`; `python -c "...assert not hasattr(a,'baseline_dir')"` exits 0 |
| `compare_experiment_csv` still raises on a missing file | `test_compare_experiment_csv_itself_still_raises_on_a_missing_baseline` (`pytest.raises(FileNotFoundError)`) |
| `compare_experiment_csv`'s signature untouched | `git diff experiments/_io.py \| grep '^-' \| grep -c 'def compare_experiment_csv'` → `0` |
| No experiment or calibration was run | Only `--help` and an argparse-rejected invocation were executed |

## Verification

All run with `PYTHONPATH="$(pwd)/src"` and the AquaCal conda interpreter.

- `pytest tests/unit/test_experiments_io.py -k baseline -q` → **18 passed** (plan asked for
  ≥5), 36 deselected.
- `pytest tests/unit/test_experiments_io.py tests/unit/test_experiments_e3.py
  tests/unit/test_experiments_e3_constants.py -q` → **128 passed** in 40.4 s.
- `python -m experiments.e3_derived_quantities --help` lists `--baseline-dir` and all five
  shared flags.
- `python -m experiments.e3_derived_quantities --check --force --baseline-dir /tmp/x` →
  exit 2, message naming `--baseline-dir` and `--force`.
- `grep -c 'capture state before' experiments/e3_derived_quantities.py` → 0;
  `grep -c 'real reproduction signal'` → 1.

The full suite was **not** run — per CLAUDE.md that is the orchestrator's post-merge gate.

## Handoff Notes

- **Plan 26-06 (E2)** should call `add_baseline_dir_argument` in `e2_real_rig`'s parser and
  replace the two policy-gitignored comparisons with `compare_experiment_csv_if_present`,
  deciding explicitly that a `None` report is N/A rather than a failure. `camera_parameters.csv`
  should keep raising/failing, since it IS committed.
- **Plan 26-07 (driver)** passes `--baseline-dir experiments/pre_rerun_baseline/results` to
  E3's `--check` stage. `check_e2_band`'s sibling resolution was left alone (26-01 proved it
  already works); nothing here uses absolute paths.
- Mirror the `_validate_e3_args`-before-`validate_args` ordering in E2 if it adds an
  equivalent validator.

## Commits

| Commit | Type | Description |
|---|---|---|
| `7bd9905` | test | Failing `TestBaselineDir` for the three helpers (RED) |
| `375f895` | feat | The three helpers + DRIVER-03 `exclude_columns` documentation (GREEN) |
| `7f0fe8a` | test | Failing E3 `--baseline-dir` plumbing tests (RED) |
| `18f448a` | feat | E3 flag, validator, `_run_check` threading, D-10 rationale (GREEN) |

## Self-Check: PASSED

- `experiments/_io.py` — FOUND (modified, helpers importable)
- `experiments/e3_derived_quantities.py` — FOUND (modified, `--baseline-dir` in `--help`)
- `tests/unit/test_experiments_io.py` — FOUND (18 `-k baseline` tests pass)
- Commits `7bd9905`, `375f895`, `7f0fe8a`, `18f448a` — all FOUND in `git log e817a03..HEAD`
