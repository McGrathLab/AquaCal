---
phase: 26-full-suite-driver-handoff-readiness
plan: 07
subsystem: experiments
tags: [driver, stage-list, d-25, d-37, d-42, d-48, ruling-a1, ruling-a3, f-001]
requires:
  - "experiments/suite_expectations.json + experiments/_expectations.py: the 20-stage manifest and load_expectations (plan 26-03)"
  - "experiments/_run_manifest.py: the run-manifest emitter, previously called by nothing (plan 26-02)"
  - "experiments/pre_rerun_baseline/results/: the archived --baseline-dir target (plan 26-01)"
  - "experiments/e2_real_rig.py --emit-invocation-configs / --invocation-dir (plan 26-06)"
  - "experiments/e6_generalization_sweep.py --axes (plan 26-05)"
  - "experiments/e3_derived_quantities.py --baseline-dir (plan 26-04 / 26-06)"
provides:
  - "experiments/run_experiment_suite.sh: THE suite driver, 20 stages covering every invocation"
  - "STAGES=(...): the machine-readable stage list plan 26-08's pool schedules"
  - "tests/unit/test_suite_stage_list.py: bidirectional stage/expectation coupling + topological-order proof"
  - ".gitignore: new-stem dry-run state ignore and driver-log un-ignore"
affects:
  - "plan 26-08 (pre-flight, sticky-failure flag, end-of-run roll-up, concurrency pool — all build on this stage list)"
  - "plan 26-09 (archives rerun_19_4.sh / rerun_19_5.sh, after grep-verifying the lift landed)"
  - "Phase 27 (portability: E2_RELEASE_CONFIG, BASELINE_DIR and E2_INVOCATION_DIR are now overridable)"
tech-stack:
  added: []
  patterns:
    - "Dispatch by name (declare -F run_stage_${name}) instead of a per-stage case arm: STAGES and the functions become one source of truth a test can prove"
    - "State-file path embeds the frozen short sha, so a foreign state file is unreachable rather than merely detected"
key-files:
  created:
    - tests/unit/test_suite_stage_list.py
  modified:
    - experiments/run_experiment_suite.sh
    - .gitignore
decisions:
  - "prelaunch_probe is placed before e3 in deliberate inversion of shortest-first: 20 seconds, against aborting after `e3 --force` has already rewritten committed tier CSVs"
  - "preflight joins prelaunch_probe as a hard-abort stage — both are pre-flight under D-03, and both run before any long stage"
  - "preflight passes --force to the manifest emitter so a resume after a crash mid-pre-flight can rewrite it rather than dying on FileExistsError"
  - "The E2 invocation configs are re-emitted by each of the three E2 stages, so a resume starting at e2_timing does not depend on a directory an earlier stage happened to leave behind"
metrics:
  duration: ~70 min
  completed: 2026-08-18
---

# Phase 26 Plan 07: The One Driver

`experiments/run_experiment_suite.sh` now carries all twenty stages of the suite — the
seven invocations no driver has ever run included — in a topological order of the
expectation manifest's dependency edges, with the stage list proven bidirectionally
coupled to that manifest by a unit test.

## What Shipped

### Task 1 — the rename and the lift (commits `0402960`, `bdd9dcc`)

Split into **two** commits on purpose. A single commit that both renamed the file and
replaced its body scored below git's 50% rename-similarity threshold, so
`git log --follow` stopped at the new file and the driver's history was lost. The pure
`git mv` landed first (`0402960`, recorded as `rename ... (100%)`), the content second.
`git log --follow -- experiments/run_experiment_suite.sh` now reaches
`29b06a5 feat(19.3-08)`, the driver's original commit.

Ruling A3 held up: this is a **union-and-lift from `rerun_19_5.sh`**, not an extension of
19.3. Lifted verbatim — `is_stage_complete` / `state_start` / `state_complete` (the ISO
stamps that are the only per-stage timing record in this project), `run_gate_check` with
the **pinned `GATE_PYTHON`** and its warning fallback, the `_dry_run_active` /
`_dry_run_stub` seam, and the **dry-run state-file separation** absent from 19.3.

Two things changed rather than being lifted:

- **State path** is `experiments/run_experiment_suite_state.<short_sha>.tsv`, with the
  dry-run variant at `...state.<short_sha>.dryrun.tsv` (D-23 as halved by D-48). There is
  **no** HEAD-vs-state refusal — that is the half D-48 cut, and the file says so, because
  a future reader who knows D-23 and not D-48 will otherwise think it was forgotten.
- **Dispatch is by name**, not a `case` arm per stage. 19.5's `case` was a second place
  the stage list lived; with `declare -F "run_stage_${name}"` the array and the functions
  cannot drift, which is what makes the Task 3 test's third assertion meaningful. The
  unknown-stage guard is preserved.

The header states **D-01 and D-03 adjacently and marked as looking contradictory**, with
the F-001 rationale verbatim in substance, plus D-27 (only the *run machine's* tree must
not move; planning-box commits continue), D-37 (shortest-first, `depends_on` wins) and
D-50. It also claims the entry-point role and names `rerun_19_{3,4,5}.sh` as historical.

### Task 2 — the twenty stages (commit `a9b12b4`)

The array is a topological order of the manifest's edges, shortest-first within each
dependency level:

```
preflight · prelaunch_probe · e3 · fd_jacobian · e1 · e7 · e5 · e2_production ·
e6_repeat1 · reconstruction_bootstrap · e2_timing · e2_memory · e7_band · e5_band ·
e2_band · e1_band · e4 · e6_band · e7_focal_standoff · e4_repeat
```

The seven genuinely missing invocations, all now present:

| # | Stage | Note |
|---|---|---|
| M1 | `e2_production` | generated `config_e2_classification.yaml`; writes the `benchmark.json` `e4` silently drops a row without |
| M2 | `e2_timing` | own out dir `results_e2_timing`, `serial_alone` |
| M3 | `e2_memory` | own out dir `results_e2_memory`, `serial_alone` |
| M4 | `e7_focal_standoff` | after `e7_band`; the `cd "${REPO_ROOT}"` is what makes its hardcoded path resolve |
| M5 | `reconstruction_bootstrap` | after `e2_production` (hardcoded `REAL_RIG_METRICS_PATH`) |
| M6 | `fd_jacobian` | placed early — seconds, and it exercises the whole queue plumbing |
| M7 | `e1_band` | uniform 4-seed × 4-level grid, **no new E1 flag** (ruling A1) |

Also: `e6_band` gained `--axes index,layout,cameras` (84 rows); E3's `--check` gained
`--baseline-dir` (and only `--check` — e3's parser rejects it alongside `--force`);
`E2_RELEASE_CONFIG`, `BASELINE_DIR` and `E2_INVOCATION_DIR` became `:-` overridable
instead of literals. `e6_repeat2` is absent (D-42) with its `tee`/`PIPESTATUS`/skip-grep
isolation template kept as a comment; `--include-per-camera-latex` stays off (D-11).

**One deliberate inversion of shortest-first is documented in the file:**
`prelaunch_probe` (0.01 h) precedes `e3` (0.005 h). Twenty seconds, against the
alternative of hard-aborting *after* `e3 --force` has rewritten committed tier CSVs.

### Task 3 — `tests/unit/test_suite_stage_list.py` (commit `35de34f`)

16 tests, all textual or manifest-level; `grep -c subprocess` is 0 and the driver is
never executed. Beyond the plan's required behaviours it also asserts that no
`run_stage_` function is *unreferenced* by `STAGES` (a stage that exists and is never
scheduled is the same silent gap as one that does not exist) and the two regression
rails from the deviation below.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 — Bug] `e6_repeat1` destroyed committed artifacts under a dry run**

- **Found during:** Task 2, while preparing to exercise the dry-run seam.
- **Issue:** the `e6_repeat1` body lifted from `rerun_19_3.sh` runs
  `rm -rf "${OUT_DIR}/e6_configs"` and `rm -f generalization_sweep.csv e6_provenance.json`
  **before** consulting `_dry_run_active`. `experiments/results/` is a **tracked**
  directory, so a control-flow rehearsal — the thing plan 26-08 is about to do
  repeatedly — deletes committed files. `rerun_19_4.sh` had already fixed this
  (`"e6_repeat1: DRY RUN -- skipping the destructive pre-run cleanup"`); the 19.3 shape
  is what the plan's `<interfaces>` pointed at, so the defect came in with the lift.
- **Fix:** dry-run branch moved above the cleanup, matching 19.4, with a comment saying
  it is a fix and not a style choice.
- **Regression rails:** `test_no_stage_destroys_anything_before_the_dry_run_seam` scans
  every `run_stage_` body for `rm`/`mkdir` preceding the seam, ignoring comment lines.
- **Commit:** `a9b12b4`

**2. [Rule 3 — Blocking] the `git mv` did not survive as a rename**

- **Found during:** Task 1 acceptance (`git log --follow` returned one commit).
- **Fix:** split into a pure-rename commit then a content commit. Described above.
- **Commits:** `0402960`, `bdd9dcc`

### Deliberate departures from the plan text

- **`preflight` is a hard-abort stage**, not only `prelaunch_probe`. The plan's lifted
  `run_one_stage` hard-aborts on `prelaunch_probe` alone, but D-03 governs *pre-flight*,
  and `preflight` is now a stage that runs before it. Both are handled by one `case`.
- **`--force` on the manifest emitter.** D-19 says the manifest is written once and
  `--force` is the explicit override. Without it, a resume after a crash *during*
  pre-flight dies on `FileExistsError` at the one stage whose failure aborts the queue.
  Documented at the call site.
- **The `_dry_run_active`-count acceptance criterion was verified functionally, not
  literally.** `grep -c '_dry_run_active'` equals 21, not 20: the twenty stage bodies
  plus the function's own definition. The intent — no stage bypasses the seam — is
  asserted properly by parsing each function body (0 missing) and by the new unit test.
- **`grep -c 'axes index,layout,cameras'` returns 1** only after rewording the adjacent
  comment, which originally quoted the flag verbatim.

## Verification

| Check | Result |
|---|---|
| `bash -n experiments/run_experiment_suite.sh` | exit 0 |
| stage-array ↔ manifest bijection (the plan's inline python) | `ok 20` |
| `pytest tests/unit/test_suite_stage_list.py -x -q` | **16 passed** (≥9 required) |
| `pytest tests/unit/test_expectations.py tests/unit/test_stale_provenance_strings.py -q` | 88 passed (26-03's tests unbroken) |
| `--collect-only \| grep -c order` | 5 (≥4 required) |
| `grep -c subprocess tests/unit/test_suite_stage_list.py` | 0 |
| orphan scripts / e2 configs / `--axes` / `--baseline-dir` greps | 14 / 3 / 1 / 2 |
| `run_stage_e6_repeat2` | 0; `e6_repeat2` appears on 1 comment line |
| `include-per-camera-latex` | comment only |
| `python -m experiments.` without `-u` | 0 |
| every `run_stage_` body consults `_dry_run_active` | 20/20 |
| `git log --follow` | reaches `29b06a5 feat(19.3-08)` |
| `rerun_19_4.sh` / `rerun_19_5.sh` | present, and absent from `git diff --name-only <base>..HEAD` |
| STATE.md / ROADMAP.md | untouched |

**Dry-run seam exercised** (`RUN_EXPERIMENT_SUITE_DRY_RUN=1`,
`RUN_EXPERIMENT_SUITE_DRY_RUN_CMD=true`, `PRELAUNCH_GATE_PYTHON=/bin/true`): all twenty
stages dispatched in order, `STAGE 1/20 preflight` → `STAGE 20/20 e4_repeat`, in ~6
seconds, no `UNKNOWN STAGE`. Afterwards **only** the `.dryrun.tsv` state file existed
(no real state file — T-26-22 demonstrated, not merely coded) and `git status --porcelain`
showed no deletions. The driver itself was never run for real at any scale.

**Mutation check (the plan's required negative test).** Removing
`reconstruction_bootstrap` from `STAGES=(...)` failed three tests. The bidirectional one
reported, verbatim:

```
AssertionError: manifest stage(s) ['reconstruction_bootstrap'] are in no driver -- this is
the exact shape of F-001: an invocation the paper depends on that no driver ever runs, so
the suite exits 0 while the artifact is never produced. Add a run_stage_<id> function and
an entry in STAGES=(...)
```

The ordering test failed too, but with a bare `KeyError` — so the four ordering tests were
refactored through an `_assert_precedes` helper that asserts membership first with the
anchor named. The driver was then restored byte-identically (`git status --porcelain`
clean apart from the new test file) and re-verified.

## Threat Model Disposition

| Threat | Status |
|---|---|
| T-26-21 (renamed script consumes old state file) | mitigated — sha-derived path; `test_state_path_embeds_the_frozen_sha` |
| T-26-22 (dry run no-ops the next real launch) | mitigated — separate paths, asserted textually **and** demonstrated by the dry run leaving only `.dryrun.tsv` |
| T-26-23 (`rm -rf` on an interpolated path) | mitigated — every isolated out dir is a literal assignment, never from argv; `set -u` |
| T-26-24 (absolute `E2_RELEASE_CONFIG` outside the repo) | mitigated — overridable variable; the generator's release-tree write refusal is untouched |
| T-26-25 (gate ImportErrors under bare `python`) | mitigated — pinned `GATE_PYTHON`; `test_gate_never_runs_under_a_bare_python` |
| T-26-SC (package installs) | N/A — nothing installed, `pyproject.toml` untouched |

## Notes for Plan 26-08

- The stage list is the scheduling input; `_gate_dir_for_stage` mirrors the manifest's
  per-stage `out_dir` and must stay in step with it.
- The sticky-failure flag belongs in `run_gate_check`'s **caller**, not in `run_gate_check`
  — that function's own exit must stay 0 so a gate FAIL never aborts the queue.
- The hard-abort `case` in `run_one_stage` currently lists `preflight|prelaunch_probe`.
  Every refusal added to `run_stage_preflight` must print its override flag (D-50).
- Four stages are `serial_alone` in the manifest (`e4`, `e4_repeat`, `e2_timing`,
  `e2_memory`). This plan only declares them; nothing here enforces it.

## Known Stubs

None. Every stage function issues its real invocation; the only substitution is the
dry-run seam, which is explicitly test-only and never cited as evidence.

## Self-Check: PASSED

- `experiments/run_experiment_suite.sh` — FOUND
- `tests/unit/test_suite_stage_list.py` — FOUND
- `experiments/rerun_19_3.sh` — correctly ABSENT (renamed)
- `experiments/rerun_19_4.sh`, `experiments/rerun_19_5.sh` — FOUND, unmodified
- commits `0402960`, `bdd9dcc`, `a9b12b4`, `35de34f` — FOUND
