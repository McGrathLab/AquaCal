# Phase 28: Suite Execution on Linux Machine — Research

**Researched:** 2026-08-24
**Domain:** Off-repo execution of a frozen experiment-suite driver; provenance capture
**Confidence:** HIGH (every load-bearing claim was read out of the frozen tree or measured on this box this session)
**Attempt:** 2, at `rerun-freeze-02`

> **No external research was performed, and none was needed.** This phase writes no code, selects
> no library, and integrates no third party. Every decision it can still make is constrained by a
> script that already exists inside the frozen tag. The whole of the useful research is therefore
> *internal*: what the driver does, what it refuses, what it emits, and what the previous attempt
> measured. WebSearch/WebFetch were not used. The one seam-driven external check that *was* run —
> the package-legitimacy gate — is reported in full below, including why its verdicts are not
> actionable here.

---

<user_constraints>
## User Constraints (from 28-CONTEXT.md)

### Locked Decisions

**Clone fresh — do not reuse the working copy (D5)**

The run MUST start from a clean clone:

    git clone --branch rerun-freeze-02 https://github.com/McGrathLab/AquaCal.git

**Do NOT reuse `~/aquacal-frozen-rerun-freeze-02`.** Plan 29.1-08's `--smoke` verification ran
in that tree. `STATE_FILE` is derived from `RUN_EXPERIMENT_SUITE_DRY_RUN` and the short sha only
(`run_experiment_suite.sh:288-292`); `--smoke` does not enter it. A completed rehearsal therefore
leaves `run_experiment_suite_state.<sha>.tsv` holding 20 `complete … 0` lines, and **a real run
at that same sha would skip all 20 stages and produce nothing.** The dry-run path has an explicit
`.dryrun.tsv` separation for exactly this failure mode; `--smoke` has none.

A second reason the fresh clone matters: `experiments/results_e2_band` holds zero tracked files
at HEAD, and git does not track empty directories, so a fresh clone does not contain it at all.
That *absent* state is what the tag ships and what the gate expects (single `N/A`). A working
copy left in the *present-and-empty* state turns that one `N/A` into two `FAIL`s.

**Expect exactly three test failures — do not treat them as a regression (D4)**

The tag was deliberately cut with a known, ruled-on 3-test failure. `pytest tests/` at this sha
reports:

    2407 passed, 26 skipped, 3 failed

    FAILED tests/unit/test_discard_accounting.py::test_matches_frozen_anchor
    FAILED tests/unit/test_optim_common.py::TestPerObservationDetailSinks::test_detail_sink_recomputed_geometry_matches_projector
    FAILED tests/unit/test_pipeline.py::TestSolverConfigSeedIsInert::test_matches_pre_change_anchor

All three are exact-equality anchor comparisons disagreeing at float noise — 1 ULP on a
`sqrt(dx²+dy²)`, rel. 1.4e-9 on a reprojection RMS, and 2.4e-16 on the off-diagonal *zeros* of an
identity rotation. They are deterministic (bit-for-bit reproducible in isolation) and are not a
threading artifact (unchanged under `OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1`).
Independently confirmed 2026-08-24 by the Phase 29.1 verification: same 3 failures, same node ids.

**No artifact of this phase may claim the suite is clean.** A run reporting 0 failures here is
the anomaly and must be investigated, not celebrated.

**Expect D1's eight provenance failures to return**

`tests/unit/test_experiments_provenance.py` carries 8 pre-existing failures that reappear once
`experiments/results/` is repopulated by this run. They are parametrized over the artifacts
actually present in the committed results tree and assert provenance properties of the *previous*
run's output. Verified byte-for-byte identical at the branch base `89c2092`. Expected; not caused
by this phase.

**Set `PRELAUNCH_GATE_PYTHON` explicitly (D-28)**

During 29.1's rehearsal the driver warned about the fallback and resolved `python` on `PATH`,
which *happened* to be the correct interpreter. Do not rely on that. Set it explicitly for the
production run so `interpreters_agree` is true by construction rather than by luck.

**Leave `SUITE_E2_RELEASE_CONFIG` unset (D-12)**

That variable is the documented **Windows** escape hatch. On the Linux run machine the in-repo
default `experiments/configs/e2_release_linux.yaml` resolves correctly. Attempt 1 set it because
it ran from Windows; this attempt must not.

**Use no pre-flight override flags**

Neither `--allow-nonempty-out` nor `--skip-e2` nor `--allow-frameset-mismatch`, in any form. If
the pre-flight refuses, archive the offending trees aside — as both attempt 1 and 29.1's
rehearsal did — rather than overriding the gate. The pre-flight refusing is a signal, not an
obstacle.

**`check_e2_band`'s `--smoke` quirk is known and NOT fixed (D6)**

Its sibling-directory resolution does not honour `--smoke`. Left unfixed deliberately: changing
the script that judges every artifact, inside the freeze window, is a trade attempt 1 declined
and 29.1 declined again. Do not "fix" it during this phase — the tag is frozen.

### Claude's Discretion

CONTEXT.md declares no explicit discretion section. What it leaves open, by omission, is the
*shape of the plan* — how the run is staged, monitored and returned — subject to every decision
above. It also carries three "Specific Ideas", which read as directives and are treated as such
below:

- Build the environment by executing the tag's **own** install command verbatim, not a
  remembered one. 29.1's whole criterion 5 was that this command was wrong; the corrected form
  ships in the tag.
- Record the interpreter path and `pip freeze` into the returned artifacts as `freeze02-*`
  counterparts to attempt 1's files, so the two attempts are comparable line for line.
- The suite's own driver prints *"NOTHING THIS RUN PRODUCES IS EVIDENCE"* during `--smoke`.
  This phase's run is not a smoke run; make sure the distinction is unambiguous in the log
  that gets returned.

### Deferred Ideas (OUT OF SCOPE)

- **Grading the returned run** — `check_rerun_gates.py` as a verdict, the E2 sanity control, the
  E7 before/after comparison. That is Phase 29.
- **Publishing the Zenodo results package** — Phase 29's RUN-05.
- **Any source change.** This phase runs a frozen tag and must not modify it.
- **Phase 29's success criterion 6** (Zenodo published before the 2026-08-21 submission) is
  unsatisfiable as written — the date has passed. Flagged upward; does not block Phase 28.
- **The E7 before/after comparison** and the **Zenodo package**, both left open by attempt 1,
  remain Phase 29's work.
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| RUN-02 | *"The full experiment suite — E1 through E7, the band runs, and **E2** — executes once end to end at that single sha"* [VERIFIED: .planning/REQUIREMENTS.md:188-189] | The single mechanism that satisfies this is one invocation of `experiments/run_experiment_suite.sh` at the frozen sha. § *The Stage List* enumerates the 20 stages the driver covers; § *The Complete Artifact Set* enumerates the 62 artifacts the `full` profile expects; § *Acceptance* gives the three signals that prove "executed end to end" rather than "exited". |

**ROADMAP success criteria, mapped to what proves each from the returned artifacts:**

| # | Criterion | What proves it |
|---|-----------|----------------|
| 1 | A result file for every experiment, none missing | The end-of-run roll-up reaching **0 FAIL** at `--profile full`. The roll-up is the only check that judges what is *absent*; see § *Acceptance*. |
| 2 | The run manifest records exactly one `aquacal_version`/git sha across all artifacts | `gate3_git_sha_consistency` PASS in the roll-up, plus `run_manifest.json`'s `git_sha` field. Note the § *Pitfall 2* trap: agreeing shas do not prove agreeing code. |
| 3 | The set of returned invocations matches the driver's coverage from Phase 26 one for one | The 20 stage names in the state TSV, each with a `complete` line at exit 0. See § *Verifying criterion 3* — this is the one criterion the returned artifacts cover only *indirectly* by default, and there is a zero-risk option to make it direct. |
</phase_requirements>

---

## Summary

This phase has no design space. The suite driver, its pre-flight refusals, its stage list, its
expectation manifest and its operator procedure all ship inside `rerun-freeze-02` and are
byte-frozen. The plan's entire job is to (a) build an environment that satisfies the tag's own
stated requirements, (b) prove it is the right environment *before* committing hours to it,
(c) launch one command and leave it alone, and (d) return the output with its provenance intact.
Every remaining risk is operational, and every one of them is already documented — attempt 1 ran
this suite once, on this exact machine, and its failures were diagnosed and fixed by Phase 29.1.

The three things most likely to destroy this run, in order, are: **reusing a contaminated
environment** (an editable install pointing at a different checkout produces artifacts stamped
with the frozen sha while executing other code — silent, and no gate catches it); **reusing a
tree that already has a state file for this sha** (all 20 stages skip and the run produces
nothing while looking finished); and **reading `$?` as the verdict** (a healthy run exits
non-zero by design). All three have already happened at least once in this project's history.

Attempt 1's measured wall clock on this machine was **6 h 00 m**, not the 15-16 h the tag's
`HANDOFF.md` budgets. The handoff's figure is derived from a Windows box and is an upper bound
here; plan against ~6-8 h with the run still able to survive the SSH session ending.

**Primary recommendation:** Follow `experiments/HANDOFF.md` §2.1 verbatim, from a fresh clone,
under a purpose-built conda environment, with `PRELAUNCH_GATE_PYTHON` set to that environment's
absolute interpreter path and no override flags of any kind. Assert `aquacal.__file__` is inside
the clone and `cv2.__version__` is `4.13.x` *before* launching. Read the acceptance verdict from
the last `END-OF-RUN COMPLETENESS ROLL-UP` block, never from the exit code.

---

## Architectural Responsibility Map

There is no application architecture here; the tiers are execution venues. Assigning work to the
wrong venue is this phase's analogue of a mis-tiered feature — e.g. a code fix applied on the run
machine instead of the planning box splits one run's artifacts across two shas.

| Capability | Primary tier | Secondary tier | Rationale |
|------------|--------------|----------------|-----------|
| Choosing the sha, the flags, the env | Operator shell (planning session) | — | Read once at driver start (`run_experiment_suite.sh:278`); nothing downstream can change it. |
| Environment construction | Conda env on the run machine | — | Must be **new**: the pre-existing `aquacal` env carries OpenCV 4.14.0, the version the pin excludes. [CITED: experiments/HANDOFF.md §1.2] |
| Provenance capture | Driver pre-flight (`_run_manifest`, `_env_lock`) | — | Automatic. *"Neither file needs anything typed into it. Do not hand-edit either one."* [CITED: experiments/HANDOFF.md:149] |
| Abort authority | Pre-flight only (stages 1-2) | — | *"Nothing aborts once stage 1 has begun"* — D-03/D-50, enforced at `run_experiment_suite.sh:2058-2076`. |
| Scheduling / concurrency | Driver's pool | — | Derived from `suite_expectations.json` per-stage attributes. Do not re-tune. |
| Computation | 18 stage subprocesses (`python -u -m experiments.<mod>`) | — | Bare `python` from PATH — hence the "activate the env first" requirement. |
| Verdict | End-of-run roll-up | Per-stage gates (early warning only) | Per-stage gates are structurally red; see § *Pitfall 1*. |
| Grading, committing, publishing | Phase 29 | — | Explicitly out of scope per CONTEXT. |
| Code fixes, if any are needed | Planning box + a **new** tag | — | *"Tags are never moved."* [CITED: experiments/HANDOFF.md §2.7] |

---

## The Frozen Package: what ships and what it does

### The tag

    tag object   533f79fbe1bf7022466e341cb4a4921f1e2575a5
    commit       7005a2771aa115e4f4c1284cec7e145739586a4a
    tag name     rerun-freeze-02
    short sha    7005a27

[VERIFIED: 29.1-FREEZE-RECORD.md:9-16, cross-checked against the live remote this session —
`git ls-remote --tags https://github.com/McGrathLab/AquaCal.git rerun-freeze-02` returns
`533f79fbe1bf7022466e341cb4a4921f1e2575a5	refs/tags/rerun-freeze-02`.]

The short sha matters operationally: it names the state file, the failures file and the stage-log
directory. Everything the plan writes about "the state file" is
`experiments/run_experiment_suite_state.7005a27.tsv`.

**The working copy this research was performed in is NOT the tag.** It is
`/home/tlancaster/aquacal-frozen-rerun-freeze-01` at `rerun-freeze-02-14-g687f969`. However
`git diff --stat rerun-freeze-02 HEAD -- experiments/ src/ pyproject.toml` prints nothing — the
14 intervening commits touch `.planning/` only. Every line-numbered citation below is therefore a
citation of the tag. [VERIFIED: measured this session.]

### The Stage List — 20 stages, and the order is a correctness constraint

[VERIFIED: experiments/run_experiment_suite.sh:541-562, verbatim]

```
STAGES=(
  preflight
  prelaunch_probe
  fd_jacobian
  e1
  e7
  e5
  e2_production
  e6_repeat1
  e3
  reconstruction_bootstrap
  e2_timing
  e2_memory
  e7_band
  e5_band
  e2_band
  e1_band
  e4
  e6_band
  e7_focal_standoff
  e4_repeat
)
```

`experiments/suite_expectations.json` carries the same 20 ids [VERIFIED: measured this session —
`len(d['stages']) == 20`], and `tests/unit/test_suite_stage_list.py` asserts both directions and
proves the array is a topological order of the manifest's `depends_on` edges
[CITED: run_experiment_suite.sh:511-517].

Two ordering edges are **silent-wrong-number** bugs rather than crashes if violated, which is why
`--start-stage` is infrastructure-recovery only [CITED: run_experiment_suite.sh:142-152]:

- `e4` MUST follow `e2_production`. `resolve_e2_benchmark_path` silently drops the real-rig row
  when E2's `benchmark.json` is absent, and `benchmark_grid.csv` comes back with 9 rows instead
  of 10. *Nothing fails; the number is just wrong.*
- `e7_focal_standoff` MUST follow `e7_band`. It reads the hardcoded, cwd-relative
  `Path("experiments/results")/interface_ablation_band.csv`, deliberately ignoring `--out`.

E3's `--check` and `--force` are one atomic stage and the internal order is load-bearing:
`--check` first records the pre-regeneration state, `--force` second regenerates. *"Running
`--force` first destroys the only evidence of what moved."* [CITED: run_experiment_suite.sh:154-158]

### The six output trees plus the driver state

[VERIFIED: experiments/run_experiment_suite.sh:264-272, 304, 309, 397-407, verbatim]

```
OUT_DIR="${SUITE_OUT_DIR:-experiments/results}"
OUT_DIR_E4_REPEAT="experiments/results_e4_repeat"
OUT_DIR_E2_BAND="experiments/results_e2_band"
OUT_DIR_E2_TIMING="experiments/results_e2_timing"
OUT_DIR_E2_MEMORY="experiments/results_e2_memory"
E2_INVOCATION_DIR="${SUITE_E2_INVOCATION_DIR:-experiments/results_e2_invocations}"
SUITE_FAILURE_LOG="${STATE_FILE%.tsv}.failures.txt"
STAGE_LOG_DIR="${STATE_FILE%.tsv}.stagelogs"
```

That is **six output trees plus three state artifacts** — nine paths the preserve step must
cover. This is a concrete, checkable finding, and it contradicts the one document a planner is
most likely to copy from: § *Pitfall 6* below.

### Environment variables the run sets, and the ones it must not

| Variable | Value for this run | Why | Source |
|---|---|---|---|
| `PRELAUNCH_GATE_PYTHON` | **set**, absolute path to the new env's `bin/python` | D-28, locked in CONTEXT. Rung 1 of a 2-rung chain; rung 2 is a PATH lookup that *warns loudly*. | [VERIFIED: run_experiment_suite.sh:462-489] |
| `SUITE_E2_RELEASE_CONFIG` | **unset** | Locked in CONTEXT. Default resolves: `E2_RELEASE_CONFIG="${SUITE_E2_RELEASE_CONFIG:-experiments/configs/e2_release_linux.yaml}"` | [VERIFIED: run_experiment_suite.sh:397] |
| `SUITE_WORKERS` | leave default (**4**) | `SUITE_WORKERS="${SUITE_WORKERS:-4}"`, clamped to 4-5 with a warning outside that band. *"Do not re-tune."* | [VERIFIED: run_experiment_suite.sh:762-767; HANDOFF.md §1.5] |
| `SUITE_THREAD_CAP` | leave default (**2**) | `SUITE_THREAD_CAP="${SUITE_THREAD_CAP:-2}"`. Applies to concurrent stages only; the four `serial_alone` timing stages run uncapped by design. | [VERIFIED: run_experiment_suite.sh:798; :2043-2049] |
| `SUITE_SERIAL` | **unset** | Escape hatch only. Serial is ~22-31 h. | [CITED: HANDOFF.md §2.2] |
| `SUITE_SMOKE` / `--smoke` | **never** | This is the production run. | — |
| `SUITE_OUT_DIR`, `SUITE_STATE_DIR` | **never** | *"Test sandboxing only — not for a production run."* | [CITED: HANDOFF.md §2.2] |
| `SUITE_STAGE_PYTHON` | **never set by hand** | Exported *by* the driver (`STAGE_PYTHON="python"`). Setting it makes the manifest describe an interpreter the stages did not use. | [VERIFIED: run_experiment_suite.sh:498-500] |
| `RUN_EXPERIMENT_SUITE_DRY_RUN` | **unset** for the real run | Any non-empty value selects the `.dryrun.tsv` state path. | [VERIFIED: run_experiment_suite.sh:287-292] |

`E2_BAND_SEEDS="42,43,44"` is a driver constant, not an env var [VERIFIED:
run_experiment_suite.sh:353] — three E2 calibrations, run sequentially inside stage `e2_band`.

### Pre-flight: five refusals, two overrides that must not be used, two with no override

[VERIFIED: experiments/run_experiment_suite.sh:964-1082 and
`suite_expectations.json → preflight.overrides`, read this session]

```
"overrides": {
  "frameset_absent": "--skip-e2",
  "frameset_mismatch": "--allow-frameset-mismatch",
  "nonempty_out_dir_without_state_file": "--allow-nonempty-out",
  "free_space_below_floor": "--allow-low-disk",
  "completeness_gate_not_invokable": "--allow-gate-precheck-failure"
}
```

Order of execution, and what each will find on this machine:

1. **Run manifest write** (`_run_manifest --out experiments/results --force`). **No override
   exists.** A failure here aborts and must be fixed at the cause.
2. **Environment lockfile** (`_env_lock`). A failure is *logged, not refused* [VERIFIED:
   run_experiment_suite.sh:1040-1046].
3. **E2 frameset identity** — 13 declared extrinsic paths must exist and total ≥ 3,000,000,000 B.
   **Measured on this machine this session: 13 directories present, 3,799,100,985 B.** Passes
   with 21% margin. [VERIFIED: `du -sb /home/tlancaster/PycharmProjects/AquaCal/aquacal_data/real-rig/real-rig/extrinsic/` this session; floor from `suite_expectations.json → preflight.frameset.cheap_check.min_total_bytes` = `3000000000`]
4. **Non-empty `OUT_DIR` with no state file for this sha.** A fresh clone has no
   `experiments/results/` at all, so this cannot fire. This is the refusal most likely to be met
   if the fresh-clone rule is broken.
5. **Free space** ≥ `free_space_floor_gib: 20`. **Measured this session: 673,467,040 KiB
   available on `/` = ~642 GiB.** 32× the floor.
6. **Completeness gate invokability.** Only asks whether the gate printed a `TOTAL:` line; FAILs
   over the empty pre-run tree are expected and are not a refusal [VERIFIED:
   run_experiment_suite.sh:1274-1291].
7. **Wall-clock warning** — only if `--remaining-hours` is passed. Warns, never aborts.

`prelaunch_probe` (stage 2) is the second and last hard-abort stage, and it has **no override at
all**: *"an illegal seed makes the band unreportable, not merely suspect"* [CITED:
run_experiment_suite.sh:2073].

### The complete artifact set — 62 files, every one expected at `full`

[VERIFIED: `experiments/suite_expectations.json → artifacts`, enumerated this session: 62 entries
total, all 62 carrying `"full"` in `profiles`.]

| Stage | # artifacts | Tree | Notable |
|---|---:|---|---|
| `preflight` | 2 | `experiments/results` | `run_manifest.json`, `environment_lock.txt` |
| `fd_jacobian` | 2 | `experiments/results` | `fd_jacobian_accuracy.{csv,json}` (csv: 8 rows) |
| `e1` | 7 | `experiments/results` | incl. `e1_benchmark_refractive.json`, `e1_benchmark_nonrefractive.json` |
| `e1_band` | 3 | `experiments/results` | `exp1_band.csv` (256 rows), `exp1_parameter_band.csv` (384) |
| `e3` | 7 | `experiments/results` | 4 CSVs + provenance + 2 `.tex` fragments |
| `e5` | 3 | `experiments/results` | `index_sensitivity.csv` (11 rows) |
| `e5_band` | 3 | `experiments/results` | `index_sensitivity_seed_band.csv` (66 rows) |
| `e6_repeat1` | 3 | `experiments/results` | `generalization_sweep.csv` (14 rows) |
| `e6_band` | 3 | `experiments/results` | `generalization_sweep_band.csv` (84 rows) |
| `e7` | 11 | `experiments/results` | 4 benchmarks, 4 traces, ablation + conditioning + degeneracy |
| `e7_band` | 3 | `experiments/results` | `interface_ablation_band.csv` (480 rows) |
| `e7_focal_standoff` | 1 | `experiments/results` | `e7_focal_standoff.csv` (4 rows) |
| `e4` | 2 | `experiments/results` | `benchmark_grid.csv` (**10 rows** — 9 if E2 is missing), `.tex` |
| `e4_repeat` | 1 | `experiments/results` | `benchmark_grid_repeat.csv` (6 rows, spliced back into `results`) |
| `e2_production` | 7 | `experiments/results` (5) + `experiments/results_e2_invocations/e2_classification` (2) | `benchmark.json`, `camera_parameters.csv` (13 rows), `real_rig_metrics.json`; the 2 conditional ones are new-graded (§ *Pitfall 5*) |
| `e2_band` | 1 | `experiments/results_e2_band` | `e2_band_scope.json` |
| `e2_timing` | 1 | `experiments/results_e2_timing` | `benchmark.json` |
| `e2_memory` | 1 | `experiments/results_e2_memory` | `benchmark.json` |
| `reconstruction_bootstrap` | 1 | `experiments/results` | `reconstruction_bootstrap.json` |

`prelaunch_probe` emits nothing — it is a structural geometry check.

Note the three separate `benchmark.json` files (production / timing / memory). They live in
separate trees on purpose: *"Three E2 runs sharing one directory would overwrite each other's
benchmark.json and the surviving file would silently be whichever ran last."* [CITED:
run_experiment_suite.sh:267-270]

---

## Standard Stack

Nothing in this section is a choice this phase makes. Every entry is read out of the frozen
`pyproject.toml` and installed by the tag's own command.

### The install command — read it out of the clone, do not retype it

[VERIFIED: experiments/HANDOFF.md:48-50, verbatim]

```bash
python -m pip install -e ".[dev,bench]"
```

**Both extras are load-bearing.** [VERIFIED: HANDOFF.md:52-66]

- `dev` → `pytest`. `experiments/e3_derived_quantities.py` imports `DECLARED_CONSTANTS` from a
  test module, which imports `pytest`. Without it **e3 exits 1 on both `--check` and `--force`**.
  This is exactly what happened on attempt 1 and produced its only `STAGE FAILED` line.
- `bench` → `psutil`. Without it `cpu_count_logical` and `ram_total_bytes` are left `None`, both
  are in `REQUIRED_MANIFEST_FIELDS`, and **`gate3_run_manifest_fields` FAILs**.

The `docs` extra is **not** needed — do not install it.

### Core

| Package | Constraint | Source | Why |
|---|---|---|---|
| `opencv-python` | **`==4.13.*`** | runtime dep | **Hard pin, do not relax.** 4.14.0 detects 1.95% fewer ChArUco corners and moves reconstruction RMSE by +7.8%. [VERIFIED: pyproject.toml:40 — `"opencv-python==4.13.*",`; rationale CITED: HANDOFF.md §1.2] |
| Python | `>=3.11` | `requires-python` | [VERIFIED: pyproject.toml:10 — `requires-python = ">=3.11"`] |
| `scipy` | `>=1.16` | runtime dep | floor only |
| `numpy` | unpinned | runtime dep | deliberately — the exact set is captured as a run artifact instead |
| `pyyaml`, `matplotlib`, `pandas`, `requests`, `tqdm` | unpinned | runtime dep | |
| `natsort` | `>=8.4.0` | runtime dep | |
| `pytest` | unpinned | **`dev` extra** | [VERIFIED: pyproject.toml `[project.optional-dependencies] dev = ["pytest", "pytest-cov", "ruff", "pre-commit", "python-semantic-release",]`] |
| `psutil` | `>=5.9` | **`bench` extra** | [VERIFIED: pyproject.toml `bench = ["psutil>=5.9",]`] |

### The environment that produced attempt 1's accepted results

[VERIFIED: 29.1-VERIFICATION-BAR.md § *The environment, identified rather than described*]

    python        3.11.15 (main, Jun 11 2026, 15:20:16) [GCC 14.3.0]
    cv2           4.13.0        (opencv-python build 4.13.0.92)
    numpy         2.4.6
    scipy         1.17.1
    BLAS/LAPACK   scipy-openblas 0.3.31.188.0
    pytest        9.1.1
    psutil        7.2.2   (measured in the 29.1-08 clone env)

A freshly built environment today may resolve `numpy`/`scipy` differently, since neither is
pinned. That is by design and is recorded rather than prevented — `run_manifest.json` and
`environment_lock.txt` capture whatever actually ran. It is worth *noticing* a divergence from
the four values above and writing it into the returned record, because Phase 29's E2 sanity
control compares against a run taken under them.

### Environments already on this machine — none of them is usable as-is

[VERIFIED: measured this session]

| Env | Editable install points at | Verdict for this run |
|---|---|---|
| `aquacal` | (not inspected) | **Excluded by name** — carries OpenCV 4.14.0, the version the pin exists to reject. [CITED: HANDOFF.md §1.2] |
| `aquacal-freeze01` | `/home/tlancaster/aquacal-frozen-rerun-freeze-01/src` | Wrong checkout. Would import attempt 1's tree while stamping `7005a27`. |
| `aquacal-freeze02-cleanenv` | `/home/tlancaster/aquacal-frozen-rerun-freeze-01/src` | Despite the name — **wrong checkout**, same hazard. |
| `aquacal-freeze02-clone` | `/home/tlancaster/aquacal-frozen-rerun-freeze-02/src` | Points at the *rehearsal* clone, not the fresh one. Reusing it with a new clone is precisely the § *Pitfall 2* hazard. |

**Conclusion: build a new conda environment for this run**, and re-run `pip install -e` inside
the fresh clone. A name that encodes the attempt (e.g. `aquacal-freeze02-prod`) is worth the
keystrokes — `aquacal-freeze02-cleanenv` pointing at the *freeze-01* tree is live evidence that
env names drift from what they contain.

### Alternatives Considered

| Instead of | Could use | Tradeoff |
|---|---|---|
| A new conda env | Reuse `aquacal-freeze02-clone` | Saves ~10 min; risks the silent editable-install hazard that **no gate catches**. Rejected. |
| A fresh clone | Reuse `~/aquacal-frozen-rerun-freeze-02` | Locked against by CONTEXT D5. Measured this session: that clone's real state file *was* archived aside on 2026-08-24, so the specific 20-skip hazard is currently discharged there — but the tree also still holds `results_smoke*` trees and a rebuilt-by-hand history, and the locked decision stands. Rejected. |
| Pooled (default) | `SUITE_SERIAL=1` | ~22-31 h vs ~6-8 h, for no benefit unless the pool is implicated in a result. Rejected. |

---

## Package Legitimacy Audit

**Run this session** via `gsd-tools query package-legitimacy check --ecosystem pypi …`.

| Package | Registry | Latest release date | Downloads | Source repo | Verdict | Disposition |
|---|---|---|---|---|---|---|
| `opencv-python` | PyPI | 2026-07-02 | unknown (PyPI does not expose) | github.com/opencv/opencv-python | `SUS` | **Approved** — false positive, reason is `unknown-downloads` only |
| `scipy` | PyPI | 2026-08-21 | unknown | null in metadata | `SUS` | **Approved** — `too-new` reflects an active release cadence, not a new package |
| `numpy` | PyPI | 2026-08-09 | unknown | null in metadata | `SUS` | **Approved** — same |
| `psutil` | PyPI | 2026-01-28 | unknown | — | `SUS` | **Approved** — same |
| `pytest`, `pyyaml`, `matplotlib`, `pandas`, `natsort` | PyPI | — | unknown | — | `SUS`/`OK` | **Approved** |

**Packages removed due to `SLOP` verdict:** none.
**Packages flagged `SUS`:** all of the above — and **none of them warrants a
`checkpoint:human-verify` task.** The reasons the seam gives are `unknown-downloads`,
`no-repository` and `too-new`, all three of which are properties of PyPI's metadata surface and
of a *frequent release cadence*, not of package identity. Decisively: **this phase selects no
package.** It installs exactly what the frozen `pyproject.toml` declares, and that dependency set
has already been installed and executed twice on this machine — attempt 1's 6-hour production run
and 29.1-08's clone verification.

**The one package assertion that IS load-bearing is a version assertion, not an identity
assertion**, and the tag already prescribes the check:

```bash
python -c "import cv2; print(cv2.__version__)"   # must print 4.13.x
```

[VERIFIED: experiments/HANDOFF.md:223, verbatim: `python -c "import cv2; print(cv2.__version__)"   # must print 4.13.x`]

That check — not a registry lookup — is what the plan must gate on.

---

## Architecture Patterns

### The launch, verbatim from the tag

[VERIFIED: experiments/HANDOFF.md:218-232, verbatim]

```bash
cd "$HOME/aquacal-frozen-<tag>"

# Confirm the environment before committing 15-16 h to it:
python -c "import aquacal, sys; print(aquacal.__file__); print(sys.executable)"
python -c "import cv2; print(cv2.__version__)"   # must print 4.13.x

# The gate interpreter, by ABSOLUTE path (conda is not on the PATH for
# non-interactive SSH; see 1.1):
export PRELAUNCH_GATE_PYTHON="<conda-root>/envs/<frozen-env>/bin/python"

nohup bash experiments/run_experiment_suite.sh \
  > "$HOME/suite_run_<tag>.log" 2>&1 &
disown
```

Three properties of that command are load-bearing [CITED: HANDOFF.md:238-247]:

- **`nohup … & disown`** — the run must survive the SSH session ending.
- **The log lands OUTSIDE the output tree and outside the clone** — writing it into
  `experiments/results/` before launch would trip the driver's own non-empty-tree refusal.
- **Unbuffered output is already handled** — every stage line is `python -u -m …`.

For this attempt, substitute `<tag>` = `rerun-freeze-02` throughout, giving
`$HOME/suite_run_rerun-freeze-02.log` (or `suite_run_freeze02.log`, matching the `freeze02-*`
naming convention CONTEXT asks for).

### Pattern: the shell must have the env activated, not merely the gate variable set

*"~25 of the driver's stage invocation lines run bare `python -u -m experiments.<module>`. **The
suite must therefore be launched from a shell in which the frozen run's environment is already
activated**"* [CITED: HANDOFF.md:39-42]. `PRELAUNCH_GATE_PYTHON` covers the *gate* interpreter
only; `STAGE_PYTHON` is the literal string `python` [VERIFIED: run_experiment_suite.sh:498].

Both facts together define the correct launch shell: an interactive shell with
`conda activate <env>` already done, from which `nohup … & disown` detaches the run.

### Pattern: pre-launch assertions, in the order that fails cheapest first

A plan should encode these as an explicit pre-launch checklist, because every one of them is a
two-minute check standing in for a six-hour loss:

1. `git -C <clone> rev-parse HEAD` = `7005a2771aa115e4f4c1284cec7e145739586a4a`
2. `git -C <clone> status --porcelain` is **empty** (dirty-at-launch makes
   `gate3_run_manifest_clean_tree` FAIL, and that one is real [CITED: HANDOFF.md:461-464])
3. `ls <clone>/experiments/results` → does not exist; no
   `run_experiment_suite_state.7005a27.tsv`; no `experiments/results_e2_band`
4. `which python` resolves inside the new env
5. `python -c "import aquacal; print(aquacal.__file__)"` → path is **under the fresh clone**
6. `python -c "import cv2; print(cv2.__version__)"` → `4.13.x`
7. `python -c "import pytest, psutil"` → both import
8. `PRELAUNCH_GATE_PYTHON` is set and `-x`
9. `SUITE_E2_RELEASE_CONFIG` is **unset** (`env | grep SUITE_` should be empty)
10. The 13 extrinsic directories exist (already measured green this session)

### Pattern: resume semantics, and when resume is forbidden

A stage is skipped only if the state file carries a `complete` event **and that event's exit code
is 0** [CITED: HANDOFF.md §2.4]. Two ways to be incomplete, and both re-run: a start-only line,
and a completion line with a non-zero exit.

Resume (re-launch the same command, or `--start-stage N`) is for **infrastructure failures only**
— a reboot, a process kill, a full disk. It is **never** the recovery path for a `src/` defect;
that is always restart-from-stage-1 [CITED: run_experiment_suite.sh:183-192].

### Anti-patterns

- **Adding an override flag to get past a refusal.** `--allow-nonempty-out` in particular *"can
  silently cost you the verdict"* — it makes the roll-up report another run's artifacts as yours,
  which is the F-001 shape. Move the offending tree aside instead. [CITED: HANDOFF.md:312-318]
- **Patching the running clone.** *"A stage that ran at a different commit than the rest makes the
  whole run unreportable."* [CITED: HANDOFF.md:419-421]
- **Backgrounding the run from a subagent.** *"NEVER via `run_in_background`, and NEVER from a
  subagent. That harness kills background commands at 35-50 min, and a subagent that backgrounds a
  long run and returns has stalled permanently — this project has already lost multiple sweeps and
  multiple hours to both."* [VERIFIED: run_experiment_suite.sh:229-233, verbatim]
- **Re-tuning `SUITE_WORKERS` or `SUITE_THREAD_CAP`.** RAM is the binding resource; the E2 timing
  and memory stages are BLAS-unpinned *precisely so* their measurements match history.
- **Running `pytest` inside the clone while the queue is in flight.** It competes for the same
  RAM the 200-frame stages need and dirties nothing useful. If the plan wants the D4 confirmation,
  take it **before** launch or **after** the run finishes.

---

## Don't Hand-Roll

| Problem | Don't build | Use instead | Why |
|---|---|---|---|
| Recording what environment ran | A hand-written env note | `run_manifest.json` + `environment_lock.txt`, written automatically at pre-flight | *"Neither file needs anything typed into it. Do not hand-edit either one."* [CITED: HANDOFF.md:149] |
| Judging completeness | A `find`/`ls` checklist of expected files | The end-of-run roll-up (`check_rerun_gates.py <out> --profile full`) | It is the only check that judges what is **absent**; its absence is what produced F-001. |
| Detecting a wrong-tree import | Trusting the sha in the artifacts | `python -c "import aquacal; print(aquacal.__file__)"` | *"A green cross-artifact sha gate does not prove the code that ran was the frozen code."* [CITED: HANDOFF.md:398-399] |
| Per-stage timing | A stopwatch or a wrapper script | The state TSV's ISO stamps | *"These ISO stamps are the ONLY per-stage timing record that exists anywhere in this project."* [VERIFIED: run_experiment_suite.sh:240-243] |
| Deciding what to preserve | Copying attempt 1's `tar` line | The driver's own `OUT_DIR*` / `E2_INVOCATION_DIR` / `STATE_FILE` variables | Attempt 1's documented `tar` line was wrong in both directions — § *Pitfall 6*. |
| A "did every invocation run" check | Parsing the run log for command lines | The state TSV's 20 stage names, or `SUITE_DISPATCH_LOG` | The run log does **not** echo stage argv — measured: `grep -c "python -u -m"` over attempt 1's 425 KB preserved log returns **2**, both from the INTERPRETERS banner. |

---

## Common Pitfalls

### Pitfall 1: reading `$?` as the verdict — a healthy run exits NON-ZERO

**What goes wrong:** The run finishes correctly and the operator reports it as failed, or re-runs
it to chase a zero.

**Why it happens:** Per-stage gates run the full E1/E4/E6/E7 battery over *whatever the tree holds
at that moment*, so early stages FAIL on artifacts later stages have not written yet; and the four
auxiliary trees (`e2_band`, `e2_timing`, `e2_memory`, `e4_repeat`) get the whole battery too
although they hold one stage's output and no run manifest. Every finding is sticky and any finding
forces a non-zero exit. [CITED: HANDOFF.md §2.8]

**How to avoid:** Read the last roll-up block.

```bash
awk '/END-OF-RUN COMPLETENESS ROLL-UP/,0' suite_run_<tag>.log | grep -E '^\[FAIL\]|TOTAL:'
```

[VERIFIED: HANDOFF.md:452-453, verbatim]

**Expected magnitude:** attempt 1 and 29.1-08's clone verification each carried **17** sticky
`GATE FAIL` findings on a healthy run. Attempt 1's driver exited **1**.

### Pitfall 2: the editable-install hazard — agreeing shas, wrong code

**What goes wrong:** The run imports `aquacal` from a *different checkout* while stamping the
frozen sha into every artifact. The cross-artifact sha gate stays green because the *recorded*
shas agree.

**Why it happens:** Three of the four conda envs on this machine carry an editable install
pointing at `/home/tlancaster/aquacal-frozen-rerun-freeze-01/src` or the rehearsal clone
(measured this session). Activating any of them from inside a fresh clone reproduces the hazard
exactly.

**How to avoid:** New env, `pip install -e ".[dev,bench]"` *inside the fresh clone*, then the
import assertion. *"The `import aquacal` assertion is the only thing that covers it."*
[CITED: HANDOFF.md:399]

**Warning sign:** `aquacal.__file__` prints a path that is not under the fresh clone.

### Pitfall 3: the `--smoke`/real state-file collision (D5) — 20 stages skipped, nothing produced

**What goes wrong:** A real run at a sha whose state file already carries 20 `complete … 0` lines
skips every stage, exits, and produces nothing while looking finished.

**Why it happens:** `STATE_FILE` is derived from `RUN_EXPERIMENT_SUITE_DRY_RUN` and the short sha
only [VERIFIED: run_experiment_suite.sh:287-292, quoted in full above]. `--smoke` does not enter
it; the dry-run path has a `.dryrun.tsv` separation and `--smoke` has none.

**How to avoid:** Fresh clone (locked). And, as a pre-launch assertion, `ls
<clone>/experiments/run_experiment_suite_state.7005a27.tsv` must not exist.

**Measured this session:** `~/aquacal-frozen-rerun-freeze-02` currently holds only the
`.dryrun.*` forms — the real ones were archived to
`/home/tlancaster/AquaCal_smoke_aside/2026-08-24-7005a27/`. So the hazard is *presently*
discharged there. This does not change the locked decision; it is recorded so the plan does not
assert something false about that directory.

### Pitfall 4: the two never-rehearsed invocation lines

`e7_focal_standoff` and `e4_repeat` are **skipped, not reduced,** under `--smoke`, so no rehearsal
at any scale exercises their invocation lines. *"A failure in either of them will first appear
during the production run… If the production run dies, look at these two first."* [CITED:
HANDOFF.md:373-380]

**Update from attempt 1, which materially lowers this risk:** both ran to exit 0 in the 2026-08-20
production run (`e7_focal_standoff` in 0.4 s at stage 19; `e4_repeat` in 23 m 32 s at stage 20)
[VERIFIED: `experiments/freeze01_run_output/driver_state/run_experiment_suite_state.3ab9c13.tsv`,
lines for stages 19 and 20]. Neither has changed since — `src/` is byte-identical between the two
tags, and neither `e7_focal_standoff_analysis.py` nor `e4_benchmark_grid.py` is on 29.1's
changed-file list except for `e4`'s guard-count exemption. They remain the first place to look,
but they are now once-rehearsed at production scale rather than never.

### Pitfall 5: the conditional-artifact gate changed under 29.1-09 — absence is no longer a free PASS

**What changed:** `degenerate_observations.csv` and `all_observation_depths.csv` were previously
scored PASS-by-absence. 29.1-09 replaced that with a machine-evaluated predicate, and corrected
their declared `dir` to `experiments/results_e2_invocations/e2_classification`.
[CITED: 29.1-CONDITIONAL-GATE-RECORD.md §2-§3]

**Why it matters here:** they are the only two `conditional: true` entries in the manifest, both
belong to `e2_production`, and both were *mis-scored* on attempt 1. On the 2026-08-20 tree the
predicate evaluates `held=True value=198` and `held=True value=True`. A run that does not populate
`experiments/results_e2_invocations/e2_classification/` will now surface as a real finding rather
than an excused absence — which is the correct behaviour, and a new way for this attempt's roll-up
to differ from attempt 1's.

**No row count is pinned for either** (`"rows": {}`), and the predicate asks only whether the
flagged count is non-zero — never whether it equals 198.

### Pitfall 6: the preserve list — attempt 1's documented `tar` command was wrong

**What goes wrong:** A plan copies `.planning/RETURN-HANDOFF-2026-08-20.md` §2's `tar` invocation
and silently loses three output trees.

**The evidence.** That document's `tar` line names:
`experiments/results`, `experiments/results_e2_band`, `experiments/results_e4_repeat`,
`experiments/results_linux32gb`, and the three state artifacts. But:

- `experiments/results_linux32gb` **does not exist and never did**. The string occurs exactly once
  in the tree, inside a comment: `experiments/_run_manifest.py:382` [VERIFIED: grep this session].
- `experiments/results_e2_invocations`, `experiments/results_e2_timing` and
  `experiments/results_e2_memory` are **absent from that `tar` line** — yet all three are real
  output trees (119, 6 and 6 files respectively in attempt 1's preserved output) [VERIFIED: file
  counts under `experiments/freeze01_run_output/` this session].
- Attempt 1's own `freeze01-tree-state-at-handoff.txt` lists all six trees as untracked, so the
  operator plainly *did* preserve more than the `tar` line named.

**How to avoid:** Derive the preserve list from the driver's variables, not from prose. The
correct nine paths:

```
experiments/results
experiments/results_e2_band
experiments/results_e2_invocations
experiments/results_e2_timing
experiments/results_e2_memory
experiments/results_e4_repeat
experiments/run_experiment_suite_state.7005a27.tsv
experiments/run_experiment_suite_state.7005a27.failures.txt
experiments/run_experiment_suite_state.7005a27.stagelogs/
```

And follow the RETURN-HANDOFF's own good rule: *"If any path in that `tar` does not exist, do not
drop it silently — report which trees are missing, because that is itself a finding about what the
run produced."*

### Pitfall 7: `gate3_run_manifest_clean_tree` — dirty-at-launch vs dirty-by-writing

The manifest is written by pre-flight, **before stage 1**, so it captures the tree state at launch
only. *"Dirty-at-launch is a defect; dirty-by-writing-results is expected."* [CITED:
HANDOFF.md:461-464]. `experiments/results/` is a **tracked** path, so `git status` in the clone
goes dirty as soon as stage 1 writes — and there is deliberately no dirty-tree refusal, because it
would fire on every resume.

### Pitfall 8: expecting the wall clock the handoff quotes

`HANDOFF.md` §1.6 budgets **~15-16 h pooled**, explicitly derived from the Windows box.
**Attempt 1 on this machine finished in 6 h 00 m 21 s.** Planning a monitoring cadence against
15-16 h is harmless; planning a *timeout* against it, or reading a ~6 h finish as evidence
something was skipped, is not. The handoff already warns about the inverse error: *"do not treat
a run finishing in ~16 h as evidence that something was skipped."*

---

## Measured Baseline: attempt 1's per-stage wall clock on THIS machine

[VERIFIED: computed this session from
`experiments/freeze01_run_output/driver_state/run_experiment_suite_state.3ab9c13.tsv`, the
2026-08-20 production run at `rerun-freeze-01` on this box, `SUITE_WORKERS` default, pooled]

| Stage | idx | Duration | Notes |
|---|---:|---:|---|
| `preflight` | 1 | ~1 s | |
| `prelaunch_probe` | 2 | ~0.4 s | |
| `fd_jacobian` | 3 | 2 s | |
| `e1` | 4 | 1 m 47 s | |
| `e7` | 5 | 2 m 11 s | |
| `e5` | 6 | 8 m 34 s | |
| `e2_production` | 7 | 25 m 53 s | real-rig calibration |
| `e6_repeat1` | 8 | 36 m 47 s | must not overlap `e6_band` |
| `e3` | 9 | 7 s | `--check` then `--force` |
| `reconstruction_bootstrap` | 10 | 11 s | |
| `e2_timing` | 11 | 19 m 44 s | `serial_alone`, BLAS-uncapped |
| `e2_memory` | 12 | 20 m 05 s | `serial_alone`, BLAS-uncapped |
| `e7_band` | 13 | 21 m 46 s | |
| `e5_band` | 14 | 52 m 59 s | |
| `e2_band` | 15 | 1 h 12 m 40 s | 3 seeds (42,43,44) sequentially |
| `e1_band` | 16 | 34 m 20 s | |
| `e4` | 17 | 42 m 58 s | `serial_alone` |
| `e6_band` | 18 | **3 h 35 m 24 s** | critical path |
| `e7_focal_standoff` | 19 | 0.4 s | never rehearsed before that run |
| `e4_repeat` | 20 | 23 m 32 s | `serial_alone`, never rehearsed before that run |
| **Total** | | **6 h 00 m 21 s** | 00:14:10Z → 06:14:31Z, 20/20 at exit 0 |

Two figures in the tag's own documentation are pessimistic against this machine and should not be
used as timeouts: `e6_band`'s 8.9 h estimate (measured 3 h 35 m here) and E2's *"48-87 min each"*
per-seed calibration (≈24 min/seed here). Both estimates are Windows-box figures and are labelled
as such in `suite_expectations.json → wall_clock_summary`.

**A practical consequence for the plan:** a single ~6-8 h window is enough, and the run is over
before a human would normally check on it twice. The *only* stage worth a specific watch is
`e6_band`, and only because it is the critical path — nothing can be done about it if it is slow.

---

## Verifying criterion 3 ("the set of returned invocations matches the driver's coverage")

This is the criterion the returned artifacts cover least directly, so it deserves an explicit
answer rather than an assumption.

**What the returned artifacts give you by default:**

1. **The state TSV** — 20 stage names, each with `start` and `complete` lines and an exit column.
   That proves every *stage* in the driver's coverage ran.
2. **The 62-artifact roll-up at `--profile full`** — proves each stage's *outputs* landed, with
   row counts.
3. **The per-stage logs** — `run_experiment_suite_state.7005a27.stagelogs/<stage>.log`, one per
   stage. Their first line is the driver banner (`>>> STAGE 16/20: e1_band starting`), then the
   stage's own stdout. They do **not** echo argv.
4. **The run log** does not echo argv either. Measured: 2 occurrences of `python -u -m` in
   attempt 1's 425 KB preserved log, both from the INTERPRETERS banner.

**The one mechanism that would make it direct** is `SUITE_DISPATCH_LOG`
[VERIFIED: run_experiment_suite.sh:947-961, verbatim body]:

```bash
_record_dispatch() {
  [ -n "${SUITE_DISPATCH_LOG:-}" ] || return 0
  printf '%s\t%s\n' "${FUNCNAME[1]#run_stage_}" "$*" >>"${SUITE_DISPATCH_LOG}"
  return 0
}
```

It is called at 22 sites covering 18 stages (all but `preflight` and `prelaunch_probe`), including
E3's two invocations, `e4_repeat`'s per-cell loop plus its splice, and `e2_band`'s config emit plus
its three per-seed calibrations. Setting the variable would produce a tab-separated
`<stage>\t<argv>` record of exactly "the set of invocations".

**The trade, stated honestly.** The variable is documented as *"TEST-ONLY observability"* and
*"unset in every real and dry run except the driver's own tests"* — so setting it is a deviation
from both attempt 1's invocation and from every rehearsal of this tag. Mechanically it is inert:
the function appends one line and unconditionally `return 0`s, it is the only consumer of the
variable in the whole tree (grep: two hits, one of them the test), and a write failure cannot
propagate. **Recommendation: this is a genuine judgment call and belongs to the user, not to the
plan's author.** Present it as a discussable option. The conservative default — matching attempt 1
exactly and deriving criterion 3 from the state TSV plus the roll-up — is defensible and is what
attempt 1's evidence was accepted on.

If it *is* set, point it outside the clone (e.g. `$HOME/freeze02-dispatch.tsv`) so it cannot
dirty the tree or land inside `OUT_DIR` before pre-flight looks at it.

---

## Acceptance: the three hard signals

[CITED: HANDOFF.md:456-464 and 29.1-FREEZE-RECORD.md § *The one thing most likely to be misread*]

A run is accepted when **all three** hold:

1. **`0 FAIL` in the last `END-OF-RUN COMPLETENESS ROLL-UP` block.**
2. **No `STAGE FAILED` line** in `run_experiment_suite_state.7005a27.failures.txt`. (`GATE FAIL`
   lines are a different thing and ~17 of them are expected.)
3. **All 20 stages carrying a zero exit code** in `run_experiment_suite_state.7005a27.tsv`.

Plus one signal that is real whenever it fires: **`gate3_run_manifest_clean_tree` FAIL** means the
tree was dirty *at launch*.

**The number to expect.** Over the freeze-01 output tree, the freeze-02 gate script scores
`TOTAL: 176 PASS, 7 N/A, 0 FAIL` — 183 result lines [VERIFIED: 29.1-GATE-BEFORE-AFTER.md §3,
§5, which shows the arithmetic 175+7+2=184 before, 176+7+0=183 after]. A freeze-02 production run
should land at or near that. It is a **reference, not an assertion**: this run's tree is new, and
the two conditional-artifact lines (§ *Pitfall 5*) and any genuinely different output could move
it. Report the actual totals; do not tune anything to reach 183.

The extraction commands, verbatim from attempt 1's return procedure [CITED:
.planning/RETURN-HANDOFF-2026-08-20.md §3.1]:

```bash
awk '/END-OF-RUN COMPLETENESS ROLL-UP/,0' ~/suite_run_<tag>.log | tee ~/freeze02-rollup.txt
grep -E "STAGE FAILED" experiments/run_experiment_suite_state.7005a27.failures.txt || echo "NO STAGE FAILED LINES"
awk -F'\t' '$3=="complete" && $5!=0 {print "NONZERO:",$1,$5}' experiments/run_experiment_suite_state.7005a27.tsv
awk -F'\t' '$3=="complete"' experiments/run_experiment_suite_state.7005a27.tsv | wc -l
```

*Note the space before the filename in those `awk` calls — omitting it has bitten before.*

---

## The Return: what "returning the artifacts with provenance intact" means

Attempt 1 established the convention, and CONTEXT asks for `freeze02-*` counterparts *"so the two
attempts are comparable line for line."* Attempt 1's set, all committed to this phase's directory
[VERIFIED: `ls .planning/phases/28-full-suite-production-run/` this session]:

| File | Produced by | Attempt 1's content |
|---|---|---|
| `freeze01-rollup.txt` | `awk` over the run log | 39 KB; the roll-up block, ending `TOTAL: 175 PASS, 7 N/A, 2 FAIL` |
| `freeze01-gates-full.txt` | `check_rerun_gates.py experiments/results --profile full` re-run after the run | 34 KB; reproduces the roll-up totals exactly |
| `freeze01-env.txt` | `import aquacal` / `import cv2` / `uname -a` | 4 lines |
| `freeze01-pip-freeze.txt` | `pip freeze` | 64 packages |
| `freeze01-tree-state-at-handoff.txt` | `git status --porcelain` before any commit | 9 untracked paths |
| `rerun-freeze-01-output.sha256` | `sha256sum` of the tarball + the preserved log | 2 lines |

The bulk itself — 31 MB, 507 files, including the `DATA-01b`-gitignored data the repo will never
hold — was preserved **outside git**, read-only, at `~/rerun-freeze-01-output.tar.gz`, with its
checksum recorded in the phase directory. Both files still exist on this machine
(31,845,719 B and 425,119 B, mode `r--r--r--`) [VERIFIED: `ls -la` this session]. **Attempt 2 must
not overwrite either**, and must not reuse the `freeze01-` prefix.

**Boundary note for the planner.** Attempt 1 also created branch `results/rerun-freeze-01` and
committed the output tree to it. That step was directed by `.planning/RETURN-HANDOFF-2026-08-20.md`
— a document whose own commit is titled `docs(29): …` — and it discharges **RUN-04**, which
REQUIREMENTS.md maps to **Phase 29** [VERIFIED: .planning/REQUIREMENTS.md:273 — `| RUN-04 | Phase 29 | Pending |`].
28-CONTEXT.md's in-scope list stops at *"returning the artifacts with provenance intact."* The
defensible split, and the recommendation: **Phase 28 preserves + captures + records checksums;
Phase 29 commits and pushes the results branch.** This is a boundary the planner should state
explicitly rather than leave to the executor, because the evidence capture in §3 of that handoff
must happen *while the tree is still pristine* and therefore cannot be deferred wholesale to
Phase 29.

---

## Runtime State Inventory

This is not a rename phase, but it *is* a phase whose correctness depends entirely on off-repo
runtime state. The same discipline applies.

| Category | Items found | Action required |
|---|---|---|
| **Stored data / prior output** | `~/rerun-freeze-01-output.tar.gz` (31.8 MB, read-only) and `~/suite_run_freeze01.log.preserved` (425 KB, read-only) — attempt 1's only copy of the DATA-01b bulk. `experiments/freeze01_run_output/` (227 tracked files) in the repo. | **Do not overwrite, do not delete.** Attempt 2 writes `freeze02-*` / `rerun-freeze-02-output.tar.gz` alongside. |
| **Live service config** | None. This suite calls no external service. The one network dependency is a Zenodo fetch, and it fires only under `--smoke` (*"A fresh clone's smoke pass downloads 4.35 GB from Zenodo record 21889922. The production run does not."*) [CITED: RETURN-HANDOFF-2026-08-20.md §7]. | None. |
| **OS-registered state** | None — no cron, no systemd unit, no service registration. The run is a detached `nohup` process only. | None. |
| **Secrets / env vars** | No credentials. The env vars that matter are the `SUITE_*` / `PRELAUNCH_GATE_PYTHON` set, all session-scoped. **`env \| grep SUITE_` must be empty before launch** — a leftover `SUITE_E2_RELEASE_CONFIG` or `SUITE_OUT_DIR` from a prior session would silently redirect the run. | Assert clean env at launch. |
| **Build artifacts / installed packages** | Four conda envs, three of them carrying an editable `aquacal` install pointing at the wrong checkout (table in § *Standard Stack*). `experiments/__pycache__` exists in both existing clones. | **Build a new env.** A fresh clone has no `__pycache__`. |
| **Filesystem residue from rehearsals** | `~/aquacal-frozen-rerun-freeze-02` holds `results_smoke*` trees and `.dryrun.*` state files; its real state files were archived to `~/AquaCal_smoke_aside/2026-08-24-7005a27/`. `~/AquaCal_smoke_aside/2026-08-24-a833a15/` holds 29.1-07's run A/run B logs. | Leave all of it alone. **Delete nothing** — attempt 1's directive 5. Clone fresh to a *new* path (e.g. `~/aquacal-frozen-rerun-freeze-02-prod`) so the rehearsal clone is not shadowed or confused with it. |

---

## Environment Availability

[VERIFIED: all rows measured on this machine this session]

| Dependency | Required by | Available | Value | Fallback |
|---|---|---|---|---|
| The frozen tag on the remote | The fresh clone | ✓ | `refs/tags/rerun-freeze-02` → `533f79fb…` | Clone from the local repo at the tag, as 29.1-08 did |
| E2 frameset (13 extrinsic dirs) | pre-flight, `e2_production`, `e2_band`, `e2_timing`, `e2_memory`, `e4`'s real-rig row | ✓ | 13 dirs, 3,799,100,985 B (floor 3,000,000,000) | none — `--skip-e2` is forbidden by CONTEXT and would make the run synthetic-only |
| E2 intrinsic dirs (13) | `e2_*` | ✓ | present at the config's absolute paths | — |
| Free disk on the clone filesystem | pre-flight floor 20 GiB | ✓ | ~642 GiB free on `/` | — |
| RAM | 200-frame stages, 9.3-11.3 GiB each | ✓ | 31 GiB total | `SUITE_SERIAL=1` (rejected) |
| Logical cores | pool of 4-5 | ✓ | 32 | — |
| Python ≥ 3.11 | `requires-python` | ✓ via conda | 3.11.15 available in existing envs; a new env needs `conda create -n <name> python=3.11` | — |
| `conda` | env construction | ✓ (interactive shell) | initialised in `~/.bashrc` — **not** available to `ssh host 'cmd'` | absolute interpreter paths |
| Network (PyPI) | `pip install -e ".[dev,bench]"` | assumed ✓ | — | — |
| Network (Zenodo) | **not needed** for a production run | — | — | — |

**Missing dependencies with no fallback:** none.
**Missing dependencies with fallback:** none.

The single environment item that does not yet exist is **the run's conda environment**, which this
phase creates. Everything else is green.

---

## Validation Architecture

`workflow.nyquist_validation` is absent from `.planning/config.json` [VERIFIED: read this session
— the `workflow` block contains `research`, `plan_check`, `verifier`, `auto_advance`,
`_auto_chain_active`, `use_worktrees` and no `nyquist_validation` key], so the section is
included. It needs an honest caveat: **this phase writes no code, so there is nothing for a unit
test to cover.** Its "tests" are assertions about a run.

### Test framework

| Property | Value |
|---|---|
| Framework | pytest (via the `dev` extra); `[tool.pytest.ini_options]` in `pyproject.toml` |
| Config file | `pyproject.toml` |
| Quick run | `pytest tests/unit/test_run_experiment_suite_dryrun.py -q` (67 tests; the driver's own wiring harness) |
| Full suite | `pytest tests/ -q` — **28 min on this machine**, and **expected to report 3 failures** (D4) |

### Phase requirements → verification map

| Req / criterion | Behavior | Type | Automated command | Exists? |
|---|---|---|---|---|
| RUN-02 / SC-1 | Every expected artifact produced | roll-up | `awk '/END-OF-RUN COMPLETENESS ROLL-UP/,0' <log> \| grep -E '^\[FAIL\]\|TOTAL:'` | ✅ in-tree |
| RUN-02 / SC-1 | Re-verifiable after the run | gate | `python experiments/check_rerun_gates.py experiments/results --profile full` | ✅ in-tree |
| RUN-02 / SC-2 | One sha across all artifacts | gate | `gate3_git_sha_consistency` line in the roll-up | ✅ in-tree |
| RUN-02 / SC-2 | Manifest fields all non-null | gate | `gate3_run_manifest_fields` line | ✅ in-tree |
| RUN-02 / SC-3 | 20 stages, all at exit 0 | state file | `awk -F'\t' '$3=="complete" && $5!=0' …tsv` and `… \| wc -l` = 20 | ✅ in-tree |
| Env correctness | Library imported from the fresh clone | assertion | `python -c "import aquacal, sys; print(aquacal.__file__); print(sys.executable)"` | ✅ in-tree |
| Env correctness | OpenCV pin holds | assertion | `python -c "import cv2; print(cv2.__version__)"` | ✅ in-tree |
| D4 caveat | 3 known failures still 3, same node ids | pytest | `pytest tests/ -q` **before launch or after the run, never during** | ✅ in-tree |
| Clean launch | Tree clean at launch | gate | `gate3_run_manifest_clean_tree` line | ✅ in-tree |

### Sampling rate

- **Pre-launch:** the 10-item assertion checklist in § *Architecture Patterns*. Minutes.
- **Optional pre-launch:** the driver's dry run —
  `RUN_EXPERIMENT_SUITE_DRY_RUN=1 bash experiments/run_experiment_suite.sh` — exits 0, walks all
  20 stages in ~1 s, and writes only to the `.dryrun.tsv` path. **Cheap and safe**; it proves the
  queue's wiring in the actual clone before an overnight commitment. Recommended.
- **During the run:** `tail` the log; check that the stage index advances. Nothing to sample.
- **At completion:** the three hard signals.

### Wave 0 gaps

**None.** Every check above already exists inside the frozen tag. This phase adds no test file,
and must not — the tag is frozen.

---

## Security Domain

`security_enforcement` is not set in `.planning/config.json` (absent = enabled), so the section is
included. The honest assessment: **this phase has almost no attack surface**, and the two real
considerations are disclosure and irreversibility rather than exploitation.

### Applicable ASVS categories

| Category | Applies | Control |
|---|---|---|
| V2 Authentication | no | No auth surface. The only credentialed operation is `git clone` over HTTPS from a public repo. |
| V3 Session Management | no | — |
| V4 Access Control | no | Single-operator local execution. |
| V5 Input Validation | **partially** | The suite's *inputs* are validated by pre-flight's frameset identity check — identity, not mere presence, precisely because *"a presence-only check passes cleanly on the wrong archive."* Do not weaken it. |
| V6 Cryptography | **yes, narrowly** | `sha256sum` over the returned tarball is the artifact-integrity control. Record it; do not skip it. |
| V14 Configuration | **yes** | The one-way doors below. |

### Threat patterns relevant to this phase

| Pattern | STRIDE | Mitigation |
|---|---|---|
| Wrong-code-right-sha (editable install at another checkout) | **Spoofing** (an artifact claims provenance it does not have) | The `import aquacal` assertion. No gate catches this. |
| Another run's artifacts reported as this run's | Spoofing | The non-empty-`OUT_DIR` refusal. **Do not override it.** |
| Publishing to PyPI by accident | Tampering / irreversibility | Already mitigated by the tag name: `publish.yml` triggers on `push: tags: ['v*']` and `rerun-freeze-02` does not match. Verified with git's own ref-glob engine at freeze time. **This phase pushes no tag at all**, so the door stays shut. |
| Disclosure of the operator's home directory | Information disclosure | Already ruled **intentional and required**: `experiments/configs/e2_release_linux.yaml` embeds 26 absolute paths under `/home/tlancaster/…`, classified as such by 27-10's pre-push audit, on the reasoning that *"a sanitised path that does not resolve on the target would be strictly worse."* Do not sanitise it; do not treat its appearance in returned logs as a new finding. |
| Losing the only copy of a 6-hour artifact | Denial of service (self-inflicted) | Preserve **first**, `chmod a-w`, checksum, and never `git checkout` in the clone (*"Merge, never checkout"*). |

---

## State of the Art

| Old (attempt 1, `rerun-freeze-01`) | Current (`rerun-freeze-02`) | Why it changed |
|---|---|---|
| `HANDOFF.md` §1.2 said `pip install -e .` | `pip install -e ".[dev,bench]"` | 29.1-04. The omission killed e3 outright and nulled two required manifest fields on attempt 1. |
| E4's real-rig row published a null guard count → `gate1_guard_count` FAIL | Publishes the 198 above-water corners E2 measured; gate exempts `record_source="pipeline"` rows and names the exemption in its PASS line | 29.1-01 / 29.1-05 |
| `e1_seed_band_degeneracy_breakdown.json` expected by three manifests, produced by nothing → completeness FAIL | Unclaimed from the manifests; the expectation no longer generates a result line | 29.1-02 |
| `degenerate_observations.csv` / `all_observation_depths.csv` PASS-by-absence at the wrong `dir` | Machine-evaluated predicate at `results_e2_invocations/e2_classification` | 29.1-09 |
| `experiments/results/` shipped populated in the tag | Moved to `experiments/freeze01_run_output/`; the tag ships an empty output tree | 29.1-06 — the pre-flight requires it |
| Run launched from a Windows-shaped invocation (`SUITE_E2_RELEASE_CONFIG` set, `PRELAUNCH_GATE_PYTHON` at a `.exe`) | Linux-native: config default resolves, gate interpreter set to an absolute conda path | D-12 / D-28 |
| Gate roll-up over that tree: **175 PASS / 7 N/A / 2 FAIL** | **176 PASS / 7 N/A / 0 FAIL** with no artifact regenerated | 29.1-GATE-BEFORE-AFTER.md |

**Still open and deliberately unfixed inside the freeze:**

- `check_e2_band`'s sibling-directory resolution ignores `--smoke` (D6). Irrelevant to a
  production run, which writes to `experiments/results` and `experiments/results_e2_band` anyway.
- `e7_interface_ablation.py`'s band carries the same benchmark-overwrite hazard 29.1-02 fixed at
  E1. **Measured 2026-08-24: it does NOT fire in the production run** — `run_stage_e7_band`
  (`run_experiment_suite.sh:1522`) passes no `--force`, so `force=False` reaches the call and the
  resumability guard holds; the `--force` at `:1511` belongs to the single-seed E7 stage. E5 is
  unaffected (`e5_index_sensitivity.py` has zero `write_direct_call_benchmark` calls). **Residual
  risk: one manual `--force` band run at E7 fires it — do not run E7's band by hand.**
  [VERIFIED: `.planning/todos/pending/2026-08-20-e7-band-mirrors-e1-benchmark-overwrite-hazard.md`
  as amended by commit `8d1576e`]
- `HANDOFF.md` still carries **no warning** about rehearsing with `--smoke` at the sha you are
  about to run for real (D5). That is why the fresh-clone rule has to be carried by the plan
  rather than by the tag.

---

## Assumptions Log

| # | Claim | Section | Risk if wrong |
|---|---|---|---|
| A1 | PyPI is reachable and `pip install -e ".[dev,bench]"` resolves without a proxy/mirror | Environment Availability | Blocks env construction; discovered in minutes, not hours. Low. |
| A2 | A fresh env built today resolves `numpy`/`scipy` compatibly with the frozen code (neither is pinned) | Standard Stack | A major-version bump could change results or break import. Mitigated by the manifest recording what actually ran, and by the pre-launch import assertions. Medium — worth *noticing* the resolved versions and comparing to numpy 2.4.6 / scipy 1.17.1 before launching. |
| A3 | The E2 frameset at `/home/tlancaster/PycharmProjects/AquaCal/aquacal_data/…` remains present and unchanged at launch time | Environment Availability | Pre-flight catches it — refuses with ABSENT or MISMATCH before any stage runs. Low. |
| A4 | The reference roll-up total for a healthy freeze-02 production run is at or near `176 PASS / 7 N/A / 0 FAIL` | Acceptance | That figure was measured over the **freeze-01 output tree** with the freeze-02 gate script, not over a freeze-02 run. Treat it as a reference, not a target. Medium. |
| A5 | `pytest tests/` still reports exactly the same 3 failures in a freshly built environment | User Constraints (D4) | If a different numpy/scipy resolves, the count could move. It is a *caveat to report*, not a gate. Medium — and it is a reason to run pytest **before** launching, so a surprise is cheap. |
| A6 | `SUITE_DISPATCH_LOG` is inert in a real run | Verifying criterion 3 | Two grep hits in the whole tree and an unconditional `return 0` make this near-certain, but it has never been exercised in a production run. Flagged as a user decision rather than a plan default. |
| A7 | ~6-8 h is the realistic window | Measured Baseline | Derived from attempt 1 on this exact machine. A slower resolve or a contended box could stretch it. Low; nothing depends on the estimate except monitoring cadence. |

---

## Open Questions

1. **Where does the Phase 28 / Phase 29 boundary fall for committing the results?**
   - Known: RUN-04 ("returned results are committed with provenance intact") maps to Phase 29 in
     REQUIREMENTS.md; CONTEXT's in-scope stops at "returning the artifacts with provenance intact";
     attempt 1 nonetheless created and pushed `results/rerun-freeze-01` under a Phase-29 handoff
     doc, and separately committed `freeze01-*` evidence into the Phase-28 directory.
   - Unclear: whether this attempt's plan should push `results/rerun-freeze-02`.
   - Recommendation: **Phase 28 preserves + captures `freeze02-*` evidence + records checksums;
     Phase 29 commits and pushes the results branch.** Have the plan state this explicitly. The
     evidence capture cannot be deferred — `gate3_run_manifest_clean_tree` and
     `git status --porcelain` must be read while the tree is still pristine.

2. **Should `SUITE_DISPATCH_LOG` be set to make criterion 3 mechanically checkable?**
   - Known: it is inert, single-purpose, and would produce exactly the artifact criterion 3
     describes. It is also documented as test-only and was not set for attempt 1.
   - Recommendation: surface as a user decision in planning. Default to *not* setting it.

3. **Should `pytest tests/` be run in the fresh clone, and when?**
   - Known: D4 requires that no artifact of this phase claim the suite is clean, which implies the
     3-failure state should be *stated*. The tag's own freeze record already states it, so
     re-measuring is confirmation rather than a requirement. It costs ~28 min and competes for RAM.
   - Recommendation: run it **before** launch (cheap confirmation that the new environment
     reproduces the known state, catching an A2/A5 surprise before six hours are spent), and never
     while the queue is in flight.

4. **What clone path should be used?**
   - Known: `~/aquacal-frozen-rerun-freeze-02` is taken by the rehearsal clone and must not be
     reused or shadowed.
   - Recommendation: a distinct path that names the attempt, e.g.
     `~/aquacal-frozen-rerun-freeze-02-prod`. Note that `HANDOFF.md` §2.1's `cd
     "$HOME/aquacal-frozen-<tag>"` line assumes the plain name; the plan should state the actual
     path once and use it consistently, since `e7_focal_standoff` and `reconstruction_bootstrap`
     read cwd-relative paths and the driver `cd`s to the repo root itself
     (`run_experiment_suite.sh:261`).

---

## Sources

### Primary (HIGH confidence — read from the frozen tree this session)

- `experiments/run_experiment_suite.sh` (2,476 lines) — stage list, output trees, state-file
  derivation, interpreter resolution, pre-flight, `_record_dispatch`, `run_one_stage`, `main`
- `experiments/HANDOFF.md` (470 lines) — the operator procedure, in full
- `experiments/suite_expectations.json` — 62 artifacts, 20 stages, `preflight` block, wall-clock summary
- `experiments/configs/e2_release_linux.yaml` — the 26 absolute frameset paths and the E2 config
- `pyproject.toml` — `requires-python`, the OpenCV pin, the `dev`/`bench` extras
- `experiments/freeze01_run_output/driver_state/run_experiment_suite_state.3ab9c13.tsv` — attempt
  1's per-stage timing, measured
- `.planning/phases/28-full-suite-production-run/freeze01-*` — attempt 1's returned evidence set

### Primary (HIGH confidence — project rulings)

- `.planning/phases/29.1-post-run-fixes-re-freeze/29.1-FREEZE-RECORD.md` — what `rerun-freeze-02` is
- `.planning/phases/29.1-post-run-fixes-re-freeze/29.1-VERIFICATION-BAR.md` — the invocation
  differences vs attempt 1, the three anchor failures, the two smoke runs
- `.planning/phases/29.1-post-run-fixes-re-freeze/29.1-GATE-BEFORE-AFTER.md` — 175/7/2 → 176/7/0
- `.planning/phases/29.1-post-run-fixes-re-freeze/29.1-CONDITIONAL-GATE-RECORD.md` — the 29.1-09 change
- `.planning/phases/29.1-post-run-fixes-re-freeze/deferred-items.md` — D1, D4, D5, D6 and their updates
- `.planning/RETURN-HANDOFF-2026-08-20.md` — attempt 1's return procedure (**and the source of the
  incorrect `tar` list — see Pitfall 6**)
- `.planning/REQUIREMENTS.md`, `.planning/ROADMAP.md`, `.planning/STATE.md`

### Measured on this machine this session (HIGH confidence)

- Frameset size, free disk, RAM, core count, conda env inventory and their editable-install targets
- Remote tag resolution for `rerun-freeze-02`
- `git diff --stat rerun-freeze-02 HEAD -- experiments/ src/ pyproject.toml` → empty
- Presence and modes of `~/rerun-freeze-01-output.tar.gz` and `~/suite_run_freeze01.log.preserved`
- Contents of `~/AquaCal_smoke_aside/2026-08-24-7005a27/` and of `~/aquacal-frozen-rerun-freeze-02`

### Secondary / Tertiary

- None. No WebSearch, no WebFetch, no third-party documentation was consulted, because none is
  relevant: this phase integrates nothing and chooses nothing.
- One external seam call: `gsd-tools query package-legitimacy check --ecosystem pypi …`, reported
  in full in § *Package Legitimacy Audit*.

---

## Metadata

**Confidence breakdown:**

| Area | Level | Reason |
|---|---|---|
| Standard stack | HIGH | Read from the frozen `pyproject.toml` and the tag's own `HANDOFF.md`; nothing is chosen here |
| The driver's behaviour | HIGH | Read line by line from the frozen script; every citation carries a line number |
| The artifact set | HIGH | Enumerated programmatically from `suite_expectations.json` |
| Pitfalls | HIGH | Every one is documented in a project ruling and most were *observed* on attempt 1 |
| Wall clock | HIGH | Measured from attempt 1's state TSV on this exact machine |
| Expected roll-up totals | MEDIUM | 176/7/0 was measured over the freeze-01 tree, not over a freeze-02 run (A4) |
| Dependency resolution in a new env | MEDIUM | numpy/scipy are unpinned by design (A2, A5) |
| Criterion 3's direct verifiability | MEDIUM | The default artifacts prove it indirectly; the direct mechanism is a user decision (A6) |

**Research date:** 2026-08-24
**Valid until:** the day the run launches. This is a phase about a single frozen artifact; the
research does not decay, but the *machine state* it measured does — re-assert the frameset, the
free disk and the absence of a state file at launch time rather than trusting the numbers above.
