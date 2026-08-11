---
quick_id: 260811-f81
slug: pre-2-0-0-release-fixes
status: complete
date: 2026-08-11
---

# Pre-2.0.0 release fixes — SUMMARY

Applies the user-selected findings from `21-PRE-RELEASE-AUDIT.md`. Everything lands before the
first push, so it all ships inside v2.0.0.

## Final history — 6 commits

| SHA | Subject |
|---|---|
| `d19b3af` | `build: require Python >=3.11 and correct release metadata for 2.0.0` |
| `0d82b82` | `refactor: remove deprecated public API ahead of the 2.0.0 cut` |
| `cee18f6` | `fix(config): default interface.normal_fixed to false and drop initial_distances` |
| `1b1b4c2` | `fix(cli): make --output-dir actually apply to the calibration run` |
| `0efbf2b` | `refactor(datasets): drop the dead min_cameras_per_frame parameter` |
| `f45d278` | `docs: correct guide, tutorial and experiment claims against the code` |

7 `BREAKING CHANGE:` footers across 4 commits. The major was already guaranteed by `d406001
feat!:` independently of any of these.

## What was applied

MUST-1, MUST-2, MUST-4, MUST-5, MUST-6, MUST-7, MUST-8; SH-1 through SH-15 and SH-17; UNV-1;
OPT-11 cosmetics; plus three follow-ups that no task owned (ruff `target-version`,
`e4_benchmark_grid.py:786`, `glossary.md:59`).

**Excluded as planned:** MUST-3 (`manifest.json`, gated on the Zenodo publish — plan 21-10),
`experiments/results/*` removals (21-11), OPT-1..4.

**SH-16 verdict — verified, not edited.** `docs/tutorials/index.md:26-27` reads accurately after
this morning's §3 update and archive rebuild. One contingency the sentence does not carry: the
reproduction is true of the *rebuilt* archive, which is not yet published, so it becomes
unconditionally true only at 21-10. **Re-check after the publish.**

## Two process failures worth keeping

### 1. Four executors shared one working tree

They were dispatched without worktree isolation, so `pre-commit`'s stash/restore cycle had four
agents' unstaged edits to trip over. Consequences observed:

- Commit `7d27821` carried **three tasks' work** under a `docs(guide):` subject, including a
  breaking API removal and the CLI fix. Since semantic-release builds the CHANGELOG from commit
  messages, v2.0.0's changelog would have misattributed both.
- Two executors had edits silently reverted mid-run; both caught it only because a verification
  step printed the old value back. One recovered its work from pre-commit's stash patch file.

**Resolved** by a soft reset to `57eca21` and re-commit into the six correctly-typed commits
above. The rewritten tree hash was verified **byte-identical** to the pre-reset tree
(`8866d6f5c26675e6a20c87b11ae415c84d460969`), so nothing was lost or altered in the rewrite.

**Lesson:** concurrent executors need worktree isolation, or they must be run sequentially. File
disjointness in the plan does not protect against `pre-commit`'s tree-wide stash.

### 2. An orchestrator override reversed a documented decision

The orchestrator overrode the plan's escalation and told task 4 to export
`generate_real_rig_trajectory`, reasoning it was library code that three experiments import.
Phase 19.1 had excluded it **deliberately**, with the reason recorded at `19.1-01-SUMMARY.md:125`:
`create_scenario("realistic")` calls it internally, so no consumer needs a direct import, and the
notebook's import is vestigial.

That was exactly right — the notebook mentioned the name once, in an import list, with **zero call
sites**. The correct fix was deleting one dead import, not widening the 2.0.0 public surface on
the same afternoon `validation.__all__` was narrowed.

`tests/unit/test_datasets.py::test_all_exports` caught the widening within minutes and is restored
intact. **Lesson:** before overriding a plan's escalation, search for a recorded rationale — an
assertion whose docstring says "deliberately absent" is a decision, not an oversight.

## Verification

Every fix was verified by the orchestrator against **file contents**, not commit messages or agent
reports — the only method that catches a silently reverted edit.

- `sphinx-build -W --keep-going` → exit 0, build succeeded, zero warnings
- `ruff check src/ experiments/` → all checks passed
- Targeted suites green per task; `test_datasets.py` + `test_conditioning.py` → 65 passed
- Both notebooks parse as JSON; zero `execution_count` churn
- Full unfiltered `pytest tests/` run by the orchestrator at the post-merge gate

## Known-remaining, not in scope

- **No HTTP Range/resume in `download_with_progress`.** Invisible at 164 MB; at 4.35 GB a failure
  at 90% restarts from zero, and users need ~9 GB free (zip is kept alongside the extraction).
  Non-breaking to add, so a legitimate 2.0.1 — but it is the first thing a tutorial reader hits.
