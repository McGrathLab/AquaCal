# Phase 13: Core Refinement - Context

**Gathered:** 2026-02-28
**Status:** Ready for planning

<domain>
## Phase Boundary

Foundational input contract (`PointCorrespondence`) and bundle adjustment (`refine_calibration()`) over 3D-to-2D point correspondences. Callers provide an existing `CalibrationResult` and weighted point correspondences; they receive an optimized `CalibrationResult` with refined extrinsics and water_z. Intrinsics remain fixed. Robust loss and intrinsic refinement are Phase 14. Validation/result wrapper is Phase 15.

</domain>

<decisions>
## Implementation Decisions

### Input contract shape
- Multi-camera bundle: one `PointCorrespondence` = one 3D point (`np.ndarray` shape (3,)) + dict of `{camera_name: pixel}` observations
- Minimum 2 camera observations per correspondence (reject at validation time)
- Per-point weight: single optional float per correspondence (not per-observation)
- 3D points as numpy arrays, consistent with existing codebase conventions

### Function signature
- `refine_calibration(result, correspondences, **kwargs)` with keyword args and sensible defaults for convergence tolerance, max iterations, etc.
- Always refines all cameras in the CalibrationResult (no subset selection)
- Silent by default; `verbose=True` enables optimizer progress output
- Returns `CalibrationResult` directly in Phase 13 (Phase 15 wraps in `RefinementResult`)

### Optimization behavior
- Reuse existing `_optim_common.py` infrastructure (param packing, cost function patterns, sparse Jacobian machinery), adapted for point correspondences
- Single shared `water_z` parameter (one water surface for the whole rig)
- Custom Jacobian callable approach (dense QR solver + sparse FD efficiency via `group_columns`) — same battle-tested pattern from the calibration pipeline
- On non-convergence: return best result found + log warning + provide programmatic way for caller to detect non-convergence (e.g., a status flag or convergence info on the result)

### Error & edge cases
- Validate all input upfront before starting optimization (well-formed correspondences, camera names exist, weights non-negative)
- Raise `ValueError` immediately for unknown camera names (fail fast — likely caller bug)
- Require minimum correspondence threshold (exact number Claude's discretion, e.g., ~10) — reject too-sparse input
- Silently drop zero-weight correspondences before optimization (allows soft-disable pattern)

### Claude's Discretion
- Exact minimum correspondence threshold
- Default convergence tolerance and max iteration values
- How to expose non-convergence status to callers (flag, enum, info object)
- Internal param packing order and sparsity pattern details
- Test data generation strategy

</decisions>

<specifics>
## Specific Ideas

- Non-convergence must be detectable programmatically by the caller, not just via logged warnings — they need to decide how to proceed
- Should feel like a natural extension of the existing calibration pipeline, not a bolted-on separate system
- Reuse `_optim_common.py` patterns so maintenance burden stays low

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 13-core-refinement*
*Context gathered: 2026-02-28*
