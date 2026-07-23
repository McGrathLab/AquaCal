---
phase: quick-3
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - src/aquacal/calibration/_optim_common.py
  - src/aquacal/calibration/refinement.py
  - src/aquacal/calibration/interface_estimation.py
  - tests/unit/test_optim_common.py
autonomous: true
requirements: [QUICK-3]

must_haves:
  truths:
    - "The joint bundle adjustment uses exactly 13 FD column groups without intrinsic refinement and 17 with it, regardless of camera/board visibility"
    - "The structurally grouped Jacobian is numerically identical to the group_columns-grouped Jacobian"
    - "point_refinement.py still uses the group_columns default (unchanged behavior)"
    - "A future change to the parameter layout trips an assertion rather than silently producing a wrong Jacobian"
  artifacts:
    - path: "src/aquacal/calibration/_optim_common.py"
      provides: "build_structural_column_groups() plus a groups=None parameter on make_sparse_jacobian_func"
      contains: "def build_structural_column_groups"
    - path: "tests/unit/test_optim_common.py"
      provides: "Validity, equivalence, and count tests for the structural grouping"
      contains: "class TestBuildStructuralColumnGroups"
  key_links:
    - from: "src/aquacal/calibration/refinement.py"
      to: "build_structural_column_groups"
      via: "groups= kwarg on make_sparse_jacobian_func"
      pattern: "groups=build_structural_column_groups"
    - from: "src/aquacal/calibration/interface_estimation.py"
      to: "build_structural_column_groups"
      via: "groups= kwarg on make_sparse_jacobian_func"
      pattern: "groups=build_structural_column_groups"
---

<objective>
Replace SciPy's generic greedy column colorer with a structural column grouping derived
from the known parameter layout, for the two call sites that build the board-observation
Jacobian sparsity pattern.

Purpose: The greedy colorer degrades as camera/board visibility gets sparser — exactly the
regime AquaCal targets. On the real 12-camera rig with tilt + intrinsic refinement it
produces 20 groups where 17 suffice, costing 3 extra full residual evaluations per Jacobian
(15-23% waste). The structural grouping always hits the theoretical lower bound.

Output: `build_structural_column_groups()` in `_optim_common.py`, an optional `groups`
parameter on `make_sparse_jacobian_func`, both call sites threaded, and a three-part test
suite (validity / equivalence / count).

**This is a pure performance change. No calibration output changes.** A column grouping
only controls how FD perturbations are batched; any grouping where no two columns in a
group share a residual row yields a bit-identical Jacobian.
</objective>

<execution_context>
@C:/Users/tucke/.claude/get-shit-done/workflows/execute-plan.md
@C:/Users/tucke/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/quick/3-use-a-structural-column-grouping-for-the/3-CONTEXT.md
@CLAUDE.md
@.claude/rules/code-style.md
@.claude/rules/source-code.md

@src/aquacal/calibration/_optim_common.py
@src/aquacal/calibration/refinement.py
@src/aquacal/calibration/interface_estimation.py
@tests/unit/test_optim_common.py

<interfaces>
<!-- Contracts extracted from the codebase. Use these directly — no exploration needed. -->

The parameter column layout, from `build_jacobian_sparsity` (`_optim_common.py:242-253`),
in order:

```python
n_tilt_params      = 0 if normal_fixed else 2
n_extrinsic_params = 6 * (n_cams - 1)
n_water_z_params   = 1
n_pose_params      = 6 * n_frames
n_intrinsic_params = 4 * n_cams if refine_intrinsics else 0
n_params = (n_tilt_params + n_extrinsic_params + n_water_z_params
            + n_pose_params + n_intrinsic_params)
```

Current signature to extend (`_optim_common.py:494`):
```python
def make_sparse_jacobian_func(
    cost_func,
    cost_args: tuple,
    jac_sparsity: NDArray[np.int8],
    bounds: tuple[NDArray[np.float64], NDArray[np.float64]],
    dense_threshold: int = 500_000_000,
)
```
Body line 519 is `groups = group_columns(jac_sparsity)`.

Already imported at the top of `_optim_common.py`:
```python
from scipy.optimize._numdiff import approx_derivative, group_columns
```

Detection schema needed to build test fixtures (`src/aquacal/config/schema.py`):
```python
@dataclass
class Detection:
    corner_ids: NDArray[np.int32]     # shape (N,)
    corners_2d: NDArray[np.float64]   # shape (N, 2)
    # .num_corners property == len(corner_ids)

@dataclass
class FrameDetections:
    frame_idx: int
    detections: dict[str, Detection]   # camera_name -> Detection

@dataclass
class DetectionResult:
    frames: dict[int, FrameDetections]  # frame_idx -> FrameDetections
    camera_names: list[str]
    total_frames: int
```

Existing test file header (`tests/unit/test_optim_common.py`) — note the filename has a
SINGLE leading underscore stripped: `test_optim_common.py`, not `test__optim_common.py`:
```python
"""Tests for optimization common utilities (_optim_common.py)."""

import numpy as np
import scipy.sparse

from aquacal.calibration._optim_common import make_sparse_jacobian_func
```
Contains one class: `TestMakeSparseJacobianFunc`.
</interfaces>

<constraints>
- `_optim_common.py` is a PRIVATE module and is not re-exported from
  `src/aquacal/calibration/__init__.py`. `build_jacobian_sparsity` is not exported either.
  The new function follows suit — do NOT add it to any `__init__.py` or `__all__`.
- **Leave `src/aquacal/calibration/point_refinement.py:665` alone.** It builds a different
  sparsity structure (point correspondences, not board observations) and the layout
  argument does not apply. It keeps the `group_columns` default. This is why the new
  parameter must default to `None`.
- Do NOT bump the version or edit `CHANGELOG.md`. python-semantic-release derives both
  from the conventional commit type. Use a `perf:` commit.
</constraints>
</context>

<tasks>

<task type="auto">
  <name>Task 1: Add build_structural_column_groups and thread it through both call sites</name>
  <files>
    src/aquacal/calibration/_optim_common.py
    src/aquacal/calibration/refinement.py
    src/aquacal/calibration/interface_estimation.py
  </files>
  <action>
**1a. New function in `_optim_common.py`, placed immediately after
`build_jacobian_sparsity` (which ends ~line 325).** The two functions must agree on column
order, so keep them adjacent and say so in the docstring.

```python
def build_structural_column_groups(
    jac_sparsity: NDArray[np.int8],
    n_cams: int,
    n_frames: int,
    refine_intrinsics: bool = False,
    normal_fixed: bool = True,
) -> NDArray[np.intp]:
```

Takes `jac_sparsity` first (mirroring `group_columns(jac_sparsity)`) purely so the length
assertion is internal.

Assign a raw group id per column, walking the layout in the same order as
`build_jacobian_sparsity`:

| block | raw group id |
|---|---|
| tilt column `j` (only when `not normal_fixed`, `j` in 0..1) | `j` |
| extrinsic column `j` (0-indexed within its block, `6 * (n_cams - 1)` columns) | `j % 6` |
| `water_z` (1 column) | `6` |
| board-placement column `j` (0-indexed within block, `6 * n_frames` columns) | `7 + (j % 6)` |
| intrinsic column `j` (0-indexed within block, `4 * n_cams` columns, only when `refine_intrinsics`) | `13 + (j % 4)` |

Tilt deliberately reuses extrinsic slots 0 and 1: the reference camera has no extrinsic
columns, and tilt appears only in reference-camera rows, so they can never collide.

Then two required details:

- **Compact to contiguous ids.** SciPy requires group indices `0..m-1`. Degenerate configs
  (e.g. `n_cams == 1` leaves no extrinsic columns) leave gaps in the raw ids. Use
  `np.unique(raw, return_inverse=True)[1]` — it returns contiguous ids ordered by raw
  value. Ensure the result is 1-D (`np.ravel`) and of an integer dtype.
- **Assert the length.** `assert len(groups) == jac_sparsity.shape[1]` with a message
  naming both counts, so a future parameter-layout change trips immediately here rather
  than silently producing a wrong Jacobian.

Google-style docstring covering: why this beats `group_columns` (recovers a priori
structure; greedy degrades under partial visibility), the correctness argument (a residual
is one corner seen by one camera in one frame, so like-indexed extrinsic columns of
different cameras never share a row and like-indexed board-placement columns of different
frames never share a row — dropping observations only removes conflicts, so a grouping
valid under full visibility is valid under any sub-pattern), and the resulting counts
(13 groups, or 17 with `refine_intrinsics`). Type hints on all params and the return, per
`.claude/rules/code-style.md`.

**1b. Extend `make_sparse_jacobian_func` (`_optim_common.py:494`).** Add a
`groups: NDArray[np.intp] | None = None` keyword parameter and replace line 519 with:

```python
if groups is None:
    groups = group_columns(jac_sparsity)
```

Keep `group_columns` imported — `point_refinement.py` relies on this default path.
Document the new parameter in the docstring, noting that passing
`build_structural_column_groups(...)` yields a strictly better grouping for the
board-observation layout.

**1c. Thread both call sites.** These already build the pattern from the layout, so they
know `n_cams`, `n_frames`, `normal_fixed`, and `refine_intrinsics`.

`refinement.py:185` — `refine_intrinsics` and `normal_fixed` are local variables there,
and `camera_order` / `frame_order` are in scope:
```python
jac = make_sparse_jacobian_func(
    compute_residuals,
    cost_args,
    jac_sparsity,
    (lower, upper),
    groups=build_structural_column_groups(
        jac_sparsity,
        len(camera_order),
        len(frame_order),
        refine_intrinsics=refine_intrinsics,
        normal_fixed=normal_fixed,
    ),
)
```

`interface_estimation.py:285` — same shape, but this stage never refines intrinsics
(note the hardcoded `False` at `interface_estimation.py:270`), so pass
`refine_intrinsics=False` and mirror the `normal_fixed` already passed to
`build_jacobian_sparsity` at line 283.

Add `build_structural_column_groups` to the existing
`from aquacal.calibration._optim_common import (...)` block in each file
(`refinement.py:11`, `interface_estimation.py:11`).
  </action>
  <verify>
  <automated>python -m pytest tests/unit/test_optim_common.py tests/unit/test_refinement.py tests/unit/test_interface_estimation.py -m "not slow" -q && python -m ruff check src/aquacal/calibration/ && python -m ruff format --check src/aquacal/calibration/</automated>
  </verify>
  <done>
`build_structural_column_groups` exists in `_optim_common.py` beside
`build_jacobian_sparsity`; `make_sparse_jacobian_func` accepts `groups=None` and falls back
to `group_columns` when omitted; both `refinement.py` and `interface_estimation.py` pass
the structural grouping; `point_refinement.py` is untouched; existing tests and lint pass.
  </done>
</task>

<task type="auto">
  <name>Task 2: Test validity, equivalence, and group count of the structural grouping</name>
  <files>tests/unit/test_optim_common.py</files>
  <action>
An *invalid* grouping silently produces a **wrong** Jacobian rather than raising, so this
test is the safety net for the whole change. Add a `TestBuildStructuralColumnGroups` class
to the existing `tests/unit/test_optim_common.py` (leave `TestMakeSparseJacobianFunc`
untouched). Extend the imports to bring in `build_jacobian_sparsity`,
`build_structural_column_groups`, and `group_columns` / `approx_derivative` from
`scipy.optimize._numdiff`.

**Shared fixture helper** — a module-level function that fabricates a `DetectionResult`
with partial visibility:

```python
def _make_detections(n_cams, n_frames, visibility, corners_per_view=4, seed=0):
    """Build a DetectionResult where each camera sees each frame with prob `visibility`."""
```
Use a seeded `np.random.default_rng`. Camera names `f"cam{i}"`. For each frame, include a
camera's `Detection` only when the draw is below `visibility`; guarantee at least one
camera per frame so no frame is empty. `corner_ids` = `np.arange(corners_per_view,
dtype=np.int32)`, `corners_2d` = arbitrary finite floats of shape `(N, 2)`. Return
`DetectionResult(frames=..., camera_names=..., total_frames=n_frames)`. Keep it small
(e.g. 4 cameras / 5 frames) so the tests stay fast — the property under test is
independent of size.

**Test 1 — validity (the critical one).** Parametrize over `visibility` in
`(1.0, 0.7, 0.4)` and over both configs: `(normal_fixed=True, refine_intrinsics=False)`
and `(normal_fixed=False, refine_intrinsics=True)`. Build the pattern with
`build_jacobian_sparsity`, build the grouping, then for each distinct group id assert
`jac_sparsity[:, cols].sum(axis=1).max() <= 1` — no two columns in a group share a
residual row. Also assert the group ids are contiguous
(`set(groups) == set(range(groups.max() + 1))`).

**Test 2 — equivalence.** Build a nonlinear residual function that honors the pattern, so
the FD result actually depends on the grouping:
```python
def _patterned_residuals(x, S, coeff):
    return np.sin(S * coeff @ x) ...   # any smooth fn whose row i depends only on
                                       # the columns where S[i] is nonzero
```
Simplest correct construction: `resid = np.sin((S * coeff) @ x)` where `coeff` is a seeded
random dense matrix of `S`'s shape — masking by `S` guarantees row `i` depends only on the
allowed columns, and `sin` makes it nonlinear. Then assert
`approx_derivative(f, x0, method="2-point", sparsity=(S, structural))` equals
`approx_derivative(f, x0, method="2-point", sparsity=(S, group_columns(S)))`.
Compare via `.toarray()` on both (`approx_derivative` returns a sparse matrix in this
mode) with `np.testing.assert_allclose(..., rtol=0, atol=0)` — these should come out
bit-identical, as verified in the context doc. If exact equality proves brittle across
SciPy versions, fall back to `atol=1e-12` and note why in a comment.

**Test 3 — count.** Assert `groups.max() + 1 == S.sum(axis=1).max()`, i.e. the number of
groups equals the theoretical lower bound (the max nonzeros in any row). Check both
configs explicitly resolve to 13 and 17.

**Test 4 — degenerate config.** `n_cams == 1` (no extrinsic columns) still yields
contiguous group ids `0..m-1` and passes the validity check. This is the case the
compaction step exists for.

Follow the existing file's style: Google-style docstrings on each test, one assertion
concern per test.
  </action>
  <verify>
  <automated>python -m pytest tests/unit/test_optim_common.py -v && python -m ruff check tests/unit/test_optim_common.py && python -m ruff format --check tests/unit/test_optim_common.py</automated>
  </verify>
  <done>
`TestBuildStructuralColumnGroups` covers validity across visibility fractions 1.0/0.7/0.4
and both configs, FD equivalence against `group_columns`, group count equal to the
row-nonzero lower bound (13 / 17), and the `n_cams == 1` degenerate case. All tests pass;
`TestMakeSparseJacobianFunc` still passes unchanged.
  </done>
</task>

</tasks>

<verification>
1. Full unit suite is green:
   `python -m pytest tests/unit/ -q`
2. No behavioral regression in the optimization stages — synthetic pipeline still
   converges to the same accuracy:
   `python -m pytest tests/synthetic/ -q`
   (this is the slow one; the change is provably output-neutral, so any failure here
   means the grouping is wrong, not that tolerances need adjusting)
3. `point_refinement.py` is unmodified: `git diff --stat` lists exactly the four files in
   `files_modified`.
4. Lint clean: `python -m ruff check src/ tests/ && python -m ruff format --check src/ tests/`
</verification>

<success_criteria>
- `build_structural_column_groups()` returns exactly 13 contiguous group ids for the base
  config and 17 with `refine_intrinsics=True`, at any visibility fraction.
- No group contains two columns that share a residual row, verified by test at visibility
  1.0, 0.7, and 0.4.
- FD Jacobian from the structural grouping is identical to the `group_columns` one.
- `make_sparse_jacobian_func` with `groups` omitted behaves exactly as before, so
  `point_refinement.py` is unaffected.
- Committed as `perf:` so python-semantic-release cuts the patch release. No manual version
  or CHANGELOG edit.
</success_criteria>

<output>
After completion, create
`.planning/quick/3-use-a-structural-column-grouping-for-the/3-SUMMARY.md`
</output>
