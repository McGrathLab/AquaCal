---
phase: 25-degeneracy-classification-claim-licensing
plan: 07
subsystem: policy-and-gates
tags: [degen-04, d-04, d-05, gate-scope, degeneracy, e4, e6, observability]
requires:
  - ".planning/probes/2026-08-17-degeneracy-classification/FINDINGS.md"
  - "42d9efb (plan 25-06's classification of the 198)"
provides:
  - "The degeneracy-gate scope decision, settled: SYNTHETIC-ONLY by design (D-04)"
  - "The authored-vs-given-geometry rationale at all three gate sites"
  - "A recorded tripwire: a materially populated camera_model_failure bucket in Phase 29's frozen table"
  - "Behavioural pinning of the count > 0 predicate at the 0/1 boundary (D-05)"
affects:
  - "src/aquacal/calibration/_observability.py"
  - "experiments/e4_benchmark_grid.py"
  - "experiments/e6_generalization_sweep.py"
  - "tests/unit/test_experiment_inertness.py"
  - "tests/unit/test_experiments_e4.py"
  - "tests/unit/test_experiments_e6.py"
  - ".planning/todos/done/2026-08-15-decide-degeneracy-gate-scope-for-real-rig-runs.md"
tech-stack:
  added: []
  patterns:
    - "`# ---` banner comment block in _observability.py: state the rule, the failure it prevents, and what must never be restored"
    - "source-text assertion scoped by FILENAME so the asserting test's own prose is out of scan range"
    - "behavioural boundary test at the smallest nonzero count, not a source-text regex"
key-files:
  created:
    - ".planning/phases/25-degeneracy-classification-claim-licensing/25-07-SUMMARY.md"
  modified:
    - "src/aquacal/calibration/_observability.py"
    - "experiments/e4_benchmark_grid.py"
    - "experiments/e6_generalization_sweep.py"
    - "tests/unit/test_experiment_inertness.py"
    - "tests/unit/test_experiments_e4.py"
    - "tests/unit/test_experiments_e6.py"
    - ".planning/todos/done/2026-08-15-decide-degeneracy-gate-scope-for-real-rig-runs.md"
decisions:
  - "The degeneracy gate stays synthetic-only; real-rig runs are removed from its scope, not gated leniently"
  - "The decision rests on the dominant failure mechanism, never on a count -- the published count is a cross-stage sum"
  - "Tripwire recorded: camera_model_failure (NAN_REASON_BEHIND_CAMERA with positive h_q) materially populated in Phase 29's frozen table"
  - "Predicate untouched (D-05); the boundary is pinned behaviourally at counts 0 and 1 rather than by source regex"
metrics:
  duration: "~50 min"
  completed: "2026-08-18"
---

# Phase 25 Plan 07: Degeneracy-Gate Scope Decision Summary

The deferred degeneracy-gate scope question is settled on mechanism: the gate stays synthetic-only
because authored geometry makes an unprojectable observation a malformed scenario while given
geometry makes it a deployment fact — with the rationale written at all three gate sites, a tripwire
recorded, and the `count > 0` predicate pinned behaviourally so the scope call cannot be mistaken
for permission to loosen it.

## What Was Built

**The premise was checked first and holds.** `.planning/probes/2026-08-17-degeneracy-classification/FINDINGS.md`
reports all flagged observations in one bucket, `above_interface`; `camera_model_failure` is
**empty, not small**. That is bucket (a), so D-04's synthetic-only branch is the live one and the
plan's premise was not falsified. Had bucket (b) been populated, this plan would have stopped.

**Task 1 — the library site.** A new `# ---` banner block in
`src/aquacal/calibration/_observability.py`, placed immediately after the phase-24 "Degeneracy split
vocabularies" block (which already forward-declared this phase) and before `_DEGENERACY_CAUSES`. It
carries four things in the surrounding blocks' register: the decision; the authored-vs-given argument;
why it was settled on which failure kind dominates rather than on a count (the published count is a
sum accumulated across stages through one un-reset `discard_stats` dict, which invalidated the
original 0.268% arithmetic outright); and the tripwire. It closes with the "what must never be
restored" note — the predicate is exactly `count > 0 -> degenerate` with a smoke carve-out, and
"real rigs tolerate a few" is an argument about real rigs, which this decision has *already removed
from the gate's scope*, not a reason to loosen the synthetic one.

The block is prose only. No vocabulary, constant or accessor entered the library: D-06's boundary
holds, the taxonomy stays in `experiments/_degeneracy.py`, and the probe's numbers are marked
**PROVISIONAL** with Phase 29's frozen table named as the sole source (D-02). The probe is cited by
path; no count from it was copied in.

**Task 2 — both harness guards, and the todo.** The rationale is compressed onto E4's existing
D-19.3-11 comment in `run_grid_cell`, and onto a lead-in note covering all three branches of E6's
gate in `run_configuration`. Both point at the library block for the long form and at the probe path
for the evidence rather than duplicating either. The deferred todo moved to `.planning/todos/done/`
with a `## Resolved` block naming the decision, the evidence, the three code sites and the tripwire.

**Task 3 — the pins.** `test_gate_scope_rationale_present_at_all_three_sites` in
`tests/unit/test_experiment_inertness.py` asserts the decision, both halves of the geometry argument,
the tripwire, the frozen-table reference, the probe path and `D-04` in each of the three files.
Behavioural gate tests were added to `tests/unit/test_experiments_e4.py` and
`tests/unit/test_experiments_e6.py`, plus an E4 smoke-path test.

## Key Decisions

**Settled on mechanism, with the count explicitly disowned.** The count is a cross-stage sum and
provisional besides; the decision rests on the fact that every flagged observation was a corner
above the water surface — a data-geometry condition on a run whose accuracy was fine. A real-rig
gate failing on a nonzero count would have failed that run. This is the sentence the rationale
carries at all three sites.

**The boundary count is what pins D-05, not the source regex.** The pre-existing
`test_degenerate_gate_source_is_a_smoke_condition_not_a_threshold` tests already regex the source,
and the pre-existing behavioural tests use count 3. A softening to, say, `> 2` would keep every one
of those passing while letting count 1 through. The new tests therefore exercise **exactly 1**,
which is the case a threshold breaks first. Written behaviourally, per the plan.

**The source-text test is scoped by filename, which is the mitigation for a defect this repo already
hit.** `_count_references` in the same module once stripped `#` lines and counted substrings, and a
docstring correctly *asserting* an invariant failed the gate that checked it. The new assertion reads
only the three named files; this test module is not one of them, so nothing in its own docstring can
satisfy or falsify it. The polarity is also the safe one — the phrases are required present, not
absent. Both points are stated in a comment inside the test, as the plan required.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] E6 boundary test replayed a cached checkpoint**

- **Found during:** Task 3
- **Issue:** The first draft called `m.run_configuration` three times against one `tmp_path`. E6
  caches an outcome per `config_key` under `out_dir/e6_configs/`, so the second call returned the
  first call's recorded `"degenerate"` outcome instead of re-exercising the gate at count 0 — the
  test failed on an assertion that was in fact correct about the gate.
- **Fix:** Each invocation now gets its own sub-directory (`count_1`, `count_0`, `smoke_{n}`), with a
  comment recording why. No production code was involved.
- **Files modified:** `tests/unit/test_experiments_e6.py`
- **Commit:** `dee5b64`

**2. [Rule 3 - Blocking] E6 comment perturbed a source-text invariant it was describing**

- **Found during:** Task 2
- **Issue:** The E6 note originally quoted the predicate literally as `` `n_degenerate > 0` ``, which
  raised that string's occurrence count in the file from 2 to 3. The plan's own acceptance criterion
  pins that count, and the existing threshold regex test scans the same text. A comment restating an
  invariant must not move the count that measures it — the same class of trap as the
  `_count_references` incident.
- **Fix:** Reworded to `"any nonzero count is degenerate"`. Counts verified back at 2 and 2.
- **Files modified:** `experiments/e6_generalization_sweep.py`
- **Commit:** `54d8586`

**3. [Rule 3 - Blocking] `git mv` staged the pre-append blob**

- **Found during:** Task 2
- **Issue:** The `## Resolved` text was appended to the todo *before* `git mv`, and `git mv` stages
  the rename from the existing index entry — so the first commit recorded a 100%-similarity rename
  with none of the new content, and the two experiment files were left unstaged because the same
  `git add` invocation included a path that no longer existed and so added nothing.
- **Fix:** Re-staged all three paths and amended the commit (unpushed, mine). Final commit is
  3 files / 78 insertions.
- **Commit:** `54d8586`

### Out of scope, not fixed

None. The worktree base was stale (`d27bda7`) at spawn and was reset to `42d9efb` per the mandated
check before any work began.

## Verification

Run with `PYTHONPATH` pointed at this worktree's `src`, confirmed via
`python -c "import aquacal; print(aquacal.__file__)"`. The full suite was **not** run — it is the
orchestrator's post-merge gate.

- `tests/unit/test_observability.py`, `tests/unit/test_discard_accounting.py` — **81 passed**
- `tests/unit/test_experiment_inertness.py`, `tests/unit/test_experiments_e4.py`,
  `tests/unit/test_experiments_e6.py` — **126 passed** (3 new)
- `tests/unit/test_e6_band_mode.py`, `test_experiments_provenance.py`, `test_experiments_render.py`,
  `test_experiments_e5.py` — **350 passed, 25 skipped** (the other modules that scan these sources)

Invariants checked directly:

- `git diff` over all three source files: `grep -c "^+[^#+ ]"` → **0**. Every added line is a comment.
- `len(DISCARD_KEYS), len(_DEGENERACY_CAUSES), len(_DISCARD_STAGES)` → `32 3 3`, unchanged.
- `grep -c "n_degenerate > 0"` → **2** in E4 and **2** in E6, both equal to their pre-edit values.
- No `status_reason` string, predicate, constant or vocabulary changed.

## Known Stubs

None.

## Threat Flags

None. The changes are comments and tests in a local scientific CLI; no trust boundary is touched.

## Commits

| Commit | Task | What |
|---|---|---|
| `5925bb3` | 1 | The gate-scope banner block in `_observability.py` |
| `54d8586` | 2 | E4/E6 guard comments; todo resolved and moved to `done/` |
| `dee5b64` | 3 | Source-text presence test + behavioural boundary tests |

## Self-Check: PASSED

- `src/aquacal/calibration/_observability.py` — FOUND, block present
- `experiments/e4_benchmark_grid.py` — FOUND, rationale present
- `experiments/e6_generalization_sweep.py` — FOUND, rationale present
- `tests/unit/test_experiment_inertness.py` — FOUND, new test present and passing
- `.planning/todos/done/2026-08-15-decide-degeneracy-gate-scope-for-real-rig-runs.md` — FOUND
- `.planning/todos/pending/2026-08-15-...` — correctly ABSENT
- Commits `5925bb3`, `54d8586`, `dee5b64` — all FOUND in `git log`

## Notes for the Orchestrator

STATE.md and ROADMAP.md were deliberately **not** touched, per the dispatch instruction.

One thing worth carrying: this plan settles the *policy*, and the tripwire it records is a genuine
obligation on **Phase 29**. When the frozen table lands, someone must look at the
`camera_model_failure` bucket specifically. If it is materially populated, the rationale now sitting
at three code sites is void and the gate's scope must be re-decided — the text says so explicitly at
each site, but it is not self-enforcing.
