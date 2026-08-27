# Phase 29: Gate Verification & Results Commit - Context

**Gathered:** 2026-08-25
**Status:** Ready for planning

<domain>
## Phase Boundary

Turn the returned v2.1 production run into the repository's committed evidence base and the
published archive the paper cites. Three requirements: **RUN-03** grade the run,
**RUN-04** commit it with provenance intact, **RUN-05** split the Zenodo record and publish the
results package before the paper is submitted.

**The run is already in hand and already measured.** Phase 28 completed 5/5 and returned:
`TOTAL: 176 PASS, 7 N/A, 0 FAIL`, 20/20 stages at exit 0, output archived read-only at
`~/rerun-freeze-02-output.tar.gz` (461 files, sha256 recorded). This phase does not run the
suite; it grades, commits and publishes what that run produced.

**Not this phase:** re-running any stage, editing any output artifact, or reconciling the
manuscript. Manuscript reconciliation is POST-01, mapped to Phase 30.

</domain>

<decisions>
## Implementation Decisions

### Zenodo publish mechanism (RUN-05)

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

### Test and gate noise vs. publication (RUN-03)

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

### E7 before/after comparison (ROADMAP criterion 3)

- **D-29-16:** **Measure, report both numbers in the phase record, and flag to the author only if
  the conclusion moved.** FIX-02 gave E7 two extra free parameters per interface, which could
  soften the fixed-intrinsics arm's published 10-of-10 sign test (p = 0.00098, supplement §14).
  If it held, it is a line in the record. If it moved, it is raised explicitly — **§3 edits stay
  the author's**, matching how the manuscript has been handled throughout. This is the one area
  of the phase that can reach into §3, and the ROADMAP's own wording is the reason it is graded
  here: *"it is reported here, not discovered during manuscript re-verification."*

### What gets committed (RUN-04)

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

### Folded Todos

- **`2026-08-15-repackage-and-reupload-the-zenodo-archive.md`** — *"Split the Zenodo record into
  immutable inputs and a versioned results package."* The only pending todo carrying
  `resolves_phase: 29`, and it **is** RUN-05. Record `21889922` is a single ~4.35 GB zip bundling
  inputs and outputs, so Zenodo's new-version flow has no file to carry forward and every future
  results revision costs a full re-upload. Splits into **Record A** (extrinsic frames, immutable)
  and **Record B** (`config_paper.yaml`, reference outputs, run manifest — a few MB, re-versioned
  whenever results change). `config_paper.yaml` goes with the **results**, not the inputs.
  Carries a documented fallback if the input upload cannot complete in time: leave `21889922`
  untouched as the historical submitted package and publish only Record B, with the paper citing
  raw data at `21889922` and results at the new DOI. **Zero large upload.**

  **Its sequencing decision was superseded on 2026-08-25** — the original said "upload from the
  Windows box while the run is in flight"; that window closed unused, so all upload work now
  happens on the Linux run machine. Recorded in the todo itself.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### The run being graded — read first
- `.planning/phases/28-full-suite-production-run/28-RUN-RECORD.md` — **the document this phase
  was written to be opened from.** Carries the three hard signals, the criterion-3 derivation,
  the environment record, the returned-artifact index, and five open items.
- `.planning/phases/28-full-suite-production-run/freeze02-rollup.txt` — the end-of-run
  completeness roll-up, `176 PASS, 7 N/A, 0 FAIL`.
- `.planning/phases/28-full-suite-production-run/freeze02-gates-full.txt` — the post-run gate
  re-run over the returned tree; agrees exactly, zero `[FAIL]` lines.
- `.planning/phases/28-full-suite-production-run/freeze02-archive-manifest.txt` — per-path file
  counts, the completeness assertion, and the 507-vs-461 reconciliation.
- `.planning/phases/28-full-suite-production-run/rerun-freeze-02-output.sha256` — the two
  recorded hashes for the archive and the preserved log.

### Zenodo (RUN-05)
- `.planning/todos/pending/2026-08-15-repackage-and-reupload-the-zenodo-archive.md` — the
  A/B split design, the API guidance, the round-trip verification requirement, the fallback, and
  the superseded sequencing note.
- `.planning/PROJECT.md` § Key Decisions — *"Zenodo is published by the user by hand, values
  pre-computed for transcription"*, and *"Generate the results table from `benchmark.json`, not
  by hand"*.
- `src/aquacal/datasets/download.py` — the **only** existing Zenodo code path. Read-only,
  unauthenticated, public-URL. **No upload tooling exists in this repo**; it must be built.
- `src/aquacal/datasets/_manifest.py` — where `zenodo_record_id` / `zenodo_filename` are pinned.
  A record split changes what these must point at.

### Provenance, tests and gates (RUN-03)
- `tests/unit/_baseline_paths.py` — `resolve_results_dir()` prefers the live tree only while it
  holds a file. Its module docstring **predicts this phase's situation in terms**. Read it before
  touching any provenance test.
- `tests/unit/test_experiments_provenance.py` — the D1 rails.
- `.planning/phases/29.1-post-run-fixes-re-freeze/29.1-VERIFICATION-BAR.md` — diagnoses D4's three
  anchor failures and predicts D1's return.
- `.planning/phases/29.1-post-run-fixes-re-freeze/29.1-PREPUSH-AUDIT.md` §1 — the D4 ruling.
- `experiments/check_rerun_gates.py` — the gate. **Inside the frozen tree; do not edit.**

### Requirements and roadmap
- `.planning/REQUIREMENTS.md` — RUN-03 (:190), RUN-04 (:192), RUN-05 (:194, re-scoped
  2026-08-25), POST-01 (:220, Phase 30).
- `.planning/ROADMAP.md` § Phase 29 — the six success criteria, criterion 6 amended 2026-08-25.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `src/aquacal/datasets/download.py` — uses `requests` with streaming and checksum verification.
  Its style and error handling are the natural model for the upload counterpart, and `requests`
  is already a dependency.
- `experiments/check_rerun_gates.py` — already re-runnable over any output tree at
  `--profile full`. Grading needs no new gate; it re-invokes this one.

### Established Patterns
- **Acceptance is read from a roll-up `TOTAL:` line, never from `$?`** (D-01/D-02). The driver
  exits non-zero on a healthy run.
- **Evidence files are written under a per-attempt prefix** (`freeze01-*`, `freeze02-*`) and sit
  side by side so attempts compare line for line. A Phase 29 evidence set should follow suit.
- **Records of what was measured are annotated, never rewritten.** Superseded decisions get a
  dated note; historical summaries and audits stay untouched.
- **Artifacts are gitignored under DATA-01b** where they are large or per-observation; the
  read-only tarball plus sha256 is the record for those.

### Integration Points
- The production clone `~/aquacal-frozen-rerun-freeze-02-prod` holds the run output **untracked**,
  on a detached HEAD at `7005a27`, with no `results/*` branch. Output reaches git by being
  committed from there or copied to the working clone — **the prod clone must not be mutated.**
- `src/aquacal/datasets/_manifest.py` pins the Zenodo record id consumers download from. Splitting
  the record has a downstream effect here that planning must decide on (it may belong to Phase 30
  rather than this phase — flag, do not assume).

</code_context>

<specifics>
## Specific Ideas

- **"Upload a draft that I can then review in the web interface before minting"** — the author's
  own framing, and the shape the whole RUN-05 approach was built around. It is a better answer
  than any of the three options originally offered, because it satisfies the locked
  publish-by-hand decision and the no-GUI constraint simultaneously rather than trading one off.
- **"I want to get these outputs published to Zenodo even if there is some noise from checks and
  tests"** — the disposition that governs RUN-03. Grading exists to catch a finding that refutes
  scientific validity, not to gate publication on rail hygiene.
- **"Building mapping docs is the job of the paper-writing agent, not you"** — the scope fence
  behind D-29-19.

</specifics>

<deferred>
## Deferred Ideas

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

### Reviewed Todos (not folded)

The `todo.match-phase` query returned 20 matches, but 19 matched only on the broad
`area: experiments` keyword and carry a `resolves_phase` of 23, 25, 26 or 27, or none at all.
None is Phase 29 scope. Notable among them:

- `2026-08-15-archive-stale-outputs-before-the-run-purge-them-after.md` (`resolves_phase: 26`) —
  its "purge at release" half is POST-03, Phase 30.
- `2026-08-15-POST-SUBMISSION-*` and `2026-08-17-POST-SUBMISSION-*` — explicitly post-submission.
- The `parallelize-the-test-suite` pair and `reduce-memory-and-cpu-load-during-calibration` —
  performance work, no phase assigned.

**Hygiene note for a later phase, not this one:** several todos carrying `resolves_phase: 23/25/26/27`
are still in `pending/` although those phases are complete. Worth a sweep; out of scope here.

</deferred>

---

*Phase: 29-gate-verification-results-commit*
*Context gathered: 2026-08-25*
