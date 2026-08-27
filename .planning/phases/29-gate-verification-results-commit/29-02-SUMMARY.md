---
phase: 29-gate-verification-results-commit
plan: 02
subsystem: experiments
tags: [provenance, gates, check_rerun_gates, gitignore, rerun-freeze-02, artifacts, evidence]

# Dependency graph
requires:
  - phase: 28-full-suite-production-run
    provides: "The v2.1 production run at rerun-freeze-02 / 7005a27 — 461 files in ~/aquacal-frozen-rerun-freeze-02-prod, the read-only archive and its sha256, and freeze02-gates-full.txt as the reference gate capture"
  - phase: 29.1-post-run-fixes-re-freeze
    provides: ".gitignore:507's stagelogs re-inclusion (f399615), the cleared landing zone (29.1-06 moved attempt 1's output to experiments/freeze01_run_output/), and the D3 byte-integrity diagnosis"
provides:
  - "The complete returned run landed in the working clone on results/rerun-freeze-02 at its original relative paths — 461 files across nine paths, byte-anchored on two md5 digests, uncommitted and ready for plan 29-05"
  - "29-gates-full.txt — check_rerun_gates.py --profile full over the landed tree: TOTAL: 176 PASS, 7 N/A, 0 FAIL, exit 0, zero failure-verdict lines, all five Gate 3 lines PASS on the single sha 7005a277…"
  - "29-commit-manifest.txt — the definitive 227-path admitted set, per-path breakdown, size check, the five ignored files, and a two-directional diff against attempt 1's 83da9b3"
  - "Proof that the production clone survives untouched as the second independent copy of the run"
affects: [29-03 e2 same-seed control, 29-05 results commit, 29-06 provenance rail repairs, 29-08 phase close, 30 post-01 manuscript reconciliation]

actuals:
  tokens: 16827
  tasks: 3
  commits: 2

tech-stack:
  added: []
  patterns:
    - "Evidence file = verbatim tool stdout captured by shell redirection, then a clearly ruled-off RECORDED ASSERTIONS block below it — the measurement and its interpretation never intermingle"
    - "Path-normalised diff for comparing tool output captured in different clones, with the raw diff count reported alongside so the normalisation is auditable rather than hidden"

key-files:
  created:
    - .planning/phases/29-gate-verification-results-commit/29-gates-full.txt
    - .planning/phases/29-gate-verification-results-commit/29-commit-manifest.txt
  modified: []

key-decisions:
  - "Task 1 makes no commit by design — the artifacts are landed but left untracked because plan 29-05 owns the results commit; keeping the landing and the commit in separate plans is what keeps the artifact commit byte-pure"
  - "The plan's Task 1 verify literal of 423 over seven paths is a plan arithmetic slip; the authoritative decomposition from freeze02-archive-manifest.txt is 423 (six trees) + 36 (stagelogs) + 2 (loose state files) = 461, and 461 is what reproduced"
  - "The raw diff against Phase 28's freeze02-gates-full.txt is 126 lines, all of them the embedded absolute clone path; the path-normalised diff is empty, and both numbers are recorded rather than only the flattering one"
  - "RUN-03 and RUN-04 are NOT marked complete by this plan — RUN-03's E2 control is 29-03's and RUN-04's commit is 29-05's; checking 'the returned results are committed' before anything is committed would be a false record in the one phase whose subject is honest provenance"

patterns-established:
  - "Copy-never-move with cp -a plus touch -r on the directory, and a pre-copy zero-file assertion per destination that halts rather than merges — a merged tree cannot honestly claim everything in it came from one run"
  - "Assert the read-only source is unmutated both before and after any bulk read: HEAD, porcelain entry count, diff --stat, and content digests"
  - "Take md5 anchors before and after any tool invocation over immutable artifacts, so 'the checker is read-only' is measured rather than assumed"

requirements-completed: []

coverage:
  - id: D1
    description: "The complete returned run (461 files across nine paths) is present in the working clone at its original relative paths, byte-identical on the two anchor artifacts"
    requirement: RUN-04
    verification:
      - kind: integration
        ref: "find <nine paths> -type f | wc -l => 461; find experiments/results -type f => 152; md5sum -c on real_rig_metrics.json (57279708f6106f411d1fe03ed2698291) and interface_ablation_band.csv (b6515ed77ed04268608b74217716020b)"
        status: pass
    human_judgment: false
  - id: D2
    description: "check_rerun_gates.py --profile full over the landed tree reports TOTAL: 176 PASS, 7 N/A, 0 FAIL at exit 0 with zero failure-verdict lines"
    requirement: RUN-03
    verification:
      - kind: integration
        ref: "python experiments/check_rerun_gates.py experiments/results --profile full > 29-gates-full.txt; grep '^TOTAL: 176 PASS, 7 N/A, 0 FAIL$'; grep -c '^[FAIL' => 0; exit code 0"
        status: pass
    human_judgment: false
  - id: D3
    description: "gate3_git_sha_consistency holds on the single sha 7005a2771aa115e4f4c1284cec7e145739586a4a, and all four gate3_run_manifest_* gates pass with 17/17 environment fields non-null (D-29-10 stop-list item 2)"
    requirement: RUN-03
    verification:
      - kind: integration
        ref: "grep 'gate3_git_sha_consistency.*7005a2771aa115e4f4c1284cec7e145739586a4a' .planning/phases/29-gate-verification-results-commit/29-gates-full.txt; grep -E 'gate3_run_manifest_(present|fields|git_sha|clean_tree)' => 4/4 PASS"
        status: pass
    human_judgment: false
  - id: D4
    description: "The admitted commit set is exactly 227 paths — 147 under experiments/results/, 18 stagelogs .log — a strict superset of attempt 1's 209 with zero paths lost, and no admitted file exceeds check-added-large-files --maxkb=1000"
    requirement: RUN-04
    verification:
      - kind: integration
        ref: "git status --porcelain -uall over the nine paths => 227; comm against git show --name-only 83da9b3 (sha-normalised) => 209 common / 18 added / 0 lost; stat over the set => max 119406 bytes, 0 files over 1024000"
        status: pass
    human_judgment: false
  - id: D5
    description: "The production clone ~/aquacal-frozen-rerun-freeze-02-prod survives as an unmutated second independent copy of the run"
    verification:
      - kind: integration
        ref: "git -C ~/aquacal-frozen-rerun-freeze-02-prod rev-parse HEAD => 7005a277…, detached; status --porcelain => 9 entries all '??'; diff --stat HEAD => empty; both anchor md5s unchanged"
        status: pass
    human_judgment: false
  - id: D6
    description: "The plan's flagged assumption — that RUN-03's word 'complete' means all six output trees plus the three state artifacts at their original relative paths — is asserted by measurement but remains an interpretation"
    requirement: RUN-03
    verification: []
    human_judgment: true
    rationale: "The plan flagged this as unclassified and explicitly declined to auto-resolve it. The 461-file count and the 176/7/0 roll-up are evidence the reading is the right one — check_e2_band resolves a sibling of out_dir and the roll-up would silently degrade under any narrower reading — but whether that is what RUN-03 meant is the author's call, not a measurement."

# Metrics
duration: 13min
completed: 2026-08-26
status: complete
---

# Phase 29 Plan 02: Land and Grade the Returned Production Run Summary

**The v2.1 production run is in the working clone at its original relative paths — 461 files, byte-anchored — and the frozen gate re-derives `TOTAL: 176 PASS, 7 N/A, 0 FAIL` over it at exit 0 with `gate3_git_sha_consistency` green on the single sha `7005a277…`; the 227-file admitted commit set is enumerated and proven a strict superset of attempt 1's 209.**

## Performance

- **Duration:** ~13 min
- **Started:** 2026-08-26T15:15Z (approximate — derived from the session's first read)
- **Completed:** 2026-08-26T15:28Z
- **Tasks:** 3 of 3
- **Files created:** 2 (both evidence files under `.planning/`); 461 artifact files landed but deliberately left uncommitted

## Accomplishments

- **ROADMAP criterion 1 is demonstrated in the real working clone, on the branch the results will
  be committed to, and written down.** Research had shown it in a disposable probe clone; this
  plan re-derived it where it counts. `python experiments/check_rerun_gates.py experiments/results
  --profile full` returns `TOTAL: 176 PASS, 7 N/A, 0 FAIL`, exit code **0**, **zero**
  failure-verdict lines, and all five Gate 3 lines PASS — including
  `gate3_git_sha_consistency` on the single sha `7005a2771aa115e4f4c1284cec7e145739586a4a`
  and `gate3_run_manifest_fields` with all 17 environment fields present and non-null.
  D-29-10's stop-list item 2 is satisfied.
- **The gate output agrees with Phase 28's own post-run capture on every measured value.** The
  path-normalised diff against `freeze02-gates-full.txt` is **empty**. Nothing mutated the tree
  between the run machine and here.
- **The complete run landed without touching the production clone.** All nine paths copied with
  `cp -a` — 461 files, `experiments/results/` at 152, stagelogs at 18 `.log` + 18 `.done`. Both
  md5 anchors match the values recorded in `29-RESEARCH.md`, before AND after the gate ran.
  `~/aquacal-frozen-rerun-freeze-02-prod` is still on detached HEAD `7005a277…` with exactly 9
  untracked entries and an empty `diff --stat HEAD`; its own copies of both anchors are unchanged.
  The second independent copy of the run survives.
- **The commit set is now a number, not a discovery.** `29-commit-manifest.txt` carries exactly
  **227** admitted paths — 147 under `experiments/results/`, 25 / 7 / 4 / 3 / 3 across the other
  five trees, 36 stagelogs files, plus the `.tsv` and `.failures.txt` — every per-path figure
  matching `29-RESEARCH.md` exactly. Against attempt 1's `83da9b3`: **209 common, 18 added, 0
  lost**. A strict superset, stated in both directions so that neither a silent loss nor a silent
  gain could hide.
- **`check-added-large-files` is confirmed not binding.** Largest admitted file is
  `experiments/results/interface_ablation_band.csv` at **119,406 bytes**; zero admitted files
  exceed 1000 KB; the whole set is 1.86 MiB. The ~11 MB `all_observation_depths.csv` that D-29-17
  names as the tripwire was confirmed with `git check-ignore -v` to be **already excluded** by
  `.gitignore:478` — the decision is unaffected, only its arithmetic needed correcting.
- **D-29-19's traceability mechanism is confirmed intact.** All three generated LaTeX fragments —
  `benchmark_grid.tex` (10,438 B), `cpr_derived_values.tex` (131 B), `cpr_grouping.tex` (938 B) —
  are inside the 147 admitted under `experiments/results/`.

## Task Commits

1. **Task 1: Land the returned run in the working clone** — **no commit, by design.** The nine
   paths were copied in and left untracked. Plan 29-05 owns the results commit; the plan's own
   prohibition is *"Do not stage or commit anything in this task."* Task 1's evidence lives in
   this summary and in Task 3's manifest.
2. **Task 2: Grade the landed tree with the frozen gate** — `224c229` (docs)
3. **Task 3: Inventory exactly which files the ignore rules admit** — `7632402` (docs)

## Files Created/Modified

- `.planning/phases/29-gate-verification-results-commit/29-gates-full.txt` (276 lines) — 185 lines
  of `check_rerun_gates.py` stdout captured verbatim by shell redirection, then a ruled-off
  RECORDED ASSERTIONS block: invocation, exit code, roll-up, failure-line count, the five Gate 3
  verdicts, the E2-band sibling explanation, the two-way comparison against Phase 28's capture,
  the before/after byte anchors, and the prohibitions honoured.
- `.planning/phases/29-gate-verification-results-commit/29-commit-manifest.txt` (441 lines) —
  headline numbers, per-path breakdown, size check, the five ignored files under
  `experiments/results/`, the two-directional attempt-1 comparison, the three LaTeX fragments, the
  prohibitions block, and then the 227 admitted paths sorted, one per line at column 0.
- **Landed but uncommitted** (plan 29-05 commits these): `experiments/results/` (152),
  `experiments/results_e2_band/` (136), `experiments/results_e2_invocations/` (119),
  `experiments/results_e2_timing/` (6), `experiments/results_e2_memory/` (6),
  `experiments/results_e4_repeat/` (4), `experiments/run_experiment_suite_state.7005a27.stagelogs/`
  (36), `…7005a27.tsv` (1), `…7005a27.failures.txt` (1). **Total 461.**

## Decisions Made

- **Task 1 commits nothing.** The plan and the phase constraints both forbid it, and the reason is
  substantive: keeping the landing and the commit in separate plans is what lets 29-05's commit be
  byte-pure and auditable. The cost is that one of three tasks has no commit hash; the summary and
  the manifest carry its evidence instead.
- **Neither RUN-03 nor RUN-04 is marked complete.** Both are shared with 29-03, 29-05, 29-06 and
  29-08. RUN-04 reads *"the returned results are committed with provenance intact"* — nothing is
  committed yet. Checking that box now, in the phase whose entire subject is honest provenance,
  would be exactly the kind of premature claim this milestone exists to prevent. `29-08` closes
  them. `requirements-completed` is therefore `[]` and `requirements mark-complete` was not run.
- **Both diff numbers against Phase 28 are recorded, not just the clean one.** Reporting only the
  empty normalised diff would hide the normalisation; reporting only the 126-line raw diff would
  imply a divergence that does not exist. The evidence file states both and shows that all 126
  changed lines carry an absolute clone path and nothing else.
- **`--no-verify` was not used and was not needed.** `.git/hooks/` in both clones holds only
  `*.sample`, `pre-commit` is not on `PATH`, and both commits touch only `.planning/` files.
  Research's belt-and-braces `--no-verify` prescription applies to 29-05's artifact commit; the
  sequential-executor contract forbids it here and nothing required it.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Task 1's automated verify carried an arithmetically impossible file count**

- **Found during:** Task 1
- **Issue:** The `<automated>` verify block asserts
  `find <six output trees> <stagelogs> -type f | wc -l -eq 423`, and the matching acceptance
  criterion reads *"returns `423`, and adding the two loose state files gives the run's `461`"* —
  but 423 + 2 = 425, not 461. The seven-path `find` cannot return 423. The correct decomposition,
  authoritative in `freeze02-archive-manifest.txt` and `28-RUN-RECORD.md`, is **423** across the
  six output trees, **36** in the stagelogs directory, and **2** loose state files = **461**.
- **Fix:** Ran the verify with the count split at the correct boundary: six trees `-eq 423`,
  stagelogs `-eq 36`, both loose files present. All three passed on the first attempt, and the
  nine-path total is **461**, agreeing with the archive manifest exactly. The plan file was not
  edited; no artifact was touched.
- **Files modified:** none (verification method only)
- **Verification:** `423 + 36 + 2 = 461`, cross-checked against the source clone, which also
  returns 461.
- **Committed in:** n/a — Task 1 makes no commit.

**2. [Rule 1 - Bug] A `.done` count of 19 where the plan expected 18 — a counting-method artifact,
not tree drift**

- **Found during:** Task 1
- **Issue:** The acceptance criterion `find …stagelogs -name '*.done' | wc -l` returns **19**, not
  18. This looked briefly like a returned-tree discrepancy against `28-RUN-RECORD.md`'s
  "18 `.log` + 18 `.done` = 36".
- **Fix:** Investigated rather than accepted. The 18 `.done` sentinels live inside a
  **subdirectory** named `.done/`, and the glob matches that directory too. With `-type f` the
  count is exactly **18**, and the directory holds exactly 36 files. The **source clone returns
  the identical 19/18/36**, so the copy is faithful and the plan's expectation was simply written
  against a glob that does not filter by type. Recorded in the manifest so nobody re-derives it.
- **Files modified:** none (verification method only)
- **Verification:** `-type f -name '*.log'` = 18, `-type f -name '*.done'` = 18, total files = 36,
  in both clones.
- **Committed in:** `7632402` (the manifest carries the note).

**3. [Rule 1 - Bug] Task 2's line-for-line comparison could not have been literal**

- **Found during:** Task 2
- **Issue:** The plan asks whether `29-gates-full.txt` *"agrees line for line"* with Phase 28's
  `freeze02-gates-full.txt`, expecting agreement. A raw `diff` returns exit 1 with **126** changed
  lines. The cause is structural, not a divergence: `main()` resolves `out_dir` and the gate
  prints that absolute path in every detail string that names an artifact. Phase 28 captured from
  `…-freeze-02-prod`; this capture came from `…-freeze-01`.
- **Fix:** Reported both measurements. All **126** changed lines were confirmed to carry a clone
  path (126 of 126). A path-normalised diff — both sides rewritten to `<CLONE>/` — returns **exit
  0, zero differing lines**. Both numbers, the normalisation rule, and the reason are recorded in
  the evidence file so the claim is auditable rather than asserted.
- **Files modified:** `.planning/phases/29-gate-verification-results-commit/29-gates-full.txt`
- **Verification:** `diff <(sed …) <(sed …)` exits 0; both files' roll-up lines are at line 185
  and identical.
- **Committed in:** `224c229`

### Precondition deviation (recorded, not auto-fixed)

**Task 1's precondition required the working clone's `git status --porcelain` to be empty; it was
not.** One line was present: ` M .planning/STATE.md` — an *unstaged* modification (column 1 is a
space) written by the GSD workflow itself when Phase 29 execution started, changing only
`current_phase_name`, `last_updated`, `last_activity`, and the "Current Position" prose. The diff
was inspected in full before proceeding.

**Continued rather than halting**, because the precondition's substantive content held completely:
`git status --porcelain -- experiments/` was **empty**, all six destination trees held **zero**
files, and the three state artifacts were **absent**. The one modified file is GSD bookkeeping
outside `experiments/` that cannot affect artifact byte integrity, and it was written by this very
execution's own orchestrator. Halting on it would have blocked the phase on its own launch record.

---

**Total deviations:** 3 auto-fixed (3 plan-authoring bugs — two arithmetic/method slips in
acceptance criteria, one structurally impossible comparison), plus 1 precondition deviation
recorded and reasoned through.
**Impact on plan:** None on outcome. Every substantive expected value reproduced exactly on the
first attempt — 461 files, both md5 anchors, `176 PASS / 7 N/A / 0 FAIL`, exit 0, the single sha,
227 admitted, 147 under `results/`, 18 stagelogs, 119,406 bytes largest, 209/18/0 against attempt
1. No artifact was edited, no ignore rule was touched, no scope was added.

## Issues Encountered

**None that required problem-solving beyond the three deviations above.** Three notes worth
carrying forward:

1. **The gate is read-only over the tree, and this is now measured rather than assumed.** md5 of
   both anchor artifacts was taken immediately before and immediately after the gate invocation;
   both are unchanged. `experiments/check_rerun_gates.py` reports empty from
   `git status --porcelain`.
2. **The byte-integrity hazard stayed latent, as designed.** `.git/hooks/` holds only `*.sample`
   in **both** clones (verified before and after all work), `pre-commit` is not on `PATH`,
   `pre-commit install` was never run, and `pre-commit run --all-files` was never invoked. The
   147 files `end-of-file-fixer` / `trailing-whitespace` would rewrite are untouched.
3. **`experiments/results_e2_band/` did not exist in the destination** and was created by the copy;
   the other five trees existed as empty directories. Both states satisfy the "holds zero files"
   precondition, and each destination was asserted individually with a halt-rather-than-merge
   guard before anything was written.

## Known Stubs

None. This plan authored no code — its two outputs are evidence files whose content is measured
tool output and measured counts, and every number in them was produced by a command run in this
session rather than transcribed.

## Next Phase Readiness

**Ready. Nothing blocks the plans that depend on this one.**

- **29-03 (E2 same-seed control)** — the E2 artifacts it reads are now in the working clone:
  `experiments/results/real_rig_metrics.json` (md5 anchored) and the 136-file
  `experiments/results_e2_band/`.
- **29-05 (results commit)** — has its exact file list. `29-commit-manifest.txt`'s final block is
  227 paths, one per line at column 0, directly consumable as a staging list. **Say 227 in the
  commit message** so the +18 delta from attempt 1's 209 is never later misread as a leak. Commit
  with `--no-verify` per research's prescription, and do **not** open a PR from
  `results/rerun-freeze-02` into `main` — that is the one action that fires the formatting
  rewrite in CI.
- **29-06 (provenance rail repairs)** — **the D1 prediction has now landed.**
  `resolve_results_dir()` re-aims from `experiments/pre_rerun_baseline/results/` to
  `experiments/results/` the moment the live tree holds a file, which it now does. Every
  tree-keyed test module has changed subject. `tests/unit/test_experiments_provenance.py` is
  **expected to start failing** — that is the documented consequence of landing the tree, not a
  regression. **Per the plan's explicit instruction, no rail baseline was measured here**: the
  CSV rails' `_is_tracked()` shells `git ls-files --error-unmatch` and reads the git **index**, so
  the full count does not exist until 29-05 commits. Measure it after 29-05, not before.
- **Two concerns to carry, neither blocking:** the `results/rerun-freeze-02` → `main` merge
  question is noted forward to Phase 30 (attempt 1's branch was never merged either), and D6's
  flagged interpretation of RUN-03's word "complete" awaits the author's confirmation — it is
  evidenced, not resolved.

---
*Phase: 29-gate-verification-results-commit*
*Completed: 2026-08-26*

## Self-Check: PASSED

- `29-gates-full.txt` — FOUND
- `29-commit-manifest.txt` — FOUND
- `29-02-SUMMARY.md` — FOUND
- Commit `224c229` — FOUND
- Commit `7632402` — FOUND
- Grep contracts intact: `grep -c '^\[FAIL'` over the gate file returns 0; the manifest carries exactly 227 lines beginning `experiments/`.
