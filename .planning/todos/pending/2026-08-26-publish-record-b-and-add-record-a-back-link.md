---
created: 2026-08-26T00:00:00.000Z
title: Publish Zenodo Record B (deposition 22117061) after v2.1.0 is cut, then add Record A's `isSourceOf` back-link by hand
area: data
resolves_phase: 29.2
files: []
---

## Owner

**Phase 29.2, criteria 3, 4 and 5.** Phase 29 built both records and deliberately stopped short of
publishing: **D-29-01** rules that the irreversible act is a human one, performed in the Zenodo web
UI. The automation token carries `deposit:write` only, and `scripts/zenodo_upload.py` contains **no
publish code path at all** — not dead code, not commented scaffolding.

**This closes RUN-05**, the one Phase 29 success criterion that stayed open.

## State as of 2026-08-26

| | Record A — inputs | Record B — results |
|---|---|---|
| Deposition | **22116461** | **22117061** |
| URL | `https://zenodo.org/records/22116461` | `https://zenodo.org/deposit/22117061` |
| Status | **PUBLISHED** | **STAGED, UNPUBLISHED** (`state: "unsubmitted"`, `doi: null`) |
| Version DOI | `10.5281/zenodo.22116461` | not yet minted |
| Concept DOI | `10.5281/zenodo.22116460` | not yet minted |
| File | `real-rig-inputs.zip`, 4,341,018,405 B, md5 `d95a1abc3f7089443ea2bc7ea12fb599` | `real-rig-results-2.1.0.zip`, 9,503,394 B, md5 `f033538e1c9da165aa6267f4ae5d4f78` |

Both md5 round trips were verified against the server's returned checksum at upload time.

## The author's ruling — `defer`, 2026-08-26

At plan 29-08's Task 3 `checkpoint:decision` the author chose **`defer`** over `publish-now`, for
the reason in Step 0 below. **Deferral is a legitimate outcome, not a failure** — Phase 29 closed
against its criteria 1-5, and RUN-05 stays `Pending` until the steps below are done.

## Do these five things, in this order

1. **Cut v2.1.0** (Step 0) — fix CI's `pre-commit` job, PR into `main` with a **merge commit, never
   a squash**, confirm `secrets.RELEASE_TOKEN`, verify `release.yml` tags `v2.1.0`.
2. **Read Record B's rendered description** (Step 1), then **Publish** it.
3. **Then** add Record A's `isSourceOf` back-link by hand (Step 2).
4. **Confirm publication preceded submission** (Step 3) — this closes RUN-05 and criterion 6.
5. **Report both DOIs to the manuscript session** (Step 3).

## Step 0 — v2.1.0 must exist first

**Record B's metadata `version` field and its packaged README both cite `2.1.0`, and that version
has not been released.** Publishing before Phase 29.2 criterion 3 completes mints a permanent record
naming a version that does not exist. Cut the release first.

Measured 2026-08-26: `origin/main` is **0 commits ahead** of `results/rerun-freeze-02`, which is
**406 ahead**. Every `src/aquacal/` change from Phases 23-26 lives on the branch, not on main, so a
release cut from main today would ship v2.0.1-era code.

What the cut requires — all of it Phase 29.2's, all of it before Step 1:

- **Fix CI's `pre-commit` job first.** `.github/workflows/test.yml` runs
  `pre-commit run --all-files` on **both** `push: [main]` **and** `pull_request: [main]`, and 143
  committed artifacts deliberately lack a final newline (plus 439 trailing-whitespace hits). Scope
  the job to changed files, or exclude `experiments/results/`. `.pre-commit-config.yaml` is editable
  again there — D-29-17's fence was Phase-29-scoped. See
  `2026-08-26-no-pull-request-into-main-until-ci-pre-commit-is-scoped.md`.
- **Merge with a MERGE COMMIT — NEVER A SQUASH.** A squash collapses the 406 commits into one
  message, and semantic-release parses only that message; if it reads as `docs:`, **no release fires
  at all and the failure is silent.**
- **Confirm `secrets.RELEASE_TOKEN` exists** before relying on `release.yml`.
- **Verify `release.yml` tags `v2.1.0`** and bumps `pyproject.toml` and `CITATION.cff` (both are in
  `version_toml` / `version_variables`). 43 `feat`, 29 `fix`, zero breaking-change markers across the
  406 commits yields a **minor** bump to 2.1.0.

## Step 1 — read Record B's rendered description before pressing Publish

**Read the record as rendered, end to end. Do not rely on a grep.**

Record A shipped with placeholder-looking prose — `(linked below once Record B exists)` — that a
token-based check did **not** catch, because plan 29-04 had already substituted the token away. An
orchestrator grep for `__RECORD_B_URL__` returned clean on text that was visibly unfinished, and it
was fixed pre-publication **only because the author read the record.**

*A token-based check verifies that a substitution ran, not that its result is finished text.*

While reading, confirm:

- the **supersession sentence naming record 21889922** reads the way a reviewer should read it;
- the **`optimality` labelling sentence** is present in the packaged README (ROADMAP-mandated:
  the value is a *real* gradient, but *volatile*, *not comparable across parameter blocks*, and
  *magnitude-dependent in reliability*);
- `isDerivedFrom` points at **`10.5281/zenodo.22116461`** — Record A's **version** DOI, not the
  concept DOI. This was deliberate: a concept DOI follows the latest version, so it would silently
  re-point Record B's provenance at frames its numbers were never computed from if Record A were
  ever re-versioned.

Then press **Publish**. This mints a permanent DOI. **It cannot be undone** — a published record can
only be superseded by a new version, never unpublished.

## Step 2 — add Record A's back-link by hand

`https://zenodo.org/records/22116461` → **Edit** → **Related identifiers** →
**`isSourceOf`** → Record B's newly minted DOI, scheme **`doi`**.

**Editing published metadata neither cuts a new version nor changes the DOI.**

This is the accepted, author-ruled cost of the `sequential` linkage choice made in plan 29-07:
Record A was published before Record B existed, so **Record A currently carries NO structured A→B
link** — the relationship is expressed only from B's side. The automation cannot add it;
`deposit:actions` is deliberately absent from the token.

## Step 3 — confirm the ordering, and hand both DOIs to the manuscript session

- **RUN-05 / ROADMAP criterion 6** is about **ordering**, not a date: publication must precede
  submission, whenever submission happens. (Amended 2026-08-25 — it previously named 2026-08-21,
  which passed while the re-run was in flight.) If the paper is not yet submitted, that also
  satisfies it.
- Report **both DOIs** to the manuscript session. The paper's DOI citation and its data-availability
  wording are that session's edits (**D-29-19**), never this repository's.
- `.planning/REQUIREMENTS.md` RUN-05 stays `Pending` until this is confirmed. Plans 29-04 and 29-07
  each had to avoid marking it complete prematurely; do not be the third.

## Evidence

- `.planning/phases/29-gate-verification-results-commit/29-zenodo-record-a.txt`
- `.planning/phases/29-gate-verification-results-commit/29-zenodo-record-b.txt`
- `.planning/phases/29-gate-verification-results-commit/29-PHASE-RECORD.md` § *Criterion 6* and
  § *Open items handed forward*, items 1, 2 and 4
- `.planning/ROADMAP.md` § *Phase 29.2: Merge, Release, and Publish*
