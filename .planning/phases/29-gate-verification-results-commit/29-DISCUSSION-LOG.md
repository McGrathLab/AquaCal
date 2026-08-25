# Phase 29: Gate Verification & Results Commit - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-08-25
**Phase:** 29-gate-verification-results-commit
**Areas discussed:** Zenodo publish mechanism, D1's 8 provenance failures, E7 before/after reporting bar, Criterion 5 traceability bar

---

## Zenodo publish mechanism

### Q1 — Where should the human gate sit, given GUI access is uncertain?

| Option | Description | Selected |
|--------|-------------|----------|
| I write it, you run the publish | Claude builds the script; user executes the final publish call with their own token | |
| I upload, you authorise publish | Claude drives the transfer; publish sits behind a blocking checkpoint | |
| Full automation behind one checkpoint | Claude does everything including publish, gated once | |
| **User's own answer** | **Automate upload into an unpublished DRAFT; review in the web UI; mint there** | ✓ |

**User's choice:** *"is there a way to automate the upload/publish, but have it upload a draft that I can then review in the web interface before minting?"*

**Notes:** Better than any option offered, and Claude confirmed it works: a Zenodo deposition
exists as a reviewable draft from creation, and no DOI is registered until Publish. It decouples
the headless 4.35 GB transfer (this box, no GUI) from review and minting (any browser, any time,
since drafts persist). It also preserves `PROJECT.md`'s locked *"published by the user by hand"*
decision instead of overriding it — the irreversible act stays a deliberate human action; only
the browser dependency for the **upload** is dropped, which was never what the decision protected.

### Q2 — How far should automation go before it stops?

| Option | Description | Selected |
|--------|-------------|----------|
| Draft + files + full metadata | Claude populates title, authors, description, license, version, A↔B related-identifier links | ✓ |
| Draft + files, metadata left to user | User completes metadata in the UI | |
| Draft + files + metadata, and reserve the DOIs | As above plus DOI reservation on the drafts | |

**Notes:** DOI reservation deliberately declined — it commits to an identifier and the manuscript
does not need the strings before Publish.

### Q3 — When should Record B's draft be built?

| Option | Description | Selected |
|--------|-------------|----------|
| After grading passes | Built only once gate verification and the E2 same-seed control pass | ✓ |
| Build both drafts immediately | Populate both up front, amend B if grading turns something up | |

**Notes:** Record A's upload still starts immediately and in parallel — it holds inputs, which
grading cannot invalidate, and at 4.35 GB it is the critical path.

### Q4 — Rehearsal

**Claude proposal, accepted in flow:** rehearse the whole split on `sandbox.zenodo.org` first —
separate instance, separate tokens, throwaway DOIs — so the real draft the author reviews is one
already known to be shaped right. Justified by the publish being one-way.

---

## D1's 8 provenance failures

### Q1 — Default disposition when the real failure count is measured

| Option | Description | Selected |
|--------|-------------|----------|
| Fix artifacts, never assertions | A failure means artifacts genuinely lack required provenance; fix the writer | |
| Triage each, rule explicitly, close phase | Fix what is cheap, rule on the rest like D4 | |
| Fix assertions where the expectation was wrong | Where 29.1 moved an expectation by design, correct the assertion | ✓ |

**Notes:** Claude flagged the sharp edge — "the assertion was wrong" and "the assertion is
inconvenient" look identical at the moment of editing, and D4's tests carry docstrings saying
*"a mismatch here is a finding to report, not a tolerance to loosen."* Claude then asked for the
evidence bar.

### Q2 — Evidence bar for changing an assertion *(superseded by the user's clarification)*

| Option | Description | Selected |
|--------|-------------|----------|
| Cite the decision that superseded it | Requires a D-NN ruling or design-table citation in commit and docstring | |
| Claude's judgement, recorded in the summary | Claude decides, records reasoning per test | |
| Cite the decision, and you approve each change | Citation plus a blocking checkpoint | |

**User's response — a scope correction rather than a selection:**

> *"clarify something for me -- we're just talking about small gate errors here, right? The run
> outputs should not be touched, I'm just trying to say that if there's an obviously broken gate
> (for example something that doesn't expect a column we purposefully added in a certain
> artifact) we should fix that rather than re-running the whole suite. Regardless, i think we
> have decided that the outputs are scientifically valid, so barring a finding that refutes that,
> I want to get these outputs published to zenodo even if there is some noise from checks and
> tests"*

**Notes:** The user was right and Claude had over-dramatized the area. Claude corrected with
evidence: the **gate is already clean** (`176 PASS, 7 N/A, 0 FAIL`, zero `[FAIL]` lines, and
`gate3_git_sha_consistency` / `gate3_run_manifest_fields` / `gate3_run_manifest_clean_tree` all
PASS). Only `tests/unit/test_experiments_provenance.py` is in question, and it asserts artifact
**metadata** — sha, seed, environment fields — never a measured value, so a failure there cannot
by construction mean the numbers are wrong. Claude also noted D1's "8" is a prediction measured
against attempt 1's tree, not a measurement against attempt 2's.

Claude held one line, drawn from the user's own *"barring a finding that refutes that"*: a
concrete three-item stop list (E2 same-seed control fails; `gate3_git_sha_consistency` stops
holding; a §3-facing number traces to a disagreeing artifact), so "refutes" is not decided in the
moment.

### Q3 — Fall-through for failures neither assertion-wrong nor cheaply fixable

| Option | Description | Selected |
|--------|-------------|----------|
| Rule explicitly, like D4 | Named ruling, phase closes with the failure documented | |
| Escalate before closing | Blocking decision to the user | |
| File a post-submission todo | Record it, defer the fix, close the phase | ✓ |

---

## E7 before/after reporting bar

| Option | Description | Selected |
|--------|-------------|----------|
| Measure, report, flag if it moved | Both numbers in the record; raised to the user only if the conclusion changed | ✓ |
| Measure and report only, no flag | Interpretation left to manuscript re-verification | |
| Measure, and draft the §3 correction if it moved | As selected, plus Claude drafts supplement §14 text | |

**Notes:** §3 edits stay the author's. The ROADMAP's own wording is why this is graded here at
all: *"it is reported here, not discovered during manuscript re-verification."*

---

## Criterion 5 traceability bar

| Option | Description | Selected |
|--------|-------------|----------|
| Mapping document, machine-verified paths | Table mapping each §3 number to artifact/column/row, with a path-verifying script | |
| Full machine-checkable value assertions | Script re-reads each cited value and fails on disagreement | |
| Spot-check the headline figures | Trace only the numbers §3 leans on | |

**User's response — a scope rejection:**

> *"the main text is not available here, and building mapping docs is the job of the paper-writing
> agent, not you. This requirement feels out of scope"*

**Notes:** Claude verified the claim before agreeing. `main.tex` lives in
`OneDrive - Georgia Institute of Technology/Thesis/Spinoffs/papers/aquacal/` — outside this
repository; the only `.tex` files tracked here are generated fragments. Claude then found the
requirement text supports the user *more precisely than the criterion does*: **RUN-04** says
*"traceable **to this run**"* while ROADMAP criterion 5 restates it as *"in the manuscript"*.
The requirement is the authority.

The traceability mechanism already exists as this run's own output — `benchmark_grid.tex`,
`cpr_derived_values.tex`, `cpr_grouping.tex`, which §3 includes rather than hand-copying, per
`PROJECT.md`'s locked *"Generate the results table from `benchmark.json`, not by hand"*. And the
manuscript-side half already has an owner: **POST-01**, mapped to **Phase 30**. Both halves owned,
neither dropped. Recorded as D-29-19.

### Second question in the same turn — what lands in the committed tree

| Option | Description | Selected |
|--------|-------------|----------|
| Follow DATA-01b, match attempt 1 | Commit what ignore rules allow (~147 files); bulk stays in archive + Record B | ✓ |
| Commit everything, relax DATA-01b | Track all 461 files | |

---

## Claude's Discretion

- Structure of the upload/publish tooling — single script vs. module, argument surface, location.
- Task ordering beyond D-29-04 (Record A first, parallel) and D-29-05 (Record B after grading).
- How the E7 before/after comparison is computed, so long as both numbers land in the record.

## Deferred Ideas

- Manuscript-side §3 reconciliation → POST-01, Phase 30.
- `_manifest.py`'s pinned Zenodo record id may need repointing after the split — flagged for
  planning to scope; may belong with POST-01.
- E7 band overwrite hazard — measured as not firing in production; do not run E7's band by hand.
- D6 — `check_e2_band`'s `--smoke` sibling-directory quirk; irrelevant to production runs.
- **Todo hygiene:** several todos carrying `resolves_phase: 23/25/26/27` are still in `pending/`
  although those phases are complete. Out of scope here; worth a later sweep.
