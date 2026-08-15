---
created: 2026-08-15T00:00:00.000Z
title: E7's fixed-intrinsics rows report verdict "no_signature" on a statistic that is vacuous by construction
area: experiments
files:
  - experiments/e7_focal_standoff_analysis.py
---

## Problem

`e7_focal_standoff.csv` carries four rows, one per arm. The two `fixed` (intrinsics-not-refined)
rows record `verdict = no_signature` while `mean_within_seed_correlation` is **blank**,
`n_seeds_negative = n_seeds_positive = 0`, and `p_one_sided = 1.0`.

With intrinsics never refined, focal-drift variance is identically zero, so there is no
correlation to compute. "No signature" there is a construction artifact, not a null result — and
`classify_verdict` (`e7_focal_standoff_analysis.py:211`) reaches it by falling through rather than
by measuring anything.

The manuscript never steps in this trap — no value from that file appears in `main.tex`,
`supplement.tex` or `numbers-ledger.tsv`, and where the supplement reasons about the fixed arm
(`:957–960`) the argument is *a priori* and draws on a different artifact. But the CSV ships to
Zenodo, where a reader meets it without the manuscript's care and reads two measured nulls.

## Solution

Label the rows in the artifact. `build_focal_standoff_df` (`:235`) already has everything it
needs — a blank correlation with zero seeds on both sides is exactly the vacuous case.

- Emit a distinct verdict for it (`vacuous_by_construction`, or equivalent) rather than
  `no_signature`, and/or add a boolean column stating that the arm admits no focal drift.
- Say why in the same row, so the CSV is self-explaining without the paper.

One change to the writer; the run regenerates the file, so it should land before the sweep rather
than be patched afterwards.

## Do not

- Do not drop the rows. Their presence documents that the arm was run; it is the verdict string
  that misleads.
- Do not change how the refined arms are classified. Those verdicts are measured and correct.
- Do not "fix" this by adding the fixed arm's correlation to the manuscript. MF-17 is right that
  the number does not exist, and the supplement's a priori argument is the sound one.

## Related

- `.planning/MANUSCRIPT-FINDINGS.md` MF-17 — original observation.
- Filed from the AquaCal manuscript goal-4 audit
  (`Spinoffs/papers/aquacal/AUDIT-goal4.md`, V-011, TODO ledger T-07).
