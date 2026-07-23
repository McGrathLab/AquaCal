---
created: 2026-07-23T14:30:00.000Z
title: Reduce memory and CPU load during calibration
area: performance
files:
  - src/aquacal/calibration/_optim_common.py
  - src/aquacal/calibration/interface_estimation.py
  - src/aquacal/calibration/refinement.py
---

## Problem

Stage 3 dominates calibration cost on the 13-camera rig: 48-87 min wall clock and
~3.6 GB peak memory. The suspected driver is `make_sparse_jacobian_func`, which
computes the finite-difference Jacobian sparsely but then returns
`.toarray()` — materializing a dense matrix so that `least_squares` can use the
`tr_solver='exact'` path.

The dense return is deliberate: `jac_sparsity` forces the LSMR trust-region
solver, which has been observed to diverge on ill-conditioned refractive bundle
adjustment problems where dense QR converges. See MEMORY / knowledge-base notes
on `scipy.optimize.least_squares + jac_sparsity`. So this is not a simple
"return the sparse matrix" fix — it trades memory against solver stability.

## Solution

Directions worth evaluating, roughly in order of expected payoff:

1. Measure first — confirm the dense `.toarray()` is actually the peak allocator
   on a 13-camera run, rather than detection buffers or residual storage.
2. Investigate whether LSMR's divergence can be controlled (preconditioning,
   `tr_options`, tighter initialization) well enough to keep the Jacobian sparse
   end to end.
3. Consider an analytic Jacobian for the refractive projection, which would
   remove the FD evaluation cost entirely rather than merely batching it better.

## Progress

Partially addressed by quick task 3 (2026-07-23, commit `3c8685c`): structural
FD column grouping cut residual evaluations per Jacobian to the theoretical
minimum (13 groups, 17 with intrinsic refinement), 15-23% fewer than scipy's
greedy colorer achieved on realistic visibility patterns. That reduces CPU time
per Jacobian. **The dense `.toarray()` memory peak is untouched.**
