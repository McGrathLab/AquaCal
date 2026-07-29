# Manuscript Findings

Measured results from the v1.9 experiment suite that **contradict, understate, or otherwise
require a change to** prose in the manuscript or supplement.

This file exists because experiment output and manuscript prose live in different trees: the
manuscript is read-only from here (OneDrive), so a finding surfaced by a script has no natural
place to land. Anything recorded here needs a human editing pass on the paper before submission.

Each entry names the artifact that is the citable source, so the correction is made against
measured data rather than against this summary.

---

## MF-01 — Newton iteration count: the supplement understates the tail

**Status:** open — needs a prose edit
**Found:** 2026-07-29, phase 19.2 plan 19.2-05 (E3 tier 2, per D-20)
**Source of truth:** `experiments/results/newton_iterations.csv`
**Where the prose is:** supplement, the refractive-projection convergence claim

The supplement says the Newton solve for the refraction point converges in **"two to four
steps."** Measured over the real rig's full working volume (104,052 points, 12 cameras):

| quantity | value |
|---|---|
| iterations, min | 2 |
| iterations, **median** | **4.0** (identical on every camera) |
| iterations, **max** | **7** (6-7 per camera) |
| not converged | **0** |
| incidence angle range | 0.13 deg - 62.92 deg |
| max residual | ~1e-9 m (at tolerance) |

**The claim is right about typical behavior and wrong about the tail.** Min 2 / median 4 matches
"two to four steps" exactly. What it misses is that the distribution runs to 7 at high incidence
angles. Convergence itself is never in question: zero points failed to converge and every residual
sits at the solver tolerance.

So this is not a correctness problem in the library, and it is not grounds for weakening any
accuracy claim. It is a prose accuracy problem: a reader sizing a compute budget or reimplementing
the solver from the paper would under-provision the iteration cap.

**Suggested framing for the edit** (wording is the author's call): report the median with the
observed maximum, e.g. "typically four steps (median 4, range 2-7 over the calibrated volume,
with the upper tail at high incidence angles)."

**Do not** silently change the number to 7 — the median genuinely is 4, and 7 is the tail. Quoting
only the max would overstate typical cost as badly as "two to four" understates the tail.

---

<!-- Append new findings above this line as MF-02, MF-03, ...
     Candidate sources still to run: E5 index sensitivity (19.2-13), E6 generalization sweep
     (19.2-11), E4 grid (19.2-09 - the 16x200 cell is projected to OOM, which is itself a
     reportable limit rather than a defect). -->
