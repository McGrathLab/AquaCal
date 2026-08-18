# Phase 25: Degeneracy Classification & Claim Licensing - Context

**Gathered:** 2026-08-17
**Status:** Ready for planning

<domain>
## Phase Boundary

Two open questions blocking manuscript language are answered and recorded before the freeze:
what the production rig's 198 unprojectable observations are (DEGEN-04), and what domain E1's
absolute-accuracy numbers may be stated over (BAND-01) — plus carrying forward the already-settled
convergence verdict (DEGEN-05, verdict only; the instrumentation was Phase 24's).

- **DEGEN-04** — a per-observation detail sink for flagged observations, an offline classifier,
  full-population `h_q` logging for E2 behind a default-off config flag, and one **provisional**
  local instrumented E2 run that settles the *mechanism*
- **BAND-01** — E1's seed band gains a `noise_std` axis at `{0.25, 0.5, 0.82, 1.2}` px across the
  existing ten seeds; the `n_cameras` geometry axis stays explicitly skipped; the licensing
  sentence is written where the code lives
- **DEGEN-05** — verdict only: the convergence question is **already answered** and must not be
  re-derived. Carry it forward, label the shipped `optimality` scalar, and close or size the one
  open objection (the Huber knee)

**Not in this phase:** the frozen E2 run and its committed classification table (Phases 28/29),
the driver/gate registration itself (Phase 26/27 consume this phase's outputs), and any manuscript
prose. The manuscript tree `Spinoffs/papers/aquacal/` is **read-only from this repo**.

</domain>

<decisions>
## Implementation Decisions

### DEGEN-04 — delivery boundary

- **D-01:** Phase 25 runs **one local instrumented E2 now**, against the archive's
  `config_paper.yaml` under **OpenCV 4.13** (the pin matters — 198 at 4.13, 194 at 4.14), rather
  than waiting for Phase 28. Cost is a 48–87 min / ~10.26 GiB unattended run. Rationale: the
  answer is needed before the freeze so the gate-scope call and the disclosure sentence can both
  be settled against the 2026-08-21 deadline.
- **D-02:** The local run is **PROVISIONAL ONLY**. It settles the *mechanism* — which bucket
  dominates — and **no count from it reaches `MANUSCRIPT-FINDINGS.md`, the disclosure, or any
  §3-facing number**. Phase 29's frozen table is the sole source of every number. This preserves
  the single-source-of-truth premise the milestone exists to establish.
- **D-03:** The probe is isolated under
  `.planning/probes/2026-08-17-degeneracy-classification/` (the pattern
  `2026-08-17-optimality-decomposition/` already set), with `--out` pointed there so **nothing
  lands in `experiments/results/`**. The classification table carries an explicit
  provisional + git-sha stamp in its header. Both `FINDINGS.md` and the table are committed.
- **D-04:** Criterion 2 (the deferred degeneracy-gate scope decision) is settled **on mechanism,
  with a tripwire**. If bucket (a) `h_q <= 0` dominates, the gate stays **synthetic-only** and the
  authored-vs-given-geometry rationale is written into `_observability.py` **and both harnesses'
  guard blocks** (`e4_benchmark_grid.py`, `e6_generalization_sweep.py`) so a code reader meets the
  reasoning at the gate. A recorded trigger re-opens it: a materially populated bucket (b) in
  Phase 29's frozen table.

  *Why mechanism and not count:* the gate argument is "synthetic geometry is authored so an
  unprojectable observation means a malformed scenario; physical geometry is given so a small
  unprojectable fraction is a fact about the deployment." That is sound only if the 198 are
  bucket (a) — a breached surface is a deployment fact; bucket (b), a camera-model failure on the
  crossing point, is a library limitation and a different decision. The count was never load-
  bearing, and the todo's own 0.268% arithmetic was already invalidated by the cross-stage-sum
  finding.
- **D-05:** Do **not** soften the synthetic gate into a threshold. `19.3-07-PLAN.md` is explicit:
  exactly `count > 0 -> degenerate`, smoke-path carve-out only.

### DEGEN-04 — artifact and flag surface

- **D-06:** **Raw sink in the library, classifier in `experiments/`.** `compute_residuals` gains a
  detail sink alongside the existing `degeneracy_breakdown_out`, filled with **raw geometry only**:
  `(camera, frame_idx, corner_id, h_q, h_c, r_q, exit angle, extension-succeeded, stage)`. The
  bucketing and the CSV writer live in `experiments/_degeneracy.py`, beside
  `write_degeneracy_breakdown`. **The library never spells a bucket name** — the same separation
  Phase 24 held for the flat `DISCARD_KEYS` strings, and the right call given the taxonomy has been
  revised twice in two days (obliquity retired, camera-model failure added).
- **D-07:** `stage` is **mandatory**, not optional — the counter is a cross-stage sum, so a
  per-observation record without its stage cannot be reconciled against the total.
- **D-08:** Ordinary users get a **`degenerate_observations.csv` sidecar** beside
  `diagnostics.json` in the normal output dir, **written only when at least one flagged row
  exists**. A clean rig writes nothing. This is what delivers the todo's "the next person to meet a
  non-zero count gets the answer for free."
- **D-09:** Full-population `h_q` logging (**E2 only**, ~74k rows/stage, ~10 MB) is a **config
  schema field** consumed by `run_calibration_from_config` and threaded to the residual call.
  **Default off.** E2 reaches it through `config_paper.yaml`, so the flag's state is captured in
  the run's own provenance rather than only in an invocation line. Phase 26's driver passes it for
  E2 and nothing else.
- **D-10:** Row cap of order **50k per stage**: truncate, keep the aggregate count **exact** (it
  comes from the Phase 24 counters, not from row length), stamp `truncated: true` plus the true
  count **in the artifact's own header**, and warn. A reader of the file alone can never mistake a
  truncated table for a complete one — the runtime warning is not enough, because unattended
  overnight is exactly when nobody reads the log.

### BAND-01 — noise axis

- **D-11:** Thread the noise level by **overriding `scenario.noise_std` before the solve**. No
  `create_scenario` signature change (a public-API change two phases before a freeze is what forced
  v2.0.0 last time). The override gets the evaluation set for free —
  `e1_refractive_comparison.py:438` already passes `scenario.noise_std` when generating test-set
  detections, so calibration and evaluation noise track together, which is what a rig-level claim
  needs. Validated by the P1 probe: reprojection RMS tracked injected noise at all three levels.
- **D-12:** The axis is **band-only**. It lives inside `_run_band`; `_run_smoke`, `_run_check` and
  the single-seed run keep today's behaviour at the scenario default. Only `exp1_band.csv` gains
  the column.
- **D-13:** The two-factor movement (added noise levels **and** E1's freed interface normal from
  FIX-02) gets an **anti-confusion note, not an emitter and not a computed delta**.

  *Rationale (author, 2026-08-17):* the old normal-fixed version will not be published, so **no
  §3-facing number depends on the attribution** and Phase 27's criterion-5 emitter requirement does
  not bite here. The note exists purely so a future agent meeting a moved number does not re-derive
  the cause or read it as a regression. Record that the 0.5 px row is the clean `normal_fixed`
  isolator (the noise axis contributes nothing at that level).
- **D-14:** The **stated domain** — the sentence licensing the absolute-accuracy claim — is
  recorded in **two** places: `e1_refractive_comparison.py`'s header **beside the existing
  D-19.3-17 demotion note** (so the next reader meets both halves and the tension does not
  resurface), and an **MF-NN entry in `.planning/MANUSCRIPT-FINDINGS.md`** carrying the derivation
  for the manuscript session.

### DEGEN-05 — verdict and the optimality caveat

- **D-15:** The convergence question is **already answered and must not be re-derived**. Warm
  restarts recover no cost (largest relative drop 1.8e-9), so E1's non-refractive baseline is
  converged, the comparison is fair, and the **97–178× band is strengthened, not caveated**.
- **D-16:** The caveat that travels with the band is the baseline arm's severe ill-conditioning
  (~3e8 directional curvature), worded as **a property of fitting a pinhole model to refracted
  data — expected, not a defect, and explicitly not a reason to qualify the accuracy claim**. It
  is stated **paired with** the converged-baseline finding, so a reader cannot read
  ill-conditioning as under-convergence — the exact misreading this project's own documents already
  made once.
- **D-17:** **Label `optimality` now, FIX-04 style.** `optimality_stage3_interface_optimization`
  ships in `benchmark_grid.csv` and `benchmark_grid.tex` to Zenodo, where a reader meets a
  volatile (43× at a fixed solution), block-incomparable (three Coleman-Li scaling regimes),
  magnitude-dependent quantity with no caveat. The probe calls this "the same shape as MF-17,"
  which FIX-04 addressed by labelling. Attach the caveat where the number ships. Pre-freeze is the
  last moment this can land.
- **D-18:** The four committed Phase 23 documents carrying the falsified pin-mechanism get
  **supersession headers pointing at the probe FINDINGS.md, bodies untouched** —
  `23-VALIDATION.md:72-74`, `23-RESEARCH.md:76`, `23-01-PLAN.md:103`, `23-01-SUMMARY.md:153`. This
  is the pattern already chosen for `19.1-E2-FRAMESET-PROVENANCE.md`: a supersession header, not an
  edit, so the phase record stays honest about what was believed when.
- **D-19:** The **Huber knee objection is CLOSED by measurement** — the check was run during this
  discussion, not deferred into the plan. See
  `.planning/probes/2026-08-17-huber-knee/FINDINGS.md`.

  **Measured at `054d753`:** re-tuning the baseline arm to Finding 6's symmetric rule
  (`f_scale = 3 x median|r|` → 2.8332 interface, 1.8522 intrinsic) moves E1's z_rmse ratio by
  **−1.09% at the deepest test point (123.87× → 122.52×)**, and by at most 6.83% anywhere. E1's
  committed seed band is 97–178×, a ~±30% spread, so the effect is an order of magnitude inside
  the noise floor. The risk direction was right — the baseline does fit slightly better when fairly
  tuned (mean z_rmse −2.12%) — and the magnitude is negligible. The untouched refractive arm
  reproduced the control **bit-for-bit** (`max|abs change|` = 0.000e+00), which is what validates
  the attribution. One pass lands within 5% of the rule's fixed point, so no second iteration is
  needed.

  **Consequence for planning: this is no longer a plan task.** There is no measurement to schedule,
  no artifact to produce, and no verification criterion. What remains is **one recorded sentence in
  the DEGEN-05 verdict**, stating the objection was measured and closed with the sign and
  magnitude, citing the probe. Combined with the optimality probe's Finding 4, both fairness
  objections against E1's comparison are now answered in E1's favour — one on convergence, one on
  loss tuning.

  **Do not** change the library's `f_scale`. Nothing measured says the symmetric rule is better,
  only that the choice does not matter at the scale of E1's claim. Re-tuning stays post-submission.

  *Implementation seam, recorded for whoever picks the re-tuning up later:* the two passes want
  different values (2.83 vs 1.85), but `PipelineConfig.loss_scale` (`schema.py:335`) is a **single
  field feeding both**, reaching `interface_estimation.py:543` and `refinement.py:356` via
  `pipeline.py:1025,1274`. `optimize_interface` and `joint_refinement` take `loss_scale`
  separately, so a direct caller can differentiate the passes; the config path cannot. E1 hardcodes
  `1.0` at `e1_refractive_comparison.py:755, 881, 1124`.

  *Cost datum for the planner:* a full E1 single-seed run is **400 s of solver time** (refractive
  88.6 + 60.1 s; non-refractive 158.0 + 93.3 s). Useful for sizing any further E1 work; it is the
  cheapest solve in the suite.

### Claude's Discretion

- Exact column names and dtypes of the per-observation table, and the CSV header/metadata
  mechanism used to carry the provisional + truncation stamps.
- The config key's exact name and where it sits in `schema.py`.
- Plan decomposition and commit granularity (subject to D-20's one-commit-per-requirement habit
  established in Phases 23/24).
- Whether the classifier is a function or a small module inside `experiments/_degeneracy.py`.

### Folded Todos

- **`2026-08-15-classify-the-198-unprojectable-observations.md`** (DEGEN-04) — nobody knows what
  the production rig's 198 unprojectable observations are; the manuscript is about to disclose the
  count. Carries the instrumentation design, the hook-point sizing argument, the retired obliquity
  bucket, and the driver/gate registration clause. **This phase's primary requirement.**
- **`2026-08-14-decide-whether-e1-may-carry-absolute-accuracy-claims.md`** (BAND-01) — add the
  `noise_std` axis so E1's promoted absolute-accuracy numbers carry a stated domain. Carries the
  settled level set, the `n_cameras` skip, the P1 probe results, and the `normal_fixed` collision
  note. **This phase's second requirement.**
- **`2026-08-15-decide-degeneracy-gate-scope-for-real-rig-runs.md`** (criterion 2) — the deferred
  policy call that waits on the classification. Folded because D-04 settles it on mechanism.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Requirement sources (read first)

- `.planning/todos/pending/2026-08-15-classify-the-198-unprojectable-observations.md` — DEGEN-04 in
  full: the NaN inventory, the retired obliquity bucket, the hook-point ~1000× sizing table, the
  log-raw-classify-offline rule, the E2-only full-population `h_q` scope, and the
  register-with-the-driver clause. **Read the whole file, including both dated appendices.**
- `.planning/todos/pending/2026-08-14-decide-whether-e1-may-carry-absolute-accuracy-claims.md` —
  BAND-01 in full: the settled decision, the level set and why 0.5 px stays, the plumbing note, the
  "Do not" list, the P1 probe measurements, and the `normal_fixed` collision.
- `.planning/todos/pending/2026-08-15-decide-degeneracy-gate-scope-for-real-rig-runs.md` — the gate
  policy question, the authored-vs-given rationale, and why the 0.268% denominator argument no
  longer holds.
- `.planning/ROADMAP.md` § Phase 25 — the four success criteria, including criterion 4's rewrite.
- `.planning/REQUIREMENTS.md` — DEGEN-04 (`:84`), DEGEN-05 (`:87`, with the why-not-DEGEN-02 note),
  BAND-01 (`:180`).

### The optimality / convergence evidence (DEGEN-05)

- `.planning/probes/2026-08-17-optimality-decomposition/FINDINGS.md` — **the settled position.**
  Findings 1–9 plus "Net position across all three probes". Criterion 4 says this question is
  answered and must **not** be re-derived.
- `.planning/probes/2026-08-17-huber-knee/FINDINGS.md` — **closes Finding 6's open item**, the last
  outstanding fairness objection to E1's comparison. Measured, null: ~1% on the headline ratio
  against a ~±30% seed band. Cite it in the DEGEN-05 verdict; do not re-run it.
- `.planning/phases/23-experiment-correctness-fixes/23-01-SUMMARY.md` § Evidence — where DEGEN-05
  originated (the unexplained 92.78 vs 0.0247 gap).

### Phase 24's shipped instrumentation (build on this, do not duplicate it)

- `src/aquacal/calibration/_observability.py:60-240` — the cause/fate/stage vocabularies,
  `DISCARD_KEYS` (32), the raising accessors, and the "two independent marginals, never a cross
  product, never additive" rule. **The per-observation joint is explicitly DEGEN-04's, i.e. this
  phase's.**
- `src/aquacal/calibration/_optim_common.py:680-880` — `compute_residuals`' existing
  `degeneracy_breakdown_out` sink, its D-06b allocate-only-when-requested discipline, and the
  hot-path prohibition. The detail sink extends this call, not the cost function.
- `src/aquacal/core/refractive_geometry.py:25-33, 660-780` — the four `NAN_REASON_*` constants and
  the write sites; `h_q = Q[:,2] - z_int` at `:675`; nothing written inside the Newton loop.
- `experiments/_degeneracy.py` — `write_degeneracy_breakdown`, the sidecar precedent the classifier
  writer should mirror.
- `.planning/phases/24-degeneracy-instrumentation/24-VERIFICATION.md` — what actually shipped, the
  adjudicated E1 deviation, and the one open warning (WR-02).

### Downstream coupling (this phase's outputs must be registered)

- `.planning/todos/pending/2026-08-15-make-the-suite-driver-cover-every-invocation.md` — DRIVER-01;
  every schema- or value-changing fix adds its outputs to the driver's stage list and the
  completeness gate's expected-artifact list.
- `.planning/todos/pending/2026-08-15-suspend-programmatic-check-for-reshaped-artifacts.md` — the
  hand-verification sheet; Phase 24 already appended a `## Phase 24 additions` section. Add the
  Phase 25 expectations (the per-observation table, the `noise_std` column, the 640-row count) the
  same way.
- `.planning/ROADMAP.md` § Phase 26 criterion / § Phase 27 criterion 6 — Phase 26 depends on this
  phase precisely because DEGEN-04 emits a table and needs a driver-passed flag; Phase 27 must
  register both.

### Standing constraints

- `CLAUDE.md` — coordinate conventions, `interface_distance` semantics, and the **"never let a
  subagent background a long run"** policy. **The local instrumented E2 (D-01) is a 48–87 min run
  and is therefore the orchestrator's job, never an executor's.** Always `python -u`, always
  detached (`nohup` + `disown`).
- `.planning/knowledge-base.md` § Known Issues — the executor-stall root cause.
- `.planning/geometry.md` § 4.3 — `water_z` semantics.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets

- **`compute_residuals`' `degeneracy_breakdown_out` sink** (`_optim_common.py:686`) — the detail
  sink is a sibling parameter on the same call, filled in the same `if record_degeneracy:` block
  that already reads `nan_reason[invalid]` and `unextendable`. The cause and fate for every flagged
  row are **already computed**; the per-observation work is emitting them alongside the geometry
  rather than only reducing them.
- **`refractive_project_batch(..., nan_reason_out=...)`** — the per-point cause array, allocated
  only when a breakdown is requested. `h_q`, `r_q` and `h_c` are all computed on the same path
  (`refractive_geometry.py:675`, `:681`, and `h_c = water_z - C_z`).
- **The two post-solve call sites** — `interface_estimation.py:619` and `refinement.py:431`, each a
  dedicated residual evaluation at `result.x` whose only purpose is counting. Both already pass
  `invalid_count_out` and `degeneracy_breakdown_out`, and both already receive `discard_stage`.
- **`experiments/_degeneracy.py:write_degeneracy_breakdown`** — the sidecar-writer precedent,
  already called from E1/E5/E7.
- **`e1_refractive_comparison.py:_run_band`** (`:958`) and `run_seed_band` — the band harness the
  `noise_std` axis extends; `merge_band_columns` (`:490`) already handles the EXP2/EXP3 merge.
- **`e1_refractive_comparison.py:438`** — already passes `scenario.noise_std` for test-set
  detections, which is why the override (D-11) gets the evaluation set for free.

### Established Patterns

- **The library holds no key strings and no bucket names.** `_optim_common.py` fills a plain dict;
  the caller maps it onto `DISCARD_KEYS`. D-06 extends this to the taxonomy.
- **Opt-in out-parameters, zero cost when `None`.** D-06b: the reason array is allocated only when
  a breakdown is requested, so the solve's thousands of residual calls pay one identity test. The
  detail sink must hold the same line.
- **Closed vocabularies with raising accessors.** An unknown key means someone added a site without
  declaring it.
- **Band CSVs gain columns; fixed-contract CSVs never do.** D-19.4-14 precedent. `exp1_band.csv`
  gains `noise_std`; `exp1_parameter_errors.csv`, `exp2_depth_generalization.csv` and
  `exp3_xy_vs_z_anisotropy.csv` are read byte-for-byte by the external figures repository.
- **One commit per requirement, none mixing two** (D-20, held through Phases 23 and 24).

### Integration Points

- `compute_residuals` → the two post-solve sites → `experiments/_degeneracy.py` writer → the
  sidecar, and (E2 only) the full-population `h_q` table.
- The new config field → `schema.py` → `run_calibration_from_config` → the residual call.
- `pipeline.py`'s output dir → the always-written `degenerate_observations.csv` sidecar beside
  `diagnostics.json`.
- `_observability.py` + `e4_benchmark_grid.py` + `e6_generalization_sweep.py` guard blocks → the
  gate-scope rationale text (D-04).
- Both new artifacts + the `noise_std` column → the Phase 26 driver stage list, the completeness
  gate's expected-artifact list, and the hand-verification sheet.

</code_context>

<specifics>
## Specific Ideas

- **The `h_q <= 0` bucket, stated precisely for the classifier's docstring:** `h_q = Q_z - z_int`
  is the corner's depth below the **estimated** water surface in the +Z-down world frame. Positive
  = submerged. `h_q <= 0` means the corner is at or above the interface, so no refracted path
  exists and the projector returns NaN tagged `NAN_REASON_ABOVE_INTERFACE`. It is a statement about
  the **estimate**, not about reality — both `Q_z` and `z_int` are free parameters, so solver
  excursion reaches it too. It is evaluated **at the solution**, which is precisely why
  `19.3-ORCHESTRATOR-NOTES.md` §4 misread the `ideal` preset by comparing a solution-state count
  against a ground-truth statement.
- **Why (a) is expected to dominate**, for the pre-registered expectation: (c) `h_c <= 0` is dead
  for E2 by measurement (`h_c` = 1.0472–1.1125 m across all 13 cameras); obliquity/TIR is refuted
  twice over (`refract_ray` holds the only `sin_t_sq > 1` check and has **zero callers in `src/`**,
  and the Newton solve gives θ_w < 48.61° by construction for this direction of travel, confirmed
  by `realistic` projecting 31,680 corners cleanly at chord incidences up to 61.5°). The positive
  signal: `reconstruction_errors.csv` shows **31 of 7,762 validation corners (0.40%) reconstructing
  up to 51.7 mm above the interface, concentrated in 2 of 52 frames** — same board, operator and
  session, and the right order against 0.27%.
- **The `optimality` label's content** (D-17), from the probe's net position: volatile at a fixed
  solution (92.78 → 2.16 across restarts, 43×); not comparable across parameter blocks (three
  Coleman-Li regimes — `v = 1` unbounded, `v ≈ 700` wide-bounded intrinsics, `v ≈ 2e-12` pinned);
  and magnitude-dependent in reliability — large values are trustworthy (92.78 real to 5 s.f.),
  small ones are not (0.001146 against a 3-point reference of 0.001655, 44% disagreement), so
  **differences between two small optimality values carry no information**.

</specifics>

<deferred>
## Deferred Ideas

- **The `f_scale` re-tuning itself.** D-19's measurement ran and closed the objection (~1% on the
  ratio). Actually changing the library's robust-loss knee remains an estimator-design change and
  is post-submission — and now with no evidence it would help. The per-pass `loss_scale` seam
  noted in D-19 is the implementation constraint if it is ever picked up.
- **WR-02**, Phase 24's open reviewer warning (zero-denominator / all-zero-cause edge case renders
  a misleading quiet warning and a spurious "dominant cause"). Tracked in
  `.planning/todos/pending/2026-08-17-close-open-phase-24-review-warnings.md`; not this phase.
- **The distinct-vs-summed count question.** The published 198 is a cross-stage sum with possible
  double-counting. The distinct count is recoverable from the frozen per-observation table in
  Phase 29 — not from the provisional probe, per D-02.

### Reviewed Todos (not folded)

- `2026-08-15-repackage-and-reupload-the-zenodo-archive.md` — RUN-05, Phase 29.
- `2026-08-13-e4-aggregator-hardcodes-e2-benchmark-path.md` — FIX-05, Phase 23 (complete).
- `2026-08-15-archive-stale-outputs-before-the-run-purge-them-after.md` — DRIVER-04, Phase 26.
- `2026-08-15-correct-stale-strings-in-e2-and-the-synthetic-generator.md` — FIX-06, Phase 23
  (complete).
- `2026-08-15-make-the-suite-driver-cover-every-invocation.md` — DRIVER-01, Phase 26. Referenced
  here only as the registration target for this phase's outputs.
- `2026-08-15-suspend-programmatic-check-for-reshaped-artifacts.md` — DRIVER-03, Phase 26. Same.

</deferred>

---

*Phase: 25-degeneracy-classification-claim-licensing*
*Context gathered: 2026-08-17*
