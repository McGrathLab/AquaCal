---
gsd_state_version: 1.0
milestone: v2.1
milestone_name: Clean Experimental Suite
status: planning
last_updated: "2026-08-15T15:03:36.414Z"
last_activity: 2026-08-15
progress:
  total_phases: 0
  completed_phases: 0
  total_plans: 0
  completed_plans: 0
  percent: 0
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-08-15)

**Core value:** Accurate refractive camera calibration from standard ChArUco board
observations — researchers can `pip install aquacal`, point it at their videos, and get a
calibration result they trust.

**Current focus:** Milestone **v2.1 Clean Experimental Suite**, defining requirements. Land every
experiment-suite fix that changes what the suite measures, records, or can claim; freeze one sha;
hand a complete full-suite driver to a larger Linux machine for the run; reconcile the returned
single-version results. **E2 is in the re-run.** Phase numbering continues from **23**.

## Current Position

Phase: Not started (defining requirements)
Plan: —
Status: Defining requirements
Last activity: 2026-08-15 — Milestone v2.1 started

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
| todo | 15 pending todos in `.planning/todos/pending/` | the experiment-cleanup backlog; see below |
| verification_gap | Phase 04 (`04-VERIFICATION.md`) | gaps_found |
| verification_gap | Phase 10 (`10-VERIFICATION.md`) | human_needed |
| verification_gap | Phase 19.2 (`19.2-VERIFICATION.md`) | human_needed |
| requirement | INDEX-01, INDEX-02, INDEX-03 | Phase 20, deferred on MF-13 |
| requirement | DOCS-07 | Phase 22, manuscript-side |

**Three todos were verified complete against the tree and closed 2026-08-15** (`d5eba65`) — the
Zenodo dataset upload, the OpenCV pin (landed tighter, as `==4.13.*`), and the band-sidecar
collision (band-owned `e{1,5,6,7}_seed_band_provenance.json`). Each carries a `## Resolved` block
in `.planning/todos/done/` naming the evidence.

**A fourth was closed by author decision the same day:**
`2026-08-05-verify-non-refractive-baseline-supports-paper-claims`. Its titled question is settled
by MF-18 (at unit index the refractive projector *is* the pinhole projector, so the baseline is
converged and `main.tex:268`'s "sole experimental variable" framing stands). Its two residual
steps have owners: step 2 → `2026-08-15-degeneracy-counter-is-unobservable-…`, and step 3 →
`2026-08-15-pin-water-z-in-e1-non-refractive-arm`, which is the same experiment with a better
rationale and has **already been measured** (guard count 14,949 → 0, optimality 9e+02 → 5e-01,
reconstruction numbers reproduced to ~4 significant figures).

**The misleading degeneracy now has a root cause and a fix.** `water_z` is an **exact null
direction** in the `n_water = 1.0` arm — cost constant to 13 significant figures over a 1.5 m
sweep while the guard count climbs to 14,949. The solver is estimating a parameter that provably
cannot influence the fit. `2026-08-15-pin-water-z-in-e1-non-refractive-arm` pins it, arm-locally,
and explicitly overrides the HANDOFF deferral gate: the author decided 2026-08-15 that it lands
**before** the 2026-08-21 submission, because the shift is −0.019% against a manuscript that
quotes 2–3 significant figures. **Do not pin `water_z` in the refractive arm** — there it is
genuinely observable, and pinning inflates the headline ratio to a flattering 168×.

The remaining 15 are live, and most are the experiment defects the next milestone exists to fix —
including the three filed 2026-08-14 and the seven filed 2026-08-15.

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
