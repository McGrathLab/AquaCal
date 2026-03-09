# AquaCal

## What This Is

AquaCal is a Python library for calibrating multi-camera arrays that view underwater scenes through a flat water surface. It models Snell's law refraction at the air-water interface to jointly optimize camera extrinsics, water surface position, and calibration board poses. Includes a refinement API for downstream consumers to improve calibration using 3D-to-2D point correspondences with validation and accept/reject recommendations. Available on PyPI with Sphinx documentation, example datasets, Jupyter tutorials, and comprehensive user guides.

## Core Value

Accurate refractive camera calibration from standard ChArUco board observations — researchers can `pip install aquacal`, point it at their videos, and get a calibration result they trust.

## Requirements

### Validated

- ✓ Four-stage calibration pipeline (intrinsics, extrinsics init, joint optimization, optional refinement) — existing
- ✓ Refractive projection through flat air-water interface using Snell's law — existing
- ✓ Pinhole and fisheye (equidistant) camera model support — existing
- ✓ ChArUco board detection with filtering (min corners, collinearity) — existing
- ✓ BFS pose graph for extrinsic initialization with rotation averaging — existing
- ✓ Sparse Jacobian optimization with Newton-Raphson fast projection — existing
- ✓ Auxiliary camera registration (cameras not seeing shared frames) — existing
- ✓ Optional interface tilt estimation — existing
- ✓ Validation with held-out frames (reprojection errors, 3D distance errors) — existing
- ✓ Diagnostic report generation with visualizations — existing
- ✓ Cross-run calibration comparison (CSV + PNG) — existing
- ✓ CLI with calibrate, init, and compare commands — existing
- ✓ JSON serialization of calibration results — existing
- ✓ YAML-based configuration — existing
- ✓ Public API: run_calibration(), load/save_calibration(), core types — existing
- ✓ Clean pip-installable package on PyPI — v1.2
- ✓ Getting started tutorial (end-to-end: collect images to calibration result) — v1.2
- ✓ Theory/math background documentation (refractive geometry, coordinate conventions, optimizer) — v1.2
- ✓ Example datasets (real calibration data + synthetic) — v1.2
- ✓ Jupyter notebook examples demonstrating the pipeline — v1.2
- ✓ Cleanup of legacy development artifacts — v1.2
- ✓ CI/CD pipeline (GitHub Actions for tests, linting, publishing) — v1.2
- ✓ Infrastructure complete: Read the Docs, Zenodo DOI, RELEASE_TOKEN — v1.4
- ✓ CLI workflows user-verified with real rig data (init, calibrate, compare) — v1.4
- ✓ Documentation audit: docstrings and Sphinx docs reviewed, terminology unified (`water_z`) — v1.4
- ✓ Documentation visuals: palette system, Mermaid pipeline, BFS graph, sparsity pattern — v1.4
- ✓ Tutorials restructured (3→2) with pre-executed outputs and progressive experiments — v1.4
- ✓ User guide pages: CLI reference, camera models, troubleshooting, glossary — v1.4
- ✓ Public `refine_calibration()` API with weighted 3D-to-2D point correspondences — v1.6
- ✓ Bundle adjustment over extrinsics + water_z with optional intrinsics refinement — v1.6
- ✓ Robust loss functions (Huber/Cauchy) for outlier tolerance — v1.6
- ✓ Structured validation report: holdout reproj error, triangulation consistency, extrinsics drift — v1.6
- ✓ Accept/reject recommendation based on validation thresholds — v1.6
- ✓ Clean input contracts: PointCorrespondence, RefinementResult, ValidationReport, CameraDrift — v1.6

### Active

(No active milestone — run `/gsd:new-milestone` to plan next)

### Out of Scope

- Web interface or REST API — this is a library/CLI tool
- GPU acceleration — CPU-only NumPy/SciPy is sufficient for calibration workloads
- Real-time calibration or streaming — batch processing only
- Non-flat interface models (curved surfaces, waves) — flat plane approximation is the scope
- Support for non-ChArUco calibration targets — ChArUco only for now
- Conda-forge recipe — defer until PyPI adoption validates demand
- Docker container — defer until reproducibility requests arrive
- Multi-language bindings — Python-only for now

## Context

Shipped v1.6 with ~13,100 LOC Python.
Tech stack: NumPy, SciPy, OpenCV, Matplotlib, Pandas, PyYAML, Sphinx (Furo), GitHub Actions.
Published on PyPI as `aquacal`. Sphinx docs live on Read the Docs. Zenodo DOI active.
45+ tests for refinement API alone; full test suite spans unit + synthetic.
Two Jupyter tutorial notebooks with pre-executed outputs.

Known issues / tech debt:
- Hero image redesign deferred (user wants to rethink concept; generation script kept)
- Memory/CPU optimization for large calibrations not yet addressed
- Version field in JSON output may not read local version properly
- Phase 15 SUMMARY.md files not generated (work done, UAT/verification passed)

Primary downstream consumer: AquaPose — a 13-camera 3D fish tracking pipeline that produces
hundreds of thousands of triangulated 3D points with known camera correspondences from animal
tracking. The refinement API allows AquaPose to feed tracked keypoint observations back into
AquaCal to improve calibration accuracy over time.

## Constraints

- **Python compatibility**: 3.10, 3.11, 3.12
- **Dependencies**: Lightweight (NumPy, SciPy, OpenCV, Matplotlib, Pandas, PyYAML)
- **License**: MIT

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| PyPI + GitHub distribution | Standard for research Python libraries | ✓ Good — v1.4.1 live on PyPI |
| Real + synthetic example data | Real data builds trust, synthetic demonstrates correctness | ✓ Good — both available |
| Jupyter notebooks for examples | Interactive, visual — ideal for research audience | ✓ Good — 2 notebooks shipped |
| MIT license | Maximizes adoption in research community | ✓ Good |
| Ruff over Black/mypy | Faster, all-in-one linting and formatting | ✓ Good |
| Trusted Publishing (OIDC) | No API tokens needed for PyPI | ✓ Good |
| python-semantic-release | Automates version bumping from conventional commits | ✓ Good |
| Sphinx + Furo theme | Clean, modern docs with MyST Markdown | ✓ Good |
| FrameSet Protocol | Structural subtyping for image/video input flexibility | ✓ Good |
| Pre-execute notebooks | Reproducible docs builds without runtime dependencies | ✓ Good |
| Rename interface_distance → water_z | Clearer semantics — it's a Z-coordinate, not a distance | ✓ Good — 55 files updated |
| Centralized palette.py | Shared color palette for all diagram scripts | ✓ Good — consistent visuals |
| Mermaid for pipeline diagram | Renders in Sphinx, easier to maintain than ASCII | ✓ Good |
| Merge diagnostics into tutorial 01 | Single calibrate-then-diagnose flow is more natural | ✓ Good |
| 2-tutorial structure | Pipeline + synthetic validation covers key use cases | ✓ Good |
| Local pack/unpack for point refinement | Point correspondences have no board poses, separate from _optim_common | ✓ Good |
| Parameterized extensions over separate functions | refine_intrinsics, loss, normal_fixed as params on single function | ✓ Good |
| Validation as optional post-step | validate=True default, holdout split before optimization | ✓ Good |
| Any-fail accept/reject logic | Conservative — any threshold exceeded rejects refinement | ✓ Good |

---
*Last updated: 2026-03-09 after v1.6 milestone*
