---
phase: 21-new-feature-documentation-dataset-refresh
plan: 02
subsystem: docs
tags: [documentation, benchmark.json, observability, sphinx]
dependency-graph:
  requires: []
  provides:
    - "docs/guide/benchmarking.md (benchmark.json / trace CSV / conditioning schema reference)"
  affects:
    - "docs/guide/configuration.md (internals section forward links)"
    - "docs/guide/refractive_geometry.md (ablation admonition pointer)"
    - "docs/guide/index.md (nav + toctree)"
tech-stack:
  added: []
  patterns:
    - "MyST admonition three-way class convention (warning/tip/note)"
    - "Reference-table + fenced-example pairing, excerpts trimmed verbatim from real artifacts"
key-files:
  created:
    - docs/guide/benchmarking.md
  modified:
    - docs/guide/configuration.md
    - docs/guide/refractive_geometry.md
    - docs/guide/index.md
decisions:
  - "D-04 verified, no rewrite: shared_interface default is still True, the config key path is still interface.shared_interface, and the 'not a recommended production setting' framing still matches src/aquacal/config/schema.py:366's docstring/comment."
  - "Trace CSV excerpt fence retagged from csv to text -- Pygments has no registered 'csv' lexer alias in this environment, and sphinx-build -W treats the resulting highlighting-failure warning as a build error. The page still carries six json-tagged excerpts, satisfying the >=3 json/csv fenced-block acceptance criterion without weakening the -W gate."
metrics:
  duration: "~45 min"
  completed: "2026-08-10"
---

# Phase 21 Plan 02: Benchmarking & Diagnostics Documentation Summary

New `docs/guide/benchmarking.md` documents `benchmark.json`, the optimization trace CSV, and
the conditioning JSON/NPZ payloads field-by-field, replacing zero documentation with a
150+ line reference page; `configuration.md`'s two internals rows and See Also list now link
forward to it.

## What Was Built

**Task 1 — `docs/guide/benchmarking.md` (300 lines).** New guide page documenting:
- `benchmark.json` top-level keys (`schema_version`, `environment`, `solver_config`,
  `problem_shape`, `stages`, `memory`, `accuracy`) field-by-field, each paired with a real
  trimmed JSON excerpt from `experiments/results/benchmark.json`.
- The `null`-with-`*_reason` convention (admonition) and an `optimality`-is-not-an-accuracy-figure
  warning admonition.
- All eight optimization trace CSV columns (`iteration`, `n_fev`, `cost`, `step_norm`,
  `optimality`, `water_z`, `tilt_rx`, `tilt_ry`) with interpretation, paired with a real
  3-line excerpt from `experiments/results/e7_trace_shared_fixed.csv`.
- Both conditioning payloads (`conditioning.json` scalars, `conditioning.npz` arrays), the
  correlation-matrix indexing rule (`parameter_names[i]` per row/column), a 5-line Python
  snippet loading the NPZ, and an MF-12 hypothesis admonition (labelled as unrun, per plan
  instruction — cited by name, not asserted as tested).
- A See Also footer linking `configuration.md`, `optimizer.md`, `cli.md`, `troubleshooting.md`.

**Task 2 — Forward links + D-04 verification.**
- `configuration.md`'s `save_optimization_trace` and `save_conditioning` internals rows each
  gained an appended forward-link clause to `benchmarking.md`; neither row nor its existing
  content was deleted.
- `configuration.md`'s See Also list gained a `benchmarking.md` bullet.
- **D-04 verification (not rewrite), three checks against `src/aquacal/config/schema.py`:**
  1. Default of `shared_interface` — confirmed `True` (`schema.py:366`,
     `shared_interface: bool = True`).
  2. Config key path — confirmed `interface.shared_interface` (matches
     `configuration.md:97`'s existing table row and admonition; no code path found using a
     different key).
  3. "Not a recommended production setting" framing — confirmed current: the field's inline
     comment reads "Analysis/ablation only... not recommended for production; the
     shared-interface assumption underlies the paper's central claim," matching
     `configuration.md:109-118`'s admonition verbatim in substance.
  All three held, so **no edit was made to the `shared_interface` row or admonition in
  `configuration.md`, nor to the ablation admonition body in `refractive_geometry.md`.**
- The one permitted content change to `refractive_geometry.md` (per plan instruction): the
  ablation admonition's last sentence, "A full worked example is deferred to a later
  documentation pass," was replaced with a pointer to `benchmarking.md`'s conditioning
  section. `git diff --stat docs/guide/refractive_geometry.md` shows exactly 2 changed lines.

**Task 3 — Guide nav registration + docs build.**
- `docs/guide/index.md` gained a `Benchmarking & Diagnostics` bullet (after Configuration
  Reference) and the bare toctree stem `benchmarking` (after `configuration`).
- Ran `sphinx-build -W --keep-going -b html docs docs/_build/html` from the repo root in the
  AquaCal conda env (`PYTHONPATH=$(pwd)/src`), exactly as CI does
  (`.github/workflows/docs.yml:30`). `docs/_build/html/guide/benchmarking.html` was produced.
  `docs/_build/` was not staged (already gitignored at `.gitignore:72`).

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking issue] Pygments has no `csv` lexer alias in this environment**
- **Found during:** Task 3's `sphinx-build -W` run.
- **Issue:** The trace CSV excerpt was fenced as ` ```csv `, which triggered
  `WARNING: Pygments lexer name 'csv' is not known [misc.highlighting_failure]`, escalated to
  a build failure by `-W`.
- **Fix:** Retagged the fence as ` ```text `. The page already carries six ` ```json ` excerpts
  (from Task 1), so the acceptance criterion "at least three fenced blocks tagged ```json``` or
  ```csv```" still holds without weakening the `-W` gate or introducing a `suppress_warnings`
  entry that would mask future genuine highlighting failures repo-wide.
- **Files modified:** `docs/guide/benchmarking.md`.
- **Commit:** `0040484`.

## Known Pre-existing Build Issue (not fixed — out of scope)

`sphinx-build -W --keep-going -b html docs docs/_build/html` still reports one error not
introduced by this plan and not owned by any file this plan modifies:

```
src/aquacal/datasets/synthetic.py:docstring of aquacal.datasets.synthetic.generate_board_trajectory:7: ERROR: Unexpected indentation. [docutils]
```

This is a Napoleon/docstring formatting defect in `generate_board_trajectory`'s docstring
(unrelated `src/aquacal/datasets/` code, not a `docs/guide/*.md` file). Per the plan's Task 3
instruction — "If the build surfaces a pre-existing error in a file this plan does not own,
record it in the SUMMARY and do not fix it here" — this is recorded and left unfixed. As a
result, `sphinx-build -W --keep-going -b html docs docs/_build/html` currently exits **1**
(one warning-as-error), not 0, but the failure is entirely attributable to this pre-existing,
out-of-scope defect: after this plan's edits, no warning originates from any file this plan
touches.

## Self-Check: PASSED

- `docs/guide/benchmarking.md` — FOUND, 300 lines (>= 150 required).
- `docs/guide/configuration.md` — FOUND, modified (3 `benchmarking.md` occurrences,
  `save_optimization_trace`/`save_conditioning` rows retained, `shared_interface` retained).
- `docs/guide/refractive_geometry.md` — FOUND, modified (1 `benchmarking.md` occurrence,
  "deferred to a later documentation pass" removed, diff is 2 changed lines).
- `docs/guide/index.md` — FOUND, modified (1 `benchmarking` toctree stem, 1 `benchmarking.md`
  bullet link).
- `docs/_build/html/guide/benchmarking.html` — FOUND (build artifact, not committed).
- Commit `b8a222d` (Task 1) — FOUND in `git log`.
- Commit `38bef02` (Task 2) — FOUND in `git log`.
- Commit `0040484` (fence-tag fix) — FOUND in `git log`.
- Commit `3a7e4a7` (Task 3) — FOUND in `git log`.
