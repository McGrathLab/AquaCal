# Phase 16: Experiment Observability Hooks - Research

**Researched:** 2026-07-23
**Domain:** scipy.optimize.least_squares internals, in-repo pipeline/synthetic-generator audit
**Confidence:** HIGH (all four priority questions resolved by reading/running actual code, not assumption)

## Summary

All four priority investigations produced concrete, actionable answers. The most
consequential finding overturns a `<priority_questions>` framing assumption rather than a
locked CONTEXT.md decision: **`least_squares` in the installed scipy (1.17.0) has a
`callback` parameter (added 1.16.0)**, which is a far better HOOK-02 mechanism than
wrapping `fun`/`jac`. This does not touch any locked decision — CONTEXT.md is silent on
*how* the trace is captured, only on its scope and format — but it does invalidate the
research prompt's premise that no callback exists, so HOOK-02's implementation plan should
change accordingly. `scipy` is currently unpinned in `pyproject.toml`; using `callback`
requires adding a `scipy>=1.16` floor.

`result.jac` (HOOK-03) is confirmed reliable: it is the Jacobian at the **accepted** solution
point, evaluated by the exact same custom dense-`jac` callable the pipeline already passes,
never a rejected trial step. The locked "reuse `result.jac`" decision stands.

The memory question (HOOK-03) resolves more favorably than CONTEXT.md's framing feared: the
727×727 correlation matrix itself is trivially small (~4.2 MB). The real risk is computing an
SVD of the *dense Jacobian* directly (`scipy.linalg.svd(J)`), which allocates a `U` matrix the
same size as `J` itself (another ~3.6-7 GB on top of the existing peak). This is avoidable:
compute the Gram matrix `J.T @ J` (n×n, tiny) and eigendecompose that instead of calling
`svd(J)` directly — this sidesteps the large `U` allocation entirely, at a real but documented
numerical cost (squaring halves the precision of small singular values, which is exactly what
the WP6 degeneracy argument cares about). This tradeoff needs a decision, not just an
estimate — flagged as an open question below.

HOOK-05 and HOOK-06 audits confirm the CONTEXT.md prediction only partially. HOOK-06
(seeding) is close to done but has one real, config-level gap: **the pipeline's own
holdout split (`pipeline.py:706-707`) never receives a seed at all** — `split_detections`
takes a seed parameter but the pipeline call site doesn't pass one, so it silently defaults
to 42 with no way to change it via config. HOOK-05 (generator knobs) has one genuine, larger
gap: **refractive index is NOT plumbed through `generate_synthetic_detections` at all** — it
hardcodes `Interface`'s default `n_water=1.333`/`n_air=1.0` with no override parameter, and
`SyntheticScenario` has no field recording what index was used. Tank-scale and working
distance, by contrast, are genuinely already independently controllable at the generator-
function level (just not through the `create_scenario()` presets).

**Primary recommendation:** Use scipy's native `callback` for HOOK-02 (requires bumping the
`scipy` dependency floor to `>=1.16`), reuse `result.jac` for HOOK-03 as planned but compute
the correlation matrix via `eigh(J.T @ J)` rather than `svd(J)` (surface the numerical
tradeoff to the user, don't silently pick), add an `n_water`/`n_air` parameter to
`generate_synthetic_detections` (real HOOK-05 gap), and thread a seed into the pipeline's
`split_detections` call plus record all seeds used in `benchmark.json`/output metadata (real
HOOK-06 gap).

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**How hooks get switched on**
- Flat config keys on `CalibrationConfig` (e.g. `save_optimization_trace`,
  `save_conditioning`, `save_stage_calibrations`) — matches `save_detailed_residuals`
  precedent. No nested `diagnostics:` sub-dataclass.
- Per-hook switches, no master flag — costs differ by orders of magnitude.
- Config-only — no CLI flags. `benchmark.json` (Phase 19) records "solver configuration in
  force" from config; CLI overrides would create a second source of truth.
- Defaults: stage dumps ON, trace and conditioning OFF.

**Artifact layout and format**
- New artifacts land in `output_dir/internals/` (not `diagnostics/` — that name is taken by
  `diagnostics.json`).
- Trace format: CSV (matches `spatial_measurements.csv` / `depth_errors.csv` precedent).
- Conditioning format: split — condition number + singular-value spectrum to JSON, full
  correlation matrix to `.npz`.
- Repeat runs overwrite, but warn when clobbering (matches `calibration.json` today).

**Trace scope (HOOK-02)**
- All bundle-adjustment stages, one file each: Stage 3, the post-outlier-rejection re-run,
  and the intrinsic pass (Stage 4) each get their own trace file.

**Conditioning diagnostics (HOOK-03)**
- Full singular-value spectrum AND full parameter correlation matrix, not just the
  camera-height ↔ water_z block. User accepted the memory risk explicitly; research must
  verify headroom, and if it doesn't fit, raise it rather than silently narrowing scope.
- Computed for whichever stage produced the final reported result (Stage 3, or the
  intrinsic pass when enabled). One matrix per run.
- Reuse `result.jac` from `least_squares` rather than recomputing — research must confirm
  it's populated/trustworthy on the custom-`jac`-callable path (**CONFIRMED, see Q1 below**).
- Pre-check the allocation and refuse with a clear message naming the estimated size and the
  config key to disable. Do NOT silently degrade to a narrower metric.

**API surface**
- `evaluate_calibration` (HOOK-04) becomes a top-level `aquacal.` export (16th name).
- Conditioning diagnostics live in `aquacal.validation.*`, documented and importable, no
  semver promise yet.
- Held-out evaluation reports the same structure the pipeline already produces.
- Pipeline refactored to call the new standalone function — one code path, guarded by a
  regression test asserting pipeline output is unchanged.

**No assumption-override parameter needed**
- WP4's "evaluate under perturbed assumptions" is encoded in the held-out set (generated at
  a different n), not a parameter on `evaluate_calibration`.

### Claude's Discretion
- Stability marking (stable vs. experimental) for the two new entry points.
- Exact config key names, beyond the `save_*` prefix convention.
- Structure of stage-dump filenames within `internals/`.
- Whether the pre-check estimates memory analytically or probes it.

### Deferred Ideas (OUT OF SCOPE)
- Reducing peak memory (dense `.toarray()` Jacobian, ~3.6 GB) — PERF-01, Future.
- CLI exposure of the diagnostics hooks — rejected to keep one source of truth for
  `benchmark.json`.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-------------------|
| HOOK-01 | Dump each stage's intermediate calibration (post-Stage-2, post-Stage-3, post-intrinsic-refinement) | §5 below: post-Stage-2 already dumped (`calibration_initial.json`, `pipeline.py:795`); post-Stage-3 and post-Stage-4 have **no** `CalibrationResult` built today — must construct one at each point via the existing `_build_calibration_result` helper, same pattern as line 769-792 |
| HOOK-02 | Opt-in per-iteration trace (iteration, cost, step norm, optimality, interface params) for all BA stages | §6 below: use scipy's native `callback` param (confirmed present, scipy 1.17.0, added 1.16.0) instead of wrapping fun/jac; enumerates all `least_squares` call sites needing tracing |
| HOOK-03 | Conditioning diagnostics at solution: SV spectrum/condition number + parameter correlation matrix | §1 (Q1) confirms `result.jac` reliability; §2 (Q2) gives concrete memory analysis and a Gram-matrix alternative to direct SVD |
| HOOK-04 | Standalone callable held-out evaluation, refactored pipeline, regression-tested | §7 below: exact extraction boundaries in `pipeline.py` lines 1108-1235, proposed `evaluate_calibration` signature, regression test shape |
| HOOK-05 | Synthetic generator audit: n_water, layout, tank-scale/working-distance independently controllable, returns ground truth | §3 (Q3): tank-scale/working-distance ARE already independent; refractive index is NOT plumbed through detection generation — real gap |
| HOOK-06 | Every sweep entry point accepts and threads a seed | §4 (Q4): seed is threaded almost everywhere already; real gap is the pipeline's own `split_detections` call site not passing a seed, and no output records which seed was used |

</phase_requirements>

## Priority Question Findings

### Q1: Is `result.jac` usable for conditioning (HOOK-03)? — YES, CONFIRMED

Traced `scipy/optimize/_lsq/trf.py` (scipy 1.17.0, both `trf_bounds` and `trf_no_bounds`
code paths) and ran two empirical tests.

**Code evidence** (`trf.py:368-377`, `trf_no_bounds` mirrors this at ~543-552):
```python
if actual_reduction > 0:
    x = x_new
    f = f_new
    ...
    cost = cost_new
    J = jac(x)          # <-- only called after a step is ACCEPTED
    njev += 1
```
`jac(x)` (the custom dense callable from `make_sparse_jacobian_func`,
`_optim_common.py:584-639`) is invoked **only inside the `actual_reduction > 0` branch**,
i.e., strictly after the trial step at `x_new` has been accepted and `x` reassigned to it.
A rejected trial step (`actual_reduction <= 0`, the inner `while` loop) never triggers a
`jac` call. The last `jac(x)` call before the loop exits is therefore always at the
accepted point that becomes `result.x`.

**Empirical confirmation** (`/tmp/test_jac_callback2.py`, run against a small linear
least-squares problem with a custom dense `jac` that logs every call):
```
njev 4  len(call_log) 4  len(trace) 3
result.jac matches last jac call x? True
```
`result.jac` is bit-identical to the array returned by the last call to the custom `jac`
callable, confirming it is the accepted-step Jacobian, not a stale/rejected one.

**Type/shape:** `result.jac` is a plain dense `numpy.ndarray` of shape `(m, n)` — because
`make_sparse_jacobian_func` already does `.toarray()` when under the 500M-element
`dense_threshold` (`_optim_common.py:621,631-636`). If a future run exceeds that threshold
and falls back to sparse, `result.jac` would be a sparse matrix instead — the conditioning
code must handle both, or (simpler) explicitly require the dense path and refuse loudly if
`use_dense` was `False` for this run (this is knowable from the same `n_elements` check).

**Verdict: the locked design decision is sound. No alternative needed.**

### Q2: Does the full correlation matrix fit in memory?

**The correlation matrix itself is not the risk — it's tiny.** For P=727 (worst case),
`727 × 727 × 8 bytes ≈ 4.2 MB`. This is negligible next to the existing ~3.6 GB peak.
CONTEXT.md's framing ("a dense 727×727 correlation matrix plus SVD workspace lands on top
of [the 3.6 GB peak]") conflates two very different costs — the matrix is cheap, the *SVD
workspace* is the expensive part, and how expensive depends entirely on which SVD routine
is used.

**Two implementation paths, very different memory profiles:**

1. **Direct `scipy.linalg.svd(J, full_matrices=False)` on the m×n dense Jacobian.**
   `full_matrices=False` still returns `U` of shape `(m, min(m,n))` = `(m, n)` since m≫n
   here. `U` is therefore **the same size as `J` itself** — computing this SVD means
   holding both `J` (already resident as `result.jac`) and a same-sized `U` simultaneously,
   i.e., roughly **doubling** the ~3.6-4 GB Jacobian footprint (LAPACK's `gesdd`/`gesvd`
   also needs O(m·n) scratch space internally, pushing it higher still). This is the
   scenario CONTEXT.md was worried about, and the worry is justified for this path.

2. **Gram-matrix approach: `G = J.T @ J` (n×n), then `eigh(G)`.** `G` is only
   `727×727×8 ≈ 4.2 MB`. Singular values of `J` are `sqrt(eigenvalues of G)`; the
   eigenvectors of `G` are exactly `J`'s right singular vectors `V`, which is everything
   needed for both the full singular-value spectrum and the parameter correlation matrix
   (`V @ diag(1/s²) @ V.T`, scaled by residual variance). This path needs **no
   Jacobian-sized workspace at all** beyond the matrix-multiply `J.T @ J` itself (BLAS
   `dsyrk`/`dgemm` streams over `J` without a full second m×n allocation). Time cost is
   `O(m·n²)`; with m on the order of hundreds of thousands and n≈727, this is tens of
   seconds of BLAS-bound compute, not a memory problem.

   **Numerical caveat (must be surfaced, not hidden):** squaring `J` into `J.T @ J`
   squares the condition number and roughly **halves the number of accurate digits** in
   small singular values relative to a direct SVD of `J`. This matters specifically
   *because* HOOK-03 exists to detect near-degenerate directions (the camera-height ↔
   water_z coupling) — exactly where the small end of the spectrum is the signal. A
   direct SVD is numerically the right tool for this diagnostic; the Gram-matrix shortcut
   trades that away for memory safety.

**Could not determine without a live run:** the actual `m` (residual count) for the
13-camera/100-frame rig. `n_elements = m × n ≤ dense_threshold` (500M) is required for the
existing `.toarray()` path to have been taken at all (confirmed it does today, since the
"peak ~3.6 GB" figure is on record) — from `3.6e9 / 8 bytes / n≈673 ≈ 668,000` this
suggests `m` is in the ~600-700K range, but this is a back-calculation from an
already-uncertain peak-memory figure (which may include non-Jacobian allocations per the
open `PERF-01` todo's own "suspected driver" language), not a verified measurement.
**Recommend the implementation compute the actual `m × n` from the live run and use it in
the pre-check formula rather than trusting this estimate.**

**Recommended pre-check formula** (parametrized, since exact `m` is unverified):
```
additional_bytes_if_direct_svd  ≈ 2 * m * n * 8    # J.T-sized U, worst case ~2x J
additional_bytes_if_gram_eigh   ≈ n * n * 8 * 3     # G, eigenvectors, small scratch — trivial
available = <psutil or platform-probe> or a configured RAM ceiling
if approach == "direct_svd" and additional_bytes_if_direct_svd > safety_fraction * available:
    raise ConditioningMemoryError(
        f"Conditioning diagnostics would need ~{additional_bytes_if_direct_svd/1e9:.1f} GB "
        f"beyond the existing calibration peak. Disable with save_conditioning: false, "
        f"or the implementation should fall back to the Gram-matrix method (numerically "
        f"weaker for small singular values)."
    )
```
No `psutil` dependency exists today (`pyproject.toml` has no such entry) — either add one
(small, well-known, no I/O) or use a stdlib/platform-specific probe. **This is a genuine
open question for the planner: which SVD path is the default, and is memory probed or only
estimated analytically?** CONTEXT.md left "whether the pre-check estimates memory
analytically or probes it" as Claude's discretion — this research recommends analytical
(no new dependency, and the actual failure mode — OOM — doesn't need a live probe to avoid,
just a conservative constant-factor estimate against a configurable ceiling).

**Verdict:** the correlation matrix is not the constraint CONTEXT.md feared. The open
question is whether HOOK-03 uses direct SVD (numerically correct for the degeneracy
argument, ~2x memory) or Gram-matrix eigh (memory-safe, numerically weaker exactly where
the paper's argument needs precision). **This is a real design decision the planner must
make, not a research gap** — recommend surfacing both options to the user rather than
silently picking one, since CONTEXT.md was explicit about not silently narrowing scope.

### Q3: How much of HOOK-05 is already done?

Read `src/aquacal/datasets/synthetic.py` in full (741 lines).

**Confirmed already satisfied:**
- `SyntheticScenario` (line 31-55) carries ground-truth `board_poses: list[BoardPose]` and
  `water_zs: dict[str, float]` — confirmed present exactly as the preliminary scoping
  found.
- `generate_camera_array` (line 121-212) genuinely implements `"ring"` layout (line
  168-176: `angles = np.linspace(0, 2*pi, n_cameras, endpoint=False)`, positions on a
  circle of `radius = spacing * n_cameras / (2*pi)`), plus `"grid"` and `"line"` — three
  real layouts, not stubs.
- **Tank-scale and working distance ARE independently controllable**, but only at the
  generator-function level, not through `create_scenario()`'s three presets:
  - Tank/rig scale: `generate_camera_array(spacing=...)` controls inter-camera spacing;
    for `"ring"` layout this also sets the ring radius.
  - Working distance: `generate_board_trajectory(depth_range=..., xy_extent=...)` and
    `generate_dense_xy_grid(depth=..., xy_extent=...)` control board-to-camera depth
    independently of camera spacing. These are separate function parameters passed by
    the caller — a sweep script calling these directly (not through `create_scenario`)
    already has full independent control today.

**Real gap found — refractive index is NOT sweepable end-to-end:**
`generate_synthetic_detections` (line 453-534) constructs
`Interface(normal=interface_normal, camera_distances={cam_name: water_zs[cam_name]})`
at line 496-499 — **no `n_air`/`n_water` argument is passed**, so it always uses
`Interface.__init__`'s defaults (`n_air: float = 1.0, n_water: float = 1.333`, confirmed in
`src/aquacal/core/interface_model.py:28-29,43-44`). There is no parameter anywhere in the
call chain (`generate_synthetic_detections` → `Interface` → `refractive_project`) to
override this. `SyntheticScenario` also has no `n_water`/`n_air` field, so even if a caller
hand-built an `Interface` with a different index elsewhere, the scenario's own ground truth
wouldn't record which index actually generated the detections.

This is exactly the WP4 requirement ("calibrate at n=1.333 and evaluate against ground
truth generated at a different n") and it does not work today without a code change.
**Required fix:** add `n_air: float = 1.0, n_water: float = 1.333` parameters to
`generate_synthetic_detections`, thread them into the `Interface(...)` construction, and
add matching fields to `SyntheticScenario` so the ground truth records what was used.

**Verdict:** two of three sweep axes (layout, tank-scale/working-distance) need no new
code — only a sweep script calling the existing generator functions directly. Refractive
index is a real, small, well-localized gap (one function signature + one dataclass field).

### Q4: How much of HOOK-06 is already done?

**Entry points enumerated, with seed status:**

| Entry point | Seed status |
|---|---|
| `generate_camera_intrinsics` | No randomness — deterministic, no seed needed |
| `generate_camera_array` (`synthetic.py:129`) | `seed: int = 42` param, threaded into `np.random.default_rng(seed)` — accepts a seed |
| `generate_board_trajectory` (`synthetic.py:299`) | `seed: int = 42`, `np.random.default_rng(seed)` — accepts a seed |
| `generate_real_rig_trajectory` (`synthetic.py:347`) | `seed: int = 42`, `np.random.default_rng(seed)` — accepts a seed |
| `generate_dense_xy_grid` (`synthetic.py:404`) | `seed: int = 42`, `np.random.default_rng(seed)` — accepts a seed |
| `generate_synthetic_detections` (`synthetic.py:461`) | `seed: int = 42`, `np.random.default_rng(seed)` for pixel noise — accepts a seed |
| `create_scenario` (`synthetic.py:621`) | `seed: int = 42` — threads to whichever generator functions it calls internally |
| `split_detections` (`pipeline.py:442-445`) | `seed: int = 42` param exists on the **function**, uses `random.Random(seed)` |
| **Pipeline's own call to `split_detections`** (`pipeline.py:706-707`) | **GAP: `split_detections(all_detections, config.holdout_fraction)` — no seed argument passed at all.** Always silently defaults to 42; `CalibrationConfig` has no seed field, so a real calibration run (not a hand-written script) has no way to change this holdout split. |
| `split_holdout` (`validation.py:33`, used by `point_refinement.py`) | `seed` parameter exists, `point_refinement.py:420` exposes `holdout_seed: int = 42` on `refine_calibration`'s public signature — accepts a seed |

**Conclusion — the real gap is narrower than "acceptance," but not nothing:**
1. Every *library function* a WP5/WP6 sweep script would call directly (generators,
   `split_holdout`, `refine_calibration`) already accepts a seed. A sweep driving the
   library through Python (not the CLI) can already reproduce any of these individually.
2. **The one real code gap:** `run_calibration_from_config`'s internal holdout split
   (`pipeline.py:706-707`) has no config-exposed seed — `CalibrationConfig` has no seed
   field, and the call site doesn't even pass the `split_detections` function's own
   `seed` parameter through. A full pipeline run's holdout assignment is *always* seed=42
   with no way to change it, which is a real (if narrow) reproducibility gap: two sweep
   runs with different intended seeds would get identical holdout splits.
3. **Recording gap (also real):** nothing writes the seed(s) actually used into
   `calibration.json` or any output artifact today — confirmed no `"seed"` key anywhere in
   `schema.py`. "A surprising result is reproducible" (ROADMAP success criterion) requires
   not just accepting a seed but recording it in the run's output, and that plumbing does
   not exist for any entry point yet.

**Verdict:** HOOK-06 needs (a) a `seed` field added to `CalibrationConfig` threaded to the
pipeline's `split_detections` call, and (b) every seed actually used (pipeline holdout
split, and whichever seed(s) a synthetic-data sweep used to generate its scenario) recorded
in the run's output metadata — not the "confirm nothing needed" outcome CONTEXT.md
predicted as one possibility, but also not a large gap.

## Additional Research Areas

### §5 — HOOK-01: what's available to dump at each stage boundary

Traced `run_calibration_from_config` (`pipeline.py:591-1039`+):

- **Post-Stage-2 (extrinsic init):** `initial_result` (a full `CalibrationResult`) is
  already built at `pipeline.py:769-792` and saved unconditionally to
  `calibration_initial.json` at line 795. **Already done — HOOK-01 for this stage is just
  "leave as-is" or relocate under a config flag for consistency.**
- **Post-Stage-3 (interface + pose optimization):** `stage3_extrinsics, stage3_distances,
  stage3_poses, stage3_rms` are returned as a **plain tuple** from `_run_stage3(...)`
  (line 837-862, and reassigned again after the outlier-rejection re-run at line 944) —
  **no `CalibrationResult` is built for this point today.** One must be constructed via
  the same `_build_calibration_result(...)` helper used for `initial_result`, using
  `stage3_extrinsics`/`stage3_distances`/`primary_intrinsics` and whichever
  `DiagnosticsData`/`CalibrationMetadata` placeholders make sense pre-validation (the
  existing `initial_result` construction at line 769-792 is a template — it uses zeroed
  diagnostics since validation hasn't run yet; the same pattern applies here).
- **Post-intrinsic-refinement (Stage 4, only when `config.refine_intrinsics`):**
  `final_extrinsics, final_distances, final_poses, final_intrinsics, final_rms` (line
  990-996) are also a **plain tuple**, no `CalibrationResult` built until much later
  (after validation, at the very end of the function). Same fix pattern as Stage 3.

**Recommendation:** add a `save_stage_calibrations: bool = True` (default ON, per CONTEXT.md)
config key; at each of the three points, call `_build_calibration_result(...)` (reusing
the exact pattern already at line 769-792) and `save_calibration(...)` to
`internals/calibration_stage3.json` and `internals/calibration_stage4.json` (naming is
Claude's discretion per CONTEXT.md) guarded by the flag. This is additive — it does not
touch the values flowing into the existing `calibration_initial.json`/`calibration.json`
outputs, satisfying the zero-numerical-change constraint.

### §6 — HOOK-02: getting a per-iteration trace out of `least_squares`

**Overturns the research prompt's premise.** The installed scipy (1.17.0) has a
`callback` parameter on `least_squares`, added in **scipy 1.16.0**
(`least_squares.py:495-514`, `.. versionadded:: 1.16.0`), implemented for both `trf` and
`dogbox` methods (not `lm` — irrelevant here since all bundle-adjustment call sites use
`method="trf"`). Signature: `callback(intermediate_result: OptimizeResult)`, called once
per **accepted** iteration (confirmed empirically: 3 callback calls for 4 `njev` calls in
a converging example — the first `njev` is the initial Jacobian at `x0`, before any
iteration/callback fires).

**What `intermediate_result` actually contains** (from `trf.py:395-397`,
`OptimizeResult(x=x, fun=f_true, nit=iteration, nfev=nfev)`, `intermediate_result["cost"] =
cost`): **only `x`, `fun`, `nit`, `nfev`, `cost`.** It does **not** include `optimality`,
`step_norm`, or `jac` — those exist only in the *final* `result`, not per-iteration.

**Consequence for the trace's required fields** (iteration, cost, step norm, optimality,
interface parameters):
- `nit`, `cost` — directly available from callback.
- `interface parameters` — extract from `x` via the existing `unpack_params` (same
  function already used post-optimization at `refinement.py:217-226`).
- `step_norm` — **not given directly**, but trivially derivable: cache the previous
  callback's `x` and take `norm(x - x_prev)` — exact, zero extra cost.
- `optimality` — **not given at all**, and not cheaply derivable from the callback alone
  (it's a Coleman-Li-scaled, bound-aware gradient norm computed internally in `trf.py`
  from `J`, `f`, and the current active-constraint state — not something a callback can
  recompute without re-deriving scipy's exact internal scaling). **Two options:**
  1. Instrument the custom `jac` callable (already wrapped in
     `make_sparse_jacobian_func`) to also compute an approximate optimality proxy
     (e.g. `norm(J.T @ f, ord=inf)`, the *unconstrained* gradient norm) each time it's
     called, and stash it in a closure-scoped buffer keyed by call count. Since `jac(x)`
     is called exactly once per accepted iteration immediately before the callback fires
     (confirmed by the Q1 experiment), the wrapper's last-cached value lines up with the
     callback's `nit`. This is a reasonable, cheap proxy but **will not bit-match** the
     `optimality` value scipy reports in the final `result` (that one applies bound
     scaling this proxy skips).
  2. Log `verbose=2` output and parse it — `trf.py` prints `g_norm` (the real optimality
     metric) via `print_iteration_nonlinear` when `verbose=2`. This is the *exact* metric
     but requires parsing stdout text, which is fragile (format not a public API,
     verbose output already goes to the user's own progress display) and explicitly
     against the researcher-role guidance to avoid parsing internal output as a stable
     mechanism.

  **Recommendation:** option 1 (instrumented `jac` wrapper), documented explicitly as an
  approximate/unconstrained proxy for optimality, not scipy's exact bound-scaled quantity.
  This keeps the trace mechanism entirely within the public `callback` + existing custom
  `jac` machinery, adds negligible cost (one `J.T @ f` matvec per iteration, on an
  already-materialized dense `J`), and needs no stdout parsing.

**Every `least_squares` call site enumerated** (from the earlier repo-wide grep):
| File:line | Stage | method | Needs tracing per HOOK-02? |
|---|---|---|---|
| `refinement.py:201` | Stage 3 interface+pose optimization (`optimize_interface`) — called via `_run_stage3` in pipeline, both the initial run and the post-outlier-rejection re-run | `trf` | **Yes** — CONTEXT.md: "Stage 3... and the re-run after outlier rejection... each get their own trace file" |
| `point_refinement.py:674` | Stage 4/joint refinement (`joint_refinement`, "the intrinsic pass") | `trf` (verify `method=` at that line — not directly read in this pass, recommend confirming during planning) | **Yes** — CONTEXT.md: "the intrinsic pass" gets its own trace file |
| `interface_estimation.py:301`, `interface_estimation.py:631` | Per-camera interface estimation (Stage 2/auxiliary registration helpers) | not yet confirmed | Likely **no** — these are single-camera PnP-style solves, not the "bundle-adjustment stages" CONTEXT.md scopes the trace to; confirm during planning which of these two lines is `_estimate_validation_poses`/`_compute_initial_board_poses` vs. actual interface-parameter estimation |
| `pipeline.py:1445` | `method="lm"`, small per-frame residual solve (used inside `_run_stage3`'s pipeline helpers for e.g. subsampling/frame handling) | `lm` | **No** — `lm` does not support `callback` at all (confirmed: `.. versionadded`/support text says "Only implemented for the trf and dogbox methods"); also not one of the three BA stages CONTEXT.md names |
| `extrinsics.py:189` | Stage 2 per-frame pose refinement (`method="lm"`) | `lm` | **No** — same reason: `lm` unsupported, and Stage 2 is initialization, not one of the three named BA stages |

**Action for planning:** confirm the exact `method=` argument at `point_refinement.py:674`
before committing — if it's not `trf`/`dogbox`, the intrinsic pass would need switching
methods (a numerical-behavior change, out of scope) or a fallback tracing mechanism.

**Dependency consequence:** since `callback` requires scipy ≥ 1.16.0 and `pyproject.toml`
currently has an unpinned `"scipy"` dependency, HOOK-02 implementation must add a
`scipy>=1.16` (or higher, matching whatever else the milestone needs) floor. This is a
genuine new minimum-version constraint the planner should call out explicitly, not an
implementation detail to bury in a task.

### §7 — HOOK-04: held-out evaluation refactor surface

Traced the pipeline's held-out evaluation, which today lives inline in
`run_calibration_from_config` from roughly `pipeline.py:1108` (comment: "Estimate board
poses for validation frames") through `pipeline.py:1235` (`reconstruction_errors =
primary_3d`), immediately followed by diagnostics generation (out of scope for the
extraction — that's reporting, not evaluation).

**What must be extracted (the actual held-out evaluation logic, distinct from diagnostics):**
1. `_compute_initial_board_poses(val_detections, final_intrinsics, final_extrinsics,
   board, min_corners=..., n_water=...)` — PnP-style initial pose estimate per held-out
   frame (line 1111-1118).
2. `_estimate_validation_poses(val_detections, val_initial_poses, final_intrinsics,
   final_extrinsics, final_distances, board, interface_normal, n_air, n_water)` — refined
   6-DOF board pose per held-out frame with cameras fixed (line 1120-1130).
3. Build a `CalibrationResult` from the calibration being scored (already done via
   `_build_calibration_result`, line 1149-1169 in the current inline code — but note this
   is *inline* construction from raw dicts; a standalone `evaluate_calibration` would take
   an already-built `CalibrationResult` as input, not raw extrinsics/intrinsics dicts).
4. Filter to primary vs. auxiliary cameras if applicable (line 1144-1146, 1172, 1218-1222)
   — likely out of scope for a general-purpose standalone function; primary/auxiliary is
   a pipeline-specific concept, not intrinsic to "evaluate this calibration against this
   held-out set."
5. `compute_reprojection_errors(result, val_detections, board_poses_dict)` (line 1175-1177).
6. `compute_3d_distance_errors(result, val_detections, board, include_spatial=True)`
   (line 1180-1182).

**Proposed `evaluate_calibration` signature** (concrete enough to plan against, final name/
kwargs are implementation detail):
```python
def evaluate_calibration(
    calibration: CalibrationResult,
    detections: DetectionResult,
    board: BoardGeometry,
    min_corners: int = 8,
) -> ValidationReport:  # or whatever the pipeline's existing result-shape type is
    """Score a calibration against a held-out detection set.

    Estimates per-frame board poses independently (PnP + refine, cameras fixed)
    against `detections`, then computes reprojection and 3D reconstruction errors.
    Does not require `detections` to have been part of the calibration's inputs —
    this is exactly how WP4 evaluates a calibration made at one n_water against
    ground truth generated at a different one.
    """
```
Internally this wraps steps 1, 2, 5, 6 above (using `calibration`'s own
`interface_params.n_air`/`n_water`/`normal` rather than pipeline config — the calibration
object already carries everything needed). The pipeline then calls this function for its
primary-camera validation and separately for auxiliary cameras (steps 3-4 stay
pipeline-side, calling the shared function once per camera subset it needs to filter to).

**Regression test requirement (per CONTEXT.md's hard constraint):** a test that runs the
full pipeline (or a small synthetic scenario through it) both before and after the
refactor and asserts **bit-identical** `reprojection_error_rms`,
`validation_3d_error_mean/std`, and `num_frames_holdout` in the resulting
`CalibrationResult` — i.e., a snapshot/golden-value test pinned to the current pipeline's
output on a synthetic scenario (`create_scenario("ideal")` or similar, deterministic seed),
asserting the extracted function produces numerically identical results to the current
inline code path. This is the only place in the phase where a behavior-preserving refactor
needs this level of proof.

### §8 — Config plumbing for new keys

Traced `load_config` (`pipeline.py:~380-439`): new keys follow the existing pattern of
`section = data.get("section_name", {})` then `key = section.get("key", default)`, passed
into the `CalibrationConfig(...)` constructor call. The `validation:` section
(`holdout_fraction`, `save_detailed_residuals`) is the closest precedent for the new
`save_*` hook flags (likely also `validation:` or a similarly-scoped section — CONTEXT.md
leaves exact key names to discretion).

**`aquacal init` config generation** (`cli.py`, the `_generate_config_yaml`-type function
around line 590-620): confirmed this is hand-maintained text generation (f-string/list-of-
lines), not derived from the schema automatically — every new config key needs an explicit
new line added here, exactly as `reject_outlier_frames` was added in quick task 2
(`cli.py:603`).

**Test precedent exists:** `tests/unit/test_cli.py:571-579` asserts the generated
config's *parsed* content (not just substring presence) for `reject_outlier_frames`
(explicitly testing "Active (uncommented) line: parsing proves it is not just present in
text" — line 574 comment). New hook config keys should get equivalent test coverage:
parse the generated YAML and assert the new keys/defaults are present and correctly typed,
following this exact pattern.

**Public API note:** `aquacal.validation.__init__.py` does **not** currently re-export
`compute_reprojection_errors`/`compute_3d_distance_errors` in its `__all__` — CONTEXT.md's
"alongside" phrasing refers to same-package membership (they live in
`validation/reprojection.py` and `validation/reconstruction.py` respectively), not an
existing `__init__.py` export. Per the repo's `code-style.md` rule ("When adding a new
public function or class, add it to the parent package's `__init__.py` and `__all__`"),
any new conditioning function placed in `aquacal/validation/` (e.g. a new
`conditioning.py`) must be added to `validation/__init__.py`'s `__all__` — and the planner
should decide whether to also add the two existing-but-unexported functions at the same
time (likely out of scope, flag as a "don't touch unless asked" boundary).

## Open Questions

1. **Direct SVD vs. Gram-matrix eigendecomposition for HOOK-03 (see §Q2).**
   - What we know: direct SVD is numerically correct for the near-degenerate small
     singular values the WP6 argument needs, but costs ~2x the Jacobian's memory (a
     same-sized `U` matrix). Gram-matrix (`eigh(J.T@J)`) is memory-cheap (~4 MB extra)
     but roughly halves precision on small singular values.
   - What's unclear: whether the halved precision materially changes the WP6 degeneracy
     conclusion (this depends on how close to numerically-zero the smallest singular
     values actually are on the real rig — not measured in this research pass).
   - Recommendation: surface this explicitly to the user during planning rather than
     silently picking one path (matches CONTEXT.md's "do not silently degrade" instruction,
     applied to the algorithm choice, not just the config flag).

2. **Exact residual count `m` for the 13-camera/100-frame rig.**
   - What we know: back-calculated to roughly 600-700K from the reported ~3.6 GB peak
     assuming it's entirely the Jacobian (it may not be — a separate open todo already
     calls this peak figure a "suspected" driver, not confirmed).
   - What's unclear: the true `m`, and how much of the 3.6 GB is the Jacobian vs. other
     allocations (input data, detection arrays, etc.).
   - Recommendation: the implementation should compute the pre-check bound from the
     live run's actual `jac_sparsity.shape` (already available at the call site in
     `refinement.py:177-185`) rather than a hardcoded constant.

3. **`point_refinement.py:674`'s exact `method=` argument** (needed to confirm HOOK-02's
   "intrinsic pass" trace is feasible via `callback` — not directly read in this pass).
   - Recommendation: read this call site during planning before committing to the
     callback-based design for all three traced stages.

4. **Whether a memory probe (e.g. via a new `psutil` dependency) or a pure analytic
   estimate is preferred for the HOOK-03 pre-check** — left as Claude's discretion by
   CONTEXT.md. This research recommends analytic (no new dependency; the risk is
   refusing-too-late on a genuine OOM, not fine-tuning against live headroom), but flags
   it as a real choice for the planner rather than assuming resolution.

## Sources

### Primary (HIGH confidence — read directly, or executed and observed)
- `src/aquacal/calibration/_optim_common.py` (full read of `make_sparse_jacobian_func`,
  `build_structural_column_groups` region)
- `src/aquacal/calibration/refinement.py:150-234` (Stage 3 `least_squares` call site)
- `src/aquacal/calibration/pipeline.py` (multiple ranges: 380-439, 440-480, 560-1039,
  1080-1330) — full trace of `run_calibration_from_config`
- `src/aquacal/datasets/synthetic.py` (full file, 741 lines)
- `src/aquacal/core/interface_model.py:20-97` (`Interface` defaults)
- `src/aquacal/config/schema.py:280-316` (`CalibrationConfig` fields)
- `src/aquacal/__init__.py`, `src/aquacal/validation/__init__.py` (public API surfaces)
- `tests/unit/test_cli.py:571-579` (generated-config test precedent)
- Installed `scipy` 1.17.0 source: `scipy/optimize/_lsq/trf.py` (full `trf_bounds`/
  `trf_no_bounds` read), `scipy/optimize/_lsq/least_squares.py:485-545` (`callback`
  docstring, `.. versionadded:: 1.16.0`)
- Two executed Python scripts confirming (a) `result.jac` matches the last custom-`jac`
  call and is the accepted-step Jacobian, (b) `callback` fires once per accepted
  iteration with `x`/`fun`/`nit`/`nfev`/`cost` only, no `optimality`/`step_norm`/`jac`.
- `pyproject.toml` (dependency list — confirms unpinned `scipy`, no `psutil`)
- `.planning/todos/pending/2026-07-23-reduce-memory-and-cpu-load-during-calibration.md`,
  `.planning/quick/3-use-a-structural-column-grouping-for-the/3-SUMMARY.md` (peak-memory
  provenance/uncertainty)

### Secondary / Tertiary
None used — all findings verified directly against installed scipy source or repo code.

## Metadata

**Confidence breakdown:**
- HOOK-01/HOOK-04 (pipeline structure): HIGH — read every relevant line directly.
- HOOK-02 (callback mechanism): HIGH for the callback's existence/behavior (read scipy
  source + ran two confirming experiments); MEDIUM for the "instrumented jac wrapper"
  optimality-proxy recommendation (sound reasoning, not yet implemented/tested in this repo).
- HOOK-03 (memory): HIGH for `result.jac` reliability and correlation-matrix size; MEDIUM
  for the exact `m`/peak-memory breakdown (back-calculated, not measured live — a live run
  takes 48-87 minutes per project memory, out of scope for this research pass).
- HOOK-05/HOOK-06 audits: HIGH — read the full relevant source files, no gaps in coverage.

**Research date:** 2026-07-23
**Valid until:** Until scipy is upgraded again or `_optim_common.py`/`pipeline.py` are
substantially restructured — these are read-the-code findings, not fast-moving ecosystem
facts, so treat as valid for the remaining life of this milestone (through 2026-08-21).

---

## Addendum: Open Question 1 resolved empirically (orchestrator, 2026-07-23)

Open Question 1 (direct SVD vs. Gram-matrix eigh for HOOK-03) was escalated to planning as a
user-facing tradeoff. It was instead **settled by measurement** — the research's framing of it
as "memory-safe but numerically weaker" understates the Gram route's failure, and a fourth
option beats both candidates outright.

**Method:** synthetic `m x n` Jacobian with an injected near-degenerate direction
(column 1 = column 0 + 1e-9 noise), giving a known true `sigma_min`. Measured peak extra
allocation with `tracemalloc` and accuracy against `svd(J, compute_uv=False)` as reference.
Run at m=20000, n=727 (the real n).

| Route | Extra memory | `sigma_min` rel. error | Yields `V` for correlation? |
|---|---|---|---|
| `svd(J, full_matrices=False)` | ~2x J | exact | yes |
| `eigh(J.T @ J)` (Q2's recommendation) | ~0 | **1.0 — returns exactly 0.0, cond = inf** | no — `inv(J.T@J)` returns **NaN** (rcond 1.3e-16) |
| `qr(mode='economic')` + `svd(R)` | ~2x J | 5.4e-16 | yes |
| **blocked tall-skinny QR + `svd(R)`** | **O(chunk), independent of m** | 7.2e-8 | yes |

**Corrections to Q2 / Open Question 1:**

1. **The Gram route does not "roughly halve precision" — it destroys the signal entirely.**
   On the near-degenerate problem it returned `sigma_min` = exactly 0.0 (condition number
   `inf`), and the correlation matrix via `inv(J.T @ J)` came back all-NaN. This is not a
   tradeoff to surface to the user; it is a route that fails in precisely the WP6 regime
   HOOK-03 exists to measure. **Do not implement it, not even as a fallback.**

2. **`compute_uv=False` is not sufficient on its own.** It gives the singular-value spectrum
   cheaply (~1x J) but no right singular vectors, so it cannot produce the correlation matrix
   that success criterion 3 requires. Spectrum and correlation must come from the same route.

3. **`scipy.linalg.qr(J, mode='r')` returns R with shape `(m, n)`, not `(n, n)`** — only
   `mode='economic'` gives the `(n, n)` R. Feeding the `mode='r'` result into `svd(R)` with
   its default `full_matrices=True` allocates an **m x m** `U`: at m=40000 that is 12.8 GB,
   and at the real rig's m it is far worse. This is a live OOM trap on the exact code path
   this phase adds — call it out in the plan's task notes.

**Recommendation (supersedes Q2's "surface both options to the user"):** implement HOOK-03 as
a **blocked tall-skinny QR** — iterate row-chunks of the Jacobian maintaining an `(n, n)` R
via `R = qr(vstack([R, chunk]), mode='economic')[1]`, then a single `svd(R, full_matrices=False)`
for the spectrum and `V`. Correlation follows from rank-truncated `V @ diag(1/s^2) @ V.T`,
normalized to unit diagonal.

Consequences for the other open questions:

- **Open Question 4 (analytic estimate vs. `psutil` probe) largely dissolves.** Peak extra
  allocation is `O(chunk * n)` and independent of `m`, so a default chunk can be chosen to
  keep the transient in the low hundreds of MB regardless of rig size. A cheap analytic
  guard is still worth keeping for the `(n, n)` products, but no new dependency is warranted
  and there is no scenario where the metric must be silently narrowed.
- **Open Question 2 (exact `m`) drops from blocking to informational.** The algorithm no
  longer has an `m`-dependent transient, so the pre-check no longer needs a trustworthy `m`
  estimate. Still compute the reported figures from the live `result.jac.shape`.

**Confidence:** HIGH for the measured table (executed and observed directly, reference-checked
against a known injected `sigma_min`). MEDIUM for the specific default chunk size, which
should be tuned against a real `result.jac` during implementation rather than fixed from this
synthetic run.

**Provenance note:** the original planning session crashed the machine while testing exactly
the `mode='r'` trap described in correction 3 above. The measurements here were re-run at a
deliberately reduced `m` to stay in safe headroom.
