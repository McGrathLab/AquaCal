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
duration: 33min (Tasks 1-2, this executor) + Task 3 (orchestrator, foreground verification run) + Task 4 (this continuation, evidence transcription)
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

## Plan status: complete

All four tasks are done. Tasks 1-2 (FIX-01, FIX-02) were executed by the first worktree agent.
Task 3 (the verification run) was executed by the orchestrator in the foreground, unbuffered, per
the plan's explicit instruction that a backgrounded run inside a subagent stalls permanently — its
observed values are transcribed into `## Evidence` below. Task 4 (this section) was written by a
continuation agent using those observed values.

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
- No library default was flipped; Phase 23's in-phase verification output directory was added to
  `.gitignore` (D-12).

## Evidence

Values below are transcribed directly, never as a path into the phase's git-ignored verification
output directory (does not survive). Non-refractive-arm values labeled "measured" come from Task 3's foreground
verification run at commit `330f9ef`; "D-02 probe" values come from
`.planning/probes/2026-08-17-phase-23-recon/probe_pinned_normal_free.py`.

### D-06 bound-hit table

| E1 arm | recovered `water_z` | landed |
|---|---|---|
| n=1.0, normal fixed | 1.990 m | on the 2.0 ceiling |
| n=1.0, normal free | 0.0120 m | on the 0.01 floor |
| n=1.333, normal free | 1.0236 m | interior (−7.43 mm from GT) |

Both degenerate arms (row 1, row 2) terminated **on** a bound rather than at an interior minimum —
that is stronger evidence for the null direction than the cost-flatness sweep alone: an
unconstrained solve given a genuinely null direction has no force pulling it toward any particular
value, so it drifts until a bound stops it. The general "parameter resting on its bound" detector
that this table implies is handed to DEGEN-02 in Phase 24 and is deliberately not implemented here.

### Pinned + normal-free measurement (the configuration the re-run actually executes)

Non-refractive arm (`n_water=1.0`, `water_z` pinned via a degenerate bounds interval, `normal_fixed=False`):

| metric | D-02 probe | Task 3 measured (commit `330f9ef`) |
|---|---|---|
| `water_z` recovered | 1.030999999999 m (GT 1.031 m) | 1.030999999999 m — matches to the digit |
| `degenerate_observations_at_solution` | 0 | 0 |
| `cost_interface` | 26067.0205835744 | 26067.0205835744 |
| `cost_intrinsic` | 15097.612313075724 | 15097.612313075724 |
| `status_interface` / `status_intrinsic` | 2 / 2 | 2 / 2 |
| `optimality_interface` / `optimality_intrinsic` | 1.4445 / 92.784 | 1.4445430872830798 / 92.7841140024072 |
| wall time, one arm | 136.1 s | 186.59 s (interface) + 94.75 s (intrinsic) = 281.34 s |

The measured run reproduces the D-02 probe's recovered `water_z`, guard count, cost, and status to
the figures the probe reported, confirming the implementation followed the probe's mechanism exactly
(bounds override reaching both stage-3 passes, not a first-pass-only patch). Wall time is higher
than the probe's single 136.1 s figure because the probe's number was a combined estimate and the
measured run reports the two stage-3 passes separately.

Refractive arm (`n_water=1.333`, `water_z` NOT pinned, `normal_fixed=False`), measured:

- `water_z` recovered: 1.0235695472039534 m — **−7.4305 mm** from GT 1.031 m, matching its
  established offset (D-02 probe: −7.43 mm), not a new large excursion.
- `degenerate_observations_at_solution`: 0.
- `cost_interface` / `cost_intrinsic`: 3688.7971450716086 / 3680.034007917413.
- `status_interface` / `status_intrinsic`: 2 / 2.
- `optimality_interface` / `optimality_intrinsic`: 0.001146159591411948 / 0.02473573255605288.
- `solver_config.water_z_pinned_m`: `null`.

Both records: `solver_config.normal_fixed == false`.

### The `optimality_intrinsic` caveat

`optimality_intrinsic` **rises** for the pinned arm (92.7841140024072, measured) versus its unpinned
counterpart (49.65, D-02 probe's arm B) because the parameter is pinned against a ~2e-12-wide box:
`least_squares`'s first-order optimality is a projected-gradient KKT residual, and a gradient
component along a direction the box forbids moving cannot be driven to zero by definition. This is
expected numerical behavior of the pin mechanism, not a conditioning regression, and it is **not**
"fixed." The acceptance metric is the recovered `water_z` against 1.031 m — never this number and
never the guard count alone. Reason: FIX-02 alone (normal free, water_z unpinned) already zeroes the
guard count at `water_z` = 0.0120 m, 1.02 m from truth (D-02 probe arm B) — so a zero guard count is
consistent with either a correct pin or a badly wrong unpinned estimate, and cannot discriminate
between them on its own.

> **CORRECTED 2026-08-17, same day, after this summary was committed.** The caveat's *conclusion*
> holds; its *mechanism* does not. Three probes in
> `.planning/probes/2026-08-17-optimality-decomposition/` measured it directly:
>
> - The pinned `water_z` contributes **0.00%** of the reported optimality — 1.95e-11 out of
>   92.7841140024072. scipy's `trf` reports `||g·v||∞` with `v` the Coleman-Li *distance to the
>   bound the negative gradient points toward*. Pinned, that distance is ~1.8e-12, so the slot is
>   crushed toward zero rather than inflated. The paragraph above describes an unscaled projected
>   gradient, which is not what scipy reports. (The raw gradient on the slot is genuinely large,
>   9.75 — it simply never reaches the reported number.)
> - The 92.78 is **entirely the max extrinsic gradient** — extrinsics are unbounded, so `v = 1`
>   and the reported optimality *is* the raw gradient there.
> - It is **not Jacobian noise**: a central-difference Jacobian agrees to five significant figures
>   (92.7841 vs 92.7843).
> - The arm is **converged**: warm-restarting from its own solution recovers no cost (relative
>   drop 1.8e-9). The real cause is severe ill-conditioning — optimality swings 92.78 → 27.58 →
>   2.16 across restarts at effectively fixed cost, implying directional curvature ~3e8.
>
> **The acceptance metric was correct and is unaffected**: recovered `water_z` = 1.030999999999
> against ground truth 1.031. Everything else in this summary — the bound-hit table, the FIX-02
> DOF note, the E7 consequence-to-watch line — stands as written. Only this caveat's explanation
> of *why* the number is large is superseded. This requirement now tracks as **DEGEN-05** in
> Phase 24.

### FIX-02's DOF note

E1 and E7 now solve at `normal_fixed=False`, matching the production pipeline
(`CalibrationConfig.interface_normal_fixed` defaults to `False`) and every other solving experiment
(E4/E5/E6). The synthetic scenarios in this plan's scope generate the interface at exactly
`[0, 0, -1]`, so freeing `normal_fixed` here measures **the cost of having to estimate a tilt that
is not actually present** — it does **not** demonstrate recovery of a real tilt. These are distinct
claims and must not be blurred: this evidence supports only the former.

### Consequence to watch

E7's published 10-of-10 fixed-intrinsics sign test (p = 0.000977, `shared_refined`, from
`e7_focal_standoff.csv`) is a re-analysis of `interface_ablation_band.csv`, not an independent run
(D-19.5-05). FIX-02 moving E7's band values therefore propagates into `e7_focal_standoff.csv`
automatically on the next E7 run. If the sign test's p-value softens as a result, that is the
honest post-FIX-02 number, not a regression — flag it explicitly in the post-run report rather than
letting it surface as an unexplained discrepancy during re-verification.

### Ledger candidate

The D-06 bound-hit table above is the one item in this section a reviewer would plausibly want
carried into `.planning/MANUSCRIPT-FINDINGS.md`: both degenerate arms terminating *on* a bound
(2.0 ceiling, 0.01 floor) strengthens MF-18's unit-index-pinhole-identity null-direction argument
with an independent line of evidence (bound-landing rather than cost-flatness). This plan does not
transcribe it there — per `.planning/phases/23-experiment-correctness-fixes/23-CONTEXT.md`'s
2026-08-17 amendment, Phase 23 modifies experiments without running them durably (D-12 sends every
in-phase run to a git-ignored directory), so no Phase 23 entry could name a surviving artifact.
Whether to promote this table to the ledger, and when, is the user's call.

## Task Commits

1. **Task 1: FIX-01 — thread a water_z bounds override to both stage-3 passes and pin E1's
   non-refractive arm** - `fb33db4` (feat)
2. **Task 2: FIX-02 — E1 and E7 solve with the interface normal free, recorded and
   test-guarded** - `57ac430` (feat)
3. **Task 3: Verification run** — no commit (checkpoint task; output landed in the phase's
   git-ignored verification directory, per D-12). Executed by the orchestrator at commit `330f9ef`.
4. **Task 4: Record the evidence in this SUMMARY.md** - (this commit)

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
- `.gitignore` - phase's in-phase verification output directory (D-12)

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

- FIX-01 and FIX-02 are both code-complete, unit-tested, committed, and verified against a
  foreground run (Task 3) whose observed values are transcribed in `## Evidence` above.
- All four tasks of this plan are complete.
- No blockers for plans 23-02/23-03/23-04 (FIX-05, FIX-03/FIX-04, FIX-06 respectively) — per the
  phase context, all four plans in this wave are file-disjoint and were confirmed genuinely
  independent (D-13/amendment 2026-08-17).
- Per the plan's D-06/D-12 amendment, no entry was added to `.planning/MANUSCRIPT-FINDINGS.md`;
  the `### Ledger candidate` note above flags the bound-hit table for the user's own ledger pass.

---
*Phase: 23-experiment-correctness-fixes*
*Completed: 2026-08-17 (all four tasks)*

## Self-Check: PASSED

All files listed under "Files Created/Modified" confirmed present on disk; task commit hashes
(`fb33db4`, `57ac430`) confirmed present in `git log --oneline --all`. Task 3 produced no commit by
design (checkpoint task, git-ignored output). Task 4's evidence values are transcribed from the
orchestrator's reported Task 3 output, not re-derived by this agent.
