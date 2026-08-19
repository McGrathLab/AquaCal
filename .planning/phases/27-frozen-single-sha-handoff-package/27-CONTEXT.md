# Phase 27: Frozen Single-Sha Handoff Package - Context

**Gathered:** 2026-08-19
**Status:** Ready for planning

<domain>
## Phase Boundary

Everything the Linux machine needs — code, driver, gates, environment, and the E2 configuration —
is frozen at **one sha**, and that sha is **proven runnable on the target itself** before the run
starts. RUN-01, and the six success criteria in `.planning/ROADMAP.md` § Phase 27.

The phase closes when: one tag names the frozen sha; a clean clone of it runs the driver's dry-run
and a short real stage plus the gate roll-up **on the Linux target**; the environment is captured
by the run manifest plus a lockfile artifact; every §3-facing number is either emitter-backed or
explicitly classified as
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
  `git describe --tags --long --dirty` in the run manifest (P26-D-45), and Gate 3's cross-artifact sha
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

- **D-04: A second tag is a normal outcome, not a failure signal — but nothing forces one.** The
  original reason it was mandatory (a lockfile committed inside the sha but capturable only after
  the env is built) was removed by D-13's revision. A second tag now happens only if verification
  actually finds a defect, which is exactly when it should.

### Where the freeze is verified

- **D-05: Verification happens ON THE LINUX TARGET.** Clone the tag, build the environment, run the
  dry-run harness (`RUN_EXPERIMENT_SUITE_DRY_RUN`) end-to-end, then one **short real stage** and the gate
  roll-up. **The short stage must be `fd_jacobian`** — `suite_expectations.json` gives it
  `depends_on: ["preflight"]` and `est_hours 0.05`. It is the ONLY dependency-free short stage:
  `e3` looks cheap at 0.005 h but carries `depends_on: ["e2_production"]` from 26-12's edge, and
  `e2_production` is 0.8–1.45 h, so scheduling `e3` drags E2 in behind it. This is the only venue that can catch a Linux-only
  failure, and it is where § E's OpenBLAS confirmation has to happen anyway. This closes Phase 26's
  **P26-D-35**, which deferred Linux-side portability verification to exactly here.

- **D-06: SSH to the target is available and plans may drive it directly** from this machine —
  `ssh`/`scp` in plan steps is in scope, so a defect is found and fixed in one loop rather than a
  paste-back cycle. **The connection details (host/alias, user, key) are not yet recorded here and
  must be obtained from the author before the first on-target step.**

- **D-07: No on-target step may be one an executor has to background.** `CLAUDE.md`'s policy is
  written about subagents — an executor whose Bash call passes the 600 s ceiling is auto-backgrounded
  and never returns — so every SSH invocation in a plan must finish inside that ceiling. The dry run and the short stage are chosen for
  exactly this reason; nothing in Phase 27 launches anything of the 15–26 h class.

### The E2 data path — and a defect found during this discussion

- **D-08: The IMAGE set (not the video set) is already on the target**, for **both intrinsics and
  extrinsics**. Nothing multi-GB is transferred in this phase; Phase 27 verifies what is there.

- **D-09: DEFECT — the pre-flight frameset check cannot pass against an image set.**
  `experiments/run_experiment_suite.sh:955-957` builds `present` with `p.is_file()` and sums
  `p.stat().st_size`. Against directory paths every `is_file()` is False, `present` is empty, and
  the probe exits **2 = ABSENT**, so the driver refuses with *"the E2 frameset is ABSENT (P26-D-14) ...
  use `--skip-e2`"* — which would make the entire re-run **synthetic-only**. The library is not
  affected: `src/aquacal/io/detection.py:134` auto-selects `ImageSet` when the path is a directory.
  **This is a driver-only defect and it is exactly the criterion-4 class: found before the freeze,
  fixed inside it.**

- **D-10: Make the pre-flight path-kind agnostic — and change NOTHING else about the check.**
  Accept a file OR a directory: `p.exists()` in place of `p.is_file()`, and a recursive byte sum in
  place of `p.stat().st_size`. Keep the two existing assertions exactly as they are — 13 paths
  present, `min_total_bytes: 4000000000` cleared. **Do NOT add a per-camera frame-count
  expectation:** that would mean inventing an expected number nobody has measured, and
  `usable_frames: 262` cannot serve as one (it is post-detection and does not decompose into
  `calibration_frames: 200` + `validation_frames: 52`). How a directory tree sums against the byte
  floor must still be **measured on the target, not assumed** — if 4.35 GB of frames does not clear
  4 GB, that is a manifest number to re-derive from measurement, not a check to weaken. Preserve the
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

- **D-13: Capture the lockfile as a RUN ARTIFACT beside the run manifest, not as a pre-freeze
  commit.** `pip freeze` from the verified target environment, written next to
  `_run_manifest.py`'s output at run time, plus a prose note naming the Python version and the
  OpenBLAS build. Rationale for the shape: `experiments/_run_manifest.py` **already** emits
  `python_version`, `numpy_version`, `scipy_version`, `opencv_version`, `opencv_build`,
  `installed_distribution_version`, `cpu_model`, `cpu_count_logical`, `ram_total_bytes`, `os`,
  `kernel`, `machine`, `git_sha`, `git_describe` and `git_dirty` — every version that moves a
  number is already captured. The lock adds only the transitive set (matplotlib, pandas, tqdm),
  which is worth recording but not worth a freeze-window commit and a forced second tag.
  **Do NOT tighten `pyproject.toml`'s pins** — that file is the shipped package's contract, and
  pinning NumPy exactly there degrades AquaCal for every pip user to serve one internal run.
  Today only `opencv-python==4.13.*` is hard-pinned (for a measured reason: 4.14.0 detected 1.95%
  fewer corners and moved reconstruction RMSE +7.8%); `numpy` is unpinned and `scipy>=1.16`.

- **D-14: Pin BLAS threads for the CONCURRENT stages ONLY; leave the serial timing stages at the
  library default.** Export a per-stage cap (`OMP_NUM_THREADS` / `MKL_NUM_THREADS` /
  `OPENBLAS_NUM_THREADS`) for stages the pool runs 4–5 wide; export nothing for `e4`, `e4_repeat`,
  `e2_timing`, `e2_memory`. The pin is justified where 4–5 processes compete: no thread limit is set
  anywhere in `src/` or `experiments/` today, and the probe measured a solve holding a **median
  0.99 cores of 20** (mean 1.20, p95 2.01, peak 2.56), so a small cap costs nothing there.
  **It is NOT justified on the timing stages:** every historical measurement was taken unpinned,
  including `results_linux32gb/e2_timing/` and `results_linux32gb/e4/benchmark_grid.csv` (3 ledger
  rows) and the nine-cell grid `main.tex:285` names. Pinning them would silently change what is
  being timed. **The run manifest must record BOTH regimes explicitly** — the cap value and the
  stage list it applies to — or the numbers become uninterpretable. The stage list already carries
  a `concurrency` attribute, so the split is read from the manifest, not hardcoded in the shell.

- **D-15: `SUITE_WORKERS` stays at P26-D-52's 4–5. Confirm RSS on the target; do not re-tune.** The
  4–5 figure came from measured RSS classes (30 frames < 1 GiB; 100 frames 2.7–3.5 GiB — E6's
  band, all 102 rows at `n_frames=100`; 200 frames 9.3–11.3 GiB) against ~31 GiB, with
  at-most-one-200-frame-stage already enforced by the scheduler. § C's warning stands: a short
  stage's RSS is a **floor** and its headroom figure an **upper bound**, never a setting to copy.

### Emitter coverage for every §3-facing number (criterion 5)

- **D-16: Do a mechanical cross-check of all 131 ledger rows and produce a written report — no
  gate.** For every named artifact, confirm the frozen code has an emitter that writes it. A gate
  is explicitly rejected: its input (`numbers-ledger.tsv`) lives outside the repo and is the
  author's to edit, which is the "gate that cannot pass" shape plan 23-02 warned about.
  **Start from D-17's result, not from scratch** — the row-level triage below was already done
  during this discussion, so the remaining work is confirming an emitter for the 27 named artifacts
  and resolving three candidate rows, not re-classifying 131 rows.

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
  machine; and `RL-determinism` is unregenerable by construction because **P26-D-42 turned `e6_repeat2`
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
  Plus the roll-up FAIL, which is their aggregate and clears with them. P26-D-49 already says smoke
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

### Criterion 6 — Phase 25's outputs registered with the driver

- **D-24: VERIFY, do not build.** ROADMAP criterion 6 asks that Phase 25's outputs — the
  per-observation classification table and E2's `h_q` logging flag — be registered with the driver,
  because Phase 26 built the driver before that work was necessarily complete. **It appears already
  satisfied:** `experiments/suite_expectations.json` lists `degenerate_observations.csv` and
  `all_observation_depths.csv` among its 62 artifacts, alongside the six
  `e{1,5,7}[_seed_band]_degeneracy_breakdown.json` sidecars. The task is therefore a short
  confirmation — every Phase 25 artifact appears in the manifest, with the right profile tags and
  the conditional-emission rules from Phase 25's D-08/D-09/D-10 honoured — and a stated finding if
  one is missing. Do not re-derive or re-register what is already there.

### Standing constraints carried in from Phase 26 — do NOT re-litigate

- Grid cuts **P26-D-40** (E6 `scale` axis dropped), **P26-D-41** (E1 noise axis = 352 rows, **not** the
  640/960 in Phase 25's D-21 — any gate asserting 640 is wrong) and **P26-D-42** (`e6_repeat2` OFF).
- **P26-D-52** selective concurrency, with its three hard constraints: `e6_repeat1` and `e6_band` never
  overlap; at most one 200-frame-class stage in flight; concurrent stages share
  `experiments/results/` so artifact filenames must be disjoint.
- **P26-D-50** — every pre-flight refusal prints its exact override flag; nothing aborts once stage 1
  has begun. **P26-D-01/P26-D-03** — gates record, pre-flight aborts.
- `e7_band` stays an **unmeasured range**. A settling probe was offered and **DECLINED** on
  2026-08-18. Do not schedule one.
- The corrected serial estimate is **~22–26 h** at Windows-box speed (~15–16 h pooled), dominated
  by `e6_band` at ~8.9 h. § A's ~50 h figure is superseded and wrong.
- One commit per requirement (D-14 of Phase 23, D-20 of Phase 25), held through Phases 23–26.

### Claude's Discretion

- The exact tag naming scheme beyond `rerun-freeze-NN`, and the lockfile's filename and location.
- The precise thread-cap value for the concurrent stages in D-14 (bounded by the probe: a solve
  holds ~1 core, p95 2.01).
- How the emitter cross-check report is formatted, and where the D-19 classification note lives.
- Whether the byte floor itself needs re-deriving once directory sums are measured on the target
  (D-10) — the check's shape is fixed, the number may not be.

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
  **§ D (de-scoping, P26-D-43..P26-D-50) and § E (the runtime correction and P26-D-51/P26-D-52 concurrency) are
  mandatory**. Where § D/E conflict with earlier decisions in that file, the amendment wins.
  P26-D-35 is the explicit hand-off of Linux-side verification to this phase.
- `.planning/phases/26-full-suite-driver-handoff-readiness/26-10-SUMMARY.md` — the P26-D-33 acceptance
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

- **The dry-run harness** (`_dry_run_active` / `_dry_run_stub`, `RUN_EXPERIMENT_SUITE_DRY_RUN`,
  `RUN_EXPERIMENT_SUITE_DRY_RUN_CMD`) — every stage routes through it. This is D-05's primary on-target
  instrument: it exercises the full stage list and scheduler in seconds.
- **The scheduler is already Linux-safe by construction.** `_stage_worker` uses a sentinel file
  rather than `wait -n -p` *specifically* so the driver behaves identically on Git Bash and the
  Linux box (the code cites P26-D-35). Do not "improve" it back to `wait -n`.
- **The scheduler hardcodes no stage list.** `_load_stage_attributes` reads `depends_on`,
  `concurrency`, `frame_class` and `est_hours` from `suite_expectations.json` via a one-shot Python
  call emitting TSV, and **fatals** on a stage missing from the manifest. Manifest edits therefore
  propagate to the pool automatically.
- **`experiments/pre_rerun_baseline/` travels with the clone** — `--baseline-dir` needs no
  separate transfer, and E2's control and E3's tier diff keep working on the target.
  **CORRECTED 2026-08-19 (clone rehearsal):** the tracked content is **226 files, ~1.7 MB**, not
  76 MB. The 76 MB is the Windows working copy, which also holds 159 *gitignored* bulk artifacts
  (four 11 MB `exp2_spatial_errors.csv`, `interface_ablation_conditioning.npz`, the
  `results_e2_band` calibrations) excluded by explicit `.gitignore` entries. The functional claim
  still holds, verified by cloning the tag: E3's `--check` matched `code_constants.csv` and
  `newton_iterations.csv` from the clone, and E2's reproduction signal is `check_e2_band`'s
  numeric `real_rig_metrics.json` comparison — which is present. E2's `--check` itself compares
  only `camera_parameters.csv` (also present); `reprojection_residuals.csv` and
  `reconstruction_errors.csv` are DATA-01b-gitignored everywhere and ship only in Zenodo, which
  `e2_real_rig.py:538-552` already states.
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
  (P26-D-50). Gates record; the sticky `SUITE_FAILED` file carries verdicts to the final exit code —
  a *file*, not a shell variable, because concurrent stages are child processes.
- **`experiments/results/` is TRACKED**, so the run dirties its own working tree. This is why
  Phase 26 cut the dirty-tree refusal (P26-D-47) and it must not be reintroduced when the clone is
  made on the target.
- **One commit per requirement**, held through Phases 23–26.

### Integration Points

- Committed Linux config + path-kind-agnostic pre-flight (D-10/D-11) -> `_preflight_frameset` ->
  E2's four invocations -> E4's real-rig row (which silently drops without E2's `benchmark.json`).
- Manifest `profiles` retags (D-20) -> per-stage gate calls -> end-of-run roll-up -> smoke exit 0
  -> the on-target verification signal (D-05).
- Tag (D-01/D-03) -> `FROZEN_SHA` -> sha-derived state path -> run manifest's `git describe` (P26-D-45)
  -> Gate 3's single-sha assertion in Phase 29 (RUN-03).
- Lockfile artifact (D-13) + the two-regime thread record (D-14) -> run manifest -> Phase 29's
  provenance answer for "what produced this number".
- Emitter report (D-16) + frozen-row note (D-19) -> Phase 29's RUN-04 traceability -> Phase 30's
  dangling-reference audit.

</code_context>

<specifics>
## Specific Ideas

- **A green smoke is the point of fixing smoke.** D-20 is not tidiness: it is what makes D-05's
  on-target pass a usable signal. Twelve known reds and one new Linux red look identical at 3 a.m.
- **A frame count MIGHT be a better identity assertion than the byte floor — but the number is not
  known yet.** `min_total_bytes` exists only to separate the current archive from the retired
  4.3x-subsampled one (record 18645385, 60 usable -> 12 validation -> 1817 comparisons). A frame
  count would be sharper, but `usable_frames: 262` is a POST-DETECTION number and does not decompose
  into `calibration_frames: 200` + `validation_frames: 52` (that is 252), so it is not safe to read
  as a raw per-directory file count, and the manifest has no field for one. Adding a frame-count
  expectation means inventing a new expected number — do it only if the target measurement supports
  it, and never as a guess.
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
- **Rewriting the driver in Python** — Phase 26's P26-D-26, explicitly post-submission.
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

---

## Amendment 2026-08-19 — the target is reachable, and three findings that bind wave 5

Written after SSH access was established. **D-06's open item is CLOSED.**

### D-25: the target is reachable as the SSH alias `lab-pc`

Connection details live in the operator's `~/.ssh/config` and are deliberately NOT recorded here
(27-01's redaction rule). Plans and commands refer to the alias only. Key auth is configured with a
dedicated passphrase-free ed25519 key scoped to this host; the host's ed25519 fingerprint was
verified **out-of-band on the machine itself**, not accepted at a prompt.

Target facts, confirmed 2026-08-19: **Ubuntu 22.04.4 LTS**, kernel 6.8.0-136 x86_64, **32 logical
cores**, **31 GiB RAM** (28 GiB available), **662 GB free** on `$HOME`'s filesystem, and
**github.com is reachable** — anonymous `git ls-remote` on `McGrathLab/AquaCal` succeeds, so
27-12's clone of the frozen tag needs no credential on the target.

That confirms D-15: 32 cores and ~31 GiB is exactly the geometry the 4–5 worker pool and the
at-most-one-200-frame-stage rule were sized against. The 20 GiB pre-flight floor clears easily.

### D-26: ⚠ the existing env has OpenCV **4.14.0** — the version the pin exists to EXCLUDE

`~/anaconda3/envs/aquacal` holds Python 3.11.15, numpy 2.4.6, scipy 1.17.1, pandas 3.0.5 — and
**`cv2 4.14.0`**. `pyproject.toml` pins `opencv-python==4.13.*` for a measured reason recorded in
that file: 4.14.0 detects **1.95% fewer corners** and moves the paper's reconstruction RMSE by
**+7.8%** on the published real-rig dataset.

**27-12 must build a NEW environment at `opencv-python==4.13.*` rather than reuse this one.** Reusing
it would silently produce E2 numbers that disagree with the archive the paper cites. D-13's lockfile
must be captured from the NEW env, and its OpenCV line is the single most important row in it.

### D-27: ⚠ the env imports aquacal from a DIFFERENT checkout by absolute path

`site-packages/__editable__.aquacal-2.0.1.pth` contains the literal line
`<home>/PycharmProjects/AquaCal/src`. That checkout sits on branch
`experiments/linux32gb-rerun` at **`27c80e7`** — not the frozen sha, and not even the frozen branch.

**This is the worst failure mode available to this phase**, because it is silent: a run launched
from a fresh clone of the frozen tag would still `import aquacal` from `27c80e7`, while every
artifact's `git_sha` — derived by the driver from `git rev-parse HEAD` in the *cwd* — would stamp
the **frozen** sha. Artifacts would claim provenance they do not have. That is the F-001/F-002
fracture class this whole milestone exists to close, in a form no gate currently catches: Gate 3
asserts the shas AGREE, and here they would.

Binding on 27-12:

1. Create a **fresh conda env** for the frozen run; do not reuse `envs/aquacal`.
2. Install the frozen clone into it (`pip install -e .` from the clone, or a non-editable install)
   so the `.pth` resolves to the clone and nothing else.
3. **Assert it**, do not assume it: `python -c "import aquacal; print(aquacal.__file__)"` must
   print a path under the frozen clone, and this belongs in 27-12's acceptance criteria and in the
   run manifest's record.
4. Note the interaction with `PYTHONPATH` — the project's own knowledge base already records
   worktree runs resolving to the wrong source tree. Same defect, remote edition.

### D-28: `conda` is not on the PATH for non-interactive SSH

`~/anaconda3` exists, but conda is initialised in `~/.bashrc`, which a non-interactive `ssh host
'cmd'` never sources. Every remote command must call interpreters by **absolute path**
(`~/anaconda3/envs/<env>/bin/python`) or explicitly source conda first. A plan step that assumes a
bare `conda activate` works over SSH will fail in a way that reads like a missing install.

This also refines **D-12**: on the target, `GATE_PYTHON`'s detect-then-fallback chain must find the
frozen run's env by absolute path. If it falls through to bare `python`, it lands on system
**Python 3.10.12** — below `pyproject.toml`'s `requires-python = ">=3.11"` floor — and fails at
import rather than at a clear version check.

*Amended: 2026-08-19*

---

## Amendment 2026-08-19 (second) — D-12 is superseded on its middle rung

Written during wave 1 execution, after plan 27-01's measurements landed. **This supersedes D-12's
`GATE_PYTHON` half.** D-12's `E2_RELEASE_CONFIG` half is unchanged.

### D-29: the conda-env-by-name rung is DELETED, not case-fixed

D-12 specified `GATE_PYTHON` as: env override -> a conda env named `AquaCal` on either platform ->
bare `python`. Plan 27-01 measured the target and the middle rung is wrong twice over:

1. The env there is lowercase **`aquacal`**, and Linux is case-sensitive.
2. **Case-fixing it is worse than leaving it broken.** `~/anaconda3/envs/aquacal` is exactly the env
   D-26 excludes — it carries **OpenCV 4.14.0**, the version `pyproject.toml` pins *against* for a
   measured reason (1.95% fewer corners, +7.8% reconstruction RMSE). A rung that auto-discovers a
   conda env by name is a rung that can silently select the contaminated env.

**Auto-discovery by name is the defect; the case is incidental.** Plan 27-12 builds a fresh
`opencv-python==4.13.*` env for the frozen run, so rung 1 (`PRELAUNCH_GATE_PYTHON`, already present
at `run_experiment_suite.sh:402`) is the only rung that should ever fire on the target.

Binding on 27-08:

- **Delete** the conda-env-by-name discovery rung. Do not repair its case.
- Keep the `PRELAUNCH_GATE_PYTHON` override as the primary path; 27-12 sets it to the scratch env's
  absolute interpreter path (D-28: no bare `conda activate` over non-interactive SSH).
- The final fallback must **fail loudly, naming the override**, rather than falling through to bare
  `python`. On the target there is no `python` on PATH at all, so the current fallback dies with
  *command not found* — which reads as a broken driver rather than an unresolved interpreter.
- Per D-12's still-binding clause: this adds **no new pre-flight refusal**. The Git Bash box must
  keep working unchanged.

### D-30: the manifest must record BOTH interpreters, with an equality verdict

Found while resolving D-29. `GATE_PYTHON` is deliberately not the run interpreter — the comment at
`run_experiment_suite.sh:842` says so, because on the Windows dev box bare `python` is Anaconda base
and pre-flight must not be where that surfaces. But:

- every stage runs bare `python -u -m experiments.<mod>` (~25 call sites, `:1224`–`:1812`);
- the run manifest is written under `GATE_PYTHON` (`:882`).

So `python_version`, `numpy_version`, `scipy_version`, `opencv_version` and
`installed_distribution_version` describe **the tooling interpreter, not the one that computed the
numbers**, and nothing asserts the two agree.

Today they coincide on the target by accident: the `.exe` default fails, the chain falls back to bare
`python`, and in an activated shell that IS the run env. Repair the middle rung naively and they stop
coinciding — **the manifest would record 4.14.0 while the stages ran 4.13**.

That is the D-27 / F-001 fracture in a new form: artifacts claiming provenance they do not have,
with the git shas agreeing so Gate 3 stays green. It is in scope for this phase precisely because the
freeze window is where it is still cheap.

Binding on 27-05's manifest emitter and 27-08's driver work:

- Record `sys.executable` for **both** the gate interpreter and the stage interpreter.
- Record an explicit **equality verdict** between them, so a mismatch is visible in the manifest
  rather than silent.
- A mismatch is **recorded, not refused** — it is legitimate on the Windows dev box by design. This
  is a provenance record, not a fourth pre-flight refusal.

*Author's ruling, 2026-08-19. Amended: 2026-08-19.*
