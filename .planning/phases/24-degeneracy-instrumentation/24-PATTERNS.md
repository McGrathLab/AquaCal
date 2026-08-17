# Phase 24: Degeneracy Instrumentation - Pattern Map

**Mapped:** 2026-08-17
**Files analyzed:** 10 (2 library-core modules + 2 bump/warning sites + pipeline plumbing + 3
experiment writers + gate + tests)
**Analogs found:** 10 / 10 (every file this phase touches already has a directly-adjacent working
pattern in the same file or its sibling — this is an extension phase, not a new-module phase)

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|---|---|---|---|---|
| `src/aquacal/calibration/_observability.py` (`DISCARD_KEYS`, `_bump` call sites) | config/utility | event-driven (counter) | itself — existing `pnp_*` key family, lines 61-90 | exact (same file, same tuple, add sibling entries) |
| `src/aquacal/calibration/_observability.py` (`SolverDiagnostics` new field) | model/dataclass | request-response (populate-then-read) | itself — `n_params`/`n_params_reason` pair, lines 296-312 | exact |
| `src/aquacal/calibration/_optim_common.py` (`compute_residuals` — `h_c` recompute + denominator) | service | CRUD/transform | itself — existing `invalid_count_out` accumulation, lines 678-726 | exact |
| `src/aquacal/calibration/_optim_common.py` (per-block optimality decomposition, DEGEN-05) | service | transform | `build_structural_column_groups`, lines 421-519 | exact (same module owns the layout) |
| `src/aquacal/calibration/interface_estimation.py` (`optimize_interface` — stage kwarg, split bump, warning rewrite) | controller/service | request-response | itself — lines 379-434 (the whole capture→guard→warn block) | exact |
| `src/aquacal/calibration/refinement.py` (`joint_refinement` — same three edits) | controller/service | request-response | `interface_estimation.py` lines 379-434 (explicitly cross-referenced by refinement.py's own comment "see the matching block in interface_estimation") | exact |
| `src/aquacal/calibration/pipeline.py` (`problem_shape` mirror + `discard_stats` block in `benchmark_record`) | controller/orchestration | request-response | itself — lines 1707-1743, the `assemble_benchmark_record` call | exact |
| `src/aquacal/datasets/pipelines.py` (`discard_stage` kwarg at the two `joint_refinement`/`optimize_interface` call sites) | controller/orchestration | request-response | itself — lines 150, 188 (`calibrate_synthetic`) | exact |
| `experiments/e1_refractive_comparison.py` (CSV column + JSON sidecar for the split) | script/writer | batch/CRUD | `experiments/e6_generalization_sweep.py` lines 255-293, 750-789 (the working E6 band-column pattern) | exact (explicitly named in CONTEXT.md as the working analog) |
| `experiments/e5_index_sensitivity.py` (write the already-threaded `discard_stats_out`) | script/writer | batch/CRUD | `e6_generalization_sweep.py` same as above, plus E5's own already-existing `discard_stats_out` plumbing at lines 454-596 | exact |
| `experiments/e7_focal_standoff_analysis.py`/`e7_interface_ablation.py` (CSV column) | script/writer | batch/CRUD | `e6_generalization_sweep.py` same as above | role-match (E7 not yet inspected in detail; same column convention applies) |
| `experiments/check_rerun_gates.py` (`_guard_count_from_record` — read the split keys / zero-emission) | script/gate | request-response | itself — `_guard_count_from_record`, lines 204-219 | exact |
| `tests/synthetic/test_guard_inertness.py` (extend for new counters) | test | request-response | itself — existing inertness proof structure, lines 1-70 | exact |
| `tests/unit/test_discard_accounting.py` (kind/stage split, unattributed bucket, raise-on-unknown-stage, zero-emission, D-07 equivalence) | test | event-driven | itself — `make_degenerate_pose_inputs` + `test_discard_stats_out_is_numerically_inert`, lines 57-90 | exact |
| `tests/unit/test_e5_band_mode.py` (module-scope fixture, D-22) | test | batch | `tests/unit/test_e6_band_mode.py` lines 74-98 (`band_run_dir` fixture) | exact (named in CONTEXT.md as the mirror target) |
| `tests/synthetic/test_full_pipeline.py` (extend `run_calibration_from_config` harness for `discard_stats`, D-17) | test | request-response | itself — `_run_full_pipeline_with_mocked_video_io` + `TestBenchmarkJsonIntegration`, lines 509-657 | exact |

## Pattern Assignments

### `src/aquacal/calibration/_observability.py` — D-01/D-04 flat enumerated keys

**Analog:** itself, `DISCARD_KEYS` tuple and its existing convergence-diagnostic entry.

**The tuple to extend** (`_observability.py:61-90`):
```python
DISCARD_KEYS: tuple[str, ...] = (
    ...
    # Convergence-diagnostic guard count (plan 19.3-02, D-19.3-11). Counted once,
    # on the FINAL solution evaluation, per solver stage (optimize_interface's
    # Stage 3 and joint_refinement's Stage 3 intrinsic pass) -- never a running
    # per-iteration count. A non-zero value means first-order optimality is
    # unreliable as a convergence measure for this run (see
    # DegenerateObservationWarning); the library records this, it never raises.
    "degenerate_observations_at_solution",
)
```
> **STALE as of 2026-08-17 — D-06's reversal split the counter on TWO axes.** The example key
> below predates it and has no axis segment. The real scheme is
> `degenerate_observations_cause_{cause}__{stage}` (3 causes) and
> `degenerate_observations_fate_{fate}__{stage}` (2 fates), 18 new keys in all, `DISCARD_KEYS`
> 14 → 32. **`24-01-SUMMARY.md § Evidence` and `24-CONTEXT.md` are authoritative for key names;
> this file is not.**

D-01 appends flat entries here, e.g. `degenerate_observations_extended__stage3_interface_optimization`,
`degenerate_observations_interface_below_camera__unattributed`, plus a per-stage
denominator key (D-10) and (D-03) an `unattributed` stage bucket variant for every kind. The
merged `degenerate_observations_at_solution` key stays and its declaring comment (lines 83-88)
must be corrected — "counted once per stage on the final evaluation" is accurate per-call and
misleading in aggregate (it is now a cross-stage sum of the new split keys).

**The bump primitive to reuse unchanged** (`_observability.py:102-113`):
```python
def _bump(stats: dict[str, int] | None, key: str, n: int = 1) -> None:
    if stats is None:
        return
    stats[key] = stats.get(key, 0) + n
```
D-04's zero-init is a NEW call pattern layered on top of this — at stage entry, before any bump,
call `_bump(discard_stats_out, key, 0)` for every declared key of that stage's kind/stage
combination so a clean run still emits the key. `_bump`'s own body needs no change: `n=0` already
works (`stats[key] = stats.get(key, 0) + 0` creates the key at 0 if absent).

**Closed-vocabulary check to keep working, not touch structurally** (`_observability.py:116-170,
166-168`):
```python
unknown = sorted(set(stats) - set(DISCARD_KEYS))
if unknown:
    violations.append(f"undeclared counter keys: {unknown}")
```
This is exactly why D-01 rejected a nested detail sub-dict — flat keys keep this int-valued,
closed-vocabulary check untouched.

---

### `src/aquacal/calibration/_observability.py` — D-16 bound-hit `SolverDiagnostics` field

**Analog:** itself, the `n_params`/`n_params_reason` absent-metric pair.

**Field-declaration pattern to copy** (`_observability.py:296-312`):
```python
n_params: int | None = None
n_params_reason: str | None = None
n_groups: int | None = None
n_groups_reason: str | None = None
```
D-16's new field (e.g. `parameters_at_bound: list[str] | None` — discretion: names only, or
names+bound+gap) follows this same `value` / `value_reason` shape per the absent-metric
convention documented at class-docstring lines 242-246. Per Claude's Discretion, if it records
"which bound and by how much" it is still one field (a list of dicts or parallel lists), not
several — keep `capture_solver_diagnostics` the single writer.

**Population site to extend, not bypass** (`_observability.py:399-474`, `capture_solver_diagnostics`):
```python
def capture_solver_diagnostics(
    result,
    diagnostics_out: SolverDiagnostics | None,
    *,
    ftol: float,
    ...
) -> None:
    if diagnostics_out is None:
        return
    diagnostics_out.nfev = int(result.nfev)
    ...
```
D-16's corroboration note: `result.active_mask` already carries what's needed (`1`/`-1`/`0` per
parameter, bound gap via `result.x` vs `bounds`) — this is a plumbing job inside this function,
reading `result.active_mask` (a small array, not `result.jac`/`result.fun`, so it does not violate
the peak-memory prohibition the docstring explains at lines 417-421). Use `build_parameter_labels`
(same file, lines 315-396) to name which index is which, exactly as the class docstring
prescribes: *"This is how D-16 names which parameters hit a bound."* A pinned parameter (bound gap
~2e-12) must be distinguished from one that travelled to its bound (wide gap) — do not flag both
identically, per the corroboration note's warning about training away an always-red field.

---

### `src/aquacal/calibration/_optim_common.py` — D-06/D-10 `h_c` recompute + denominator

**Analog:** itself, the existing `invalid_count_out` accumulation inside `compute_residuals`.

**Signature and scope where the new logic lands** (`_optim_common.py:613-630`, and the unpacked
scope at 666-676):
```python
def compute_residuals(
    params: NDArray[np.float64],
    detections: DetectionResult,
    ...
    invalid_count_out: list[int] | None = None,
) -> NDArray[np.float64]:
    ...
    extrinsics, water_zs, board_poses, intrinsics = unpack_params(
        params, reference_camera, reference_extrinsics, camera_order, frame_order,
        base_intrinsics=base_intrinsics, refine_intrinsics=refine_intrinsics,
        normal_fixed=normal_fixed, shared_interface=shared_interface,
    )
```
`water_zs[cam_name]` and each camera's `extrinsics[cam_name]` (whose `.C` gives the camera
center) are already in scope right here — D-06's `h_c = water_zs[cam_name] - extrinsics[cam_name].C[2]`
comparison goes in the existing per-(camera, frame) loop below (lines 688-723), NOT inside the
per-point batch (`refractive_project_batch` call at 708) — matching the hot-path prohibition
documented at `_observability.py:51-56`.

**Where the existing invalid/extended/unextendable split already lives** (`_optim_common.py:706-723`):
```python
diff = projected_batch - detection.corners_2d
invalid = np.isnan(diff).any(axis=1)
if invalid.any():
    n_invalid += int(invalid.sum())
    extended = _extend_invalid_projections(camera, points_3d[invalid])
    diff_invalid = extended - detection.corners_2d[invalid]
    unextendable = np.isnan(diff_invalid).any(axis=1)
    diff_invalid[unextendable] = INVALID_PROJECTION_PENALTY_PX
    diff[invalid] = diff_invalid
residuals.append(diff.ravel())
```
This is D-06's Integration Point reference: `extended` vs `penalized`(`unextendable`) is already
computed here — that half of the kind split (`extended`, `penalized`) is nearly free by tagging
these two branches with `_bump`. `interface_below_camera` (the `h_c <= 0` case) is the one NEW
comparison, done once per (camera, frame) alongside this loop's existing per-batch work, not
per-point.

**Denominator (D-10):** add a bump of the per-stage observation count in this same loop — the pass
already iterates every (camera, frame) pair it evaluates, so the count and the kind splits come
from the same pass over the same data, per D-10's explicit rejection of `n_residuals / 2` and
`problem_shape` totals as derivation sources.

---

### `src/aquacal/calibration/_optim_common.py` — DEGEN-05 per-parameter-block decomposition

**Analog:** `build_structural_column_groups`, lines 421-519 (same file, the layout DEGEN-05
must not duplicate).

**The group-index scheme to reuse for bucketing per-block optimality** (`_optim_common.py:482-510`):
```python
n_tilt_params = 0 if normal_fixed else 2
n_extrinsic_params = 6 * (n_cams - 1)
n_pose_params = 6 * n_frames
n_intrinsic_params = 4 * n_cams if refine_intrinsics else 0

raw_groups = []
raw_groups.extend(range(n_tilt_params))                       # 0. tilt
raw_groups.extend(j % 6 for j in range(n_extrinsic_params))    # 1. extrinsics
n_water_z_params = 1 if shared_interface else n_cams
raw_groups.extend([6] * n_water_z_params)                      # 2. water_z (dedicated slot)
raw_groups.extend(7 + (j % 6) for j in range(n_pose_params))    # 3. board poses
raw_groups.extend(13 + (j % 4) for j in range(n_intrinsic_params))  # 4. intrinsics
```
This structural layout is the same one `build_parameter_labels` mirrors (`_observability.py:315-396`
docstring: "Mirrors `_optim_common.pack_params`'s layout exactly"). DEGEN-05's decomposition
groups the per-parameter KKT/gradient contribution (`J^T f` at the solution, analogous to
`OptimizerObserver.wrap_jac`'s `grad = J.T @ f` computation at `_observability.py:585-588`) into
these same structural buckets (tilt, extrinsics, water_z, board poses, intrinsics) rather than
re-deriving a parallel layout in `experiments/` — this is the explicit reasoning in CONTEXT.md's
DEGEN-05 addendum: *"computing it in `experiments/` would duplicate that layout... the exact drift
that function's docstring exists to prevent."* Implement alongside D-16 (both are solve-level
`SolverDiagnostics` fields keyed by parameter, both want `build_parameter_labels`).

---

### `src/aquacal/calibration/interface_estimation.py` / `refinement.py` — D-02/D-03 stage kwarg,
split bump, warning rewrite

**Analog:** `interface_estimation.py` lines 379-434 is its own analog for `refinement.py`'s
matching block — `refinement.py`'s existing comment even says so ("Degeneracy guard -- see the
matching block in interface_estimation").

**The block both files edit adjacently** (`interface_estimation.py:407-434`):
```python
if result.status <= 0:
    raise ConvergenceError(f"Optimization failed: {result.message}")

# Degeneracy guard. ...
invalid_counts: list[int] = []
compute_residuals(result.x, *cost_args, invalid_count_out=invalid_counts)
n_invalid = invalid_counts[0] if invalid_counts else 0
_bump(discard_stats_out, "degenerate_observations_at_solution", n_invalid)
if n_invalid > 0:
    warnings.warn(
        f"Stage 3 finished with {n_invalid} observation(s) the refractive "
        f"model could not project (corners at or above the water surface, "
        f"or behind a camera). These were continued with a pinhole "
        f"extension, which puts the residual on a C0-but-not-C1 kink at "
        f"the refractive/pinhole boundary -- first-order optimality "
        f"({getattr(result, 'optimality', float('nan')):.4g}, termination "
        f"status {result.status}) is UNRELIABLE as a convergence measure "
        f"here, and neither it nor the reprojection RMS can be trusted to "
        f"judge convergence. Fix the scenario geometry so no corner sits "
        f"at or above the interface; do not re-tune the solver.",
        DegenerateObservationWarning,
        stacklevel=2,
    )
```
`refinement.py:325-345` is line-for-line the same shape with `"Stage 3's intrinsic pass finished
with..."` phrasing. D-02's new `discard_stage: str` kwarg is added to both function signatures
(`optimize_interface` at `:135`, `joint_refinement` at `refinement.py:41`); D-03's `unattributed`
default and raise-on-unrecognized-string logic belongs at the top of each function body, validated
once before the solve rather than at this trailing block. The `_bump` call here becomes
`n_invalid`-many calls into the flat split keys (kind × `discard_stage`), still routed through the
unchanged `_bump` primitive. The warning rewrite (D-13/D-14/D-15) replaces the single always-fired
`if n_invalid > 0` block with fraction-and-kind-aware branching — keep the "do not re-tune the
solver" / geometry-vs-hardware framing but narrow per D-15's C0-not-C1, per-parameter-gradient
qualification (see CONTEXT.md's 2026-08-17 amendment — do NOT claim "optimality remains
meaningful for them").

**Diagnostics capture immediately above, for context on ordering** (both files, `capture_solver_diagnostics(...)`
called BEFORE the `result.status <= 0` raise) — `refinement.py:290-293`'s comment explains why:
*"Capturing after the raise would silently drop diagnostics for exactly the runs... where they are
most diagnostic."* DEGEN-05's decomposition and D-16's bound-hit field should be captured in this
same pre-raise position, inside `capture_solver_diagnostics` itself (see `_optim_common.py`/
`_observability.py` pattern above) so a non-converged run still gets them.

---

### `src/aquacal/calibration/pipeline.py` — D-11 `problem_shape` mirror + `discard_stats` block

**Analog:** itself, the existing `assemble_benchmark_record` call and its `problem_shape` dict.

**The gap D-11 fixes** (`pipeline.py:1709-1741`):
```python
problem_shape = {
    "n_cameras": len(final_intrinsics),
    "n_frames_calibration": len(optim_detections.frames),
    "n_frames_holdout": len(val_detections.frames),
}
...
benchmark_record = assemble_benchmark_record(
    problem_shape=problem_shape,
    timings=timings,
    diagnostics=solver_diagnostics,
    solver_config=solver_config,
    accuracy=accuracy,
    environment=capture_environment(),
    memory_readings=memory_readings if config.benchmark_memory else None,
)
write_benchmark_json(benchmark_record, config.output_dir / "benchmark.json")
```
`discard_stats` (the run-scoped dict, already populated at `pipeline.py:766` and threaded to six
`_bump` sites) exists in this function's scope already — it is saved into `diagnostic_report` at
line 1623 (`discard_stats=dict(discard_stats)`) but never reaches `benchmark_record`. D-11 (a) adds
`problem_shape["degenerate_observations_at_solution"] = discard_stats.get(...)` — mirroring E1's
own `write_direct_call_benchmark` pattern below — and (b) passes the WHOLE `discard_stats` dict as
a new top-level `discard_stats` key to `assemble_benchmark_record` (requires a signature change
there; see `io/benchmark.py:385-395` for the existing keyword-arg style to match). This is exactly
the `check_rerun_gates.py:212-218` third read shape (`record.get("discard_stats")`) already
expects.

**The console summary this sits beside, unaffected** (`pipeline.py:1627-1639`):
```python
if discard_stats:
    _violations = check_discard_invariants(discard_stats)
    print("  Discards: " + ", ".join(f"{k}={discard_stats[k]}" for k in sorted(discard_stats)))
    if _violations:
        print(f"  WARNING: discard-counter invariant violated: {_violations}")
```
No change needed here — `check_discard_invariants` already iterates whatever keys are present, so
the new flat split keys are picked up automatically once D-01 declares them.

---

### `src/aquacal/datasets/pipelines.py` — D-02 stage kwarg at both call sites

**Analog:** itself — `calibrate_synthetic`'s two solver calls.

**The two sites needing distinct `discard_stage` values** (`pipelines.py:150-171` and `:186-206`):
```python
opt_extrinsics, opt_distances, opt_poses, rms = optimize_interface(
    detections=detections, ...,
    discard_stats_out=discard_stats_out,
    water_z_bounds=water_z_bounds,
)
...
if refine_intrinsics:
    opt_extrinsics, opt_distances, opt_poses, opt_intrinsics, rms = joint_refinement(
        stage3_result=stage3_result, ...,
        discard_stats_out=discard_stats_out,
        water_z_bounds=water_z_bounds,
    )
```
D-02's motivating example is precisely this file: `joint_refinement` is called from `pipeline.py`
at both Stage 3 joint (`pipelines.py:159` in CONTEXT.md's line numbering, matches `:150` here for
`optimize_interface` — line drift from context capture is expected) and the intrinsic pass
(`:192`/`:188` here) with different stage identities, and the module cannot tell which. Add
`discard_stage="stage3_interface_optimization"` to the first call and
`discard_stage="stage3_intrinsic_pass"` to the second — matching the exact stage-name vocabulary
already used as dict keys elsewhere in this file (`diagnostics_out.get("stage3_interface_optimization")`
at line 145, `diagnostics_out.get("stage3_intrinsic_pass")` at line 182), so the new kwarg reuses
strings the codebase already treats as the canonical stage vocabulary rather than inventing new
ones.

---

### `experiments/e1_refractive_comparison.py` / `e5_index_sensitivity.py` / `e7_*.py` — D-09 CSV
column + JSON sidecar

**Analog:** `experiments/e6_generalization_sweep.py` — the working, already-shipped E6 band-column
pattern (explicitly named in CONTEXT.md as what to copy).

**E6's column declaration, append-only** (`e6_generalization_sweep.py:255-293`):
```python
E6_COLUMNS = [
    ...
    "num_comparisons",
    "num_frames",
    # D-19.3-11/plan 19.3-07: the final-solution guard count this
    # configuration's calibrate_synthetic call recorded via
    # discard_stats_out["degenerate_observations_at_solution"]. Appended
    # last so every existing column keeps its position. ...
    "degenerate_observations_at_solution",
    # FIX-03 (23-03): appended, never inserted, so E6_COLUMNS keeps every
    # prior column's position ...
    "water_z_error_mm_signed_mean",
    "z_position_error_mm_gauge_corrected_mean",
]
assert len(E6_COLUMNS) == 33 and len(set(E6_COLUMNS)) == 33
```

**E6's row-builder, populating it from `discard_stats_out`** (`e6_generalization_sweep.py:750-789`):
```python
def _build_row(..., degenerate_count: int | None) -> dict:
    """
    ...
    degenerate_count: The final-solution guard count recorded via
        `discard_stats_out["degenerate_observations_at_solution"]`, or
        `None` when it was never computed for this row (e.g. a
        `"failed"` or `"skipped_existing"` row predating this column).
    """
    row = {
        ...
        "status": status,
        "status_reason": status_reason,
        "degenerate_observations_at_solution": degenerate_count,
    }
```
And the call-site sequence that produces `degenerate_count` (`e6_generalization_sweep.py:1098,
1125`):
```python
n_degenerate = discard_stats.get("degenerate_observations_at_solution", 0)
...
outcome["degenerate_observations_at_solution"] = n_degenerate
```

> **STALE as of 2026-08-17 — D-09 was revised to publish BOTH axes: six columns, not four.**
> The real list is the merged total plus `degenerate_observations_cause_above_interface`,
> `..._cause_behind_camera`, `..._cause_interface_below_camera`, `..._fate_extended`,
> `..._fate_penalized`. Each axis independently sums to the merged total, which is what makes the
> CSV self-validating — do not sum cause and fate columns together. See `24-CONTEXT.md` § D-09's
> REVISED note. The paragraph below is retained for its *append-at-end* convention, which is
> unchanged and still correct.

**D-09's ~4-column plan (merged + one per kind)**: E1/E5/E7 each append `E6_COLUMNS`-style entries
for the merged total (mirroring E6's `"degenerate_observations_at_solution"` column exactly, same
name, same append-at-end convention) plus one column per kind (e.g.
`degenerate_observations_extended`, `degenerate_observations_penalized`,
`degenerate_observations_interface_below_camera`) — NOT the full kind × stage cross product,
which goes to the JSON sidecar instead (discretion: filename/location, avoid colliding with
`e{1,5,6,7}_seed_band_provenance.json`).

**E1's existing (partial) analog — problem_shape only, no CSV yet** (`e1_refractive_comparison.py:667-681`):
```python
write_direct_call_benchmark(
    record_path,
    problem_shape={
        "n_cameras": len(scenario.intrinsics),
        "n_frames_calibration": len(scenario.board_poses),
        "n_frames_holdout": 0,
        # D-19.3-11: the final-solution guard count, recorded (never
        # gated) for this arm.
        "degenerate_observations_at_solution": discard_stats_by_model[label].get(
            "degenerate_observations_at_solution", 0
        ),
    },
    ...
)
```
This is the JSON-only half already done; D-09 additionally wants this value (plus the kind split)
appended to E1's own CSV row-builder (`_build_dataframes`, not yet inspected in this pass — locate
via the `df_exp1`/`df_exp2`/`df_exp3` construction near `e1_refractive_comparison.py:637`) using
E6's exact append-at-end column convention above.

**E5's plumbing is already wired, only the write is missing** (`e5_index_sensitivity.py:454-500,
533-596`): `run_index_point`/`run_band` already accept and thread `discard_stats_out` (summed
across the band per the docstring at lines 552-561: *"Summed across the whole band rather than
kept per-point... the attribution question... is answered at the band level"*). D-09's E5 work is
adding the resulting summed dict as a column via `build_row`/`E5_COLUMNS` (declared at
`e5_index_sensitivity.py:122-140`) — the same append-only pattern as E6.

---

### `experiments/check_rerun_gates.py` — D-04/D-11 zero-emission reachability

**Analog:** itself, `_guard_count_from_record`.

**The three read shapes, unaffected by D-01's flat-key choice, but needing the split keys added**
(`check_rerun_gates.py:204-219`):
```python
_GUARD_COLUMN = "degenerate_observations_at_solution"

def _guard_count_from_record(record: dict) -> int | None:
    """Extract the final-solution guard count from any of the shapes this
    project's provenance records carry it in: a direct-call benchmark
    record's `problem_shape`, an E6 per-configuration checkpoint's top level,
    or a `discard_stats` block (E5's provenance sidecar). Returns `None` if
    none of the three shapes carries the field.
    """
    problem_shape = record.get("problem_shape")
    if isinstance(problem_shape, dict) and _GUARD_COLUMN in problem_shape:
        return problem_shape[_GUARD_COLUMN]
    if _GUARD_COLUMN in record:
        return record[_GUARD_COLUMN]
    discard_stats = record.get("discard_stats")
    if isinstance(discard_stats, dict) and _GUARD_COLUMN in discard_stats:
        return discard_stats[_GUARD_COLUMN]
    return None
```
The FAIL branch this makes reachable (`check_rerun_gates.py:348-355`):
```python
count = _guard_count_from_record(record)
...
f"{label}: no {_GUARD_COLUMN!r} field found (cannot confirm zero)",
```
D-04's zero-init plus D-11's mirror together make this branch pass instead of FAIL on a clean
production run for the first time — no code change needed to `_guard_count_from_record` itself
since it already reads the merged key from all three shapes; D-12 says the gate IS updated in this
same phase but the driver (`rerun_19_3.sh`'s stage list) is Phase 26's. If the gate needs to be
made aware of the new per-kind/per-stage keys (e.g. for a richer report), extend this same
three-shape lookup function rather than writing a parallel one.

---

## Shared Patterns

### The `_bump`/opt-in-out-parameter convention
**Source:** `_observability.py:44-49, 102-113`
**Apply to:** every new counter site in `_optim_common.py`, `interface_estimation.py`, `refinement.py`
```python
def _bump(stats: dict[str, int] | None, key: str, n: int = 1) -> None:
    if stats is None:
        return
    stats[key] = stats.get(key, 0) + n
```
`stats is None` is a single identity test with zero behavior change for every existing caller —
D-04's zero-init must preserve this (no dict, no keys, when `discard_stats_out=None`).

### Hot-path prohibition
**Source:** `_observability.py:51-56`
**Apply to:** D-06's `h_c` check and D-10's denominator — both computed per-(camera, frame), never
per-point/per-residual, exactly like the existing `invalid`/`n_invalid` accounting in
`compute_residuals`.

### Absent-metric convention (`value` + `value_reason`, never silent omission)
**Source:** `_observability.py:242-246` (class docstring), applied at `n_params`/`n_params_reason`
**Apply to:** D-16's bound-hit field and DEGEN-05's decomposition field on `SolverDiagnostics`.

### Append-only experiment columns
**Source:** `e6_generalization_sweep.py:255-293` (`E6_COLUMNS`, with two separate append comments
documenting two separate phases' additions, plus the `assert len(E6_COLUMNS) == 33` guard)
**Apply to:** E1/E5/E7's new columns (D-09) — always appended at the end, with an inline comment
citing the requirement, never inserted mid-list.

### Closed-vocabulary, cross-check-driven counter validation
**Source:** `_observability.py:116-190` (`check_discard_invariants`/`check_denominator_only`)
**Apply to:** no code change required by this phase (D-01 deliberately preserves it), but
`tests/unit/test_discard_accounting.py` is the place new split-key invariants (if any) would be
asserted, following its existing A. Inertness / B. Counter correctness split.

### Diagnostics captured before the convergence raise
**Source:** `refinement.py:290-293` comment + both `capture_solver_diagnostics(...)` call
placements in `interface_estimation.py`/`refinement.py`
**Apply to:** DEGEN-05's decomposition and D-16's bound-hit field — must be captured inside/via
`capture_solver_diagnostics` before the `if result.status <= 0: raise` line, so a non-converged
run still records them.

## No Analog Found

None. Every file this phase touches has a directly-adjacent, already-working pattern in the same
file (bump sites, diagnostics capture, column declarations) or an explicitly-named sibling
(`e6_generalization_sweep.py` for E1/E5/E7; `test_e6_band_mode.py` for `test_e5_band_mode.py`).
This phase is uniformly an *extension* of established machinery, per CONTEXT.md's Reusable Assets
list — no new architectural pattern is being introduced.

## Metadata

**Analog search scope:** `src/aquacal/calibration/` (`_observability.py`, `_optim_common.py`,
`interface_estimation.py`, `refinement.py`, `pipeline.py`), `src/aquacal/datasets/pipelines.py`,
`src/aquacal/io/benchmark.py`, `experiments/` (`e1_refractive_comparison.py`,
`e5_index_sensitivity.py`, `e6_generalization_sweep.py`, `check_rerun_gates.py`), `tests/unit/`
(`test_discard_accounting.py`, `test_e5_band_mode.py`, `test_e6_band_mode.py`), `tests/synthetic/`
(`test_guard_inertness.py`, `test_full_pipeline.py`).
**Files scanned:** 14 read directly (several via targeted offset/limit reads on large files), plus
grep sweeps across `experiments/` and `tests/`.
**Pattern extraction date:** 2026-08-17
