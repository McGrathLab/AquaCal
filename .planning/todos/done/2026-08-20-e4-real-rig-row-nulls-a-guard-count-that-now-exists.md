---
created: 2026-08-20T00:00:00.000Z
title: E4's real-rig row nulls degenerate_observations_at_solution on a rationale that is no longer true, and the null is what fails gate 1
area: experiments
resolves_phase: 28
files:
  - experiments/e4_benchmark_grid.py
  - experiments/check_rerun_gates.py
---

Found by the 2026-08-20 production run at `rerun-freeze-01`. One of the **two real FAILs** in
the end-of-run roll-up (175 PASS, 7 N/A, 2 FAIL).

## The finding

    [FAIL] E4  gate1_guard_count:benchmark_grid.csv
           benchmark_grid.csv: 1 of 10 row(s) have a non-zero or missing guard count

The row is `real_rig_13cam_200fr` — the `record_source="pipeline"` row harvested from E2.
Its `degenerate_observations_at_solution` cell is **empty**, and gate 1 refuses by design to
read a missing field as zero ("an un-instrumented artifact is not evidence of a clean solve").

`_extract_pipeline_row` (`e4_benchmark_grid.py:1380`) hardcodes the null:

```python
# D-26: E2's benchmark.json predates this plan's discard_stats
# threading and stays out of this phase's re-run scope (E2 is real
# data, unaffected by a synthetic scenario-geometry change); None
# rather than invented (D-14).
"degenerate_observations_at_solution": None,
```

**That rationale is now stale.** The `results/benchmark.json` this function reads carries the
field twice:

    /problem_shape/degenerate_observations_at_solution   198
    /discard_stats/degenerate_observations_at_solution   198

plus the full cause and fate decomposition (198 `above_interface`, 198 `fate_extended`,
0 `behind_camera`, 0 `interface_below_camera`). So the value is not absent — it is being
discarded by a comment describing a state of the world that ended when `discard_stats`
threading landed.

## Why this is a decision, not a patch

Wiring the field through does not make the FAIL go away — it converts it. E4's publish rule is
exactly `> 0`, never a threshold (`e4_benchmark_grid.py:1511-1529`), so a populated 198 flips
the real-rig anchor row to `status="degenerate"` with
`"first-order optimality is unreliable for this cell (D-19.3-11)"`.

The library disagrees with that reading on the same numbers. `pipeline.py:1288`'s warning puts
198 at **0.268% of 73,975 observations**, below its 1% threshold, and says so explicitly:

> At 0.268% this is a small tail below the 1% threshold, so it is reported for the record
> rather than as a verdict on the whole solve: the reported first-order optimality (18.39,
> termination status 2) is not declared unreliable on the strength of this count alone.

So three options, and the choice is the author's:

1. Thread the field through and accept the anchor row publishing as `degenerate`.
2. Thread it through and give E4's rule a threshold consistent with the library's 1%.
3. Keep the null, and replace the stale D-26 comment with the real reason plus an explicit
   gate-1 exemption for `record_source="pipeline"` rows, so the FAIL stops being noise.

Option 3 is the smallest change and the only one that does not touch a published number one
day before submission.

## Related, not duplicated

- `2026-08-15-classify-the-198-unprojectable-observations.md` — asks **what the 198 are**
  (breached interface vs critical angle). This TODO is about the count not reaching the grid
  at all, and is independent of how that one resolves.
- `2026-08-13-e4-aggregator-hardcodes-e2-benchmark-path.md` — same harvest path, same
  function's neighbourhood; both are about the real-rig row being second-class. Worth fixing
  together.

## Evidence

    experiments/results/benchmark_grid.csv          row real_rig_13cam_200fr, empty guard cell
    experiments/results/benchmark.json              198, twice, with full cause/fate breakdown
    stagelogs/e2_production.log                     the DegenerateObservationWarning in full

---

## Resolved 2026-08-24 — OPTION 3 EXTENDED: the value is published AND the row is exempt (D-01, D-02, D-03)

Phase 29.1, plan `29.1-01`. Of the three resolutions offered above, the author chose neither
option 3 as written (keep the null) nor option 2 (give E4's rule a threshold). The resolution
taken is **option 3 extended**: the count E2 measured is now **published** rather than nulled,
and the `record_source="pipeline"` row is **exempt at both** the publish rule and gate 1.

**Why not option 3 as written.** Keeping the null keeps a measured number out of a
Zenodo-bound artifact for no reason other than a comment that had gone stale. The value exists
under two keys in the record E4 already reads.

**Why not option 2.** A threshold in E4's publish rule would relax the gate for the nine
*synthetic* cells too, where the library's 1% reasoning does not apply — those cells can be
re-run with different geometry, so a non-zero count there is a defect to fix, not a fact to
live with. The exemption is keyed to the row kind, not to a magnitude.

**Why the exemption had to land in two places (D-02).** Populating the field makes gate 1 see
`198`, which fails the "non-zero" half of its predicate exactly as the null failed the
"missing" half. Fixing only `e4_benchmark_grid.py` converts one FAIL into a different FAIL.

### What changed

| Site | Change |
|---|---|
| `e4_benchmark_grid._extract_pipeline_row` | Reads `degenerate_observations_at_solution` from `discard_stats` (canonical) with `problem_shape` as fallback. Absent from both still returns `None` — "never measured" stays distinguishable from "measured zero", the property gate 1 rests on. |
| `e4_benchmark_grid._extract_pipeline_row` (comment) | The stale D-26 claim is **replaced**, not deleted (D-03): what the value's present-day source is, what the 198 physically are, and that the row is exempt at both sites. |
| `e4_benchmark_grid.build_grid_dataframe` (comment) | The `> 0` downgrade now states it is scoped to `record_source="assembled"` rows and that the pipeline row's exemption is intentional — previously the exemption was real but purely structural, and a refactor unifying the two branches would have silently flipped the anchor row to `status="degenerate"`. |
| `check_rerun_gates._check_guard_column` | Excludes `record_source="pipeline"` rows from `bad_mask`. **One** gate result is kept, not a second gate id — the roll-up's PASS/N/A/FAIL arithmetic is an audited number. Frames with no `record_source` column are byte-identical to before. |

### Roll-up, before and after

Full-profile gate check over the committed `experiments/results/` (the 2026-08-20 run's output,
**not regenerated** by this fix — `git diff --quiet -- experiments/results/` exits 0):

| | PASS | N/A | FAIL |
|---|---|---|---|
| Before (2026-08-20 as-run) | 175 | 7 | 2 |
| After (this plan) | **176** | 7 | **1** |

The surviving FAIL is `e1_band completeness:e1_seed_band_degeneracy_breakdown.json`, which plan
`29.1-02` owns (D-04). E4's gate now reads:

    [PASS] E4  gate1_guard_count:benchmark_grid.csv
           benchmark_grid.csv: 9 of 10 row(s) gated, guard count zero everywhere;
           1 row(s) exempt (real_rig_13cam_200fr=missing) -- a record_source='pipeline'
           row is a real-hardware anchor row whose count the library itself declines to
           treat as a verdict at 0.268% of 73,975 observations (pipeline.py:1288), so it
           is published and reported here rather than gated on (D-01/D-02)

The exempt row reads `missing` rather than `198` because the committed CSV is deliberately not
regenerated by this phase; the writer fix reaches the artifact on the next run. The gate's
exemption covers both shapes, and a test pins that.

### What now pins this

- `tests/unit/test_experiments_e4.py::TestPipelineRowGuardCount` — the four read shapes
  (`discard_stats`, `problem_shape` fallback, precedence, un-instrumented → `None`) plus
  measured-zero → `0`.
- `tests/unit/test_experiments_e4.py::test_real_rig_row_keeps_status_ok_at_a_non_zero_guard_count`
  — the pipeline row stays `"ok"` at 198 while a synthetic cell at 4 in the **same frame** is
  still downgraded to `"degenerate"`.
- `tests/unit/test_rerun_gates.py::TestGate1PipelineRowExemption` — the exemption is named in
  the PASS message with its count and reason; an `assembled` row with a non-zero count still
  FAILs; an `assembled` row with a **missing** count still FAILs; a frame with no
  `record_source` column is asserted byte-identical on the whole `GateResult`.

All fixtures are synthetic. No test asserts on `experiments/results/` content, so the re-run
cannot break them.

### Still open, deliberately

`2026-08-13-e4-aggregator-hardcodes-e2-benchmark-path.md` is the same function's neighbourhood
and the same underlying complaint (the real-rig row is second-class), but it is a separate
resolution and stays pending.
