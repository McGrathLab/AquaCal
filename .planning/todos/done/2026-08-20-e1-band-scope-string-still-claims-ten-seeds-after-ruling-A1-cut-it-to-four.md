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

---

## Resolved 2026-08-24 — the field is DERIVED from the run, not re-frozen at four (D-08, D-10)

Phase 29.1, plan `29.1-02`, task 3. The fix this todo asked for was "update the literal to say
four seeds and 256/384 rows". That was **not** the fix taken, and D-10 is why: three stale
rationales surfaced in a single day, each a claim outliving the conditions that produced it.
Re-freezing a correct number into the same literal buys one grid resize before the same defect
returns. So the class was fixed, not the instance.

**What the `scope` field now does.** `_run_band` builds it as an f-string at write time from the
run's own values: `len(seeds)` and the resolved seed list, `len(band_df)` and
`len(parameter_band_df)` read back from the frames just emitted, and the noise levels and depths
read back out of `band_df` (so a `--smoke` band describes its own collapsed axes instead of the
production grid). **Ruling A1** is cited by name — `run_experiment_suite.sh`'s
`run_stage_e1_band`, which carries the seed count, the reason for it and the row arithmetic — as
the reason the seed axis is the size it is. A stable cross-reference is a citation, not a
recomputed value, so it stays.

**Kept, unchanged in substance:** the `realistic` 12-camera synthetic-geometry restriction, the
warm-restart evidence that the non-refractive baseline is converged (largest relative drop
1.8e-9), the ill-conditioning caveat travelling with it (D-16), and D-19.3-17's qualified
demotion of E1's accuracy claim with E2 carrying the accuracy claim against reality.

**Dropped:** the forward-looking clause naming the phase that "will" execute and verify the band.
It is a schedule, not a domain, and it is the half of the string that needed re-dating after
every run — which is the defect.

**The module docstring carried the same claim**, and was corrected with it. This todo's "Fix"
section only named the `scope` literal, but `e1_refractive_comparison.py`'s module docstring
STATED DOMAIN paragraph repeated the ten-seed / 640-960-row / "executed in Phase 28, verified in
Phase 29" claim verbatim. Correcting one and leaving the other reads as complete from either
site alone — the exact partial-fix shape `tests/unit/test_stale_provenance_strings.py` exists to
catch — and the claim-sentence gate below is scoped to the file, so it could not pass with the
docstring left stale. The docstring now names the AXES and defers to the derived `scope` field
for the VALUES, quoting neither a seed count nor a row count, and keeps the retired ten-seed
figures under an explicit "the version that did" attribution so the trail survives.

**What pins it.**

- `tests/unit/test_e1_band_mode.py::TestBandScopeIsDerived` — seven cases covering the seed
  count/list, both emitted row counts, the noise levels and depths, a `--smoke` band's collapsed
  axes, the ruling A1 citation, the absence of any forward-looking clause, and the survival of
  the four static claims. Every expected value is built from the module's own constants, never
  hardcoded — a test that froze `4` or `256` into itself would be this defect one level up.
- `tests/unit/test_stale_provenance_strings.py::TestE1BandScopeIsDerived` — the filename-scoped
  claim-sentence gate, with `E1_PRE_RULING_A1_CLAIMS` quoting the seven pre-A1 clauses verbatim,
  plus positive assertions that the field is computed rather than merely deleted.

All seven claim-sentence assertions and all seven behaviour assertions were confirmed failing
against the pre-change implementation before the change landed.

**Still open, deliberately.**
`2026-08-14-decide-whether-e1-may-carry-absolute-accuracy-claims.md` still describes the pre-A1
ten-seed plan and is worth annotating with ruling A1, but the accuracy-claim decision is Phase
25/29 scope and stays pending.
