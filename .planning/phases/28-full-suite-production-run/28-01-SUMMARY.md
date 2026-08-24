---
phase: 28-full-suite-production-run
plan: 01
subsystem: infra
tags: [conda, pip-editable, opencv-pin, git-clone, pytest, experiment-suite-driver, dry-run]

# Dependency graph
requires:
  - phase: 29.1-post-run-fixes-re-freeze
    provides: "the frozen tag rerun-freeze-02 at 7005a2771aa115e4f4c1284cec7e145739586a4a, its corrected HANDOFF §1.2 install command, and the D4 three-failure ruling in 29.1-PREPUSH-AUDIT.md §1"
  - phase: 27-frozen-single-sha-handoff-package
    provides: "experiments/HANDOFF.md — the interpreter, dependency and invocation contract read out of the clone rather than from memory"
provides:
  - "A fresh production clone of rerun-freeze-02 at /home/tlancaster/aquacal-frozen-rerun-freeze-02-prod, HEAD 7005a277, at a path no rehearsal has ever used"
  - "A new conda environment aquacal-freeze02-prod built by executing the tag's own install command verbatim, with aquacal resolving from inside the production clone"
  - "Proof that the frozen 20-stage queue walks end to end at exit 0 inside that clone (dry run), with the real state file still absent"
  - "The D4 three-failure state reproduced and recorded in the new environment before any hours are committed"
  - "Four freeze02-* evidence files, counterparts to attempt 1's, for the returned record"
affects: [28-02-preflight-and-launch-authorisation, 28-03-the-production-run, 28-05-run-record, 29-gate-verification-results-commit]

actuals:
  tokens: 3200
  tasks: 3
  commits: 4

tech-stack:
  added: []
  patterns:
    - "Environment provenance asserted by string comparison against the clone path prefix, before the burn rather than after it"
    - "Install command read out of the frozen tree by line number and executed verbatim, never retyped"
    - "Dry run as the safe full-queue rehearsal, relying on the driver's .dryrun.tsv separation"

key-files:
  created:
    - /home/tlancaster/aquacal-frozen-rerun-freeze-02-prod/
    - /home/tlancaster/anaconda3/envs/aquacal-freeze02-prod/
    - /home/tlancaster/aquacal-frozen-rerun-freeze-02-prod/experiments/run_experiment_suite_state.7005a27.dryrun.tsv
    - /home/tlancaster/freeze02-install-command.txt
    - /home/tlancaster/freeze02-env.txt
    - /home/tlancaster/freeze02-pip-freeze.txt
    - /home/tlancaster/freeze02-pytest-prelaunch.txt
  modified: []

key-decisions:
  - "The production clone was obtained from the GitHub remote (git clone --branch rerun-freeze-02), not from the local repository — provenance recorded because the tree alone does not say how it was got"
  - "The freshly resolved dependency set is bit-for-bit the environment that produced attempt 1's accepted results — numpy 2.4.6, scipy 1.17.1, cv2 4.13.0.92, python 3.11.15, BLAS scipy-openblas 0.3.31.188.0 — so assumption A2's divergence risk did not materialise and Phase 29's E2 sanity control faces no environment delta"
  - "The suite is NOT clean at this sha: 3 failed, 2407 passed, 26 skipped. Three failures is the expected, ruled-on state (D4). Nothing was deselected, xfailed, re-baselined or renormalised"
  - "The empty experiments/results/ created by the pytest run was moved aside, never deleted and never overridden with a pre-flight flag"

patterns-established:
  - "Absence assertions are taken twice — before the write and after it — so a passing assertion cannot be an artefact of ordering"
  - "A long (28 min) confirmation run is launched detached with setsid+nohup and polled from short calls, never held open in one foreground call"

requirements-completed: [RUN-02]

coverage:
  - id: D1
    description: "A fresh clone of rerun-freeze-02 exists at the -prod path with HEAD 7005a2771aa115e4f4c1284cec7e145739586a4a, holding no real state file, no experiments/results and no experiments/results_e2_band"
    requirement: RUN-02
    verification:
      - kind: integration
        ref: "git -C $CLONE rev-parse HEAD; test ! -e experiments/run_experiment_suite_state.7005a27.tsv; test ! -e experiments/results; test ! -e experiments/results_e2_band"
        status: pass
    human_judgment: false
  - id: D2
    description: "A new conda environment aquacal-freeze02-prod in which aquacal resolves from inside the production clone, cv2 is 4.13.x, and pytest and psutil both import"
    requirement: RUN-02
    verification:
      - kind: integration
        ref: "$ENVPY -c 'import aquacal;print(aquacal.__file__)' prefix-matched against the clone path; cv2.__version__.startswith('4.13.'); import pytest, psutil"
        status: pass
    human_judgment: false
  - id: D3
    description: "The frozen 20-stage queue walks end to end at exit 0 inside the production clone, writing only to the .dryrun.tsv path"
    requirement: RUN-02
    verification:
      - kind: e2e
        ref: "RUN_EXPERIMENT_SUITE_DRY_RUN=1 bash experiments/run_experiment_suite.sh (exit 0); awk -F'\\t' '$3==\"complete\" && $5==0' ...dryrun.tsv | wc -l == 20"
        status: pass
    human_judgment: false
  - id: D4
    description: "The new environment reproduces the tag's ruled-on three-failure state with the three registered node ids and no fourth"
    requirement: RUN-02
    verification:
      - kind: unit
        ref: "pytest tests/ -q in aquacal-freeze02-prod → '3 failed, 2407 passed, 26 skipped'; node ids matched against 29.1-PREPUSH-AUDIT.md §1"
        status: pass
    human_judgment: false

duration: 31min
completed: 2026-08-24
status: complete
---

# Phase 28 Plan 01: Build and Prove the Production Venue Summary

**A fresh `rerun-freeze-02` clone at `…-freeze-02-prod`, a new `aquacal-freeze02-prod` conda environment that resolves `aquacal` from inside that clone on the pinned OpenCV 4.13.0, and a dry run that walked all 20 driver stages at exit 0 — with the D4 three-failure state reproduced bit-for-bit before any hours were committed.**

## Performance

- **Duration:** 31 min (27 of which was the prelaunch pytest)
- **Started:** 2026-08-24T23:17:56Z
- **Completed:** 2026-08-24T23:49:53Z
- **Tasks:** 3
- **Files created:** 7 paths (2 trees, 1 driver artifact, 4 evidence files) — all off-repo by plan design

## Accomplishments

- **The production venue exists and is proven.** Clone at `/home/tlancaster/aquacal-frozen-rerun-freeze-02-prod`, HEAD `7005a2771aa115e4f4c1284cec7e145739586a4a`, `git describe` = `rerun-freeze-02`, tree unedited.
- **The three absences hold, asserted before and after every write.** No `run_experiment_suite_state.7005a27.tsv`, no `experiments/results`, no `experiments/results_e2_band`. T-28-02's 20-stage-skip hazard and T-28-03's `N/A → two FAILs` hazard are both closed by construction rather than by inspection.
- **The editable-install hazard (T-28-01) is closed by the only control that covers it.** `aquacal.__file__` is `/home/tlancaster/aquacal-frozen-rerun-freeze-02-prod/src/aquacal/__init__.py` — asserted by prefix string comparison, and explicitly checked against the three wrong answers (the freeze-01 tree, the rehearsal clone, a site-packages copy).
- **The whole 20-stage queue was walked in ~1 second at exit 0**, in the clone that will run it, in the environment that will run it, and the real state file is still absent afterwards.
- **The D4 state reproduced exactly**, in 0:27:18, catching an A5 surprise for 28 minutes instead of six hours.

## Task Commits

Each task was committed atomically:

1. **Task 1 (tracer): clone, environment, install, dry run** — `baa0523` (chore)
2. **Task 2: assert environment provenance before the burn** — `79106d8` (chore)
3. **Task 3: confirm the D4 three-failure state** — `701b257` (chore)

**Plan metadata:** see final `docs(28-01)` commit.

## Files Created/Modified

All of this plan's artifacts are **off-repo by design** — the plan's `files_modified` frontmatter lists `$HOME` paths, and plan 28-05 is the step that copies the `freeze02-*` evidence into `.planning/phases/28-full-suite-production-run/`.

- `/home/tlancaster/aquacal-frozen-rerun-freeze-02-prod/` — the production clone; frozen, unedited
- `/home/tlancaster/anaconda3/envs/aquacal-freeze02-prod/` — the run environment
- `…-prod/experiments/run_experiment_suite_state.7005a27.dryrun.tsv` — 40 rows, 20 `complete` at exit 0
- `/home/tlancaster/freeze02-install-command.txt` — 1 line, byte-identical to `HANDOFF.md:49`
- `/home/tlancaster/freeze02-env.txt` — 4 lines, attempt 1's order
- `/home/tlancaster/freeze02-pip-freeze.txt` — 64 packages
- `/home/tlancaster/freeze02-pytest-prelaunch.txt` — the D4 confirmation run
- `/home/tlancaster/AquaCal_prod_aside/2026-08-24-7005a27-pytest-created-results/results/` — the empty directory moved aside (see Deviations)

## The measured record

### Clone provenance

| Property | Value |
|---|---|
| Source | `https://github.com/McGrathLab/AquaCal.git`, `--branch rerun-freeze-02` — **the network remote, not a local clone** |
| Path | `/home/tlancaster/aquacal-frozen-rerun-freeze-02-prod` (the `-prod` suffix, per C1/D5) |
| HEAD | `7005a2771aa115e4f4c1284cec7e145739586a4a` |
| `git describe --tags` | `rerun-freeze-02` |
| `status --porcelain --untracked-files=no` | empty, at every checkpoint through the end of the plan |

The rehearsal clone at `/home/tlancaster/aquacal-frozen-rerun-freeze-02` was **not touched**: mtime `2026-08-24 14:13:44.155677945 -0400` before and after, and its state-file set is still exactly the three `.dryrun.*` forms.

### The install line, as read

`grep -n 'pip install -e'` over the clone's `experiments/HANDOFF.md` returned three hits — lines 49, 53 and 70. Line 53 and line 70 are prose *about* the command; **line 49 is the §1.2 install line**:

    python -m pip install -e ".[dev,bench]"

Written to `/home/tlancaster/freeze02-install-command.txt` with `sed -n '49p'` and confirmed byte-identical by `diff`. Executed verbatim (`eval "$(cat …)"`) from the clone root in the activated environment; exit 0.

### The resolved environment — no divergence from attempt 1

| | This run | Attempt 1 | |
|---|---|---|---|
| python | 3.11.15 (main, Jun 11 2026, 15:20:16) [GCC 14.3.0] | 3.11.15 (main, Jun 11 2026, 15:20:16) [GCC 14.3.0] | same |
| `cv2` | 4.13.0 (opencv-python 4.13.0.92) | 4.13.0 (opencv-python 4.13.0.92) | same — **pin holds** |
| `numpy` | **2.4.6** | 2.4.6 | **same** |
| `scipy` | **1.17.1** | 1.17.1 | **same** |
| BLAS/LAPACK | scipy-openblas 0.3.31.188.0 | scipy-openblas 0.3.31.188.0 | same |
| `pytest` | 9.1.1 | 9.1.1 | same |
| `psutil` | 7.2.2 | 7.2.2 | same |

**`numpy` and `scipy` did not diverge.** Both are deliberately unpinned, so this was not guaranteed — assumption **A2** flagged a resolve-drift risk and it did not materialise. This is a fact Phase 29's E2 sanity control wants: the comparison run and the reference run share an identical numerical stack, so any E2 difference cannot be attributed to a library bump.

### The dry run

`RUN_EXPERIMENT_SUITE_DRY_RUN=1 bash experiments/run_experiment_suite.sh` — **exit 0** in ~1 s, ending with `Suite driver finished all 20 stages.` and the roll-up's `SUITE COMPLETE` banner (dry).

`awk -F'\t' '$3=="complete" && $5==0' …7005a27.dryrun.tsv | wc -l` = **20**; the complement (`$5!=0`) = **0**. All 20 stage indices 1–20 present, all 20 distinct stage names, matching `run_experiment_suite.sh:541-562` in order:

    1 preflight · 2 prelaunch_probe · 3 fd_jacobian · 4 e1 · 5 e7 · 6 e5 · 7 e2_production
    8 e6_repeat1 · 9 e3 · 10 reconstruction_bootstrap · 11 e2_timing · 12 e2_memory
    13 e7_band · 14 e5_band · 15 e2_band · 16 e1_band · 17 e4 · 18 e6_band
    19 e7_focal_standoff · 20 e4_repeat

The `.dryrun.tsv` separation held: the real state file was absent before the dry run and absent after it.

### The prelaunch pytest — the suite is NOT clean, and that is the pass condition

    3 failed, 2407 passed, 26 skipped, 30 warnings in 1638.58s (0:27:18)

    FAILED tests/unit/test_discard_accounting.py::test_matches_frozen_anchor
    FAILED tests/unit/test_optim_common.py::TestPerObservationDetailSinks::test_detail_sink_recomputed_geometry_matches_projector
    FAILED tests/unit/test_pipeline.py::TestSolverConfigSeedIsInert::test_matches_pre_change_anchor

`grep -c '^FAILED '` = **3**; all three node ids match `29.1-PREPUSH-AUDIT.md` §1 verbatim; there is no fourth. Passed and skipped counts are **measured, not asserted** — 2407 and 26, which happen to equal the register's figures.

**No artifact of this phase states or implies that the test suite is clean.** Three failures is the expected, ruled-on state (D4). Nothing was suppressed, deselected, xfailed, re-baselined or renormalised.

The disagreement values reproduce bit-for-bit against the register's table, which strengthens the D4 diagnosis from "same count, same names" to "same numbers":

| Test | Actual | Expected |
|---|---|---|
| `test_matches_frozen_anchor` | `0.794471850364211` | `0.7944718492870945` |
| `test_detail_sink_recomputed_geometry_matches_projector` | `0.10681280743540097` | `0.10681280743540099` |
| `test_matches_pre_change_anchor` | `1.179461e-16`, `2.493056e-16` | `1.626336e-16`, `4.927961e-16` |

`tests/unit/test_experiments_provenance.py` contributed **0** failures. D1's eight are parametrized over a populated `experiments/results/`; the tree is empty, so they are absent now and their reappearance after the run is expected and not caused by this phase.

## Decisions Made

- **Clone provenance is recorded, not just the tree.** The network remote was reachable, so the plan's primary path was taken; the SUMMARY says so explicitly because a tree cannot testify to how it was obtained.
- **The `numpy`/`scipy` identity is reported as a positive finding, not passed over.** The plan asked for a divergence to be recorded; the *absence* of divergence is equally load-bearing for Phase 29 and is stated in the table above rather than left implicit.
- **The empty `experiments/results/` was moved aside rather than deleted.** Hard constraint 8 and the D-24 pre-flight rule both point the same way: no deletion, no override flag.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 — Blocking] The prelaunch pytest created an empty `experiments/results/` in the frozen clone**

- **Found during:** Task 3 (D4 confirmation run)
- **Issue:** Task 3's `<verify>` block ends with `test ! -e $CLONE/experiments/results`, and it failed. The `pytest tests/ -q` run left an **empty** `experiments/results/` directory (0 entries) in the production clone. Left in place it is a live hazard: a present-but-empty output tree is exactly the state that turns a clean pre-flight into a refusal, and `experiments/results_e2_band`'s present-and-empty analogue converts one `N/A` into two `FAIL`s in the roll-up.
- **Fix:** Moved aside exactly as the plan's own action text directs — `mv` into `/home/tlancaster/AquaCal_prod_aside/2026-08-24-7005a27-pytest-created-results/results`. **Nothing was deleted, and no pre-flight override flag was used** (constraint 2, constraint 8).
- **Files modified:** none inside the clone; the directory was untracked and `git -C $CLONE status --porcelain --untracked-files=no` remained empty throughout.
- **Verification:** all three absences re-asserted clean afterwards; Task 3's verify block re-run and returned `OK`; Task 1's verify block re-run as a regression check and returned `OK`.
- **Committed in:** `701b257` (Task 3 commit)

**2. [Rule 3 — Blocking] Task commits have no in-repo content to stage**

- **Found during:** Task 1
- **Issue:** Every artifact this plan produces is off-repo by design — the plan's `files_modified` frontmatter lists only `$HOME` paths, and the artifacts table routes the `freeze02-*` evidence into `.planning/` at **plan 05**, not here. The per-task atomic-commit protocol therefore had nothing to stage, and writing the evidence into `.planning/` now would preempt plan 05 and duplicate it.
- **Fix:** Each task was committed as a `--allow-empty` marker commit whose **message body carries the task's literal assertion output** (shas, paths, versions, counts, node ids). This preserves per-task atomicity and audit granularity, and has the side benefit of putting the assertion evidence into repository history where it is durable independent of `$HOME`.
- **Files modified:** none
- **Verification:** all three hashes confirmed present via `git log --oneline --all`
- **Committed in:** `baa0523`, `79106d8`, `701b257`

---

**Total deviations:** 2 auto-fixed (2 blocking).
**Impact on plan:** No scope creep and no change to what the assertions mean. Deviation 1 is the plan's own contingency executed as written; deviation 2 is a protocol accommodation to an off-repo plan, not a change to the work.

## Issues Encountered

- **The plan's `<verify>` block for Task 3 initially failed**, on its final clause only. This was not a false alarm and was not worked around: it correctly detected the empty `experiments/results/` described in Deviation 1. Every clause was isolated and re-run individually before acting, so the failure was attributed precisely rather than by guess.
- **Harness timeout vs. a 28-minute run.** The Bash tool caps at 10 minutes, so the pytest run was launched detached (`setsid nohup`, writing to the evidence file plus a sentinel `.done` file) and polled from four short calls. Process health was confirmed mid-run (pid 876846, correct interpreter, 952% CPU) rather than inferred from the file alone. The suite's own anti-pattern about backgrounding applies to the six-hour production run, not to this bounded confirmation step, and the plan explicitly prescribes the detached form used here.

## Known Stubs

None. This plan writes no code — the tag is frozen and nothing under the clone was edited.

## Threat Flags

None. No new security-relevant surface: this plan adds no endpoint, no auth path and no schema. T-28-05 (absolute home paths in `freeze02-env.txt` and `freeze02-pip-freeze.txt`) is the register's **accepted** row, ruled intentional by 27-10's pre-push audit; those paths are present as ruled and were deliberately not sanitised.

## Verification Against `must_haves`

| Truth | Result |
|---|---|
| Clone at the `-prod` path, HEAD `7005a277…`, never used by a rehearsal | PASS |
| No real state file, no `experiments/results`, no `experiments/results_e2_band` | PASS (asserted 3×: pre-dry-run, post-dry-run, post-pytest) |
| New env; `aquacal.__file__` under the production clone | PASS — `…-freeze-02-prod/src/aquacal/__init__.py` |
| `cv2` 4.13.x; `pytest` and `psutil` import | PASS — 4.13.0; both import |
| Dry run walked all 20 stages at exit 0, real state file still absent | PASS — 20/20, exit 0 |
| `pytest tests/ -q` reports exactly 3 failures, node ids match the register | PASS — 3/3, verbatim |

| Prohibition | Result |
|---|---|
| No result from a non-production checkout presented as `rerun-freeze-02` | HELD — import path asserted before any run; no run has occurred |
| No artifact states or implies the suite is clean | HELD — every artifact states `3 failed` plainly |

## User Setup Required

None.

## Next Phase Readiness

**Ready for plan 28-02 (pre-flight and launch authorisation).** The venue is built and every precondition for the launch is on disk as evidence.

Carry forward into 28-02/28-03:

1. **Nothing has been launched.** Plan 28-01 deliberately ends here. The production run is plan 28-03 and remains gated behind a human decision that has **not** been given.
2. **`PRELAUNCH_GATE_PYTHON` must still be set explicitly (D-28)** — `/home/tlancaster/anaconda3/envs/aquacal-freeze02-prod/bin/python`. It was not needed for the dry run and was not set.
3. **`SUITE_E2_RELEASE_CONFIG` and `SUITE_DISPATCH_LOG` were explicitly unset for the dry run** (D-12, B1) and must stay unset.
4. **Running `pytest` again inside the clone will recreate the empty `experiments/results/`.** D4 confirmation is done; do not re-run it before launch, and if anything does, re-check that directory before pre-flight.
5. **The `.dryrun.*` artifacts are in the clone and are gitignored** (`.gitignore:266-272`), so they do not dirty the tree and `gate3_run_manifest_clean_tree` is unaffected.
6. **Assumption A2 is discharged for this run.** The dependency set is identical to attempt 1's, so Phase 29's E2 sanity control compares like with like.

---
*Phase: 28-full-suite-production-run*
*Completed: 2026-08-24*

## Self-Check: PASSED

All 8 claimed artifact paths exist on disk (production clone, environment interpreter,
`.dryrun.tsv`, the four `freeze02-*` evidence files, the moved-aside directory), and all four
claimed commits resolve in `git log --oneline --all`: `baa0523`, `79106d8`, `701b257`, `055225c`.
