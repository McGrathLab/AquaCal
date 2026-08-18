---
created: 2026-08-15T00:00:00.000Z
title: Decide what --check means across the re-base — suspend the reproduction bar where schemas change, verify by written expectation instead
area: experiments
resolves_phase: 26
files:
  - experiments/_io.py
  - tests/unit/test_experiments_provenance.py
---

## Problem

Every experiment carries a `--check` mode comparing its output against committed baselines
(`compare_experiment_csv`, E1's D-19 byte-identical-header contract, the per-experiment
reproduction bars). The full-suite re-run **deliberately replaces those baselines**, and
filed TODOs change schemas *or values* on top of that:

- `exp1_band.csv` gains `noise_std` (E1 noise axis)
- E6 gains `water_z_error_mm_signed` and gauge-corrected columns, plus per-camera `h_c`
- E5 and the band runs gain persisted degeneracy columns
- the degeneracy counter splits per kind and per stage, changing counts wherever it is recorded
- **E1's and E7's values move on `normal_fixed=False`** — no schema change, but the numbers do
- **E7's focal/standoff verdicts change** for the two `fixed` rows
- **E4's real-rig row** resolves differently under `--out`

See the corrected table below; the last four were identified 2026-08-15 and are the reason the
original three-item framing understated the blast radius.

So `--check` will fail broadly, for correct reasons. **The hazard is the repair**: someone
relaxing tolerances or regenerating baselines mid-run to make the suite go green, which destroys
the one signal that would catch a real defect.

**`--check` is doing two jobs and only one of them is invalidated.** The *reproduction bar* —
same code, same seed, same digits — is meaningless against an intentional re-base. The *sanity
invariants* riding in the same mode do not depend on old baselines at all, and matter more during
a re-base, not less: row counts matching the design, no NaNs, `status` values, degenerate counts
zero where expected, seeds present, the newly added columns actually populated.

## Decision (author, 2026-08-15)

**Verify this run by hand — an agent checking outputs — rather than programmatically. Then,
after the run, re-baseline the regression checks against the new outputs and restore automated
checking.** Accepted as the pragmatic call given how many artifacts change shape.

## Solution

**Before the run — write the expectation sheet.** For every artifact the suite produces: expected
row count and how it is derived (seeds × depths × models, cells, configurations), the full column
set including new columns, which columns must be non-null, expected `status` values, and expected
degenerate counts per arm (zero everywhere synthetic once the `water_z` pin lands; ~198 on the
real rig). This is what converts "an agent looks at the outputs" into something with a pass/fail.
Without it the check has no failure mode — and the audit's F-013 was exactly a two-cell error that
survived because nothing covered those cells.

**Keep the programmatic check where the schema does not change.** **⚠ Corrected 2026-08-15 — the
original inventory here was wrong on two experiments, and getting it wrong in this direction is
expensive: it labels expected movement as "signal" and sends someone investigating a non-defect
mid-run.** The current picture:

| experiment | changes? | why |
|---|---|---|
| **E1 band** | **yes** | gains `noise_std`; row count 160 → 640 |
| **E1 single-seed** | **yes — newly identified** | `normal_fixed=False` moves the values, so `exp1_parameter_errors.csv` / `exp2` / `exp3` move even though their **headers** are frozen under D-19 |
| **E6** | **yes** | `water_z_error_mm_signed`, gauge-corrected columns, per-camera table |
| **E5** | **yes** | persisted degeneracy columns |
| **E7 ablation + band** | **yes — newly identified** | `normal_fixed=False` may change the result itself, not just digits; the 10-of-10 fixed-intrinsics sign test is exactly what two extra free parameters could soften |
| **E7 focal/standoff** | **yes — newly identified** | `e7-vacuous-fixed-rows` changes the verdict string for the two `fixed` rows |
| **E4** | **yes — newly identified** | the aggregator fix changes how the real-rig row resolves under `--out` |
| **E3** | no | |
| **E2** | no | and it is the control, below |

So `--check` survives meaningfully on **E3 and E2 only**. Treat a `--check` failure anywhere else
as expected and pre-declared, not as a finding.

**E2 is the useful control**: F-001 measured the entire
Windows→Linux, `6c7f930`→v2.0.1 span reproducing to **1.5e-8** with OpenCV held at 4.13. If the
fresh E2 lands at that order, the new suite is sane; if it lands at 1e-2, something is wrong and
it is worth knowing before the numbers reach the paper.

**After the run — restore automation.** Re-baseline every `--check` contract against the new
outputs, update the byte-identical-header contracts for the columns that were added, and record
in the SUMMARY which baselines were replaced and why. Until that lands, the suite has no
regression protection at all, so it should not sit unfinished.

## Do not

- Do not relax a tolerance to make a check pass during the run. If a check fails, either the
  baseline is stale (expected — suspend it) or something is wrong (investigate). There is no
  third case that tolerance-tuning is the answer to.
- Do not regenerate baselines silently mid-run. Baseline replacement is a deliberate post-run
  step with a written record, not a repair.
- Do not skip the expectation sheet because the hand-check "will catch anything obvious". The
  errors this project has actually shipped were not obvious: a hand-transcribed parameter count
  off by ten, a mean-absolute column hiding a datum shift, a version string shared by two commits.
- Do not leave the suite permanently on manual verification. The post-run re-baselining is part of
  this TODO, not a follow-up.

## Phase 24 additions (written 2026-08-17 by plan 24-02 — for DRIVER-01's completeness audit)

This section is the concrete input § Solution asks for above ("the full column set including new
columns"). Phase 24 shipped; everything below is already on disk. Nothing here is a proposal.

### New `benchmark.json` shapes

- A new **top-level `discard_stats` block**, carrying the run's whole discard-accounting dict
  unmodified. Written by `assemble_benchmark_record(..., discard_stats=...)`, so it appears in the
  pipeline-written `benchmark.json` **and** in every `write_direct_call_benchmark` record (E1's
  `e1_benchmark_<model>.json`, E7's `e7_benchmark_<arm>.json`) that passes one. Absent entirely
  when the writer had no accounting to record — it is never an empty block.
- **`problem_shape.degenerate_observations_at_solution`**, a mirror of the block's merged total.
  It exists only so `check_rerun_gates.py`'s first read shape and every existing consumer keep
  working; the two values are always equal. This mirror is the DEGEN-01 fix: the counter existed
  in `discard_stats` and was never written into `problem_shape` (`pipeline.py:1709`).

### The six new CSV columns

Verbatim, in append order:

```
degenerate_observations_at_solution
degenerate_observations_cause_above_interface
degenerate_observations_cause_behind_camera
degenerate_observations_cause_interface_below_camera
degenerate_observations_fate_extended
degenerate_observations_fate_penalized
```

Where they landed:

| file / artifact | column list | note |
|---|---|---|
| `experiments/e5_index_sensitivity.py` | `E5_COLUMNS`, now **23** entries (was 17) | `index_sensitivity.csv` and `index_sensitivity_seed_band.csv` |
| `experiments/e7_interface_ablation.py` | `ABLATION_COLUMNS`, now 23 entries | `interface_ablation.csv` and `interface_ablation_band.csv`; per-arm values repeated on that arm's camera rows |
| `experiments/e7_focal_standoff_analysis.py` | the `pd.DataFrame(rows)` frame (no constant) | `e7_focal_standoff.csv`; summed per arm from the band CSV's own columns, `None` when the band predates them |
| `experiments/e1_refractive_comparison.py` | `SPATIAL_COLUMNS` | `exp2_spatial_errors.csv` **only** |

**E6 was NOT reshaped.** Its band already carries `degenerate_observations_at_solution` on all 102
committed rows, and reshaping a committed artifact was out of scope.

**E1's three FIXED-CONTRACT CSVs were NOT reshaped either.** `EXP1_COLUMNS`, `EXP2_COLUMNS` and
`EXP3_COLUMNS` pin byte-identical headers for an external, read-only figures repository (D-19,
"do not add, remove, reorder, or rename a column"), so the six columns went to
`exp2_spatial_errors.csv`, which is E1's own output with no committed baseline and is explicitly
excluded from `--check` (D-20). Note for the audit: if E1 must publish these per model in a
`--check`ed artifact, that is a deliberate D-19 renegotiation, not an oversight here.

**Consequence for `--check`.** `E5_COLUMNS` and `ABLATION_COLUMNS` changing means
`compare_experiment_csv` reports a **header mismatch** against the committed
`index_sensitivity.csv`, `interface_ablation.csv` and `e7_focal_standoff.csv` until those
artifacts are regenerated. That is the "E5 gains persisted degeneracy columns" row of the table
above, now also true of both E7 artifacts.

### The new sidecar

`e{N}_degeneracy_breakdown.json`, one per run, written into the experiment's own `--out`
directory. It holds the raw `discard_stats` dict, unaggregated, keyed by arm/configuration:

| writer | filename | keyed by |
|---|---|---|
| `e1_refractive_comparison.py` (`_run_full`, `_run_smoke`) | `e1_degeneracy_breakdown.json` | model label |
| `e5_index_sensitivity.py` (`_run_full`) | `e5_degeneracy_breakdown.json` | `"band"` |
| `e5_index_sensitivity.py` (`--seeds`) | `e5_seed_band_degeneracy_breakdown.json` | seed |
| `e7_interface_ablation.py` (single-seed) | `e7_degeneracy_breakdown.json` | arm name |
| `e7_interface_ablation.py` (`--seeds`) | `e7_seed_band_degeneracy_breakdown.json` | seed, then arm |

Band runs use a distinct band-owned filename for the same reason the provenance sidecars are kept
apart: a `--seeds` run must never overwrite a single-seed artifact. None of these collide with the
existing `e{1,5,6,7}_seed_band_provenance.json`.

### The complete new `DISCARD_KEYS` vocabulary

`len(DISCARD_KEYS) == 32` — 14 pre-existing plus these 18, copied verbatim from
`24-01-SUMMARY.md § Evidence`:

```
degenerate_observations_cause_above_interface__stage3_interface_optimization
degenerate_observations_cause_above_interface__stage3_intrinsic_pass
degenerate_observations_cause_above_interface__unattributed
degenerate_observations_cause_behind_camera__stage3_interface_optimization
degenerate_observations_cause_behind_camera__stage3_intrinsic_pass
degenerate_observations_cause_behind_camera__unattributed
degenerate_observations_cause_interface_below_camera__stage3_interface_optimization
degenerate_observations_cause_interface_below_camera__stage3_intrinsic_pass
degenerate_observations_cause_interface_below_camera__unattributed
degenerate_observations_fate_extended__stage3_interface_optimization
degenerate_observations_fate_extended__stage3_intrinsic_pass
degenerate_observations_fate_extended__unattributed
degenerate_observations_fate_penalized__stage3_interface_optimization
degenerate_observations_fate_penalized__stage3_intrinsic_pass
degenerate_observations_fate_penalized__unattributed
observations_evaluated__stage3_interface_optimization
observations_evaluated__stage3_intrinsic_pass
observations_evaluated__unattributed
```

**These 18 keys, and the six CSV columns derived from them, are NOT a double count.** Cause and
fate are two independent decompositions of the *same* set of invalid observations, and **each axis
sums exactly to `degenerate_observations_at_solution`** — so an expectation sheet should assert
that equality per axis, and must never assert that the two axes sum to it together. The merged key
`degenerate_observations_at_solution` is unchanged in name and meaning, which is why
`check_rerun_gates.py`'s three existing read shapes still work.

### New `aquacal.core` constants

`NAN_REASON_NONE` (0), `NAN_REASON_INTERFACE_BELOW_CAMERA` (1), `NAN_REASON_ABOVE_INTERFACE` (2),
`NAN_REASON_BEHIND_CAMERA` (3) — exported from `aquacal.core`. The sidecar's cause names derive
from them. `INTERFACE_BELOW_CAMERA` is a statement about the *estimate*, never a claim that
hardware was submerged.

### New `SolverDiagnostics` fields

`optimality_by_block` (`dict[str, dict]`) and `parameters_at_bound` (`list[dict]`), each with a
`*_reason` companion, appended last so existing field order is unperturbed. They reach
`benchmark.json` through the **existing** diagnostics path — `assemble_benchmark_record` emits
every `SolverDiagnostics` field via `dataclasses.asdict`, so each stage block now carries
`optimality_by_block` beside its `optimality` with no per-experiment work.

### Zero-emission expectation

A clean synthetic run now emits these keys at an explicit **0** rather than omitting them, so
`check_rerun_gates.py`'s `cannot confirm zero` branch **passes** rather than fails — verified end
to end through `run_calibration_from_config`. The corollary the gate's message now states: an
absent field means an artifact predating the instrumentation, not an unmeasurable run.

### `rerun_19_3.sh` was deliberately NOT edited

Phase 24 left `experiments/rerun_19_3.sh` untouched (D-12). Registering these artifacts with the
driver is DRIVER-01's, because Phase 26's job is a completeness audit of that file and a partial
edit from Phase 24 would be something the audit has to reconcile rather than simply write.

## Related

- `2026-08-15-emit-a-single-run-manifest-for-the-full-suite.md` — the manifest is what makes a
  hand-verified run auditable after the fact.
- The three schema-changing TODOs: E1 noise axis, E6 Z-error reporting, degeneracy counters.

## Scope boundary — artifacts, not prose

Library and experiment work only. The manuscript tree (`Spinoffs/papers/aquacal/`) is read-only
from this repo. Where a fix has a manuscript consequence, emit the artifact and record the
derivation in `.planning/MANUSCRIPT-FINDINGS.md`; the prose is the manuscript session's.

---

## Phase 25 additions (written 2026-08-18 by plan 25-08 — for DRIVER-01's completeness audit)

Phase 25 shipped; everything below is already on disk. Nothing here is a proposal.

### FIRST AND MOST IMPORTANT — the code and the committed artifacts disagree ON PURPOSE

For three phases, E1's band code emits a shape the committed band artifacts do not have. This is
deliberate, decided as **D-21** on 2026-08-18. Read this before writing any gate.

- **The code emits `noise_std` and four noise levels as of Phase 25.** Plan 25-04 added `noise_std`
  to **both** `BAND_KEY_COLUMNS` and `PARAMETER_BAND_KEY_COLUMNS`, nested `NOISE_LEVELS` inside
  `_run_band`, and collapsed the list under `--smoke`.
- **`experiments/results/exp1_band.csv` and `exp1_parameter_band.csv` stay at 160 and 240 rows,
  with NO `noise_std` column, through Phases 25, 26 and 27.** Phase 25's noise run is a **two-seed
  probe** written to `.planning/probes/2026-08-18-e1-noise-axis/` and is deliberately not committed
  to `experiments/results/` — a probe-shaped artifact there would be neither the old contract nor
  the frozen run's shape.
- **The 640 / 960 shape, with four `noise_std` values `{0.25, 0.5, 0.82, 1.2}`, is a PHASE 28
  expectation.** It is produced by the ten-seed band at the frozen sha and verified in Phase 29.
  **No Phase 26 gate may assert 640 or 960, and none may require a `noise_std` column in
  `experiments/results/`.** A gate that does will fail every run until Phase 28.

### New library artifacts

- **`degenerate_observations.csv`** — new per-observation sidecar written beside `diagnostics.json`,
  **only when at least one flagged row exists**. A clean run legitimately produces no file, so the
  completeness gate must treat its absence as **pass, not fail**. Column order is pinned by
  `DEGENERATE_OBSERVATION_COLUMNS` in `src/aquacal/validation/diagnostics.py` — import it rather
  than hard-coding the list.
- **`all_observation_depths.csv`** — new, written only when `internals.log_all_observation_depths`
  is true. Phase 26's driver passes that flag for **E2 and nothing else**. Column order pinned by
  `OBSERVATION_DEPTH_COLUMNS` in the same module. Expect ~11 MB on the 13-camera rig.
- Both sidecars carry a `stage` column. **A stage-agnostic `len()` double-counts** any observation
  flagged in both stage-3 passes — group by `stage` first. (The 2026-08-18 E2 probe happened to
  flag only in `stage3_intrinsic_pass`, so its 198 is a distinct count, but that is a property of
  that run, not a guarantee.)

### Text-only changes

- **`benchmark_grid.tex`** gains a `%` comment block — the D-17 optimality caveat, emitted from
  `OPTIMALITY_CAVEAT_TEX` in `experiments/e4_benchmark_grid.py`. All lines start with `%`.
  `GRID_COLUMNS` / `GRID_SUMMARY_COLUMNS` are unchanged at 36 / 7; **the CSV schema did not move.**
- `e6_generalization_sweep.py` gains a pointer comment to E4's caveat. No schema change.

### Unchanged and must stay byte-identical

`exp1_parameter_errors.csv`, `exp2_depth_generalization.csv`, `exp3_xy_vs_z_anisotropy.csv` — the
three fixed-contract CSVs the external figures repository reads.
