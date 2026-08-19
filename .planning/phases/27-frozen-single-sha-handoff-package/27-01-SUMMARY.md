---
phase: 27-frozen-single-sha-handoff-package
plan: 01
subsystem: experiments-driver
tags: [measurement, preflight, target-machine, freeze-prep]
requires: []
provides:
  - "27-TARGET-FACTS.md: measured CPU/RAM/disk, E2 image-set location and byte sums, interpreter inventory, worker headroom"
  - "A measured verdict against min_total_bytes: 4000000000 (FAIL, 5.02% short)"
  - "The on-target E2 image-set root and the near-verbatim D-11 source config (config_paper_cv413.yaml)"
affects:
  - "27-02 / 27-08: min_total_bytes must be re-derived; the check's shape stays fixed (D-10)"
  - "27-08: D-12's GATE_PYTHON chain is broken on this target in two places"
  - "27-08: D-11's config must resolve paths against something other than the driver's cwd"
  - "27-12: SUITE_WORKERS 4-5 confirmed; D-26/D-27 re-confirmed independently"
tech-stack:
  added: []
  patterns: ["read-only remote measurement over foreground SSH round trips (D-07)"]
key-files:
  created:
    - .planning/phases/27-frozen-single-sha-handoff-package/27-TARGET-FACTS.md
  modified: []
decisions:
  - "The extrinsic byte total (3,799,096,889 B) does not clear the 4e9 floor; the floor was derived from the packaged archive size (4.35 GB), not the expanded tree, so it is a manifest number to re-derive rather than a check to weaken"
  - "The frozen clone will live at $HOME/aquacal-frozen-<tag>, deliberately not the D-27 checkout"
  - "The E2 image-set root was located by authorised probing, not supplied; it is flagged for author confirmation at review"
metrics:
  duration: ~25 min
  completed: 2026-08-19
---

# Phase 27 Plan 01: Measure the Linux Run Machine Summary

Measured the Linux run machine over eight read-only foreground SSH round trips and recorded the
results in `27-TARGET-FACTS.md`; **three of the four assumptions this plan existed to test came
back false**, all of them inside plan 27-08's scope and all of them now fixable inside the frozen
sha rather than after it.

## What Was Done

**Task 1 (checkpoint, pre-answered by the author):** the four values were supplied in the executor
prompt. Reachability was still verified with the single cheap round trip the plan specifies —
`ssh lab-pc 'echo ok; uname -s'` printed `ok` / `Linux` in under a second. Nothing was written to
disk from this task.

**Task 2 (measurement):** seven measurement groups, each its own foreground `ssh` invocation, none
backgrounded (D-07). No file modified, so no commit — this task is measurement only per its
`<files>` declaration.

**Task 3:** wrote `27-TARGET-FACTS.md` with all six required sections plus the `Pre-push flag`
callout. Commit `7f04941`.

## The Three Findings

**1. The byte floor fails — and for an instructive reason.** The sum over the 13 extrinsic
directories is **3,799,096,889 B**, against `min_total_bytes: 4000000000`. That is **5.02% short**.
The frameset is nonetheless correct by every other observable: 13 directories, exactly 262 PNG
files in each, all thirteen cameras. The floor's rationale cites *"4.35 GB as published"* — the
**Zenodo packaged** size — while the check sums the **expanded** tree, which is 3.80 GB decimal.
The floor was set against a number that does not describe the thing being summed. D-10 anticipated
exactly this (*"if 4.35 GB of frames does not clear 4 GB, that is a manifest number to re-derive
from measurement, not a check to weaken"*), and the note states the verdict in D-10's own words.
The discriminating power lost by re-deriving is nil: the retired ~4.3x-subsampled archive is on the
order of 0.9 GB expanded, so any floor between roughly 1.5e9 and 3.7e9 still does the check's only
job.

**2. D-12's `GATE_PYTHON` chain is broken on this target at two of its three rungs.** The conda env
is named lowercase **`aquacal`**, not `AquaCal`, and Linux filesystems are case-sensitive — the
middle rung as specified resolves to nothing. Worse, the final fallback rung is worse than
mis-versioned: **there is no `python` on the target's PATH at all** (`command -v python` returns
nothing; only `/usr/bin/python3` at 3.10.12 exists). `GATE_PYTHON=python` would fail with *command
not found*, which reads like a broken driver rather than an unresolved interpreter. D-28 warned the
fallback lands below the `>=3.11` floor; the measurement shows it does not land at all.

**3. The on-target config declares RELATIVE paths.** `config_paper_cv413.yaml` at the image-set
root uses `extrinsic/e3v829d/`. The pre-flight probe does `pathlib.Path(p)` then `p.exists()`,
resolved against the **driver's cwd** — the frozen clone under D-01/D-05, not the data root. A
verbatim copy into the repo would make the probe test `<clone>/extrinsic/e3v829d/` and refuse with
ABSENT. 27-08 must resolve this before D-11's config is committed.

A fourth, smaller find worth 27-08's attention: that same config already carries `frame_step: 1`,
`max_calibration_frames: 200`, both board specs and the 12+1 camera split — it is the D-11 config
almost verbatim. Its header also **dissolves the discrepancy D-11 flagged**: the frames are already
subsampled at every 30th video frame, so `frame_step: 1` over these images equals `frame_step: 30`
over the source video. The Desktop config and this one are not in conflict; they address different
input kinds.

## What Confirmed Cleanly

- **Every D-25 amendment value re-measured identically.** Ubuntu 22.04.4, kernel 6.8.0-136, 32
  logical cores, 31.06 GiB RAM. The amendment's "662 GB free" and the measured
  710,725,156,864 B are the same number in different units — **no disagreement**. New here: the CPU
  model (i9-13900KF) and 32 GiB of swap.
- **`SUITE_WORKERS` 4–5 holds and was not re-tuned** (D-15). Worst realistic mix — one 200-frame
  stage plus the rest at the 100-frame ceiling — is 21.8 GiB at 4 workers and 25.3 GiB at 5,
  against 31.06 GiB.
- **Free disk clears `free_space_floor_gib: 20` by 33x.**
- **D-26 and D-27 re-confirmed independently:** `envs/aquacal` holds `cv2 4.14.0` (the version the
  pin exists to exclude), and its `.pth` points at a different checkout. The chosen frozen-clone
  path `$HOME/aquacal-frozen-<tag>` was checked and does not exist, so the clone lands on virgin
  ground.

## Deviations from Plan

**1. [Rule 3 - Blocking] The E2 image-set root was located by probing, not supplied.**
- **Found during:** Task 1 (pre-answered checkpoint)
- **Issue:** value 3 of the four was not supplied verbatim; the author authorised a bounded probe.
- **Fix:** four `ssh ls`/`find` round trips located
  `$HOME/PycharmProjects/AquaCal/aquacal_data/real-rig/real-rig/`, whose children are exactly the
  per-camera `extrinsic/` and `intrinsic/` trees D-08 describes.
- **Residual risk:** the root is inferred. The note carries an explicit *Confirm at review* callout
  saying that if the intended image set lives elsewhere, every byte figure is measuring the wrong
  tree.

**2. [Rule 2 - Correctness] Paths written as `$HOME/…` rather than verbatim.**
- **Issue:** Task 3's redaction rule says to write a personal-identifier path *as recorded* but flag
  it; the plan's acceptance criteria say *no username anywhere in the committed note*. These
  conflict, because the literal root is under a home directory named for the operator.
- **Fix:** the stricter reading wins. All paths are written `$HOME/…`, and the `Pre-push flag`
  callout explains the elision and hands 27-11's audit two specific things to check.

**3. Base-commit correction.** The worktree forked from `d27bda7`, not the specified
`4f6e1f5`. The startup assertion caught it and `git reset --hard` corrected it. This is the known
stale-base issue; it fired again here.

No Rule 4 situations arose. `conda env list` was unavailable remotely (D-28 predicted this
exactly), so envs were enumerated by listing `~/anaconda3/envs` directly — a substitution the plan's
own action text already permits.

## What This Plan Did NOT Do

No environment was built, no repository cloned, no AquaCal code imported or run on the target.
Every remote call was `uname`, `free`, `df`, `ls`, `find`, `du -sb` or `python -V`. The note says so
in its own words: nothing here proves the code runs on the target — that is 27-12's clean-clone
verification against the tag, and it remains the only venue that can catch a Linux-only failure.

Per `<verification>`, no test was run: this plan touches none of the repo's Python.

## Known Stubs

None.

## Threat Flags

None. The single threat this plan's register dispositioned as `mitigate` for the committed artifact
(T-27-01-01, information disclosure) is mitigated as specified: the note contains no hostname,
username or key material — verified by grep — and the pre-commit `Detect secrets` hook passed.

## Self-Check: PASSED

- `FOUND: .planning/phases/27-frozen-single-sha-handoff-package/27-TARGET-FACTS.md`
- `FOUND: 7f04941`
- `grep -c min_total_bytes` = 4 (>= 1)
- `grep -Ec SUITE_WORKERS` = 2 (>= 1)
- byte-floor verdict line present ("does not clear the floor")
- `grep -Eic '(ssh-rsa|BEGIN [A-Z ]*PRIVATE KEY|password)'` = 0
- hostname occurrences = 0; username occurrences = 0
