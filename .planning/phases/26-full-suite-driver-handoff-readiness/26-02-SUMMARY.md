---
phase: 26-full-suite-driver-handoff-readiness
plan: 02
subsystem: experiments-provenance
tags: [provenance, driver, gates, DRIVER-02]
requires:
  - "aquacal.io.capture_environment (unchanged, reused)"
  - "experiments/check_rerun_gates.py Gate 3 (_collect_all_json_paths, GateResult)"
provides:
  - "experiments/_run_manifest.py — the suite-level run-manifest emitter"
  - "RUN_MANIFEST_FILENAME / REQUIRED_MANIFEST_FIELDS as the single field-list source"
  - "_check_run_manifest in check_rerun_gates.py — Gate 3's all-hard-FAIL manifest check"
  - "_collect_artifact_shas — the shared artifact sha set"
affects:
  - "plan 26-01 (driver): must invoke the emitter once at pre-flight"
  - "plan 26-03 (completeness gate): owns the empty-sha-set hole Gate 3 deliberately leaves"
tech-stack:
  added: []
  patterns:
    - "importlib.metadata for build-suffix-bearing distribution versions"
    - "git describe --match 'v[0-9]*' as the version anchor"
    - "try/except ModuleNotFoundError sys.path fallback for script-path invocation"
key-files:
  created:
    - experiments/_run_manifest.py
    - tests/unit/test_run_manifest.py
  modified:
    - experiments/check_rerun_gates.py
    - tests/unit/test_rerun_gates.py
decisions:
  - "git describe is restricted to version tags (--match 'v[0-9]*') because this phase itself creates the non-version tag pre-rerun-baseline, which would otherwise displace the semantic anchor"
  - "git_dirty excludes untracked files so it agrees with git describe's own -dirty suffix"
metrics:
  duration: ~35 min
  completed: 2026-08-18
---

# Phase 26 Plan 02: Run Manifest & Gate 3 Extension Summary

One suite-level `run_manifest.json` emitted at pre-flight, recording the OpenCV PyPI build
suffix and a `git describe` version anchor that cannot collide across commits, plus a Gate 3
extension that FAILs hard — never warns — on a missing manifest, a null field, a sha
mismatch, or a dirty tree.

## What Was Built

### `experiments/_run_manifest.py` (new)

- `build_run_manifest()` layers four things on top of `aquacal.io.capture_environment()`
  (reused, not reimplemented, and **not modified** — D-45):
  - `git_describe` from `git describe --tags --long --dirty --match 'v[0-9]*'`
  - `git_dirty` from `git status --porcelain --untracked-files=no`
  - `opencv_build` from `importlib.metadata.version("opencv-python")` with a fallback chain
    over `opencv-contrib-python` / `opencv-python-headless`
  - `installed_distribution_version` — named so it can never be read as "the code that ran"
- Module-level constants `RUN_MANIFEST_FILENAME`, `MANIFEST_SCHEMA_VERSION`,
  `REQUIRED_MANIFEST_FIELDS` (17 names, verbatim from D-20). The gate imports this tuple;
  there is exactly one field list in the codebase.
- `write_run_manifest(out_dir, force=False)` raises `FileExistsError` on a second write
  (D-19: written once at pre-flight, not mutable mid-run).
- `main(argv)` behind `--out PATH` / `--force`, returning non-zero on a failed write, so the
  driver's one aborting checkpoint (D-03) gets an honest signal.
- The module docstring names **F-002** explicitly (4 occurrences of the string), records why
  end-of-run timing is deliberately NOT appended, and explains the `.90` vs `.92` ownership.

Verified on this box: every required field non-null; `opencv_build` `4.13.0.90` against
`opencv_version` `4.13.0`; `git_describe` `v2.0.1-162-g1674883`.

### `_check_run_manifest` in `check_rerun_gates.py`

Four sub-verdicts, all `PASS`/`FAIL` and never `N/A`, emitted as `GateResult("ALL", ...)`:

| Gate | FAILs when |
|------|-----------|
| `gate3_run_manifest_present` | manifest absent, or present but unparseable |
| `gate3_run_manifest_fields` | any required field null or missing — **the detail names them** |
| `gate3_run_manifest_git_sha` | manifest sha disagrees with the artifact sha set — **names both** |
| `gate3_run_manifest_clean_tree` | `git_dirty` is true, or absent |

Wired into `run_all_gates` on the line after `_check_git_sha_consistency`.

`_collect_artifact_shas(out_dir)` was factored out of `_check_git_sha_consistency` so the
manifest check compares against the *same* sha set rather than re-deriving one (D-21: Gate 3
already establishes sha agreement and does it better). The pre-existing check's verdict logic
is untouched — including its PASS-on-empty-set branch, which stays as-is because covering an
empty tree is plan 26-03's job, and CONTEXT is explicit that Gate 3 failing is the system
working.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] `git describe --tags` anchored to a non-version tag**

- **Found during:** Task 1
- **Issue:** The plan's `<behavior>` requires `git_describe` to match
  `^v?\d+\.\d+\.\d+-\d+-g[0-9a-f]+(-dirty)?$`, sourced from the research's verified
  `v2.0.1-156-ge1a202a`. That observation predates the `pre-rerun-baseline` tag **this phase
  itself creates** (D-22). Bare `git describe --tags --long --dirty` in this worktree returns
  `pre-rerun-baseline-0-gd0bbe09` — no semantic version at all. Left unfixed, Phase 28's
  manifest would have recorded a version anchor with no version in it.
- **Fix:** `--match 'v[0-9]*'` restricts the describe to version tags, yielding
  `v2.0.1-162-g1674883`. Recorded as `_VERSION_TAG_GLOB` with the rationale beside it.
- **Files modified:** `experiments/_run_manifest.py`
- **Commit:** `24e547a`

**2. [Rule 1 - Bug] `git_dirty` could contradict the `-dirty` suffix**

- **Found during:** Task 1
- **Issue:** The plan specifies `git_dirty` from `git status --porcelain` being non-empty AND
  that it be `True` exactly when `git_describe` carries `-dirty`. Those two cannot both hold:
  `--porcelain` counts untracked files, `git describe --dirty` ignores them. Any run whose
  output directory is untracked (the normal case for a fresh `results_*` tree) would have
  produced a manifest that FAILs its own consistency contract.
- **Fix:** `git status --porcelain --untracked-files=no`, matching `git describe`'s semantics.
  Documented in the resolver's docstring.
- **Files modified:** `experiments/_run_manifest.py`
- **Commit:** `24e547a`

**3. [Rule 3 - Blocking] the new import broke script-path invocation of the gate**

- **Found during:** Task 2
- **Issue:** `from experiments._run_manifest import ...` resolves under `python -m` and pytest,
  but the driver invokes the gate **by path** — `"${GATE_PYTHON}" experiments/check_rerun_gates.py
  "${target_dir}"` (`rerun_19_5.sh:257`, `rerun_19_4.sh:180`, `rerun_19_3.sh:121`). That puts
  `experiments/` on `sys.path`, not the repository root, so the gate died with
  `ModuleNotFoundError: No module named 'experiments'` before running a single check. Confirmed
  by direct invocation, then confirmed fixed the same way.
- **Fix:** a `try` / `except ModuleNotFoundError` that inserts the repository root on `sys.path`
  and retries. A bare `from _run_manifest import ...` was rejected — it would have broken
  `python -m` and the tests instead.
- **Files modified:** `experiments/check_rerun_gates.py`
- **Commit:** `c8444fc`

**4. [Rule 1 - Bug] `test_exit_code_zero_on_a_fully_passing_tree` no longer passed**

- **Found during:** Task 2
- **Issue:** Under D-21, a tree with no `run_manifest.json` is by definition not fully passing,
  so the pre-existing fixture correctly began FAILing. This is the gate working.
- **Fix:** the fixture now writes a manifest agreeing with the fixture's sha. The test's
  assertion (`exit 0`, `0 FAIL`) is unchanged.
- **Files modified:** `tests/unit/test_rerun_gates.py`
- **Commit:** `c8444fc`

### Acceptance-criteria note (not a deviation in behaviour)

`git diff experiments/check_rerun_gates.py | grep '^-' | grep -c '_check_git_sha_consistency'`
returns **1**, not 0. The single matching line is the function's `def` line, which git renders
as removed-and-re-added purely because `_collect_artifact_shas` was inserted immediately above
it; the line is byte-identical on both sides and **no line inside the function's body was
removed**. The criterion's intent — that the check was extended around, never weakened — holds,
and all of `TestGate3Provenance` plus the new
`test_sha_consistency_gate_is_unchanged_by_the_manifest_gate` pass unchanged.

Two docstring sentences originally containing the literal `N/A` were reworded so the
zero-`N/A` grep is literally satisfied; no verdict logic changed.

## Verification

| Check | Result |
|-------|--------|
| `pytest tests/unit/test_run_manifest.py -x -q` | **18 passed** (criterion: ≥8) |
| `pytest tests/unit/test_rerun_gates.py -k manifest -x -q` | **12 passed** (criterion: ≥5) |
| `pytest tests/unit/test_rerun_gates.py -q` | **71 passed**, no regression |
| Both files together | **89 passed** |
| all required fields non-null | `[]` |
| `opencv_build` suffix consistent | `4.13.0.90` vs `4.13.0`, exits 0 |
| `grep -c 'F-002' experiments/_run_manifest.py` | 4 (≥1) |
| `grep -c 'installed_distribution_version'` | 5 (≥2) |
| `N/A` inside `_check_run_manifest` | 0 |
| `REQUIRED_MANIFEST_FIELDS` inside `_check_run_manifest` | 3 (≥1) |
| `git diff --name-only` contains a `src/` path | **no** (D-45 honored) |
| script-path gate invocation | runs, reports `gate3_run_manifest_present FAIL` |

The full suite was NOT run — that is the orchestrator's post-merge gate. No experiment,
calibration or driver was executed.

## Follow-ups for the Rest of Phase 26

1. **Plan 26-01 (driver)** must invoke
   `"${GATE_PYTHON}" -m experiments._run_manifest --out "${OUT_DIR}"` at pre-flight, before
   stage 1, and treat a non-zero exit as an abort (D-03). Nothing invokes the emitter yet.
2. **Plan 26-03 (completeness gate)** still owns the PASS-on-empty-sha-set hole at
   `_check_git_sha_consistency`. This plan deliberately did not close it.
3. Every existing committed output tree (`experiments/results/`, `results_e2_band/`, …) will now
   report `gate3_run_manifest_present FAIL` when the gate is run against it, because none of them
   carries a manifest. That is correct and expected — those trees predate DRIVER-02 — but anyone
   running the gate against an archived tree before Phase 28 should expect it.

## Known Stubs

None.

## Threat Flags

None. No new network endpoint, auth path, file-access pattern or schema at a trust boundary was
introduced; the manifest is written into the run's own output directory and read back by the gate.

## TDD Gate Compliance

Both tasks followed RED → GREEN. `1674883` (test) precedes `24e547a` (feat); `2dc19ef` (test)
precedes `c8444fc` (feat). No REFACTOR commit was needed.

## Self-Check: PASSED

All four commits (`1674883`, `24e547a`, `2dc19ef`, `c8444fc`) exist in `git log`, and all five
claimed files exist on disk. No file was deleted by any commit in this plan. `STATE.md` and
`ROADMAP.md` were not modified — the orchestrator owns those writes.
