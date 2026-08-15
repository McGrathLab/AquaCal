---
gsd_state_version: 1.0
milestone: v2.0
milestone_name: Publication Prep
status: milestone_complete
stopped_at: v2.0 closed 2026-08-15; next milestone not yet defined
last_updated: "2026-08-15T13:30:00.000Z"
last_activity: 2026-08-15 -- milestone v2.0 Publication Prep closed and archived; no release cut
progress:
  total_phases: 12
  completed_phases: 10
  total_plans: 106
  completed_plans: 106
  percent: 100
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-08-15)

**Core value:** Accurate refractive camera calibration from standard ChArUco board
observations — researchers can `pip install aquacal`, point it at their videos, and get a
calibration result they trust.

**Current focus:** Between milestones. The next one is agreed in shape but not yet defined:
clean up the experiments, fix the accumulated defects, then one final full experiment-suite
re-run at a single code version for the paper. Run `/gsd:new-milestone`. Phase numbering
continues from **23**.

## Current Position

**Milestone v2.0 Publication Prep is CLOSED (2026-08-15).** 10 of 12 phases executed,
106/106 plans complete, 51 of 55 requirements satisfied. Archived to
`.planning/milestones/v2.0-ROADMAP.md` and `v2.0-REQUIREMENTS.md`.

**No release was cut at close, by user decision.** The releases that exist — v2.0.0 and
v2.0.1, tagged on GitHub 2026-08-11 — came out of Phase 21, not out of the close. No git tag
was created for the milestone itself.

**Label note:** the milestone was planned as "v1.9" and is archived as **v2.0**, because Phase
19.3 made `board` a required parameter of two public exports and forced a major bump. Any older
planning document saying "v1.9" means this milestone.

**Deferred and carried forward, not dropped:** Phase 20 (Refractive Index Helper, INDEX-01..03)
— deferred 2026-08-07 on measured evidence, MF-13. Phase 22 (Release Cut, DOCS-07) — pre-empted
by the v2.0.0/v2.0.1 releases; the manuscript C1 cell and the DOI citation stay the user's work.

**Hard deadline still live:** revised SoftwareX manuscript due **2026-08-21**.

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
| todo | 17 pending todos in `.planning/todos/pending/` | the experiment-cleanup backlog; see below |
| verification_gap | Phase 04 (`04-VERIFICATION.md`) | gaps_found |
| verification_gap | Phase 10 (`10-VERIFICATION.md`) | human_needed |
| verification_gap | Phase 19.2 (`19.2-VERIFICATION.md`) | human_needed |
| requirement | INDEX-01, INDEX-02, INDEX-03 | Phase 20, deferred on MF-13 |
| requirement | DOCS-07 | Phase 22, manuscript-side |

**Three pending todos look already discharged and want confirming before the next milestone
plans around them** — none were deleted, because verifying is the user's call:

- `2026-08-05-pin-opencv-below-5-0` — `pyproject.toml:40` now reads `opencv-python==4.13.*`
  (`fa9ec3a`), which is tighter than the todo asked for
- `2026-02-24-upload-new-zenodo-dataset-with-image-based-inputs` — Phase 21 published record
  21889922
- `2026-08-05-verify-non-refractive-baseline-supports-paper-claims` — plan 21-12 did exactly this

The remaining 14 are live, and most of them are the experiment defects the next milestone exists
to fix — including the three filed 2026-08-14 (E1 absolute-accuracy claims, E6 z-error sign and
gauge correction, per-camera gauge decomposition) and the five filed 2026-08-15.

## Accumulated Context

### Roadmap Evolution

v2.0 inserted five decimal phases mid-milestone, each because the previous one exposed the next
defect. Full narrative in `.planning/milestones/v2.0-ROADMAP.md` § Milestone Summary and in
`.planning/RETROSPECTIVE.md`. Not duplicated here.

### Decisions

Logged in PROJECT.md § Key Decisions. The load-bearing one from v2.0: **D-19.3-17 — an
experiment may carry an accuracy claim only where a measured seed band supports it.**

### Blockers/Concerns

- **MF-19** — §3's numbers predate the current library. This is the manuscript-level blocker and
  the direct reason the next milestone ends in a single-version suite re-run.
- **The DOI freezes the reference numbers.** Section 3, the archive's `reference_outputs/`, and
  the tutorial's expected-value table are a matched set of three. Any change that moves the
  real-rig numbers breaks all three and requires cutting another Zenodo version. Nothing in the
  deferred batch re-runs E2, so the archive is currently safe — but a full suite re-run must
  decide deliberately whether E2 is in scope.

## Session Continuity

Last session: 2026-08-15 — milestone closed and archived.
Stopped at: between milestones, nothing in flight.
Next: `/gsd:new-milestone`.

Prior position (Phase 21 close) is preserved in `.planning/HANDOFF.json` and in
`.planning/milestones/v2.0-ROADMAP.md`.
