---
phase: quick-260813-clj
plan: 01
type: execute
wave: 1
depends_on: []
autonomous: true
requirements: [TODO-PROV-01, TODO-E1BAND-02, TODO-CV-03, TODO-LINUX-04]
files_modified:
  - experiments/prelaunch_gate.sh
  - src/aquacal/io/benchmark.py
  - experiments/README.md
  - .planning/knowledge-base.md
  - experiments/e1_refractive_comparison.py
  - experiments/check_rerun_gates.py
  - tests/unit/test_e1_band_mode.py
  - tests/unit/test_experiments_provenance.py
  - pyproject.toml
  - requirements.txt
  - docs/tutorials/03_cli_walkthrough.md
  - src/aquacal/datasets/loader.py
  - .planning/todos/pending/ -> .planning/todos/done/

must_haves:
  truths:
    - "prelaunch_gate.sh FAILs when the installed aquacal dist-info version differs from pyproject.toml's version, naming both versions and the remedy"
    - "capture_environment() emits an additive aquacal_version_declared field and still never raises"
    - "A --seeds E1 run emits exp1_parameter_band.csv keyed (seed, camera, model) carrying all EXP1_COLUMNS"
    - "A single-seed E1 run emits no exp1_parameter_band.csv"
    - "Both provenance gates accept the new CSV rather than rejecting it as unregistered"
    - "opencv-python is pinned to ==4.13.* in pyproject.toml and requirements.txt"
    - "Every place a real-rig number is claimed reproducible names OpenCV 4.13.0"
    - "experiments/README.md §2 distinguishes results_linux32gb/ (timing/memory, Linux) from results/ (accuracy, Windows)"
    - "The E2_BENCHMARK_PATH aggregator defect is discoverable from the repo, not only from linux32gb_scope.json"
    - "Each of the four todos is moved from .planning/todos/pending/ to .planning/todos/done/ in the same commit as its fix"
  artifacts:
    - path: "experiments/prelaunch_gate.sh"
      provides: "ENV_VERSION_MATCH as check 2, beside LEGALITY_PROBE"
      contains: "ENV_VERSION_MATCH"
    - path: "src/aquacal/io/benchmark.py"
      provides: "aquacal_version_declared in capture_environment()"
      contains: "aquacal_version_declared"
    - path: "experiments/e1_refractive_comparison.py"
      provides: "exp1_parameter_band.csv emission from _run_band"
      contains: "exp1_parameter_band.csv"
  key_links:
    - from: "experiments/e1_refractive_comparison.py::_run_band"
      to: "experiments/results/exp1_parameter_band.csv"
      via: "write_experiment_csv with PARAMETER_BAND_KEY_COLUMNS, force=True"
    - from: "experiments/check_rerun_gates.py::run_all_gates"
      to: "exp1_parameter_band.csv"
      via: "second check_band_csv call beside the existing E1 one"
---

<objective>
Land four independent pre-run todo fixes as four atomic commits, in order A -> B -> C -> D.

Purpose: this is the PREREQUISITE work for an E1 seed-band re-run (`--seeds 42-51`, ~70 min)
that the ORCHESTRATOR will launch afterward. Task A must land first because without it the
re-run would stamp 2.0.1 code with `aquacal_version: 1.8.0` and commit that as the
manuscript's evidence. Task B is what the re-run needs to emit. Tasks C and D are release
hygiene ahead of the 2026-08-21 SoftwareX deadline.

Output: four commits, four todo files relocated from `.planning/todos/pending/` to
`.planning/todos/done/`.
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@./CLAUDE.md
@.claude/rules/code-style.md
@.planning/todos/pending/2026-08-13-editable-install-metadata-can-mislabel-artifact-provenance.md
@.planning/todos/pending/2026-08-13-e1-band-does-not-carry-parameter-level-columns.md
@.planning/todos/pending/2026-08-12-name-the-opencv-version-in-real-rig-reproducibility-claims.md
@.planning/todos/pending/2026-08-12-merge-linux32gb-rerun-branch-to-main.md

READ EACH TODO'S `## Do not` SECTION IN FULL BEFORE TOUCHING ITS FILES. Those sections
encode decisions already made (D-19, D-05, D-260807-dcv, D-19.4-14). They are binding, not
advisory. The per-task `<constraints>` blocks below restate them, but the todo is the source.
</context>

<global_prohibitions>
These apply to EVERY task in this plan. Violating any one fails the plan.

1. **DO NOT run the full test suite.** `pytest tests/` takes 56-88 min, is auto-backgrounded
   past the 600 s tool ceiling, and PERMANENTLY STALLS the executor (CLAUDE.md; three phases
   lost to this). The ORCHESTRATOR runs the full suite at the post-merge gate. Run ONLY the
   targeted commands named in each task's `<verify>`.
2. **DO NOT run `experiments/prelaunch_gate.sh` end to end.** Its check 3, SUITE_GREEN, IS
   the unfiltered full suite. Verify Task A's new check by the isolated commands given, never
   by invoking the script whole.
3. **DO NOT run the E1 `--seeds 42-51` band re-run.** That is ~70 minutes and is the
   ORCHESTRATOR's job after this plan lands. Task B's tests use `--smoke --seeds 42,43`,
   which is what the existing band tests already do.
4. **DO NOT run `pip install -e .` (or `--no-deps`).** The orchestrator does that after
   Task A lands. Task A's new gate check is EXPECTED to FAIL on this box right now
   (pyproject says 2.0.1, the env dist-info says 1.8.0) — that failure is the check working
   correctly, not a bug to chase.
5. **pytest must run under the AquaCal conda interpreter:**
   `$HOME/anaconda3/envs/AquaCal/python.exe -m pytest ...`. Git Bash `python` is Anaconda
   base and produces collection errors that look like test failures.
6. **DO NOT hand-edit the version string or CHANGELOG.** The repo uses
   python-semantic-release. See `<commit_types>`.
7. **DO NOT re-run E2, regenerate any archived number, or retro-edit `aquacal_version` in
   any committed artifact.** All 156 existing artifacts are correct as written.
</global_prohibitions>

<commit_types>
Chosen deliberately, because commit type (not file path) drives python-semantic-release.

| Task | Type | Why |
|---|---|---|
| A | `fix(provenance):` | Touches `src/aquacal/io/benchmark.py` and genuinely repairs a defect (mislabelled provenance). `fix` cuts a PATCH (2.0.2), which is the smallest honest bump. `feat` would cut a minor for what is a repair. |
| B | `chore(experiments):` | `experiments/` and `tests/` only — nothing shipped changes. A `feat:` here would cut a minor for work that alters no installed behavior. Precedent: the linux32gb todo's item 3 explicitly directs non-`src/` work to `chore:`/`docs:`. |
| C | `fix(deps):` | Tightening `opencv-python` to `==4.13.*` changes what every downstream installer resolves — genuinely releasable, and a constraint repair rather than a new capability. The prose edits ride along in the same atomic commit. |
| D | `docs(experiments):` | Documentation only. |

Consequence to state in the SUMMARY, not to act on: with A and C both `fix`, the next push
cuts **v2.0.2**. That is expected and correct. Do not attempt to suppress it, and do not
touch `pyproject.toml`'s `version` field or `CHANGELOG.md`.
</commit_types>

<todo_bookkeeping>
`.planning/todos/` has exactly two subdirectories: `pending/` and `done/` (NOT `completed/`).
Files in `done/` keep the identical `YYYY-MM-DD-slug.md` filename they had in `pending/` —
verified against the existing entries. So the move is a plain `git mv` with no rename:

```bash
git mv .planning/todos/pending/<file>.md .planning/todos/done/<file>.md
```

Do this as part of each task's own commit, so a todo is only marked done in the same commit
that fixes it.
</todo_bookkeeping>

<tasks>

<task type="auto">
  <name>Task A: Gate and record the editable-install version drift (BLOCKER — must land first)</name>
  <files>experiments/prelaunch_gate.sh, src/aquacal/io/benchmark.py, experiments/README.md, .planning/knowledge-base.md, .planning/todos/pending/2026-08-13-editable-install-metadata-can-mislabel-artifact-provenance.md</files>

  <action>
Three layers, one commit.

**A1. `experiments/prelaunch_gate.sh` — add a seventh check, `ENV_VERSION_MATCH`.**

Place it EARLY, immediately beside `LEGALITY_PROBE` (currently check 2, at the
`--- 2. LEGALITY_PROBE ---` banner around line 96), on the reasoning the script already
records there: a seconds-long structural check belongs before the ~60-90 min `SUITE_GREEN`.
Renumber the banner comments and the header block's check list so the numbering stays
contiguous — the header currently enumerates "The six checks:" with `1. TREE_CLEAN`,
`2. LEGALITY_PROBE`, `3. SUITE_GREEN`, `4. HEAD_RECORDED`, `5. ARCHIVES_PRESENT`,
`6. WORKTREES_CLEAN`. Update "six" to "seven" everywhere it appears in that header
(including the "Every one of the six checks below" sentence).

The check must:
- Run under `$PYTHON_BIN` (defined at line 49), NEVER bare `python`, for the reason the
  script already documents in its header ("Git Bash's `python` on this box is Anaconda base,
  not the AquaCal env").
- Mirror the existing interpreter-not-found guard idiom verbatim — see lines 105 and 152:
  `if [ ! -x "$PYTHON_BIN" ] && ! command -v "$PYTHON_BIN" >/dev/null 2>&1; then fail ... else ... fi`,
  with the same parenthetical reason text.
- Read the INSTALLED version via `importlib.metadata.version("aquacal")` under `$PYTHON_BIN`.
- Read the DECLARED version from `pyproject.toml`'s `[project] version` field, parsed with
  `tomllib` (stdlib on the project's >=3.11 floor) — not by grep, which would match the
  wrong `version` key in another table.
- `pass ENV_VERSION_MATCH` when equal; `fail ENV_VERSION_MATCH "..."` when not.
- The FAIL message must print BOTH versions and name the remedy literally:
  `pip install -e . --no-deps`. Model the wording so the abort line is self-servicing —
  a reader must not have to open a todo to know what to do.

Use `$REPO_ROOT/pyproject.toml` (the script already `cd`s to `REPO_ROOT` at line 47).

**A2. `src/aquacal/io/benchmark.py` — additive `aquacal_version_declared`.**

In `capture_environment()` (the `env = {...}` literal begins around line 100; the
`aquacal_version` resolution is the `try` at ~line 114). Add `"aquacal_version_declared": None`
to the initial `env` dict literal, then populate it in ITS OWN `try/except Exception` block
that logs at `logger.debug` on failure, exactly matching the surrounding blocks' style.

Read it from the `pyproject.toml` of the checkout that the function ALREADY locates for
`git_sha`: reuse the same `cwd` expression (`repo_hint_path` if given, else
`_find_git_root(Path(__file__).resolve().parent)`) rather than computing a second root.
Compute `cwd` once and use it for both the pyproject read and the existing `git rev-parse`
call. Parse with `tomllib` (add the import to the stdlib import group). Leave the field
`None` when the file is absent — a pip-installed package outside a checkout is the
documented graceful-degradation case and must behave identically here.

Update the `Returns:` docstring section to describe the new key alongside the existing ones
(Google style, per `.claude/rules/code-style.md`).

**A3. Docs.**
- `experiments/README.md` §7 "Reproducing a number" (heading at line 364): state the
  precondition once, beside the per-experiment commands — a source checkout must have a
  CURRENT editable install, and `pip install -e . --no-deps` is required after any
  `pyproject.toml` version change, or every artifact produced in between is mislabeled.
- `.planning/knowledge-base.md`: add ONE short `###` subsection under the existing
  `## Known Issues & Workarounds` heading (line 81). NOTE: the todo says "alongside 'Commit
  nothing during a production run'" — that rule lives in the user's MEMORY.md, not in
  knowledge-base.md, so place the new entry under Known Issues & Workarounds, which is the
  same genre (a cheap precondition whose violation is invisible in the output). Add the
  matching line to the Table of Contents at line 3 if that ToC enumerates subsections.
  </action>

  <constraints>
- Do NOT make `capture_environment()` raise or abort on mismatch. Its docstring commits to
  "Never raises" (D-05); that decision is deliberate and is NOT overturned here. The gate is
  the thing that stops a run.
- Do NOT hardcode `__version__` as a string literal in `src/aquacal/__init__.py` to dodge
  this. It trades a detectable mismatch for a silent one.
- Do NOT retro-edit `aquacal_version` in any committed artifact.
- Do NOT run `pip install -e .`. The gate SHOULD fail when first run on this box (pyproject
  2.0.1 vs dist-info 1.8.0) — that is correct behavior. The orchestrator fixes the install.
- Do NOT run `experiments/prelaunch_gate.sh` whole (its check 3 is the full suite).
  </constraints>

  <verify>
    <automated>bash -n experiments/prelaunch_gate.sh</automated>
    <automated>$HOME/anaconda3/envs/AquaCal/python.exe -m pytest tests/unit/test_benchmark.py -q</automated>
    <automated>$HOME/anaconda3/envs/AquaCal/python.exe -c "from aquacal.io.benchmark import capture_environment; e=capture_environment(); assert 'aquacal_version_declared' in e; print(e['aquacal_version'], e['aquacal_version_declared'])"</automated>
    <automated>grep -v '^#' experiments/prelaunch_gate.sh | grep -c 'ENV_VERSION_MATCH'</automated>
  </verify>

  <done>
`bash -n` clean. `test_benchmark.py` passes (every existing test asserts a SUBSET of
environment keys — `REQUIRED_ENVIRONMENT_KEYS - set(...)` / `<= set(...)` — so the additive
field is safe by construction; if any test pins an exact key set, STOP and report rather than
loosening the test). The inline `capture_environment()` probe prints two versions and does not
raise. `ENV_VERSION_MATCH` appears in non-comment lines of the gate script (the grep excludes
comments so the header prose cannot self-satisfy the check). Committed as
`fix(provenance): ...` together with the `git mv` of
`2026-08-13-editable-install-metadata-can-mislabel-artifact-provenance.md` into
`.planning/todos/done/`.
  </done>
</task>

<task type="auto">
  <name>Task B: Emit exp1_parameter_band.csv from E1's band mode</name>
  <files>experiments/e1_refractive_comparison.py, experiments/check_rerun_gates.py, tests/unit/test_experiments_provenance.py, tests/unit/test_e1_band_mode.py, .planning/todos/pending/2026-08-13-e1-band-does-not-carry-parameter-level-columns.md</files>

  <action>
**B1. Collect and emit the parameter-level frame.**

`_run_band` in `experiments/e1_refractive_comparison.py` (def at line 743) computes
`_df_exp1, df_exp2, _df_spatial, df_exp3 = _build_dataframes(...)` at ~line 799 and drops
`_df_exp1` on the floor. Collect it instead.

CRITICAL MECHANISM NOTE: `run_seed_band()` in `experiments/_io.py` (def at line 166) returns
ONE concatenated frame and stamps the `seed` column itself. It CANNOT return two frames, and
its signature is shared with E7 — do NOT change it. Instead accumulate the exp1 frames in a
list defined in `_run_band`'s scope and appended to from inside the existing `_runner` closure
(the closure already `nonlocal`s five accumulators; follow that pattern). Because
`run_seed_band` will not stamp these frames, stamp `seed` yourself on each collected frame
before appending, so the resulting concatenation carries a correct `seed` column on every row.

After `band_df = run_seed_band(_runner, seeds)` (line ~813), concatenate the collected exp1
frames (`pd.concat(..., ignore_index=True)`) and write:

- filename: `out_dir / "exp1_parameter_band.csv"`
- key columns: a new module-level constant beside `BAND_KEY_COLUMNS` (line 154), e.g.
  `PARAMETER_BAND_KEY_COLUMNS = ["seed", "camera", "model"]`, with a comment explaining why
  it is a SECOND key shape rather than an extension of `BAND_KEY_COLUMNS` (EXP1 has no depth
  axis).
- column order: `seed` followed by all of `EXP1_COLUMNS` — emit the full set, not just the
  two the manuscript needs; it costs nothing and keeps the per-camera position errors
  available for S-section use.
- `force=True`, matching `exp1_band.csv`'s call at line 817 and its D-19.4-14 comment
  (regenerating a band on demand is the point of it being reproducible).
- written ONLY under `--seeds`, i.e. only inside `_run_band` — no other code path.

Extend `_run_band`'s docstring to name the new artifact alongside `exp1_band.csv`.

**B2. Extend the sidecar `scope` string.**

In the `e1_seed_band_provenance.json` payload (the `"scope"` value at ~line 848), extend the
prose to say the band now ALSO bounds seed-to-seed variance of the parameter-level columns
(`focal_length_error_pct`, `reprojection_rms_px`, and the per-camera position errors) emitted
in `exp1_parameter_band.csv`. KEEP the existing scope qualifier intact and verbatim: it is
still calibration-scenario variance on the `"realistic"` synthetic scenario only, NOT a
physical-rig or real-data claim, and the sidecar must continue to neither assert nor deny an
accuracy claim for E1 (D-19.3-17 already demoted E1's own). Do not weaken or drop those
sentences.

**B3. Register the artifact in BOTH gates that would otherwise reject it.**

- `tests/unit/test_experiments_provenance.py` — the artifact->record mapping dict; the
  `"exp1_band.csv"` entry sits at lines 136-152. Add an `"exp1_parameter_band.csv"` entry
  mirroring that entry's wording: point it at
  `experiments/results/e1_seed_band_provenance.json` as the band-owned sidecar whose
  `solver_config['seeds']` matches this CSV's own seed column, and reuse the existing
  note-shape "previously existed per-seed only in gitignored sweep output" — which describes
  this case verbatim (the columns lived only in `seed_sweep_19_3/e1/seed_*/`, gitignored at
  `.gitignore:254`). Keep the SEEDLESS_LEGACY_RECORDS explanation about the two
  `e1_benchmark_*.json` files.
- `experiments/check_rerun_gates.py` — `check_band_csv` is reusable AS-IS. Add a SECOND call
  immediately beside the existing E1 one (lines 1685-1691), same `"E1"` label, same
  `"e1_benchmark_*.json"` and `band_sidecar="e1_seed_band_provenance.json"`, differing only
  in the CSV name. Do NOT widen `check_band_csv`'s signature.

**B4. Test.**

Add to `tests/unit/test_e1_band_mode.py`, mirroring the `z_rmse_mm` regenerability test
(`test_band_csv_carries_exp3_columns`, line 144) and the negative-assertion pattern
(`TestSingleSeedPathUnaffected`, line 203):

- Positive: `main(["--smoke", "--seeds", "42,43", "--out", str(tmp_path)])`, then assert
  `exp1_parameter_band.csv` exists, that `set(df.columns) >= set(EXP1_COLUMNS)` plus `seed`,
  and that `sorted(df["seed"].unique().tolist()) == [42, 43]` (all requested seeds present).
- Negative: extend or mirror `test_band_mode_does_not_write_single_seed_csvs` /
  `test_non_band_smoke_run_writes_no_band_csv` so a single-seed run asserts
  `not (tmp_path / "exp1_parameter_band.csv").exists()`.
  </action>

  <constraints>
- Do NOT merge EXP1's columns into `exp1_band.csv`, and do NOT widen `merge_band_columns` or
  reindex EXP1 onto the depth axis. The key shapes are incompatible and the result would
  fabricate a depth dependence the parameter errors do not have.
- Do NOT modify `EXP1_COLUMNS`, `EXP2_COLUMNS`, `EXP3_COLUMNS`, `exp1_parameter_errors.csv`,
  or any other single-seed CSV. Those are pinned byte-identical to their committed baselines
  (D-19) and the archive diffs depend on it.
- Do NOT change `run_seed_band`'s shared signature (E7 depends on it).
- Do NOT re-run E1's single-seed production artifacts. Band mode deliberately does not
  overwrite `e1_benchmark_<model>.json`, and that separation is load-bearing (D-260807-dcv).
- Do NOT launch the `--seeds 42-51` re-run (~70 min). That is the orchestrator's.
- Do NOT promote `seed_sweep_19_3/` out of `.gitignore` as a shortcut.
- Do NOT narrate the 0.033% -> 0.054% movement as the refractive model getting worse or as a
  regression anywhere in code comments, docstrings or the SUMMARY. The depth-clearance fix
  corrected the SCENARIO GEOMETRY, not the calibration; the old numbers describe a geometry
  the generator no longer produces.
  </constraints>

  <verify>
    <automated>$HOME/anaconda3/envs/AquaCal/python.exe -m pytest tests/unit/test_e1_band_mode.py -q</automated>
    <automated>$HOME/anaconda3/envs/AquaCal/python.exe -m pytest tests/unit/test_experiments_provenance.py -q</automated>
    <automated>git status --porcelain experiments/results/</automated>
  </verify>

  <done>
Both targeted test files pass, including the two new assertions. `git status --porcelain
experiments/results/` is EMPTY — no committed production artifact moved (the existing
`test_no_results_dir_modified` guard asserts this too; if it reports anything, STOP). Committed
as `chore(experiments): ...` together with the `git mv` of
`2026-08-13-e1-band-does-not-carry-parameter-level-columns.md` into `.planning/todos/done/`.
  </done>
</task>

<task type="auto">
  <name>Task C: Name OpenCV 4.13.0 in reproducibility claims and tighten the pin</name>
  <files>experiments/README.md, docs/tutorials/03_cli_walkthrough.md, src/aquacal/datasets/loader.py, pyproject.toml, requirements.txt, .planning/todos/pending/2026-08-12-name-the-opencv-version-in-real-rig-reproducibility-claims.md</files>

  <action>
**C1. Prose — name OpenCV 4.13.0 wherever a real-rig number is claimed reproducible.**

- `experiments/README.md` §3 "E2 has two invocation paths — read this before citing a
  number" (heading at line 279). Both invocation paths are described there — the Zenodo-archive
  default (line 281) and the `--config` full-frameset path that "reproduces §3 exactly"
  (line 286). State that the reference numbers were produced under **OpenCV 4.13.0**.
- `docs/tutorials/03_cli_walkthrough.md` — THIS is the expected-value table the todo means
  (§3 "Reproduce the paper's numbers", table at lines 94-104; nine reference quantities each
  sourced from `reference_outputs/diagnostics.json`). The `.ipynb` tutorial has no real-rig
  expected-value table — verified: no cell in `01_full_pipeline.ipynb` references `real-rig`,
  `real_rig` or `load_example`, and its single "real-rig" string is incidental output text
  from a synthetic scenario name. Do not edit the notebook.
  In the walkthrough: say which OpenCV produced the expected values (4.13.0), and that a
  different minor version can move them at the ~1-10% level without anything being wrong.
  Also add or amend the Troubleshooting row at line 167 ("Numbers don't match Section 3"),
  which currently attributes a mismatch solely to running the wrong config — OpenCV version
  is now a second, independent cause and the reader cannot currently diagnose it.
- `src/aquacal/datasets/loader.py` — wherever `load_example("real-rig")`'s
  `reference_outputs/` is described as reproducible. The relevant docstrings are around
  lines 19-50 and the `reference_calibration` handling at 65-73. Add the OpenCV 4.13.0
  statement to the docstring that makes the reproducibility claim; if no docstring there
  actually claims reproducibility, say so in the SUMMARY rather than inventing a claim to
  qualify.

Every `benchmark.json` already records `opencv_version` in its `environment` block, so the
machine-readable half is done — this task is only the prose that points at it.

**C2. Pin — THE USER HAS ALREADY DECIDED on the TIGHT pin.**

Set `opencv-python==4.13.*` in BOTH:
- `pyproject.toml` line 32 (currently `"opencv-python>=4.6,<5.0"` inside `dependencies`)
- `requirements.txt` line 10 (currently `opencv-python>=4.6,<5.0`)

**Do not re-litigate the tradeoff, and do NOT substitute the todo's own "middle option"
recommendation (loose runtime pin + a separate pinned reproduction environment).** The todo
records that recommendation; the user overrode it. Implement the tight pin.

**C3. SKIP part 3 of the todo entirely** — the optional `CharucoDetector`-vs-`calibrateCamera`
isolation. It is explicitly not required and affects no attribution and no manuscript claim.
  </action>

  <constraints>
- Do NOT describe either OpenCV version's output as more correct, in any file or in the
  SUMMARY. 450 corners were not detected; nothing measured says which run detected the right
  set.
- Do NOT "fix" the numbers by re-running E2 or updating any archived number. The DOI is
  published; Section 3, `reference_outputs/` and the tutorial table must move together or not
  at all, and the 2026-08-12 manuscript decision is to KEEP the published numbers and NAME the
  environment.
- Do NOT touch the `scipy>=1.16` line or any other dependency while editing those two files.
- Do NOT treat the separate `2026-08-05-pin-opencv-below-5-0` todo as superseded — it stays
  open for its constants-relocation research. Leave it in `pending/`.
  </constraints>

  <verify>
    <automated>grep -c 'opencv-python==4.13' pyproject.toml requirements.txt</automated>
    <automated>$HOME/anaconda3/envs/AquaCal/python.exe -c "import tomllib,pathlib; d=tomllib.loads(pathlib.Path('pyproject.toml').read_text()); assert 'opencv-python==4.13.*' in d['project']['dependencies'], d['project']['dependencies']; print('pin ok')"</automated>
    <automated>grep -c '4\.13' docs/tutorials/03_cli_walkthrough.md experiments/README.md</automated>
  </verify>

  <done>
`pyproject.toml` parses and its `dependencies` list contains `opencv-python==4.13.*`;
`requirements.txt` matches. OpenCV 4.13.0 is named in `experiments/README.md` §3, in the
`03_cli_walkthrough.md` expected-value table plus its troubleshooting row, and in
`loader.py`'s reproducibility claim (or the SUMMARY records that no such claim exists there).
Committed as `fix(deps): ...` together with the `git mv` of
`2026-08-12-name-the-opencv-version-in-real-rig-reproducibility-claims.md` into
`.planning/todos/done/`.
  </done>
</task>

<task type="auto">
  <name>Task D: Document the linux32gb results tree and the E4 aggregator defect</name>
  <files>experiments/README.md, .planning/todos/pending/2026-08-12-merge-linux32gb-rerun-branch-to-main.md, possibly a new file under .planning/todos/pending/</files>

  <action>
The todo's item 1 (merging `experiments/linux32gb-rerun` to `main`) is ALREADY DONE by the
orchestrator — the branch is merged. Do not attempt the merge, and do not run the
`git diff main...experiments/linux32gb-rerun` confirmation it describes. Only items 2 and 4
remain.

**D1. Item 2 — `experiments/README.md` §2 "Provenance table" (heading at line 50).**

Add a line to the provenance table (or to §2's surrounding prose, whichever the table's own
shape makes correct — the table is "one row per artifact committed under
`experiments/results/`", so a sibling TREE may belong in the surrounding prose rather than as
a table row; use judgment and say which you chose in the SUMMARY) distinguishing:

- `results_linux32gb/` — TIMING and MEMORY numbers, measured on 32 GB Linux
- `results/` — ACCURACY numbers, measured on Windows

The point to make legible: the paper's timing numbers and its accuracy numbers come from
DELIBERATELY DIFFERENT trees. `results_linux32gb/` sits beside `results/`, `results_e2_band/`,
`results_e4_repeat/` and `results_e6_repeat2/`, so the sibling convention is established — but
this is the first sibling distinguished by MACHINE rather than by experiment variant, and that
is exactly what needs stating. `linux32gb_scope.json` in that tree is the scope and
confound-control statement; reference it.

**D2. Item 4 — surface the E4 aggregator defect.**

`experiments/e4_benchmark_grid.py:226` hardcodes `E2_BENCHMARK_PATH`, which does NOT follow
`--out`. That is why the Linux `benchmark_grid.csv` carries the nine synthetic cells only and
the real-rig row was dropped — currently worked around by hand. Choose ONE:

(a) note the workaround in `experiments/README.md` (near §2's E4 material), or
(b) file it as its own todo in `.planning/todos/pending/`, following the existing
    `YYYY-MM-DD-slug.md` naming and the frontmatter shape used by the four todos this plan
    closes (`created`, `title`, `area`, `files`), with `## Problem` / `## Solution` sections.

Either is acceptable; (b) is preferable if the fix is more than a sentence to describe. What is
NOT acceptable is leaving it discoverable only from `linux32gb_scope.json`. If you choose (b),
the new todo file is created in the SAME commit.
  </action>

  <constraints>
- Do NOT re-perform or verify the branch merge — it is done.
- Do NOT let semantic-release cut a version off this work: commit type is `docs(...)`. The
  linux32gb todo's item 3 states this requirement explicitly.
- Do NOT modify anything under `experiments/results/` or `experiments/results_linux32gb/`.
- Do NOT fix `e4_benchmark_grid.py` in this task — item 4 asks only that the defect be
  documented or filed, not repaired. Repairing it here would put a `src`-shaped behavior
  change into a docs commit.
  </constraints>

  <verify>
    <automated>grep -c 'results_linux32gb' experiments/README.md</automated>
    <automated>grep -rl 'E2_BENCHMARK_PATH' experiments/README.md .planning/todos/pending/ | head</automated>
    <automated>git status --porcelain experiments/results/ experiments/results_linux32gb/</automated>
  </verify>

  <done>
`experiments/README.md` §2 names `results_linux32gb/` and states the timing-vs-accuracy,
Linux-vs-Windows split. The `E2_BENCHMARK_PATH` defect is present either in the README or as
a new file under `.planning/todos/pending/`. Both results trees are untouched
(`git status --porcelain` empty for them). Committed as `docs(experiments): ...` together with
the `git mv` of `2026-08-12-merge-linux32gb-rerun-branch-to-main.md` into
`.planning/todos/done/`.
  </done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| working tree -> committed provenance artifact | A version string crosses here and is later cited as evidence in a published manuscript |
| pyproject/requirements -> downstream installer | A dependency constraint crosses here and determines what every reader resolves |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-clj-01 | Spoofing | `capture_environment()`'s `aquacal_version` | mitigate | Task A: `ENV_VERSION_MATCH` aborts the queue before a mislabeled artifact can be produced; `aquacal_version_declared` makes an escaped case self-identifying after the fact |
| T-clj-02 | Tampering | committed artifacts under `experiments/results/` | mitigate | Tasks B and D both verify `git status --porcelain experiments/results/` is empty; `test_no_results_dir_modified` asserts it in-suite |
| T-clj-03 | Repudiation | `exp1_parameter_band.csv` without a sidecar link | mitigate | Task B registers it in both gates so its seed column is checked against `solver_config["seeds"]` |
| T-clj-04 | Information disclosure | none — no secrets, no network, no user input | accept | This plan adds no I/O surface |
| T-clj-05 | Denial of service | executor stalls on a backgrounded long run | mitigate | `<global_prohibitions>` 1-3 forbid the full suite, the whole prelaunch gate, and the 70-min band re-run; every `<verify>` command is targeted and finishes well inside the 600 s ceiling |
| T-clj-SC | Tampering | npm/pip/cargo installs | mitigate | No package installs in this plan. `pip install -e .` is explicitly FORBIDDEN to the executor (prohibition 4) and is the orchestrator's step. The `opencv-python==4.13.*` pin in Task C is a constraint edit only — no install is performed |
</threat_model>

<verification>
After all four commits, the following must hold. Run these as a batch at the end; none is
long-running.

```bash
# Four commits, in order, correctly typed
git log --oneline -4

# Four todos moved, none left behind
ls .planning/todos/pending/ | grep -E '2026-08-1[23]' || echo "all four relocated"
ls .planning/todos/done/ | grep -E '2026-08-1[23]'

# Nothing under any results tree moved
git status --porcelain experiments/

# Targeted suites green
$HOME/anaconda3/envs/AquaCal/python.exe -m pytest \
  tests/unit/test_benchmark.py \
  tests/unit/test_e1_band_mode.py \
  tests/unit/test_experiments_provenance.py -q

# Gate script parses
bash -n experiments/prelaunch_gate.sh
```

NOTE on the pending/ check: `2026-08-05-pin-opencv-below-5-0.md` may still be in `pending/`
and MUST stay there — it is not closed by this plan. Only the four named files move.

The full unfiltered suite is NOT part of this verification. The orchestrator runs it at the
post-merge gate.
</verification>

<success_criteria>
- Four atomic commits exist, in order A -> B -> C -> D, typed `fix(provenance)`,
  `chore(experiments)`, `fix(deps)`, `docs(experiments)`.
- `ENV_VERSION_MATCH` is check 2 in `prelaunch_gate.sh`, runs under `$PYTHON_BIN`, prints both
  versions on FAIL and names `pip install -e . --no-deps`.
- `capture_environment()` returns `aquacal_version_declared` and still never raises.
- `--seeds` E1 runs emit `exp1_parameter_band.csv`; single-seed runs do not; both gates accept it.
- `opencv-python==4.13.*` in `pyproject.toml` and `requirements.txt`; OpenCV 4.13.0 named in
  `experiments/README.md` §3, `docs/tutorials/03_cli_walkthrough.md`, and `loader.py`.
- `experiments/README.md` §2 distinguishes `results_linux32gb/` from `results/`; the
  `E2_BENCHMARK_PATH` defect is documented or filed.
- Four todo files relocated to `.planning/todos/done/`, each in its own fix's commit.
- No committed artifact under `experiments/results*/` modified.
- The executor ran no full suite, no whole prelaunch gate, no `pip install`, and no band re-run.
</success_criteria>

<orchestrator_followup>
NOT part of this plan — recorded so no executor attempts it:

1. `pip install -e . --no-deps` in the `AquaCal` env, then confirm
   `python -c "import aquacal; print(aquacal.__version__)"` reports 2.0.1. Task A's new gate
   check will FAIL until this is done; that failure is correct.
2. The full unfiltered `pytest tests/` post-merge gate (56-88 min).
3. The E1 `--seeds 42-51` band re-run (~70 min, detached, `python -u`). Its run notes —
   seed-42 self-check to ~1e-7 relative rather than bit-identity, commit nothing while in
   flight, ignore the sidecar's `seconds` — are in the E1 todo's `## Run notes` section.
</orchestrator_followup>

<output>
Create `.planning/quick/260813-clj-land-four-pre-run-todo-fixes-provenance-/260813-clj-SUMMARY.md` when done.
</output>
