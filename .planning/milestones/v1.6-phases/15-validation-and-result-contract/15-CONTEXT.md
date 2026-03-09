# Phase 15: Validation and Result Contract - Context

**Gathered:** 2026-02-28
**Status:** Ready for planning

<domain>
## Phase Boundary

`refine_calibration()` returns a `RefinementResult` with a structured `ValidationReport` and a clear accept/reject recommendation. Includes holdout reprojection error, triangulation consistency, and extrinsics drift detection. This phase wraps the existing refinement pipeline with validation — it does not change the optimization itself.

</domain>

<decisions>
## Implementation Decisions

### Holdout strategy
- Default holdout fraction: 20% of correspondences (`holdout_fraction=0.2`, configurable)
- Split applied per-camera (each camera holds out 20% of its own points), not globally
- Seeded random split with configurable seed (default 42) for reproducibility
- Same data + same seed = same split every time

### Threshold defaults
- Holdout reprojection error threshold: 1.0 px (configurable)
- Extrinsics drift thresholds: both translation and rotation checked
  - Translation: 50mm default (configurable)
  - Rotation: 2° default (configurable)
- All thresholds individually configurable by the caller with sensible defaults

### Acceptance logic
- Any-fail rejects: `accepted=False` if ANY threshold is exceeded
- No warning level — binary accept/reject only
- `ValidationReport` includes a human-readable `summary` string explaining the decision (e.g., "Rejected: camera 3 translation drift 62mm exceeds 50mm threshold")
- Callers can disable validation entirely with `validate=False` (default True) — skips holdout split and threshold checks

### Result structure
- `RefinementResult` is a dataclass (consistent with schema.py conventions)
- Always returns `RefinementResult` regardless of `validate` flag — when `validate=False`, `validation_report=None` and `accepted=None`
- Per-camera drift details nested inside `ValidationReport` as `camera_drifts` dict mapping camera_id to {translation_mm, rotation_deg, exceeded}
- `ValidationReport` stores before/after values for all metrics (holdout reproj, triangulation consistency) so callers can see improvement

### Claude's Discretion
- Triangulation consistency metric implementation details (ray intersection tightness calculation)
- How to structure the holdout split internally (indexing strategy)
- Exact dataclass field names and types beyond what's specified above
- Whether to add `__repr__` or pretty-printing to result types

</decisions>

<specifics>
## Specific Ideas

- Summary string should name the specific camera(s) and metric(s) that caused rejection
- Before/after values let callers show "reprojection error improved from 1.2px to 0.8px" style messages

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 15-validation-and-result-contract*
*Context gathered: 2026-02-28*
