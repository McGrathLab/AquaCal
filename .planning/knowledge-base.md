# AquaCal Knowledge Base

## Table of Contents
- Architecture (1 entry)
- Optimization & Performance (2 entries)
- Coordinate Frames & Geometry (2 entries)
- Calibration Lessons (1 entry)
- Known Issues & Workarounds (6 entries)
- Debugging Recipes (0 entries)

## Architecture

### Water-Z reparameterization to break height/distance degeneracy
**Context**: Camera Z position (in extrinsics) and interface distance are mathematically degenerate — the optimizer can trade one for the other, reaching valid but nonphysical solutions where cameras appear at very different heights above the water surface.
**Insight**: A single global `water_z` parameter replaces N independent per-camera interface distances. Each camera's distance is derived as `d_i = water_z - C_z_i`. This eliminates the degeneracy by construction: moving a camera's Z also changes its interface distance, so the optimizer can't play them against each other. The reference camera has `C_z = 0` (at origin), so `water_z = d_ref`. Auxiliary cameras use a 6-param (extrinsics-only) optimization since their distance is derived from the known `water_z`.
**References**: `src/aquacal/calibration/_optim_common.py:pack_params` (line 20), `src/aquacal/calibration/interface_estimation.py:optimize_interface` (line 140), CHANGELOG entry "P.18 Replace Per-Camera Interface Distances with Global Water Surface Z".
**Added**: 2026-02-12

## Optimization & Performance

### Sparse Jacobian without LSMR: custom callable approach
**Context**: Bundle adjustment in Stages 3/4 uses `scipy.optimize.least_squares`. The obvious way to exploit Jacobian sparsity — passing `jac_sparsity` — forces the LSMR trust-region solver, which diverges on our ill-conditioned problems while the dense exact (QR) solver converges fine.
**Insight**: Use a custom `jac` callable that computes the Jacobian via `scipy.optimize._numdiff.approx_derivative` with `sparsity=(pattern, groups)` and returns `.toarray()` (dense). This gives sparse finite-difference efficiency (only `len(groups)` evaluations instead of `n_params`) with the exact TR solver's stability. `group_columns()` from `scipy.optimize._numdiff` computes optimal column groupings — e.g. 13 groups instead of 33 columns for the 3-camera test case. For large problems, a `dense_threshold` parameter falls back to returning sparse (LSMR) to avoid OOM (e.g. 13-camera, 629-frame rig would need 13.5 GiB dense).
**References**: `src/aquacal/calibration/_optim_common.py:make_sparse_jacobian_func` (line 498), `group_columns` and `approx_derivative` imported from `scipy.optimize._numdiff` (line 10). `tr_solver='exact'` is incompatible with `jac_sparsity` parameter — see scipy docs.
**Added**: 2026-02-12

### Block-sparse Jacobian structure in bundle adjustment
**Context**: The Stage 3/4 cost function has natural sparsity: each reprojection residual depends only on one camera's extrinsics, the global water_z, and one board pose. Understanding this structure is essential for anyone modifying the sparsity pattern or adding new parameter types.
**Insight**: The Jacobian has a block-sparse structure where each row (residual) touches at most ~14 columns: 6 extrinsic params for one camera + 1 water_z + 6 board pose params (+ optionally 4 intrinsic params). Column grouping exploits this — independent columns can be finite-differenced simultaneously. This reduces function evaluations by 10-15x (e.g. ~50 groups instead of ~685 columns for a 13-camera rig). Adding a new parameter type requires updating `build_jacobian_sparsity()` to mark which residuals depend on it.
**References**: `src/aquacal/calibration/_optim_common.py:build_jacobian_sparsity` (line 200), `make_sparse_jacobian_func` (line 498). See also "Sparse Jacobian without LSMR" entry above for the solver-side details.
**Added**: 2026-02-12

## Coordinate Frames & Geometry

### `interface_distance` is a Z-coordinate, not a physical gap
**Context**: The name `interface_distance` suggests a camera-to-water distance, but all downstream code treats it as the Z-coordinate of the water surface.
**Insight**: Functions like Newton projection, Brent projection, and `get_interface_point` compute the camera-to-water gap internally as `h_c = interface_distance - C_z`. So `interface_distance` must be the absolute water surface Z, not the per-camera gap. When deriving from the global `water_z` parameter, the correct assignment is `interface_distance = water_z` for all cameras. Deriving it as `water_z - C_z` double-counts `C_z` because downstream code subtracts it again. This was the root cause of bug B.6.
**References**: `src/aquacal/calibration/_optim_common.py:unpack_params` (line 165), `src/aquacal/core/refractive_geometry.py` (line ~346), `src/aquacal/core/interface_model.py` (line ~81), `tasks/archive/b6_debug_report.md`.
**Added**: 2026-02-12

### A "realism" jitter applied to `water_z` gives every camera its own water surface
**Context**: `generate_camera_array`'s `height_variation` parameter is documented as "Std dev of per-camera **height** variation", but was applied to `water_z` — the world-frame Z of the water *surface* — while leaving every camera at `C_z = 0`. The synthetic ground truth therefore modelled **one water plane per camera**: a single board corner was refracted through a different surface by each camera. The method, and the paper, assume a single flat interface.
**Insight**: This is the same misconception that produced bug B.6 (see the entry above), in the opposite direction. B.6 *derived* `interface_distance` as `water_z - C_z`, double-counting the gap; this one *jitters* `water_z` as though it were a per-camera gap. Because every camera sat at `C_z = 0`, `h_c = water_z - C_z` makes "jitter the plane" and "jitter the camera height" numerically identical — so the wrong variable was moved and nothing looked wrong for months. **Whenever a per-camera quantity is perturbed, ask whether it is a property of the camera or of the shared scene. `water_z` is the scene.** Measured impact before the fix: mean **1.42 px**, max **6.33 px** over 31,680 corner observations — *larger than the ~0.4-0.9 px reprojection RMS the experiments were reporting*. It also had a second-order symptom that cost a whole misdirected phase: `max(water_zs)` became seed-dependent, so a clearance floor frozen at one seed was wrong at ~94% of others, which presented as "E4/E6 are seed-locked to 42". The correct fix is `C_z = -delta` with `water_z = height_above_water` shared, which preserves each camera's `h_c` exactly. Do *not* simply set `height_variation = 0` — that removes the `C_z <-> water_z` degeneracy E7 exists to probe.
**References**: `src/aquacal/datasets/synthetic.py` (line ~259), `src/aquacal/core/interface_model.py` (lines 8-22, the docstring stating the value is the surface Z and should be shared), `.planning/phases/19.4-grid-family-clearance-floor-fix/19.4-RESCOPE-PROPOSAL.md`.
**Added**: 2026-08-04

### Top-down camera rig plot CW/CCW flip from Y-axis convention
**Context**: The world frame is defined by the reference camera, where Y = camera-Y-down. Plotting with standard Y-up convention mirrors CW/CCW camera ordering in the top-down view.
**Insight**: Call `ax.invert_yaxis()` on the top-down subplot to match the camera Y-down convention. Z-negation and `invert_zaxis()` do NOT affect CW/CCW — they only change the vertical display direction. The CW/CCW flip is purely a Y-axis mismatch. This was the root cause of bug B.7.
**References**: `src/aquacal/validation/diagnostics.py:plot_camera_rig` (line 547), `tasks/archive/b7_report.md`.
**Added**: 2026-02-12

## Calibration Lessons

### water_z is unobservable in non-refractive mode (n_air == n_water)
**Context**: When running calibration with n_air=n_water=1.0 as a comparison baseline, water_z moves significantly (1.0 -> 0.35 -> 0.47) despite having zero analytical gradient.
**Insight**: With equal refractive indices, the projected pixel is exactly independent of water_z (Newton-Raphson converges in 0 iterations to the pinhole solution; the interface point lies on the C-to-Q ray, so perspective division cancels). Stage 3 movement is caused by the `h_q <= 0` boundary penalty driving water_z below all board corners. Stage 4 drift is accumulated numerical noise in a flat cost valley. The final water_z value is arbitrary and meaningless; all other parameters (extrinsics, intrinsics, board poses) are unaffected.
**References**: `_refractive_project_newton` line 357 (h_q guard), `compute_residuals` (invalid-projection handling), `dev/tasks/water_z_nonrefractive_report.md`.
**Added**: 2026-02-13
**UPDATED 2026-07-30**: the stated mechanism no longer exists. The flat 100 px
penalty this entry blames for "driving water_z below all board corners" was
removed — invalid projections are now continued with the pinhole extension, which
is differentiable, so that spurious driver is gone. The CONCLUSION (water_z is
analytically unobservable when n_air == n_water, and its final value is
meaningless) still holds and is independent of the penalty. The explanation for
the observed *movement* has NOT been re-measured since the change and should be
re-derived before being cited. See `.planning/debug/stage3-diverges-new-geometry.md`.

### Fronto-parallel board views leave focal length degenerate
**Context**: One camera on a 13-camera rig solved 15 cm out of the rig plane with 2.9 px reprojection error, while its intrinsics passed every `validate_intrinsics()` check. Its fx was 1367.9 against ~1578 for eleven identical-lens peers.
**Insight**: Focal length is recovered from perspective foreshortening. When board views are near fronto-parallel, the projection is nearly a pure scaling and fx becomes degenerate with board distance -- they can be scaled together with almost no change in reprojection error. The optimizer settles anywhere along that valley, producing a *self-consistent* calibration (low RMS, sane distortion, centered principal point) whose fx is badly wrong. Downstream, PnP distance scales linearly with fx, so a 13% fx deficit displaced the camera ~15 cm toward the water. `validate_intrinsics()` cannot detect this -- all of its checks pass. `validate_view_diversity()` (added `16fd84f`) inspects the input geometry instead and warns when 90th-percentile board tilt < 15 deg. Measured separation on the real rig: bad camera 7.2 deg, correct cameras 19.6-29.7 deg. A cross-camera `expected_fx` check was rejected as a fix: the library must support arbitrary mixed camera sets and cannot assume prior knowledge of shared focal lengths.
**References**: `src/aquacal/calibration/intrinsics.py:validate_view_diversity`, `.planning/debug/callibration071626-tilt-high-reproj.md`.
**Added**: 2026-07-20

### cv2.calibrateCamera needs an explicit initial guess
**Context**: One camera calibrated to fx=3844 against ~1580 for its peers, with distortion k2=-10.9, k3=+32.7 and Stage 1 RMS 2.87 px vs 0.37-0.61 px. Its board-view data was verified to be as good as a normal camera's.
**Insight**: Without `CALIB_USE_INTRINSIC_GUESS`, OpenCV auto-initializes K from a homography/DLT decomposition that can be badly ill-conditioned for some board-pose distributions, and the nonlinear refinement never escapes the resulting basin. A richer distortion model does not help (rational 8-coeff produced fx=3971). Seeding `fx = fy = max(image_width, image_height)` with the principal point at the image center fixes it and reproduces the unguided result to 6+ significant figures on well-behaved cameras, so it is a safe no-op where calibration already worked. A bad K here poisons Stage 2 PnP directly -- the camera was already misplaced in `calibration_initial.json`, before any joint optimization -- and Stage 3/4 does not self-correct, because the wrong intrinsics and wrong pose are locally mutually consistent.
**References**: `src/aquacal/calibration/intrinsics.py:calibrate_intrinsics_single`, `.planning/debug/callibration071626-tilt-high-reproj.md`.
**Added**: 2026-07-20

## Known Issues & Workarounds

### A subagent executor that backgrounds a long test run will stall and never finish
**Context**: Phase 19.3 plan 07's executor committed its two code tasks correctly, then launched
the test suite as a background job and returned before it completed — leaving no SUMMARY.md.
Resumed with explicit "run everything in the foreground" instructions, it did exactly the same
thing again: ~78 min and ~300k tokens on the second attempt with zero progress. The orchestrator
took the task over and finished it in one foreground run. Phase 19.2 hit the same class of
failure repeatedly with production sweeps.
**Insight**: The agent's *return text* is not evidence of what happened. It read as though work
were still legitimately in flight ("I'll wait for the notification"), which is indistinguishable
from a stall. **Always verify a subagent's claim against the filesystem and git before acting on
it** — `git log --oneline HEAD..<worktree-branch>` for committed work, and an `ls` for the
expected SUMMARY.md. Doing that is what revealed the plan was two-thirds done rather than failed,
so resuming/taking over was correct and re-running the whole plan would have been waste.
**How to apply**:
- Tell executors explicitly: run long commands **synchronously**; never launch a background job
  and return waiting on it.
- Tell them what *not* to run — plan 08 writes a queue script but must not execute the ~9 h
  sweep; without that sentence an executor may try, and then stall for hours.
- ~~Split a ~10 min suite into `-m "not slow"` then `-m "slow"`~~ — **superseded 2026-08-04.**
  This no longer works: `-m "not slow"` alone is now ~26 min, itself 2.6x over the ceiling.
- If an executor stalls twice on the same step, stop resuming it and finish that step in the
  orchestrator. Note in the SUMMARY who measured what, so later readers know which numbers came
  from the executor and which from the orchestrator.
**References**: `.planning/phases/19.3-scenario-geometry-and-convergence/19.3-07-SUMMARY.md`
(its header records the takeover), `19.3-ORCHESTRATOR-NOTES.md`.
**Added**: 2026-08-02

#### ROOT CAUSE, found 2026-08-04 (phase 19.4) — and the policy that removes it

**The mechanism is a harness message that is correct for the orchestrator and fatal for a
subagent.** When a Bash call exceeds the tool's ceiling it is auto-backgrounded, and the tool
returns *"You will be notified when it completes."* For the top-level agent that is true. For a
subagent, **ending its turn IS task completion** — there is no one left to deliver the
notification to. The tool therefore instructs precisely the behaviour that kills the agent, which
is why hardening the prompt kept failing: the prompt said "never do X" while the tool said "X is
how this works." In phase 19.4, five of six executors stalled, including ones given an explicit
anti-stall section and a literal `until grep ...; do sleep 10; done` poll recipe.

**Why it started in this milestone.** The suite crossed the ceiling by a wide margin, and only
recently. Measured in phase 19.4: unfiltered post-merge runs of **56 min** and **88 min**; a
plan's own suite run 47 min; `-m "not slow"` ~26 min. The ceiling is 600 s. Test *count* is not
the cause (1168 → 1283 → 1411 across 19.2/19.3/19.4); test *content* is — phases 16-19.4 added
tests that run real optimizations and full synthetic calibrations (`test_discard_accounting.py`
alone is ~127 s for 13 tests). Before this milestone most runs fit under the ceiling, so nobody
hit the trap.

**Policy (user decision, 2026-08-04): the full suite belongs to the post-merge gate, not to
executors.**
- Executor plans get a **targeted** test command — the files their own plan touches — which
  finishes inside the ceiling.
- The **orchestrator** owns the one unfiltered `pytest tests/` run, in the post-merge gate, where
  auto-backgrounding is harmless because the notification actually arrives.
- Executor prompts should say plainly: *"Do NOT run the full suite; the orchestrator runs it at
  the post-merge gate."* Removing the trap beats asking agents to resist it.
- This also puts the integration run where it belongs — after merge, where cross-plan breakage is
  visible. A per-executor suite run cannot see the other plans in its own wave anyway. Phase
  19.4's wave-2 gate proved the point: plans 04 and 06 each passed alone and contradicted each
  other once merged.

**Still binding regardless:** never trust a subagent's return text. Verify against
`git log --oneline <base>..<worktree-branch>`, `git -C <worktree> status --porcelain` for
uncommitted work at risk, and an `ls` for the expected SUMMARY.md. In 19.4 that discipline caught
every one of the five stalls with zero work lost — including plan 05, whose completed Task 2
existed only as uncommitted files that would have died with its worktree.
**Added**: 2026-08-04

### A targeted test file can also exceed the 600 s ceiling — naming files is not a safe instruction

**Context**: The existing rule (§ "A subagent executor that backgrounds a long test run will stall")
says never give an executor the full suite, and instead give it a *targeted* command covering only
the files its plan touches. In quick task 260807-dcv the executor was told exactly that — "run the
files you touched" — and stalled anyway, with the same signature: it backgrounded the run and ended
its turn.

**Insight**: The instruction was the defect, not the agent. `tests/unit/test_e1_band_mode.py` runs
real band solves; the same command later auto-backgrounded on the *orchestrator* and took **28
minutes**. "The files your plan touches" is not a proxy for "fast": an experiment repo has unit
test files that each drive a full calibration. Name the *specific fast tests*, or state plainly
that the orchestrator runs the tests and the executor runs none. Before dispatching, it is worth
checking whether any named file is marked `slow` or drives a solve.

The executor's work was intact — all six files were correctly edited — so the recovery is to verify
against git and take over the remaining verify/commit steps, not to re-dispatch.

**References**: `.planning/quick/260807-dcv-e1-e7-band-provenance-emit-z-rmse-column/`, CLAUDE.md
§ "Never let a subagent background a long run and return".
**Added**: 2026-08-07

### A gate FAIL that everyone has learned to expect stops being read

**Context**: `gate4_band` FAILed for E1 and E7 from phase 19.4 onward. It was documented as
"recording-only, tracked", carried through 19.4's closure and all of 19.5, and re-stated as benign
in several handoffs. In phase 19.5 plan 11 it turned out that E1's instance was flagging something
real: the manuscript's headline `~135x` ratio had **no committed artifact containing the quantity
it is computed from**. The band was regenerable only from a gitignored sweep directory, and MF-08
positively asserted the wrong file as its source.

**Insight**: The two FAILs looked identical and were not. E7's really was benign — its band CSV
carries its claim quantity and reproduces MF-05 unaided. E1's was a live provenance hole on the
paper's most prominent number. A shared label ("recording-only") had merged them, and the merge
survived two phases because nobody re-derived *why* each one failed.

This is the same shape as the phase's other three integration defects — the unregistered CSVs, the
CI-lane bloat, the E5/E6 fixture asymmetry — each locally correct, each invisible to its own
executor, each surfacing only at an integration gate. What is missing in all four is an owner for
the cross-plan question. The additional lesson here is narrower and sharper: **a tolerated failure
needs a re-derivation, not an annotation.** If a gate is expected to fail, the expectation should
be re-checked at each phase boundary against what the gate actually asserts, or it should be
converted to an explicit N/A that states the premise it is waiving (as `ARCHIVES_PRESENT` was in
19.5).

**References**: `.planning/MANUSCRIPT-FINDINGS.md` MF-16; `experiments/check_rerun_gates.py`
`check_band_csv`; phase 19.5 plan 10 SUMMARY.
**Added**: 2026-08-07

### A mean-absolute error metric can hide whether two errors add or cancel

**Context**: E6's `layout/line` configuration reported an 18.9 mm `water_z_error_mm_mean` at one
seed of six — 7.5x the worst value of any other configuration. Its `z_position_error_mm_mean` was
-18.5 mm, and the two tracked each other across seeds at r = +0.997. It was not possible to tell
from the committed artifacts whether the water surface and the cameras had moved *together* (a
datum shift, physically harmless) or *apart* (a real standoff failure), because
`water_z_error_mm_mean` is a mean of absolute values and destroys the sign.

**Insight**: Re-solving the configuration and reading signed values showed both errors were
negative and nearly equal: the physical camera-to-surface gap `h_c = water_z - C_z` was off by only
0.36 mm in the mean, against an 18.85 mm world-frame surface error. Roughly 80% of the apparent
camera-Z error is a global datum offset. The discriminator is a same-seed comparison against the
grid baseline: gauge correction removes **79.5%** of the line layout's camera-Z error magnitude and
only **4.6%** of the grid's — a collinear array admits the datum shift almost freely, a grid array
barely at all. The residual after removing it is real but an order of magnitude smaller (~2.4 mm
against grid's ~0.6 mm). The library already has
`compute_per_camera_errors(..., gauge_correct_z=True)` for exactly this, documented as removing
"an artifact of choosing where Z=0 is, not a real geometric error". **E6 does not pass it**, so its
Z errors are reported uncorrected.

Two rules follow. Report a **signed** error alongside any mean-absolute one when the quantity can
trade off against another parameter. And for a gauge-dependent coordinate, also report the
gauge-invariant physical quantity — here `h_c`, which `interface_distance` is explicitly *not*
(see § "`interface_distance` is a Z-coordinate, not a physical gap"). Report both: `h_c` alone
would hide a rig that slid bodily through the world frame.

**References**: `.planning/MANUSCRIPT-FINDINGS.md` MF-12;
`src/aquacal/datasets/pipelines.py:compute_per_camera_errors`;
`experiments/e6_generalization_sweep.py:compute_water_z_error_mm_mean`.
**Added**: 2026-08-07

### Neither CLAUDE.md nor .claude/ is tracked in this repo
**Context**: Attempted to record the pitfall above in `.claude/rules/`, believing it was tracked.
**Insight**: `.gitignore:214` ignores `.claude/` and `:216` ignores `CLAUDE.md`. `git ls-files
.claude/` returns **zero** — the rules files are local-only, not committed-but-ignored. Anything
written to either location persists only on that one machine and is invisible to collaborators
and to a fresh clone. Durable, shareable project lessons belong in `.planning/knowledge-base.md`
(this file), which CLAUDE.md itself designates as the home for accumulated gotchas.
**Added**: 2026-08-02

### A stale editable install stamps the wrong version onto every artifact it produces
**Context**: On 2026-08-13 `pyproject.toml` read **2.0.1** (bumped 2026-08-11, `2ba0f8e`) while the
`AquaCal` env still carried `aquacal-1.8.0.dist-info` and an `__editable__.aquacal-1.8.0.pth`.
`aquacal.__version__` reported 1.8.0 and `aquacal.__file__` pointed at the working tree — so 2.0.1
code would have been recorded as 1.8.0 in every `benchmark.json` and every provenance sidecar it
wrote. Nothing was corrupted only because no artifact had been produced since the bump.
**Insight**: `src/aquacal/__init__.py` and `capture_environment()` both resolve the version through
`importlib.metadata.version("aquacal")`, i.e. *installed distribution metadata*. An editable
install writes that metadata once, at `pip install -e .` time, and editing `pyproject.toml` never
refreshes it; meanwhile the `.pth` keeps resolving imports to the live tree. The two diverge
**silently** — no warning, no exception, just a confident and wrong provenance record. This is the
same genre as "commit nothing during a production run": a cheap precondition whose violation is
invisible in the output. It matters because `aquacal_version` is load-bearing evidence — MF-19
traced §3's real-rig numbers by reading it, and MF-20 is stated as a 1.8.0 -> 2.0.1 comparison.
**How to apply**: run `pip install -e . --no-deps` immediately after any `pyproject.toml` version
bump, and before any production run in a source checkout; confirm with
`python -c "import aquacal; print(aquacal.__version__)"`. `experiments/prelaunch_gate.sh`'s
`ENV_VERSION_MATCH` check (check 2) now asserts installed == declared and aborts the queue if not,
and `capture_environment()` records `aquacal_version_declared` beside `aquacal_version` so an
escaped case is diagnosable from the artifact alone. Do **not** "fix" this by hardcoding
`__version__` — that trades a detectable mismatch for a silent one.
**References**: `experiments/prelaunch_gate.sh` (ENV_VERSION_MATCH),
`src/aquacal/io/benchmark.py:capture_environment`, `experiments/README.md` §7,
`.planning/todos/done/2026-08-13-editable-install-metadata-can-mislabel-artifact-provenance.md`.
**Added**: 2026-08-13

### A verification gate that cannot pass is worse than no gate (D-10)
**Context**: E4's `--check` reported 9 of 10 cells mismatched on the committed tree, on exactly two
columns (`exit_code`, `status_reason`), while all 33 other metric columns reproduced to 1e-6. Both
failures were structural, not regressions: `_run_check` hardcodes `"exit_code": None` because no
subprocess runs under `--check` (the committed CSV holds the real run's `0.0`), and
`status_reason` round-trips an empty string through CSV as `NaN`. Neither can ever clear by
construction. This is the same shape as another gate observed to pass while parsing nothing
against a `CONTEXT.md` holding 21 trackable decisions — a decision-coverage gate reporting 0
trackable decisions and reading as green.
**Insight**: A verification gate that cannot pass is worse than no gate at all — a gate that has
only ever been observed in one state (always red, or always green) has not been validated — it has not been shown capable of the *other* state, so nobody can tell a
genuine failure/pass from the gate's own structural inability to do otherwise. Both instances here
trained a reader to expect the gate's output regardless of what actually happened underneath: an
always-red `--check` trains "red is normal, don't look closer"; an always-green decision-coverage
gate trains "green means covered" when it means "parsed nothing." **Before trusting a gate,
establish that it can fail and that it can pass** — with a concrete case of each, not by reading
the gate's own source and assuming. FIX-05 fixed the always-red case by excluding exactly the two
named, measurement-backed columns (`experiments/e4_benchmark_grid.py:CHECK_EXCLUDED_COLUMNS`) and
printing what was skipped on every run, so the exclusion itself stays visible rather than becoming
a second thing nobody re-derives.
**How to apply**: when a check is asserted "passing" or "failing" as a matter of course, ask what
would make it flip. If the answer requires code you have not written or a state you have never
produced, the gate is unvalidated, not green. A wider audit of this project's other gates
(`experiments/check_rerun_gates.py`) was considered here and deliberately not taken — worth
revisiting at the Phase 27 freeze, the last cheap moment before Phase 29 depends on those gates.
**References**: `.planning/phases/23-experiment-correctness-fixes/23-02-SUMMARY.md`,
`.planning/probes/2026-08-17-phase-23-recon/e4_check_detail.py`,
`experiments/e4_benchmark_grid.py:CHECK_EXCLUDED_COLUMNS`.
**Added**: 2026-08-17

## Debugging Recipes

### Offline Stage 1 analysis must match the pipeline's frame_step
**Context**: An offline probe reproducing Stage 1 intrinsic calibration produced fx values (841, 1300) that did not match the pipeline's (1368, 1578) for the same cameras and videos.
**Insight**: `_select_calibration_frames` caps at `max_frames` (default 100). At `frame_step=1` a video yields ~900-2200 candidate views and the probe picks 100 *by coverage*; at the config's `frame_step=30` it yields only ~30-77 candidates, all of which are used. These are entirely different frame sets, so fx differs materially. Re-run at the pipeline's frame_step, the probe reproduced its fx exactly (1367.9 / 1577.6 / 1575.9 / 1574.1). Always pass the config's `detection.frame_step` when analyzing Stage 1 behaviour offline. A corollary worth noting: fx that shifts by ~20% purely from a different frame subset is itself evidence that fx is weakly constrained for that camera.
**References**: `src/aquacal/calibration/intrinsics.py:_select_calibration_frames`, `.planning/debug/callibration071626-tilt-high-reproj.md`.
**Added**: 2026-07-20
