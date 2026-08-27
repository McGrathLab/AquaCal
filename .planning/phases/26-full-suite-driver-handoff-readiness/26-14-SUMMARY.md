# 26-14 SUMMARY — the baseline rails follow the tree the frozen run writes

**Status:** COMPLETE. One commit (`88512b7`).
**Executed by:** the orchestrator, inline.
**Origin:** raised to the user 2026-08-18 while writing 26-13; they directed this one be fixed and
the resume gap deferred.

## What was wrong

DRIVER-04 (plan 26-09) emptied `experiments/results/`, and 26-01 (`e3a7bf3`) repointed four test
modules at `experiments/pre_rerun_baseline/results/`. Correct at the time — with the live tree
empty, the archive **is** the subject of any statement about committed baselines.

Nothing pointed them back. After Phase 28 repopulates the live tree, every provenance, schema and
exhaustiveness rail in those four modules would still validate the archive: **green regardless of
what the frozen run produced.** Same shape as the decision-coverage gate that reported passing
while parsing nothing.

26-01 half-saw this coming. Its commit message flags
`test_experiments_e5.py::TestDefaultMetricsPathAnchoring` as something that "re-tightens once Phase
28 repopulates `experiments/results/`" — a re-tightening that depended on someone remembering.

## The resolver

`tests/unit/_baseline_paths.py`: prefer the live tree once it **holds a file**, else the archive.

"Holds a file" rather than `.exists()` is the crux — 26-09's move leaves `experiments/results/`
present and **empty**, which is the repository's state between DRIVER-04 and Phase 28. It walks the
tree rather than reading the top level, because E4's records live at
`e4_cells/<cell>/benchmark.json`.

Three entry points: `resolve_results_dir()` returning `(dir, "live"|"archive")`, `baseline_file()`
for a single artifact resolved by the same rule, and `archive_results_dir()` for callers that
genuinely mean the archive.

`tests/unit/test_baseline_paths.py` drives both branches through a **sandbox** repo root, never the
real one. A resolver whose branches can only be distinguished by the repository's current state
would be untestable at exactly the moment it matters.

## The four modules do not all want the same treatment

This is the part that would have gone wrong under a blanket path swap.

| Module | Treatment | Why |
|---|---|---|
| `test_experiments_provenance.py` | resolver + `RESULTS_TREE` marker | its gates assert properties of *whatever tree is current* |
| `test_experiments_e3.py` | `baseline_file()` | `BENCHMARK_JSON_PATH` is **input** to `build_cpr_grouping_df`, not a subject |
| `test_experiments_e5.py` | `baseline_file()` | checks `compute_scale_bias` *against* committed data; fresher data is a stronger check |
| `test_experiments_io.py` | **`archive_results_dir()`, pinned** | asserts the committed record has **no** seed |

That last row is a live trap: `test_e1_committed_record_has_no_seed_key` asserts
`"seed" not in record["solver_config"]`, and plan 26-13 — hours earlier — made E1's call sites pass
`seed=`. Routing it through the resolver would have inverted it the moment Phase 28 lands.

The two `SEEDLESS_LEGACY_RECORDS` tests are pinned for the same reason, and **the carve-out itself
is now conditional**: exemptions apply only when the resolved tree is the archive. Against a live
tree no record is exempt, which 26-13 made true at write time.

## Also tightened

`TestDefaultMetricsPathAnchoring` asserted `resolved.exists() or archived.exists()`. Contrary to
its docstring, that does **not** re-tighten on its own — the disjunction stays permissive forever,
so a broken production path could be rescued by the archive indefinitely. The fallback is now
allowed only while the live tree is unpopulated.

## Verification

| Check | Result |
|---|---|
| `pytest tests/unit/test_baseline_paths.py` | 7 passed |
| Four modules, **before** | 412 passed, 25 skipped |
| Four modules, **after** | 414 passed, 25 skipped |
| Hardcoded archive paths outside the resolver | none, except comments, `tmp_path` fixtures, and a `--baseline-dir` CLI assertion |
| `experiments/` modified | no |

The +2 are this plan's own observability tests (`TestResolvedTreeIsObservable`). **Skips are
identical at 25**, which is the evidence that no pre-existing test changed subject or started
skipping — a changed skip count would have been the failure mode to catch.

`test_a_populated_live_tree_would_disable_the_carve_out` copies two real archived records into a
sandbox live tree and asserts the exemption predicate is False there — the Phase 28 state,
simulated now rather than discovered later.

## Deliberately not done

No production constant is repointed. 26-01 left those alone and routed the question to plan 26-03;
re-opening it here would have widened a test-infrastructure fix into a behavior change immediately
before the freeze.

Per the user's 2026-08-18 direction, the resume gap (`is_stage_complete` ignoring the exit-code
column, `run_experiment_suite.sh:669`) is **not** fixed and remains open.
