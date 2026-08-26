---
phase: 29-gate-verification-results-commit
plan: 03
subsystem: experiments
tags: [e2, e7, sign-test, same-seed-control, provenance, evidence, rerun-freeze-02, roadmap-criteria]

# Dependency graph
requires:
  - phase: 29-gate-verification-results-commit
    provides: "Plan 29-02 landed the returned run in the working clone — experiments/results/real_rig_metrics.json, benchmark.json and interface_ablation_band.csv are present at their original relative paths (untracked), which is what both scripts read"
  - phase: 28-full-suite-production-run
    provides: "The v2.1 production run at rerun-freeze-02 / 7005a27, whose artifacts are the 'after' side of both comparisons"
  - phase: 26-frozen-handoff-package
    provides: "experiments/pre_rerun_baseline/results/ — the Windows / aquacal 1.8.0 / 6c7f930b archive that is the 'before' side of the criterion's comparison"
provides:
  - "analyze_e2_control.py + 29-e2-control.txt — ROADMAP criterion 2 / D-29-10 stop-list item 1 measured and PASSING: seed 42 vs seed 42, worst scalar relative drift 2.5146e-08 on inter_corner_rmse_mm against the pre-run baseline, exactly 0 against attempt 1, integer n_comparisons exact at 7762 on both sides"
  - "analyze_e7_before_after.py + 29-e7-before-after.txt — ROADMAP criterion 3 / D-29-16 discharged: fixed pairing HELD at 10/10, p = 1/1024 = 0.00098 in both trees; refined pairing MOVED 8/10 (56/1024 = 0.05469) -> 7/10 (176/1024 = 0.17188)"
  - "The D-29-16 flag-to-author finding, raised in the phase record rather than discovered during manuscript re-verification"
  - "A re-runnable provenance for both numbers — the phase record now cites a committed script, not a research session"
affects: [29-05 results commit, 29-06 provenance rail repairs, 29-08 phase close, 30 post-01 manuscript reconciliation]

actuals:
  tokens: 13300
  tasks: 2
  commits: 2

tech-stack:
  added: []
  patterns:
    - "One-off evidence producer lives beside the evidence it produces, in the phase directory — matches .planning/phases/19.2-.../analyze_e7_spread.py; scripts/ stays reusable operational tooling"
    - "Evidence file = verbatim script stdout captured by shell redirection, never hand-edited (carried from 29-02)"
    - "Copy the recipe, replace the entry point: a script whose statistic is validated by reproducing its own published output is transferred verbatim, while its hard-coded paths and hard-wired domain constants are discarded"
    - "A control that cannot be misread out of context: the disambiguating fact (here, the seed) is printed on EVERY comparison line, not once in a header"
    - "Read the fact, assert the fact, print the fact — the seed comes from each tree's own benchmark.json solver_config['seed'] and is asserted equal before any value is compared; disagreement fails closed"
    - "Verdict headers are derived from the computed booleans, not hard-coded prose, so the conclusion text can never contradict the numbers printed above it"

key-files:
  created:
    - .planning/phases/29-gate-verification-results-commit/analyze_e2_control.py
    - .planning/phases/29-gate-verification-results-commit/analyze_e7_before_after.py
    - .planning/phases/29-gate-verification-results-commit/29-e2-control.txt
    - .planning/phases/29-gate-verification-results-commit/29-e7-before-after.txt
  modified: []

key-decisions:
  - "The E2 control reports TWO worst-case figures per comparison, not one: the worst over the top-level scalar fields (the seven-row set RESEARCH measured and the criterion's headline) and the worst including the flattened compound leaves. Silently skipping auxiliary_reprojection_px, camera_height_range_m and reprojection_range_px in a publication-blocking control would leave three fields unchecked; reporting both keeps the criterion's number intact AND closes the gap."
  - "The exit code gates on the stronger figure (worst including compound leaves, 3.6317e-08), not the headline one — a control should fail on the largest drift it can see, not the most flattering."
  - "The seed is read from benchmark.json and asserted equal rather than assumed; SEED = 42 is stated as an expectation to check. A cross-seed comparison fails closed and prints no values, because at this tolerance a cross-seed number is not merely wrong, it is misleading."
  - "The E7 verdict's section headers ('HELD' / 'MOVED') are computed from the data, not written as prose. The analog's hard-wired 'n = 5' caveat is exactly the defect that motivates this; a verdict that can contradict its own table is worse than none."
  - "The refined pairing's move is reported flatly with both published figures and its FIX-02 attribution, and nothing further. No manuscript file was opened, read for editing, or written (D-29-16, D-29-19)."
  - "Neither script uses tests/unit/_baseline_paths.py's resolve_results_dir(); it switches subject on whether the live tree holds a file, and the whole point of this plan is that the two baselines give different, differently-meaningful answers, so each is named by full path."

patterns-established:
  - "Fail-closed verification of a control's own failure mode: injected-drift and injected-seed-mismatch probes run against copies in the scratchpad confirm the non-zero exit path, so 'exits non-zero on failure' is measured rather than asserted"
  - "Both ruff versions in play (0.15.1 pinned by .pre-commit-config.yaml, 0.16.4 in the freeze envs) are run over new source, so a lint pass cannot be an artefact of which env was on PATH"

requirements-completed: []

coverage:
  - id: D1
    description: "ROADMAP criterion 2 — the E2 same-seed control, seed 42 vs seed 42, both baselines named in full, worst-case relative drift below 1e-6, exiting non-zero if not"
    requirement: RUN-03
    verification:
      - kind: integration
        ref: "python .planning/phases/29-gate-verification-results-commit/analyze_e2_control.py => exit 0; 27 lines carry the literal 'seed 42 vs seed 42'; pre_rerun_baseline worst scalar inter_corner_rmse_mm = 2.5146e-08, worst overall reprojection_range_px[1] = 3.6317e-08, both < DRIFT_LIMIT = 1e-6; freeze01_run_output exactly 0.0 on every field; n_comparisons EXACT EQUAL at 7762 in both comparisons; mean_per_camera_reprojection_px 0.8240385366779744 -> 0.8240385407126619 (rel 4.8962e-09)"
        status: pass
      - kind: integration
        ref: "fail-closed probe (scratchpad copies, no repo file touched): inter_corner_rmse_mm scaled by 1.001 => RESULT: FAIL, exit 1, worst case 1.0000e-03; benchmark.json seed forced to 43 => 'SEEDS DISAGREE' + 'SEED MISMATCH', no values compared, exit 1"
        status: pass
      - kind: unit
        ref: "ruff 0.15.1 (.pre-commit-config.yaml pin) and ruff 0.16.4: check + format --check on analyze_e2_control.py => both exit 0"
        status: pass
    human_judgment: false
  - id: D2
    description: "ROADMAP criterion 3 / D-29-16 — the E7 before/after sign test, both pairings across both trees, n derived from the data, p at full precision with its exact fraction"
    requirement: RUN-03
    verification:
      - kind: integration
        ref: "python .planning/phases/29-gate-verification-results-commit/analyze_e7_before_after.py => exit 0; four rows: pre_rerun_baseline fixed 10/10 crosses=False p=0.00098=1/1024 r=+0.5567, refined 8/10 crosses=True p=0.05469=56/1024 r=+0.8372; freeze-02 fixed 10/10 crosses=False p=0.00098=1/1024 r=+0.5059, refined 7/10 crosses=True p=0.17188=176/1024 r=+0.8435. All eight figures match 29-RESEARCH.md's measured table exactly, as do the four paired-diff ranges."
        status: pass
      - kind: integration
        ref: "n reported as 10 with the literal '(n = 10, derived from len(per.columns), not hard-coded)'; md5 b6515ed77ed04268608b74217716020b recorded for both freeze01_run_output and freeze-02 with 'byte-identical: True'"
        status: pass
      - kind: integration
        ref: "missing-arm probe (scratchpad CSV with percamera_refined dropped): pairing reported 'arm missing ... -- SKIPPED, not dropped', row carries skipped=True, verdict line degrades to 'SKIPPED on at least one tree -- not compared'"
        status: pass
      - kind: unit
        ref: "ruff 0.15.1 and ruff 0.16.4: check + format --check on analyze_e7_before_after.py => both exit 0"
        status: pass
    human_judgment: false
  - id: D3
    description: "The E7 refined pairing moved from 8/10 (p = 0.055) to 7/10 (p = 0.172) — both figures are published in supplement §14 / MF-05. This is the D-29-16 flag-to-author case."
    requirement: RUN-03
    verification: []
    human_judgment: true
    rationale: "D-29-16 and D-29-19 reserve every §3 and manuscript decision to the author. The measurement is automated and verified (D2); what the author does about a published digit that moved is not a decision this phase may take, and the flag is only discharged when the author has seen it."
  - id: D4
    description: "Neither result required running a stage, editing an artifact, or touching the manuscript"
    requirement: RUN-03
    verification:
      - kind: integration
        ref: "git status --porcelain experiments/ | grep -v '^??' => empty (only the nine untracked run-output paths 29-02 landed); no E2 or E7 stage invoked; no --force band run; git branch --show-current => results/rerun-freeze-02"
        status: pass
    human_judgment: false

# Metrics
duration: 25min
completed: 2026-08-26
status: complete
---

# Phase 29 Plan 03: E2 Same-Seed Control & E7 Before/After Sign Test Summary

**ROADMAP criteria 2 and 3 are both discharged from committed, re-runnable scripts: the solver reproduces its pre-run real-rig numbers at seed 42 to 2.5e-08 (stop-list item 1 does not fire), and E7's published 10-of-10 fixed-intrinsics sign test held at p = 0.00098 while the secondary refined pairing moved 8/10 → 7/10 — the D-29-16 case that must be flagged to the author.**

## Performance

- **Duration:** ~25 min
- **Started:** 2026-08-26T15:14Z (approx.)
- **Completed:** 2026-08-26T15:39Z
- **Tasks:** 2 of 2
- **Files created:** 4 (2 scripts, 2 evidence files)

## Accomplishments

- **ROADMAP criterion 2 PASSES.** `analyze_e2_control.py` compares seed 42 against seed 42 across all three trees, reading the seed from each tree's own `benchmark.json` and asserting agreement before comparing a single value. Against the pre-run baseline (Windows / aquacal 1.8.0 / `6c7f930b`) the worst scalar relative drift is **2.5146e-08** on `inter_corner_rmse_mm`; the §3 headline `mean_per_camera_reprojection_px` drifts **4.8962e-09**; `n_comparisons` is exactly equal at **7762**. Against attempt 1 (`freeze01_run_output`) every field is exactly **0.0**, because the files are byte-identical — reported and labelled explicitly as the weaker statement it is. **D-29-10 stop-list item 1 does not fire.**
- **Every one of the 27 comparison lines carries the literal `seed 42 vs seed 42`.** This is the criterion's own requirement and the reason the file is safe to quote out of context: E2's *seed* band on `mean_per_camera_reprojection_px` spans 0.761 → 0.910 px, so a cross-seed reading of these same numbers would look catastrophic.
- **ROADMAP criterion 3 discharged, and the moved conclusion raised here rather than later.** `analyze_e7_before_after.py` reports both pairings for both trees. The **primary fixed-intrinsics pairing HELD**: 10/10, no zero crossing, p = 1/1024 = 0.00098, identical before and after — FIX-02's two extra free parameters per interface did not soften it. The **secondary refined pairing MOVED**: 8/10 (56/1024 = 0.05469) → 7/10 (176/1024 = 0.17188). Both figures are published (supplement §14 / MF-05).
- **The move is dated, not merely observed.** Attempt 1 and attempt 2 share md5 `b6515ed77ed04268608b74217716020b` on `interface_ablation_band.csv`, so the 8→7 move landed *before* attempt 1 and is a Phase 23-26 (FIX-02) effect, not a re-run artefact. The evidence file says so, so nobody attributes it to the run.
- **All twelve expected figures reproduce RESEARCH exactly** — seven E2 drift values plus `n_comparisons`, and all eight E7 statistics with their four paired-diff ranges and four correlations. Nothing needed reinterpretation, and no measured value failed to reproduce.
- **Both scripts fail closed, verified by injection, not by assertion.** Scaling `inter_corner_rmse_mm` by 1.001 in a scratchpad copy drives the E2 control to `RESULT: FAIL` at exit 1; forcing a `benchmark.json` seed to 43 produces `SEEDS DISAGREE` / `SEED MISMATCH`, compares no values, and exits 1. Dropping an arm from a scratchpad E7 CSV produces `SKIPPED, not dropped`.

## Task Commits

1. **Task 1: The E2 same-seed control — seed 42 against seed 42, both baselines, named** — `8e34c6b` (feat)
2. **Task 2: The E7 before/after sign test — both pairings, both trees** — `9b94f51` (feat)

## Files Created/Modified

- `.planning/phases/29-gate-verification-results-commit/analyze_e2_control.py` — Read-only same-seed drift control over `real_rig_metrics.json` across three named trees. Module constants `BASELINE_PRERUN`, `BASELINE_FREEZE01`, `AFTER`, `SEED = 42`, `DRIFT_LIMIT = 1e-6`; functions `read_seed()`, `compare()`, `main() -> int`. Exits non-zero on seed disagreement, on any integer field differing, or on worst-case relative drift reaching `DRIFT_LIMIT`.
- `.planning/phases/29-gate-verification-results-commit/29-e2-control.txt` — Verbatim stdout of the above. Header carries all three trees' `git_sha` / `aquacal_version` / `numpy_version` / `opencv_version` / `os`, then both labelled comparisons, then an explicit `=== VERDICT ===` naming this as D-29-10 stop-list item 1. **RESULT: PASS.**
- `.planning/phases/29-gate-verification-results-commit/analyze_e7_before_after.py` — Read-only one-tailed exact paired sign test, statistic transferred verbatim from `.planning/phases/19.2-.../analyze_e7_spread.py`. Constants `METRIC`, `PAIRS`, `BEFORE`, `AFTER`, `ATTEMPT1`; functions `sign_test()`, `report()`, `_pairing_move()`, `main() -> int`.
- `.planning/phases/29-gate-verification-results-commit/29-e7-before-after.txt` — Verbatim stdout: three md5s, per-seed detail for both trees, a four-row summary table, and a `=== VERDICT ===` block whose HELD/MOVED headers are computed from the data.

## Decisions Made

1. **Both worst-case figures are reported, and the exit code gates on the stronger one.** `real_rig_metrics.json` holds three compound fields (`auxiliary_reprojection_px`, `camera_height_range_m`, `reprojection_range_px`) that RESEARCH's seven-row table did not cover. The control flattens them and reports every leaf, then prints *two* worst cases per comparison: over the top-level scalars (`inter_corner_rmse_mm` = 2.5146e-08, the criterion's headline and the figure the plan's acceptance criteria name) and over everything (`reprojection_range_px[1]` = 3.6317e-08). The PASS/FAIL decision uses the larger. Both are four orders of magnitude below `DRIFT_LIMIT`, so the verdict is unaffected — but three fields are no longer unchecked in the phase's only solver-correctness control.
2. **The seed is data, not a parameter.** `compare()` re-reads both trees' `solver_config["seed"]` itself and builds its `seed N vs seed N` stamp from what it read, so the printed statement cannot drift from the files being compared. `SEED = 42` exists only as the expectation to check against.
3. **Verdict prose is derived.** Both scripts' verdict headers and branches are computed from booleans (`ok`, `fixed_held`, `refined_moved`). This is a direct response to the analog's hard-wired `n = 5` caveat, which contradicted the domain it measured.
4. **`resolve_results_dir()` is deliberately unused.** Named paths only, per the plan's prohibition — the two baselines answer different questions and a helper that silently switches subject would erase the distinction the evidence file exists to preserve.
5. **The E7 finding is reported and stopped there.** No manuscript file was opened, read for editing, or written. The verdict block states in words that §3 edits remain the author's, per D-29-16 and D-29-19.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing critical functionality] Compound metric fields would have been silently skipped**
- **Found during:** Task 1 (E2 same-seed control)
- **Issue:** The plan's `compare()` recipe iterates top-level keys and compares "each pair of numeric values". Three of `real_rig_metrics.json`'s ten non-provenance fields are a dict or a list (`auxiliary_reprojection_px`, `camera_height_range_m`, `reprojection_range_px`) and would have fallen through unreported. In the phase's only publication-blocking correctness control, three unchecked fields is a real gap — and one of them (`reprojection_range_px[1]`, 3.6317e-08) carries the largest drift in the document.
- **Fix:** Added `_flatten()`, which expands dicts to `key.subkey` and lists to `key[i]`. Every leaf is printed with its own `seed 42 vs seed 42` stamp and a `scalar`/`compound` tag. Two worst cases are reported per comparison so the criterion's headline number (`inter_corner_rmse_mm` = 2.5146e-08, exactly as the plan's acceptance criteria specify) is preserved intact while the exit code gates on the larger overall figure.
- **Files modified:** `.planning/phases/29-gate-verification-results-commit/analyze_e2_control.py`
- **Verification:** All 12 leaves appear in `29-e2-control.txt`; the scalar worst case matches RESEARCH's table exactly; `RESULT: PASS` at exit 0 either way.
- **Committed in:** `8e34c6b` (part of Task 1 commit)

**2. [Rule 1 - Bug] Environment field names in the plan do not exist in the artifacts**
- **Found during:** Task 1 (E2 same-seed control)
- **Issue:** The plan's action text asks for the trees' `numpy` and `opencv` environment values. The actual keys in `benchmark.json`'s `environment` block are `numpy_version` and `opencv_version`; `numpy` and `opencv` both read back as `None`. RESEARCH's table used the short display names as column headings, which is where the slip originates.
- **Fix:** `ENV_FIELDS` uses the real keys. The header prints `numpy_version : 2.4.2 / 2.4.6 / 2.4.6` and `opencv_version : 4.13.0` across the three trees, matching RESEARCH's measured values.
- **Files modified:** `.planning/phases/29-gate-verification-results-commit/analyze_e2_control.py`
- **Verification:** `29-e2-control.txt` header carries non-null values for all five environment fields on all three trees.
- **Committed in:** `8e34c6b` (part of Task 1 commit)

**3. [Rule 1 - Bug] Verdict prose could contradict the table above it**
- **Found during:** Task 2 (E7 sign test), first run
- **Issue:** The first draft printed the literal headers `THE PUBLISHED PRIMARY CONCLUSION HELD` and `THE SECONDARY REFINED PAIRING MOVED` unconditionally, while computing `fixed_held` and `refined_moved` only to print them as separate lines below. On any future input those headers could state the opposite of the numbers directly above them — structurally the same defect as the analog's hard-wired `n = 5` caveat, which the plan explicitly calls out as "worse than no caveat". The verdict block also indexed `n_pos`/`p_one` on rows that may be `skipped`, which would raise `KeyError` rather than degrade.
- **Fix:** Headers now read `HELD`/`MOVED` from the computed booleans, and each branch prints text consistent with its own result. Added `_pairing_move()`, a skip-safe one-line before→after formatter used by both branches.
- **Files modified:** `.planning/phases/29-gate-verification-results-commit/analyze_e7_before_after.py`
- **Verification:** Output on the real inputs is unchanged in substance (HELD / MOVED, same numbers). Skip path exercised against a scratchpad CSV with `percamera_refined` removed: reports `SKIPPED, not dropped` and the verdict degrades to `SKIPPED on at least one tree -- not compared` without raising.
- **Committed in:** `9b94f51` (part of Task 2 commit)

**4. [Rule 3 - Blocking] `ruff` is not on PATH in the active environment**
- **Found during:** Task 1 verification
- **Issue:** The plan's `<verify>` block calls bare `ruff`; the active `aquacal` conda env has no `ruff` and no `pytest`.
- **Fix:** Used the ruff pinned by `.pre-commit-config.yaml` (`rev: v0.15.1`, resolved at `~/.cache/pre-commit/reposqwqmefs/py_env-python3.12/bin/ruff`) as the authority, and cross-checked with 0.16.4 from `aquacal-freeze02-prod`. No package was installed, no environment modified. Both versions report `All checks passed!` and `1 file already formatted` on both scripts.
- **Files modified:** None (tooling invocation only)
- **Verification:** Four clean ruff invocations, two versions × two files, plus two `ruff format` passes that reformatted the E2 script's two over-long lines before the file was committed.
- **Committed in:** n/a (no repository change)

---

**Total deviations:** 4 auto-fixed (2 × Rule 1 bug, 1 × Rule 2 missing critical functionality, 1 × Rule 3 blocking)
**Impact on plan:** All four are corrections in service of the plan's own stated intent — closing an unchecked-field gap in a stop-list control, using the field names the artifacts actually carry, preventing exactly the hard-wired-prose defect the plan warns about, and resolving a tooling-path block without touching the environment. Every measured value the plan predicted reproduced exactly. No scope creep; nothing under `experiments/` was read non-read-only, no stage was executed, no manuscript file was touched.

## Issues Encountered

**`tests/unit/test_experiments_provenance.py` reports 4 failures, not 8 — because the landed tree is untracked, not staged.** Run out of scope-curiosity for plan 29-06's benefit (this plan touches no test and no tracked artifact, so it cannot have changed the count). RESEARCH measured **8 failures** with all 227 admitted files `git add`-ed. Against the current working-clone state — tree landed by 29-02 but *untracked* — the module reports:

```
4 failed, 251 passed, 2 skipped in 23.04s
FAILED TestEnvironmentPresence::test_every_benchmark_record_has_environment[run_manifest.json]
FAILED TestSeedProvenance::test_every_benchmark_record_carries_a_seed[run_manifest.json]
FAILED TestCsvProvenanceMap::test_csv_to_record_has_no_stale_entries
FAILED TestSelfDescribingJson::test_schema_versionless_json_set_equals_self_describing_json
```

The mechanism is `_discover_csv_files()`'s `_is_tracked()` filter: with nothing staged, the CSV rails see no CSVs, so the three "missing map entry" / "band seed coverage" failures cannot fire and `test_csv_to_record_has_no_stale_entries` fires *instead* (every mapped CSV looks stale). `_discover_json_files()` has no such filter, which is why both JSON-side failures appear at both tree states. **Expect the count to change from 4 to 8 the moment plan 29-05 stages the artifacts** — the two sets are not nested and `test_csv_to_record_has_no_stale_entries` should disappear as the other three appear. Recorded here so 29-06 can distinguish "as measured" from "something new"; no repair attempted, that work is 29-06's.

Also of note: `pytest` is absent from the active `aquacal` env; the run above used `aquacal-freeze02-prod`'s interpreter. Plans 29-05/29-06 will need the same.

## User Setup Required

None — no external service configuration required. Both scripts are unprivileged, local, read-only, and take no credentials.

## Next Phase Readiness

**Ready.** Both of the phase's scientific verdicts are now committed evidence with a re-runnable provenance:

- **D-29-05's precondition is satisfied.** Grading's E2 same-seed control passes, so Record B's Zenodo draft may now be built against these numbers (plan 29-07).
- **D-29-10's stop list is two-thirds clear.** Item 1 (E2 control) PASSES here; item 2 (`gate3_git_sha_consistency`) passed in 29-02's `29-gates-full.txt`. Item 3 (§3-facing number vs. artifact) is Phase 30 / POST-01.
- **Plan 29-05 (results commit) is unblocked** and the tree is verified untouched: `git status --porcelain experiments/` shows only the nine untracked run-output paths 29-02 landed, no tracked file modified.
- **Plan 29-06 has a measured baseline** for the provenance rails (see Issues Encountered) and a prediction it can check its own starting state against.

**One item requires the author.** The E7 refined pairing's published figures moved: **8/10, p = 0.055 → 7/10, p = 0.172** (supplement §14 / MF-05). The conclusion is unchanged — the refined arm was already non-significant and is now more clearly so — and the move is attributable to FIX-02 (Phases 23-26), not to this run, since attempt 1 and attempt 2 are byte-identical on the artifact. Under **D-29-16** this is reported, not acted on; **§3 edits stay the author's**, and Phase 30 / POST-01 owns the manuscript-side half.

---
*Phase: 29-gate-verification-results-commit*
*Completed: 2026-08-26*

## Self-Check: PASSED

All 5 claimed files exist on disk; both claimed commits (`8e34c6b`, `9b94f51`) resolve in `git log`.
