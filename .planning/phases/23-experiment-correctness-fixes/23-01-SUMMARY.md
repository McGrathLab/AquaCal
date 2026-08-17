---
phase: 23-experiment-correctness-fixes
plan: 01
subsystem: experiments
tags: [calibration, refractive-geometry, water_z, normal_fixed, bundle-adjustment, provenance]

# Dependency graph
requires:
  - phase: 22
    provides: v2.1 roadmap, FIX-01/FIX-02 requirement definitions, D-02 probe measurements
provides:
  - "water_z_bounds override threaded from calibrate_synthetic through both stage-3 passes to build_bounds"
  - "E1's non-refractive arm pinned at its scenario's own ground-truth water_z via a degenerate bounds interval"
  - "E1 and E7 solve with normal_fixed=False explicitly at every experiment-level solver call site"
  - "AST-based recurrence-prevention test across all five solving experiments"
affects: [24-degeneracy-instrumentation, 27-frozen-handoff, 28-suite-execution, e1-experiment, e7-experiment]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Degenerate bounds interval (lb=ub-/+1e-12) as a solve-time pin mechanism, distinct from a library boolean flag"
    - "Module-level *_NORMAL_FIXED constant referenced at every call site (mirrors E3/E4/E5/E6 convention)"
    - "AST-walk test asserting a keyword argument is present at every call site of named callees, across a declared module list"

key-files:
  created: []
  modified:
    - src/aquacal/calibration/_optim_common.py
    - src/aquacal/calibration/interface_estimation.py
    - src/aquacal/calibration/refinement.py
    - src/aquacal/datasets/pipelines.py
    - experiments/e1_refractive_comparison.py
    - experiments/e7_interface_ablation.py
    - tests/unit/test_optim_common.py
    - tests/unit/test_experiments_e1.py
    - tests/unit/test_experiments_provenance.py
    - .gitignore

key-decisions:
  - "D-01: water_z held by a bounds freeze threaded from the experiment (water_z_bounds param), not a library water_z_fixed flag"
  - "D-03: acceptance is the recovered water_z against ground truth 1.031 m, never the guard count alone"
  - "D-04: both arms' benchmark records carry the same provenance key set so a reader can diff the asymmetry and its justification"
  - "D-14: FIX-01 and FIX-02 land as two separate, ordered commits inside this one plan, bisectable apart"

patterns-established:
  - "water_z_bounds: tuple[float, float] | None = None appended last in build_bounds/optimize_interface/joint_refinement/calibrate_synthetic signatures — zero-signature-break convention"

requirements-completed: [FIX-01, FIX-02]

# Metrics
duration: 33min (Tasks 1-2 only; Task 3/4 not run by this executor, see below)
completed: 2026-08-17
---

# Phase 23 Plan 01: E1 water_z pin and E1/E7 normal_fixed unification (FIX-01, FIX-02) Summary

**Threaded a `water_z_bounds` override from `calibrate_synthetic` through both stage-3 passes to pin E1's non-refractive arm at its own ground-truth `water_z`, and made E1/E7 solve with the interface normal free (`normal_fixed=False`) at every call site, both with an AST-based recurrence-prevention test.**

## Performance

- **Duration:** 33 min (Task 1 at 10:00:45-04:00, Task 2 at 10:32:44-04:00; wall time includes ~20 min of targeted pytest verification per task)
- **Started:** 2026-08-17T~09:55:00-04:00 (approx, plan read/setup)
- **Completed (Tasks 1-2 only):** 2026-08-17T10:32:44-04:00
- **Tasks:** 2 of 4 completed by this executor (Task 3 is a `checkpoint:human-verify` explicitly reserved for the orchestrator/user; Task 4 depends on Task 3's observed values)
- **Files modified:** 10

## IMPORTANT: Plan is NOT fully complete

This plan has four tasks. **Only Tasks 1 and 2 (the two `type="auto"` tasks) were executed by this
worktree agent.** Task 3 is a `checkpoint:human-verify` gated `blocking`, and the plan's own text is
explicit that it **"belongs to the orchestrator or the user, never to a plan executor — a
backgrounded run inside a subagent stalls permanently."** Task 4 (write the `## Evidence` section
below into this SUMMARY) requires Task 3's observed values as input and could not be completed
without them.

**What remains, for the orchestrator or user:**

1. Run, in the foreground, unbuffered:
   ```
   python -u -m experiments.e1_refractive_comparison --out experiments/verify_23/
   ```
   (~5-7 min; see the plan's Task 3 `<how-to-verify>` for the six checks to run against the two
   output records.)
2. Read `experiments/verify_23/e1_benchmark_nonrefractive.json` and
   `experiments/verify_23/e1_benchmark_refractive.json` and record: non-refractive
   `accuracy.water_z_recovered_m`, its `problem_shape.degenerate_observations_at_solution`,
   refractive `accuracy.water_z_recovered_m`, and both `diagnostics.stage3_interface_optimization
   /stage3_intrinsic_pass` `cost` values.
3. Append an `## Evidence` section to this file (this SUMMARY.md, not a new one) per Task 4's
   `<action>` in `23-01-PLAN.md`: the D-06 bound-hit table, the pinned + normal-free measurement
   using the observed values from step 2, the optimality caveat (92.78 pinned vs 49.65 unpinned is
   expected, not a regression), the tilt-cost-not-tilt-recovery precision note, the E7 propagation
   warning, and a `### Ledger candidate` note. Commit that addition separately.
4. `experiments/verify_23/` is git-ignored (already landed in Task 1's commit, see below) — nothing
   under it is ever committed; `git status --porcelain experiments/verify_23` must stay clean.

Code-level readiness for that run: `water_z_bounds` and `normal_fixed=False` are both fully wired
and unit-tested (see below) — the pinned + normal-free measurement is expected to reproduce the
D-02 probe's `.planning/probes/2026-08-17-phase-23-recon/probe_pinned_normal_free.py` result
(`water_z` recovered 1.030999999999 m, guard count 0) since this plan's implementation follows that
probe's mechanism exactly (bounds override reaching both stage-3 passes, not a first-pass-only
patch).

## Accomplishments

- **FIX-01:** `water_z_bounds` threads from `calibrate_synthetic` through both stage-3 passes
  (`optimize_interface` and `joint_refinement`) to `build_bounds`, which overwrites the default
  `[0.01, 2.0]` water_z slot(s) with a degenerate interval when given. E1's non-refractive arm
  (`n_water=1.0`) pins `water_z` at its scenario's own ground-truth value via
  `resolve_water_z_pin`; the refractive arm stays unpinned by construction.
- All three of E1's benchmark writers (`_run_full`, `_run_smoke`, `_run_band`) now emit the D-04
  provenance triple (`water_z_pinned_m`/`water_z_pin_mechanism`/`water_z_pin_reason`) via a shared
  `build_water_z_provenance` helper, plus `water_z_recovered_m` in the `accuracy` block.
- **FIX-02:** E1 and E7 pass `normal_fixed=False` explicitly at every experiment-level solver call
  site (E1's `_run_one_model`; E7's two `_run_arm` calls via a new `E7_NORMAL_FIXED` constant),
  matching production (`CalibrationConfig.interface_normal_fixed` defaults to `False`) rather than
  silently inheriting the library's `normal_fixed=True` default.
- A new AST-based recurrence-prevention test
  (`tests/unit/test_experiments_provenance.py::test_every_experiment_passes_normal_fixed_explicitly`)
  walks E1/E4/E5/E6/E7's source and fails loudly, naming module/callee/line, if any
  `calibrate_synthetic`/`optimize_interface`/`joint_refinement` call omits `normal_fixed`.
- No library default was flipped; `experiments/verify_23/` was added to `.gitignore` (D-12).

## Task Commits

1. **Task 1: FIX-01 — thread a water_z bounds override to both stage-3 passes and pin E1's
   non-refractive arm** - `fb33db4` (feat)
2. **Task 2: FIX-02 — E1 and E7 solve with the interface normal free, recorded and
   test-guarded** - `57ac430` (feat)

Tasks 3 and 4 were not executed by this agent (see "IMPORTANT" section above).

## Files Created/Modified

- `src/aquacal/calibration/_optim_common.py` - `water_z_bounds` param on `build_bounds`, overwrites
  the default slot when given; default `[0.01, 2.0]` bound untouched
- `src/aquacal/calibration/interface_estimation.py` - forwards `water_z_bounds` to `build_bounds`
  in `optimize_interface`
- `src/aquacal/calibration/refinement.py` - forwards `water_z_bounds` to `build_bounds` in
  `joint_refinement`
- `src/aquacal/datasets/pipelines.py` - `calibrate_synthetic` forwards `water_z_bounds` to both
  stage-3 passes
- `experiments/e1_refractive_comparison.py` - `WATER_Z_PIN_HALF_WIDTH`, `resolve_water_z_pin`,
  `build_water_z_provenance`; `_run_one_model` pins the non-refractive arm, passes
  `normal_fixed=False`, returns the resolved pin as a sixth tuple element; all four call sites and
  all three benchmark writers updated
- `experiments/e7_interface_ablation.py` - `E7_NORMAL_FIXED = False` constant referenced at both
  solver call sites in `_run_arm` and in `_build_arm_benchmark_payload`'s `solver_config`
- `tests/unit/test_optim_common.py` - `TestWaterZBoundsOverride`: the override pins exactly the
  water_z slot(s) across `normal_fixed`/`shared_interface` combinations, and omitting it reproduces
  the default byte-identically
- `tests/unit/test_experiments_e1.py` - `resolve_water_z_pin`/`build_water_z_provenance` coverage,
  a source-level threading test naming Trap 1 (first-pass-only is a measured, silent failure mode),
  and existing `_run_one_model` tests updated for the new six-element return tuple
- `tests/unit/test_experiments_provenance.py` - `test_every_experiment_passes_normal_fixed_explicitly`
- `.gitignore` - `experiments/verify_23/` (D-12)

## Decisions Made

- Followed the plan's D-01 exactly: the pin is a bounds override threaded as a parameter, not a
  library `water_z_fixed` flag (that surgery, mirroring `normal_fixed`'s 101-reference precedent,
  is explicitly deferred post-submission).
- FIX-01 and FIX-02 landed as two separate commits in that order (D-14), verified via
  `git diff --stat HEAD~1 -- src/aquacal/` showing no change for FIX-02's commit and
  `git show HEAD -- experiments/e1_refractive_comparison.py` showing no `normal_fixed` diff in
  FIX-01's commit.
- `test_every_experiment_passes_normal_fixed_explicitly` was written as a module-level function
  (not nested in a test class) so the plan's literal acceptance-criterion pytest node ID
  (`tests/unit/test_experiments_provenance.py::test_every_experiment_passes_normal_fixed_explicitly`)
  resolves exactly.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Own test's expected substring count for `calibrate_synthetic`'s water_z_bounds forwarding was wrong**
- **Found during:** Task 1 verification (targeted pytest run)
- **Issue:** The newly-written test
  `test_water_z_bounds_threads_through_both_stage3_call_sites` asserted
  `inspect.getsource(calibrate_synthetic).count("water_z_bounds=") == 3`, expecting the parameter's
  own type-annotated signature line (`water_z_bounds: tuple[float, float] | None = None,`) to also
  match the substring `"water_z_bounds="`. It does not (the `:` type annotation sits between the
  name and the `=`), so the true count is 2 (the two forwarding calls only).
- **Fix:** Corrected the assertion to count `"water_z_bounds=water_z_bounds"` occurrences (2) with
  a comment explaining why the signature line itself doesn't match.
- **Files modified:** `tests/unit/test_experiments_e1.py`
- **Verification:** Targeted pytest run passed (120/120)
- **Committed in:** `fb33db4` (Task 1 commit)

**2. [Rule 3 - Blocking] `import ast` not at top of file tripped ruff's E402**
- **Found during:** Task 2 commit (pre-commit hook)
- **Issue:** `import ast` was placed immediately above the new `NORMAL_FIXED_MODULES` block,
  partway through `tests/unit/test_experiments_provenance.py`, which ruff flags as a
  module-level-import-not-at-top violation.
- **Fix:** Moved `import ast` to the file's top-level import block alongside `json`/`pathlib`/
  `subprocess`.
- **Files modified:** `tests/unit/test_experiments_provenance.py`
- **Verification:** `ruff check` passed; `test_every_experiment_passes_normal_fixed_explicitly`
  re-run and still passing.
- **Committed in:** `57ac430` (Task 2 commit)

---

**Total deviations:** 2 auto-fixed (1 bug in this plan's own new test, 1 blocking lint failure)
**Impact on plan:** Both are narrow, self-contained fixes to code this plan itself introduced. No
scope creep; no change to production or experiment logic beyond what the plan specified.

## Issues Encountered

- **Task 2's targeted pytest command (`test_experiments_provenance.py test_experiments_e1.py
  test_e1_band_mode.py test_e7_band_mode.py test_datasets_pipelines.py -x -q -m "not slow"`) ran
  far longer than expected — roughly 20 minutes of wall-clock CPU time** before completing
  successfully (all passed/skipped, 0 failed, exit code 0; confirmed via the captured output after
  the fact). The likely cause: `normal_fixed=False` adds 2 tilt DOF to every E1/E7 solve these test
  files exercise (`test_e1_band_mode.py`/`test_e7_band_mode.py` run several `--seeds`-band smoke
  solves each), and E7's per-camera arms are already a documented near-degenerate
  height/distance parameterization (the ablation's own subject) — adding free tilt on top of that
  plausibly slows convergence substantially for those specific arms. This did not indicate a bug;
  the command completed cleanly and all assertions passed. No code change was made in response to
  this — flagging it here as a process note in case a similar targeted run is scoped in a future
  plan touching E7's per-camera arms with tilt free.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- FIX-01 and FIX-02 are both code-complete, unit-tested, and committed.
- **Task 3 (the verification run) and Task 4 (the Evidence section) are outstanding** and must be
  completed by the orchestrator or user before this plan can be considered fully done — see the
  "IMPORTANT" section above for the exact steps.
- No blockers for plans 23-02/23-03/23-04 (FIX-05, FIX-03/FIX-04, FIX-06 respectively) — per the
  phase context, all four plans in this wave are file-disjoint and were confirmed genuinely
  independent (D-13/amendment 2026-08-17).

---
*Phase: 23-experiment-correctness-fixes*
*Completed: 2026-08-17 (Tasks 1-2 only; Tasks 3-4 outstanding)*

## Self-Check: PASSED

All files listed under "Files Created/Modified" confirmed present on disk; both task commit
hashes (`fb33db4`, `57ac430`) confirmed present in `git log --oneline --all`.
