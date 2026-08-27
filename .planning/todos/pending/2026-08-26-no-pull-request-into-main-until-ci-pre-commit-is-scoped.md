---
created: 2026-08-26T00:00:00.000Z
title: Do not open a PR from `results/rerun-freeze-02` into `main` until CI's `pre-commit run --all-files` job is scoped — it would put the formatting hooks through 147 committed run artifacts
area: infra
resolves_phase: 29.2
files:
  - .github/workflows/test.yml
  - .pre-commit-config.yaml
---

## Owner

**Phase 29.2 success criterion 1.** This todo exists so the constraint is findable from
`.planning/todos/pending/` as well as from the roadmap and the phase record. Phase 29 deliberately
stopped short of it; Phase 29 also could not fix it, because **D-29-17 fenced
`.pre-commit-config.yaml` for the duration of Phase 29**. That fence was Phase-29-scoped and is
lifted in 29.2.

## The constraint

`.github/workflows/test.yml` runs **`pre-commit run --all-files`** on **both**
`push: [main]` **and** `pull_request: [main]`.

Commit `70e783f  results(29): full production suite at rerun-freeze-02` put **227** run artifacts
into the repository, **147** of them under `experiments/results/`. Of those:

- **143 files deliberately lack a final newline.** `end-of-file-fixer` would rewrite every one.
- **439 trailing-whitespace advisories** are present in the artifacts' own bytes. `git` warned at
  commit time; nothing was acted on, by design.

Both facts are positive evidence that the byte-integrity hazard stayed latent through Phase 29 —
`git show HEAD | grep -c '^\ No newline at end of file'` returns exactly **143**, the count
research predicted. They are also exactly what CI would undo.

## What actually happens if a PR is opened today

**A blocked merge, not data corruption.** The job modifies the *runner's* checkout and exits
non-zero; it cannot write back to the branch. Nothing in the repository is harmed. But the PR
cannot go green, and the natural "fix" — running the hooks locally and committing the result —
**would** destroy the byte-for-byte property that plan 29-05 proved and that
`gate3_git_sha_consistency` and both md5 anchors rest on:

| Anchor | Value that must not move |
|---|---|
| `experiments/results/real_rig_metrics.json` | `57279708f6106f411d1fe03ed2698291` |
| `experiments/results/interface_ablation_band.csv` | `b6515ed77ed04268608b74217716020b` |

## Resolution (Phase 29.2)

Scope the CI job to **changed files**, or exclude `experiments/results/` from the two formatting
hooks. Then merge — **with a MERGE COMMIT, never a squash** (Phase 29.2 criterion 2: a squash
collapses 406 commits into one message, and semantic-release parses only that message; if it reads
as `docs:`, no release fires at all and the failure is silent).

## Status as of 2026-08-26

- **No PR was opened by Phase 29.** Attempt 1's branch (`results/rerun-freeze-01`) was never merged
  either.
- `origin/main` is **0 commits ahead** of `results/rerun-freeze-02`, which is **406 ahead**.
- **`pre-commit run --all-files` was never invoked anywhere in Phase 29.** Every hook run was scoped
  with `--files`.

## Evidence

- `.planning/phases/29-gate-verification-results-commit/29-PHASE-RECORD.md` § *Open items handed
  forward*, items 3 and 9
- `.planning/phases/29-gate-verification-results-commit/29-05-SUMMARY.md` — the byte-integrity
  evidence table
- `.planning/ROADMAP.md` § *Phase 29.2: Merge, Release, and Publish*, criteria 1 and 2
