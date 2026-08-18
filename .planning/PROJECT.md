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
- ✓ Outlier-frame rejection scored from independent PnP poses — v1.7
- ✓ `detection.start_frame` / `detection.stop_frame` to trim contaminated frame ranges — v1.7
- ✓ `reject_outlier_frames` emitted as an active key in generated configs — v1.8
- ✓ Seeded `cv2.calibrateCamera` with fronto-parallel board view warning — v1.8
- ✓ Structural FD column grouping (theoretical-minimum group count) — quick task 3
- ✓ Benchmark instrumentation and machine-readable `benchmark.json` run records — v2.0
- ✓ Experiment observability hooks (stage dumps, traces, conditioning, held-out evaluation, seeding) — v2.0
- ✓ Per-camera interface ablation mode (`shared_interface=False`) — v2.0
- ✓ Documentation reconciliation with the paper, including the three-stage model in code and docs — v2.0
- ✓ Consolidated, provenance-complete experiment suite with uncertainty bands — v2.0
- ✓ Dataset refresh: full-frameset Zenodo archive republished, tutorials re-executed — v2.0

## Current State

**Shipped:** v2.0.1 (2026-08-11). Milestone **v2.0 Publication Prep** closed 2026-08-15 with
10 of 12 phases executed and 106/106 plans complete. No release was cut at close.

The Zenodo dataset archive is live at record **21889922** (version DOI
`10.5281/zenodo.21889922`), regenerated from the full frameset so §3 reproduces from the
published bytes. CI is green on all six jobs. The library is tagged v2.0.0/v2.0.1 on GitHub.

**Hard deadline still live:** revised SoftwareX manuscript due **2026-08-21**.

**Phase 24 complete (2026-08-18)** — degeneracy instrumentation. The counter is now observable
end to end: it reaches `benchmark.json`, is split on independent cause and fate axes (14 -> 32
`DISCARD_KEYS`), carries a per-stage `e{N}_degeneracy_breakdown.json` sidecar, and its warning
is narrowed by cause and fraction instead of over-firing. Optimality is decomposed per parameter
block, and a bound-hit detector separates pinned-by-request from ran-into-a-limit. Verified 5/5;
full suite 1932 passed, 0 failed.

## Current Milestone: v2.1 Clean Experimental Suite

**Goal:** Land every experiment-suite fix that changes what the suite measures, records, or can
claim; freeze one sha; hand a complete full-suite driver to a larger Linux machine for the run;
reconcile the returned single-version results into the manuscript's evidence base.

**Target features:**

- Experiment correctness fixes that move or license a published number — E1's `water_z` pin in
  the non-refractive arm, `normal_fixed` unification for E1/E7, E6's signed and gauge-corrected
  Z error with per-camera decomposition, E7's vacuous `fixed` rows, E4's hardcoded E2 path
- Degeneracy made observable — the counter split by stage *and* kind, persisted by E5 and the
  band runs, reaching the production benchmark record; the over-broad warning narrowed and its
  cause list corrected; the production rig's 198 unprojectable observations classified
- A full-suite driver that covers **every** invocation — `rerun_19_3.sh` extended over the band
  runs and E2, which is exactly where the six-sha provenance spine fractured
- A run manifest capturing the environment, with `aquacal_version` and the OpenCV build recorded
  truthfully
- A decided meaning for `--check` across a deliberate baseline re-base, and stale output trees
  moved aside before the run
- E1's seed band gains a `noise_std` axis, so its promoted absolute-accuracy numbers carry a
  stated domain
- The full suite executed once at one frozen sha — **E2 included** — on the Linux machine, gates
  green
- Post-submission: the Zenodo record split into immutable inputs and a versioned results
  package, stale outputs purged from the library

**Agreed 2026-08-15.** The three motivating problems: the suite's defects accumulated faster than
they were fixed once the deadline started dominating; the carried-forward defect list needs
closing; and MF-19 (§3's numbers predate the current library) needs one run at one code version,
which no single run has yet delivered.

**Execution split (author, 2026-08-15).** Code edits land on this machine. The full re-run is
handed off to a larger Linux machine — so the driver, the manifest, and the gates must be
complete and portable *before* handoff, not discovered during the run.

**E2 is in the re-run.** Section 3, the Zenodo archive's `reference_outputs/`, and the tutorial's
expected-value table are a matched set of three; re-running E2 moves all of them together and
makes the archive repackage load-bearing rather than optional.

**Deadline split.** Fixes → frozen handoff → run → manuscript-facing numbers land before the
**2026-08-21** SoftwareX submission. The Zenodo repackage and re-upload, the stale-output purge,
and the follow-ups gated on the 198-classification come after.

**Explicitly deferred, not dropped:** the source-level `normal_fixed` reconciliation
(POST-SUBMISSION), the degeneracy-gate scope decision for real-rig runs (blocked until the 198
are classified), and all solver memory/CPU work.

**Scope boundary (author, 2026-08-15):** targeted fixes that improve the experimental suite —
nothing else. Specifically **out**: the solver's memory/CPU trade-off (`_optim_common.py`'s dense
`.toarray()`, LSMR preconditioning, an analytic Jacobian). Every experiment routes through that
file, so touching it makes the fresh suite unattributable, which is the one thing the re-run
exists to prevent. Genuinely deferred, not forgotten — revisit after submission, against a suite
that is no longer the paper's evidence.

The test for whether something belongs: *does it change what the suite measures, records, or can
claim?* If yes, it is in scope and should land before the run. If it only changes how fast or how
cheaply the library gets there, it waits.

### Active

- [ ] Experiment correctness fixes that change what the suite measures or can claim
- [ ] Degeneracy observability: split counter, persistence, narrowed warning, the 198 classified
- [ ] Full-suite driver covering every invocation, with an environment-capturing run manifest
- [ ] E1 noise-axis band licensing its absolute-accuracy claim
- [ ] Frozen single-sha handoff package for the Linux machine
- [ ] Full single-version experiment-suite re-run, E2 included
- [ ] Post-run reconciliation: manuscript findings, Zenodo repackage, stale-output purge
- [ ] Carried forward, unscheduled: INDEX-01..03 (Phase 20, deferred on MF-13), DOCS-07
      (manuscript-side), CLEAN-01

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

Shipped v1.8.0 (2026-07-23). v1.7/v1.7.1/v1.8 landed outside the GSD milestone
framework, via debug sessions and quick tasks; the last GSD phase was 15.
Tech stack: NumPy, SciPy, OpenCV, Matplotlib, Pandas, PyYAML, Sphinx (Furo), GitHub Actions.
Published on PyPI as `aquacal`. Sphinx docs live on Read the Docs. Zenodo DOI active.
45+ tests for refinement API alone; full test suite spans unit + synthetic.
Two Jupyter tutorial notebooks with pre-executed outputs.

Known issues / tech debt:
- Hero image redesign deferred (user wants to rethink concept; generation script kept)
- Peak memory measured at **10.26 GiB** on the 13-camera rig (not the long-quoted ~3.6 GB,
  which was never measured) from the dense `.toarray()` Jacobian — v2.0 measured and reported
  it; reducing it stays deferred (the dense return exists because sparse `jac_sparsity`
  forces LSMR, observed to diverge on this problem)
- ~~Version field in JSON output~~ — fixed
- Phase 15 SUMMARY.md files not generated (work done, UAT/verification passed)
- `initial_distances` compat shim in `pipeline.py` — now unblocked by the v2.0 dataset
  re-upload, but retiring it is still a breaking change for pre-v1.4 configs (CLEAN-01)
- Paper metadata cell C1 and the cited DOI are still outstanding manuscript work (DOCS-07)
- **The experiment suite's numbers do not all come from one library version** (MF-19) — the
  driver for the next milestone
- v2.0.0's CHANGELOG lists 1 of 7 breaking changes; GitHub release notes were corrected by
  hand. Prevention: one commit per breaking change

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
| AquaKit as shared geometry layer | Cross-library code reuse (AquaCal, AquaMVS, future) | — Pending |
| NumPy internals + torch at edges | Clean boundary for incremental PyTorch migration | — Pending |
| Centralized palette.py | Shared color palette for all diagram scripts | ✓ Good — consistent visuals |
| Mermaid for pipeline diagram | Renders in Sphinx, easier to maintain than ASCII | ✓ Good |
| Merge diagnostics into tutorial 01 | Single calibrate-then-diagnose flow is more natural | ✓ Good |
| 2-tutorial structure | Pipeline + synthetic validation covers key use cases | ✓ Good |
| Local pack/unpack for point refinement | Point correspondences have no board poses, separate from _optim_common | ✓ Good |
| Parameterized extensions over separate functions | refine_intrinsics, loss, normal_fixed as params on single function | ✓ Good |
| Validation as optional post-step | validate=True default, holdout split before optimization | ✓ Good |
| Any-fail accept/reject logic | Conservative — any threshold exceeded rejects refinement | ✓ Good |
| Reconcile stage model to three stages in code, not just docs | Paper, docs, console output, and benchmark.json must agree; A4 would otherwise bake `stage4_*` into the artifact the results table is generated from | — Pending |
| Measure peak memory, do not reduce it in v1.9 | The dense `.toarray()` trades memory for solver stability; changing it before the 2026-08-21 deadline risks destabilizing every experiment | — Pending |
| Per-camera interface as ablation only, default `shared_interface=True` | The paper's central claim is that the shared parameter is the correct model; docs must not present per-camera as co-equal | — Pending |
| Generate the results table from `benchmark.json`, not by hand | The paper has already been bitten by stale hand-copied numbers across a 9-run grid | ✓ Good — provenance table now maps every artifact to its script |
| Reconcile stage model to three stages in code, not just docs | (see above) | ✓ Good — shipped in Phase 18, no artifact baked `stage4_*` |
| Measure peak memory, do not reduce it in v2.0 | (see above) | ✓ Good — measured 10.26 GiB; the ~3.6 GB figure it replaced was never measured |
| Per-camera interface as ablation only, default `shared_interface=True` | (see above) | ✓ Good — default proven bit-unchanged by exact-equality test |
| An experiment may claim accuracy only where a measured seed band supports it (D-19.3-17) | A single-seed number is not an accuracy claim; applying this strictly demoted several published numbers | ✓ Good — the single most consequential decision of v2.0 |
| Production runs go out as one risk-first detached queue under one frozen git sha | A per-cell `git rev-parse` splits an artifact's recorded SHA; a mid-run commit destroys provenance | ✓ Good — held across 19.3, 19.4 and 19.5 |
| Zenodo is published by the user by hand, values pre-computed for transcription | Publishing is irreversible and assigns a permanent DOI | ✓ Good — record 21889922, lineage preserved |
| Defer Phase 20 (refractive index helper) on measured evidence | MF-13: across the full ±0.010 assumed-index sweep, reconstruction MAE moves ~5× below seed noise | ✓ Good — deferred, not dropped |
| E2 is inside the v2.1 single-version re-run | MF-19 is only discharged if §3's real-rig numbers come from the same build as everything else; a partial re-run leaves the paper mixing two library versions | — Pending — forces §3, the Zenodo `reference_outputs/`, and the tutorial table to be re-cut as a matched set |
| Edit here, run on the Linux machine | The 13-camera rig costs 48–87 min at 10.26 GiB peak per calibration; the full suite is not a workstation job | — Pending — makes driver coverage, the run manifest, and the gates portable-before-handoff requirements rather than run-time discoveries |

## Evolution

This document evolves at phase transitions and milestone boundaries.

**After each phase transition** (via `/gsd-transition`):
1. Requirements invalidated? → Move to Out of Scope with reason
2. Requirements validated? → Move to Validated with phase reference
3. New requirements emerged? → Add to Active
4. Decisions to log? → Add to Key Decisions
5. "What This Is" still accurate? → Update if drifted

**After each milestone** (via `/gsd:complete-milestone`):
1. Full review of all sections
2. Core Value check — still the right priority?
3. Audit Out of Scope — reasons still valid?
4. Update Context with current state

---
*Last updated: 2026-08-18 — Phase 24 Degeneracy Instrumentation complete*
