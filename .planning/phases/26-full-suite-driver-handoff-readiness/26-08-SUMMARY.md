---
phase: 26-full-suite-driver-handoff-readiness
plan: 08
subsystem: experiments/driver
tags: [driver, preflight, concurrency, sticky-exit, dry-run, tests]
requires:
  - "experiments/run_experiment_suite.sh (26-07): the lifted stage list, the sha-derived state path, the dry-run seam"
  - "experiments/_run_manifest.py (26-02): the manifest emitter, invoked for the first time here"
  - "experiments/_expectations.py + suite_expectations.json (26-03): the completeness gate, its --profile/--stage CLI, and the per-stage depends_on/concurrency/frame_class/est_hours attributes"
provides:
  - "Pre-flight: manifest emission, E2 frameset IDENTITY, the two narrowed D-24 refusals, a crude free-space floor, a gate-invokability precheck and the D-38 wall-clock warning -- each printing its own override flag"
  - "SUITE_FAILED: the sticky flag, the failure log, the loud terminal summary and a final exit code that cannot lie"
  - "The end-of-run completeness roll-up over the whole tree (D-02's third check point)"
  - "The D-52 concurrency pool: manifest-driven admission control, 4 wide, with SUITE_SERIAL=1 as the escape hatch"
  - "tests/unit/test_run_experiment_suite_dryrun.py: the first automated test of any driver script in this repo"
affects:
  - "Phase 27 (Linux handoff): SUITE_OUT_DIR / SUITE_STATE_DIR / SUITE_WORKERS / SUITE_SERIAL are the knobs it repoints; the pool's OpenBLAS behaviour is its two-minute confirmation"
  - "Phase 28 (the production run): schedules against expected_total_with_concurrency_hours, ~15-17 h rather than ~28-31 h serial"
  - "Plan 26-10's full --smoke pass: the ORCHESTRATOR's run, not touched here"
tech-stack:
  added: []
  patterns:
    - "Sentinel-file completion detection instead of `wait -n -p` (needs bash >= 5.1; the driver must behave identically on Git Bash and the Linux run machine)"
    - "A failure LOG FILE rather than a shell variable, because a child process cannot set its parent's variable"
    - "Millisecond ISO stamps in the state TSV, so overlap is observable rather than tied"
    - "Scheduler attributes read from the manifest via a one-shot Python TSV emitter -- bash cannot parse JSON reliably"
key-files:
  created:
    - "tests/unit/test_run_experiment_suite_dryrun.py"
  modified:
    - "experiments/run_experiment_suite.sh"
    - "experiments/suite_expectations.json"
decisions:
  - "D-24 implemented as NARROWED: two refusals, not four. D-46/D-47 supersede it and D-48 cut a third."
  - "run_gate_check keeps its always-return-0 contract; D-01 is implemented in its CALLER via LAST_GATE_EXIT."
  - "SUITE_WORKERS defaults to 4 and is clamped to 4-5, never the probe's recommended_workers: 16."
  - "State-file stamps go to millisecond resolution, because at whole-second resolution a dry run's stages tie and a tie cannot distinguish 'ordered' from 'overlapped'."
metrics:
  tasks: 3
  commits: 2
  tests_added: 20
  test_wall_clock_s: 76
  completed: 2026-08-18
---

# Phase 26 Plan 08: Driver Safety Rails, Concurrency and Its First Test — Summary

Pre-flight now refuses exactly two things and prints an escape hatch for every
refusal; a gate FAIL after stage 1 is sticky rather than fatal and makes the
final exit code non-zero with a loud summary; stages are scheduled 4 wide from
the manifest's own `depends_on` / `concurrency` / `frame_class` attributes; and
the driver has 20 automated tests where it previously had none.

## What Was Built

### Task 1 — Pre-flight (D-03, D-14, D-17, D-19, D-24-as-narrowed, D-50)

`experiments/suite_expectations.json` gained a **new top-level `preflight` key
and nothing else**. It carries the E2 frameset identity signature (262 usable →
52 validation → 7,762 comparisons), the retired archive's signature so a
mismatch report can name what was probably found, a cheap file/byte check the
driver can run in seconds, the crude free-space floor, the override-flag table,
and a `refusals_cut` block naming D-46/D-47/D-48 so nobody restores them.

`run_stage_preflight` now runs, in order: manifest emission → frameset identity
→ non-empty-output-tree refusal → free space → completeness-gate invokability →
the D-38 wall-clock warning. Every refusal names its override flag, and the
abort path in `run_one_stage` reprints all five.

Two things are worth flagging for a future reader:

- **The frameset signature exists nowhere in the shell script, not even in a
  comment.** `grep -c '262' experiments/run_experiment_suite.sh` returns 0. A
  comment is exactly where FIX-06's retired numbers survived.
- **The completeness gate at pre-flight is not judging output.** The tree is
  empty by construction, so it is *expected* to report FAILs; those never
  abort. What is checked is whether the gate RAN AT ALL — a malformed manifest
  or a broken import discovered at hour 18 is the class of failure pre-flight
  exists to convert into a two-minute one. The gate exits 1 both on "artifacts
  missing" and on an uncaught exception, so the exit code cannot distinguish
  them; the presence of its terminal `TOTAL:` line can, and that is the signal.

### Task 2 — Sticky exit, roll-up, concurrency pool (D-01, D-02, D-52)

- `SUITE_FAILED` plus a **failure log file**. A file rather than a variable
  because concurrent stages run in child processes. `main` prints every finding
  in a terminal block and exits `${SUITE_FAILED}`.
- `run_gate_check` keeps its always-return-0 contract. The caller reads
  `LAST_GATE_EXIT` and records a finding. Nothing aborts after stage 1.
- The **end-of-run roll-up** runs the gate over the whole tree with no `--stage`
  selector. Its comment states why Gate 3 cannot own this class:
  `_check_git_sha_consistency` PASSes over an empty tree.
- The **scheduler** reads `depends_on`, `concurrency`, `frame_class` and
  `est_hours` from the manifest and hardcodes no stage name. `serial_alone`
  runs alone and blocks further launches; at most one `frame_class == "200"` in
  flight; at most `SUITE_WORKERS` (4, clamped to 4-5); shortest-first within the
  ready set; per-stage `tee` logs with `PIPESTATUS[0]`.
- `SUITE_SERIAL=1` forces the historical serial path.

### Task 3 — `tests/unit/test_run_experiment_suite_dryrun.py`

20 tests, 76 s. Sequencing, resume, the started-vs-completed distinction,
dry-run state separation, the sticky exit, the pre-flight abort, `--skip-e2`,
serial mode, and all three D-52 constraints.

The ordering assertions run under the **pooled** scheduler, from the state
file's millisecond ISO stamps. A guard test (`test_the_pool_really_did_overlap_something`)
asserts the pooled run genuinely overlapped stages, so none of the others can
pass vacuously — without it, a scheduler that silently degraded to serial would
turn every overlap assertion green while proving nothing.

Named tests the plan asked for by name:

| Requirement | Test |
|---|---|
| `e6_band.start > e6_repeat1.complete` under POOLED mode | `test_e6_band_starts_only_after_e6_repeat1_completes_under_pooled_mode` |
| `e4` after E2 production (O1/O4) | `test_e4_starts_only_after_e2_production_completes_under_pooled_mode` |
| E3 `--check`/`--force` atomicity | `test_e3_check_and_force_stay_atomic_under_pooled_mode` |
| Real state file absent after a dry run | `test_dry_run_does_not_write_the_real_state_file` |

## Verification

| Check | Result |
|---|---|
| `bash -n experiments/run_experiment_suite.sh` | exit 0 |
| `pytest tests/unit/test_run_experiment_suite_dryrun.py -q` | 20 passed, 76 s |
| `pytest ...dryrun.py ...test_suite_stage_list.py ...test_expectations.py -q` | 113 passed, 75 s |
| `suite_expectations.json` `stages` array | **byte-identical** to HEAD (`json.dumps` compared; sha256 `16e667b9f0773373…`) |
| `suite_expectations.json` `artifacts` array | **byte-identical** to HEAD (sha256 `ff56f35c2ba90773…`) |
| `git diff experiments/suite_expectations.json` | 40 insertions, **0 deletions**; only new key is `preflight` |
| `grep -c '262' experiments/run_experiment_suite.sh` | 0 |
| `grep -c 'status --porcelain'` inside `run_stage_preflight` | 0 |
| `grep -c -- '--skip-e2'` | 7 |
| override mentions inside `run_stage_preflight` | 17 |
| `grep -c '_run_manifest'` | 2 |
| `grep -c 'exit "${SUITE_FAILED}"'` | 1, in `main` |
| `grep -c 'PIPESTATUS'` | 4 |
| `grep -c 'serial_alone'` / `'frame_class'` / `'F-001'` | 9 / 5 / 7 |
| `SUITE_WORKERS` default | `${SUITE_WORKERS:-4}`, clamped to 4-5 |
| `subprocess.run(` vs `timeout=` in the test file | 3 vs 4 — every call carries one |

**No experiment ran.** Every driver invocation in this plan's work went through
the dry-run seam with `RUN_EXPERIMENT_SUITE_DRY_RUN=1` and both `SUITE_OUT_DIR`
and `SUITE_STATE_DIR` redirected into a sandbox. `experiments/results` was never
written. The full pytest suite was not run — that is the orchestrator's
post-merge gate.

## Deviations from Plan

### Auto-fixed / adjusted

**1. [Rule 3 — blocking] `run_gate_check`'s invocation line gained `--profile` /
`--stage`.**
- **Found during:** Task 2.
- **Issue:** the acceptance criterion asks for no removed line inside
  `run_gate_check`, but `check_rerun_gates.py` runs the completeness gate *only*
  when `--profile` is passed. Without it there is no per-stage completeness
  check at all, and D-02's second check point plus the plan's own `key_links`
  (`--profile`) would both be unmet.
- **Fix:** the one invocation line was extended, not removed. The
  always-return-0 contract, the verdict-block framing and every other line of
  the function are untouched; the sticky flag is set entirely by the caller.
- **Diff evidence:** the driver's whole diff removes exactly one line inside
  that function — that invocation — and adds its replacement.

**2. [Rule 1 — bug] State-file stamps moved to millisecond resolution.**
- **Found during:** Task 3.
- **Issue:** at whole-second resolution every stage of a dry run shares a
  timestamp, so `e6_band.start > e6_repeat1.complete` could not be distinguished
  from an overlap. The plan's highest-consequence assertion would have been
  untestable, or testable only as `>=`, which passes trivially on a tie.
- **Fix:** `STATE_TIME_FMT` uses `%3N`, with a runtime probe that degrades to
  whole seconds if the platform's `date` lacks the GNU extension. Format stays
  ISO-8601 and stays `datetime.fromisoformat`-parseable.

**3. [Rule 3 — blocking] Test sandbox overrides added to the driver.**
- `SUITE_OUT_DIR` and `SUITE_STATE_DIR`. Without them there is no way to run the
  driver in a test at all without writing into `experiments/results`. Both are
  documented as test-only. `STATE_FILE` still has exactly two assignments, both
  carrying `${FROZEN_SHA}`, so `test_suite_stage_list.py`'s dry-run-separation
  and sha-embedding assertions still hold.

**4. [Rule 3 — blocking] `bash` is resolved explicitly in the test module.**
- On Windows, `CreateProcess` searches `System32` before `PATH`, so
  `subprocess.run(["bash", ...])` finds **WSL's** bash, which cannot see a
  `C:/...` path and fails with a bare "No such file or directory" naming a file
  that plainly exists. The module now probes candidate interpreters and picks
  the first that can actually stat the driver, skipping the module if none can.

**5. [process] Tasks 1 and 2 share one commit.**
- Both edit `experiments/run_experiment_suite.sh` and were implemented in a
  single pass. Splitting them afterwards would mean synthesizing an intermediate
  file state that never existed and was never verified. The commit message names
  both task scopes separately.

**6. [scope] The pre-flight checks are exercised through the stub, not for real.**
- Under the dry-run seam `run_stage_preflight` short-circuits, so the tests
  assert the ABORT PATH (via a stub that fails for `preflight`) and the override
  messages, not the individual refusal predicates. Running them for real would
  mean invoking the driver outside the seam, which this plan forbids. The
  refusal bodies are covered textually by the driver's own greps above and will
  be exercised end-to-end by plan 26-10's `--smoke` pass, which is the
  orchestrator's run.

### Not implemented, deliberately

- **No dirty-tree refusal** (D-47), **no disk-headroom estimator** (D-46), **no
  HEAD-vs-state refusal** (D-48). All three are named in a comment at the
  pre-flight block and in the manifest's `preflight.refusals_cut`.
- **No `e6_band` seed-level split** (CONTEXT § E declines it).
- **No Python rewrite of the driver** (D-26).

## Deferred Issues

None.

## Known Stubs

None. The dry-run stub is a test seam, not an unwired code path: it is gated
behind `RUN_EXPERIMENT_SUITE_DRY_RUN` and every production invocation runs the
real body.

## Threat Flags

None. No new network endpoint, auth path, file-access pattern or schema change
at a trust boundary. The one new file-access pattern — pre-flight reading the E2
release config and stat-ing its declared extrinsic videos — is read-only, inside
the trust boundary the plan's threat model already names, and mitigates T-26-28
rather than adding surface.

## Self-Check: PASSED

- `experiments/run_experiment_suite.sh` — FOUND
- `experiments/suite_expectations.json` — FOUND
- `tests/unit/test_run_experiment_suite_dryrun.py` — FOUND
- commit `edf6f49` (tasks 1-2) — FOUND
- commit `7fcc413` (task 3) — FOUND
