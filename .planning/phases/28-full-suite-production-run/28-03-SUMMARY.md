---
phase: 28-full-suite-production-run
plan: 03
subsystem: infra
tags: [production-run, experiment-suite, acceptance, roll-up, provenance, evidence, wall-clock]

# Dependency graph
requires:
  - phase: 28-full-suite-production-run
    plan: 02
    provides: "the 183-line pre-launch assertion record at /home/tlancaster/freeze02-prelaunch-assertions.txt, 15 PASS / 0 FAIL, which task 1's authorisation was taken against"
  - phase: 29.1-post-run-fixes-re-freeze
    provides: "the rerun-freeze-02 tag (533f79fb -> 7005a27) that licenses this run, D-28 (set PRELAUNCH_GATE_PYTHON explicitly), D5 (state-file collision -- run from a fresh clone, never ~/aquacal-frozen-rerun-freeze-02), and the 176/7/0 roll-up reference"
  - phase: 26-full-suite-driver-handoff-readiness
    provides: "D-01 (the queue continues past a gate finding and the driver exits non-zero) and D-02 (the end-of-run completeness roll-up is the verdict)"
provides:
  - "The completed v2.1 full-suite production run at 7005a27: 20/20 stages at exit 0, 2026-08-25T00:47:07Z -> 06:48:28Z"
  - "Six output trees and three driver state artifacts in the production clone, untouched and unarchived (plan 04 preserves them)"
  - "/home/tlancaster/freeze02-rollup.txt -- the end-of-run completeness roll-up, 218 lines, TOTAL: 176 PASS, 7 N/A, 0 FAIL"
  - "/home/tlancaster/freeze02-stage-timing.txt -- per-stage start/end/duration/exit for all 20 stages with attempt-1 deltas; the only per-stage timing record this run has"
  - "The acceptance verdict established from the three hard signals, with the exit code explicitly excluded"
affects: [28-04-preserve-the-output, 28-05-run-record, 29-gate-verification-results-commit]

actuals:
  tokens: 3900
  tasks: 3
  commits: 1

tech-stack:
  added: []
  patterns:
    - "Acceptance read from three named signals (roll-up TOTAL, failures file, state TSV) with the exit code excluded by construction, never from $?"
    - "The production-vs-rehearsal distinction asserted positively in the returned log by the absence of the smoke disclaimer banner, rather than assumed from the invocation"
    - "Per-stage wall clock derived from the state TSV's ISO stamps and printed beside attempt 1's, so a schedule divergence is visible as a delta rather than needing reconstruction"

key-files:
  created:
    - /home/tlancaster/freeze02-rollup.txt
    - /home/tlancaster/freeze02-stage-timing.txt
  modified: []

key-decisions:
  - "The operator launched through /home/tlancaster/launch_freeze02.sh, a fail-closed wrapper, rather than pasting the plan's raw block. The wrapper re-checks the plan's three volatile facts plus three more (output trees absent, interpreter identity, aquacal import path), refuses to launch if any fails, refuses to overwrite an existing log, exports PRELAUNCH_GATE_PYTHON, and then issues the identical nohup line. A faithful superset of the plan's instruction, recorded here rather than passed over."
  - "Acceptance was taken at the end-of-run roll-up. The driver exited non-zero, as a healthy run does by construction (D-01); $? was never read as the verdict."
  - "The 17 GATE FAIL findings are reported as a count and labelled expected-by-construction. Nothing in check_rerun_gates.py, suite_expectations.json or the driver was edited to reduce them -- that would be a change to the frozen tree."
  - "176 PASS / 7 N/A / 0 FAIL is quoted beside 29.1-02's predicted 176/7/0 as a reference that was met, not as a target that was tuned toward. No gate, manifest or expectation was touched between the tag and this run; the clone's tracked tree is byte-identical to the tag."

patterns-established:
  - "The run log lands outside both the clone and the output tree, so capturing it cannot trip the driver's own non-empty-tree refusal"

requirements-completed: [RUN-02]

coverage:
  - id: D1
    description: "The v2.1 full-suite production run executed to completion at the frozen sha, 20/20 stages at exit 0"
    requirement: RUN-02
    verification:
      - kind: automated
        ref: "awk -F'\\t' '$3==\"complete\" && $5==0' run_experiment_suite_state.7005a27.tsv | wc -l  =>  20; non-zero-exit filter prints nothing"
        status: pass
  - id: D2
    description: "The end-of-run completeness roll-up over experiments/results at profile full reports zero FAIL"
    requirement: RUN-02
    verification:
      - kind: automated
        ref: "tail of /home/tlancaster/freeze02-rollup.txt  =>  TOTAL: 176 PASS, 7 N/A, 0 FAIL; grep -c 'NOT FOUND' => 0"
        status: pass
  - id: D3
    description: "The returned log is provably a production log and its artifacts carry the frozen sha"
    requirement: RUN-02
    verification:
      - kind: automated
        ref: "grep -c 'NOTHING THIS RUN PRODUCES IS EVIDENCE' suite_run_freeze02.log => 0; run_manifest.json git_sha == 7005a27...; gate3_git_sha_consistency / gate3_run_manifest_fields / gate3_run_manifest_clean_tree all PASS"
        status: pass
  - id: D4
    description: "Per-stage wall clock derived and compared against the measured baseline"
    requirement: RUN-02
    verification:
      - kind: automated
        ref: "/home/tlancaster/freeze02-stage-timing.txt -- 20 stage rows plus total; 6h 01m 21s vs 6h 00m 21s, e6_band 3h 36m 01s vs 3h 35m 24s"
        status: pass
---

# Phase 28 Plan 03: The Production Run Summary

**The v2.1 full-suite production run ran to completion at `7005a27` in 6 h 01 m 21 s — 20/20 stages at exit 0, `TOTAL: 176 PASS, 7 N/A, 0 FAIL`, zero `STAGE FAILED` lines, and 17 `GATE FAIL` findings that are expected by construction. All three hard signals are green. The driver exited non-zero, as a healthy run does; the exit code was not read as the verdict.**

## Performance

- **Duration:** 6 h 01 m 21 s (the run) + readout
- **Started:** 2026-08-25T00:47:07.773Z
- **Completed:** 2026-08-25T06:48:28.378Z
- **Tasks:** 3
- **Files created:** 2 (off-repo by plan design; plan 05 routes the `freeze02-*` set into the phase directory)

## The verdict — three hard signals

| # | Signal | Required | Measured | Verdict |
|---|---|---|---|---|
| 1 | End-of-run completeness roll-up | `0 FAIL` | **`TOTAL: 176 PASS, 7 N/A, 0 FAIL`** | **GREEN** |
| 2 | `STAGE FAILED` lines in the failures file | 0 | **0** | **GREEN** |
| 3 | State file: `complete` at exit 0 | 20, none non-zero | **20**, non-zero filter prints nothing | **GREEN** |

**The exit code was not used as the verdict.** The driver exited non-zero, which is the designed behaviour of a healthy run under D-01: the queue continues past a per-stage gate finding so every stage's measurements are still taken, and the non-zero exit exists so the run cannot be mistaken for green. F-001 — the failure this convention was built against — was a run that *exited 0* while a band CSV was never produced.

**Zero `NOT FOUND` lines in the roll-up.** Every artifact the manifest expects this run to produce at profile `full` was produced.

### The 17 `GATE FAIL` findings, labelled

17 sticky per-stage findings, one per stage from 3 to 20 excluding `e4` (stage 17):

    fd_jacobian(3)  e1(4)  e7(5)  e5(6)  e2_production(7)  e6_repeat1(8)  e3(9)
    reconstruction_bootstrap(10)  e2_timing(11)  e2_memory(12)  e7_band(13)
    e5_band(14)  e2_band(15)  e1_band(16)  e6_band(18)  e7_focal_standoff(19)
    e4_repeat(20)

These are **expected by construction, not defects.** `check_rerun_gates.py` evaluates every experiment against whichever out-dir the stage that invoked it used, so a stage finishing early necessarily sees artifacts that later stages have not written yet, and the four stages writing to sibling trees (`results_e2_timing`, `results_e2_memory`, `results_e2_band`, `results_e4_repeat`) see trees that legitimately hold only their own output.

The mechanism is visible in the log as a monotonic decline in the per-stage FAIL count over `experiments/results`: **89 → 31 → 25 → 13 → 8 → 8 → 8 → 8 → 7 → 7 → … → 0.** Stage 17 (`e4`) — the last gate to run against `experiments/results`, by which point every contributing stage had finished — reports **`TOTAL: 112 PASS, 8 N/A, 0 FAIL`**, and is for that reason the one stage with no `GATE FAIL` finding. Attempt 1 produced 18 findings at this point: the same 17 plus `e4`, plus a `ROLL-UP FAIL`.

Nothing in `check_rerun_gates.py`, `suite_expectations.json` or the driver was edited to reduce the count.

## Manifest and provenance gates

All three quoted verbatim from `/home/tlancaster/freeze02-rollup.txt`:

    [PASS] ALL gate3_git_sha_consistency     every artifact carries the same git_sha
                                             (7005a2771aa115e4f4c1284cec7e145739586a4a)
    [PASS] ALL gate3_run_manifest_fields     all 17 required environment fields are present and non-null
    [PASS] ALL gate3_run_manifest_clean_tree the working tree was clean when this run started

The clean-tree PASS is the meaningful one and it is a statement about **launch time**, not now. The tree is dirty now — `experiments/results/` is a tracked path and goes dirty the moment stage 1 writes — and that is expected and is not what this gate judges.

`experiments/results/run_manifest.json`, recorded as the plan asks:

| Field | Value |
|---|---|
| `git_sha` | `7005a2771aa115e4f4c1284cec7e145739586a4a` — the frozen sha |
| `git_describe` | `v2.0.1-346-g7005a27` |
| `aquacal_version_declared` | `2.0.1` |
| `installed_distribution_version` | `2.0.1` — agrees with the declared version, so the run did not import from a stale editable install elsewhere |
| `cpu_count_logical` | `32` — non-null |
| `ram_total_bytes` | `33351241728` (31.06 GiB) — non-null |

`cpu_count_logical` and `ram_total_bytes` are the two fields the `bench` extra exists to populate, and are the two that came back null on attempt 1's target before 29.1-04 corrected `HANDOFF.md` §1.2 to install `.[dev,bench]`. Both are populated here. **The field is named `aquacal_version_declared`, not `aquacal_version`** — worth recording, because the plan's acceptance text names the latter and a literal lookup returns `None`.

## The log is a production log, not a rehearsal

    grep -c 'NOTHING THIS RUN PRODUCES IS EVIDENCE' /home/tlancaster/suite_run_freeze02.log  ->  0

The driver prints that disclaimer banner during every `--smoke` run. Its absence, asserted rather than assumed, is what makes the returned log unambiguously a production log. The header agrees: `Scale: FULL (production). Output tree: experiments/results.`

## Invocation parity

| Item | State | Consequence |
|---|---|---|
| `SUITE_E2_RELEASE_CONFIG` | **unset** (D-12) | driver resolved the in-repo default: `experiments/configs/e2_release_linux.yaml` |
| `PRELAUNCH_GATE_PYTHON` | **set explicitly** (D-28) | log records `gate=…/envs/aquacal-freeze02-prod/bin/python (rung: PRELAUNCH_GATE_PYTHON override)` |
| `SUITE_DISPATCH_LOG` | **unset** (B1) | ROADMAP criterion 3 stays a *derived* argument; the derivation is carried into `28-RUN-RECORD.md` by plan 05 |
| `SUITE_SERIAL`, `SUITE_OUT_DIR`, `SUITE_STATE_DIR`, `SUITE_STAGE_PYTHON`, `RUN_EXPERIMENT_SUITE_DRY_RUN` | **unset** | pooled 4-wide, default thread cap, real state path |
| Pre-flight override flags | **none** — `grep -cE 'allow-nonempty-out\|skip-e2\|allow-frameset-mismatch'` → **0** | the pre-flight was satisfied, not bypassed |
| E2 frameset identity | `preflight: E2 frameset identity check PASSED` | E2 ran against the real rig, not `--skip-e2` synthetic-only |

## Deviation: the launch wrapper

The operator launched through `/home/tlancaster/launch_freeze02.sh` rather than pasting the plan's verbatim block. Recording it because it is a difference from the written instruction, and because the script is part of the run's provenance.

The wrapper is a **fail-closed superset** of the plan's block. It re-checks the plan's three volatile facts (tracked tree clean, no real state file, `SUITE_` namespace empty) and adds three more — output trees absent, `which python` identical to the production env interpreter, and `aquacal.__file__` resolving inside the clone — then refuses to launch if any check fails, refuses to launch if the log already exists, exports `PRELAUNCH_GATE_PYTHON`, and issues the identical `nohup bash experiments/run_experiment_suite.sh > "$LOG" 2>&1 & disown` line. It prints the "healthy run exits non-zero with ~17 GATE FAIL lines, never judge by `$?`" warning at launch.

No check was overridden and no flag was added. The wrapper strengthens the precondition rather than relaxing it.

## The schedule

Full per-stage table in `/home/tlancaster/freeze02-stage-timing.txt`. Against the plan's two named reference figures, both measured on this same machine on 2026-08-20:

| | Baseline (attempt 1) | This run | Delta |
|---|---:|---:|---:|
| **Total wall clock** | 6 h 00 m 21 s | **6 h 01 m 21 s** | +1 m 00 s |
| **`e6_band`** (critical path) | 3 h 35 m 24 s | **3 h 36 m 01 s** | +37 s |

**No material divergence.** The largest single-stage deltas are `e1_band` at −1 m 12 s and `e4` at +1 m 09 s; every other stage is within ±41 s. `e6_band` remains the critical path at 60% of the run. Recorded as an observation, not a gate.

The two stages no rehearsal at any scale exercises — `e7_focal_standoff` (19) and `e4_repeat` (20) — both completed at exit 0, in 0.4 s and 22 m 52 s.

## The clone did not move under the run

    git diff --stat HEAD -- src/ experiments/*.sh experiments/*.py   ->  (empty)

Nothing inside the production clone was edited, at any point, by anyone. The nine untracked output paths are the run's own writes and are all that `git status --porcelain` reports.

## Task Commits

1. **Task 1: authorise the six-hour burn** — `checkpoint:decision`, selection **`launch-now`**, taken against `/home/tlancaster/freeze02-prelaunch-assertions.txt` (15 PASS / 0 FAIL, final line `ALL PRELAUNCH ASSERTIONS PASSED`), the measured 6 h 00 m 21 s schedule with `e6_band` named as the 3 h 35 m critical path, and the statement that a healthy run exits non-zero with ~17 gate findings.
2. **Task 2: operator launches and returns** — `checkpoint:human-action`, one detached invocation, no intervention, log at `/home/tlancaster/suite_run_freeze02.log` (4,645 lines).
3. **Task 3: read the verdict and capture the roll-up** — evidence files written; the plan's automated verify returns `OK`.

## Files Created/Modified

Off-repo by plan design; plan 05 routes the `freeze02-*` evidence set into the phase directory.

- `/home/tlancaster/freeze02-rollup.txt` — 218 lines, 41,168 bytes, begins at `END-OF-RUN COMPLETENESS ROLL-UP (D-02, profile=full)`, last `TOTAL:` line is `TOTAL: 176 PASS, 7 N/A, 0 FAIL`
- `/home/tlancaster/freeze02-stage-timing.txt` — 37 lines, 3,773 bytes, 20 stage rows with start/end/duration/exit and attempt-1 deltas, plus a total line

Nothing inside the production clone was created, modified, moved or deleted by this plan. The run's own nine output paths are untouched and unarchived — that is plan 04's job and it must happen before anything else touches them.

## The reference, and why meeting it is not tuning

29.1-02 predicted `TOTAL: 176 PASS, 7 N/A, 0 FAIL` for the full-profile roll-up, and this run reports exactly that. **The reference is a reference.** Nothing was tuned toward it: no gate, manifest, expectation or driver file was edited between the tag being cut and this run, and the production clone's tracked tree is byte-identical to `rerun-freeze-02` (`git diff --stat HEAD` over `src/` and the driver is empty). Attempt 1's roll-up read `175 PASS, 7 N/A, 2 FAIL`; the two FAILs it carried were closed in phase 29.1 by amending expectations to match documented design, and both are recorded in the tag annotation.

## What this plan does NOT establish

**This phase reports; it does not grade.** Whether the run's *numbers* are correct, reproduce attempt 1, or support the manuscript's claims is Phase 29's question, not this one. Signals 1–3 establish that the run completed and produced what the manifest expects — nothing more.

Two items are handed forward explicitly:

1. **D1's 8 `tests/unit/test_experiments_provenance.py` failures should now return.** They went dormant only because 29.1-06 emptied `experiments/results/`, which made `_baseline_paths.resolve_results_dir()` fall back to the archive. `experiments/results/` is repopulated as of this run, so the fallback no longer applies. 29.1-VERIFICATION-BAR predicted this in terms — *"the 8 failures return the moment a re-run repopulates `experiments/results/`, which is the next thing that happens after the tag."* Phase 29's business.
2. **D4's 3 exact-equality anchor failures** remain as ruled on in the tag annotation and `29.1-PREPUSH-AUDIT.md` §1. Untouched by this run.
