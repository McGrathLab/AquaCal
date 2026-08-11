---
phase: 21-new-feature-documentation-dataset-refresh
artifact: pre-release-audit
status: findings-only
audited: 2026-08-11
quick_task: 260811-e7s-pre-2-0-0-release-audit
---

# Pre-2.0.0 Release Audit

**Read-only.** No source, docs, config or packaging file was modified in producing this. Every
finding below is a proposal for a separate follow-up task.

## Why the ranking is what it is

663 commits are unpushed. The first push triggers python-semantic-release and cuts **v2.0.0**
(confirmed: a `feat!:` at `d406001` plus two `BREAKING CHANGE` footers since `v1.8.0` — the major
will be cut correctly). Everything fixed before that push lands inside 2.0.0 for free.

So findings are ranked by **lock-in, not ugliness**:

- **MUST-FIX-BEFORE-2.0.0** — leaving it is materially harder or impossible to correct after the
  cut: public API shape, published PyPI metadata, content archived at the tag, or a default whose
  later correction is itself a breaking change.
- **SHOULD-FIX** — real defects, but correctable in a 2.0.1 at no compatibility cost.
- **OPTIONAL** — cosmetic or housekeeping.

A cosmetic problem is OPTIONAL no matter how annoying it looks. A one-line fix can be MUST-FIX if
the release freezes it.

## Method and coverage

Four parallel scopes, each writing an independent fragment, merged and re-ranked globally here.

| Scope | Coverage |
|---|---|
| Public API | 3 known shims traced tree-wide; all 126 `__all__` entries across 10 modules import-verified; CLI flags traced to consumption |
| Packaging | `python -m build` actually run; wheel and sdist namelists inspected; wheel extracted and imported in isolation; `sphinx -W` built |
| Docs | 15 hand-crafted pages + `README.md` + `CONTRIBUTING.md` read in full; 2 notebooks via source-cell extraction; `docs/api/*.rst` target-resolution only (mid-depth, per user decision) |
| Orphans | 447 path tokens from 19 hand-authored files existence-tested; 44 source modules cross-referenced |

`docs/tutorials/03_cli_walkthrough.md` was excluded as corrected earlier the same day. **That
exclusion turned out to be partly wrong** — see MUST-4; the page is correct on numbers, which is
what was actually verified, but it advertises a broken flag.

Findings marked **[verified by orchestrator]** were independently re-checked against the source
rather than taken from the reporting agent.

---

# MUST-FIX-BEFORE-2.0.0

## MUST-1 — `scipy>=1.16` is unsatisfiable on Python 3.10, which the package claims to support
**[verified by orchestrator]**

`pyproject.toml:10` declares `requires-python = ">=3.10"`. `pyproject.toml:32` pins
`scipy>=1.16`. PyPI reports `scipy 1.16.0` as `requires_python: ">=3.11"` (fetched live
2026-08-11). **`pip install aquacal` cannot resolve on Python 3.10.**

Publishing 2.0.0 bakes that false claim into PyPI metadata that cannot be edited afterwards.

Two live consequences already latent in the repo:
- `test.yml:16` runs 3.10 jobs on ubuntu and windows; their `pip install -e ".[dev]"` must fail.
- `.readthedocs.yaml:6` pins Python 3.10, so the docs site advertised at `pyproject.toml:66`
  cannot build.

numpy 2.4 and pandas 3.0 also now require `>=3.11`, so 3.10 support is fictional in practice.

**Decision required:** drop 3.10 (itself a compatibility change that belongs in a major) or relax
the scipy floor. **Cost:** 4-5 files. See also OPT-7 — `requirements.txt` duplicates the
dependency list and doubles the edit surface.

## MUST-2 — `CITATION.cff` and the README BibTeX will ship 2.0.0 saying `version: 1.7.0`
**[verified by orchestrator]**

`CITATION.cff:18` says `version: 1.7.0`; `README.md:62` says `version = {1.7.0}`.
`pyproject.toml:122` configures semantic-release with `version_toml =
["pyproject.toml:project.version"]` **only** — no `version_variables` entry covers either file.
Already one release behind; at 2.0.0 it is two majors wrong.

This is locked because GitHub's citation widget and the Zenodo GitHub-release integration read the
file **at the tag**. The archived citation for v2.0.0 would be permanently wrong — which matters
directly for the SoftwareX submission.

`CITATION.cff:17` (`doi:`) and `date-released:` go stale by the same mechanism and should be
resolved in the same pass.

**Fix:** add `version_variables = ["CITATION.cff:version"]` so it is maintained durably, rather
than hand-editing once. Never hand-edit `pyproject.toml:project.version`. **Cost:** 2 files.

## MUST-3 — the shipped `manifest.json` points at the superseded Zenodo archive

`src/aquacal/datasets/data/manifest.json` carries `zenodo_record_id: 18645385`,
`md5:c66380aa…`, `size_bytes: 164023590`. The archive this phase built is `4350418046` bytes,
`md5:dff1012f…`. This file ships **inside the wheel** and is the sole runtime source of the
download URL and integrity check, so cutting 2.0.0 now ships a release whose
`load_example('real-rig')` fetches the archive Phase 21 exists to supersede.

**Already planned** — this is exactly plan 21-10, gated on the Zenodo publish. Recorded here so
the release checklist cannot cut before it lands. **Cost:** 3 fields, one file.

## MUST-4 — `aquacal calibrate -o/--output-dir` is silently ignored, and `--dry-run` reports otherwise
**[verified by orchestrator]**

`cli.py:163-164` sets `config.output_dir` on the in-memory object. `cli.py:190` then calls
`run_calibration(config_path, ...)`, which takes a **path** and re-reads the YAML from disk
(`pipeline.py:595`). The override never reaches the run.

Two aggravating factors:
- `cli.py:179-185` prints "Output will be saved to {config.output_dir}" under `--dry-run`, using
  the overridden value. Validating with `--dry-run -o out/` *confirms* an override that will not
  happen.
- The docs instruct readers to use it in three places, one of which offers it as the remedy for a
  named problem: `docs/guide/cli.md:25`, `docs/tutorials/03_cli_walkthrough.md:85`, and
  `docs/tutorials/03_cli_walkthrough.md:170` ("Re-run step 3 with `-o output_paper/` to keep the
  two runs' outputs separate").

Ranked MUST-FIX despite being non-breaking to fix later: the archive and paper drive readers
straight into the CLI walkthrough, which tells them to use this flag.

**Fix:** call `run_calibration_from_config(config, ...)` (`pipeline.py:772`) at `cli.py:190`.
**Cost:** 1 line, plus a test.

## MUST-5 — `generate_board_trajectory(min_cameras_per_frame=...)` is a documented no-op

Declared at `synthetic.py:513`, referenced zero times in the body (AST scan including nested
defs), promised twice in the docstring (`:522`, `:582`), and **passed by a live in-library
caller** at `pipeline.py:462` from `CalibrationConfig.min_cameras_per_frame` (`schema.py:337`).

Locked because 2.0.0 freezes this public signature — the same one Phase 19.3 already made
breaking by requiring `board`.

**Trap in the repair choice, and the reason this needs your decision:** *implementing* the filter
later would silently change generated trajectories for every existing seed and invalidate the
manuscript's seed bands. Dropping the parameter is the safe release-day move; implementing it is
a Phase-22 decision made deliberately, not a cleanup.

**Cost:** dropping is 2-3 files.

## MUST-6 — `aquacal.validation.__all__` exports a surface its own docstrings call experimental

`conditioning.py:64`, `:196`, `:250` each state "Experimental -- return shape may change", yet
`validation/__init__.py:29-34` exports all five conditioning names. `docs/api/validation.rst`
does **not** document them, so nothing external is being invited in deliberately.

Narrowing `__all__` after 2.0.0 is a breaking change; doing it now is free. Only internal
consumers exist: `_observability.py:658,662`, `pipeline.py:661`,
`e7_interface_ablation.py:453`. **Cost:** 1 file.

## MUST-7 — `interface.normal_fixed` has a three-way default disagreement
**[verified by orchestrator]**

| Source | Default |
|---|---|
| `pipeline.py:274` (YAML parser) | **`True`** |
| `schema.py:333` (dataclass) | `False` |
| `configuration.md:95` (docs) | `false` |

A config that omits the key gets tilt estimation **silently disabled**, opposite to both the
documented and the dataclass default. Only configs written by `aquacal init` are unaffected —
`cli.py:583` writes the key explicitly.

Ranked MUST-FIX because correcting a default *after* the release is itself a breaking behaviour
change. Fixing it now costs nothing.

**Not auto-fixable — the code may be what is wrong, not the docs.** This needs arbitration.

**Unaffected:** the published archive's `config_paper.yaml` sets `normal_fixed: false`
explicitly, so §3 and the Zenodo reference outputs do not depend on this.

## MUST-8 — remove the three deprecation shims (user decision 2026-08-11)

All three are effectively removable, and **there are no deprecation tests at all** — `grep -rin
'deprecat|initial_distances|refractive_project_fast' tests/` returns zero matches — so removal is
cheaper than expected.

| Shim | Verdict | Dependents |
|---|---|---|
| `initial_distances` (`pipeline.py:282`) | **CLEAN** | none |
| `refractive_project_fast()` (`refractive_geometry.py:921`) | **DEPENDENTS** | one: `docs/api/core.rst:17` (`autofunction`, doc-only) |
| `refractive_project_fast_batch()` (`refractive_geometry.py:945`) | **CLEAN** | none |

None is in any `__all__`. The `initial_distances` blocker — the published Zenodo dataset shipping
a config that used it — was cleared 2026-08-11; the new archive's `config_paper.yaml` uses
`initial_water_z`, and the one in-tree config
(`docs/tutorials/aquacal_data/real-rig/real-rig/config.yaml:72`) does too.

**Coupling:** `docs/api/core.rst:17` must be removed with the shim or the sphinx `-W` gate breaks.

**Caveat carried forward:** no `config_paper.yaml` exists in the repo — it lives only in the
Desktop archive staging — so the clearance rests on `21-ARCHIVE-MANIFEST.md:124-137`'s recorded
evidence rather than a file re-greppable here.

---

# SHOULD-FIX

## SH-1 — a fourth, undeclared compat shim in `load_calibration`
`serialization.py:92-101` silently accepts a legacy `interface_distance` field with **no warning
at all**, and its error message at `:101` advertises the legacy field to users. Unlike the three
named shims, this one was never declared deprecated. Decide whether it is supported or removed —
but do it knowingly.

## SH-2 — `docs/guide/optimizer.md` documents two mechanisms that were deliberately removed
`optimizer.md:132` and `:144` describe a board-Z bound and a boundary penalty that no longer
exist. `_optim_common.py:563-575` bounds only tilt/water_z/intrinsics — board-pose columns stay
±inf — and `_optim_common.py:56-61` states verbatim "No extra above-interface penalty term is
added," explaining that such a hinge would destroy the optimality diagnostic. The docs describe
the design that was rejected for a specific reason.

## SH-3 — every `aquacal compare` output filename in `docs/guide/cli.md` is wrong
`cli.md:137-144` vs `validation/comparison.py`: `metrics.csv`→`metrics_summary.csv` (`:335`),
`per_camera.csv`→`per_camera_metrics.csv` (`:342`), `depth_error_plot.png`→
`depth_error_comparison.png` (`:393`), `depth_binned.csv`→`depth_binned_errors.csv` (`:439`).
`xy_error_heatmaps.png` (`:431`) is undocumented. This is the **same defect class corrected in
the walkthrough today** — the guide page was missed.

## SH-4 — `docs/guide/benchmarking.md:16-17` claims a flag does not exist
"there is no config flag to disable it" is false: `pipeline.py:1763` guards the write with
`if config.save_benchmark:`, parsed at `pipeline.py:443`.

## SH-5 — `configuration.md:241-245` omits `save_benchmark` and `benchmark_memory`
Both are parsed (`pipeline.py:443-444`, `schema.py:363-364`). `benchmark_memory` is the only
switch for the per-stage memory block that `benchmarking.md:163-194` documents at length.

## SH-6 — `docs/index.md:55` loads `output/calibration.yaml`, which is never written
The pipeline writes `calibration.json` (`pipeline.py:1758`) and `load_calibration` is JSON-only
(`serialization.py:253-258`). The landing page's first code sample fails for anyone who runs it.
The same error is autodoc'd from a docstring at `schema.py:155`, so the fix touches `src/`.

## SH-7 — `aquacal_data/` has no `.gitignore` rule
**[verified by orchestrator]** `git check-ignore -v aquacal_data` exits 1. `download.py:24` sets
`cache_dir = Path.cwd() / "aquacal_data"`. The only guard is a nested `aquacal_data/.gitignore`
containing `*` — which **ignores itself**, is therefore untracked, and does not survive a clone.
Same for `docs/tutorials/aquacal_data/` (currently 354 MB, including a copy of the archive zip).

This machine is safe and `git status` is clean; the exposure is a fresh contributor one
`git add -A` from staging a multi-GB blob. Downgraded from the reporting agent's MUST-FIX: a
`.gitignore` line is not locked by the release. **Cost:** 1 line.

## SH-8 — `experiments/README.md` under-qualifies two downstream paths
`:68` (`figures/aquacal/synthetic_validation.py`) and `:74` (`figures/aquacal/zenodo_e2e.py`)
read as repo-relative, but no `figures/` directory exists. Sibling rows `:90` and `:92` give the
same class of path **fully qualified** as `DissertationFigures/src/dissertationfigures/figures/
aquacal/` — a different repository. These are not missing files; they are ambiguous references.
Ditto marks at `:69`, `:70`, `:71`, `:75`, `:76` inherit the bad cell, so **2 edits fix 7 rows.**

This also resolves the rig-figure generator question from earlier today: `zenodo_e2e.py` is not
lost, it lives in the DissertationFigures repository.

## SH-9 — `experiments/README.md` omits 4 of 11 experiment scripts
`e7_focal_standoff_analysis.py`, `reconstruction_bootstrap.py` and `check_rerun_gates.py` all
have tests — live code the repo's own map does not point at. `fd_jacobian_accuracy.py` is the
genuine orphan: no README row, **no test file**, referenced only from `19.5-02-PLAN.md`.

## SH-10 — `02_synthetic_validation.ipynb` imports from `tests/`
Cell 4 makes the tutorial unrunnable from a `pip install` — and cell 1 (`:59`) tells Colab users
to clone rather than pip-install because of it. All nine names are now public at
`datasets/__init__.py:42-59`, so the import can simply be repointed.

## SH-11 — notebook Colab badges point at the wrong repository
`01_full_pipeline.ipynb:9` and `02_synthetic_validation.ipynb:10,:59` reference
`tlancaster6/AquaCal`; the canonical repo is `McGrathLab/AquaCal` (`CITATION.cff:8`). The same
error is live on the Zenodo record's repository URL.

## SH-12 — `01_full_pipeline.ipynb` cell 22 uses a key the parser ignores
It names `initial_water_zs` (plural); `pipeline.py:340` reads only `initial_water_z`. Silently
ignored.

## SH-13 — `optimizer.md:222` misdescribes `dense_threshold` by orders of magnitude
Documented as "1000+ parameters"; actually `n_residuals × n_params > 5e8`
(`_optim_common.py:725, 756-757`).

## SH-14 — public docstrings advertise dataset names that raise
`_manifest.py:39` and `download.py:133` reference `small`/`medium`/`large` datasets; only
`real-rig` exists, so those raise `ValueError`.

## SH-15 — no `py.typed` marker
Every annotation in the package is invisible to downstream mypy/pyright. Additive, so not locked
— but a major release is the natural moment.

## SH-16 — `docs/tutorials/index.md:26-27` claims Tutorial 03 reproduces §3
Gated on the manuscript work tracked in MF-19, not independently fixable. Sits outside the
already-corrected walkthrough.

## SH-17 — `Development Status :: 4 - Beta` on a 2.0.0
`pyproject.toml:19`. Publishing a 2.0.0 as Beta is a metadata claim readers act on.

---

# OPTIONAL

- **OPT-1** — `docs/_static.png`, a tracked 21 KB PNG at docs root with zero references repo-wide
  (`conf.py:43` sets `html_static_path = ["_static"]`, a separate directory that exists).
- **OPT-2** — `docs/tutorials/output/*.csv`, 4 tracked CSVs referenced by no page and neither
  notebook; `nbsphinx_execute = "never"` means nothing regenerates them.
- **OPT-3** — `experiments/rerun_19_4.log` (144 KB) is tracked with no un-ignore rule, unlike
  `rerun_19_5.log` and `repeat_stdout.log` which are tracked deliberately with rationale at
  `.gitignore:251` and `:281`. Predates the convention; survives only because gitignore does not
  apply to tracked files.
- **OPT-4** — aggregated experiment residue: 14 `*.log` (12 already ignored), 4 `*_state.tsv`,
  3 `*_frozen_sha.txt`, 5 `.sh` runners, 4 superseded `results_*` dirs, `experiments/archive/`
  (9 snapshots, 31 tracked files). Explicitly not worth fixing.
- **OPT-5** — `src/aquacal/config/example_config.yaml` sits inside the importable package but
  ships in nothing. Harmless: nothing opens it.
- **OPT-6** — `docs/conf.py:73-97` regenerates four **tracked** PNGs during any docs build. Output
  was byte-identical here so git stayed clean, but `conf.py:94-95` swallows generation failures.
- **OPT-7** — `requirements.txt` duplicates the dependency list, doubling MUST-1's edit surface.
- **OPT-8** — `release.yml` cuts the tag with no `needs:` on any test job, so MUST-1's red 3.10
  jobs will not block the 2.0.0 tag. PyPI itself is protected: `publish.yml:8-31` gates on pytest.
- **OPT-9** — sphinx is unpinned (`pyproject.toml:51`, `sphinx>=6.2`); the clean `-W` result below
  is authoritative for sphinx 9.1.0 only.
- **OPT-10** — sdist ships no tests, CHANGELOG or CITATION (no `MANIFEST.in`).
- **OPT-11** — cosmetic docs: `cli.md:175` sample output `aquacal 0.1.0`; `optimizer.md:280`
  line-range cites the fisheye branch rather than the simplification loop at
  `intrinsics.py:451-462`; `optimizer.md:333` "Stage 2-4"; `troubleshooting.md:190-191`
  mislabelled parameter counts; orphan "Exported Data" sections in both notebooks; mojibake em
  dashes at `01_full_pipeline.ipynb:51,55,542,618`; `CONTRIBUTING.md:129-131` misnumbered list;
  `benchmarking.md:289` points readers at unshipped `.planning/`.
- **OPT-12** — the scalar Newton diagnostic's name does not match what it measures (compare the
  pre-existing note that `newton_iterations.csv` measures the wrong Newton loop).
- **OPT-13** — stale "will be populated as modules are implemented" scaffolding in shipped
  `__init__` files.

---

# UNVERIFIED

- **UNV-1** — the "~50× faster than Brent" claim (`refractive_geometry.md:103`, and in source at
  `refractive_geometry.py:825`) has no locatable measurement. No experiment times Newton against
  Brent. **It must not be conflated with E1's 97-178× band**, which measures something else
  entirely. Settling it needs a new microbenchmark; the honest alternative is to drop the number.
- **UNV-2** — the ReadTheDocs URL advertised at `pyproject.toml:66` returned 403. Ambiguous
  between a bot block and an unpublished project. Settled by opening it in a browser.
- **UNV-3** — whether the "v1.7/v1.8" version framing in `configuration.md` should be rewritten
  for a 2.0.0. Editorial.

---

# Clean results

Recorded so coverage is auditable rather than best-effort.

- **The sphinx `-W` release gate is CLEAN.** `sphinx-build -W --keep-going` exits 0 with zero
  warnings. The deferred `generate_board_trajectory` docutils error in `deferred-items.md` is
  genuinely **FIXED**, not merely untriggered — the function was confirmed to be actually
  autodoc'd (`docs/api/datasets.rst:16`; it appears in the rendered output), and `conf.py` sets no
  `suppress_warnings`. **That deferred item can be closed.** Caveat: `docs.yml:3-5` triggers on
  `pull_request` only, so this gate will not run on the push regardless.
- **The wheel is not broken.** `datasets/data/manifest.json` is present at 374 bytes. Verified the
  hard way: the wheel was extracted and imported with `PYTHONPATH` pointing only at the extracted
  tree, where `get_manifest()` returned real content and `list_datasets()` returned
  `['real-rig']`.
- **Zero stray inclusions** in wheel or sdist — no `.planning/`, tests, experiments,
  `aquacal_data/`, logs or `__pycache__`. Wheel 197 KB, sdist 177 KB, largest member 79,853 B.
- **All 126 `__all__` entries** across 10 modules resolve; no underscore helpers exported, no
  divergent duplicate re-exports.
- **Every CLI flag is consumed** except MUST-4, and no subcommand or flag name looks regrettable
  for a 2.0.0.
- **Zero orphaned source modules** — all 44 non-`__init__` modules have ≥3 cross-references.
- **Zero orphaned docs pages** — every `.md`/`.rst` under `docs/` appears in a toctree.
- **All 33 autodoc targets** in `docs/api/*.rst` import cleanly; all four toctrees match the
  filesystem; zero broken relative links across the 15 hand-crafted pages; all `{ref}` labels
  resolve; every notebook API call matches its live signature.
- **No stale run-quoted numbers found in docs.** The only memory figure present
  (`benchmarking.md:189`, ~10.26 GiB) is the correct one; no `~135×` point estimate and no
  `~3.6 GB` figure appears anywhere.
- **446 of 447 path tokens** across 19 hand-authored files resolve; the exceptions are SH-8.
- **semantic-release will cut a major correctly** — `d406001 feat!:` plus two `BREAKING CHANGE`
  footers since `v1.8.0`.

# Suggested line

If the whole MUST list is too much before 2026-08-21, the defensible cut is **MUST-1 through
MUST-4 plus MUST-8**: they cover unfixable published metadata, the citation archived at the tag,
the dataset pointer, a flag the paper's own tutorial tells readers to use, and the shim removal
already decided. MUST-5 through MUST-7 each need a judgement call that should not be rushed —
and each is a decision about behaviour, not a repair.
