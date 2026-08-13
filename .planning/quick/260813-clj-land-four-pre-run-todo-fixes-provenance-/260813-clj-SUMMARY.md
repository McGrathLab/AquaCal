---
phase: quick-260813-clj
plan: 01
subsystem: provenance, experiments, packaging
tags: [provenance, band-artifact, opencv-pin, release-hygiene]
requires:
  - AquaCal conda env (Python 3.12.12, OpenCV 4.13.0, NumPy 2.4.2, SciPy 1.17.0)
provides:
  - ENV_VERSION_MATCH prelaunch gate check
  - environment.aquacal_version_declared in every benchmark record
  - exp1_parameter_band.csv emission from E1 band mode
  - opencv-python==4.13.* pin
affects:
  - the orchestrator's E1 --seeds 42-51 re-run (needs `pip install -e . --no-deps` first)
tech-stack:
  added: []
  patterns:
    - "tomllib for declared-version reads (stdlib on the >=3.11 floor, never grep)"
    - "a second band key shape rather than widening an incompatible one"
key-files:
  created:
    - .planning/todos/pending/2026-08-13-e4-aggregator-hardcodes-e2-benchmark-path.md
  modified:
    - experiments/prelaunch_gate.sh
    - src/aquacal/io/benchmark.py
    - experiments/e1_refractive_comparison.py
    - experiments/check_rerun_gates.py
    - tests/unit/test_e1_band_mode.py
    - tests/unit/test_experiments_provenance.py
    - pyproject.toml
    - requirements.txt
    - docs/tutorials/03_cli_walkthrough.md
    - src/aquacal/datasets/loader.py
    - experiments/README.md
    - .planning/knowledge-base.md
decisions:
  - "ENV_VERSION_MATCH placed as check 2, ahead of LEGALITY_PROBE, because the probe imports the very library this check validates"
  - "exp1_parameter_band.csv registered in CSV_TO_RECORD ahead of its artifact, guarded by a new self-expiring PENDING_CSVS allowance"
  - "E4 aggregator defect filed as its own todo (option b) rather than described in the README alone"
metrics:
  duration: ~2h10m (35 min of it a single test file)
  completed: 2026-08-13
---

# Quick Task 260813-clj: Land Four Pre-Run Todo Fixes Summary

Four atomic commits landing the prerequisites for the E1 seed-band re-run: a gate that
catches a stale editable install before it mislabels an artifact, the band artifact the
re-run needs to emit, an OpenCV pin with the prose that explains it, and the
`results_linux32gb/` tree made legible.

## Commits

| # | Commit | Type | Task |
|---|---|---|---|
| A | `25e65c0` | `fix(provenance)` | Gate and record editable-install version drift |
| B | `5ae6683` | `chore(experiments)` | Emit `exp1_parameter_band.csv` from E1's band mode |
| C | `fa9ec3a` | `fix(deps)` | Pin opencv-python to 4.13.* and name it in reproduction claims |
| D | `3eb1f4a` | `docs(experiments)` | Distinguish `results_linux32gb/`, file the E4 aggregator defect |

Base was `ade98c2`. Two `fix:` commits are in the set, so **the next push cuts v2.0.2**.
That is expected and correct; nothing here touched `pyproject.toml`'s `version` field or
`CHANGELOG.md`.

## Task A — the version-drift gate

`ENV_VERSION_MATCH` is check **2** of seven in `experiments/prelaunch_gate.sh`. It runs under
`$PYTHON_BIN` with the existing interpreter-not-found guard idiom copied verbatim, reads the
installed version via `importlib.metadata.version("aquacal")` and the declared one from
`$REPO_ROOT/pyproject.toml` with `tomllib`, and on FAIL prints both versions and names
`pip install -e . --no-deps` in the abort line itself.

**Placement deviates slightly from the plan's prose and matches its success criterion.** The
plan's action text said "immediately beside `LEGALITY_PROBE` (currently check 2)" while its
`<success_criteria>` said "ENV_VERSION_MATCH is check 2". I made it check 2 and shifted
LEGALITY_PROBE to 3, on the reasoning that the probe imports `experiments.check_rerun_gates`
and thus the library whose install this check validates — so validating the install first is
the correct order, not merely an acceptable one. That reasoning is recorded in the script.
All banners and the header's check list renumbered; "six" → "seven" throughout.

`capture_environment()` gained `aquacal_version_declared`, populated in its own
`try/except Exception` logging at `logger.debug`. The `cwd` expression was hoisted so the
pyproject read and the existing `git rev-parse` use **one** repo root — an artifact must not
describe two checkouts. `Path(None)` on a no-checkout box raises inside the `try` and
degrades to `None`, matching the documented graceful-degradation case. The function still
never raises (D-05 stands).

### The gate FAILS on this box, and that is the point

Verified in isolation (never by running the script whole — its check 4 is the full suite):

```
installed (dist-info): 1.8.0
declared (pyproject):  2.0.1
exit=1
```

`capture_environment()` reports the same pair. This is the latent defect the todo was filed
for: 2.0.1 code would have been stamped `aquacal_version: 1.8.0` on the E1 re-run and
committed as the manuscript's evidence. Not "fixed" by reinstalling — that is the
orchestrator's step (prohibition 3) — and the check was not weakened to make it pass.

## Task B — `exp1_parameter_band.csv`

`_run_band` now collects each seed's EXP1 frame into a list in its own scope, appended to
from inside the existing `_runner` closure and stamped with `seed` there, because
`run_seed_band` returns one concatenated frame and its signature is shared with E7. Written
as `exp1_parameter_band.csv`, keyed by a new `PARAMETER_BAND_KEY_COLUMNS = ["seed",
"camera", "model"]` — a **second** key shape, commented as such, since EXP1 has no depth
axis — carrying `seed` plus all of `EXP1_COLUMNS`, `force=True`, under `--seeds` only.

Sidecar `scope` extended to name the parameter-level columns; the synthetic-scenario-only
qualifier and the D-19.3-17 non-claim sentence are intact and verbatim. Registered in both
gates: a second `check_band_csv` call in `check_rerun_gates.py` (signature untouched) and a
`CSV_TO_RECORD` entry mirroring `exp1_band.csv`'s wording, including the literal span
`seeds 42-51` the seed-coverage gate requires.

`EXP1_COLUMNS`, `EXP2_COLUMNS`, `EXP3_COLUMNS` and every single-seed CSV are untouched.

### Deviation: `PENDING_CSVS` (Rule 3 — blocking issue)

Registering the CSV before its artifact exists trips
`test_csv_to_record_has_no_stale_entries`, which asserts every map key names a file on disk.
The artifact only arrives with the orchestrator's ~70 min re-run, and it cannot arrive first
because an unregistered CSV fails `test_all_committed_csvs_have_a_named_record` the moment it
appears — the gate's own failure would sit between the run and its commit.

Resolved with an explicit per-file `PENDING_CSVS = frozenset({"exp1_parameter_band.csv"})`,
subtracted only in the stale-entry test, plus a new `test_pending_csvs_are_still_pending`
that **fails as soon as the file lands**, forcing the exemption's removal. The removed-CSV
case the stale test exists for still fails for every other filename. This is narrower than
loosening the assertion and it is self-expiring, but it is a real (small) weakening of one
guard for one file for one run, so it is flagged here rather than buried.

**Orchestrator action:** after the re-run commits `exp1_parameter_band.csv`, delete
`PENDING_CSVS`'s single entry (the new test will tell you).

Nothing here narrates the 0.033% → 0.054% movement as a regression; it is not mentioned
outside this sentence saying it is not mentioned.

## Task C — OpenCV 4.13.0

`opencv-python==4.13.*` in `pyproject.toml` (with a comment recording the controlled
experiment behind it) and `requirements.txt`. The tight pin was implemented as the user
decided; the todo's own "middle option" recommendation was **not** substituted. `scipy>=1.16`
and every other dependency untouched. `2026-08-05-pin-opencv-below-5-0.md` left in
`pending/`.

Prose: `experiments/README.md` §3 (covering both E2 invocation paths),
`docs/tutorials/03_cli_walkthrough.md`'s expected-value table plus a **new** troubleshooting
row for "close but off by ~1–10% with the right config" — the case the existing row, which
blames the wrong config alone, cannot diagnose. Part 3 of the todo (the CharucoDetector
isolation) skipped as directed. The notebook was not edited.

**Reporting as instructed:** `src/aquacal/datasets/loader.py` contained **no pre-existing
reproducibility claim** to qualify — `load_example`'s docstring describes downloading and
caching, and `reference_outputs` appears nowhere under `src/`. Rather than invent a claim, I
added a `Note:` qualifying the artifact the function hands back: the archive's
`reference_outputs/` were produced under OpenCV 4.13.0 and a different minor can move a
comparison at the ~1–10% level. If that is more than intended, it is one docstring block and
trivially removable.

No file describes either OpenCV version's output as more correct.

## Task D — `results_linux32gb/` and the E4 aggregator

Placed in §2's **surrounding prose**, not as a table row — the table is explicitly "one row
per artifact committed under `experiments/results/`", and a sibling *tree* is not an artifact
of that tree. The paragraph states the timing/memory-on-Linux vs accuracy-on-Windows split,
names `linux32gb_scope.json` as the scope statement to read first, and makes the point that
this sibling is distinguished by **machine** rather than by experiment variant, so its rows
must not be diffed against the table's as repeats.

The `E2_BENCHMARK_PATH` defect took **option (b)** — its own todo at
`.planning/todos/pending/2026-08-13-e4-aggregator-hardcodes-e2-benchmark-path.md` — because
the fix is more than a sentence: it needs an explicit non-silent fallback. The sharper form
of the defect is not the dropped row but its inverse: an `--out` run *can* silently pair one
machine's synthetic cells with another machine's real-rig row whenever
`experiments/results/benchmark.json` happens to exist. The README names the defect and points
at the todo, so it is discoverable from both. `e4_benchmark_grid.py` was not modified.

The merge was not re-performed or verified; it was already done.

## Verification

| Check | Result |
|---|---|
| `bash -n experiments/prelaunch_gate.sh` | clean |
| `ENV_VERSION_MATCH` in non-comment lines | 4 |
| ENV_VERSION_MATCH probe in isolation | exit 1, prints `1.8.0` / `2.0.1` — **correct failure** |
| `capture_environment()` probe | `1.8.0 2.0.1 ade98c2c`, no raise |
| `pytest tests/unit/test_benchmark.py` | 32 passed |
| `pytest tests/unit/test_e1_band_mode.py` | **19 passed** in 2123 s (35 min), incl. 2 new + 1 new negative assertion |
| `pytest tests/unit/test_experiments_provenance.py` | 292 passed, 25 skipped |
| both fast suites re-run at final HEAD | 324 passed, 25 skipped |
| `pytest tests/unit/test_datasets.py` (Task C) | 53 passed |
| `git status --porcelain experiments/` | **empty** — no results tree moved |
| `grep -c 'opencv-python==4.13'` | 1 in each of pyproject.toml, requirements.txt |
| pyproject parses, dependency present | `pin ok` |
| `4.13` named | walkthrough 4, README 2, loader.py 4 |
| `results_linux32gb` in README | 2 |
| `E2_BENCHMARK_PATH` discoverable | README + new pending todo |
| todos in `pending/` matching `2026-08-1[23]` | only the **new** E4 todo; all four target files gone |
| todos in `done/` | all four present |
| `2026-08-05-pin-opencv-below-5-0.md` | still in `pending/`, as required |
| ruff check + format | clean on every touched Python file; pre-commit passed on all four commits |

The full suite was **not** run. No `pip install`. The prelaunch gate was never invoked whole.
No E1 band re-run.

## Deviations from Plan

**1. [Rule 3 — Blocking] `PENDING_CSVS` allowance in `test_experiments_provenance.py`**
- **Found during:** Task B
- **Issue:** `test_csv_to_record_has_no_stale_entries` fails on a map entry whose artifact is
  produced by a run that happens after this plan.
- **Fix:** explicit per-file exemption plus a new test that fails once the file lands.
- **Files:** `tests/unit/test_experiments_provenance.py`
- **Commit:** `5ae6683`

**2. [Plan-internal ambiguity] ENV_VERSION_MATCH numbered 2, LEGALITY_PROBE 3**
- Reconciles the plan's action prose with its success criterion; ordering justified on
  dependency grounds and documented in the script. Detailed above.

**3. [Bookkeeping] `git mv` not usable for the todo moves**
- All four todo files were **untracked** at dispatch (`??` in `git status`), so `git mv`
  errors with "not under version control". Used a plain `mv` plus `git add` of the
  destination path — identical end state, and each move is still in its own fix's commit.
  The files appear as `create mode` under `done/` in each commit.

**4. [Judgement, reported as instructed] `loader.py` had no reproducibility claim**
- Added a qualifying `Note:` rather than inventing one. Detailed under Task C.

**5. [Not done, deliberately] knowledge-base Table of Contents not updated**
- The plan said to update the ToC "if that ToC enumerates subsections". It does not — it
  lists top-level sections with entry counts, and those counts are already stale (Known
  Issues & Workarounds reads "(0 entries)" against 6). Editing one count would neither fix
  nor consistently extend it. Left alone rather than half-corrected.

## Known Stubs

None.

## Threat Flags

None. No new network, auth, file-access or schema surface. The `aquacal_version_declared`
field is additive and read-only; the `opencv-python` change is a constraint edit with no
install performed.

## Orchestrator Follow-Up

1. `pip install -e . --no-deps` in the `AquaCal` env; confirm
   `python -c "import aquacal; print(aquacal.__version__)"` reports **2.0.1**. Task A's gate
   check FAILs until then, correctly.
2. Full unfiltered `pytest tests/` post-merge gate.
3. The E1 `--seeds 42-51` re-run (~70 min, detached, `python -u`). Run notes in the E1 todo,
   now at `.planning/todos/done/2026-08-13-e1-band-does-not-carry-parameter-level-columns.md`.
4. **After that run commits `exp1_parameter_band.csv`:** empty `PENDING_CSVS` in
   `tests/unit/test_experiments_provenance.py`. `test_pending_csvs_are_still_pending` will
   fail until you do.

## Self-Check: PASSED

All four commits verified present in `git log`. All twelve modified files and the one created
file verified on disk. `experiments/` verified clean.
