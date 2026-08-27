# Phase 25: Degeneracy Classification & Claim Licensing - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-08-17
**Phase:** 25-degeneracy-classification-claim-licensing
**Areas discussed:** DEGEN-04 delivery boundary, Per-observation artifact & the h_q flag, BAND-01 noise-axis shape, DEGEN-05 verdict & the optimality caveat

---

## DEGEN-04 delivery boundary

### Q1 — Answer or capability?

| Option | Description | Selected |
|--------|-------------|----------|
| Capability now, answer at Phase 28 | Ship the sink, classifier and a pre-registered expectation; the frozen run produces the answer. Cleanest provenance, but the manuscript sentence and gate-scope call stay pending until Phase 29 against the 08-21 deadline. | |
| Local investigation run now | One instrumented E2 locally under OpenCV 4.13 as a probe artifact, not the suite record. 48–87 min; answers the question before the freeze. | ✓ |
| Capability + conditional decisions | Ship the capability and pre-commit downstream decisions as an outcome-keyed rule Phase 29 evaluates. | |

**User's choice:** Local investigation run now.

### Q2 — Which run is the manuscript-facing finding?

| Option | Description | Selected |
|--------|-------------|----------|
| Probe answers, Phase 28 confirms | Probe's classification recorded now as the finding; Phase 29 checks agreement and updates counts. | |
| Probe is provisional only | Probe settles the mechanism and nothing numeric; no count reaches MANUSCRIPT-FINDINGS.md or the disclosure. Phase 29's frozen table is the sole source of every number. | ✓ |
| Probe is the record | Treat the probe as authoritative; Phase 28 emits without re-reading. | |

**User's choice:** Probe is provisional only.
**Notes:** Preserves the single-source-of-truth premise the milestone exists to establish. The mechanism travels; the numbers do not.

### Q3 — Gate-scope decision (criterion 2)

**First response was a request for explanation**, not a selection: *"explain. what is the h_q<=0 bucket, and why do we expect it to dominate?"* Answered with the definition (`h_q = Q_z − z_int`, depth below the **estimated** surface, evaluated **at the solution**), the elimination argument for buckets (b) and (c), the positive `reconstruction_errors.csv` signal, and why the gate argument rests on mechanism rather than count. Re-asked with that framing:

| Option | Description | Selected |
|--------|-------------|----------|
| Decide on mechanism, with a tripwire | Synthetic-only lands now with the rationale written at the gate, plus a recorded trigger if bucket (b) is materially populated in Phase 29. | ✓ |
| Decide on mechanism, unconditionally | Same decision, no tripwire. | |
| Stays blocked, recorded as blocked | Criterion 2's explicit-blocked branch. | |
| Decide only if (a) is overwhelming | Threshold the probe (e.g. ≥90%) and treat it as a gate rather than an input. | |

**User's choice:** Decide on mechanism, with a tripwire.

### Q4 — Probe run isolation

| Option | Description | Selected |
|--------|-------------|----------|
| Probe dir, provisional-stamped | Under `.planning/probes/<date>-degeneracy-classification/` with `--out` pointed there; table carries a provisional + sha stamp; FINDINGS.md and table both committed. | ✓ |
| Probe dir, findings only committed | Same isolation, raw table untracked. | |
| Scratch tree, nothing committed | One-line verdict, outputs deleted. | |

**User's choice:** Probe dir, provisional-stamped.

---

## Per-observation artifact & the h_q flag

### Q1 — Where the sink and classifier live

| Option | Description | Selected |
|--------|-------------|----------|
| Raw sink in library, classifier in `experiments/` | Library emits raw geometry only; bucketing and CSV writer in `experiments/_degeneracy.py`. Library never spells a bucket name. | ✓ |
| Both in the library | Labelled rows emitted directly; freezes a taxonomy revised twice this week into `src/`. | |
| Standalone `classify_degeneracy.py` | A new one-purpose script; a new driver stage and a new file for the freeze. | |

**User's choice:** Raw sink in library, classifier in `experiments/`.

### Q2 — What an ordinary user gets

| Option | Description | Selected |
|--------|-------------|----------|
| Sidecar, always written when non-empty | `degenerate_observations.csv` beside `diagnostics.json`; a clean rig writes nothing. | ✓ |
| Into `diagnostics.json` | No new artifact, but inflates a summary-level file. | |
| Sidecar, opt-in for library users | Keeps the default surface unchanged; loses the free-diagnosis property. | |

**User's choice:** Sidecar file, always written when non-empty.

### Q3 — Threading the full-population `h_q` flag

| Option | Description | Selected |
|--------|-------------|----------|
| Config schema field | Consumed by `run_calibration_from_config`; E2 reaches it via `config_paper.yaml`, so the flag state lands in run provenance. | ✓ |
| `run_calibration` kwarg only | Clean public YAML, but E2 runs the config path and the flag would not appear in provenance. | |
| Experiment CLI flag | Visibly an experiment concern; provenance must capture the invocation, not the config. | |

**User's choice:** Config schema field.

### Q4 — Row-cap behaviour

| Option | Description | Selected |
|--------|-------------|----------|
| Truncate, flag in the artifact, warn | Count stays exact from the Phase 24 counters; `truncated: true` plus the true count stamped in the artifact's own header. | ✓ |
| Truncate silently, warn only | The warning lives in a log nobody reads overnight. | |
| Reservoir sample | Faithful under truncation, non-deterministic unless seeded, for a backstop nobody expects to hit. | |

**User's choice:** Truncate, flag in the artifact, warn.

---

## BAND-01 noise-axis shape

### Q1 — Threading the noise level

| Option | Description | Selected |
|--------|-------------|----------|
| Override `scenario.noise_std` before the solve | No public signature change; gets the eval set free via `e1:438`; validated by the P1 probe. | ✓ |
| New `create_scenario` argument | Cleaner API, but a public change two phases before a freeze. | |
| Both | Most flexible, largest surface to freeze. | |

**User's choice:** Override `scenario.noise_std` before the solve.

### Q2 — Scope of the axis

| Option | Description | Selected |
|--------|-------------|----------|
| Band-only | Lives inside `_run_band`; only `exp1_band.csv` gains a column. | ✓ |
| Band-only plus a `--noise` override | One more invocation shape for the driver and freeze to cover. | |
| General axis across all modes | Moves single-seed artifact values and reopens frozen contracts. | |

**User's choice:** Band-only.

### Q3 — Attributing the two-factor movement

| Option | Description | Selected |
|--------|-------------|----------|
| An emitter that writes the comparison | Phase 27 criterion 5 requires an emitter for every §3-facing number. | |
| Derived in Phase 29 from committed CSVs | Reproducible but hand-asserted. | |
| Recorded as a note, not a number | State that the 0.5 px row is the clean isolator; produce no delta. | ✓ (via free text) |

**User's choice (free text):** *"the old version with the interface normal fixed isn't something we'll publish, so just make a note for the sake of an agent that might get confused over the number moving."*
**Notes:** This settles more than the option itself — because nothing normal-fixed is published, no §3-facing number depends on the attribution, so Phase 27's emitter requirement does not apply here. The note is anti-confusion for a future agent, not evidence.

### Q4 — Where the stated domain lives

| Option | Description | Selected |
|--------|-------------|----------|
| Script header + MANUSCRIPT-FINDINGS.md | Header beside the D-19.3-17 demotion note, plus an MF-NN derivation for the manuscript session. | ✓ |
| Script header only | No filed derivation for the manuscript session. | |
| Also stamped into the artifact | Licence travels with the data; one more schema field to freeze. | |

**User's choice:** Script header + MANUSCRIPT-FINDINGS.md.

---

## DEGEN-05 verdict & the optimality caveat

### Q1 — The un-caveated `optimality` shipping to Zenodo

| Option | Description | Selected |
|--------|-------------|----------|
| Label it now, FIX-04 style | Attach the caveat where the number ships; pre-freeze is the last moment. | ✓ |
| Record the caveat, defer the labelling | On the record, but the un-caveated scalar still reaches the archive. | |
| Out of scope, file for post-submission | Neither DEGEN-05 nor BAND-01 covers artifact labelling. | |

**User's choice:** Label it now, FIX-04 style.

### Q2 — The four Phase 23 documents carrying a falsified mechanism

| Option | Description | Selected |
|--------|-------------|----------|
| Supersession headers, bodies untouched | The `19.1-E2-FRAMESET-PROVENANCE.md` pattern; keeps the record honest about what was believed when. | ✓ |
| Correct the text in place | Cleanest for a cold reader; erases the trail showing how the error was caught. | |
| Leave them | Four documents keep asserting a wrong mechanism with nothing pointing away. | |

**User's choice:** Supersession headers, bodies untouched.

### Q3 — Wording the ill-conditioning caveat

| Option | Description | Selected |
|--------|-------------|----------|
| Property of the comparison, not a defect | Paired with the converged-baseline finding so ill-conditioning cannot be read as under-convergence. | ✓ |
| Neutral, measurement only | Maximally conservative, but invites the misreading this project already made once. | |
| Also state the reliability rule | Adds the magnitude-dependent trust rule, superseding "never quote beyond 1 s.f.". | |

**User's choice:** Property of the comparison, not a defect.
**Notes:** The magnitude-dependent reliability rule was not adopted as part of the band caveat, but it is captured in CONTEXT.md `<specifics>` as content for the D-17 `optimality` label, where it belongs.

### Q4 — The Huber knee

**First response was a challenge to the premise:** *"but didn't the probe indicate that an improved f_scale was unlikely to materially improve the result?"* Checked against the text — it did not. Finding 4 settled convergence **under the current `f_scale`**; Finding 6 is explicitly open and predicts nothing about magnitude, and its "reproduces the status quo almost exactly" refers to the **refractive** arm (3 × 0.3357 = 1.007 vs 1.0), which is what makes the rule non-disruptive to the method — not a claim about the baseline, which moves to ~2.8 / ~1.9. Re-asked with the sign of the bias stated (a too-tight knee down-weights 29–48% of baseline residuals, so the current setting flatters E1's ratio):

| Option | Description | Selected |
|--------|-------------|----------|
| Note it in the verdict, file the todo | A considered recorded position; work is post-submission. | |
| Cheap single-seed measurement now | One baseline solve at `f_scale = 3 × median\|r\|`, seed 42, compared on accuracy. Same shape as the P1 probe. | ✓ |
| Out of scope, no verdict mention | Keeps the verdict to what the probes settled. | |

**User's choice:** Cheap single-seed measurement now.

---

## Claude's Discretion

- Exact column names and dtypes of the per-observation table; the header/metadata mechanism
  carrying the provisional and truncation stamps.
- The config key's name and placement in `schema.py`.
- Plan decomposition and commit granularity (within the one-commit-per-requirement habit).
- Whether the classifier is a function or a small module in `experiments/_degeneracy.py`.

## Deferred Ideas

- The `f_scale` re-tuning itself — an estimator-design change, post-submission regardless of what
  the measurement shows.
- WR-02, Phase 24's open reviewer warning (zero-denominator edge case) — tracked in its own todo.
- The distinct-vs-summed count question — recoverable only from the frozen table in Phase 29.

---

## Post-discussion: D-19 resolved before planning (2026-08-17)

The user asked whether the Huber-knee check should go into the plan or be run immediately as a
one-off. Run-now was chosen on the grounds that the outcome changes the plan's shape rather than
sitting inside it: a null result collapses D-19 to a recorded sentence, a material result would be
a scope change to BAND-01 and the DEGEN-05 verdict. Planning first would have meant hedging both
branches.

**Ran it. Null result.** ~1% on the headline ratio against a ~±30% seed band. Full method,
self-checks and numbers in `.planning/probes/2026-08-17-huber-knee/FINDINGS.md`. D-19 in
CONTEXT.md was rewritten from "run a measurement" to "closed by measurement, record one sentence",
and the deferred-ideas entry updated accordingly.

Two data points folded into CONTEXT.md for the planner while this was open: the measured E1
single-seed cost (400 s of solver time), and the per-pass `loss_scale` seam — the interface and
intrinsic passes want different `f_scale` values but `PipelineConfig.loss_scale` is one field
feeding both.
