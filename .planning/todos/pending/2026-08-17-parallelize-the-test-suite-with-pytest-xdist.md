---
created: 2026-08-17T16:40:00.000Z
title: Parallelize the test suite with pytest-xdist
area: tooling
files:
  - pyproject.toml
---

## Problem

The full suite runs single-threaded on a 20-logical-core machine. Measured
2026-08-17 at the Phase 23 post-merge gate: **1865 passed, 25 skipped, 0 failed
in 4182 s (1:09:42)** at merge commit `330f9ef`. `pytest-xdist` is not installed
(only `coverage` / `pytest-cov` are present, and no `addopts` enables coverage by
default, so that is not the overhead).

This is **not** a dev-loop problem. Project policy already restricts the full
suite to the wave-merge gate — executors run targeted files only (CLAUDE.md
§ "Never let a subagent background a long run and return"). The cost is a
blocking ~70-minute gate, once or twice per phase.

The reason it is worth doing anyway is arithmetic: Phases 24, 25, 26 plus the
Phase 27 freeze imply roughly 4-6 more full-suite runs before Phase 28. At
60-90 minutes each that is 4-9 hours of wall clock still ahead.

## Solution

Install `pytest-xdist`; run the gate as `-n 12 --dist loadfile`.

`--dist loadfile` keeps all tests in a file on one worker, preserving any
within-file ordering assumptions. The cost is that the longest single *file*
becomes the floor.

Parallel-safety was surveyed 2026-08-17 and looks favourable:

- 33 test files use `tmp_path`/`tmpdir` — properly isolated
- only **1** session/module-scoped fixture in the whole tree
- the 2 files that `chdir` (`test_datasets.py`, `test_experiments_e5.py`) are
  safe under xdist: workers are separate processes, so `chdir` is process-local
- **the one thing to verify:** ~10 files reference `experiments/results`
  (`test_e1_band_mode.py`, `test_e5_band_mode.py`, `test_e6_band_mode.py`,
  `test_e7_band_mode.py`, `test_experiments_e4.py`, `test_experiments_e5.py`,
  `test_experiments_io.py`, `test_experiments_provenance.py`,
  `test_fd_accuracy.py`, `test_reconstruction_bootstrap.py`). If those are
  read-only assertions against committed artifacts they are safe as-is; any that
  *write* need `tmp_path` or serialization.

Add `--durations=25` on the first parallel run — it yields the speedup and the
profile in one pass. Optimization suites usually have 2-3 tests running real
bundle adjustments that dominate; if the top 3 are most of the wall clock, xdist
will not fix the tail and those tests need attention specifically.

## Sequencing — do NOT land this during a correctness gate

Parallelizing changes execution order and process isolation, which can surface
latent test interdependencies as brand-new failures. If that happens during a
wave-merge gate, a red test is ambiguous between real cross-plan breakage and an
xdist artifact, and disentangling it costs more than the hours saved.

Correct order:

1. **Baseline exists already:** 1865 passed / 25 skipped / 0 failed at `330f9ef`
   (2026-08-17). Compare against exactly this.
2. Install xdist and re-run against the same tree. **The bar is reproducing the
   identical pass/fail set**, not merely being faster. This is also what flushes
   out whichever `experiments/results` file actually writes.
3. From Phase 24's gate onward, every run is cheap.

## Scope note

This is dev infrastructure, deliberately **not** a milestone requirement and not
in the roadmap. It changes only how fast the tests get there, never what the
suite measures, records, or can claim — so by the milestone's own scope test
(REQUIREMENTS.md, author 2026-08-15) it does not belong in v2.1's requirement
set. It touches no library code and cannot affect the frozen sha's behaviour,
which is why it is safe to do mid-milestone unlike the deferred solver
performance work in
[2026-07-23-reduce-memory-and-cpu-load-during-calibration].

Do not pursue speed by loosening solver tolerances or capping iterations in
tests. This library's value is numerical correctness, bit-identity gates here are
already known to be conditioning-dependent, and Phase 23 (FIX-05) has just spent
a task fixing a verification gate that could not fail — a suite that is fast
because it stopped checking convergence is the same failure mode wearing
different clothes.
