---
phase: 27-frozen-single-sha-handoff-package
plan: 04
subsystem: experiments
tags: [D-23, hardcode-removal, provenance, smoke]
requires: []
provides:
  - "resolve_real_rig_metrics_path(out_dir) -> (Path|None, note)"
  - "reconstruction_bootstrap.json field: real_rig_metrics_resolution"
  - "point_estimate_matches_real_rig_metrics may be null (not comparable)"
affects:
  - "experiments/run_experiment_suite.sh --smoke exit code (stage 10 no longer exits 1)"
tech-stack:
  added: []
  patterns:
    - "companion-artifact resolution: native / __file__-anchored default-tree / (None, reason)"
key-files:
  created: []
  modified:
    - experiments/reconstruction_bootstrap.py
    - tests/unit/test_reconstruction_bootstrap.py
decisions:
  - "Branch 2 (the __file__-anchored fallback) fires only when --out resolves to that constant's own parent, so a smoke or scratch run can never import the default tree's numbers."
  - "Absence is recorded as null plus a reason string, never False; --check prints 'not comparable' and does not add it to the mismatch list."
  - "LOCAL_RECONSTRUCTION_ERRORS_PATH left untouched, per the plan's explicit out-of-scope note."
metrics:
  duration: "~25 min"
  completed: 2026-08-19
requirements: [RUN-01]
---

# Phase 27 Plan 04: Resolve `real_rig_metrics.json` from `--out` Summary

`reconstruction_bootstrap.py` now resolves its `real_rig_metrics.json` companion relative to
`--out` with a `__file__`-anchored default-tree fallback, so the stage exits 0 under `--smoke`
instead of dying with `FileNotFoundError`, and an absent companion degrades to `null` with a
recorded reason rather than to a false negative.

## What Changed

**`REAL_RIG_METRICS_PATH` is no longer cwd-relative.** It was
`Path("experiments/results/real_rig_metrics.json")`; it is now anchored to `__file__` the way
`e4_benchmark_grid.py`'s `E2_BENCHMARK_PATH` and `e5_index_sensitivity.py`'s
`_default_metrics_path` are. It also changed meaning: it names the **default tree's** copy only,
and is consulted exclusively through the new resolver.

**New `resolve_real_rig_metrics_path(out_dir) -> tuple[Path | None, str]`**, three branches
mirroring `e4_benchmark_grid.py:296-309`:

1. `out_dir / "real_rig_metrics.json"` if it exists — `"native: ..."`.
2. `REAL_RIG_METRICS_PATH`, but only when `out_dir.resolve() == REAL_RIG_METRICS_PATH.parent.resolve()`
   — `"default tree: ..."`.
3. Otherwise `(None, "absent: ... refusing to import <path>, which describes a different run")`.

Both sides of the branch-2 comparison are `.resolve()`d. The plan's analog resolves only the left
side; resolving both makes the comparison correct for a non-canonical spelling of the default tree
(a relative `--out`, a `..` component, a symlink) — the only path form under which branch 2 is
reachable at all, since a canonically-spelled default tree holding the file is caught by branch 1.

**`_run` gained an `out_dir` parameter** (`out_dir: Path | None = None`, defaulting to the default
tree so no existing caller changes behaviour), and `_load_real_rig_metrics` now takes a resolved
path rather than reading a module global.

**The record carries a new `real_rig_metrics_resolution` field** holding the reason string, so a
reader of the artifact can distinguish "not comparable" from "compared and disagreed".
`point_estimate_matches_real_rig_metrics` is now `bool | None`.

**The `--check` branch no longer conflates absence with disagreement.** `None` prints
`point_estimate_matches_real_rig_metrics: not comparable -- <reason>` and is not appended to
`mismatches`; only an explicit `False` is.

## Verification

- `grep -c 'Path("experiments/results/real_rig_metrics.json")' experiments/reconstruction_bootstrap.py` → **0**.
- `python -m pytest tests/unit/test_reconstruction_bootstrap.py -q` → **25 passed** (15 pre-existing,
  10 new). RED was confirmed first: 9 failed / 15 passed at commit `f4ea3ff`.
- CLI acceptance, against a scratch directory holding no `real_rig_metrics.json` and an explicit
  `--reconstruction-errors`: **EXIT=0**, with a WARNING naming the reason, and the emitted record
  carrying `"point_estimate_matches_real_rig_metrics": null` alongside the resolution string.
  Nothing was written into `experiments/results/`.

New tests assert, explicitly with `is None` rather than falsiness: the absent-companion case; the
present-and-agreeing case (`is True`); the present-and-disagreeing case (`is False`, so the
degradation path did not swallow real mismatches); the default-tree case resolving the same file
as before; and the `--check` "not comparable" path exiting 0.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Branch-2 comparison resolved only one side**
- **Found during:** Task 1, GREEN phase
- **Issue:** `out_dir.resolve() == REAL_RIG_METRICS_PATH.parent` — copied from the analog — compares
  a resolved path against an unresolved one, so branch 2 misses whenever the constant's own path
  contains a symlink or is not canonical (on this machine, `%TEMP%` under test).
- **Fix:** `.resolve()` both sides.
- **Files modified:** `experiments/reconstruction_bootstrap.py`
- **Commit:** `131f16a`

**2. [Rule 1 - Bug] Two new tests used the wrong companion-file keys**
- **Found during:** Task 1, GREEN phase
- **Issue:** the fixtures wrote `reconstruction_rmse_mm` / `reconstruction_mae_mm`, but
  `_REAL_RIG_METRICS_MAP` maps those *local* names to the companion's `inter_corner_rmse_mm` /
  `inter_corner_mae_mm`. `KeyError`, not an assertion failure.
- **Fix:** fixtures now write the `inter_corner_*` keys.
- **Files modified:** `tests/unit/test_reconstruction_bootstrap.py`
- **Commit:** `131f16a`

**3. [Rule 1 - Test defect] A test conflated branch 1 with branch 2**
- **Found during:** Task 1, GREEN phase
- **Issue:** `test_default_tree_uses_the_file_anchored_constant` placed the file in the default
  tree and then asserted the note said `"default tree"` — but branch 1 correctly matches first, and
  returns the identical path. The test asserted an unreachable branch.
- **Fix:** split into two honest tests — one asserting production behaviour (default tree with the
  file present resolves that same file, whichever branch serves it), one exercising branch 2 via a
  non-canonical spelling of the default tree with the file absent.
- **Files modified:** `tests/unit/test_reconstruction_bootstrap.py`
- **Commit:** `131f16a`

## Findings

**The sibling hardcode is still there, deliberately.**
`LOCAL_RECONSTRUCTION_ERRORS_PATH = Path("experiments/results/reconstruction_errors.csv")`
(`experiments/reconstruction_bootstrap.py:60`) remains cwd-relative and is NOT `--out`-aware. The
plan put it explicitly out of scope: it already degrades to the published Zenodo archive rather
than raising, and D-23 does not name it. Two properties are worth recording for whoever revisits it:

1. It is **cwd-relative**, so a run launched from anywhere but the repo root silently skips the
   local copy and reaches for the 4.35 GB archive. That is the same anchoring defect D-23 named,
   in a branch that fails slowly rather than loudly.
2. It is **not** `--out`-relative, and arguably should not be — `reconstruction_errors.csv` is an
   *input* produced by E2, not a companion of this stage's own output tree.

**`experiments/results/` does not exist in a fresh worktree.** The CLI acceptance run therefore
could not have used the default tree even if it wanted to; it was driven with an explicit
`--reconstruction-errors` against a scratch CSV to avoid triggering an archive download. Worth
knowing for 27-10's smoke acceptance pass: stage 10 needs either a local `reconstruction_errors.csv`
or the archive present in the dataset cache.

## Known Stubs

None.

## Threat Flags

None. The two threats in the plan's register are both mitigated as specified: T-27-04-01 by the
branch-2 guard (asserted by `test_absent_and_not_default_tree_returns_none_with_both_locations`),
T-27-04-02 by the `None`-plus-reason degradation and the `--check` "not comparable" path (asserted
by `test_absent_companion_gives_none_not_false` and
`test_check_treats_none_as_not_comparable_not_a_mismatch`).

## TDD Gate Compliance

RED (`f4ea3ff`, `test(27-04)`) → GREEN (`131f16a`, `fix(27-04)`). No REFACTOR commit was needed.
Note the GREEN commit is `fix`, not `feat` — this plan removes a defect rather than adding a
feature.

## Commits

| Hash | Message |
|------|---------|
| `f4ea3ff` | test(27-04): add failing tests for --out-relative real_rig_metrics resolution |
| `131f16a` | fix(27-04): resolve real_rig_metrics.json from --out, not a hardcode (D-23) |

## Self-Check: PASSED

- `experiments/reconstruction_bootstrap.py` — FOUND (modified)
- `tests/unit/test_reconstruction_bootstrap.py` — FOUND (modified)
- `f4ea3ff` — FOUND
- `131f16a` — FOUND
- No file deletions in either commit.
- `.planning/STATE.md` and `.planning/ROADMAP.md` untouched, per the parallel-executor contract.
