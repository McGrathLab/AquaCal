---
phase: 23-experiment-correctness-fixes
plan: 04
subsystem: testing
tags: [provenance, documentation, experiments, synthetic-data, regression-test]

# Dependency graph
requires: []
provides:
  - "Four corrected provenance strings in experiments/e2_real_rig.py and src/aquacal/datasets/synthetic.py describing the live Zenodo archive (21889922) instead of the retired one (18645385)"
  - "A supersession header on 19.1-E2-FRAMESET-PROVENANCE.md preserving its historical body"
  - "tests/unit/test_stale_provenance_strings.py -- a source-text regression guard against partial fixes of this defect class"
affects: [23-run-execution, 26-full-suite-driver-and-handoff, 28-suite-execution]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Source-text regression tests for provenance strings: assert on claim sentences (not bare number tokens) scoped to named files, never repo-wide, because the test file and any supersession header necessarily quote the stale strings themselves."
    - "Supersession header over an edit: a historical document that was correct when written gets a header block declaring what changed and why, with its body preserved verbatim below a `---` rule, rather than being rewritten to look correct in hindsight."

key-files:
  created:
    - tests/unit/test_stale_provenance_strings.py
  modified:
    - experiments/e2_real_rig.py
    - src/aquacal/datasets/synthetic.py
    - .planning/phases/19.1-experiment-suite-consolidation/19.1-E2-FRAMESET-PROVENANCE.md

key-decisions:
  - "Site 2's provenance string names its derivation and marks the release comparison (0.8786 px) superseded rather than swapping in today's live value (0.8240) -- hardcoding a fresh number reproduces the same defect at the next run."
  - "19.1-E2-FRAMESET-PROVENANCE.md received a pure-insertion header (0 deletions), never an edit -- it remains an accurate historical record of the now-retired Zenodo record 18645385."
  - "Sites 1 and 4 (the --config help and the explicit-config branch comment) were corrected together in one pass and asserted together by test_both_archive_sites_were_corrected, because a previous pass at this defect class fixed one and left the other."

patterns-established:
  - "Pattern: negative-control proof for a regression test -- before trusting a new source-text test, temporarily swap in the pre-fix file content (via git show HEAD:path > scratch file, not git stash, since stash is shared across worktrees) and confirm the test fails, then restore."

requirements-completed: [FIX-06]

# Metrics
duration: 35min
completed: 2026-08-17
---

# Phase 23 Plan 04: FIX-06 Stale Provenance Strings Summary

**Corrected four provenance strings in `e2_real_rig.py`/`synthetic.py` that described the retired, subsampled Zenodo record as the current archive, superseded (not edited) the document that first diagnosed it, and added a source-text regression test — zero logic changes anywhere in the diff.**

## Performance

- **Duration:** ~35 min
- **Started:** 2026-08-17 (worktree agent-a2bd13de8d5f5b91e)
- **Completed:** 2026-08-17
- **Tasks:** 3 (all landed in a single commit per D-14: FIX-06 is one requirement)
- **Files modified:** 4 (3 modified, 1 created)

## Accomplishments

- All four stale provenance sites corrected, stated consistently: record `21889922` via commit `25655f7`, retired record `18645385`, chain `262 usable frames -> 210/52 split -> 200 calibration frames -> reconstruction.num_comparisons = 7762`, MF-19 named as the open value question.
- `19.1-E2-FRAMESET-PROVENANCE.md` received a supersession header as a pure insertion (verified `git diff --stat`: 22 insertions, 0 deletions); its historical body, including the subsampling table, survives intact below the `---` rule.
- `tests/unit/test_stale_provenance_strings.py` created: 11 tests, 0 skipped, and demonstrated to fail (5 of 11) against the reverted, pre-fix source before being trusted.
- Confirmed via `git diff -U0` inspection that every added/removed line across both source files sits inside a string literal, docstring, or comment — no logic, signature, default, or emitted-column change anywhere (D-13).

## Task Commits

All three tasks landed in a single commit per D-14 (FIX-06 is one requirement, shipped as one commit covering all four sites, the supersession header, and the regression test):

1. **Task 1 (four stale code sites) + Task 2 (supersession header) + Task 3 (regression test)** - `3f867c2` (fix)

**Plan metadata:** this SUMMARY's own commit (docs)

## Files Created/Modified

- `experiments/e2_real_rig.py` — three corrected provenance strings: the `--config` help (site 1, :847-870 after edit), the `mean_per_camera_reprojection_px` provenance parenthetical (site 2, :286-290), and the explicit-config branch comment (site 4, :559-572)
- `src/aquacal/datasets/synthetic.py` — `generate_camera_array`'s `height_above_water` Args entry corrected to describe `WATER_Z` as a frozen design constant that approximates the real-rig standoff, naming the rig's actual estimated `water_z` (1.0738404 m) without reconciling the constant toward it (site 3, :183-193)
- `.planning/phases/19.1-experiment-suite-consolidation/19.1-E2-FRAMESET-PROVENANCE.md` — supersession header inserted above the original H1; pre-edit blob hash `9b0ffd48eb8329183375af4b54ff35b34c0914ae`
- `tests/unit/test_stale_provenance_strings.py` (new) — 11 tests across three classes (`TestE2RealRigStrings`, `TestSyntheticWaterZDescription`, `TestFramesetProvenanceSupersession`), repo-root anchored via `parents[2]`, no repo-wide grep

## Decisions Made

- No live measured value (0.8240) was hardcoded into site 2's provenance string; it instead names its derivation and marks the release comparison (0.8786) explicitly superseded. Swapping one frozen number for another would reproduce the defect at the next run.
- The supersession document was given a header, not an edit — `git diff` shows zero deleted lines, preserving the document's value as a description of the retired record and the trail of how the four code-site errors originated.
- Sites 1 and 4 (the two places carrying the identical stale claim) were verified together via `test_both_archive_sites_were_corrected`, which asserts `count(token) >= 2` for four shared tokens — directly encoding the failure mode a previous partial fix left behind.

## Deviations from Plan

None - plan executed exactly as written. All four sites, the supersession header, and the regression test match the plan's literal current/replacement text specifications.

## Evidence

**Pre-edit blob hash of `19.1-E2-FRAMESET-PROVENANCE.md`:** `9b0ffd48eb8329183375af4b54ff35b34c0914ae`

**Reverted-source test proof (D-11's inspection-plus-unit-test verification):**
- With `experiments/e2_real_rig.py` swapped to its pre-fix content (via `git show HEAD:experiments/e2_real_rig.py` to a scratchpad file, then copied over the worktree file — **not** `git stash`, since the stash ref is shared across worktrees and pops the wrong session's WIP): `python -m pytest tests/unit/test_stale_provenance_strings.py -q` → **5 failed, 6 passed** (the tests scoped to `synthetic.py` and the frameset doc correctly kept passing, since only `e2_real_rig.py` was reverted).
- After restoring the fixed content: **11 passed, 0 failed, 0 skipped.**

**Targeted test runs (per D-11, no E1/E4/E2 run, no `pytest tests/`):**
- `python -m pytest tests/unit/test_stale_provenance_strings.py -x -q` → 11 passed.
- `python -m pytest tests/unit/test_datasets.py tests/unit/test_synthetic_scenario_geometry.py -x -q` → 117 passed — proves the `synthetic.py` docstring edit broke no existing consumer.

**Static checks:** `ruff check` and `ruff format --check` exit 0 on all three touched/created Python files; `ast.parse` succeeds on both edited source files.

## Checked-and-left items (from `<what_is_deliberately_left_alone>`)

- **`e2_real_rig.py:255-262`** (the comment above the `provenance` dict return, citing 0.8786/1.0191) — left unchanged. It is correct as history: it describes the release run explicitly and by name, distinguishing the pooled RMS from the per-camera mean. Site 2's defect was different — a provenance string attached to a field holding 0.8240 quoting 0.8786 as if describing that field.
- **`src/aquacal/datasets/synthetic.py:1016, :1062, :1100, :1142`** (four further "real-rig standoff" shorthand uses) — left unchanged. `:1100`/`:1142` are inside scenario `description=` values that are committed artifact data (echoed into `docs/tutorials/01_full_pipeline.ipynb:164` and read by `tests/unit/test_datasets.py:502`); editing them would move artifact content, which this plan must not do. `:1016`/`:1062` are prose shorthand outside FIX-06's four named sites.
- **`docs/tutorials/01_full_pipeline.ipynb:180`** ("Found 60 usable frames") — left unchanged. This is captured historical output from a real run against the subsampled archive, not a claim; regenerating notebooks is out of phase.
- **`docs/guide/troubleshooting.md:99`** — left unchanged per D-05. It accurately describes the still-live hardcoded `water_z` `[0.01, 2.0]` bound and changes only when that limitation does.

## Issues Encountered

None. The `git diff -U0` line-shape inspection required for the no-logic acceptance criterion (every added/removed line inside a string, docstring, or comment) was checked directly against the actual diff and confirmed clean on the first pass.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- FIX-06 is fully landed and independently verifiable by inspection plus the new regression test; no runtime probe was needed or run (D-11).
- No `.planning/MANUSCRIPT-FINDINGS.md` entry was created, per the 2026-08-17 amendment to D-12: this plan produced no evidence artifact (a strings-only fix), so no findings entry was manufactured.
- This plan's diff is fully disjoint from the other three wave-1 plans (23-01, 23-02, 23-03) — no shared files, no code-logic touch, isolated per D-13 so it can never be attributed to a moving number elsewhere in phase 23.

---
*Phase: 23-experiment-correctness-fixes*
*Completed: 2026-08-17*

## Self-Check: PASSED

- FOUND: `tests/unit/test_stale_provenance_strings.py`
- FOUND: `.planning/phases/23-experiment-correctness-fixes/23-04-SUMMARY.md`
- FOUND: commit `3f867c2`
- FOUND: commit `defc75a`
