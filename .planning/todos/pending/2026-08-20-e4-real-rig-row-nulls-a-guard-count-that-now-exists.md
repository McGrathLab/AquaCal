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
