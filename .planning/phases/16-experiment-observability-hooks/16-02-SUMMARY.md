---
phase: 16-experiment-observability-hooks
plan: 02
subsystem: testing
tags: [synthetic-data, refractive-index, seed-reproducibility, pytest]

requires: []
provides:
  - "generate_synthetic_detections accepts n_air/n_water and forwards them to Interface"
  - "SyntheticScenario records n_air, n_water, seed as ground truth"
  - "create_scenario forwards n_air/n_water to every preset"
  - "Executable audit proving layout, tank scale, working distance, and refractive
    index are independently controllable, and all synthetic generators are
    seed-reproducible"
affects: [17-per-camera-interface-ablation, wp4-wp5-experiments]

tech-stack:
  added: []
  patterns:
    - "Keyword-only new parameters with defaults matching prior hardcoded values,
      placed before pre-existing keyword-only params, to guarantee zero-behavior-
      change for existing positional/keyword callers"

key-files:
  created:
    - tests/unit/test_synthetic_sweep_axes.py
  modified:
    - src/aquacal/datasets/synthetic.py
    - tests/unit/test_datasets.py

key-decisions:
  - "n_air/n_water default to 1.0/1.333 everywhere so every existing call site
    (including create_scenario's three presets) is untouched and bit-identical"
  - "create_scenario records n_air/n_water/seed as ground-truth metadata only;
    it does not generate detections itself, so the caller must pass the same
    values to generate_synthetic_detections to actually generate at that index"

patterns-established:
  - "Sweep-axis audit tests (test_synthetic_sweep_axes.py) as the executable form
    of a design audit — future refactors that couple sweep axes together will
    fail these tests instead of silently regressing"

requirements-completed: [HOOK-05, HOOK-06]

duration: 20min
completed: 2026-07-23
---

# Phase 16 Plan 02: Synthetic Data Sweep-Axis Support Summary

**Refractive index now flows from `generate_synthetic_detections` through to the `Interface` constructor, `SyntheticScenario` self-describes with `n_air`/`n_water`/`seed`, and an executable test file pins layout, tank-scale, working-distance, and index sweep independence plus seed reproducibility across every synthetic generator.**

## Performance

- **Duration:** ~20 min
- **Completed:** 2026-07-23T17:12:44Z
- **Tasks:** 2 completed
- **Files modified:** 3 (1 created, 2 modified)

## Accomplishments

- Closed the one real HOOK-05 gap: `generate_synthetic_detections` previously
  hardcoded `Interface`'s defaults (n_air=1.0, n_water=1.333) with no way to
  generate detections at a different refractive index. It now accepts and
  forwards `n_air`/`n_water`.
- `SyntheticScenario` and `create_scenario` now record `n_air`, `n_water`, and
  `seed` as ground truth (the synthetic-data half of HOOK-06).
- The remaining three WP5 sweep axes (layout, tank scale, working distance)
  were confirmed already implemented correctly by code inspection in
  16-RESEARCH.md §Q3 — this plan converts that audit into 6 executable tests
  in `tests/unit/test_synthetic_sweep_axes.py` (333 lines) so future refactors
  cannot silently couple those axes.

## Task Commits

1. **Task 1: Plumb refractive index through detection generation and record it
   on the scenario** - `85e60c2` (feat)
2. **Task 2: Write the executable WP5 sweep-axis audit** - `25cf08a` (test)

**Plan metadata:** (this commit, docs)

## Files Created/Modified

- `src/aquacal/datasets/synthetic.py` - added `n_air`/`n_water` params to
  `generate_synthetic_detections` (forwarded into `Interface(...)`), added
  `n_air`/`n_water`/`seed` fields to `SyntheticScenario`, added `n_air`/`n_water`
  params to `create_scenario` forwarded into all three preset literals
- `tests/unit/test_datasets.py` - 4 new tests: default-index-unchanged
  regression guard, index-changes-projection proof, scenario records
  index/seed, scenario defaults are backward compatible
- `tests/unit/test_synthetic_sweep_axes.py` (new) - 6 tests: layout produces
  distinct geometries (incl. a genuine-ring check), tank scale is independent
  of working distance, working distance is independent of rig geometry,
  refractive index moves only optics, every preset carries full ground truth,
  and all four generator functions are seed-reproducible

## Decisions Made

- HOOK-05 (refractive index): treated as the only real code gap per
  16-RESEARCH.md audit — layout, tank scale, and working distance required no
  production code changes, only tests. This is called out explicitly in this
  summary per the plan's `<output>` instruction.
- Zero-behavior-change requirement enforced via explicit regression test
  (`test_generate_detections_default_index_unchanged`) comparing omitted-args
  vs explicit-defaults output corner-for-corner.

## Deviations from Plan

None - plan executed exactly as written. All four `must_haves.truths` and
both `must_haves.artifacts` are satisfied; all `key_links` patterns
(`n_air=n_air`, `seed=seed`) appear in the diff as specified.

## Issues Encountered

One transient failure was observed in a single full-suite run
(`tests/unit/test_conditioning.py::test_public_exports` — `ImportError`), caused
by a parallel plan (16-01, owning `src/aquacal/validation/`) mid-edit to a file
outside this plan's ownership scope. Re-running the full suite immediately
after showed 680 passed / 0 failed. Not investigated further — out of scope
per the plan's file-ownership boundary (`src/aquacal/validation/` belongs to
plan 16-01, running in parallel).

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- HOOK-05 and HOOK-06 (synthetic-data half) are both fully satisfied and
  pinned by executable tests.
- `tests/unit/test_synthetic_sweep_axes.py` is available as a template/example
  for WP5 sweep scripts written outside the library (calling the generator
  functions directly, as the audit notes were designed to support).
- No blockers for downstream plans in this phase or Phase 17.

---
*Phase: 16-experiment-observability-hooks*
*Completed: 2026-07-23*

## Self-Check: PASSED

- FOUND: src/aquacal/datasets/synthetic.py
- FOUND: tests/unit/test_synthetic_sweep_axes.py
- FOUND: commit 85e60c2
- FOUND: commit 25cf08a
