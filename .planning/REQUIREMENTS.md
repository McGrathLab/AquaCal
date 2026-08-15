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

- [ ] **FIX-01**: E1's non-refractive arm pins `water_z`, which is an exact null direction there,
      driving the arm's 14,949 degenerate observations to zero without pinning it in the
      refractive arm — todo `2026-08-15-pin-water-z-in-e1-non-refractive-arm`
- [ ] **FIX-02**: E1 and E7 solve with the interface normal free, matching the production
      pipeline's DOF count instead of inheriting the library signature default —
      todo `2026-08-15-e1-and-e7-run-with-the-interface-normal-fixed-unlike-everything-else`
- [ ] **FIX-03**: E6 reports signed, gauge-corrected Z error and emits the per-camera
      decomposition behind the collinear caveat, both landing in the same change —
      todo `2026-08-15-e6-z-error-reporting-and-per-camera-gauge-decomposition`
- [ ] **FIX-04**: E7's `fixed` rows are labelled vacuous-by-construction rather than reported as
      a measured `no_signature` verdict —
      todo `2026-08-15-e7-vacuous-fixed-rows-ship-as-measured-nulls`
- [ ] **FIX-05**: E4's aggregator resolves E2's benchmark row relative to the active output
      directory, so the real-rig row survives `--out` —
      todo `2026-08-13-e4-aggregator-hardcodes-e2-benchmark-path`
- [ ] **FIX-06**: The three stale provenance strings in `e2_real_rig.py` and `synthetic.py`
      describe what is actually true — todo
      `2026-08-15-correct-stale-strings-in-e2-and-the-synthetic-generator`

### Degeneracy Observability (DEGEN) — the gate quantity must be readable off the artifacts

- [ ] **DEGEN-01**: `degenerate_observations_at_solution` reaches the production benchmark
      record and is persisted by E5 and the band runs, instead of being lost before it is
      written — todo `2026-08-15-degeneracy-counter-is-unobservable-and-merges-two-failure-kinds`
- [ ] **DEGEN-02**: The counter is split by failure kind **and** by stage, so the re-run's
      artifacts can answer the degeneracy question without re-running anything —
      todo `2026-08-15-degeneracy-instrumentation-the-rerun-must-emit`
- [ ] **DEGEN-03**: The degenerate-observation warning is narrowed to the cases it actually
      applies to, and its cause list is corrected before it ships to users —
      todo `2026-08-15-narrow-the-degenerate-observation-warning`
- [ ] **DEGEN-04**: The production rig's 198 unprojectable observations are classified, with the
      finding recorded so the manuscript can disclose the count and say what it is —
      todo `2026-08-15-classify-the-198-unprojectable-observations`

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

### Post-Submission Reconciliation (POST)

- [ ] **POST-01**: §3, the Zenodo archive's `reference_outputs/`, and the tutorial's
      expected-value table are re-cut as a matched set against the new E2 numbers
- [ ] **POST-02**: The Zenodo record is split into immutable inputs and a versioned results
      package, so a results revision no longer costs a 4.35 GB re-upload —
      todo `2026-08-15-repackage-and-reupload-the-zenodo-archive`
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

Filled by the roadmapper.
