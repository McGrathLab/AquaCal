---
phase: 27-frozen-single-sha-handoff-package
plan: 06
subsystem: experiments/provenance
tags: [emitter-coverage, criterion-5, traceability, numbers-ledger, freeze]
requires:
  - numbers-ledger.tsv (read-only, off-repo)
  - experiments/suite_expectations.json
  - experiments/EXPECTATIONS.md (house style)
provides:
  - experiments/EMITTER-COVERAGE.md
affects:
  - 27-07 (frozen-row note, D-19) — recommended to carry FOUR rows, not three
  - Phase 29 RUN-04 traceability
  - Phase 30 dangling-reference audit
tech-stack:
  added: []
  patterns: [in-repo verification note modelled on experiments/EXPECTATIONS.md]
key-files:
  created:
    - experiments/EMITTER-COVERAGE.md
  modified: []
decisions:
  - "NO EMITTER count is 0 — criterion 5 closes without adding an emitter"
  - "M-L281-19mm and M-L281-135x are lockstep restatements of M-L68-* (artifact exp1_band.csv); emitter exists, none added"
  - "RL-determinism is unregenerable by construction (P26-D-42); handed to 27-07 rather than given an invented emitter"
  - "RL-guard-frac is a FOURTH row of the same class, unnamed by D-17 — 27-07's note should carry four rows"
  - "linux32gb_scope.json graded EMITTER-BACKED/NOT REGENERATED rather than NO EMITTER; flagged as the one judgement call"
  - "diagnostics.json is emitted but NOT registered in suite_expectations.json — no completeness gate covers it"
metrics:
  duration: ~35 min
  tasks_completed: 2 of 3 (Task 3 is a blocking human-verify checkpoint)
  completed: 2026-08-19
---

# Phase 27 Plan 06: Emitter Coverage Report Summary

Walked all 27 distinct artifacts in the manuscript numbers ledger to a `file:line` write call in
the frozen code and produced `experiments/EMITTER-COVERAGE.md` — **0 NO EMITTER**, so ROADMAP
criterion 5 closes without adding an emitter or reshaping a schema.

## What was built

`experiments/EMITTER-COVERAGE.md` (280 lines), modelled on `experiments/EXPECTATIONS.md`'s house
style: a "written before the fact" opener, a dense per-row verdict-plus-reason table, every claim
carrying a `file:line`, and a bold anti-misreading callout.

Sections:

1. **The headline** — NO EMITTER count stated up front, plus the two flagged caveats.
2. **"An emitter existing does not make the number right"** — the §4-voice callout, with three
   consequences spelled out (a zero count closes traceability, not accuracy; NOT REGENERATED is
   not a weaker grade; the ledger's `derivation` column is not verified by this walk).
3. **The walk** — 27 artifact rows: artifact, ledger row count, emitting stage, emitter
   `file:line`, verdict. Totals 19 EMITTER-BACKED / 8 EMITTER-BACKED, NOT REGENERATED / 0 NO
   EMITTER, covering 110 of the ledger's 131 rows.
4. **The three genuine candidates** resolved, plus a fourth found.
5. **The seven `KEEP-FROZEN-5f` rows** and their tie to the OpenCV 4.13 pin / D-26 risk.
6. **The 11 non-`EDIT` empty-artifact rows**, by ledger `id`, each with a reason.
7. **The 10 `EDIT` empty-artifact rows**, for completeness — all 21 accounted for.
8. **What the author is being asked to confirm.**

## The three candidates (Task 2, D-18)

| candidate | conclusion | evidence |
|---|---|---|
| `M-L281-19mm` | **Emitter exists** | Lockstep group `g-19mm` binds it to `M-L68-19mm`, which carries `artifact = exp1_band.csv` and the full derivation. Emitter `experiments/e1_refractive_comparison.py:1182`. Empty `artifact` cell is a restatement marker, not a gap — the ledger's own note says "must not drift from the abstract". |
| `M-L281-135x` | **Emitter exists** | Lockstep group `g-135x` → `M-L68-135x`, same artifact and emitter; the derivation is a ratio over `z_rmse_mm` grouped by model at `test_depth_m==2.5`. |
| `RL-determinism` | **Unregenerable by construction** | Needs a paired repeat; P26-D-42 turned `e6_repeat2` OFF. Pinned negatively by `tests/unit/test_expectations.py:353`. Handed to 27-07's frozen-row note. |

**No emitter was added**, so no manifest edit, no expectation-sheet regeneration, no new test, and
no `render_expectation_sheet --check` run were required. No stop-and-report condition arose.

## Findings for the orchestrator / author

1. **`RL-guard-frac` is a fourth unregenerable-by-construction row that D-17 did not name.** Its
   ledger note says "no committed artifact — pre-fix state"; it measures a state the fixed code
   cannot produce. **Recommendation: plan 27-07's D-19 note should carry four rows, not three.**
2. **`diagnostics.json` is emitted but unregistered.** `save_diagnostic_report`
   (`src/aquacal/validation/diagnostics.py:876`, JSON write at `:1016`) is called from
   `src/aquacal/calibration/pipeline.py:1644` and writes into the *config's* `output_dir`. E2
   copies only `benchmark.json` and `calibration.json` out of that directory
   (`experiments/e2_real_rig.py:747`), so the file never reaches `experiments/results/` and is
   absent from the manifest's 62 artifacts. The two rows on it (`RL-pnp-rejected`,
   `RL-pnp-translation`) are regenerated but uncovered by any completeness gate.
3. **The ledger's `generalization_sweep_band.csv + seed-43 re-solve` artifact string is now stale
   in the ledger's favour.** FIX-03 (23-03) folded the gauge-corrected Z column into the standard
   band emitter (`experiments/e6_generalization_sweep.py:303-304`, built at `:760`), so this run
   regenerates `S-collinear-residual` directly. Manuscript-side edit; not made here.
4. **The `KEEP-FROZEN-5f` rows are the tripwire for D-26.** All seven name
   `real_rig_metrics.json` and are frozen behind the OpenCV 4.13 pin. If 27-12's new-environment
   step slips and the run lands on the target's existing OpenCV 4.14, these seven rows are where
   it surfaces first.

## Deviations from Plan

**1. [Process] Tasks 1 and 2 landed in one commit.** Both tasks write sections of the same new
file; Task 2's output is §4 of the document Task 1 creates. Splitting them would have meant
writing `EMITTER-COVERAGE.md` twice with an intermediate state that was deliberately incomplete.
Committed once as `c1f3af2`. No content was dropped — both tasks' acceptance criteria are met and
verified below.

**2. [Reporting judgement, not a rule deviation] `linux32gb_scope.json` graded NOT REGENERATED
rather than NO EMITTER.** It is the only one of the 27 with no code write at all — a hand-assembled
scope and confound-control statement. Its numeric claims quote artifacts beside it that do have
emitters (`e2_cv413/`, `e4/benchmark_grid.csv`, `e2_timing/`, `e2_memory/`), and the tree is
deliberately never re-run, so it is not a "hand-asserted number with no artifact behind it". The
report states the judgement explicitly and names it as the first thing to spot-check rather than
rounding it silently in either direction. **If the author re-grades it, the NO EMITTER count
becomes 1 and the freeze goes back to this phase (D-03/D-18).**

No Rule 1/2/3 auto-fixes were needed. No architectural (Rule 4) question arose.

## Verification

| Acceptance criterion | Result |
|---|---|
| `experiments/EMITTER-COVERAGE.md` exists | PASS |
| Main table has 27 artifact rows | PASS — `grep -c '^\| [0-9]'` → 27 |
| No EMITTER-BACKED row has an empty or "TBD" emitter cell | PASS — `grep -ci 'TBD'` → 0; every row's emitter cell inspected |
| 11 non-`EDIT` empty-artifact rows enumerated by ledger `id` with a reason | PASS — §6 |
| Bold "an emitter existing does not make the number right" callout present | PASS — §2 heading |
| Three candidates each have exactly one conclusion with evidence | PASS — §4 |
| `grep -c 'M-L281-19mm'` | 2 |
| OneDrive manuscript tree unmodified | PASS — `numbers-ledger.tsv` mtime still `Aug 14 11:37`, size 33539; the file was never opened for writing |
| `git status --porcelain` clean, no OneDrive path in the repo diff | PASS |
| STATE.md / ROADMAP.md untouched | PASS |

Full test suite NOT run — no code changed, and per CLAUDE.md the orchestrator owns the post-merge
gate. No experiment was run: this plan locates emitters, it does not re-derive values.

## Commits

- `c1f3af2` — `docs(27-06): walk all 27 ledger artifacts to their emitters` (Tasks 1 + 2)

## Status

**Tasks 1–2 complete. Task 3 is a blocking `checkpoint:human-verify` gate and is NOT
self-approved.** The author must state the NO EMITTER count and whether the freeze proceeds, and
rule on the two flagged verdicts plus the 27-07 four-row recommendation.

## Self-Check: PASSED

- `experiments/EMITTER-COVERAGE.md` — FOUND
- `.planning/phases/27-frozen-single-sha-handoff-package/27-06-SUMMARY.md` — FOUND
- commit `c1f3af2` — FOUND in `git log`
