# Phase 24: Degeneracy Instrumentation - Context

**Gathered:** 2026-08-17
**Status:** Ready for planning

<domain>
## Phase Boundary

The library's own gate quantity — `degenerate_observations_at_solution` — becomes readable off
the artifacts a reader would actually check, split finely enough to answer the degeneracy question
without another run, and its warning stops serving two opposite situations with one text.

- **DEGEN-01** — the counter reaches the production `benchmark.json`, and E1/E5/E7 persist it
  (E6's band already does — all 102 rows)
- **DEGEN-02** — the counter is split by failure kind **and** by stage, with a recorded denominator
- **DEGEN-03** — the warning is narrowed to the cases it applies to, with a corrected cause list
- **DEGEN-05** — each stage's reported `optimality` is accompanied by a per-parameter-block
  decomposition

  > **Added to this context 2026-08-17, after the session that wrote it.** DEGEN-05 was opened at
  > 11:58 and this context was captured at 12:52, but the discuss session had already loaded the
  > roadmap — so the requirement is absent below and the phase looks like a three-requirement
  > phase. `ROADMAP.md` § Phase 24 lists **DEGEN-01, 02, 03, 05** and carries a fifth success
  > criterion. Plan for four.
  >
  > *What it is:* `optimality` is a single scalar that mixes three Coleman-Li scaling regimes —
  > `v = 1` for unbounded extrinsics and board poses, `v ≈ 700` for wide-bounded intrinsics,
  > `v ≈ 2e-12` for a pinned slot — so it is **not a like-for-like maximum across blocks**. The
  > decomposition is computed in `_optim_common.py`, which already owns the layout via
  > `build_structural_column_groups` (it carries a dedicated `water_z` group slot); computing it
  > in `experiments/` would duplicate that layout, the exact drift that function's docstring
  > exists to prevent. E1 records it beside the existing `stages.*.optimality`, the same path
  > `degenerate_observations_at_solution` takes — so it shares D-11's plumbing rather than adding
  > a new one.
  >
  > *It fits D-16, not competes with it.* Both are solve-level `SolverDiagnostics` fields keyed by
  > parameter, both reach `benchmark.json` through the existing diagnostics path, and both want
  > `build_parameter_labels`. Implement them together.
  >
  > *Evidence:* `.planning/probes/2026-08-17-optimality-decomposition/FINDINGS.md` (three probes).
  > Note what is **already settled** and must not be re-litigated during planning: the pinned
  > `water_z` contributes 0.00% of the reported optimality (the Phase 23 documents' mechanism is
  > wrong), FD Jacobian noise is **falsified** as the cause (a central-difference Jacobian agrees
  > to five significant figures), and E1's non-refractive baseline **is converged** (warm restarts
  > recover no cost). The residual finding is genuine severe ill-conditioning, curvature ~3e8.

**Not this phase:** classifying the production rig's 198 (DEGEN-04, Phase 25); E1's `noise_std`
axis (BAND-01, Phase 25); the suite driver and the `--check` contract (Phase 26); any run of the
full suite (Phase 28); the real-rig degeneracy *gate scope* policy decision (deferred, and it
cannot be made until DEGEN-04 reports).

**Locked by the todos, not re-decided here:**
- The merged key is never dropped or renamed — the production gate, the re-run gates and the
  manuscript ledger all read it.
- The synthetic gate stays exactly `count > 0 → degenerate`. **No threshold, no tolerance.**
- **Beyond-critical-angle obliquity must NOT be added to any cause list.** It was refuted
  2026-08-15: the projection path has no TIR check (`refract_ray` has zero callers in `src/`),
  and `realistic` projects cleanly at chord incidences to 61.5°, past the 48.61° critical angle.
- The projection maths is not touched. The pinhole continuation is correct; the bookkeeping and
  the label around it are not.

  > **Clarified 2026-08-17 (D-06 revision).** `core/refractive_geometry.py` IS now edited — but for
  > bookkeeping only: an opt-in, `None`-defaulted reason array written at four existing failure
  > branches, all outside the Newton loop. No arithmetic, no termination rule, no clip, and no
  > return-type change. "The projection maths is not touched" stays literally true, and is the
  > property D-18 asserts.
- No plan writes `.planning/MANUSCRIPT-FINDINGS.md` (Phase 23's 2026-08-17 amendment). Evidence
  goes in each plan's own `SUMMARY.md` under `## Evidence`.

</domain>

<decisions>
## Implementation Decisions

### Counter schema — how the split is represented

- **D-01: flat enumerated keys.** The kind × stage split is expressed as flat entries in
  `DISCARD_KEYS`, e.g. `degenerate_observations_extended__stage3_interface_optimization`. The
  merged key `degenerate_observations_at_solution` is retained as their sum.

  *Why:* `DISCARD_KEYS` (`_observability.py:61-90`) is a closed tuple and
  `check_discard_invariants` reports `undeclared counter keys` as a violation. Flat keys keep that
  machinery working untouched, and keep `check_rerun_gates.py`'s three read shapes valid.

  *Rejected — nested detail sub-dict:* would need a carve-out in both the closed-vocabulary check
  and its int-valued assumption. *Rejected — per-stage dicts at the source:* fixes the root cause
  (`pipeline.py:766` threads one dict to six sites with no reset) but rewires how every `pnp_*`
  counter accumulates — the widest diff of the three, in a file Phase 29's E2 sanity control is
  watching.

- **D-02: the stage label is an explicit kwarg supplied by the caller.** `optimize_interface` and
  `joint_refinement` gain a `discard_stage: str` argument.

  *Why it cannot be derived:* `joint_refinement` bumps under **two different stage identities** —
  Stage 3 joint (`pipelines.py:159`) and the intrinsic pass (`:192`) are the same function. The
  module cannot tell you which it is.

  *Rejected — reuse `OptimizerObserver.stage`:* it already carries exactly this vocabulary and is
  already threaded to both sites, but the observer is opt-in and `None` on an ordinary run, so the
  stage split would silently collapse for every production run the counter exists for.
  *Rejected — infer from `refine_intrinsics`:* correct today, silently wrong the first time a stage
  or flag combination shifts.

- **D-03: an absent stage label lands in a declared `unattributed` bucket; an unrecognized string
  raises.** Absent is a legitimate call pattern (unit tests, direct calls to `joint_refinement`)
  and must be visible rather than merged into a real stage. An unrecognized string is a
  programming error, and catching it is what the closed vocabulary is for. The merged total stays
  correct either way.

- **D-04: the degeneracy keys are zero-initialized; the `pnp_*` keys are not.** Every stage that
  runs declares its degeneracy keys at 0 up front, so a clean solve emits an explicit zero.

  *Why:* `_bump` creates keys on first fire, so today a clean run emits **no key at all** — which
  is exactly why `check_rerun_gates.py:355` reports `no field found (cannot confirm zero)` instead
  of a pass. The todo's own formulation: *a zero that is present is evidence; a column that is
  absent is not.* Scoping it to this key family means no other artifact's shape moves days before
  a freeze.

### The third kind — reframed from hardware to solver excursion

- **D-05: `h_c <= 0` is kept as a third kind, but reframed and renamed.** Not `camera_submerged`
  (a claim about hardware) but something like **`interface_below_camera`** — *the estimated
  interface fell below an estimated camera center*. Documented as a **convergence diagnostic**;
  the physical-submersion reading is explicitly declared out of scope in the docstring.

  *Why the reframe — the user's correction, and it is the sharper reading:* physically submerged
  cameras are not what the library is built for and are out of scope. But `h_c = water_z - C_z`
  and **both terms are free parameters**. The reference camera sits at the origin so its `h_c` is
  just `water_z`; every other camera's `tvec_z` is estimated. So the condition is reachable with
  the cameras bolted above the water the whole time.

  *Direct evidence it happens:* Phase 23's D-06 measured E1's non-refractive, normal-free arm
  recovering `water_z = 0.0120 m`, pinned to the bound floor. At a 12 mm interface, any camera
  whose estimated Z exceeds 12 mm satisfies `h_c <= 0` — and that arm is where the 14,949 count
  lives. **Hypothesis, unmeasured:** most of E1's 14,949 is this kind, not corners above the
  surface. It matches the todo's own Finding 3 guess that the counter is really a diagnostic of
  solver excursion rather than of authored geometry.

  *This question answers itself for free in Phase 28* once the split ships — which is why no
  in-phase probe was taken (see D-13).

- **D-06 (REVISED 2026-08-17 — see amendment note): the NaN *reason* is plumbed out of
  `refractive_project_batch` via an opt-in, `None`-defaulted out-parameter.** The projector fills a
  per-point `int8` reason array at its four existing failure sites; `compute_residuals` reads it
  instead of re-deriving anything.

  The four sites are already cleanly separated in that function's control flow, so this is a
  read-off, not a new detection:
  1. `refractive_geometry.py:622` — `h_c <= 0`, whole batch → `interface_below_camera`
  2. the `valid` mask, which after the `on_axis` branch is exactly `h_q <= 0` → `above_interface`
  3. `camera.project()` returning `None` in the on-axis loop → `behind_camera`
  4. `camera.project()` returning `None` in the final projection loop → `behind_camera`

  **Nothing is written inside the Newton loop.** `delta`, `r_p_v`, the clip and the termination
  check are untouched. When the out-parameter is `None` — which is what production passes on every
  hot iteration — the function allocates nothing and pays one identity test, matching
  `_observability.py:44-49`'s established opt-in pattern.

  *Why this reverses the original decision:* the original rejected it to protect
  `core/refractive_geometry.py`'s return contract. But (a) that function **already carries an
  opt-in diagnostics flag** (`return_diagnostics`), which does strictly *more* invasive work —
  it allocates two arrays and computes `np.abs(delta)` on every Newton iteration, inside the loop;
  (b) an out-parameter avoids `return_diagnostics`' wart of changing the return *type*; and (c) an
  argument production passes as `None` cannot perturb the arithmetic, so the E2 sanity control has
  nothing to detect. D-18 proves that here rather than inferring it four phases later.

  *What it buys, beyond retiring the duplicated predicate:*
  - **The kind-precedence rule becomes unnecessary.** With cause available per point, cause and
    fate are independent: cause comes from the reason array, fate (`extended` vs `penalized`) from
    `unextendable`. The invariant becomes `sum over reasons == n_invalid` — derived and exact,
    rather than resting on an invented tie-break between `interface_below_camera` and `extended`.
  - **`extended` stops being a grab-bag.** Its split into `above_interface` and `behind_camera` is
    a direct down payment on Phase 25's DEGEN-04 question about the production rig's 198. Report
    the split; **do not interpret it here** — the classification claim is Phase 25's.

- **D-07 (REVISED 2026-08-17): a unit test asserts the reason array agrees with the observable
  outcome.** There is no longer a duplicated predicate to guard, so the test changes shape: construct
  a geometry with the interface below a camera center and assert `refractive_project_batch` returns
  an all-NaN batch **and** reports every point's reason as `interface_below_camera`; add the
  matching case for a corner above the interface and one behind the camera. The test now guards the
  *labelling* against the *behaviour*, which is the property that was actually at risk.

  *Why a test and not a comment:* unchanged — a comment is not a mechanism, and this project's
  knowledge base carries the recurring lesson that acknowledgment does not prevent recurrence.

- **D-06b (NEW 2026-08-17): the diagnostic out-parameters are threaded ONLY on the post-solve
  evaluation, never during the solve.** The counting apparatus already works this way today — the
  `_bump` at `interface_estimation.py:419` and `refinement.py:329` runs *after* `least_squares`
  returns, against one extra `compute_residuals(result.x, ...)` call. Every new out-parameter
  (the reason array, the kind breakdown, D-10's denominator) inherits that placement.

  *Why this is stated as a decision rather than left implicit:* threading the new out-parameters on
  every call instead of only the post-solve one would silently convert a free diagnostic into a
  hot-path cost on thousands of iterations, and nothing in the type signatures would catch it. A
  test asserts the projector is called with a `None` reason array during the solve.

  > **Amendment note (2026-08-17, the user's call).** D-06 and D-07 as originally captured chose to
  > recompute `h_c <= 0` at the call site and accept a duplicated predicate. On review during
  > planning the risk of plumbing was found to be overstated: the writes are ~5 lines, all at
  > existing failure branches, all outside the Newton loop, in a function that already ships a more
  > invasive opt-in diagnostic. The reversal also removes the kind-precedence rule that planning had
  > to invent to keep the three kinds from double-counting — the overlap it patched was an artifact
  > of mixing a cause-bucket with two fate-buckets, which having the cause per point dissolves.
  > The original decisions are preserved above in struck form for the record.

- **D-08: no hard raise for this kind.** A transient solver excursion must not abort a solve that
  converged, and Phase 28 runs the suite unattended on a machine nobody is watching. It counts and
  warns like the other kinds; the warning text is what distinguishes it (see D-14).

### Persistence — where the numbers land

- **D-09 (SUPERSEDED IN PART — see the REVISED note below; the column count is now 6, not ~4):**
  **CSVs get the merged total plus one column per kind (~4 columns); the full kind × stage
  breakdown and the per-stage denominators go to a JSON sidecar per run.**

  Enough to answer *"benign tail or solver excursion?"* by eye across a whole band, without adding
  ~12 columns to every band CSV — including E6's already-committed 102-row shape. Appends beside
  E6's existing column rather than redefining it, per the established experiment pattern.

  Applies to **E5, E1 and E7** — E6's band already persists the merged column on all 102 rows.

  > **REVISED 2026-08-17 (the user's call), after D-06's reversal produced two axes.** "One column
  > per kind" no longer resolves: there are now three *causes* and two *fates*, not one kind list.
  > **Both axes go in the CSV** — merged total + 3 cause columns + 2 fate columns = **6 columns.**
  > The stage breakdown and the per-stage denominators still go to the JSON sidecar.
  >
  > *Why both, when the original capped at ~4:* the cap existed to avoid ~12 columns, and 6 is
  > comfortably under it. The binding constraint named above — E6's committed 102-row shape — does
  > not actually apply, because this phase does not touch E6 at all.
  >
  > *Why neither axis can be the one published:* they answer different questions. **Fate** answers
  > *"can I trust this row's `optimality`?"* — `penalized > 0` means zero gradient, which is what
  > invalidates the convergence diagnostic. **Cause** answers *"what do I fix?"* —
  > `interface_below_camera` is a solver excursion, `above_interface` is scenario geometry.
  > Publishing one and burying the other in a sidecar forces a guess about which question the
  > future reader has, and the sidecar is the artifact nobody opens while scanning a band.
  >
  > *The structural bonus:* each axis independently sums to the merged total, so a six-column CSV
  > is **self-validating** — a bookkeeping bug appears as a row where the two axes disagree,
  > visible by eye. Publishing one axis discards that check.
  >
  > *Mitigation for the double-count hazard* (a reader summing cause and fate columns together):
  > column names must carry the axis, in the **full** form matching the key scheme —
  > `degenerate_observations_cause_*` and `degenerate_observations_fate_*`. Suppressing an axis to
  > prevent misreading is weaker than naming it so misreading is obvious.
  >
  > *(Corrected 2026-08-17: an earlier draft of this note wrote the short prefixes `degen_cause_*` /
  > `degen_fate_*` while also requiring "matching the key scheme" — the two could not both hold.
  > The full form wins: it matches `DISCARD_KEYS`, and it sits beside E6's already-committed
  > `degenerate_observations_at_solution` column without a spelling discontinuity.)*

- **D-10: the observation denominator is an explicit per-stage counter, not derived.**
  `compute_residuals` counts the observations it actually evaluated and emits it as a declared key
  per stage, beside the counts it is the denominator for. Count and denominator are produced by
  the same pass over the same data at the same moment.

  *Rejected — derive from `n_residuals / 2`:* `n_residuals` is `None` whenever
  `use_sparse_jacobian=False`, and the `/2` is an unstated invariant. *Rejected — reuse
  `problem_shape` totals:* that product is the number of observations that *could* have existed,
  not what the solve evaluated — `min_corners` filtering and absent observations already make the
  two differ, in the direction that flatters.

  This is what retires the hand-reconstructed `0.268%`.

- **D-11: `benchmark.json` gains the whole `discard_stats` dict as its own block, AND the merged
  total is mirrored into `problem_shape`.**

  The gate's third read shape (`check_rerun_gates.py:212-218`) already handles a `discard_stats`
  block; the mirror keeps its first read shape and any existing consumer working. **Structural
  upside:** every future counter reaches the benchmark record automatically — DEGEN-01's defect was
  precisely a field that existed in `discard_stats` and never got written into `problem_shape`
  (`pipeline.py:1709`). A hand-picked field list reproduces that defect's shape.

  *Accepted cost:* some duplication with `diagnostics.json`.

- **D-12 (Claude's discretion — user said "up to you"): the gate is updated here; the driver is
  Phase 26's.** `check_rerun_gates.py` changes in the same commit as the split — the todo is
  explicit that splitting the counter without touching the gate leaves it reading a key that no
  longer means what it did. `rerun_19_3.sh`'s stage list is left to DRIVER-01, because Phase 26's
  job is a completeness audit of that file and a partial edit from here is something it must
  reconcile rather than simply write. **Planning must leave Phase 26 a note naming this phase's new
  artifacts** — the todo warns this coupling was unenforced in every sibling todo. Mirrors Phase
  23's D-08.

### Warning rewrite (DEGEN-03)

- **D-13: severity is decided by kind AND fraction together.** Fraction separates E6's failure
  (whole frames across the interface, large fraction) from the production rig's 0.268% tail; kind
  decides what the text actually *says* — benign C0 continuation vs solver excursion vs flat
  penalty with no gradient.

  *Neither alone works:* E6's failure and the rig's 198 are both the `extended` kind, so kind alone
  gives the one case that must stay loud and the one that must quiet down identical treatment.

- **D-14: the threshold is 1%, justified in the docstring by the two measurements.** The production
  rig is 198 / 73,975 = **0.268%**; E1's degenerate arm logged 14,949 against a scenario with
  observations in the tens of thousands — tens of percent. Two orders of magnitude apart, so the
  value is not delicate. 1% is ~4× the measured rig value and errs toward staying loud: a rig that
  degraded to 1% would still shout.

  *Rejected — 5%:* better margin, but a rig at 3% (a tenfold degradation) would be reported
  quietly, and that trend is exactly what a user would want shouted at. *Rejected — make it a
  parameter:* same shape as the `water_z` bounds generalization this milestone just deferred (D-05,
  Phase 23) — source surgery days before a freeze.

  **This scales warning volume only.** The `count > 0 → degenerate` gate is untouched.

- **D-15: the text names both readings rather than inferring provenance.** One text that states the
  condition and hands the branch to the reader: *if this is an authored scenario the geometry is
  the fix; if this is measured hardware that is not available to you, and here is what the count
  does and does not invalidate.*

  *Why not a caller-supplied synthetic/measured flag:* threading a provenance argument through the
  solver stack for the sole benefit of warning text, and it is an assumption about the caller
  rather than a fact derived from the data — against the standing rule that the library stays
  camera-agnostic and validation derives from input data.

  The consequence clause narrows to what is true: the continuation is **C0 but not C1**;
  observations continued through it carry **zero `water_z` gradient**; **every other parameter keeps
  full gradient**, so those parameters still contribute to the reported optimality. Do not claim the
  continuation is smooth.

  > **Qualified 2026-08-17.** This clause originally read "*so the reported optimality remains
  > meaningful for them*". That is too strong, and measured the same day: `optimality` is volatile
  > at a fixed solution (92.78 → 27.58 → 2.16 across warm restarts while cost moved 1.8e-9), not
  > comparable across parameter blocks, and unreliable at small magnitudes (44% disagreement
  > against a 3-point reference at ~0.001, while large values are solid to 5 s.f.). The gradient
  > *contribution* claim is what the argument needs and is correct; the *meaningfulness* claim is
  > not this clause's to make. See `.planning/knowledge-base.md` § "`optimality` is real but
  > volatile".

### The D-06 bound-hit detector (handed over from Phase 23)

- **D-16: it becomes a solve-level field on `SolverDiagnostics`, not a kind in `discard_stats`.**
  A new field listing which parameters terminated *on* a bound rather than at a minimum, named via
  `build_parameter_labels`, generic over the whole parameter vector rather than `water_z`-specific.
  Reaches `benchmark.json` through the diagnostics path that already exists.

  *Why not as D-06 literally proposed (a failure kind):* `check_discard_invariants`' relations are
  about observation bookkeeping, so a parameter count sits in that dict as a unit error — and the
  merged total, which the production gate reads, would start summing two incommensurate things.
  The intent of D-06 is honored: the detector is degeneracy instrumentation and it lands here.

  *Motivating evidence (Phase 23):* both degenerate E1 arms terminated on a bound — 1.990 m against
  the 2.0 ceiling, 0.0120 m against the 0.01 floor — stronger evidence for the null direction than
  the cost-flatness sweep alone.

  > **Corroboration added 2026-08-17 — the detector's signal is confirmed present before anyone
  > implements it.** The block-decomposition probe read `result.active_mask` directly at each
  > solution: the pinned `water_z` slot reports `active_mask = 1` with a bound gap of
  > **2.000177801164682e-12**, while every other block reports `at_bound = 0`. So scipy's own
  > `active_mask` already carries exactly what D-16 wants to surface, on the real solve, with no
  > new computation — the field is a *plumbing* job, not a detection problem.
  >
  > One design consequence: a pinned parameter is legitimately at its bound by construction, so a
  > detector that flags "on a bound" without distinguishing *pinned by request* from *ran into a
  > limit* will fire on E1's non-refractive arm every time and be trained away, exactly as the
  > always-red gate in `knowledge-base.md` § "A gate FAIL that everyone has learned to expect" was.
  > The bound gap discriminates them cheaply: ~2e-12 means pinned, a wide gap means it travelled
  > there. Raw values in `optimality_blocks.json`.

### Verification budget

- **D-17: tests only — no long runs in this phase.** Extend
  `tests/synthetic/test_full_pipeline.py`'s existing `run_calibration_from_config` harness
  (`:512`, video decode stubbed) to assert the `discard_stats` block and the mirrored total
  actually land in `benchmark.json`; unit tests for the kind/stage split, the unattributed bucket,
  the raise-on-unknown-stage, zero-emission, and D-07's equivalence case.

  **This distinction is load-bearing:** `calibrate_synthetic` (`pipelines.py`) and
  `run_calibration_from_config` (`pipeline.py`) are **different writers**, and DEGEN-01's defect is
  in the production one. A test exercising only `calibrate_synthetic` verifies nothing about the
  claim this phase makes. `test_full_pipeline.py:649` was written for a previous gap of exactly
  this shape.

  *Not taken:* a short E1 non-refractive arm run (~3 min) to measure the D-05 hypothesis. It falls
  out of Phase 28 for free once the split ships. *Not taken:* an E2 real-rig run (48-87 min,
  10.26 GiB) — that is Phase 25's DEGEN-04 question, and Phase 28 produces the artifact anyway.

- **D-18: extend `tests/synthetic/test_guard_inertness.py` to cover the new counters.** The same
  solve with and without `discard_stats_out` must agree — asserted on **cost** and on a
  **well-conditioned case**, per this project's rule that bit-identity gates are
  conditioning-dependent.

  *Why local rather than relying on Phase 29's E2 sanity control:* that control fires four phases
  later against a tree that also contains Phase 23's solver-touching changes, so a failure would
  not attribute. And by then the freeze has happened.

### Plan decomposition

- **D-19: two plans, serial.**
  1. **Library core** — the kind/stage split, the stage kwarg, the denominator, zero-init, the
     `h_c` recomputation and its equivalence test, the warning rewrite, and the
     `SolverDiagnostics` bound-hit field. Every edit inside `interface_estimation.py`,
     `refinement.py`, `_optim_common.py` and `_observability.py`, done once by one executor.
  2. **Artifacts** — `pipeline.py`'s `problem_shape` mirror, `io/benchmark.py`, the E1/E5/E7
     columns and JSON sidecar, and `check_rerun_gates.py`. Depends on plan 1's key names.

  *Why not three plans (split, then warning ∥ artifacts):* DEGEN-02's bump sites and DEGEN-03's
  warning text are **adjacent lines in the same two blocks** (`interface_estimation.py:411-428`,
  `refinement.py:315-335`). The wave model's disjointness assumption is spatial, and this violates
  it in exactly the way the knowledge base warns about.

- **D-20: no commit mixes two requirements** (reworded 2026-08-17 — see below). Carries Phase 23's
  D-14 forward. Plan 1 ships DEGEN-02, DEGEN-03 and the bound-hit detector as separate commits so
  they bisect apart.

  > **Reworded 2026-08-17 (the user's call).** This previously read "one commit per requirement,"
  > which was ambiguous once DEGEN-02 grew to three commits (reason plumbing, counting core,
  > wiring). The stated purpose is *"so they bisect apart"*, and **more** granular commits inside a
  > requirement bisect better, not worse. The property that matters is that no commit mixes two
  > requirements; the minimum count was never the point.
  >
  > Squashing to literally one commit per requirement would also be actively harmful here: plan
  > 24-01's resumption contract uses per-task commit boundaries as handback points, so squashing
  > Tasks 1-3 would leave Tasks 1-2 uncommitted at the exact moment an executor hands back. That is
  > the "finished-but-uncommitted work that dies with the worktree" failure the knowledge base
  > already records.

- **D-21: keep both `_optim_common.py` diffs minimal and reviewable.** Phase 23's FIX-01 also
  touches this file, and Phase 29's E2 sanity control (~3e-09, same-seed) is what proves neither
  phase perturbed the solve. Carried forward from Phase 23's `<code_context>`.

- **D-22: while `test_e5_band_mode.py` is open for the new column, put its `TestBandMode` tests on
  a `scope="module"` fixture** mirroring `test_e6_band_mode.py:74`. E5's five tests currently re-run
  the band per test (317 s against E6's 93.89 s for six). Test-time only; changes no artifact and
  gates nothing. Absorbed into the DEGEN-01 todo from a retired todo — worth doing here only
  because those tests need editing anyway.

### Claude's Discretion

- **D-12's split of gate-vs-driver ownership** was explicitly delegated ("up to you") and is
  recorded above with its rationale.
- The exact spelling of the flat key scheme (separator, kind names, whether `unattributed` is one
  key or one per kind) — pick something greppable and consistent with `DISCARD_KEYS`' existing
  naming.
- The final name for the third kind. `interface_below_camera` is the working name; anything that
  reads as a statement about the *estimate*, not the hardware, satisfies D-05.
- The JSON sidecar's filename and location, subject to not colliding with the band-owned
  `e{1,5,6,7}_seed_band_provenance.json` sidecars.
- Whether the bound-hit field records names only, or names plus which bound and by how much.

### Folded Todos

All three carry `resolves_phase: 24` frontmatter, so folding was not re-asked.

- `2026-08-15-degeneracy-counter-is-unobservable-and-merges-two-failure-kinds.md` — DEGEN-01 and
  the counter split. **Owns the split.** Carries the "third defect" section establishing the
  cross-stage accumulation for E2 (198 = interface-optimization count + intrinsic-pass count;
  double-counting factor at most 2), and the D-22 test-fixture clause.
- `2026-08-15-degeneracy-instrumentation-the-rerun-must-emit.md` — DEGEN-02's third kind and the
  denominator. Its Finding 2 is **superseded** by the sibling above; Finding 1 (the pinhole
  continuation is *exactly* correct for `h_q <= 0`, not merely continuous) and Finding 3 (obliquity
  is refuted) are live and binding.
- `2026-08-15-narrow-the-degenerate-observation-warning.md` — DEGEN-03. Its obliquity Solution
  bullet is struck; do not action it.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Phase requirements
- `.planning/REQUIREMENTS.md` § Degeneracy Observability (DEGEN) — DEGEN-01..03 statements,
  including the 2026-08-17 narrowing (E6's band already persists the column; the gap is E5/E1/E7)
- `.planning/ROADMAP.md` § Phase 24 — the four success criteria

### The three todos (all `resolves_phase: 24`)
- `.planning/todos/pending/2026-08-15-degeneracy-counter-is-unobservable-and-merges-two-failure-kinds.md`
  — **read § "Third defect" and § "Do not" before planning.** Owns the split.
- `.planning/todos/pending/2026-08-15-degeneracy-instrumentation-the-rerun-must-emit.md`
  — **read Findings 1 and 3; Finding 2 is superseded.** Owns the third kind and the denominator.
- `.planning/todos/pending/2026-08-15-narrow-the-degenerate-observation-warning.md`
  — **its obliquity bullet is struck; do not action it.**

### Adjacent phases — do not absorb their scope
- `.planning/phases/23-experiment-correctness-fixes/23-CONTEXT.md` — D-06 hands the bound-hit
  detector here; § Integration Points warns both phases touch `_optim_common.py`; the 2026-08-17
  amendment forbids writing `MANUSCRIPT-FINDINGS.md`
- `.planning/todos/pending/2026-08-15-classify-the-198-unprojectable-observations.md` — DEGEN-04,
  **Phase 25.** Owns the per-observation emission. Composes with this split; do not implement.
- `.planning/todos/pending/2026-08-15-decide-degeneracy-gate-scope-for-real-rig-runs.md` —
  deferred policy decision. Its 0.268% denominator argument is what D-10 retires.
- `.planning/todos/pending/2026-08-15-make-the-suite-driver-cover-every-invocation.md` — DRIVER-01,
  **Phase 26.** Owns `rerun_19_3.sh`; D-12 leaves it a note, not an edit.
- `.planning/todos/pending/2026-08-15-suspend-programmatic-check-for-reshaped-artifacts.md` — the
  hand-verification sheet the DEGEN-01 todo asks these expectations be added to.

### Domain and evidence
- `.planning/MANUSCRIPT-FINDINGS.md` :1878-1882 — the split-the-counter recommendation, unactioned
  since. **Read, do not write** (Phase 23's 2026-08-17 amendment).
- `.planning/geometry.md` § 4.3 — `water_z` is a Z-coordinate, not a distance; `h_c = water_z - C_z`
- `.planning/knowledge-base.md` § Known Issues — the executor/background-run policy
- `docs/guide/benchmarking.md` — what `benchmark.json` currently documents as its shape

### Scope boundary
- The manuscript tree `Spinoffs/papers/aquacal/` is **read-only from this repo.** Where a fix has a
  manuscript consequence the deliverable is *the evidence, not the sentence*. Line references to
  `main.tex`/`supplement.tex` in any todo are motivation, never work orders.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets

- **`DISCARD_KEYS` + `check_discard_invariants` (`_observability.py:61-170`)** — the closed
  vocabulary and its violation reporting. D-01 is chosen specifically to leave this untouched.
  `degenerate_observations_at_solution` is declared at `:89` with a comment asserting it is counted
  once per stage on the final evaluation — that comment is accurate per-call and misleading in
  aggregate, and should be corrected alongside the split.
- **`_bump` (`_observability.py:102-113`)** — `stats[key] = stats.get(key, 0) + n`, the
  accumulation that makes the merged key a cross-stage sum.
- **`SolverDiagnostics` (`_observability.py:231-312`)** — D-16's home. Already carries scipy's
  terminal state and the **absent-metric convention (D-15 of Phase 19)**: a metric a site cannot
  produce is `None` plus a `*_reason` string, never silently omitted. The bound-hit field should
  follow it.
- **`build_parameter_labels` (`_observability.py:315-396`)** — mirrors `pack_params`' layout
  exactly, so `labels[i]` names `x[i]`. This is how D-16 names which parameters hit a bound.
- **`capture_solver_diagnostics` (`:399`)** — the single intended writer of `SolverDiagnostics`
  fields; D-16's field is populated there, not by reading `result.x` at a call site (the docstring
  explains why: retaining large arrays inflates the peak-memory measurement BENCH-02 depends on).
- **`tests/synthetic/test_full_pipeline.py:512`** — an existing end-to-end
  `run_calibration_from_config` harness with only video decode stubbed. D-17's vehicle. `:649`
  documents a previous gap of exactly this shape.
- **`tests/synthetic/test_guard_inertness.py`** — the existing contract that observability does not
  move the numbers. D-18 extends it.
- **`tests/unit/test_discard_accounting.py`** — where the counter vocabulary is already tested.

### Established Patterns

- **Opt-in out-parameter, defaulting to `None`** — `_observability.py:44-49`: when `stats is None`,
  `_bump` does one identity test and returns, so behaviour is byte-for-byte unchanged for every
  existing caller. D-04's zero-init must preserve this: no dict, no keys.
- **Nothing may be counted from a per-point or per-residual loop** (`_observability.py:51-56`).
  Every instrumented site is per-(camera, frame). D-06 and D-10 both respect this — `h_c` is
  per-camera and the denominator is a per-batch sum.
- **Experiments append columns rather than redefine them,** so old artifacts stay readable. D-09 is
  bound by this, and E6's committed 102-row band is the concrete constraint.
- **The absent-metric convention:** `None` plus a `*_reason` string, never a silent omission.

### Integration Points

- `interface_estimation.py:411-428` and `refinement.py:315-335` — the two bump sites, each
  immediately followed by its warning block. **DEGEN-02 and DEGEN-03 edit adjacent lines here**;
  D-19's two-plan split exists because of it.
- `_optim_common.py:695-710` — `refractive_project_batch` → `invalid` mask → `_extend_invalid_projections`
  → `unextendable` → `INVALID_PROJECTION_PENALTY_PX`. **The `extended` vs `penalized` split is
  already computed here** — `unextendable` is exactly the behind-camera case. That half of the kind
  split is nearly free. `h_c <= 0` is not, hence D-06.
- `refractive_geometry.py:622` — the whole-batch `h_c <= 0` early return. D-07's equivalence test
  anchors on this line; D-06 deliberately does not modify it.
- `pipeline.py:766` → six `_bump` call sites (`:808, :915, :1031, :1107, :1280, :1439`) with no
  reset. **Only two of them bump this key**; the other four bump `pnp_*`. So the production 198 is
  a two-term sum, not six.
- `pipeline.py:1709` `problem_shape` → `io/benchmark.py:458` — the DEGEN-01 gap. D-11 fixes it
  structurally rather than by adding a field.
- `check_rerun_gates.py:212-218` (`_guard_count_from_record`, three read shapes) and `:348-362`
  (the `cannot confirm zero` FAIL branch) — D-04 and D-11 together make that branch reachable-and-
  passing for the first time on the headline run.
- `e5_index_sensitivity.py:460, 579` — E5 already threads `discard_stats_out` internally and simply
  never writes it out. D-09's E5 column is a write, not new plumbing.

</code_context>

<specifics>
## Specific Ideas

- **The user's reframe of the third kind is the discussion's most consequential moment** and should
  survive into the docstrings verbatim in spirit: *"The cameras are never submerged in reality,
  that's just not what the library is built to do. If there's a possibility that this condition
  arises in error due to bad optimization or something, that's different."* That is exactly the
  case — `h_c = water_z - C_z` with both terms estimated — and it converts a dismissible
  hardware edge case into a solver-excursion diagnostic. See D-05.

- **The measurement that makes it concrete**, from Phase 23's D-06:

  | E1 arm | recovered `water_z` | landed |
  |---|---|---|
  | n=1.0, normal fixed | 1.990 m | on the 2.0 ceiling |
  | n=1.0, normal free | 0.0120 m | on the 0.01 floor |
  | n=1.333, normal free | 1.0236 m | interior (−7.43 mm from GT) |

  A 12 mm estimated interface with cameras above it is `h_c <= 0` for most of the rig.

- **The two numbers that justify D-14's 1% threshold** should be quoted in the docstring, not
  paraphrased: 198 / 73,975 = 0.268% on the production rig; 14,949 on E1's degenerate arm against
  a scenario with observations in the tens of thousands.

- **Phase 28 answers the D-05 hypothesis for free.** Planning should note it as an expected
  read-off from the frozen run rather than an open question, so nobody re-opens it as a probe.

</specifics>

<deferred>
## Deferred Ideas

- **Measuring how much of E1's 14,949 is `interface_below_camera`** — considered as a ~3 min
  in-phase probe under D-17 and not taken. It falls out of Phase 28's frozen run for free once the
  split ships.
- **Making the 1% warning threshold a parameter** — D-14. Same shape as Phase 23's D-05 deferral of
  the hardcoded `water_z` bounds: source generalization days before a freeze. Revisit
  post-submission, alongside that todo.
- ~~**Plumbing a NaN-reason flag out of `refractive_project_batch`** — D-06's rejected
  alternative.~~ **ADOPTED 2026-08-17** — no longer deferred; see the revised D-06. It was the
  authoritative route, it retires D-07's duplicated predicate, and it removes the need for a
  kind-precedence rule.
- **Registering these artifacts in `rerun_19_3.sh`** — D-12. Explicitly Phase 26's (DRIVER-01), with
  a note left by this phase.
- **The real-rig degeneracy gate scope decision** — remains deferred and cannot be made until
  DEGEN-04 (Phase 25) reports what the 198 are.
- **Correcting `MANUSCRIPT-FINDINGS.md`'s F-003/F-006 denominators** — the drafted "198 of 73,975
  (0.27%)" assumes a solution-state count and is wrong against a cross-stage sum. This phase owes
  the manuscript session *a counter whose value means what its name says*, not the sentence.
  Manuscript work is the user's, per standing rule.

### Reviewed Todos (not folded)

`todo.match-phase` surfaced these on keyword similarity; their `resolves_phase` frontmatter binds
them elsewhere, and frontmatter is authoritative.

- `2026-08-15-classify-the-198-unprojectable-observations.md` — DEGEN-04, **Phase 25**
- `2026-08-14-decide-whether-e1-may-carry-absolute-accuracy-claims.md` — BAND-01, **Phase 25**
- `2026-08-13-e4-aggregator-hardcodes-e2-benchmark-path.md` — FIX-05, **Phase 23**
- `2026-08-15-correct-stale-strings-in-e2-and-the-synthetic-generator.md` — FIX-06, **Phase 23**
- `2026-08-15-archive-stale-outputs-before-the-run-purge-them-after.md` — DRIVER-04, **Phase 26** /
  POST-03, **Phase 30**
- `2026-08-15-decide-degeneracy-gate-scope-for-real-rig-runs.md` — deferred policy, no phase

</deferred>

---

*Phase: 24-Degeneracy Instrumentation*
*Context gathered: 2026-08-17*
