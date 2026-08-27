---
phase: 27-frozen-single-sha-handoff-package
plan: 13
subsystem: on-target-verification
tags: [linux, smoke, frameset, close, deviation, d-05, d-09, d-10, d-11, d-12, d-21]
requires:
  - "27-12 (the verified clone and environment)"
provides:
  - ".planning/phases/27-frozen-single-sha-handoff-package/27-ONTARGET-VERIFICATION.md (sections 4-9)"
  - "the CLOSE decision: rerun-freeze-01 is final"
affects:
  - "Phase 28 (launched from this clone at 2026-08-20T00:14:10Z)"
  - "Phase 29 (gate verification against this run)"
tech-stack:
  added: []
  patterns: []
key-files:
  created:
    - .planning/todos/pending/2026-08-20-POST-SUBMISSION-frozen-package-install-command-omits-required-extras.md
  modified:
    - .planning/phases/27-frozen-single-sha-handoff-package/27-ONTARGET-VERIFICATION.md
    - .planning/phases/27-frozen-single-sha-handoff-package/27-FREEZE-RECORD.md
decisions:
  - "CLOSE, not refreeze (author's ruling 2026-08-19). The install-command defect is an environment-setup defect, not a code defect; the correction is captured in the run's own environment_lock.txt. SoftwareX is 2026-08-21 and the production run needed to start that night."
  - "The deeper design defect -- e3 importing DECLARED_CONSTANTS from a test module, so a section-3-facing generator needs pytest at runtime -- was NOT fixed. It touches the source of published constants and would require re-running the full suite behind it. Filed post-submission."
  - "Acceptance was read at the end-of-run roll-up, not the driver's exit code, per the 27-10 ruling."
metrics:
  duration: ~45 min
  completed: 2026-08-20
---

# Plan 27-13: on-target smoke, and the close-or-refreeze decision

**Result: CLOSE.** `rerun-freeze-01` at `3ab9c13723202a58bb50e351b0b6bc0c0ffcd59c` is final. No
`rerun-freeze-02`. Full detail in `27-ONTARGET-VERIFICATION.md` §4-9.

## The pass

| | Windows local | Linux on-target |
|---|---|---|
| Roll-up | 72 PASS / 18 N/A / **0 FAIL** | 72 PASS / 18 N/A / **0 FAIL** |
| `STAGE FAILED` | 0 | **0** |
| Stages at exit 0 | 20 / 20 | 20 / 20 |
| Wall clock | 10 min 56 s | 3 min 03 s |

Identical verdict sets across two operating systems, with no override flag used in either.
`fd_jacobian` also ran at full scale on target first: exit 0, both artifacts, both stage-scoped
completeness checks PASS, nothing written into `experiments/results/`.

## The result that mattered most

Pre-flight's **frameset identity check PASSED** on the real image set — the blind spot `--smoke`
structurally cannot cover. It clears D-09/D-10 (the path-kind-agnostic probe; the original
`p.is_file()` bug read an image-directory set as ABSENT and would have forced `--skip-e2`,
silently making the whole run synthetic-only), D-11, D-12, and 27-08's re-derived byte floor
(3.0 GB against a measured 3.80 GB).

## The deviation, and why it is recorded rather than fixed

**Attempt 1 failed**, and found that the frozen package's own install command is incomplete.
`HANDOFF.md` §1.2 says `pip install -e .`, which omits two extras the suite needs:

- **`pytest`** (`dev`) — without it **e3 dies outright**, both passes, because
  `e3_derived_quantities.py:243` imports `DECLARED_CONSTANTS` from a test module that imports
  pytest. That produced the run's only `STAGE FAILED` line.
- **`psutil`** (`bench`) — without it `cpu_count_logical` and `ram_total_bytes` are `None`, and
  both are in `REQUIRED_MANIFEST_FIELDS`, so `gate3_run_manifest_fields` FAILed.

Corrected on the target with `pip install -e ".[dev,bench]"`; attempt 2 was green. Recorded as a
deviation and filed as a post-submission todo, on the author's ruling: no code is wrong, the
shipped *instructions* are, and the correction is fully captured in `environment_lock.txt`.

**This is the single best argument for D-05's decision to verify on the target.** Both packages
are always present on the development box, so neither defect could have surfaced there.

## Also found

A fresh clone's smoke pass downloads 4.35 GB — `reconstruction_bootstrap` falls through to the
published archive because `--smoke` sends E2's output to `results_smoke` while the resolver's
second tier checks `experiments/results/`. Pinned to record 21889922 with an MD5, declared inside
the frozen sha, so it is a fixed input rather than a floating one. **The production run does not
do this**: `reconstruction_bootstrap` `depends_on: [e2_production]`, which writes
`reconstruction_errors.csv` into `experiments/results/` first, so the fresh file wins — which is
what the re-run wants.

## Outcome

Phase 28 launched from this clone at **2026-08-20T00:14:10Z**: pre-flight PASSED, frameset
`MATCH`, pool running 4-wide, artifacts appearing in `experiments/results/`.
