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

**Status:** open — needs a prose edit, **and its source is under review (see caveat below)**
**Found:** 2026-07-29, phase 19.2 plan 19.2-05 (E3 tier 2, per D-20)
**Source of truth:** `experiments/results/newton_iterations.csv`
**Where the prose is:** supplement, the refractive-projection convergence claim

> **⚠ Provenance caveat added 2026-07-29 (phase 19.2 code review CR-05, confirmed in source).**
> `newton_iterations.csv` is produced by `refractive_project_newton_diagnostic`, which routes
> through the shared `_solve_newton_r_p` helper. But production residual evaluation does **not**
> use that path: `calibration/_optim_common.py:635` projects via `refractive_project_batch` →
> `_refractive_project_newton_batch`, a separately inlined Newton loop that never calls
> `_solve_newton_r_p` and terminates on `np.all(np.abs(delta) < tolerance)` — all points at once,
> with no per-point convergence flag.
>
> Two consequences for the numbers below. (1) `not converged = 0` is measured for a loop the
> optimizer never runs. (2) The per-point iteration counts do not transfer: under all-points
> termination every point in a batch iterates until the *slowest* converges, so production
> per-point cost behaves like the tail, not the median — which if anything sharpens this entry's
> "understates the tail" conclusion, but on different evidence than what is tabulated here.
>
> **Resolve before citing.** Either migrate `_refractive_project_newton_batch` onto
> `_solve_newton_r_p` and regenerate, or correct the diagnostic's docstring and restate the CSV's
> scope as the scalar path. The measured distribution below is not known to be wrong — it is
> known to describe a different loop than the one the prose is about.

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

## MF-02 — E4's memory curve does not bound a real deployment of the same camera count

**Status:** open — needs a prose caveat wherever the grid is presented as a capacity guide
**Found:** 2026-07-29, phase 19.2 (orchestrator analysis of the committed E4 grid vs E2's record)
**Source of truth:** `experiments/results/benchmark_grid.csv` (all values below are columns in it)
**Where the prose is:** wherever `benchmark_grid.csv`'s cameras × frames scaling is discussed

E4's 16-camera × 200-frame cell peaks at **3.31 GiB**, while E2's real rig at **13** cameras ×
200 frames peaks at **9.78 GiB** — fewer cameras, ~3× the memory. Both numbers are correct. A
reader who takes the grid as a deployment sizing guide would under-provision by roughly 3×.

| | params | **residuals** | Jacobian (dense) | peak, stage-3 interface |
|---|---|---|---|---|
| E4 16×200 (synthetic) | 1005 | 54,460 | 0.41 GiB | 3.11 GiB |
| E2 real rig 13×200 | 1269 | **147,950** | 1.40 GiB | 8.96 GiB |
| ratio | 1.26× | **2.72×** | 3.43× | 2.88× |

(The 3.31 / 9.78 GiB figures quoted above are the max across all stages; the table compares the
stage-3 interface optimization like-for-like. The real rig's overall peak lands in the
intrinsic-refinement pass.)

**Peak memory tracks residual count, not camera count.** The Jacobian is `n_residuals × n_params`
held **dense** — the library computes a sparse-FD Jacobian and then calls `.toarray()`, because
`jac_sparsity` forces LSMR, which diverges on these problems where dense QR converges. Peak scales
with the Jacobian (3.43×) far more closely than with parameters (1.26×). Camera count inflates the
parameter block, which is the small one.

**It is not a smaller calibration board.** E4's `GRID_BOARD_CONFIG` deliberately mirrors
`synthetic.py`'s `default_board`, commented "matches real hardware" — 12×9 squares, 60 mm square,
45 mm marker, `DICT_5X5_100`, giving 11×8 = **88 interior corners** in both the synthetic and real
cases. The difference is observation *density*, on two compounding axes:

- **Board-observing views:** E4's 16×200 cell records 1395 observations out of 16×200 = 3200
  possible camera-frame pairs — **44%**. (E4's own probe noted a median of 9 of 16 cameras
  observing.)
- **Corners per observing view:** 27,230 corners / 1395 observations = **19.5 of 88 (22%)**. The
  real rig averages 28.5 corners per camera-frame *pair* before accounting for non-observing
  pairs, so its per-observing-view density is materially higher.

Synthetic cameras see a modest slice of the board; a real ChArUco target filling the frame yields
several times the corners per view. Same board, sparser scenes.

**Suggested framing for the edit** (wording is the author's call): present the grid as a *scaling
curve in problem size* rather than a per-camera-count capacity table, and state that the real-rig
point is the one to size against, because synthetic observation density is lower than a real
deployment's. Do not present "16 cameras ≈ 3.3 GiB" as a deployment figure.

**Caveat on the data itself:** `n_observations` is not recorded for the real-rig row (it is a
pipeline-written record and the column is null), so the real rig's corners-per-observing-view
cannot be computed from committed data — only its corners-per-camera-frame-pair. Recording that
field for pipeline runs would make this comparison exact.

---

<!-- Append new findings above this line as MF-02, MF-03, ...
     Candidate sources still to mine: E5 index sensitivity (19.2-13, run) and E6 generalization
     sweep (19.2-11, run) - both complete and committed, neither yet mined for prose conflicts.
     E4 grid (19.2-09) is run; note the 16x200 cell did NOT OOM - it peaked at 3.31 GiB, see MF-02. -->
