---
phase: 26
slug: full-suite-driver-handoff-readiness
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-08-18
---

# Phase 26 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.
> Derived from `26-RESEARCH.md` § Validation Architecture (file-anchored).

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest (markers incl. `slow`; `pytest-xdist` available) |
| **Config file** | `pyproject.toml` |
| **Quick run command** | `python -m pytest tests/unit/<file> -x -q` |
| **Full suite command** | `python -m pytest tests/` — **ORCHESTRATOR ONLY** (56–88 min; `-m "not slow"` still ~26 min) |
| **Interpreter** | AquaCal conda env. Worktree executors MUST `export PYTHONPATH="$(pwd)/src"` |
| **Estimated runtime** | targeted file: ~5–60 s |

---

## Sampling Rate

- **After every task commit:** targeted `python -m pytest tests/unit/<file touched> -x -q`
- **After every plan wave:** union of the wave's touched test files, still targeted
- **Before `/gsd:verify-work`:** full suite green — run by the **orchestrator only**
- **Max feedback latency:** 60 s (targeted)

> Per `CLAUDE.md`: an executor that backgrounds the full suite has stalled permanently.
> Executors receive targeted commands only.

---

## Per-Task Verification Map

Task IDs are assigned by the planner. Requirement-level map (authoritative until plans exist):

| Requirement | Behavior | Test Type | Automated Command | File Exists | Status |
|-------------|----------|-----------|-------------------|-------------|--------|
| DRIVER-01 | Every declared stage has an expectation entry and vice versa | unit | `pytest tests/unit/test_suite_stage_list.py -x` | ❌ W0 | ⬜ pending |
| DRIVER-01 | Ordering constraints hold structurally (O1, O2, O4, e6_repeat1 ∦ e6_band) | unit | same file | ❌ W0 | ⬜ pending |
| DRIVER-01 | Driver sequences, resumes, sticky non-zero exit on gate FAIL | unit (bash via dry-run seam) | `pytest tests/unit/test_run_experiment_suite_dryrun.py -x` | ❌ W0 | ⬜ pending |
| DRIVER-01 | Dry run does not write the real state file | unit | same file | ❌ W0 | ⬜ pending |
| DRIVER-01 | Pre-flight ABORTS and prints its override flag (D-03, D-50) | unit | same file | ❌ W0 | ⬜ pending |
| DRIVER-02 | Manifest emitter produces every D-20 field, all non-null | unit | `pytest tests/unit/test_run_manifest.py -x` | ❌ W0 | ⬜ pending |
| DRIVER-02 | OpenCV **build** captured (`4.13.0.90`, not bare `4.13.0`) | unit | same file | ❌ W0 | ⬜ pending |
| DRIVER-02 | `git describe --tags --long --dirty` distinguishes commits sharing a tag | unit | same file | ❌ W0 | ⬜ pending |
| DRIVER-02 | Gate 3 FAILs on missing manifest / null field / sha mismatch / dirty tree | unit | `pytest tests/unit/test_rerun_gates.py -k manifest -x` | ⚠ extend (1296 ln) | ⬜ pending |
| DRIVER-03 | `smoke` asserts existence only; `full` asserts row counts | unit | `pytest tests/unit/test_expectations.py -x` | ❌ W0 | ⬜ pending |
| DRIVER-03 | **Tripwire:** no expectation asserts 640/960 (nor 352/528), and none requires `noise_std` in `experiments/results/` | unit | same file | ❌ W0 | ⬜ pending |
| DRIVER-03 | `degenerate_observations.csv` absence is PASS (conditional artifact) | unit | same file | ❌ W0 | ⬜ pending |
| DRIVER-03 | `--baseline-dir` reads baselines from archive while writing to `--out`; missing baseline → N/A, not raise | unit | `pytest tests/unit/test_experiments_io.py -k baseline -x` | ⚠ extend | ⬜ pending |
| DRIVER-04 | The four archive-aside breakages stay green after the move | unit | `pytest tests/unit/test_experiments_provenance.py tests/unit/test_experiments_e5.py tests/unit/test_experiments_io.py -x` | ⚠ **existing, will break** | ⬜ pending |
| D-07 | Experiment column constants agree with the expectation manifest | unit | `pytest tests/unit/test_expectations.py -k columns -x` | ❌ W0 | ⬜ pending |
| D-08 | Rendered prose expectation sheet is up to date with the manifest | unit | `pytest tests/unit/test_expectations.py -k sheet -x` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/unit/test_suite_stage_list.py` — DRIVER-01 stage/expectation bijection + ordering
- [ ] `tests/unit/test_run_experiment_suite_dryrun.py` — DRIVER-01 driver mechanics (**no scaffold exists**; mechanism `RERUN_19_3_DRY_RUN`/`_CMD` has only ever been driven by hand)
- [ ] `tests/unit/test_run_manifest.py` — DRIVER-02 emitter
- [ ] `tests/unit/test_expectations.py` — DRIVER-03 manifest, completeness gate, row-count tripwire, D-07 columns, D-08 sheet
- [ ] Fixture strategy for a synthetic output tree the completeness gate can be pointed at (`tmp_path`-scoped; copy the shape in `tests/unit/test_e5_band_mode.py`)

**Pattern to reuse:** `tests/unit/test_experiments_provenance.py` already implements the
"constants agree with a manifest" shape D-07/D-08 need — module-level expectation dict
(`CSV_TO_RECORD:106`), a shrinking `PENDING_CSVS` escape hatch (`:255`, enforced at `:658`),
collection-time discovery degrading to `[]` when the tree is absent (`:277`, `:311`), a
`_is_tracked()` git filter (`:282-308`), and **bidirectional** assertions (`:591`, `:640`).
⚠ `CSV_TO_RECORD` is a second artifact inventory that **will drift** from the new expectation
manifest unless one reads the other.

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| `full`-profile row counts are **correct**, not merely self-consistent | DRIVER-03 | Only Phase 28 produces them; Phase 26 can assert only internal coherence | Compare Phase 28 output against the rendered expectation sheet |
| E2's ~1e-8 control reproduces | DRIVER-03 | Needs the 4.35 GB frameset + 48–87 min | Phase 28 |
| Concurrency model does not OOM at 4–5 wide | DRIVER-01 | Peak RSS untested; probe measured one E1 solve at 0.61 GiB and says RSS does not transfer | Phase 27/28 smoke |
| Column **values** are gauge-corrected, not merely present | DRIVER-03 | Existence and row count are not correctness | Hand-verification sheet (D-08); manifest marks shape-only columns |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 60s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
