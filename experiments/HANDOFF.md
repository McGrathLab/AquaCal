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
python -m pip install -e .
```

which resolves `pyproject.toml`'s runtime dependencies:

| Dependency | Constraint | Note |
|---|---|---|
| `opencv-python` | **`==4.13.*`** | **Hard pin. Do not relax it.** See below. |
| `scipy` | `>=1.16` | floor only |
| `numpy` | unpinned | deliberately — see below |
| `pyyaml`, `matplotlib`, `pandas`, `requests`, `tqdm` | unpinned | |
| `natsort` | `>=8.4.0` | |

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
require cutting a new tag. **Tags are never moved.** See §2.6.

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
