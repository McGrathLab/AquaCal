---
phase: 27-frozen-single-sha-handoff-package
plan: 12
subsystem: on-target-verification
tags: [linux, clone, environment, dry-run, openblas, d-05, d-30]
requires:
  - "27-11 (rerun-freeze-01 on origin)"
provides:
  - ".planning/phases/27-frozen-single-sha-handoff-package/27-ONTARGET-VERIFICATION.md (sections 1-3)"
  - "a verified clone + environment on the Linux run machine"
affects:
  - "plan 27-13 (runs its real stage and smoke pass in this clone)"
  - "Phase 28 (executes here)"
tech-stack:
  added: []
  patterns:
    - "fresh env per freeze, never reuse a dev env carrying an editable install"
key-files:
  created:
    - .planning/phases/27-frozen-single-sha-handoff-package/27-ONTARGET-VERIFICATION.md
  modified:
    - .planning/phases/27-frozen-single-sha-handoff-package/27-12-PLAN.md
    - .planning/phases/27-frozen-single-sha-handoff-package/27-CONTEXT.md
decisions:
  - "A NEW conda env (aquacal-freeze01) was built. The pre-existing `aquacal` env carries OpenCV 4.14.0 -- the exact version the pin excludes -- and an editable install pointing at a different checkout (27c80e7). Reusing it would import unfrozen code while stamping the frozen sha."
  - "The '76 MB tracked' baseline figure was WRONG and was corrected before the on-target run: 226 files / ~1.7 MB. Caught by rehearsing the clone locally rather than trusting the number."
metrics:
  duration: ~30 min
  completed: 2026-08-19
---

# Plan 27-12: the frozen package, cloned and verified on Linux

**Result: PASS.** Full detail in `27-ONTARGET-VERIFICATION.md` §1-3.

## Highlights

- Clone of `rerun-freeze-01` is at `3ab9c137…`, `git status` empty, `import aquacal` resolves
  **inside the clone**, cv2 **4.13.0**.
- Fresh env `aquacal-freeze01` at Python 3.11.15. The pre-existing `aquacal` env was rejected on
  measured grounds (OpenCV 4.14.0 + editable install to another checkout).
- OpenBLAS recorded verbatim: `scipy-openblas 0.3.31.188.0`,
  `USE64BITINT DYNAMIC_ARCH NO_AFFINITY Haswell MAX_THREADS=64`.
- Manifest: `git_sha` matches the frozen sha, `git_dirty: false`, 16 capped stages and exactly the
  4 `serial_alone` unpinned stages.
- Dry run: exit 0, all 20 stages, `E2 release config: … e2_release_linux.yaml (in-repo default)` —
  **D-12's repointing works on Linux with no override**.

## Two findings

**D-30 got its first real test.** `interpreters_agree: true` with `gate_interpreter` and
`stage_interpreter` differing textually (`bin/python` vs `bin/python3.11`) and resolving equal
through the symlink. On Windows this field compared equal for the wrong reason — that filesystem
is case-insensitive — so Linux is where it first meant anything.

**The baseline-size criterion was wrong and would have failed a correct clone.** 27-12 asserted
`pre_rerun_baseline/` is "76 MB, tracked"; a clone holds 1.7-1.8 MB. 159 of its 385 files are
gitignored bulk artifacts. Corrected in the plan and in 27-CONTEXT before the operator could hit
it, and the functional claim was verified rather than assumed: e3's `--check` read its committed
baselines from the clone and matched `code_constants.csv` and `newton_iterations.csv`.

## Deviation

Task 3's criterion "the pre-flight frameset verdict is recorded as PASS" **cannot be satisfied by
a dry run** — a dry run stubs pre-flight itself, so the check never executes. It was satisfied in
27-13's smoke pass instead, where pre-flight runs for real. The dry run proves wiring only; its
`SUITE COMPLETE` banner compared nothing (`rollup: DRY RUN`).
