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
| 1 | `rerun-freeze-01` | `3ab9c13` | 2026-08-19T22:24Z | **SUPERSEDED by attempt 2** — closed successfully; verified on target; its run surfaced the defects attempt 2 fixes | — (closed clean; see the note below) |
| 2 | `rerun-freeze-02` | `7005a27` | 2026-08-24T18:07Z | **OPEN — cut, verified from a fresh clone, approved and pushed 2026-08-24.** Licenses the v2.1 re-run; closes when that run is verified on target | — (carries a ruled-on 3-test exception; see below) |

**Closed 2026-08-20.** Plans 27-12 and 27-13 verified the tag on the Linux run machine: clean
clone at the frozen sha, fresh environment at cv2 4.13.0, dry run 20/20, `fd_jacobian` at full
scale, and an on-target `--smoke` roll-up of **72 PASS / 18 N/A / 0 FAIL** with all 20 stages at
exit 0 — matching the Windows pass exactly. Pre-flight's frameset identity check PASSED on the
real image set.

One deviation, recorded not fixed: the frozen `HANDOFF.md` §1.2 install command omits the `dev`
and `bench` extras, so a runtime-only environment kills e3 (no pytest) and nulls two required
manifest fields (no psutil). Environment corrected on the target with
`pip install -e ".[dev,bench]"`. No code defect, so **no refreeze**. See
`27-ONTARGET-VERIFICATION.md` §6 and the post-submission todo.

The production run (Phase 28) launched from the verified clone at **2026-08-20T00:14:10Z**.

### Attempt 2 — `rerun-freeze-02`, cut 2026-08-24

**Full record: `.planning/phases/29.1-post-run-fixes-re-freeze/29.1-FREEZE-RECORD.md`.**
Exposure audit and rulings: `29.1-PREPUSH-AUDIT.md`. Verification bar:
`29.1-VERIFICATION-BAR.md`.

**Attempt 1 is superseded, not invalidated, and its tag is not moved.** It closed cleanly and
its production run (Phase 28) produced real, committed output that is still the project's
evidence. Attempt 2 exists because that run surfaced defects worth fixing before the next one —
which is exactly the outcome the "tags are never moved" rule above anticipates. `rerun-freeze-01`
still resolves to tag object `b31c8020…` and commit `3ab9c137…`, re-asserted before and after
attempt 2's tag was cut.

What attempt 2 changes, and what it does not: **`src/` is byte-identical between the two tags.**
Phase 29.1 changed what the suite records and reports, never what it measures. Its gate roll-up
over the 2026-08-20 tree moves **175 PASS / 7 N/A / 2 FAIL → 176 PASS / 7 N/A / 0 FAIL**, and it
discharges §6's deviation above — the frozen `HANDOFF.md` §1.2 install command now reads
`pip install -e ".[dev,bench]"`, proven by building attempt 2's verification environment from
that corrected command and watching e3 exit 0 and all 17 manifest fields come back non-null.

**Attempt 2 was verified the same way attempt 1 was**, on the same Linux run machine: fresh
clone at the tag, a new environment (never the old editable one), the import path asserted to be
inside the clone, a dry run at 20/20, and an on-target `--smoke` roll-up of
**72 PASS / 18 N/A / 0 FAIL** with all 20 stages at exit 0, no `STAGE FAILED` line,
`gate3_run_manifest_clean_tree` PASS, and pre-flight's frameset identity check PASSED against the
real image set. The verdict sets match attempt 1 exactly.

**One difference the reader must not miss: attempt 2's tag was cut with a known, ruled-on
3-test failure.** `pytest tests/` at `rerun-freeze-02` reports **2407 passed, 26 skipped,
3 failed** on Linux — three exact-equality anchor comparisons missing by 1 ULP to rel. 1.4e-9.
They are byte-identical to `rerun-freeze-01` and **fail at attempt 1's tag too**: attempt 1's
`0 failed` is a Windows measurement, and its on-target verification never ran `pytest`. Nothing
was deselected, xfailed, skipped, regenerated or loosened. The ruling — recorded, reasoned, and
in the same shape as this phase's own `GATE FAIL` ruling — is `29.1-PREPUSH-AUDIT.md` §1.

**Pushed 2026-08-24**, after the author approved the exposure audit. `git push` named the branch
and the one tag by full ref — never the all-tags form — and created exactly two refs, as its dry
run predicted. Verified against the remote afterwards: `rerun-freeze-02` is public with its
annotated object intact (`533f79fb…` → `7005a277…`), `rerun-freeze-01` still resolves to
`b31c8020…` → `3ab9c137…`, and the `v[0-9]*` tag count is still **20**. **No workflow fired** —
confirmed against the public Actions API, which shows no run at the new tag, the new branch or
sha `7005a27`, and which also shows `Publish to PyPI` runs at `ref=v2.0.1` and `ref=v2.0.0`, so
the trigger this naming convention exists to dodge is demonstrably live rather than theoretical.

**`results/rerun-freeze-01` was deliberately left at `89c2092`** on the remote, by the author's
ruling, rather than fast-forwarded — the same preservation principle that never moves a tag. A
later reader who finds that pointer 48 commits behind should read it as attempt 1's preserved
endpoint, not a forgotten push; every commit between the two is reachable from
`refs/tags/rerun-freeze-02`.

**Tags are never moved.** If on-target verification finds a defect, that finding sends the freeze
**back**: fix it in the branch, commit, cut `rerun-freeze-02` at the new sha, and re-verify against
that. Abandoned tags stay as the audit trail — a force-moved tag destroys the record of the failed
attempt, which is precisely the provenance fracture this milestone exists to stop repeating. A
second tag is a normal outcome, not a failure signal.

Do **not** patch the running clone in place and continue. A stage that ran at a different commit
than the rest makes the whole run unreportable.
