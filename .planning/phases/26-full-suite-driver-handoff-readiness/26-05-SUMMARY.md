---
phase: 26-full-suite-driver-handoff-readiness
plan: 05
subsystem: experiments
tags: [e6, cli, d-40, band, provenance]
requires: []
provides:
  - "experiments.e6_generalization_sweep.ALL_AXES"
  - "experiments.e6_generalization_sweep.resolve_axes"
  - "build_axis_configurations(axes=...)"
  - "e6 --axes CLI flag"
  - "e6_seed_band_provenance.json `axes` field"
affects:
  - "plan 26-07 (the driver stage that will pass --axes index,layout,cameras)"
tech-stack:
  added: []
  patterns:
    - "argparse `type=` callable validates the selection at parse time, not mid-sweep"
    - "a 'full set == no restriction' normalisation keeps a new CLI default inert"
key-files:
  created: []
  modified:
    - experiments/e6_generalization_sweep.py
    - tests/unit/test_experiments_e6.py
decisions:
  - "axes and include_cameras_axis UNION rather than fight: neither flag can veto the other's request"
  - "passing the full axis set is identical to passing None, which is what makes the --axes CLI default byte-inert"
  - "--check keeps the unrestricted call: it compares against the committed 14-row generalization_sweep.csv"
metrics:
  duration: ~35 min
  completed: 2026-08-18
---

# Phase 26 Plan 05: E6 `--axes` Selector Summary

An opt-in `--axes` selector on E6 that lets the frozen re-run drop the `scale` axis
(14 x 6 = 84 band rows instead of 17 x 6 = 102) while leaving every existing invocation
byte-unchanged.

## What Was Built

**`ALL_AXES` and `resolve_axes()`** (`experiments/e6_generalization_sweep.py:359-418`).
`resolve_axes(axes=None, include_cameras_axis=False)` returns the axis names that will
actually be emitted, in `ALL_AXES` order, and is the single validation site: `ValueError`
naming the offending value and listing the valid set on an unknown axis, `ValueError` on
an empty selection. A silently-ignored typo would produce a band that is quietly the wrong
shape while still exiting 0 — the same class of trap E6's all-failed-rows behaviour already
has (T-26-16).

**Composition rule (documented in `resolve_axes`'s docstring, asserted in two tests).**
`axes` and `include_cameras_axis` are both *requests*; neither vetoes the other:

- `index`/`layout`/`scale` are emitted when `axes` is `None` or names them.
- `cameras` is emitted when `include_cameras_axis` is true, **or** when `axes` is a genuine
  restriction (a proper subset of `ALL_AXES`) that names `cameras`.

Passing the full set is deliberately identical to passing `None` — it is no restriction at
all, so `cameras` stays gated on `include_cameras_axis` alone. This is what makes the new
CLI default (`index,layout,scale,cameras`) inert: `_run_full` still gets 14 configurations
and `_run_seed_band` still gets 17.

The plan's `<action>` block *recommended* an AND rule (`cameras` emitted only when in `axes`
AND `include_cameras_axis`), but the plan's own `<behavior>` block requires
`build_axis_configurations(axes=("index","layout","scale"), include_cameras_axis=True)` to
return **17**, which AND cannot produce (it gives 14). The union rule satisfies all four
counts the behavior block specifies, and the plan explicitly permits either rule provided it
is stated and asserted. It is stated in the docstring and asserted by
`test_include_cameras_axis_wins_when_axes_omits_cameras` and
`test_axes_can_request_cameras_without_the_include_flag`.

**`build_axis_configurations(include_cameras_axis=False, axes=None)`.** Each of the four
append loops is now gated on membership in the resolved set. Selection *filters* — it never
reorders or reshapes — asserted element-for-element against the unrestricted call.

**CLI.** `--axes` parses a comma-separated string to a tuple via `_parse_axes_argument`,
which calls `resolve_axes` so a typo fails at argparse time. Its help text records what D-40
decided and why (zero `numbers-ledger.tsv` rows on the `scale` axis, ~1.9 h of a ~22–26 h
serial budget, and the frozen invocation). Threaded into `_run_full` and `_run_seed_band`;
`--check` deliberately keeps the unrestricted call, since it reconstitutes rows for
comparison against the committed 14-row `generalization_sweep.csv`.

**Provenance (T-26-15).** `e6_seed_band_provenance.json` gains an `axes` field carrying the
resolved list, and its `scope` string is now built by `_band_scope_string(resolved_axes)`
rather than hardcoding "index/layout/scale/cameras" — a scope string claiming coverage the
run did not have is precisely the defect class FIX-06 cleaned up.

## Verification

TDD gates: RED `59d6249` (13 of 14 new tests failing), GREEN `02a4c82`. No REFACTOR commit
was needed.

- `pytest tests/unit/test_experiments_e6.py -q` — **70 passed** (14 new).
- `pytest tests/unit/test_e6_band_mode.py -q -m "not slow"` — 8 passed;
  `-m "slow"` — 6 passed in 108 s. The slow class runs a real `--smoke --seeds 42,43` band,
  so the changed provenance sidecar path is exercised end to end.
- `pytest tests/unit/test_experiments_provenance.py tests/unit/test_experiment_inertness.py
  tests/unit/test_fail_fast.py -q -m "not slow"` — 332 passed, 25 skipped. No E6-adjacent
  regression.
- `build_axis_configurations(include_cameras_axis=True)` → 17;
  `(axes=("index","layout","cameras"), include_cameras_axis=True)` → 14 with no `scale`.
- `axes=("bogus",)` exits 1 with
  `ValueError: unknown axis name(s): bogus. Valid axes: index, layout, scale, cameras.`
- `python -m experiments.e6_generalization_sweep --help` lists `--axes`, `--seeds`,
  `--no-fail-fast`.
- `len(INDEX_AXIS_VALUES) == 8` and `len(SCALE_AXIS_VALUES) == 3` — the `index` 8→5 cut was
  not taken and the `scale` axis was not deleted.

The full suite was **not** run (orchestrator's post-merge job), and E6's production band was
**not** run.

## Deviations from Plan

**1. [Rule 3 — blocking] The composition rule follows the behavior block, not the action
block's recommendation.** As described above, the recommended AND rule contradicts the
required count of 17. Adopted the union rule, documented it in the docstring, and asserted
it in both directions. No user decision needed — the plan explicitly allowed either rule so
long as it was stated and tested.

**2. Acceptance criterion `git diff | grep '^-' | grep -c 'SCALE_AXIS_VALUES'` returns 1,
not 0.** The single removed line is the loop header
`for label, ... in SCALE_AXIS_VALUES:`, replaced by
`for label, ... in (SCALE_AXIS_VALUES if "scale" in resolved_axes else []):`. The criterion's
intent — the axis is deselectable, not deleted — holds: the constant is defined and iterated
exactly as before, and `test_scale_axis_values_still_defined` plus the acceptance one-liner
`len(SCALE_AXIS_VALUES) == 3` both pass.

## Notes for Downstream

- The frozen invocation is `--seeds <list> --axes index,layout,cameras` → 14 configs × 6
  seeds = **84** band rows. Plan 26-07 owns passing it; the driver was not touched here.
- `experiments/check_rerun_gates.py` and `experiments/suite_expectations.json` were **not**
  edited (plan 26-03 owns them). Neither `_E6_EXPECTED_SEED_COUNT` nor
  `_E6_EXPECTED_CAMERA_VALUES` encodes a configuration or row count, so no gate constant
  needed changing here — but any *new* gate that asserts an E6 band row count must be
  written against 84, not 102, for the frozen run.
- Because `cameras` is unioned in by band mode itself, `--axes` cannot drop the cameras axis
  from a `--seeds` run. That is intentional (D-40 drops only `scale`); a future plan wanting
  a cameras-free band must change `_run_seed_band`'s own `include_cameras_axis=True`.

## Self-Check: PASSED

- `experiments/e6_generalization_sweep.py` — FOUND (modified)
- `tests/unit/test_experiments_e6.py` — FOUND (modified)
- `.planning/phases/26-full-suite-driver-handoff-readiness/26-05-SUMMARY.md` — FOUND
- Commit `59d6249` — FOUND
- Commit `02a4c82` — FOUND
