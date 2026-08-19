---
phase: 27-frozen-single-sha-handoff-package
plan: 02
subsystem: experiment-suite-driver
tags: [preflight, resume, frameset, image-set, bash, dry-run-tests]
requires:
  - experiments/suite_expectations.json (preflight.frameset.cheap_check, read by key)
  - the RUN_EXPERIMENT_SUITE_DRY_RUN seam
provides:
  - a path-kind-agnostic E2 frameset pre-flight (directories or video files)
  - an exit-code-aware resume predicate (a failed stage is re-invoked)
  - eleven new driver tests, including the first that exercise the frameset probe
affects:
  - every launch and every resume of the frozen 15-16 h re-run
tech-stack:
  added: []
  patterns:
    - the frameset probe is SLICED out of the driver source at test time, never copied
    - the byte floor is lowered in a sandbox COPY of the manifest, never in the script
    - resume assertions match the SKIP line by stage NAME, never by queue index
key-files:
  created: []
  modified:
    - experiments/run_experiment_suite.sh
    - tests/unit/test_run_experiment_suite_dryrun.py
decisions:
  - D-10 implemented as p.exists() plus a recursive per-path byte sum; a directory's own st_size is never summed
  - D-22 implemented as `&& $5 == 0` in the awk predicate; resume gets strictly stricter
  - the pre-existing resume assertion on "SKIP stage 7 (e5)" was vacuous and was replaced with a name-based predicate
metrics:
  duration: ~35 min
  completed: 2026-08-19
---

# Phase 27 Plan 02: Driver Defects D-10 and D-22 Summary

Pre-flight now sees an image set (13 directories) instead of refusing it as ABSENT, and a
crashed-then-resumed stage that ran and FAILED is re-invoked instead of silently skipped.

## What Changed

### D-09/D-10 — `_preflight_frameset` is path-kind agnostic

`present` was built with `p.is_file()`, which is False for every path in an image set. On the
frozen run's target that made `present` empty, the probe exited 2 = ABSENT, and the driver's
refusal advised `--skip-e2` — advice that would have turned the entire re-run synthetic-only.

Two expressions changed inside the embedded Python probe:

- `present = [p for p in paths if p.exists()]`
- `total_bytes = sum(_path_bytes(p) for p in present)`, where `_path_bytes` sums
  `f.stat().st_size` over `p.rglob("*")` for regular files when the path is a directory and
  falls back to `p.stat().st_size` for a file. A directory's own `st_size` is never summed.

Everything else is byte-for-byte unchanged: both assertions, both manifest reads
(`cheap["n_extrinsic_videos"]`, `cheap["min_total_bytes"]`), every `print` prefix, all three
`sys.exit` codes, and the `retired_signature` message. No sixth override and no new refusal.
The header comment now records that the check is path-kind agnostic and why —
`io/detection.py:134` already auto-selects `ImageSet` for a directory, which is what makes this
a driver defect rather than a library one.

### D-22 — `is_stage_complete` reads the exit-code column

The awk predicate is now `$1 == stage && $3 == "complete" && $5 == 0`. `state_complete` always
writes the exit code as column 5, so a completion line carrying a non-zero exit no longer counts
as done. The comment was rewritten in step: it now names both incomplete cases (start-only, and
completed-non-zero) and the failure it closes. The change makes resume strictly stricter — no
stage that would have re-run before is skipped now.

## Verification

- `bash -n experiments/run_experiment_suite.sh` → exit 0.
- `grep -c 'p.is_file()'` → 0. `grep -c 'rglob'` → 1. `grep -Ec 'sys.exit\(2\)|sys.exit\(3\)'`
  → 3, unchanged from the pre-edit count. `grep -c '\$5 == 0'` → 1.
- `grep -c '4000000000'` → 0: the byte floor is still read from the manifest by key and appears
  nowhere in the script (see the criterion note below).
- `experiments/suite_expectations.json` was not touched; `preflight.overrides` still holds five
  entries.
- `pytest tests/unit/test_run_experiment_suite_dryrun.py` → **47 passed in 152 s** (35 before
  this plan, 47 after). The full file was run; no narrowing was needed. The full suite was NOT
  run — that is the orchestrator's post-merge gate.

Both tasks were executed RED → GREEN. The RED runs are on the record: the three directory cases
failed with `assert 2 == 3` / ABSENT before the D-10 fix, and only the non-zero-exit resume case
failed before the D-22 fix.

## Deviations from Plan

### 1. [Rule 3 - Blocking] The prescribed test harness cannot reach the frameset probe

- **Found during:** Task 1
- **Issue:** The plan directs the new pre-flight tests to invoke the driver through `run_driver`
  with `SUITE_E2_RELEASE_CONFIG`. Under the dry-run seam the WHOLE pre-flight stage is
  substituted (`run_stage_preflight` hits `_dry_run_stub` and returns at
  `run_experiment_suite.sh:856`, before `_preflight_frameset` is ever called), so `run_driver`
  structurally cannot execute the probe. A test written that way would assert nothing.
- **Fix:** The tests SLICE the probe's Python body out of the driver source on every call
  (`_frameset_probe_source()`, anchored on the unique `SUITE_E2_RELEASE_CONFIG=... <<'PY'`
  heredoc opener) and run it directly. The program under test is therefore still exactly the one
  the driver ships and cannot drift from it. The `--skip-e2` / `--allow-frameset-mismatch`
  coupling that lives in the Bash `case` is asserted separately against the driver source, and
  the pre-existing `TestPreflight` tests still cover the refusal banner through `run_driver`.
- **Files modified:** tests/unit/test_run_experiment_suite_dryrun.py
- **Commit:** 61d9a86

### 2. [Rule 3 - Blocking] The byte floor cannot be met with real files in a test

- **Found during:** Task 1
- **Issue:** `min_total_bytes` is 4 GB. No test can create 52 GB of frameset.
- **Fix:** Each test sandbox gets its own COPY of `experiments/suite_expectations.json` with only
  `preflight.frameset.cheap_check.min_total_bytes` lowered, and the probe runs with the sandbox
  as cwd. The floor is moved in the MANIFEST, never in the probe — which is itself the property
  FIX-06 requires, and one of the tests asserts the real floor value appears nowhere in the
  driver source.
- **Files modified:** tests/unit/test_run_experiment_suite_dryrun.py
- **Commit:** 61d9a86

### 3. [Rule 1 - Bug] A pre-existing resume assertion was vacuous

- **Found during:** Task 2
- **Issue:** `TestResume::test_a_started_but_uncompleted_stage_is_rerun_from_scratch` asserted
  `"SKIP stage 7 (e5)" not in run.stdout`. The index in that message is the position in the
  driver's shortest-first EXECUTION order, not the manifest's listing order: e5 is 9th in the
  manifest and 6th in the queue. The string `SKIP stage 7 (e5)` can never appear, so the negative
  assertion passed against every driver ever written — the vacuous-gate shape this project has
  already been bitten by.
- **Fix:** All three resume assertions now use `_was_skipped_as_complete(run, "e5")`, which
  matches the skip line by stage NAME and keeps the index out of the predicate entirely. This
  is what turned the new exit-0 test from a false red into a real assertion.
- **Files modified:** tests/unit/test_run_experiment_suite_dryrun.py
- **Commit:** 03ee55b

### 4. [Clarification] Two acceptance criteria were read against their stated intent

- `grep -c 'min_total_bytes' == 0` is not satisfiable and was never meant to be: the probe must
  read the key by name, and it did so before this plan (1 occurrence, at
  `run_experiment_suite.sh:961`). The intent — the NUMBER is never a shell literal — is asserted
  instead as `grep -c '4000000000' == 0`, plus a test that reads the live floor from the manifest
  and asserts its string form is absent from the driver.
- `<behavior>`'s "a frameset where fewer than 13 paths exist still exits 2 (ABSENT)" does not
  match the shipped probe, which exits 2 only when NOTHING declared exists and treats a partial
  frameset (11 of 13) as a MISMATCH, exit 3. The plan forbids changing anything else, so the
  shipped semantics were preserved and both cases are now tested explicitly, for both path kinds.

## Threat Model Follow-through

| Threat ID | Disposition | Outcome |
|-----------|-------------|---------|
| T-27-02-01 | mitigate | The recursive walk runs in pre-flight only, the one place permitted to abort before any long stage. Unchanged by this plan; the on-target measurement stays 27-12's. |
| T-27-02-02 | mitigate | Resume is strictly stricter. Asserted by the new exit-0 test (a clean stage is still skipped) and by the pre-existing start-only test, both green. |
| T-27-02-03 | mitigate | No new refusal, no sixth override. `suite_expectations.json` is untouched and `preflight.overrides` still has five entries. |

No new security-relevant surface beyond the declared boundary: the probe recurses a directory
tree named by a config the operator already points the driver at.

## Notes for the Next Plan

- The frozen run's target holds an image set, so the pre-flight byte floor is now compared
  against a WALKED total. Whoever sets the target's release config (27-08/27-11) should confirm
  the walked total of the on-target frameset clears 4 GB — the published archive is 4.35 GB and
  the local raw capture 10.57 GB, so both clear, but the number is now measured differently than
  it was for the video set.
- `experiments/run_experiment_suite_state.88512b7.tsv` still carries the
  `reconstruction_bootstrap ... complete ... 1` line. With D-22 in place, a resume against that
  state file now re-runs that stage rather than skipping it.

## Self-Check: PASSED

All three files exist on disk and all four commits (61d9a86, 6dddbaa, 03ee55b, 1b8afa3) are
present in `git log`.
