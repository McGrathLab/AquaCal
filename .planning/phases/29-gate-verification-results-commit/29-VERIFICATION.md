---
phase: 29-gate-verification-results-commit
verified: 2026-08-26T20:15:24Z
status: passed
score: 5/5 must-haves verified (criterion 6 correctly and honestly deferred, not counted as a failure)
behavior_unverified: 0
overrides_applied: 0
---

# Phase 29: Gate Verification & Results Commit — Verification Report

**Phase Goal:** The returned run is graded and becomes the repo's committed evidence base, with
every manuscript-facing number traceable to it.
**Verified:** 2026-08-26T20:15:24Z
**Status:** passed
**Re-verification:** No — initial verification

## Method

This verification did not trust SUMMARY.md or PHASE-RECORD.md prose. For every quantitative claim
that could be independently reproduced without violating the stated constraints (no
`pre-commit run --all-files`, no full 28-minute suite re-run, no Zenodo write calls, no mutation of
`~/aquacal-frozen-rerun-freeze-02-prod`), it was reproduced live against the actual repository
state and compared byte-for-byte against the evidence files. Findings below distinguish
**independently reproduced** from **evidence-file-only** (not independently re-derivable without
violating a constraint).

## Goal Achievement — the six ROADMAP criteria

| # | Criterion | Claimed | Independently checked | Verdict |
|---|-----------|---------|------------------------|---------|
| 1 | Gate passes over complete returned run, Gate 3 included | `176 PASS, 7 N/A, 0 FAIL`, sha `7005a277…` | **Re-ran `check_rerun_gates.py --profile full` live** against the current committed tree using the frozen-sha conda env (`aquacal-freeze02-clone`, aquacal 2.0.1, matches `7005a2771aa115e4f4c1284cec7e145739586a4a`). Got exit code 0, `TOTAL: 176 PASS, 7 N/A, 0 FAIL`, 0 `[FAIL` lines, `gate3_git_sha_consistency` PASS on the single sha, all 4 `gate3_run_manifest_*` lines PASS — exact match to `29-gates-full.txt`/`29-gates-committed.txt` | ✓ VERIFIED |
| 2 | E2 reproduces to ~1e-8, same-seed only | worst 2.5146e-08, headline 4.8962e-09, n=7762 exact | **Re-ran `analyze_e2_control.py` live.** Output: worst scalar `inter_corner_rmse_mm` = 2.5146e-08, worst overall 3.6317e-08, `RESULT: PASS` — exact match | ✓ VERIFIED |
| 3 | E7 before/after compared explicitly | fixed held 10/10 p=0.00098; refined moved 8/10→7/10 | **Re-ran `analyze_e7_before_after.py` live.** Output: primary held 10/10 p=0.00098 identical before/after; secondary moved 8/10(p=0.05469)→7/10(p=0.17188); artifact byte-identical (md5 `b6515ed77…`) across both run attempts, proving the move pre-dates the re-run — exact match, and the escalation is prominently flagged (own `⚠` section in the phase record, not buried) | ✓ VERIFIED |
| 4 | Results committed with provenance intact | `70e783f`, 227 files, 147 under `experiments/results/`, 40,497 ins / 0 del | **`git show --stat/--name-only 70e783f`**: 227 files changed, 40,497 insertions(+), 0 deletions, 147 under `experiments/results/`, zero files outside `experiments/`, all 227 are pure adds (git diff-status all `A`). md5 of `real_rig_metrics.json` = `57279708f6106f411d1fe03ed2698291` and `interface_ablation_band.csv` = `b6515ed77ed04268608b74217716020b` on disk right now — exact match to both the pre-commit and post-commit anchors quoted in the record. `git show 70e783f \| grep -c '^\ No newline at end of file'` = 143 exactly (proves formatting hooks never touched the artifacts). `git status --porcelain experiments/` empty | ✓ VERIFIED |
| 5 | Every §3-facing number traceable to this run (repo-side, D-29-19) | 3 LaTeX fragments inside the committed 147, single sha | Confirmed the 3 fragments (`benchmark_grid.tex`, `cpr_derived_values.tex`, `cpr_grouping.tex`) are among the 227 committed files and are the *only* `.tex` files touched anywhere in the phase's commit range. `main.tex` confirmed absent from this repository. The D-29-19 narrowing (repo-scoped traceability vs. manuscript-scoped) is a recorded, reasoned author ruling, not a silent scope-shrink — RUN-04's own wording ("traceable to this run") is the narrower, correct authority and REQUIREMENTS.md marks RUN-04 Complete on that basis | ✓ VERIFIED (repo-side, as explicitly scoped) |
| 6 | Zenodo results package published before submission | Record A published, Record B staged/unpublished, deferred by author ruling | **Live, read-only HTTP checks** (no write calls made): `https://doi.org/10.5281/zenodo.22116461` → 200; `https://zenodo.org/records/22116461` → 200 (Record A genuinely public, not merely claimed). `https://zenodo.org/records/22117061` → 404 and `https://zenodo.org/deposit/22117061` → 200 (draft page), confirming Record B is genuinely still unpublished, not silently pushed live. Deferral reason (v2.1.0 not yet cut) is internally consistent — confirmed `origin/main` HEAD equals `results/rerun-freeze-02`'s merge-base with no v2.1.0 tag present locally | **OPEN — honestly recorded and finishable (acceptable deferral)** |

## RUN-05 Pending Check (the specific adversarial ask)

- `REQUIREMENTS.md` currently reads `- [ ] **RUN-05**` and the traceability table row `| RUN-05 | Phase 29 | Pending |`. Confirmed by direct read of the file at HEAD.
- Walked the **entire git history** of `.planning/REQUIREMENTS.md` (`git log -p --follow`): RUN-05 never appears as `[x]` / `Complete` at any commit in this repository's history. The "three refusals" narrated in 29-04-SUMMARY.md and 29-07-SUMMARY.md (premature completions caught and reverted before commit) are consistent with this — no false completion ever reached a committed state.
- **One inconsistency found and worth flagging (non-blocking):** `29-04-SUMMARY.md`'s own YAML frontmatter still carries `requirements-completed: [RUN-05]` even though that same file's body explicitly documents the completion being reverted as a caught bug ("State-update correction (Rule 1 — bug)"). This is a leftover metadata artifact inside one SUMMARY file, not a leak into REQUIREMENTS.md or the roadmap. It does not affect the actual requirements ledger (confirmed correct via git history above), but a later automated process trusting `requirements-completed` frontmatter without cross-checking REQUIREMENTS.md itself could be misled. Recorded here rather than silently accepted.

## Scope Fences — verified, not assumed

| Fence | Check | Result |
|---|---|---|
| `.gitignore` / `.pre-commit-config.yaml` unchanged across phase | `git log <first-29-01-commit>~1..HEAD -- .gitignore .pre-commit-config.yaml` | empty — unchanged |
| `experiments/check_rerun_gates.py` unedited | included in the same diff range check | not present in the diff — unedited |
| No manuscript file touched | `git diff --name-only <range> \| grep '\.tex$'` | only the 3 generated result fragments |
| Nothing outside `experiments/`, `.planning/`, `scripts/` touched (except the one ruled rails-repair) | `git diff --name-only <range>` filtered | only `tests/unit/test_experiments_provenance.py` (the ruled, single-file rails repair, commit `5799b14`) |
| No test skipped/xfailed/deselected | `git diff <range> -- tests/ \| grep -iE 'skip\(\|xfail\|deselect'` | empty |
| `.git/hooks/` has no live (non-`.sample`) hooks | evidence file + repo check | 0 |
| No credential leak | `grep` across phase commits for token-shaped strings; `scripts/zenodo_upload.py` inspected | none found; token read from `os.environ`, never a CLI flag; no `/actions/` publish path exists anywhere in the file or repo |
| Rails-repair commit isolated | `git show --stat 5799b14`; ancestry check | exactly 1 file changed (241 ins / 5 del); confirmed descendant of `70e783f`, never amends it |

## Test/Gate State (spot-checked, not fully re-run per constraints)

- `pytest tests/unit/test_experiments_provenance.py -q` re-run live: **287 passed, 20 skipped** — exact match to the claimed "after" state and to the confirmation sample quoted in the task.
- The tag `rerun-freeze-02` annotation (read directly via `git tag -l -n99`) independently confirms, in the author's own pre-Phase-29 words, the same three ruled node IDs (`test_matches_frozen_anchor`, `test_detail_sink_recomputed_geometry_matches_projector`, `test_matches_pre_change_anchor`) as platform-pinned Windows-anchor exact-equality failures — this is not a claim invented inside Phase 29's own record, it pre-exists in the tag. Per the task's explicit instruction, the 3 failures are treated as the ruled expected count, not a defect.
- Full-suite `3 failed / 2394 passed / 21 skipped` was **not** re-run (constraint honored — ~28 min, unnecessary given the tag annotation and the targeted-module re-run above corroborate it).

## Anti-Pattern Scan

Searched all phase-touched non-artifact files (`scripts/zenodo_upload.py`, both analysis scripts,
`tests/unit/test_experiments_provenance.py`) for `TBD`/`FIXME`/`XXX`/`TODO`/`HACK`/`PLACEHOLDER` and
empty-implementation patterns. **None found.** No debt markers anywhere in the phase's code
deliverables.

## What Could Not Be Independently Verified (evidence-file-only)

- The Zenodo Record A/B payload internals (byte-for-byte archive membership, the 3,996-entry
  manifest, the md5 round-trip against the server's own returned checksum at upload time) rely on
  `29-zenodo-record-a.txt` / `29-zenodo-record-b.txt` — reproducing these would require re-uploading
  multi-gigabyte payloads, explicitly forbidden by the constraints. The externally-visible half
  (DOI resolution, publish/unpublish state) **was** independently confirmed live over HTTP.
- The sandbox rehearsal (`29-zenodo-sandbox-rehearsal.txt`) and the author's live UI actions
  (publishing Record A by hand) are, by design, human/UI actions outside repo-only verification —
  their after-effects (the DOI now resolving) were checked instead.
- Full pytest suite count (2394 passed / 21 skipped / 3 failed) was not re-run per explicit
  constraint; corroborated via the targeted module re-run and the pre-existing tag annotation.

## Requirements Coverage

| Requirement | Status in REQUIREMENTS.md | Verified |
|---|---|---|
| RUN-03 | `[x]` Complete | ✓ — gate re-run confirms |
| RUN-04 | `[x]` Complete | ✓ — commit contents, hashes, byte-integrity all re-verified |
| RUN-05 | `[ ]` Pending | ✓ correctly left open — confirmed never flipped to complete anywhere in git history |

No orphaned requirements found for this phase.

## Gaps Summary

**None that block the phase goal.** Criterion 6 (RUN-05) is open, but this is an honest,
reasoned, and finishable deferral by explicit author ruling (2026-08-26), not a failure to
deliver: Record A is genuinely published (confirmed live), Record B is genuinely built and staged
but deliberately not published (confirmed live), the reason (v2.1.0 not yet cut) is
internally consistent with the actual git state, and a specific, actionable todo file plus a new
roadmap phase (29.2) exist to close it. RUN-05 is correctly left `Pending` and was never
silently or accidentally marked complete at any point in the repository's history.

One minor, non-blocking documentation inconsistency was found and is recorded above (the stale
`requirements-completed: [RUN-05]` frontmatter line in `29-04-SUMMARY.md`, contradicted by that
same file's own body text and by the authoritative `REQUIREMENTS.md`). It does not change the
> **Follow-up applied 2026-08-26 (orchestrator).** The stale frontmatter was corrected in `29-04-SUMMARY.md` **and** in `29-01-SUMMARY.md`, which carried the identical `requirements-completed: [RUN-05]` claim and was not caught by this verification pass. Both now read `requirements-completed: []`, matching their own body text and the authoritative `REQUIREMENTS.md` (RUN-05 `[ ]`). RUN-03 `[x]` and RUN-04 `[x]` were checked at the same time and their claims in `29-06`/`29-05` are sound.

verdict.

## Overall Verdict

**Phase 29's goal is achieved.** Every reproducible quantitative claim in the PHASE-RECORD was
independently re-derived from the live repository and matched exactly: the gate roll-up, the E2
same-seed drift figures, the E7 before/after sign-test figures (including the byte-identical-csv
proof that the moved conclusion pre-dates the re-run), the commit's file/line/hash statistics, and
the byte-integrity markers. The scope fences (gitignore, pre-commit config, no manuscript edits,
no credential exposure, no silenced tests) all held under direct inspection. RUN-05's deferral is
honest, externally verifiable (Record A publicly resolving, Record B publicly still unpublished),
and actionable. Criteria 1-5 are met and measured; criterion 6 is legitimately open by
construction, exactly as claimed.

---

*Verified: 2026-08-26T20:15:24Z*
*Verifier: Claude (gsd-verifier)*
