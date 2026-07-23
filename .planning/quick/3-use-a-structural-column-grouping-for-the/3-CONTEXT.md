# AquaCal: use a structural column grouping for the FD Jacobian

**Type:** performance optimization, no behavioral change
**Scope:** `src/aquacal/calibration/_optim_common.py` (+ two call sites, + one test)
**Expected gain:** 15–23% fewer residual evaluations per Jacobian in the joint bundle adjustment

---

## The problem

`make_sparse_jacobian_func` (`_optim_common.py:494`) computes its column grouping by
calling SciPy's generic greedy colorer:

```python
groups = group_columns(jac_sparsity)   # line 519
```

That greedy doesn't recover the structure that's already known a priori from the
parameter layout, and it degrades as camera/board visibility gets sparser — which is
exactly the regime AquaCal targets (wide baselines, no board placement visible to every
camera at once).

Measured, using `build_jacobian_sparsity` + `group_columns` as currently shipped:

| pattern | visibility | config | lower bound | `group_columns` |
|---|---|---|---|---|
| real 12-cam rig, real images, 60 frames | 0.72 | base | 13 | 14 |
| | | tilt + intrinsics | 17 | **20** |
| `generate_real_rig_*` synthetic, 12 cam / 100 frames | 0.66 | base | 13 | 15 |
| | | tilt + intrinsics | 17 | **22** |
| every camera sees every frame (control) | 1.00 | base | 13 | 13 |
| | | tilt + intrinsics | 17 | 17 |

The bound is the maximum number of nonzeros in any single row, and each group costs one
extra residual evaluation per Jacobian. So the current code does 20 evaluations where 17
suffice.

## Why the bound is always attainable

A residual is one corner, seen by **one** camera in **one** frame. So:

- like-indexed extrinsic columns of *different* cameras never share a row
- like-indexed board-placement columns of *different* frames never share a row

This is a statement about a single row, and it never refers to *which* (camera, frame)
pairs actually exist. Dropping observations only removes conflicts — it can never create
one. Therefore a grouping valid under full visibility is valid under **any** sub-pattern,
and the minimum is 13 (or 17 with intrinsic refinement) regardless of visibility.

Verified: the structural grouping below was checked against the real-rig pattern, the
synthetic pattern, and the full-visibility control — valid in every case (no group
contains two columns sharing a row), at exactly 13 / 17 groups.

## The change

### 1. New function, beside `build_jacobian_sparsity`

Keep it adjacent to `build_jacobian_sparsity` (`_optim_common.py:207`) — the two must
agree on column order, so they should be read together.

Column layout, per `build_jacobian_sparsity` lines 242–253, in order:
`tilt (0 or 2) | extrinsics 6*(n_cams-1) | water_z (1) | board poses 6*n_frames | intrinsics (0 or 4*n_cams)`

Assignment:

| block | group id |
|---|---|
| tilt column *j* | `j` — reuses extrinsic slots 0,1 (reference camera has no extrinsics, and tilt appears only in reference rows) |
| extrinsic column *j* | `j % 6` |
| `water_z` | `6` |
| board-placement column *j* | `7 + (j % 6)` |
| intrinsic column *j* | `13 + (j % 4)` |

Totals: 13 groups without intrinsic refinement, 17 with.

Two details to handle:

- **Renumber to contiguous ids.** SciPy expects group indices `0..m-1`. Degenerate configs
  (e.g. `n_cams == 1`, so no extrinsic columns) leave gaps. Compact before returning.
- **Assert the length** matches `jac_sparsity.shape[1]`, so a future layout change trips
  immediately rather than silently.

### 2. Thread it through

```python
def make_sparse_jacobian_func(..., groups=None, ...):
    if groups is None:
        groups = group_columns(jac_sparsity)   # preserve existing behavior
```

Pass the structural grouping from the two call sites that already build the pattern from
the layout and so know `n_cams`, `n_frames`, `normal_fixed`, `refine_intrinsics`:

- `refinement.py:185`
- `interface_estimation.py:285`

**Leave `point_refinement.py:665` alone.** It uses a different sparsity structure
(point correspondences, not board observations); the layout argument above doesn't apply.
It keeps the `group_columns` default.

### 3. Test (not optional)

An *invalid* grouping silently produces a **wrong** Jacobian rather than an error, so the
test is the safety net for this change:

1. **Validity** — for each group, `jac_sparsity[:, cols].sum(axis=1).max() <= 1`. Run it
   over several visibility fractions (1.0, 0.7, 0.4) and both configs.
2. **Equivalence** — build a nonlinear residual honoring the pattern, then assert
   `approx_derivative(..., sparsity=(S, structural))` equals
   `approx_derivative(..., sparsity=(S, group_columns(S)))`.
3. **Count** — assert group count equals `S.sum(axis=1).max()` (13 / 17).

## Why this is safe

A column grouping only controls how finite-difference perturbations are **batched**. Any
grouping where no two columns in a group share a residual row yields the identical
Jacobian: perturbing a group changes row *i* only via the one column in that group with a
nonzero at row *i*, so every difference quotient is unchanged.

This was checked empirically, not just argued — on a 520×129 partial-visibility pattern,
the greedy-grouped and structurally-grouped Jacobians came out **bit-identical**
(`np.array_equal` → `True`), and both matched the dense unsparsified Jacobian exactly.

Consequence: **no calibration output changes.** No results to re-run, no regression
expected in any accuracy test. Only the evaluation count drops.

## After merging

Bump the version (currently `v1.6.0`) — the SoftwareX manuscript's code-metadata table
cell C1 references it, and the supplement's §5.2 states 13 / 17 evaluations, which becomes
true as written once this lands.

---

*Context: found while verifying Table 2 of the AquaCal supplement, which reports 13 / 17
groups. Those numbers are correct as mathematics but were not what the shipped code
achieved on any realistic visibility pattern. This change closes that gap.*
