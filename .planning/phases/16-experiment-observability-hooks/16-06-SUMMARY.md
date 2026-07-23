---
phase: 16-experiment-observability-hooks
plan: 06
subsystem: calibration-pipeline
tags: [seed, reproducibility, config, io, holdout-split]

# Dependency graph
requires: ["16-03"]
provides:
  - "config.seed threaded into the pipeline's own holdout split (split_detections call site)"
  - "CalibrationMetadata.seed persisted with backward-compatible deserialization"
affects: []

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "New CalibrationMetadata fields use .get() on deserialize so old calibration JSON keeps loading"

key-files:
  created: []
  modified:
    - src/aquacal/calibration/pipeline.py
    - src/aquacal/config/schema.py
    - src/aquacal/io/serialization.py
    - tests/unit/test_pipeline.py
    - tests/unit/test_schema.py
    - tests/unit/test_serialization.py

key-decisions:
  - "Only the two real HOOK-06 gaps were touched: split_detections call site and metadata seed recording; every other randomized entry point (generators, split_holdout, refine_calibration) was already threaded per the RESEARCH.md audit and left untouched"
  - "The throwaway CalibrationMetadata used for the temporary primary-camera validation result (pipeline.py ~1328) was deliberately left with no seed - it is a placeholder never written to disk, not a record"
  - "_compute_config_hash hashes an explicit field-string, not the whole dataclass, so seed had to be added to that string manually - confirmed by reading the function rather than assuming automatic coverage"

requirements-completed: [HOOK-06]

# Metrics
duration: 35min
completed: 2026-07-23
---

# Phase 16 Plan 06: Seed Threading & Recording (HOOK-06 Gap Closure) Summary

**Closed the two real HOOK-06 gaps: the pipeline's own holdout split now honors `config.seed` instead of silently hardcoding 42, and every calibration artifact the run produces (`calibration_initial.json`, `calibration.json`, and all three stage dumps) now records the seed that produced it, with `config_hash` distinguishing seed-only differences.**

## Performance

- **Duration:** ~35 min
- **Completed:** 2026-07-23
- **Tasks:** 2/2 completed
- **Files modified:** 6

## HOOK-06 Audit Outcome

Per RESEARCH.md's Q4 entry-point enumeration, this plan acted on exactly the two gaps the audit found — everything else was already satisfied and required no code:

**Already satisfied (no changes needed):**
- `generate_camera_array`, `generate_board_trajectory`, `generate_real_rig_trajectory`, `generate_dense_xy_grid`, `generate_synthetic_detections`, `create_scenario` — all already accept `seed: int = 42` and use `np.random.default_rng(seed)`
- `split_holdout` (`validation.py:33`) — already threaded
- `refine_calibration` — already has `holdout_seed: int = 42` on its public signature
- Plan 16-02 additionally already records the generating seed on `SyntheticScenario`

**Required code (this plan):**
- Gap 1: `split_detections`'s call site in `run_calibration_from_config` never passed a seed, always defaulting to 42 with no config control
- Gap 2: no output artifact recorded which seed was actually used, so a surprising result could not be reproduced from the artifact alone

## Accomplishments

- `run_calibration_from_config`'s `split_detections` call now passes `seed=config.seed` explicitly; the adjacent run-log print shows the seed alongside the holdout fraction
- `CalibrationMetadata` gained `seed: int | None = None` as its last field, defaulting to `None` so every existing throwaway-metadata construction site in `pipeline.py` stays valid without modification
- `_serialize_metadata`/`_deserialize_metadata` write/read the seed, using `.get("seed")` on load (not `data["seed"]`) so calibration JSON files written before this change keep loading, with `metadata.seed` defaulting to `None`
- `pipeline.py` sets `seed=config.seed` on the three real calibration records it writes: `calibration_initial.json`'s metadata, the final `calibration.json`'s metadata, and every `_dump_stage_calibration` call (stage3/stage3_rerun/stage4 dumps) — the throwaway validation-only `CalibrationMetadata` (empty-string placeholder, never written to disk) was deliberately left alone
- `_compute_config_hash` explicitly hashes a field-string (not the whole dataclass), so `seed` was added to that string; two configs differing only by seed now hash differently

## Zero-Behavior-Change Guarantee

`split_detections`'s own default stays `seed: int = 42`, and `CalibrationConfig.seed` defaults to 42 (set in plan 16-03), so **every existing config reproduces its current holdout split byte for byte.** This is verified by `test_split_detections_default_seed_is_42`, which asserts `split_detections(dets, 0.2)` (no seed arg) and `split_detections(dets, 0.2, seed=42)` produce identical calibration/validation frame-index sets.

## Task Commits

Each task was committed atomically:

1. **Task 1: Thread the configured seed into the pipeline's holdout split** - `e92a01d` (feat)
2. **Task 2: Record the seed in the saved calibration** - `f4f0249` (feat)

## Files Created/Modified
- `src/aquacal/calibration/pipeline.py` - `split_detections` call site passes `seed=config.seed`; run-log print includes seed; `CalibrationMetadata(...)` construction sites for `calibration_initial.json`, final `calibration.json`, and `_dump_stage_calibration` all pass `seed=config.seed`; `_compute_config_hash`'s hash-input string includes `config.seed`
- `src/aquacal/config/schema.py` - `CalibrationMetadata.seed: int | None = None` with docstring entry
- `src/aquacal/io/serialization.py` - `_serialize_metadata` writes `"seed"`; `_deserialize_metadata` reads via `.get("seed")`
- `tests/unit/test_pipeline.py` - `test_split_detections_default_seed_is_42`, `test_pipeline_passes_config_seed_to_split` (source-inspection wiring guard), `test_config_hash_changes_with_seed`
- `tests/unit/test_schema.py` - `test_calibration_metadata_seed_defaults_none`
- `tests/unit/test_serialization.py` - `test_metadata_seed_roundtrips`, `test_load_calibration_without_seed_key` (deletes the `"seed"` key from a saved JSON file and confirms `load_calibration` still succeeds with `seed=None`)

## Decisions Made
- Left the throwaway `CalibrationMetadata(calibration_date="", software_version="", ...)` used for the temporary primary-camera validation result unmodified — it is a placeholder that is never written to disk, not a run record
- `_compute_config_hash` required a manual edit (not automatic) because it builds an explicit hash-input string rather than hashing the dataclass as a whole; verified by reading the function before assuming coverage, per the plan's instruction

## Deviations from Plan

None — plan executed exactly as written. `TestSplitDetections` in `test_pipeline.py` already contained `test_split_detections_reproducible` and `test_split_detections_different_seed` from earlier plans, functionally equivalent to the plan's suggested `test_split_detections_same_seed_identical`/`test_split_detections_different_seed_differs`; only the two net-new tests (`default_seed_is_42`, the wiring guard) were added to avoid duplicating existing coverage.

## Issues Encountered
None.

## User Setup Required
None.

## Next Phase Readiness
- HOOK-06 fully closed: all six randomized entry points enumerated in RESEARCH.md Q4 are now either already-threaded (five of them) or newly threaded and recorded (the pipeline split, this plan).
- Full unit suite: 718 passed (was 717 at wave-3 baseline, +1 net after both tasks' additions/removals). `tests/ -m "not slow"`: 723 passed, 29 deselected. No regressions.
- `ruff check`/`ruff format --check` clean on `src/aquacal`.
- `grep -n 'data\["seed"\]' src/aquacal/io/serialization.py` returns nothing, confirming the deserializer uses `.get`.
- Remaining phase 16 work: plan 16-07.

---
*Phase: 16-experiment-observability-hooks*
*Completed: 2026-07-23*

## Self-Check: PASSED

All modified files and both task commit hashes (`e92a01d`, `f4f0249`) verified present.
