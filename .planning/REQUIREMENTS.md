# Requirements: v2.1 Clean Experimental Suite

**Milestone goal:** Land every experiment-suite fix that changes what the suite measures,
records, or can claim; freeze one sha; hand a complete full-suite driver to a larger Linux
machine for the run; reconcile the returned single-version results into the manuscript's
evidence base.

**Source of truth:** the 19 todos in `.planning/todos/pending/`. Each requirement below names
the todo it discharges. The todos carry the measurements, line numbers, and rationale — this
file does not restate them.

**Scope test (author, 2026-08-15):** *does it change what the suite measures, records, or can
claim?* If yes, it is in scope and lands **before** the run. If it only changes how fast or how
cheaply the library gets there, it waits.

**Execution split:** code edits land on this machine. The full re-run executes on a larger Linux
machine, so the driver, manifest, and gates must be complete and portable before handoff.

**Deadline split:** FIX / DEGEN / DRIVER / BAND / RUN land before the **2026-08-21** SoftwareX
submission. POST follows it.

---

## v2.1 Requirements

### Experiment Correctness (FIX) — changes a number, or what a number is licensed to say

- [x] **FIX-01**: E1's non-refractive arm pins `water_z`, which is an exact null direction there,
      driving the arm's 14,949 degenerate observations to zero without pinning it in the
      refractive arm — todo `2026-08-15-pin-water-z-in-e1-non-refractive-arm`

      *Acceptance criterion corrected 2026-08-17.* Verified by the **recovered `water_z` against
      ground truth 1.031 m**, not by the guard count. Measured: FIX-02 alone drives the count to 0
      with `water_z` at 0.0120 m — 1.02 m from truth — at a cost identical to the unpinned solve to
      10 significant figures. The count reports where the free parameter landed, not whether it was
      removed, so it is corroboration only. **Lands before FIX-02** in the non-refractive arm; the
      pinned-and-normal-free combination is unmeasured and its `water_z` is the first thing the
      implementation must emit.
- [x] **FIX-02**: E1 and E7 solve with the interface normal free, matching the production
      pipeline's DOF count instead of inheriting the library signature default —
      todo `2026-08-15-e1-and-e7-run-with-the-interface-normal-fixed-unlike-everything-else`
- [x] **FIX-03**: E6 reports signed, gauge-corrected Z error and emits the per-camera
      decomposition behind the collinear caveat, both landing in the same change —
      todo `2026-08-15-e6-z-error-reporting-and-per-camera-gauge-decomposition`
- [x] **FIX-04**: E7's `fixed` rows are labelled vacuous-by-construction rather than reported as
      a measured `no_signature` verdict —
      todo `2026-08-15-e7-vacuous-fixed-rows-ship-as-measured-nulls`
- [x] **FIX-05**: E4's aggregator resolves E2's benchmark row relative to the active output
      directory, so the real-rig row survives `--out` —
      todo `2026-08-13-e4-aggregator-hardcodes-e2-benchmark-path`

      *Scope corrected 2026-08-17.* **Two call sites**, not one: `_run_check`
      (`e4_benchmark_grid.py:1876`) passes the module-level `E2_BENCHMARK_PATH` too. And `--check`
      cannot be the verification: 33 of its 35 columns already reproduce to 1e-6, while `exit_code`
      (hardcoded `None` at :1872) and `status_reason` can never match — red before the fix and red
      after. Consumes DRIVER-03's `--check` contract decision rather than inventing a local one.
- [x] **FIX-06**: The stale provenance strings in `e2_real_rig.py` and `synthetic.py` describe what
      is actually true — todo
      `2026-08-15-correct-stale-strings-in-e2-and-the-synthetic-generator`

      *Count corrected 2026-08-17: **four** code sites, not three*, plus one planning-doc header.
      The unfiled fourth is `e2_real_rig.py:555-563`, a comment carrying the retired-archive claim
      as a concrete wrong triple ("60 usable → 12 validation → 1,817 comparisons" against the
      verified 262 → 52 → 7,762) on the branch the re-run uses. It is the same claim as the
      `--config` help text and must be fixed in the same pass.
      `19.1-E2-FRAMESET-PROVENANCE.md:35-48` gets a **supersession header, not an edit** — it is
      correct as a description of the superseded record `18645385`.

### Degeneracy Observability (DEGEN) — the gate quantity must be readable off the artifacts

- [x] **DEGEN-01**: `degenerate_observations_at_solution` reaches the production benchmark
      record and is persisted by E5 and the band runs, instead of being lost before it is
      written — todo `2026-08-15-degeneracy-counter-is-unobservable-and-merges-two-failure-kinds`

      *Scope narrowed 2026-08-17:* **E6's band already persists the column** (present on all 102
      rows). The gap is E5, E1 and E7 only. E1's 14,949 lives solely in
      `e1_benchmark_nonrefractive.json → problem_shape` and appears in no CSV.
- [x] **DEGEN-02**: The counter is split by failure kind **and** by stage, so the re-run's
      artifacts can answer the degeneracy question without re-running anything —
      todo `2026-08-15-degeneracy-instrumentation-the-rerun-must-emit`
- [x] **DEGEN-03**: The degenerate-observation warning is narrowed to the cases it actually
      applies to, and its cause list is corrected before it ships to users —
      todo `2026-08-15-narrow-the-degenerate-observation-warning`
- [ ] **DEGEN-04**: The production rig's 198 unprojectable observations are classified, with the
      finding recorded so the manuscript can disclose the count and say what it is —
      todo `2026-08-15-classify-the-198-unprojectable-observations`
- [x] **DEGEN-05**: The first-order optimality reported by each stage is decomposed by parameter
      block, so a reader can tell a residual concentrated in a pinned or bounded slot (benign)
      from one spread across extrinsics and board poses (a non-stationary solve) without
      re-running anything — origin `Phase 23 verification run at 330f9ef`, recorded in
      `23-01-SUMMARY.md § Evidence`

      *Why this is not covered by DEGEN-02:* DEGEN-02 splits the **degeneracy counter** by
      failure kind and stage. This is a different quantity — the projected-gradient KKT residual
      attributed to parameter blocks — and the two answer different questions. Keeping them
      separate keeps the traceability honest.

      *Motivating measurement (2026-08-17):* E1's non-refractive arm reports
      `optimality_intrinsic` of 92.78 pinned, 49.65 unpinned, and 873.98 with the normal fixed,
      against the refractive arm's 0.0247 on the same scenario and seed.

      *Measured 2026-08-17 by `.planning/probes/2026-08-17-optimality-decomposition/` — supersedes
      the pin explanation:* the pinned `water_z` contributes **0.00%** of the reported optimality
      (1.95e-11 of 92.78), not the majority. scipy's `trf` reports `||g·v||∞` with `v` the
      Coleman-Li *distance to the bound*, so a pinned slot is crushed toward zero, not inflated —
      the phase documents describe an unscaled projected gradient, which is not what scipy
      reports. The reported number is **entirely the max extrinsic gradient** (extrinsics are
      unbounded, so `v = 1`): 92.78 non-refractive against 0.0247 refractive, a 3751x gap where
      the residual-magnitude ratio is only 2.03x. Both passes terminated on `ftol`, never `gtol`
      — cost stopped moving while the gradient stayed large.

      *Resolved the same day by the warm-restart test (`probe_warm_restart.py`):* restarting each
      solve from its own solution recovers **no cost** (largest relative drop 1.8e-9, on the
      non-refractive intrinsic pass). **E1's baseline is converged and the comparison is fair** —
      the ratio is not inflated by under-optimization, and the 97–178x band is *strengthened*, not
      threatened. The fairness objection this requirement was opened over is answered.

      *What replaces it — the reason the requirement still stands:* `optimality` is **unstable at
      a fixed solution**. Cost moves 1.8e-9 while the reported number goes 92.78 → 27.58 → 2.16, a
      43x range (control: the one solve whose cost moved exactly zero reports a bit-identical
      optimality all three times).

      *Cause settled 2026-08-17 by `probe_fd_noise.py`.* Two candidates were on the table; the
      FD-noise one is **falsified**. The production Jacobian's gradient agrees with a
      central-difference Jacobian to five significant figures (92.7841 vs 92.7843), so
      `optimality` measures a real gradient and **no benchmark record needs re-interpreting on
      Jacobian-error grounds**. What remains is genuine **severe ill-conditioning**: at call 4
      cost fell 2.7e-5 against a gradient of 92.78 (step ~3e-7) while the gradient fell ~90,
      implying directional curvature ~3e8. The solution sits on the flat floor of an extremely
      narrow, high-curvature valley.

      *Magnitude-dependent reliability (same probe, applies suite-wide):* naive FD steps are
      catastrophic where the true gradient is small (call 1 inflates six orders at `rel_step`
      1e-10) and harmless where it is large (call 4 is stable at every step tried); the production
      step rule tracks the 3-point reference in both regimes, which **validates the library's FD
      step choice**. Consequence: large optimality values are trustworthy, small ones are not
      (call 1's 0.001146 disagrees 44% with its reference). Differences between two *small*
      optimality values carry no information; the 0.0247-vs-92.78 gap is solid. Recorded in
      `.planning/knowledge-base.md`.

      *Third regime found:* the scalar also mixes `v ≈ 700` for wide-bounded intrinsics (call 4's
      intrinsics block reads 49.97 scaled against a 0.068 raw gradient). `optimality` is therefore
      not a like-for-like maximum across blocks under any configuration — independent of anything
      Phase 23 changed, and the core reason this requirement ships the decomposition rather than
      the scalar.

      *Placement:* the decomposition is computed in `_optim_common.py`, which already owns the
      parameter layout via `build_structural_column_groups` (it carries a dedicated `water_z`
      group slot). Computing it in `experiments/` would duplicate that layout — the exact drift
      that function's docstring exists to prevent. E1 records it beside the existing
      `stages.*.optimality`, the same path `degenerate_observations_at_solution` takes.

      *Deadline:* must land before the Phase 27 freeze. A diagnostic absent at the frozen sha
      does not appear in Phase 28's results, and retrofitting it costs another full-suite run.

### Run Infrastructure (DRIVER) — one sha, every invocation, a portable handoff

- [ ] **DRIVER-01**: `rerun_19_3.sh` covers every invocation in the suite, including the band
      runs and E2, closing the coverage gap where the six-sha provenance spine fractured —
      todo `2026-08-15-make-the-suite-driver-cover-every-invocation`
- [ ] **DRIVER-02**: The suite emits one run manifest capturing the execution environment, with
      `aquacal_version` and the OpenCV build recorded truthfully —
      todo `2026-08-15-emit-a-single-run-manifest-for-the-full-suite`
- [ ] **DRIVER-03**: `--check` has a decided, documented meaning across a deliberate baseline
      re-base, with written expectations replacing the reproduction bar where schemas change —
      todo `2026-08-15-suspend-programmatic-check-for-reshaped-artifacts`

      *Concrete case added 2026-08-17:* E4's `--check` is **already** structurally always-red,
      before any schema change — `exit_code` (hardcoded `None` because no subprocess runs) and
      `status_reason` can never match, while all 33 metric columns reproduce to 1e-6. The contract
      must say what happens to columns that are artifacts of the checking path itself rather than
      of the run. FIX-05 (Phase 23) consumes this answer, so the decision cannot wait for Phase 26
      to begin — settle it early and let Phase 26 document it.
- [ ] **DRIVER-04**: Every pre-re-run output tree is moved aside before the run, so no stale
      artifact can be mistaken for a fresh one — phase 1 of todo
      `2026-08-15-archive-stale-outputs-before-the-run-purge-them-after`

### Claim Licensing (BAND)

- [ ] **BAND-01**: E1's seed band gains a `noise_std` axis, so its promoted absolute-accuracy
      numbers carry a stated domain; the `n_cameras` geometry axis is explicitly skipped —
      todo `2026-08-14-decide-whether-e1-may-carry-absolute-accuracy-claims`

### The Re-run (RUN)

- [ ] **RUN-01**: The library is frozen at one sha and packaged for the Linux machine, with the
      driver, gates, and environment requirements verified to run there before handoff
- [ ] **RUN-02**: The full experiment suite — E1 through E7, the band runs, and **E2** — executes
      once end to end at that single sha
- [ ] **RUN-03**: `check_rerun_gates.py` passes over the complete run, including Gate 3's
      single-sha assertion now that the previously-uncovered stages are inside the queue
- [ ] **RUN-04**: The returned results are committed with provenance intact, and every §3-facing
      number is traceable to this run
- [ ] **RUN-05**: The Zenodo record is split into immutable inputs and a versioned results
      package, and the results package matching this run's numbers is published **before** the
      2026-08-21 submission, so the archive the paper cites agrees with the §3 it supports —
      todo `2026-08-15-repackage-and-reupload-the-zenodo-archive`

      *Re-timed 2026-08-15 (was POST-02).* Phase 29 commits new §3 numbers pre-submission, so
      leaving the archive until after the deadline would ship a paper citing record 21889922
      whose bundled `reference_outputs/` contradict its own §3 — a reviewer downloading it to
      check reproducibility meets stale outputs. The split is not cheap to defer either: the
      record is a **single** 4.35 GB zip, so there is no input file for Zenodo's new-version flow
      to carry forward, and cheap results revisions only become possible *after* the split. The
      4.35 GB re-upload is therefore staged during Phase 28's run window (from the Windows box,
      while the Linux run is going), and the results package is published once Phase 29 verifies.

### Post-Submission Reconciliation (POST)

- [ ] **POST-01**: §3, the Zenodo archive's `reference_outputs/`, and the tutorial's
      expected-value table are re-cut as a matched set against the new E2 numbers
- **POST-02** — *re-timed to **RUN-05** on 2026-08-15 and moved to Phase 29.* The Zenodo split
  must land before submission, not after it. ID retired; see RUN-05 above.
- [ ] **POST-03**: Stale output trees are purged from the library, so the shipped package carries
      only the data the paper cites — phase 2 of todo
      `2026-08-15-archive-stale-outputs-before-the-run-purge-them-after`
- [ ] **POST-04**: MF-19 is closed in `MANUSCRIPT-FINDINGS.md`, and any finding the re-run
      contradicts or newly raises is appended

---

## Future Requirements

Deferred with a reason, scheduled for after the SoftwareX submission.

- **Source-level `normal_fixed` reconciliation** — the config layer defaults `False`, eighteen
  library signatures default `True`. FIX-02 fixes this at the experiment level pre-run; the
  source-level fix waits until the suite is no longer the paper's evidence.
  Todo `2026-08-15-POST-SUBMISSION-reconcile-normal-fixed-defaults-between-config-and-library`
- **Degeneracy-gate scope for real-rig runs** — blocked until DEGEN-04 reports what the 198 are.
  Todo `2026-08-15-decide-degeneracy-gate-scope-for-real-rig-runs`
- **INDEX-01, INDEX-02, INDEX-03** — Phase 20 refractive index helper, deferred 2026-08-07 on
  MF-13 (the effect is ~5× below seed noise). Deferred, not dropped.
- **DOCS-07** — manuscript C1 metadata cell and which DOI the paper cites. Manuscript-side, the
  author's work.
- **CLEAN-01** — retire the `initial_distances` compat shim. Unblocked by DATA-02, still a
  breaking change for pre-v1.4 configs.
- **`download_with_progress` HTTP Range/resume** — non-breaking to add, called a convenience.

## Out of Scope

- **Solver memory and CPU work** — the dense `.toarray()` in `_optim_common.py`, LSMR
  preconditioning, an analytic Jacobian. Every experiment routes through that file, so touching
  it makes the fresh suite unattributable, which is the one thing the re-run exists to prevent.
  Todo `2026-07-23-reduce-memory-and-cpu-load-during-calibration`. Revisit after submission.
- **Any change that only makes the library faster or cheaper** — fails the scope test.
- **New calibration features** — this milestone changes what the suite records and claims, not
  what the library can do.

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| FIX-01 | Phase 23 | Complete |
| FIX-02 | Phase 23 | Complete |
| FIX-03 | Phase 23 | Complete |
| FIX-04 | Phase 23 | Complete |
| FIX-05 | Phase 23 | Complete |
| FIX-06 | Phase 23 | Complete |
| DEGEN-01 | Phase 24 | Complete |
| DEGEN-02 | Phase 24 | Complete |
| DEGEN-03 | Phase 24 | Complete |
| DEGEN-04 | Phase 25 | Pending |
| DEGEN-05 | Phase 24 | Complete |
| BAND-01 | Phase 25 | Pending |
| DRIVER-01 | Phase 26 | Pending |
| DRIVER-02 | Phase 26 | Pending |
| DRIVER-03 | Phase 26 | Pending |
| DRIVER-04 | Phase 26 | Pending |
| RUN-01 | Phase 27 | Pending |
| RUN-02 | Phase 28 | Pending |
| RUN-03 | Phase 29 | Pending |
| RUN-04 | Phase 29 | Pending |
| RUN-05 | Phase 29 | Pending |
| POST-01 | Phase 30 | Pending |
| POST-02 | — | Retired — re-timed to RUN-05 (2026-08-15) |
| POST-03 | Phase 30 | Pending |
| POST-04 | Phase 30 | Pending |

**Coverage: 23/23 v2.1 requirements mapped.** (Note: the milestone brief's "19 todos" refers to
the pending-todo backlog files; the discrete v2.1 requirement IDs derived from them number 23 —
FIX-01..06 (6), DEGEN-01..04 (4), DRIVER-01..04 (4), BAND-01 (1), RUN-01..04 (4), POST-01..04 (4).
All 23 are mapped above, none orphaned.)
