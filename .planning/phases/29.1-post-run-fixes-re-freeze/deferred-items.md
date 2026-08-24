# Phase 29.1 — Deferred Items

Out-of-scope discoveries logged during execution. Per the executor's scope boundary,
these were NOT fixed: they are not caused by this phase's changes.

## D1. `tests/unit/test_experiments_provenance.py` — 8 pre-existing failures

**Found during:** plan 29.1-01, task 3 (regression run over every test file that imports
`check_rerun_gates` or `e4_benchmark_grid`).

**Status:** pre-existing. Verified byte-for-byte identical at the branch base `89c2092`
with `experiments/e4_benchmark_grid.py` and `experiments/check_rerun_gates.py` restored to
their pre-plan state — same 8 failures, same node ids.

    TestEnvironmentPresence::test_every_benchmark_record_has_environment[run_manifest.json]
    TestSeedProvenance::test_every_benchmark_record_carries_a_seed[run_manifest.json]
    TestCsvProvenanceMap::test_all_committed_csvs_have_a_named_record[generalization_sweep_per_camera.csv]
    TestCsvProvenanceMap::test_all_committed_csvs_have_a_named_record[generalization_sweep_per_camera_band.csv]
    TestCsvProvenanceMap::test_multi_seed_band_declares_its_seed_coverage[exp1_band.csv]
    TestCsvProvenanceMap::test_multi_seed_band_declares_its_seed_coverage[exp1_parameter_band.csv]
    TestCsvProvenanceMap::test_multi_seed_band_declares_its_seed_coverage[generalization_sweep_per_camera_band.csv]
    TestSelfDescribingJson::test_schema_versionless_json_set_equals_self_describing_json

**Why they fail:** the tests are parametrized over the artifacts actually present in the
committed `experiments/results/` tree, which exists only on `results/rerun-freeze-01`. They
are asserting provenance properties of the 2026-08-20 run's output, not of any code this
phase touches.

**Why not fixed here:** plan 29.1-01's hard constraint 2 forbids regenerating any committed
artifact under `experiments/results/`, which is what most of these would need. Fixing them
by amending the provenance map instead would be a change to what the project accepts as
evidence, made outside any plan that reasoned about it.

**Where it matters:** D-14 requires the **full test suite** to pass locally before the
`rerun-freeze-02` tag is cut (plan 29.1-08). These 8 failures will meet that bar. Plan
29.1-08 must either resolve them, or record an explicit expected-by-construction ruling for
them in `29.1-PREPUSH-AUDIT.md` the way Phase 27 attempt 1 ruled on its GATE FAIL.
