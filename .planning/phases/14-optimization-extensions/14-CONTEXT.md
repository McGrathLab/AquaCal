# Phase 14: Optimization Extensions - Context

**Gathered:** 2026-02-28
**Status:** Ready for planning

<domain>
## Phase Boundary

Extend `refine_calibration()` with two optional capabilities: (1) intrinsics refinement that adds fx, fy, cx, cy per camera to the optimization, and (2) robust loss functions (Huber/Cauchy) for outlier tolerance. The existing extrinsics + water_z refinement behavior remains the default.

</domain>

<decisions>
## Implementation Decisions

### Intrinsics refinement API
- Single bool flag: `refine_intrinsics=True` refines fx, fy, cx, cy for ALL cameras (including reference camera)
- Only fx, fy, cx, cy — distortion coefficients stay fixed from in-air calibration
- Bounded drift: constrain each intrinsic param within a configurable percentage of its initial value
- Configurable bound with sensible default: add `intrinsics_bound_pct` parameter (default ~10%)
- Default is `refine_intrinsics=False` — intrinsics stay fixed unless explicitly enabled

### Reference camera tilt
- Include 2-DOF reference camera tilt (rx, ry) in point refinement, matching the main pipeline's `normal_fixed=False` convention from `_optim_common.py`
- Add `normal_fixed` parameter to `refine_calibration()` (default True for backward compatibility)

### Robust loss configuration
- String parameter: `loss='huber'` or `loss='cauchy'`, matching scipy.optimize.least_squares API
- Default: `loss='linear'` (squared loss) — preserves current behavior
- Only Huber and Cauchy supported (validate input, reject others)
- Configurable scale: `f_scale` parameter with sensible default (e.g., 1.0 pixel)

### Parameter interaction
- Intrinsics refinement and robust loss are fully independent — any combination works
- Active extensions recorded in output CalibrationResult metadata (refine_intrinsics, loss type, f_scale)
- When intrinsics are refined, initial intrinsics stored in metadata for before/after comparison

### Convergence guardrails
- Log warning when any intrinsic param shifts more than ~5% from initial value
- Auto-scale max_nfev when intrinsics are enabled (more params → more iterations needed), unless caller explicitly set it
- Reported RMS uses raw (unweighted) residuals so it's comparable across loss settings
- Sparse Jacobian pattern extends automatically to include intrinsic columns when enabled

### Code reuse strategy
- Refactor point_refinement.py to reuse shared machinery from `_optim_common.py` (pack_params, unpack_params, build_jac_sparsity, compute_bounds)
- `_optim_common.py` already has full intrinsics refinement support (pack/unpack, sparsity, bounds with ±10% drift) from the Stage 4 joint refinement
- Point refinement needs adaptation for point-based (vs board-based) residual structure, but parameter layout and sparsity machinery can be shared

### Claude's Discretion
- Exact default value for `intrinsics_bound_pct` (around 10%)
- Exact default value for `f_scale` (around 1.0 pixel)
- How to adapt _optim_common pack/unpack for point-based residuals (may need to pass empty frame_order or refactor to separate extrinsic/intrinsic packing)
- Warning threshold for intrinsic drift logging
- max_nfev auto-scaling factor

</decisions>

<specifics>
## Specific Ideas

- Reuse the proven `_optim_common.py` machinery rather than duplicating intrinsics handling in point_refinement.py — the Stage 4 code already handles fx/fy/cx/cy packing, sparsity patterns, and bounds
- The `normal_fixed=False` 2-DOF reference tilt is already implemented in `_optim_common.py` — carry it over to point refinement
- scipy's `least_squares` already accepts `loss` and `f_scale` parameters natively — implementation is largely pass-through

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 14-optimization-extensions*
*Context gathered: 2026-02-28*
