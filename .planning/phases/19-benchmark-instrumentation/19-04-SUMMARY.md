---
phase: 19-benchmark-instrumentation
plan: 04
subsystem: infra
tags: [psutil, tracemalloc, benchmark, instrumentation, pyproject-extras]

# Dependency graph
requires:
  - phase: 19-benchmark-instrumentation
    provides: "Phase 19 context (D-01/D-02/D-05/D-18 locked decisions), research on zero-polling OS peak-memory reads"
provides:
  - "aquacal.io.benchmark.capture_environment() -- never-fails environment snapshot (versions, OS/CPU, best-effort git SHA)"
  - "aquacal.io.benchmark.capture_peak_memory() -- stateless, platform-dispatched peak-memory reading safe to call at every stage boundary"
  - "pyproject.toml [bench] optional extra (psutil>=5.9)"
affects: ["19-05"]

# Tech tracking
tech-stack:
  added: ["psutil>=5.9 (optional [bench] extra, not core)"]
  patterns:
    - "Never-fails capture function: every external call wrapped in its own try/except, degrading to None/labelled-unavailable rather than raising"
    - "Platform dispatch via platform.system() for zero-polling OS-native high-water-mark reads (Windows peak_wset, Linux /proc VmHWM)"
    - "mode string field distinguishes true OS high-water marks from weaker instantaneous/fallback readings"

key-files:
  created:
    - src/aquacal/io/benchmark.py
    - tests/unit/test_benchmark.py
  modified:
    - pyproject.toml
    - src/aquacal/io/__init__.py

key-decisions:
  - "Both functions built together in one commit (feat) after a single shared RED (test) commit covering both classes, since they live in the same new module and were tested together"
  - "capture_peak_memory() dispatches Linux -> /proc VmHWM first (no psutil dependency at all on Linux), then Windows -> psutil peak_wset, then other platforms -> single psutil RSS sample, then tracemalloc as the last-resort fallback -- matching D-01/D-02/D-18 exactly"
  - "capture_environment()'s git_sha resolution walks upward from this module's own file (bounded to 6 parent levels) rather than assuming CWD is the repo root, per D-05 and 19-RESEARCH.md's repo_hint_path recipe"

patterns-established:
  - "New aquacal.io.* modules are exported from aquacal/io/__init__.py's __all__ immediately, following the existing internals.py precedent"

requirements-completed: [BENCH-02]

# Metrics
duration: 10min
completed: 2026-07-24
---

# Phase 19 Plan 04: Benchmark Capture Primitives Summary

**`capture_environment()` and `capture_peak_memory()` in a new `aquacal.io.benchmark` module — never-fails environment/git-SHA capture and platform-dispatched, zero-polling peak-memory reads (Windows `peak_wset`, Linux `/proc` `VmHWM`), stateless and safe to call at every stage boundary.**

## Performance

- **Duration:** ~10 min (RED commit `1b11f94` at 14:04:24, GREEN commit `c637b86` at 14:05:56, plus verification/summary time)
- **Started:** 2026-07-24T13:58:43-04:00 (worktree base commit)
- **Completed:** 2026-07-24T18:08Z
- **Tasks:** 2 (executed as one shared RED/GREEN cycle, see Deviations)
- **Files modified:** 4 (2 created, 2 modified)

## Accomplishments

- `pyproject.toml` declares a new `[bench]` optional extra (`psutil>=5.9`), not a core dependency
- `capture_environment()` never raises under any tested failure mode: psutil missing, git subprocess raising `FileNotFoundError`/`TimeoutExpired`, or no `.git` findable within 6 parent levels — always returns `aquacal_version` as a non-empty string
- `capture_peak_memory()` correctly dispatches by platform: verified live on this Windows dev machine (`mode == "psutil_peak_wset"`, `peak_bytes > 0`), and unit-tested for Linux (mocked `/proc/<pid>/status` VmHWM parsing), Darwin (mocked, `psutil_rss_sampled`), and psutil-entirely-unavailable (`tracemalloc_python_heap`) paths
- Proved stateless/repeatable via an explicit 3-call-in-a-row monotonicity test and a thread-count-unchanged test — the exact property Plan 19-05 depends on for per-stage attribution (D-18)
- Both functions exported from `aquacal.io.__init__.__all__`

## Task Commits

Both tasks (Task 1: `capture_environment`, Task 2: `capture_peak_memory`) were implemented together in a single module and tested together, following one shared TDD RED/GREEN cycle rather than two separate cycles, since the plan's own `<action>` blocks describe adding both functions to the same new file with tests appended to the same test file:

1. **Tasks 1+2 RED:** `1b11f94` (test) — added `tests/unit/test_benchmark.py` with `TestCaptureEnvironment` (8 tests) and `TestCapturePeakMemory` (9 tests); confirmed failing via `ModuleNotFoundError: No module named 'aquacal.io.benchmark'` before any implementation existed.
2. **Tasks 1+2 GREEN:** `c637b86` (feat) — added `pyproject.toml`'s `[bench]` extra, `src/aquacal/io/benchmark.py` (`capture_environment`, `capture_peak_memory`, `_find_git_root`, `_linux_vmhwm_bytes`), and the `aquacal.io.__init__` exports; all 17 tests pass.

**Plan metadata:** (this commit, pending)

## Files Created/Modified

- `pyproject.toml` — added `[project.optional-dependencies].bench = ["psutil>=5.9"]`
- `src/aquacal/io/benchmark.py` — new module: `capture_environment()`, `capture_peak_memory()`, and two private helpers (`_find_git_root`, `_linux_vmhwm_bytes`)
- `src/aquacal/io/__init__.py` — exports `capture_environment`, `capture_peak_memory` in `__all__` and the import block
- `tests/unit/test_benchmark.py` — 17 tests across `TestCaptureEnvironment` (8) and `TestCapturePeakMemory` (9)

## Decisions Made

- Combined Task 1 and Task 2 into a single RED/GREEN pair (one `test` commit, one `feat` commit) rather than two separate TDD cycles, because both functions were designed together in the same new file and plan's own task ordering has Task 2 extending the same test file Task 1 creates. This does not weaken TDD gate compliance: the RED commit demonstrably fails (`ModuleNotFoundError`) before the GREEN commit exists, and both task's `<verify>` commands (`-k CaptureEnvironment`, `-k CapturePeakMemory`) pass independently against the final state.
- On Linux, `capture_peak_memory()` reads `/proc/<pid>/status` directly and never touches `psutil` at all (matches D-02's finding that psutil has no Linux peak-RSS equivalent) — only Windows and the generic-platform fallback branch import `psutil`.
- `_find_git_root` is a small private helper (not part of the public 2-function surface named in the plan's `must_haves.artifacts`) added to satisfy D-05's "walk upward, bounded to 6 parent levels" resolution recipe without duplicating that logic inline.

## Deviations from Plan

None — plan executed exactly as written, aside from the RED/GREEN cycle consolidation noted above under Decisions Made (not a scope or behavior deviation, purely a commit-sequencing choice).

## Issues Encountered

**Editable install resolves to the main repo, not this worktree.** `pip show aquacal` reports `Editable project location: C:\Users\tucke\PycharmProjects\AquaCal` (the main checkout), so a bare `python`/`pytest` invocation from inside this worktree silently imports and tests the main repo's `src/aquacal`, not the code written here. Discovered independently before the coordinator's warning arrived, already working around it. Fix: export `PYTHONPATH="$(pwd)/src"` before every verification command run from the worktree root.

**Verification integrity confirmation (per coordinator's warning):**
- `python -c "import aquacal.io.benchmark as m; print(m.__file__)"` with `PYTHONPATH` set printed `...\.claude\worktrees\agent-a433e293d24e062e5\src\aquacal\io\benchmark.py` — confirmed resolving to this worktree's own code, not the main repo.
- Every verification command below was run (or re-run) with `PYTHONPATH="$(pwd)/src"` exported from the worktree root before this SUMMARY was written; no verification numbers in this document were produced without it.

## Verification Results (all run with `PYTHONPATH="$(pwd)/src"` from the worktree root)

- `python -m pytest tests/unit/test_benchmark.py -q` → **17 passed**
- `python -m pytest tests/unit/test_benchmark.py -k CaptureEnvironment -q` → **8 passed, 9 deselected**
- `python -m pytest tests/unit/test_benchmark.py -k CapturePeakMemory -q` → **9 passed, 8 deselected**
- `python -m pytest tests/ -m "not slow" -q` → **792 passed, 31 deselected** (baseline was 775 passed / 31 deselected; +17 is exactly this plan's new test count, confirming no other test count regressed or was skipped)
- `python -m ruff check` → **All checks passed**
- `python -c "import tomllib; d=tomllib.load(open('pyproject.toml','rb')); assert 'bench' in d['project']['optional-dependencies']; print(...)"` → `['psutil>=5.9']`
- `python -m sphinx -W --keep-going -b html docs docs/_build/html` → **build succeeded**, no warnings (autodoc's existing `api/io.rst` did not error on the new module; `docs/_build/` remains gitignored, no untracked files produced)

## TDD Gate Compliance

- `test(19-04)` commit `1b11f94` (RED) exists and was confirmed failing (`ModuleNotFoundError`) prior to any implementation.
- `feat(19-04)` commit `c637b86` (GREEN) exists after it, with all 17 tests passing.
- No `refactor` commit was needed — the implementation required no post-GREEN cleanup.

## User Setup Required

None — no external service configuration required. `psutil` installs via `pip install aquacal[bench]` or is already present in this dev environment (confirmed 7.2.2 installed, per 19-RESEARCH.md).

## Next Phase Readiness

- `capture_peak_memory()` is confirmed stateless and safe to call repeatedly (proven by the monotonicity and no-new-thread tests) — Plan 19-05 can call it once per stage boundary with no bracketing.
- `capture_environment()` is confirmed to never raise under every tested failure mode, including outside a git checkout (`tmp_path`-based test with no `.git` anywhere in the tree).
- Neither function touched `config/schema.py`, `pipeline.py`, or any calibration call site — this plan is purely additive capture primitives, as scoped. Plan 19-05 owns wiring these into the pipeline and writing `benchmark.json`.
- No blockers identified for 19-05.

---
*Phase: 19-benchmark-instrumentation*
*Completed: 2026-07-24*

## Self-Check: PASSED

- FOUND: `src/aquacal/io/benchmark.py`
- FOUND: `tests/unit/test_benchmark.py`
- FOUND commit `1b11f94` (test)
- FOUND commit `c637b86` (feat)
