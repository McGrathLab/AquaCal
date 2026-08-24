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

- [x] **Phase 23: Experiment Correctness Fixes** - Six independent single-file fixes that change what E1, E6, E7, E4, E2, and the synthetic generator measure or are licensed to claim (completed 2026-08-17)
- [x] **Phase 24: Degeneracy Instrumentation** - The degeneracy counter reaches the benchmark record, is persisted by E5 and the band runs, split by kind and stage, and its warning is narrowed
 (completed 2026-08-17)

- [x] **Phase 25: Degeneracy Classification & Claim Licensing** - The 198 unprojectable production-rig observations are classified, and E1's seed band gains the noise_std axis it needs to license an accuracy claim (completed 2026-08-18)
- [x] **Phase 26: Full-Suite Driver & Handoff Readiness** - One driver covers every invocation including the band runs and E2, emits one run manifest, has a decided `--check` contract, and stale outputs are moved aside
- [ ] **Phase 27: Frozen Single-Sha Handoff Package** - The library, driver, gates, and environment requirements are frozen at one sha and packaged for the Linux machine
- [ ] **Phase 28: Suite Execution on Linux Machine** - The full experiment suite — E1 through E7, the band runs, and E2 — executes once end to end at the frozen sha
- [ ] **Phase 29: Gate Verification & Results Commit** - The returned run passes `check_rerun_gates.py`, clears the E2 sanity control and the E7 before/after comparison, its results are committed with provenance intact, and the Zenodo results package is published before submission
- [ ] **Phase 29.1: Post-Run Fixes & Re-Freeze** (INSERTED) - The four defects the 2026-08-20 production run surfaced are fixed, the frozen package's install command gains the `dev` and `bench` extras the suite actually needs, and a new frozen sha is cut so the suite can be re-run cleanly before the Zenodo upload
- [ ] **Phase 30: Post-Submission Reconciliation** - After the 2026-08-21 submission: §3/tutorial re-cut as a matched set with the archive, stale outputs purged, MF-19 closed

## Phase Details

### Phase 23: Experiment Correctness Fixes

**Goal**: The suite's E1, E6, E7, E4, E2, and synthetic-generator outputs are numerically and
textually correct, so downstream phases build the driver and run against a fixed, trustworthy
suite rather than a moving target.
**Depends on**: Nothing (first phase of the milestone)
**Requirements**: FIX-01, FIX-02, FIX-03, FIX-04, FIX-05, FIX-06
**Success Criteria** (what must be TRUE):

  1. E1's non-refractive arm pins `water_z` — verified by the arm's **recovered `water_z` reading
     ground truth 1.031 m**, with the guard count's drop to 0 (from 14,949) reported as
     corroboration — while the refractive arm is left unpinned. The guard count alone is not the
     test: FIX-02 alone zeroes it at a `water_z` of 0.0120 m (measured 2026-08-17), so a
     criterion phrased on the count passes whether or not the pin exists.

  2. E1 and E7 solve with the interface normal free, matching the production pipeline's DOF
     count instead of the library's `normal_fixed` signature default. **FIX-01 lands before
     FIX-02 in the non-refractive arm**, and the combined pinned-`water_z`/free-normal
     configuration — which is what the re-run executes, and which no probe could reach before the
     pin existed — has its `water_z` and guard count emitted and checked here.

  3. E6's report shows signed, gauge-corrected Z error together with the per-camera
     decomposition, both behind the existing collinear caveat.

  4. E7's `fixed` rows are labelled vacuous-by-construction rather than presented as a measured
     `no_signature` verdict.

  5. E4's aggregator resolves E2's benchmark row correctly under a custom `--out` directory —
     at **both** call sites, including `_run_check` (`e4_benchmark_grid.py:1876`) — and the
     **four** stale provenance sites in `e2_real_rig.py`/`synthetic.py` describe what is actually
     true, with `19.1-E2-FRAMESET-PROVENANCE.md` carrying a supersession header rather than an
     edit.

  6. FIX-05 is verified by something other than `--check`, or by a `--check` whose contract
     excludes `exit_code` and `status_reason`. Today those two columns can never match (33 of 35
     already reproduce to 1e-6), so `--check` reads red before and after the fix and would hide a
     regression instead of catching one. This is DRIVER-03's decision to make; Phase 23 consumes
     it rather than answering it locally, which means the two phases must agree before either
     ships.

**Note on independence**: the phase brief calls these "six independent single-file fixes." Recon on
2026-08-17 found three of them are not: FIX-01 and FIX-02 interact and must be sequenced, FIX-05 is
two call sites plus a `--check` contract shared with Phase 26, and FIX-06 is four sites across two
trees. The phase boundary is unchanged — the plan decomposition inside it is not six-way parallel.

**Plans** (4, grouped by coupling per D-13; all wave 1 — `files_modified` verified pairwise disjoint):

**Wave 1** *(no inter-plan dependencies)*

- `23-01` — FIX-01 + FIX-02: pin `water_z` in E1's non-refractive arm via a bounds freeze threaded to
  **both** `build_bounds` sites, then free the interface normal in E1 and E7. Two commits, FIX-01
  first. `autonomous: false` (the E1 verification run is the user's).

- `23-02` — FIX-05: resolve E2's real-rig row relative to `--out` at both call sites (`_run_check`
  `:1876`, `_run_full` `:1954`), plus the named `--check` exclusion contract (`exit_code`,
  `status_reason`) shared with Phase 26's DRIVER-03.

- `23-03` — FIX-03 + FIX-04: E6 signed/gauge-corrected Z error plus the per-camera decomposition;
  E7's `fixed` rows labelled vacuous-by-construction in the existing `scope` column. Two commits.

- `23-04` — FIX-06: four stale provenance strings in `e2_real_rig.py`/`synthetic.py` plus a
  supersession header on `19.1-E2-FRAMESET-PROVENANCE.md`. Touches no logic, isolated so it can never
  be blamed for a number moving.

Cross-cutting constraints (appear in 2+ plans):

- D-11: cheap-tier verification only — no E4 nine-cell grid, no E1 10-seed band, no full suite. Those
  are Phase 28 at the frozen sha.

- D-12 (as amended 2026-08-17): in-phase runs write to git-ignored `experiments/verify_23/`; evidence
  is transcribed as values into each plan's own `SUMMARY.md`. **No plan writes
  `.planning/MANUSCRIPT-FINDINGS.md`** — see `23-CONTEXT.md` § Amendment 2026-08-17.

- D-14: one commit per requirement (a floor, not a ceiling).
- Scope fence: `Spinoffs/papers/aquacal/` is read-only from this repo; `docs/guide/troubleshooting.md`
  is not edited (it describes a live limitation, D-05).

### Phase 24: Degeneracy Instrumentation

**Goal**: The degeneracy counter is observable end to end — it reaches the artifacts a reader
would actually check, split finely enough to answer the degeneracy question without re-running
anything, and its warning stops over-firing.
**Depends on**: Nothing (independent of Phase 23's fixes; touches different files)
**Requirements**: DEGEN-01, DEGEN-02, DEGEN-03, DEGEN-05
**Success Criteria** (what must be TRUE):

  1. `degenerate_observations_at_solution` appears in the production `benchmark.json` record
     instead of being dropped before it is written.

  2. E5 and the band runs persist the counter in their own output artifacts. (Narrowed
     2026-08-17: **E6's band already does** — the column is present on all 102 rows. The real gap
     is E5, E1 and E7; E1's 14,949 lives only in `e1_benchmark_nonrefractive.json →
     problem_shape` and reaches no CSV.)

  3. The persisted counter is split by failure kind and by stage.
  4. The degenerate-observation warning fires only for the cases it actually applies to, with a
     corrected cause list.

  5. (Added 2026-08-17, DEGEN-05) Each stage's reported `optimality` is accompanied by a
     per-parameter-block decomposition, computed in `_optim_common.py` from the layout
     `build_structural_column_groups` already owns and recorded beside `stages.*.optimality` in
     E1's benchmark records. A reader can then tell a KKT residual concentrated in a pinned or
     bounded slot from one spread across extrinsics and board poses, without re-running. This
     exists because Phase 23's verification left E1's non-refractive arm at `optimality_intrinsic`
     92.78 against the refractive arm's 0.0247, with the ~2000x gap unexplained — see
     `23-01-SUMMARY.md § Evidence`. Interpretation and any claim consequence belong to Phase 25
     (BAND-01), not here.
**Plans** (2, serial per D-19 — `files_modified` overlap on the calibration modules makes them
spatially non-disjoint, so 24-02 waits on 24-01's key names):

**Wave 1**

- `24-01` — Library core: the NaN-reason array plumbed out of `refractive_project_batch`, the
  cause/fate counter split with its per-stage denominator and zero-init, the `discard_stage`
  kwarg, the narrowed warning, and the `SolverDiagnostics` per-block optimality decomposition plus
  bound-hit detector. DEGEN-02, DEGEN-03, DEGEN-05. Six commits, none mixing two requirements
  (D-20).

**Wave 2** *(depends on 24-01)*

- `24-02` — Artifacts: `pipeline.py`'s `problem_shape` mirror and the whole `discard_stats` block
  into `benchmark.json`, E1/E5/E7 columns plus the `e{N}_degeneracy_breakdown.json` sidecar,
  `check_rerun_gates.py`, and the Phase 26 (DRIVER-01) hand-off note. DEGEN-01, DEGEN-05.

### Phase 25: Degeneracy Classification & Claim Licensing

**Goal**: Two open questions blocking manuscript language — what the 198 unprojectable
production-rig observations are, and what domain E1's accuracy claim may state — are answered
and recorded before the frozen run, so neither becomes a mid-run discovery.
**Depends on**: Phase 24, for success criterion 4 only (added 2026-08-17). DEGEN-04 and BAND-01
remain investigation/decision work sharing no code with Phases 23-24 and can proceed in parallel;
only the DEGEN-05 verdict needs Phase 24's decomposition to exist first. If Phase 24 slips, run
criteria 1-3 and carry criterion 4 rather than blocking the phase.
**Requirements**: DEGEN-04, BAND-01, DEGEN-05 (verdict only — instrumentation is Phase 24's)
**Success Criteria** (what must be TRUE):

  1. The production rig's 198 unprojectable observations are classified into named categories,
     with the finding recorded so the manuscript can disclose the count and say what it is.

  2. The finding also unblocks (or explicitly leaves blocked) the deferred degeneracy-gate
     scope decision for real-rig runs.

  3. E1's seed band gains a `noise_std` axis, with the `n_cameras` geometry axis explicitly
     marked skipped, so promoted absolute-accuracy numbers carry a stated domain.
     **Rescoped 2026-08-18 (D-21):** what lands here is the *axis* — the code, both corrected key
     lists, the smoke collapse, the stated-domain sentence — plus a **two-seed probe** (≈1.5 h,
     four levels, written to `.planning/probes/2026-08-18-e1-noise-axis/`) confirming it runs end
     to end. The **band of record** — four levels × ten seeds, 640/960 rows, ≈7 h — is executed by
     **Phase 28** at the frozen sha and verified in **Phase 29**; running it here would measure at
     7 h something measured again properly two phases later. `experiments/results/` therefore
     stays at 160/240 rows through Phase 27, and no Phase 26 gate may assert 640.

  4. (Added 2026-08-17, rewritten same day once the probes reported) The convergence question
     behind E1's ratio is **already answered** and must not be re-derived here — see
     `.planning/probes/2026-08-17-optimality-decomposition/FINDINGS.md`. Measured: restarting each
     solve from its own solution recovers no cost (largest relative drop 1.8e-9), so E1's
     non-refractive baseline is converged, the comparison is fair, and the 97–178x band is
     **strengthened rather than caveated**. This phase's job is only to carry that forward: BAND-01's
     stated domain cites the warm-restart evidence as support, and the one caveat that does travel
     with the band is that the baseline arm is severely ill-conditioned (directional curvature
     ~3e8) — which is a property of fitting a pinhole model to refracted data, not a defect, and
     not a reason to qualify the accuracy claim.
**Plans**: 8 plans in 5 waves

Plans:
**Wave 1**

- [x] 25-01-PLAN.md — per-observation degeneracy detail sinks in compute_residuals and both post-solve call sites (DEGEN-04)
- [x] 25-04-PLAN.md — E1's noise_std band axis, both key-column lists, and the stated claim domain (BAND-01)
- [x] 25-05-PLAN.md — the optimality caveat where the number ships, MF-21, and the carried-forward DEGEN-05 verdict (DEGEN-05)

**Wave 2** *(blocked on Wave 1 completion)*

- [x] 25-02-PLAN.md — the log_all_observation_depths config flag and the degenerate_observations.csv user sidecar (DEGEN-04)
- [x] 25-03-PLAN.md — the offline bucket classifier and its provisional-stamped table writer in experiments/_degeneracy.py (DEGEN-04)

**Wave 3** *(blocked on Wave 2 completion)*

- [x] 25-06-PLAN.md — ORCHESTRATOR: the provisional instrumented E2 run and the classification finding (DEGEN-04)

**Wave 4** *(blocked on Wave 3 completion)*

- [x] 25-07-PLAN.md — the degeneracy-gate scope decision, its rationale at three code sites, and its tripwire (DEGEN-04)

**Wave 5** *(blocked on Wave 4 completion)*

- [x] 25-08-PLAN.md — ORCHESTRATOR: the two-seed E1 noise-axis probe, driver registration, and MF-22 (BAND-01; rescoped by D-21 — the ~7 h ten-seed band of record is Phase 28's)

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
**Plans**: 10 plans

Plans:
**Wave 1**

- [x] 26-01-PLAN.md — Archive-aside (DRIVER-04) and the four unit-test repairs it forces
- [x] 26-02-PLAN.md — Run-manifest emitter and the hard-FAIL Gate 3 extension (DRIVER-02)
- [x] 26-05-PLAN.md — E6 `--axes` selector, so D-40's `scale`-axis cut is implementable

**Wave 2** *(blocked on Wave 1 completion)*

- [x] 26-03-PLAN.md — Expectation manifest and the completeness gate with a stage/profile selector
- [x] 26-04-PLAN.md — `_io.py` baseline-dir helpers, the missing-baseline N/A guard, and E3

**Wave 3** *(blocked on Wave 2 completion)*

- [x] 26-06-PLAN.md — E2's four invocations (config variants) plus `--baseline-dir` and the N/A guard

**Wave 4** *(blocked on Wave 3 completion)*

- [x] 26-07-PLAN.md — `run_experiment_suite.sh`: rename, union-and-lift from 19.5, full stage list

**Wave 5** *(blocked on Wave 4 completion)*

- [x] 26-08-PLAN.md — Pre-flight, sticky exit, end-of-run roll-up, concurrency pool, dry-run tests

**Wave 6** *(blocked on Wave 5 completion)*

- [x] 26-09-PLAN.md — README §2/§7 rewrite, expectation sheet, MF-23, archive the two old drivers

**Wave 7** *(blocked on Wave 6 completion)*

- [ ] 26-10-PLAN.md — Orchestrator's full `--smoke` acceptance pass (checkpoint)

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
**Plans**: 13 plans in 6 waves

Plans:
**Wave 1** *(no inter-plan dependencies; `files_modified` pairwise disjoint)*

- [x] 27-01-PLAN.md — ORCHESTRATOR/author: target reconnaissance over SSH; the measured facts D-10's byte floor, D-11's paths, D-12's interpreter chain and D-15 all read (RUN-01)
- [x] 27-02-PLAN.md — driver: path-kind-agnostic `_preflight_frameset` (D-09/D-10) and exit-code-aware resume (D-22)
- [x] 27-03-PLAN.md — a truthful smoke profile: manifest retags + profile-aware E4/E5/E6 gates (D-20), and the Phase 25 registration finding (D-24, criterion 6)
- [x] 27-04-PLAN.md — `reconstruction_bootstrap.py` honours `--out` (D-23); the exit-1 stage that also blocks a green smoke
- [x] 27-05-PLAN.md — the environment lockfile emitter (D-13) and the two-regime thread record in the run manifest (D-14)
- [x] 27-06-PLAN.md — emitter-coverage report over the ledger's 27 artifacts, and the three genuine candidates (D-16/D-17/D-18, criterion 5)
- [x] 27-07-PLAN.md — the frozen-row classification note: every row this run will not regenerate, with sha and machine (D-19)

**Wave 2** *(blocked on Wave 1)*

- [x] 27-08-PLAN.md — the committed Linux E2 release config (D-11), both Windows literals detect-then-fallback (D-12), the concurrent-stages-only thread pin and the lockfile call site (D-14/D-13)
- [x] 27-09-PLAN.md — `experiments/HANDOFF.md`: environment requirements (criterion 3), the run procedure, and the two never-rehearsed invocation lines (D-21)

**Wave 3** *(blocked on Wave 2)*

- [x] 27-10-PLAN.md — ORCHESTRATOR: the local `--smoke` acceptance pass (roll-up `0 FAIL`; the driver's own exit code is non-zero on a healthy run — see 27-PREPUSH-AUDIT.md) and the pre-push public-exposure audit

**Wave 4** *(blocked on Wave 3)*

- [x] 27-11-PLAN.md — push the branch and cut the annotated non-`v*` tag `rerun-freeze-01`; record the frozen sha (D-01/D-02/D-03, criterion 1)

**Wave 5** *(blocked on Wave 4 — the tag must exist)*

- [x] 27-12-PLAN.md — ORCHESTRATOR: clean clone of the tag on the Linux target, environment build, OpenBLAS + lockfile capture, dry run and the pre-flight frameset verdict (D-05/D-06/D-07)

**Wave 6** *(blocked on Wave 5)*

- [x] 27-13-PLAN.md — ORCHESTRATOR: `fd_jacobian` at full scale on target, the gate roll-up, `--smoke` roll-up `0 FAIL` (NOT exit 0 — see HANDOFF.md §2.8), and the close-or-refreeze loop (D-03/D-04, criteria 2 and 4)

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

     **The control is same-seed only.** Verified 2026-08-17: a §3 quantity reproduces across the
     Windows→Linux span to **3.07e-09**, better than the 1.5e-8 quoted above — but E2's *seed*
     band on the same quantity spans 0.761→0.910 px. So compare seed 42 against seed 42 and
     nothing else; run the control across seeds and a healthy run looks catastrophically broken.
     State the seed in the gate's own output so the comparison cannot be misread later.

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

     **Label `optimality` in the upload** (added 2026-08-17, author's call: label at upload time,
     do not act earlier). `optimality_stage3_interface_optimization` ships in
     `benchmark_grid.csv` / `.tex`. Measured that day: the value is a **real** gradient — a
     central-difference Jacobian agrees to five significant figures, so it is not Jacobian noise —
     but it is *volatile* (43x range at a fixed solution, because the problem is severely
     ill-conditioned), *not comparable across parameter blocks* (it mixes Coleman-Li scalings of
     1, ~700 and ~2e-12), and *magnitude-dependent in reliability* (large values trustworthy,
     small ones not — a 44% disagreement at 0.001). One sentence in the package README covers it.
     This is the same shape as MF-17, where E7's vacuous `no_signature` nulls reached the archive
     unaccompanied; FIX-04 fixed that by labelling, and the same remedy applies here. Evidence:
     `.planning/probes/2026-08-17-optimality-decomposition/FINDINGS.md`.
**Plans**: TBD

### Phase 29.1: Post-Run Fixes & Re-Freeze (INSERTED)

**Goal**: The defects the 2026-08-20 production run surfaced are fixed, the frozen package's
install instructions match what the suite actually needs, and a new frozen sha is cut and tagged
so the suite can be re-run cleanly before the Zenodo results package is built.
**Depends on**: Phase 29
**Requirements**: Discharges the five todos listed under Success Criteria; no new REQUIREMENTS.md
IDs (this phase closes defects rather than adding scope).
**Why inserted**: The run at `rerun-freeze-01` completed all 20 stages with exit 0 and a roll-up
of 175 PASS / 7 N/A / **2 FAIL**. Neither FAIL is expected-by-construction, and two further
defects are invisible to the gates entirely. Directive 2 of the return handoff forbade fixing
anything on the run machine, so they were filed rather than repaired. This is where they get
repaired — before a re-run, not after, because one of them behaves differently on a clean
output tree than it did on the tree the production run inherited.

**Success Criteria** (what must be TRUE):

  1. **E4's real-rig row no longer fails Gate 1 for an unexplained reason.** The row nulls
     `degenerate_observations_at_solution` on a D-26 comment asserting E2's `benchmark.json`
     "predates this plan's discard_stats threading" — untrue as of this run, which records 198
     twice with the full cause/fate split. The decision is the author's and all three options
     are live: thread the value through and accept the anchor row publishing as `degenerate`
     under E4's exact `>0` rule; give that rule a threshold consistent with the library's own
     1% (198 is 0.268%); or keep the null, replace the stale rationale, and exempt
     `record_source="pipeline"` rows from Gate 1 explicitly. What must not survive is the
     current state, where a real FAIL is produced by a comment describing a world that ended.

  2. **`e1_seed_band_degeneracy_breakdown.json` exists or is unclaimed — consistently.**
     `suite_expectations.json`, `EXPECTATIONS.md` and `README.md` all name it; the authoritative
     writer table in the 2026-08-15 reshaped-artifacts todo has band rows for E5 and E7 and none
     for E1, and the code matches the table. All four documents agree afterwards, whichever way
     it is decided.

  3. **No log line claims a write that did not happen.** `_run_band` prints `Wrote <path>`
     ignoring `write_direct_call_benchmark`'s `False` return, so `e1_band.log` claims two writes
     the resumability guard skipped. The contradiction behind it is also resolved: the comment at
     `e1_refractive_comparison.py:1209-1212` says band mode must never overwrite the benchmark
     records, and the call at `:1300-1328` overwrites them. **Correction (2026-08-20, from planning):** the
     originally-stated mechanism was wrong. A clean `experiments/results/` does *not* remove the
     skip — stage `e1` runs with `--force` (`run_stage_e1`) and always precedes `e1_band` in the
     queue, so both records exist by the time the band runs. That is why the skip fired on
     2026-08-20 even though the run started from a clean tree. The defect is real; the live
     hazards are a `--force` band run, or a standalone band into a fresh `--out` with no
     single-seed run before it, where the write proceeds and stamps the records with `seeds[-1]`.

  4. **E1's band scope string states the domain that was actually run.** The provenance sidecar
     records `seeds: [42, 43, 44, 45]` while its own `scope` field authorises quoting E1 over a
     ten-seed, 640/960-row domain. Four is correct per ruling A1
     (`run_experiment_suite.sh:1452`); the prose is the survivor, and it is the field whose whole
     job is stating what a published number may be quoted over.

  5. **A fresh clone can run the suite by following the bundled instructions verbatim.**
     `experiments/HANDOFF.md` §1.2 says `pip install -e .`, which installs runtime dependencies
     only. The suite needs two extras: without `pytest` (`dev`) **e3 dies outright** on both
     `--check` and `--force`, taking `code_constants.csv`, `newton_iterations.csv`,
     `cpr_grouping.csv`, `e3_provenance.json` and the LaTeX fragments with it; without `psutil`
     (`bench`) the required manifest fields `cpu_count_logical` and `ram_total_bytes` go null.
     The working command is `pip install -e ".[dev,bench]"`. Ruled **record, do not refreeze** on
     2026-08-19 because the run had to start that night — this phase is where the refreeze
     happens. Verified by execution from a clean environment, not by asserting the string changed.

  6. **A new frozen sha is cut and tagged, replacing `rerun-freeze-01`,** and carries the same
     on-target verification Phase 27 applied to its predecessor: a smoke pass on the Linux run
     machine from a fresh clone, installed by following criterion 5's corrected command exactly.
     That pass is what licenses the re-run; the re-run itself is a re-execution of Phase 28 and
     is not in this phase's scope.

  7. **The completeness gate stops reporting a PASS it cannot justify.** `e2_production`'s two
     conditional artifacts — `degenerate_observations.csv` and `all_observation_depths.csv` — are
     both expected at `experiments/results` and both scored **PASS** on the reasoning that "this
     artifact is conditional and is legitimately absent when the condition did not hold (Phase 25
     D-08)". For this run that reasoning is false in both cases: the condition **held** (198
     observations were flagged) and both files **were written**, into
     `results_e2_invocations/` rather than `experiments/results`. The gate therefore reads
     "no flagged rows" from an absence that actually means "written somewhere else" — a green
     result standing in for an unchecked one, which is the failure mode
     `check_rerun_gates.py`'s own docstring calls out as a defect this project has already hit.
     These are the only two `conditional: true` entries in `suite_expectations.json`, so the
     mechanism is 100% mis-scored where it is used at all.

     What must be true afterwards: an absent conditional artifact is scored PASS **only** when the
     condition demonstrably did not hold, and an artifact written outside its expected directory is
     never silently green. The mechanism is open — correct the manifest's `dir`, have E2 emit into
     `--out` as well, or teach the completeness gate to resolve conditional artifacts across the
     invocation trees. Do **not** resolve it by removing the conditional mechanism or by treating
     absence as unconditionally acceptable. **Constraint:** `all_observation_depths.csv` is
     10.9 MB, so any fix that lands it under `experiments/results` needs a matching DATA-01b
     ignore rule or it trips `check-added-large-files --maxkb=1000`.

**Not in scope**: the re-run and the Zenodo results package — both wait on the new tag.

**Already settled, so criterion 1 is not a scientific question**: the 198 unprojectable
observations are **above-water board corners**. The 2026-08-15 classification todo opens by saying
"what the 198 are is not established, and no committed artifact can settle it" — true when written,
and superseded by Phase 24's DEGEN-02 instrumentation, which did not exist yet. This run's
`benchmark.json` decomposes them: **198 of 198 `above_interface`**, 0 `behind_camera`,
0 `interface_below_camera`, all in `stage3_intrinsic_pass`, all continued via the pinhole extension.
With trigger (b) — obliquity/TIR — already refuted on 2026-08-15, the breached-interface reading is
the only one left, and it matches the independent rate in `reconstruction_errors.csv` (31 of 7762
validation corners, 0.40%, reconstructing up to 51.7 mm above the interface in 2 of 52 frames)
against the 198's 0.268%. Criterion 1 is therefore purely a plumbing-and-policy decision about how
a known, physically-explained count is reported — not an open question about what it is.

**Plans**: 1/9 plans executed, 6 waves. Wave 1 leads with a tracer that proves the writer -> CSV -> gate ->
roll-up path end to end; every later plan expands from it. The re-freeze strictly follows all
of them. Plan 09 was added when criterion 7 was folded in; it is numbered last but executes in
wave 3, so the list below is ordered by wave rather than by number.

Plans:

- [x] 29.1-01-PLAN.md — E4's real-rig guard count: publish the value, exempt the pipeline row at both sites (SC-1) [wave 1, tracer]
- [ ] 29.1-02-PLAN.md — E1's band: unclaim the sidecar, enforce the write policy, derive the scope string (SC-2, SC-3, SC-4) [wave 2]
- [ ] 29.1-04-PLAN.md — install extras corrected in HANDOFF.md, proven from a clean environment (SC-5) [wave 2]
- [ ] 29.1-05-PLAN.md — discharge the 198-observation and E4-path todos against committed evidence (folded todos) [wave 2]
- [ ] 29.1-03-PLAN.md — bounded stale-string sweep over the run's writer modules, with a claim-sentence gate (SC-4) [wave 3]
- [ ] 29.1-09-PLAN.md — conditional artifacts: expect them where they are written, and make the condition machine-evaluated (SC-7) [wave 3]
- [ ] 29.1-06-PLAN.md — record the gate before/after, then archive the 2026-08-20 output aside (SC-1..SC-4, SC-6, SC-7) [wave 4]
- [ ] 29.1-07-PLAN.md — Phase 27 attempt 1's full verification bar, run locally (SC-6) [wave 5]
- [ ] 29.1-08-PLAN.md — cut, verify from a fresh clone, and push `rerun-freeze-02` (SC-5, SC-6) [wave 6, checkpoints]

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
| 23. Experiment Correctness Fixes | v2.1 | 4/4 | Complete    | 2026-08-17 |
| 24. Degeneracy Instrumentation | v2.1 | 2/2 | Complete    | 2026-08-18 |
| 25. Degeneracy Classification & Claim Licensing | v2.1 | 8/8 | Complete   | 2026-08-18 |
| 26. Full-Suite Driver & Handoff Readiness | v2.1 | 14/14 | Complete    | 2026-08-19 |
| 27. Frozen Single-Sha Handoff Package | v2.1 | 0/13 | Planned | - |
| 28. Suite Execution on Linux Machine | v2.1 | 0/TBD | Not started | - |
| 29. Gate Verification & Results Commit | v2.1 | 0/TBD | Not started | - |
| 30. Post-Submission Reconciliation | v2.1 | 0/TBD | Not started | - |
