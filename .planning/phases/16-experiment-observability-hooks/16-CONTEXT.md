# Phase 16: Experiment Observability Hooks - Context

**Gathered:** 2026-07-23
**Status:** Ready for planning

<domain>
## Phase Boundary

Make optimizer internals observable and reproducible for the WP5/WP6 experiments:
per-stage intermediate calibrations (HOOK-01), an opt-in per-iteration optimization trace
(HOOK-02), conditioning and parameter-correlation diagnostics (HOOK-03), standalone
held-out evaluation (HOOK-04), a synthetic-generator audit against the WP5 sweep list
(HOOK-05), and end-to-end deterministic seeding (HOOK-06).

**Hard constraint: zero change to numerical behavior.** Everything in this phase is
visibility and persistence. The one deliberate exception is the HOOK-04 refactor, which
moves existing held-out evaluation behind a shared function — guarded by a regression test
asserting pipeline output is unchanged.

This phase is the first half of the milestone's only true experiment blocker. Per-camera
interface mode is Phase 17 and depends on HOOK-03.

</domain>

<decisions>
## Implementation Decisions

### How hooks get switched on

- **Flat config keys** on `CalibrationConfig`, e.g. `save_optimization_trace`,
  `save_conditioning`, `save_stage_calibrations`. Matches the existing
  `save_detailed_residuals` precedent exactly. No nested `diagnostics:` sub-dataclass —
  the config is flat today and stays flat.
- **Per-hook switches, no master flag.** Costs differ by orders of magnitude: stage dumps
  are nearly free, the trace is cheap, conditioning needs an SVD and a dense correlation
  matrix over 673–727 parameters. Wanting a cheap trace must not drag in an expensive SVD.
- **Config-only — no CLI flags.** The config file is the reproducibility record, and
  BENCH-04 (Phase 19) records "solver configuration in force" from it. CLI overrides would
  create a second source of truth for what `benchmark.json` claims was active.
- **Defaults: stage dumps ON, trace and conditioning OFF.** HOOK-01 extends
  `calibration_initial.json`, which `pipeline.py:795` already writes unconditionally, so
  dumping the remaining stages matches existing behavior at the cost of a few small JSON
  files. Everything else is strictly opt-in.

### Artifact layout and format

- **New artifacts land in `output_dir/internals/`.** Not `diagnostics/` — `output_dir`
  already contains a `diagnostics.json` file (`diagnostics.py:894`) holding the
  user-facing diagnostics report, and a directory of the same name beside it would force
  every doc sentence and error message to disambiguate. `internals/` also signals "not
  part of normal output" to a user browsing the directory.
- **Trace format: CSV.** The trace is many rows × few scalar columns (iteration, cost,
  step norm, optimality, interface parameters) — natively tabular. Matches the existing
  `spatial_measurements.csv` / `depth_errors.csv` precedent, loads in pandas with no
  parsing, diffs readably.
- **Conditioning format: split.** Condition number and singular-value spectrum go to JSON
  (human-readable, greppable, easy to quote in the paper); the correlation matrix goes to
  `.npz` (compact, exact float round-trip, one numpy call to load). A 727×727 matrix
  serialized as JSON is ~5–10 MB of text and loses precision.
- **Repeat runs overwrite, but warn when clobbering.** Matches `calibration.json` today.
  A sweep gives each grid point its own `output_dir`, so accumulation solves a problem the
  runner does not have — but the warning guards against silently mixing a fresh trace with
  a stale conditioning file from a different config.

### Trace scope (HOOK-02)

- **All bundle-adjustment stages, one file each.** Stage 3, the re-run after outlier
  rejection, and the intrinsic pass each get their own trace file. R4.3 asks whether the
  joint optimization converges reliably, and the post-rejection re-run is part of that
  story. Merging stages into one file makes the iteration axis meaningless, since
  numbering restarts per stage.

### Conditioning diagnostics (HOOK-03)

- **Full singular-value spectrum AND the full parameter correlation matrix**, not just
  the camera-height ↔ water_z block. User accepted the memory risk explicitly.
  ⚠️ **Research must verify headroom** — the 13-camera rig already peaks at ~3.6 GB from
  the dense `.toarray()` Jacobian, and a dense 727×727 correlation matrix plus SVD
  workspace lands on top of that. If it does not fit, raise it rather than silently
  narrowing scope.
- **Computed for whichever stage produced the final reported result** — Stage 3, or the
  intrinsic pass when enabled. One matrix per run, unambiguous provenance.
- **Reuse `result.jac` from `least_squares`** rather than recomputing. scipy returns the
  Jacobian at the solution and the codebase already materializes it dense via `.toarray()`,
  so this is free and is exactly the solution point. Research should confirm `result.jac`
  is populated and trustworthy on the custom-`jac`-callable path before this is relied on.
- **Pre-check the allocation and refuse with a clear message** naming the estimated size
  and the config key to disable. Do NOT silently degrade to a narrower metric — WP6 would
  then quietly receive a different quantity than intended, which is precisely the
  paper/code divergence this milestone exists to close.

### API surface

- **`evaluate_calibration` (HOOK-04) becomes a top-level `aquacal.` export**, joining the
  deliberately small 15-name public API. It is broadly useful beyond this milestone and
  the paper can point a reviewer straight at it.
- **Conditioning diagnostics live in `aquacal.validation.*`**, alongside the existing
  `compute_reprojection_errors` and `compute_3d_distance_errors`. Documented and
  importable, without a semver promise on a niche experiment tool whose return shape has
  not yet been exercised by WP6.
- **Held-out evaluation reports the same structure the pipeline already produces** for
  held-out frames. Standalone and pipeline-internal results must be directly comparable,
  because the paper quotes both. No new result type to document.
- **The pipeline is refactored to call the new standalone function** — one code path,
  guarded by a regression test asserting pipeline output is unchanged. Two implementations
  of "held-out evaluation" would drift, and the divergence would be invisible and wrong.

### No assumption-override parameter needed

WP4's "evaluate under perturbed assumptions" is encoded in the **held-out set** — ground
truth generated at a different refractive index — not in the calibration being scored. So
`evaluate_calibration` takes a calibration and a held-out set; it needs no `n_water`
override parameter.

### Claude's Discretion

- **Stability marking** for the two new entry points (stable vs. experimental) — decide
  once return shapes are concrete.
- Exact config key names, beyond following the `save_*` prefix convention.
- Structure of the stage-dump filenames within `internals/`.
- Whether the pre-check estimates memory analytically or probes it.

</decisions>

<specifics>
## Specific Ideas

- Follow `save_detailed_residuals` as the model for every new config key — same prefix,
  same flat placement, same docstring style.
- Follow `spatial_measurements.csv` as the model for the trace file.
- `internals/` should read as "optimizer guts exposed for inspection," clearly distinct
  from the user-facing `diagnostics.json` report.

## Scoping notes from pre-discussion code review

Two requirements are likely **already mostly satisfied** — research should audit rather
than assume work is needed:

- **HOOK-06 (seeding):** `seed: int = 42` with `np.random.default_rng(seed)` is already
  threaded through every synthetic generator (`synthetic.py:129,299,347,404,461`), and
  `pipeline.py:462` seeds frame shuffling with `random.Random(seed)`. The likely real gap
  is whether the seed is **recorded in outputs**, not whether it is accepted.
- **HOOK-05 (generator knobs):** `SyntheticScenario` already carries ground-truth
  `board_poses` and `water_zs`, and `generate_camera_array` genuinely implements the ring
  layout (`synthetic.py:168`), not merely accepts it. The worklist predicted this may turn
  up nothing. Confirm independently: refractive-index sweepability, and whether
  tank-scale / working-distance are controllable independently of each other.

</specifics>

<deferred>
## Deferred Ideas

- **Reducing peak memory** (dense `.toarray()` Jacobian, ~3.6 GB) — recorded as PERF-01 in
  REQUIREMENTS.md Future. This phase may surface a sharper number for it via the
  conditioning pre-check, but must not attempt the fix.
- **CLI exposure of the diagnostics hooks** — rejected for this phase to keep one source of
  truth for `benchmark.json`. Revisit only if experiment scripts turn out to drive the
  pipeline through the CLI rather than through Python.

</deferred>

---

*Phase: 16-experiment-observability-hooks*
*Context gathered: 2026-07-23*
