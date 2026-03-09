# Project Retrospective

*A living document updated after each milestone. Lessons feed forward into future planning.*

## Milestone: v1.6 — Refinement API

**Shipped:** 2026-03-09
**Phases:** 3 | **Plans:** 6 | **Commits:** 20

### What Was Built
- `refine_calibration()` API with PointCorrespondence input — bundle adjustment over extrinsics + water_z
- Optional intrinsics refinement (fx/fy/cx/cy) and robust loss functions (Huber/Cauchy)
- Validation pipeline: holdout reprojection error, triangulation consistency, extrinsics drift
- `RefinementResult` contract with accept/reject recommendation
- 45 tests covering input validation, optimization, extensions, and validation

### What Worked
- Single-function parameterized design (refine_intrinsics, loss, validate as params) — clean API surface
- Local pack/unpack/sparsity/bounds matching _optim_common patterns but separate — no coupling to board-pose code
- Phase 15 validation wired as optional post-step inside refine_calibration() — zero API complexity for callers
- Verification + UAT caught no issues — clean implementation across all 3 phases

### What Was Inefficient
- Phase 15 SUMMARY.md files not generated despite work being complete (UAT/verification passed)
- All 3 phases executed in a single day — velocity tracking per-plan is less meaningful at this pace
- Phase numbering continued from v1.4 (13-15) which caused init tool to count all 15 phases for this milestone

### Patterns Established
- Any-fail accept/reject logic for validation — conservative by default, callers can override
- Holdout split before optimization for unbiased validation metrics
- Per-camera CameraDrift dataclass for structured drift reporting
- f_scale parameter for controlling robust loss inlier threshold

### Key Lessons
1. Parameterized extensions on a single function scale well — 3 phases of features added without API surface explosion
2. Validation as an integrated step (not a separate API call) ensures callers get quality metrics by default
3. scipy's native loss parameter (Huber/Cauchy) is cleaner than custom loss wrappers

### Cost Observations
- Model mix: Primarily sonnet for execution, opus for orchestration
- Sessions: Multiple within a single day
- Notable: Entire milestone completed in ~1 day — well-scoped phases with clear requirements

---

## Cross-Milestone Trends

### Process Evolution

| Milestone | Phases | Plans | Key Change |
|-----------|--------|-------|------------|
| v1.2 MVP | 6 | 20 | Initial project setup, packaging, docs |
| v1.4 QA & Polish | 6 | 10 | QA verification, terminology cleanup, visuals |
| v1.6 Refinement API | 3 | 6 | Feature development — new API surface |

### Cumulative Quality

| Milestone | New Tests | Key Additions |
|-----------|-----------|---------------|
| v1.2 | Existing suite | CI/CD, packaging, tutorials |
| v1.4 | User verification | CLI QA, doc audit, visual diagrams |
| v1.6 | 45 refinement tests | refine_calibration API, validation pipeline |

### Top Lessons (Verified Across Milestones)

1. Well-scoped milestones (3-6 phases) execute faster and cleaner than large ones
2. Verification and UAT at phase level catches issues before milestone completion
3. Keeping planning artifacts (REQUIREMENTS, ROADMAP) milestone-scoped prevents unbounded growth
