---
created: 2026-08-13T00:00:00.000Z
title: A stale editable install silently stamps the wrong aquacal_version onto every artifact
area: provenance
files:
  - experiments/prelaunch_gate.sh
  - src/aquacal/io/benchmark.py
  - experiments/README.md
  - .planning/knowledge-base.md
---

## Problem

`src/aquacal/__init__.py:5` resolves the version from **installed distribution metadata**:

```python
from importlib.metadata import version as _get_version
__version__ = _get_version("aquacal")
```

`capture_environment()` (`src/aquacal/io/benchmark.py:117`) uses the same source for the
`aquacal_version` field it writes into every `benchmark.json` and every provenance sidecar.

Under an **editable install**, that metadata is written once at `pip install -e .` time and is
never refreshed by editing `pyproject.toml`. So after a version bump the two diverge silently:
the **code** that runs is the current working tree, while the **recorded version** is whatever
was installed months ago.

Measured on the Windows box, 2026-08-13:

| | value |
|---|---|
| `pyproject.toml` | **2.0.1** (bumped 2026-08-11, `2ba0f8e`) |
| `AquaCal` env dist-info | `__editable__.aquacal-1.8.0.pth`, `aquacal-1.8.0.dist-info` |
| `aquacal.__version__` | **1.8.0** |
| `aquacal.__file__` | `C:\Users\tucke\PycharmProjects\AquaCal\src\aquacal\__init__.py` |

The `.pth` resolves imports to the working tree, so **2.0.1 code would be recorded as 1.8.0**.

**Nothing is corrupted yet, and that is the point of filing this now.** All 156 committed
artifacts carrying an `environment.aquacal_version` report `1.8.0`, and none were produced
after the 2026-08-11 bump — the newest file under `experiments/results/` is 2026-08-07. The
defect is **latent**. It would have first realized on the E1 band re-run scheduled by
`2026-08-13-e1-band-does-not-carry-parameter-level-columns.md`, producing a 2.0.1 artifact
labelled 1.8.0 and committed as the manuscript's evidence.

**Why this is worth machinery rather than a note.** `aquacal_version` is not decoration. MF-19
turned on exactly this question — §3's real-rig numbers were traced to a release-era library by
reading provenance records — and MF-20's controlled experiment is stated as "holding OpenCV
fixed, the **1.8.0 -> 2.0.1** library gap is inert." Both arguments are only as good as the
version stamp they rest on. A wrong stamp does not fail loudly; it produces a confident,
plausible, wrong provenance record, and the archive convention
(`experiments/archive/README.md`) instructs readers to trust that field: it directs them to
read the producing commit from "that experiment's own provenance sidecar."

This is also a recurrence of a family the repo has already been bitten by. `prelaunch_gate.sh`
pins its interpreter with the comment "Git Bash's `python` on this box is Anaconda base, not
the AquaCal env" — same root cause, different symptom: the environment that runs is not the
environment assumed.

## Solution

Three layers. (1) is the fix; (2) makes an escaped case self-identifying after the fact; (3)
addresses the step that *causes* the drift.

### 1. Gate it — `experiments/prelaunch_gate.sh` (primary)

Add a seventh check, `ENV_VERSION_MATCH`: assert `importlib.metadata.version("aquacal")` under
`$PYTHON_BIN` equals the `version` field in `pyproject.toml`, and FAIL if not.

This fits the script's stated taxonomy exactly — "a precondition verifiable by a command exit
code is scripted and aborts on failure" — and it is a seconds-long structural check, so place
it **early**, beside `LEGALITY_PROBE`, on the same reasoning already recorded there: catch it
in seconds rather than after an hour of pytest or a 70-minute solve.

Emit the two versions in the FAIL message and name the remedy (`pip install -e . --no-deps`),
so the abort line is self-servicing rather than sending the reader here.

Note the check must run under `$PYTHON_BIN`, not bare `python`, for the reason the script
already documents.

### 2. Record it — `capture_environment()` (secondary)

**Do not make `capture_environment()` raise.** Its docstring commits to "Never raises" (D-05)
so a partial record is always produced rather than aborting the calibration run that requested
it. That decision is correct and should not be overturned to solve this.

Instead, make the record self-describing. Add an **additive** field — e.g.
`aquacal_version_declared` — read from the `pyproject.toml` of the checkout
`_find_git_root()` already locates for `git_sha`, wrapped in its own `try/except` and left
`None` when absent (a pip-installed package outside a checkout is the documented graceful-
degradation case, and behaves identically here). A reader diffing two artifacts can then see
the mismatch instead of inferring it.

**Additive is safe:** every test asserts a **subset** — `REQUIRED_ENVIRONMENT_KEYS - set(...)`
in `test_experiments_provenance.py:351,383,398` and `test_experiments_e5.py:240,267`,
`<= set(...)` in `test_experiments_e6.py:645,655`. No test pins the exact key set. Extending
the environment block additively also has precedent (`solver_config["seeds"]`, D-19.4-14).

Parsing needs `tomllib`, which is stdlib on the project's floor of Python >= 3.11.

### 3. Document it — the step that causes the drift

- **`experiments/README.md` §7 ("Reproducing a number")** — state the precondition once,
  beside the per-experiment commands: a source checkout must have a **current** editable
  install, and `pip install -e . --no-deps` after any `pyproject.toml` version change.
- **The release procedure** — bumping `version` in `pyproject.toml` must be followed by
  reinstalling in the dev env. Without it, every artifact produced between the bump and the
  next reinstall is mislabeled. `.planning/phases/21-.../21-PRE-RELEASE-AUDIT.md` is the
  closest existing release artifact; if a standing checklist is created later, this belongs on
  it.
- **`.planning/knowledge-base.md`** — one line alongside "Commit nothing during a production
  run," which is the same genre of rule: a cheap precondition whose violation is invisible in
  the output.

## Do not

- Do not make `capture_environment()` raise or abort on mismatch. D-05 is deliberate; the
  gate is the place that stops a run.
- Do not switch `__version__` to a hardcoded string in `__init__.py` to dodge this. It trades
  a detectable mismatch for a silent one — the string would then drift from `pyproject.toml`
  with nothing comparing them — and it breaks the single-source-of-truth the packaging
  metadata provides for installed users.
- Do not retro-edit `aquacal_version` in any committed artifact. All 156 are correct as
  written; there is nothing to repair, and hand-editing a provenance record is precisely what
  these records exist to make unnecessary.
- Do not treat this as superseding `2026-08-12-name-the-opencv-version-in-real-rig-
  reproducibility-claims.md`. That one is about which OpenCV a *reader* needs; this one is
  about whether *our own* records say what produced them.
