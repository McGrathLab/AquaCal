---
created: 2026-08-26T00:00:00.000Z
title: POST-SUBMISSION — D4's three exact-equality anchors were captured on Windows and fail on Linux; decide what an anchor means across platforms
area: testing
resolves_phase: 30
files:
  - tests/unit/test_discard_accounting.py
  - tests/unit/test_optim_common.py
  - tests/unit/test_pipeline.py
---

## Why this is filed rather than fixed

**D-29-14:** anything neither assertion-wrong nor cheaply fixable becomes a post-submission todo
naming what fails and what would fix it, rather than being forced.

These three are **already RULED** — in the `rerun-freeze-02` annotated tag's own message and in
`.planning/phases/29.1-post-run-fixes-re-freeze/29.1-PREPUSH-AUDIT.md` §1 — and **D-29-15 names
three as the expected count: zero and four are both anomalies.** Repairing them inside Phase 29
would have been precisely the over-correction that decision exists to forbid.

## What fails

`pytest tests/` reports `3 failed, 2394 passed, 21 skipped`. The three, by node id:

- `tests/unit/test_discard_accounting.py::test_matches_frozen_anchor`
- `tests/unit/test_optim_common.py::TestPerObservationDetailSinks::test_detail_sink_recomputed_geometry_matches_projector`
- `tests/unit/test_pipeline.py::TestSolverConfigSeedIsInert::test_matches_pre_change_anchor`

All three assert **exact floating-point equality** against anchors captured on Windows. The run
that matters was executed on Linux. Nothing about the solve is wrong; the assertions encode a
platform.

This count is stable and expected. It did not change across Phase 29's repairs: `29-rails-before.txt`
records the same three node ids failing before plan 29-06 touched anything, and `29-rails-after.txt`
records them still failing afterwards — character for character the same ids.

## What would fix it

Either, and it is a decision rather than a repair:

1. **Re-capture the three anchors on Linux.** Cheap mechanically, but it discards the cross-platform
   information the current failure carries — after this, a genuine Windows regression would go
   unnoticed.
2. **Convert the three exact-equality assertions to a documented ULP-scale comparison**, with the
   cross-platform reason stated *at the constant*, not in a commit message. This keeps the anchor
   meaningful on both platforms and makes the tolerance auditable.

Option 2 is the better shape for the same reason the manifest todo prefers *promote* over *add
alongside*: it makes the assertion state what is actually true, rather than pinning it to one
variant and hoping nobody runs the other.

**Whichever is chosen, do not `skip`, `xfail` or `--deselect` them.** Phase 29 repaired eight rail
failures without silencing a single one (D-29-13), and the value of "three is the expected count"
comes entirely from the three being *visible*.

## Evidence

- `.planning/phases/29-gate-verification-results-commit/29-rails-after.txt` § 7, RESIDUAL 1
- `.planning/phases/29-gate-verification-results-commit/29-PHASE-RECORD.md` § *Test and gate state*
  and § *Open items handed forward*, item 10
- `.planning/phases/29.1-post-run-fixes-re-freeze/29.1-PREPUSH-AUDIT.md` §1 — the D4 ruling
- the `rerun-freeze-02` annotated tag message
