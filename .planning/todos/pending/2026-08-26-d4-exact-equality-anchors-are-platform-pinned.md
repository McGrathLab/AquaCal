---
created: 2026-08-26T00:00:00.000Z
title: POST-SUBMISSION — D4's two remaining exact-equality anchors were captured on Windows and fail on Linux; decide what an anchor means across platforms
area: testing
resolves_phase: 30
files:
  - tests/unit/test_discard_accounting.py
  - tests/unit/test_pipeline.py
---

## Why this is filed rather than fixed

**D-29-14:** anything neither assertion-wrong nor cheaply fixable becomes a post-submission todo
naming what fails and what would fix it, rather than being forced.

These three are **already RULED** — in the `rerun-freeze-02` annotated tag's own message and in
`.planning/phases/29.1-post-run-fixes-re-freeze/29.1-PREPUSH-AUDIT.md` §1 — and **D-29-15 names
three as the expected count: zero and four are both anomalies.** Repairing them inside Phase 29
would have been precisely the over-correction that decision exists to forbid.

*Amended 2026-08-26: one of the three left this set in Phase 29.2 — see § Why this names two and
not three. The paragraph above is left exactly as written, describing the state at filing.*

## What fails

`pytest tests/` reports `2 failed, 2395 passed, 21 skipped` — measured 2026-08-26 at commit
`3026813` and recorded verbatim in
`.planning/phases/29.2-merge-release-and-publish/29.2-smoke-runs.txt` § 4, which is where this
count comes from rather than from memory. The two, by node id:

- `tests/unit/test_discard_accounting.py::test_matches_frozen_anchor`
- `tests/unit/test_pipeline.py::TestSolverConfigSeedIsInert::test_matches_pre_change_anchor`

Both assert **exact floating-point equality** against anchors they read as constants from
`tests/fixtures/`, captured on Windows. The run that matters was executed on Linux. Nothing about
the solve is wrong; the assertions encode a platform. Both are `@pytest.mark.slow`, so neither is
in the `pytest -m "not slow"` selection CI's `test` job runs — a failure here is not a red check on
a pull request, which is why deferring them stays affordable.

This count was three until Phase 29.2 and is stable at two now. It did not change across Phase 29's
repairs: `29-rails-before.txt` records the same node ids failing before plan 29-06 touched
anything, and `29-rails-after.txt` records them still failing afterwards — character for character
the same ids.

**Two is now the expected count; zero and three are both anomalies.** A zero would mean these two
had been silenced. A three would mean something new had broken, or that Phase 29.2's conversion had
been reverted.

## Why this names two and not three: the third left the set

**What was done.** `tests/unit/test_optim_common.py::TestPerObservationDetailSinks::test_detail_sink_recomputed_geometry_matches_projector`
was repaired in Phase 29.2 (plan 29.2-03, commit `3026813`). Two of its four assertions — `r_q_m`
and `chord_incidence_deg` — became documented bounds expressed as a hard count of representable
steps (`np.testing.assert_array_max_ulp`, `maxulp=4` and `maxulp=8`, four times the measured worst
cases of 1 and 2), with the reason written at the assertion. The other two, `h_c_m` and `h_q_m`,
measured zero mismatches across all 22 rows and keep exact equality. The node now reports
`1 passed`. It left this set by passing, not by being suppressed.

**Why its framing in _this document_ was wrong.** That member has no captured anchor at all. It
recomputes the geometry inline from the library's own formulas and compares the result against the
per-observation sink, so its disagreement was never between a Windows-captured constant and a Linux
run. It was between the library's **vectorized** evaluation of `r_q = np.sqrt(dx*dx + dy*dy)` over
N points (`src/aquacal/core/refractive_geometry.py:676`) and the test's **scalar** evaluation of the
same formula on one element — numpy's array and scalar paths, **on the same machine**, differing by
one representable step. It was invisible on Windows only because that numpy build dispatched
differently. The cross-platform-anchor question this todo exists to answer genuinely does not arise
for it.

That is a correction of **this document**, not a defect of the phase that wrote it. From the failure
list alone — three exact-equality assertions, all green on Windows, all red on Linux — the
classification was the reasonable one. It took instrumenting all 22 rows to see that one of the
three was a different phenomenon wearing the same symptom.

**Why the other two are different and stay.** Both `test_matches_frozen_anchor` and
`test_matches_pre_change_anchor` genuinely do read captured constants from the fixtures tree, and
both are `@pytest.mark.slow`. For them the question of what an anchor means across platforms is
live and unanswered, and answering it is a decision about the scientific record rather than a
repair. They stay here and `resolves_phase` stays at 30.

**Where the superseding statement lives.** The `rerun-freeze-02` annotated tag message and
`.planning/phases/29.1-post-run-fixes-re-freeze/29.1-PREPUSH-AUDIT.md` §1 both still say three, and
both are left exactly as written — readable as what was true when they were written, the same
reasoning that declined to edit MF-12 in place. Nothing prior was rewritten to agree with the new
count. The statement that supersedes them belongs in Phase 29.2's own record,
`29.2-PHASE-RECORD.md`, which plan **29.2-08** owns.

## What would fix it

Either, and it is a decision rather than a repair:

1. **Re-capture the two anchors on Linux.** Cheap mechanically, but it discards the cross-platform
   information the current failure carries — after this, a genuine Windows regression would go
   unnoticed.
2. **Convert the two exact-equality assertions to a documented ULP-scale comparison**, with the
   cross-platform reason stated *at the constant*, not in a commit message. This keeps the anchor
   meaningful on both platforms and makes the tolerance auditable.

Option 2 has now been exercised once, on the member that left this set — see the docstring of
`test_detail_sink_recomputed_geometry_matches_projector` for the shape a documented step bound takes
in this codebase. That is a worked example of the *mechanism*, **not** a precedent for the
*decision*: that member's gap was a same-machine dispatch asymmetry, whereas these two carry a
genuine cross-platform question, and a bound wide enough to cover an unknown platform difference is
a different and much harder number to justify.

Option 2 is the better shape for the same reason the manifest todo prefers *promote* over *add
alongside*: it makes the assertion state what is actually true, rather than pinning it to one
variant and hoping nobody runs the other.

**Whichever is chosen, do not `skip`, `xfail` or `--deselect` them.** Phase 29 repaired eight rail
failures without silencing a single one (D-29-13), and the value of "two is the expected count"
comes entirely from the two being *visible*. (Unchanged in substance; only the number it quotes
moved from three to two. Phase 29.2 honoured it — the member that left did so by passing.)

## Evidence

- `.planning/phases/29-gate-verification-results-commit/29-rails-after.txt` § 7, RESIDUAL 1
- `.planning/phases/29-gate-verification-results-commit/29-PHASE-RECORD.md` § *Test and gate state*
  and § *Open items handed forward*, item 10
- `.planning/phases/29.1-post-run-fixes-re-freeze/29.1-PREPUSH-AUDIT.md` §1 — the D4 ruling
- the `rerun-freeze-02` annotated tag message
- `.planning/phases/29.2-merge-release-and-publish/29.2-smoke-runs.txt` §§ 1, 2 and 4 — the measured
  two-failure count, the superseded invariant, and both remaining node ids as the suite reported them
