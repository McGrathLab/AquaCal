# Phase 26: Full-Suite Driver & Handoff Readiness - Research

**Researched:** 2026-08-18
**Domain:** Bash queue driver, Python gate/manifest tooling, experiment CLI surface, git-tracked artifact trees
**Confidence:** HIGH for every claim about this codebase (all file-anchored and tool-verified); MEDIUM for runtime/schedule figures inherited from CONTEXT.

> **Scope note.** This is a *codebase ground-truth* research pass, not a library-ecosystem pass.
> Every stack decision in this phase is already locked by CONTEXT (bash driver, `check_rerun_gates.py`,
> `experiments/_io.py`). No external package is introduced, so there is no Package Legitimacy Audit
> section — the phase installs nothing. The value here is the **eight stale premises** in § Stale
> Premises, each of which would produce a hallucinated or unimplementable task if the planner
> trusted CONTEXT alone.

---

<user_constraints>
## User Constraints (from CONTEXT.md)

CONTEXT.md is 47 KB and carries D-01..D-52 plus a two-part amendment. It is the authority and must
be read in full by the planner. Copied verbatim below are only the sections whose *shape* the
planner needs while reading this research. **Where the amendment (§ D, § E) conflicts with
D-01..D-39, the amendment wins** — CONTEXT states this explicitly.

### Locked Decisions — the load-bearing subset

- **D-01 / D-03:** a completeness FAILURE never aborts the queue (sticky flag → non-zero final
  exit); **pre-flight** failure DOES abort. Both halves must be stated together in the driver header.
- **D-02:** completeness checked at three points — pre-flight, after each stage, end-of-run roll-up.
- **D-04:** the completeness gate is a **new gate inside `check_rerun_gates.py`** taking a stage /
  expectation selector.
- **D-05:** a machine-readable **expectation manifest** is the single source of truth.
- **D-06 + D-49:** two profiles. `smoke` asserts artifact **existence only**; `full` asserts row
  counts. **No Phase 26 gate may assert 640/960 or require `noise_std` in `experiments/results/`.**
- **D-09 → REVERSED by D-42:** `e6_repeat2` is **OFF**. The gate must not expect
  `results_e6_repeat2/` under **either** profile.
- **D-10:** E3's `--check`-then-`--force` ordering stays; rationale rewritten to "E3 is one of only
  two experiments whose `--check` is still a real reproduction signal".
- **D-11:** `--include-per-camera-latex` stays OFF.
- **D-12:** surviving `--check` paths gain an explicit **`--baseline-dir`**, threaded by the driver
  at the archive directory.
- **D-13:** the `--check` verdict is settled — hand-verify, re-baseline in Phase 29. Phase 26
  **documents** `compare_experiment_csv(..., exclude_columns=())`; it does not reinvent it.
- **D-14 / D-17:** a missing E2 frameset hard-fails pre-flight unless declared via `--skip-e2`;
  pre-flight asserts frameset **IDENTITY** (262 usable → 52 validation → 7,762 comparisons).
- **D-15 / D-16:** E2 is multi-invocation — production/classification, band, **timing and memory as
  two distinct runs**. `internals.log_all_observation_depths` rides the classification run only.
- **D-18 → DOWNGRADED by D-45:** record `git describe --tags --long --dirty` in the **run manifest
  only**. Do **not** change the provenance schema in `src/aquacal/io/benchmark.py`.
- **D-19 / D-20:** manifest written by a **Python emitter** beside `experiments/_io.py`, invoked
  once at pre-flight. Contents: git sha, `git describe`, dirty state, OS/kernel, Python, NumPy,
  SciPy, **OpenCV including the PyPI build suffix**, machine id, UTC start.
- **D-21:** Gate 3 extends over the manifest with **all-hard-FAIL** semantics.
- **D-22:** the pre-run sha is tagged **`pre-rerun-baseline`**.
- **D-23 → HALVED by D-48:** keep the **sha-derived state-file path**; cut the HEAD-vs-state refusal.
- **D-24 → NARROWED by D-46/D-47:** cut the disk-headroom estimator (log free space, crude floor);
  **cut the dirty-tree refusal** (`experiments/results/` is tracked → the run dirties its own tree →
  a dirty-tree refusal would refuse every resume).
- **D-25:** `git mv` to `experiments/run_experiment_suite.sh`. State and frozen-sha files follow the
  same stem.
- **D-26:** do **not** rewrite the driver in Python for this run.
- **D-27:** the commit rule relaxes — only the **RUN MACHINE's** tree must not move.
- **D-28 / D-29 / D-30 / D-31 / D-32:** the archive-aside is a committed Phase 26 step immediately
  after tagging; scope is all six tracked results trees plus loose state/logs plus the untracked
  `verify_23*/`; **nothing is deleted**; the archive name must not collide with `experiments/archive/`.
- **D-33 / D-34:** three forms of acceptance — one full `--smoke` pass (**ORCHESTRATOR's run, never
  an executor's**), the dry-run harness extended, unit tests over stage list / manifest / expectations.
- **D-35:** Linux-side smoke is Phase 27, not 26. Write portability-sensitive constructs
  conservatively anyway.
- **D-36:** `experiments/README.md` §2 is rewritten **by hand**, one row per *invocation*.
- **D-37 / D-38:** shortest-first ordering holds; a per-stage wall-clock estimate summing to a
  stated total is a deliverable.
- **D-39:** record an MF-NN for `cpr_grouping.tex` never being `\input`. Record only — do not edit
  the manuscript.
- **D-40:** drop E6's `scale` axis (18 of 102 band cells, ~1.9 h). E6's `index` axis stays at 8.
- **D-41:** E1's noise axis runs **10 seeds at 0.5 px and 4 seeds at each of {0.25, 0.82, 1.2}** —
  **352 / 528 rows**, superseding Phase 25's flat 640/960. **Any gate asserting 640 is wrong.**
- **D-42:** `e6_repeat2` OFF.
- **D-43:** CUT D-07's column-constant coupling test.
- **D-44:** CUT D-08's renderer and freshness test — hand-write the prose expectation sheet once.
- **D-50:** *every pre-flight refusal must print the exact override flag that bypasses it, and
  nothing may abort once stage 1 has begun.*
- **D-51:** corrected serial estimate ≈ **22–26 h** at Windows-box speed, dominated by `e6_band`
  at ~8.9 h (~40% of the suite).
- **D-52:** **selective concurrency ADOPTED.** Stage list gains a serial/concurrent attribute plus a
  worker count. Serial-and-alone: `e4`, `e4_repeat`, `e2_timing`, `e2_memory`. Concurrent 4–5 wide:
  every accuracy stage. Three hard constraints: (1) `e6_repeat1` and `e6_band` must never overlap;
  (2) at most one 200-frame-class stage at a time; (3) concurrent stages share
  `experiments/results/` so filename disjointness must be verified against the manifest.

### Claude's Discretion

- The expectation manifest's file format, location, and schema (JSON / YAML / Python module), and
  how "exists only when at least one flagged row exists" is expressed declaratively.
- The archive directory's exact name (must not collide with the existing `experiments/archive/`).
- Whether `check_rerun_gates.py` is factored before the completeness gate is added to it.
- The exact stage identifiers and the internal shape of `STAGES=()` under multi-invocation stages.
- Plan decomposition and commit granularity, subject to the one-commit-per-requirement habit held
  through Phases 23–25.

### Deferred Ideas (OUT OF SCOPE)

- Rewriting the driver in Python (D-26).
- Purging the archive directory — Phase 30 / POST-03 (D-32).
- Post-run `--check` re-baselining and restoring automated checking — Phase 29.
- The dangling-reference audit before the purge (`linux32gb_scope.json`, `README.md` §2,
  `check_rerun_gates.py`, test fixtures) — Phase 30. **⚠ See Stale Premise SP-1: part of this
  cannot wait for Phase 30.**
- Editing the manuscript to `\input` `cpr_grouping.tex` — the manuscript session's call.
- Linux-side portability verification — Phase 27 / RUN-01 (D-35).
- Splitting `e6_band` across processes by seed (§ C of the amendment, explicitly not attempted).

</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description (`.planning/REQUIREMENTS.md`) | Research Support |
|----|-------------|------------------|
| **DRIVER-01** | `rerun_19_3.sh` covers every invocation in the suite, including the band runs and E2 | § Current Driver Coverage gives the exact union of the three existing drivers, the seven genuinely-missing invocations, and the five real ordering constraints (two of which CONTEXT does not name). § Stale Premises SP-2/SP-3 flag that two locked cuts (D-40, D-41) are not expressible with today's CLI surface. |
| **DRIVER-02** | The suite emits one run manifest with `aquacal_version` and the OpenCV build recorded truthfully | § Provenance Ground Truth: `capture_environment` at `src/aquacal/io/benchmark.py:67`, the exact defect line (`:125`), the verified mechanism for the OpenCV build suffix, and the verified `git describe` output. § Stale Premise SP-6 corrects the "E5/E6 record only a seed" belief. |
| **DRIVER-03** | `--check` has a decided, documented meaning across a deliberate baseline re-base | § The `--check` Surface: a per-script table of which `_run_check` exists, what baseline path it resolves, and how many `compare_experiment_csv` calls it makes. § Stale Premise SP-5 shows E2's `--check` is **already broken** (2 of its 3 baselines are gitignored by policy), which materially weakens CONTEXT's "survives on E2 and E3 only". |
| **DRIVER-04** | Every pre-re-run output tree is moved aside before the run | § The Output Trees: exact tracked/untracked/size inventory matching D-29 and D-30. § Stale Premise SP-1: the move **breaks four unit tests immediately**, in Phase 26, not Phase 30. |

</phase_requirements>

---

## Summary

CONTEXT's picture of the driver is **materially incomplete in the direction that matters**: it
treats `experiments/rerun_19_3.sh` as "the queue to rename and extend", and reads as though the
band stages must be written from scratch. In fact there are **three** drivers on disk —
`rerun_19_3.sh` (290 lines), `rerun_19_4.sh` (417) and `rerun_19_5.sh` (487) — and 19.4/19.5 already
implement, in production-proven form, the E1 band, the E7 band, the E6 band, the E5 band, E2's band,
E4's repeat, a hard-abort pre-flight probe, a pinned gate interpreter, and the dry-run/state-file
separation fix. The correct framing for the planner is **union-and-lift**, not "extend 19.3": the
new `run_experiment_suite.sh` should be assembled from the best of all three, and 19.5 is the most
evolved base, not 19.3. Only **seven** invocations are genuinely absent from every driver.

Three locked decisions cannot be implemented as written against today's code. D-40 (drop E6's
`scale` axis) and D-41 (E1's ragged 10/4/4/4 noise grid) both require **experiment-script code
changes** — E6 has no axis-selection flag and `build_axis_configurations` is unconditional
(`e6_generalization_sweep.py:400-460`); E1's `_run_band` runs a strict cartesian
`seeds × NOISE_LEVELS` (`e1_refractive_comparison.py:1091,1120`) with no way to vary seed count per
level. D-15/D-16 (E2's four invocations, `log_all_observation_depths` on the classification run
only) is likewise not expressible: `benchmark_memory` and `log_all_observation_depths` are YAML
`internals.*` keys (`src/aquacal/config/schema.py:373-374`), not CLI flags, and the only config
generator that exists — `emit_seed_variant_configs` — varies **seed and output_dir only**.

The single most expensive omission is DRIVER-04's blast radius. `experiments/results/` is read
**unguardedly** by four unit tests, and `test_experiments_provenance.py:640`
(`test_csv_to_record_has_no_stale_entries`) asserts that every key of a ~30-entry map exists on
disk there. Moving the tree aside makes the test suite red **at the frozen sha** — which is exactly
what Phase 27 must package and Phase 28 must run. CONTEXT defers the "test fixtures" audit to
Phase 30, but that deferral covers the *purge*; the *move* lands in Phase 26 and breaks things now.

**Primary recommendation:** plan Phase 26 as five commits — (1) archive-aside + the four test fixes
it forces, (2) the manifest emitter and its Gate-3 extension, (3) the expectation manifest + the
new selector-taking completeness gate in `check_rerun_gates.py`, (4) the union driver lifted from
19.5 with `--baseline-dir` threading and the D-40/D-41/D-15 code changes it depends on, (5) the
README §2 rewrite + hand-written expectation sheet + MF-NN. Sequence (1) first so the test breakage
is visible and fixed before anything is built on top of it, and treat the D-40/D-41/D-15 code
changes as a **named risk** requiring an explicit go/no-go — they are experiment-script edits days
before a freeze, which is the class of change D-45 just refused for a smaller reason.

---

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Stage sequencing, resume, sticky exit, concurrency pools | **Bash driver** (`experiments/run_experiment_suite.sh`) | — | D-26 locks bash. All state/recovery machinery already lives there. |
| Environment capture → run manifest | **Python emitter** (new, beside `experiments/_io.py`) | Bash driver (invokes once at pre-flight) | D-19: bash cannot get NumPy/SciPy/OpenCV build strings reliably. |
| Expectation manifest (artifact/row/column inventory) | **Data file** (JSON, `experiments/`) | Python gate (reads it) | D-05. A data file is diffable and importable; neither bash nor a Python module alone gives both. |
| Completeness verdict | **`check_rerun_gates.py`** (new gate + selector) | Bash driver (calls it, records sticky flag) | D-04: one tool owns "was this run good"; it already has `_load_json`/`_load_csv`/`GateResult`. |
| Baseline resolution for `--check` | **Experiment scripts** (new `--baseline-dir`) | Bash driver (passes the archive path) | D-12. The scripts resolve baselines by path today; only they can decouple read-path from write-path. |
| Per-experiment artifact production | **Experiment scripts** (unchanged where possible) | — | D-52: "requires no change to any experiment". ⚠ D-40/D-41/D-15 violate this — see SP-2/SP-3/SP-4. |
| Archive-aside | **Git / orchestrator commit** | — | D-28: a committed Phase 26 step, explicitly *not* a driver action. |

---

## Current Driver Coverage — the exact ground truth

### The three drivers on disk

| File | Lines | `STATE_FILE` | `STAGES=(...)` |
|---|---|---|---|
| `experiments/rerun_19_3.sh` | 290 | `rerun_19_3_state.tsv` (`:91`) | `e3 e7 e1 e5 e6_repeat1 e6_repeat2 e4` (`:93`) |
| `experiments/rerun_19_4.sh` | 417 | `rerun_19_4_state.tsv` (`:125`) | `e6_repeat1 e4 e6_repeat2 e6_seed43 e7 e1 e5 e3` (`:144`) |
| `experiments/rerun_19_5.sh` | 487 | `rerun_19_5_state.tsv` / `.dryrun.tsv` (`:181-185`) | `prelaunch_probe e6_band e4_repeat e2_band e5_band` (`:225`) |

`[VERIFIED: wc -l, sed]`

### Every invocation present across the three, with exact flags

| Stage | Invocation (verbatim) | Source |
|---|---|---|
| `e3` (a) | `python -u -m experiments.e3_derived_quantities --check --out "${OUT_DIR}"` | `rerun_19_3.sh:150` |
| `e3` (b) | `python -u -m experiments.e3_derived_quantities --force --out "${OUT_DIR}"` | `rerun_19_3.sh:157` |
| `e7` single | `python -u -m experiments.e7_interface_ablation --force --out "${OUT_DIR}"` | `rerun_19_4.sh:298` |
| `e7` band | `python -u -m experiments.e7_interface_ablation --seeds "${BAND_SEEDS}" --out "${OUT_DIR}"` | `rerun_19_4.sh:305` |
| `e1` single | `python -u -m experiments.e1_refractive_comparison --force --out "${OUT_DIR}"` | `rerun_19_4.sh:322` |
| `e1` band | `python -u -m experiments.e1_refractive_comparison --seeds "${BAND_SEEDS}" --out "${OUT_DIR}"` | `rerun_19_4.sh:329` |
| `e5` single | `python -u -m experiments.e5_index_sensitivity --force --out "${OUT_DIR}"` | `rerun_19_3.sh:184` |
| `e5` band | `python -u -m experiments.e5_index_sensitivity --seeds "${E5_BAND_SEEDS}" --out "${OUT_DIR}" --force` | `rerun_19_5.sh:421-422` |
| `e6_repeat1` | `rm -rf "${OUT_DIR}/e6_configs"; rm -f generalization_sweep.csv e6_provenance.json` then `--force --out "${OUT_DIR}"` | `rerun_19_3.sh:195-200` |
| `e6` band | `python -u -m experiments.e6_generalization_sweep --seeds "${E6_BAND_SEEDS}" --out "${OUT_DIR}" --force` | `rerun_19_5.sh:326-327` |
| `e6_repeat2` | isolated dir, `tee`, `PIPESTATUS[0]`, `grep -c "already exists (resumability)"` | `rerun_19_3.sh:204-228` — **OFF per D-42** |
| `e6_seed43` | `--force --seed 43 --out "${OUT_DIR_E6_SEED43}"` | `rerun_19_4.sh:282` — probe, not a suite stage |
| `e4` | `python -u -m experiments.e4_benchmark_grid --force --out "${OUT_DIR}"` | `rerun_19_3.sh:235` |
| `e4_repeat` | `for repeat in 1 2; for cell in 8x100 12x100 16x100: --cell "$cell" --out "${OUT_DIR_E4_REPEAT}" --force`, then `--splice-repeat "${OUT_DIR_E4_REPEAT}" --out "${OUT_DIR}"` | `rerun_19_5.sh:349-372` |
| `e2_band` (emit) | `--emit-band-configs --config "${E2_RELEASE_CONFIG}" --band-seeds "${E2_BAND_SEEDS}" --band-dir "${OUT_DIR_E2_BAND}"` | `rerun_19_5.sh:389-393` |
| `e2_band` (run) | per seed: `--config "${OUT_DIR_E2_BAND}/config_seed${seed}.yaml" --out "${OUT_DIR_E2_BAND}/seed_${seed}_e2_out" --force` | `rerun_19_5.sh:404-407` |
| `prelaunch_probe` | inline heredoc calling `experiments.check_rerun_gates.legality_probe` | `rerun_19_5.sh:296-311` |

`[VERIFIED: sed over all three files]`

### The seven invocations genuinely absent from every driver

| # | Missing invocation | Evidence of absence | Notes for the planner |
|---|---|---|---|
| M1 | **E2 production / classification run** | No `e2_real_rig` invocation outside `e2_band` in any driver | Needs `--config <release config> --out experiments/results --force` **plus** `internals.log_all_observation_depths: true` (D-16), which is a **config key, not a flag** — see SP-4. |
| M2 | **E2 timing run** | absent | Requires a config with `internals.benchmark_memory: false`. |
| M3 | **E2 memory run** | absent | Requires a config with `internals.benchmark_memory: true`. Two distinct runs, D-15, non-negotiable. |
| M4 | **`e7_focal_standoff_analysis`** | `grep -rn` across `*.sh` returns **zero** hits | `python -u -m experiments.e7_focal_standoff_analysis --out "${OUT_DIR}"` (documented at `e7_focal_standoff_analysis.py:44`). |
| M5 | **`reconstruction_bootstrap`** | zero hits | `python -u -m experiments.reconstruction_bootstrap --out "${OUT_DIR}" --force`. |
| M6 | **`fd_jacobian_accuracy`** | zero hits | `python -u -m experiments.fd_jacobian_accuracy --out "${OUT_DIR}" --force`. |
| M7 | **E1's noise-axis band at D-41's ragged shape** | no `--noise-*` flag exists anywhere | See SP-3. |

`[VERIFIED: grep -rn --include=*.sh over experiments/]`

### Ordering constraints — five, not three

CONTEXT names three (`## Integration Points`). Two more are real and unnamed.

| # | Constraint | Anchor |
|---|---|---|
| O1 | `e7_focal_standoff_analysis` **after** E7's band | `e7_focal_standoff_analysis.py:389` reads `Path("experiments/results")/interface_ablation_band.csv` |
| O2 | `reconstruction_bootstrap` **after** E2 | `reconstruction_bootstrap.py:171-173` resolution order prefers `experiments/results/reconstruction_errors.csv`; `:56` `REAL_RIG_METRICS_PATH = Path("experiments/results/real_rig_metrics.json")` is a hard read |
| O3 | `fd_jacobian_accuracy` anywhere | no external input |
| **O4 (new)** | **`e4` must run AFTER E2's production run** | `e4_benchmark_grid.py:298` — `resolve_e2_benchmark_path` looks for `out_dir/benchmark.json`; branch 3 returns `None` and the real-rig row is **silently dropped**. Under DRIVER-04's move `experiments/results/benchmark.json` will not exist, so E2 *must* have written it first. `benchmark_grid.csv` is 10 rows = 9 synthetic + 1 real-rig; without E2 first it is 9. |
| **O5 (new)** | **`e3` `--check` must run before anything regenerates its inputs**, and E3's own `--force` must follow immediately | `rerun_19_3.sh:32-45` header; the two invocations are one stage by construction |

`[VERIFIED: sed, grep]`

⚠ **O4 fights D-37 (shortest-first) and D-52 (concurrency).** E2's production run is ~50–87 min and
E4 is ~3.6 h; shortest-first would put E4 before E2 if only wall clock were consulted. It also
fights D-52's "serial and alone: e4, e2_timing, e2_memory" grouping — E2's *production* run is not
in that list but E4 depends on it. The stage list must carry an explicit `depends_on`, not rely on
array order (this project has the exact lesson recorded: *"Wave model can't express temporal
constraints"*).

### Reusable machinery, by anchor

| Asset | Location | Note |
|---|---|---|
| `is_stage_complete()` awk over state TSV | `rerun_19_3.sh:100-106` (identical `rerun_19_5.sh:232-238`) | start-line-without-completion ⇒ re-run from scratch |
| `state_start` / `state_complete` | `:108-116` / `:240-248` | ISO-stamped; this is the **only** per-stage timing record that exists (see § Runtime) |
| `run_gate_check` (always returns 0) | `rerun_19_3.sh:118-127`; **pinned-interpreter version** `rerun_19_5.sh:250-263` | D-01's sticky flag changes the **caller**, not this function |
| `GATE_PYTHON` pin + fallback | `rerun_19_5.sh:219-223` | ⚠ `rerun_19_3.sh:121` uses bare `python` — a known defect fixed in 19.4/19.5. **Lift 19.5's version.** |
| Dry-run seam | `rerun_19_3.sh:129-143` (`RERUN_19_3_DRY_RUN` / `_CMD`) | rename per D-25 |
| **Dry-run state-file separation** | `rerun_19_5.sh:174-185` | ⚠ absent from 19.3. Without it a dry run leaves a state file that makes the next real launch a silent no-op — the exact hazard D-23 describes. **Lift.** |
| `e6_repeat2` isolation template | `rerun_19_3.sh:204-228` | `tee` + `PIPESTATUS[0]` + `grep -c "already exists (resumability)"` — the template for any stage that must not reuse checkpoints |
| Hard-abort pre-flight pattern | `rerun_19_5.sh:455-463` | exactly D-03's shape, already proven |
| `_collect_all_json_paths` / `_check_git_sha_consistency` | `check_rerun_gates.py:1711` / `:1732` | Gate 3; D-21 extends it |
| `run_all_gates` | `check_rerun_gates.py:1768-1830` | 13 call sites; the completeness gate joins here |
| `compare_experiment_csv(..., exclude_columns=())` | `experiments/_io.py:332-338` | docstring at `:376-381` already names Phase 26 / DRIVER-03 |
| `capture_environment` | `src/aquacal/io/benchmark.py:67` | the manifest emitter's foundation |
| `build_experiment_arg_parser` (the five-flag contract) | `experiments/_io.py:43-87` | `--seed --out --force --smoke --check`. A shared `--baseline-dir` would go here — but see SP-5 on *which* scripts actually need it |

---

## ⚠ Stale Premises — verify these before planning

These are the highest-value findings in this document. Each is a place where a locked decision or a
CONTEXT assertion does not match the code.

### SP-1 — DRIVER-04's move breaks four unit tests **in Phase 26**, not Phase 30

CONTEXT defers the dangling-reference audit (naming "test fixtures") to Phase 30. That deferral is
attached to the **purge**. The **move** happens in Phase 26 (D-28) and the breakage is immediate.

Unguarded reads of `experiments/results/`:

| Test | Anchor | Failure mode after the move |
|---|---|---|
| `test_csv_to_record_has_no_stale_entries` | `tests/unit/test_experiments_provenance.py:640-656` | `stale = set(CSV_TO_RECORD) - on_disk - PENDING_CSVS`; `PENDING_CSVS` is `frozenset()` (`:255`) and `CSV_TO_RECORD` starts at `:106`. Empty dir ⇒ every entry stale ⇒ **FAIL** |
| `test_self_describing_json_files_are_named_and_exist` | `:704` | same class |
| `test_scale_bias_matches_e1_committed_column` | `tests/unit/test_experiments_e5.py:90` | bare `pd.read_csv("experiments/results/exp2_depth_generalization.csv")` ⇒ **FileNotFoundError** |
| `test_e1_committed_record_has_no_seed_key` | `tests/unit/test_experiments_io.py:758` | bare `.read_text()` on `experiments/results/e1_benchmark_refractive.json` ⇒ **FileNotFoundError** |
| `tests/unit/test_experiments_e3.py:275` | `BENCHMARK_JSON_PATH` module constant | depends on downstream use; audit |

*Mitigating detail:* the **discovery** helpers degrade cleanly —
`_discover_json_files` / `_discover_csv_files` return `[]` when `RESULTS_DIR` is absent
(`test_experiments_provenance.py:277-279, 311-315`), so the parametrized suites go quiet rather
than erroring. It is the two **exhaustiveness** assertions and the two **bare reads** that break.

**Planning consequence:** the archive-aside plan must include the test updates in the same commit,
or the frozen sha ships a red suite. Point the four reads at the archive directory (they are
asserting properties of *committed baselines*, which is what the archive now holds).
`[VERIFIED: sed over the four test files]`

### SP-2 — D-40 (drop E6's `scale` axis) requires an E6 code change

`build_axis_configurations` (`experiments/e6_generalization_sweep.py:400-460`) unconditionally
emits `index` (8 values, `:139`), `layout` (3, `:144`), `scale` (3, `:214`) and — behind
`include_cameras_axis` — `cameras` (3, `:155`). The only selector is `include_cameras_axis`
(`:1406`); there is **no** flag or parameter to drop `scale`. E6's CLI has exactly two extra flags:
`--no-fail-fast` (`:1446`) and `--seeds` (`:1459`).

17 configs × 6 seeds = 102 rows, matching the committed `generalization_sweep_band.csv` (102 rows,
verified). Dropping `scale` gives 14 × 6 = 84. `check_e6_seed_band` also hardcodes
`_E6_EXPECTED_SEED_COUNT = 6` (`check_rerun_gates.py:948`) and
`_E6_EXPECTED_CAMERA_VALUES = (8, 12, 16)` (`:949`) — the gate has its own copy of the shape.

**D-40 is not a driver change. It is an E6 source change plus a gate-constant change.**
`[VERIFIED: grep + sed + wc on the committed CSV]`

### SP-3 — D-41's ragged E1 noise grid is not expressible by today's E1

`_run_band` (`e1_refractive_comparison.py:1046`) builds
`noise_levels = [None] if smoke else NOISE_LEVELS` (`:1091`) and loops it **inside** the per-seed
runner (`:1120`). Every seed runs at every level — a strict cartesian product. `NOISE_LEVELS`
(`:217`) is `[0.25, 0.5, 0.82, 1.2]`. E1's only script-local flag is `--seeds` (`:1329`).

D-41 asks for 10 seeds at 0.5 and 4 seeds at each of the other three ⇒ 352 / 528 rows. Today's code
produces 640 / 960 for 10 seeds, or 256 / 384 for 4 seeds. **352 is unreachable.**

Two invocations do not work either: both write `exp1_band.csv` and `exp1_parameter_band.csv` with
`force=True` (`:1177`, `:1202`) — the second invocation **overwrites** the first, and no merge
tooling exists.

**Options for the planner, in preference order:**
1. Add a script-local `--noise-levels` (comma list) to E1 and invoke twice into **different** out
   dirs, then add a small merge step. Two code changes.
2. Add a `--noise-plan` accepting `level:seed_count` pairs. One code change, one invocation, no merge.
3. **Descope D-41 back to a uniform grid** (e.g. 4 seeds × 4 levels = 256/384, or 10 × 4 = 640/960)
   and raise the cost to the author. This is the only zero-code-change path.

Whichever is chosen, the **expectation manifest's `full`-profile row count must follow it**, and
D-06's prohibition (`no Phase 26 gate may assert 640`) means the `smoke` profile asserts existence
only — that part is already safe. `[VERIFIED: sed over e1_refractive_comparison.py; row counts from
the committed CSVs]`

### SP-4 — E2's four invocations need four config YAMLs, and nothing generates them

`benchmark_memory` and `log_all_observation_depths` are **YAML `internals.*` keys**
(`src/aquacal/config/schema.py:373-374`, read at `src/aquacal/calibration/pipeline.py:390-392`),
not CLI flags. E2's CLI (`e2_real_rig.py:842-905`) has exactly four extra flags: `--config`,
`--emit-band-configs`, `--band-seeds`, `--band-dir`.

`emit_seed_variant_configs` (`e2_real_rig.py:792`) varies **only** the top-level `seed:` and
`paths.output_dir` (documented at `:874-878`). It cannot produce a memory-on or h_q-logging variant.

So D-15/D-16 requires one of: (a) three additional hand-written config YAMLs committed in-repo and
pointed at by `--config`; (b) extending `emit_seed_variant_configs` (or a sibling) to set arbitrary
`internals.*` overrides; (c) a new `--internals key=value` passthrough flag on E2. **(a) is the
lowest-risk pre-freeze option** and keeps the config content reviewable in a diff — which matters,
because CONTEXT's own § Specific Ideas notes that `--smoke` *cannot* catch a bad production YAML.

Note also `E2_RELEASE_CONFIG="C:/Users/tucke/Desktop/Aqua/AquaCal/release_calibration/config.yaml"`
(`rerun_19_5.sh:209`) is an **absolute Windows path**. It resolves today `[VERIFIED: ls]`, but it
cannot travel to the Linux machine. Phase 27 owns portability, but the stage list must make this a
variable with an override, not a literal. `[VERIFIED: grep + sed]`

### SP-5 — E2's `--check` is already broken; the "E3 and E2 only" table is optimistic

`e2_real_rig._run_check` (`:477`) compares **three** CSVs against `args.out`:
`camera_parameters.csv`, `reprojection_residuals.csv`, `reconstruction_errors.csv` (`:497-527`).

Only `camera_parameters.csv` is present in `experiments/results/`. The other two are **gitignored by
deliberate policy (DATA-01b)** — `.gitignore:238-239`. And `compare_experiment_csv` opens with a
bare `committed = pd.read_csv(committed_path)` (`experiments/_io.py:390`), whose docstring states
its only propagating exception is exactly this: *"I/O errors reading `committed_path` (e.g. the
file does not exist)"* (`:353-356`).

So on a clean checkout `python -m experiments.e2_real_rig --check` **raises FileNotFoundError after
a ~50–87 minute calibration**. It only works on a box that has just re-run E2 locally.

**Consequences:**
- DRIVER-03's blast-radius table ("`--check` survives meaningfully on E3 and E2 only") is
  overstated for E2 — it survives on **one of E2's three artifacts**, and only when the local tree
  is warm.
- D-12's `--baseline-dir` for E2 must **also** tolerate a missing baseline gracefully (report N/A,
  not crash), or the archive's copies of those two files must be the baseline — but the archive
  will not have them either, for the same DATA-01b reason.
- The E2 ~1e-8 sanity anchor CONTEXT relies on is more accurately anchored on
  `real_rig_metrics.json`, which `check_e2_band` already compares numerically at
  `_E2_METRICS_RTOL = 1e-6` (`check_rerun_gates.py:1340`). That is a working mechanism; `--check`
  is not. `[VERIFIED: ls, grep .gitignore, sed]`

### SP-6 — "E5/E6 record only a seed" is stale

Project memory carries *"E5/E6 record only a seed, not full provenance"*. That was fixed in Phase
19.2 wave 5. Both call `capture_environment`: `e5_index_sensitivity.py:366`,
`e6_generalization_sweep.py:1327, 1578, 1687`, and `e5_provenance.json` / `e6_provenance.json` are
committed. `experiments/README.md:55-57` documents the fix. **DRIVER-02 has no E5/E6 defect to
close.** `[VERIFIED: grep -rn capture_environment; ls experiments/results/]`

### SP-7 — a `--smoke` pass writes almost nothing to the output tree

D-33's acceptance form 1 and D-49's `smoke`-profile "artifact existence" assertion are in tension
with how `--smoke` is implemented.

| Script | `--smoke` write target | Anchor |
|---|---|---|
| **E1** | **ALWAYS a `TemporaryDirectory`** — no honor-`--out` branch | `e1_refractive_comparison.py:893` |
| **E2** | **ALWAYS a `TemporaryDirectory`**, or prints `SKIPPED` when the dataset is uncached | `e2_real_rig.py:428-431, 443` |
| E3 | honors an explicitly-passed `--out`, else temp | `e3_derived_quantities.py:1030-1045` |
| E4 | honors, else temp | `e4_benchmark_grid.py:2105-2113` |
| E5 | honors, else temp | `e5_index_sensitivity.py:892-905` |
| E6 | honors, else temp | `e6_generalization_sweep.py:1658-1667` |
| E7 | honors, else temp | `e7_interface_ablation.py:918-934` |
| `e7_focal_standoff_analysis` | **ignores `--smoke` entirely** (0 references) — always does the full re-analysis | `e7_focal_standoff_analysis.py` |
| `reconstruction_bootstrap` | writes to `--out`; smoke only reduces resamples 10 000 → 200 | `:314`, `:59` |
| `fd_jacobian_accuracy` | writes to `--out` | `:652-665` |

⚠ **The "honors an explicitly-passed `--out`" test is `args.out == parser.get_default("out")`**, and
the default is `Path("experiments/results")` (`experiments/_io.py:64`). So passing
`--out experiments/results` — which is exactly what the driver does — is **indistinguishable from
the default**, and E3/E4/E5/E6/E7 fall into the temp-dir branch too.

**Planning consequences:**
1. The `--smoke` acceptance pass must use a **distinct** out dir (e.g. `experiments/results_smoke/`)
   or nothing lands on disk to check.
2. Even then, E1 and E2 produce **nothing** — a `smoke`-profile existence expectation for any E1 or
   E2 artifact is unsatisfiable. The manifest needs a per-artifact `profiles: [full]` marker, not
   just per-profile row counts.
3. The one exception worth knowing: E1/E5/E6/E7's `--seeds` **band** path is checked *before* the
   smoke branch (e.g. `e1_refractive_comparison.py:1367` vs `:1370`), so `--seeds ... --smoke`
   **does** write band CSVs to `--out` at collapsed scale. That is the usable smoke signal for the
   band stages. `[VERIFIED: sed over all ten scripts]`

### SP-8 — three orphan scripts read hardcoded, cwd-relative, `--out`-ignoring input paths

| Script | Hardcoded input | Anchor |
|---|---|---|
| `e7_focal_standoff_analysis` | `Path("experiments/results")/interface_ablation_band.csv` | `:389` (docstring at `:378-380` says this is deliberate: "never the `--out` directory") |
| `reconstruction_bootstrap` | `experiments/results/reconstruction_errors.csv` (resolution step 2), and `REAL_RIG_METRICS_PATH = Path("experiments/results/real_rig_metrics.json")` | `:171-172`, `:56` |

Both are **cwd-relative**, so they only work when invoked from the repo root — which the driver
guarantees (`cd "${REPO_ROOT}"`, `rerun_19_3.sh:87`). But under DRIVER-04's move they resolve to
nothing until E7's band / E2 have re-populated `experiments/results/` in the same run. Ordering
constraints O1 and O2 cover it, but the manifest's `smoke` profile must **not** expect
`e7_focal_standoff.csv` or `reconstruction_bootstrap.json` unless the smoke pass wrote the inputs
first (and per SP-7 it will not, for E2). `[VERIFIED: sed]`

---

## Runtime State Inventory

Phase 26 moves and renames files. This is the rename/refactor inventory.

| Category | Items found | Action required |
|---|---|---|
| **Stored data** | None. No database, no Mem0/Chroma/Redis state carries a driver name. The `experiments/results/` trees are plain files. | None — verified by inspection of `experiments/` (files only) and absence of any datastore in `src/`. |
| **Live service config** | None. No n8n / Datadog / cloud service is involved. | None. |
| **OS-registered state** | None. The driver is launched ad hoc via `nohup ... & disown` (`rerun_19_3.sh:79`); no Task Scheduler entry, no pm2, no systemd unit. | None — verified: no scheduler references anywhere in `experiments/` or `.planning/`. |
| **Secrets / env vars** | `PRELAUNCH_GATE_PYTHON` (override for `GATE_PYTHON`, `rerun_19_5.sh:219`), `RERUN_19_3_DRY_RUN` / `RERUN_19_3_DRY_RUN_CMD` (`rerun_19_3.sh:138,142`), `RERUN_19_5_DRY_RUN` (`:181,273`). **Renaming the dry-run vars per D-25 is a code edit in the driver AND in any doc/test that sets them.** No test currently sets them (`grep -rln` over `tests/` returns nothing driver-related). | Rename the two `RERUN_19_*_DRY_RUN*` vars to the new stem; keep `PRELAUNCH_GATE_PYTHON` unchanged (it is shared with `prelaunch_gate.sh`). |
| **Build artifacts / installed packages** | `aquacal` is installed as an editable/source distribution reporting **2.0.1** (`importlib.metadata.version("aquacal")` — verified). This is F-002's mechanism and D-45 explicitly leaves it alone. No egg-info rename is triggered by Phase 26 (no package rename). | None for the rename. Record the caveat in the manifest per D-45. |
| **Git-tracked path references** | `experiments/rerun_19_3.sh` is referenced by name in `CLAUDE.md`, `.planning/*`, and phase SUMMARYs. Only the **live** references matter: `.gitignore:256-267` names `rerun_19_5_state.dryrun.tsv` and `!experiments/rerun_19_5.log`. | The rename needs a matching `.gitignore` update for the new stem, or the new state/log files land in the wrong ignore class. |

---

## Provenance Ground Truth (DRIVER-02)

### `capture_environment` — the one existing helper

`src/aquacal/io/benchmark.py:67`, exported via `src/aquacal/io/__init__.py:22,31`. Called from
`pipeline.py:1784`, `experiments/_io.py:759`, and E1/E3/E5/E6/E7/`fd_jacobian_accuracy`/
`reconstruction_bootstrap`. **Never raises** by design (`:70-73`).

Fields it emits (`:109-122`):
`aquacal_version`, `aquacal_version_declared`, `python_version`, `numpy_version`, `scipy_version`,
`opencv_version`, `os`, `cpu_model`, `cpu_count_logical`, `ram_total_bytes`, `git_sha`,
`git_sha_source`.

### The two recording defects, located precisely

| Defect | Anchor | Verified evidence | D-45's disposition |
|---|---|---|---|
| **F-002 — `aquacal_version` names the last *built* version** | `benchmark.py:125` — `env["aquacal_version"] = importlib.metadata.version("aquacal")` | `importlib.metadata.version("aquacal")` → **`2.0.1`** while `git describe --tags --long --dirty` → **`v2.0.1-156-ge1a202a`**. Every commit after the tag reports `2.0.1`. The committed `experiments/results/benchmark.json` records `aquacal_version: "1.8.0"` at `git_sha 6c7f930…` | Do **not** change the schema. Record `git describe` in the **run manifest only**, plus a documented caveat naming F-002. |
| **OpenCV build suffix is dropped** | `benchmark.py:115` — `"opencv_version": cv2.__version__` | `cv2.__version__` → `4.13.0`; `importlib.metadata.version("opencv-python")` → **`4.13.0.90`**. The `.90` vs `.92` ambiguity D-20 names is real and the mechanism to resolve it is confirmed working. | The manifest is the sole owner. Use `importlib.metadata.version("opencv-python")` with a fallback chain over `opencv-contrib-python` / `opencv-python-headless` (both **absent** here — verified). |

`[VERIFIED: ~/anaconda3/envs/AquaCal/python.exe probe, 2026-08-18]`

### Verified environment values on this box (the manifest's first row)

| Field | Value | Source |
|---|---|---|
| `git_sha` | `e1a202a76fdb43efc74539ebafd640f5447e4fde` | `git rev-parse HEAD` |
| `git describe --tags --long --dirty` | `v2.0.1-156-ge1a202a` (clean) | verified |
| `python_version` | `3.12.12` | verified |
| `numpy_version` | `2.4.2` | verified |
| `scipy_version` | `1.17.0` | verified |
| `cv2.__version__` | `4.13.0` | verified |
| `opencv-python` dist | **`4.13.0.90`** | verified |
| `aquacal` dist | `2.0.1` | verified |
| box | Intel Alder Lake-H, 20 logical cores, 15.7 GiB | `benchmark.json` env + concurrency probe `summary.json` |

### Gate 3's extension point (D-21)

`_check_git_sha_consistency` (`check_rerun_gates.py:1732-1766`) collects `environment.git_sha` from
`_collect_all_json_paths` (`:1711-1730`) — which globs `e1_benchmark_*.json`, `e3_provenance.json`,
`e5_provenance.json`, `e6_provenance.json`, `e7_benchmark_*.json`, `e4_cells/*/benchmark.json`,
`e6_configs/*.json`. **The manifest is not in that glob list.** D-21's extension is: add the
manifest to the collection (or a sibling check), assert every required field is non-null, assert
`manifest.git_sha == the single sha`, assert not dirty. All hard FAIL, per D-21 and the
`GateResult("ALL", ...)` convention already used at `:1750`.

⚠ Note the current PASS branch: `len(shas) <= 1` passes even when `shas` is **empty**, with detail
`"no git_sha values found across any artifact to compare"` (`:1749-1754`). That is a green verdict
over an empty tree — the exact F-001 class. The completeness gate must cover it; do not weaken
Gate 3 to do so (CONTEXT § Specific Ideas).

---

## The `--check` Surface (DRIVER-03)

| Script | `_run_check` | `compare_experiment_csv` calls | Baseline path resolved from | Schema moved in 23/24/25? |
|---|---|---|---|---|
| E1 | `:1` (yes) | 1 | `args.out` | **yes** — `SPATIAL_COLUMNS` 6→12 cols |
| E2 | yes (`:477`) | 3 | `args.out` (`:490`) | no — **but see SP-5, 2 of 3 baselines are gitignored** |
| E3 | yes (`:899` region) | 3 | `args.out` | **no** — the genuine survivor |
| E4 | yes | 1 | `args.out`, + `resolve_e2_benchmark_path` (`:261`) | structurally always-red (`exit_code`, `status_reason`) — `CHECK_EXCLUDED_COLUMNS` at `:215` |
| E5 | yes | 1 | `args.out` | **yes** — `E5_COLUMNS` 17→23 |
| E6 | yes | 1 | `args.out` | **yes** — `E6_COLUMNS` 31→33 |
| E7 ablation | yes | 1 | `args.out` | **yes** — `ABLATION_COLUMNS` 17→23 |
| `e7_focal_standoff_analysis` | **none** | 0 | — | verdict strings changed (23-03) |
| `reconstruction_bootstrap` | inline (`:316-332`) | 0 — compares 3 JSON fields by hand | `out_dir/reconstruction_bootstrap.json` | no |
| `fd_jacobian_accuracy` | yes | 1 | `args.out` | no |

`[VERIFIED: grep -c 'def _run_check' / 'compare_experiment_csv(' per file; column counts from a
Python import of each constant]`

### The measured code-vs-artifact schema gap

This table is the concrete input for the expectation manifest's `full` profile, and it shows
exactly which `--check` calls are pre-declared to fail.

| Artifact (committed) | rows | cols on disk | pinning constant | constant's length | moves? |
|---|---|---|---|---|---|
| `exp1_parameter_errors.csv` | 24 | 12 | `EXP1_COLUMNS` (`e1:347`) | 12 | frozen ✓ |
| `exp2_depth_generalization.csv` | 16 | 7 | `EXP2_COLUMNS` (`e1:361`) | 7 | frozen ✓ |
| `exp3_xy_vs_z_anisotropy.csv` | 16 | 6 | `EXP3_COLUMNS` (`e1:370`) | 6 | frozen ✓ |
| `exp2_spatial_errors.csv` (gitignored) | 121 478 | 6 | `SPATIAL_COLUMNS` (`e1:378`) | **12** | **→ 12** |
| `exp1_band.csv` | **160** | 12 | `BAND_MERGED_COLUMNS` (`e1:419`) + seed | 11 (+seed) | **→ D-41 shape** |
| `exp1_parameter_band.csv` | **240** | 13 | `PARAMETER_BAND_KEY_COLUMNS` + `EXP1_COLUMNS` | — | **→ D-41 shape** |
| `index_sensitivity.csv` | 11 | 17 | `E5_COLUMNS` (`e5:140`) | **23** | **→ 23** |
| `index_sensitivity_seed_band.csv` | 66 | 17 | `E5_COLUMNS` | **23** | **→ 23** |
| `interface_ablation.csv` | 48 | 17 | `ABLATION_COLUMNS` (`e7:195`) | **23** | **→ 23** |
| `interface_ablation_band.csv` | 480 | 18 | `ABLATION_COLUMNS` + seed | **23** (+seed) | **→ 24** |
| `generalization_sweep.csv` | 14 | 31 | `E6_COLUMNS` (`e6:234`) | **33** | **→ 33** |
| `generalization_sweep_band.csv` | **102** | 31 | `E6_COLUMNS` | **33** | **→ 33 cols, 84 rows if D-40** |
| `generalization_sweep_per_camera.csv` | **absent** | — | `E6_PER_CAMERA_COLUMNS` (`e6:334`) | 10 | **new (23-03)** |
| `generalization_sweep_per_camera_band.csv` | **absent** | — | `E6_PER_CAMERA_COLUMNS` | 10 | **new (23-03)** |
| `benchmark_grid.csv` | 10 (9 synth + 1 real) | 36 | `GRID_COLUMNS` (`e4:497`) | 36 | frozen ✓ (25 additions confirm) |
| `benchmark_grid_repeat.csv` | 6 | 40 | — | — | — |
| `e7_focal_standoff.csv` | 4 | 9 | — | — | verdict strings move |
| `fd_jacobian_accuracy.csv` | 8 | 8 | `FD_ACCURACY_COLUMNS` (`fd:68`) | 8 | frozen ✓ |
| `code_constants.csv` | 9 | 7 | `CODE_CONSTANTS_COLUMNS` (`e3:84`) | 7 | frozen ✓ |
| `newton_iterations.csv` | 26 | 10 | `NEWTON_COLUMNS` (`e3:95`) | 10 | tier-2, geometry-dependent, **expected to move** |
| `cpr_grouping.csv` | 12 | 10 | `CPR_COLUMNS` (`e3:129`) | 10 | frozen ✓ |
| `structural_scaling.csv` | 84 | 13 | `SCALING_COLUMNS` (`e3:174`) | 13 | frozen ✓ |
| `camera_parameters.csv` | 13 | 11 | `CAMERA_PARAMS_COLUMNS` (`e2:56`) | 11 | frozen ✓ |
| `reconstruction_errors.csv` | **gitignored** | — | `RECONSTRUCTION_COLUMNS` (`e2:69`) | 5 | DATA-01b |
| `reprojection_residuals.csv` | **gitignored** | — | `RESIDUALS_COLUMNS` (`e2:70`) | 4 | DATA-01b |
| `e4_cells/` | 9 dirs | — | — | — | |
| `e6_configs/` | 12 files | — | — | — | |
| `e6_band/` | 6 seed dirs | — | — | — | |

`[VERIFIED: wc/head over every CSV in experiments/results/; constant lengths by import under
PYTHONPATH=src]`

### D-07's named constant list — all exist, but the list is incomplete

D-43 cuts the coupling test, so this is now advisory input for the manifest. All ten names in D-07
resolve:

| D-07 name | Location | len |
|---|---|---|
| `E5_COLUMNS` | `experiments/e5_index_sensitivity.py:140` | 23 |
| `ABLATION_COLUMNS` | `experiments/e7_interface_ablation.py:195` | 23 |
| `SPATIAL_COLUMNS` | `experiments/e1_refractive_comparison.py:378` | 12 |
| `DEGENERATE_OBSERVATION_COLUMNS` | `src/aquacal/validation/diagnostics.py:30` | 12 |
| `OBSERVATION_DEPTH_COLUMNS` | `src/aquacal/validation/diagnostics.py:47` | 8 |
| `GRID_COLUMNS` | `experiments/e4_benchmark_grid.py:497` | 36 |
| `GRID_SUMMARY_COLUMNS` | `experiments/e4_benchmark_grid.py:594` | 7 |
| `EXP1_COLUMNS` / `EXP2_COLUMNS` / `EXP3_COLUMNS` | `e1:347 / 361 / 370` | 12 / 7 / 6 |

**But the manifest needs eleven more that D-07 omits**, or its artifact coverage is short:
`E6_COLUMNS` (`e6:234`, 33), `E6_PER_CAMERA_COLUMNS` (`e6:334`, 10), `DEGENERACY_COLUMNS`
(`experiments/_degeneracy.py:94`, 6), `FD_ACCURACY_COLUMNS` (`fd:68`, 8), `CODE_CONSTANTS_COLUMNS` /
`NEWTON_COLUMNS` / `CPR_COLUMNS` / `SCALING_COLUMNS` (`e3:84/95/129/174`), `CAMERA_PARAMS_COLUMNS` /
`RECONSTRUCTION_COLUMNS` / `RESIDUALS_COLUMNS` (`e2:56/69/70`), plus `BAND_MERGED_COLUMNS`
(`e1:419`). `[VERIFIED: grep + import]`

### The `exclude_columns` contract Phase 26 documents (D-13)

- Mechanism: `experiments/_io.py:332-338`, parameter documented `:365-382` — the docstring **already
  names Phase 26 / DRIVER-03 and warns the two must not diverge**.
- E4-local list: `CHECK_EXCLUDED_COLUMNS: tuple[str, ...] = ("exit_code", "status_reason")` at
  `experiments/e4_benchmark_grid.py:215`.
- Key property to document: `exclude_columns` affects the **cell-level** comparison only; the
  full-header comparison is never affected, so a genuine schema change still fails loudly
  (`_io.py:369-372`).

---

## The Output Trees (DRIVER-04)

### D-29's six tracked trees — verified counts and sizes

| Tree | tracked files | files on disk | size | CONTEXT said |
|---|---|---|---|---|
| `experiments/results/` | **151** | 153 | **16 M** | 151 files, 16 M ✓ |
| `experiments/results_e2_band/` | **7** | 133 | **26 M** | 7, 26 M ✓ |
| `experiments/results_linux32gb/` | **25** | 25 | 157 K | 25 ✓ |
| `experiments/results_e6_repeat2/` | **14** | 15 | 69 K | 14 ✓ |
| `experiments/results_e6_seed43/` | **14** | 14 | 61 K | 14 ✓ |
| `experiments/results_e4_repeat/` | **4** | 4 | 16 K | 4 ✓ |
| `experiments/archive/` (must NOT collide) | 31 | 31 | 268 K | 31 ✓ |

**Every D-29 number is correct.** `[VERIFIED: git ls-files | wc -l; find | wc -l; du -sh]`

Because these are tracked, the move is a **`git mv`** and lands as a reviewable commit — D-28's
requirement is mechanically satisfiable. The untracked residue inside `results_e2_band/` (126 files,
the bulk of the 26 M) and `results/` (2 files) moves as a plain `mv` and needs `.gitignore` pattern
updates: `.gitignore:282-287` and `:312-325` pin paths by literal prefix
(`experiments/results_e2_band/*`, `experiments/results_linux32gb/e2_*/…`), so the new archive prefix
needs matching rules or the untracked bulk becomes newly visible in `git status`.

### D-30's loose files — tracked status matters

| File | tracked? | size |
|---|---|---|
| `rerun_19_3_state.tsv` / `_19_4` / `_19_5` | **TRACKED** | 1 K each |
| `rerun_19_3_frozen_sha.txt` / `_19_4` / `_19_5` | **TRACKED** | 1 K each |
| `rerun_19_4.log`, `rerun_19_5.log` | **TRACKED** (via `!experiments/rerun_19_5.log`, `.gitignore:267`) | 144 K, 160 K |
| `e6_legal_seed_probe_state.tsv` | **TRACKED** | 1 K |
| `rerun_19_3.log` | untracked | 120 K |
| `e1_band_rerun.log`, `e7_band_rerun.log` | untracked | 16 K, 4 K |
| `final_/postcommit_/postqueue_suite_19_5.log`, `suite_260807_dcv.log` | untracked | 16–20 K each |
| `prelaunch_gate_19_5.log`, `prelaunch_gate_2026-08-02.log` | untracked | 24 K, 12 K |
| `e6_legal_seed_probe.log`, `e6_legal_seeds.log`, `seed_sweep_19_3.log` | untracked | 1–4 K |

⚠ `rerun_19_3.sh` / `rerun_19_4.sh` / `rerun_19_5.sh` and `seed_sweep_19_3.sh`,
`e6_legal_seed_probe.sh`, `prelaunch_gate.sh` are all **tracked scripts**, not outputs. D-25 renames
only `rerun_19_3.sh`. **Decide explicitly what happens to `rerun_19_4.sh` and `rerun_19_5.sh`** —
CONTEXT does not say. Leaving them in place after the rename is a live footgun (three drivers, one
of which is the real one); archiving them alongside the state files is the consistent choice, but
their band stage functions must be **lifted into the new driver first**.
`[VERIFIED: git ls-files --error-unmatch per file; du -h]`

### D-31's untracked probe trees

`experiments/verify_23/`, `verify_23_fdnoise/`, `verify_23_optblocks/` — gitignored at
`.gitignore:331-333` (`git check-ignore -v` confirms). Local hygiene only, plain `mv`, not a
reviewable commit — exactly as D-31 says. `[VERIFIED: git check-ignore -v]`

---

## `check_rerun_gates.py` — a factoring strategy, not "append to the end"

1 863 lines, flat module, no classes beyond `GateResult`. Full structural map:

| Region | Lines | Contents |
|---|---|---|
| Imports + module constants | 40–58 | `_GUARD_COLUMN`, `_STATUS_COLUMN`, `_DEGENERATE_STATUS` |
| `GateResult` dataclass | 62–77 | `experiment`, `gate`, `verdict`, `detail` — frozen |
| `legality_probe` | 80–180 | imported by `rerun_19_5.sh:300` — **a cross-file contract; do not move or rename** |
| Loaders | 181–203 | `_load_json`, `_load_csv` |
| Guard/breakdown helpers | 204–323 | `_guard_count_from_record`, `_guard_breakdown_from_record`, `_sum_by_axis`, `_format_guard_breakdown` |
| Provenance/optimality helpers | 324–389 | `_provenance_gaps`, `_optimality_present` |
| Generic artifact checks | 390–608 | `_check_json_artifact`, `_check_guard_column`, `_check_status_column` |
| Per-experiment gates | 609–791 | `check_e1`, `check_e3`, `check_e4`, `check_e5`, `check_e6`, `check_e7` |
| Generic band checker | 792–930 | `check_band_csv` |
| **Phase 19.5 band gates** | 931–1710 | `check_e6_seed_band` (952), `check_e5_seed_band` (1194), `check_e2_band` (1380), `check_e4_repeat` (1560) + their hardcoded constants |
| Gate 3 | 1711–1766 | `_collect_all_json_paths`, `_check_git_sha_consistency` |
| Orchestration + CLI | 1768–1863 | `run_all_gates`, `build_arg_parser`, `main` |

**Recommended factoring (minimal-risk, deadline-aware):**

- **Do not** split the file. The 19.5 band gates (780 lines) are the natural extraction, but they
  carry hardcoded constants that D-40 will change, and moving them adds import churn to a file the
  driver calls at every stage boundary. Cost/benefit is bad three days before a freeze.
- **Do** add a new module `experiments/_expectations.py` (or similar) holding the manifest loader
  and the completeness gate, and import it into `check_rerun_gates.py`. Keeps the new ~100 lines
  (CONTEXT's own estimate) out of the 1 863, is importable by the D-33 form-3 unit tests, and adds
  exactly one import.
- **Do** extend `build_arg_parser` (`:1832-1841`). It currently takes **one positional `out_dir`
  and nothing else** — no `--stage`, no `--profile`. D-04's selector is a new `--stage NAME` and
  `--profile {smoke,full}` here, both optional so every existing call site (including
  `rerun_19_5.sh:257`) keeps working unchanged.
- **Do** append the completeness gate to `run_all_gates` (`:1768`) after the 13 existing calls and
  before `_check_git_sha_consistency`, guarded on the selector being supplied.

**Constants that hardcode shape and must be reconciled with the manifest** (otherwise there are two
sources of truth, which is the exact failure D-05 exists to prevent):
`_E6_EXPECTED_SEED_COUNT = 6` (`:948`), `_E6_EXPECTED_CAMERA_VALUES = (8,12,16)` (`:949`),
`_E5_EXPECTED_SEED_COUNT = 6` (`:1191`), `_E2_EXPECTED_RECORD_COUNT = 3` (`:1342`),
`_E2_METRICS_RTOL = 1e-6` (`:1340`), `_E4_REPEAT_CELLS = ((8,100),(12,100),(16,100))` (`:1555`).

⚠ `check_e2_band` is invoked as `check_e2_band(out_dir.parent / "results_e2_band", committed_metrics_path=out_dir / "real_rig_metrics.json")` (`:1817-1820`) — **a hardcoded sibling path**.
DRIVER-04's move relocates `results_e2_band/`; this call site must follow, and it is a second place
where `--baseline-dir` semantics apply. `[VERIFIED: grep -n, sed]`

---

## `experiments/README.md` §2 — what a rewrite is actually rewriting

475 lines total. §2 spans **`:50` to `:297`** (247 lines) and is not one table — it is a table plus
six subsections:

| Anchor | Content |
|---|---|
| `:50-64` | §2 preamble: "One row per artifact committed under `experiments/results/`" + the provenance-coverage claim |
| `:66-84` | The accuracy-tree vs timing-tree (`results_linux32gb/`) distinction |
| `:86-113` | The 30-row artifact table (`\| Paper artifact \| Experiment \| Command \| Output file(s) \| Figure generator \| Runtime \|`) |
| `:115-135` | The "three `generalization_sweep.csv` rows did not converge" callout |
| `:137-168` | E4 direct-call rationale + the `--check`-always-red explanation |
| `:170-204` | `### DATA-01b` |
| `:205-239` | `### Which committed artifacts are pre- and which are post-D-27` |
| `:240-256` | `### cpr_grouping.csv is the sole origin of tab:cpr` — **⚠ contradicted by D-39** |
| `:257-265` | `### Every cell in E4 and E6 runs tilt-enabled` |
| `:266-280` | `### The seed carve-out` |
| `:281-297` | `### The four scripts with no row in the table above` |

**Two stale statements the rewrite must fix (both are current defects, not style):**
1. `:81-83` — *"E4's aggregator reads the real-rig record from a hardcoded `E2_BENCHMARK_PATH`
   (`e4_benchmark_grid.py:226`)"*. FIX-05 (Phase 23) fixed this; the resolver is
   `resolve_e2_benchmark_path` at `:261` and the constant moved to `:256`. The line number and the
   claim are both wrong now.
2. `:240` — *"`cpr_grouping.csv` is the sole origin of `tab:cpr`"* directly conflicts with **D-39**
   (the generated `.tex` is never `\input`; `tab:cpr` is hand-transcribed). The README and the MF-NN
   must agree.

Also note §7 (`:394-468`) is a shell block of reproduction commands **with the same coverage gap** —
no `--seeds` row anywhere. D-36 names §2; §7 has the identical defect and should be swept in the
same pass. `[VERIFIED: grep -n '^#', sed]`

---

## Testing Conventions for `experiments/`

- **Location:** `tests/unit/`, one file per experiment concern. No separate experiments test dir.
  21 relevant files. `[VERIFIED: ls tests/unit/]`
- **Sizes:** `test_experiments_provenance.py` 803 lines, `test_rerun_gates.py` 1 296,
  `test_experiments_e3_constants.py` 554.
- **There is no test of any driver shell script.** `grep -rln "rerun_19\|DRY_RUN\|STAGES" tests/`
  returns only two unrelated files. D-33 form 2 (extend the dry-run harness) has **no existing test
  scaffold** — the planner must budget for creating one. The mechanism exists
  (`RERUN_19_3_DRY_RUN` / `_CMD`), but it has only ever been driven by hand.
- **The "constants agree with a manifest" pattern D-07/D-08 asked for already exists**, in
  `tests/unit/test_experiments_provenance.py`. Its shape, worth copying:
  - a module-level dict of expectations (`CSV_TO_RECORD`, `:106`),
  - a `PENDING_CSVS` escape hatch that must shrink to empty (`:255`, with
    `test_pending_csvs_are_still_pending` at `:658` enforcing that),
  - collection-time discovery that degrades to `[]` when the tree is absent (`:277`, `:311`),
  - a `_is_tracked()` git filter so working-tree-only files do not trip the tripwire (`:282-308`),
  - **bidirectional** assertions: `test_all_committed_csvs_have_a_named_record` (`:591`) and
    `test_csv_to_record_has_no_stale_entries` (`:640`).

  This is the exact pattern D-33 form 3 needs ("every declared stage has an expectation entry, every
  expectation has an owning stage") — **reuse the shape, and note that `CSV_TO_RECORD` is a second
  artifact inventory that will drift from the new expectation manifest unless one reads the other.**

---

## Common Pitfalls

### Pitfall 1: appending a `--seeds` stage into a directory the single-seed stage also writes
**What goes wrong:** the band overwrites the single-seed artifact, or vice versa.
**Why it doesn't here:** band mode writes disjoint files by design — E1's `_run_band` docstring
(`e1_refractive_comparison.py:1072-1077`) states it *"Deliberately does NOT write
`exp1_parameter_errors.csv`, `exp2_depth_generalization.csv`, `exp2_spatial_errors.csv`, or
`exp3_xy_vs_z_anisotropy.csv`"*. Sidecars are keyed apart (`e{N}_seed_band_provenance.json`).
**How to avoid:** verify filename disjointness **against the manifest** (D-52 constraint 3), never
by inspection.

### Pitfall 2: `e6_repeat1` clobbering `e6_band` under concurrency
**What goes wrong:** `run_stage_e6_repeat1` does `rm -rf "${OUT_DIR}/e6_configs"` and
`rm -f generalization_sweep.csv e6_provenance.json` (`rerun_19_3.sh:195-196`) under the **shared**
`OUT_DIR`, which `e6_band` also writes.
**How to avoid:** D-52 constraint 1 — never overlap them. Encode as `depends_on`, not array order.

### Pitfall 3: a dry run leaving a state file that silently no-ops the real launch
**What goes wrong:** the dry run "completes" every stage in ~1 s; automatic resume then skips all of
them and the queue exits 0 with no artifacts.
**Anchor:** documented at `rerun_19_5.sh:174-180` ("Found 2026-08-06 by dry-running this script and
inspecting what it left behind"). **19.3 does not have this fix.**
**How to avoid:** lift 19.5's separate `STATE_FILE` path. This composes with D-48's sha-derived path.

### Pitfall 4: bare `python` for the gate
**What goes wrong:** `check_rerun_gates.py` imports pandas AND `aquacal.datasets.synthetic` /
`experiments.e4_benchmark_grid`; Git Bash's `python` is Anaconda base, so the gate ImportErrors.
**Anchor:** `rerun_19_3.sh:121` (bare `python`) vs `rerun_19_5.sh:219-223, 257` (pinned
`GATE_PYTHON` with fallback). Project memory carries this as *"pytest needs the AquaCal conda env"*.
**How to avoid:** lift 19.5's pin. `PRELAUNCH_GATE_PYTHON` is the shared override variable.

### Pitfall 5: an empty tree passing Gate 3
**What goes wrong:** `_check_git_sha_consistency` returns PASS when it finds zero shas (`:1749-1754`).
**How to avoid:** the completeness gate's end-of-run roll-up (D-02) must be the thing that catches
it. Do not "fix" Gate 3 — CONTEXT's § Specific Ideas explicitly forbids weakening it, and the
correct division of labour is Gate 3 = consistency, completeness gate = presence.

### Pitfall 6: reading `optimality` as evidence
**Warning sign:** any expectation-sheet row quoting optimality to more than one significant figure.
**Anchor:** `experiments/README.md:133-135` — *"it varies ~2x between runs of identical code"*.

### Pitfall 7: attributing a runtime change to a code change
**Anchor:** `rerun_19_5.sh:26-29` — *"Do NOT read a stage's actual runtime as evidence about any
code change — that attribution is a standing prohibition in this project."* Applies directly to
D-38's budget: the 1.6–2.0× swing between 19.3 and 19.4 tracked the **machine**.

---

## Runtime and the Wall-Clock Budget (D-38 / D-51)

**The only historical timing data that exists** is the ISO start/complete stamps in
`experiments/rerun_19_{3,4,5}_state.tsv` (four tracked files, 1 K each). No band CSV and no
`e{N}_seed_band_provenance.json` records its own runtime. The concurrency probe
(`.planning/probes/2026-08-18-solver-concurrency/summary.json`, verified present) is the only fresh
measurement.

Verified probe facts the stage model depends on:

| Fact | Value | Source |
|---|---|---|
| E1 single-seed wall clock, 2026-08-18 | **318.4 s (5.3 min)**, exit 0 | `summary.json` |
| cores busy, median / mean / p95 / peak | **0.99 / 1.20 / 1.99 / 2.56** of 20 | `summary.json` |
| E1 peak RSS | **0.61 GiB** | `summary.json` |
| Recommended workers on the Linux target | 16 (cores-bound), 43 (memory-bound at 85%) — **"an upper bound on headroom, not a setting"** | `summary.json` |
| Peak RSS vs frame count | 30 frames <1 GiB (E5); 100 frames 2.7–3.5 GiB (E6 band, all 102 rows at `n_frames=100`); 200 frames 9.3–11.3 GiB (E2, E4) | `FINDINGS.md` Finding 2 |

⚠ The probe's own caveat is load-bearing: *"E1 is the cheapest and smallest solve in the suite …
peak RSS especially does not transfer."* D-52's "4–5 wide" is the author's decision and is well
inside the probe's bound; the planner should not widen it on the probe's `recommended_workers: 16`.

**D-38's deliverable is a per-stage estimate summing to a stated total.** The planner has:
- 19.3/19.5 state files for `e3`, `e5`, `e6_repeat1/2`, `e4`, `e6_band`, `e4_repeat`, `e2_band`,
  `e5_band` `[VERIFIED: files exist and carry ISO stamps]`
- the probe for `e1` `[VERIFIED]`
- **nothing** for `e7_band` — CONTEXT § E states a probe was offered and **DECLINED**; the estimate
  carries a range (1–2 h) and a note that it is unmeasured `[CITED: 26-CONTEXT.md § E]`
- **nothing** for the three orphan scripts (all are seconds-to-minutes: `fd_jacobian_accuracy` is a
  small FD sweep, `reconstruction_bootstrap` is 10 000 resamples of an in-memory CSV,
  `e7_focal_standoff_analysis` is a pandas re-analysis of a 480-row CSV) `[ASSUMED — from code shape,
  not measured]`
- **nothing** for E2's timing and memory runs individually; the 48–87 min per-run figure from
  CLAUDE.md is the only anchor `[CITED: CLAUDE.md]`

---

## Environment Availability

| Dependency | Required by | Available | Version | Fallback |
|---|---|---|---|---|
| `$HOME/anaconda3/envs/AquaCal/python.exe` | every gate and experiment invocation | ✓ | 3.12.12 | bare `python` (degrades gate to a logged finding; `rerun_19_5.sh:220-223`) |
| pandas / numpy / scipy | gates, all experiments | ✓ | numpy 2.4.2, scipy 1.17.0 | — |
| `cv2` (opencv-python) | pipeline, E2 | ✓ | 4.13.0 (dist `4.13.0.90`) | — |
| `git` (`rev-parse`, `describe`, `ls-files`, `mv`) | manifest, Gate 3, archive-aside | ✓ | `git describe` verified | — |
| GNU `awk`, `date -u`, `du`, `grep -c`, `tee` | driver | ✓ (Git Bash MINGW64) | — | ⚠ D-35: write conservatively for Linux |
| E2 release config `C:/Users/tucke/Desktop/Aqua/AquaCal/release_calibration/config.yaml` | E2 production, E2 band | ✓ **on this box only** | — | `--skip-e2` (D-14). **Does not travel to Linux — see SP-4** |
| E2 frameset (4.35 GB, Zenodo 21889922) | E2 | not verified in this pass (no download attempted) | — | `--skip-e2` |
| `psutil` | `capture_environment`'s `cpu_count_logical` / `ram_total_bytes` | ✓ (values populated in committed `benchmark.json`) | — | fields go `None`; `capture_environment` never raises |

**Missing dependencies with no fallback:** none identified for Phase 26's *build* work. The E2
frameset and the absolute release-config path are Phase 27/28 concerns and are covered by
`--skip-e2`.

---

## Validation Architecture

### Test Framework

| Property | Value |
|---|---|
| Framework | pytest (markers incl. `slow`; `pytest-xdist` present per `.planning/probes/2026-08-18-xdist-validation/`) |
| Config file | `pyproject.toml` (markers documented in `CLAUDE.md`) |
| Quick run command | `python -m pytest tests/unit/<file> -x -q` |
| Full suite command | `python -m pytest tests/` — **ORCHESTRATOR ONLY.** 56–88 min unfiltered; `-m "not slow"` is still ~26 min (`CLAUDE.md`) |
| Interpreter | must be the AquaCal conda env; worktree executors must `export PYTHONPATH="$(pwd)/src"` |

### Phase Requirements → Test Map

| Req | Behavior | Test type | Automated command | Exists? |
|---|---|---|---|---|
| DRIVER-01 | Every declared stage has an expectation entry and vice versa | unit | `pytest tests/unit/test_suite_stage_list.py -x` | ❌ Wave 0 |
| DRIVER-01 | Ordering constraints hold structurally (O1, O2, O4, e6_repeat1∦e6_band) | unit | same file | ❌ Wave 0 |
| DRIVER-01 | Driver sequences, resumes, and sets a sticky non-zero exit on a gate FAIL | unit (bash, driven via the dry-run seam) | `pytest tests/unit/test_run_experiment_suite_dryrun.py -x` | ❌ Wave 0 — **no driver test exists today** |
| DRIVER-01 | A dry run does not write the real state file | unit | same file | ❌ Wave 0 |
| DRIVER-01 | Pre-flight aborts and prints its override flag (D-50) | unit | same file | ❌ Wave 0 |
| DRIVER-02 | Manifest emitter produces every D-20 field, all non-null | unit | `pytest tests/unit/test_run_manifest.py -x` | ❌ Wave 0 |
| DRIVER-02 | OpenCV build suffix is captured (not bare `cv2.__version__`) | unit | same file | ❌ Wave 0 |
| DRIVER-02 | `git describe --tags --long --dirty` is captured and distinguishes commits sharing a tag | unit | same file | ❌ Wave 0 |
| DRIVER-02 | Gate 3 FAILs on a missing manifest, a null field, a sha mismatch, or a dirty tree | unit | `pytest tests/unit/test_rerun_gates.py -k manifest -x` | ⚠ extend existing (1 296 lines) |
| DRIVER-03 | Completeness gate at `smoke` asserts existence only; at `full` asserts row counts | unit | `pytest tests/unit/test_expectations.py -x` | ❌ Wave 0 |
| DRIVER-03 | No expectation asserts 640/960 or requires `noise_std` in `experiments/results/` (D-06) | unit | same file — **a literal-value tripwire; cheap and high-value** | ❌ Wave 0 |
| DRIVER-03 | `degenerate_observations.csv` absence is PASS, not FAIL (conditional artifact) | unit | same file | ❌ Wave 0 |
| DRIVER-03 | `--baseline-dir` reads baselines from the archive while writing to `--out` | unit | `pytest tests/unit/test_experiments_io.py -k baseline -x` | ⚠ extend |
| DRIVER-04 | The four tests of SP-1 pass after the move | unit | `pytest tests/unit/test_experiments_provenance.py tests/unit/test_experiments_e5.py tests/unit/test_experiments_io.py -x` | ⚠ **existing tests, currently green, will break** |

### Sampling Rate

- **Per task commit:** the targeted file(s) that task touches, e.g.
  `python -m pytest tests/unit/test_expectations.py -x -q`.
- **Per wave merge:** the union of the wave's touched test files, still targeted.
- **Phase gate:** `python -m pytest tests/` — **run by the orchestrator only**, after merge. Per
  `CLAUDE.md`, an executor that backgrounds this has stalled permanently.

### Wave 0 Gaps

- [ ] `tests/unit/test_suite_stage_list.py` — DRIVER-01 stage/expectation bijection + ordering
- [ ] `tests/unit/test_run_experiment_suite_dryrun.py` — DRIVER-01 driver mechanics (no scaffold exists)
- [ ] `tests/unit/test_run_manifest.py` — DRIVER-02 emitter
- [ ] `tests/unit/test_expectations.py` — DRIVER-03 manifest + completeness gate + the 640/960 tripwire
- [ ] Fixture strategy for a synthetic "output tree" the completeness gate can be pointed at
      (`tmp_path`-scoped; the existing band tests already use this shape — `tests/unit/test_e5_band_mode.py`)

### What cannot be tested without a full run

- That the `full`-profile row counts are **correct** rather than merely self-consistent. Only
  Phase 28 produces 352/528 (or whatever D-41 resolves to), 84 or 102 E6 band rows, 23-column
  `index_sensitivity.csv`. Phase 26 can only assert the manifest is internally coherent and that
  the gate reads it correctly.
- That E2's ~1e-8 control reproduces. Requires the 4.35 GB frameset and 48–87 min.
- That the concurrency model does not OOM. Peak RSS at 4–5 wide is untested; the probe measured a
  single E1 solve at 0.61 GiB and explicitly says RSS does not transfer.
- **Existence and row count are not correctness.** A gauge-corrected column populated with
  uncorrected values passes every completeness check. That is the hand-verification sheet's job;
  the manifest must mark which columns carry only a *shape* expectation.

---

## Security Domain

`security_enforcement` is not set in `.planning/config.json`, so it is treated as enabled. This
phase is a local, single-user research CLI with no network surface, no auth, no session, and no
untrusted input.

| ASVS category | Applies | Standard control |
|---|---|---|
| V2 Authentication | no | no auth surface |
| V3 Session Management | no | no sessions |
| V4 Access Control | no | single-user local CLI |
| V5 Input Validation | **partially** | `argparse` + `validate_args` (`experiments/_io.py:90`) + per-script `_validate_e{N}_args`. `resolve_out_dir` (`:220`) deliberately does **not** add a `..`-traversal guard — judged disproportionate in the Phase 21 RESEARCH security assessment; do not add one now. |
| V6 Cryptography | **yes, narrowly** | `hashlib.sha256` over the source config in `_run_emit_band_configs` (`e2_real_rig.py:951`) — integrity provenance, not a secret. Correct use; do not hand-roll anything further. |

| Pattern | STRIDE | Mitigation in this phase |
|---|---|---|
| Destructive `rm -rf` on a variable path in the driver | Denial of Service (own data) | `OUT_DIR_E6_REPEAT2` / `OUT_DIR_E4_REPEAT` / `OUT_DIR_E2_BAND` are literals, never interpolated from argv. **Keep it that way** — any new isolated-dir stage must use a literal, and `set -u` (`:83`) already turns an unset variable into an error rather than `rm -rf /`. |
| The archive-aside deleting instead of moving | Repudiation / data loss | D-32: nothing is deleted in Phase 26. Use `git mv`; the commit is the audit trail. |
| Absolute path to a tree outside the repo (`E2_RELEASE_CONFIG`) | Tampering (accidental) | `emit_seed_variant_configs` already refuses to write into or under the release config's own parent (`e2_real_rig.py:874-878`). Preserve that refusal. |

---

## Sources

### Primary (HIGH confidence — read directly in this session)

- `experiments/rerun_19_3.sh`, `rerun_19_4.sh`, `rerun_19_5.sh` — full reads
- `experiments/check_rerun_gates.py` — structure map, `GateResult`, Gate 3, `run_all_gates`, CLI, band-gate constants
- `experiments/_io.py` — `build_experiment_arg_parser`, `validate_args`, `parse_seed_list`, `run_seed_band`, `resolve_out_dir`, `compare_experiment_csv`
- `experiments/e1_refractive_comparison.py` (`_run_band`, all column constants, `NOISE_LEVELS`), `e2_real_rig.py` (CLI, `_run_check`, `_run_smoke`, `_run_emit_band_configs`), `e3_derived_quantities.py`, `e4_benchmark_grid.py` (`resolve_e2_benchmark_path`, `CHECK_EXCLUDED_COLUMNS`), `e5_index_sensitivity.py`, `e6_generalization_sweep.py`, `e7_interface_ablation.py`, `e7_focal_standoff_analysis.py`, `reconstruction_bootstrap.py`, `fd_jacobian_accuracy.py`
- `src/aquacal/io/benchmark.py:67-127` — `capture_environment`
- `src/aquacal/config/schema.py:373-374`, `src/aquacal/calibration/pipeline.py:390-392`
- `tests/unit/test_experiments_provenance.py`, `test_experiments_e5.py`, `test_experiments_io.py`, `test_experiments_e3.py`
- `experiments/README.md` §2, `.gitignore`
- `.planning/phases/26-.../26-CONTEXT.md` (full), `.planning/REQUIREMENTS.md`, `.planning/ROADMAP.md` §§ 23–30
- `.planning/todos/pending/2026-08-15-suspend-programmatic-check-for-reshaped-artifacts.md` §§ Solution, Phase 25 additions
- `.planning/phases/2{3,4}-*/…-SUMMARY.md` § "Notes for Phase 26"
- `.planning/probes/2026-08-18-solver-concurrency/{summary.json,FINDINGS.md}`

### Tool-verified measurements (this session)

- `git ls-files | wc -l`, `find | wc -l`, `du -sh` over all seven `experiments/results*` / `archive` trees
- `git check-ignore -v`, `git ls-files --error-unmatch` per loose file
- `wc -l` / `head -1` over all 25 committed CSVs in `experiments/results/`
- Python import of 23 column constants under `PYTHONPATH=src` (lengths)
- `importlib.metadata.version` for `aquacal`, `opencv-python`, `numpy`, `scipy`; `cv2.__version__`
- `git describe --tags --long --dirty`, `git rev-parse HEAD`

### Not consulted

No external documentation, Context7, or web search was used or needed. Every claim in this document
is about this repository and is anchored to a path and line.

---

## Assumptions Log

| # | Claim | Section | Risk if wrong |
|---|---|---|---|
| A1 | The three orphan scripts run in seconds-to-minutes | Runtime | Low — worst case the budget is a few minutes short |
| A2 | Hand-written E2 config variants (SP-4 option a) are lower-risk than extending `emit_seed_variant_configs` | SP-4 | Medium — if the author prefers generated configs, the plan shape changes |
| A3 | `tests/unit/test_experiments_e3.py:275`'s `BENCHMARK_JSON_PATH` is used in a way that breaks under the move | SP-1 | Low — flagged as "audit", not asserted |
| A4 | `results_e2_band/`'s 126 untracked files are the seed-run outputs the `.gitignore` block at `:282-287` describes | Output Trees | Low — the pattern block is explicit |
| A5 | Archiving `rerun_19_4.sh` / `rerun_19_5.sh` alongside the state files is the consistent choice | Output Trees | Medium — CONTEXT is silent; this is a real open decision, see below |
| A6 | The E2 frameset is present on this box (not verified — no download attempted) | Environment | Low — `--skip-e2` covers it, and it is Phase 27/28's concern |

---

## Open Questions (ALL RESOLVED 2026-08-18)

> **Resolution summary.** All five were put to the author during planning and answered. The
> rulings are recorded as A1–A5 in the plan-phase directive and implemented across the plans:
>
> | Q | Resolution | Where implemented |
> |---|---|---|
> | 1 — D-41 ragged E1 grid | **DESCOPED** to a uniform 4 levels x 4 seeds = **256/384** grid; no E1 source change. No gate may assert 640, 960, 352 or 528 (A1). | `26-03-PLAN.md` (`TestForbiddenLiterals`) |
> | 2 — D-40 / D-15 / D-16 | **Both planned as normal work**, not behind a checkpoint. D-40 buys ~1.9 h for zero ledger cost; D-15/D-16 defends E2's timing number from 2.7-5.5% contamination at 48-87 min/run to redo (A2). | `26-05-PLAN.md` (E6 `--axes`), `26-06-PLAN.md` (E2 config split) |
> | 3 — fate of `rerun_19_4.sh` / `rerun_19_5.sh` | **Union-and-lift from 19.5, then archive both** after the lift is verified (A3). | `26-07-PLAN.md` (lift), `26-09-PLAN.md` Task 3 (archive) |
> | 4 — E2 baselines for `--baseline-dir` | Missing baseline reports **N/A rather than raising**, guarded in the **caller**, never inside `compare_experiment_csv` (A4). | `26-04-PLAN.md` (`compare_experiment_csv_if_present`) |
> | 5 — how `smoke` asserts anything | Distinct out-dir `experiments/results_smoke` plus a per-artifact `profiles: [...]` field; E1/E2 are **not** changed to write on smoke (A5). | `26-03-PLAN.md`, `26-10-PLAN.md` |
>
> The original questions are preserved below as written, for the record.


1. **How is D-41's ragged E1 noise grid actually produced?** (SP-3)
   - What we know: 352/528 is unreachable with today's code; three implementation options, one of
     which is descoping.
   - What's unclear: whether the author will accept an E1 source change three days before the freeze.
   - **Recommendation:** raise this to the author before planning. It is the single largest
     unresolved dependency in the phase, and option 3 (uniform grid, e.g. 4×4 = 256/384) costs no
     code and still delivers BAND-01's stated domain with wider error bars — which is exactly D-41's
     own justification.

2. **Same question for D-40 (E6 `scale` axis) and D-15/D-16 (E2 config variants).** (SP-2, SP-4)
   - Both are experiment-script or config-file changes, not driver changes. D-52 explicitly claims
     "requires no change to any experiment"; that claim covers concurrency only, and the three grid
     cuts break it.
   - **Recommendation:** group all three into one explicit go/no-go plan task with a
     `checkpoint:human-verify`, sequenced early so a "no" can be absorbed.

3. **What happens to `rerun_19_4.sh` and `rerun_19_5.sh` after the rename?** (A5)
   - CONTEXT's D-25 names only `rerun_19_3.sh`. Leaving three drivers on disk, one renamed, is the
     footgun D-23 exists to close, one level up.
   - **Recommendation:** archive both alongside the state files in the DRIVER-04 commit, **after**
     their stage functions have been lifted into the new driver.

4. **Where do E2's `reprojection_residuals.csv` / `reconstruction_errors.csv` baselines live for
   `--baseline-dir`?** (SP-5)
   - They are gitignored by policy (DATA-01b) and ship in the Zenodo archive, so neither
     `experiments/results/` nor the new archive directory will have them.
   - **Recommendation:** `--baseline-dir` must report a missing baseline as N/A rather than raising
     — a one-line guard around `pd.read_csv` in the *caller*, not in `compare_experiment_csv`
     (whose totality contract at `_io.py:348-357` deliberately excludes I/O errors).

5. **How does the `smoke` profile assert anything, given SP-7?**
   - E1 and E2 write nothing on `--smoke`; the other five write nothing when `--out` equals the
     default string.
   - **Recommendation:** the smoke pass runs with `--out experiments/results_smoke`, and the
     manifest carries a per-artifact `profiles: [...]` field so E1/E2 artifacts are simply not
     expected under `smoke`. Do not try to make E1/E2 write on smoke — that is an experiment change
     for an acceptance convenience.

---

## Metadata

**Confidence breakdown:**
- Current driver coverage / missing invocations: **HIGH** — three files read end to end, `grep -rn`
  across all `*.sh` for the orphan scripts.
- Column constants and artifact shapes: **HIGH** — imported and measured, not read off a doc.
- Provenance mechanism (OpenCV suffix, `git describe`): **HIGH** — executed in the AquaCal env.
- Output-tree inventory: **HIGH** — every D-29/D-30 number independently reproduced.
- Test breakage under DRIVER-04: **HIGH** — the assertions were read; not executed against a moved
  tree (that would require performing the move).
- Runtime estimates: **MEDIUM** — inherited from CONTEXT and the state files; `e7_band` is
  explicitly unmeasured by author decision.
- Orphan-script runtimes: **LOW** — inferred from code shape.

**Research date:** 2026-08-18
**Valid until:** 2026-08-21 (submission). This document describes a tree that Phase 26 is about to
change; re-verify any `path:line` before citing it in a later phase.
