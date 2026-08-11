---
task: 260811-f81-pre-2-0-0-release-fixes
type: execute
wave: 1
autonomous: true
source_of_truth: .planning/phases/21-new-feature-documentation-dataset-refresh/21-PRE-RELEASE-AUDIT.md
files_modified:
  # Task 1 -- public-API removals
  - src/aquacal/core/refractive_geometry.py
  - src/aquacal/io/serialization.py
  - src/aquacal/validation/__init__.py
  - docs/api/core.rst
  - tests/unit/test_conditioning.py
  - tests/unit/test_serialization.py
  - tests/unit/test_refractive_geometry.py
  # Task 2 -- behaviour fixes
  - src/aquacal/cli.py
  - src/aquacal/calibration/pipeline.py
  - src/aquacal/config/schema.py
  - src/aquacal/datasets/synthetic.py
  - tests/unit/test_cli.py
  - tests/unit/test_pipeline.py
  - tests/unit/test_schema.py
  - tests/unit/test_datasets.py
  - tests/unit/test_synthetic_sweep_axes.py
  # Task 3 -- packaging / metadata
  - pyproject.toml
  - requirements.txt
  - CITATION.cff
  - README.md
  - .readthedocs.yaml
  - .github/workflows/test.yml
  - .gitignore
  - src/aquacal/py.typed
  # Task 4 -- docs / notebooks
  - docs/index.md
  - docs/guide/cli.md
  - docs/guide/optimizer.md
  - docs/guide/benchmarking.md
  - docs/guide/configuration.md
  - docs/guide/refractive_geometry.md
  - docs/guide/troubleshooting.md
  - docs/tutorials/01_full_pipeline.ipynb
  - docs/tutorials/02_synthetic_validation.ipynb
  - experiments/README.md
  - CONTRIBUTING.md

must_haves:
  truths:
    - "pip install aquacal advertises only Python versions where its own dependency floors resolve"
    - "The citation metadata archived at tag v2.0.0 says 2.0.0"
    - "aquacal calibrate -o PATH actually writes to PATH"
    - "A config omitting interface.normal_fixed estimates tilt, matching the docs and the dataclass"
    - "No function signature advertises a parameter it does not use"
    - "sphinx-build -W --keep-going exits 0 with zero warnings after every change"
  artifacts:
    - path: src/aquacal/py.typed
      provides: "PEP 561 marker so downstream type checkers see the annotations"
    - path: tests/unit/test_cli.py
      provides: "regression test pinning -o/--output-dir to the run"
    - path: tests/unit/test_pipeline.py
      provides: "test pinning normal_fixed default to False"
  key_links:
    - from: src/aquacal/cli.py
      to: src/aquacal/calibration/pipeline.py
      via: run_calibration_from_config
      pattern: "run_calibration_from_config\\(config"
    - from: pyproject.toml
      to: CITATION.cff
      via: "semantic-release version_variables"
      pattern: "version_variables"
---

<objective>
Apply the user-selected pre-2.0.0 fixes from the pre-release audit before the first push.

663 commits are unpushed. The push triggers python-semantic-release and cuts **v2.0.0**, so
every fix here ships inside 2.0.0 for free, and anything left undone is either frozen in
published PyPI metadata or costs a compatibility break to correct later.

Purpose: land the fixes whose cost is zero now and non-zero after the tag.
Output: four file-disjoint sets of atomic commits, each independently verified.
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
</execution_context>

<context>
@.planning/phases/21-new-feature-documentation-dataset-refresh/21-PRE-RELEASE-AUDIT.md

The audit is the source of truth for evidence and file:line. Every line number quoted in
this plan was re-verified against the working tree on 2026-08-11 — but re-check a line before
an edit that depends on it, because sibling tasks do not shift each other's files.
</context>

<locked_decisions>
These came from the user. Do not re-litigate, do not offer alternatives, do not "improve" them.

| ID | Decision |
|---|---|
| D-01 | Python 3.10 is DROPPED. `requires-python = ">=3.11"`. |
| D-02 | `interface.normal_fixed` defaults to **`False`** (estimate tilt). The parser is wrong; align it to the docs and the dataclass. |
| D-03 | The legacy `interface_distance` loader shim is **REMOVED**, not deprecated-and-kept. |
| D-04 | The "~50x faster than Brent" claim is **DELETED** in both the docs and the source docstring. No microbenchmark is commissioned. |
| D-05 | MUST-5: **drop** the dead parameter. Do not implement it. |
| D-06 | MUST-6: narrow `__all__`. |
</locked_decisions>

<out_of_scope>
A change touching any of these is wrong. Do not make it, do not "notice and fix it in passing."

- **`src/aquacal/datasets/data/manifest.json`** (MUST-3) — gated on a Zenodo publish still in
  flight. It belongs to plan 21-10.
- **`experiments/results/*`** removals — plan 21-11's job.
- **OPT-1, OPT-2, OPT-3, OPT-4** — orphan file and log deletions, skipped by decision.
- **`pyproject.toml` `[project].version`** and **`CHANGELOG.md`** — semantic-release owns both.
  Never hand-edit them. (`CITATION.cff:version` IS hand-set here; see Task 3.)
- **SH-16** (`docs/tutorials/index.md:26-27`) — **VERIFY ONLY, DO NOT EDIT.** §3 was updated to
  current-library numbers earlier today and the archive now reproduces it, so the claim may now
  be TRUE. The audit's framing of it is stale. Report whether the two lines read accurately as of
  today; take no action on them.
- **`.claude/worktrees/`**, **`build/lib/`**, **`docs/_build/`**, **`docs/tutorials/.ipynb_checkpoints/`**,
  **`experiments/archive/`** — all contain copies of files edited here. They are build output,
  stale worktrees and frozen history. Never edit a match found in them. Filter every repo-wide
  grep with `grep -v -e '/\.claude/' -e '^build/' -e 'docs/_build/' -e '\.ipynb_checkpoints/'`.
</out_of_scope>

<hard_constraints>
Violating any of these has previously cost this project hours. They are not style preferences.

1. **DO NOT run the full pytest suite.** Unfiltered `pytest tests/` measured 56 and 88 minutes.
   Each task below states its own targeted command. Run only that. The orchestrator runs the
   unfiltered suite at the post-merge gate.

2. **Never background a long run and end your turn.** A subagent that backgrounds a command and
   returns "waiting for the notification" has stalled permanently — for a subagent, ending the
   turn IS completion, so the notification can never arrive. Every command in this plan completes
   inline. If a command you chose looks like it will exceed ~8 minutes, narrow it (fewer test
   files, `-m "not slow"`, `-k` selection) rather than backgrounding it.

3. **`export PYTHONPATH="$(pwd)/src"` before any python or pytest invocation.** A worktree's
   editable install resolves to `main`'s code, so without this you test the wrong tree.

4. **pytest needs the AquaCal conda environment.** Git Bash `python` is Anaconda base. Collection
   errors are an interpreter problem, not a code problem — fix the interpreter, do not "fix" the
   test.

5. **Sphinx is the acceptance gate for every docs and shim change.** It currently exits 0 with
   ZERO warnings and must still exit 0 after:
   ```
   SCRATCH=$(mktemp -d)
   sphinx-build -W --keep-going -b html docs "$SCRATCH/html"
   ```
   Build to a scratch dir. **NEVER build to `docs/_build/`** — that directory already holds a
   previous build whose stale doctrees will mask a real failure.

6. **Notebook edits must preserve valid JSON and must NOT execute cells.** Edit the source-cell
   strings in place. Verify with `python -m json.tool <nb> > /dev/null`. `nbsphinx_execute` is
   `"never"`, so nothing regenerates outputs — do not try.

7. **Atomic commits per logical fix.** Not one giant commit per task.

8. **Breaking-change commits carry a `BREAKING CHANGE:` footer** so they land in the CHANGELOG
   honestly. Do **not** add a `!` to the commit type — a major is already guaranteed by the
   existing `feat!:` at `d406001`, and manufacturing another is noise.
</hard_constraints>

<file_ownership>
The four tasks are file-disjoint and may run in parallel. Three fixes are deliberately **split
across two tasks**. Each half is real work. If you own one half, do not assume the other task
did yours, and do not reach across into the other task's file.

| Fix | Source half (owner) | Docs half (owner) |
|---|---|---|
| UNV-1 — the ~50x claim | `refractive_geometry.py:825` (**Task 1**) | `docs/guide/refractive_geometry.md:103` (**Task 4**) |
| SH-6 — `calibration.yaml` | `schema.py:155` docstring (**Task 2**) | `docs/index.md:55` (**Task 4**) |
| MUST-8 — the three shims | `refractive_geometry.py` + `docs/api/core.rst` (**Task 1**); `pipeline.py` `initial_distances` (**Task 2**) | — |

`docs/api/core.rst` is the one file under `docs/` that belongs to **Task 1**, not Task 4. It is
there because of a hard coupling (see Task 1). Task 4 must not touch it.
</file_ownership>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: Remove the deprecated shims, the undeclared legacy loader, and the unmeasured speed claim</name>

  <files>
src/aquacal/core/refractive_geometry.py
src/aquacal/io/serialization.py
src/aquacal/validation/__init__.py
docs/api/core.rst
tests/unit/test_conditioning.py
tests/unit/test_serialization.py
tests/unit/test_refractive_geometry.py
  </files>

  <behavior>
    - `aquacal.core.refractive_geometry.refractive_project_fast` no longer exists (AttributeError on access).
    - `aquacal.core.refractive_geometry.refractive_project_fast_batch` no longer exists.
    - `_deserialize_camera_calibration` on a dict carrying only `interface_distance` raises
      `ValueError`, and the message names only `water_z` — it must not advertise the removed field.
    - `_deserialize_camera_calibration` on a dict carrying `water_z` is unchanged.
    - `"compute_conditioning" not in aquacal.validation.__all__`, and likewise for
      `ConditioningReport`, `ConditioningMemoryError`, `load_conditioning_report`,
      `save_conditioning_report`.
    - `from aquacal.validation import compute_conditioning` still succeeds (the names stay
      importable; only the advertised surface narrows).
  </behavior>

  <action>
**MUST-8 — remove the two `refractive_geometry` shims (D-03 family).**
Delete `refractive_project_fast` (`refractive_geometry.py:921`) and
`refractive_project_fast_batch` (`:945`), together with the `# Deprecated backward-compatibility
shims` comment banner above them. Neither is in any `__all__`. There are no deprecation tests —
`grep -rin 'deprecat\|initial_distances\|refractive_project_fast' tests/` returns zero matches.

**MUST-8 coupling — this is the one that breaks the build if you miss it.**
`docs/api/core.rst:17` is `.. autofunction:: aquacal.core.refractive_geometry.refractive_project_fast`.
It MUST be deleted in the SAME commit as the shim, or `sphinx-build -W` fails on an autodoc
import error. Delete that directive line and the blank line that follows it. Leave
`refractive_project` (`:13`) and `refractive_project_batch` (`:15`) alone. This is the only
reference to either shim anywhere outside the definitions — verified repo-wide.

**UNV-1 (source half) — delete the ~50x claim per D-04.**
`refractive_geometry.py:825` reads:
`- Flat interface (normal ≈ [0,0,-1]): Newton-Raphson (2-4 iterations, ~50x faster)`
Drop the `, ~50x faster` clause; keep the iteration-count statement, which is observable. There is
no measurement anywhere in the repo backing the number, and it must not be conflated with E1's
97-178x band, which measures something else entirely. The docs half of this fix
(`docs/guide/refractive_geometry.md:103`) belongs to Task 4 — do not edit it.

**SH-1 — remove the undeclared legacy `interface_distance` loader (D-03).**
`serialization.py:88-101`, `_deserialize_camera_calibration`. Collapse the three-branch
`water_z` / `interface_distance` / raise block down to a `water_z`-only read, and rewrite the
`ValueError` message at `:101` so it names only `water_z`. Right now the error message itself
advertises the legacy field to users. Also drop the "Supports backward compatibility: accepts both
'water_z' (new) and 'interface_distance' (legacy)" sentence from the docstring.

Known consequence, to record in the commit footer rather than work around: any
`calibration.json` written by AquaCal <= v1.5 will now fail to load. The one such file present
locally, `docs/tutorials/aquacal_data/real-rig/real-rig/reference_calibration.json` (13
occurrences of `interface_distance`), is **untracked and gitignored** — it is download cache from
the superseded Zenodo archive, not repo content. Do not edit it, do not delete it, and do not let
it block you.

**MUST-6 — narrow `aquacal.validation.__all__` (D-06).**
Remove these five entries from `validation/__init__.py:29-34`'s `__all__`, along with the
`# conditioning` comment: `ConditioningMemoryError`, `ConditioningReport`, `compute_conditioning`,
`load_conditioning_report`, `save_conditioning_report`. Their own docstrings
(`conditioning.py:64`, `:196`, `:250`) each say "Experimental -- return shape may change", and
`docs/api/validation.rst` does not document them, so nothing external was being invited in.

**Keep the `from aquacal.validation.conditioning import (...)` block at `:8-14`.** Removing the
names from `__all__` de-advertises them; removing the imports would break
`from aquacal.validation import compute_conditioning`, which is a real break for no gain. Ruff's
F401 fires on an `__init__.py` import that is no longer re-exported via `__all__`, so add
`# noqa: F401` to that import block and confirm with `ruff check`.

**Update `tests/unit/test_conditioning.py::test_public_exports` (`:167-177`) — it WILL fail
otherwise.** It currently asserts `"compute_conditioning" in validation_module.__all__` and the
same for `ConditioningReport` and `save_conditioning_report`. Invert those three assertions to
`not in`, keep the `public_compute_conditioning is compute_conditioning` identity assertion
(importability is still guaranteed), and rename the test to reflect what it now pins — something
like `test_conditioning_is_importable_but_not_advertised`. Add a one-line comment recording that
the narrowing was deliberate and pre-2.0.0.

Only internal consumers exist and none goes through the package `__all__`:
`_observability.py:657-662`, `pipeline.py:64,1406`, `experiments/e7_interface_ablation.py`. They
import from `aquacal.validation.conditioning` directly and are unaffected.

**Tests to add** in `tests/unit/test_refractive_geometry.py` and `tests/unit/test_serialization.py`
respectively: assert the two shim names are absent from the module, and assert the
`interface_distance`-only payload now raises `ValueError` with a message that does not mention
`interface_distance`.

**Commits** (atomic, in this order):
1. `refactor(core): remove deprecated refractive_project_fast shims` — + `BREAKING CHANGE:` footer.
   Includes the `docs/api/core.rst` directive removal and the shim-absence test.
2. `docs(core): drop the unmeasured ~50x-faster-than-Brent claim from refractive_project`
3. `refactor(io): drop legacy interface_distance field from calibration loading` — + `BREAKING CHANGE:` footer.
4. `refactor(validation): narrow __all__ to exclude experimental conditioning API` — + `BREAKING CHANGE:` footer.
  </action>

  <verify>
    <automated>export PYTHONPATH="$(pwd)/src" && python -m pytest tests/unit/test_refractive_geometry.py tests/unit/test_serialization.py tests/unit/test_conditioning.py tests/unit/test_validation.py -q</automated>
    <automated>ruff check src/aquacal/validation/__init__.py src/aquacal/io/serialization.py src/aquacal/core/refractive_geometry.py</automated>
    <automated>SCRATCH=$(mktemp -d) && sphinx-build -W --keep-going -b html docs "$SCRATCH/html" &amp;&amp; echo SPHINX_OK</automated>
    <automated>export PYTHONPATH="$(pwd)/src" && python -c "import aquacal.core.refractive_geometry as m; assert not hasattr(m,'refractive_project_fast'); assert not hasattr(m,'refractive_project_fast_batch'); import aquacal.validation as v; assert 'compute_conditioning' not in v.__all__; from aquacal.validation import compute_conditioning; print('OK')"</automated>
  </verify>

  <done>
Both `refractive_project_fast*` shims gone; `docs/api/core.rst` has no directive referencing them;
sphinx `-W` still exits 0 with zero warnings; the legacy `interface_distance` read path is gone
and its error message no longer names the field; five conditioning names are out of
`aquacal.validation.__all__` but still importable; `test_public_exports` updated rather than
deleted; four atomic commits, three carrying `BREAKING CHANGE:` footers and none adding a new `!`.
  </done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: Fix the ignored --output-dir flag, the inverted normal_fixed default, and the dead trajectory parameter</name>

  <files>
src/aquacal/cli.py
src/aquacal/calibration/pipeline.py
src/aquacal/config/schema.py
src/aquacal/datasets/synthetic.py
tests/unit/test_cli.py
tests/unit/test_pipeline.py
tests/unit/test_schema.py
tests/unit/test_datasets.py
tests/unit/test_synthetic_sweep_axes.py
  </files>

  <behavior>
    - `aquacal calibrate config.yaml -o some/dir` runs with `config.output_dir == some/dir`.
      Pin this by asserting the object handed to `run_calibration_from_config` carries the
      overridden `output_dir` (patch the pipeline entry point; do not run a real calibration).
    - Parsing a YAML config whose `interface:` block omits `normal_fixed` yields
      `CalibrationConfig.interface_normal_fixed is False`.
    - Parsing a YAML config with `normal_fixed: true` still yields `True`.
    - `inspect.signature(generate_board_trajectory).parameters` does not contain
      `min_cameras_per_frame`.
    - `CalibrationConfig.min_cameras_per_frame` still exists and still defaults to `2`.
  </behavior>

  <action>
**MUST-4 — `-o/--output-dir` is silently ignored.**
`cli.py:163-164` sets `config.output_dir` on the in-memory object. `cli.py:190` then calls
`run_calibration(config_path, verbose=args.verbose)`, which takes a **path** and re-reads the YAML
from disk (`pipeline.py:595`), so the override never reaches the run. Change `cli.py:190` to
`run_calibration_from_config(config, verbose=args.verbose)` (`pipeline.py:772`, signature
`(config: CalibrationConfig, verbose: bool = False) -> CalibrationResult`) and update the import at
the top of `cli.py` accordingly. Leave `run_calibration` itself in place — it is the public
path-taking entry point and other callers use it.

This is ranked MUST-FIX because `--dry-run` at `cli.py:179-185` prints "Output will be saved to
{config.output_dir}" using the overridden value, so validating with `--dry-run -o out/` actively
*confirms* an override that will not happen; and the docs instruct readers to use the flag in three
places (`docs/guide/cli.md:25`, `docs/tutorials/03_cli_walkthrough.md:85` and `:170`). **Those docs
are correct — the code is wrong. Do not edit the docs.** After this fix all three read true.

Add the regression test to `tests/unit/test_cli.py`: monkeypatch
`aquacal.cli.run_calibration_from_config` with a spy, invoke the calibrate command with `-o`, and
assert the captured config's `output_dir` matches. Do not invoke a real calibration.

**MUST-7 — `normal_fixed` three-way default disagreement (D-02).**
`pipeline.py:274` reads `normal_fixed = interface.get("normal_fixed", True)`. Both
`schema.py:333` (`interface_normal_fixed: bool = False`) and `docs/guide/configuration.md:95`
(documented default `false`) say otherwise. Today a config that omits the key gets tilt estimation
**silently disabled**. Change the parser default to `False`. The docs and the dataclass are already
right; leave both alone.

Add the pinning test to `tests/unit/test_pipeline.py` alongside the existing config-parsing tests
(see `:165` and `:240` for the established pattern): parse a config with no `normal_fixed` key and
assert `interface_normal_fixed is False`; parse one with `normal_fixed: true` and assert `True`.

Unaffected by design: `cli.py:583` (`aquacal init`) writes `normal_fixed: false` explicitly, and
the published archive's `config_paper.yaml` sets it explicitly too, so §3 and the Zenodo reference
outputs do not move.

**MUST-8 (third shim) — remove the `initial_distances` config shim.**
`pipeline.py:282-296`: the `if "initial_distances" in interface:` branch, its `warnings.warn`, and
the scalar/dict handling beneath it. Zero dependents; the in-tree config
`docs/tutorials/aquacal_data/real-rig/real-rig/config.yaml:72` uses `initial_water_z`. Keep the
`initial_water_z` branch untouched. If `warnings` becomes an unused import in `pipeline.py`, check
before removing it — the module uses `warnings` elsewhere.

**MUST-5 — drop the dead `min_cameras_per_frame` parameter (D-05).**

:::{warning}
**Read this before touching anything named `min_cameras_per_frame`. The audit's original text
conflated two different things and an executor that follows it will damage live code.**

`CalibrationConfig.min_cameras_per_frame` (`schema.py:337`, documented `schema.py:233`) is a
**DIFFERENT, LIVE field**. It performs real frame filtering at `pipeline.py:912` and `:954`, and
`pipeline.py:462` merely constructs the config from the YAML key `detection.min_cameras`.
**Do not touch `schema.py:337`, `schema.py:233`, `pipeline.py:462`, `pipeline.py:912`,
`pipeline.py:954`, `tests/unit/test_schema.py:233`, `tests/unit/test_pipeline.py:165`,
`tests/unit/test_pipeline.py:240`, `docs/guide/configuration.md:180`, or any YAML
`detection.min_cameras` key.** All of those are correct and must survive unchanged.

The dead parameter is **only** `generate_board_trajectory`'s own.
:::

Delete `min_cameras_per_frame: int = 2` from the `generate_board_trajectory` signature
(`synthetic.py:513`). It is referenced zero times in the body (AST scan including nested defs). Then
remove its two docstring promises: the bullet `- Each frame is visible by at least
min_cameras_per_frame cameras` (`:522`) and the Args entry `min_cameras_per_frame: Minimum cameras
that must see board` (`:582`). Rewrite the surrounding docstring so it no longer claims a
connectivity guarantee the function does not provide — this parameter is the sole basis for that
claim, and 19.2 already recorded the mismatch as a live trap.

Locked pre-2.0.0 because the release freezes this public signature, the same one Phase 19.3 already
made breaking by requiring `board`. Per D-05 the parameter is dropped, not implemented:
implementing the filter would silently change generated trajectories for every existing seed and
invalidate the manuscript's seed bands.

**Caller sweep — the actual result differs from the audit's expectation.** Re-run this before
editing, then again after:
```
grep -rn "min_cameras_per_frame" --include=*.py . \
  | grep -v -e '/\.claude/' -e '^\./build/' -e '\.ipynb_checkpoints/'
```
As verified on 2026-08-11, **no caller anywhere passes it by keyword** — not the two in-library
callers (`synthetic.py:1075`, `:1117`), not any test in `tests/unit/test_datasets.py` or
`tests/unit/test_synthetic_sweep_axes.py`, not `experiments/e4_benchmark_grid.py:689`, not
`experiments/fd_jacobian_accuracy.py:362`. Also note `tests/unit/test_datasets.py:855`'s frozen
historical `_pre_d27_generate_board_trajectory` does **not** carry the parameter — leave that
reimplementation exactly as it is, it is a frozen RNG-stream reference. So the deletion should be
signature + docstring only. **If the post-edit grep shows a remaining keyword caller, fix that
caller; do not restore the parameter.**

Two textual references stay, because they describe history rather than call the function:
`experiments/e4_benchmark_grid.py:786` and `docs`-adjacent prose in `experiments/README.md`. The
`e4_benchmark_grid.py` docstring at `:786` says the parameter is "accepted but not enforced" —
that sentence becomes false. `e4_benchmark_grid.py` is not owned by any task in this plan; note it
in your SUMMARY as a follow-up rather than editing it.

Add to `tests/unit/test_datasets.py` (near the existing signature test at `:473`, which uses
`inspect.signature(generate_camera_array)` — follow that pattern): assert
`"min_cameras_per_frame" not in inspect.signature(generate_board_trajectory).parameters`.

**SH-6 (source half) — `schema.py:155` autodoc'd docstring loads a file the pipeline never writes.**
The example reads `>>> save_calibration(result, "output/calibration.yaml")`. The pipeline writes
`calibration.json` (`pipeline.py:1758`) and `load_calibration` is JSON-only
(`serialization.py:253-258`). Change the extension to `.json`. Because this docstring is autodoc'd,
this edit is in `src/`, not docs. The docs half (`docs/index.md:55`) belongs to Task 4.

**SH-14 — docstrings advertise dataset names that raise.**
`_manifest.py:39` and `download.py:133` reference `small`/`medium`/`large`; only `real-rig` exists,
so those names raise `ValueError`. Replace the examples with `'real-rig'`. *(These two files are
not in this task's declared file list — add them to your commit and note the addition; they are
touched by no other task, so there is no collision risk.)*

**Commits** (atomic):
1. `fix(cli): honour -o/--output-dir by running from the in-memory config` (+ test)
2. `fix(config): default interface.normal_fixed to false, matching docs and dataclass` (+ test) — + `BREAKING CHANGE:` footer (a behaviour change for configs omitting the key)
3. `refactor(config): drop deprecated initial_distances config field` — + `BREAKING CHANGE:` footer
4. `refactor(datasets): drop unused min_cameras_per_frame from generate_board_trajectory` (+ test) — + `BREAKING CHANGE:` footer
5. `docs(datasets): correct dataset names and calibration filename in docstrings`
  </action>

  <verify>
    <automated>export PYTHONPATH="$(pwd)/src" && python -m pytest tests/unit/test_cli.py tests/unit/test_schema.py tests/unit/test_synthetic_sweep_axes.py -q</automated>
    <automated>export PYTHONPATH="$(pwd)/src" && python -m pytest tests/unit/test_datasets.py tests/unit/test_datasets_pipelines.py -q -m "not slow"</automated>
    <automated>export PYTHONPATH="$(pwd)/src" && python -m pytest tests/unit/test_pipeline.py -q -m "not slow"</automated>
    <automated>export PYTHONPATH="$(pwd)/src" && python -c "import inspect; from aquacal.datasets import generate_board_trajectory as g; assert 'min_cameras_per_frame' not in inspect.signature(g).parameters; from aquacal.config.schema import CalibrationConfig as C; import dataclasses; assert [f for f in dataclasses.fields(C) if f.name=='min_cameras_per_frame'][0].default == 2; print('OK')"</automated>
    <automated>ruff check src/aquacal/cli.py src/aquacal/calibration/pipeline.py src/aquacal/config/schema.py src/aquacal/datasets/synthetic.py</automated>
    <automated>SCRATCH=$(mktemp -d) && sphinx-build -W --keep-going -b html docs "$SCRATCH/html" &amp;&amp; echo SPHINX_OK</automated>
  </verify>

  <done>
`cli.py` calls `run_calibration_from_config(config, ...)` and a test pins the `-o` override;
the YAML parser defaults `normal_fixed` to `False` and a test pins it; the `initial_distances`
branch is gone; `generate_board_trajectory` no longer declares `min_cameras_per_frame` and a
signature test pins that; `CalibrationConfig.min_cameras_per_frame` and every one of its
five live call sites are untouched; sphinx `-W` still exits 0 with zero warnings.
  </done>
</task>

<task type="auto">
  <name>Task 3: Packaging and citation metadata</name>

  <files>
pyproject.toml
requirements.txt
CITATION.cff
README.md
.readthedocs.yaml
.github/workflows/test.yml
.gitignore
src/aquacal/py.typed
  </files>

  <action>
**Reminder: never hand-edit `pyproject.toml`'s `[project] version = "1.8.0"` (line 7). Never touch
`CHANGELOG.md`.** semantic-release owns both. `CITATION.cff:version` IS hand-set here, deliberately
— see MUST-2.

**MUST-1 — drop Python 3.10 (D-01).**
`pyproject.toml:10` declares `requires-python = ">=3.10"` while `:32` pins `scipy>=1.16`, and
scipy 1.16.0 itself requires `>=3.11` (fetched live from PyPI 2026-08-11). `pip install aquacal`
therefore cannot resolve on 3.10, and publishing 2.0.0 bakes that false claim into PyPI metadata
that cannot be edited afterwards. numpy 2.4 and pandas 3.0 have the same floor, so 3.10 support is
fictional in practice.

Four edits:
- `pyproject.toml:10` → `requires-python = ">=3.11"`
- `pyproject.toml:26` → delete the `"Programming Language :: Python :: 3.10"` classifier. Leave
  3.11 and 3.12. Consider adding `3.13` only if you can confirm the dependency set supports it —
  otherwise leave the list as 3.11/3.12; an unverified classifier is the same class of defect this
  fix exists to remove.
- `.readthedocs.yaml:6` → `python: "3.11"`. It currently pins 3.10, so the docs site advertised at
  `pyproject.toml:66` cannot build at all.
- `.github/workflows/test.yml:16` → drop `"3.10"` from the matrix, leaving
  `["3.11", "3.12"]`. Those 3.10 jobs' `pip install -e ".[dev]"` must currently fail.

**OPT-7 (falls out of MUST-1) — `requirements.txt` duplicates the dependency list.** It already
mirrors `pyproject.toml` and its header names pyproject as authoritative. Confirm the two lists
still agree after your edit; no version-floor change is needed there, but if you change any floor
in `pyproject.toml` you must mirror it.

**MUST-2 — citation metadata will otherwise ship 2.0.0 saying 1.7.0.**
This is locked because GitHub's citation widget and the Zenodo GitHub-release integration read
`CITATION.cff` **at the tag**. The archived citation for v2.0.0 would be permanently wrong, which
matters directly for the SoftwareX submission.

Three parts, all required:
1. `CITATION.cff:18` → `version: 2.0.0`. `README.md:62` → `version = {2.0.0}`.
2. Add to the `[tool.semantic_release]` block (`pyproject.toml:121-126`, which currently has
   `version_toml = ["pyproject.toml:project.version"]` **only**):
   ```
   version_variables = ["CITATION.cff:version"]
   ```
   This is the durable half. Without it the file goes stale again at 2.0.1. Setting the value by
   hand as well is belt-and-braces: if the regex fails to match, we still ship 2.0.0 rather than
   1.7.0.
3. `CITATION.cff:19` → `date-released:` currently `"2026-07-15"`. semantic-release does not
   maintain this field. Set it to today's date (`2026-08-11`) and **state in your SUMMARY that the
   orchestrator must re-check it if the push slips past that date** — it is the one value here that
   silently rots on the calendar.

**`CITATION.cff:17` `doi:` — verify before changing, do not guess.**
It currently reads `doi: "10.5281/zenodo.18644658"`. Whether this is stale depends on whether it is
a **concept DOI** (always resolves to the newest version, so correct and permanent) or a **version
DOI** (pinned to one release, so wrong from 2.0.0 onward). Open `https://doi.org/10.5281/zenodo.18644658`
and read the record's "Versions" panel:
- If it is the concept DOI (the page shows "all versions" / lists multiple versions under it) →
  **leave it unchanged** and say so in your SUMMARY.
- If it is a version DOI → replace it with the concept DOI shown on that page.
- If the page is ambiguous or unreachable → **change nothing** and escalate in your SUMMARY as a
  blocking pre-push item. Do not guess a DOI.

Note for context: `18644658` is the *software* record. `18645385`, which appears in the phase-21
plans, is the *dataset* record and is a different thing — do not substitute one for the other.

**SH-15 — add the `py.typed` marker.**
Create an empty `src/aquacal/py.typed`. Then extend `[tool.setuptools.package-data]`
(`pyproject.toml:76-79`), which currently lists only `"datasets/data/**/*.json"`, to also include
`"py.typed"`. Without the package-data entry the marker will not ship in the wheel and the fix is
inert. Every annotation in the package is currently invisible to downstream mypy/pyright; a major
release is the natural moment. Verify by building and inspecting the wheel namelist (command
below).

**SH-17 — `Development Status :: 4 - Beta` on a 2.0.0.**
`pyproject.toml:19` → `"Development Status :: 5 - Production/Stable"`. Publishing a 2.0.0 as Beta
is a metadata claim readers act on.

**SH-7 — `aquacal_data/` has no `.gitignore` rule.**
`git check-ignore -v aquacal_data` exits 1. `download.py:24` sets
`cache_dir = Path.cwd() / "aquacal_data"`, so the cache lands wherever the user runs from. The only
current guard is a nested `docs/tutorials/aquacal_data/.gitignore` containing `*` — which **ignores
itself**, is therefore untracked, and does not survive a clone. That directory is currently 354 MB
including a copy of the archive zip. Append to `.gitignore`, with a brief comment explaining the
self-ignoring-nested-file problem:
```
# Dataset download cache (download.py writes to <cwd>/aquacal_data). The nested
# aquacal_data/.gitignore ignores itself, so it is untracked and does not survive a clone.
aquacal_data/
```
A bare `aquacal_data/` pattern matches at any depth, covering `docs/tutorials/aquacal_data/` too.
Verify both paths afterwards with `git check-ignore -v`.

**Commits** (atomic):
1. `build: require Python >=3.11 and drop 3.10 from CI and RTD` — + `BREAKING CHANGE:` footer
2. `build: maintain CITATION.cff version via semantic-release and set 2.0.0`
3. `build: ship py.typed marker for PEP 561 type-checker support`
4. `build: mark project Production/Stable for 2.0.0`
5. `chore: ignore the aquacal_data download cache`
  </action>

  <verify>
    <automated>python -c "import tomllib,pathlib; d=tomllib.loads(pathlib.Path('pyproject.toml').read_text()); assert d['project']['requires-python']=='>=3.11'; assert not any('3.10' in c for c in d['project']['classifiers']); assert 'Production/Stable' in ' '.join(d['project']['classifiers']); assert d['tool']['semantic_release']['version_variables']==['CITATION.cff:version']; print('OK')"</automated>
    <automated>python -c "import yaml,pathlib; c=yaml.safe_load(pathlib.Path('CITATION.cff').read_text()); assert str(c['version'])=='2.0.0', c['version']; print('OK', c['doi'], c['date-released'])"</automated>
    <automated>grep -q 'version = {2.0.0}' README.md && echo README_OK</automated>
    <automated>python -c "import yaml,pathlib; d=yaml.safe_load(pathlib.Path('.readthedocs.yaml').read_text()); assert d['build']['tools']['python']=='3.11'; w=yaml.safe_load(pathlib.Path('.github/workflows/test.yml').read_text()); assert '3.10' not in [str(v) for v in w['jobs']['test']['strategy']['matrix']['python-version']]; print('OK')"</automated>
    <automated>git check-ignore -v aquacal_data docs/tutorials/aquacal_data && echo IGNORE_OK</automated>
    <automated>rm -rf dist build/lib && python -m build -q &amp;&amp; python -c "import zipfile,glob; n=zipfile.ZipFile(glob.glob('dist/*.whl')[0]).namelist(); assert 'aquacal/py.typed' in n, n; assert 'aquacal/datasets/data/manifest.json' in n; print('WHEEL_OK')"</automated>
  </verify>

  <done>
`requires-python` is `>=3.11` with matching classifiers, RTD config and CI matrix; `CITATION.cff`
says `version: 2.0.0` with a current `date-released`, and `version_variables` keeps it that way;
the `doi:` field was verified against the live record and either left correct or corrected, never
guessed; `README.md` BibTeX says 2.0.0; `py.typed` exists AND is present in the built wheel;
the project is classified Production/Stable; `aquacal_data/` is ignored at every depth;
`pyproject.toml:project.version` and `CHANGELOG.md` are untouched.
  </done>
</task>

<task type="auto">
  <name>Task 4: Documentation and notebook corrections</name>

  <files>
docs/index.md
docs/guide/cli.md
docs/guide/optimizer.md
docs/guide/benchmarking.md
docs/guide/configuration.md
docs/guide/refractive_geometry.md
docs/guide/troubleshooting.md
docs/tutorials/01_full_pipeline.ipynb
docs/tutorials/02_synthetic_validation.ipynb
experiments/README.md
CONTRIBUTING.md
  </files>

  <action>
**Do not touch `docs/api/core.rst` — it belongs to Task 1** (it is coupled to a shim removal).
Do not touch `docs/tutorials/index.md` — see SH-16 below, verify only.
Do not touch `docs/tutorials/03_cli_walkthrough.md` — corrected earlier today, and its `-o` flag
advice becomes true once Task 2 lands.

**UNV-1 (docs half) — delete the ~50x claim (D-04).**
`docs/guide/refractive_geometry.md:103`: "This Newton-Raphson approach is **~50x faster** than
bracketing methods like Brent's method, while maintaining excellent numerical stability."
No measurement backing this exists anywhere in the repo; no experiment times Newton against Brent.
It must **not** be conflated with E1's 97-178x band, which measures something else entirely.
Rewrite to keep the stability claim and drop the number — e.g. "This Newton-Raphson approach
converges in 2-4 iterations for flat interfaces and avoids the bracketing search Brent's method
requires, while maintaining excellent numerical stability." The source half
(`refractive_geometry.py:825`) belongs to Task 1.

**SH-6 (docs half) — `docs/index.md:55` loads a file that is never written.**
`calib = load_calibration("output/calibration.yaml")`. The pipeline writes `calibration.json`
(`pipeline.py:1758`) and `load_calibration` is JSON-only (`serialization.py:253-258`), so the
landing page's first code sample fails for anyone who runs it. Change to `.json`. The autodoc'd
twin at `schema.py:155` belongs to Task 2.

**SH-2 — `docs/guide/optimizer.md` documents two mechanisms that were deliberately removed.**
- `optimizer.md:132` — "**Board tvec[2]** (Z-coordinate): Must be greater than water_z (boards are
  underwater)". False: `_optim_common.py:563-575` bounds only tilt, water_z and intrinsics;
  board-pose columns stay ±inf.
- `optimizer.md:144` — "**Boundary penalties**: Soft constraint to keep board Z > water_z pushes
  water_z downward". False: `_optim_common.py:56-61` states verbatim "No extra above-interface
  penalty term is added."

These describe the design that was **rejected for a specific reason** — a hinge there would destroy
the first-order-optimality diagnostic. Do not merely delete the two lines; state what the code
actually does and why, citing `_optim_common.py:56-61`. In the "water_z is unobservable in
non-refractive mode" admonition, the numbered list at `:143-146` gives boundary penalties as cause
1 of water_z drift; with that mechanism gone, only cause 2 (numerical noise in a flat cost valley)
survives, so rewrite the list rather than leaving a dangling "1.".

**SH-13 — `optimizer.md:222` misdescribes `dense_threshold` by orders of magnitude.**
Documented as "For very large problems (e.g., 1000+ parameters)"; the real trigger is
`n_residuals x n_params > 5e8` (`_optim_common.py:725, 756-757`). Correct it to the actual product
threshold.

**OPT-11 (optimizer.md, cosmetic — in scope only because you are already in the file):**
`optimizer.md:280` cites a line range in the fisheye branch rather than the simplification loop at
`intrinsics.py:451-462`; `optimizer.md:333` says "Stage 2-4" for a three-stage pipeline. Fix both.
Re-verify `intrinsics.py:451-462` before quoting it.

**SH-3 — every `aquacal compare` output filename in `docs/guide/cli.md` is wrong.**
`cli.md:137-144` against `validation/comparison.py`:

| Documented | Actual | Source |
|---|---|---|
| `metrics.csv` | `metrics_summary.csv` | `comparison.py:335` |
| `per_camera.csv` | `per_camera_metrics.csv` | `:342` |
| `depth_error_plot.png` | `depth_error_comparison.png` | `:393` |
| `depth_binned.csv` | `depth_binned_errors.csv` | `:439` |

Also add the undocumented `xy_error_heatmaps.png` (`:431`). Verify each filename against
`comparison.py` as you go rather than trusting this table — this is the same defect class corrected
in the CLI walkthrough today, and the guide page was missed. Leave `parameter_diffs.csv`,
`rms_bar_chart.png`, `position_overlay.png` and `z_position_dumbbell.png` alone unless the source
disagrees.

**OPT-11 (cli.md, cosmetic):** `cli.md:175` sample output shows `aquacal 0.1.0`. Update it to
match what `aquacal --version` will print at 2.0.0.

**Do NOT edit `cli.md:25`** (the `-o/--output-dir` row). It is correct; Task 2 is fixing the code
to match it.

**SH-4 — `docs/guide/benchmarking.md:16-17` claims a flag does not exist.**
"Written unconditionally to `output_dir/benchmark.json` at the end of every
`run_calibration_from_config` invocation — there is no config flag to disable it." False:
`pipeline.py:1763` guards the write with `if config.save_benchmark:`, parsed at `pipeline.py:443`.
Rewrite to name the flag and its default.

**OPT-11 (benchmarking.md, cosmetic):** `:289` points readers at `.planning/`, which does not ship
in either the wheel or the sdist. Remove or re-target the pointer.

**SH-5 — `configuration.md:241-245` omits `save_benchmark` and `benchmark_memory`.**
Both are parsed (`pipeline.py:443-444`, `schema.py:363-364`). Add two rows to the internals table
in the same style as the existing `save_stage_calibrations` / `save_optimization_trace` /
`save_conditioning` rows, reading the real defaults off `schema.py:363-364`. `benchmark_memory`
matters: it is the only switch for the per-stage memory block that `benchmarking.md:163-194`
documents at length, so cross-link it the way the neighbouring rows cross-link.

**Do NOT edit `configuration.md:95`** (the `normal_fixed` row) — it is already correct and Task 2
is fixing the parser to match it. **Do NOT edit `configuration.md:180`** (the
`detection.min_cameras` row) — that documents a live field; see Task 2's warning block.

**UNV-3 (editorial, optional):** `configuration.md` carries "v1.7/v1.8" version framing. Rewrite it
for a 2.0.0 only where it is plainly wrong; do not restructure the page.

**`docs/guide/troubleshooting.md`:**
- **OPT-11:** `:190-191` carries mislabelled parameter counts. Re-derive them from
  `_optim_common.py`'s packing before rewriting; if you cannot derive them confidently, leave them
  and note it rather than substituting a guess.
- `:112` uses `interface_distance` to name a **physical quantity** ("Each camera's
  `interface_distance` equals `water_z - C_z`"), not the removed config/JSON field. Task 1's removal
  does not make this false, but the collision is confusing now that the field is gone. Reword to
  "camera-to-interface distance" and drop the code formatting. Same call for
  `docs/guide/glossary.md:59`, which already frames it as an older superseded term — **that file is
  not in your list; note it in your SUMMARY as a follow-up rather than editing it.**

**SH-8 — `experiments/README.md` under-qualifies two downstream paths.**
`:68` (`figures/aquacal/synthetic_validation.py`) and `:74` (`figures/aquacal/zenodo_e2e.py`) read
as repo-relative, but no `figures/` directory exists here. Sibling rows `:90` and `:92` give the
same class of path fully qualified as
`DissertationFigures/src/dissertationfigures/figures/aquacal/` — a **different repository**. These
are not missing files; they are ambiguous references. Qualify both to match the sibling rows. The
ditto marks at `:69`, `:70`, `:71`, `:75`, `:76` inherit the corrected cell, so **2 edits fix 7
rows** — do not expand the dittos.

**SH-9 — `experiments/README.md` omits 4 of 11 experiment scripts.**
Missing from the map: `e7_focal_standoff_analysis.py`, `reconstruction_bootstrap.py`,
`check_rerun_gates.py` (all three have tests — `tests/unit/test_e7_focal_standoff.py`,
`test_reconstruction_bootstrap.py`, `test_rerun_gates.py` — so they are live code the repo's own map
does not point at) and `fd_jacobian_accuracy.py` (the genuine orphan: no README row, **no test
file**, referenced only from `19.5-02-PLAN.md`). Add rows for all four. Mark
`fd_jacobian_accuracy.py` explicitly as a one-off diagnostic with no test coverage and no paper
artifact rather than implying parity with the E-series.

**SH-10 — `02_synthetic_validation.ipynb` imports from `tests/`, making the tutorial unrunnable
from a `pip install`.**
Cell 4 imports 3 names from `tests.synthetic.experiment_helpers` (`calibrate_synthetic`,
`compute_per_camera_errors`, `evaluate_reconstruction`) and 6 from `tests.synthetic.ground_truth`
(`SyntheticScenario`, `create_scenario`, `generate_dense_xy_grid`, `generate_real_rig_array`,
`generate_real_rig_trajectory`, `generate_synthetic_detections`).

:::{warning}
**The audit says all nine names are public. Eight are. `generate_real_rig_trajectory` is NOT** —
verified 2026-08-11: it is defined at `src/aquacal/datasets/synthetic.py:648` but is absent from both
the import block and the `__all__` of `src/aquacal/datasets/__init__.py`.
:::

So: repoint the eight public names to a single `from aquacal.datasets import (...)`. For the ninth,
**do not add it to `datasets/__init__.py`** — that file belongs to no task in this plan and adding a
public export is a 2.0.0 API decision, not a docs fix. Instead keep `generate_real_rig_trajectory`
on its existing `tests.synthetic.ground_truth` import, leave the `sys.path` bootstrap at `:138-143`
in place to support it, and **flag it in your SUMMARY as a blocking pre-push question**: either
export it from `aquacal.datasets` (small, additive, free before 2.0.0) or the notebook keeps
needing a full clone. Say plainly that the "unrunnable from pip install" defect is only ~90% closed
by this task.

Consequently cell 1's Colab comment at `:50-51` ("This notebook imports test helpers from the
repo's `tests/` directory, so a full clone is needed") stays **true** until that question is
settled — update it to name the single remaining reason rather than deleting it.

**SH-11 — notebook Colab badges point at the wrong repository.**
`01_full_pipeline.ipynb:9`, `02_synthetic_validation.ipynb:10` and `:59` reference
`tlancaster6/AquaCal`. The canonical repo is `McGrathLab/AquaCal` (`CITATION.cff:8`,
`pyproject.toml:65`). Replace all three, including the `git clone` URL at `02:59`.

**SH-12 — `01_full_pipeline.ipynb` cell 22 uses a key the parser ignores.**
Line 714 says "Provide better `initial_water_zs` in config" — plural. `pipeline.py:340` reads only
`initial_water_z`. Silently ignored. Fix to the singular.

**OPT-11 (notebooks, cosmetic):** mojibake em dashes at `01_full_pipeline.ipynb:51,55,542,618`, and
orphan "Exported Data" sections in both notebooks. Fix the mojibake; for the orphan sections, remove
them only if they reference outputs no cell produces — verify before deleting.

**Notebook editing rules (constraint 6):** edit the source-cell strings in place, preserve valid
JSON, execute nothing. Validate each file after editing with
`python -m json.tool <nb> > /dev/null`. Do not reformat unrelated JSON — keep the diff to the lines
you changed.

**OPT-11 (`CONTRIBUTING.md`, cosmetic):** `:129-131` is a misnumbered list. Fix the numbering only.

**SH-16 — VERIFY ONLY, NO EDIT.**
Read `docs/tutorials/index.md:26-27` and report in your SUMMARY whether its claim that Tutorial 03
reproduces §3 now reads accurately. §3 was updated to current-library numbers earlier today and the
archive now reproduces it, so the claim may have become TRUE — the audit's framing (which cites
MF-19) predates that. **Do not edit the file** regardless of what you find. State your reading and
stop.

**Commits** (atomic, grouped by subject):
1. `docs(guide): correct optimizer bounds, penalties and dense_threshold description`
2. `docs(guide): correct aquacal compare output filenames`
3. `docs(guide): document save_benchmark and benchmark_memory, correct benchmark.json claim`
4. `docs: drop the unmeasured ~50x speed claim and fix the calibration.json example`
5. `docs(experiments): qualify DissertationFigures paths and add the four missing scripts`
6. `docs(tutorials): repoint notebook imports to the public API and fix Colab badges`
7. `docs: cosmetic corrections (version strings, mojibake, list numbering)`
  </action>

  <verify>
    <automated>python -m json.tool docs/tutorials/01_full_pipeline.ipynb > /dev/null &amp;&amp; python -m json.tool docs/tutorials/02_synthetic_validation.ipynb > /dev/null &amp;&amp; echo JSON_OK</automated>
    <automated>SCRATCH=$(mktemp -d) && sphinx-build -W --keep-going -b html docs "$SCRATCH/html" &amp;&amp; echo SPHINX_OK</automated>
    <automated>! grep -rn "tlancaster6" docs/tutorials/*.ipynb &amp;&amp; echo BADGE_OK</automated>
    <automated>! grep -rn "50×\|~50x faster" docs/guide/refractive_geometry.md &amp;&amp; echo CLAIM_OK</automated>
    <automated>! grep -n "calibration.yaml" docs/index.md &amp;&amp; echo INDEX_OK</automated>
    <automated>! grep -n "initial_water_zs" docs/tutorials/01_full_pipeline.ipynb &amp;&amp; echo NB_KEY_OK</automated>
    <automated>for f in e7_focal_standoff_analysis reconstruction_bootstrap check_rerun_gates fd_jacobian_accuracy; do grep -q "$f" experiments/README.md || { echo "MISSING $f"; exit 1; }; done; echo README_OK</automated>
    <automated>git diff --name-only -- docs/api/core.rst docs/tutorials/index.md docs/tutorials/03_cli_walkthrough.md | grep . &amp;&amp; { echo "ERROR: touched an out-of-scope file"; exit 1; } || echo SCOPE_OK</automated>
  </verify>

  <done>
Every SH docs finding corrected against re-verified source line numbers; `docs/api/core.rst`,
`docs/tutorials/index.md` and `03_cli_walkthrough.md` untouched; both notebooks are valid JSON with
unexecuted cells and no `tlancaster6` references; SH-16 reported on and not edited; the
`generate_real_rig_trajectory` gap escalated in the SUMMARY as a pre-push question; sphinx `-W`
exits 0 with zero warnings.
  </done>
</task>

</tasks>

<orchestrator_only>
These are the orchestrator's, not an executor's. Do not dispatch them.

1. **Post-merge full suite.** After merging all four tasks, run the single unfiltered
   `python -m pytest tests/` from the merged tree. Auto-backgrounding is harmless here. This is the
   only place cross-task breakage is visible — an executor's targeted run cannot see the other three
   tasks. Expect 56-88 minutes.
2. **Post-merge sphinx gate.** Rebuild to a scratch dir from the merged tree. Task 1 removes a
   shim and Task 4 rewrites pages that reference the same subsystem; only the merged build proves
   the `-W` gate is still clean.
3. **Post-merge wheel build.** `python -m build` and re-inspect the namelist. Confirm `py.typed`
   present, `datasets/data/manifest.json` present, and still zero stray inclusions (no `.planning/`,
   tests, experiments, `aquacal_data/`, logs, `__pycache__`).
4. **Verify executor claims against git, never against return text.** For each task:
   `git log --oneline <base>..<branch>`, `git -C <worktree> status --porcelain` (catches
   finished-but-uncommitted work that dies with the worktree), and check the SUMMARY exists.
5. **Collect the three escalations** before authorising the push:
   - Task 3: the `CITATION.cff` `doi:` verdict (concept vs version DOI) and the `date-released`
     value if the push slips past 2026-08-11.
   - Task 4: whether to export `generate_real_rig_trajectory` from `aquacal.datasets` — additive and
     free before 2.0.0, a new public export afterwards.
   - Task 4: the SH-16 reading of `docs/tutorials/index.md:26-27`.
6. **Still blocking the push, owned elsewhere:** MUST-3 (`manifest.json`, plan 21-10, gated on the
   Zenodo publish) and the `experiments/results/*` removals (plan 21-11). This plan does not clear
   the release checklist on its own.
7. **Noted follow-ups from executors, owned by no task here:**
   `experiments/e4_benchmark_grid.py:786` (a docstring that becomes false once MUST-5 lands) and
   `docs/guide/glossary.md:59` (`interface_distance` as a superseded term).
</orchestrator_only>

<success_criteria>
- All four tasks merged; the unfiltered `pytest tests/` passes on the merged tree.
- `sphinx-build -W --keep-going` exits 0 with zero warnings on the merged tree, built to a scratch
  directory.
- `python -m build` produces a wheel containing `aquacal/py.typed` and `aquacal/datasets/data/manifest.json`,
  with zero stray inclusions.
- `pyproject.toml:project.version` and `CHANGELOG.md` are byte-identical to the pre-task state.
- `git diff --stat` shows no change under `src/aquacal/datasets/data/`, `experiments/results*/`,
  `docs/tutorials/index.md`, or `docs/tutorials/03_cli_walkthrough.md`.
- Commit history is atomic per logical fix, with `BREAKING CHANGE:` footers on the removals and the
  `normal_fixed` default change, and no newly introduced `!` commit type.
- The three escalations from `<orchestrator_only>` item 5 are answered before the push.
</success_criteria>

<output>
Each executor writes `.planning/quick/260811-f81-pre-2-0-0-release-fixes/SUMMARY-task-N.md` recording:
what changed, the commit SHAs, the targeted test command it ran and the result, the sphinx result,
and any escalation or follow-up it is handing back.
</output>
