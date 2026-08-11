---
quick_id: 260811-e7s
slug: pre-2-0-0-release-audit
status: complete
date: 2026-08-11
---

# Pre-2.0.0 release audit — SUMMARY

**Deliverable:** `.planning/phases/21-new-feature-documentation-dataset-refresh/21-PRE-RELEASE-AUDIT.md`

Read-only audit. Zero tracked files modified — verified by
`git status --porcelain | grep -vc '^?? '` returning `0` before the commit, and enforced as a
gate at the end of every task rather than checked only at the end.

## Shape

Five tasks, one wave. Tasks 1-4 ran in parallel, each writing an independent findings fragment to
the session scratchpad (outside the repo); task 5 merged, re-ranked globally, wrote the document
and made the single commit. Fragments stayed outside the repo so the read-only property held
structurally, not by discipline.

## Outcome

8 MUST-FIX-BEFORE-2.0.0, 17 SHOULD-FIX, 13 OPTIONAL, 3 UNVERIFIED, plus recorded clean results.

Ranked by **lock-in, not ugliness** — whether the release freezes the mistake — so several
one-line fixes rank above larger cosmetic ones.

Highest-value findings, none of which were on the pre-audit suspicion list:

- **MUST-1** `scipy>=1.16` is unsatisfiable on Python 3.10 while `requires-python = ">=3.10"`.
  Publishing bakes a false claim into immutable PyPI metadata; also explains latent CI and RTD
  failures waiting on the push.
- **MUST-2** `CITATION.cff` / README ship `1.7.0` because semantic-release covers only
  `pyproject.toml`. Locked at the tag, where GitHub and Zenodo read it — directly relevant to the
  SoftwareX submission.
- **MUST-4** `aquacal calibrate -o` is silently ignored, `--dry-run` reports the override as
  applied, and three doc locations instruct readers to use it.
- **MUST-7** `interface.normal_fixed` defaults disagree three ways; a config omitting the key
  silently disables tilt estimation.

## Deviations from plan

- Task 5 was executed by the orchestrator rather than a sixth executor, to avoid a subagent
  backgrounding risk on the commit step and because global re-ranking needed all four fragments
  in one context.
- Four findings were independently re-verified by the orchestrator against source rather than
  accepted from the reporting agent (MUST-1, MUST-2, MUST-4, MUST-7, SH-7). All held.
- One reporting agent's MUST-FIX (`aquacal_data/` gitignore gap) was **downgraded to SHOULD-FIX**
  at merge: a `.gitignore` line is not locked in by the release.
- The plan excluded `docs/tutorials/03_cli_walkthrough.md` as corrected earlier the same day.
  That exclusion was partly wrong — the page is correct on numbers, which is what had actually
  been verified, but it advertises the broken `-o` flag (MUST-4). Recorded in the audit's method
  section.

## Notable clean results

The deferred sphinx `-W` docutils error is genuinely FIXED — confirmed by verifying the function
is actually being autodoc'd, not silently skipped. `deferred-items.md`'s entry can be closed.
The wheel is not broken: `datasets/data/manifest.json` ships, verified by extracting the wheel and
importing it in isolation from `src/`.

## Not done, by design

No fixes applied. A follow-up task applies whatever the user selects from the ranked list.
