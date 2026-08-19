# 26-13 SUMMARY — seed provenance on E1's and E7's benchmark records

**Status:** COMPLETE. One commit covering both tasks (`56e1ae5`).
**Executed by:** the orchestrator, inline (not dispatched to an executor).

## What was wrong

`gate3_provenance` reads `record["seed"]` or `record["solver_config"]["seed"]`
(`check_rerun_gates.py:374-378`). E1's three and E7's two `write_direct_call_benchmark` call
sites never passed one, so six gated records failed the gate in **every** run — including the
26-10 smoke pass, on records it had just written with current code.

Verified against the full-scale archived artifacts, not just the reduced-scale pass: walking
`pre_rerun_baseline/results/e7_benchmark_shared_fixed.json` and `e1_benchmark_refractive.json`
found **no key containing "seed" at any nesting depth**.

The consequence was not cosmetic. Phase 29's RUN-03 is "gates pass"; six unconditional FAILs make
that unsatisfiable and turn the frozen run's gate output into a list a human must hand-triage into
"expected" and "real" — the condition F-001 came out of.

## The fix

The writer has accepted `seed=` since plan **19.2-02**; it folds the value into a shallow copy as
`solver_config["seed"]` and raises if the passed dict already holds that key. Only the call sites
were missing it. E4 (`e4_cells/*/benchmark.json`, `solver_config.seed=42`) and E6
(`e6_configs/*.json`, top-level seed) already passed it, and E5's sidecar carries `seed`
directly — which is why the failing set was exactly six and not more.

| Site | Path | Seed passed |
|---|---|---|
| `e1_refractive_comparison.py:841` | `_run_full` | `args.seed` |
| `e1_refractive_comparison.py:968` | `_run_smoke` | `args.seed` |
| `e1_refractive_comparison.py:1315` | `_run_band` | `seeds[-1]` |
| `e7_interface_ablation.py:693` | `_write_ablation_artifacts` | `seed` (new parameter) |
| `e7_interface_ablation.py:866` | `_run_band` | `seeds[-1]` |

`_write_ablation_artifacts` did not receive a seed at all; it gained a `seed: int` parameter,
threaded from its three callers, all of which already had `args.seed` in scope.

## Deviation worth review: the band paths contradicted a documented decision

E1's module docstring said the band-written records "are seedless legacy records that band mode
must never overwrite with a single seed's values", and E1/E7 both wrote only
`solver_config["seeds"]` (the full swept list).

Leaving the band sites alone was not viable: `e1_band` and `e7_band` run **after** their
single-seed stages and rewrite the same filenames, so seeding only the single-seed paths would
leave the final artifacts seedless and the gate still failing — which is exactly the ordering the
26-10 roll-up showed.

Both band sites now pass `seeds[-1]`, and **this is factually accurate rather than a compromise**:
each file's own docstring already states the payload is taken from the last seed's run
("The benchmark payload ... is taken from the LAST seed in `seeds`'s run"). The record is labelled
with the seed it actually measured. `solver_config["seeds"]` keeps the full list, so the two
fields make different statements: `seed` names what this record measured, `seeds` what the band
swept.

Both docstrings were updated to say so. **Flagging it because it reverses a sentence that was
written deliberately** — if the intent was that these records must stay unlabelled even when they
describe one specific solve, this is the change to revisit.

## Corrected: the `SEEDLESS_LEGACY_RECORDS` comment was wrong

`tests/unit/test_experiments_provenance.py` carries a carve-out naming exactly these six files,
whose comment claimed the exemption "is removed the moment any of these six is regenerated".

That premise was false. 19.2-02 added the writer's *parameter* but not the call sites, so
regenerating those six never stamped a seed — the 26-10 smoke pass regenerated all six and the
gate still reported six FAILs. The comment now records what actually happened and why the named
files stay exempt: they are the archived Phase-19.1 artifacts under
`experiments/pre_rerun_baseline/results/`, exempt because they will never be rewritten, not
because a rewrite would fix them.

The carve-out's membership and its two exactness tests are unchanged and still pass.

## Tests

Three new tests in `tests/unit/test_experiments_provenance.py`:

1. **`test_e7_records_from_a_real_run_carry_a_seed`** — runs `run_all_arms(seed=7, smoke=True)`
   and `_write_ablation_artifacts(...)` into a tmp dir, then reads all four E7 files off disk and
   asserts `solver_config["seed"] == 7` and `_provenance_gaps(...) == []`. Real files, real run.
2. **`test_e1_records_carry_a_seed_through_the_writer`** — E1's two filenames, records constructed
   through the same writer. Stated plainly in the docstring as constructed, because E1's `--smoke`
   path writes into an internal `TemporaryDirectory` that `--out` cannot redirect
   (`e1_refractive_comparison.py:893`), so no file it writes survives the call, and its full and
   band paths are minutes long.
3. **`test_e1_call_sites_pass_a_seed`** — parses both modules with `ast` and asserts every
   `write_direct_call_benchmark` call passes `seed=`. This is what actually covers E1's argument
   threading, which test 2 cannot.

Assertions use the gate's own `_provenance_gaps`, not a re-implementation of its logic.

### RED gate

The tests were written after the fix, so RED was demonstrated by reverting: removing `seed=seed`
from `e7_interface_ablation.py:693` fails **two** of the three tests —

```
AssertionError: experiments/e7_interface_ablation.py:688 calls write_direct_call_benchmark
without seed= -- gate3_provenance will FAIL on its output
FAILED ...::test_e7_records_from_a_real_run_carry_a_seed
FAILED ...::test_e1_call_sites_pass_a_seed
```

The call site was restored immediately afterward.

## Verification

| Check | Result |
|---|---|
| `pytest tests/unit/test_experiments_provenance.py` | 298 passed, 25 skipped (66 s) |
| `_provenance_gaps` on fresh E1 and E7 records | `[]` |
| `git diff experiments/_io.py check_rerun_gates.py suite_expectations.json` | empty |
| Writer's duplicate-seed `ValueError` | not raised on any tested path |

## Flagged for Phase 29, not acted on

That module's `RESULTS_DIR` points at `experiments/pre_rerun_baseline/results` (`:45`) — the
**archived** tree. Every provenance test in it therefore validates an archive, and will pass no
matter what the frozen run produces. Repointing it belongs with the results commit in Phase 29,
not before the freeze; but until then this rail guards history rather than the run.
