---
phase: 27-frozen-single-sha-handoff-package
plan: 08
subsystem: experiment-suite-driver
tags: [portability, e2-release-config, gate-python, blas-threads, provenance, d-10, d-11, d-12, d-13, d-14, d-29, d-30]
requires:
  - "experiments/_env_lock.py (27-05)"
  - "SUITE_THREAD_CAP -- the contract name defined by 27-05"
  - "experiments/suite_expectations.json stages[].concurrency"
  - "aquacal_data/real-rig/real-rig/config_paper.yaml (structural analog)"
provides:
  - "experiments/configs/e2_release_linux.yaml -- E2's exact release inputs, inside the frozen sha"
  - "SUITE_STAGE_PYTHON -- the driver/manifest contract name for the stage interpreter"
  - "run_manifest.json keys: gate_interpreter, stage_interpreter_declared, stage_interpreter, interpreters_agree"
  - "detect-then-fallback resolution for GATE_PYTHON and E2_RELEASE_CONFIG"
  - "the _env_lock call site in run_stage_preflight"
affects:
  - "plan 27-10 (consumes the resolution contract; no sixth override flag exists)"
  - "plan 27-12 (the manifest it captures now carries both interpreters)"
  - "Phase 28 (the driver this hands to the Linux target)"
  - "Phase 29 (Gate 3 provenance, and answering 'which interpreter computed this')"
tech-stack:
  added: []
  patterns:
    - "in-repo default + env var repointer (BASELINE_DIR precedent) for E2_RELEASE_CONFIG"
    - "never-raise resolution (_run_git shape) for the stage interpreter"
    - "None-never-absent: an undecidable verdict is a recorded None, not a missing key"
    - "artifact-not-refusal: the lockfile call site logs a non-zero exit and continues"
key-files:
  created:
    - experiments/configs/e2_release_linux.yaml
    - tests/unit/test_e2_release_config.py
  modified:
    - experiments/run_experiment_suite.sh
    - experiments/suite_expectations.json
    - experiments/EXPECTATIONS.md
    - experiments/_run_manifest.py
    - tests/unit/test_run_manifest.py
    - tests/unit/test_run_experiment_suite_dryrun.py
decisions:
  - "D-11: E2's release inputs are COMMITTED inside the frozen sha. The off-repo Desktop config carried `frame_step: 30`, which does not produce the 13 x 262 signature pre-flight asserts -- provenance outside the artifact is the F-001 shape."
  - "D-12/D-29: neither Windows literal is reachable as a default. The conda-env-by-name discovery rung was DELETED rather than case-fixed -- auto-discovery by name is the defect, and repairing the case would have pointed the fallback at the OpenCV 4.14.0 env D-26 excludes."
  - "The resolved gate interpreter is printed loudly on success, not only on failure."
  - "D-14: the BLAS cap is exported for CONCURRENT stages only. The four serial_alone timing stages see no cap variable at all, because every historical measurement was taken unpinned and pinning them would silently change what is being timed."
  - "Both thread-regime stage lists are READ from suite_expectations.json, never hardcoded."
  - "D-13: the environment lockfile is written beside the run manifest as a run ARTIFACT; a non-zero exit is logged and the run continues."
  - "D-30: a gate/stage interpreter mismatch is RECORDED, never REFUSED -- it is legitimate on the Windows dev box by design, where bare `python` is Anaconda base. That is precisely why pre-flight does not use it."
  - "All four interpreter keys stay OUT of REQUIRED_MANIFEST_FIELDS, so an undecidable None can never become a Gate 3 FAIL."
metrics:
  duration: ~2 h (spanned a machine crash; see Deviations)
  completed: 2026-08-19
---

# Plan 27-08: Driver portability and E2's frozen inputs

## What shipped

Task 1 (`ce9154a`) committed `experiments/configs/e2_release_linux.yaml` — image-directory
paths, `frame_step: 1`, `max_calibration_frames: 200`, 13 extrinsic paths (12 main + 1
auxiliary) — so the exact E2 inputs live inside the frozen sha.

Task 2 (`bb5a4ae`) made both Windows literals detect-then-fallback: `GATE_PYTHON` detects and
falls back with a loud resolution log, and `E2_RELEASE_CONFIG` defaults to the in-repo Linux
config with `SUITE_E2_RELEASE_CONFIG` as the repointer. No sixth override flag was added.

Task 3 (`d2b026b`) added the two-regime BLAS pin — capped for concurrent stages, absent (not
empty) for the four `serial_alone` timing stages — plus the `_env_lock` call site in
`run_stage_preflight` and the re-derived byte floor.

A fourth commit (`fdd1ce4`) landed D-30, which was ruled in by `fdd0f3c` after this plan was
written: `_resolve_interpreters` records `gate_interpreter`, `stage_interpreter_declared`,
`stage_interpreter` and an `interpreters_agree` verdict. The driver already exported
`SUITE_STAGE_PYTHON` at `:500` as part of Task 2; this is the consuming half.

## Why D-30 matters

`GATE_PYTHON` writes the manifest while every stage runs bare `python -u -m experiments.<mod>`
(~25 call sites). So `python_version`, `numpy_version`, `scipy_version`, `opencv_version` and
`installed_distribution_version` all describe the *tooling* interpreter, not the one that
computed the numbers — and Gate 3 cannot see the gap, because it checks that the git shas agree
and they do. On the run machine the risk is concrete: D-26 records a pre-existing environment
carrying the excluded OpenCV 4.14.0, which would have been stamped onto a manifest whose stages
ran 4.13. `interpreters_agree` is the only field that says whether those are the same thing.

## Verification

- `bash -n experiments/run_experiment_suite.sh` — exit 0.
- `python -m experiments.render_expectation_sheet --check` — up to date.
- `tests/unit/test_run_manifest.py` — 33 passed.
- `test_run_experiment_suite_dryrun.py`, `test_expectations.py`, `test_e2_release_config.py` —
  167 passed (1:58), including
  `test_serial_alone_is_exactly_the_four_timing_stages`.

Run under `envs/aquacal/python.exe` with `PYTHONPATH=$(pwd)/src`; bare `python` in Git Bash is
Anaconda base and fails collection on `import cv2`.

## Deviations

The development machine crashed mid-plan, after Tasks 1-3 were committed but while the D-30
addendum was still uncommitted in the worktree. The work survived intact in
`worktree-agent-a56aab3071203a9b7`. The orchestrator verified it against the plan's acceptance
criteria, committed it as `fdd1ce4`, and wrote this summary rather than re-dispatching an
executor — the machine's instability makes a fresh executor pass the larger risk.
