# Roadmap: AquaCal

## Milestones

- ✅ **v1.2 MVP** — Phases 1-6 (shipped 2026-02-15)
- ✅ **v1.4 QA & Polish** — Phases 7-12 (shipped 2026-02-19)
- ✅ **v1.6 Refinement API** — Phases 13-15 (shipped 2026-03-09)
- ✅ **v2.0 Publication Prep** — Phases 16-22 (closed 2026-08-15)
- 📋 **Next milestone** — experiment cleanup, defect fixes, single-version suite re-run (not yet defined)

**Interim releases v1.7–v1.8** shipped outside the GSD framework (debug sessions,
quick tasks) — no phases. See `.planning/MILESTONES.md`.

**Note on labels:** the milestone below was planned as "v1.9" and shipped as **v2.0.0 /
v2.0.1** — Phase 19.3 made `board` a required parameter of two public exports, forcing a major
bump. It is archived under what shipped. Older documents saying "v1.9" mean this milestone.
Phase numbering continues from **23** in the next milestone.

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

<details>
<summary>✅ v1.6 Refinement API (Phases 13-15) — SHIPPED 2026-03-09</summary>

- [x] Phase 13: Core Refinement (2/2 plans) — completed 2026-02-28
- [x] Phase 14: Optimization Extensions (2/2 plans) — completed 2026-02-28
- [x] Phase 15: Validation and Result Contract (2/2 plans) — completed 2026-02-28

See `.planning/milestones/v1.6-ROADMAP.md` for full details.

</details>

<details>
<summary>✅ v2.0 Publication Prep (Phases 16-22) — CLOSED 2026-08-15, 106/106 plans</summary>

- [x] Phase 16: Experiment Observability Hooks (7/7 plans) — completed 2026-07-23
- [x] Phase 17: Per-Camera Interface Ablation Mode (5/5 plans) — completed 2026-07-23
- [x] Phase 18: Documentation Corrections & Stage-Model Reconciliation (8/8 plans) — completed 2026-07-24
- [x] Phase 19: Benchmark Instrumentation (6/6 plans) — completed 2026-07-24
- [x] Phase 19.1: Experiment Suite Consolidation (INSERTED) (8/8 plans) — completed 2026-07-27
- [x] Phase 19.2: Experiment Execution and Provenance (INSERTED) (29/29 plans) — completed 2026-08-01
- [x] Phase 19.3: Scenario Geometry and Convergence (INSERTED) (10/10 plans) — completed 2026-08-04
- [x] Phase 19.4: Single Flat Interface (INSERTED) (10/10 plans) — completed 2026-08-05
- [x] Phase 19.5: Experiment Coverage and Uncertainty Bands (INSERTED) (11/11 plans) — completed 2026-08-07
- [ ] Phase 20: Refractive Index Helper — **DEFERRED** on measured evidence (MF-13); carried forward
- [x] Phase 21: New-Feature Documentation & Dataset Refresh (12/12 plans) — completed 2026-08-11
- [ ] Phase 22: Release Cut — **DEFERRED**, pre-empted by v2.0.0/v2.0.1; carried forward

Releases cut during the milestone: **v2.0.0** and **v2.0.1** (GitHub, 2026-08-11). Zenodo
dataset record **21889922**, version DOI `10.5281/zenodo.21889922`.

See `.planning/milestones/v2.0-ROADMAP.md` for full details and
`.planning/milestones/v2.0-REQUIREMENTS.md` for the requirement outcomes.

</details>

### 📋 Next Milestone — Experiment Cleanup and Final Suite Re-run (not yet defined)

No release is cut off v2.0. The next milestone's shape, agreed 2026-08-15:

1. Clean up the experiment suite.
2. Fix the defects accumulated along the way (see `Carried Forward` below and
   `.planning/todos/pending/`).
3. Run the **full experiment suite once, end to end, at a single code version**, so every
   number in the paper comes from one library build.

Run `/gsd:new-milestone` to define it. Phase numbering continues from **23**.

## Carried Forward

Open at the close of v2.0 and inputs to the next milestone. Full detail in STATE.md
§ Deferred Items and in the archived requirements.

| Item | Origin | Note |
|------|--------|------|
| INDEX-01, INDEX-02, INDEX-03 | Phase 20 | Refractive index helper. Deferred 2026-08-07 on MF-13 — the effect is ~5× below seed noise. Deferred, not dropped |
| DOCS-07 | Phase 22 | Manuscript C1 metadata cell + which DOI the paper cites. Recommendation on file: the **version** DOI |
| Post-Zenodo re-run batch | Phase 21 close | Small experiment/provenance repairs; one deliberately shifts a published number in its 4th significant figure |
| MF-19 | Manuscript findings | §3's numbers predate the current library — the manuscript-level blocker, and the reason the suite needs one single-version re-run |
| **14 pending todos** | `.planning/todos/pending/` | The experiment-cleanup backlog, after three were verified complete and closed 2026-08-15. Live ones include: E6 z-error metrics destroy sign and skip gauge correction; per-camera gauge decomposition for the layout axis; whether E1 may carry absolute-accuracy claims; E4 aggregator hardcodes the E2 benchmark path; E7 vacuous `fixed` rows ship as measured nulls; stale provenance strings in E2 metrics |
| Reduce memory and CPU load during calibration | todo 2026-07-23 | Peak measured at 10.26 GiB. Measured in v2.0, never reduced |
| CLEAN-01 | v2.0 backlog | Retire the `initial_distances` compat shim — unblocked by DATA-02, still a breaking change |
| `download_with_progress` has no HTTP Range/resume | Phase 21 | User called it "a convenience". Non-breaking to add |
| Two open debug sessions | `.planning/debug/` | `e6-seed-locked-clearance-floor` (diagnosed), `stage3-diverges-new-geometry` (awaiting human verify) |

## Progress

| Phase | Milestone | Plans Complete | Status | Completed |
|-------|-----------|----------------|--------|-----------|
| 1-6 | v1.2 | 20/20 | Complete | 2026-02-15 |
| 7-12 | v1.4 | 10/10 | Complete | 2026-02-19 |
| 13-15 | v1.6 | 6/6 | Complete | 2026-02-28 |
| 16. Experiment Observability Hooks | v2.0 | 7/7 | Complete | 2026-07-23 |
| 17. Per-Camera Interface Ablation Mode | v2.0 | 5/5 | Complete | 2026-07-23 |
| 18. Documentation Corrections & Stage-Model Reconciliation | v2.0 | 8/8 | Complete | 2026-07-24 |
| 19. Benchmark Instrumentation | v2.0 | 6/6 | Complete | 2026-07-24 |
| 19.1 Experiment Suite Consolidation | v2.0 | 8/8 | Complete | 2026-07-27 |
| 19.2 Experiment Execution and Provenance | v2.0 | 29/29 | Complete | 2026-08-01 |
| 19.3 Scenario Geometry and Convergence | v2.0 | 10/10 | Complete | 2026-08-04 |
| 19.4 Single Flat Interface | v2.0 | 10/10 | Complete | 2026-08-05 |
| 19.5 Experiment Coverage and Uncertainty Bands | v2.0 | 11/11 | Complete | 2026-08-07 |
| 20. Refractive Index Helper | v2.0 | 0/0 | Deferred → carried forward | - |
| 21. New-Feature Documentation & Dataset Refresh | v2.0 | 12/12 | Complete | 2026-08-11 |
| 22. Release Cut | v2.0 | 0/0 | Deferred → carried forward | - |
