# HANDOFF — what the Linux run machine needs, and what the run does

**Read this before building the environment or launching the suite.** It is the environment
requirements document for the receiving machine, and it lives *inside the frozen sha* on purpose:
everything here has to travel with the code rather than beside it, because provenance that lives
outside the artifact is the failure class this whole freeze exists to close.

It states the things that are true but **not discoverable from the code**: which OpenCV is
required and why, what is captured automatically, what must be confirmed on the target, how long
the run takes, what a resume does, and which invocation lines have **never been rehearsed**.

What it deliberately does not do: repeat `experiments/EXPECTATIONS.md` (how to judge a finished
run), `experiments/README.md` (what each experiment is and its CLI contract), or
`experiments/FROZEN-ROWS.md` (the rows this run will not regenerate). Read those there.

The machine this is written for is referred to throughout as **the Linux run machine**. Its
hostname, the login account and all key material are absent by construction.

---

## 1. Environment requirements

### 1.1 The interpreter

**Python 3.11 or newer.** `pyproject.toml` declares `requires-python = ">=3.11"`. On the Linux run
machine the environment used for this run is a **conda environment at Python 3.11**.

Two measured facts about that machine change how you build it:

- **There is no bare `python` on the PATH at all.** Not "the wrong version" — absent. Only
  `/usr/bin/python3` exists, at **3.10.12**, which is *below* the `>=3.11` floor and would fail at
  import rather than at a clear version check.
- **`conda` is not on the PATH for a non-interactive SSH command.** It is initialised in
  `~/.bashrc`, which `ssh host 'cmd'` never sources. Any remote step must either call the
  interpreter by **absolute path** (`<conda-root>/envs/<env>/bin/python`) or source conda
  explicitly first. A step that assumes a bare `conda activate` works over SSH fails in a way that
  reads exactly like a missing install.

This matters for the launch procedure in §2, because ~25 of the driver's stage invocation lines run
bare `python -u -m experiments.<module>`. **The suite must therefore be launched from a shell in
which the frozen run's environment is already activated**, so that bare `python` *is* that
environment's interpreter.

### 1.2 The dependency set, and the one hard pin

Install from the frozen clone:

```bash
python -m pip install -e ".[dev,bench]"
```

**Both extras are load-bearing for this suite — neither is optional.** A bare
`python -m pip install -e .` resolves `pyproject.toml`'s *runtime* dependencies only, and the
suite additionally needs two packages that `pyproject.toml` declares as **extras**:

- **`dev`, for `pytest`.** `experiments/e3_derived_quantities.py` imports `DECLARED_CONSTANTS`
  from `tests/unit/test_experiments_e3_constants.py`, and that test module imports `pytest` — so
  a **§3-facing artifact generator depends on a test module, which depends on the test runner**.
  Without `pytest`, **e3 exits 1 on both `--check` and `--force`** with
  `ModuleNotFoundError: No module named 'pytest'`, taking `code_constants.csv`,
  `newton_iterations.csv`, `cpr_grouping.csv`, `e3_provenance.json` and the LaTeX fragments
  down with it.
- **`bench`, for `psutil`.** `capture_environment()` fills `cpu_count_logical` and
  `ram_total_bytes` from `psutil` inside a `try/except`, so both are left `None` when it is
  absent. Both are in `REQUIRED_MANIFEST_FIELDS`, so **`gate3_run_manifest_fields` FAILs** — a
  Gate 3 failure caused by a missing optional package rather than by anything about the run.

> ⚠ **This was measured on the Linux run machine on 2026-08-19**, by the on-target smoke pass
> against `rerun-freeze-01`: e3 failed on both passes and Gate 3's manifest check failed, and
> `pip install -e ".[dev,bench]"` fixed both. **It did not surface on the Windows development
> box**, where `pytest` and `psutil` are permanently present because the test suite is run there
> constantly — nothing there ever asked whether the *shipped instructions* would build a working
> environment. That is precisely the Linux-only failure class the on-target verification venue
> exists to catch, and it is the strongest single argument for keeping that step. Recorded in
> `27-ONTARGET-VERIFICATION.md` §6; the instructions are corrected here.

The resulting dependency set:

| Dependency | Constraint | Source | Note |
|---|---|---|---|
| `opencv-python` | **`==4.13.*`** | runtime | **Hard pin. Do not relax it.** See below. |
| `scipy` | `>=1.16` | runtime | floor only |
| `numpy` | unpinned | runtime | deliberately — see below |
| `pyyaml`, `matplotlib`, `pandas`, `requests`, `tqdm` | unpinned | runtime | |
| `natsort` | `>=8.4.0` | runtime | |
| `pytest` | unpinned | **`dev` extra** | **Required.** e3 exits 1 on both passes without it. |
| `psutil` | `>=5.9` | **`bench` extra** | **Required.** Two `REQUIRED_MANIFEST_FIELDS` go null without it. |

The rest of the `dev` extra (`pytest-cov`, `ruff`, `pre-commit`, `python-semantic-release`)
arrives alongside `pytest` and is inert here; the run needs none of it. The `docs` extra is
**not** needed — do not install it.

**The OpenCV pin is the single most important line in the environment.** ChArUco corner detection
is entirely OpenCV's, and it changes across minor versions. A controlled single-variable experiment
(2026-08-12) measured **4.14.0 detecting 1.95% fewer corners than 4.13.0** on the published
real-rig dataset, moving the paper's **reconstruction RMSE by +7.8%**. The published numbers, the
Zenodo archive's `reference_outputs/` and the tutorial's expected-value table are a matched set
behind a DOI, so the environment that produced them is pinned rather than the numbers restated.

> ⚠ **Do not reuse a pre-existing `aquacal` environment on the Linux run machine.** The one already
> present there carries **OpenCV 4.14.0** — precisely the version this pin exists to exclude. It
> would silently produce E2 numbers that disagree with the archive the paper cites. **Build a new
> environment.**

> ⚠ **And assert where `aquacal` is imported from — do not assume it.** The pre-existing
> environment installs AquaCal as an *editable* install pointing by absolute path at a **different
> checkout**, on a different branch, at a different commit. A run launched from a fresh clone of
> the frozen tag inside that environment would still `import aquacal` from the other checkout while
> stamping the **frozen** sha into every artifact's `git_sha` — artifacts claiming provenance they
> do not have, with the shas agreeing so the cross-artifact sha gate stays green. It is silent and
> no gate catches it. After installing, run:
>
> ```bash
> python -c "import aquacal, sys; print(aquacal.__file__); print(sys.executable)"
> ```
>
> and confirm the printed path is **under the frozen clone**. If it is not, the environment is
> contaminated; rebuild it rather than patching around it.

**`pyproject.toml` and `requirements.txt` are NOT tightened for this run, on purpose.** They are
the shipped package's dependency contract. Pinning NumPy exactly there would degrade AquaCal for
every pip user in order to serve one internal run. The exact transitive set that actually ran is
captured as a run artifact instead — see §1.3.

### 1.3 What is captured automatically (do not record it by hand)

Two artifacts are written into the run's output tree at pre-flight, before any stage starts:

| Artifact | Written by | Carries |
|---|---|---|
| `run_manifest.json` | `experiments/_run_manifest.py` | the load-bearing provenance record |
| `environment_lock.txt` | `experiments/_env_lock.py` | a provenance header plus `pip freeze` |

`run_manifest.json` already records `git_sha`, `git_sha_source`, `git_describe`, `git_dirty`, `os`,
`kernel`, `machine`, `python_version`, `numpy_version`, `scipy_version`, `opencv_version`,
`opencv_build`, `cpu_model`, `cpu_count_logical`, `ram_total_bytes` and
`installed_distribution_version` — **every version that moves a number**. It also records the BLAS
thread-cap regime (the cap value plus the stage lists it does and does not apply to), because the
concurrent stages run pinned and the timing stages run unpinned, and a run that did not say which
was which would be uninterpretable.

`environment_lock.txt` adds only the **transitive** set — matplotlib, pandas, tqdm and everything
beneath them — which is worth recording but was not worth a commit inside the freeze window. It is
captured at run time, so it describes the environment that actually ran, which a pre-freeze commit
could not. A failed `pip freeze` writes the *reason* in place of the body and does not abort the
run: the lock is supplementary to a manifest that already carries the load-bearing versions, and
adding a pre-flight refusal for it is out of scope.

**Neither file needs anything typed into it. Do not hand-edit either one.**

> Note: at the time this file was frozen, the driver's call site for `experiments/_env_lock.py` is
> being added alongside it in the same freeze. The intended end state described above — the lock
> emitted beside `run_manifest.json` at pre-flight, under the same interpreter — is what the frozen
> driver does. If the two disagree, the driver is authoritative and this paragraph is the defect.

### 1.4 What must be confirmed on the target, and is not in this sha

**The OpenBLAS build behind NumPy.** `pip freeze` names wheels, not the BLAS compiled into them, so
the lock reads it from `numpy.show_config(mode="dicts")` — but *confirming* what that resolves to
on the Linux run machine can only be done there, after the clean clone and the fresh environment
exist.

That confirmation is recorded in the on-target verification plan's own record, **not by editing
this file** — because this file lives inside the frozen sha, and editing anything inside it would
require cutting a new tag. **Tags are never moved.** See §2.7.

### 1.5 Resources

Measured RSS classes for the suite's stages, against the run machine's **31 GiB** of RAM and 32
logical cores:

| Stage class | Measured RSS | At 4 workers | At 5 workers |
|---|---|---:|---:|
| 30-frame stages | < 1 GiB | < 4 GiB | < 5 GiB |
| 100-frame stages | 2.7–3.5 GiB | 10.8–14.0 GiB | 13.5–17.5 GiB |
| 200-frame stages | 9.3–11.3 GiB | — the scheduler permits **at most one in flight** — | |

Worst realistic mix — one 200-frame stage plus the rest at the 100-frame ceiling — is **21.8 GiB at
4 workers** and **25.3 GiB at 5**, against 31.06 GiB total. `SUITE_WORKERS` **4–5 holds**, with 5
the tighter of the two; the driver clamps anything outside that band to 4 and says so.

**Do not re-tune `SUITE_WORKERS`.** A short stage's RSS is a *floor*, not a setting, and the
headroom figure above is an *upper bound*. Swap exists on that machine but is not headroom: a
swapping solver is a stalled run. With 4–5 processes each holding a measured median 0.99 cores
against 32 logical cores, **RAM is the binding resource, not CPU**.

**Disk.** The pre-flight enforces a crude absolute floor of **20 GiB** free
(`preflight.free_space_floor_gib` in `experiments/suite_expectations.json`). The run machine
measured ~662 GiB free on the clone filesystem — 33× the floor. Disk is not a constraint here. The
floor is a discriminator against a pathological state, not an estimate.

### 1.6 How long it takes

**~22-26 h serial at the Windows development box's speed; ~15-16 h with the 4-5 worker pool.**
The critical path is `e6_band` at roughly **8.9 h**, which no amount of pool width shortens — it is
one stage.

> The **~50 h** figure that appears in older planning documents is **superseded and wrong**. Do not
> plan against it, and do not treat a run finishing in ~16 h as evidence that something was skipped.

`e7_band` remains a **stated range** rather than a measurement; a settling probe was offered and
declined. Budget for the upper end.

Runtime is not a number this run is trying to reproduce, with one exception: the E2 timing and
memory stages, which run **serially and BLAS-unpinned** precisely so that what they measure matches
every historical measurement. Do not "optimise" them.

---

## 2. Running the suite

### 2.1 The invocation

From a shell on the Linux run machine **with the frozen run's environment activated** (§1.1 — bare
`python` must resolve to that environment, because ~25 stage invocation lines use it), in the
frozen clone:

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

**Before you read the exit code:** a completed, healthy run exits **non-zero**. The verdict
that judges the run is the end-of-run roll-up, not `$?`. See **§2.8** before concluding
anything from the exit status.

Three things about that command are deliberate:

- **`nohup ... & disown`.** The run is ~15-16 h. It must survive the SSH session ending. A
  foreground run over SSH is a run that dies with the connection.
- **The log lands OUTSIDE the output tree and outside the clone.** Pre-flight refuses to start a
  fresh run into a non-empty output tree that has no state file for this sha, so writing the log
  into `experiments/results/` before launch would trip the driver's own check against you.
- **Unbuffered output is already handled** — every stage invocation line inside the driver is
  `python -u -m experiments.<module>`. Python block-buffers stdout when it is a pipe, and a
  buffered log is indistinguishable between "working normally" and "hung on the first stage".

**The run dirties its own working tree, and that is expected.** `experiments/results/` is a
**tracked** path, so `git status` inside the clone goes dirty as soon as stage 1 writes anything.
There is deliberately **no dirty-tree refusal** in the driver: such a check fires on *resume* and
would refuse every restart after the first crash — a check that kills a run which would otherwise
have succeeded. Dirtiness is still *recorded* post-hoc by the gates, which can never kill a run.
**Do not add a dirty-tree refusal back.**

> **Done, as of plan 27-08 (in this frozen sha).** `E2_RELEASE_CONFIG` now defaults to
> `experiments/configs/e2_release_linux.yaml`, committed inside the frozen sha, with any off-repo
> path reachable only via `SUITE_E2_RELEASE_CONFIG`. The gate interpreter comes from
> `PRELAUNCH_GATE_PYTHON` and fails **loudly, naming that variable**, rather than falling through
> to a bare `python` that does not exist on this machine — and the conda-env-by-name discovery
> rung was **deleted** rather than case-fixed (D-29), because auto-discovery by name was the
> defect. If the driver and this paragraph ever disagree, the driver is authoritative.

### 2.2 Useful environment variables

| Variable | Effect |
|---|---|
| `SUITE_WORKERS=4` | Concurrency width, bounded to 4-5. Anything else is clamped to 4 with a warning. |
| `SUITE_SERIAL=1` | Force the fully serial path (~22-26 h). |
| `SUITE_SMOKE=1` | Equivalent to `--smoke`. |
| `SUITE_OUT_DIR`, `SUITE_STATE_DIR` | Test sandboxing only — not for a production run. |
| `PRELAUNCH_GATE_PYTHON` | Absolute path to the gate/pre-flight interpreter. |
| `SUITE_E2_RELEASE_CONFIG` | Override the E2 release config path. |
| `SUITE_THREAD_CAP=2` | BLAS threads for the CONCURRENT stages (default 2). The four `serial_alone` timing stages are never capped -- every historical measurement was taken unpinned, so capping them would silently change what is being timed. |
| `RUN_EXPERIMENT_SUITE_DRY_RUN=1` | Dry run -- see 2.2.1. Any non-empty value. **Not a `--flag`, and not in `--help`.** |

`SUITE_STAGE_PYTHON` is exported *by* the driver to name the stage interpreter for the run
manifest (D-30). Do not set it yourself; setting it makes the manifest describe an interpreter
the stages did not use.

#### 2.2.1 The dry run

    RUN_EXPERIMENT_SUITE_DRY_RUN=1 bash experiments/run_experiment_suite.sh

Walks all 20 stages, substituting every stage command, so it proves the queue's **wiring** --
stage order, `depends_on` edges, dispatch, state-file handling -- in seconds. It computes
nothing. It writes to a **separate** state file
(`run_experiment_suite_state.<sha>.dryrun.tsv`), so it can never make a real run's stage look
complete; that separation exists because a dry run once did exactly that (2026-08-06).

**A dry run exits 0. A real `--smoke` pass exits NON-ZERO even when healthy (2.8).** Do not read
the dry run's clean exit as evidence that the smoke pass will match it -- they are different
checks with different exit semantics. Verified locally on 2026-08-19: dry run exit 0, 20/20
stages, "SUITE COMPLETE".

### 2.3 Pre-flight, and its five overrides

**Pre-flight is the only place permitted to abort. Nothing aborts once stage 1 has begun** — from
there on, gates *record* and the end-of-run roll-up reports. Every surviving refusal prints the
exact flag that bypasses it, so a malformed check costs one minute and one flag, never a night.

Each flag disables **exactly one** refusal:

| Flag | Declares |
|---|---|
| `--skip-e2` | that the E2 frameset is absent. The run becomes **synthetic-only**, the omission is announced at launch and reprinted in the roll-up, and E2's artifacts still count as missing. |
| `--allow-frameset-mismatch` | proceed although the frameset's identity signature does not match the manifest. |
| `--allow-nonempty-out` | proceed although the output tree is non-empty and no state file exists for this sha. |
| `--allow-low-disk` | proceed although free space is below the manifest's crude absolute floor. |
| `--allow-gate-precheck-failure` | proceed although the completeness gate could not be invoked at pre-flight. |

**`--allow-nonempty-out` is the one flag that can silently cost you the verdict, and it is also
the refusal you are most likely to meet first.** It fired twice during the 2026-08-19 local
acceptance pass. The refusal means the output tree holds artifacts from a run at a *different*
sha, and the completeness gate cannot tell those from this run's — so overriding it makes the
roll-up report another run's artifacts as yours, which is the F-001 shape the roll-up exists to
prevent. **Move the old tree aside instead** (`mv experiments/results_smoke ../aside-<sha>/`);
the flag is for the case where you have already established the leftovers are irrelevant.

The same refusal governs stage sequencing: if you run a single stage into a scratch directory
first (plan 27-13 does this with `fd_jacobian`), that scratch directory must **not** be
`experiments/results_smoke`, or the smoke pass that follows will refuse to start.

Two refusals have **no** override and are not in that table: a run manifest that cannot be written
(every artifact's provenance anchors to it, so a run without one is unreportable), and pre-flight's
own hard failures. Fix the cause and restart from stage 1.

The other options, from the driver's own `--help`:

| Option | Meaning |
|---|---|
| `N`, `--start-stage N` | start from the 1-indexed stage N. **Infrastructure recovery only** — never the recovery path for a `src/` defect, which is always restart-from-stage-1. |
| `--profile {smoke,full}` | expectation profile for the completeness gate. Default `full`. |
| `--remaining-hours H` | **warn**, never abort, if the estimated wall clock exceeds H hours. |
| `--smoke` | the reduced-scale pass. See §2.5. |

### 2.4 Resume

The driver keeps a **state file whose path is derived from the frozen sha**
(`experiments/run_experiment_suite_state.<sha>.tsv`; a dry run writes a separate `.dryrun.tsv`
path). That derivation is what structurally makes another run's state file unreachable — there is
no separate HEAD-vs-state refusal, because that half is what wrongly blocks a 3 a.m. resume.

Re-launch the same command to resume. A stage is skipped only if the state file carries a
`complete` event for it **and that event's exit code is 0**. There are two ways to be incomplete
and **both re-run**:

- a start-only line — the stage started, then died, and never reached a completion line;
- a completion line carrying a **non-zero exit** — the stage **ran and failed**, so it produced
  nothing the roll-up can use.

That second case is the one that matters here: an earlier version matched the completion line and
ignored the exit column, so a crashed-then-resumed run silently dropped the failed stage. On a
single-shot 15-16 h run that is the failure most likely to cost the whole night. The fix makes
resume **stricter, never looser** — no stage that would have re-run before is skipped now.

### 2.5 Declared reductions, and the two never-rehearsed invocation lines

`--smoke` runs every supporting stage at reduced scale in one pass, into its own output tree
(`experiments/results_smoke`), so that a flag typo or an import error in a stage's invocation line
surfaces in minutes rather than hours into the frozen run. **It is not evidence.** It says nothing
about geometry, convergence, accuracy, runtime or any published number. Every acceptance and
production run is at full scale, never substituted.

**Two stages are SKIPPED under `--smoke`, not reduced.** Both are announced at launch and reprinted
in the terminal summary as DECLARED REDUCTIONs:

| Stage | Why it cannot be reduced |
|---|---|
| `e7_focal_standoff` | It has **no `--smoke` branch**. It ignores the flag and reads a **hardcoded, cwd-relative** production path (`experiments/results/interface_ablation_band.csv`) rather than `--out`, so a reduced-scale pass would re-analyse the *production* tree's band. |
| `e4_repeat` | **Both** of its invocation shapes refuse the flag — `e4_benchmark_grid` rejects `--cell` and `--splice-repeat` when `--smoke` is present. There is no reduced-scale form of this stage. |

> ⚠ **The consequence, stated plainly: these two invocation lines are never exercised by any
> rehearsal — including the on-target verification pass. A failure in either of them will first
> appear during the production run.**

That is a deliberate trade: adding `--smoke` branches to them would be freeze-window code changes
for diagnostic-only benefit, which is a worse risk than the one being accepted. **Naming them here
IS the mitigation** — an untested path that nobody wrote down is the exact failure class this
freeze exists to close. If the production run dies, look at these two first.

When one of them fails, it fails *late* (both sit deep in the stage order) and the roll-up will
report their artifacts as missing. That is recoverable: fix, then `--start-stage N` at the failed
stage — this is precisely the infrastructure-recovery case `--start-stage` exists for, provided the
failure is in the invocation line and not in `src/`.

### 2.6 What a green verification does NOT prove

- **Existence and row count are not correctness.** The completeness gate asserts that a file exists
  and, at the `full` profile, that it has the right number of rows. A gauge-corrected column
  populated with uncorrected values passes every one of those checks. Judge the numbers against
  `experiments/EXPECTATIONS.md`; that is what it is for.
- **`--smoke` cannot catch a wrong `--config` path or a bad production YAML.** The reduced-scale
  pass never touches the production config. Pre-flight's **frameset identity check** is the only
  thing covering that blind spot — which is why that check being able to *pass* against the actual
  input set matters so much, and why it was fixed inside this freeze rather than after it.
- **A green cross-artifact sha gate does not prove the code that ran was the frozen code.** It
  proves the *recorded* shas agree. The editable-install hazard in §1.2 produces agreeing shas and
  wrong code. The `import aquacal` assertion is the only thing that covers it.
- **`--smoke` says nothing at all about the two stages in §2.5**, by construction.
- **A non-zero exit code is not a failed run.** The per-stage gates are structurally red;
  only the end-of-run roll-up judges the run. See §2.8.

### 2.7 If something is missing after the package is transferred

The package is supposed to require **no further code edits once transferred**. If it turns out to
need one, that finding sends the freeze **back**, not forward into the run:

1. Fix it here, in the branch.
2. Commit it.
3. Cut the **next** `rerun-freeze-NN` tag at the new sha.
4. Re-verify on the target against that tag.

**Tags are never moved.** A new tag per freeze attempt, each at a distinct sha; abandoned tags stay
as the audit trail. A force-moved tag destroys the record of the failed attempt, which is exactly
the provenance fracture this milestone exists to stop repeating. A second tag is a normal outcome,
not a failure signal.

Do **not** patch the running clone in place and continue. A stage that ran at a different commit
than the rest makes the whole run unreportable, and the sha gate catching it is the system working
— do not weaken it to accommodate the patch.

### 2.8 Reading the exit code: the ROLL-UP is authoritative, not `$?`

**A completed, healthy run exits NON-ZERO. This is expected. Do not treat it as a failed run,
and do not re-run to chase a zero.**

The driver runs `check_rerun_gates.py` at three points (§ the header's "three check points"). The
one that judges the run is the **end-of-run completeness roll-up** over the whole tree. The
per-stage invocations after each stage are *early warnings*, and they are structurally red for two
reasons that have nothing to do with the run's health:

1. **The per-stage gate judges the whole tree, not just its stage.** `--stage` scopes only the
   *completeness* checks; gates 1-4 (guard count, status, provenance, optimality) run the full
   E1/E4/E6/E7 battery over whatever the tree holds at that moment. So `fd_jacobian` at stage 3
   FAILs on E1 and E7 benchmarks that stages 4-18 have not written **yet**. Watch the totals climb
   as the tree fills — on the 2026-08-19 local pass they went 19 PASS at the first gate to 71 PASS
   at the roll-up, with the same artifacts.

2. **The auxiliary trees get the whole battery too.** `e2_band`, `e2_timing`, `e2_memory` and
   `e4_repeat` each write their own output tree holding one stage's output and no run manifest, so
   the E1/E4/E6/E7 gates and `gate3_run_manifest_present` FAIL there by construction. Locally each
   scored `1 PASS / 18 N/A / 28 FAIL`.

Every one of those is recorded as a sticky finding, and any finding forces a non-zero exit. That
is D-01 working as designed (the queue continues; the exit code makes it impossible to mistake for
green) — it is simply not a per-run health signal.

**So, to judge the run:**

```bash
# The verdict that counts -- the LAST verdict block in the log:
awk '/END-OF-RUN COMPLETENESS ROLL-UP/,0' suite_run_<tag>.log | grep -E '^\[FAIL\]|TOTAL:'
```

- **The acceptance condition is `0 FAIL` in that roll-up block**, plus all 20 stages carrying a
  zero exit code in `experiments/run_experiment_suite_state.<sha>.tsv`.
- A `STAGE FAILED` line in the sticky failures file is real and always matters — that is a stage
  that ran and failed, and it is distinct from a `GATE FAIL` line.
- `gate3_run_manifest_clean_tree` FAILing means the working tree was dirty **at launch**. That one
  is real: the recorded `git_sha` then does not fully describe the code that ran. Commit or stash
  before launching. **This is not the same as the run dirtying the tree as it writes results**
  (§2.1) — the manifest is written by pre-flight, before stage 1, so it captures the state at
  launch only. Dirty-at-launch is a defect; dirty-by-writing-results is expected.

This reading was ruled by the author on 2026-08-19 and is recorded in
`.planning/phases/27-frozen-single-sha-handoff-package/27-PREPUSH-AUDIT.md`. The alternative —
scoping gates 1-4 per stage — is a change to the script that judges every artifact, and was
declined inside the freeze window as risk spent on cosmetics rather than on evidence. It is a
reasonable post-submission cleanup.
