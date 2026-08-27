---
phase: 29-gate-verification-results-commit
plan: 08
subsystem: planning
tags: [phase-record, roadmap-criteria, forward-carried, zenodo, doi, e7-sign-test, run-05, checkpoint]

# Dependency graph
requires:
  - phase: 29-06
    provides: "the repaired provenance rails (8 -> 0) and the ruled full-suite count (11 -> 3), plus 29-rails-after.txt's D-29-14 residual section"
  - phase: 29-07
    provides: "Record B's verified draft at deposition 22117061, Record A's minted DOIs, and the sequential linkage ruling"
  - phase: 29-02
    provides: "29-gates-full.txt and 29-commit-manifest.txt — criteria 1 and 4's measured values"
  - phase: 29-03
    provides: "29-e2-control.txt and 29-e7-before-after.txt — criteria 2 and 3's measured values"
  - phase: 29-05
    provides: "the 227-file artifacts commit 70e783f and 29-gates-committed.txt — the committed-tree form of criterion 1"
provides:
  - "29-PHASE-RECORD.md — the document Phase 29.2 and Phase 30 open first: one row per ROADMAP success criterion with its measured value and the evidence file it came from, the E7 escalation, D-29-10's stop list evaluated, and twelve forward-carried items"
  - "A `WHAT REMAINS` section at the top of the record: the five steps that finish the job, in order, so a returning session does not reconstruct the reasoning"
  - "Seven todos under .planning/todos/pending/ carrying the manifest repoint's ten-site table, the deposit-API posture, the no-PR-into-main constraint, the D-29-14 residual, the publish sequence, the Phase 30 date defect, and the STATE.md format divergence"
  - "The author's `defer` ruling on criterion 6, recorded with its date, its reason and every consequence"
affects: [29.2, 30-post-01, RUN-05]

actuals:
  tokens: 47000
  tasks: 3
  commits: 4

tech-stack:
  added: []
  patterns:
    - "The phase record's ordered `WHAT REMAINS` section sits ABOVE the derivations, because the reader most likely to need it is the one least likely to read to the end"
    - "Every forward-carried item is filed twice — once as a numbered item in the record, once as a todo whose filename the record names — so neither document is a single point of failure"
    - "A deferral is recorded with its consequences enumerated (task skipped, requirement left Pending, criteria closed against) rather than as a bare option id"

key-files:
  created:
    - .planning/phases/29-gate-verification-results-commit/29-PHASE-RECORD.md
    - .planning/todos/pending/2026-08-26-repoint-the-dataset-manifest-after-the-zenodo-split.md
    - .planning/todos/pending/2026-08-26-legacy-zenodo-deposit-api-deprecation-posture.md
    - .planning/todos/pending/2026-08-26-no-pull-request-into-main-until-ci-pre-commit-is-scoped.md
    - .planning/todos/pending/2026-08-26-d4-exact-equality-anchors-are-platform-pinned.md
    - .planning/todos/pending/2026-08-26-publish-record-b-and-add-record-a-back-link.md
    - .planning/todos/pending/2026-08-26-phase-30-dependency-still-names-the-passed-2026-08-21-submission-date.md
    - .planning/todos/pending/2026-08-26-state-md-body-format-diverges-from-gsd-state-handlers.md
  modified: []

key-decisions:
  - "Criterion 6 closed as OPEN on the author's `defer` ruling (2026-08-26), not on an inference. Record B cites 2.1.0 and v2.1.0 does not exist; publishing would mint a permanent record naming a version nobody can install."
  - "RUN-05 was NOT marked complete. Plans 29-04 and 29-07 each had to avoid a premature completion of this same requirement; this is the third refusal and it is deliberate."
  - "Task 4 (the human-verify publication gate) was SKIPPED under the defer branch, because the publication it verifies is not happening in this phase."
  - "The E7 refined-pairing move is routed explicitly to POST-01 / Phase 30 as a manuscript-side item, with the byte-identity finding that dates it to FIX-02 rather than to the re-run. No manuscript file was opened."
  - "Three forward-carried items discovered after the plan was written (the Phase 30 date defect, the STATE.md format divergence, the publish-and-back-link sequence) were filed as todos of their own rather than left as record prose only."
  - "The manifest repoint carries its full ten-site table verbatim into the todo, because the entire point of filing rather than doing is that a later session must not have to re-grep."

patterns-established:
  - "When a checkpoint's premises have changed since the plan was written, present the CHANGED premises first — the plan assumed both records unpublished; Record A was already published, and the v2.1.0 ordering constraint did not exist when the options were drafted"
  - "Record an author's ruling by enumerating what it makes true and what it leaves untrue, so a later reader cannot mistake a deliberate deferral for an oversight"

requirements-completed: []

coverage:
  - id: D1
    description: "29-PHASE-RECORD.md answers every one of ROADMAP Phase 29's six success criteria with a measured value and the evidence file that value came from"
    requirement: RUN-03
    verification:
      - kind: other
        ref: "grep -F over the record for all fourteen load-bearing literals: '176 PASS, 7 N/A, 0 FAIL', '2.52e-08', '4.90e-09', '7762', '10/10', '8/10', '7/10', '0.00098', '227', '147', '209', '7005a2771aa115e4f4c1284cec7e145739586a4a', 'b6515ed77ed04268608b74217716020b', '119,406' and '119406' — all present"
        status: pass
      - kind: other
        ref: "git diff --quiet -- experiments/ src/ tests/ => exit 0; git status --porcelain experiments/ => empty"
        status: pass
    human_judgment: false
  - id: D2
    description: "The E7 refined-pairing move is raised in its own headed subsection with the byte-identity finding, and routed to POST-01 / Phase 30"
    requirement: RUN-03
    verification:
      - kind: other
        ref: "record section '⚠ THE E7 REFINED-PAIRING MOVE — D-29-16's flag-to-author case' carries 8/10 (p = 0.05469) -> 7/10 (p = 0.17188), md5 b6515ed77ed04268608b74217716020b byte-identical across attempts, 'Routed to: POST-01, Phase 30', and 'section 3 edits stay the author's'"
        status: pass
    human_judgment: false
  - id: D3
    description: "Every forward-carried item is filed as an actionable todo whose filename the phase record names"
    verification:
      - kind: other
        ref: "7 new todos under .planning/todos/pending/ dated 2026-08-26; the manifest todo contains all ten blast-radius sites verbatim, 'resolves_phase: 30', 'POST-01', the four-frozen-sites note and the promote-not-add-alongside verdict; git diff --quiet -- src/ experiments/ tests/ => exit 0"
        status: pass
    human_judgment: false
  - id: D4
    description: "Success criterion 6 is closed on the author's explicit ruling, never on an inference, and RUN-05 is left Pending"
    requirement: RUN-05
    verification: []
    human_judgment: true
    rationale: "Phase 29 cannot observe the paper's submission event, and it cannot press Publish (D-29-01). Whether to walk through a one-way door that mints a permanent DOI is the author's decision by construction; the phase's only job was to present it honestly and record the answer with its consequences."

# Metrics
duration: 45min
completed: 2026-08-26
status: complete
---

# Phase 29 Plan 08: Phase Record, Forward-Carried Items, and Criterion 6 Summary

**Phase 29 now has a record a reviewer can check line by line — every ROADMAP criterion with its measured value and the evidence file it came from — and the one criterion Phase 29 could never close by itself was deferred on the author's explicit ruling rather than fabricated, leaving the phase closed against criteria 1-5 with RUN-05 honestly `Pending`.**

## Performance

- **Duration:** ~45 min, including one blocking checkpoint the author resolved mid-plan
- **Started:** 2026-08-26T15:20Z
- **Completed:** 2026-08-26T16:05Z
- **Tasks:** 3 executed, 1 deliberately skipped (Task 4, under the `defer` branch)
- **Files created:** 8 (1 phase record, 7 todos)

## Accomplishments

- **Every ROADMAP criterion is answered with a number and a filename.** Six rows, each carrying its measured value and the evidence file beside it: `TOTAL: 176 PASS, 7 N/A, 0 FAIL` at exit 0 on the single sha `7005a2771aa115e4f4c1284cec7e145739586a4a`; E2 at **2.5146e-08** worst scalar, §3 headline at **4.8962e-09**, `n_comparisons` exact at **7762**; E7 fixed pairing held at **10/10**, p = **0.00098**; **227** files committed at `70e783f`, **147** under `experiments/results/`, a strict superset of attempt 1's **209**, largest admitted file **119,406** bytes. Nothing was recalled — every figure was transcribed from an evidence file in the phase directory.
- **The one conclusion that moved is raised where the author will see it.** The E7 refined pairing went **8/10 (p = 0.05469) → 7/10 (p = 0.17188)**, both figures published in supplement §14 / MF-05. It has its own headed subsection, it carries the finding that `interface_ablation_band.csv` is byte-identical between the two run attempts (md5 `b6515ed77ed04268608b74217716020b`) so the move is a **FIX-02 effect, not a re-run artefact**, and it is **explicitly routed to POST-01 in Phase 30** as a manuscript-side item. §3 edits stay the author's. No manuscript file was opened, read for editing, or written.
- **D-29-10's stop list was evaluated in full and not one item fired.** The E2 same-seed control passed four orders of magnitude clear of its limit; `gate3_git_sha_consistency` PASSED over the **committed** tree, which is the form the stop list cares about; and the third item resolved to a *manuscript*-vs-artifact disagreement rather than an artifact-vs-artifact one — which is Phase 30's, not a blocker.
- **The handoff is unmissable.** A `WHAT REMAINS` section sits at the **top** of the record, above every derivation, listing the five steps in order: cut v2.1.0 (CI `pre-commit` fix, PR merged with a **merge commit never a squash**, `secrets.RELEASE_TOKEN` confirmed, `release.yml` verified to tag v2.1.0), read Record B's **rendered** description then publish, then add Record A's `isSourceOf` back-link by hand, confirm publication preceded submission, report both DOIs to the manuscript session.
- **Twelve forward-carried items, seven of them new todo files.** Each is filed twice — as a numbered item in the record and as a todo whose filename the record names — so neither document is a single point of failure. The manifest repoint carries its **full ten-site table verbatim**, because the entire point of filing rather than doing is that a later session must not re-grep.
- **Criterion 6 was closed honestly.** The author ruled `defer`. The record states the option id, the date, the reason, and every consequence: Task 4 skipped, RUN-05 left `Pending`, the phase closed against criteria 1-5, and deferral named as a legitimate outcome rather than a failure.

## Task Commits

1. **Task 1: Write the phase record** — `0bcf13d` (docs)
2. **Task 2: File what is deliberately carried forward** — `9ea932e` (docs)
3. **Task 3: `checkpoint:decision` — the one-way door** — `da8312c` (docs), recording the author's `defer` ruling, the `WHAT REMAINS` handoff, the E7 routing to POST-01, and the Record A attribution correction
4. **Task 4: author publishes both records** — **SKIPPED**, correctly, under the `defer` branch

## Files Created

- `.planning/phases/29-gate-verification-results-commit/29-PHASE-RECORD.md` — the phase record. Header table, `WHAT REMAINS`, the six-criterion table, a derivation section per criterion, the E7 escalation subsection, test and gate state, D-29-10's stop list evaluated, twelve forward-carried items, and a closing table of what the phase deliberately did not touch.
- Seven todos under `.planning/todos/pending/`, all dated `2026-08-26`:

| Todo | `resolves_phase` | What it carries |
|---|---|---|
| `repoint-the-dataset-manifest-after-the-zenodo-split` | 30 (POST-01) | the ten-site blast-radius table verbatim, the four-frozen-sites warning, both records' sizes/digests/flat roots, the two `loader.py` findings, the promote-not-add-alongside verdict, and a suggested invariant test |
| `publish-record-b-and-add-record-a-back-link` | 29.2 | the five ordered steps, self-contained |
| `no-pull-request-into-main-until-ci-pre-commit-is-scoped` | 29.2 | the 147-artifact rewrite, why it is a blocked merge and not corruption, and the two md5 anchors that must not move |
| `legacy-zenodo-deposit-api-deprecation-posture` | 30 | MEDIUM-confidence community sourcing; the risk is only that a future re-upload needs rework |
| `d4-exact-equality-anchors-are-platform-pinned` | 30 | the one D-29-14 residual needing a new file; the other was already filed as the pytest-xdist todo |
| `phase-30-dependency-still-names-the-passed-2026-08-21-submission-date` | 30 | roadmap hygiene — the same defect criterion 6 was amended away from on 2026-08-25 |
| `state-md-body-format-diverges-from-gsd-state-handlers` | 30 | pre-existing; measured against this project's `STATE.md` headings |

## Decisions Made

1. **Criterion 6 closed as OPEN on the author's ruling, and every consequence enumerated.** A bare option id would have left a later reader unable to distinguish a deliberate deferral from an oversight. The record states that Task 4 was skipped, that RUN-05 stays `Pending`, that the phase closes against criteria 1-5, and that deferral is legitimate — in those words.
2. **RUN-05 was not marked complete.** It requires the results package to be **published** before the paper is submitted. Record B is built, uploaded, byte-verified — and unpublished. Plans 29-04 and 29-07 each had to avoid a premature completion of this same requirement; this is the third refusal.
3. **Three items discovered after the plan was written were filed as todos of their own**, not left as record prose: the Phase 30 date defect, the STATE.md format divergence, and the publish-then-back-link sequence. A numbered item inside a phase record is findable only by someone already reading that record.
4. **The `WHAT REMAINS` section sits above the derivations.** The reader most likely to need it — someone returning cold, possibly in another session — is the one least likely to read to the end.
5. **Nothing was fixed, only filed.** `git diff --quiet -- src/ experiments/ tests/` exits 0 and `git status --porcelain experiments/` is empty. The manifest pin was not repointed, neither `tests/` assertion on `21889922` was changed, and nothing inside the frozen tree was touched.

## Deviations from Plan

### Premises that had changed since the plan was written (recorded, not auto-resolved)

**1. Task 3's options were drafted against "both records unpublished". Record A was already published.**
- **Found during:** Task 3, preparing the checkpoint
- **Issue:** The plan's `checkpoint:decision` reads *"Publish both Zenodo records now, or leave both drafts staged"*. By the time it was reached, the author had already published Record A **by hand, in the Zenodo web UI, between plan 29-07's Task 1 checkpoint and that plan's completion** — under the `sequential` linkage ruling. Only Record B's Publish remained.
- **Handling:** The changed premise was presented **first** at the checkpoint, before the options, rather than the options being restated as written. Not auto-resolved — the decision stayed the author's.
- **Files modified:** none

**2. A constraint that did not exist when the options were drafted: Record B cites `2.1.0`, which does not exist.**
- **Found during:** Task 3
- **Issue:** Record B's metadata `version` field and its packaged README both name `2.1.0`. `origin/main` is 0 commits ahead of `results/rerun-freeze-02`, which is 406 ahead — the release has not been cut. `publish-now` would have minted a permanent record naming a version nobody can install. The plan could not have known this; Phase 29.2 was inserted the same day.
- **Handling:** Surfaced at the checkpoint as the decisive fact. The author ruled `defer` on exactly this basis.
- **Files modified:** none

**3. Task 4 skipped.**
- The plan's Task 3 instructs: *"If `defer` is chosen … **skip Task 4** — the phase closes against criteria 1-5."* Followed exactly. Task 4 is a human-verify gate for a publication that is not happening in this phase.

### Attribution correction applied

The checkpoint message described Record A as published *"mid-29-07"*, which could be read as an automated act. Corrected in the record to: **published by the author, by hand, in the Zenodo web UI, between plan 29-07's Task 1 checkpoint and that plan's completion.** The record now states explicitly that **no automation published anything at any point** — `grep -v '^\s*#' scripts/zenodo_upload.py | grep -c '/actions/'` still returns **0**, and the token carries `deposit:write` only.

---

**Total deviations:** 0 auto-fixed under Rules 1-3. Three changed premises recorded and escalated rather than resolved unilaterally, plus one attribution correction. No prohibition was touched.

## Issues Encountered

**Two `state` handlers do not work against this project's `STATE.md`, and were not worked around by reshaping it.** `gsd-tools query state.advance-plan` and `state.update-progress` expect `Current Plan` / `Total Plans` / `Progress` fields in the document **body**; this project carries them in the **frontmatter**, and the body's headings are `## Project Reference`, `## Current Position`, `## Roadmap Summary (v2.1)`, `## Deferred Items`, `## Accumulated Context`, `## Session Continuity`, `## Performance Metrics` — none of which the handlers can parse. Verified by reading the file, not inferred from the error. This predates Phase 29 and several of its plans hit it. `STATE.md` was updated by hand instead; rewriting a project's state document to satisfy a parser is not a change one plan should make unilaterally, and `## Current Position` holds hundreds of lines of hand-written narrative the handler format does not accommodate. Filed as a todo.

**The plan's Task 1 verify block and its acceptance criteria disagreed on one literal.** The `<automated>` block does not list `119406`; the acceptance criteria ask for `119406` **or** `119,406`. The record was written with the comma form (which is how `29-commit-manifest.txt` presents it in prose) and the bare form was added alongside it — `stat` reads `119406` — so both checks pass and neither reading is privileged.

## Known Stubs

None. This plan authored one record and seven todos; every number in the record was transcribed from an evidence file produced by an earlier plan in this phase, and every todo names a real file, a real line number, or a real measured value.

The one intentional incompleteness is **criterion 6, recorded as OPEN**. That is not a stub: it is the author's dated ruling, with what remains named in five ordered steps, an owning phase (29.2), and a todo of its own.

## Threat Flags

None. This plan created no network endpoint, no auth path, no file-access pattern and no schema at a trust boundary. Its threat register was implemented rather than extended:

| Threat | How it was mitigated here |
|---|---|
| T-29-52 repudiation / the phase record | Every criterion row names the evidence file its value came from; a literal-presence gate asserts all fourteen load-bearing numbers are in the document rather than paraphrased |
| T-29-53 tampering / Publish | Nothing was published by automation; `grep -v '^\s*#' scripts/zenodo_upload.py \| grep -c '/actions/'` returns **0**; the decision was returned to the author as a blocking checkpoint |
| T-29-54 repudiation / criterion 6 | Closed as OPEN on the author's explicit, dated ruling with its reason recorded; no inference was made, and RUN-05 was left `Pending` |
| T-29-55 information disclosure / deferred work | The manifest repoint carries its full ten-site table into the todo, with the promote-not-add-alongside warning travelling alongside it |
| T-29-56 tampering / prior records | No prior record was rewritten. Superseded readings are annotated with dated notes; the record's own rule is restated in its opening paragraph |
| T-29-57 tampering / `main` branch CI | The no-pull-request constraint is filed with its reason (147 artifacts whitespace-rewritten, 143 missing final newlines, 439 trailing-whitespace hits), so a future merge is a decision rather than an accident |
| T-29-58 elevation / Zenodo edit after publish | Record A's `isSourceOf` back-link is named as a manual UI task in three places — the record's `WHAT REMAINS`, its open-items section, and a todo — with the note that editing published metadata neither cuts a new version nor changes the DOI |

## User Setup Required

None for this plan. **Five actions remain outstanding and are deliberately not automatable** — they are `WHAT REMAINS` at the top of `29-PHASE-RECORD.md` and the body of `2026-08-26-publish-record-b-and-add-record-a-back-link.md`: cut v2.1.0, read then publish Record B at `https://zenodo.org/deposit/22117061`, add Record A's back-link at `https://zenodo.org/records/22116461`, confirm the ordering against submission, and report both DOIs to the manuscript session.

## Next Phase Readiness

**Phase 29 is complete against success criteria 1-5.** Criterion 6 is recorded as OPEN on the author's `defer` ruling, which the plan names as a legitimate outcome.

- **Phase 29.2 is unblocked and is the owner of what remains.** It has the ordered sequence, the CI defect with its exact cause, the merge-commit-never-squash constraint with its silent-failure mode, and both records' handles.
- **Phase 30 / POST-01 has three inputs written down**: the E7 refined-pairing move as a manuscript-side item, the manifest repoint with its ten sites, and the roadmap date defect on its own dependency.
- **RUN-03 and RUN-04 are `Complete`** in `REQUIREMENTS.md` (closed by plans 29-06 and 29-05 respectively). **RUN-05 stays `Pending`**, correctly.
- **Nothing is blocked, and nothing irreversible was done.** Branch still `results/rerun-freeze-02`; `git status --porcelain experiments/` empty; no PR opened; no record published by automation.

---
*Phase: 29-gate-verification-results-commit*
*Completed: 2026-08-26*

## Self-Check: PASSED

All nine claimed files exist on disk (`29-PHASE-RECORD.md`, `29-08-SUMMARY.md`, and the seven
`2026-08-26-*` todos under `.planning/todos/pending/`), and all four claimed commits resolve in
`git log --oneline --all` (`0bcf13d`, `9ea932e`, `da8312c`, `cbf56a3`). The record's fourteen
load-bearing literals were re-grepped after the final edit and are all present.
`git diff --quiet -- experiments/ src/ tests/` exits 0.
