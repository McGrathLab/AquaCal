---
phase: 18-documentation-corrections-stage-model-reconciliation
plan: 02
subsystem: docs
tags: [vocabulary, stage-model, best-first, manuscript-reconciliation]

# Dependency graph
requires:
  - phase: 18-documentation-corrections-stage-model-reconciliation
    provides: 18-CONTEXT.md (D-02, D-04, D-05 revised, D-06, D-07 resolved, D-23 new) and 18-RESEARCH.md (superseded Q2/Q4 findings)
provides:
  - The confirmed vocabulary contract with verbatim manuscript citations
  - Per-plan verdict for 18-05, 18-06, 18-07, 18-08
  - Explicit note that 18-RESEARCH.md Q2's four-stage/BFS conclusion is superseded
affects: [18-05, 18-06, 18-07, 18-08]

# Tech tracking
tech-stack:
  added: []
  patterns: []

key-files:
  created: [.planning/phases/18-documentation-corrections-stage-model-reconciliation/18-02-SUMMARY.md]
  modified: []

key-decisions:
  - "D-05 (REVISED): ex-Stage-4 is 'Stage 3's second pass, with intrinsics unlocked' in prose/console, matching main.tex:215,218 verbatim, not the earlier inferred 'optional intrinsic pass'"
  - "D-07 (RESOLVED): vocabulary confirmed against the live manuscript (OneDrive main.tex/supplement.tex), not the stale Desktop\\main.pdf which caused the original false alarm"
  - "D-23 (NEW): auxiliary-camera registration carries no stage number at all — main.tex excludes it from Stages 2 and 3 and frames it as a post-hoc 6-DOF/10-DOF refinement"

patterns-established: []

requirements-completed: [DOCS-02, DOCS-06]

# Metrics
duration: 12min
completed: 2026-07-24
---

# Phase 18 Plan 02: Confirmed Vocabulary Contract Summary

**Recorded the confirmed three-stage / best-first vocabulary as a concrete string contract, grounded in verbatim `main.tex`/`supplement.tex` citations re-spot-checked at execution time, superseding the stale-PDF-derived four-stage/BFS finding in 18-RESEARCH.md.**

## Performance

- **Duration:** 12 min
- **Started:** 2026-07-24
- **Completed:** 2026-07-24
- **Tasks:** 1
- **Files modified:** 0 (repo source), 1 planning artifact created

## Accomplishments
- Re-confirmed both manuscript citations live at execution time via grep, rather than trusting CONTEXT.md's prior transcription
- Recorded the exact target strings the four rename plans (18-05..18-08) will write, closing the vocabulary question this plan was originally a blocking checkpoint for
- Marked 18-RESEARCH.md's Q2 (four-stage/BFS) as superseded, with the stale artifact named explicitly so it is not re-derived

## Task Commits

Each task was committed atomically:

1. **Task 1: Record the confirmed vocabulary contract** - (this SUMMARY.md, committed as this plan's sole artifact; no repository source files were touched, per the plan's `files_modified: []` frontmatter)

**Plan metadata:** committed alongside this SUMMARY.md

_Note: This plan modifies no repository source files. Its entire deliverable is this SUMMARY.md itself._

## Files Created/Modified
- `.planning/phases/18-documentation-corrections-stage-model-reconciliation/18-02-SUMMARY.md` - the vocabulary contract this document is

## Decisions Made

**This plan does not make new decisions — it records and grounds decisions already locked in `18-CONTEXT.md` (D-05 revised, D-07 resolved, D-23 new).** No new deviation was needed; both required spot-checks passed on the first attempt.

## The Confirmed Vocabulary Contract

### Spot-check verification (re-run at execution time, both matched)

```
$ grep -n "Three-stage calibration" "/c/Users/tucke/OneDrive - Georgia Institute of Technology/Thesis/Spinoffs/papers/aquacal/main.tex"
208:\noindent\textbf{Three-stage calibration.}

$ grep -n "best-first traversal" "/c/Users/tucke/OneDrive - Georgia Institute of Technology/Thesis/Spinoffs/papers/aquacal/supplement.tex"
483:$\mathbf t = \mathbf 0$), a best-first traversal alternates between camera and frame
```

Both citations are confirmed against the live manuscript source
(`C:\Users\tucke\OneDrive - Georgia Institute of Technology\Thesis\Spinoffs\papers\aquacal\`),
**not** the stale `C:\Users\tucke\Desktop\main.pdf` (a 2026-06-15 pre-revision export, code
version `v1.6.0`, that says the opposite on both counts — four stages, BFS throughout).

### Stage model — three stages, confirmed (D-04, D-07)

- **Stage 1** = in-air intrinsic calibration
- **Stage 2** = extrinsic initialization (best-first pose-graph traversal)
- **Stage 3** = joint refractive bundle adjustment (extrinsics + `water_z` + board poses)

Verbatim citation: `main.tex:208` — `\noindent\textbf{Three-stage calibration.}`

### Prose/console label for the ex-Stage-4 — "Stage 3's second pass, with intrinsics unlocked" (D-05, REVISED)

Exact target string: **"Stage 3's second pass, with intrinsics unlocked"**

This supersedes the earlier inferred "optional intrinsic pass" wording. The manuscript's
own words are (`main.tex:215`) "Stage~3 runs a second time, warm-started with each camera's
focal length and principal point unlocked ($4N$ further parameters, distortion held fixed)"
and (`main.tex:218`) "The second pass is optional because Stage~1 already constrains the
intrinsics tightly." It is **not** "Stage 4", and it is not the earlier inferred phrase.

### Machine key form — `stage3_intrinsic_pass` (D-06)

Replacing, with **no backward-compat shim** (D-03):

- `timings["stage4_joint_refinement"]` → `timings["stage3_intrinsic_pass"]`
- `internals/calibration_stage4.json` → `internals/calibration_stage3_intrinsic_pass.json`
- `internals/trace_stage4.csv` → `internals/trace_stage3_intrinsic_pass.csv`
- conditioning/dump `stage` tag `"stage4"` → `"stage3_intrinsic_pass"`

`"stage3"` and `"stage3_rerun"` are **unaffected** — they are unrelated to the ex-Stage-4 rename.

### Traversal term — "best-first" everywhere except the genuine BFS carve-out (D-02, D-11)

Exact target string: **"best-first"**

Verbatim citation: `supplement.tex:483-486` — "a best-first traversal alternates between
camera and frame nodes, expanding next whichever node was reached by the highest-corner-count
observation (rather than whichever lies fewest hops from the reference, as a breadth-first
order would)." `main.tex` contains **zero** occurrences of "BFS" or "breadth-first".

`_find_connected_components` (`extrinsics.py:200,208`) is a **hard carve-out** — it genuinely
is breadth-first and is correctly named. It is untouched by the sweep.

### Auxiliary-camera registration — no stage number (D-23, NEW)

Exact target string: **"Auxiliary camera registration"** — with **no stage number** in the
label. The DOF distinction (6-DOF vs 10-DOF) belongs in the message body, not the label.
The existing stage-agnostic timing key `auxiliary_registration` is retained unchanged.

Verbatim citation: `main.tex:222-224` — auxiliary cameras are excluded "from Stages~2 and~3",
then "registered post-hoc against the frozen board placements and `water_z` via refractive
Perspective-n-Point (PnP) initialization, followed by either a 6-DOF refinement ... or a
10-DOF refinement that adds focal length and principal point."

This supersedes the research pass's recommendation (18-RESEARCH.md Q3) to collapse
`pipeline.py`'s conditional "Stage 4b"/"Stage 3b" label to an unconditional "Stage 3b" — the
paper does not number this step at all, so no stage-numbered label of any form is correct.

### Per-plan verdict

| Plan | Verdict |
|------|---------|
| 18-05 | Proceeds as planned, taking the D-05 revised string ("Stage 3's second pass, with intrinsics unlocked") and the `stage3_intrinsic_pass` machine key form |
| 18-06 | Proceeds as planned, taking the D-23 string ("Auxiliary camera registration", no stage number, DOF distinction in message body) |
| 18-07 | Proceeds as planned — no string revision from this plan; implements the best-first/BFS sweep and pose-graph figure work per the existing CONTEXT.md decisions |
| 18-08 | Proceeds as planned — no string revision from this plan |

DOCS-01, DOCS-03, and DOCS-04 were never blocked on this vocabulary question and are
unaffected by this plan's findings.

## 18-RESEARCH.md Q2 — SUPERSEDED

`18-RESEARCH.md`'s "Answers" section, Q2, concluded (based on reading
`C:\Users\tucke\Desktop\main.pdf`) that the manuscript describes a **four**-stage pipeline
and uses **BFS** terminology throughout (abstract, Figure 1 caption, Figure 2 title "Stage 2:
BFS Pose Graph", body prose), directly contradicting the CONTEXT.md-locked vocabulary.

**That conclusion is superseded.** The Desktop PDF is a stale 2026-06-15 export (metadata
still lists code version `v1.6.0`). The live manuscript source — read directly for this plan,
at `C:\Users\tucke\OneDrive - Georgia Institute of Technology\Thesis\Spinoffs\papers\aquacal\`
— confirms the originally locked three-stage / best-first vocabulary exactly as recorded
above. A future reader of `18-RESEARCH.md` should treat its Q2 conclusion (and the related
Q4 negative-result framing, also superseded per `18-CONTEXT.md`'s D-07 block) as historical
record of a false alarm, not as an open question requiring re-derivation. Do not substitute
`C:\Users\tucke\Desktop\main.pdf` for the OneDrive `.tex` sources in any future work on this
phase or its successors.

## Deviations from Plan

None - plan executed exactly as written. Both required grep spot-checks (`"Three-stage
calibration"` in `main.tex`, `"best-first traversal"` in `supplement.tex`) returned a match
on the first attempt, so no STOP-and-report branch was triggered.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

The vocabulary contract is settled and grounded. Plans 18-05, 18-06, 18-07, and 18-08 can
proceed using the exact target strings recorded above without re-deriving them from
CONTEXT.md or the manuscript. No blockers.

---
*Phase: 18-documentation-corrections-stage-model-reconciliation*
*Completed: 2026-07-24*
