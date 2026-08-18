---
phase: 26-full-suite-driver-handoff-readiness
plan: 09
subsystem: experiments-docs
tags: [DRIVER-01, DRIVER-03, DRIVER-04, d-05, d-08, d-13, d-36, d-39, d-44, ruling-a3, mf-23]
requires:
  - "experiments/run_experiment_suite.sh: the twenty-stage driver (plan 26-07) — the authoritative invocation list every README row is diffed against"
  - "experiments/suite_expectations.json + experiments/_expectations.py (plan 26-03): the manifest the sheet is rendered from"
  - "experiments/pre_rerun_baseline/ (plan 26-01): the archive the README now names as the baselines' home, and the destination of the two archived drivers"
  - "experiments/e2_real_rig.py --baseline-dir DATA-01b N/A verdict (plan 26-06): the E2 honesty note's factual basis"
  - "experiments/run_experiment_suite.sh pre-flight / sticky exit / concurrency pool (plan 26-08): the README's abort-vs-sticky split and SUITE_WORKERS prose"
provides:
  - "experiments/README.md §2: the twenty-stage invocation table, one row per INVOCATION (D-36)"
  - "experiments/EXPECTATIONS.md: the written hand-verification sheet, rendered region + hand-written --check contract (D-05/D-08/D-13)"
  - "experiments/render_expectation_sheet.py: render_sheet/split_sheet/replace_generated_region/main"
  - "tests/unit/test_expectations.py::TestExpectationSheet: nine freshness tests, -k sheet"
  - ".planning/MANUSCRIPT-FINDINGS.md MF-23: cpr_grouping.tex is generated and never \\input"
  - "exactly ONE suite driver on disk (DRIVER-04 close-out, ruling A3)"
affects:
  - "Phase 27 (portability): prelaunch_gate.sh now reads its seed list from run_experiment_suite.sh; EXPECTATIONS.md is the handoff's expectation document"
  - "Phase 28 (the production run): §7.1 is the launch procedure; EXPECTATIONS.md is what the finished tree is judged against"
  - "Phase 29 (re-baseline): §2 of EXPECTATIONS.md enumerates every schema that pre-declares a header mismatch"
  - "Phase 30 (POST-03 purge): the README cites the pre-rerun-baseline tag as the purge anchor"
  - "the manuscript session: MF-23 is a recorded finding awaiting a decision; nothing was edited"
tech-stack:
  added: []
  patterns:
    - "Generated-region markers in a hand-written markdown file, with a unit test asserting the region matches its source — the sheet analogue of the column-coupling test in 26-03"
    - "A renderer that is a formatter, not a second source of truth: it reads the manifest through the same loader that validates it"
key-files:
  created:
    - experiments/EXPECTATIONS.md
    - experiments/render_expectation_sheet.py
  modified:
    - experiments/README.md
    - tests/unit/test_expectations.py
    - .planning/MANUSCRIPT-FINDINGS.md
    - experiments/prelaunch_gate.sh
  renamed:
    - experiments/rerun_19_4.sh -> experiments/pre_rerun_baseline/driver_state/rerun_19_4.sh
    - experiments/rerun_19_5.sh -> experiments/pre_rerun_baseline/driver_state/rerun_19_5.sh
decisions:
  - "D-43/D-44 conflict resolved as the plan directed: KEEP the renderer and the freshness test. The rollback (delete the module and the -k sheet class, hand-maintain the sheet) remains one commit if the author prefers D-44"
  - "README §7 gained a 7.3 block for the four commands the driver deliberately does NOT run, rather than silently mixing them into the reproduction list"
  - "prelaunch_gate.sh repointed at run_experiment_suite.sh before the archive move — the only live code reference that would have broken"
metrics:
  duration: ~75 min
  tasks: 3
  commits: 4
  completed: 2026-08-18
---

# Phase 26 Plan 09: Handoff Documentation, the Expectation Sheet, and the DRIVER-04 Close-Out

The frozen package now ships with a README that produces the whole suite when followed, a written
expectation sheet provably in step with the manifest, a recorded manuscript finding, and exactly
one driver on disk.

## Commits

| Commit | Task | What |
|---|---|---|
| `df3ed29` | 1 | `experiments/README.md` §2 and §7 rewritten to one row per invocation |
| `adee237` | 2 (RED) | `TestExpectationSheet` — nine failing tests, `-k sheet` |
| `5497d4e` | 2 (GREEN) | `render_expectation_sheet.py` + `EXPECTATIONS.md` |
| `bd055e1` | 3 | MF-23 recorded; both superseded drivers archived |

## Task 1 — README §2/§7

§2 was a 30-row table indexed by *committed artifact*, listing one bare command per experiment.
It contained no `--seeds` row anywhere, so an operator following it produced the manuscript's
single-seed numbers and none of its seed bands — the defect D-36 exists to close. It is now a
twenty-row table indexed by *invocation*, in the driver's execution order, carrying each stage's
wall-clock estimate and its `serial_alone`/`concurrent` attribute from `suite_expectations.json`.
Written by hand, as D-36 directs; deliberately not rendered.

New subsections: **2.1** names `run_experiment_suite.sh` as THE entry point (detached launch,
`--skip-e2`, `SUITE_WORKERS`/`SUITE_SERIAL`, and the abort-vs-sticky split — a pre-flight failure
aborts, a completeness failure sets a sticky non-zero exit and never stops the queue). **2.3**
documents E2's four distinct invocations and why one run cannot honestly produce all four results.
**2.4** states the five ordering constraints as `depends_on` edges. **2.5** consolidates the three
provenance record shapes.

§7 had the identical coverage gap in a shell block. It is now driver-first (7.1), then a
per-experiment reproduction list where every band is present and marked as *the* paper's number
(7.2), then **7.3 — the four commands the driver deliberately does not run**.

### Both stale statements corrected

1. The hardcoded-`E2_BENCHMARK_PATH` claim (old `:81-83`, citing `e4_benchmark_grid.py:226`) is
   gone. FIX-05 in Phase 23 replaced the bare constant with `resolve_e2_benchmark_path`
   (`:261`, constant at `:256`) — **both the claim and the line number were wrong**. The
   replacement states the current mechanism *and* its operational consequence, which is now an
   ordering constraint: the resolver returns `None`, E4 silently drops the real-rig row, and
   `benchmark_grid.csv` comes back with nine rows instead of ten.
2. `### cpr_grouping.csv is the sole origin of tab:cpr` is replaced by D-39's verified finding and
   points at MF-23. The phrase "sole origin of" appears nowhere in the file, including in the
   correction's own wording — the first draft quoted the old claim verbatim and tripped its own
   acceptance grep.

### How the command cross-check was done (T-26-31)

Mechanically, not by eye. A script extracted every `-m experiments.<module>` occurrence from §2 and
§7 together with the long flags following it on the same line, and checked each module against the
set of modules the driver invokes and each flag against the set of flags appearing in the driver.
Result: **40 of 43 (module, flags) combinations matched**. The three that did not:

| README combination | Why |
|---|---|
| `e2_real_rig` with `---config` | A typo produced by an em-dash in prose (`no---config`). **Fixed**, then re-checked. |
| `render_expectation_sheet --check` | §7.3, explicitly labelled as not a driver command. |
| `render_expectation_sheet --write` | §7.3, same. |

**No aspirational command remains in §2 or §7.** The two `render_expectation_sheet` invocations and
the two other §7.3 entries (`e2_real_rig` with no config — the Zenodo reader path of §3 — and
`e4_benchmark_grid --check`) are documented under a heading that says the driver does not run them.
`e4_benchmark_grid --check` is also discussed in §2's E4 prose, as a diagnostic rather than a table
row.

### Acceptance greps

| Check | Required | Actual |
|---|---|---|
| `run_experiment_suite.sh` | ≥1 | 4 |
| `--seeds` | ≥4 | 10 |
| `e7_focal_standoff_analysis\|reconstruction_bootstrap\|fd_jacobian_accuracy` | ≥3 | 13 |
| `config_e2_classification\|config_e2_timing\|config_e2_memory` | ≥3 | 6 |
| `e4_benchmark_grid.py:226` | 0 | 0 |
| `resolve_e2_benchmark_path` | ≥1 | 1 |
| `sole origin of` | 0 | 0 |
| `MF-23` | ≥1 | 1 |
| `pre_rerun_baseline` | ≥1 | 5 |
| forbidden literals `640\|960\|352\|528` | 0 | 0 |

## Task 2 — the expectation sheet and its renderer (TDD)

**RED (`adee237`):** nine tests in `TestExpectationSheet`, all failing on
`ModuleNotFoundError: experiments.render_expectation_sheet`. The module is imported lazily inside
the class so the RED commit fails those nine rather than erroring collection for the whole file —
`9 failed, 77 deselected`.

**GREEN (`5497d4e`):** `9 passed, 77 deselected`; the whole file `86 passed`, later `102 passed`
together with `test_suite_stage_list.py`.

`render_sheet()` derives the generated region entirely from the manifest — per artifact: name,
owning stage, directory, expected rows under `full`, conditional, immutable, and which columns
carry only a SHAPE expectation. `main()` exposes `--check` (exit 1 when stale) and `--write`
(idempotent). The module is a formatter: it loads through `_expectations.load_expectations`, which
is also what validates the manifest, so it cannot become a second source of truth.

### The freshness test genuinely fails when broken

Demonstrated outside pytest as well, on a drifted copy of the manifest (one pinned row count moved,
`exp1_parameter_errors.csv` 24 → 25), with the committed sheet left untouched — `--check` never
writes. Exit code 1, and the message:

```
EXPECTATIONS.md is STALE: its generated region no longer matches experiments/suite_expectations.json. Regenerate it with:
    python -m experiments.render_expectation_sheet --write
```

A failure that does not say how to fix it costs more than no check, so the regeneration command is
a module constant that the message and the docstring both read.

### Acceptance

| Check | Result |
|---|---|
| `render_expectation_sheet --check` against the committed sheet | exit 0 |
| `pytest tests/unit/test_expectations.py -k sheet -q` | 9 selected, 9 passed (≥2 required) |
| `--write` twice | "already up to date." both times; no diff |
| `BEGIN GENERATED` occurrences | exactly 1 |
| Sheet contains `CHECK_EXCLUDED_COLUMNS`, `DATA-01b`, `_E2_METRICS_RTOL`, `optimality`, `DISCARD_KEYS`, a "cannot certify" section | all present |

The hand-written prose carries what a machine cannot derive: the `--check` contract table (one row
per script, naming each schema that MOVED in Phases 23–25 and therefore pre-declares a header
mismatch, with the key property that `exclude_columns` affects the CELL-level comparison only so a
genuine schema change still fails loudly); the E2 honesty note (SP-5 — `--check` survives on **one**
of E2's three artifacts, the other two being DATA-01b-gitignored, and `check_e2_band`'s
`real_rig_metrics.json` comparison at `_E2_METRICS_RTOL = 1e-6` is the better-anchored control);
"existence and row count are not correctness"; the two reading rules (never quote `optimality`
beyond one significant figure; the degeneracy breakdown's cause and fate marginals each sum to the
total and are **never additive together**, from the 32 `DISCARD_KEYS`); and what the sheet cannot
certify.

### Line references verified rather than copied

Two of the plan's `<interfaces>` line numbers had drifted and were corrected against the source
before being written into the sheet: `compare_experiment_csv` is at `_io.py:332` (plan said
`:331`/`:332-338`), and `_E2_METRICS_RTOL` is at `check_rerun_gates.py:1378` (plan said `:1340`).
`CHECK_EXCLUDED_COLUMNS` at `e4_benchmark_grid.py:215` and `resolve_e2_benchmark_path` at `:261`
with the constant at `:256` were confirmed correct as given.

## Task 3 — MF-23 and the DRIVER-04 close-out

**The nine-function grep ran FIRST and passed**, before anything was moved. All nine lifted stage
functions are present in `experiments/run_experiment_suite.sh`:

| Function | Line | From |
|---|---|---|
| `run_stage_prelaunch_probe` | 966 | 19.5 |
| `run_stage_e1` | 1044 | 19.4 |
| `run_stage_e1_band` | 1053 | 19.4 |
| `run_stage_e7` | 1084 | 19.4 |
| `run_stage_e7_band` | 1095 | 19.4 |
| `run_stage_e5_band` | 1136 | 19.5 |
| `run_stage_e6_band` | 1193 | 19.5 |
| `run_stage_e4_repeat` | 1342 | 19.5 |
| `run_stage_e2_band` | 1391 | 19.5 |

Only then were `rerun_19_4.sh` and `rerun_19_5.sh` `git mv`-ed into
`experiments/pre_rerun_baseline/driver_state/`. `git show --stat --find-renames HEAD` shows two
R100% entries and **zero D-status entries**; `git diff --diff-filter=D HEAD~1 HEAD` is empty.
Nothing was deleted (D-32). `ls experiments/*.sh` is now `e6_legal_seed_probe.sh`,
`prelaunch_gate.sh`, `run_experiment_suite.sh`, `seed_sweep_19_3.sh` — one suite driver.

**MF-23** records that `cpr_grouping.tex` is generated on every E3 run and `\input` by nothing;
`tab:cpr` at `supplement.tex:449` is hand-transcribed, six rows, all shared-interface; therefore
`--include-per-camera-latex` stays OFF (D-11) and the fragment is currently decorative. The entry
classes it with "a hand-transcribed parameter count off by ten" and records the interaction that
makes it worth writing down now: Phase 27's pre-freeze gate requires every §3-facing number to have
a generating emitter, and this table is the case that distinguishes "is there an emitter?" (passes)
from "does the published number come *from* the emitter?" (does not). **The manuscript was not
touched** — `git status --porcelain Spinoffs/` is empty, and the tree is not even present in this
worktree.

### Reference sweep

`grep -rn 'rerun_19_[45]\.sh' --include='*.sh' --include='*.py' .` before the move returned hits in
`check_rerun_gates.py` (×4), `e2_real_rig.py` (×2), `e6_generalization_sweep.py`,
`run_experiment_suite.sh` (×5), `test_suite_stage_list.py`, and the two files themselves — **all
comments or docstrings citing the historical source, none resolving a path at run time**. Those are
left alone; so are the `.planning/` and `.planning/milestones/` hits, which are history.

**One live reference would have broken** — see the deviation below.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 — Blocking] `prelaunch_gate.sh` resolved `rerun_19_5.sh` by path at run time**

- **Found during:** Task 3, in the pre-move reference sweep.
- **Issue:** `experiments/prelaunch_gate.sh:175` set
  `QUEUE_SH="$REPO_ROOT/experiments/rerun_19_5.sh"` and grepped it for `E6_BAND_SEEDS` /
  `E5_BAND_SEEDS` to drive the LEGALITY_PROBE. Archiving the file would have made that grep return
  nothing and the gate `fail LEGALITY_PROBE "could not read E6/E5_BAND_SEEDS"` — on the very script
  the rewritten README §7.1 tells an operator to run *first*, before the frozen run. The plan's
  `files_modified` did not include `prelaunch_gate.sh`, so this was a genuine blocker rather than
  optional tidying.
- **Fix:** repointed `QUEUE_SH` at `experiments/run_experiment_suite.sh`. The grep is unchanged —
  the new driver declares both variables in the same shape — and verified to extract
  `42,43,44,45,46,47`, the union of E6's and E5's lists, exactly as before. This is strictly more
  correct than the original: the seeds now come from the script that will actually run, which is
  the stated reason the gate does not keep its own copy. `bash -n` clean. Two accompanying strings
  updated: the echo naming the source file, and the frozen-tree banner, which quoted
  `rerun_19_5.sh`'s stale "~15 h nominal, 26 h ceiling" — now the manifest's ~15–17 h pooled /
  ~28–31 h serial, citing `EXPECTATIONS.md` and the new driver.
- **Files modified:** `experiments/prelaunch_gate.sh`
- **Commit:** `bd055e1`

**2. [Rule 1 — Bug] The §2 correction tripped its own acceptance grep**

- **Found during:** Task 1 verification.
- **Issue:** the rewritten `cpr_grouping` subsection quoted the claim it was correcting verbatim —
  `is "the sole origin of tab:cpr"` — leaving one occurrence of the forbidden phrase.
- **Fix:** reworded the correction to describe the old claim rather than quote it. `grep -c 'sole
  origin of'` is now 0.
- **Commit:** `df3ed29`

### Decisions Recorded, Not Deviations

**The D-43/D-44 conflict was resolved as the plan directed: keep both.** CONTEXT amendment § D's
D-44 cut the renderer and the freshness test; `26-VALIDATION.md`'s contract requires them and
carries a ⚠ note about exactly this. Plan 26-09's `<decisions_implemented>` settled it in favour of
keeping both, and that is what shipped. The rollback stays cheap and is stated here so it does not
have to be reconstructed: delete `experiments/render_expectation_sheet.py` and the
`TestExpectationSheet` class, remove the generated-region markers from `EXPECTATIONS.md`, and
hand-maintain §7. Nothing else in the phase depends on the renderer.

## Threat Model Verification

| Threat | Disposition | Evidence |
|---|---|---|
| T-26-31 — a documented command the driver does not run | mitigated | Mechanical (module, flags) cross-check; 40/43 matched, one typo fixed, two labelled under §7.3 |
| T-26-32 — a sheet that drifted from the manifest | mitigated | Nine `-k sheet` tests; staleness demonstrated to exit 1 with the regeneration command named |
| T-26-33 — editing the read-only manuscript tree | mitigated | `git status --porcelain Spinoffs/` empty; the tree is absent from this worktree entirely |
| T-26-34 — archiving before the lift | mitigated | Nine stage functions grepped with line numbers BEFORE the `git mv`; zero D-status entries in the commit |
| T-26-SC — package installs | N/A | Nothing installed; `pyproject.toml` untouched |

## Known Stubs

None. Every artifact this plan created is complete and exercised: the sheet renders, the renderer's
`--check` and `--write` both work, and the tests assert the coupling rather than its existence.

## Deferred Issues

- **`.planning/` and `.planning/milestones/` still name `experiments/rerun_19_4.sh` /
  `rerun_19_5.sh` at their old paths.** Deliberately not rewritten — those are historical records
  of what was run. The dangling-reference audit proper (`linux32gb_scope.json`, test fixtures) is
  Phase 30's, per the plan's `executor_rules`.
- **`experiments/README.md` §3's DATA-01a paragraph** still describes the Zenodo frameset gap in
  Phase 21 terms. Out of this plan's scope (§2/§7 only) and unchanged.

## Verification

| Check | Result |
|---|---|
| `python -m experiments.render_expectation_sheet --check` | exit 0 |
| `pytest tests/unit/test_expectations.py -q` | 86 passed |
| `pytest tests/unit/test_expectations.py -k sheet -q` | 9 passed, 77 deselected |
| `pytest tests/unit/test_suite_stage_list.py tests/unit/test_expectations.py -q` | 102 passed |
| `ls experiments/*.sh` | exactly one suite driver |
| `git status --porcelain Spinoffs/` | empty |

The full unfiltered suite was **not** run — that is the orchestrator's post-merge gate.
