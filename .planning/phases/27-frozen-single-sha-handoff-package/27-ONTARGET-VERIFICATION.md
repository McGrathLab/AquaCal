# 27-ONTARGET-VERIFICATION — the frozen package, verified on the Linux run machine

Plans 27-12 and 27-13, executed on the Linux run machine against `rerun-freeze-01` on
2026-08-19/20.

**Verdict: CLOSE.** The freeze holds. One deviation is recorded below and filed as a
post-submission todo; it is an environment-setup defect, not a code defect, and it was corrected
on the target before the production run launched.

---

## 1. The clone (27-12, Task 1)

    git clone --branch rerun-freeze-01 https://github.com/McGrathLab/AquaCal.git \
      aquacal-frozen-rerun-freeze-01

| Check | Result |
|---|---|
| `.git` present | yes |
| `git rev-parse HEAD` | `3ab9c13723202a58bb50e351b0b6bc0c0ffcd59c` — the frozen sha |
| `git status --porcelain` | empty |
| `import aquacal` resolves to | `<clone>/src/aquacal/__init__.py` — the clone, not another checkout |
| `sys.executable` | `~/anaconda3/envs/aquacal-freeze01/bin/python` |
| `cv2.__version__` | **4.13.0** |
| `experiments/pre_rerun_baseline/` | present, 1.8 MB (**see note**) |
| extrinsic directories | 13 |

**Note on the baseline size.** 27-12's criterion originally said "76 MB, tracked". That was
wrong and was corrected before the on-target run: the tracked content is 226 files / ~1.7-1.8 MB.
The 76 MB is the Windows working copy, which also holds 159 *gitignored* bulk artifacts. A 1.7 MB
baseline directory in a clone is correct and complete.

## 2. The environment (27-12, Task 2)

Built fresh — the pre-existing `~/anaconda3/envs/aquacal` was **not** reused, because it carries
OpenCV 4.14.0 (the exact version the pin excludes) and an editable install pointing at a
different checkout at `27c80e7`. Reusing it would have imported unfrozen code while stamping the
frozen sha.

| Field | Value |
|---|---|
| Python | 3.11.15 |
| numpy / scipy | 2.4.6 / 1.17.1 |
| opencv | 4.13.0 |
| `git_sha` | `3ab9c137…` — matches the frozen sha |
| `git_dirty` | `false` |
| `interpreters_agree` | **`true`** |
| BLAS cap stages / unpinned | 16 / exactly the 4 `serial_alone` timing stages |

**OpenBLAS, recorded verbatim:**

    scipy-openblas, version 0.3.31.188.0
    OpenBLAS 0.3.31.188.0  USE64BITINT DYNAMIC_ARCH NO_AFFINITY Haswell MAX_THREADS=64

**D-30 verified where it actually mattered.** `gate_interpreter` and `stage_interpreter` differ
textually (`bin/python` vs `bin/python3.11`) and resolve equal through the symlink, giving
`interpreters_agree: true`. On Windows this field was uninformative — that filesystem is
case-insensitive, so it compared equal for the wrong reason. Linux is case-sensitive, so this is
the first real test of it.

## 3. The dry run (27-12, Task 3)

Completed in the foreground in ~1 s, exit 0, all 20 stages named, no override flags.

- `GATE_PYTHON` resolved via the `PRELAUNCH_GATE_PYTHON` override to the new env.
- `E2 release config: experiments/configs/e2_release_linux.yaml (in-repo default)` — **D-12's
  repointing works on Linux with no override.**
- State file: `run_experiment_suite_state.3ab9c13.dryrun.tsv` — frozen sha, separate dry-run path.
- `git status` empty afterwards, confirming the dry run's state files are correctly gitignored.

**What the dry run did NOT prove.** It stubs every stage command *including pre-flight*, so its
`SUITE COMPLETE` banner and its roll-up compared nothing (`rollup: DRY RUN`), and the frameset
identity check did not run. A dry run exits 0; a healthy real pass does not. Wiring only.

## 4. One real stage at full scale (27-13, Task 1)

`fd_jacobian` into a scratch dir outside the clone's output trees:

- exit 0, 1.6 s, `plateau_detected=True`, both artifacts written.
- Stage-scoped completeness: **PASS** on `fd_jacobian_accuracy.csv` (8 data rows, as expected)
  and on the `.json` sidecar.
- Full roll-up ran to completion; its 32 FAILs are all stages that had not run — expected.
- **Nothing written into the clone's `experiments/results/`** — the directory did not yet exist.

## 5. The on-target smoke pass (27-13, Task 2)

**Attempt 1 — FAILED, and found the deviation.** See §6.

**Attempt 2 — GREEN**, after correcting the environment:

| | Windows local pass | Linux on-target |
|---|---|---|
| Roll-up | 72 PASS / 18 N/A / **0 FAIL** | 72 PASS / 18 N/A / **0 FAIL** |
| `STAGE FAILED` lines | 0 | **0** |
| Stages at exit 0 | 20 / 20 | 20 / 20 |
| Wall clock | 10 min 56 s | 3 min 03 s |

**The verdict sets match exactly across two operating systems.** No pre-flight override flag was
used in either.

Gates worth naming individually:

- `gate3_git_sha_consistency` — *"every artifact carries the same git_sha (3ab9c137…)"*. This is
  RUN-03's core assertion, working on the target.
- `gate3_run_manifest_clean_tree` — PASS.
- `gate3_run_manifest_fields` — *"all 17 required environment fields are present and non-null"*.
- All twelve E7 gates — PASS.

### The frameset identity check — the highest-value single result

    262 usable -> 52 validation -> 7762 comparisons
    13 x 262 extrinsic frames at frame_step: 1 / max_calibration_frames: 200
    MATCH: the frameset's cheap identity check agrees with the manifest.
    preflight: E2 frameset identity check PASSED.

This is the blind spot `--smoke` structurally cannot cover — a wrong `--config` path or a bad
production YAML — and it clears four things at once on the real data: **D-09/D-10** (the
path-kind-agnostic probe; the original `p.is_file()` defect read an *image directory* set as
ABSENT and would have forced `--skip-e2`, silently making the entire run synthetic-only),
**D-11** (the committed image-set config produces the asserted signature), **D-12** (the in-repo
default resolves with no override), and **27-08's re-derived byte floor** (3.0 GB against a
measured 3.80 GB; the old 4.0 GB floor compared the Zenodo record's *packaged* size against this
check's *expanded* PNG tree, so a verified-correct frameset came in 5% under — the number was
wrong, not the data).

## 6. DEVIATION — recorded, not fixed

**The frozen package's own install command is incomplete.** `HANDOFF.md` §1.2 says
`pip install -e .`, which installs runtime dependencies only. The suite additionally needs
`pytest` (the `dev` extra) and `psutil` (the `bench` extra):

- **Without pytest, e3 dies outright.** `e3_derived_quantities.py:243` imports
  `DECLARED_CONSTANTS` from `tests/unit/test_experiments_e3_constants.py`, which imports pytest.
  Both `--check` and `--force` exited 1 with `ModuleNotFoundError`, taking four e3 artifacts and
  the LaTeX fragments with them, and producing the `STAGE FAILED` line in attempt 1.
- **Without psutil, `cpu_count_logical` and `ram_total_bytes` are `None`**, and both are in
  `REQUIRED_MANIFEST_FIELDS`, so `gate3_run_manifest_fields` FAILed.

Corrected on the target with `pip install -e ".[dev,bench]"`; attempt 2 was green.

**Why this is a deviation and not a refreeze.** No code is wrong — the shipped *instructions*
are. The correction is an environment change, fully captured in the run's own
`environment_lock.txt`. Author's ruling 2026-08-19, with the SoftwareX submission at 2026-08-21
and the production run needing to start that night. Filed as
`.planning/todos/pending/2026-08-20-POST-SUBMISSION-frozen-package-install-command-omits-required-extras.md`,
which also records the deeper design defect: a §3-facing artifact generator should not depend on
a test module, and `psutil` arguably belongs in runtime dependencies given two required manifest
fields need it.

**This deviation is the single best argument for D-05's decision to verify on the target.** It is
invisible on the development box, where pytest and psutil are always present.

## 7. Also found, not a defect

**A fresh clone's smoke pass downloads 4.35 GB.** `reconstruction_bootstrap` resolves
`reconstruction_errors.csv` in three tiers: an explicit path, then the local
`experiments/results/` copy, then the published archive via `load_example("real-rig")`. Under
`--smoke`, E2's output goes to `results_smoke`, so the second tier misses on a fresh clone and it
falls through to Zenodo.

Pinned and safe: record **21889922**, `md5:dff1012fb772d627e0f3f106d5c6de84`, 4,350,418,046 bytes,
declared in `src/aquacal/datasets/data/manifest.json` inside the frozen sha. It fetches one
specific record, not "latest" — a floating input would be a genuine provenance problem.

**The production run does not do this.** `reconstruction_bootstrap` `depends_on: [e2_production]`,
and `e2_production` produces `reconstruction_errors.csv` into `experiments/results/`, so the
second tier hits and the fresh file is used — which is what the re-run wants, since the point is
to bootstrap from *this* run's E2 output rather than the published one.

Worth stating in the handoff so nobody on a metered or air-gapped machine is ambushed.

## 8. What this does not prove

- **Two stages were never rehearsed at any scale**: `e7_focal_standoff` and `e4_repeat` have no
  `--smoke` form (D-21). Their invocation lines are unverified until the production run reaches
  them.
- **`--smoke` is not evidence.** Reduced scale says nothing about geometry, convergence, accuracy
  or runtime.
- **Existence is not correctness.** At the smoke profile the completeness gate asserts existence
  only (D-49). A gauge-corrected column full of uncorrected values passes every check here.
- **Do not extrapolate the 3.6x wall-clock difference** between the Windows and Linux smoke
  passes. Smoke is dominated by fixed overhead, and per the standing rule a runtime swing tracks
  the machine, not the diff.

## 9. Outcome

**CLOSE.** `rerun-freeze-01` at `3ab9c13723202a58bb50e351b0b6bc0c0ffcd59c` is the frozen sha for
the v2.1 re-run. No refreeze; no `rerun-freeze-02`.

The production run launched from the clone at **2026-08-20T00:14:10Z**, pre-flight PASSED with
the frameset `MATCH`, and the pool was running 4-wide with artifacts appearing in
`experiments/results/`. That run is Phase 28.
