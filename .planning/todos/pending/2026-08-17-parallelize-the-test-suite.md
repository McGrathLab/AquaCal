---
created: 2026-08-17
type: tooling
priority: high
blocks_phase_start: true
---

# Parallelize the test suite before starting the next phase

`pytest-xdist` is **not installed** and there is no `addopts` in `pyproject.toml`, so
`pytest tests/` has always run serially. Two full-suite gate runs during Phase 24 measured
**1:16:27** and **1:09:56** for 1956 tests. Every post-merge gate pays that in full, and it
is the single largest source of orchestrator wall-clock in a phase.

## What to do

```bash
pip install pytest-xdist
python -m pytest tests/ -n auto --dist loadfile
```

Then, if it holds up, persist it in `pyproject.toml` so it is the default.

## Why `--dist loadfile`, not bare `-n auto`

Checked during Phase 24:

- **20 cores** available.
- **No session-scoped fixtures anywhere in `tests/`** — nothing globally shared to corrupt.
- **Two module-scoped fixtures**: `tests/unit/test_e5_band_mode.py` and
  `tests/unit/test_e6_band_mode.py`. Bare `--dist load` scatters a file's tests across
  workers and would re-run those expensive fixtures per worker, erasing the gain.
  `--dist loadfile` pins each file to one worker and preserves module scope exactly.

## Expected ceiling

Wall-clock floors at the slowest single *file*, not the slowest test. The band-mode files
each run full smoke calibrations, so profile with `--durations=25` on the first parallel run
to find which file sets the floor. If one file dominates, splitting it is the next lever.

## Caveats to check on the first parallel run

- Tests that write to shared paths under `experiments/` or a fixed output dir will collide
  under parallelism even with `loadfile`, if two *different* files target the same path.
  A first run that fails in artifact-writing tests is this, not a real regression.
- Confirm the parallel run reproduces `1931 passed, 25 skipped` before trusting it as a gate.

## Provenance

Raised by the user during Phase 24 execution, 2026-08-17, after the second gate run appeared
to stall. It had not in fact regressed — the run was passing through one slow block — but the
underlying point stands: the gate is serial and does not need to be.
