# Project Retrospective

*A living document updated after each milestone. Lessons feed forward into future planning.*

## Milestone: v1.6 — Refinement API

**Shipped:** 2026-03-09
**Phases:** 3 | **Plans:** 6 | **Commits:** 20

### What Was Built
- `refine_calibration()` API with PointCorrespondence input — bundle adjustment over extrinsics + water_z
- Optional intrinsics refinement (fx/fy/cx/cy) and robust loss functions (Huber/Cauchy)
- Validation pipeline: holdout reprojection error, triangulation consistency, extrinsics drift
- `RefinementResult` contract with accept/reject recommendation
- 45 tests covering input validation, optimization, extensions, and validation

### What Worked
- Single-function parameterized design (refine_intrinsics, loss, validate as params) — clean API surface
- Local pack/unpack/sparsity/bounds matching _optim_common patterns but separate — no coupling to board-pose code
- Phase 15 validation wired as optional post-step inside refine_calibration() — zero API complexity for callers
- Verification + UAT caught no issues — clean implementation across all 3 phases

### What Was Inefficient
- Phase 15 SUMMARY.md files not generated despite work being complete (UAT/verification passed)
- All 3 phases executed in a single day — velocity tracking per-plan is less meaningful at this pace
- Phase numbering continued from v1.4 (13-15) which caused init tool to count all 15 phases for this milestone

### Patterns Established
- Any-fail accept/reject logic for validation — conservative by default, callers can override
- Holdout split before optimization for unbiased validation metrics
- Per-camera CameraDrift dataclass for structured drift reporting
- f_scale parameter for controlling robust loss inlier threshold

### Key Lessons
1. Parameterized extensions on a single function scale well — 3 phases of features added without API surface explosion
2. Validation as an integrated step (not a separate API call) ensures callers get quality metrics by default
3. scipy's native loss parameter (Huber/Cauchy) is cleaner than custom loss wrappers

### Cost Observations
- Model mix: Primarily sonnet for execution, opus for orchestration
- Sessions: Multiple within a single day
- Notable: Entire milestone completed in ~1 day — well-scoped phases with clear requirements

---

## Milestone: v2.0 — Publication Prep

**Closed:** 2026-08-15 (planned as "v1.9"; shipped as v2.0.0/v2.0.1)
**Phases:** 10 executed of 12 | **Plans:** 106 | **Commits:** 673

### What Was Built
- Experiment observability hooks: per-stage calibration dumps, per-iteration optimizer traces,
  conditioning diagnostics, standalone `evaluate_calibration`, seed threading everywhere
- Benchmark instrumentation: solver diagnostics, opt-in peak memory, live column-group counts,
  and a `benchmark.json` on every run
- Per-camera interface ablation mode, with the shared default proven bit-unchanged
- A consolidated `experiments/` suite — one implementation per experiment, one CLI contract,
  and a provenance table mapping every paper artifact to script, data file, and figure generator
- Two geometry corrections (19.3 board protrusion, 19.4 per-camera water surfaces) and the
  uncertainty bands (19.5) that established what may be claimed from the results
- A regenerated, republished Zenodo archive that reproduces §3 from downloadable bytes

### What Worked
- **One frozen git sha per production queue.** Risk-first stage ordering, detached, no commit
  between launch and completion. Held across three separate overnight queues; every artifact's
  recorded SHA is trustworthy because of it.
- **Refusing accuracy claims without a seed band (D-19.3-17).** Applied strictly it was painful
  — it demoted numbers that were already written down — but it is why nothing shipped that a
  reviewer could overturn with a different seed.
- **Bit-identity gates as the default proof of inertness.** Every "this change is safe" claim in
  the milestone was an exact-equality test, not an argument. It caught a real Rule-1 bug in
  17-05 that two earlier plans had both missed.
- **Reading the defect before believing the metric.** The 19.4 root cause (1.42 px modelling
  error against a 0.4–0.9 px residual) was found by auditing ground truth, not by chasing the
  number that looked wrong.

### What Was Inefficient
- **674 commits went unpushed.** Two latent CI failures — Linux ULP anchors and a Windows psutil
  assumption — surfaced together on release day and turned two trivial fixes into an emergency.
- **Five decimal phases inserted mid-milestone.** Each was justified, but the milestone as
  defined (build tooling) was not the milestone as executed (fix and re-measure the science).
  The scope grew because each fix revealed the next.
- **Experiment defects accumulated faster than they were fixed** once the deadline dominated.
  That backlog is the entire premise of the next milestone.
- **Subagent stalls on backgrounded runs** cost multiple hours across 19.2–19.4 before the
  policy landed: the full suite is the orchestrator's job, never an executor's.
- **Measuring the noise floor kept being skipped**, three separate times, once producing a
  decomposition of pure noise that nearly reached the manuscript.

### Patterns Established
- Long runs: `nohup` + `disown`, never the harness's background mode (killed at ~35–50 min)
- Verify subagent claims against git and the filesystem, never against their return text
- Every worktree executor must `export PYTHONPATH="$(pwd)/src"` or pytest tests `main`'s code
- Opt-in diagnostic hooks follow the D-32/E3 pattern: off by default, proven bit-identical when unset
- Manuscript findings land as MF-NN entries in `.planning/MANUSCRIPT-FINDINGS.md`; the assistant
  records manuscript work, the user executes it
- Rank a pre-release audit by lock-in, not severity — a metadata error that a DOI freezes outranks
  a bug that can be patched next week

### Key Lessons
1. **Push often.** The cost of not pushing is not linear; it lands all at once, on release day.
2. **A single-seed number is not a result.** Ask what varies before quoting any delta.
3. **Chase the sign before believing a magnitude** — 80% of one 18.9 mm error turned out to be gauge.
4. **One commit per breaking change**, or semantic-release renders one of seven in the CHANGELOG.
5. **The fix that unblocks the next phase is often a side effect.** 19.4's interface fix made the
   clearance floor seed-invariant, which is the only reason 19.5's bands were affordable.
6. **Never attribute a runtime change to a code fix.** The ~2× swing measured in 19.4 tracked the
   machine, not the diff.

### Cost Observations
- Model mix: opus for orchestration and all production-queue supervision; sonnet for executors
- Sessions: many, across 22 days
- Notable: three overnight production queues (6 h 02 m, ~9 h 30 m, 16 h 31 m). The 19.5 queue ran
  at 0.97× of nominal after 19.4 ran at 1.6× — the difference was budgeting from a *measured*
  prior queue rather than an estimate

---

## Cross-Milestone Trends

### Process Evolution

| Milestone | Phases | Plans | Key Change |
|-----------|--------|-------|------------|
| v1.2 MVP | 6 | 20 | Initial project setup, packaging, docs |
| v1.4 QA & Polish | 6 | 10 | QA verification, terminology cleanup, visuals |
| v1.6 Refinement API | 3 | 6 | Feature development — new API surface |
| v2.0 Publication Prep | 10 (of 12) | 106 | Science under deadline — five phases inserted mid-milestone as each fix revealed the next |

### Cumulative Quality

| Milestone | New Tests | Key Additions |
|-----------|-----------|---------------|
| v1.2 | Existing suite | CI/CD, packaging, tutorials |
| v1.4 | User verification | CLI QA, doc audit, visual diagrams |
| v1.6 | 45 refinement tests | refine_calibration API, validation pipeline |
| v2.0 | Suite 799 → 1,817 passing | Observability hooks, benchmark records, per-camera ablation, provenance-complete experiment suite with uncertainty bands |

### Top Lessons (Verified Across Milestones)

1. Well-scoped milestones (3-6 phases) execute faster and cleaner than large ones — v2.0 is the
   counter-example that proves it: 12 phases, five of them inserted mid-flight
2. Verification and UAT at phase level catches issues before milestone completion
3. Keeping planning artifacts (REQUIREMENTS, ROADMAP) milestone-scoped prevents unbounded growth
4. Prove inertness with an exact-equality test, not an argument (v2.0)
5. Push often — unpushed work hides platform failures until they all land at once (v2.0)
