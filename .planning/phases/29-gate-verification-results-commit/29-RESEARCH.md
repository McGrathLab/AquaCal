# Phase 29: Gate Verification & Results Commit — Research

**Researched:** 2026-08-26
**Domain:** Scientific-artifact provenance grading, git commit mechanics under an ignore policy, and the Zenodo REST API (deposition draft + bucket upload)
**Confidence:** HIGH for everything repo-side (measured this session in a disposable probe clone); HIGH for the Zenodo API surface (developers.zenodo.org, fetched this session); MEDIUM for the legacy-vs-InvenioRDM deprecation posture.

---

## Summary

This phase has far less unknown in it than it looks. **Four of the six ROADMAP success criteria
were measured to completion during this research session**, in a throwaway clone that mutated
neither the working clone nor the production clone. The gate passes over a *relocated copy* of the
returned tree at `176 PASS, 7 N/A, 0 FAIL` with `gate3_git_sha_consistency` green on the single sha
`7005a277…`; the E2 same-seed control passes at a worst-case relative drift of **2.5e-08**; the E7
fixed-arm sign test **holds unchanged at 10/10, p = 0.00098**; and the exact set of files the ignore
rules admit is **227**, none of which exceeds `check-added-large-files --maxkb=1000`. What Phase 29
must do is *re-derive these in a plan-owned, committed evidence set* and then do the two things
research cannot: commit, and upload.

Three findings change the shape of the plan and are not in `29-CONTEXT.md`.

**(1) D-29-12's "measure first" has been done, and D1's prediction is exactly right — 8 failures,
same 8 node ids.** Every one is a stale assertion, not a bad number, and every one has a specific
one-line diagnosis (below). Two of them are `run_manifest.json` being swept into rails written for
benchmark records; three are new artifacts (E6 per-camera CSVs, DEGEN breakdown JSONs) with no map
entry; two are E1's band having been cut from ten seeds to **four** by Ruling A1 while the map text
still says "seeds 42-51"; one is a gitignored 2.1 MB `calibration.json` reaching a JSON discovery
helper that — unlike its CSV sibling — has no `_is_tracked` filter.

**(2) A byte-integrity hazard the phase must actively avoid.** `end-of-file-fixer` and
`trailing-whitespace` would rewrite **147** of the 227 files being committed (143 lack a final
newline, 4 carry trailing whitespace). That would destroy the "byte-for-byte what the run produced"
property D-29-08 exists to protect. It is currently *latent*, not active: `.git/hooks/` is empty in
both clones and `pre-commit install` has never been run — verified. The plan must keep it latent
(commit with `--no-verify`, never run `pre-commit run --all-files`) and must not push this branch
into `main`, where CI does run `pre-commit run --all-files`.

**(3) D-29-17's file-count arithmetic needs one correction, which does not disturb the decision.**
The ~11 MB `all_observation_depths.csv` cited as the thing that would trip
`check-added-large-files` **is already gitignored** (`.gitignore:478`), and no non-ignored file in
the entire returned tree exceeds 1000 KB. The decision — "commit what the existing ignore rules
allow" — is unchanged and now has a precise number: **227 files**, which is attempt 1's 209 *plus
the 18 per-stage stage logs that `.gitignore:507` was deliberately widened to admit during Phase
28*. "Match attempt 1's shape" and "what the ignore rules allow" differ by exactly those 18 files,
and the ignore rule is the newer, deliberate authority.

**Primary recommendation:** grade in a disposable probe clone (the operation is already proven),
land the 227 files on `results/rerun-freeze-02` with `--no-verify`, fix the 8 provenance assertions
in place per D-29-13, and build the Zenodo tooling as one standalone `scripts/zenodo_*.py`
rehearsed against `sandbox.zenodo.org` with a small dummy file before the real 4.35 GB PUT.

---

## User Constraints (from CONTEXT.md)

### Locked Decisions

*(Copied verbatim from `.planning/phases/29-gate-verification-results-commit/29-CONTEXT.md`
`<decisions>`.)*

#### Zenodo publish mechanism (RUN-05)

- **D-29-01:** **Automate the upload into an UNPUBLISHED DRAFT; the author reviews the draft in
  the Zenodo web UI and presses Publish there.** A Zenodo deposition exists as a draft from
  creation — files, metadata and all — and **no DOI is registered until Publish**. This decouples
  the two constraints: the 4.35 GB transfer runs headless on the Linux box (where GUI access is
  uncertain), while review and minting happen from any browser, any time, since drafts persist.
  — **Reversibility:** one-way — the Publish call mints a permanent DOI that can never be
  unpublished, only superseded by a new version. Everything up to Publish is fully reversible;
  a draft can be edited or discarded.

  **This preserves `PROJECT.md`'s locked decision rather than overriding it.** That decision reads
  *"Zenodo is published by the user by hand, values pre-computed for transcription"*, with the
  rationale *"publishing is irreversible and assigns a permanent DOI."* Under D-29-01 the
  irreversible act is still a deliberate human action. Only the browser dependency for the
  **upload** is dropped, which is not what the decision was protecting.

- **D-29-02:** **Populate full metadata on both drafts** — title, authors, description, license,
  version, and the related-identifier links between Record A and Record B. The author opens two
  finished drafts to check, rather than filling forms without GUI access.

- **D-29-03:** **Do NOT reserve the DOIs.** Zenodo can display a reserved DOI on an unpublished
  draft, but reservation commits to that identifier and the manuscript does not need the strings
  before Publish. Revisit only if §3 or the data-availability statement needs a DOI before the
  author will have pressed Publish.

- **D-29-04:** **Record A's upload starts immediately and in parallel with all grading work.**
  It holds inputs, which grading cannot invalidate, and at 4.35 GB it is the phase's critical
  path — the paper submits within days and the transfer is hours.

- **D-29-05:** **Record B's draft is built only AFTER grading passes** (RUN-03's gate verification
  and the E2 same-seed control), so the results package can never contain numbers a later check
  disowns. Costs nothing on the critical path, since Record A is the long pole.

- **D-29-06:** **Rehearse the entire split on `sandbox.zenodo.org` first** — create Record A,
  upload, create Record B, confirm both drafts render correctly in the UI. Separate instance,
  separate tokens, throwaway DOIs. One cheap pass, so the real draft the author reviews is one
  already known to be shaped right. Justified by D-29-01's one-way rating.

- **D-29-07:** **Use the Zenodo REST API, not a browser** (carried from the folded todo). Large
  files go to the bucket URL (`PUT /api/files/<bucket>/<filename>`), not the small form-based
  files endpoint. The token is read from the environment and never committed.
  **Multipart resume is explicitly NOT a concern** (author, 2026-08-25) — a plain streaming `PUT`
  with a retry-on-failure loop is sufficient; no resume machinery is to be built.

#### Test and gate noise vs. publication (RUN-03)

- **D-29-08:** **The run's outputs are immutable. Nothing regenerates any artifact.** Where a
  check fails because it encodes a stale expectation — e.g. it does not expect a column
  deliberately added since — **the check is fixed, not the run repeated.**

- **D-29-09:** **Test and gate noise does not block the Zenodo publish.** The author's ruling:
  the outputs are scientifically valid and are to be published, *"barring a finding that refutes
  that."* Supporting measurement from this session, not assumption: `real_rig_metrics.json` is
  **bit-identical** to attempt 1; across every JSON in `results/` exactly one substantive field
  differs and it is a deliberate 29.1 improvement; 19 of 26 CSVs are bit-identical and the rest
  differ only in timing, peak memory, and the now-populated 198 guard count.

- **D-29-10:** **The stop list — the only findings that block publication.** Anything outside
  these three is fixed if cheap, ruled on if not, and never blocks:
  1. **The E2 same-seed control fails** (seed 42 vs seed 42, ~1e-8). The designated sanity check
     and the only one that speaks to solver correctness.
  2. **`gate3_git_sha_consistency` stops holding** on the committed tree — artifacts from mixed
     shas, the exact provenance fracture this milestone exists to prevent.
  3. **A §3-facing number traces to an artifact that disagrees with it.**

- **D-29-11:** **Scope correction — the gate is already clean; only pytest rails are in
  question.** `check_rerun_gates.py` over the returned tree reports `176 PASS, 7 N/A, 0 FAIL`
  with zero `[FAIL]` lines, and `gate3_git_sha_consistency`, `gate3_run_manifest_fields` (all 17
  environment fields non-null) and `gate3_run_manifest_clean_tree` all PASS. What may fail is
  `tests/unit/test_experiments_provenance.py`, which asserts artifact **metadata** — sha, seed,
  environment fields — and touches no measured value. A failure there cannot by construction
  indicate the numbers are wrong.

- **D-29-12:** **D1's "8 failures" is a prediction, not a measurement — measure first.** The 8
  were counted against *attempt 1's* tree. Phase 29.1 has since fixed several of the exact
  defects those tests probe (E4's guard count, E1's band sidecar, stale annotation strings, and
  the `.[dev,bench]` install that was nulling manifest fields). The real count against attempt
  2's artifacts is unknown until run.

- **D-29-13:** **Where an assertion encodes an expectation that moved by design, fix the
  assertion.** Nothing is deselected, xfailed, skipped or loosened to a tolerance.

- **D-29-14:** **Fall-through: anything neither assertion-wrong nor cheaply fixable becomes a
  post-submission todo.** Recorded with what fails and what would fix it; the phase closes.

- **D-29-15:** **D4's three exact-equality anchor failures stand as ruled on** in the
  `rerun-freeze-02` tag annotation. `pytest tests/` reports `3 failed, 2407 passed, 26 skipped`.
  **Three is the expected count — zero or four are both anomalies.**

#### E7 before/after comparison (ROADMAP criterion 3)

- **D-29-16:** **Measure, report both numbers in the phase record, and flag to the author only if
  the conclusion moved.** FIX-02 gave E7 two extra free parameters per interface, which could
  soften the fixed-intrinsics arm's published 10-of-10 sign test (p = 0.00098, supplement §14).
  If it held, it is a line in the record. If it moved, it is raised explicitly — **§3 edits stay
  the author's**, matching how the manuscript has been handled throughout. This is the one area
  of the phase that can reach into §3, and the ROADMAP's own wording is the reason it is graded
  here: *"it is reported here, not discovered during manuscript re-verification."*

#### What gets committed (RUN-04)

- **D-29-17:** **Follow DATA-01b as it stands; match attempt 1's shape.** Commit what the
  existing ignore rules allow — attempt 1 landed 147 tracked files under `experiments/results`
  — and leave the gitignored bulk in the archive and Zenodo Record B. **No ignore rule changes
  during this phase.** Committing all 461 files would trip `check-added-large-files` (the ~11 MB
  `all_observation_depths.csv` alone), which 29.1-09 explicitly rejected. The read-only tarball
  and its recorded sha256 are the record for everything git will not hold.

- **D-29-18:** **The results commit lands on `results/rerun-freeze-02`**, the branch renamed this
  session to match attempt 1's convention — exactly as attempt 1's `83da9b3 results(28): full
  production suite at rerun-freeze-01` landed on `results/rerun-freeze-01`.

- **D-29-19:** **RUN-04's traceability obligation is discharged repo-side, and criterion 5 is
  narrowed to match it.** RUN-04's own wording is *"every §3-facing number is traceable **to this
  run**"*; ROADMAP criterion 5 restates it as *"every §3-facing number **in the manuscript**"*,
  which reaches outside this repository. **The requirement is the authority.**

  `main.tex` lives in `OneDrive - Georgia Institute of Technology/Thesis/Spinoffs/papers/aquacal/`
  — **not in this repo**; the only `.tex` files here are generated fragments. The traceability
  mechanism already exists and is this run's own output: `benchmark_grid.tex`,
  `cpr_derived_values.tex` and `cpr_grouping.tex`, which §3 includes rather than hand-copying.
  That is `PROJECT.md`'s locked decision *"Generate the results table from `benchmark.json`, not
  by hand"* (✓ Good — *"provenance table now maps every artifact to its script"*).

  **Phase 29 therefore:** commits the generated fragments alongside the artifacts that produced
  them at the frozen sha, with `gate3_git_sha_consistency` proving the single-sha property.
  **Phase 29 does NOT:** build a mapping document against the manuscript. That is the
  manuscript-side half, already owned by **POST-01** (*"§3, the Zenodo archive's
  `reference_outputs/`, and the tutorial's expected-value table are re-cut as a matched set
  against the new E2 numbers"*), mapped to **Phase 30**. Both halves are owned; neither is
  dropped. Author's ruling, 2026-08-25.

### Claude's Discretion

- The exact structure of the upload/publish tooling (single script vs. module, argument surface,
  where it lives in the tree) — no decision was requested and none is locked.
- Task ordering within the phase, beyond D-29-04 (Record A first, in parallel) and D-29-05
  (Record B after grading).
- How the E7 before/after comparison is computed, so long as both numbers land in the record.

### Deferred Ideas (OUT OF SCOPE)

- **Manuscript-side reconciliation of §3** — POST-01, **Phase 30**. Phase 29 discharges the
  repo-side half only (D-29-19).
- **`_manifest.py`'s pinned Zenodo record id** may need repointing once the record is split.
  Flagged for planning to scope; may belong to Phase 30 with POST-01.
- **The E7 band overwrite hazard** —
  `.planning/todos/pending/2026-08-20-e7-band-mirrors-e1-benchmark-overwrite-hazard.md`. Measured
  2026-08-24 as **not firing** in the production run (`run_stage_e7_band` passes no `--force`).
  Residual risk: a manual `--force` band run at E7 fires it. **Do not run E7's band by hand.**
- **D6 — `check_e2_band`'s sibling-directory resolution ignores `--smoke`.** Irrelevant to a
  production run. Left unfixed inside the freeze.

---

## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| **RUN-03** | `check_rerun_gates.py` passes over the complete run, including Gate 3's single-sha assertion now that the previously-uncovered stages are inside the queue | § *The Grading Mechanics* — the gate is hermetic w.r.t. the host clone (Gate 3 reads only artifact-recorded `git_sha` values, never live git), so it re-runs cleanly over a relocated copy. **Reproduced this session: `176 PASS, 7 N/A, 0 FAIL`, exit 0, zero `[FAIL]` lines.** § *The E2 Same-Seed Control* and § *The E7 Before/After Comparison* supply the two ROADMAP criteria that sit beside the gate. |
| **RUN-04** | The returned results are committed with provenance intact, and every §3-facing number is traceable to this run | § *Commit Mechanics* — the exact 227-file admitted set, the byte-integrity hazard and its containment, the three `.tex` fragments that discharge traceability under D-29-19, and the copy procedure that leaves the prod clone untouched. |
| **RUN-05** | The Zenodo record is split into immutable inputs and a versioned results package, and the results package matching this run's numbers is published **before the paper is submitted** | § *Zenodo REST API* — verified draft/bucket/publish surface, metadata schema, `related_identifiers` relation values, token scopes, quotas, and the failure modes a 4.35 GB streaming PUT actually hits. § *The A/B Split Payloads* gives the measured composition of the source archive, which is on this machine. |

---

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Gate re-run over the returned tree | Local CLI (`experiments/check_rerun_gates.py`) | — | Already re-runnable at `--profile full`; hermetic w.r.t. host git. No new gate. |
| Provenance-rail assertion repair | Test tier (`tests/unit/`) | — | D-29-13 fixes assertions, never artifacts. `tests/` is outside the frozen `experiments/` tree. |
| E2 same-seed control | Analysis script / evidence file | Test tier | A read-only JSON comparison; belongs in the phase evidence set, not as a new permanent rail. |
| E7 before/after sign test | Analysis script / evidence file | — | Pure re-analysis of two committed CSVs; no solve. |
| Results commit | git (working clone, `results/rerun-freeze-02`) | — | The prod clone is read-only by decision; files are copied out, never committed from. |
| Archive repackaging (A/B split) | Local filesystem + `zip` | — | Source archive is already extracted on this machine. |
| Zenodo draft create / file upload / metadata | Zenodo REST API over HTTPS (`requests`) | — | Network tier. Publish is explicitly a **human** action in the Zenodo web UI (D-29-01). |
| Secret handling (API token) | Process environment | — | D-29-07: read from env, never committed. |

---

## Project Constraints (from CLAUDE.md)

**There is no `CLAUDE.md` and no `.claude/CLAUDE.md` in this repository, and no
`.claude/skills/` or `.agents/skills/` directory.** [VERIFIED: `ls` over repo root and `.claude/`
this session — `.claude/` contains only `worktrees/`.] The binding project constraints therefore
come from `.planning/` and from the toolchain config, and they are:

| Constraint | Source | Effect on the plan |
|---|---|---|
| Ruff `line-length = 88`, `target-version = "py311"`, lint select `E4,E7,E9,F,W,I`, format `quote-style = "double"` | `pyproject.toml:94-110` | Any new script must pass `ruff check` and `ruff format --check`. Pre-push hooks run ruff over **all** files. |
| `check-added-large-files --maxkb=1000` | `.pre-commit-config.yaml` | Verified non-binding for this commit (largest admitted file is 119 KB). |
| `detect-secrets` with `--baseline .secrets.baseline`, excluding `experiments/…results[^/]*/…` | `.pre-commit-config.yaml` | Verified PASS against the full 227-file staged set this session. A Zenodo token must never be written to a file. |
| `end-of-file-fixer`, `trailing-whitespace` | `.pre-commit-config.yaml` | **Would rewrite 147 of the 227 files.** See § *The Byte-Integrity Hazard*. |
| Pre-push hooks: `bash .hooks/pre-push-ruff-check.sh`, `bash .hooks/pre-push-ruff-format.sh` (`stages: [pre-push]`, `pass_filenames: false`) | `.pre-commit-config.yaml` | Only fire if `pre-commit install --hook-type pre-push` has been run. It has not been. |
| CI `pre-commit run --all-files` | `.github/workflows/test.yml:42-57`, triggered `on: push: branches: [main]` / `pull_request: branches: [main]` | Does **not** fire for `results/rerun-freeze-02`. Would fire on a PR into `main` — a Phase-30 concern. |
| Acceptance is read from the roll-up `TOTAL:` line, never from `$?` (D-01/D-02) | `29-CONTEXT.md` § Established Patterns | The gate driver exits non-zero on a healthy full-suite run. *(Note: the standalone `check_rerun_gates.py` invocation used for grading does exit 0 — measured — but the roll-up line stays the verdict of record.)* |
| Evidence files use a per-attempt prefix (`freeze01-*`, `freeze02-*`) side by side | `29-CONTEXT.md` § Established Patterns | Phase 29's evidence set should follow: `29-*.txt` / `29-*.md` in the phase directory. |
| Records of what was measured are annotated, never rewritten | `29-CONTEXT.md` § Established Patterns | Superseded findings get a dated note. |

---

## The Grading Mechanics (RUN-03)

### `check_rerun_gates.py` — invocation surface

[VERIFIED: `experiments/check_rerun_gates.py:2276-2331`, read this session]

```
positional:  out_dir           Output directory containing the re-run's artifacts (e.g. experiments/results/)
--profile    {PROFILES}        'smoke' asserts artifact existence only; 'full' asserts row counts.
                               Omitted: the completeness gate does not run.
--stage      <stage id>        Restrict the completeness gate to one stage id from
                               experiments/suite_expectations.json. Ignored without --profile.
```

`main()` prints one `[VERDICT] EXPERIMENT gate detail` line per result, then a blank line, then
`TOTAL: {n_pass} PASS, {n_na} N/A, {n_fail} FAIL`, and `return 1 if n_fail else 0`.

**The full-tree grading invocation is therefore:**

```bash
python experiments/check_rerun_gates.py experiments/results --profile full
```

### Two path facts the plan must honour

1. **`check_e2_band` reads a SIBLING of `out_dir`, not a child.**
   `run_all_gates` calls
   `check_e2_band(out_dir.parent / "results_e2_band", committed_metrics_path=out_dir / "real_rig_metrics.json")`
   [VERIFIED: `experiments/check_rerun_gates.py:2262-2264`]. A grading tree that contains only
   `experiments/results/` will not grade E2's band. **All six output trees must be present
   together**, at their original relative paths, for the roll-up to reproduce.

2. **Gate 3 is hermetic with respect to the host clone.** `_check_git_sha_consistency` collects
   `environment.git_sha` from artifacts under `out_dir` and asserts they agree
   [VERIFIED: `experiments/check_rerun_gates.py:2011-2037`]; `_check_run_manifest` compares
   `run_manifest.json`'s `git_sha` to that same set and reads the *recorded* `git_dirty` field for
   the clean-tree assertion [VERIFIED: `experiments/check_rerun_gates.py:2040-2190`]. **Nothing
   shells out to live git.** This is why the tree can be copied into a different clone at a
   different HEAD and still pass — which is exactly what Phase 29 must do.

### Measured this session — the gate reproduces over a relocated copy

Procedure: `git clone` the working clone into a scratch directory, check out
`results/rerun-freeze-02`, `cp -a` all six output trees plus the three state artifacts from
`~/aquacal-frozen-rerun-freeze-02-prod`, then run the gate. **Neither the working clone nor the
production clone was modified.**

```
TOTAL: 176 PASS, 7 N/A, 0 FAIL          exit code 0
[FAIL] line count: 0
[PASS] ALL gate3_git_sha_consistency     every artifact carries the same git_sha (7005a2771aa115e4f4c1284cec7e145739586a4a)
[PASS] ALL gate3_run_manifest_present    run_manifest.json found and parsed
[PASS] ALL gate3_run_manifest_fields     all 17 required environment fields are present and non-null
[PASS] ALL gate3_run_manifest_git_sha    manifest git_sha matches every artifact (7005a2771aa115e4f4c1284cec7e145739586a4a)
[PASS] ALL gate3_run_manifest_clean_tree the working tree was clean when this run started
```

[VERIFIED: run this session in a disposable probe clone; agrees line for line with
`.planning/phases/28-full-suite-production-run/freeze02-gates-full.txt`]

**ROADMAP criterion 1 is therefore already demonstrable.** Phase 29's job is to reproduce it once
more *against the committed tree* and to write the output to a `29-gates-*.txt` evidence file.

### The working clone is byte-identical to the frozen tag outside `.planning/`

```
git diff --stat rerun-freeze-02 HEAD -- . ':(exclude).planning'    ->  (empty)
git merge-base HEAD rerun-freeze-02                                ->  7005a2771aa115e4f4c1284cec7e145739586a4a
git log --oneline rerun-freeze-02..HEAD | wc -l                    ->  34   (all docs/planning)
```

[VERIFIED: run this session in `/home/tlancaster/aquacal-frozen-rerun-freeze-01`]

So grading may run in the working clone itself once the tree is copied in; the gate code, the
expectations file and `_run_manifest.py` are all the frozen versions. There is no need to grade
from the prod clone.

---

## The D1 Provenance Rails — MEASURED, not predicted (D-29-12)

### Method

Same probe clone. All 227 admitted files were `git add`-ed (staging is sufficient —
`_is_tracked()` shells `git ls-files --error-unmatch`, which reads the index
[VERIFIED: `tests/unit/test_experiments_provenance.py:333-355`]). Then:

```bash
python -m pytest tests/unit/test_experiments_provenance.py -q -p no:cacheprovider
```

### Result: **8 failed, 279 passed, 20 skipped in 23.11s** — the same 8 node ids D1 recorded

[VERIFIED: run this session]

| # | Node id | Root cause | Cheapest correct fix (D-29-13) |
|---|---|---|---|
| 1 | `TestEnvironmentPresence::test_every_benchmark_record_has_environment[run_manifest.json]` | `run_manifest.json` carries `schema_version` but is **flat** — its keys are `aquacal_version_declared, blas_thread_cap, …, git_sha, …` with no `environment` block. It is DRIVER-02's suite-level manifest, a different schema from `assemble_benchmark_record`. | Exclude `run_manifest.json` from `_schema_versioned_json_files()` (or add a named carve-out beside `SELF_DESCRIBING_JSON`), with a comment naming `experiments/_run_manifest.py:82` as its schema owner. |
| 2 | `TestSeedProvenance::test_every_benchmark_record_carries_a_seed[run_manifest.json]` | Same file, same cause — no `solver_config`. A suite-level manifest describes a *run*, not a solve; it has no seed to carry. | Same carve-out as #1 — one fix resolves both. |
| 3 | `TestCsvProvenanceMap::test_all_committed_csvs_have_a_named_record[generalization_sweep_per_camera.csv]` | New E6 artifact, no `CSV_TO_RECORD` entry. | Add a map entry naming `experiments/results/e6_provenance.json`. |
| 4 | `…test_all_committed_csvs_have_a_named_record[generalization_sweep_per_camera_band.csv]` | New E6 band artifact, no map entry (the assertion message reports the record text as `''`). | Add a map entry naming `e6_seed_band_provenance.json` **and containing the literal `seeds 42-47`** — otherwise #7 fails instead. |
| 5 | `TestCsvProvenanceMap::test_multi_seed_band_declares_its_seed_coverage[exp1_band.csv]` | The artifact spans **4 seeds (42-45)**; the map text still says `seeds 42-51`. This is **Ruling A1 (2026-08-15)**, which cut E1's band from ten seeds to four. | Update the map text `seeds 42-51` → `seeds 42-45`. |
| 6 | `…test_multi_seed_band_declares_its_seed_coverage[exp1_parameter_band.csv]` | Same, same entry family. | Same. |
| 7 | `…test_multi_seed_band_declares_its_seed_coverage[generalization_sweep_per_camera_band.csv]` | Spans 6 seeds (42-47); no entry at all. | Covered by the #4 fix if the span string is included. |
| 8 | `TestSelfDescribingJson::test_schema_versionless_json_set_equals_self_describing_json` | Six extra schema-versionless JSONs beyond the two named: `e1_degeneracy_breakdown.json`, `e5_degeneracy_breakdown.json`, `e5_seed_band_degeneracy_breakdown.json`, `e7_degeneracy_breakdown.json`, `e7_seed_band_degeneracy_breakdown.json` (**all five new from DEGEN-01/DEGEN-02, deliberately added since**) and `calibration.json` (**2.1 MB and gitignored** — it reaches the rail only because `_discover_json_files()` has no `_is_tracked` filter, unlike its CSV sibling `_discover_csv_files()`). | Two independent fixes: (a) add the five degeneracy breakdowns to `SELF_DESCRIBING_JSON` with the record that covers each; (b) give `_discover_json_files()` the same `_is_tracked` filter `_discover_csv_files()` already has, so gitignored working-tree output stops entering a rail whose docstring scope is *"committed under `experiments/results/`"*. |

**Every one of the eight is an assertion encoding an expectation that moved by design.** None
touches a measured value. This is precisely the D-29-08/D-29-13 case, and none of them is on
D-29-10's stop list.

### The other four tree-keyed modules are clean

`tests/unit/test_baseline_paths.py`, `test_expectations.py`, `test_experiments_e3.py`,
`test_experiments_e5.py`, `test_experiments_io.py` → **245 passed** against the repopulated tree.
[VERIFIED: run this session] So the D1 module is the only one affected by repopulation.

### D4's three anchor failures still fail (D-29-15's "three is the expected count")

```
FAILED tests/unit/test_discard_accounting.py::test_matches_frozen_anchor
FAILED tests/unit/test_optim_common.py::TestPerObservationDetailSinks::test_detail_sink_recomputed_geometry_matches_projector
FAILED tests/unit/test_pipeline.py::TestSolverConfigSeedIsInert::test_matches_pre_change_anchor
3 failed in 22.50s
```

[VERIFIED: run this session]

**Expected full-suite failure count for Phase 29 against a repopulated tree: 3 (D4) + 8 (D1) = 11,
falling to 3 once the eight assertions are repaired.** State that number in the plan so a verifier
can distinguish "as ruled" from "something new".

### How `resolve_results_dir()` chooses

[VERIFIED: `tests/unit/_baseline_paths.py:96-110`, read this session]

```python
def resolve_results_dir(repo_root=None) -> tuple[pathlib.Path, str]:
    live = live_results_dir(repo_root)
    if _holds_a_file(live):
        return live, "live"
    return archive_results_dir(repo_root), "archive"
```

with `LIVE = ("experiments", "results")` and
`ARCHIVE = ("experiments", "pre_rerun_baseline", "results")`, and `_holds_a_file` using
`rglob("*")` rather than `iterdir()` "because E4's records live one level down, in
`e4_cells/<cell>/benchmark.json`".

The consequence for task ordering: **the D1 rails flip subject the moment the first file lands
under `experiments/results/`.** A plan that copies the tree in and then runs the suite gets 11
failures; a plan that runs the suite first gets 3. Order the tasks knowingly.

---

## The E2 Same-Seed Control (ROADMAP criterion 2) — MEASURED

### Where the numbers live

| Tree | Path | Role |
|---|---|---|
| Pre-run baseline | `experiments/pre_rerun_baseline/results/real_rig_metrics.json` | The **"before"** — Phase 26 / DRIVER-04's archive of the committed pre-re-run tree. `md5 3d943f68d34fa37587a7826ac02916bc`. |
| Attempt 1 | `experiments/freeze01_run_output/results/real_rig_metrics.json` | The 2026-08-20 Linux run. `md5 57279708f6106f411d1fe03ed2698291`. |
| Attempt 2 (this run) | `~/aquacal-frozen-rerun-freeze-02-prod/experiments/results/real_rig_metrics.json` | The **"after"**. `md5 57279708f6106f411d1fe03ed2698291` — **byte-identical to attempt 1**. |

[VERIFIED: `md5sum` over all three, this session. This independently confirms D-29-09's
bit-identical claim.]

**All three carry `solver_config["seed"] == 42`** in the sibling `benchmark.json`
[VERIFIED: this session], so the comparison is same-seed as the criterion requires. The three
environments differ exactly as expected:

| Tree | `git_sha` | `aquacal_version` | `numpy` | `opencv` | `os` |
|---|---|---|---|---|---|
| pre_rerun_baseline | `6c7f930b…` | 1.8.0 | 2.4.2 | 4.13.0 | Windows 11 |
| freeze01_run_output | `3ab9c137…` | 2.0.1 | 2.4.6 | 4.13.0 | Linux 6.8.0-136-generic |
| freeze-02 (this run) | `7005a277…` | 2.0.1 | 2.4.6 | 4.13.0 | Linux 6.8.0-136-generic |

### The control passes

Relative drift, pre-run baseline → this run, seed 42 vs seed 42:

| Field | pre_rerun_baseline | freeze-02 | rel. drift |
|---|---:|---:|---:|
| `water_z_m` | 1.073840398 | 1.073840401 | **2.79e-09** |
| `mean_per_camera_reprojection_px` | 0.8240385366779744 | 0.8240385407126619 | **4.90e-09** |
| `inter_corner_mae_mm` | 0.25817717557392356 | 0.25817717737878654 | 6.99e-09 |
| `mean_relative_error_pct` | 0.4302952926232059 | 0.4302952956313109 | 6.99e-09 |
| `mean_reprojection_px` | 0.9276607330387148 | 0.9276607463816985 | 1.44e-08 |
| `inter_corner_rmse_mm` | 0.628138580850984 | 0.628138596646187 | **2.52e-08** (max) |
| `n_comparisons` | 7762 | 7762 | 0 (exact) |

[VERIFIED: computed this session from the two JSON files named above]

**Worst-case relative drift is 2.5e-08, on the same order as F-001's measured 1.5e-8 for the
identical Windows→Linux / `6c7f930`→v2.0.1 span.** The §3 headline
`mean_per_camera_reprojection_px` drifts 4.9e-09 — better than the ~1e-8 the criterion asks for,
and consistent with the 3.07e-09 recorded on 2026-08-17. **DEGEN-02's touch of `_optim_common.py`
did not perturb the solve.**

### Guardrails the control's own output must carry

- **State the seed in the output.** `29-CONTEXT.md` criterion 2 is explicit: E2's seed band on
  `mean_per_camera_reprojection_px` spans 0.761 → 0.910 px, so a cross-seed comparison of the same
  quantity looks catastrophic. The gate's printed line must read *"seed 42 vs seed 42"*.
- **Name the baseline file, not "the pre-run numbers".** There are two candidate baselines and
  they differ: `pre_rerun_baseline/` (Windows, 1.8.0) and `freeze01_run_output/` (Linux, 2.0.1).
  The criterion's "~1e-8 across the whole span" is the `pre_rerun_baseline/` comparison; the
  `freeze01_run_output/` comparison is exactly zero (byte-identical) and is a *different, weaker*
  statement. **Report both, label both.**
- **Do not confuse this with `check_e2_band`.** That gate compares the band's seed-42 record to the
  same-run `real_rig_metrics.json` at `rtol=1e-6` — a *within-run* consistency check. It is
  already covered by the roll-up and is not ROADMAP criterion 2.

---

## The E7 Before/After Comparison (ROADMAP criterion 3 / D-29-16) — MEASURED

### Where the published number comes from

The 10-of-10, p = 0.00098 result is produced by
**`.planning/phases/19.2-experiment-execution-and-provenance/analyze_e7_spread.py`**
[VERIFIED: read in full this session]. Its recipe, verbatim from the source:

- `METRIC = "camera_height_drift_mm"`
- `PAIRS = [("shared_fixed", "percamera_fixed"), ("shared_refined", "percamera_refined")]`
- group by `(arm, seed)`, take `mean` of `abs(METRIC)`
- `diff = per.loc[percam] - per.loc[shared]`  (`> 0` means shared is better)
- `n_pos = int((diff > 0).sum())`; `crosses = bool(diff.min() < 0 < diff.max())`
- `p_one = sum(comb(n, k) for k in range(n_pos, n + 1)) / 2**n`
- `r = per.loc[shared].corr(per.loc[percam])`

**Two cautions about that script as it stands.** Its `ROOT` is a hard-coded Windows path
(`C:/Users/tucke/Desktop/Aqua/AquaCal/seed_sweep_19_2/e7_interface_ablation`) and it globs per-seed
`interface_ablation.csv` files from a sweep directory that no longer exists on this machine; and
its own closing `CAVEAT` text is hard-wired to `n = 5`. **Do not run it as-is.** The modern input
is `experiments/results/interface_ablation_band.csv`, which carries `arm`, `seed` and
`camera_height_drift_mm` columns directly (480 rows = 4 arms × 10 seeds × 12 cameras)
[VERIFIED: column list read this session].

### The recipe reproduces the published number exactly on the baseline

Applying the recipe above to `experiments/pre_rerun_baseline/results/interface_ablation_band.csv`
gives **10/10, p = 0.00098** for the fixed pairing and **8/10, p = 0.05469** for the refined
pairing — which is exactly what `.planning/phases/19.3-…/.continue-here.md:174-176` records as
published (*"The primary `fixed` pairing STRENGTHENED to 10/10, no zero crossing, p = 0.00098. The
secondary `refined` pairing WEAKENED to 8/10 (p = 0.055)"*). **The recipe is confirmed correct by
reproducing its own published output.**

### The result

| Tree | pairing | shared better | crosses zero | `p_one` | `r` | paired diff range |
|---|---|---:|---|---:|---:|---|
| pre_rerun_baseline (**before**) | `shared_fixed` vs `percamera_fixed` | **10/10** | no | **0.00098** | +0.5567 | [+0.9190, +1.8792] |
| pre_rerun_baseline (**before**) | `shared_refined` vs `percamera_refined` | **8/10** | yes | **0.05469** | +0.8372 | [−0.4707, +2.5243] |
| freeze-02 (**after**) | `shared_fixed` vs `percamera_fixed` | **10/10** | no | **0.00098** | +0.5059 | [+0.7878, +1.8014] |
| freeze-02 (**after**) | `shared_refined` vs `percamera_refined` | **7/10** | yes | **0.17188** | +0.8435 | [−0.5419, +2.5335] |

[VERIFIED: computed this session from the two `interface_ablation_band.csv` files]

**Findings the plan should carry forward:**

1. **The published primary conclusion HELD.** FIX-02's two extra free parameters per interface did
   **not** soften the fixed-intrinsics arm. 10/10, no zero crossing, p = 0.00098 — identical.
   Under D-29-16 this is *"a line in the record"*, not an author escalation.

2. **The secondary refined pairing MOVED: 8/10 (p = 0.055) → 7/10 (p = 0.172).** That number is
   also in supplement §14 / MF-05. It was already non-significant and is now more clearly so, so
   the *conclusion* ("E7 does not support a directional claim on the refined arm") is unchanged —
   but the digits are published and they moved. **Under D-29-16 this is the flag-to-author case.**
   Raise it explicitly; do not edit §3.

3. **Attempt 1 and attempt 2 are byte-identical on this artifact**
   (`md5 b6515ed77ed04268608b74217716020b` for both `freeze01_run_output/results/` and the
   freeze-02 tree) [VERIFIED: `md5sum`, this session]. So the 8→7 move landed **before** attempt
   1, i.e. it is a Phase 23-26 change (FIX-02), not a re-run artefact. Say so, so nobody attributes
   it to the run.

4. **Do not run E7's band by hand** to re-derive this (deferred item: the `--force` overwrite
   hazard). The comparison is pure re-analysis of two committed CSVs — no solve, no `--force`.

---

## Commit Mechanics (RUN-04)

### The returned tree, and where it is

`~/aquacal-frozen-rerun-freeze-02-prod` — detached HEAD at `7005a2771aa115e4f4c1284cec7e145739586a4a`,
tag `rerun-freeze-02`, **9 untracked top-level entries and nothing else**
[VERIFIED: `git -C … status --porcelain`, this session]:

```
?? experiments/results/
?? experiments/results_e2_band/
?? experiments/results_e2_invocations/
?? experiments/results_e2_memory/
?? experiments/results_e2_timing/
?? experiments/results_e4_repeat/
?? experiments/run_experiment_suite_state.7005a27.failures.txt
?? experiments/run_experiment_suite_state.7005a27.stagelogs/
?? experiments/run_experiment_suite_state.7005a27.tsv
```

**Its `.git/hooks/` contains only `*.sample` files** — `pre-commit` has never been installed there
[VERIFIED]. Nothing in this phase should commit from it. `cp -a` out, work in the working clone.

### The destination is empty and clean

In `/home/tlancaster/aquacal-frozen-rerun-freeze-01` (branch `results/rerun-freeze-02`,
`git status --porcelain` empty):

```
experiments/results:                0 files
experiments/results_e2_band:        0 files
experiments/results_e2_invocations: 0 files
experiments/results_e2_memory:      0 files
experiments/results_e2_timing:      0 files
experiments/results_e4_repeat:      0 files
experiments/run_experiment_suite_state.*  (absent)
```

[VERIFIED: `find … -type f | wc -l`, this session] — 29.1-06 moved attempt 1's output to
`experiments/freeze01_run_output/`, so the landing zone is clean.

### What the ignore rules actually admit — **227 files**

[VERIFIED: `git status --porcelain --untracked-files=all` in the prod clone, this session]

| Path | Admitted (non-ignored) | On disk | Ignored |
|---|---:|---:|---:|
| `experiments/results/` | **147** | 152 | 5 |
| `experiments/results_e2_invocations/` | 25 | 119 | 94 |
| `experiments/results_e2_band/` | 7 | 136 | 129 |
| `experiments/results_e4_repeat/` | 4 | 4 | 0 |
| `experiments/results_e2_timing/` | 3 | 6 | 3 |
| `experiments/results_e2_memory/` | 3 | 6 | 3 |
| `…stagelogs/` (18 `.log` + 18 `.done`) | 36 | 36 | 0 |
| `…7005a27.tsv` | 1 | 1 | 0 |
| `…7005a27.failures.txt` | 1 | 1 | 0 |
| **Total** | **227** | **461** | **234** |

**The 147 under `experiments/results/` matches attempt 1's 147 exactly.** D-29-17's anchor holds.

**Diffed against attempt 1's commit `83da9b3` (209 files), path for path with the sha normalised,
attempt 2's admitted set is a strict superset: identical 209 plus 18 files, all of them
`experiments/run_experiment_suite_state.<sha>.stagelogs/*.log`.** [VERIFIED: `comm` over the two
sorted path lists, this session — zero paths present in attempt 1 and absent now.]

Those 18 logs are admitted by `.gitignore:507`
`!experiments/run_experiment_suite_state.*.stagelogs/*.log`, added **deliberately in Phase 28** by
commit `f399615 chore(28): commit the production queue's 18 per-stage logs`, whose own comment
block reads *"18 files, 363 KB total, largest 50 KB (`e6_band.log`) — all far under
`check-added-large-files --maxkb=1000`."* [VERIFIED: `.gitignore:495-507` read this session; the
rule is absent from `git show 3ab9c13:.gitignore`.]

> **Planner note.** D-29-17's two clauses — *"commit what the existing ignore rules allow"* and
> *"match attempt 1's shape"* — now differ by exactly these 18 files. The ignore rule is the newer
> and deliberate authority, and D-29-17 also says **no ignore rule changes during this phase**, so
> the admitted set is **227**. Say the number in the commit message so the delta from attempt 1's
> 209 is not read later as a leak.

### `check-added-large-files` is not binding, and the cited file is already ignored

- Largest admitted file anywhere in the tree: `experiments/results/interface_ablation_band.csv`,
  **119,406 bytes (117 KB)**. **No admitted file exceeds 1000 KB.** [VERIFIED: `du -k` over the
  full 227-path set, this session]
- `all_observation_depths.csv` (11 MB) — the file D-29-17 names as the tripwire — lives at
  `experiments/results_e2_invocations/e2_classification/all_observation_depths.csv` and is
  **already ignored** by `.gitignore:478`
  `experiments/results_e2_invocations/*/all_observation_depths.csv` [VERIFIED:
  `git check-ignore -v`, this session]. The decision is unaffected; only its arithmetic needs the
  correction.
- The five ignored files under `experiments/results/` are `calibration.json` (2.1 MB),
  `exp2_spatial_errors.csv` (13 MB), `interface_ablation_conditioning.npz` (3.2 MB),
  `reconstruction_errors.csv` (620 KB), `reprojection_residuals.csv` (1.2 MB) [VERIFIED].

### The three non-formatting hooks PASS against the full staged set

```
check for added large files..............................................Passed
Detect secrets...........................................................Passed
check yaml...............................................................Passed
```

[VERIFIED: `pre-commit run <hook> --files <all 227>` in the probe clone, this session, using
`pre-commit 4.6.2`]

### The Byte-Integrity Hazard — the finding CONTEXT.md does not carry

**`end-of-file-fixer` would rewrite 143 of the 227 files and `trailing-whitespace` would rewrite 4
— up to 147 distinct files.** [VERIFIED: measured this session over the staged set]

This is the same defect `29.1-deferred-items.md` § D3 recorded against attempt 1's tree (143 / 5 /
148 there), and its diagnosis carries over verbatim: the run was produced in a clone with no hooks
installed, so its artifacts have never been through the formatting hooks, whereas
`experiments/pre_rerun_baseline/`'s 226 files give **0**.

> *"A whitespace-only rewrite does not change a measurement, but it does change bytes the gate
> reads and it destroys the 'byte-for-byte what the run produced' claim."*
> — `.planning/phases/29.1-post-run-fixes-re-freeze/deferred-items.md:132-136` [CITED]

**Why it is currently latent, and how to keep it that way:**

| Fact | Status |
|---|---|
| `/home/tlancaster/aquacal-frozen-rerun-freeze-01/.git/hooks/` | only `*.sample` — **`pre-commit install` has never been run** [VERIFIED] |
| `~/aquacal-frozen-rerun-freeze-02-prod/.git/hooks/` | only `*.sample` [VERIFIED] |
| `pre-commit` on `PATH` | not present; it lives inside the conda envs [VERIFIED] |
| CI `pre-commit run --all-files` | `.github/workflows/test.yml`, `on: push: branches: [main]` / `pull_request: branches: [main]` — **does not fire for `results/rerun-freeze-02`** [VERIFIED] |

**Prescriptions for the plan:**

1. Commit the results with **`git commit --no-verify`** — belt and braces, and free.
2. **Never run `pre-commit run --all-files`** during this phase. If a hook run is wanted, scope it:
   `pre-commit run <hook-id> --files <explicit list>`, and only the three non-formatting hooks.
3. **Do not run `pre-commit install`** in either clone.
4. **Do not open a PR from `results/rerun-freeze-02` into `main`** — that is the one action that
   would fire the rewrite in CI. Attempt 1's branch was never merged either; note it forward to
   Phase 30 rather than solving it here.
5. Record the pre- and post-commit `sha256` (or `md5`) of a sample of the artifacts, or simply
   re-run the gate after committing and confirm `176/7/0` again — a rewrite would not change the
   totals, so prefer a hash check on `real_rig_metrics.json` and `interface_ablation_band.csv`
   against the values in this document.

### Traceability under D-29-19 — the three fragments exist

```
experiments/results/benchmark_grid.tex        10,438 B
experiments/results/cpr_derived_values.tex       131 B
experiments/results/cpr_grouping.tex             938 B
```

[VERIFIED: `ls -la` over the prod clone, this session] All three are inside the 147 admitted files
under `experiments/results/`, so committing the admitted set discharges D-29-19's mechanism by
construction. `gate3_git_sha_consistency` supplies the single-sha proof.

### The archive is the record for the 234 files git will not hold

| Artifact | Bytes | Mode | sha256 |
|---|---:|---|---|
| `/home/tlancaster/rerun-freeze-02-output.tar.gz` | 31,838,334 | `r--r--r--` | `3b21b88323bd7c04e9712ae2742cc09d423f925620e729ea7bbe2d391c9f030e` |
| `/home/tlancaster/suite_run_freeze02.log.preserved` | 430,438 | `r--r--r--` | `5bdc6090df5741c86c225a1a14a4eee05f344a71f5d39ade7e50bd9dcf46915e` |

[VERIFIED: `ls -la` and
`.planning/phases/28-full-suite-production-run/rerun-freeze-02-output.sha256`, this session]

**461 reconciles exactly:** 423 files across the six output trees + 38 state artifacts (18 `.log`
+ 18 `.done` + `.tsv` + `.failures.txt`) = 461 [VERIFIED: `find … -type f | wc -l`, this session],
agreeing with `28-RUN-RECORD.md` § *The nine paths in the archive*.

---

## Zenodo REST API (RUN-05)

### Which API surface is live

Zenodo's own developer documentation at **`https://developers.zenodo.org/`** documents the
Deposit / Records / Files APIs and carries **no deprecation notice** for the deposit API
[VERIFIED: fetched 2026-08-26]. Zenodo did migrate its backend to InvenioRDM, and InvenioRDM's
native draft API (`/api/records/{id}/draft`) exists alongside; community reporting says the legacy
deposit API *"remains functional"* but that *"new integrations should not rely on the feature being
available in the future"* [ASSUMED — community sources, not an official Zenodo statement].

**Recommendation: use the legacy deposit API.** It is what Zenodo documents, what its own
maintainer's reference upload gist uses, and what D-29-07 already specifies. It is also the API
whose bucket semantics are stable — the InvenioRDM `PUT /api/records/{id}/draft` replaces the whole
draft resource including metadata, which is a sharper edge for a two-record link job. Note the
deprecation posture in the phase record as a Phase-30+ follow-up; do not rebuild on it now.

### Base URLs and the sandbox

| | Production | Sandbox |
|---|---|---|
| API base | `https://zenodo.org/api/` | `https://sandbox.zenodo.org/api/` |
| DOI prefix | `10.5281` | `10.5072` (test DOIs) |
| Account / token | production account | **separate registration, separate token** |

[VERIFIED: developers.zenodo.org, fetched this session]

**For the D-29-06 rehearsal:** the sandbox differs only in host, account and DOI prefix as far as
the documented API is concerned. **Rehearse with a small dummy file, not the 4.35 GB payload** —
the rehearsal's purpose (D-29-06) is *"confirm both drafts render correctly in the UI"*, which is a
metadata-and-linkage question, and sandbox large-file uploads have a documented history of failing
where production does not [ASSUMED — zenodo/zenodo issue #833 *"Fail to upload larger file via API
to sandbox"*]. Do the shape rehearsal on sandbox; do the size on production.

### Token scopes

| Scope | Official description | Needed for |
|---|---|---|
| `deposit:write` | *"Grants write access to depositions, but does not allow publishing the upload."* | Create draft, PUT files, PUT metadata. **This is all Phase 29's tooling needs.** |
| `deposit:actions` | *"Grants access to publish, edit and discard edits for depositions."* | Publish / discard. **Under D-29-01 the author publishes in the web UI — so the automation token should deliberately NOT carry this scope.** |

[VERIFIED: developers.zenodo.org § REST API / OAuth scopes, fetched this session]

> **Prescription:** mint the automation token with `deposit:write` **only**. That makes D-29-01's
> "no accidental publish" property enforced by the credential, not just by the code. It also makes
> a `discard` impossible, so pair it with recording the draft `id` and `links.html` in the phase
> record.

Authentication: `Authorization: Bearer <ACCESS_TOKEN>` header (recommended) or `?access_token=`
query parameter. Rate limits for authenticated users: **100 requests/minute, 5,000/hour**;
`X-RateLimit-Limit` / `-Remaining` / `-Reset` headers report status. [VERIFIED]

### Creating an unpublished draft — and the D-29-01 premise, verified

```http
POST https://zenodo.org/api/deposit/depositions
Authorization: Bearer $ZENODO_TOKEN
Content-Type: application/json

{}
```

`201 Created` returns `id`, `links.bucket`, `links.publish`, and — *only if requested* —
`metadata.prereserve_doi.doi`, which the documentation states is **"not registered with DataCite
until you publish your deposition"**. [VERIFIED: developers.zenodo.org, fetched this session]

**D-29-01's premise holds: a draft exists with files and metadata, and no DOI is registered until
Publish.** D-29-03 (do not reserve) is satisfied simply by not asking for `prereserve_doi`.

### The bucket / files API — the large-file path

Quoted from the Zenodo docs [VERIFIED]:

> *"We have recently released a new API, which is significantly more performant and supports much
> larger file sizes. The current API supports 100MB per file, the new one has a limit of 50GB total
> in the record (and any given file), and up to 100 files in the record."*

```bash
curl --upload-file /path/to/your/file.dat \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  https://zenodo.org/api/files/568377dd-daf8-4235-85e1-a56011ad454b/file.dat
```

The bucket UUID URL comes straight from the draft's `links.bucket`. `200 OK` returns:

```json
{
  "key": "filename.zip",
  "mimetype": "application/zip",
  "checksum": "md5:2942bfabb3d05332b66eb128e0842cff",
  "size": 13264,
  "version_id": "38a724d3-40f1-4b27-b236-ed2e43200f85",
  "created": "...", "updated": "...", "links": { ... }
}
```

**Quota answers for this phase:** 4.35 GB is well inside both the per-file and per-record 50 GB
limits; the record will hold **1** file, not near the 100-file cap. The default per-record quota is
**50 GB**, with *"an additional allowance of up to 150GB that can be distributed across your
uploads as needed"* [VERIFIED: `help.zenodo.org/docs/deposit/manage-quota/`, fetched this session].
**No quota-increase request is needed.**

### The sanctioned streaming-PUT shape

From the reference gist by Zenodo maintainer `slint` [CITED:
gist.github.com/slint/92e4d38eb49dd177f46b02e1fe9761e1]:

```python
res = requests.post(url, json={}, params=params)      # create draft
bucket_url = res.json()["links"]["bucket"]

with open('/path/to/my-file.zip', 'rb') as fp:
    res = requests.put(bucket_url + '/my-file.zip', data=fp, params=params)
```

Note *"No headers included in the request, since it's a raw byte request"* — passing an open file
object to `data=` makes `requests` stream it and set `Content-Length` from the file's size. Do
**not** pass a generator (that switches to chunked transfer encoding and has been reported to
behave worse against Zenodo).

### Failure modes for a multi-hour 4.35 GB PUT, and what makes a plain retry reliable

D-29-07 forbids resume machinery. The following make a plain streaming PUT with retry reliable:

| Failure mode | Evidence | Mitigation inside the sanctioned shape |
|---|---|---|
| `504 Gateway Time-out` on the PUT or on publish | zenodo/zenodo issues #2442, #2131 [CITED] | Set an explicit, generous `timeout` — one reporter raised theirs from 250 s to 1 hour. Use `timeout=(connect, read)` with a large read timeout; **never leave `timeout=None`** (a hung socket then blocks forever). |
| Connection reset / abort mid-upload, "randomly between 10% and 99%" | zenodo/zenodo issues #2328, #2514 [CITED] | The **retry loop must reopen the file and restart from byte 0** — a `requests` retry on a consumed file object silently uploads nothing. `download.py`'s existing loop already reopens per attempt; mirror that structure. |
| Rate limiting | 100 req/min authenticated [VERIFIED] | Irrelevant for one PUT; matters only if the tooling polls. Do not poll in a tight loop. |
| Silent truncation | — | **Verify the round trip on every attempt**: compute the local `md5` and compare to the response's `checksum` field, which is literally `"md5:<hex>"`. Treat a mismatch as a failed attempt and retry. |

**`src/aquacal/datasets/download.py` is the right model to mirror** [VERIFIED: read in full this
session]: `for attempt in range(max_retries)` with `2**attempt` exponential backoff (1 s, 2 s,
4 s), a `.tmp` staging path, explicit `algorithm:hash` checksum parsing that already understands
`md5:` and `sha256:` prefixes, a `tqdm` progress bar, and `raise RuntimeError(f"… after
{max_retries} attempts")` on exhaustion. Its checksum-format convention is **the same one Zenodo
returns**, which makes the verification symmetric.

**Practical additions for an hours-long transfer:** wrap the file object so the `tqdm` bar advances
on read (otherwise there is no progress signal for hours); run the upload under `nohup`/`tmux` so a
dropped SSH session does not kill it; and log the response JSON (`key`, `size`, `checksum`,
`version_id`) to the phase evidence set — that JSON *is* the round-trip proof.

### Metadata schema for D-29-02

**Required:** `upload_type` (controlled vocabulary; `dataset` for both records), `title`,
`description` (a limited HTML subset is allowed), `creators` (array of `{name, affiliation, orcid}`),
`publication_date` (`YYYY-MM-DD`), `access_right` (`open`), `license` (required when
`access_right` is `open`). **Optional and needed here:** `version`, `related_identifiers`.
[VERIFIED: developers.zenodo.org, fetched this session]

Metadata is set either in the creating `POST` body (`{"metadata": {…}}`) or by a subsequent
`PUT /api/deposit/depositions/{id}` with the full metadata block.

**`related_identifiers` — the full allowed `relation` vocabulary** [VERIFIED]:

```
isCitedBy, cites, isSupplementTo, isSupplementedBy, isContinuedBy, continues,
isDescribedBy, describes, hasMetadata, isMetadataFor, isNewVersionOf,
isPreviousVersionOf, isPartOf, hasPart, isReferencedBy, references,
isDocumentedBy, documents, isCompiledBy, compiles, isVariantFormOf,
isOriginalFormOf, isIdenticalTo, isAlternateIdentifier, isReviewedBy, reviews,
isDerivedFrom, isSourceOf, requires, isRequiredBy, isObsoletedBy, obsoletes
```

**Recommended A↔B linkage** (Claude's discretion; the planner should present it for author
confirmation because the semantics are a publication-facing choice):

| On record | `relation` | points at | reads as |
|---|---|---|---|
| **B (results)** | `isDerivedFrom` | Record A's DOI | the results were computed from those inputs |
| **B (results)** | `isSupplementTo` | the paper's DOI, when it exists | the standard Zenodo idiom for "supports this article" |
| **A (inputs)** | `isSourceOf` | Record B's DOI | the exact inverse of `isDerivedFrom` |
| **Both** | `isNewVersionOf` **NOT used** | — | Do **not** use `isNewVersionOf` against `21889922`. Zenodo's versioning is a first-class mechanism (`newversion` action); asserting it in `related_identifiers` on a *different concept record* misrepresents the relationship. Prefer `isDerivedFrom` / `references` and an explicit supersession sentence in the description, which the folded todo already requires. |

**Chicken-and-egg:** under D-29-03 no DOI exists until Publish, so **A and B cannot carry each
other's DOI in the drafts the author reviews.** Options for the planner, in preference order:
(a) upload A, have the author publish A alone, then build B's draft with A's minted DOI — this
respects D-29-05 (B is built after grading) and is the only ordering that yields real identifiers;
(b) put the linkage in prose in both descriptions and add the `related_identifiers` after Publish
via a Zenodo "edit" (which needs `deposit:actions`); (c) reserve DOIs — **excluded by D-29-03**.
**Flag (a) vs (b) to the author; do not choose it silently.** Option (a) also matches the folded
todo's *"Record B uploads after the run is verified"*.

### The publish action — automation must NOT call it

```http
POST /api/deposit/depositions/{id}/actions/publish
```

`202 Accepted`, returns the deposition with `record_id` and `doi_url` populated. [VERIFIED]
**Under D-29-01 this call is the author's, made from the Zenodo web UI. The tooling must not
implement it**, and the `deposit:write`-only token makes that structural.

---

## The A/B Split Payloads — measured, and the source is on this machine

The full published archive is present locally, both as the zip and extracted:

```
aquacal_data/downloads/real-rig-calib.zip     4,350,418,046 B   (matches manifest.json size_bytes exactly)
aquacal_data/real-rig/real-rig/               8.2 GB total cache, 3,977 files extracted
```

[VERIFIED: `ls -la` / `du`, this session. Note `aquacal_data/.gitignore` contains `*`, so the whole
cache is ignored by git.]

Composition:

| Sub-tree | Size | Contents | Belongs to |
|---|---:|---|---|
| `extrinsic/` | **3.6 GB** | 13 camera directories | **Record A** (the todo names these explicitly) |
| `intrinsic/` | **518 MB** | 13 camera directories | **Record A** — *but the todo says "Record A — inputs. The extrinsic frames." Flag: `intrinsic/` is also an input and is not named. Confirm with the author.* |
| `reference_calibration.json` | 2.2 MB | — | **Unassigned by the todo.** It is a calibration *result* used as a comparison target and is read by `src/aquacal/datasets/loader.py:79-86`. Arguably Record B. **Flag.** |
| `reference_outputs/` | 19 MB, 6 files | `calibration.json`, `diagnostics.json`, `exp2_spatial_errors.csv`, `interface_ablation_conditioning.npz`, `reconstruction_errors.csv`, `reprojection_residuals.csv` | **Record B**, and **replaced** with this run's own copies |
| `config_paper.yaml` | 4 KB | — | **Record B** (explicit author decision in the todo) |
| `config_quickstart_not_paper.yaml`, `README.md` | 8 KB | — | Unassigned. **Flag.** |

**Consequence for the plan:** Record A's zip must be **built**, not reused — the published
`real-rig-calib.zip` bundles inputs *and* outputs, which is the defect being fixed. The build is
`zip` over `extrinsic/` (+ whatever else the author assigns) from the extracted cache, followed by
an `md5sum` that becomes the round-trip target and, later, `manifest.json`'s `checksum`. Budget
disk for a second multi-GB zip alongside the existing 4.35 GB one.

**All six `reference_outputs/` filenames exist in this run's output**, five of them gitignored:
`calibration.json`, `exp2_spatial_errors.csv`, `interface_ablation_conditioning.npz`,
`reconstruction_errors.csv`, `reprojection_residuals.csv` are the five ignored files under
`experiments/results/` [VERIFIED], and `diagnostics.json` is written per-run. **Record B is exactly
the payload the git ignore rules exclude**, which is the design working as intended (D-29-17: *"the
gitignored bulk … in the archive and Zenodo Record B"*).

---

## `_manifest.py` Blast Radius — scope, do not decide (deferred item)

### What is pinned, exactly

`src/aquacal/datasets/_manifest.py` contains **no record id**. It is a thin loader
(`get_manifest`, `get_dataset_info`, `list_datasets`) over package data
[VERIFIED: read in full this session]. The pin lives in
**`src/aquacal/datasets/data/manifest.json`** [VERIFIED, read in full this session]:

```json
{
  "version": "1.0",
  "datasets": {
    "real-rig": {
      "type": "real",
      "included": false,
      "zenodo_record_id": 21889922,
      "zenodo_filename": "real-rig-calib.zip",
      "checksum": "md5:dff1012fb772d627e0f3f106d5c6de84",
      "size_bytes": 4350418046,
      "description": "13-camera production rig (12 primary + 1 auxiliary fisheye) — download from Zenodo"
    }
  }
}
```

`download.py:151-162` reads exactly `zenodo_record_id`, `zenodo_filename`, `checksum` and builds
**one** URL: `f"https://zenodo.org/records/{record_id}/files/{filename}"`
[VERIFIED: `src/aquacal/datasets/download.py:145-180`].

### What breaks if the record is split

| Site | What breaks | Where it lives |
|---|---|---|
| `manifest.json` | Describes **one** file. A two-record split needs either two entries and a compose step in `download_and_extract`, or an explicit decision to leave the pin on `21889922`. | `src/` — **shipped library**, and `package-data` in `pyproject.toml:83-87` |
| `download.py:126-180` | Downloads and extracts **one** zip into `aquacal_data/<name>/`. Two records means two downloads merged into one cache layout. | `src/` |
| `loader.py:49-58` | Docstring asserting `reference_outputs/` ships in "the `'real-rig'` archive". Also resolves `reference_calibration.json` and looks for **`config.yaml`** (not `config_paper.yaml`) at `loader.py:90` — a latent mismatch worth noting. | `src/` |
| `reconstruction_bootstrap.py:57, 181, 226, 365` | Hard-codes the relative path `"reference_outputs/reconstruction_errors.csv"` and its prose. Moving `reference_outputs/` to Record B breaks the resolution. | **inside the frozen tree** |
| `e2_real_rig.py:635, 1231, 1233` | Help text and the no-`--config` "reader's default" path naming record `21889922` and the 4.35 GB bundle. | **inside the frozen tree** |
| `experiments/suite_expectations.json:1641` | `"verified": "2026-08-12, against Zenodo record 21889922 (4.35 GB) …"` | **inside the frozen tree** |
| `experiments/FROZEN-ROWS.md:145, 263` | Names record `21889922` as the source of `reconstruction_errors.csv`. | **inside the frozen tree** |
| `tests/unit/test_datasets.py:577` | `assert datasets["real-rig"]["zenodo_record_id"] == 21889922` — **hard-coded equality**. | `tests/` |
| `tests/unit/test_stale_provenance_strings.py:120, 176` | Asserts the literal token `"21889922"` is present (`for token in ("21889922", "18645385", "262 usable frames", "7762")`, and `assert "21889922" in header`). | `tests/` |
| `.gitignore:226, 454` | Comment prose naming record `21889922`. | root |

[VERIFIED: `grep -rn "21889922"` repo-wide and `grep -rln` for the loader consumers, this session]

### Recommendation to the planner (scope only — the ruling is the author's)

**Four of the ten sites are inside the frozen `experiments/` tree.** Repointing them changes source
files at the tag the run was made from, which is a materially different act from committing that
run's output. Combined with D-29-08's spirit and the fact that **nothing in Phase 29 needs the pin
to move** — the split's drafts are unpublished and have no DOIs until the author acts —
**the manifest repoint reads as Phase 30 / POST-01 work.** The `deferred` block already flags it;
the plan should carry it forward as an explicit, named todo with this table attached rather than
attempting it. If the author disagrees, the two `tests/` assertions are the first things to change
and are the cheap half.

---

## Don't Hand-Roll

| Problem | Don't build | Use instead | Why |
|---|---|---|---|
| Streaming a 4.35 GB upload | A chunked generator, a resumable multipart client, an S3 multipart shim | `requests.put(bucket_url + "/" + name, data=open(path, "rb"), headers={"Authorization": ...}, timeout=(30, 3600))` | D-29-07 explicitly rules out resume machinery. A file object gives `requests` a real `Content-Length`; a generator forces chunked transfer, which is the shape multiple Zenodo issue reports blame for aborted uploads. |
| Retry with backoff + checksum verification | A new loop | Mirror `src/aquacal/datasets/download.py:52-124` | Already in-repo, already the project's idiom, already parses the exact `md5:<hex>` format Zenodo returns. Reopen the file per attempt — the existing loop's structure does this correctly. |
| Grading the returned tree | A new gate, a new completeness check | `python experiments/check_rerun_gates.py experiments/results --profile full` | D-29-11 and `29-CONTEXT.md` § Reusable Assets: grading needs no new gate, it re-invokes this one. Editing it is forbidden (D-29-08 / canonical refs). |
| The E7 sign test | A new statistic, `scipy.stats.binomtest`, a two-sided p | The exact recipe in `analyze_e7_spread.py` (one-tailed `sum(comb(n,k) for k in range(n_pos, n+1)) / 2**n`) applied to `interface_ablation_band.csv` | It reproduces the published 0.00098 exactly. A two-sided p or a different metric silently answers a different question — the module's own docstring records that one/two-sided was conflated once already. |
| The E2 control | A tolerance sweep, a new rail | A direct field-by-field relative comparison of two `real_rig_metrics.json` files at seed 42 | Already done in this document; the plan reproduces it into an evidence file. |
| Secret storage for the Zenodo token | A dotenv file, a config entry, a keyring | `os.environ["ZENODO_TOKEN"]` / `ZENODO_SANDBOX_TOKEN`, exported in the shell only | D-29-07. `detect-secrets` runs against a baseline and a committed token is unrecoverable once pushed. |

---

## Common Pitfalls

### Pitfall 1: Grading a partial tree

**What goes wrong:** `check_e2_band` silently degrades because `out_dir.parent / "results_e2_band"`
is absent, and the roll-up total drops below 176 without an obvious cause.
**Why:** the gate resolves E2's band as a **sibling** of `out_dir`, not a child
[VERIFIED: `check_rerun_gates.py:2262`].
**Avoid:** copy all six output trees together, at their original relative paths, before grading.
**Warning sign:** a `TOTAL:` that is not `176 PASS, 7 N/A, 0 FAIL`.

### Pitfall 2: Running the E2 control across seeds

**What goes wrong:** a healthy run looks catastrophically broken — `mean_per_camera_reprojection_px`
spans 0.761 → 0.910 px across E2's seed band, four orders of magnitude worse than the 1e-8 the
criterion asks for.
**Avoid:** compare seed 42 to seed 42 only, and **print the seed in the control's own output** so
the comparison cannot be misread later. `29-CONTEXT.md` criterion 2 makes this an explicit
instruction.

### Pitfall 3: Letting the formatting hooks touch the artifacts

**What goes wrong:** 147 of the 227 committed files get whitespace-normalised, destroying the
byte-for-byte claim `29.1-GATE-BEFORE-AFTER.md` asserts.
**Why:** the run was produced in a hooks-free clone; 143 of its files have no trailing newline.
**Avoid:** `git commit --no-verify`; never `pre-commit run --all-files`; never `pre-commit install`;
no PR into `main` from this branch.
**Warning sign:** `git diff` showing single-character changes at end of file across dozens of
artifacts.

### Pitfall 4: Reading the D1 count before the tree is populated

**What goes wrong:** `pytest tests/unit/test_experiments_provenance.py` reports `300 passed` and
someone records "the rails are green".
**Why:** `resolve_results_dir()` falls back to `experiments/pre_rerun_baseline/results/` while the
live tree is empty, so the module changes subject rather than validating nothing
[VERIFIED: `_baseline_paths.py` docstring and code].
**Avoid:** run the rails **after** copying the tree in, and confirm the skip reason names `live`,
not `archive`. `TestResolvedTreeIsObservable::test_the_resolved_tree_is_named` exists for this.

### Pitfall 5: Assuming the CSV and JSON discovery helpers behave the same

**What goes wrong:** a gitignored 2.1 MB `calibration.json` reaches a rail whose stated scope is
"committed under `experiments/results/`", producing failure #8.
**Why:** `_discover_csv_files()` filters through `_is_tracked()`; `_discover_json_files()` does not
[VERIFIED: `test_experiments_provenance.py:322-360`].
**Avoid:** fix the asymmetry as part of the D-29-13 repairs; do not paper over it by adding
`calibration.json` to `SELF_DESCRIBING_JSON` (it is not committed, so it has no business in a
committed-artifact carve-out).

### Pitfall 6: Publishing before the author does

**What goes wrong:** an irreversible DOI is minted by automation, contradicting `PROJECT.md`'s
locked decision and D-29-01.
**Avoid:** mint the automation token with `deposit:write` **only** — publishing then fails at the
credential, not at a code review. Do not implement the publish endpoint at all.

### Pitfall 7: Rehearsing 4.35 GB on the sandbox

**What goes wrong:** hours burned on an instance with a documented history of large-upload failures
[ASSUMED — zenodo/zenodo #833], for a rehearsal whose purpose is metadata/linkage shape.
**Avoid:** sandbox rehearsal with a small dummy file; production for the real payload.

---

## Code Examples

### Grading invocation (the exact command, reproduced this session)

```bash
# Source: experiments/check_rerun_gates.py:2276-2331 (VERIFIED)
python experiments/check_rerun_gates.py experiments/results --profile full \
  > .planning/phases/29-gate-verification-results-commit/29-gates-full.txt
# expect: TOTAL: 176 PASS, 7 N/A, 0 FAIL   and   0 lines matching '^\[FAIL'
```

### The E2 same-seed control

```python
# Source: measured this session; both files read directly.
import json

BEFORE = "experiments/pre_rerun_baseline/results/real_rig_metrics.json"
AFTER  = "experiments/results/real_rig_metrics.json"
SEED   = 42  # printed in the output; the band spans 0.761->0.910 px across seeds

a = json.load(open(BEFORE))
b = json.load(open(AFTER))
for k in sorted(set(a) | set(b)):
    if k == "provenance":
        continue
    va, vb = a.get(k), b.get(k)
    if isinstance(va, (int, float)) and isinstance(vb, (int, float)):
        rel = abs(vb - va) / abs(va) if va else float("nan")
        print(f"seed {SEED} vs seed {SEED}  {k:36s} {va!r:>24} -> {vb!r:>24}  rel={rel:.3e}")
```

### The E7 before/after sign test

```python
# Source: recipe transcribed from
# .planning/phases/19.2-experiment-execution-and-provenance/analyze_e7_spread.py
# (VERIFIED: it reproduces the published 10/10, p = 0.00098 on the baseline tree).
# Do NOT run that script directly: its ROOT is a hard-coded Windows sweep path.
import pandas as pd
from math import comb

METRIC = "camera_height_drift_mm"
PAIRS = [("shared_fixed", "percamera_fixed"), ("shared_refined", "percamera_refined")]

def sign_test(band_csv):
    df = pd.read_csv(band_csv)                       # interface_ablation_band.csv
    per = (df.assign(a=df[METRIC].abs())
             .groupby(["arm", "seed"])["a"].mean().unstack("seed"))
    n = len(per.columns)
    for shared, percam in PAIRS:
        diff = per.loc[percam] - per.loc[shared]     # > 0 means shared is better
        n_pos = int((diff > 0).sum())
        crosses = bool(diff.min() < 0 < diff.max())
        p_one = sum(comb(n, k) for k in range(n_pos, n + 1)) / 2 ** n
        r = per.loc[shared].corr(per.loc[percam])
        yield shared, percam, n_pos, n, crosses, p_one, r
```

### Zenodo draft + bucket upload (the sanctioned shape)

```python
# Source: developers.zenodo.org (VERIFIED) + gist.github.com/slint/92e4d38eb49dd177f46b02e1fe9761e1 (CITED)
# Modelled on src/aquacal/datasets/download.py's retry/checksum structure (VERIFIED, in-repo).
import hashlib, os, time
import requests

BASE = "https://zenodo.org/api"            # sandbox: https://sandbox.zenodo.org/api
TOKEN = os.environ["ZENODO_TOKEN"]         # deposit:write ONLY -- publish stays manual (D-29-01)
HEADERS = {"Authorization": f"Bearer {TOKEN}"}

def create_draft(metadata: dict) -> dict:
    r = requests.post(f"{BASE}/deposit/depositions",
                      json={"metadata": metadata}, headers=HEADERS, timeout=(30, 120))
    r.raise_for_status()
    return r.json()                        # -> id, links.bucket, links.publish, links.html

def _md5(path, block=1 << 20):
    h = hashlib.md5()
    with open(path, "rb") as fp:
        for chunk in iter(lambda: fp.read(block), b""):
            h.update(chunk)
    return h.hexdigest()

def put_file(bucket_url: str, path: str, name: str, max_retries: int = 5) -> dict:
    expected = _md5(path)
    for attempt in range(max_retries):
        try:
            with open(path, "rb") as fp:   # reopened every attempt -- a consumed
                r = requests.put(          # file object uploads zero bytes on retry
                    f"{bucket_url}/{name}", data=fp, headers=HEADERS,
                    timeout=(30, 3600),    # never timeout=None; 504s are documented
                )
            r.raise_for_status()
            body = r.json()
            if body["checksum"] != f"md5:{expected}":
                raise RuntimeError(f"round-trip mismatch: {body['checksum']} != md5:{expected}")
            return body                    # key, size, checksum, version_id -> evidence file
        except (requests.RequestException, RuntimeError) as e:
            if attempt == max_retries - 1:
                raise RuntimeError(f"upload failed after {max_retries} attempts: {e}")
            time.sleep(2 ** attempt)

# NO publish() function. POST /deposit/depositions/{id}/actions/publish is the
# author's action in the web UI (D-29-01), and the deposit:write-only token
# makes that structural rather than a matter of code review.
```

---

## Runtime State Inventory

Phase 29 is not a rename or refactor, but it *does* move state across machines and into an external
service, so the same discipline applies.

| Category | Items found | Action required |
|---|---|---|
| **Stored data** | None in a datastore. The run output is 461 files on the filesystem of `~/aquacal-frozen-rerun-freeze-02-prod` (untracked) plus the read-only tarball `~/rerun-freeze-02-output.tar.gz` (sha256 `3b21b88…`). — verified by `git status --porcelain --untracked-files=all` and `ls -la`. | Copy (never move) 227 admitted files into the working clone; leave prod clone byte-identical. |
| **Live service config** | **Zenodo.** Record `21889922` (version DOI `10.5281/zenodo.21889922`, concept DOI `10.5281/zenodo.18645384`) is live and referenced by the manuscript. Two new drafts will exist as service-side state with no repo representation until their DOIs are minted. | Record draft `id` and `links.html` for both records in the phase evidence set — otherwise the drafts are unfindable from the repo. |
| **OS-registered state** | **None.** No systemd unit, cron entry, pm2 process or scheduled task references this run — verified: the only OS-level residue is the driver's own state files (`run_experiment_suite_state.7005a27.*`), which are ordinary files and are in the admitted commit set. | None. |
| **Secrets / env vars** | `ZENODO_TOKEN` and `ZENODO_SANDBOX_TOKEN` **do not currently exist** in the environment — verified (`env | grep -i zenodo` returns nothing). Both must be minted by the author on two separate Zenodo accounts. | Author action, gated. `detect-secrets` baseline is `.secrets.baseline`; the token must never reach a file. |
| **Build artifacts / installed packages** | Four conda envs exist: `aquacal-freeze01` (2.0.1), `aquacal-freeze02-prod` (editable from the prod clone), `aquacal-freeze02-clone`, `aquacal-freeze02-cleanenv` (editable from the working clone `-01`). — verified by importing `aquacal` in each. Nothing is stale for this phase; **use `aquacal-freeze02-cleanenv` for work in the working clone**, and do not `pip install` into `aquacal-freeze02-prod`. | None, beyond choosing the right interpreter. |

---

## Environment Availability

| Dependency | Required by | Available | Version | Fallback |
|---|---|---|---|---|
| Python (conda `aquacal-freeze02-cleanenv`) | everything | ✓ | 3.11 / aquacal 2.0.1, editable from `-01` | `aquacal-freeze01` (also 2.0.1) |
| `pytest` | D1/D4 rail measurement | ✓ | 9.1.1 | — |
| `pandas` | E7 sign test, band CSVs | ✓ | 3.0.5 | — |
| `requests` | Zenodo upload | ✓ | 2.34.2 — **already a runtime dependency** (`pyproject.toml:44`) | — |
| `tqdm` | upload progress | ✓ | 4.70.0 — **already a runtime dependency** (`pyproject.toml:45`) | — |
| `pre-commit` | scoped hook checks only | ✓ | 4.6.2, inside the conda envs; **not on `PATH`** | — |
| `zip` / `tar` | building Record A's archive | ✓ (`tar` proven by the Phase 28 archive) | — | Python `zipfile` |
| Source archive (4.35 GB) | Record A/B split | ✓ | `aquacal_data/downloads/real-rig-calib.zip`, 4,350,418,046 B, plus the 8.2 GB extracted cache | Re-download from `21889922` (hours) |
| Free disk | second multi-GB zip | ✓ | 640 GB free on `/` | — |
| `ZENODO_TOKEN` | Record A/B upload | ✗ | — | **BLOCKING — author must mint (`deposit:write` scope) and export** |
| `ZENODO_SANDBOX_TOKEN` | D-29-06 rehearsal | ✗ | — | **BLOCKING for the rehearsal — separate sandbox account required** |
| Network to `zenodo.org` | upload | untested | — | The fallback in the folded todo: leave `21889922` untouched and publish only Record B |

**Missing dependencies with no fallback:**
- `ZENODO_TOKEN` and `ZENODO_SANDBOX_TOKEN`. Both require a human at a browser. **The plan must
  open with a `checkpoint:human-verify` task for token creation**, because D-29-04 makes Record A's
  upload the critical path and every hour of token delay is an hour of transfer not started.

**Missing dependencies with fallback:**
- None else.

---

## Validation Architecture

`workflow.nyquist_validation` is absent from `.planning/config.json` [VERIFIED: read this session],
so it is treated as enabled.

### Test Framework

| Property | Value |
|---|---|
| Framework | pytest 9.1.1 |
| Config file | `pyproject.toml` `[tool.pytest.ini_options]` (markers only: `slow`) |
| Quick run command | `python -m pytest tests/unit/test_experiments_provenance.py -q` (~23 s) |
| Full suite command | `python -m pytest tests/` (~28 min on this box) |
| Interpreter | `~/anaconda3/envs/aquacal-freeze02-cleanenv/bin/python` in the working clone |

### Phase Requirements → Test Map

| Req | Behaviour | Test type | Automated command | Exists? |
|---|---|---|---|---|
| RUN-03 | Gate passes over the complete returned tree at `--profile full` | integration (script) | `python experiments/check_rerun_gates.py experiments/results --profile full` → `TOTAL: 176 PASS, 7 N/A, 0 FAIL`, zero `^\[FAIL` | ✅ exists, **verified reproducing this session** |
| RUN-03 | `gate3_git_sha_consistency` holds on the committed tree | integration (script) | same command; grep `gate3_git_sha_consistency.*PASS` | ✅ |
| RUN-03 | Provenance rails are green after the D-29-13 repairs | unit | `python -m pytest tests/unit/test_experiments_provenance.py -q` → **`0 failed`** (baseline today: 8 failed) | ✅ module exists; assertions need repair |
| RUN-03 | No new failures elsewhere from repopulation | unit | `python -m pytest tests/unit/test_baseline_paths.py tests/unit/test_expectations.py tests/unit/test_experiments_e3.py tests/unit/test_experiments_e5.py tests/unit/test_experiments_io.py -q` → `245 passed` | ✅ **verified this session** |
| RUN-03 | Full suite lands at the ruled count | unit (slow) | `python -m pytest tests/` → **`3 failed`** (D4 only) after repairs; `11 failed` before | ✅ |
| ROADMAP c2 | E2 same-seed control, seed 42 vs seed 42, ~1e-8 | analysis + evidence file | a `29-e2-control.txt` produced by the snippet above; assert max relative drift `< 1e-6` and print the seed | ❌ **Wave 0 — no script exists** |
| ROADMAP c3 | E7 before/after sign test on both pairings | analysis + evidence file | a `29-e7-before-after.txt` from the recipe above, run against `pre_rerun_baseline/` and the committed tree | ❌ **Wave 0 — no runnable script exists** (`analyze_e7_spread.py` has a Windows-only hard-coded `ROOT`) |
| RUN-04 | 227 files committed, admitted set exactly | integration (git) | `git show --name-only --format="" <sha> \| wc -l` → `227`; `git show --name-only --format="" <sha> \| grep -c '^experiments/results/'` → `147` | ❌ **Wave 0 — assertion is a plan verification step, not a test** |
| RUN-04 | Artifacts unmodified by the commit | integration (hash) | `md5sum experiments/results/real_rig_metrics.json` → `57279708f6106f411d1fe03ed2698291`; `…/interface_ablation_band.csv` → `b6515ed77ed04268608b74217716020b` | ✅ baseline hashes recorded in this document |
| RUN-05 | Upload round-trips | integration (API) | response `checksum` equals `md5:` + locally computed md5, for each record | ❌ **Wave 0 — tooling does not exist** |
| RUN-05 | Both drafts render correctly | manual | author opens both drafts in the Zenodo UI (D-29-01, D-29-06) | manual-only by decision — **not automatable, and deliberately so** |

### Sampling rate

- **Per task commit:** `python -m pytest tests/unit/test_experiments_provenance.py -q` (23 s) — the
  only module the phase's changes can move.
- **Per wave merge:** the five tree-keyed modules above (~54 s combined).
- **Phase gate:** full `pytest tests/` once, expecting **exactly 3 failures** (D4, ruled). Plus a
  final gate re-run over the committed tree at `176/7/0`.

### Wave 0 gaps

- [ ] An E2 same-seed control script + `29-e2-control.txt` evidence file — covers ROADMAP c2 /
      D-29-10 stop-list item 1. Must print the seed.
- [ ] An E7 before/after script + `29-e7-before-after.txt` evidence file — covers ROADMAP c3 /
      D-29-16. Must report **both** pairings, both trees.
- [ ] Zenodo tooling (`scripts/zenodo_*.py`) with the draft/upload/verify surface — covers RUN-05.
      Suggested home: `scripts/`, alongside the existing `scripts/extract_frames.py`.
      **`scripts/` is not packaged** (`[tool.setuptools.packages.find] where = ["src"]`
      [VERIFIED: `pyproject.toml:80-82`]), so nothing there ships to PyPI or touches the frozen
      `experiments/` tree — the cleanest home for one-off operational tooling.
- [ ] No new framework install needed.

---

## Security Domain

`security_enforcement` is absent from `.planning/config.json`, so it is treated as enabled.

### Applicable ASVS categories

| ASVS category | Applies | Standard control |
|---|---|---|
| V2 Authentication | yes | Zenodo personal access token, `Authorization: Bearer` header over TLS. Token minted with **`deposit:write` only** — omitting `deposit:actions` makes the irreversible publish structurally impossible for the automation. |
| V3 Session Management | no | Stateless bearer-token API; no sessions. |
| V4 Access Control | yes | Least privilege via scope selection (above). Separate sandbox account/token for the D-29-06 rehearsal, so a rehearsal defect cannot touch production. |
| V5 Input Validation | partial | The only external input is Zenodo's JSON responses. Validate the `checksum` field shape before comparing rather than assuming `md5:` — a `KeyError` on `body["checksum"]` should be a failed attempt, not a traceback. |
| V6 Cryptography | yes | `hashlib.md5` for **integrity round-trip only**, matching Zenodo's own returned digest and `manifest.json`'s existing `md5:` convention. Not a security control; do not substitute a "stronger" hash — the point is symmetry with what the server returns. |
| V7 Error Handling / Logging | yes | **Never log the token.** Log the response JSON (`key`, `size`, `checksum`, `version_id`) and the request URL, but scrub `Authorization` before printing any header dict or `requests` exception `request` object. |
| V14 Configuration | yes | Token read from `os.environ`, never a file, never a CLI argument (CLI args appear in `ps` output and shell history). `detect-secrets` with `.secrets.baseline` is the repo's tripwire. |

### Known threat patterns for this stack

| Pattern | STRIDE | Standard mitigation |
|---|---|---|
| Secret committed to git | Information disclosure | Env-var-only token; `detect-secrets` hook (verified PASS against the staged set); a pushed token on a public repo is unrecoverable and must be revoked at Zenodo, not deleted from history. |
| Secret leaked in a traceback or log | Information disclosure | Catch `requests.RequestException` and re-raise with a scrubbed message; never `print(response.request.headers)`. |
| Accidental irreversible publish | Tampering (of the scholarly record) | `deposit:write`-only token; no `publish()` in the codebase; D-29-01. |
| Uploading to production while intending sandbox | Tampering | Distinct env-var names (`ZENODO_TOKEN` vs `ZENODO_SANDBOX_TOKEN`) and a required explicit `--base-url` or `--sandbox` flag with **no default that points at production**. |
| Silent truncated upload published as complete | Tampering / repudiation | Mandatory md5 round-trip check on every attempt; log `version_id`. |
| Artifact mutation by formatting hooks | Tampering | `--no-verify`; never `pre-commit run --all-files`; recorded baseline hashes in this document. |

---

## Package Legitimacy Audit

**This phase installs no external packages.** Every library the plan needs — `requests` (2.34.2),
`tqdm` (4.70.0), `pandas` (3.0.5), `pytest` (9.1.1), `pre-commit` (4.6.2) — is already declared in
`pyproject.toml` and already present in the conda environments [VERIFIED: `pyproject.toml:29-56`
read this session; versions confirmed by import]. `requests` and `tqdm` are **runtime**
dependencies of the shipped package, not dev extras.

| Package | Registry | Already a dependency? | Verdict | Disposition |
|---|---|---|---|---|
| `requests` | PyPI | yes — `pyproject.toml:44` | OK | Reuse; no install |
| `tqdm` | PyPI | yes — `pyproject.toml:45` | OK | Reuse; no install |
| `pandas` | PyPI | yes — `pyproject.toml:43` | OK | Reuse; no install |

**Packages removed due to `[SLOP]` verdict:** none.
**Packages flagged as suspicious `[SUS]`:** none.

> If the planner is tempted to reach for a third-party Zenodo client (`zenodopy`, `zenodo-client`,
> `pyzenodo3`, etc.), **do not.** None is in the dependency set, all would need a legitimacy audit
> and a `checkpoint:human-verify`, and the entire required surface is three HTTP calls that
> `requests` already covers. Adding a dependency to the shipped package's environment days before
> a submission is the wrong trade.

---

## State of the Art

| Old approach | Current approach | When changed | Impact |
|---|---|---|---|
| `POST /api/deposit/depositions/{id}/files` (multipart form) | `PUT {links.bucket}/{filename}` (raw body) | Zenodo "new files API" | 100 MB/file → 50 GB/file. **The old endpoint cannot carry a 4.35 GB payload at all.** D-29-07 already specifies the bucket path. |
| Zenodo on legacy Invenio | Zenodo on InvenioRDM, with `/api/records/{id}/draft` alongside the legacy deposit API | Zenodo's InvenioRDM migration | The legacy deposit API is still documented and functional; new integrations are informally discouraged. [ASSUMED for the discouragement; VERIFIED for the docs carrying no deprecation banner.] |
| `upload_type` + `publication_type` | `resource_type` in the InvenioRDM API | InvenioRDM migration | Only relevant if the plan switches APIs. On the deposit API, `upload_type` is still correct. |

**Deprecated / not to be used here:**
- `metadata.prereserve_doi` — excluded by D-29-03.
- `POST …/actions/publish` from automation — excluded by D-29-01.
- `analyze_e7_spread.py` as an executable — its `ROOT` is a Windows path to a sweep directory that
  no longer exists. Its *recipe* is current and verified; its *entry point* is not.

---

## Assumptions Log

| # | Claim | Section | Risk if wrong |
|---|---|---|---|
| A1 | The legacy Zenodo deposit API "will be deprecated but currently remains functional"; new integrations are discouraged. | State of the Art / Zenodo | Low for this phase — the API is documented and working today. Risk is only that a future re-upload needs rework. Mitigation: note it as a Phase-30+ todo. |
| A2 | `sandbox.zenodo.org` has a documented history of large-file upload failures where production does not. | Pitfall 7 | Low — the recommendation (rehearse small on sandbox, upload big on production) is correct regardless. |
| A3 | The recommended `related_identifiers` relations (`isDerivedFrom` / `isSourceOf` / `isSupplementTo`) are the right semantic choice for the A↔B link. | Zenodo / metadata | Medium. The vocabulary is verified; the *choice within it* is a publication-facing judgement. **Present to the author; do not lock silently.** |
| A4 | `intrinsic/` (518 MB), `reference_calibration.json` (2.2 MB), `config_quickstart_not_paper.yaml` and `README.md` belong with Record A, Record B, or neither. | A/B Split Payloads | **High.** The folded todo assigns only `extrinsic/` (A) and `config_paper.yaml` + `reference_outputs/` + run manifest (B). Getting this wrong makes Record A incomplete for a downstream consumer and is only fixable by a new version. **Author decision required before the 4.35 GB PUT starts** — and D-29-04 wants that PUT started immediately, so this is the highest-priority question in the phase. |
| A5 | `supplement §14`'s published numbers are `camera_height_drift_mm`-based, matching `analyze_e7_spread.py`'s `METRIC`. | E7 comparison | Low — the recipe reproduces the published 10/10 and p = 0.00098 exactly on the baseline tree, which is strong evidence the metric is right. |
| A6 | The manifest repoint belongs to Phase 30 rather than Phase 29. | `_manifest.py` blast radius | Medium. Scoped, not decided — the deferred block already flags it and the table above gives the planner the ten sites. |
| A7 | Committing with `--no-verify` is acceptable project practice for the results commit. | Byte-integrity hazard | Low — hooks are not installed, so `--no-verify` is a no-op belt on top of an already-absent brace. But state it in the commit message so it is not read as an evasion. |

---

## Open Questions

1. **What exactly goes into Record A?** (A4 above.)
   - *Known:* the todo says "the extrinsic frames" (3.6 GB) for A, and `config_paper.yaml` +
     reference outputs + run manifest for B.
   - *Unclear:* `intrinsic/` (518 MB), `reference_calibration.json` (2.2 MB),
     `config_quickstart_not_paper.yaml`, `README.md`.
   - *Recommendation:* **first task of the phase, a `checkpoint:human-verify`.** Record A is
     immutable once published; a missing input costs a new version. Default proposal to put to the
     author: A = `extrinsic/` + `intrinsic/` + `README.md`; B = `config_paper.yaml` +
     `config_quickstart_not_paper.yaml` + fresh `reference_outputs/` + `run_manifest.json` +
     `reference_calibration.json`.

2. **A↔B DOI linkage ordering under D-29-03.**
   - *Known:* no DOI exists until Publish; the author publishes by hand.
   - *Unclear:* whether the author will publish A before B's draft is built (giving B a real
     `isDerivedFrom` target) or wants both drafts staged simultaneously.
   - *Recommendation:* propose the sequential ordering (publish A → build B with A's DOI), note it
     is also what D-29-05 and the folded todo already imply, and get a yes.

3. **Does the phase commit the 227 admitted files, or attempt 1's 209?**
   - *Known:* the sets differ by exactly the 18 stage logs, admitted by a rule added deliberately
     in Phase 28.
   - *Recommendation:* **227**, and say the number and the reason in the commit message. Flag it in
     the plan so the plan-checker does not read it as ignore-rule drift.

4. **Should the D-29-13 assertion repairs land before or after the results commit?**
   - *Known:* the rails only fail once the tree is populated; the repairs touch `tests/` only.
   - *Recommendation:* commit the results **first** (a `results(29):` commit that is purely
     artifacts, matching attempt 1's `83da9b3` shape), then a separate `fix(29):` commit for the
     eight assertions. Two commits keep the artifact commit byte-pure and reviewable.

5. **Success criterion 6 closure evidence.**
   - *Known:* re-scoped 2026-08-25 from a date to the submission event.
   - *Unclear:* Phase 29 cannot observe the submission. The criterion is closable only as
     *"published, and the author confirms it precedes submission."*
   - *Recommendation:* close it on the author's confirmation of Publish, recorded with the two
     minted DOIs in the phase record; do not attempt to gate on the submission itself.

---

## Sources

### Primary (HIGH confidence)

- **In-repo files read this session** — `experiments/check_rerun_gates.py` (CLI parser :2276-2331,
  gate 3 :1970-2190, band sibling resolution :2262), `tests/unit/_baseline_paths.py` (full),
  `tests/unit/test_experiments_provenance.py` (:1-360, class/def index),
  `src/aquacal/datasets/_manifest.py` (full), `src/aquacal/datasets/download.py` (full),
  `src/aquacal/datasets/data/manifest.json` (full), `src/aquacal/datasets/loader.py` (:40-115),
  `.pre-commit-config.yaml` (full), `pyproject.toml` (:1-140), `.gitignore` (:59, :260-300,
  :478, :495-507), `.github/workflows/test.yml` (:3-57),
  `.planning/phases/19.2-experiment-execution-and-provenance/analyze_e7_spread.py` (full),
  `.planning/phases/29.1-post-run-fixes-re-freeze/deferred-items.md` (full),
  `.planning/phases/28-full-suite-production-run/28-RUN-RECORD.md` (:333-447),
  `.planning/todos/pending/2026-08-15-repackage-and-reupload-the-zenodo-archive.md` (full).
- **Measurements executed this session** in a disposable probe clone and read-only over
  `~/aquacal-frozen-rerun-freeze-02-prod` — gate roll-up, D1 rail run, D4 rail run, the four other
  tree-keyed modules, the E2 control, the E7 sign test, the 227/147 admitted-file counts, the
  attempt-1 diff, the file-size scan, the three non-formatting hook runs, and the
  end-of-file/trailing-whitespace exposure count.
- **`https://developers.zenodo.org/`** — deposit draft creation, bucket API, metadata schema,
  `related_identifiers` relation vocabulary, OAuth scopes, rate limits, publish action. Fetched
  2026-08-26.
- **`https://help.zenodo.org/docs/deposit/manage-files/`** and
  **`https://help.zenodo.org/docs/deposit/manage-quota/`** — 100 files / 50 GB per record;
  50 GB default quota plus a 150 GB additional allowance. Fetched 2026-08-26.

### Secondary (MEDIUM confidence)

- `https://gist.github.com/slint/92e4d38eb49dd177f46b02e1fe9761e1` — the minimal draft + bucket PUT
  reference by a Zenodo maintainer.
- zenodo/zenodo issues #2442 (504 Gateway Time-out, timeout raised to 1 hour), #2131 (504 on
  publish), #2328 (`ConnectionAbortedError` on large Python uploads), #2514 (connection resets
  before end of upload), #833 (sandbox large-file failure), #1764 (REST API file size limit).

### Tertiary (LOW confidence)

- Community reporting on the legacy deposit API's deprecation posture relative to InvenioRDM
  (`zen4R` issue #145, third-party blog posts). Recorded as A1; not acted on.

---

## Metadata

**Confidence breakdown:**

| Area | Level | Reason |
|---|---|---|
| Grading mechanics (RUN-03) | **HIGH** | Reproduced end to end this session, including the relocated-tree case the phase actually needs. |
| D1 rail failure set | **HIGH** | Measured, not predicted. 8 failures, 8 matching node ids, each with a read diagnosis from source. |
| E2 same-seed control | **HIGH** | Computed from the actual files; seeds verified equal; three-way md5 recorded. |
| E7 before/after | **HIGH** | Recipe validated by reproducing its own published output before being applied to the new tree. |
| Commit mechanics (RUN-04) | **HIGH** | Every count measured against the returned tree and diffed path-for-path against attempt 1's commit. |
| Byte-integrity hazard | **HIGH** | Counted directly; hook-installation state verified in both clones and in CI config. |
| Zenodo API surface | **HIGH** | Official Zenodo documentation, fetched this session. |
| Zenodo deprecation posture | **MEDIUM** | No official statement found; community sources only. |
| A/B split payload assignment | **LOW** | The todo does not assign four of the archive's members. **Author decision required.** |
| `_manifest.py` blast radius | **HIGH** for the site list, **MEDIUM** for the phase assignment | Sites grepped and read; the phase assignment is a recommendation the deferred block already flags. |

**Research date:** 2026-08-26
**Valid until:** 2026-09-25 for the repo-side findings (they describe a frozen tree and will not
drift). **7 days** for the Zenodo API findings — a live third-party service with an active
migration.
