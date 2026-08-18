---
phase: 26-full-suite-driver-handoff-readiness
plan: 03
subsystem: experiments-gates
tags: [DRIVER-01, DRIVER-03, manifest, completeness-gate, F-001, D-05, D-40, D-42]
requires:
  - "experiments/check_rerun_gates.py GateResult, _load_csv, run_all_gates (26-02's sys.path fallback preserved)"
  - "experiments/pre_rerun_baseline/ (plan 26-01) for the committed baseline shapes"
  - "e6 --axes selector (plan 26-05) — what makes an 84-row E6 band reachable"
provides:
  - "experiments/suite_expectations.json — the single expectation manifest: 20 stages, 62 artifacts"
  - "experiments/_expectations.py — load_expectations, check_completeness, EXPECTATIONS_PATH, PROFILES"
  - "check_rerun_gates.py --stage / --profile, both optional"
  - "tests/unit/test_expectations.py — the tripwire and every manifest coupling"
affects:
  - "plan 26-07 (the driver) — its STAGES=() array, ordering and concurrency pool read this manifest"
  - "plan 26-09 — adds the -k sheet freshness test to tests/unit/test_expectations.py; that keyword is unclaimed"
  - "Phases 27, 28, 29 — every row count, profile and wall-clock number they schedule against"
tech-stack:
  added: []
  patterns:
    - "a JSON data manifest imported by both the gate and its tests, so drift is a red test rather than a written plea"
    - "late import of GateResult to break the check_rerun_gates <-> _expectations cycle"
    - "ast-parsed cross-inventory reconciliation, so the test cannot pass because an import failed"
key-files:
  created:
    - experiments/suite_expectations.json
    - experiments/_expectations.py
    - tests/unit/test_expectations.py
  modified:
    - experiments/check_rerun_gates.py
decisions:
  - "serial_total_hours is the manifest's OWN sum (28.3-31.3 h), not D-51's 22-26 h; D-51's range is recorded beside it with the reconciliation, because D-51 predates counting the seven invocations no driver has ever run"
  - "the four duplicated shape constants carry an AUTHORITY COMMENT rather than deriving from the manifest — but the comment is made binding by TestShapeConstantReconciliation, so it is a red test, not a plea"
  - "preflight is concurrency=concurrent, not serial_alone: serial_alone is reserved for the four TIMING-sensitive stages (review H4's actual rationale), and pre-flight is de facto alone via depends_on anyway"
  - "e2_timing and e2_memory write into their own results_e2_timing/ and results_e2_memory/ trees, so their benchmark.json can never overwrite the production run's"
metrics:
  duration: ~65 min
  tasks: 3
  completed: 2026-08-18
---

# Phase 26 Plan 03: Expectation Manifest & Completeness Gate Summary

One machine-readable manifest — 20 stages, 62 artifacts, every ordering constraint expressed as
`depends_on` — plus the completeness gate that reads it and is the only gate in the suite that
FAILs over an empty tree.

## What Was Built

### `experiments/suite_expectations.json` — `8d00c69`

Twenty stages, ordered shortest-first (D-37) except where `depends_on` overrides it, and 62
artifacts. Every acceptance criterion in the plan verified by running it, not by reading:

| Criterion | Result |
|---|---|
| `ok N stages, M artifacts` | **ok 20 stages 62 artifacts** (criteria: ≥18, ≥25) |
| `serial_alone` set | exactly `['e2_memory', 'e2_timing', 'e4', 'e4_repeat']` |
| `e4.depends_on` / `e7_focal_standoff` / `reconstruction_bootstrap` / `e6_band` | `e2_production` / `e7_band` / `e2_production` / `e6_repeat1` — all present |
| `exp1_band.csv` / `exp1_parameter_band.csv` / `generalization_sweep_band.csv` `rows.full` | **256 / 384 / 84** |
| `grep -c 'results_e6_repeat2'` | **0** |
| forbidden literals `640`, `960`, `352`, `528` anywhere in the file | **0 occurrences of any** |
| every `est_hours.source` non-empty; `e7_band` says `unmeasured` | both hold |
| `wall_clock_summary` names the machine | `machine` names the Windows box, `target_machine` the Linux target |

**The `noise_std` check, stated as the plan's acceptance criterion asks.** `noise_std` appears in
exactly **two** artifact entries — `exp1_band.csv` and `exp1_parameter_band.csv`, both as an
`extra_columns` member and in prose, never as a required column. No other artifact under
`dir: "experiments/results"` names it. Verified programmatically, not by eye.

**Ordering.** All five research constraints are `depends_on` edges, not array positions, because
this project has the lesson filed as *"Wave model can't express temporal constraints"*. O4 is the
uncomfortable one and is recorded as such in `e4`'s own `description`: `e4` must follow
`e2_production` because `resolve_e2_benchmark_path` branch 3 returns `None` and **silently** drops
the real-rig row, giving 9 rows where 10 are expected. That fights D-37's shortest-first ordering,
and `depends_on` wins.

**E1's band is a uniform grid (ruling A1).** 4 seeds × 4 `NOISE_LEVELS` → 256 / 384. The
`rows_rationale` records that `_run_band` is a strict cartesian product (`:1091`, `:1120`) so the
ragged D-41 shape is unreachable, that two invocations would overwrite each other (`force=True` at
`:1177`, `:1202`), and that 0.5 px is one of the four levels — so the headline 97–178× band and all
16 ledger numbers backed by `exp1_band.csv` are untouched.

**E6's band is 84, not 102.** 14 configurations × 6 seeds after D-40 drops the `scale` axis, which
appears in **zero** rows of `numbers-ledger.tsv`. The frozen invocation recorded in the manifest is
`--seeds ${E6_BAND_SEEDS} --axes index,layout,cameras --out ... --force`, matching what plan 26-05
shipped.

### `experiments/_expectations.py` + the gate selector — `8c0c538`

`load_expectations()` validates the stage/artifact bijection in **both** directions and raises
naming the offending id. `check_completeness(out_dir, *, profile, stage=None)` returns
`list[GateResult]` — the existing type, via a late import, because `check_rerun_gates` imports this
module at its top and a module-level import back would be a cycle. A comment says so.

Row counting goes through `check_rerun_gates._load_csv` and counts DATA rows, never lines.

Non-`experiments/results` artifacts resolve as `out_dir.parent / <basename>` — **the same
construction `check_e2_band` uses**, which plan 26-01 proved still works against the archive. It
was deliberately *not* rewritten to an absolute path; a test asserts the sibling behaviour in both
directions.

Exactly three edits to `check_rerun_gates.py`, as the plan requires:

| Acceptance criterion | Result |
|---|---|
| empty-tree roll-up has a FAIL | **60 FAIL of 62** over the now-empty `experiments/results` |
| no-selector run still prints `TOTAL:` and no completeness verdicts | `TOTAL: 102 PASS, 7 N/A, 9 FAIL`; **0** completeness lines |
| `--profile smoke` and `--profile full --stage e6_band` run without traceback | both do; smoke emits 22 completeness verdicts, the stage form emits **3** — strictly fewer than the 62-verdict roll-up |
| `grep -c legality_probe` unchanged | **4** at `e817a03` and **4** now |
| `git diff --stat` on the gate module | **59 insertions, 3 deletions = 62 changed lines** (< 80) |
| `pytest tests/unit/test_rerun_gates.py -q` | **71 passed** |

The no-selector total is 9 FAIL rather than 26-01's 8 because plan 26-02 added
`gate3_run_manifest_present`, which correctly FAILs on an archived tree carrying no manifest. The
102 PASS / 7 N/A figures are unchanged from 26-01's measurement, which is the evidence that no
existing call site's behaviour moved.

**Duplicated shape constants — the choice made, per constant.** All four carry an **authority
comment** naming `experiments/suite_expectations.json` and the exact field to keep in step, rather
than deriving from the manifest. Deriving would make the band gates depend on a manifest load at
import time and would change the behaviour of tests that predate this plan — a bad trade three days
before a freeze. The comment is not left as a plea: `TestShapeConstantReconciliation` makes each one
binding.

| Constant | Choice | Bound to |
|---|---|---|
| `_E6_EXPECTED_SEED_COUNT` | authority comment | `generalization_sweep_band.csv` `rows.full` must be a multiple of it, and the quotient must be 14 |
| `_E5_EXPECTED_SEED_COUNT` | authority comment | `index_sensitivity_seed_band.csv` `rows.full` / it must be 11 |
| `_E2_EXPECTED_RECORD_COUNT` | authority comment | the `e2_band` stage entry |
| `_E4_REPEAT_CELLS` | authority comment | `benchmark_grid_repeat.csv` `rows.full` must equal `2 * len(cells)` |
| `_E6_EXPECTED_CAMERA_VALUES` | **unchanged, deliberately** | asserted still `(8, 12, 16)`; the `cameras` axis survives D-40 |

### `tests/unit/test_expectations.py` — `872754f` (RED) then `db9f0ba`

**77 tests, all passing.** `-k columns` selects **30** (criterion: ≥5). `-k sheet` selects **0** —
plan 26-09's keyword is unclaimed. No `@pytest.mark.skip` or `@pytest.mark.xfail` anywhere
(`grep -c` returns 0). `grep -c 'D-21'` returns 6, `grep -c 'results_e6_repeat2'` returns 2.

**The tripwire was demonstrated red.** A scratch copy of the manifest with `exp1_band.csv`'s
`rows.full` set to `640` failed **two** tests, and the change was discarded (`git status --short`
clean on the manifest afterwards). The failure messages, verbatim:

```
E       AssertionError: ['exp1_band.csv'] declare an expected row count of 640. Phase 25 D-21
        forbids 640 and 960 (they are the Phase 28 shape, unreachable before then); ruling A1
        forbids 352 and 528 (the ragged D-41 grid, which _run_band cannot express). The uniform
        E1 noise grid is 4 seeds x 4 noise levels = 256 / 384 rows.
E       assert ['exp1_band.csv'] == []
```

```
E       AssertionError: the literal 640 appears in suite_expectations.json. Phase 25 D-21 forbids
        640/960 and ruling A1 forbids 352/528 -- even in prose, because the next reader will copy it.
E       assert '640' not in '{\n  "schem...."\n  }\n}\n'
```

`TestCsvToRecordReconciliation` reads `CSV_TO_RECORD`'s 24 keys with `ast` rather than importing the
module, and asserts ≥20 were parsed before comparing — so it cannot report green because a parse or
import quietly failed. All 24 are manifest artifacts.

## Deviations from Plan

**1. [Rule 3 — Blocking] The worktree forked from a stale base.**

- **Found during:** the startup branch check. `git merge-base HEAD e817a03` returned `d27bda7`,
  i.e. HEAD was an *ancestor* of the expected base — the worktree was created before wave 1 merged.
- **Fix:** `git reset --hard e817a03` per the sanctioned startup step, with a clean
  `git status --porcelain` confirmed first. Nothing was lost.
- **Commit:** none (pre-work).

**2. [Rule 1 — Bug] `serial_alone` initially included `preflight`, failing its own criterion.**

- **Found during:** Task 1 verification.
- **Issue:** pre-flight genuinely must not overlap anything, so `serial_alone` looked right — but
  the plan requires that set to be exactly the four timing stages, and review H4's rationale for the
  exemption is **timing integrity**, which pre-flight has none of.
- **Fix:** `preflight` is `concurrent`; every other stage depends on it transitively, so it is alone
  in practice without borrowing an attribute that means something else. Rationale recorded in the
  stage's own `description`.
- **Files modified:** `experiments/suite_expectations.json`
- **Commit:** `8d00c69`

**3. [Deviation, deliberate] `serial_total_hours` is 28.3–31.3 h, not D-51's 22–26 h.**

The plan's Task 1 says `wall_clock_summary` states `serial_total_hours ≈ 22–26` (D-51), while
Task 3's `<behavior>` requires that number to agree with the sum of the stage estimates within 15%.
Those two cannot both hold: the stages sum to a **midpoint of 29.78 h**.

D-51's figure is not wrong — it covers only the stages the three existing drivers already run.
Restricted to those, this manifest sums to **≈26.2 h**, the top of D-51's band. The extra ≈3.5 h is
the seven invocations *no driver has ever carried*: E2's production, timing and memory runs
(≈2.4–4.4 h together) plus the three orphan scripts and pre-flight (≈0.15 h). Rather than pick one
number and hide the other, the manifest carries both — `serial_total_hours` (its own sum, which the
test binds) and `d51_stated_range_hours` beside it, with `serial_total_derivation` explaining the
gap. `expected_total_with_concurrency_hours` lands at **15–17 h**, which reproduces D-52's
independently-stated ≈15–16 h: the four serial_alone stages (≈6.9 h) cannot overlap, and the
concurrent remainder is bounded below by `e6_band` at 8.9 h.

**No runtime figure is attributed to a code change anywhere in the manifest** — a standing
prohibition in this project — and `wall_clock_summary` carries an explicit
`runtime_attribution_warning` saying so. The 19.4 `e1` and `e7` rows are anomalous by ~27× and were
deliberately not used; `e1` comes from the 2026-08-18 probe (318.4 s) and `e7` from 19.3.

## Findings for the Rest of Phase 26

1. **The completeness gate FAILs against the archived baseline, and that is correct.**
   `--profile full --stage e6_band` against `experiments/pre_rerun_baseline/results` reports
   `expected 84 data row(s), found 102`. The archive is the pre-D-40 composition; the manifest
   describes the Phase 28 run. Do **not** "fix" the manifest to match the archive — that would
   re-import the cut D-40 made.

2. **Plan 26-07's driver has four new out-dir variables to define**, because the manifest gives
   `e2_timing` and `e2_memory` their own trees (`experiments/results_e2_timing/`,
   `experiments/results_e2_memory/`) so their `benchmark.json` can never overwrite the production
   run's, plus `${OUT_DIR_E2_BAND}` and `${OUT_DIR_E4_REPEAT}` which already exist in 19.5.

3. **SP-4 is unresolved and the manifest records it as such.** `e2_production`, `e2_timing` and
   `e2_memory` reference `${E2_PRODUCTION_CONFIG}` / `${E2_TIMING_CONFIG}` / `${E2_MEMORY_CONFIG}`.
   `benchmark_memory` and `log_all_observation_depths` are YAML `internals.*` keys, not flags, and
   `emit_seed_variant_configs` cannot produce those variants. Three config YAMLs still have to be
   written by whichever plan owns D-15/D-16.

4. **`_check_git_sha_consistency` was NOT weakened**, per the plan's executor rules. Its
   PASS-on-empty-set branch is untouched. 26-01 recommended giving it an explicit non-PASS
   empty-input verdict; that was deliberately declined here — the completeness gate is now the
   authority on "were the artifacts produced at all", and layering the same job onto Gate 3 would
   recreate the two-sources-of-truth problem. Gate 3's PASS still must never be read as evidence of
   a complete run, and `_expectations.py`'s module docstring says so in those words.

## Verification

| Check | Result |
|---|---|
| `pytest tests/unit/test_expectations.py -x -q` | **77 passed** |
| `pytest tests/unit/test_rerun_gates.py -q` | **71 passed** |
| Both together | **148 passed** |
| Plus `tests/unit/test_run_manifest.py` | **166 passed** |
| `pytest tests/unit/test_experiments_provenance.py -q -m "not slow"` | **295 passed, 25 skipped** — no regression in the file this one reconciles against |
| `pytest tests/unit/test_expectations.py -k columns -q` | **30 passed, 47 deselected** |
| `pytest tests/unit/test_expectations.py -k sheet -q` | **0 selected** (room left for 26-09) |

`PYTHONPATH=<worktree>/src` was exported for every run, with the AquaCal conda interpreter. **The
full suite was NOT run** — that is the orchestrator's post-merge gate. **No experiment, calibration
or driver was executed**; every row count in the manifest comes from a committed artifact, from
declared arithmetic, or from a state-file timestamp.

## Known Stubs

None. Every artifact entry carries a real derivation; the entries with `rows: {}` are the ones
where no design arithmetic pins a count (per-point frames, solver traces, and the two Phase 23-03
artifacts absent from the committed tree), and each says which in its `rows_rationale`. They are
existence-checked under `full`, not skipped.

## Threat Flags

None. No network endpoint, auth path or trust-boundary schema was introduced. T-26-SC holds: this
plan installs nothing and `pyproject.toml` is untouched.

T-26-07 (a green gate over an empty tree) is mitigated and asserted: 60 FAIL of 62.
T-26-08 (manifest drift) is mitigated by `TestColumnConstants`, `TestShapeConstantReconciliation`
and `TestCsvToRecordReconciliation`.
T-26-09 (a gate that cannot pass until Phase 28) is mitigated: the `smoke` profile is
existence-only, and no E1 or E2 single-seed artifact is expected under it at all.

## Self-Check: PASSED

Files confirmed on disk: `experiments/suite_expectations.json`, `experiments/_expectations.py`,
`tests/unit/test_expectations.py`, `experiments/check_rerun_gates.py`.

Commits confirmed in `git log e817a03..HEAD`: `8d00c69`, `872754f`, `8c0c538`, `db9f0ba`.

`STATE.md` and `ROADMAP.md` were **not** modified — the orchestrator owns those writes.
