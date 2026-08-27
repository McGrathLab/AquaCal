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

## Interim releases v1.7 – v1.8 (2026-07-15 → 2026-07-23)

Shipped **outside** the GSD milestone framework — no phases, no roadmap entries. Recorded
here so phase numbering and the release history stay reconcilable. The last GSD phase was 15.

| Release | Date | Delivered | Origin |
|---------|------|-----------|--------|
| v1.7.0 | 2026-07-15 | Outlier-frame rejection (`reject_outlier_frames`) scored from independent PnP poses; `detection.start_frame` / `detection.stop_frame` | Frame-contamination debug session |
| v1.7.1 | 2026-07-16 | Metadata-only patch: PEP 639 license form, McGrathLab URLs, CITATION/README resync, self-updating Sphinx `release` | Housekeeping |
| v1.8.0 | 2026-07-23 | Seeded `cv2.calibrateCamera` + `validate_view_diversity()` fronto-parallel warning; `reject_outlier_frames` emitted in generated configs | Rig-tilt debug session, quick task 2 |
| (unreleased) | 2026-07-23 | Structural FD column grouping — theoretical-minimum group count, output-neutral | Quick task 3 |

**Documentation debt this created:** every v1.7–v1.8 feature is discoverable only from
`troubleshooting.md`, and the intrinsics seeding is undocumented entirely. Addressed by
v2.0 Task Group E.

---

## v2.0 Publication Prep (Closed: 2026-08-15)

**Phases completed:** 10 of 12 (16, 17, 18, 19, 19.1, 19.2, 19.3, 19.4, 19.5, 21), 106 plans
**Deferred, carried forward:** Phase 20 (Refractive Index Helper), Phase 22 (Release Cut)
**Timeline:** 22 days (2026-07-23 → 2026-08-13)
**Changes:** 709 files, +145,357 / −3,657 lines across 673 commits
**Git range:** `cd5dd00` (feat(16-01)) → `f55dd51`
**Releases:** v2.0.0 and v2.0.1 tagged on GitHub 2026-08-11 — the first push in 674 commits.
Zenodo dataset record **21889922**, version DOI `10.5281/zenodo.21889922`, concept DOI
`10.5281/zenodo.18645384` preserved.

> **Planned as "v1.9", shipped as v2.0.** Phase 19.3 made `board` a required parameter of
> `generate_board_trajectory` and `generate_real_rig_trajectory`, both public exports, forcing
> a major bump. Archived under what shipped.

**Delivered:** All code-side tooling the SoftwareX reviewer responses depend on — observability
hooks, benchmark instrumentation, a per-camera interface ablation mode — and then, through five
inserted decimal phases, the experiment suite itself: consolidated, executed, provenance-complete,
geometrically corrected twice, and uncertainty-banded. The Zenodo archive was regenerated from
the full frameset and republished so §3 reproduces from bytes a reader can download.

**Key accomplishments:**
1. Experiment observability and benchmark instrumentation: per-stage calibration dumps,
   per-iteration optimizer traces, conditioning diagnostics via blocked tall-skinny QR, standalone
   held-out evaluation, and a machine-readable `benchmark.json` on every run
2. Per-camera interface ablation mode (`shared_interface=False`) with `True` proven bit-unchanged
3. One `experiments/` directory, one implementation per experiment, and a provenance table mapping
   every paper artifact to its script, data file, and figure generator
4. Two geometry defects found and corrected — boards protruding through the water surface (19.3),
   and ground truth giving each camera its own water surface (19.4, 1.42 px mean modelling error
   against a 0.4–0.9 px residual)
5. Uncertainty bands (19.5): E5 and E6 gained seed bands, E2 a split band, and R1.2/R1.3 got their
   first experimental answers — establishing what may be *claimed*, not just what is correct
6. Dataset refresh and first push in 674 commits: full-frameset Zenodo archive published as a new
   version with lineage preserved, `load_example("real-rig")` verified from a cold cache, and a
   pre-2.0.0 audit that caught three release-locked defects before they froze

**Known deferred items at close:** 15 (see STATE.md § Deferred Items) — 2 debug sessions,
5 quick-task records, 5 todos, 3 verification gaps. Plus 4 unsatisfied requirements
(INDEX-01..03, DOCS-07), all carried forward rather than dropped.

**No release cut at close** by user decision 2026-08-15. The next milestone cleans up the
experiments, fixes the accumulated defects, and re-runs the full suite at a single code version.

---
