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
state-dependent**.

**Correction (2026-08-20, during Phase 29.1 planning).** The originally-filed mechanism —
"a clean `experiments/results/` removes the skip" — is wrong. Stage `e1` runs with `--force`
(`run_stage_e1`) and always precedes `e1_band` in the queue, so both records exist by the time
the band runs; that is why the skip fired on 2026-08-20 even though the run started clean. The
live hazards are narrower but real: a `--force` band run, or a standalone band invoked into a
fresh `--out` with no single-seed run before it — there the write proceeds and creates both
records stamped `seed=seeds[-1]`, silently, with a log that looks identical either way.

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

---

## Resolved 2026-08-24 — the policy is ENFORCED at the call, and the log reports the outcome (D-06, D-07)

Phase 29.1, plan `29.1-02`, task 2. Both halves landed; they were independent, as this todo said,
but the second is the one that mattered.

**The resolution chosen for D-07.** The `:1209` comment, the manifest and the band sidecar's own
reason for existing all say band mode does not own the `e1_benchmark_<model>.json` records; only
the docstring and the call site dissented, and the docstring was written to describe the call
site. Resolved in favour of the comment, in the form that keeps every reading true:

> Band mode may **CREATE** `e1_benchmark_<model>.json` when it is absent, and must **NEVER**
> overwrite one that exists — enforced at the call, not delegated to the resumability guard.

**Concretely, in `_run_band`:**

- the `write_direct_call_benchmark` call passes the **literal `False`** for `force`, ignoring the
  run's `--force`. A comment states that this is the one place `--force` is deliberately not
  honoured and why: honouring it is what would turn the policy above into a lie, silently
  republishing two records the single-seed stage owns with `seeds[-1]`'s values;
- the print is **branched on the writer's return value** (D-06) — a write confirmation only on
  `True`, and on `False` a distinct `Kept existing <path>: band mode never overwrites the
  single-seed benchmark record (D-07).` line. The wording deliberately differs from `_io`'s own
  `logger.info` skip text: two identical claims in one log is the shape this defect had;
- the docstring no longer asserts the sidecars are written unconditionally — it says they are
  written only when absent, and that the band's own seed record lives in
  `e1_seed_band_provenance.json`;
- the `:1209` comment states the policy as enforced and names the mechanism.

**The two source corrections are recorded in that comment**, because both were relied on when
this todo was filed and both were wrong on the original telling: (1) a clean
`experiments/results/` does not remove the skip — stage `e1` runs with `--force` and `e1_band`
`depends_on` `e1`, so both records exist by the time the band runs, which is why the skip fired
on 2026-08-20 despite a clean start; the live hazards are a `--force` band run or a standalone
band into a fresh `--out`. (2) `gate3_provenance` does not depend on this write — `_run_full`
already stamps `seed=args.seed` onto both records.

**E7 is untouched and the asymmetry is filed.** `experiments/e7_interface_ablation.py` carries
the identical call (`force=force`) and the identical docstring claim, and is out of this phase's
scope. `git diff --quiet -- experiments/e7_interface_ablation.py` exits 0. The hazard is filed at
`.planning/todos/pending/2026-08-20-e7-band-mirrors-e1-benchmark-overwrite-hazard.md`, which
names the asymmetry and E1's resolution; E1's comment names the asymmetry and points there.

**What pins it.** `tests/unit/test_e1_band_mode.py::TestBandBenchmarkWritePolicy` — six cases:
byte-identity under `--force` (the case that fails without the literal) and without it, the
kept-existing log line with no write claimed, creation into an empty `--out` with a confirmation
per path, `solver_config` carrying both `seeds` and `seed`, and the three band-owned outputs
still written unconditionally (D-19.4-14). Two of the six failed against the pre-change
implementation, which is exactly this defect.
