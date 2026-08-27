---
phase: 27-frozen-single-sha-handoff-package
plan: 05
subsystem: experiment-suite-provenance
tags: [provenance, environment-capture, blas-threads, d-13, d-14]
requires:
  - "experiments/suite_expectations.json stages[].concurrency"
  - "aquacal.io.capture_environment"
provides:
  - "experiments/_env_lock.py -- the run-time environment lockfile emitter"
  - "SUITE_THREAD_CAP -- the driver/manifest contract name for the BLAS cap"
  - "run_manifest.json keys: blas_thread_cap, blas_thread_cap_stages, blas_thread_unpinned_stages"
affects:
  - "plan 27-08 (driver call site for _env_lock; exports SUITE_THREAD_CAP)"
  - "plan 27-12 (captures the lock from the NEW opencv-python==4.13.* env on the target)"
  - "Phase 29 (answering 'what produced this number')"
tech-stack:
  added: []
  patterns:
    - "never-raise subprocess helper (_run_git shape) reused for `pip freeze`"
    - "writer + FileExistsError/--force guard + build_arg_parser + main, copied from _run_manifest"
    - "None-never-absent: an unresolvable source is a recorded reason, not a missing key"
key-files:
  created:
    - experiments/_env_lock.py
    - tests/unit/test_env_lock.py
  modified:
    - experiments/_run_manifest.py
    - tests/unit/test_run_manifest.py
decisions:
  - "The lockfile is a RUN ARTIFACT, not a pre-freeze commit (D-13) -- no second tag is forced."
  - "pyproject.toml and requirements.txt are untouched; the shipped package's pins are not this run's to tighten."
  - "A failed `pip freeze` writes a reason and still exits 0 -- no fourth pre-flight refusal (P26-D-50)."
  - "`pip freeze` is invoked as `sys.executable -m pip`, not a bare `pip` (D-28: conda is not on a non-interactive SSH PATH)."
  - "The BLAS cap env var is named SUITE_THREAD_CAP; this plan defines it, 27-08 exports it."
  - "Both thread-regime stage lists are READ from suite_expectations.json's `concurrency`, never hardcoded."
  - "The three new manifest keys stay OUT of REQUIRED_MANIFEST_FIELDS -- Gate 3 turns a None there into a FAIL, and an unset cap is legitimate."
metrics:
  duration: ~35 min
  completed: 2026-08-19
  tasks: 2
  commits: 4
  tests_added: 27
---

# Phase 27 Plan 05: Environment Provenance (D-13 lockfile, D-14 two-regime thread record) Summary

A `pip freeze` lockfile emitter modelled wholesale on `_run_manifest.py`, plus three manifest keys
that record which stages the BLAS thread cap applies to and which are deliberately left unpinned.

## What Was Built

### Task 1 -- `experiments/_env_lock.py` (D-13)

CLI-invokable as `python -m experiments._env_lock --out <dir>`, writing `environment_lock.txt`.

The header names `sys.executable`, `platform.python_version()`, the first line of `sys.version`
(which carries the compiler), `platform.platform()`, a UTC stamp in `_run_manifest`'s
`%Y-%m-%dT%H:%M:%SZ` form, and the **BLAS build** read from `numpy.show_config(mode="dicts")` --
the half of D-13's ask that `pip freeze` structurally cannot supply, because a freeze names wheels
rather than the BLAS compiled into them. On this box it resolves to
`name=scipy-openblas; version=0.3.31.dev; openblas_configuration=OpenBLAS 0.3.31.dev USE64BITINT
DYNAMIC_ARCH NO_AFFINITY Haswell MAX_THREADS=24`. Confirming it on the Linux target is 27-12's job.

The body is `sys.executable -m pip freeze` -- deliberately not a bare `pip`, so the lock describes
the interpreter actually running the suite. D-28 makes that distinction load-bearing on the target:
conda is initialised in `~/.bashrc`, which non-interactive SSH never sources, so a bare `pip` there
is the system one.

**The emitter never refuses a run.** A failed freeze (missing pip, non-zero exit, unlaunchable
executable) writes an `UNAVAILABLE: ...` reason in place of the body and `main()` still returns 0.
This is the one place the plan's template diverges from its analog: `run_stage_preflight`'s
run-manifest call site turns a non-zero exit into a refusal with no override, and copying that half
would have added a fourth pre-flight refusal after Phase 26 § D cut three (P26-D-50, D-12).

### Task 2 -- three keys in `build_run_manifest()` (D-14)

| Key | Value here | Source |
|-----|-----------|--------|
| `blas_thread_cap` | `None` unset, `2` under `SUITE_THREAD_CAP=2` | env var `SUITE_THREAD_CAP` |
| `blas_thread_cap_stages` | the 16 `concurrent` stage ids | `suite_expectations.json` |
| `blas_thread_unpinned_stages` | `["e4_repeat","e2_timing","e2_memory","e4"]` | `suite_expectations.json` |

Both lists come from a single never-raise read of the expectations manifest's `concurrency`
attribute (`_resolve_stage_ids_by_concurrency`), in the `_run_git` shape: a missing, unreadable or
unparseable manifest degrades to `(None, None)` rather than raising. **No second hardcoded stage
list exists** -- that duplication is precisely the drift `REQUIRED_MANIFEST_FIELDS`' single-copy
comment was written to prevent, and `tests/unit/test_expectations.py` already pins the four
`serial_alone` stages independently.

A non-integer `SUITE_THREAD_CAP` is recorded **verbatim** rather than dropped: a malformed cap is
itself evidence about the run, and silently discarding it would make the record disagree with the
environment (T-27-05-01).

## Verification

- `python -m pytest tests/unit/test_env_lock.py tests/unit/test_run_manifest.py -q` -> **45 passed**.
- `python -m experiments._env_lock --out <scratch>` -> exit 0, printed the path, header and freeze
  body both present (`opencv`, `numpy`, `scipy` all appear).
- `SUITE_THREAD_CAP=2` -> cap `2`, both lists populated; unset -> key present with value `None`.
- `len(REQUIRED_MANIFEST_FIELDS)` still **17**.
- `experiments.check_rerun_gates` still imports (it consumes that tuple).
- `git diff --name-only 4f6e1f5..HEAD` shows **neither `pyproject.toml` nor `requirements.txt`**.

Per the phase's parallel-execution rule the full suite was NOT run -- the orchestrator owns the
post-merge gate.

## Threat Model Compliance

| Threat | Disposition | How it landed |
|--------|-------------|---------------|
| T-27-05-01 (repudiation, thread record) | mitigated | Cap read from `SUITE_THREAD_CAP`, stage lists from the expectations manifest -- record and enforcement share one source. 27-12 cross-checks on the target. |
| T-27-05-02 (DoS, `pip freeze` in pre-flight) | mitigated | The emitter never raises and never refuses; a failed freeze writes a reason and returns 0. |
| T-27-05-03 (tampering, dependency contract) | mitigated | Asserted by `git diff --name-only`: neither `pyproject.toml` nor `requirements.txt` is in the diff. |
| T-27-05-SC (package installs) | accepted | Nothing installed; `pip freeze` only reports. |

## Deviations from Plan

None -- the plan executed as written. Two mechanical notes:

1. The plan's `<artifacts>` block names exports `build_arg_parser`, `main`, `write_environment_lock`.
   All three exist. `build_environment_lock_text` was added alongside them so the header/body
   contract is unit-testable without a filesystem write; it is additive, not a substitution.
2. `ruff-format` reformatted two commits' worth of staged files via the pre-commit hook; the files
   were re-staged and committed unchanged in substance.

## What This Hands Downstream

- **Plan 27-08** must (a) add the driver call site beside the run-manifest write in
  `run_stage_preflight`, copying the invocation shape but **not** the hard-abort half, and
  (b) export `SUITE_THREAD_CAP` alongside `OMP_NUM_THREADS`/`MKL_NUM_THREADS`/
  `OPENBLAS_NUM_THREADS` for concurrent stages only. This plan deliberately did not touch
  `run_experiment_suite.sh`.
- **Plan 27-12** must capture the lock from the **new** `opencv-python==4.13.*` environment, not
  the target's existing `envs/aquacal` (D-26: it carries the excluded 4.14.0). The lock's OpenCV
  line is the single row most worth reading in the emitted artifact.

## Known Stubs

None.

## Self-Check: PASSED

- `experiments/_env_lock.py` FOUND
- `tests/unit/test_env_lock.py` FOUND
- `experiments/_run_manifest.py` FOUND (modified)
- `tests/unit/test_run_manifest.py` FOUND (modified)
- Commits `2c25829`, `bc2cc25`, `38c0560`, `cd958c9` all FOUND in `git log`
