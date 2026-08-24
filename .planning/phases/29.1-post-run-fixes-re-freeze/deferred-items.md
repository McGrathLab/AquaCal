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

---

## Stale figures in `.planning/MANUSCRIPT-FINDINGS.md` (found by plan 29.1-03, not fixed)

**Found:** 2026-08-24, during plan 29.1-03's bounded stale-string sweep, while verifying
`e6_generalization_sweep.py:625` and `e1_refractive_comparison.py:51` against the committed
2026-08-20 artifacts. Recorded in `29.1-STALE-STRING-AUDIT.md` § *Twin sites outside the boundary*.

Two manuscript findings carry figures the 2026-08-20 run has since remeasured:

- **MF-12 (`:1558-1564`)** — its decomposition table gives the seed-43 line-layout signed means as
  `-18.8547 / -18.4955 / -0.3592 mm`. The committed `generalization_sweep_per_camera_band.csv` from
  the 2026-08-20 run measures `-18.8593 / -18.4996 / -0.3596 mm`. The finding — ~80% gauge, ~20%
  physical — is unchanged; only the digits moved, in the fourth significant figure.
- **MF-16 (`:751`)** — states that MF-08's `97-178x` ratio band and the `2 of 10 seeds exceed 2 mm`
  finding "both regenerate from the newly committed" `exp1_band.csv`. Ruling A1 (2026-08-15) cut
  E1's band from ten seeds to four, so they do not: both are n=10 figures, and the committed
  four-seed band yields a `92-179x` spread instead. `e1_refractive_comparison.py:51` and
  `run_experiment_suite.sh:1471` carried the same claim in source and were corrected by plan
  29.1-03; MF-16 is the planning-side twin.

**Why not fixed here:** `.planning/` is outside D-09's bound, and a manuscript finding is *supposed*
to record what was measured when it was written — editing the digits in place would destroy the
provenance trail rather than repair it. What both entries need is a dated re-measurement note, and
that is a manuscript-session decision, not an experiments-suite edit.

**Where it matters:** MF-12's figures reach §3's layout discussion and MF-16's reach the abstract's
improvement ratio. Neither is a *phase* blocker — no gate reads them and no artifact moves — but
whoever next edits §3 should re-measure both against the tree at `rerun-freeze-02` rather than
quoting the entries as they stand.
