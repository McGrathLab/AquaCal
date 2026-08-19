# 27-FREEZE-RECORD — the frozen sha for the v2.1 full-suite re-run

## The freeze

| | |
|---|---|
| **Frozen sha** | `3ab9c13723202a58bb50e351b0b6bc0c0ffcd59c` |
| **Short sha** | `3ab9c13` |
| **Tag** | `rerun-freeze-01` (annotated) |
| **`git describe --tags --long --match 'v[0-9]*'`** | `v2.0.1-277-g3ab9c13` |
| **Branch** | `experiments/full-suite-rerun` |
| **Cut (UTC)** | 2026-08-19T22:24Z |
| **Remote** | `github.com/McGrathLab/AquaCal` |

Clone the frozen package with:

    git clone --branch rerun-freeze-01 https://github.com/McGrathLab/AquaCal.git aquacal-frozen-rerun-freeze-01

**Every artifact of the re-run must record this sha.** The run machine's tree must not move —
no pull, no checkout, no commit there (D-27). A per-stage `git rev-parse` would otherwise split
one run's artifacts across two shas.

## Why this tag name

`rerun-freeze-01` deliberately **does not match `v*`**. `.github/workflows/publish.yml` triggers
on `push: tags: ['v*']` and publishes to PyPI; `release.yml` and `test.yml` trigger on push to
`main`, and `docs.yml` on PRs to `main`. Pushing this branch plus this tag therefore fires **no
workflow at all** and publishes nothing. Verified against all five workflow files before cutting.

`git describe` is restricted to `--match 'v[0-9]*'` wherever it anchors a version, so this
non-version tag cannot silently replace the semantic-version anchor. Confirmed after tagging:
`git describe --tags --long --dirty --match 'v[0-9]*'` still resolves to `v2.0.1-277-g3ab9c13`,
and the `v*` tag count is unchanged at 20.

## What was verified before cutting

| Check | Result |
|---|---|
| Full test suite | **2315 passed, 25 skipped, 0 failed** (1:09:13) |
| Local `--smoke` acceptance roll-up | **72 PASS / 18 N/A / 0 FAIL** |
| Stages at exit 0 | **20 / 20** (10 min 56 s) |
| `STAGE FAILED` lines | **0** |
| `gate3_run_manifest_clean_tree` | **PASS** — tree clean at launch |
| Dry-run harness | exit 0, 20/20 stages |
| Pre-push exposure audit | credentials clean; two home-directory usernames disclosed and approved |
| Working tree at tag time | clean (`git describe` reports no `-dirty`) |

Against the 26-10 baseline (71 PASS / 9 N/A / 12 FAIL, `reconstruction_bootstrap` exiting 1):
**all 12 FAILs cleared, none new.** Full detail in `27-PREPUSH-AUDIT.md`.

## The one thing most likely to be misread

**The driver exits NON-ZERO on a healthy run.** Acceptance is read at the **end-of-run
completeness roll-up**, never at `$?` — author's ruling, 2026-08-19. 17 per-stage `GATE FAIL`
findings survive a passing run because gates 1-4 judge the whole tree while it is still filling,
and are applied to the auxiliary `e2_band` / `e2_timing` / `e2_memory` / `e4_repeat` trees they do
not own. See `experiments/HANDOFF.md` §2.8 and `27-PREPUSH-AUDIT.md`.

## Attempt log

| # | Tag | Sha | Cut (UTC) | Outcome | Defect that ended it |
|---|---|---|---|---|---|
| 1 | `rerun-freeze-01` | `3ab9c13` | 2026-08-19T22:24Z | **verification pending** | — |

Plan 27-12 (clone, environment, dry run on the Linux target) and plan 27-13 (one real stage, the
gate roll-up, the on-target smoke pass) fill in this row's outcome.

**Tags are never moved.** If on-target verification finds a defect, that finding sends the freeze
**back**: fix it in the branch, commit, cut `rerun-freeze-02` at the new sha, and re-verify against
that. Abandoned tags stay as the audit trail — a force-moved tag destroys the record of the failed
attempt, which is precisely the provenance fracture this milestone exists to stop repeating. A
second tag is a normal outcome, not a failure signal.

Do **not** patch the running clone in place and continue. A stage that ran at a different commit
than the rest makes the whole run unreportable.
