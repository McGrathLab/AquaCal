# Milestones

## v1.2 MVP (Shipped: 2026-02-15)

**Phases completed:** 6 phases, 20 plans
**Timeline:** 2 days (2026-02-14 → 2026-02-15)
**Execution time:** 1.85 hours
**Changes:** 170 files, +21,632 / -2,180 lines
**Git range:** `feat(01-01)` → `docs(phase-06)`
**PyPI:** aquacal v1.2.0 on [pypi.org/project/aquacal](https://pypi.org/project/aquacal/)

**Delivered:** AquaCal transformed from a working calibration library into a pip-installable PyPI package with CI/CD, Sphinx documentation, example datasets, and Jupyter tutorials.

**Key accomplishments:**
1. Clean pip-installable package on PyPI with semantic versioning and automated releases
2. GitHub Actions CI/CD: matrix testing (Python 3.10-3.12, Linux/Windows), Sphinx doc builds, Trusted Publishing
3. Public release with community files: CODE_OF_CONDUCT, CITATION.cff, GitHub issue/PR templates, README with badges
4. Example datasets: synthetic data API with presets, download infrastructure with caching/checksums, real rig on Zenodo
5. Sphinx documentation site: Furo theme, theory pages (refractive geometry, coordinates, optimizer), complete API reference
6. Interactive tutorials: FrameSet protocol for image directory support, 3 Jupyter notebooks, hero visual, concise README

---

## v1.4 QA & Polish (Shipped: 2026-02-19)

**Phases completed:** 6 phases (7-12), 10 plans
**Timeline:** 5 days (2026-02-15 → 2026-02-19)
**Changes:** 74 files, +4,156 / -2,099 lines
**Git range:** `v1.3.0` → `v1.4.1`
**PyPI:** aquacal v1.4.1 on [pypi.org/project/aquacal](https://pypi.org/project/aquacal/)

**Delivered:** Documentation and QA polish — all CLI workflows user-verified with real data, codebase-wide terminology cleanup (`interface_distance` → `water_z`), new visualization system, and restructured tutorials.

**Key accomplishments:**
1. Verified all infrastructure (Read the Docs, Zenodo DOI, RELEASE_TOKEN) already complete
2. User-verified all CLI workflows (init, calibrate, compare) with real rig data — no major bugs
3. Audited 18 API modules + 11 Sphinx docs; renamed `interface_distance` → `water_z` across 55 files
4. Created centralized color palette, Mermaid pipeline flowchart, BFS graph + sparsity pattern diagrams
5. Restructured tutorials (3→2), rewrote synthetic validation with 3 progressive experiments

---

## v1.6 Refinement API (Shipped: 2026-03-09)

**Phases completed:** 3 phases (13-15), 6 plans
**Timeline:** 1 day (2026-02-28)
**Changes:** 27 files, +5,027 / -133 lines
**Git range:** `docs(13)` → `test(15)`

**Delivered:** Public refinement API enabling downstream consumers (e.g., AquaPose) to refine an existing AquaCal calibration using 3D-to-2D point correspondences, with optional intrinsics refinement, robust loss functions, and a structured validation pipeline with accept/reject recommendations.

**Key accomplishments:**
1. `PointCorrespondence` dataclass and `refine_calibration()` API — bundle adjustment over extrinsics + water_z using point correspondences
2. Optional intrinsics refinement (fx/fy/cx/cy) with configurable bounds and drift warnings
3. Robust loss functions (Huber/Cauchy) via scipy native API for outlier tolerance
4. Validation pipeline: holdout reprojection error, triangulation consistency, extrinsics drift detection with per-camera details
5. `RefinementResult` contract with `CalibrationResult`, `ValidationReport`, and accept/reject recommendation
6. 45 tests across input validation, optimization correctness, extensions, and validation

---
