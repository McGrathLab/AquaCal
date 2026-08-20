---
created: 2026-08-20T00:00:00.000Z
title: E1's band prints "Wrote <path>" for benchmark records the resumability guard skipped, so the run log states something false
area: experiments
resolves_phase: 28
files:
  - experiments/e1_refractive_comparison.py
  - experiments/_io.py
---

Found by the 2026-08-20 production run at `rerun-freeze-01`. Not caught by any gate — the gates
check artifact content, and the artifacts here are valid. Only the log lies.

## The finding

`stagelogs/e1_band.log` contains, consecutively:

    Skipping write to .../e1_benchmark_refractive.json: file already exists and --force was not given (resumability).
    Wrote .../e1_benchmark_refractive.json

Both lines are about the same file. `write_direct_call_benchmark` returns `False` without
writing when the target exists and `force` is falsy (`_io.py:875-881`), and `_run_band` prints
its confirmation unconditionally, ignoring the return value (`e1_refractive_comparison.py:1328`).

Confirmed against the artifacts: both `e1_benchmark_*.json` still carry the **stage 4** mtime
(00:15Z, the single-seed `e1` run) rather than stage 16's (01:12Z), and their `solver_config`
holds `seed: 42` with **no `seeds` key** — so `_run_band`'s docstring promise that the sidecars
"additively carry `solver_config["seeds"] = seeds`" did not happen.

## Severity: low now, latent later

For this run the outcome is arguably the intended one. The comment immediately above the write
(`:1209-1212`) says the opposite of what the code below it does:

> the `e1_benchmark_<model>.json` records below are seedless legacy records that band mode
> **must never overwrite** with a single seed's values

...and then the code calls the writer with `seed=seeds[-1]`. The resumability skip is the only
reason the policy in the comment was honoured. That makes the artifact content **order- and
state-dependent**: on a `results/` tree where stage 4 had not already run — a resumed queue, a
`--force` run, a fresh out-dir — stage 16 *would* overwrite both records with the last seed's
values, silently, and the log would look identical either way.

## The fix

Two small ones, and they are independent:

1. Print only on a true return: `if write_direct_call_benchmark(...): print(f"Wrote {path}")`,
   and print the skip otherwise. A run log that claims a write that did not happen is worse
   than no line at all.
2. Resolve the contradiction between `:1209-1212` and `:1300-1328`. Either band mode updates
   those records (and the comment is wrong) or it must not (and the call should not be there).

## Note for the re-run

If the suite is re-run into a clean `experiments/results/`, stage ordering changes what these
two files contain. Worth settling before then rather than after.
