---
phase: 28-full-suite-production-run
plan: 05
subsystem: infra
tags: [provenance, evidence, run-record, gates, environment-verification, handoff]

# Dependency graph
requires:
  - phase: 28-full-suite-production-run
    plan: 04
    provides: "the read-only archive and checksums, freeze02-tree-state-at-handoff.txt and freeze02-archive-manifest.txt"
  - phase: 28-full-suite-production-run
    plan: 03
    provides: "freeze02-rollup.txt and freeze02-stage-timing.txt, and the three-hard-signals verdict"
  - phase: 28-full-suite-production-run
    plan: 01
    provides: "freeze02-install-command.txt, freeze02-env.txt, freeze02-pip-freeze.txt and the D4 pytest confirmation"
provides:
  - "/home/tlancaster/freeze02-gates-full.txt -- the post-run completeness gate re-run over the returned tree, TOTAL: 176 PASS, 7 N/A, 0 FAIL, zero FAIL lines"
  - "Proof that the environment did not move under the run: post-run pip freeze byte-identical to the pre-launch capture"
  - "The eleven-file freeze02-* evidence set committed beside attempt 1's freeze01-* set"
  - ".planning/phases/28-full-suite-production-run/28-RUN-RECORD.md -- the document Phase 29 opens first"
affects: [29-gate-verification-results-commit]

actuals:
  tokens: 8200
  tasks: 2
  commits: 1

tech-stack:
  added: []
  patterns:
    - "The post-run gate is re-run as an independent capture rather than trusting the in-run roll-up, so the two totals can be compared and a disagreement would itself be a finding"
    - "Environment immutability across a six-hour run proven by diffing pip freeze against the pre-launch capture, not asserted"
    - "The run record carries derivations, not just measurements, so a criterion graded by argument rather than by observation does not have to be reconstructed later"

key-files:
  created:
    - /home/tlancaster/freeze02-gates-full.txt
    - .planning/phases/28-full-suite-production-run/28-RUN-RECORD.md
    - ".planning/phases/28-full-suite-production-run/freeze02-*.txt (11 files copied)"
    - .planning/phases/28-full-suite-production-run/rerun-freeze-02-output.sha256
  modified: []

key-decisions:
  - "The post-run gate capture was transcribed, not adjudicated. It contains zero FAIL lines, so there was nothing to classify -- but the record says explicitly that classification would have been Phase 29's RUN-03, not this plan's."
  - "The two attempts' pip freeze files were diffed and found NOT identical: five dev-tooling packages drifted. Recorded prominently rather than passed over, because the reproducibility claim rests on the numerical stack being identical -- which it is -- and someone would otherwise assume the whole environment was."
  - "Phase 29's success criterion 6 was flagged upward as unsatisfiable rather than silently failed: its 2026-08-21 submission date has passed and this run finished 2026-08-25."

patterns-established:
  - "An evidence set is committed under a per-attempt prefix beside its predecessor rather than replacing it, so two attempts compare line for line"

requirements-completed: [RUN-02]

coverage:
  - id: D1
    description: "The post-run completeness gate was re-run over the returned tree and captured whole"
    requirement: RUN-02
    verification:
      - kind: automated
        ref: "check_rerun_gates.py experiments/results --profile full  =>  TOTAL: 176 PASS, 7 N/A, 0 FAIL; zero [FAIL] lines; agrees with the in-run roll-up"
        status: pass
  - id: D2
    description: "The environment that produced the run is proven to be the one already on record"
    requirement: RUN-02
    verification:
      - kind: automated
        ref: "diff freeze02-pip-freeze.txt <(pip freeze) => empty; aquacal.__file__ under the clone; cv2 4.13.0"
        status: pass
  - id: D3
    description: "The gate run wrote nothing into the frozen tree"
    requirement: RUN-02
    verification:
      - kind: automated
        ref: "diff <(git status --porcelain) freeze02-tree-state-at-handoff.txt => identical"
        status: pass
  - id: D4
    description: "The freeze02 evidence set and 28-RUN-RECORD.md are committed beside attempt 1's"
    requirement: RUN-02
    verification:
      - kind: automated
        ref: "11 freeze02-*/sha256 files non-empty in the phase dir; 28-RUN-RECORD.md carries the sha, criterion 3, SUITE_DISPATCH_LOG, 'not clean', all three node ids and the Phase 29 boundary"
        status: pass
---

# Phase 28 Plan 05: Run Record Summary

**The post-run gate over the returned tree reports `TOTAL: 176 PASS, 7 N/A, 0 FAIL` with zero `FAIL` lines, agreeing exactly with the run's own roll-up. The environment is proven not to have moved under the six-hour run. The eleven-file `freeze02-*` evidence set and `28-RUN-RECORD.md` are committed beside attempt 1's. Phase 29 can start from a document rather than a reconstruction.**

## Performance

- **Duration:** 12 min
- **Tasks:** 2
- **Files created:** 13 (1 off-repo capture, 11 copied evidence files, 1 run record)

## The post-run gate capture

    python experiments/check_rerun_gates.py experiments/results --profile full

`TOTAL: 176 PASS, 7 N/A, 0 FAIL` — 185 lines at `/home/tlancaster/freeze02-gates-full.txt`.

**Every `FAIL` line, transcribed verbatim:**

> *(none — the capture contains zero `[FAIL]` lines)*

The gate script itself exited **0**, which is consistent with zero FAILs but was not read as the verdict; the `TOTAL:` line was.

**Capture, not adjudication.** There was nothing to classify here, but the boundary holds regardless: grading the returned run is **Phase 29's RUN-03**, not this plan's. Nothing was repaired and the gate script — which lives inside the frozen tree — was not edited.

### The two totals agree

| Source | Total |
|---|---|
| The run's own end-of-run roll-up (plan 03, `freeze02-rollup.txt`) | `TOTAL: 176 PASS, 7 N/A, 0 FAIL` |
| This post-run re-run (`freeze02-gates-full.txt`) | `TOTAL: 176 PASS, 7 N/A, 0 FAIL` |

**They agree exactly.** A disagreement would itself have been a finding; there is none.

Beside the reference `176 PASS, 7 N/A, 0 FAIL` — measured by phase 29.1 over the **freeze-01 output tree** with the freeze-02 gate script, not over a freeze-02 run. It is a reference, not a target, and nothing was tuned toward it: no gate, manifest, expectation or driver file was edited between the tag and this run.

Both of the plan's named legitimate reasons for divergence were available and neither produced one: 29.1-09's machine-evaluated predicate for `degenerate_observations.csv` and `all_observation_depths.csv` scored both PASS on the real files at `results_e2_invocations/e2_classification` (198 rows and ≈11 MB respectively), and this tree is new.

## The environment did not move under the run

    diff /home/tlancaster/freeze02-pip-freeze.txt <(pip freeze)   ->  (empty)

Byte-identical. That is what makes the pre-launch capture a valid record of what actually executed across the six hours.

Re-asserted at the same time:

| Check | Value |
|---|---|
| `aquacal.__file__` | `/home/tlancaster/aquacal-frozen-rerun-freeze-02-prod/src/aquacal/__init__.py` — under the clone |
| `cv2.__version__` | `4.13.0` |
| `numpy` / `scipy` | 2.4.6 / 1.17.1 |
| Python | 3.11.15 |

## The gate run wrote nothing into the tree

    diff <(git -C $CLONE status --porcelain) /home/tlancaster/freeze02-tree-state-at-handoff.txt  ->  identical

Nine untracked output paths, unchanged from the handoff state captured in plan 04. The gate reads; it does not write.

## A finding worth its own section: the two environments are not identical

`diff freeze01-pip-freeze.txt freeze02-pip-freeze.txt` reports **six** changed entries — not the zero a casual reading would assume from "same box, same pins".

One is the editable `aquacal` sha, as expected. The other five are dev tooling that drifted because attempt 2's environment was built by a **fresh resolve** of `pip install -e ".[dev,bench]"` five days later:

| Package | Attempt 1 | Attempt 2 |
|---|---|---|
| `filelock` | 3.32.3 | 3.32.4 |
| `packaging` | 26.2 | 26.3 |
| `platformdirs` | 4.11.3 | 4.11.4 |
| `python-discovery` | 1.5.2 | 1.5.3 |
| `ruff` | 0.16.3 | 0.16.4 |

**None is in the numerical stack.** `numpy` (2.4.6), `scipy` (1.17.1) and `opencv-python` (4.13.0.92) are identical to the patch level across both attempts — the property that licenses comparing the two runs' numbers at all.

Recorded prominently in `28-RUN-RECORD.md` because the reproducibility argument rests on the numerical pins, and a reader who assumed the *whole* environment was identical would be drawing a stronger conclusion than the evidence supports.

## The evidence set, committed beside attempt 1's

Eleven files copied into `.planning/phases/28-full-suite-production-run/` with the `freeze02-` prefix:

| File | Bytes | Producer |
|---|---:|---|
| `freeze02-install-command.txt` | 40 | 28-01 |
| `freeze02-env.txt` | 289 | 28-01 |
| `freeze02-pip-freeze.txt` | 1,223 | 28-01 |
| `freeze02-pytest-prelaunch.txt` | 27,018 | 28-01 (D4) |
| `freeze02-prelaunch-assertions.txt` | 11,216 | 28-02 |
| `freeze02-rollup.txt` | 41,168 | 28-03 |
| `freeze02-stage-timing.txt` | 3,773 | 28-03 |
| `freeze02-tree-state-at-handoff.txt` | 375 | 28-04 |
| `freeze02-archive-manifest.txt` | 3,635 | 28-04 |
| `rerun-freeze-02-output.sha256` | 229 | 28-04 |
| `freeze02-gates-full.txt` | 36,763 | 28-05 |

**No `freeze01-*` file was modified, moved or renamed** — `git status --porcelain` reports no change to any of them. The two sets sit side by side so the attempts compare line for line. (Note `freeze02-tree-state-at-handoff.txt` and `freeze01-tree-state-at-handoff.txt` are both 375 bytes and both nine lines — byte-parallel, but describing trees that were *not* in the same state; see 28-04-SUMMARY.)

## 28-RUN-RECORD.md

Written to `.planning/phases/28-full-suite-production-run/28-RUN-RECORD.md`, carrying, in order: the header; the verbatim invocation with the deliberately-unset list; the three hard signals; the roll-up and gate totals beside the reference; the 20-stage timing table with the three Windows-derived upper bounds called out as unusable timeouts; all three ROADMAP success criteria mapped to specific returned artifacts, with criterion 3's two-part derivation and its residual gap copied in full; the environment record including the five-package drift; the D4 test-suite caveat with all three node ids; the D1 note; the returned-artifact index with both sha256 sums and the 507-vs-461 reconciliation; the differences-from-attempt-1 table; the Phase 28 / Phase 29 boundary; and five open items handed forward.

## Open item flagged upward

**Phase 29's success criterion 6 is unsatisfiable as written.** It requires the Zenodo results package to be published *"before the 2026-08-21 submission"* (RUN-05). That date has passed — this run finished 2026-08-25. The criterion needs re-dating or re-scoping by the author before Phase 29 can close against it. Flagged rather than silently failed.

## The boundary this plan does not cross (A1)

No `results/rerun-freeze-02` branch was created or pushed — the production clone has **no** branch matching `results/*` and is still on a detached HEAD. No output tree was committed. The run was not graded, the E2 sanity control and the E7 before/after comparison were not run, and Zenodo was not touched. RUN-03, RUN-04 and RUN-05 all map to Phase 29.

## Task Commits

1. **Task 1: capture the post-run gate output and prove the environment never moved** — verify returns `OK`
2. **Task 2: assemble the evidence set and write 28-RUN-RECORD.md** — verify returns `OK`
