---
phase: 27-frozen-single-sha-handoff-package
plan: 11
subsystem: release-freeze
tags: [freeze, tag, push, provenance, d-01, d-02]
requires:
  - "27-10 (the smoke acceptance pass and the author's exposure approval)"
provides:
  - "sha 3ab9c13723202a58bb50e351b0b6bc0c0ffcd59c, tagged rerun-freeze-01 on origin"
  - ".planning/phases/27-frozen-single-sha-handoff-package/27-FREEZE-RECORD.md"
  - "a cloneable frozen package: git clone --branch rerun-freeze-01"
affects:
  - "plan 27-12 (clones this tag on the Linux target)"
  - "plan 27-13 (verifies it, then closes or refreezes)"
  - "Phase 28 (executes the suite at this sha)"
tech-stack:
  added: []
  patterns:
    - "non-v* tag name so no release workflow can fire"
    - "annotated tag carrying the verification record in its message"
key-files:
  created:
    - .planning/phases/27-frozen-single-sha-handoff-package/27-FREEZE-RECORD.md
decisions:
  - "The tag is rerun-freeze-01, deliberately NOT matching v* -- publish.yml triggers on v* tags and would have published to PyPI."
  - "Annotated (-a), never lightweight: the verification record travels in the tag message."
  - "The push was restarted twice, deliberately, so the frozen sha would CONTAIN the operator documentation rather than tag a sha that lacked it. Nothing reached origin before the final push."
  - "The pre-push hook was never skipped. --no-verify was available and not used; the interpreter was fixed instead."
metrics:
  duration: ~1.5 h (dominated by the pre-push test hook, run three times)
  completed: 2026-08-19
---

# Plan 27-11: cut the freeze

## Result

**Frozen at `3ab9c13723202a58bb50e351b0b6bc0c0ffcd59c`, tagged `rerun-freeze-01`, both on
`origin`.** `git describe --tags --long --match 'v[0-9]*'` = `v2.0.1-277-g3ab9c13`.

    git clone --branch rerun-freeze-01 https://github.com/McGrathLab/AquaCal.git

## Acceptance

| Criterion | Result |
|---|---|
| `HEAD` == `origin/experiments/full-suite-rerun` | both `3ab9c13723...` |
| Tag is annotated, not lightweight | `git cat-file -t` prints `tag` |
| `rerun-freeze-01^{commit}` == pushed HEAD | yes |
| Tag listed by `git ls-remote --tags origin` | yes |
| No tag matching `v*` created | 20 before, 20 after, locally and on origin |
| Version anchor still resolves | `v2.0.1-277-g3ab9c13` |
| No CI workflow fired | latest run on origin is 2026-08-12; nothing from this push |

All five workflow triggers were read before tagging: `publish.yml` fires on `v*` tags only,
`release.yml` and `test.yml` on push to `main`, `docs.yml` on PRs to `main`, `slow-tests.yml` on
`workflow_dispatch`. A non-`v*` tag on a non-`main` branch fires none of them.

## Deviations

**The push was launched three times; only the third reached origin.** The first two were stopped
deliberately, not because they failed:

1. Stopped to fold in the ruff pre-push fix plus the handoff's dry-run documentation.
2. Stopped to fold in three further handoff corrections found while auditing 27-12 and 27-13.

The reasoning: a freeze tag is worth little if the operator documentation the target needs is one
commit *after* it. Each push costs a ~50 min pre-push test hook, so restarting was the expensive
choice, and the right one. `git ls-remote` confirmed nothing had reached origin before each stop.

**The pre-push hook blocked the first attempt** with 62 collection errors — `.hooks/pre-push-tests.sh`
runs bare `python -m pytest`, which in Git Bash resolves to Anaconda base with no numpy. Fixed by
putting the environment on `PATH` for the push, **not** by `--no-verify`. The hook then ran the
real `-m "not slow"` suite and passed.

**The hook's runtime was ~50 min, not the documented ~26.** Verified as genuinely computing rather
than hung: 2863 s of CPU over 2880 s wall, ~99% of one core. Per the standing rule, no attribution
of that swing to any diff.
