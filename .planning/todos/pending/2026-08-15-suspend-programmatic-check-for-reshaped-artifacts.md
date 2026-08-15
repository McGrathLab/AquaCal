---
created: 2026-08-15T00:00:00.000Z
title: Decide what --check means across the re-base — suspend the reproduction bar where schemas change, verify by written expectation instead
area: experiments
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

## Related

- `2026-08-15-emit-a-single-run-manifest-for-the-full-suite.md` — the manifest is what makes a
  hand-verified run auditable after the fact.
- The three schema-changing TODOs: E1 noise axis, E6 Z-error reporting, degeneracy counters.

## Scope boundary — artifacts, not prose

Library and experiment work only. The manuscript tree (`Spinoffs/papers/aquacal/`) is read-only
from this repo. Where a fix has a manuscript consequence, emit the artifact and record the
derivation in `.planning/MANUSCRIPT-FINDINGS.md`; the prose is the manuscript session's.
