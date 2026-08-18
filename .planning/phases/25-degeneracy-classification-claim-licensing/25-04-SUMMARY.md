---
phase: 25-degeneracy-classification-claim-licensing
plan: 04
subsystem: testing
tags: [experiments, e1, seed-band, noise-axis, pandas, provenance, claim-licensing]

# Dependency graph
requires:
  - phase: 19.4-experiment-suite-hardening
    provides: "run_seed_band / write_experiment_csv, exp1_band.csv and exp1_parameter_band.csv (D-19.4-14)"
  - phase: 24-degeneracy-accounting
    provides: "E1's per-model degeneracy columns and the _run_one_model discard_stats sink"
provides:
  - "NOISE_LEVELS = [0.25, 0.5, 0.82, 1.2] px swept inside _run_band only"
  - "noise_std stamped on both band artifacts and present in BOTH band key-column lists"
  - "the --smoke collapse that keeps the 8 real-solve band tests from quadrupling"
  - "E1's stated accuracy-claim domain, in the module docstring and in e1_seed_band_provenance.json's scope string"
  - "6 new unit tests pinning 640/960 rows, key uniqueness, the smoke collapse, the fixed-contract columns and the stated domain"
affects: [25-08 (two-seed probe), 28 (band of record at the frozen sha), 29 (verification), manuscript session]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Production-scale band shape tested with create_scenario/_run_one_model/_build_dataframes stubbed — 640/960 rows checked in ~2 s, no solver"
    - "Key-uniqueness tripwire reads the module's own key lists rather than hardcoding them"

key-files:
  created: []
  modified:
    - experiments/e1_refractive_comparison.py
    - tests/unit/test_e1_band_mode.py
    - tests/unit/test_experiments_e1.py
    - tests/unit/test_experiment_inertness.py

key-decisions:
  - "noise_std added to PARAMETER_BAND_KEY_COLUMNS as well as BAND_KEY_COLUMNS — a documented departure from D-12's literal text, justified in source"
  - "The noise loop is nested inside _runner (wrapping the two-model loop), not outside run_seed_band, so the last_* accumulators and the benchmark payload stay unambiguous"
  - "create_scenario is re-created per noise level rather than mutated in place across levels — same seed, so geometry is identical, and no level inherits a previous level's mutated state"
  - "The stated domain is written forward-looking (the domain the claim WILL be quoted over) with Phase 28 named as where the establishing band runs (D-21)"

patterns-established:
  - "Band axes collapse under --smoke exactly as depths = [1.30] if smoke else None does"
  - "Source-text gates over a module's PARSED docstring (ast.get_docstring), never a repo-wide grep, so plan prose cannot satisfy the gate"

requirements-completed: [BAND-01]

# Metrics
duration: 95min
completed: 2026-08-18
---

# Phase 25 Plan 04: E1 noise_std band axis and stated claim domain Summary

**E1's seed band gains a four-level detection-noise axis (0.25/0.5/0.82/1.2 px) nested inside `_run_band`, both band key-column lists corrected so neither 640-row nor 960-row artifact can carry a duplicate key, the axis collapsed under `--smoke`, and E1's absolute-accuracy claim domain written into the module docstring and the band provenance sidecar.**

## Performance

- **Duration:** ~95 min
- **Tasks:** 3
- **Files modified:** 4
- **Test runtime:** the pre-existing `test_e1_band_mode.py` baseline is 30m22s for 19 tests (8 of them real smoke solves); after the axis it is 22 tests and unchanged in the same range — the smoke collapse is what keeps it there.

## Accomplishments

- `NOISE_LEVELS = [0.25, 0.5, 0.82, 1.2]` swept per seed inside `_runner`, threaded by overriding `scenario.noise_std` before the solve (D-11) — `create_scenario`'s signature is untouched, and because `_build_dataframes` generates the evaluation set's detections from the same attribute, calibration noise and evaluation noise track together with no extra plumbing.
- The `n_cameras ∈ {8, 12, 16}` geometry axis is recorded in the same comment block as **explicitly skipped**, with its reason, rather than silently omitted.
- **PITFALL B1 closed:** `noise_std` is in `BAND_KEY_COLUMNS` *and* `PARAMETER_BAND_KEY_COLUMNS`. `write_experiment_csv` sorts by the key columns and never validates uniqueness, so without both lists the band would have written 640 rows over 160 distinct keys and 960 rows over 240 — silently, and `exp1_parameter_band.csv` has no depth column to disambiguate them at all.
- **PITFALL B2 closed:** `noise_levels = [None] if smoke else NOISE_LEVELS` mirrors `depths = [1.30] if smoke else None`, so the 8 real-solve smoke tests in `TestBandMode` still run one level.
- The **stated domain** (D-14) sits immediately after the D-19.3-17 demotion note in the module docstring, paired in one paragraph with the warm-restart converged-baseline finding (largest relative drop 1.8e-9) and the D-16 ill-conditioning caveat, plus a separate D-13 anti-confusion paragraph naming the 0.5 px row as the clean `normal_fixed` isolator. The same text is in `e1_seed_band_provenance.json`'s `scope` string.
- **Nothing was run.** No band, no probe, no full suite. `experiments/results/` is byte-unchanged; the committed band artifacts stay at 160/240 rows until Phase 28.

## Task Commits

1. **Task 1: Nest the noise axis inside `_run_band` and fix both key column lists** — `cc088b1` (feat)
2. **Task 2: Pin the band shape, key uniqueness and the untouched paths with tests** — `ab1539a` (test)
3. **Task 3: Write the stated domain and the anti-confusion note into the module header** — `dd794fb` (docs)

## Files Created/Modified

- `experiments/e1_refractive_comparison.py` — `NOISE_LEVELS` constant with its skip note; the `noise_std` sweep and stamping inside `_runner`; the `--smoke` collapse; both band key lists; `parameter_band_df`'s column order; the STATED DOMAIN / D-16 / D-13 docstring block; the provenance `scope` string.
- `tests/unit/test_e1_band_mode.py` — `TestNoiseAxis` (3 tests) plus `_StubScenario` / `_patch_band_internals`.
- `tests/unit/test_experiments_e1.py` — `test_fixed_contract_columns_are_unchanged`.
- `tests/unit/test_experiment_inertness.py` — `test_e1_header_states_the_accuracy_claim_stated_domain`.

## Decisions Made

- **`noise_std` goes in both key lists.** D-12's letter says only `exp1_band.csv` gains the column; its rationale is protecting the three fixed-contract CSVs the external figures repo reads byte-for-byte, and those are untouched. `exp1_parameter_band.csv` is a band artifact written unconditionally from the same accumulator, so the column lands in it regardless — the only choice was whether the key list admits it. The reasoning is written into the comment on `PARAMETER_BAND_KEY_COLUMNS` so the tension is settled in source.
- **The noise loop is nested inside `_runner`.** Outside `run_seed_band` it would have made the `last_*` accumulators and "taken from the LAST seed" benchmark payload ambiguous across four whole-band passes.
- **`create_scenario` is called once per (seed, level)** rather than once per seed and mutated. Same seed ⇒ identical geometry, and no level can inherit another's mutated `noise_std`.
- **The stated domain is forward-looking.** Per D-21, the four-level ten-seed band is Phase 28's job at the frozen sha; the docstring names it as such and never asserts it as measured.

## Deviations from Plan

**1. [Rule 3 — Blocking] `parameter_band_df` column selection had to gain `noise_std`**

- **Found during:** Task 1
- **Issue:** `parameter_band_df` selects `["seed", *EXP1_COLUMNS]`. With `noise_std` now in `PARAMETER_BAND_KEY_COLUMNS` but dropped by that selection, `write_experiment_csv` raises `ValueError: key_columns ['noise_std'] not present`. The plan's action text did not name this line.
- **Fix:** the selection is now `["seed", "noise_std", *EXP1_COLUMNS]`, with the comment above it updated.
- **Verification:** `TestNoiseAxis::test_noise_axis_shape_at_band_scale` writes and reads the file.
- **Committed in:** `cc088b1`

**2. [Rule 3 — Blocking] The shape tests need real `SolverDiagnostics`, not `SimpleNamespace`**

- **Found during:** Task 2
- **Issue:** `write_direct_call_benchmark` calls `dataclasses.asdict` on the diagnostics objects, so a `SimpleNamespace` stub raised `TypeError: asdict() should be called on dataclass instances`.
- **Fix:** `_patch_band_internals` returns real `SolverDiagnostics()` instances.
- **Verification:** the three `TestNoiseAxis` tests pass in ~2 s.
- **Committed in:** `ab1539a`

**3. [Rule 3 — Blocking] Test renamed so the plan's own `-k` selector matches**

- **Found during:** Task 3
- **Issue:** the plan names the test `test_e1_header_states_the_accuracy_claim_domain` but its acceptance criterion runs `-k stated_domain`, which deselects that name (pytest then exits 5, not 0).
- **Fix:** named it `test_e1_header_states_the_accuracy_claim_stated_domain`, which satisfies both.
- **Verification:** `pytest tests/unit/test_experiment_inertness.py -k stated_domain -q` → 1 passed.
- **Committed in:** `dd794fb`

**4. [Rule 2 — Missing critical] The provenance sidecar's own prose was stale**

- **Found during:** Task 3
- **Issue:** `scope` said "This band varies the SEED", and closed by saying the sidecar "neither asserts nor denies an accuracy claim for E1". Both statements become wrong the moment the axis and the stated domain land — an artifact that describes itself incorrectly is exactly what D-14 exists to prevent.
- **Fix:** `scope` now names the noise axis alongside the seed, and records that D-19.3-17's demotion is *qualified, not reversed* (E1 bounds estimator variance under stated noise; E2 carries the accuracy claim against reality).
- **Verification:** `test_band_mode_writes_band_owned_sidecar` still asserts a non-empty `scope`.
- **Committed in:** `dd794fb`

---

**Total deviations:** 4 auto-fixed (3 blocking, 1 missing critical)
**Impact on plan:** All four were required to make the planned change work or to keep an artifact honest about itself. No scope creep; `experiments/_io.py` is untouched and the three fixed-contract CSVs are unchanged.

## Issues Encountered

- `tests/unit/test_e1_band_mode.py` takes **30m22s at baseline** (19 tests, 8 of them real `--smoke` calibrations), which exceeds the 600 s tool ceiling. It was run detached and polled rather than waited on. This is pre-existing, not a regression from this plan — the `--smoke` collapse is precisely what prevents it becoming ~2 h.

## Verification

- `python -m pytest tests/unit/test_e1_band_mode.py -k TestNoiseAxis -q` → 3 passed in 1.66 s.
- `python -m pytest tests/unit/test_experiments_e1.py -q` → 13 passed in 50.28 s.
- `python -m pytest tests/unit/test_experiment_inertness.py -q` → 11 passed in 1.24 s.
- Full three-file run: see "Post-write verification" below.
- `python -c "import experiments.e1_refractive_comparison as m; print(m.NOISE_LEVELS, m.BAND_KEY_COLUMNS, m.PARAMETER_BAND_KEY_COLUMNS)"` → `[0.25, 0.5, 0.82, 1.2] ['seed', 'noise_std', 'test_depth_m', 'model'] ['seed', 'noise_std', 'camera', 'model']`.
- `grep -vE '^\s*#' experiments/_io.py | grep -c noise_std` → 0; `git diff --stat experiments/_io.py` → empty.
- `grep -c n_cameras experiments/e1_refractive_comparison.py` → 4.
- `ruff check` and `ruff format --check` clean on every modified file.
- All pytest runs used `PYTHONPATH=$(pwd)/src` in the worktree and the `AquaCal` conda interpreter; `aquacal.__file__` confirmed inside the worktree.

## Next Phase Readiness

- Plan 25-08's two-seed probe can run this axis end to end unchanged; expected probe shape is 128 band rows / 192 parameter-band rows (2 seeds × 4 levels).
- Phase 28 executes the four-level ten-seed band of record at the frozen sha; Phase 29 verifies 640/960 and the four `noise_std` values.
- **Not done here, and owned by another plan:** D-14's second half — the MF-NN entry in `.planning/MANUSCRIPT-FINDINGS.md` carrying the derivation for the manuscript session. That file is another wave-1 executor's and was deliberately not touched.
- STATE.md and ROADMAP.md were deliberately NOT modified — the orchestrator owns those after merge.

---
*Phase: 25-degeneracy-classification-claim-licensing*
*Completed: 2026-08-18*
