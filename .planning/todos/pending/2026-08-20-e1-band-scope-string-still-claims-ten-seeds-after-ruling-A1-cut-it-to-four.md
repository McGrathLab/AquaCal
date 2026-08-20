---
created: 2026-08-20T00:00:00.000Z
title: e1_seed_band_provenance.json records four seeds while its own embedded scope string claims ten seeds and 640/960 rows
area: experiments
resolves_phase: 28
files:
  - experiments/e1_refractive_comparison.py
---

Found by the 2026-08-20 production run at `rerun-freeze-01`. No gate catches it: E1's band gate
compares the CSV's distinct seeds against the sidecar's recorded seed list, and those two agree
(both four). The free-text `scope` field is not parsed for E1.

## The finding

`experiments/results/e1_seed_band_provenance.json` contains, in one object:

    "solver_config": { "seeds": [42, 43, 44, 45] }

and

    "scope": "STATED DOMAIN (BAND-01, D-14): ... the 'realistic' scenario's single 12-camera
              synthetic geometry, TEN SEEDS, detection noise from 0.25 px to 1.2 px ... the
              four-level ten-seed band establishing it (640/960 ROWS) is executed in Phase 28
              at the frozen sha and verified in Phase 29 (D-21)."

The run *is* Phase 28 at the frozen sha. It executed **four** seeds and produced **256/384**
rows, not ten and 640/960.

## Four is correct; the prose is what is stale

`run_experiment_suite.sh:1452` (`run_stage_e1_band`) documents ruling A1 in full:

> **FOUR seeds and not ten:** ten seeds x four levels was sized at about 7 h in Phase 25; the
> uniform 4-seed grid is 16 of those 40 cells, about 2.8 h. 0.5 px IS one of the four levels,
> and that matters: the headline 97-178x ratio band and all sixteen ledger numbers backed by
> `exp1_band.csv` live at 0.5 px.

and the arithmetic pins the row counts: 4 x 4 x 16 = 256, 4 x 4 x 24 = 384. `EXPECTATIONS.md`
and the completeness gate both expect 256/384 and both PASS.

So the scope string is a survivor of the pre-A1 plan, which is also what
`2026-08-14-decide-whether-e1-may-carry-absolute-accuracy-claims.md` still describes
("across the existing ten seeds ... Row count goes 160 -> 640"). That TODO predates ruling A1
and should be annotated with it.

## Why it matters more than a typo

This string is not a comment — it is the `scope` field of a **provenance artifact**, written to
state the domain a published claim may be quoted over. It currently authorises quoting E1's
numbers over a ten-seed domain that was never run. Anyone reading the sidecar alone, which is
exactly what it is for, gets the wrong domain.

## Fix

Update the scope literal at `e1_refractive_comparison.py:1217+` to state four seeds and
256/384 rows, and cite ruling A1 for why. Then re-check the same string for the "executed in
Phase 28 / verified in Phase 29" clause, which will also need re-dating after the planned
re-run.
