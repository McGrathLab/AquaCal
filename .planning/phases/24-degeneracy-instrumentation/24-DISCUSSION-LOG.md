# Phase 24: Degeneracy Instrumentation - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-08-17
**Phase:** 24-degeneracy-instrumentation
**Areas discussed:** Counter schema (kind × stage), camera_submerged detect + escalate,
Persistence granularity + denominator, Warning rewrite + D-06 bound-hit, Verification budget,
Plan decomposition

---

## Counter schema (kind × stage)

### Q1 — How should the kind × stage split be represented in discard_stats?

| Option | Description | Selected |
|--------|-------------|----------|
| Flat enumerated keys | Closed flat `DISCARD_KEYS` tuple untouched, merged key stays as the sum; vocabulary must enumerate every pair up front | ✓ |
| Nested detail sub-dict | Open over stages, JSON-shaped, denominator adjacent to its count; needs carve-outs in the invariant checker | |
| Per-stage dicts at the source | Fixes the root cause (`pipeline.py:766` threads one dict to six sites); widest diff, touches every `pnp_*` counter | |

**User's choice:** Flat enumerated keys
**Notes:** Preserves `check_discard_invariants` and `check_rerun_gates.py`'s three read shapes with
no modification.

### Q2 — Where does the stage label come from, given one function bumps under two stage identities?

| Option | Description | Selected |
|--------|-------------|----------|
| Explicit kwarg from the caller | `discard_stage: str` on `optimize_interface` / `joint_refinement`; inert when unset, independent of observability | ✓ |
| Reuse `OptimizerObserver.stage` | Vocabulary already exists and is already threaded; but observer is `None` on ordinary runs, so the split would silently collapse | |
| Infer from existing arguments | No signature change; correct today, silently wrong on the next flag combination | |

**User's choice:** Explicit kwarg from the caller
**Notes:** Forced by `joint_refinement` being invoked as both Stage 3 joint (`pipelines.py:159`)
and the intrinsic pass (`:192`).

### Q3 — What happens when a bump arrives with no stage label, or one outside the declared set?

| Option | Description | Selected |
|--------|-------------|----------|
| Named bucket + reject unknown strings | Absent → declared `unattributed` key; unrecognized string raises as a programming error | ✓ |
| Named bucket, accept anything | Permissive; routes around the undeclared-key violation that would catch a typo | |
| Default to the module's natural stage | No bucket needed; gets the intrinsic pass — the site that most needs a label — silently wrong | |

**User's choice:** Named bucket + reject unknown strings

### Q4 — Should the degeneracy keys be emitted with explicit zeros on a clean run?

| Option | Description | Selected |
|--------|-------------|----------|
| Zero-initialize the degeneracy keys only | Clean solve emits an explicit zero; `pnp_*` keep create-on-bump so no other artifact shape moves | ✓ |
| Zero-initialize every DISCARD_KEY | Uniform; changes `diagnostics.json` shape for every counter right before a freeze | |
| Keep create-on-bump; gate infers zero | No library change; the absent-means-fine inference is what let 14,949 go unrecorded | |

**User's choice:** Zero-initialize the degeneracy keys only
**Notes:** Directly fixes `check_rerun_gates.py:355`'s `cannot confirm zero` branch at the source.

---

## camera_submerged: detect + escalate

### Q1 — How should camera_submerged (h_c <= 0) be detected?

| Option | Description | Selected |
|--------|-------------|----------|
| Recompute in `compute_residuals` | One comparison per (camera, frame), outside the per-point loop; no change to `core/refractive_geometry.py`; risks predicate drift | ✓ |
| Flag out of the projector | Authoritative by construction; touches core geometry's return contract, where TIR branches were deliberately left silent | |
| Don't distinguish it this phase | Smallest scope; the frozen run would again be unable to tell you if it fired | |

**User's choice:** Recompute in `compute_residuals`

### Q2 — How should the duplicated predicate be protected against drift?

| Option | Description | Selected |
|--------|-------------|----------|
| Equivalence test on a constructed case | Asserts the projector's all-NaN batch and the classifier agree; fails if either condition changes | ✓ |
| Test plus a cross-reference comment | Belt and braces | |
| Comment only | A comment is not a mechanism | |

**User's choice:** Equivalence test on a constructed case

### Q3 — What should a non-zero camera_submerged count do?

**Asked, then re-framed.** The user first replied *"what do you mean by air-calibrated intrinsics
were used underwater?"* — answered: Stage 1 calibrates intrinsics in air; when `h_c <= 0` the
projector returns all-NaN and `_extend_invalid_projections` falls back to pinhole with those in-air
`fx, fy`, but behind a flat port the effective focal length scales roughly with `n_water` (~1.33×),
so the fallback is systematically ~33% short and its residual looks like an ordinary large
reprojection error.

The user then pushed back:

> *"I kind of feel like this edge-case is a non-problem, or at least not the problem we're
> describing. The cameras are never submerged in reality, that's just not what the library is
> built to do. If there's a possibility that this condition arises in error due to bad optimization
> or something, that's different. But if it's actually submerged cameras, that's out of our scope."*

**This was correct and re-scoped the kind.** `h_c = water_z − C_z`, and both terms are free
parameters — the reference camera sits at the origin so its `h_c` is just `water_z`, and every
other camera's `tvec_z` is estimated. The condition is reachable with the cameras in air the whole
time. Phase 23's D-06 measured E1's non-refractive normal-free arm recovering `water_z = 0.0120 m`;
at a 12 mm interface most of the rig satisfies `h_c <= 0`. That arm is also where the 14,949 count
lives.

### Q3b — Given that, how should the third kind be scoped?

| Option | Description | Selected |
|--------|-------------|----------|
| Keep it, reframed as an excursion | Renamed to `interface_below_camera`, documented as a convergence diagnostic; no hard raise; physical submersion declared out of scope | ✓ |
| Reframe it and measure the E1 split | Same, plus a ~3 min in-phase probe to test the hypothesis before the freeze | |
| Drop the third kind | Ship extended vs penalized only; hypothesis stays untested | |

**User's choice:** Keep it, reframed as an excursion
**Notes:** The probe was not taken — once the split ships, Phase 28's frozen run answers the
hypothesis as a side effect at no extra cost. The hard-raise option was dropped in the reframe: a
transient excursion must not abort a converged solve, especially in Phase 28's unattended suite.

---

## Persistence granularity + denominator

### Q1 — How wide should the persisted counter be in the experiment CSVs?

| Option | Description | Selected |
|--------|-------------|----------|
| Total + per-kind in CSV, full detail in JSON | ~4 columns, enough to read benign-vs-excursion across a band; kind × stage and denominators to a JSON sidecar | ✓ |
| Full kind × stage width in the CSV | One artifact, nothing to join; ~12 columns onto E6's committed 102-row shape, some structurally empty | |
| Total only in CSV, everything else in JSON | Narrowest change; answering which-kind-which-stage across a band means opening 10 JSON files | |

**User's choice:** Total + per-kind in CSV, full detail in JSON

### Q2 — Where does the per-stage observation denominator come from?

| Option | Description | Selected |
|--------|-------------|----------|
| Explicit per-stage counter | Count and denominator produced by the same pass over the same data at the same moment | ✓ |
| Derive from `n_residuals` | Zero new instrumentation; `None` under `use_sparse_jacobian=False` and the `/2` is an unstated invariant | |
| Reuse `problem_shape` totals | No new fields; counts observations that *could* have existed, wrong in the flattering direction | |

**User's choice:** Explicit per-stage counter
**Notes:** Retires the hand-reconstructed 0.268%.

### Q3 — How should the degeneracy fields reach the production benchmark.json?

| Option | Description | Selected |
|--------|-------------|----------|
| Whole `discard_stats` block + total mirrored in `problem_shape` | Gate's third read shape already handles it; mirror keeps the first shape alive; every future counter reaches the record automatically | ✓ |
| Whole `discard_stats` block only | No duplication; `problem_shape` never carries the count and the gate's first read shape stays dead | |
| Hand-picked fields into `problem_shape` | Narrowest diff; reproduces the original defect's shape | |

**User's choice:** Whole `discard_stats` block + total mirrored in `problem_shape`

### Q4 — Who registers this phase's new artifacts with the gate and the driver?

| Option | Description | Selected |
|--------|-------------|----------|
| Gate here, driver in Phase 26 | Mirrors Phase 23's D-08 | ✓ (Claude's discretion) |
| Both here | Closes the coupling immediately; two phases editing `rerun_19_3.sh` | |
| Both in Phase 26 | One pass with full visibility; leaves the gate reading a changed key in the interim | |

**User's choice:** *"up to you"* — delegated.
**Notes:** Claude chose gate-here / driver-in-26. The gate change is not optional (the todo says
splitting the counter without touching the gate leaves it reading a key that no longer means what
it did); the driver is a completeness audit by nature and should not be half-edited from here.

---

## Warning rewrite + D-06 bound-hit

### Q1 — What decides the warning's severity and wording?

| Option | Description | Selected |
|--------|-------------|----------|
| Kind and fraction together | Fraction separates E6 from the rig's tail, kind decides what the text says; introduces a threshold constant | ✓ |
| Kind only, no threshold | No magic number; E6's failure and the rig's 198 are both the `extended` kind, so it cannot separate them | |
| Fix the text, don't scale at all | Smallest change; leaves the todo's central complaint in place | |

**User's choice:** Kind and fraction together

### Q2 — What fraction separates the quiet tail from the loud failure?

| Option | Description | Selected |
|--------|-------------|----------|
| 1%, stated as measured-derived | ~4× the rig's 0.268%, two orders below the E1-arm regime; errs toward staying loud | ✓ |
| 5%, maximum margin both ways | Neither regime near the boundary; a rig at 3% (tenfold degradation) would be reported quietly | |
| Parameter with a default | Retunable without a source fork; same shape as the `water_z` bounds generalization just deferred | |

**User's choice:** 1%, stated as measured-derived
**Notes:** Scales warning volume only — the `count > 0 → degenerate` gate is untouched, per
`19.3-07-PLAN.md`.

### Q3 — How should the warning advise without knowing synthetic vs measured rig?

| Option | Description | Selected |
|--------|-------------|----------|
| Name both readings, let the user pick | One text giving the branch to the reader; no plumbing, no provenance inference, camera-agnostic | ✓ |
| Caller-supplied provenance flag | Sharpest advice per audience; threads a provenance argument through the solver stack for warning text | |
| Let kind and fraction carry it | Drops prescriptive advice; serves neither audience | |

**User's choice:** Name both readings, let the user pick

### Q4 — Where does the bound-hit detector live?

| Option | Description | Selected |
|--------|-------------|----------|
| Solve-level field on `SolverDiagnostics` | Generic over the parameter vector, named via `build_parameter_labels`; honors D-06 without treating a parameter as an observation | ✓ |
| As a kind in `discard_stats` | Literally what D-06 said; unit error in an observation-counting dict, and the merged total would sum incommensurate things | |
| Defer it out of Phase 24 | Cleanest scope; the pre-freeze window is when the detector is worth anything | |

**User's choice:** Solve-level field on `SolverDiagnostics`

---

## Verification budget

### Q1 — What verifies this phase in-phase?

| Option | Description | Selected |
|--------|-------------|----------|
| Tests only, on the production-path harness | Extend `test_full_pipeline.py`'s `run_calibration_from_config` harness plus unit tests; no long runs | ✓ |
| Tests plus a short E1 arm run | ~3 min, tests the excursion hypothesis before the freeze | |
| Tests plus a real-rig run | 48-87 min, 10.26 GiB; Phase 25's question, and Phase 28 produces the artifact anyway | |

**User's choice:** Tests only, on the production-path harness
**Notes:** The `calibrate_synthetic` vs `run_calibration_from_config` distinction is load-bearing —
DEGEN-01's defect is in the production writer, so a test exercising only `calibrate_synthetic`
verifies nothing.

### Q2 — Should this phase carry its own inertness check?

| Option | Description | Selected |
|--------|-------------|----------|
| Extend the existing guard-inertness test | Local, fast, attributes a regression to this diff rather than a four-phase window | ✓ |
| Rely on Phase 29's E2 control | Real end-to-end evidence; fires after the freeze and cannot attribute | |
| Both, with the local test as the gate | Most coverage; Phase 29's control is not this phase's to add | |

**User's choice:** Extend the existing guard-inertness test
**Notes:** Asserted on cost and a well-conditioned case, per the project's rule that bit-identity
gates are conditioning-dependent.

---

## Plan decomposition

### Q1 — How should DEGEN-01/02/03 plus the bound-hit detector split into plans?

| Option | Description | Selected |
|--------|-------------|----------|
| Two plans, serial | Library core (both solver files + `_observability.py`), then artifacts (benchmark, experiments, gate) | ✓ |
| Three plans, 02 then a parallel wave | Cleaner requirement mapping; plans 2 and 3 edit adjacent lines in the same two files | |
| Four plans, one per requirement | Tightest traceability; three of four touch the same files, so nothing parallelizes | |

**User's choice:** Two plans, serial
**Notes:** DEGEN-02's bump sites and DEGEN-03's warning text are adjacent lines in the same two
blocks. One commit per requirement inside the shared plan, carrying Phase 23's D-14 forward.

---

## Claude's Discretion

- **Gate-vs-driver ownership** (Persistence Q4) — explicitly delegated. Chose gate here, driver in
  Phase 26, with a note left for DRIVER-01.
- The exact spelling of the flat key scheme — separator, kind names, whether `unattributed` is one
  key or one per kind.
- The final name for the third kind; `interface_below_camera` is the working name.
- The JSON sidecar's filename and location, subject to not colliding with the band-owned
  `e{1,5,6,7}_seed_band_provenance.json` sidecars.
- Whether the bound-hit field records parameter names only, or names plus which bound and by how
  much.

## Deferred Ideas

- Measuring how much of E1's 14,949 is `interface_below_camera` — falls out of Phase 28 for free.
- Making the 1% warning threshold a parameter — post-submission, alongside the `water_z` bounds
  todo.
- Plumbing a NaN-reason flag out of `refractive_project_batch` — belongs with any future work that
  reopens `core/refractive_geometry.py`.
- Registering these artifacts in `rerun_19_3.sh` — Phase 26 (DRIVER-01).
- The real-rig degeneracy gate scope decision — blocked on DEGEN-04 (Phase 25).
- Correcting `MANUSCRIPT-FINDINGS.md`'s F-003/F-006 denominators — manuscript work, the user's.
