---
phase: 27-frozen-single-sha-handoff-package
plan: 10
subsystem: experiment-suite-acceptance
tags: [acceptance, smoke, gates, pre-push-audit, exposure, d-01, d-05, d-20]
requires:
  - "27-02, 27-03, 27-04, 27-05, 27-08 (the fixes this pass proves)"
  - "experiments/run_experiment_suite.sh --smoke"
  - "experiments/check_rerun_gates.py --profile smoke"
provides:
  - ".planning/phases/27-frozen-single-sha-handoff-package/27-PREPUSH-AUDIT.md"
  - "the roll-up acceptance reading, propagated to HANDOFF.md 2.8 / 27-13 / ROADMAP"
  - "the author's push-and-tag authorisation"
affects:
  - "plan 27-11 (authorised to push and tag)"
  - "plan 27-13 (acceptance criteria rewritten to the roll-up)"
  - "Phase 28 (the operator reads HANDOFF.md 2.8 before judging an exit code)"
tech-stack:
  added: []
  patterns:
    - "archive-aside rather than --allow-nonempty-out, so the before/after comparison stays honest"
    - "bounded waiter with an explicit verdict, so silence never reads as success"
key-files:
  created:
    - .planning/phases/27-frozen-single-sha-handoff-package/27-PREPUSH-AUDIT.md
  modified:
    - experiments/HANDOFF.md
    - .planning/phases/27-frozen-single-sha-handoff-package/27-13-PLAN.md
    - .planning/ROADMAP.md
decisions:
  - "ACCEPTANCE IS READ AT THE ROLL-UP, NOT THE DRIVER'S EXIT CODE (author, 2026-08-19). A healthy run exits non-zero; the criterion as written was unsatisfiable and its intent was met."
  - "Per-stage gates 1-4 judge the whole tree and are applied to auxiliary trees they do not own. Scoping them was DECLINED inside the freeze window -- risk spent on a number, not on evidence."
  - "Three signals stay hard and were promoted to explicit 27-13 criteria: STAGE FAILED, any non-zero stage exit, and gate3_run_manifest_clean_tree."
  - "Stale smoke trees were ARCHIVED ASIDE, never cleared with --allow-nonempty-out, which would have let the completeness gate count another run's artifacts as this run's."
  - "The exposure was approved as-is: two home-directory usernames become public; scrubbing .planning was offered and declined."
metrics:
  duration: ~2 h (three smoke passes; two found real defects)
  completed: 2026-08-19
---

# Plan 27-10: the smoke acceptance pass and the pre-push audit

## Result

**Both gates clear.** Roll-up **72 PASS / 18 N/A / 0 FAIL** at sha `9ac6a6d`, all 20 stages at
exit 0, 10 min 56 s. Against 26-10's baseline of 71/9/12 with `reconstruction_bootstrap` exiting
1: **all 12 FAILs cleared, none new**. Full record and both rulings in `27-PREPUSH-AUDIT.md`.

## Three passes, and what the first two found

The pass was run three times, and the first two each caught something real rather than being
wasted work:

1. **Pre-flight refused.** `experiments/results_smoke` still held the 2026-08-18 `88512b7`
   artifacts with no state file for the new sha. Correct refusal: a fresh run into a populated
   tree lets the completeness gate report someone else's artifacts as this run's. Resolved by
   archiving aside, deliberately **not** by `--allow-nonempty-out`.
2. **One roll-up FAIL: `gate3_run_manifest_clean_tree`.** An uncommitted `STATE.md` left the tree
   dirty, so the recorded `git_sha` did not fully describe the code that ran. The orchestrator's
   own dirt, and the same constraint binds the frozen run.
3. **Green.**

## The ruling that matters downstream

The driver exits **non-zero on a passing run**. 17 `GATE FAIL` findings survive, all from
*per-stage* gates that judge the whole tree while it is still filling (totals climb 19 PASS to
72 PASS over the same artifacts) or that apply the full battery to the auxiliary
`e2_band` / `e2_timing` / `e2_memory` / `e4_repeat` trees. Pre-existing — `88512b7` produced the
same shape.

So the plan's "final exit code is 0" was unsatisfiable while its intent was met. The author ruled
acceptance is read at the roll-up. Propagated to `HANDOFF.md` section 2.8 (new), `27-13-PLAN.md`
acceptance criteria, and `ROADMAP.md` 409/421 — 27-13 is where this would otherwise have stalled
the on-target run.

## Exposure scan

273 commits (not the recorded 218 — waves 1-2 landed after that count), 498 files, 69,169
insertions, no upstream configured. **Credentials clean**: every hit is a GitHub Actions secrets
reference or an OIDC permission, no literal keys. Residue is two home-directory usernames —
`C:\Users\tucke\` in 131 tracked files and `/home/tlancaster/` in the 26 release-config paths,
the latter deliberate because the paths must resolve on the target.

## Deviations

- **Task 1's acceptance criterion was superseded**, not met as written. See the ruling above.
- A portability finding surfaced from D-30's new manifest keys: `gate_interpreter` and
  `stage_interpreter` differ in case here yet `interpreters_agree: True`, because Windows is
  case-insensitive and there is one env on disk. **Linux is not**, so that field is the one to
  check on the target before trusting the recorded versions. Recorded in the audit.
