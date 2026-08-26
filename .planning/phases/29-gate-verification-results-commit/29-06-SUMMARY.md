---
phase: 29-gate-verification-results-commit
plan: 06
subsystem: testing
tags: [pytest, provenance-rails, git-ls-files, csv-provenance-map, degeneracy-sidecars, run-manifest]

requires:
  - phase: 29-gate-verification-results-commit
    provides: "plan 29-05's results(29) commit of the 227 returned artifacts, which is what makes _is_tracked() resolve them and what turns five of the eight rail failures from vacuous passes into real ones"
  - phase: 29-gate-verification-results-commit
    provides: "29-RESEARCH's measured eight-row diagnosis table and 29-PATTERNS' four repair idioms"
  - phase: 29.1-post-run-fixes-re-freeze
    provides: "the D4 ruling in 29.1-PREPUSH-AUDIT.md §1 that licenses three as the correct residual full-suite count"
provides:
  - "tests/unit/test_experiments_provenance.py green against the repopulated live tree: 8 failed -> 0 failed"
  - "the full suite at its ruled count: 11 failed -> 3 failed, all three D4's exact-equality anchors"
  - "a SUITE_LEVEL_MANIFEST_JSON carve-out separating DRIVER-02's flat suite manifest from assemble_benchmark_record's schema"
  - "symmetric tracked-file discovery across the JSON and CSV provenance rails"
  - "CSV_TO_RECORD entries for both FIX-03 per-camera E6 artifacts, and E1's band span corrected to Ruling A1's four seeds"
  - "two evidence files recording the before and after measurements node id by node id"
affects: [29-08, 30-post-submission, any-phase-adding-an-experiments-results-artifact]

actuals:
  tokens: 15000
  tasks: 3
  commits: 3

tech-stack:
  added: []
  patterns:
    - "carve-out as a named frozenset with a per-member comment naming its schema owner or covering record, plus a test holding the carve-out to exactly its named members"
    - "discovery helpers filter through _is_tracked() so a rail's discovered set matches its documented scope of committed artifacts"

key-files:
  created:
    - .planning/phases/29-gate-verification-results-commit/29-rails-before.txt
    - .planning/phases/29-gate-verification-results-commit/29-rails-after.txt
  modified:
    - tests/unit/test_experiments_provenance.py

key-decisions:
  - "Fixed the assertion, never the run or the artifact (D-29-13/D-29-08). All eight failures encoded expectations that moved by design."
  - "run_manifest.json is carved out of the benchmark-record rails as DRIVER-02's flat suite-level manifest rather than being made to satisfy a schema it never claimed."
  - "The JSON/CSV discovery asymmetry was fixed at the helper; calibration.json was deliberately NOT added to any carve-out, because an uncommitted file has no business in a committed-artifact carve-out."
  - "rglob preserved in _discover_json_files(); only the filter changed, so E4's nested e4_cells records and E6's checkpoints stay discoverable."
  - "E1's band span corrected 42-51 -> 42-45 per Ruling A1, annotated in the dated '# CORRECTED' style rather than silently rewritten."
  - "The contaminated full-suite before-run was killed and disclosed rather than quoted; the 11 is composed from two clean pre-edit measurements and forced by the after-run."

patterns-established:
  - "Carve-out exactness: every new carve-out gets a companion test asserting its members really have the property claimed, and that the set stays at exactly its named members."
  - "Measure before repairing, and write the measurement down node id by node id, so repairs target a measurement rather than a prediction (D-29-12)."

requirements-completed: [RUN-03]

coverage:
  - id: D1
    description: "The eight D1 provenance-rail assertions are repaired, and tests/unit/test_experiments_provenance.py reports 0 failed against the committed live tree"
    requirement: RUN-03
    verification:
      - kind: unit
        ref: "python -m pytest tests/unit/test_experiments_provenance.py -q -p no:cacheprovider => 287 passed, 20 skipped in 34.54s (exit 0), against 8 failed, 279 passed, 20 skipped before"
        status: pass
    human_judgment: false
  - id: D2
    description: "The full suite lands at exactly three failures, and those three are D4's ruled exact-equality anchors by node id"
    requirement: RUN-03
    verification:
      - kind: unit
        ref: "python -m pytest tests/ -q -p no:cacheprovider => 3 failed, 2394 passed, 21 skipped in 1830.93s; FAILED node ids exactly test_discard_accounting.py::test_matches_frozen_anchor, test_optim_common.py::TestPerObservationDetailSinks::test_detail_sink_recomputed_geometry_matches_projector, test_pipeline.py::TestSolverConfigSeedIsInert::test_matches_pre_change_anchor"
        status: pass
    human_judgment: false
  - id: D3
    description: "Nothing was silenced: no skip, xfail, deselect, -k or loosened tolerance was introduced, no artifact was edited, and _baseline_paths.py was left alone"
    requirement: RUN-03
    verification:
      - kind: other
        ref: "git diff HEAD~1 HEAD -- tests/unit/test_experiments_provenance.py | grep -cE '^\\+.*(xfail|mark\\.skip|deselect)' => 0; same grep for pytest\\.skip => 0; git status --porcelain experiments/ => empty; git diff HEAD~1 HEAD -- tests/unit/_baseline_paths.py => exit 0; git diff HEAD~1 HEAD --name-only => one path"
        status: pass
    human_judgment: false
  - id: D4
    description: "Two evidence files record the before and after measurements node id by node id, including the live-tree confirmation and the 245-passed control run"
    requirement: RUN-03
    verification:
      - kind: other
        ref: ".planning/phases/29-gate-verification-results-commit/29-rails-before.txt (198 lines) and 29-rails-after.txt (204 lines)"
        status: pass
    human_judgment: false
  - id: D5
    description: "The repairs are a separate, reviewable fix(29) commit touching exactly one file, landing after and leaving untouched plan 29-05's artifacts commit"
    verification:
      - kind: other
        ref: "git log -1 --pretty=%s => fix(29): ...; git show --name-only --format='' HEAD => tests/unit/test_experiments_provenance.py only; 70e783f still present and unamended"
        status: pass
    human_judgment: false
  - id: D6
    description: "The four repaired assertions state what the artifacts actually are, in the module's own idioms, with every superseded rationale annotated rather than deleted"
    verification: []
    human_judgment: true
    rationale: "Whether a provenance record's prose correctly describes what a published number may be quoted over is an editorial judgment about the manuscript's evidence, not something a test can settle. The rails prove the seed spans agree with the data; they cannot prove the surrounding sentences are the right ones."

duration: 75min
completed: 2026-08-26
status: complete
---

# Phase 29 Plan 06: Repair the Provenance Rails Summary

**All eight D1 provenance-rail failures were assertions that had gone stale against artifacts which moved by design; correcting them took the module from 8 failed to 0 and the full suite from 11 failed to exactly the three ruled D4 anchors, with no artifact edited and nothing silenced.**

## Performance

- **Duration:** 75 min (of which 31 min was the serial full-suite run)
- **Started:** 2026-08-26T16:50Z
- **Completed:** 2026-08-26T18:10Z
- **Tasks:** 3 completed
- **Files modified:** 3 (1 source, 2 evidence)

## Accomplishments

- **Measured before repairing.** `29-rails-before.txt` records `8 failed, 279 passed, 20 skipped` against the committed tree, every failing node id verbatim, the confirmation that `RESULTS_TREE == live` (so the rails were validating this run and not the pre-run baseline), `245 passed` on the five tree-keyed control modules, and D4's three node ids still failing. The measured set matched D1's predicted set in **both** directions — no ninth failure, none missing.
- **Repaired all eight in four idioms**, editing only `tests/unit/test_experiments_provenance.py`:
  - *DRIVER-02's flat suite manifest* (failures 1–2) — a new commented `SUITE_LEVEL_MANIFEST_JSON` frozenset, excluded from `_schema_versioned_json_files()`.
  - *Ruling A1's four-seed E1 band* (failures 5–6) — `seeds 42-51` → `seeds 42-45`, annotated.
  - *New artifacts that were never registered* (failures 3, 4, 7, 8a) — five DEGEN sidecars into `SELF_DESCRIBING_JSON`, two FIX-03 per-camera CSVs into `CSV_TO_RECORD`.
  - *The JSON/CSV discovery asymmetry* (failure 8b) — `_discover_json_files()` gained the `_is_tracked` filter its sibling always had.
- **Landed the ruled count.** `pytest tests/` reports `3 failed, 2394 passed, 21 skipped` — the three D4 anchors, character for character the same node ids recorded before the repairs. Not zero, not four.
- **Added a guard the plan did not ask for but the module's own philosophy demands** — `TestSuiteLevelManifestCarveOut`, so the new carve-out cannot quietly become a blanket exemption.

## Task Commits

1. **Task 1: Measure the rails against the committed tree** — `4256e82` (docs)
2. **Task 2: Repair the eight assertions in place** — `5799b14` (fix) — also serves as Task 3's `fix(29):` commit, see *Deviations*
3. **Task 3: Land the ruled full-suite count** — verified against `5799b14`; produced `29-rails-after.txt`

**Plan metadata:** see the `docs(29-06): complete ...` commit.

## Files Created/Modified

- `tests/unit/test_experiments_provenance.py` — the eight repairs (+241 / −5). New `SUITE_LEVEL_MANIFEST_JSON` constant and `TestSuiteLevelManifestCarveOut` class; five new `SELF_DESCRIBING_JSON` members; two new `CSV_TO_RECORD` keys; two corrected seed spans; `_discover_json_files()` gains an `_is_tracked` filter; `_is_tracked()`'s docstring extended with the JSON case; `_schema_versioned_json_files()` excludes the suite manifest.
- `.planning/phases/29-gate-verification-results-commit/29-rails-before.txt` — the pre-repair measurement, node id by node id, with a per-failure diagnosis.
- `.planning/phases/29-gate-verification-results-commit/29-rails-after.txt` — both deltas in one place, the residual-findings section, and the disclosure in §4(b).

## Decisions Made

**The interpreter.** `~/anaconda3/envs/aquacal-freeze02-cleanenv/bin/python` (3.11.15, pytest 9.1.1), per 29-RESEARCH:1252's nomination for work in the working clone. `pytest` is absent from the active `aquacal` env. Every count in both evidence files and in this summary comes from that one interpreter, so the deltas compare like with like.

**Fix the assertion, never the run.** Each of the eight was traced to a specific artifact fact before being touched: `run_manifest.json`'s 26 flat keys read directly off the file; `exp1_band.csv`'s 256 rows over `[42,43,44,45]` and `exp1_parameter_band.csv`'s 384 over the same four, cross-checked against `e1_seed_band_provenance.json`'s `solver_config['seeds'] == [42,43,44,45]`; `generalization_sweep_per_camera_band.csv`'s 864 rows over seeds 42–47 against `e6_seed_band_provenance.json`'s matching list; each DEGEN sidecar's writer located in `experiments/_degeneracy.py` and its covering record named.

**`calibration.json` was not carved out.** The plan and Pitfall 5 both forbade it and were right: the file is gitignored, so admitting it to a set whose stated scope is committed artifacts would have papered over the real defect. The fix went to the helper. Its absence is proven at runtime, not just by grep — neither carve-out contains it, and it is no longer in the discovered set (117 discovered of 118 on disk, the one difference being exactly that file).

**`_baseline_paths.py` was not touched.** `resolve_results_dir()` re-aiming from `archive` to `live` once the tree holds a file is the module's entire purpose. `git diff HEAD~1 HEAD -- tests/unit/_baseline_paths.py` exits 0.

**`pre-commit run --all-files` was never run.** 143 committed artifacts deliberately lack a final newline; `end-of-file-fixer` would rewrite them and destroy the byte-for-byte property 29-05 proved. Ruff was run scoped to the one modified file, on both the pinned 0.15.1 from `.pre-commit-config.yaml` and 0.16.4 from `aquacal-freeze02-prod`; both report `All checks passed!` and `1 file already formatted`.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 — Missing critical functionality] Added a carve-out exactness guard the plan did not specify**

- **Found during:** Task 2
- **Issue:** The plan asked for `SUITE_LEVEL_MANIFEST_JSON` as a commented frozenset but specified no test for it. This module holds every one of its other carve-outs to an exactness gate — `test_seedless_carve_out_is_exact`, `test_seedless_carve_out_has_exactly_six_members_and_excludes_e2`, `test_schema_versionless_json_set_equals_self_describing_json` — precisely because, in its own words (review H5), a carve-out must be "earned by an explicit, commented, exactly-verified set — not by omission." A new carve-out that lifts two rails off a file, with nothing checking it stays honest, is the one shape this module exists to prevent.
- **Fix:** Added `TestSuiteLevelManifestCarveOut` with two tests: each carved-out file found on disk genuinely carries a `schema_version` and genuinely lacks both an `environment` block and a `solver_config`; and the set stays at exactly one named member, so a second suite-level schema has to fail there first and be added deliberately.
- **Files modified:** `tests/unit/test_experiments_provenance.py`
- **Verification:** Both tests pass. Deliberately written without any `pytest.skip` — the first iterates the *discovered* set rather than the carve-out, so a tree that legitimately holds no manifest (the pre-run baseline archive has none) asserts nothing instead of skipping.
- **Committed in:** `5799b14`

**2. [Rule 3 — Blocking issue] The full-suite "before" run was killed rather than quoted**

- **Found during:** Task 3
- **Issue:** A full-suite run was started against the committed tree before any edit, to measure the `11 failed` directly. The suite runs serially at 30–90 minutes (`pytest-xdist` is not installed; there is a standing pending todo about it), and it was still running when the repairs landed on disk. pytest reads source from disk to *render* a failure, so that run would have printed post-repair source lines under pre-repair node ids — actively misleading evidence in a file whose entire purpose is honest measurement.
- **Fix:** Killed it and disclosed the decision in `29-rails-after.txt` §4(b) rather than omitting it. The `11` is composed from two clean pre-edit measurements recorded in `29-rails-before.txt` (8 on the provenance module + 3 on D4), corroborated by 29-RESEARCH's independent full-suite measurement of 11 on the probe clone, by `245 passed` on the control modules ruling out any other tree-sensitive contributor, and — most strongly — by the after-run itself: since this plan changed exactly one test file, and the whole suite afterwards reports exactly the three D4 nodes, the pre-repair total is forced to 11 rather than assumed.
- **Files modified:** none (evidence only)
- **Verification:** Collected totals reconcile exactly: `3 + 2394 + 21 = 2418` after, and this plan's net effect on collection is zero (−2 `run_manifest` parametrized cases, +2 new tests), so `11 + 2386 + 21 = 2418` before. Nothing was dropped from the suite.
- **Committed in:** evidence in the plan-metadata commit

**3. [Rule 3 — Blocking issue] Task 3's `fix(29):` commit was made at the end of Task 2**

- **Found during:** Task 3
- **Issue:** The plan places the single `fix(29):` commit in Task 3, after the full-suite run. Committing per task, as the executor contract requires, would have produced either two commits touching the same file or an uncommitted Task 2.
- **Fix:** Made one `fix(29):` commit at the end of Task 2, which satisfies every one of Task 3's commit criteria verbatim — `git log -1 --pretty=%s` matches `^fix(29):`, `git show --name-only --format="" HEAD | wc -l` returns `1` and that path is `tests/unit/test_experiments_provenance.py`, and it sits strictly after the unamended `70e783f results(29)` artifacts commit. `29-rails-after.txt` is deliberately held out of it and lands in the plan-metadata commit, so the `fix(29):` commit stays a one-file change.
- **Files modified:** none beyond the planned one
- **Verification:** All of Task 3's commit acceptance criteria checked and passing against `5799b14`.
- **Committed in:** `5799b14`

---

**Total deviations:** 3 auto-fixed (1 × Rule 2, 2 × Rule 3)
**Impact on plan:** No scope creep. One guard added that the module's own conventions require; two are sequencing and evidence-integrity decisions that made the record more honest, not less. Zero prohibitions were touched.

## Issues Encountered

**Two acceptance criteria are literally unmet and substantively met; both are reported rather than engineered around.**

- `grep -c 'rglob'` was to be *unchanged*. It went 1 → 2. The second occurrence is the word `rglob` inside the new `_discover_json_files()` docstring, which explains why the walk is recursive. The code is still `RESULTS_DIR.rglob("*.json")` at one site, and the intent behind the criterion — that the JSON walk stayed recursive — is proven at runtime, not by grep: the discovered set still contains E4's nine `e4_cells/*/benchmark.json` records and E6's nested checkpoints.
- `grep -c 'calibration.json'` was to be *unchanged from its pre-repair value*. It went 1 → 3. Both new occurrences are prose: a dated `# NOTE 2026-08-26 (plan 29-06)` recording *why* the file was **not** re-admitted, and the `_is_tracked` docstring extension. `grep -cE '^[^#]*"calibration\.json"'` returns `0`, and at runtime `'calibration.json' in (SELF_DESCRIBING_JSON | SUITE_LEVEL_MANIFEST_JSON)` is `False`. The criterion's intent — that the file was not added to any carve-out — holds exactly.

**A third stated expectation did not survive measurement, and is recorded as measured.** The plan's prose predicted `2407 passed, 26 skipped`; the suite reported `2394 passed, 21 skipped`. The gated quantity, the failure count, is exactly 3 with exactly the three ruled node ids. The pass/skip figures were prose rather than a measurement carried forward, and the collected totals reconcile cleanly at 2418 before and after. Under D-29-12 this is information, so it is written down in `29-rails-after.txt` §4(a) rather than smoothed over.

**One tension between the plan's own two statements was resolved toward the more careful one.** The `<verification>` block says "`seeds 42-51` is gone"; the acceptance criteria say the check is "deliberately **not** gated on the absence of the superseded ten-seed string", because the annotate-never-rewrite idiom keeps the prior span in the entry's prose. The criteria are right and the verification line could not be satisfied anyway: `interface_ablation_band.csv` legitimately spans seeds 42–51 and its entry says so, and that rail passes. The superseded E1 claim is preserved inside a dated `# CORRECTED 2026-08-26 (plan 29-06).` block; the rail that matters matches against the dict *value*, which now reads `seeds 42-45`.

## Known Stubs

None. No placeholder, no `TODO`, no unwired data path was introduced.

## Threat Flags

None. This plan changed one test module; it added no endpoint, no auth path, no file-access pattern and no schema at a trust boundary. Its net effect on the project's attack surface is negative: `_discover_json_files()` now refuses to read untracked working-tree JSON into a rail scoped to committed artifacts (T-29-40).

## Next Phase Readiness

- **RUN-03 is closed on both halves.** The gate half landed in 29-05 (`TOTAL: 176 PASS, 7 N/A, 0 FAIL`, `gate3_git_sha_consistency` PASS on one sha); the test half is this plan. Plan 29-08 re-declares `RUN-03` in its frontmatter as the phase closer, so a final re-check there is expected and should find it already green.
- **A residual for 29-08 to file, under D-29-14.** D4's three exact-equality anchors stay as ruled. What would fix them: re-capturing the three anchors on Linux, or converting the three assertions to a documented ULP-scale comparison with the cross-platform reason stated at the constant. Either is a deliberate decision about what an anchor means across platforms, and belongs to the author, post-submission. Recorded in `29-rails-after.txt` §7.
- **A twin site worth knowing about.** The E1 four-seed correction here is the same defect class as the completed todo `2026-08-20-e1-band-scope-string-still-claims-ten-seeds-after-ruling-A1-cut-it-to-four.md`, which corrected the *sidecar's* `scope` string in `e1_refractive_comparison.py`. That todo's own words — "four is correct; the prose is what is stale" — describe this repair exactly. Anyone auditing Ruling A1's blast radius should treat those two sites as a pair.
- **Nothing is blocked.** `experiments/` is byte-untouched, `.gitignore` and `.pre-commit-config.yaml` are unchanged, the branch is still `results/rerun-freeze-02`, and `70e783f` is unamended.

---
*Phase: 29-gate-verification-results-commit*
*Completed: 2026-08-26*

## Self-Check: PASSED

All claimed files exist on disk (`tests/unit/test_experiments_provenance.py`,
`29-rails-before.txt`, `29-rails-after.txt`, `29-06-SUMMARY.md`) and both claimed
commits resolve in `git log --oneline --all` (`4256e82`, `5799b14`).
