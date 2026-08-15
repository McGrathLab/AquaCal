# Roadmap: AquaCal

## Milestones

- ✅ **v1.2 MVP** — Phases 1-6 (shipped 2026-02-15)
- ✅ **v1.4 QA & Polish** — Phases 7-12 (shipped 2026-02-19)
- ✅ **v1.6 Refinement API** — Phases 13-15 (shipped 2026-03-09)
- ✅ **v2.0 Publication Prep** — Phases 16-22 (closed 2026-08-15)
- 🚧 **v2.1 Clean Experimental Suite** — Phases 23-30 (started 2026-08-15)

**Interim releases v1.7–v1.8** shipped outside the GSD framework (debug sessions,
quick tasks) — no phases. See `.planning/MILESTONES.md`.

**Note on labels:** the v2.0 milestone was planned as "v1.9" and shipped as **v2.0.0 /
v2.0.1** — Phase 19.3 made `board` a required parameter of two public exports, forcing a major
bump. It is archived under what shipped. Older documents saying "v1.9" mean that milestone.

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

### 🚧 v2.1 Clean Experimental Suite (Phases 23-30) — started 2026-08-15

**Goal:** Land every experiment-suite fix that changes what the suite measures, records, or can
claim; freeze one sha; hand a complete full-suite driver to a larger Linux machine for the run;
reconcile the returned single-version results into the manuscript's evidence base.

**Scope boundary:** targeted experimental-suite fixes only. Performance work on the solver
(`_optim_common.py`'s dense `.toarray()`, LSMR preconditioning, an analytic Jacobian) is **out** —
every experiment routes through that file, so touching it makes the fresh suite unattributable.
The test: *does it change what the suite measures, records, or can claim?* If yes, in scope, and
it lands before the run. If it only changes how fast the library gets there, it waits.

**Deadline split:** Phases 23-29 (FIX / DEGEN / DRIVER / BAND / RUN) land before the
**2026-08-21** SoftwareX submission. Phase 30 (POST) follows it.

The Zenodo split (originally POST-02) was pulled forward into Phase 29 as **RUN-05** on
2026-08-15: Phase 29 commits new §3 numbers pre-submission, so leaving the archive until after
the deadline would ship a paper citing a record whose bundled `reference_outputs/` contradict
its own §3. What stays in Phase 30 is the reconciliation *around* that archive, not the archive.

- [ ] **Phase 23: Experiment Correctness Fixes** - Six independent single-file fixes that change what E1, E6, E7, E4, E2, and the synthetic generator measure or are licensed to claim
- [ ] **Phase 24: Degeneracy Instrumentation** - The degeneracy counter reaches the benchmark record, is persisted by E5 and the band runs, split by kind and stage, and its warning is narrowed
- [ ] **Phase 25: Degeneracy Classification & Claim Licensing** - The 198 unprojectable production-rig observations are classified, and E1's seed band gains the noise_std axis it needs to license an accuracy claim
- [ ] **Phase 26: Full-Suite Driver & Handoff Readiness** - One driver covers every invocation including the band runs and E2, emits one run manifest, has a decided `--check` contract, and stale outputs are moved aside
- [ ] **Phase 27: Frozen Single-Sha Handoff Package** - The library, driver, gates, and environment requirements are frozen at one sha and packaged for the Linux machine
- [ ] **Phase 28: Suite Execution on Linux Machine** - The full experiment suite — E1 through E7, the band runs, and E2 — executes once end to end at the frozen sha
- [ ] **Phase 29: Gate Verification & Results Commit** - The returned run passes `check_rerun_gates.py`, clears the E2 sanity control and the E7 before/after comparison, its results are committed with provenance intact, and the Zenodo results package is published before submission
- [ ] **Phase 30: Post-Submission Reconciliation** - After the 2026-08-21 submission: §3/tutorial re-cut as a matched set with the archive, stale outputs purged, MF-19 closed

## Phase Details

### Phase 23: Experiment Correctness Fixes
**Goal**: The suite's E1, E6, E7, E4, E2, and synthetic-generator outputs are numerically and
textually correct, so downstream phases build the driver and run against a fixed, trustworthy
suite rather than a moving target.
**Depends on**: Nothing (first phase of the milestone)
**Requirements**: FIX-01, FIX-02, FIX-03, FIX-04, FIX-05, FIX-06
**Success Criteria** (what must be TRUE):
  1. E1's non-refractive arm pins `water_z` and its degenerate-observation guard count drops
     to 0 (from 14,949), while the refractive arm is left unpinned.
  2. E1 and E7 solve with the interface normal free, matching the production pipeline's DOF
     count instead of the library's `normal_fixed` signature default.
  3. E6's report shows signed, gauge-corrected Z error together with the per-camera
     decomposition, both behind the existing collinear caveat.
  4. E7's `fixed` rows are labelled vacuous-by-construction rather than presented as a measured
     `no_signature` verdict.
  5. E4's aggregator resolves E2's benchmark row correctly under a custom `--out` directory, and
     the three stale provenance strings in `e2_real_rig.py`/`synthetic.py` describe what is
     actually true.
**Plans**: TBD

### Phase 24: Degeneracy Instrumentation
**Goal**: The degeneracy counter is observable end to end — it reaches the artifacts a reader
would actually check, split finely enough to answer the degeneracy question without re-running
anything, and its warning stops over-firing.
**Depends on**: Nothing (independent of Phase 23's fixes; touches different files)
**Requirements**: DEGEN-01, DEGEN-02, DEGEN-03
**Success Criteria** (what must be TRUE):
  1. `degenerate_observations_at_solution` appears in the production `benchmark.json` record
     instead of being dropped before it is written.
  2. E5 and the band runs persist the counter in their own output artifacts.
  3. The persisted counter is split by failure kind and by stage.
  4. The degenerate-observation warning fires only for the cases it actually applies to, with a
     corrected cause list.
**Plans**: TBD

### Phase 25: Degeneracy Classification & Claim Licensing
**Goal**: Two open questions blocking manuscript language — what the 198 unprojectable
production-rig observations are, and what domain E1's accuracy claim may state — are answered
and recorded before the frozen run, so neither becomes a mid-run discovery.
**Depends on**: Nothing (investigation/decision work, not code shared with Phases 23-24)
**Requirements**: DEGEN-04, BAND-01
**Success Criteria** (what must be TRUE):
  1. The production rig's 198 unprojectable observations are classified into named categories,
     with the finding recorded so the manuscript can disclose the count and say what it is.
  2. The finding also unblocks (or explicitly leaves blocked) the deferred degeneracy-gate
     scope decision for real-rig runs.
  3. E1's seed band gains a `noise_std` axis, with the `n_cameras` geometry axis explicitly
     marked skipped, so promoted absolute-accuracy numbers carry a stated domain.
**Plans**: TBD

### Phase 26: Full-Suite Driver & Handoff Readiness
**Goal**: A single driver invocation covers the entire suite — nothing left for the Linux machine
to discover is missing — with one truthful run manifest, a decided `--check` contract, and a
clean output tree to run into.
**Depends on**: Phase 23, Phase 24, Phase 25 (the driver must invoke the corrected experiments and
capture the corrected degeneracy artifacts, not the pre-fix behavior — and Phase 25 is a real
dependency, not an optional one: DEGEN-04's classification emits a per-observation table and needs
a driver-passed flag for E2's full-population `h_q` logging, kept off by default so ordinary users
do not get a multi-megabyte sidecar per calibration. Build the driver against 23 and 24 alone and
it gets built, then amended at the freeze.)
**Requirements**: DRIVER-01, DRIVER-02, DRIVER-03, DRIVER-04
**Success Criteria** (what must be TRUE):
  1. `rerun_19_3.sh` invokes every experiment in the suite, including the band runs and E2 — the
     exact invocations where the six-sha provenance spine previously fractured.
  2. A single suite run emits one run manifest recording `aquacal_version` and the OpenCV build
     truthfully, alongside the rest of the execution environment.
  3. `--check`'s meaning across a deliberate baseline re-base is documented, with written
     expectations replacing bit-identity reproduction wherever schemas changed.
  4. Every pre-existing output tree is moved aside (not deleted) before a driver invocation, so a
     fresh run cannot be confused with a stale one.
**Plans**: TBD

### Phase 27: Frozen Single-Sha Handoff Package
**Goal**: Everything the Linux machine needs — code, driver, gates, and environment
requirements — is frozen at one sha and verified runnable before it leaves this machine.
**Depends on**: Phase 23, Phase 24, Phase 25, Phase 26 (every fix, instrumentation change,
classification finding, and driver capability must be in before the freeze)
**Requirements**: RUN-01
**Success Criteria** (what must be TRUE):
  1. One git sha is designated and recorded as the frozen version for the re-run.
  2. The driver and `check_rerun_gates.py` run successfully against a clean checkout of that sha.
  3. Environment requirements (Python version, OpenCV build, dependencies) are written down for
     the receiving machine.
  4. The handoff package requires no further code edits once transferred — anything discovered
     missing sends the freeze back to this phase, not forward into the run.
  5. Every §3-facing number has a generating emitter in the frozen code. A number that is
     hand-asserted with no artifact behind it cannot be made traceable after the freeze — the fix
     is an emitter, and Phase 29 is too late to add one. (The ledger classification that
     identifies which rows those are is manuscript-side and the author's; it must land before
     this freeze. Named here as a dependency, not imported as a task.)
  6. Phase 25's outputs are registered with the driver — the per-observation classification table
     and the E2 `h_q` logging flag — since Phase 26 built the driver before that work was
     necessarily complete.
**Plans**: TBD

### Phase 28: Suite Execution on Linux Machine
**Goal**: The full experiment suite runs once, end to end, at the frozen sha, on hardware sized
for the 13-camera rig's 48-87 minute / 10.26 GiB calibrations.
**Depends on**: Phase 27
**Requirements**: RUN-02
**Success Criteria** (what must be TRUE, verifiable from the returned artifacts — this phase
executes off-repo):
  1. Returned artifacts include a result file (e.g. `benchmark.json`) for every experiment —
     E1 through E7, the band runs, and E2 — with none missing.
  2. The returned run manifest records exactly one `aquacal_version`/git sha across all
     artifacts.
  3. The set of returned invocations matches the driver's coverage from Phase 26 one for one.
**Plans**: TBD

### Phase 29: Gate Verification & Results Commit
**Goal**: The returned run is graded and becomes the repo's committed evidence base, with every
manuscript-facing number traceable to it.
**Depends on**: Phase 28
**Requirements**: RUN-03, RUN-04, RUN-05
**Success Criteria** (what must be TRUE):
  1. `check_rerun_gates.py` passes over the complete returned run, including Gate 3's
     single-sha assertion, now that the band runs and E2 are inside its coverage.
  2. **E2 reproduces its pre-run numbers to ~1e-8.** E2 and E3 are the only experiments whose
     schemas do not change, and nothing in Phases 23-26 touches E2's solve inputs (FIX-06 is
     strings; E2 already runs `normal_fixed=False` via the config layer). F-001 measured the
     entire Windows→Linux, `6c7f930`→v2.0.1 span reproducing to 1.5e-8 with OpenCV held at
     4.13. So E2 is the run's sanity control, and because DEGEN-02 does touch
     `_optim_common.py`, this check is also what proves the degeneracy instrumentation did not
     perturb the solve. A drift to ~1e-2 means the run is broken in a way no completeness gate
     detects — check it explicitly, do not leave it to whoever reads the results.
  3. **E7's ablation conclusion is compared before and after, explicitly.** FIX-02 gives E7 two
     extra free parameters per interface, which is exactly the kind of change that could soften
     the fixed-intrinsics arm's published 10-of-10 sign test (p = 0.00098, supplement §14). If
     it moved, the new number is the honest one — but it is reported here, not discovered during
     manuscript re-verification.
  4. The returned results are committed to the repository with provenance (sha, manifest)
     intact.
  5. Every §3-facing number in the manuscript can be traced to a specific committed artifact
     from this run.
  6. **The Zenodo results package is published before the 2026-08-21 submission** (RUN-05), so
     the archive the paper cites agrees with the §3 it supports. The 4.35 GB input-package
     re-upload that makes this possible is staged during Phase 28's run window, from the Windows
     box, while the Linux run is going.
**Plans**: TBD

### Phase 30: Post-Submission Reconciliation
**Goal**: After the 2026-08-21 SoftwareX submission, the manuscript's evidence base and the
public data artifacts are brought into agreement with the single-version run, and the finding
that motivated this milestone is closed out.
**Depends on**: Phase 29, and the 2026-08-21 SoftwareX submission (calendar dependency — this
phase does not start before the submission ships)
**Requirements**: POST-01, POST-03, POST-04
  *(POST-02, the Zenodo split, was re-timed to **RUN-05** in Phase 29 on 2026-08-15 — it has to
  land before submission, not after it.)*
**Success Criteria** (what must be TRUE):
  1. §3, the Zenodo archive's `reference_outputs/`, and the tutorial's expected-value table are
     re-cut as a matched set against the new E2 numbers.
  2. Stale output trees are purged from the library, so the shipped package carries only the
     data the paper cites.
  3. MF-19 is marked closed in `MANUSCRIPT-FINDINGS.md`, with any finding the re-run
     contradicts or newly raises appended alongside it.
**Plans**: TBD

## Carried Forward

Open at the close of v2.0 and inputs to the v2.1 milestone (beyond the 19 discharging todos
already mapped above). Full detail in STATE.md § Deferred Items and in the archived requirements.

| Item | Origin | Note |
|------|--------|------|
| INDEX-01, INDEX-02, INDEX-03 | Phase 20 | Refractive index helper. Deferred 2026-08-07 on MF-13 — the effect is ~5× below seed noise. Deferred, not dropped. Not part of v2.1 |
| DOCS-07 | Phase 22 | Manuscript C1 metadata cell + which DOI the paper cites. Recommendation on file: the **version** DOI. Manuscript-side, not part of v2.1's phases |
| CLEAN-01 | v2.0 backlog | Retire the `initial_distances` compat shim — unblocked, still a breaking change. Not part of v2.1 |
| Source-level `normal_fixed` reconciliation | v2.1 scoping | Config layer defaults `False`, 18 library signatures default `True`. FIX-02 fixes this at the experiment level; source-level fix deferred to POST-SUBMISSION |
| Degeneracy-gate scope for real-rig runs | v2.1 scoping | Blocked until DEGEN-04 (Phase 25) reports what the 198 are |
| `download_with_progress` HTTP Range/resume | Phase 21 | User called it "a convenience". Non-breaking to add. Not part of v2.1 |
| Reduce memory and CPU load during calibration | todo 2026-07-23 | Peak measured at 10.26 GiB. Explicitly out of scope for v2.1 (see Scope boundary above) |
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
| 23. Experiment Correctness Fixes | v2.1 | 0/TBD | Not started | - |
| 24. Degeneracy Instrumentation | v2.1 | 0/TBD | Not started | - |
| 25. Degeneracy Classification & Claim Licensing | v2.1 | 0/TBD | Not started | - |
| 26. Full-Suite Driver & Handoff Readiness | v2.1 | 0/TBD | Not started | - |
| 27. Frozen Single-Sha Handoff Package | v2.1 | 0/TBD | Not started | - |
| 28. Suite Execution on Linux Machine | v2.1 | 0/TBD | Not started | - |
| 29. Gate Verification & Results Commit | v2.1 | 0/TBD | Not started | - |
| 30. Post-Submission Reconciliation | v2.1 | 0/TBD | Not started | - |
