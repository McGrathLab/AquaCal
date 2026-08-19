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
  - "RL-guard-frac is a FOURTH row of the same class, unnamed by D-17 — CONFIRMED by the author; 27-07's note carries four rows"
  - "linux32gb_scope.json graded EMITTER-BACKED/NOT REGENERATED rather than NO EMITTER; grade UPHELD by the author as the one judgement call"
  - "linux32gb_scope.json's top-level git_sha disagrees with e2_cv413/benchmark.json (d27bda7 vs 1af0650) — cv413 rows attributed per artifact, matching 27-07"
  - "diagnostics.json is emitted but NOT registered in suite_expectations.json — recorded as a deliberately-deferred coverage hole; NOT fixed in the freeze window"
metrics:
  duration: ~35 min
  tasks_completed: 3 of 3 (human-verify gate reached, presented, approved)
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
- `9270ea8` — `docs(27-06): record the emitter-coverage walk and its checkpoint` (SUMMARY, pre-gate)
- `20db9ac` — `docs(27-06): apply the author's three rulings and 27-07's sha finding` (Task 3)

## Task 3 — the human-verify gate: reached, presented, APPROVED

The gate was **not self-approved**. Execution stopped at Task 3, the report was presented to the
author with the NO EMITTER count stated up front, and the author returned a verdict plus three
rulings.

**Verdict: approved. NO EMITTER count 0. Criterion 5 is CLOSED and the freeze proceeds** — no
emitter added, no tag re-cut, no return to this phase.

| # | question | ruling | applied as |
|---|---|---|---|
| 1 | Does `linux32gb_scope.json`'s grade stand, or is it NO EMITTER? | **Grade STANDS** (EMITTER-BACKED, NOT REGENERATED). Make the reasoning explicit rather than implicit. | §3 note § rewritten: its numbers are traceable *through* the neighbouring emitter-backed artifacts it quotes, **not** through code that writes the file itself; the tree is deliberately never re-run. §1 and §8 updated to match. |
| 2 | Fix `diagnostics.json`'s gate coverage now? | **No — record only, change nothing.** No copy-out added to `experiments/e2_real_rig.py`; the freeze window is for defects that would cost the run. | §3 note ‡ rewritten as a known, deliberately-deferred coverage hole, naming the emitter, the reason it never reaches `experiments/results/`, and that closing it is later-phase work. |
| 3 | Is `RL-guard-frac` a fourth unregenerable-by-construction row? | **Confirmed.** Note it; do not edit `experiments/FROZEN-ROWS.md` (27-07 owns it, running concurrently). | §4 retitled "A CONFIRMED fourth row…" with a four-row handoff table and an explicit statement that `FROZEN-ROWS.md` is 27-07's file and was not touched. |

### Post-ruling input from plan 27-07, verified here and folded in

27-07 walked the same trees and found that **`linux32gb_scope.json`'s top-level `git_sha` is wrong
for at least one subtree.** Verified independently rather than taken on report:

| file | recorded `git_sha` |
|---|---|
| `linux32gb_scope.json` (claims the whole tree) | `d27bda76fe7c765b3c975b2052ca1f8f7b286068` |
| `results_linux32gb/e2_timing/benchmark.json` | `d27bda76…` — agrees |
| `results_linux32gb/e2_memory/benchmark.json` | `d27bda76…` — agrees |
| `results_linux32gb/e2_cv413/benchmark.json` | **`1af06508db120daacce8618b8387c7a7213b1fbe`** — disagrees |

Two further facts established here, both by direct check: `1af0650` is **exactly one commit** after
`d27bda7` (`chore(experiments): commit the 32 GB Linux re-run of E4 and E2`), so the OpenCV 4.13
control ran *after* its sibling artifacts were committed; and **`git diff d27bda7 1af0650 -- src/`
is empty**, so no library code moved between them.

**Consequence: provenance moves, no number does.** A reader trusting the scope file's single
top-level sha would attribute `RL-repro-rig` to the wrong commit. This is the F-001
provenance-fracture shape in miniature. It does **not** overturn the author's ruling — the grade
stays EMITTER-BACKED, NOT REGENERATED — but it supplies a second reason, independent of the
missing emitter, why that row is the judgement call.

**Agreed treatment, shared with 27-07:** attribute the two cv413-sourced ledger rows **per
artifact**, from `e2_cv413/benchmark.json`'s own `git_sha`, never through the scope file's
top-level claim. Both documents state this, so they agree where they are read together.

## Status

**Plan 27-06 COMPLETE — 3 of 3 tasks.** Criterion 5 is closed. `experiments/FROZEN-ROWS.md`,
`STATE.md`, `ROADMAP.md` and `numbers-ledger.tsv` were not touched by this plan.

## Self-Check: PASSED

- `experiments/EMITTER-COVERAGE.md` — FOUND
- `.planning/phases/27-frozen-single-sha-handoff-package/27-06-SUMMARY.md` — FOUND
- commits `c1f3af2`, `9270ea8`, `20db9ac` — all FOUND in `git log`
- main table still 27 rows after the ruling edits; 0 occurrences of "TBD"
- `numbers-ledger.tsv` mtime unchanged (`Aug 14 11:37`, 33539 bytes)
- `experiments/FROZEN-ROWS.md`, `STATE.md`, `ROADMAP.md` — absent from this plan's diff
