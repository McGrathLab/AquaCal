---
phase: 29-gate-verification-results-commit
plan: 05
subsystem: experiments
tags: [results-commit, provenance, byte-integrity, pre-commit-hooks, gitignore, rerun-freeze-02, run-04, evidence]

# Dependency graph
requires:
  - phase: 29-gate-verification-results-commit
    provides: "Plan 29-02 landed all nine paths of the returned run in the working clone (461 files on disk) and enumerated the exact 227-path admitted set in 29-commit-manifest.txt; 29-gates-full.txt is its pre-commit gate capture, which this plan's post-commit capture is diffed against"
  - phase: 29-gate-verification-results-commit
    provides: "Plan 29-03 finished grading — the E2 same-seed control PASSES and E7's before/after sign test is discharged — so committing the run was authorised rather than premature"
  - phase: 28-full-suite-production-run
    provides: "The run itself at tag rerun-freeze-02 / 7005a2771aa115e4f4c1284cec7e145739586a4a, and commit f399615's deliberate .gitignore:507 widening that admits the 18 per-stage logs"
provides:
  - "70e783f results(29): full production suite at rerun-freeze-02 — the 227-file artifact commit on results/rerun-freeze-02, pushed to origin. This is the repository's committed evidence base for v2.1."
  - "29-gates-committed.txt — check_rerun_gates.py --profile full over the COMMITTED tree: TOTAL: 176 PASS, 7 N/A, 0 FAIL, exit 0, zero failure-verdict lines, all five Gate 3 lines PASS on the single sha 7005a277…, byte-identical to 29-02's pre-commit capture over all 185 stdout lines"
  - "Measured proof that the byte-integrity hazard stayed latent: both md5 anchors unchanged across the commit, 227 creates and zero modifications, and 143 files still carrying '\\ No newline at end of file' — exactly the 143 end-of-file-fixer would have rewritten"
  - "The three generated LaTeX fragments (benchmark_grid.tex, cpr_derived_values.tex, cpr_grouping.tex) committed beside the artifacts that produced them at a sha Gate 3 proves is single — RUN-04's traceability obligation discharged repo-side under D-29-19"
  - "A confirmed count of the D1 prediction arriving: tests/unit/test_experiments_provenance.py flips 4 failures -> 8 once the CSVs are in the index, which is plan 29-06's inbox"
affects: [29-06 provenance rail repairs, 29-07 zenodo, 29-08 phase close, 30 post-01 manuscript reconciliation]

# Actuals (#2632). NOTE ON SCALE: the 227 committed artifacts are 1,951,128 bytes of
# machine-generated output copied verbatim by plan 29-02 — not authored content, and
# counting them here (~488k) would measure the run, not this plan. `tokens` below is
# chars/4 over what this plan actually authored: the commit message body (4,183 chars),
# 29-gates-committed.txt's annotation block, and this summary.
actuals:
  tokens: 16000
  tasks: 3
  commits: 2

tech-stack:
  added: []
  patterns:
    - "A hook bypass on a scientific-artifact commit explains itself IN the commit message — an unexplained --no-verify reads as an evasion, and here it is the opposite: it is what protects the bytes"
    - "A commit message states its own file count and the arithmetic of any delta from the prior attempt, so a reviewer cannot mistake a deliberate ignore-rule widening for drift"
    - "Verify integrity by hash on named anchors, never by re-checking totals — a whitespace-only rewrite does not move a PASS/N/A/FAIL roll-up"
    - "Prove a hazard stayed latent with positive evidence (143 surviving '\\ No newline at end of file' markers), not merely with the absence of a failure"
    - "The staged set is compared path-for-path against a pre-enumerated manifest before committing, not merely counted"
    - "Evidence file = verbatim stdout captured by shell redirection, then a ruled-off 'RECORDED ASSERTIONS' block; the stdout half is never hand-edited, which is what makes the two captures diffable (carried from 29-02)"

key-files:
  created:
    - .planning/phases/29-gate-verification-results-commit/29-gates-committed.txt
  modified: []

key-decisions:
  - "Committed 227 files, not 209. D-29-17's two clauses ('commit what the existing ignore rules allow' and 'match attempt 1's shape') diverge by exactly the 18 stage logs that .gitignore:507 admits. The ignore rule is the newer and deliberate authority and D-29-17 forbids ignore-rule changes, so the rules won — and the commit message carries the arithmetic so the delta is not reconstructed later by inference."
  - "Used git commit --no-verify and said so in the message. No hook is installed in this clone, so the flag changes nothing today; it is belt-and-braces against an environment that acquires them later. The message names the byte-integrity reason explicitly."
  - "Ran exactly three hooks — check-added-large-files, detect-secrets, check-yaml — each scoped as `pre-commit run <id> --files <227 explicit paths>`. pre-commit run --all-files was never invoked; end-of-file-fixer and trailing-whitespace were never run at all, scoped or otherwise."
  - "Diffed only the stdout halves of the two gate captures (lines 1-185 of each), because lines 186+ are each plan's own annotation block and are not gate output. That diff is 0 lines — byte-identical, not merely equal on totals."
  - "Recorded 8 provenance-rail test failures as an observation and repaired nothing. The flip from 4 to 8 is the documented D1 prediction arriving, caused by _is_tracked() reading the git index; repairing it is plan 29-06's separate fix(29): commit, and mixing it in would have cost this commit its artifact-only purity."
  - "Reported actuals.tokens over authored content only, with the artifact byte volume stated in a frontmatter note. Counting 1.95 MB of copied machine output as this plan's cost would corrupt every later projection."

patterns-established:
  - "Byte anchors are read four times around a risky commit — before staging, after the scoped hook runs, immediately after the commit, and in the evidence file — so 'byte-for-byte' is a measured claim with a timeline, not a remembered one"
  - "The push is a plain push to a results branch and nothing more; no PR into main, because CI's `pre-commit run --all-files` fires only for main and would rewrite 147 artifacts there"

requirements-completed: [RUN-04]

coverage:
  - id: D1
    description: "The exact 227-path admitted set staged and verified against 29-02's pre-enumerated manifest, with only the three non-formatting hooks run against it"
    requirement: RUN-04
    verification:
      - kind: integration
        ref: "git diff --cached --name-only | wc -l => 227; grep -c '^experiments/results/' => 147; grep -c 'stagelogs/.*\\.log$' => 18; grep -vc '^experiments/' => 0; diff of sorted staged list against 29-commit-manifest.txt lines 215-441 => 0 differences"
        status: pass
      - kind: integration
        ref: "pre-commit 4.x from aquacal-freeze01 env: `pre-commit run check-added-large-files|detect-secrets|check-yaml --files <227 paths>` => all three Passed, exit 0; ls .git/hooks/ | grep -vc '\\.sample$' => 0 before and after"
        status: pass
    human_judgment: false
  - id: D2
    description: "One artifact-only results(29): commit on results/rerun-freeze-02, pushed to origin, whose body explains its own file count and its hook bypass"
    requirement: RUN-04
    verification:
      - kind: integration
        ref: "70e783f: git show --name-only --format='' HEAD | wc -l => 227; grep -c '^experiments/' => 227 (zero source, test or planning files); grep -c '^experiments/results/' => 147; git show --shortstat => 227 files changed, 40497 insertions(+), zero deletions; git log -1 --pretty=%s matches ^results\\(29\\):"
        status: pass
      - kind: integration
        ref: "commit body contains the literals 227, 147, 209, 18, f399615, .gitignore:507, 83da9b3, 7005a2771aa115e4f4c1284cec7e145739586a4a, '176 PASS, 7 N/A, 0 FAIL', and an explicit --no-verify rationale naming the byte-integrity reason"
        status: pass
      - kind: integration
        ref: "git rev-parse HEAD == git rev-parse origin/results/rerun-freeze-02 => 70e783fd8433c0d75616911d1bdd4c436c9a417e; branch still results/rerun-freeze-02; tags rerun-freeze-01=b31c802 and rerun-freeze-02=533f79f unchanged; origin/results/rerun-freeze-01 still 89c2092; no PR opened"
        status: pass
    human_judgment: false
  - id: D3
    description: "Proof after the fact that both the bytes and the single-sha property survived the commit"
    requirement: RUN-04
    verification:
      - kind: integration
        ref: "python experiments/check_rerun_gates.py experiments/results --profile full over the committed tree => TOTAL: 176 PASS, 7 N/A, 0 FAIL, exit 0, grep -c '^\\[FAIL' => 0, gate3_git_sha_consistency PASS on 7005a2771aa115e4f4c1284cec7e145739586a4a; diff against 29-gates-full.txt lines 1-185 => 0 diff lines"
        status: pass
      - kind: integration
        ref: "md5sum -c: experiments/results/real_rig_metrics.json = 57279708f6106f411d1fe03ed2698291 and experiments/results/interface_ablation_band.csv = b6515ed77ed04268608b74217716020b, both OK after the commit and identical to the pre-staging readings; git diff --quiet HEAD => exit 0"
        status: pass
      - kind: integration
        ref: "hazard-stayed-latent evidence: git show HEAD | grep -c '^\\\\ No newline at end of file' => 143 (exactly RESEARCH's predicted count); git diff --check HEAD~1 HEAD | grep -c 'trailing whitespace' => 439 advisories, nothing acted on; git show --name-only HEAD | grep -c '\\.tex$' => 3"
        status: pass
    human_judgment: false

# Metrics
duration: 12min
completed: 2026-08-26
status: complete
---

# Phase 29 Plan 05: Commit the Returned Run Summary

**The v2.1 production run is in the repository — 227 files, byte-for-byte, on `results/rerun-freeze-02` at `70e783f` and pushed to `origin` — and the post-commit gate reproduces `176 PASS, 7 N/A, 0 FAIL` on a single sha while both md5 anchors read identically to their pre-staging values.**

## Performance

- **Duration:** ~12 min
- **Tasks:** 3/3
- **Commits:** 2 (plus this summary's docs commit)

## Accomplishments

### The artifact commit — 70e783f

`results(29): full production suite at rerun-freeze-02` carries **227 files**, all under
`experiments/`, **147** of them under `experiments/results/` — matching attempt 1's 147 exactly.
227 creates, 40,497 insertions, **zero deletions and zero modifications**. No source file, no test
file and no planning document is in it.

Staging was verified against plan 29-02's pre-enumerated inventory rather than merely counted: the
sorted staged path list `diff`s to **zero differences** against `29-commit-manifest.txt`'s 227
paths. `.gitignore` and `.pre-commit-config.yaml` are untouched (D-29-17).

### The 227-vs-209 delta, explained in the commit itself

Attempt 1's `83da9b3` carried 209 files. This set is a strict superset in both directions — the
identical 209 plus **18** `run_experiment_suite_state.*.stagelogs/*.log` files, zero paths lost.
Those 18 are admitted by **`.gitignore:507`**'s `!experiments/run_experiment_suite_state.*.stagelogs/*.log`
re-inclusion, added deliberately in Phase 28 by commit **`f399615`**. The commit message states all
of that as checkable facts, so a later reviewer cannot read a deliberate ignore-rule widening as
drift or as a leak.

### The byte-integrity hazard stayed latent, and it is proven rather than assumed

The commit used **`git commit --no-verify`**, and the message says why: `end-of-file-fixer` and
`trailing-whitespace` would rewrite **147 of the 227** artifacts. Positive evidence that nothing
was rewritten:

| Check | Reading |
|---|---|
| `md5 real_rig_metrics.json` | `57279708f6106f411d1fe03ed2698291` — before staging, after the scoped hook runs, and after the commit |
| `md5 interface_ablation_band.csv` | `b6515ed77ed04268608b74217716020b` — same three readings |
| `git show --shortstat HEAD` | 227 files changed, 40497 insertions(+), **0 deletions, 0 modifications** |
| `git show HEAD \| grep -c '^\ No newline at end of file'` | **143** — exactly the count RESEARCH predicted `end-of-file-fixer` would rewrite; they went into the object store still missing their final newline |
| `git diff --check HEAD~1 HEAD \| grep -c 'trailing whitespace'` | 439 advisories about the artifacts' own bytes, added verbatim. Git warned; nothing acted |
| `ls .git/hooks/ \| grep -vc '\.sample$'` | **0**, before staging and after the commit |
| `git diff --quiet HEAD` | exit 0 |

Only three hooks were run, each scoped as `pre-commit run <id> --files <227 explicit paths>`:
`check-added-large-files` (largest admitted file 119,406 B — non-binding), `detect-secrets`,
`check-yaml`. All three **Passed**. `pre-commit run --all-files` was never invoked and the two
formatting hooks were never run at all.

### The post-commit gate — 29-gates-committed.txt

`python experiments/check_rerun_gates.py experiments/results --profile full` over the committed
tree: **`TOTAL: 176 PASS, 7 N/A, 0 FAIL`**, exit code 0, **zero** `[FAIL` lines, all five Gate 3
lines PASS including `gate3_git_sha_consistency` on the single sha
`7005a2771aa115e4f4c1284cec7e145739586a4a`. That is D-29-10 stop-list item 2 evaluated against the
**committed** tree, which is the form the stop list actually cares about.

Diffed against 29-02's pre-commit capture over both stdout halves (lines 1-185 of each file): **0
diff lines** — byte-identical, not merely equal on totals. There is no timestamp difference,
because the gate reads timestamps recorded inside the artifacts rather than the wall clock.

### RUN-04's traceability half, discharged by construction

All three generated LaTeX fragments are in the commit: `benchmark_grid.tex`,
`cpr_derived_values.tex`, `cpr_grouping.tex`, all under `experiments/results/`. §3 includes these
rather than hand-copying digits, so committing them beside the artifacts that produced them, at a
sha Gate 3 proves is single, **is** the traceability mechanism (D-29-19). No mapping document was
built — that is POST-01 in Phase 30.

## Deviations from Plan

**None — the plan executed exactly as written.** All three tasks' acceptance criteria were met on
the first attempt, with no auto-fix invoked under any deviation rule. The staged set came out at
227/147/18 on the first `git add`, all three scoped hooks passed first time, and the post-commit
gate reproduced the pre-commit capture byte for byte.

## Observations (recorded, deliberately not acted on)

- **The D1 prediction arrived, exactly as documented.**
  `tests/unit/test_experiments_provenance.py` now reports **8 failed, 279 passed, 20 skipped**
  — up from 4 failures — because `_is_tracked()` reads the git *index*, so the CSVs became visible
  to the provenance rails only once staged. The four new failures are
  `TestCsvProvenanceMap::test_all_committed_csvs_have_a_named_record` on
  `generalization_sweep_per_camera.csv` and `generalization_sweep_per_camera_band.csv`, and
  `test_multi_seed_band_declares_its_seed_coverage` on `exp1_band.csv`,
  `exp1_parameter_band.csv` and `generalization_sweep_per_camera_band.csv`, alongside
  `TestSelfDescribingJson::test_schema_versionless_json_set_equals_self_describing_json`.
  **Nothing was repaired, deselected, xfailed or skipped** — that is plan 29-06's separate
  `fix(29):` commit, and keeping it out is what leaves this commit artifact-pure.

- **The PR-into-`main` constraint is live and carried forward.** CI's `pre-commit run --all-files`
  fires on pushes to and PRs against `main`. Opening a PR from `results/rerun-freeze-02` would
  rewrite 147 artifacts there. No PR was opened; attempt 1's branch was never merged either. This
  is a Phase 30 concern, noted rather than solved.

- **`check-added-large-files` remains non-binding by measurement**, not by assumption: the largest
  admitted file anywhere in the set is `interface_ablation_band.csv` at 119,406 bytes, well under
  `--maxkb=1000`. The ~11 MB `all_observation_depths.csv` is already ignored by `.gitignore:478`.

- **The 234 gitignored files** are recorded by `~/rerun-freeze-02-output.tar.gz`
  (sha256 `3b21b88323bd7c04e9712ae2742cc09d423f925620e729ea7bbe2d391c9f030e`) and ship via Zenodo
  Record B. 227 + 234 = 461 reconciles exactly with `28-RUN-RECORD.md`.

## Refs Asserted Unchanged

| Ref | Value |
|---|---|
| tag `rerun-freeze-01` | `b31c8020403c11609b1fea5d330c29b58d902914` |
| tag `rerun-freeze-02` | `533f79fbe1bf7022466e341cb4a4921f1e2575a5` |
| `origin/results/rerun-freeze-01` | `89c20923e098ec3f521a1d4e31272ebe24ae56ea` |
| branch | `results/rerun-freeze-02` (never changed) |
| `~/aquacal-frozen-rerun-freeze-02-prod` | not touched; nothing committed from it |

## Commits

| Commit | Subject | Files |
|---|---|---|
| `70e783f` | `results(29): full production suite at rerun-freeze-02` | 227 artifact paths under `experiments/` |
| `da86892` | `docs(29-05): record the post-commit gate re-run and byte anchors` | `29-gates-committed.txt` |

`git rev-parse origin/results/rerun-freeze-02` = `70e783fd8433c0d75616911d1bdd4c436c9a417e` at push
time — plain push, never forced.

## Known Stubs

None. No placeholder, TODO or unwired data path was introduced; this plan authored one evidence
file and one commit message.

## Next

Plan **29-06** — repair the eight `tests/unit/test_experiments_provenance.py` assertions in their
own `fix(29):` commit. D-29-13 fixes assertions, never artifacts.

## Self-Check: PASSED

- `29-05-SUMMARY.md` — FOUND
- `29-gates-committed.txt` — FOUND
- commit `70e783f` — FOUND
- commit `da86892` — FOUND
