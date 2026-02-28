# Roadmap: AquaCal

## Milestones

- ✅ **v1.2 MVP** — Phases 1-6 (shipped 2026-02-15)
- ✅ **v1.4 QA & Polish** — Phases 7-12 (shipped 2026-02-19)
- 🚧 **v1.6 Refinement API** — Phases 13-15 (in progress)

## Phases

<details>
<summary>✅ v1.2 MVP (Phases 1-6) — SHIPPED 2026-02-15</summary>

- [x] Phase 1: Foundation and Cleanup (3/3 plans) — completed 2026-02-14
- [x] Phase 2: CI/CD Automation (3/3 plans) — completed 2026-02-14
- [x] Phase 3: Public Release (3/3 plans) — completed 2026-02-14
- [x] Phase 4: Example Data (3/3 plans) — completed 2026-02-14
- [x] Phase 5: Documentation Site (4/4 plans) — completed 2026-02-14
- [x] Phase 6: Interactive Tutorials (4/4 plans) — completed 2026-02-15

See `.planning/milestones/v1.2-ROADMAP.md` for full details.

</details>

<details>
<summary>✅ v1.4 QA & Polish (Phases 7-12) — SHIPPED 2026-02-19</summary>

- [x] Phase 7: Infrastructure Check (1/1 plans) — completed 2026-02-15
- [x] Phase 8: CLI QA Execution (1/1 plans) — completed 2026-02-15
- [x] Phase 9: Bug Triage (0/0 plans — no bugs found) — completed 2026-02-17
- [x] Phase 10: Documentation Audit (3/3 plans) — completed 2026-02-16
- [x] Phase 11: Documentation Visuals (2/2 plans) — completed 2026-02-17
- [x] Phase 12: Tutorial Verification (3/3 plans) — completed 2026-02-19

See `.planning/milestones/v1.4-ROADMAP.md` for full details.

</details>

### 🚧 v1.6 Refinement API (In Progress)

**Milestone Goal:** Enable downstream consumers (e.g., AquaPose) to refine an existing AquaCal calibration using 3D-to-2D point correspondences from their own analysis.

- [x] **Phase 13: Core Refinement** - Foundational input contract and bundle adjustment over point correspondences (completed 2026-02-28)
- [ ] **Phase 14: Optimization Extensions** - Optional intrinsics refinement and robust loss functions
- [ ] **Phase 15: Validation and Result Contract** - Full validation layer with structured accept/reject output

## Phase Details

### Phase 13: Core Refinement
**Goal**: Callers can invoke `refine_calibration()` with weighted 3D-to-2D point correspondences and receive an optimized calibration
**Depends on**: Phase 12 (existing calibration pipeline)
**Requirements**: API-01, API-03, OPT-01
**Success Criteria** (what must be TRUE):
  1. `from aquacal import refine_calibration, PointCorrespondence` works without error
  2. Caller can construct a `PointCorrespondence` with a 3D point, per-camera pixel observations, and an optional weight
  3. `refine_calibration()` accepts a `CalibrationResult` and a list of `PointCorrespondence` objects and returns without error
  4. After refinement, extrinsic parameters and water_z have changed to better fit the input correspondences (reprojection error decreases on training data)
  5. Intrinsics remain unchanged by default (fixed during optimization)
**Plans:** 2/2 plans complete
Plans:
- [ ] 13-01-PLAN.md — PointCorrespondence dataclass + refine_calibration() implementation + public API wiring
- [ ] 13-02-PLAN.md — Comprehensive tests for input validation and optimization correctness

### Phase 14: Optimization Extensions
**Goal**: Callers can enable optional intrinsics refinement and apply robust loss functions to tolerate outlier observations
**Depends on**: Phase 13
**Requirements**: OPT-02, OPT-03
**Success Criteria** (what must be TRUE):
  1. Passing `refine_intrinsics=True` causes fx, fy, cx, cy to be included in the optimization parameters for each camera
  2. Intrinsics remain fixed (unchanged from input) when `refine_intrinsics=False` (the default)
  3. Caller can select a Huber or Cauchy loss function via a parameter; the optimization uses it
  4. Robust loss visibly reduces the influence of high-residual correspondences compared to squared loss on the same data
**Plans**: TBD

### Phase 15: Validation and Result Contract
**Goal**: Callers receive a `RefinementResult` with a structured validation report and a clear accept/reject recommendation they can act on
**Depends on**: Phase 13
**Requirements**: VAL-01, VAL-02, VAL-03, VAL-04, API-02
**Success Criteria** (what must be TRUE):
  1. `refine_calibration()` returns a `RefinementResult` containing the refined `CalibrationResult`, a `ValidationReport`, and an `accepted` boolean
  2. `ValidationReport` contains holdout reprojection error computed on a configurable held-out fraction of the input correspondences
  3. `ValidationReport` contains a triangulation consistency metric comparing ray intersection tightness before and after refinement
  4. `ValidationReport` flags refinements where any camera's extrinsics shift beyond configurable thresholds, with per-camera details
  5. The `accepted` recommendation is `False` when any configured threshold is exceeded, allowing callers to reject poor refinements automatically
**Plans**: TBD

## Progress

| Phase | Milestone | Plans Complete | Status | Completed |
|-------|-----------|----------------|--------|-----------|
| 1. Foundation and Cleanup | v1.2 | 3/3 | Complete | 2026-02-14 |
| 2. CI/CD Automation | v1.2 | 3/3 | Complete | 2026-02-14 |
| 3. Public Release | v1.2 | 3/3 | Complete | 2026-02-14 |
| 4. Example Data | v1.2 | 3/3 | Complete | 2026-02-14 |
| 5. Documentation Site | v1.2 | 4/4 | Complete | 2026-02-14 |
| 6. Interactive Tutorials | v1.2 | 4/4 | Complete | 2026-02-15 |
| 7. Infrastructure Check | v1.4 | 1/1 | Complete | 2026-02-15 |
| 8. CLI QA Execution | v1.4 | 1/1 | Complete | 2026-02-15 |
| 9. Bug Triage | v1.4 | 0/0 | Complete | 2026-02-17 |
| 10. Documentation Audit | v1.4 | 3/3 | Complete | 2026-02-16 |
| 11. Documentation Visuals | v1.4 | 2/2 | Complete | 2026-02-17 |
| 12. Tutorial Verification | v1.4 | 3/3 | Complete | 2026-02-19 |
| 13. Core Refinement | 2/2 | Complete    | 2026-02-28 | - |
| 14. Optimization Extensions | v1.6 | 0/TBD | Not started | - |
| 15. Validation and Result Contract | v1.6 | 0/TBD | Not started | - |
