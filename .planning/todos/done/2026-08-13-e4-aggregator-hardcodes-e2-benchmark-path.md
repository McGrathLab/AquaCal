---
created: 2026-08-13T00:00:00.000Z
title: E4's aggregator hardcodes E2_BENCHMARK_PATH, so the real-rig row is dropped under --out
area: experiments
resolves_phase: 23
files:
  - experiments/e4_benchmark_grid.py
  - experiments/README.md
---

## Problem

`experiments/e4_benchmark_grid.py:226` resolves E2's real-rig row from a module-level
constant anchored to `__file__`:

```python
E2_BENCHMARK_PATH = (
    Path(__file__).resolve().parents[1] / "experiments" / "results" / "benchmark.json"
)
```

That anchoring is deliberate and correct as far as it goes — the comment above it records
why (a cwd-relative path silently resolves to nothing when the module is invoked from
anywhere other than the repo root, mirroring E3's `_E2_BENCHMARK_JSON_PATH`). What it does
**not** do is follow `--out`. So when the grid is run into a non-default output directory,
the nine synthetic cells are written there while the real-rig row is still sourced from
`experiments/results/benchmark.json`, which describes a different machine's run.

**Observed 2026-08-12** on the 32 GB Linux re-run: `results_linux32gb/benchmark_grid.csv`
carries the nine synthetic cells only, with no real-rig row at all. It was folded back in
by hand. The defect is currently discoverable only from `linux32gb_scope.json` and from
`experiments/README.md` §2.

**Severity is low, and the reason it is low is worth recording.** The two columns
`timing_scope` and `record_source` already exist specifically so a reader cannot compare
the synthetic rows against the real-rig row as if they measured the same thing, and
`benchmark_grid.tex` renders the real-rig row in its own labeled block. So the dropped row
degrades to a missing row rather than to a wrong one. The failure mode to avoid is the
opposite case: an `--out` run that silently *pairs* one machine's synthetic cells with
another machine's real-rig row, which is what happens today whenever
`experiments/results/benchmark.json` does exist and the run was not on that machine.

## Solution

Make the real-rig source follow `--out`, with an explicit and visible fallback rather than
a silent one. Sketch:

- Resolve the real-rig record relative to the output directory first
  (`out_dir / "benchmark.json"`), falling back to the `__file__`-anchored
  `E2_BENCHMARK_PATH` only when `out_dir` is the default `experiments/results/`.
- When neither resolves, emit the CSV **without** the real-rig row and say so on stdout —
  do not fall back across machines. A row absent and announced is safe; a row silently
  imported from another machine's tree is not.
- Whatever the resolution, record which path was used. `record_source` already
  distinguishes `assembled` from `pipeline`; the resolved path belongs beside it or in the
  run's own log, so a reader of a `--out` tree can tell whether the row is native.

Keep the `__file__` anchoring for the default path — removing it reintroduces the
cwd-relative bug its comment documents.

## Do not

- Do not "fix" this by copying `experiments/results/benchmark.json` into a `--out` tree.
  That manufactures a provenance record for a run that did not happen on that machine.
- Do not modify any committed artifact under `experiments/results/` or
  `experiments/results_linux32gb/` while fixing this. The hand-folded row in the Linux tree
  is documented in `linux32gb_scope.json` and stays as-is.
- Do not re-run the nine-cell grid to test this (~3.15 h). `--check` re-aggregates the
  committed per-cell records without running a cell, and the smoke cells
  (`SMOKE_CELLS = [(3, 3), (3, 4)]`) exercise the aggregation path cheaply.

## Related

- Filed out of `2026-08-12-merge-linux32gb-rerun-branch-to-main.md` item 4, which required
  this be documented or filed rather than left discoverable only from
  `linux32gb_scope.json`.
- `experiments/README.md` §2 names it beside the `results_linux32gb/` tree description.

## Re-scoped 2026-08-15 — now a pre-run blocker, not a low-severity annoyance

The severity assessment above was written when the observed failure was a one-off on
`results_linux32gb/` that got folded back in by hand. The committed full-suite re-run changes
that reading in two ways:

- **It will almost certainly run under `--out`,** on the Linux box, exactly as the 2026-08-12
  re-run did. So the fresh `benchmark_grid.csv` reproduces the defect by default: nine synthetic
  cells and no real-rig row, or — the worse case this todo already identifies — one machine's
  synthetic cells silently paired with whatever `experiments/results/benchmark.json` happens to
  hold from another machine.
- **There is no hand-fold available afterwards.** The re-run's premise is a single source of truth
  where every row traces to that run; splicing a row in by hand is the exact provenance failure
  the milestone exists to end.

**Land the fix before the run.** The instruction below not to re-run the nine-cell grid to test it
still stands and gets easier, not harder — `--check` re-aggregates from the committed cells, and
the smoke cells exercise the aggregation path in seconds. Testing this costs nothing; discovering
it after a multi-hour grid costs the grid.

## Two corrections measured 2026-08-17

**1. `--check` is structurally always-red, so it cannot serve as the test above.** Run today it
reports 9 of 10 cells mismatched. Enumerating all 35 compared columns: **33 metric columns
reproduce to 1e-6.** The only two failures are

- `exit_code` — committed `0.0` versus a recomputed `None`, because `_run_check`
  (`e4_benchmark_grid.py:1836`) hardcodes `"exit_code": None` at **:1872**; no subprocess runs
  under `--check`, so there is no exit code to report.
- `status_reason` — committed `NaN` versus a recomputed `''`.

Neither can ever clear, on any tree, so `--check` gives **red before the fix and red after it** and
would mask a real regression rather than catch one. Either exclude those two columns from the
comparison, or verify with the smoke cells only. Whichever is chosen, it is the same decision
DRIVER-03 is making about `--check`'s contract — settle it once, there, and have this fix consume
it rather than inventing a local answer.

**2. `_run_check` is itself on the defective path.** Line **1876** calls
`build_grid_dataframe(out_dir, cell_statuses, E2_BENCHMARK_PATH)` — passing the module-level
constant directly. The Solution above describes the aggregation path only; the fix must cover
`_run_check` as well, or `--check` under `--out` keeps importing the other machine's real-rig row
even after the main path is corrected. There are **two call sites, not one.**

Column-by-column enumeration: `.planning/probes/2026-08-17-phase-23-recon/e4_check_detail.py`.

---

## Resolved — 2026-08-24 (phase 29.1, plan 05)

**Fixed by Phase 23 as FIX-05 / D-09, and left pending afterwards.** This block closes it, but
only after checking every requirement above against the current source of
`experiments/e4_benchmark_grid.py` on `phase/29.1-post-run-fixes` — the tree the new freeze will
carry. A todo left pending after its fix ships is the same defect class this phase exists to end
(29.1-CONTEXT.md D-10), so it is closed on evidence, not on the assumption that FIX-05 covered it.

### The resolver

`resolve_e2_benchmark_path(out_dir) -> tuple[Path | None, str]` at **:261**, three branches at
**:297-308**, verbatim:

```python
out_dir = Path(out_dir)
candidate = out_dir / "benchmark.json"
if candidate.exists():                                    # :299-300  branch 1
    return candidate, "native: resolved relative to --out"
if out_dir.resolve() == E2_BENCHMARK_PATH.parent:         # :301-302  branch 2
    return E2_BENCHMARK_PATH, "default tree: __file__-anchored E2_BENCHMARK_PATH"
return (                                                  # :303-308  branch 3
    None,
    f"absent: no benchmark.json under {out_dir} and --out is not the default "
    f"tree; refusing to import {E2_BENCHMARK_PATH}, which describes a "
    "different machine's run",
)
```

### Requirement-by-requirement, with evidence

| # | requirement (from *Solution* above) | verdict | evidence |
|---|---|---|---|
| 1 | Resolve relative to `--out` first | **HOLDS** | branch 1, `:299-300` — `out_dir / "benchmark.json"` is tried before anything else. |
| 2 | Fall back to the `__file__`-anchored constant **only** when `out_dir` is the default tree | **HOLDS** | branch 2, `:301-302`, gated on `out_dir.resolve() == E2_BENCHMARK_PATH.parent`. |
| 3 | Return nothing rather than importing across machines | **HOLDS** | branch 3, `:303-308` — returns `None`, and the note says so in words: *"refusing to import ..., which describes a different machine's run"*. |
| 4 | Keep the `__file__` anchoring for the default path | **HOLDS** | `E2_BENCHMARK_PATH` at `:256-258` is unchanged, still `Path(__file__).resolve().parents[1] / ...`, with the cwd-relative rationale still on it at `:251-255`. Branch 2 exists *specifically* to preserve it, and the docstring at `:276-282` records that it is kept as an explicit branch even though it is path-equal to branch 1 for the default directory. |
| 5 | Announce the resolved path | **HOLDS, and it is observed firing.** `_run_check`: `logger.info` at `:2101` **and** `print` at `:2102`. `_run_full`: `logger.info` at `:2197`. Measured, not asserted — the 2026-08-20 production run's committed stage log `experiments/run_experiment_suite_state.3ab9c13.stagelogs/e4.log:12` reads: `E2 real-rig record: /home/tlancaster/aquacal-frozen-rerun-freeze-01/experiments/results/benchmark.json (native: resolved relative to --out)`. Branch 1, native, announced in the run's own log. |
| 6 | A missing record produces an **announced null row**, not a silent drop | **HOLDS** | `logger.warning` at `:1579-1583`; the row is then built at `:1607-1619` with `status="failed"`, `status_reason=f"E2 benchmark.json missing or unreadable at {e2_benchmark_path}"` and `record_source="missing_e2_benchmark"`. The row is emitted and marked, never dropped. |
| 7 | **Both** `build_grid_dataframe` call sites go through the resolver | **HOLDS — this is the 2026-08-17 correction, and it is covered.** `_run_check` (`:2060`): resolver at `:2100`, call at `:2114` as `build_grid_dataframe(out_dir, cell_statuses, e2_path)`. `_run_full` (`:2160`): resolver at `:2196`, call at `:2199`, identical form. Verified structurally by AST rather than by grep: exactly two `build_grid_dataframe` calls and exactly two `resolve_e2_benchmark_path` calls exist in the module, and **neither call site passes `E2_BENCHMARK_PATH` as an argument**. |
| 8 | The always-red `--check` contract is settled | **HOLDS, and settled where the todo asked** | `CHECK_EXCLUDED_COLUMNS = ("exit_code", "status_reason")` at `:215`, passed to `compare_experiment_csv` as `exclude_columns` at `:2120`. The exclusion is printed **unconditionally, before the comparison runs**, at `:2106-2113` — pass or fail — with the reason for each column inline (`exit_code`: `_run_check` hardcodes `None` because no subprocess runs under `--check`; `status_reason`: an empty-string-versus-NaN round-trip through CSV). |

Requirement 8 was settled by DRIVER-03's excluded-columns contract, exactly as the 2026-08-17
correction asked ("settle it once, there, and have this fix consume it rather than inventing a
local answer"), not by a local answer here. The comment at `:210-214` records that a third entry
in that tuple would require the same measurement-backed justification rather than being inherited
silently.

The `build_grid_dataframe` docstring at `:1464-1468` now states the contract on the callee side
too: *"Callers should supply the output of the module's `resolve_e2_benchmark_path` resolver rather
than a bare constant (FIX-05, D-09) — `None` means no native record exists for this `out_dir` and
the row is emitted absent-and-marked rather than imported from another tree."* So the requirement
is documented where the next caller will read it, not only where it was fixed.

### Interaction with plan 29.1-06's archive-aside

Plan 29.1-06 moves the 2026-08-20 output tree aside (to `experiments/freeze01_run_output/`) before
the re-run. That **independently defuses the worst case this todo names** — one machine's synthetic
cells silently paired with another machine's real-rig row — because that failure requires a stale
`benchmark.json` to be sitting at the default path in the first place, and after the archive-aside
none is.

**The archive-aside does not replace this fix, and must not be read as covering it.** It is a
property of one particular run's directory layout; the resolver is a property of the code. An
`--out` run on a tree that *does* still hold a default-path record — a developer's working clone, a
partial re-run, any future machine — is protected by branch 3 and by nothing else.

### Verification

```
$PY -c "<AST check>"   # two build_grid_dataframe calls, two resolve_e2_benchmark_path calls,
                       # neither call site passing E2_BENCHMARK_PATH; CHECK_EXCLUDED_COLUMNS present
=> OK
```

No file under `experiments/` or `src/` was modified while closing this — the fix was already in the
tree; this plan only checked it and wrote the evidence down.
