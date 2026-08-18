---
phase: 25-degeneracy-classification-claim-licensing
verified: 2026-08-18T17:47:40Z
status: passed
score: 4/4 success criteria verified
overrides_applied: 0
---

# Phase 25: Degeneracy Classification & Claim Licensing — Verification Report

**Phase Goal:** Two open questions blocking manuscript language — what the 198 unprojectable
production-rig observations are, and what domain E1's accuracy claim may state — are answered and
recorded before the frozen run, so neither becomes a mid-run discovery.
**Verified:** 2026-08-18T17:47:40Z
**Status:** passed
**Re-verification:** No — initial verification

## Goal Achievement

### Success Criteria (from ROADMAP.md)

| # | Criterion | Status | Evidence |
|---|-----------|--------|----------|
| 1 | The 198 unprojectable observations are classified into named categories, finding recorded so the manuscript can disclose the count and say what it is | VERIFIED | `.planning/probes/2026-08-17-degeneracy-classification/FINDINGS.md`: all 198 classify to `above_interface` (`nan_reason=2`), the other two buckets are empty. Two independent counters agree (sidecar row count, Phase 24's aggregate counter). `experiments/_degeneracy.py` implements `OBSERVATION_BUCKETS`/`observation_bucket`/`classify_degenerate_observations` keyed strictly off the imported `NAN_REASON_*` codes — confirmed by grep: `h_q_m >` / `h_q_m <` occurs 0 times in the classifier, and a test (`test_classify_separates_camera_model_failure_by_code_not_geometry`) pins two rows at an identical positive `h_q_m` with different codes landing in different buckets. |
| 2 | The finding unblocks (or explicitly leaves blocked) the deferred degeneracy-gate scope decision for real-rig runs | VERIFIED | Settled on mechanism (D-04): the gate stays synthetic-only. The rationale — authored-vs-given geometry, why mechanism not count, and the `camera_model_failure` tripwire — is written verbatim at all three code sites: `src/aquacal/calibration/_observability.py:84-135`, `experiments/e4_benchmark_grid.py` (D-04 comments at `:979-988` and elsewhere), `experiments/e6_generalization_sweep.py:1105-1115`. The deferred todo moved to `.planning/todos/done/2026-08-15-decide-degeneracy-gate-scope-for-real-rig-runs.md`. The synthetic gate predicate is untouched: `count > 0` (`n_degenerate > 0`) still appears literally in both harnesses (D-05 held). |
| 3 | E1's seed band gains a `noise_std` axis, `n_cameras` geometry axis explicitly marked skipped, so promoted absolute-accuracy numbers carry a stated domain (rescoped by D-21: axis + two-seed probe here, ten-seed band of record is Phase 28's) | VERIFIED | `NOISE_LEVELS = [0.25, 0.5, 0.82, 1.2]` present in `experiments/e1_refractive_comparison.py`, nested inside `_run_band`/`_runner`; `noise_std` present in **both** `BAND_KEY_COLUMNS` and `PARAMETER_BAND_KEY_COLUMNS` (confirmed by grep at lines 325/344); `--smoke` collapses the axis to `[None]` (`noise_levels = [None] if smoke else NOISE_LEVELS`, line 1091). `n_cameras` skip is explicitly documented in-source (lines 206-216) rather than silently omitted. The STATED DOMAIN sentence is in the module docstring (line 64) and forward-looking, correctly deferring the establishing band to Phase 28. The two-seed probe ran and is committed at `.planning/probes/2026-08-18-e1-noise-axis/FINDINGS.md` (128/192 rows, 4 distinct noise levels, zero duplicate keys — confirms both key-list edits were necessary). Committed `experiments/results/exp1_band.csv` and `exp1_parameter_band.csv` verified still 160/240 data rows (161/241 with header) with **no** `noise_std` column in the header — exactly what D-21 requires through Phase 27. |
| 4 | Convergence question (E1 ratio) already answered by the optimality probe — must NOT be re-derived here | VERIFIED | No solve, calibration, or measurement was run for this criterion. `25-05-SUMMARY.md` explicitly records "No measurement, no solve, no experiment run" and every number in MF-21 and the `benchmark_grid.tex` caveat is transcribed, with citation, from the two pre-existing probes (`2026-08-17-optimality-decomposition/FINDINGS.md`, `2026-08-17-huber-knee/FINDINGS.md`). `OPTIMALITY_CAVEAT_TEX` is a new module constant in `experiments/e4_benchmark_grid.py`, emitted into `benchmark_grid.tex` before the two blocks that carry the `optimality` column, verified by a source/output-text test that also checks ordering. |

**Score:** 4/4 success criteria verified

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `src/aquacal/calibration/_optim_common.py` sinks | `degeneracy_details_out`/`observation_depths_out` opt-in, inert when None | VERIFIED | Present at lines 706-707, guarded independently, row caps `DEGENERACY_DETAIL_ROW_CAP_PER_STAGE=50_000` / `OBSERVATION_DEPTH_ROW_CAP_PER_STAGE=200_000` present |
| Threading at both post-solve sites | `interface_estimation.py`, `refinement.py` | VERIFIED | Both files accept and forward both sinks, stamp `stage`/`n_*_at_stage`/`truncated` |
| `CalibrationConfig.log_all_observation_depths` | exists, default False, round-trips | VERIFIED | `schema.py:374` default `False`; `pipeline.py:391-392` parses via `bool(internals.get(...))`; round-trip test present and passing |
| `degenerate_observations.csv` sidecar | written only when ≥1 flagged row | VERIFIED | `save_diagnostic_report` writes conditionally (`if degeneracy_details:` truthiness check per 25-02-SUMMARY) |
| `experiments/_degeneracy.py` classifier | bucket vocabulary keyed off `nan_reason` codes, no `h_q` predicate | VERIFIED | `grep -c "h_q_m >|h_q_m <"` in classifier = 0; `grep -c "NAN_REASON_"` = 17, all imported |
| Gate-scope rationale (3 sites) | present verbatim | VERIFIED | `_observability.py`, `e4_benchmark_grid.py`, `e6_generalization_sweep.py` all carry the D-04 text and the tripwire |
| Synthetic gate predicate `count > 0` | unchanged | VERIFIED | `n_degenerate > 0` present literally in both harnesses |
| `experiments/results/exp1_band.csv` / `exp1_parameter_band.csv` | still 160/240 rows, no `noise_std` column | VERIFIED | `wc -l` = 161/241 (header + 160/240); header greps confirm no `noise_std` column |
| MF-21, MF-22 in MANUSCRIPT-FINDINGS.md | present, no §3-facing magnitude smuggled | VERIFIED | Both entries read in full; explicit "no §3-facing number" / "no magnitude is publishable" language throughout, all quoted figures are diagnostic/probe numbers, not accuracy claims |
| `.planning/todos/pending/2026-08-15-suspend-programmatic-check-for-reshaped-artifacts.md` `## Phase 25 additions` | registers the timing split for Phase 26's driver | VERIFIED | Section present, states explicitly "No Phase 26 gate may assert 640 or 960" |

### Key Link Verification

| From | To | Via | Status | Details |
|------|-----|-----|--------|---------|
| `compute_residuals` sinks | `optimize_interface`/`joint_refinement` | parameter threading | WIRED | Both call sites pass sinks through, confirmed by grep |
| Config flag | `run_calibration_from_config` → residual call | `pipeline.py` accumulators | WIRED | `pipeline.py:789` conditional accumulator; threaded to both stage-3 calls per 25-02-SUMMARY |
| Per-observation rows | `experiments/_degeneracy.py` classifier | `nan_reason` code | WIRED | Classifier consumes rows produced by the library sink, confirmed by the probe's successful 198-row run |
| E1 band code | `experiments/results/` artifacts | NOT extended (deliberately) | CORRECTLY UNWIRED | D-21 requires the committed CSVs stay at the old shape; confirmed unchanged |
| Gate-scope rationale | Phase 29 obligation | code comment + SUMMARY note | WIRED (durable) | Tripwire text is embedded in `_observability.py` and both harness files — code Phase 29 will directly touch when working with the gate, not merely a planning doc |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| Classifier separates by code not geometry | `pytest tests/unit/test_discard_accounting.py -k "classif or provenance or stage_stamped or row_cap" -q` | 5 passed | PASS |
| Source-text assertions (stated domain, gate rationale) | `pytest tests/unit/test_experiment_inertness.py -q` | 12 passed | PASS |
| Noise axis shape/key-uniqueness | `pytest tests/unit/test_e1_band_mode.py -k TestNoiseAxis -q` | 3 passed | PASS |
| Optimality caveat ships in `.tex` | `pytest tests/unit/test_experiments_e4.py -k optimality_caveat -q` | 1 passed | PASS |
| Degenerate sidecar presence/absence | `pytest tests/unit/test_diagnostics.py -k degenerate_sidecar -q` | 2 passed | PASS |

All spot-checks run directly against HEAD (`5569fbf`) inside a live `PYTHONPATH` pointed at `src/`,
independent of SUMMARY.md claims. No full-suite run was executed here — the orchestrator already
ran it (1951 passed, 25 skipped, 0 failed at `42d9efb`), and the diff between `42d9efb` and `5569fbf`
is limited to waves 4-5 (25-07, 25-08 registration/probe work, both spot-checked above).

### Probe Execution

No `scripts/*/tests/probe-*.sh` conventional probes apply to this phase. The phase's "probes" are
the two orchestrator-run investigation directories (`2026-08-17-degeneracy-classification/`,
`2026-08-18-e1-noise-axis/`) — both are one-off measurement runs, not re-runnable scripts, and both
were verified via their committed `FINDINGS.md` and cross-checked against the classifier/band code
that produced them. Re-running either is out of scope per the verification instructions (no
experiment or calibration runs).

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|--------------|------------|--------------|--------|----------|
| DEGEN-04 | 25-01, 25-02, 25-03, 25-06, 25-07 | Per-observation sinks, config flag, sidecar, classifier, provisional E2 run, gate-scope decision | SATISFIED | All artifacts present and wired; classification finding recorded |
| BAND-01 | 25-04, 25-08 | `noise_std` axis, `n_cameras` skip, stated domain, two-seed probe (rescoped by D-21) | SATISFIED | Axis code present and correct; probe committed; committed CSVs correctly unchanged |
| DEGEN-05 (verdict only) | 25-05 | Carry-forward verdict, `optimality` caveat, MF-21 | SATISFIED | No re-derivation; caveat shipped where the number ships; MF-21 recorded |

No orphaned requirements found for this phase in REQUIREMENTS.md (file was noted as removed post
v2.0 close; requirement provenance for this milestone lives in ROADMAP.md and 25-CONTEXT.md, both
consistent with the above).

### Anti-Patterns Found

None blocking. No `TBD`/`FIXME`/`XXX` markers found in the touched files during review. All
"stub-shaped" greps (empty returns, placeholder strings) in the touched source files came back
clean per each SUMMARY's own verification tables, and spot-checks above confirm the code is live,
not decorative.

## Judgement Calls

### 1. Is criterion 3 genuinely met under D-21's rescope, or was it quietly narrowed?

**Genuinely met, not narrowed.** The roadmap's own criterion 3 text was edited in-place by D-21
(visible in `ROADMAP.md`'s Phase 25 section, "Rescoped 2026-08-18 by D-21") to explicitly describe
the reduced deliverable: axis + both key lists + smoke collapse + stated-domain sentence + a
two-seed probe, with the ten-seed band of record explicitly assigned to Phase 28. What shipped
matches that rescoped text exactly — verified directly against the code (axis present, both key
lists corrected, smoke collapse present, stated-domain sentence present, probe committed) rather
than only trusting the SUMMARY narrative. The registration in
`2026-08-15-suspend-programmatic-check-for-reshaped-artifacts.md`'s `## Phase 25 additions` section
is explicit and load-bearing: it tells Phase 26's driver work, in the first and most prominent
point, that `experiments/results/` stays at 160/240 rows through Phase 27 and that "no Phase 26
gate may assert 640 or 960." That is a real protection, not a paper promise — it sits in the exact
file DRIVER-03 is scoped to consume. The committed CSVs were independently confirmed unchanged
(160/240 data rows, no `noise_std` column), so the protection is currently true, not merely
documented as intended.

One soft spot: the protection depends on Phase 26's executor actually reading that todo file before
writing gates. That is a process risk, not a Phase 25 defect — Phase 25's job was to leave the
correct information in the correct place, which it did.

### 2. Is the provisional discipline actually held?

**Held.** Read MF-21 and MF-22 in full. MF-21 carries diagnostic-scalar numbers (92.78, 2.16, 43×,
the Huber-knee ±1-7% shift) that are explicitly framed as properties of a diagnostic quantity, not
a §3 accuracy claim, and the entry states directly: "Do not quote 92.78, 2.16 or the 43× swing as a
result about the method." MF-22 carries the two-seed noise-axis table (74.6×→13.5×) but states
three times in different words that no magnitude is publishable ("PROVISIONAL on every magnitude,"
"No magnitude here is publishable," "No comparison to the published 97-178× band may be drawn").
Neither entry writes a number into a disclosure sentence or a §3-facing claim — both are framed as
derivations for the manuscript session to use later, with the sole-source constraint (Phase 29's
frozen table) restated in every relevant place. The E2 classification probe's `FINDINGS.md` and the
gate-scope code comments both restate D-02's constraint independently (provisional, Phase 29 is
sole source) rather than assuming it's understood once.

### 3. Phase 29 tripwire — recorded where it will actually be encountered?

**Recorded durably, in code Phase 29 will directly touch.** The `camera_model_failure` tripwire is
not only in the SUMMARY narrative — it is embedded as a code comment inside
`src/aquacal/calibration/_observability.py` (the module that defines the bucket-adjacent
vocabularies) and inside both `experiments/e4_benchmark_grid.py` and
`experiments/e6_generalization_sweep.py` at the exact gate predicate sites. Anyone touching the
degeneracy gate or reading the classification results in Phase 29 will encounter this text directly
in the source, not merely in a planning document that could go unread. This is a stronger placement
than "only in code comments" implies dismissively — comments at the load-bearing code site are
exactly where a future agent editing that code is most likely to look. The one gap: there is no
automated CI check or gate that would *fail* if Phase 29 skips checking `camera_model_failure`
specifically — the obligation is discoverable but not enforced. That is a reasonable trade-off for
a prose-only tripwire and not a phase-25 defect, but it is worth flagging as a WARNING for Phase 29
planning: the tripwire should be explicitly restated in Phase 29's plan/context so it isn't missed.

## Human Verification Required

None. All four success criteria and all judgement calls were resolvable by direct codebase
inspection, targeted test execution, and reading the committed probe/finding artifacts. No visual,
real-time, or external-service behavior is involved in this phase's deliverables.

## Gaps Summary

No gaps found. All four ROADMAP success criteria are verified against the actual codebase state at
HEAD (`5569fbf`), not merely against SUMMARY.md claims. The one soft process risk (judgement call 1)
and one enforcement gap (judgement call 3) are both flagged as informational — they do not block
this phase's goal, which was fully achieved, but are worth carrying into Phase 26/29 planning as
explicit reminders.

---

_Verified: 2026-08-18T17:47:40Z_
_Verifier: Claude (gsd-verifier)_
