---
phase: 24-degeneracy-instrumentation
plan: 02
subsystem: experiment-artifacts
tags: [degeneracy, benchmark-json, csv-columns, sidecar, rerun-gates, DEGEN-01, DEGEN-05, D-09, D-11, D-12, D-22]
requires:
  - "plan 24-01's 32-entry DISCARD_KEYS, its cause/fate/denominator split and the SolverDiagnostics optimality_by_block/parameters_at_bound fields"
  - "assemble_benchmark_record's memory_readings omit-when-None precedent"
  - "e6_generalization_sweep.py's append-only column convention and None-when-never-computed row convention"
provides:
  - "benchmark.json's top-level discard_stats block plus the problem_shape mirror of the merged total"
  - "experiments/_degeneracy.py: DEGENERACY_COLUMNS, summarize_degeneracy_columns, write_degeneracy_breakdown"
  - "six append-only degeneracy columns on E5, both E7 artifacts and E1's exp2_spatial_errors.csv"
  - "the e{N}_degeneracy_breakdown.json sidecar family, single-seed and band-owned"
  - "check_rerun_gates.py's _guard_breakdown_from_record and the enriched guard report"
  - "the Phase 26 (DRIVER-01) hand-off inventory"
affects:
  - "Phase 26 DRIVER-01/DRIVER-03: E5_COLUMNS and ABLATION_COLUMNS changed shape, so --check reports a header mismatch until those artifacts are regenerated"
  - "Phase 25 DEGEN-04: the gate now prints cause and fraction but interprets neither"
tech-stack:
  added: []
  patterns:
    - "pass the whole dict, not a hand-picked field list (D-11), reused for both the benchmark block and the sidecar"
    - "append-only experiment columns with the axis carried in the column name"
    - "module-scope pytest fixture for a band run (mirrors test_e6_band_mode.py:74)"
key-files:
  created:
    - experiments/_degeneracy.py
  modified:
    - src/aquacal/io/benchmark.py
    - src/aquacal/calibration/pipeline.py
    - docs/guide/benchmarking.md
    - experiments/e1_refractive_comparison.py
    - experiments/e5_index_sensitivity.py
    - experiments/e7_interface_ablation.py
    - experiments/e7_focal_standoff_analysis.py
    - experiments/check_rerun_gates.py
    - tests/unit/test_benchmark.py
    - tests/unit/test_e5_band_mode.py
    - tests/unit/test_e7_focal_standoff.py
    - tests/unit/test_e7_band_mode.py
    - tests/unit/test_rerun_gates.py
    - tests/synthetic/test_full_pipeline.py
    - .planning/todos/pending/2026-08-15-suspend-programmatic-check-for-reshaped-artifacts.md
decisions:
  - "E1's six columns went to exp2_spatial_errors.csv, NOT to the three D-19 byte-identical-header CSVs an external figures repository reads (see Deviations)"
  - "Band runs write a band-owned e{N}_seed_band_degeneracy_breakdown.json so a --seeds run never overwrites a single-seed artifact"
  - "optimality_by_block needed no per-experiment work: it is a SolverDiagnostics field, so assemble_benchmark_record already emits it beside each stage's optimality"
metrics:
  tasks: 3
  commits: 4
  duration: single session
  completed: 2026-08-17
---

# Phase 24 Plan 02: Degeneracy Artifact Persistence Summary

Carried plan 24-01's split counters out of the library and into the artifacts a reader actually
checks: `benchmark.json` now carries the whole `discard_stats` dict as its own block plus a
mirrored merged total, E1/E5/E7 publish both axes as six append-only CSV columns backed by a
per-run JSON sidecar holding the per-stage breakdown and denominators, and the re-run gate reads
the split — reporting dominant cause and a recorded fraction while keeping its verdict at exactly
`count > 0`.

## What Shipped

**Task 1 — the benchmark record (`9102b7c` RED, `6c76986` GREEN).**
`assemble_benchmark_record` gained a keyword-only `discard_stats: dict | None = None`, emitted as
a top-level block and omitted entirely when `None` (`memory_readings`' precedent). `pipeline.py`
passes `discard_stats=dict(discard_stats)` and mirrors the merged total into `problem_shape`, with
a comment stating why it is deliberately BOTH: the whole-dict pass is the structural fix (every
future counter arrives automatically), the mirror only keeps the existing read shape working.
`docs/guide/benchmarking.md` documents the block, including the two-axes note.

**Task 2 — the experiment artifacts (`a55c6f1`).** A new `experiments/_degeneracy.py` owns
`DEGENERACY_COLUMNS`, `summarize_degeneracy_columns` (raw dict → six values, `None` when never
computed) and `write_degeneracy_breakdown`. The six names are additionally spelled out verbatim in
each experiment's own column list — with an `assert` tying each list's last six entries to the
shared tuple — so a reader sees the names without chasing an import and the two can never drift.
`test_e5_band_mode.py::TestBandMode` moved onto a module-scope fixture.

**Task 3 — the gate and the hand-off (`a381453`).** `_guard_breakdown_from_record` uses the same
three read shapes as `_guard_count_from_record`; `_format_guard_breakdown` renders dominant cause,
its fraction against the recorded denominator, and the fate split, with both axes labelled. The
`cannot confirm zero` FAIL now explains that an absent field means a stale artifact. The
reshaped-artifacts todo gained a `## Phase 24 additions` section.

## Evidence

### `benchmark.json` as actually written by the harness test

Captured from a real `run_calibration_from_config` run through
`_run_full_pipeline_with_mocked_video_io` (4 cameras, 16 calibration frames):

```json
{
  "discard_stats": {
    "degenerate_observations_at_solution": 0,
    "degenerate_observations_cause_above_interface__stage3_interface_optimization": 0,
    "degenerate_observations_cause_behind_camera__stage3_interface_optimization": 0,
    "degenerate_observations_cause_interface_below_camera__stage3_interface_optimization": 0,
    "degenerate_observations_fate_extended__stage3_interface_optimization": 0,
    "degenerate_observations_fate_penalized__stage3_interface_optimization": 0,
    "observations_evaluated__stage3_interface_optimization": 5603,
    "pnp_attempts_nonrefractive": 131,
    "pnp_attempts_total": 131
  },
  "problem_shape": {
    "degenerate_observations_at_solution": 0,
    "n_cameras": 4,
    "n_frames_calibration": 16,
    "n_frames_holdout": 4
  }
}
```

Three things this shows that no prior artifact did: the mirror and the block agree; a clean run
emits the counters at an explicit **0** rather than omitting them (D-04, verified end to end for
the first time); and the pre-existing `pnp_*` keys came along without being named — the whole-dict
pass working as intended.

### `E5_COLUMNS`

`len(E5_COLUMNS) == 23` (was 17). `E5_COLUMNS[-6:]`:

```
degenerate_observations_at_solution
degenerate_observations_cause_above_interface
degenerate_observations_cause_behind_camera
degenerate_observations_cause_interface_below_camera
degenerate_observations_fate_extended
degenerate_observations_fate_penalized
```

`ABLATION_COLUMNS` is 23 entries with the same last six, in the same order. Both are appended, so
every pre-existing column keeps its index — asserted positionally in
`test_band_row_carries_the_six_degeneracy_columns` and, for E7, by the pre-existing
`test_ablation_columns_unchanged`.

### Cause-sum and fate-sum on a generated row

`test_each_axis_sums_to_the_merged_total_on_a_generated_row` builds a row through `build_row`
(not a hand-written dict) from a `discard_stats` whose entries deliberately span two stages:

| quantity | value |
|---|---|
| `degenerate_observations_at_solution` | **5** |
| cause columns summed (`4 + 1 + 0`... i.e. `3 + 2 + 0`) | **5** |
| fate columns summed (`4 + 1`, the `1` recorded under `stage3_intrinsic_pass`) | **5** |

Each axis reaches the merged total independently, and the cross-stage summation is exercised
rather than assumed. `5 + 5 != 5` is exactly the double count the `cause_`/`fate_` prefixes exist
to prevent.

### Sidecar filenames per experiment

| writer | filename | keyed by |
|---|---|---|
| E1 `_run_full` / `_run_smoke` | `e1_degeneracy_breakdown.json` | model label |
| E5 `_run_full` | `e5_degeneracy_breakdown.json` | `"band"` |
| E5 `--seeds` | `e5_seed_band_degeneracy_breakdown.json` | seed |
| E7 ablation, single-seed | `e7_degeneracy_breakdown.json` | arm name |
| E7 ablation, `--seeds` | `e7_seed_band_degeneracy_breakdown.json` | seed, then arm |

`ls experiments/results/` before the change confirmed no `e*_degeneracy_breakdown.json` existed
and no collision with the four committed `e{1,5,6,7}_seed_band_provenance.json`.

### D-22: `test_e5_band_mode.py` wall-clock

| | tests | wall-clock |
|---|---|---|
| before (per-test band run) | 11 | **366.19 s** |
| after (module-scope fixture) | 15 | **126.17 s** |

2.9x faster while running four MORE tests. The plan quoted 317 s from D-22's earlier measurement;
366.19 s is what this machine measured today on the unmodified file.

### `optimality_by_block` reaches E1's benchmark records with no new plumbing

It is a `SolverDiagnostics` field, and `assemble_benchmark_record` builds each stage block from
`dataclasses.asdict(diag)`. The pre-existing
`test_every_solver_diagnostics_field_appears_in_stage_dict` therefore already asserts it lands
beside that stage's `optimality`, in E1's `e1_benchmark_<model>.json` as much as in the
pipeline-written record. `_to_native` recurses through its `dict[str, dict]` shape, so no
serialization work was needed either. Recorded here rather than re-implemented (ROADMAP criterion
5's persistence half).

### Hand-off section heading

`## Phase 24 additions (written 2026-08-17 by plan 24-02 — for DRIVER-01's completeness audit)`,
appended to `.planning/todos/pending/2026-08-15-suspend-programmatic-check-for-reshaped-artifacts.md`
before its `## Related` section. No other section of that file, and no part of its frontmatter,
was touched.

## Test Results

All targeted; the full suite was **not** run — that is the orchestrator's post-merge gate.
`PYTHONPATH` was set to this worktree's `src` for every run, so these are this branch's code.

| Command | Result |
|---|---|
| `pytest tests/unit/test_benchmark.py` | **35 passed** (33.9 s) |
| `pytest tests/synthetic/test_full_pipeline.py -k "benchmark or discard"` | **6 passed** (284.5 s) |
| `pytest tests/unit/test_e5_band_mode.py` | **15 passed** (126.2 s) |
| `pytest tests/unit/test_rerun_gates.py tests/unit/test_benchmark.py` | **94 passed** (36.9 s) |
| `pytest tests/unit/test_e7_focal_standoff.py` | **21 passed** (1.0 s) |
| `pytest tests/unit/test_experiments_e1.py` | passed (in the 31-passed run with focal_standoff) |
| `pytest tests/unit/test_e1_band_mode.py -k "Merge or contract"` | **6 passed** (1.0 s) |
| `ruff check src/aquacal/calibration/pipeline.py src/aquacal/io/benchmark.py experiments/ tests/unit/test_e5_band_mode.py tests/unit/test_rerun_gates.py` | clean |

**Not completed:** `pytest tests/unit/test_e1_band_mode.py tests/unit/test_e7_band_mode.py -m "not
slow"` exceeded the 600 s tool ceiling and was left running rather than waited on (CLAUDE.md's
standing rule: never end a turn waiting on a backgrounded run). Its band tests each execute a full
E1/E7 smoke calibration, so `-m "not slow"` does not bound them — the same trap the knowledge base
records for the suite as a whole. Substituted: the fast subset above, plus the observation that
`test_ablation_columns_unchanged` asserts the band CSV header against the `ABLATION_COLUMNS`
constant itself, so appending to that constant cannot desynchronize it. The orchestrator's
post-merge gate covers the rest.

## Deviations from Plan

### 1. [Rule 4 avoided — plan/codebase conflict] E1's six columns went to `exp2_spatial_errors.csv`, not to the frames the plan named

- **Found during:** Task 2
- **Issue:** The plan says to "append the six columns to whichever `_build_dataframes` output
  frames carry a `model` column". All four carry one — but three of them (`EXP1_COLUMNS`,
  `EXP2_COLUMNS`, `EXP3_COLUMNS`) are declared in E1's own module docstring as **FIXED CONTRACTS,
  byte-for-byte identical headers to the committed baselines the external figures repository
  (read-only, outside this repo) reads (D-19). Do not add, remove, reorder, or rename a column.**
  Following the plan literally would have broken a consumer outside this repository, which is a
  strictly worse failure than the one it fixes.
- **Fix:** The six columns went to `exp2_spatial_errors.csv` (`SPATIAL_COLUMNS`) — the only
  `_build_dataframes` output with a `model` column that is E1's own new output, has no committed
  baseline, and is explicitly excluded from `--check` (D-20, confirmed at `_run_check`'s
  docstring). The counter is per-model, so each model's six values repeat across that model's
  rows; no per-point split was fabricated. E1 still gets full coverage via the sidecar and the two
  benchmark records.
- **Left for Phase 26:** the hand-off note states this explicitly, so DRIVER-01's audit sees it as
  a deliberate, reversible decision rather than an omission. If E1 must publish these in a
  `--check`ed artifact, that is a D-19 renegotiation with the figures repository.
- **Files modified:** `experiments/e1_refractive_comparison.py`
- **Commit:** `a55c6f1`

### 2. [Rule 3 — blocking] A new `experiments/_degeneracy.py` rather than editing `experiments/_io.py`

Four files needed the same summarizer and sidecar writer. `_io.py` is the natural home but is not
in this plan's `files_modified` and is shared by every experiment, so editing it risked a merge
conflict with a sibling wave-2 plan (the knowledge base's "wave disjointness is spatial" note). A
new module has no such exposure. The six column names are still spelled verbatim in each
experiment's own column list, with an `assert` binding each list to the shared tuple.

### 3. [Rule 1 — bug] `test_e7_focal_standoff.py::test_column_set_unchanged` broken by the appended columns

- **Issue:** It asserted `list(result.columns) == [...nine...]` — exact whole-header equality,
  which appending six columns necessarily falsifies. The property it exists to protect is that no
  pre-existing column was renamed, reordered or dropped.
- **Fix:** Re-anchored to a prefix assertion on the nine, plus a companion assertion that the six
  new columns are appended last and in the shared order — the same repair 24-01 applied to
  `test_n_residuals_field_order`. Renamed to `test_original_column_set_and_order_unchanged`. Added
  `test_band_without_degeneracy_columns_yields_none_not_zero`, which covers the case the fixture
  already exercised silently: a band CSV predating plan 24-02 must produce `None`, not `0`.
- **Files modified:** `tests/unit/test_e7_focal_standoff.py` (not in the plan's `<files>`)
- **Commit:** `a55c6f1`

### 4. [Rule 2 — missing critical functionality] Band runs write a band-owned breakdown filename

The plan names one sidecar per experiment. E5 and E7 both have a `--seeds` mode that must never
overwrite a single-seed artifact (T-19.5-05-01) — the reason `e5_provenance.json` and
`e5_seed_band_provenance.json` are separate files. Reusing one breakdown filename across both
modes would have reintroduced exactly that hazard, so band runs write
`e{5,7}_seed_band_degeneracy_breakdown.json`, keyed by seed. Asserted in
`test_band_mode_does_not_write_single_seed_artifacts`.

### 5. [Rule 2] E7's focal/standoff script sums the columns rather than recording them

`e7_focal_standoff_analysis.py` is pure re-analysis — it runs no calibration and has no
`discard_stats` to record. Its six columns are the per-arm sum of the band CSV's own columns of
the same names, and are `None` (never `0`) when the input band predates them. It writes no
sidecar; the breakdown for E7 belongs to `e7_interface_ablation.py`, which produced the counts.

### 6. [process] `test_e7_band_mode.py`'s stale docstring corrected

`test_ablation_columns_unchanged`'s docstring said "E7 gains only the sidecar — ABLATION_COLUMNS
must not change", which was true of D-19.4-14 and is no longer true. The assertion is against the
constant so it still passes unchanged; only the docstring was updated, to explain what the test
protects now.

## Notes for Phase 26 (DRIVER-01/DRIVER-03)

Everything is written up in the todo's new `## Phase 24 additions` section. The two items most
likely to surprise an audit:

- **`--check` now reports a header mismatch** on `index_sensitivity.csv`,
  `interface_ablation.csv` and `e7_focal_standoff.csv` until those artifacts are regenerated —
  `compare_experiment_csv` fails on any header difference before it compares a single cell. This
  is the "E5 gains persisted degeneracy columns" row of that todo's own table, now also true of
  both E7 artifacts. It is expected and pre-declared, not a finding.
- **E1's three frozen CSVs deliberately did not change**, so an audit expecting six new columns
  everywhere will find E1 short. Deviation 1 above records why and what renegotiating it costs.

## Self-Check: PASSED

- All four commits verified present in `git log b41982759bb95d34e27847f95ad8ba474b832bbe..HEAD`:
  `9102b7c`, `6c76986`, `a55c6f1`, `a381453`.
- `experiments/_degeneracy.py` verified created; all 15 modified files verified present in
  `git diff --name-only b41982759..HEAD`.
- `git diff --name-only` against the base lists NONE of: `.planning/STATE.md`,
  `.planning/ROADMAP.md`, `.planning/MANUSCRIPT-FINDINGS.md`, anything under `Spinoffs/`,
  `experiments/rerun_19_3.sh`, `experiments/e6_generalization_sweep.py`,
  `src/aquacal/core/refractive_geometry.py`, or any `src/aquacal/calibration/` file other than
  `pipeline.py`.
- No package installed, added, removed or upgraded; `pyproject.toml` untouched (T-24-SC).
- No experiment script and no calibration was run (D-17).
