---
created: 2026-08-06T00:00:00.000Z
title: E5's band-mode tests re-run the band once per test; E6 shares one module fixture
area: testing
files:
  - tests/unit/test_e5_band_mode.py
  - tests/unit/test_e6_band_mode.py
---

## Problem

Measured 2026-08-06 with `--durations=40` while triaging CI bloat in phase 19.5.
Two band-mode test files were written to the same plan shape but differ in cost by
3x per test:

| file | slow tests | wall clock | mechanism |
|---|---|---|---|
| `test_e6_band_mode.py` | 6 | **93.89 s total** | one `@pytest.fixture(scope="module")` `band_run_dir`, shared |
| `test_e5_band_mode.py` | 5 | **317 s total** | no shared fixture — each test re-runs the band |

E5's four `TestBandMode` tests cost 71.17 / 69.27 / 69.26 / 69.06 s, which is the
same smoke-scale band run four times over. E6 gets six tests for the price of less
than one of E5's.

## Why it went unnoticed

Both plans passed their own targeted test gate — plan 05 even measured its pair at
393 s and reported it as an anticipated, non-blocking observation. Nothing compared
the two files against each other, because no single executor saw both.

## Solution

Refactor `test_e5_band_mode.py::TestBandMode` onto a `scope="module"` fixture
mirroring `test_e6_band_mode.py:74`. Expected saving ~210 s in the slow lane
(the fast lane is already unaffected — all five are marked `slow` as of this phase).

Low priority: these tests no longer run in PR CI, so the cost lands only on
`slow-tests.yml` and the post-merge gate. Worth doing when E5 is next touched
rather than on its own.

## Related

Same triage added `pytest.mark.slow` to 13 experiment tests across E4/E5/E6,
cutting those four files' fast-lane time from 432.87 s to 5.12 s. The library's
own tests were never the problem — `experiments/` tests had simply never been
routed away from the `-m "not slow"` lane that `test.yml` runs on every push.

## Re-scoped 2026-08-15 — the "when E5 is next touched" condition is now met

The directive above says *"Worth doing when E5 is next touched rather than on its own."* That
condition fires in the fix milestone: `2026-08-15-degeneracy-counter-is-unobservable-and-merges-two-failure-kinds.md`
names `experiments/e5_index_sensitivity.py` as one of its edit targets, and its T-14 half adds a
persisted degeneracy column to E5's band output — which means `test_e5_band_mode.py` is being
opened anyway.

**Do it in the same change.** The ~210 s saving in the slow lane is incidental; the real reason is
that the band-mode tests will need updating for the new column regardless, and refactoring five
tests onto a `scope="module"` fixture while already editing them is free. Doing it later means
opening the same file twice.

Still **not** a reason to hold the re-run: this is test-time only and changes no artifact.
