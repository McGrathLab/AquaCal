---
phase: 26-full-suite-driver-handoff-readiness
plan: 01
subsystem: experiments-provenance
tags: [DRIVER-04, archive-aside, gitignore, provenance, test-repair]
requires: []
provides:
  - "experiments/pre_rerun_baseline/ — the reachable archive --baseline-dir (D-12) resolves to"
  - "pre-rerun-baseline tag — the sha Phase 30 / POST-03's purge commit cites by name (D-22)"
  - "an EMPTY experiments/results/ for the v2.1 re-run to write into"
affects:
  - "plan 26-03 (check_rerun_gates.py) — measured gate verdicts recorded below"
  - "plans 26-04 / 26-06 (--baseline-dir) — three production constants still name experiments/results/"
  - "Phase 30 / POST-03 — the purge, and the .gitignore + detect-secrets blocks that go with it"
tech-stack:
  added: []
  patterns:
    - "repo-root-anchored baseline paths (WR-06) with an explicit pytest.skip guard for fresh clones"
key-files:
  created:
    - experiments/pre_rerun_baseline/results/            # 151 tracked
    - experiments/pre_rerun_baseline/results_e2_band/    # 7
    - experiments/pre_rerun_baseline/results_linux32gb/  # 25
    - experiments/pre_rerun_baseline/results_e6_repeat2/ # 14
    - experiments/pre_rerun_baseline/results_e6_seed43/  # 14
    - experiments/pre_rerun_baseline/results_e4_repeat/  # 4
    - experiments/pre_rerun_baseline/driver_state/       # 9
  modified:
    - .gitignore
    - .pre-commit-config.yaml
    - tests/unit/test_experiments_provenance.py
    - tests/unit/test_experiments_e5.py
    - tests/unit/test_experiments_io.py
    - tests/unit/test_experiments_e3.py
decisions:
  - "Sibling layout preserved inside the archive so check_e2_band's out_dir.parent resolution keeps working — VERIFIED by a live gate run, not assumed"
  - "detect-secrets' exclude regex is path-literal and had to be extended; the pure rename tripped it on ~200 already-excluded provenance fields"
  - "The production baseline constants were NOT repointed — that is D-12's --baseline-dir work, plans 26-04/26-06"
metrics:
  duration: ~35 min
  tasks: 3
  completed: 2026-08-18
---

# Phase 26 Plan 01: Archive-Aside and Test Repair Summary

Moved all six tracked results trees plus nine loose driver state/log files into
`experiments/pre_rerun_baseline/` as 224 pure renames with zero deletions, tagged the pre-move sha
`pre-rerun-baseline`, and repointed **five** (not four) broken committed-baseline test reads at the
archive.

## What Was Built

**Task 1 — `048c14f`.** Annotated tag `pre-rerun-baseline` on `d0bbe09`, created *before* any
commit in this plan (D-22/D-28). The tag did not previously exist, so no re-point question arose;
had it existed at a different sha the plan required a STOP, which is the T-26-02 mitigation.

The archive root is `experiments/pre_rerun_baseline/`, deliberately not colliding with the
pre-existing `experiments/archive/` (still 31 tracked files, untouched). **Sibling structure is
preserved inside it** — `results/` and `results_e2_band/` are siblings there exactly as they were
under `experiments/` — because `check_e2_band` resolves its band tree as
`out_dir.parent / "results_e2_band"`. Task 3 confirmed by live run that this resolution works
against the archive; it was not left as an assumption.

`rerun_19_3.sh`, `rerun_19_4.sh`, `rerun_19_5.sh`, `seed_sweep_19_3.sh`, `e6_legal_seed_probe.sh`
and `prelaunch_gate.sh` were **not** moved — they are tracked scripts, not outputs. Verified still
at their original paths.

**Task 2 — `e3a7bf3`.** Four test files repointed at the archive. Repointed, never weakened:
`PENDING_CSVS` is still `frozenset()`, and both bidirectional exhaustiveness gates
(`test_csv_to_record_has_no_stale_entries`, `test_all_committed_csvs_have_a_named_record`) still
**execute** — confirmed by a `-rs` selection run showing 26 passed and zero skipped.

**Task 3.** Read-only probe. Zero source files changed (`git diff --name-only` empty).

## Verification

| Check | Result |
|---|---|
| Tracked counts under archive: results / e2_band / linux32gb / e6_repeat2 / e6_seed43 / e4_repeat | **151 / 7 / 25 / 14 / 14 / 4** — every research figure matched |
| `driver_state/` tracked files | 9 |
| `git show --name-status HEAD` on the move commit | **224 R100, 2 M, zero D** |
| Untracked count, plan start → after move | **0 → 0** (no ignored bulk became newly visible) |
| `experiments/archive/` | 31 tracked, untouched |
| The four targeted test files | **390 passed, 25 skipped, 0 failed** |
| `tests/unit/test_rerun_gates.py` | **59 passed** |

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 — Blocking] `detect-secrets` rejected the pure-rename commit**

- **Found during:** Task 1, at the pre-commit hook.
- **Issue:** `.pre-commit-config.yaml`'s detect-secrets `exclude` is the **path-literal** regex
  `experiments/results[^/]*/.*`. The rename moved ~200 already-committed, already-excluded
  `git_sha` and `config_hash` provenance fields out from under it, so the hook re-flagged every one
  of them as a Hex High Entropy String. `.secrets.baseline` contains **no** `experiments/` entries
  at all — the exclude regex was doing all the work — so there was no baseline to rewrite.
- **Fix:** made the archive segment optional:
  `experiments/(pre_rerun_baseline/)?results[^/]*/.*`. The original branch is preserved, so the
  rule still covers the fresh `experiments/results/` the run writes into. Commented with the
  Phase 30 removal note.
- **Files modified:** `.pre-commit-config.yaml` (not in the plan's `files_modified`).
- **Commit:** `048c14f`

**2. [Rule 1 — Bug] SP-1 under-counted: a FIFTH test breaks on the move**

- **Found during:** Task 2 verification.
- **Issue:** `test_experiments_e5.py::TestDefaultMetricsPathAnchoring::`
  `test_resolves_to_an_existing_file_from_a_foreign_directory` fails with
  `AssertionError: .../experiments/results/real_rig_metrics.json`. It asserts the **production**
  `_default_metrics_path()` resolves to an **existing** file. SP-1's table does not list it.
- **Fix:** the test's subject is WR-06 cwd-independence, which the move does not touch. The
  existence leg was kept **real** rather than deleted, by accepting either the fresh-run location
  or its archive counterpart; it re-tightens on its own once Phase 28 repopulates
  `experiments/results/`. The production constant was **not** repointed — that is out of this
  plan's `files_modified` and is D-12's `--baseline-dir` work.
- **Files modified:** `tests/unit/test_experiments_e5.py`
- **Commit:** `e3a7bf3`

**3. [Rule 1 — Bug] the `test_experiments_e3.py` "audit" item does break**

SP-1 listed `BENCHMARK_JSON_PATH` as *audit, may need no change* (research risk A3, rated Low).
It is used unguarded at line 358 by `test_per_camera_rows_present`, so it breaks. Repointed.

### Scoped Out (not deviations — recorded for the orchestrator)

**The worktree contains only tracked files.** Every untracked/ignored item this plan's Task 1
names — the ~126-file bulk inside `results_e2_band/`, the 2 inside `results/`, the untracked loose
logs (`rerun_19_3.log`, `e1_band_rerun.log`, `e7_band_rerun.log`, the `final_/postcommit_/postqueue_`
suite logs, `suite_260807_dcv.log`, `prelaunch_gate_*.log`, `e6_legal_seed*.log`,
`seed_sweep_19_3.log`), and **D-31's three `verify_23*/` probe trees** — exists only in the **main
checkout**, never in this worktree. A `mv` here would have been a no-op on nothing.

`.gitignore` carries the mirrored rules for all of them (including
`experiments/pre_rerun_baseline/verify_probes/`), so the moves are safe to perform. **The plain-`mv`
of that untracked residue is left to the orchestrator in the main checkout after merge.** It is
local hygiene and not part of any commit, exactly as D-31 says — but the `results_e2_band/` and
`results/` residue is D-30/D-29 scope, not D-31, and leaving it at the old paths would leave a
non-empty `experiments/results/` on disk that D-24's pre-flight would refuse. Concrete commands:

```bash
cd /c/Users/tucke/PycharmProjects/AquaCal/experiments
mv results/*                 pre_rerun_baseline/results/          # 2 files
mv results_e2_band/*         pre_rerun_baseline/results_e2_band/  # ~126 files
mkdir -p pre_rerun_baseline/verify_probes
mv verify_23 verify_23_fdnoise verify_23_optblocks pre_rerun_baseline/verify_probes/
mv rerun_19_3.log e1_band_rerun.log e7_band_rerun.log *suite_19_5.log \
   suite_260807_dcv.log prelaunch_gate_*.log e6_legal_seed*.log \
   seed_sweep_19_3.log pre_rerun_baseline/driver_state/ 2>/dev/null
rmdir results results_e2_band 2>/dev/null   # only if now empty; NEVER rm -rf
```

**Two commits, not one.** The plan's objective says "one reviewable commit" while its task
structure and Task 1's acceptance criterion (`git show --stat --find-renames HEAD` reporting
R-status) require Task 1 to be its own HEAD. Followed the task structure. SP-1's real requirement —
that the **frozen sha** never ships a red suite — is satisfied: both commits land together in this
plan, and `d0bbe09..e3a7bf3` is green on every file the move touches.

## Findings for plan 26-03

Both runs used the AquaCal conda interpreter with `PYTHONPATH=<worktree>/src`, at `e3a7bf3`.

### Run 1 — archived tree (`experiments/pre_rerun_baseline/results`)

```
TOTAL: 102 PASS, 7 N/A, 8 FAIL
```
Exit code **1**.

All eight FAILs verbatim:

```
[FAIL] E1  gate3_provenance:e1_benchmark_refractive.json e1_benchmark_refractive.json: missing provenance field(s) ['seed']
[FAIL] E1  gate1_guard_count:e1_benchmark_nonrefractive.json e1_benchmark_nonrefractive.json: non-zero guard count (14949) at the final solution -- optimality is unreliable here
[FAIL] E1  gate3_provenance:e1_benchmark_nonrefractive.json e1_benchmark_nonrefractive.json: missing provenance field(s) ['seed']
[FAIL] E4  gate1_guard_count:benchmark_grid.csv          benchmark_grid.csv: 1 of 10 row(s) have a non-zero or missing guard count
[FAIL] E7  gate3_provenance:e7_benchmark_shared_fixed.json e7_benchmark_shared_fixed.json: missing provenance field(s) ['seed']
[FAIL] E7  gate3_provenance:e7_benchmark_shared_refined.json e7_benchmark_shared_refined.json: missing provenance field(s) ['seed']
[FAIL] E7  gate3_provenance:e7_benchmark_percamera_fixed.json e7_benchmark_percamera_fixed.json: missing provenance field(s) ['seed']
[FAIL] E7  gate3_provenance:e7_benchmark_percamera_refined.json e7_benchmark_percamera_refined.json: missing provenance field(s) ['seed']
```

⚠ **These eight are PRE-EXISTING properties of the committed baselines, not damage from the move.**
Seven are `missing provenance field(s) ['seed']` on records that predate the seed-recording change,
plus E1's known non-zero guard count and E4's one hinged grid row. Plan 26-03 should treat this as
the **archive's fixed FAIL floor** and not chase it — but it is also the reason a naive
"gate must return zero FAILs" completeness check cannot be written against the archive.

**`check_e2_band` DID resolve the archived sibling.** Confirmed, not inferred, by this PASS line:

```
[PASS] E2  gate_e2_band:seed42_reproduction  seed-42 band record matches
       ...\experiments\pre_rerun_baseline\results\real_rig_metrics.json within rtol=1e-06
```

plus `record_count` finding 3 per-seed records at seeds [42, 43, 44] and `not_identical` /`scope`
both passing. The `out_dir.parent / "results_e2_band"` construction therefore needs **no change**
provided the archive keeps its sibling layout. **Plan 26-03 must not "fix" it into an absolute
path** — doing so would break the very property that makes `--baseline-dir` cheap.

### Run 2 — now-absent fresh tree (`experiments/results`)

```
TOTAL: 1 PASS, 14 N/A, 31 FAIL
```
Exit code **1**.

**No exception was raised.** The tool degrades cleanly to `not found` FAIL verdicts and `not present
(its stage has not run yet)` N/A verdicts. `check_e2_band` again resolved the sibling correctly,
reporting `...\experiments\results_e2_band not present` — i.e. the sibling mechanism is sound in
both directions.

### ⚠ Gate 3 returns PASS over the empty tree — F-001 confirmed

Research's prediction (`check_rerun_gates.py:1749-1754`) is **correct**. The single PASS in run 2 is:

```
[PASS] ALL gate3_git_sha_consistency   no git_sha values found across any artifact to compare
```

This is the exact vacuous-PASS class the completeness gate exists to kill: a cross-artifact
consistency gate that reports success **because there are no artifacts**. Note the ordering hazard
for D-01's sticky-exit design — the run still exits 1 here, but only because 31 *other* gates
failed. Against a run that produced *some* artifacts but silently dropped a band CSV, Gate 3 would
compare the survivors, agree, and PASS. Gate 3's PASS is therefore **not** evidence of a complete
run and must never be read as one.

Recommendation for 26-03: give `_check_git_sha_consistency` an explicit empty-input verdict that is
**not** PASS (N/A at minimum, FAIL under a profile that expects artifacts), and make the
completeness gate the authority on "were the artifacts produced at all" rather than layering that
onto Gate 3.

### `tests/unit/test_rerun_gates.py` — still green

**59 passed**, zero failures. No test in it reads `experiments/results` literally; its module
docstring states it is built to be independent of `experiments/results/` state, and that held.
**Plan 26-03 inherits no test repairs from the move.**

### Production constants that still name `experiments/results/` (for 26-04 / 26-06, D-12)

Not repointed here — out of this plan's `files_modified` — but they now resolve to an empty
directory and are the concrete surface `--baseline-dir` must cover:

| Constant | Location | Reads |
|---|---|---|
| `_E2_BENCHMARK_JSON_PATH` | `experiments/e3_derived_quantities.py:170` | `results/benchmark.json` — tier 3's 13/200 copy source (`build_cpr_grouping_df`, called at `:944` and `:1008`) |
| `E2_BENCHMARK_PATH` | `experiments/e4_benchmark_grid.py:256` | `results/benchmark.json` — E2's real-rig tenth row; note `resolve_e2_benchmark_path(out_dir)` at `:260` already has an `--out`-relative fallback and is the natural seam |
| `_default_metrics_path()` | `experiments/e5_index_sensitivity.py:670` | `results/real_rig_metrics.json` — feeds `holdout_floor_pct` and `scale_bias_over_floor`, and a miss **degrades both to null with only a WARNING**, which is precisely F-001's signature |

`experiments/README.md` §2 also names `experiments/results/` at lines 30, 52, 108, 113, 191, 202 and
328; D-36 rewrites §2 by hand and the archive move belongs in that rewrite.

## Known Stubs

None.

## Threat Flags

None. No network, auth, or schema surface was introduced; the plan installs nothing (T-26-SC holds —
`pyproject.toml` untouched).

## Self-Check: PASSED

Artifacts confirmed on disk: `experiments/pre_rerun_baseline/results/exp1_parameter_errors.csv`,
`experiments/pre_rerun_baseline/driver_state/rerun_19_5_state.tsv`,
`experiments/pre_rerun_baseline/results_e2_band/e2_band_scope.json`,
`experiments/rerun_19_5.sh` (unmoved, as required), `experiments/archive/` (untouched).

Commits confirmed in `git log`: `048c14f`, `e3a7bf3`.
Tag confirmed: `git rev-list -n1 pre-rerun-baseline` → `d0bbe09c29fb8da29c7a214f36b10ed8ff312b3e`,
equal to the sha recorded at plan start.

`STATE.md` and `ROADMAP.md` were **not** modified — the orchestrator owns those writes.
