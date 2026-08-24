---
gsd_state_version: 1.0
milestone: v2.1
milestone_name: Clean Experimental Suite
current_phase: 29.1
current_phase_name: post-run-fixes-re-freeze
status: executing
stopped_at: Completed 29.1-07-PLAN.md (verification bar re-run; bar NOT fully cleared -- D4 blocking); next is 29.1-08 (tag)
last_updated: "2026-08-24T17:06:18.295Z"
last_activity: 2026-08-20
last_activity_desc: "Phase 29.1 planned: 9 plans / 6 waves, plan-checker PASS; criterion 7 folded in"
progress:
  total_phases: 9
  completed_phases: 5
  total_plans: 50
  completed_plans: 49
  percent: 56
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-08-15)

**Core value:** Accurate refractive camera calibration from standard ChArUco board
observations — researchers can `pip install aquacal`, point it at their videos, and get a
calibration result they trust.

**Current focus:** Phase 29.1 — post-run-fixes-re-freeze
experiment-suite fix that changes what the suite measures, records, or can claim; freeze one sha;
hand a complete full-suite driver to a larger Linux machine for the run; reconcile the returned
single-version results. **E2 is in the re-run.** Phases 23-30, all 23 requirements mapped 1:1
into eight phases with 100% coverage validated. Next: `/gsd:plan-phase 23`.

## Current Position

Phase: 29.1 (post-run-fixes-re-freeze) — EXECUTING
Phase 29 (gate-verification-results-commit) — PARTIAL. Phase 28's run FINISHED on the Linux machine.
Plan: 8 of 9
Previous phase: 27 — COMPLETE (13/13), closed at rerun-freeze-01 / 3ab9c13
Status: Ready to execute
7 N/A, 2 FAIL); output preserved to ~/rerun-freeze-01-output.tar.gz (31 MB, 507 files, sha256 in
.planning/phases/28-full-suite-production-run/); results committed and pushed on branch
`results/rerun-freeze-01`; E2 sanity control PASSES (seed 42 reproduces real_rig_metrics.json
within rtol=1e-6). OPEN: the E7 before/after comparison (success criterion 3) and the Zenodo
results package (RUN-05) — the latter deliberately deferred until after 29.1's re-freeze and
re-run, so the archive is built from clean output.
NEXT: /gsd-plan-phase 29.1
Last activity: 2026-08-20 — Phase 29.1 execution started

Phase 27 discussion found a blocking driver defect and reopened two Phase 26 deferrals:
`_preflight_frameset` uses `p.is_file()`, so the target's IMAGE set reads as ABSENT and would
force `--skip-e2` (synthetic-only). Also in scope now: `is_stage_complete` ignoring the exit-code
column on resume, and `reconstruction_bootstrap.py:56`'s hardcoded output path. Smoke is being made
truthful so it can exit 0, because on-target smoke is the chosen verification venue. See
`.planning/phases/27-frozen-single-sha-handoff-package/27-CONTEXT.md`.

Phase 26 closed at sha `88512b7`. Plans 26-01..26-09 delivered the driver, manifest, gates and
archive-aside; 26-11 added the reduced-scale path; 26-10 recorded the D-33 form-1 acceptance pass.
Three gap-closure plans came out of that pass and are the reason the phase ran to 14:

- **26-12** — `e3` was scheduled five stages before `e2_production` wrote the record it reads, and
  crashed stage 3 on `int(NaN)`. Dependency edge + a non-numeric marker for the absent-record case.

- **26-13** — E1's and E7's benchmark records carried no seed, so `gate3_provenance` failed on six
  artifacts unconditionally, which would have made Phase 29's RUN-03 unsatisfiable.

- **26-14** — the committed-baseline test rails were pinned to the archive by 26-01 and would have
  passed green against history once Phase 28 repopulated `experiments/results/`.

Full suite green at close: **2190 passed, 25 skipped, 0 failed** (1:08:55).

### Open, deliberately, at close

1. The `smoke` profile expects three artifacts the smoke code paths never write
   (`structural_scaling.csv`, `e5_provenance.json`, `fd_jacobian_accuracy.json`), so a smoke pass
   can never exit 0. Diagnosed in 26-10-SUMMARY; not a driver defect.

2. Automatic resume skips a stage that ran AND FAILED — `is_stage_complete`
   (`run_experiment_suite.sh:669`) matches a completion line and ignores the exit-code column. The
   end-of-run roll-up still catches the missing artifact. User deferred this 2026-08-18.

3. `reconstruction_bootstrap.py:56` hardcodes `experiments/results/real_rig_metrics.json` instead
   of `--out`; smoke-only, correct in production.

## Roadmap Summary (v2.1)

Eight phases, phase numbering continues from 23. Full detail in `.planning/ROADMAP.md` §
Phase Details.

| Phase | Goal | Requirements |
|-------|------|--------------|
| 23. Experiment Correctness Fixes | E1/E6/E7/E4/E2/synthetic outputs are numerically and textually correct | FIX-01..06 |
| 24. Degeneracy Instrumentation | The degeneracy counter reaches artifacts, split by kind and stage, warning narrowed | DEGEN-01..03 |
| 25. Degeneracy Classification & Claim Licensing | The 198 unprojectable observations classified; E1's noise_std axis added | DEGEN-04, BAND-01 |
| 26. Full-Suite Driver & Handoff Readiness | One driver covers every invocation, one manifest, decided `--check`, stale outputs moved aside | DRIVER-01..04 |
| 27. Frozen Single-Sha Handoff Package | Code, driver, gates, environment requirements frozen and verified portable | RUN-01 |
| 28. Suite Execution on Linux Machine | Full suite — E1-E7, band runs, E2 — executes once at the frozen sha | RUN-02 |
| 29. Gate Verification & Results Commit | Gates pass, E2 sanity control and E7 before/after clear, results committed, Zenodo results package published pre-submission | RUN-03, RUN-04, RUN-05 |
| 30. Post-Submission Reconciliation | §3/tutorial re-cut against the archive, stale outputs purged, MF-19 closed | POST-01, POST-03, POST-04 |

**Sequencing constraints honored:** all FIX/DEGEN/DRIVER/BAND phases (23-26) land before the RUN
phases (27-29); RUN-01 (freeze) precedes RUN-02 (execute, on the Linux machine) precedes RUN-03/04
(gate + commit); DRIVER-04 (move stale outputs aside) lands in Phase 26, before Phase 28's
execution; Phase 30 (POST) is gated on both Phase 29 and the 2026-08-21 SoftwareX submission.

**Revised 2026-08-15 after external roadmap review** (four findings taken, one re-scoped):
Phase 26 now depends on Phase 25 (DEGEN-04 emits a per-observation table and needs a driver-passed
E2 `h_q` flag); Phase 27 gained a pre-freeze gate that every §3-facing number has a generating
emitter, since that is unfixable after the freeze; Phase 29 gained the E2 sanity control (E2's
schema does not change, so it should reproduce to ~1e-8 — and because DEGEN-02 touches
`_optim_common.py`, that check is also what proves the instrumentation did not perturb the solve)
and an explicit E7 before/after comparison (FIX-02's two extra free parameters could soften a
published 10-of-10 result); and POST-02 was re-timed to RUN-05 in Phase 29, because the paper
cannot be submitted citing an archive that contradicts its own §3.

**Revised 2026-08-17 after pre-planning recon on Phase 23** (read-only measurement, no source
changed). Four corrections landed in ROADMAP.md, REQUIREMENTS.md and the todos:

1. **FIX-01's acceptance criterion was vacuous and is now the recovered `water_z` against ground
   truth 1.031 m.** Measured: FIX-02 alone drives E1's guard count 14,949 → 0 with `water_z` at
   0.0120 m, at a cost identical to the unpinned solve to 10 significant figures. A criterion
   phrased on the count passes whether or not the pin exists. FIX-01 now lands **before** FIX-02
   in the non-refractive arm, and the combined pinned/normal-free configuration — the one the
   re-run executes — is still unmeasured and must be emitted first.

2. **E4's `--check` is structurally always-red** on `exit_code` and `status_reason` while its 33
   metric columns reproduce to 1e-6, so it cannot verify FIX-05; and `_run_check` is itself on the
   defective path (**two** call sites). DRIVER-03 must settle the contract early — Phase 23
   consumes it.

3. **FIX-06 is four code sites, not three**, the unfiled one being `e2_real_rig.py:555-563`'s
   "60 → 12 → 1,817" against the verified 262 → 52 → 7,762.
   `19.1-E2-FRAMESET-PROVENANCE.md` gets a supersession header, not an edit.

4. **Phase 29's E2 sanity control is same-seed only** — 3.07e-09 across platforms at seed 42, but
   a 0.761→0.910 px band across seeds.

Also narrowed: DEGEN-01 (E6's band already persists the counter; the gap is E5/E1/E7), and FIX-03
(the layout axis already runs all six seeds — MF-12's hand analysis was seed-43-only, not the
sweep; the reproducible difference is 0.3592 mm, not 0.3600). **Phase 23's "six independent
single-file fixes" framing does not survive:** three of the six interact. The phase boundary is
unchanged, the plan decomposition is not six-way parallel.

**Coverage:** 23/23 v2.1 requirement IDs mapped to exactly one phase, no orphans. (The milestone
brief's "19 todos" is the pending-todo backlog file count; the discrete requirement IDs derived
from those todos number 23 — see REQUIREMENTS.md § Traceability for the note.)

## Deferred Items

Acknowledged and deferred at milestone close on 2026-08-15. These are inputs to the next
milestone, not losses.

| Category | Item | Status |
|----------|------|--------|
| debug | e6-seed-locked-clearance-floor | diagnosed (fix landed via Phase 19.4; session never formally closed) |
| debug | stage3-diverges-new-geometry | awaiting_human_verify |
| quick_task | 1-add-calibration-file-based-synthetic-rig | no SUMMARY on disk |
| quick_task | 2-add-explicit-reject-outlier-frames-param | no SUMMARY on disk |
| quick_task | 3-use-a-structural-column-grouping-for-the | no SUMMARY on disk |
| quick_task | 260807-dcv-e1-e7-band-provenance-emit-z-rmse-column | no SUMMARY on disk |
| quick_task | 260813-clj-land-four-pre-run-todo-fixes-provenance- | no SUMMARY on disk |
| todo | 15 pending todos in `.planning/todos/pending/` | discharged into v2.1 requirements above (23 IDs); see ROADMAP.md and REQUIREMENTS.md |
| verification_gap | Phase 04 (`04-VERIFICATION.md`) | gaps_found |
| verification_gap | Phase 10 (`10-VERIFICATION.md`) | human_needed |
| verification_gap | Phase 19.2 (`19.2-VERIFICATION.md`) | human_needed |
| requirement | INDEX-01, INDEX-02, INDEX-03 | Phase 20, deferred on MF-13; not part of v2.1 |
| requirement | DOCS-07 | Phase 22, manuscript-side; not part of v2.1 |

**Three todos were verified complete against the tree and closed 2026-08-15** (`d5eba65`) — the
Zenodo dataset upload, the OpenCV pin (landed tighter, as `==4.13.*`), and the band-sidecar
collision (band-owned `e{1,5,6,7}_seed_band_provenance.json`). Each carries a `## Resolved` block
in `.planning/todos/done/` naming the evidence.

**A fourth was closed by author decision the same day:**
`2026-08-05-verify-non-refractive-baseline-supports-paper-claims`. Its titled question is settled
by MF-18 (at unit index the refractive projector *is* the pinhole projector, so the baseline is
converged and `main.tex:268`'s "sole experimental variable" framing stands). Its two residual
steps have owners: step 2 → DEGEN-01 (Phase 24), and step 3 → FIX-01 (Phase 23), which is the
same experiment with a better rationale and has **already been measured** (guard count 14,949 →
0, optimality 9e+02 → 5e-01, reconstruction numbers reproduced to ~4 significant figures).

**The misleading degeneracy now has a root cause and a fix.** `water_z` is an **exact null
direction** in the `n_water = 1.0` arm — cost constant to 13 significant figures over a 1.5 m
sweep while the guard count climbs to 14,949. The solver is estimating a parameter that provably
cannot influence the fit. FIX-01 (Phase 23) pins it, arm-locally, and explicitly overrides the
HANDOFF deferral gate: the author decided 2026-08-15 that it lands **before** the 2026-08-21
submission, because the shift is −0.019% against a manuscript that quotes 2–3 significant
figures. **Do not pin `water_z` in the refractive arm** — there it is genuinely observable, and
pinning inflates the headline ratio to a flattering 168×.

## Accumulated Context

### Roadmap Evolution

v2.0 inserted five decimal phases mid-milestone, each because the previous one exposed the next
defect. Full narrative in `.planning/milestones/v2.0-ROADMAP.md` § Milestone Summary and in
`.planning/RETROSPECTIVE.md`. Not duplicated here.

v2.1's roadmap (2026-08-15) was planned as a straight-line eight-phase sequence: fixes and
instrumentation (23-26) → freeze (27) → execute off-repo (28) → gate and commit (29) → reconcile
after submission (30). It was expected to insert no siblings, on the reasoning that the code-side
work was fully scoped by 19 already-filed todos rather than discovered mid-run.

**That held until the run itself.** Phase 28's execution surfaced four defects no todo predicted —
two of them the roll-up's only real FAILs — so 29.1 was inserted on 2026-08-20. The reasoning was
sound for code-side work and did not extend to what executing the suite end to end would reveal.

- Phase 29.1 inserted after Phase 29: Post-Run Fixes & Re-Freeze -- four defects from the 2026-08-20 production run, the deferred install-extras documentation fix, and a new frozen tag (URGENT)

### Decisions

Logged in PROJECT.md § Key Decisions. The load-bearing one from v2.0: **D-19.3-17 — an
experiment may carry an accuracy claim only where a measured seed band supports it.** BAND-01
(Phase 25) applies this to E1's noise axis.

- [Phase 29.1]: Phase 29.1 work happens on branch phase/29.1-post-run-fixes, based on results/rerun-freeze-01 (D-13). Merge it back; never check out around it, or the 147 tracked files under experiments/results/ leave the tree.
- [Phase 29.1]: E4 gate 1 exempts record_source="pipeline" rows inside the existing gate rather than gaining a second gate id, because the roll-up PASS/N/A/FAIL totals are an audited number (D-02). The exemption is keyed to row kind, never to a count magnitude, so synthetic (assembled) rows are gated exactly as before.
- [Phase 29.1]: E4 real-rig row publishes the guard count E2 measured (198 above-water board corners) and is exempt from the > 0 status downgrade at both the writer and the gate (D-01). Reverting means re-nulling a number the manuscript may cite.
- [Phase 29.1]: D-04 resolved by removal: the 2026-08-15 design table has --seeds sidecar rows for E5 and E7 and deliberately none for E1, so the expectation was unclaimed rather than a writer added
- [Phase 29.1]: D-07 resolved in favour of the :1209 comment: band mode may CREATE e1_benchmark_<model>.json and never overwrites it, enforced by a literal force=False that ignores the run's --force
- [Phase 29.1]: D-08 fixed as a class not an instance: e1_seed_band_provenance.json's scope field is derived at write time rather than re-frozen at four seeds and 256/384 rows (D-10)
- [Phase 29.1]: E7's identical band-overwrite hazard is filed as a pending todo, not fixed: it surfaced by reading rather than by a failing gate and is out of this phase's scope
- [Phase 29.1]: Plan 29.1-04: took todo option 1 (doc-only) in full — HANDOFF §1.2 now installs ".[dev,bench]"; options 2 (move DECLARED_CONSTANTS out of the test module) and 3 (promote psutil to runtime) left explicitly open because both touch src/ and need the suite re-run behind them (D-11).
- [Phase 29.1]: Plan 29.1-04: `pip install -e . --no-deps` metadata-refresh sites must NOT gain extras — five sites ruled 'correct as-is — not a first install'; adding extras would change what the command does.
- [Phase 29.1]: Plan 29.1-04: install-instruction correctness is verified by building an environment from the command read out of HANDOFF.md, not by diffing the string — aquacal-freeze02-cleanenv left in place for plan 29.1-07.
- [Phase 29.1]: Plan 29.1-05: The 198 unprojectable observations are settled as above-water board corners in MANUSCRIPT-FINDINGS.md MF-24, by citation of the committed 198-row per-observation table rather than by inference from summary counts
- [Phase 29.1]: Plan 29.1-05: The degeneracy count is seed-sensitive (198/210/183 across band seeds 42/43/44) while the cause decomposition is not -- 198 must be attributed to seed 42 in the manuscript, not presented as a dataset constant
- [Phase 29.1]: Plan 29.1-05: The E4 aggregator path defect (E2_BENCHMARK_PATH not following --out) is confirmed fixed by Phase 23's FIX-05/D-09 at BOTH build_grid_dataframe call sites, verified by AST and by the run's own e4.log:12 announcement
- [Phase ?]: 29.1-03: the stale-string sweep's enumeration command was widened mid-pass after its own blind spot was found by hand -- a pre-filter for comment/string lines silently dropped wrapped docstring lines, one of which was a defect. A boundary with a blind spot is not a boundary.
- [Phase ?]: 29.1-03: retired measurements are retained under an explicit owner, never scrubbed and never swapped for the current value -- MF-12's digits stay in e6 under its name, because a corrected literal reproduces the defect one run later.
- [Phase ?]: 29.1-03: two twin sites outside D-09's bound (_expectations.py, check_rerun_gates.py) were corrected rather than only recorded; the sweep did not widen but a twin of a corrected claim is the partial-fix shape the gate module exists to catch.
- [Phase ?]: 29.1-09: mechanism A of D-18's three -- correct the manifest dir and evaluate the predicate; the only candidate keeping src/ untouched, moving no published artifact, creating no second copy of a measurement and avoiding the 10.9 MB hazard
- [Phase ?]: 29.1-09: an absent conditional artifact scores PASS only on a machine-evaluated predicate; an unevaluable predicate is N/A, never PASS, and a misplaced artifact is a FAIL naming both paths
- [Phase ?]: 29.1-09: the predicate asks whether the flagged count is non-zero, never whether it is 198 -- MF-24 measured that count to be seed- and OpenCV-sensitive
- [Phase ?]: 29.1-09: the misplacement search set is bounded to directories the manifest declares, with the bound stated in the docstring rather than closed by a filesystem walk
- [Phase ?]: 29.1-06: the 2026-08-20 run output is archived at experiments/freeze01_run_output/ -- named for the tag whose run produced it, so two archives stay distinguishable. 499 files moved, 0 deleted.
- [Phase ?]: 29.1-06: experiments/results/ must be EMPTY at tag time -- D-24's pre-flight refuses a non-empty OUT_DIR, and 'everything here was produced by this run' is only true if it starts empty. Never --allow-nonempty-out.
- [Phase ?]: 29.1-06: suite_expectations.json's two conditional entries deliberately did NOT follow the move -- they describe where a fresh run writes. Proved: archive gates PASS/PASS, emptied tree gates N/A/N/A.
- [Phase ?]: 29.1-06: _baseline_paths.ARCHIVE still points at pre_rerun_baseline/ -- its subject is six Phase-19.1 seedless records that live there. No code changed; the live-or-archive rule repointed the rails by itself.
- [Phase ?]: 29.1-07: the verification bar is recorded as NOT cleared -- the full suite reports 3 failures on Linux against attempt 1's 0, and nothing was deselected, xfailed or loosened to reach green
- [Phase ?]: 29.1-07: the three failures are pre-existing exact-equality anchor misses (1 ULP to 1.4e-9), proven by byte-identity of every input to rerun-freeze-01; they are the first Linux evaluation of anchors captured on Windows
- [Phase ?]: 29.1-07: the --smoke roll-up matches attempt 1 at 72 PASS / 18 N/A / 0 FAIL once the empty experiments/results_e2_band/ left by 29.1-06's git mv is removed; both the 72/17/2 and 72/18/0 runs are reported

### Blockers/Concerns

- **MF-19** — §3's numbers predate the current library. This is the manuscript-level blocker and
  the direct reason v2.1 ends in a single-version suite re-run (Phases 27-29), closed out in
  Phase 30.

- **The DOI freezes the reference numbers.** Section 3, the archive's `reference_outputs/`, and
  the tutorial's expected-value table are a matched set of three. Phase 28 re-runs E2 by design,
  so Phase 30 (POST-01) must re-cut all three together against the new numbers before another
  Zenodo version is cut.

- 8 pre-existing failures in tests/unit/test_experiments_provenance.py (not caused by 29.1-01; verified at branch base). They will meet the D-14 full-suite bar in plan 29.1-08 -- resolve there or rule expected-by-construction. Details: .planning/phases/29.1-post-run-fixes-re-freeze/deferred-items.md
- 29.1-08 BLOCKING (deferred-items D4): three exact-equality anchor tests fail on the Linux run machine, so D-14's full-suite bar is not met. 29.1-08 must resolve them or record an explicit ruling in 29.1-PREPUSH-AUDIT.md; it must not record 'full test suite: 0 failed'.

## Session Continuity

**Resume file:** None

Last session: 2026-08-24T17:06:18.283Z
(`870151c`), then `/gsd-discuss-phase 23` captured 14 decisions across four gray areas
(`6a0b772`). One new POST-SUBMISSION todo filed: the hardcoded `water_z` optimization bound.
Stopped at: Completed 29.1-07-PLAN.md (verification bar re-run; bar NOT fully cleared -- D4 blocking); next is 29.1-08 (tag)
Next: `/gsd:plan-phase 23` (Experiment Correctness Fixes).

Prior position (Phase 21 close) is preserved in `.planning/HANDOFF.json` and in
`.planning/milestones/v2.0-ROADMAP.md`.

## Performance Metrics

| Plan | Duration | Tasks | Files |
|------|----------|-------|-------|
| Phase 29.1 P01 | 13 min | 3 tasks | 7 files |
| Phase 29.1 P02 | 78 min | 3 tasks | 10 files |
| Phase 29.1 P04 | 7 min | 2 tasks | 3 files |
| Phase 29.1 P05 | 12 min | 2 tasks | 3 files |
| Phase 29.1 P03 | 72 min | 3 tasks | 12 files |
| Phase 29.1 P09 | 25 min | 3 tasks | 6 files |
| Phase 29.1 P06 | 50m | 3 tasks | 11 files |
| Phase 29.1 P07 | 2h45m | 3 tasks | 2 files |
