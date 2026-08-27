---
phase: 24-degeneracy-instrumentation
reviewed: 2026-08-17T00:00:00Z
depth: standard
files_reviewed: 26
files_reviewed_list:
  - src/aquacal/core/refractive_geometry.py
  - src/aquacal/core/__init__.py
  - src/aquacal/calibration/_observability.py
  - src/aquacal/calibration/_optim_common.py
  - src/aquacal/calibration/interface_estimation.py
  - src/aquacal/calibration/refinement.py
  - src/aquacal/calibration/pipeline.py
  - src/aquacal/datasets/pipelines.py
  - src/aquacal/config/schema.py
  - src/aquacal/io/benchmark.py
  - experiments/_degeneracy.py
  - experiments/e1_refractive_comparison.py
  - experiments/e5_index_sensitivity.py
  - experiments/e7_interface_ablation.py
  - experiments/e7_focal_standoff_analysis.py
  - experiments/check_rerun_gates.py
  - tests/unit/test_refractive_geometry.py
  - tests/unit/test_discard_accounting.py
  - tests/unit/test_observability.py
  - tests/unit/test_optim_common.py
  - tests/unit/test_benchmark.py
  - tests/unit/test_e5_band_mode.py
  - tests/unit/test_e7_focal_standoff.py
  - tests/unit/test_e7_band_mode.py
  - tests/unit/test_rerun_gates.py
  - tests/synthetic/test_guard_inertness.py
  - tests/synthetic/test_full_pipeline.py
  - docs/guide/benchmarking.md
findings:
  critical: 2
  warning: 10
  info: 0
  total: 12
status: issues_found_blockers_resolved
---

# Phase 24: Code Review Report

**Reviewed:** 2026-08-17
**Depth:** standard
**Diff base:** `a25fae2..HEAD`
**Status:** issues_found

## Summary

The library-side instrumentation is, as far as I can trace it, numerically inert.
`nan_reason_out` is written only at the four terminal failure branches and never inside the
Newton loop; nothing is threaded into `cost_args` or into the callable SciPy invokes; the
reason array is allocated only on the single post-solve `compute_residuals` call. The packed
block layout in `build_parameter_block_slices` matches `pack_params`/`build_parameter_labels`
exactly (tilt → extrinsics → water_z → board_poses → intrinsics, zero-width blocks skipped
but `start` still advanced), and `_coleman_li_scaling` reproduces SciPy's
`CL_scaling_vector` faithfully, so `max(max_scaled)` really does reconstruct
`result.optimality`. I found no inertness defect.

The defects are on the **experiments** side, where the split counters are consumed. Two are
blocking: `e7_focal_standoff.csv` publishes degeneracy counts inflated by a factor of
`n_cameras_per_seed`, and E7 never labels its solver stages, so the artifact that exists to
carry the cause×stage / fate×stage split carries no stage split at all. Both survive the new
tests, and — importantly — both survive the "two axes must agree" self-check that the phase
leans on as its bookkeeping tripwire, because both scale or merge the two axes identically.

## Critical Issues

### CR-01: `e7_focal_standoff.csv` degeneracy counts are inflated by the camera count

**File:** `experiments/e7_focal_standoff_analysis.py:398-405`

**Issue:** `_arm_degeneracy_columns` sums each degeneracy column over **every row of the
arm**. But `e7_interface_ablation._build_ablation_rows` emits one row **per camera** per arm
and stamps the *same* per-arm value on each of them ("Per-ARM values, summed across this
arm's stages and repeated on each of its camera rows", `ABLATION_COLUMNS` comment). The band
CSV therefore holds `n_seeds x n_cameras` copies of each arm's single value, and summing over
rows multiplies the true per-arm total by `n_cameras_per_seed` (12 on the production rig).

The same function computes `n_cameras_per_seed = int(arm_df.groupby("seed").size().iloc[0])`
eleven lines below, so the per-camera row granularity is known to the code at the point of
the bug.

This is not caught by anything:

- `test_original_column_set_and_order_unchanged` only checks header names/order.
- `test_band_without_degeneracy_columns_yields_none_not_zero` only checks the all-absent case.
- The phase's headline invariant ("each axis sums independently and exactly to
  `degenerate_observations_at_solution`, so a row where the two axes disagree is a
  bookkeeping bug, visible by eye") is **blind to this**: all six columns are scaled by the
  same factor, so both axes still agree with the (equally inflated) merged total. The
  self-validating property the docstrings advertise cannot detect it.

**Fix:** deduplicate to one value per seed before summing.

```python
    summed: dict[str, int | None] = {}
    for column in DEGENERACY_COLUMNS:
        if column not in arm_df.columns:
            summed[column] = None
            continue
        # One value per SEED: the column is a per-arm quantity repeated on every
        # camera row, so summing raw rows multiplies it by n_cameras_per_seed.
        per_seed = arm_df.groupby("seed")[column].first().dropna()
        summed[column] = int(per_seed.sum()) if not per_seed.empty else None
    return summed
```

Add a test with a hand-built band frame carrying, say, 2 seeds x 3 cameras and a per-arm
count of 5, asserting the output is 10 and not 30.

### CR-02: E7 never labels its solver stages, so `e7_degeneracy_breakdown.json` has no stage split

**File:** `experiments/e7_interface_ablation.py:391, 428` (call sites), `:398-400, 436-437`
(merge), `:568-575` (sidecar write)

**Issue:** `_run_arm` calls `optimize_interface(..., discard_stats_out=discard_stats_stage3)`
and `joint_refinement(..., discard_stats_out=discard_stats_intrinsic_pass)` **without
`discard_stage=`**. Both therefore resolve to the `"unattributed"` bucket, and every counter
E7 produces is spelled `..._cause_*__unattributed` / `..._fate_*__unattributed` /
`observations_evaluated__unattributed`.

Consequences:

1. `e7_degeneracy_breakdown.json` is documented (module docstring, `ArmResult.discard_stats`
   comment, `_write_ablation_artifacts` comment) as carrying "the full cause x stage and
   fate x stage breakdown and the per-stage `observations_evaluated__*` denominators, keyed
   by arm". It carries neither — every stage collapses into one bucket. That is the phase
   deliverable for E7.
2. The inline justification at `:397-399` is factually wrong: *"The stage is already carried
   in each split key's `__<stage>` suffix, so summing the two dicts loses nothing -- Stage
   3's and the intrinsic pass's entries have disjoint keys."* With no stage label the two
   dicts' keys are **entirely** overlapping, and the key-by-key `+=` merges the two stages
   irreversibly.
3. The per-stage denominator — the number the phase repeatedly cites as "what retires the
   hand-reconstructed 198 / 73,975" — is only available as a sum across the two stages, so
   the `stage3_intrinsic_pass` fraction can no longer be computed for E7's `refined` arms.
4. `check_rerun_gates._format_guard_breakdown` will report the merged denominator for E7
   records, which is roughly double the per-stage one for refined arms.

The module already defines `STAGE_INTERFACE = "stage3_interface_optimization"` and
`STAGE_INTRINSIC_PASS = "stage3_intrinsic_pass"` (`:495-496`) and uses them as
`diagnostics`/`observers` keys immediately around the two calls — the labels were in scope
and simply not threaded.

**Fix:**

```python
    opt_extrinsics, opt_water_zs, opt_poses, rms = optimize_interface(
        ...,
        discard_stats_out=discard_stats_stage3,
        discard_stage=STAGE_INTERFACE,
    )
    ...
        ... = joint_refinement(
            ...,
            discard_stats_out=discard_stats_intrinsic_pass,
            discard_stage=STAGE_INTRINSIC_PASS,
        )
```

and correct the `:397-399` comment — with the labels supplied the disjointness claim becomes
true for the split keys, but `degenerate_observations_at_solution` is still a shared key that
the `+=` merge is deliberately summing.

## Warnings

### WR-01: An infinite bound interval is misclassified as `"pinned"`

**File:** `src/aquacal/calibration/_observability.py:851-853`

**Issue:**

```python
pinned = interval_width <= _PINNED_INTERVAL_RTOL * max(1.0, abs(float(lower[i])))
```

If `lower[i] == -inf` and `upper[i]` is finite, `interval_width` is `inf`, the right-hand
side is `1e-9 * inf == inf`, and `inf <= inf` is `True` — the widest possible interval is
reported as a pin by request. SciPy's `find_active_constraints` *can* return `+1` for such a
parameter (`upper_active = isfinite(ub) & (upper_dist <= min(lower_dist, upper_threshold))`
does not require a finite `lb`), so this is reachable the moment any one-sided bound is
introduced. Today `build_bounds` happens to give every boundable slot two finite bounds, so
it is latent rather than live — but the classification is the whole point of D-16 ("a
detector that flagged 'on a bound' without separating pinned-by-request from
ran-into-a-limit would fire ... every single run and be trained away"), and this failure mode
is silent in exactly the direction that trains the signal away.

**Fix:**

```python
    interval_width = float(upper[i] - lower[i])
    scale = max(1.0, abs(float(lower[i])), abs(float(upper[i])))
    pinned = np.isfinite(interval_width) and interval_width <= (
        _PINNED_INTERVAL_RTOL * scale
    )
```

### WR-02: Degenerate-warning text degrades badly when the denominator is zero or all causes are zero

**File:** `src/aquacal/calibration/interface_estimation.py:117-123` (`fraction`, `dominant`)

**Issue:** two related edge cases in `_format_degenerate_observation_warning`:

- `fraction = (n_invalid / denominator) if denominator else float("nan")`. With
  `denominator == 0` the message renders `nan%`, and `fraction >= THRESHOLD` is `False` for
  NaN, so the function silently takes the *quiet* "small tail below the threshold" branch and
  asserts the optimality "is not declared unreliable" — for a state where nothing at all was
  measured. Quiet-by-NaN is the same failure shape the threshold docstring says it is trying
  to avoid.
- `dominant = max(_DEGENERACY_CAUSE_DESCRIPTIONS, key=...)` returns `"above_interface"` by
  dict order when every cause count is zero (which is exactly the bookkeeping-bug state the
  module says relation 3 exists to catch). The warning then confidently names a dominant
  cause that was never observed.

**Fix:** branch explicitly.

```python
    denominator = breakdown.get("observations_evaluated", 0)
    if not denominator:
        fraction_text = "an unknown fraction of"
        loud = True          # unmeasured denominator is not evidence of a small tail
    else:
        fraction = n_invalid / denominator
        fraction_text = f"{fraction:.3%} of"
        loud = fraction >= DEGENERACY_WARNING_FRACTION_THRESHOLD

    causes_seen = {c: breakdown.get(c, 0) for c in _DEGENERACY_CAUSE_DESCRIPTIONS}
    dominant = max(causes_seen, key=causes_seen.get) if any(causes_seen.values()) else None
```

and render "no cause was recorded (this is a bookkeeping bug -- see
`check_discard_invariants` relation 3)" when `dominant is None`.

### WR-03: A pre-Phase-24 `discard_stats` dict reads as "measured and clean"

**File:** `experiments/_degeneracy.py:78-93`

**Issue:** `summarize_degeneracy_columns` returns all-`None` only when `discard_stats` is
falsy. A **non-empty** dict produced before this phase (any run that recorded e.g.
`pnp_guard_rejected` but none of the split keys) returns `0` for all six columns, because
`.get(..., 0)` and `_cross_stage_sum` both floor at zero. The docstring's stated convention —
"`None` means 'never computed for this row', never 'computed and found to be zero'" — is
therefore violated for precisely the artifact class the convention exists to protect, and
`check_rerun_gates` was hardened in this same phase around the opposite reading ("an absent
field means an artifact predating the instrumentation, not an unmeasurable run").

**Fix:** treat the absence of the merged key as "never computed".

```python
    if not discard_stats or MERGED_DEGENERACY_COLUMN not in discard_stats:
        return {column: None for column in DEGENERACY_COLUMNS}
```

### WR-04: `write_degeneracy_breakdown` ignores the `--force` overwrite guard

**File:** `experiments/_degeneracy.py:106-131`; callers
`experiments/e1_refractive_comparison.py:147-150`,
`experiments/e5_index_sensitivity.py:301-303, 332-334`,
`experiments/e7_interface_ablation.py:572-575, 839-841`

**Issue:** every other artifact in these scripts is written through `write_experiment_csv(...,
force=args.force)` or an explicit `if args.force or not sidecar_path.exists():` guard (see
`e5_index_sensitivity.py:306`, immediately after the unguarded breakdown write). The new
sidecars are written unconditionally with `open(path, "w")` and will silently clobber a
committed `e{N}_degeneracy_breakdown.json` on any re-run without `--force` — the exact
accident the guard convention exists to prevent, days before a freeze.

**Fix:** give the helper a `force: bool` parameter and thread `args.force` from all five call
sites, skipping (and logging) when the file exists and `force` is `False`; or route through
`aquacal.io.internals.warn_if_overwriting`, already used elsewhere in this codebase.

### WR-05: `docs/guide/benchmarking.md` `stages` table omits this phase's two new fields

**File:** `docs/guide/benchmarking.md:139-160`

**Issue:** the doc adds a `discard_stats` section and a `problem_shape` row, but the `stages`
key table — presented as the field-by-field schema reference for a stage block — was not
updated with `optimality_by_block`, `optimality_by_block_reason`, `parameters_at_bound` and
`parameters_at_bound_reason`. Those four now appear in **every** stage block, since
`assemble_benchmark_record` serializes `SolverDiagnostics` via `dataclasses.asdict`. A reader
using this table as the schema will see undocumented keys, and the `*_reason` row ("Paired
with any `null` field above") no longer covers the reasons for fields that are not "above".
The `optimality` admonition ("Quote optimality to one significant figure") is also the natural
home for a pointer to the per-block decomposition and why the scalar is not a like-for-like
maximum across blocks.

**Fix:** add the four rows plus a short subsection describing the per-block entry shape
(`max_scaled` / `max_unscaled` / `argmax_parameter` / `n_params`) and the
`pinned` vs `traveled` classification, and cross-link from the optimality admonition.

### WR-06: `refinement.DEGENERACY_WARNING_FRACTION_THRESHOLD` is an alias documented as a parallel definition

**File:** `src/aquacal/calibration/refinement.py:36-38, 53-74`

**Issue:** the 20-line docstring says the constant is *"Held line-for-line parallel with the
matching constant in `interface_estimation.py` -- the two staying in sync is why that
cross-reference exists"*, and then reproduces the entire justification verbatim. In fact
line 74 is `DEGENERACY_WARNING_FRACTION_THRESHOLD = _DEGENERACY_WARNING_FRACTION_THRESHOLD`,
a re-export of the imported object; there is no second value and nothing can drift. The
duplicated rationale is dead prose that a future reader will maintain twice, and the module
never uses the name itself (only the imported formatter reads it). This is the kind of comment
that becomes actively false the first time someone "fixes" the drift it describes.

**Fix:** reduce to a one-line re-export note (`#: Re-exported from interface_estimation so
callers of this module can read the threshold; single definition lives there.`) and delete the
duplicated justification, or drop the re-export entirely and have consumers import from
`interface_estimation`.

### WR-07: `refinement.py` imports a private helper across module boundaries

**File:** `src/aquacal/calibration/refinement.py:36-41`

**Issue:** `refinement` imports `_format_degenerate_observation_warning` (leading underscore =
module-private by this project's own convention) from `interface_estimation`, plus the
threshold constant. `_observability.py` is the module that already owns the degeneracy
vocabulary (`DEGENERACY_CAUSES`, `DEGENERACY_FATES`, the key builders, the invariant checks),
and both callers already import from it. Putting the renderer in `interface_estimation`
creates a `refinement -> interface_estimation` dependency that exists only for warning text
and is one import away from a cycle if `interface_estimation` ever needs anything from
`refinement`.

**Fix:** move `_DEGENERACY_CAUSE_DESCRIPTIONS`, `DEGENERACY_WARNING_FRACTION_THRESHOLD` and
`format_degenerate_observation_warning` into `_observability.py` beside the vocabularies they
consume, and import from there in both solver modules.

### WR-08: `nan_reason_out`'s contract is only length-checked; violations are silent

**File:** `src/aquacal/core/refractive_geometry.py:651-655, 689-690`

**Issue:** the docstring states the caller "MUST supply it zero-initialized
(`np.zeros(n, dtype=np.int8)`)", but only the length is validated. A caller that reuses a
dirty array across camera-frames — the obvious optimization someone will reach for in
`compute_residuals` — gets stale reason codes attributed to clean points with no error, and
the resulting cause counts are wrong in a way relation 3 will *not* catch (it only detects
*under*-count, since stale non-zero codes still match one of the three cause values).

Separately, `~valid & ~on_axis` is documented as "exactly `h_q <= 0`". With a NaN coordinate
in `points_3d`, `h_q` is NaN, both comparisons are `False`, and the point is bucketed as
`above_interface` — a NaN input is silently reported as a geometry problem.

**Fix:** validate the dtype and the zero-initialization contract cheaply (this path is opt-in
and post-solve, so the cost is irrelevant):

```python
    if nan_reason_out is not None:
        if len(nan_reason_out) != n_points:
            raise ValueError(...)
        if nan_reason_out.dtype != np.int8:
            raise ValueError(
                f"nan_reason_out must be int8, got {nan_reason_out.dtype}"
            )
        if nan_reason_out.any():
            raise ValueError("nan_reason_out must be supplied zero-initialized")
```

and either guard the `above_interface` mask with `np.isfinite(h_q)` or add a fourth
`NAN_REASON_NON_FINITE_INPUT` code.

### WR-09: `behind_camera` silently absorbs non-finite Newton output

**File:** `src/aquacal/core/refractive_geometry.py:770-777`

**Issue:** failure branch 4 assigns `NAN_REASON_BEHIND_CAMERA` whenever
`camera.project(P)` returns `None`. `P` is built from `px_v`/`py_v`, which derive from
`r_p_v` after the Newton loop. If the loop produced a non-finite `r_p_v` (e.g. `f_prime`
underflowing to zero for a near-tangent ray), `P` contains NaN, `Camera.project`'s `z > 0`
test is `False`, and the point is reported as "behind the camera". Two physically distinct
failures — a genuine behind-camera geometry and a Newton breakdown — end up under one cause
code, in a phase whose stated purpose is that the cause axis "answers what do I fix". The
gloss `"behind_camera (no pixel exists for it)"` is technically true but will be read as the
geometric statement, and Phase 25's DEGEN-04 classification of the production rig's 198 will
inherit the conflation.

**Fix:** distinguish at the branch:

```python
        P = np.array([px_v[i], py_v[i], z_int], dtype=np.float64)
        if not np.isfinite(P).all():
            if nan_reason_out is not None:
                nan_reason_out[idx] = NAN_REASON_NEWTON_NON_FINITE
            continue
        projected = camera.project(P, apply_distortion=True)
```

(adding the fourth code to `DEGENERACY_CAUSES`, `_DEGENERACY_CAUSE_DESCRIPTIONS` and the
`core/__init__` export). If a fourth cause is out of scope for this phase, at minimum widen
the gloss so the geometric reading is not implied.

### WR-10: Relation 5 is skipped whenever the denominator is missing or zero

**File:** `src/aquacal/calibration/_observability.py:373-387`

**Issue:**

```python
        denominator = stats.get(observations_evaluated_key(stage), 0)
        if denominator <= 0:
            continue
```

A stage that recorded non-zero cause counts but no denominator — which is what a partially
written or hand-merged stats dict looks like, and what the pre-Phase-24 artifacts in
WR-03 look like — passes relation 5 silently. The docstring says relations 3-5 "hold
unconditionally"; relation 5 in fact holds only conditionally, and the condition is exactly
the missing-denominator state the phase is trying to make visible.

Related: `optimize_interface`/`joint_refinement` pre-emit all their keys at `0` at function
*entry* (D-04), before the solve. If the solve raises `ConvergenceError`, the caller's dict
is left holding an explicit `0` for causes, fates and the denominator — which by this phase's
own stated convention reads as "measured and found clean", not "never measured".

**Fix:** flag the inconsistent case rather than skipping it, and soften the docstring:

```python
        stage_causes = sum(
            stats.get(degeneracy_cause_key(cause, stage), 0)
            for cause in _DEGENERACY_CAUSES
        )
        denominator = stats.get(observations_evaluated_key(stage))
        if denominator is None or denominator <= 0:
            if stage_causes:
                violations.append(
                    f"degeneracy denominator missing for stage {stage!r}: cause "
                    f"counts sum to {stage_causes} but no positive "
                    f"observations_evaluated was recorded"
                )
            continue
```

For the entry-time pre-emission, consider emitting the denominator only after the post-solve
pass, or documenting explicitly that a stage whose solve raised leaves zeros behind.

---

## Verified clean (checked, no finding)

Recorded so the next reviewer does not re-derive these:

- **Newton-loop inertness.** `nan_reason_out` is written at four branches only, all outside
  the loop; the loop body is byte-identical to the pre-phase version. No accumulation,
  allocation or reordering was added to the residual hot path — `compute_residuals` allocates
  the `int8` array only when `degeneracy_breakdown_out is not None`, and neither
  `optimize_interface` nor `joint_refinement` threads that argument into `cost_args` or into
  the callable SciPy invokes.
- **Block indexing.** `build_parameter_block_slices` reproduces `pack_params`/`unpack_params`
  ordering (tilt, extrinsics excluding the reference camera, water_z, board poses, intrinsics)
  and advances `start` past zero-width blocks it omits; `build_parameter_labels` emits the
  same order, so `parameter_labels[block.start + argmax]` is correct.
- **Coleman-Li reconstruction.** `_coleman_li_scaling` matches SciPy's `CL_scaling_vector`
  (`v = ub - x` where `g < 0` and `ub` finite; `v = x - lb` where `g > 0` and `lb` finite;
  `1.0` otherwise), and `trf_bounds` reports `optimality = norm(g * v, inf)` — so
  `max(max_scaled)` genuinely equals `result.optimality`.
- **Cause/fate exactness in `compute_residuals`.** `~valid & ~on_axis == (h_q <= 0)` for
  finite inputs; `n_extended = invalid.sum() - unextendable.sum()` partitions the invalid set
  exactly; both marginals sum to `n_invalid` by construction.
- **Stage labelling in the library pipelines.** All four in-library call sites
  (`pipeline.py:156, 1033, 1283`; `datasets/pipelines.py:171, 206`) pass an explicit
  `discard_stage`, so E1 and E5 (which go through `calibrate_synthetic`) get a real stage
  split. E7 does not — see CR-02.
- **`benchmark.json` plumbing.** `assemble_benchmark_record` serializes `SolverDiagnostics`
  generically via `dataclasses.asdict`, so the two new fields reach the record without being
  named; `discard_stats` is passed through `_to_native` unmodified and copied at the call
  site, so no aliasing.
- **`check_rerun_gates.py` header mismatches** for the three reshaped artifacts are in scope
  of the phase's documented intent and are not reported here.

---

_Reviewed: 2026-08-17_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_

---

## Resolution log (orchestrator, 2026-08-17)

Applied during the Phase 24 code-review gate. Each finding was independently
verified against the code before any fix was made.

| ID | Verdict | Resolution | Commit |
|----|---------|-----------|--------|
| CR-01 | Confirmed | Collapse to one value per seed before summing. Regression test asserts hand-computed **absolute** totals (7, not 21 at 3 cameras) because the two-axes-agree tripwire is blind to a multiplicative error. Proven non-vacuous against the old logic. | `bc8cbf7` |
| CR-02 | Confirmed | Threaded `discard_stage=STAGE_INTERFACE` / `STAGE_INTRINSIC_PASS` into E7's two `joint_refinement` calls. Also makes the arm-merge comment true — the `__<stage>` suffixes are disjoint only once the stage is passed. | `9f42c0e` |
| WR-01 | Confirmed | `isfinite` guard on `interval_width`; scale on both bounds, not just `lower`. | `dfbbfe7` |
| WR-03 | Confirmed | Absence of `MERGED_DEGENERACY_COLUMN` is now the "never computed" discriminator. | `dfbbfe7` |
| WR-04 | Confirmed | `write_degeneracy_breakdown` gained `force: bool = False`; threaded through all six call sites. | `dfbbfe7` |
| WR-02, WR-05 … WR-10 | Not addressed | Left for the verifier and/or a follow-up. Not blocking; see each finding above. |

**Not a finding, confirmed by the reviewer and worth preserving:** the inertness
claim holds. `nan_reason_out` is written only at the four terminal failure
branches, never inside the Newton loop; the `int8` array is allocated only when
`degeneracy_breakdown_out` is supplied, which happens only on the single
post-solve `compute_residuals` call; nothing new reaches `cost_args`.
`build_parameter_block_slices` matches `pack_params` ordering exactly, and
`_coleman_li_scaling` faithfully reproduces SciPy's `CL_scaling_vector`.

Full suite after all fixes: see the phase completion report.
