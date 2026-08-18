---
phase: 26-full-suite-driver-handoff-readiness
plan: 11
subsystem: experiments-driver
tags: [driver, smoke, acceptance, dry-run-seam, gap-closure]
requires:
  - "experiments/run_experiment_suite.sh (26-07)"
  - "tests/unit/test_run_experiment_suite_dryrun.py (26-08)"
  - "experiments/suite_expectations.json (26-03, READ ONLY)"
provides:
  - "`--smoke` / `SUITE_SMOKE=1` reduced-scale pass over the whole queue"
  - "`_record_dispatch`: the dispatched argv is observable through the dry-run seam"
  - "A frozen 17-line snapshot of the full-scale dispatch list"
affects:
  - "26-10's acceptance step, which was unrunnable before this plan"
tech-stack:
  added: []
  patterns:
    - "One invocation line per stage, varying only by `$(_smoke_args)` -- never two stage bodies for two modes"
    - "Test-only observability via an env-gated recorder, alongside the existing SUITE_MARKER convention"
key-files:
  created: []
  modified:
    - experiments/run_experiment_suite.sh
    - tests/unit/test_run_experiment_suite_dryrun.py
    - .gitignore
decisions:
  - "e7_interface_ablation DOES honor --smoke; the plan's verified list omitted it. Added (measured, not assumed)."
  - "e4_repeat is skipped under --smoke as a second DECLARED REDUCTION: both its invocation shapes refuse the flag."
  - "Every sibling out dir moves with OUT_DIR under smoke, because run_stage_e2_band opens with `rm -rf`."
  - "`--smoke` is documented as the fourth exception to the parser's pre-flight-override rule, NOT added to the manifest's `preflight.overrides`."
metrics:
  duration: ~2.5 h
  completed: 2026-08-18
  tasks: 2
  commits: 2
  files_changed: 3
---

# Phase 26 Plan 11: Driver Reduced-Scale Path Summary

`bash experiments/run_experiment_suite.sh --smoke` now runs the whole queue at
reduced scale in minutes, forcing its own `experiments/results_smoke` tree, so a
mistyped flag in any of twenty invocation lines surfaces before the frozen 22-31
hour run rather than eighteen hours into it.

## What Was Built

### Task 1 — the reduced-scale path (`5c0faee`)

| Piece | What it does |
|-------|--------------|
| `--smoke` / `SUITE_SMOKE=1` | Selects the reduced-scale pass. Documented in `usage()` under its own heading. |
| `_smoke_args` | The single place the flag is decided; interpolated unquoted into each supporting stage's one invocation line. |
| `_record_dispatch` | Env-gated (`SUITE_DISPATCH_LOG`) recorder of the argv a stage was about to launch. No-op in any real run. |
| Smoke resolution block | Re-points `OUT_DIR` and every sibling tree, and defaults `PROFILE` to `smoke` only when `--profile` was not given. |
| Two skip gates | `e7_focal_standoff` and `e4_repeat`, each with a DECLARED REDUCTION line, each returning 0. |
| Launch banner | States loudly that the pass is not evidence, names both skipped stages and the reason for each. |

### Task 2 — the tests (`cc3c28d`)

15 new tests in three classes, all through the dry-run seam, none running an
experiment. 35 pass in 155 s (20 pre-existing + 15 new); `-k smoke` selects 12.

## The Problem This Solved

Plan 26-10 asked the orchestrator to run a `--smoke` acceptance pass. It could
not: the driver threaded `--smoke` to no stage, and `--profile smoke` selects
only the completeness gate's expectation profile. Following 26-10's launch line
would have started the **full-scale production suite** while grading it against
smoke expectations.

The deeper reason the path is worth having: the dry-run seam substitutes the
*entire* command, so it proves sequencing, resume and gate wiring and can never
prove a stage's invocation line is correct. `_record_dispatch` closes that gap
even without `--smoke` — the argv is now assertable.

**26-07's rationale is preserved, not deleted.** Every acceptance and production
run is still at full scale, never substituted. The banner, the usage text and
the code comments all say so. A `--smoke` pass proves one narrow thing: that
each stage's invocation line is correct.

## Deviations from Plan

### `[Rule 1 - Bug] The plan's verified support list omitted e7_interface_ablation`

- **Found during:** Task 1, before writing any code.
- **Issue:** The plan named eight scripts as accepting `--smoke` and did not
  include `e7_interface_ablation`. It has 20 `smoke` references and a genuine
  smoke branch with the standard SP-7 default-out check at
  `e7_interface_ablation.py:918`.
- **Fix:** `e7` and `e7_band` receive the flag. Without this, E7's two stages
  (~1-2 h) would have run at full scale inside a pass whose purpose is minutes.
- **Verified:** argparse-level probe (parse-only, nothing executed) over the
  exact argv the driver builds for every stage.
- **Commit:** `5c0faee`

### `[Rule 2 - Missing critical functionality] e4_repeat needs a second DECLARED REDUCTION`

- **Found during:** Task 1, same probe.
- **Issue:** The plan named only `e7_focal_standoff` as skipped. But
  `e4_benchmark_grid` **refuses** `--cell` with `--smoke` and `--splice-repeat`
  with `--smoke` (`:1890-1893`, exit 2). `e4_repeat` uses both. It could neither
  take the flag (exit 2, a spurious failure) nor run without it (~1 h at full
  scale).
- **Fix:** Skipped with its own DECLARED REDUCTION line, returning 0. The
  manifest already lists its artifact as `full`-profile only, so the roll-up
  does not count the omission — no manifest change was needed or made.
- **Commit:** `5c0faee`

### `[Rule 1 - Bug] A smoke pass would have deleted the production E2 band tree`

- **Found during:** Task 1, after the first working smoke dry run.
- **Issue:** `run_stage_e2_band`'s first act is `rm -rf "${OUT_DIR_E2_BAND}"`.
  The plan re-pointed only `OUT_DIR`. Left at its production value,
  `experiments/results_e2_band` — three 48-87 minute calibrations — would have
  been destroyed by a rehearsal. `run_stage_e4_repeat` has the same shape
  against `experiments/results_e4_repeat`.
- **Fix:** Under smoke, `OUT_DIR_E4_REPEAT`, `OUT_DIR_E2_BAND`,
  `OUT_DIR_E2_TIMING`, `OUT_DIR_E2_MEMORY` and `E2_INVOCATION_DIR` (with its
  three derived config paths) all move to `results_smoke_*`. `.gitignore` gained
  the matching glob. `test_smoke_moves_every_sibling_out_dir_too` is the rail.
- **Commit:** `5c0faee`

### `[Deviation - Counting] "Exactly 8 stages receive the flag" was a category error`

The plan's `<why_this_plan_exists>` lists **eight experiment SCRIPTS** that
accept `--smoke`. Its acceptance criterion restated that as "exactly 8 stage
invocation lines". Those are different things: 20 driver stages map onto ~10
scripts, and several scripts own two or more stages (`e1`/`e1_band`,
`e5`/`e5_band`, four E2 stages). Eight stages taking the flag would have left
eleven running at full scale, contradicting the plan's own truth #1 — *"the
driver can run every stage at reduced scale in one pass"*.

**Measured outcome, all verified at the argparse level and again empirically
through the seam:**

| Count | What |
|-------|------|
| 16 | dispatched invocation lines carry `--smoke` (15 distinct stages; `e3` dispatches twice) |
| 2 | stages skipped with a DECLARED REDUCTION (`e7_focal_standoff`, `e4_repeat`) |
| 2 | stages dispatch no experiment at all (`preflight`, `prelaunch_probe`) |
| 3 | invocations correctly withhold the flag because the experiment refuses it: `--emit-invocation-configs`, `--emit-band-configs`, `e4_repeat`'s two shapes |

## Verification

### The full-scale path did not move

Two independent proofs:

1. **Static.** A normalizer extracted every `python -u -m experiments.*` argv
   from `git show HEAD:experiments/run_experiment_suite.sh` and from the changed
   file, dropping `$(_smoke_args)`. Both produced 22 invocations, **identical**.
2. **Empirical, and now permanent.** A no-smoke dry run's 17 dispatched lines
   are frozen as `_FULL_SCALE_DISPATCH_SNAPSHOT` in the test file, with a
   companion test asserting the snapshot's stage coverage against the manifest
   so it cannot pass by capturing nothing.

### Commands run

| Check | Result |
|-------|--------|
| `bash -n experiments/run_experiment_suite.sh` | clean |
| `bash experiments/run_experiment_suite.sh --help` | documents `--smoke` under its own heading |
| `pytest tests/unit/test_run_experiment_suite_dryrun.py tests/unit/test_suite_stage_list.py` | **51 passed** in 155 s |
| `pytest ... -k smoke --collect-only` | 12 selected (plan asked for >= 6) |
| `git diff experiments/suite_expectations.json` | empty |
| `grep -c 'subprocess.run(' / 'timeout='` | 3 / 4 — unchanged from HEAD, no new `subprocess.run` added |

**The driver was never run outside the dry-run seam.** Every invocation used
`RUN_EXPERIMENT_SUITE_DRY_RUN=1`, or was `bash -n` / `--help`. The reduced-scale
smoke pass itself remains the orchestrator's to run.

## Known Limitations

These are properties of the experiments, not of this plan, and they bound what a
reduced-scale pass can prove:

- **E2's `--smoke` returns before it reads `--config`** (`e2_real_rig.py:428`),
  writing stub CSVs to a temp dir or printing `SKIPPED` when the dataset is not
  cached. So the pass verifies E2's flag *names* but cannot catch a bad config
  *path*. CONTEXT already notes `--smoke` cannot catch a bad production YAML.
- **E1's single-seed `--smoke` always uses a temp dir** regardless of `--out`
  (`:893`), so `e1` writes nothing under smoke. E1's `--seeds` band path does
  land. The manifest's `smoke` profile already encodes both facts.
- **The two E2 config emitters run full-fidelity** under smoke, since they
  refuse the flag. On a box without the release config they will fail and set
  the sticky flag — honest, and the same as a real run.
- **`e4_repeat` and `e2_band` are invisible to the snapshot rail**: both build
  their invocations only after the dry-run seam returns. They are the only two,
  and `test_the_snapshot_covers_every_stage_that_can_be_observed` names them
  explicitly so the gap cannot be mistaken for drift.

## TDD Gate Compliance

Task 2 carried `tdd="true"`, but its subject was Task 1's already-committed
behavior, so a meaningful RED gate was not available: the commits are
`feat` then `test`, not `test` then `feat`. The tests are not vacuous — before
`5c0faee` the driver rejected `--smoke` with `unrecognised argument` and exit 2,
so every test in `TestSmokeMode` and `TestSmokeAndProfileStaySeparable` would
have failed, and `_record_dispatch` did not exist, so all four
`TestFullScalePathDidNotMove` tests would have failed on an empty dispatch list.

## Self-Check: PASSED

- `experiments/run_experiment_suite.sh` — FOUND, modified
- `tests/unit/test_run_experiment_suite_dryrun.py` — FOUND, modified
- `.gitignore` — FOUND, modified
- `experiments/suite_expectations.json` — FOUND, unmodified (`git diff` empty)
- Commit `5c0faee` — FOUND
- Commit `cc3c28d` — FOUND
- `STATE.md` / `ROADMAP.md` — NOT modified, as instructed
