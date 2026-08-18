# Phase 26: Full-Suite Driver & Handoff Readiness - Context

**Gathered:** 2026-08-18
**Status:** Ready for planning

<domain>
## Phase Boundary

One driver invocation covers the **entire** experimental suite — nothing left for the Linux
machine to discover is missing — with one truthful run manifest, a decided `--check` contract, and
a clean output tree to run into. DRIVER-01 through DRIVER-04.

- **DRIVER-01** — `rerun_19_3.sh` is renamed to `run_experiment_suite.sh` and extended to cover
  every invocation: the four `--seeds` band stages (E1, E5, E6, E7), E2's four distinct
  invocations, and the three orphan scripts (`e7_focal_standoff_analysis`,
  `reconstruction_bootstrap`, `fd_jacobian_accuracy`) with their ordering constraints made
  structural. Plus a new **completeness gate** and a rewritten `experiments/README.md` §2.
- **DRIVER-02** — one suite-level run manifest capturing the execution environment, with the
  `aquacal_version` and OpenCV-build recording defects closed.
- **DRIVER-03** — the `--check` contract across the deliberate re-base, delivered as a
  machine-readable **expectation manifest** plus a rendered hand-verification sheet.
- **DRIVER-04** — every pre-existing output tree moved aside (never deleted) in a committed step.

**Not in this phase:** the suite run itself (Phase 28), the freeze and portability verification
including any Linux-side smoke (Phase 27 / RUN-01), the post-run `--check` re-baselining
(Phase 29), the archive **purge** (Phase 30 / POST-03), and any manuscript prose. The manuscript
tree `Spinoffs/papers/aquacal/` is **read-only from this repo**.

</domain>

<decisions>
## Implementation Decisions

### Completeness gate — the one thing neither existing tool does

- **D-01:** A completeness FAILURE **never aborts the queue**. D-19.3-18's rationale holds — E1,
  E5, E6 and E4 are independent and their measurements are still wanted. Instead a **sticky
  failure flag** makes the driver's **final exit non-zero**, with a loud terminal summary block
  naming every missing or short artifact.

  *Rationale:* this project's injury has never been "we kept running after a gate failed" — it has
  been **a run that exited 0 and looked green while a band CSV was never produced at all** (F-001).
  An exit code that cannot lie kills that class without discarding hours of valid work.

- **D-02:** Completeness is checked at **all three** points, because each catches a distinct class:
  **pre-flight** (preconditions, before stage 1), **after each stage** (that stage's own artifacts
  and row counts, at the existing `check_rerun_gates.py` invocation point), and an **end-of-run
  roll-up** over the whole tree. The roll-up is the check whose absence produced F-001.

- **D-03 (derived, not asked):** **Pre-flight failure ABORTS.** It runs before stage 1, so nothing
  is lost, and the whole point is trading minutes for nine-plus hours. D-01's "never abort" governs
  stages 1..N only. This distinction must be explicit in the driver header — the two rules look
  contradictory to a reader who meets only one of them.

- **D-04:** The completeness gate lives as a **new gate inside `check_rerun_gates.py`**, taking an
  explicit stage / expectation selector. One tool owns "was this run good"; it already has the
  JSON/CSV loaders, the per-stage invocation point, and Gate 3's cross-artifact sweep. The file is
  already 1,863 lines — the planner should expect to factor, not just append.

### The expectation manifest — one source of truth

- **D-05:** **A machine-readable expectation manifest is the single source of truth**, and the
  prose hand-verification sheet DRIVER-03 asks for is **rendered from it**. The completeness gate
  reads the manifest directly. Drift becomes structurally impossible because there is one list.

  *Rationale:* the todo names the failure mode precisely — *"nothing makes those TODOs update the
  expected list"* — and it has already fired twice: Phases 24 and 25 each had to retroactively
  hand-append a `## Phase N additions` section to a todo file to communicate their new artifacts
  forward.

- **D-06:** The manifest carries **explicit run profiles**, and the gate is invoked with one,
  asserting only that profile's numbers. **Two profiles: `smoke` and `full`.** `full` is the frozen
  Phase 28 run; `smoke` is what Phases 26 and 27 can actually execute.

  *This is what makes Phase 25's D-21 satisfiable.* E1's band is 160/240 rows today and 640/960 at
  the frozen sha with four noise levels. **No Phase 26 gate may assert 640 or 960, and none may
  require a `noise_std` column in `experiments/results/`** — those belong to the `full` profile
  only. A gate that asserts them unconditionally fails every run until Phase 28.

- **D-07:** The registration coupling is **structurally enforced by a unit test** that
  cross-references the experiments' declared column constants (`E5_COLUMNS`, `ABLATION_COLUMNS`,
  `SPATIAL_COLUMNS`, `DEGENERATE_OBSERVATION_COLUMNS`, `OBSERVATION_DEPTH_COLUMNS`, `GRID_COLUMNS`,
  `GRID_SUMMARY_COLUMNS`, `EXP1/EXP2/EXP3_COLUMNS`) against the manifest and **fails when they
  disagree**. This turns *"the last step of each fix must be to add its outputs to the driver and
  the gate"* from a written plea into a red test. Highest-leverage item in the phase for
  Phases 28–30.

- **D-08:** The rendered prose expectation sheet is **committed and regenerated**, with a test
  asserting it is up to date with the manifest — same pattern as D-07. It must be reviewable in a
  diff, because DRIVER-03 requires the sheet to exist **before** the run.

### Inherited stages

- **D-09:** `e6_repeat2` is gated behind an explicit flag that **defaults OFF**, but the **`full`
  profile turns it ON**. Determinism is a standing claim (16 of 308 cells, D-19.3-13/D-19.3-20);
  leaving it off would keep that number attributed to the 2026-08-02 run at `22e75ef`,
  reintroducing the exact multi-sha provenance spine this milestone exists to retire. Cost: ~107 min
  on the frozen run. The completeness gate must expect `results_e6_repeat2/` under `full` and
  **not** under `smoke`.

- **D-10:** E3's `--check`-then-`--force` ordering **stays, with its rationale rewritten**. The old
  justification ("capture state before `--force` destroys it") is retired by DRIVER-04's archive.
  The operative reason is now: **E3 is one of only two experiments whose `--check` is still a real
  reproduction signal** (DRIVER-03's table: `--check` survives meaningfully on E3 and E2 only).
  Same code, honest reason — leaving the stale rationale in place is the class of defect FIX-06
  just spent a plan cleaning up.

- **D-11:** `--include-per-camera-latex` **stays OFF.** Verified against the live manuscript on
  2026-08-18: the flag renders `shared_interface=False` rows into `cpr_grouping.tex`; `tab:cpr`
  lives at `supplement.tex:449` with six rows, **all shared-interface**, and the generated fragment
  is **not `\input` anywhere** — the table is hand-transcribed. See **D-39** for the finding this
  produced.

### `--check` and baseline resolution

- **D-12:** The surviving `--check` paths gain an explicit **`--baseline-dir`**, threaded through by
  the driver and pointed at the archive directory.

  *This closes an interaction that would otherwise break the suite's sanity anchor.* DRIVER-04 moves
  `experiments/results/` aside, and that directory **is** where the committed baselines live. Move
  it and E3's `--check` has nothing to compare against — and neither does E2's ~1e-8 control, which
  is the suite's sanity anchor. "Keep the archive reachable" is not enough; the scripts resolve
  baselines by path. Phase 23's `resolve_e2_benchmark_path` is adjacent and must be checked for
  agreement.

- **D-13 (inherited, do not re-litigate):** the `--check` **verdict** is already settled —
  hand-verify this run against the written expectation sheet, then re-baseline and restore automated
  checking **after** the run (Phase 29). The exclusion **mechanism** already shipped in Phase 23:
  `compare_experiment_csv(..., exclude_columns=())` in `experiments/_io.py` (shared) plus
  `CHECK_EXCLUDED_COLUMNS = ("exit_code", "status_reason")` local to `e4_benchmark_grid.py`
  (D-07/D-08 of plan 23-02). Phase 26 **documents** this contract suite-wide; it does not reinvent
  it.

### E2 — data dependency, invocations, and pre-flight

- **D-14:** A missing E2 frameset **hard-fails pre-flight**, unless the omission is **declared** via
  an explicit `--skip-e2` flag. When declared, the driver announces it, the completeness gate
  records a **DECLARED REDUCTION** in its roll-up, and the manifest records that the run is
  synthetic-only. A reviewer without the 4.35 GB can still run everything else; a *silent* skip
  becomes impossible. This is stricter than the todo's literal "skip with a loud announcement" —
  because "loud" is a log line, and nobody reads the log overnight.

- **D-15:** E2 is an explicitly **multi-invocation** stage. Its runs are: the **production /
  classification** run against `config_paper.yaml`, the **band** runs (`--band-dir` /
  `--band-seeds` / `--emit-band-configs`), and **timing and memory as two distinct runs** (inherited
  and non-negotiable: `internals.benchmark_memory` costs 2.7–5.5% wall clock, so one run cannot
  produce both numbers honestly).

- **D-16:** Phase 25's `internals.log_all_observation_depths` (Phase 25 D-09) rides on the
  **classification run only — never the timing run**. Same logic that already splits timing from
  memory: an ~11 MB per-stage sidecar is not free, and a flag that perturbs the quantity being
  measured cannot ride along with it. The gate must know which E2 artifact comes from which
  invocation.

- **D-17:** Pre-flight asserts frameset **IDENTITY, not mere presence** — the verified signature
  (262 usable → 52 validation → 7,762 comparisons, or the equivalent file/frame count), sourced from
  the expectation manifest.

  *Rationale:* E2's ~1e-8 reproduction only means anything if the fresh run reads the *same* frames.
  This project has already shipped a frameset mix-up — FIX-06's "60 → 12 → 1,817" against the
  verified "262 → 52 → 7,762", the retired archive's numbers surviving in a comment on the branch
  the re-run uses. A presence-only check passes cleanly on the wrong archive and hands you a control
  that reads red for a reason nobody would guess at 3 a.m.

### Run manifest and version truth (DRIVER-02)

- **D-18:** **`git describe --tags --long --dirty` becomes the human-readable version anchor**;
  `git_sha` stays authoritative; the installed distribution's version is still recorded but under a
  name that says what it is (e.g. `installed_distribution_version`) so it can never be read as "the
  code that ran".

  *Rationale — this corrects the todo's framing.* Resolving `aquacal_version` from the installed
  distribution **does not fix F-002** here: an editable/source install reports the last *built*
  version, which is `2.0.1` for every commit after the tag — the identical defect that made two
  commits share `1.8.0`. `git describe` cannot collide across commits. Note this is a provenance
  **schema change** on top of those already queued.

- **D-19:** The manifest is written by a **Python emitter** (a small module beside
  `experiments/_io.py`), invoked **once by the driver at pre-flight**, into the run's output
  directory. Bash cannot get NumPy/SciPy/OpenCV build strings reliably, and a Python module is
  importable by D-07's coupling test. Written at pre-flight so a run that dies at stage 3 still has
  its environment recorded.

  *Consequence (recorded so nobody adds it back):* end-of-run timing is **not** appended to the
  manifest — the driver's `*_state.tsv` already stamps ISO start and completion per stage, so
  per-stage and total wall clock are recoverable without making the manifest mutable mid-run.

- **D-20:** Manifest contents: git sha, `git describe --tags --long --dirty`, dirty-tree state, OS
  and kernel, Python, NumPy, SciPy, **OpenCV including the PyPI build suffix** (`.90` vs `.92` —
  both report `cv2.__version__ == "4.13.0"`, and this manifest is the sole owner of that
  ambiguity), machine identifier, and UTC start time.

- **D-21:** **Gate 3 extends over the manifest with all-hard-FAIL semantics:** the manifest exists;
  every required environment field is non-null (including the OpenCV build suffix); its `git_sha`
  equals the single sha Gate 3 already establishes across artifacts; and **the tree was not dirty**.
  No warnings — the todo is explicit that a provenance mismatch which only warns is a provenance
  mismatch that ships. Do **not** re-implement sha agreement; Gate 3 already does it and does it
  better than a per-experiment assertion.

- **D-22:** The pre-run sha is tagged **`pre-rerun-baseline`**. Phase 30's purge commit must cite
  this tag by name.

### Driver safety rails

- **D-23:** The stale-state footgun is closed **two ways**: the state file's **path embeds the
  frozen sha** (so a state file from another commit is structurally unreachable, not merely
  detected), **and** the driver refuses to start when a found state file's recorded sha disagrees
  with `HEAD`. The old `rerun_19_3_state.tsv` stays on disk as history and can never be consumed.
  State files accumulate one per sha; that is acceptable.

  *The hazard being closed:* rename the script, keep the state file, and every stage is skipped —
  the suite does nothing and **exits 0**.

- **D-24:** Pre-flight refuses on **all four** of: a **dirty working tree** (a sha is not provenance
  if the tree moved; consistent with D-21); a **non-empty output tree with no matching state file
  for this sha** (phrased this way so a genuine resume still proceeds — otherwise the first crash
  bricks the recovery path the driver was built around); an **absent or identity-mismatched
  frameset** (D-14/D-17, subject to `--skip-e2`); and **insufficient disk headroom**, estimated
  from the run's output footprint (E2's ~11 MB h_q sidecars, E6's checkpoints, `e6_repeat2`'s
  isolated tree).

- **D-25:** The driver is renamed via **`git mv` to `experiments/run_experiment_suite.sh`** — not
  `run_suite.sh` — because in this repo "run the suite" already means pytest in every CLAUDE.md
  warning. State and frozen-sha files follow the same stem. Its header claims the entry-point role
  explicitly.

- **D-26 (inherited, do not re-litigate):** **Do not rewrite the driver in Python for this run.**
  A Python entry point is the better long-term shape, but the bash script encodes details easy to
  lose in translation (`tee`/`PIPESTATUS` exit capture, the resumability skip-line grep, the
  started-versus-completed distinction, `disown` semantics), and rewriting a proven overnight driver
  under a six-day deadline is the wrong bet. Rename, extend, revisit after submission. The manifest
  emitter (D-19) being Python is not a partial rewrite — it is a called helper.

- **D-27 (restate precisely in the driver header):** D-19.3-18's commit rule **relaxes** under
  two-machine operation. The real constraint is that **the RUN MACHINE's tree must not move** — no
  pull, checkout, or commit *there*. Work on the planning box, including commits and pushes, is safe
  and is **expected to continue during the run**. The over-broad version would idle the planning box
  for the whole window for no reason.

### Archive-aside (DRIVER-04)

- **D-28:** The move is a **committed step in Phase 26, immediately after tagging
  `pre-rerun-baseline`** — not a driver action. The driver's only role is to *refuse* a non-empty
  tree (D-24).

  *Why this matters beyond tidiness:* the frozen sha then ships with an empty `experiments/results/`
  and a populated archive, so the Linux checkout **arrives in the correct starting state** and
  D-12's `--baseline-dir` resolves to a path that exists at that sha. If the move happened on the
  Linux box at run time, the frozen sha and the run's starting state would disagree.

- **D-29:** Scope of the move — **all six tracked results trees**: `experiments/results/` (151
  files, 16 M), `results_e2_band/` (7, 26 M), `results_linux32gb/` (25), `results_e6_repeat2/` (14),
  `results_e6_seed43/` (14), `results_e4_repeat/` (4). The todo names only the first three; the
  other three are the same class, and `results_e6_repeat2/` especially, since D-09 has the frozen
  run writing there again.

- **D-30:** **Also move the loose stale driver state and logs** — `rerun_19_3_state.tsv`,
  `rerun_19_4/19_5` state, frozen-sha and log files, and the loose `e1_band_rerun.log` /
  `e7_band_rerun.log` that are the physical evidence of the out-of-queue band runs. Directly serves
  D-23: nothing stale left to be consumed or misread.

- **D-31:** **Also move the untracked `verify_23*/` probe trees** (`verify_23/`,
  `verify_23_fdnoise/`, `verify_23_optblocks/`, ~12 M each, git-ignored). They cannot confuse the
  Linux run because they never travel, but they can confuse a local verifier. This is local hygiene,
  not a reviewable commit — say so.

- **D-32:** **Nothing is deleted in Phase 26.** The archive stays reachable for the whole run —
  E2's ~1e-8 control and E3's tier diff both compare against it (D-12). The **purge is Phase 30 /
  POST-03**, gated on Phase 29's verification *and* the post-run `--check` re-baselining, and its
  commit message cites `pre-rerun-baseline` (D-22). The dangling-reference audit
  (`linux32gb_scope.json`, `experiments/README.md` §2, `check_rerun_gates.py`, test fixtures) is
  Phase 30's, not Phase 26's.

  **The archive directory name must not collide with the existing `experiments/archive/`** (31
  tracked files, already present).

### Acceptance — how the driver is proven without the real run

- **D-33:** Three forms of evidence, all required:
  1. **One full `--smoke` pass, end to end** over the real stage list — real invocations, real gate
     calls, real manifest, real completeness gate at the `smoke` profile. Verified 2026-08-18 that
     **every** experiment has a `--smoke` path, including E2 (visible SKIPPED when the dataset is
     absent, D-25/P7 of that module) and all three orphan scripts, so this is executable, not
     aspirational.
  2. **The dry-run harness extended over all new stages** (`RERUN_19_3_DRY_RUN` /
     `RERUN_19_3_DRY_RUN_CMD`, renamed to follow D-25's stem) — sequencing, resume, sticky-exit and
     the started-versus-completed distinction testable in seconds, including failure paths a smoke
     pass will not exercise.
  3. **Unit tests** over the stage list, manifest and expectations: D-07's coupling test, plus every
     declared stage having an expectation entry, every expectation having an owning stage, and the
     ordering constraints holding structurally.

- **D-34:** ⚠ **The full `--smoke` pass is the ORCHESTRATOR's run, never an executor's.** Per
  CLAUDE.md: an executor that backgrounds a long run and returns has stalled permanently and will
  not come back. `python -u`, `nohup` + `disown`. Give executors targeted test commands only, and
  state explicitly what they must NOT run.

- **D-35:** **Linux-side smoke is Phase 27 / RUN-01, not Phase 26.** Phase 26's smoke runs on the
  Windows planning box. Proving the frozen package runs on the target machine is RUN-01's stated
  job. Portability-sensitive constructs (`date -u`, `awk`, `du`, `git describe`) should nonetheless
  be written conservatively here so Phase 27 finds nothing.

- **D-36:** **`experiments/README.md` §2 is in scope and is rewritten by hand** to one row per
  *invocation*. As written it lists `python -m experiments.e1_refractive_comparison` with no
  `--seeds` row anywhere, so an operator following it produces no seed bands at all. (Deliberately
  **not** rendered from the stage list — the author's call; keep the prose natural.)

### Wall clock and ordering

- **D-37:** **Shortest-first ordering holds.** Its purpose — surface a systematic failure in seconds
  rather than after the longest stage — gets *more* valuable as the tail grows, not less.

- **D-38:** **A per-stage wall-clock estimate summing to a stated total is a Phase 26 deliverable**,
  carried in the stage list / manifest, so Phases 27 and 28 schedule against a number rather than a
  hope. Pre-flight may warn when the estimate exceeds the remaining window.

  ⚠ **Sizing flag for the planner and for Phase 28.** The current queue is ~9 h. The `full` profile
  adds four `--seeds` band stages (Phase 25 sized E1's four-level × ten-seed band **alone at ≈7 h**),
  four E2 invocations at 48–87 min each, three orphan scripts, and `e6_repeat2` ON (D-09). That is
  plausibly **~24–30 h — no longer one overnight**, against a **2026-08-21** submission from a
  **2026-08-18** start. Measure it; do not assume 9 h carries forward.

### Manuscript finding

- **D-39:** Record an **MF-NN entry in `.planning/MANUSCRIPT-FINDINGS.md`**: `cpr_grouping.tex` is a
  *generated* fragment that is **never `\input`** — `tab:cpr` at `supplement.tex:449` is
  **hand-transcribed**. This is the same class as *"a hand-transcribed parameter count off by ten"*
  from DRIVER-03's own "Do not" list, and it interacts with **Phase 27's pre-freeze gate that every
  §3-facing number has a generating emitter**. Record the derivation only — **do not edit the
  manuscript**; that is the manuscript session's, and the tree is read-only from this repo.

### Claude's Discretion

- The expectation manifest's file format, location, and schema (JSON / YAML / Python module), and
  how "exists only when at least one flagged row exists" is expressed declaratively.
- The archive directory's exact name (must not collide with the existing `experiments/archive/`).
- Whether `check_rerun_gates.py` is factored before the completeness gate is added to it.
- The exact stage identifiers and the internal shape of `STAGES=()` under multi-invocation stages.
- Plan decomposition and commit granularity, subject to the one-commit-per-requirement habit held
  through Phases 23–25.

### Folded Todos

All four todos carrying `resolves_phase: 26` are folded — they are this phase's requirement sources
and must be read in full, including their dated appendices.

- **`.planning/todos/pending/2026-08-15-make-the-suite-driver-cover-every-invocation.md`**
  (DRIVER-01) — the coverage gap that is the root cause of audit findings F-001/F-002; the rename
  decision and the state-file footgun; the two inherited stages; the "do not rewrite in Python"
  call; the stress-test section naming where the driver still does not save you.
- **`.planning/todos/pending/2026-08-15-emit-a-single-run-manifest-for-the-full-suite.md`**
  (DRIVER-02) — the six-sha spine table, the `aquacal_version` and OpenCV-build defects, and the
  explicit "do not re-implement sha agreement" narrowing.
- **`.planning/todos/pending/2026-08-15-suspend-programmatic-check-for-reshaped-artifacts.md`**
  (DRIVER-03) — the corrected blast-radius table (`--check` survives on E3 and E2 only), the
  expectation-sheet requirement, **and the `## Phase 24 additions` / `## Phase 25 additions`
  appendices, which are the concrete input for the expectation manifest.**
- **`.planning/todos/pending/2026-08-15-archive-stale-outputs-before-the-run-purge-them-after.md`**
  (DRIVER-04) — the two-phase move/purge split and the three failure modes the move defuses.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Requirement sources (read first, in full)

- `.planning/todos/pending/2026-08-15-make-the-suite-driver-cover-every-invocation.md` — DRIVER-01.
- `.planning/todos/pending/2026-08-15-emit-a-single-run-manifest-for-the-full-suite.md` — DRIVER-02.
- `.planning/todos/pending/2026-08-15-suspend-programmatic-check-for-reshaped-artifacts.md` —
  DRIVER-03. **The `## Phase 24 additions` and `## Phase 25 additions` sections are the concrete
  artifact/column inventory the expectation manifest is built from — do not paraphrase them, read
  them.**
- `.planning/todos/pending/2026-08-15-archive-stale-outputs-before-the-run-purge-them-after.md` —
  DRIVER-04.
- `.planning/ROADMAP.md` § Phase 26 — the four success criteria and the "Depends on 23, 24, 25"
  rationale.
- `.planning/REQUIREMENTS.md` — DRIVER-01 (`:158`), DRIVER-02 (`:161`), DRIVER-03 (`:164`, with the
  2026-08-17 always-red concrete case), DRIVER-04 (`:174`).

### The code being changed

- `experiments/rerun_19_3.sh` — 290 lines; the queue to rename and extend. Read the whole header:
  it encodes the shortest-first rationale, the started-vs-completed state distinction, E3's
  ordering, E6 repeat-2 isolation, the no-tree-mutation guarantee, and the `nohup … & disown` launch
  line.
- `experiments/check_rerun_gates.py` (1,863 lines) — Gates 1–4, `_check_git_sha_consistency`
  (Gate 3's cross-artifact form, `:1732`), `run_all_gates` (`:1768`), and the per-experiment
  `check_e{1..7}` / band checkers the completeness gate sits beside.
- `experiments/_io.py` (763 lines) — `compare_experiment_csv(..., exclude_columns=())`, the shared
  provenance writers; likely home for the manifest emitter's neighbours.
- `experiments/README.md` §2 — the invocation table to rewrite (D-36).
- `experiments/e4_benchmark_grid.py` — `resolve_e2_benchmark_path`, `CHECK_EXCLUDED_COLUMNS`;
  D-12's `--baseline-dir` must agree with this resolver.

### Upstream phase outputs this driver must register

- `.planning/phases/25-degeneracy-classification-claim-licensing/25-CONTEXT.md` — **its D-21
  especially** (the code/committed-artifact disagreement, and the explicit prohibition on any
  Phase 26 gate asserting 640/960 or requiring `noise_std` in `experiments/results/`); D-08's
  conditional `degenerate_observations.csv`; D-09's E2-only `log_all_observation_depths`; D-10's row
  cap and truncation stamp.
- `.planning/phases/24-degeneracy-instrumentation/24-VERIFICATION.md` — what actually shipped, and
  the one open warning (WR-02).
- `.planning/phases/23-experiment-correctness-fixes/23-02-SUMMARY.md` — the `--check` exclusion
  contract Phase 26 documents rather than reinvents; its `affects:` field names this phase
  explicitly.
- `src/aquacal/validation/diagnostics.py` — `DEGENERATE_OBSERVATION_COLUMNS` and
  `OBSERVATION_DEPTH_COLUMNS`. **Import them; never hard-code the lists** (Phase 25's instruction).
- `src/aquacal/calibration/_observability.py` — the 32 `DISCARD_KEYS`, and the "two independent
  marginals, each summing to the total, never additive together" rule the expectation sheet must
  encode correctly.

### Audit and provenance background

- `Spinoffs/papers/aquacal/AUDIT-goal4.md` Pass A — findings **F-001** (six shas, not one anchor)
  and **F-002** (two commits sharing "1.8.0"). This phase is their fix. **Read-only.**

### Standing constraints

- `CLAUDE.md` — the **"never let a subagent background a long run"** policy (D-34), always
  `python -u`, and the Git Bash / `/c/...` path conventions.
- `.planning/knowledge-base.md` § Known Issues — the executor-stall root cause, and plan 23-02's
  "a verification gate that cannot pass is worse than no gate" entry.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets

- **The queue driver's whole recovery machinery** — `is_stage_complete()`'s awk over the state TSV,
  `state_start` / `state_complete`, `run_one_stage`'s skip logic, `run_gate_check`'s always-return-0
  contract. D-01's sticky flag is a change to that last function's *caller*, not to the gate call.
- **`_dry_run_active` / `_dry_run_stub`** (`RERUN_19_3_DRY_RUN`, `RERUN_19_3_DRY_RUN_CMD`) — the
  existing seam D-33's second acceptance form extends. Every stage function already routes through
  it.
- **`e6_repeat2`'s isolation pattern** — `rm -rf` of a dedicated directory plus the positive
  re-solve signal (`grep -c "already exists (resumability)"`, 0 expected). The right template for
  any new stage that must not silently reuse checkpoints.
- **`compare_experiment_csv(..., exclude_columns=())`** — shared mechanism, E4-local list. The
  pattern for any further named exclusion: mechanism shared, list at the consuming call site.
- **`check_rerun_gates.py`'s `_load_json` / `_load_csv` / `GateResult`** — the completeness gate
  should emit `GateResult`s so the existing verdict-block formatting applies unchanged.

### Established Patterns

- **Gates record, they do not abort** (D-19.3-18). D-01 preserves this and adds a sticky exit; D-03
  carves out pre-flight as the sole exception. Both halves must be stated together or a reader meets
  a contradiction.
- **Band mode and default mode write disjoint artifacts.** E1's docstring: *"A `--seeds` run NEVER
  writes `exp1_parameter_errors.csv` … those remain exclusively the single-seed run's artifacts."*
  Band stages are **additional**, never substitutions.
- **Band CSVs gain columns; fixed-contract CSVs never do.** `exp1_parameter_errors.csv`,
  `exp2_depth_generalization.csv`, `exp3_xy_vs_z_anisotropy.csv` are read byte-for-byte by an
  external figures repository (D-19). The expectation manifest must mark them immutable.
- **Sidecars keyed apart between band and single-seed runs** —
  `e{1,5,6,7}_seed_band_provenance.json` and `e{N}_seed_band_degeneracy_breakdown.json`. A `--seeds`
  run must never overwrite a single-seed artifact.
- **One commit per requirement** (D-14 of Phase 23, D-20 of Phase 25), held through Phases 23–25.

### Integration Points

- Stage list → expectation manifest → completeness gate → rendered hand-verification sheet →
  Phase 28's run → Phase 29's gate verification.
- Manifest emitter → `check_rerun_gates.py` Gate 3 (extended) → the "one run, one machine"
  assertion.
- Archive move (D-28) → `--baseline-dir` (D-12) → E3's `--check` tier diff and E2's ~1e-8 control.
- `pre-rerun-baseline` tag (D-22) → Phase 30's purge commit message (D-32).
- Ordering constraints made structural in the stage list: `e7_focal_standoff_analysis` **after**
  E7's `--seeds` stage (it reads the band CSV at `:299`); `reconstruction_bootstrap` **after** E2
  (it consumes `--reconstruction-errors` from E2's output); `fd_jacobian_accuracy` anywhere.

</code_context>

<specifics>
## Specific Ideas

- **The smoke pre-flight validates wiring, not config content.** `--smoke` runs
  `create_scenario("ideal")` — different geometry, 4 cameras, and it deliberately reports a non-zero
  degenerate count. It catches a flag typo or an import error in minutes. It does **not** catch a
  wrong `--config` path or a bad production YAML, which is the failure that costs the most. D-17's
  frameset-identity check exists partly to cover that blind spot.
- **Existence and row count are not correctness.** A gauge-corrected column populated with
  uncorrected values passes every completeness check. That is the expectation sheet's and the
  hand-verifier's job, not the gate's — the manifest should be explicit about which columns carry
  only a *shape* expectation.
- **Do not weaken Gate 3** to accommodate a stage running at a different commit. Gate 3 failing is
  the system working: the run really did fracture, and the answer is to re-run that stage inside the
  frozen window.
- **Do not merge E2's timing and memory runs**, and do not fold the band runs into the default
  stages as substitutions. Both are inherited hard constraints.
- **`e6_legal_seed_probe*` and `seed_sweep_19_3.sh`** sit loose in `experiments/` alongside the
  driver; they are probes, not suite stages, and are not being folded into the queue.

</specifics>

<deferred>
## Deferred Ideas

- **Rewriting the driver in Python.** The better long-term shape — cross-platform, testable, able to
  emit the manifest directly — but explicitly post-submission (D-26).
- **Purging the archive directory** — Phase 30 / POST-03, gated on Phase 29's verification and the
  post-run re-baselining (D-32).
- **Post-run `--check` re-baselining and restoring automated checking** — Phase 29. DRIVER-03 is
  explicit that this is part of the same obligation, not a follow-up; the suite must not be left
  permanently on manual verification.
- **The dangling-reference audit before the purge** (`linux32gb_scope.json`, `README.md` §2,
  `check_rerun_gates.py`, test fixtures) — Phase 30.
- **Editing the manuscript** to `\input` the generated `cpr_grouping.tex` instead of a hand-typed
  `tab:cpr` — the manuscript session's call; Phase 26 records the finding only (D-39).
- **Linux-side portability verification** — Phase 27 / RUN-01 (D-35).

### Reviewed Todos (not folded)

- `2026-08-13-e4-aggregator-hardcodes-e2-benchmark-path.md` — FIX-05, Phase 23 (complete).
  Referenced only because D-12's `--baseline-dir` must agree with its resolver.
- `2026-08-14-decide-whether-e1-may-carry-absolute-accuracy-claims.md` — BAND-01, Phase 25
  (complete). Referenced for the 640/960 shape the `full` profile expects.
- `2026-08-15-classify-the-198-unprojectable-observations.md` — DEGEN-04, Phase 25 (complete).
  Referenced for the artifacts this driver must register.
- `2026-08-15-repackage-and-reupload-the-zenodo-archive.md` — RUN-05, Phase 29.
- `2026-08-15-e1-and-e7-run-with-the-interface-normal-fixed-unlike-everything-else.md`,
  `2026-08-15-e6-z-error-reporting-and-per-camera-gauge-decomposition.md`,
  `2026-08-15-e7-vacuous-fixed-rows-ship-as-measured-nulls.md`,
  `2026-08-15-correct-stale-strings-in-e2-and-the-synthetic-generator.md` — FIX-01..06, Phase 23
  (complete). Matched only on the `experiments` area.
- `2026-08-17-close-open-phase-24-review-warnings.md` (WR-02),
  `2026-08-17-parallelize-the-test-suite*.md`,
  `2026-08-17-revert-execution-model-override-after-phase-24.md`,
  `2026-08-17-audit-static-strings-that-annotate-recomputed-values.md` — not Phase 26.

</deferred>

---

*Phase: 26-full-suite-driver-handoff-readiness*
*Context gathered: 2026-08-18*

---

## Amendment 2026-08-18 — runtime measurement and de-scoping

Written after the initial context was committed (`15d3060`). Two author concerns drove it: the
suite's runtime, and overengineering in a codebase that may not be reopened after submission.
**Where this amendment conflicts with a decision above, the amendment wins.**

### A. The suite is ~50 h at Windows-box speed, not 24–30 h

> **SUPERSEDED by § E below (2026-08-18).** Two stage timings used here are anomalous; the
> corrected serial estimate is ≈ 22–26 h. The machine correction and the no-timing-recorded
> observation still stand.

Measured from `experiments/rerun_19_{3,4,5}_state.tsv`, which stamp ISO start/complete per stage:

| stage | wall clock | source |
|---|---|---|
| `e6_band` | 10.8 h | measured, 19.5 |
| `e7_band` | ≤ 8.8 h | bracketed from artifact mtimes; no timing recorded anywhere |
| `e1_band` ×4 noise levels | ~7 h | Phase 25 estimate |
| `e4` | 3.6 h | measured, 19.4 |
| `e2` production + timing + memory | ~3.5 h | 48–87 min each |
| `e6_repeat1` + `e6_repeat2` | 2.8 + 2.8 h | measured, 19.4 |
| `e1` / `e7` / `e5` single | 2.5 / 2.2 / 0.75 h | measured, 19.4 |
| `e2_band` / `e5_band` / `e4_repeat` | 2.4 / 2.3 / 1.0 h | measured, 19.5 |
| `e3` + 3 orphan scripts | ~0.1 h | measured |
| **total** | **~50 h** | |

**Machine correction, and it matters.** Those measurements were taken on the **Windows box** —
Intel Alder Lake-H, **20 logical cores, 15.7 GiB** (this is the "16 GB Windows box" of
`linux32gb_scope.json`). Phase 28 runs on the **Linux target: i9-13900KF, 32 logical cores,
~31 GiB**, the same machine `supplement.tex:596` credits for the nine-cell grid. The target is the
faster box, so **~50 h is an upper bound**. Phase 28 must state which machine each estimate refers
to; a budget that silently mixes them is worthless.

**No band artifact records its own runtime** — not in the CSVs, not in the
`e{N}_seed_band_provenance.json` sidecars. D-38's budget has nothing historical to build on beyond
those three state files. The manifest (D-19/D-20) should fix this going forward.

### B. Grid cuts taken (author, 2026-08-18)

Selected against the manuscript's own `numbers-ledger.tsv` (132 rows mapping each cited number to
its generating artifact), so each cut's claim cost is measured rather than argued.

- **D-40: drop E6's `scale` axis** — 18 of 102 band cells, ~1.9 h. It appears in **zero** ledger
  rows; all 11 numbers backed by `generalization_sweep_band.csv` sit on the `cameras`, `index` or
  `layout` axes. E6's band composition is 17 configs × 6 seeds: index 8, cameras 3, layout 3,
  scale 3.
- **D-41: E1's noise axis runs 10 seeds at 0.5 px and 4 seeds at each of `{0.25, 0.82, 1.2}`** —
  352 rows rather than 640, ~3.9 h rather than ~7. The headline 97–178× band and all 16 ledger
  numbers backed by `exp1_band.csv` live at 0.5 px and are untouched; the three new levels deliver
  BAND-01's *stated domain* with wider error bars, which is what the requirement asks for.
  **This supersedes the flat 640/960 shape named in Phase 25's D-21** — the `full` profile expects
  352 / 528 rows. Any gate asserting 640 is wrong.
- **D-42: `e6_repeat2` is OFF, reversing D-09** — ~2.8 h. The determinism statistic (63 → 16 of
  308 cells) is a **response-letter** number, not a §3 number, and is produced by
  `determinism_probe.py` comparing two repeats rather than by the stage alone. Leave it off and
  disclose the sha it was measured at. The completeness gate must not expect
  `results_e6_repeat2/` under either profile.

  *E6's `index` axis 8 → 5 was offered and NOT taken; it stays at 8 values.*

**Rejected and why, so they are not revisited:** E6/E7 band seed counts (seed spread *is* the
cited quantity in four response-letter rows; E7's refined arms are already seed-unstable past
10 mm and Phase 29 gates on an E7 before/after comparison); E4's nine cells (`supplement.tex:605`
is a nine-cell table and `main.tex:285` names the "nine-cell timing grid" — cutting cells means
editing the paper).

**Net: ~7.8 h off the Windows-box figure.**

### C. Concurrency — the larger lever

The "one calibration at a time" rule (review H4) exists to protect **timing** measurements. Only
`e4`, `e4_repeat`, `e2_timing` and `e2_memory` are timing-sensitive (~8.6 h). The remaining ~35 h
is accuracy work indifferent to wall clock.

Established facts: **no thread limit is set anywhere** in `src/` or `experiments/`
(`OMP_NUM_THREADS`, `MKL_NUM_THREADS`, threadpoolctl — all absent); NumPy 2.4.2 / SciPy 1.17.0 on
`scipy-openblas`; the solve path densifies the FD Jacobian (`.toarray()`) to use
`tr_solver='exact'`, so it mixes a BLAS-threaded factorization with a largely serial Python-level
FD loop. Whether concurrency pays depends on that split — a property of the wheels and the problem
shape, **not the OS**, which is why it was measured on the Windows box.

Probe: `.planning/probes/2026-08-18-solver-concurrency/` — one E1 single-seed solve with a
CPU/RSS sampler. **Read that directory's `summary.json` and `FINDINGS.md` before planning the
driver's stage model.** Peak RSS is the binding constraint on the target (E2 alone peaks at
10.26 GiB against ~31 GiB), and E1 is the suite's smallest solve, so its RSS is a floor and its
headroom figure an upper bound — never a setting to copy.

### D. De-scoping — protect this run, not a hypothetical future one

Author's framing: *"achieving a clean, accurate baseline run"* matters more than *"protecting
against every possible future eventuality — I may never touch this codebase again after
submission."* Seven reductions, all taken.

- **D-43: CUT D-07's coupling test.** It protects future schema-changing fixes from forgetting to
  register their artifacts. Phases 23, 24 and 25 have shipped and no further schema-changing fix is
  scheduled, so it defends a window that is already closed.
- **D-44: CUT D-08's renderer and freshness test.** Keep the machine-readable manifest (the gate
  reads it); **hand-write the prose expectation sheet once**. It is authored once and frozen days
  later — there is no drift window to defend.
- **D-45: DOWNGRADE D-18 to manifest-only.** Record `git describe --tags --long --dirty` in the
  **run manifest**, a new file. Do **not** change the provenance schema in
  `src/aquacal/io/benchmark.py`: touching every artifact writer days before a freeze risks the run
  itself, to fix a field the manifest supersedes. Leave `aquacal_version` as-is with a documented
  caveat naming F-002.
- **D-46: CUT D-24's disk-headroom estimator.** Log free space and refuse below a crude absolute
  floor. A wrong estimate is precisely the malformed-check failure mode this de-scoping targets.
- **D-47: CUT D-24's dirty-tree refusal.** ⚠ **`experiments/results/` is tracked, so the run
  dirties its own working tree.** A dirty-tree refusal fires on **resume** and would refuse every
  restart after the first crash — a check that kills a run which would otherwise have succeeded.
  Gate 3 still records dirtiness post-hoc (D-21), which can never kill a run.
- **D-48: CUT D-23's HEAD-vs-state refusal; KEEP the sha-derived state path.** The path derivation
  is a few lines, cannot false-positive, and structurally makes a foreign state file unreachable.
  The separate refusal is the half that can wrongly block a 3 a.m. resume.
- **D-49: SIMPLIFY D-06's profiles.** `smoke` asserts artifact **existence only**; `full` asserts
  row counts. Roughly halves the manifest work and removes the class of smoke-profile row-count
  expectations that would need maintaining twice.

**D-50 — the governing principle for every remaining check.** *Every pre-flight refusal must print
the exact override flag that bypasses it, and nothing may abort once stage 1 has begun.* A
malformed check then costs one minute and one flag, never a night. This is what makes the surviving
refusals safe rather than merely fewer, and it applies to D-14's `--skip-e2` and D-17's frameset
identity check as well.

**Retained deliberately:** the completeness gate itself (~100 lines; it catches the exact F-001
mechanism), the pre-flight frameset-identity check (cheap, and it protects the largest single
block of run time), `--baseline-dir` (without it E2's ~1e-8 control and E3's tier diff both break),
the run manifest, the full `--smoke` pass, the dry-run harness extension, a small set of stage-list
unit tests, and the `README.md` §2 rewrite.

### E. Correction to § A, and the concurrency decision (probe landed 2026-08-18)

Probe: `.planning/probes/2026-08-18-solver-concurrency/` — `FINDINGS.md`, `summary.json`,
`samples.csv`. **Read FINDINGS.md before planning the driver's stage model or Phase 28's schedule.**

**⚠ § A's ~50 h figure is WRONG and is superseded. The corrected serial estimate is ≈ 22–26 h.**

The error: § A used `e1` and `e7` wall clock from the 19.4 state file, and those two rows are
anomalous by ~27×. Measured directly on 2026-08-18, an `e1_refractive_comparison` single-seed run
completes in **5.3 min** (19.3: 5.7 min; 19.4: 152 min), producing complete and correct output —
`exp1_parameter_errors.csv` 25 rows, `exp2_depth_generalization.csv` 17, `exp3_xy_vs_z_anisotropy.csv`
17, matching the committed artifacts exactly. Every *other* stage moves a consistent 1.6–2.0×
between 19.3 and 19.4 (the known machine swing); `e1` and `e7` do not fit that pattern. 19.4 is the
phase that fixed the grid-family clearance floor, and during that run those two solves ground on
against still-marginal geometry. **Use 19.3 or the probe for `e1`/`e7`; 19.4 remains sound for
`e5`, `e6`, `e4`.** § A's `e7_band` upper bound of 8.8 h is likewise a loose mtime bracket; the
stage is probably 1–2 h and **nothing measures it** — one E7 single-seed run (~10 min) would settle
it — **offered and DECLINED by the author on 2026-08-18: the soft estimate is sufficient.** D-38's budget therefore **states the uncertainty rather than closing it**; `e7_band` carries a range and a note that it is unmeasured. Do not schedule a probe for it.

- **D-51: the corrected serial estimate is ≈ 22–26 h at Windows-box speed** with D-40/41/42
  applied, dominated by `e6_band` at **8.9 h — roughly 40% of the whole suite**, and the critical
  path under any scheduling. It is the highest-value target if more time must be found later.

**D-52: selective concurrency is ADOPTED** (author, 2026-08-18). Measured: a solve holds a **median
0.99 cores of 20**, mean 1.20, p95 2.01, peak 2.56 — stable through Stage 3 — so ~30 of the target's
32 cores idle during every accuracy stage. No thread limit is set anywhere in `src/` or
`experiments/`; the dense-Jacobian `tr_solver='exact'` path is BLAS-threaded in principle but at
P ≈ 700–1,350 the serial Python-level FD loop dominates.

  The stage list gains a **serial/concurrent attribute plus a worker count**:

  - **Serial and alone** — `e4`, `e4_repeat`, `e2_timing`, `e2_memory` (~6–7 h). Review H4's
    rationale is *timing integrity*, and it is preserved exactly where it applies.
  - **Concurrent, 4–5 wide** — every accuracy stage (~16–19 h of work), bounded by the longest
    single stage rather than the sum.
  - **Expected total ≈ 15–16 h**, a saving of ~8–10 h. Requires **no change to any experiment**,
    only the driver's stage model — a smaller change than several of the items cut in § D.

  **Three hard constraints on the stage model:**

  1. **`e6_repeat1` and `e6_band` must never overlap.** `run_stage_e6_repeat1` does
     `rm -rf ${OUT_DIR}/e6_configs` and deletes `generalization_sweep.csv` / `e6_provenance.json`
     under the shared `OUT_DIR`, which `e6_band` also writes. (Moot for `e6_repeat2`, which D-42
     turns off.)
  2. **At most one 200-frame-class stage at a time** — E2 and E4's 200-frame cells peak at
     9.3–11.3 GiB. Five 3.5 GiB stages plus one of those is 27.8 of ~31 GiB, too tight. Peak RSS
     tracks frame count: 30 frames < 1 GiB (E5), 100 frames 2.7–3.5 GiB (**E6's band, all 102 rows
     at `n_frames=100`**), 200 frames 9.3–11.3 GiB.
  3. **Concurrent stages share `experiments/results/`,** so any shared artifact name is a
     collision. The expectation manifest already enumerates every artifact — verify filename
     disjointness there, not by inspection.

  **Not attempted, deliberately:** splitting `e6_band` across processes by seed. It attacks the
  critical path directly but needs a merge step and provenance handling inside the experiment,
  which is out of proportion to a phase just de-scoped in § D.

  One confirmation belongs in **Phase 27's Linux smoke**: that the same OpenBLAS build behaves the
  same way on the target. Two minutes there, not a reason to defer.

*Amended: 2026-08-18 (second pass, post-probe)*
