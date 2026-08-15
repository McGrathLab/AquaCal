---
created: 2026-08-13T00:00:00.000Z
title: E4's aggregator hardcodes E2_BENCHMARK_PATH, so the real-rig row is dropped under --out
area: experiments
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
