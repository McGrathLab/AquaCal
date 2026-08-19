# Phase 27: Frozen Single-Sha Handoff Package - Context

**Gathered:** 2026-08-19
**Status:** Ready for planning

<domain>
## Phase Boundary

Everything the Linux machine needs — code, driver, gates, environment, and the E2 configuration —
is frozen at **one sha**, and that sha is **proven runnable on the target itself** before the run
starts. RUN-01, and the six success criteria in `.planning/ROADMAP.md` § Phase 27.

The phase closes when: one tag names the frozen sha; a clean clone of it runs the driver's dry-run
and a short real stage plus the gate roll-up **on the Linux target**; the environment is captured as
a committed lockfile; every §3-facing number is either emitter-backed or explicitly classified as
deliberately-frozen; and `--smoke` exits 0 so a Linux-specific failure is visible.

**Not in this phase:** the suite run itself (Phase 28), the post-run `--check` re-baselining and
gate verification (Phase 29), the archive purge and dangling-reference audit (Phase 30 / POST-03),
the Zenodo results package (RUN-05 / Phase 29), and any manuscript prose. The manuscript tree
`.../Thesis/Spinoffs/papers/aquacal/` — including `numbers-ledger.tsv` — is **read-only from this
repo**.

</domain>

<decisions>
## Implementation Decisions

### The freeze anchor and how the package travels

- **D-01: Push `experiments/full-suite-rerun` to `origin`, plus an annotated tag, and `git clone
  --branch <tag>` on the target.** The branch currently has **no upstream and is 218 commits ahead
  of `origin/main`** — nothing about this work is on GitHub, so this push is a prerequisite, not a
  detail. A real clone is what makes "clean checkout" (criterion 2) meaningful and keeps `.git`
  present, which the driver needs: `FROZEN_SHA` derivation, the sha-derived state-file path,
  `git describe --tags --long --dirty` in the run manifest (D-45), and Gate 3's cross-artifact sha
  assertion all read git.

- **D-02: The tag MUST NOT match `v*`.** Verified against the workflows, and this is the entire CI
  constraint: `.github/workflows/publish.yml` triggers on `push: tags: ['v*']` (PyPI);
  `release.yml` on `push: branches: [main]` (python-semantic-release); `test.yml` on push-to-main
  or PR-to-main. Pushing this branch plus a non-`v*` tag therefore **fires no workflow at all**.
  Name shape: `rerun-freeze-NN`.

- **D-03: New tag per freeze attempt; tags are never moved.** `rerun-freeze-01`, `-02`, ... each at
  a distinct sha. A defect found during verification means fix -> commit -> next tag -> re-verify.
  Abandoned tags stay as the audit trail. A force-moved tag would destroy the record of the failed
  attempt — the same shape as audit finding **F-002** (two commits sharing "1.8.0"), which this
  milestone exists to stop repeating.

- **D-04: At least two tags are expected by construction, not as a failure.** D-13's lockfile can
  only be captured *after* the target environment is built, and it must live *inside* the frozen
  sha. Plans must not treat a second tag as a defect signal.

### Where the freeze is verified

- **D-05: Verification happens ON THE LINUX TARGET.** Clone the tag, build the environment, run the
  dry-run harness (`RERUN_19_3_DRY_RUN`) end-to-end, then one **short real stage** (`e3` or
  `fd_jacobian`, minutes) and the gate roll-up. This is the only venue that can catch a Linux-only
  failure, and it is where § E's OpenBLAS confirmation has to happen anyway. This closes Phase 26's
  **D-35**, which deferred Linux-side portability verification to exactly here.

- **D-06: SSH to the target is available and plans may drive it directly** from this machine —
  `ssh`/`scp` in plan steps is in scope, so a defect is found and fixed in one loop rather than a
  paste-back cycle. **The connection details (host/alias, user, key) are not yet recorded here and
  must be obtained from the author before the first on-target step.**

- **D-07: `CLAUDE.md`'s never-background-a-long-run policy binds every on-target step.** Each SSH
  invocation must finish inside the tool ceiling. The dry run and the short stage are chosen for
  exactly this reason; nothing in Phase 27 launches anything of the 15–26 h class.

### The E2 data path — and a defect found during this discussion

- **D-08: The IMAGE set (not the video set) is already on the target**, for **both intrinsics and
  extrinsics**. Nothing multi-GB is transferred in this phase; Phase 27 verifies what is there.

- **D-09: DEFECT — the pre-flight frameset check cannot pass against an image set.**
  `experiments/run_experiment_suite.sh:955-957` builds `present` with `p.is_file()` and sums
  `p.stat().st_size`. Against directory paths every `is_file()` is False, `present` is empty, and
  the probe exits **2 = ABSENT**, so the driver refuses with *"the E2 frameset is ABSENT (D-14) ...
  use `--skip-e2`"* — which would make the entire re-run **synthetic-only**. The library is not
  affected: `src/aquacal/io/detection.py:134` auto-selects `ImageSet` when the path is a directory.
  **This is a driver-only defect and it is exactly the criterion-4 class: found before the freeze,
  fixed inside it.**

- **D-10: Make the pre-flight path-kind agnostic** — accept a file OR a directory, summing
  directory bytes recursively and counting frames per camera. The **frame count is the stronger
  assertion**; `min_total_bytes: 4000000000` was calibrated against the 4.35 GB published archive
  and how a directory tree sums must be **measured on the target, not assumed**. Preserve the
  existing distinction between ABSENT (exit 2 -> `--skip-e2`) and MISMATCH (exit 3 ->
  `--allow-frameset-mismatch`), and keep reading the expected numbers from
  `experiments/suite_expectations.json` — never from a shell literal (that is how FIX-06's stale
  numbers survived).

- **D-11: Commit a Linux image-set release config into the frozen sha**, with `frame_step: 1` and
  `max_calibration_frames: 200`. Note the discrepancy that motivated this: the current off-repo
  config at `C:/Users/tucke/Desktop/Aqua/AquaCal/release_calibration/config.yaml` has
  **`frame_step: 30`**, while the manifest's verified signature is *"13 x 262 extrinsic frames at
  `frame_step: 1` / `max_calibration_frames: 200`"* — so the Desktop config is **not** the one that
  produces the signature pre-flight asserts. Committing the target's config puts the exact inputs
  inside the frozen sha instead of leaving provenance outside the artifact (the F-001 shape).

- **D-12: Both Windows literals become detect-then-fallback, with a loud resolution log.**
  `GATE_PYTHON` (`:402`, currently `$HOME/anaconda3/envs/AquaCal/python.exe`): env override ->
  a conda env named `AquaCal` on either platform -> bare `python`, printing which one it resolved
  to. `E2_RELEASE_CONFIG` (`:374`, currently the Desktop path): defaults to the newly committed
  in-repo Linux config, with the Desktop path reachable only via `SUITE_E2_RELEASE_CONFIG`. The
  Git Bash box must keep working unchanged — it is where defects get diagnosed. No new pre-flight
  refusal is added for either (Phase 26 § D cut three; do not add a fourth).

### Environment specification

- **D-13: Capture an exact lockfile from the verified target environment and commit it inside the
  frozen sha** (e.g. `experiments/run-environment.lock`), plus a prose note naming the Python
  version and the OpenBLAS build. The environment then carries the same provenance as the code.
  **Do NOT tighten `pyproject.toml`'s pins** — that file is the shipped package's contract, and
  pinning NumPy exactly there degrades AquaCal for every pip user to serve one internal run.
  Today only `opencv-python==4.13.*` is hard-pinned (for a measured reason: 4.14.0 detected 1.95%
  fewer corners and moved reconstruction RMSE +7.8%); `numpy` is unpinned and `scipy>=1.16`.

- **D-14: Pin BLAS thread counts in the driver and record the value in the run manifest.** Export a
  fixed per-stage cap (`OMP_NUM_THREADS` / `MKL_NUM_THREADS` / `OPENBLAS_NUM_THREADS`). No thread
  limit is set anywhere in `src/` or `experiments/` today. The probe measured a solve holding a
  **median 0.99 cores of 20** (mean 1.20, p95 2.01, peak 2.56), so a small cap costs nothing and
  removes the risk of five concurrent stages each grabbing 32 threads on the target. It also makes
  the timing stages' numbers a property of a **stated** configuration.

- **D-15: `SUITE_WORKERS` stays at D-52's 4–5. Confirm RSS on the target; do not re-tune.** The
  4–5 figure came from measured RSS classes (30 frames < 1 GiB; 100 frames 2.7–3.5 GiB — E6's
  band, all 102 rows at `n_frames=100`; 200 frames 9.3–11.3 GiB) against ~31 GiB, with
  at-most-one-200-frame-stage already enforced by the scheduler. § C's warning stands: a short
  stage's RSS is a **floor** and its headroom figure an **upper bound**, never a setting to copy.

### Emitter coverage for every §3-facing number (criterion 5)

- **D-16: Do a mechanical cross-check of all 131 ledger rows and produce a written report — no
  gate.** For every named artifact, confirm the frozen code has an emitter that writes it. A gate
  is explicitly rejected: its input (`numbers-ledger.tsv`) lives outside the repo and is the
  author's to edit, which is the "gate that cannot pass" shape plan 23-02 warned about.

- **D-17: The walk is already partly done and its shape is known.** `numbers-ledger.tsv` holds
  **131 rows / 27 distinct artifacts** — 78 `KEEP-VERIFIED`, 46 `EDIT` (all `applied`), 7
  `KEEP-FROZEN-5f`. **21 rows have an empty `artifact` column; 11 of those are non-`EDIT`.** Most
  of the 11 are legitimately not emitter-backed — `M-L271-noise` / `M-L268-noise` are pixel-noise
  *inputs*, `M-L245-spacing` / `M-L276-spacing` are apparatus facts, `RL-idx-seawater` /
  `RL-idx-temp` are physical constants, `M-L246-frames` is a frame count. The genuine candidates
  are **`M-L281-19mm`** (refractive Z-RMSE at 2.5 m, body), **`M-L281-135x`** (depth-axis
  improvement ratio, body) and **`RL-determinism`** (E6 paired-repeat determinism). The 7
  `KEEP-FROZEN-5f` rows all name `real_rig_metrics.json` — they have an emitter and are frozen
  behind the OpenCV 4.13 pin rather than re-derived.

- **D-18: A genuine gap is closed by ADDING AN EMITTER, then re-freezing.** Criterion 5's stated
  remedy; Phase 29 is too late. A new emitter is **additive** — it writes a new artifact rather
  than reshaping an existing one — so it carries far less risk than the schema edits § D cut. Each
  such fix costs one new tag under D-03.

- **D-19: Write an in-repo note classifying every ledger row this run will NOT regenerate,
  with the sha and machine each was measured at.** Three rows cite `archive/e6-2026-08-02-...` and
  `archive/e2-2026-07-30-...` pre-fix trees; six cite `results_linux32gb/...` from the earlier
  machine; and `RL-determinism` is unregenerable by construction because **D-42 turned `e6_repeat2`
  off**. This turns "stale reference" into "stated provenance" before Phase 30 purges the trees, and
  hands Phase 30 its dangling-reference list for free.

### The smoke profile (Phase 26 open item #1)

- **D-20: Make the whole `smoke` profile truthful so a smoke pass can exit 0 — manifest/gate-side
  only, no experiment code changes.** This is load-bearing given D-05: with 12 known reds, a
  Linux-specific failure is invisible in the noise. Three classes, all pre-existing, from
  `26-10-SUMMARY.md`:
  1. **4 failures** — `structural_scaling.csv`, `e5_provenance.json` (x2 + completeness) and
     `fd_jacobian_accuracy.json` are listed under `profiles: ["smoke","full"]` but the smoke code
     paths never write them (`e3_derived_quantities.py:1106-1126` runs tiers 1–3 and returns
     without calling `_write_tier4`; the `_run_smoke` paths of the other two return before their
     sidecar writes). **Retag as `full`-only.**
  2. **5 failures** — E6 `gate4_optimality` on four `e6_configs/*.json` (collapsed smoke solve) and
     `cameras axis missing [12, 16]; found [8]`. **Make the axis expectation profile-dependent and
     stop asserting optimality at smoke scale.**
  3. **2 failures** — E4's smoke path writes no `benchmark_grid.csv`. **Make that artifact
     `full`-only.**
  Plus the roll-up FAIL, which is their aggregate and clears with them. D-49 already says smoke
  asserts **existence only** — this makes the manifest match that rule rather than inventing a new
  one.

- **D-21: `e7_focal_standoff` and `e4_repeat` stay skipped under `--smoke`, as DECLARED
  REDUCTIONs.** `e7_focal_standoff` has no `--smoke` branch and reads a hardcoded path; `e4_repeat`
  refuses `--smoke` for both `--cell` and `--splice-repeat`. Adding smoke branches is
  freeze-window code for diagnostic-only benefit. **The handoff note must state explicitly that
  these two invocation lines are never rehearsed — that is the F-001 class, and naming it is the
  mitigation.**

### The other two Phase 26 open items — both now IN SCOPE

- **D-22: Fix `is_stage_complete` (`run_experiment_suite.sh:669`) — resume must not skip a stage
  that ran AND FAILED.** It matches a completion line and ignores the exit-code column, so a
  crashed-then-resumed run silently drops that stage. On a single-shot 15–16 h run this is the
  failure mode most likely to cost the whole thing. The end-of-run roll-up still catches the
  missing artifact — loud, but late. The fix is a one-column `awk` change. **This reverses the
  2026-08-18 deferral; the author reopened it on 2026-08-19 in light of D-05/D-06.**

- **D-23: Fix `reconstruction_bootstrap.py:56`** — it hardcodes
  `experiments/results/real_rig_metrics.json` instead of honouring `--out`. Correct in production,
  wrong under `--smoke`. Now matters more because D-20 makes the smoke tree the target's
  verification signal, and it removes a hardcode of the same class as `e7_focal_standoff`'s.

### Standing constraints carried in from Phase 26 — do NOT re-litigate

- Grid cuts **D-40** (E6 `scale` axis dropped), **D-41** (E1 noise axis = 352 rows, **not** the
  640/960 in Phase 25's D-21 — any gate asserting 640 is wrong) and **D-42** (`e6_repeat2` OFF).
- **D-52** selective concurrency, with its three hard constraints: `e6_repeat1` and `e6_band` never
  overlap; at most one 200-frame-class stage in flight; concurrent stages share
  `experiments/results/` so artifact filenames must be disjoint.
- **D-50** — every pre-flight refusal prints its exact override flag; nothing aborts once stage 1
  has begun. **D-01/D-03 of Phase 26** — gates record, pre-flight aborts.
- `e7_band` stays an **unmeasured range**. A settling probe was offered and **DECLINED** on
  2026-08-18. Do not schedule one.
- The corrected serial estimate is **~22–26 h** at Windows-box speed (~15–16 h pooled), dominated
  by `e6_band` at ~8.9 h. § A's ~50 h figure is superseded and wrong.
- One commit per requirement (D-14 of Phase 23, D-20 of Phase 25), held through Phases 23–26.

### Claude's Discretion

- The exact tag naming scheme beyond `rerun-freeze-NN`, and the lockfile's filename and location.
- The precise thread-cap value in D-14 (bounded by the probe: a solve holds ~1 core, p95 2.01).
- How the emitter cross-check report is formatted, and where the D-19 classification note lives.
- Whether the D-10 frame-count check replaces or supplements the byte floor — decide from what is
  measured on the target.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Requirement sources (read first, in full)

- `.planning/ROADMAP.md` § Phase 27 — the six success criteria, and the "Depends on 23, 24, 25, 26"
  rationale. **Criterion 5's parenthetical matters:** the ledger classification is manuscript-side
  and the author's; it is named as a dependency, not imported as a task.
- `.planning/REQUIREMENTS.md` — RUN-01 (`:186`), and RUN-02..05 (`:188-197`) for what this phase
  must NOT do.
- `.planning/STATE.md` — Phase 26's three deliberately-open items; **two of them (D-22, D-23) are
  now in Phase 27's scope**, so the STATE text is history, not a live deferral.

### Phase 26's decisions, which bind this phase

- `.planning/phases/26-full-suite-driver-handoff-readiness/26-CONTEXT.md` — the whole file, but
  **§ D (de-scoping, D-43..D-50) and § E (the runtime correction and D-51/D-52 concurrency) are
  mandatory**. Where § D/E conflict with earlier decisions in that file, the amendment wins.
  D-35 is the explicit hand-off of Linux-side verification to this phase.
- `.planning/phases/26-full-suite-driver-handoff-readiness/26-10-SUMMARY.md` — the D-33 acceptance
  pass, the precise location of all 12 pre-existing smoke failures (D-20's inventory), and what the
  smoke pass does **not** prove (26-12's dependency edge cannot be demonstrated under `--smoke`).
- `.planning/probes/2026-08-18-solver-concurrency/FINDINGS.md`, `summary.json`, `samples.csv` —
  the CPU/RSS measurements behind D-14 and D-15. Read before touching the stage model.

### The code being changed

- `experiments/run_experiment_suite.sh` — `:374` (`E2_RELEASE_CONFIG`), `:402` (`GATE_PYTHON`),
  `:669` (`is_stage_complete`), `:913-1000` (`_preflight_frameset`, incl. the `is_file()` defect at
  `:955-957`), and the scheduler at `:1875+`. Its header encodes the two abort rules — read it.
- `experiments/suite_expectations.json` — `profiles`, `profile_semantics`, `stages` (20 stages with
  `depends_on` / `concurrency` / `frame_class` / `est_hours`), `artifacts`, and `preflight`
  (`frameset.cheap_check`, `free_space_floor_gib: 20`, `overrides`). D-20 edits the `profiles` tags
  here; D-10 reads `cheap_check` from here.
- `experiments/check_rerun_gates.py` — Gates 1–4, `_check_git_sha_consistency` (`:1732`),
  `run_all_gates` (`:1768`). D-20's class-2 changes live near the per-experiment checkers.
- `experiments/reconstruction_bootstrap.py:56` — D-23's hardcoded output path.
- `experiments/e3_derived_quantities.py:1106-1126` — the smoke branch that returns before
  `_write_tier4`, i.e. why `structural_scaling.csv` is never written under smoke.
- `src/aquacal/io/detection.py:134` — `_create_frame_source` selects `ImageSet` for a directory.
  This is why D-09 is a driver defect and not a library one. **Do not change it.**
- `pyproject.toml` / `requirements.txt` — the OpenCV 4.13 pin and its recorded rationale. D-13
  explicitly does not touch these.

### CI, and why the tag name is constrained

- `.github/workflows/publish.yml` — `push: tags: ['v*']` -> PyPI. **The reason D-02 exists.**
- `.github/workflows/release.yml` — `push: branches: [main]` -> python-semantic-release.
- `.github/workflows/test.yml` — push-to-main / PR-to-main only.

### Manuscript-side, READ-ONLY from this repo

- `C:\Users\tucke\OneDrive - Georgia Institute of Technology\Thesis\Spinoffs\papers\aquacal\numbers-ledger.tsv`
  — 131 rows; columns `id, file, line_hint, locator, current_text, target_text, quantity, artifact,
  derivation, verdict, lockstep_group, lockstep_value, status, forbid_global, note`. D-16/D-17's
  input. **Never edit it.**
- `Spinoffs/papers/aquacal/AUDIT-goal4.md` Pass A — findings **F-001** (six shas, not one anchor)
  and **F-002** (two commits sharing "1.8.0"). D-01/D-03 exist to close them.

### Standing constraints

- `CLAUDE.md` — **never let a subagent background a long run** (binds D-07 and every SSH step),
  always `python -u`, Git Bash `/c/...` path conventions.
- `.planning/knowledge-base.md` § Known Issues — the executor-stall root cause, and plan 23-02's
  "a verification gate that cannot pass is worse than no gate" (the reason D-16 is a report, not a
  gate).

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets

- **The dry-run harness** (`_dry_run_active` / `_dry_run_stub`, `RERUN_19_3_DRY_RUN`,
  `RERUN_19_3_DRY_RUN_CMD`) — every stage routes through it. This is D-05's primary on-target
  instrument: it exercises the full stage list and scheduler in seconds.
- **The scheduler is already Linux-safe by construction.** `_stage_worker` uses a sentinel file
  rather than `wait -n -p` *specifically* so the driver behaves identically on Git Bash and the
  Linux box (the code cites D-35). Do not "improve" it back to `wait -n`.
- **The scheduler hardcodes no stage list.** `_load_stage_attributes` reads `depends_on`,
  `concurrency`, `frame_class` and `est_hours` from `suite_expectations.json` via a one-shot Python
  call emitting TSV, and **fatals** on a stage missing from the manifest. Manifest edits therefore
  propagate to the pool automatically.
- **`experiments/pre_rerun_baseline/` is 76 MB and TRACKED** — `--baseline-dir` travels with the
  clone for free. No separate transfer, and E2's ~1e-8 control and E3's tier diff keep working on
  the target.
- **The preflight override vocabulary already exists** — `--skip-e2`, `--allow-frameset-mismatch`,
  `--allow-nonempty-out`, `--allow-low-disk`, `--allow-gate-precheck-failure`, mirrored in the
  manifest's `preflight.overrides`. D-10 reuses these; it must not invent a new one.
- **`check_rerun_gates.py`'s `GateResult` / `_load_json` / `_load_csv`** — D-20's changes should
  keep emitting `GateResult`s so the verdict-block formatting is unchanged.

### Established Patterns

- **Expected values live in `suite_expectations.json`, never in a shell literal.** FIX-06's stale
  numbers survived precisely because they were a code comment. D-10 must keep reading `cheap_check`
  from the manifest.
- **Pre-flight is the only place permitted to abort**, and every refusal prints its override flag
  (D-50). Gates record; the sticky `SUITE_FAILED` file carries verdicts to the final exit code —
  a *file*, not a shell variable, because concurrent stages are child processes.
- **`experiments/results/` is TRACKED**, so the run dirties its own working tree. This is why
  Phase 26 cut the dirty-tree refusal (D-47) and it must not be reintroduced when the clone is
  made on the target.
- **One commit per requirement**, held through Phases 23–26.

### Integration Points

- Committed Linux config + path-kind-agnostic pre-flight (D-10/D-11) -> `_preflight_frameset` ->
  E2's four invocations -> E4's real-rig row (which silently drops without E2's `benchmark.json`).
- Manifest `profiles` retags (D-20) -> per-stage gate calls -> end-of-run roll-up -> smoke exit 0
  -> the on-target verification signal (D-05).
- Tag (D-01/D-03) -> `FROZEN_SHA` -> sha-derived state path -> run manifest's `git describe` (D-45)
  -> Gate 3's single-sha assertion in Phase 29 (RUN-03).
- Lockfile (D-13) + thread pin (D-14) -> run manifest -> Phase 29's provenance answer for "what
  produced this number".
- Emitter report (D-16) + frozen-row note (D-19) -> Phase 29's RUN-04 traceability -> Phase 30's
  dangling-reference audit.

</code_context>

<specifics>
## Specific Ideas

- **A green smoke is the point of fixing smoke.** D-20 is not tidiness: it is what makes D-05's
  on-target pass a usable signal. Twelve known reds and one new Linux red look identical at 3 a.m.
- **The frame count is a better identity assertion than the byte floor.** `min_total_bytes` exists
  only to separate the current archive from the retired 4.3x-subsampled one (record 18645385,
  60 usable -> 12 validation -> 1817 comparisons). Against directories, counting 13 x 262 frames
  says more than summing bytes.
- **Existence and row count are still not correctness** (inherited from Phase 26). A green
  completeness gate on the target proves the wiring, never the numbers.
- **`--smoke` cannot catch a wrong `--config` path or a bad production YAML** — pre-flight's
  frameset identity check is the only thing that covers that blind spot, which is precisely why
  D-09 is a serious find rather than a cosmetic one.
- **Do not weaken Gate 3** to accommodate a stage at a different commit. Gate 3 failing is the
  system working.
- The author's framing from Phase 26 still governs: *achieving a clean, accurate baseline run*
  beats *protecting against every possible future eventuality*. Every item here earns its place by
  protecting **this** run.

</specifics>

<deferred>
## Deferred Ideas

- **Adding `--smoke` branches to `e7_focal_standoff` and `e4_repeat`** — D-21 leaves them skipped;
  post-submission if ever.
- **Rewriting the driver in Python** — Phase 26's D-26, explicitly post-submission.
- **Splitting `e6_band` across processes by seed** — attacks the ~8.9 h critical path directly but
  needs a merge step and provenance handling inside the experiment. Phase 26 declined it
  deliberately; still declined.
- **Measuring `e7_band`'s true runtime** — offered and DECLINED 2026-08-18. It stays a stated range.
- **Post-run `--check` re-baselining and restoring automated checking** — Phase 29, part of
  DRIVER-03's same obligation.
- **The archive purge and the dangling-reference audit** — Phase 30 / POST-03. D-19's note is
  written here to feed it, but the purge itself is not this phase.
- **The Zenodo results package split** — RUN-05, Phase 29, before the 2026-08-21 submission.
- **Reconciling `normal_fixed` defaults between config and library**, and **`water_z`'s hardcoded
  [0.01, 2.0] m bound** — both explicitly POST-SUBMISSION todos.
- **Parallelizing the test suite with pytest-xdist** and **reverting `model_profile` from `quality`
  to `balanced`** — tooling todos, not Phase 27.

### Reviewed Todos (not folded)

No pending todo maps to RUN-01. The 21 todos `todo.match-phase 27` surfaced all matched on generic
keywords ("phase", "run", "before") and belong to completed Phases 23–26 (FIX-01..06, DEGEN-01..04,
DRIVER-01..04, BAND-01), to Phase 29 (`2026-08-15-repackage-and-reupload-the-zenodo-archive.md`,
RUN-05), to Phase 30, or to post-submission. **Phase 27's obligations come from ROADMAP § Phase 27's
six criteria and REQUIREMENTS.md RUN-01, not from a todo file.**

</deferred>

---

*Phase: 27-frozen-single-sha-handoff-package*
*Context gathered: 2026-08-19*
