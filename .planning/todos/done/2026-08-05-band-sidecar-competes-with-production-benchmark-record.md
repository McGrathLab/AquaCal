---
created: 2026-08-05T00:00:00.000Z
title: Band run and production run compete for one benchmark sidecar, so gate4_band fails
area: experiments
files:
  - experiments/e1_refractive_comparison.py
  - experiments/e7_interface_ablation.py
  - experiments/rerun_19_4.sh
  - experiments/check_rerun_gates.py
  - experiments/_io.py
---

## Problem

The 19.4 production queue finished 8/8 with two `gate4_band` FAILs that were not
in the phase's expected-FAIL table:

```
[FAIL] E7 gate4_band:interface_ablation_band.csv  … 10 distinct seed(s) [42..51],
       but no sidecar matching 'e7_benchmark_*.json' records solver_config['seeds']
[FAIL] E1 gate4_band:exp1_band.csv                … same
```

### Mechanism (confirmed, not inferred)

E1 and E7 each run twice per stage: single-seed production **with** `--force`,
then the 10-seed band **without** it (`rerun_19_4.sh:298` vs `305`,
`rerun_19_4.sh:322` vs `330`). The band writer *does* set
`solver_config["seeds"]` (`e1_refractive_comparison.py:774`,
`e7_interface_ablation.py:698`), but passes `force=force`, and
`_io.py:711-716` skips when the path exists and force is false. The single-seed
run created the files first, so the band's write never happens.

The run logged it plainly — exactly 6 skips, matching exactly the 6 sidecars
missing the field:

```
Skipping write to …e7_benchmark_shared_fixed.json: file already exists and
--force was not given (resumability).
```

### Why the obvious fix is wrong

**Do not add `--force` to the band invocation.** The band writes from
`last_results` / `last_scenario` — the final seed's values. E1's own docstring:
*"reflecting the LAST seed's diagnostics/timings/accuracy (one provenance record
cannot represent N independent solves)."* Forcing it would overwrite the seed-42
production benchmark with seed 51's numbers. The current skip is what protects
the production record; the FAIL is the symptom of a correct guard.

### The actual design gap

With one filename and both runs writing to the same `OUT_DIR`, the production
record and the band's seed list cannot coexist — in either order the second
write destroys the first's meaning. D-19.4-14 folded the band into the stage
(`rerun_19_4.sh:61-64`); the sidecar format cannot express both. The gate asks
for something the layout makes impossible.

## Severity: low — recording only, no data affected

`exp1_band.csv` and `interface_ablation_band.csv` both carry all 10 seeds in a
`seed` column. Nothing is missing or wrong. What is absent is the
machine-checkable attestation of which seeds were *requested*. That is recorded
in `experiments/rerun_19_4.log`, itself a committed artifact:

```
[2026-08-05T16:27:54Z] e7: 10-seed band (42,43,…,51) -> interface_ablation_band.csv
```

So a human can verify the provenance; a script cannot. **No re-run is needed.**
Artifacts committed 2026-08-05 with this FAIL outstanding and understood.

## Solution

Preferred: give the band its own sidecar (`e1_benchmark_band.json`,
`e7_benchmark_band.json`) so the two records stop competing for one filename,
and point `gate4_band` at it. A few lines, and it makes the gate meaningful.

Rejected alternatives:
- `--force` on the band — actively destructive, see above.
- Relaxing `gate4_band` to accept the queue log — makes the gate unfalsifiable
  and brushes against anti-pattern #3 (the fix moves, never the tolerance).
- Separate `--out` dir for the band — changes artifact layout; the gate and the
  commit procedure both assume `results/`.

Whichever lands, add the expected-FAIL row to the next queue's prediction table
so this is not re-diagnosed from scratch.

## Related

Same run, unrelated cause: the other 8 FAILs are the four documented categories
(E1 provenance ×2, E1 guard count 14949, E4 grid 1-of-10, E7 provenance ×4).
`ALL gate3_git_sha_consistency` PASSED — every artifact carries `2a623f9`.

## Resolved (2026-08-15, verified at milestone close)

The preferred solution landed, in the shape this todo specified — band-owned sidecars, not
`--force`, not a relaxed gate.

- `experiments/results/e{1,5,6,7}_seed_band_provenance.json` all exist and all record
  `solver_config["seeds"]`: E1 and E7 `[42..51]`, E5 and E6 `[42..47]`.
- `check_rerun_gates.py:764` searches the band-owned sidecar **first** and falls back to the
  legacy `eN_benchmark_*.json` glob only for backwards compatibility; the call sites at `:1678`,
  `:1685` and `:1696` pass `band_sidecar=` for E7 and E1.
- The production single-seed sidecars are untouched, so the separation this todo identified as
  load-bearing still holds: band mode deliberately does not overwrite `e1_benchmark_<model>.json`
  (D-260807-dcv).

Landed via quick task 260807-dcv (`cda9d0e`, `fea64a9`). The gate now asks for something the
layout can express.
