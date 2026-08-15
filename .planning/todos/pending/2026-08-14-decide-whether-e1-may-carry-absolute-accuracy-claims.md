---
created: 2026-08-14T00:00:00.000Z
title: E1 is documented as carrying no accuracy claim, yet the manuscript quotes E1 absolute numbers throughout — decide before the re-run
area: manuscript
files:
  - experiments/e1_refractive_comparison.py
  - .planning/MANUSCRIPT-FINDINGS.md
  - "OneDrive - Georgia Institute of Technology/Thesis/Spinoffs/papers/aquacal/main.tex"
---

## Problem

`experiments/e1_refractive_comparison.py:42` states plainly:

> E1 carries NO accuracy claim (D-19.3-17 demoted it)

Only E7 survived that gate (MF-08). Yet the manuscript's abstract and its entire §3 synthetic
paragraph quote E1 outputs as absolute magnitudes:

- \SI{1.9}{\milli\meter} depth-axis RMSE at \SI{2.5}{\meter} and the ${\sim}135\times$ ratio
  (abstract, `main.tex:68`; restated `:281`)
- \SI{0.498}{px} and \SI{1.245}{px} reprojection RMS with their ten-seed bands (`:261`)
- focal drift 0.054% against 7.03% with their bands (`:260`)

`.planning/MANUSCRIPT-FINDINGS.md` names this tension and explicitly declines to resolve it:
"every number in `main.tex`'s table … is an E1 output. **This measurement does not close that
gap.**" It draws the line precisely — MF-16 "licenses 'the depth-axis improvement is two orders
of magnitude, 97–178× depending on seed'; it does **not** license 'E1's absolute error numbers
are accurate' for either arm."

**This is not a numeric error.** Every one of those numbers was traced to its artifact and
verified during the goal-4 audit; the aggregations match the prose, and the bands are real
ten-seed spans. The open question is what E1 is *licensed to assert*, which no checker reaches.

## Why it must be decided before the re-run, not after

One of the three resolutions is a re-run scoping decision. If the answer is "promote E1", the
full suite must produce whatever seed-band backing E7 has, and that has to be scoped before the
run starts rather than discovered afterwards.

## Solution

Pick one and record the rationale where it will not be re-litigated:

**(a) The demotion was about E1 as a standalone accuracy benchmark, and §3's comparative
framing is not an absolute accuracy claim.** §3 reads comparatively already ("the refractive
model held focal lengths near ground truth … whereas the non-refractive baseline drifted"), and
every quoted figure is seed-banded across ten seeds with spans stated. If this is the intent,
say so in `e1_refractive_comparison.py`'s header beside the demotion note, so the next reader
sees both halves.

**(b) Reframe §3's E1 numbers as comparative or ratio statements throughout**, keeping the
bands MF-16 licenses and hedging or dropping absolute magnitudes. Costs manuscript edits and
weakens the abstract.

**(c) Promote E1 by giving it the seed-band backing E7 has.** A re-run item — scope it into the
full suite now if this is the choice.

Recommendation from the audit: **(a) plus a recorded rationale**, if it survives inspection.
But this is a judgement about the project's own gate, and it should be *decided* rather than
left in the state MF-12 and MF-18 left it.

## Do not

- Do not resolve this by editing the manuscript alone. The demotion note lives in the
  experiment script; if the manuscript's usage is legitimate, that script is where the
  reconciliation belongs, or the tension resurfaces at the next audit.
- Do not treat the traced-and-verified status of the numbers as settling it. They are correct
  *as measurements of what E1 computed*; the question is whether E1 is the right instrument to
  cite for them.
- Do not silently drop the demotion note to make the conflict disappear.

## Related

- `.planning/MANUSCRIPT-FINDINGS.md`, "The independent tension this measurement does NOT
  resolve" — the fullest statement of the problem, and the source of the MF-08/MF-16 line.
- `2026-08-05-verify-non-refractive-baseline-supports-paper-claims.md` — adjacent, covers
  whether the `n_water=1.0` arm is converged; that question is settled, this one is not.
- Filed from the AquaCal manuscript goal-4 audit
  (`Spinoffs/papers/aquacal/AUDIT-goal4.md`, finding F-012, TODO ledger T-13).
